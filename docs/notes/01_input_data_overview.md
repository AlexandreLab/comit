# Input Data Overview

The COMIT input is a single Excel workbook
(`data_template_archive/comit_input_1_4_0_public_updated.xlsx`) with **66 sheets**
that together fully specify one model run: every control, constraint, assumption
and dataset the optimiser needs. The model reads it via `read_excel_data_template()`.

> ⚠️ **This is the public version.** The `Title` sheet warns that sensitive
> figures have been replaced with *artificial numbers*. Running it as-is produces
> results that "should not be used for any inference — they will be completely
> inaccurate." The public file exists so the model runs end-to-end; real
> assumptions must be substituted. The input file version must match the
> installed package version (both **1.4.0** here).

## What the model does
COMIT is a linear-programming (cost-optimisation) model of UK industry. It finds
the **least-cost pathway** to meet exogenous industrial commodity demand. The
objective it minimises includes technology capex, technology opex, carbon cost,
and CO₂ transport & storage plus hydrogen infrastructure costs.

## Structure — five sections
Sheets are grouped by `==>` divider tabs. The workbook's own `Contents` sheet
documents each one.

### 1. Parameters — the run's control panel
- `model_parameters_a` (numeric): start year **2021**, end year **2051**,
  **5-year** timestep, price base year, capex "optimism adjustment" multipliers.
- `model_parameters_b` (boolean toggles): e.g. `model_H2_production`,
  `run_counterfactual`, `include_site_closures`, `use_retrofit`, `Use_IDBR`,
  `Two_nps_sites`, `Traded_share_calc`.
- `model_parameters_c` (text): e.g. `headroom_scenario` for the electricity
  capacity constraint.
- `objective_function`: which cost components to include (can switch carbon cost off).
- `constraints_to_include`: master on/off list for which constraints bind.

### 2. Constraints — the feasibility envelope
- **Demand**: `Demand_drivers` (annual national demand per commodity).
- **Capacity**: `maximum_capacity`, `minimum_capacity`, `tech_stability`
  (limits switching away from incumbents), `supply_chain_constraints` (rollout
  rate per period).
- **Fuel**: `max_fuel_constraints`, `min_fuel_constraints`, `max_fuel_share`.
- **Hydrogen**: `H2_availability`, `Non_industry_H2_demand`, `H2_grid_start`,
  `H2_plant_size`.
- **CO₂/CCS**: `Non_industry_CO2_demand`, `max_CCS`, `CO2_storage` (offshore
  injection limits), `emissions_limit` (total CO₂e cap).
- **Grid/other**: `headroom_constraints` (electricity available per site/cluster),
  `counterfactual_rollout` (fixed deployment path for counterfactual mode).

### 3. Assumptions — techno-economic data
- `Technologies`, `technology_input_output` (each technology's inputs→outputs),
  `commodities` (names, fuel category, CO₂ factors).
- Efficiency: `resource_efficiency`, `energy_efficiency`.
- Costs/factors: `Carbon_price`, `Fuel_costs` (£m per unit, 2019/2021 prices),
  `Fuel_emissions`, `rates` (discount + borrowing rates).
- Infrastructure: `cluster_radius`, `H2_transport_cost`, `CO2_transport_cost`,
  `CO2_T&S_cost`, `Pipes_lifetime`, `sector_max_H2_CO2`.

### 4. Data — spatial / site-level backbone
Covered in detail in [02_site_data.md](02_site_data.md). Includes NAEI site data,
ONS/IDBR-derived non-point sources, sector/location mappings, cluster geography,
and emissions baselines (`Emissions`, `traded_share`, `ghg_splits`, `gdp_deflators`).

### 5. Attribution — post-run calculations
`attribution_parameters`, `CCS_BECCS_split` (used in post-model attribution).

## Mental model
Three stacked layers:
1. **Controls** (Parameters) — *how* to run the model.
2. **Rules** (Constraints) — the *boundaries* of valid solutions.
3. **Facts** (Assumptions + Data) — the *numbers and geography* it optimises over.

The model reads all of this, builds the objective function and constraint matrix,
and solves for the cheapest technology-deployment pathway that meets demand within
every constraint.
