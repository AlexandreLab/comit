# CaRB3-Driven Per-Site Decarbonisation — Vision and Rationale

**Status:** Draft v1 for review
**Date:** 2026-08-19
**Scope:** Great Britain (England, Wales, Scotland) · CaRB3 **Factory class** only (55 activities)
**Detailed specification:** [2026-08-19-carb3-site-decarbonisation-implementation.md](2026-08-19-carb3-site-decarbonisation-implementation.md)
**Worked example:** [2026-08-19-carb3-site-decarbonisation-worked-example.md](2026-08-19-carb3-site-decarbonisation-worked-example.md)
**Supersedes:** [2026-08-05-site-heterogeneity-prd.md](2026-08-05-site-heterogeneity-prd.md)

**Related reading:** [notes/06](../notes/06_inputting_measured_site_energy.md) ·
[notes/08](../notes/08_python_redesign_approach.md) ·
[notes/09](../notes/09_objective_function.md) ·
[notes/11](../notes/11_sector_coverage_and_carb3_mapping.md) ·
[notes/12](../notes/12_output_data_schema.md) ·
[notes/13](../notes/13_emissions_calculation.md) ·
[notes/14](../notes/14_emissions_source_split.md) ·
[notes/15](../notes/15_carb3_process_comparison.md)

---

## 1. The question this answers

For **every industrial premise in Great Britain** — every premise whose CaRB3 activity
falls in the 55-activity **Factory class** — we want to answer:

> What would it cost this site to decarbonise, and what would it actually do — switch
> fuels, or switch the process itself?

Today COMIT answers a related but different question: *what is the least-cost
decarbonisation pathway for the UK's ~1,026 industrial point sources, given national
demand, shared infrastructure and a national emissions budget?* That is a national
planning question. This is a **site assessment** question, asked at building-stock scale.

The two differ in more than resolution. A national planner needs sites to compete for a
fixed demand and shared pipelines. A site assessor needs each site taken on its own
terms, with its own measured energy and its own options.

## 2. Where the inputs come from

A **CaRB3 building-stock model** sits upstream and produces one record per premise:

- its **CaRB3 activity** (one of the 55 Factory-class activities — see D1; premises
  outside the Factory class are out of scope)
- its **current energy consumption by vector** — electricity, gas, oil, coal, biomass
- its **location**
- its **physical throughput** in Mt/yr, for activities carrying mass-denominated
  processes (D5)
- optionally floorspace and building attributes
- optionally **site intelligence** where it exists (D10) — the actual process list and
  installed capacity, reported emissions, the operating schedule, measured load
  statistics, and the grid import/export capacity that two planned extensions will need

