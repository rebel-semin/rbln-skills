# 트레이스 해석 규칙과 관측 사례 (ATOM-Max, Qwen3-ASR-1.7B fp32 아티팩트)

## 판정 규칙

- **compute-bound**: Neural Engine busy ≥ 90% of span, DMA-only 구간 작음.
- **weight-DMA-bound**: Neural DMA busy ≥ 90%, NE `comp_cycle` 합이 작음(NE busy는 DMA
  대기 포함), Neural DMA 상위 family가 `linear`.
- **activation/KV 전송**: Task DMA 이동 바이트가 크고 `paged_attn` family가 Task DMA에.
- **호스트 병목**: 1층에서 gap + host prep이 20% 이상. 2층 `Host` 트랙만으로는 판단 불가.

## 사례: 배치-1 hybrid ASR (62초 클립, 192 token)

1층 (profiler OFF, 5 run):

| 구간 | p50 | 전체 대비 |
|---|---:|---:|
| audio tower (ATOM) | 55.7 ms | 1.7% |
| embedding + masked_scatter (CPU) | 2.8 ms | 0.1% |
| prefill (ATOM, 1024 chunk 1회) | 177 ms | 5.3% |
| decode 191 step | 15.88 ms/step (합 3,036 ms) | 91.4% |
| generate loop host gap | 0.25 ms/step (합 50 ms) | 1.5% |

step 분포 p50 15.88 / p95 15.93 / max 16.20 ms (균질). host 합계 0.3 ms/token(2%) →
루프 최적화 여지 없음.

2층 (16 token 트레이스):

| phase | device span | NE busy | Neural DMA busy | Task DMA moved | 판정 |
|---|---:|---:|---:|---:|---|
| audio tower | 54.7 ms | 95% | 12% | 0.6 GB | compute-bound (linear 22.8, conv 14.9, SDPA 5.7 ms) |
| prefill | 176 ms | 94% | 20% | 4.47 GB | compute-bound (linear 140, paged_attn_prefill 17.5 ms) |
| decode step | 15.7 ms | 79% | **97%** | 1 MB | **weight-DMA-bound** |

decode 세부: Neural DMA 15.2 ms 중 14.2 ms가 `linear`(fp32 가중치 스트리밍). DMA만
도는 구간 3.2 ms, NE만 0.4 ms. NE comp_cycle 2.74M → 실제 compute 몫 ~7%. 최대 단일
op `linear_196` = lm_head (151936×2048 fp32 ≈ 1.24 GB) 2.64 ms = step의 17%. step당
스트리밍 ~6.9 GB / 15.2 ms ≈ 450 GB/s 유효.

함의: decode는 가중치 바이트에 비례. 16-bit weight면 step 최대 ~2배, lm_head만
저정밀화해도 ~8%. prefill/audio tower는 compute-bound고 전체 7%라 우선순위 낮음.

## 사례: 서빙 (vllm-rbln, 3초 클립, N=3 폐루프)

| | chunk 1024 | chunk 128 |
|---|---:|---:|
| prefill span p50 | 176 ms (63 token인데 1024 패딩 전부 계산) | 22 ms |
| device busy 내역 | prefill 61.5% / decode 36.8% / audio 1.4% | decode 79.4% / prefill 17.0% / audio 3.0% |
| 같은 40초 처리 요청 | 77 | 155 |

→ "KV 9%인데 Waiting>0", "처리량이 N에 아선형"의 원인은 device 포화였고 주범은
prefill 패딩. 칩당 동시 한계 2 → 9 (RTF 0.5 기준).

## 사례: decoder batch bucket 사다리 (1/2/4/8/16/32)

| 실행 행 수 | 1 | 4 | 8 | **9** | 16 |
|---|--:|--:|--:|--:|--:|
| step ms | 15.5 | 17.2 | 18.9 | **26.4** | 28.0 |

9행이 16행 버킷으로 패딩되어 KV 읽기 2배 → 40% 점프. 운영 동시성은 버킷 경계에.

## 사례: speculative decoding 비용 구조

verify(5 token/행)는 1-token decode 대비 +7~19%만 비싸다(DMA-bound라 예상대로). 비용은
draft(0.6B step 6.1~6.4 ms × K)와 요청당 draft prefill(+11.6 ms)에 있다. 배치-1 1.51x,
서빙 N≥4에서는 prefill 직렬화와 배치 파편화로 손해.

## 사례: host sampler

`[b,1,151936]` float32 logits 전송이 비용의 실체. 샘플링 b=1 0.2 ms → b=16 1.2 ms
(step의 2~4%). 그래프 argmax fusion의 상한도 그만큼. 포화 전 p50 −4~5%, 포화 후 무효.
