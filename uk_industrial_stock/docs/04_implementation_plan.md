# 04 Implementation plan: milestones 0 and 1 (access, and the Lincolnshire pilot)

**Goal.** Build the ten-step pipeline of [03_build_plan.md](03_build_plan.md) end to end
for the pilot area, North Lincolnshire (`E06000013`) and North East Lincolnshire
(`E06000012`), and produce the pilot's `buildings`, `premises`, `building_premise`, `sites`
and `evidence` tables, the CaRB3 export and a validation report. The pilot is the decision
point for scaling out (03 §7), so every threshold the build plan leaves open is fixed here
from measurement.

**Defaults adopted for the open decisions in 03 §9,** unless Alexandre overrides them at
checkpoint A: Factory core plus an unvalidated adjacent layer (decision 1); VOA in a
restricted layer (decision 2); one row per building (decision 3); base year 2023 (decision
4); code in this folder for now (decision 5). Decision 6 is settled: rules only.

## How the work is run

- **Branches.** Nothing starts until PR #99 (the plan documents) is merged, because the
  fork takes no stacked PRs. Each lane then works on its own branch off `fork/main`, in its
  own worktree under `.worktrees/<branch>`, and opens its own PR to `main`. Auto-merge is
  disabled on the fork, so every PR needs a manual merge.
- **No shared files between parallel lanes.** Task 1 declares every dependency in
  `pyproject.toml`, and task 3 fixes every interim schema in `schemas.py`, so that no lane
  needs to edit either. Each source has its own config file (`config/sources/<id>.toml`) so
  that two lanes adding sources never touch the same file.
- **herdr lanes.** The primary session runs tasks 1 to 3 itself, then starts the five lanes
  below in sibling herdr panes, each with a self-contained prompt pointing at this document,
  its task numbers, its file allowlist and its verify commands. The primary session reviews
  and merges each PR, runs the quality gate, and runs tasks 13 to 19 (the integration) with
  lanes only where they are independent.

| Lane | Tasks | Model and effort | Why that tier |
|---|---|---|---|
| `ukis-geometry` | 4, 5 | sonnet, medium | Multi-file geometry work with a clear spec |
| `ukis-geography` | 6 | sonnet, low | Joins and point in polygon, mechanical once the schema is fixed |
| `ukis-lookups` | 7, 8 | opus, high | Judgement on every mapping row, and each row must cite its source |
| `ukis-records` | 9, 10, 11 | sonnet, medium | Several loaders and a dedupe |
| `ukis-height` | 12 | sonnet, medium | Raster access spike plus zonal statistics |
| integration (primary) | 13 to 19 | opus, high for 13 and 16; sonnet otherwise | Linking and energy are the hardest algorithms |

- **Tests never touch the network.** Every test uses fixtures under `tests/fixtures/`.
  Downloads are exercised only by `ukis fetch`, run by hand.
- **Verify commands** run from `uk_industrial_stock/`: `uv run pytest -q` for the project,
  and `bash ../tools/quality_gate.sh` from the repo root before every push.

## Human steps (Alexandre), milestone 0

These gate specific tasks, not the whole plan.

| Step | What | Gates |
|---|---|---|
| Human 1 | Read the VOA download terms, accept them, download the 2023 list entries and summary valuations plus the technical specification PDF into `data/raw/voa/2023/`. Record in `config/sources/voa_2023.toml` what the terms allow (release of derived classes: yes, no or unclear) | Task 11; the restricted layer's release status |
| Human 2 | Download the non-domestic EPC and DEC records for the two pilot authorities (GOV.UK One Login needed) into `data/raw/epc_nondom/<date>/` | Task 9's EPC loader on real data |
| Human 3 | Email the UCL NBD team asking for the SCat/PD-to-CaRB3 lookup and the CaRB3-to-CaRBE group mapping | Task 7 can start without it; a reply replaces the rebuilt lookup |
| Human 4 | Confirm or override the defaults above | Checkpoint A |

