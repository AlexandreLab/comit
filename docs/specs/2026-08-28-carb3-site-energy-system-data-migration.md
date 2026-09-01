# CaRB3 Site Energy System — Data Migration

**Status:** Draft v1 for review
**Date:** 2026-08-28
**Scope:** Great Britain · CaRB3 **Factory class** only (55 activities)
**Part of:** the v2 migration plan. The process and decarbonisation-option tables.

**This plan is five documents.** Read the overview first; the other four are independent.

| Doc | For | |
|---|---|---|
| [Overview and decisions](2026-08-28-carb3-site-energy-system-overview.md) | everyone — start here |  |
| [Architecture](2026-08-28-carb3-site-energy-system-architecture.md) | modellers |  |
| [Spec changes and tests](2026-08-28-carb3-site-energy-system-spec-changes.md) | whoever writes the v2 spec |  |
| [Data migration](2026-08-28-carb3-site-energy-system-data-migration.md) | whoever owns the data tables | **you are here** |
| [Delivery](2026-08-28-carb3-site-energy-system-delivery.md) | whoever schedules the work |  |

> **This plans work; it does not specify it.** The v2 specification itself
> (`2026-08-28-carb3-site-energy-system-implementation.md`) does not exist yet — writing it is task T4.

---

## TODO list — processes and decarbonisation options

**This document is the list.** Groups run in order; items inside a group are parallel.
There is deliberately no root `TODOS.md` — a second copy of these items would drift from
this one, and this document is already indexed and cross-linked from the other four.

### Group A — taxonomy split (blocks everything)

- **A1.** Split `technology_category` (11 values, 397 rows) into three orthogonal columns:
  `carrier_id`, `unit_type`, `abatement`. Today it conflates fuel carrier (Electricity,
  Natural gas, Hydrogen, Biomass, Oil, Coal, Steam), device (Heat pump 31, Dry kiln 1),
  and bolt-on (CCS 25).
- **A2.** Resolve `Standard_FF` (39 rows). A catch-all that must become explicit carriers
  or it silently defeats the whole carrier model.
- **A3.** Resolve `Dry kiln` (n=1). Obvious taxonomy leak; decide unit_type vs mis-tag.
- **A4.** Build the `carrier` table from the 18 fuel commodity codes; add `heat@band`
  grades and the cascade ranking.
- **A5.** Derive the duty families from the 94 process codes, **excluding the 16
  sector-root codes** (`ICH`, `ICN`, `ICR`, `IEE`, `IFD`, `IME`, `INF`, `IOI`, `IPR`,
  `ITX`, `IVH`, `ICM`, `IGL`, `IIS`, `ILM`, `IPP`) which are sector-level demand
  commodities and not duties. Expect 12 service families and 14 chemistry nodes; classify
  each per Issue 2. An earlier draft said 24 families, which counted the sector roots.

### Group B — the collapse

- **B1.** Collapse the 293 pure fuel-variant technologies into units plus carrier
  bindings. **Reconcile row counts explicitly** — 397 in, units + bindings out, no orphans.
- **B2.** Preserve the 57 non-fuel technologies (CCS 25, heat pump 31, dry kiln 1) as
  distinct unit archetypes; do not let them collapse.
- **B3.** Assign `grade_in`/`grade_out` to every unit and every heat duty
  (LTH/HTH/STM/DRY/SPC). Non-nullable — see failure mode #6.
- **B4.** Re-derive heat pump COP from grade lift, replacing the flat `33.333` (LTH, DRY,
  **and STM**) and `25` (SPC) coefficients.
- **B5.** **Reject-heat coefficients — without these, waste heat recovery does not work at
  all.** For every heat-consuming unit, state the fraction of input rejected and the grade
  it is rejected at, as a *positive* `unit_input_output` coefficient on a low-grade heat
  carrier. Grades alone (B3) say what a unit can *accept*, not what it *throws away*; with
  no reject coefficient every unit rejects zero, the cascade has nothing to cascade, and
  the 28 `efficiency_heat_recovery` options in the library stay unmodellable. Use D10
  evidence tiers — expect most rows to start at the weakest tier, and say so rather than
  hiding it.

### Group C — decarbonisation options

- **C1.** Normalise `displaces` in `decarbonisation_options_library.csv`: 51 free-text
  values (`gas`, `natural_gas`, `gas; oil`, `coke; coking coal; natural gas`) → `carrier_id`
  references. This column is the de facto carrier reference and is unnormalised.
- **C2.** **Build the missing join.** The 1109 option mappings are keyed to CaRB3
  `process_id` strings; the 397 technologies are keyed to COMIT `output_commodity`. There
  is no join. The only bridge is the hand-curated `carb3_comit_crosswalk.csv`. Replace it
  with an option→unit mapping.
- **C3.** Add a `route_change` flag for whole-route options — H2-DRI+EAF, molten oxide
  electrolysis, cupola→induction. `README_decarbonisation_options.md` challenge #7 already
  asks for this and today anchors them to a single dominant process row.
- **C4.** Add exclusivity groups for interacting options (challenge #8: AD heat
  integration vs biogas upgrading are alternatives, not additive; biochar options compete
  for one UK feedstock pool).
- **C5.** Add the **supply units** the library has no concept of: PV, battery, thermal
  store, electrolyser, AD, CHP. All 134 current options are demand-side.
- **C6.** Add the **hybrid units** (PD3), each at a fixed sizing ratio: `pv_battery`,
  `chp_thermal_store`, `electrolyser_battery`, `hp_thermal_store`. Roughly 3 ratios × 4
  pairings, so around 12 rows, not a combinatorial explosion. Keep the ratio set small and
  deliberately chosen — every ratio is a separate Tier A dispatch run.
- **C7.** Populate `unit_bill_of_materials` for every hybrid unit: component capacity
  share, capex share and lifetime. This is what V20 (b) and (c) assert against, and what
  lets outputs answer *how much battery does GB industry need*.
- **C8.** Populate `unit_eligibility` including the minimum-scale screening thresholds
  that replace the MILP binary.

### Group D — new data the model does not have

- **D1.** Roof and land area per premise, or a per-activity usable-area fraction. **The
  single biggest gap** — without it C12 is unbounded and the LP builds infinite PV.
- **D2.** Export price and per-carrier import/export tariff series in
  `scenario_parameters`.
- **D3.** Biomethane as an `infrastructure_scenario` carrier with regional availability
  and tariff. Its constraint is a shared catchment, which D2 forbids modelling per-premise.
- **D4.** Archetype definitions and the ψ/β/χ/**ε** coefficient tables from Tier A, one
  constant per coefficient per unit. **ε is non-nullable on flexible-load hybrids** —
  without it `electrolyser_battery` is strictly dominated by a bare electrolyser and never
  gets built, so the whole hybrid-unit mechanism silently does nothing (failure mode #8).

### Group E — hygiene, unblocked by the above

- **E1.** Validator for all seven Family-B files (Issue 4) — **do this first**, on today's
  data, for a green baseline.
- **E2.** Fix the vision doc λ→ξ bug at lines 146 and 240.
- **E3.** Fix the worked example's wrong cross-reference at line 372 (`§1.5` should be
  `§1.6`) and the inconsistent withholding set at line 414 (omits `§1.9`).
- **E4.** Reconcile the worked example's A3 shares against
  `activity_process_energy_profile.csv` — the example uses coal 0.97 to the kiln, the data
  asset says 1.0.
