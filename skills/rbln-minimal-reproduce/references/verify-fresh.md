# Fresh-environment verification: mechanics and fallbacks

`scripts/verify_fresh.sh` is the skill's own tool. It proves that a repro runs
with nothing but its declared deps. It is never copied into the deliverable.

```
verify_fresh.sh <repro_dir> [--device N] [--python PATH] [--clean] [-- <main.py args>]
```

Run it **inside the RBLN container** that has the driver, `rbln-smi` and
`/opt/python`. On a bare host without the SDK it exits with "rbln-smi not
found". Environment variables are passed through to `main.py` unchanged, so
set `HF_HUB_CACHE` (and `HF_HUB_OFFLINE=1` if the machine has no hub access)
on the `docker exec` / shell line, never in the script under test.

## What it does

1. Parses every `- pkg==ver` bullet from the `deps` field of `main.py`'s header
   docstring and from `README.md`. Anything else in those files is ignored, so
   the bullets must be the complete dependency list.
2. Picks an idle device from `rbln-smi`: the lowest container-visible id with
   no row in the "Context Information" table. `--device N` insists on N and
   refuses if N is busy. No idle device means exit 3 and no run.
3. Copies the repro directory into `mktemp -d` (drops `out/` and
   `__pycache__/`), so relative imports into the project tree cannot work.
4. Builds a venv from `--python` (default `/opt/python/bin/python`, else
   `python3`) and installs the deps by the first source that succeeds:

   | order | source | grade | needs |
   |---|---|---|---|
   | 1 | `https://pypi.rbln.ai/simple` | FRESH | credentials |
   | 2 | `https://pypi.rebellions.in/simple` | FRESH | credentials; times out from some networks |
   | 3 | local wheels: `$RBLN_WHEEL_DIRS` (default `/wheels`) plus `*.whl` found in the pip cache, public PyPI for everything else | FRESH | a wheel for the pinned rebel-compiler |
   | 4 | `--system-site-packages` venv; only the non-rbln deps are installed | PARTIAL | nothing |

   Public PyPI and the PyTorch CPU index (`RBLN_TORCH_INDEX`, default
   `https://download.pytorch.org/whl/cpu`) are always extra indexes, so
   `torch` resolves to the `+cpu` build instead of the CUDA wheel.
5. Runs `python main.py --device N <args>` from the copy, tees the output to
   `run.log`, and prints one summary line:

   ```
   VERIFY: grade=FRESH source=wheels device=0 exit=0 elapsed=412s log=/tmp/rbln-verify.abc/run.log
   ```

   The exit code is `main.py`'s. For an error-ending repro a non-zero exit is
   the expected outcome; read the traceback in `run.log`. The work directory is
   kept unless `--clean` is given.

## Credentials

The index steps run only if a credential source already exists:
`RBLN_PYPI_USER` + `RBLN_PYPI_PASS`, a `machine <host>` entry in `~/.netrc`,
or an index for that host in `pip config list`. The script never prompts and
never writes credentials anywhere. If the user wants a FRESH grade through the
index, they export the variables in their own shell before invoking the skill;
**do not ask for a password in the conversation** — it would be stored in the
transcript.

pip masks `user:pass@` in its own output. The script additionally masks it in
the one-line failure summary it prints.

## Reading the grade

- **FRESH** — every dependency came from an index or a wheel. This is the
  claim "works on a fresh machine with these deps".
- **PARTIAL** — the rbln packages were inherited from the current interpreter.
  The script's *code* is proven standalone (no project imports, no hidden
  paths) but installability of the pinned rbln versions is not. Say so when
  handing over.
- **NONE** (exit 4) — no environment could be built. Do not hand over.

## Known facts (verified 2026-09-09)

- ATOM-Max (RBLN-CA25) host, KMD 3.2.2, container with `/opt/python` 3.12.13,
  rebel-compiler 0.10.5.dev143, optimum-rbln 0.10.4, torch 2.10.0+cpu,
  transformers 4.57.6.
- `optimum-rbln` is on public PyPI; `rebel-compiler` is not (only the
  internal indexes or a wheel). The dev wheel
  `rebel_compiler-0.10.5.dev143+g4b9a219c.prod-cp312-…whl` in `/wheels` has
  no torch pin (torch is an extra), so torch comes from optimum-rbln's
  requirement.
- `pypi.rbln.ai` answers 401 without credentials; `pypi.rebellions.in` timed
  out from the lab network.
- `pip install --no-index --find-links /wheels rebel-compiler` fails on
  `attrs`: the wheel dir holds only the rbln packages. That is why step 3 keeps
  public PyPI as an extra index.
- End-to-end run of the Qwen3-0.6B random-init compile smoke repro
  (`max_seq_len=1024`, batch 1): install via `/wheels` + public PyPI about
  2.5 min, compile 56 s, `VERIFY: grade=FRESH source=wheels … exit=0
  elapsed=76s`, `prefill.rbln` 1.5 GB and `decoder_batch_1.rbln` 323 MB.
- The busy-device parser reads the "Context Information" table. A compile-only
  script never opens a device context, so the table stayed `N/A` throughout
  that run; the "device in use" branch has been exercised only with an
  unknown id (exit 3), not with a live runtime on another process.
- Do not edit `verify_fresh.sh` while a run is in progress: bash reads the
  script incrementally and a mid-run overwrite produced a spurious syntax error
  at the very end of an otherwise successful run.
