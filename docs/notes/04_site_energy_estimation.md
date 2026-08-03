# Estimating a Point Source's Current Energy Consumption

How COMIT estimates the **start-year (current) energy consumption** of an
individual point-source site, split by fuel — gas, electricity, and non-metered
fuels.

Sources: `docs/COMIT Documentation and Technical Guide.pdf` (Baseline
technological capacities; Site level modelling), `technology_input_output` /
`Technologies` sheets, and `R/fct_create_energy_tables.R`.

## Key premise
NAEI gives COMIT only **CO₂ emissions** and a **sector** per site — never energy
directly. Current energy consumption is therefore **back-derived** top-down:
national fuel statistics → sector fuel use → apportioned to each site by its
emissions share. It is not measured per site.

## The five steps at a glance

```
Step 1  ECUK / DUKES (external gov.uk statistics)  →  which fuels each sector uses nationally
Step 2  `technology_input_output` sheet            →  fuel burned per unit of output, per technology
Step 3  `Technologies` sheet                       →  how much of each technology exists today
                                                      (Step 2 × Step 3, summed = sector fuel totals)
Step 4  `NAEI_df_clean_2023_revised` sheet         →  split the sector total between sites by
                                                      each site's share of sector CO₂ emissions
Step 5  `Emissions` + `traded_share` + `nps_sites` →  handle the sites NAEI does NOT list
                                                      (the "non-point" remainder of each sector)
```

## Before you start — where everything lives

All sheet references below are to the input workbook
`data_template_archive/comit_input_1_4_0_public_updated.xlsx`. One quirk to know:
**row 1 of each sheet is a text description, and the real column headers are further
down** — so if you open a sheet and see no headers, scroll a few rows:

| Sheet | Header row | Columns used in this note |
|---|---|---|
| `Technologies` | row 7 | `code`, `name`, `sector`, `existing_capacity_2020`, `capacity_to_activity_factor`, `availability_factor` |
| `technology_input_output` | row 7 | `technology_code`, `commodity`, `output` |
| `commodities` | row 2 | `commodity`, `description`, `commodity_category` |
| `NAEI_df_clean_2023_revised` | row 7 | `Site`, `Operator`, `IPM_sector`, `Emissions_tco2e` |
| `Emissions` | row 7 | `IPM_sector`, `Total_emissions` (whole-sector 2021 MtCO₂, GHGI scope) |
| `traded_share` | row 7 | `IPM_sector`, `traded_share`, `non_traded_point_share`, `non_point_share` |
| `nps_sites` | row 7 | `SIC`, one column per region (business counts) |

**ECUK and DUKES are not sheets in the workbook.** They are DESNZ national-statistics
publications on gov.uk (ECUK = Energy Consumption in the UK; DUKES = Digest of UK
Energy Statistics). They were used *offline, while the template was being built* —
see Step 1.

### How to read technology codes and fuel codes
The workbook uses two kinds of codes you'll meet throughout this note.

**Technology codes** (e.g. `IPPBOINGA01`) name a piece of equipment. The fuel it
runs on is not stored in a separate column — it is a **3-letter tag embedded in the
code itself**, following a sector–process–fuel–variant pattern:

```
IPPBOINGA01  =  IPP + BOI + NGA + 01
                 │      │     │     └─ variant number
                 │      │     └─ fuel: Natural GAs
                 │      └─ process: BOIler
                 └─ sector: Industry, Paper & Pulp
```

So `IOIDRYELC01` is "Other industries, DRYing, ELeCtricity, variant 01". You see
these codes in column `code` of `Technologies` and column `technology_code` of
`technology_input_output`.

**Fuel (commodity) codes** are the second kind — the codes the model actually
computes fuel quantities with. They live in the `commodities` sheet (headers on
row 2). The ones behind this note's three buckets:

| Commodity code (`commodity` col) | Description | `commodity_category` | Bucket |
|---|---|---|---|
| `IND_NGABOM` | Natural gas and biomethane | Gas | Gas |
| `INDDISTELC` | Electricity for industry (after distribution grid) | Electricity | Electricity |
| various | coal, oil, biomass commodities | Coal / Oil / Biomass and organic waste | Non-metered |

The `commodity_category` column is what lets you bucket any fuel row into
Gas / Electricity / Non-metered without memorising codes.

## Step 1 — Which fuels does each sector use nationally? (ECUK / DUKES — external)

**In plain words:** before looking at any individual site, the modellers needed to
know, e.g., "the UK paper industry as a whole runs mostly on gas and electricity;
the cement industry runs on coal". That picture comes from ECUK, which publishes
each industrial sector's fuel consumption split by fuel type (coal, gas, oil,
electricity, …), cross-checked against DUKES.

