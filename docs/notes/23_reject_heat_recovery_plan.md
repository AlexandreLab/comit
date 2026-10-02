# Reject heat by source, and what it costs to recover: the plan

*Written 2026-10-02 and revised the same day after an engineering review (section 9). Answers
[note 20](20_reference_data_open_questions.md) item 74. **Phase 1 was built the same day, under
the owner's decisions of section 6; section 10 says what was built, what was left out and why,
and where it departs from the plan below.** Sections 1 to 9 are kept as the plan was written,
with corrections marked. Section 10.6 records four fixes made later the same day, after review:
the process-exhaust and gap rows moved to [DECC_SURPLUSHEAT2014]'s technical share, the coal and
oil flue rows were removed, and the eligibility build was made reproducible.*

## In plain terms

Every fuel-burning unit in the reference data gives off some waste heat that could be
recovered, carried as a `reject` row. Today all of that heat is treated the same: it lands on
one carrier, `heat_lt60`, whatever made it, and one generic heat pump is the only unit built to
use it. So the optimiser sees the warm exhaust of a powder dryer, the flue of a gas boiler and
the condenser of a chiller as equally easy to recover, at the same temperature and the same cost.

They are not. A gas boiler's flue is hot and clean, and an off-the-shelf economiser recovers it.
A spray dryer's exhaust is a huge volume of humid air carrying milk powder, and recovering it is
expensive and carries a fire risk. This plan makes the model tell them apart:

1. **Each reject row names its source type**, through a reject carrier per source class, instead
   of all landing on `heat_lt60`.
2. **Recovering each class takes its own unit**, with its own cost per PJ/yr recovered and its own
   output temperature.
3. **The recoverable fraction depends on the class**, instead of one 0.12027 for most units.
4. **A minimum size is screened before the solve**, through `unit.csv`'s existing
   `min_viable_scale`, so a recovery unit is not offered where the source is too small to be
   worth it. The problem stays a linear programme.

Heat that no recovery unit takes stays as disposal. "Non-recoverable" is therefore not a new
category: it is what the optimiser chooses not to recover, plus the losses that were never a
carrier.

The first phase covers the 31 reject rows on boilers, CHP and engines, dryers and chillers,
which are the ones food and drink sites run. The 34 rows on kilns, furnaces and other
high-temperature process plant stay as they are until a second phase.

## 1. What the model does today

Measured on `fork/main` at `0e77577`.

- **65 `reject` rows on 65 units, every one on `heat_lt60`** (`unit_input_output.csv`).
- **50 of them are 0.12027 × fuel input**, the [DECC_SURPLUSHEAT2014] recoverable fraction. The
  other 15 depart from it: 10 are capped at their unit's losses (note 20 item 70); the three
  chillers carry their **whole condenser heat** (1.3333, or 1.3876 for `chiller_electric_lt0`, per
  PJ of cooling), not a recoverable fraction; `dryer_direct_gas` carries 0.12 and `dryer_electric`
  0.0526. Losses beyond the reject row are no carrier: they leave the energy balance inside the
  unit, as §3.6 of the live spec allows.
- **0.12027 is already a recoverable fraction**, not the whole loss. Any further haircut a
  recovery unit applies (an output below 1 per unit drawn) is a second cut on top of it, and
  Task 2 must say which one carries the practical limit. *Corrected by Task 2: it is not a
  recoverable fraction. (48 - 13)/291 is the rejected non-solid heat as a share of UK industrial
  energy, and the report's recoverable shares are 11, 7 and 5 TWh/yr of those 35 (section 5,
  p.24, which the data cited as section 4.1). Note 20 item 75.*
- **`heat_pump_lt_reject` is the unit built to draw reject heat:** 0.6875 PJ of `heat_lt60` and
  0.3125 PJ of electricity per PJ of `heat_60_100` out, at a capex of 10.1966 £m per PJ/yr. It
  has 110 rows in `unit_eligibility.csv`. It also draws `heat_lt60` that is not reject heat at
  all: the output of space-heat units released to the carrier balance.
- **Reject heat cannot serve a duty on its own.** A reject row lands on C8 (the carrier
  balance); a duty is met only through C1 (duty satisfaction), by a unit dispatched to it
  (`carb3/src/carb3/build.py`, `_dispatch_pairs`). So moving a reject row to a hotter band would
  do nothing by itself: some unit has to draw it.
- **The mvp-dairy run already recovers heat.** It builds `heat_pump_lt_reject` from 2030 at
  0.037 PJ/yr of `heat_60_100`, and disposes of 0.1208 PJ of `heat_lt60` in 2021: 0.0874 from
  the chiller, 0.0123 from the CHP, 0.0117 from the boiler and 0.0095 from the dryer.

## 2. The six source classes

