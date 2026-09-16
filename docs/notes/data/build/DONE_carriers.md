# DONE — lane `carriers`

Emission factors, biogenic fractions, scenario parameters and infrastructure availability
for the CaRB3 site energy system. Everything below is against spec §3.4 (`carrier`),
§3.7 (`infrastructure_scenario`), §3.8 (`scenario_parameters`) and §7 (emissions accounting)
of `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md`.

**Check:** `python3 docs/notes/data/build/check_carriers.py` — runs clean from any
directory. 8 blocking checks pass; 2 warnings, both recorded gaps (below).

---

## 1. Files written

| File | Rows | Owner |
|---|---:|---|
| `docs/notes/data/build/carrier_factors.csv` | 17 | this lane |
| `docs/notes/data/scenario_parameters.csv` | 155 | this lane |
| `docs/notes/data/infrastructure_scenario.csv` | 189 | this lane |
| `docs/notes/data/build/references_carriers.csv` | 10 | this lane |
| `docs/notes/data/build/check_carriers.py` | — | this lane |

Nothing else was touched. `carrier.csv`, `activity_process_register.csv`,
`activity_process_energy_profile.csv`, the options library, the specs, the READMEs and
`references.csv` are unchanged.

**Periods used: 2021, 2025, 2030, 2035, 2040, 2045, 2050.** 2021 is the base year the brief
names; 2025–2050 are the six periods both worked examples use, so their §6.3 tables line up
row for row with these files.

---

## 2. Coverage

### `carrier_factors.csv` — 17 rows, one per primary carrier in `carrier.csv`

| Column | Populated | Blank |
|---|---:|---|
| `carrier_id` | 17/17 | — |
| `emission_factor_source` | 17/17 | — |
| `biogenic_fraction` | 14/17 | `hydrogen`, `waste_derived_fuel`, `electricity` |
| `ef_gross_kt_per_pj` | 15/17 | `hydrogen`, `organic_waste` |
| `ef_year` | 15/17 | same two |
| `gcv_ncv_basis` | 15/17 | same two |
| `provenance` | 17/17 | — (the two blank rows carry a provenance saying *why* they are blank) |
| `confidence` | 15/17 | same two |

| Carrier | `ef_gross_kt_per_pj` | `biogenic_fraction` | Basis | Source |
|---|---:|---:|---|---|
| `natural_gas` | 51.12 | 0.0115 | gross CV | GHG CF 2026 |
| `biomethane` | 55.28 | 1 | net CV | GHG CF 2026 |
| `hydrogen` | *(blank)* | *(blank)* | — | — |
| `lpg` | 59.50 | 0 | gross CV | GHG CF 2026 |
| `light_fuel_oil` | 70.44 | 0 | gross CV | GHG CF 2026 |
| `heavy_fuel_oil` | 74.19 | 0 | gross CV | GHG CF 2026 |
| `petroleum_products_misc` | 68.25 | 0 | gross CV | GHG CF 2026 |
| `coal` | 89.39 | 0 | gross CV | GHG CF 2026 |
| `coking_coal` | 98.78 | 0 | gross CV | GHG CF 2026 |
| `coke` | 107.00 | 0 | net CV | UK ETS MRR Annex VI |
| `coke_oven_gas` | 44.40 | 0 | net CV | UK ETS MRR Annex VI |
| `blast_furnace_gas` | 260.00 | 0 | net CV | UK ETS MRR Annex VI |
| `solid_biomass` | 97.22 | 1 | net CV | GHG CF 2026 |
| `wood_pellets` | 97.22 | 1 | net CV | GHG CF 2026 |
| `organic_waste` | *(blank)* | 1 | — | — |
| `waste_derived_fuel` | 143.00 | *(blank)* | net CV | UK ETS MRR Annex VI |
| `electricity` | 58.02 | *(blank)* | n/a | Green Book Table 1, 2021 |

### `scenario_parameters.csv` — 155 rows, 20 series

| Series | Rows | Carriers | Periods |
|---|---:|---|---|
| `ef_<carrier>` × 14 combustion carriers | 98 | as listed above | all 7 (combustion constants, repeated) |
| `ef_electricity` | 7 | `electricity` | all 7 |
| `ef_electricity_lrmf` | 7 | `electricity` | all 7 |
| `import_price` | 29 | 5 at 2021, 4 at 2025–2050 | see §4.3 |
| `export_price` | 6 | `electricity` | 2025–2050 only |
| `carbon_price` | 7 | — | all 7 |
| `discount_rate` | 1 | — | none (a scalar) |