**Where to look:** nothing to open in the workbook — there is no ECUK sheet. ECUK
was a *calibration source used during data preparation*: the modellers chose which
technologies each sector contains and how much capacity each one gets (the numbers
you will meet in Steps 2 and 3) **so that the modelled start-year fuel use adds up
to the ECUK/DUKES national picture**:

```
ECUK/DUKES ──(tune existing_capacity_2020 & fuel profiles to match)──► input template ──► model
```

**Where you can see its footprint:** open `Technologies` (headers row 7), filter
`sector` = `Paper`, and the technology list itself *is* the ECUK fuel mix made
concrete — gas boilers (`…NGA…`), electric equipment (`…ELC…`), biomass boilers,
etc., each with a calibrated capacity.

Qualifications:
- ECUK is strongest for **energy-based sectors** (generic heat/steam/drying
  processes). For **process-based sectors** (cement, lime, iron & steel) the
  technologies come from real production-process data; ECUK/DUKES is a cross-check.
- ECUK sets the fuel **mix**, not the demand **quantity** — how much each sector
  must produce comes from the `Demand_drivers` sheet (sourced from EEP 2019).
  ECUK = *how* demand is met; `Demand_drivers` = *how much*.
- The **public file** contains dummy figures, so its numbers will not actually
  reproduce ECUK.

(The three-way "metered gas / metered electricity / non-metered" framing is the
DESNZ subnational-energy convention; COMIT's equivalent is the ECUK/DUKES fuel
categories bucketed via `commodity_category` as above.)

## Step 2 — How much fuel per unit of output? (`technology_input_output`)

**In plain words:** each technology is a recipe — "to make 1 unit of product, burn
X units of fuel". This sheet holds the recipes.

**Where to look:** sheet `technology_input_output`, headers on **row 7**. Each
technology occupies several rows, one per commodity it touches. Sign convention in
the `output` column: **negative = consumed (an input), positive = produced (an
output)**.

**Concrete example** (public file, rows 958–959): the Paper-sector gas boiler
`IPPBOINGA01`:

| `technology_code` | `commodity` | `output` | meaning |
|---|---|---:|---|
| `IPPBOINGA01` | `IND_NGABOM` | −1.075 | consumes 1.075 PJ of natural gas… |
| `IPPBOINGA01` | `IPPLTH` | +1.000 | …to produce 1 PJ of low-temperature heat |

i.e. ~1.08 PJ of gas in per PJ of heat out (a 93%-efficient boiler). To find which
bucket a fuel belongs to, look its `commodity` code up in the `commodities` sheet
and read `commodity_category`. Since each technology is essentially "one process +
one fuel", the mix of technologies present in a sector *is* the sector's fuel mix.

## Step 3 — How much of each technology exists today? (`Technologies`)

**In plain words:** a recipe tells you fuel *per unit*; now you need to know how
many units each sector actually produces with each technology. Nobody knows the
true installed capacity per technology, so it was **estimated so that modelled
start-year fuel use lines up with ECUK/DUKES** (Step 1), assuming just enough
capacity to meet demand, with no spare.

**Where to look:** sheet `Technologies`, headers on **row 7**. Three columns per
technology drive the calculation: `existing_capacity_2020` (calibrated start-year
capacity), `capacity_to_activity_factor` (capacity units → output units), and
`availability_factor` (fraction of the year it actually runs).

**The calculation**, continuing the `IPPBOINGA01` example (public-file values
`existing_capacity_2020` = 7.34, `capacity_to_activity_factor` = 1,
`availability_factor` = 0.98):

```
annual output  = existing_capacity_2020 × capacity_to_activity_factor × availability_factor
               = 7.34 × 1 × 0.98                      = 7.21 PJ of heat per year
annual gas use = annual output × fuel-per-unit (Step 2)
               = 7.21 × 1.075                          = 7.75 PJ of gas per year
```

Repeat this for **every** Paper technology with `existing_capacity_2020` > 0, bucket
each fuel via `commodity_category`, and sum: that yields the sector totals (for
Paper in the public file: gas 53.95 PJ, electricity 43.97 PJ, non-metered 32.36 PJ —
see the worked example below).

## Step 4 — Split the sector total between sites (`NAEI_df_clean_2023_revised`)

**In plain words:** the model now knows the whole sector's fuel use but nothing
about individual sites' fuel use — no site meters exist in the data. So it divides
the sector pie between sites **in proportion to each site's share of the sector's
CO₂ emissions**, which NAEI *does* report per site. A site producing 18% of the
sector's emissions is assumed to use 18% of each of the sector's fuels.

**Where to look:** sheet `NAEI_df_clean_2023_revised`, headers on **row 7**. Filter
the sector column (`IPM_sector`) to your sector; each row is one site with its
`Emissions_tco2e`.

**The calculation:**

