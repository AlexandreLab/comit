# Lane `carriers` — emission factors, biogenic fractions, scenario parameters

Read `docs/notes/data/build/00_CONVENTIONS.md` first, then spec §3.4, §3.7, §3.8 and §7.

## Deliverables

1. `docs/notes/data/build/carrier_factors.csv` — one row per **primary** carrier in
   `docs/notes/data/carrier.csv` (17 rows), columns:
   `carrier_id,emission_factor_source,biogenic_fraction,ef_gross_kt_per_pj,ef_year,gcv_ncv_basis,provenance,confidence`.
   - `emission_factor_source` is the series name to use in `scenario_parameters`, of the form
     `ef_<carrier_id>` (just write it; it is a pointer).
   - `ef_gross_kt_per_pj` is the **gross combustion** CO₂ factor (fossil + biogenic carbon,
     before any zero-rating), kt CO₂ per PJ, converted from the DESNZ/DEFRA GHG conversion
     factors (latest published year; state which) — show the conversion in the provenance
     pointer (e.g. kg CO₂e/kWh gross CV × 277,778 / 1000). Use the CO₂-only figure, not CO₂e.
   - `biogenic_fraction` ∈ [0,1]: 0 for pure fossil fuels, 1 for pure biomass, and for
     `waste_derived_fuel` the published UK biogenic carbon share of RDF/SRF (DESNZ/DEFRA
     conversion factors, Environment Agency or WRAP guidance). Leave blank if no UK source
     states it.
   - For `electricity` and `hydrogen` the factor is a scenario series, not a combustion
     constant: give the base-year (2021 or latest) DESNZ grid factor for electricity, and for
     hydrogen leave `ef_gross_kt_per_pj` blank and explain in the DONE file.
2. `docs/notes/data/scenario_parameters.csv` — spec §3.8 columns
   `parameter_id,carrier_id,period,value,unit,provenance,confidence` (the last three are
   extra columns for provenance; keep them). Populate what published UK data supports for the
   **base year 2021** and, where a published projection exists, later periods:
   - `ef_<carrier>` per carrier per period (base year from deliverable 1; grid electricity
     projections from DESNZ Green Book supplementary tables / Treasury Green Book long-run
     marginal factors, cite the table).
   - `import_price` per carrier (DESNZ industrial energy prices statistics, 2021, £/kWh →
     £m/PJ; state the size band chosen).
   - `export_price` for electricity (state the basis; must be strictly below import).
   - `carbon_price` per period (UK ETS 2021 average auction price; Green Book carbon values
     series for projections; cite).
   - `discount_rate` (Green Book 3.5%, cite).
   - Leave blank / omit any series with no published source; list them in DONE.
3. `docs/notes/data/infrastructure_scenario.csv` — spec §3.7 columns plus `provenance`.
   Populate only what is published: the nine GB industrial clusters (name them from the UK
   Industrial Decarbonisation Strategy / cluster plans), hydrogen and CO₂ transport
   `available` and `earliest` periods from the published cluster timelines (HyNet, East Coast
   Cluster, Acorn, etc.). Tariffs blank unless published. Use `scenario_id = published_2024`
   or the year of the source.
4. `docs/notes/data/build/references_carriers.csv` and `DONE_carriers.md`.

Check: every `carrier_id` resolves to `carrier.csv`; every `[REF_ID]` resolves to your
staging references or the existing `references.csv`. Write a small stdlib Python check and run it.