The 65 rows fall into six classes, counted by script against `unit_input_output.csv`. The class
decides how hard the heat is to recover: its temperature, the medium it travels in, how dirty
that medium is, and whether it runs continuously.

| Class (proposed carrier) | Rows | Units | Medium and temperature (to be sourced) | Phase |
|---|---|---|---|---|
| `reject_flue_clean` | 4 | `boiler_lt_gas`, `_hydrogen`, `_lpg`, `_biomethane` | Clean flue gas, roughly 120 to 250 °C before any economiser | 1 |
| `reject_flue_solid_liquid` | 5 | `boiler_lt_biomass`, `_coal`, `_oil`; `chp_biomass_st`, `chp_coal_st` | Flue gas with ash or sulphur, so fouling and acid dew point limit how far it can be cooled | 1 |
| `reject_engine_exhaust` | 13 | the 12 other `chp_*` units and `engine_mot_gas` | Gas turbine or engine exhaust after the CHP's own heat recovery, plus jacket water | 1 |
| `reject_dryer_exhaust` | 6 | the 6 `dryer_*` units | Humid air, roughly 60 to 95 °C, carrying product dust | 1 |
| `reject_chiller_condenser` | 3 | `chiller_electric`, `_hfo`, `_lt0` | Superheated refrigerant (desuperheat) and condenser heat at roughly 30 to 45 °C | 1 |
| `reject_process_exhaust` | 34 | kilns, furnaces, glass, steel, crackers, reformers, gasifiers, the refinery heater, reheat furnaces | Hot, often dusty process exhaust; too varied for one recovery unit | 2 |

Three members of `reject_engine_exhaust` need care in Task 2:
- `chp_thermal_store_2h`, `_4h` and `_8h` are correctly here: their bill of materials is
  `chp_gas_turbine` plus a hot-water store (`unit_bill_of_materials.csv`).
- `engine_mot_gas` is a mechanical-drive engine with no heat recovery of its own, so its whole
  exhaust, not a residue, is the source.
- `chp_hydrogen_fuelcell` rejects stack cooling water, not exhaust.

**The chiller class carries two rows per unit, not one.** A chiller's reject row is its whole
condenser heat, and `heat_lt60` is open below (`<60C`), so a unit drawing it at 1:1 could deliver
30 to 45 °C condenser water to a 55 °C space-heat duty with no lift. Only the superheat, roughly
10 to 20% of the condenser heat (to be sourced), is hot enough to use directly. Task 5 therefore
splits each chiller's reject into a desuperheat row and a condenser row, which means two carriers:
`reject_chiller_desuperheat` and `reject_chiller_condenser`. Phase 1 then moves 31 rows and adds 3.

The temperatures above are engineering judgement and are not yet data. Task 2 sources them.

## 3. How hard each class is to recover

The working ranking, easiest first. Like the temperatures, it is judgement until Task 2 sources
it, and the costs Task 3 finds will replace it.

| Rank | Class | Why | Typical recovery |
|---|---|---|---|
| 1 | `reject_flue_clean` | Hot, clean, continuous; packaged economisers are standard and often already fitted | Economiser preheating boiler feedwater; condensing economiser |
| 2 | `reject_engine_exhaust` | Hot and continuous, but the CHP already recovers most of its heat, so what is left is modest | Exhaust economiser; jacket water into a hot water loop |
| 3 | `reject_chiller_desuperheat` and `_condenser` | Large, clean and continuous; the desuperheat is warm enough to use, the rest needs a lift | Desuperheater for wash water; a heat pump on the condenser heat |
| 4 | `reject_flue_solid_liquid` | Hot, but fouling and corrosion limit the recovery and raise the cost | Economiser with soot blowing and corrosion-resistant surfaces |
| 5 | `reject_dryer_exhaust` | Large air volume, humid, low temperature, product fouling and fire risk | Air-to-air or run-around coil preheating the dryer's inlet air ([ATKINS_ATE2011]) |

## 4. The recovery units

Each phase 1 class gets at least one unit that draws its carrier as an `aux_input`, with a blank
`fuel_carrier_id`, and is dispatched to a duty like any other unit. Its capex in `unit.csv` is per
PJ/yr of primary output (§3.5), so for a heat exchanger that is the cost per PJ/yr recovered. For
a heat pump the recovered heat is the output times (1 − 1/COP), and the plan reports the cost on
both bases.

