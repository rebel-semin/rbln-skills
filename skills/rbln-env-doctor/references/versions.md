# 검증된 버전 조합

| 용도 | rebel-compiler | optimum-rbln | vllm-rbln | torch | transformers | Python |
|---|---|---|---|---|---|---|
| 배치-1 latency (atom-model-lab) | 0.10.5.dev143 (cp312 wheel) | 0.10.4 | — | 2.10.0+cpu | 4.57.6 | 3.12 (`/opt/python`) |
| 서빙 (vllm-rbln 이미지) | 0.11.0.post1 | 0.11.0.post1 | 0.11.0 | 이미지 내장 | 이미지 내장 | 3.12 |

- 0.10.4 ↔ 0.10.5.dev 조합은 "different base versions" ImportWarning을 낸다. 컴파일과
  추론은 정상. 결과 JSON에 두 실제 버전을 모두 기록한다.
- rebel-compiler는 Python < 3.13 wheel. 상위 pin 예: `rebel-compiler>=0.10.5.dev0,<0.12`.
- `/latest/` 공개 문서는 다른 release를 설명할 수 있다. 클래스 이름, 옵션, 기본값,
  지원 모델은 설치본 소스와 대조한다.
- 컨테이너 베이스 이미지는 드라이버 도구만 포함하고 Python SDK는 직접 설치하는 경우가
  있다. 이미지 이름과 레지스트리는 환경마다 다르니 `<RBLN_IMAGE>`로 기록.
- KMD 3.2.0~3.2.2, kernel 6.14~6.17에서 결과 재현 확인 (p50 1% 이내).

## 하드웨어 참고 (공식 스펙 기반)

| | ATOM (RBLN-CA22) | ATOM-Max (RBLN-CA25) |
|---|---|---|
| 카드 | 1 논리 device | 4 논리 device |
| 논리 device당 메모리 | 16 GB | 16 GB (실측 15.7 GiB) |
| 논리 device당 대역폭 | 256 GB/s | 256 GB/s (카드 1024 GB/s ÷ 4, 산술 분배) |
| fp16 dense | 32 TFLOPS | 32 TFLOPS/device (카드 128) |

카드 전체 값을 4로 나눈 것은 산술 envelope이며 TP=1 성능 보증이 아니다. 두 SKU를
혼동하지 않는다.
