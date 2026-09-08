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
| [16_input_data_readiness.md](16_input_data_readiness.md) | **Input-data audit.** For every input the per-site model reads: does a schema exist, does data exist, and who supplies it. Finds three gaps — no duty family and no heat grade on any of the 376 processes, and no default on-site generation anywhere — plus the reason `archetype_id` has no defining entity. Tasks T17–T19 |

## Specifications

Design documents live in [`../specs/`](../specs/). The five documents there are
self-contained; superseded and frozen material is in
[`../specs/archive/`](../specs/archive/README.md) and is not required reading.

### The live specification

| Doc | Topic |
|-----|-------|
| [2026-08-28-carb3-site-energy-system-overview.md](../specs/2026-08-28-carb3-site-energy-system-overview.md) | **Start here.** What the system is, the three capabilities it exists to provide, the two programme decisions `PD1`–`PD2`, and where the boundaries are |
| [2026-08-28-carb3-site-energy-system-implementation.md](../specs/2026-08-28-carb3-site-energy-system-implementation.md) | **The specification itself — partial.** §1 scope, conventions and the twelve design decisions `D1`–`D12`; §2 system overview; §3 data model (22 entities); §4 algorithms A1–A9 with the carrier-mix rule and the relaxation ladder; §5 the optimisation model (C1–C12); §7 emissions attribution; §9 performance and the four scale gates; §10 validation (V1–V26, the carrier-equivalent configuration, and the failure-mode table). §6, §8 and §11–§13 are not yet written, and §5.3.1 and §5.6 are cited but unwritten (delivery T23) |
| [2026-08-28-carb3-site-energy-system-architecture.md](../specs/2026-08-28-carb3-site-energy-system-architecture.md) | **The design and its reasoning.** Three layers with a carrier balance between them, the graded-heat cascade, the unit spine, the two-tier temporal structure that lets storage have a value, and the nine foundations it reuses rather than reinvents |
| [2026-08-28-carb3-site-energy-system-data-migration.md](../specs/2026-08-28-carb3-site-energy-system-data-migration.md) | **The data work.** Twenty-three items in five ordered groups covering the 397-row technology collapse, the `technology_category` split, the missing decarbonisation-option join, the hybrid-unit set, reject-heat coefficients, and the inputs the model does not yet have |
| [diagrams/](../specs/diagrams/README.md) | **Generated — do not hand-edit.** The 22 entities of §3 as an ER diagram, the same graph boxed into eight subjects, a locator table naming every non-key column, and the full attribute model |
| [2026-08-28-carb3-site-energy-system-delivery.md](../specs/2026-08-28-carb3-site-energy-system-delivery.md) | **Sequencing.** Files to create and modify, twenty-three tasks with effort estimates, six parallelisation lanes, an explicit not-in-scope list, and the verification commands |

### Implementation plans

Working documents. Each one is executed against the specification and then kept as the
record of what was decided and what was deliberately left out.

| Doc | Topic |
|-----|-------|
| [2026-09-07-temporal-coverage.md](../superpowers/plans/2026-09-07-temporal-coverage.md) | **Temporal coverage.** Several years of measured history behind one base year (D12), and a premise's process list stated as at a year. Carries the reviewed design for the declared forward process switch, which is deferred behind delivery T23 |
| [2026-08-04-comit-headless-integration.md](../superpowers/plans/2026-08-04-comit-headless-integration.md) | Running COMIT without the Shiny front end, so another model can call it |
| [2026-08-04-site-level-pathways-note.md](../superpowers/plans/2026-08-04-site-level-pathways-note.md) | The note explaining how sites sharing a base-year configuration can follow different modelled pathways |
| [../superpowers/specs/2026-08-04-site-level-pathways-design.md](../superpowers/specs/2026-08-04-site-level-pathways-design.md) | The design behind that note. Kept for its reasoning; the note is the reader-facing version |

### Archive

**Archived, not retired.** The frozen baseline specification is not built; it says what the
tables of the coupled-off R run mean. V1 freezes that run, and V1b compares the live model
to it through the data migration's lineage table (live spec §10.2). The baseline must stay
readable for that reading — it simply no longer sits in the main reading path. Section
numbers are aligned between the two, so a `§3.x` reference means the same thing in either.

See [`../specs/archive/README.md`](../specs/archive/README.md) for the full contents and what
still points there.

| Doc | Topic |
|-----|-------|
| [archive/…-implementation.md](../specs/archive/2026-08-19-carb3-site-decarbonisation-implementation.md) | **The COMIT-parity baseline, frozen.** Data model, algorithms A1–A9, the optimisation stated mathematically, emissions rules, output schema, scale gates, validation |
| [archive/…-vision.md](../specs/archive/2026-08-19-carb3-site-decarbonisation-vision.md) | The rationale behind `D1`–`D11` — why COMIT is the base, the three assumptions that block the route, and what is lost by solving each site independently. The decisions themselves are stated in the live specification at §1.6 |
| [archive/…-worked-example.md](../specs/archive/2026-08-19-carb3-site-decarbonisation-worked-example.md) | One cement premise end to end through the baseline's A1–A9, plus the same premise without site intelligence |
| [archive/…-spec-changes.md](../specs/archive/2026-08-28-carb3-site-energy-system-spec-changes.md) | The change record against the baseline. Every forward-looking statement in it has been folded into the live specification |
| [archive/…-review-log.md](../specs/archive/2026-09-01-carb3-site-energy-system-review-log.md) | The two engineering reviews, their fourteen findings and resolutions, and the three known defects in the frozen documents |
| [archive/interfaces/](../specs/archive/interfaces/input-data-model.md) | The baseline's input and output contracts, generated from its §3 and §8 |
| [archive/diagrams/](../specs/archive/diagrams/spec_data_model.md) | The baseline's flow and data-model diagrams, generated from the whole document |
| [archive/…-site-heterogeneity-prd.md](../specs/archive/2026-08-05-site-heterogeneity-prd.md) | ⚠️ **Superseded** and R-file-specific |

## Conventions
- Units (from the workbook `Contents` sheet): energy/capacity in **PJ** (GW for CHP),
  emissions in **kt/Mt CO₂e**, cost in **£m**, distance in **km**, prices based to **2021**.
- Code references point to functions in the `R/` directory of this package.
