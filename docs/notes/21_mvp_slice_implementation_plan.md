# The pre-M2 demonstration slice — implementation plan

*Written 2026-09-18, revised 2026-09-19 after `/plan-eng-review`. Plans the first Python
build of the CaRB3 site energy system: a running least-cost model over three synthetic
premises, on the real reference tables.*

This note plans **code**, not specification. The specification it builds against is the
live [implementation spec](../specs/2026-08-28-carb3-site-energy-system-implementation.md)
§5, and the feature and milestone vocabulary is
[note 18](18_mvp_feature_prioritisation.md)'s. Nothing here proposes a specification change,
with one exception recorded in §6.4.

> **Revised after review.** The first draft dropped the disposal variable $d_{c,t}$ and
> charged carbon on fuel. Both were wrong, and together they made the slice unsolvable at
> both example premises. §2 and §4 below are rewritten. The review's full finding list is in
> the report at the foot of this file.

---

## 1. What this is, and why it is not M2

[Note 18](18_mvp_feature_prioritisation.md) defines the MVP as features `MF-01`–`MF-80`
under MoSCoW, delivered across milestones M0–M6. The build planned here maps onto **M2
(walking skeleton, trusted solve)** but sits deliberately *below* its exit gate.

M2 exits on: the cement fixture (`MF-22`) matching its expected tables within the `MF-58`
tolerances; V10 (determinism) passing on two machines; V29 (every emission carrier balances)
and V30 (the fossil/biogenic split before capture) green; and `G1` (single-premise wall clock)
measured and recorded. That is a demanding first build — it asks for a trustworthy answer
before anything has produced an answer at all.

This slice asks for less: **a model that solves, over three premises, and whose answer can be
checked by hand.** It is the rung below M2, and M2's gate is what it hands off to.

| | This slice | M2 |
|---|---|---|
| Premises | Three, synthetic | One, the cement fixture |
| Answer trusted to | Hand-computed arithmetic, plus a post-solve constraint-row check | `MF-58` tolerances against `MF-22`'s expected tables |
| Determinism | Not addressed; degenerate optima left visible | V10 on two machines, tie-break as a second-objective solve |
| Emissions | Carbon priced on disposal; no attribution layer, no evidence tiers | `MF-52`, `MF-53`, `MF-79`, `MF-80`; V29 and V30 |
| On-site generation | None | CHP, PV, export |

**Three premises rather than M2's one is a breadth gain, not a depth gain.** Once one premise
solves, a second is a loop rather than a structure. It is in scope because the demonstration
this slice exists to give is *comparative*, and one site cannot be comparative.

---

## 2. The model — §5 with terms switched off

Every symbol below is the live spec's §5. Nothing is invented for this slice; features are
removed, never added.

### 2.1 Objective

$$\min \; Z = \sum_{t} \delta_t \big( Z^{\text{capex}}_t + Z^{\text{opex}}_t + Z^{\text{fuel}}_t + Z^{\text{carbon}}_t \big)$$

with $\delta_t$ the present-value factor at the `discount_rate` of 0.035 held in
`scenario_parameters.csv`, and capex annuitised over each unit's `lifetime`.

**$\delta_t$ aggregates over each period's own span, which is not constant.** See §6.4.

| §5.4 term | In this slice | Why |
|---|---|---|
| $Z^{\text{capex}}$ | **In**, annuitised | Investment is the decision being demonstrated |
| $Z^{\text{opex}}$ | **In** | `unit.fixed_opex`, present for every admitted unit |
| $Z^{\text{fuel}}$ | **In** | `import_price` by carrier and period, for the five carriers that have one (§3.1) |
| $Z^{\text{carbon}}$ | **In**, charged on **disposal**, per §5.4 as written | The only dynamic input in the dataset; see §4 |
| $Z^{\text{infra}}$ | Out | No reinforcement variable; C11 (connection capacity) is out |
| $Z^{\text{net}}$ | Out | Tariffs are a refinement on a cost already dominated by carbon |
| $Z^{\text{exp}}$ | Out | No on-site generation, so nothing to export |
| $Z^{\text{strand}}$ | Out | No early retirement, so nothing strands |

**Carbon is charged on venting, not on fuel.** $Z^{\text{carbon}}_t$ reads $d_{c,t}$ over
carriers where `carrier.carbon_charge` is `charged`, less the biogenic credit, exactly as
§5.4 writes it. The first draft charged it on fuel consumed and claimed equivalence. That
claim was false on three counts: the spec's subtrahend is the **`zero_rated` credit**, not a
capture credit, and `biomethane`, `solid_biomass`, `wood_pellets` and `organic_waste` all
carry `biogenic_fraction` 1.0; process CO₂ reaches the objective through `co2_process`, which
fuel-charging cannot produce and which is the majority of a cement kiln's emissions; and
`electricity` is `is_indirect`, so it is never disposed of on site and its carbon belongs to
the §7.7 allocation layer rather than to the objective.

### 2.2 Decision variables

