# PRD / Technical Specification — Site-Level Baselines, Plans, and Pathways

**Status:** Draft v2 for review
**Date:** 2026-08-05
**Related reading:** [notes/04_site_energy_estimation.md](../notes/04_site_energy_estimation.md),
[notes/06_inputting_measured_site_energy.md](../notes/06_inputting_measured_site_energy.md),
[notes/07_high_level_testing_strategy.md](../notes/07_high_level_testing_strategy.md),
[notes/10_site_level_pathways.md](../notes/10_site_level_pathways.md),
[notes/11_sector_coverage_and_carb3_mapping.md](../notes/11_sector_coverage_and_carb3_mapping.md)

---

## 1. Vision

Enhance COMIT so that the industrial sector is modelled **site by site** end to
end:

1. **Baseline** — each site has its own base-year energy consumption
   (electricity, gas, other fuels), its own set of processes, and an estimate
   of the energy consumed by each process — instead of being an
   emissions-share-scaled copy of its sector.
2. **Plans** — each site can carry information about its known or announced
   decarbonisation plans (fuel switching, electrification, hydrogen, CCS,
   closure), with dates and firmness.
3. **Pathways** — the optimisation runs over these site-specific baselines and
   plan constraints and selects a least-cost decarbonisation pathway **per
   site**, reported as a site-level trajectory.

The model already has the right *decision structure* for this — capacity
decisions are indexed site × technology × year, and `known_changes` already
constrains named technologies at named plants. What is missing is site-level
*data resolution*: today one scalar per site (its emissions share) sets its
size, and everything else — fuel mix, process mix, process intensities — is
inherited from the sector.

### Current mechanism being replaced (summary)

```r
# R/fct_sites.R:113  (get_site_demand)
scaling_factor_within_sector = total_MtCO2 / total_sector_emissions
```

This one scalar multiplies site demand (`fct_sites.R:173`) and every
technology's existing capacity (`fct_constraints_capacity_transfer.R:249,315`,
`fct_constraints_existing_capacity.R:44`,
`fct_comit_counterfactual_solver.R:150`). Process structure is sector-fixed in
`technology_input_output` coefficients. Site plans have one partial hook
(`known_changes`, marked "in development"). Full analysis: note 06.

---

## 2. Problem statement

Users hold real site-level data — metered energy by vector, knowledge of which
processes run at which plant, published decarbonisation commitments — and the
model structurally cannot ingest any of it at site level. Consequences: site
baselines misrepresent outlier sites (a coal-heavy site in a gas-dominated
sector), pathway results cannot be reconciled against what sites have actually
announced, and per-site outputs carry false precision (every same-sector site
is the same site, rescaled). Workarounds (one-site sectors, emissions tuning)
distort other inputs and do not scale beyond a handful of sites.

## 3. Goals

1. A user can build a **site-by-site baseline** for the industrial sector:
   per-site energy consumption by vector *and* per-site process set with
   process-level energy estimates.
2. A user can record **site decarbonisation plans** and have the optimiser
   respect them (as constraints) or explore around them (as scenarios).
3. The model outputs a **per-site pathway**: chosen technologies, energy by
   vector, and emissions per model period, traceable to the site's baseline
   and plans.
4. **Sector anchoring preserved** — ECUK/GHGI sector totals remain the
   calibration truth; site data redistributes within sectors, and gaps are
   filled by today's emissions-share apportionment.
5. **Zero-impact default** — workbooks with no site-level data reproduce
   current results exactly.

## 4. Non-goals

- **Re-estimating sector totals from site data.** Sector calibration
  (`Technologies!existing_capacity_2020`, GHGI `Emissions`) stays authoritative;
  conflicts between site data and sector totals are surfaced as validation
  errors, not silently resolved.
- **Automatic inference of site baselines** from public proxies (NAEI pollutant
  ratios, satellite data, etc.). Inputs are user-supplied estimates; how users
  produce them is out of scope.
