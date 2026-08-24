# CaRB3-Driven Per-Site Decarbonisation — Worked Example

**Status:** Draft v1 for review
**Date:** 2026-08-19
**Vision and rationale:** [2026-08-19-carb3-site-decarbonisation-vision.md](2026-08-19-carb3-site-decarbonisation-vision.md)
**Specification:** [2026-08-19-carb3-site-decarbonisation-implementation.md](2026-08-19-carb3-site-decarbonisation-implementation.md)

One premise carried end to end through A1–A9, exercising every input entity. Section
references are to the implementation specification. **All values are illustrative.** They
are internally consistent — every total reconciles, and the arithmetic in each step
follows from the step before — but none is a citation.

The premise is deliberately one that has **site intelligence** (D10 tier 1), so that the
machinery is visible. §11 re-runs the same premise with that intelligence withheld, to
isolate what it buys.

---

## 1. The input

### 1.1 `premise_record` (§3.1)

```
premise_id                   P-000123
carb3_activity               Cement Works
process_set_id               dry_kiln_preheater        -- the activity default
nation                       England
latitude / longitude         53.35 / -1.75
floorspace                   —                          (not supplied)
data_year                    2024
source                       CaRB3 stock model v3.1

import_capacity              25 MW
export_capacity              0 MW
connection_voltage           33 kV
onsite_generation_capacity   0 MW
```

### 1.2 `premise_energy` (§3.1.1)

| `commodity_id` | `vector` | `quantity` (PJ/yr) | `data_status` |
|---|---|---|---|
| `electricity` | electricity | 0.42 | measured |
| `coal` | coal | 2.10 | measured |
| `natural_gas` | gas | 0.31 | measured |
| `waste_derived_fuel` | other | 1.55 | measured |
| `fuel_oil` | oil | 0.00 | **not_consumed** |
| — | biomass | — | **row absent — not assessed** |

**Total 4.38 PJ/yr.** Three things this table shows that the previous wide format could
not:

1. **Waste-derived fuel is just a row.** Cement kilns co-fire substantial quantities of
   SRF/RDF, and under the old fixed columns it had to go through the `energy_other` /
   `energy_other_carrier` escape hatch. Naming its own commodity also lets §7.3 apply the
   right biogenic fraction rather than treating the whole stream as fossil.
2. **`fuel_oil` is an explicit measured zero** — this site burns no oil, and that is
   known.
3. **Biomass is absent, meaning nobody assessed it** — which is *not* the same claim.
   Carrier coverage for this premise is therefore recorded as incomplete and reported in
   §8.5 (§3.1.1, absence rule).

### 1.3 `premise_throughput` (§3.1.2)

| `commodity_id` | `quantity` (Mt/yr) | `data_status` |
|---|---|---|
| `clinker` | 0.85 | measured |

Required, because `Cement Works` carries a mass-denominated process (D5).

### 1.4 `premise_process_detail` (§3.10) — D10 tier 1

From the site's environmental permit:

| `process_id` | `known_capacity` | `technology_code` | `commissioned_year` | `confidence` |
|---|---|---|---|---|
| `quarry_crushing` | — | — | — | medium |
| `raw_milling` | — | — | — | medium |
| `kiln_pyroprocessing` | 0.95 Mt/yr | `kiln_dry_preheater_coal` | 2004 | high |
| `clinker_cooling` | — | — | — | medium |
| `cement_milling` | — | — | — | medium |
| `packing_dispatch` | — | — | — | medium |

Six rows, so this is the site's **complete** process list (§3.10 completeness rule). Only
the kiln carries a capacity and a named technology; the rest are listed to establish that
they exist and nothing more.

### 1.5 `premise_measured_emissions` (§3.11)

From the site's UK ETS account, 2024:

| `source_category` | `ghg` | `quantity` (kt CO₂e/yr) | `scope` |
|---|---|---|---|
| `combustion` | total_co2e | 291 | direct |
| `process` | total_co2e | 452 | direct |

Parts sum to 743 kt, consistent to within the 1% rule.

### 1.6 `premise_operating_profile` (§3.12)

```
operating_pattern            continuous
operating_hours_per_year     8,400
operating_days_per_week      7
shutdown_weeks               3            (annual kiln maintenance)
peak_electricity             16.2 MW
load_factor_electricity      0.82
profile_basis                half_hourly
confidence                   high
```

### 1.7 `process_load_shape` (§3.13)

