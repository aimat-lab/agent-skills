---
name: xtb
description: >-
  Run semiempirical tight-binding quantum-chemistry calculations with the
  Grimme group's xtb program from the command line: single-point energies,
  geometry optimizations (--opt), vibrational frequencies and thermochemistry
  (--hess/--ohess), implicit solvation (ALPB/GBSA), and method selection across
  GFN0/GFN1/GFN2-xTB and the GFN-FF force field. Also covers the new g-xTB
  general-purpose method and CREST conformer/rotamer searches. Use whenever the
  user wants to optimize a molecule, get energies/frequencies/free energies,
  pre-screen geometries cheaply, search conformers, or mentions xtb, GFN2-xTB,
  GFN-FF, g-xTB, crest, ALPB, or an xtbopt/coord/.CHRG file.
compatibility: Requires the `xtb` binary on PATH (and `crest` for conformer search). g-xTB needs the separate g-xtb release.
metadata:
  domain: computational-chemistry
  tool: xtb
---

# xtb — semiempirical tight-binding calculations

xtb (Grimme group, "Semiempirical Extended Tight-Binding Program Package") runs
fast electronic-structure calculations using the GFNn-xTB methods and the GFN-FF
force field. It is the workhorse for cheap geometry optimization, energies,
frequencies/free energies, and (with CREST) conformer searching.

This skill covers command-line usage on a local machine. It assumes `xtb` is
already installed and on `PATH`.

## Before you start

1. **Check availability and version:**
   ```bash
   xtb --version        # mainline stable is 6.7.1 (Jul 2024)
   ```
   If missing, the usual install is `mamba install -c conda-forge xtb`
   (and `crest` for conformer search). Do not assume a module name — ask or
   check the cluster's module system if relevant.
2. **Have a structure file** in xyz (Å) or Turbomole `coord` (Bohr) format.
3. **Set the thread/stack environment** for non-trivial jobs (see Gotchas).
4. **Run in a dedicated working directory** — xtb writes many files with fixed
   names (`xtbopt.xyz`, `xtbout.json`, `charges`, `wbo`, …) into the CWD and
   will overwrite them. One calculation per directory.

## Choosing a method

Select with `--gfn` (or `--gfnff`); **GFN2-xTB is the default** if you pass
nothing.

| Flag        | Method   | Use it for                                                            |
|-------------|----------|----------------------------------------------------------------------|
| `--gfn 2`   | GFN2-xTB | Default. Best all-round accuracy (geometries, energies, noncovalent). |
| `--gfn 1`   | GFN1-xTB | Older parametrization; occasionally more robust for some metals.      |
| `--gfn 0`   | GFN0-xTB | No self-consistent charges → very fast/robust; good first pre-opt.    |
| `--gfnff`   | GFN-FF   | Generic force field, quadratic scaling. Large systems / cheap pre-opt.|
| `--gxtb`    | g-xTB    | Newest general method (separate release — see the g-xTB section).     |

Rule of thumb: optimize and report with **GFN2-xTB**; drop to **GFN0-xTB** or
**GFN-FF** to pre-optimize big or troublesome systems, then refine with GFN2.

## Core workflows

In all examples `mol.xyz` is the input structure. Charge/multiplicity default to
neutral singlet unless set (see "Charge and spin").

**Single-point energy:**
```bash
xtb mol.xyz                      # GFN2-xTB single point
xtb mol.xyz --gfn 1 > sp.out     # different method, capture output
```

**Geometry optimization** (`--opt [level]`, default level `normal`):
```bash
xtb mol.xyz --opt                # optimize at GFN2-xTB, 'normal' convergence
xtb mol.xyz --opt tight          # tighter convergence
```
- Optimized geometry → **`xtbopt.xyz`** (or `xtbopt.coord`).
- Convergence levels, tightest last: `crude, sloppy, loose, lax, normal,
  tight, vtight, extreme`. `normal` = E conv 5e-6 Eh, grad conv 1e-3 Eh/a0.

**Frequencies / thermochemistry:**
```bash
xtb mol.xyz --hess               # Hessian on the CURRENT geometry only
xtb mol.xyz --ohess              # optimize THEN Hessian (use this for thermo)
```
- Use `--ohess`, not `--hess`, unless the geometry is already optimized — a
  Hessian on an unconverged structure gives meaningless (imaginary) modes.
- Gives vibrational frequencies and Gibbs free-energy terms (`g298.gp`, etc.).
- Check for imaginary frequencies; a true minimum has none.

**Implicit solvation** (add to any run):
```bash
xtb mol.xyz --opt --alpb water       # ALPB model (recommended default)
xtb mol.xyz --opt --gbsa toluene     # older GBSA model
```
Use `--alpb <solvent>` by default; `--gbsa` is the older model kept for
compatibility. Solvent names are keywords (water, methanol, thf, toluene,
dmso, acetonitrile, …) — see `references/command-reference.md`.

## Charge and spin

xtb is **neutral closed-shell by default.** Getting these wrong silently gives
wrong energies — always set them for ions/radicals. Three ways, in priority
order (**command line > xcontrol > files**):

1. **Files in the CWD** (auto-detected): `.CHRG` holds the integer charge,
   `.UHF` holds the number of unpaired electrons (= multiplicity − 1).
   ```bash
   echo -1 > .CHRG          # anion
   echo  2 > .UHF           # triplet (2 unpaired electrons)
   ```
2. **Command line** (overrides the files):
   ```bash
   xtb mol.xyz --opt --chrg -1 --uhf 2
   ```
3. **xcontrol file** via `$chrg` / `$spin` (`$spin` = unpaired electrons).

## Input / output files