| §5.2 variable | In this slice | Why |
|---|---|---|
| $n_{u,t}$ new capacity built | **In** | The investment decision. Bounded to zero before `earliest_year` (§3.1) |
| $a_{u,t}$ capacity available | **In** | Bounds dispatch through C2 |
| $z_{u,q,t}$ activity dispatched to duty | **In** | Duty-indexed, per §5.2 — one boiler in several $U_q$ must not be credited twice |
| $e_{u,t}$ surviving incumbent capacity | **In** | Carries D11 (existing plant has an age). Mechanism only; see §4.3 |
| $m_{c,t}$ / $m_{c,k,t}$ import | **In** | Site-level for delivered fuels, connection-indexed for networked carriers, per D16 (the site boundary on the carrier) |
| $d_{c,t}$ **disposal** | **In** | **Restored after review.** Without it C8 has no sink and the model cannot solve; see below |
| $h_{c \to c',t}$ heat cascaded | Out | C10 (heat grade cascade) is enforced by eligibility instead — see §6.2 |
| $z^{\circ}_{u,t}$ undispatched primary output | Out | No internal `product` carriers in the synthetic premises |
| $r_{u,t}$ early retirement | Out | Retirement is by survival function only |
| $x_{c,k,t}$ export | Out | No on-site generation |
| $w_{k,t}$ reinforcement | Out | C11 out |

**Why $d_{c,t}$ is not optional.** `unit_input_output.csv` carries **59 rows with
`role = reject`**, from 59 distinct units, every one of them into `heat_lt60`.
`carrier.csv` makes `heat_lt60` an `intermediate` at `grade_rank` 1, `may_dispose` TRUE,
`may_import` FALSE — and exactly one unit in the whole table consumes it,
`heat_pump_lt_reject`. Grade 1 is the bottom, so there is nothing to cascade *to*. With no
disposal variable, C8 at that node forces every fuel-fired low-temperature-heat boiler to
zero unless a reject heat pump is co-built in fixed proportion, which is a physical coupling
that does not exist. The same holds for `co2_process`: 34 producing units, two consumers
(`ccs_amine`, `tgr_blast_furnace_coke`), so a cement kiln cannot run without a capture train
and `mvp-cement` is infeasible rather than unchanged.

**It is gated on `carrier_kind`, and the gate is the whole safety argument** (§5.2).
`intermediate` and `emission` carriers may be disposed of; `primary` and `product` may not.
Otherwise the model could import gas and dump it.

**Restoring $d_{c,t}$ pulls `MF-77` and `MF-78` forward from M2.** Emission carriers, the
derived fuel-CO₂ coefficients and the fossil/biogenic split are now in scope. This is the
largest single change the review made to the slice's size, and it is not optional.

### 2.3 Constraints

| §5.5 constraint | In this slice | Why |
|---|---|---|
| C1 duty satisfaction | **In** | The model's purpose. Carries the `max_share` upper bound (§3.1) |
| C2 activity limited by available capacity | **In** | What makes the LP split across units rather than picking one |
| C3 capacity transfer between periods | **In** | What makes it a pathway rather than seven independent years |
| C4 incumbent ageing | **In**, fallback tier only | `MF-43`. Mechanism only — it binds on nothing in this slice; see §4.3 |
| C5 no building in the start year | **In** | One line; prevents the base year absorbing the whole pathway |
| C8 carrier balance | **In** | "The core change"; every carrier node, every period, with the disposal term |
| C10 heat grade cascade | **In**, via eligibility | Without it the gas boiler and the heat pump never contend; see §6.2 |
| C6 unit stability | Out | `MF-51`, a Could, deferred by note 18's temporal-coverage review |
| C7 known changes | Out | No announced commitments in synthetic premises |
| C9 infrastructure availability | Out | No scenario gating in the slice |
| C11 connection capacity | Out | Needs the §5.6 peak rebuild, which is a milestone of its own |
| C12 siting cap | Out | Exists because PV is otherwise unbounded; no area-bound units in scope |

**The problem is a pure LP and must stay one.** No binaries, per §5.2. Minimum viable scale
is handled by the `min_duty` screen at load (§3.1), never by a fixed-charge binary.

---

## 3. The data — real reference tables, synthetic premises

The reference side is **read, not written**. The premise side is synthetic. This split is
what the slice exists to test: whether the reference tables built over the last month are
actually sufficient to construct a problem.

### 3.1 Read from a configurable reference root, default `docs/notes/data/`

The root is a parameter with a documented default resolved from the repo root, never a path
literal and never relative to the caller's working directory. **CLAUDE.md's line "COMIT never
reads it" is corrected in the same commit**: the directory is now an input to `carb3`.

| Table | Rows | What the model takes from it |
|---|---|---|
| `carrier.csv` | 44 | `carrier_kind`, `grade_rank`, `may_import`, `may_dispose`, `is_indirect`, `biogenic_fraction`, `carbon_charge` |
| `unit.csv` | 137 | `capex`, `fixed_opex`, `lifetime`, `availability_factor`, `capacity_to_activity_factor`, `grade_out`, `grade_in_max`, `duty_family` |
| `unit_input_output.csv` | 446 | Signed coefficients $\iota_{u,c,\theta}$ by role, **including `reject` and `emission`** |
| `unit_eligibility.csv` | 2612 | $U_q$, **and** `earliest_year`, `max_share`, `min_duty` |
| `scenario_parameters.csv` | 155 | `import_price`, `carbon_price`, `discount_rate`, `ef_natural_gas`, `ef_electricity` |
| `activity_process_duty_profile.csv` | 427 | Duty structure: which duties, on which carrier, at which `grade_rank` |
| `activity_process_register.csv` | 376 | The process set behind each `carb3_activity` |

Row counts are as at 2026-09-19 and are descriptive, not asserted.

**`unit_eligibility.csv` is a three-table join, not a lookup.** It is keyed
`(unit_id, carb3_activity, process_id)` — by *process*, not by duty — with no carrier or
grade column, and **142 rows carry a blank `process_id`** and are activity-level supply.
Building $U_q$ means joining it to `activity_process_duty_profile` for the duty and to
`unit.grade_out` for C10. Its three constraint columns are all live and all honoured:

| Column | Rows | Values | Where it lands |
|---|---|---|---|
| `earliest_year` | 9 | 2030, 2035, 2040 | Upper bound of zero on $n_{u,t}$ before that year. `boiler_lt_hydrogen` 2035, `heat_pump_ht` 2030, every CCS train 2035 or 2040 |
| `max_share` | 4 | 0.00, 0.35, 0.55, 0.60 | Upper bound on that unit's share of the duty in C1. One is `boiler_lt_coal` at `Food Processing Centre`, `max_share` 0.00 — a hard prohibition at the dairy |
| `min_duty` | 15 | 0.01 to 0.50 | Screens the unit out where the duty is smaller. `heat_pump_lt_air` carries 0.01, so `mvp-minimal`'s duty must clear it |

### 3.2 The admission screen — a unit the model cannot fully cost does not enter $U$

**This is the single most important guard in the build.** `validate_carb3_data.py` reports
24 blocking checks green on data that a cost-minimiser reads as free energy.

A unit is admitted only if **all** of the following hold. Failures are dropped, not fatal;
every drop is listed by `unit_id` with its reason in the run report.

| Requirement | Why | Scale of the gap today |
|---|---|---|
| `capex` present and non-blank | A blank is read as zero and the unit is built free | 15 units blank |
| `lifetime`, `fixed_opex`, `availability_factor`, `capacity_to_activity_factor` present | Annuitisation and C2 are undefined without them | 13, 15, 13, 13 units blank |
| At least one `unit_input_output` row | No rows means no consumption, so output is free | 26 units |
| `fuel_input` row present where `unit_class` requires one | Same failure one step along | 37 units have none, not all wrongly |
| **Every consumed carrier has an `import_price` for every period, or is produced on site** | Otherwise the fuel is free | **Only 5 of 15 `may_import` carriers have a price** |

**The worked example of why.** `unit.csv:12`, `heat_exchanger_lt_steam`: `capex` 0,
`fixed_opex` 0, and no `unit_input_output` rows at all. It produces low-temperature heat from
nothing, for nothing, and `unit_eligibility.csv:1644-1646` makes it eligible on
`hot_water_sterilisation_cleaning`, `scalding_singeing` and `steam_hot_water` — the dairy's
own duties. Unscreened, it serves the whole duty free and the demonstration never happens.

**The price leg bites hardest.** `import_price` exists for `coal`, `electricity`,
`heavy_fuel_oil`, `light_fuel_oil` and `natural_gas`. It is missing for `hydrogen`,
`biomethane`, `lpg`, `solid_biomass`, `wood_pellets`, `organic_waste`, `waste_derived_fuel`,
`coke`, `coking_coal` and `petroleum_products_misc`. `boiler_lt_hydrogen`,
`boiler_lt_biomass`, `boiler_lt_biomethane` and `boiler_lt_lpg` all have complete capex and
coefficients, so only the price check stops them burning free fuel and winning.

**The screen's output is a work list.** Each dropped unit names the carrier and the periods
whose price is missing, which is precisely what
[note 20](20_reference_data_open_questions.md) needs to record.

The same check lands in `validate_carb3_data.py` as an **advisory** count surfaced by
`make data-report`, not by `make data-check`. Making it blocking would turn 38 units red and
break the green baseline note 18's M1 exit depends on, in the same commit as an unrelated
package.

### 3.3 Duty structure is derived; only magnitudes are synthetic

Spec §3.9 is explicit that `process_duty` is "derived at run time by A2 from
`activity_process_register` and `activity_process_duty_profile`". It is not an input table.

A **minimal A2** therefore reads those two tables to determine which duties each premise has,
on which carrier, at which `grade_rank`. **Only `quantity` is hand-written**, taken from the
worked examples. No premise energy allocation, no A3, no A4 back-solve, no D10 refinement
ladder.

This keeps the duty-profile table genuinely read, so the slice proves the grade bands, carrier
bindings and process keys resolve — which is the integration finding worth having. Both
worked-example activities exist in the register: `Cement Works` and `Food Processing Centre`,
of 55.

### 3.4 Synthetic, written under `carb3/data/premises/`

Four premise-side tables, three premises, **CSV** so every file a human edits stays diffable.

| Premise | Cut from | `carb3_activity` | Why it is here |
|---|---|---|---|
| `mvp-minimal` | Written fresh | `Food Processing Centre` | One duty, two eligible units, one incumbent. The case whose optimum is arithmetic. Its duty must clear `min_duty` 0.01 |
| `mvp-dairy` | [food and drink worked example](../specs/2026-08-28-carb3-site-energy-system-worked-example-food-drink.md) | `Food Processing Centre` | Low- and mid-grade heat, a genuine heat pump route, and the `max_share` 0.00 row on `boiler_lt_coal` |
| `mvp-cement` | [cement worked example](../specs/2026-08-28-carb3-site-energy-system-worked-example-cement.md) | `Cement Works` | High-grade duty, delivered fuels, process CO₂ through `co2_process`, and `earliest_year` gating every capture train |

| Table | Spec | What the synthetic rows carry |
|---|---|---|
| `premise_record` | §3.1 | Premise identity, `carb3_activity`, connections for networked carriers (§3.1.3) |
| `premise_process_detail` | §3.10 | Which processes run at the premise, and at what capacity |
| `premise_process_unit` | §3.10.2 | Which units each process runs — the one-row-per-unit table from the 2026-09-17 pass |
| `premise_process_vintage` | §3.15 | Install year per unit. Mechanism input for C4; see §4.3 for why it changes no result |

`process_duty` is **not** in this list. It is derived (§3.3). Outputs and any fixture written
for M2 are **parquet**.

---

## 4. What drives the pathway

### 4.1 Price divergence does not fire

`import_price`, £m/PJ at 2021 prices:

| Year | Electricity | Natural gas | Ratio |
|---|---|---|---|
| 2021 | 31.50 | 7.04 | 4.47 |
| 2025 | 45.14 | 10.53 | 4.29 |
| 2030 | 32.10 | 7.50 | 4.28 |
| 2035 | 30.45 | 7.53 | 4.04 |
| 2040 | 29.39 | 7.56 | 3.89 |
| 2045 | 29.61 | 7.59 | 3.90 |
| 2050 | 30.12 | 7.63 | 3.95 |

The ratio narrows to 2040 and widens again. **There is no crossover anywhere in the horizon.**
Note the 2025 gas spike to 10.53, a 50% rise over 2021 and the largest single move in the
table.

### 4.2 Carbon drives it, and it drives it immediately

The two units that contend for a low-grade heat duty, from `unit.csv` and
`unit_input_output.csv`:

| | `boiler_lt_gas` | `heat_pump_lt_air` |
|---|---|---|
| Output carrier | `heat_100_150` (grade 3) | `heat_60_100` (grade 2) |
| Coefficient | 1.13636 PJ gas per PJ heat (η = 0.88) | 0.3571 PJ electricity per PJ heat (COP 2.80) |
| `reject` row | 0.13668 into `heat_lt60` | none |
| `capex` | 5.6421 | 15.2949 |
| `fixed_opex` | 0.11284 | 0.3059 |
| `lifetime` | 25 | 20 |
| `availability_factor` | 0.9823 | 0.9808 |

**The decision is between a new heat pump and an incumbent boiler's *avoidable* cost.** The
incumbent's capex is sunk, so it does not appear. At 2025, the first period C5 allows
building, per PJ/yr of `heat_60_100` duty, capex annuitised at 3.5%:

| £m/yr | New heat pump | Gas incumbent, avoidable only |
|---|---|---|
| Annuitised capex | 1.08 | — (sunk) |
| Fixed opex | 0.31 | — (on standing capacity either way) |
| Fuel | 16.12 | 11.97 |
| Carbon @ £259.70/t | 3.26 | 15.09 |
| **Total** | **20.76** | **27.06** |

The heat pump wins by 23% at the **first** opportunity, at every premise, at every vintage.

**The carbon term is the only dynamic input in the dataset.** `ef_natural_gas` is flat at
51.12 kt/PJ across the horizon while `ef_electricity` falls 58.02 → 0.67 kt/PJ from 2021 to
2050, against a `carbon_price` rising £244.47 → £378.09/t.

Capacity figures above omit the $1/(\gamma\alpha)$ factor, understating both capex rows by
about 2%. Directionally irrelevant; the analytic tests in §5.2 carry it.

### 4.3 C4 and the vintages are mechanism, not driver

**They change no number in this slice, and the plan no longer claims they do.** C2 is an
inequality and C1 is an equality, so nothing compels an incumbent to run; idling costs only
`fixed_opex` on standing capacity. Given §4.2, the model abandons the incumbent at the first
buildable period regardless of how old it is.

C4, $e_{u,t}$, the survival function and `premise_process_vintage` are all built anyway,
because `MF-43` is a Must at M2 and the survival function is a short pure-parameter routine.
The test asserts **the decay itself** — that surviving incumbent capacity falls as
$\eta_{u,t}$ says — not that a build waits for it.

**What would make the pathway gradual is C6 (unit stability), not C4.** C6 is `MF-51`, a
Could, and stays out. The slice's honest expected answer is a step at the first buildable
period, staggered only where `earliest_year` gates a technology.

---

## 5. Build

### 5.1 Layout

```
carb3/                          # new; R/ is untouched
  pyproject.toml                # linopy, pandas, xarray, pandera, pydantic, pyarrow; HiGHS pinned
  src/carb3/
    load.py                     # reference + premise tables -> typed records; the §3.2 screen
    sets.py                     # minimal A2; Q, U, U_q via the three-table join; C10 widening;
                                #   earliest_year / max_share / min_duty; unservable-duty diagnosis
    survival.py                 # D11 survival function, computed before the LP
    build.py                    # variables, C1-C5, C8, C10, objective, solve
    ledger.py                   # cost by term, carrier mix, dispatch, build, disposal -> parquet
  data/premises/*.csv
  tests/
```

One line, `^carb3$`, is added to `.Rbuildignore` so `R CMD check` ignores the directory.

**Nothing in the stack is installed today.** Of numpy, pandas, xarray, linopy, highspy,
pandera and pyarrow, only `pydantic` is present. The slice introduces a second Python
environment, and the stdlib-only generators under `docs/notes/examples/` must not share it.

### 5.2 Infeasibility is an expected outcome, not an error

Spec §13's failure-mode table routes "a duty has no eligible unit after screening" to the A7
ladder. The §3.2 screen makes that likelier, not less likely.

**Before building the LP**, check every duty has a non-empty eligible-unit set and report by
name any that does not, with its premise, its period and the units the screen removed. Handle
a non-optimal solver status explicitly and print it rather than raising.

**No A7 relaxation ladder.** Of its eight rungs only C10 and C1 exist here, and at three
premises knowing which duty is unservable is worth more than automatically working around it.

### 5.3 Tests — every path, not only the arithmetic

Full coverage of all 25 traced codepaths. Four are **critical**: no test, no error handling,
and a silent wrong answer rather than a crash.

| Path | Asserts | Critical |
|---|---|---|
| Admission screen, capex leg | Blank and zero-capex units dropped and reported | **yes** |
| Admission screen, coefficient leg | `heat_exchanger_lt_steam` specifically refused | **yes** |
| Admission screen, price leg | `boiler_lt_hydrogen` dropped, naming carrier and periods | **yes** |
| Lifetime conversion | $\ell_u$ from actual years, not a uniform Δ | **yes** |
| Solver status | Non-optimal reported, not raised | **yes** |
| C8 closure | Matrix × solution checked per node per period, independent of the solver | **yes** |
| Loader fail-loud | Missing file, missing column, unknown column | |
| Type coercion | `period` stays integer through CSV | |
| FK resolution | Synthetic premise `unit_id` and `process_id` resolve against the reference tables | |
| Minimal A2 | Duty profile rows resolve; `grade_rank` present where gradeable | |
| C10 direction | Grade-3 unit serves a grade-2 duty, **refused** a grade-4 duty | |
| `earliest_year` | $n_{u,t} = 0$ before the year; positive after | |
| `max_share` | `boiler_lt_coal` held at zero share at the dairy | |
| `min_duty` | Unit screened out below its floor | |
| Unservable duty | Named with premise and period before the LP is built | |
| Survival decay | $e_{u,t}$ falls as $\eta_{u,t}$ says | |
| Survival edges | Unit past lifetime at $t_0$; unit with no vintage row | |
| One duty, one unit | Cost = duty × coefficient × price | |
| Cheaper uncapped | All flow to the cheaper | |
| Cheaper capped | Split exactly at the cap; C2 binds | |
| C3 transfer | Capacity persists across periods | |
| Disposal | `heat_lt60` reject disposed of; boiler runs without a reject heat pump | |
| Carbon on and off | Ranking inverts per §4.2 | |
| Objective decomposition | Terms sum to the reported objective | |
| Problem size | Variable and constraint counts within a band derived from screened set sizes | |

**The size assertion exists because a dense formulation is invisible here.**
[PyPSA/linopy #248](https://github.com/PyPSA/linopy/issues/248) documents that an
ineffective mask silently produces a dense model rather than an error. At three premises
HiGHS solves either version in under a second, so the mistake would surface at M5 instead.
Counts and solve time per premise are printed, which also starts the `G1` measurement.

### 5.4 Exit

- All 25 paths tested and passing.
- All three premises solve, and a non-optimal status would be reported rather than thrown.
- C8 closes at every carrier node in every period, checked post-solve against the built matrix.
- `mvp-dairy` switches and `mvp-cement` does not, and both are explicable from §4.2.
- The screen's dropped-unit list is written to the run report and folded into note 20.
- `make check` is still green, and no file under `docs/notes/data/` has changed.

---

## 6. Deliberate deviations, to be repaid

### 6.1 C10 enforced by eligibility, not by a cascade variable

§5.5's C10 admits $h_{c \to c',t}$. This slice widens $U_q$ at load so a unit is eligible for
any duty at or below its `grade_out`, which is what `MF-41` describes.

**Not a debt** — `MF-41` is the Must form and this is it. Recorded because the variable's
absence from §2.2 would otherwise read as a gap.

### 6.2 No determinism work

`MF-45` (price wedge and lexicographic tie-break) and `MF-74` (determinism made real) are
both Musts and both out. Degenerate optima are left **visible** rather than silently resolved.

**Repaid at:** M2, where V10 (determinism) is on the gate.

### 6.3 No emissions attribution layer

`MF-52` (§7's attribution rules), `MF-53` (evidence tiers) and `MF-79` (an indirect carrier
charged on import) are out. `MF-77` and `MF-78` are **in**, pulled forward by §2.2.

**Repaid at:** M2. `MF-79` cannot bite here: it exists because on-site generation makes
consumption exceed import, and there is no on-site generation.

### 6.4 Periods are a vector, not a formula — a spec defect

Spec §5.1 assumes a uniform timestep: $y_t = y_{t_0} + \Delta t$ and
$\ell_u = \lceil L_u / \Delta \rceil$. **The real periods are 2021, 2025, 2030, 2035, 2040,
2045, 2050 — a 4-year first gap and 5-year gaps thereafter.** Neither formula holds.

This slice carries the explicit year vector, derives each gap, aggregates $\delta_t$ over each
period's own span, and converts lifetimes against actual years remaining.

**This is a defect in §5.1, not in the slice.** It is the one item in this note that owes the
specification a change.

---

## 7. Decisions taken at review

| Question | Decision |
|---|---|
| Module count | Five, not seven: `load`, `sets`, `survival`, `build`, `ledger` |
| Uncosted units | Load-time admission screen, fail loud, listed and skipped (§3.2) |
| Infeasibility | Pre-solve diagnosis, explicit solver status, no A7 ladder (§5.2) |
| `process_duty` | Minimal A2 derives structure; magnitudes hand-written (§3.3) |
| Reference-data location | Configurable root, default `docs/notes/data`, CLAUDE.md corrected |
| Stack | Full note 08 stack: linopy, pandas, xarray, pandera, pydantic, parquet |
| File format | CSV for hand-authored inputs, parquet for outputs and fixtures |
| Validator | Advisory in `validate_carb3_data.py`, blocking in `carb3` |
| Test scope | All 25 paths |
| Problem size | Asserted in tests, printed per premise |
| Disposal | $d_{c,t}$ restored; carbon charged on venting; `MF-77`/`MF-78` in scope |
| C4 and vintages | Kept as mechanism; end-of-life narrative withdrawn; test rewritten |
| Fuel prices | Folded into the admission screen |
| Eligibility columns | `earliest_year`, `max_share`, `min_duty` all honoured; $U_q$ built as the real join |
| Timestep | Explicit year vector; §5.1 owed a correction |

---

## 8. What already exists

| Thing | Reused? |
|---|---|
| `docs/notes/examples/comit_mini_linopy.py` | **Yes.** 131 lines, two sites, three techs, three years, with a hand-computed optimum in its docstring and an honest note on degeneracy. It does not run today (no pandas). It is the reference for objective shape and for `build.py`'s linopy idiom. The first draft of this plan did not mention it |
| The 13 reference tables under `docs/notes/data/` | **Yes**, read unmodified through a configurable root |
| `validate_carb3_data.py` | **Yes**, extended with the advisory cost-completeness count |
| The two worked examples and their `MF-22`/`MF-23` fixtures | **Partly.** Their §1 premises are cut down into the synthetic tables; their expected tables are M2's gate, not this slice's |
| `R/` — the running national model | **No.** Untouched. The comparison against it is M3 |

---

## 9. NOT in scope

| Deferred | Rationale |
|---|---|
| A7 relaxation ladder | Only two of eight rungs exist here; diagnosis beats automatic relaxation at three premises |
| Determinism (`MF-45`, `MF-74`) | Degenerate optima are more useful visible than hidden at this rung |
| Emissions attribution (`MF-52`, `MF-53`, `MF-79`, `MF-80`) | Reporting layers; none changes a pathway |
| C6, C7, C9, C11, C12 | Each needs machinery the slice has no use for; C12 exists for PV, which is out |
| On-site generation, CHP, PV, export, storage | The exclusion that makes `MF-42`, `MF-79` and `MF-80` moot rather than skipped |
| Collapsing $m_{c,k,t}$ to $m_{c,t}$ | The connection index carries no information while C11, $Z^{\text{net}}$ and export are all out, and `import_price` has no connection dimension. Left as-is to stay close to §5.2; see the TODO |
| A PyPSA / Calliope spike | Note 08 §2 names it as a prerequisite — "a spike might show 70% of COMIT is configuration rather than code" — and it has never been run. Not blocking a first slice, but it is owed before the architecture hardens |
| CI, packaging, distribution | No `.github/` exists and `make check` has no `carb3` target. The package's tests would sit outside every gate in the repo. A separate call, flagged rather than silently dropped |
| Filling the 10 missing `import_price` carriers | A sourcing task with real scenario implications, especially hydrogen. The screen makes the gap visible and precise instead |

---

## 10. Failure modes

| Codepath | Realistic failure | Test? | Error handling? | Silent? |
|---|---|---|---|---|
| Admission screen | A blank capex is read as zero and a unit is built free | yes | drop + report | would have been |
| Admission screen, price leg | An unpriced carrier burns free | yes | drop + report | would have been |
| Minimal A2 | A premise names an activity absent from the register | yes | fail loud at load | no |
| $U_q$ join | A blank-`process_id` row is mapped to a duty it should not reach | yes | documented rule | **partly** |
| `earliest_year` | A capture train is built in 2025 | yes | bound | would have been |
| Survival | A 25-year life read as 25 periods | yes | assertion | would have been |
| C8 | A carrier node does not balance and the solver hides it | yes | post-solve matrix check | would have been |
| Solve | Status is infeasible and the run reports a pathway anyway | yes | explicit status | would have been |
| Problem size | Mask ineffective, model built dense | yes | count assertion | **yes, until M5** |

**No critical gaps remain** — every silent failure mode above now has both a test and a
handler. The two marked were critical before this review.

---

## 11. Implementation Tasks

Synthesized from the review's findings. Each derives from a specific finding above.

- [ ] **T1 (P1, human: ~1 day / CC: ~30min)** — scaffolding — Create `carb3/` with `pyproject.toml`, the five modules, `.Rbuildignore` entry, and a `carb3` target in the Makefile
  - Surfaced by: Step 0 complexity check; NOT-in-scope CI gap
  - Files: `carb3/`, `Makefile`, `.Rbuildignore`
  - Verify: `uv run pytest` collects; `make check` still green
- [ ] **T2 (P0, human: ~1 day / CC: ~35min)** — load — Admission screen over capex, lifetime, opex, coefficients and fuel prices; dropped units reported
  - Surfaced by: Architecture issue 2 and issue 14 — `unit.csv:12`; 5 of 15 `may_import` carriers priced
  - Files: `carb3/src/carb3/load.py`
  - Verify: `heat_exchanger_lt_steam` and `boiler_lt_hydrogen` both dropped with reasons
- [ ] **T3 (P0, human: ~2 days / CC: ~60min)** — build — Restore $d_{c,t}$ gated on `carrier_kind`, add its term to C8, charge carbon on venting per §5.4
  - Surfaced by: Outside voice issue 11 — 59 `reject` rows into `heat_lt60`; 34 `co2_process` producers, 2 consumers
  - Files: `carb3/src/carb3/build.py`
  - Verify: `boiler_lt_gas` runs without a co-built reject heat pump; `mvp-cement` solves
- [ ] **T4 (P1, human: ~1 day / CC: ~40min)** — sets — Build $U_q$ as the three-table join; honour `earliest_year`, `max_share`, `min_duty`; rule for the 142 blank-`process_id` rows
  - Surfaced by: Outside voice issue 15 — `max_share` 0.00 at `Food Processing Centre`
  - Files: `carb3/src/carb3/sets.py`
  - Verify: no capture train built before its `earliest_year`; `boiler_lt_coal` held at zero at the dairy
- [ ] **T5 (P1, human: ~1 day / CC: ~45min)** — sets — Minimal A2: duty structure from `activity_process_duty_profile` and `activity_process_register`
  - Surfaced by: Architecture issue 4 — spec §3.9 derives `process_duty` at run time
  - Files: `carb3/src/carb3/sets.py`
  - Verify: both premises' duties resolve with `grade_rank` where gradeable
- [ ] **T6 (P1, human: ~2h / CC: ~15min)** — sets — Pre-solve unservable-duty diagnosis and explicit solver-status handling
  - Surfaced by: Architecture issue 3 — plan mentioned infeasibility zero times
  - Files: `carb3/src/carb3/sets.py`, `carb3/src/carb3/build.py`
  - Verify: a duty with an empty $U_q$ is named with premise and period
- [ ] **T7 (P2, human: ~4h / CC: ~25min)** — build — Explicit period year vector; per-period $\delta_t$ and lifetime conversion
  - Surfaced by: Outside voice issue 16 — first gap is 4 years, the rest 5
  - Files: `carb3/src/carb3/build.py`, `carb3/src/carb3/survival.py`
  - Verify: 2021→2025 discounting differs from 2025→2030
- [ ] **T8 (P1, human: ~3 days / CC: ~90min)** — tests — All 25 paths per §5.3, including the four critical and the problem-size assertion
  - Surfaced by: Test review — 6 of 25 paths planned
  - Files: `carb3/tests/`
  - Verify: `uv run pytest` green; coverage report shows no untested branch
- [ ] **T9 (P2, human: ~3h / CC: ~20min)** — data — Advisory cost-completeness count in `validate_carb3_data.py`, surfaced by `make data-report`
  - Surfaced by: Code quality issue 8 — root cause, `make data-check` is blind
  - Files: `docs/notes/examples/validate_carb3_data.py`
  - Verify: `make data-check` still green; `make data-report` names the count
- [ ] **T10 (P2, human: ~1h / CC: ~10min)** — docs — Correct CLAUDE.md's "COMIT never reads it" line; fold the screen's dropped-unit list into note 20
  - Surfaced by: Architecture issue 5
  - Files: `CLAUDE.md`, `docs/notes/20_reference_data_open_questions.md`
  - Verify: no stale claim remains
- [ ] **T11 (P2, human: ~2h / CC: ~15min)** — spec — Raise §5.1's uniform-Δ assumption as a defect
  - Surfaced by: §6.4
  - Files: `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md`
  - Verify: `make docs-check` green after the edit

---

## 12. Parallelisation

| Step | Modules touched | Depends on |
|---|---|---|
| T1 | `carb3/` root, `Makefile`, `.Rbuildignore` | — |
| T2 | `carb3/src/carb3/load.py` | T1 |
| T5 | `carb3/src/carb3/sets.py` | T2 |
| T4 | `carb3/src/carb3/sets.py` | T5 |
| T3 | `carb3/src/carb3/build.py` | T1 |
| T7 | `carb3/src/carb3/build.py`, `survival.py` | T3 |
| T6 | `carb3/src/carb3/sets.py`, `build.py` | T4, T7 |
| T8 | `carb3/tests/` | T6 |
| T9 | `docs/notes/examples/` | — |
| T10 | `CLAUDE.md`, `docs/notes/` | — |
| T11 | `docs/specs/` | — |

```
                    ┌─ Lane B: T2 → T5 → T4 ─┐
   Lane A: T1 ──────┤                        ├──→ Lane E: T6 → T8
                    └─ Lane C: T3 → T7 ──────┘

   Lane D: T9, T10, T11   (independent of carb3 entirely, parallel from the start)
```

- **Lane A** — T1 alone. Blocks B and C; nothing else can start inside `carb3/`.
- **Lane B** — T2 → T5 → T4, sequential, all on `load.py` then `sets.py`.
- **Lane C** — T3 → T7, sequential, both on `build.py` and `survival.py`.
- **Lane D** — T9, T10, T11. Three different trees (`examples/`, `CLAUDE.md` plus note 20,
  `specs/`), no shared file, launchable immediately.
- **Lane E** — T6 then T8. T6 spans `sets.py` **and** `build.py`, so it cannot run beside
  either B or C.

**Conflict flag:** T6 is the only task touching two modules owned by different lanes. Run it
after both merge, never inside one of them.

**Execution order:** launch A and D together. On A's merge, launch B and C in parallel
worktrees. Merge both, then E.

---

## Sources

- [Live implementation specification](../specs/2026-08-28-carb3-site-energy-system-implementation.md) §3, §4.2, §5, §13
- [Note 18](18_mvp_feature_prioritisation.md) — feature IDs, MoSCoW, milestones M0–M6
- [Note 17](17_mvp_what_it_does.md) — what the MVP does relative to COMIT
- [Note 08](08_python_redesign_approach.md) — the Python target architecture, the library recommendation, and the unrun PyPSA/Calliope spike
- [Note 20](20_reference_data_open_questions.md) — where the screen's findings get recorded
- [`examples/comit_mini_linopy.py`](examples/comit_mini_linopy.py) — the runnable proof-of-concept
- [Cement worked example](../specs/2026-08-28-carb3-site-energy-system-worked-example-cement.md) §12 — the `MF-22` fixture settings
- [Food and drink worked example](../specs/2026-08-28-carb3-site-energy-system-worked-example-food-drink.md)
- [PyPSA/linopy #248](https://github.com/PyPSA/linopy/issues/248) — sparsity and masking
- `docs/notes/data/` — read 2026-09-19

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Outside Review | Claude subagent (Codex `model_unusable`) | Independent 2nd opinion | 1 | completed | 6 findings, 2 P0, all verified independently |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | clean | 16 issues, 0 critical gaps remaining |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | not applicable, no UI |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**OUTSIDE COVERAGE:** provider `codex`, status **unavailable** — the preflight returned
`model_unusable` (`gpt-6-astra` is not supported on a ChatGPT account; fix with
`GSTACK_CODEX_MODEL=<supported-model>`). A native Claude subagent ran the fallback and
completed. Same harness, so model identity is unknown and its agreement is weaker evidence
than a true outside model; every load-bearing claim it made was re-verified against the
reference CSVs before being acted on, and one claim (`premise_connection` not being a §3
entity — it is §3.1.3) was rejected as wrong, with three row counts corrected.

**CROSS-MODEL:** no tension. The outside voice did not disagree with the native review; it
found two P0 defects the native review missed, both of which were errors in the plan's own
§2.2 and §6.1 rather than contested judgements. Verified and accepted.

**VERDICT:** ENG CLEARED — plan reworked, 16 findings folded, ready to implement.

NO UNRESOLVED DECISIONS