| `process_id` | `shape_class` | `duty_factor` | `peak_to_mean` | `runs_when_idle` |
|---|---|---|---|---|
| `quarry_crushing` | throughput_following | 0.85 | 1.30 | false |
| `raw_milling` | throughput_following | 0.95 | 1.20 | false |
| `kiln_pyroprocessing` | flat | 1.00 | 1.05 | false |
| `clinker_cooling` | flat | 1.00 | 1.05 | false |
| `cement_milling` | throughput_following | 0.90 | 1.25 | false |
| `packing_dispatch` | intermittent | 0.35 | 3.00 | false |

---

## 2. A1 — ingest and validate

- `nation` is England — in scope (D8).
- `carb3_activity` is one of the 55 Factory-class activities (D1).
- Energy sums to 4.38 PJ/yr > 0.
- No negative quantities; every row's `vector` agrees with its commodity's category.
- Carrier coverage recorded: **five of six vectors stated, biomass unassessed.**
- A `premise_throughput` row exists, as the activity requires (else `missing_throughput`).
- Nearest of the 9 GB clusters assigned.

**Accepted.**

## 3. A2 — expand to the process set

`premise_process_detail` has rows, so **tier 1 applies**: the process set is taken from
the permit, and the activity default is not consulted.

```
process_evidence_tier = "site_known"
process_set = { quarry_crushing, raw_milling, kiln_pyroprocessing,
                clinker_cooling, cement_milling, packing_dispatch }
```

Had this site been a **grinding station** — a cement works with no kiln, importing
clinker — the register's `grinding_only` process set would have applied instead, either
by `process_set_id` (tier 2) or by the permit detail above (tier 1). The activity label
alone cannot distinguish the two, which is the argument for D10.

## 4. A3 — allocate energy across processes

Applying the activity's energy profile (the shares tabulated at implementation §3.3.4,
Example A), with waste-derived fuel assigned wholly to the kiln:

| Process | Electricity | Coal | Gas | WDF | Row total |
|---|---|---|---|---|---|
| `quarry_crushing` | 0.0336 | — | — | — | 0.0336 |
| `raw_milling` | 0.1008 | 0.0630 | 0.0093 | — | 0.1731 |
| `kiln_pyroprocessing` | 0.0924 | 2.0370 | 0.3007 | 1.5500 | 3.9801 |
| `clinker_cooling` | 0.0252 | — | — | — | 0.0252 |
| `cement_milling` | 0.1428 | — | — | — | 0.1428 |
| `packing_dispatch` | 0.0252 | — | — | — | 0.0252 |
| **Total** | **0.4200** | **2.1000** | **0.3100** | **1.5500** | **4.3800** |

Column totals reconcile with §1.2 exactly — **V3 passes**. No optional process is absent,
so the R2 renormalisation is the identity here (§3.3.3).

## 5. A4 — back-solve capacity and utilisation

The kiln's thermal input is 2.0370 + 0.3007 + 1.5500 = **3.8877 PJ/yr**. With
`technology_code = kiln_dry_preheater_coal` supplied, there is no choice among candidate
technologies. Coefficients: `|io| = 4.6 PJ per Mt clinker`,
`capacity_to_activity_factor = 1.0`, `availability_factor = 0.90`.

```
annual_output = 3.8877 / 4.6              = 0.8452 Mt clinker
known_capacity                            = 0.9500 Mt   (from the permit)
utilisation   = 0.8452 / (0.9500 × 1.0)   = 0.890
```

**Capacity is not back-solved here — utilisation is** (§A4 step 14). Three checks follow,
and all three pass:

| Check | Result |
|---|---|
| Utilisation ≤ availability factor (0.890 ≤ 0.90) | Pass — no `capacity_energy_inconsistent` |
| Implied output vs declared throughput (0.8452 vs 0.85 Mt) | 0.57% apart — profile and coefficients agree |
| Utilisation vs operating schedule (continuous, 8,400 h/yr) | Consistent — no `utilisation_schedule_inconsistent` |

The third is the one that only exists because the schedule was supplied. A continuous
site back-solving to 0.89 is credible; the same site back-solving to 0.2 would have
signalled an error in the capacity, the coefficients or the energy, and none of the other
inputs could have told us which.

## 6. A5 — apply the infrastructure scenario

From the premise's cluster, under scenario `central`:

| Carrier | Available | From | Tariff |
|---|---|---|---|
| `co2_transport` | true | 2035 | £18m/Mt |
| `hydrogen` | false | — | — |
| `grid_headroom` | true | throughout | — |

## 7. A6 / A7 — build and solve

Candidate technologies for `kiln_pyroprocessing`: the incumbent coal kiln, a gas kiln, a
biomass/WDF-maximised kiln, and a coal kiln with CCS available from 2035. Milling
processes are electric motor load and switch on fuel price alone.

