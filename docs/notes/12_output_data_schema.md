# COMIT output data schema — what a model run actually produces

**Question this note answers:** after COMIT solves, what does it hand back? What are the tables, what are the exact field names and types, what is the grain (one row = what?), and — concretely — what does the output look like for a *single site*?

Written as a reference for anyone consuming COMIT outputs programmatically (dashboards, Python post-processing, headless pipelines — see [07](07_high_level_testing_strategy.md) and [08](08_python_redesign_approach.md)).

Everything below was extracted from a real run:
`outputs/comit_output_20260729_15h14m59s.zip` (package version 1.4.0, run 2026-07-29, public/artificial input data).

---

## 1. The physical artefact

A run produces a **zip archive** named `comit_output_<YYYYMMDD>_<HH>h<MM>m<SS>s.zip` containing two files:

| File | Role |
|---|---|
| `Scenario_<input_stem>.xlsx` | **The outputs.** 11 sheets (~20 MB for a 1,026-site national run). Built by copying `inst/output_template/output_template.xlsx` and writing Excel *tables* into it. |
| `<input_stem>.xlsx` | A verbatim **copy of the input workbook** used for the run, so a result set is self-describing and reproducible. |

The prefix `Scenario_` reflects the model mode (the `Log` sheet records `Model type: Scenario`); counterfactual/least-cost runs are named for their mode.

### Sheet inventory

| Sheet | Kind | Written by |
|---|---|---|
| `Title` | Metadata | run stamp: package version, run date, completion time |
| `Info` | Static | contents page + unit-conversion notes |
| `Definitions` | Static | field-level data dictionary (see §7 for where it drifts from reality) |
| `DetailedTables` | Static formulas | pivot-style summary tables that reference the data sheets |
| `Sites_info` | **Data table** | `create_sites_info_tables()` |
| `Costs` | **Data table** | `create_cost_tables()` → `adjust_cost_tables()` |
| `Emissions` | **Data table** | `create_emissions_tables()` |
| `Outputs` | **Data table** | `create_outputs_table()` |
| `Energy` | **Data table** | `create_energy_tables()` |
| `Infrastructure` | **Data table** | `create_infrastructure_tables()` |
| `Log` | Diagnostics | every message emitted during the solve |

Assembly happens in `R/fct_create_output_tables.R`: `combine_tables()` builds the named list, `create_output_xlsx()` writes each element as a same-named Excel table.

When `model_parameters$output_cluster_level` is `TRUE`, five extra orange tabs are appended — `Costs_cluster`, `Outputs_cluster`, `Emissions_cluster`, `Energy_cluster`, `Infrastructure_cluster` (§6). They are **off by default**, which is why the reference run has only the blue site-level tabs.

---

## 2. The shape convention: long in categories, wide in years

Every data table follows the same pattern:

```
[ ... dimension columns (character/logical) ... ][ ... one numeric column per model year ... ]
```

The year columns are **generated from the input parameters**, not fixed:

```
seq(model_parameters$start_year, model_parameters$end_year, by = model_parameters$timestep)
```

In the reference run that is `start_year = 2021`, `end_year = 2051`, `timestep = 5` → columns **`2021`, `2026`, `2031`, `2036`, `2041`, `2046`, `2051`**.

> **Do not hard-code the year columns.** Any consumer should discover them by pattern (`^2\d{3}(_TWh|_ktCO2e)?$`) or by re-reading `model_parameters`. Changing the timestep changes the column set and therefore the schema.

`Energy` is the one sheet with **two** year-column families — `<year>_TWh` and `<year>_ktCO2e` — carrying fuel volume and the emissions from that fuel side by side.

---

## 3. Grain summary

| Sheet | One row = | Rows (national run) | Rows for one site (site 43) |
|---|---|---|---|
| `Sites_info` | one site | 1,026 | 1 |
| `Costs` | site × technology × cost type (+ infra rows) | 156,139 | 272 |
| `Outputs` | site × technology (used capacity) | 30,379 | 53 |
| `Emissions` | site × technology × emissions category × pollutant split | 24,042 | 56 |
| `Energy` | site × technology × input commodity | 36,764 | 89 |
| `Infrastructure` | site × infrastructure variable type | 3,167 | 5 |

So a single site is described by **476 rows across six tables**. Each row carries 7 numbers (one per model year), except `Energy` rows which carry 14 (TWh + ktCO₂e) — about **3,950 data points per site**. Note `Costs` is by far the widest: 272 rows for one site, of which only **65 are non-zero** in this run. Zero-filled rows are the norm, not the exception.

---

## 4. Field-by-field schema

Types below are as read back from the workbook (`readxl`), which is what any consumer sees. `Nullable` means blank/`NA` legitimately occurs.

### 4.1 `Sites_info` — 8 fields

**Grain:** one row per modelled site. **Key:** `site_ID`.

