# `kit-ki-toolbox` Agent Skill

A portable agent skill for querying the **KIT KI Toolbox** — an
OpenAI-compatible endpoint at `https://ki-toolbox.scc.kit.edu/api/v1` hosted on
KIT SCC infrastructure.

Key features:
- **Local-first routing** — checks the catalogue and blocks external or unknown routing by default; documented local ID conventions are a fallback when routing metadata is missing
- **`KIT_KI_API` authentication** — reads the token from the environment
- **Reference utilities** — smoke test CLI and a reusable batch client (requires Python 3.9+ and `openai`; `rich` is optional for formatted listings)
- **Progressive-disclosure docs** — `<think>` handling, JSON extraction, rate limits

---

## Directory Structure

```text
kit-ki-toolbox/
├── SKILL.md                 # Agent entry point & runbook
├── README.md                # This file — export & install guide
├── examples/
│   ├── smoke_test.py        # CLI: list models, validate token, test completion
│   └── toolbox_client.py    # Reusable client with retries, batching, JSON parsing
├── tests/
│   └── test_toolbox.py      # Offline regressions; no KIT token needed
└── references/
    ├── api_reference.md     # REST endpoint docs & model discovery
    └── patterns.md          # <think> handling, JSON extraction, concurrency tips
```

---

## Export & Install

### Global (Antigravity — all projects on this machine)

```bash
# Symlink (recommended — stays in sync with source):
ln -s "$(pwd)/.agents/skills/kit-ki-toolbox" ~/.gemini/config/skills/kit-ki-toolbox

# Or copy:
cp -r .agents/skills/kit-ki-toolbox ~/.gemini/config/skills/kit-ki-toolbox
```

### Into Another Project

```bash
mkdir -p /path/to/project/.agents/skills
cp -r .agents/skills/kit-ki-toolbox /path/to/project/.agents/skills/
```

---

## Quick Verification

```bash
export KIT_KI_API="<your-token>"

# List models and run a test completion:
python .agents/skills/kit-ki-toolbox/examples/smoke_test.py

# Or list models only:
python .agents/skills/kit-ki-toolbox/examples/smoke_test.py --list-only
```
