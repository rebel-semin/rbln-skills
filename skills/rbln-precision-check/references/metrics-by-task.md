# task별 correctness metric

| task | 권장 metric | 참조 | 비고 |
|---|---|---|---|
| ASR, greedy LLM | `token_parity` (exact), `text_identical` | CPU fp32 greedy | 길이 차이는 mismatch. `min_total: 1` |
| ASR 품질 | normalized WER (Whisper `EnglishTextNormalizer` + Levenshtein) | dataset ground truth | CPU와 NPU를 **같은 클립**에서 비교 |
| 스트리밍 ASR / transducer | WER vs CPU fp32 ≤ 임계 | CPU fp32 | argmax는 bf16 누적에 견고했음 (WER 0.0488, 2 token) |
| diffusion (t2i) | PSNR ≥ 25 dB (디코드 RGB), 같은 seed 초기 latent 공유 | CPU fp32 동일 prompt/seed/steps | latent cosine, LPIPS, CLIP score delta는 diagnostic |
| vision | top-1 일치, `logit_rel_err` | CPU fp32 | |
| hidden state (component probe) | `max_abs`, `mean_rel` | CPU fp32 같은 입력 | 재작성 vs 원본은 CPU에서 0이어야 함 |

## token parity 정의

```
ratio = matched / max(len(candidate), len(reference))
```

빈 출력이 통과하지 않도록 `min_total >= 1`. 부등식 임계(WER ≤ 0.05 등)는 headline
자격을 정하므로 사용자 확인을 기록한다.

## 참조 조건 기록 항목

- 모델 immutable revision, fixture SHA256
- CPU fp32 eager, `torch.set_num_threads(N)`의 N (ATOM 실행 전 캡처)
- greedy/beam, max_new_tokens, forced prompt (예: ASR language suffix — 없으면
  `language English<asr_text>` 태그가 출력에 섞여 WER이 오염됨)
- seed, steps, guidance (diffusion)