| Proposed unit | Draws | Gives | Duty family | Serves |
|---|---|---|---|---|
| `economiser_flue_clean` | `reject_flue_clean` | `heat_60_100` | LTH | LTH duties (Decision 5) |
| `economiser_flue_solid_liquid` | `reject_flue_solid_liquid` | `heat_60_100` | LTH | LTH duties (Decision 5) |
| `recovery_engine_exhaust` | `reject_engine_exhaust` | `heat_60_100` | LTH | LTH duties |
| `desuperheater_chiller` | `reject_chiller_desuperheat` | `heat_lt60` | LTH and SPC | Wash water and space heat. **Not** a dryer segment: a `DRY` duty takes `DRY` units only (§3.5, the medium rule) |
| `heat_pump_chiller_condenser` | `reject_chiller_condenser`, electricity | `heat_60_100` | LTH | LTH duties |
| `recovery_dryer_exhaust` | `reject_dryer_exhaust` | `heat_lt60` | DRY | The `heat_lt60` segment of a `DRY` duty: air-to-air preheat of the inlet air, the same medium, so it satisfies the medium rule (note 20 item 71 split the duty so this segment exists) |

**`heat_pump_lt_reject` does not disappear from food and drink sites.** It keeps drawing
`heat_lt60`, which after phase 1 carries the 34 process-exhaust rows **and** the output of any
unit releasing `heat_lt60` to the balance, including `desuperheater_chiller`. That opens a chain,
chiller → desuperheater → `heat_pump_lt_reject`, that bypasses the per-class costs. Decision 4
settles it. `dryer_heat_pump`, which recovers its own exhaust inside the unit, is unaffected.

**An economiser as a separate unit is not quite the same as a better boiler.** Its `heat_60_100`
cannot meet a steam duty (rank 3), so on a steam-only site the most common economiser, preheating
feedwater, finds no duty to serve. And an incumbent boiler's 0.88 efficiency may already include
an economiser, so a separate one could count the same saving twice. Decision 5 settles it, and
Task 2 checks what the base-year efficiencies assume.

## 5. The minimum size

The live spec keeps the problem a linear programme: a minimum plant size is a screen applied by
A2 (expanding the premise to duties and candidate units), never an on/off variable (§3.5,
"`min_duty` replaces the MILP binary").