The solver trades CCS capex plus the CO₂ tariff against avoided carbon cost on **both**
the fuel emissions and the calcination process emissions. That second component is the
decisive one: it cannot be touched by fuel switching at all, so for a cement works the
process-emission term is what makes or breaks the CCS case.

## 8. A8 — assemble output

Rows per process × technology × period across `Outputs`, `Energy`, `Emissions` and
`Costs`. Each row carries:

- `process_evidence_tier = site_known` (§A2)
- the **lower** of the technology's and the energy profile's confidence
- the carrier-coverage flag from A1 — incomplete, biomass unassessed
- the utilisation derived in A4

## 9. §7.6 — reconcile against measured emissions

Computed baseline-year emissions:

| Source | Basis | kt CO₂e |
|---|---|---|
| Process (calcination) | 0.85 Mt clinker × 0.525 t/t | 446 |
| Fuel — coal | 2.10 PJ × 94.6 kt/PJ | 199 |
| Fuel — gas | 0.31 PJ × 56.1 kt/PJ | 17 |
| Fuel — WDF | 1.55 PJ × 45.0 kt/PJ (net of biogenic) | 70 |
| **Computed total** | | **732** |
| **Measured total** (§1.5) | | **743** |

**Divergence 1.5%**, reported and not corrected. The measured split
(291 combustion / 452 process) is adopted for the baseline year in preference to the
computed split (286 / 446), because measured data distinguishes the two sources directly
while the computed split inherits the energy profile's assumptions.

Intensity calibration is **not** applied: it is off by default, and at 1.5% divergence
there is nothing to explain.

## 10. §5.6 — what the peak data supports

**Not implemented.** Shown because this premise carries the inputs the extension needs.

Baseline electrical demand:

```
mean over operating hours = 0.42 PJ/yr × 277,778 / 8,400 h  = 13.9 MW
measured peak                                                = 16.2 MW
implied within-shift peak factor λ = 16.2 / 13.9             = 1.17
```

λ is *observed* here rather than assumed, because the site supplied both a schedule and a
metered peak. That observed value is what makes a credible default for cement works that
supply only a schedule.

Now the question the extension exists to answer. If the kiln's 3.8877 PJ/yr of thermal
input were fully electrified:

```
mean electrical demand = 3.8877 × 277,778 / 8,400 = 128.6 MW
import_capacity                                    =  25.0 MW
```

**A factor of five beyond the connection**, before any peaking factor is applied. For
this premise, electrification is not a fuel-price question at all — it is a network
reinforcement question, and a model that ignores the connection would happily electrify
the kiln for free. This is the single clearest argument for extension 1.

## 11. The same premise, without site intelligence

Identical `premise_record`, `premise_energy` and `premise_throughput`; §1.4 to §1.7
withheld. This section is deliberately shorter than the walkthrough above — it is not a
second example, but the same one re-run to isolate what the optional inputs contribute.

| Step | With intelligence (tier 1) | Without (tier 3) |
|---|---|---|
| A2 | Process set from the permit; `site_known` | Activity default set; `activity_default` |
| A4 | Capacity **known** 0.950 Mt; utilisation derived 0.890 | Capacity **inferred** 0.939 Mt at assumed availability 0.90; utilisation not independently known |
| A4 checks | Three cross-checks, all passing | One — implied output vs declared throughput |
| §7.6 | Divergence measured at 1.5%; measured split adopted | No reconciliation possible; computed split stands unexamined |
| §5.6 | λ observed at 1.17; reinforcement gap quantified | λ assumed from an activity default; peak uncertain |
| Output confidence | Governed by profile confidence | Governed by the weakest of several defaults |

The two capacity figures differ by only 1.2%, which is reassuring rather than
disappointing — it says the back-solve is sound for sites where nothing better exists.
What tier 1 changes is not primarily the number but **how much of the answer is
checkable**: four independent cross-checks become one.

## 12. What this example demonstrates

1. **The mass denominator is load-bearing (D5).** Had `kiln_pyroprocessing` been
   denominated in PJ, its 446 kt of calcination CO₂ would have scaled with fuel
   efficiency, and a more efficient kiln would have appeared to emit less process CO₂ —
   which is physically wrong, since that CO₂ comes from the limestone.
2. **The long format earns its place immediately.** Waste-derived fuel at 35% of this
   site's energy is an ordinary row rather than an escape hatch, and the measured zero
   for oil is distinguishable from the unassessed biomass.
3. **Site intelligence changes what is checkable more than what is computed** (§11).
4. **Peak and energy are different questions** (§10). This site's annual energy says
   electrification is straightforward; its connection capacity says it is a
   reinforcement project five times larger than the existing supply.
