# CaRB3 Site Energy System — Worked Example: a cement works

**The parity case.** One premise carried end to end through the nine algorithms `A1`–`A9`
(§4), exercising the mass denominator (`D5`, hybrid denominators), tier-1 plant vintage
(`D11`, existing plant has an age), a capture train as an abatement unit treating its hosts'
flue gas under C14 (a capture train treats its hosts' flue gas), and `D16` (internal products
are carriers, not duties) on the clinker this works grinds itself. It is the premise `V1b` (reproduce the R run's objective and
per-carrier energy) is meant to compare in the carrier-equivalent configuration of the
specification's §10.2, but its captured-CO₂ export breaks that configuration's condition 5
(no export) as written, which §13.3 point 13 records as open.

Section references without a document name are to the
[implementation specification](2026-08-28-carb3-site-energy-system-implementation.md).
Feature labels `MF-nn` are from
[notes/18](../notes/18_mvp_feature_prioritisation.md); task labels `Tnn` from the
[delivery document](2026-08-28-carb3-site-energy-system-delivery.md).

**Every figure here can be checked against a run.** The premise is the `carb3` slice's
synthetic cement works `mvp-cement`, exactly as its rows in
[`carb3/data/premises/`](../../carb3/data/premises/) state it, and every reference figure is
read from the tables in [`docs/notes/data/`](../notes/data/). §8's results are the slice's
own output, reproduced by

```
uv run --directory carb3 python -m carb3 mvp-cement --out-dir <dir> --show-dropped
```

which solves to optimality at **£3,640.0994m**, discounted to 2021, and writes the parquet
tables §9 lists. The hand arithmetic beside each result is there so a reader can check the
key figures without the solver. Where the specification describes a mechanism the slice does
not build (C11 connection capacity, C12 siting cap, the peak rebuild, reinforcement, stranding, PV, storage, A1's named
checks and the base-year carrier-mix rule), the example says what the specification would do,
marks it as not built, and quotes no number for it (§8.5.1).

Money is £m at 2021 prices, energy PJ, mass Mt, emissions kt CO₂, power MW. Figures are
quoted at six decimal places where the run prints them. Where a hand check multiplies run
quantities, the inputs are quoted at eight or nine places, and the 30-year annuity factor at
nine, so that the product shown reproduces the run's figure at six. The figures are
synthetic: the premise is hand-authored and
several reference rows carry low confidence (§1.11), so nothing here is a statement about a
real works.

**This example cannot show the carrier mechanism**, and that is structural rather than a
matter of taste: `Cement Works` resolves to two COMIT process commodities, `ICMCLK`
(clinker) and `ICM` (cement), and its processes present only three duty families with a
non-zero share at this works, `HTH` on the kiln, `MOT` on the motors and grinding, and the
small `OTH` and `REF` loads in site services. There is no `LTH` (low-temperature heat), no
`STM` (steam), no `DRY` (drying) and no `SPC` (space heating): nothing cascades and the
kiln's candidates differ by *fuel* rather than by device. The mechanism is demonstrated on the
[food and drink premise](2026-08-28-carb3-site-energy-system-worked-example-food-drink.md)
instead. The two examples keep the same thirteen sections, in the same order.

---

## 1. The premise

All of §1.1 to §1.10 is the `mvp-cement` rows of the six premise tables, verbatim except for
the provenance column, which is summarised.

### 1.1 `premise_record` (§3.1)

```
premise_id                   mvp-cement
carb3_activity               Cement Works
process_set_id               (blank: the activity's default set)
nation                       England
cluster_id                   humber
latitude / longitude         53.35 / -1.75
floorspace                   46,000 m²
construction_year            1957
construction_year_band       (blank)
last_refurbishment_year      2011                   (collected, not read: §3.1)
data_year                    2024                   the base year (D12)
source                       synthetic
```

`construction_year` 1957 bounds plant age at 67 years under `D11` (existing plant has an
age). Every unit this works runs has its own `commissioned_year` (§1.5.1), so the bound is
never read here. `cluster_id` is not a §3.1 field: §3.7 has A1 (ingest and validate) assign
the nearest cluster, A1 is not built in the slice, so the assignment is written down
([notes/20](../notes/20_reference_data_open_questions.md) item 58).

### 1.2 `premise_energy` (§3.1.1): consumption by carrier

| `carrier_id` | Vector (from `carrier`) | `quantity` PJ/yr | `data_status` | `data_year` |
|---|---|---|---|---|
| `coal` | coal | 3.407053 | modelled | 2024 |
| `natural_gas` | gas | 0.502947 | modelled | 2024 |
| `electricity` | electricity | 0.420005 | modelled | 2024 |
| `light_fuel_oil` | oil | 0.000000 | not_consumed | 2024 |
| `solid_biomass` | biomass | 0.000000 | not_consumed | 2024 |
| `waste_derived_fuel` | other | 0.000000 | not_consumed | 2024 |

**Base-year energy: 3.407053 + 0.502947 + 0.420005 = 4.330005 PJ/yr.** Three things this
table shows:

1. **The two fuels are written from the kilns, not metered.** 3.407053 PJ is 0.740664 Mt of
   clinker on `kiln_dry_coal` at 4.6 PJ per Mt and 0.502947 is 0.109336 Mt on `kiln_dry_gas`,
   which is the 0.85 Mt/yr clinker throughput (§1.3) split on the two kiln cohorts'
   `capacity_share` (§1.5.1). Electricity is kiln auxiliary 0.092404 + grinder 0.159601 +
   motive power 0.168000. `data_status` is `modelled` on all three, and §3.1.1 carries that
   to every output row.
2. **Coverage is complete.** All five main vectors are stated, two of them as explicit
   `not_consumed` zeros, plus `waste_derived_fuel` on the `other` vector, also an explicit
   zero. This works does not co-fire waste fuel: `waste_derived_fuel` has no `import_price` in
   any period, so a kiln burning it would burn free and the admission screen drops it (§3.3).
3. **There is no history.** Every row is at the base year, so §3.1.1's substitution ladder
   resolves at its first rung and `V25` (history is never read) has nothing to remove here.

### 1.3 `premise_throughput` (§3.1.2): physical output by carrier

| `carrier_id` | `quantity` Mt/yr | `data_status` | `data_year` |
|---|---|---|---|
| `clinker` | 0.850000 | measured | 2024 |
| `cement` | 1.130000 | measured | 2024 |

**The `cement` row is the duty; the `clinker` row is evidence.** `cement` is a product this
works sells (`may_export` true, §1.11), so under `D5` (hybrid denominators) it carries a
mass-denominated duty, and A1 (ingest and validate) would reject the premise with
`missing_throughput` without it. `clinker` is internal: made here, ground here, never sold,
so under `D16` (internal products are carriers, not duties) it has no `process_duty` row
(§3.2) and its throughput row is a cross-check only. The clinker factor of the base-year
grinder, 0.85 ÷ 1.13 = **0.752212**, is the `grinder_mixer_elec` coefficient of §1.11.

### 1.4 `premise_connection` (§3.1.3)

| `connection_id` | `carrier_id` | `import_capacity` | `export_capacity` | `connection_voltage` | `available_area` |
|---|---|---|---|---|---|
| `C-01` | `electricity` | 25 MW | 0 MW | 33 kV | (blank) |
| `C-02` | `natural_gas` | 20 MW | 0 MW | (blank) | (blank) |
| `C-03` | `co2_captured` | 0 | (blank) | (blank) | (blank) |

- **`C-03` is what lets capture run.** An export is declared only where a connection row
  carries the carrier (V32, the site boundary is honoured), and captured CO₂ has nowhere to go
  but out. A blank `export_capacity` on a **mass** carrier means unbounded, because a MW figure
  cannot bound a mass flow; on an energy carrier a blank would mean zero.
- **Coal is delivered** and has no connection row, which is the ordinary case §3.1.3
  describes: its import is site-level, $m_{c,t}$, outside C11 (connection capacity).
- **`available_area` is blank on every row.** The specification would fall back to
  `MF-09`'s footprint proxy (floorspace × a per-activity usable-area ratio, tagged
  `area_evidence_tier = proxy`) and bound PV by C12 (siting cap). The ratio table has no
  owner yet and the slice builds neither C12 nor PV, so no area is computed here (§8.5.1).

### 1.5 `premise_process_detail` (§3.10): `D10` tier 1 (known site detail wins)

| `process_id` | `valid_from_year` | `valid_to_year` | `connection_id` | `known_capacity` | `known_activity` | `confidence` |
|---|---|---|---|---|---|---|
| `quarrying_crushing` | 1957 | | `C-01` | | 0.021000 PJ/yr | medium |
| `raw_grinding_blending` | 1957 | | `C-01` | | 0.100800 PJ/yr | medium |
| `raw_meal_homogenisation` | 1957 | | `C-01` | | 0.025200 PJ/yr | medium |
| `kiln_pyroprocessing` | **1957** | **2003** | `C-01` | 0.700000 Mt/yr | | medium |
| `kiln_pyroprocessing` | **2004** | | `C-01` | **0.950000 Mt/yr** | **0.850000 Mt/yr** | high |
| `clinker_cooling` | 2004 | | `C-01` | | | medium |
| `cement_grinding` | 1957 | | `C-01` | | 1.130000 Mt/yr | high |
| `packing_dispatch` | 1957 | | `C-01` | | 0.021000 PJ/yr | medium |
| `site_services` | 1957 | | `C-01` | | | medium |

Nine rows covering eight processes, the site's complete process list at the base year.

- **The register's ninth process, `quarry_mobile_plant`, is absent.** The quarry plant is
  outside the metered boundary, and tier 1 overrides the activity's default set outright
  (`D10`, tiered site intelligence). It is also why `light_fuel_oil` is an explicit zero.
- **`kiln_pyroprocessing` carries two disjoint validity intervals**, a line of 0.70 Mt/yr to
  2003 and the dry line of 0.95 Mt/yr from 2004. Only the interval valid at the base year is
  read (§3.10, `V26`), so the works is not modelled as a blend of two lines that never
  coexisted. The closed interval has no `premise_process_unit` row, so nothing hangs off it.
- **`clinker_cooling` and `site_services` carry no `known_activity`**, because §3.10 cannot
  state a known zero (`known_activity` blank means unknown, not zero). The slice therefore
  derives no duty for them (§3.2).

### 1.5.1 `premise_process_unit` (§3.10.2): which units a known process runs, and when each was installed

| `process_id` | `valid_from_year` | `cohort_id` | `unit_id` | `commissioned_year` | `capacity_share` | `confidence` |
|---|---|---|---|---|---|---|
| `quarrying_crushing` | 1957 | 1 | `motor_elec` | 2016 | 1.000000 | medium |
| `raw_grinding_blending` | 1957 | 1 | `motor_elec` | 2016 | 1.000000 | medium |
| `raw_meal_homogenisation` | 1957 | 1 | `motor_elec` | 2016 | 1.000000 | medium |
| `kiln_pyroprocessing` | 2004 | 1 | `kiln_dry_coal` | **2004** | **0.871369** | high |
| `kiln_pyroprocessing` | 2004 | 2 | `kiln_dry_gas` | **2004** | **0.128631** | high |
| `clinker_cooling` | 2004 | 1 | `motor_elec` | 2016 | 1.000000 | medium |
| `cement_grinding` | 1957 | 1 | `grinder_mixer_elec` | **1998** | 1.000000 | medium |
| `packing_dispatch` | 1957 | 1 | `motor_elec` | 2016 | 1.000000 | medium |
| `site_services` | 1957 | 1 | `motor_elec` | 2016 | 0.078629 | medium |
| `site_services` | 1957 | 2 | `generic_process_elec` | 2016 | 0.859879 | low |
| `site_services` | 1957 | 3 | `chiller_electric` | 2016 | 0.061492 | low |

**One row per cohort, so a co-firing kiln is expressible.** The first three fields are a
foreign key to the §1.5 parent. `known_capacity` stays on the parent, because a permit states
the line's capacity once, and the two kiln children split it by `capacity_share`: 0.95 ×
0.871369 = **0.827801 Mt/yr** of `kiln_dry_coal` and 0.95 × 0.128631 = **0.122199** of
`kiln_dry_gas`. The kiln is two units, not one, because D13 (one primary carrier per unit)
puts the fuel in the unit's identity (D13, one primary carrier per unit). The three `site_services` shares are the activity's
duty-profile split of that process (§3.3), and they sum to 1.000000.