**The threshold lives on `unit.csv`, in the existing `min_viable_scale`** ("Screening threshold,
applied in A2", §3.5). `carb3/src/carb3/load.py` already loads the column; nothing applies it
yet. Recovery units carry their minimum source size there, in PJ/yr of the reject carrier they
draw.

It does **not** go on `unit_eligibility.csv`. The family rows there are rebuilt from the join by
`build/rebuild_eligibility_join.py`, which drops every `proxy` row and writes it again with its
constraint columns blank, so a value there would be wiped on the next rebuild. That table is also
keyed by `(unit, activity, process)`, the wrong grain for a per-site test.

**What the screen does:** A2 offers a recovery unit at a premise only if the premise's
**incumbent** sources of that class, at their base-year activity, reject at least the unit's
`min_viable_scale`. The base-year activity comes from `premise_process_detail.known_activity`
and `premise_process_unit.capacity_share`.

**How it reports:** as an **eligibility refusal**, written to `eligibility_dropped`, the way a
`min_duty` refusal already is (`carb3/src/carb3/sets.py`). Not through `screen_dropped`: that is
the admission screen's output, and `test_the_screen_leaves_every_objective_where_it_was`
(`test_integration.py`) requires every unit it drops to have been held at zero anyway. A
recovery unit refused for size might have paid, so it would fail that test.

This screen ignores sources the optimiser might build later, so it can only under-offer
recovery, never over-offer it. That is the conservative direction, and it is Decision 3.

## 6. Decisions for Alexandre

*Decided 2026-10-02: 1 to 4 as recommended; 5 as a separate unit, a **condensing** economiser,
with a standard economiser taken as already inside the boilers' efficiency. Section 10 has the
detail.*

1. **Source-class carriers or grade bands.** The plan puts each class on its own carrier. The
   alternative, putting each reject row on the heat band of its temperature, is smaller, but it
   loses the source: a dryer-exhaust recovery unit could then draw chiller heat at the same band,
   and the cost per class means nothing. *Recommended: source-class carriers.*
2. **Phase 2 now or later.** The 34 process-exhaust rows are too varied for one recovery unit:
   a cement kiln's cooler air, a glass furnace's regenerator exhaust and a steam cracker's flue
   need different equipment. *Recommended: later, after phase 1 has run on all three premises.*
3. **What the minimum-size screen counts.** Incumbent sources only (conservative), or also every
   source unit eligible at the premise (generous: it may offer recovery where no source is ever
   built). *Recommended: incumbents only.*
4. **Whether `heat_pump_lt_reject` keeps its food and drink rows.** Keeping them leaves the
   chiller → desuperheater → `heat_pump_lt_reject` chain open. Removing them means remapping its
   "heat recovery heat pump" option rows at refrigeration processes to
   `heat_pump_chiller_condenser` (`build/build_eligibility.py`,
   `decarbonisation_option_unit.csv`). *Recommended: remap, so each class is reached only through
   its own unit.*
5. **Economiser as a separate unit, or a boiler variant with an economiser.** A separate unit is
   simpler and reaches every boiler; a variant at higher efficiency is closer to the plant,
   serves steam, and cannot double-count. *Recommended: decide after Task 2 has found what the
   base-year efficiencies assume.*

## 7. Tasks

Each task names its goal, the files it may change, the rule its evidence must meet, and how it is
verified. Tasks 2 and 3 are research and can run in parallel. **Task 5 is one change:** data,
code, tests and the re-run land together, because `make check` runs the `carb3` tests on
pre-push and moving the reject rows breaks tests the moment the data changes.

### Task 1: Settle the five decisions

- **Goal:** section 6 answered, and the answers recorded in note 20 item 74.
- **Files:** `docs/notes/20_reference_data_open_questions.md`.
- **Verification:** item 74 marked settled, with the date.

### Task 2: Source each class's temperature and recoverable fraction

- **Goal:** for each phase 1 class, a typical source temperature and a recoverable fraction,
  replacing 0.12027; the chiller's desuperheat share; and what the incumbent boilers' and CHPs'
  efficiencies assume about economisers (Decision 5).
- **Files:** a research table in this note's section 2, `references.csv` for every new source.
- **Evidence rule:** every figure carries a reference with page or table. Candidates:
  [DECC_SURPLUSHEAT2014], the EU BREF on energy efficiency (2009), [BREF_FDM2019], [BEIS_CHP2021],
  [ATKINS_ATE2011] (the last three are cited in `docs/notes/activities/` and not yet in
  `references.csv`). A class with no sourced fraction keeps 0.12027 and is marked as a gap.
- **Verification:** say, for each class, whether the practical limit sits in the fraction or in
  the recovery unit's coefficient, never both. Every fraction stays within the unit's losses.

### Task 3: Source the recovery units' costs and minimum sizes

- **Goal:** capex (£m per PJ/yr, 2021 prices), fixed opex, lifetime and `min_viable_scale` for
  each unit in section 4.
- **Files:** a research table in this note's section 4, `references.csv`.
- **Evidence rule:** as Task 2, with the price-base deflation stated as `unit.csv` already does.
- **Verification:** no unit left with a blank `capex`, `lifetime` or `fixed_opex`; CLAUDE.md
  records 40 uncostable units already, and this must not add to them.

### Task 4: Write the specification

- **Goal:** the live spec says what the plan does.
- **Files:** `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md`:
  - §3.4: the phase 1 reject carriers, intermediate, not gradeable, `may_dispose` true, with
    `vector` and `comit_commodity` filled as the existing non-gradeable carriers
    (`motive_power`, `electric_service`) do.
  - §3.5: `min_viable_scale` applied to recovery units, and the medium rule naming
    `recovery_dryer_exhaust` as a `DRY` unit.
  - §3.6: the reject rule names a source class instead of "a low-grade heat carrier".
  - §5.5: the C13 (a cap is not routed through a consumer) example, "a coal boiler barred from a
    process rejects `heat_lt60` that `heat_pump_lt_reject` lifts back", uses the route this plan
    removes; rewrite it on a reject class carrier. Same for V35 (d) (the reject-heat route is
    closed).
  - §5.7: the screen.
  - §10.3: a new V36 (V1 to V35 are taken).
  - The label range in §1.4, and both places CLAUDE.md quotes it (the label table and the
    "Widening … V1–V35" sentence), widened in the same commit.
- **V36:** every `reject` row lands on a reject class carrier or on `heat_lt60`; every phase 1
  class has at least one unit that draws it; a recovery unit's `grade_out` is no hotter than its
  source class allows; `min_viable_scale` on a recovery unit is in PJ/yr of the carrier it draws.
- **Verification:** `make docs-check`; the `*Section last updated*` line bumped on each section
  touched.

### Task 5: Data, code, tests and re-run, as one change

- **Goal:** the 31 phase 1 reject rows moved to their class carriers at the Task 2 fractions, the
  three chiller desuperheat rows added, the six recovery units added with their coefficients,
  costs and `min_viable_scale`; `carb3` loads the carriers and applies the screen; the three
  premises re-run.
- **Data files:** `carrier.csv`, `unit.csv`, `unit_input_output.csv`, `references.csv`;
  `unit_eligibility.csv` only through `build/rebuild_eligibility_join.py` and, under Decision 4,
  `build/build_eligibility.py` and `decarbonisation_option_unit.csv`.
- **Validator:** `docs/notes/examples/validate_carb3_data.py`: V36, and the advisory note that
  names `heat_pump_lt_reject`. `check_lineage.py`'s `NO_COMIT_ANCESTOR` if the new units have no
  COMIT ancestor.
- **Code:** `carb3/src/carb3/load.py` and `sets.py` (apply `min_viable_scale`, refuse to
  `eligibility_dropped`); the stale "59 reject rows" docstring in `build.py`.
- **Tests:** rewrite the integration tests that follow the coal boiler's reject heat at the dairy
  (`test_c13_tracks_the_banned_coal_boilers_reject_heat_at_the_dairy` and its neighbours in
  `test_integration.py`), and the "59 reject rows" text in `test_build.py`. Add a test that a
  premise below `min_viable_scale` gets no recovery unit and one above it does. **Check
  `test_the_screen_drops_nothing_at_the_cement_works` explicitly:** mvp-cement has an incumbent
  `chiller_electric`, so its reject carrier moves even though the cement works' kiln rows do not.
- **Docs:** the food and drink worked example and note 19 where they quote `heat_pump_lt_reject`
  or the dairy's reject flows; the cement worked example only if its 0.12027 quotes change (its
  kilns are phase 2, so they should not); `docs/notes/activities/food_processing_centre.md`
  section 8; `carb3/README.md`'s dairy objective. That objective, £144.1177m, already disagrees
  with note 20 item 73's £144.39m; settle which is current before overwriting either.
