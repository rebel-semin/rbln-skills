# Porting decision tree (cheapest first)

## 1. optimum-rbln supports the whole model

Check: `optimum/rbln/transformers/models/<model>/` exists in the installed
package and an `RBLN<Model>ForXxx` class is exported. As of 0.10.4 the notable
coverage is whisper, llama, gemma/2/3, mistral, qwen2/qwen3, qwen2_5_vl,
qwen3_vl, qwen3_moe, gpt2, t5, bart, bert, clip, siglip, vit, wav2vec2, AST; on
the diffusers side SD / SD3 / SDXL / Cosmos / Kandinsky plus
`RBLNAutoencoderKL`.

```python
from optimum.rbln import RBLNAutoModelForSpeechSeq2Seq
model = RBLNAutoModelForSpeechSeq2Seq.from_pretrained(
    model_id="openai/whisper-large-v3", export=True,
    rbln_batch_size=1, rbln_token_timestamps=True,
)
model.save_pretrained("whisper-large-v3")
```

Validate export, load, generate and device options through the official path
before considering any wrapper.

## 2. Shim a sub-stack

Condition: no full class exists, but a text decoder or vision encoder is
structurally the same as an existing architecture (layer composition, attention,
rotary). How to check:

1. Compare the sub-module's `state_dict` keys against the keys the target
   optimum architecture expects.
2. Confirm the original config converts into the optimum config class
   (`text_config` and friends).
3. Confirm position-id rank, the rotary table and special-token handling match.
   If they differ, keep the original modules **as they are** inside the shim and
   only expose `forward` — do not copy weights.

Success: the Qwen3-ASR thinker text stack onto `RBLNQwen3ForCausalLM`.
Failure: copying those same weights into a plain `Qwen3ForCausalLM`, where 3D
position ids did not apply.

## 3. Hand-written L1

Condition: a novel attention structure (conformer relative position, an RNN-T
joint), a DiT, a new MoE, or a custom KV layout.

Order of work:

1. Fix the CPU reference and the smallest representative static workload.
2. Split components (preprocess / encoder / decoder step / cache update / head /
   postprocess).
3. Try the stock graph at fixed shapes, then minimize the first failing op.
4. Search the installed optimum-rbln (`<model>_architecture.py`, `decoderonly/`,
   `ops/`) and applicable vllm-rbln adapters for the same problem.
5. Replace dynamic indexing / mutation / masks / position math with static
   buffers, fixed buckets, tensor masking, precomputed tensors or custom ops.
6. Move control flow and lightweight work to the host; keep heavy tensor work on
   ATOM.
7. Re-check component parity after each rewrite, then end-to-end parity after
   integration.

## What to offload first

Highest CPU stage time first. Observed pattern:

| Model | Large CPU stages | Outcome |
|---|---|---|
| Whisper-large-v3 | decoder+lm 45.8 s, encoder 20.2 s (68.9 s total) | encoder-only torch.compile → 1.2×; full optimum path → 13.5× |
| Qwen3-ASR-1.7B | text decode 39.5 s + lm_head decode 7.8 s (49.5 s total), audio tower 0.55 s | audio + lm_head → 1.2×; text/KV shim → 15–16× |
| Nemotron 0.6B RNN-T | encoder 408 ms, RNN-T greedy loop 523 ms | encoder only → 1.81× e2e (encoder itself 13×). Decode step is next |
| Z-Image-Turbo | 8 DiT forwards dominate | DiT via compile_from_torch; text encoder and VAE stay planned-hybrid |

## vLLM-RBLN is a source reference

For a model with an LLM or VLM backbone, read vllm-rbln's attention modes,
sampler and model adapters. It is a serving runtime though: do not reshape a
batch-1 latency experiment around its scheduler, and never mix its throughput
numbers into a latency result.
