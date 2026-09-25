# Duty families and processes — the plan to fill the gaps

*Written 2026-09-24. A plan, not the work: nothing in `docs/notes/data/` changes here.
Answers the data side of [note 20](20_reference_data_open_questions.md) items 60 and 61, whose
specification side landed the same day in the live
[implementation spec](../specs/2026-08-28-carb3-site-energy-system-implementation.md).*

## In plain terms

The specification now says three things the reference data does not yet do:

1. **Cooling comes in three temperatures** — below 0 °C, 0–15 °C and above 15 °C — and a
   colder supply can serve a warmer need, never the reverse. The data still has one
   ungraded `cooling` carrier, 17 cooling duties with no temperature, and two chillers that
   differ only by refrigerant.
2. **A duty is always a service, never a fuel.** Eleven `OTH` duty rows sit on
   `electricity`, which the new check V34 (duties are services at a grade) will reject.
3. **`PHEAT` is a heat family and `EN` is not a duty family at all.** `PHEAT`'s 14 rows are
   already graded correctly; two of them have no unit that can reach their temperature.
   `EN` has no duty rows, and the validator still lists it as a duty family.

The audit below also found that **89 of the 427 duty rows have no eligible unit able to
serve them**, most of them for reasons note 20 already records. This plan fixes the
cooling, `OTH`, `PHEAT` and `EN` gaps, adds the validator checks that would have caught
them, and routes the other coverage gaps to the note 20 items that own them.

**Status 2026-09-25:** Tasks 1, 2 and 7 are done (§8) and Task 8 is done as labels; the
cooling carriers are in `carrier.csv`, and the unservable count is re-measured at 89 with a
cause and owner per row.

**Ten tasks in six lanes.** The first one — teaching the validator that ranks are unique
per grade family — has to land before any cooling carrier is added, or `make data-check`
goes red on the first row. The new service carrier for non-motive electric end uses
(lighting, instruments, welding, fab tools), `electric_service`, was accepted on 2026-09-24
and is applied; three `OTH` rows remain for Task 5.

---

## 1. What was measured

A stdlib Python audit over `activity_process_duty_profile.csv`,
`activity_process_register.csv`, `carrier.csv`, `unit.csv`, `unit_input_output.csv`,
`unit_eligibility.csv` and `activity_default_unit.csv`, run 2026-09-24 on the head of
`docs/duty-family-carrier-gaps`. "Serves" below means: the unit is admitted by
`unit_eligibility` for the duty's `(carb3_activity, process_id)` or by an activity-level row
with a blank `process_id`, **and** its `primary_output` row in `unit_input_output.csv` is the
duty's carrier — for a graded duty, a carrier of the same grade family at a `grade_out` that
reaches the duty's rank. A unit with no coefficients serves nothing.

| Table | Rows | What matters here |
|---|---|---|
| `activity_process_duty_profile.csv` | 427 | 9 families in use: `MOT` 243, `SPC` 48, `HTH` 27, `LTH` 24, `STM` 22, `REF` 17, `DRY` 17, `OTH` 15, `PHEAT` 14. No `EN`, `NEUOTH` or `HRS` row |
| `activity_process_register.csv` | 376 | Every register key has at least one duty row |
| `carrier.csv` | 44 | 6 gradeable carriers, all heat; `cooling` is one ungraded `intermediate` row |
| `unit.csv` | 137 | 52 units have a `grade_out`, none above 5; 41 cannot be fully costed (note 20 item 49) |
| `unit_input_output.csv` | 446 | Two rows produce `cooling`, one per chiller |
| `unit_eligibility.csv` | 2612 | 30 rows admit the two chillers, over 15 `(activity, process)` pairs |
| `activity_default_unit.csv` | 456 | 15 rows name `chiller_electric` as the default |

| Check | Result |
|---|---|
| `duty_share` sums per `(carb3_activity, process_set_id, process_id)`, ±0.015 | **0 violations** over 376 keys |
| Register processes with no duty row | **0** |
| Duty rows on a gradeable carrier with a blank `grade_rank` | **0** |
| Duty rows carrying a `grade_rank` that disagrees with the carrier's | **0** |
| Duty rows on a `primary` carrier | **11**, all `OTH` on `electricity` |
| Duty rows with no unit able to serve them | **89** — `MOT` 37, `HTH` 21, `SPC` 19, `OTH` 6, `REF` 2, `PHEAT` 2, `LTH` 1, `STM` 1 |
| Heat duty rows at rank 6 (`heat_gt1000`) | 18, and no unit in the library has `grade_out` 6 |
| Units with a gradeable primary output and a blank `grade_out` | 1, `solar_thermal_flat` |
| Units whose `grade_out` differs from their primary output's rank | 3, `hp_thermal_store_2h`, `_4h`, `_8h` (3 against 2) |
| Multi-duty process keys | 51, carrying 80 of the 151 `fallback` rows |

