#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "multiatoms @ git+https://github.com/aimat-lab/multi-atoms.git",
#     "ase>=3.28",
#     "torch>=2.2",
#     "numpy",
# ]
#
# # ---------------------------------------------------------------------------
# # PyTorch is pulled from the CPU wheel index by default so this script runs
# # anywhere with no CUDA toolchain (the EMT smoke test needs no GPU). For real
# # GPU MD with an ML potential, change the index URL below to your CUDA build
# # (e.g. .../whl/cu124) OR delete this whole [[tool.uv.index]] / [tool.uv.sources]
# # section to let uv pull the default PyPI wheel (CUDA-enabled on Linux).
# # ---------------------------------------------------------------------------
# [[tool.uv.index]]
# name = "pytorch-cpu"
# url = "https://download.pytorch.org/whl/cpu"
# explicit = true
#
# [tool.uv.sources]
# torch = [{ index = "pytorch-cpu" }]
# ///
"""Parallel MD with ASE + multiatoms — a self-contained, runnable reference.

Runs N replicas of a system through the canonical workflow:

    minimize (BFGS) -> init velocities -> NVT equilibrate -> NVT produce
      -> per-replica ASE trajectory -> basic analysis (temperature, RDF)

Out of the box it simulates an FCC copper slab with ASE's built-in EMT
potential, so it runs anywhere with no GPU and no model download — a smoke
test. To turn it into a real study, change two things (both marked `SWAP`):

  * the POTENTIAL — replace `ASECalculatorManager(EMT)` with a `ModelManager`
    around your MLIP. A *batched* torch model is what unlocks the GPU speedup;
    see ../references/model-manager.md.
  * the STRUCTURE — pass `--structure my_system.pdb` (any ASE-readable file).

Examples:
    uv run scripts/run_md.py                              # EMT Cu smoke test
    uv run scripts/run_md.py --n-systems 16 --prod-steps 5000
    uv run scripts/run_md.py --structure system.pdb --temperature 310
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from ase import Atoms, units
from ase.build import bulk
from ase.calculators.emt import EMT
from ase.io import Trajectory, read
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
from ase.optimize import BFGS

from multiatoms import ModelManager, MultiAtoms
from multiatoms.ase_md import NullLogger, SmartLangevin


# --- POTENTIAL  (SWAP: a batched torch model unlocks the GPU speedup) --------
class ASECalculatorManager(ModelManager):
    """Adapt any ASE calculator into a multiatoms ModelManager (non-batched).

    Correct and simple, but evaluates systems in a Python loop -> no GPU
    batching. Ideal for a smoke test, CPU potentials, or single systems. For
    throughput write a batched ModelManager instead (see references/model-manager.md).
    """

    def __init__(self, calc_factory, device="cpu"):
        super().__init__(model=None, device=device)
        self.calc = calc_factory()

    def curate_batch(self, atoms_list):
        return {"atoms_list": atoms_list}

    def model_forward(self, batched_input):
        energies, forces = [], []
        for atoms in batched_input["atoms_list"]:
            probe = Atoms(atoms)  # plain copy; BatchedAtoms.copy() needs ctor args
            probe.calc = self.calc
            energies.append(probe.get_potential_energy())  # eV
            forces.append(probe.get_forces())              # eV/A
        return (
            torch.as_tensor(np.asarray(energies)),
            torch.as_tensor(np.concatenate(forces, axis=0)),
        )

    def clean_up(self):
        pass


def build_template(structure: str | None) -> Atoms:
    if structure:  # SWAP: your own system
        return read(structure)
    # Default smoke-test system: FCC copper, periodic, EMT-friendly.
    return bulk("Cu", "fcc", a=3.6, cubic=True).repeat((3, 3, 3))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Parallel MD with ASE + multiatoms.")
    p.add_argument("--structure", default=None,
                   help="ASE-readable structure file (default: FCC Cu slab).")
    p.add_argument("--n-systems", type=int, default=4,
                   help="Parallel replicas; raise to fill a GPU.")
    p.add_argument("--temperature", type=float, default=300.0, help="K")
    p.add_argument("--timestep", type=float, default=1.0, help="fs")
    p.add_argument("--friction", type=float, default=0.01, help="1/fs (Langevin)")
    p.add_argument("--equil-steps", type=int, default=200)
    p.add_argument("--prod-steps", type=int, default=500)
    p.add_argument("--log-every", type=int, default=20)
    p.add_argument("--fmax", type=float, default=0.05, help="eV/A (BFGS convergence)")
    p.add_argument("--output-dir", default="md_out")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    template = build_template(args.structure)
    manager = ASECalculatorManager(lambda: EMT(), device=device)  # SWAP potential
    multi = MultiAtoms(template=template, model_manager=manager,
                       n_systems=args.n_systems)

    # --- minimize (BFGS) — INSIDE parallel(): it calls get_forces() ----------
    optimizers = multi.map(lambda a: BFGS(a, logfile=NullLogger()), multi.atoms)
    with multi.parallel():
        multi.foreach(lambda opt: opt.run(fmax=args.fmax, steps=100), optimizers)

    # --- setup — OUTSIDE parallel(): no force calls needed yet ---------------
    multi.foreach(
        lambda a: MaxwellBoltzmannDistribution(a, temperature_K=args.temperature),
        multi.atoms,
    )
    integrators = multi.map(
        lambda a: SmartLangevin(
            a, timestep=args.timestep * units.fs, temperature_K=args.temperature,
            friction=args.friction / units.fs, logfile=NullLogger()),
        multi.atoms,
    )
    trajs = multi.map(
        lambda a, i: Trajectory(str(outdir / f"prod_{i}.traj"), "w", a),
        multi.atoms, range(args.n_systems),
    )

    records: list[list] = [[] for _ in range(args.n_systems)]

    def make_recorder(atoms, i):
        def record():
            records[i].append((atoms.get_temperature(),
                               atoms.get_potential_energy(),
                               atoms.get_kinetic_energy()))
        return record

    recorders = multi.map(make_recorder, multi.atoms, range(args.n_systems))

    # --- equilibrate, then produce — INSIDE parallel() -----------------------
    with multi.parallel():
        multi.foreach(lambda dyn: dyn.run(args.equil_steps), integrators)

    # attach recorders + trajectory writers for the production phase only
    multi.foreach(lambda dyn, rec: dyn.attach(rec, interval=args.log_every),
                  integrators, recorders)
    multi.foreach(lambda dyn, tr: dyn.attach(tr.write, interval=args.log_every),
                  integrators, trajs)

    with multi.parallel():
        multi.foreach(lambda dyn: dyn.run(args.prod_steps), integrators)

    multi.foreach(lambda tr: tr.close(), trajs)
    multi.clean_up()

    # --- basic analysis ------------------------------------------------------
    print(f"\n{args.n_systems} replicas @ {args.temperature:.0f} K "
          f"({args.prod_steps} production steps):")
    for i, rec in enumerate(records):
        arr = np.array(rec)                        # (frames, 3): T, Epot, Ekin
        temp, etot = arr[:, 0], arr[:, 1] + arr[:, 2]
        half = len(temp) // 2                      # drop the equilibration transient
        print(f"  system {i}: <T> = {temp[half:].mean():6.1f} "
              f"+/- {temp[half:].std():4.1f} K "
              f"(target {args.temperature:.0f}); "
              f"E_tot spread = {etot[half:].max() - etot[half:].min():.3f} eV")

    # RDF only makes sense for a periodic / bulk system.
    frames = read(str(outdir / "prod_0.traj"), index=":")
    last = frames[-1]
    if last.cell.rank == 3 and last.pbc.all():
        from ase.geometry.rdf import get_rdf
        sample = frames[-min(20, len(frames)):]
        rmax = 0.49 * min(last.cell.lengths())     # < half the smallest cell vector
        rdf = np.mean([get_rdf(f, rmax=rmax, nbins=120)[0] for f in sample], axis=0)
        dists = get_rdf(sample[-1], rmax=rmax, nbins=120)[1]
        print(f"  g(r) first peak at ~{dists[np.argmax(rdf)]:.2f} A")

    print(f"\nTrajectories + logs written to {outdir}/")


if __name__ == "__main__":
    main()
