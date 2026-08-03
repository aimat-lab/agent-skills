# autoslurm

Submit and monitor Slurm jobs with **AutoSlurm** (the `aslurm` CLI), which packs
many commands into few jobs from a YAML template config.

## When to use it

Any time an agent runs `aslurm` — launching a parameter sweep, packing tasks
onto GPUs, or picking a config. It exists mainly to pre-empt AutoSlurm's *silent*
failure modes, which are otherwise rediscovered on every session:

- **"Where did my output go?"** Slurm reports `StdOut=/dev/null`, but the output
  is in `slurm-<jobid>*.out` in the submit directory.
- **A sweep that ran once.** `[a,b,c]` without angle brackets is passed to your
  program as a literal string — no error, one task instead of N.
- **"My config isn't being picked up."** `~/.config/auto_slurm/configs/` shadows
  the package's shipped configs by filename; a repo-local YAML does nothing until
  it is symlinked there.

**When not to use it:** for getting *onto* an OTP-protected cluster in the first
place, that is a separate concern (see a cluster-access skill such as
`cluster-tunnel`). This skill is about constructing and submitting the jobs once
you have a shell.

## Contents

| File | Purpose |
|---|---|
| `SKILL.md` | The instructions. Discovery, the log/sweep/config traps, packing, chain and interactive jobs, flags. |
| `references/configs.md` | Loaded on demand: writing a config — inheritance, environment activation, slice sizing, the OmegaConf `${...}` trap. |
| `references/chain-jobs.md` | Loaded on demand: the resume mechanism for work longer than the walltime, and debugging a chain that stopped early. |

## Dependencies

- AutoSlurm installed and importable (`aslurm --list-configs` works). Upstream is
  [aimat-lab/AutoSlurm](https://github.com/aimat-lab/AutoSlurm):
  `pip install git+https://github.com/aimat-lab/AutoSlurm.git`. It is often
  installed into a project environment rather than on the login node's `PATH` —
  `pixi run aslurm` / `uv run aslurm` from the project root.
- Access to a Slurm cluster with configs in `~/.config/auto_slurm/configs/`.

## Scope note

The skill describes AutoSlurm's own behaviour, verified against the package
source, and is deliberately **not** a list of our clusters or configs — those
change, and `aslurm --list-configs` is authoritative. Cluster-specific reasoning
(node shapes, partitions, walltimes) belongs in the header comments of the
individual config files, where it can be dated and revised.

## Install

```bash
ln -s "$(pwd)/autoslurm" ~/.claude/skills/autoslurm
```

or copy it:

```bash
cp -r autoslurm ~/.claude/skills/
```
