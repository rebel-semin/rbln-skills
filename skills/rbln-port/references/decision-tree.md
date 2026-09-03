# 포팅 경로 결정 트리 (비용 낮은 순)

## 1. optimum-rbln 전체 지원

확인: 설치본의 `optimum/rbln/transformers/models/<model>/` 존재, `RBLN<Model>ForXxx`
클래스 존재. 0.10.4 기준 주요 지원: whisper, llama, gemma/2/3, mistral, qwen2/qwen3,
qwen2_5_vl, qwen3_vl, qwen3_moe, gpt2, t5, bart, bert, clip, siglip, vit, wav2vec2,
AST; diffusers는 SD/SD3/SDXL/Cosmos/Kandinsky + `RBLNAutoencoderKL`.

```python
from optimum.rbln import RBLNAutoModelForSpeechSeq2Seq
model = RBLNAutoModelForSpeechSeq2Seq.from_pretrained(
    model_id="openai/whisper-large-v3", export=True,
    rbln_batch_size=1, rbln_token_timestamps=True,
)
model.save_pretrained("whisper-large-v3")
```

export, load, generate, device option을 공식 경로로 먼저 검증한 뒤 wrapper를 고민한다.

## 2. 서브스택 shim

조건: 전체 클래스는 없지만 text decoder / vision encoder가 기존 architecture와
구조적으로 같다 (layer 구성, attention, rotary). 확인 방법:

1. 원본 서브모듈의 `state_dict` 키와 대상 optimum architecture의 기대 키 비교.
2. 원본 config를 optimum config 클래스로 변환 가능한지 (`text_config` 등).
3. position id 차원, rotary table, special token 처리가 같은지. 다르면 원본 모듈을
   **그대로** shim 안에 두고 forward만 노출한다 (가중치 복사 금지).

성공 사례: Qwen3-ASR thinker text stack → `RBLNQwen3ForCausalLM`.
실패 사례: 같은 가중치를 plain `Qwen3ForCausalLM`에 복사 → 3D position id 불일치.

## 3. L1 손 작성

조건: 새 attention 구조(conformer relative-position, RNN-T joint), DiT, 새 MoE,
custom KV layout.

시작 순서:

1. CPU reference와 가장 작은 representative static workload 고정.
2. 컴포넌트 분리(preprocess / encoder / decoder step / cache update / head / postprocess).
3. stock 그래프를 고정 shape로 컴파일 시도 → 첫 실패 op 최소화.
4. optimum 설치본(`<model>_architecture.py`, `decoderonly/`, `ops/`)과 vllm-rbln
   adapter에서 같은 문제의 해법 검색.
5. 동적 인덱싱/mutation/mask/position을 static buffer, fixed bucket, tensor masking,
   precomputed tensor, custom op으로 치환.
6. control flow와 경량 작업은 host, heavy tensor는 ATOM.
7. 각 재작성마다 component parity, 통합 후 e2e parity.

## 어느 것을 먼저 올리나

CPU stage breakdown에서 시간이 큰 것부터. 관측된 패턴:

| 모델 | CPU에서 큰 stage | 결과 |
|---|---|---|
| Whisper-large-v3 | decoder+lm 45.8s, encoder 20.2s (총 68.9s) | encoder만 torch.compile → 1.2x; 전체 optimum → 13.5x |
| Qwen3-ASR-1.7B | text decode 39.5s + lm_head decode 7.8s (총 49.5s), audio tower 0.55s | audio+lm_head → 1.2x; text/KV shim → 15~16x |
| Nemotron 0.6B RNN-T | encoder 408ms, RNN-T greedy loop 523ms | encoder만 → 1.81x (encoder 자체 13x). 다음은 decode step |
| Z-Image-Turbo | DiT 8회 forward가 지배 | DiT만 compile_from_torch, text-enc/VAE는 planned-hybrid |

## vLLM-RBLN은 source reference

LLM/VLM backbone이 있으면 vllm-rbln의 attention mode, sampler, model adapter를
참고한다. 하지만 서빙 런타임이므로 배치-1 latency 실험 구조를 scheduler에 맞추지
않고, throughput 수치를 latency 결과에 섞지 않는다.
