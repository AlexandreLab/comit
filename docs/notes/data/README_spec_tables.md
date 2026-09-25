# The §3 reference tables — first build

**Date:** 2026-09-15 · **Status:** Draft v0.1 for review · **Spec:** §3 of
`docs/specs/2026-08-28-carb3-site-energy-system-implementation.md`

Fourteen tables populating the live specification's data model. Thirteen were built in one
pass by eight parallel research lanes against the briefs in [`build/`](build/);
`unit_abatement_host.csv` was added on 2026-09-17 when §3.5.3 replaced `unit.abates_unit_id`. Every lane's report
(`build/DONE_<lane>.md`) records row counts, coverage per column, every judgement call, the
gaps and why each is a gap, and the questions it could not settle. **Read the report before
quoting a number from its table.** The questions are consolidated in
[note 20](../20_reference_data_open_questions.md).

The existing tables — `activity_process_register.csv` (§3.2) and
`activity_process_energy_profile.csv` (§3.3.1) — already carry the spec's columns and were not
changed. `decarbonisation_options_library.csv` gained three columns (below). File names are
kept as the spec cites them, so `activity_process_energy_profile.csv` still populates the entity
the spec calls `activity_process_energy_share`.

## Files

| File | Spec entity | Rows | Built by | Report |
|---|---|---:|---|---|
| `carrier.csv` | §3.4 `carrier` | 47 | coordinator (skeleton) + lane `carriers` (factors) + lane `units` (product carriers) | `build/DONE_carriers.md` |
| `activity_process_duty_profile.csv` | §3.3 `activity_process_duty_profile` | 427 | lanes `duty_a`, `duty_b` | `build/DONE_duty_a.md`, `build/DONE_duty_b.md` |
| `carb3_comit_process_crosswalk.csv` | the process-level join T17 asked for (no spec entity) | 376 | lanes `duty_a`, `duty_b` | same |
| `unit.csv` | §3.5 `unit` | 138 | lane `units`; `chiller_electric_lt0` added by note 22 Task 10 | `build/DONE_units.md` |
| `unit_input_output.csv` | §3.6 `unit_input_output` | 453 | lane `units` | same |
| `unit_bill_of_materials.csv` | §3.5.2 `unit_bill_of_materials` | 24 | lane `units` | same |
| `unit_eligibility.csv` | §3.5.1 `unit_eligibility` | 3,207 | lane `eligibility`; family rows rebuilt from the join by `build/rebuild_eligibility_join.py` (note 22 Task 10) | `build/DONE_eligibility.md`, the script's docstring |
| `unit_abatement_host.csv` | §3.5.3 `unit_abatement_host` | 37 | lane `units`, 2026-09-17 | `build/DONE_units.md` §8 |
| `decarbonisation_option_unit.csv` | the option→unit join (data-migration item C2) | 163 | lane `eligibility` | same |
| `comit_technology_lineage.csv` | the 397-row reconciliation V1b reads (data-migration item B1) | 397 | lane `lineage` | `build/DONE_lineage.md` |
| `process_load_shape.csv` | §3.13 `process_load_shape` | 371 | lane `loadshape` | `build/DONE_loadshape.md` |
| `scenario_parameters.csv` | §3.8 `scenario_parameters` | 155 | lane `carriers` | `build/DONE_carriers.md` |
| `infrastructure_scenario.csv` | §3.7 `infrastructure_scenario` | 189 | lane `carriers` | same |
| `activity_default_unit.csv` | §3.16 `activity_default_unit` | 456 | lane `default_unit` | `build/DONE_default_unit.md` |

`references.csv` grew from 270 to 313 entries; every `[REF_ID]` in every `provenance` and
`provenance_ref` column resolves to it, and `make data-check` asserts that.

## Conventions every lane worked to

Stated in full in [`build/00_CONVENTIONS.md`](build/00_CONVENTIONS.md). The ones that decide
how to read a cell:

- **Nothing is invented.** A blank means no source stated the value. A populated cell carries a
  `[REF_ID] pointer` naming the table, page or section that was read.
- **UK sources first**: DESNZ/BEIS, DUKES, ECUK, UK ETS, CCC, Carbon Trust, trade bodies; then
  EU BREF; then IEA/IRENA/DOE; then peer-reviewed; vendor material last at `confidence = low`.
- **Costs in 2021 GBP**, with the original year, currency and deflator shown in the pointer.
- **Enums as the spec spells them**, booleans `TRUE`/`FALSE`, blanks empty.

## Extra columns, beyond the spec's field tables

| File | Column | Why |
|---|---|---|
| `carrier.csv` | `vector` | The §3.1.1 consistency hook: `premise_energy.vector` must agree with the carrier, and the spec names no column to check it against |
| `carrier.csv` | `comit_commodity` | The COMIT commodity codes the carrier collapses, for the lineage |
| `carrier.csv` | `provenance` | Citation |
| `unit.csv` | `fuel_carrier_id` | D13 (a unit is family-or-node × fuel): the fuel is part of the identity, and a column is easier to key on than the `role = fuel_input` row of §3.6 |
| `unit.csv`, `unit_input_output.csv`, `unit_bill_of_materials.csv`, `unit_eligibility.csv` | `provenance_ref` | The spec's `provenance` column is an enum (`comit_reuse` / `bref` / `proxy`); the citation needs its own column |
| `unit_eligibility.csv` | `notes` | The reason for a `max_share` or `earliest_year` |
| `process_load_shape.csv` | `carb3_activity` | `process_id` is unique only within an activity (`site_services` appears at all 55). §3.13 now keys on the pair, so this is no longer an extra column (note 20 item 3) |
| `scenario_parameters.csv` | `unit`, `provenance`, `confidence` | The spec's `value` is unitless; a series without its unit is unusable |
| `infrastructure_scenario.csv` | `provenance` | Citation |
| `decarbonisation_options_library.csv` | `displaces_carrier_ids`, `route_change`, `exclusivity_group` | Data-migration items C1, C3, C4 |

