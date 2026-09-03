# L1 / L2 recipe: a hand-written decoder with a shared CompileContext

This is the path used to rewrite optimum's WhisperWrapper by hand and still get
identical text at 1.01× the latency. It is the same contract optimum uses
internally.

## L2: the compile contract (model-independent, reuse as-is)

```python
import rebel
from rebel.compile_context import CompileContext

def register_optimum_ops():
    import optimum.rbln.ops  # registers paged_causal_attn_*, rbln_cache_update, ...

def mark_static_kv(ctx, input_info, example_inputs, key="key_value_states"):
    statics = {}
    for (name, _shape, _dtype), tensor in zip(input_info, example_inputs):
        if key in name:
            statics[name] = tensor
            ctx.mark_static_address(tensor)   # the very tensor passed to compile
    return statics

ctx = CompileContext(use_weight_sharing=False)
statics = mark_static_kv(ctx, enc_info, enc_ex)
dec_ex = build_decoder_inputs(dec_info, statics)   # decoder receives the same cross-KV tensors
mark_static_kv(ctx, dec_info, dec_ex)

cenc = rebel.compile_from_torch(enc.eval(), input_info=enc_info,
                                example_inputs=enc_ex, compile_context=ctx)
cdec = rebel.compile_from_torch(dec.eval(), input_info=dec_info,
                                example_inputs=dec_ex, compile_context=ctx)

enc_rt = rebel.Runtime(cenc, device=0, tensor_type="pt")   # must outlive the calls
dec_rt = rebel.Runtime(cdec, device=0, tensor_type="pt")
```

`input_info` is `[(name, shape, dtype_str), ...]`. Creating the Runtime inside
the call breaks persistent KV lifetime. To persist and reload:
`compiled.save(path)` then
`rebel.RBLNCompiledModel(path).create_runtime(device=N, tensor_type="pt")`.

## L1: what the Whisper decoder rewrite actually did

1. Precompute cross-attention K/V from the encoder output into a static buffer:
   ```python
   cross_key_values = torch.ops.rbln_custom_ops.rbln_cache_update(
       cross_key_values, cross_kv, b_idx[0], batch_axis)
   ```
2. Index `embed_positions.weight[position_id]` instead of computing positions.
3. Replace the self-attention KV write plus causal attention with a custom op:
   ```python
   attn_output = torch.ops.rbln_custom_ops.paged_causal_attn_decode(
       q=q, k=k, v=v,
       kcache=past_key_value[0].view(num_blocks, num_heads, 1, -1, head_dim),
       vcache=past_key_value[1].view(num_blocks, num_heads, 1, -1, head_dim),
       seq=cache_position.expand(bsz, 1),
       scale=torch.tensor(1.0, dtype=torch.float32),
       block_table=block_tables, block_size=block_size, mask=None)
   ```
4. Implement cross-attention as a plain matmul over the static cross-KV.

## L3: wiring generate

Substitute the rewritten runtimes for the optimum model's `encoder` / `decoder`
so the **same HF/optimum generate** still drives them. A simplified
reconstruction harness corrupted words at the 30-second chunk boundary; wiring
it back into the original generate restored identical full-clip text. Stride,
logits processors, timestamps and stop conditions belong to the orchestration.

## Stateless modules (encoder, DiT, conformer)

With no KV there is nothing to mark static. Compile at fixed shapes with
`compile_from_torch`, then `RBLNCompiledModel.save` / `create_runtime`. The
Nemotron FastConformer compiled with plain matmul attention and no custom ops, so
`optimum.rbln.ops` was never imported.

## Checklist for a new model

- [ ] Determine the KV layout the decode loop uses under `use_cache=True`
- [ ] Identify hostile ops: `index_copy_`, dynamic positions, mask construction
- [ ] Decide whether position embeddings / RoPE can be made static-friendly
- [ ] Decide whether self-attention maps onto a paged / custom op
- [ ] Decide whether cross-attention or tower output can be handed over as a
      static buffer
- [ ] Write a CPU-eager vs rewritten-wrapper token parity probe
- [ ] Write the adapter that reuses the existing generate orchestration
- [ ] Check text at long-form / chunk boundaries
