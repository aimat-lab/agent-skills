# mol-gnn skill

Train **graph neural networks for molecular property prediction** with
**PyTorch Geometric**, using the **`chem_mat_data`** library to featurize
molecules (SMILES → graph). Ships a complete, runnable reference training script.

## When to use it

Use it when you want to train (or fine-tune) a GNN that predicts a property of a
molecule from its SMILES: solubility, toxicity, activity, a computed descriptor,
etc. It covers the full path — CSV of `SMILES + targets` → featurization →
model → trained, evaluated, checkpointed GNN — for both **regression** and
**classification**, single- or multi-target, on a **local GPU or CPU**.

Triggers include: PyTorch Geometric / PyG, message passing, `GINEConv` /
`GATv2Conv`, `chem_mat_data` / `MoleculeProcessing`, "train a GNN on molecules",
"predict a molecular property", or a SMILES-plus-targets dataset.

Not for: full 3D/equivariant models on conformers (this is 2D graph-from-SMILES),
non-molecular graphs, or HPC/Slurm submission (single-machine training only —
put cluster submission in a separate skill).

## What's in the folder

- `SKILL.md` — the agent instructions: featurization with `chem_mat_data`, the
  model menu (GCN/GAT/GIN benchmarks vs recommended GIN/GINE/GATv2), the
  regression/classification switch, the Lightning training loop, splitting,
  metrics, and gotchas.
- `scripts/train.py` — a self-contained **`uv` standalone script** (PEP 723
  inline dependencies) that runs the whole pipeline. Copy and adapt it.
- `assets/example.csv` — a 40-molecule example dataset (`smiles`, `logp`,
  `active`, `aromatic`) so the script runs end-to-end out of the box.

## Quickstart

```bash
# from the skill folder; uv builds the environment from train.py's inline deps
uv run scripts/train.py --csv assets/example.csv \
    --target-cols logp --task regression --model gine --epochs 50
```

Point `--csv` at your own file and set `--smiles-col` / `--target-cols` /
`--task` accordingly. `uv run scripts/train.py --help` lists every flag.

## Dependencies

Installed automatically by `uv` from the inline metadata in `scripts/train.py`
(you don't `pip install` anything yourself):

- `chem_mat_database` (imported as `chem_mat_data`) — featurization + datasets;
  brings RDKit. **Note:** it also pulls in `pycomex` transitively — installed but
  unused by this skill.
- `torch`, `torch_geometric`, `lightning`, `torchmetrics`, `pandas`.

You do need **[`uv`](https://docs.astral.sh/uv/)** on your PATH. The script pins
**Python 3.11** (a `chem_mat_database` requirement) and installs **CPU** PyTorch
by default; switch to a CUDA wheel index in the script's header for GPU training
(one line — see `SKILL.md`).

## Install

Copy or symlink the folder into your agent's skills directory (Claude Code:
`~/.claude/skills/`):

```bash
# symlink (recommended — auto-updates on git pull)
ln -s "$(pwd)/mol-gnn" ~/.claude/skills/mol-gnn
```
