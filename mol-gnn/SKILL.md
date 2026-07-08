---
name: mol-gnn
description: >-
  Train graph neural networks (GNNs) for molecular property prediction with
  PyTorch Geometric, using the chem_mat_data library to featurize molecules
  (SMILES -> graph). Covers turning a CSV of SMILES + target columns into PyG
  Data objects via MoleculeProcessing, choosing an architecture (GCN/GAT/GIN
  benchmarks vs the recommended GIN/GINE/GATv2), and training with a PyTorch
  Lightning loop for both regression and classification (single- or
  multi-target). Use whenever the user wants to train or fine-tune a GNN on
  molecules, predict a molecular property from SMILES, featurize molecules into
  graphs, or mentions PyTorch Geometric / PyG, message passing, GINEConv /
  GATv2Conv, chem_mat_data / MoleculeProcessing, or a SMILES+targets dataset.
compatibility: >-
  Local single-GPU (or CPU). Needs the runnable script's deps (chem_mat_database,
  torch, torch_geometric, lightning, torchmetrics); scripts/train.py declares
  them inline and is run with `uv run`. chem_mat_database requires Python 3.9-3.11.
metadata:
  domain: ai / computational-chemistry
  tool: pytorch-geometric
---

# mol-gnn — training GNNs for molecular property prediction

This skill trains a graph neural network to predict properties of molecules from
their SMILES strings, using **PyTorch Geometric** for the model and
**`chem_mat_data`** for the molecule→graph featurization. It is scoped to
**local single-GPU (or CPU) training** on **your own datasets** (a CSV of SMILES
plus one or more target columns).

The whole pipeline is:

```
CSV (smiles, target...)  ->  MoleculeProcessing.process()  ->  graph dict
     ->  pyg_data_list_from_graphs()  ->  PyG Data (x, edge_index, edge_attr, y)
     ->  DataLoader  ->  Lightning GNN  ->  train / eval / checkpoint
```

There is a **complete, runnable reference implementation** at
[`scripts/train.py`](scripts/train.py). Prefer reading and adapting it over
writing a training loop from scratch — it is a self-contained `uv` script and
already handles both regression and classification, single- and multi-target.

> **On pycomex:** `chem_mat_data` pulls in `pycomex` as a transitive dependency,
> so it *is* installed. This skill deliberately does **not** use it — no part of
> the workflow is structured as a pycomex experiment. Ignore it.

## Before you start

