---
name: rbln-minimal-reproduce
description: >-
  Turn an issue or a measurement found while working in a project directory on
  a Rebellions ATOM / RBLN NPU server into a minimal standalone reproduction:
  one top-level main.py (a small folder only when unavoidable) with a fixed
  header, argparse for model / weights / device, the original code path
  inlined at the same API layer, no setup files, pinned deps as bullets, and a
  fresh-venv run on an idle device before handoff. Use for "재현 스크립트",
  "repro 만들어", "다른 서버에서 재현", "SDK 팀에 리포트", "minimal repro",
  "standalone script", "벤치마크 재현", attaching a reproducer to a
  rebel-compiler / optimum-rbln / vllm-rbln bug report, or handing a
  benchmark or profile-trace script to a colleague on another ATOM server.
---

# Building a minimal repro

This skill owns the **form** of a reproducer: skeleton, what gets replaced,
what gets checked, how it is verified. The **content** of the body is whatever
the original code did. If a related rbln skill covers that domain (profiling,
precision, porting, compile errors), consult it before writing the body.

## When this applies

- Something happened in a working project directory on an ATOM server (an
  error, a wrong output, a latency number, a profiler trace) and it has to be
  shown to someone on another server or attached to an SDK / compiler bug
  report.
- The receiver is an internal colleague or the SDK team: they know how to
  install rbln packages, they do not know this project.

Not for: reducing a model to the smallest failing graph (that is bisection,
not packaging), or documenting a procedure with no code to run.

## Procedure

### 1. Confirm the target (the only stop)

Read the project directory and find the exact command and code path behind
what the user described. Then show, in one message, and wait for a yes:

- **what** is reproduced (the error text, the metric, or the files produced)
- **the original command** and the files it passes through
- **how the script will end** (table below)
- **weights policy** (section 4) and **single file or folder** (section 5)
- **output location**: `${RBLN_REPRO_ROOT:-$HOME/repros}/<YYYYMMDD>-<slug>/`.
  Inside a container use a mounted path (for example `/data/repros/...`) so
  the result survives the container.

Do not stop again after this. Assumptions made later go into the header's
`weights` field or the README Notes.

### 2. Classify how the script ends

The user does not pick a mode. Decide which ending the script has and shape
only the tail accordingly:

| ending | the last thing that happens | the receiver checks |
|---|---|---|
| **error** | the exception propagates: no `try/except`, no "reproduced?" logic, no message matching | the traceback type and text in stderr |
| **metric** | one line `RESULT: <metric> p50 … p95 … (<conditions>)` | the numbers; defaults 1 warmup, 5 iters |
| **artifact** | files under `--out`, then `RESULT: wrote [...]` listing them | the files exist and have plausible sizes |

A request that fits none of these (rare) still ends in one of them; pick the
closest and say so in the header `kind`.

### 3. Write `main.py` from the template

Copy `${CLAUDE_SKILL_DIR}/assets/templates/main.py` and fill it in. The shape
is fixed:

1. **Header docstring**, plain `key : value`, fields in this order:
   `kind`, `title`, then exactly one of `symptom` / `measured` / `produces`,
   then `expected`, `found on`, `weights`, `run`, `deps`. `found on` records
   NPU name, KMD, Python and the four package versions actually present when
   the issue was seen (`rebel.__version__`, `optimum.rbln.__version__`,
   `torch.__version__`, `transformers.__version__`). `deps` is a bullet list of
   `- pkg==ver`; it is the **only** dependency declaration and the verifier
   parses it.
2. **Imports**, grouped at the top.
3. **`parse_args()`** — the only function allowed. Common args `--model`,
   `--weights {random,pretrained}`, `--device`; add `--out` when files are
   written, `--new-tokens` / `--warmup` / `--iters` for timing. No
   absolute-path defaults, ever.
4. **Body**: the original path, inlined top to bottom at the **same API layer**
   it was found on (optimum class stays optimum, `compile_from_torch` stays
   `compile_from_torch`). Do not shrink layers, sequence length or batch below
   what triggered the observation; standalone-ization is the whole reduction.
5. **Ending** from the table in section 2.

Style: comments in English and only where a line needs a reason (the failing
setting, a pinned generation length). No section banners, no box drawing, no
verdict JSON, no logging setup.

### 4. Weights

| what is reproduced | first try | fall back to |
|---|---|---|
| compile error, graph conversion, segfault, runtime crash | random-init from config: `AutoModel*.from_config(AutoConfig.from_pretrained(id))` with `torch.manual_seed(0)`; re-run to confirm the same symptom | pretrained, and record why in `weights` |
| precision drift vs CPU | pretrained; public HF id preferred | local checkpoint through `--model <path>`, provenance in README |
| latency, TPOT, profiler trace | random-init; pin length with `min_new_tokens == max_new_tokens`; fixed-shape synthetic inputs (`torch.randint`, zeros) | pretrained only if the timing depends on generated content |

