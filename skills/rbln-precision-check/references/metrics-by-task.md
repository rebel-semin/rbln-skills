# Correctness metrics by task

| Task | Recommended metric | Reference | Note |
|---|---|---|---|
| ASR, greedy LLM | `token_parity` (exact), `text_identical` | CPU fp32 greedy | a length difference is a mismatch; require `min_total: 1` |
| ASR quality | normalized WER (Whisper `EnglishTextNormalizer` + Levenshtein) | dataset ground truth | compare CPU and NPU on the **same clips** |
| streaming ASR / transducer | WER vs CPU fp32 ≤ threshold | CPU fp32 | argmax proved robust to bf16 compounding (WER 0.0488, 2 tokens) |
| diffusion (t2i) | PSNR ≥ 25 dB on the decoded RGB, sharing the same seed latent | CPU fp32, same prompt / seed / steps | latent cosine, LPIPS and CLIP score delta are diagnostics |
| vision | top-1 agreement, `logit_rel_err` | CPU fp32 | |
| hidden state (component probe) | `max_abs`, `mean_rel` | CPU fp32, same input | a rewrite vs the original must be 0 on CPU |

## Token parity definition

```
ratio = matched / max(len(candidate), len(reference))
```

Require `min_total >= 1` so an empty output cannot pass. An inequality threshold
(WER ≤ 0.05 and similar) sets headline eligibility, so record the user's
confirmation.

## Reference conditions to record

- Model immutable revision, fixture SHA256
- CPU fp32 eager and the N in `torch.set_num_threads(N)` (captured before ATOM runs)
- greedy vs beam, max_new_tokens, any forced prompt (for ASR, a language suffix:
  without it the model can emit a `language English<asr_text>` tag that pollutes
  WER)
- seed, steps, guidance (diffusion)
