#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.12"
# dependencies = [
#     "chem_mat_database>=1.10.0",
#     "torch>=2.2",
#     "torch_geometric>=2.5",
#     "lightning>=2.2",
#     "torchmetrics>=1.3",
#     "pandas<2.2.2",
#     "numpy<2.0",
# ]
#
# # ---------------------------------------------------------------------------
# # PyTorch is installed from the CPU wheel index by default so this script runs
# # anywhere without a CUDA toolchain. For GPU training on your machine, change
# # the index URL below to match your CUDA version (e.g. .../whl/cu124) OR delete
# # this whole [[tool.uv.index]] / [tool.uv.sources] section to let uv pull the
# # default PyPI wheel (which is CUDA-enabled on Linux). The Trainer already uses
# # accelerator="auto", so it will use the GPU automatically once torch sees one.
# # ---------------------------------------------------------------------------
# [[tool.uv.index]]
# name = "pytorch-cpu"
# url = "https://download.pytorch.org/whl/cpu"
# explicit = true
#
# [tool.uv.sources]
# torch = [{ index = "pytorch-cpu" }]
# ///
"""
Train a graph neural network for molecular property prediction.

A self-contained, runnable reference: it goes from a CSV of SMILES + target
columns all the way to a trained, evaluated, checkpointed model. Molecules are
featurized with ``chem_mat_data``'s ``MoleculeProcessing`` (SMILES -> graph
dict -> PyG ``Data``); the model is a small configurable GNN wrapped in a
PyTorch Lightning module. It supports both regression and (binary / multi-label)
classification via ``--task``.

Run it (uv reads the inline dependency block above and builds the env itself):

    # regression on a continuous column
    uv run scripts/train.py --csv assets/example.csv \
        --target-cols logp --task regression --model gine --epochs 30

    # classification on a 0/1 column
    uv run scripts/train.py --csv assets/example.csv \
        --target-cols active --task classification --model gatv2 --epochs 30

Copy this file into your project and adapt it; it is meant to be edited.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch.nn import BatchNorm1d, Dropout, Linear, ReLU, Sequential

import lightning as L
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from lightning.pytorch.loggers import CSVLogger

from torch_geometric.loader import DataLoader
from torch_geometric.nn import (
    GATv2Conv,
    GCNConv,
    GINConv,
    GINEConv,
    global_add_pool,
    global_mean_pool,
)

# chem_mat_data featurization. NOTE: MoleculeProcessing is NOT exported at the
# top level, it lives in the ``processing`` submodule. pyg_data_list_from_graphs
# IS exported at the top level.
from chem_mat_data import pyg_data_list_from_graphs
from chem_mat_data.processing import MoleculeProcessing


# == FEATURIZATION ============================================================


def featurize_csv(
    csv_path: str,
    smiles_col: str,
    target_cols: list[str],
    cache_path: str | None = None,
) -> list:
    """
    Read ``csv_path`` and turn every row into a PyG ``Data`` object.

    Each SMILES string is processed into a graph dict by ``MoleculeProcessing``
    (atom features -> ``x``, bond features -> ``edge_attr``, bonds -> a
    bidirectional ``edge_index``), with the row's target columns attached as the
    graph label ``y``. Rows whose SMILES cannot be parsed by RDKit are skipped
    with a warning.

    ``y`` is reshaped to ``(1, num_targets)`` per graph so that PyG batching
    yields ``(batch_size, num_targets)`` instead of a flat concatenation -- this
    is what makes multi-target training work correctly.
    """
    if cache_path and Path(cache_path).exists():
        print(f"[featurize] loading cached graphs from {cache_path}")
        # weights_only=False is required to unpickle PyG Data objects on torch>=2.6
        return torch.load(cache_path, weights_only=False)

    df = pd.read_csv(csv_path)
    for col in [smiles_col, *target_cols]:
        if col not in df.columns:
            raise ValueError(
                f"column {col!r} not found in {csv_path}. "
                f"available columns: {list(df.columns)}"
            )

    # One processing instance for the whole dataset guarantees a consistent
    # feature layout. Subclass MoleculeProcessing and override node_attribute_map
    # / edge_attribute_map to customize the features (see the skill README).
    processing = MoleculeProcessing()

    data_list = []
    n_skipped = 0
    for _, row in df.iterrows():
        smiles = row[smiles_col]
        labels = [float(row[c]) for c in target_cols]
        try:
            graph = processing.process(
                smiles,
                # bidirectional edges: molecular bonds are undirected, and
                # message passing needs to flow both ways.
                double_edges_undirected=True,
                graph_labels=labels,
            )
        except Exception as exc:  # noqa: BLE001 - RDKit raises various things
            n_skipped += 1
            print(f"[featurize] skipping unparseable SMILES {smiles!r}: {exc}")
            continue

        # Skip bond-less molecules (single atoms, disconnected ions): they yield
        # an empty edge_index that breaks the edge-aware conv layers.
        if len(graph["edge_indices"]) == 0:
            n_skipped += 1
            print(f"[featurize] skipping bond-less molecule {smiles!r} (no bonds)")
            continue

        data = pyg_data_list_from_graphs([graph])[0]
        # reshape (num_targets,) -> (1, num_targets) for correct batching
        data.y = data.y.view(1, -1)
        data_list.append(data)

    if not data_list:
        raise RuntimeError("no molecules could be featurized -- check the CSV")

    print(
        f"[featurize] {len(data_list)} molecules featurized"
        f"{f', {n_skipped} skipped' if n_skipped else ''}; "
        f"node_dim={data_list[0].x.shape[1]}, edge_dim={data_list[0].edge_attr.shape[1]}"
    )

    if cache_path:
        torch.save(data_list, cache_path)
        print(f"[featurize] cached graphs to {cache_path}")

    return data_list


def split_data(
    data_list: list, val_frac: float, test_frac: float, seed: int
) -> tuple[list, list, list]:
    """Random train / val / test split of the graph list."""
    n = len(data_list)
    idx = torch.randperm(n, generator=torch.Generator().manual_seed(seed)).tolist()
    n_test = int(round(n * test_frac))
    n_val = int(round(n * val_frac))
    test_idx = idx[:n_test]
    val_idx = idx[n_test : n_test + n_val]
    train_idx = idx[n_test + n_val :]
    take = lambda ids: [data_list[i] for i in ids]  # noqa: E731
    return take(train_idx), take(val_idx), take(test_idx)


# == MODEL ====================================================================


def make_conv(kind: str, dim: int, edge_dim: int):
    """Build one message-passing layer of the requested ``kind`` (dim -> dim)."""
    if kind == "gcn":
        # Vanilla benchmark. Uses only the graph structure, ignores edge_attr.
        return GCNConv(dim, dim)
    if kind == "gin":
        # Vanilla benchmark. Expressive (WL-test power) but edge-feature blind.
        mlp = Sequential(Linear(dim, dim), ReLU(), Linear(dim, dim))
        return GINConv(mlp, train_eps=True)
    if kind == "gine":
        # GIN that *does* fold in bond features -- a sensible default for
        # molecules, since edge_attr carries bond type / conjugation / ring info.
        mlp = Sequential(Linear(dim, dim), ReLU(), Linear(dim, dim))
        return GINEConv(mlp, train_eps=True, edge_dim=edge_dim)
    if kind == "gatv2":
        # Dynamic attention (an improvement over the original GAT) and edge-aware
        # via edge_dim. concat=False keeps the output width at `dim`.
        return GATv2Conv(dim, dim, heads=4, concat=False, edge_dim=edge_dim)
    raise ValueError(f"unknown model kind: {kind!r}")


EDGE_AWARE = {"gine", "gatv2"}  # kinds that consume edge_attr


class GNN(L.LightningModule):
    """A configurable GNN + graph-pooling readout, as a Lightning module.

    Handles regression and (binary/multi-label) classification with the same
    body; only the head activation, loss, and metrics differ. For regression,
    targets are standardized using train-set statistics and predictions are
    de-standardized before metrics so they are reported in the original units.
    """

    def __init__(
        self,
        node_dim: int,
        edge_dim: int,
        num_targets: int,
        task: str,
        model: str = "gine",
        hidden: int = 128,
        layers: int = 3,
        dropout: float = 0.1,
        lr: float = 1e-3,
        pooling: str = "mean",
        target_mean: torch.Tensor | None = None,
        target_std: torch.Tensor | None = None,
    ) -> None:
        super().__init__()
        self.save_hyperparameters(ignore=["target_mean", "target_std"])
        self.task = task
        self.model = model
        self.lr = lr
        self.num_targets = num_targets
        self.uses_edge = model in EDGE_AWARE
        self.pool = global_mean_pool if pooling == "mean" else global_add_pool

        # target standardization buffers (regression only; identity otherwise)
        if target_mean is None:
            target_mean = torch.zeros(num_targets)
        if target_std is None:
            target_std = torch.ones(num_targets)
        self.register_buffer("target_mean", target_mean.float())
        self.register_buffer("target_std", target_std.float())

        # input projection -> stack of conv layers -> MLP head
        self.input_lin = Linear(node_dim, hidden)
        self.convs = torch.nn.ModuleList(
            [make_conv(model, hidden, edge_dim) for _ in range(layers)]
        )
        self.norms = torch.nn.ModuleList([BatchNorm1d(hidden) for _ in range(layers)])
        self.dropout = Dropout(dropout)
        self.head = Sequential(
            Linear(hidden, hidden), ReLU(), Dropout(dropout), Linear(hidden, num_targets)
        )

        self._build_metrics()

    # -- metrics -------------------------------------------------------------

    def _build_metrics(self) -> None:
        import torchmetrics as tm

        n = self.num_targets
        if self.task == "regression":
            def reg_bundle() -> torch.nn.ModuleDict:
                return torch.nn.ModuleDict(
                    {
                        "mae": tm.MeanAbsoluteError(),
                        "rmse": tm.MeanSquaredError(squared=False),
                        # R2Score infers the number of outputs from the data shape
                        "r2": tm.R2Score(multioutput="uniform_average"),
                    }
                )

            self.metrics = torch.nn.ModuleDict(
                {"val": reg_bundle(), "test": reg_bundle()}
            )
        else:
            from torchmetrics.classification import (
                BinaryAccuracy,
                BinaryAUROC,
                MultilabelAccuracy,
                MultilabelAUROC,
            )

            def clf_bundle() -> torch.nn.ModuleDict:
                if n == 1:
                    return torch.nn.ModuleDict(
                        {"auroc": BinaryAUROC(), "acc": BinaryAccuracy()}
                    )
                return torch.nn.ModuleDict(
                    {
                        "auroc": MultilabelAUROC(num_labels=n),
                        "acc": MultilabelAccuracy(num_labels=n),
                    }
                )

            self.metrics = torch.nn.ModuleDict(
                {"val": clf_bundle(), "test": clf_bundle()}
            )

    # -- forward / steps -----------------------------------------------------

    def forward(self, data) -> torch.Tensor:
        h = self.input_lin(data.x)
        for conv, norm in zip(self.convs, self.norms):
            if self.uses_edge:
                h = conv(h, data.edge_index, data.edge_attr)
            else:
                h = conv(h, data.edge_index)
            h = norm(h)
            h = F.relu(h)
            h = self.dropout(h)
        h = self.pool(h, data.batch)
        return self.head(h)  # (batch, num_targets), raw (logits / normalized)

    def _step(self, batch, stage: str) -> torch.Tensor:
        out = self(batch)
        y = batch.y.float()

        if self.task == "regression":
            y_norm = (y - self.target_mean) / self.target_std
            loss = F.mse_loss(out, y_norm)
            # de-standardize predictions for reporting in original units
            preds = out * self.target_std + self.target_mean
            target = y
        else:
            loss = F.binary_cross_entropy_with_logits(out, y)
            preds = torch.sigmoid(out)
            target = y.long()

        self.log(f"{stage}_loss", loss, batch_size=batch.num_graphs, prog_bar=True)

        if stage in self.metrics:
            p, t = self._shape_for_metric(preds, target)
            for name, metric in self.metrics[stage].items():
                metric.update(p, t)
                self.log(
                    f"{stage}_{name}",
                    metric,
                    prog_bar=(name in ("r2", "auroc")),
                    batch_size=batch.num_graphs,
                )
        return loss

    def _shape_for_metric(self, preds: torch.Tensor, target: torch.Tensor):
        # binary metrics want 1-D tensors; multi-target/label want (N, k)
        if self.num_targets == 1:
            return preds.view(-1), target.view(-1)
        return preds, target

    def training_step(self, batch, _):
        return self._step(batch, "train")

    def validation_step(self, batch, _):
        return self._step(batch, "val")

    def test_step(self, batch, _):
        return self._step(batch, "test")

    def predict_step(self, batch, batch_idx=0, dataloader_idx=0):
        # predictions in the ORIGINAL target space: de-standardized values for
        # regression, probabilities for classification. Use this (or
        # trainer.predict) for inference -- NOT forward(), which returns raw /
        # standardized output.
        out = self(batch)
        if self.task == "regression":
            return out * self.target_std + self.target_mean
        return torch.sigmoid(out)

    def configure_optimizers(self):
        opt = torch.optim.Adam(self.parameters(), lr=self.lr)
        sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, patience=10, factor=0.5)
        return {
            "optimizer": opt,
            "lr_scheduler": {"scheduler": sched, "monitor": "val_loss"},
        }


# == DRIVER ===================================================================


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--csv", required=True, help="CSV with a SMILES column + targets")
    p.add_argument("--smiles-col", default="smiles")
    p.add_argument(
        "--target-cols",
        required=True,
        help="comma-separated target column name(s), e.g. 'logp' or 'tox1,tox2'",
    )
    p.add_argument("--task", choices=["regression", "classification"], required=True)
    p.add_argument(
        "--model",
        choices=["gcn", "gin", "gine", "gatv2"],
        default="gine",
        help="gcn/gin are vanilla benchmarks; gine/gatv2 use bond features (recommended)",
    )
    p.add_argument("--hidden", type=int, default=128)
    p.add_argument("--layers", type=int, default=3)
    p.add_argument("--dropout", type=float, default=0.1)
    p.add_argument("--pooling", choices=["mean", "add"], default="mean")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--val-frac", type=float, default=0.1)
    p.add_argument("--test-frac", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--num-workers", type=int, default=0)
    p.add_argument("--patience", type=int, default=20, help="early-stopping patience")
    p.add_argument("--cache-path", default=None, help="optional .pt cache for graphs")
    p.add_argument("--output-dir", default="runs/mol-gnn")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    L.seed_everything(args.seed, workers=True)
    torch.set_float32_matmul_precision("medium")
    target_cols = [c.strip() for c in args.target_cols.split(",") if c.strip()]
    os.makedirs(args.output_dir, exist_ok=True)

    # 1. featurize + split ---------------------------------------------------
    data_list = featurize_csv(
        args.csv, args.smiles_col, target_cols, cache_path=args.cache_path
    )
    train, val, test = split_data(data_list, args.val_frac, args.test_frac, args.seed)
    print(f"[split] train={len(train)} val={len(val)} test={len(test)}")

    loader = lambda ds, shuffle: DataLoader(  # noqa: E731
        ds, batch_size=args.batch_size, shuffle=shuffle, num_workers=args.num_workers
    )
    train_loader, val_loader, test_loader = (
        loader(train, True),
        loader(val, False),
        loader(test, False),
    )

    # 2. target standardization (regression only) ----------------------------
    node_dim = data_list[0].x.shape[1]
    edge_dim = data_list[0].edge_attr.shape[1]
    target_mean = target_std = None
    if args.task == "regression":
        ys = torch.cat([d.y for d in train], dim=0)  # (n_train, num_targets)
        target_mean = ys.mean(dim=0)
        target_std = ys.std(dim=0).clamp_min(1e-8)

    # 3. model ---------------------------------------------------------------
    model = GNN(
        node_dim=node_dim,
        edge_dim=edge_dim,
        num_targets=len(target_cols),
        task=args.task,
        model=args.model,
        hidden=args.hidden,
        layers=args.layers,
        dropout=args.dropout,
        lr=args.lr,
        pooling=args.pooling,
        target_mean=target_mean,
        target_std=target_std,
    )

    # 4. train ---------------------------------------------------------------
    ckpt = ModelCheckpoint(
        dirpath=args.output_dir, filename="best", monitor="val_loss", mode="min"
    )
    callbacks = [ckpt]
    if len(val) > 0:
        callbacks.append(
            EarlyStopping(monitor="val_loss", mode="min", patience=args.patience)
        )
    trainer = L.Trainer(
        max_epochs=args.epochs,
        accelerator="auto",
        devices="auto",
        logger=CSVLogger(args.output_dir, name="logs"),
        callbacks=callbacks,
        log_every_n_steps=1,
        enable_model_summary=True,
    )
    trainer.fit(model, train_loader, val_loader if len(val) else None)

    # 5. evaluate on the held-out test set -----------------------------------
    print("\n[test] evaluating best checkpoint on the held-out test set")
    results = trainer.test(
        model,
        test_loader,
        ckpt_path=ckpt.best_model_path or None,
    )
    print(f"\n[done] best checkpoint: {ckpt.best_model_path}")
    print(f"[done] test metrics: {results}")


if __name__ == "__main__":
    main()
