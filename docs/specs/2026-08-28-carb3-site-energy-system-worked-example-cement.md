# CaRB3 Site Energy System — Worked Example: a cement works

**The parity case.** One premise carried end to end through the nine algorithms `A1`–`A9`
(§4), exercising the mass denominator (`D5`, hybrid denominators), tier-1 plant vintage
(`D11`, existing plant has an age), the stranding charge, a CCS train as an abatement unit,
and — in §10 — the carrier-equivalent configuration that `V1b` (reproduce the R run's
objective and per-carrier energy) compares against.

Section references without a document name are to the
[implementation specification](2026-08-28-carb3-site-energy-system-implementation.md).
Feature labels `MF-nn` are from
[notes/18](../notes/18_mvp_feature_prioritisation.md); task labels `Tnn` from the
[delivery document](2026-08-28-carb3-site-energy-system-delivery.md).

**All values are illustrative.** They are internally consistent — every total reconciles and
every step's arithmetic follows from the one before — but none is a citation. Money is £m at
2021 prices, energy PJ, mass Mt, emissions kt CO₂e, area m², power MW, on §1's conventions.
Intermediate arithmetic is carried at six significant figures and quoted at five.

**This example cannot show the carrier mechanism**, and that is structural rather than a
matter of taste: `Cement Works` resolves to exactly two COMIT process commodities, `ICMCLK`
(clinker) and `ICM` (cement), so there is no `LTH` (low-temperature heat), no `STM` (steam),
no `DRY` (drying) and no `SPC` (space heating). Nothing cascades, the kiln's candidates
differ by *fuel* rather than by device, and CHP appears only fused inside bundled capture
rows. The mechanism is demonstrated on the
[food and drink premise](2026-08-28-carb3-site-energy-system-worked-example-food-drink.md)
instead. The two examples are deliberately parallel: the same thirteen sections, in the same
order, at the same depth.

---

## 1. The premise

### 1.1 `premise_record` (§3.1)

```
premise_id                   P-000123
carb3_activity               Cement Works
process_set_id               —                      (absent ⇒ the activity's default set)
nation                       England
latitude / longitude         53.35 / -1.75
floorspace                   46,000 m²
construction_year            1957
construction_year_band       —
last_refurbishment_year      2011                   (collected, not read — §3.1)
data_year                    2024                   ← the base year (D12)
source                       CaRB3 stock model v3.1
```

`construction_year` 1957 bounds plant age at 67 years under `D11` (existing plant has an
age) — longer than any lifetime on site, so the bound is slack and buys nothing here. That
is the expected outcome for heavy industry, and it is the *young* premise, not this one, on
which the §5.3.1 tier-2 formula binds. §5.3.1 is cited throughout the specification and is
**not written** (`T23`, complete §5); the tier-2 window quoted in §5 below is therefore read
from the [COMIT-parity baseline specification](archive/2026-08-19-carb3-site-decarbonisation-implementation.md)
and must be re-derived when §5.3.1 lands.

### 1.2 `premise_energy` (§3.1.1) — consumption by carrier per year

| `carrier_id` | `vector` | `quantity` PJ/yr | `data_status` | `data_year` | Read as |
|---|---|---|---|---|---|
| `electricity` | electricity | 0.39000 | measured | 2022 | history |
| `electricity` | electricity | 0.41000 | measured | 2023 | history |
| `electricity` | electricity | **0.42000** | measured | **2024** | **base year** |
| `coal` | coal | 2.31000 | measured | 2022 | history |
| `coal` | coal | 2.18000 | measured | 2023 | history |
| `coal` | coal | **2.10000** | measured | **2024** | **base year** |
| `natural_gas` | gas | **0.31000** | measured | **2024** | **base year** |
| `waste_derived_fuel` | other | 1.42000 | measured | 2022 | history |
| `waste_derived_fuel` | other | **1.55000** | measured | 2023 | **substituted** |
| `fuel_oil` | oil | **0.00000** | **not_consumed** | **2024** | **base year** |
| `solid_biomass` | biomass | — | — | — | **absent — not assessed** |

All rows are metered at connection `C-01` or `C-02` (§1.4) and omit `connection_id`, which
§3.1.1 permits for a site whose carriers each arrive on one supply.

**Base-year energy read by the model: 0.42000 + 2.10000 + 0.31000 + 1.55000 + 0.00000 =
4.38000 PJ/yr.** Four things this table shows that a wide, one-row-per-premise format could
not:

1. **Waste-derived fuel is an ordinary row.** Cement kilns co-fire substantial SRF/RDF —
   35.4% of this site's energy — and it names its own carrier, so §7.3 (biomass zero-rated
   before capture) can apply the right biogenic fraction rather than treating the stream as
   wholly fossil.
