# CaRB3 Site Energy System — Worked Example: a food and drink site

**The mechanism case.** One premise carried end to end through the nine algorithms `A1`–`A9`
(§4), exercising the thing the model exists for and the
[cement works](2026-08-28-carb3-site-energy-system-worked-example-cement.md) structurally
cannot show: eight fuel-variant technology rows collapsing to three units, a 120 °C duty with
a boiler, a CHP, a heat pump and an electric resistance heater competing under C10 (the grade
cascade), reject heat carried by its source class with the chillers' condenser heat lifted by a
heat pump, a CHP producing heat **and** electricity into the carrier balance, rooftop PV
bounded by C12 (siting cap), and an electricity export priced below the import price that the
solve never uses, because the site never has a surplus.

Section references without a document name are to the
[implementation specification](2026-08-28-carb3-site-energy-system-implementation.md).
Feature labels `MF-nn` are from
[notes/18](../notes/18_mvp_feature_prioritisation.md); task labels `Tnn` from the
[delivery document](2026-08-28-carb3-site-energy-system-delivery.md).

**All values are illustrative.** They are internally consistent — every total reconciles and
every step's arithmetic follows from the one before — but none is a citation. Money is £m at
2021 prices, energy PJ, emissions kt CO₂e, area m², power MW, on §1's conventions.
Intermediate arithmetic is carried at six significant figures and quoted at five.

**What is the example's own and what is the reference data's.** Every unit coefficient of §1.11
(efficiencies, co-products, reject rows and their carriers) agrees with
[`unit_input_output.csv`](../notes/data/unit_input_output.csv), and the three heat-recovery
units take their costs from [`unit.csv`](../notes/data/unit.csv), which is the only place they
are stated. The other units' costs, lifetimes and availability factors, the scenario of §6 and
the duty profile of §3.2 are the example's own and differ from the reference tables; the
`carb3` run of the synthetic dairy `mvp-dairy` reads those tables instead, which is why its
pathway differs from §8.7 in the ways §8.7 lists.

This document and the
[cement one](2026-08-28-carb3-site-energy-system-worked-example-cement.md) are deliberately
parallel: the same thirteen sections, in the same order, at the same depth. Where a finding is
shared it is stated identically in both.

---

## 1. The premise

### 1.1 `premise_record` (§3.1)

```
premise_id                   P-004417
carb3_activity               Food Processing Centre
process_set_id               —                      (absent ⇒ the activity's default set)
nation                       England
latitude / longitude         53.39 / -2.59
floorspace                   18,400 m²
construction_year            —
construction_year_band       1965-1984              ← read as its EARLIEST year, 1965
last_refurbishment_year      2019                   (collected, not read — §3.1)
data_year                    2024                   ← the base year (D12)
source                       CaRB3 stock model v3.1
```

The site is a milk-powder dairy: liquid intake, pasteurising and clean-in-place, evaporation,
spray drying, cold storage.

**`construction_year` is absent and a band is given**, which is the ordinary case for
CaRB3-style stock data. §3.1's rule reads a band as its **earliest** year, 1965, because that
is the conservative reading: it admits the widest range of plant ages and therefore stays
closest to the default tier. Reading it as the midpoint or the latest year would make plant
look younger than the evidence supports, and erring in that direction is the more dangerous
mistake. At this premise the bound is slack anyway — §1.6 gives cohort years for the plant
that matters.

### 1.2 `premise_energy` (§3.1.1) — consumption by carrier per year

| `carrier_id` | `vector` | `quantity` PJ/yr | `data_status` | `data_year` | Read as |
|---|---|---|---|---|---|
| `natural_gas` | gas | 0.31500 | measured | 2022 | history |
| `natural_gas` | gas | 0.30800 | measured | 2023 | history |
| `natural_gas` | gas | **0.30000** | measured | **2024** | **base year** |
| `electricity` | electricity | 0.05700 | measured | 2022 | history |
| `electricity` | electricity | 0.05900 | measured | 2023 | history |
| `electricity` | electricity | **0.06000** | measured | **2024** | **base year** |
| `fuel_oil` | oil | **0.00000** | **not_consumed** | **2024** | **base year** |
| `coal` | coal | **0.00000** | **not_consumed** | **2024** | **base year** |
| `solid_biomass` | biomass | **0.00000** | **not_consumed** | **2024** | **base year** |

**Base-year energy read by the model: 0.30000 + 0.06000 = 0.36000 PJ/yr.**

**Carrier coverage is complete**, and that is the contrast with the cement works, where
`solid_biomass` was absent and the premise carried an incomplete-coverage flag on every output
row. Here all five main vectors are stated — two by a positive quantity and three by an
explicit `not_consumed` zero — which is what §3.1.1 asks the stock model to aim for. A missing
row would have meant *"nobody checked"*, and at a dairy that is a materially different claim
from *"this site burns no coal"*: coal firing is exactly the option a decarbonisation model
would otherwise report as unexamined.

**The electricity row is a net import, not site consumption**, and this premise is where that
distinction bites. The site runs a CHP (§1.12), so the meter reads what the CHP did not
supply. Reconstructing consumption from the meter is `A4`'s job (§5.1), and getting it wrong
understates the site's electrical load by 32%.

The 2022 and 2023 rows are **history**. `V25` (history is never read) asserts that adding
them, at years before *and* after the base year, moves no §5.3 parameter, no constraint
coefficient, no solution value and no reported reconciliation by more than 1e-9.

### 1.3 `premise_throughput` (§3.1.2) — physical output by carrier per year

**Zero rows, and that is correct.** `Food Processing Centre` carries no mass-denominated
process: every one of its six processes is an energy service under `D5` (hybrid denominators),
so the site is denominated wholly in PJ. §3.1.2's rule is explicit — activities with no
mass-denominated process need no rows at all — and `A1` does **not** reject the premise with
`missing_throughput`.

This is the cleanest available contrast with the cement works, where the same rule makes
throughput mandatory and the two duties are masses. `D5`'s two denominator conventions are
both exercised across the pair of examples and neither example exercises both.

### 1.4 `premise_connection` (§3.1.3)

| `connection_id` | `carrier_id` | `import_capacity` | `export_capacity` | `connection_voltage` | `available_area` |
|---|---|---|---|---|---|
| `E-01` | `electricity` | **4 MW** | **2 MW** | 11 kV | **12,000 m²** |
| `G-01` | `natural_gas` | 18 MW | 0 MW | — | — |

**Capacities are never summed across connections** (§3.1.3), and C11 (connection capacity) is
written per connection for exactly that reason. A 4 MW electrical supply and an 18 MW gas
supply are not 22 MW of anything.

**`available_area` is supplied directly**, from a site survey, so
`area_evidence_tier = measured` — the top rung of the `D10` ladder (tiered site intelligence)
for this input. The cement works had none and fell to `MF-09`'s footprint proxy, floorspace
times a per-activity usable-area ratio, at tier `proxy`. Both tiers appear on output rows and
neither is mistaken for the other. Without an area at all, C12 is unbounded and the LP builds
infinite PV.

The 2 MW `export_capacity` never binds: the site imports electricity in every period, so the
export variable it bounds stays at zero (§8.6).

### 1.5 `premise_process_detail` (§3.10) — `D10` tier 1 (known site detail wins)

From the site's Climate Change Agreement audit, 2024:

| `process_id` | `valid_from_year` | `valid_to_year` | `connection_id` | `known_capacity` | `known_activity` | `confidence` |
|---|---|---|---|---|---|---|
| `boiler_steam_hot_water` | 2011 | — | `E-01` | — | — | high |
| `direct_heating` | **2019** | — | `E-01` | **0.10000 PJ/yr** | 0.07905 PJ/yr (the §3.2 duty, its four band segments summed) | **high** |
| `refrigeration` | 2016 | — | `E-01` | — | — | high |
| `machinery_motors` | 2011 | — | `E-01` | — | — | medium |
| `compressed_air` | 2011 | — | `E-01` | — | — | medium |
| `site_services` | 2011 | — | `E-01` | — | — | medium |

Six rows, matching the register's default set for `Food Processing Centre` exactly, so this is
the site's **complete** process list as at any year in range (§3.10's completeness rule). No
interval is closed: this dairy has not changed route, which is the ordinary case and the
reason `V26`'s interval machinery is usually invisible.

**`valid_from_year` 2011 on four rows is stated, not blank.** The audit names the processes
without saying when each began; §3.10 requires the field, and where the year is unknown the
rule is to state `premise_record.data_year` and say so in `provenance`. Here the audit does
give one date — the 2011 rebuild that installed the boiler house and the CHP — so 2011 is a
genuine observation and the `provenance` field records which document it came from.

**Only `direct_heating` carries a capacity.** Which units each process runs is not on this
table; that is §1.5.1.

### 1.5.1 `premise_process_unit` (§3.10.2) — which units a known process runs, and when each was installed

From the same audit:

| `process_id` | `valid_from_year` | `cohort_id` | `unit_id` | `commissioned_year` | `capacity_share` | `confidence` |
|---|---|---|---|---|---|---|
| `boiler_steam_hot_water` | 2011 | `1` | `chp_gas_turbine` | **2011** | — | high |
| `boiler_steam_hot_water` | 2011 | `2` | `boiler_lt_gas` | **2016** | — | medium |
| `direct_heating` | 2019 | `1` | `dryer_direct_gas` | **2019** | — | high |

**The audit names the plant of two processes, and that makes it known.** Under §3.10's
precedence rule `A4` does not choose among candidates for `boiler_steam_hot_water` or
`direct_heating`: the boiler house is a CHP plus a gas boiler, and the spray dryer is a direct
gas dryer. For `direct_heating`, with a `known_capacity` on the parent (and `known_activity`, the duty it runs at), `A4` back-solves
*utilisation* rather than capacity (§5.1). The other four processes have no rows, so their
plant is unknown and comes from `activity_default_unit` (§1.12).

**What the audit does not give is the split.** `capacity_share` is blank, which §3.10.2
allows because each unit is a single cohort. The boiler house's two units both burn
`natural_gas`, so the meter cannot separate them either, and the split between CHP and boiler
falls to the activity default of §1.12: 0.60 / 0.40 on the steam duty (§5.2). **Naming a CHP
does not size it.** Had the audit not named it at all, §1.12 would be the only thing putting
a CHP on this site.

### 1.6 Plant age (§3.10.2's `commissioned_year`) — `D11` tier 1

The `commissioned_year` column above is the vintage evidence. **Two cohorts inside one
premise-process**: the CHP and the boiler serve the same duty family from the same boiler
house and were commissioned five years apart, which is why §3.10.2 is keyed per cohort rather
than per process. Each is aged on its own year rather than on an average of the two; that both
reach end of life in 2035 below is the lifetimes, not the dates. The 2016 boiler joins the
2011 interval as cohort 2 and opens no new interval, because replacing or adding plant is not
a fact on the §3.10 row (§3.10, "what opens a new version").

**Refurbishment is not recommissioning** (§3.10.2). The 2019 entry in `last_refurbishment_year`
(§1.1) is a packing-hall extension, not a recommissioning of any of these three units, and it
stays collected and unread.

End-of-life years follow from the lifetimes of §1.11:

| Unit | Cohort | $L$ | Last operating year |
|---|---|---|---|
| `chp_gas_turbine` | 2011 | 25 | **2035** |
| `boiler_lt_gas` | 2016 | 20 | **2035** |
| `dryer_direct_gas` | 2019 | 20 | **2038** |

All three incumbents die inside the horizon, and the boiler house dies as one — which makes
2040 a genuinely open investment decision rather than a marginal retrofit. That is the shape
this example was chosen for.

### 1.7 `premise_measured_emissions` (§3.11)

From the site's Climate Change Agreement returns:

| `emission_year` | `source_category` | `ghg` | `quantity` kt CO₂e/yr | `scope` |
|---|---|---|---|---|
| 2022 | combustion | total_co2e | 17.9 | direct |
| 2023 | combustion | total_co2e | 17.3 | direct |

**No row at the base year.** Under §3.1.1's table this is **reported as
`emissions_year_unmatched` and never a rejection**: the entity is optional intelligence, and
rejecting the premise would discard the evidence. §7.6's reconciliation is skipped and said to
be skipped (§10.2). The cement works is the opposite case — a base-year row exists there, the
reconciliation runs, and it closes to 1.96% — so the two examples between them exercise both
branches of the rule.

No `process` rows, because the site has no process chemistry; no `total` row, because the
split was never in doubt.

### 1.8 `premise_operating_profile` (§3.12)

| Field | `E-01` (electricity) | `G-01` (gas) |
|---|---|---|
| `profile_year` | 2024 | 2024 |
| `operating_pattern` | three_shift | three_shift |
| `operating_hours_per_year` | 7,200 | 7,200 |
| `operating_days_per_week` | 6 | 6 |
| `shutdown_weeks` | 2 | 2 |
| `peak_electricity` | 3.4 MW | — |
| `peak_gas` | — | 14.5 MW |
| `load_factor_electricity` | 0.56 | — |
| `load_factor_gas` | — | 0.66 |
| `within_shift_peak_factor` | **1.47** | 1.25 |
| `profile_basis` | half_hourly | monthly |
| `confidence` | high | medium |

§3.12's consistency rule, at like years:

$$\text{load factor} = \frac{E\,[\text{PJ/yr}] \times 277{,}778}{P^{\text{peak}}\,[\text{MW}] \times 8{,}760}$$

- Electricity: 0.06000 × 277,778 = 16,667 MWh; ÷ (3.4 × 8,760 = 29,784) = **0.55959**, against
  the declared 0.56 — **0.07% apart**, inside the 5% tolerance.
- Gas: 0.30000 × 277,778 = 83,333 MWh; ÷ (14.5 × 8,760 = 127,020) = **0.65607**, against the
  declared 0.66 — **0.60% apart**.

Neither is reported as `profile_energy_inconsistent`.

The within-shift peak factor is *observed*: mean electrical demand over operating hours is
16,667 ÷ 7,200 = **2.3148 MW**, and 3.4 ÷ 2.3148 = **1.4688**, quoted as 1.47. That figure is
what §8.5's connection arithmetic runs on, and it is higher than the cement works' 1.17
because a three-shift dairy with batch clean-in-place is peakier than a continuous kiln.

**The electricity load factor is measured against the meter, and the meter nets the CHP.** A
site peak of 3.4 MW against a 4 MW connection leaves 0.6 MW of headroom on the *import* side
only; the CHP's output sits behind it and is not headroom.

### 1.9 `premise_weekly_profile` (§3.14)

Supplied for `electricity` at `E-01` and for `gas` at `G-01`, `season = annual`,
`profile_year = 2024`, 336 half-hourly points each, normalised so the week's maximum is 1,
with `annual_peak` recorded separately as 3.4 MW and 14.5 MW. Not tabulated here.

§3.14's rule bites at this site: the representative week's own electrical maximum is 3.1 MW
and the annual maximum is 3.4 MW, a 9% understatement, because the dairy's heaviest week is a
summer intake peak that a typical week is typical by construction of excluding. The week gives
the *shape*; `annual_peak` carries the *level*.

§3.14 also recommends seasonal weeks wherever §3.13 declares seasonality other than `none`,
and `refrigeration` here is `summer_weighted` (§1.10). Only an `annual` week was supplied, so
the annual peak cannot be attributed to the right process when the mix changes. Reported, not
failed.

### 1.10 `process_load_shape` (§3.13)

| `process_id` | `shape_class` | `duty_factor` | `peak_to_mean` | `runs_when_idle` | `seasonality` |
|---|---|---|---|---|---|
| `boiler_steam_hot_water` | batch_cyclic | 0.55 | 2.40 | false | none |
| `direct_heating` | flat | 1.00 | 1.10 | false | none |
| `refrigeration` | **standing** | 1.00 | 1.00 | **true** | **summer_weighted** |
| `machinery_motors` | throughput_following | 0.85 | 1.35 | false | none |
| `compressed_air` | throughput_following | 0.80 | 1.45 | false | none |
| `site_services` | **standing** | 1.00 | 1.00 | **true** | none |

§3.13's rule holds: the two `standing` rows carry `runs_when_idle = true` and every other row
false. That distinction is what makes this site's peak differ from its energy — the cold store
runs through both shutdown weeks and the evaporator does not — and it is why the within-shift
peak factor of §1.8 is 1.47 rather than something closer to 1.

**The shape belongs to the process, not to the unit** (§3.13). The spray dryer runs flat
whether it is fired by gas, by hydrogen or by an electric heater, so the shape is declared once
here and inherited by every unit serving `direct_heating`. Declaring shapes per unit would have
multiplied this table by the fuel variants of §3.3 — eight rows where one will do — for
information that does not vary along that axis. No unit at this premise sets
`load_shape_override`.

### 1.11 Reference data this premise reads

**Carriers (§3.4).** Nineteen rows are in play: four graded heat, one graded cooling and five
reject carriers, one per source class of reject heat.
Ranks count within a grade family (§3.4), so `cooling_0_15`'s rank 2 is the cooling family's
chilled-water band and has nothing to do with heat rank 2.

| `carrier_id` | `carrier_kind` | `is_gradeable` | `grade_rank` | `grade_label` | `is_indirect` | `denominator_kind` | `may_import` | `may_export` |
|---|---|---|---|---|---|---|---|---|
| `natural_gas` | primary | no | — | — | no | energy | yes | no |
| `hydrogen` | primary | no | — | — | no | energy | yes | no |
| `solid_biomass` | primary | no | — | — | no | energy | yes | no |
| `lpg` | primary | no | — | — | no | energy | yes | no |
| `coal` | primary | no | — | — | no | energy | yes | no |
| `electricity` | primary | no | — | — | **yes** | energy | **yes** | **yes** |
| `heat_lt60` | intermediate | **yes** | **1** | `<60C` | no | energy | no | no |
| `heat_60_100` | intermediate | **yes** | **2** | `60-100C` | no | energy | no | no |
| `heat_100_150` | intermediate | **yes** | **3** | `100-150C` | no | energy | no | no |
| `heat_150_400` | intermediate | **yes** | **4** | `150-400C` | no | energy | no | no |
| `motive_power` | intermediate | no | — | — | no | energy | no | no |
| `cooling_0_15` | intermediate | **yes** (cooling) | 2 | `0-15C` | no | energy | no | no |
| `reject_flue_clean` | intermediate | no | — | — | no | energy | no | no |
| `reject_flue_solid_liquid` | intermediate | no | — | — | no | energy | no | no |
| `reject_engine_exhaust` | intermediate | no | — | — | no | energy | no | no |
| `reject_dryer_exhaust` | intermediate | no | — | — | no | energy | no | no |
| `reject_chiller_condenser` | intermediate | no | — | — | no | energy | no | no |
| `co2_fuel_fossil` | **emission** | no | — | — | no | **mass** | no | no |
| `co2_fuel_biogenic` | **emission** | no | — | — | no | **mass** | no | no |