Whatever is chosen goes in the header `weights` field, including "symptom
re-verified" when random-init was confirmed.

### 5. Single file or folder

Default is one `main.py`. Make a folder only if one of these is true:

- the model implementation itself is needed (an L1 wrapper, a shim class that
  cannot be inlined in reasonable length)
- data files are needed (an audio clip, an image, a token dump)
- two processes are involved (a vllm-rbln server plus a client)

Folder layout: `main.py` (header keeps only `title` and `run`), `README.md`
from `${CLAUDE_SKILL_DIR}/assets/templates/README.md` carrying every header
field plus **Requirements** bullets, **Layout** (one line per file) and
**Notes** (what was replaced or removed relative to the original), and the
extra modules / `data/`. Nothing else: no `requirements.txt`, `pyproject.toml`,
`setup.sh`, `Dockerfile`, or venv. The receiver installs from the bullets.

### 6. Redaction

Before running anything, grep the deliverable:

```bash
grep -rnE '/home/|/data/|/workspace/|HF_TOKEN|hf_[A-Za-z0-9]{20,}|://[^/@ ]+:[^/@ ]+@|HF_HUB_CACHE|([0-9]{1,3}\.){3}[0-9]{1,3}' --include='*.py' --include='*.md' <repro_dir>
```

Every hit is a defect: home or project absolute paths (turn into args),
tokens and `user:pass@` index URLs (remove; write "needs HF_TOKEN" in README
if a gated model is unavoidable), hostnames, IPs and container image names
(replace with `<HOST>`, `<RBLN_IMAGE>`), hardcoded shared HF cache paths
(drop; the receiver's default cache applies). The `deps` bullets say
`(internal index)` and never name the index host.

### 7. Verify

1. **In place**, with the current interpreter, from the repro directory, on an
   idle device (`rbln-smi` "Context Information" has no row for it). This
   catches syntax and API mistakes cheaply. For an error-ending repro the
   expected outcome is the traceback.
2. **Fresh**, inside the same container:

   ```bash
   ${CLAUDE_SKILL_DIR}/scripts/verify_fresh.sh <repro_dir> [--device N] [-- <main.py args>]
   ```

   It copies the repro to a temp dir, builds a venv, installs only the `deps`
   bullets (index → local wheels → inherited, see
   [references/verify-fresh.md](references/verify-fresh.md)), runs
   `main.py --device N` and prints `VERIFY: grade=FRESH|PARTIAL …`. Pass
   caches through the environment on the command line (for example
   `HF_HUB_CACHE=/hub HF_HUB_OFFLINE=1`), not through the script.
   Credentials for the internal index come only from `RBLN_PYPI_USER` /
   `RBLN_PYPI_PASS`, `~/.netrc` or pip config; if the user wants a FRESH
   grade through the index and none exist, tell them to export the variables
   in their shell and re-invoke. **Never ask for a password in the chat.**
3. Show the user the tail of the run (traceback, `RESULT:` line, or `out/`
   listing), the `VERIFY:` line and the grade. **The user decides whether it
   passes.** Do not declare "reproduced" yourself.

If the grade is PARTIAL, say so at handoff: the code is proven standalone but
installability of the pinned rbln versions is not.

### 8. Hand over

- Folder mode: `tar -czf <dir>.tar.gz -C <parent> <dir-name>` next to the
  directory. Single file: the directory only.
- In the chat: the path, the `VERIFY:` line, the deps as bullets (the same
  list as the header), and what was replaced relative to the original.

## Done when

1. The user confirmed the target in step 1.
2. `main.py` (and README plus modules in folder mode) exist under the repros
   directory with the fixed header, `parse_args()` as the only function, and
   one of the three endings.
3. The redaction grep returns nothing.
4. `verify_fresh.sh` ran and its `VERIFY:` line plus the output tail were
   shown; the grade is stated at handoff.
5. The deps bullets were repeated in the chat; the tarball exists in folder
   mode.
6. The user judged the result.

## Verified against

ATOM-Max (RBLN-CA25), KMD 3.2.2, container `/opt/python` 3.12.13,
rebel-compiler 0.10.5.dev143, optimum-rbln 0.10.4, torch 2.10.0+cpu,
transformers 4.57.6. The template's `RBLN<Model>ForCausalLM.from_model(model,
rbln_config=RBLN<Model>ForCausalLMConfig(batch_size, max_seq_len, device))`
path and `verify_fresh.sh` were run on this combination; details in
[references/verify-fresh.md](references/verify-fresh.md).