| Field | Type | Nullable | Domain / example | Meaning |
|---|---|---|---|---|
| `site_ID` | numeric (integer-valued) | no | `43` | Primary key for every other sheet. 1…1,026 in this run. |
| `site_traded_status` | character | no | `Traded`, `Non-traded`, `Non-traded-non-point` | UK ETS scope of the site. |
| `cluster` | character | yes | `Teesside`, `Humberside`, `Humberside2`, `Merseyside`, `Grangemouth`, `Peterhead`, `South Wales`, `Southampton`, `Medway`, `Londonderry` (10) | Nearest hydrogen/CO₂ cluster point (`H2_point` in the input). `NA` where unassigned. |
| `site_name` | character | yes | `BOC Ltd` | Operator/site name from NAEI. |
| `Latitude` | numeric (double) | yes | `54.60403` | WGS84. |
| `Longitude` | numeric (double) | yes | `-1.213661` | WGS84. |
| `region` | character | yes | 12 UK ITL1 regions, e.g. `North East (England)` | Region of the site itself. |
| `PlantID` | numeric | yes | `13763` | NAEI plant identifier — the join key back to source inventory data. |

> Aggregated small sites: where several sub-threshold point sources were merged (see [02_site_data.md](02_site_data.md)), one `site_ID` represents several physical plants. `Sites_info` does **not** carry the member count — the `Site_count` field described in `Definitions` belongs to a `sites` summary table that `create_sites_tables()` computes but `combine_tables()` never writes to the workbook (§7).

### 4.2 `Costs` — 21 fields

**Grain:** one row per `Sector_infrastructure` × `site_ID` × `Primary_output` × `Technology_code` × `Cost_type`, plus infrastructure rows keyed differently (below).
**Units:** **£ million per year**, rebased to `model_parameters$base_price_year` (2021) using GDP deflators via `base_year_adjustment()`.

| Field | Type | Nullable | Domain / example | Meaning |
|---|---|---|---|---|
| `Sector_infrastructure` | character | no | 17 sector names (`Chemicals`, `Cement`, `Iron & steel`, `Refineries`, `hydrogen_conversion`, …) **or** 7 infrastructure codes (`CO2_C2S`, `CO2_pipe_new_capacity`, `CO2_pipe_available_capacity`, `CO2_truck_used_capacity`, `H2_pipe_new_capacity`, `H2_pipe_available_capacity`, `H2_truck_used_capacity`) | Discriminator: sector row vs infrastructure row. 24 values total. |
| `site_ID` | numeric | yes | `43` | `NA` on `CO2_C2S` rows (cluster→storage costs are not site-attributable). |
| `site_traded_status` | character | yes | as `Sites_info` | Joined from `Sites_info`. |
| `cluster` | character | yes | `Teesside` | Joined from `Sites_info` via `site_ID`. |
| `cluster_rad` | character | yes | `<25km`, `25-30km`, `>30km` | Distance band from site to cluster centre. |
| `Storage_site` | character | yes | `Southern North Sea`, `East Irish Sea`, `Northern and Central North Sea`, `Southampton Sea` | Populated **only** on the 18 `CO2_C2S` rows; `NA` elsewhere. |
| `Primary_output` | character | yes | `ICHHTH`, `IHVC`, `IAM` | Commodity code the technology produces. `NA` on infrastructure rows. |
| `Output_description` | character | yes | `High temperature heat for the other chemicals subsector` | Human-readable expansion of `Primary_output`. |
| `Technology_code` | character | yes | `ICHHVCSCQB01` | Join key to the input `Technologies` sheet. `NA` on all 4,244 infrastructure rows. |
| `Technology_description` | character | yes | `Steam cracker with post-combustion CCS with biomass boiler…` | |
| `Technology_category` | character | yes | `Biomass`, `CCS`, `Coal`, `Dry kiln`, `Electricity`, `Heat pump`, `Hydrogen`, `Natural gas`, `Oil`, `Standard_FF`, `Steam` (11) | Fuel/technology grouping. |
| `Traded_NonTraded` | **logical** | yes | `TRUE` / `FALSE` | `TRUE` = site inside UK ETS. `NA` on infrastructure rows. Note this is a *boolean*, unlike the character `site_traded_status`. |
| `Cost_type` | character | yes | `Capex`, `Capex_lump`, `Opex`, `Fuel cost`, `Carbon cost` | `NA` on the 18 `CO2_C2S` rows. See cost-type semantics below. |
| `Sector_group` | character | yes | `Industry`, `Refineries` | Coarse grouping. `NA` on infrastructure rows. |
| `2021` … `2051` | numeric (double) | no (0-filled) | `0.204928` | £m incurred **in that year**, un-discounted back to a yearly figure and rebased to 2021 prices. |

**Cost-type semantics** (this is the field most often misread):

