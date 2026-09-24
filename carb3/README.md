# carb3

The CaRB3 site energy system, Python side — the pre-M2 demonstration slice planned in
[note 21](../docs/notes/21_mvp_slice_implementation_plan.md). A least-cost pathway over
three synthetic premises, solved as a pure LP on the real reference tables under
`docs/notes/data/`, which are **read and never written**.

## Run it

```
make carb3-run                                   # all three premises, report only
make carb3-run PREMISES=mvp-dairy                # one premise
make carb3-run OUT_DIR=outputs/carb3             # write the parquet ledger too
uv run --directory carb3 python -m carb3 --help  # the flags, including --reference-root
```

The run report prints what §5.2 and §5.3 ask for: the units the §3.2 admission screen
dropped and why, any unservable duty with its premise and period, the solver status, the
variable and constraint counts, the wall clock (the `G1` measurement), the objective
decomposition, and the disposal and dispatch tables.

```
make carb3                                       # the tests; also part of `make check`
```

## What is here

| Module | Owes |
|---|---|
| `load.py` | Reference + premise tables → typed records; the §3.2 admission screen |
| `sets.py` | Minimal A2; Q, U, U_q via the three-table join; C10 widening; unservable-duty diagnosis |
| `survival.py` | D11 survival function and the capacity behind a cohort, computed before the LP |
| `build.py` | Variables, C1–C5, C8, C10 via eligibility, the objective, the solve |
| `ledger.py` | Cost by term, carrier mix, dispatch, build, disposal → parquet |
| `__main__.py` | The entry point. Not a sixth module: no model code, only the wiring and the report |

Inputs a human edits stay **CSV**; outputs are **parquet** (§3.4).

## State of the three premises

| Premise | Outcome |
|---|---|
| `mvp-minimal` | Solves. The grade-2 heat duty switches to a heat pump at 2025, the first period C5 allows building |
| `mvp-dairy` | Solves. Both the grade-2 and the grade-4 drying duty switch at 2025 |
| `mvp-cement` | **Does not solve**, and the cause is in the reference data — see below |

`mvp-cement` is stopped before the LP is built, by §5.2's pre-solve diagnosis, with the duty
named: `cement_grinding` on `motive_power`, in all seven periods.
`activity_process_duty_profile.csv` carries **no mass carrier anywhere**, so the minimal A2
cannot derive the premise's 1.130000 Mt/yr `cement` duty; it derives a motive-power duty from
a mass figure instead, and every eligible grinder outputs `cement`. The premise's
`premise_throughput.csv` says the same figure "is the premise's mass duty under D5", so the
premise tables and A2 disagree about where a D5 mass duty comes from. It is
[note 20](../docs/notes/20_reference_data_open_questions.md) item 51, and closing it is a
decision about A2 rather than a fix.

Three further findings from the build are items 52–54 of the same note: on-site generation is
live through the 23 `coproduct` rows although note 21 says three times that it is not; every
capture train is unbuildable while export is out, so `earliest_year` is untested at the
cement works; and a D16-suppressed process's producers need the activity variable note 21
§2.2 removed.
