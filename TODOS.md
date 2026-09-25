# TODOS

Open work on the CaRB3 duty families and cooling grades. The full plan is
[note 22](docs/notes/22_duty_family_gap_plan.md); the open questions are
[note 20](docs/notes/20_reference_data_open_questions.md) items 60 and 61.

## Blocking

- [x] **Bring the data checker up to the spec before any cooling carrier lands.** Done
  2026-09-25: `EN` left the duty families and stays a unit family, `grade_rank` is unique
  within its `grade_family`, and the three cooling carriers are in `carrier.csv` with
  `make data-check` green. *Note 22 Tasks 1 and 2.*

## Decisions for Alexandre

- [ ] **Which heat band does a duty go in?** §3.4 now states the rule the reference build
  used: a duty takes the band of its hottest temperature, and band edges read as the labels
  do. Note 20 item 27 had left this open. Confirm or reverse it; the cooling rule (the band of
  the coldest temperature) mirrors whichever stands.

## Data

- [ ] **The last three `OTH` rows on `electricity`.** Mill and Works `other_process` to
  `motive_power` (screening lines, fans); Mineral Production - Gas `power_generation` deleted,
  because a generator is a unit, not a demand (note 20 item 37). V34 (duties are services at
  a grade) rejects all three. *Note 22 Task 5.*
- [ ] **Two rows may carry a duty share copied from the fuel split.** Large industrial NEC
  `other_process` (0.36, now on `electric_service`) and Oil refinery `alkylation`. Check both
  against note 20 item 1a before relying on their shares; they are flagged, not recomputed.
- [ ] **Laboratory ultra-low-temperature freezers.** `lab_equipment` moved to
  `electric_service` as a whole. If SLAB2011 Table 7 separates the freezers, split them out
  as a `REF` duty in the `cooling_lt0` band.
- [ ] **Shipbuilding `steel_prep_cutting` names `generic_process_elec` as incumbent on an
  `HTH` duty** (`activity_default_unit.csv`, share 0.13636). That unit now produces
  `electric_service`, so it cannot serve a heat duty; the plasma-cutting share needs a heat
  unit. The row was already unservable before, when the unit had no coefficients.
- [x] **Band the 17 `REF` rows.** Done 2026-09-25: 3 on `cooling_lt0`, 14 on `cooling_0_15`,
  each citing a temperature source or, under the task's fallback rule, the equipment that
  decided it; both chillers on `cooling_0_15` at `grade_out` 2; the ungraded `cooling` carrier
  retired; V34 (duties are services at a grade) leg (c) blocking. *Note 22 Task 3.*
- [ ] **Per-band cooling units, and `chiller_electric_hfo`'s COP of 0.9** against
  `ICHREFEHFC01` in the workbook. The three `cooling_lt0` rows have no unit that reaches them
  until a sub-zero unit exists. *Note 22 Tasks 4 and 10.*
- [ ] **Split Distillery `cooling_systems`?** It names condenser water and cooling-tower fans
  (`cooling_gt15`) beside yeast refrigeration (`cooling_0_15`). No source gives the share, so
  under Task 3's rule the row is whole, on `cooling_0_15`. A published split would move part
  of it to `cooling_gt15`. *Note 20 item 62.*
- [ ] **One consolidated pass over the unit library and the duty rows.** Fix the 89
  unservable duties in a single sweep with one owner, rather than lane by lane, and rebuild
  `unit_eligibility.csv` from the join (family, grade family, `grade_out` in C10's direction,
  coefficients present) instead of today's no-grade-filter proxy rows. The work list is
  `docs/notes/data/build/unservable_duties.csv`, written by `make data-worklist`, one row
  per duty with its cause and owner. *Note 22 Task 10.*
- [ ] **`heat_exchanger_spc_steam` draws `heat_100_150` at 59 places where nothing eligible
  makes steam, even through C8's heat cascade.** Found 2026-09-25 by the new advisory
  "intermediate draws with no eligible producer": 119 (unit, activity, process) draws have no
  exact producer, 71 have none even through the cascade, and this unit is 59 of them. Its
  eligibility needs a steam source beside it, or the rows go. *Note 22 Task 10.*
- [ ] **`heat_pump_lt_reject` has no source at 11 `REF` processes, not 16.** Note 22 §1 counted
  16; at five of them another admitted unit makes `heat_lt60` — `solar_thermal_flat` at four,
  the `SPC` units at Artificial Fibre Works `spinning_hvac` — which is not the condenser heat
  the unit exists to lift. The fix is still the chillers' `reject` rows. *Note 22 Task 4.*

## Documents and code

- [x] **Put the Food Processing Centre `refrigeration` data row on `cooling_0_15`.** Done
  2026-09-25 with Task 3. The
  food-and-drink worked example now says chilled water at that band (decided 2026-09-25, labels
  only, no figure moved), and the row in `activity_process_duty_profile.csv` cites the example.
  It still says ungraded `cooling`; the `cooling_0_15` carrier exists since 2026-09-25, so
  only the row move is left. *Note 22 Task 3.*
- [x] **`carb3` handles grades for heat only.** Done 2026-09-25 (note 22 Task 9, landed with
  Task 3 because the banded data needed it): `_serves` matches the grade family first and reads
  the direction from it, and two tests pin a sub-zero plant serving chilled water and a
  cooling tower refused a freezer duty. Before it, `heat_pump_lt_reject` sat in the dairy's
  chilled-water U_q. C10 (the grade cascade) in the code needs the
  reversed direction for cooling once graded cooling carriers are in the data. `carb3` now
  reads `carrier.grade_family` (its schema requires the column) but nothing uses it yet.
  *Note 22 Task 9.*
- [ ] **`docs/notes/data/build/check_units.py` does not run.** It reads
  `build/carrier_products_units.csv`, which is not in the tree, and dies with
  `FileNotFoundError` before any check. Found 2026-09-25; its `EN` family set was updated
  anyway. Either restore the staging file or drop the read. `make check` does not call it.
- [ ] **The lane scripts `check_duty_a.py` and `check_duty_b.py` do not run.** Their `EN`
  family and `REF`-on-`cooling` rules were updated with Task 3 (2026-09-25), but both read lane
  staging files (`build/activity_process_duty_profile_duty_a.csv`, `_duty_b.csv`) that are not
  in the tree and die with `FileNotFoundError`. Neither is in `make check`. Restore or retire.