Nineteen carriers: four of them graded heat, five of them reject heat by source class, and two
of them emissions.

**Reject heat is carried by where it comes from, not by its temperature.** A gas boiler's clean
flue, a CHP's exhaust after its own heat recovery, a spray dryer's humid and dusty exhaust and a
chiller's condenser heat differ in how hard they are to recover, so each lands on its own
carrier and each is reached only by a unit built to recover that class
([notes/23](../notes/23_reject_heat_recovery_plan.md) section 10). The five are not gradeable,
so C10 (the grade cascade) declares no $h$ on them and nothing reaches a duty from them without
a recovery unit. All five may be disposed of, which is what happens to the heat no unit draws.

**`electricity` is the only carrier that crosses the boundary both ways here**, and that is
what D16 (the site boundary is a property of the carrier) records. `may_import` and
`may_export` decide which $m_{c,k,t}$ and $x_{c,k,t}$ variables A6 (the problem builder)
declares at all, so this premise's export variable exists because the column says it may and
the connection carries the carrier, not because §5.2 happened to leave the variable free; that
it stays at zero is a result (§8.6).
The thirteen `intermediate` and `emission` rows are false on both, which is V32 (c) (an emission
or intermediate carrier never crosses the site boundary). **No `product` carrier appears at
this site**, so the D16 case that the cement works exercises — an internal product with
`may_export` false and therefore no duty — has no instance here.

**The emission carriers are thin here, and that is the contrast with cement.** This dairy
burns natural gas and, later, hydrogen. Gas carries `biogenic_fraction` 0 so A6 derives a
`co2_fuel_fossil` coefficient and nothing else; hydrogen carries a zero factor so it derives
neither. There is **no `co2_process` carrier at all**, because no process here has a mass
denominator (§1.3) — where the cement works books 446.25 kt of calcination CO₂ that no fuel
switch can touch, this site's entire footprint is combustion and disappears when the fuel
does.

**`solid_biomass` is not a zero-factor fuel, and saying so is the point.** It carries
`biogenic_fraction` **1** and an `emission_factor_source` naming the `scenario_parameters`
series that holds the factor itself; that series is **97.22 kt/PJ gross** in every period
(§6.3). So A6 (the problem builder) derives a fossil coefficient against
97.22 × (1 − 1) = 0.0 and a biogenic one against 97.22 × 1 = **97.22 kt/PJ**. Biogenic CO₂ is
part of what this site would emit, and it is derived, balanced and reported as a quantity; what
makes it cost nothing is that `co2_fuel_biogenic` is `zero_rated` at the carrier, not that the
fuel has no carbon in it. `co2_fuel_biogenic` is therefore **live whenever a biomass unit
runs**, which is no period of this premise's pathway, because the biomass boiler is never built
(§8.3) and `chp_biomass_st` is screened out before the LP; and the coefficients that
would make it non-zero are stated below all the same.

**Grades are carriers, not an attribute of one** (§3.4). `heat_60_100` and `heat_100_150` are
two rows with different `grade_rank`, which is what lets C8 (carrier balance) balance them
independently and C10 order them, with no special case in either. Four bands rather than the
two of note 17's sketch, because a dairy's 80 °C hot water and its 120 °C evaporator duty must
land in **different** bands or C10's filter cannot tell them apart and the heat pump becomes
eligible for both.

> **The band set is the example's own.** §3.4 declares `grade_rank` and `grade_label` fields
> but no canonical list of bands, and nothing in the reference data holds one — `T17` (give
> every process a duty family and a heat grade) owns it. The four bands here are chosen to make
> the dairy's duties separable; a different set would change which units are eligible for
> which duty. §13 records it.

**`carrier_kind` is load-bearing for emissions** (§3.4, §7): fuel CO₂ attaches only to units
consuming a `primary` carrier. Every heat carrier here is `intermediate`, so a unit drawing
heat adds nothing — the fuel was already charged upstream. Getting this wrong double-counts
every boiler in the stock.

**`motive_power` and `cooling_0_15` are carriers, and they have to be.** The `MOT` (motors) duty's
carrier cannot be `electricity`, because C8 would then have the motor unit consuming and
producing the same carrier and the node would be circular; the same holds for a `REF`
(refrigeration) duty. A duty is a *service*. The refrigeration here is chilled water, so it
sits in §3.4's `cooling_0_15` band; the centre has no freezer store and so no sub-zero duty,
which is why the chiller keeps its COP of 3.00. This is forced by C8's algebra and is recorded in
§13 as an open point, because §3.4 does not say it.

**Units (§3.5).** Capacity in PJ/yr of the unit's primary output, except PV and storage in MW.

| `unit_id` | `unit_class` | `duty_family` | **fuel** | `grade_out` | `grade_in_max` | `capex` | `fixed_opex` | `L` | `α` |
|---|---|---|---|---|---|---|---|---|---|
| `boiler_lt_gas` | converter | `LTH` | **natural_gas** | **4** | — | 4.5 £m/(PJ/yr) | 0.18 | 20 | 0.85 |
| `boiler_lt_hydrogen` | converter | `LTH` | **hydrogen** | 4 | — | 4.7 | 0.19 | 20 | 0.85 |
| `boiler_lt_biomass` | converter | `LTH` | **solid_biomass** | 4 | — | 7.9 | 0.41 | 20 | 0.82 |
| `boiler_lt_lpg` | converter | `LTH` | **lpg** | 3 | — | 4.6 | 0.18 | 20 | 0.85 |
| `boiler_lt_coal` | converter | `LTH` | **coal** | 3 | — | 6.8 | 0.37 | 20 | 0.82 |
| `resistance_heater_lt` | converter | `LTH` | **electricity** | **4** | — | 2.8 | 0.09 | 20 | 0.85 |
| `heat_pump_lt_air` | converter | `LTH` | **electricity** | **2** | — | 16.0 | 0.32 | 20 | 0.85 |
| `heat_pump_lt_reject` | converter | `LTH` | **electricity** | **2** | **1** | 18.0 | 0.36 | 20 | 0.85 |
| `heat_pump_ht` | converter | `STM` | **electricity** | **3** | **2** | 26.0 | 0.52 | 20 | 0.85 |
| `chp_gas_turbine` | **generator** | `STM` | **natural_gas** | **4** | — | 38.0 | 1.20 | 25 | 0.85 |
| `chp_hydrogen_ccgt` | **generator** | `STM` | **hydrogen** | **4** | — | 42.0 | 1.30 | 25 | 0.85 |
| `chp_biomass_st` | generator | `STM` | solid_biomass | 4 | — | 61.0 | 2.10 | 25 | 0.82 |
| `dryer_direct_gas` | converter | `DRY` | **natural_gas** | **4** | — | 5.0 | 0.21 | 20 | 0.85 |
| `dryer_direct_hydrogen` | converter | `DRY` | **hydrogen** | 4 | — | 5.2 | 0.21 | 20 | 0.85 |
| `dryer_electric` | converter | `DRY` | **electricity** | **4** | — | 6.8 | 0.24 | 20 | 0.85 |
| `chiller_electric` | converter | `REF` | **electricity** | **2** | — | 9.0 | 0.22 | 20 | 0.90 |
| `motor_elec` | converter | `MOT` | **electricity** | — | — | 3.2 | 0.35 | 20 | 0.95 |
| `economiser_flue_condensing` | converter | `LTH` | — | **1** | — | 14.4867 | 0.32193 | 20 | 0.9823 |
| `recovery_engine_exhaust` | converter | `LTH` | — | **2** | — | 12.9808 | 0.86539 | 15 | 0.93 |
| `heat_pump_chiller_condenser` | converter | `LTH` | **electricity** | **2** | — | 21.3479 | 0.64053 | 25 | 0.9808 |
| `pv_rooftop` | **generator** | — | — | — | — | 0.62 £m/MW | 0.011 | 30 | **0.11** |
| `battery_2h` | **storage** | — | — | — | — | 0.58 £m/MW | 0.009 | 15 | 0.95 |

`γ` is 1.0 on every service unit; `pv_rooftop` and `battery_2h` carry 8,760 h × 3.6 × 10⁻⁶ =
**0.031536 PJ/yr per MW**, with PV's capacity factor in `α` = 0.11. `area_per_capacity` is set
on `pv_rooftop` alone, at **6,500 m²/MW**: both CHPs, the battery and every boiler leave it
unset and are outside C12.

**The three recovery units are the reference library's, costs included.** Each draws one reject
class and nothing else: the condensing economiser a clean-fuel boiler's flue, the exhaust
recovery unit a CHP's exhaust, and the condenser heat pump a chiller's condenser heat, lifted
at COP 3.95. Their costs are the sourced figures of `unit.csv`
([notes/23](../notes/23_reject_heat_recovery_plan.md) section 10.3), and each carries a
`min_viable_scale` in PJ/yr of the class it draws: 0.00169, 0.00194 and 0.01178. `A2` (duties
and candidate units) offers a recovery unit only where the premise's incumbents reject at least
that much at the base year, and here they reject 0.006618, 0.005226 and 0.086129 (§8.1), so all
three are offered. No unit draws the dryer's exhaust: the reference library has no costed one
yet, so that heat is always disposed of.

**D13 is visible in the first column, and it earns its place immediately.** What was one
`boiler_lt` with five carrier bindings is five units, and the five differ in ways a single row
could not hold: a biomass boiler costs £7.9m per PJ/yr against a gas boiler's £4.5m, runs at
0.82 availability against 0.85, and — the point that decided it — can be screened out by
`unit_eligibility` at a site with no fuel handling while the gas boiler stays. The dryer
splits the same way, and its hydrogen variant's £5.2m capex is now an attribute rather than a
footnote.

**`grade_out` is the whole mechanism in one column.** `heat_pump_lt_air` and
`heat_pump_lt_reject` top out at rank 2, which removes them from the 120 °C duty's candidate
set; `heat_pump_ht` reaches rank 3 and is admitted. The gas boiler and the CHP are rated to
rank 4 — they raise steam above 150 °C — but only the three dryers are offered for the rank-4
drying duty, because a boiler or CHP delivers hot water or steam and a spray dryer needs hot
air: §3.5.1 offers a duty to its own family, or to a family that takes the same medium. C10
states the temperature leg as physics rather than as a technology-to-process mapping, which is
what lets a new unit be added without editing a mapping table.

**Coefficients (§3.6), consumed negative, produced positive.** Per unit of the unit's output.

| `unit_id` | `carrier_id` | `coefficient` | `role` | Authored |
|---|---|---|---|---|
| `boiler_lt_gas` | `heat_100_150` | **+1.00000** | `primary_output` | declared |
| `boiler_lt_gas` | `natural_gas` | −1.13636 | `fuel_input` | declared *(η 0.88)* |
| `boiler_lt_gas` | `reject_flue_clean` | **+0.05682** | `reject` | declared: the condensing increment, 0.05 of the fuel |
| `boiler_lt_gas` | `co2_fuel_fossil` | **+63.74980** | `emission` | **derived** — 1.13636 × 56.1 |
| `boiler_lt_hydrogen` | `heat_100_150` | +1.00000 | `primary_output` | declared |
| `boiler_lt_hydrogen` | `hydrogen` | −1.11111 | `fuel_input` | declared *(η 0.90)* |
| `boiler_lt_hydrogen` | `reject_flue_clean` | +0.04200 | `reject` | declared |
| `boiler_lt_hydrogen` | `co2_fuel_fossil` | **+0.00000** | `emission` | **derived** — 1.11111 × 0.0 |
| `boiler_lt_biomass` | `heat_100_150` | +1.00000 | `primary_output` | declared |
| `boiler_lt_biomass` | `solid_biomass` | −1.12360 | `fuel_input` | declared *(η 0.89)* |
| `boiler_lt_biomass` | `reject_flue_solid_liquid` | +0.04494 | `reject` | declared |
| `boiler_lt_biomass` | `co2_fuel_fossil` | **+0.00000** | `emission` | **derived**: 1.12360 × 97.22 × (1 − 1) |
| `boiler_lt_biomass` | `co2_fuel_biogenic` | **+109.23639** | `emission` | **derived**: 1.12360 × 97.22 × 1 |
| `resistance_heater_lt` | `heat_100_150` | +1.00000 | `primary_output` | declared |
| `resistance_heater_lt` | `electricity` | −1.02041 | `fuel_input` | declared *(η 0.98)* |
| `heat_pump_lt_air` | `heat_60_100` | +1.00000 | `primary_output` | declared |
| `heat_pump_lt_air` | `electricity` | −0.35710 | `fuel_input` | declared *(COP 2.80)* |
| `heat_pump_lt_reject` | `heat_60_100` | +1.00000 | `primary_output` | declared |
| `heat_pump_lt_reject` | `electricity` | −0.31250 | `fuel_input` | declared *(COP 3.20)* |
| `heat_pump_lt_reject` | `heat_lt60` | **−0.68750** | `aux_input` | declared — `intermediate` |
| `heat_pump_ht` | `heat_100_150` | +1.00000 | `primary_output` | declared |
| `heat_pump_ht` | `electricity` | −0.47620 | `fuel_input` | declared *(COP 2.10)* |
| `heat_pump_ht` | `heat_60_100` | **−0.52380** | `aux_input` | declared |
| `chp_gas_turbine` | `heat_100_150` | **+1.00000** | `primary_output` | declared |
| `chp_gas_turbine` | `natural_gas` | −2.22220 | `fuel_input` | declared |
| `chp_gas_turbine` | `electricity` | **+0.77780** | `coproduct` | declared |
| `chp_gas_turbine` | `reject_engine_exhaust` | **+0.15555** | `reject` | declared: 0.07 of the fuel |
| `chp_gas_turbine` | `co2_fuel_fossil` | **+124.66542** | `emission` | **derived** — 2.22220 × 56.1 |
| `chp_hydrogen_ccgt` | `heat_100_150` | +1.00000 | `primary_output` | declared |
| `chp_hydrogen_ccgt` | `hydrogen` | −2.30000 | `fuel_input` | declared |
| `chp_hydrogen_ccgt` | `electricity` | **+0.95000** | `coproduct` | declared |
| `chp_hydrogen_ccgt` | `reject_engine_exhaust` | +0.08694 | `reject` | declared |
| `chp_biomass_st` | `heat_100_150` | +1.00000 | `primary_output` | declared |
| `chp_biomass_st` | `solid_biomass` | −1.37500 | `fuel_input` | declared *(η 0.727)* |
| `chp_biomass_st` | `electricity` | **+0.10000** | `coproduct` | declared |
| `chp_biomass_st` | `reject_flue_solid_liquid` | +0.05500 | `reject` | declared |
| `chp_biomass_st` | `co2_fuel_fossil` | **+0.00000** | `emission` | **derived** — 1.37500 × 97.22 × (1 − 1) |
| `chp_biomass_st` | `co2_fuel_biogenic` | **+133.67750** | `emission` | **derived** — 1.37500 × 97.22 × 1 |
| `dryer_direct_gas` | `heat_150_400` | **+1.00000** | `primary_output` | declared |
| `dryer_direct_gas` | `natural_gas` | −1.17650 | `fuel_input` | declared *(η 0.85)* |
| `dryer_direct_gas` | `reject_dryer_exhaust` | **+0.17650** | `reject` | declared: 0.20 of the fuel, capped at the unit's losses |
| `dryer_direct_gas` | `co2_fuel_fossil` | **+66.00165** | `emission` | **derived** — 1.17650 × 56.1 |
| `dryer_direct_hydrogen` | `heat_150_400` | +1.00000 | `primary_output` | declared |
| `dryer_direct_hydrogen` | `hydrogen` | −1.08696 | `fuel_input` | declared *(η 0.92)* |
| `dryer_direct_hydrogen` | `reject_dryer_exhaust` | +0.08696 | `reject` | declared, capped at the unit's losses |
| `dryer_direct_hydrogen` | `co2_fuel_fossil` | **+0.00000** | `emission` | **derived**: 1.08696 × 0.0 |
| `dryer_electric` | `heat_150_400` | +1.00000 | `primary_output` | declared |
| `dryer_electric` | `electricity` | −1.05260 | `fuel_input` | declared *(η 0.95)* |
| `dryer_electric` | `reject_dryer_exhaust` | **+0.05260** | `reject` | declared, capped at the unit's 0.05260 of losses at η 0.95 |
| `chiller_electric` | `cooling_0_15` | **+1.00000** | `primary_output` | declared |
| `chiller_electric` | `electricity` | −0.33330 | `fuel_input` | declared *(COP 3.00)* |
| `chiller_electric` | `reject_chiller_condenser` | **+1.33330** | `reject` | declared: the whole condenser heat |
| `motor_elec` | `motive_power` | **+1.00000** | `primary_output` | declared |
| `motor_elec` | `electricity` | −1.00000 | `fuel_input` | declared |
| `economiser_flue_condensing` | `heat_lt60` | +1.00000 | `primary_output` | declared |
| `economiser_flue_condensing` | `reject_flue_clean` | **−1.00000** | `aux_input` | declared |
| `recovery_engine_exhaust` | `heat_60_100` | +1.00000 | `primary_output` | declared |
| `recovery_engine_exhaust` | `reject_engine_exhaust` | **−1.00000** | `aux_input` | declared |
| `heat_pump_chiller_condenser` | `heat_60_100` | +1.00000 | `primary_output` | declared |
| `heat_pump_chiller_condenser` | `electricity` | −0.25320 | `fuel_input` | declared *(COP 3.95)* |
| `heat_pump_chiller_condenser` | `reject_chiller_condenser` | **−0.74680** | `aux_input` | declared |
| `pv_rooftop` | `electricity` | **+1.00000** | `primary_output` | declared |

Five things this table carries that a fuel-variant technology list could not:

- **A CHP's electricity is a positive coefficient on a second carrier**, not a property of the
  technology row. That single sign is what makes onsite generation, self-consumption and
  export expressible at all, and it is why §3.16 carries **no** electricity co-product field.
- **`role = reject` marks heat a unit gives off that could be recovered**, a *positive*
  coefficient on the carrier of its source class: the boiler's on `reject_flue_clean`, the CHPs'
  on `reject_engine_exhaust`, the dryers' on `reject_dryer_exhaust` and the chiller's whole
  condenser heat on `reject_chiller_condenser`. Without these rows every unit rejects zero and
  nothing is there to recover. A reject carrier is `intermediate`, so it carries no emissions:
  the fuel was charged to the unit that burnt it.