### 1.6 Plant age (§3.10.2's `commissioned_year`): `D11` tier 1

Every cohort carries a year, so every incumbent is aged at tier 1 (`process_known`), a point
mass that stands whole to its last operating year, $g + L - 1$, on the unit's own `lifetime`
from [`unit.csv`](../notes/data/unit.csv):

| Unit | Commissioned | `lifetime` | Last operating year | Standing at |
|---|---|---|---|---|
| `kiln_dry_coal`, `kiln_dry_gas` | 2004 | 30 | **2033** | 2021, 2025, 2030 |
| `grinder_mixer_elec` | 1998 | 30 | **2027** | 2021, 2025 |
| `motor_elec` | 2016 | 20 | **2035** | 2021 to 2035 |

The construction year of 1957 is never consulted. These three end-of-life years are what
drive §8's rebuilds at 2030 (the grinder), 2035 (the gas kiln cohort) and 2040 (the motors).

### 1.7 `premise_measured_emissions` (§3.11)

**No rows.** The entity is optional, so its absence is reported, not rejected, and §7.6's
reconciliation has nothing to run against (§10.2).

### 1.8 `premise_operating_profile` (§3.12)

**No rows.** No schedule, metered peak or load factor is stated, so §3.12's consistency check
has nothing to test and any peak C11 (connection capacity) would read must come from
activity defaults. The slice reads none of it.

### 1.9 `premise_weekly_profile` (§3.14)

**No rows**, so the premise has no measured shape at any connection.

### 1.10 `process_load_shape` (§3.13)

**No premise override.** Load shapes are read only for the peak rebuild of C11, which the
slice does not build, so this example states none.

### 1.11 Reference data this premise reads

**Carriers (§3.4).** Eleven carriers carry a flow in the run, one C8 (carrier balance) node
each:

| `carrier_id` | `carrier_kind` | `is_gradeable` | `is_indirect` | `biogenic_fraction` | `carbon_charge` | `denominator_kind` | `may_dispose` | `may_import` | `may_export` |
|---|---|---|---|---|---|---|---|---|---|
| `coal` | primary | no | no | 0 | | energy | no | **yes** | no |
| `natural_gas` | primary | no | no | **0.0115** | | energy | no | **yes** | no |
| `electricity` | primary | no | **yes** | | | energy | no | **yes** | **yes** |
| `heat_lt60` | intermediate | **yes** (heat rank 1) | no | | | energy | **yes** | no | no |
| `motive_power` | intermediate | no | no | | | energy | **yes** | no | no |
| `clinker` | product | no | no | | | **mass** | no | **no** | **no** |
| `cement` | product | no | no | | | **mass** | no | no | **yes** |
| `co2_process` | emission | no | no | | **charged** | mass | **yes** | no | no |
| `co2_fuel_fossil` | emission | no | no | | **charged** | mass | **yes** | no | no |
| `co2_fuel_biogenic` | emission | no | no | | **zero_rated** | mass | **yes** | no | no |
| `co2_captured` | product | no | no | | | mass | no | no | **yes** |

The other three carriers of §1.2, `light_fuel_oil`, `solid_biomass` and `waste_derived_fuel`,
appear only as explicit zeros: no unit in the model consumes them.

- **`may_import` and `may_export` are the site boundary (`D16`).** `clinker` is false on both,
  so it is internal: made and consumed on site, with no duty. `cement` and `co2_captured` are
  the two products that leave.
- **Natural gas is not wholly fossil.** Its `biogenic_fraction` of 0.0115 is the biogas share
  of mains gas, so every PJ burnt puts 51.12 × 0.9885 = **50.53212** kt on `co2_fuel_fossil`
  and 51.12 × 0.0115 = **0.58788** kt on `co2_fuel_biogenic`. This is what gives the capture
  train a biogenic stream to credit (§8.4).
- **`motive_power` is a carrier, and has to be.** The `MOT` (motors) duty's carrier cannot be
  `electricity`, or C8 would have the motor consuming and producing the same carrier.

**Units (§3.5) in the model.** Six units take a variable; their [`unit.csv`](../notes/data/unit.csv)
rows:

| `unit_id` | `unit_class` | `spine` | `process_id` / `duty_family` | fuel | `capex` £m per unit/yr | `fixed_opex` | `lifetime` | α | γ |
|---|---|---|---|---|---|---|---|---|---|
| `kiln_dry_coal` | converter | chemistry | `kiln_pyroprocessing` | coal | 114.7832 | 4.01633 | 30 | 0.913 | 1 |
| `kiln_dry_gas` | converter | chemistry | `kiln_pyroprocessing` | natural_gas | 114.7832 | 4.01633 | 30 | 0.913 | 1 |
| `ccs_amine` | abatement | chemistry | `kiln_pyroprocessing` | natural_gas | 354.5981 | 8.86495 | 30 | 0.913 | 1 |
| `grinder_mixer_elec` | converter | chemistry | `cement_grinding` | electricity | 28.3319 | 1.13747 | 30 | 0.913 | 1 |
| `grinder_mixer_clinker_sub_elec` | converter | chemistry | `cement_grinding` | electricity | 28.3319 | 1.13747 | 30 | 0.913 | 1 |
| `motor_elec` | converter | service | `MOT` | electricity | 2.8679 | 0.0717 | 20 | 0.95 | 1 |

Capacity units follow `D5`: Mt/yr of output for the chemistry units (Mt of `co2_captured` for
the train) and PJ/yr for the motor. **The reference data costs the two kiln units
identically**, so D13's split of the kiln by fuel changes nothing about its capital or fixed
cost here; what it changes is the fuel, the CO₂ and the eligibility each unit carries.

Two more admitted units are eligible here and get no variable: `pv_rooftop` (capex £0.62m per
MW, `fixed_opex` 0.006, `lifetime` 30, α 0.11, γ 0.031536, `area_per_capacity` 6,500 m² per
MW) and `pv_ground_mount`, because the slice gives a variable only to a unit that serves a duty
or supplies a product with no duty row, and PV does neither. `battery_2h` (`lifetime` 15,
α 0.95) is dropped by the admission screen for want of coefficients (§3.3).

**`unit_abatement_host` (§3.5.3).** `ccs_amine` has four host rows, one per dry kiln unit
that could carry it:

| `unit_id` | `host_unit_id` |
|---|---|
| `ccs_amine` | `kiln_dry_coal` |
| `ccs_amine` | `kiln_dry_gas` |
| `ccs_amine` | `kiln_dry_wdf` |
| `ccs_amine` | `kiln_dry_oil` |

[`unit_abatement_host.csv`](../notes/data/unit_abatement_host.csv) carries 20 cement rows:
five trains (`ccs_amine`, `ccs_amine_mdea`, `ccs_amine_coal_chp`, `ccs_oxyfuel`,
`ccs_oxyfuel_partial`) against the same four kilns. The other four trains carry no
`unit_input_output` rows and are dropped by the screen, and `kiln_dry_wdf` and `kiln_dry_oil`
are dropped for unpriced fuels, so at this premise `ccs_amine` has two hosts in the model,
and from 2025 only `kiln_dry_gas` runs.

**Coefficients (§3.6), consumed negative, produced positive, per unit of the unit's output.**
The declared rows are [`unit_input_output.csv`](../notes/data/unit_input_output.csv)'s; the
derived rows are A6's (the problem builder), from the fuel coefficient, the carrier's emission
factor (§6.3) and its `biogenic_fraction`:

| `unit_id` | `carrier_id` | `coefficient` | `role` | Authored |
|---|---|---|---|---|
| `kiln_dry_coal` | `clinker` | +1 | `primary_output` | declared |
| `kiln_dry_coal` | `coal` | −4.6 | `fuel_input` | declared |
| `kiln_dry_coal` | `electricity` | −0.10871 | `aux_input` | declared |
| `kiln_dry_coal` | `heat_lt60` | +0.17388 | `reject` | declared, low confidence |
| `kiln_dry_coal` | `co2_process` | **+525** | `emission` | declared: calcination, kt per Mt clinker |
| `kiln_dry_coal` | `co2_fuel_fossil` | **+411.19400** | emission | **derived**: 4.6 × 89.39 × (1 − 0) |
| `kiln_dry_gas` | `clinker` | +1 | `primary_output` | declared |
| `kiln_dry_gas` | `natural_gas` | −4.6 | `fuel_input` | declared |
| `kiln_dry_gas` | `electricity` | −0.10871 | `aux_input` | declared |
| `kiln_dry_gas` | `heat_lt60` | +0.17388 | `reject` | declared, low confidence |
| `kiln_dry_gas` | `co2_process` | +525 | `emission` | declared |
| `kiln_dry_gas` | `co2_fuel_fossil` | **+232.447752** | emission | **derived**: 4.6 × 50.53212 |
| `kiln_dry_gas` | `co2_fuel_biogenic` | **+2.704248** | emission | **derived**: 4.6 × 0.58788 |
| `ccs_amine` | `co2_captured` | +1 | `primary_output` | declared |
| `ccs_amine` | `co2_process` | **−0.9** | `emission_input` | declared: a **capture rate** $\nu$, not a draw |
| `ccs_amine` | `co2_fuel_fossil` | **−0.9** | `emission_input` | declared: a capture rate |
| `ccs_amine` | `co2_fuel_biogenic` | **−0.9** | `emission_input` | declared: a capture rate |
| `ccs_amine` | `natural_gas` | −1.9 | `fuel_input` | declared: the reboiler |
| `ccs_amine` | `electricity` | −0.35 | `aux_input` | declared: auxiliary, and `primary` |
| `ccs_amine` | `co2_fuel_fossil` | **+96.011028** | emission | **derived**: 1.9 × 50.53212, the reboiler's own stack |
| `ccs_amine` | `co2_fuel_biogenic` | **+1.116972** | emission | **derived**: 1.9 × 0.58788 |
| `grinder_mixer_elec` | `cement` | +1 | `primary_output` | declared |
| `grinder_mixer_elec` | `clinker` | −0.752212 | `aux_input` | declared |
| `grinder_mixer_elec` | `electricity` | −0.14124 | `fuel_input` | declared |
| `grinder_mixer_clinker_sub_elec` | `cement` | +1 | `primary_output` | declared |
| `grinder_mixer_clinker_sub_elec` | `clinker` | **−0.60059** | `aux_input` | declared |
| `grinder_mixer_clinker_sub_elec` | `electricity` | −0.07249 | `fuel_input` | declared |
| `motor_elec` | `motive_power` | +1 | `primary_output` | declared |
| `motor_elec` | `electricity` | −1 | `fuel_input` | declared |

