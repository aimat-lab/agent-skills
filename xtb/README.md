# xtb skill

Run the Grimme group's **xtb** semiempirical tight-binding program from the
command line — geometry optimization, energies, frequencies/thermochemistry,
implicit solvation, the GFN0/1/2-xTB and GFN-FF methods, the new **g-xTB**
method, and **CREST** conformer searches.

## When to use it

Use it when you want fast quantum-chemistry calculations on a molecule:
optimize a structure, get an energy or free energy, compute frequencies,
pre-screen geometries cheaply before DFT, or search conformers. Triggers
include `xtb`, `GFN2-xTB`, `GFN-FF`, `g-xTB`, `crest`, `ALPB`, or files like
`coord` / `.CHRG` / `xtbopt.xyz`.

Not for: full DFT/ab-initio jobs (different tools), or HPC/Slurm submission
(that belongs in a separate cluster-submission skill — this skill is local CLI).

## Dependencies

- `xtb` on `PATH` (mainline stable 6.7.1). Install e.g.
  `mamba install -c conda-forge xtb`.
- `crest` for conformer search (`mamba install -c conda-forge crest`).
- For g-xTB: the separate `grimme-lab/g-xtb` release binaries (experimental).

## Contents

- `SKILL.md` — the skill instructions (method selection, core workflows,
  charge/spin, g-xTB, CREST, gotchas).
- `references/command-reference.md` — fuller flag/level/solvent/xcontrol
  reference, loaded on demand.
- `references/hpc-high-throughput.md` — best practices for running on a cluster
  / high-throughput campaigns (don't submit one job per calculation), loaded on
  demand.
- `assets/ethanol.xyz` — small example structure for the walkthrough below.

## Worked example

With `assets/ethanol.xyz`, a typical optimize-then-thermochemistry run in water:

```bash
# optimize at GFN2-xTB (default method), then frequencies + free energy, in water
xtb ethanol.xyz --ohess --alpb water > ethanol_opt.out

# optimized geometry is written to xtbopt.xyz
```

For a charged/radical species, set charge and unpaired electrons:

```bash
xtb ethanol.xyz --opt --chrg 0 --uhf 0 --alpb water
```

## Install

Copy or symlink this folder into your agent's skills directory (for Claude Code,
`~/.claude/skills/`):

```bash
# copy
cp -r xtb ~/.claude/skills/

# or symlink (auto-updates on git pull) — recommended
ln -s "$(pwd)/xtb" ~/.claude/skills/xtb
```