## File map

All paths are under `uk_industrial_stock/`.

| Path | Responsibility |
|---|---|
| `pyproject.toml`, `uv.lock`, `.python-version` | The project's own uv environment. Python 3.12 (geospatial wheels lag on 3.14). All dependencies declared in task 1 |
| `.gitignore` | Ignores `data/` |
| `Makefile` | `test`, `pilot` (all steps for the pilot area), `fetch-pilot` |
| `config/pilot.toml` | Pilot LAD codes, buffer distance, working CRS, data root |
| `config/sources/<id>.toml` | One per source: URL, licence, tier (`open`, `restricted`, `excluded`), vintage, expected format; `sha256` and `retrieved` are written by `ukis fetch` |
| `src/ukis/cli.py` | `ukis fetch <id>`, `ukis run <step> --area pilot`, `ukis validate --area pilot` |
| `src/ukis/paths.py` | Raw, interim and output directories from `config/pilot.toml` |
| `src/ukis/manifest.py` | Load source configs, download into a new directory per vintage, checksum, refuse a restricted source in an `open` build |
| `src/ukis/io.py` | Read and write GeoParquet 1.1: bbox covering, Hilbert sort, fixed row order, deterministic bytes |
| `src/ukis/schemas.py` | Every interim and output table's columns and types, as pyarrow schemas, plus enum value sets |
| `src/ukis/area.py` | The pilot polygon (union of the two LADs, buffered 2 km) and clipping helpers |
| `src/ukis/steps/step02_osm.py` | OSM extract to `osm_buildings`, `osm_landuse`, `osm_pois` |
| `src/ukis/steps/step03_footprints.py` | OS OpenMap Local gap fill, dedupe, `scu_id`, completeness per LSOA |
| `src/ukis/steps/step04_geography.py` | UPRN spine with ONSUD geography, UPRN-to-TOID, TOID points, building geography |
| `src/ukis/records/{epc,fsa,prtr,naei,ets,business_counts,voa}.py` | One loader per source, each writing the common `records` schema |
| `src/ukis/records/installations.py` | Deduplicate PRTR, NAEI, ETS records into one `installations` row per site |
| `src/ukis/steps/step05_link.py`, `src/ukis/address.py`, `src/ukis/assign.py` | UPRN-to-building and record-to-building linking; address normaliser; size-consistent assignment within a postcode |
| `src/ukis/steps/step06_classify.py` | Evidence rows, resolution, area activity prior |
| `src/ukis/steps/step07_height.py`, `src/ukis/lidar.py` | LiDAR access and zonal statistics |
| `src/ukis/steps/step08_floorarea.py` | Storeys and floor area |
| `src/ukis/steps/step09_energy.py` | The three energy tiers and calibration |
| `src/ukis/steps/step10_assemble.py` | Join, licence filter, final GeoParquet, CaRB3 export |
| `src/ukis/validate.py` | The checks of 03 §6 that apply to the pilot, written to a Markdown report |
| `src/ukis/handcheck.py` | Draws the stratified hand-check sample and writes a review sheet |
| `lookups/*.csv`, `lookups/README.md` | Hand-built lookups, one source column per row, and their provenance |
| `tests/`, `tests/fixtures/` | Unit tests and small synthetic fixtures |
| `../Makefile` (repo root) | Adds a `ukis` target to `check`, so the pre-push gate runs this project's tests |

## Interim schemas (fixed in task 3)

Lanes code against these. A change to one after task 3 merges is its own small PR, made
before any lane depends on the change.

