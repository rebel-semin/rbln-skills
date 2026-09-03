# 관측된 에러 카탈로그

실제 ATOM-Max 포팅에서 나온 에러 문자열과 확인된 원인. 새 사례는 아래 표에 추가.

| 에러 / 증상 | 어디서 | 확인된 원인 | 해결 |
|---|---|---|---|
| `RBLNCompileError: Graph Generation: [DEVICE_GRAPH_CONVERSION]` | `torch.compile(backend="rbln", options={"mode":"strict"})` audio tower, text prefill | forward 안의 dynamic host chunking(`ceil`, `tolist`, `split`, `pad_sequence`)이 host shape tensor를 만들어 device 출력 타입과 불일치 | 고정 feature length 기준으로 chunk 메타데이터를 사전 계산한 static wrapper |
| `tensor<6xi64, {mem_loc = "host"}>` vs expected device output host tensor | 위와 동일 | 위와 동일 | 위와 동일 |
| Dynamo graph break warning at `Tensor.item()` | full thinker(use_cache=True) probe | audio feature 길이 slicing이 `.item()` 사용 | host에서 길이 고정, 그래프에는 정수 상수로 |
| `librbln.so` segfault, exit code 139, graph optimization 중 | `torch.compile` + optimum WhisperWrapper + `ctx.mark_static_address` + `torch._dynamo.mark_static_address` | `index_copy_`/`diff` 컴파일 에러는 custom op으로 사라졌지만, torch.compile 경로가 static KV 공유 계약을 backend graph input에 묶지 못함 | `rebel.compile_from_torch` + 공유 `CompileContext` + `Runtime` 소유로 전환 |
| eager attention에서 `kvcache_block_size != max_seq_len` 거부 | `RBLNQwen3ForCausalLMConfig` | optimum-rbln 요구사항 | 둘을 같은 값으로 (예: 1024/1024) |
| `prefill_chunk_size % 64 != 0` 거부 | `configuration_decoderonly.py` | optimum 체크. 완화해도 컴파일러가 32를 거부 | 64, 128, 256 중 선택 |
| `kvcache_partition_len` 4096~32768 강제 | `attn_impl="flash_attn"` (optimum-rbln 0.11.0.post1) | flash attention 파티션 하한 | 1024 컨텍스트에서는 eager 유지; KV 읽기 절감은 `max_seq_len` 축소로 |
| `Global num_threads state changed while dynamo tracing` | audio tower `torch.compile` 중 | 컴파일 프로세스의 `RBLN_NUM_THREADS`와 Torch 스레드 수 불일치 | `RBLN_NUM_THREADS == torch.get_num_threads()` 고정 |
| 3D position id로 plain HF `Qwen3ForCausalLM` 실행 실패 / 2D fallback logits 불일치 | ASR text 가중치를 plain Qwen3에 복사 | 모델 고유 position/rotary semantics | 원본 text 모듈을 `PreTrainedModel` shim으로 감싸 optimum 클래스에 전달 |
| ATOM 실행 후 `torch.get_num_threads()`가 바뀜 (32 → 64) | 벤치마크 하네스 | RBLN 런타임이 Torch 전역 스레드 설정을 변경 | CPU baseline 스레드 수는 ATOM 실행 전에 캡처 |
| optimum text runtime이 HF output object 대신 Tensor 반환 | `RBLNQwen3ForCausalLM` decode | 반환 타입이 경로에 따라 다름 | 두 타입 모두 처리 |
| `device_count = 0` | 컨테이너 | `/dev/rsd0` 미마운트 | `--device /dev/rsd0` 추가 (rbln-env-doctor) |
