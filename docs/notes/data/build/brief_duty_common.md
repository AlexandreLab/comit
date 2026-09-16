# Lanes `duty_a` / `duty_b` — `activity_process_duty_profile` and the process crosswalk (T17)

Read `docs/notes/data/build/00_CONVENTIONS.md`, then spec **§3.3** (the entity you are
populating), §3.4 (carriers and the heat bands), §3.13 (not yours, but the shape classes
help), and both worked examples' §3.2 `process_duty` tables.

## What you produce

For **every** `(carb3_activity, process_set_id, process_id)` row of
`docs/notes/data/activity_process_register.csv` in your activity list (below), one or more
rows of `docs/notes/data/build/activity_process_duty_profile_<lane>.csv` with exactly
the §3.3 columns:

`carb3_activity,process_set_id,process_id,duty_family,carrier_id,grade_rank,duty_share,share_low,share_high,evidence_tier,provenance,confidence`

Rules that the validator will enforce:
- `duty_family` ∈ {DRY, EN, HRS, HTH, LTH, MOT, NEUOTH, OTH, PHEAT, REF, SPC, STM}.
- `carrier_id` is the **service** carrier, never a fuel: heat families (LTH, HTH, STM, DRY,
  SPC, PHEAT) → one of the six `heat_*` bands with `grade_rank` set (1 `<60C`, 2 `60-100C`,
  3 `100-150C`, 4 `150-400C`, 5 `400-1000C`, 6 `>1000C`); MOT → `motive_power`; REF →
  `cooling`; OTH → whichever service it really is (say which); NEUOTH → blank carrier (feedstock,
  no duty); HRS is the steel hot-rolling chemistry node only. EN (energy, generic) is a last
  resort — avoid.
- **`grade_rank` is non-nullable on any heat row.** Choose the band from the process's
  *required delivery temperature* stated by a source (BREF, roadmap, Carbon Trust sector
  guide, DESNZ electrification study, trade body). If no source gives a temperature, put the
  row at `evidence_tier = fallback`, `confidence = low`, and say in provenance what the fallback
  reasoning is — but **do not leave the band blank** and do not invent a °C figure; cite the
  analogous process you borrowed from.
- `duty_share` per `(activity, set, process)` sums to 1.00 ± 0.015. A process that is purely
  one duty has one row at 1.0. A multi-duty process (e.g. a paper machine: STM at 100-150C plus
  MOT) splits, citing the source of the split; if no split is published, use one row for the
  dominant duty at 1.0 and state so.
- `evidence_tier` ∈ {measured, engineering, published_sec, fallback}; `confidence` ∈ {high,
  medium, low}. Same reading as `activity_process_energy_profile.csv` (see its README).
- Named non-default sets (`bf_bof` at Iron and/or Steel Works, `grain_distillery` at
  Distillery) need rows only where they differ from the default (inheritance, §3.3).

Also produce `docs/notes/data/build/carb3_comit_process_crosswalk_<lane>.csv`: one row
per register process in your list, columns
`carb3_activity,process_set_id,process_id,comit_process_code,match_kind,notes` where
`comit_process_code` is one of the 94 COMIT process codes in
`docs/notes/data/comit_sector_processes.csv` (column `process_commodity`, e.g. `IFDLTH`,
`ICMCLK`) or blank, and `match_kind` ∈ {direct, analogue, none}. The 16 sector-root codes
(`ICH`, `ICM`, … `IPP`) are sector totals, not processes — never map to them. Use
`docs/notes/data/carb3_comit_crosswalk.csv` (activity level) to find the sector first.

Useful corroboration already in the repo (supply side, not a source of duty): 28 rows of
`decarbonisation_options_library.csv` column `duty` and 45 of
`process_decarbonisation_options.csv` column `notes` carry °C values.

Write a stdlib check that (a) every register row in your list has ≥1 duty row, (b) shares
sum to 1 ± 0.015, (c) heat rows have `grade_rank`, (d) all keys and `[REF_ID]`s resolve.
Run it. Then write `DONE_<lane>.md` and reply with its path.
