# 사례 연구 (ATOM-Max RBLN-CA25, rebel-compiler 0.10.5.dev143, optimum-rbln 0.10.4)

수치는 single-stream, CPU fp32 eager 32 threads 대비, 저부하 host 조건. 내부 저장소
수치이므로 공개 전환 시 이 파일만 정리한다.

## Whisper-large-v3 — 경로 1 (+ 경로 3 검증)

- optimum `RBLNAutoModelForSpeechSeq2Seq`, `rbln_batch_size=1`, `rbln_token_timestamps=True`.
  아티팩트 encoder 1.5 GB + decoder 1.9 GB.
- 62.45초 클립: ATOM 약 5.0 s vs CPU 68.9 s (13.5x). WER 동일 20클립 3.09% vs 3.31%.
- stage: encoder 37x, decoder+lm 16x (token당 9.1 ms vs 149 ms), CPU glue는 양쪽 CPU.
  glue의 정체는 per-token logits processor(51,865 vocab 위 rep-penalty/suppress/timestamp).
- CPU 스레드 스윕: 8/16/32/64/96/128 → 91/86/**68.9**/82/84/124 s. 32 최적.
- encoder만 torch.compile: 122.6 ms/chunk지만 e2e 58 s (1.2x).
- torch.compile full decoder + custom op: `librbln.so` segfault.
- 손 재작성 L1 + compile_from_torch: optimum과 text 동일, 4.887 vs 4.849 s (1.01x).
- 고부하(load 55~66)에서 NPU e2e도 13~24 s로 악화 (CPU glue starvation). device compute는 불변.

## Qwen3-ASR-1.7B — 경로 2 (shim)

- 전체 클래스 없음. audio tower는 static wrapper + torch.compile, text stack은 shim →
  `RBLNQwen3ForCausalLM`.
- audio tower static wrapper: CPU bit-exact. NPU 배속 shape별 12.8x(5.9초) / 8.2x(30초)
  / 5.9x(62초). hidden state mean rel err 1.0~1.4% (bf16 유사).
- decode-step lm_head `[1,1,2048]→[1,1,151936]`: 2.9 ms vs 41~50 ms (14~17x).
- audio + lm_head hybrid: 1.2x. text/KV shim: 15.6~16.1x, 192/192 token exact.
- 커널 프로파일: decode step은 weight-DMA-bound (Neural DMA 97%, NE compute ~7%),
  prefill/audio tower는 compute-bound. lm_head 단독이 step의 17%.
- speculative decoding (0.6B draft, K=4, verify 그래프를 같은 CompileContext에): 배치-1
  1.51x, exact parity 유지. 서빙 동시성에서는 draft prefill과 배치 파편화로 손해.
- transformers 4.57.6는 `qwen3_asr`를 모름 → `qwen-asr==0.0.6 --no-deps`로 backend만 설치.

## Nemotron 3.5 ASR streaming 0.6B — 경로 3 (encoder)

- FastConformer + RNN-T. optimum에 conformer/RNN-T 없음. 상위 transformers 버전이
  필요해 encoder를 plain torch로 재구현(safetensors 키로 로드), 참조는 격리 venv에서.
- 재구현 검증: last_hidden max abs 1.5e-6, RNN-T greedy token-exact.
- encoder ATOM 31.3 ms vs CPU 407.6 ms (13x). e2e 0.546 vs 0.987 s (1.81x) — host RNN-T
  loop 523 ms가 96%.
- compiler-default bf16 누적: 층별 rel err 0.6% → 3% → 11% → 23%, pooler 87%. 그래도
  greedy WER 0.0488 (2 token 차이). fp32 강제 knob 무효.
- upstream eager attention의 float mask 방향 버그 → sdpa 참조 사용.

## Z-Image-Turbo — 경로 3 (DiT)

- diffusers 0.37 native `ZImagePipeline`. optimum diffusers 지원에 S3-DiT 없음.
- DiT만 compile_from_torch (bf16 weight, 15.7 GiB 안에 들어가도록), text-encoder/VAE는
  planned-hybrid. RoPE complex → real rotation, `t_embedder`는 host fp32.
- 시퀀스 4224 (image 4096 + caption 128 패딩)에 bound. 다른 길이는 recompile.
- 교훈: comparator를 bf16 변환 **전에** fp32로 만들 것 (한 결과에 두 precision의 CPU
  기준선이 섞인 사고).

## 공통 교훈

1. 정적 encoder류만 올리면 e2e는 거의 안 빨라진다. autoregressive/KV 경로가 본체.
2. compile 성공 ≠ 완료. device 배치, 반복 decode, full workload parity까지.
3. host glue와 load 민감도를 p50/p95와 loadavg로 같이 기록.
4. 마이크로벤치 배속(static wrapper vs static wrapper)과 e2e 배속을 섞지 않는다.
