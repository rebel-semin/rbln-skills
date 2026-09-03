# Compiler-hostile op → rewrite mapping

Principle: compute once on the host for a fixed shape and pass constant tensors
into the graph. Before compiling, confirm the rewritten module matches the
original on CPU (`max_abs == 0`, or a documented tolerance).

| Original pattern | Why it breaks | Rewrite | Real case |
|---|---|---|---|
| `ceil`, `tolist`, `split`, `pad_sequence` to derive chunk lengths | host shape tensors end up inside the graph | compute chunk lengths and `cu_seqlens` in `__init__`, register them as buffers, keep `forward` to fixed slices plus pad | Qwen3-ASR `AudioTowerStaticChunk` (CPU bit-exact) |
| `Tensor.item()` to read a length | graph break | take the length as a constructor argument and use it as a Python int | Qwen3-ASR full-thinker probe |
| `index_copy_` for a KV write | in-place dynamic indexing | `torch.ops.rbln_custom_ops.rbln_cache_update(cache, new, batch_idx, axis)` | Whisper cross-KV |
| causal self-attention plus a KV write | dynamic mask, dynamic indexing | `torch.ops.rbln_custom_ops.paged_causal_attn_decode(q, k, v, kcache, vcache, seq, scale, block_table, block_size, mask=None)` | Whisper decoder |
| runtime position arithmetic (`arange(past_len, past_len + 1)`) | integer math at runtime | index `embed_positions.weight[position_id]` directly, with `position_id` as a graph input | Whisper decoder |
| recomputing cross-attention K/V every step | depends on encoder output | compute cross-KV once after the encoder into a static buffer; the decoder does a plain matmul | Whisper |
| `torch.view_as_complex` / `view_as_real` RoPE | complex dtype unsupported | precompute cos/sin on the host, rotate interleaved pairs as real math in the graph | Z-Image S3-DiT (3 axes, head_dim 128 = 64 pairs) |
| per-item Python list handling, patchify / unpatchify reshapes | dynamic shapes | shapes are constant for a fixed prompt and resolution, so compute them once in host prep | Z-Image |
| building the attention mask inside the graph | dynamic boolean work | drop it when a single batch at fixed length makes it all-ones; otherwise pass a precomputed additive mask | Z-Image, Nemotron |
| `masked_fill_(mask.logical_not(), -inf)` on a float mask | wrong direction (upstream eager bug) | build the additive mask yourself: `softmax(qk * scale + rel + mask) @ v` | Nemotron FastConformer |
| small precision-sensitive modules (timestep embedder, norm scales) | vulnerable to bf16 downcast | compute on the host in fp32 and inject as a graph input | Z-Image `t_embedder` |
| prefill lm_head `[1, L, H]` alongside decode `[1, 1, H]` | two shapes | compile only the decode-step lm_head as its own fixed-shape graph | Qwen3-ASR partial hybrid |
| batch b with query K+1 for speculative verification | the decode op takes one query, the prefill op takes batch 1 | keep linear layers batched, loop rows through the prefill op; add the third graph to the same `CompileContext` | Qwen3-ASR verify graph |
| shipping `[b, 1, V]` float32 logits to a host sampler | transfer scales with batch | end the graph with `argmax(keepdim)` cast to int32 (greedy only) | Qwen3-ASR `fuse_greedy_argmax` |

## Partitioning rule

- Python control flow, tokenizer, logits processors and the generate loop are
  host orchestration.
- Heavy tensor components (encoder, prefill, decode step, head) belong on ATOM.
- Never disguise a failed ATOM stage as planned CPU work. Record it as a
  `fallback`.
