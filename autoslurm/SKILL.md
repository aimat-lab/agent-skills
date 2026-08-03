---
name: autoslurm
description: >-
  Submit and monitor Slurm jobs with AutoSlurm (the `aslurm` / `aslurmx` CLI),
  which packs many commands into few jobs from a YAML template config. Use when
  running `aslurm`, launching a parameter sweep or hyperparameter grid on a
  cluster, packing tasks onto GPUs, picking/writing an aslurm config, setting up
  chain/resume jobs for work that outlives the walltime, or starting an
  interactive compute-node shell — and especially when hitting its silent
  failures: "where did my job's output go?"
  (Slurm reports `StdOut=/dev/null`), "there exists no AutoSlurm config file
  with the name X", "my config edits have no effect", or a sweep that ran once
  with a literal `[a,b,c]` string instead of expanding.
---

# Submitting jobs with AutoSlurm (`aslurm`)

`aslurm` turns a list of commands into Slurm job scripts from a YAML **template
config**, packing multiple commands into each job and running them concurrently
on separate GPUs. You give it commands; it decides how many `sbatch` jobs to
create.

> **Cluster-specific.** The `aslurm` command, the configs available, and the
> environment activation all depend on the machine you are on. Never assume the
> configs or paths from another project — run the discovery step below.

## Orientation — always start here

```bash
aslurm --list-configs      # the authoritative list of config names
```

This one command resolves most confusion. Configs are referenced by name
**without the `.yaml`** (`-cn horeka_1gpu`, not `-cn horeka_1gpu.yaml`).

If `aslurm` is not found, it is usually installed in a project environment
rather than on the login node's `PATH`. Try `pixi run aslurm ...` or
`uv run aslurm ...` from the project root before concluding it is missing.

## 1. Where the output actually goes

**This is the trap agents hit most often, and it looks exactly like data loss.**

The standard `main.yaml` template hardcodes:

```
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
```

So `scontrol show job <id>` reports `StdOut=/dev/null`. **Your output is not
gone.** aslurm appends its own redirect to every command it packs:

```bash
<your command> &>> slurm-${SLURM_JOB_ID}.out &
```

Look for these files **in the directory you submitted from**:

| Job packs… | File(s) written |
|---|---|
| exactly 1 command | `slurm-<jobid>.out` |
| N > 1 commands | `slurm-<jobid>_<taskindex>.out` — **one file per task** |

The task index is global across the submission (task 0..N-1 over all jobs), not
per-job — so a 3-job submission of 12 tasks yields `_0` through `_11` spread
across the three job IDs.

Two consequences worth internalising:

- `ls slurm-*.out` in the submit directory is the correct way to find output;
  querying Slurm for the log path is not.
- A config **may** override `--output` to a real file (this is a good idea — a
  `/dev/null`'d batch hides errors that occur *before* your command starts, like
  a failed environment activation). When it does, there are two layers: the
  sbatch-level file gets the script's own stdout, and `slurm-<jobid>*.out` gets
  your command's. Check both when debugging a job that produced nothing.

## 2. Sweep syntax — the angle brackets are load-bearing

aslurm expands placeholders in the command *before* packing:

```bash
# zipped — paired positionally, all lists must be the SAME length
aslurm -cn <config> cmd python train.py --lr '<[0.01,0.1]>' --bs '<[32,64]>'
#   → --lr 0.01 --bs 32
#   → --lr 0.1  --bs 64

# cartesian product — every combination
aslurm -cn <config> cmd python train.py --lr '<{0.01,0.1}>' --bs '<{32,64}>'
#   → 4 tasks: (0.01,32) (0.01,64) (0.1,32) (0.1,64)
```

### ⚠️ Always single-quote the sweep expression

`<` and `>` are redirection operators. **Unquoted, the command never reaches
aslurm** — the shell fails first:

```
zsh:  parse error near `>'
bash: syntax error near unexpected token `newline'
```

Quote the value (`--lr '<[0.01,0.1]>'`) or the whole argument
(`'lr=<[0.01,0.1]>'`). This is the first thing to check when a sweep command
errors before printing anything.

Rules, all enforced at expansion time:

- **Writing `[a,b,c]` or `{a,b,c}` without the angle brackets does not error.**
  The literal string is passed to your program and you get one task instead of
  N. This is the silent one — always verify the expansion with `-d` (§4).
- Mixing `<[...]>` and `<{...}>` in one command raises
  `ValueError: Cannot mix <[]> and <{}> syntax in the same command.`
- Unequal `<[...]>` lengths raise `ValueError: Paired lists must have the same
  length.`
- Commas split at **top level only**, so values may contain nested commas if
  quoted: `--features '<{"charges", "charges,x", "x"}>'` gives three values.

### The `cmd` separator

`cmd` is a literal token separating commands on the CLI — everything after it up
to the next `cmd` is one command. Pass several to run different commands in one
submission:

