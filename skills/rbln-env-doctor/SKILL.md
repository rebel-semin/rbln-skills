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

# Checking an RBLN environment

Before any hardware work, prove device visibility, the interpreter, the versions
and the actual placement, in that order. The probe really compiles and runs a
small graph on the chip, so **never run it on a device in use.**

## When this applies

- First compile in a new container or on a new host.
- You are seeing one of: `device_count = 0`, an import failure, a version
  warning, or uncertainty about placement.
- A benchmark result needs evidence of which chip it ran on.

## Procedure

### 1. Device visibility

```bash
ls -l /dev/rsd* /dev/rbln*        # both must be present
rbln-smi                          # device table, KMD version
```

- Without `/dev/rsd0`, `rebel.device_count()` returns 0. Add `/dev/rsd0` to the
  container's device list (mounting only the rbln devices is not enough).
- Ids inside the container are **container-visible ids**. Mounting host
  `/dev/rbln16-19` makes them 0-3 inside. Renumbering a single chip to
  `/dev/rbln0` makes it always 0. Every config and flag uses the inside id.
- One ATOM-Max (RBLN-CA25) card appears as 4 logical devices, roughly 15.7 GiB
  each.

### 2. Interpreter and packages

```bash
${CLAUDE_SKILL_DIR}/scripts/env_report.sh          # prints everything below at once
```

What to confirm:

- The python that has `rebel` is usually `/opt/python/bin/python`. The system
  python3.10 gives `No module named rebel`.
- `import torch, rebel, optimum.rbln` all succeed in one process.
- If optimum-rbln and rebel-compiler have different base versions you get an
  ImportWarning. It is non-fatal on the validated combination, but **record both
  versions in the result**. Table:
  [references/versions.md](references/versions.md).
- The HF cache path is writable (`HF_HUB_CACHE`). Use a shared cache directory
  only if the container user can write to it.

### 3. Prove placement (idle devices only)

```bash
/opt/python/bin/python ${CLAUDE_SKILL_DIR}/scripts/device_probe.py --devices 0
```

It compiles a tiny graph with `compile_from_torch`, runs it through
`Runtime(device=N)`, and checks both that the output is correct and that
`rbln-smi` shows the current PID on device N's row. It prints one JSON line
(`ATOM_LAB_DEVICE_PROOF=...`); anything other than `ok: true` is a failure.

Placement rules:

- Hand-written path: `rebel.Runtime(compiled, device=N, tensor_type="pt")`.
- optimum: `rbln_device=N` or `rbln_config.device_map`.
- Do not guess at environment variables. On the validated SDK the Runtime still
  landed on device 0 despite `RBLN_DEVICE_MAP=1`.
- Serving containers (vllm-rbln) use `RBLN_DEVICES=<container id>`.
- Proving individual device placement does not validate a model's multi-device or
  tensor-parallel behaviour.

### 4. Threads and environment variables

- `RBLN_NUM_THREADS` must equal `torch.get_num_threads()` during compilation,
  otherwise you get "Global num_threads state changed while dynamo tracing".
- The RBLN runtime mutates Torch's global thread count. Capture the CPU baseline
  thread count before ATOM runs.
- On bare metal a serving engine grabs as many threads as there are cores and
  busy-polls. Running several engines requires pinning each to 4-8 physical cores
  plus their HT siblings (the chip's NUMA node) through the container's cpuset;
  vllm-rbln detects the cpuset and sizes its thread pool accordingly.
- `HF_HUB_DISABLE_XET=1` prevents large-download hangs.
- If the container user is a numeric uid, set `HOME`, `USER` and `LOGNAME` so
  Torch/getpass do not die in a pwd lookup.

### 5. Extra dependencies

To avoid breaking the pins (torch, transformers, optimum-rbln, rebel-compiler),
install model-specific packages with `pip install --no-deps <pkg>==<ver>` and
verify the import. For example `qwen-asr` needs `--no-deps` to keep
transformers 4.57.6. torchcodec needs the system ffmpeg package. Frequent
symptoms: [references/known-issues.md](references/known-issues.md).

## Done when

1. `rbln-smi` and `rebel.device_count()` both report the expected device count.
2. `torch`, `rebel` and `optimum.rbln` import under the SDK python, and both
   versions are recorded.
3. Every device you plan to use returns `ok: true` from the probe (correct output
   plus a matching `rbln-smi` PID).
4. The thread count and required environment variables are decided and reflected
   in the compile / benchmark scripts.

## Verified against

ATOM-Max (RBLN-CA25), KMD 3.2.x, rebel-compiler 0.10.5.dev143 + optimum-rbln
0.10.4 (batch-1), rebel-compiler / optimum-rbln 0.11.0.post1 + vllm-rbln 0.11.0
(serving). Python 3.12 (`/opt/python`). Detail:
[references/versions.md](references/versions.md).
