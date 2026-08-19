# Reference datasets for the discussion notes

Machine-readable companions to the notes in `docs/notes/`. These are **derived
reference data, not model inputs** — COMIT never reads this directory. They exist
so analysts can filter, join and amend the classifications without re-deriving
them from the workbook each time.

| File | Companion note | Regenerate with |
|---|---|---|
| `emissions_source_classification.csv` | [14_emissions_source_split.md](../14_emissions_source_split.md) | [`../examples/build_emissions_classification.R`](../examples/build_emissions_classification.R) |
| `carb3_factory_processes.json` | [15_carb3_process_comparison.md](../15_carb3_process_comparison.md) | *(supplied verbatim — not generated)* |
| `comit_sector_processes.json` · `.csv` | [15_carb3_process_comparison.md](../15_carb3_process_comparison.md) | [`../examples/build_comit_process_taxonomy.R`](../examples/build_comit_process_taxonomy.R) |
| `carb3_comit_crosswalk.csv` | [15_carb3_process_comparison.md](../15_carb3_process_comparison.md) | *(curated by hand — not generated)* |

---

## `emissions_source_classification.csv`

One row per technology (397 rows, 22 columns, unique on `technology_code`), recording how much
of its **direct** emissions come from process chemistry versus fuel combustion.

Generated from `data_template_archive/comit_input_1_4_0_public_updated.xlsx`
(public reference workbook, v1.4.0) at fuel-factor year **2021**.

> **The values are placeholders.** The `commodities` and `Fuel_emissions` sheets of
> the public workbook are labelled *"dummy figures"* / *"Mostly dummy numbers"*. The
> **classification and method are real**; the absolute intensities are not. Regenerate
> against your production workbook before quoting any number.

### Regenerating

```bash
Rscript docs/notes/examples/build_emissions_classification.R \
  path/to/comit_input.xlsx 2021 \
  docs/notes/data/emissions_source_classification.csv
```

The script takes `<workbook> [ref_year] [out_csv]`. Change `ref_year` to pick a
different year's fuel emission factors — several factors (grid electricity in
particular) vary annually, so `energy_*` columns are year-specific while
`process_*` columns are not.

### Amending

Prefer **fixing the workbook and regenerating** over hand-editing this CSV: every
column below is derived, so a manual edit is silently lost on the next run. The
source of each column is given so you know which sheet to change.

Two columns cannot be changed from the workbook at all — `energy_direct` vs
`energy_indirect` depends on a hardcoded commodity list in `R/fct_emissions.R`.
See §6 of note 14.

### Columns

| Column | Type | Source | Meaning |
|---|---|---|---|
| `technology_code` | string | `Technologies!code` | Primary key. Joins to every output sheet's `Technology_code`. |
| `technology_name` | string | `Technologies!name` | Description. |
| `sector` | string | `Technologies!sector` | One of 17 (16 industrial + `Hydrogen`). |
| `technology_category` | string | `Technologies!technology_category` | Fuel/technology grouping (`CCS`, `Natural gas`, `Electricity`, …). |
| `output_commodity` | string | `Technologies!output_commodity` | What the technology produces. |
| `output_unit` | string | `Technologies!output_unit` | **Denominator of every `*_per_unit` column** — `Mt`, `PJ` or `kt`. Not comparable across differing units. |
| `emission_class` | enum | *derived* | `A_pure_process`, `B_process_dominant`, `C_mixed_energy_dominant`, `D_pure_energy`, `E_zero_direct`. See classification rule below. |
| `process_share_pct` | float | *derived* | `100 × process_total / direct_total`. Blank when `direct_total` is 0. Can exceed 100 or go negative where `energy_direct` is negative (by-product credits). |
| `process_co2_kt_per_unit` | float | `technology_input_output` × `INDCO2P` | Process CO₂ per unit of output, kt. |
| `process_ch4_kt_per_unit` | float | `technology_input_output` × `INDCH4P` | Process CH₄, **already in kt CO₂e** — no GWP conversion is applied anywhere in the model. |
| `process_n2o_kt_per_unit` | float | `technology_input_output` × `INDN2OP` | Process N₂O, likewise already kt CO₂e. |
| `process_total_kt_per_unit` | float | *derived* | Sum of the three above. Independent of fuel mix and of `ref_year`. |
| `energy_direct_kt_per_unit` | float | `technology_input_output` × `Fuel_emissions` | Combustion emissions from **direct** fuels at `fuel_factor_year`. Negative values are legitimate (by-product / self-generation credits). |
| `energy_direct_biomass_zerorated_kt_per_unit` | float | *derived* | `energy_direct` recomputed with `Biomass and organic waste` fuels set to a zero factor — i.e. **what the model actually books** under the default `zero_emissions_from_biomass = TRUE`. Differs from `energy_direct` for 50 technologies. |
| `energy_indirect_kt_per_unit` | float | as above, indirect commodities | Emissions occurring off-site (grid electricity, mains hydrogen). **Excluded** from `direct_total` and from `process_share_pct`. |
| `consumes_biomass_fuel` | bool | `commodities!commodity_category` | Whether any consumed fuel is in the biomass category. `TRUE` for 57 technologies — these are the rows where the two `energy_direct*` columns can diverge and where BECCS negative emissions arise. |
| `direct_total_kt_per_unit` | float | *derived* | `process_total + energy_direct`. The site-attributable total. |
| `emissions_released` | float | `Technologies!emissions_released` | Fraction **not** captured (1 = no CCS, 0.05 = 95% capture). **Not applied** to the `*_per_unit` columns — they are gross. Multiply yourself, but see the CCS caveat below. |
| `n_emitting_fuel_inputs` | int | *derived* | Count of emitting fuel commodities consumed. |
| `emitting_fuel_commodities` | string | `technology_input_output` | `;`-separated commodity codes, direct and indirect together. |
| `retrofit_to` | string | `Technologies!retrofit_to` | Base technology this one retrofits, if any. Retrofit costs are differenced against it. |
| `fuel_factor_year` | int | script argument | Year whose fuel emission factors produced the `energy_*` columns. |

