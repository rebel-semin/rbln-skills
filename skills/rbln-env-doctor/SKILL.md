---
name: rbln-env-doctor
description: >-
  Check and repair a Rebellions ATOM / RBLN NPU container or host before
  compiling or benchmarking: rebel.device_count() == 0, missing /dev/rsd0 or
  /dev/rbln*, "No module named rebel" (wrong interpreter, use /opt/python),
  optimum-rbln vs rebel-compiler version-mismatch ImportWarning,
  container-visible vs host device ids, RBLN_DEVICES / rbln_device /
  Runtime(device=N) placement proof with rbln-smi, RBLN_NUM_THREADS, HF hub
  download hangs (HF_HUB_DISABLE_XET), installing extra model deps without
  breaking pinned torch / transformers (pip --no-deps). Use on "device가 안
  보여", "rbln 컨테이너 세팅", first compile in a new container, or when a
  benchmark must prove which chip it ran on.
---

# RBLN 환경 점검

하드웨어 작업 전에 device 가시성, 인터프리터, 버전, 실제 배치를 순서대로 증명한다.
"doctor"는 실제로 작은 그래프를 컴파일해 device에서 돌리므로 **사용 중인 device에는
실행하지 않는다.**

## 적용 조건

- 새 컨테이너/호스트에서 첫 컴파일 전.
- `device_count = 0`, import 실패, 버전 경고, 배치 불확실 중 하나가 보인다.
- 벤치마크 결과에 "어느 칩에서 돌았는지" 증거가 필요하다.

## 절차

### 1. device 가시성

```bash
ls -l /dev/rsd* /dev/rbln*        # 둘 다 있어야 함
rbln-smi                          # device 표, KMD 버전
```

- `/dev/rsd0`이 없으면 `rebel.device_count()`가 0이다. 컨테이너에 `--device /dev/rsd0`
  추가 (rbln 장치만 마운트하면 부족).
- 컨테이너 안의 id는 **container-visible id**다. 호스트 `/dev/rbln16~19`를 마운트하면
  안에서는 0~3. 칩 하나만 `/dev/rblnN:/dev/rbln0`으로 재번호 마운트하면 항상 0.
  모든 config/flag는 안쪽 id를 쓴다.
- ATOM-Max(RBLN-CA25) 카드 하나는 논리 device 4개로 보인다. 논리 device당 약 15.7 GiB.

### 2. 인터프리터와 패키지

```bash
${CLAUDE_SKILL_DIR}/scripts/env_report.sh          # 아래 항목을 한 번에 출력
```

확인 항목:

- `rebel`을 가진 python은 보통 `/opt/python/bin/python`. 시스템 python3.10에서는
  `No module named rebel`.
- `import torch, rebel, optimum.rbln`이 한 프로세스에서 성공.
- `optimum-rbln`과 `rebel-compiler`의 base version이 다르면 ImportWarning이 나온다.
  검증된 조합에서는 비치명적이지만 **두 버전을 결과에 모두 기록**한다.
  버전 표는 [references/versions.md](references/versions.md).
- HF cache 경로가 쓰기 가능한지 (`HF_HUB_CACHE`). 공유 `/hub`는 컨테이너 사용자가
  쓸 수 있을 때만.

### 3. 배치 증명 (idle device에서만)

```bash
/opt/python/bin/python ${CLAUDE_SKILL_DIR}/scripts/device_probe.py --devices 0
```

작은 그래프를 `compile_from_torch`로 컴파일해 `Runtime(device=N)`으로 실행하고,
출력이 맞는지와 `rbln-smi` 출력의 device N 행에 현재 PID가 있는지 둘 다 확인한다.
JSON 한 줄(`ATOM_LAB_DEVICE_PROOF=...`)을 출력하며 `ok: true`가 아니면 실패.

배치 규칙:

- 손 작성 경로: `rebel.Runtime(compiled, device=N, tensor_type="pt")`.
- optimum: `rbln_device=N` 또는 `rbln_config.device_map`.
- `RBLN_DEVICE_MAP=1` 같은 환경변수 추측은 하지 않는다. 검증된 SDK에서 Runtime은
  여전히 device 0에 생성됐다.
- 서빙 컨테이너(vllm-rbln)는 `RBLN_DEVICES=<container id>`.
- 개별 device 배치 증명은 그 모델의 multi-device/TP 동작을 보장하지 않는다.

### 4. 스레드와 환경변수

- `RBLN_NUM_THREADS`: 컴파일 중에는 `torch.get_num_threads()`와 같아야 한다
  (다르면 "Global num_threads state changed while dynamo tracing").
- RBLN 런타임은 Torch 전역 스레드 수를 바꾼다. CPU baseline 스레드 수는 ATOM 실행
  전에 캡처.
- 서빙 엔진은 bare-metal에서 코어 수만큼 스레드를 잡고 busy-poll한다. 여러 엔진을
  띄우면 `--cpuset-cpus`로 물리 4~8코어+HT(칩의 NUMA node)에 고정해야 host가 포화하지
  않는다. vllm-rbln은 cpuset을 감지해 스레드를 맞춘다.
- `HF_HUB_DISABLE_XET=1`: 대용량 다운로드 hang 방지.
- 컨테이너 사용자가 숫자 uid면 `HOME`, `USER`, `LOGNAME`을 넣어야 Torch/getpass가
  pwd lookup에서 죽지 않는다.

### 5. 추가 의존성

핀(torch, transformers, optimum-rbln, rebel-compiler)을 깨지 않도록 모델 전용 패키지는
`pip install --no-deps <pkg>==<ver>`로 설치하고 import를 확인한다. 예: `qwen-asr`는
transformers 4.57.6 pin을 유지하기 위해 `--no-deps`. torchcodec은 `apt install ffmpeg`
필요. 자주 만나는 증상은 [references/known-issues.md](references/known-issues.md).

## 완료 조건

1. `rbln-smi`와 `rebel.device_count()`가 기대한 device 수를 보인다.
2. SDK python에서 `torch`, `rebel`, `optimum.rbln` import 성공, 두 버전 기록.
3. 사용할 device마다 probe `ok: true` (출력 정확 + rbln-smi PID 매칭).
4. 스레드 수와 필수 환경변수가 결정되어 컴파일/벤치 스크립트에 반영됐다.

## 검증 환경

ATOM-Max(RBLN-CA25), KMD 3.2.x, rebel-compiler 0.10.5.dev143 + optimum-rbln 0.10.4
(배치-1), rebel-compiler / optimum-rbln 0.11.0.post1 + vllm-rbln 0.11.0 (서빙).
Python 3.12 (`/opt/python`). 세부는 [references/versions.md](references/versions.md).
