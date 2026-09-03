# shim 패턴: 서브스택을 기존 RBLN 클래스에 태우기

Qwen3-ASR-1.7B에서 검증된 형태. text stack(`thinker.model`, `thinker.lm_head`)을 원본
그대로 감싸 optimum의 Qwen3 decoder-only 런타임(static KV, paged attention,
prefill/decode 분리)을 재사용했다.

## shim 클래스

```python
import copy
from transformers import GenerationConfig, PreTrainedModel

class ASRTextCausalLMShim(PreTrainedModel):
    base_model_prefix = "model"
    main_input_name = "input_ids"

    def __init__(self, thinker):
        text_config = copy.deepcopy(thinker.config.text_config)
        text_config._attn_implementation = "eager"
        text_config._attn_implementation_internal = "eager"
        super().__init__(text_config)
        self.model = thinker.model          # 원본 모듈, 복사 아님
        self.lm_head = thinker.lm_head
        self.vocab_size = thinker.config.text_config.vocab_size
        self.generation_config = GenerationConfig(
            pad_token_id=thinker.config.pad_token_id,
            eos_token_id=[151645, 151643],
        )

    def get_input_embeddings(self):
        return self.model.embed_tokens

    def set_input_embeddings(self, value):
        self.model.embed_tokens = value

    def can_generate(self):
        return True

    def forward(self, *args, **kwargs):
        outputs = self.model(*args, **kwargs)
        logits = self.lm_head(outputs.last_hidden_state)
        return type("ShimOutput", (), {
            "logits": logits, "past_key_values": outputs.past_key_values,
        })()
```

## 컴파일

```python
from optimum.rbln import RBLNQwen3ForCausalLM, RBLNQwen3ForCausalLMConfig

compiled = RBLNQwen3ForCausalLM.from_model(
    shim, config=shim.config,
    rbln_config=RBLNQwen3ForCausalLMConfig(
        batch_size=1, max_seq_len=1024,
        use_inputs_embeds=True,      # audio-merged embedding 주입
        use_attention_mask=True, use_position_ids=False,
        attn_impl="eager",
        prefill_chunk_size=128,      # 프롬프트를 한 패스로 덮는 최소값 (1024는 패딩 낭비)
        kvcache_block_size=1024,     # eager: == max_seq_len
        kvcache_num_blocks=1,
        dtype="float32", device=device,   # container-visible id
    ),
    model_save_dir=save_dir,
)
```

## 실행 (hybrid generate)

1. audio tower는 별도 static wrapper로 ATOM에 (fixed feature length).
2. host에서 token embedding + audio embedding `masked_scatter` (수 ms).
3. `inputs_embeds`로 optimum generate. `input_ids`는 HF bookkeeping용으로 그대로 전달.
4. optimum runtime이 Tensor를 반환하는 경우와 output object를 반환하는 경우 모두 처리.

## 확인된 함정

- 가중치를 plain HF `Qwen3ForCausalLM`에 복사: state_dict는 맞지만 3D position id에서
  실패, 2D fallback은 logits/argmax 불일치. **원본 모듈 보존이 핵심.**
- eager attention → `kvcache_block_size == max_seq_len`.
- 아티팩트: prefill 3.3 GB, decoder_batch_1 15 MB, torch_artifacts 1.2 GB (1.7B fp32,
  max_seq_len 1024). 아티팩트 크기 ≠ 런타임 device 메모리.
- 서빙에서 같은 그래프를 쓰려면 `decoder_batch_sizes` 사다리와 audio bucket을
  컴파일 시 정한다. 실행 배치는 상한 버킷으로 패딩된다.

## 결과 (62.455초 클립, greedy, 배치 1)

| 항목 | 값 |
|---|---|
| CPU fp32 32thr p50 | 52~53 s |
| ATOM hybrid p50 / p95 | 3.31 / 3.32 s |
| token parity | 192/192 exact |
| stage | audio tower 56 ms, prefill 177 ms, decode 191 × 15.8 ms, host gap 0.25 ms/step |