```bash
aslurm -cn <config>                        \
   cmd python train.py --config conf0.yaml \
   cmd python train.py --config conf1.yaml
```

`cmdx<N>` repeats a command N times — useful for reproducibility runs where the
same command is repeated:

```bash
aslurm -cn <config> cmdx4 python train.py
```

## 3. Configs: the search order explains most "my config is ignored"

aslurm looks for a config by name in this order, first match wins:

1. `~/.config/auto_slurm/configs/` — your own configs
2. the configs shipped inside the installed `auto_slurm` package

Two things follow, and they cause distinct symptoms:

- **A config in your repo has no effect until it is in `~/.config/auto_slurm/configs/`.**
  Copy or symlink it there. Editing `jobs/aslurm_configs/foo.yaml` and running
  `-cn foo` silently uses a *different* `foo` if one exists upstream, or fails
  with `There exists no AutoSlurm config file with the name "foo"!`.
- **`main.yaml` in your user dir shadows the shipped one**, so the base template
  every inheriting config builds on — including the environment activation line
  and the `/dev/null` redirects — may differ from machine to machine at the same
  path. Read the local file rather than assuming; `conda activate <env>` and a
  pixi/`uv` equivalent are both common.

Omitting `-cn` entirely makes aslurm match the current **hostname** against regex
mappings in `~/.config/auto_slurm/general_config.yaml`. Zero or multiple matches
raise a `RuntimeError`. Passing `-cn` explicitly is the predictable path.

For writing or adapting a config — inheritance, fillers, packing shape, and the
OmegaConf pitfalls — see `references/configs.md`.

## 4. Always dry-run first

```bash
aslurm -cn <config> -d cmd <your command>
```

`-d` writes the job scripts without submitting, and prints the authoritative
line:

```
Splitting N tasks into M job(s)
```

**Read N off that output; do not compute the packing yourself.** It is the only
reliable check that your sweep expanded to the number of tasks you intended, and
it catches a missing set of angle brackets immediately (N would be 1).

The generated scripts go to `.aslurm/<timestamp>_<hash>/{main_N.sh,resume_N.sh}`.
Read `main_N.sh` to see the exact sbatch directives and commands. This directory
is also where to look when inspecting an already-running job.

## 5. Packing: one equation

```
tasks_per_job = NO_gpus / gpus_per_task
```

Packed commands run **concurrently in the background** inside one job, each
pinned to its own GPUs via `CUDA_VISIBLE_DEVICES`. The trade:

- **Full-node configs** (e.g. `NO_gpus: 4`, `--exclusive`) pack 4 tasks per job
  and cannot start until 4 GPUs are free *together*.
- **1-GPU configs** (`NO_gpus: 1, gpus_per_task: 1`) emit one independently
  schedulable job per task, so tasks start as single GPUs free and backfill into
  partially-used nodes. Cost: N jobs instead of N/4, and no guarantee siblings
  land together.

Prefer 1-GPU configs when filling arbitrary idle capacity. Some clusters only
offer full-node allocations — a per-cluster fact, not a universal preference.

Give more commands than fit in one job and aslurm splits them across jobs
automatically — 12 tasks against a 4-task config becomes 3 jobs.

Override per submission without editing the config:
`-gpus/--NO_gpus`, `-gpt/--gpus_per_task`, `-mt/--max_tasks`.

**For CPU-only jobs**, disable the GPU arithmetic and set the task count
directly — note the literal string `None`:

```bash
aslurm -cn <config> -gpt None -gpus None -mt 8 cmd ...
```

## 6. Environment activation and `general_config.yaml`

Templates that inherit `main.yaml` activate an environment via an `<env>` filler,
whose default lives in `~/.config/auto_slurm/general_config.yaml` under
`global_fillers`. That file is created from a default on first run (e.g.
`aslurm --help`) and **ships with the placeholder `env: "my_env"`** — if nobody
edited it, every inheriting config tries to activate an environment named
`my_env`. Check it before blaming the cluster.

Override per submission:

```bash
aslurm -cn <config> -o env=my_real_env,time=01:00:00 cmd python train.py
```

`general_config.yaml` also holds the `hostname_config_mappings` used when `-cn`
is omitted. Fillers may reference global fillers, so a config's `job_name` can be
`<inner_filler>` and resolve through to a `global_fillers` entry.

## 7. Name your jobs

Job names default to the config's `job_name` filler, so **every job from one
config shows the same name in `squeue`** and you cannot tell a sweep's jobs
apart. Set it per submission:

```bash
aslurm -cn <config> -o job_name=lr_sweep cmd ...
```

This matters the moment a sweep is more than a couple of jobs.

## 8. Chain jobs — for work longer than the walltime

aslurm can resume work across jobs indefinitely: if a task is about to hit the
walltime, it checkpoints and writes a **resume file**; aslurm then submits a
follow-up job that continues it. The chain ends when no task writes one.

