# Lane `default_unit` — `activity_default_unit` (T18): what plant each activity already has

Read `docs/notes/data/build/00_CONVENTIONS.md`, then spec **§3.16** in full, both worked
examples' §1.12, and the delivery document's T18 entry
(`docs/specs/2026-08-28-carb3-site-energy-system-delivery.md`, search "T18"). Inputs you
read and never edit: `docs/notes/data/activity_process_register.csv`,
`docs/notes/data/build/activity_process_duty_profile_duty_a.csv` and `…_duty_b.csv`
(the duty families per process), `docs/notes/data/unit.csv`,
`docs/notes/data/unit_eligibility.csv` (if present; else note that eligibility is pending).

Produce `docs/notes/data/activity_default_unit.csv` with the §3.16 columns:
`carb3_activity,process_set_id,process_id,duty_family,unit_id,default_share,sizing_basis,evidence_tier,provenance,confidence`

- One or more rows per `(activity, set, process, duty_family)` in the duty profile;
  `default_share` sums to 1.00 ± 0.015 per that key.
- `evidence_tier = sector_statistic` **only** for figures traceable to a published UK
  statistic: DUKES Chapter 7 (CHP capacity, output and fuel by sector), the CHPQA register,
  DESNZ ECUK end-use tables, the 2015 industrial decarbonisation roadmaps' fleet
  descriptions, UK ETS / EA permit fleet descriptions, trade-body surveys. `derived` where
  you computed the share from such a statistic plus the energy profile; `assumed` where the
  unit is the only plausible incumbent (e.g. `motor_elec` on a MOT duty) — say so.
- **The CHP question is the point of this table.** For every activity whose sector has
  material CHP in DUKES 7, state the share of the steam/LTH duty met by CHP versus boilers,
  cited, and name the CHP unit from `unit.csv`. Where DUKES gives sector totals but not a
  per-site share, derive the share from CHP heat output ÷ sector heat demand (ECUK) and cite
  both; mark `derived`.
- Fuel split of the incumbent: use `activity_process_energy_profile.csv`'s vectors for the
  process to pick the incumbent fuel unit(s) (a process with gas 1.0 has `boiler_lt_gas` at
  1.0); cite that file as provenance.
- Blank rows are not allowed here (every duty is served), so where you cannot cite, use
  `assumed` + `confidence = low` and explain in DONE — never invent a statistic.

Check script: shares sum per key; every `unit_id` resolves; every `(activity, set, process)`
resolves to the register; every `(unit_id, activity, process_id)` has an eligibility row
(report the count that do not, do not fail). `DONE_default_unit.md`, reply with its path.
