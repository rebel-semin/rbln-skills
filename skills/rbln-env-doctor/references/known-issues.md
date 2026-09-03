# Frequent symptoms

| Symptom | Cause | Fix |
|---|---|---|
| `rebel.device_count() == 0` | `/dev/rsd0` not mounted | add both `/dev/rsd0` and `/dev/rblnN` to the container's device list |
| container exits immediately | entrypoint is not bash, or a typo in the keep-alive command | override the entrypoint to bash and keep the container alive with `sleep infinity` |
| a multi-GB model download hangs | HF xet backend | `HF_HUB_DISABLE_XET=1` |
| `libavutil.so.*` missing | torchcodec's FFmpeg dependency | install the system ffmpeg package |
| `No module named rebel` | using the system python3.10 | `/opt/python/bin/python` |
| optimum-rbln / rebel-compiler version-mismatch ImportWarning | differing base versions | non-fatal; record both versions |
| `ValueError: ... model type <x> but Transformers does not recognize` | the pinned transformers predates the model | install the model's backend package with `--no-deps` (do not upgrade transformers) |
| `AutoTokenizer` cannot load the tokenizer (`extra_special_tokens` is a list) | transformers version difference | load `tokenizer.json` directly with the `tokenizers` library |
| processes survive in the container after Ctrl-C | only the exec client was killed | pass a run token via env and have a guard terminate the container children by that token |
| pwd lookup errors from Torch/getpass | a numeric uid with no /etc/passwd entry | set `HOME`, `USER` and `LOGNAME` in the exec environment |
| `RBLN_DEVICE_MAP=1` set, still runs on device 0 | the installed SDK does not consume that variable | `Runtime(device=N)` / `rbln_device=N` |
| "Global num_threads state changed while dynamo tracing" | `RBLN_NUM_THREADS` differs from the Torch thread count | match them and remove `set_num_threads` calls during compilation |
| CPU baseline recorded 64 threads although 32 was set | ATOM execution mutated Torch's global thread count | capture the value before ATOM runs |
| several engines together run 4-5x slower, loadavg above the CPU count | each engine takes core-count threads and busy-polls | pin each engine to 4-8 physical cores plus HT siblings on the chip's NUMA node via the container cpuset |
| a serving request's `max_tokens` is ignored | field name on the transcriptions endpoint | use `max_completion_tokens` |
| the engine core exits with FileNotFoundError at startup | the adapter expects an HF snapshot (the CPU-side modules) | include the `hf/hub/models--.../snapshots/*` tree under the model directory |
| a remote load generator keeps running after ssh drops | detached process | check for a live load generator process before measuring |
| audio-tower torch.compile fails during compilation (threads) | compile-time and runtime thread env differ | set `RBLN_NUM_THREADS` equal to the compile thread count |

## Container launch checklist (placeholders)

Whatever tooling launches the container, it must provide:

- devices: `/dev/rsd0` **and** every `/dev/rblnN` the workload uses
- env: `HF_HUB_CACHE=<cache path>`, `HF_HUB_DISABLE_XET=1`
- mounts: the HF cache and the workspace
- image: `<RBLN_IMAGE>` (driver tools only in some images; install the Python SDK
  yourself)
- a keep-alive command so the container does not exit

Remember that host `/dev/rbln16,17` appear as ids 0,1 inside the container.
