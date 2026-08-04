# A high-level testing strategy for COMIT

**Question this note answers:** how do we validate that the *model as a whole* behaves as expected — not that every function is individually correct, but that the overall approach (read inputs → build constraints → optimise → produce tables) gives answers we can trust? And what is the R equivalent of Python's Hypothesis for this kind of testing?

---

## 1. What the test suite validates today (and what it doesn't)

The existing suite (`tests/testthat/`) is stronger than it may look, but its coverage is concentrated at two levels:

| Level | What exists | Where |
|---|---|---|
| Constraint construction | Unit tests that individual constraint matrices have the right shape, types, and values | `test-fct_constraints*.R`, `test-fct_combining_constraints.R` |
| Solver plumbing | Two textbook problems with known optima — a diet LP (objective 90) and a steel-production MILP (objective 8495) — solved through `comit_problem_solver()` | `test-comit_solver.R:134-272` |
| Whole-model regression | A single golden number: the objective value of the reference input must round to 105,827 | `test-comit_solver.R:278-288` |

What this means in practice: we know the solver machinery solves LPs correctly, and we know the *total cost* of the reference run hasn't drifted. We do **not** currently know:

- whether the solution *satisfies the constraints we think we built* (a bug that builds a wrong-but-feasible constraint matrix changes the answer without failing anything except, sometimes, the golden number);
- whether the output tables respect basic physical accounting (energy balance, non-negative capacities, emissions within caps);
- whether the model responds in the right *direction* to input changes (a tighter carbon cap should never make the transition cheaper);
- whether any of this holds for inputs other than the one reference workbook.

The golden number is also fragile in the wrong way: it fails on every intentional change (so it gets updated ritually) and stays silent on compensating errors that cancel out in the total.

The strategy below adds four layers, ordered by value-for-effort. None of them tests individual methods — they all treat the model as a black box or near-black-box, which is exactly the "validate the whole approach" goal.

---

## 2. Layer 1 — Post-solve invariant checks ("laws of physics")

The cheapest high-value addition. The test suite already performs one full solve of the reference input (`test-comit_solver.R:3` builds `solved_data` from the fixtures in `setup.R`). Every one of the following can be asserted on that *existing* solved object, adding seconds — not minutes — to the suite:

**Mathematical invariants (catch solver-interface bugs):**

- **The solution satisfies every constraint row.** We built `constraints$matr`, `constraints$directions`, `constraints$rhs` — so multiply them out and check them against the returned solution. This is the single most powerful test in this whole note: it verifies the *actual* solution against the *actual* constraint system, independently of the solver.

```r
test_that("the returned solution satisfies every constraint", {
  x <- solved_data$solution$solution
  lhs <- as.vector(slam::matprod_simple_triplet_matrix(
    constraints$matr, matrix(x, ncol = 1)))
  tol <- 1e-6
  ok <- ifelse(constraints$directions == '<=', lhs <= constraints$rhs + tol,
        ifelse(constraints$directions == '>=', lhs >= constraints$rhs - tol,
               abs(lhs - constraints$rhs) <= tol))
  expect_true(all(ok),
              info = paste("violated constraint rows:",
                           paste(head(which(!ok)), collapse = ', ')))
})
```

- **The objective value equals coefficients · solution** (guards against the solver being handed a different objective than we think).
- **Decision variables are non-negative** (they represent capacities and energy flows).

**Domain invariants (catch modelling bugs), asserted on the output tables from `create_tables()`:**

