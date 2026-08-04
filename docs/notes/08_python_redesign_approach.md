# Redesigning COMIT in Python — recommended approach

**Question this note answers:** if COMIT were rebuilt from scratch in Python, what should the design look like, which libraries fit, and — most importantly — how do you execute a rewrite without ending up with a model that gives *slightly different answers* and no way to know which is right?

A runnable proof-of-concept accompanies this note: [`examples/comit_mini_linopy.py`](examples/comit_mini_linopy.py) rebuilds the "mini scenario" from the [testing-strategy note](07_high_level_testing_strategy.md) in ~120 lines of linopy and reproduces a hand-computed optimum exactly.

---

## 1. The prerequisite, before any Python is written

A rewrite's dominant risk is silent divergence: a Python model that is plausible, runs, and disagrees with the R model by 3% for reasons nobody can locate. Two pieces of already-planned work are the antidote, and they are prerequisites rather than nice-to-haves:

1. **The format-neutral data contract** from the [headless-integration plan](../superpowers/plans/2026-08-04-comit-headless-integration.md) — the canonical input/output tables as parquet plus schema. Both models read and write the same artefacts, so "same inputs" is guaranteed by construction, not by careful copying.
2. **The acceptance harness** from the [testing-strategy note](07_high_level_testing_strategy.md) — golden-master output tables from the R model, post-solve invariants, metamorphic relations, and the tiny hand-checkable scenario. This *is* the rewrite's definition of done: the Python model passes the same harness the R model passes.

Implement at least the contract and the golden masters first. They de-risk the rewrite, and if the rewrite is later abandoned, none of that work is wasted — it serves the wrap-and-integrate path equally.

## 2. What the redesign should change (and why)

The R codebase's core maintenance burden is not R itself — it is that the optimisation problem is **hand-assembled**. Twenty-plus `fct_constraints_*.R` files build sparse `slam` triplet matrices row by row, with decision variables tracked by integer index in data frames. Every new constraint is bookkeeping code, and a wrong-but-feasible matrix changes answers without failing loudly (which is why the testing note leans so hard on "verify A·x against the constraint system").

The single biggest win of a Python redesign is replacing that layer with an **algebraic modelling framework**, where constraints are stated mathematically and matrix assembly is the framework's job:

| Option | Verdict |
|---|---|
| **linopy** | **Recommended.** xarray-based, built for energy-system models (PyPSA's backbone), variables dimensioned naturally over site × tech × year, first-class HiGHS support — the same solver COMIT uses today, so parity comparisons are apples-to-apples. |
| Pyomo | The mature general-purpose alternative. More flexible, more verbose, slower model build on large problems. Choose it if the model ever needs constraint types linopy can't express. |
| CVXPY / gurobipy | CVXPY targets convex problems generally; gurobipy ties you to a commercial solver. Neither fits better than linopy here. |
| **PyPSA / Calliope** (frameworks, not libraries) | **Evaluate before writing anything.** COMIT — site-level industrial capacity expansion with fuel switching, CCS, and emissions caps — is close to what these already do; a spike might show 70% of COMIT is *configuration* rather than code. If the chain-sector / process-site logic (notes 04–06) can't be expressed cleanly, drop down to linopy. The cheapest code is code not written. |

The difference in practice: a constraint becomes

```python
m.add_constraints((production * emission_factor).sum(["site", "tech"]) <= co2_cap,
                  name="co2_cap")
```

instead of a hundred lines of index arithmetic — which also makes the model auditable by domain experts who are not programmers. The proof-of-concept shows the full shape: variables, capacity accounting, demand satisfaction, an emissions cap that forces fuel switching, and post-solve invariant assertions, in one readable file.

## 3. Target architecture

Boring and layered — deliberately the same shape the headless-integration plan pushes the R code toward, so the rewrite lands where the wrapper was already heading:

```
adapters          Excel import / parquet / cloud APIs
                  │   validated against the schema (pandera)
                  ▼
canonical inputs  xarray Datasets for dimensioned data,
                  pydantic model for model_parameters
                  ▼
model core        pure: inputs → linopy model → solution
                  (no I/O, no UI, no printing)
                  ▼
post-processing   Costs / Energy / Emissions tables + run manifest
                  ▼
interfaces        CLI · Python API · (UI later if needed)
```

Concrete choices: **pandera** for table-schema validation (the `validate_inputs()` idea as a first-class library), **pydantic** for parameters, **xarray** so dimensioned data flows straight into linopy, **parquet** as the native format with Excel demoted to one import adapter. The Shiny app is not ported on day one — parquet outputs plus notebooks cover analysis, and a thin Streamlit front end can be added later if the upload-a-workbook workflow is genuinely needed.

## 4. Execution: parallel run, not big bang

1. **Port the mini scenario first.** The proof-of-concept is the seed: the tiny workbook solving in Python with a handful of constraints proves the whole pipeline shape in days.
2. **Grow constraint by constraint, with parity checks as you go.** COMIT has a built-in gift here: the `constraints_to_include` input sheet toggles constraints on and off. For each constraint ported, run *both* models with only the so-far-ported set enabled and compare objective values and key tables within tolerance. Divergence is caught the week it is introduced, not at the end of the project.
3. **Full parity gate at the end:** the reference workbook through both models; golden-master tables matching within tolerance; the metamorphic relations (tighter CO2 cap ⇒ cost non-decreasing, cost scaling ⇒ objective scaling) holding on both. Only then does the R model become the frozen fallback.

One caution surfaced by the proof-of-concept itself: LP optima can be **degenerate** — in the mini scenario both the per-site split of gas and the timing of the electric build are cost-equivalent, so the two models may legitimately disagree on *those* while agreeing on totals and objective. Parity tolerances should therefore be defined on the quantities that are unique (objective value, totals, binding-constraint activity), not on every cell of every table.

## 5. Trade-offs, honestly

- **Cost:** months of focused work to full parity, and the constraint-porting phase needs whoever does it to understand the *modelling intent*, not just the R code — several constraint files encode undocumented domain decisions. Capture them as notes while porting (extending this `docs/notes/` series), or the knowledge stays locked in R.
- **The alternative is real:** keeping the R core and integrating via the headless contract (PR #4) costs a fraction as much. If the model were feature-frozen, wrapping would be the end of it.
- **When the rewrite earns its price:** the maintaining team is Python-native; the model must keep evolving (new constraint types, tighter coupling with other Python models); or the hand-rolled matrix layer is actively slowing changes. In an architecture where the surrounding models and data pipelines are Python, those conditions largely hold — which makes the rewrite defensible, *sequenced after* the contract and harness exist, because that work de-risks both paths and is wasted in neither.

## 6. Running the proof-of-concept

```bash
pip install linopy highspy xarray pandas
python docs/notes/examples/comit_mini_linopy.py
```

Expected: HiGHS reports an optimal objective of **1425.0**, gas production capped at 7.5 PJ in 2035 with electric boilers (not hydrogen) filling the gap, and the script's hand-calculation and invariant assertions all pass.
