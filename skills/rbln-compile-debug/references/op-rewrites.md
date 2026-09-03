# compiler-hostile op → 재작성 매핑

원칙: 고정 shape에 대해 host에서 1회 계산하고 그래프에는 고정 tensor를 넘긴다.
재작성 모듈은 컴파일 전에 CPU에서 원본과 `max_abs == 0`(또는 문서화된 오차)을 확인한다.

| 원본 패턴 | 왜 막히나 | 재작성 | 실제 사례 |
|---|---|---|---|
| `ceil`, `tolist`, `split`, `pad_sequence`로 chunk 길이 계산 | host shape tensor가 그래프에 섞임 | 고정 feature length에서 chunk 길이·`cu_seqlens`를 `__init__`에서 계산해 buffer로 등록, forward는 고정 slice + pad | Qwen3-ASR `AudioTowerStaticChunk` (CPU bit-exact) |
| `Tensor.item()`으로 길이 추출 | graph break | 길이를 생성자 인자로 받아 Python int 상수로 | Qwen3-ASR full thinker probe |
| `index_copy_`로 KV write | in-place 동적 인덱스 | `torch.ops.rbln_custom_ops.rbln_cache_update(cache, new, batch_idx, axis)` | Whisper cross-KV |
| causal self-attention + KV write | 동적 mask, 동적 인덱스 | `torch.ops.rbln_custom_ops.paged_causal_attn_decode(q,k,v,kcache,vcache,seq,scale,block_table,block_size,mask=None)` | Whisper decoder |
| 동적 position 계산 (`arange(past_len, past_len+1)`) | 런타임 정수 연산 | `embed_positions.weight[position_id]` 직접 indexing, position_id는 입력 tensor | Whisper decoder |
| cross-attention K/V를 매 step 재계산 | encoder 출력 의존 | encoder 직후 cross-KV를 한 번 계산해 static buffer에 write, decoder는 plain matmul | Whisper |
| `torch.view_as_complex` / `view_as_real` RoPE | complex dtype 미지원 | host에서 cos/sin precompute, 그래프에서 interleaved pair를 real rotation | Z-Image S3-DiT (3축 freqs, head_dim 128 = 64 pair) |
| per-item Python list 처리, patchify/unpatchify reshape | 동적 shape | 고정 prompt/해상도에서 shape 상수 → host prep 1회 | Z-Image |
| 그래프 내부 attention mask 생성 | 동적 boolean 연산 | 단일 배치·고정 길이면 all-ones로 제거, 아니면 precomputed additive mask 입력 | Z-Image, Nemotron |
| float mask를 `masked_fill_(mask.logical_not(), -inf)` | 방향 오류(upstream eager 버그) | additive mask를 직접 만들어 `softmax(qk*scale + rel + mask) @ v` | Nemotron FastConformer |
| precision-sensitive 소형 모듈 (timestep embedder 등) | bf16 downcast에 취약 | host fp32에서 계산해 그래프 입력으로 주입 | Z-Image `t_embedder` |
| prefill lm_head `[1,L,H]` vs decode `[1,1,H]` | 두 shape | decode-step lm_head만 별도 fixed-shape 컴파일 (`[1,1,H]→[1,1,V]`) | Qwen3-ASR partial hybrid |
| 배치 b, query K+1 검증 그래프 (speculative decoding) | decode op은 query 1, prefill op은 batch 1 | linear는 배치, attention은 행별 prefill op 루프; 같은 CompileContext에 3번째 그래프 추가 | Qwen3-ASR verify graph |
| host sampler로 `[b,1,V]` float32 logits 전송 | 전송량이 배치에 비례 | 그래프 끝에서 `argmax(keepdim)` → int32 (greedy 전용) | Qwen3-ASR fuse_greedy_argmax |

## 분할 원칙

- Python control flow, tokenizer, logits processor, generate loop는 host orchestration.
- heavy tensor component(encoder, prefill, decode step, head)는 ATOM.
- 실패한 ATOM stage를 "계획된 CPU"로 위장하지 않는다. `fallback`으로 기록한다.