**Nothing changes in the `aslurm` command** — this is driven entirely from
inside your script, via `auto_slurm.helpers`:

```python
from auto_slurm.helpers import start_run, write_resume_file

timer = start_run(time_limit=10)  # HOURS — set below the config's --time

for i in range(start_iter, max_iter):
    ...  # work
    if timer.time_limit_reached() and i < max_iter - 1:
        ...  # save your checkpoint first
        write_resume_file(f"python main.py --checkpoint ckpt.pt --start_iter {i+1}")
        break
```

`time_limit` is in **hours** and must be comfortably less than the job's `time`
filler — the task needs slack after the check to write its checkpoint.

⚠️ **Do not change the working directory while the task runs.** Resume files are
written to `./.aslurm/` **relative to the cwd**, so a task that `chdir`s writes
its resume file somewhere aslurm will not look, and the chain silently ends. If
you must, change back before calling `write_resume_file`.

See `references/chain-jobs.md` for the mechanism and how to debug a chain that
stopped early.

## 9. Interactive jobs

```bash
aslurm -i          # any commands given are ignored
```

This queues a job that just idles, and prints the `srun --jobid <id> --pty bash`
line to attach a shell to it once it starts.

⚠️ **It holds the allocation until cancelled** — it does not exit when you close
the shell. Always `scancel <jobid>` when finished, and prefer a batch job for
anything that does not genuinely need a human at a prompt.

## `aslurm` vs `aslurmx` — do not mix flags

`aslurmx` is a separate, newer CLI (subcommand-based: `aslurmx config list`,
`aslurmx schedule ...`) with **different flag spellings** for the same concepts —
e.g. `-ng/--num-gpus` where `aslurm` has `-gpus/--NO_gpus`, and `--dry-run`
where `aslurm` has `-d/--dry`. Pick one binary and use `--help` on that one.
The rest of this skill describes `aslurm`.

## `aslurm` flag reference

| Flag | Meaning |
|---|---|
| `-cn`, `--config` | Config name, without `.yaml` |
| `-o`, `--overwrite_fillers` | `key1=v1,key2=v2` — override config fillers |
| `-d`, `--dry` | Write job scripts, do not submit |
| `--list-configs` | List available configs and exit |
| `-gpt`, `--gpus_per_task` | GPUs per task (overrides config) |
| `-gpus`, `--NO_gpus` | Total GPUs per job (overrides config) |
| `-mt`, `--max_tasks` | Max tasks per job (overrides config) |
| `-i`, `--interactive` | Interactive job to attach a shell to; ignores commands |
| `-x`, `--exclude` | Comma-separated nodes to exclude |

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `scontrol` says `StdOut=/dev/null`; "logs are gone" | Template hardcodes `/dev/null`; aslurm redirects separately | `ls slurm-*.out` in the submit dir (§1) |
| `parse error near '>'` / `syntax error near unexpected token` | Sweep expression not quoted; the shell ate it | Single-quote it: `--lr '<[1,2]>'` (§2) |
| Sweep produced 1 task, arg was literal `[a,b]` | Missing angle brackets | Use `<[...]>` / `<{...}>`; confirm with `-d` |
| Chain job never resumed | Task `chdir`'d, so `./.aslurm/` resolved elsewhere — or no resume file written | Write the resume file from the submit dir (§8) |
| `conda activate my_env` fails | `general_config.yaml` still has the shipped placeholder | Edit it, or `-o env=<real>` (§6) |
| Allocation stays busy after you log out | `aslurm -i` job is still running | `scancel <jobid>` (§9) |
| `There exists no AutoSlurm config file with the name "X"!` | Config not in `~/.config/auto_slurm/configs/` or the package | `aslurm --list-configs`; symlink your repo config |
| Config edits have no effect | A same-named config shadows it earlier in the search order | Check both locations (§3) |
| `ValueError: Cannot mix <[]> and <{}>` | Both sweep forms in one command | Split into two `cmd` commands |
| `ValueError: Paired lists must have the same length.` | Unequal `<[...]>` lists | Equalise, or switch to `<{...}>` |
| `which aslurm` finds nothing | Installed in a project env, not on `PATH` | `pixi run aslurm` / `uv run aslurm` |
| Job dies instantly, no output at all | Env activation failed before your command ran | Point `--output` at a real file to see it (§1) |
| Every job named the same in `squeue` | Default `job_name` filler | `-o job_name=...` (§6) |

## References

- `references/configs.md` — config anatomy, inheritance, sizing a slice, and
  the OmegaConf `${...}` trap when writing templates.
- `references/chain-jobs.md` — the resume mechanism in detail, and debugging a
  chain that stopped early.

Upstream: <https://github.com/aimat-lab/AutoSlurm> — issues and new cluster
templates are welcome there.
