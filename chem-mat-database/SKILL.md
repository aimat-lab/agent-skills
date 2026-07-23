---
name: chem-mat-database
description: >-
  Discover, download, and load chemistry & materials-science datasets from the
  ChemMatData database using the chem_mat_data package (PyPI: chem_mat_database)
  — both its `cmdata` command-line interface and its Python loading API. Covers
  browsing the catalog (`cmdata list/info/stats`), downloading raw or processed
  datasets, and loading them programmatically as pandas DataFrames
  (`load_smiles_dataset`), GNN-ready graph dicts (`load_graph_dataset`), 3D
  structures (`load_xyz_dataset`), or transition-metal complexes
  (`load_tmc_dataset`), plus PyG/Jraph conversion, streaming datasets, and cache
  management. Use whenever the user wants a molecular/materials benchmark
  dataset (clintox, esol, qm9, tox21, bace, lipophilicity, tmqm, …), asks to
  "download/load a dataset of molecules", mentions ChemMatData / chem_mat_data /
  cmdata, or needs SMILES+targets data to feed a model. For *training* a GNN on
  the data, hand off to the `mol-gnn` skill.
compatibility: >-
  Pure data access, machine-independent. Needs `chem_mat_database` on PyPI
  (imported as `chem_mat_data`), Python 3.9–3.12. Works out of the box against
  the public default file-share — no credentials required to read/download.
  torch + torch_geometric (or jax + jraph) are OPTIONAL extras, needed only to
  convert graphs to PyG/Jraph. The runnable `scripts/explore.py` declares its
  deps inline and runs with `uv run`.
metadata:
  domain: computational-chemistry / materials-science / ai
  tool: chem_mat_data
---

# chem-mat-database — get datasets out of ChemMatData

**ChemMatData** is a curated database of chemistry and materials-science
datasets, packaged in ML-ready form (especially for graph neural networks). This
skill is the **consumer / data-access** side: *find* a dataset, *download* it,
and *load* it into Python in whatever format you need. It is deliberately scoped
to reading data — it does **not** create or upload datasets, and it does **not**
train models.

- **To train a GNN** on a dataset you loaded here → use the **`mol-gnn`** skill
  (it covers featurizing your own SMILES CSV and the full training loop). This
  skill stops at "you have the data in memory / on disk".
- **Package naming (important):** install `chem_mat_database` from PyPI, but
  **import `chem_mat_data`** (underscore). The CLI command is `cmdata`.

There is a **complete, runnable reference** at
[`scripts/explore.py`](scripts/explore.py) — a self-contained `uv` script that
walks the whole consumer surface (discover → inspect → load raw → load graph →
optional PyG conversion). Read/adapt it before writing loader code from scratch.

## Before you start

1. **Install.** `pip install chem_mat_database` (or add it to the project). This
   pulls in RDKit, NumPy, pandas. Python must be **3.9–3.12** (`requires-python
   = ">=3.9,<3.13"`).
2. **No credentials needed to read.** The package ships pointing at a **public**
   file-share, so `cmdata list` and every loader work immediately after install.
   You do **not** need a `.env`, an account, or a password to download datasets.
3. **PyG/Jraph are optional.** `torch` + `torch_geometric` (or `jax` + `jraph`)
   are *not* installed by `chem_mat_database`. You only need them to convert
   graph dicts into framework tensors — plain loading (`load_smiles_dataset`,
   `load_graph_dataset` → list of dicts) needs neither.
4. **Two ways in, same data:** the **`cmdata` CLI** (great for browsing and
   one-off downloads) and the **Python API** (for use inside code). They share
   the same local cache.

## Two interfaces at a glance

| Task | CLI | Python API |
|------|-----|------------|
| Browse the catalog | `cmdata list` | `get_file_share(Config()).fetch_metadata()["datasets"]` |
| Dataset details | `cmdata info NAME` | `load_dataset_metadata(NAME)` |
| Molecule statistics | `cmdata stats NAME` | — (CLI only) |
| Download to disk | `cmdata download NAME` | any `load_*` call downloads on demand |
| Load raw SMILES table | — | `load_smiles_dataset(NAME)` → `DataFrame` |
| Load processed graphs | — | `load_graph_dataset(NAME)` → `list[dict]` |
| Load 3D structures | — | `load_xyz_dataset(NAME)` → `DataFrame` of RDKit Mols |
| Load TMC (metal complexes) | — | `load_tmc_dataset(NAME)` → `DataFrame` |
| Manage the local cache | `cmdata cache {list,info,remove,clear}` | — |

