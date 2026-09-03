---
name: rbln-profile
description: >-
  Find where time goes in a model running on Rebellions ATOM (RBLN NPU): stage
  wall-time hooks around optimum RBLNRuntimeModel.forward and the inner
  rebel.Runtime call, RBLN_PROFILER=1 kernel traces (Perfetto .pb via
  rebel.profiler.profile), Neural Engine vs Neural DMA vs Task DMA busy to
  decide compute-bound vs weight-DMA-bound, host generate-loop share, and
  recovering traces from a vllm-rbln server whose workers never call
  profiler.done(). Use for "병목이 어디", "프로파일", "decode step이 왜 느려",
  prefill vs decode split, TPOT analysis, or before picking an optimization.
---

# Profiling on ATOM

Measure in two layers. Layer 1 is stage wall time with the profiler off; layer 2
is a kernel trace with it on. Layer-2 wall times carry roughly 2× overhead, so
never quote them as timings — read only track occupancy and op distribution.

## When this applies

- You have an end-to-end latency but do not know which stage dominates.
- You need to know whether the decode step, prefill or encoder is compute-bound
  or DMA-bound before choosing an optimization lever.
- You need the device-time composition inside a serving engine (vllm-rbln).

## Procedure

### Layer 1: stage wall time (profiler OFF)

1. Wrap host preprocessing, each ATOM call and host postprocessing in
   `perf_counter`. Discard at least one warmup, repeat 5+ times, report p50/p95.
2. On the optimum path, hook at two depths:
   - `RBLNRuntimeModel.forward` (host prep plus the device call)
   - the inner `runtime_model.runtime` (the `rebel.Runtime` call: device plus
     transfer)
   The difference is optimum's per-step host work. Hook code lives in
   [references/profiler-mechanics.md](references/profiler-mechanics.md).
3. Measure the generate loop's host share as the sum of gaps between consecutive
   decode call start times minus the device call durations.
4. Tabulate stage, p50 and share of total. For decode, also report the step
   distribution (p50 / p95 / max).

**First verdict**: what percentage is host work (gaps plus optimum prep)? Around
2% means loop optimization has nothing to give and device time is the body.

### Layer 2: kernel trace (profiler ON)

1. Run once on a short workload (say 16 tokens) with `RBLN_PROFILER=1` inside a
   `rebel.profiler.profile(output_dir)` context. On the optimum path, create the
   runtime with `rbln_activate_profiler=True`. Do one unprofiled warmup first.
2. Output is `rbln_<date>_<time>_<seq>.pb`. The profiler assigns `seq` in call
   order, so map indices to phases by execution order (warmup calls consume
   indices too).
3. Aggregate per-phase track busy, NE/DMA overlap, top op families and Task DMA
   bytes moved:
   `${CLAUDE_SKILL_DIR}/scripts/trace_summary.py --trace-dir <dir> --prefix rbln_<date>_<time> --phase prefill=19 --phase decode=20-34`
   Requires the `perfetto` package (it downloads its trace_processor shell with
   curl on first use).
4. In a serving engine, `.pb` files are only written by `profiler.done()`, which
   the workers never call. Put
   `${CLAUDE_SKILL_DIR}/scripts/profiler_flush_hook.py` on `PYTHONPATH` as
   `sitecustomize.py` and create the trigger file to flush. Details in the
   mechanics reference.

### 3. Interpret

Rules in [references/interpretation.md](references/interpretation.md). Summary:

| Observation | Verdict | Lever |
|---|---|---|
| Neural Engine busy ≥ 90%, DMA low | compute-bound | lower-precision compute, shrink sequence/padding (prefill chunk) |
| Neural DMA busy ≥ 90%, small NE `comp_cycle`, `linear` family dominates DMA | weight-DMA-bound | lower-precision weights, speculative decoding (verifying K+1 costs about as much as 1 token), shrink lm_head, share weight streaming across a batch |
| Large byte movement on Task DMA | activation / KV transfer | shrink the KV length (`max_seq_len`), shrink logits transfer (argmax fusion) |
| A short prompt's prefill span equals a long prompt's | prefill padding | set `prefill_chunk_size` to the smallest chunk that covers the prompt in one pass |
| Step time jumps when batch b crosses a bucket edge | decoder batch bucket padding | align the operating batch to a bucket edge, or compile extra buckets |

### 4. Before committing to a lever

- What share of end-to-end is that stage? Halving a stage worth 7% buys 3.5%.
- Does the lever preserve the correctness gate
  (`/rbln-skills:rbln-precision-check`)?
- In serving, single-request latency and concurrent throughput can move in
  opposite directions: speculative decoding gave +17% at N=1 and −12 to −28% at
  N ≥ 4.

## Done when

1. You have the stage table (p50, share) and the host share.
2. For the dominant stage you have a compute-bound / DMA-bound / padding verdict
   with the supporting numbers (track busy, top ops).
3. One next experiment is written down with its expected upper bound (e.g.
   "lm_head is 17% of a step, so lowering its precision caps out near 8%").

## Verified against

ATOM-Max (RBLN-CA25), rebel-compiler 0.10.5.dev143 (`RBLN_PROFILER` in
`rebel/compiled_model.py`, `profile()` in `rebel/profiler.py`), optimum-rbln
0.10.4 (`rbln_activate_profiler` in `modeling_decoderonly.py`), serving on
vllm-rbln 0.11.0.
