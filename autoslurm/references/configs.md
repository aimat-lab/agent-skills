# Writing and adapting an AutoSlurm config

Load this when `aslurm --list-configs` has nothing that fits and you need to add
a config, or when you need to understand why an existing one behaves as it does.

A config is a YAML file in `~/.config/auto_slurm/configs/`. Its name (minus
`.yaml`) is what `-cn` takes. Keeping the canonical copy in a project repo and
**symlinking** it into that directory is the usual arrangement — the config is
then versioned with the project and still visible to `aslurm`.

## Anatomy

```yaml
defaults:
  - main          # inherit the base template (omit for self-contained; see below)
  - _self_

NO_gpus: 1        # total GPUs per job      ─┐ exactly one of these two
max_tasks: null   # max tasks per job       ─┘ is set; the other is null
gpus_per_task: 1  # GPUs each task gets (GPU jobs)

default_fillers:  # substituted into <angle_bracket> placeholders in the template
  partition: "gpu"
  job_name: "my_job"
  time: "24:00:00"
  cpus: "16"
  mem: "120000mb"
  gres: "gpu:1"
  additional_sbatch_configs: ""

template: |
  #!/bin/bash
  #SBATCH --cpus-per-task=<cpus>
  #SBATCH --gres=<gres>
  ...
```

Placeholders in `template` are `<name>`, filled from `default_fillers` and
overridable per submission with `-o name=value`. Keep
`additional_sbatch_configs` as a filler even if empty — it is the escape hatch
for one-off directives without editing the config.

### Two filler scopes

- `default_fillers` — **per config**, in the config file.
- `global_fillers` — **per machine**, in `~/.config/auto_slurm/general_config.yaml`
  (alongside `hostname_config_mappings`). This is where cross-cutting values like
  `env` and cluster account/project names live.

A `default_filler` may itself contain a `<placeholder>` that resolves from
`global_fillers`, so a config can say `job_name: "<inner>"` and pick the value up
from the machine-level file. Resolution order for a given name is
`-o` override → `default_fillers` → `global_fillers`.

Because `general_config.yaml` is generated from a template on first run, an
untouched install still has `env: "my_env"` — a config that inherits `main` will
then try to activate a nonexistent environment. Worth checking once per machine.

## Inheritance: `defaults`

- `defaults: [main, _self_]` — **inherits** the base `main.yaml` template,
  including its environment activation line and its `--output`/`--error`
  settings. Your file only needs to state what differs.
- `defaults: [_self_]` — **self-contained**; `main.yaml` is not read at all. You
  must supply the whole template, including environment setup.

Choose self-contained when the machine's environment story differs from whatever
`main.yaml` assumes (e.g. `main.yaml` does `conda activate <env>` but the cluster
has no conda).

### Self-contained configs must put the environment on `PATH` themselves

A Slurm batch shell is **non-interactive**, and most distributions' `~/.bashrc`
begins with an early-return guard for that case — so the `PATH` line an installer
appended to `~/.bashrc` never runs. `source $HOME/.bashrc` in the template does
not save you. Set it explicitly:

```bash
export PATH="$HOME/.pixi/bin:$PATH"
```

Symptom when this is missing: the job starts and dies in about a second with no
output at all — because the *only* thing that failed happened before your
command's redirect existed. Point `--output` at a real file while debugging.

## Log to a real file, at least while a config is new

The base template's `--output=/dev/null` hides everything that happens before
your command starts. In a config you control, prefer:

```
#SBATCH --output=<name>_%x_%j.out
#SBATCH --error=<name>_%x_%j.out
```

Your command's own stdout still goes to `slurm-<jobid>*.out` (aslurm's redirect,
see SKILL.md §1) — the sbatch file captures the script around it.

## ⚠️ Never write `${...}` in a template

aslurm loads configs through OmegaConf, which interprets `${...}` as a config
interpolation and dies with `UnsupportedInterpolationType` — **including inside
comments**. Use `$VAR` and `$(command)` instead:

```bash
RESTARTS="$SLURM_RESTART_COUNT"     # ✅
RESTARTS="${SLURM_RESTART_COUNT}"   # ❌ kills config loading
```

(aslurm's own `&>> slurm-${SLURM_JOB_ID}.out` is appended *after* the config is
parsed, which is why it is allowed to use that form and you are not.)

## Sizing a slice, and the rounding trap

For a config that takes a fraction of a node, size each resource as the node's
total divided by its GPU count, **then round down with slack**.

The trap: exact division can overshoot. If a node has 489741 MB and 4 GPUs,
`489741 / 4 = 122435.25`, and asking for `122435` MB × 4 = 489740 MB looks like
it fits — but any rounding in the scheduler's accounting, or any per-node reserve,
means only **3** slices fit, and you have silently lost a quarter of the node.
A 1 MB overshoot costs a whole GPU slice.

Take the quotient with visible slack (`122000` rather than `122435`). The lesson
generalises to CPUs: leave headroom rather than claiming the exact quotient.

Sizing CPUs is a separate judgement from sizing memory. If the work is GPU-bound,
requesting a full one-quarter-node CPU share can make the job *unschedulable* on
a partition whose nodes are CPU-saturated by other users — a smaller CPU request
backfills into gaps that the exact quotient cannot.

## Prefer a dynamic guard over a static `--exclude` list

If some nodes are broken in a way Slurm does not detect (the node reads as idle
precisely because every job on it dies immediately), a static
`--exclude=node-a,node-b` is a snapshot that goes stale silently.

A preflight check at the top of the template that verifies the thing you actually
need — a real GPU context, not just `nvidia-smi` — and calls
`scontrol requeue "$SLURM_JOB_ID"` on failure covers nodes that break later too.
**Cap the retries** (e.g. bail after 10 via `$SLURM_RESTART_COUNT`) so a wholly
broken partition fails loudly instead of churning the scheduler forever.

Gate on the real capability: a driver/userspace version mismatch can make
`nvidia-smi` fail on *every* node including healthy ones, and an `nvidia-smi`-gated
preflight would then requeue off all of them forever without ever running a step.

## Checklist for a new config

- [ ] Name is descriptive of cluster + shape (`<cluster>_<n>gpu[_variant]`).
- [ ] Exactly one of `NO_gpus` / `max_tasks` set; the other `null`.
- [ ] `defaults` correct — and if `_self_` only, environment is on `PATH`.
- [ ] No `${...}` anywhere in the file, comments included.
- [ ] Symlinked into `~/.config/auto_slurm/configs/`.
- [ ] `aslurm --list-configs` shows it.
- [ ] `aslurm -cn <name> -d cmd echo hi` produces a sane `main_0.sh`.
- [ ] Header comment says *why* the numbers are what they are, and dates any
      claim about transient cluster state.