```
site share                   = site Emissions_tco2e / Σ Emissions_tco2e over the sector
site current gas use         ≈ site share × sector gas use          (from Step 3)
site current electricity use ≈ site share × sector electricity use  (from Step 3)
site current non-metered use ≈ site share × sector non-metered use  (from Step 3)
```

Strictly, the NAEI share only divides up the **point-source part** of the sector —
Step 5 explains where the rest goes.

## Step 5 — Sites NAEI doesn't cover: the non-point remainder

**In plain words:** NAEI only lists large "point source" sites — for some sectors
just a handful. But the national statistics (ECUK energy, GHGI emissions) cover the
**whole** sector, including thousands of small businesses with no NAEI entry. If the
model divided the whole sector pie among just the NAEI sites, it would over-allocate
to them. So each sector's national total is first cut into slices by a **fixed,
per-sector assumption** — the ratio is *not* computed on the fly from NAEI coverage;
it is an input:

- `Emissions` sheet (headers row 7): `Total_emissions` — the whole sector's 2021
  emissions in MtCO₂ (GHGI scope, i.e. everyone).
- `traded_share` sheet (headers row 7): three fractions per sector that sum to 1 —
  `traded_share` (large sites in the ETS carbon market), `non_traded_point_share`
  (other NAEI point sources), and `non_point_share` (**everything NAEI does not
  list**). Per its own row-1 note, this split "comes from a combination of GHGI,
  NAEI and some manual imputation to solve discrepancies".

**The calculation** (`R/fct_process_sites.R`, `get_sector_emission_totals()` and
`get_non_point_sites_by_sector()`):

```
point-source slice = (traded_share + non_traded_point_share) × Total_emissions
non-point slice    = non_point_share × Total_emissions
```

The NAEI emissions from Step 4 are then only used **within the point-source slice**:
a site's `sector_share_by_traded` = its emissions ÷ Σ NAEI point-site emissions in
that sector/traded group. NAEI provides the *relative* sizes of the big sites; the
*absolute* total they share out is anchored to GHGI via the `traded_share` split.

The non-point slice is not dropped — it becomes **artificial aggregated sites**, one
per region × sector (named like `North West_Food & drink`, suffix `_npsg`). The
slice is spread across the 12 regions in proportion to the number of registered
businesses in that sector and region, taken from the `nps_sites` sheet (ONS business
counts by SIC code × region, headers row 7, mapped to COMIT sectors via
`ONS_sector_mapping` + `GHGI_sector_mapping`). Each artificial site then gets its
energy estimated by the same emissions-share method as real sites.

**Example values from the public file** (`traded_share` sheet):

| Sector | `traded_share` | `non_traded_point_share` | `non_point_share` | Meaning |
|---|---:|---:|---:|---|
| Cement | 1.0 | 0 | 0 | NAEI point sources cover the whole sector |
| Chemicals | 0.5 | 0 | 0.5 | half the sector's emissions come from sites not in NAEI |
| Food & drink | 0.4 | 0 | 0.6 | most of the sector is small non-NAEI sites |

So for a sector where NAEI lists only five or six sites, those sites share only the
point-source fraction of the sector's energy and emissions; the rest is carried by
the regional `_npsg` aggregates.

## Worked example — Paper sector, Kemsley Mill CHP

A concrete illustration using the public (artificial) figures. **Numbers are
illustrative only** — the public file has dummy values, and this is a simplified
reconstruction of the four steps above.

### Sheets and formulas used
- `Technologies`: `existing_capacity_2020`, `capacity_to_activity_factor`,
  `availability_factor` per technology.
- `technology_input_output`: fuel inputs per unit output (rows with **negative**
  `output` = fuel consumed).
- `commodities`: `commodity_category` used to bucket each fuel into
  Gas / Electricity / Non-metered.
- `NAEI_df_clean_2023_revised`: site emissions for the emissions-share apportionment.

Per base-year technology (with `existing_capacity_2020 > 0`):
```
activity(t)      = existing_capacity_2020 × capacity_to_activity_factor × availability_factor
fuel_use(t, c)   = |input_per_unit(t, c)| × activity(t)
```
Buckets: **Gas** = `Gas`; **Electricity** = `Electricity`; **Non-metered** =
`Coal` + `Oil` + `Biomass and organic waste` (+ `Hydrogen`, ~0 at base year).
Intermediate carriers (`Steam`, `Heat`) and non-energy categories are excluded to
avoid double-counting the fuel that produced them.

### Step A — Paper sector base-year energy use (summed over the fleet)
| Fuel bucket | PJ/yr | Share |
|---|---:|---:|
| Gas | 53.95 | 41.4% |
| Electricity | 43.97 | 33.8% |
| Non-metered | 32.36 | 24.8% |
| **Total** | **130.28** | |

Non-metered breaks down as: Biomass & organic waste 28.93, Coal 1.98, Oil 1.44 PJ.