The full interface contract — what must be supplied, what must not, quality requirements
and rejection behaviour — is set out in
[implementation §1.6](2026-08-19-carb3-site-decarbonisation-implementation.md#16-what-the-building-stock-model-must-supply).

**Deriving that baseline is explicitly out of scope here.** How the stock model turns
floorspace, meter data or benchmarks into per-site energy is its own problem. This
design begins at the point where a validated per-site energy record exists.

That single assumption removes the hardest obstacle noted in
[note 11 §5.1](../notes/11_sector_coverage_and_carb3_mapping.md): COMIT's site sizing
depends on CO₂ point-source emissions, which most premises do not have. If energy
arrives directly, nothing needs to be inferred from emissions at all.

## 3. Why COMIT is the base

COMIT already owns the parts that are expensive to build and easy to get wrong:

| Asset | Where |
|---|---|
| An objective function with annuitised capex, fuel cost, carbon cost and infrastructure terms, all in present value | [note 09](../notes/09_objective_function.md) |
| An emissions engine that separates **combustion** emissions from **process chemistry** — including biomass zero-rating and CCS capture | [notes 13](../notes/13_emissions_calculation.md), [14](../notes/14_emissions_source_split.md) |
| A technology set whose variants differ **precisely by fuel** — 82 of 94 processes have variants differing only by `technology_category` | [note 15](../notes/15_carb3_process_comparison.md) |
| Decision variables already indexed **site × technology × year** | `R/fct_decision_variables.R` |
| A stable, documented output schema | [note 12](../notes/12_output_data_schema.md) |

Fuel switching is the primary decarbonisation lever, and COMIT's technology set is
organised around exactly that axis. Rebuilding this from scratch would be wasteful.

## 4. The three assumptions that block the route

### 4.1 Demand is derived, not given

```
R/fct_sites.R:113   scaling_factor_within_sector = total_MtCO2 / total_sector_emissions
R/fct_sites.R:173   demand = national_demand × scaling_factor_within_sector
```

Every site is a scaled-down copy of its sector's fleet, sized by its share of sector
emissions. The CaRB3 route supplies demand directly, so this entire mechanism is
bypassed — and with it the assumption that sites within a sector are homogeneous
([note 06](../notes/06_inputting_measured_site_energy.md)).

### 4.2 Scale

COMIT today: **1,026 sites → ~638,000 capacity variables**, roughly 30 technologies and
620 variables per site. That scales linearly. The GB Factory-class stock is orders of
magnitude larger than 1,026, so a single coupled optimisation is not reachable — and
[note 11 §5.2](../notes/11_sector_coverage_and_carb3_mapping.md) already flagged that
even 5,374 sites would strain the current MILP.

### 4.3 Process granularity

COMIT decomposes a sector into ~10 generic energy services plus product chains in six
sectors. CaRB3 decomposes an activity into **unit operations**. These are orthogonal
axes, not two resolutions of the same thing: of 76 distinct CaRB3 process names,
**37 have no COMIT analogue at all**, and 34 of the remaining 39 merely *collapse* into
a generic energy service ([note 15](../notes/15_carb3_process_comparison.md)).

## 5. The design

```
CaRB3 stock model              Modified COMIT                          Output
─────────────────              ──────────────                          ──────
premise record      ──►  1. expand: activity → process set      ──►  per-site pathway
 · CaRB3 activity        2. allocate site energy across processes     · technology per
 · energy by vector      3. build per-site optimisation                 process, per period
 · location              4. solve — independently, in parallel        · energy by vector
 · floorspace                                                          · emissions
                         scenario inputs, per site:                    · cost
                          · H₂ / CO₂ / grid availability
                          · carbon price, fuel prices          ──►  aggregate to GB,
                                                                     compare vs ECUK/GHGI
```

The essential move is in step 4. Because demand arrives exogenously, sites no longer
compete for a national total — so they **decouple**, and each becomes a small,
independent optimisation. Scaling becomes a matter of running more of them, not of
solving a bigger problem.

## 6. The eleven decisions

| # | Decision | What it buys | What it costs |
|---|---|---|---|
| **D1** | Full CaRB3 **Factory-class** stock — all 55 activities, every premise | Coverage of the whole industrial stock, not just the ~1,026 point sources | Rules out a single coupled optimisation; non-Factory premises (offices, retail, schools, warehouses) are excluded |
| **D2** | Per-site independent solves | Linear scaling; embarrassingly parallel; genuinely per-site answers | Removes national and cluster coupling entirely |
| **D3** | Full CaRB3 unit operations as processes | Process switching becomes a real lever, not just fuel switching | Replaces the process taxonomy; a large data build |
| **D4** | Baseline energy supplied upstream | Removes the emissions-proxy problem; real heterogeneity per site | Creates a hard dependency on the stock model's quality |
| **D5** | Hybrid denominators — energy by default, mass for chemistry | Most coefficients derivable from supplied energy; keeps process emissions physically grounded (kt CO₂ per Mt) | Two denominator conventions to keep straight |
| **D6** | Tiered cost provenance — reuse COMIT, then BREF/BAT, then proxy | Shrinks the data build far below the naive count; weak estimates visible not hidden | Mixed-confidence dataset needs careful reporting |
| **D7** | Infrastructure exogenous — H₂/CO₂ availability as scenario input | Simple, explicable; the assumption is owned and stated | **No infrastructure co-optimisation** — see §7 |
| **D8** | Great Britain scope | Keeps Grangemouth and Peterhead; matches expected stock coverage | Excludes Northern Ireland — 56 sites and the Londonderry cluster |
| **D9** | Supersedes the site-heterogeneity PRD | One direction, no conflicting roadmaps | Retires work already specced against the model that runs today |
| **D10** | Tiered site intelligence — known site detail replaces activity defaults | Real sites modelled as themselves wherever evidence exists; the model improves as intelligence accumulates, without redesign | Mixed-evidence results; every output must carry its evidence tier or the quality is invisible |
| **D11** | Existing plant has an age — it retires when its life ends, and early replacement pays the residual value | Replacement timing becomes an economic result instead of an artefact; near-new plant stops being scrapped for free | A vintage assumption for every premise with no age data, and one more parameter (λ) to defend |

### On D5 — why two denominators

COMIT's coefficients are all *per unit of output*, and that unit is either PJ (energy
services) or Mt (products). A unit operation like "Welding" has no obvious denominator.

