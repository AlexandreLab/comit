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

## Step 1 — Sector fuel mix from national statistics (ECUK / DUKES)
ECUK provides fuel consumption split by fuel type (**coal, gas, oil, electricity**)
for generic industrial processes in each sector. This national split defines the
sector's fuels and technology set, and is the calibration target for modelled fuel
use in the start year.

Mapping to the "gas / electricity / non-metered" framing:
- **Gas** → natural gas (`NGA`), grid-metered.
- **Electricity** → `ELC`, grid-metered.
- **Non-metered fuels** → everything else not delivered via gas/electricity grids:
  coal, oil, LPG, biomass, coke-oven gas, etc. (the residual solid/liquid/other
  fuels in the ECUK breakdown).

(The literal three-way "metered gas / metered electricity / non-metered" split is
the DESNZ **subnational energy** convention; COMIT's equivalent is the ECUK/DUKES
fuel categories.)

### Is the sector energy "coming from ECUK"?
Yes, but **indirectly** — ECUK/DUKES is a *calibration source*, not a live input.
There is no ECUK sheet in the workbook. The model computes sector base-year energy
from the input template (`Technologies` × `technology_input_output`); those template
values were **tuned during data prep so modelled start-year fuel use matches ECUK/
DUKES**:

```
ECUK/DUKES ──(set existing_capacity_2020 & fuel profiles to match)──► input template ──► model
```

Qualifications:
- ECUK is strongest for **energy-based sectors** (it defines their generic processes
  and fuel split). For **process-based sectors** (cement, lime, iron & steel) the
  processes come from real production-process data; ECUK/DUKES is more a cross-check.
- ECUK sets the fuel **mix/intensity**, not the demand **quantity** — how much each
  sector must produce comes from `Demand_drivers` (per `Contents`, sourced from EEP
  2019). ECUK = *how* demand is met; `Demand_drivers` = *how much*.
- In the **public file** these are dummy figures, so they will not actually match ECUK.

## Step 2 — Technology "fuel-use profiles"
`technology_input_output` specifies, for each technology, the input commodities
(fuels) **per unit of output** — its fuel-use profile. Example: paper-sector gas
boiler `IPPBOINGA01` uses **1.11 PJ gas per PJ** of low-temperature heat. Since a
technology is effectively "a fuel + a process", the technology mix present *is* the
fuel mix.

Fuel type is encoded in the technology code (3-3-3 pattern: sector–process–fuel):
`IOIDRYELC01` = Other-industries drying by **ELC**; `IOIDRYNGA01` = same by **NGA**.

## Step 3 — Baseline capacities calibrated to the statistics
Actual installed capacity by technology in 2021 is unknown, so
`existing_capacity_2021` is **estimated so modelled start-year fuel use aligns with
ECUK/DUKES**, assuming *just enough capacity to meet demand, no spare*.

```
start-year fuel use = fuel-use profile × availability_factor × existing_capacity
implied output      = existing_capacity_2021 × capacity_to_activity_factor × availability_factor
```

This gives, per sector, the gas / electricity / non-metered fuel consumed to meet
that sector's demand.

## Step 4 — Apportion sector total to each site by NAEI emissions share
Sector-level starting capacities (hence fuel use) are **apportioned to individual
sites in proportion to each site's share of that sector's NAEI emissions** (same
mechanism as site demand):

```
site current gas use         ≈ (site_emissions / sector_total_emissions) × sector gas use
site current electricity use ≈ (site_emissions / sector_total_emissions) × sector electricity use
site current non-metered use ≈ (site_emissions / sector_total_emissions) × sector non-metered use
```

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

> Refinement not shown here: the model apportions using a **traded-share**-adjusted
> emissions share (`sector_share_by_traded`, see [02_site_data.md](02_site_data.md))
> rather than the raw emissions share used above, and small sub-cut-off sites are
> aggregated (`_psg`). The high-level logic is identical.

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
