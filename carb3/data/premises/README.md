# Synthetic premise tables (plan §3.4)

Four CSV tables per premise — `premise_record`, `premise_process_detail`,
`premise_process_unit`, `premise_process_vintage` — for `mvp-minimal`, `mvp-dairy` and
`mvp-cement`. CSV so every file a human edits stays diffable; outputs and M2 fixtures are
parquet. `process_duty` is **not** here: it is derived by the minimal A2 (`sets.py`).

Empty at the scaffolding stage — the rows are written alongside T2.