Denominating everything in **PJ of useful energy** works for most processes and is
directly derivable from the energy the stock model supplies. But **process emissions are
kt CO₂ per tonne of material** — calcination CO₂ comes from the limestone, not the fire.
Expressing those per PJ would sever them from their physical basis and make them respond
to fuel efficiency, which is wrong.

So: energy denominators by default; physical mass for the ~20 processes that carry
process emissions. Those are concentrated in six sectors, all of which already have
mass-denominated product chains in COMIT today.

### On D10 — evidence tiers, not averages

D4 makes the stock model authoritative for what a premise consumes. D10 extends the same
logic to what a premise *is*. An activity is a classification, not a description: two
paper mills in one CaRB3 activity may run kraft and recycled-fibre lines sharing almost
no unit operations, and where that is known for a specific site, averaging it into an
activity default throws away the best information available.

So process detail is **tiered**, most specific first:

1. **Known site** — the site's actual process list, and where known its installed
   technology, capacity, operating schedule and measured load statistics. *When* that
   plant was commissioned is deliberately not here: vintage has its own parallel ladder
   under D11, resolved per technology rather than per premise, so a site can be D10 tier 1
   and D11 tier 3 at the same time.
2. **Named route** — the site is known to run one of several recognised routes for its
   activity, so that route's process set is used.
3. **Activity default** — no site-specific intelligence; the default set applies.

The same applies to emissions. Where a site reports under UK ETS or a permit, those
figures are better evidence than anything computed here, and are used to reconcile the
baseline and correct the combustion/process split. They cannot simply *replace* the
computed emissions — emissions must stay a function of the decision variables, or the
carbon price stops pricing the decision it exists to price. [Implementation
§7.6](2026-08-19-carb3-site-decarbonisation-implementation.md) sets out what is done
instead.

Two consequences worth stating plainly. First, the tiers are **exclusive, not blended** —
better evidence replaces weaker evidence outright, because a blend of a known site and an
average is a site that exists nowhere. Second, results become **mixed-evidence**, so every
output row carries the tier it was produced from. Without that, a national aggregate
silently mixes surveyed sites with defaulted ones and reads as uniformly reliable.

This also means the model gets better as intelligence accumulates, with no structural
change — new site knowledge is new rows, not a new design.

### On D11 — the asymmetry that made plant free to scrap

The model as specified before this decision had no notion of how old anything was. A
three-year-old furnace and a nineteen-year-old one were the same object: both could be
abandoned at no cost the moment something cheaper to run appeared. That is not a
calibration problem, it is a structural one, and it comes from a single asymmetry in the
objective.

**New capacity pays for its whole life.** Capex is financed as a level annuity over the
technology's lifetime, and those instalments are charged every period from the build year
to the end of life *whether or not the plant is still running*. **Incumbent capacity pays
nothing**, because it was built before the model starts and appears in no capex term at
all. So the model faced a real cost to build and no cost to scrap, and behaved
accordingly: it replaced plant whenever the fuel-and-carbon saving cleared the annuitised
capex of the replacement, with no reference to whether the incumbent was new.

