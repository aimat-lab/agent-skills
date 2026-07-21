---
name: md-multiatoms
description: >-
  Run molecular-dynamics (MD) simulations with ASE, scaled by the multiatoms
  package for batched, parallel dynamics on a GPU: replicate a structure into
  many systems and batch their force evaluations into one GPU forward pass.
  Covers writing a ModelManager to drive any interatomic potential (a batched
  torch model, or an off-the-shelf ASE calculator like MACE/XTB/EMT), the
  MultiAtoms/PolyAtoms API, the setup-outside / step-inside parallel() rule, the
  minimize -> equilibrate -> produce workflow, and writing + analyzing
  trajectories (temperature, energy, RDF). Use whenever the user wants to run MD,
  simulate a molecule or material, relax / energy-minimize a structure, run
  NVT/NVE Langevin or Verlet dynamics, drive an ML interatomic potential (MLIP),
  run many replicas at once, or mentions ASE MD, multiatoms, BatchedAtoms,
  MaxwellBoltzmann, a .traj/PDB/xyz trajectory, or ns/day throughput.
compatibility: >-
  Python with multiatoms (github.com/aimat-lab/multi-atoms) plus ase, torch,
  numpy, greenlet, and an interatomic potential (e.g. mace-torch, or one of ASE's
  built-in calculators). A GPU is optional but recommended — batching targets a
  single GPU. The runnable scripts/run_md.py is a self-contained `uv` script whose
  default EMT example needs no GPU and no model download.
metadata:
  domain: computational-chemistry / materials
  tool: multiatoms
---

# md-multiatoms — parallel MD with ASE + multiatoms