- **Verification:** `make check` passes. The cement objective is unchanged, or the change is
  explained. The dairy run reports which recovery units it builds, and its disposal falls by
  what they recover.

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

## 9. Engineering review, 2026-10-02

The first version of this note went out without a review. A fresh-context review against the
spec, data and code found three issues that would have broken the build or silenced the screen,
seven gaps and seven corrections. All are resolved above.

| Severity | Finding | Resolved in |
|---|---|---|
| P0 | A `min_source` column on `unit_eligibility` would be wiped by the eligibility rebuild, fail the spec-shape check and sit at the wrong grain | Section 5: `unit.csv`'s `min_viable_scale` |
| P0 | Reporting the screen through `screen_dropped` breaks the test that every admission drop was idle anyway | Section 5: an eligibility refusal |
| P0 | Data and code tasks could not land separately past the pre-push gate | Section 7: Task 5 is one change |
| P1 | A chiller's reject is its whole condenser heat, usable at 55 °C with no lift | Sections 2 and 4: a desuperheat row and a condenser row |
| P1 | The desuperheater was offered to a dryer segment, which the medium rule forbids | Section 4 |
| P1 | "Food and drink sites lose the generic route" was false, and a chain bypassed the class costs | Section 4, Decision 4 |
| P1 | §5.5's C13 example and V35 (d) use the route being removed | Task 4 |
| P1 | A separate economiser cannot serve steam and may double-count | Section 4, Decision 5, Task 2 |
| P1 | "The cement run is unchanged" ignored its incumbent chiller | Task 5 |
| P1 | Several files that quote the reject route were missing from the tasks | Task 5 |
| P2 | 15 rows depart from 0.12027 × fuel, not none | Section 1 |
| P2 | Steam-turbine CHPs on coal and biomass belonged in the solid and liquid flue class | Section 2 (recounted by script) |
| P2 | 0.12027 is already a recoverable fraction, so a second haircut must be explicit | Section 1, Task 2 |
| P2 | New carriers need `vector` and `comit_commodity`; recovery units need `aux_input` and a checked `grade_out` | Sections 4 and Task 4 |
| P2 | V36 must widen the label range in three places | Task 4 |
| P2 | `engine_mot_gas` and `chp_hydrogen_fuelcell` do not fit the exhaust description | Section 2 |
| P2 | Emissions and reporting need no change: the ledger does not allocate, and the Sankey groups by carrier kind | No change needed |

## 10. Phase 1 as built, 2026-10-02

### 10.1 The owner's decisions

1. **Source-class reject carriers**, not grade bands.
2. **Phase 2 later.** The 34 process-exhaust rows (kilns, furnaces, glass, steel, crackers,
   reformers, gasifiers, the refinery heater, reheat) stay on `heat_lt60` at 0.12027 × fuel and
   keep `heat_pump_lt_reject`.
3. **The minimum-size screen counts the premise's incumbent sources only**, at base-year
   activity.
4. **`heat_pump_lt_reject`'s refrigeration option rows are remapped to
   `heat_pump_chiller_condenser`**, so each class is reached only through its own unit. A
   refrigeration process is one whose duty profile rows at that activity are all `REF`: 16
   rows. `heat_pump_lt_reject` keeps its other 94 rows.
5. **The economiser is a separate unit, and a condensing one.** A standard feedwater economiser
   is taken as already inside the incumbent boilers' efficiency ([DOE_WHR2008] assumes 75% of
   US boiler capacity has one), so the unit is `economiser_flue_condensing` and the clean-flue
   reject row carries the condensing increment only.
6. **Units with a cost gap are left out**: no `economiser_flue_solid_liquid`, no
   `desuperheater_chiller`, no `recovery_dryer_exhaust`. Their classes still get carriers, so
   that heat is disposed of rather than reached by `heat_pump_lt_reject`.