### Classification rule

Applied to `process_total` and `energy_direct` (indirect emissions are ignored):

| Class | Condition | Reading |
|---|---|---|
| `A_pure_process` | process > 0, energy_direct = 0 | Emits only through chemistry — already fuel-switched or unfuelled. Fuel switching cannot abate it. |
| `B_process_dominant` | process > 0, share ≥ 50% | Majority of direct emissions are chemistry. Kilns, reformers, refineries. |
| `C_mixed_energy_dominant` | process > 0, share < 50% | Both matter; fuel switching gets you part-way. |
| `D_pure_energy` | process = 0, energy_direct ≠ 0 | Fully abatable by fuel switching. |
| `E_zero_direct` | direct_total = 0 | No direct emissions — electric/hydrogen technologies, or non-emitting demand technologies. Check `energy_indirect` before calling it clean. |

### Two traps when applying `emissions_released`

1. **CCS never abates non-CO₂.** `nonCO2_process_captured_direct` and
   `nonCO2_fuel_captured_direct` are hardcoded to `0` in `R/fct_emissions.R:327-328`,
   and the non-CO₂ released term carries no `emissions_released` factor. So
   `emissions_released` applies to `process_co2_kt_per_unit` **only** — never to the
   CH₄ or N₂O columns.
2. **Biomass is zero-rated before capture, not after.** Fuels in the
   `Biomass and organic waste` category have their factor set to 0 when
   `zero_emissions_from_biomass` is on, while the captured stream still counts —
   which is what makes BECCS net negative. `energy_direct_kt_per_unit` is computed
   **without** that zero-rating (gross combustion); use
   `energy_direct_biomass_zerorated_kt_per_unit` to match what the model books.
   `direct_total_kt_per_unit`, `process_share_pct` and `emission_class` are all
   built on the **gross** figure, so a biomass-fired technology classed
   `D_pure_energy` here may book zero direct emissions in a run.


---

## `carb3_factory_processes.json`

The supplied CaRB3 *Factory*-class list, **stored verbatim**: 55 activities, 128
activity-process pairs (76 distinct process names), 247 equipment entries (218
distinct).

```json
{ "<activity>": { "<process>": ["<equipment>", ...] } }
```

Provenance: supplied as a dictionary of processes and associated technologies per
CaRB3 activity. **Not verified against the NDBS source document** — activity names
are as supplied. Amend by editing directly; nothing regenerates this file.

## `comit_sector_processes.json` and `.csv`

COMIT's equivalent taxonomy in the **same three-level shape**, so the two can be
compared directly: 17 sectors, 94 sector-process pairs (30 process families), 397
technologies.

```json
{ "<sector>": { "<process description>": ["<technology name>", ...] } }
```

The middle level is the technology's **primary output commodity** — the energy
service or product it delivers. That is the closest structural analogue to a CaRB3
"process", but the two are not the same kind of thing: see §1 of note 15.

The `.csv` is the flat form of the same data, carrying the codes needed for joins:

| Column | Source |
|---|---|
| `sector` | `Technologies!sector` |
| `process_commodity` | `Technologies!output_commodity` |
| `process_description` | `commodities!description` for that commodity |
| `technology_code` | `Technologies!code` — joins to `emissions_source_classification.csv` and to every output sheet |
| `technology_name` | `Technologies!name` |
| `technology_category` | `Technologies!technology_category` — the axis COMIT's variants actually vary on |
| `output_unit` | `Technologies!output_unit` |

Regenerate with:

```bash
Rscript docs/notes/examples/build_comit_process_taxonomy.R path/to/comit_input.xlsx
```

## `carb3_comit_crosswalk.csv`

One row per CaRB3 activity (55 rows), mapping it to COMIT.

| Column | Meaning |
|---|---|
| `carb3_activity` | Activity name, matching a top-level key in `carb3_factory_processes.json` |
| `carb3_code` | FA code from note 11 (Table 28 of the NDBS report). **Blank on 9 rows** where note 11 gives no code — mostly the Mineral Production family. Not guessed. |
| `comit_sector` | Matching COMIT sector, blank where none. Populated on 43 of 55 rows. |
| `coverage` | `direct` (31) · `absent` (11) · `partial` (3) · `catch-all` (3) · `gap` (3) · `generic` (2) · `weak` (1) · `ambiguous` (1) |
| `comit_process_analogue` | Which COMIT process(es) the activity's operations collapse into |
| `notes` | Rationale, and what is lost in the mapping |

**This file is analyst judgement**, built on the sector↔activity mapping in note 11
§3-4. The `coverage` and `comit_process_analogue` columns are interpretive, not
derived — review them before relying on them. Edit by hand; nothing regenerates it.
