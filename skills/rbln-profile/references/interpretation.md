# Interpretation rules and observed cases (ATOM-Max, Qwen3-ASR-1.7B fp32 artifact)

## Verdict rules

- **compute-bound**: Neural Engine busy ≥ 90% of span, little DMA-only time.
- **weight-DMA-bound**: Neural DMA busy ≥ 90%, summed NE `comp_cycle` small (NE
  busy includes waiting on DMA), and the top Neural DMA family is `linear`.
- **activation / KV transfer**: large Task DMA byte movement with the
  `paged_attn` family on Task DMA.
- **host-bound**: layer 1 shows gaps plus host prep above 20%. The `Host` track
  alone cannot establish this.

## Case: batch-1 hybrid ASR (62 s clip, 192 tokens)

Layer 1 (profiler off, 5 runs):

| Segment | p50 | Share |
|---|---:|---:|
| audio tower (ATOM) | 55.7 ms | 1.7% |
| embedding + masked_scatter (CPU) | 2.8 ms | 0.1% |
| prefill (ATOM, one 1024 chunk) | 177 ms | 5.3% |
| decode, 191 steps | 15.88 ms/step (3,036 ms total) | 91.4% |
| generate-loop host gap | 0.25 ms/step (50 ms total) | 1.5% |

Step distribution p50 15.88 / p95 15.93 / max 16.20 ms (uniform). Host total is
0.3 ms per token (2%), so there is nothing to win in the loop.

Layer 2 (16-token trace):

| Phase | Device span | NE busy | Neural DMA busy | Task DMA moved | Verdict |
|---|---:|---:|---:|---:|---|
| audio tower | 54.7 ms | 95% | 12% | 0.6 GB | compute-bound (linear 22.8, conv 14.9, SDPA 5.7 ms) |
| prefill | 176 ms | 94% | 20% | 4.47 GB | compute-bound (linear 140, paged_attn_prefill 17.5 ms) |
| decode step | 15.7 ms | 79% | **97%** | 1 MB | **weight-DMA-bound** |

Decode detail: of 15.2 ms Neural DMA, 14.2 ms is `linear` (streaming fp32
weights). DMA-only time 3.2 ms, NE-only 0.4 ms. NE comp_cycles total 2.74M, so
actual compute is about 7%. The largest single op, `linear_196` = lm_head
(151936×2048 fp32, about 1.24 GB), takes 2.64 ms = 17% of the step. Streaming per
step is roughly 6.9 GB in 15.2 ms, about 450 GB/s effective.

Implication: decode scales with weight bytes. 16-bit weights could nearly halve
the step; lowering only lm_head's precision is worth about 8%. Prefill and the
audio tower are compute-bound and together only 7% of the total, so they rank low.

## Case: serving (vllm-rbln, 3 s clips, closed loop at N=3)

| | chunk 1024 | chunk 128 |
|---|---:|---:|
| prefill span p50 | 176 ms (a 63-token prompt padded to 1024 and fully computed) | 22 ms |
| device busy split | prefill 61.5% / decode 36.8% / audio 1.4% | decode 79.4% / prefill 17.0% / audio 3.0% |
| requests served in the same 40 s | 77 | 155 |

So "KV at 9% yet Waiting > 0" and "throughput sublinear in N" both came from
device saturation, and the saturation came from prefill padding. Per-chip
concurrency at RTF 0.5 went from 2 to 9.

## Case: the decoder batch bucket ladder (1/2/4/8/16/32)

| Running rows | 1 | 4 | 8 | **9** | 16 |
|---|--:|--:|--:|--:|--:|
| step ms | 15.5 | 17.2 | 18.9 | **26.4** | 28.0 |

Nine rows pad up to the 16-row bucket, doubling KV reads for a 40% jump. Pick
operating concurrency at a bucket edge.

## Case: the cost structure of speculative decoding

Verification (5 tokens per row) costs only 7–19% more than a 1-token decode,
exactly as a DMA-bound step predicts. The cost sits in the draft (a 0.6B step at
6.1–6.4 ms × K) and in one extra draft prefill per request (+11.6 ms). Net 1.51×
at batch 1; a loss at serving N ≥ 4 from prefill serialization and batch
fragmentation.

## Case: the host sampler

The real cost is transferring `[b, 1, 151936]` float32 logits. Sampling itself is
0.2 ms at b=1 rising to 1.2 ms at b=16 (2–4% of a step), which also caps what
graph-side argmax fusion can win. Measured −4 to −5% p50 before saturation, and
nothing after.
