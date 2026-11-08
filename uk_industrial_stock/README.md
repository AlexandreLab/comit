# UK industrial building stock (open data)

A planned open-data model of every industrial building in the UK that can be found,
delivered as GeoParquet. Each building carries its footprint, height, storeys, floor area,
postcode, LSOA (Data Zone in Scotland, Data Zone or Super Data Zone in Northern Ireland),
local authority, a CaRBE / CaRB3 activity class and, where the evidence allows, an
energy estimate by carrier.

**Status (2026-11-08): research and plan only. Nothing is built.**

This is a separate project from `carb3/`. The relationship is one way: this model is the
upstream "stock model" that the CaRB3 site energy system assumes exists (live spec §3.1,
`premise_record` and `premise_energy`). It can be built, run and released on its own.

## Documents

| Document | What it holds |
|---|---|
| [docs/01_research_summary.md](docs/01_research_summary.md) | What the National Buildings Database (NBD) phases 1 and 2 did, how CaRB3 and CaRBE classify premises, and the methods literature for each pipeline step. With references |
| [docs/02_open_data_inventory.md](docs/02_open_data_inventory.md) | Every candidate data source with its licence, coverage, join key and role, sorted into "open", "restricted" and "excluded" |
| [docs/03_build_plan.md](docs/03_build_plan.md) | The pipeline, the output schema, the validation plan, the milestones, the risks and the decisions still open |

## The five things to know before reading further

1. **CaRBE, not CaRB3, is the phase 2 taxonomy.** The NBD phase 2 report (DESNZ, May
   2026) uses CaRBE: 15 reported classes, 365 activities, Factory has 58 activities in 7
   groups (`FA_A` Workshops etc to `FA_O` Factory, other). CaRB3 (phase 1, 2024) has 61
   Factory activities with codes `FA01` to `FA99`. Neither publishes its activity lookup
   from VOA codes, so the lookup has to be rebuilt.
2. **The VOA rating list is not open data.** Its download page states "An open government
   licence does not apply". It is free, but under restricted terms. The VOA has also refused
   (FOI, 4 Sept 2025) to release a UARN-to-UPRN lookup. VOA-derived columns therefore sit in
   a separately licensed layer until the terms are read and, if needed, cleared with the VOA.
3. **There is an open route from UPRN to building.** OS Open Linked Identifiers carries the
   UPRN to MasterMap building TOID link (about 40.7 million rows), and OS Open TOID gives each
   TOID a location. Neither carries geometry, so OSM footprints are matched to TOID points.
4. **No open building height or use product exists.** Height comes from Environment Agency,
   Welsh and (partial) Scottish LiDAR. Use comes from VOA, EPC, FSA, OSM tags and site
   registers.
5. **Floor-area energy benchmarks are weak for process industry.** The plan uses reported
   site data first, published NBD phase 2 medians second, and calibrates to DESNZ MSOA
   totals and the NBD synthetic population. Building-level numbers are indicative.

## Planned layout (once building starts)

```
uk_industrial_stock/
  pyproject.toml          uv-managed, its own environment
  config/sources.toml     one entry per source: URL, licence, vintage, checksum
  lookups/                hand-built and versioned: SCat/PD -> CaRB3 -> CaRBE group
  src/ukis/               one module per pipeline stage
  tests/
  data/                   git-ignored: raw/, interim/, output/
```