- **Emission rows are derived, not authored (D15).** Every `co2_fuel_fossil` row above is
  A6's work: the fuel coefficient times the scenario's factor times one minus the biogenic
  fraction, and every `co2_fuel_biogenic` row the same with the fraction itself. Authoring
  them by hand would have frozen one scenario's factors into the unit library, and the
  hydrogen rows show why that matters — they are zero **in this scenario**, on its low-carbon
  production assumption, and a different scenario changes them without touching a unit. The
  two biomass units are the mirror image: `biogenic_fraction` 1 sends the whole 97.22 kt/PJ
  down the biogenic leg and leaves the fossil one at zero, so a **gross** factor and a
  `zero_rated` carrier do the work that a zero factor would have done silently and wrongly.
- **`role = fuel_input` picks out one carrier where several are consumed.**
  `heat_pump_chiller_condenser` draws electricity *and* condenser heat, `heat_pump_lt_reject`
  electricity *and* heat below 60 °C, and `heat_pump_ht` electricity *and* rank-2 heat; in each
  the electricity is the fuel and the heat is an `aux_input` on an `intermediate` carrier. The
  economiser and the exhaust recovery unit burn nothing, so they carry an `aux_input` and no
  `fuel_input` at all. V27 (unit fuel identity) counts the role, not the inputs.
- **The COP is declared against the lift, not flat.** `heat_pump_lt_air` at 2.80,
  `heat_pump_lt_reject` at 3.20, `heat_pump_chiller_condenser` at 3.95 and `heat_pump_ht` at
  2.10 are four numbers for four jobs.
  Today `IFDSTMHP01` (steam) carries the same `33.333` coefficient as `IFDLTHELCHP01`
  (low-temperature hot water) — the situation the
  [architecture document](2026-08-28-carb3-site-energy-system-architecture.md) records as
  physically wrong, and data migration B4 is what fixes it. Without B4 the 120 °C competition
  in §8.3 is meaningless.

**`heat_pump_lt_air` is the one row that does not close on energy**, and §3.6 exempts it by
name: roughly two-thirds of its output is ambient heat, which does not flow between units and
never balances, so it carries `draws_ambient` and V2 skips its energy-closure leg. Every other
unit here puts out no more energy than it takes in, reject heat included; what is left over is
losses, which are no carrier.

**`unit_eligibility` (§3.5.1).** `min_duty` replaces COMIT's MILP binary and screens in `A2`,
outside the LP.

| `unit_id` | `process_id` | `min_duty` | `max_share` | `earliest_year` |
|---|---|---|---|---|
| `boiler_lt_gas` | `boiler_steam_hot_water` | — | — | — |
| `boiler_lt_hydrogen` | `boiler_steam_hot_water` | — | — | 2035 |
| `boiler_lt_biomass` | `boiler_steam_hot_water` | — | — | — |
| `boiler_lt_lpg` | `boiler_steam_hot_water` | — | — | — |
| `boiler_lt_coal` | `boiler_steam_hot_water` | — | **0.00** | — |
| `resistance_heater_lt` | `boiler_steam_hot_water` | — | — | — |
| `heat_pump_lt_air` | `boiler_steam_hot_water` | 0.01 PJ/yr | — | — |
| `heat_pump_lt_reject` | `boiler_steam_hot_water` | 0.01 PJ/yr | — | — |
| `heat_pump_ht` | `boiler_steam_hot_water` | 0.02 PJ/yr | — | 2030 |
| `chp_gas_turbine` | `boiler_steam_hot_water` | **0.03 PJ/yr** | — | — |
| `chp_hydrogen_ccgt` | `boiler_steam_hot_water` | **0.03 PJ/yr** | — | 2035 |
| `chp_biomass_st` | `boiler_steam_hot_water` | **0.25 PJ/yr** | — | — |
| `dryer_direct_gas` | `direct_heating` | — | — | — |
| `dryer_direct_hydrogen` | `direct_heating` | — | — | — |
| `dryer_electric` | `direct_heating` | — | — | — |
| `chiller_electric` | `refrigeration` | — | — | — |
| `motor_elec` | `machinery_motors`, `compressed_air`, `site_services` | — | — | — |
| `economiser_flue_condensing` | `site_services` | — | — | — |
| `recovery_engine_exhaust` | `boiler_steam_hot_water`, `site_services` | — | — | — |
| `heat_pump_chiller_condenser` | `boiler_steam_hot_water`, `refrigeration`, `site_services` | — | — | — |
| `pv_rooftop` | — | — | — | — |
| `battery_2h` | — | — | — | — |

The boiler-house units are offered at `site_services` as well, whose space-heat duty they serve
on the same terms as the hot-water duty. `dryer_direct_hydrogen` carries no `earliest_year`:
C9 (infrastructure availability) holds it, like every hydrogen unit, until hydrogen arrives in
2035 (§6.2). The recovery units carry no constraint column here; their screen is
`min_viable_scale` on the unit (above).

### 1.12 `activity_default_unit` (§3.16) — what the activity already has

| `process_id` | `duty_family` | `unit_id` | `default_share` | `sizing_basis` | `evidence_tier` | `provenance` |
|---|---|---|---|---|---|---|
| `boiler_steam_hot_water` | `LTH` | `boiler_lt_gas` | **1.00** | duty_annual | derived | sector heat-demand study |
| `site_services` | `SPC` | `boiler_lt_gas` | **1.00** | duty_annual | assumed | — |
| `boiler_steam_hot_water` | `STM` | **`chp_gas_turbine`** | **0.60** | duty_annual | **`sector_statistic`** | **DUKES Table 7 / CHPQA register** |
| `boiler_steam_hot_water` | `STM` | `boiler_lt_gas` | **0.40** | duty_annual | derived | residual |
| `direct_heating` | `DRY` | `dryer_direct_gas` | 1.00 | duty_annual | derived | sector heat-demand study |
| `refrigeration` | `REF` | `chiller_electric` | 1.00 | duty_annual | assumed | — |
| `machinery_motors` | `MOT` | `motor_elec` | 1.00 | duty_annual | assumed | — |
| `compressed_air` | `MOT` | `motor_elec` | 1.00 | duty_annual | assumed | — |
| `site_services` | `MOT` | `motor_elec` | 1.00 | duty_annual | assumed | — |

Shares sum to 1.00 ± 0.015 per `(activity, set, process, duty_family)` as §3.16 requires, and
every row has a `unit_eligibility` entry, which §3.16 makes a precondition — the default
cannot assert plant the model would refuse to build, or `A4` back-solves a baseline the
optimiser cannot reproduce.

**This entity sizes the boiler house, and it is the only source of plant where the site is
silent.** §1.5.1 names the CHP and the boiler but not their split, and `A4` cannot infer one
from metered heat and electricity — the same heat is equally consistent with a boiler. The
0.60 / 0.40 here is that split. For the four processes the audit leaves unnamed, this table
is the plant itself, and for a dairy whose audit named nothing it would be the only thing
telling a site with a 2.5 MWe CHP from one without; the base year would then have no
electricity co-product at all.
`MF-13` (default installed-unit table) is a Must for exactly this reason: milestone M4 has to
show an **existing** CHP, not only a new one.

`evidence_tier` is non-nullable, and `sector_statistic` is reserved for figures traceable to
DUKES Table 7 or the CHPQA register (`T18`). The 0.60 share is one of those; the 0.40 residual
is `derived` and says so.

---

## 2. `A1` — ingest and validate

Ten checks, all passing.

| # | Check | Result |
|---|---|---|
| 1 | `nation` is England — in scope under `D8` (Great Britain scope) | pass |
| 2 | `carb3_activity` is one of the 55 Factory-class activities (`D1`) | pass |
| 3 | Base-year energy sums to 0.36000 PJ/yr > 0 | pass — not `no_energy` |
| 4 | No duplicate `(premise_id, carrier_id, connection_id, data_year)` | pass — not `duplicate_year_row` |
| 5 | **No `premise_throughput` row is required** — no mass-denominated process (§1.3) | pass — not `missing_throughput` |
| 6 | `commissioned_year` 2011, 2016, 2019 ≤ `data_year` 2024; no `capacity_share` is given, so the sum rule is vacuous | pass — not `vintage_in_future` |
| 7 | `construction_year_band` resolves to 1965 ≤ `data_year`; `last_refurbishment_year` 2019 between them | pass |
| 8 | `premise_process_detail` intervals per `(premise, process)` are disjoint, and all six are valid at 2024 | pass — not `process_intervals_overlap` / `no_process_valid_in_base_year` |
| 9 | `premise_measured_emissions` has rows but **none at the base year** | **reported `emissions_year_unmatched`** — never a rejection (§3.1.1) |
| 10 | Profile statistics reconcile with energy at 2024, within 5% | pass — not `profile_energy_inconsistent` |

Two things are **reported rather than failed**:

- `emissions_year_unmatched` (check 9), so §7.6's reconciliation is skipped and said to be
  skipped.
- Only an `annual` weekly profile was supplied where `refrigeration` declares
  `summer_weighted` seasonality (§1.9), so the annual peak cannot be attributed to the right
  process when the mix changes.

Carrier coverage is **complete** — all five main vectors stated (§1.2) — which is the contrast
with the cement works.

The premise is assigned to the nearest of the nine in-scope GB clusters, `mersey`.
**Accepted.**

---

## 3. `A2` — duties and candidate units

### 3.1 The process set

`premise_process_detail` has rows, so `D10` tier 1 applies and the register's default set is
not consulted — although here the two coincide:

```
process_evidence_tier = "site_known"
process set, as at the base year 2024 =
    { boiler_steam_hot_water, direct_heating, refrigeration,
      machinery_motors, compressed_air, site_services }
```

`V11` (process sets resolve to exactly one tier per premise) passes: tier 1 resolved, and
neither the named-set tier nor the activity-default tier was consulted. That the two agree at
this premise is a fact about the dairy, not a shortcut — §1.5's rows are what the model read.

### 3.2 `process_duty` (§3.9) — what the premise must produce

Duties are **useful energy at a carrier and a grade**, not fuel. Two steps get there, and
§3.3.1 supplies the first — the step that had no source until it was promoted to an entity.

**Step one: the published process shares.**
[`activity_process_energy_share.csv`](../notes/data/activity_process_energy_share.csv)
gives `Food Processing Centre` these, all `engineering` tier at medium confidence, each column
summing to 1.00 down the processes:

| `vector` | `process_id` | `energy_share` | Premise PJ/yr |
|---|---|---|---|
| `gas` | `boiler_steam_hot_water` | **0.62** | **0.186000** |
| `gas` | `direct_heating` | **0.31** | **0.093000** |
| `gas` | `site_services` | **0.07** | **0.021000** |
| `electricity` | `machinery_motors` | **0.45** | **0.038759** |
| `electricity` | `refrigeration` | **0.25** | **0.021533** |
| `electricity` | `site_services` | **0.20** | **0.017226** |
| `electricity` | `compressed_air` | **0.10** | **0.008613** |
| `oil` | `boiler_steam_hot_water` | 0.85 | 0.000000 |
| `oil` | `site_services` | 0.15 | 0.000000 |

Unlike the cement works, **every one of this activity's six register processes carries a
row**, so no coverage gap distorts the split and no renormalisation is needed. The oil rows
apply to an explicit zero (§1.2).

**The electricity column is applied to consumption, not to the meter, and that is the trap.**
The site's metered 0.060000 PJ is a *net import*; the CHP's output sits behind it. §5.1
reconstructs consumption as 0.060000 + 0.026130 = **0.086130 PJ**, and the shares above are
taken on that. Applying them to the meter would have sized the chiller and the motors 30%
small.

**Step two: the duty split within each process**, from §3.3, and the conversion to useful
energy through the incumbent units of §1.5.1 and §1.12 and their coefficients:

| `process_id` | `duty_family` | `carrier_id` | Grade | `duty_share` | Delivered PJ/yr | **Duty PJ/yr** |
|---|---|---|---|---|---|---|
| `boiler_steam_hot_water` | `LTH` — hot water and CIP, 80 °C | `heat_60_100` | **2** | 0.46180 | 0.085895 gas | **0.075587** |
| `boiler_steam_hot_water` | `STM` — evaporator, 120 °C | `heat_100_150` | **3** | 0.53820 | 0.100105 gas | **0.055992** |
| `direct_heating` | `DRY`: spray dryer air, 10.3 to 60 °C | `heat_lt60` | **1** | 0.261993 | 0.024365 gas | **0.020711** |
| `direct_heating` | `DRY`: spray dryer air, 60 to 100 °C | `heat_60_100` | **2** | 0.210859 | 0.019610 gas | **0.016668** |
| `direct_heating` | `DRY`: spray dryer air, 100 to 150 °C | `heat_100_150` | **3** | 0.263574 | 0.024512 gas | **0.020836** |
| `direct_heating` | `DRY`: spray dryer air, 150 to 200 °C | `heat_150_400` | **4** | 0.263574 | 0.024512 gas | **0.020836** |
| `site_services` | `SPC` — space heating | `heat_60_100` | **2** | 1.00000 | 0.021000 gas | **0.018480** |
| `refrigeration` | `REF` | `cooling_0_15` | **2** | 1.00000 | 0.021533 elec | **0.064598** |
| `machinery_motors`, `compressed_air`, `site_services` | `MOT` | `motive_power` | — | 1.00000 | 0.064598 elec | **0.064598** |

The conversions: LTH 0.085895 × 0.88 (boiler η); STM 0.100105 ÷ 1.787864, the incumbent mix
divisor of §1.12 — 0.60 × 2.22220 + 0.40 × 1.13636 — which is higher than the boiler's own
1.13636 because a CHP burns more gas per unit of heat and gets electricity back for it; DRY
0.093000 × 0.85 = 0.079050, split into band segments below; SPC 0.021000 × 0.88; REF
0.021533 × COP 3.00; MOT identity.

**The spray dryer is four duties, because its air is heated once through** (§3.4, the rule that
a stream heated once through is split at the band edges). It draws outside air at 10.3 °C, the
1991–2020 annual mean of §3.4, and heats it to 200 °C, so the rise crosses the edges at 60, 100
and 150 °C and each band takes the share of the 189.7 °C rise that lies in it: 49.7, 40, 50 and
50 °C. The four duties sum to 0.079050 PJ/yr and their gas to 0.093000 PJ/yr before rounding
(0.079051 and 0.092999 as rounded above). The
placement rule alone would have put all of it at rank 4, as an earlier draft of this table did.

**Every heat duty carries a `grade_rank`, and §3.3 makes it non-nullable wherever the carrier
is gradeable.** The rule covers cooling too, which is why `refrigeration` carries rank 2. A
heat duty with no grade is invisible to C10's cascade: it could be served by
any grade at all, including one far below what the process needs, and the LP would take the
cheapest. That is failure mode 6 of §10.5, it fails silently, and this premise is where it
would have bitten: a heat pump firing the 150–200 °C top of a spray dryer.

**Seven heat duties at four grades, and `site_services` sits at two vectors.** Its gas is a
space-heating duty at rank 2 and its electricity is motive power, which is the ordinary shape
for a process that is really a bundle of site overheads — and it is only expressible because
§3.3.1 is keyed on `(process, vector)` rather than on the process alone.

**The reference data has since moved on from this example at `site_services`**, and this
example keeps its own figures. On 2026-10-02 the reference duty profile split the bundle's
electricity three ways on the UK building-services survey (BEES): 0.860 electric service for
lighting, ICT and small power, 0.079 motive power for fans and 0.061 chilled-water cooling. It
also moved the space heating to `heat_lt60` at rank 1, because most factories heat the space
with direct gas warm air or radiant tubes, not a water circuit at 60–100 °C
([notes/20](../notes/20_reference_data_open_questions.md) items 72 and 73). `mvp-dairy` runs on
the reference data, so it carries the split.

### 3.3 The collapse: 84 rows across eleven sectors to eight units

`Food Processing Centre` reaches **30 of COMIT's 397 technology rows**, on the six `IFD`
process commodities. `IFDLTH` — Industry · Food and Drink · Low-Temperature Heat — is where
the collapse is visible, and **D13 changes what the demonstration is**. Its eight rows:

| COMIT `technology_code` | `technology_category` | Disposition |
|---|---|---|
| `IFDLTHNGA01` | Natural gas | **preserved** as `boiler_lt_gas` |
| `IFDLTHHDG01` | Hydrogen | **preserved** as `boiler_lt_hydrogen` |
| `IFDLTHLPG01` | Oil | **preserved** as `boiler_lt_lpg` |
| `IFDLTHHCO01` | Coal | **preserved** as `boiler_lt_coal` |
| `IFDLTHBIOS01` | Biomass | **preserved** as `boiler_lt_biomass` |
| `IFDLTHELC01` | Electricity | **preserved** as `resistance_heater_lt` |
| `IFDLTHELCHP01` | Heat pump | **preserved** as `heat_pump_lt` |
| `IFDLTHSTM01` | Steam | **dropped** — see below |

**Seven units from eight rows, and read that way it is not a collapse at all.** Under D13 fuel
is part of a unit's identity, so a gas boiler and a hydrogen boiler stay two units. Within one
sector there is almost nothing to collapse.

**The collapse is across sectors, and it is much larger than the within-sector one ever was.**
`IFDLTHNGA01` is the food and drink sector's low-temperature gas boiler; ten other sectors
carry their own, and every one of them is the same machine:

| Fuel | Rows across the eleven `*LTH` sectors | Units |
|---|---|---|
| Hydrogen | 13 | **1** |
| Biomass | 12 | **1** |
| Natural gas | 12 | **1** |
| Heat pump | 11 | **1** |
| Electricity | 9 | **1** |
| Coal | 8 | **1** |
| Oil | 8 | **1** |
| Steam | 6 | **0 — dropped** |
| `Standard_FF` | 5 | **1**, once the category is resolved |
| **Total** | **84** | **8** |

**84 rows to eight units, a factor of ten**, against the three-to-one the within-sector reading
gave. Sector specificity moves into `unit_eligibility` (§3.5.1), which is where it belongs: a
dairy and a paper mill are told which units they may build, not given their own copies of the
same boiler.

> **⚠ The MVP's exit gate is stated in the old terms and needs restating.** Milestone M4
> asserts that *"eight fuel-variant rows collapse to three units"*. Under D13 that is no longer
> true and no longer the interesting claim. The gate should assert the cross-sector collapse —
> **84 low-temperature-heat rows to eight units, of which this dairy reaches seven** — and the
> per-fuel attributes D13 buys: a biomass boiler at £7.9m per PJ/yr against a gas boiler's
> £4.5m, screened out independently by `unit_eligibility`. Recorded in §13.

**`IFDLTHSTM01` is dropped, with a reason.** COMIT's own description says it plainly: *"not an
actual technology, only transfers heat from CHP plants, therefore no cost/capacity"*. It exists
because COMIT has no carrier balance and needed a pseudo-technology to move CHP heat onto a
demand. **C8 and C10 replace it outright**: a CHP's heat is a positive coefficient on
`heat_100_150`, the balance carries it, and C10 lets it serve a duty at or below that grade.
Its two siblings, `IFDDRYSTM01` and `IFDOTHSTM01`, drop for the same reason, and so does
`IFD01`, which COMIT describes as a demand technology that only transforms energy services
into a final demand commodity.