7. **The chiller reject is not split.** With no desuperheater built, one carrier,
   `reject_chiller_condenser`, carries the whole condenser heat, as the coefficient did before.

### 10.2 The reject rows: 31 moved (28 after section 10.6)

Counted by script: 4 rows on `reject_flue_clean`, 5 on `reject_flue_solid_liquid`, 13 on
`reject_engine_exhaust`, 6 on `reject_dryer_exhaust` and 3 on `reject_chiller_condenser`; 34
stay on `heat_lt60`. Every row stays within its unit's losses (note 20 item 70), and every row
touched now cites [DECC_SURPLUSHEAT2014] section 5, p.24, where it cited section 4.1.

| Class | Fraction of fuel used | Source | Units at a gap, kept at their old coefficient |
|---|---|---|---|
| `reject_flue_clean` | 0.05, the condensing increment | [DOE_STEAM26A] "up to 10%" for the whole condensing economiser, less [BREF_ENE2009]'s 4 to 4.5 points for the feedwater step already in the efficiency; under [ACEEE_SCHIFFHAUER2009]'s 6 to 8 points | `boiler_lt_hydrogen` (0.11111): no hydrogen flue source |
| `reject_flue_solid_liquid` | 0.04 | [BREF_ENE2009] 4%; floors from [DOE_STEAM3_2012] and the BREF acid dew points | none |
| `reject_engine_exhaust` | 0.07 for the gas turbines (incl. the steelworks-gas and thermal-store CHPs); 0.30 for `engine_mot_gas` | [EPA_CHP_CT] Table 3-2; [EPA_CHP_RICE] Table 2-3 | the five combined cycles (0.37895, 0.27663) and the fuel cell (0.30069) |
| `reject_dryer_exhaust` | 0.20, capped at the losses | [ATKINS_ATE2011] | none; only `dryer_direct_gas` moves (0.12 to 0.17650), the other five stay at their cap |
| `reject_chiller_condenser` | the whole condenser heat | first-law balance | none; coefficients unchanged |

**Why the clean-flue fraction is the increment only.** [DOE_STEAM26A]'s "up to 10%" is the gain
of a feedwater and condensing economiser together. Decision 5 puts the feedwater step inside the
boiler's 0.88 already, so recoverable heat beyond it is only the latent step, released below the
water dew point (about 57 °C): 10 less 4 to 4.5 points leaves about 5.5, taken as 0.05. That is
also why the economiser delivers `heat_lt60`, not `heat_60_100` as section 4 proposed.

**A tension left standing** (*resolved in section 10.6: the coal and oil rows are removed, and
the biomass rows are kept as a marked gap*). The solid and liquid flue fraction, 0.04, is the sensible
economiser's own share, which decision 5's reading would also count as already inside those
boilers' efficiency. No unit draws that class, so it moves only the reported disposal; it is
kept because it is the sourced figure, and a later decision may set it to the increment over an
economiser instead (for acid flue gas, close to nothing).

### 10.3 The three units built

