# L1/L2 레시피: 손으로 쓰는 decoder + 공유 CompileContext

Whisper-large-v3에서 optimum WhisperWrapper를 직접 재작성해 optimum 대비 text 동일,
latency 1.01x를 확인한 경로. optimum이 내부에서 쓰는 것과 같은 계약이다.

## L2: compile 계약 (모델 무관, 그대로 재사용)

```python
import rebel
from rebel.compile_context import CompileContext

def register_optimum_ops():
    import optimum.rbln.ops  # paged_causal_attn_*, rbln_cache_update 등 등록

def mark_static_kv(ctx, input_info, example_inputs, key="key_value_states"):
    statics = {}
    for (name, _shape, _dtype), tensor in zip(input_info, example_inputs):
        if key in name:
            statics[name] = tensor
            ctx.mark_static_address(tensor)   # compile에 넘기는 바로 그 tensor
    return statics

ctx = CompileContext(use_weight_sharing=False)
statics = mark_static_kv(ctx, enc_info, enc_ex)
dec_ex = build_decoder_inputs(dec_info, statics)   # decoder는 같은 cross-KV tensor를 받음
mark_static_kv(ctx, dec_info, dec_ex)

cenc = rebel.compile_from_torch(enc.eval(), input_info=enc_info,
                                example_inputs=enc_ex, compile_context=ctx)
cdec = rebel.compile_from_torch(dec.eval(), input_info=dec_info,
                                example_inputs=dec_ex, compile_context=ctx)

enc_rt = rebel.Runtime(cenc, device=0, tensor_type="pt")   # 호출 사이에 살아 있어야 함
dec_rt = rebel.Runtime(cdec, device=0, tensor_type="pt")
```

`input_info`는 `[(name, shape, dtype_str), ...]`. Runtime을 함수 안에서 매번 만들면
persistent KV 수명이 끊긴다. 저장/복원은 `compiled.save(path)` →
`rebel.RBLNCompiledModel(path).create_runtime(device=N, tensor_type="pt")`.

## L1: Whisper decoder 재작성에서 한 일

1. encoder 출력으로 cross-attention K/V를 미리 계산해 static buffer에 write:
   ```python
   cross_key_values = torch.ops.rbln_custom_ops.rbln_cache_update(
       cross_key_values, cross_kv, b_idx[0], batch_axis)
   ```
2. 동적 position 대신 `embed_positions.weight[position_id]` 직접 indexing.
3. self-attention KV write + causal attention을 custom op으로:
   ```python
   attn_output = torch.ops.rbln_custom_ops.paged_causal_attn_decode(
       q=q, k=k, v=v,
       kcache=past_key_value[0].view(num_blocks, num_heads, 1, -1, head_dim),
       vcache=past_key_value[1].view(num_blocks, num_heads, 1, -1, head_dim),
       seq=cache_position.expand(bsz, 1),
       scale=torch.tensor(1.0, dtype=torch.float32),
       block_table=block_tables, block_size=block_size, mask=None)
   ```
4. cross-attention은 static cross-KV 위의 plain matmul.

## L3: generate 연결

재작성한 runtime을 optimum 모델 객체의 `encoder`/`decoder` 자리에 꽂아 **같은
HF/optimum generate**를 재사용한다. 단순 재구성 harness에서는 30초 chunk 경계 단어가
깨졌고, 같은 generate에 연결하자 full-clip text가 다시 동일해졌다. stride, logits
processor, timestamp, stop condition은 orchestration이 소유한다.

## stateless 모듈 (encoder, DiT, conformer)

KV가 없으면 L2에서 `mark_static_kv`가 필요 없다. `compile_from_torch`로 고정 shape
컴파일 후 `RBLNCompiledModel.save`/`create_runtime`. Nemotron FastConformer는 custom op
없이 plain matmul attention으로 컴파일됐다 (`optimum.rbln.ops` import 불필요).

## 새 모델 체크리스트

- [ ] `use_cache=True`에서 decode loop의 KV layout 확인
- [ ] `index_copy_`, 동적 position, mask 생성 등 hostile op 식별
- [ ] position embedding / RoPE를 static-friendly로 바꿀 수 있는지
- [ ] self-attention을 paged/custom op으로 치환 가능한지
- [ ] cross-attention / tower 출력을 static buffer로 넘길 수 있는지
- [ ] CPU eager vs 재작성 wrapper token parity probe
- [ ] generate orchestration 재사용 adapter
- [ ] long-form / chunk 경계 text 확인
