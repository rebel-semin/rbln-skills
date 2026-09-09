#!/usr/bin/env bash
# Verify that a minimal repro runs standalone: copy it to a temp dir, build a
# fresh venv, install only the pinned deps listed in its header / README, run
# main.py on one idle RBLN device, and report a grade.
#
#   verify_fresh.sh <repro_dir> [--device N] [--python PATH] [--clean] [-- <main.py args>]
#
# Grades printed on the final VERIFY: line
#   FRESH    every dep installed into an empty venv (index or local wheels)
#   PARTIAL  rbln packages inherited from the current interpreter
#            (--system-site-packages) because no index / wheel source worked
#
# Install sources, tried in order; the first that succeeds wins:
#   1. https://pypi.rbln.ai/simple         needs credentials
#   2. https://pypi.rebellions.in/simple   needs credentials
#   3. local wheels: $RBLN_WHEEL_DIRS (colon-separated, default /wheels) plus
#      any *.whl in the pip cache, with public PyPI for the rest
#   4. --system-site-packages venv, non-rbln deps installed fresh  -> PARTIAL
# Credentials come only from RBLN_PYPI_USER / RBLN_PYPI_PASS, ~/.netrc, or an
# existing pip config. Nothing here asks for them and nothing writes them.
# Public PyPI and the PyTorch CPU index are always allowed as extra indexes so
# torch resolves to the +cpu build.
#
# This script is a tool of the skill. It is never copied into a deliverable.
set -uo pipefail

PY=${RBLN_PYTHON:-/opt/python/bin/python}
[ -x "$PY" ] || PY=$(command -v python3)
DEVICE=""
CLEAN=0
REPRO=""
MAIN_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --device) DEVICE=$2; shift 2 ;;
    --python) PY=$2; shift 2 ;;
    --clean)  CLEAN=1; shift ;;
    --)       shift; MAIN_ARGS=("$@"); break ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    -*)       echo "unknown option $1" >&2; exit 2 ;;
    *)        REPRO=$1; shift ;;
  esac
done
[ -n "$REPRO" ] && [ -f "$REPRO/main.py" ] || { echo "usage: verify_fresh.sh <repro_dir> [--device N] [--python PATH] [--clean] [-- args]" >&2; exit 2; }
REPRO=$(cd "$REPRO" && pwd)

log() { printf '\n== %s\n' "$*"; }

# ---- 1. collect pinned deps from the header docstring or README bullets ------
# A bullet may follow "deps :" on the same line, so do not anchor at line start.
DEPS=$(grep -hoE '(^|[[:space:]])-[[:space:]]+[A-Za-z0-9_.-]+(\[[A-Za-z0-9_,-]+\])?==[^[:space:]]+' "$REPRO/main.py" "$REPRO/README.md" 2>/dev/null \
       | sed -E 's/^[[:space:]]*-[[:space:]]+//' | sort -u)
[ -n "$DEPS" ] || { echo "no '- pkg==ver' bullets found in main.py header or README.md" >&2; exit 2; }
RBLN_DEPS=$(printf '%s\n' "$DEPS" | grep -E '^(rebel-compiler|rebel_compiler|optimum-rbln|optimum_rbln|vllm-rbln|vllm_rbln|torch-rbln|torch_rbln)' || true)
OTHER_DEPS=$(printf '%s\n' "$DEPS" | grep -vE '^(rebel-compiler|rebel_compiler|optimum-rbln|optimum_rbln|vllm-rbln|vllm_rbln|torch-rbln|torch_rbln)' || true)
log "deps"; printf '  %s\n' $DEPS

# ---- 2. pick an idle device ---------------------------------------------------
if ! command -v rbln-smi >/dev/null 2>&1; then
  echo "rbln-smi not found: run this inside the RBLN container" >&2; exit 2
fi
SMI=$(rbln-smi 2>/dev/null)
ALL_DEV=$(printf '%s\n' "$SMI" | awk '/Context Information/{exit} /^\| *[0-9]+ /{gsub(/ /,"",$2); print $2}')
BUSY_DEV=$(printf '%s\n' "$SMI" | awk 'f && /^\| *[0-9]+ /{gsub(/ /,"",$2); print $2} /Context Information/{f=1}' | sort -u)
IDLE_DEV=$(comm -23 <(printf '%s\n' $ALL_DEV | sort -u) <(printf '%s\n' $BUSY_DEV) | sort -n)
if [ -z "$DEVICE" ]; then
  DEVICE=$(printf '%s\n' $IDLE_DEV | head -1)
  [ -n "$DEVICE" ] || { echo "no idle device (all rows in rbln-smi Context Information are in use)" >&2; exit 3; }
elif ! printf '%s\n' $ALL_DEV | grep -qx "$DEVICE"; then
  echo "device $DEVICE is not visible in this container; visible: $(echo $ALL_DEV)" >&2; exit 3
elif ! printf '%s\n' $IDLE_DEV | grep -qx "$DEVICE"; then
  echo "device $DEVICE is in use according to rbln-smi; idle: $(echo $IDLE_DEV)" >&2; exit 3
fi
log "device $DEVICE (idle: $(echo $IDLE_DEV))"

# ---- 3. isolated copy + venv ---------------------------------------------------
WORK=$(mktemp -d "${TMPDIR:-/tmp}/rbln-verify.XXXXXX")
cp -r "$REPRO" "$WORK/repro"
rm -rf "$WORK/repro/out" "$WORK/repro/__pycache__"
log "workdir $WORK (python: $PY)"

