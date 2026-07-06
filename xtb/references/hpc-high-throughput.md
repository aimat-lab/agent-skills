# Running xtb on an HPC cluster (high-throughput campaigns)

Load this when the user wants to run xtb/CREST on a cluster (Slurm or similar),
**especially for more than a handful of calculations** ("high throughput",
"screen these N molecules", "run the whole dataset"). It exists to prevent one
specific, expensive mistake.

## The cardinal rule: do NOT submit one job per calculation

xtb calculations are *small and fast* (seconds to minutes). A cluster scheduler
is built for a modest number of larger jobs. Submitting one Slurm job per
molecule in a campaign of hundreds or thousands is an anti-pattern that:

- floods the queue and annoys other users / admins (and may trip submission
  limits or get you rate-limited),
- adds scheduler + node-spin-up overhead that often **dwarfs** the actual xtb
  runtime per task,
- makes the campaign slower overall, not faster,
- is hard to track, clean up, and resubmit.

**Default behavior: pack the entire campaign into ONE job (or a small number of
array tasks) and parallelize *inside* the job.** Never fan a campaign out into
one-job-per-calculation by default.

## Always ask the user before launching a campaign

Batching strategy and resource sizing are the user's call. Before submitting,
**ask** — do not assume. Confirm at minimum:

1. **Batching:** "I'll run all <N> calculations in a single job and parallelize
   across the allocated cores — is that what you want, or do you prefer job
   arrays / a different split?" (One job is the recommended default; present it
   as such.)
2. **Resources:** how many nodes/cores, which partition/QOS, and the wall-time
   limit.
3. **Account/allocation:** which project/account to charge, if applicable.

State the default clearly, recommend it, but get explicit sign-off because this
spends shared compute budget.

## How to parallelize within one job

xtb itself is OpenMP-threaded, so there are two levels of parallelism. The goal:

```
(threads per task)  ×  (concurrent tasks)  ≈  cores allocated
```

For many *small* molecules, prefer **many concurrent single/low-thread tasks**
over few heavily-threaded ones — xtb's threading scales poorly past a few cores
for small systems. A common sweet spot is `OMP_NUM_THREADS=1` (or 2) with as
many concurrent tasks as cores.

### Pattern A — GNU parallel inside one job (recommended default)

```bash
#!/bin/bash
#SBATCH --job-name=xtb_campaign
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64        # whole node
#SBATCH --time=04:00:00
# #SBATCH --account=<project>     # set if your cluster requires it

export OMP_NUM_THREADS=1          # 1 thread per xtb, many in parallel
export OMP_STACKSIZE=2G
ulimit -s unlimited

# run one xtb optimization per structure, 64 at a time, each in its own dir
ls structures/*.xyz | parallel -j "$SLURM_CPUS_PER_TASK" '
  name={/.}; mkdir -p run/$name; cd run/$name
  xtb ../../{} --opt --gfn 2 > xtb.out 2>&1
'
```

Each task gets **its own directory** — xtb writes fixed-name files
(`xtbopt.xyz`, `charges`, …) and concurrent runs in the same folder corrupt each
other (see the main skill's Gotchas). `xargs -P` works too if GNU parallel
isn't available.

### Pattern B — Slurm job array for very large / long campaigns

When the campaign is too big or too long for one wall-time window, chunk it into
a *small* number of array tasks (e.g. 10–50), each of which still runs many xtb
calculations internally via Pattern A. This is the compromise — array tasks
chunk the work; they are **not** one-task-per-molecule.

```bash
#SBATCH --array=0-9               # 10 chunks, NOT one per molecule
# each task processes its slice of the file list, parallelizing within.
```

## Other cluster best practices

- **Never run xtb on the login node.** Always go through the scheduler (or an
  interactive allocation). Login nodes are shared and not for compute.
- **Estimate before submitting:** time one representative calculation, multiply
  by N, divide by concurrency → pick wall-time with margin.
- **One directory per calculation** (see above). Use a clear naming scheme so
  results are easy to collect.
- **Collect results in the job**, e.g. append energies to a CSV / extract from
  each `xtb.out`, so you don't post-process thousands of folders by hand.
- **CREST is heavy** — a single CREST run already uses many cores. Do *not* run
  many CREST jobs concurrently on one node; give each CREST run a healthy thread
  count (`-T`) and run them sequentially or across separate nodes.
- **Modules/environment:** load xtb the cluster's way (`module load xtb` or a
  conda/mamba env) inside the batch script, not interactively.

## If this cluster needs tunneled/OTP access

If reaching the cluster requires an authenticated tunnel or one-time-password
login, that connection/setup is out of scope here — use the dedicated cluster
access tooling/skill for logging in and submitting, then apply the batching
rules above.
