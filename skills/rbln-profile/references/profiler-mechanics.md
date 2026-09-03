# 프로파일러 동작과 훅 코드

## 1층 훅: optimum RBLNRuntimeModel 두 깊이

```python
import time

class TimedRuntime:
    """rebel.Runtime 프록시. device 호출 시간만 기록."""
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

optimum decoder-only 모델은 `model.prefill_decoder`, `model.decoders[batch]` 같은
`RBLNRuntimeModel`을 가진다. 각각에 훅을 건다. 호출 − device = optimum step별 host 작업.
generate 루프 gap = `starts[i+1] − (starts[i] + calls[i])`.

## 2층: 프로파일러 활성화

```python
import os
os.environ["RBLN_PROFILER"] = "1"           # 런타임 생성 전에
from optimum.rbln import RBLNQwen3ForCausalLM
model = RBLNQwen3ForCausalLM.from_pretrained(cache_dir, export=False,
                                             rbln_device=0, rbln_activate_profiler=True)
# 손 작성 경로: rebel.Runtime(...) 는 RBLN_PROFILER 환경변수를 읽음

from rebel.profiler import profile
run_once()                                   # unprofiled warmup (lazy setup 제외)
with profile(output_dir="traces"):
    run_once()                               # 짧게 (예: 16 token)
```

출력 `traces/rbln_<YYYYMMDD>_<HHMMSS...>_<seq>.pb`. seq는 런타임 호출 순서. 예: audio
runtime 초기 호출 0, warmup audio/prefill/decode 1/2/3~17, profiled run 18/19/20~34.
현재 디렉터리에 `rbln_*.pb`가 떨어지는 경우도 있으니 실행 전후 파일 목록 차이로 새
파일을 잡는다.

프로파일된 런의 step 시간은 약 2배(15.8 → 31.8 ms, 대부분 트레이스 파일 쓰기). 시간
수치로 인용하지 않고 `profiled: true`로 표시한다.

## 트레이스 읽기

`perfetto` 패키지의 `TraceProcessor`. 스레드 트랙 이름: `Host`, `Neural Engine
Clusters`, `Neural DMA`, `Task DMA`, `External HDMA`, `Device HDMA`, `Device Sync`.
slice args(`debug.Slice Arguments`)에 `transfer: [":<N>Byte"]`, `comp_cycle: [...]`.
op 이름 형식 `<idx>_<family>_<opid>_<n>` (예: `12_linear_196_0`).

`scripts/trace_summary.py`가 phase별로 집계한다:
- 트랙별 busy_us, span 대비 %, union
- NE-only / DMA-only / NE|DMA overlap
- Task DMA 이동 바이트, NE comp_cycle 합
- 트랙별 상위 op family, Neural DMA 상위 linear op id (가중치 스트리밍 큰 층 식별)

## 서빙 엔진(vllm-rbln)에서 트레이스 회수

문제: `RBLN_PROFILER=1`이면 수집은 되지만 `.pb`는 `rebel._C.profiler.done()`에서
쓰인다. vLLM 서버는 이를 부르지 않고, mp executor worker는 `timeout=0`으로 종료되어
atexit/`worker.shutdown()` 훅으로 회수되지 않았다 (3회 실패).

동작한 방법: `scripts/profiler_flush_hook.py`를 `sitecustomize.py`라는 이름으로
PYTHONPATH 앞에 두면 `RBLN_PROFILER=1`인 모든 Python 프로세스에 daemon thread가 생겨
트리거 파일(`RBLN_PROFILER_TRIGGER`, 기본 `/traces/FLUSH`)을 폴링한다. 트리거가
생기면 `rebel`을 import한 프로세스가 `profiler.start(cwd) + profiler.done()`을 실행해
멀티스트림 `.pb` 1개를 쓴다.

```bash
mkdir -p /path/hooks && cp profiler_flush_hook.py /path/hooks/sitecustomize.py
# 엔진 컨테이너에 -e RBLN_PROFILER=1 -e PYTHONPATH=/hooks:$PYTHONPATH -v /path/hooks:/hooks:ro -v /path/traces:/traces
# 부하를 건 뒤:
touch /path/traces/FLUSH   # 각 프로세스가 FLUSH.<pid>.done 을 남김
```

서빙 트레이스의 "모듈" 번호는 그래프별(예: prefill, decoder 버킷, audio tower 버킷,
sampler 소형 그래프)이며 span 길이와 호출 수로 정체를 맞춘다.