**`heat_pump_lt` then splits into two units**, `heat_pump_lt_air` and `heat_pump_lt_reject`,
under data migration B4 (heat-pump COP by grade lift). One row becomes two model units because
the COP is declared against the lift rather than flat, and a heat pump drawing heat below
60 °C is a genuinely different machine from one drawing ambient air.

The rest of the `IFD` family, for completeness:

| Family | Rows | Disposition |
|---|---|---|
| `IFDLTH` | 8 | 7 units, 1 dropped (above) |
| `IFDDRY` | 8 | 5 per-fuel dryers, `dryer_electric`, `heat_pump_ht`; `IFDDRYSTM01` **dropped** |
| `IFDSTM` | 4 | all preserved — `chp_gas_turbine`, `chp_biomass_st`, `chp_hydrogen_ccgt`, and `IFDSTMHP01` as `heat_pump_ht` (the same unit `IFDDRYELCHP01` maps to) |
| `IFDREF` | 1 | preserved as `chiller_electric` |
| `IFDMOT` | 1 | preserved as `motor_elec` |
| `IFDOTH` | 7 | 6 per-fuel generic heaters; `IFDOTHSTM01` **dropped** |
| `IFD01` | 1 | **dropped** — a demand pseudo-technology, not plant |
| **Total** | **30** | **4 rows dropped**; the rest resolve to units shared across all sixteen sectors |

**CHP stops being invisible, and that is the headline D13 does not touch.** In COMIT the four
`IFDSTM` rows are the only place a CHP exists at a food and drink site, and a dairy's CHP
reaches the hot-water duty only through the `IFDLTHSTM01` pseudo-technology — a row with no
cost and no capacity. Here `chp_gas_turbine` is a `generator` unit with a real capex, a real
lifetime, a gas input and **two** positive outputs, and §1.12 asserts that this premise already
has one.

### 3.4 The candidate unit set, after eligibility and C10

This is where C10 (the grade cascade) does its work. §5.5 is explicit that the duty-side leg
is enforced by **eligibility at load** rather than as an LP row — a unit whose `grade_out` is
below the duty's grade is never in $U_q$, so the variable is never created — which is why
`V19` is a load-scope test.

| Unit | `grade_out` | `LTH` rank 2 | `STM` rank 3 | `DRY` ranks 1–4 (the four band segments) |
|---|---|---|---|---|
| `boiler_lt_gas`, `_hydrogen`, `_biomass` | 4 | **eligible** | **eligible** | **refused** — not offered: `DRY` takes its own family (§3.5.1) |
| `boiler_lt_lpg` | 3 | **eligible** | **eligible** | **refused**: not offered, `DRY` takes its own family |
| `boiler_lt_coal` | 3 | **screened** — `max_share` 0.00 at this site | screened | refused |
| `resistance_heater_lt` | 4 | **eligible** | **eligible** | **refused** — not offered: `DRY` takes its own family (§3.5.1) |
| `heat_pump_lt_air` | **2** | **eligible** | **refused** — 2 < 3 | **refused** |
| `heat_pump_lt_reject` | **2** | **eligible** | **refused** — 2 < 3 | **refused** |
| `heat_pump_ht` | 3 | **eligible** | **eligible** | **refused**: not offered, `DRY` takes its own family, and 3 < 4 at the top segment |
| `chp_gas_turbine` | 4 | **eligible** | **eligible** | **refused** — not offered: `DRY` takes its own family (§3.5.1) |
| `chp_hydrogen_ccgt` | 4 | eligible from 2035 | eligible from 2035 | **refused** |
| `chp_biomass_st` | 4 | **screened out** — `min_duty` 0.25 > 0.07559 | **screened out** | refused |
| `dryer_direct_gas` | 4 | not eligible — bound to `direct_heating` | not eligible | **eligible** at all four |
| `dryer_direct_hydrogen` | 4 | not eligible | not eligible | **eligible** at all four from 2035 |
| `dryer_electric` | 4 | not eligible | not eligible | **eligible** at all four |
| `heat_pump_chiller_condenser` | **2** | **eligible** | **refused** — 2 < 3 | **refused** |
| `recovery_engine_exhaust` | **2** | **eligible** | **refused** — 2 < 3 | **refused** |
| `economiser_flue_condensing` | **1** | **refused** — 1 < 2 | **refused** | **refused**: not offered, `DRY` takes its own family |

**Four units compete at the 120 °C duty** — a gas boiler, a CHP, a high-temperature heat pump
and an electric resistance heater — which is milestone M4's assertion, and it is the first
time in either model that a duty has a genuine choice of *device* rather than a choice of
*fuel*.

**The heat pumps are absent from the drying duties' candidate sets**, and not by a mapping table:
150 °C output cannot reach the 150–200 °C segment, so `grade_out` 3 < 4 removes them from it at
load, and below it the family does, since they make hot water and a spray dryer needs hot air.
That is M4's second assertion, and stating it as physics is what lets a new unit be added to the
library without editing anything. **This premise's library holds no dryer below grade 4**, so
the same two dryers contest all four segments and every figure from §4 on is what it was with
one drying duty. The reference library's `dryer_heat_pump` (grade 2) does reach the two lower
segments, which is what moves `mvp-dairy` ([notes/20](../notes/20_reference_data_open_questions.md)
item 71).

**The condensing economiser reaches no duty at this premise.** Its heat is below 60 °C, and the
only rank-1 duty here is the bottom segment of the spray dryer, which takes `DRY` units only.
The one way its heat could be used is through the balance, lifted by `heat_pump_lt_reject`, the
only unit that draws `heat_lt60`; §8.4 prices that chain and it never pays. The boiler's flue
heat is therefore disposed of, which is the honest answer for a site with no low-grade duty.

`chp_biomass_st` is screened out by `min_duty`, outside the LP, in `A2`. COMIT would have
introduced a binary per technology per site to express the same thing
(`R/fct_constraints_hydrogen.R:650`, `R/fct_decision_variables.R:597`); at stock scale that is
the tractability problem the design removes. The site is **reported** if its optimal size later
lands below a credible minimum.

> **D13 removed the question this paragraph used to ask.** An earlier draft had one
> `boiler_lt` carrying five primary-carrier input rows and had to assume that `A2` expanded it
> into one variable set per fuel — an expansion no section described. Under D13 the five are
> five units, the expansion is the data, and `unit_eligibility` can cap coal at this site
> without touching gas, which the shared row could not do.

---

## 4. `A3` — allocate premise energy onto carriers

`premise_energy` already names its carriers, so `A3` is close to an identity here: it maps each
row's `(carrier_id, vector)` onto a `carrier` row, checks that the vector agrees with
`carrier_kind` (§3.1.1), and hands on the base-year quantities.

| `carrier_id` | Base-year quantity | Source year | `year_evidence_tier` |
|---|---|---|---|
| `natural_gas` | 0.30000 PJ/yr | 2024 | `base_year` |
| `electricity` | 0.06000 PJ/yr | 2024 | `base_year` |
| `fuel_oil` | 0.00000 | 2024 | `base_year` |
| `coal` | 0.00000 | 2024 | `base_year` |
| `solid_biomass` | 0.00000 | 2024 | `base_year` |

**Every carrier reads at the base year**, so no substitution occurs and no output row carries
`year_evidence_tier = substituted`. The cement works is the opposite case, where 35.4% of the
site's energy is pinned from a 2023 reading. Both branches of §3.1.1's ladder are exercised
across the pair.

**`A3` does not allocate energy across processes**, and that is the live specification's change
from the COMIT-parity baseline, which did. Which unit burns what is decided by C8 (carrier
balance), not by a profile applied up front. At this premise it matters: the three gas
consumers — boiler, CHP and dryer — are all eligible for gas, and only the balance plus the
duty structure decides how 0.30 PJ splits between them.

---

## 5. `A4` — back-solve capacity, carrier mix and vintage

### 5.1 Capacity, utilisation, and the CHP the meter hides

§3.10's precedence rule applies to one process only. `direct_heating` names a unit and a
capacity, so `A4` back-solves **utilisation** there; everywhere else it back-solves capacity.

```
dryer duty                                              = 0.079050 PJ/yr
known_capacity (audit)                                  = 0.100000 PJ/yr
utilisation = duty / (capacity x gamma) = 0.079050 / 0.100000 = 0.790500
availability_factor alpha                               = 0.850000
```

Utilisation sits comfortably below the availability factor, so the dryer has headroom — a
credible reading for a plant whose campaign is set by milk intake. A dryer back-solving above
0.85 would have tripped `capacity_energy_inconsistent`.

For the other units, capacity follows from the duty and α:

| Unit | $z_{u,0}$ | α | $a_{u,0}$ |
|---|---|---|---|
| `boiler_lt_gas` | 0.116465 PJ — LTH 0.075587 + STM share 0.022397 + SPC 0.018480 | 0.85 | **0.137018 PJ/yr** |
| `chp_gas_turbine` | 0.033595 PJ | 0.85 | **0.039524 PJ/yr** |
| `dryer_direct_gas` | 0.079050 PJ | 0.85 | **0.100000 PJ/yr** (known) |
| `chiller_electric` | 0.064598 PJ | 0.90 | **0.071776 PJ/yr** |
| `motor_elec` | 0.064598 PJ | 0.95 | **0.067998 PJ/yr** |

One boiler serves three duties at two grades — LTH and SPC at rank 2, STM at rank 3 — through
three separate $z_{u,q,t}$ dispatches sharing one capacity under C2. With a single activity
variable it would have been credited in full against each.

**Site electricity consumption is reconstructed, not read.** The meter gives net import; the
CHP's co-product sits behind it:

```
CHP electricity  = 0.033595 x 0.77780                   = 0.026130 PJ/yr
metered import                                           = 0.060000 PJ/yr
site consumption = import + CHP output                   = 0.086130 PJ/yr
```

**30% of this dairy's electrical load is invisible to its meter.** Had the model read
0.060000 as consumption, the chiller and the motors would have been sized 30% small, the `REF`
and `MOT` duties understated throughout the horizon, and every later electrification decision
run on the wrong base. This is the argument for §3.16 in one number — and it is a problem only
a site with onsite generation has, so the cement works cannot show it.

**The gas side closes exactly:**

```
boiler, LTH    0.075587 / 0.88                          = 0.085895
boiler, STM    0.022397 / 0.88                          = 0.025451
boiler, SPC    0.018480 / 0.88                          = 0.021000
CHP            0.033595 x 2.22220                       = 0.074655
dryer          0.079050 / 0.85                          = 0.093000
                                                          --------
back-solved gas                                          = 0.300001
metered gas                                              = 0.300000
                                                          +0.0003%
```

**The residual is arithmetic rounding and nothing else**, because §3.3.1's shares are an
allocation of the meter rather than an independent estimate of it. An earlier draft of this
example asserted its own process split and carried a −1.11% gap; running on the published
shares removes it. What remains to be reconciled is §7.6's emissions check, and at this
premise that cannot run at all (§10.2).

### 5.2 The carrier mix (§4.1)

Tiers are tried in order and exactly one resolves:

| Tier | Test at this premise | Resolves? |
|---|---|---|
| 1 — `site_known` | `premise_process_unit` (§1.5.1) names the CHP and the boiler for `boiler_steam_hot_water`, but gives no `capacity_share`, so the split between them is not stated | **no** |
| 2 — `carrier_bounded` | `premise_energy` gives a site total for `natural_gas`, but **three units** at this premise consume it | **no** — not determined by division |
| 3 — `activity_default` | the activity-default mix applies, carried as an assumption | **yes** |

```
mix_evidence_tier = "activity_default"
```

**This is the tier that cement did not reach, and it matters.** At the cement works the kiln was
the only consumer of coal, gas and waste-derived fuel, so tier 2 determined the mix by
division. Here three units share `natural_gas` and division cannot separate them. §4.1's rule
is that where several units share a carrier at tier 2 the split is made by duty share and
**recorded as an assumption rather than presented as measured** — and at this premise even that
is unavailable, because the audit names the boiler-house plant but not its split, and the
split comes from §1.12. The gas split of §5.1 is therefore an assumption end to end, and every output row
says so.

`V23` (the mix resolves to exactly one tier, tiers are tried in order, and `mix_evidence_tier`
appears on every output row) passes on all three properties. A premise running on an assumed
mix is never mistaken on paper for one running on an observed one, which is the whole of `D10`.

### 5.3 Vintage (`D11`)

Scenario `central` runs 2025 to 2050 in five-year periods, so $t_0$ = 2025, $\Delta$ = 5, and
$N$ = 5. The stranding factor is $\xi$ = 1.0. Lifetimes convert to periods before use:
$\ell_{\text{chp}} = \lceil 25/5 \rceil = 5$ and $\ell_{\text{boiler}} = \lceil 20/5 \rceil = 4$
periods. Reading 25 as a period offset would give a 125-year asset.

Tiers resolve per unit:

| Unit | Tier | Age at 2025 | Why |
|---|---|---|---|
| `chp_gas_turbine` | `process_known` | point mass, 14 years | §1.6, cohort 1 at 2011 |
| `boiler_lt_gas` | `process_known` | point mass, 9 years | §1.6, cohort 2 at 2016 |
| `dryer_direct_gas` | `process_known` | point mass, 6 years | §1.6, cohort at 2019 |
| `chiller_electric`, `motor_elec` | `premise_bounded` | [0, 20] | No cohort row, so the 1965 band year applies; the bound is slack, so the window matches the default tier's — but the label records that the evidence was consulted |

Survival, standing capacity and the stranding charge for the three known cohorts:

| | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|
| **`chp_gas_turbine`** ($L$ 25, dies 2035, κ 38.0) | | | | | | |
| Survival η | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 |
| Standing $e_{u,t}$ (PJ/yr) | 0.039524 | 0.039524 | 0.039524 | 0 | 0 | 0 |
| Mean remaining life R̄ (yr) | 11 | 6 | 1 | 0 | 0 | 0 |
| Stranding rate κ·ξ·R̄/L (£m per PJ/yr) | 16.720 | 9.120 | 1.520 | 0 | 0 | 0 |
| Write-off if scrapped whole (£m) | **0.661** | **0.360** | **0.060** | 0 | 0 | 0 |
| **`boiler_lt_gas`** ($L$ 20, dies 2035, κ 4.5) | | | | | | |
| Survival η | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 |
| Standing $e_{u,t}$ (PJ/yr) | 0.137018 | 0.137018 | 0.137018 | 0 | 0 | 0 |
| Mean remaining life R̄ (yr) | 11 | 6 | 1 | 0 | 0 | 0 |
| Write-off if scrapped whole (£m) | **0.339** | **0.185** | **0.031** | 0 | 0 | 0 |
| **`dryer_direct_gas`** ($L$ 20, dies 2038, κ 5.0) | | | | | | |
| Survival η | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 |
| Standing $e_{u,t}$ (PJ/yr) | 0.100000 | 0.100000 | 0.100000 | 0 | 0 | 0 |
| Mean remaining life R̄ (yr) | 14 | 9 | 4 | 0 | 0 | 0 |
| Write-off if scrapped whole (£m) | **0.350** | **0.225** | **0.100** | 0 | 0 | 0 |

The CHP's 2025 write-off is 38.0 × 1.0 × 11 ÷ 25 = £16.720m per PJ/yr, times 0.039524 PJ/yr =
**£0.661m**. The same arithmetic gives the other rows. Standing capacity is the back-solved
$a_{u,0}$ of §5.1, so each incumbent runs at its availability factor exactly in the base year
and has no headroom to grow into.

**The write-offs here are small, and that is itself the result.** At the cement works the kiln
carried £119.5m of residual value at $t_0$ and the charge dominated the switching decision;
at a dairy the whole boiler house is worth under £1.1m and `D11` prices delay in fractions of
a million. The mechanism is the same and its weight is not, which is worth knowing before
assuming `D11` matters everywhere.