Real operators do not do this, and the reason is not sentiment. The loan on a
three-year-old furnace does not disappear when the furnace does. D11 charges incumbent
plant the same unpaid balance a new build would owe — its residual value, straight-line in
remaining life — so that scrapping something new is expensive and scrapping something worn
out is nearly free. It is the same financing treatment COMIT already applies to new build,
applied consistently to plant that happens to predate the model's start year.

**Age comes from evidence, in three tiers, exactly as in D10.** Where the commissioning
year of a process is known, it is used. Where it is not but the premise's construction year
is, that bounds plant age from above — plant cannot predate the building — which is cheap,
already held in stock data, and decisive on young sites. Where neither exists, capacity is
assumed uniformly spread across every age from new to end-of-life.

**That third tier is what COMIT already does**, and this is the part worth pausing on.
COMIT decays existing capacity linearly to zero over one technology lifetime. That straight
line has always been the survival curve of a uniformly-aged fleet — it was a vintage
assumption all along, simply never named as one. D11 names it, makes it the fallback, and
lets better evidence displace it. A premise with no age data therefore **ages** exactly as
it does today. Switching the decision out entirely takes more than that — the charge set to
zero, the default tier in force, and early retirement disallowed — because giving plant the
ability to retire at all is itself a change. The implementation spec states the three
conditions together as the COMIT-equivalent configuration, and one validation test runs it.

**What it costs.** Most premises will sit in tier 3 for a long time, so most of the stock
is still ageing on an assumption — and it is now an assumption doing visible work on
replacement timing rather than sitting quietly inside a constraint. λ is a genuine
judgement, not a measurement. And life extension through major refurbishment is not
modelled at all, which makes heavily-refurbished plant retire earlier here than it will in
reality.

### On D7 — the deliberate simplification

For cement, steel and chemicals sites, CCS and hydrogen are *the* decarbonisation
levers, and whether a pipeline gets built depends on aggregate demand at a cluster.
A per-site solve cannot decide that. Under D7, availability becomes an input: *"hydrogen
is available at these clusters from 2030"*. Runs are repeated under alternative
scenarios and the spread is reported.

This is honest but consequential. The model does not tell you whether the infrastructure
is worth building — it tells you what happens to sites conditional on your assumption.
**The results for energy-intensive clustered sites are only as good as that assumption.**

### On the national emissions cap

Kept exogenous too, for consistency with D7. The carbon price is a scenario input, and
aggregate emissions are a **reported and compared** output rather than an enforced
constraint. An iterative carbon-price loop that hits a target cap is possible and is
documented in the implementation spec as an optional extension — but it reintroduces
exactly the coupling D2 removes, so it is not the default.

## 7. What is lost, stated plainly

Anyone reading results from this model needs to know these six things:

1. **No infrastructure co-optimisation.** Where H₂ and CO₂ pipelines get built is an
   input, not an output.
2. **No enforced national emissions budget.** Aggregate emissions are an outcome to be
   inspected, not a constraint that binds.
3. **Sector calibration is demoted from truth to check.** COMIT anchors fleets to
   ECUK/GHGI totals; here, site data is authoritative and sector totals become a
   validation comparison. This is a deliberate inversion of the superseded PRD's Goal 4.
4. **No parity with current COMIT.** Aggregate results will not reconcile with today's
   model runs, and parity is not a meaningful acceptance test. Agreement should only be
   assessed on the energy-intensive subset, with coupling disabled on both sides.
5. **Northern Ireland is excluded.** 56 sites and the Londonderry cluster drop out; the
   cluster list goes from 10 to 9. National totals are **GB**, not UK, and cannot be
   compared against UK GHGI without adjustment.
6. **Non-Factory premises are excluded.** Scope is the CaRB3 Factory class only (D1).
   Offices, retail, schools, hospitals and warehouses are not modelled, so results are
   an **industrial** total and not a non-domestic-stock total. Comparisons against ECUK
   must be taken on the industrial sub-total, not the whole service sector.

## 8. Relationship to existing work

**This supersedes** [2026-08-05-site-heterogeneity-prd.md](2026-08-05-site-heterogeneity-prd.md).
That PRD specified F0–F6 for making the *existing coupled model* site-heterogeneous,
with two goals this design inverts: sector calibration authoritative (its Goal 4) and
zero-impact default (its Goal 5). Those cannot be reconciled, so the coupled roadmap is
retired rather than merged.

