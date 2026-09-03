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

# Porting a model to ATOM

Try the cheapest path first, let a CPU stage breakdown decide what to offload,
lock correctness before measuring speed. The path classification picks a
starting implementation; it does not predict the outcome.

## When this applies

- A new model has to run on ATOM, or an existing port still has stages on the CPU.
- If you are chasing a compile failure itself, start with
  `/rbln-skills:rbln-compile-debug` instead.

## Procedure

### 0. Investigate before asking anything

1. Check what the installed optimum-rbln supports:
   `python -c "import optimum.rbln as o; print([n for n in dir(o) if n.startswith('RBLN')])"`
   plus the `optimum/rbln/transformers/models/` directory. The installed package
   is the authority, not the public `/latest/` docs.
2. Decompose the architecture into sub-stacks: preprocessing, encoder / tower,
   text decoder, head, postprocessing. Write down which sub-stack structurally
   matches which optimum class.
3. Measure a **CPU fp32 eager stage breakdown**. Offload the expensive stages
   first. Making a small encoder 10× faster barely moves end-to-end latency:
   in one case an audio-tower + lm_head hybrid reached 1.2×, and moving the
   text/KV decode took the same model to 15×.

### 1. Classify the path

Work through [references/decision-tree.md](references/decision-tree.md) in order.

| Path | Condition | Next |
|---|---|---|
| 1. official class | `RBLN<Model>` covers the whole model | export via `from_pretrained(export=True)`, jump to step 3 |
| 2. shim | a sub-stack (text decoder, vision encoder) matches an existing class | [references/shim-pattern.md](references/shim-pattern.md) |
| 3. hand-written L1 | no class fits (novel attention, RNN-T, DiT, conformer) | [references/l1-recipe.md](references/l1-recipe.md) |

Path 3 is common and is not a stop condition. Estimated effort or session count
is not a technical blocker.

### 2. Implement for the chosen path

**Path 2 (shim).** Build a `PreTrainedModel` subclass that keeps the original
modules (`thinker.model`, `thinker.lm_head`, ...) by reference, force the config
to eager attention, then call
`RBLN<Base>ForCausalLM.from_model(shim, rbln_config=...)`. Copying weights into
a plain HF class breaks as soon as position or rotary semantics differ. Inject
externally built embeddings with `use_inputs_embeds=True`.

**Path 3 (L1).** Separate what you reuse from what you write.

| Layer | Content | Reuse |
|---|---|---|
| L1 | rewrite decoder / attention / position / KV to be static-friendly | per model |
| L2 | `compile_from_torch`, shared `CompileContext`, static-address KV, owned `Runtime` | recipe as-is |
| L3 | `import optimum.rbln.ops`, runtime adapter, HF `generate` wiring | optimum / SDK |

Stateless fixed-shape modules (encoder, audio tower, DiT, decode-step lm_head)
work through either `torch.compile(backend="rbln", dynamic=False)` or
`compile_from_torch`. Stateful (KV) modules require `compile_from_torch`.

### 3. Correctness ladder, before any speed number

1. Rewritten module vs original on CPU: `max_abs` (target 0).
2. Component parity: ATOM output vs CPU fp32 (hidden-state relative error;
   thresholds per case in `/rbln-skills:rbln-precision-check`).
3. N-step token parity: from the same encoder input, decoder tokens agree for
   N steps.
4. Full-clip / full-prompt parity: wired into the **original generate
   orchestration**, including stride, logits processors, timestamps and stop
   conditions. Model tensors can be right while a different orchestration
   corrupts words at chunk boundaries — that happened on Whisper.

### 4. Record where each stage ran

For every stage inside the timing scope, state the backend and, for CPU stages,
the role: `atom` / `cpu: host-orchestration` (preprocessing, tokenizer, generate
loop) / `cpu: planned-hybrid` (deliberately left this session) / `cpu: fallback`
(intended for ATOM but unsupported). Never label a fallback as planned. Name the
placement evidence for each ATOM stage (`rbln-smi` PID, `Runtime(device=N)`).

### 5. Measure and phrase it honestly

- CPU baseline is fp32 eager. Sweep thread counts (32 was best in past ASR work;
  batch-1 autoregressive decode gets slower with more threads). Capture the
  thread count **before** ATOM runs.
- Report p50 and p95, warmup count, run count, load average, compile time and
  artifact size.
- Label every ratio "vs CPU fp32 eager". A GPU comparison requires a separate
  run at matching workload, precision and timing scope.
- Never quote a partial-offload microbenchmark ratio as an end-to-end ratio.

## Done when

1. The requested end-to-end path has at least one real ATOM stage with placement
   evidence.
2. All four rungs of the correctness ladder pass (or the task-appropriate metric
   gate does).
3. The execution map, CPU baseline, p50/p95 and versions (rebel-compiler,
   optimum-rbln, torch, transformers) are recorded.
4. Any stage still on the CPU is marked planned-hybrid or fallback, and the next
   bottleneck is written down.

## Verified against

ATOM-Max (RBLN-CA25), rebel-compiler 0.10.5.dev143, optimum-rbln 0.10.4,
torch 2.10.0+cpu, transformers 4.57.6. Per-model numbers and lessons:
[references/case-studies.md](references/case-studies.md).
