# xtb command reference

Load this when you need a flag, level, solvent, or xcontrol block not covered in
`SKILL.md`. This is a curated extract — the authoritative source is the official
documentation: <https://xtb-docs.readthedocs.io/>.

## Common command-line flags

| Flag                | Meaning                                                        |
|---------------------|---------------------------------------------------------------|
| `--gfn <0\|1\|2>`   | Select GFN0/1/2-xTB (default `2`).                             |
| `--gfnff`           | Use the GFN-FF force field.                                    |
| `--gxtb`            | Use g-xTB (separate g-xtb binary only).                        |
| `--opt [level]`     | Geometry optimization (default level `normal`).               |
| `--hess`            | Vibrational analysis (Hessian) on current geometry.           |
| `--ohess [level]`   | Optimize then Hessian (use for thermochemistry).              |
| `--omd`             | Optimize then molecular dynamics.                             |
| `--md`              | Molecular dynamics (controlled by `$md` block).               |
| `--grad`            | Compute energy + gradient only.                               |
| `--chrg <int>` / `-c` | Molecular charge (overrides `.CHRG` and xcontrol).          |
| `--uhf <int>` / `-u`  | Unpaired electrons = multiplicity − 1 (overrides `.UHF`).   |
| `--alpb <solvent>`  | ALPB implicit solvation (recommended).                        |
| `--gbsa <solvent>`  | GBSA implicit solvation (older).                              |
| `--acc <real>`      | SCC accuracy (smaller = tighter; default 1.0).               |
| `--iterations <n>`  | Max SCC iterations.                                           |
| `-P, --parallel <n>`| Number of threads (also via `OMP_NUM_THREADS`).              |
| `--input <file>` / `-I` | Read an xcontrol/detailed-input file.                    |
| `--namespace <name>`| Prefix for output file names (isolate runs).                 |
| `--json`            | Write machine-readable `xtbout.json`.                         |

Run `xtb --help` for the complete, version-specific list.

## Optimization levels (`--opt`/`--ohess [level]`)

Loosest → tightest:

```
crude  sloppy  loose  lax  normal  tight  vtight  extreme
```

- Default is `normal` (energy conv 5×10⁻⁶ Eh, gradient conv 1×10⁻³ Eh/a₀).
- Use `tight`/`vtight` before a frequency calculation; `crude`/`sloppy` for
  quick pre-optimization only.

## Common solvent keywords

`water` (`h2o`), `methanol`, `ethanol`, `acetone`, `acetonitrile`,
`chloroform`, `dichloromethane` (`ch2cl2`, `dcm`), `dmso`, `dmf`, `thf`,
`toluene`, `benzene`, `hexane`, `ether`, `nhexane`, `furane`, `phenol`,
`woctanol`, `hexadecane`. Availability differs slightly between `--alpb` and
`--gbsa`; check `xtb --help` / the docs for the exact set in your version.

## Charge & spin precedence

Highest priority wins:

1. Command line: `--chrg` / `--uhf`
2. xcontrol: `$chrg` / `$spin`
3. Files in CWD: `.CHRG` / `.UHF`
4. Default: charge 0, 0 unpaired electrons (neutral singlet)

`$spin` and `.UHF` both count **unpaired electrons** (Nα − Nβ), i.e.
multiplicity − 1. A triplet → `2`; a doublet radical → `1`.

## xcontrol / detailed-input syntax

Pass with `xtb mol.xyz --input control.inp`. Rules:

- Every instruction block starts with a `$flag` and is terminated by the next
  `$flag` (or `$end`).
- `key=value` options set a global variable, are locked at first encounter, and
  may be used once.
- `key: value` options may appear multiple times (e.g. multiple constraints).

### Example: charge/spin + tight optimization

```
$chrg 0
$spin 0
$opt
   optlevel=tight
   maxcycle=200
$end
```

### Example: constrained optimization (freeze a bond length)

```
$constrain
   force constant=1.0
   distance: 1, 2, 1.54     # atoms 1 and 2 held at 1.54 Å (auto if 'auto')
$end
$opt
   optlevel=normal
$end
```

### Example: relaxed scan (stretch a bond in steps)

```
$constrain
   force constant=1.0
   distance: 1, 2, auto
$scan
   1: 1.2, 2.0, 20          # scan constraint #1 from 1.2 to 2.0 Å in 20 steps
$end
```

### Example: fix/freeze a set of atoms

```
$fix
   atoms: 1-10
$end
```

The `$set` block holds lower-level global settings (e.g. `$set` with
`chrg`, `uhf`, electronic temperature `etemp`, etc.); for most work prefer the
dedicated blocks above. See the docs for the full directive list.