- No negative values in the Costs, Energy, Outputs (production), or Emissions tables.
- Total emissions per period ≤ the CO2 constraint trajectory for that period.
- Emissions captured ≤ emissions produced, per site and period.
- Production meets demand in every period (or exactly equals it, per the model's design).
- Aggregation consistency: cluster-level tables sum to the same totals as site-level tables (`Costs_cluster` vs `Costs`, etc.) — this checks the attribution logic end to end.
- Deployments respect `known_changes`: technologies forced in by that input sheet appear in the solution at the specified site and year.

Each of these is one `test_that` block over data frames — no new tooling, no extra solves. Together they turn every future full-solve test run into a behavioural audit.

## 3. Layer 2 — Golden-master on tables, not one number

Replace the single-objective golden number with snapshots of the key output tables, using testthat's built-in snapshot mechanism (third edition):

```r
test_that("reference-run output tables are unchanged", {
  tables <- create_tables(solved_data, raw_data, in_app = FALSE)
  # round to tolerance so solver noise across platforms doesn't churn snapshots
  expect_snapshot_value(round_tables(tables[c('Costs', 'Emissions', 'Energy')], 2),
                        style = "json2")
})
```

First run writes `tests/testthat/_snaps/…` files (committed to git); later runs diff against them, and `testthat::snapshot_review()` gives an accept/reject workflow when a change is intentional. This keeps the "did anything drift?" property of the current golden number but tells you *what* changed and *where*, and it catches compensating errors the total-cost scalar hides.

Keep the objective-value test too — it's a fast tripwire — but the snapshots are the real regression net.

## 4. Layer 3 — Metamorphic tests (directional behaviour)

You usually can't say what the optimal answer *is* for a realistic input, but you can say how it must *move* when the input changes. These "metamorphic relations" are the closest thing to validating the modelling approach itself:

| Perturbation of the reference input | Required relation |
|---|---|
| Tighten the CO2 cap (scale the emissions-constraint trajectory down) | Objective value (total discounted cost) is **non-decreasing** |
| Remove/relax a constraint (via `constraints_to_include`) | Objective value is **non-increasing** |
| Multiply *all* costs (capex, opex, fuel) by k | Objective scales by exactly k; the optimal deployment is unchanged |
| Multiply all demands by k (homogeneous scaling) | Energy and emissions tables scale ≈ k |
| Make one technology strictly dominant (near-zero cost, no cap) | It is deployed wherever eligible |
| Set optimism-bias factor to 1 vs its default > 1 | Objective is no higher than the baseline |

Each row is one extra full solve (~minutes), so these live behind the same `COMIT_RUN_SLOW_TESTS` environment-variable gate proposed in the headless-integration plan, run on demand or nightly rather than on every `devtools::test()`:

```r
test_that("a tighter carbon cap never lowers total cost", {
  skip_if(Sys.getenv("COMIT_RUN_SLOW_TESTS") == "")
  tighter <- raw_data
  tighter$Emissions$value <- tighter$Emissions$value * 0.8   # illustrative field
  expect_gte(solve_objective(tighter), solve_objective(raw_data))
})
```

Half a dozen of these relations, checked occasionally, give far more confidence in the *approach* than hundreds of unit tests — they exercise reading, constraint building, solving, and table creation together, against properties an energy-systems modeller would state independently of the code.

## 5. Layer 4 — A tiny hand-checkable scenario (the keystone fixture)

The highest-effort, highest-payoff item: a **minimal synthetic input workbook** — one or two sectors, two sites, two or three technologies, two or three timesteps — small enough that the least-cost answer can be computed by hand on paper.

Why it matters:

- It is the only test that validates the *entire* pipeline against ground truth (the textbook LP tests bypass reading and constraint construction; the reference-input tests have no known answer).
- It solves in **seconds**, not minutes — which is what makes the property-based testing in §6 feasible at the whole-model level.
- It doubles as executable documentation of what every input sheet means.

Notably, the repo already intended this: `tests/testthat/setup.R:46` points at `data_template_archive/input_template_for_testing.xlsx`, which is absent from the repo. Recreating it (from the reference workbook, stripped down) restores the original design intent. Concrete acceptance tests then look like: "with gas at cost X and hydrogen at cost Y and a cap that binds in 2035, the optimum switches site B to hydrogen in 2035 and total cost is Z."

---

## 6. Property-based testing: the Hypothesis question

### The R equivalent is `hedgehog`

The closest R analogue to Python's Hypothesis is **[hedgehog](https://cran.r-project.org/package=hedgehog)** (CRAN): composable random generators, properties as testthat tests, and automatic **shrinking** of failing cases to a minimal counterexample — the feature that makes Hypothesis useful rather than just a fuzzer. It plugs straight into the existing suite:

```r
library(hedgehog)

test_that("interpolation preserves endpoint values for any series", {
  forall(
    gen.and_then(gen.int(10), function(n)
      list(years  = gen.c(gen.element(2020:2050), of = n),
           values = gen.c(gen.unif(0, 1e6),      of = n))),
    function(years, values) {
      out <- interpolate_data(data.frame(year = years, value = values), timestep = 5)
      expect_true(all(!is.na(out$value)))
    })
})
```

(An older alternative, RevolutionAnalytics' `quickcheck`, is GitHub-only and not actively maintained — `hedgehog` is the practical choice.)

**The honest caveat:** property-based testing wants hundreds of executions per property. At several minutes per full COMIT solve, running Hypothesis-style generation against the full reference model is impractical no matter the language. The resolution is the split this note is built around:

- **Full model, few executions** → invariants, snapshots, metamorphic relations (§2–4).
- **Many executions, fast targets** → hedgehog on the pure data-transformation layers (`tidy()`, `interpolate_data()`, constraint builders: e.g. *for any generated Technologies table, the constraint matrix has one column per decision variable*), and on the **tiny scenario** from §5, where dozens of randomised cost/cap perturbations per property become affordable and every one of the §2 invariants can be asserted on each.

### Could it be done from Python instead? Yes — once the headless contract exists

The [headless-integration plan](../superpowers/plans/2026-08-04-comit-headless-integration.md) gives COMIT a CLI with parquet inputs/outputs. That makes a Python validation harness natural: Hypothesis generates perturbed input tables in pandas, writes them as a parquet input directory, runs the container, and asserts the §2 invariants on the output parquet:

```python
from hypothesis import given, settings, strategies as st

@settings(max_examples=20, deadline=None)   # each example is a real solve
@given(cost_scale=st.floats(0.5, 2.0))
def test_cost_scaling_scales_objective(cost_scale, base_inputs, run_comit):
    scaled = scale_costs(base_inputs, cost_scale)
    result = run_comit(scaled)              # subprocess → docker → parquet out
    assert result.objective == pytest.approx(cost_scale * BASELINE_OBJECTIVE, rel=1e-6)
```

Hypothesis is more mature than any R equivalent (better shrinking, a database of past failures, `stateful` testing), so if the surrounding architecture is Python anyway, putting the *whole-model* property harness in Python and keeping the *fast, fine-grained* properties in R/hedgehog is a defensible split. It is, however, dependent on the integration plan landing first — so the R-native layers (§2–4) are the right place to start regardless.

---

## 7. Suggested order of work

1. **Invariant suite on the existing solved fixture** (§2) — days of effort, immediate payoff, no new dependencies.
2. **Table snapshots replacing the lone golden number** (§3) — hours, testthat built-in.
3. **Tiny hand-checkable scenario workbook** (§5) — the missing `input_template_for_testing.xlsx`; unlocks everything else and restores the suite's original design intent.
4. **Metamorphic slow-test set** (§4) — behind `COMIT_RUN_SLOW_TESTS`, run nightly/on demand.
5. **hedgehog properties** on fast layers and the tiny scenario (§6).
6. **Optional, later:** Python/Hypothesis whole-model harness on top of the headless CLI once the integration plan is implemented.

Layers 1–3 alone would move COMIT from "the total cost hasn't changed" to "every solve is checked against the constraint system, physical accounting, and a known-good baseline" — which is the substance of validating that the model behaves as expected.
