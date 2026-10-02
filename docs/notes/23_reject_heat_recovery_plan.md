# Reject heat by source, and what it costs to recover: the plan

*Written 2026-10-02. A plan, not the work: nothing in `docs/notes/data/`, `docs/specs/` or
`carb3/` changes here. Answers [note 20](20_reference_data_open_questions.md) item 74.*

## In plain terms

Every fuel-burning unit in the reference data gives off some waste heat that could be
recovered, carried as a `reject` row. Today all of that heat is treated the same: it lands on
one carrier, `heat_lt60`, whatever made it, and one generic heat pump is the only way to use it.
So the optimiser sees the warm exhaust of a powder dryer, the flue of a gas boiler and the
condenser of a chiller as equally easy to recover, at the same temperature and the same cost.

They are not. A gas boiler's flue is hot and clean, and an off-the-shelf economiser recovers it.
A spray dryer's exhaust is a huge volume of humid air carrying milk powder, and recovering it is
expensive and carries a fire risk. This plan makes the model tell them apart:

1. **Each reject row names its source type**, through a reject carrier per source class, instead
   of all landing on `heat_lt60`.
2. **Recovering each class takes its own unit**, with its own cost per PJ/yr recovered and its own
   output temperature.
3. **The recoverable fraction depends on the class**, instead of one 0.12027 for every unit.
4. **A minimum size is screened before the solve**, so a recovery unit is not offered where the
   source is too small to be worth it. The problem stays a linear programme.

Heat that no recovery unit takes stays as disposal. "Non-recoverable" is therefore not a new
category: it is what the optimiser chooses not to recover, plus the losses that were never a
carrier.

The first phase covers the 31 reject rows on boilers, CHP and engines, dryers and chillers,
which are the ones food and drink sites run. The 34 rows on kilns, furnaces and other
high-temperature process plant stay as they are until a second phase.

## 1. What the model does today

Measured on `fork/main` at `0e77577`.

- **65 `reject` rows on 65 units, every one on `heat_lt60`** (`unit_input_output.csv`).
- **Each is sized at 0.12027 × fuel input**, the [DECC_SURPLUSHEAT2014] recoverable fraction,
  capped at the unit's own losses since 2026-10-02 (note 20 item 70). Losses beyond the reject
  row are no carrier: they leave the energy balance inside the unit, as §3.6 of the live spec
  allows.
- **One unit consumes reject heat**: `heat_pump_lt_reject`, which draws 0.6875 PJ of `heat_lt60`
  and 0.3125 PJ of electricity per PJ of `heat_60_100` out, at a capex of 10.1966 £m per PJ/yr.
  It has 110 rows in `unit_eligibility.csv`.
- **Reject heat cannot serve a duty on its own.** A reject row lands on C8 (the carrier
  balance); a duty is met only through C1 (duty satisfaction), by a unit dispatched to it
  (`carb3/src/carb3/build.py`, `_dispatch_pairs`). So moving a reject row to a hotter band would
  do nothing by itself: some unit has to draw it.
- **The mvp-dairy run already recovers heat.** It builds `heat_pump_lt_reject` from 2030 at
  0.037 PJ/yr of `heat_60_100`, and disposes of 0.1208 PJ of `heat_lt60` in 2021: 0.0874 from
  the chiller, 0.0123 from the CHP, 0.0117 from the boiler and 0.0095 from the dryer.

## 2. The six source classes

The 65 rows fall into six classes. The class is what decides how hard the heat is to recover:
its temperature, the medium it travels in, how dirty that medium is, and whether it runs
continuously.

| Class (proposed carrier) | Rows | Units | Medium and temperature (to be sourced) | Phase |
|---|---|---|---|---|
| `reject_flue_clean` | 4 | `boiler_lt_gas`, `_hydrogen`, `_lpg`, `_biomethane` | Clean flue gas, roughly 120 to 250 °C before any economiser | 1 |
| `reject_flue_solid_liquid` | 3 | `boiler_lt_biomass`, `_coal`, `_oil` | Flue gas with ash or sulphur, so fouling and acid dew point limit how far it can be cooled | 1 |
| `reject_engine_exhaust` | 15 | the 14 `chp_*` units and `engine_mot_gas` | Exhaust after the CHP's own heat recovery, plus engine jacket water | 1 |
| `reject_dryer_exhaust` | 6 | the 6 `dryer_*` units | Humid air, roughly 60 to 95 °C, carrying product dust | 1 |
| `reject_chiller_condenser` | 3 | `chiller_electric`, `_hfo`, `_lt0` | Condenser water or refrigerant, roughly 30 to 45 °C, higher from a desuperheater | 1 |
| `reject_process_exhaust` | 34 | kilns, furnaces, glass, steel, crackers, reformers, gasifiers, the refinery heater, reheat furnaces | Hot, often dusty process exhaust; too varied for one recovery unit | 2 |