[`multiatoms`](https://github.com/aimat-lab/multi-atoms) runs **many MD
simulations of a system at once** and batches their force evaluations into a
single GPU forward pass. Every simulation stays an ordinary ASE `Atoms` object
driven by an ordinary ASE integrator (Langevin, VelocityVerlet) or optimizer
(BFGS); a cooperative scheduler pauses each one when it needs forces, collects
all the pending systems, runs **one** batched forward, and resumes them. GPU
utilization then scales with the number of parallel systems instead of drowning
in per-call overhead.

Use this skill whenever the task is "simulate this molecule / run MD / relax this
structure / drive an ML potential." It works for a single system too
(`n_systems=1`) — you just don't get the batching speedup.

**There is a complete, runnable reference at [`scripts/run_md.py`](scripts/run_md.py)**
(a self-contained `uv` script). Read and adapt it rather than writing a driver
from scratch — it already implements the whole workflow below.

## The mental model — five things that are always true

1. **`MultiAtoms` owns `N` systems.** It replicates one template structure into
   `N` `BatchedAtoms` (ASE `Atoms` subclasses) and exposes `map` / `foreach` /
   `parallel()` to drive them together.
2. **You implement one thing: a `ModelManager`.** Subclass it and write
   `curate_batch(atoms_list) -> dict[str, Tensor]` to turn N systems into one
   batched model input. Everything else (scheduling, caching, distributing
   results) is done for you. See [references/model-manager.md](references/model-manager.md).
3. **Setup happens *outside* `parallel()`; force-stepping happens *inside* it.**
   Building integrators, attaching loggers/trajectories, initializing velocities
   — outside. `optimizer.run(...)` / `integrator.run(...)` — inside
   `with multi.parallel():`. This is the rule people get wrong.
4. **Units are ASE units, always.** `curate_batch` receives positions in **Å**;
   your model must return energy in **eV** (shape `(n_systems,)`) and forces in
   **eV·Å⁻¹** (shape `(Σ n_atoms, 3)`). Convert inside `post_process_hook` if your
   model speaks kcal/mol or similar.
5. **`PolyAtoms` shares one GPU across processes.** For extra throughput it runs
   `K` worker processes that ship force requests to one shared GPU server. It uses
   `spawn`, so the worker function must be top-level and guarded by
   `if __name__ == "__main__":`. See [references/api-reference.md](references/api-reference.md).

## The canonical workflow

`template → ModelManager → MultiAtoms(N) → [seed positions] → minimize (BFGS) →
init velocities → build integrators → attach loggers/trajectories → equilibrate
→ produce → analyze`. The skeleton:

```python
import torch
from ase import units
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution

from multiatoms import MultiAtoms
from multiatoms.ase_md import NullLogger, SmartLangevin

# 1. Wrap your potential  (see references/model-manager.md)
manager = MyModelManager(model=my_model.eval().to(device), device=device)

# 2. Replicate a template into N parallel systems. `template` is an ASE Atoms
#    object OR a path to any ASE-readable file (PDB, xyz, CIF, ...).
multi = MultiAtoms(template="system.pdb", model_manager=manager, n_systems=64)

# 3. SETUP — outside parallel(): no batched force calls needed yet
multi.foreach(lambda a: MaxwellBoltzmannDistribution(a, temperature_K=300), multi.atoms)
integrators = multi.map(
    lambda a: SmartLangevin(a, timestep=1 * units.fs, temperature_K=300,
                            friction=0.01 / units.fs, logfile=NullLogger()),
    multi.atoms,
)

# 4. STEP — inside parallel(): get_forces() across all systems batches into
#    one GPU pass. Always drive with foreach/map (never a plain for-loop).
with multi.parallel():
    multi.foreach(lambda dyn: dyn.run(10_000), integrators)

multi.clean_up()
```

## Golden rules

These are correctness rules, not style. Break them and the run is either wrong or
crashes.

- **Setup outside `parallel()`, force-stepping inside.** Only code that triggers
  `get_forces()` / `get_potential_energy()` — `integrator.run`, `optimizer.run` —
  belongs inside `with multi.parallel():`. Constructing integrators, attaching
  loggers/trajectories, and `MaxwellBoltzmannDistribution` do **not** need forces;
  keep them outside.
- **Inside `parallel()`, drive systems with `multi.foreach` / `multi.map` — never
  a plain Python `for` loop.** `foreach`/`map` put each system in its own greenlet
  so their force calls collect into one batched GPU pass. A bare loop runs them
  one at a time and throws away the entire point of the package.
- **Return ASE units from your model.** Energy `(n_systems,)` in eV, forces
  `(Σ n_atoms, 3)` in eV·Å⁻¹; positions arrive in Å. Wrong units = silently wrong
  dynamics. Do conversions in `post_process_hook`.
- **Avoid the file-descriptor leak.** ASE opens `/dev/null` per integrator when no
  `logfile` is given, so many parallel integrators exhaust the fd limit. Pass
  `logfile=NullLogger()` to every integrator/optimizer, or use `SmartLangevin`.
- **`BatchedAtoms.copy()` doesn't work** — it needs constructor args. To get a
  plain copy (e.g. inside a `ModelManager`), use `ase.Atoms(batched_atoms)`.
- **`PolyAtoms` needs `spawn` hygiene.** The worker `simulate(multi, worker_id)`
  function must be defined at module top level (picklable), and the launch must
  sit under `if __name__ == "__main__":`.
- **Always release the model** — call `multi.clean_up()` at the end, or use
  `PolyAtoms` as a context manager.
- **GPU MD is real compute — never run it on a cluster login node.** It goes
  through Slurm. See [references/running-on-a-cluster.md](references/running-on-a-cluster.md).

## Running the reference script

`scripts/run_md.py` is a `uv` standalone script (PEP 723 inline deps). Its default
run simulates an FCC copper slab with ASE's built-in **EMT** potential — no GPU,
no model download — so it doubles as a smoke test:

```bash
uv run scripts/run_md.py                             # 4 replicas, EMT Cu slab
uv run scripts/run_md.py --n-systems 16 --prod-steps 5000
uv run scripts/run_md.py --structure system.pdb --temperature 310
uv run scripts/run_md.py --help                      # all flags
```

Expected tail on the default run (temperatures near the 300 K target; the RDF
first peak on Cu's nearest-neighbor distance — the dynamics are physical):

```
4 replicas @ 300 K (500 production steps):
  system 0: <T> =  ~300 +/- ~20 K (target 300); E_tot spread = ~1 eV
  ...
  g(r) first peak at ~2.55 A
```

To make it a real study, change the two spots marked `SWAP` in the script: the
**potential** (a `ModelManager` around your MLIP — batched for GPU speed) and the
**structure** (`--structure`). See [references/model-manager.md](references/model-manager.md).

## References

- [`scripts/run_md.py`](scripts/run_md.py) — the runnable reference (uv standalone
  script): minimize → equilibrate → produce → trajectory → analysis. Read it first.
- [`references/model-manager.md`](references/model-manager.md) — how to wrap a
  potential: a generic batched torch model (A), any ASE calculator / MACE (B), a
  single-system fallback (C). Load it when writing the manager.
- [`references/api-reference.md`](references/api-reference.md) — full `multiatoms`
  API: `MultiAtoms`, the `ModelManager` contract, `PolyAtoms`, the `ase_md`
  helpers. Load it for exact signatures.
- [`references/running-on-a-cluster.md`](references/running-on-a-cluster.md) —
  submitting an MD run to a Slurm GPU cluster, sizing `n_systems`/`PolyAtoms`.
  Load it for any cluster run.
- multiatoms source & README: https://github.com/aimat-lab/multi-atoms ·
  ASE MD docs: https://wiki.fysik.dtu.dk/ase/ase/md.html
