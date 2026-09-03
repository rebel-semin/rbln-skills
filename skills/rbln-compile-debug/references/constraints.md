# Compile constraints and knobs (version-pinned)

## Device generations

| Generation | Card | Note |
|---|---|---|
| ATOM (base) | RBLN-CA22 | The official base product. Measurements here are from CA25 and need re-confirmation on CA22. |
| ATOM-Max | RBLN-CA25 | 4 logical devices per card, roughly 15.7 GiB per logical device. Basis for everything below. |

## Invariants for an autoregressive decoder

1. Static shapes: tensor layout and maximum length are fixed before compiling.
2. Static-address KV: call `CompileContext.mark_static_address(tensor)` on the
   **very** example tensor you pass to compile.
3. One shared `CompileContext`: encoder and decoder (or tower and text stack)
   must use the same context.
4. Own the `rebel.Runtime`: persistent buffers have to outlive the call.

## optimum-rbln decoder-only config (confirmed on 0.10.4)

| Knob | Constraint / observation |
|---|---|
| `attn_impl="eager"` | Requires `kvcache_block_size == max_seq_len`. Reads the compiled KV length × decoder batch rows every step regardless of the true sequence length. |
| `attn_impl="flash_attn"` | Forces `kvcache_partition_len` into 4096–32768 (seen on 0.11.0.post1). Unusable for short contexts. |
| `prefill_chunk_size` | Multiple of 64; default 128. Setting it equal to `seq_len` makes a short prompt pay for the full padded length. Rule: the smallest chunk that covers the prompt in one pass. |
| `kvcache_num_blocks` | 1 for eager with batch 1. |
| `use_inputs_embeds=True` | Needed to inject externally built embeddings (audio, vision). Core of the shim pattern. |
| `use_attention_mask`, `use_position_ids` | Follow the model's semantics. The ASR shim used mask True, position_ids False. |
| `dtype="float32"` | Weight storage dtype. Compiler-internal compute may still be downcast to bf16 (see rbln-precision-check). |
| `decoder_batch_sizes` (serving) | The running batch is padded up to the next compiled bucket. With a 1/2/4/8/16/32 ladder, 9 rows cost a 16-row step. |
| `batch_size`, `max_seq_len`, `device` | Fixed at compile time. `device` is a container-visible id. |

## Choosing a compile surface

| Surface | Use for | Cannot express |
|---|---|---|
| `RBLN<Model>.from_pretrained(export=True)` | models optimum supports end to end | — |
| `RBLN<Model>.from_model(shim, rbln_config=...)` | a sub-stack that matches an existing class | a sub-stack whose semantics differ from the target class |
| `torch.compile(backend="rbln", dynamic=False, options={"mode":"strict"})` | fixed-shape stateless modules | autoregressive KV, dynamic host work |
| `rebel.compile_from_torch(module, input_info, example_inputs, compile_context)` | everything else; this is what optimum uses internally | — |

`torch.compile` and `compile_from_torch` share the same RBLN lowering. The
difference is the Dynamo adapter and who owns the inputs, context and runtime.

## Environment variables (observed)

| Variable | Effect |
|---|---|
| `RBLN_NUM_THREADS` | Runtime / compile threads. Must equal the Torch thread count during compilation. |
| `RBLN_PROFILER=1` | Collects kernel traces (see rbln-profile). |
| `RBLN_DEVICES` | Device selection in a serving container (container-visible id). |
| `RBLN_DEVICE_MAP` | **Not** consumed as a Runtime device selector by the installed SDK (0.10.5.dev143). Use `Runtime(device=N)` or `rbln_device`. |
| `DISABLE_REBEL_DATA_TYPE_CONVERSION_PASS=1`, `TRITON_F32_DEFAULT=ieee` | **No effect** on a `compile_from_torch` result; bf16 downcast persists (0.10.5.dev143). |