| Table | Key | Columns |
|---|---|---|
| `osm_buildings` | `building_id` | `geometry` (EPSG:27700), `osm_id`, `osm_type`, `building`, `building_levels`, `height_tag`, `name`, `operator`, `addr_housenumber`, `addr_street`, `addr_postcode`, `industrial`, `man_made`, `craft`, `product` |
| `osm_landuse` | `landuse_id` | `geometry`, `kind` (`industrial`, `quarry`, `works`), `name`, `operator` |
| `osm_pois` | `poi_id` | `geometry` (point), the same tag columns as `osm_buildings` |
| `footprints` | `building_id` | `geometry`, `footprint_source`, `footprint_area_m2`, `scu_id`, and the OSM tag columns (null for non-OSM footprints) |
| `uprn_spine` | `uprn` | `x`, `y`, `toid`, `toid_x`, `toid_y`, `oa_code`, `lsoa_code`, `msoa_code`, `lad_code`, `postcode` (null if ONSUD has none) |
| `building_geo` | `building_id` | `oa_code`, `lsoa_code`, `msoa_code`, `lad_code`, `nation`, `geo_level` |
| `records` | `record_id` | `source`, `source_ref`, `licence_tier`, `name`, `address_line`, `housenumber`, `street`, `town`, `postcode`, `uprn`, `x`, `y`, `activity_scheme` (`scat_pd`, `nace`, `sic`, `fsa`, `epc_type`, `naei_sector`), `activity_code`, `activity_text`, `floor_area_m2`, `floor_area_basis`, `employees`, `co2_t`, `data_year` |
| `installations` | `installation_id` | `x`, `y`, `name`, `operator`, `postcode`, `nace_code`, `sector`, `co2_t`, `member_record_ids` (list) |
| `building_premise` | (`building_id`, `premise_id`) | `link_method`, `link_score`, `area_share` |
| `evidence` | (`subject_id`, `source`, `source_ref`) | `subject_kind` (`building`, `premise`), `raw_value`, `carbe_class`, `carbe_group`, `carb3_activity_code`, `weight` |
| `heights` | `building_id` | `height_p50_m`, `height_p90_m`, `height_max_m`, `height_source`, `lidar_year`, `pixel_count` |

Lookup files and their columns are fixed in task 7 and task 8.

## Tasks

### Phase 1: foundation (primary session, sequential)

- [ ] **Task 1. Scaffold the project**
  - **Files:** `pyproject.toml`, `.python-version`, `.gitignore`, `Makefile`,
    `src/ukis/__init__.py`, `src/ukis/cli.py` (stub), `tests/test_smoke.py`, `../Makefile`.
  - **Test first:** `test_smoke.py::test_cli_help` runs `ukis --help` through the CLI's
    entry function and expects exit code 0 and the three subcommands named.
  - **Change:** a uv project named `ukis` with these runtime dependencies: `duckdb`,
    `quackosm`, `geopandas>=1.0`, `shapely>=2`, `pyogrio`, `pyarrow`, `rasterio`,
    `exactextract`, `numpy`, `scipy` (for the assignment solver), `openpyxl`, `requests`,
    `tomli-w`. Dev dependencies: `pytest`. Add a `ukis` target to the root `Makefile` that
    runs `cd uk_industrial_stock && uv run pytest -q`, and make `check` depend on it.
  - **Gotcha:** check that every wheel installs on macOS arm64 with Python 3.12 before
    committing `uv.lock`. If `exactextract` has no wheel, fall back to `rasterstats` and say
    so in the PR.
  - **Verify:** before, `uv run pytest` fails (no project); after, `uv run pytest -q`
    passes, and `bash ../tools/quality_gate.sh` passes from the repo root.
  - **Depends on:** PR #99 merged.

