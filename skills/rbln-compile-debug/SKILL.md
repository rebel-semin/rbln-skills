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

# Diagnosing an RBLN compile failure

One compile failure is not a stop condition for a port. Minimize the failing
graph, identify the exact op or state transition that breaks, then route around
it with a semantics-preserving rewrite. Declare a component blocked only when a
minimized reproducer plus materially different alternatives have all failed.

## When this applies

- `rebel.compile_from_torch`, `torch.compile(backend="rbln")`, or an optimum-rbln
  `RBLN<Model>.from_model / from_pretrained(export=True)` ended in an exception
  or a crash.
- Compilation succeeded but you suspect a stage is silently running on the host.

## Procedure

### 1. Capture the error and classify it

Save the full traceback and stderr. Read the **first** RBLN error, not the last
line. Full catalog: [references/error-catalog.md](references/error-catalog.md).

| Symptom | Class |
|---|---|
| `RBLNCompileError ... [DEVICE_GRAPH_CONVERSION]`, `tensor<...{mem_loc = "host"}>` vs device output | A. dynamic host work inside the graph |
| Dynamo graph break warning (`Tensor.item()`, `tolist`, dynamic slicing) | A. same cause, torch.compile path |
| `librbln.so` segfault, exit 139, crash during graph optimization | B. autoregressive KV contract expressed through torch.compile |
| `kvcache_block_size`, `prefill_chunk_size % 64`, `kvcache_partition_len` assertion | C. optimum-rbln config constraint |
| `Global num_threads state changed while dynamo tracing` | D. thread count changed mid-compile |
| A specific op is named unsupported | A, or E if a replacement op is needed |

### 2. Minimize the failing graph

1. Split the model into preprocessing / encoder (tower) / decoder step / cache
   update / head and compile each at fixed shapes. Tabulate what compiles and
   what does not.
2. Inside the failing module, bisect `forward` until you reach the first failing
   op. Strict mode does not fall back silently, so the failure point is the cause.
3. Make the reproducer run with random weights. It is then usable as-is for a
   compiler bug report.

### 3. Fix by class

**A. Dynamic host work leaked into the graph.**
Typical offenders: `ceil`, `tolist`, `split`, `pad_sequence`, `Tensor.item()`,
runtime position arithmetic, attention-mask construction inside the graph.
Rewrite using the mapping table in
[references/op-rewrites.md](references/op-rewrites.md). The core pattern is
**compute once on the host for a fixed shape, pass a constant tensor into the
graph**. Verify the rewritten module is bit-exact against the original on CPU
(`max_abs == 0`) before compiling it.

**B. You tried to put a decoder plus KV cache through torch.compile.**
Custom ops do not rescue this. The static-address KV, shared `CompileContext`
and runtime-ownership contract is only expressible through
`rebel.compile_from_torch`. Switch to the L1 recipe in
`/rbln-skills:rbln-port`. Keep `torch.compile(backend="rbln")` for fixed-shape
stateless modules only (encoder, audio tower, decode-step lm_head).

**C. optimum-rbln config constraint.**
Match the values in [references/constraints.md](references/constraints.md).
Common ones: eager attention requires `kvcache_block_size == max_seq_len`;
`prefill_chunk_size` must be a multiple of 64 (32 is rejected by the compiler
even if you relax the optimum check); flash attention's
`kvcache_partition_len` lower bound rules it out for short contexts.

**D. Thread count changed.**
Compilation fails if `RBLN_NUM_THREADS` and `torch.get_num_threads()` diverge
while tracing. Pin both to the same value before compiling and remove any
`torch.set_num_threads` call that runs during compilation (benchmark harnesses
are a frequent source).

**E. Genuinely unsupported op.**
1. After `import optimum.rbln.ops`, look for a replacement in
   `torch.ops.rbln_custom_ops` (`paged_causal_attn_decode/prefill`,
   `rbln_cache_update`, flash / moe / linear variants).
2. Read the nearest `<model>_architecture.py` and `decoderonly/` in the
   installed optimum-rbln to see how the same problem was solved there.
3. Otherwise express the same semantics with static buffers, tensor masking and
   gather/scatter.

### 4. Verify after a successful compile

Compiling is not the finish line.

- Real device placement: does `rbln-smi` show this PID on the expected device
  row? (probe in `/rbln-skills:rbln-env-doctor`)
- Repeated calls: run the decoder for at least N steps and confirm the KV cache
  survives; make sure the runtime is not rebuilt inside the call.
- Correctness: gate against the CPU fp32 reference with
  `/rbln-skills:rbln-precision-check`.

## Done when

All of the following hold:

1. The target module compiles at fixed shapes and produced its `.rbln` artifacts.
2. The rewritten module matches the original numerically on CPU (or within a
   documented tolerance).
3. Device placement is proven, and stateful modules keep their output across
   repeated calls.
4. For anything still unresolved, a minimized reproducer, the alternatives you
   tried, and the next smallest experiment are written down.

## Verified against

ATOM-Max (RBLN-CA25), rebel-compiler 0.10.5.dev143, optimum-rbln 0.10.4
(batch-1 path); rebel-compiler / optimum-rbln 0.11.0.post1 (some class-C
constraints, serving path). Version detail:
[references/constraints.md](references/constraints.md).
