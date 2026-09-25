# TODOS

Open work on the CaRB3 duty families and cooling grades. The full plan is
[note 22](docs/notes/22_duty_family_gap_plan.md); the open questions are
[note 20](docs/notes/20_reference_data_open_questions.md) items 60 and 61.

## Blocking

- [ ] **Bring the data checker up to the spec before any cooling carrier lands.**
  `validate_carb3_data.py:444` still lists `EN` as a duty family, and it checks `grade_rank`
  uniqueness across all carriers rather than within a grade family. Adding the three cooling
  carriers first turns `make data-check` red. *Note 22 Task 1 (split the family sets, make
  ranks unique per grade family).*

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
- [ ] **Band the 17 `REF` rows, add the cooling carriers and per-band chillers**, and check
  `chiller_electric_hfo`'s COP of 0.9 against `ICHREFEHFC01` in the workbook.
  *Note 22 Tasks 2–4.*
- [ ] **One consolidated pass over the unit library and the duty rows.** Fix the 89
  unservable duties in a single sweep with one owner, rather than lane by lane, and rebuild
  `unit_eligibility.csv` from the join (family, grade family, `grade_out` in C10's direction,
  coefficients present) instead of today's no-grade-filter proxy rows. Uses Task 7's
  per-row report as the work list. *Note 22 Task 10.*

## Documents and code

- [ ] **Put the Food Processing Centre `refrigeration` data row on `cooling_0_15`.** The
  food-and-drink worked example now says chilled water at that band (decided 2026-09-25, labels
  only, no figure moved), and the row in `activity_process_duty_profile.csv` cites the example.
  It still says ungraded `cooling` because the cooling carriers are not in `carrier.csv` yet.
  *Note 22 Tasks 2 and 3.*
- [ ] **`carb3` handles grades for heat only.** C10 (the grade cascade) in the code needs the
  reversed direction for cooling once graded cooling carriers are in the data.
  *Note 22 Task 9.*
