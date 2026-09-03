---
name: rbln-skill-template
description: Scaffold and review a skill in the rbln-skills repository. Use when adding a new SKILL.md, restructuring an existing one, or checking a skill against the repo's authoring rules before opening a PR.
argument-hint: [new-skill-name]
disable-model-invocation: true
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/new-skill.sh *) Read Write Edit
---

# Authoring a skill in rbln-skills

This skill is both the template and the checklist. Copy it, gut it, keep the shape.

## 1. Scaffold

Run the bundled script from the repository root. It creates
`skills/<name>/SKILL.md` with the frontmatter already filled in:

```!
${CLAUDE_SKILL_DIR}/scripts/new-skill.sh --help
```

The skill name must be kebab-case and should read as the command someone types:
`/rbln-skills:rbln-compile-debug`, not `/rbln-skills:helper`.

## 2. Write the frontmatter

Only two fields matter for discovery:

- `name` — kebab-case, matches the directory name.
- `description` — what the skill does **and when to use it**, in that order.
  Claude reads only this line when deciding whether to load the skill, so it
  must name the concrete triggers: tool names, error strings, file extensions,
  the phrases an engineer would actually type. "Helps with RBLN" triggers on
  nothing.

Everything else is optional. Reach for these only when they earn their place:

| Field | Use it when |
|---|---|
| `disable-model-invocation: true` | The skill has side effects and must be typed, not inferred (deploy, compile-and-flash, anything that writes to a device). |
| `user-invocable: false` | Background reference material nobody should type. |
| `allowed-tools` | The skill tells Claude to run a specific bundled script, and you want no permission prompt. Scope it to that exact command. |
| `paths` | The skill only applies to certain files, e.g. `**/*.rbln`, `compile_*.py`. |
| `argument-hint` | The skill takes arguments. |

Full field reference: <https://code.claude.com/docs/en/skills#frontmatter-reference>

## 3. Write the body

Keep `SKILL.md` under roughly 500 lines. It is loaded in full whenever the
skill fires, so it pays for its length on every invocation.

Push anything long into `references/` and link to it from the body — Claude
reads those files only when it needs them. Put executable steps in `scripts/`
and have the body call them rather than restating the commands inline.

```
skills/<name>/
├── SKILL.md          # the decision procedure — short
├── references/       # long-form knowledge, loaded on demand
└── scripts/          # things to run, not things to read
```

Write the body as a procedure with a stopping condition, not as prose about
the topic. State what to check, what the answer means, and what to do next.
For RBLN work specifically, record the numbers: driver and SDK versions,
device names (`ATOM`, `ATOM+`, `REBEL`), the exact error text, the flag that
fixed it. Version-pinned facts belong in `references/`, where they are cheap
to update.

## 4. Check before opening a PR

- [ ] Directory name, `name` field, and the intended command all agree.
- [ ] `description` names at least one concrete trigger phrase or error string.
- [ ] Body is a procedure, not an essay; long material moved to `references/`.
- [ ] Every command in the body was actually run on a real RBLN host.
- [ ] No internal hostnames, tokens, customer names, or unreleased part numbers.
- [ ] `python3 -c "import json,sys;json.load(open('.claude-plugin/marketplace.json'))"` still passes if you touched the manifests.
- [ ] Skill listed in the README table.
- [ ] `version` bumped in `.claude-plugin/plugin.json` and `marketplace.json`.

Detailed conventions and the description-writing rules: see
[references/authoring-guide.md](references/authoring-guide.md).