**The MVP implements the fallback tier only** (`MF-43`, C4 at the fallback tier only, which
reproduces COMIT's linear decay and is what `V1b` needs). Cohort vintage, the stranding charge
and the early-retirement variable are `MF-46`, a Should landing at milestone M6. At the
fallback tier all three units decay linearly from $t_0$ instead of standing whole to a known
death, which at this premise **softens** the 2040 cliff of §8.4 into a gradual replacement from
2030: a materially different pathway, on the same inputs.

---

## 6. `A5` — apply the scenario

### 6.1 Periods, rates and the calendar

```
scenario_id        central
t0                 2025        Δ = 5 years      periods t = 0 … 5  ⇒  2025 … 2050
discount rate r    3.5%        interest rate i  3.5%
stranding factor ξ 1.0
data_year offset   premise data_year 2024, t0 2025 ⇒ offset −1 year, recorded on every row
```

The offset is recorded rather than silently absorbed (§3.1.1). Stock data is mixed vintage, so
two premises may hold different `data_year` values while the model's periods are global;
stating the offset is what stops a carbon price at one period being applied to two different
calendar years without trace. This premise and the cement works happen to share a base year;
nothing in the design requires it.

### 6.2 `infrastructure_scenario` (§3.7), cluster `mersey`, `D7`

| `carrier` | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 | `unit_tariff` |
|---|---|---|---|---|---|---|---|
| `hydrogen` | false | false | **true** | true | true | true | — |
| `co2_transport` | false | false | false | false | false | false | — |
| `grid_headroom` | true | true | true | true | true | true | — |

**Hydrogen arrives here and never arrives at the cement works' cluster**, which is the cleanest
available illustration of `D7` (infrastructure exogenous): availability is a scenario input
owned and stated, not something the model decides, and two premises in the same run can face
opposite answers. C9 (infrastructure availability) removes every hydrogen-consuming unit from
this premise's problem before 2035 and admits them after.

**No `unit_tariff` is charged on hydrogen.** The reference table leaves the field blank on every
row, and the specification's §3.7 records that the slice does not read it, so the hydrogen price of §6.3 is the whole delivered
cost. **The scenario is the example's own.** The reference scenario `published_2026` never
brings hydrogen to `mersey` and prices no hydrogen at all; under it every hydrogen unit below
would be held out by C9 in every period.

CO₂ transport never arrives, and this site has nothing to capture: no process chemistry, and
a stack too small for a train.

### 6.3 `scenario_parameters` (§3.8)

Import prices, £m per PJ:

| `carrier_id` | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|
| `natural_gas` | 7.10 | 7.60 | 8.20 | 8.40 | 8.60 | 8.80 |
| `hydrogen` | — | — | **19.50** | **16.50** | **14.00** | **11.00** |
| `solid_biomass` | 15.00 | 15.80 | 16.60 | 17.40 | 18.20 | 19.00 |
| `lpg` | 12.00 | 12.50 | 13.00 | 13.40 | 13.80 | 14.20 |
| `coal` | 2.60 | 2.70 | 2.80 | 2.90 | 3.00 | 3.10 |
| `electricity` | 32.00 | 29.00 | 26.00 | 25.00 | 24.00 | 23.50 |

Export prices, £m per PJ, and the wedge `V21` (the export price is strictly below the import
price for every carrier and period) asserts at load:

| `carrier_id` | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|
| `electricity` | 19.00 | 17.00 | 15.00 | 14.50 | 14.00 | **13.50** |

Carbon price $\pi_t$, £/t: **90, 125, 165, 205, 240, 275**.

Emission factors, kt CO₂ per PJ:

| `carrier_id` | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 | Note |
|---|---|---|---|---|---|---|---|
| `natural_gas` | 56.1 | 56.1 | 56.1 | 56.1 | 56.1 | 56.1 | direct |
| `hydrogen` | — | — | **0.0** | 0.0 | 0.0 | 0.0 | direct; a low-carbon production standard is the scenario's assumption |
| `solid_biomass` | **97.22** | 97.22 | 97.22 | 97.22 | 97.22 | 97.22 | direct, **gross**; `biogenic_fraction` 1, so A6 derives fossil 0.0 and biogenic 97.22, and §7.3 zero-rates the carrier rather than the fuel |
| `lpg` | 63.1 | 63.1 | 63.1 | 63.1 | 63.1 | 63.1 | direct |
| `coal` | 94.6 | 94.6 | 94.6 | 94.6 | 94.6 | 94.6 | direct |
| `electricity` | 18.0 | 13.0 | 9.0 | 6.0 | 4.0 | 3.0 | **indirect** (`is_indirect` true) |

`reinforcement_cost` at 11 kV: **£0.65m per MW**.

The hydrogen series falls steeply, from £19.50 to £11.00 per PJ. That is a scenario choice and
it is stated as one: §8.4's choice of the hydrogen CHP for the 120 °C duty depends on it. Held
flat at £19.50, the hydrogen CHP would cost £25.63m per PJ of heat at 2040 and the
high-temperature heat pump would take the duty instead.

> **The objective charges direct carbon only.** §5.4's $Z^{\text{carbon}}_t$ does not say
> whether an `is_indirect` carrier's emissions enter the cost, and §7.4 settles only that
> indirect is excluded from the *comparison*. This example charges direct emissions and
> **reports** indirect ones, consistently with the cement example. §13 records it as an open
> point.

---

## 7. `A6` — the problem as built

### 7.1 Sets

```
T    = {0,1,2,3,4,5}                             six periods, Δ = 5
Q    = { LTH, STM, SPC, DRY×4, REF, MOT }        nine duties, all energy-denominated;
                                                 DRY is the four band segments of §3.2
U    = 12 units of §3.3, less chp_biomass_st (screened, §3.4), plus the B4 heat-pump split,
       plus the three recovery units of §1.11, plus pv_rooftop and battery_2h,
       less every hydrogen unit before 2035 (C9)
U⁰   = { boiler_lt@natural_gas, chp_gas_turbine, dryer_direct_gas@natural_gas,
         chiller_electric, motor_elec }                                       incumbents
Ugen = { chp_gas_turbine, chp_hydrogen_ccgt, pv_rooftop }                    generators
Uarea= { pv_rooftop }             area_per_capacity set; NEITHER CHP is in it, nor the battery
C    = nineteen carriers of §1.11, five of them gradeable (four heat, one cooling)
       and five of them reject classes
K    = { E-01, G-01 }
g(c) = 1 … 4 on the heat carriers; 2 on cooling_0_15, in the cooling family
```

### 7.2 Variables (§5.2), all continuous and non-negative

| Variable | Instances here | Note |
|---|---|---|
| $n_{u,t}$ new capacity | one per (unit, binding) pair per period | §3.4's expansion |
| $a_{u,t}$ available capacity | as above | |
| $z_{u,q,t}$ dispatch to a duty | declared over $u \in U_q$ only, per §3.4's eligibility table | **the duty index is what stops one unit being credited twice** |
| $z^{\circ}_{u,t}$ released to the balance | declared for every unit whose primary carrier balances; on the solved pathway non-zero for `pv_rooftop` alone | no heat is released, because no unit that draws heat from the balance (`heat_pump_ht`, `heat_pump_lt_reject`) is ever built |
| $h_{c \to c',t}$ cascade | declared only where both carriers are gradeable and $g(c') < g(c)$: **six pairs × 6 periods = 36** | 4→3, 4→2, 4→1, 3→2, 3→1, 2→1, all heat. None in the cooling family, which has one band here, and none across families |
| $e_{u,t}$, $r_{u,t}$ | 5 × 6 each | over $U^0$ only |
| $d_{c,t}$ disposal | one per `may_dispose` carrier per period | used on the four reject carriers that carry heat and on `co2_fuel_fossil`; declared and zero on `co2_fuel_biogenic` |
| $m_{c,k,t}$, $x_{c,k,t}$ | per carrier per connection per period | $m = x = 0$ where the connection does not carry $c$ |
| $w_{k,t}$ reinforcement | 2 × 6 | |

**`boiler_lt_gas` sits in three $U_q$ sets**, `LTH`, `STM` and `SPC`, and dispatches to each through its own $z_{u,q,t}$, sharing one
capacity through C2. With a single activity variable it would have been credited in full
against every duty it is eligible for. §5.2 states this as the reason the duty index exists,
and this premise is where it is visible: at 2025 the boiler serves 0.075587 PJ of `LTH`,
0.022397 PJ of `STM` and 0.018480 PJ of `SPC` out of one 0.137018 PJ/yr machine.

**The problem is a pure LP** (§5.2) and stays one: `min_duty` was applied in `A2`, not as a
binary, and `D11`'s survival function η and mean remaining life R̄ are parameters computed
before the build.

### 7.3 Constraints, instantiated

| # | Constraint | Instances here | Binds? |
|---|---|---|---|
| **C1** | Duty satisfaction | 9 duties × 6 periods = 54 | always, as an equality |
| **C2** | Activity ≤ available capacity × γ × α | one per (unit, binding) per period | on every incumbent but the dryer in the base year (§5.3), which is why none can grow into a duty |
| **C3** | Capacity transfer between periods | as above | — |
| **C4** | Incumbent ageing and early retirement (`D11`) | 5 × 6 = 30 | **the boiler house dies together at 2035**, and the gas boiler's idle part retires early that year (§8.4) |
| **C5** | No building in the start year | one per (unit, binding) | binds — $n_{u,0} = 0$ |
| **C6** | Unit stability | deferred (`MF-51`, Could) | — |
| **C7** | Known changes | none announced at this premise | — |
| **C8** | **Carrier balance** | 19 carriers × 6 = 114 | always, as equalities |
| **C9** | Infrastructure availability | hydrogen from 2035; no CO₂ transport | **binds before 2035** |
| **C10** | **Grade cascade, heat and cooling** | duty side by eligibility (§3.4); carrier side = the 36 $h$ declarations | **binds on the duty side** (§3.4, §8.3); the 36 $h$ carry nothing on the solved pathway |
| **C11** | Connection capacity | 2 × 6 = 12 | never on the solved pathway (§8.5, §8.6) |
| **C12** | Siting cap | 6 | **binds** — §8.2 |

### 7.4 Objective (§5.4)

$$\min \; Z = \sum_{t} \Big[\; \delta_t \big( Z^{\text{capex}}_t + Z^{\text{opex}}_t + Z^{\text{fuel}}_t + Z^{\text{carbon}}_t + Z^{\text{infra}}_t + Z^{\text{net}}_t - Z^{\text{exp}}_t \big) \;+\; d_t \, Z^{\text{strand}}_t \;\Big]$$

$Z^{\text{exp}}$ enters negative, so no implementation may assume a cost component is
non-negative; `V6` records the trap. At this premise the term is declared, priced and **zero
in every period**, because the site imports electricity throughout (§8.6), so neither worked
example gives the objective a negative component with a non-zero value. The trap is real all
the same: a premise whose generation exceeds its load would trip it.

Capex is annuitised over $L_u$ at $i$ = 3.5%. The annuity factors used below:

| $L$ | $(1+i)^L$ | Annuity $i/(1-(1+i)^{-L})$ |
|---|---|---|
| 15 | 1.67535 | 0.086825 |
| 20 | 1.98979 | **0.070361** |
| 25 | 2.36324 | **0.060674** |
| 30 | 2.80679 | **0.054371** |

Levelised comparisons in §8 are per PJ of heat **delivered to the duty**, at a capacity factor
of $1/\alpha$ = 1/0.85 = **1.17647** for the heat units.

---

## 8. `A7` — the solve

### 8.1 The base year, 2025, worked in full

C5 forbids building at $t_0$, so period 0 is the back-solved baseline running at the prices of
2025. Every number below is determined, not chosen.

**C8, every carrier node, period 0.** Nineteen nodes close to zero, which is what `V18`
asserts to 1e-6 and `V30` extends to the emission carriers.

| Carrier | Consumed by units | Produced by units | Import $m$ | **Disposal $d$** | Residual |
|---|---|---|---|---|---|
| `natural_gas` | boiler −0.132346, CHP −0.074655, dryer −0.093000 | — | +0.300001 | — | **0** |
| `electricity` | chiller −0.021533, motor −0.064598 | **CHP +0.026130** | +0.060000 | — | **0** |
| `hydrogen`, `lpg`, `coal`, `solid_biomass` | — | — | 0 | — | **0** |
| `heat_150_400` | — | dryer +0.079050, **all dispatched to the four `DRY` segments** ⇒ $z^{\circ}=0$ | — | — | **0** |
| `heat_100_150` | — | boiler +0.116465 and CHP +0.033595, **all dispatched** ⇒ $z^{\circ}=0$ | — | — | **0** |
| `heat_60_100`, `heat_lt60` | — | no unit active | — | — | **0** |
| **`reject_flue_clean`** | — | boiler **+0.006618** (0.116465 × 0.05682) | — | **−0.006618** | **0** |
| **`reject_engine_exhaust`** | — | CHP **+0.005226** (0.033595 × 0.15555) | — | **−0.005226** | **0** |
| **`reject_dryer_exhaust`** | — | dryer **+0.013952** (0.079050 × 0.17650) | — | **−0.013952** | **0** |
| **`reject_chiller_condenser`** | — | chiller **+0.086129** (0.064598 × 1.33330) | — | **−0.086129** | **0** |
| `reject_flue_solid_liquid` | — | no biomass unit runs | — | 0 | **0** |
| `motive_power` | — | motor +0.064598, dispatched | — | — | **0** |
| `cooling_0_15` | — | chiller +0.064598, dispatched | — | — | **0** |
| **`co2_fuel_fossil`** | — | boiler +7.42461, CHP +4.18814, dryer +5.21730 = **+16.83005 kt** | — | **−16.83005** | **0** |
| **`co2_fuel_biogenic`** | — | **none at 2025** — no biomass unit is built in this period | — | 0 | **0** |

Arithmetic: gas −0.132346 − 0.074655 − 0.093000 + 0.300001 = **0.000000**; electricity
−0.021533 − 0.064598 + 0.026130 + 0.060000 = **−0.000001**, rounding.

**Four things this node table settles.**

- **The CHP's electricity enters the balance even though its heat went to a duty.** §5.5 is
  explicit that a unit's inputs, co-products and reject heat scale with its *total* activity,
  while its primary output enters the balance only through $z^{\circ}$. So the CHP's
  0.033595 PJ of heat satisfies C1 and never appears at the `heat_100_150` node, and its
  0.026130 PJ of electricity appears at the electricity node regardless. That asymmetry is what
  makes a CHP representable, and COMIT has no way to express it.
- **The reject nodes close through disposal, not through an assumption.** Four units produce
  reject heat, each on its own class's carrier; reject heat scales with total activity, so it
  appears whatever the unit's output did. In 2025 nothing consumes any of it, because C5 (no
  building in the start year) lets no recovery unit be built yet. Under D15 and §5.2 each node closes through
  $d_{c,0}$, a declared variable on a `may_dispose` carrier, and the total is **reported**: this
  site throws away 0.111925 PJ, or 112 TJ, of heat a year, 77% of it the chillers' condenser
  heat. From 2030 the condenser heat pump and the exhaust recovery unit draw part of it (§8.4).
  An earlier draft of this example asserted an implicit vent the specification did not define.
- **Emissions are carriers now, and they balance like anything else.** The three combusting
  units produce `co2_fuel_fossil` through coefficients A6 derived (§1.11), and all of it is
  disposed of because this site has nothing to capture. `co2_fuel_biogenic` is declared and
  balances at zero **in this period, and in every period of §8.7's pathway**, because no
  biomass unit is ever built, not because the fuel is carbon-free. Build
  `boiler_lt_biomass` and the node carries 109.23639 kt per PJ of heat it makes (§1.11),
  disposed of and reported at a charge of £0.
