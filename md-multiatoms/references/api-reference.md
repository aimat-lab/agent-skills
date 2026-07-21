# `multiatoms` API reference

Everything an agent needs to drive the package. Concepts first, then each public
class. Import surface:

```python
from multiatoms import MultiAtoms, PolyAtoms, ModelManager, BatchedAtoms
from multiatoms.ase_md import NullLogger, SmartLangevin
```

## How the batching works (one paragraph)

Inside `with multi.parallel():`, each system runs in its own **greenlet**. When a
system calls `get_forces()` / `get_potential_energy()` it *yields* to a
cooperative `HubScheduler` instead of computing. The scheduler waits until every
live system has yielded, hands the whole collection to your `ModelManager` for
**one** batched forward pass, distributes the results, and resumes each greenlet
where it paused. Outside `parallel()` there is no scheduler in the loop —
`get_forces()` calls the model directly for that one system. This is why setup
(no force calls) can happen outside, and only stepping needs to be inside.

---

## `MultiAtoms(template, model_manager, n_systems=1)`

Owns `n_systems` replicas of one template and drives them together.

- **`template`** — an ASE `Atoms` object **or** a path (str/`Path`) to any
  ASE-readable structure file (PDB, xyz, CIF, …). Its full state — positions,
  cell, PBC, constraints, charges — is deep-copied into every system, so systems
  never share arrays.
- **`model_manager`** — a live `ModelManager` instance (see below).
- **`n_systems`** — number of parallel replicas. `1` is valid (single MD, no
  batching benefit).

### Methods & attributes

| Member | Meaning |
| --- | --- |
| `.atoms` | `list[BatchedAtoms]` — the individual systems. |
| `.n_systems` | `int`. |
| `.parallel()` | context manager; inside it, `map`/`foreach` batch force calls. |
| `.map(fn, *iterables) -> list` | apply `fn` across systems, collect results. Serial outside `parallel()`, greenlet-parallel inside. |
| `.foreach(fn, *iterables) -> None` | same, discard results. |
| `.clean_up()` | release the model / GPU resources. Call when done. |

`map`/`foreach` zip multiple iterables like the builtin `map`:
`multi.map(lambda a, i: Trajectory(f"{i}.traj", "w", a), multi.atoms, range(N))`.

### Attribute delegation (convenient but sharp)

`MultiAtoms` forwards attribute access to its systems:

- **Method call** → runs on every system, returns a list:
  `multi.get_potential_energy()` → `list[float]`,
  `multi.get_positions()` → `list[np.ndarray]`.
- **Simple property** → a list of values: `multi.positions`, `multi.cell`.
- **Assignment** → set on every system: `multi.info = {...}` sets all.
- **Array item assignment** → `multi.arrays["partial_charges"] = arr` writes into
  each system's `arrays`.

> Reading `multi.get_potential_energy()` **outside** `parallel()` is fine and
> cheap after a step (per-system position cache means no recompute if positions
> are unchanged). Inside `parallel()` it yields to the scheduler like any force
> call, so it works from monitors attached to an integrator.

---

## `BatchedAtoms`

An `ase.Atoms` subclass. You rarely construct it directly (MultiAtoms does), but
you interact with instances via `multi.atoms`. Two things to know:

- `get_forces()` / `get_potential_energy()` are overridden to yield-or-call as
  described above. Otherwise it behaves like a normal `Atoms`.
- **`.copy()` does not work** — ASE's `copy()` calls `self.__class__(...)`, and
  `BatchedAtoms.__init__` requires `model_manager`/`scheduler`. To get a plain,
  independent copy (e.g. inside a `ModelManager` to attach an ASE calculator),
  build a base `Atoms`: `plain = ase.Atoms(batched_atoms)` — this copies numbers,
  positions, cell, PBC, and constraints into a vanilla `Atoms`.

---

## `ModelManager` (abstract)

Subclass and implement `curate_batch`; override the rest only as needed. Full
recipes in [model-manager.md](model-manager.md).

