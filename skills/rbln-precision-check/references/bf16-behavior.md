# Default-precision observations (rebel-compiler 0.10.5.dev143, ATOM-Max)

## 1. The compiler downcasts compute to bf16

An `add_convert_type_to_bf16` pass applies on the `compile_from_torch` path. The
public Python API and cache files do not expose the internal arithmetic dtype, so
this was inferred from the error pattern.

Qwen3-ASR audio tower (dummy shape, hidden state vs CPU fp32):

| Comparison | mean_rel | max_abs |
|---|---:|---:|
| CPU bf16 simulation | 0.862% | 1.30e-3 |
| CPU fp16 simulation | 0.103% | 1.65e-4 |
| **NPU** | **1.00%** | **1.39e-3** |

The NPU error sits in the same order of magnitude as the bf16 simulation, not
fp16 or fp32.

## 2. It compounds through a deep stack

Nemotron FastConformer (24 layers, compile_from_torch, no custom ops):

| Stage | rel err |
|---|---:|
| early layers | 0.6% |
| middle | 3% → 11% |
| late | 23% |
| pooler | 87% |

Greedy RNN-T argmax stayed robust regardless: WER 0.0488 vs CPU fp32, with two
tokens differing at utterance boundaries ("Mr." → "Mister", a dropped trailing
"and").

## 3. Attempts to force fp32 (no effect)

| Knob | Result |
|---|---|
| `DISABLE_REBEL_DATA_TYPE_CONVERSION_PASS=1` | pooler error bit-identical (no change) |
| `TRITON_F32_DEFAULT=ieee` | no change (tested at shell level with triton caches cleared) |

Untested alternatives: optimum's `RBLNCompileConfig` fp32 route, per-op fp32
annotation.

## 4. The optimum decoder-only path (`dtype="float32"`)

The Qwen3-ASR text stack reproduced 192/192 tokens exactly across three or more
runs. Kernel traces show the decode step streaming what looks like fp32 weights
(about 6.9 GB per step), suggesting weights stay fp32 on this path. The artifact's
internal dtype was never confirmed directly.

## 5. Near-tie flips between recompiled graphs

Two graphs compiled from the same weights at different query lengths (a 1-token
decode graph and a K+1 verify graph) differed by at most 0.23 in logits with a
minimum top-1 margin of 0.19. Teacher-forced argmax agreed 190/190, yet 2 of 40
serving clips produced a different transcript (8 argmax disagreements across
1,420 positions, all at a top-2 margin ≤ 0.09). This is numerical difference
between recompiled graphs, not a bookkeeping error. Report such differences with
margin statistics rather than demanding exact parity.

## 6. The comparator-precision incident

In a DiT benchmark the comparator was built **after** the bf16 conversion, so the
supposedly "CPU fp32" stage figure was in fact a bf16 CPU measurement. One result
then mixed an fp32 end-to-end baseline with a bf16 stage baseline. Build the
comparator before any conversion with `compute_dtype=float32` and put the
precision in the detail key name.
