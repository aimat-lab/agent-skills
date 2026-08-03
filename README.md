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

## Existing skills

The skills currently in this repo:

| Skill | Summary |
|-------|---------|
| [xtb](xtb/) | Run the Grimme group's `xtb` semiempirical tight-binding program from the command line: geometry optimization, single-point energies, vibrational frequencies and thermochemistry, and implicit solvation (ALPB/GBSA) across the GFN0/1/2-xTB and GFN-FF methods — plus the newer general-purpose g-xTB method and CREST conformer/rotamer searches. The fast, cheap route to QM on a molecule, e.g. for pre-screening geometries before DFT. |
| [chem-mat-database](chem-mat-database/) | Discover, download, and load chemistry & materials-science datasets from the **ChemMatData** database using the `chem_mat_data` package — both its `cmdata` CLI (`list`/`info`/`stats`/`download`) and its Python loaders. Pull any benchmark (clintox, esol, qm9, tox21, bace, lipophilicity, tmqm, …) as a pandas DataFrame (SMILES + targets), GNN-ready graph dicts, 3D structures, or transition-metal-complex tables, with PyG/Jraph conversion, streaming datasets for big data, and cache management. Pure data access — hands off to `mol-gnn` for training. Ships a self-contained `uv` script that tours the whole consumer API end-to-end. |
| [mol-gnn](mol-gnn/) | Train a graph neural network to predict molecular properties from a CSV of SMILES + targets, using `chem_mat_data` to featurize the molecules and PyTorch Geometric + Lightning for the model. Covers regression and classification, single- and multi-target, the model menu (GCN/GAT/GIN benchmarks vs. the recommended GIN/GINE/GATv2), train/val/test splitting, metrics, and gotchas — and ships a self-contained `uv` training script plus an example dataset that run end-to-end. |
| [megan-xai](megan-xai/) | Train a MEGAN self-explaining GNN on a SMILES + target CSV: it predicts a property *and* produces per-node/edge attribution masks across multiple explanation channels. Drives the full loop — write a pycomex sub-experiment, smoke-test, run, read the automatic post-training diagnostic self-check, tune the explanation knobs when a run fails, and assemble a human-facing explanation report. Operates inside a `graph_attention_student` checkout. |
| [md-multiatoms](md-multiatoms/) | Run molecular dynamics with ASE, scaled by the `multiatoms` package for batched, parallel dynamics on a GPU: replicate a structure into many systems and batch their force evaluations into one forward pass. Covers writing a `ModelManager` for any interatomic potential (a batched torch model, or an off-the-shelf ASE calculator like MACE/XTB/EMT), the MultiAtoms/PolyAtoms API, the setup-outside / step-inside `parallel()` rule, the minimize → equilibrate → produce workflow, and writing + analyzing trajectories (temperature, energy, RDF) — and ships a self-contained `uv` script that runs an EMT smoke test end-to-end. |
| [autoslurm](autoslurm/) | Submit and monitor Slurm jobs with AutoSlurm (the `aslurm` CLI), which packs many commands into few jobs from a YAML template config. Covers config discovery, the sweep syntax (`<[zipped]>` vs. `<{product}>`), packing tasks onto GPUs, chain jobs for work longer than the walltime, and dry-running before submit — written mainly to pre-empt AutoSlurm's silent failure modes: output that looks like it went to `/dev/null` but didn't, a sweep that ran once because the angle brackets were unquoted or missing, and a config that is ignored because a same-named one shadows it. |

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
├── chem-mat-database/         ← discover/download/load ChemMatData datasets
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/              ← runnable uv tour of the loader API
│   └── references/           ← catalog + graph-format docs
├── mol-gnn/                   ← train GNNs for molecular property prediction (PyG)
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/              ← runnable uv training script
│   └── assets/               ← example dataset
├── megan-xai/                 ← train self-explaining MEGAN GNNs + judge explanations
│   ├── SKILL.md
│   ├── README.md
│   ├── templates/           ← pycomex sub-experiment template
│   └── references/          ← diagnostic + knob docs loaded on demand
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