The temperatures above are engineering judgement and are not yet data. Task 2 sources them.

## 3. How hard each class is to recover

The working ranking, easiest first. Like the temperatures, it is judgement until Task 2 sources
it, and the costs Task 3 finds will replace it.

| Rank | Class | Why | Typical recovery |
|---|---|---|---|
| 1 | `reject_flue_clean` | Hot, clean, continuous; packaged economisers are standard and often already fitted | Economiser preheating boiler feedwater; condensing economiser |
| 2 | `reject_engine_exhaust` | Hot and continuous, but the CHP already recovers most of its heat, so what is left is modest | Exhaust economiser; jacket water into a hot water loop |
| 3 | `reject_chiller_condenser` | Large, clean and continuous, but low temperature | Desuperheater for wash water; a heat pump to lift the rest |
| 4 | `reject_flue_solid_liquid` | Hot, but fouling and corrosion limit the recovery and raise the cost | Economiser with soot blowing and corrosion-resistant surfaces |
| 5 | `reject_dryer_exhaust` | Large air volume, humid, low temperature, product fouling and fire risk | Air-to-air or run-around coil preheating the dryer's inlet air ([ATKINS_ATE2011]) |

## 4. The recovery units

Each phase 1 class gets at least one unit that draws its carrier and is dispatched to a duty
like any other unit. Its capex in `unit.csv` is per PJ/yr of primary output (§3.5), so for a
heat exchanger that is the cost per PJ/yr recovered. For a heat pump the recovered heat is the
output times (1 − 1/COP), and the plan reports the cost on both bases.

| Proposed unit | Draws | Gives | Serves |
|---|---|---|---|
| `economiser_flue_clean` | `reject_flue_clean` | `heat_60_100` | LTH duties, boiler feedwater |
| `economiser_flue_solid_liquid` | `reject_flue_solid_liquid` | `heat_60_100` | LTH duties |
| `recovery_engine_exhaust` | `reject_engine_exhaust` | `heat_60_100` | LTH duties |
| `desuperheater_chiller` | `reject_chiller_condenser` | `heat_lt60` | Wash water, space heat, the lowest dryer segment |
| `heat_pump_chiller_condenser` | `reject_chiller_condenser`, electricity | `heat_60_100` | LTH duties |
| `recovery_dryer_exhaust` | `reject_dryer_exhaust` | `heat_lt60` | The `heat_lt60` segment of the same `DRY` duty: preheating the inlet air (note 20 item 71 split the duty so this segment exists) |

`heat_pump_lt_reject` stays, drawing `heat_lt60`, which after phase 1 carries only the 34
`reject_process_exhaust` rows. A food and drink site therefore loses that generic route and
gains the six specific ones. `dryer_heat_pump`, which recovers its own exhaust inside the unit,
is unaffected.

## 5. The minimum size

The live spec keeps the problem a linear programme: a minimum plant size is a screen applied by
A2 (expanding the premise to duties and candidate units), never an on/off variable (§3.5,
"`min_duty` replaces the MILP binary"). Recovery follows the same pattern, but `min_duty` is the
wrong measure: what makes recovery worth it is the size of the **source**, not of the duty it
serves.

**Proposed:** a new optional `unit_eligibility` column, `min_source` (PJ/yr), on recovery units
only. A2 offers the recovery unit at a premise only if its **incumbent** sources of that class,
at their base-year activity, reject at least `min_source`. The units the screen drops are
reported through the existing `screen_dropped` output, with the reason.

This screen ignores sources the optimiser might build later, so it can only under-offer
recovery, never over-offer it. That is the conservative direction, and it is Decision 3 below.

## 6. Decisions for Alexandre

1. **Source-class carriers or grade bands.** The plan puts each class on its own carrier. The
   alternative, putting each reject row on the heat band of its temperature, is smaller, but it
   loses the source: a dryer-exhaust recovery unit could then draw chiller heat at the same band,
   and the cost per class means nothing. *Recommended: source-class carriers.*
2. **Phase 2 now or later.** The 34 process-exhaust rows are too varied for one recovery unit:
   a cement kiln's cooler air, a glass furnace's regenerator exhaust and a steam cracker's flue
   need different equipment. *Recommended: later, after phase 1 has run on all three premises.*
3. **What the minimum-size screen counts.** Incumbent sources only (conservative, as above), or
   also every source unit eligible at the premise (generous: it may offer recovery where no
   source is ever built). *Recommended: incumbents only.*

## 7. Tasks

Each task names its goal, the files it may change, the rule its evidence must meet, and how it is
verified. Tasks 2 and 3 are research and can run in parallel; the rest are in order.

