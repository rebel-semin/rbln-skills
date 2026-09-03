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

# ATOM 프로파일링

두 층으로 잰다. 1층은 프로파일러를 끄고 stage wall time, 2층은 프로파일러를 켜고 커널
트레이스. 2층의 wall time은 오버헤드(약 2배)가 실려 있어 시간 수치로 쓰지 않고 트랙
점유율과 op 분포만 읽는다.

## 적용 조건

- e2e latency는 있는데 어느 stage가 지배하는지 모른다.
- decode step / prefill / encoder 중 무엇이 compute-bound인지 DMA-bound인지 알아야
  최적화 레버를 고를 수 있다.
- 서빙 엔진(vllm-rbln) 안의 device 시간 구성을 봐야 한다.

## 절차

### 1층. stage wall time (profiler OFF)

1. host 전처리, 각 ATOM 호출, host 후처리를 `perf_counter`로 감싼다. warmup 1회 이상
   제외, 5회 이상 반복해 p50/p95.
2. optimum 경로는 두 깊이로 훅을 건다:
   - `RBLNRuntimeModel.forward` (host prep + device 호출)
   - 내부 `runtime_model.runtime` (`rebel.Runtime` 호출 = device + 전송)
   차이가 optimum의 step별 host 작업이다. 훅 코드는
   [references/profiler-mechanics.md](references/profiler-mechanics.md).
3. generate 루프의 host 몫은 연속 decode 호출의 시작 시각 차이에서 device 호출 시간을
   뺀 gap 합으로 잰다.
4. 표: stage, p50, 전체 대비 %. decode는 step 분포(p50/p95/max)도.

**첫 판정**: host 몫(gap + optimum prep)이 몇 %인가. 2% 수준이면 루프 최적화는 의미
없고 device 시간이 본체다.

### 2층. 커널 트레이스 (profiler ON)

1. 짧은 workload(예: 16 token)로 `RBLN_PROFILER=1` + `rebel.profiler.profile(output_dir)`
   컨텍스트에서 1회 실행. optimum은 `rbln_activate_profiler=True`로 런타임 생성.
   프로파일 전에 unprofiled warmup 1회.
2. 출력은 `rbln_<date>_<time>_<seq>.pb`. `seq`는 프로파일러가 호출 순서로 매기므로
   어느 인덱스가 어느 phase인지 실행 순서로 매핑한다 (warmup 호출도 인덱스를 소비).
3. `${CLAUDE_SKILL_DIR}/scripts/trace_summary.py --trace-dir <dir> --prefix rbln_<date>_<time> --phase prefill=19 --phase decode=20-34`
   로 phase별 트랙 busy, NE/DMA overlap, 상위 op family, Task DMA 이동 바이트를 집계한다.
   `perfetto` 패키지 필요 (첫 실행 시 trace_processor shell을 curl로 내려받음).
4. 서빙 엔진은 `.pb`가 `profiler.done()`에서만 쓰이고 worker가 그걸 부르지 않는다.
   `${CLAUDE_SKILL_DIR}/scripts/profiler_flush_hook.py`를 `sitecustomize.py`로
   PYTHONPATH에 넣고 트리거 파일을 만들어 flush한다. 상세는 mechanics 문서.

### 3. 해석

[references/interpretation.md](references/interpretation.md)의 규칙. 요약:

| 관측 | 판정 | 레버 |
|---|---|---|
| Neural Engine busy ≥ 90%, DMA 낮음 | compute-bound | 저정밀 compute, 시퀀스/패딩 축소(prefill chunk) |
| Neural DMA busy ≥ 90%, NE `comp_cycle` 작음, `linear` family가 DMA 지배 | weight-DMA-bound | 저정밀 weight, speculative decoding(K+1 검증이 1 token과 비슷한 비용), lm_head 축소, 배치로 가중치 스트리밍 공유 |
| Task DMA에 큰 바이트 이동 | activation/KV 전송 | KV 길이(max_seq_len) 축소, logits 전송 축소(argmax fusion) |
| 짧은 프롬프트인데 prefill span이 긴 프롬프트와 같음 | prefill 패딩 | `prefill_chunk_size`를 프롬프트를 한 패스로 덮는 최소값으로 |
| 배치 b가 버킷 경계를 넘을 때 step 점프 | decoder batch bucket 패딩 | 운영 배치를 버킷 경계에 맞추거나 버킷 추가 컴파일 |

### 4. 레버 선택 전 확인

- 그 stage가 e2e의 몇 %인가. 7%짜리 stage를 2배 빨리 해도 3.5%다.
- 레버가 정확성 게이트를 유지하는가 (`/rbln-skills:rbln-precision-check`).
- 서빙이면 단건 지연과 동시 처리량이 반대로 움직일 수 있다 (speculative decoding은
  단건 +17%, 동시성 N≥4에서 −12~28%).

## 완료 조건

1. stage 표(p50, %)와 host 몫이 있다.
2. 지배 stage에 대해 compute-bound / DMA-bound / 패딩 판정과 근거 수치(트랙 busy,
   상위 op)가 있다.
3. 다음 실험 하나가 기대 이득 상한과 함께 적혀 있다 (예: "lm_head가 step의 17% →
   저정밀화 상한 ~8%").

## 검증 환경

ATOM-Max(RBLN-CA25), rebel-compiler 0.10.5.dev143 (`rebel/compiled_model.py`의
`RBLN_PROFILER`, `rebel/profiler.py`의 `profile()`), optimum-rbln 0.10.4
(`modeling_decoderonly.py`의 `rbln_activate_profiler`), 서빙은 vllm-rbln 0.11.0.
