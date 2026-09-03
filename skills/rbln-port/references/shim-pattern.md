# Shim pattern: a sub-stack onto an existing RBLN class

Validated on Qwen3-ASR-1.7B. The text stack (`thinker.model`,
`thinker.lm_head`) is wrapped as-is so that optimum's Qwen3 decoder-only runtime
(static KV, paged attention, prefill/decode split) can be reused.

## The shim class

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
        self.model = thinker.model          # original module, not a copy
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

## Compiling it

```python
from optimum.rbln import RBLNQwen3ForCausalLM, RBLNQwen3ForCausalLMConfig

compiled = RBLNQwen3ForCausalLM.from_model(
    shim, config=shim.config,
    rbln_config=RBLNQwen3ForCausalLMConfig(
        batch_size=1, max_seq_len=1024,
        use_inputs_embeds=True,      # inject audio-merged embeddings
        use_attention_mask=True, use_position_ids=False,
        attn_impl="eager",
        prefill_chunk_size=128,      # smallest chunk covering the prompt; 1024 wastes padding
        kvcache_block_size=1024,     # eager: == max_seq_len
        kvcache_num_blocks=1,
        dtype="float32", device=device,   # container-visible id
    ),
    model_save_dir=save_dir,
)
```

## Running it (hybrid generate)

1. Compile the audio tower separately as a static wrapper on ATOM (fixed feature
   length).
2. On the host, `masked_scatter` the audio embeddings into the token embeddings
   (a few ms).
3. Call optimum generate with `inputs_embeds`; still pass `input_ids` for HF
   bookkeeping.
4. Handle both return types from the optimum runtime (Tensor and output object).

## Confirmed pitfalls

- Copying weights into a plain HF `Qwen3ForCausalLM`: the state dict loads with
  no missing keys, but 3D position ids fail and the 2D fallback disagrees on
  logits/argmax. **Keeping the original modules is the point.**
- Eager attention requires `kvcache_block_size == max_seq_len`.
- Artifacts: prefill 3.3 GB, `decoder_batch_1` 15 MB, torch artifacts 1.2 GB
  (1.7B fp32, max_seq_len 1024). Artifact size is not runtime device memory.
- To reuse the same graphs for serving, fix the `decoder_batch_sizes` ladder and
  the audio buckets at compile time. The running batch is padded up to the next
  bucket.

## Result (62.455 s clip, greedy, batch 1)

| Item | Value |
|---|---|
| CPU fp32, 32 threads, p50 | 52–53 s |
| ATOM hybrid p50 / p95 | 3.31 / 3.32 s |
| token parity | 192/192 exact |
| stages | audio tower 56 ms, prefill 177 ms, decode 191 × 15.8 ms, host gap 0.25 ms/step |
