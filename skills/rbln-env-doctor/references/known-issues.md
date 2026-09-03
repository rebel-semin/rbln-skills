# 자주 만나는 증상

| 증상 | 원인 | 해결 |
|---|---|---|
| `rebel.device_count() == 0` | `/dev/rsd0` 미마운트 | `docker run --device /dev/rsd0 --device /dev/rblnN ...` |
| 컨테이너가 바로 종료 | entrypoint가 bash가 아님 / `tail -f /dev/nul` 오타 | `--entrypoint bash ... sleep infinity` |
| 3 GB 모델 다운로드 hang | HF xet 백엔드 | `HF_HUB_DISABLE_XET=1` |
| `libavutil.so.*` 없음 | torchcodec의 FFmpeg 의존 | `apt install -y ffmpeg` |
| `No module named rebel` | 시스템 python3.10 사용 | `/opt/python/bin/python` |
| optimum-rbln / rebel-compiler version mismatch ImportWarning | base version 상이 | 비치명적. 두 버전 기록 |
| `ValueError: ... model type qwen3_asr but Transformers does not recognize` | pin된 transformers가 신모델을 모름 | 모델 backend 패키지를 `--no-deps`로 설치 (transformers 업그레이드 금지) |
| `AutoTokenizer`가 tokenizer를 못 로드 (`extra_special_tokens`가 list) | transformers 버전 차이 | `tokenizers` 라이브러리로 `tokenizer.json` 직접 로드 |
| Ctrl-C 후 컨테이너에 프로세스 잔존 | `docker exec`만 종료됨 | 실행 토큰을 env로 넣고 guard가 컨테이너 child를 `pkill` |
| pwd lookup 오류 (Torch/getpass) | 숫자 uid에 /etc/passwd 항목 없음 | `-e HOME=/tmp -e USER=<name> -e LOGNAME=<name>` |
| `RBLN_DEVICE_MAP=1`을 줬는데 device 0에서 실행 | 설치 SDK가 그 변수를 소비하지 않음 | `Runtime(device=N)` / `rbln_device=N` |
| 컴파일 중 "Global num_threads state changed while dynamo tracing" | `RBLN_NUM_THREADS` ≠ torch threads | 두 값 일치, 컴파일 중 `set_num_threads` 호출 제거 |
| CPU baseline 스레드가 64로 기록 (32로 설정했는데) | ATOM 실행이 Torch 전역 스레드 변경 | ATOM 실행 전 캡처 |
| 여러 엔진 동시 실행 시 4~5배 느려짐, loadavg > CPU 수 | 엔진당 코어 수만큼 스레드 + busy-poll | `--cpuset-cpus`(물리 4~8코어+HT, 칩 NUMA node) + `--cpuset-mems` |
| 서빙 요청의 `max_tokens`가 무시됨 | transcriptions 엔드포인트 필드명 | `max_completion_tokens` |
| 서빙 엔진 기동 시 FileNotFoundError로 EngineCore 종료 | adapter가 HF snapshot(CPU 측 모듈)을 요구 | 모델 디렉터리에 `hf/hub/models--.../snapshots/*` 포함 |
| ssh 끊겨도 원격 loadgen 계속 실행 | 프로세스 분리 | 측정 전 `pgrep -af "[l]oadgen.py"` 확인 |
| 컴파일러 audio tower torch.compile 실패 (스레드) | 컴파일 스레드 env와 런타임 스레드 env 불일치 | 컴파일 시 `RBLN_NUM_THREADS == COMPILE_THREADS` |

## 컨테이너 실행 예 (자리표시자)

```bash
docker run -d --name <NAME> \
  --device /dev/rsd0 --device /dev/rbln16 --device /dev/rbln17 \
  --env HF_HUB_CACHE=/hub --env HF_HUB_DISABLE_XET=1 \
  -v <HOST_HF_CACHE>:/hub -v <WORKSPACE>:/workspace \
  <RBLN_IMAGE> sleep infinity
# 안에서 /dev/rbln16,17 은 0,1
```
