# Contributing a skill

This guide explains how to add a new skill to the collection. It should take a
few minutes for a simple skill.

## 1. Start from the template

```bash
cp -r _template-skill my-new-skill
```

Use a **short, descriptive, kebab-case folder name** that reads like the task,
ideally verb-first:

- ✅ `start-dft-calculation`, `submit-slurm-job`, `analyze-md-trajectory`
- ❌ `dft`, `skill1`, `MyNewSkill`

The folder name is the skill's identity — keep it stable once published.

## 2. Write `SKILL.md`

`SKILL.md` is the file the agent reads. It has two parts.

### Frontmatter (required)

A YAML block at the very top of the file:

```yaml
---
name: my-new-skill
description: >-
  One or two sentences describing what the skill does AND when the agent should
  reach for it. This is what the agent matches against, so mention concrete
  trigger terms (tool names, file types, commands, domain words).
---
```

- `name` — must match the folder name.
- `description` — the most important field. The agent decides whether to use a
  skill almost entirely from this. Lead with the capability, then the triggers.
  Include the words a user would actually say ("VASP", "relaxation", "Slurm",
  "fine-tune", "cif file", …).

### Body (the instructions)

Everything after the frontmatter is guidance for the agent. Good skills:

- **State preconditions** — what must be true / available before starting
  (loaded modules, environment, input files, credentials).
- **Give a clear procedure** — numbered steps the agent can follow.
- **Show concrete commands and file templates** — copy-pasteable, with the
  parameters that typically change called out.
- **Note pitfalls and how to verify success** — what "done" looks like, common
  errors and their fixes.
- **Stay focused** — one skill = one task. If it sprawls, split it.

Keep the main file readable; push long reference material into `references/` and
point to it ("see `references/pseudopotentials.md`").

## 3. Write the per-skill `README.md`

Short, human-facing. It should cover:

- A one-line summary.
- When to use it (and when not to).
- How to install it (copy/symlink — usually the same two lines from the root
  README, adjusted to the folder name).
- Any external dependencies (codes, modules, accounts) the user must have.

## 4. Optional supporting files

Add these subfolders only if the skill actually needs them:

- `scripts/` — executable helpers the skill calls. Keep them dependency-light
  and documented.
- `assets/` — input templates, config stubs, small reference data the skill
  copies or fills in.
- `references/` — longer docs the agent loads on demand.

## 5. Checklist before you commit

- [ ] Folder name is kebab-case and matches `name` in the frontmatter.
- [ ] `description` clearly says what the skill does and when to use it.
- [ ] Instructions are self-contained and don't assume our specific machine
      unless that's the point of the skill (if so, say so explicitly).
- [ ] `README.md` tells a human how to install and when to use it.
- [ ] No secrets, credentials, or absolute personal paths committed.
- [ ] You tried it end-to-end with an agent at least once.

## Style notes

- Prefer clarity over cleverness — these are read by both agents and humans.
- Be explicit about anything destructive or expensive (large jobs, queue costs,
  file deletion) so the agent confirms before acting.
- When a skill is specific to a particular cluster, code version, or account,
  say so at the top so it doesn't get misapplied.