**The 22 back-derived rows are not recounted here.** Note 20 item 1 (and 1a for the
corrected counts) holds them: the `duty_share` values lane `duty_b` computed by renormalising
a process's own vector shares, which §3.3 now forbids. Two rows this plan touches may be
among them and must be checked against that list, not re-derived: `Large industrial
(> 20,000 m2) NEC / other_process` (`OTH` 0.36 on electricity, `LTH` 0.64) and
`Oil refinery, gas processing etc / alkylation` (`REF` 0.03, whose provenance says the split
was "computed from published vector weights").

---

## 2. The eleven `OTH` rows on `electricity`

§3.4 now says an `OTH` row on a fuel is invalid, and V34 (duties are services at a grade)
rejects it. Each needs a service. **Seven are not motive power**, so two routes are
proposed and one needs a decision.

| # | Activity / process | Equipment the register names | Proposed service | Evidence needed |
|---|---|---|---|---|
| 1 | Laboratory / `lab_equipment` | ULT freezers, incubators, autoclaves, instruments, IT | `electric_service` | SLAB2011 Table 7 split of instruments vs ULT freezers; the freezers are `cooling_lt0` if the source separates them |
| 2 | Laboratory / `lighting` | lab and circulation lighting | `electric_service` | none beyond the existing row |
| 3 | Large industrial NEC / `other_process` (0.36) | site-specific plant | `electric_service` | MECS 2022 Table 5.2 definition of "other process use"; check against note 20 item 1a first |
| 4 | Mill / `other_process` | screening, packing lines | **`motive_power`** | CTV059 already cites motors and compressed air |
| 5 | Mineral Production - Gas / `power_generation` | gas turbines, gas engines | **no duty** — delete the row | note 20 item 37: a generator is a unit, and the process presents no duty |
| 6 | Motor Vehicle Works / `welding` | spot-welding robots, weld guns | `electric_service` | LBNL50939 Table 2; resistance welding is electric heat with no fuel alternative |
| 7 | Newspaper print works / `prepress_platemaking` | CTP platesetters, plate processors | `electric_service` | none beyond the existing row |
| 8 | Shipbuilding / `welding_fabrication` | arc welding sets, panel lines | `electric_service` | EPA_SHIP chapter |
| 9 | Wafer Fabrication / `process_tools` | lithography, etch, CVD, implant, CMP | `electric_service` | HUCHUAH2003 |
| 10 | Works / `other_process` | test rigs, fume extraction | **`motive_power`** | MECS 2022 Table 5.2; fume extraction is fan load |
| 11 | Workshop / `other_process` | test rigs, battery charging | `electric_service` | MECS 2022 Table 5.2; battery charging is not shaft work |

**Why not `motive_power` for all eleven.** It is the cheapest fix and it is wrong for seven
rows: a motor-efficiency unit would be offered to lithography scanners and lighting, and
the motive duty would be overstated by exactly the error §3.3 warns about for oxy-fuel and
plasma cutting. **Why not leave them on `electricity`.** C8 (carrier balance) goes circular
at the `electricity` node, which is the reason §3.4's rule exists.

**Decided 2026-09-24: a new service carrier, `electric_service`**: `intermediate`,
internal, not gradeable. It adds one row to §3.4's table and one carrier row, and it is where
lighting and ICT efficiency options can later attach. **The producer is the existing
`generic_process_elec`, not a new `electric_end_use` unit** as first proposed: it is already
the incumbent in `activity_default_unit.csv` for these processes and already eligible for
all but one, and COMIT gives it a sourced coefficient — 1.0101 PJ of electricity per PJ of
service (`IFDOTHELC01` and eight other sector copies; `INFOTHELC01` is 1.1765). Giving it
that coefficient pair also takes it off the uncostable list. **Applied 2026-09-24:** the
seven rows marked `electric_service` above and Chemical Works `electrochemical_processes`
are on the new carrier; `generic_process_elec` gained its two `unit_input_output` rows and
an eligibility row at Wafer Fabrication `process_tools`; the default unit at Wafer
Fabrication `process_tools` (was `motor_elec`) and at Large industrial NEC `other_process`
(was `generic_process_gas`) is now `generic_process_elec`. Rows 4, 5 and 10 are not yet
done.

**The four `OTH` rows on `motive_power` get the same scrutiny.** Aircraft works, Factory and
Industrial NEC `other_process` are plausibly shaft work. Chemical Works
`electrochemical_processes` (chlor-alkali cells, electrolysers) is not: electrolysis is
`electric_service` under the recommendation.

**No `OTH` row is served by an `OTH` unit today.** The seven `generic_process_*` units that
`unit_eligibility` offers for `OTH` carry no `unit_input_output` rows at all. Six of the
fifteen rows — the four on `motive_power` and the two Laboratory rows — have no serving unit
of any kind. The other nine look served only because a generator admitted at the activity
(a CHP, PV) produces `electricity`: that is the circular node §3.4 forbids, not coverage.

---

## 3. The seventeen `REF` rows and their bands

The rule is §3.4's: **a cooling duty takes the band of the coldest temperature it needs.**
Four rows go to `cooling_lt0`, thirteen to `cooling_0_15`, none to `cooling_gt15` under that
rule — though one (the distillery) should be split so its cooling-tower share can land there.