Every column is populated on every row except `carrier_id` on the 8 non-carrier rows
(`carbon_price`, `discount_rate`) and `period` on the single `discount_rate` row — both
optional in §3.8.

### `infrastructure_scenario.csv` — 189 rows

Complete grid: 9 GB clusters × 3 carriers × 7 periods, `scenario_id = published_2026`.

| Carrier | `available = TRUE` | `available = FALSE` |
|---|---:|---:|
| `co2_transport` | 20 | 43 |
| `hydrogen` | 0 | 63 |
| `grid_headroom` | 63 | 0 |

`capacity_limit` and `unit_tariff` are blank on all 189 rows — see §5.

---

## 3. Which cluster ids, and where the nine come from

§3.7 says `cluster_id` is "one of the 9 GB clusters" but never lists them. The nine are
COMIT's ten active clusters (`docs/notes/03_clusters_and_sectors.md`) minus Londonderry,
which D8 (Great Britain scope) excludes with the rest of Northern Ireland. Ids are
snake_case of COMIT's names, except that **`humber` and `mersey` keep the spellings the two
worked examples use** so their §6.2 tables keep resolving:

| `cluster_id` | COMIT `Cluster_location` |
|---|---|
| `teesside` | Teesside |
| `humber` | Humberside — spelled `humber` because the cement worked example §6.2 uses `humber` |
| `humber2` | Humberside2 |
| `southampton` | Southampton |
| `south_wales` | South Wales |
| `mersey` | Merseyside — spelled `mersey` because the food & drink worked example §6.2 uses `mersey` |
| `peterhead` | Peterhead |
| `grangemouth` | Grangemouth |
| `medway` | Medway |

§3.7 has no name column, so the mapping lives here rather than in the file.

---

## 4. Judgement calls

### 4.1 Gross CV for the fuels the DESNZ factors cover, net CV for the three they do not

The brief specifies the gross combustion CO₂ factor from the DESNZ/Defra GHG conversion
factors, gross CV, CO₂-only. That is what 12 of the 15 populated rows carry. The DESNZ set
has no row for `coke`, `coke_oven_gas` or `blast_furnace_gas`, and no UK publication of a
gross-CV factor for them was found. Those three, plus `waste_derived_fuel`, come from
**Annex VI Table 1 of Commission Implementing Regulation (EU) 2018/2066 as retained in UK
law** (legislation.gov.uk) — the standard calculation factors the UK ETS itself uses, in
t CO₂/TJ on a **net** CV basis. `gcv_ncv_basis` records which every row is.

**This is the one place where the files carry two bases in one column.** It is deliberate —
the column exists for exactly this — but it means a consumer must read `gcv_ncv_basis`
before using `ef_gross_kt_per_pj`. See question Q1.

### 4.2 `ef_electricity` is the grid-average factor, not the long-run marginal one

Green Book Table 1 publishes four industrial series. Its own guidance says long-run marginal
factors are for "measuring small changes in consumption or generation" and grid average
factors "are used for footprinting". §7.6 (base-year reconciliation) requires reported totals
to reconcile against `premise_measured_emissions` at the base year, and measured/reported
emissions are footprinted — so `ef_electricity` uses **grid average, consumption-based,
Industrial**. At 2021 that is 58.02 kt/PJ; the long-run marginal figure is 74.73, a 29% gap
that would make every base-year reconciliation fail.

The brief named the long-run marginal series, so it is written too, as
**`ef_electricity_lrmf`** — same table, long-run marginal / consumption-based / Industrial,
all seven periods. Nothing points at it: `carrier.emission_factor_source` is `ef_electricity`.
It is there so the appraisal alternative is one column swap away. See question Q2.

### 4.3 Import prices: actuals for 2021, Green Book projections after

- **2021** — DESNZ *Prices of fuels purchased by manufacturing industry*, Table 3.1.3,
  annual, Great Britain, **excluding the Climate Change Levy**, **size band "Large"**.
  Large is the right band for a CaRB3 premise; the table's other bands are Small, Medium,
  Extra Large and Moderately Large. 2021 cash is 2021 prices, so no deflation.
  Covers `electricity` (31.50), `natural_gas` (7.04), `coal` (3.26),
  `light_fuel_oil` (11.88), `heavy_fuel_oil` (10.11), all £m/PJ.