- [ ] **Task 2. Source manifest and fetcher**
  - **Files:** `src/ukis/manifest.py`, `src/ukis/paths.py`, `config/pilot.toml`,
    `config/sources/*.toml` (one per open source in 02 that the pilot uses: Geofabrik GB,
    OS OpenMap Local, OS Open UPRN, OS Open Linked Identifiers, OS Open TOID, ONSUD, NSPL,
    LSOA/MSOA/OA 2021 and LAD boundaries, Code-Point Open, FSA FHRS, FSA approved
    establishments, UK PRTR 2023, NAEI point sources 2023, UK ETS allocation, ONS Business
    Counts, NBD Factory workbook, NBD synthetic population, DESNZ MSOA non-domestic gas and
    electricity, EA LiDAR DSM and DTM), `tests/test_manifest.py`.
  - **Test first:** `test_manifest.py`:
    - `test_every_source_has_licence_and_tier`: loads every TOML and expects `licence`,
      `tier` and `url`, with `tier` in the allowed set;
    - `test_fetch_writes_new_vintage_dir_and_checksum`: a fake downloader serving bytes
      `b"abc"` writes `data/raw/<id>/<vintage>/<file>` and records SHA-256
      `ba7816bf...` in the manifest lock;
    - `test_open_build_refuses_restricted`: `require_tier("open", source)` raises for a
      source with tier `restricted`.
  - **Change:** `ukis fetch <id>` downloads into a new directory, never overwriting, and
    writes `data/raw/manifest.lock.json` (the checksums live there, not in the TOML, so
    fetching never edits a tracked file). OS products are fetched through the OS Downloads
    API (no key for open data).
  - **Verify:** the three tests fail before (no module) and pass after.
  - **Depends on:** task 1.

- [ ] **Task 3. Schemas, GeoParquet IO and the pilot area**
  - **Files:** `src/ukis/schemas.py`, `src/ukis/io.py`, `src/ukis/area.py`,
    `tests/test_io.py`, `tests/test_area.py`, `tests/fixtures/lads_mini.gpkg`.
  - **Test first:**
    - `test_io.py::test_roundtrip_preserves_schema`: write then read a 3-row
      `osm_buildings` frame and expect identical columns, types and values;
    - `test_io.py::test_write_is_deterministic`: two writes of the same frame give
      byte-identical files;
    - `test_io.py::test_geoparquet_metadata_has_bbox_covering`: the file metadata declares
      GeoParquet 1.1 and a `bbox` covering;
    - `test_area.py::test_pilot_polygon_buffers_union`: two adjacent squares in
      `lads_mini.gpkg` give one polygon whose area equals the buffered union.
  - **Change:** `schemas.py` holds the interim schemas table above as pyarrow schemas, plus
    the enums from 03 §3.2. `io.write_table(df, name, area)` validates against the schema,
    sorts by Hilbert distance and then by key, and writes with fixed compression and row
    group size.
  - **Verify:** the tests fail before and pass after; full suite passes.
  - **Depends on:** task 2.
  - **Checkpoint A (Alexandre):** the schemas and the defaults for decisions 1 to 5. The
    lanes start after this.

### Phase 2: five parallel lanes

- [ ] **Task 4. OSM extract** (lane `ukis-geometry`)
  - **Files:** `src/ukis/steps/step02_osm.py`, `tests/test_step02_osm.py`,
    `tests/fixtures/mini.osm.pbf` (a hand-made extract of a few ways, built with pyosmium in
    a fixture script `tests/fixtures/make_mini_pbf.py`).
  - **Test first:** from `mini.osm.pbf`, expect: a `building=yes` way inside
    `landuse=industrial` kept in `osm_buildings`; a multipolygon building relation kept as
    `osm_type = relation`; a `building:levels=2` tag parsed to integer 2; an unparseable
    `height=approx 10m` stored as null (not an error); the landuse polygon in `osm_landuse`
    with `kind = industrial`.
  - **Change:** QuackOSM with a tag filter (03 §4 step 2) and the pilot polygon as geometry
    filter, then reprojection to EPSG:27700 and type coercion.
  - **Verify:** tests fail before and pass after. Then `ukis run step02 --area pilot` on the
    real extract, and report building and landuse counts in the PR.
  - **Depends on:** task 3.