| `Cost_type` | What it is |
|---|---|
| `Capex` | Investment **annuitised** — spread over the equipment lifetime as level loan payments at the interest rate, truncated at `end_year`. Sums to the financed cost. |
| `Capex_lump` | The **same investment as a single spike** in the build year — no borrowing, no spreading, no discounting. |
| `Opex` | Fixed annual running cost of installed capacity. |
| `Fuel cost` | Fuel bill for the activity in that year. |
| `Carbon cost` | Carbon price applied to residual emissions (traded vs untraded price by site status). |

`Capex` and `Capex_lump` are **two views of the same money** — never sum them together. In the site-43 example, `CO2_pipe_new_capacity` shows `Capex_lump = 0.2049` in 2031 only, while `Capex = 0.01114` repeats across 2031–2051: the lump spike versus the annuitised stream. See [09_objective_function.md](09_objective_function.md) §4 for the finance mechanics.

### 4.3 `Outputs` — 19 fields

**Grain:** one row per `site_ID` × `Primary_output` × `Technology_code`.
**Units:** per the `Unit` column — activity, not money.

| Field | Type | Nullable | Domain / example | Meaning |
|---|---|---|---|---|
| `Sector` | character | no | 17 values incl. `Chemicals`, `hydrogen_conversion` | Industrial sector. |
| `site_ID` | numeric | no | `43` | |
| `site_traded_status` | character | yes | as `Sites_info` | |
| `cluster` | character | yes | `Teesside` | |
| `cluster_rad` | character | yes | `<25km`, `25-30km`, `>30km` | |
| `Primary_output` | character | no | `IHVC` | Commodity produced. |
| `Output_description` | character | yes | `High-value chemicals (demand commodity in Mt)` | |
| `Technology_code` | character | no | `ICHHVCSCQB01` | |
| `Technology_description` | character | yes | `Steam cracker with post-combustion CCS…` | |
| `Technology_category` | character | yes | 11 values as `Costs` | |
| `Capacity` | character | no | **`used_capacity` only** | The variable type reported. `new_capacity` / `available_capacity` exist in the solver but are *not* exported — build activity must be inferred from `Capex_lump` in `Costs` or from `Infrastructure` for pipes. |
| `Unit` | character | yes | `PJ` (26,810 rows), `Mt` (3,444), `kt` (122) | Unit of the year columns — **varies row to row**, so never sum across rows without grouping by `Unit`. |
| `2021` … `2051` | numeric | no (0-filled) | `0.0156219` | Used capacity / activity in that year, in `Unit`. |

### 4.4 `Emissions` — 22 fields

**Grain:** one row per `site_ID` × `Technology_code` × `Emissions_category` × (`CO2_NonCO2`, `Emission_type`, `ghg_type`) split.
**Units:** **kt CO₂e per year** (kt of the specific gas where `ghg_type` is `CH4`/`N2O`).

| Field | Type | Nullable | Domain / example | Meaning |
|---|---|---|---|---|
| `Emissions_category` | character | no | `Direct (total CO2e)`, `Direct (split by ghg type)`, `Direct_and_Indirect`, `Captured`, `Electricity`, `Hydrogen`, `Negative` (7) | **The most important field on the sheet — you must filter on it.** See below. |
| `Sector` | character | no | `Chemicals` | |
| `site_ID` | numeric | no | `43` | |
| `site_traded_status` | character | yes | as `Sites_info` | |
| `cluster` | character | yes | `Teesside` | |
| `cluster_rad` | character | yes | `<25km` | |
| `Primary_output` | character | no | `IHVC` | |
| `Output_description` | character | yes | `High-value chemicals (demand commodity in Mt)` | |
| `Technology_code` | character | no | `ICHHVCSCQB01` | |
| `Technology_description` | character | yes | `Steam cracker with post-combustion CCS…` | |
| `Technology_category` | character | yes | 11 values as `Costs` | |
| `CO2_NonCO2` | character | yes | `CO2`, `NonCO2` | `NA` on `Direct (total CO2e)`, `Electricity`, `Hydrogen`, `Negative` rows. |
| `Emission_type` | character | yes | `Energy`, `Process` | Combustion vs process emissions. `NA` on `Electricity`, `Hydrogen`, `Negative` rows. |
| `ghg_type` | character | yes | `CO2`, `CH4`, `N2O`, `total_CO2e` | Populated only on the two `Direct …` categories. |
| `Sector_group` | character | yes | `Industry`, `Refineries` | |
| `2021` … `2051` | numeric | no (0-filled) | `-4.708393` | kt in that year. **Can be negative** (`Negative` category = bioenergy CO₂ removals). |

**Which category to use** — the categories overlap by design, so summing the sheet raw double-counts:

| `Emissions_category` | Rows | `ghg_type` | Use it for |
|---|---|---|---|
| `Direct (total CO2e)` | 3,645 | `total_CO2e` | **Headline direct emissions.** One row per technology × `Emission_type`, all gases already combined. |
| `Direct (split by ghg type)` | 10,935 | `CO2`, `CH4`, `N2O` | The same total decomposed by gas — sums to `Direct (total CO2e)`. |
| `Direct_and_Indirect` | 6,463 | `NA` | Direct plus upstream electricity/hydrogen emissions. |
| `Electricity` | 2,561 | `NA` | Indirect emissions from purchased electricity only. |
| `Hydrogen` | 118 | `NA` | Indirect emissions from purchased hydrogen only. |
| `Captured` | 226 | `NA` | CO₂ captured by CCS, split `Energy` / `Process`. |
| `Negative` | 94 | `NA` | Removals — negative values. |

For **net industry emissions**, sum `Direct (total CO2e)` + `Negative`.

### 4.5 `Energy` — 27 fields

**Grain:** one row per `site_ID` × `Technology_code` × `Input_commodity`.
**Units:** two families — `<year>_TWh` for fuel volume, `<year>_ktCO2e` for the emissions from that fuel.

| Field | Type | Nullable | Domain / example | Meaning |
|---|---|---|---|---|
| `Sector` | character | no | `Chemicals` | |
| `site_ID` | numeric | no | `43` | |
| `site_traded_status` | character | yes | as `Sites_info` | |
| `cluster` | character | yes | `Teesside` | |
| `cluster_rad` | character | yes | `<25km` | |
| `Primary_output` | character | no | `ICHHTH` | |
| `Output_description` | character | yes | `High temperature heat for the other chemicals subsector` | |
| `Technology_code` | character | no | `ICHHTHNGA01` | |
| `Technology_description` | character | yes | `High-temperature heat technology based on natural gas…` | |
| `Technology_category` | character | yes | 11 values as `Costs` | |
| `Input_commodity` | character | no | 22 codes: `INDDISTELC`, `IND_NGABOM`, `INDMAINSHYG`, `INDCOA`, `IND_SOLIDBIO`, `PRCOILCRD`, `INDNEU*`, … | The fuel/material consumed. |
| `Fuel_category` | character | no | `Biomass and organic waste`, `Coal`, `Electricity`, `Gas`, `Hydrogen`, `Inorganic waste`, `NonEnergyUse`, `Oil` (8) | Grouping of `Input_commodity`. |
| `Generate_emissions` | **logical** | no | `TRUE` / `FALSE` | Whether burning this input produces emissions. |
| `2021_TWh` … `2051_TWh` | numeric | no (0-filled) | `0.00300882` | Fuel consumed in that year, **TWh**. |
| `2021_ktCO2e` … `2051_ktCO2e` | numeric | no (0-filled) | `0.920698` | Emissions from that fuel, **kt CO₂e**. |

`Energy` is the sheet to use for **fuel-switching and fuel-volume** analysis; `Emissions` is the one for **GHG accounting**. Its `ktCO2e` columns are *not* a re-keying of `Emissions` — they are gross combustion emissions of the fuel, before biogenic-carbon exclusion and CCS capture, and they carry no process emissions. See gotcha 14 in §7 before using them for any reported emissions figure.

### 4.6 `Infrastructure` — 15 fields

**Grain:** one row per `site_ID` × `variable_type` for site-connected infrastructure; plus one row per cluster→storage pair for `CO2_transported`.
**Units:** per the `unit` column.

| Field | Type | Nullable | Domain / example | Meaning |
|---|---|---|---|---|
| `site_ID` | numeric | yes | `43` | `NA` on the 5 `CO2_transported` rows. |
| `site_traded_status` | character | yes | `Traded` | |
| `cluster` | character | yes | `Teesside` | `NA` on `CO2_transported` rows (see `terminal` instead). |
| `variable_type` | character | no | `CO2_pipe_new_capacity`, `CO2_pipe_available_capacity`, `CO2_truck_used_capacity`, `CO2_transported`, `H2_pipe_new_capacity`, `H2_pipe_available_capacity`, `H2_truck_used_capacity` (7) | What the row measures. |
| `unit` | character | no | `kt_a`, `PJ_a`, `kt` | Deterministic from `variable_type`: CO₂ capacities → `kt_a`; H₂ capacities → `PJ_a`; `CO2_transported` → `kt`. |
| `terminal` | character | yes | `Teesside`, `Humberside`, `Merseyside`, `Peterhead`, `Southampton` | Populated only on `CO2_transported` rows — the **cluster end** of the transport link. |
| `storage_site` | character | yes | `Southern North Sea`, `East Irish Sea`, `Northern and Central North Sea`, `Southampton Sea` | Populated only on `CO2_transported` rows. |
| `pipe_cluster_end` | character *(reads as **logical** when empty)* | yes | `NA` throughout this run | Destination cluster for cluster-to-cluster H₂ pipes. Only populated when `model_parameters$model_H2_production` is on. **Typing hazard** — see §7. |
| `2021` … `2051` | numeric | **yes** | `22.591169`, `NA` | Capacity/flow in that year. This is the only data sheet where year cells are genuinely `NA` (647 of 3,167 rows in 2021), meaning *variable not present in that period* — distinct from a solved `0`. |

