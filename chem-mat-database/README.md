# chem-mat-database skill

**Discover, download, and load** chemistry & materials-science datasets from the
**ChemMatData** database, via both the **`cmdata` CLI** and the **`chem_mat_data`
Python API**. Pure data access — it gets you the data; it does not train models
or create/upload datasets.

## When to use it

Use it when you want a ready-made molecular or materials dataset to work with:
browse the catalog, pull down a benchmark (clintox, esol, qm9, tox21, bace,
lipophilicity, tmqm, …), and load it as a pandas DataFrame (SMILES + targets),
GNN-ready graph dicts, 3D structures, or transition-metal-complex tables — then
optionally convert to PyTorch Geometric / Jraph.

Triggers include: ChemMatData, `chem_mat_data` / `chem_mat_database`, `cmdata`,
`load_smiles_dataset` / `load_graph_dataset`, "download a dataset of molecules",
"get me a SMILES + targets benchmark", or a named dataset like `clintox`/`qm9`.

**Not for:**
- **Training** a model on the data → use the **`mol-gnn`** skill (featurization +
  GNN training). This skill hands off at "you have the data".
- **Creating or uploading** datasets (the `cmmanage` producer side) — out of scope.

## What's in the folder

- `SKILL.md` — the agent instructions: the CLI (`list`/`info`/`stats`/`download`/
  `cache`/`config`), the Python loaders (raw / graph / xyz / TMC), streaming
  datasets for big data, PyG/Jraph conversion, caching, and a security note about
  config secrets.
- `scripts/explore.py` — a self-contained **`uv` script** (PEP 723 inline deps)
  that tours the whole consumer API end to end (discover → inspect → load raw →
  load graph → optional PyG). Copy and adapt it.
- `references/datasets.md` — a snapshot of the dataset catalog (organic + tmc).
- `references/graph-format.md` — the graph-dict schema and framework conversion.

## Quickstart

```bash
# browse and pull with the CLI (after: pip install chem_mat_database)
cmdata list
cmdata info esol
cmdata download esol

# or tour the Python API with zero setup via uv
uv run scripts/explore.py --list
uv run scripts/explore.py --dataset esol
```

```python
# in code
from chem_mat_data import load_smiles_dataset, load_graph_dataset
df     = load_smiles_dataset("clintox")   # pandas DataFrame: smiles + targets
graphs = load_graph_dataset("clintox")    # list of GNN-ready graph dicts
```

## Dependencies

- **`chem_mat_database`** (PyPI) — imported as **`chem_mat_data`**; provides the
  `cmdata` CLI and the loaders. Pulls in RDKit / NumPy / pandas. **Python
  3.9–3.12.**
- **No account or credentials** are needed to read/download — the package ships
  pointing at a public file-share.
- **Optional:** `torch` + `torch_geometric` (or `jax` + `jraph`) — only to
  convert graph dicts into framework tensors. Not required for plain loading.
- For the runnable script you need **[`uv`](https://docs.astral.sh/uv/)** on your
  PATH; it builds the environment from `scripts/explore.py`'s inline metadata.

## Install

Copy or symlink the folder into your agent's skills directory (Claude Code:
`~/.claude/skills/`):

```bash
# symlink (recommended — auto-updates on git pull)
ln -s "$(pwd)/chem-mat-database" ~/.claude/skills/chem-mat-database

# or copy (frozen at install time)
cp -r chem-mat-database ~/.claude/skills/
```