- [ ] **Task 5. Footprint gap fill and SCUs** (lane `ukis-geometry`)
  - **Files:** `src/ukis/steps/step03_footprints.py`, `tests/test_step03_footprints.py`.
  - **Test first:** with synthetic squares: an OS polygon overlapping an OSM building at
    intersection over union 0.8 is dropped; an OS polygon with no overlap is added with
    `footprint_source = os_openmap_local`; two touching footprints share a `scu_id` and a
    detached one does not; the completeness ratio for a fixture LSOA equals OSM area over OS
    area.
  - **Change:** as 03 §4 step 3. SCUs are connected components of footprints that touch or
    overlap within 0.5 m. In the pilot, SCUs do not yet use premises (03 §1.3's
    no-split rule is applied in task 13, which may merge SCUs).
  - **Verify:** tests; then the real pilot run, with the completeness ratio per LSOA in the
    PR.
  - **Depends on:** task 4.

- [ ] **Task 6. Address spine and geography** (lane `ukis-geography`)
  - **Files:** `src/ukis/steps/step04_geography.py`, `tests/test_step04_geography.py`.
  - **Test first:** with fixture CSVs shaped like OS Open UPRN, ONSUD, the
    `BLPU_UPRN_TopographicArea_TOID_5` relationship and OS Open TOID: expect each UPRN to get
    its TOID and TOID point; a UPRN absent from ONSUD to get null geography and appear in the
    step's exceptions file; a fixture footprint to get the LSOA containing its point on
    surface. Also: whether ONSUD has a postcode column is detected from the header, not
    assumed.
  - **Change:** DuckDB joins over the CSVs, clipped to the pilot polygon; building geography
    by point in polygon on the 2021 boundaries.
  - **Verify:** tests; then the real pilot run, reporting UPRN count, the share with a TOID,
    and the share of UPRNs whose ONSUD LSOA disagrees with point in polygon.
  - **Depends on:** task 3 (it reads `footprints` only in the last step, so it can develop
    against fixtures until task 5 lands).

- [ ] **Task 7. Activity lookups** (lane `ukis-lookups`)
  - **Files:** `lookups/scat_pd_to_carb3.csv`, `lookups/carb3_to_carbe_group.csv`,
    `lookups/nace_sic_to_carb3.csv`, `lookups/fsa_activity_to_carb3.csv`,
    `lookups/epc_type_to_class.csv`, `lookups/osm_tag_to_carb3.csv`, `lookups/README.md`,
    `tests/test_lookups.py`.
  - **Test first:** `test_lookups.py`: every `carb3_activity_code` exists in the repo's
    `docs/notes/data/carb3_comit_crosswalk.csv` or is `FA99`; every row has a non-empty
    `source` column; `carb3_to_carbe_group.csv` maps every Factory activity to exactly one
    of `FA_A` to `FA_O`; no duplicate keys in any file.
  - **Change:** build each lookup by hand, one source per row (the OGL SCat list, the PD list
    from the VOA specification once Human 1 lands, CaRB3 Table 28, the NACE Rev. 2 and SIC
    2007 lists, FSA activity names, EPC building types, the OSM wiki). Where a mapping is
    judgement, the `source` says `judgement` with a one-line reason. Check
    `carb3_to_carbe_group.csv` against the NBD phase 2 floor areas per group (01 §1.2):
    summing the CaRB3 Table 28 floor areas by the mapped group should land within ±15% of
    each group's NBD figure, and the PR reports the ratios.
  - **Gotcha:** the CaRB3 floor areas are VOA 2020 (England and Wales) and the NBD figures
    are 2023 (Great Britain), so ±15% is a sanity bound, not a fit target. Do not tune the
    mapping to the bound.
  - **Verify:** tests fail before and pass after.
  - **Depends on:** task 1 (no code dependency beyond the test runner).

