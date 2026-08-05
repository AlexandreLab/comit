# COMIT Sector Coverage and Mapping to the CaRB3 Classification

Which sectors COMIT currently models, where they come from in the data, and
how they line up with the **CaRB3** activity classification used by DESNZ's
Non-Domestic Building Stock (NDBS) model for England and Wales (DESNZ research
paper 2024/005, *Non-Domestic Building Stock — Part 1: Stock Description*,
March 2023). The mapping identifies which industrial activity types COMIT
covers, which it absorbs into catch-alls, and which it does not represent —
useful when planning new sector archetypes (see the site-heterogeneity PRD,
`docs/specs/2026-08-05-site-heterogeneity-prd.md`).

## 1. Sectors currently covered by COMIT

The model's sector list is defined by the `sector` column of the
`Technologies` workbook sheet and mirrored (hard-coded) in the Shiny UI
(`R/app_ui.R:16-36`). **16 industrial sectors:**

Cement, Ceramics, Chemicals, Construction, Electrical engineering,
Food & drink, Glass, Iron & steel, Lime, Mechanical engineering,
Non-ferrous metals, Other, Paper, Refineries, Textiles, Vehicles.

Alongside these:

- **Hydrogen** — a 17th entry in `Technologies`, but a pseudo-sector for H₂
  supply (special-cased in `get_site_demand`), not an industrial sector with
  real sites.
- **CO2 Infrastructure** / **H2 Infrastructure** — UI-only display categories
  for transport & storage results; no baseline sites.

### NAEI source sectors → COMIT sectors

Site data arrives with 18 NAEI sector labels, folded to the 16 model sectors
via `new_sector_mapping`. Non-trivial folds:

| NAEI source sector | COMIT sector |
|---|---|
| Chemical industry | Chemicals |
| Food, drink & tobacco industry | Food & drink |
| Iron & steel industries | Iron & steel |
| Non-ferrous metal industries | Non-ferrous metals |
| Paper, printing & publishing industries | Paper |
| Processing & distribution of petroleum products | Refineries |
| Textiles, clothing, leather & footwear | Textiles |
| Other industries | Other |
| **Waste collection, treatment & disposal** (107 sites) | **Other** |
| **Water & sewerage** | **Other** |

So **"Other" is a heterogeneous catch-all** (Other industries + waste +
water), which is where the model's homogeneous-sites assumption (note 06/10)
is most strained.

## 2. CaRB3 in one paragraph

CaRB3 (Carbon Reduction in Buildings v3) classifies every non-domestic
premises in England & Wales into **19 classes** subdivided into ~400
**activities**, derived from VOA rating data. The class most relevant to COMIT
is **Factory** (61 activities, 276k premises, 167M m² — 28% of all
non-domestic floorspace), with industrial-adjacent activities also in
**Utilities**, **Warehouse**, and **Transport**. CaRB3 classifies *buildings
by activity*; COMIT models *point-source industrial sites by sector* — so the
mapping below is many-to-many and approximate, but it shows coverage.

## 3. COMIT sector ↔ CaRB3 activity mapping

CaRB3 codes are from Table 28 of the NDBS report (Annex 1).