## 1 · Discover what's available

```bash
cmdata list              # table: name, category, description, #compounds, #targets, REG/CLS
cmdata list --sort       # sort by name
cmdata info clintox      # detailed metadata for one dataset
cmdata stats esol        # download + compute molecular stats (sizes, elements,
                         # rings, Lipinski, diversity); --sample N for big sets
```

There are ~40+ datasets in two categories: **`organic`** (SMILES-based small
molecules — `clintox`, `esol`, `tox21`, `bace_cls/reg`, `lipophilicity`,
`qm9`, `hiv`, `bbbp`, `sider`, `toxcast`, …) and **`tmc`** (transition-metal
complexes — `tmqm`, `tmqmg`, `kulik_spin`, `electrum_oxstate`). Each dataset is
either regression (**REG**) or classification (**CLS**), with one or more target
columns. A snapshot catalog lives in
[`references/datasets.md`](references/datasets.md) — but always trust a live
`cmdata list` over the snapshot, since the remote catalog changes.

## 2 · Download (optional — loaders auto-download)

```bash
cmdata download clintox                 # -> ./clintox.csv (raw form)
cmdata download clintox --full          # both raw (.csv) and processed graph (.mpack)
cmdata download clintox --path /data    # choose the destination folder
```

Downloads are **cached** (see §6), so a later `load_*` call for the same dataset
does not re-fetch. You usually don't need to download manually — the Python
loaders download-then-cache on first use.

## 3 · Load in Python — pick your format

Every loader takes the dataset **name** and returns the data directly. They all
accept `folder_path=` (where files land, default = temp dir) and `use_cache=True`.

**Raw / tabular (SMILES + targets)** → a `pandas.DataFrame`:

```python
from chem_mat_data import load_smiles_dataset

df = load_smiles_dataset("clintox")
# columns: 'smiles' + one column per target (e.g. 'FDA_APPROVED', 'CT_TOX')
```

**Processed / graph (GNN-ready)** → a `list[dict]`, one graph per molecule,
already featurized (44-dim atom features, 14-dim bond features by default):

```python
from chem_mat_data import load_graph_dataset

graphs = load_graph_dataset("clintox")     # list of graph dicts
g = graphs[0]
# keys: node_indices, node_attributes (N,44), edge_indices (E,2),
#       edge_attributes (E,14), graph_labels, graph_attributes,
#       graph_repr (SMILES), node_atoms, edge_bonds
```

See [`references/graph-format.md`](references/graph-format.md) for the full field
reference and the PyG/Jraph conversion.

**3D structures (xyz bundles — materials / conformers)** → a `DataFrame` whose
`mol` column holds RDKit `Mol` objects **with 3D coordinates**:

```python
from chem_mat_data import load_xyz_dataset

df = load_xyz_dataset("qm9")               # columns: 'id', 'mol', + targets
mol = df.iloc[0]["mol"]                     # RDKit Mol with a 3D conformer
```

**Transition-metal complexes (decomposed TMC format)** → a `DataFrame` with the
metal center, ligand SMILES, and coordination metadata:

```python
from chem_mat_data import load_tmc_dataset

df = load_tmc_dataset("tmqmg")
# columns include metal identity, ligand_smiles (list), connecting_atom_indices
# (list) — JSON list columns are parsed to Python lists automatically.
```

## 4 · Convert graphs to PyTorch Geometric / Jraph

Only needed if you'll feed a model. Requires the optional extras installed.

```python
from chem_mat_data import load_graph_dataset, pyg_data_list_from_graphs

graphs = load_graph_dataset("clintox")
data_list = pyg_data_list_from_graphs(graphs)   # list[torch_geometric.data.Data]
# each Data has x, edge_index, edge_attr, y
```

For JAX: `from chem_mat_data.main import jraph_from_graph,
jraph_implicit_batch_from_graphs`. Handing the `data_list` to a training loop is
the **`mol-gnn`** skill's job — don't reimplement training here.

## 5 · Large datasets — stream instead of loading all at once

