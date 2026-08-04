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

## Conventions
- Units (from the workbook `Contents` sheet): energy/capacity in **PJ** (GW for CHP),
  emissions in **kt/Mt CO₂e**, cost in **£m**, distance in **km**, prices based to **2021**.
- Code references point to functions in the `R/` directory of this package.