- **2025–2050** — Green Book supplementary Tables 4–8, retail prices, **Central**,
  **Industrial**, rebased from real 2022 to real 2021 prices with Table 19's UK GDP deflator
  (95.1068 / 100). Covers `electricity`, `natural_gas`, `coal`, `light_fuel_oil`.
  `heavy_fuel_oil` has no Green Book industrial projection, so it has a 2021 row only.

The two sources agree well where they overlap at 2021 (Green Book rebased: electricity
13.35 p/kWh vs the measured 11.34; gas 2.70 p/kWh vs 2.54), so the join is not a step change.
Every row's provenance names its own source, so the mix is visible in the file.

`coal` and the oils are published per tonne or per litre. Converting to £m/PJ needed a
calorific value and a density: both come from the **same** GHG CF 2026 workbook,
sheet "Fuel properties" (coal industrial 26.742 GJ/t gross; gas oil 45.286 GJ/t gross and
1171 litres/tonne; fuel oil 43.353 GJ/t gross). Each conversion is written out in the row's
provenance. This is the weakest link in the price rows and is why they carry
`confidence = medium`.

### 4.4 Export price: long-run variable cost, and no 2021 row

Basis: Green Book Table 9, *Electricity LRVC*, Central, Industrial — the long-run variable
cost of supply, i.e. the supply cost a unit of exported electricity avoids, with fixed
network and policy costs excluded. That is the closest published UK series to what a site is
paid for an export.

**2021 is omitted.** At 2021 the LRVC (14.29 p/kWh, 2022 prices) sits *above* the retail
industrial price (14.04) — the 2021 wholesale spike, a real feature of the data. Writing the
row would ship a known violation of V21 (the export price is strictly below the import price
for every carrier and period), so it is not written. No published UK 2021 export basis was
found that sits below the 2021 industrial import price. The six rows that are written pass
V21 with a wide margin (32.52 vs 45.14 at 2025, 23.66 vs 30.12 at 2050). See question Q3.

### 4.5 Carbon price is the Green Book carbon value at every period, including 2021

The brief asked for the UK ETS 2021 average auction price at the base year and the Green Book
series after. **No UK government publication of a 2021 annual average UK ETS auction clearing
price was found.** What is published is the first auction — 19 May 2021, cleared at
£43.99/tonne — and per-auction results held by ICE, not by a UK department. Averaging 17
auction results off an exchange report centre is not a published figure and would be my
arithmetic, not a source, so it was not done.

All seven periods therefore come from **Green Book Table 3, carbon values, Central**, rebased
to 2021 prices: 244.47 at 2021 rising to 378.07 at 2050, £/tCO₂e. This is the appraisal value,
not a market price, and it is roughly 5.5× the 2021 auction clearing price. See question Q4.

### 4.6 `natural_gas` biogenic fraction is 0.0115, not 0

The GHG CF "Fuels" sheet publishes two natural gas rows and explains the difference:
`Natural gas` is "the gas received through the gas mains grid network in the UK containing a
limited biogas content"; `Natural gas (100% mineral blend)` is the pure fossil case. Both have
the same calorific value in "Fuel properties" (49.521 GJ/t gross), so the whole difference in
kg CO₂/kWh is carbon that has been moved to "Outside of scopes" as biogenic.

So `ef_gross_kt_per_pj` = the 100% mineral blend figure (51.12, the gross combustion carbon),
and `biogenic_fraction` = 1 − 0.18194/0.18405 = 0.0115. Applying the split of §7.3 and D15
(the three-carrier emission split) to those two numbers reproduces the published mains-gas
factor, 50.54 kt/PJ, exactly. That round-trip is the reason for doing it this way rather than
writing 0.

### 4.7 `scenario_parameters` carries the gross factor, not the net-of-biogenic factor

§7.3 (biomass zero-rating applied before capture) and D15 (the three-carrier emission split)
put the fossil/biogenic split at production, driven by `carrier.biogenic_fraction`. So the
`ef_<carrier>` series carries the **gross** factor and the split happens downstream —
`ef_solid_biomass` is 97.22, not 0.

