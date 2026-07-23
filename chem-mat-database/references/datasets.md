# ChemMatData dataset catalog (snapshot)

> **This is a point-in-time snapshot for orientation.** The remote catalog
> changes as datasets are added/updated. **Always trust a live `cmdata list`**
> (or `get_file_share(Config()).fetch_metadata()["datasets"]`) over this table.

Two categories:

- **`organic`** — SMILES-based small molecules. Available in raw (CSV) and
  processed (graph) form; some also as 3D xyz bundles (e.g. `qm9`).
- **`tmc`** — transition-metal complexes. Also loadable in the decomposed TMC
  tabular form via `load_tmc_dataset` (metal center + ligand SMILES + coordination
  metadata).

`type` is **REG** (regression) or **CLS** (classification); `targets` is the
number of target columns. (A couple of entries carry a mislabeled `target_type`
in metadata — e.g. `bace_reg` is regression despite showing CLS — so confirm
against `cmdata info NAME` when it matters.)

| name | category | compounds | targets | type | description |
|------|----------|-----------|---------|------|-------------|
| MCF_7 | organic | 26,776 | 2 | REG | Cancer-related (MCF-7 cell line) |
| ames | organic | 6,512 | 2 | CLS | Ames mutagenicity |
| aqsoldb | organic | 9,889 | 1 | REG | Curated aqueous solubility |
| bace_cls | organic | 1,513 | 2 | CLS | BACE β-secretase inhibition (qualitative) |
| bace_reg | organic | 1,513 | 1 | REG | BACE β-secretase inhibition (IC50) |
| bbbp | organic | 1,934 | 1 | CLS | Blood–brain barrier penetration |
| beet | organic | 254 | 2 | CLS | Toxicity in honey bees |
| bl_chembl_cls | organic | 8,780 | 35 | CLS | Briem & Lessel ChEMBL multi-target (classification) |
| bl_chembl_reg | organic | 52,484 | 35 | REG | Briem & Lessel ChEMBL multi-target (regression) |
| clintox | organic | 1,465 | 2 | CLS | FDA-approved vs. clinical-trial toxicity failures |
| compas_1x | organic | 34,072 | 9 | REG | COMPAS cata-condensed PAHs (DFT properties) |
| compas_3x | organic | 39,482 | 9 | REG | COMPAS peri-condensed PAHs |
| dpp4 | organic | 3,933 | 2 | CLS | DPP-4 inhibitors (ChEMBL) |
| dud_e | organic | 400,040 | 102 | CLS | DUD-E directory of useful decoys (enhanced) |
| elanos_bp | organic | 5,431 | 1 | REG | Boiling point |
| elanos_vp | organic | 2,704 | 1 | REG | Vapor pressure |
| electrum_oxstate | tmc | 39,166 | 7 | CLS | ~39k mononuclear TMC oxidation states |
| esol | organic | 1,127 | 1 | REG | Water solubility (log mol/L) |
| freesolv | organic | 639 | 2 | REG | Hydration free energies (exp + calc) |
| half_life | organic | 892 | 1 | REG | Soil biotic half-life |
| hiv | organic | 38,040 | 2 | CLS | HIV replication inhibition |
| hopv15_exp | organic | 175 | 6 | REG | Harvard Organic Photovoltaics (HOPV15) |
| kulik_spin | tmc | 1,920 | 7 | REG | Kulik octahedral TMC spin states |
| lipophilicity | organic | 4,199 | 1 | REG | Octanol/water distribution (logD) |
| muv | organic | 93,111 | 17 | CLS | Maximum Unbiased Validation |
| open_melting_point | organic | 27,965 | 1 | REG | Bradley open melting-point dataset |
| pcqm4mv2 | organic | 3,378,606 | 1 | REG | PubChemQC-derived HOMO–LUMO gap (very large) |
| qm9 | organic | 134,000 | 16 | REG | QM9 DFT properties (has 3D xyz bundle) |
| qm9_smiles | organic | 133,882 | 19 | REG | QM9 in SMILES form |
| riniker_1 | organic | 168,326 | 88 | CLS | RDKit benchmarking platform subset I |
| riniker_1_filtered | organic | 105,294 | 69 | CLS | RDKit benchmarking subset I (filtered) |
| riniker_2 | organic | 20,922 | 37 | CLS | RDKit benchmarking platform subset II |
| sider | organic | 1,220 | 27 | CLS | Marketed drugs & adverse reactions |
| skin_irritation | organic | 1,263 | 2 | CLS | Skin irritation |
| skin_sensitizers | organic | 1,263 | 2 | CLS | Skin sensitization |
| synth_binary_global | organic | 249,455 | 2 | CLS | Synthetic global binary task |
| synth_binary_local | organic | 249,455 | 2 | REG | Synthetic local task |
| tadf | organic | 460,199 | 3 | REG | TADF emitters (high-throughput virtual screen) |
| tmqm | tmc | 100,847 | 8 | REG | ~100k mononuclear TMCs (tmQM) |
| tmqmg | tmc | 63,466 | 20 | REG | ~63k mononuclear TMCs (tmQMg) |
| tox21 | organic | 7,570 | 12 | CLS | Toxicity across 12 biological targets |
| toxcast | organic | 6,842 | 617 | CLS | ToxCast high-throughput toxicology |
| zinc250k | organic | 249,455 | 3 | REG | ~250k drug-like ZINC molecules |

## Picking a small one for a smoke test

For quick end-to-end checks prefer the small sets: **`esol`** (1,127, single-target
regression), **`freesolv`** (639), **`clintox`** (1,465, classification), or
**`bbbp`** (1,934). Avoid `pcqm4mv2` (3.4M), `tadf` (460k), and `dud_e` (400k)
unless you actually need scale — and use the streaming datasets (`SmilesDataset`
/ `GraphDataset`) for those.

## Available forms per dataset

- **raw** (`.csv`) — every dataset. `load_smiles_dataset` / `cmdata download`.
- **processed graph** (`.mpack`) — every dataset. `load_graph_dataset` /
  `cmdata download --full`.
- **xyz bundle** (3D coordinates) — only datasets with 3D structures (e.g.
  `qm9`). `load_xyz_dataset`.
- **TMC decomposed** — the `tmc`-category datasets. `load_tmc_dataset`.

Use `cmdata info NAME` to see exactly which forms and targets a given dataset
exposes.