For datasets too big to hold in memory, use the streaming classes (they yield
one item at a time and can process graphs in parallel worker processes):

```python
from chem_mat_data import SmilesDataset, GraphDataset

# yields (smiles, target_array) tuples, one row at a time
for smiles, targets in SmilesDataset("esol",
                                      smiles_column="smiles",
                                      target_columns=["measured log solubility in mols per litre"]):
    ...

# yields featurized graph dicts; num_workers>0 processes them in parallel
ds = GraphDataset("esol", num_workers=4, target_columns=["..."])
for graph in ds:
    ...
ds.close()   # release worker processes when done
```

`GraphDataset` auto-detects CSV (SMILES) vs xyz-bundle (3D) datasets.
`ShuffleDataset` wraps a streaming dataset to shuffle within a buffer.

## 6 · Cache management

Downloads are cached in an OS-specific user cache dir (Linux:
`~/.cache/chem_mat_data`). Inspect and prune it:

```bash
cmdata cache info      # location, total size, #datasets, #files
cmdata cache list      # which datasets are cached
cmdata cache remove NAME
cmdata cache clear     # wipe everything (frees disk; re-downloads next time)
```

To bypass the cache in code, pass `use_cache=False` to any loader (forces a
re-download).

## 7 · Configuration (rarely needed)

```bash
cmdata config show     # current settings: remote file-share URL, cache location
cmdata config edit     # open the config TOML in your editor
```

The config file lives in the user config dir (Linux:
`~/.config/chem_mat_data/config.toml`). The **default remote is public**, so you
normally never touch this.

> **⚠️ Security — do not echo or commit config secrets.** `cmdata config show`
> prints the *entire* config file, which on a contributor's machine may contain
> private credentials (a Nextcloud DAV username/password, API/OAuth tokens for
> the optional discovery/agent features). When helping a user, **never** paste
> that output into chat, a commit, an issue, or a shared artifact, and never copy
> real credentials into this skill. Redact to placeholders
> (`dav_password = "<REDACTED>"`). Reading/downloading datasets needs none of
> these secrets.

## Verifying success

- `cmdata list` prints a table of datasets (needs network for the first fetch).
- A loader returns a non-empty `DataFrame` / `list` and the file appears under
  `cmdata cache list`.
- Smoke test with the runnable script:
  ```bash
  uv run scripts/explore.py --list           # catalog
  uv run scripts/explore.py --dataset esol    # discover→raw→graph on one dataset
  ```

## Common pitfalls

- **Import name ≠ install name.** `pip install chem_mat_database`, but
  `import chem_mat_data`. The CLI is `cmdata` (management CLI `cmmanage` is
  out of scope for this skill).
- **PyG/Jraph not installed.** `pyg_data_list_from_graphs` raises `ImportError`
  unless `torch` + `torch_geometric` are present — they're optional extras.
  Install them yourself; plain dict loading doesn't need them.
- **Python version.** `chem_mat_database` requires **3.9–3.12** (`<3.13`
  excludes 3.13). If dependency resolution fails, check your interpreter.
- **First call needs network.** Loaders/`cmdata list` fetch from the remote on a
  cache miss. After that they work offline from `~/.cache/chem_mat_data`.
- **`load_graph_dataset` default folder is the CWD** (it writes the `.mpack`
  there); pass `folder_path=` to control where files land. The cache is separate
  and always used.
- **Don't confuse "raw" vs "processed".** Raw = CSV/SMILES (`load_smiles_dataset`);
  processed = pre-featurized graphs (`load_graph_dataset`). `cmdata download
  --full` fetches both.
- **Never expose config secrets** (see §7).

## References

- [`scripts/explore.py`](scripts/explore.py) — runnable `uv` tour of the whole
  consumer API. Read/copy it first.
- [`references/datasets.md`](references/datasets.md) — snapshot of the dataset
  catalog and the two categories (organic / tmc). Trust live `cmdata list` over
  this.
- [`references/graph-format.md`](references/graph-format.md) — the graph-dict
  schema and PyG/Jraph conversion in detail.
- Sibling skill **`mol-gnn`** — training a GNN on data loaded here.
- Docs: https://the16thpythonist.github.io/chem_mat_data ·
  PyPI: https://pypi.org/project/chem_mat_database/ ·
  uv scripts: https://docs.astral.sh/uv/guides/scripts/
