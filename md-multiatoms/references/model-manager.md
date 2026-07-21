# Writing a `ModelManager`

A `ModelManager` is the one piece you write to plug a potential into
`multiatoms`. It answers a single question: **given the systems that need new
forces right now, how do I run one model call and get energy + forces back?**

## The contract

Subclass `multiatoms.ModelManager`. You **must** implement `curate_batch`; the
rest have working defaults.

| Method | Required? | Job |
| --- | --- | --- |
| `curate_batch(atoms_list) -> dict[str, Tensor]` | **yes** | Turn the list of systems that need forces into one batched model input. |
| `model_forward(batched_input) -> (energy, forces)` | no | How the model is called. Default: `model(**batched_input)` then `model.get_forces(energy, pos)`. |
| `post_process_hook(forces, energy) -> (forces, energy)` | no | Unit conversion / scaling before results are handed back. Default: identity. |
| `clean_up()` | no | Teardown (GPU workers, etc.). Default: calls `model.clean_up()` if it exists. |

**Non-negotiable I/O conventions** (see the golden rules in [../SKILL.md](../SKILL.md)):

- Positions in `curate_batch` are in **Å**.
- `energy` returned from `model_forward` → shape `(n_systems,)`, in **eV**.
- `forces` returned from `model_forward` → shape `(Σ n_atoms, 3)`, in **eV·Å⁻¹**,
  ordered the same way you concatenated systems in `curate_batch`.
- `model_forward` returns **torch tensors** (the base class calls `.cpu()` on
  them). If your source is numpy, wrap it: `torch.as_tensor(arr)`.

`curate_batch` only ever receives the systems whose positions changed since their
last evaluation — per-system caching is handled for you, so don't filter yourself.

---

## Recipe A — a batched torch model (the real speedup)

This is the native path: one forward pass over all systems at once. Your model
takes flat positions plus a `batch_idx` that says which system each atom belongs
to, and returns a per-system energy; forces come from autograd.

```python
import numpy as np
import torch
from multiatoms import ModelManager


class BatchedTorchManager(ModelManager):
    """Drive a torch MLIP that consumes (pos, z, batch_idx) for a whole batch."""

    def curate_batch(self, atoms_list):
        n_atoms = len(atoms_list[0])            # assumes equal-size replicas
        pos = torch.tensor(
            np.stack([a.positions for a in atoms_list]).reshape(-1, 3),
            dtype=torch.float32, device=self.device,
        )
        z = torch.tensor(
            np.concatenate([a.get_atomic_numbers() for a in atoms_list]),
            dtype=torch.long, device=self.device,
        )
        batch_idx = torch.arange(
            len(atoms_list), device=self.device
        ).repeat_interleave(n_atoms)
        return {"pos": pos, "z": z, "batch_idx": batch_idx}

    def model_forward(self, batched_input):
        pos = batched_input["pos"]
        pos.requires_grad_(True)
        with torch.enable_grad():
            energy = self.model(pos, batched_input["z"], batched_input["batch_idx"])
            forces = -torch.autograd.grad(energy.sum(), pos, create_graph=False)[0]
        return energy, forces

    # Only if your model speaks other units, e.g. kcal/mol -> eV:
    # def post_process_hook(self, forces, energy):
    #     EV_PER_KCAL = 1.0 / 23.060548
    #     return forces * EV_PER_KCAL, energy * EV_PER_KCAL
```

Instantiate with your model on the target device:

```python
device = "cuda" if torch.cuda.is_available() else "cpu"
manager = BatchedTorchManager(model=my_model.to(device).eval(), device=device)
```

Notes:

- If your model already exposes `get_forces(energy, pos)` and is called as
  `model(**batched_input)`, you can **delete `model_forward`** and rely on the
  default.
- Different-size systems are fine — build `batch_idx` from each system's own atom
  count instead of assuming `n_atoms` is constant.
- Everything is `torch`, so keep tensors on `self.device`; the base class moves
  results back to CPU/numpy for you.

---

## Recipe B — wrap any ASE calculator (MACE, XTB, EMT, …)

