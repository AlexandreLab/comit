# Lane `lineage` — the 397-row COMIT technology lineage table (T8, data-migration A1–A3, B1–B2)

Read `docs/notes/data/build/00_CONVENTIONS.md`, the data-migration document
`docs/specs/2026-08-28-carb3-site-energy-system-data-migration.md` Groups A and B, spec §3.5
(D13: a unit is family-or-node × fuel) and §10.2 (V1b compares through this table). The unit
list is `docs/notes/data/unit.csv` (read only; request missing units in your DONE file and
leave `unit_id` blank on that row with `disposition = unmapped`).

Produce `docs/notes/data/comit_technology_lineage.csv`: **exactly one row per technology in
`docs/notes/data/emissions_source_classification.csv` (397 rows)**, columns:
`technology_code,technology_name,sector,technology_category,output_commodity,carrier_id,unit_type,abatement,disposition,unit_id,fuel_carrier_id,reason,notes`

- `carrier_id`, `unit_type`, `abatement` are the A1 split of `technology_category` into three
  orthogonal columns: the fuel carrier (→ `carrier.csv`), the device kind (boiler, heat_pump,
  kiln, furnace, dryer, chp, motor, …), and the bolt-on (`ccs`, blank). `Standard_FF` (A2) and
  `Dry kiln` (A3) must be resolved explicitly — read the technology name and its
  `emitting_fuel_commodities` in `emissions_source_classification.csv` and the workbook sheet
  `technology_input_output` (R `readxl`, 2 title rows) to find the actual fuel; say what you did.
- `disposition` ∈ {collapsed (a fuel variant folded into unit X), preserved (kept as its own
  unit — the 25 CCS, 31 heat pump, 1 dry kiln rows and every chemistry node), dropped (with a
  reason — e.g. hydrogen-production sector rows that are not site units), unmapped}. Counts
  must sum to 397 with **zero** rows lacking a disposition.
- `unit_id` → `unit.csv` for collapsed/preserved rows; `fuel_carrier_id` must equal that unit's
  `fuel_carrier_id`.

Check script: 397 rows, unique `technology_code`, every disposition set, every `unit_id`
and `carrier_id` resolves, disposition counts printed. `DONE_lineage.md`, reply with its
path. No web research is needed for this lane; it is a reconciliation.
