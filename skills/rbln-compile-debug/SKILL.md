---
name: rbln-compile-debug
description: >-
  Diagnose and fix rebel-compiler / optimum-rbln compile failures when porting a
  PyTorch model to Rebellions ATOM (RBLN NPU). Use on RBLNCompileError,
  "Graph Generation: [DEVICE_GRAPH_CONVERSION]", host tensor mismatch
  (mem_loc = "host"), librbln.so segfault / exit 139 during
  torch.compile(backend="rbln"), Dynamo graph break at Tensor.item(),
  "Global num_threads state changed while dynamo tracing",
  kvcache_block_size / prefill_chunk_size / kvcache_partition_len assertion
  errors, or when a compiled .rbln silently leaves a stage on the CPU.
  Korean triggers: 컴파일 실패, 컴파일 에러, unsupported op, 그래프 변환 실패.
---

# RBLN 컴파일 실패 진단

컴파일 실패 하나는 포팅 종료 조건이 아니다. 실패 그래프를 최소화하고, 정확히 어떤
op 또는 state transition이 문제인지 찍은 뒤, 의미를 보존하는 재작성으로 우회한다.
"blocked"는 최소 재현과 서로 다른 우회 시도 실패가 함께 있을 때만 선언한다.

## 적용 조건

- `rebel.compile_from_torch`, `torch.compile(backend="rbln")`, 또는 optimum-rbln
  `RBLN<Model>.from_model / from_pretrained(export=True)`가 예외나 crash로 끝났다.
- 컴파일은 됐지만 실행 시 일부 stage가 host(CPU)에서 도는 것으로 의심된다.

## 절차

### 1. 에러 원문을 잡고 분류한다

전체 traceback과 stderr를 저장한다. 첫 줄이 아니라 **첫 번째 RBLN 오류**를 본다.
분류표는 [references/error-catalog.md](references/error-catalog.md).

| 증상 | 분류 |
|---|---|
| `RBLNCompileError ... [DEVICE_GRAPH_CONVERSION]`, `tensor<...{mem_loc = "host"}>` vs device output | A. 그래프 안의 동적 host 연산 |
| Dynamo graph break warning (`Tensor.item()`, `tolist`, dynamic slicing) | A. 같은 원인, torch.compile 경로 |
| `librbln.so` segfault, exit 139, graph optimization 중 crash | B. autoregressive KV 계약을 torch.compile로 표현 |
| `kvcache_block_size`, `prefill_chunk_size % 64`, `kvcache_partition_len` assertion | C. optimum-rbln config 제약 |
| `Global num_threads state changed while dynamo tracing` | D. 컴파일 중 스레드 수 변경 |
| 특정 op 이름이 unsupported로 명시됨 | A 또는 E(대체 op 필요) |

### 2. 실패 그래프를 최소화한다

1. 모듈을 preprocessing / encoder(tower) / decoder step / cache update / head로 분리해
   각각 고정 shape로 컴파일한다. 성공하는 것과 실패하는 것을 표로 남긴다.
2. 실패 모듈에서 forward를 반으로 잘라 가며 첫 실패 op을 찾는다. strict 모드에서는
   silent fallback이 없으므로 실패 지점이 곧 원인이다.
3. 재현 스크립트는 가중치 없이(random init) 돌아가게 만든다. 컴파일러 이슈 보고에도
   그대로 쓸 수 있다.

### 3. 분류별 조치

**A. 동적 host 연산이 그래프에 들어갔다**
`ceil`, `tolist`, `split`, `pad_sequence`, `Tensor.item()`, 동적 position 계산,
그래프 내부 attention mask 생성이 대표적이다.
[references/op-rewrites.md](references/op-rewrites.md)의 매핑표로 재작성한다.
핵심 패턴은 **고정 shape에 대해 host에서 1회 계산 → 그래프에는 고정 tensor로 전달**.
재작성 모듈은 먼저 CPU에서 원본과 bit-exact(`max_abs == 0`)임을 확인한 뒤 컴파일한다.

**B. torch.compile로 decoder + KV를 올리려 했다**
custom op을 얹어도 안 된다. static-address KV, 공유 `CompileContext`, `Runtime` 소유
계약은 `rebel.compile_from_torch` 경로에서만 표현된다. `/rbln-skills:rbln-port`의
L1 레시피로 전환한다. `torch.compile(backend="rbln")`은 fixed-shape stateless
모듈(encoder, audio tower, decode-step lm_head)에만 쓴다.

**C. optimum-rbln config 제약**
[references/constraints.md](references/constraints.md)의 표대로 값을 맞춘다.
자주 걸리는 것: eager attention은 `kvcache_block_size == max_seq_len`,
`prefill_chunk_size`는 64의 배수(32는 optimum 체크를 풀어도 컴파일러가 거부),
flash attention은 `kvcache_partition_len` 하한 때문에 짧은 컨텍스트에서 불가.

**D. 스레드 수 변경**
컴파일 프로세스의 `RBLN_NUM_THREADS`와 `torch.get_num_threads()`가 tracing 중 바뀌면
실패한다. 컴파일 전에 둘을 같은 값으로 고정하고, 컴파일 중 `torch.set_num_threads`를
호출하는 코드(벤치마크 하네스 포함)를 제거한다.

**E. 지원되지 않는 op**
1. `import optimum.rbln.ops` 후 `torch.ops.rbln_custom_ops`에 대체 op이 있는지 본다
   (`paged_causal_attn_decode/prefill`, `rbln_cache_update`, flash/moe/linear 변형).
2. 설치된 optimum-rbln의 가장 가까운 `<model>_architecture.py`와 `decoderonly/`에서
   같은 문제를 어떻게 풀었는지 찾는다.
3. 없으면 static buffer + tensor masking + gather/scatter 조합으로 같은 의미를 만든다.

### 4. 컴파일 성공 뒤에 확인할 것

컴파일 성공은 끝이 아니다.

- 실제 device 배치: `rbln-smi`에 프로세스 PID가 해당 device 행에 보이는지
  (`/rbln-skills:rbln-env-doctor`의 probe).
- 반복 호출: decoder는 최소 N step 반복해 KV가 유지되는지, runtime을 함수 안에서
  매번 만들지 않는지.
- 정확성: `/rbln-skills:rbln-precision-check`로 CPU fp32 대비 parity.

## 완료 조건

다음이 모두 참이면 끝난다.

1. 대상 모듈이 고정 shape로 컴파일되어 `.rbln` 아티팩트가 생겼다.
2. 재작성한 모듈이 CPU에서 원본과 수치 동일(또는 문서화된 허용 오차)이다.
3. 실행 시 device 배치가 증명됐고, stateful 모듈은 반복 호출에서 출력이 유지된다.
4. 우회하지 못한 op이 있다면 최소 재현 + 시도한 대안 + 다음 실험이 기록됐다.

## 검증 환경

ATOM-Max(RBLN-CA25), rebel-compiler 0.10.5.dev143, optimum-rbln 0.10.4
(배치-1 경로); rebel-compiler / optimum-rbln 0.11.0.post1 (서빙 경로 제약 C 일부).
버전별 세부는 [references/constraints.md](references/constraints.md).