| # | Activity / process | Equipment | Proposed band | Evidence needed | Source in hand? |
|---|---|---|---|---|---|
| 1 | Abattoir / `refrigeration_chilling` | ammonia plant, blast chillers, cold stores | `cooling_lt0` | freezer-store temperature; share of chill (0–4 °C) vs freeze (−18 °C and below) if a split is wanted | BREF_SLAUGHTER, for the share only |
| 2 | Aircraft works / `process_cooling` | chillers, environmental test chambers | `cooling_0_15` | chilled-water supply temperature; whether test chambers dominate | **no** |
| 3 | Artificial Fibre Works / `spinning_hvac` | air washers, AHUs, chillers | `cooling_0_15` | quench-air and chilled-water temperature | POLBREF2007, document level only |
| 4 | Brewery / `refrigeration` | glycol chillers, ammonia plant, FV jackets | `cooling_lt0` | glycol supply temperature (typically −4 to −6 °C) | BA_ENERGY, document level only |
| 5 | Chemical Works / `refrigeration` | ammonia/HFC sets, chilled water plant | `cooling_lt0` | whether sub-zero sets or chilled water dominate; low confidence either way | **no** |
| 6 | Creamery / `refrigeration` | ammonia/glycol chillers, cold stores | `cooling_0_15` | ice-water and cold-store temperatures (dairy stores are chill, not freeze) | LBNL_DAIRY |
| 7 | Distillery / `cooling_systems` | condenser pumps, cooling towers, yeast refrigerators | `cooling_0_15` now; **split** recommended | a share between condenser cooling (`cooling_gt15`) and yeast chilling (`cooling_0_15`) — an uncoupled split under §3.2 | BALMENACH_CS, document level only |
| 8 | Factory / `process_cooling` | chillers, refrigerated dryers | `cooling_0_15` | none beyond MECS | MECS2022_T52 |
| 9 | Food Processing Centre / `refrigeration` | ammonia plant, chill/freezer stores | **`cooling_0_15`** — decided 2026-09-25 | none further: the food-and-drink worked example now states chilled water with no freezer store, and this row cites it | the worked example, **done** (§6) |
| 10 | Industrial NEC / `process_cooling` | chillers | `cooling_0_15` | none beyond MECS | MECS2022_T52 |
| 11 | Large industrial NEC / `process_cooling` | chillers | `cooling_0_15` | none beyond MECS | MECS2022_T52 |
| 12 | Maltings - Non Trad / `refrigeration_attemperation` | chillers for steep/germination air | `cooling_0_15` | germination air temperature (about 14–16 °C, which needs chilled coils) | **no** — the row already says so |
| 13 | Mill / `process_cooling` | chillers | `cooling_0_15` | a source that is about cooling: the cited CTV059 is about motors and compressed air | **no** |
| 14 | Oil refinery / `alkylation` (0.03) | refrigeration compressors | `cooling_0_15` | reactor temperature (sulphuric-acid alkylation runs about 5–10 °C); check the 0.03 against note 20 item 1 first | oil_roadmap_2015, for the share only |
| 15 | Wafer Fabrication / `chilled_water_plant` | centrifugal chillers, cooling towers, PCW | `cooling_0_15` | chilled-water supply temperature; SST2004 gives cleanroom conditions, not the plant's | partial |
| 16 | Works / `process_cooling` | quench systems, chillers | `cooling_0_15` | whether quench water (cooling-tower band) or chillers dominate | **no** |
| 17 | Workshop / `process_cooling` | coolant chillers, refrigerated dryers | `cooling_0_15` | none beyond MECS | MECS2022_T52 |

**No row's current source names a temperature**, and five (2, 5, 12, 13, 16) have no source
that bears on the band at all. The evidence rule in Task 3 says what they get meanwhile.

**Two `REF` rows have no unit at all today.** `Artificial Fibre Works / spinning_hvac` is
offered space-heating boilers, heat pumps and a motor, but no chiller; `Oil refinery /
alkylation` is offered only `refinery_process_heat_gas`. Both are eligibility gaps, fixed in
Task 4.

**`heat_pump_lt_reject` is eligible at 16 of the 17 `REF` processes and draws `heat_lt60`
that nothing there produces.** It is meant to recover a chiller's condenser heat, but neither
chiller carries a `reject` row, so the draw has no source. Task 4 adds the reject rows.

---

## 4. Cooling carriers and units

**Carriers.** `carrier.csv` gains `grade_family` (heat on the six heat rows, cooling on the
new three) and three rows — `cooling_lt0` (rank 1, `<0C`), `cooling_0_15` (rank 2, `0-15C`),
`cooling_gt15` (rank 3, `>15C`) — each `intermediate`, `may_dispose` true, `may_import` and
`may_export` false. The ungraded `cooling` row is retired once nothing references it: two
`unit_input_output` rows, 17 duty rows, and the worked examples of §6.

**Units per band.** D13 (one primary carrier per unit) is about fuel, not refrigerant, so a
refrigerant variant stays a separate unit only where its costs differ.