- **A capture train's `emission_input` rows are rates, not quantities.** Each says what
  fraction of a host's stream of that carrier the train captures: 0.90, from COMIT's
  `emissions_released` of 0.1 on the bundle `ICMKLNMNQ01`. C14 (a capture train treats its
  hosts' flue gas) turns the rates into quantities (§7.3), and V37 (a capture rate is a
  fraction of its hosts' streams) bands them in [−1, 0) at load. Every other emission
  coefficient here is in kt per unit of output.
- **The train holds two rows on `co2_fuel_fossil` and on `co2_fuel_biogenic`.** It captures
  its hosts' stream as `emission_input` and makes its own from the reboiler as a derived
  `emission` row. §3.6's key is `(unit_id, carrier_id, role)`, so the two coexist; netting them
  would hide the reboiler's 49.08 kt a year (§8.4). The reboiler has its own stack and the train
  is never its own host, so that CO₂ is vented and charged.
- **One `fuel_input` per unit** (V27, unit fuel identity). `ccs_amine`'s electricity is
  `primary` but `aux_input`, so it is not counted against D13.
- **Each kiln rejects 0.17388 PJ of low-grade heat per Mt of clinker** on `heat_lt60`: the
  technical recovery share 11/291 = 0.037801 of fuel in, from [DECC_SURPLUSHEAT2014], times
  4.6. Confidence is low and the row says so. Nothing at this works draws rank-1 heat, so all of
  it is disposed (§8.1).
- **Electricity derives no fuel CO₂.** It is `is_indirect`, so A6 skips it and its emissions
  are reported on the import (§7.8), never charged.

`V2` (round-trip against `capacity_to_activity_factor`, with its energy-closure leg) holds on
every row: no unit puts out more energy than it takes in, and none is flagged `draws_ambient`.

**`unit_eligibility` (§3.5.1), the `Cement Works` rows.** 34 rows over 29 units. The ones that
reach the kiln and the grinding duty:

| `unit_id` | `process_id` | `min_duty` | `max_share` | `earliest_year` |
|---|---|---|---|---|
| `kiln_dry_coal` | `kiln_pyroprocessing` | 0.15 | | |
| `kiln_dry_gas` | `kiln_pyroprocessing` | 0.15 | | |
| `kiln_dry_wdf` | `kiln_pyroprocessing` | 0.15 | 0.55 | |
| `kiln_dry_oil` | `kiln_pyroprocessing` | | | |
| `kiln_fluidbed_wdf` | `kiln_pyroprocessing` | 0.40 | | |
| `kiln_calcium_looping_coal` | `kiln_pyroprocessing` | 1.20 | | 2035 |
| `ccs_amine` | `kiln_pyroprocessing` | 0.25 | | **2035** |
| `ccs_amine_mdea` | `kiln_pyroprocessing` | 0.25 | | 2035 |
| `ccs_amine_coal_chp` | `kiln_pyroprocessing` | | | |
| `ccs_oxyfuel` | `kiln_pyroprocessing` | 0.50 | | 2040 |
| `ccs_oxyfuel_partial` | `kiln_pyroprocessing` | 0.30 | | 2035 |
| `grinder_mixer_elec` | `cement_grinding` | | | |
| `grinder_mixer_clinker_sub_elec` | `cement_grinding` | | **0.60** | |
| `cement_lowcarbon_elec` | `cement_grinding` | | 0.35 | 2035 |

The remaining 20 rows are `furnace_ht_elec`, `furnace_ht_hydrogen` and
`dryer_direct_hydrogen` on the kiln; `motor_elec` on six processes; six other units on
`site_services`; two mobile-plant units on `quarry_mobile_plant`; and `battery_2h`,
`pv_rooftop` and `pv_ground_mount` at activity level.

### 1.12 `activity_default_unit` (§3.16): what the activity already has

| `process_id` | `duty_family` | `unit_id` | `default_share` | `sizing_basis` | `evidence_tier` |
|---|---|---|---|---|---|
| `kiln_pyroprocessing` | `HTH` | `kiln_dry_coal` | 0.53 | throughput | derived |
| `kiln_pyroprocessing` | `HTH` | `kiln_dry_wdf` | 0.39 | throughput | derived |
| `kiln_pyroprocessing` | `HTH` | `kiln_dry_gas` | 0.08 | throughput | derived |
| `cement_grinding` | `MOT` | `grinder_mixer_elec` | 1.00 | throughput | derived |
| five motor processes | `MOT` | `motor_elec` | 1.00 | duty_annual | assumed |
| `site_services` | `MOT`, `OTH`, `REF` | `motor_elec`, `generic_process_elec`, `chiller_electric` | 1.00 each | duty_annual | assumed |
| `quarry_mobile_plant` | `MOT` | `mobile_plant_diesel` | 1.00 | duty_annual | assumed |

**This premise never consults these rows**, because §1.5.1 names every unit directly and `D10`
(tiered site intelligence) puts site knowledge above the activity default. They are what a
cement works with no `premise_process_unit` rows would fall back to, and the
[food and drink example](2026-08-28-carb3-site-energy-system-worked-example-food-drink.md)
turns on a CHP that only this entity can assert.

---

## 2. `A1`: ingest and validate

A1's named checks are not in the slice's code; the slice's own
[`verify_premise_keys.py`](../../carb3/data/premises/verify_premise_keys.py) checks the keys
and rules of the six premise tables. Read against §3.1's checks, the premise passes all of
them:

| # | Check | Result |
|---|---|---|
| 1 | `nation` is England, in scope under `D8` (Great Britain scope) | pass |
| 2 | `carb3_activity` is one of the Factory-class activities (`D1`) | pass |
| 3 | Base-year energy sums to 4.330005 PJ/yr > 0 | pass: not `no_energy` |
| 4 | No duplicate `(premise_id, carrier_id, connection_id, data_year)` | pass: not `duplicate_year_row` |
| 5 | A `premise_throughput` row exists for every **exported** product carrier, `cement` here | pass: not `missing_throughput` |
| 6 | Every `commissioned_year` ≤ `data_year` 2024, and each parent's `capacity_share` sums to 1 | pass: the kiln's 0.871369 + 0.128631 and `site_services`' three shares both sum to 1.000000 |
| 7 | `construction_year` 1957 ≤ `data_year`; `last_refurbishment_year` 2011 between them | pass |
| 8 | `premise_process_detail` intervals per `(premise, process)` are disjoint, at least one valid at 2024 | pass: not `process_intervals_overlap` |

**Reported rather than failed:** no `premise_measured_emissions`, so §7.6 is skipped (§10.2);
no operating or weekly profile, so the peak would come from defaults; and `data_status`
`modelled` on every energy row. **Accepted.**

---

## 3. `A2`: duties and candidate units

### 3.1 The process set

`premise_process_detail` has rows, so `D10` (tiered site intelligence) tier 1 applies and the
register's default set is not consulted:

```
process_evidence_tier = "site_known"
process set at the base year 2024 =
    { quarrying_crushing, raw_grinding_blending, raw_meal_homogenisation,
      kiln_pyroprocessing, clinker_cooling, cement_grinding,
      packing_dispatch, site_services }
```

`V11` (process sets resolve to exactly one tier per premise) passes.

### 3.2 `process_duty` (§3.9): what the premise must produce

The slice derives **five** duties, and prints them:

| `process_id` | `carrier_id` | `quantity` | Read from |
|---|---|---|---|
| `cement_grinding` | `cement` | **1.130000 Mt/yr** | `premise_throughput`'s `cement` row (§3.1.2) |
| `quarrying_crushing` | `motive_power` | 0.021000 PJ/yr | `known_activity` |
| `raw_grinding_blending` | `motive_power` | 0.100800 PJ/yr | `known_activity` |
| `raw_meal_homogenisation` | `motive_power` | 0.025200 PJ/yr | `known_activity` |
| `packing_dispatch` | `motive_power` | 0.021000 PJ/yr | `known_activity` |

The motive-power duties sum to **0.168000 PJ/yr**.

**`kiln_pyroprocessing` has no duty**, and that is `D16` (internal products are carriers, not
duties): a duty exists only for a service carrier or a `product` with `may_export` true, and
the kiln makes `clinker`, false on both flags. The kiln keeps everything else a process has
(units, a §3.10 row, vintage) and C8 (carrier balance) pins its output, because the grinder
draws clinker and only the kilns make it. The slice prints this as *supply, no duty row*:
`clinker` from `kiln_dry_coal` and `kiln_dry_gas`, and `co2_captured` from `ccs_amine`.

**`clinker_cooling` and `site_services` get no duty**, because their `known_activity` is
blank (§1.5). The specification derives the same duties another way, by applying
[`activity_process_energy_share.csv`](../notes/data/activity_process_energy_share.csv)'s
`Cement Works` shares to §1.2's electricity, and lands within 3 × 10⁻⁶ PJ of them. The
difference is rounding: §1.2's electricity row was built up from the duties and the unit
coefficients (0.092404 + 0.159601 + 0.168000), and the shares split the rounded total back down:

| Process | `energy_share` (electricity) | × 0.420005 PJ | Goes to |
|---|---|---|---|
| `cement_grinding` | 0.38 | 0.159602 | the grinder's input coefficient, 0.159602 ÷ 1.13 = 0.14124 per Mt cement |
| `raw_grinding_blending` | 0.24 | 0.100801 | `MOT` duty |
| `kiln_pyroprocessing` | 0.22 | 0.092401 | the kiln's auxiliary coefficient, 0.092401 ÷ 0.85 = 0.10871 per Mt clinker |
| `raw_meal_homogenisation` | 0.06 | 0.025200 | `MOT` duty |
| `packing_dispatch` | 0.05 | 0.021000 | `MOT` duty |
| `quarrying_crushing` | 0.05 | 0.021000 | `MOT` duty |
| `clinker_cooling`, `site_services` | no row | 0 | none |

The shares sum to 1.00 on electricity, as V28 (process energy) requires. `clinker_cooling` and
`site_services` carry **no** electricity row, so under the specification their duty is a
known zero, with `clinker_cooling` treated as `MOT`/`motive_power` like the other motor
stages. Cooler fans are a real, continuous load, so this is a gap in the reference shares and
not a fact about cement works. The oil vector's split {`quarry_mobile_plant` 0.80, kiln 0.20}
renormalises over the processes this premise runs to {kiln 1.00}, the R2 rule of the archived
baseline §3.3.3; it moves nothing, because the premise burns no oil.

**A blank pair is safe here only because both processes really draw nothing.** The slice
sizes a duty from `known_activity` alone and reads neither §1.2 nor the shares above, so a
process that does run and is left blank loses its energy without complaint. Blanking
`packing_dispatch`'s 0.021000 PJ/yr in a copy of the premise and re-running shows it: the 2021
electricity import falls from 0.420005 to 0.399005 PJ, 5.0% under §1.2's meter, the run exits
0, and the only trace is the process's name on the *no duty derived* line, beside
`clinker_cooling` and `site_services`, whose zeros are real. Nothing tells the two apart. None
of the six checks of the specification's §5.7 compares the base year's imports with the meter
(§8.5.1). As written the premise closes: its 2021 electricity import is 0.420005 PJ, equal to
§1.2.

**So a process that runs needs a stated activity before the slice can size it.** Where there
is no sub-meter (§3.10.1), state `known_activity` as the share route would derive it: the
base-year quantity of each vector the process draws × its `energy_share` on that vector × its
incumbent's useful output per unit of input. For a motor stage that factor is 1, because
`motor_elec` makes 1 PJ of `motive_power` from 1 PJ of electricity, so `packing_dispatch` is
0.420005 × 0.05 = 0.021000 PJ/yr, the figure §1.5 carries. The incumbent's capacity then
follows from §5.1, `known_activity` ÷ (γ α), where γ is its capacity-to-activity factor and α
its availability. Record the derivation in `provenance` and set `confidence` to match. Leave
the pair blank only for a process whose base-year activity is genuinely zero, and say so in
`provenance`, as these two rows do.

No duty carries a `grade_rank`: the one gradeable carrier in play, `heat_lt60`, appears only
as the kilns' reject.

### 3.3 The candidate unit set, the screen, and the lineage

**Check 1 of §5.7, the admission screen, runs first.** Of `unit.csv`'s 148 units it admits 67
and drops 81 (the run prints each finding). Of the 29 units eligible at `Cement Works` it drops
12:

| Unit | Dropped because |
|---|---|
| `kiln_dry_wdf`, `kiln_fluidbed_wdf` | consume `waste_derived_fuel`, which has no `import_price` in any period (and `organic_waste`, `heavy_fuel_oil` for the fluidised bed) |
| `kiln_dry_oil` | consumes `heavy_fuel_oil`, priced at 2021 only, and `petroleum_products_misc`, never priced |
| `kiln_calcium_looping_coal` | consumes `solid_biomass` and `waste_derived_fuel`, never priced |
| `ccs_amine_mdea`, `ccs_amine_coal_chp`, `ccs_oxyfuel`, `ccs_oxyfuel_partial` | no `unit_input_output` rows, and a declared fuel with no `fuel_input` row |
| `cement_lowcarbon_elec` | consumes `heavy_fuel_oil`, `organic_waste` and `waste_derived_fuel` |
| `dryer_direct_hydrogen`, `furnace_ht_hydrogen` | consume `hydrogen`, never priced |
| `battery_2h` | no `unit_input_output` rows |

An unpriced fuel is read by a cost minimiser as free energy, so the screen is what stops the
model running the kiln on waste fuel at no cost.

**Of the 17 admitted, six enter the problem**: `kiln_dry_coal`, `kiln_dry_gas` and `ccs_amine`
as supply units of `clinker` and `co2_captured`, `grinder_mixer_elec` and
`grinder_mixer_clinker_sub_elec` on the cement duty, and `motor_elec` on the four motive-power
duties. The other eleven have nothing to serve: the six `site_services` units have no duty,
`furnace_ht_elec`'s output is heat, not a product, so it cannot supply the kiln's clinker, the
two mobile-plant units belong to a process this premise does not run, and the two PV units
serve no duty.

**The lineage.** `Cement Works` reaches eleven of COMIT's 397 technology rows, eight on
`ICMCLK` and three on `ICM`. [`comit_technology_lineage.csv`](../notes/data/comit_technology_lineage.csv)
records every one as `preserved`:

| COMIT `technology_code` | Name | Unit |
|---|---|---|
| `ICMKLND01` | Dry kiln, best available technology | `kiln_dry_coal`, with `d13_fan_out` to `kiln_dry_gas`, `kiln_dry_wdf` and `kiln_dry_oil` |
| `ICMKLNWST02` | Fluidised bed kiln with waste utilisation | `kiln_fluidbed_wdf` |
| `ICMKLNCLQ01` | Calcium looping kiln | `kiln_calcium_looping_coal` |
| `ICMKLNMNQ01` | Dry kiln with natural gas CHP and MEA CCS | `ccs_amine` |
| `ICMKLNMAQ02` | Advanced amine (MDEA) BAT kiln, CCS | `ccs_amine_mdea` |
| `ICMKLNMCQ01` | Dry kiln with coal CHP and MEA CCS | `ccs_amine_coal_chp` |
| `ICMKLNOXQ01` | BAT kiln full oxyfuel, CCS | `ccs_oxyfuel` |
| `ICMKLNPOQ01` | Partial oxyfuel dry kiln, CCS | `ccs_oxyfuel_partial` |
| `ICMLOCARB01` | Alternative low carbon cement | `cement_lowcarbon_elec` |
| `ICMGRIMIX01` | Grinding and mixing technology | `grinder_mixer_elec` |
| `ICMGRIMIX02` | Grinder and mixer, increased clinker substitution | `grinder_mixer_clinker_sub_elec` |

**The capture bundles are kept as trains, not as kilns.** COMIT sells a kiln, a capture train
and sometimes a CHP as one technology; the lineage maps each bundle to its train, which hosts
off the dry kilns through `unit_abatement_host`. That is what lets the model retrofit capture
onto the kiln it already has rather than rebuild the kiln to acquire it. The kiln's own row
fans out by fuel under D13 (one primary carrier per unit), so one COMIT row becomes four kiln
units, two of which this premise runs.

### 3.4 `min_duty`, `max_share` and `earliest_year`, applied before the LP

| Unit | Column | Value | Against | Effect |
|---|---|---|---|---|
| `kiln_dry_coal`, `kiln_dry_gas` | `min_duty` | 0.15 Mt/yr | the kiln's `known_activity` 0.85 | offered |
| `ccs_amine` | `min_duty` | 0.25 | the kiln's 0.85 | offered |
| `ccs_amine` | `earliest_year` | 2035 | | no build before 2035 |
| `grinder_mixer_clinker_sub_elec` | `max_share` | 0.60 | the 1.13 Mt/yr cement duty | at most 0.678 Mt/yr of cement |

`min_duty` is a floor on a duty, and the kiln process has none (D16), so the slice reads the
supply units' floors against the process's `known_activity`, which is what a duty would have
been sized at. No unit is refused here (the run's `eligibility_dropped` table is empty). The
other gated rows (calcium looping's 1.20, the other trains, `cement_lowcarbon_elec`'s 0.35)
never reach this step, because the screen dropped their units first.

`V19` (no unit is eligible for a duty above its `grade_out`) is vacuous at this premise: no
duty carries a grade.

---

## 4. `A3`: allocate premise energy onto carriers

`premise_energy` already names its carriers, so A3 is close to an identity here: each row maps
onto its `carrier` row, which supplies its `vector` (§3.4), and the base-year quantities pass on with
`year_evidence_tier = base_year` on all six. **A3 does not allocate energy across processes.**
Which unit burns what is decided by C8 (carrier balance), and at this works it is forced:
`kiln_dry_coal` is the only unit that can consume coal, and from 2035 natural gas has two
consumers, the kiln and the capture train's reboiler. The slice does not read `premise_energy`
at all (§8.5.1).

---

## 5. `A4`: back-solve capacity, carrier mix and vintage

### 5.1 Capacity

§3.10's precedence rule: where `known_capacity` is given it is the nameplate, in output units,
so capacity is `known_capacity` ÷ γ; otherwise `known_activity` is the activity, and capacity
is `known_activity` ÷ (γ α). The slice computes exactly this:

```
kiln line          0.950000 / 1                         = 0.950000 Mt/yr
  kiln_dry_coal    0.950000 x 0.871369                  = 0.827801 Mt/yr
  kiln_dry_gas     0.950000 x 0.128631                  = 0.122199 Mt/yr
grinder_mixer_elec 1.130000 / (1 x 0.913)               = 1.237678 Mt/yr
motor_elec         (0.021 + 0.1008 + 0.0252 + 0.021) / (1 x 0.95)
                 = 0.168000 / 0.95                      = 0.176842 PJ/yr
```

`clinker_cooling` and `site_services` add no motor capacity, because their `known_activity`
is blank. **Utilisation at the base year**: the kiln line's deliverable output is
0.950000 × 0.913 = 0.867350 Mt/yr against the 0.850000 drawn, so it runs at 0.850000 ÷
0.950000 = **0.894737** of nameplate, within its availability factor of 0.913.

### 5.2 The carrier mix (§4.1)

The kiln is two units on two fuels, so the base-year split between them is the carrier mix:

| Tier | Test at this premise | Resolves? |
|---|---|---|
| 1, `site_known` | `premise_process_unit` (§1.5.1) names both kiln units and states each one's `capacity_share` | **yes** |
| 2, `carrier_bounded` | not reached | |
| 3, `activity_default` | not reached | |

Under the specification the mix is observed, `mix_evidence_tier = site_known`, and the
dispatch is pinned to it: 0.850000 × 0.871369 = **0.740664 Mt** of clinker on coal and
**0.109336** on gas, which is what §1.2's fuel rows were written from (0.74066370 × 4.6 =
3.407053 PJ of coal, 0.10933630 × 4.6 = 0.502947 of gas). `V23` (one tier resolves, tried in
order, and `mix_evidence_tier` on every row) passes on all three properties.

**The slice builds no carrier-mix rule**, so the LP chooses the base-year dispatch inside the
two capacities instead (§8.1), and it chooses differently: gas is the cheaper fuel once carbon
is priced, so `kiln_dry_gas` runs at its limit and coal makes the rest. §8.5.1 records the
difference.

### 5.3 Vintage (`D11`)

Every incumbent is at tier 1 (`process_known`, a point mass on its commissioning year, §1.6).
The slice implements this tier only (`carb3/src/carb3/survival.py`), and C4 (incumbent ageing)
pins surviving capacity $e_{u,t}$ with an **equality**, so an incumbent stands, and pays its
fixed opex, whether or not it runs:

| Unit | 2021 | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|---|
| `kiln_dry_coal` (Mt/yr) | 0.827801 | 0.827801 | 0.827801 | 0 | 0 | 0 | 0 |
| `kiln_dry_gas` (Mt/yr) | 0.122199 | 0.122199 | 0.122199 | 0 | 0 | 0 | 0 |
| `grinder_mixer_elec` (Mt/yr) | 1.237678 | 1.237678 | 0 | 0 | 0 | 0 | 0 |
| `motor_elec` (PJ/yr) | 0.176842 | 0.176842 | 0.176842 | 0.176842 | 0 | 0 | 0 |

**The specification also allows early retirement** ($r_{u,t}$) priced by a stranding charge
$Z^{\text{strand}}$, whose formula §5.4 names and does not yet define (§13.3, point 6). The
slice builds neither, so no write-off is quoted here.

---

## 6. `A5`: apply the scenario

### 6.1 Periods, rates and the calendar

```
periods            2021, 2025, 2030, 2035, 2040, 2045, 2050
spans (years)      4, 5, 5, 5, 5, 5, 5          (the last span repeats the one before, §5.1)
discount rate r    0.035                        (scenario_parameters' discount_rate)
annuity rate i     0.035                        (no interest_rate row, so the discount rate)
base year offset   premise data_year 2024 read as the 2021 period
```

$\delta_t$ sums the single-year factor $(1 + r)^{-(y - 2021)}$ over the years each period
stands for, so that an annual cost times $\delta_t$ is that period's present value:

| Period | 2021 | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|---|
| $\delta_t$ | 3.801637 | 4.072319 | 3.428783 | 2.886943 | 2.430729 | 2.046608 | 1.723189 |

2021's is 1 + 1.035⁻¹ + 1.035⁻² + 1.035⁻³ = 1 + 0.966184 + 0.933511 + 0.901943 = 3.801637.

### 6.2 `infrastructure_scenario` (§3.7), scenario `published_2026`, cluster `humber`, `D7`

| `carrier` | 2021 | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|---|
| `co2_transport` | false | false | **true** | true | true | true | true |
| `hydrogen` | false | false | false | false | false | false | false |
| `grid_headroom` | true | true | true | true | true | true | true |

CO₂ transport reaches `humber` in 2030, so C9 (infrastructure availability) opens the
`co2_captured` export from 2030. Hydrogen never arrives, which is exogenous under `D7`
(infrastructure exogenous) and not something the model decides; no hydrogen unit survives the
screen here anyway.

### 6.3 `scenario_parameters` (§3.8)

Import prices, £m per PJ:

| `carrier_id` | 2021 | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|---|
| `coal` | 3.26 | 8.16 | 7.85 | 7.18 | 6.54 | 6.37 | 6.36 |
| `natural_gas` | 7.04 | 10.53 | 7.50 | 7.53 | 7.56 | 7.59 | 7.63 |
| `electricity` | 31.50 | 45.14 | 32.10 | 30.45 | 29.39 | 29.61 | 30.12 |

Carbon price $\pi_t$, £/t: **244.47, 259.70, 280.09, 302.08, 325.79, 350.97, 378.09**.

CO₂ transport and storage tariff $\tau$ on `co2_captured`: **£40.00m per Mt** in every period.
It is synthetic: no sourced price exists yet (notes/20 item 55).

Emission factors, kt CO₂ per PJ, gross of the biogenic split:

| `carrier_id` | Every period | Note |
|---|---|---|
| `coal` | 89.39 | direct |
| `natural_gas` | 51.12 | direct; split 50.53212 fossil and 0.58788 biogenic by `biogenic_fraction` 0.0115 |
| `electricity` | 58.02 (2021), 35.18 (2025), 13.23, 5.39, 4.29, 2.11, 0.67 (2050) | **indirect**: reported on the import, never charged |

`electricity` has an `export_price` only from 2025, so the slice refuses its export variable
outright (an export priced in some periods only would be free disposal in the others);
`C-01`'s export capacity is 0 MW in any case.

**Process CO₂ is not a scenario parameter.** The 525 kt per Mt of clinker is the kilns'
declared `co2_process` coefficient, the stoichiometry of calcination (§3.6 and D15, fuel CO₂
derived, process CO₂ declared).

**The objective charges direct carbon only.** §5.4 charges carbon on what is vented; an
`is_indirect` carrier's emissions are reported and not charged, consistently in both worked
examples.

---

## 7. `A6`: the problem as built

### 7.1 Sets

```
T      = {2021, 2025, 2030, 2035, 2040, 2045, 2050}       seven periods
Q      = the five duties of §3.2                          one mass, four motive power
U      = { kiln_dry_coal, kiln_dry_gas, ccs_amine,
           grinder_mixer_elec, grinder_mixer_clinker_sub_elec, motor_elec }
U^0    = { kiln_dry_coal, kiln_dry_gas, grinder_mixer_elec, motor_elec }   incumbents
U^abate= { ccs_amine },  H(ccs_amine) in the model = { kiln_dry_coal, kiln_dry_gas }
C      = the eleven carriers of §1.11                     one C8 node each
```

### 7.2 Variables (§5.2), all continuous and non-negative

The run reports **245 variables and 237 constraints**. The variable kinds:

| Variable | Here |
|---|---|
| $n_{u,t}$ new capacity, $a_{u,t}$ available capacity | per unit and period; $n$ bounded to zero before `earliest_year` |
| $e_{u,t}$ surviving incumbent capacity | the four incumbents, fixed by C4 |
| $z_{u,q,t}$ dispatch to a duty | the grinders on `cement`, `motor_elec` on the four motive-power duties |
| $z^{\circ}_{u,t}$ released to the balance | the two kilns (`clinker`) and `ccs_amine` (`co2_captured`) |
| $z^{\text{host}}_{u,u',t}$ host activity a train treats | `ccs_amine` on `kiln_dry_coal` and on `kiln_dry_gas` |
| $m_{c,t}$ import | `coal`, `natural_gas`, `electricity`, held site-wide in the slice |
| $x_{c,t}$ export | `co2_captured`, bounded to zero before 2030 by C9 |
| $d_{c,t}$ disposal | the four `may_dispose` carriers that carry a flow: the three CO₂ carriers and `heat_lt60` |

**The problem is a pure LP.** `min_duty` is applied before the build, not as a binary, and the
survival function is a parameter.

### 7.3 Constraints, instantiated

| # | Constraint | In the slice | Binds? |
|---|---|---|---|
| **C1** | Duty satisfaction | 5 duties × 7 periods | always: an equality |
| **C2** | Activity ≤ available capacity × γ × α | every unit and period | on `kiln_dry_gas` at 2021, on every unit built |
| **C3** | Capacity transfer between periods | every unit | |
| **C4** | Incumbent ageing (tier 1, an equality) | the four incumbents | the coal kiln stands idle from 2025 to 2030 |
| **C5** | No building in the start year | $n_{u,2021} = 0$ | binds at 2021 |
| **C6**, **C7** | Unit stability, known changes | not built | |
| **C8** | Carrier balance | 11 carriers × 7 periods = 77 | always: equalities |
| **C9** | Infrastructure availability | `co2_captured` export closed in 2021 and 2025 | not binding: the train's `earliest_year` 2035 bites first |
| **C10** | Grade cascade | a filter on eligibility; nothing to filter here | |
| **C11** | Connection capacity | **not built** | §8.5.1 |
| **C12** | Siting cap | **not built** | §8.5.1 |
| **C13** | A cap is not routed through a consumer | no capped unit's output is drawn by another unit here, so no tracer rows | |
| **C14** | A capture train treats its hosts' flue gas | `ccs_amine` on its two hosts | treats the whole gas kiln from 2035 |

`max_share` enters as an upper bound on $z_{u,q,t}$: `grinder_mixer_clinker_sub_elec` ≤ 0.60 ×
1.13 = 0.678 Mt/yr of cement, which binds from 2025.

**C14, as it is written for this train.** For each carrier $c$ the train holds a rate on:

$$\Gamma_{c,t} = \nu_c \sum_{u' \in \{\text{coal kiln},\,\text{gas kiln}\}} \iota^{\text{gross}}_{u',c}\; z^{\text{host}}_{u',t}
\qquad z_{\text{ccs},t} = 10^{-3}\sum_c \Gamma_{c,t}
\qquad z^{\text{host}}_{u',t} \le z^{\circ}_{u',t}$$

with $\nu_c = 0.9$ on all three CO₂ carriers and $\iota^{\text{gross}}$ the host's production per
Mt of clinker from §1.11 (525 process; 411.194 fossil on coal; 232.447752 fossil and 2.704248
biogenic on gas). Treating a *share of the host's activity* rather than a fraction of each stream
is what keeps the constraint linear, and it captures every stream of that share in the host's
own proportions. C8 on each CO₂ carrier takes $-\Gamma_{c,t}$.

### 7.4 Objective (§5.4), as the slice builds it

$$\min Z = \sum_t \delta_t\big(Z^{\text{capex}}_t + Z^{\text{opex}}_t + Z^{\text{fuel}}_t + Z^{\text{carbon}}_t - Z^{\text{exp}}_t\big)$$

- $Z^{\text{capex}}_t$: capex × annuity on the **new** capacity standing in $t$; an incumbent's
  capex is sunk. Annuity $i/(1-(1+i)^{-L})$: **0.054371332** at $L$ = 30, **0.07036108** at 20.
- $Z^{\text{opex}}_t$: `fixed_opex` × available capacity, incumbents included.
- $Z^{\text{fuel}}_t$: import × `import_price`.
- $Z^{\text{carbon}}_t = 10^{-3}\pi_t\,(d_{\text{co2\_process}} + d_{\text{co2\_fuel\_fossil}} - \Gamma_{\text{co2\_fuel\_biogenic}})$:
  charged on what is vented, less a credit on biogenic CO₂ captured.
- $-Z^{\text{exp}}_t = x_{\text{co2\_captured},t}\,(\tau_t - p^{\text{exp}}_t)$ with no export price,
  so **+£40.00m per Mt** exported: a cost. The run reports it under the term `export`.

$Z^{\text{infra}}$, $Z^{\text{net}}$ and $Z^{\text{strand}}$ are not built.

---

## 8. `A7`: the solve

The run: `status=ok termination=optimal`, **objective £3,640.0994m**, 245 variables, 237
constraints. Check 4 of §5.7 (the row check, every constraint row re-verified against the
built matrix) finds 0 violations, and check 6 (the capture check, the post-solve legs of V37, a capture rate is a fraction of its hosts' streams)
finds 0.

### 8.1 The base year, 2021, worked in full

C5 (no building in the start year) forbids building at 2021, so the base year runs on the
incumbents of §5.1 at 2021 prices.

**Activity.** The cement duty is met entirely by the incumbent grinder, which draws
1.130000 × 0.752212 = **0.850000 Mt** of clinker (0.84999956 before rounding). The kilns must
make it. `kiln_dry_gas` can deliver at most 0.122199 × 0.913 = **0.111568 Mt**, and runs at
that limit; `kiln_dry_coal` makes the rest, 0.850000 − 0.111568 = **0.738431 Mt**, within its
0.827801 × 0.913 = 0.755782. Gas runs first because it is cheaper per Mt of clinker once
carbon is priced:

```
coal kiln  fuel 4.6 x 3.26 = 15.00   + fossil CO2 411.194 kt x £244.47/t = 100.53   = 115.52 £m/Mt
gas kiln   fuel 4.6 x 7.04 = 32.38   + fossil CO2 232.448 kt x £244.47/t =  56.83   =  89.21 £m/Mt
```

(the 525 kt of process CO₂ is the same on both, so it does not separate them).

**C8, every carrier node, 2021.** Every node closes to zero, which is V18 (carrier balance
closes to 1e-6) and V30 (emissions close through the balance) together.

| Carrier | Consumed by units | Produced by units | Import $m$ | Disposal $d$ | Export / duty |
|---|---|---|---|---|---|
| `coal` | `kiln_dry_coal` −3.396785 | | +3.396785 | | |
| `natural_gas` | `kiln_dry_gas` −0.513213 | | +0.513213 | | |
| `electricity` | kilns −0.092404 (coal 0.080275, gas 0.012129), grinder −0.159601, motor −0.168000 | | +0.420005 | | |
| `clinker` | grinder −0.850000 | kilns +0.850000 (coal 0.738431, gas 0.111568), released through $z^{\circ}$ | | | |
| `cement` | | grinder +1.130000 | | | duty 1.130000 |
| `motive_power` | | motor +0.168000 | | | duties 0.168000 |
| `heat_lt60` | | kilns +0.147798 (coal 0.128398, gas 0.019399) | | −0.147798 | |
| `co2_process` | | kilns +446.249769 kt (coal 387.676518, gas 58.573251) | | −446.249769 | |
| `co2_fuel_fossil` | | coal 303.638587 + gas 25.933754 = +329.572340 kt | | −329.572340 | |
| `co2_fuel_biogenic` | | gas +0.301708 kt | | −0.301708 | |
| `co2_captured` | | none | | | export 0 |

Hand checks: coal 0.73843146 × 4.6 = 3.396785 PJ and × 411.194 = 303.638587 kt; gas
0.11156810 × 4.6 = 0.513213 PJ, × 232.447752 = 25.933754 kt fossil and × 2.704248 = 0.301708
kt biogenic;
process CO₂ 0.84999956 × 525 = 446.249769 kt; kiln electricity 0.84999956 × 0.10871 =
0.092404; grinder 1.13 × 0.14124 = 0.159601. **The base year reproduces §1.2's electricity,
0.420005 PJ, exactly**; the fuels differ from §1.2 by the dispatch choice of §5.2 (coal
3.396785 against 3.407053, gas 0.513213 against 0.502947).

**The reject heat is disposed.** Nothing draws rank-1 heat at this works, so the kilns' whole
0.147798 PJ goes to $d_{\text{heat\_lt60}}$, free: it carries no carbon, because `heat_lt60` is
`intermediate` and its fuel was charged to the kiln that burnt it.

**Biogenic CO₂ is vented free.** The 0.301708 kt from the gas kiln is `zero_rated`: a quantity
on an output row, priced at £0.

**The 2021 annual cost.**

| Term | Computation | £m |
|---|---|---|
| $Z^{\text{capex}}$ | C5: nothing new | **0.000000** |
| $Z^{\text{opex}}$ | kilns 0.95 × 4.01633 = 3.815514; grinder 1.23767798 × 1.13747 = 1.407822; motor 0.17684211 × 0.0717 = 0.012680 | **5.236015** |
| $Z^{\text{fuel}}$ | coal 3.39678473 × 3.26 = 11.073518; gas 0.51321325 × 7.04 = 3.613021; electricity 0.420004652 × 31.50 = 13.230147 | **27.916686** |
| $Z^{\text{carbon}}$ | (446.249769 + 329.572340) = 775.822109 kt × £244.47/t × 10⁻³ | **189.665231** |
| $-Z^{\text{exp}}$ | no export | **0.000000** |
| **Total** | | **£222.817932m** |

Discounted: 222.817932 × 3.801637 = **£847.0729m**, the base year's share of the objective.
Carbon is 85% of it. Indirect emissions on the electricity import, 0.42000465 × 58.02 =
24.368670 kt, are reported by the specification and not charged; the slice's tables do not
carry them.

### 8.2 2025: the kiln switches to gas, and the grinder substitutes clinker

The first period C5 allows building, two things happen at once.

**Clinker substitution.** `grinder_mixer_clinker_sub_elec` takes its `max_share` of the
cement duty, 0.60 × 1.13 = **0.678000 Mt/yr**, on **0.742607 Mt/yr** of new capacity
(0.678 ÷ 0.913). The incumbent grinder makes the other 0.452000. Clinker drawn falls to

```
0.452 x 0.752212 + 0.678 x 0.60059 = 0.340000 + 0.407200 = 0.747200 Mt/yr     (from 0.850000)
```

Every Mt of cement moved to the substituting grinder saves 0.752212 − 0.60059 = 0.151622 Mt
of clinker and 0.14124 − 0.07249 = 0.06875 PJ of electricity. At 2025 prices a Mt of clinker
from a new gas kiln costs 4.6 × 10.53 = 48.438 of gas, 232.448 kt × £259.70/t = 60.367 of
fuel CO₂, 525 kt × £259.70/t = 136.343 of process CO₂, 0.10871 × 45.14 = 4.907 of auxiliary
electricity and 6.836 + 4.399 of kiln capital and fixed cost (below): **£261.29m**. The saving
is 0.151622 × 261.29 + 0.06875 × 45.14 = **£42.72m** a year per Mt of cement, against the
substituting grinder's 28.3319 × 0.054371332 ÷ 0.913 + 1.13747 ÷ 0.913 = **£2.93m**. The cap binds,
and it binds in every later period too.

**The kiln moves to gas.** The coal kiln still stands (to 2033), but it is cheaper to build gas
kiln capacity and leave coal idle:

```
per Mt clinker per year, 2025          coal kiln (standing)     new gas kiln
fuel                                   4.6 x 8.16  = 37.536     4.6 x 10.53 = 48.438
fuel CO2 at £259.70/t                  411.194 kt  = 106.787    232.448 kt  = 60.367
capital, 114.7832 x 0.054371332 / 0.913                         6.836
fixed opex, 4.01633 / 0.913                                     4.399
total                                               144.323                  120.039
```

The coal kiln's fixed opex is not in its column because C4 (incumbent ageing) keeps it standing
and paying either way. Gas saves **£24.28m per Mt of clinker a year**, so the LP builds
0.747200 ÷ 0.913 − 0.122199 = **0.696201 Mt/yr** of `kiln_dry_gas`, enough with the gas cohort
to make all 0.747200 Mt, and dispatches the coal kiln at zero from 2025.

**That saving is the budget a gas reinforcement must beat.** It is 24.28 × 0.7472 ≈ **£18.1m a
year** at 2025 prices, and the switch takes the works' gas draw from 0.502947 PJ (15.9 MW on
mean flow) to 3.437119 PJ (109.0 MW) against `C-02`'s 20 MW `import_capacity`. The slice does
not build C11 (connection capacity), so the switch is free of that cost here; §8.5.1 says what
the specification would do.

**C8 at 2025**: natural gas 0.74719984 × 4.6 = **3.437119 PJ**; electricity 0.081228 (kiln) +
0.063840 (grinder) + 0.049148 (substituting grinder) + 0.168000 (motors) = **0.362217 PJ**;
`co2_process` 0.747199844 × 525 = **392.279918 kt**; `co2_fuel_fossil` 0.747199844 × 232.447752 =
**173.684924 kt**; `co2_fuel_biogenic` **2.020614 kt**; reject heat 0.129923 PJ. All of it is
disposed.

| Term, 2025 | Computation | £m |
|---|---|---|
| $Z^{\text{capex}}$ | gas kiln 0.69620126 × 114.7832 × 0.054371332 = 4.344933; substituting grinder 0.74260679 × 28.3319 × 0.054371332 = 1.143944 | **5.488877** |
| $Z^{\text{opex}}$ | kilns (0.82780055 + 0.81840071) × 4.01633 = 6.611687; grinders (1.23767798 + 0.74260679) × 1.13747 = 2.252515; motor 0.012680 | **8.876882** |
| $Z^{\text{fuel}}$ | gas 3.43711928 × 10.53 = 36.192866; electricity 0.36221680 × 45.14 = 16.350466 | **52.543332** |
| $Z^{\text{carbon}}$ | (392.279918 + 173.684924) = 565.964842 kt × £259.70/t | **146.981070** |
| **Total** | | **£213.890160m** |

### 8.3 2030, 2035 and 2040: the incumbents' ends of life

**2030.** The 1998 grinder's last year is 2027 (§1.6), so it is gone, and the LP rebuilds
0.452 ÷ 0.913 = **0.495071 Mt/yr** of `grinder_mixer_elec` for the share the substituting
grinder may not take. Capex rises by 0.49507119 × 28.3319 × 0.054371332 = 0.762629 to **6.251506**.
Nothing else changes in quantity; prices do: gas 3.43711928 × 7.50 = 25.778395, electricity
0.36221680 × 32.10 = 11.627159, carbon 565.964842 × 0.28009 = 158.521093.

**2035.** The 2004 kiln cohorts reach their last year in 2033. The coal kiln, idle since 2025,
simply goes, and its fixed opex with it; the gas cohort's 0.122199 Mt/yr is rebuilt as new
`kiln_dry_gas` (capex 0.762636 a year). The capture train arrives the same period (§8.4).

**2040.** The 2016 motors' last year is 2035, so **0.176842 PJ/yr** of `motor_elec` is rebuilt,
at 0.17684211 × 2.8679 × 0.07036108 = 0.035685 a year.

### 8.4 The capture decision at 2035

CO₂ transport reaches `humber` in 2030 (§6.2), but `ccs_amine`'s `earliest_year` is 2035, so the
train is built at 2035 and not before.

**What the train treats.** From 2025 the only kiln running is `kiln_dry_gas`, so C14 (a capture
train treats its hosts' flue gas) sets $z^{\text{host}}$ on the gas kiln to its whole activity,
**0.747200 Mt** of clinker, and captures 0.9 of each stream that activity makes:

```
host stream (gas kiln, 0.747200 Mt clinker)          made           captured (x 0.9)    vented
  co2_process        0.747199844 x 525          = 392.279918 kt     353.051926          39.227992
  co2_fuel_fossil    0.747199844 x 232.447752   = 173.684924 kt     156.316432          17.368492
  co2_fuel_biogenic  0.747199844 x 2.704248     =   2.020614 kt       1.818552           0.202061
                                                  567.985456 kt     511.186910 kt
z(ccs_amine) = 511.186910 / 1000                                    = 0.511187 Mt/yr of co2_captured
capacity     = 0.511187 / (gamma 1 x alpha 0.913)                    = 0.559898 Mt/yr
```

The run's `capture_by_host` table carries exactly these three rows at rate 0.9 and treated
activity 0.7472, and nothing on `kiln_dry_coal`. Capture is pro rata by construction: the three
captured streams stand in the host's own proportions, which is V37's leg (d).

**The train's own inputs and stack.** Per Mt of CO₂ captured it burns 1.9 PJ of gas and draws
0.35 PJ of electricity:

```
reboiler gas        1.9  x 0.51118691 = 0.971255 PJ
  fossil CO2        0.97125513 x 50.53212 = 49.079581 kt     vented, charged (never its own host)
  biogenic CO2      0.97125513 x 0.58788  =  0.570981 kt     vented, zero-rated
auxiliary power     0.35 x 0.51118691 = 0.178915 PJ
```

**What is vented at 2035**, the disposal the run reports:

| Carrier | Made | Captured | Vented $d$ | Charge |
|---|---|---|---|---|
| `co2_process` | 392.279918 | 353.051926 | **39.227992** | charged |
| `co2_fuel_fossil` | 173.684924 + reboiler 49.079581 | 156.316432 | **66.448073** | charged |
| `co2_fuel_biogenic` | 2.020614 + reboiler 0.570981 | 1.818552 | **0.773043** | zero-rated |

The carbon term charges the vented fossil and process CO₂ and credits the captured biogenic:

$$10^{-3} \times 302.08 \times (39.227992 + 66.448073 - 1.818552) = 0.30208 \times 103.857513 = \textbf{£31.373277m}$$

**Biogenic CO₂ captured is a credit, not a zero.** Its 1.818552 kt enters the carbon term
negative, £0.549 m a year, because §7.3 zero-rates biomass *before* capture. Had zero-rating
been applied after, it would be lost. V5 (biomass zero-rated before capture) and V30 (emissions close through the balance) assert it.

**The 2035 economics, annual.**

| Term | Computation | £m/yr |
|---|---|---|
| Capex, annuitised over the train's own 30 years | 0.55989804 × 354.5981 × 0.054371332 | 10.794818 |
| Fixed opex | 0.55989804 × 8.86495 | 4.963468 |
| Reboiler gas | 0.97125513 × 7.53 | 7.313551 |
| Auxiliary electricity | 0.17891542 × 30.45 | 5.447975 |
| Transport and storage tariff | 0.51118691 × 40.00 | 20.447476 |
| **Cost of capture** | | **48.967288** |
| Carbon without capture | 565.964842 kt × £302.08/t | 170.966660 |
| Carbon with capture | (above) | 31.373277 |
| **Carbon avoided** | | **139.593382** |
| **Net** | | **+£90.626094m/yr** |

Per Mt captured the train costs 21.117 (capital) + 9.710 (fixed) + 14.307 (gas) + 10.658
(electricity) + 40.000 (tariff) + 96.011 kt × £302.08/t = 29.003 (its reboiler's own CO₂) =
**£124.80m**, against **£302.08m** of carbon avoided, whichever stream the Mt came from. So the
train treats the whole kiln: it would treat more if there were more.

**The capital is charged over the train's own life, not the host's.** The specification's
retrofit rule (C3 capacity transfer and C4 incumbent ageing with §3.5.3, checked by V17, vintage and stranding per unit) gives an abatement unit the earliest
remaining life among its hosts. The slice annuitises every unit over its own `lifetime`, and
the gas kiln capacity the train treats was built in 2025 and 2035 and outlives the horizon, so
at this premise the two readings would not differ within it.

**The 2035 annual cost.**

| Term | Computation | £m |
|---|---|---|
| $Z^{\text{capex}}$ | 6.251506 + gas kiln rebuild 0.762636 + train 10.794818 | **17.808960** |
| $Z^{\text{opex}}$ | kiln 0.81840071 × 4.01633 = 3.286967; grinders 1.23767798 × 1.13747 = 1.407822; motor 0.012680; train 4.963468 | **9.670937** |
| $Z^{\text{fuel}}$ | gas (3.43711928 + 0.97125513) = 4.40837441 × 7.53 = 33.195059; electricity (0.36221680 + 0.17891542) = 0.54113221 × 30.45 = 16.477476 | **49.672535** |
| $Z^{\text{carbon}}$ | above | **31.373277** |
| $-Z^{\text{exp}}$ | tariff on 0.511187 Mt | **20.447476** |
| **Total** | | **£128.973186m** |

### 8.5 The pathway, and the objective

| | 2021 | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|---|---|---|---|---|---|---|---|
| `kiln_dry_coal` dispatch (Mt clinker) | 0.738431 | 0 | 0 | 0 | 0 | 0 | 0 |
| `kiln_dry_gas` dispatch (Mt clinker) | 0.111568 | 0.747200 | 0.747200 | 0.747200 | 0.747200 | 0.747200 | 0.747200 |
| `grinder_mixer_elec` (Mt cement) | 1.130000 | 0.452000 | 0.452000 | 0.452000 | 0.452000 | 0.452000 | 0.452000 |
| `grinder_mixer_clinker_sub_elec` (Mt cement) | 0 | 0.678000 | 0.678000 | 0.678000 | 0.678000 | 0.678000 | 0.678000 |
| `ccs_amine` captured (Mt CO₂) | 0 | 0 | 0 | 0.511187 | 0.511187 | 0.511187 | 0.511187 |
| Built (capacity) | | gas kiln 0.696201; sub grinder 0.742607 | grinder 0.495071 | gas kiln 0.122199; train 0.559898 | motors 0.176842 | | |
| Natural gas import (PJ) | 0.513213 | 3.437119 | 3.437119 | 4.408374 | 4.408374 | 4.408374 | 4.408374 |
| Coal import (PJ) | 3.396785 | 0 | 0 | 0 | 0 | 0 | 0 |
| Electricity import (PJ) | 0.420005 | 0.362217 | 0.362217 | 0.541132 | 0.541132 | 0.541132 | 0.541132 |
| Vented `co2_process` (kt) | 446.249769 | 392.279918 | 392.279918 | 39.227992 | 39.227992 | 39.227992 | 39.227992 |
| Vented `co2_fuel_fossil` (kt) | 329.572340 | 173.684924 | 173.684924 | 66.448073 | 66.448073 | 66.448073 | 66.448073 |
| Vented `co2_fuel_biogenic` (kt, zero-rated) | 0.301708 | 2.020614 | 2.020614 | 0.773043 | 0.773043 | 0.773043 | 0.773043 |
| **Direct emissions charged, net of credit** (kt) | **775.822109** | **565.964842** | 565.964842 | **103.857513** | 103.857513 | 103.857513 | 103.857513 |

**Annual cost by term, and the objective** (the run's `cost_by_term` table, £m):

| Period | Capex | Opex | Fuel | Carbon | Export (tariff) | Annual total | $\delta_t$ | Discounted |
|---|---|---|---|---|---|---|---|---|
| 2021 | 0.000000 | 5.236015 | 27.916686 | 189.665231 | 0 | 222.817932 | 3.801637 | 847.0729 |
| 2025 | 5.488877 | 8.876882 | 52.543332 | 146.981070 | 0 | 213.890160 | 4.072319 | 871.0289 |
| 2030 | 6.251506 | 8.032189 | 37.405554 | 158.521093 | 0 | 210.210341 | 3.428783 | 720.7656 |
| 2035 | 17.808960 | 9.670937 | 49.672535 | 31.373277 | 20.447476 | 128.973186 | 2.886943 | 372.3383 |
| 2040 | 17.844645 | 9.670937 | 49.231186 | 33.835739 | 20.447476 | 131.029983 | 2.430729 | 318.4983 |
| 2045 | 17.844645 | 9.670937 | 49.482487 | 36.450871 | 20.447476 | 133.896416 | 2.046608 | 274.0335 |
| 2050 | 17.844645 | 9.670937 | 49.934799 | 39.267487 | 20.447476 | 137.165344 | 1.723189 | 236.3619 |
| **Discounted by term** | **205.8472** | **171.4799** | **898.7457** | **2,178.2109** | **185.8158** | | | **3,640.0994** |

The discounted column sums to **£3,640.0994m**, the objective. **Carbon is 59.8% of it**, and
most of that is the three periods before capture: 2021 to 2030 carry £1,863.1m of the £2,178.2m.

Three features of this pathway:

- **Fuel switching does most of the fuel CO₂ work, and none of the process CO₂.** The move from
  coal to gas takes fuel CO₂ from 329.57 to 173.68 kt a year; the calcination CO₂ falls only
  through clinker substitution (446.25 to 392.28) and capture (to 39.23).
- **Capture runs as soon as it may.** It is worth £90.6m a year net at 2035, so the 2035
  `earliest_year`, not the economics, decides when it starts.
- **The direct-emissions floor is the reboiler.** Of the 103.86 kt charged from 2035, 49.08 is
  the train's own reboiler stack, which the train does not capture.

#### 8.5.1 What the specification does here that the slice does not build

The slice builds a narrower problem than the specification describes. These are the gaps that
remain at this premise. None is built, so none moves the run's figures; the figures below are
arithmetic on the run, not results of the missing mechanisms.

- **The base-year carrier-mix rule.** Under §4.1 tier 1 the 2021 dispatch is pinned to the
  stated `capacity_share`, 0.740664 Mt of clinker on coal and 0.109336 on gas, which is what
  §1.2's fuel rows encode. The slice builds no carrier-mix rule and reads no `premise_energy`,
  so the LP picks 0.738431 and 0.111568. The base year's fuels therefore differ from the
  premise's rows, by 0.3% on coal and 2.0% on gas, and its electricity not at all.
- **C11 (connection capacity) and the peak rebuild.** Not built, and the connection rows are
  collected without being read. The method for rebuilding peak with λ (the peak factor, §5.6)
  is open under T23 (complete §5), and this premise supplies no operating profile, so no peak
  is computed. **Mean flow alone says C11 would bind on gas.** From 2025 the kiln draws
  3.437119 PJ a year, a mean of 3.437119 × 277,778 MWh ÷ 8,760 h = **109.0 MW**, and from 2035
  4.408374 PJ, **139.8 MW**, against `C-02`'s 20 MW `import_capacity`; electricity's mean is
  17.2 MW against `C-01`'s 25 MW, which binds if λ exceeds 25 ÷ 17.2 = 1.46. The 20 MW gas
  connection is not a data defect: it covers the base year's 0.502947 PJ (15.9 MW mean) and the
  gas cohort at full output (16.3 MW). Under the specification the coal-to-gas switch would
  either pay for transmission-scale gas reinforcement or not happen as it does here.
- **Reinforcement $w_{k,t}$ and $Z^{\text{net}}$.** Not built, so no reinforcement cost.
- **C12 (siting cap) and PV.** Not built. `pv_rooftop` is admitted but gets no variable, and
  with no `available_area` the specification's area would be the footprint proxy, whose
  usable-area ratio nobody owns yet.
- **Storage.** `battery_2h` is dropped by the screen (no coefficients), so β, its
  firm-capacity contribution to C11, is never exercised.
- **Early retirement and stranding.** C4 (incumbent ageing) is an equality in the slice, so the idle coal kiln
  stands and pays 0.82780055 × 4.01633 = £3.32m of fixed opex a year in 2025 and 2030. The
  specification would let it retire early against a stranding charge whose formula is still
  unwritten (§13.3, point 6).
- **The retrofit's host life.** Not built (§8.4); it would not bind within the horizon here.
- **A1's named checks, the evidence tiers on output rows and §7.6's reconciliation.** Not in the
  slice's code (§2, §9, §10.2).
- **Sizing from the meter, and any check against it.** The specification sizes every process
  from §3.3.1's shares of the base-year meter, or from §3.10.1's sub-meters, so the meter is
  allocated in full by construction (within V28's 1.00 ± 0.015, process energy). The slice
  sizes from `known_activity` only and never loads `premise_energy`, so a process left blank
  that does draw energy drops out of the base year unreported (§3.2). No §5.7 check closes the
  gap, in the specification or the slice: all six test units, duties or the solved matrix, none
  the meter. Here the gap is zero, because §1.5's activities were written from §3.2's shares.
- **Imports and exports per connection.** The slice holds them site-wide, as $m_{c,t}$ and
  $x_{c,t}$.

### 8.6 The relaxation ladder (§4.2)

This premise is feasible at every period, so no rung is used. The ladder's order is
**C6 → C7 → C4b → C12 → C10 → C11 → C9 → C1** (C6 unit stability, C7 known changes, C4b forced ageing, C12 siting cap, C10 grade cascade,
C11 connection capacity, C9 infrastructure availability, C1 duty satisfaction). In the slice,
of these only C4, C9 and C1 have rows here, and none binds infeasibly. Under the
specification C11 (connection capacity) is the rung this works would reach first: on the gas
connection, by the margin §8.5.1 shows. Relaxing it must be loud, because it asserts a network
reinforcement nobody has costed.

---

## 9. `A8`: the output rows and their evidence tiers

**What the slice writes.** With `--out-dir`, eleven parquet tables under `<dir>/mvp-cement/`:
`dispatch`, `build`, `carrier_mix`, `cost_by_term`, `unit_flow`, `disposal` and
`capture_by_host` from the ledger, and `run_report`, `screen_dropped`, `eligibility_dropped`
and `sub_minimum_recovery` from the run report. Every figure in §8 is read from them:
`unit_flow` keeps each unit's legs gross, so the train's `emission_input` (−156.316432 kt of
`co2_fuel_fossil` at 2035) and its derived reboiler `emission` (+49.079581) are separate rows,
while `carrier_mix` nets them per unit to 107.236851 kt consumed.

§8 of the specification is **not written** (`MF-20`, the §8 output schema; `T6`, its
remainder), so the evidence-tier fields below are what the specification's rules give at this
premise, not columns the slice writes. One row, `kiln_dry_gas` on `natural_gas` at 2035:

| Field | Value |
|---|---|
| `premise_id` | `mvp-cement` |
| `unit_id` / `carrier_id` / `role` | `kiln_dry_gas` / `natural_gas` / `fuel_input` |
| `period` | 2035 |
| `flow` | −3.437119 PJ/yr |
| `process_evidence_tier` | `site_known` (§3.1) |
| `mix_evidence_tier` | `site_known` (§5.2) |
| `year_evidence_tier` | `base_year` on every carrier |
| `vintage_evidence_tier` | built by the model, so none; the incumbent gas cohort's rows carry `process_known` |
| `area_evidence_tier` | `proxy` once C12 is built (§1.4) |
| `archetype_evidence_tier` | `default`: no Tier A run exists (`MF-15`, a Could) |
| `carrier_coverage` | complete (§1.2) |
| `data_status` | `modelled` on the energy it rests on (§1.2) |

**Every row carries every tier**, which is `D10`'s (tiered site intelligence) stated cost: the
quality is invisible unless each row says what it rests on. `V23` (one carrier-mix tier per unit) asserts that
`mix_evidence_tier` in particular appears on all of them. A9 (roll-up and comparison) rolls the
rows up to GB and compares against ECUK, the inventory and the emissions budget, reported and
never enforced.

---

## 10. §7: emissions attribution and reconciliation

### 10.1 Attribution, base year

| # | Rule | At this premise, 2021 |
|---|---|---|
| 7.1 | Fuel CO₂ to the unit consuming the fuel; process CO₂ to the chemistry unit on its mass denominator | coal's 303.638587 kt to `kiln_dry_coal`, gas's 25.933754 to `kiln_dry_gas`; calcination split on clinker output, 387.676518 and 58.573251 kt |
| 7.2 | Non-CO₂ gases separate; capture never abates them | vacuous: no non-CO₂ row is stated here |
| 7.3 | **Biomass zero-rated before capture** | gas's 0.0115 biogenic share goes to `co2_fuel_biogenic`, 0.301708 kt, vented free; from 2035 the captured 1.818552 kt is a credit (§8.4) |
| 7.4 | Direct versus indirect is a property of the carrier | `electricity.is_indirect` = true; every other carrier here is direct |
| 7.5 | Reporting categories may overlap | each kiln appears under combustion and under process |
| 7.6 | Reconciliation at the base year | skipped (§10.2) |

**Direct emissions are read off the balance (D15), not computed beside it.** §7's expression is
the one the objective charges, so the reported and the costed totals cannot drift apart:

$$\text{direct}_t = \sum_{c\,:\,\text{charged}} d_{c,t} - \sum_{c\,:\,\text{zero\_rated}} \Gamma_{c,t}$$

| Term, 2021 | Computation | kt CO₂ |
|---|---|---|
| $d_{\text{co2\_process}}$ | 0.84999956 Mt × 525 | 446.249769 |
| $d_{\text{co2\_fuel\_fossil}}$, coal | 3.39678473 PJ × 89.39 | 303.638587 |
| $d_{\text{co2\_fuel\_fossil}}$, gas | 0.51321325 PJ × 50.53212 | 25.933754 |
| $d_{\text{co2\_fuel\_biogenic}}$ | 0.51321325 PJ × 0.58788 | 0.301708, zero-rated |
| Biogenic captured | none before 2035 | 0 |
| **Direct total** | | **775.822109** |
| Indirect, on the import (§7.8) | 0.42000465 PJ × 58.02 | 24.368670, reported |

`V30` (emissions close through the balance) holds: 775.822109 kt × £244.47/t × 10⁻³ =
£189.665231m, the carbon term of §8.1. At 2035 the same identity gives 103.857513 kt and
£31.373277m.

### 10.2 §7.6 reconciliation

**Skipped.** `mvp-cement` states no `premise_measured_emissions` rows (§1.7), so there is no
base-year measurement to reconcile against, and §3.11's rule makes that a report
(`emissions_year_unmatched`) rather than a rejection. The slice does not implement the
reconciliation in any case. A premise with a measured UK ETS figure is needed to exercise the
branch where it runs.

---

## 11. What this fixture asserts

Tests are the specification's, at §10.3. Scope is `load`, `premise` or `release`. "The run"
means the `carb3` slice on this premise, and "data-check" means `make data-check`.

| # | Scope | Asserted here as |
|---|---|---|
| **V1** (the coupled-off R run), **V1b** (reproduce its objective and energy) | release | *not asserted by this fixture*: the coupled-off R run is `MF-57`, and the comparison is §10.2's (see §13.3, point 13) |
| **V2** (unit coefficients round-trip) | load | §1.11: coefficients round-trip against `capacity_to_activity_factor`, and no unit puts out more energy than it takes in (data-check) |
| **V5** (emissions invariants, biomass before capture) | premise | §8.4: biogenic CO₂ is zero-rated before capture, so the captured 1.818552 kt is a credit of £0.549m at 2035, not lost |
| **V6** (no cost term assumed non-negative) | premise | §7.4: no cost term is assumed non-negative; the export term here is a *cost*, the tariff on captured CO₂ |
| **V10** (determinism) | release | two runs of this fixture agree under the §9.3 tie-break |
| **V11** (one process tier) | load | §3.1: one process tier resolves, `site_known` |
| **V17** (vintage and stranding per unit) | premise | §5.3: incumbents stand whole to their known last year at tier 1; the abatement leg is not built in the slice (§8.4) |
| **V18** (carrier balance closes) | premise | §8.1: all eleven carrier nodes close to 1e-6 in every period, including `clinker` (D16) and the three CO₂ carriers; the run's row check finds 0 violations |
| **V19** (no unit above its grade) | load | vacuous: no duty carries a grade |
| **V22** (attribution closes across a chain) | premise | (a) only primary, non-indirect carriers derive emissions: coal and gas do, electricity does not; (b) and (c) untestable here, since the reject heat feeds nothing |
| **V23** (one carrier-mix tier) | load + premise | §5.2: the mix resolves at tier 1, `site_known`; the slice does not pin to it |
| **V26** (disjoint validity intervals) | premise | §1.5: `kiln_pyroprocessing`'s two intervals are disjoint and only the 2004 one is read |
| **V27** (unit fuel identity) | load | §1.11: each unit has at most one `fuel_input`; `ccs_amine`'s electricity is `aux_input` |
| **V28** (process energy) | load + premise | §3.2: the `Cement Works` electricity shares sum to 1.00, and the oil vector renormalises over the processes this premise runs |
| **V29** (disposal and allocation) | premise | §8.1: disposal only on `may_dispose` carriers, the three CO₂ carriers and `heat_lt60`, each a row of the run's `disposal` table |
| **V30** (emissions close through the balance) | premise | §10.1: §7's direct total equals the carbon term ÷ π × 10³ in every period, net of the biogenic credit |
| **V31** (role and sign agree) | load | §1.11: `ccs_amine` holds `co2_fuel_fossil` and `co2_fuel_biogenic` twice, as `emission_input` (the rate −0.9) and as the derived reboiler `emission`; every sign agrees with its role |
| **V32** (the site boundary is honoured) | load + premise | §1.4, §1.11: exports exist only for `co2_captured` (at `C-03`); `clinker` gets neither import nor export and no duty; electricity's export is refused for want of a price in every period |
| **V33** (plant is named one unit at a time) | load + premise | §1.5.1, §1.11: every `premise_process_unit` row names an eligible unit, the kiln's shares sum to 1, and `ccs_amine`'s four hosts are `converter` units on `kiln_pyroprocessing`, none of them itself |
| **V36** (reject heat by source class) | load | §1.11: the kilns' reject lands on `heat_lt60` (data-check) |
| **V37** (a capture rate is a fraction of its hosts' streams) | load + premise | §1.11, §8.4: the three rates lie in [−1, 0); after the solve, no stream is captured above 0.9 of its host's production, the streams are pro rata, the host is treated once, and the credit is π × Γ on the biogenic stream; the run's capture check finds 0 violations |

**What the slice checks itself.** Check 4 of §5.7 (the row check) covers V18 (carrier balance closes) and the C8 half of
V30 (emissions close through the balance); check 6 (the capture check) covers V37's post-solve legs; `make data-check` covers the load
legs of V2 (round-trip and energy closure), V27 (unit fuel identity), V31 (role and sign
agree), V36 (reject heat by source class) and V37. The rest are asserted by this document and wait for their
tests.

---

## 12. The published fixture (`MF-22`)

`MF-22` (the cement worked example as a fixture) is a Must at milestone M0, and is M2's gate.
The fixture is the premise, the reference data and the expected tables, all of which exist
in the repository today:

| Artefact | Content |
|---|---|
| `carb3/data/premises/*.csv`, rows `mvp-cement` | §1.1 to §1.10 |
| `docs/notes/data/*.csv`, and its subset `carb3/data/reference_mvp/` | §1.11, §1.12, §6 |
| the run's eleven parquet tables | §8's results: dispatch, builds, the carrier balance, disposal, capture by host and the cost decomposition |

**Units and rounding.** Money £m at 2021 prices, energy PJ/yr, mass Mt/yr, emissions kt
CO₂/yr. Figures are compared at six decimal places, the precision the run prints.

**Solver settings**, pinned in the package so `V10` (determinism) can hold across machines:
HiGHS, presolve on, single-threaded.

**What M2's gate does with it** (`MF-22`, `MF-59`): the fixture solves to the objective of §8.5
and the tables of §8; V18 (the carrier balance, all eleven nodes including `clinker`), V30 (emissions close through the balance), V32
(the site boundary on the carrier) and V37 (per-stream capture) pass; the row check verifies
every constraint row independently of the solver; and G1 (single-premise wall clock) is
measured and recorded with its machine and settings.

---

## 13. What this example demonstrates, and what it leaves open

### 13.1 What it demonstrates

1. **The mass denominator is load-bearing (`D5`).** The kiln's 525 kt of process CO₂ per Mt of
   clinker comes from the limestone, so it scales with clinker, not with fuel: the switch to gas
   leaves it untouched, and only clinker substitution (§8.2) and capture (§8.4) reduce it.
2. **An internal product is a carrier, not a duty (`D16`).** `clinker` has no duty; the kilns
   release it to the balance, the grinders draw it, and the node closes. When the grinder
   substitutes clinker the kilns simply make less, with no duty to restate.
3. **Clinker substitution is a chemistry decision the balance makes.** The substituting grinder
   is worth about £42.7m a year per Mt of cement against £2.9m of cost, so its 0.60 cap binds
   from the first buildable period (§8.2).
4. **Plant age decides when, not whether** (§1.6, §8.3). The grinder, the gas kiln cohort and
   the motors are rebuilt exactly when their stated cohorts end; the coal kiln stops running at
   2025 while it still stands, because nothing compels an incumbent to run.
5. **A capture train treats a flue gas** (C14, a capture train treats its hosts' flue gas, §8.4). It captures 0.9 of every stream of the
   activity it treats, in the host's own proportions: 353.05 kt of process, 156.32 kt of fossil
   and 1.82 kt of biogenic CO₂, 0.511187 Mt a year.
6. **Biomass zero-rating before capture makes captured biogenic CO₂ a credit** (§8.4). Small
   here, because mains gas is 1.15% biogenic; the rule is the same at a works co-firing waste
   fuel, where it is large.
7. **The reboiler is the floor.** The train's own stack, 49.08 kt a year, is vented and charged
   (§1.11, §8.4); netting it into the capture rate would have hidden it.
8. **The screen is what makes a cost minimiser honest.** Waste-derived fuel and the other four
   trains are dropped because they cannot be fully costed (§3.3), not because they are bad
   choices.
9. **Peak and energy are different questions** (§8.5.1). The energy pathway is affordable; the
   gas connection, on mean flow alone, is not.

### 13.2 What it cannot show

- **One grade only, so no cascade.** `heat_lt60` is the only gradeable carrier and nothing
  draws it, so C10 (the grade cascade) has nothing to filter and the reject heat is disposed.
- **No low-grade duty, so no waste-heat sink.** Representing the recovery a cement works
  actually runs, kiln exhaust drying raw meal, needs per-unit reject coefficients
  (data migration B5, `MF-12`, a Should at milestone M6).
- **No unit competition at a heat duty.** The kiln's candidates differ by fuel, not by device.
- **No CHP, no PV, no storage in the model** (§8.5.1).
- **No reconciliation** against measured emissions (§10.2).
- **V22 (b) and (c) untestable**: there is no intermediate-carrier chain to follow.

The cascade, unit competition, CHP and PV are demonstrated on the
[food and drink premise](2026-08-28-carb3-site-energy-system-worked-example-food-drink.md),
which is why §13 of the specification says cement alone is not sufficient.

### 13.3 Open points against the specification

Fourteen points have been raised against the specification by working this premise; ten are
closed and four remain open, and they are kept with their resolutions because the record of *why* a rule exists is
what stops it being undone.

| # | Point | Status |
|---|---|---|
| 1 | Where a process's share of premise energy comes from | **Closed**: §3.3.1 `activity_process_energy_share`, which §3.2 above runs on |
| 2 | No per-premise tier over that table | **Closed**: §3.10.1 `premise_process_energy` |
| 3 | C8 admitted no disposal route, so vented process CO₂ could not balance | **Closed**: $d_{c,t}$ (§5.2), gated on `may_dispose` |
| 4 | §7 double-counted once electricity was generated on site | **Closed**: §7.8 charges an indirect carrier on the import; §7.7 allocates |
| 5 | A `MOT` or `REF` duty had no carrier that kept C8 acyclic | **Closed**: the service carriers of §3.4, `motive_power` among them |
| 8 | `premise_process_detail.unit_id` was singular, and D13 splits a co-firing kiln into units | **Closed**: §3.10.2 `premise_process_unit`, one row per cohort (§1.5.1) |
| 9 | A product consumed downstream had no route through C8 that also satisfied C1 | **Closed**: D16, which gives `clinker` no duty (§3.2, §8.1) |
| 10 | A fired capture train needs two coefficients on one carrier | **Closed**: §3.6's key `(unit_id, carrier_id, role)` (§1.11) |
| 11 | `abates_unit_id` was singular, and a train abates several kiln units | **Closed**: §3.5.3 `unit_abatement_host` (§1.11) |
| 12 | A6 would derive fuel CO₂ on `electricity` and §7.8 charge it again | **Closed**: A6 derives only for carriers that are not `is_indirect` (§1.11) |

Four remain open:

| # | Open point | Where it bites | Closed by |
|---|---|---|---|
| **6** | **The stranding formula is not written.** $Z^{\text{strand}}$ is named in §5.4's objective and has no defining expression | §5.3, §8.5.1: the idle coal kiln could retire early against a charge nobody can compute | `T23` (complete §5) / `MF-18` |
| **7** | **§5.6 defines only the peak factor λ**, so nothing says how C11's peak is rebuilt or which year it reads | §8.5.1: the gas connection's breach is shown on mean flow only | `T23` / `MF-18` |
| **13** | **§10.2's condition 5 forbids every export, and the parity case exports captured CO₂.** COMIT's capture bundles keep the CO₂ inside the technology; this model routes it out through `C-03` at a tariff, a cost and not a revenue | §11: `V1b` (reproduce the R run's objective and energy) cannot compare this premise as §10.2 is written | an amendment to §10.2 naming a tariffed CO₂ export as compatible with the comparison |
| **14** | **§3.10 and A2 (duties and candidate units) disagree on what sizes a process.** §3.10's precedence rule says `known_activity` sizes the duty and that a row with neither `known_activity` nor `known_capacity` yields no duty and no incumbent capacity; §4 has A2 size every process from §3.3.1's shares or §3.10.1's sub-meters, which needs neither field | §3.2: the four motor stages get the same duties by either route only because §1.5's activities were written from the shares. A premise that leaves a running process blank gets a duty under A2 and none under §3.10, and the slice follows §3.10 | an amendment to §3.10 saying which route wins where both apply, and a §5.7 check that the base year's imports per vector reconcile with `premise_energy` |

One thing stated rather than filed: **the objective charges direct carbon only** (§6.3).
§5.4 charges what is vented, and both worked examples report indirect emissions without
charging them.

---

## Sources

- Implementation specification §1.6, §3.1 to §3.17, §4.1, §5.1 to §5.7, §7, §9.3, §10.2 and
  §10.3, §13.
- The `carb3` slice: [`carb3/README.md`](../../carb3/README.md), the premise tables in
  [`carb3/data/premises/`](../../carb3/data/premises/) and the run of §8.
- Reference data in [`docs/notes/data/`](../notes/data/): `carrier.csv`, `unit.csv`,
  `unit_input_output.csv`, `unit_abatement_host.csv`, `unit_eligibility.csv`,
  `activity_default_unit.csv`, `activity_process_energy_share.csv`,
  `activity_process_register.csv`, `activity_process_duty_profile.csv`,
  `comit_technology_lineage.csv`, `infrastructure_scenario.csv` and `scenario_parameters.csv`.
- [Delivery document](2026-08-28-carb3-site-energy-system-delivery.md): `T10` (this example),
  `T23`; [data migration](2026-08-28-carb3-site-energy-system-data-migration.md) groups B and
  B5.
- Notes [18](../notes/18_mvp_feature_prioritisation.md) (`MF-09`, `MF-12`, `MF-15`, `MF-18`,
  `MF-20`, `MF-22`, `MF-57`, `MF-59`), [20](../notes/20_reference_data_open_questions.md)
  items 55, 57 and 58, and [24](../notes/24_ccs_per_stream_capture_plan.md), per-stream capture.
- **[DECC_SURPLUSHEAT2014]** *The potential for recovering and using surplus heat from
  industry*, Element Energy, Ecofys and Imperial College London for DECC, March 2014,
  section 5, p.24 and Figure 5: 11 TWh/yr of technically recoverable industrial waste heat
  against ca. 291 TWh/yr of industrial energy use, behind the kilns' `reject` coefficient.
- The [archived worked example](archive/2026-08-19-carb3-site-decarbonisation-worked-example.md),
  which walks a hand-built cement premise against the COMIT-parity baseline.
