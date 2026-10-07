# carb3

The CaRB3 site energy system, Python side — the pre-M2 demonstration slice planned in
[note 21](../docs/notes/21_mvp_slice_implementation_plan.md). A least-cost pathway over
three synthetic premises, solved as a pure LP on the real reference tables under
`docs/notes/data/`, which are **read and never written**.

## Run it

```
make carb3-run                                   # all three premises, report only
make carb3-run PREMISES=mvp-dairy                # one premise
make carb3-run OUT_DIR=outputs/carb3             # write the parquet ledger and a site report too
make carb3-report OUT_DIR=outputs/carb3          # rebuild the site reports from parquet, no solve
make carb3-run PREMISES="mvp-cement --co2-tariff 60"  # flat CO₂ tariff in £/t (note 21 §4.4)
uv run --directory carb3 python -m carb3 --help  # the flags, including --reference-root
```

The run report prints what §5.2 and §5.3 ask for: the units the §3.2 admission screen
dropped and why, the units dropped at each premise because an input can be neither imported
nor made there (below), any unservable duty with its premise and period, any start-year shortfall
in the incumbent plant (below), the solver status, the
variable and constraint counts, the wall clock (the `G1` measurement), the objective
decomposition, and the disposal and dispatch tables. It also lists each unit a process
refused by `min_duty`, a 0.00 `max_share` or a recovery unit's `min_viable_scale` (the unit
stays admitted, so it is not in the screen's list). With `--out-dir` that list is written as
`eligibility_dropped.parquet` (`premise_id`, `process_id`, `unit_id`, `reason`, `detail`),
beside `screen_dropped.parquet`, which holds only the per-unit admission-screen findings. After
the solve it lists each recovery unit built below its `min_viable_scale` (spec §5.7, check 5),
written as `sub_minimum_recovery.parquet`: reported, not constrained, since the problem stays a
pure LP. It then runs the capture check (spec §5.7, check 6): V37 (a capture rate is a fraction
of its hosts' streams) legs (c) to (f), read back from the output tables. A violation there is a
build defect, so it fails the run.

```
make carb3                                       # the tests; also part of `make check`
```

## Before the solve: one screen and two checks

**The per-premise screen runs first.** `build.screen_premise` drops a unit when it consumes a
carrier that can be neither imported (`carrier.may_import`) nor made by any *other* unit in
this premise's model, and repeats until nothing changes, since a dropped producer can strand
its consumers. It is per-premise because the §3.2 admission screen runs once for every
premise and cannot know which other units are present: `chp_bfg_gas_turbine` reaches the
dairy through the grade join in `unit_eligibility.csv`, burns `blast_furnace_gas`, and nothing
at a dairy makes it. Such a unit was held at zero by C8 (carrier balance) anyway, so dropping
it clears its zero rows from the ledger and leaves the optimum unchanged. **Incumbents (units
with surviving capacity) are never dropped**: the site pays their fixed opex whether they run
or not, so removing one would lower the objective by a real cost. An incumbent with an
unsourceable input stays, held at zero by C8. The drops are printed per premise and written to
`screen_dropped.parquet` under the leg `unreachable_input`. A capture train is judged by its
hosts instead: its `emission_input` rows are capture rates on its hosts' streams, not draws, so
it is dropped, under the leg `no_capture_host`, only when no host it names in
`unit_abatement_host.csv` is in the model and makes a CO₂ stream it captures. A duty unit's output counts as made where
another unit draws it, because z° (the activity a unit releases to the carrier balance rather
than dispatches to a duty) puts it in C8: `heat_pump_ht` lifts the `heat_60_100` that the
low-grade heat pumps and space-heating boilers release. A unit is never its own source. The
screen reads only the signs of C8's coefficients, so a stranded unit burning a fuel with no
emission factor is dropped rather than stopping the run; one that survives still fails loud
when the model is built.

A premise can then fail before any LP is built, and both failures are reported as
`NOT SOLVED` with the reason, never as a traceback (§5.2, infeasibility is an expected
outcome). A duty the screen empties surfaces in the first check.

| Check | Function | Fails when | What to fix |
|---|---|---|---|
| Unservable duty | `sets.diagnose_unservable_duties` | A duty has **no** eligible unit in some period | The unit library or eligibility: nothing on the site's candidate list makes that carrier at that grade |
| Start-year shortfall | `sets.diagnose_start_year_shortfall` | The incumbent plant is **too small** to meet the first period's duties | `premise_process_unit.capacity_share` against the duties each unit can serve, or `premise_process_detail.known_activity` or `known_capacity` |

**Why the start year is special.** C1 (duty satisfaction) is an equality and C5 (no building
in the start year) allows no new capacity in the first period, so the plant named in
`premise_process_unit` has to meet every duty on its own, each unit capped by C2 (activity
limited by available capacity) at its capacity × γ × α. From the second period on, a
shortfall is simply built, and costs money rather than failing.

**How it decides.** C2 is written per `unit_id`, so one unit's capacity is a pool shared by
every duty it is eligible for. Comparing each duty with its eligible units one at a time
would count that pool once per duty, so the check solves a small maximum flow instead
(incumbents supply, duties demand) and, where it falls short, reports the smallest group of
duties whose demand exceeds what the incumbents able to serve them can deliver. A
`max_share` caps its unit's contribution exactly as it caps the LP's dispatch.

```
the incumbent plant cannot meet its duties in 2021, the start year, where C5 (no building in
the start year) allows no new capacity: boiler_steam_hot_water on heat_100_150,
boiler_steam_hot_water on heat_60_100, site_services on heat_60_100 need 0.150059 together,
and the incumbents able to serve them (boiler_lt_gas, chp_gas_turbine, heat_pump_lt_air) can
deliver 0.145043, short by 0.005015. ...
```

That is `mvp-dairy` with `site_services` split 0.40 / 0.60 instead of 0.549 / 0.451: the
heat pump is 0.149 × 0.033661 PJ/yr short of the space-heating duty, the motor's spare
capacity cannot make heat, and the boilers that could are fully used by the boiler house, so
all three duties are named together.

**It is a necessary condition, not a proof.** Units making an internal product with no duty
(D16, the cement works' clinker kiln) draw on C2 through C8 (carrier balance) rather than C1,
and are not in the flow. A premise that fails the check is certainly infeasible in the start
year; one that passes can still be infeasible for another reason.

## What is here

| Module | Owes |
|---|---|
| `load.py` | Reference + premise tables → typed records; the §3.2 admission screen |
| `sets.py` | Minimal A2; Q, U, U_q via the three-table join; C10 widening; unservable-duty diagnosis; the start-year adequacy check |
| `survival.py` | D11 survival function and the capacity behind a cohort, computed before the LP |
| `build.py` | The per-premise reachability screen; variables, C1–C5, C8, C10 via eligibility, C9 for CO₂ export only, the objective, the solve |
| `ledger.py` | Cost by term, carrier mix, dispatch, build, disposal, unit flow → parquet |
| `__main__.py` | The entry point. Not a sixth module: no model code, only the wiring and the report |
| `report/` | The site report, parquet → `site_report.html`. Not model code: it reads only the ledger's parquet and imports nothing from the five modules |

Inputs a human edits stay **CSV**; outputs are **parquet** (§3.4).

## The site report

With `--out-dir`, each solved premise also gets `site_report.html` beside its parquet
(`--no-report` skips it). It is one file with d3 and the data inlined, so it opens offline.

- **A Sankey of the site in one period.** Each layer has its own tab and its own unit:
  Energy (PJ/yr), CO₂ (kt/yr) and Materials (Mt/yr). A carrier's layer comes from its
  `carrier_kind`. Imports enter on the left. Flows leave to a process duty, to export, to
  disposal, or, in the Energy layer, to `Losses` or `Used in processing` (energy drawn by a
  unit that makes a material product). A heat pump's or chiller's surplus output enters
  from `Ambient heat`.
- **A year slider with a play button.** The layout and the width scale are fixed across
  periods, so a node never moves and a smaller site draws smaller.
- **Charts across all periods.** Imports by carrier, available capacity by unit (side by
  side, one chart per capacity unit), cost by term (discounted or not, checked against the
  reported objective), and CO₂ vented against CO₂ captured.

The edges come from the ledger's `unit_flow` table, one row per `(unit, carrier, role,
period)`, signed. Its C8-side rows net per unit to `carrier_mix.produced` and `consumed`,
and its `duty_output` rows sum to `dispatched`. The report nets each unit's roles on a
carrier before drawing, because the capture train both draws and emits `co2_fuel_fossil`;
the tooltip shows the roles behind the net figure. The vendored d3 and its rebuild recipe
are in `src/carb3/report/vendor/`.

## State of the three premises

All three solve to optimality (checked 2026-10-07, `make carb3-run`).

| Premise | Objective | Outcome |
|---|---|---|
| `mvp-minimal` | £39.5707m | The grade-2 and grade-3 heat duties switch to heat pumps at 2025, the first period C5 (no building in the start year) allows |
| `mvp-dairy` | £142.7571m | The grade-2 and grade-4 drying duties switch at 2025; refrigeration is met by an electric chiller, and from 2025 a heat pump on its condenser heat (`heat_pump_chiller_condenser`) serves the boiler-house hot water ([note 23](../docs/notes/23_reject_heat_recovery_plan.md) section 10) |
| `mvp-cement` | £3,640.0994m | The kiln moves from coal to gas and the grinder substitutes clinker at 2025; an amine capture train is built at 2035, captures 90% of each of the gas kiln's three CO₂ streams, and its CO₂ is exported |

Carbon is 60% of the cement works' objective. The works stopped being infeasible on
2026-09-20, after two fixes. The first is that A2 (premise to duties) now reads a product duty
from `premise_throughput` at the base year, as spec §3.1.2 says. The second restores export,
x_{c,t}, for carriers with `may_export`, a `premise_connection` row and a complete price
series. Without it nothing could consume `co2_captured`, so C8 (carrier balance) pinned every
capture train to zero. [Note 20](../docs/notes/20_reference_data_open_questions.md) items 51
to 53 record this. The kilns' `co2_process` coefficients were then corrected to the kt basis
(item 56), which is when capture started being built.

**The capture train takes a fraction of each stream its hosts make**
([note 24](../docs/notes/24_ccs_per_stream_capture_plan.md), closing item 57). Each of
`ccs_amine`'s `emission_input` rows is a capture rate, 0.90, from the COMIT workbook, and C14
(a capture train treats its hosts' flue gas) lets it treat a share of each host kiln's
activity and capture 0.90 of every CO₂ stream that share makes. From 2035 it treats the whole
gas kiln: 0.511 Mt/yr captured of 568 kt/yr made, on 0.560 Mt/yr of capacity. Its own
reboiler's CO₂ is not captured, so the works still vents about 106 kt/yr of charged CO₂ (39.2
of process CO₂ and 66.4 of fossil fuel CO₂, the reboiler's 49.1 among it). Until 2026-10-07
the three rows were read as a fixed blend, the cement worked example's own stack, and the
scarce biogenic stream capped the train at 0.023 Mt/yr; the objective was £4,554.93m.

## Output tables

With `--out-dir`, each solved premise writes eleven parquet tables under `<out>/<premise_id>/`:
seven from the ledger and four from the run report. This is the slice's output, not the full
spec §8 target contract.

| Table | Rows | Columns (one row per) | Meaning |
|---|---|---|---|
| `cost_by_term.parquet` | one per term per period (long format) | `period`, `term`, `annual`, `discount_factor`, `discounted` | Cost contribution by term. Five terms: `capex`, `opex`, `fuel`, `carbon`, `export` (the one term that can be a revenue or a cost, with the CO₂ transport tariff folded in). `annual` is undiscounted, `discounted` is `annual` times `discount_factor`. The `discounted` values must sum to `run_report.objective` |
| `carrier_mix.parquet` | one per carrier per period | `carrier_id`, `period`, `carrier_kind`, `imported`, `produced`, `consumed`, `disposed`, `exported`, `dispatched`, `net` | Carrier balance, flow in and flow out. `produced` and `consumed` are the two halves of C8 (carrier balance) read separately; `net` is C8's own residual and is zero where the balance closes |
| `dispatch.parquet` | one per unit per duty per period | `unit_id`, `premise_id`, `process_id`, `carrier_id`, `duty`, `kind`, `period`, `activity` | Activity of a unit on a duty (z_{u,q,t}). `kind` is `supply` for a unit making a carrier that no duty asks for, which carries no process and is settled by C8 rather than C1 (duty satisfaction) |
| `build.parquet` | one per unit per period | `unit_id`, `period`, `new_capacity`, `available_capacity`, `surviving_capacity`, `built_standing` | n_{u,t}, a_{u,t} and e_{u,t}. `built_standing` is `a - e`, the new capacity standing that capex is charged on |
| `disposal.parquet` | one per carrier per period | `carrier_id`, `period`, `quantity`, `carbon_charge`, `carbon_price`, `carbon_cost` | Amount vented (d_{c,t}); `carbon_cost` is non-zero only where `carbon_charge` is 'charged' (spec §3.4) |
| `unit_flow.parquet` | one per unit per carrier per role per period | `unit_id`, `carrier_id`, `role`, `period`, `carrier_kind`, `flow` | Signed flow of each unit on each carrier in each role: a single `flow` column, drawn from the solved activity times the C8 coefficient set. A capture train's `emission_input` rows are its capture, −Γ, read from `capture_by_host` |
| `capture_by_host.parquet` | one per capture train per host per carrier per period | `unit_id`, `host_unit_id`, `carrier_id`, `period`, `rate`, `treated_activity`, `captured` | C14 (a capture train treats its hosts' flue gas) split by host: the rate ν, the host activity the train treats (z^host) and the kt it captures. `captured` sums over hosts to the train's `emission_input` rows in `unit_flow`. Where a train's capacity binds, the split across hosts is an allocation the LP chose, not a measurement. Empty at a premise with no capture train |
| `run_report.parquet` | one row | `premise_id`, `status`, `objective`, `n_variables`, `n_constraints`, `wall_clock_seconds`, `n_units_admitted`, `n_units_dropped`, `n_units_dropped_at_premise` | The G1 (single-premise wall clock) measurement, solver status, final objective, problem size, and the §3.2 admission screen counts |
| `screen_dropped.parquet` | one per dropped unit per failed leg | `unit_id`, `leg`, `detail` | §3.2 admission screen's work list: which units were refused and why. Written even if empty |
| `eligibility_dropped.parquet` | one per refused unit per process | `premise_id`, `process_id`, `unit_id`, `reason`, `detail` | Units a process refused by `min_duty`, a 0.00 `max_share` or a recovery unit's `min_viable_scale`. Written even if empty |
| `sub_minimum_recovery.parquet` | one per recovery unit per period built below its floor | `unit_id`, `period`, `new_capacity`, `min_viable_scale` | Recovery units the LP built with positive new capacity below `min_viable_scale` (spec §5.7, check 5). Reported, not constrained. Written even if empty |

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

The `duty_share` handling matches §3.3. A duty's quantity is the premise's `known_activity`
for the process times the row's `duty_share`. A gradeable carrier with no `grade_rank` stops
the run, following §3.3's rule that a heat or cooling duty must have a grade. A process whose
units make a non-exportable `product`, such as `clinker`, yields no duty (D16, an internal
product is a carrier and not a duty) and is settled by C8.

Still open from the build: note 20 item 54, the activity variable a D16-suppressed process
still needs; item 55, the CO₂ export route has no sourced price, so the £40/t tariff is
synthetic. Item 57 is closed by note 24; the cement worked example is re-solved against it
as a follow-on (note 24 Task 4).
