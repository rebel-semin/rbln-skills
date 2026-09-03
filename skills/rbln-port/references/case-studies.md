# Case studies (ATOM-Max RBLN-CA25, rebel-compiler 0.10.5.dev143, optimum-rbln 0.10.4)

All numbers are single-stream, against CPU fp32 eager at 32 threads, on a
low-load host. These are internal figures: if this repository ever goes public,
this is the file to scrub.

## Whisper-large-v3 — path 1 (plus a path-3 validation)

- optimum `RBLNAutoModelForSpeechSeq2Seq`, `rbln_batch_size=1`,
  `rbln_token_timestamps=True`. Artifacts: encoder 1.5 GB + decoder 1.9 GB.
- 62.45 s clip: ATOM about 5.0 s vs CPU 68.9 s (13.5×). WER on the same 20 clips
  3.09% vs 3.31%.
- Stages: encoder 37×, decoder+lm 16× (9.1 ms vs 149 ms per token). CPU glue runs
  on the CPU either way; its content is the per-token logits processors
  (repetition penalty / suppress / timestamps over a 51,865 vocab).
- CPU thread sweep 8/16/32/64/96/128 → 91/86/**68.9**/82/84/124 s. 32 is best.
- encoder-only torch.compile: 122.6 ms per chunk but 58 s end-to-end (1.2×).
- torch.compile on the full decoder with custom ops: `librbln.so` segfault.
- Hand-written L1 with compile_from_torch: text identical to optimum,
  4.887 vs 4.849 s (1.01×).
- Under heavy host load (load 55–66) even NPU end-to-end degraded to 13–24 s from
  CPU-glue starvation, while device compute stayed flat.

## Qwen3-ASR-1.7B — path 2 (shim)

- No full class. The audio tower runs as a static wrapper under torch.compile;
  the text stack goes through a shim into `RBLNQwen3ForCausalLM`.
- Audio tower static wrapper: bit-exact on CPU. NPU speedup varies by shape,
  12.8× (5.9 s) / 8.2× (30 s) / 5.9× (62 s). Hidden-state mean relative error
  1.0–1.4% (bf16-like).
- Decode-step lm_head `[1,1,2048] → [1,1,151936]`: 2.9 ms vs 41–50 ms (14–17×).
- audio + lm_head hybrid: 1.2×. Text/KV shim: 15.6–16.1× with 192/192 tokens exact.
- Kernel profile: the decode step is weight-DMA-bound (Neural DMA 97% busy, NE
  compute about 7%); prefill and the audio tower are compute-bound. lm_head alone
  is 17% of a step.
- Speculative decoding (0.6B draft, K=4, verify graph in the same CompileContext):
  1.51× at batch 1 with exact parity preserved; a loss under serving concurrency
  because of draft prefill and batch fragmentation.
- transformers 4.57.6 does not know `qwen3_asr`, so the backend package was
  installed with `--no-deps` to keep the pin.

## Nemotron 3.5 ASR streaming 0.6B — path 3 (encoder)

- FastConformer plus RNN-T. optimum has no conformer or RNN-T class. A newer
  transformers was required, so the encoder was reimplemented in plain torch
  (weights loaded from safetensors by key) and the reference produced in an
  isolated venv.
- Reimplementation check: last_hidden max abs 1.5e-6; RNN-T greedy decode
  token-exact.
- Encoder on ATOM 31.3 ms vs CPU 407.6 ms (13×). End-to-end 0.546 vs 0.987 s
  (1.81×) — the host RNN-T loop at 523 ms is 96% of it.
- Compiler-default bf16 compounds: per-stage relative error 0.6% → 3% → 11% →
  23%, pooler 87%. Greedy WER still 0.0488 (2 tokens differ). The fp32 knobs had
  no effect.
- The upstream eager attention path has a float-mask direction bug, so sdpa was
  used for the reference.

## Z-Image-Turbo — path 3 (DiT)

- diffusers 0.37 ships a native `ZImagePipeline`; optimum's diffusers support has
  no S3-DiT class.
- Only the DiT is compiled with compile_from_torch (bf16 weights, to fit inside
  15.7 GiB); the text encoder and VAE stay planned-hybrid. Complex RoPE became
  real rotation, and `t_embedder` runs on the host in fp32.
- The artifact is bound to sequence length 4224 (4096 image + 128 padded caption).
  A different length needs a recompile.
- Lesson: build the comparator **before** the bf16 conversion. One result
  otherwise carried two different CPU baselines (an fp32 e2e baseline next to a
  bf16 stage baseline).

## Shared lessons

1. Offloading only the static encoder-ish parts barely moves end-to-end latency.
   The autoregressive / KV path is the real body of work.
2. A successful compile is not the finish line: prove device placement, repeated
   decode, and full-workload parity.
3. Record host glue and load sensitivity alongside p50/p95 and load average.
4. Never mix a microbenchmark ratio (static wrapper vs static wrapper) with an
   end-to-end ratio.