- [ ] **Task 8. Energy and geometry lookups** (lane `ukis-lookups`)
  - **Files:** `lookups/carbe_group_eui.csv` (median total, gas and electricity EUI per
    group, from the NBD workbook), `lookups/process_co2_share.csv` (per sector),
    `lookups/sector_fuel_mix.csv` (from ECUK), `lookups/fuel_emission_factor.csv` (from the
    DESNZ conversion factors), `lookups/floor_to_floor.csv` (initial values per group,
    replaced in task 15), `tests/test_energy_lookups.py`.
  - **Test first:** every share column in `sector_fuel_mix.csv` sums to 1 within 1e-6 per
    sector; every `process_co2_share` is in [0, 1); every row cites a source; the EUI file
    has one row per group `FA_A` to `FA_O`.
  - **Change:** extract and cite. The cement process share must reproduce the calcination
    factor (about 0.525 t CO₂ per t of clinker) against a typical kiln's fuel CO₂, and the
    PR shows that arithmetic.
  - **Verify:** tests fail before and pass after.
  - **Depends on:** task 1.

- [ ] **Task 9. Open record loaders** (lane `ukis-records`)
  - **Files:** `src/ukis/records/{epc,fsa,prtr,naei,ets,business_counts}.py`,
    `tests/test_records.py`, `tests/fixtures/records/*` (ten-row extracts in each source's
    real column layout).
  - **Test first:** one test per loader: the fixture loads into the `records` schema with
    the expected `activity_scheme`, the expected postcode normalised to `AA9A 9AA` form, and
    coordinates in EPSG:27700. PRTR: a facility with pollutant rows for CO₂ and NOx becomes
    one record with `co2_t` from the CO₂ row only, converted from kg. Business Counts is
    area-level and writes to its own `area_activity_counts` table, not `records`.
  - **Change:** one loader per source. PRTR is filtered to reporting year 2023 and to the
    pilot polygon.
  - **Verify:** tests; then each loader on real pilot data, with record counts per source in
    the PR.
  - **Depends on:** task 3.

- [ ] **Task 10. Installation dedupe** (lane `ukis-records`)
  - **Files:** `src/ukis/records/installations.py`, `tests/test_installations.py`.
  - **Test first:** a PRTR record and a NAEI record 120 m apart with operator names
    "Tata Steel UK Ltd" and "TATA STEEL UK LIMITED" become one installation; two records
    400 m apart with the same operator stay two; the merged row takes PRTR's NACE code and
    PRTR's `co2_t` (PRTR is the regulator-reported figure), and lists both source records in
    `member_record_ids`.
  - **Change:** as 03 §4 step 5 (250 m plus normalised operator name).
  - **Verify:** tests fail before and pass after; real pilot run with installation count.
  - **Depends on:** task 9.

- [ ] **Task 11. VOA loader, restricted layer** (lane `ukis-records`)
  - **Files:** `src/ukis/records/voa.py`, `tests/test_voa.py`,
    `tests/fixtures/records/voa_sample.txt` (synthetic rows in the asterisk-delimited layout
    from the VOA specification, no real data).
  - **Test first:** list entries parse to `records` with `licence_tier = restricted` and
    `activity_scheme = scat_pd`; summary valuation floor-area lines for one assessment sum to
    that record's `floor_area_m2`; a record written by this loader cannot be passed to
    `io.write_table` for an `open` output (it raises).
  - **Change:** parse both files per the specification. Restricted outputs go to
    `data/interim/restricted/`.
  - **Verify:** tests; then the real pilot run.
  - **Depends on:** task 9, Human 1.

