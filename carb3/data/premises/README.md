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
| `premise_process_unit.csv` | §3.10.2 | Which units each process runs — one row per unit, from the 2026-09-17 pass |
| `premise_process_vintage.csv` | §3.15 | Install year per cohort (D11, existing plant has an age) |
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

**Four tables were commissioned; seven are written.** `premise_connection`, `premise_energy`
and `premise_throughput` are the three §3.1 companions. §3.1 declares the first two
**required** alongside `premise_record`, and without `premise_throughput` the cement premise
has no `cement` duty at all — nothing draws clinker, the kiln never runs, and the process-CO₂
and capture-train behaviour the premise exists to exercise never happens. They are small and
they are the spec's own shape, so they are written rather than deferred.

## Where the duty magnitude lives

**`premise_process_detail.known_capacity` is the premise's annual magnitude for that
process**, in PJ/yr for an energy-denominated process and Mt/yr for a mass-denominated one
(D5, hybrid denominators). A2 splits it across the process's
`activity_process_duty_profile` rows by `duty_share`.

This is the slice's reading of §3.10, and it is stated here because the four commissioned
tables carry no other magnitude field. Each row's `provenance` names the unit it is in.

Two consequences worth knowing before reading a number:

- **`known_capacity` cannot state a known zero** — §3.10 requires `> 0 if present`. Two
  `mvp-cement` processes, `clinker_cooling` and `site_services`, have a genuine duty of
  0.00000 PJ/yr (the reference `activity_process_energy_profile.csv` carries no row for
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

**Which figures are synthetic.** All of them. `known_capacity` is 0.100000 PJ/yr, chosen round
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
| Duties | Eight rows across five carriers: `heat_60_100` grade 2 (LTH 0.060763 and SPC 0.018480), `heat_100_150` grade 3 (STM 0.070816), `heat_150_400` grade 4 (DRY 0.079050), `cooling_0_15` grade 2 (REF 0.064598), `motive_power` (MOT 0.062553 over three processes) |
| Incumbents | Eight rows over six processes: `chp_gas_turbine` + `boiler_lt_gas`, `dryer_direct_gas`, `chiller_electric`, `motor_elec` ×3, `heat_pump_lt_air` |
| Base-year energy | `natural_gas` 0.300000, `electricity` 0.060000 PJ/yr; three explicit `not_consumed` zeros |

**What it exists to exercise.** The low- and mid-grade heat route with a genuine heat-pump
option, and the `max_share` 0.00 prohibition. `unit_eligibility.csv` carries exactly one
`max_share` 0.00 row — `boiler_lt_coal` at `Food Processing Centre` on
`boiler_steam_hot_water` — and this premise runs that process, so the prohibition is actually
tested rather than merely present. `heat_pump_lt_air` contends on both grade-2 duties, at
0.060763 and 0.018480 PJ/yr, each clearing its 0.01 floor.

**Which figures are taken from the worked example.** The premise record (§1.1), both
connections (§1.4), the base-year energy rows (§1.2), the six processes and their
`valid_from_year` values (§1.5), and the `boiler_steam_hot_water` and `direct_heating` units
and cohorts (§1.6). Every `known_capacity` is the example's §3.2 duty figure for that process,
except `site_services`: 0.033661 PJ/yr is set so the reference SPC share 0.549 reproduces the
example's 0.018480 SPC duty exactly.

**Which figures are synthetic.** The incumbents for the four processes the example leaves
unnamed — `refrigeration`, `machinery_motors`, `compressed_air` and `site_services` — which
are the `activity_default_unit` choices for each, with one substitution described below. Their
cohort years are a 2016 drives refit, chosen so `motor_elec` (`lifetime` 20) is alive at the
2021 start year. `chiller_electric` has `lifetime` 10 and is commissioned 2016, so it dies in
**2026** and must be replaced inside the horizon.

**One substitution, forced by the reference data.** The `activity_default_unit` SPC unit for
this activity is `boiler_spc_gas`, which has `grade_out` 1 and therefore cannot serve the
grade-2 SPC duty the profile states. `heat_pump_lt_air` stands in as the incumbent. See
[Findings](#findings-for-the-reference-data) — this is a whole-table defect, not a quirk of
this premise. **Since 2026-09-25 the reason is gone** — the five fuel-fired
`SPC` boilers are at `grade_out` 2 (finding 1) — but the premise keeps its heat-pump
incumbent, since it is synthetic and changing it would move the solve.

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
  `valid_from_year ≤ data_year`, `known_capacity > 0` where present;
- the §3.10.2 rules: children distinct, `capacity_share` all-or-none and summing to 1 within
  1e-6 — V33 (plant is named one unit at a time) — each child's parent triple present;
- the §3.15 rules: `capacity_share` summing to 1 within 1e-6 per premise-process,
  `commissioned_year ≤ data_year`, and every cohort naming a unit the premise runs at the
  base year;
- **the note 21 §3.2 admission screen, applied to every incumbent these premises name** — no
  named unit has a blank cost field, a missing coefficient set, a declared fuel with no
  `fuel_input` row, or a consumed carrier that is not priced in all seven periods;
- **every process valid at the base year names at least one unit.** C1 (duty satisfaction)
  is an equality and C5 (no building in the start year) forbids it, so a duty with no
  incumbent is infeasible at 2021. This is the check that decided the incumbent rows for
  the eleven processes the worked examples leave unnamed.

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
5. **`known_capacity` cannot express a known zero** (§3.10), where §3.1.1 solved the same
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
