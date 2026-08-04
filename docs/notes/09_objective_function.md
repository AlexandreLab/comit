# What COMIT is actually minimising — the objective function explained

**Question this note answers:** when COMIT "solves" and reports a least-cost pathway, what exactly is the cost it minimised? What is included, what do the finance terms (discounting, annuitised capex) mean, and where does each number come from in the input workbook?

Written for readers with basic energy and finance knowledge — no optimisation background needed.

---

## 1. The one-sentence version

COMIT considers every allowed combination of *which technologies to build, at which sites, in which years, and how much to run them*, and picks the combination that meets all the constraints (demand, emissions caps, build limits, …) at the **lowest total cost to the system over the whole model horizon**, where costs occurring in different years are converted to today's money so they can be added together fairly.

That total, converted-to-today's-money cost is the **objective function**. Formally it is a simple weighted sum:

```
minimise   c₁·x₁ + c₂·x₂ + … + cₙ·xₙ
```

where each `x` is one decision the model can make (see §2) and each `c` is the present-value cost of making one unit of that decision (see §3–4). All the financial sophistication lives inside the `c` coefficients — the optimisation itself just finds the cheapest feasible combination.

## 2. What the model gets to decide (the `x` variables)

For every site (or cluster), every eligible technology, and every model period, the model holds separate decision variables — you can see their names in the model internals, formatted like `used_capacity_IPPBOINGA01(2030,site_123)`:

| Decision | Plain meaning |
|---|---|
| `new_capacity` | How much of this technology to **build** at this site in this period (PJ of capacity) |
| `used_capacity` | How much of the installed capacity to actually **run** in this period |
| `available` capacity | How much remains installed and ready to use |
| Hydrogen transport choices | Whether a site gets its hydrogen by pipeline, trucking, or grid connection |
| CO₂ transport | Capacity of CO₂ pipes from sites to clusters and onward to storage |
| `non_industry_H2` | Hydrogen produced for users outside industry (it shares the same infrastructure) |

One refinement: if the input parameter for minimum hydrogen plant size is set above zero, the model also gets yes/no (binary) variables for whether each hydrogen plant exists at all, which turns the problem from a pure linear programme (LP) into a mixed-integer one (MILP) — same objective, slightly harder to solve.

## 3. The eight cost components

The costs included are **configurable in the input workbook**: the `objective_function` sheet lists eight terms with an include/exclude flag. In the public reference workbook all eight are switched on:

| Term | What it prices, in plain terms |
|---|---|
| `PV_technology_capex` | The investment cost of building new equipment — boilers, furnaces, CCS units, hydrogen plants (see §4 for how it's financed) |
| `PV_fixed_opex` | The fixed annual running costs of equipment you've installed — staffing, maintenance — paid whether or not you run it |
| `PV_fuel_cost` | The fuel bill: every unit of activity consumes fuel (gas, electricity, hydrogen, biomass…) priced per commodity per year from the `Fuel_costs` sheet |
| `PV_carbon_cost` | The carbon bill: emissions that still occur are charged at the carbon price from the `Carbon_price` sheet |
| `PV_CO2_national_transport` | National-scale CO₂ transport and storage infrastructure (getting captured CO₂ from clusters to storage) |
| `PV_CO2_pipe_cluster_to_site` | The local CO₂ pipework connecting an individual site to its cluster network |
| `PV_H2_pipe_national` | The national hydrogen pipeline backbone |
| `PV_H2_pipe_cluster_to_site` | The local hydrogen pipework connecting a site to its cluster |

Each term has its own calculation file in the code (`R/fct_pv_*.R`), and their results are summed into a single cost coefficient per decision variable (`R/fct_pv_sum_coefficients.R`). The "PV" prefix means *present value* — every term is expressed in today's money, which is what makes them addable.

Because the terms are individually switchable, you can run the model with, say, carbon costs excluded to see how much the carbon price alone is driving the answer — the same trick the `constraints_to_include` sheet offers on the constraints side.

Some details worth knowing inside these terms:

- **Fuel quantities** come from the `technology_input_output` sheet: each technology has coefficients saying how much of each commodity it consumes per unit of activity.
- **Electricity generated on site** (commodity `ELCGEN`, e.g. from CHP) is priced at the same rate as grid-purchased industrial electricity (`INDDISTELC`), so the model doesn't treat self-generated power as free.
- **Retrofits pay the difference.** A retrofit technology (e.g. adding CCS to an existing plant) is charged its own costs *minus* the costs of the base technology it replaces, so the model sees the true incremental cost of retrofitting rather than double-counting.
- **Two carbon prices.** Emissions at sites in the emissions trading scheme are charged the *traded* carbon price; emissions elsewhere get the *untraded* price; non-CO₂ greenhouse gases are always charged as untraded. Both price trajectories come from the `Carbon_price` sheet.

## 4. The finance: how money in 2045 is compared with money in 2025

Two financial mechanisms shape every coefficient. Both use rates from the workbook's `rates` sheet — in the public workbook, **3.5% for both**, with prices in **2021 £m**. (3.5% is the standard UK Treasury "Green Book" discount rate for appraising public projects, which is a good clue to the model's perspective: it evaluates cost to society, not to an individual firm.)