- [ ] **Task 12. Height** (lane `ukis-height`)
  - **Files:** `src/ukis/lidar.py`, `src/ukis/steps/step07_height.py`,
    `tests/test_step07_height.py`, `tests/fixtures/dsm_mini.tif`, `tests/fixtures/dtm_mini.tif`.
  - **Test first:** a synthetic 50 by 50 m DSM with a 10 m-high block on a flat DTM and one
    3 m roof-plant pixel above it: the block's footprint gets `height_p50_m` 10,
    `height_max_m` 13 and `height_p90_m` 10; a footprint of 20 m² is not buffered; a
    footprint outside the raster gets `height_source = none`.
  - **Change:** first a spike, written up in the PR: how EA LiDAR composite tiles are
    fetched for an area (WCS or tile download), with the URL pattern and the size for the
    pilot. Then fetch, nDSM, exactextract with a 1 m inward buffer.
  - **Verify:** tests; then the pilot run, reporting coverage share and the height
    distribution for footprints over 500 m².
  - **Depends on:** task 3 (develops against fixtures; the pilot run needs task 5).

### Phase 3: integration (primary session)

- [ ] **Task 13. Linking**
  - **Files:** `src/ukis/address.py`, `src/ukis/assign.py`, `src/ukis/steps/step05_link.py`,
    `tests/test_address.py`, `tests/test_assign.py`, `tests/test_step05_link.py`.
  - **Test first:**
    - `test_address.py`: "Unit 3, Foo Ind. Est., Bar Rd" and "UNIT 3 FOO INDUSTRIAL ESTATE
      BAR ROAD" normalise to the same key; a postcode with no space is normalised;
    - `test_assign.py`: three VOA records (100, 400, 2,000 m²) and three candidate buildings
      in one postcode (2,100, 90, 380 m² geometric GIA) are assigned 100 to 90, 400 to 380
      and 2,000 to 2,100; adding a fourth record of 150 m², which the one-to-one solve leaves
      unassigned, sends it in a second pass to the building with the most room left
      (2,100 − 2,000 = 100 m², against negative room in the other two), and both links on
      that building carry an `area_share`;
    - `test_step05_link.py`: a UPRN whose TOID point lies in footprint A while its own point
      lies in footprint B links to A with `link_method = toid`; a nearest match at 12 m is
      refused when the second-nearest building is at 18 m (less than twice as far).
  - **Change:** as 03 §4 step 5, with the assignment solved by
    `scipy.optimize.linear_sum_assignment` on the absolute log ratio of areas, per postcode.
    After linking, merge SCUs so that no premises spans two SCUs.
  - **Verify:** tests; then the pilot run, with match rate per source.
  - **Depends on:** tasks 5, 6, 9, 10 (11 when available).
  - **Checkpoint B (Alexandre):** the match rates per source. If VOA records reach
    buildings for under 60% of Factory-class floor area, stop and decide between the
    group-level fallback (03 §7) and more matching work.

- [ ] **Task 14. Classification**
  - **Files:** `src/ukis/steps/step06_classify.py`, `tests/test_step06_classify.py`.
  - **Test first:** a building with a PRTR record (NACE 23.51) and an OSM
    `building=warehouse` tag resolves to `FA45`, `FA_E` with the conflict recorded and
    confidence lowered; a building with only `landuse=industrial` gets class `FA`, group
    `unknown` and a prior; an MSOA with Business Counts of 10 food and 10 metal sites, 5
    food already classed, gives unclassed buildings a prior of one third food, two thirds
    metal; a prior of 0.5 or above sets the group, a lower one leaves `unknown`.
  - **Change:** as 03 §4 step 6, reading the task 7 lookups.
  - **Verify:** tests; then the pilot run, with counts per class, group and
    `class_source`.
  - **Depends on:** tasks 7, 13.

- [ ] **Task 15. Storeys and floor area**
  - **Files:** `src/ukis/steps/step08_floorarea.py`, `tests/test_step08_floorarea.py`,
    `lookups/floor_to_floor.csv` (values updated from the pilot).
  - **Test first:** a 2,000 m² footprint at 9 m p90 height in class `FA` gets 1 storey and
    `storeys_source = assumed_single`; an OSM `building:levels=3` at 12 m is kept; at 40 m it
    is rejected as implausible; geometric GIA equals footprint × storeys × 0.95; a VOA area
    against a geometric area at a ratio of 2.5 sets the review flag.
  - **Change:** as 03 §4 step 8. Fit the floor-to-floor heights on pilot buildings with
    both OSM levels and LiDAR, and write them to `lookups/floor_to_floor.csv` with the
    sample size in the source column.
  - **Verify:** tests; the pilot run, with the VOA-to-geometric ratio distribution.
  - **Depends on:** tasks 12, 14.