| COMIT sector | Matching CaRB3 activities (Factory class unless noted) | Match quality |
|---|---|---|
| Cement | FA45 Cement Works; FA49 Cement Tile Works | Direct |
| Ceramics | FA31 Pottery; FA24 Brickworks / clay tile/pipe works | Direct |
| Chemicals | FA15 Chemical Works; FA58 Artificial Fibre Works | Direct |
| Construction | FA06 Concrete batching plant; FA19 Concrete Product Works; FA25 Concrete Block Works; FA21 Asphalt Plant; FA12 Aggregate/Mineral Processing | Direct (materials supply chain) |
| Electrical engineering | FA53 Wafer Fabrication; otherwise inside FA01/FA02 generics | **Weak** — mostly generic |
| Food & drink | FA13 Food Processing Centre; FA14 Brewery; FA16 Abattoir; FA23 Provender Mill; FA28 Flour Mill; FA35 Creamery; FA47/FA54 Maltings; FA50 Distillery; FA56 Beet Sugar Factory | Direct, rich detail |
| Glass | *(no glass-manufacture activity code)* — inside FA02 Factory / FA99 NEC | **Weak** — no distinctive code |
| Iron & steel | FA27 Iron and/or Steel Works; FA59 Coking & Carbonising Plant; FA30 Foundry (shared) | Direct |
| Lime | *(no lime-kiln code)* — nearest FA20 Industrial Minerals NEC | **Weak** |
| Mechanical engineering | FA01 Workshop / FA02 Factory generics only | **Weak** — generic |
| Non-ferrous metals | FA48 Aluminium Smelting Works; FA30 Foundry (shared) | Partial |
| Other | FA99 Industrial NEC; FA55 Large industrial NEC; FA22 Works | Catch-all ↔ catch-all |
| Paper | FA34 Paper Mill; FA33 Newspaper print works | Direct |
| Refineries | FA42 Oil refinery / gas processing; FA36 Mineral Production – Oil | Direct |
| Textiles | FA52 Tannery (leather); otherwise generic FA01/FA02 | Partial |
| Vehicles | FA40 Motor Vehicle Works; FA39 Aircraft works; FA11 Shipbuilding/boatyard; (FA03 vehicle repair is servicing, arguably out of scope) | Direct |

**Key data limitation:** the two generic activities — FA01 Workshop (62M m²)
and FA02 Factory (87M m²) — dominate Factory floorspace and cannot be
assigned to a COMIT sector from CaRB3 alone; sector attribution needs the
NAEI/SIC route COMIT already uses.

## 4. Industrial activities in CaRB3 with no COMIT sector (gaps)

Activities that are industrial (or industrial-adjacent, energy-intensive)
in CaRB3 but have **no dedicated COMIT sector** today:

| CaRB3 activity/class | Current COMIT treatment | Candidate new sector? |
|---|---|---|
| Waste handling: UT03 Refuse handling/disposal (Utilities); FA07 Scrap Metal/Breakers Yard; FA17 Mineral Production – Putrescible | Folded into **Other** via NAEI waste sector | **Yes — Waste & recycling** (107 NAEI sites already in the data) |
| Water & sewerage: UT01 Sewage works (5,374 premises) | Folded into **Other** | **Yes — Water & sewerage** |
| Mining/quarrying/extraction: FA08, FA18, FA36, FA37, FA44, FA46, FA51, FA57 (Mineral Production family); FA38 Minewater Treatment | Not represented (COMIT models manufacturing point sources) | Possible — Extraction, if in scope |
| Cold-chain storage: WA07 Cold store, CHL/CLD accommodation uses (Warehouse) | Out of scope (buildings, not industrial point sources) | Only if scope widens to logistics energy |
| Data centres: OF11 Computer centre (1.43M m², Office class) | Out of scope | Only if scope widens beyond industry |
| Laboratories: FA09 Laboratory (1.14M m²) | Not represented | Unlikely (dispersed, building-like loads) |
| Post/parcel sorting: FA10 (0.86M m²) | Not represented | Unlikely |

And the reverse gap: COMIT sectors **Glass, Lime, Mechanical engineering,
Electrical engineering, and (largely) Textiles** have no distinctive CaRB3
activity — their sites hide in the FA01/FA02 generics. CaRB3/VOA data can
therefore *not* serve as an independent site register for those sectors,
whereas for Cement, Food & drink, Paper, Refineries, Iron & steel it can
cross-check NAEI site lists and provide floorspace/building attributes
(age, heating system, off-gas status, retrofit complexity) per site.

## 5. Implementation challenges for the missing sectors

The gaps in §4 are not equally easy to close. Five structural obstacles,
mapped to the model mechanics they collide with:

### 5.1 The emissions-share engine assumes CO₂-emitting point sources

All site sizing hangs off `scaling_factor_within_sector = site CO₂ / sector
CO₂` (`R/fct_sites.R:113`, note 06). Two failure modes:

- **Electricity-dominated sites (data centres, cold stores)** have near-zero
  on-site combustion CO₂ and mostly do not appear in NAEI point-source data
  at all — there is nothing to scale on. They would need a different size
  proxy (metered electricity, floorspace, IT load), i.e. the PRD's F1
  direct-baseline mechanism made *mandatory* for the sector rather than
  optional enrichment.
- **Waste and sewage emissions are largely non-CO₂ and non-energy**
  (landfill CH₄, treatment N₂O/CH₄). Emissions share becomes a distorted
  proxy for energy demand, and the model's levers (fuel switching, CCS,
  electrification) cannot abate the dominant gases — gas capture and process
  change are not in the technology set, yet the carbon-cost terms would
  price those emissions.

### 5.2 Site count and dispersion vs MILP size

107 NAEI waste sites are manageable. **5,374 sewage works** are not: COMIT
builds decision variables per site × technology × year plus binary
minimum-plant-size variables, so full site resolution would blow up the
MILP. Representative/aggregated sites would be needed — which cuts against
the site-level-pathways goal. Dispersion also undermines the cluster and
H₂/CO₂ transport logic, which assumes proximity to a few industrial
clusters matters.

### 5.3 Producers vs consumers

Energy-from-waste plants export electricity/heat; sewage works run AD-CHP
that self-supplies and exports. COMIT is demand-driven (national demand ×
site share; technologies consume fuel to meet it) and has no net-export
shape — the Hydrogen pseudo-sector shows supply-side roles need
special-casing. Boundary risk: large EfW plants sit in the GHGI *energy
supply* sector, not industry, so including them risks double-counting with
the power sector.

### 5.4 No calibration anchor

Fleets are calibrated to ECUK industrial fuel data + GHGI totals (note 04).
ECUK classifies water/sewage and data centres under services, so the
`existing_capacity_2020` back-solve has no source. CaRB3/VOA helps less
than hoped — the fuel-used field is null for 50–65% of premises and
floorspace ≠ energy (NDBS Part 2 links meter data but is access-restricted).
New `Demand_drivers` commodities ("Ml treated", "t waste processed") with
credible forecasts would also be needed.

### 5.5 Mining/extraction has the wrong energy shape

Dominated by mobile plant / off-road diesel rather than stationary
combustion serving a process chain, so `technology_input_output` does not
fit; activity is resource-driven, not demand-driven.

### Practical ranking

| Candidate | Verdict |
|---|---|
| **Waste (NAEI's 107 sites, excl. EfW export)** | Tractable with the PRD's F6 mechanics alone — first candidate |
| **Water & sewerage** | Needs site aggregation + a non-emissions size proxy first |
| **Data centres / cold stores** | Structural work: mandatory F1 baselines, no NAEI anchor — beyond "new sector = data edit" |
| **EfW / export-heavy waste** | Needs net-export modelling + power-sector boundary decision |
| **Mining/extraction** | Poor fit for the model's technology representation |

## 6. Why this matters

1. **New-sector archetypes** — the waste and water activities folded into
   "Other" are the strongest candidates for promotion to their own sectors
   (data already in NAEI; distinctive process energy); the PRD's archetype
   feature (F2.3/F6) defines the mechanism.
2. **Baseline enrichment** — for sectors with direct CaRB3 matches, NDBS/VOA
   attributes (floorspace, fuel-used code, heating, off-gas distance,
   process/waste-heat flags) are a candidate external source for the per-site
   baselines of PRD features F1/F2.
3. **Scope boundary** — cold stores, data centres, and mining are outside
   COMIT's current industrial point-source scope; representing them is a
   scope decision, not just data work.
