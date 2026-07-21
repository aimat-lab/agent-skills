# Running an MD job on a GPU cluster

Batched MD with an ML potential is a **GPU compute job**. On a shared HPC cluster
one rule dominates: **it runs through Slurm, never on a login node.** This page is
generic Slurm guidance; the actual login/upload/submit mechanism is your cluster's
concern (plain `ssh`/`sbatch`, or a dedicated cluster-submission skill if your
group has one — see the last section).

## Division of labor

| Belongs on the **login node** (cheap, allowed) | Belongs in a **Slurm job** (real compute) |
| --- | --- |
| Building the environment (`uv`/`pip`/`conda`, `module load`) | Every `python run_md.py` that evaluates the potential |
| Uploading structures and code | Minimization, equilibration, production |
| `squeue` / `sacct` / inspecting outputs | Anything touching the GPU |

Running the MD driver directly on the login node to "just test it" is the exact
thing not to do — even a short run steals resources from a shared node. Smoke-test
locally first: the default EMT run of [`../scripts/run_md.py`](../scripts/run_md.py)
needs no GPU.

## Environment on the login node

`scripts/run_md.py` is a `uv` script with inline (PEP 723) dependencies, so the
simplest path is to let `uv` build the environment on first run — no venv to
manage. For real GPU MD, edit the script's inline `[[tool.uv.index]]` block to
your CUDA build (e.g. `.../whl/cu124`), or delete that block to use the default
CUDA-enabled wheel, and add your potential (e.g. `mace-torch`) to `dependencies`.

If you prefer an explicit environment instead:

```bash
python -m venv .venv && . .venv/bin/activate
pip install "multiatoms @ git+https://github.com/aimat-lab/multi-atoms.git"
pip install torch --index-url https://download.pytorch.org/whl/cu124   # match drivers
pip install mace-torch          # or your own potential
```

`multiatoms` runtime deps are `ase numpy greenlet torch`.

## Slurm batch template (`run_md.sbatch`)

Adjust partition, time, and GPU count to your cluster's limits.

```bash
#!/bin/bash
#SBATCH --job-name=md
#SBATCH --partition=<gpu-partition>
#SBATCH --gres=gpu:1                    # one GPU; MD batches many systems onto it
#SBATCH --cpus-per-task=8               # integrators step on the CPU
#SBATCH --time=02:00:00                 # set a realistic limit — be a good tenant
#SBATCH --output=md_out/slurm-%j.log

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
mkdir -p md_out

# module load cuda/12.x                 # if the cluster uses environment modules

# Option 1 — uv builds the env from the script's inline deps on first run:
uv run scripts/run_md.py --structure system.pdb --n-systems 64 --prod-steps 100000

# Option 2 — an explicit venv you built on the login node:
# source .venv/bin/activate
# python scripts/run_md.py --structure system.pdb --n-systems 64 --prod-steps 100000
```

## Sizing the run for the GPU

- **`n_systems`** is your throughput knob: one batched forward evaluates all
  replicas at once, so raise `n_systems` until the GPU is full (watch memory). This
  is the whole reason to use `multiatoms` on a big GPU — but only with a **batched**
  `ModelManager` (Recipe A). The EMT/ASE-calculator wrapper (Recipe B) does not
  batch the GPU. See [model-manager.md](model-manager.md).
- **`PolyAtoms(..., workers=K)`** overlaps CPU integration with GPU forward passes
  across processes. Use it when a single `MultiAtoms` leaves the GPU idle between
  batches. Mind its `spawn` rules (top-level worker fn, `if __name__ == "__main__":`)
  — see [api-reference.md](api-reference.md).
- **One GPU, not many.** Batching is designed to saturate a single device; request
  `--gres=gpu:1` unless you have a measured reason for more.

## Etiquette (shared machine)

- **Never run the potential on a login node** — Slurm only.
- **Don't submit one tiny job per replica.** The batching *is* the parallelism;
  pack replicas into one job via `n_systems` (and job arrays only for genuinely
  independent campaigns).
- **Ask the user before launching** large or long jobs — confirm resources, wall
  time, partition, and account. It spends shared compute budget.
- **Set a realistic `--time`** and prefer batch jobs over idle interactive
  allocations.

## If your group has a cluster-submission skill

Some setups drive an OTP-protected cluster through a persistent authenticated
tunnel / submission tool (so an agent can `sbatch` and monitor without handling
credentials). If such a skill is installed, use **it** for the login, file
transfer, submission, and job monitoring, and use **this** skill for the MD itself
(the driver script, `n_systems`/`PolyAtoms` sizing, the sbatch body above). Keep
the two concerns separate: this skill stays portable across clusters.