| Unit | Draws | Gives | capex £m per PJ/yr | fixed opex | life | `min_viable_scale`, PJ/yr of the class |
|---|---|---|---|---|---|---|
| `economiser_flue_condensing` | `reject_flue_clean` at 1.0 | `heat_lt60`, grade 1 | 14.4867: [DECC_SURPLUSHEAT2014_APP]'s 4.8289 for a conventional exchanger, × 3 for condensing ([DOE_WHR2008]) | 0.32193 (proxy) | 20 | 0.00169 (100 bhp boiler, [DOE_STEAM3_2012]) |
| `recovery_engine_exhaust` | `reject_engine_exhaust` at 1.0 | `heat_60_100`, grade 2 | 12.9808 ([EPA_CHP_RICE] Table 2-4, heat recovery set) | 0.86539 (proxy, 6.67% of capex) | 15 (proxy, engine plant) | 0.00194 (smallest EPA system) |
| `heat_pump_chiller_condenser` | `reject_chiller_condenser` 0.7468, electricity 0.2532 (COP 3.95) | `heat_60_100`, grade 2 | 21.3479 ([DEA_IPH_2026]) | 0.64053 (fixed plus variable O&M) | 25 | 0.01178 (DEA's 0.5 MW floor) |

Conversions are in each row's provenance in `unit.csv`. All three are fully costed, so
CLAUDE.md's count of uncostable units does not grow. The join (`rebuild_eligibility_join.py`)
offers them at 33, 67 and 65 (activity, process) pairs, and `unit_eligibility.csv` goes from 3,608 to 3,773 rows.

**The screen is in A2** (expanding the premise to duties and candidate units; `carb3/src/carb3/sets.py`, `recovery_refusals`): a recovery unit is
offered at a premise only if its incumbents reject at least its `min_viable_scale` of the class
at the base year, and a refusal is an `eligibility_dropped` row with reason
`min_viable_scale`. `mvp-minimal` refuses `heat_pump_chiller_condenser` and
`recovery_engine_exhaust` (it has neither a chiller nor a CHP); `mvp-dairy` refuses nothing, its
chillers rejecting 0.0874 PJ/yr against the heat pump's 0.01178.

**V36** (reject heat by source class) is a new blocking check in `validate_carb3_data.py`, and
the spec's §3.4, §3.5, §3.6, §5.5, §5.7 and §10 say all of the above.

### 10.4 What the three premises do now

| Premise | Objective before | After | Why |
|---|---|---|---|
| `mvp-minimal` | £39.5505m | £39.5707m | Its boiler's reject now lands on `reject_flue_clean`, and the economiser's `heat_lt60` reaches none of its grade-2 and grade-3 duties, so `heat_pump_lt_reject` has nothing to draw and `heat_pump_lt_air` takes the 2025 duty it shared |
| `mvp-dairy` | £144.3926m | £142.7571m | `heat_pump_chiller_condenser` (COP 3.95) replaces `heat_pump_lt_reject` (COP 3.2) on the boiler-house hot water from 2025 and feeds `heat_pump_ht` from 2030; fuel falls £3.28m, capex and opex rise £1.64m; carbon does not move |
| `mvp-cement` | £4,554.9330m | £4,554.9330m | Unchanged. Its kiln rows are phase 2, and its incumbent chiller, whose reject did move, sits in `site_services`, whose `known_activity` is blank, so it never runs |

**What the dairy builds.** `heat_pump_chiller_condenser` 0.05465 PJ/yr in 2025 and 0.04512 in
2030 (the 2025 tranche rebuilt in 2050); `recovery_engine_exhaust` 0.00770 and
`economiser_flue_condensing` 0.00143 in 2025, each used for that one period only, since the CHP
and the gas boiler stop at 2030. `heat_pump_lt_reject` is no longer built.

**Its disposal of reject heat**, PJ/yr:

| | 2021 | 2025 | 2030 to 2050 |
|---|---|---|---|
| Before: `heat_lt60` | 0.12083 | 0.06628 | 0.02510 |
| After: `reject_chiller_condenser` | 0.08737 | 0.04734 | 0.01429 |
| After: `reject_dryer_exhaust` | 0.01395 | 0.00735 | 0.00735 |
| After: `reject_engine_exhaust` | 0.00716 | 0 | 0 |
| After: `reject_flue_clean` | 0.00486 | 0 | 0 |
| After: total | 0.11334 | 0.05469 | 0.02164 |

The 2021 total falls because the boiler's and the CHP's rows fell to their sourced fractions
while the dryer's rose to its cap; from 2025 the recovery units take the CHP's and the boiler's
reject in full and a larger share of the condenser heat.

**`carb3/README.md` was stale before this change**: it quoted £144.1177m for the dairy (and
£42.8055m and £4,557.0832m for the other two), where the run before this change gave
£144.3926m, the figure note 20 item 73 records. It now quotes the run after.

### 10.5 Left as it was

- **The food and drink worked example keeps its dryer reject on `heat_lt60`** feeding
  `heat_pump_lt_reject` (its §1.11 and §8.4), under its own coefficient table. Rewriting it onto
  `reject_dryer_exhaust` would remove its reject-heat leg entirely, since no unit draws that class
  yet; a note in the example says where it and the reference data part. Note 19 mirrors the
  example and is unchanged.
  *Deferred to its own change (owner's decision, 2026-10-02).* Applying the data properly does
  more than drop that leg: `heat_pump_chiller_condenser` (£8.30m/PJ by the example's own
  comparison) displaces `heat_pump_lt_air` (£10.63m/PJ), so the hydrogen CHP never expands and the
  2050 electricity export, one of the exit conditions of milestone M4 (the MVP exit gate), goes.
  The same check found two defects that predate this note: the example's 2030 "nothing changes"
  is false (the air-source heat pump at £12.06m/PJ beats the standing boiler's avoidable
  £16.82m/PJ), and two fuel coefficients differ from the data (`boiler_lt_biomass` −1.28205
  against −1.1236, `dryer_direct_hydrogen` −1.17650 against −1.08696). The follow-up re-solves
  2025 to 2050 on the data, drops the export, and updates note 19 and M4's exit conditions.
- **The cement worked example** quotes 0.12027 for its kilns, which are phase 2; unchanged.
  *Superseded by section 10.6: it now quotes 0.037801.*
- **The 34 process-exhaust rows** still carry 0.12027 as if it were recoverable (note 20 item 75).
  *Superseded by section 10.6.*

### 10.6 Fixes after review, 2026-10-02

Four open issues, fixed the same day. Every count below was measured by script against the
tables after the change.

**1. The technical recoverable share replaces 0.12027 (owner's decision).** 0.12027 is
(48 - 13)/291, the heat UK industry rejects in non-solid form as a share of its energy
([DECC_SURPLUSHEAT2014] section 5, p.24), not a recoverable fraction. Decided by Alexandre: the
rows that carried it now carry the report's technical potential, "a technical potential of 11
TWh/yr ... can be technically recovered" (section 5, p.24, Figure 5), as 11/291 = 0.037801 of
fuel energy in. Technical, not economic (7 TWh/yr) or commercial (5 TWh/yr), because the LP
already prices recovery through each recovery unit's capex, so an economic screen would count
that cost twice. Each row is min(0.037801 × fuel input, the unit's losses); no row reaches its
losses, so none is capped. **41 rows changed**: the 34 process-exhaust rows on `heat_lt60`, and
7 phase 1 rows that had kept 0.12027 as a gap, namely the five combined-cycle CHPs (0.37895 to
0.11910; `chp_hydrogen_ccgt` 0.27663 to 0.08694), `chp_hydrogen_fuelcell` (0.30069 to 0.09450)
and `boiler_lt_hydrogen` (0.11111, its losses, to 0.04200). Each now cites section 5, p.24.
The cement kilns' row goes from 0.55326 to 0.17388 per Mt of clinker, and the worked example's
kiln reject from 0.470271 to 0.147798 PJ (coal 0.078378, gas 0.011570, waste fuel 0.057850).

**2. No reject row on coal or oil flue gas (owner's decision).** Decision 5 puts a standard
economiser inside the boilers' efficiency, so 0.04, [BREF_ENE2009]'s standard-economiser gain,
counted it twice. Beyond it nothing is recoverable from coal or oil flue gas, because the acid
dew point bars condensing: [DOE_STEAM3_2012] (the DOE steam tip sheet) puts the floor at 300 F
(149 °C) for coal and low-sulphur oil and 350 F (177 °C) for high-sulphur oil, and
[BREF_ENE2009] section 3.2.5 gives acid dew points of about 160 °C for heavy and 130 °C for light
fuel oil. **The reject rows of `boiler_lt_coal`, `boiler_lt_oil` and `chp_coal_st` are
removed**, with the reason in each unit's `unit.csv` provenance, as `mobile_plant_diesel` records
why it has none. `boiler_lt_biomass` and `chp_biomass_st` keep 0.04 on
`reject_flue_solid_liquid`, marked as a gap: the increment beyond a standard economiser is
unsourced, and biomass flue-gas condensation exists but no source for it was verified. The class
keeps two members, so V36 (reject heat by source class) and spec §3.4 still hold; §3.4's table
now names them. `reject` rows: 65 to 62, of which 28 on source classes (`reject_flue_solid_liquid`
5 to 2) and 34 on `heat_lt60`.

**3. `build_eligibility.py` reproduces `unit_eligibility.csv` again.** Run before this fix, it
wrote 3,350 rows, and `rebuild_eligibility_join.py` after it gave 4,329, against 3,773
committed: 603 rows added and 47 removed, all `proxy` rows of the three process-keyed service
units (`engine_mot_gas`, `mobile_plant_diesel`, `mobile_plant_battery`), and two chemistry rows
whose citations (`lime_kiln_sugar_coke`, `potline_prebake_elec`) were reset. The cause: the
rebuild reads a keyed unit's reach back from the file it rewrites, and that reach was set by
hand (note 20 items 30 and 65), while `build_eligibility.py`, unchanged in that respect since it
was written, still rewrote the whole file with its old step (c), offering every family unit at
every process of its family. The rebuild alone was idempotent, which is why nothing caught it.
`build_eligibility.py` now rewrites only the rows it owns (worked-example, options-join and
chemistry-node rows, by `provenance_ref`) and keeps every other row; its old family step is
gone. The pair now reproduces the committed file with an empty diff, on the tables before and
after fixes 1 and 2. The canonical sequence is in both scripts' docstrings and in
`data/README_spec_tables.md`.

**4. Stale counts in CLAUDE.md** were re-measured and updated.

**What the premises do.** No objective moves: `mvp-minimal` £39.5707m, `mvp-dairy` £142.7571m,
`mvp-cement` £4,554.9330m, since reject heat that nothing draws is disposed of at no cost and
none of the changed rows feeds a recovery unit that runs. `mvp-cement` disposes of 0.14780 PJ of
`heat_lt60` in 2021 and 0.12992 from 2025, where it disposed of 0.47027 and 0.41340.
`mvp-dairy`'s disposal is unchanged; its 2021 dispatch moves within a tie at the same objective
(`boiler_spc_gas` now serves 0.01848 PJ of boiler-house hot water and `chp_gas_turbine` the
same amount of space heat, with the gas boiler and the CHP trading as much steam), because the problem has 14 fewer variables and the solver lands on
another optimal vertex.
