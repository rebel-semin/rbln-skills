# How the profiler behaves, and the hook code

## Layer 1 hook: optimum RBLNRuntimeModel at two depths

```python
import time

class TimedRuntime:
    """Proxy around rebel.Runtime that times only the device call."""
    def __init__(self, inner, sink):
        self._inner, self._sink = inner, sink
    def __call__(self, *a, **k):
        t0 = time.perf_counter()
        out = self._inner(*a, **k)
        self._sink.append(time.perf_counter() - t0)
        return out
    def __getattr__(self, name):
        return getattr(self._inner, name)

def hook_runtime_model(runtime_model, calls, device, starts):
    device_sink = []
    runtime_model.runtime = TimedRuntime(runtime_model.runtime, device_sink)
    original = runtime_model.forward
    def timed_forward(*a, **k):
        start = time.perf_counter(); before = len(device_sink)
        out = original(*a, **k)
        calls.append(time.perf_counter() - start)
        starts.append(start)
        device.extend(device_sink[before:])
        return out
    runtime_model.forward = timed_forward
```

An optimum decoder-only model holds `RBLNRuntimeModel` objects such as
`model.prefill_decoder` and `model.decoders[batch]`. Hook each one. Call minus
device is optimum's per-step host work. The generate-loop gap is
`starts[i+1] - (starts[i] + calls[i])`.

## Layer 2: turning the profiler on

```python
import os
os.environ["RBLN_PROFILER"] = "1"           # before creating any runtime
from optimum.rbln import RBLNQwen3ForCausalLM
model = RBLNQwen3ForCausalLM.from_pretrained(cache_dir, export=False,
                                             rbln_device=0, rbln_activate_profiler=True)
# hand-written path: rebel.Runtime(...) reads the RBLN_PROFILER env var

from rebel.profiler import profile
run_once()                                   # unprofiled warmup, keeps lazy setup out
with profile(output_dir="traces"):
    run_once()                               # keep it short (e.g. 16 tokens)
```

Output lands as `traces/rbln_<YYYYMMDD>_<HHMMSS...>_<seq>.pb`, where `seq` is
runtime call order. Example mapping: the audio runtime's first call is 0, warmup
audio/prefill/decode are 1/2/3–17, and the profiled run is 18/19/20–34. Files
sometimes land in the current directory as `rbln_*.pb`, so diff the file listing
before and after the run to pick up new files.

Step times in a profiled run roughly double (15.8 → 31.8 ms, mostly writing trace
files). Never quote them; mark the run `profiled: true`.

## Reading a trace

Use `TraceProcessor` from the `perfetto` package. Thread track names: `Host`,
`Neural Engine Clusters`, `Neural DMA`, `Task DMA`, `External HDMA`,
`Device HDMA`, `Device Sync`. Slice args (`debug.Slice Arguments`) carry
`transfer: [":<N>Byte"]` and `comp_cycle: [...]`. Op names look like
`<idx>_<family>_<opid>_<n>`, e.g. `12_linear_196_0`.

`scripts/trace_summary.py` aggregates per phase:
- busy_us per track, share of span, union
- NE-only / DMA-only / NE|DMA overlap
- Task DMA bytes moved, summed NE comp_cycles
- top op families per track, and the top linear op ids on Neural DMA (which
  identifies the layers streaming the most weight)

## Recovering traces from a serving engine (vllm-rbln)

The problem: `RBLN_PROFILER=1` collects data, but `.pb` files are written only by
`rebel._C.profiler.done()`. A vLLM server never calls it, and its worker
processes are torn down (mp executor, shutdown timeout 0) in a way that made
atexit and `worker.shutdown()` hooks unreliable — three attempts failed.

What worked: place `scripts/profiler_flush_hook.py` on `PYTHONPATH` under the
name `sitecustomize.py`. Every Python process with `RBLN_PROFILER=1` then starts a
daemon thread polling for a trigger file (`RBLN_PROFILER_TRIGGER`, default
`/traces/FLUSH`). When the trigger appears, each process that imported `rebel`
calls `profiler.start(cwd)` followed by `profiler.done()`, writing one
multi-stream `.pb`.

```bash
mkdir -p /path/hooks && cp profiler_flush_hook.py /path/hooks/sitecustomize.py
# engine container: -e RBLN_PROFILER=1 -e PYTHONPATH=/hooks:$PYTHONPATH \
#                   -v /path/hooks:/hooks:ro -v /path/traces:/traces
# after applying load:
touch /path/traces/FLUSH   # each process leaves FLUSH.<pid>.done
```

The "module" numbers in a serving trace are per graph (prefill, decoder buckets,
audio-tower buckets, small sampler graphs); identify them by span length and call
count.
