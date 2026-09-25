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
make carb3-run PREMISES="mvp-cement --co2-tariff 60"  # flat CO₂ tariff in £/t (note 21 §4.4)
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
| `build.py` | Variables, C1–C5, C8, C10 via eligibility, C9 for CO₂ export only, the objective, the solve |
| `ledger.py` | Cost by term, carrier mix, dispatch, build, disposal → parquet |
| `__main__.py` | The entry point. Not a sixth module: no model code, only the wiring and the report |

Inputs a human edits stay **CSV**; outputs are **parquet** (§3.4).

## State of the three premises

All three solve to optimality (checked 2026-09-25, `make carb3-run`).

| Premise | Objective | Outcome |
|---|---|---|
| `mvp-minimal` | £42.8055m | The grade-2 and grade-3 heat duties switch to heat pumps at 2025, the first period C5 (no building in the start year) allows |
| `mvp-dairy` | £144.1177m | The grade-2 and grade-4 drying duties switch at 2025; refrigeration is met by an electric chiller |
| `mvp-cement` | £4,557.0832m | The kiln moves from coal to gas and the grinder substitutes clinker at 2025; an amine capture train is built at 2035 and its CO₂ is exported |

Carbon is 77% of the cement works' objective. The works stopped being infeasible on
2026-09-20, after two fixes. The first is that A2 (premise to duties) now reads a product duty
from `premise_throughput` at the base year, as spec §3.1.2 says. The second restores export,
x_{c,t}, for carriers with `may_export`, a `premise_connection` row and a complete price
series. Without it nothing could consume `co2_captured`, so C8 (carrier balance) pinned every
capture train to zero. [Note 20](../docs/notes/20_reference_data_open_questions.md) items 51
to 53 record this. The kilns' `co2_process` coefficients were then corrected to the kt basis
(item 56), which is when capture started being built.

The capture train is small: it captures 0.023 Mt/yr against about 0.55 Mt/yr still vented.
Item 57 is the reason. `ccs_amine` draws a fixed composition, 89.88 kt of biogenic CO₂ per Mt
captured, and the works vents only about 2 kt/yr of biogenic CO₂. The scarcest stream caps
the train, and `co2_fuel_biogenic` disposal drops to nothing from 2035. Treat the capture
result as a data artefact until item 57 is closed.

## Against the live spec

The slice implements a subset of spec §5, on purpose (note 21 §2). Out of scope: h_{c→c′,t},
the cascade variable; r_{u,t}, early retirement; w_{k,t}, reinforcement; and C6, C7, C11 and
C12. **Two recent spec changes are not yet in the code.** Both are safe for now only because
the reference data has not caught up either.

- **C10 (the grade cascade) is heat-only.** `sets.py` tests `grade_out >= grade_rank` and
  treats `cooling` as ungraded. Since 2026-09-24 the spec grades cooling in three bands,
  `cooling_lt0`, `cooling_0_15` and `cooling_gt15`. It runs C10 per family, on the service
  rank ĝ = ω_f · g, with the comparison reversed for cooling and no unit serving across
  families. C8's cascade sums carry the same family filter. `carrier.csv` still has one
  ungraded `cooling` row and no `grade_family` column, so today's runs are unaffected. Once
  note 22 Tasks 1 and 2 add the cooling bands, the code must read `grade_family`, compare on
  ĝ and refuse cross-family eligibility. Without that, a grade-2 heat unit could pass the test
  for a grade-2 cooling duty.
- **V34 (duties are services at a grade) is not asserted at load.** The spec now rejects duty
  rows on a primary or emission carrier. The eight OTH rows it caught have moved to
  `electric_service`, which `generic_process_elec` produces, and the three-table join finds
  that unit with no code change. None of the three premises draws an OTH duty, so nothing here
  exercises it.

The `duty_share` handling matches §3.3. A duty's quantity is the premise's `known_capacity`
for the process times the row's `duty_share`. A gradeable carrier with no `grade_rank` stops
the run, following §3.3's rule that a heat or cooling duty must have a grade. A process whose
units make a non-exportable `product`, such as `clinker`, yields no duty (D16, an internal
product is a carrier and not a duty) and is settled by C8.

Still open from the build: note 20 item 54, the activity variable a D16-suppressed process
still needs; item 55, the CO₂ export route has no sourced price, so the £40/t tariff is
synthetic; and item 57 above.
