# Lane `loadshape` — `process_load_shape` (spec §3.13)

Read `docs/notes/data/build/00_CONVENTIONS.md`, then spec **§3.13** in full (the six shape
classes and their indicative ranges), §3.12, §5.6's intent, and both worked examples' §1.10.

Produce `docs/notes/data/process_load_shape.csv` with the §3.13 columns:
`shape_id,process_id,shape_class,duty_factor,peak_to_mean,runs_when_idle,seasonality,provenance,confidence`
plus an extra `carb3_activity` column first, because `process_id` in the register is unique
only within an activity (e.g. `site_services` appears at many activities). `shape_id` =
`<activity_slug>__<process_id>`.

One row per register process (376 rows in `docs/notes/data/activity_process_register.csv`;
named non-default sets share the default's shape unless a source says otherwise).

- `shape_class` is required on every row; choose it from what the process physically does,
  and cite the source that describes the operation (BREF operating descriptions, Carbon
  Trust sector guides, DESNZ roadmaps, published sub-metering case studies, half-hourly
  demand studies of UK industrial sites, CIBSE/BSRIA load profiles).
- `duty_factor` and `peak_to_mean` are **numbers only where a source states or lets you compute
  them** (a published load profile, a sub-metering study, a published load factor). Otherwise
  leave both blank — the spec's indicative ranges are *not* a source and must not be copied
  in as values. Expect most rows blank; say so in DONE.
- `runs_when_idle`: TRUE only for `standing` class (refrigeration, compressed air baseload,
  lighting/site services, IT) per §3.13's rule; FALSE otherwise unless cited.
- `seasonality` ∈ {none, winter_weighted, summer_weighted, campaign}: `campaign` for beet
  sugar, maltings, distillery seasonal, quarry winter shutdowns etc., cited.
- `confidence` low wherever the class was inferred rather than cited.

Check: every register (activity, process) has exactly one row; enums valid; `standing` ⇒
`runs_when_idle = TRUE`; `[REF_ID]`s resolve. `DONE_loadshape.md`, reply with its path.
