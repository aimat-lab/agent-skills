# md-multiatoms skill

Run **molecular dynamics with ASE**, scaled by the
[`multiatoms`](https://github.com/aimat-lab/multi-atoms) package for **batched,
parallel dynamics on a GPU** — replicate a structure into many systems and batch
their force evaluations into one GPU forward pass, while every simulation stays an
ordinary ASE `Atoms` driven by an ordinary ASE integrator.

## When to use it

Use it when you want to simulate a molecule or material: energy-minimize/relax a
structure, run NVT/NVE (Langevin/Verlet) dynamics, drive an ML interatomic
potential (MLIP) such as MACE, run many replicas at once for throughput, or write
and analyze trajectories (temperature, energy, RDF). Triggers include `multiatoms`,
ASE MD, `MultiAtoms`/`PolyAtoms`, `BatchedAtoms`, `MaxwellBoltzmann`, a
`.traj`/PDB/xyz trajectory, or "run MD / simulate this system / ns/day".

Not for: training the potential itself (that's a model-training skill), or the
cluster login/submission mechanism (that belongs in a cluster-submission skill —
this skill's cluster notes are portable Slurm guidance).

## Dependencies

- `multiatoms` (`pip install "multiatoms @ git+https://github.com/aimat-lab/multi-atoms.git"`)
  and its deps `ase numpy greenlet torch`.
- An interatomic potential: your own torch MLIP, or an ASE calculator such as
  `mace-torch` (`pip install mace-torch`), `xtb`, or ASE's built-in `EMT`.
- A GPU is optional but recommended (batching targets a single GPU). The bundled
  example runs on CPU.

## Contents

- `SKILL.md` — the skill instructions: the mental model, the canonical
  minimize → equilibrate → produce workflow, and the golden rules.
- `scripts/run_md.py` — a complete, runnable `uv` reference script (its default
  EMT copper example needs no GPU and no model download).
- `references/model-manager.md` — how to wrap any potential in a `ModelManager`
  (batched torch model, ASE calculator/MACE, single system).
- `references/api-reference.md` — the full `multiatoms` API.
- `references/running-on-a-cluster.md` — submitting an MD run via Slurm.

## Worked example

The reference script runs end to end with nothing but ASE + multiatoms:

```bash
# 4 replicas of an FCC copper slab (EMT), CPU-only smoke test
uv run scripts/run_md.py

# your own structure, more replicas, a longer production run
uv run scripts/run_md.py --structure system.pdb --n-systems 16 --prod-steps 5000
```

It prints per-replica mean temperature and the RDF first peak, and writes one ASE
trajectory per replica to `md_out/`. To make it a real study, swap the two spots
marked `SWAP` in the script — the potential (your MLIP) and the structure.

## Install

Copy or symlink this folder into your agent's skills directory (for Claude Code,
`~/.claude/skills/`):

```bash
# copy (frozen at install time)
cp -r md-multiatoms ~/.claude/skills/

# or symlink (auto-updates on git pull) — recommended
ln -s "$(pwd)/md-multiatoms" ~/.claude/skills/md-multiatoms
```