---

## 5. Worked example — one site, all six tables

**Site 43: `BOC Ltd`, Chemicals, Teesside cluster, Traded, `<25km` from the cluster centre.**

For *why* one site's pathway diverges from another in the same sector, see [10_site_level_pathways.md](10_site_level_pathways.md); this section is about the shape of the numbers rather than the modelling logic behind them.

### `Sites_info` — 1 row

| site_ID | site_traded_status | cluster | site_name | Latitude | Longitude | region | PlantID |
|---|---|---|---|---|---|---|---|
| 43 | Traded | Teesside | BOC Ltd | 54.60403 | -1.213661 | North East (England) | 13763 |

### `Outputs` — 53 rows (selection, PJ unless noted)

| Primary_output | Technology_code | Technology_category | Unit | 2021 | 2026 | 2031 | 2036 | 2041 | 2046 | 2051 |
|---|---|---|---|---|---|---|---|---|---|---|
| ICHHTH | ICHHTHELC01 | Electricity | PJ | 0.001143 | 0 | 0 | 0 | 0 | 0 | 0.001010 |
| ICHHTH | ICHHTHNGA01 | Natural gas | PJ | 0 | 0.001120 | 0.0000223 | 0 | 0 | 0 | 0 |
| ICHHTH | ICHHTHHDG01 | Hydrogen | PJ | 0 | 0 | 0.001076 | 0.001076 | 0.001053 | 0.001032 | 0 |
| ICHMOT | ICHMOTELC01 | Electricity | PJ | 0.154063 | 0.150997 | 0.147962 | 0.144958 | 0.141984 | 0.139042 | 0.136130 |
| IHVC | ICHHVCSCE01 | Natural gas | Mt | 0.016951 | 0.016613 | 0.000658 | 0.000327 | 0 | 0 | 0 |
| IHVC | ICHHVCSCQB01 | CCS | Mt | 0 | 0 | 0.015622 | 0.015622 | 0.015622 | 0.015298 | 0.014978 |
| ICHSTM | ICHCHPBIOS01 | Biomass | PJ | 0.034000 | 0.085274 | 0.036135 | 0.066241 | 0.053961 | 0 | 0 |

The story reads straight off the rows: high-value chemicals production switches from the unabated steam cracker (`ICHHVCSCE01`) to the CCS steam cracker (`ICHHVCSCQB01`) between 2026 and 2031, and high-temperature heat moves electricity → natural gas → hydrogen → back to electricity by 2051.

### `Infrastructure` — 5 rows

| variable_type | unit | 2021 | 2026 | 2031 | 2036 | 2041 | 2046 | 2051 |
|---|---|---|---|---|---|---|---|---|
| CO2_pipe_new_capacity | kt_a | NA | NA | 22.591169 | 0 | 0 | 0 | 0 |
| CO2_pipe_available_capacity | kt_a | NA | NA | 22.591169 | 22.591169 | 22.591169 | 22.591169 | 22.591169 |
| H2_pipe_new_capacity | PJ_a | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H2_pipe_available_capacity | PJ_a | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| H2_truck_used_capacity | PJ_a | 0 | 0 | 0.001793 | 0.001793 | 0.001756 | 0.001719 | 0 |

Consistent with the technology picture: a CO₂ pipe connection is **built in 2031** (new capacity spikes once, available capacity persists) to serve the CCS cracker, and the hydrogen boiler is supplied by **trucking**, not pipeline.

### `Emissions` — 56 rows (selection, kt CO₂e)

| Emissions_category | Technology_code | CO2_NonCO2 | Emission_type | 2021 | 2026 | 2031 | 2036 | 2041 | 2046 | 2051 |
|---|---|---|---|---|---|---|---|---|---|---|
| Direct_and_Indirect | ICHMOTELC01 | CO2 | Energy | 15.752840 | 13.123455 | 10.590320 | 8.152016 | 5.807127 | 3.554235 | 1.391921 |
| Direct_and_Indirect | ICHHVCSCE01 | CO2 | Energy | 12.014108 | 11.774329 | 0.466092 | 0.231831 | 0 | 0 | 0 |
| Direct_and_Indirect | ICHHVCSCE01 | CO2 | Process | 6.714172 | 6.580560 | 0.260510 | 0.129584 | 0 | 0 | 0 |
| Direct_and_Indirect | ICHHVCSCE01 | NonCO2 | Energy | 1.334374 | 1.307819 | 0.051774 | 0.025753 | 0 | 0 | 0 |
| Direct_and_Indirect | ICHHTHNGA01 | CO2 | Energy | 0 | 0.086041 | 0.001712 | 0 | 0 | 0 | 0 |
| Direct_and_Indirect | ICHHTHNGA01 | NonCO2 | Energy | 0 | 0.009560 | 0.000190 | 0 | 0 | 0 | 0 |
| Captured | ICHHVCSCQB01 | CO2 | Energy | 0 | 0 | 7.485810 | 7.485810 | 7.485810 | 7.330668 | 7.177150 |
| Captured | ICHHVCSCQB01 | CO2 | Process | 0 | 0 | 7.776932 | 7.776932 | 7.776932 | 7.615756 | 7.456269 |
| Negative | ICHHVCSCQB01 | NA | NA | 0 | 0 | -4.708393 | -4.708393 | -4.708393 | -4.610812 | -4.514253 |