The pragmatic on-ramp: you already have an ASE *calculator* (a foundation MLIP
like MACE, a semi-empirical method like XTB, or a classical one like EMT) and
want to run it under this workflow. Evaluate each system through the calculator
and stack the results.

```python
import numpy as np
import torch
from ase import Atoms
from multiatoms import ModelManager


class ASECalculatorManager(ModelManager):
    """Adapt any ASE calculator into a multiatoms ModelManager.

    Simple and always correct: ASE calculators already return eV / eV·Å, so no
    unit conversion is needed. It evaluates systems in a Python loop, so it does
    NOT batch the GPU — use it for single-system runs, CPU potentials, or to get
    going fast; switch to Recipe A when you want the batched-GPU speedup.
    """

    def __init__(self, calc_factory, device="cpu"):
        # calc_factory: a zero-arg callable returning a fresh ASE calculator.
        super().__init__(model=None, device=device)
        self.calc = calc_factory()

    def curate_batch(self, atoms_list):
        return {"atoms_list": atoms_list}       # nothing to tensorize

    def model_forward(self, batched_input):
        energies, forces = [], []
        for atoms in batched_input["atoms_list"]:
            # BatchedAtoms.copy() needs constructor args; build a plain Atoms.
            probe = Atoms(atoms)                 # copies numbers/pos/cell/pbc/constraints
            probe.calc = self.calc
            energies.append(probe.get_potential_energy())   # eV
            forces.append(probe.get_forces())               # eV/Å
        energy = torch.as_tensor(np.asarray(energies), dtype=torch.float64)
        force = torch.as_tensor(np.concatenate(forces, axis=0), dtype=torch.float64)
        return energy, force

    def clean_up(self):
        pass                                    # no torch model to tear down
```

Concrete: the **MACE** foundation model (`pip install mace-torch`):

```python
from mace.calculators import mace_off

device = "cuda" if torch.cuda.is_available() else "cpu"
manager = ASECalculatorManager(
    calc_factory=lambda: mace_off(model="small", device=device),
    device=device,
)
multi = MultiAtoms(template="system.xyz", model_manager=manager, n_systems=1)
```

Swap the factory for any other calculator:

```python
from xtb.ase.calculator import XTB          # GFN-xTB
manager = ASECalculatorManager(lambda: XTB(method="GFN2-xTB"))

from ase.calculators.emt import EMT         # toy potential, great for smoke tests
manager = ASECalculatorManager(lambda: EMT())
```

> **Batching caveat.** Because Recipe B loops over systems, running with
> `n_systems > 1` gives you independent replicas but **no GPU batching benefit** —
> each system is a separate calculator call. MACE and some other MLIPs expose a
> native batched interface; wiring that into Recipe A (one `curate_batch` /
> `model_forward` over the whole batch) is what unlocks the throughput. Start with
> B to validate the physics, move hot paths to A.

This is exactly the manager used by [`scripts/run_md.py`](../scripts/run_md.py)
(with EMT), so it is a verified, runnable starting point.

---

## Recipe C — single system, minimal

`n_systems=1` needs no special manager — reuse Recipe A or B unchanged:

```python
manager = ASECalculatorManager(lambda: EMT())
multi = MultiAtoms(template=atoms, model_manager=manager, n_systems=1)
# ... same setup/step workflow; parallel() has near-zero cost with one system.
```

You still get the ASE-integrator workflow and trajectory/analysis tooling; you
simply skip the batching machinery. This is the right choice for quick tests,
expensive per-call potentials, or a genuinely single-replica study.

---

## Choosing a recipe

| Situation | Use |
| --- | --- |
| Your own torch MLIP, want max GPU throughput, many replicas | **A** |
| Off-the-shelf calculator (MACE/XTB/EMT), getting started, validating physics | **B** |
| One system, or an expensive/CPU potential | **B or C** |
| Model speaks kcal/mol, Hartree, etc. | any + `post_process_hook` |

When in doubt, start with **B** (correct and quick to stand up), confirm the
trajectory looks physical, then port to **A** if throughput matters. Full class
signatures are in [api-reference.md](api-reference.md).