## The grade band sets, heat and cooling

§3.4 declares two grade families, each a set of gradeable `carrier` rows, and `carrier.csv`
carries a `grade_family` column (heat or cooling) on every gradeable row and on no other.
`grade_rank` is ordered by temperature within the family, rank 1 coldest, and is unique
**within the family only**: cooling ranks 1 to 3 sit beside heat ranks 1 to 3 by design.
C10 (the grade cascade) runs down the heat bands and up the cooling bands, and never between
the two families.

**Heat.** The food-and-drink worked example says the four bands it uses are its own. This
build **extends those four upward by two** so that furnace and kiln duties have somewhere to
land, and every heat row in the duty profile, every `grade_out` and every reject row uses it:

| `grade_family` | `carrier_id` | `grade_rank` | `grade_label` |
|---|---|---|---|
| heat | `heat_lt60` | 1 | `<60C` |
| heat | `heat_60_100` | 2 | `60-100C` |
| heat | `heat_100_150` | 3 | `100-150C` |
| heat | `heat_150_400` | 4 | `150-400C` |
| heat | `heat_400_1000` | 5 | `400-1000C` |
| heat | `heat_gt1000` | 6 | `>1000C` |

Where the lines fall decides which units are eligible for which duty. This set is a proposal
for review, not a settled answer — note 20 lists the places it bites.

**Cooling.** Added 2026-09-25 (note 22 Task 2), the specification's own three bands:

| `grade_family` | `carrier_id` | `grade_rank` | `grade_label` |
|---|---|---|---|
| cooling | `cooling_lt0` | 1 | `<0C` |
| cooling | `cooling_0_15` | 2 | `0-15C` |
| cooling | `cooling_gt15` | 3 | `>15C` |

**The 17 `REF` duty rows sit on them since 2026-09-25** (note 22 Task 3): three on
`cooling_lt0` (the abattoir's freezer stores, the brewery's glycol loop, and Chemical Works
refrigeration, the last on a `fallback` reading of its equipment) and fourteen on
`cooling_0_15`; nothing is on `cooling_gt15`. Each row's provenance names the temperature
source or, where none was found, the equipment that decided the band. The two chillers
produce `cooling_0_15` at `grade_out` 2, and the ungraded `cooling` carrier is retired.
V34 (duties are services at a grade) leg (c) is now blocking in `make data-check`.

## What is thin, and known to be

| Table | The gap | Where it is explained |
|---|---|---|
| `process_load_shape.csv` | `duty_factor` and `peak_to_mean` blank on all 371 rows: no published load profile survived the no-invention rule. The classification is the deliverable; §3.13 now makes both optional and §5.6 defaults each to 1.00 (mean load over operating hours, the floor of the peak), flagged as an assumption not data | `build/DONE_loadshape.md`, note 20 item 2 |
| `unit.csv` | 15 units uncosted (thermal stores, digester, solar thermal, most hybrids); `min_viable_scale` blank throughout; 24 units now on published UK costs, 92 on COMIT reuse, 21 proxy | `build/DONE_units.md` §4 and §7 |
| `unit.csv` | ~~`abates_unit_id` blank on 11 of 13 abatement units~~ — **closed 2026-09-17.** The column is gone; `unit_abatement_host.csv` carries one row per (train, host) pair, 37 rows over all 13 trains, none blank, and V33 (b) is blocking | `build/DONE_units.md` §8, note 20 item 5 |
| `unit_input_output.csv` | Capture trains other than `ccs_amine` have no coefficients; the four standalone storage units have none either, for want of a published round-trip efficiency — they are now *expressible*, since §3.6 keys on `(unit_id, carrier_id, role)` (note 20 item 4), but not yet written | `build/DONE_units.md` G2, G8 |
| `unit_eligibility.csv` | `min_duty` on 15 rows and `earliest_year` on 9, all from the worked examples; 2,446 of 3,207 rows are `proxy` — 2,442 rebuilt from the join (each serves a duty at its process in C10's direction with a costed unit) and the two rolling mills' 4 node rows. 158 worked-example or options rows offer a unit beyond its `grade_out` at their process; `carb3` drops them from U_q, and `make data-report` lists them under V19 | `build/rebuild_eligibility_join.py`, note 22 Task 10 |
| `activity_process_duty_profile.csv` | 159 of 427 rows are `fallback`; no row is `measured` or `high` | the two duty reports |
| `activity_default_unit.csv` | 366 of 456 rows are `assumed`; 20 name a unit that cannot serve their duty, each a named gap in note 22 Task 10; the CHP shares on 17 rows are the `sector_statistic` content | `build/DONE_default_unit.md` |
| `scenario_parameters.csv` | No 2021 export price, no hydrogen price, no reinforcement cost; import prices for 11 minor carriers absent | `build/DONE_carriers.md` §5 |
| `infrastructure_scenario.csv` | `unit_tariff` and `capacity_limit` blank on every row; hydrogen `available = FALSE` everywhere because nothing published names a region | same |

## Rebuilding

`build/build_*.py` and `build/check_*.py` are the lanes' own generators and checks, kept as a
record of how each table was assembled; each ran clean at the time it was written.
**Do not re-run `build/build_eligibility.py`**: its step (c) writes the no-grade-filter proxy
rows back and would clobber later hand rows. `build/rebuild_eligibility_join.py` owns the
family rows since note 22 Task 10; it is idempotent, and it is the one to run after any
change to the duty profile, the units or the carriers, followed by `make data-worklist`. The
authoritative check is `make data-check`, which now covers all fourteen tables.
