# megan-xai skill

Train a **MEGAN self-explaining graph neural network** on a molecular dataset (a CSV of
SMILES + target values) and judge whether the resulting **explanations** are actually usable —
not just whether the prediction is good. MEGAN predicts a property *and* produces per-node/edge
importance masks across multiple explanation channels; this skill drives the full train →
diagnose → tune → deliver loop and leans on MEGAN's built-in post-training diagnostic as an
objective self-check.

## When to use it

Use it when asked to train MEGAN, build an **explainable** molecular property-prediction model,
produce **attribution/explanations** for a molecular dataset, or "train a model on this CSV of
molecules and report the explanations". It covers both **regression** and **classification**,
writing a pycomex sub-experiment, smoke-testing then running it, reading the automatic diagnostic
(`report.json` + scorecard/examples/fidelity images), tuning the explanation knobs when a run
fails its self-check, and assembling a human-facing explanation report.

Triggers include: MEGAN, self-explaining / explainable GNN, XAI on molecules, explanation
channels, importance masks / attribution, fidelity, or a SMILES-plus-targets dataset where the
*explanations* matter.

Not for: plain (non-explainable) GNN property prediction — use the `mol-gnn` skill for that; or
non-molecular graph tasks.

## Prerequisites

This skill works **inside a checkout of the `graph_attention_student` project** — the package
that implements MEGAN:

- Repo: <https://github.com/aimat-lab/graph_attention_student>
- Install: `pip install graph_attention_student` (or `pip install -e .` in a clone), Python
  `3.9–3.13`. A CUDA GPU is strongly preferred for training.

The workflow creates and runs a sub-experiment under that repo's
`graph_attention_student/experiments/` directory, so you need the project checked out with its
virtual environment active (`source .venv/bin/activate`). This skill folder does not vendor the
package — it drives it.

## What's in the folder

- `SKILL.md` — the agent instructions: validate the CSV, create the sub-experiment from the
  template, smoke-test, full run, read the diagnostic self-check, decide whether to rerun
  (validation vs. test discipline), and deliver.
- `templates/train_model__megan__TEMPLATE.py` — the pycomex sub-experiment template. Copy it into
  `graph_attention_student/experiments/`, rename per dataset, fill in every `# TODO`.
- `references/interpreting-the-report.md` — field-by-field meaning of `report.json` and the
  diagnostic images.
- `references/knobs-and-troubleshooting.md` — the failing-axis → knob mapping (`IMPORTANCE_OFFSET`
  is the primary lever), swept the honest way.
- `references/human-report.md` — how to assemble the human-facing explanation report from the run
  artifacts.

## Quickstart

Inside a `graph_attention_student` checkout (venv active):

```bash
# 1. copy the template into the experiments directory and rename it per dataset
cp templates/train_model__megan__TEMPLATE.py \
   graph_attention_student/experiments/train_model__megan__mydata.py
# 2. fill in every # TODO (CSV path, columns, DATASET_TYPE, channels, ...)
# 3. smoke test (set __TESTING__ = True), then full run (__TESTING__ = False):
python graph_attention_student/experiments/train_model__megan__mydata.py
# 4. read the diagnostic:
#    graph_attention_student/experiments/results/train_model__megan__mydata/debug/report.json
```

See `SKILL.md` for the full workflow and the tuning loop.

## Install

Copy or symlink the folder into your agent's skills directory (Claude Code:
`~/.claude/skills/`):

```bash
# symlink (recommended — auto-updates on git pull)
ln -s "$(pwd)/megan-xai" ~/.claude/skills/megan-xai
```