2. **`fuel_oil` is an explicit measured zero.** This works burns no oil and that is known.
3. **`solid_biomass` is absent, which is a different claim** — nobody assessed it. Carrier
   coverage for this premise is recorded as incomplete and reported on every output row
   (§3.1.1's absence rule, §8).
4. **Waste-derived fuel has no base-year row** and substitutes from the nearest year, 2023.
   `year_evidence_tier = substituted` on this premise's output rows. Without §3.1.1's
   substitution ladder a carrier carrying 35.4% of the site's energy would have been read as
   *absent*, `A4` would have back-solved no plant for it, and the site's baseline emissions
   would have fallen by 69.75 kt — failure mode 9 of §10.5, exactly.

The 2022 and 2023 rows are **history**. `V25` (history is never read) asserts that adding
them, at years before *and* after the base year, moves no §5.3 parameter, no constraint
coefficient, no solution value and no reported reconciliation by more than 1e-9.

### 1.3 `premise_throughput` (§3.1.2) — physical output by carrier per year

| `carrier_id` | `quantity` Mt/yr | `data_status` | `data_year` | Read as |
|---|---|---|---|---|
| `clinker` | 0.83000 | measured | 2023 | history |
| `clinker` | **0.85000** | measured | **2024** | **base year** |
| `cement` | 1.11000 | measured | 2023 | history |
| `cement` | **1.13000** | measured | **2024** | **base year** |

Required, because `Cement Works` carries two mass-denominated processes under `D5` (hybrid
denominators); `A1` rejects the premise with reason `missing_throughput` otherwise. Two
products in one premise is the case the previous single `throughput_quantity` column could
not express, and cement is the ordinary case for it: clinker is made, then ground and blended
into cement at a clinker factor of 0.85 / 1.13 = **0.75221**.

### 1.4 `premise_connection` (§3.1.3)

| `connection_id` | `carrier_id` | `import_capacity` | `export_capacity` | `connection_voltage` | `available_area` |
|---|---|---|---|---|---|
| `C-01` | `electricity` | 25 MW | 0 MW | 33 kV | — |
| `C-02` | `natural_gas` | 12 MW | 0 MW | — | — |

**Capacities are never summed across connections** (§3.1.3), and here they could not be: one
is electrical and one gas. C11 (connection capacity) is written per connection for this
reason.

**`available_area` is not supplied**, which is the normal case and the reason `MF-09`
(available area, Must tier) exists. The fallback is a footprint proxy: `floorspace`
46,000 m² × the per-activity usable-area ratio for `Cement Works`, 0.35, = **16,100 m²**,
carried as `area_evidence_tier = proxy`. That ratio table is a modelling-team input nobody
owns yet ([notes/18](../notes/18_mvp_feature_prioritisation.md), open calls). Without an area
C12 (siting cap) is unbounded and the LP builds infinite PV.

### 1.5 `premise_process_detail` (§3.10) — `D10` tier 1 (known site detail wins)

From the site's environmental permit:

| `process_id` | `valid_from_year` | `valid_to_year` | `connection_id` | `known_capacity` | `unit_id` | `confidence` |
|---|---|---|---|---|---|---|
| `quarrying_crushing` | 1957 | — | `C-01` | — | — | medium |
| `raw_grinding_blending` | 1957 | — | `C-01` | — | — | medium |
| `raw_meal_homogenisation` | 1957 | — | `C-01` | — | — | medium |
| `kiln_pyroprocessing` | **1957** | **2003** | `C-01` | 0.70 Mt/yr | `kiln_wet_ICMCLK` | medium |
| `kiln_pyroprocessing` | **2004** | — | `C-01` | **0.95 Mt/yr** | `kiln_dry_coal` ⚠ | **high** |
| `clinker_cooling` | 2004 | — | `C-01` | — | — | medium |
| `cement_grinding` | 1957 | — | `C-01` | — | — | medium |
| `packing_dispatch` | 1957 | — | `C-01` | — | — | medium |
| `site_services` | 1957 | — | `C-01` | — | — | medium |

Nine rows covering eight processes, so this is the site's **complete** process list as at any
year in range (§3.10's completeness rule). Two things it shows:

- **The register's ninth process, `quarry_mobile_plant`, is absent.** At this works the
  excavators and haulers are contractor-operated and outside the metered boundary, so they
  are not processes of this premise. Tier 1 overrides the activity's default set outright
  (`D10`, tiered site intelligence), and that is what tier 1 is for. It is also why
  `fuel_oil` is an explicit zero in §1.2.
- **`kiln_pyroprocessing` carries two disjoint validity intervals**, a wet line to 2003 and
  the dry preheater/precalciner line from 2004. `A2` and `A4` read only the interval valid at
  the base year (§3.10, `V26`), so the site is not back-solved as a blend of a wet and a dry
  kiln that never coexisted — failure mode 10 of §10.5. The closed interval also explains the
  step in `premise_energy`'s history that would otherwise look like a data error.

Only the kiln carries a capacity and a named unit; the rest are listed to establish that they
exist and nothing more.

**⚠ `unit_id` names one unit, and this kiln is three (D13).** The works co-fires coal, gas and
waste fuel, which §1.11 models as three units sharing the clinker duty. §3.10's field is
singular, so the permit's entry names the dominant one and A4 resolves the rest from the
metered carriers (§5.2). A site that genuinely ran a single-fuel kiln would be fully
determined here and is not. Recorded in §13 — the field should take a set, or the entity
should be keyed one field wider, and this is a consequence of D13 that §3.10 has not caught up
with.

### 1.6 `premise_process_vintage` (§3.15) — `D11` tier 1

From the same permit, which records the kiln line's commissioning:

| `process_id` | `cohort_id` | `unit_id` | `commissioned_year` | `capacity_share` | `confidence` |
|---|---|---|---|---|---|
| `kiln_pyroprocessing` | `1` | `kiln_dry_coal` | **2004** | 0.53030 | high |
| `kiln_pyroprocessing` | `2` | `kiln_dry_wdf` | **2004** | 0.39141 | high |
| `kiln_pyroprocessing` | `3` | `kiln_dry_gas` | **2004** | 0.07829 | high |

Three rows at one commissioning year, because §3.15 is keyed per `(cohort_id, unit_id)` and
D13 makes this one physical kiln line three units. The shares are the base-year fuel split of
§5.2 and sum to 1.00 as §3.15 requires. This is the entity handling D13 gracefully where
§3.10 above does not: because vintage is stated as *shares*, a co-firing kiln decomposes
naturally, and all three cohorts carry the same year because they are the same steel. **No rows for the other seven processes**, and unlike §1.5 that is not an omission:
this table asserts nothing about completeness. They fall to tier 2 and are aged from the
works' 1957 construction year, where the bound is slack. The cohort is read only because
`kiln_pyroprocessing` is valid at the base year (§3.15's last rule); the wet line's plant is
already gone and ageing it under `D11` would strand an asset that no longer exists.

### 1.7 `premise_measured_emissions` (§3.11)

From the site's UK ETS account:

| `emission_year` | `source_category` | `ghg` | `quantity` kt CO₂e/yr | `scope` |
|---|---|---|---|---|
| 2023 | combustion | total_co2e | 298 | direct |
| 2023 | process | total_co2e | 437 | direct |
| **2024** | **combustion** | **total_co2e** | **291** | **direct** |
| **2024** | **process** | **total_co2e** | **452** | **direct** |

Base-year parts sum to **743 kt**, and §3.11's rule needs a `total` row only where the split
is unavailable, so no consistency check applies. §7.6 reconciles against the 2024 rows
(§10); the 2023 rows are a reported trend and never a calibration target.

### 1.8 `premise_operating_profile` (§3.12)

Per connection, because peak and load-factor fields are per connection where a site has more
than one; the schedule fields are premise-wide and repeat.

| Field | `C-01` (electricity) | `C-02` (gas) |
|---|---|---|
| `profile_year` | 2024 | 2024 |
| `operating_pattern` | continuous | continuous |
| `operating_hours_per_year` | 8,400 | 8,400 |
| `operating_days_per_week` | 7 | 7 |
| `shutdown_weeks` | 3 (annual kiln maintenance) | 3 |
| `peak_electricity` | 16.2 MW | — |
| `peak_gas` | — | 11.0 MW |
| `load_factor_electricity` | 0.82 | — |
| `load_factor_gas` | — | 0.89 |
| `within_shift_peak_factor` | 1.17 | 1.25 |
| `profile_basis` | half_hourly | daily |
| `confidence` | high | medium |

§3.12's consistency rule, at like years:

$$\text{load factor} = \frac{E\,[\text{PJ/yr}] \times 277{,}778}{P^{\text{peak}}\,[\text{MW}] \times 8{,}760}$$

- Electricity: 0.42000 × 277,778 = 116,667 MWh; ÷ (16.2 × 8,760 = 141,912) = **0.82211**,
  against the declared 0.82 — **0.26% apart**, inside the 5% tolerance.
- Gas: 0.31000 × 277,778 = 86,111 MWh; ÷ (11.0 × 8,760 = 96,360) = **0.89364**, against the
  declared 0.89 — **0.41% apart**.

Neither is reported as `profile_energy_inconsistent`.

The within-shift peak factor is *observed* here rather than assumed, because the site supplied
both a schedule and a metered peak: mean electrical demand over operating hours is
116,667 ÷ 8,400 = **13.890 MW**, and 16.2 ÷ 13.890 = **1.1663**, quoted as 1.17. An observed
value is what makes a credible activity default for cement works that supply only a schedule.

### 1.9 `premise_weekly_profile` (§3.14)

Supplied for `electricity` at `C-01`, `season = annual`, `profile_year = 2024`, 336 half-hourly
points normalised so the week's maximum is 1, with `annual_peak = 16.2 MW` recorded separately.
Not tabulated here. §3.14's rule is load-bearing at this site: the representative week's own
maximum is 15.4 MW, and using it as the site peak would understate the connection question by
5%. The week gives the *shape*; `annual_peak` carries the *level*.

Gas at `C-02` has no weekly profile, so the premise is reported as having partial shape
coverage rather than `profile_base_year_missing` (§3.1.1), which applies only where no
profile exists at the base year at all.

### 1.10 `process_load_shape` (§3.13)

| `process_id` | `shape_class` | `duty_factor` | `peak_to_mean` | `runs_when_idle` | `seasonality` |
|---|---|---|---|---|---|
| `quarrying_crushing` | throughput_following | 0.85 | 1.30 | false | none |
| `raw_grinding_blending` | throughput_following | 0.95 | 1.20 | false | none |
| `raw_meal_homogenisation` | standing | 1.00 | 1.05 | **true** | none |
| `kiln_pyroprocessing` | flat | 1.00 | 1.05 | false | none |
| `clinker_cooling` | flat | 1.00 | 1.05 | false | none |
| `cement_grinding` | throughput_following | 0.90 | 1.25 | false | none |
| `packing_dispatch` | intermittent | 0.35 | 3.00 | false | none |
| `site_services` | standing | 1.00 | 1.00 | **true** | none |

§3.13's rule holds: the two `standing` rows carry `runs_when_idle = true` and every other row
false. That distinction is what makes the works' peak differ from its energy — the homogenising
silo blowers and the site services run through the three shutdown weeks and the crushers do
not.

### 1.11 Reference data this premise reads

**Carriers (§3.4).** Nine rows are in play. Grades are carriers, not an attribute of one.

| `carrier_id` | `carrier_kind` | `is_gradeable` | `grade_rank` | `is_indirect` | `denominator_kind` |
|---|---|---|---|---|---|
| `coal` | primary | no | — | no | energy |
| `natural_gas` | primary | no | — | no | energy |
| `waste_derived_fuel` | primary | no | — | no | energy |
| `fuel_oil` | primary | no | — | no | energy |
| `electricity` | primary | no | — | **yes** | energy |
| `motive_power` | intermediate | no | — | no | energy |
| `clinker` | product | no | — | no | **mass** |
| `cement` | product | no | — | no | **mass** |
| `co2_process` | **emission** | no | — | no | **mass** |
| `co2_fuel_fossil` | **emission** | no | — | no | **mass** |
| `co2_fuel_biogenic` | **emission** | no | — | no | **mass** |
| `co2_captured` | product | no | — | no | **mass** |

Twelve carriers, four of them emissions. `carrier_kind` is load-bearing (§3.4, §7): a unit
consuming `motive_power` produces no CO₂ at all, because the electricity that made it was
already charged upstream.

**The emission carriers and what they carry (D15):**

| `carrier_id` | `carbon_charge` | `may_dispose` | Produced by |
|---|---|---|---|
| `co2_process` | **charged** | yes | The kiln units, declared at 0.52500 Mt per Mt clinker (§3.6 — stoichiometry) |
| `co2_fuel_fossil` | **charged** | yes | Every combusting unit, **derived** by A6 from its fuel coefficient × factor × (1 − biogenic fraction) |
| `co2_fuel_biogenic` | **zero_rated** | yes | The waste-fuel kiln only, at this premise |
| `co2_captured` | — | **no** | The capture train; leaves through the CO₂ transport network under C9 |

**Waste-derived fuel is the carrier that makes the split earn its keep.** It carries
`emission_factor` 92.0 kt/PJ **gross** and `biogenic_fraction` **0.5109**, so A6 derives a
fossil coefficient against 92.0 × 0.4891 = 44.9972 kt/PJ and a biogenic one against
92.0 × 0.5109 = 47.0028. Every other fuel here has `biogenic_fraction` 0 and generates a
fossil coefficient only. Before D15 this site's waste fuel carried a single net factor of
45.0 kt/PJ, and the 71.93 kt of biogenic CO₂ inside it was invisible — which is exactly the
quantity that turns capture net-negative in §8.4.

**`motive_power` is a carrier, and it has to be.** The `MOT` (motors) duty's carrier cannot be
`electricity`, because C8 (carrier balance) would then have the motor unit consuming and
producing the same carrier and the node would be circular. A duty is a *service*, so the
motor consumes `electricity` and produces `motive_power`; the same holds for `cooling` on a
`REF` (refrigeration) duty. This is forced by C8's algebra and is recorded in §13 as an open
point, because §3.4 does not say it.

**Units (§3.5), the rows this premise can reach.** Capacity units follow `D5`: Mt/yr for
chemistry, PJ/yr for energy services, MW for PV and storage.

| `unit_id` | `unit_class` | `spine` | key | **fuel** | `capex` | `fixed_opex` | `L` | `α` | `γ` | `λ` area |
|---|---|---|---|---|---|---|---|---|---|---|
| `kiln_dry_coal` | converter | chemistry | `ICMCLK` | **coal** | 260 £m/(Mt/yr) | 8.00 | 40 | 0.90 | 1.0 | — |
| `kiln_dry_gas` | converter | chemistry | `ICMCLK` | **natural_gas** | 252 | 7.60 | 40 | 0.90 | 1.0 | — |
| `kiln_dry_wdf` | converter | chemistry | `ICMCLK` | **waste_derived_fuel** | 274 | 9.10 | 40 | 0.90 | 1.0 | — |
| `kiln_fluidbed_wdf` | converter | chemistry | `ICMCLK` | waste_derived_fuel | 295 | 9.20 | 40 | 0.88 | 1.0 | — |
| `kiln_calcium_looping_coal` | converter | chemistry | `ICMCLK` | coal | 430 | 16.50 | 30 | 0.88 | 1.0 | — |
| `ccs_amine` | abatement | chemistry | `ICMCLK` | **natural_gas** | 190 £m/(Mt/yr) | 9.50 | 25 | 0.90 | 1.0 | — |
| `ccs_amine_mdea` | abatement | chemistry | `ICMCLK` | natural_gas | 205 | 8.80 | 25 | 0.90 | 1.0 | — |
| `ccs_oxyfuel` | abatement | chemistry | `ICMCLK` | electricity | 240 | 11.00 | 25 | 0.90 | 1.0 | — |
| `ccs_oxyfuel_partial` | abatement | chemistry | `ICMCLK` | electricity | 165 | 7.90 | 25 | 0.90 | 1.0 | — |
| `grinder_mixer_elec` | converter | chemistry | `ICM` | **electricity** | 45 £m/(Mt/yr) | 1.50 | 25 | 0.92 | 1.0 | — |
| `grinder_mixer_clinker_sub_elec` | converter | chemistry | `ICM` | electricity | 58 | 1.70 | 25 | 0.92 | 1.0 | — |
| `cement_lowcarbon_elec` | converter | chemistry | `ICM` | electricity | 112 | 3.40 | 25 | 0.90 | 1.0 | — |
| `motor_elec` | converter | service | `MOT` | **electricity** | 3.2 £m/(PJ/yr) | 0.35 | 20 | 0.95 | 1.0 | — |
| `pv_rooftop` | generator | service | — | — | 0.62 £m/MW | 0.011 | 30 | **0.10** | **0.031536** | **6,500 m²/MW** |
| `battery_2h` | storage | service | — | — | 0.58 £m/MW | 0.009 | 15 | 0.95 | 0.031536 | **unset** |

**The kiln is three units, and that is D13 doing its job.** A dry preheater kiln co-fires
coal, gas and waste fuel simultaneously — a genuinely multi-fuel machine — and under D13 it
cannot be one unit. It is modelled as three, each producing clinker into the same duty, and
**the mix becomes a dispatch split rather than a coefficient blend**. Three things follow:

- **The capex is not tripled, but it is not identical either.** C1 is an equality on the
  clinker duty, so the three units' capacities sum to the kiln's rather than each carrying a
  whole one. The cost does move, and deliberately: at §8.1's standing capacities the split
  comes to 0.50379 × 260 + 0.37184 × 274 + 0.07437 × 252 = **£251.611m** against
  0.95 × 260 = **£247.000m** at a single blended rate, because the waste-fuel unit carries the
  £14m per Mt/yr premium its feed handling actually costs and the gas unit its £8m discount.
  That £4.6m difference is the point of D13: a single blended row could not express it.
- **A4's carrier-mix rule becomes a statement about dispatch** (§5.2), not about coefficients
  inside one unit.
- **`unit_eligibility` can now screen one fuel.** A works with no waste-fuel permit is told it
  may run `kiln_dry_coal` and not `kiln_dry_wdf`, which was inexpressible while the three were
  one row.

`ρ` (`emissions_released`) has left this table. Under D15 what is released is not a unit
attribute but the disposal variable $d_{c,t}$, and a capture train's rate is its coefficient
on the CO₂ carriers instead.

`γ` for `pv_rooftop` and `battery_2h` is 8,760 h × 3.6 × 10⁻⁶ PJ/MWh = **0.031536 PJ/yr per
MW**, and the PV capacity factor is carried in `α` = 0.10. `area_per_capacity` is set only on
area-bound units (§3.5): PV carries 6,500 m²/MW, and the battery, being containerised plant,
leaves it **unset** and is outside C12 (siting cap) — as is every kiln, grinder and motor at
this works.

**Coefficients (§3.6), consumed negative, produced positive.** Per unit of the unit's output.

| `unit_id` | `carrier_id` | `coefficient` | `is_primary_output` | `is_fuel_input` | Authored |
|---|---|---|---|---|---|
| `kiln_dry_coal` | `clinker` | **+1.00000** | **yes** | no | declared |
| `kiln_dry_coal` | `coal` | −4.60000 | no | **yes** | declared |
| `kiln_dry_coal` | `electricity` | −0.10871 | no | no | declared |
| `kiln_dry_coal` | `co2_process` | **+0.52500** | no | no | **declared** — stoichiometry |
| `kiln_dry_coal` | `co2_fuel_fossil` | **+435.16000** | no | no | **derived** — 4.60000 × 94.6 × (1 − 0) |
| `kiln_dry_gas` | `clinker` | +1.00000 | **yes** | no | declared |
| `kiln_dry_gas` | `natural_gas` | −4.60000 | no | **yes** | declared |
| `kiln_dry_gas` | `electricity` | −0.10871 | no | no | declared |
| `kiln_dry_gas` | `co2_process` | +0.52500 | no | no | declared |
| `kiln_dry_gas` | `co2_fuel_fossil` | **+258.06000** | no | no | **derived** — 4.60000 × 56.1 |
| `kiln_dry_wdf` | `clinker` | +1.00000 | **yes** | no | declared |
| `kiln_dry_wdf` | `waste_derived_fuel` | −4.60000 | no | **yes** | declared |
| `kiln_dry_wdf` | `electricity` | −0.10871 | no | no | declared |
| `kiln_dry_wdf` | `co2_process` | +0.52500 | no | no | declared |
| `kiln_dry_wdf` | `co2_fuel_fossil` | **+206.98712** | no | no | **derived** — 4.60000 × 92.0 × 0.4891 |
| `kiln_dry_wdf` | `co2_fuel_biogenic` | **+216.21288** | no | no | **derived** — 4.60000 × 92.0 × 0.5109 |
| `ccs_amine` | `co2_captured` | **+1.00000** | **yes** | no | declared |
| `ccs_amine` | `co2_process` | −0.55756 | no | no | declared — the stack's composition, §8.4 |
| `ccs_amine` | `co2_fuel_fossil` | −0.35257 | no | no | declared |
| `ccs_amine` | `co2_fuel_biogenic` | −0.08987 | no | no | declared |
| `ccs_amine` | `natural_gas` | −1.90000 | no | **yes** | declared |
| `ccs_amine` | `electricity` | −0.35000 | no | no | declared — **auxiliary, and `primary`** |
| `ccs_amine` | `co2_fuel_fossil` | **⚠ see below** | no | no | the derived reboiler row **collides with the declared capture row above** |
| `grinder_mixer_elec` | `cement` | **+1.00000** | **yes** | no | declared |
| `grinder_mixer_elec` | `clinker` | −0.75221 | no | no | declared |
| `grinder_mixer_elec` | `electricity` | −0.14124 | no | **yes** | declared |
| `motor_elec` | `motive_power` | **+1.00000** | **yes** | no | declared |
| `motor_elec` | `electricity` | −1.00000 | no | **yes** | declared |
| `pv_rooftop` | `electricity` | **+1.00000** | **yes** | no | declared |

Each kiln unit consumes **4.60000 PJ per Mt clinker**, a published best-available-technology
dry-kiln figure, of its own single fuel. `V2` (round-trip against
`capacity_to_activity_factor`) holds on every row; no unit here draws ambient heat, so its
exemption is not needed.

**The capture train is what settles §3.6's fuel rule.** `ccs_amine` consumes reboiler gas
**and** auxiliary grid electricity, and both are `primary` carriers. Only the gas carries
`is_fuel_input`; the electricity is an auxiliary and is not counted against D13. A rule
phrased as "one primary carrier per unit" would have rejected every capture train in the
library, which is why §3.6 is phrased on the fuel input instead.

**⚠ The capture train needs two coefficients on one carrier, and the schema has room for
one.** `ccs_amine` *consumes* `co2_fuel_fossil` from the kiln at −0.35257 and *produces* its
own from the reboiler at 1.90000 × 56.1 = +0.10659 Mt per Mt captured. §3.6 keys
`unit_input_output` on `(unit_id, carrier_id)`, so those two rows cannot coexist and the unit
will not load.

Netting them to a single −0.24598 makes it load and **destroys the number that matters**: the
reboiler's 76.78 kt a year would vanish into the capture coefficient, and §8.4's carbon
arithmetic reads it separately. This example therefore states both legs and flags the
collision rather than papering over it. §13 records it, and it is a defect in §3.6 rather than
in this premise: any abatement unit that burns fuel hits it, which is most of them.

The modelling choice underneath is worth keeping either way: the reboiler has its own stack
and is **not** self-capturing. A train recirculating its flue gas would carry a different
coefficient, and the difference is 76.78 kt a year here (§8.4).

**No unit at this works carries an `is_reject` row.** The kiln's exhaust genuinely does dry
raw meal, and representing that needs the reject-heat coefficients of data migration group B5
— which do not exist (`MF-12`, a Should, lands at milestone M6). Until they do, the kiln's
whole fuel is charged to the kiln and the raw mill is a motor duty only. §13 records this.

**`unit_eligibility` (§3.5.1).** `min_duty` is what replaces COMIT's MILP binary, and it
screens in `A2` — outside the LP.

| `unit_id` | `carb3_activity` | `process_id` | `min_duty` | `max_share` | `earliest_year` |
|---|---|---|---|---|---|
| `kiln_dry_coal` | Cement Works | `kiln_pyroprocessing` | 0.15 Mt/yr | — | — |
| `kiln_dry_gas` | Cement Works | `kiln_pyroprocessing` | 0.15 Mt/yr | — | — |
| `kiln_dry_wdf` | Cement Works | `kiln_pyroprocessing` | 0.15 Mt/yr | **0.55** | — |
| `kiln_fluidbed_wdf` | Cement Works | `kiln_pyroprocessing` | 0.40 Mt/yr | — | — |
| `kiln_calcium_looping_coal` | Cement Works | `kiln_pyroprocessing` | **1.20 Mt/yr** | — | 2035 |
| `ccs_amine` | Cement Works | `kiln_pyroprocessing` | 0.25 Mt/yr | — | 2035 |
| `ccs_amine_mdea` | Cement Works | `kiln_pyroprocessing` | 0.25 Mt/yr | — | 2035 |
| `ccs_oxyfuel` | Cement Works | `kiln_pyroprocessing` | 0.50 Mt/yr | — | 2040 |
| `ccs_oxyfuel_partial` | Cement Works | `kiln_pyroprocessing` | 0.30 Mt/yr | — | 2035 |
| `grinder_mixer_elec` | Cement Works | `cement_grinding` | — | — | — |
| `grinder_mixer_clinker_sub_elec` | Cement Works | `cement_grinding` | — | 0.60 | — |
| `cement_lowcarbon_elec` | Cement Works | `cement_grinding` | — | 0.35 | 2035 |
| `motor_elec` | Cement Works | *(six electric processes)* | — | — | — |
| `pv_rooftop` | Cement Works | — | — | — | — |
| `battery_2h` | Cement Works | — | — | — | — |

### 1.12 `activity_default_unit` (§3.16) — what the activity already has

| `process_id` | `duty_family` | `unit_id` | `default_share` | `sizing_basis` | `evidence_tier` |
|---|---|---|---|---|---|
| `kiln_pyroprocessing` | `ICMCLK` | `kiln_dry_coal` | 0.53 | throughput | derived |
| `kiln_pyroprocessing` | `ICMCLK` | `kiln_dry_wdf` | 0.39 | throughput | derived |
| `kiln_pyroprocessing` | `ICMCLK` | `kiln_dry_gas` | 0.08 | throughput | derived |
| `cement_grinding` | `ICM` | `grinder_mixer_elec` | 1.00 | throughput | derived |
| *(six electric processes)* | `MOT` | `motor_elec` | 1.00 | duty_annual | assumed |

Shares sum to 1.00 per `(activity, set, process, duty_family)` as §3.16 requires, and every
row has a `unit_eligibility` entry, which §3.16 makes a precondition. **This premise never
consults these rows**, because §1.5 names the kiln's unit directly and `D10` puts site
knowledge above the activity default; they are shown because the table is what the same
premise would fall back to, and because §11 of the
[food and drink example](2026-08-28-carb3-site-energy-system-worked-example-food-drink.md)
turns on a CHP that only this entity can assert.

---

## 2. `A1` — ingest and validate

Ten checks, all passing.

| # | Check | Result |
|---|---|---|
| 1 | `nation` is England — in scope under `D8` (Great Britain scope) | pass |
| 2 | `carb3_activity` is one of the 55 Factory-class activities (`D1`) | pass |
| 3 | Base-year energy sums to 4.38000 PJ/yr > 0 | pass — not `no_energy` |
| 4 | No duplicate `(premise_id, carrier_id, connection_id, data_year)` | pass — not `duplicate_year_row` |
| 5 | A `premise_throughput` row exists, as a mass-denominated activity requires | pass — not `missing_throughput` |
| 6 | `commissioned_year` 2004 ≤ `data_year` 2024; cohort shares sum to 1.00 | pass — not `vintage_in_future` / `vintage_shares_unbalanced` |
| 7 | `construction_year` 1957 ≤ `data_year`; `last_refurbishment_year` 2011 between them | pass |
| 8 | `premise_process_detail` intervals per `(premise, process)` are disjoint, and at least one is valid at 2024 | pass — not `process_intervals_overlap` / `no_process_valid_in_base_year` |
| 9 | `premise_measured_emissions` has a base-year row | pass — not `emissions_year_unmatched` |
| 10 | Profile statistics reconcile with energy at 2024, within 5% | pass — not `profile_energy_inconsistent` |

Two things are **reported rather than failed**:

- `waste_derived_fuel` has no base-year row and substitutes from 2023;
  `year_evidence_tier = substituted` is carried to every output row.
- `solid_biomass` was not assessed, so carrier coverage is **incomplete**: four of the five
  main vectors are stated, plus a `waste_derived_fuel` row on the `other` vector, which sits
  outside the five-vector coverage metric.

The premise is assigned to the nearest of the nine in-scope GB clusters, `humber`.
**Accepted.**

---

## 3. `A2` — duties and candidate units

### 3.1 The process set

`premise_process_detail` has rows, so `D10` tier 1 applies and the register's default set is
not consulted:

```
process_evidence_tier = "site_known"
process set, as at the base year 2024 =
    { quarrying_crushing, raw_grinding_blending, raw_meal_homogenisation,
      kiln_pyroprocessing, clinker_cooling, cement_grinding,
      packing_dispatch, site_services }
```

Eight processes. `kiln_pyroprocessing`'s 1957–2003 interval and the register's ninth process
`quarry_mobile_plant` are both outside the set, for the reasons in §1.5. `V11` (process sets
resolve to exactly one tier per premise) passes: tier 1 resolved, and neither the named-set
tier nor the activity-default tier was consulted.

### 3.2 `process_duty` (§3.9) — what the premise must produce

| `process_id` | `duty_family` | `carrier_id` | `grade_rank` | `quantity` | `evidence_tier` |
|---|---|---|---|---|---|
| `kiln_pyroprocessing` | `ICMCLK` | `clinker` | — | **0.85000 Mt/yr** | `site_known` |
| `cement_grinding` | `ICM` | `cement` | — | **1.13000 Mt/yr** | `site_known` |
| `raw_grinding_blending` | `MOT` | `motive_power` | — | 0.10080 PJ/yr | `site_known` |
| `raw_meal_homogenisation` | `MOT` | `motive_power` | — | 0.02520 PJ/yr | `site_known` |
| `quarrying_crushing` | `MOT` | `motive_power` | — | 0.02100 PJ/yr | `site_known` |
| `packing_dispatch` | `MOT` | `motive_power` | — | 0.02100 PJ/yr | `site_known` |
| `clinker_cooling` | `MOT` | `motive_power` | — | **0.00000 PJ/yr** | `site_known` |
| `site_services` | `MOT` | `motive_power` | — | **0.00000 PJ/yr** | `site_known` |

No row carries a `grade_rank`, because no carrier at this works is gradeable — the structural
point of §13 of the specification, and the reason cement alone cannot demonstrate the model's
mechanism.

**The two chemistry duties are masses**, read straight from `premise_throughput` under `D5`.
The energy duties are derived from the premise's metered energy by the published process
shares in
[`activity_process_energy_profile.csv`](../notes/data/activity_process_energy_profile.csv),
which is keyed `(carb3_activity, process_set_id, process_id, vector)` and carries an
`energy_share` summing to 1.00 ± 0.015 down the **process** column **for each vector**. The
`Cement Works` rows, verbatim:

| `vector` | `process_id` | `energy_share` | `evidence_tier` | `confidence` |
|---|---|---|---|---|
| `coal` | `kiln_pyroprocessing` | **1.00** | published_sec | high |
| `gas` | `kiln_pyroprocessing` | **1.00** | published_sec | medium |
| `other` | `kiln_pyroprocessing` | **1.00** | published_sec | high |
| `biomass` | `kiln_pyroprocessing` | **1.00** | published_sec | high |
| `oil` | `quarry_mobile_plant` | 0.80 | engineering | medium |
| `oil` | `kiln_pyroprocessing` | 0.20 | engineering | medium |
| `electricity` | `cement_grinding` | **0.38** | published_sec | medium |
| `electricity` | `raw_grinding_blending` | **0.24** | published_sec | medium |
| `electricity` | `kiln_pyroprocessing` | **0.22** | published_sec | medium |
| `electricity` | `raw_meal_homogenisation` | 0.06 | published_sec | medium |
| `electricity` | `packing_dispatch` | 0.05 | published_sec | medium |
| `electricity` | `quarrying_crushing` | 0.05 | published_sec | medium |

**This table is the missing link, and it already exists.** It is keyed on `vector`, so a
process that draws several sources gets one row per source — the kiln takes all of four
vectors, a fifth of the oil and a fifth of the electricity — and 104 of the 359 processes it
covers carry more than one. Applied to §1.2's base-year quantities:

| `vector` | Premise PJ/yr | Process | Share | PJ/yr | Goes to |
|---|---|---|---|---|---|
| `coal` | 2.10000 | `kiln_pyroprocessing` | 1.00 | **2.10000** | the `ICMCLK` duty, as a kiln input coefficient |
| `gas` | 0.31000 | `kiln_pyroprocessing` | 1.00 | **0.31000** | as above |
| `other` | 1.55000 | `kiln_pyroprocessing` | 1.00 | **1.55000** | as above |
| `oil` | 0.00000 | `kiln_pyroprocessing` | **1.00** after R2 | **0.00000** | as above |
| `electricity` | 0.42000 | `kiln_pyroprocessing` | 0.22 | **0.09240** | as above |
| | | `cement_grinding` | 0.38 | **0.15960** | the `ICM` duty, as a grinder input coefficient |
| | | `raw_grinding_blending` | 0.24 | **0.10080** | the `MOT` duty |
| | | `raw_meal_homogenisation` | 0.06 | **0.02520** | the `MOT` duty |
| | | `packing_dispatch` | 0.05 | **0.02100** | the `MOT` duty |
| | | `quarrying_crushing` | 0.05 | **0.02100** | the `MOT` duty |
| | | `clinker_cooling` | **no row** | **0.00000** | — |
| | | `site_services` | **no row** | **0.00000** | — |

The `MOT` duty is therefore **0.16800 PJ/yr**, and the two chemistry units' electricity is
0.09240 and 0.15960, which is where §1.11's coefficients come from: 0.09240 ÷ 0.85000 =
**0.10871** PJ per Mt clinker and 0.15960 ÷ 1.13000 = **0.14124** PJ per Mt cement. The three
sum to 0.42000 exactly — the split is an allocation of the meter, so it closes by
construction, and the only residual left is the 1.26% between the kiln's metered fuel and its
coefficient (§5.1).

**R2 renormalisation is exercised on the oil vector.** §1.5 puts this premise at `D10` tier 1
with `quarry_mobile_plant` outside the metered boundary, so the activity's oil split
{quarry 0.80, kiln 0.20} renormalises over the processes that remain to {kiln 1.00} — the
rule the archived baseline states at §3.3.3 as R2, for processes that are absent. It moves
nothing here because the premise burns no oil, which is the point of running it anyway: the
mechanism is visible on a vector where an error would cost nothing.

> **Two of this activity's nine processes carry no energy row at all.** `clinker_cooling` and
> `site_services` are in the register and absent from the profile, and because `energy_share`
> sums to 1.00 per vector, absence is unambiguously **zero** rather than "not assessed". So
> the model gives a clinker cooler no electricity. Cooler fans are a real and continuous load
> — §1.10 classes the cooler `flat` with `duty_factor` 1.00 — so this is a gap in the
> reference data, not a statement about cement works. Seventeen of the register's 376
> processes are in the same position. Closing them is a `T17` (duty families and heat grades)
> follow-on, and until then the `MOT` duty at every cement works is understated and the shares
> of the six processes that do carry rows are correspondingly overstated.

> **The specification rules this table out as an input, and that is the defect.** §3.3 calls
> it "the 490-row fuel split" and makes it `V1b`'s **parity target**, never an input, on the
> ground that supplying a fuel split alongside a duty split over-determines the problem. The
> reasoning is right and the target is wrong: this is a process × vector **marginal** — of the
> premise's gas, what share goes to the kiln — which is a demand-side fact about the site's
> layout. What `V1b` compares is the **conditional over time**: in 2040, is a duty served by
> gas, hydrogen or electricity. Reading the marginal over-determines nothing, because at the
> base year the per-carrier totals are pinned by the meter on both sides anyway (C8 forces
> import to equal consumption); what it fixes is the duty structure that drives every later
> period. It is also the natural source for §4.1's tier 3 `activity_default` mix, which today
> names no table at all. §13 records the change §3.3 needs.

### 3.3 The candidate unit set, and the lineage it is read through

`Cement Works` reaches **11 of COMIT's 397 technology rows**, eight on `ICMCLK` and three on
`ICM`. Under the unit spine (§3.5) they dispose as follows, and every one of the eleven has
exactly one disposition — the property `MF-03` (unit collapse plus lineage table) makes a
gate and `V1b` compares through:

| COMIT `technology_code` | Name | Disposition |
|---|---|---|
| `ICMKLND01` | Dry kiln, best available technology | **split by fuel (D13)** into `kiln_dry_coal`, `kiln_dry_gas` and `kiln_dry_wdf` |
| `ICMKLNWST02` | Fluidised bed kiln with waste utilisation | **preserved** as `kiln_fluidbed_wdf` |
| `ICMKLNCLQ01` | Calcium looping kiln | **preserved** as `kiln_calcium_looping_coal` |
| `ICMKLNMAQ02` | Advanced amine (MDEA) BAT kiln, CCS | **collapsed** into `kiln_dry_coal` + `ccs_amine_mdea` |
| `ICMKLNOXQ01` | BAT kiln full oxyfuel, CCS | **collapsed** into `kiln_dry_coal` + `ccs_oxyfuel` |
| `ICMKLNPOQ01` | Partial oxyfuel dry kiln, CCS | **collapsed** into `kiln_dry_coal` + `ccs_oxyfuel_partial` |
| `ICMKLNMNQ01` | Dry kiln with natural gas CHP and MEA CCS | **collapsed** into `kiln_dry_gas` + `chp_gas_turbine` + `ccs_amine` |
| `ICMKLNMCQ01` | Dry kiln with coal CHP and MEA CCS | **collapsed** into `kiln_dry_coal` + `chp_coal_st` + `ccs_amine` |
| `ICMLOCARB01` | Alternative low carbon cement | **preserved** as `cement_lowcarbon_elec` |
| `ICMGRIMIX01` | Grinding and mixing technology | **preserved** as `grinder_mixer_elec` |
| `ICMGRIMIX02` | Grinder and mixer, increased clinker substitution | **preserved** as `grinder_mixer_clinker_sub_elec` |

**Eleven source rows become fourteen units, and the direction is the point.** Cement is the one
place in the library where the collapse *expands*: five of the eleven rows are bundles of a
kiln, a capture train and sometimes a CHP sold as one technology, and unbundling them is what
lets the model retrofit capture onto the kiln it already has rather than rebuilding the kiln
to acquire capture. It is also why `chp_gas_turbine` and `chp_coal_st` appear at a cement
works at all — fused inside two capture rows, invisible as plant. The fourteen units are the three
per-fuel dry kilns, `kiln_fluidbed_wdf`, `kiln_calcium_looping_coal`, four capture units,
`grinder_mixer_elec`, `grinder_mixer_clinker_sub_elec`, `cement_lowcarbon_elec`, and the two
CHP units `chp_gas_turbine` and `chp_coal_st`.

**Two of the fourteen are not reachable by this premise, and are not in §1.11.** A CHP serves
an `STM` (steam) duty, and a cement works has none — the bundles' CHP is a utility for the
capture train's reboiler, not plant serving a duty. `chp_gas_turbine` is defined in the
[food and drink example](2026-08-28-carb3-site-energy-system-worked-example-food-drink.md)
§1.11, where it does serve a duty; `chp_coal_st` is defined nowhere yet and is Group B
migration work. So this premise's candidate set is the **twelve** units §1.11 lists, out of
fourteen the lineage produces.

The seven `ICMCLK` capture and kiln archetypes are part of data migration B2's floor of
**57 non-fuel technologies** (25 CCS, 31 heat pump, 1 dry kiln) that must survive the
collapse as distinct units.

### 3.4 `min_duty` screening, which happens here and not in the LP

| Unit | `min_duty` | Premise duty | Offered? |
|---|---|---|---|
| `kiln_dry_coal` | 0.15 Mt/yr | 0.85 Mt/yr | yes |
| `kiln_dry_gas` | 0.15 | 0.85 | yes |
| `kiln_dry_wdf` | 0.15 | 0.85 | yes, capped at `max_share` 0.55 |
| `kiln_fluidbed_wdf` | 0.40 | 0.85 | yes |
| `kiln_calcium_looping_coal` | **1.20** | 0.85 | **no — screened out** |
| `ccs_amine` | 0.25 | 0.85 | yes, from 2035 |
| `ccs_amine_mdea` | 0.25 | 0.85 | yes, from 2035 |
| `ccs_oxyfuel` | 0.50 | 0.85 | yes, from 2040 |
| `ccs_oxyfuel_partial` | 0.30 | 0.85 | yes, from 2035 |

Calcium looping needs a works half again the size of this one and is never in $U_q$, so no
variable is created for it. COMIT would have introduced a binary per technology per site to
express the same thing (`R/fct_constraints_hydrogen.R:650`,
`R/fct_decision_variables.R:597`); at stock scale that is the tractability problem `D7`
(infrastructure exogenous) was taken to avoid. The decision is made here, outside the LP, and
the site is **reported** if its optimal size later lands below a credible minimum.

`V19` (no unit is eligible for a duty above its `grade_out`) is vacuously satisfied at this
premise, because no duty carries a grade. It is a load-scope test and passes on the reference
data as a whole, not on this fixture.

---

## 4. `A3` — allocate premise energy onto carriers

`premise_energy` already names its carriers, so `A3` is close to an identity here: it maps
each row's `(carrier_id, vector)` onto a `carrier` row, checks that the vector agrees with
`carrier_kind` (§3.1.1), and hands on the base-year quantities.

| `carrier_id` | Base-year quantity | Source year | `year_evidence_tier` |
|---|---|---|---|
| `electricity` | 0.42000 PJ/yr | 2024 | `base_year` |
| `coal` | 2.10000 | 2024 | `base_year` |
| `natural_gas` | 0.31000 | 2024 | `base_year` |
| `waste_derived_fuel` | 1.55000 | **2023** | **`substituted`** |
| `fuel_oil` | 0.00000 | 2024 | `base_year` |
| `solid_biomass` | — | — | **`absent`** |

**`A3` does not allocate energy across processes**, and that is the live specification's
change from the COMIT-parity baseline, which did. Which process burns what is decided by C8
(carrier balance), not by a profile applied up front. At this works the answer is forced
rather than chosen — the kiln is the only unit eligible to consume coal, gas or waste-derived
fuel — but it is forced by the balance, not asserted by `A3`.

---

## 5. `A4` — back-solve capacity, carrier mix and vintage

### 5.1 Capacity, or utilisation

§3.10's precedence rule applies: `known_capacity` is given, so `A4` back-solves **utilisation**
rather than capacity.

```
kiln thermal input, metered   = 2.10000 + 0.31000 + 1.55000       = 3.96000 PJ/yr
kiln thermal coefficient      |ι| = 4.60000 PJ per Mt clinker
implied clinker output        = 3.96000 / 4.60000                 = 0.86087 Mt/yr
declared throughput                                               = 0.85000 Mt/yr
known_capacity (permit)                                           = 0.95000 Mt/yr
utilisation = duty / (capacity × γ) = 0.85000 / (0.95000 × 1.0)    = 0.89474
```

Three checks, and all three pass:

| Check | Basis | Result |
|---|---|---|
| Utilisation ≤ `availability_factor` | 0.89474 ≤ 0.90 | pass — not `capacity_energy_inconsistent` |
| Implied output vs declared throughput | 0.86087 vs 0.85000 | **1.28% apart** — profile and coefficients agree |
| Utilisation vs operating schedule | continuous, 8,400 h/yr vs 0.89474 | pass — not `utilisation_schedule_inconsistent` |

The two checks use different bases deliberately. Utilisation is computed against the *duty*,
which is a measured throughput, so it is the figure the LP must reproduce. The 1.28% is the
independent cross-check between the meter and the coefficient, and it is the source of the
base-year reconciliation gap in §10. The third check exists only because the schedule was
supplied: a continuous works back-solving to 0.89 is credible; the same works back-solving to
0.2 would have signalled an error in the capacity, the coefficients or the energy, and no
other input could have said which.

`grinder_mixer_elec` has no `known_capacity`, so its capacity **is** back-solved:
1.13000 ÷ 0.92 = **1.22826 Mt/yr**. `motor_elec` likewise: 0.16800 ÷ 0.95 = **0.17684 PJ/yr**.

### 5.2 The carrier mix (§4.1)

The kiln may burn a mix, so the same metered energy is consistent with many
`(capacity, mix)` pairs and the mix must be pinned from evidence rather than solved for.
Tiers are tried in order and exactly one resolves:

| Tier | Test at this premise | Resolves? |
|---|---|---|
| 1 — `site_known` | `premise_process_detail` names a kiln unit but not the split across the three | **no** |
| 2 — `carrier_bounded` | `premise_energy` gives site totals per carrier, and **exactly one kiln unit consumes each** of coal, gas and waste fuel | **yes** |
| 3 — `activity_default` | not reached | — |

```
mix_evidence_tier = "carrier_bounded"
coal                  2.10000 / 3.96000 = 0.53030
natural_gas           0.31000 / 3.96000 = 0.07828
waste_derived_fuel    1.55000 / 3.96000 = 0.39141
                                          ───────
                                          1.00000  (0.99999 at five places)
```

**Under D13 the mix is a dispatch split, not a coefficient blend.** Before, one kiln carried
three fuel coefficients and A4 chose their proportions. Now each kiln unit burns one fuel at
4.60000 PJ per Mt, and A4 divides the clinker duty between them:

| Unit | Share | $z_{u,\text{ICMCLK},0}$ (Mt) | Fuel drawn (PJ) |
|---|---|---|---|
| `kiln_dry_coal` | 0.53030 | **0.450756** | 0.450756 × 4.60000 = **2.073478** |
| `kiln_dry_wdf` | 0.39141 | **0.332699** | **1.530415** |
| `kiln_dry_gas` | 0.07828 | **0.066538** | **0.306075** |
| **Total** | **1.00000** | **0.849993** | **3.909968** |

The totals are the same as a blended kiln would have given — 0.85000 Mt of clinker on
3.91000 PJ of fuel — which is the point: D13 changes how the mix is *expressed*, not what it
is. What it adds is that each unit now carries its own capex, its own eligibility and, in
§8.4, **its own CO₂ carriers**, which is what makes the waste fuel's biogenic share visible at
all.

**Tier 2 is reached cleanly here precisely because of D13.** Each fuel has exactly one
consumer at this premise, so each share is determined by division and none of it is assumed.
Under the old multi-fuel unit the same division worked, but §4.1's warning about several units
sharing a carrier was one unit away from biting. `V23` passes on all three properties, and
`V27` (at most one `is_fuel_input` per unit) passes on each of the three kiln units.

The mix also inherits `waste_derived_fuel`'s `year_evidence_tier = substituted`: 39.1% of the
kiln's fuel is pinned from a 2023 reading, and every output row says so.

### 5.3 Vintage (`D11`)

Scenario `central` runs 2025 to 2050 in five-year periods, so $t_0$ = 2025, $\Delta$ = 5, and
$N$ = 5. The stranding factor is $\xi$ = 1.0. Lifetimes convert to periods before use:
$\ell_{\text{kiln}} = \lceil 40/5 \rceil = 8$ periods. Reading 40 as a period offset would
give a 200-year asset.

Tiers resolve per unit, not per premise:

| Process | Tier | Age at 2025 | Why |
|---|---|---|---|
| `kiln_pyroprocessing` | `process_known` | point mass, 21 years | §1.6 gives the cohort year, 2004 |
| The other seven | `premise_bounded` | [0, 40] | No cohort row, so the 1957 construction year applies; the bound is slack, so the window matches the default tier's — but the label records that the evidence was consulted |

For the kiln, the final operating year is 2004 + 40 − 1 = **2043**:

| | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|
| Elapsed years τ | 0 | 5 | 10 | 15 | 20 | 25 |
| Survival η | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 |
| Standing capacity $e_{u,t}$ (Mt/yr) | 0.95000 | 0.95000 | 0.95000 | 0.95000 | 0 | 0 |
| Mean remaining life R̄ (yr) | 19 | 14 | 9 | 4 | 0 | 0 |
| Stranding rate κ·ξ·R̄/L (£m per Mt/yr) | 123.500 | 91.000 | 58.500 | 26.000 | 0 | 0 |
| Write-off if scrapped whole (£m) | **117.325** | **86.450** | **55.575** | **24.700** | 0 | 0 |

A point mass has no spread, so R̄ is exact rather than a pool average: at 2035 the rate is
£260m × 1.0 × 9 ÷ 40 = £58.500m per Mt/yr, and the write-off is that times 0.95000 Mt/yr.

**The same kiln at the fallback tier**, had §1.6 been absent — the uniform survival function
that reproduces COMIT's linear decay, and the only tier the MVP implements (`MF-43`, C4 at
the fallback tier only):

| | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|
| Survival η = 1 − τ/L | 1.000 | 0.875 | 0.750 | 0.625 | 0.500 | 0.375 |
| Standing capacity (Mt/yr) | 0.95000 | 0.83125 | 0.71250 | 0.59375 | 0.47500 | 0.35625 |
| Mean remaining life R̄ = (L − τ)/2 | 20.0 | 17.5 | 15.0 | 12.5 | 10.0 | 7.5 |
| Stranding rate (£m per Mt/yr) | 130.000 | 113.750 | 97.500 | 81.250 | 65.000 | 48.750 |

The two survival paths could hardly be less alike, and one line on a permit decides which the
site gets. Meeting the duty of 0.85000 Mt/yr at an availability factor of 0.90 needs
**0.94444 Mt/yr** of standing capacity. At tier 1 the kiln clears that until it dies in 2043.
At the fallback tier it falls to 0.83125 Mt/yr by **2030** — a shortfall of 0.11319 Mt/yr,
five years before CO₂ transport arrives, forcing a piecemeal unabated rebuild the site would
then be carrying when capture becomes available. Both are defensible readings of a *fleet* of
kilns; only one is a reading of *this* kiln.

`V17` (vintage and stranding per unit; an abatement unit inherits its host's remaining life
and strands nothing while the host stands) is asserted in §7 and §11.

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

The offset is recorded rather than silently absorbed (§3.1.1): the premise's 2024 quantities
are read as representing period 0, and every output row says the base year sat one year
before it. That is what stops a 2025 carbon price being applied to a 2024 calendar year
without trace.

### 6.2 `infrastructure_scenario` (§3.7), cluster `humber`, `D7`

| `carrier` | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 | `unit_tariff` |
|---|---|---|---|---|---|---|---|
| `co2_transport` | false | false | **true** | true | true | true | £18.00m per Mt from 2035 |
| `hydrogen` | false | false | false | false | false | false | — |
| `grid_headroom` | true | true | true | true | true | true | — |

Hydrogen never arrives at this cluster in this scenario, so C9 (infrastructure availability)
removes every hydrogen-consuming unit from the problem at every period. It is exogenous under
`D7` and is not a thing the model decides.

### 6.3 `scenario_parameters` (§3.8)

Import prices, £m per PJ:

| `carrier_id` | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|
| `coal` | 2.60 | 2.70 | 2.80 | 2.90 | 3.00 | 3.10 |
| `natural_gas` | 7.10 | 7.60 | 8.20 | 8.40 | 8.60 | 8.80 |
| `waste_derived_fuel` | 1.00 | 1.10 | 1.20 | 1.30 | 1.40 | 1.50 |
| `electricity` | 32.00 | 29.00 | 26.00 | 25.00 | 24.00 | 23.50 |

Export prices, £m per PJ, and the wedge `V21` (the export price is strictly below the import
price for every carrier and period) asserts at load:

| `carrier_id` | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|
| `electricity` | 19.00 | 17.00 | 15.00 | 14.50 | 14.00 | 13.50 |

Carbon price $\pi_t$, £/t: **90, 125, 165, 205, 240, 275**.

Emission factors, kt CO₂ per PJ:

| `carrier_id` | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 | Note |
|---|---|---|---|---|---|---|---|
| `coal` | 94.6 | 94.6 | 94.6 | 94.6 | 94.6 | 94.6 | direct |
| `natural_gas` | 56.1 | 56.1 | 56.1 | 56.1 | 56.1 | 56.1 | direct |
| `waste_derived_fuel` | **45.0** | 45.0 | 45.0 | 45.0 | 45.0 | 45.0 | direct, **net of biogenic** — gross 92.0, biogenic fraction 0.511 |
| `electricity` | 18.0 | 13.0 | 9.0 | 6.0 | 4.0 | 3.0 | **indirect** (`is_indirect` true) |

Process CO₂: **525 kt per Mt clinker**, on the `co2_process` carrier's mass denominator.
`reinforcement_cost` at 33 kV: **£0.42m per MW**.

> **The objective charges direct carbon only.** §5.4's $Z^{\text{carbon}}_t$ does not say
> whether an `is_indirect` carrier's emissions enter the cost, and §7.4 settles only that
> indirect is excluded from the *comparison*. This example charges direct emissions and
> **reports** indirect ones, consistently in both worked examples. §13 records it as an open
> point.

---

## 7. `A6` — the problem as built

### 7.1 Sets

```
T   = {0,1,2,3,4,5}                             six periods, Δ = 5
Q   = { ICMCLK, ICM, MOT×6 }                    eight duties, of which two are mass
U   = the twelve units of §1.11 (of §3.3's fourteen; two CHPs are unreachable),
      less kiln_calcium_looping_coal (screened, §3.4)
      less every hydrogen unit (C9, §6.2)                                    ⇒ 11 units
U⁰  = { kiln_dry_coal, kiln_dry_gas, kiln_dry_wdf,
        grinder_mixer_elec, motor_elec }                                     incumbents
Ugen= { pv_rooftop }                                                         generators
Uarea = { pv_rooftop }                          area_per_capacity set; battery_2h is NOT
C   = twelve carriers of §1.11
K   = { C-01, C-02 }
```

### 7.2 Variables (§5.2), all continuous and non-negative

| Variable | Count here | Note |
|---|---|---|
| $n_{u,t}$ new capacity | 11 × 6 = 66 | |
| $a_{u,t}$ available capacity | 66 | |
| $z_{u,q,t}$ dispatch to a duty | declared over $u \in U_q$ only: 8 duties × eligible units × 6 | the duty index is what stops one unit being credited twice |
| $z^{\circ}_{u,t}$ released to the balance | 66 | non-zero only for `pv_rooftop` |
| $h_{c \to c',t}$ cascade | **0** | no gradeable carrier at this premise |
| $e_{u,t}$, $r_{u,t}$ incumbent survival and early retirement | 3 × 6 each | over $U^0$ only |
| $m_{c,k,t}$, $x_{c,k,t}$ import and export | per carrier per connection per period | $m = x = 0$ where the connection does not carry $c$ |
| $w_{k,t}$ reinforcement | 2 × 6 | |

**The problem is a pure LP** (§5.2) and stays one: `min_duty` was applied in `A2`, not as a
binary, and `D11`'s survival function η and mean remaining life R̄ are parameters computed
before the build.

### 7.3 Constraints, instantiated

| # | Constraint | Instances here | Binds? |
|---|---|---|---|
| **C1** | Duty satisfaction | 8 duties × 6 periods = 48 | always — it is an equality |
| **C2** | Activity ≤ available capacity × γ × α | 11 × 6 = 66 | on the kiln at 0.89474 utilisation, slack elsewhere |
| **C3** | Capacity transfer between periods | 66 | — |
| **C4** | Incumbent ageing and early retirement (`D11`) | 3 × 6 = 18 | the kiln dies at 2045 |
| **C5** | No building in the start year | 11 | binds — $n_{u,0} = 0$ for every unit |
| **C6** | Unit stability | deferred (`MF-51`, Could) | — |
| **C7** | Known changes | none announced at this premise | — |
| **C8** | **Carrier balance** | 12 carriers × 6 = 72 | always — equalities |
| **C9** | Infrastructure availability | hydrogen false throughout; CO₂ transport from 2035 | binds before 2035 |
| **C10** | Heat grade cascade | **0 rows** | no gradeable carrier |
| **C11** | Connection capacity | 2 × 6 = 12 | **binds at `C-01` from 2035** — §8.3 |
| **C12** | Siting cap | 6 | **binds** — §8.2 |

C10's two sides both vanish here, and that is the honest statement of what a cement works
cannot show. On the duty side there is no `grade_out` to compare against; on the carrier side
there is no gradeable carrier for $h$ to flow between. The
[food and drink example](2026-08-28-carb3-site-energy-system-worked-example-food-drink.md)
is where C10 does work.

### 7.4 Objective (§5.4)

$$\min \; Z = \sum_{t} \Big[\; \delta_t \big( Z^{\text{capex}}_t + Z^{\text{opex}}_t + Z^{\text{fuel}}_t + Z^{\text{carbon}}_t + Z^{\text{infra}}_t + Z^{\text{net}}_t - Z^{\text{exp}}_t \big) \;+\; d_t \, Z^{\text{strand}}_t \;\Big]$$

$Z^{\text{exp}}$ enters negative, so no implementation may assume a cost component is
non-negative — `V6` records the trap. Here the export term is **identically zero** at every
period, because `C-01`'s `export_capacity` is 0 MW; it is still present in the objective, and
`V6` asserts that it is.

Capex is annuitised over $L_u$ at $i$ = 3.5%. The annuity factors used below:

| $L$ | $(1+i)^L$ | Annuity $i/(1-(1+i)^{-L})$ |
|---|---|---|
| 9 | 1.36288 | **0.131446** |
| 15 | 1.67535 | 0.086825 |
| 20 | 1.98979 | 0.070361 |
| 25 | 2.36324 | 0.060674 |
| 30 | 2.80679 | 0.054371 |
| 40 | 3.95926 | 0.046827 |

---

## 8. `A7` — the solve

### 8.1 The base year, 2025, worked in full

C5 forbids building at $t_0$, so period 0 is the back-solved baseline running at the prices
of 2025. Every number below is determined, not chosen.

**Activity and capacity.**

| Unit | $z_{u,0}$ | α | $a_{u,0}$ | Basis |
|---|---|---|---|---|
| `kiln_dry_coal` | 0.450756 Mt | 0.90 | **0.503785 Mt/yr** | permit capacity 0.95000 split on §5.2's shares |
| `kiln_dry_wdf` | 0.332699 Mt | 0.90 | **0.371843 Mt/yr** | as above |
| `kiln_dry_gas` | 0.066538 Mt | 0.90 | **0.074369 Mt/yr** | as above |
| `grinder_mixer_elec` | 1.13000 Mt | 0.92 | **1.228261 Mt/yr** | back-solved |
| `motor_elec` | 0.16800 PJ | 0.95 | **0.176842 PJ/yr** | back-solved |

The three kiln capacities sum to **0.949997 Mt/yr**, the permit's kiln, and each runs at the
same utilisation 0.85000 ÷ 0.95000 = **0.89474**.

**C8, every carrier node, period 0.** Eleven of the twelve nodes close to zero, which is what `V18`
asserts to 1e-6 and `V30` extends to the emission carriers.

| Carrier | Consumed by units | Produced by units | Import $m$ | **Disposal $d$** | Residual |
|---|---|---|---|---|---|
| `coal` | `kiln_dry_coal` −2.073478 | — | +2.073478 | — | **0** |
| `natural_gas` | `kiln_dry_gas` −0.306075 | — | +0.306075 | — | **0** |
| `waste_derived_fuel` | `kiln_dry_wdf` −1.530415 | — | +1.530415 | — | **0** |
| `fuel_oil` | — | — | 0 | — | **0** |
| `electricity` | kilns −0.092404, grinder −0.159600, motor −0.168000 | — | +0.420004 | — | **0** |
| `motive_power` | — | motor +0.168000, all dispatched ⇒ $z^{\circ}=0$ | — | — | **0** |
| `clinker` | grinder −0.850000 | kilns +0.850000, **but all of it dispatched to the `ICMCLK` duty** ⇒ $z^{\circ}=0$ | — | — | **⚠ −0.850000 — does not close** |
| `cement` | — | grinder +1.130000, dispatched | — | — | **0** |
| **`co2_process`** | — | kilns **+446.25000 kt** | — | **−446.25000** | **0** |
| **`co2_fuel_fossil`** | — | coal +196.15102, gas +17.17081, wdf +68.86439 = **+282.18622 kt** | — | **−282.18622** | **0** |
| **`co2_fuel_biogenic`** | — | wdf **+71.93379 kt** | — | **−71.93379** | **0** |
| `co2_captured` | — | no capture before 2035 | — | — | **0** |

Kiln electricity: 0.850000 × 0.10871 = **0.092404**. Grinder: 1.130000 × 0.14124 =
**0.159601**. Motor: **0.168000**. Import **0.420004** against the metered 0.420000,
**+0.001%**.

**Every node closes, and nothing is assumed.** An earlier draft of this example could not
close `co2_process` — the kiln produced 0.44625 Mt that nothing consumed, and C8 admits no
sink — so it asserted an implicit vent the specification did not define. Under D15 and §5.2
the vent is $d_{c,t}$, it is declared, and it is **reported as a quantity**:

| Disposal at 2025 | kt CO₂ | `carbon_charge` | Charged at £90/t |
|---|---|---|---|
| $d_{\text{co2\_process}}$ | 446.25000 | charged | £40.16250m |
| $d_{\text{co2\_fuel\_fossil}}$ | 282.18622 | charged | £25.39676m |
| $d_{\text{co2\_fuel\_biogenic}}$ | **71.93379** | **zero_rated** | **£0.00000m** |
| **Total vented** | **800.37001** | | **£65.55926m** |

That the biogenic 71.93 kt is vented **free** rather than not counted is §7.3 operating at the
carrier level, and it is what makes capturing it a credit rather than a saving in §8.4.

**⚠ The `clinker` node does not close, and no convention available today makes it.** An
earlier draft of this example claimed it did, by releasing the kilns' output to the balance
through $z^{\circ}$ and letting the grinder's draw satisfy the `ICMCLK` duty. That is not
feasible under §5.2 and C1, and the pair of constraints admits no third option:

| If the kilns… | C1 on `ICMCLK` | C8 at `clinker` |
|---|---|---|
| dispatch all 0.85 Mt to the duty ($z^{\circ}=0$) | **satisfied** | **fails** — the grinder's −0.85 has nothing to meet it |
| release all 0.85 Mt to the balance ($z_{u,q}=0$) | **fails** — nothing serves the duty | satisfied |
| do both | satisfied | satisfied, **by counting the same 0.85 Mt twice** — exactly what C8's indicator functions exist to prevent |

The table above shows the first row, because C1 is an equality and cannot be left unmet. So
**this example does not claim C8 closure at `clinker`, and `V18` fails there** until the
specification says how a product carrier reaches a downstream unit rather than a duty. Two
resolutions are plausible and §13 records both; the choice is a design decision, not an
arithmetic one.

Every other node closes to 1e-6.

**The 2025 annual cost, undiscounted.**

| Term | Computation | £m |
|---|---|---|
| $Z^{\text{capex}}$ | C5: $n_{u,0}=0$ | **0.00000** |
| $Z^{\text{opex}}$ | kilns 0.949997 × 8.00 (weighted, §1.11) = 7.60000; grinder 1.228261 × 1.50 = 1.84239; motor 0.176842 × 0.35 = 0.06189 | **9.50428** |
| $Z^{\text{fuel}}$ | coal 2.073478 × 2.60 = 5.39104; gas 0.306075 × 7.10 = 2.17313; WDF 1.530415 × 1.00 = 1.53042; electricity 0.420004 × 32.00 = 13.44013 | **22.53472** |
| $Z^{\text{carbon}}$ | **disposal, not fuel** — (446.25000 + 282.18622) kt × £90/t × 10⁻³ | **65.55926** |
| $Z^{\text{infra}}$ | no CO₂ transport before 2035 | **0.00000** |
| $Z^{\text{net}}$ | $w_{k,0}=0$ | **0.00000** |
| $Z^{\text{exp}}$ | no generation, `export_capacity` 0 MW | **0.00000** |
| $Z^{\text{strand}}$ | nothing retired early | **0.00000** |
| **Total** | | **£97.59826m** |

**The carbon term reads the disposal variable, not the fuel.** It is the same number it would
have been — the kiln burns what it burns — but the route matters at 2035, when capture removes
90% of it without any term in the objective changing form.

Indirect emissions, reported and not charged: 0.420004 × 18.0 = **7.56007 kt**. Under §7.8
these are charged on the **import**, which at this premise is the whole of the site's
electricity because nothing is generated on site until PV arrives in 2030.

### 8.2 C12 and the PV decision

$$\sum_{u \in U^{\text{area}}} \lambda_u\, a_{u,t} \;\le\; \sum_{k \in \mathcal{K}} A_k \qquad \Longrightarrow \qquad 6{,}500 \times a_{\text{pv},t} \;\le\; 16{,}100$$

so $a_{\text{pv},t} \le$ **2.47692 MW**. Area is summed across connections here, unlike
capacity in C11, because roof and land are one estate however many supplies serve them
(§5.5); at this works the whole 16,100 m² proxy sits against `C-01`.

**The sum runs over area-bound units only**, and every other unit at this works is outside it.
One site-wide area density applied to every generator would have capped the kiln, the grinder
and — in the bundled capture rows of §3.3 — the CHP, at the footprint of the PV array that
fits on the same roof. None of those has that constraint. `V12` (capacity bounds hold,
including the siting cap, whose sum runs over area-bound units only) asserts it.

At the cap, PV output is 2.47692 × 0.031536 × 0.10 = **0.00781 PJ/yr**, which is **1.86%** of
the works' 0.42000 PJ of electricity. The decision at 2030:

| | £m/yr |
|---|---|
| Displaced import: 0.00781 × 29.00 | **+0.22649** |
| Annuitised capex: 0.62 × 2.47692 × 0.054371 | −0.08350 |
| Fixed opex: 0.011 × 2.47692 | −0.02725 |
| **Net** | **+£0.11574m/yr** |

PV is built to the area cap from 2030, and it is worth almost nothing to this site. That is
the correct answer for a cement works and it is worth stating plainly: the roof is small
relative to a kiln, and no amount of it changes the problem.

**PV reduces energy but not peak.** Whether rooftop generation is coincident with the site's
maximum demand is what the Tier A coefficient ψ (onsite-generation self-consumption) answers,
and ψ is a `Could` feature gated on the G4 scale gate (`MF-36`, S0 archetype dispatch). Absent
it, C11 in §8.3 takes no credit for PV, which is the conservative reading.

### 8.3 C11 and the connection

C11 is written per connection and never summed across them:

$$P^{\text{peak}}_{k,t} \;\le\; \overline{P}^{\text{imp}}_{k} + w_{k,t} + \sum_{u} \beta_u\,a_{u,t}$$

Peak is rebuilt from the solved pathway by the §5.6 method. **§5.6 is not written** (`T23`),
so this example uses mean import over operating hours multiplied by the observed within-shift
peak factor of §1.8, and states that this **understates** the true peak because it applies no
diversity step and no seasonal correction:

| | 2025 | 2035, with capture |
|---|---|---|
| Electricity import (PJ/yr) | 0.42000 | 0.67212 |
| Mean over 8,400 h (MW) | 13.889 | 22.226 |
| × within-shift peak factor 1.17 (MW) | **16.25** | **26.00** |
| `import_capacity` at `C-01` (MW) | 25.00 | 25.00 |
| Headroom (MW) | +8.75 | **−1.00** |

At 2025 the rebuilt peak of 16.25 MW is within 0.3% of the metered 16.2 MW, which is `V16`'s
assertion (connection peak is rebuilt correctly from the solved pathway) at the base year.
From 2035 the capture train's 0.25212 PJ/yr of electricity pushes the works **1.00 MW past its
connection**, and C11 binds.

The MVP **reports** that overshoot rather than costing it: C11 with the reinforcement variable
is `MF-47` (a Should, landing at milestone M6), and the MVP collects `import_capacity` without
reading it. Once `MF-47` lands, $w_{\text{C-01},t}$ = 1.00 MW at £0.42m/MW = **£0.42m** of
reinforcement, weighed against curtailing capture.

**The battery is not built**, at any period. A standalone battery earns only through β, its
firm-capacity contribution to C11 (`V20` (d): a unit with `is_storage` and no hybrid parent
has β set and ψ, χ, ε unset). At β = 0.35, covering the shortfall — 1.0047 MW before
rounding — needs 2.87 MW of
battery, costing 0.58 × 2.87 × 0.086825 = £0.14453m/yr plus 0.009 × 2.87 = £0.02583m/yr of
opex — **£0.17036m a year against a £0.42m one-off reinforcement**. Reinforcement wins on the
first period. That is the right answer and it is only expressible because β exists.

### 8.4 The capture decision at 2035

CO₂ transport arrives at `humber` in 2035 (§6.2), and `ccs_amine` becomes eligible. **Under
D15 capture needs no special case at all**: the train is a unit that consumes the three CO₂
carriers and produces `co2_captured`. What it does not consume is disposed of, and the carbon
charge falls with it.

The three stack carriers at 2035, unchanged from §8.1 because the kilns are unchanged:

| Carrier | kt CO₂ | Share of stack |
|---|---|---|
| `co2_process` | 446.25000 | 0.55756 |
| `co2_fuel_fossil` | 282.18622 | 0.35257 |
| `co2_fuel_biogenic` | **71.93379** | 0.08987 |
| **Total** | **800.37001** | 1.00000 |

Those three shares are `ccs_amine`'s consumption coefficients in §1.11 — the train takes the
stack as it finds it. At 90% capture:

```
capacity a = captured / α = 720.33301 / 0.90         = 800.37001 kt/yr  ⇒ 0.80037 Mt/yr
z(ccs_amine)                                          = 0.72033 Mt of CO2 captured
  co2_process           446.25000 x 0.90             = 401.62500 kt    vented  44.62500
  co2_fuel_fossil       282.18622 x 0.90             = 253.96760 kt    vented  28.21862
  co2_fuel_biogenic      71.93379 x 0.90             =  64.74041 kt    vented   7.19338
```

**§7.3 now falls out of the carrier set rather than being applied to it.** The objective's
carbon term at 2035:

| Component | kt CO₂ | Rate |
|---|---|---|
| $d_{\text{co2\_process}}$, vented | +44.62500 | charged |
| $d_{\text{co2\_fuel\_fossil}}$, vented from the kiln | +28.21862 | charged |
| $d_{\text{co2\_fuel\_fossil}}$, the reboiler's own stack | **+76.77997** | charged |
| $d_{\text{co2\_fuel\_biogenic}}$, vented | +7.19338 | **zero_rated — £0** |
| **`co2_fuel_biogenic` captured** | **−64.74041** | **credit** |
| **Net charged** | **+84.88319** | × £165/t |

The reboiler's 1.36863 PJ of gas derives 1.36863 × 56.1 = **76.77997 kt** onto
`co2_fuel_fossil` and is not captured (§1.11). The biogenic line is the one that matters:
**capturing 64.74 kt of biogenic CO₂ is a negative number in the objective**, not a zero, and
the kiln's own reported emissions fall to 28.21862 − 64.74041 = **−36.52179 kt** before the
reboiler is added. Had zero-rating been applied after capture, that credit would have been
lost and the model would have undervalued co-firing at a cement works by an order of
magnitude. `V5` and `V30` assert it.

**The 2035 economics, annual.** The train is a *retrofit*: it bolts onto the kiln rather than
replacing it, names it in `abates_unit_id`, and under C4 inherits the host's remaining life.
The kiln dies in 2043, so the capex annuitises over **9 years, not 25**.

| Term | Computation | £m/yr |
|---|---|---|
| Annuitised capex, **host life** $L$ = 9 | 190 × 0.131446 × 0.80037 | **19.98903** |
| Annuitised capex, own life $L$ = 25, for contrast | 190 × 0.060674 × 0.80037 | *(9.22672)* |
| Fixed opex | 9.50 × 0.80037 | 7.60351 |
| Reboiler gas | 0.72033 × 1.90 = 1.36863 PJ × 8.20 | 11.22274 |
| Auxiliary electricity | 0.72033 × 0.35 = 0.25212 PJ × 26.00 | 6.55500 |
| CO₂ transport tariff | 0.72033 × 18.00 | 12.96594 |
| **Total cost** | | **£58.33623m** |
| Carbon avoided | (728.43622 − 84.88319) kt × £165/t × 10⁻³ | **+106.18625** |
| **Net** | | **+£47.85002m/yr** |

**Capture is built at 2035, and the host-life rule more than doubles its capex charge** — from
£9.23m to £19.99m a year. That is the honest cost of retrofitting late onto old plant, and
before `D11` it did not exist: the train would have annuitised over its own 25 years and
outlived the kiln it was bolted to.

**What D15 changed here, and what it did not.** The net benefit moved by £0.0006m — the
arithmetic was already right. What changed is that none of it is now computed outside the
model: the captured quantity is a dispatch, the vented quantity is a disposal variable, the
biogenic credit is a `carbon_charge` on a carrier, and every one of them is an output row
someone can read. The previous draft reached the same answer through an emissions calculation
sitting beside the LP, and nothing checked that the two agreed. `V30` now does.

### 8.5 The pathway

| | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|
| `kiln_dry_coal` standing (Mt/yr) | 0.50379 | 0.50379 | 0.50379 | 0.50379 | 0 | 0 |
| `kiln_dry_wdf` standing (Mt/yr) | 0.37184 | 0.37184 | 0.37184 | 0.37184 | 0 | 0 |
| `kiln_dry_gas` standing (Mt/yr) | 0.07437 | 0.07437 | 0.07437 | 0.07437 | 0 | 0 |
| kiln units built, total (Mt/yr) | 0 | 0 | 0 | 0 | **0.94444** | 0 |
| `ccs_amine` (Mt CO₂/yr capacity) | 0 | 0 | **0.80037** | 0.80037 | **0.80037** | 0.80037 |
| `grinder_mixer_elec` (Mt/yr) | 1.22826 | 1.22826 | 1.22826 | 1.22826 | 1.22826 | 1.22826 |
| `motor_elec` (PJ/yr) | 0.17684 | 0.17684 | 0.17684 | 0.17684 | 0.17684 | 0.17684 |
| `pv_rooftop` (MW) | 0 | **2.47692** | 2.47692 | 2.47692 | 2.47692 | 2.47692 |
| `battery_2h` (MW) | 0 | 0 | 0 | 0 | 0 | 0 |
| $w_{\text{C-01}}$ reported (MW) | 0 | 0 | **1.00** | 1.00 | 1.00 | 1.00 |
| **Vented `co2_process`** (kt/yr) | 446.25 | 446.25 | **44.63** | 44.63 | 44.63 | 44.63 |
| **Vented `co2_fuel_fossil`** (kt/yr) | 282.19 | 282.19 | **104.998** | 104.998 | 104.998 | 104.998 |
| **Vented `co2_fuel_biogenic`** (kt/yr) | 71.93 | 71.93 | 7.19 | 7.19 | 7.19 | 7.19 |
| **Biogenic captured, credited** (kt/yr) | 0 | 0 | **−64.74** | −64.74 | −64.74 | −64.74 |
| **Direct emissions, charged** (kt CO₂e/yr) | **728.44** | 728.44 | **84.88** | 84.88 | 84.88 | 84.88 |
| Stranded value (£m) | 0 | 0 | 0 | 0 | **0** | 0 |

Three features of this pathway:

- **The kiln is never scrapped early.** The write-off of §5.3 does not forbid switching, it
  *prices delay*: it falls by a constant £30.875m a period (κ × 0.95000 × 5 ÷ 40, which is
  simply the kiln depreciating). Capture at £47.85m a year of net benefit is cheaper than any
  rebuild that would trigger the charge, so `Stranded value` is zero in every period. That is
  the behaviour `D11` was designed to produce.
- **A new kiln at 2045 needs a new capture train**, because under C3 an abatement unit expires
  with its host rather than on its own life. The 2045 rebuild is 0.85000 ÷ 0.90 =
  **0.94444 Mt/yr**, slightly below the 0.95000 it replaces, because the permit capacity
  carried spare headroom the model does not pay to reproduce.
- **PV and the battery change nothing.** Both are in the problem, both are correctly bounded,
  and one of them is built to a cap that buys 1.86% of the site's electricity. Reporting that
  is worth as much as reporting a large number.

### 8.6 The relaxation ladder (§4.2)

This premise is feasible at every period, so no rung is used. The ladder's order is
**C6 → C7 → C4b → C12 → C10 → C11 → C9 → C1**, and at this works only C12 (siting cap), C11
(connection capacity) and C9 (infrastructure availability) could ever be reached: C6 (unit
stability) and C7 (known changes) have no instances, and C10 (grade cascade) has no rows. Had
`import_capacity` at `C-01` been 20 MW rather than 25 MW, C11 would have relaxed in 2035 —
loudly, because relaxing it asserts a network reinforcement nobody has costed.

---

## 9. `A8` — the output rows and their evidence tiers

§8 of the specification is **not written** (`MF-20`, the §8 output schema; `T6` remainder), so
the shape below is the contract this fixture asserts and the schema must honour. One row per
premise per unit per carrier per period, plus the cost and network roll-ups.

An illustrative slice, `kiln_dry_coal` at 2035:

| Field | Value |
|---|---|
| `premise_id` | `P-000123` |
| `unit_id` | `kiln_dry_coal` |
| `carrier_id` | `coal` |
| `period` / calendar year | 2 / 2035 |
| `flow` | −2.07347 PJ/yr |
| `process_evidence_tier` | `site_known` (§3.1) |
| `mix_evidence_tier` | **`carrier_bounded`** (§5.2) |
| `year_evidence_tier` | `base_year` for this carrier; **`substituted`** on the `waste_derived_fuel` row |
| `vintage_evidence_tier` | **`process_known`** — the 2004 cohort |
| `area_evidence_tier` | **`proxy`** — floorspace × 0.35 |
| `archetype_evidence_tier` | **`default`** — no Tier A run exists (`MF-15`, a Could) |
| `carrier_coverage` | **incomplete** — `solid_biomass` not assessed |
| `commissioned_year` | 2004 |
| `remaining_life_years` | 9 |
| `data_year_offset` | −1 year |
| `confidence` | the **lower** of the unit's and the duty profile's |

Three rules govern the tiers on this premise:

- **They resolve per unit, not per premise.** `vintage_evidence_tier` is `process_known` on
  the kiln rows and `premise_bounded` on the other seven processes, in the same solve. That
  mixture is the normal case.
- **`commissioned_year` is 2004 on the kiln rows and blank on the rest.** The other seven do
  have a working age assumption, but writing its midpoint into this field would make an
  inferred date indistinguishable from a permit date.
- **Every row carries every tier**, which is `D10`'s stated cost: mixed-evidence results, and
  the quality is invisible unless each row says what it rests on. `V23` asserts that
  `mix_evidence_tier` in particular appears on all of them.

`A9` rolls these rows up to GB and compares against ECUK, the greenhouse-gas inventory and the
emissions budget. The budget comparison is **reported, never enforced** — the
"reported comparison, not constraint" pattern.

---

## 10. §7 — emissions attribution and reconciliation

### 10.1 Attribution, base year

| # | Rule | At this premise |
|---|---|---|
| 7.1 | Fuel CO₂ to the unit **consuming the fuel carrier**; process CO₂ to the chemistry unit against its mass denominator | all fuel and all 446.25 kt of calcination charged to `kiln_dry_coal` |
| 7.2 | Non-CO₂ gases tracked separately; **CCS never abates them** | the kiln's N₂O is reported and uncaptured |
| 7.3 | **Biomass zero-rated before capture** | §8.4 — the biogenic share of waste-derived fuel goes net-negative under capture |
| 7.4 | Direct versus indirect is a property of the carrier | `electricity.is_indirect` = true; every other carrier here is direct |
| 7.5 | Reporting categories derived over units, and they may overlap | the kiln appears under *combustion* and under *process* |
| 7.6 | Reconciliation **at the base year** | §10.2 |

**Base-year direct emissions are read off the balance (D15), not computed beside it.** §7's
expression is the same one the objective charges, which is what stops the reported total and
the costed total drifting apart:

$$\text{direct emissions}_t \;=\; \sum_{c\,:\,\text{charged}} d_{c,t} \;-\; \sum_{c\,:\,\text{zero\_rated}}\;\sum_{u \in U^{\text{abate}}} \big|\iota_{u,c}\big|\, z_{u,t}$$

| Term at 2025 | Computation | kt CO₂e |
|---|---|---|
| $d_{\text{co2\_process}}$ | 0.850000 Mt × 525 | **446.25000** |
| $d_{\text{co2\_fuel\_fossil}}$, coal | 2.073478 PJ × 94.6 | **196.15102** |
| $d_{\text{co2\_fuel\_fossil}}$, gas | 0.306075 PJ × 56.1 | **17.17081** |
| $d_{\text{co2\_fuel\_fossil}}$, waste fuel | 1.530415 PJ × 92.0 × 0.4891 | **68.86439** |
| $d_{\text{co2\_fuel\_biogenic}}$ | 1.530415 PJ × 92.0 × 0.5109 | 71.93379 — **zero_rated** |
| Biogenic captured | none before 2035 | 0 |
| **Computed direct total** | | **728.43622** |
| Indirect, on the **import** (§7.8) | 0.420004 PJ × 18.0 | 7.56007 |

**The waste fuel is the row D15 changed.** Before, it carried one net factor of 45.0 kt/PJ and
contributed 68.87 kt. Now it carries a gross 92.0 with a biogenic fraction of 0.5109, produces
**two** carriers, and contributes the same 68.86 kt of charged emissions — plus 71.93 kt that
is vented free today and becomes a £10.68m-a-year credit the moment capture arrives (§8.4).
The charged number did not move; the thing that was invisible is now a line item.

### 10.2 §7.6 reconciliation

| | kt CO₂e |
|---|---|
| Computed direct total (§10.1) | 728.44 |
| **Measured total** (§1.7, 2024 rows) | **743** |
| **Divergence** | **1.96%** |

Reported and not corrected. Two notes:

- **The reconciliation runs on the model's flows, not the meter's.** On the metered fuel of
  4.38000 PJ the computed total is 732.05 kt and the divergence 1.47%; on the back-solved
  3.90999 PJ it is 728.44 kt and 1.96%. The difference is entirely the 1.26% throughput-vs-
  energy gap of §5.1. The model's base year is the meter *reconciled through the unit
  coefficients*, and stating which basis a reported number sits on is what stops the two being
  confused.
- **The measured split is adopted for the base year** — 291 combustion / 452 process, in
  preference to the computed 282.19 / 446.25 — because measured data distinguishes the two
  sources directly while the computed split inherits the duty profile's assumptions.
  Intensity calibration is **off by default**, and at 1.96% there is nothing to explain.

The 2023 rows are a **reported trend and never a calibration target**: 298 + 437 =
735 kt against 2024's 743 kt, a 1.1% rise on a 2.4% rise in clinker throughput (0.83000 to
0.85000 Mt, §1.3). The process leg tracks throughput closely — 437 ÷ 0.83000 = 526.5 kt/Mt
against 452 ÷ 0.85000 = 531.8 kt/Mt, both within 1.3% of the 525 kt/Mt factor of §6.3 — which
is the kind of corroboration history is held for. `V25` still requires that adding these rows
changes nothing the model computes.

---

## 11. What this fixture asserts

Tests are the specification's, at §10.3. Scope is `load`, `premise` or `release`.

| # | Scope | Asserted here as |
|---|---|---|
| **V1** | release | *not asserted by this fixture* — the coupled-off R run is `MF-57` |
| **V1b** | release | §12: objective within 0.5%, energy per carrier per period within 1%, through the `MF-03` lineage table |
| **V2** | load | the coefficients of §1.11 round-trip against `capacity_to_activity_factor` to 1e-6 |
| **V4** | load | every carrier the units declare appears in `unit_input_output` |
| **V5** | premise | §8.4 — biomass zero-rated **before** capture, giving +8.10 kt rather than 72.84 kt |
| **V6** | premise | §7.4, §8.1 — $Z^{\text{exp}}$ is present and zero, and no term is assumed non-negative |
| **V10** | release | two runs of this fixture agree under the §9.3 tie-break |
| **V11** | load | §3.1 — exactly one process tier resolves, `site_known` |
| **V12** | premise | §8.2 — the siting cap holds and its sum runs over `pv_rooftop` alone |
| **V16** | batch | §8.3 — 16.25 MW rebuilt against 16.2 MW metered, **0.3% apart** |
| **V17** | premise | §8.4 — the capture train inherits the kiln's 2043 end of life and strands nothing while the kiln stands |
| **V18** | premise | §8.1 — **eleven of twelve** carrier nodes close to 1e-6, emission carriers included, with no assumed vent. **`clinker` does not close** and V18 fails there, for the reason in §8.1 — a specification gap, not an arithmetic one |
| **V19** | load | vacuous here; no duty at this premise carries a grade |
| **V20** | load | (d) only — `battery_2h` has β set and ψ, χ, ε unset |
| **V27** | load | §1.11 — each kiln unit carries exactly one `is_fuel_input` row; `ccs_amine`'s auxiliary electricity is `primary` and is not counted against it |
| **V28** | load + premise | §3.2 — the published `Cement Works` shares sum to 1.00 per vector, and the oil vector renormalises over the processes this premise runs |
| **V29** | premise | §8.1 — disposal exists only on the `may_dispose` carriers and every non-zero quantity is an output row |
| **V30** | premise | §8.1, §8.4, §10.1 — emission carriers balance; §7's total equals the objective's carbon term ÷ π × 10³; the waste fuel's fossil and biogenic coefficients sum to its 92.0 kt/PJ gross factor; captured biogenic returns a **negative** contribution |
| **V21** | load | §6.3 — the export price is strictly below the import price at all six periods |
| **V22** | premise | (a) total equals the sum over units consuming **primary** carriers; (b) no chain to test — no intermediate carrier is consumed here; (c) no reject leg exists at this works |
| **V23** | load + premise | §5.2 — one tier resolves, `carrier_bounded`, and it appears on every output row |
| **V24** | load + premise | §1.2 — one row per key at the base year or a recorded substitution; no duplicate `(key, year)` |
| **V25** | premise | §1.2 — the 2022 and 2023 rows move nothing by more than 1e-9 |
| **V26** | premise | §1.5 — `kiln_pyroprocessing`'s two intervals are disjoint, one is valid at 2024, and `A2`, `A4` and §3.15's cohort read touch no row outside it |

**V22 (b) and (c) are untestable at this premise**, and that is the clearest single statement
of what a cement works cannot demonstrate. There is no `gas → boiler → heat → dryer` chain to
book once, and no recovered-heat leg to contribute zero. Both legs are asserted on the
[food and drink fixture](2026-08-28-carb3-site-energy-system-worked-example-food-drink.md).

---

## 12. The published fixture (`MF-22`)

This example is published as a test fixture, not only as prose. `MF-22` (the cement worked
example as a fixture) is a Must at milestone M0, and is M2's gate.

| Artefact | Content |
|---|---|
| `fixtures/cement/premise.parquet` | §1.1–§1.10 as the four required and six optional entities, loaded through the package's pandera schemas |
| `fixtures/cement/reference/*.parquet` | §1.11–§1.12: the `carrier`, `unit`, `unit_input_output`, `unit_eligibility` and `activity_default_unit` rows this premise reaches |
| `fixtures/cement/scenario.parquet` | §6: `infrastructure_scenario` and `scenario_parameters` for `central` at `humber` |
| `fixtures/cement/expected/*.parquet` | §8.1's base-year ledger, §8.5's pathway, §10.1's emissions and §8.1's objective decomposition |
| `fixtures/cement/manifest.json` | units, rounding, solver, and the settings below |

**Units and rounding.** Money £m at 2021 prices, energy PJ/yr, mass Mt/yr, emissions
kt CO₂e/yr, area m², power MW. Intermediate arithmetic at six significant figures, asserted
values at five. Comparisons are relative, at the `MF-58` tolerances: objective within 0.5%,
energy per carrier per period within 1%.

**Solver settings**, pinned in the package so `V10` (determinism) can hold across machines:
HiGHS, version pinned in `pyproject.toml`, presolve on, **single-threaded**, the
lexicographic tie-break of §9.3 over `(unit_id, carrier_id)` applied as a second-objective
solve over the optimal face.

**What M2's gate does with it** (`MF-22`, `MF-59`): the fixture runs through S1–S8 in the
carrier-equivalent configuration of §13 below; its objective and per-carrier energy match the
expected tables within the `MF-58` tolerances; V2, V6, V12, V18, V22 (a), V23 pass; the
post-solve constraint-row check multiplies the built matrix by the returned solution and
verifies every row independently of the solver; and G1 (single-premise wall clock) is measured
and recorded with its machine and settings.

---

## 13. What this example demonstrates, and what it leaves open

### 13.1 What it demonstrates

1. **The mass denominator is load-bearing (`D5`).** Had `kiln_pyroprocessing` been denominated
   in PJ, its 446.25 kt of calcination CO₂ would have scaled with fuel efficiency and a more
   efficient kiln would have appeared to emit less process CO₂ — which is physically wrong,
   since that CO₂ comes from the limestone.
2. **Plant age changes the pathway, not just the cost** (§5.3, §8.4). The same kiln, the same
   units and the same prices give a 2030 unabated rebuild at the fallback tier and a 2035
   capture retrofit at tier 1. One line on a permit is the difference, and no other optional
   input at this premise moves the answer nearly as far.
3. **The write-off prices delay rather than forbidding change** (§8.5). It falls by a constant
   £30.875m a period as the kiln depreciates, so a switch the model rejects at 2030 it accepts
   at 2040, and a carbon price high enough still buys the kiln out early. That is the
   difference between representing inertia and hard-coding it.
4. **Abatement is a unit, and inheriting the host's life is what makes retrofit honest**
   (§8.4). Annuitising the capture train over the kiln's remaining 9 years rather than its own
   25 more than doubles its annual charge — £19.99m against £9.23m — and it is still built.
5. **Biomass zero-rating before capture is the rule that makes co-firing worth anything**
   (§8.4). 71.93 kt of biogenic CO₂ captured is a credit, and applying the zero-rating after
   capture would have hidden all of it.
6. **The collapse expands, at a cement works.** Eleven COMIT rows become fourteen units (§3.3),
   because five of them are bundles of a kiln, a capture train and sometimes a CHP sold as one
   technology. Unbundling them is what lets capture be retrofitted rather than rebuilt into.
7. **The long energy format earns its place immediately** (§1.2). Waste-derived fuel at 35.4%
   of this site's energy is an ordinary row rather than an escape hatch; the measured zero for
   oil is distinguishable from the unassessed biomass; and the substitution ladder rescues
   1.55 PJ that a base-year-only reading would have deleted.
8. **Peak and energy are different questions** (§8.3). This site's annual energy says capture
   is comfortably affordable; its connection capacity says capture puts the works 1.00 MW past
   its 25 MW supply.
9. **Reporting a small number is worth as much as reporting a large one** (§8.2). PV is built
   to the roof cap and supplies 1.86% of the site's electricity. The battery is not built at
   all, and β is what makes that a result rather than an omission.

### 13.2 What it cannot show

The structural limits, restated so nobody tries to close them here:

- **No graded heat, so no cascade.** C10 has zero rows at this premise; $h_{c \to c',t}$ has
  no declaration set, and the candidate kilns differ by *fuel* rather than by device.
- **No low-grade duty, so no waste-heat sink.** The kiln's exhaust genuinely dries raw meal,
  but representing that needs the reject-heat coefficients of data migration B5 (`MF-12`, a
  Should at milestone M6). Until they exist the raw mill is a motor duty only.
- **No unit competition at a duty.** Each of the eight duties here has one sensible incumbent.
- **CHP only fused inside bundled capture rows** (§3.3), never as plant the site runs.
- **V22 (b) and (c) untestable** (§11), for want of an intermediate-carrier chain and a reject
  leg.

All five are demonstrated on the
[food and drink premise](2026-08-28-carb3-site-energy-system-worked-example-food-drink.md),
and that is why §13 of the specification says cement alone is not sufficient.

### 13.3 Open points against the specification

**Five of the seven this example originally raised are now closed**, and an external review of 2026-09-15 added two more, by D13, D15, the
disposal variable, the two new §3 entities and §7.7. They are kept with their resolutions
rather than deleted, because the record of *why* a rule exists is what stops it being undone.

| # | Open point | Status |
|---|---|---|
| 1 | Nothing said where a process's share of premise energy comes from; §3.3 ruled out the only table that held it | **Closed.** §3.3.1 promotes it to an entity, on the marginal-versus-conditional argument, and §3.2 above now runs on the published shares |
| 2 | No per-premise tier over that table, so every premise of an activity got the same split | **Closed.** §3.10.1 `premise_process_energy` — quantities, not shares, with the residual renormalised |
| 3 | C8 admitted no disposal route, so vented process CO₂ could not balance and V18 failed on a physically fine premise | **Closed.** $d_{c,t}$ (§5.2), gated on `carrier_kind`, and §8.1's thirteen nodes now close with nothing assumed |
| 4 | §7 double-counted once electricity was generated on site, and said nothing about exports | **Closed.** §7.8 charges an indirect carrier on the import; §7.7 gives the allocation layer; D14 keeps the two apart |
| 5 | A `MOT` or `REF` duty had no carrier that worked, because a duty carrier that is also a fuel makes C8 circular | **Closed.** §3.4 states the service-carrier convention and names `motive_power` and `cooling` |

Two remain, and both are the same thing — a section cited from several places and never
written:

| # | Open point | Where it bites | Closed by |
|---|---|---|---|
| **6** | **§5.3.1 is cited and unwritten.** The vintage tier ladder, the survival function and the stranding formula are cited from §3.15, §5.3 and §5.5, and the section does not exist | §5.3 — the tier-2 window is read from the archived COMIT-parity baseline rather than from the live specification | `T23` / `MF-18` |
| **7** | **§5.6 is cited and unwritten**, so nothing says how C11's peak is rebuilt or which year it reads | §8.3 — this example uses mean import × the observed within-shift peak factor, with no diversity step, and **understates** the peak | `T23` / `MF-18`; §10.4 records that this row carries no automated guard |

And two new ones, both consequences of D13 that the entities have not caught up with:

| # | Open point | Where it bites | Closed by |
|---|---|---|---|
| **8** | **`premise_process_detail.unit_id` is singular, and a co-firing kiln is three units.** D13 splits the kiln by fuel, and §3.10 has one field to name it with | §1.5 — the permit's entry names the dominant unit and A4 resolves the rest, so a site that genuinely runs one fuel is no better determined than one that runs three | §3.10 — the field should take a set, or the entity should be keyed one field wider. §3.15 already handles it correctly, by stating vintage as shares |
| **9** | **A product carrier consumed by a downstream unit has no route through C8 that also satisfies C1**, and this is a hard failure rather than a missing convention. The kilns' clinker is consumed by the grinder; C1 needs it dispatched to the `ICMCLK` duty, C8 needs it released to the balance, and doing both double-counts | §8.1 — **`V18` fails at the `clinker` node** and the example says so rather than claiming closure | §5.5. Two resolutions: let a dispatched primary output also enter the balance where its consumer is a unit rather than a duty; **or** drop the `ICMCLK` duty entirely and make clinker a pure intermediate, so the works' only duty is cement and throughput's clinker row is evidence. The second is cleaner and is a D5 question |
| **10** | **An abatement unit that burns fuel needs two coefficients on one carrier, and `unit_input_output` is keyed for one.** A capture train consumes `co2_fuel_fossil` from its host and produces its own from the reboiler; §3.6's `(unit_id, carrier_id)` key admits only one row | §1.11 — `ccs_amine` cannot load as written. Netting the two makes it load and hides the reboiler's 76.78 kt/yr, which §8.4 reads separately | §3.6 — either a distinct-legs key, or a stated aggregation rule that keeps the gross legs reportable. Affects most abatement units, not just this one |

One thing stated rather than filed: **the objective charges direct carbon only** (§6.3). §5.4
does not say whether an `is_indirect` carrier's emissions enter $Z^{\text{carbon}}$, and both
worked examples charge direct and report indirect so that they remain comparable.

---

## Sources

- Implementation specification §1.1–§1.6, §2.1–§2.3, §3.1–§3.17, §4, §5.1–§5.5, §7, §9.2–§9.3,
  §10.1–§10.5, §13.
- [Delivery document](2026-08-28-carb3-site-energy-system-delivery.md): `T10` (this example),
  `T13`, `T17`, `T18`, `T23`; the not-in-scope list.
- [Data migration](2026-08-28-carb3-site-energy-system-data-migration.md): groups A, B (the
  397-row collapse and B2's 57 preserved non-fuel archetypes), B5 (reject heat), D1 (area).
- [Architecture](2026-08-28-carb3-site-energy-system-architecture.md): the unit spine, the 12
  service families and 14 chemistry nodes, the two-tier temporal structure.
- Notes [17](../notes/17_mvp_what_it_does.md) worked example B,
  [18](../notes/18_mvp_feature_prioritisation.md) `MF-03`, `MF-09`, `MF-12`, `MF-22`, `MF-43`,
  `MF-47`, `MF-57`–`MF-59`, milestones M0 and M2.
- [`docs/notes/data/emissions_source_classification.csv`](../notes/data/emissions_source_classification.csv)
  for the eleven `ICM` technology rows of §3.3;
  [`activity_process_register.csv`](../notes/data/activity_process_register.csv) for the
  `Cement Works` default process set.
- The [archived worked example](archive/2026-08-19-carb3-site-decarbonisation-worked-example.md),
  which walks the same premise against the COMIT-parity baseline. Its premise identifier and
  its headline quantities are kept here on purpose, so the two can be read side by side.
