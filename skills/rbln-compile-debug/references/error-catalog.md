# Observed error catalog

Error strings seen in real ATOM-Max ports, with the cause that was confirmed.
Add new cases to the table.

| Error / symptom | Where | Confirmed cause | Fix |
|---|---|---|---|
| `RBLNCompileError: Graph Generation: [DEVICE_GRAPH_CONVERSION]` | `torch.compile(backend="rbln", options={"mode":"strict"})` on an audio tower, on a text prefill | dynamic host chunking in `forward` (`ceil`, `tolist`, `split`, `pad_sequence`) produces host shape tensors that do not type-check against device output | static wrapper that precomputes chunk metadata for one fixed feature length |
| `tensor<6xi64, {mem_loc = "host"}>` vs expected device output host tensor | same as above | same as above | same as above |
| Dynamo graph break warning at `Tensor.item()` | full-thinker (`use_cache=True`) probe | audio feature length slicing calls `.item()` | fix the length on the host, pass it as a Python int constant |
| `librbln.so` segfault, exit code 139, during graph optimization | `torch.compile` + optimum WhisperWrapper + `ctx.mark_static_address` + `torch._dynamo.mark_static_address` | the `index_copy_` / `diff` compile errors disappeared with custom ops, but the torch.compile path could not bind the shared static-KV contract to the actual backend graph inputs | move to `rebel.compile_from_torch` with a shared `CompileContext` and an owned `Runtime` |
| eager attention rejects `kvcache_block_size != max_seq_len` | `RBLNQwen3ForCausalLMConfig` | optimum-rbln requirement | set both to the same value (e.g. 1024 / 1024) |
| `prefill_chunk_size % 64 != 0` rejected | `configuration_decoderonly.py` | optimum check; relaxing it still leaves the compiler rejecting 32 | choose 64, 128 or 256 |
| `kvcache_partition_len` forced to 4096–32768 | `attn_impl="flash_attn"` (optimum-rbln 0.11.0.post1) | flash attention partition lower bound | stay on eager for a 1024 context; reduce KV reads via a smaller `max_seq_len` instead |
| `Global num_threads state changed while dynamo tracing` | audio tower `torch.compile` | `RBLN_NUM_THREADS` differs from the Torch thread count | pin `RBLN_NUM_THREADS == torch.get_num_threads()` |
| 3D position ids fail in plain HF `Qwen3ForCausalLM`; 2D fallback logits disagree | copying ASR text weights into a plain HF class | model-specific position / rotary semantics | wrap the original modules in a `PreTrainedModel` shim and hand that to the optimum class |
| `torch.get_num_threads()` changes after ATOM execution (32 → 64) | benchmark harness | the RBLN runtime mutates Torch's global thread setting | capture the CPU baseline thread count before any ATOM execution |
| optimum text runtime returns a Tensor instead of an HF output object | `RBLNQwen3ForCausalLM` decode | return type varies by path | handle both types |
| `device_count = 0` | container | `/dev/rsd0` not mounted | add `--device /dev/rsd0` (see rbln-env-doctor) |
