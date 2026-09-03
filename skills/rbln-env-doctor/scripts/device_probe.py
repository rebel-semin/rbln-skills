"""Tiny real-device placement probe for RBLN ATOM.

Compiles `x + 1` with rebel.compile_from_torch, runs it with
rebel.Runtime(device=N) on every requested container-visible device, and
checks both the output and that `rbln-smi` shows this PID on that device row.
Prints one JSON line prefixed with ATOM_LAB_DEVICE_PROOF= and exits non-zero
unless every requested device is verified.

Run only on idle devices: this really executes on the chip.
Verified on ATOM-Max (RBLN-CA25), rebel-compiler 0.10.5.dev143, devices 0-3.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--devices", required=True, help="comma-separated container-visible ids")
    args = ap.parse_args()
    requested = [int(x) for x in args.devices.split(",") if x]

    import rebel
    import torch

    class Probe(torch.nn.Module):
        def forward(self, x):
            return x + 1.0

    count = int(rebel.device_count())
    if not requested or len(set(requested)) != len(requested):
        raise ValueError("devices must be a non-empty list of unique ids")
    if any(d < 0 or d >= count for d in requested):
        raise ValueError(f"requested {requested}, but SDK exposes 0..{count - 1}")

    x = torch.zeros(1, 4, dtype=torch.float32)
    compiled = rebel.compile_from_torch(
        Probe().eval(),
        input_info=[("x", [1, 4], "float32")],
        example_inputs=[x],
    )
    verified, details = [], []
    for device in requested:
        runtime = rebel.Runtime(compiled, tensor_type="pt", device=device)
        output = runtime(x)
        output_ok = bool(torch.equal(output, x + 1.0))
        smi = subprocess.run(["rbln-smi"], check=False, capture_output=True, text=True).stdout
        placement_ok = any(
            re.search(rf"\|\s*{device}\s*\|.*\b{os.getpid()}\b", line)
            for line in smi.splitlines()
        )
        details.append({"device": device, "output_ok": output_ok, "placement_ok": placement_ok})
        if output_ok and placement_ok:
            verified.append(device)

    result = {
        "ok": verified == requested,
        "device_count": count,
        "npu": rebel.get_npu_name(),
        "rebel_version": getattr(rebel, "__version__", "unknown"),
        "verified_devices": verified,
        "details": details,
    }
    print("ATOM_LAB_DEVICE_PROOF=" + json.dumps(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
