# Lane `units` — the unit library: `unit`, `unit_input_output`, `unit_bill_of_materials` (T9 core, T8 collapse)

> **Dated record.** Written against the schema of September 2026, before §3.6's `role`
> enum replaced the three booleans and widened the key. See the banner in
> [`00_CONVENTIONS.md`](00_CONVENTIONS.md); the live gate is `make check`.

Read `docs/notes/data/build/00_CONVENTIONS.md`, then spec **§3.5, §3.5.2, §3.6**, §1.6
decisions D5, D6, D13, D15, and both worked examples' §1.11 tables **in full** — their unit
rows are the seed and must be reproduced verbatim (IDs, classes, families, fuels).

## Phase 1 — identity first (do this before anything else, ~30 min)

Write `docs/notes/data/unit.csv` with the §3.5 columns **plus** an extra `fuel_carrier_id`
column (the D13 fuel, → `carrier.csv`; blank for PV/storage) and `provenance_ref` (the
`[REF_ID] pointer`; the spec's `provenance` column holds the enum comit_reuse/bref/proxy).
Populate **only the identity columns** in phase 1: `unit_id, unit_name, unit_class, spine,
duty_family, process_id, fuel_carrier_id, is_hybrid, draws_ambient, abates_unit_id`. Leave
costs blank for now. Then **immediately** write `docs/notes/data/build/PHASE1_units.md`
saying "unit identity list ready" with the row count — other lanes are waiting on it.

The unit set is: (a) every unit in the two worked examples; (b) the D13 collapse of COMIT's
397 technologies (`docs/notes/data/comit_sector_processes.csv`,
`emissions_source_classification.csv`): one unit per (duty family or chemistry node) ×
fuel — expect ~55 service units and ~40 chemistry-node units, ~98 total before hybrids;
(c) the supply units the options library lacks: PV, battery (state hours in the ID, e.g.
`battery_2h`), thermal store, electrolyser, anaerobic digestion, CHP variants; (d) the four
hybrid units of PD2 at a small set of fixed ratios (`pv_battery`, `chp_thermal_store`,
`electrolyser_battery`, `hp_thermal_store`), ~12 rows, `is_hybrid = TRUE`. Chemistry-node
units are keyed on `process_id` — use the **CaRB3 register `process_id`** (e.g.
`kiln_pyroprocessing`), not the COMIT code; write the COMIT code into `unit_name` or the
notes so the lineage lane can match.

Naming: `<device>_<qualifier>_<fuel>` lower snake, e.g. `boiler_lt_gas`, `kiln_dry_coal`,
`heat_pump_lt_air`, `eaf_elec`, `chp_gas_turbine`. Fuels: `gas`, `hydrogen`, `biomass`,
`lpg`, `oil`, `coal`, `coke`, `wdf`, `elec`, `biomethane`.

Product carriers: a chemistry unit produces a mass product (`clinker`, `cement`, `steel_crude`,
`glass`, `lime`, `paper`, `ammonia`, …). Write those as rows of
`docs/notes/data/build/carrier_products_units.csv` with the `carrier.csv` columns
(`carrier_kind = product`, `denominator_kind = mass`). Do not edit `carrier.csv`.

## Phase 2 — attributes and coefficients

Fill `unit.csv`: `capex` (£m per capacity unit, 2021 GBP), `fixed_opex`, `lifetime`,
`availability_factor`, `capacity_to_activity_factor` (1.0 for service units in PJ/yr; 0.031536
PJ/yr per MW for MW-rated units), `area_per_capacity` (**only** PV, solid biomass storage
yards, solar thermal — cite m²/MW), `emissions_released` (1.0 unless a capture unit — but see
D15: capture rate lives in the coefficients), `min_viable_scale`, `provenance`, `confidence`.
Source order: published UK first (DESNZ/BEIS 2018 Industrial Fuel Switching, DESNZ 2024
electrification of industrial heat, Element Energy/Jacobs, CCC Sixth Carbon Budget
technology tables, DESNZ generation cost reports for PV/CHP/batteries, BEIS heat pump cost
studies), then the COMIT workbook
`data_template_archive/comit_input_1_4_0_public_updated.xlsx` (sheets `Technologies`,
`technology_input_output`, `technology_cost`; read with R `readxl`, the sheets have 2 title
rows) with `provenance = comit_reuse`, then BREF (`bref`), then proxies (`proxy`, low
confidence). **Blank beats guess.** Costs originally in £/kW or €/kW must be converted to £m
per PJ/yr of output using the availability you state — show the arithmetic in the pointer.

Write `docs/notes/data/unit_input_output.csv` with the §3.6 columns plus `provenance` and
`confidence`: per unit, the primary output at +1.0, the fuel input at −1/η with
`is_fuel_input = TRUE`, auxiliary electricity, reject heat as a positive `is_reject` row on a
low band (B5 — cite the BREF/roadmap fraction; blank row absent if no source), declared
`co2_process` rows for chemistry (stoichiometry, cite), and **no** `co2_fuel_*` rows (A6
derives them). Heat pump COPs by grade lift (B4), cited. Every non-ambient unit must close on
energy to 1e-6 (V2); flag `draws_ambient` ones.

Write `docs/notes/data/unit_bill_of_materials.csv` (§3.5.2 + `provenance`) for every hybrid.

Check script: unit IDs unique; every worked-example unit present; every `carrier_id` resolves
to `carrier.csv` ∪ your product staging; exactly one `is_primary_output` and ≤1
`is_fuel_input` per unit; BOM shares sum to 1; `[REF_ID]`s resolve. Then `DONE_units.md`,
reply with its path.