| Band | Units needed | Coefficient per unit of cooling | Today |
|---|---|---|---|
| `cooling_lt0` | electric vapour-compression refrigeration at a sub-zero evaporator (ammonia or HFO) | electricity about −0.5 to −0.7 (COP about 1.5–2), `reject` to `heat_lt60` about +1.5 to +1.7 | **none** |
| `cooling_0_15` | electric chiller (existing `chiller_electric`, COP 3, air-cooled); absorption chiller on `heat_100_150` or `heat_60_100` (COP about 0.7) — the unit that turns CHP or kiln reject heat into cooling | electric: −0.20 to −0.33; absorption: heat −1.4, `reject` about +2.4 | `chiller_electric` only |
| `cooling_gt15` | cooling tower (`draws_ambient` true); dry cooler | electricity about −0.01 to −0.05 per unit of heat rejected | **none** |

The ranges are orders of magnitude to size the work, **not values to enter**: every
coefficient needs a source under D6 (tiered cost provenance). `grade_out` on a cooling unit is
its coldest band (§3.5): 1, 2 and 3 respectively.

**The `chiller_electric_hfo` anomaly.** It is COMIT's `ICHREFEHFO01`, "advanced
refrigeration with HFO refrigerant", and its coefficient is electricity −1.11111 per unit of
cooling: a COP of 0.9 for the unit labelled advanced, against `chiller_electric`'s 3.0. The
3.0 came from the food-and-drink worked example; the HFO row came from COMIT verbatim. The
likeliest reading is that COMIT's refrigeration coefficients are not COPs at all but final
energy per unit of COMIT's energy-service commodity, in which case `ICHREFEHFC01` — the
standard unit `chiller_electric` collapsed from — carries a comparable figure and the two
rows are on different conventions. **Evidence rule:** read `ICHREFEHFC01`'s coefficient from
the workbook's `technology_input_output` sheet before changing anything. If it is near 1.1
too, rebase the HFO unit on the same published COP as `chiller_electric` with a small
refrigerant penalty or none; if it is near 0.33, the HFO row is a genuine error to report
upstream.

---

## 5. `PHEAT`, `EN` and the coverage gaps in other families