From 2031 the CCS cracker captures ~15.3 kt/yr and, because it burns biomass, delivers ~4.7 kt/yr of **negative** emissions. Note that one technology occupies **several rows per category** — `ICHHVCSCE01` needs three `Direct_and_Indirect` rows to cover the CO₂/NonCO₂ × Energy/Process splits. This is why aggregation must group on the full split key, not on `Technology_code` alone.

### `Energy` — 89 rows (selection)

| Technology_code | Input_commodity | Fuel_category | Gen. emis. | 2021_TWh | 2026_TWh | 2031_TWh | 2021_ktCO2e | 2026_ktCO2e | 2031_ktCO2e |
|---|---|---|---|---|---|---|---|---|---|
| ICHHTHELC01 | INDDISTELC | Electricity | TRUE | 0.00037356 | 0 | 0 | 0.1344803 | 0 | 0 |
| ICHHTHNGA01 | IND_NGABOM | Gas | TRUE | 0 | 0.00051867 | 0.00001032 | 0 | 0.0956014 | 0.0019021 |
| ICHMOTELC01 | INDDISTELC | Electricity | TRUE | 0.04375789 | 0.04288711 | 0.04202508 | 15.7528403 | 13.1234550 | 10.5903195 |

These `ktCO2e` figures are attributed to the **fuel** rather than the pollutant, and are already summed over the gas splits. For the fossil technologies shown here the arithmetic ties out against `Emissions`: `ICHHTHNGA01` in 2026 has an Energy figure of `0.0956014`, which is exactly the CO₂ row (`0.086041`) plus the NonCO₂ row (`0.009560`); `ICHMOTELC01` has only a CO₂ row, so it matches one-to-one.

**This tie-out is a property of fossil, non-process technologies only** — it breaks for biomass and for process emitters. Site 43's own biomass CHP (`ICHCHPBIOS01`) and its CCS cracker are among the mismatching cases. Read gotcha 14 in §7 before generalising from this table.

### `Costs` — 272 rows, 65 non-zero (selection, £m per year, 2021 prices)

| Sector_infrastructure | Technology_code | Cost_type | 2021 | 2026 | 2031 | 2036 | 2041 | 2046 | 2051 |
|---|---|---|---|---|---|---|---|---|---|
| Chemicals | ICHAMMSRS01 | Opex | 0.101554 | 0.081244 | 0.060933 | 0.040622 | 0.020311 | 0 | 0 |
| Chemicals | ICHHTHNGA01 | Capex | 0 | 0.000560 | 0.000560 | 0.000560 | 0.000560 | 0.000560 | 0.000560 |
| Chemicals | ICHHTHNGA01 | Capex_lump | 0 | 0.010292 | 0 | 0 | 0 | 0 | 0 |
| Chemicals | ICHHTHNGA01 | Carbon cost | 0 | 0.026503 | 0.000569 | 0 | 0 | 0 | 0 |
| Chemicals | ICHHTHNGA01 | Fuel cost | 0 | 0.018849 | 0.000261 | 0 | 0 | 0 | 0 |
| Chemicals | ICHHTHNGA01 | Opex | 0 | 0.000129 | 0.000129 | 0.000129 | 0.000129 | 0.000129 | 0.000129 |
| CO2_pipe_new_capacity | NA | Capex | 0 | 0 | 0.011142 | 0.011142 | 0.011142 | 0.011142 | 0.011142 |
| CO2_pipe_new_capacity | NA | Capex_lump | 0 | 0 | 0.204929 | 0 | 0 | 0 | 0 |
| CO2_pipe_available_capacity | NA | Opex | 0 | 0 | 0.001025 | 0.001025 | 0.001025 | 0.001025 | 0.001025 |

The natural-gas heat technology `ICHHTHNGA01` shows the complete five-cost-type picture for one technology: a £0.0103m investment in 2026 (`Capex_lump`), the same money as a £0.00056m/yr annuity (`Capex`), plus opex, fuel and carbon costs. Note that its **carbon and fuel costs collapse to zero after 2031**, which is exactly when `Outputs` shows the switch to the hydrogen boiler.

