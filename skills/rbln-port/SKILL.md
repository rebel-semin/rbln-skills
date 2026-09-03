---
name: rbln-port
description: >-
  Port a PyTorch / Hugging Face model to Rebellions ATOM (RBLN NPU) by the
  cheapest working path: an official optimum-rbln RBLN<Model> class, a
  PreTrainedModel shim onto an existing RBLN class (e.g.
  RBLNQwen3ForCausalLM.from_model(..., use_inputs_embeds=True) for a speech-LM
  text stack), or a hand-written L1 wrapper compiled with
  rebel.compile_from_torch + one shared CompileContext + static-address KV +
  an owned rebel.Runtime. Use for "ATOM에 올려", "RBLN 포팅", "optimum-rbln에
  없는 모델", encoder-decoder ASR, decoder-only LLM, audio tower, DiT / diffusion
  denoiser, conformer / RNN-T, or when deciding what to offload first.
---

# ATOM 포팅 절차

가장 싼 경로부터 확인하고, CPU stage breakdown으로 무엇을 올릴지 정한 뒤, 정확성을
먼저 맞추고 속도를 잰다. 경로 분류는 시작점이지 결과 예측이 아니다.

## 적용 조건

- 새 모델을 ATOM에서 돌려야 한다, 또는 기존 포팅에서 CPU에 남은 stage를 더 올려야 한다.
- 컴파일 실패 자체를 잡는 중이면 `/rbln-skills:rbln-compile-debug`가 먼저다.

## 절차

### 0. 조사 (질문하기 전에)

1. 설치된 optimum-rbln에서 지원 모델을 확인한다:
   `python -c "import optimum.rbln as o; print([n for n in dir(o) if n.startswith('RBLN')])"`
   와 `optimum/rbln/transformers/models/` 디렉터리. `/latest/` 문서가 아니라 설치본이 기준.
2. 모델 아키텍처를 서브스택으로 분해한다: preprocessing, encoder/tower, text decoder,
   head, postprocessing. 각 서브스택이 어느 optimum 클래스와 구조가 같은지 적는다.
3. CPU fp32 eager로 **stage breakdown**을 잰다. 시간이 큰 stage부터 올린다. 작은
   encoder를 10배 빨리 해도 e2e는 거의 안 줄어든다 (사례: audio tower + lm_head만
   올린 hybrid는 1.2x, text/KV decode를 올리자 15x).

### 1. 경로 분류

[references/decision-tree.md](references/decision-tree.md)의 순서대로.

| 경로 | 조건 | 다음 |
|---|---|---|
| 1. 공식 클래스 | `RBLN<Model>`이 전체 모델을 지원 | `from_pretrained(export=True)`로 export → 바로 5단계 |
| 2. shim | 서브스택(text decoder, vision encoder)이 기존 클래스 구조와 일치 | [references/shim-pattern.md](references/shim-pattern.md) |
| 3. L1 손 작성 | 맞는 클래스가 없음 (새 attention, RNN-T, DiT, conformer) | [references/l1-recipe.md](references/l1-recipe.md) |

경로 3은 흔하며 중단 조건이 아니다. 예상 작업량이나 세션 수는 기술적 blocker가 아니다.

### 2. 경로별 구현

**경로 2 (shim)**: 원본 모듈(`thinker.model`, `thinker.lm_head` 등)을 그대로 보존하는
`PreTrainedModel` 서브클래스를 만들고, config를 eager attention으로 강제한 뒤
`RBLN<Base>ForCausalLM.from_model(shim, rbln_config=...)`. 가중치를 plain HF 클래스에
복사하는 shortcut은 position/rotary semantics가 다르면 logits가 틀어진다. 외부
embedding은 `use_inputs_embeds=True`로 주입한다.

**경로 3 (L1)**: 재사용할 것과 새로 쓸 것을 분리한다.

| 레이어 | 내용 | 재사용 |
|---|---|---|
| L1 | decoder/attention/position/KV를 static-friendly로 재작성 | 모델별 작성 |
| L2 | `compile_from_torch`, 공유 `CompileContext`, static-address KV, `Runtime` 소유 | 레시피 그대로 |
| L3 | `import optimum.rbln.ops`, runtime adapter, HF `generate` 연결 | optimum/SDK |

stateless fixed-shape 모듈(encoder, audio tower, DiT, decode-step lm_head)은
`torch.compile(backend="rbln", dynamic=False)` 또는 `compile_from_torch` 둘 다 가능.
stateful(KV) 모듈은 `compile_from_torch`만.

### 3. 정확성 사다리 (속도 전에)

1. 재작성 모듈 vs 원본: CPU에서 `max_abs` (목표 0).
2. 컴포넌트 parity: ATOM 출력 vs CPU fp32 (hidden state 상대 오차, 사례별 기준은
   `/rbln-skills:rbln-precision-check`).
3. N-step token parity: 같은 encoder 입력으로 decoder 토큰이 N step 동안 일치.
4. full-clip/full-prompt parity: stride, logits processor, timestamp, stop condition을
   포함한 **원래 generate orchestration**에 연결해서. 모델 텐서가 맞아도 orchestration이
   다르면 chunk 경계 단어가 깨진 사례가 있다.

### 4. 실행 위치를 기록한다

timing 안의 모든 stage에 대해 backend와 CPU 역할을 적는다:
`atom` / `cpu: host-orchestration`(전처리, tokenizer, generate loop) /
`cpu: planned-hybrid`(이번 범위에서 의도적으로 남김) / `cpu: fallback`(올리려 했지만
실패). fallback을 planned로 위장하지 않는다. ATOM stage마다 배치 증거(`rbln-smi` PID,
`Runtime(device=N)`)를 남긴다.

### 5. 측정과 표현

- CPU baseline은 fp32 eager, 스레드 스윕으로 최적값(과거 ASR 사례 32 threads; 배치-1
  autoregressive decode는 스레드가 많으면 느려짐). 스레드 수는 ATOM 실행 **전에** 기록.
- p50과 p95, warmup 횟수, run 수, load average, 컴파일 시간과 아티팩트 크기.
- 배속은 항상 "vs CPU fp32 eager"로 라벨. GPU 비교는 같은 workload·precision·timing
  scope에서 별도 측정한 것만.
- 부분 offload 마이크로벤치 배속을 e2e 배속처럼 쓰지 않는다.

## 완료 조건

1. 요청된 e2e 경로에 실제 ATOM stage가 최소 하나 있고 배치 증거가 있다.
2. 정확성 사다리 4단계를 통과했다(또는 task에 맞는 metric 게이트).
3. execution map, CPU baseline, p50/p95, 버전(rebel-compiler, optimum-rbln, torch,
   transformers)이 기록됐다.
4. CPU에 남은 stage가 있으면 planned-hybrid인지 fallback인지 명시되고 다음 병목이
   적혀 있다.

## 검증 환경

ATOM-Max(RBLN-CA25), rebel-compiler 0.10.5.dev143, optimum-rbln 0.10.4,
torch 2.10.0+cpu, transformers 4.57.6. 사례별 수치와 교훈은
[references/case-studies.md](references/case-studies.md).
