# COMIT — Discussion Notes

Working notes captured while exploring the COMIT model and its input data.
These are informal, evolving notes (not the official documentation — see
`docs/COMIT Documentation and Technical Guide.pdf` for that).

Source input file under discussion: `data_template_archive/comit_input_1_4_0_public_updated.xlsx`
(public version, v1.4.0 — contains artificial/placeholder figures).

## Index

| Doc | Topic |
|-----|-------|
| [01_input_data_overview.md](01_input_data_overview.md) | High-level tour of the 66-sheet input workbook and its five sections |
| [02_site_data.md](02_site_data.md) | Where site information comes from; point vs non-point sources; aggregation logic |
| [03_clusters_and_sectors.md](03_clusters_and_sectors.md) | The 10 active clusters, 16 modelled sectors (18→16 merges), and point-source site counts |
| [04_site_energy_estimation.md](04_site_energy_estimation.md) | How a site's current energy use (gas / electricity / non-metered) is back-derived from emissions + ECUK/DUKES |
| [05_paper_walkthrough.md](05_paper_walkthrough.md) | Cell-by-cell spreadsheet walkthrough of the Paper example — which sheets, filters, and commodity codes to use |
| [06_inputting_measured_site_energy.md](06_inputting_measured_site_energy.md) | How to feed measured site energy (electricity/gas/coal) into the model; the homogeneous-sites assumption and five input approaches, incl. per-site fuel-mix options |
| [07_high_level_testing_strategy.md](07_high_level_testing_strategy.md) | Validating whole-model behaviour (not per-method units): post-solve invariants, table snapshots, metamorphic tests, a hand-checkable mini scenario, and property-based testing with hedgehog (R) / Hypothesis (Python) |
| [08_python_redesign_approach.md](08_python_redesign_approach.md) | If COMIT were rebuilt in Python: linopy + xarray + pandera architecture, parallel-run migration with per-constraint parity checks, and a runnable mini-scenario proof-of-concept ([examples/comit_mini_linopy.py](examples/comit_mini_linopy.py)) |
| [09_objective_function.md](09_objective_function.md) | Plain-language explanation of what the model minimises: the eight configurable cost terms, discounting at 3.5%, capex as annuitised loans truncated at the horizon, traded/untraded carbon prices, and which sheets/code files each number comes from |
| [10_site_level_pathways.md](10_site_level_pathways.md) | Why same-sector sites start as emissions-share-scaled copies, yet can take different least-cost pathways through eligibility, infrastructure, grid-headroom, and known-change constraints |
| [11_sector_coverage_and_carb3_mapping.md](11_sector_coverage_and_carb3_mapping.md) | The 16 modelled sectors (+ Hydrogen pseudo-sector), the NAEI→COMIT sector folds, a COMIT↔CaRB3 (DESNZ NDBS) activity mapping, and the coverage gaps — waste, water, mining — that are candidates for new sector archetypes |
| [12_output_data_schema.md](12_output_data_schema.md) | Schema of what a model run produces: the output zip, 11 sheets, field-by-field types/domains/nullability for all six data tables, a worked single-site example, verified post-solve invariants, and the `Definitions` / `Energy`-vs-`Emissions` traps |
| [13_emissions_calculation.md](13_emissions_calculation.md) | Plain-language walkthrough of how emissions are calculated: NAEI site emissions as input weights, the per-technology `get_emissions()` engine and its five switches (gas/source/capture/location/biomass), where emissions bite (carbon cost + national cap), the post-solve site-level tables, and why per-site emissions are emergent rather than tracked |
| [14_emissions_source_split.md](14_emissions_source_split.md) | Splitting emissions into process chemistry vs energy combustion: the 3 process pseudo-commodities, an a-priori classification of all 397 technologies ([data/](data/emissions_source_classification.csv)), the kt/TWh detector, and what is hardcoded vs workbook-driven |
| [15_carb3_process_comparison.md](15_carb3_process_comparison.md) | How the CaRB3 Factory activity/process/equipment taxonomy compares with COMIT's sector/service/fuel-variant one: they decompose industry on orthogonal axes — coverage of all 55 activities ([crosswalk](data/carb3_comit_crosswalk.csv)), and the 37 CaRB3 processes with no COMIT analogue |

## Specifications

Design documents live in [`../specs/`](../specs/).

| Doc | Topic |
|-----|-------|
| [2026-08-19-carb3-site-decarbonisation-vision.md](../specs/2026-08-19-carb3-site-decarbonisation-vision.md) | **High-level plan.** Driving a modified COMIT from a CaRB3 building-stock register to assess per-premise decarbonisation across GB: why COMIT is the base, the three assumptions that block the route, the ten design decisions, and what is lost by solving each site independently |
| [2026-08-19-carb3-site-decarbonisation-implementation.md](../specs/2026-08-19-carb3-site-decarbonisation-implementation.md) | **Detailed plan, language-agnostic** (implementable in R or Python). Data model, algorithms A1–A9 as pseudocode, the optimisation stated mathematically, constraint disposition, emissions rules, output schema, scale gates, and validation. The worked example lives in its own document |
| [2026-08-19-carb3-site-decarbonisation-worked-example.md](../specs/2026-08-19-carb3-site-decarbonisation-worked-example.md) | **Worked example.** One cement premise carried end to end through A1–A9 with every input entity populated, plus the same premise re-run without site intelligence to show what the optional inputs contribute |
| [2026-08-05-site-heterogeneity-prd.md](../specs/2026-08-05-site-heterogeneity-prd.md) | ⚠️ **Superseded** by the three above. Site-level baselines, plans and pathways (F0–F6) specced against the current coupled model |

## Conventions
- Units (from the workbook `Contents` sheet): energy/capacity in **PJ** (GW for CHP),
  emissions in **kt/Mt CO₂e**, cost in **£m**, distance in **km**, prices based to **2021**.
- Code references point to functions in the `R/` directory of this package.