```python
class ModelManager(ABC):
    def __init__(self, model, device): ...

    @abstractmethod
    def curate_batch(self, atoms_list) -> dict[str, Tensor]: ...

    def model_forward(self, batched_input) -> tuple[Tensor, Tensor]:
        # default: model(**batched_input), then model.get_forces(energy, pos)
        ...

    def post_process_hook(self, forces, energy) -> tuple[ndarray, ndarray]:
        return forces, energy            # override for unit conversion

    def clean_up(self) -> None:
        # default: model.clean_up() if it exists
        ...
```

Machinery you don't override (but should understand):

- **`compute_energy_and_forces(atoms_list)`** — the entry point the scheduler
  calls. It (1) filters out systems whose positions are unchanged since their last
  evaluation (per-system caching — you never see cached systems in
  `curate_batch`), (2) runs `_infer`, (3) distributes results, (4) refreshes the
  cache.
- **`_infer(atoms)`** = `curate_batch` → `model_forward` → to-numpy →
  `post_process_hook`. Returns `(forces, energy)` as numpy.
- **`distribute_results(...)`** — writes each system's slice into its
  `ProxyCalculator`. Standard; no need to override.

**I/O contract:** positions in Å; `model_forward` returns torch tensors —
`energy` shape `(n_systems,)` in eV, `forces` shape `(Σ n_atoms, 3)` in eV·Å⁻¹.

---

## `PolyAtoms(pdb_path, model_manager, n_systems=1, workers=2)`

Runs `workers` independent `MultiAtoms` in **separate processes** that share one
GPU force server in the main process. While one worker integrates on the CPU, the
GPU serves another worker's batch (a meaningful speedup — one worker's CPU stepping
overlaps another's GPU forward).

- **`pdb_path`** — a template path/`Atoms`, **or a list of length `workers`** so
  different workers simulate different systems on the same GPU. (Name is
  historical; any ASE-readable structure works. Pass positionally.)
- **`model_manager`** — one live manager in the main process; it must handle every
  worker's system. `PolyAtoms` owns it and calls its `clean_up()` on exit.
- **`n_systems`** — int for all workers, or a list of per-worker counts. Size each
  worker's count so its batched forward costs comparable GPU time (bigger systems
  → fewer replicas).
- **`workers`** — `K` processes. `None` → a single in-main `MultiAtoms` (no IPC);
  `1` → the real pool with one worker.

Use as a context manager, then `run` a **top-level** worker function:

```python
from multiatoms import PolyAtoms

def simulate(multi, worker_id):          # top-level so `spawn` can pickle it
    integrators = multi.map(lambda a: SmartLangevin(a, ...), multi.atoms)
    with multi.parallel():
        multi.foreach(lambda dyn: dyn.run(10_000), integrators)
    return multi.get_positions()

if __name__ == "__main__":               # REQUIRED: PolyAtoms uses spawn
    with PolyAtoms("system.pdb", manager, n_systems=64, workers=2) as poly:
        results = poly.run(simulate, seeds=[0, 1])   # one result per worker
```

`run(fn, *, seeds=None) -> list` — `fn(multi, worker_id)` runs in each worker;
returns one result per worker. `seeds` (one per worker, default `range(workers)`)
seed each worker's RNG so trajectories diverge. `fn` must be a module-level
function or a `functools.partial` of one (picklable).

Per-worker templates + counts on one shared GPU:

```python
with PolyAtoms(["ligand_a.pdb", "ligand_b.pdb"], manager,
               n_systems=[64, 32], workers=2) as poly:
    results = poly.run(simulate, seeds=[0, 1])
```

---

## `multiatoms.ase_md` helpers

Opt-in; never imported by the package core. They exist because ASE's
`MolecularDynamics` opens a `/dev/null` file descriptor whenever no `logfile` is
given, so `N` parallel integrators leak `N` descriptors and can hit the process
limit.

- **`NullLogger`** — a singleton no-op stream (`write`/`flush`/`close` do
  nothing). Pass it as `logfile=NullLogger()` to any ASE integrator **or**
  optimizer (`Langevin`, `VelocityVerlet`, `BFGS`, …).
- **`SmartLangevin`** — a `Langevin` subclass that returns a `NullLogger` instead
  of opening `/dev/null` even when ASE forces `logfile=None` internally. Prefer it
  over plain `Langevin` in multi-system runs.

For an optimizer or a different integrator, just pass `logfile=NullLogger()`
explicitly — that covers the same leak.
