---
name: rbln-precision-check
description: >-
  Verify that a model compiled for Rebellions ATOM (RBLN NPU) matches its CPU
  fp32 reference and localize precision drift before any speedup is quoted.
  Covers the rebel-compiler default bf16 downcast (add_convert_type_to_bf16),
  layer-by-layer error compounding, choosing token parity vs WER / PSNR /
  logit error as the gate, and near-tie argmax flips between recompiled
  graphs. Use when "ATOM 출력이 CPU와 다르다", transcripts differ, token parity
  fails, hidden-state error looks large, or a correctness gate must be
  designed for a new task.
---

# Checking ATOM correctness

Lock correctness before producing any speed number. Latency that did not pass a
gate is not a headline. Phrase the result as "no regression vs CPU fp32 on this
input set", never as "lossless".

## When this applies

- ATOM output has to be compared against CPU fp32 (right after a port, after
  changing a variant, after a recompile).
- Output differs and you need to localize where the divergence starts.

## Procedure

### 1. Pin the reference

- CPU fp32 eager with identical preprocessing, prompt, generation options and
  seed. For greedy, `num_beams=1`.
- Record the reference run's thread count **before ATOM runs** — the RBLN
  runtime mutates Torch's global thread setting.
- Note the input fixture's SHA256 and the model revision.
- If the reference needs different library versions, produce it in an isolated
  environment and import the artifact as a file. Do not disturb the container's
  pins.

### 2. Choose the metric for the task

See [references/metrics-by-task.md](references/metrics-by-task.md).

| Task | Primary gate | Supporting |
|---|---|---|
| greedy ASR / LLM | token parity (exact), text identical | normalized WER vs ground truth |
| streaming ASR (RNN-T etc., robust argmax) | WER vs CPU fp32 ≤ threshold (user-confirmed) | list of differing tokens |
| diffusion | decoded-image PSNR ≥ threshold, sharing the same seed latent | latent cosine, LPIPS, CLIP delta |
| vision classification | top-1 agreement | logit relative error |

An inequality threshold (≤, ≥) decides headline eligibility, so use only a value
the user explicitly confirmed. Token parity is defined as
`matched / max(len_candidate, len_reference)` — a length difference is a
mismatch — with `min_total: 1` so an empty output cannot pass.

### 3. Compare end-to-end

If it passes, go to step 6. If not, go to step 4.

### 4. Localize with a stage probe

1. Split the module into stages (subsampling → layers 1..N → pooler/head) and
   dump intermediate outputs for both ATOM and CPU fp32 from the same input.
2. Tabulate `max_abs` and `mean_rel` per stage. Error that grows layer by layer
   is **compiler-default bf16 downcast compounding**
   ([references/bf16-behavior.md](references/bf16-behavior.md)).
3. Simulate the same module on CPU in bf16 and fp16 and compare against the ATOM
   error. Same order of magnitude as the bf16 simulation means a dtype issue;
   much larger means a semantics issue (rewrite bug, mask direction, positions).
4. Stop at the first stage where the error jumps. Compare that stage's rewrite
   against the original on CPU (target `max_abs == 0`).

### 5. Mitigate

| Cause | Action |
|---|---|
| bf16 compounding, but greedy / argmax is robust | leave it, gate on the task metric (WER etc.) and record the error table |
| a small precision-sensitive module (timestep embedder, norm scale) | move it to the host in fp32 and inject as a graph input |
| rewrite semantics error | fix the rewrite until it is bit-exact against the original on CPU |
| near-tie argmax flips between two recompiled graphs (e.g. a decode graph vs a verify graph) | at a top-2 margin below about 0.1 this is numerical noise, not a bookkeeping bug. Record the frequency and margins, then judge by transcript impact |
| trying to force fp32 compute | `DISABLE_REBEL_DATA_TYPE_CONVERSION_PASS=1` and `TRITON_F32_DEFAULT=ieee` have no effect on `compile_from_torch` (0.10.5.dev143). Untested alternatives: optimum's `RBLNCompileConfig` fp32 route, per-op fp32 annotation |

### 6. Phrase the claim

- "Token-identical to CPU fp32 greedy on the N tested samples", or "WER x% vs
  y%, within sampling error".
- Parity on one or two samples means that execution path produced the same
  output; it is not a dataset accuracy guarantee. Multilingual, noisy, long-form
  and timestamp behaviour need separate evaluation.
- State the comparator's precision. Measuring the CPU side after a bf16
  conversion and calling it an fp32 baseline puts two baselines in one result.

## Done when

1. The chosen metric gate passes for ATOM vs CPU fp32.
2. If it failed first, the first diverging stage and its cause class (bf16 /
   semantics / near-tie) are recorded.
3. The gate definition, threshold and reference conditions (threads, seed,
   revision, fixture hash) are stored with the result.

## Verified against

ATOM-Max (RBLN-CA25), rebel-compiler 0.10.5.dev143, optimum-rbln 0.10.4.
Measured numbers: [references/bf16-behavior.md](references/bf16-behavior.md).
