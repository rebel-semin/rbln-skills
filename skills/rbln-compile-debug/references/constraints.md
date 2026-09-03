# 컴파일 제약과 knob (버전 고정)

## 디바이스 세대

| 세대 | 카드 | 확인 사항 |
|---|---|---|
| ATOM (base) | RBLN-CA22 | 공식 base 제품. 이 표의 실측은 CA25 기준이며 CA22에서 재확인 필요 |
| ATOM-Max | RBLN-CA25 | 카드당 논리 device 4개, 논리 device당 약 15.7 GiB. 아래 실측의 기준 |

## 불변 조건 (autoregressive decoder)

1. static shape: compile 전에 tensor layout과 최대 길이 결정
2. static-address KV: `CompileContext.mark_static_address(tensor)`를 compile에
   넘기는 **바로 그** example tensor에 적용
3. 공유 `CompileContext`: encoder/decoder(또는 tower/text stack)가 같은 context
4. `rebel.Runtime` 소유: persistent buffer가 호출 사이에 살아 있어야 함

## optimum-rbln decoder-only config (0.10.4 기준 확인)

| knob | 제약 / 관측 |
|---|---|
| `attn_impl="eager"` | `kvcache_block_size == max_seq_len` 필수. 실제 길이와 무관하게 컴파일된 KV 길이 × 디코더 배치 행을 매 스텝 읽음 |
| `attn_impl="flash_attn"` | `kvcache_partition_len` 4096~32768 강제 (0.11.0.post1에서 확인). 짧은 컨텍스트 불가 |
| `prefill_chunk_size` | 64의 배수. 기본 128. `seq_len`과 같게 두면 짧은 프롬프트도 전체 길이를 계산(패딩 비용). 규칙: 프롬프트를 한 패스로 덮는 가장 작은 값 |
| `kvcache_num_blocks` | eager + 배치 1이면 1 |
| `use_inputs_embeds=True` | 외부(audio 등) embedding을 주입할 때. shim 패턴의 핵심 |
| `use_attention_mask`, `use_position_ids` | 모델 semantics에 맞게. ASR shim은 mask True, position_ids False |
| `dtype="float32"` | 가중치 저장 dtype. 컴파일러 내부 compute는 bf16 downcast pass가 적용될 수 있음 (rbln-precision-check 참조) |
| `decoder_batch_sizes` (서빙) | 실행 배치는 상한 버킷으로 패딩. 사다리 1/2/4/8/16/32면 9행이 16행 비용 |
| `batch_size`, `max_seq_len`, `device` | 컴파일 시 고정. `device`는 container-visible id |

## 컴파일 surface 선택

| surface | 쓰는 곳 | 안 되는 것 |
|---|---|---|
| `RBLN<Model>.from_pretrained(export=True)` | optimum이 전체 지원하는 모델 | — |
| `RBLN<Model>.from_model(shim, rbln_config=...)` | 서브스택이 기존 클래스와 맞을 때 | 원본 모듈과 semantics가 다르면 shim으로도 불가 |
| `torch.compile(backend="rbln", dynamic=False, options={"mode":"strict"})` | fixed-shape stateless 모듈 | autoregressive KV, 동적 host 연산 |
| `rebel.compile_from_torch(module, input_info, example_inputs, compile_context)` | 그 외 전부. optimum 내부도 이것을 사용 | — |

`torch.compile`과 `compile_from_torch`는 같은 RBLN lowering을 쓴다. 차이는 Dynamo
adapter를 거치는지와 input/context/runtime 소유권이다.

## 환경변수 (관측)

| 변수 | 효과 |
|---|---|
| `RBLN_NUM_THREADS` | 런타임/컴파일 스레드. 컴파일 중 Torch 스레드 수와 같아야 함 |
| `RBLN_PROFILER=1` | 커널 트레이스 수집 (rbln-profile 참조) |
| `RBLN_DEVICES` | 서빙 컨테이너에서 device 선택 (container-visible id) |
| `RBLN_DEVICE_MAP` | 설치된 SDK(0.10.5.dev143)에서 Runtime device 선택으로 **소비되지 않음**. `Runtime(device=N)` 또는 `rbln_device` 사용 |
| `DISABLE_REBEL_DATA_TYPE_CONVERSION_PASS=1`, `TRITON_F32_DEFAULT=ieee` | `compile_from_torch` 결과에 **효과 없음** (bf16 downcast 유지, 0.10.5.dev143) |