**`PHEAT`.** All 14 rows are graded — 8 at rank 4, 4 at rank 5, 2 at rank 3 — and all 14
agree with their carrier's rank. **Two have no unit that can reach them**: `Oil refinery /
fcc` and `Oil refinery / hydrogen_production`, both rank 5, where the only eligible heat
source is `refinery_process_heat_gas` at `grade_out` 4. `furnace_ht_hydrogen` (rank 5)
serves the refinery's `catalytic_reforming` and `other_units` but is not admitted at these
two. **Four more rest on a single unit** — `furnace_ht_elec` alone at Artificial Fibre
Works `drawing_texturing`, Asphalt Plant `bitumen_storage_heating` and Chemical Works
`reaction_heating`, `furnace_ht_hydrogen` alone at refinery `catalytic_reforming` and
`other_units` — and the refinery rows' hydrogen units burn a carrier with no import price
(note 20 item 48), so they are servable on paper only.

**`EN`.** No duty row carries it. Ten units do — `electrolyser_alkaline`, `_pem`, `_soec`,
`smr_gas_ccs`, `atr_gas_ccs`, `gasifier_biomass_ccs`, `gasifier_coal_ccs` and the three
`electrolyser_battery_*` hybrids — reached through 14 eligibility rows and one
`activity_default_unit` row; every one produces `hydrogen`. That is legitimate: §3.4 now
says `EN` keys units and presents no duty. **What is wrong** is that
`validate_carb3_data.py` (line 444) and `data/build/check_units.py` (line 56) hold one
`DUTY_FAMILIES` set for both the duty profile and `unit.duty_family`, so the validator
cannot reject an `EN` duty row without also rejecting the ten units. Task 1 splits the set.

**The other coverage gaps are already owned, and this plan does not duplicate them.**

| Gap | Rows | Owner |
|---|---|---|
| `SPC` duties at rank 2, `boiler_spc_*` and the other `SPC` units at `grade_out` 1 | 19 unservable | note 20 item 24 |
| `HTH` at rank 6 with no unit reaching rank 6 | all 18 rank-6 rows, plus 3 at rank 5 — the 21 unservable `HTH` | note 20 item 27 (the band boundary) and the chemistry-node units, whose primary output is a product, not heat |
| Refinery `utilities_steam` at rank 4, CHPs at 3 | 1 `STM` | note 20 item 25 |
| Mobile plant, haulage, drilling and loading — diesel vehicles with no unit | 20 of the 37 unservable `MOT` | note 20 item 30 |
| `MOT` at processes where `motor_elec` is not admitted (it is admitted for 206 of the 243 `MOT` rows) | the other 17 | Task 7 below reports them; the fix is per process |
| `solar_thermal_flat` with a gradeable output and no `grade_out`; `hp_thermal_store_*` `grade_out` 3 against a rank-2 output | 4 units | Task 6 |

---

## 6. Worked examples and code that quote `cooling`

**Done 2026-09-25, as labels only.** Alexandre put the food-and-drink example's refrigeration
in `cooling_0_15` (chilled water, no freezer store), so the chiller keeps its COP of 3.00 and
no figure moved. The example, the cement example's prose and note 19 now name the graded
carrier, C10 (the grade cascade) by its new name, and five gradeable carriers where they said
four. The table below is kept as the record of what was touched. Changing the carrier id is a
label change; choosing a band for a freezer store is not, because it questions the COP the
example computes from. **Originally none of these was edited in this plan's first pass.** Each is listed so that Task 8 can apply them in one sweep, by one
agent owning each file, as CLAUDE.md requires for anything that feeds derived figures.

| File | Lines | What quotes `cooling` or `REF` | Numeric cascade? |
|---|---|---|---|
| `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-food-drink.md` | 305 | carrier table row `cooling`, not gradeable | no |
| same | 359–362 | prose: `REF` resolves to `cooling` | no |
| same | 384 | `chiller_electric`, `grade_out` — | no |
| same | 451 | `chiller_electric` `cooling` +1.00000 | no |
| same | 525 | default-unit row `refrigeration` → `chiller_electric` | no |
| same | 640, 646 | duty row `REF` · `cooling` · no grade; 0.064598 PJ = 0.021533 × COP 3.00 | **yes, if the band is `cooling_lt0`** — a sub-zero COP moves the electricity, the C8 row at line 1148, and note 19 |
| same | 1148 | C8 balance row for `cooling` | follows 640 |
| same | 1810 | closed point 5 names `cooling` | no |
| `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-cement.md` | 355–357, 1734 | prose: `REF` maps to `cooling` | no |
| `docs/notes/19_worked_example_data_flow.md` | 244, 279, 286 | carrier node list; chiller at COP 3.00; the `REF` duty | follows the food-and-drink example |
| `carb3/src/carb3/sets.py` | 97–104 | `eligible_units` docstring: admits a unit "whose `grade_out` is at or above the duty's `grade_rank`" | no numbers; the rule is heat-only and must read $\hat g$ (§5.1) once cooling carriers exist |

The `carb3` package's sources and tests mention `cooling` nowhere else, so the running slice
is untouched until the data changes.

---

## 7. Validator additions to `make data-check`

CLAUDE.md's rule for blocking against advisory stands: **a check that would turn many rows
red today is advisory until the data work lands, then it becomes blocking**; a check that
is green today is blocking from the start.

| Check | Red today | Blocking or advisory | Becomes blocking after |
|---|---|---|---|
| `grade_rank` unique **within `grade_family`**, replacing the global uniqueness in `check_carrier` (line 540) | 0 | blocking | now — and it must land first, or three cooling carriers at ranks 1–3 collide with `heat_lt60`, `heat_60_100` and `heat_100_150` |
| Every gradeable carrier has a `grade_family`; no ungradeable one does | 6 (the column is absent) | blocking | Task 2, in the same commit as the column |
| No duty-profile row on a `primary` or `emission` carrier — V34 (a) | 11 | advisory | Task 5 |
| Every `REF` row on a cooling band with its rank — V34 (c) | 17 | advisory | Task 3 |
| Duty families split from unit families; no duty row on `EN`, `NEUOTH` or `HRS` — V34 (c) | 0 | blocking | now |
| A unit's `grade_out` is a rank of its primary output's family; required where that output is gradeable | 1 (`solar_thermal_flat`) | advisory | Task 6 |
| Every duty has at least one eligible unit whose primary output serves it at its rank, per C10 (the grade cascade) | 89 | **advisory, permanently for now** | not scheduled — it depends on note 20 items 24, 25, 27 and 30 |
| A unit eligible at a process draws an intermediate carrier nothing eligible there produces (`heat_pump_lt_reject` at `REF` processes) | 16 pairs | advisory | Task 4 |

The last two are counts, not failures, and belong in `make data-report` beside the
admission screen's cost-completeness count.

**All eight landed on 2026-09-25 (Tasks 1, 2 and 7), in the modes the table gives.** Red
today, as measured then: 0, 0, **3**, 17, 0, 1, 89 and **11** — the third fell from 11 when
`electric_service` took eight rows, and the last is 11 `REF` processes of 119 unsourced draws
across the library (Task 1's status says why it is not 16). The draw check matches the carrier
exactly rather than through C8's heat cascade: a boiler cascading into `heat_lt60` would feed
`heat_pump_lt_reject` in LP terms, but that is not the condenser heat the unit exists to lift.

---

## 8. Tasks

Six lanes: **validator** (`validate_carb3_data.py` and `check_units.py`), **carriers**
(`carrier.csv`), **duties** (`activity_process_duty_profile.csv`, the register),
**units** (`unit.csv`, `unit_input_output.csv`, `unit_eligibility.csv`,
`activity_default_unit.csv`), **examples** (the two worked examples, note 19), and
**carb3** (the package).

```
  Task 1 validator ──▶ Task 2 carriers ──┬──▶ Task 3 REF bands ──┐
                                         └──▶ Task 4 cooling units┴──▶ Task 8 examples
  Task 5 OTH rows (electric_service done; three rows left)
  Task 6 grade_out repairs      (independent)
  Task 7 coverage report        (after Task 1)
  Task 9 carb3 direction        (after Task 2)
  Tasks 1, 2, 7 ──▶ Task 10 consolidated units-and-duties pass (absorbs 3–6's row fixes)
```

### Task 1 — Split the family sets and make ranks unique per grade family

- **Status:** **done 2026-09-25.** `DUTY_FAMILIES` holds §3.3's eleven and `UNIT_FAMILIES`
  adds `EN`, in `validate_carb3_data.py` and `check_units.py`. `check_carrier` keys uniqueness
  on `(grade_family, grade_rank)` and checks `grade_family` presence (V34 (duties are services
  at a grade) leg (d)). New blocking check: V34 (c), no `EN`, `NEUOTH` or `HRS` duty row, green.
  New advisory checks, measured: V34 (a) **3** rows on a primary carrier (§1 said 11, before
  `electric_service`); V34 (c) **17** `REF` rows off a cooling band; `grade_out` **1** blank
  (`solar_thermal_flat`) and 3 disagreeing with their output; the unsourced-draw check **119**
  (unit, activity, process) draws with no exact producer, 71 with none even through C8's heat
  cascade, `heat_pump_lt_reject` at **11** `REF` processes rather than 16 — at the other five
  `solar_thermal_flat` or the `SPC` units make `heat_lt60`. The 89 is Task 7's.
- **Lane:** validator.
- **Goal:** the validator accepts cooling bands and rejects an `EN`, `NEUOTH` or `HRS` duty row.
- **Inputs:** `validate_carb3_data.py` lines 444–458 and 522–556; `check_units.py` line 56.
- **Change:** one `DUTY_FAMILIES` set of the eleven duty families and a separate
  `UNIT_FAMILIES` set that adds `EN`; `check_carrier` keys rank uniqueness on
  `(grade_family, grade_rank)`, reading a missing `grade_family` as heat until Task 2 adds the
  column; the advisory checks of §7 that are green or counted today.
- **Evidence rule:** none — a mechanical change against §3.3 and §3.4.
- **Verification:** `make data-check` green; `make data-report` prints the new advisory
  counts at 11, 17, 1, 89 and 16 as measured in §1.
- **Depends on:** nothing.

### Task 2 — Add the cooling carriers and `grade_family`

- **Status:** **done 2026-09-25.** `carrier.csv` has `grade_family` after `is_gradeable`
  (heat on six rows, cooling on three, blank on the rest) and rows `cooling_lt0`,
  `cooling_0_15`, `cooling_gt15` at ranks 1–3, provenance citing §3.4; 48 carriers. The
  ungraded `cooling` row stays, its provenance saying it retires after Tasks 3 and 4. The
  `grade_family` check is blocking and passes; `carb3`'s carrier schema and the validator's
  column list carry the column; `README_spec_tables.md` covers both band sets. `make check`
  green, 180 `carb3` tests.
- **Lane:** carriers.
- **Goal:** `carrier.csv` carries the three cooling bands of §3.4.
- **Inputs:** §3.4's band table; `README_spec_tables.md` "The heat-grade band set".
- **Change:** the `grade_family` column (heat on six rows, cooling on three); rows
  `cooling_lt0`, `cooling_0_15`, `cooling_gt15`; the README section renamed to cover both
  families. The ungraded `cooling` row stays until Tasks 3 and 4 have moved every reference.
- **Evidence rule:** the bands are the specification's; provenance cites §3.4.
- **Verification:** the `grade_family` check turns blocking and passes; `make data-check`
  green; the `carb3` tests pass, since `carrier.csv` is one of its inputs.
- **Depends on:** Task 1.

### Task 3 — Band the seventeen `REF` rows

- **Status:** open. The three bands exist in `carrier.csv` since Task 2; all 17 rows are
  still on `cooling`, which `make data-report`'s V34 (c) advisory counts.
- **Lane:** duties.
- **Goal:** every `REF` row sits on a cooling band with its rank.
- **Inputs:** §3 of this note; the sources named there; note 20 item 1 for the alkylation
  row's share.
- **Change:** `carrier_id` and `grade_rank` on the 17 rows, provenance citing the
  temperature source; the distillery split into two processes if a share is found.
- **Evidence rule:** a band needs a source naming the coolant, store or process temperature
  for that activity. Where none exists, the row takes the band its equipment list implies,
  `evidence_tier` `fallback` and `confidence` low, and the provenance says which equipment
  decided it. A split needs a source for its share; without one, no split.
- **Verification:** the `REF` check of §7 turns blocking and passes; `duty_share` sums still
  hold on all 376 keys.
- **Depends on:** Task 2.

### Task 4 — Cooling units, coefficients and eligibility

- **Status:** open. Measured 2026-09-25: `heat_pump_lt_reject` lacks a `heat_lt60` source at
  11 `REF` processes, and 2 `REF` rows are unservable.
- **Lane:** units.
- **Goal:** each cooling band has at least one costed unit, and every `REF` duty has one
  that reaches it.
- **Inputs:** §4 of this note; the COMIT workbook's `technology_input_output` sheet for
  `ICHREFEHFC01` and `ICHREFEHFO01`.
- **Change:** `grade_out` on both chillers (2 for `chiller_electric`); a sub-zero refrigeration
  unit, an absorption chiller, a cooling tower and a dry cooler, each with costs and
  coefficients; `reject` rows to `heat_lt60` on every chiller; the HFO coefficient resolved;
  eligibility rows for `spinning_hvac` and `alkylation`; `activity_default_unit` rows per band;
  the two chillers' `cooling` rows moved to their band.
- **Evidence rule:** D6 (tiered cost provenance) — COMIT reuse, then BREF or a published COP,
  then proxy, and a proxy says so. No coefficient is entered from §4's ranges.
- **Verification:** the reject-draw advisory falls from 16 to 0; the unservable count for
  `REF` falls from 2 to 0; `make data-report` shows no new uncostable unit.
- **Depends on:** Task 2; the eligibility part on Task 3.

### Task 5 — Resolve the eleven `OTH` rows on `electricity`

- **Status:** partly done 2026-09-24 (`electric_service`, §2). Three rows remain — the 3 that
  V34 (a) counts, and 3 of the 6 unservable `OTH` rows.
- **Lane:** duties, with a specification edit to §3.4 if the decision is yes.
- **Goal:** no duty row sits on a fuel.
- **Inputs:** §2 of this note; note 20 items 8, 37 and 1a.
- **Change:** `electric_service` was accepted and its part is **done** (§2): the §3.4 row, the
  carrier, `generic_process_elec` as its producer, and seven rows plus Chemical Works
  `electrochemical_processes` moved. **Still to do:** rows 4 and 10 to `motive_power`; row 5
  deleted, with the generator admitted as a unit at that activity.
- **Evidence rule:** a row moves to `motive_power` only where its source names motors, fans,
  pumps or compressed air.
- **Verification:** V34 (a) turns blocking and passes; the `OTH` unservable count falls to 0
  once `motor_elec` and `generic_process_elec` are admitted where their rows now point.
- **Depends on:** nothing now; the `electric_service` decision was taken on 2026-09-24.

### Task 6 — Repair the four inconsistent `grade_out` values

- **Status:** open. The `grade_out` advisory counts 1 blank and 3 disagreeing, as §1 did.
- **Lane:** units.
- **Goal:** every unit with a gradeable output has a `grade_out` in that output's family that
  its coefficients support.
- **Inputs:** `unit.csv` rows for `solar_thermal_flat` and `hp_thermal_store_2h`, `_4h`, `_8h`.
- **Change:** a `grade_out` for `solar_thermal_flat` (flat-plate collectors deliver band 1 or
  2); for the three heat-pump stores, either `grade_out` 2 or a primary output at rank 3.
- **Evidence rule:** the collector's or heat pump's rated supply temperature, cited.
- **Verification:** the `grade_out` check of §7 turns blocking and passes.
- **Depends on:** nothing.

### Task 7 — Report the unservable duties by cause

- **Status:** **done 2026-09-25.** `make data-report` carries the advisory "duty coverage"
  check, one line per unservable row with its cause and owner; `make data-worklist` (or
  `validate_carb3_data.py --unservable-csv PATH`) writes the same list to
  `docs/notes/data/build/unservable_duties.csv` for Task 10. A fifth cause joined the four:
  `duty_on_fuel`, a row on a primary carrier, which no unit can serve without making C8
  (carrier balance) circular. Re-measured on today's data: **89 of 427**, the same total and
  per-family split as §1, but the `OTH` six are different rows (see below).

  | Family | Rows | Cause | Owner |
  |---|---:|---|---|
  | `MOT` | 37 | 34 no unit of the family admitted, 3 no unit at all | note 20 item 30 (20 mobile-plant rows); Task 10, `motor_elec` not admitted (17) |
  | `HTH` | 21 | 11 grade ceiling, 10 no unit of the family admitted | note 20 item 27 |
  | `SPC` | 19 | 19 grade ceiling | note 20 item 24 |
  | `OTH` | 6 | 3 duty on a fuel, 3 unit without coefficients | Task 5 (note 20 items 8 and 37); Task 10 (note 20 item 49) |
  | `PHEAT` | 2 | 2 grade ceiling | §5, Task 10 |
  | `REF` | 2 | 2 no unit of the family admitted | Task 4 |
  | `LTH` | 1 | 1 no unit of the family admitted | Task 10 |
  | `STM` | 1 | 1 grade ceiling | note 20 item 25 |
  | **All** | **89** | 47 no unit of the family, 33 grade ceiling, 3 duty on a fuel, 3 without coefficients, 3 no unit | |

  **`electric_service` made its rows servable.** All nine `OTH` rows on it are served by
  `generic_process_elec`, including the two Laboratory rows §1 counted. The six `OTH` rows
  left are the three still on `electricity` (Task 5) and the three on `motive_power` —
  Aircraft works, Factory and Industrial NEC `other_process` — where only the coefficient-less
  `generic_process_*` units are admitted and `motor_elec` is not.
- **Lane:** validator.
- **Goal:** the 89 unservable rows are a standing, attributed count rather than a surprise
  at solve time.
- **Inputs:** §5 of this note's gap table.
- **Change:** the advisory coverage check prints each unservable row with its cause —
  grade ceiling, no unit of the family admitted, unit without coefficients, or no unit at
  all — and the note 20 item that owns it.
- **Evidence rule:** none — a report.
- **Verification:** the per-family counts match §1 on today's data, and each later task's
  count falls as stated.
- **Depends on:** Task 1.

### Task 8 — Bring the worked examples and note 19 into step

**Done 2026-09-25, labels only** (§6): the band chosen was `cooling_0_15`, so the COP branch
below never applied. What remains is Task 3 putting the reference-data row for Food
Processing Centre `refrigeration` on the same band, so that the row and the example it cites
agree again.

- **Status:** **done 2026-09-25, labels only** (above); the data row waits on Task 3.
- **Lane:** examples — one agent per file, as CLAUDE.md requires.
- **Goal:** no document quotes the ungraded `cooling` carrier.
- **Inputs:** §6 of this note; Task 3's band for Food Processing Centre; Task 4's COP for it.
- **Change:** the label rows of §6; then, if the band is `cooling_lt0` and the COP differs
  from 3.00, the food-and-drink example's `REF` electricity, its C8 row and note 19's figures,
  after a `grep -rn` of every value derived from 0.021533 and 0.064598.
- **Evidence rule:** the example's figures follow the reference data; nothing is rounded
  differently from the source.
- **Verification:** `grep -rn "\`cooling\`" docs/specs docs/notes` finds only the three band
  ids; the example's C8 table closes to 1e-6 as before.
- **Depends on:** Tasks 3 and 4.

### Task 9 — Read the cascade direction in `carb3`

- **Status:** open. Since Task 2, `carb3`'s carrier schema requires `grade_family`; nothing
  reads it yet.
- **Lane:** carb3.
- **Goal:** `eligible_units` admits cooling units by the cooling direction and never across
  families.
- **Inputs:** `carb3/src/carb3/sets.py` lines 94–104; §5.1's $\hat g$ and §5.5's C10 (the
  grade cascade).
- **Change:** the docstring and, when the function is written, the comparison on
  $\omega_f \cdot \text{grade\_out}$ against $\hat g$, with a family match first.
- **Evidence rule:** none — follows the specification.
- **Verification:** a unit test with a sub-zero chiller serving a chilled-water duty (admitted)
  and a cooling tower offered to a sub-zero duty (refused); `make carb3` green.
- **Depends on:** Task 2.

### Task 10 — One consolidated pass over the unit library and the duty rows

- **Status:** open, unblocked. Tasks 1, 2 and 7 are done; the work list is
  `docs/notes/data/build/unservable_duties.csv` (89 rows).
- **Lane:** units and duties together, one owner for all six files.
- **Goal:** every duty row has an eligible unit that can serve it at its grade and in its
  grade family, and every unit offered for a duty can actually be costed and run. The 89
  unservable rows of §1 fall to zero, or each survivor is a named, deliberate gap.
- **Inputs:** Task 7's per-row report, as the work list; §3 to §5 of this note; note 20 items
  24, 25, 27, 30 and 49; `activity_process_duty_profile.csv`, `unit.csv`,
  `unit_input_output.csv`, `unit_eligibility.csv`, `activity_default_unit.csv` and
  `carrier.csv`.
- **Change:** the per-row fixes of Tasks 3 to 6 and the remaining `OTH` rows, applied in one
  sweep rather than lane by lane, because each fix on one side of the join moves the other:
  a band change on a duty changes which units reach it, and a `grade_out` change on a unit
  changes which duties it serves. **Eligibility is rebuilt from the join** — family, grade
  family, `grade_out` against the duty's band in C10's direction, and a coefficient check —
  replacing today's proxy rows, which offer every unit of a family to every process of that
  family with no grade filter. Each base-year row in `activity_default_unit.csv` is checked
  to name a unit that produces its duty's carrier.
- **Evidence rule:** as for the tasks it absorbs: no new coefficient, grade or unit without a
  source; a duty that still has no unit after the pass is recorded as a gap with its cause,
  not served by a stand-in.
- **Verification:** the coverage check, run once at the end, reports zero unservable rows
  or only the named gaps; V19 (no unit eligible beyond its `grade_out`) and V34 (duties are
  services at a grade) pass; `make check` green; the counts quoted in `CLAUDE.md`'s data
  caveats and pinned in `carb3/tests/test_load.py` re-measured and updated in the same
  commit.
- **Depends on:** Tasks 1, 2 and 7.

---

## 9. What this plan does not settle

- **The heat band set and its placement rule** remain note 20 items 23 and 27. §3.4 now
  states the rule the reference build used; confirming or reversing it moves the cooling rule
  with it.
- **`electric_service`** was accepted on 2026-09-24 and is applied (§2); rows 4, 5 and 10 remain.
- **Compressed air** stays under `motive_power`, as §3.4 defers it.
- **Refrigerant emissions** — HFC leakage, which is what separates the two chillers in COMIT —
  are outside the carrier set and outside this plan.