---

## 6. Cluster-level variant

With `output_cluster_level = TRUE`, five extra sheets appear. They are the same tables aggregated up, with two schema differences applied in `combine_tables()`:

- **`site_ID`, `site_traded_status` and `site_name` are gone.** The grain key becomes `cluster`.
- **`region_of_cluster_centre`** (character) is inserted immediately after `cluster` — the region of the *cluster centre*, not of any site. It is a deliberate rename of the joined `region` field to avoid confusion with `Sites_info$region`.

Everything else — field names, types, domains, year columns, units — is unchanged. There is **no** `Sites_info_cluster`.

---

## 7. Gotchas for anyone consuming these outputs

1. **`Definitions` has drifted from the actual columns.** The sheet is hand-maintained and describes the cluster-level naming, so a consumer that trusts it will break. Confirmed mismatches in this run:

   | `Definitions` says | Workbook actually has |
   |---|---|
   | `Emissions.Emissions_total` | `Emissions.Emissions_category` |
   | `Costs.cost_traded_status` | `Costs.Traded_NonTraded` (and it's a boolean) |
   | `Costs.Unit` | *no such column* — `Costs` has `Sector_group` instead |
   | `region_of_cluster_centre` on every sheet | cluster-level sheets only |
   | a `Sites` sheet (`Sector`, `cluster_rad`, `traded_site`, `Site_count`) | *never written* — `create_sites_tables()` output is dropped by `combine_tables()` |
   | `Emissions` categories `Direct`, `Direct and Indirect` | `Direct (total CO2e)`, `Direct (split by ghg type)`, `Direct_and_Indirect` |

   Treat the workbook itself as the schema of record; `Definitions` is documentation, not a contract.

2. **Year columns are parameter-dependent.** Discover them; don't hard-code them.

3. **Two traded-status fields with different types.** `site_traded_status` is character with three levels (`Traded` / `Non-traded` / `Non-traded-non-point`); `Traded_NonTraded` is a two-valued logical. They encode the same fact at different resolution.

4. **`pipe_cluster_end` type is data-dependent.** It is semantically a cluster name, but when H₂ production is off the whole column is empty and every Excel reader types it as logical/`NA`. Force it to character on read, or a run *with* H₂ production will change your column type underneath you.

5. **`NA` in `Infrastructure` year cells means "variable absent", not zero.** Every other data sheet is zero-filled (`replace_na(.x, 0)` in the builders), so `NA` there is meaningful. Don't blanket-`fillna(0)`.

6. **`Capacity` is always `used_capacity`.** Build decisions are not exported to `Outputs`; recover them from `Costs.Capex_lump` or from `Infrastructure.*_new_capacity`.

7. **`Outputs.Unit` varies within the sheet** (`PJ` / `Mt` / `kt`). Group by `Unit` before any aggregation.

8. **`Emissions` overlaps by construction.** Always filter `Emissions_category` first (§4.4).

9. **`Capex` vs `Capex_lump` are alternative views of the same spend.** Never add them.

10. **`CO2_C2S` cost rows lose their cluster attribution.** `calculate_costs_CO2_cluster2storage()` groups by `cluster` × `storage_site`, but the `select()` in `create_cost_tables()` keeps only `site_ID` — so the 18 `CO2_C2S` rows arrive with `site_ID`, `cluster` and `Cost_type` all `NA` and only `Storage_site` set. Multiple clusters feeding the same storage site therefore appear as indistinguishable rows. To attribute cluster→storage costs, use the `Infrastructure` sheet's `CO2_transported` rows (which *do* keep `terminal`) or read the cluster-level `Costs_cluster` tab.

11. **Costs are per-year, un-discounted, 2021-rebased.** The builders divide out the present-value factor (`undiscounted_yearly_cost()`) and then apply GDP deflators (`base_year_adjustment()`). Do **not** re-inflate or re-discount them. The `Info` sheet's wording ("including inflation, after discounting 3.5%") is misleading — see [09_objective_function.md](09_objective_function.md).

12. **Zero rows dominate.** 65 of 272 `Costs` rows are non-zero for site 43. Filtering all-zero rows shrinks the data ~4× at no information cost.

13. **Read the `Log` sheet.** It is the only place solver warnings surface. The workbook's own `Info` sheet calls reviewing it a required QA step.

14. **`Energy` and `Emissions` are *not* two views of the same numbers — despite what `Info` says.** The `Info` sheet states that `Energy` "contains the same information as the Emissions sheet but with the type of pollutant included". Measured on the reference run, it does not:

    | Year | `Energy` Σ ktCO₂e | `Emissions` Σ `Direct (total CO2e)` | `Captured` | `Negative` |
    |---|---|---|---|---|
    | 2021 | 12,981 | 5,163 | 0 | 0 |
    | 2031 | 13,426 | 972 | 1,500 | −241 |
    | 2051 | 6,745 | 546 | 1,798 | −234 |

    At technology grain the mismatch is concentrated on **biomass** technologies (codes ending `BIOS01` — `ICRHTHBIOS01`, `IFDCHPBIOS01`, `ICHCHPBIOS01`, …) and on **process-emitting** technologies such as the cement dry kiln `ICMKLND01`. The reading consistent with the data: `Energy.<year>_ktCO2e` is the **gross combustion emissions of the fuel burnt**, before biogenic-carbon exclusion and before CCS capture; `Emissions` applies the full GHG-accounting treatment (biogenic carbon excluded from `Direct`, capture moved to `Captured`, removals to `Negative`) and additionally covers process emissions that no fuel row can carry. 12,389 site × technology × year keys have non-zero `Energy` emissions with no corresponding `Direct_and_Indirect` row at all.

    **Use `Emissions` for any GHG accounting or reporting figure. Use `Energy` for fuel-switching and fuel-volume analysis only.** Do not cross-check one against the other, and do not substitute one for the other.

---

## 8. A tidy target schema for headless consumption

For the integration work in [07](07_high_level_testing_strategy.md) / [08](08_python_redesign_approach.md), the wide-year Excel layout is the wrong interchange format. A single long table keyed consistently is far easier to validate, diff and join:

| Column | Type | Notes |
|---|---|---|
| `run_id` | string | from the archive name / `Title` sheet |
| `package_version` | string | from `Title` |
| `scope` | enum | `site` \| `cluster` |
| `site_id` | int, nullable | null for cluster-scope and non-site-attributable rows |
| `cluster` | string, nullable | |
| `region` | string, nullable | |
| `sector` | string, nullable | |
| `technology_code` | string, nullable | null for infrastructure rows |
| `commodity` | string, nullable | `Primary_output` or `Input_commodity` depending on `measure` |
| `measure` | enum | `used_capacity` \| `cost` \| `emissions` \| `fuel` \| `infrastructure` |
| `submeasure` | string, nullable | `Cost_type`, `Emissions_category`, or `variable_type` |
| `year` | int | from the un-pivoted year column |
| `value` | float, nullable | null preserved for `infrastructure` |
| `unit` | enum | `£m` \| `kt` \| `ktCO2e` \| `PJ` \| `Mt` \| `TWh` \| `kt_a` \| `PJ_a` |

Key properties this buys you: the timestep no longer changes the schema, units travel with every value, the `NA`-vs-`0` distinction survives, and the double-count traps become explicit filters on `submeasure` rather than tribal knowledge.

### Post-solve invariants

Candidates for the property tests in note 07. The four below were **checked against the reference run** and hold:

| Invariant | Result on the reference run |
|---|---|
| `Emissions`: `Direct (split by ghg type)` summed over `ghg_type` equals `Direct (total CO2e)`, per `site_ID` × `Technology_code` × `Emission_type` × year | Holds. 16,562 keys compared, zero unmatched, max abs difference 5.7 × 10⁻¹³ (floating point). |
| `Infrastructure`: `*_available_capacity` in year *t* equals the cumulative sum of `*_new_capacity` up to *t* | Holds **exactly** (max abs difference 0) for both `CO2_pipe` (1,029 site-years) and `H2_pipe` (6,419 site-years). No retirement occurs within the horizon. |
| `Energy`: `Generate_emissions == FALSE` implies every `<year>_ktCO2e` is zero | Holds. All 46,928 such cells are exactly 0. |
| Non-negativity of physical quantities: `Outputs`, `Energy.<year>_TWh`, `Infrastructure` | Holds — minimum value 0 across all three. |

Two invariants that look obvious but are **false** — do not assert them:

- **"Values are non-negative except `Emissions_category == 'Negative'`."** `Costs` contains 1,097 negative cells (minimum −6.78 £m): `Fuel cost` on `Standard_FF` / `Natural gas` rows (by-product and self-generation credits) and `Carbon cost` on `CCS` rows (the carbon-price credit for negative emissions). `Emissions` also goes negative outside the `Negative` category — 832 cells, all on `Standard_FF` rows, minimum −0.18 kt. Both follow from the retrofit-differencing described in [09_objective_function.md](09_objective_function.md): a technology is charged its own costs *minus* those of the technology it displaces, which can net out below zero.
- **"`Energy` and `Emissions` are the same numbers."** They are not — see gotcha 14 below.

One invariant that is **not checkable from the workbook alone**: `sum(Capex_lump) ≈ NPV(Capex stream)`. The `Capex` annuity is an *annual* payment stream, but the year columns sample it only every `timestep` years, so the full stream is unobservable at 5-year resolution. Verifying the annuitisation requires the in-memory cost table (`create_cost_tables()` output before `pivot_wider`), not the exported workbook.
