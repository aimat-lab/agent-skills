# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "chem_mat_database",
# ]
# ///
"""
explore.py — a runnable tour of the ChemMatData database (data-access only).

This standalone `uv` script demonstrates the whole *consumer* surface of the
``chem_mat_data`` package end to end:

  1. discover  — fetch the remote catalog and print what's available
  2. inspect   — show the metadata for one dataset
  3. load raw  — ``load_smiles_dataset`` -> pandas DataFrame (SMILES + targets)
  4. load graph— ``load_graph_dataset``  -> list of graph dicts (GNN-ready)
  5. convert   — graph dicts -> PyTorch Geometric ``Data`` (only if torch + PyG
                 are installed; they are optional extras, not required to run)

It intentionally does NOT train anything — for training a GNN on this data see
the sibling ``mol-gnn`` skill.

Run it with uv (builds the environment from the inline metadata above):

    uv run scripts/explore.py                      # full tour on 'clintox'
    uv run scripts/explore.py --list               # just print the catalog
    uv run scripts/explore.py --dataset esol        # a different dataset
    uv run scripts/explore.py --dataset qm9 --xyz    # 3D / xyz-bundle dataset

If ``chem_mat_database`` is already installed in your environment you can also
just run ``python scripts/explore.py`` — the inline metadata is only used by uv.
"""

from __future__ import annotations

import argparse
import tempfile


def list_catalog() -> None:
    """
    Fetch the remote dataset catalog and print a compact table.

    This mirrors what ``cmdata list`` does, but from the Python API so you can
    see how to enumerate datasets programmatically. The catalog is a dict keyed
    by dataset name; each value is a metadata dict.
    """
    from chem_mat_data.config import Config
    from chem_mat_data.main import get_file_share

    file_share = get_file_share(Config())
    catalog: dict = file_share.fetch_metadata()["datasets"]

    print(f"\n{len(catalog)} datasets available:\n")
    print(f"  {'name':<22} {'compounds':>10} {'targets':>8}  type")
    print(f"  {'-' * 22} {'-' * 10:>10} {'-' * 8:>8}  {'-' * 14}")
    for name in sorted(catalog):
        meta = catalog[name]
        ttype = ",".join(meta.get("target_type", [])) or "-"
        print(
            f"  {name:<22} {meta.get('compounds', '?'):>10} "
            f"{meta.get('targets', '?'):>8}  {ttype}"
        )
    print()


def inspect(dataset: str) -> None:
    """Print the metadata dict for a single ``dataset`` (like ``cmdata info``)."""
    from chem_mat_data.main import load_dataset_metadata

    meta = load_dataset_metadata(dataset)
    print(f"\n=== metadata: {dataset} ===")
    for key in ("description", "compounds", "targets", "target_type", "tags"):
        if key in meta:
            print(f"  {key:<12}: {meta[key]}")
    print()


def load_raw(dataset: str, folder: str) -> None:
    """Load the raw (SMILES + targets) form as a pandas DataFrame."""
    from chem_mat_data import load_smiles_dataset

    df = load_smiles_dataset(dataset, folder_path=folder)
    print(f"\n=== raw / SMILES form: {dataset} ===")
    print(f"  shape  : {df.shape[0]} rows x {df.shape[1]} cols")
    print(f"  columns: {list(df.columns)}")
    print(df.head(3).to_string(max_colwidth=40))
    print()


def load_graph(dataset: str, folder: str, to_pyg: bool) -> None:
    """
    Load the processed graph form (list of graph dicts) and describe the first
    graph. Optionally convert to a PyTorch Geometric ``Data`` object.
    """
    import numpy as np

    from chem_mat_data import load_graph_dataset

    graphs = load_graph_dataset(dataset, folder_path=folder)
    graph = graphs[0]
    print(f"\n=== processed / graph form: {dataset} ===")
    print(f"  {len(graphs)} graphs; first graph fields:")
    for key, value in graph.items():
        arr = np.asarray(value)
        shape = arr.shape if arr.shape else "scalar"
        print(f"    {key:<18} shape={str(shape):<10} dtype={arr.dtype}")

    if not to_pyg:
        print("\n  (pass --pyg to also convert to PyTorch Geometric Data)\n")
        return

    try:
        from chem_mat_data import pyg_data_list_from_graphs
    except Exception as exc:  # noqa: BLE001
        print(f"\n  PyG conversion unavailable: {exc}")
        print("  install the extras first, e.g.  pip install torch torch_geometric\n")
        return

    try:
        data_list = pyg_data_list_from_graphs(graphs)
    except ImportError:
        print("\n  torch / torch_geometric not installed — skipping PyG conversion.")
        print("  install them with:  pip install torch torch_geometric\n")
        return

    data = data_list[0]
    print("\n  -> converted to torch_geometric.data.Data:")
    print(f"     x={tuple(data.x.shape)}  edge_index={tuple(data.edge_index.shape)}", end="")
    if getattr(data, "edge_attr", None) is not None:
        print(f"  edge_attr={tuple(data.edge_attr.shape)}", end="")
    if getattr(data, "y", None) is not None:
        print(f"  y={tuple(data.y.shape)}", end="")
    print("\n")


def load_xyz(dataset: str, folder: str) -> None:
    """Load an xyz-bundle (3D structure) dataset as a DataFrame of RDKit Mols."""
    from chem_mat_data import load_xyz_dataset

    df = load_xyz_dataset(dataset, folder_path=folder)
    print(f"\n=== xyz / 3D form: {dataset} ===")
    print(f"  shape  : {df.shape[0]} rows x {df.shape[1]} cols")
    print(f"  columns: {list(df.columns)}")
    if "mol" in df.columns and len(df):
        mol = df.iloc[0]["mol"]
        n_atoms = mol.GetNumAtoms() if mol is not None else "?"
        print(f"  first element: {n_atoms} atoms (RDKit Mol with 3D conformer)")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="clintox", help="dataset name (see --list)")
    parser.add_argument("--list", action="store_true", help="print the catalog and exit")
    parser.add_argument("--xyz", action="store_true", help="load as an xyz/3D dataset instead")
    parser.add_argument("--pyg", action="store_true", help="also convert graphs to PyG Data")
    parser.add_argument(
        "--download-dir",
        default=tempfile.gettempdir(),
        help="where to place downloaded files (still cached globally)",
    )
    args = parser.parse_args()

    if args.list:
        list_catalog()
        return

    inspect(args.dataset)
    if args.xyz:
        load_xyz(args.dataset, args.download_dir)
    else:
        load_raw(args.dataset, args.download_dir)
        load_graph(args.dataset, args.download_dir, to_pyg=args.pyg)


if __name__ == "__main__":
    main()