PIP_COMMON=(--disable-pip-version-check --no-input)
EXTRA=(--extra-index-url https://pypi.org/simple --extra-index-url "${RBLN_TORCH_INDEX:-https://download.pytorch.org/whl/cpu}")

have_creds_for() {  # host -> 0 if some credential source exists
  local h=$1
  [ -n "${RBLN_PYPI_USER:-}" ] && [ -n "${RBLN_PYPI_PASS:-}" ] && return 0
  grep -qs "machine $h" ~/.netrc 2>/dev/null && return 0
  "$PY" -m pip config list 2>/dev/null | grep -q "$h" && return 0
  return 1
}

all_installed() {  # every dep name must be importable by pip in the venv
  local spec name
  for spec in $DEPS; do
    name=${spec%%==*}; name=${name%%[*}
    "$WORK/venv/bin/python" -m pip "${PIP_COMMON[@]}" show "$name" >/dev/null 2>&1 || { echo "  $name missing after install"; return 1; }
  done
}

new_venv() {  # $1 = extra venv flags
  rm -rf "$WORK/venv"
  "$PY" -m venv $1 "$WORK/venv" || return 1
  "$WORK/venv/bin/python" -m pip "${PIP_COMMON[@]}" install -q --upgrade pip >/dev/null 2>&1 || true
}

try_index() {  # $1 = host
  local h=$1 url
  have_creds_for "$h" || { echo "  skip $h: no credentials (RBLN_PYPI_USER/PASS, ~/.netrc, or pip config)"; return 1; }
  if [ -n "${RBLN_PYPI_USER:-}" ]; then url="https://${RBLN_PYPI_USER}:${RBLN_PYPI_PASS}@$h/simple"; else url="https://$h/simple"; fi
  new_venv "" || return 1
  echo "  installing from $h ..."
  "$WORK/venv/bin/python" -m pip "${PIP_COMMON[@]}" install --index-url "$url" "${EXTRA[@]}" $DEPS \
      > "$WORK/pip-$h.log" 2>&1 && all_installed && return 0
  echo "  failed ($(tail -1 "$WORK/pip-$h.log" | sed -E 's#https://[^@/]+@#https://***@#g'))"; return 1
}

try_wheels() {
  local links=() d
  IFS=: read -ra dirs <<< "${RBLN_WHEEL_DIRS:-/wheels}"
  for d in "${dirs[@]}"; do [ -d "$d" ] && links+=(--find-links "$d"); done
  local cache; cache=$("$PY" -m pip cache dir 2>/dev/null || true)
  if [ -n "$cache" ] && [ -d "$cache" ]; then
    mkdir -p "$WORK/cache-wheels"
    find "$cache" -name '*.whl' -exec ln -sf {} "$WORK/cache-wheels/" \; 2>/dev/null
    [ -n "$(ls -A "$WORK/cache-wheels")" ] && links+=(--find-links "$WORK/cache-wheels")
  fi
  [ ${#links[@]} -gt 0 ] || { echo "  skip wheels: no wheel dir (RBLN_WHEEL_DIRS) and empty pip cache"; return 1; }
  new_venv "" || return 1
  echo "  installing with ${links[*]} + public PyPI ..."
  "$WORK/venv/bin/python" -m pip "${PIP_COMMON[@]}" install --index-url https://pypi.org/simple "${EXTRA[@]}" "${links[@]}" $DEPS \
      > "$WORK/pip-wheels.log" 2>&1 && all_installed && return 0
  echo "  failed ($(tail -1 "$WORK/pip-wheels.log"))"; return 1
}

try_inherit() {
  new_venv "--system-site-packages" || return 1
  echo "  rbln packages inherited from $PY; installing the rest ..."
  [ -z "$OTHER_DEPS" ] && all_installed && return 0
  "$WORK/venv/bin/python" -m pip "${PIP_COMMON[@]}" install --index-url https://pypi.org/simple "${EXTRA[@]}" $OTHER_DEPS \
      > "$WORK/pip-inherit.log" 2>&1 && all_installed && return 0
  echo "  failed ($(tail -1 "$WORK/pip-inherit.log"))"; return 1
}

log "install"
GRADE=""; SOURCE=""
for h in pypi.rbln.ai pypi.rebellions.in; do
  if try_index "$h"; then GRADE=FRESH; SOURCE="index:$h"; break; fi
done
if [ -z "$GRADE" ] && try_wheels; then GRADE=FRESH; SOURCE="wheels"; fi
if [ -z "$GRADE" ] && try_inherit; then GRADE=PARTIAL; SOURCE="system-site-packages"; fi
[ -n "$GRADE" ] || { echo "VERIFY: grade=NONE could not build an environment; logs in $WORK" >&2; exit 4; }

log "installed ($GRADE via $SOURCE)"
"$WORK/venv/bin/python" -m pip "${PIP_COMMON[@]}" list 2>/dev/null | grep -iE '^(torch|rebel|optimum|transformers|vllm)' | sed 's/^/  /'

# ---- 4. run ---------------------------------------------------------------------
log "run: python main.py --device $DEVICE ${MAIN_ARGS[*]:-}"
START=$(date +%s)
( cd "$WORK/repro" && "$WORK/venv/bin/python" main.py --device "$DEVICE" "${MAIN_ARGS[@]}" ) 2>&1 | tee "$WORK/run.log"
RC=${PIPESTATUS[0]}
ELAPSED=$(( $(date +%s) - START ))

echo
echo "VERIFY: grade=$GRADE source=$SOURCE device=$DEVICE exit=$RC elapsed=${ELAPSED}s log=$WORK/run.log"
[ -d "$WORK/repro/out" ] && { echo "out/:"; ls -la "$WORK/repro/out" | sed 's/^/  /'; }
[ "$CLEAN" -eq 1 ] && rm -rf "$WORK"
exit "$RC"