### Task 1: Settle the three decisions

- **Goal:** Section 6 answered, and the answers recorded in note 20 item 74.
- **Files:** `docs/notes/20_reference_data_open_questions.md`.
- **Verification:** item 74 marked settled, with the date.

### Task 2: Source each class's temperature and recoverable fraction

- **Goal:** for each phase 1 class, a typical source temperature and a recoverable fraction of
  fuel or electricity input, replacing the flat 0.12027.
- **Files:** a research table in this note's section 2, `references.csv` for every new source.
- **Evidence rule:** every figure carries a reference with page or table. Candidates:
  [DECC_SURPLUSHEAT2014], the EU BREF on energy efficiency (2009), [BREF_FDM2019], [BEIS_CHP2021],
  [ATKINS_ATE2011]. A class with no sourced fraction keeps 0.12027 and is marked as a gap.
- **Verification:** every fraction stays within the unit's losses, so `check_energy_closure`
  still passes.

### Task 3: Source the recovery units' costs and minimum sizes

- **Goal:** capex (£m per PJ/yr, 2021 prices), fixed opex, lifetime and a credible minimum source
  size for each unit in section 4.
- **Files:** a research table in this note's section 4, `references.csv`.
- **Evidence rule:** as Task 2, with the price-base deflation stated as `unit.csv` already does.
- **Verification:** no unit left with a blank `capex`, `lifetime` or `fixed_opex`; CLAUDE.md
  records 40 uncostable units already, and this must not add to them.

### Task 4: Write the specification

- **Goal:** the live spec says what the plan does.
- **Files:** `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md`: §3.4 (the five
  phase 1 reject carriers, not gradeable, `may_dispose` true), §3.5 (`min_source` beside
  `min_duty`), §3.6 (the reject rule names a source class instead of "a low-grade heat carrier"),
  §5.7 (the screen), §10.3 (one new validation test, below), and the label ranges in §1.4 and in
  CLAUDE.md's table, widened in the same commit.
- **New validation test:** every `reject` row lands on a reject class carrier or on `heat_lt60`;
  every phase 1 class has at least one unit that draws it; a `min_source` value appears only on a
  unit that draws a reject class carrier.
- **Verification:** `make docs-check`; the `*Section last updated*` line bumped on each section
  touched.

### Task 5: Change the data

- **Goal:** the 31 phase 1 reject rows moved to their class carriers at the Task 2 fractions; the
  six recovery units added with their coefficients and eligibility; `min_source` filled.
- **Files:** `carrier.csv`, `unit.csv`, `unit_input_output.csv`, `unit_eligibility.csv` (through
  `build/rebuild_eligibility_join.py`, never by hand), `references.csv`.
- **Verification:** `make data-check` passes, including `check_energy_closure` and
  `check_emission_coefficient_basis`; `make data-report`'s uncostable count does not rise.

### Task 6: Read the new carriers and the screen in `carb3`

- **Goal:** `carb3` loads the reject class carriers, applies the `min_source` screen in A2 and
  reports what it drops.
- **Files:** `carb3/src/carb3/load.py`, `sets.py`, and the tests that quote
  `heat_pump_lt_reject` or `heat_lt60` reject flows: `test_load.py`, `test_sets.py`,
  `test_build.py`, `test_integration.py`, `test_report.py`.
- **Verification:** the full `carb3` test suite passes; a new test shows a premise below
  `min_source` gets no recovery unit and a premise above it does.

### Task 7: Re-run the three premises and update the worked examples

- **Goal:** mvp-dairy, mvp-cement and mvp-minimal re-run; the food and drink worked example and
  note 19 updated where they quote `heat_pump_lt_reject` or the dairy's reject flows.
- **Files:** `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-food-drink.md`,
  `docs/notes/19_worked_example_data_flow.md`, `docs/notes/activities/food_processing_centre.md`
  section 8.
- **Verification:** the cement run is unchanged, because its kiln rejects are phase 2. The dairy
  run reports which recovery units it builds, and its disposal falls by what they recover.

## 8. What this plan does not settle

- **Phase 2:** recovery of the 34 process-exhaust rows.
- **Compressed air.** Compressors turn most of their electricity into heat at about 70 °C, and
  packaged recovery kits are common, but no compressor unit carries a `reject` row today. Adding
  one is a separate item.
- **Timing.** The model is annual, so it cannot check that a source and its heat user run at the
  same time. A batch dryer's exhaust cannot heat a process that runs only at night. The
  activity notes in `docs/notes/activities/` record each activity's operating pattern; a
  coincidence factor per class is a possible later refinement.
- **Distance.** A source and a user at opposite ends of a large site need pipework the unit
  cost does not include.
