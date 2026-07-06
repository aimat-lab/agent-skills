# Agent Skills

A collection of **agent skills** for our research group working on computational
chemistry, materials science, and AI.

Each skill is a self-contained folder describing how an AI coding/research agent
(e.g. [Claude Code](https://docs.claude.com/en/docs/claude-code), but the format
is intentionally generic) should carry out a recurring task — for example
starting a new DFT calculation, submitting a job to the cluster, or setting up an
ML training run.

You pick the skills you want and install them into your local agent's skills
folder. Skills are independent: installing one does not require installing any
other.

## Repository layout

Skills live as a **flat list of folders** at the repo root. Each folder is one
skill:

```
agent-skills/
├── README.md                 ← you are here
├── CONTRIBUTING.md           ← how to write a new skill
├── _template-skill/          ← copy this to start a new skill
│   ├── SKILL.md              ← the instruction file (with frontmatter)
│   └── README.md             ← human-facing usage notes
├── xtb/                       ← run xtb / GFN-xTB / g-xTB / CREST calculations
│   ├── SKILL.md
│   ├── README.md
│   ├── references/           ← detail loaded on demand
│   └── assets/               ← example structure
└── ...
```

Folders prefixed with `_` (like `_template-skill/`) are not real skills — they
are scaffolding/templates.

## What a skill folder contains

| File        | Audience | Purpose                                                                 |
|-------------|----------|-------------------------------------------------------------------------|
| `SKILL.md`  | agent    | The skill itself: YAML frontmatter (`name`, `description`) + instructions. |
| `README.md` | human    | Short description, when to use it, and install/usage notes.             |

Optional, add only if a skill needs them:

- `scripts/` — helper scripts the skill invokes.
- `assets/` — input templates, config files, reference data the skill copies or reads.
- `references/` — longer docs the agent can load on demand.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full convention.

## Installing a skill

There is no installer — you copy or symlink the skill folder into your agent's
skills directory. For Claude Code that directory is `~/.claude/skills/`.

**Option A — copy** (simple, frozen at install time):

```bash
cp -r start-dft-calculation ~/.claude/skills/
```

**Option B — symlink** (recommended; auto-updates when you `git pull`):

```bash
ln -s "$(pwd)/start-dft-calculation" ~/.claude/skills/start-dft-calculation
```

Repeat for each skill you want. To update copied skills, re-copy after pulling;
symlinked skills update automatically.

To uninstall, remove the folder (or symlink) from `~/.claude/skills/`.

> **Note:** different agents look in different places. The skill content is
> portable; only the install location changes. Check your agent's docs for where
> it loads skills from.

## Contributing

New skills are welcome and encouraged. Start by copying `_template-skill/` and
read [`CONTRIBUTING.md`](CONTRIBUTING.md).
