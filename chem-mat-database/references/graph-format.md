# Graph-dict format & framework conversion

`load_graph_dataset(name)` returns a **`list[dict]`** — one dict per molecule,
already featurized. This is the same graph representation used across the
`chem_mat_data` ecosystem (and by the `mol-gnn` skill). Each dict has these
fields (shapes shown for a 5-atom, 4-bond example):

| key                | shape        | dtype   | meaning |
|--------------------|--------------|---------|---------|
| `node_indices`     | `(N,)`       | int     | `0..N-1` atom indices |
| `node_attributes`  | `(N, 44)`    | float   | per-atom feature vector (default 44 dims) |
| `edge_indices`     | `(E, 2)`     | int     | `[src, dst]` pairs; **directed** (each bond appears once by default) |
| `edge_attributes`  | `(E, 14)`    | float   | per-bond feature vector (default 14 dims) |
| `graph_labels`     | `(T,)`       | number  | the target value(s) — `T` = number of targets |
| `graph_attributes` | `(1,)`       | float   | graph-level scalar/metadata (dataset-dependent) |
| `graph_repr`       | scalar (str)| str     | the molecule's SMILES string |
| `node_atoms`       | `(N,)`       | str     | element symbols (`'C'`, `'O'`, …) — human-readable |
| `edge_bonds`       | `(E,)`       | str     | bond symbols (`'-'`, `'='`, …) — human-readable |

`N` = number of atoms, `E` = number of edges (bonds), `T` = number of targets.

**Default node features (44 dims)** are a one-hot of element plus hybridization,
degree, H-count, mass, formal charge, aromaticity, ring membership, and Crippen
logP contributions. **Edge features (14 dims)** encode bond type and related
flags. These are produced by `chem_mat_data`'s `MoleculeProcessing`; if you need
*custom* features (subclassing `MoleculeProcessing`, overriding the attribute
maps), that's covered by the **`mol-gnn`** skill.

## Directed vs. undirected edges

The stored `edge_indices` list each bond **once** (directed). Most message-
passing GNNs want edges in **both** directions. When you featurize your own
molecules via `MoleculeProcessing.process(..., double_edges_undirected=True)`
you get both directions; the prepackaged graph datasets loaded here are already
in their stored form, and the PyG converter below preserves whatever is present.
If message passing seems to "flow one way", duplicate + flip `edge_index` (and
`edge_attr`) to symmetrize.

## Convert to PyTorch Geometric

Requires `torch` + `torch_geometric` (optional extras — install them yourself):

```python
from chem_mat_data import load_graph_dataset, pyg_data_list_from_graphs

graphs = load_graph_dataset("clintox")
data_list = pyg_data_list_from_graphs(graphs)   # list[torch_geometric.data.Data]

d = data_list[0]
d.x            # (N, 44)  node features
d.edge_index   # (2, E)   connectivity
d.edge_attr    # (E, 14)  edge features
d.y            # (T,)     graph label(s)
```

For a single graph: `from chem_mat_data.main import pyg_from_graph`.

**Multi-target `y` gotcha (from `mol-gnn`):** PyG's default collation
concatenates `y` along dim 0, which scrambles multi-target batches. Reshape each
to `(1, T)` (`data.y = data.y.view(1, -1)`) so a batch becomes `(batch_size, T)`.
The `mol-gnn` training script already handles this.

## Convert to Jraph (JAX)

Requires `jax` + `jraph`:

```python
from chem_mat_data.main import jraph_from_graph, jraph_implicit_batch_from_graphs

g = jraph_from_graph(graphs[0])                 # single GraphsTuple
batch = jraph_implicit_batch_from_graphs(graphs)  # implicitly batched
```

## When you don't need a framework

If you only need the raw arrays (e.g. your own featurization, analysis, or a
non-PyG model), just use the dict directly — it's plain NumPy arrays. No torch,
no jax required. That's the whole point of the dict form.
