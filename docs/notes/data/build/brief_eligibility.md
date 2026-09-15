# Lane `eligibility` — `unit_eligibility`, the option→unit join, and the options library alignment (T9, data-migration C1–C4, C8)

Read `docs/notes/data/build/00_CONVENTIONS.md`, then spec **§3.5.1**, §3.4, §3.6, the
data-migration document `docs/specs/2026-08-28-carb3-site-energy-system-data-migration.md`
items **C1–C4 and C8**, and `docs/notes/data/README_decarbonisation_options.md`. The unit
identity list is `docs/notes/data/unit.csv` (owned by the `units` lane; read it, never edit
it — if it lacks a unit you need, request it in your DONE file and leave the mapping row's
`unit_id` blank with a note).

## Deliverables

1. `docs/notes/data/decarbonisation_option_unit.csv` — the missing join (C2). One row per
   `(option_id, unit_id)`: columns `option_id,unit_id,relationship,notes,provenance,confidence`
   with `relationship` ∈ {is_unit (the option *is* this unit), enables (efficiency/heat
   recovery option that changes a unit's coefficient — say which), route_change (whole-route
   replacement spanning several processes), supply (PV/battery/CHP/AD/electrolyser
   supply-side), none (no unit representation possible — explain)}. Every one of the 134
   options in `decarbonisation_options_library.csv` gets ≥1 row.
2. `docs/notes/data/build/decarbonisation_options_library_aligned.csv` — the library with
   three **added** columns (all existing columns and rows unchanged, same order):
   `displaces_carrier_ids` (C1: the free-text `displaces` normalised to `;`-separated
   `carrier_id`s from `carrier.csv`; blank where `displaces` is blank), `route_change`
   (C3: TRUE/FALSE), `exclusivity_group` (C4: a short slug shared by mutually exclusive
   options, e.g. `ad_biogas_use`, `biochar_feedstock`; blank otherwise). Cite the reasoning in
   DONE. The coordinator swaps it in.
3. `docs/notes/data/unit_eligibility.csv` — spec §3.5.1 columns plus `notes` and
   `provenance_ref`. One row per `(unit_id, carb3_activity, process_id)` the unit may serve,
   derived from: the worked examples' eligibility tables (reproduce verbatim, including
   `min_duty`, `max_share`, `earliest_year` values there); the 1,109 rows of
   `process_decarbonisation_options.csv` through your join in (1); and, for the service
   units, every register process whose duty family and grade the unit can serve (you need
   the duty families: read `docs/notes/data/build/activity_process_duty_profile_duty_a.csv`
   and `…_duty_b.csv` if they exist yet; if not, derive from the register's process names
   and say so, flagging `provenance = proxy`). `min_duty` (C8, the screening threshold that
   replaces the MILP binary) and `earliest_year` only where a published source states a
   minimum viable plant size or first-availability year (DESNZ IFS reports, CCC, IEA, trade
   bodies) — otherwise blank. `max_share` only with a cited physical or regulatory basis.
   `provenance` enum ∈ {comit_reuse, bref, proxy}.

Check script: every option has a join row; every `unit_id` resolves to `unit.csv`; every
`(carb3_activity, process_id)` resolves to the register; every `carrier_id` in
`displaces_carrier_ids` resolves; every `[REF_ID]` resolves. `DONE_eligibility.md`, reply
with its path.