- **New solver or model rewrite.** This targets the current R/LP structure.
  (Each feature should port cleanly to the linopy redesign of note 08 — the
  site × technology share and per-site process demands are natural xarray
  dimensions — but the Python build is a separate initiative.)
- **Non-industrial sectors and the Hydrogen pseudo-sector** — existing special
  handling unchanged.

---

## 5. Feature breakdown

The work splits into five features plus a cross-cutting foundation. F1–F2 build
the baseline, F3 the plans, F4 the optimisation semantics, F5 the outputs.
Each is independently shippable in the order given.

```
F0 foundation ─┬─ F1 site energy baseline (vectors) ─┐
               ├─ F2 site process register           ├─ F4 pathway optimisation ── F5 pathway outputs
               ├─ F3 site decarbonisation plans ─────┘
               └─ F6 new-sector archetypes (extends coverage; reuses F0 ingestion + F2.3 mechanics)
```

### F0 — Foundation: site data model, ingestion, validation (P0)

New optional workbook sheets, one ingestion/validation layer, and the testing
scaffold every later feature relies on.

Requirements:

- **F0.1** Extend `read_excel_data_template` (`R/fct_read_data.R`) and upload
  validation (`R/fct_upload_utilities.R`, surfaced via `R/mod_upload.R`) to
  read the new sheets defined in F1–F3. All sheets optional; absent or empty
  sheets change nothing.
