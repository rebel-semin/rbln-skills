"""Summarize RBLN profiler traces (Perfetto .pb) per inference phase.

Reads traces written under ``RBLN_PROFILER=1`` / ``rebel.profiler.profile`` and
aggregates, per phase, how busy each hardware track was (Neural Engine
Clusters, Neural DMA, Task DMA, ...), how much compute and DMA overlap, which
op families dominate, and which linear ops stream the most weight bytes.
Sequence indices are assigned by the profiler in call order; pass the mapping
explicitly, e.g.

    python trace_summary.py --trace-dir traces \
        --prefix rbln_20260902_012906319 \
        --phase audio_tower=18 --phase prefill=19 --phase decode=20-34

Verified with rebel-compiler 0.10.5.dev143 traces on ATOM-Max (RBLN-CA25).

Requires the ``perfetto`` package (trace_processor downloads its shell binary
on first use, which needs ``curl``).
"""

from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

from perfetto.trace_processor import TraceProcessor

TRACKS = ["Host", "Neural Engine Clusters", "Neural DMA", "Task DMA",
          "External HDMA", "Device HDMA", "Device Sync"]


def parse_range(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def union_us(intervals: list[tuple[int, int]]) -> float:
    total = 0
    cur_s = cur_e = None
    for s, e in sorted(intervals):
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += cur_e - cur_s
    return total / 1e3


def family(name: str) -> str:
    name = re.sub(r"^\d+_", "", name)
    name = re.sub(r"_\d+$", "", name)
    return re.sub(r"_\d+$", "", name)


def op_id(name: str) -> int | None:
    match = re.match(r"^\d+_linear_(\d+)_\d+$", name)
    return int(match.group(1)) if match else None


def summarize_trace(path: Path) -> dict:
    tp = TraceProcessor(trace=str(path))
    rows = list(tp.query("""
        select th.name as thread, s.name as sname, s.dur as dur, s.ts as ts,
               a.display_value as v
        from slice s
        join thread_track tt on s.track_id = tt.id
        join thread th using(utid)
        left join args a on s.arg_set_id = a.arg_set_id
             and a.key = 'debug.Slice Arguments'"""))
    tp.close()

    device_rows = [r for r in rows if r.thread != "Host"]
    t0 = min(r.ts for r in device_rows)
    t1 = max(r.ts + r.dur for r in device_rows)
    span_us = (t1 - t0) / 1e3

    by_track: dict[str, dict] = {}
    intervals: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
    bytes_by_track: collections.Counter = collections.Counter()
    cycles = 0
    fam_busy: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    linear_nd: collections.Counter = collections.Counter()
    for r in rows:
        track = by_track.setdefault(r.thread, {"slices": 0, "busy_us": 0.0})
        track["slices"] += 1
        track["busy_us"] += r.dur / 1e3
        intervals[r.thread].append((r.ts, r.ts + r.dur))
        fam_busy[r.thread][family(r.sname)] += r.dur / 1e3
        if r.v:
            args = json.loads(r.v)
            for item in args.get("transfer", []):
                match = re.search(r":(\d+)Byte", item)
                if match:
                    bytes_by_track[r.thread] += int(match.group(1))
            for item in args.get("comp_cycle", []):
                cycles += int(item)
        if r.thread == "Neural DMA":
            ident = op_id(r.sname)
            if ident is not None:
                linear_nd[ident] += r.dur / 1e3
    for name, track in by_track.items():
        track["busy_pct_of_span"] = 100.0 * track["busy_us"] / span_us
        track["union_us"] = union_us(intervals[name])

    ne = intervals["Neural Engine Clusters"]
    dma = intervals["Neural DMA"] + intervals["Task DMA"]
    both = union_us(ne + dma)
    overlap = {
        "ne_union_us": union_us(ne),
        "dma_union_us": union_us(dma),
        "ne_or_dma_us": both,
        "ne_only_us": both - union_us(dma),
        "dma_only_us": both - union_us(ne),
    }
    top_linear = sorted(linear_nd.items(), key=lambda x: -x[1])[:3]
    return {
        "file": path.name,
        "device_span_us": span_us,
        "tracks": by_track,
        "overlap": overlap,
        "task_dma_transfer_bytes": bytes_by_track.get("Task DMA", 0),
        "neural_engine_comp_cycles": cycles,
        "top_families": {
            track: [(f, round(v, 1)) for f, v in counter.most_common(6)]
            for track, counter in fam_busy.items()
        },
        "top_linear_ops_neural_dma_us": [(i, round(v, 1)) for i, v in top_linear],
        "linear_ops_on_neural_dma": len(linear_nd),
    }


def mean(values):
    return sum(values) / len(values) if values else 0.0


def aggregate_phase(items: list[dict]) -> dict:
    tracks = {}
    for name in TRACKS:
        present = [i["tracks"][name] for i in items if name in i["tracks"]]
        if present:
            tracks[name] = {
                "busy_us": mean([p["busy_us"] for p in present]),
                "busy_pct_of_span": mean([p["busy_pct_of_span"] for p in present]),
                "slices": mean([p["slices"] for p in present]),
            }
    return {
        "sequences": [i["file"] for i in items],
        "n": len(items),
        "device_span_us": mean([i["device_span_us"] for i in items]),
        "tracks": tracks,
        "overlap": {
            k: mean([i["overlap"][k] for i in items]) for k in items[0]["overlap"]
        },
        "task_dma_transfer_mb": mean([i["task_dma_transfer_bytes"] for i in items]) / 1e6,
        "neural_engine_comp_cycles": mean([i["neural_engine_comp_cycles"] for i in items]),
        "top_families": items[0]["top_families"],
        "top_linear_ops_neural_dma_us": items[0]["top_linear_ops_neural_dma_us"],
        "linear_ops_on_neural_dma": items[0]["linear_ops_on_neural_dma"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-dir", required=True, help="directory holding rbln_*.pb")
    parser.add_argument("--prefix", required=True, help="rbln_<date>_<time>")
    parser.add_argument("--phase", action="append", required=True,
                        help="name=<seq range>, e.g. decode=20-34")
    parser.add_argument("--out", default="kernel_trace_summary.json")
    args = parser.parse_args()

    trace_dir = Path(args.trace_dir)
    report = {"prefix": args.prefix, "phases": {}}
    for spec in args.phase:
        name, rng = spec.split("=", 1)
        items = [
            summarize_trace(trace_dir / f"{args.prefix}_{seq}.pb")
            for seq in parse_range(rng)
        ]
        report["phases"][name] = aggregate_phase(items)

    for name, ph in report["phases"].items():
        print(f"\n== {name}: n={ph['n']} device span {ph['device_span_us']:.1f} us")
        for track, t in ph["tracks"].items():
            print(f"   {track:24s} busy {t['busy_us']:10.1f} us ({t['busy_pct_of_span']:5.1f}%)")
        ov = ph["overlap"]
        print(f"   overlap: NE-only {ov['ne_only_us']:.1f} us, DMA-only {ov['dma_only_us']:.1f} us, "
              f"NE|DMA {ov['ne_or_dma_us']:.1f} us; Task DMA moved {ph['task_dma_transfer_mb']:.1f} MB; "
              f"NE cycles {ph['neural_engine_comp_cycles']:.0f}")
        for track in ("Neural Engine Clusters", "Neural DMA", "Task DMA"):
            fams = ph["top_families"].get(track)
            if fams:
                print(f"   top {track}: {fams[:4]}")
        if ph["top_linear_ops_neural_dma_us"]:
            print(f"   top linear ops on Neural DMA (id, us): {ph['top_linear_ops_neural_dma_us']}")

    out = Path(args.out)
    out.write_text(json.dumps(report, indent=2))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