- **Input:** `.xyz` (Cartesian, Å) or Turbomole `coord` (Bohr). Both accepted.
- **`xtbopt.xyz` / `xtbopt.coord`** — optimized geometry.
- **`xtbout.json`, `xtbrestart`, `charges`, `wbo`, `g98.out`** — results,
  restart data, atomic charges, bond orders, frequencies.
- **xcontrol / "detailed input"** — an instruction file passed with
  `--input control.inp` (or the auto-read `.xcontrol`/`xtb.inp`). Syntax: each
  block starts with a `$flag` and ends at the next `$`. See
  `references/command-reference.md` for the `$opt`, `$scc`, `$constrain`,
  `$set`, `$chrg`/`$spin` blocks and constrained-optimization / scan examples.

## g-xTB — the new general-purpose method (preliminary)

> **Status (mid-2025): preliminary / development release. Treat as experimental.**
> g-xTB is **not** part of mainline `xtb`; it ships separately and the Grimme
> group states the final implementation will live in **tblite**, so invocation
> and features may change. Verify against the g-xtb repo before relying on it.

**What it is.** g-xTB ("general" extended tight-binding) is the newest method
from the Grimme group, designed as a successor to the GFNn-xTB family. It
covers all elements **H–Lr (Z = 1–103)** and targets **ωB97M-V/def2-TZVPPD**
accuracy at tight-binding speed (developers report WTMAD-2 ≈ 9.3 kcal/mol on
GMTKN55, roughly half GFN2-xTB's error — self-reported, not yet independently
benchmarked).

**Getting it.** Download the statically linked binaries from the
`grimme-lab/g-xtb` GitHub release (Linux / Windows / ARM macOS). They bundle a
**modified `xtb` 6.7.1 + modified tblite** — use that bundled binary, not your
stock `xtb`.

**Invocation** — add `--gxtb` to the bundled xtb binary:
```bash
xtb struc.xyz --gxtb                  # single point
xtb struc.xyz --gxtb --opt            # geometry optimization
xtb struc.xyz --gxtb --hess           # numerical Hessian
xtb struc.xyz --gxtb --molden         # Molden file for orbitals
```
`--chrg`, `--uhf`, `--acc`, and `--grad` work as usual.

**Current limitations** (per the g-xtb README): no aISS docking (`dock`), no
orbital localization (`--lmo`), no point-charge embedding (`$pcem`), no cube
generation (`$cube`); **solvation is preliminary and can be unstable** during
optimization — use solvated g-xTB with caution.

## CREST — conformer / rotamer search

CREST drives xtb to sample conformers and rotamers; xtb is the underlying
energy/gradient engine. Install `crest` separately.

```bash
crest mol.xyz                          # default iMTD-GC conformer search (GFN2)
crest mol.xyz --gfn2//gfnff -T 8       # faster: GFN-FF sampling, GFN2 refine
crest mol.xyz --chrg -1 --uhf 0 --alpb water   # ions/solvent: pass like xtb
```
- Outputs: **`crest_conformers.xyz`** (ranked ensemble) and
  **`crest_best.xyz`** (lowest-energy conformer).
- Typical pipeline: CREST search → take `crest_best.xyz` → refine with
  `xtb --ohess` (often in solvent) for final geometry + free energy.
- CREST is expensive; always set threads (`-T`) and run on adequate hardware.
- Full keyword reference: https://crest-lab.github.io/crest-docs/

## Gotchas

- **One run per directory.** Fixed-name outputs are overwritten; concurrent
  runs in the same folder corrupt each other.
- **Set resources for real jobs:** `export OMP_NUM_THREADS=<n>` (and
  `export OMP_STACKSIZE=4G`; raise `ulimit -s unlimited`). Too-small stack is a
  classic crash for Hessians/large systems.
- **`--hess` vs `--ohess`:** only `--hess` on an already-optimized geometry;
  use `--ohess` otherwise, or you get spurious imaginary frequencies.
- **Charge/spin are silent:** wrong `--chrg`/`--uhf` gives a converged but wrong
  answer. Double-check for ions and radicals.
- **Convergence failures:** pre-optimize with `--gfn 0` or `--gfnff`, then
  refine with GFN2-xTB. Loosen `--opt` level only as a last resort.
- **g-xTB is experimental:** don't use it for production results without
  checking the current g-xtb release notes; prefer GFN2-xTB when in doubt.

## Running on an HPC cluster / high-throughput campaigns

If the user wants to run on a cluster (Slurm etc.) or screen many structures,
**read `references/hpc-high-throughput.md` first.** Key rules from it:

- **Never submit one job per calculation.** The default is to pack the whole
  campaign into **one job** (or a few job-array chunks) and parallelize *inside*
  the job. One-job-per-molecule floods the scheduler and is slower overall.
- **Ask the user before launching** — confirm the batching strategy (recommend
  the single-job default), resources, wall time, and account. It spends shared
  compute budget, so get explicit sign-off.
- Never run xtb on a login node; give each task its own directory.

## References

- `references/command-reference.md` — fuller flag list, optimization levels,
  solvent keywords, and xcontrol (`$`-block) syntax with constraint/scan
  examples. Load it when you need a flag or block not covered above.
- `references/hpc-high-throughput.md` — how to run xtb/CREST on a cluster
  without flooding the scheduler. Load it for any cluster or high-throughput
  run.
- `assets/ethanol.xyz` — a small example structure used in `README.md`'s
  worked walkthrough.
- Official docs: xtb https://xtb-docs.readthedocs.io/ ·
  CREST https://crest-lab.github.io/crest-docs/ ·
  g-xTB https://github.com/grimme-lab/g-xtb