- **F0.2** Row-level validation with actionable messages: unknown `PlantID`,
  unknown commodity/process/technology for the site's sector, negative values,
  duplicates, and cross-sheet consistency (a plan referencing a process the
  site doesn't have).
- **F0.3** Parity gate in CI: public workbook with no site-level sheets →
  solver-input tables identical to current model (snapshot test per note 07).
  This is the safety net for every feature below.
- **F0.4** Hand-checkable mini scenario (1 sector, 2 sites, 2–3 technologies,
  2 processes) extended per feature as its acceptance vehicle.

### F1 — Site energy baseline by vector (P0)

Per-site base-year consumption of electricity, gas, and other fuels, entered
directly rather than derived from emissions share.

New sheet `site_energy_baseline`: `PlantID` × `input_commodity` →
`annual_consumption_PJ`, plus `data_year`, `source`, and optional
`technology_code` (for when a vector is served by multiple technologies with
different roles — e.g. gas boiler vs gas CHP — and proportional allocation
would be wrong).

Requirements:

- **F1.1** Back-solve measured vector consumption into technology capacities by
  inverting the note 04 Step 3 formula
  (`capacity = use / (fuel_per_unit × availability × capacity_to_activity)`),
  allocating multi-technology vectors in proportion to sector capacities unless
  `technology_code` is given.
- **F1.2** Replace the scalar `scaling_factor_within_sector` with a per-site,
  **per-technology** share table at all five call sites listed in §1:
  measured sites take `implied_capacity / sector_capacity`; remaining sites
  split the residual by emissions share, renormalised so each technology's
  shares sum to 1 (sector totals conserved — asserted at build time).
- **F1.3** Demand apportionment for baselined sites follows their energy share
  (so capacity and demand are mutually consistent); unbaselined sites keep
  renormalised emissions-share demand. *(Pending decision Q1.)*
- **F1.4** Validation: Σ implied site capacity ≤ sector capacity per
  technology; violations name the technology and sites and point to sector
  recalibration (note 06 Option 2) as the fix.
- **F1.5** Plant-closure and counterfactual logic operate on the new share
  table unchanged in behaviour (factor → 0 after `closure_date`; counterfactual
  solver consumes the same shares).
- **Acceptance:** a baselined site's pre-solve implied energy reproduces its
  measured vectors within ≤1%; sector sums unchanged; no-override parity holds.

### F2 — Site process register and process-level energy (P0 for energy-based sectors, P1 for chain sectors)

Per-site statement of *which processes run at the site* and *how much energy
each consumes*. This is the structurally deepest feature: process structure
currently lives in sector-level `technology_input_output` coefficients — a
demand technology bundles services in fixed proportions (e.g. Chemicals `ICH01`:
motors 0.60 / LTH 0.13 / drying 0.06 …), and chain sectors (Paper) hard-code
step intensities per Mt of product. One scalar × fixed bundle ⇒ every site
runs identical processes in identical proportions (note 06 §process-level).

New sheet `site_process_baseline`: `PlantID` × `process_commodity` (service or
intermediate commodity already defined for the sector) →
`annual_energy_PJ` (or `share_of_site_energy`), plus `source`.

Requirements:

- **F2.1 (energy-based sectors)** Allow site demand to be expressed directly in
  *service* commodities (PJ of drying / motors / LTH per site) instead of the
  sector's final-demand commodity, bypassing the fixed demand-technology
  bundle. Implementation point: the demand join in `get_site_demand`
  (`R/fct_sites.R:150-179`), branching per site on register presence. Sites
  without a register keep the sector bundle.
- **F2.2** National demand conservation: Σ (site service demands + bundled
  demands of unregistered sites) reconciles to `Demand_drivers` totals per
  commodity; the residual redistribution mirrors F1.2 and violations are
  validation errors, not silent rescaling.
- **F2.3 (chain sectors, P1)** For sectors modelled as process chains (Paper),
  per-site process mix means a per-site *product* mix (tissue vs board is a
  drying-intensity difference). Support via **archetype sub-sectors** (note 06
  Option 4): archetype definition remains a workbook exercise
  (duplicate fleet + coefficients), made a pure data edit by the data-driven
  sector registry of **F6.1** (which removes the hard-coded sector names in
  `R/app_ui.R` and audits the Iron & steel special case in
  `R/fct_attribution.R`) — an archetype and a new sector are the same
  mechanism at different granularity.
- **F2.4** Consistency check between F1 and F2 for doubly-baselined sites:
  Σ process energy ≈ Σ vector energy (tolerance configurable; default warn at
  5%, error at 20%).
- **Acceptance:** mini scenario where two same-sector sites hold different
  service splits produces different optimal technology choices for otherwise
  identical costs; unregistered sites bit-match current behaviour.

### F3 — Site decarbonisation plans (P0)

Structured input of what each site is known or announced to be doing, as an
extension of the existing `known_changes` mechanism
(`R/fct_constraints_known_changes.R` already builds per-site min/max-proportion
constraints on a named technology's share of an output commodity over
`year_from`–`year_to`; note 06 flags it "in development").

Extend `known_changes` (or supersede with `site_plans`) with:

| Column | Purpose |
|---|---|
| `plan_type` | fuel switch / electrification / hydrogen / CCS / efficiency / closure / new build |
| `status` | `operational` / `committed` / `announced` / `speculative` |
| `technology`, `output_commodity`, `year_from`, `year_to`, `min/max_proportion` | as today |
| `source`, `notes` | provenance |

Requirements:

- **F3.1** Harden the existing constraint builder: define and test semantics
  for overlapping plans at one site, plans on technologies the site cannot host
  (eligibility conflicts), and interaction with plant closures (`plan_type =
  closure` should subsume/align with the `plant_closures` sheet — one
  mechanism, not two).
- **F3.2** `status`-based inclusion policy, set per model run (F4.2):
  e.g. "hard-constrain `operational`+`committed`, ignore `announced` and
  below" vs "constrain everything". Default preserves current behaviour
  (all rows constrain).
- **F3.3** Validation: plan references resolve against the site's sector
  technologies and against F2's process register where present; date ranges
  within the model horizon; infeasibility pre-checks where cheap (e.g. forced
  proportion on an ineligible technology) fail at load, not at solve.
- **Acceptance:** a committed "CCS from 2030" row forces the site's pathway
  through CCS from 2030 in outputs; removing the row lets the optimiser
  diverge; an infeasible plan produces a load-time error naming the row.

### F6 — New-sector coverage via archetypes (P1)

The model covers 16 industrial sectors; the mapping against the CaRB3/NDBS
classification (note 11) shows material industrial activity with no COMIT
sector of its own — most notably **waste collection, treatment & disposal**
(107 NAEI sites) and **water & sewerage**, both currently folded into the
"Other" catch-all by `new_sector_mapping`, plus out-of-scope candidates
(mining/extraction, cold-chain logistics, data centres) that are a scope
decision rather than data work. F6 makes *adding a sector (or sector
archetype) a data-only exercise*, using the same mechanics as F2.3's
within-sector archetypes — a new sector **is** an archetype with its own
NAEI mapping.

**Scope caveat (note 11 §5):** the data-only premise holds where the
candidate consists of NAEI CO₂ point sources in manageable numbers — i.e.
**Waste** (107 sites). It does *not* hold for: water & sewerage (5,374
dispersed sites → MILP size, needs aggregation + a non-emissions size
proxy); electricity-dominated sectors like data centres and cold stores (no
NAEI point-source record → nothing for emissions-share scaling to act on;
they require F1 baselines as *mandatory* input); energy-from-waste
(net energy export — a structure the demand-driven LP lacks — plus a
power-sector boundary/double-counting risk); and mining/extraction (mobile
plant energy, poor fit for `technology_input_output`). F6.1–F6.4 below
deliver the data-only path; the structural extensions are out of F6's scope
and gated on Q8.

Requirements:

- **F6.1 Data-driven sector registry.** The sector list is derived from the
  workbook (`Technologies` + `new_sector_mapping`), never from code: remove
  the hard-coded lists in `R/app_ui.R:16-36,155-173`, audit the Iron & steel
  special case in `R/fct_attribution.R`, and make cluster/plot modules take
  sectors from the loaded data. This is the single enabler both F2.3 and F6
  depend on.
- **F6.2 Sector-definition template.** Document (and validate) the complete
  row-set a new sector needs across the workbook: `Technologies` (fleet +
  `existing_capacity_2020`), `technology_input_output` (process
  coefficients), `new_sector_mapping` + `NAEI_mapping` (site assignment),
  `Demand_drivers`, `Emissions` (GHGI anchor), `traded_share`
  (+ `non_point_share`). Loading a workbook with a partially-defined sector
  fails with a checklist of the missing sheets/rows, not a downstream join
  error.
- **F6.3 Site reassignment.** Sites move to a new sector purely by editing
  `sector_NAEI` → `IPM_sector` rows in `new_sector_mapping` (whole source
  sector) or per-site `IPM_sector` values in `NAEI_df_clean_2023_revised`
  (subset of sites). Emissions-share scaling then applies within the new
  sector automatically — no code change.
- **F6.4 Conservation on split.** When a new sector is carved out of an
  existing one (e.g. Waste out of Other), validation checks that the two
  sectors' GHGI `Emissions` totals and fleet capacities sum to the
  original's (tolerance configurable), so national totals are conserved by
  construction — mirroring F1.2's within-sector renormalisation at sector
  level.
- **F6.5 Calibration guidance (documentation, not code).** For candidate
  sectors, note 11 identifies which external data can seed the fleet
  calibration: NAEI already carries the waste/water sites; CaRB3/VOA
  floorspace and fuel-used attributes can cross-check sectors with direct
  activity matches (Cement, Food & drink, Paper, Refineries, Iron & steel)
  but *not* the generic-coded sectors (Glass, Lime, Mechanical/Electrical
  engineering, Textiles).
- **Acceptance:** in the mini scenario, defining a two-technology "Waste"
  sector and reassigning the NAEI waste source sector to it via workbook
  edits alone produces a solved model with the new sector's sites, demand,
  and constraints present; the pre-split parity run (waste still in Other)
  is unchanged; a deliberately incomplete sector definition fails at load
  with the F6.2 checklist.

### F4 — Per-site pathway optimisation semantics (P0 thin / P1 full)

The solver already chooses per site — F4 makes the *run configuration* around
site data explicit.

Requirements:

- **F4.1 (P0)** Feasibility diagnostics: when site constraints make the LP
  infeasible, report which site/plan/baseline rows are implicated (at minimum,
  re-solve with plan constraint groups relaxed one at a time to bisect;
  IIS-style reporting if the solver exposes it).
- **F4.2 (P1)** Run-level toggles in `model_parameters`: plan-status inclusion
  threshold (F3.2) and site-baseline on/off — enabling paired runs
  ("with plans vs without plans", "site baselines vs sector-average") for
  exactly the comparison studies this feature exists to serve.
- **F4.3 (P1)** Solve-health guard: site-level constraints add rows but no new
  variables; benchmark that MILP solve time on the public workbook stays within
  an agreed envelope (note 07 performance snapshot).

### F5 — Per-site pathway outputs (P1)

Site-indexed results exist internally (decisions are site × technology ×
year); F5 makes the pathway *legible*.

Requirements:

- **F5.1** Per-site pathway table in the output workbook: for each site ×
  model period — active technologies and capacities, energy by vector,
  emissions, and which plan rows were binding.
- **F5.2** Baseline provenance table: per site × technology/process — applied
  share and basis (`measured` / `process register` / `apportioned`), and
  deviation from sector-average mix. Makes runs auditable and makes the
  F1/F2 data visible for review.
- **F5.3** Site pathway view in the Shiny app (existing plot patterns in
  `R/fct_plot_outputs.R` / `fct_processes_sankey.R`): pick a site, see its
  trajectory. P2 if app work is deprioritised.

---

## 6. Priorities at a glance

| Priority | Scope |
|---|---|
| **P0** | F0 all; F1.1–F1.5; F2.1–F2.2 (energy-based sectors); F3.1–F3.3; F4.1 |
| **P1** | F2.3–F2.4 (chain sectors/archetypes, cross-checks); F4.2–F4.3; F5.1–F5.2; F6.1–F6.4 (new-sector archetypes — F6.1 data-driven sector registry is the shared enabler for F2.3 and should land first within P1) |
| **P2** | F5.3 (app view); F6 applied to out-of-scope candidates (mining/extraction, cold-chain, data centres — pending scope decision Q8); time-varying baselines (`data_year` vintages); data-quality weighting of measured vs apportioned; emissions re-derivation from measured energy (Q2) |

## 7. Success metrics

**Hard gates (CI):** no-site-data parity 100%; baselined sites reproduce
measured vectors ≤1% in pre-solve tables; sector totals conserved under any
override set (property-tested, hedgehog); mini-scenario hand-checks pass.

**Adoption (1–2 modelling cycles):** ≥1 study builds a multi-site baseline for
at least one sector using F1+F2 without one-site-sector workarounds; ≥1 paired
run ("with vs without plans") published from F4.2; note 06's Options 1/3
retired as recommended practice.

**Health:** solve time on public workbook within agreed envelope; no growth in
MILP variable count from site features.

## 8. Open questions

| # | Question | Owner | Blocking |
|---|---|---|---|
| Q1 | Demand basis for baselined sites: energy-share (self-consistent, as specced in F1.3) or keep emissions-share demand? Affects attribution downstream. | Modelling lead | F1 |
| Q2 | Are NAEI emissions authoritative when measured energy implies different emissions (via fuel factors)? Decides whether `fct_attribution.R` and traded/non-traded splits are in scope. | Modelling lead | F1 |
| Q3 | Partial data: site with gas metered but not electricity — allow mixed measured/apportioned vectors in v1, or all-or-nothing per site? | Modelling lead + eng | No (restrictable) |
| Q4 | F2 input unit: absolute PJ per process or share of site energy? Shares compose better with F1; absolutes are what engineers hold. Support both? | Modelling lead | F2 |
| Q5 | Plan semantics for `closure`: fold `plant_closures` into `site_plans` or keep both sheets with a precedence rule? | Eng | F3 |
| Q6 | Feasibility reporting depth (F4.1): is group-relaxation bisection enough, or is solver IIS support required (and does the current solver expose it)? | Eng | No |
| Q7 | Do site plans interact with cluster/infrastructure build-out constraints (a committed CCS plan implies T&S availability — force it or flag inconsistency)? | Modelling lead | F3/F4 |
| Q8 | Scope of new sectors (F6): Waste (data-only, first candidate) vs the structurally hard candidates per note 11 §5 — is site-aggregated water & sewerage wanted, and are electricity-dominated sectors (data centres, cold-chain), EfW export, or mining in COMIT's remit at all given each needs model extensions (mandatory F1 baselines, net export, non-emissions sizing)? | Modelling lead | No — F6.1–F6.4 proceed on Waste regardless |

## 9. Phasing

- **Phase 1 — Baseline (F0 + F1):** data model, parity harness, vector-level
  site baselines with per-technology shares. Prerequisites: Q1, Q2.
  *Value shipped: measured site energy usable; mix heterogeneity per site.*
- **Phase 2 — Processes + plans (F2.1–F2.2 + F3):** per-site service demands
  for energy-based sectors; hardened plan constraints with status policy.
  Prerequisites: Q4, Q5. *Value shipped: full site baseline incl. processes;
  pathways respect known plans.*
- **Phase 3 — Semantics + legibility (F4 + F5.1–F5.2):** feasibility
  diagnostics, run toggles, pathway and provenance outputs.
- **Phase 4 — Structure & coverage (F6.1 data-driven sectors, then F2.3
  within-sector archetypes and F6.2–F6.4 new sectors — first candidates:
  Waste and Water & sewerage carved out of "Other"; F5.3 app view; P2
  items).** Prerequisite: Q8 for candidates beyond waste/water.

Dependency notes: the note 07 testing scaffold is a Phase 1 prerequisite
(F0.3/F0.4 are its first consumers). If the Python redesign proceeds, each
phase should be specced against both codebases from this document.

---

## 10. Engineering summary (touch points)

| Area | Files | Change |
|---|---|---|
| Ingestion & validation | `R/fct_read_data.R`, `R/fct_upload_utilities.R`, `R/mod_upload.R` | 2–3 new optional sheets, schema + cross-sheet validation |
| Share computation | `R/fct_sites.R` | site × technology share table replacing the scalar; per-site service-demand branch |
| Constraint builders | `R/fct_constraints_capacity_transfer.R`, `R/fct_constraints_existing_capacity.R`, `R/fct_comit_counterfactual_solver.R` | join on share table instead of scalar |
| Plans | `R/fct_constraints_known_changes.R` | schema extension, status policy, closure unification, load-time feasibility checks |
| Sector lists | `R/app_ui.R`, `R/fct_attribution.R` | data-driven sector registry (F6.1 — enabler for archetypes and new sectors) |
| New-sector validation | `R/fct_read_data.R`, `R/fct_upload_utilities.R` | sector-definition completeness checks (F6.2) and split-conservation checks (F6.4) |
| Outputs | `R/fct_create_output_tables.R`, `R/fct_plot_outputs.R` | pathway + provenance tables, site view |
| Tests | note 07 scaffold | parity snapshots, mini scenario, hedgehog properties |

The riskiest arithmetic is concentrated in two places: the renormalisation
that conserves sector totals (F1.2/F2.2) and the plan-constraint semantics
under overlap (F3.1). Both are covered by the mini scenario before any full-
workbook run.