### Step B — Site's emissions share
NAEI has **49 Paper point sources**, total **1,437,995 tCO₂e**. The largest is
**Kemsley Mill CHP** (E.ON UK CHP Ltd) at **253,528 tCO₂e**:
```
share = 253,528 / 1,437,995 = 0.1763  (17.63% of the sector)
```

### Step C — Apportion sector fuel use to the site
`site fuel = share × sector fuel`:

| Fuel bucket | Site energy (PJ/yr) |
|---|---:|
| Gas | 9.51 |
| Electricity | 7.75 |
| Non-metered | 5.71 |
| **Total** | **22.97** |

So Kemsley Mill CHP's estimated current energy consumption is ~23 PJ/yr, split
≈41% gas / 34% electricity / 25% non-metered — i.e. the **sector's** fuel mix,
scaled to the site's 17.6% emissions share.

Top 5 Paper sites by emissions share for reference: Kemsley Mill CHP 17.6%,
Partington Papermill 12.9%, Saddlebow Paper Mill 11.7%, Smurfit Kappa Townsend
5.3%, Nechells 4.7%.

> Refinement not shown here: the model apportions using the **traded-share**-adjusted
> emissions share (`sector_share_by_traded`, see Step 5 and
> [02_site_data.md](02_site_data.md)) rather than the raw emissions share used
> above, and small sub-cut-off sites are aggregated (`_psg`). The high-level logic
> is identical.

## Worked example 2 — Cement sector, Hope Cement Works (a process-based contrast)

Same method, a **process-based** sector (output is Mt of product, not PJ of heat).
Public/artificial figures — illustrative only.

### Step A — Cement sector base-year energy use
| Fuel bucket | PJ/yr | Share |
|---|---:|---:|
| Non-metered | 23.02 | 93.0% |
| Electricity | 1.31 | 5.3% |
| Gas | 0.43 | 1.7% |
| **Total** | **24.76** | |

Non-metered is almost entirely **Coal** (22.68 PJ) plus a little Oil (0.33 PJ) —
cement kilns are coal/solid-fuel fired, the opposite of Paper's gas/electricity mix.

### Step B — Site's emissions share
NAEI has **20 Cement point sources**, total **5,196,341 tCO₂e**. Largest is
**Hope Cement Works** (Hope Construction Materials Ltd) at **1,036,412 tCO₂e**:
```
share = 1,036,412 / 5,196,341 = 0.1995  (19.95% of the sector)
```

### Step C — Apportion to the site
| Fuel bucket | Site energy (PJ/yr) |
|---|---:|
| Non-metered | 4.59 |
| Electricity | 0.26 |
| Gas | 0.09 |
| **Total** | **4.94** |

Top 5 Cement sites by share: Hope Cement Works 19.95%, New Rugby 14.64%,
Tunstead Cement 10.96%, Ketton 9.90%, Cauldon Cement 9.30%.

### Paper vs Cement — what the contrast shows
| | Paper (energy-based) | Cement (process-based) |
|---|---|---|
| Output unit | PJ of useful heat/energy | Mt of product |
| Sector base-year energy | 130.28 PJ | 24.76 PJ |
| Dominant fuel | Gas (41%) + Electricity (34%) | Non-metered / **Coal** (93%) |
| Sector NAEI emissions | 1.44 MtCO₂e | 5.20 MtCO₂e |

Two takeaways:
1. **Fuel mix is sector-specific** and falls straight out of the technology fleet —
   Paper is gas/electricity heavy, Cement is coal-dominated.
2. **Cement has ~4× the emissions of Paper but ~1/5 the fuel energy.** This is the
   process-emissions effect: most cement CO₂ comes from **calcination of limestone**
   (a process emission), not fuel combustion. Combustion of the 24.76 PJ implies
   only ~2 MtCO₂; the rest of the 5.2 Mt is process CO₂. Because the apportionment
   key is *total* NAEI emissions (process + combustion), a cement site's emissions
   share is a good proxy for its size but **not** proportional to its fuel energy —
   worth remembering when interpreting apportioned energy for process-based sectors.

## Caveats
- **Homogeneous sites:** all sites in a sector run the same process/fuel mix,
  scaled only by emissions share and adjusted for location/infrastructure access.
  No genuinely site-specific fuel measurement exists.
- **Emissions ≠ energy:** electricity has zero *direct* on-site CO₂ but real energy
  use, so a site's electricity consumption is inferred from its sector's electricity
  intensity (ECUK) × emissions share — not by converting the site's own CO₂ to fuel.
- **Process- vs energy-based sectors:** process-based sectors (cement, lime, glass,
  parts of chemicals, iron & steel) model real production steps; energy-based
  sectors (food & drink, other industries, ceramics, textiles, etc.) model generic
  fuel-consuming processes calibrated to ECUK. The apportionment logic is the same;
  the underlying process detail differs.
