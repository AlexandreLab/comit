# CaRB3-Driven Per-Site Decarbonisation — Worked Example

**Status:** Draft v1 for review
**Date:** 2026-08-19
**Vision and rationale:** [2026-08-19-carb3-site-decarbonisation-vision.md](2026-08-19-carb3-site-decarbonisation-vision.md)
**Specification:** [2026-08-19-carb3-site-decarbonisation-implementation.md](2026-08-19-carb3-site-decarbonisation-implementation.md)

One premise carried end to end through A1–A9, exercising every input entity. Section
references are to the implementation specification. **All values are illustrative.** They
are internally consistent — every total reconciles, and the arithmetic in each step
follows from the step before — but none is a citation.

The premise is deliberately one that has **site intelligence** (D10 tier 1) and a known
**plant vintage** (D11 tier 1), so that the machinery is visible. §11 re-runs the same
premise with that intelligence withheld, to isolate what it buys — and for vintage the
answer is not a sharper number but a different pathway.

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
construction_year            1957
last_refurbishment_year      2011                       (collected, not read)
data_year                    2024
source                       CaRB3 stock model v3.1
```

The works dates from 1957, which under D11 bounds plant age at 68 years — longer than any
technology lifetime on site, so the bound is slack and buys nothing here (§5.3.1 tier 2).
That is the expected outcome for heavy industry and is shown deliberately — implementation
§5.3.1 works the tier-2 formula through a young premise, where it binds hard and settles
the question on its own.

### 1.2 `premise_connection` (§3.1.3)

A single electricity connection, so `connection_id` may be omitted everywhere downstream
and the defaults apply. A works with a second supply serving, say, the cement mills would
carry a second row here — and its headroom would be assessed separately, never added to
the first.

| `connection_id` | `carrier` | `is_default` | `import_capacity` | `export_capacity` | `connection_voltage` | `metering_type` |
|---|---|---|---|---|---|---|
| `C-01` | electricity | true | 25 MW | 0 MW | 33 kV | half_hourly |

### 1.3 `premise_energy` (§3.1.1)

| `commodity_id` | `vector` | `quantity` (PJ/yr) | `data_status` |
|---|---|---|---|
| `electricity` | electricity | 0.42 | measured |
| `coal` | coal | 2.10 | measured |
| `natural_gas` | gas | 0.31 | measured |
| `waste_derived_fuel` | other | 1.55 | measured |
| `fuel_oil` | oil | 0.00 | **not_consumed** |
| — | biomass | — | **row absent — not assessed** |

**Total 4.38 PJ/yr**, all through the single connection `C-01`. Three things this table shows that the previous wide format could
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

### 1.4 `premise_throughput` (§3.1.2)

| `commodity_id` | `quantity` (Mt/yr) | `data_status` |
|---|---|---|
| `clinker` | 0.85 | measured |

Required, because `Cement Works` carries a mass-denominated process (D5).

### 1.5 `premise_process_detail` (§3.10) — D10 tier 1

From the site's environmental permit:

| `process_id` | `known_capacity` | `technology_code` | `confidence` |
|---|---|---|---|
| `quarry_crushing` | — | — | medium |
| `raw_milling` | — | — | medium |
| `kiln_pyroprocessing` | 0.95 Mt/yr | `kiln_dry_preheater_coal` | high |
| `clinker_cooling` | — | — | medium |
| `cement_milling` | — | — | medium |
| `packing_dispatch` | — | — | medium |

Six rows, so this is the site's **complete** process list (§3.10 completeness rule). Only
the kiln carries a capacity and a named technology; the rest are listed to establish that
they exist and nothing more. When the plant was installed is not here — it lives in §1.9,
for the reason given in §3.10.

### 1.6 `premise_measured_emissions` (§3.11)

From the site's UK ETS account, 2024:

| `source_category` | `ghg` | `quantity` (kt CO₂e/yr) | `scope` |
|---|---|---|---|
| `combustion` | total_co2e | 291 | direct |
| `process` | total_co2e | 452 | direct |

Parts sum to 743 kt, consistent to within the 1% rule.

### 1.7 `premise_operating_profile` (§3.12)

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

### 1.8 `process_load_shape` (§3.13)

| `process_id` | `shape_class` | `duty_factor` | `peak_to_mean` | `runs_when_idle` |
|---|---|---|---|---|
| `quarry_crushing` | throughput_following | 0.85 | 1.30 | false |
| `raw_milling` | throughput_following | 0.95 | 1.20 | false |
| `kiln_pyroprocessing` | flat | 1.00 | 1.05 | false |
| `clinker_cooling` | flat | 1.00 | 1.05 | false |
| `cement_milling` | throughput_following | 0.90 | 1.25 | false |
| `packing_dispatch` | intermittent | 0.35 | 3.00 | false |

### 1.9 `premise_process_vintage` (§3.15) — D11 tier 1

From the same environmental permit, which records the kiln line's commissioning:

| `process_id` | `cohort_id` | `technology_code` | `commissioned_year` | `capacity_share` | `confidence` |
|---|---|---|---|---|---|
| `kiln_pyroprocessing` | `1` | `kiln_dry_preheater_coal` | 2004 | 1.00 | high |

One row, because this works runs a single kiln line. The shares sum to 1.00, as §3.15
requires.

**No rows for the other five processes**, and that is not an omission — unlike §1.5, this
table asserts nothing about completeness. The mills and the packing plant fall through to
tier 2, which on a 1957 works is slack, and therefore to tier 3. So this premise resolves
its kiln at `process_known` and everything else at `uniform_default`, in the same solve.
That mixture is the normal case, not an edge case.

**What a second line would look like.** A works whose second kiln was added in 2016 would
carry two rows for `kiln_pyroprocessing` — cohort `1` at 2004 with share 0.60 and cohort
`2` at 2016 with share 0.40 — and §5.3.1 would age the two independently, the older line
retiring in 2043 and the newer in 2055. Recording that site as a single 2011 average kiln,
which is what the old `commissioned_year` column forced, would have retired all of it at
once in 2050: too late for the old line and too early for the new one.

---

## 2. A1 — ingest and validate

- `nation` is England — in scope (D8).
- `carb3_activity` is one of the 55 Factory-class activities (D1).
- Energy sums to 4.38 PJ/yr > 0.
- No negative quantities; every row's `vector` agrees with its commodity's category.
- Carrier coverage recorded: **five of six vectors stated, biomass unassessed.**
- A `premise_throughput` row exists, as the activity requires (else `missing_throughput`).
- `commissioned_year` 2004 ≤ `data_year` 2024, so the vintage row is accepted; shares sum
  to 1.00 (else `vintage_in_future` or `vintage_shares_unbalanced`, §3.15).
- `construction_year` 1957 ≤ `data_year`; `last_refurbishment_year` 2011 lies between them.
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

## 5. A4 — back-solve capacity, utilisation and vintage

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

**Vintage (D11, §5.3.1).** Scenario `central` runs 2025 to 2050 in five-year periods, so
$t_0$ = 2025, with `stranding_factor` λ = 1.0. The kiln's lifetime is `L` = 40 years and
its capex `κ` = £260m per Mt/yr of capacity.

The tiers resolve per technology, not per premise:

| Process | Tier | Age window at 2025 | Why |
|---|---|---|---|
| `kiln_pyroprocessing` | `process_known` | point mass at 21 years | §1.9 gives the cohort year, 2004 |
| The other five | `uniform_default` | [0, 40] | No cohort row; the 1957 bound is slack |

For the kiln, the final operating year is 2004 + 40 − 1 = **2043**:

| | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|
| Elapsed years τ | 0 | 5 | 10 | 15 | 20 | 25 |
| Survival θ | 1.00 | 1.00 | 1.00 | 1.00 | 0 | 0 |
| Standing capacity (Mt/yr) | 0.950 | 0.950 | 0.950 | 0.950 | 0 | 0 |
| Mean remaining life R̄ (yr) | 19 | 14 | 9 | 4 | 0 | 0 |
| Stranding rate (£m per Mt/yr) | 123.5 | 91.0 | 58.5 | 26.0 | 0 | 0 |
| Write-off if scrapped whole (£m) | 117.3 | 86.5 | **55.6** | 24.7 | 0 | 0 |

A point mass has no spread, so R̄ is exact here rather than a pool average, and the
stranding rate is simply κ × R̄ / L — at 2035, £260m × 9 / 40 = £58.5m per Mt/yr.

**The same kiln under tier 3**, had §1.9 been absent, for contrast:

| | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|
| Survival θ | 1.000 | 0.875 | 0.750 | 0.625 | 0.500 | 0.375 |
| Standing capacity (Mt/yr) | 0.950 | 0.831 | 0.713 | 0.594 | 0.475 | 0.356 |
| Mean remaining life R̄ (yr) | 20.0 | 17.5 | 15.0 | 12.5 | 10.0 | 7.5 |
| Stranding rate (£m per Mt/yr) | 130.0 | 113.8 | 97.5 | 81.3 | 65.0 | 48.8 |

The two survival paths could hardly be less alike, and one number decides which the site
gets. Meeting the back-solved 0.8452 Mt/yr of output at an availability factor of 0.90
needs **0.939 Mt/yr** of standing capacity. Under tier 1 the kiln clears that until it
dies in 2043. Under tier 3 it falls to 0.831 Mt/yr by **2030** — a shortfall of 0.108
Mt/yr, five years before CO₂ transport arrives, forcing a piecemeal unabated rebuild that
the site would then be carrying when CCS becomes available in 2035.

Both are defensible readings of a fleet of kilns. Only one is a reading of *this* kiln,
and the difference between them is a single line on a permit.

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

**What D11 adds to that trade.** The kiln has 19 years of life left at $t_0$, and until
2043 the model may keep it, convert it or scrap it. Scrapping it charges the write-off
from §5. Take the gas-kiln option — a switch that looks attractive whenever gas plus
carbon undercuts coal plus carbon — at a rebuild cost of £300m per Mt/yr, so £285m for
this site:

| Switch the kiln away from coal in | 2025 | 2030 | 2035 | 2040 | 2045 |
|---|---|---|---|---|---|
| Write-off charged (£m) | 117.3 | 86.5 | 55.6 | 24.7 | 0 |
| As a share of the £285m rebuild | 41% | 30% | 20% | 9% | 0% |

**The charge does not forbid the switch — it prices delay**, and that is the behaviour
this design was after. Each period of waiting removes a constant £30.9m of write-off
(κ × 0.95 Mt × 5 ⁄ 40, which is just the kiln depreciating), so a switch that is
marginally uneconomic in 2030 becomes comfortably economic by 2040, and by 2045 the kiln
has died on its own and the switch is free. A carbon price high enough to clear £86.5m
still buys the kiln out in 2030 — nothing here is prohibited, only priced.

**Retrofit pays none of it.** The CCS option available from 2035 is a retrofit: it bolts a
capture train onto the existing kiln rather than replacing it, so the plant is not
scrapped, `Stranded value` is zero, and §5.5's retrofit rule keeps the capture train on
the kiln's own 2043 end-of-life rather than giving it a fresh one. That last part cuts
both ways — the retrofit's capex is annuitised over the 9 years the host has left rather
than its own 25 (§5.4), which roughly doubles its annual charge and is the honest cost of
retrofitting late onto old plant.

So the model's 2035 choice is between a cheap retrofit on a kiln that dies in 2043 and an
expensive rebuild that lives past the horizon, with £55.6m of write-off attached to the
second. Before D11 that £55.6m was zero and the 2043 death did not exist, so the two
options differed only in capex and fuel cost.

## 8. A8 — assemble output

Rows per process × technology × period across `Outputs`, `Energy`, `Emissions` and
`Costs`. Each row carries:

- `process_evidence_tier = site_known` (§A2)
- the **lower** of the technology's and the energy profile's confidence
- the carrier-coverage flag from A1 — incomplete, biomass unassessed
- the utilisation derived in A4
- `vintage_evidence_tier` — `process_known` on the kiln rows, `uniform_default` on the
  other five processes, since the tiers resolve per technology (§5)
- `commissioned_year = 2004` on the kiln rows and **blank** on the rest. The other five
  do have a working age assumption, but writing its midpoint here would make an inferred
  date indistinguishable from a permit date (§8.1)
- `remaining_life_years` — 19, 14, 9, 4, 0, 0 across the six periods for the kiln,
  anchored on 2025 and not on the 2024 `data_year`
- a `Stranded value` cost row, zero in every period unless the solve scraps the kiln
  early

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

Identical `premise_record`, `premise_energy`, `premise_connection` and
`premise_throughput`; §1.5 to §1.8 withheld. This section is deliberately shorter than the walkthrough above — it is not a
second example, but the same one re-run to isolate what the optional inputs contribute.

| Step | With intelligence (tier 1) | Without (tier 3) |
|---|---|---|
| A2 | Process set from the permit; `site_known` | Activity default set; `activity_default` |
| A4 | Capacity **known** 0.950 Mt; utilisation derived 0.890 | Capacity **inferred** 0.939 Mt at assumed availability 0.90; utilisation not independently known |
| A4 checks | Three cross-checks, all passing | One — implied output vs declared throughput |
| A4 vintage | Kiln aged from its 2004 permit date; `process_known`; stands whole until 2043 | Uniform default; `uniform_default`; 12.5% of the kiln already gone by 2030 |
| Replacement timing | Free to wait for CCS in 2035; nothing forced | A 0.108 Mt/yr shortfall from **2030**, forcing an unabated rebuild five years before CCS exists |
| Early switching | Write-off exact: £55.6m at 2035, falling £30.9m a period | Write-off is a pool average, £97.5m per Mt/yr at 2035, and overstates the cost of scrapping the oldest capacity (§5.3.1) |
| §7.6 | Divergence measured at 1.5%; measured split adopted | No reconciliation possible; computed split stands unexamined |
| §5.6 | λ observed at 1.17; reinforcement gap quantified | λ assumed from an activity default; peak uncertain |
| Output confidence | Governed by profile confidence | Governed by the weakest of several defaults |

The two capacity figures differ by only 1.2%, which is reassuring rather than
disappointing — it says the back-solve is sound for sites where nothing better exists.
What tier 1 changes is not primarily the number but **how much of the answer is
checkable**: four independent cross-checks become one.

**Vintage is the exception, and it is a large one.** Everywhere else in this table the
optional inputs sharpen a number the model would have got roughly right anyway. Here they
change the answer outright: with the permit date the site waits and retrofits, and without
it the site is rebuilding from 2030. Capacity was 1.2% apart; the pathways are not
comparable at all. That asymmetry is worth knowing when deciding what site intelligence is
worth collecting — one line recording when the kiln was commissioned buys more than
everything else in §1.5 put together.

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
5. **Plant age changes the pathway, not just the cost** (§5, §7, §11). The same kiln, the
   same technologies and the same prices give a 2030 unabated rebuild under the default
   vintage assumption and a 2035 CCS retrofit under the permit's commissioning date. No
   other optional input in this example moves the answer that far.
6. **The write-off prices delay rather than forbidding change** (§7). It falls by a
   constant £30.9m every period as the kiln depreciates, so a switch the model rejects in
   2030 it accepts in 2040 — and a carbon price high enough still buys the kiln out early.
   That is the difference between representing inertia and hard-coding it.