**Discounting.** A pound spent in the future counts for less than a pound spent today. Each future cost is divided by (1 + 3.5%) once for every year between the model start and the year the cost occurs:

> £100 spent in 2035, viewed from 2025: £100 ÷ 1.035¹⁰ ≈ **£70.9**

This is why the model doesn't treat "£1bn now" and "£1bn in twenty years" as equally painful — deferring cost is genuinely rewarded, exactly as in a standard investment appraisal.

**Capex as a loan, not a lump sum.** When the model builds equipment, it does not pay the full investment cost up front. Instead the cost is spread over the technology's lifetime as equal annual instalments — like a fixed-rate mortgage — using the standard annuity formula (`PMT()` in `R/fct_finance.R`):

> Equipment costing £1,000/PJ with a 25-year lifetime at 3.5% interest → **≈ £60.7 per year for 25 years**

Two consequences follow:

1. Each instalment is then discounted from the year it's paid, like every other cost.
2. **Instalments beyond the model's end year are never paid.** A plant built in 2048 with a 25-year lifetime only pays the instalments that fall before `end_year` (2050, say) — the model horizon truncates the loan. This deliberately avoids punishing late-horizon investment for costs that fall outside the assessed period (though it also means late builds look somewhat cheaper per unit of service than early ones — a standard end-of-horizon effect to keep in mind when interpreting late-period results).

One subtlety: the workbook carries **two separate rates** — an *interest* rate (used to size the loan instalments) and a *discount* rate (used to convert future payments to present value). They happen to both be 3.5% in the public workbook, but they answer different questions ("what does borrowing cost?" vs "how much do we care about the future?") and can be set independently.

Finally, because the model often runs in 5-year steps, annual costs (fuel, carbon, opex) within a step are treated as paid **each year of the step** and discounted year by year — a 2030 model period with a 5-year timestep charges 2030-through-2034's discounted payments, not a single payment.

## 5. Where everything comes from

| Piece | Input workbook sheet | Code |
|---|---|---|
| Which cost terms are on | `objective_function` (include flags) | `get_pv_functions()` in `R/fct_pv_generic_functions.R` |
| Interest & discount rates, price base year | `rates` | `R/fct_finance.R` (`PMT()`, `present_value()`) |
| Investment costs, lifetimes, retrofit links | `Technologies` (capex, lifetime, `retrofit_to`) | `R/fct_pv_technology_capex.R` |
| Fixed running costs | `Technologies` | `R/fct_pv_fixed_opex.R` |
| Fuel prices per commodity per year | `Fuel_costs` | `R/fct_pv_fuel.R` |
| Fuel use per technology | `technology_input_output` | `R/fct_pv_fuel.R` |
| Carbon price trajectories (traded/untraded) | `Carbon_price` | `R/fct_pv_carbon_cost.R` |
| CO₂/H₂ infrastructure costs | infrastructure cost sheets | `R/fct_pv_co2.R`, `R/fct_pv_h2.R` |
| Assembly into one coefficient per variable | — | `comit_objective_function()` in `R/comit_solver.R`, `R/fct_pv_sum_coefficients.R` |

## 6. Implications worth remembering

- **"Least cost" means least *discounted system* cost.** The model is not maximising any firm's profit, and a pathway that looks expensive in 2045 nominal pounds can still win if its discounted total is lowest.
- **The optimum can be a tie.** Sites with identical per-unit costs under a shared constraint can swap roles at no cost difference, so *which* of two identical sites decarbonises first may be an arbitrary choice by the solver, not a finding — see the degeneracy discussion in [08_python_redesign_approach.md](08_python_redesign_approach.md).
- **The objective is auditable from the outputs.** Every cost the model counted appears in the output Costs tables; summing them (with discounting) reproduces the objective value — which is also the basis of the whole-model checks proposed in [07_high_level_testing_strategy.md](07_high_level_testing_strategy.md).