- [ ] **Task 16. Energy**
  - **Files:** `src/ukis/steps/step09_energy.py`, `tests/test_step09_energy.py`.
  - **Test first:** a cement installation with 500 kt CO₂ and a process share of 0.6 gets
    fuel from 200 kt of combustion CO₂ only, and no electricity from tier 1; a benchmark
    building of 1,000 m² in `FA_F` gets 293 MWh total before calibration; calibration with
    a target 10% below the benchmark sum scales benchmark buildings by 0.9 and leaves tier-1
    buildings unchanged; a carrier not assessed is absent, not zero.
  - **Change:** as 03 §4 step 9. Calibration targets are the NBD synthetic population's
    Factory energy per MSOA, with the DESNZ MSOA non-domestic totals as an upper bound.
  - **Verify:** tests; the pilot run, with MSOA totals against both targets.
  - **Depends on:** tasks 8, 10, 15.

- [ ] **Task 17. Assembly and CaRB3 export**
  - **Files:** `src/ukis/steps/step10_assemble.py`, `tests/test_step10_assemble.py`.
  - **Test first:** an `open` build drops every column whose source tier is `restricted` and
    still writes; the CaRB3 export writes `premise_record` with `carb3_activity`,
    `latitude`, `longitude`, `nation`, `floorspace`, `data_year`, `source` (the live spec
    §3.1 fields) and `premise_energy` with `data_status` in {measured, estimated, modelled,
    not_consumed}; a premises with no assessed carrier is omitted from the export and listed
    in its exceptions file.
  - **Change:** as 03 §4 step 10. Writes `output/pilot/buildings.parquet` (CRS84),
    `premises.parquet`, `building_premise.parquet`, `sites.parquet`, `evidence.parquet`, and
    `output/pilot/carb3/`.
  - **Verify:** tests; the pilot run; the output reads in GeoPandas and DuckDB.
  - **Depends on:** task 16.

- [ ] **Task 18. Validation report**
  - **Files:** `src/ukis/validate.py`, `tests/test_validate.py`.
  - **Test first:** each check in 03 §6 that applies to the pilot returns a structured
    result with value, aim and status; the determinism check runs the build twice on a
    fixture area and compares bytes.
  - **Change:** writes `output/pilot/validation.md`. Pilot-relevant checks: completeness per
    LSOA, area counts against VOA Stock of Properties, Business Counts mix, large-site
    coverage, height against OSM tags, floor area against EPC, energy against the synthetic
    population and DESNZ, determinism.
  - **Verify:** tests; the report generated for the pilot.
  - **Depends on:** task 17.

- [ ] **Task 19. Hand-check sample**
  - **Files:** `src/ukis/handcheck.py`, `tests/test_handcheck.py`.
  - **Test first:** with a fixed seed, the sample of 150 is stratified by `carbe_group` with
    at least 10 per group where the group has that many, and is reproducible.
  - **Change:** writes `output/pilot/handcheck.csv` with building id, coordinates, a map
    link, the classified activity and empty columns for the reviewer's answer.
  - **Verify:** tests; the sheet generated.
  - **Depends on:** task 17.
  - **Checkpoint C (Alexandre):** fill in the hand-check sheet. Activity accuracy is then
    added to the validation report.

- [ ] **Checkpoint D: the pilot decision.** With the validation report and the hand check,
  decide whether to scale out to England and Wales (milestone 2) as planned, or revise 03
  first.