1. **`uv` is the runner.** `scripts/train.py` carries [PEP 723 inline
   metadata](https://docs.astral.sh/uv/guides/scripts/) declaring its
   dependencies, so you just run `uv run scripts/train.py ...` and uv builds the
   environment. No manual `pip install`, no venv to activate.
2. **Python is pinned to 3.11.** `chem_mat_database` declares
   `requires-python = ">=3.9,<=3.12"`, and that `<=3.12` (PEP 440) actually
   *excludes* 3.12.x point releases — so the script requests `>=3.11,<3.12`.
   Don't "modernize" this to 3.12 or resolution breaks.
3. **PyTorch defaults to CPU wheels** in the script for portability. For GPU,
   edit the index URL in the inline metadata (see "Running the script"). The
   Lightning `Trainer` uses `accelerator="auto"`, so it uses the GPU as soon as
   torch can see one.
4. **Have a dataset**: a CSV with a SMILES column (default name `smiles`) and one
   or more numeric target columns. See [`assets/example.csv`](assets/example.csv)
   for the expected shape (columns `smiles, logp, active, aromatic`).

## Featurization with chem_mat_data

This is the heart of the skill — a **consistent, reusable** SMILES→graph
conversion instead of hand-rolled RDKit code.

**The API** (note the import paths — `MoleculeProcessing` is *not* exported at
the top level):

```python
from chem_mat_data import pyg_data_list_from_graphs      # top-level
from chem_mat_data.processing import MoleculeProcessing   # submodule

processing = MoleculeProcessing()
graph = processing.process(
    "c1ccccc1O",                  # SMILES (or an RDKit Mol)
    double_edges_undirected=True, # make bonds bidirectional — you almost always want this
    graph_labels=[1.46],          # the row's target(s); becomes Data.y
)
data = pyg_data_list_from_graphs([graph])[0]   # -> torch_geometric.data.Data
```

**What you get.** `process()` returns a *graph dict*; `pyg_data_list_from_graphs`
converts each into a PyG `Data` with:

| attribute    | meaning                                                        |
|--------------|----------------------------------------------------------------|
| `x`          | node (atom) features — default **44 dims** per atom             |
| `edge_index` | `(2, num_edges)` connectivity (bidirectional if you set the flag) |
| `edge_attr`  | edge (bond) features — default **14 dims** per edge             |
| `y`          | graph label(s) from `graph_labels` (present only if you pass them) |
| `pos`        | 3D coordinates — only if `use_node_coordinates=True`           |

The default atom features are a one-hot of element plus hybridization, degree,
H-count, mass, formal charge, aromaticity, ring membership, and Crippen logP
contributions; edges encode bond type and related flags.

**Two gotchas that the reference script already handles:**

- **`y` shape / batching.** `process(graph_labels=[t1, t2])` gives `Data.y` of
  shape `(num_targets,)`. PyG's default collation concatenates `y` along dim 0,
  which scrambles multi-target batches. Reshape each to `(1, num_targets)`
  (`data.y = data.y.view(1, -1)`) so a batch becomes `(batch_size, num_targets)`.
- **Bad SMILES.** `Chem.MolFromSmiles` can return `None`/raise; wrap `process()`
  in try/except and skip unparseable rows rather than crashing the run.

**Customizing the features.** Subclass `MoleculeProcessing` and override the
`node_attribute_map` / `edge_attribute_map` class dicts — each entry maps a
feature name to a `callback` that extracts it from the RDKit atom/bond. Use the
same subclass for the whole dataset so the feature layout stays consistent.
Determine `node_dim`/`edge_dim` at runtime from `data.x.shape[1]` /
`data.edge_attr.shape[1]` rather than hardcoding, so custom features just work.

**Prepackaged datasets (quickstart).** To get running without your own data,
`chem_mat_data` ships benchmark datasets already in graph form:

```python
from chem_mat_data import load_graph_dataset, pyg_data_list_from_graphs
graphs = load_graph_dataset("clintox")            # downloads + caches
data_list = pyg_data_list_from_graphs(graphs)
```

or `load_smiles_dataset("clintox")` for a raw `pandas.DataFrame` you featurize
yourself. Good for a smoke test; the main workflow targets custom CSVs.

## Choosing a model

`chem_mat_data` provides **edge features**, so prefer layers that actually use
them. The reference script exposes four via `--model`:

| `--model` | Layer          | Edge features? | Notes                                          |
|-----------|----------------|----------------|------------------------------------------------|
| `gcn`     | `GCNConv`      | no             | Vanilla benchmark. Structure only.             |
| `gin`     | `GINConv`      | no             | Vanilla benchmark. Very expressive, edge-blind.|
| `gine`    | `GINEConv`     | **yes**        | GIN that folds in bond features. Good default. |
| `gatv2`   | `GATv2Conv`    | **yes**        | Dynamic attention (improves on GAT), edge-aware.|

**Guidance to give the user:** GCN, GAT and GIN are the standard *benchmark*
GNNs, but for molecules the ones that actually make the most sense are **GIN,
GINE, or GATv2** — GIN for its expressive power, and **GINE/GATv2** because they
incorporate the bond (edge) features that `chem_mat_data` provides. Default to
`gine`; reach for `gatv2` when attention/interpretability helps.

The body in `train.py` is: input linear projection → N × (conv → BatchNorm →
ReLU → dropout) → global pooling (`mean`/`add`) readout → MLP head. Swapping the
conv type is the only thing that changes between architectures.

## Regression vs classification

Pass `--task {regression,classification}`; the number of target columns sets the
output width automatically.

|                    | regression                          | classification (binary / multi-label)      |
|--------------------|-------------------------------------|--------------------------------------------|
| head output        | raw values                          | logits                                     |
| loss               | MSE (on standardized targets)       | `binary_cross_entropy_with_logits`         |
| metrics            | MAE, RMSE, R² (in original units)   | ROC-AUC, accuracy                          |
| target handling    | standardize with train mean/std; de-standardize predictions for metrics | targets must be 0/1 |

- **Regression:** standardize targets using **training-set** statistics only,
  and de-standardize predictions before computing metrics so MAE/RMSE are in the
  original units. `train.py` does this via buffers on the module.
- **Classification** here means binary or **multi-label** (one independent 0/1
  per target column, e.g. Tox21-style) with `BCEWithLogits` + sigmoid. For
  single-label **multi-class** (mutually exclusive classes), switch the head to
  `num_classes` outputs, the loss to cross-entropy, and metrics to the
  multiclass variants — noted as an extension in the script.

## Training with PyTorch Lightning

The model is a `lightning.LightningModule`; training is a `lightning.Trainer`.
Metrics are `torchmetrics` objects logged per stage. The script wires up:
`ModelCheckpoint` (best val loss), `EarlyStopping`, a `CSVLogger`,
`ReduceLROnPlateau`, and `accelerator="auto"`. This keeps the loop boilerplate
minimal and portable — no custom training engine, no pycomex.

## Running the script

```bash
# regression on a continuous column
uv run scripts/train.py --csv assets/example.csv \
    --target-cols logp --task regression --model gine --epochs 50

# binary classification
uv run scripts/train.py --csv assets/example.csv \
    --target-cols active --task classification --model gatv2 --epochs 50

# multi-label classification (two 0/1 columns)
uv run scripts/train.py --csv assets/example.csv \
    --target-cols active,aromatic --task classification --model gine
```

Key flags: `--smiles-col`, `--hidden`, `--layers`, `--dropout`, `--pooling
{mean,add}`, `--batch-size`, `--lr`, `--val-frac`/`--test-frac`, `--patience`,
`--cache-path` (cache featurized graphs to a `.pt` so re-runs skip RDKit),
`--output-dir`. Run `uv run scripts/train.py --help` for the full list.

**GPU:** in the inline metadata block at the top of `train.py`, change the
`pytorch-cpu` index URL to your CUDA build (e.g.
`https://download.pytorch.org/whl/cu124`) or delete the `[[tool.uv.index]]` /
`[tool.uv.sources]` section entirely to use the default PyPI wheel (CUDA-enabled
on Linux). Nothing else changes — `accelerator="auto"` picks up the GPU.

**Verification:** on `assets/example.csv` (40 molecules) all four models train,
evaluate on a held-out test split, and write `best.ckpt` without error. The
metrics are meaningless at that size — it is a smoke test, not a benchmark.

## Predicting on new molecules

Training saves `best.ckpt`. To score new, unlabeled SMILES, reload it and use
Lightning's `predict` — the module's `predict_step` returns values in the
**original** target space (de-standardized for regression, probabilities for
classification), so you don't redo that by hand:

```python
import lightning as L, pandas as pd
from torch_geometric.loader import DataLoader
from chem_mat_data import pyg_data_list_from_graphs
from chem_mat_data.processing import MoleculeProcessing
from train import GNN                      # reuse the module definition

proc = MoleculeProcessing()
data = []
for s in pd.read_csv("new.csv")["smiles"]:
    g = proc.process(s, double_edges_undirected=True)
    if len(g["edge_indices"]) == 0:        # same bond-less filter as training
        continue
    data += pyg_data_list_from_graphs([g])

model = GNN.load_from_checkpoint("runs/mol-gnn/best.ckpt").eval()
preds = L.Trainer(accelerator="auto", logger=False).predict(
    model, DataLoader(data, batch_size=64))
# preds: list of (batch, num_targets) tensors, already in original units
```

**Do not** call `model(data)` directly for regression — `forward()` returns
standardized outputs; `predict_step` de-standardizes using the train-set
mean/std stored in the checkpoint.

## Splitting

The script does a **random** train/val/test split. For molecular property
prediction, a random split is optimistic: near-duplicate scaffolds leak between
train and test. For an honest estimate of generalization to *new* chemistry, use
a **scaffold split** (group by Bemis–Murcko scaffold, keep whole scaffolds on one
side). Swap `split_data` for a scaffold splitter (RDKit
`MurckoScaffold.MurckoScaffoldSmiles`, or `deepchem`'s `ScaffoldSplitter`) when
the user cares about real-world generalization.

## Gotchas

- **Import paths:** `pyg_data_list_from_graphs` is top-level; `MoleculeProcessing`
  is in `chem_mat_data.processing`. `torch`/`torch_geometric` are *not* installed
  by `chem_mat_data` (they're a dev extra) — declare them yourself (the script
  does).
- **Python 3.11 only** for `chem_mat_database` (see "Before you start"). If uv
  errors on resolution, check you didn't widen `requires-python`.
- **Undirected edges:** pass `double_edges_undirected=True` or message passing
  only flows one way along each bond.
- **Bond-less molecules** (single atoms like `"O"`, or disconnected ions like
  `"[Na+].[Cl-]"`) have no edges → an empty `edge_index` that breaks edge-aware
  layers. `train.py`'s `featurize_csv` drops them automatically (and logs the
  count); if you write your own featurization loop, filter the same way
  (`len(graph["edge_indices"]) == 0`).
- **Target standardization uses train stats only** — never fit the scaler on
  val/test, or you leak.
- **Tiny val/test + AUROC:** ROC-AUC is undefined if a split has one class only;
  on small data it can read 0.5. Not a bug, just too little data.
- **Class imbalance:** for skewed classification, add `pos_weight` to
  `BCEWithLogitsLoss` and prefer ROC-AUC/PR-AUC over accuracy.

## References

- [`scripts/train.py`](scripts/train.py) — the runnable reference (uv standalone
  script). Read it first; it is meant to be copied and edited.
- [`assets/example.csv`](assets/example.csv) — 40-molecule example with a
  continuous (`logp`) and two binary (`active`, `aromatic`) targets.
- `chem_mat_data` — featurization + datasets. Source of `MoleculeProcessing`,
  `pyg_data_list_from_graphs`, `load_graph_dataset`. On PyPI as
  **`chem_mat_database`** (imported as `chem_mat_data`).
- PyTorch Geometric: https://pytorch-geometric.readthedocs.io/ ·
  Lightning: https://lightning.ai/docs/pytorch/stable/ ·
  torchmetrics: https://lightning.ai/docs/torchmetrics/ ·
  uv scripts: https://docs.astral.sh/uv/guides/scripts/
