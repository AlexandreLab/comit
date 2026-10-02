# Synthetic premise tables

The premise side of the pre-M2 demonstration slice
([note 21](../../../docs/notes/21_mvp_slice_implementation_plan.md) §3.4): three synthetic
premises, hand-authored, **CSV so every file a human edits stays diffable**. Outputs and any
M2 fixture are parquet.

The reference side — `docs/notes/data/` — is **read, never written**. Nothing here modifies a
single row of it.

## The tables

| File | Spec | What it carries |
|---|---|---|
| `premise_record.csv` | §3.1 | One row per premise: identity, `carb3_activity`, location, `cluster_id`, base year |
| `premise_connection.csv` | §3.1.3 | One row per networked connection. Delivered fuels carry no row and need none. **Read**: §5.2 declares an export only where a row carries the carrier |
| `premise_energy.csv` | §3.1.1 | Base-year consumption by carrier. Required entity; A1 (ingest and validate) rejects `no_energy` without it |
| `premise_throughput.csv` | §3.1.2 | Base-year physical output. Required where the activity has a mass-denominated process. **Read**: an exportable product's row is the premise's D5 mass duty |
| `premise_process_detail.csv` | §3.10 | Which processes run, over which validity interval, at what capacity |
| `premise_process_unit.csv` | §3.10.2 | Which units each process runs, one row per cohort, and when each cohort was installed (D11, existing plant has an age) |
| `verify_premise_keys.py` | — | Stdlib key- and rule-checker. See [Verification](#verification) |

**`process_duty` is not here.** §3.9 derives it at run time by A2 (duties and candidate
units), in its relaxation-free minimal form, from `activity_process_register` and
`activity_process_duty_profile` — **and, from 2026-09-20, from `premise_throughput` for a
product duty**. The duty profile carries no mass carrier anywhere, so a cement works' 1.13
Mt/yr cannot come from it; §3.1.2 says the throughput row on an exportable product *is*
that duty. See [finding 6](#findings-for-the-reference-data).

**`premise_record` carries a `cluster_id` that §3.1 does not define.** §3.7's rule is that
A1 assigns the nearest in-scope cluster on ingest, and A1 is out of scope, so C9
(infrastructure availability) has nothing to read unless the assignment is written down.
`mvp-cement` is `humber` and the two Food Processing Centres are `mersey`, matching the two
worked examples' own §6.2. A premise with no `cluster_id` is treated as outside every
cluster. Recorded as a specification gap in
[note 20](../../../docs/notes/20_reference_data_open_questions.md) item 58.

**Four tables were commissioned; six are written.** `premise_process_vintage`, the fourth, was merged into `premise_process_unit` on 2026-10-01, because the two held the same units and the same shares twice. `premise_connection`, `premise_energy`
and `premise_throughput` are the three §3.1 companions. §3.1 declares `premise_energy`
and `premise_throughput` **required** alongside `premise_record`, and `premise_connection`
optional. Without `premise_throughput`, the cement premise has no `cement` duty at all:
nothing draws clinker, the kiln never runs, and the process-CO₂ and capture-train
behaviour the premise exists to exercise never happens. They are small and they are the
spec's own shape, so they are written rather than deferred.

## Field reference

Every field in the six tables, with what it means and a value from these premises. The
spec section in each heading is the authority; this is the plain reading of it. **The base
year (`premise_record.data_year`) is 2024 for all three premises**, and it is the only year
the model reads.

**Reading the Key column.** **PK** marks the fields that together identify a row: no two rows
may share them, and "PK part" means the field is one of several that do so together. **→**
means the value must exist in another table, so the field is a link to it. "Pointed to by"
names the tables whose fields link to this one. A link that uses several fields at once, such
as `premise_process_unit`'s `(premise_id, process_id, valid_from_year)`, is described on each
of its fields.

### `premise_record` (§3.1): the premise itself

One row per premise.

| Field | Required | Key | What it means | Example |
|---|---|---|---|---|
| `premise_id` | yes | **PK**. Every other premise table points here | The premise's unique, stable identifier. Every other table joins on it | `mvp-cement` |
| `carb3_activity` | yes | → `activity_process_register.csv` | The CaRB3 activity class. It selects the default process list in `activity_process_register.csv` | `Cement Works` |
| `latitude`, `longitude` | yes | | Location in degrees. Must fall inside the GB bounding box | `53.35`, `-1.75` for `mvp-cement` |
| `nation` | yes | | England, Wales or Scotland. Northern Ireland is out of scope | `England` |
| `cluster_id` | no | → `infrastructure_scenario.csv` | The industrial cluster the premise sits in, read by C9 (infrastructure availability) for hydrogen and CO₂ access. **Not a §3.1 field**: the spec has A1 assign it on ingest, and A1 is not built, so it is written down here (note 20 item 58). Blank means outside every cluster | `humber` for `mvp-cement`; `mersey` for the two food premises |
| `floorspace` | no | | Floor area in m² | `46000` for `mvp-cement` |
| `process_set_id` | no | → `activity_process_register.csv` | Picks a named, non-default process set for the activity. Blank means the activity's default set | blank on all three |
| `construction_year` | no | | The year the premise was built. The upper bound on plant age for a unit with no `commissioned_year` (D11, existing plant has an age). Must be ≤ `data_year` | `1957` for `mvp-cement`; `2009` for `mvp-minimal` |
| `construction_year_band` | no | | A build-year range, used only when `construction_year` is blank, read as its earliest year | `1965-1984` for `mvp-dairy`, read as 1965 |
| `last_refurbishment_year` | no | | Collected for future use; nothing reads it. A refurbishment does not reset plant age | `2011` for `mvp-cement` |
| `data_year` | yes | | **The base year**: the one year of measured data the model reads (D12, one base year) | `2024` on all three |
| `source` | yes | | Where the row came from | `synthetic - cut from the cement worked example section 1.1 (premise P-000123)` |

### `premise_connection` (§3.1.3): the site's network connections

One row per networked connection. A delivered fuel (coal by road, oil by tanker) has no
row and needs none.

| Field | Required | Key | What it means | Example |
|---|---|---|---|---|
| `premise_id` | yes | **PK** part; → `premise_record` | The premise | `mvp-cement` |
| `connection_id` | yes | **PK** part. Pointed to by `premise_energy.connection_id` and `premise_process_detail.connection_id` | The connection's name, unique within the premise. Other tables point at it | `C-01` |
| `carrier_id` | yes | → `carrier.csv` | Which network it connects to | `C-01` is `electricity`, `C-02` is `natural_gas`, `C-03` is `co2_captured` |
| `import_capacity` | no | | Maximum import in MW. Capacities are never summed across connections: each is its own limit in C11 (connection capacity) | `25` MW on `C-01`; `0` on `C-03` |
| `export_capacity` | no | | Maximum export in MW. A site exports a carrier only through a connection carrying it. **Blank means 0 for an energy carrier**: no export. A mass carrier is not bounded by it (a MW figure cannot bound a mass flow) | `2` MW on `mvp-dairy`'s `E-01`; blank on `C-03`, but `co2_captured` is mass, so its export is not bounded by the connection |
| `connection_voltage` | no | | Voltage in kV, for electricity connections | `11` kV on `mvp-dairy`'s `E-01`; `33` kV on `mvp-cement`'s `C-01` |
| `available_area` | no | | Roof plus land in m² available for onsite generation, read by C12 (siting cap). Without it PV is unbounded | `12000` m² on `mvp-dairy`'s `E-01`; blank on `mvp-cement` |

### `premise_energy` (§3.1.1): what the site consumes, by carrier

One row per carrier, per connection, per year. Required: a premise without it is rejected.

| Field | Required | Key | What it means | Example |
|---|---|---|---|---|
| `premise_id` | yes | **PK** part; → `premise_record` | The premise | `mvp-dairy` |
| `carrier_id` | yes | **PK** part; → `carrier.csv` | The carrier as metered | `natural_gas` |
| `connection_id` | no | **PK** part; → `premise_connection` | The connection the quantity came through. Blank means the premise's default connection | blank on every row here |
| `vector` | yes | | The broad grouping (electricity, gas, oil, coal, biomass, other) used to join the duty profile | `gas` for `natural_gas`; `other` for `waste_derived_fuel` |
| `quantity` | yes | | Annual consumption in PJ/yr, ≥ 0 | `0.300000` PJ/yr of gas at `mvp-dairy` |
| `data_status` | yes | | measured, estimated, modelled, or `not_consumed`. **A carrier known not to be used is written as a zero with `not_consumed`**, because a missing row means "nobody checked", not "zero" | `measured` for `mvp-dairy`'s gas; `not_consumed` for its coal; `modelled` for all of `mvp-cement` |
| `data_year` | yes | **PK** part | The year the quantity was measured. Only the base-year row is read; other years are history | `2024` on every row |
| `source` | yes | | Where this carrier's figure came from | `synthetic - duty 0.100000 PJ/yr through boiler_lt_gas at 1.13636 PJ gas per PJ heat` |

### `premise_throughput` (§3.1.2): what the site makes, by mass

One row per product carrier per year, in Mt/yr. Needed where the activity has a
mass-denominated process (D5, hybrid denominators: energy in PJ, chemistry in Mt).

| Field | Required | Key | What it means | Example |
|---|---|---|---|---|
| `premise_id` | yes | **PK** part; → `premise_record` | The premise | `mvp-cement` |
| `carrier_id` | yes | **PK** part; → `carrier.csv` | The product. Must be a mass carrier. If the carrier may be exported, this row **is** the site's demand for it; if not, it is evidence only (D16, the site boundary is a property of the carrier) | `cement` is exported, so it is the 1.13 Mt/yr duty; `clinker` is not, so its row is evidence only |
| `quantity` | yes | | Annual output in Mt/yr, > 0 | `1.130000` Mt/yr of cement; `0.850000` Mt/yr of clinker |
| `data_year` | yes | **PK** part | The year it was measured. Only the base-year row is read | `2024` |
| `data_status` | yes | | measured, estimated or modelled | `measured` on both rows |
| `source` | yes | | Where the figure came from | `cement worked example section 1.3 base-year row` |

### `premise_process_detail` (§3.10): which processes the site runs, when, and how big

Optional. One row per process per validity window. Where it is given, it replaces the
activity's default process list, and **the rows valid in a year are the site's complete
process list for that year**.

| Field | Required | Key | What it means | Example |
|---|---|---|---|---|
| `premise_id` | yes | **PK** part; → `premise_record` | The premise | `mvp-cement` |
| `process_id` | yes | **PK** part; → `activity_process_register.csv`, on `(carb3_activity, process_id)` | The process. Must exist for the premise's activity in `activity_process_register.csv` | `kiln_pyroprocessing` |
| `valid_from_year` | yes | **PK** part. The full key `(premise_id, process_id, valid_from_year)` is what `premise_process_unit` points to | The year this version of the process **started at the site**. A new version opens only when a fact on this row changes (`connection_id` or `known_capacity`), never because plant was replaced: see §3.10, "what opens a new version". It can't be later than the base year, because a planned future change isn't an observation. If the start year is unknown, write the base year and say so in `provenance`. With `process_id` it identifies the row, so child tables repeat it to point at their parent | `mvp-cement`'s kiln has two rows: `1957` for the old wet line and `2004` for the current dry line, which opens because the rated capacity changed from 0.70 to 0.95 Mt/yr |
| `valid_to_year` | no | | The year this version of the process **stopped**. Blank means it's still running. Must be ≥ `valid_from_year`. Windows for one process must not overlap, and only the window covering the base year is read; closed windows are history | `2003` closes the wet kiln line, which the model ignores; blank on the 2004 dry line, so that is the row read |
| `connection_id` | no | → `premise_connection` | Which electricity connection serves this process, which decides where electrified load lands. Blank means the default. **These premises put the gas connection `G-01` on gas-fired processes**, which the spec's wording (an electricity connection) does not cover | `C-01` (electricity) on every `mvp-cement` row; `G-01` (gas) on `mvp-dairy`'s boiler |
| `known_capacity` | no | | **The installed nameplate capacity** of the process's plant, in the process's output unit (PJ/yr-equivalent for an energy process, Mt/yr for a mass one). A4 (back-solve) sizes the incumbent from it directly, and `known_activity / known_capacity` is the utilisation. Must be > 0 | `0.950000` Mt/yr clinker line capacity on the 2004 kiln line; `0.700000` on the closed wet line; blank on every other `mvp-*` row |
| `known_activity` | no | | **The annual activity** in the process's output unit: PJ/yr for an energy process, Mt/yr for a mass one. A2 (duties and candidate units) splits it into duties by `duty_share`. With no `known_capacity`, the incumbent's capacity is `known_activity / (γα)`. Must be > 0, so a known zero has to be left blank with the reason in `provenance`. Must not exceed `known_capacity` when both are given | `0.850000` Mt/yr clinker on the 2004 kiln line; `0.131579` PJ/yr on `mvp-dairy`'s boiler; blank on `mvp-cement`'s `clinker_cooling` (a genuine zero) |
| `provenance` | yes | | Where the row came from, including the unit `known_capacity` and `known_activity` are in | `Mt/yr clinker line capacity; cement worked example section 1.5 permit figure` |
| `confidence` | yes | | high, medium or low. Carried through to the outputs | `high` on the 2004 kiln line; `medium` on the closed wet line |

### `premise_process_unit` (§3.10.2): which units each process runs, and when each was installed

Optional. One row per **cohort**: a batch of one unit's capacity installed in the same year,
under one `premise_process_detail` window. The rows under one window are that process's
**complete** list of plant. A window with no rows means the plant is unknown and A4 (the
carrier-mix rule) resolves it from the candidate units. It feeds D11 (existing plant has an
age); a row with no `commissioned_year` falls back to `construction_year`, then to the default.

| Field | Required | Key | What it means | Example |
|---|---|---|---|---|
| `premise_id` | yes | **PK** part; with the next two fields, → `premise_process_detail` | The premise | `mvp-dairy` |
| `process_id` | yes | **PK** part; part of the same link | The process. With `premise_id` and `valid_from_year`, points at the parent `premise_process_detail` row | `boiler_steam_hot_water` |
| `valid_from_year` | yes | **PK** part; completes the link to `premise_process_detail`, so it must equal the parent row's value | **Not a date of its own.** It names which parent window this row belongs to, so it always equals that parent row's `valid_from_year`. The rows under a window list the plant as at the end of the window: the base year for an open window, `valid_to_year` for a closed one. Only rows under the window valid at the base year are aged: plant under a closed window is gone, and ageing it would strand an asset that no longer exists | `2011` on both boiler-house rows, though the boiler was installed in 2016 |
| `cohort_id` | yes | **PK** part | The row's number within its window. `1`, `2`, … is enough | `1` and `2` on `mvp-dairy`'s boiler process |
| `unit_id` | yes | → `unit.csv`, and must be admitted by `unit_eligibility.csv` | The unit this cohort is. Must be in `unit.csv` and eligible for this process at this activity. A unit appears twice in one window only with two different `commissioned_year` values | cohort 1 is `chp_gas_turbine`, cohort 2 is `boiler_lt_gas`; `mvp-cement`'s kiln line is `kiln_dry_coal` and `kiln_dry_gas` (D13, one primary carrier per unit) |
| `commissioned_year` | no | | The year this equipment was **installed**. It can't be later than the base year. The unit is retired once `year − commissioned_year` reaches its `lifetime` in `unit.csv`. **A refurbishment does not reset it**: a 1998 kiln relined in 2019 is a 1998 cohort. It can differ from the process's `valid_from_year`, because a site can run a process for decades on newer equipment: replacing plant adds or changes a cohort and opens no new window (§3.10.2, "a parent's children are its plant list as at the end of the interval"). It can be later than the window's start or earlier (plant carried over from before), but under a closed window it can't be later than `valid_to_year` (`vintage_after_interval`). In the slice's data seven `mvp-cement` processes keep their `1957` (or `2004`) window though their synthetic plant dates from `2016` (the `motor_elec`, `generic_process_elec` and `chiller_electric` cohorts) or `1998` (the `cement_grinding` grinder), which the rule makes valid | `2011` for the CHP and `2016` for the boiler, though the process has run since `2011`; `mvp-cement`'s `grinder_mixer_elec` is `1998` on a process running since `1957`; `mvp-minimal`'s `boiler_lt_gas` is `2009` with a 25-year lifetime, so it retires in 2034 |
| `capacity_share` | no | | The cohort's share of the parent's `known_capacity`, in (0, 1]. If one row in a window gives it, every row must, and they sum to 1 (V33, plant is named one unit at a time). Blank means A4 splits by the carrier mix, which only works when each unit is a single cohort, so **a unit with two cohorts needs it stated**. The slice does not build A4, so `survival.py` refuses a window of several rows with blank shares. **A share too small for the duties only that unit can serve makes the start year infeasible**: see "Incumbents too small for the start year" below | `0.350000` CHP and `0.650000` boiler; `0.871369` coal kiln and `0.128631` gas kiln |
| `provenance` | yes | | Where the row came from, for both the unit and its install year | `cement worked example section 1.5.1 permit fuel schedule; share renormalised after dropping kiln_dry_wdf; commissioned_year: cement worked example section 1.6; share renormalised after dropping kiln_dry_wdf` |
| `confidence` | yes | | high, medium or low. Where the unit and its install year came from sources of different quality, the lower one | `high` for the CHP; `medium` for the boiler, whose install year is less certain than its presence |

---

## Where the duty magnitude lives

**`premise_process_detail.known_activity` is the premise's annual magnitude for that
process**, in PJ/yr for an energy-denominated process and Mt/yr for a mass-denominated one
(D5, hybrid denominators). A2 splits it across the process's
`activity_process_duty_profile` rows by `duty_share`.

`known_capacity` is a different quantity: the installed nameplate, stated only where a
permit gives it (the cement kiln's 0.95 Mt/yr and the closed wet line's 0.70 Mt/yr). Where
given it sizes the incumbent directly; otherwise the incumbent is `known_activity / (γα)`.
The kiln's `known_activity` is 0.850000 Mt/yr, its nameplate 0.95 times the worked example's
utilisation (§5.1: 0.85 declared throughput over 0.95 × γ 1.0 = 0.89474). Each row's `provenance` names the unit it is in.

Two consequences worth knowing before reading a number:

- **`known_activity` cannot state a known zero**: §3.10 requires `> 0 if present`. Two
  `mvp-cement` processes, `clinker_cooling` and `site_services`, have a genuine duty of
  0.00000 PJ/yr (the reference `activity_process_energy_share.csv` carries no row for
  either), and they are written blank with the reason in `provenance`. This is §3.1.1's
  absence-is-not-zero trap in a table that has no `data_status` column to resolve it.
- **The duty split is the reference table's, not the worked example's.** Each example derives
  its split through its own incumbent efficiencies; the magnitudes below are the example's
  process totals, and `duty_share` from `activity_process_duty_profile.csv` does the split.
  Where the two disagree, the reference table wins, because the point of the slice is that
  the duty profile is genuinely read.

---

## `mvp-minimal`

| | |
|---|---|
| `carb3_activity` | `Food Processing Centre` |
| Cut from | **Written fresh.** No worked example |
| Processes | One: `boiler_steam_hot_water` |
| Duties | Two: `heat_60_100` grade 2 (LTH, 0.046180 PJ/yr) and `heat_100_150` grade 3 (STM, 0.053820 PJ/yr) |
| Incumbents | One: `boiler_lt_gas`, commissioned 2009, `capacity_share` 1.000000 |
| Base-year energy | `natural_gas` 0.113636 PJ/yr; four explicit `not_consumed` zeros |

**What it exists to exercise.** The case whose optimum is computable by hand. One incumbent,
one fuel, one process, and the note 21 §4.2 contest — a new `heat_pump_lt_air` against the
avoidable cost of the incumbent gas boiler — on the grade-2 duty. `boiler_lt_gas` has
`grade_out` 3, so under C10 (the heat grade cascade), enforced here by eligibility, it
covers both duties and the premise needs no second incumbent.

**The duty clears `min_duty`.** `unit_eligibility.csv` puts `heat_pump_lt_air` at `min_duty`
0.01 PJ/yr on `boiler_steam_hot_water`. The grade-2 duty is **0.046180 PJ/yr**, 4.6× the
floor, so the demonstration unit is not screened out.

**Which figures are synthetic.** All of them. `known_activity` is 0.100000 PJ/yr, chosen round
so the reference split 0.46180 / 0.53820 lands exactly and the gas figure is
0.100000 × 1.13636 = 0.113636 PJ/yr on the nose. Location, floorspace and construction year
are plausible filler; the construction year 2009 matches the single cohort so the premise has
no vintage ambiguity. `boiler_lt_gas` has `lifetime` 25, so the incumbent dies in **2034**,
inside the horizon.

**What it does not exercise.** No `max_share`, no `earliest_year`, no mass denominator, no
process CO₂, no co-firing, no second cohort.

---

## `mvp-dairy`

| | |
|---|---|
| `carb3_activity` | `Food Processing Centre` |
| Cut from | [Food and drink worked example](../../../docs/specs/2026-08-28-carb3-site-energy-system-worked-example-food-drink.md), premise `P-004417` |
| Processes | Six: the activity's whole default set |
| Duties | Thirteen rows across seven carriers: `heat_lt60` grade 1 (SPC 0.018480, DRY 0.020711), `heat_60_100` grade 2 (LTH 0.060763, DRY 0.016668), `heat_100_150` grade 3 (STM 0.070816, DRY 0.020836), `heat_150_400` grade 4 (DRY 0.020836), `cooling_0_15` grade 2 (REF 0.064598 and 0.000934), `motive_power` (MOT 0.048566 over three processes), `electric_service` (OTH 0.013054). The dryer is four band segments (note 20 item 71) and `site_services` four duties (note 20 items 72 and 73) |
| Incumbents | Ten rows over six processes: `chp_gas_turbine` + `boiler_lt_gas`, `dryer_direct_gas`, `chiller_electric` ×2, `motor_elec` ×3, `boiler_spc_gas`, `generic_process_elec` |
| Base-year energy | `natural_gas` 0.300000, `electricity` 0.060000 PJ/yr; three explicit `not_consumed` zeros |

**What it exists to exercise.** The low- and mid-grade heat route with a genuine heat-pump
option, and the `max_share` 0.00 prohibition. `unit_eligibility.csv` carries exactly one
`max_share` 0.00 row — `boiler_lt_coal` at `Food Processing Centre` on
`boiler_steam_hot_water` — and this premise runs that process, so the prohibition is actually
tested rather than merely present. `heat_pump_lt_air` contends on the boiler house's grade-2
duty, 0.060763 PJ/yr, clearing its 0.01 floor, and on the grade-1 space heating, 0.018480
PJ/yr, beside the grade-1 `heat_pump_spc_air`.

**Which figures are taken from the worked example.** The premise record (§1.1), both
connections (§1.4), the base-year energy rows (§1.2), the six processes and their
`valid_from_year` values (§1.5), and the `boiler_steam_hot_water` and `direct_heating` units
and cohorts (§1.6). Every `known_activity` is the example's §3.2 duty figure for that process,
except `site_services`: 0.033661 PJ/yr is set so the reference SPC share 0.549 reproduces the
example's 0.018480 SPC duty exactly.

**Which figures are synthetic.** The incumbents for the four processes the example leaves
unnamed — `refrigeration`, `machinery_motors`, `compressed_air` and `site_services` — which
are the `activity_default_unit` choices for each, with no substitution (below). Their
cohort years are a 2016 drives refit, chosen so `motor_elec` (`lifetime` 20) is alive at the
2021 start year. `chiller_electric` has `lifetime` 10 and is commissioned 2016, so it dies in
**2026** and must be replaced inside the horizon.

**No substitution any more.** Until 2026-10-02 `heat_pump_lt_air` stood in for the
`activity_default_unit` SPC unit, `boiler_spc_gas`, which then had `grade_out` 1 and could not
serve a grade-2 SPC duty (see [Findings](#findings-for-the-reference-data)). The five
fuel-fired `SPC` boilers have been at `grade_out` 2 since 2026-09-25 (finding 1), and the duty
itself is grade 1 since note 20 item 73, so the default is the incumbent again, commissioned
2011 with the process. It burns gas, as the worked example's `site_services` does (§3.2,
0.021000 PJ/yr gas). Restoring it raised the `mvp-dairy` objective from £143.77m to
£144.39m: the heat pump had been free base-year capacity, and the model now builds a
`heat_pump_spc_air` in 2025 to replace the boiler's gas.

**What it does not exercise.** No mass denominator, no process CO₂, no `earliest_year` gate
that can fire (`boiler_lt_hydrogen` at 2035 and `chp_hydrogen_ccgt` at 2035 are both dropped
by the price leg first), no closed validity interval.

---

## `mvp-cement`

| | |
|---|---|
| `carb3_activity` | `Cement Works` |
| Cut from | [Cement worked example](../../../docs/specs/2026-08-28-carb3-site-energy-system-worked-example-cement.md), premise `P-000123` |
| Processes | Eight valid at the base year, plus one closed interval |
| Duties | The `cement` mass duty 1.130000 Mt/yr from `premise_throughput` (§3.1.2), and `motive_power` 0.168000 PJ/yr over four processes. Neither `kiln_pyroprocessing` nor `cement_grinding` carries a duty from the profile: both make a `product`, so their profile rows classify their energy need rather than stating a demand (§3.9) |
| Incumbents | Nine rows over eight processes: `kiln_dry_coal` + `kiln_dry_gas`, `grinder_mixer_elec`, `motor_elec` ×6 |
| Base-year energy | `coal` 3.407053, `natural_gas` 0.502947, `electricity` 0.420005 PJ/yr; three explicit `not_consumed` zeros |

**What it exists to exercise.** The high-grade kiln, delivered fuels, and process CO₂ through
`co2_process`. `kiln_dry_coal` and `kiln_dry_gas` each emit 0.525 Mt `co2_process` per Mt
clinker, so at 0.850000 Mt clinker the premise vents **446.25 kt/yr** of process CO₂ — a
carrier with `may_dispose` TRUE and `carbon_charge` `charged`, which is what puts the disposal
term $d_{c,t}$ and the carbon objective on the critical path. `coal` arrives by road and
carries no `premise_connection` row, which is the delivered-fuel case §3.1.3 describes;
`natural_gas` and `electricity` are networked and carry one each. `ccs_amine` survives the
admission screen and carries `earliest_year` 2035 and `min_duty` 0.25 on
`kiln_pyroprocessing`, so the capture-train gate is live and testable against a 0.95 Mt/yr
process. **It is genuinely testable from 2026-09-20 and was not before**: `ccs_amine`
serves no duty, so it sat in no $U_q$, the duty-keyed `earliest_year` never reached it, and
its `co2_captured` output had no sink at all. A `C-03` connection on `co2_captured` and the
restored export variable give it one; C9 (infrastructure availability) then opens `humber`
at 2030 and the 2035 eligibility gate binds first. The train is buildable and, on the
reference data as it stands, still not built — see
[note 20](../../../docs/notes/20_reference_data_open_questions.md) items 56 and 57.

**Which figures are taken from the worked example.** The premise record (§1.1), both
throughput rows (§1.3), both connections (§1.4), the nine `premise_process_detail` rows
including the closed 1957–2003 wet-line interval (§1.5), the kiln's 0.95 Mt/yr permit capacity
(§1.5), the four `motive_power` duty figures (§3.2), and the 2004 kiln commissioning year
(§1.6).

**Which figures are synthetic.** The kiln is **two units, not three**: `kiln_dry_wdf` is
dropped because `waste_derived_fuel` carries no `import_price` in any period, so the example's
fuel split 0.530303 / 0.391414 / 0.078283 renormalises over the survivors to
**0.871369 / 0.128631**. The three fuel quantities follow from that split through the kilns'
own 4.6 PJ/Mt coefficient rather than from the example's meter, which is why `coal` is
3.407053 rather than 2.10000 and `waste_derived_fuel` is an explicit zero. The electricity
figure is built the same way — kiln aux 0.092403 + grinder 0.159601 + motive 0.168000 =
**0.420005 PJ/yr** — and reproduces the example's metered 0.42000 to five decimal places,
which is the check that the reconstruction is right. `C-02`'s `import_capacity` is raised from
12 MW to 20 MW because gas now carries part of the dropped WDF kiln's share. The incumbents
and cohort years for the seven processes the example leaves unnamed are the
`activity_default_unit` choices at a 2016 drives refit.

**The closed interval has no child rows.** The example's §1.5.1 hangs `kiln_wet_ICMCLK` off
the 1957–2003 interval, and **that `unit_id` does not exist in `unit.csv`**. The interval is
kept, because it is what exercises §3.10's validity machinery and V26 (validity intervals
are disjoint and only base-year rows are read), but it names no unit —
which under §3.10's precedence rule means the plant is unknown, and is correct for a line
scrapped two decades before the base year.

**Feasibility is tight and deliberate.** The kiln's 0.95 Mt/yr at `availability_factor` 0.913
is 0.86735 Mt/yr of clinker against a requirement of 0.850000 — 2% of headroom. The grinder
draws 1.130000 × 0.752212 = 0.850000 Mt of clinker exactly, so the `clinker` node closes by
construction.

**What it does not exercise.** No gradeable heat duty at all — the works' only gradeable
carrier, `heat_lt60`, appears solely as the kilns' reject — so C10's cascade is invisible
here, which is the structural point the specification's §13 makes about cement.

---

## Verification

```
python3 carb3/data/premises/verify_premise_keys.py      # from the repo root
```

Stdlib only, because `pandas` is not installed in this repo. It checks, and currently passes:

- every `carb3_activity` resolves against `activity_process_register.csv`;
- every `process_id` resolves on the pair `(carb3_activity, process_id)`;
- every `unit_id` resolves against `unit.csv` **and** is eligible for its
  `(unit_id, carb3_activity, process_id)` triple in `unit_eligibility.csv`, or reaches it
  through one of the 142 activity-level rows with a blank `process_id`;
- every `carrier_id` resolves against `carrier.csv`, and every `premise_throughput` carrier
  has `denominator_kind = mass`;
- every `connection_id` resolves against `premise_connection.csv`;
- every `cluster_id` resolves against `infrastructure_scenario.csv`, and a premise
  without one is warned about, because C9 then permits it no CO₂ export at all;
- the §3.10 rules: validity intervals disjoint, at least one row valid at the base year,
  `valid_from_year ≤ data_year`, `known_capacity > 0` and `known_activity > 0` where present, and `known_activity ≤ known_capacity` where both are;
- the §3.10.2 rules: `(window, cohort_id)` unique, a unit repeated in one window only with
  different `commissioned_year` values, `capacity_share` all-or-none and summing to 1 within
  1e-6 per window (V33, plant is named one unit at a time), each row's parent triple present,
  `commissioned_year ≤ data_year`, and no `commissioned_year` after a closed parent window's
  `valid_to_year` (`vintage_after_interval`, part of V26, validity intervals are disjoint);
- **the note 21 §3.2 admission screen, applied to every incumbent these premises name** — no
  named unit has a blank cost field, a missing coefficient set, a declared fuel with no
  `fuel_input` row, or a consumed carrier that is not priced in all seven periods;
- **every process valid at the base year names at least one unit.** C1 (duty satisfaction)
  is an equality and C5 (no building in the start year) forbids it, so a duty with no
  incumbent is infeasible at 2021. This is the check that decided the incumbent rows for
  the eleven processes the worked examples leave unnamed.

### Incumbents too small for the start year

`verify_premise_keys.py` checks that every process valid at the base year names at least one
unit. It does **not** check that the named units are big enough. That is checked at run time,
by `sets.diagnose_start_year_shortfall`, before any LP is built: in the first period C5 (no
building in the start year) allows no new plant, so the units here must meet every duty on
their own. A premise that fails it is reported `NOT SOLVED` with the duties that are short and
by how much; [the package README](../../README.md#two-checks-before-the-solve) has the
detail and a worked failure.

The usual cause is a `capacity_share` that does not match the duties each unit can serve.
Shares always add up to the process's whole incumbent capacity, so the total is never short; what
goes wrong is giving a unit less than the duty **only it** can serve. `mvp-dairy`'s
`site_services` shows it: its heat pump must carry the whole space-heating duty (54.9% of the
process) because a motor cannot make heat, so its share must be at least 0.549.

## Findings for the reference data

Recorded, not fixed. Nothing under `docs/notes/data/` was changed.

1. **Every `SPC` duty in the reference data is unservable by every `SPC` unit.** All 48 `SPC`
   rows in `activity_process_duty_profile.csv`, across the 41 activities that have one, sit on
   `heat_60_100` at `grade_rank` 2. Every `SPC`-family unit in `unit.csv` —
   `boiler_spc_coal`, `boiler_spc_gas`, `boiler_spc_biomass`, `boiler_spc_hydrogen`,
   `boiler_spc_lpg`, `heat_pump_spc_air`, `resistance_heater_spc`, `heat_exchanger_spc_steam`
   — has `grade_out` 1 and produces `heat_lt60`. Under C10 (the grade cascade) no
   `SPC` unit can serve an `SPC` duty. `activity_default_unit.csv` compounds it by naming
   `boiler_spc_gas` as the default `SPC` unit for `Food Processing Centre`. Either the duty
   belongs at grade 1 or the units belong at grade 2; one of the two is wrong everywhere. **Resolved 2026-09-25 on the unit side** (note 22 Task 10, note 20
   item 24): the five fuel-fired `SPC` boilers deliver an 82/71 °C LPHW circuit
   (`CIBSEJ_RETURN`), so they produce `heat_60_100` at `grade_out` 2. `heat_pump_spc_air`,
   `resistance_heater_spc` and `heat_exchanger_spc_steam` stay at 1: nothing sourced puts
   them above 60 °C.
2. **`kiln_wet_ICMCLK` does not exist.** The cement worked example §1.5.1 names it as a
   `premise_process_unit.unit_id`; `unit.csv` has no such row.
3. **`fuel_oil` is not a `carrier_id`.** Both worked examples use it in their §1.2
   `premise_energy` tables. `carrier.csv` has `light_fuel_oil` and `heavy_fuel_oil`.
4. **Lifetimes disagree between the worked examples and `unit.csv`.** The food and drink
   example's §1.6 end-of-life table gives `boiler_lt_gas` 20 years and `dryer_direct_gas` 20;
   `unit.csv` gives both 25. These tables follow `unit.csv`.
5. **`known_activity` cannot express a known zero** (§3.10), where §3.1.1 solved the same
   absence-versus-zero problem with `data_status = not_consumed`.
6. **A minimal A2 that reads `activity_process_duty_profile.csv` without applying §3.9's D16
   suppression will get `mvp-cement` wrong in two ways at once.** *(Closed 2026-09-20: A2
   now reads `premise_throughput` for product duties and suppresses the profile row of any
   process whose units make a `product`. Kept here because the diagnosis is what the fix
   was built from.)* It will manufacture a
   `heat_gt1000` grade-6 duty at `kiln_pyroprocessing` that no unit can serve — `kiln_dry_coal`
   and `kiln_dry_gas` have a blank `grade_out`, and the only HTH unit, `furnace_ht_elec`, is
   `grade_out` 5 — and it will read `cement_grinding`'s duty as `motive_power` in PJ/yr rather
   than as the `cement` mass in Mt/yr, missing the one duty that drives the whole premise. The
   kiln's duty row is an activity-level classification; `clinker` is `may_export` FALSE, so
   under D16 the premise-level row does not exist and C8 (carrier balance) pins the kiln through the
   `clinker` balance instead.
