# compiler-default 정밀도 관측 (rebel-compiler 0.10.5.dev143, ATOM-Max)

## 1. 컴파일러가 compute를 bf16으로 내린다

`compile_from_torch` 경로에 `add_convert_type_to_bf16` pass가 적용된다. 공개 Python
API와 캐시 파일은 내부 arithmetic dtype을 노출하지 않으므로 오차 패턴으로 추론했다.

Qwen3-ASR audio tower (dummy shape, CPU fp32 대비 hidden state):

| 비교 | mean_rel | max_abs |
|---|---:|---:|
| CPU bf16 시뮬레이션 | 0.862% | 1.30e-3 |
| CPU fp16 시뮬레이션 | 0.103% | 1.65e-4 |
| **NPU** | **1.00%** | **1.39e-3** |

→ NPU 오차는 bf16 시뮬레이션과 같은 자릿수. fp16/fp32가 아니다.

## 2. 깊은 스택에서는 누적된다

Nemotron FastConformer (24 layer, compile_from_torch, custom op 없음):

| stage | rel err |
|---|---:|
| 초기 층 | 0.6% |
| 중간 | 3% → 11% |
| 후반 | 23% |
| pooler | 87% |

그래도 greedy RNN-T argmax는 견고해 WER 0.0488 vs CPU fp32 (utterance 경계 token 2개
차이: "Mr."→"Mister", 끝 "and" 누락).

## 3. fp32 강제 시도 (효과 없음)

| knob | 결과 |
|---|---|
| `DISABLE_REBEL_DATA_TYPE_CONVERSION_PASS=1` | pooler 오차 bit-identical (변화 없음) |
| `TRITON_F32_DEFAULT=ieee` | 변화 없음 (triton 캐시 정리 후 shell 레벨에서 확인) |

미검증 대안: optimum `RBLNCompileConfig`의 fp32 경로, op별 fp32 annotation.

## 4. optimum decoder-only (`dtype="float32"`) 경로

Qwen3-ASR text stack은 192/192 token exact를 3회 이상 재현. 커널 트레이스에서 decode
step이 fp32 가중치 스트리밍(step당 약 6.9 GB)으로 보여 이 경로의 가중치는 fp32로
유지되는 것으로 추정. 아티팩트 내부 dtype 직접 확인은 미완.

## 5. 재컴파일된 그래프 간 near-tie flip

같은 가중치를 다른 query_length로 컴파일한 두 그래프(decode 1-token vs verify K+1)의
logits 최대 차이 0.23, top-1 margin 최소 0.19. teacher-forced 190/190 argmax 일치했지만
서빙 40클립 중 2클립에서 transcript 차이(1,420 위치 중 argmax 불일치 8, top-2 margin
≤ 0.09). 재컴파일 그래프 간 수치 차이 수준으로 부기 오류가 아님. 이런 차이는 exact
parity 대신 margin 통계와 함께 보고한다.

## 6. comparator precision 사고

DiT bench에서 comparator를 bf16 변환 **후에** 만들어 "CPU fp32" stage 수치가 실제로는
bf16 CPU였다. 한 결과에 fp32 e2e baseline과 bf16 stage baseline이 섞였다. comparator는
변환 전에 `compute_dtype=float32`로 만들고 detail key에 precision을 명시한다.
