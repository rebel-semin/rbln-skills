#!/usr/bin/env bash
# Print the RBLN environment facts the doctor procedure asks for.
# Read-only. Safe to run on a busy host (it does not touch the chips).
set -u

PY=${RBLN_PYTHON:-/opt/python/bin/python}
[ -x "$PY" ] || PY=$(command -v python3)

echo "== devices"
ls -l /dev/rsd* /dev/rbln* 2>&1
echo
echo "== rbln-smi"
if command -v rbln-smi >/dev/null 2>&1; then rbln-smi 2>&1 | head -40; else echo "rbln-smi not found"; fi
echo
echo "== python: $PY"
"$PY" - <<'PYEOF' 2>&1
import importlib, sys
print("python", sys.version.split()[0])
for name in ("torch", "rebel", "optimum.rbln", "transformers", "vllm"):
    try:
        m = importlib.import_module(name)
        print(f"{name:14s} {getattr(m, '__version__', '?')}")
    except Exception as exc:  # noqa: BLE001
        print(f"{name:14s} IMPORT FAILED: {exc!r}")
try:
    import rebel
    print("device_count", rebel.device_count(), "npu", rebel.get_npu_name())
except Exception as exc:  # noqa: BLE001
    print("device_count FAILED:", repr(exc))
try:
    import torch
    print("torch threads", torch.get_num_threads())
except Exception:
    pass
PYEOF
echo
echo "== pip versions"
"$PY" -m pip show rebel-compiler optimum-rbln vllm-rbln 2>/dev/null | grep -E "^(Name|Version)" || true
echo
echo "== env"
env | grep -E "^(RBLN_|HF_HUB_|OMP_|CUDA_VISIBLE)" | sort
echo
echo "== host"
nproc; uptime; uname -r
if [ -f /sys/fs/cgroup/cpuset.cpus.effective ]; then echo "cpuset: $(cat /sys/fs/cgroup/cpuset.cpus.effective)"; fi
