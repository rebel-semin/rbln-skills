#!/usr/bin/env bash
# Scaffold a new skill directory in the rbln-skills repository.
set -euo pipefail

usage() {
  cat <<'USAGE'
new-skill.sh — scaffold a skill in rbln-skills

Usage:
  new-skill.sh <skill-name> [--root <repo-root>] [--force]

Arguments:
  <skill-name>   kebab-case, becomes skills/<skill-name>/ and the command name
                 (e.g. rbln-compile-debug -> /rbln-skills:rbln-compile-debug)

Options:
  --root DIR     repository root (default: current directory)
  --force        overwrite an existing SKILL.md
  -h, --help     show this message

Creates:
  skills/<skill-name>/SKILL.md
  skills/<skill-name>/references/.gitkeep
  skills/<skill-name>/scripts/.gitkeep

After scaffolding, fill in the description (it is the only thing Claude reads
when deciding to load the skill) and add the skill to the README table.
USAGE
}

name=""
root="$PWD"
force=0

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --force)   force=1; shift ;;
    --root)    root="${2:?--root needs a directory}"; shift 2 ;;
    -*)        echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    *)         if [ -n "$name" ]; then echo "unexpected argument: $1" >&2; exit 2; fi
               name="$1"; shift ;;
  esac
done

if [ -z "$name" ]; then
  usage >&2
  exit 2
fi

if ! printf '%s' "$name" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$'; then
  echo "error: skill name must be kebab-case (got: $name)" >&2
  exit 1
fi

if [ ! -d "$root/skills" ]; then
  echo "error: $root/skills not found — run from the rbln-skills repo root or pass --root" >&2
  exit 1
fi

dir="$root/skills/$name"
if [ -e "$dir/SKILL.md" ] && [ "$force" -eq 0 ]; then
  echo "error: $dir/SKILL.md already exists (use --force to overwrite)" >&2
  exit 1
fi

mkdir -p "$dir/references" "$dir/scripts"
touch "$dir/references/.gitkeep" "$dir/scripts/.gitkeep"

cat > "$dir/SKILL.md" <<TEMPLATE
---
name: $name
description: >-
  TODO — what this skill does, then when to use it. Name the concrete triggers:
  tool names, exact error strings, file extensions, device generations.
  This one line is all Claude reads when deciding whether to load the skill.
---

# TODO: title

## When this applies

TODO — the situation, stated so someone can tell in one glance whether they are
in it.

## Procedure

1. TODO — what to run.
2. TODO — what the output means.
   - If <A>: TODO
   - If <B>: read [references/TODO.md](references/TODO.md), then TODO

## Done when

TODO — the condition that makes this finished. Without it the skill never stops.

## Known versions

TODO — driver / rebel-compiler / SDK versions these steps were verified against,
and the device generation (ATOM, ATOM+, REBEL). Move the table to references/
once it grows.
TEMPLATE

echo "created $dir/SKILL.md"
echo "next: fill in the description, then add the skill to README.md"
