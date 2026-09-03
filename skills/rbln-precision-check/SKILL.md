---
name: rbln-precision-check
description: >-
  Verify that a model compiled for Rebellions ATOM (RBLN NPU) matches its CPU
  fp32 reference and localize precision drift before any speedup is quoted.
  Covers the rebel-compiler default bf16 downcast (add_convert_type_to_bf16),
  layer-by-layer error compounding, choosing token parity vs WER / PSNR /
  logit error as the gate, and near-tie argmax flips between recompiled
  graphs. Use when "ATOM 출력이 CPU와 다르다", transcripts differ, token parity
  fails, hidden-state error looks large, or a correctness gate must be
  designed for a new task.
---

# ATOM 정확성 검증

속도 수치를 만들기 전에 정확성을 먼저 잠근다. 게이트를 통과하지 못한 latency는 headline이
아니다. "lossless"가 아니라 "이 입력 집합에서 CPU fp32 대비 no regression"으로 표현한다.

## 적용 조건

- ATOM 출력을 CPU fp32와 비교해야 한다 (포팅 직후, variant 변경 후, 재컴파일 후).
- 출력이 다른데 어디서 갈라지는지 몰라 stage별로 localize해야 한다.

## 절차

### 1. 참조를 고정한다

- CPU fp32 eager, 같은 전처리·prompt·generation option·seed. greedy면 `num_beams=1`.
- 참조 실행의 스레드 수를 **ATOM 실행 전에** 기록한다 (RBLN 런타임이 Torch 전역
  스레드 수를 바꾼다).
- 입력 fixture의 SHA256과 모델 revision을 적는다.
- 참조가 다른 라이브러리 버전을 요구하면 격리 env에서 만들고 파일로 가져온다.
  ATOM 컨테이너의 pin은 건드리지 않는다.

### 2. task에 맞는 metric을 고른다

[references/metrics-by-task.md](references/metrics-by-task.md).

| task | 1차 게이트 | 보조 |
|---|---|---|
| greedy ASR / LLM | token parity (exact), text identical | normalized WER vs ground truth |
| 스트리밍 ASR (RNN-T 등, argmax가 견고) | WER vs CPU fp32 ≤ 임계 (사용자 확인) | token 차이 목록 |
| diffusion | 디코드 이미지 PSNR ≥ 임계, 같은 seed latent 공유 | latent cosine, LPIPS, CLIP delta |
| vision classification | top-1 일치 | logit rel err |

부등식 임계(≤, ≥)는 headline 자격을 결정하므로 사용자가 명시적으로 확인한 값만 쓴다.
token parity 정의: `matched / max(len_candidate, len_reference)` (길이 차이는 mismatch,
빈 출력 방지용 `min_total: 1`).

### 3. e2e 비교

통과하면 6단계로. 실패하면 4단계.

### 4. stage probe로 localize

1. 모듈을 stage로 나눠(subsampling → layer 1..N → pooler/head) 같은 입력으로 ATOM과
   CPU fp32 중간 출력을 덤프한다.
2. stage별 `max_abs`, `mean_rel`을 표로. 오차가 층을 지날수록 커지면 **compiler-default
   bf16 downcast 누적**이다 ([references/bf16-behavior.md](references/bf16-behavior.md)).
3. CPU에서 같은 모듈을 bf16과 fp16으로 시뮬레이션해 ATOM 오차와 비교한다. ATOM 오차가
   bf16 시뮬레이션과 같은 자릿수면 dtype 문제, 훨씬 크면 semantics 문제(재작성 버그,
   mask 방향, position).
4. 첫 번째로 오차가 튀는 stage에서 멈춘다. 그 stage의 재작성을 원본과 CPU에서 비교한다
   (목표 `max_abs == 0`).

### 5. 완화

| 원인 | 조치 |
|---|---|
| bf16 누적이지만 argmax/greedy 견고 | 그대로 두고 task metric(WER 등)으로 게이트. 오차 표를 기록 |
| 소형 precision-sensitive 모듈 (timestep embedder, norm scale 등) | host fp32로 빼서 그래프 입력으로 주입 |
| 재작성 semantics 오류 | CPU에서 원본 대비 bit-exact가 될 때까지 재작성 수정 |
| 재컴파일된 두 그래프 간 near-tie argmax flip (예: decode 그래프 vs verify 그래프) | 수치 차이 수준(top-2 margin < 0.1)이면 부기 오류가 아님. 빈도와 margin을 기록하고 transcript 영향으로 판단 |
| fp32 compute 강제 시도 | `DISABLE_REBEL_DATA_TYPE_CONVERSION_PASS=1`, `TRITON_F32_DEFAULT=ieee`는 `compile_from_torch`에 효과 없음(0.10.5.dev143). 미검증 대안: optimum `RBLNCompileConfig` fp32 경로, op별 fp32 annotation |

### 6. 주장 문구

- "tested N samples에서 CPU fp32 greedy와 token 단위 동일" 또는 "WER x% vs y%,
  표본오차 내".
- 한두 샘플의 parity는 실행 경로가 같은 출력을 냈다는 뜻이며 dataset accuracy 보장이
  아니다. 다국어·잡음·long-form·timestamp는 별도 평가.
- comparator의 precision을 명시한다. bf16 변환 후의 CPU 측정을 fp32 기준선으로
  쓰면 결과 하나에 두 기준선이 섞인다.

## 완료 조건

1. 선택한 metric으로 ATOM vs CPU fp32 게이트가 `passed`.
2. 실패했던 경우 첫 발산 stage와 원인 분류(bf16 / semantics / near-tie)가 기록됐다.
3. 게이트 정의, 임계값, 참조 조건(스레드, seed, revision, fixture hash)이 결과에 남았다.

## 검증 환경

ATOM-Max(RBLN-CA25), rebel-compiler 0.10.5.dev143, optimum-rbln 0.10.4. 관측 수치는
[references/bf16-behavior.md](references/bf16-behavior.md).