The PRD is kept in the repository, not deleted. Its F0 (site data model, ingestion,
validation) and F2 (site process register) thinking informed the data model here, and
its problem statement remains the clearest description of why site heterogeneity matters.

**Language-agnostic by design.** The implementation spec is written so it can be built
in R or Python. [Note 08](../notes/08_python_redesign_approach.md) sets out a linopy +
xarray architecture for a COMIT rebuild; if that proceeds, this design should not need
rewriting. A per-site independent problem is, if anything, a better fit for that stack.

**Existing data assets reused:** the CaRB3 activity → process register comes from
[`notes/data/carb3_factory_processes.json`](../notes/data/carb3_factory_processes.json);
the activity → COMIT sector mapping from
[`notes/data/carb3_comit_crosswalk.csv`](../notes/data/carb3_comit_crosswalk.csv); the
existing technology structure from
[`notes/data/comit_sector_processes.csv`](../notes/data/comit_sector_processes.csv).

## 9. Phasing

| Phase | Content | What it proves |
|---|---|---|
| **1** | Input contract; per-site solve using **existing** COMIT technologies, 2–3 activities; plant ageing and the stranding charge (D11) | Decoupling works; the per-site problem solves; parallelism scales; replacement timing is economic rather than accidental |
| **2** | Infrastructure scenarios; GB aggregation and comparison against ECUK/GHGI | Aggregates are credible without coupling |
| **3** | Process taxonomy for the highest-energy activities — Cement, Iron & steel, Chemicals, Food & drink, Paper | Unit-operation modelling is tractable and the data obtainable |
| **4** | Remaining activities; full-stock run | Coverage |

**Phase 1 is deliberately shallow on process depth.** Prove the architecture before
committing to the technology data build (D3, D6), which is the expensive and hardest-to-
reverse part of the whole programme. If Phase 1 shows the per-site problem does not
scale, or that decoupled results are not credible, that is far cheaper to learn before
the data work than after.

## 10. Residual risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| **Activity → process energy profile** is the weakest link | The stock model supplies *total* site energy; a per-process model needs it split. That split is a benchmark assumption with little empirical grounding | Specified in [implementation §3.3](2026-08-19-carb3-site-decarbonisation-implementation.md): explicit evidence tiers, mandatory citation, optional low/high bands, and a systematic-error warning. Report per-process results with a sensitivity band |
| **Tier-3 proxy cost estimates** | A meaningful share of technologies will have proxy costs with no calibration anchor | Mandatory `provenance` and `confidence` fields; results filterable by confidence; proxies concentrated in low-energy activities |
| **Sensitivity to the infrastructure scenario (D7)** | Cement/steel/chemicals pathways may swing entirely on the assumption | Always run at least two bounding scenarios; never publish a single-scenario result for clustered sites |
| **Stock model quality (D4)** | Everything downstream inherits its errors, and this design has no independent check | Validation gate on ingestion; GB aggregate comparison against ECUK/GHGI as an outside check |
| **Plant vintage is assumed for most premises (D11)** | Replacement timing now depends on an age the model has usually guessed, and the guess drives both when plant must be replaced and what replacing it early costs | The default tier reproduces COMIT's existing survival curve, so the ageing assumption does not regress; `stranding_factor = 0` disables the economic half for an A/B (full pre-D11 equivalence needs the three conditions in implementation §5.4); every output row carries its vintage tier, so results can be split by how much rested on a real commissioning date |
| **No life extension through refurbishment (D11)** | Major overhauls genuinely extend plant life; the model has no way to represent one, so refurbished plant retires earlier here than in reality — biasing towards *more* replacement, not less | Recorded as a known gap in implementation §5.3.1; representing it needs a life-extension option competing against replacement in the technology set, which is a data build rather than a model change |
| **Scale may still not reach "every premise"** | Linear scaling is necessary but not sufficient — memory and orchestration also bind | Explicit scale gates at 10k / 100k / 1M premises in Phase 1, before the data build |