**Both worked examples do the opposite.** The cement example §6.3 lists
`waste_derived_fuel` at 45.0 with the note "direct, **net of biogenic** — gross 92.0,
biogenic fraction 0.511", and the food & drink example §6.3 lists `solid_biomass` at 0.0
"direct, biogenic and zero-rated under §7.3". If the examples' convention is the intended
one, these files are pre-split and would double-apply the zero-rating. See question Q5 — this
is the one that would silently produce wrong numbers.

### 4.8 Infrastructure: `available = FALSE` where nothing is published

Every one of the 189 rows carries a provenance, and the FALSE rows say which published
document establishes the absence:

- **CO₂ transport, TRUE from 2030** at `teesside`, `humber`, `humber2` (East Coast Cluster,
  transport and storage financial close 10 Dec 2024, "operational from 2028") and `mersey`
  (HyNet, financial close 24 Apr 2025, anchor and build-out projects "expected to be
  operational from 2028"). 2028 falls between model periods, so 2030 is the first period
  marked available.
- **CO₂ transport, FALSE throughout** at `grangemouth` and `peterhead` (Acorn) and
  `south_wales`, `southampton`, `medway`. Acorn and Viking were selected for Track-2 but
  **no operational date is published**; the other three are in neither track. FALSE here
  records the absence of a published date, not a published forecast of never.
- **Hydrogen, FALSE everywhere.** The Hydrogen Infrastructure Strategic Planning policy
  statement (October 2025) says "We intend for the UK's first regional hydrogen network to
  become operational from 2031" with "over £500 million" committed — **but names no region**.
  On published evidence no cluster can be marked available. See question Q6; this is the
  single largest scenario gap and it removes every hydrogen unit from every premise under
  C9 (infrastructure availability).
- **Grid headroom, TRUE everywhere**, `capacity_limit` blank. Every GB industrial cluster is
  grid-connected. TRUE here asserts *connection*, not *headroom*: no per-cluster headroom
  figure is published, so an unbounded limit is the honest encoding and the wrong answer for
  any site that is actually constrained.

`humber` and `humber2` inherit the East Coast Cluster date. The Humber leg of the Northern
Endurance pipeline is a later phase than the Teesside leg and no separate Humber date is
published, so both Humberside clusters read across from the cluster-level statement.

---

## 5. Gaps, and why each is a gap

| Gap | Why |
|---|---|
| `hydrogen` — no `ef_gross_kt_per_pj`, no `biogenic_fraction`, no `import_price` | Hydrogen combustion emits no CO₂; the factor is a property of the production route, which is a scenario choice, not a constant. No published UK industrial hydrogen price series exists for any period — the Hydrogen Production Business Model strike prices are project-specific and not published as a series |
| `organic_waste` — no `ef_gross_kt_per_pj` | No UK-published CO₂ factor for the biogenic organic fraction of MSW burned as a fuel. The GHG CF "Outside of scopes" sheet has Wood logs, Wood chips, Wood pellets and Grass/straw, none of which is organic MSW. `biogenic_fraction` is 1 by the carrier's own definition in `carrier.csv` |
| `waste_derived_fuel` — no `biogenic_fraction` | No UK-published biogenic carbon share of RDF/SRF found. The DESNZ *UK & Global Bioenergy Resource Model* methodology (2024) describes a per-nation calculation but publishes no single fraction; the Environment Agency requires it to be measured per consignment under EN ISO 21644 rather than defaulted. Non-UK literature quotes 50–66% but convention 1 rules that out |
| `import_price` for `biomethane`, `lpg`, `coking_coal`, `coke`, `coke_oven_gas`, `blast_furnace_gas`, `solid_biomass`, `wood_pellets`, `organic_waste`, `waste_derived_fuel`, `petroleum_products_misc` | No published UK industrial price series. The DESNZ manufacturing-industry table has LPG and hard coke columns but both are **blank for 2021**; Green Book Tables 4–8 cover only electricity, gas, coal and oil |
| `export_price` at 2021 | No published basis below the 2021 import price — see §4.4 |
| `reinforcement_cost` per voltage band | §3.8 names it and both worked examples quote a figure (£0.42m/MW at 33 kV, £0.65m/MW at 11 kV), but no published UK source for either was found. Not written |
| `capacity_limit` on all 189 infrastructure rows | No published per-cluster CO₂, hydrogen or grid capacity figures. Blank reads as unbounded |
| `unit_tariff` on all 189 infrastructure rows | §3.7 marks it required; the brief says "Tariffs blank unless published" and none is. **The brief wins, so the file violates §3.7's Req column on every row.** Flagged rather than filled |
| `co2_process` intensity per chemistry | Out of scope for this lane — it is declared per process against a mass denominator under D5 (the mass denominator), not a carrier-level factor |
| UK ETS 2021 annual average auction price | See §4.5 |

---

## 6. Questions for Alexandre

**Q1 — one calorific basis, or two?** Twelve rows are gross CV (DESNZ) and four are net CV
(UK ETS MRR); `gcv_ncv_basis` says which. The alternative is to put **everything** on the MRR
net-CV basis, which would be internally consistent, would cover all 16 carriers from one
table, and would make these files agree with both worked examples — the examples' 56.1
(`natural_gas`), 63.1 (`lpg`) and 94.6 (`coal`) are the MRR Annex VI Table 1 values exactly.
The cost is departing from the brief's instruction to use the DESNZ conversion factors.
**My recommendation: switch the whole table to MRR net CV.** It is one source, it is UK law,
it covers every carrier, and it is demonstrably what the worked examples already assume.

**Q2 — `ef_electricity`: grid average or long-run marginal?** Grid average is written, for
the §7.6 reconciliation reason in §4.2; the long-run marginal series is alongside it as
`ef_electricity_lrmf`. If the model is to be read as appraisal of a *change* in consumption
rather than a footprint, swap them. They differ by 29% at the base year.

**Q3 — the 2021 export price.** Options: (a) leave it absent, as now; (b) move the base year
off the 2021 wholesale spike; (c) accept a non-published basis. (a) is what is shipped.

**Q4 — carbon price: appraisal value or market price?** £244/t at 2021 (Green Book) against
£43.99/t (the first UK ETS auction, 19 May 2021). The worked examples use 90 → 275 £/t, which
is neither. Which does §5.4's carbon term mean to charge?

**Q5 — do the `ef_<carrier>` series carry the gross or the net-of-biogenic factor?** These
files say gross, on the §7.3 and D15 reading; both worked examples say net. Getting this
wrong zero-rates biomass twice or not at all, silently. **This is the one to settle first.**

**Q6 — hydrogen availability.** Nothing published names a region for the 2031 network, so
`hydrogen` is FALSE on all 63 rows and C9 (infrastructure availability) deletes every
hydrogen unit from every premise in every period. If a `published_*` scenario is meant to be
runnable rather than strictly evidenced, the minimal defensible change is TRUE from 2035 at
the four Track-1 and Track-2 cluster ids that host HAR1/HPP1 production — but that is an
inference, so it is not in the file.

**Q7 — `waste_derived_fuel` versus `organic_waste`.** `carrier.csv` maps
`waste_derived_fuel` to `INDMSWINO` (the *inorganic*, fossil fraction of MSW) and
`organic_waste` to `INDMSWORG` (the biogenic fraction) — a split already made at the carrier
level. But `waste_derived_fuel`'s `carrier_name` says "mixed fossil and biogenic", and the
cement worked example gives it a biogenic fraction of 0.511. Both cannot be right. If the
COMIT commodity mapping is authoritative, `waste_derived_fuel` should have
`biogenic_fraction = 0` and the blank should close.

**Q8 — `scenario_id`.** These rows use `published_2026`, not the brief's suggested
`published_2024`, because the CCUS and hydrogen statuses are current to September 2026 while
the Green Book tables date from November 2023. Rename if a different convention is wanted.

---

## 7. Requests to other lanes

- **`carrier.csv` (not this lane's file).** Its `emission_factor_source` and
  `biogenic_fraction` columns are empty on all 29 rows. `carrier_factors.csv` supplies both
  for the 17 primary carriers and they should be merged in — `emission_factor_source` is
  `ef_<carrier_id>` on every row, including the two with no published factor, because §3.4
  marks the field required on a `primary` carrier.
- **Whoever owns `docs/notes/README.md`.** `scenario_parameters.csv` and
  `infrastructure_scenario.csv` are new files in `docs/notes/data/` and need rows in the
  index, which is maintained by hand and is the only one.
- **The coordinator.** `references_carriers.csv` adds 10 `ref_id`s, none of which collides
  with the 270 already in `references.csv`. Closest existing entry is `HYNET2022`, which is
  the 2022 Industrial Fuel Switching project report — a different document from
  `HYNET_T1_EXPANSION_2026`.
