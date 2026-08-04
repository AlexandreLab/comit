"""Proof-of-concept: the COMIT "mini scenario" rebuilt with linopy.

A deliberately tiny capacity-expansion problem with the same *shape* as
COMIT — sites x technologies x years, least-cost objective, demand
satisfaction, capacity accounting, and a CO2 cap that tightens until it
forces fuel switching — small enough that the optimum is hand-checkable.

Hand-computed expectation (see docs/notes/08_python_redesign_approach.md):
  - 2025, 2030: all demand (15 PJ/y) met by existing gas boilers.
    Cost = 15 * 5 = 75 GBPm per year.
  - 2035: the CO2 cap (420 kt) limits gas to 420/56 = 7.5 PJ. The
    cheapest zero-carbon option is the electric boiler
    (150 capex + 15 fuel = 165/PJ vs hydrogen 200 + 12 = 212/PJ),
    so 7.5 PJ of electric capacity is built and used.
    Cost = 7.5*5 (gas fuel) + 7.5*150 (capex) + 7.5*15 (fuel) = 1275.
  - Total objective = 75 + 75 + 1275 = 1425 GBPm.

Note on degeneracy: the CO2 cap is economy-wide, so *which site* keeps
its gas share is arbitrary — totals are unique, per-site splits are not.
This mirrors COMIT's homogeneous-sites behaviour (docs/notes/06).
Likewise, with no discounting the *timing* of the electric build is
cost-equivalent anywhere before 2035, so the solver may build early;
only the total built (7.5 PJ) is unique. Real COMIT discounts costs,
which breaks this tie.

Run:  pip install linopy highspy xarray pandas
      python comit_mini_linopy.py
"""

import linopy
import pandas as pd
import xarray as xr

# --- Input data (in COMIT these tables come from the input workbook) -------

SITES = ["site_A", "site_B"]
TECHS = ["GAS", "ELC", "H2"]
YEARS = [2025, 2030, 2035]

coords_sty = {"site": SITES, "tech": TECHS, "year": YEARS}

# Heat demand per site, PJ per year (constant across the horizon)
demand = xr.DataArray(
    [[10.0] * 3, [5.0] * 3], coords={"site": SITES, "year": YEARS}
)

# Technology parameters: capex GBPm per PJ of capacity, fuel/opex GBPm per
# PJ produced, emission factor ktCO2 per PJ produced
tech_params = pd.DataFrame(
    {
        "capex": [100.0, 150.0, 200.0],
        "fuel_cost": [5.0, 15.0, 12.0],
        "emission_factor": [56.0, 0.0, 0.0],
    },
    index=pd.Index(TECHS, name="tech"),
)
capex = xr.DataArray(tech_params["capex"])
fuel_cost = xr.DataArray(tech_params["fuel_cost"])
emission_factor = xr.DataArray(tech_params["emission_factor"])

# Existing capacity in the start year: gas boilers sized to demand
existing_capacity = xr.zeros_like(
    xr.DataArray(coords={"site": SITES, "tech": TECHS}, dims=["site", "tech"])
)
existing_capacity.loc[{"tech": "GAS"}] = [10.0, 5.0]

# Economy-wide CO2 cap, ktCO2 per year: slack, exactly binding, then forcing
co2_cap = xr.DataArray([900.0, 840.0, 420.0], coords={"year": YEARS})

# --- Model -----------------------------------------------------------------

m = linopy.Model()

build = m.add_variables(lower=0, coords=coords_sty, name="build")
production = m.add_variables(lower=0, coords=coords_sty, name="production")

# Capacity in year y = existing + everything built up to and including y
# (no retirements in the mini scenario; COMIT would subtract end-of-life here)
capacity = {
    y: existing_capacity + build.sel(year=[yy for yy in YEARS if yy <= y]).sum("year")
    for y in YEARS
}

# Demand must be met at every site in every year
m.add_constraints(
    production.sum("tech") >= demand, name="demand_satisfaction"
)

# Production cannot exceed capacity
for y in YEARS:
    m.add_constraints(
        production.sel(year=y) <= capacity[y], name=f"capacity_limit_{y}"
    )

# Economy-wide emissions cap per year
m.add_constraints(
    (production * emission_factor).sum(["site", "tech"]) <= co2_cap,
    name="co2_cap",
)

# Least-cost objective: capex on builds + fuel cost on production
m.add_objective((build * capex).sum() + (production * fuel_cost).sum())

m.solve(solver_name="highs")

# --- Results and invariant checks (testing-strategy note, section 2) -------

prod = production.solution
built = build.solution
emissions = (prod * emission_factor).sum(["site", "tech"])

print("\nProduction by tech and year (PJ):")
print(prod.sum("site").to_pandas().round(2))
print("\nCapacity built (PJ):")
print(built.sum("site").to_pandas().round(2))
print("\nEmissions vs cap (ktCO2):")
print(
    pd.DataFrame(
        {"emissions": emissions.to_pandas(), "cap": co2_cap.to_pandas()}
    ).round(1)
)
print(f"\nObjective (total cost, GBPm): {m.objective.value:.1f}")

assert abs(m.objective.value - 1425.0) < 1e-6, "objective differs from hand calc"
assert (prod.sum("tech") >= demand - 1e-6).all(), "demand not met"
assert (emissions <= co2_cap + 1e-6).all(), "CO2 cap violated"
assert (
    abs(prod.sel(tech="GAS", year=2035).sum("site") - 7.5) < 1e-6
), "gas in 2035 should be capped at 7.5 PJ"
assert built.sel(tech="H2").sum() < 1e-6, "hydrogen should not be built"
print("\nAll hand-calculation and invariant checks passed.")