- **The cascade variables are all zero.** All 36 $h_{c \to c',t}$ exist and none carries flow
  in the base year, because every unit's output goes straight to a duty. C10 is live and not
  yet doing work.

**The 2025 annual cost, undiscounted.**

| Term | Computation | £m |
|---|---|---|
| $Z^{\text{capex}}$ | C5: $n_{u,0}=0$ | **0.00000** |
| $Z^{\text{opex}}$ | boiler 0.137018 × 0.18 = 0.024663; CHP 0.039524 × 1.20 = 0.047429; dryer 0.100000 × 0.21 = 0.021000; chiller 0.071776 × 0.22 = 0.015791; motor 0.067998 × 0.35 = 0.023799 | **0.13268** |
| $Z^{\text{fuel}}$ | gas 0.300001 × 7.10 = 2.130007; electricity 0.060000 × 32.00 = 1.920000 | **4.05001** |
| $Z^{\text{carbon}}$ | **disposal, not fuel** — 16.83005 kt × £90/t × 10⁻³ | **1.51470** |
| $Z^{\text{infra}}$ | no infrastructure tariff before 2035 | **0.00000** |
| $Z^{\text{net}}$ | $w_{k,0}=0$ | **0.00000** |
| $Z^{\text{exp}}$ | generation 0.026130 < consumption 0.086130, so no surplus | **0.00000** |
| $Z^{\text{strand}}$ | nothing retired early | **0.00000** |
| **Total** | | **£5.69739m** |

Direct emissions: **16.83005 kt**, all natural gas, all vented. Indirect, reported and not
charged: 0.060000 × 18.0 = **1.08000 kt**, charged on the **import** under §7.8, which at this
premise is 30% less than the site's consumption because the CHP supplies the rest.

**Export is zero in the base year by construction, not by choice.** The meter shows a positive
import, so generation cannot exceed consumption: export needs import to reach zero first. Any
base year with a positive metered import has $x = 0$, in both worked examples and at every
premise the model will ever see. `V6` still asserts the term is present.

#### 8.1.1 What the CHP's electricity is worth, per §7.7

This is the premise the allocation layer exists for. The site wants an intensity for its CHP
electricity, and taking it from a second emission factor would count the same gas twice — the
trap D14 closes.

**Accounted layer (§7.1), which is the model's answer.** The CHP burns 0.074655 PJ of gas and
is charged 0.074655 × 56.1 = **4.18814 kt**. That figure is in $Z^{\text{carbon}}$ and in the
site total, and it does not move.

**Allocated layer (§7.7), on the avoided-boiler convention.** The CHP produced 0.033595 PJ of
heat and 0.026130 PJ of electricity. A reference boiler at η 0.88 would have burnt
0.033595 ÷ 0.88 = 0.038176 PJ of gas to make that heat, so:

| | PJ | Gas allocated | kt CO₂ | Intensity |
|---|---|---|---|---|
| Heat | 0.033595 | 0.038176 | **2.14167** | 63.75 kt/PJ, the reference boiler's |
| Electricity | 0.026130 | 0.074655 − 0.038176 = 0.036479 | **2.04647** | **78.32 kt/PJ** = **282 gCO₂e/kWh** |
| **Total** | | **0.074655** | **4.18814** | sums to the accounted figure |

**282 gCO₂e per kWh**, against a 2025 grid import at 18.0 kt/PJ = **65 gCO₂e/kWh**. On this
scenario's grid the dairy's CHP electricity is more than four times as carbon-intensive as the
grid it displaces, and by 2045 the grid is at 4.0 kt/PJ = 14 gCO₂e/kWh while the CHP is
unchanged. **That is the number that kills the gas CHP in §8.7**, and it is invisible unless
the allocation is done.

Three properties `V29` asserts, and the third is the one that matters:

- The allocation sums to 4.18814 kt exactly, by construction.
- The objective read the **accounted** layer, so changing convention from avoided-boiler to
  energy or exergy allocation moves the intensities and moves **no pathway**.
- The two layers are reported side by side and **never added**. A site reporting 4.18814 kt of
  accounted emissions plus 2.04647 kt of "CHP electricity emissions" would be double-counting
  its own gas, which is exactly the error §7.7 exists to prevent.

### 8.2 C12 and the PV decision

$$\sum_{u \in U^{\text{area}}} \mu_u\, a_{u,t} \;\le\; \sum_{k \in \mathcal{K}} A_k \qquad \Longrightarrow \qquad 6{,}500 \times a_{\text{pv},t} \;\le\; 12{,}000$$

so $a_{\text{pv},t} \le$ **1.846154 MW**. Area is summed across connections here, unlike
capacity in C11, because roof and land are one estate however many supplies serve them (§5.5);
at this dairy the whole 12,000 m² sits against `E-01`.

**The sum runs over area-bound units only, and both CHPs are outside it.** This is the premise
where that matters: a single site-wide area density applied to every generator would cap the
gas turbine and the hydrogen CCGT at the footprint of the PV array that fits on the same roof,
which is not a constraint either has. The gas turbine is a container in the yard.
`V12` (capacity bounds hold, including the siting cap, whose sum runs over area-bound units
only) asserts it.

At the cap, PV output is 1.846154 × 0.031536 × 0.11 = **0.006404 PJ/yr**, which is **7.28%** of
the dairy's 0.088000 PJ of consumption, four times the share the cement works' much larger
roof achieved, because the load is forty times smaller. The decision at 2030:

| | £m/yr |
|---|---|
| Displaced import: 0.006404 × 29.00 | **+0.185716** |
| Annuitised capex: 0.62 × 1.846154 × 0.054371 | −0.062234 |
| Fixed opex: 0.011 × 1.846154 | −0.020308 |
| **Net** | **+£0.103174m/yr** |

PV is built to the area cap from 2030, the earliest period C5 allows, and stays for its
30-year life. It is never curtailed: the site imports in every period, so every PJ it makes
displaces an import (§8.6).

**PV reduces energy but not peak.** Whether rooftop generation is coincident with the site's
maximum demand is what the Tier A coefficient ψ (onsite-generation self-consumption) answers,
and ψ is a `Could` feature gated on the G4 scale gate (`MF-36`, S0 archetype dispatch). Absent
it, C11 in §8.5 takes no credit for PV, which is the conservative reading.

**The battery is not built**, at any period. A standalone battery earns only through β, its
firm-capacity contribution to C11 (`V20` (d): a unit with `unit_class` = storage and no hybrid parent has
β set and ψ, χ, ε unset). C11's import leg never binds on the chosen pathway (§8.5), so β has
nothing to relieve, and the export leg never binds either. Reporting that is a result, not an
omission.

### 8.3 The 120 °C competition, 2035

This is milestone M4's assertion, and the reason the example exists. All four kinds of device
are priced per PJ of heat delivered to the `STM` duty, at the 2035 prices of §6.3: gas £8.20,
hydrogen £19.50, electricity £26.00, biomass £16.60, carbon £165/t. A standing unit is priced at
its avoidable cost (its capex is sunk); a new one at its full cost, capex annuitised.

| Unit | Capex, annuitised | Fixed opex | Fuel or electricity | Direct carbon | Electricity credit | Source heat | **Total £m/PJ** |
|---|---|---|---|---|---|---|---|
| `heat_pump_ht`, new | 26.0 × 0.070361 × 1.17647 = 2.152219 | 0.611765 | 0.47620 × 26.00 = 12.381200 | 0 | — | 0.52380 × 8.55689 = 4.482099 | **19.62728** |
| `boiler_lt_biomass`, new | 7.9 × 0.070361 × 1.21951 = 0.677868 | 0.500000 | 1.12360 × 16.60 = 18.651760 | **0 charged**: 1.12360 × 97.22 = **109.23639 kt/PJ** vented `zero_rated` | — | — | **19.82963** |
| **`chp_gas_turbine`, standing** | **0** (sunk) | 1.411764 | 2.22220 × 8.20 = 18.222040 | 2.22220 × 9.25650 = 20.569794 | −0.77780 × 26.00 = −20.222800 | — | **19.98080** |
| **`boiler_lt_gas`, standing** | **0** (sunk) | 0.211765 | 1.13636 × 8.20 = 9.318152 | 1.13636 × 9.25650 = 10.518716 | — | — | **20.04863** |
| `boiler_lt_gas`, new | 4.5 × 0.070361 × 1.17647 = 0.372499 | 0.211765 | 9.318152 | 10.518716 | — | — | **20.42113** |
| `boiler_lt_hydrogen`, new | 4.7 × 0.070361 × 1.17647 = 0.389055 | 0.223529 | 1.11111 × 19.50 = 21.666645 | 0 | — | — | **22.27923** |
| `chp_gas_turbine`, new | 38.0 × 0.060674 × 1.17647 = 2.712484 | 1.411764 | 18.222040 | 20.569794 | −20.222800 | — | **22.69328** |
| `chp_hydrogen_ccgt`, new | 42.0 × 0.060674 × 1.17647 = 2.998009 | 1.529411 | 2.30000 × 19.50 = 44.850000 | 0 | −0.95000 × 26.00 = −24.700000 | — | **24.67742** |
| `resistance_heater_lt`, new | 2.8 × 0.070361 × 1.17647 = 0.231778 | 0.105882 | 1.02041 × 26.00 = 26.530660 | 0 | — | — | **26.86832** |

The carbon conversion is §5.4's 10⁻³: 56.1 kt/PJ × £165/t × 10⁻³ = **£9.25650m per PJ of gas**.
The heat pump's source heat is priced at the marginal cost of rank-2 heat. At 2035 the condenser
heat pump built in 2030 (§8.4) is fully used, so the marginal unit is a new one, at 1.320618 +
0.653069 + 0.25320 × 26.00 = **£8.55689m/PJ**; the chillers' unused condenser heat would carry
0.026489 PJ more of it, 90% of the 0.029329 PJ the high-temperature heat pump would draw. The
CHPs' electricity credit is the displaced import price, because the site is a net importer at
2035. The biomass boiler's capex and fixed opex are divided by its own α, 0.82.

**On 2035's prices alone the high-temperature heat pump is cheapest, then the biomass boiler,
and the LP builds neither.** The standing CHP and gas boiler keep the duty until they die at
the end of 2035. The reason is the one judgement this hand method needs: **a unit built in 2035
is paid for in all four of its periods inside the horizon, so it has to win over those four,
not in the year it is built.** The LP's objective sums exactly that, so where one period's
ranking and the life test disagree, the example follows the life test. Per PJ/yr of the duty, in
present value over 2035 to 2050 (δ = 3.3128, 2.7893, 2.3485 and 1.9774):

| Path, £m per PJ | 2035 | 2040 | 2045 | 2050 | **Present value** |
|---|---|---|---|---|---|
| Standing plant, then `chp_hydrogen_ccgt` from 2040 (the LP's) | 20.00793 | 18.72742 | 13.92742 | 7.50242 | **166.06394** |
| `heat_pump_ht` from 2035, displaced by `chp_hydrogen_ccgt` in 2045 | 19.62728 | 19.01846 | 13.92742 + 2.76398 idle | 7.50242 + 2.76398 idle | **177.57151** |
| `boiler_lt_biomass` from 2035, displaced by `chp_hydrogen_ccgt` in 2040 | 19.82963 | 18.72742 + 1.17787 idle | 13.92742 + 1.17787 idle | 7.50242 + 1.17787 idle | **173.85407** |

The standing plant's 20.00793 is the duty's own blend, 0.60 × 19.98080 + 0.40 × 20.04863. The
heat pump would hold the duty through 2040, because its running cost then, £16.86624m/PJ, is
below the hydrogen CHP's full £18.72742m, but in 2045 the hydrogen CHP's full cost of
£13.92742m undercuts the heat pump's running £16.25741m, and the heat pump would stand idle
for two periods at its £2.76398m/PJ of annuity and fixed opex. The biomass boiler's running cost
is £20.05064m/PJ by 2040, above the hydrogen CHP's full cost, so it would stand idle for three.
Saving £0.38m or £0.18m per PJ in 2035 does not pay for that: over the 0.055992 PJ duty the heat
pump path costs **£0.644m** more in present value and the biomass path **£0.436m** more.
Keeping the heat pump running after 2045 instead of idling it is dearer still.

Four observations:

- **The standing plant wins on avoidable cost, not on merit against a new build.** A new gas
  turbine at £22.69m/PJ loses to the boiler; the one already standing wins because its capex is
  sunk. That distinction only exists because the audit named the CHP and dated it (§1.5.1),
  and it is the difference between a model that keeps working plant and one that rebuilds the
  country every period.
- **The high-temperature heat pump leads at 2035 because its source heat is recovered.** Priced
  on the air-source heat pump at 1.324442 + 0.376471 + 0.35710 × 26.00 = £10.98551m/PJ, as an
  earlier draft of this example did, it would cost £20.89939m/PJ and trail both standing units.
  Condenser heat at £8.55689m takes £1.27m/PJ off it. Recovered heat moves the 120 °C contest
  even though no recovery unit can serve that duty directly.
- **Biomass is cheaper than the plant it would replace at 2035 and is still not built.** Its
  factor is not zero: 97.22 kt/PJ gross, of which 109.23639 kt per PJ of delivered heat would
  be vented and reported. It is the carrier that is `zero_rated`, so the charge is £0 and the
  quantity is still on the books. The unit is in the candidate set, correctly priced, and
  rejected by the life test, which is a better answer than excluding it by hand.
- **Electric resistance is never close**, at £26.87m/PJ against £19.98m. It is in the set
  because M4 requires it to compete, and its job is to lose visibly.

### 8.4 Reject heat from 2030, and the 2040 rebuild

**2030: recovered heat takes the hot water.** 2030 is the first period C5 (no building in the
start year) lets anything be built, and the rank-2 duties, `LTH` 0.075587 and `SPC` 0.018480 PJ/yr, 0.094067 between them,
are where the standing gas boiler is weakest. At the 2030 prices (gas £7.60, electricity
£29.00, carbon £125/t), per PJ of rank-2 heat:

| Unit | Draws | £m/PJ | How much the source allows |
|---|---|---|---|
| `recovery_engine_exhaust`, new | the gas CHP's exhaust | 1.211890 + 0.930527 = **2.14242** | 0.005226 PJ/yr, all the CHP rejects |
| `heat_pump_chiller_condenser`, new | condenser heat and electricity | 1.320618 + 0.653069 + 0.25320 × 29.00 = **9.31649** | 0.086129 ÷ 0.74680 = 0.115330 PJ/yr |
| `heat_pump_lt_reject` on `economiser_flue_condensing`, new | the boiler's flue, then a lift | 1.489998 + 0.423529 + 0.31250 × 29.00 + 0.68750 × 1.36540 = **11.91474** | 0.006618 ÷ 0.68750 = 0.009626 PJ/yr, and only 0.001273 ÷ 0.68750 once the boiler stops making hot water |
| `heat_pump_lt_air`, new | ambient air and electricity | 1.324442 + 0.376471 + 0.35710 × 29.00 = **12.05681** | none |
| `boiler_lt_gas`, standing | gas | 0.211765 + 1.13636 × 7.60 + 1.13636 × 7.01250 = **16.81683** | its standing capacity |

The economiser's £1.36540m per PJ of `heat_lt60` is 1.037665 + 0.327731. The exhaust recovery
unit takes everything the CHP rejects, **0.005226 PJ/yr**, and the condenser heat pump the rest,
**0.088841 PJ/yr**, well inside what the chillers' condenser heat allows. Neither the
economiser chain nor the air-source heat pump is needed. Both new units pass the life test of
§8.3: the condenser heat pump stands from 2030 to 2050 and its running cost stays below every
rival's full cost in every period, and the exhaust recovery unit stands for its three periods,
to 2040. Capacity is output ÷ α: **0.090580** and **0.005619 PJ/yr**.

The standing boiler keeps only its 0.022397 PJ of the 120 °C duty, so it burns
0.025451 PJ of gas where it burnt 0.132346, and site gas falls from 0.300001 to **0.193106 PJ**.
Direct emissions fall from 16.83 to **10.83 kt** in 2030, five years before any plant dies. The
reject nodes at 2030, PJ/yr:

| Carrier | Produced | Drawn by a recovery unit | Disposed of |
|---|---|---|---|
| `reject_chiller_condenser` | chiller 0.086129 | condenser heat pump 0.088841 × 0.74680 = 0.066347 | **0.019782** |
| `reject_engine_exhaust` | gas CHP 0.005226 | exhaust recovery 0.005226 | **0** |
| `reject_flue_clean` | boiler 0.022397 × 0.05682 = 0.001273 | none | **0.001273** |
| `reject_dryer_exhaust` | dryer 0.013952 | none: no unit draws it | **0.013952** |

**One other new unit beats standing plant at 2030 and fails the life test: a new gas CHP on
the boiler's slice of the 120 °C duty.** It costs 2.712484 + 1.411764 + 2.22220 × 7.60 +
2.22220 × 7.01250 − 0.77780 × 29.00 = £14.03995m/PJ against the boiler's £16.81683m, but from
2040 its running cost is £26.18966m/PJ, above the hydrogen CHP's full £18.72742m, so it would
stand idle for three of its five periods at £4.12425m/PJ of annuity and fixed opex. It is not
built. The other 120 °C challengers lose at 2030 even on one period: `heat_pump_ht` costs
£21.45376m/PJ on condenser heat and a new biomass boiler £18.93075m.

**The boiler's idle capacity retires early in 2035, not in 2030.** From 2030 0.110669 PJ/yr of
the boiler stands idle. Retiring it in 2030 would write off 4.5 × 1.0 × 6 ÷ 20 = £1.35m per PJ/yr,
more than the £0.18m a year of fixed opex it would save before 2035; in 2035 the write-off is
4.5 × 1.0 × 1 ÷ 20 = £0.225m per PJ/yr, **£0.0249m** in all, against £0.0199m a year of fixed
opex for the five years of the 2035 period, so C4's early-retirement leg (incumbent ageing)
takes it then. This is the only
early retirement on the pathway.

**2040: the clean-sheet rebuild.** The boiler house dies at the end of 2035 (§5.3) and the dryer
at the end of 2038, so 2040 is a clean-sheet decision on the 120 °C duty and the dryer, with the
rank-2 duties already held by recovered heat. At the 2040 prices:

| Duty | Grade | Winner | £m/PJ | Runner-up |
|---|---|---|---|---|
| `LTH` 80 °C **and `SPC`** | 2 | **`heat_pump_chiller_condenser`**, standing, and **`recovery_engine_exhaust`**, standing | **6.98307** / **0.93053** avoidable | `heat_pump_lt_air`, new, 10.62841 |
| `STM`, 120 °C | 3 | **`chp_hydrogen_ccgt`** | **18.72742** | `boiler_lt_hydrogen` 18.94590 |
| `DRY`, all four segments, to 200 °C | 1–4 | **`dryer_direct_hydrogen`** | **18.61234** | `dryer_direct_gas` 24.07389 |

`heat_pump_chiller_condenser`, standing: 0.653069 + 0.25320 × 25.00 = **£6.98307m/PJ**.
`chp_hydrogen_ccgt`: 2.998009 + 1.529411 + 2.30000 × 16.50 = 37.950000 − 0.95000 × 25.00 =
23.750000 → **£18.72742m/PJ**.
`boiler_lt_hydrogen`: 0.389055 + 0.223529 + 1.11111 × 16.50 = 18.333315 → **£18.94590m/PJ**.
`dryer_direct_hydrogen`: 5.2 × 0.070361 × 1.17647 = 0.430443 + 0.247059 +
1.08696 × 16.50 = 17.934840 → **£18.61234m/PJ**.

The hydrogen CHP and the hydrogen dryer both pass the life test: their costs only fall as
hydrogen gets cheaper, to £13.92742m and £7.50242m per PJ for the CHP in 2045 and 2050. The
hydrogen CHP rejects less exhaust than the gas one, 0.055992 × 0.08694 = **0.004868 PJ/yr**,
and the exhaust recovery unit built in 2030 now draws that. The condenser heat pump covers the
rest of the rank-2 duty, 0.094067 − 0.004868 = **0.089199 PJ/yr**, 0.000358 more than its 2030
build can make, so **0.000365 PJ/yr** of it is added at the full £8.30369m/PJ. In 2045 the
exhaust recovery unit reaches the end of its 15-year life and is rebuilt at **0.005234 PJ/yr**,
its £2.14242m full cost still the cheapest rank-2 heat on the site. From 2040 the condenser
heat pump draws 0.089199 × 0.74680 = 0.066614 of the chillers' 0.086129 PJ, and 0.019515 is
disposed of; the hydrogen dryer's 0.079050 × 0.08696 = 0.006874 PJ of exhaust is disposed of
too.

**§7 makes the recovered heat emissions-free, and that is a real result rather than an
accounting trick.** The chillers' electricity is charged to the chillers and the CHP's fuel to
the CHP; the recovery units draw `intermediate` carriers and inherit nothing. This is precisely
why heat recovery abates, and it works only because §7's attribution rule is stated rather than
assumed. `V22` (c) asserts it.

**C10's carrier side carries nothing here, and that is a result.** Reject heat sits on carriers
that are not gradeable, so no $h$ moves it: it reaches a duty only through the recovery unit
built for its class, which is what gives each class's cost per PJ its meaning. And $h$'s
declaration set still guarantees that nothing climbs: there is no variable for heat to rise
from rank 1 to rank 2, so the economiser's heat could only reach the hot water through
`heat_pump_lt_reject`, paying electricity for the lift, at £10.66474m/PJ in 2040 against the
condenser heat pump's £8.30369m. **A cascade moves heat down for free; a heat pump moves it up
for a price.** Both are expressible and the model cannot confuse them.

**Why the hydrogen CHP takes the 120 °C duty and not the 80 °C one.** At 2040 the CHP costs
£18.73m/PJ and the standing condenser heat pump £6.98m/PJ, so the heat pumps keep the rank-2
duties outright. The CHP wins `STM` only because the heat pump serving rank 3 must buy its
source heat at rank 2, 0.52380 × 8.30369 = £4.35m/PJ of it, which pushes `heat_pump_ht` to
£19.02m/PJ. **The grade ladder is what separates the two duties**, and without it a single
flat-COP heat pump would have taken both, which is exactly the error the architecture document
records.

**Why no CHP reaches the spray dryer.** Not the grade: the CHP raises steam at rank 4. It is
not offered, because §3.5.1 offers a `DRY` duty to `DRY` units only: a CHP delivers steam or
hot water, and a spray dryer needs hot air. So the drying duties, all four band segments up to
200 °C, are contested only by the direct-fired dryers and an electric one. That is M4's second
assertion, at a different duty from the one it names.

### 8.5 C11 and the connection

C11 is written per connection and never summed across them:

$$P^{\text{peak}}_{k,t} \;\le\; \overline{P}^{\text{imp}}_{k} + w_{k,t} + \sum_{u} \beta_u\,a_{u,t}, \qquad \sum_c x_{c,k,t} \le \overline{P}^{\text{exp}}_k$$

Peak is rebuilt from the solved pathway by C11's method. **§5.6 defines only the peak factor $\lambda$ and the method is open** (`T23`, complete §5), so
this example uses mean flow over operating hours multiplied by the observed within-shift peak
factor of §1.8, and states that this **understates** the true peak because it applies no
diversity step and no seasonal correction.

| | 2025 | 2040, chosen pathway | **2040, all-electric counterfactual** |
|---|---|---|---|
| Site electricity consumption (PJ/yr) | 0.086130 | 0.108716 | 0.144876 |
| Onsite generation (PJ/yr) | CHP 0.026130 | CHP 0.053192 + PV 0.006404 | PV 0.006404 |
| Net import (PJ/yr) | **0.060000** | **0.049120** | **0.138472** |
| Mean over 7,200 h (MW) | 2.3148 | 1.8950 | 5.3423 |
| × within-shift peak factor 1.47 (MW) | **3.40** | **2.79** | **7.85** |
| `import_capacity` at `E-01` (MW) | 4.00 | 4.00 | 4.00 |
| Headroom (MW) | +0.60 | +1.21 | **−3.85** |

At 2025 the rebuilt peak of 3.40 MW matches the metered 3.4 MW exactly, which is `V16`'s
assertion (connection peak is rebuilt correctly from the solved pathway) at the base year.

The chosen pathway's consumption is the chiller's 0.021533 and the motors' 0.064598 plus the
condenser heat pump's 0.089199 × 0.25320 = 0.022585. The counterfactual puts the 120 °C duty
on `heat_pump_ht` instead of the hydrogen CHP: 0.055992 × 0.47620 = 0.026663 PJ of
electricity, and 0.055992 × 0.52380 = 0.029329 PJ of rank-2 source heat on top of the rank-2
duties. With no CHP exhaust left to recover, the condenser heat pump runs to the limit of the
condenser heat, 0.115330 PJ for 0.029202 PJ of electricity, and the air-source heat pump makes
the last 0.008066 PJ for 0.002880.

**The chosen pathway needs no reinforcement, and the all-electric one needs more than the
existing supply.** Had the model put the 120 °C duty on a heat pump as well, the dairy's peak
would have reached 7.85 MW against a 4 MW connection: a reinforcement of 3.85 MW at
£0.65m/MW = **£2.50m**, nearly doubling the supply. The hydrogen CHP is chosen on cost (§8.4)
and avoids that as a side effect, which is the kind of interaction a model with no electricity
balance cannot see at all. The recovered heat cuts the chosen pathway's import below the base
year's: the 2040 peak is 0.62 MW lower than 2025's.

The MVP **reports** the counterfactual rather than costing it: C11 with the reinforcement
variable is `MF-47` (a Should, landing at milestone M6), and the MVP collects
`import_capacity` without reading it. On the chosen pathway the import leg never binds, and
nor does the export leg (§8.6).

### 8.6 No surplus, so no export

The electricity export variable is declared at `E-01`, because `electricity.may_export` is true
and the connection carries the carrier (§1.11), and it is priced at £19.00 to £13.50 per PJ,
below the import price in every period (`V21`, the price wedge, §6.3). **It is zero in every period**, and the
2 MW `export_capacity`, 2 × 7,200 ÷ 277,778 = 0.051840 PJ/yr over the operating hours, is never
approached.

**Export needs a surplus, and this site never has one.** Its generation peaks at 2040 to 2050,
when the hydrogen CHP's 0.053192 PJ and PV's 0.006404 PJ meet 0.108716 PJ of consumption, and
the 0.049120 PJ gap is imported. The only way to a surplus would be a larger CHP, and the one
unit cheap enough to grow is the hydrogen CHP at 2050, when hydrogen reaches £11.00 per PJ:

| At 2050, per PJ of rank-2 heat | £m/PJ |
|---|---|
| `chp_hydrogen_ccgt`, new: 2.998009 + 1.529411 + 2.30000 × 11.00 = 25.300000 − 0.95000 × 23.50 = 22.325000 | 7.50242 |
| `heat_pump_chiller_condenser`, standing, **avoidable**: 0.653069 + 0.25320 × 23.50 = 5.950200 | **6.60327** |

The standing condenser heat pump is £0.90m/PJ cheaper, so the hydrogen CHP never grows into
the hot-water duties, and its electricity never exceeds the site's load. The heat pump's fixed
opex is in fact paid whether it runs or not, since C4's early retirement covers incumbents
only, so its true avoidable cost is £5.95020m and the margin wider still. Even a CHP that did
grow would export only past the point where the site stops importing, and each PJ of heat it
made there would earn 0.95000 × 13.50 rather than displace 0.95000 × 23.50: £17.00242m/PJ
against the heat pumps' £6.60m. The wedge `V21` asserts is what makes that loss certain.

**The export is not dropped from the model, only from the result.** $Z^{\text{exp}}$ is in the
objective at zero in every period (§7.4), and whether a premise exports is decided by its
generation and its prices, never by a switch. §11 records what the pathway without the reject
leg does at 2050, where the hydrogen CHP does grow, and stops exactly at zero import.

### 8.7 The pathway

| | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|
| `boiler_lt_gas` (PJ/yr) | 0.13702 | 0.13702 | **0.02635** | 0 | 0 | 0 |
| `chp_gas_turbine` (PJ/yr heat) | 0.03952 | 0.03952 | 0.03952 | 0 | 0 | 0 |
| `chp_hydrogen_ccgt` (PJ/yr heat) | 0 | 0 | 0 | **0.06587** | 0.06587 | 0.06587 |
| `heat_pump_chiller_condenser` (PJ/yr) | 0 | **0.09058** | 0.09058 | **0.09094** | 0.09094 | 0.09094 |
| `recovery_engine_exhaust` (PJ/yr) | 0 | **0.00562** | 0.00562 | 0.00562 | **0.00523** | 0.00523 |
| `dryer_direct_gas` (PJ/yr) | 0.10000 | 0.10000 | 0.10000 | 0 | 0 | 0 |
| `dryer_direct_hydrogen` (PJ/yr) | 0 | 0 | 0 | **0.09300** | 0.09300 | 0.09300 |
| `chiller_electric` (PJ/yr) | 0.07178 | 0.07178 | 0.07178 | 0.07178 | 0.07178 | 0.07178 |
| `motor_elec` (PJ/yr) | 0.06800 | 0.06800 | 0.06800 | 0.06800 | 0.06800 | 0.06800 |
| `pv_rooftop` (MW) | 0 | **1.84615** | 1.84615 | 1.84615 | 1.84615 | 1.84615 |
| `battery_2h` (MW) | 0 | 0 | 0 | 0 | 0 | 0 |
| Net import, electricity (PJ/yr) | 0.06000 | **0.07609** | 0.07609 | **0.04912** | 0.04912 | 0.04912 |
| **Export, electricity (PJ/yr)** | 0 | 0 | 0 | 0 | 0 | 0 |
| **Reject heat recovered** (PJ/yr) | 0 | **0.07157** | 0.07157 | **0.07148** | 0.07148 | 0.07148 |
| **Reject heat disposed of** (PJ/yr) | **0.11193** | **0.03501** | 0.03501 | **0.02639** | 0.02639 | 0.02639 |
| **$d_{\text{co2\_fuel\_fossil}}$** (kt/yr) | **16.83** | **10.83** | 10.83 | **0** | 0 | 0 |
| Indirect emissions (kt CO₂e/yr) | 1.08 | 0.99 | 0.68 | 0.29 | 0.20 | 0.15 |

Capacities are $a_{u,t}$, the duty divided by α. `heat_pump_lt_air`, `heat_pump_lt_reject`,
`heat_pump_ht` and `economiser_flue_condensing` are never built. Disposal by class, 2030 and
2035: condenser 0.019782, flue 0.001273, dryer 0.013952; from 2040: condenser 0.019515, dryer
0.006874. The 2040 exhaust recovery capacity, 0.00562, stands above the 0.004868 PJ it can
recover; it is the 2030 build, not resized.

Three features of this pathway:

- **The first change comes from recovered heat, not from dead plant.** In 2030 the condenser
  heat pump and the exhaust recovery unit take the hot water from the standing boiler, whose
  avoidable cost they undercut by more than £7m per PJ, and direct emissions fall by a third
  five years before the boiler house dies. The incumbents' sunk capex keeps them only where no
  recovered heat can reach, the 120 °C duty and the dryer, until C4 removes them at 2035 and
  2038. Under the MVP's fallback vintage tier (`MF-43`) the boiler house decays gradually from
  2030 instead, and the pathway is materially different: the same inputs, a different answer,
  decided by which tier of C4 is implemented.
- **Direct emissions go to zero at 2040 and the site is still burning something.** Hydrogen at
  a zero factor is a scenario assumption (§6.3), stated as one, and the indirect column is what
  keeps the grid's remaining carbon visible. This is the reporting `D10` and §7.4 exist to
  force.
- **Some reject heat is always thrown away, and the model says which.** The dryer's dusty
  exhaust has no recovery unit, the chillers make more condenser heat than the hot-water duties
  can use, and the boiler's condensing increment has no duty at all. Waste heat is only worth
  recovering when something needs it at the right grade and a unit exists to reach it, and the
  model reports the rest by source rather than assuming a recovery rate.

**The `carb3` run of `mvp-dairy` is not this example, and it agrees where the inputs agree.**
Both build `heat_pump_chiller_condenser` for the boiler-house hot water and `recovery_engine_exhaust`
for the CHP's exhaust in their first build period, neither builds `heat_pump_lt_reject` or
`heat_pump_lt_air`, and neither exports. The run differs because it reads the reference tables:
its base year is 2021, so its first build period is 2025; `published_2026` brings no hydrogen,
so `heat_pump_ht` takes the 120 °C duty and the gas dryer stays; the reference library's
`dryer_heat_pump` takes the dryer's two lower segments; its space heat sits at `heat_lt60`, where
`economiser_flue_condensing` can serve it; and its costs, lifetimes and availability factors are
`unit.csv`'s.

### 8.8 The relaxation ladder (§4.2)

This premise is feasible at every period, so no rung is used. The ladder's order is
**C6 → C7 → C4b → C12 → C10 → C11 → C9 → C1** (C4b is leg (b) of C4, forced ageing), and at this dairy three rungs are live:

- **C12 (siting cap) relaxes first.** An over-large PV array is an input-data problem about
  roof area, not a statement about the site's physics. Here the area is `measured`, so
  relaxing it would be relaxing a survey.
- **C10 (grade cascade) next, and relaxing it must be loud.** At this premise it would mean
  serving the 200 °C spray dryer with 150 °C heat, physically impossible, and the one
  relaxation that changes the answer's meaning rather than its cost. Report it; never silently
  absorb it.
- **C11 (connection capacity) last of the three**, because relaxing it asserts a network
  reinforcement nobody has costed. On this pathway neither leg comes near it; the import leg
  would be the one reached on the all-electric counterfactual of §8.5, at 7.85 MW against 4.

---

## 9. `A8` — the output rows and their evidence tiers

§8 of the specification is **not written** (`MF-20`, the §8 output schema; `T6` remainder), so
the shape below is the contract this fixture asserts and the schema must honour. One row per
premise per unit per carrier per period, plus the cost and network roll-ups.

An illustrative slice, the rank-2 hot-water duties (`LTH` and `SPC`) at 2040:

| `unit_id` | `carrier_id` | Flow PJ/yr | `mix_evidence_tier` | `vintage_evidence_tier` | `area_evidence_tier` |
|---|---|---|---|---|---|
| `chiller_electric` | `reject_chiller_condenser` | **+0.086129** *(reject)* | `activity_default` | `premise_bounded` | n/a |
| `heat_pump_chiller_condenser` | `electricity` | −0.022585 | `activity_default` | `premise_bounded` | n/a |
| `heat_pump_chiller_condenser` | `reject_chiller_condenser` | −0.066614 | `activity_default` | `premise_bounded` | n/a |
| `heat_pump_chiller_condenser` | `heat_60_100` | +0.089199 | `activity_default` | `premise_bounded` | n/a |
| `chp_hydrogen_ccgt` | `reject_engine_exhaust` | **+0.004868** *(reject)* | `activity_default` | `process_known` | n/a |
| `recovery_engine_exhaust` | `reject_engine_exhaust` | −0.004868 | `activity_default` | `premise_bounded` | n/a |
| `recovery_engine_exhaust` | `heat_60_100` | +0.004868 | `activity_default` | `premise_bounded` | n/a |
| `pv_rooftop` | `electricity` | +0.006404 | n/a | n/a | **`measured`** |

And the premise-level fields every row carries:

| Field | Value |
|---|---|
| `process_evidence_tier` | `site_known` (§3.1) |
| `mix_evidence_tier` | **`activity_default`** (§5.2) — the weakest of the three tiers |
| `year_evidence_tier` | **`base_year`** on every carrier (§4) |
| `area_evidence_tier` | **`measured`** (§1.4) — the strongest tier for this input |
| `archetype_evidence_tier` | **`default`** — no Tier A run exists (`MF-15`, a Could) |
| `carrier_coverage` | **complete** — all five main vectors stated |
| `emissions_reconciliation` | **`emissions_year_unmatched`** (§1.7, §10.2) |
| `data_year_offset` | −1 year |
| `confidence` | the **lower** of the unit's and the duty profile's |

**The tiers are mixed in both directions at this premise**, and that is the point of carrying
all of them. Area is `measured` and the carrier mix is `activity_default`; the dryer's vintage
is `process_known` and the chiller's is `premise_bounded`; the emissions reconciliation did not
run at all. A single site-level quality score would have averaged that into something
meaningless. `V23` asserts that `mix_evidence_tier` in particular appears on every row.

`A9` rolls these rows up to GB and compares against ECUK, the greenhouse-gas inventory and the
emissions budget. The budget comparison is **reported, never enforced**: the
"reported comparison, not constraint" pattern.

---

## 10. §7 — emissions attribution and reconciliation

### 10.1 Attribution, base year

| # | Rule | At this premise |
|---|---|---|
| 7.1 | Fuel CO₂ is **produced by** the unit that burns the fuel, on a coefficient A6 derived (D15); process CO₂ by the chemistry unit | all 16.83 kt produced by the boiler, the CHP and the dryer, and all of it vented; **no process CO₂ at all** — the contrast with cement |
| 7.2 | Non-CO₂ gases tracked separately; CCS never abates them | the site's refrigerant losses are reported and are not a combustion emission |
| 7.3 | Biomass zero-rated before capture | `solid_biomass` carries a **gross** 97.22 kt/PJ and `biogenic_fraction` 1 (§1.11, §6.3), so A6 derives the whole of it onto `co2_fuel_biogenic`; the zero-rating is on the **carrier**, so the quantity is reported and the charge is £0. No period of this pathway burns biomass, so the quantity is zero here, and with no capture at this site the ordering the rule is about has nothing to bite on |
| 7.4 | Direct versus indirect is a property of the carrier | `electricity.is_indirect` = true; every other carrier here is direct |
| 7.5 | Reporting categories derived over units, and they may overlap | `chp_gas_turbine` appears under *combustion* and under *generation* |
| 7.6 | Reconciliation **at the base year** | §10.2 — **skipped and reported** |

**Base-year direct emissions are read off the balance (D15), not computed beside it.** §7's
expression is the same one the objective charges:

| Unit | Carrier | Computation | kt CO₂e |
|---|---|---|---|
| `boiler_lt_gas` | `co2_fuel_fossil` | 0.132346 PJ × 56.1 | **7.42461** |
| `chp_gas_turbine` | `co2_fuel_fossil` | 0.074655 PJ × 56.1 | **4.18815** |
| `dryer_direct_gas` | `co2_fuel_fossil` | 0.093000 PJ × 56.1 | **5.21730** |
| **Total produced, and $d_{\text{co2\_fuel\_fossil}}$ vented** | | | **16.83006** |
| `co2_fuel_biogenic` | — | no biomass unit runs at 2025, and none in any later period of §8.7 | **0** |
| Indirect, on the **import** (§7.8) | | 0.060000 PJ × 18.0 | 1.08000 |

**No process emissions at all**, which is the contrast with the cement works: every duty here
is energy-denominated (§1.3), so the site's whole footprint is combustion and disappears when
the fuel does: 16.83 kt at 2025, 10.83 kt once recovered heat takes the hot water in 2030, **zero from 2040**. A cement works cannot do that, because
446.25 kt of its CO₂ comes from limestone and no fuel switch touches it.

§8.1.1 gives the §7.7 allocation of the CHP's 4.18815 kt across its two outputs, and the
282 gCO₂e/kWh that falls out of it.

### 10.2 §7.6 reconciliation

**Skipped, and reported as skipped.** `premise_measured_emissions` has rows at 2022 and 2023 but
none at the base year (§1.7), so under §3.1.1's table the premise is reported
`emissions_year_unmatched` and is **never rejected** — the entity is optional intelligence, and
rejecting the premise would discard the evidence.

The 2022 and 2023 rows remain a **reported trend and never a calibration target**:

| Year | Measured direct | Computed direct | Note |
|---|---|---|---|
| 2022 | 17.9 kt | — | reported trend |
| 2023 | 17.3 kt | — | reported trend |
| **2024** | **no row** | **16.83 kt** | **`emissions_year_unmatched`** |

The trend 17.9 → 17.3 → 16.83 is consistent with the metered gas of §1.2 falling 0.315 → 0.308
→ 0.300 PJ, which is the kind of corroboration history is held for and is exactly what `V25`
forbids the model from *acting* on. Adding a 2025 row, after the base year, must move nothing
either — and a test that only adds older years would pass against an implementation that
silently reads `max(data_year)`, which is the most natural wrong thing to write.

**The biogenic leg does not complicate the comparison here, and it would elsewhere.** Nothing
biogenic is burnt in this base year, so the computed 16.83 kt is the whole of the site's direct
CO₂ and the measured rows are comparable to it without qualification. At a site that did burn
biomass the two would first have to agree on whether the measured figure is gross or net of the
zero-rated carrier — §7.6 compares like with like or not at all — and this example cannot
exercise that.

Where the cement works reconciles to 1.96% and adopts the measured combustion/process split for
its base year, this premise has nothing to reconcile against and says so on every output row.
Both branches are exercised across the pair of examples.

---

## 11. What this fixture asserts

Tests are the specification's, at §10.3. Scope is `load`, `premise` or `release`.

| # | Scope | Asserted here as |
|---|---|---|
| **V1** | release | *not asserted by this fixture* — the coupled-off R run is `MF-57` |
| **V1b** | release | *not asserted* — this premise is **outside** the carrier-equivalent configuration (§13.2) |
| **V2** | load | the coefficients of §1.11 round-trip to 1e-6, **except `heat_pump_lt_air`**, which carries `draws_ambient` and is exempted by name (§3.6) |
| **V4** | load | every carrier the units declare appears in `unit_input_output`; profile uncertainty bands order correctly |
| **V5** | premise | emissions invariants over units; the **zero-rating** leg is asserted at the carrier — `solid_biomass`'s 97.22 kt/PJ is gross and the whole of it derives onto a `zero_rated` carrier (§1.11) — while the **before capture** ordering is vacuous, because no capture exists here and no period burns biomass |
| **V6** | premise | §7.4, §8.6 — $Z^{\text{exp}}$ is in the objective and **zero in every period**, because the site never has a surplus; the term is computed, not assumed non-negative, and its sign is exercised only at a premise whose generation exceeds its load |
| **V10** | release | two runs of this fixture agree under the §9.3 tie-break |
| **V11** | load | §3.1 — exactly one process tier resolves, `site_known` |
| **V12** | premise | §8.2 — the siting cap holds and its sum runs over `pv_rooftop` alone; **neither CHP is in it** |
| **V16** | batch | §8.5 — 3.40 MW rebuilt against 3.4 MW metered, **exact** |
| **V17** | premise | §5.3 — three cohorts age to their own end-of-life years; no abatement unit exists here |
| **V18** | premise | §8.1 — **nineteen** carrier nodes close to 1e-6, emission carriers included. Every reject node closes through disposal in 2025; from 2030 the condenser and engine-exhaust nodes close through a recovery unit's draw, the condenser node with disposal beside it, and the dryer-exhaust node through disposal alone; `heat_lt60` carries no flow in any period |
| **V19** | load | **§3.4 — no unit is eligible for a duty above its `grade_out`.** The four rank-2 heat units (both low-grade heat pumps, the condenser heat pump and the exhaust recovery unit) are absent from the `STM` and `DRY` candidate sets; the rank-1 economiser reaches no duty at all; no unit reaches `DRY` except the three dryers |
| **V20** | load | (d) only — `battery_2h` has β set and ψ, χ, ε unset; (a)–(c) and (e) need archetype and hybrid rows this premise has none of, and V20 (a) is **reported as not-run** |
| **V21** | load | §6.3 — the export price is strictly below the import price at all six periods; §8.6 and the pathway without the reject leg (below) are where it decides the result, by making export at 2050 a loss |
| **V22** | premise | **all three legs** — §10.1 |
| **V23** | load + premise | §5.2 — one tier resolves, `activity_default`, tiers were tried in order, and it appears on every output row |
| **V24** | load + premise | §1.2, §1.7 — one row per key at the base year; no duplicate `(key, year)`; the optional entities **report** rather than reject, and §1.7 exercises that branch |
| **V25** | premise | §1.2, §10.2 — the 2022 and 2023 rows move nothing by more than 1e-9, including §7.6's reported reconciliation |
| **V26** | premise | §1.5 — six disjoint intervals, all valid at 2024, and `A2`, `A4` and §3.10.2's cohort read touch no row outside them, and no §3.10.2 cohort under a closed interval has a `commissioned_year` after that interval's `valid_to_year` (no interval here is closed, so the clause is vacuous) |
| **V27** | load | §1.11 — each of the five boilers, three dryers and four heat pumps carries exactly one `fuel_input` row and the economiser and the exhaust recovery unit none; the source-heat inputs are auxiliary `intermediate` carriers and are not counted |
| **V28** | load + premise | §3.2 — the published `Food Processing Centre` shares sum to 1.00 per vector, all six register processes carry rows, and no renormalisation is needed |
| **V29** | premise | §8.1, §8.1.1 — disposal is used on the four reject carriers that carry heat and on `co2_fuel_fossil`, and declared at zero on `reject_flue_solid_liquid` and `co2_fuel_biogenic`; the CHP's §7.7 allocation sums to its 4.18815 kt accounted figure exactly; the two layers are never added |
| **V30** | premise | §8.1, §10.1 — emission carriers balance; §7's total equals the objective's carbon term ÷ π × 10³; on the two biomass units the derived fossil and biogenic coefficients sum to the **gross 97.22 kt/PJ** — 0.00000 + 109.23639 on `boiler_lt_biomass`, 0.00000 + 133.67750 on `chp_biomass_st`, each per PJ of heat — and any `co2_fuel_biogenic` disposal is a reported quantity charged at **£0** rather than an absent one; hydrogen's derived coefficients are zero **in this scenario** and change with it, which is why §3.6 derives them rather than declaring them |
| **V31** | load | §1.11 — no unit at this site consumes a carrier it also makes, so every `(unit, carrier)` pair here holds one role; each row's sign agrees with it, each of the nineteen units has exactly one `primary_output`, every unit's reject heat is `reject` on its class's carrier, and the heat pumps' and recovery units' source heat is `aux_input` |

**This fixture is what milestone M4, the MVP exit, runs on.** Its gate, item by item:

| M4 exit condition | Where |
|---|---|
| ⚠ *Restated under D13* — **84 low-temperature-heat rows across eleven sectors collapse to eight units**, of which this dairy reaches seven | §3.3 |
| A 120 °C duty has boiler, CHP, heat pump and electric resistance competing under C10 | §3.4, §8.3 |
| The heat pump is absent from the drying duty's candidate set | §3.4 |
| The premise's existing CHP, named by the audit and sized by the default installed-unit table, appears in the baseline with its electricity co-product | §1.5.1, §1.12, §5.1, §8.1 |
| The CHP produces heat **and** electricity into the balance | §8.1 |
| Electricity export is declared and priced below the import price, and stays at zero: the site never has a surplus, and without the reject leg the hydrogen CHP grows at 2050 only to the site's own load | §6.3, §8.6, below |
| PV is bounded by the area and the CHP is not | §8.2 |
| V19, V21, V22 (a) (b), V23 pass | above |
| Every output row carries its evidence tiers | §9 |

**The reject-heat leg of §8.4 is not part of M4's gate.** It belongs to `MF-12` (reject-heat
coefficients on every heat-consuming unit), a Should landing at milestone M6, and it is walked
here so that the coefficient's shape is settled before the data build starts. Without it no
unit rejects anything and the recovery units have nothing to draw, so the pathway M4 runs on
differs from §8.7 in three places:

- **2030.** `heat_pump_lt_air` takes the rank-2 duties instead, at £12.05681m/PJ against the
  standing boiler's £16.81683m: 0.094067 PJ/yr on 0.110667 PJ/yr of capacity. Direct emissions
  still fall to 10.83 kt.
- **2040 and 2045.** As §8.7, with the air-source heat pump in place of the two recovery units;
  net import is 0.060126 PJ/yr.
- **2050.** The air-source heat pump built in 2030 reaches the end of its 20-year life, and
  rebuilding it at £10.09276m/PJ loses to growing the hydrogen CHP at £7.50242m, whose
  electricity displaces import at £23.50. The CHP grows until the site stops importing: with
  CHP heat $H$ covering the 120 °C duty and part of the hot water, and the air-source heat pump
  the rest of the 0.150059 PJ of boiler-house and space heat, 0.95000 $H$ + 0.006404 =
  0.086131 + 0.35710 (0.150059 − $H$), so $H$ =
  **0.101991 PJ/yr** and the heat pump is rebuilt for **0.048068 PJ/yr**. It stops exactly
  there, because past that point its electricity would be exported at £13.50 and its heat would
  cost £17.00242m/PJ against the new heat pump's £10.09276m. **Export stays at zero**, and it
  is the price wedge `V21` asserts that keeps it there.

---

## 12. The published fixture (`MF-23`)

This example is published as a test fixture, not only as prose. `MF-23` (the food and drink
worked example as a fixture) is a Must and is the MVP's exit criterion at milestone M4.

| Artefact | Content |
|---|---|
| `fixtures/food_drink/premise.parquet` | §1.1–§1.10 as the three required and six optional entities — **and no `premise_throughput` rows**, which the schema must accept |
| `fixtures/food_drink/reference/*.parquet` | §1.11–§1.12: the `carrier`, `unit`, `unit_input_output`, `unit_eligibility` and `activity_default_unit` rows this premise reaches |
| `fixtures/food_drink/lineage.parquet` | §3.3's thirty `IFD` rows with one disposition each, which `MF-03` requires and `V1b` compares through |
| `fixtures/food_drink/scenario.parquet` | §6: `infrastructure_scenario` and `scenario_parameters` for `central` at `mersey` |
| `fixtures/food_drink/expected/*.parquet` | §8.1's base-year ledger, §8.3's and §8.4's levelised tables, §8.7's pathway, §10.1's emissions |
| `fixtures/food_drink/manifest.json` | units, rounding, solver, and the settings below |

**Units and rounding.** Money £m at 2021 prices, energy PJ/yr, emissions kt CO₂e/yr, area m²,
power MW. Intermediate arithmetic at six significant figures, asserted values at five.
Comparisons are relative, at the `MF-58` tolerances: objective within 0.5%, energy per carrier
per period within 1%.

**Solver settings**, pinned in the package so `V10` (determinism) can hold across machines:
HiGHS, version pinned in `pyproject.toml`, presolve on, **single-threaded**, the lexicographic
tie-break of §9.3 over `(unit_id, carrier_id, role)` applied as a second-objective solve over the
optimal face. The tie-break matters at this premise, and in one place it is the only thing
deciding. The exhaust recovery unit and the condenser heat pump are both eligible for both
rank-2 duties, `LTH` and `SPC`, at the same grade, so which duty the 0.005226 PJ of recovered
exhaust is booked against is a genuine tie: the plant and the objective are the same either
way, and only the tie-break makes the dispatch rows repeat. Elsewhere margins are narrow
without being ties: §8.3 puts the standing CHP and the standing gas boiler within £0.07m per PJ
of each other at 2035, and §8.4 the hydrogen CHP and the hydrogen boiler within £0.22m per PJ at
2040. Without the price wedge of §6.3 and this tie-break, two identical runs could legitimately
report different dispatch.

**What M4's gate does with it**: the fixture runs through S1–S8 in the **full** configuration —
not the carrier-equivalent one — and the nine conditions of §11 are asserted against the
expected tables. Table snapshots of the fixture outputs, rounded, are the regression net
(`MF-61`, a Should at milestone M6).

---

## 13. What this example demonstrates, and what it leaves open

### 13.1 What it demonstrates

1. **The collapse is real, and under D13 it is a cross-sector one** (§3.3). 84 low-temperature-heat rows across eleven sectors become eight units — a factor of ten, against the three-to-one the within-sector reading gave. Five boiler rows differing only by
   fuel become one unit with five carrier bindings; the electric boiler and the heat pump are
   preserved as their own devices; and the CHP-steam pseudo-technology is dropped outright
   because C8 and C10 replace it. Adding hydrogen firing is now one row in
   `unit_input_output`, not a new technology.
2. **A CHP produces two carriers at once, and one of them balances** (§8.1). Its heat satisfies
   a duty through C1 and never touches the `heat_100_150` node; its electricity enters C8
   regardless, because a unit's co-products scale with total activity. That asymmetry is what
   makes onsite generation, self-consumption and export expressible at all.
3. **The meter hides a third of this site's electrical load** (§5.1), and only a known CHP
   recovers it. Here the audit names it (§1.5.1) and `activity_default_unit` sizes it; for a
   dairy whose audit named nothing, §3.16 alone would put it there. Without either, a dairy with
   a CHP and one without are the same row, and every electrification decision downstream runs on
   a base that is 32% too small.
4. **The grade ladder separates two duties a flat coefficient would have merged** (§3.4, §8.4).
   The 80 °C duty goes to a heat pump and the 120 °C duty to a CHP, because the rank-3 heat
   pump must buy rank-2 source heat and the rank-2 one cannot reach rank 3 at all. Today
   `IFDSTMHP01` and `IFDLTHELCHP01` carry the same `33.333` coefficient, and under that number
   one machine would have taken both.
5. **C10 is enforced at load, not in the matrix** (§3.4). No variable is created for a heat pump
   at the 150–200 °C drying segment, so there is nothing to relax and nothing to get wrong, and `V19` is a
   load-scope test for that reason.
6. **Waste heat abates because §7's attribution rule says so** (§8.4, §10.1). Reject heat
   carries no fuel, and the units drawing it inherit nothing, so when the condenser heat pump and
   the exhaust recovery unit take the hot water in 2030, direct emissions fall from 16.83 to
   10.83 kt five years before any plant dies.
7. **Reject heat is sorted by where it comes from, and the cheap tranches go first** (§1.11,
   §8.4). The CHP's exhaust at £2.14m per PJ and the chillers' condenser heat at £9.32m are
   recovered; the dryer's dusty exhaust has no recovery unit and the boiler's condensing
   increment no duty at its grade, so both are disposed of and reported by source. A single
   low-grade carrier would have offered all four at one price.
8. **The connection is a different question from the energy** (§8.5). The chosen pathway needs
   no reinforcement; the all-electric counterfactual needs 3.85 MW on a 4 MW supply. A model
   with no electricity balance cannot see either number.
9. **Evidence tiers mix in both directions at one premise** (§9). Area `measured`, carrier mix
   `activity_default`, one unit's vintage `process_known` and another's `premise_bounded`, and
   no emissions reconciliation at all. A single site-level quality score would have averaged
   that into nothing.
10. **`D11` matters much less here than at the cement works** (§5.3). The whole boiler house
    carries under £1.1m of residual value against a kiln's £119.5m. The mechanism is identical
    and its weight is not, which is worth knowing before assuming plant age is decisive
    everywhere.

### 13.2 What it cannot show

- **No mass denominator.** Every duty here is energy-denominated, so `D5`'s second convention,
  the process-emission term and the `premise_throughput` requirement are all exercised only at
  the [cement works](2026-08-28-carb3-site-energy-system-worked-example-cement.md).
- **No abatement unit, so no `unit_abatement_host` rows and no host-life annuity.** `V17`'s
  abatement leg and `V33` (a capture train abates several hosts) are asserted there.
- **No `V1b` comparison.** This premise is deliberately **outside** the carrier-equivalent
  configuration of §10.2: it has a battery in the candidate set (condition 2), onsite
  generation (condition 3) and an active cascade, siting cap and connection limit (condition 4),
  so three of the five conditions fail. Condition 1 holds under D13 at every premise, and
  condition 5 (no export) holds here only as a result of the solve, not by configuration. The
  R run has no way to express any of it, so there is nothing to
  compare against. Parity is the cement works' job; mechanism is this one's, and conflating the
  two is what the pair of examples exists to prevent.
- **No export.** The site imports electricity in every period (§8.6), so $Z^{\text{exp}}$ is
  zero throughout and the sign trap `V6` (no cost component is assumed non-negative) records is
  exercised by neither worked example. A premise whose generation exceeds its load is needed.
- **No Tier A coefficients.** ψ, β, χ and ε are `default`-tier throughout, so PV takes no peak
  credit (§8.2) and the battery's β is the only one doing work. `MF-15` and `MF-36` are Coulds
  gated on the G4 scale gate.
- **No hybrid unit.** `V20` (b), (c) and (e) need `unit_bill_of_materials` rows this premise
  has none of.

### 13.3 Open points against the specification

**Five of the seven this example originally raised are now closed**, by D13, D15, the disposal
variable, the two new §3 entities and §7.7. They are kept with their resolutions rather than
deleted, because the record of *why* a rule exists is what stops it being undone.

| # | Open point | Status |
|---|---|---|
| 1 | Nothing said where a process's share of premise energy comes from; §3.3 ruled out the only table that held it | **Closed.** §3.3.1 promotes it to an entity, and §3.2 above now runs on the published `Food Processing Centre` shares. The gas side closes to +0.0003% |
| 2 | No per-premise tier over that table | **Closed.** §3.10.1 `premise_process_energy` — quantities, not shares, with the residual renormalised |
| 3 | C8 admitted no disposal route, so unrecovered reject heat could not balance | **Closed.** $d_{c,t}$ (§5.2). This site disposes of 0.11193 PJ of reject heat in 2025, 0.03501 in 2030 and 0.02639 from 2040, each by source class: a reported quantity rather than an assumption |
| 4 | §7 double-counted once electricity was generated on site | **Closed.** §7.8 charges an indirect carrier on the import; §7.7 gives the allocation layer, which §8.1.1 uses to put the CHP's electricity at **282 gCO₂e/kWh** against a grid at 65 |
| 5 | A `MOT` or `REF` duty had no carrier that worked | **Closed.** §3.4 states the service-carrier convention and names `motive_power` and the graded `cooling@band` carriers |
| 6 | Nothing said how a multi-binding unit becomes LP variables | **Closed, by removal.** D13 makes fuel part of a unit's identity, so there are no multi-binding units left to expand. `unit_eligibility.max_share` now caps a fuel, which was the knock-on |

One remains, and one is new:

| # | Open point | Where it bites | Closed by |
|---|---|---|---|
| **7** | **§3.4 declares `grade_rank` and `grade_label` but no canonical band set**, and nothing in the reference data holds one. Where the lines are drawn decides which units are eligible for which duty | §1.11 — the four bands are this example's own; with two bands a single heat pump would take both the 80 °C and the 120 °C duty | `T17` (duty families and heat grades). §3.4 now declares a canonical band set, six heat and three cooling; this example keeps its own four heat bands to show the heat pump split, and its one cooling duty sits in §3.4's `cooling_0_15` |
| **8** | **The MVP's exit gate is stated in pre-D13 terms.** Milestone M4 asserts "eight fuel-variant rows collapse to three units", which D13 makes false and uninteresting — within a sector there is now almost nothing to collapse | §3.3 — the real claim is the cross-sector one, 84 rows to eight units | [notes/18](../notes/18_mvp_feature_prioritisation.md) M4 and `MF-03`, which should assert the cross-sector collapse and the per-fuel attributes D13 buys |

Two things stated rather than filed. **The objective charges direct carbon only** (§6.3): §5.4
does not say whether an `is_indirect` carrier's emissions enter $Z^{\text{carbon}}$, and both
worked examples charge direct and report indirect so that they remain comparable. And **§5.6 defines
only the peak factor $\lambda$**, so nothing says how C11's peak is rebuilt, which year it reads, or how
an annual energy becomes a power for the export bound; this example uses mean flow over
operating hours times the observed within-shift peak factor, applies no diversity step, and
therefore **understates** the import peak of §8.5; it would understate an export peak too,
were there one.

---

## Sources

- Implementation specification §1.1–§1.6, §2.1–§2.3, §3.1–§3.17, §4, §5.1–§5.5, §7, §9.2–§9.3,
  §10.1–§10.5, §13.
- [Delivery document](2026-08-28-carb3-site-energy-system-delivery.md): `T16` (this example),
  `T13`, `T17`, `T18`, `T23`; the not-in-scope list.
- [Data migration](2026-08-28-carb3-site-energy-system-data-migration.md): groups A and B (the
  397-row collapse), B4 (heat-pump COP by grade lift), B5 (reject heat), C5 (supply units), D1
  (area).
- [Architecture](2026-08-28-carb3-site-energy-system-architecture.md): the unit spine, the 12
  service families and 14 chemistry nodes, the graded-heat cascade, and the `IFDSTMHP01` /
  `IFDLTHELCHP01` flat-coefficient defect.
- Notes [16](../notes/16_input_data_readiness.md) for the duty-family and default-generation
  gaps, [17](../notes/17_mvp_what_it_does.md) worked example A,
  [18](../notes/18_mvp_feature_prioritisation.md) `MF-03`, `MF-12`, `MF-13`, `MF-23`, `MF-41`,
  `MF-42`, `MF-43`, `MF-46`, `MF-47`, `MF-59`, `MF-61`, and milestone M4.
- [`docs/notes/data/emissions_source_classification.csv`](../notes/data/emissions_source_classification.csv)
  for the thirty `IFD` technology rows of §3.3;
  [`activity_process_register.csv`](../notes/data/activity_process_register.csv) for the
  `Food Processing Centre` default process set.
- The [cement worked example](2026-08-28-carb3-site-energy-system-worked-example-cement.md),
  which walks the parity case on the same thirteen sections. Read together, the two cover both
  denominators of `D5`, both branches of §3.1.1's base-year rule, both branches of §7.6, and
  all three tiers of §4.1's carrier-mix ladder.
