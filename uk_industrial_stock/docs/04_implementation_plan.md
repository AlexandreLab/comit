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

- **Branches and PRs (eng review D5).** Nothing starts until PR #99 (the plan documents)
  is merged, because the fork takes no stacked PRs. Then three PRs, one per phase, each
  opened at its checkpoint and merged by hand (auto-merge is disabled on the fork):
  1. **Foundation** (`feat/ukis-foundation`, tasks 1 to 3), opened at checkpoint A.
  2. **Lanes** (`feat/ukis-lanes`, tasks 4 to 12), branched off `fork/main` once the
     foundation PR is merged. Each lane works on its own branch off `feat/ukis-lanes`
     (`lane/ukis-geometry` and so on) in its own worktree; it does not open a PR. The
     primary session reviews each lane branch, runs the tests and merges it into
     `feat/ukis-lanes` locally. The PR opens when all five lanes are merged.
  3. **Integration** (`feat/ukis-integration`, tasks 13 to 19), branched off `fork/main`
     once the lanes PR is merged; opened at checkpoint D.
- **No shared files between parallel lanes.** Task 1 declares every dependency in
  `pyproject.toml`, and task 3 fixes every interim schema in `schemas.py`, so that no lane
  needs to edit either. Each source has its own config file (`config/sources/<id>.toml`) so
  that two lanes adding sources never touch the same file.
- **herdr lanes.** The primary session runs tasks 1 to 3 itself, then starts the five lanes
  below in sibling herdr panes, each with a self-contained prompt pointing at this document,
  its task numbers, its file allowlist and its verify commands. The primary session reviews
  and merges each lane branch, runs the quality gate, and runs tasks 13 to 19 (the
  integration) with lanes only where they are independent.

| Lane | Tasks | Model and effort | Why that tier |
|---|---|---|---|
| `ukis-geometry` | 4, 5 | sonnet, medium | Multi-file geometry work with a clear spec |
| `ukis-geography` | 6 | sonnet, low | Joins and point in polygon, mechanical once the schema is fixed |
| `ukis-lookups` | 7, 8 | opus, high | Judgement on every mapping row, and each row must cite its source |
| `ukis-records` | 9, 10, 11 | sonnet, medium | Several loaders and a dedupe |
| `ukis-height` | 12 | sonnet, medium | Raster access spike plus zonal statistics |
| integration (primary) | 13 to 19 | opus, high for 13 and 16; sonnet otherwise | Linking and energy are the hardest algorithms |

- **Loud failure (eng review D9).** Every loader declares the source columns it needs and
  raises, naming them, if any is missing. Every step writes the rows it cannot use to
  `exceptions/<step>.parquet` (`subject_id`, `reason`, `detail`) through `io.write_exceptions`;
  nothing is dropped silently. Every loader has a missing-column test and every step a
  dropped-rows test, in addition to the tests listed under each task.
- **Determinism.** Every spatial match that can tie (a point on a shared edge, two
  equidistant buildings) breaks the tie by the smallest `building_id`, so a rebuild is
  byte-identical (03 §2 principle 5). A copy of `manifest.lock.json` is written beside
  every output, and `source_manifest_sha` is its SHA-256.
- **Tests never touch the network.** Every test uses fixtures under `tests/fixtures/`.
  Downloads are exercised only by `ukis fetch`, run by hand.
- **Verify commands** run from `uk_industrial_stock/`: `uv run pytest -q` for the project,
  and `bash ../tools/quality_gate.sh` from the repo root before every push.

## Human steps (Alexandre), milestone 0

These gate specific tasks, not the whole plan.

| Step | What | Gates |
|---|---|---|
| Human 1 | Read the VOA download terms, accept them, download the 2023 list entries and summary valuations plus the technical specification PDF into `$UKIS_DATA_ROOT/raw/voa/2023/`. Record in `config/sources/voa_2023.toml` what the terms allow (release of derived classes: yes, no or unclear) | Task 11; the restricted layer's release status |
| Human 2 | Download the non-domestic EPC and DEC records for the two pilot authorities (GOV.UK One Login needed) into `$UKIS_DATA_ROOT/raw/epc_nondom/<date>/` | Task 9's EPC loader on real data |
| Human 3 | Email the UCL NBD team asking for the SCat/PD-to-CaRB3 lookup and the CaRB3-to-CaRBE group mapping | Task 7 can start without it; a reply replaces the rebuilt lookup |
| Human 4 | Confirm or override the defaults above | Checkpoint A |
| Human 5 | Read the EPC register's licence terms for address and postcode fields (03 milestone 0). Record in `config/sources/epc_nondom.toml` whether the address fields are open; if not, the EPC address bridge in task 13 runs in the `full` tier only (outside voice O8) | Tasks 0 and 13 |

## File map

All paths are under `uk_industrial_stock/`.

| Path | Responsibility |
|---|---|
| `pyproject.toml`, `uv.lock`, `.python-version` | The project's own uv environment. Python 3.12 (geospatial wheels lag on 3.14). All dependencies declared in task 1 |
| `.gitignore` | Ignores `data/` (interim and output; raw data lives outside the repo) |
| `Makefile` | `test`, `pilot` (all steps for the pilot area), `fetch-pilot` |
| `config/pilot.toml` | Pilot LAD codes, buffer distance, working CRS, data root |
| `config/sources/<id>.toml` | One per source: URL, licence, tier (`open`, `restricted`, `excluded`), vintage, expected format; `sha256` and `retrieved` are written by `ukis fetch` |
| `src/ukis/cli.py` | `ukis fetch <id>`, `ukis run <step> --area pilot`, `ukis validate --area pilot` |
| `src/ukis/paths.py` | Raw data under `UKIS_DATA_ROOT` (default `~/data/ukis`, shared by every worktree, eng review D7); interim and output inside the checkout |
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
| `spikes/voa_match/`, `docs/05_voa_match_spike.md` | Task 0's throwaway measurement and its write-up (eng review D14) |
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
| `sites` | `site_id` | `geometry`, `site_source` (`osm_landuse`, `inspire`, `installation`), `name`, `installation_id` (nullable). Built in task 5 from `osm_landuse` (INSPIRE polygons join at milestone 2); task 13 attaches `installation_id` (outside voice O4) |
| `premises` | `premise_id` | `record_ids` (list), `source_tier`, `carb3_activity_code`, `floor_area_m2`, `floor_area_source`, `postcode`. Built in task 13 from linked records (outside voice O4) |
| `area_activity_counts` | (`msoa_code`, `sic_code`, `size_band`) | `count`, `data_year`. Written by task 9's Business Counts loader (outside voice O4) |
| `building_premise` | (`building_id`, `premise_id`) | `link_method`, `link_score`, `area_share` |
| `evidence` | (`subject_id`, `source`, `source_ref`) | `subject_kind` (`building`, `premise`), `raw_value`, `carbe_class`, `carbe_group`, `carb3_activity_code`, `weight` |
| `heights` | `building_id` | `height_p50_m`, `height_p90_m`, `height_max_m`, `height_source`, `lidar_year`, `pixel_count` |

Lookup files and their columns are fixed in task 7 and task 8.

## Tasks

### Phase 1: foundation (primary session, sequential)

- [ ] **Task 0. VOA match-feasibility spike** (eng review D14; runs alongside tasks 1 to 3)
  - **Files:** `spikes/voa_match/` (throwaway scripts, not package code, not tested),
    `docs/05_voa_match_spike.md` (the write-up, plus a row in this project's README).
  - **Change:** for North Lincolnshire and North East Lincolnshire, load the VOA 2023 list,
    OS Open UPRN, ONSUD, the non-domestic EPC records and OS OpenMap Local building
    footprints, and report: VOA records per LAD and per CaRBE Factory group (through a rough
    SCat lookup); the number of candidate buildings per VOA postcode under each candidate
    rule considered for task 13: (i) buildings holding a UPRN whose EPC or ONSUD postcode
    equals the VOA postcode, (ii) buildings within 100, 250 or 500 m of the postcode's
    Code-Point Open centroid inside the same industrial land-use or site polygon, and their
    union, each with its hit rate on the ground-truth records below (eng review D16); the share of VOA records whose address matches an EPC
    record carrying a UPRN; and, on those as ground truth, the share a size-consistent
    assignment gets right. Every number cites the command that produced it.
  - **Verify:** the write-up exists and states each number with its source.
  - **Depends on:** Human 1 and Human 2.

- [ ] **Task 1. Scaffold the project**
  - **Files:** `pyproject.toml`, `.python-version`, `.gitignore`, `Makefile`,
    `src/ukis/__init__.py`, `src/ukis/cli.py` (stub), `tests/test_smoke.py`, `../Makefile`.
  - **Test first:** `test_smoke.py::test_cli_help` runs `ukis --help` through the CLI's
    entry function and expects exit code 0 and the three subcommands named.
  - **Change:** a uv project named `ukis` with these runtime dependencies: `duckdb`,
    `quackosm`, `geopandas>=1.0`, `shapely>=2`, `pyogrio`, `pyarrow`, `rasterio`,
    `exactextract`, `numpy`, `scipy` (for the assignment solver), `openpyxl`, `requests`,
    `tomli-w`. Dev dependencies: `pytest`. Add a `ukis` target to the root `Makefile` that
    runs `cd uk_industrial_stock && uv run pytest -q -m "not slow"`, and a `ukis-all` target
    that runs the whole suite (eng review D18), and make `check` depend on `ukis` after
    the existing targets: `check: docs-check data-check carb3 ukis` (eng review D12). Add
    `tests/conftest.py`, which blocks socket connections for the whole suite and registers
    the `slow` marker. Before pytest, the `ukis` target installs DuckDB's `spatial`
    extension into a project-local extension directory (`DUCKDB_EXTENSION_DIRECTORY` under
    `$UKIS_DATA_ROOT/duckdb_ext`), so tests never need the network for it, and QuackOSM's
    working cache is pointed at `$UKIS_DATA_ROOT/cache/quackosm` rather than `./files`
    (outside voice O5). Add `osmium` (pyosmium) to the dev dependencies for the PBF
    fixtures (outside voice O10).
  - **Gotcha:** check that every wheel installs on macOS arm64 with Python 3.12 before
    committing `uv.lock`. If `exactextract` has no wheel, fall back to `rasterstats` and say
    so in the PR.
  - **Verify:** before, `uv run pytest` fails (no project); after, `uv run pytest -q`
    passes, and `bash ../tools/quality_gate.sh` passes from the repo root with docs-check,
    data-check and carb3 still running first, its output naming the ukis test count, and
    the ukis gate suite (`-m "not slow"`) under 60 s; `make ukis-all` runs every test,
    including the `slow` ones, and is part of every phase PR's verification (eng review
    D18).
  - **Depends on:** PR #99 merged.

- [ ] **Task 2. Source manifest and fetcher**
  - **Files:** `src/ukis/manifest.py`, `src/ukis/paths.py`, `config/pilot.toml`,
    `config/sources/*.toml` (one per open source in 02 that the pilot uses: Geofabrik Lincolnshire (`geofabrik_lincolnshire`, about 43 MB; the GB extract
    joins at milestone 2, eng review D13),
    OS OpenMap Local, OS Open UPRN, OS Open Linked Identifiers, OS Open TOID, ONSUD, NSPL,
    LSOA/MSOA/OA 2021 and LAD boundaries, Code-Point Open, FSA FHRS, FSA approved
    establishments, UK PRTR 2023, NAEI point sources 2023, UK ETS allocation, ONS Business
    Counts, VOA Stock of Properties March 2026 (outside voice O15), NBD Factory workbook, NBD synthetic population, DESNZ MSOA non-domestic gas and
    electricity, EA LiDAR DSM and DTM), `tests/test_manifest.py`.
  - **Test first:** `test_manifest.py`:
    - `test_every_source_has_licence_and_tier`: loads every TOML and expects `licence`,
      `tier` and `url`, with `tier` in the allowed set;
    - `test_fetch_writes_new_vintage_dir_and_checksum`: a fake downloader serving bytes
      `b"abc"` writes `data/raw/<id>/<vintage>/<file>` and records SHA-256
      `ba7816bf...` in the manifest lock;
    - `test_interrupted_fetch_leaves_nothing`: a fake downloader that raises halfway
      leaves no vintage directory and no lock entry, and a second fetch then succeeds
      (eng review D11);
    - `test_concurrent_fetch_single_dir`: two fetches of one source started together
      (threads, fake downloader) leave exactly one vintage directory and one lock entry;
    - `test_open_build_refuses_restricted`: `require_tier("open", source)` raises for a
      source with tier `restricted`, and `require_tier("full", source)` does not.
  - **Change:** `ukis fetch <id>` downloads into a new directory under
    `$UKIS_DATA_ROOT/raw/`, never overwriting, holding a per-source lock file while it
    runs. It downloads to `<raw>/.partial/<id>-<random>/`, checks the size against the
    server's `Content-Length` and the SHA-256 against any checksum the lock already holds
    for that vintage, then renames the directory into place in one step (eng review D11).
    Steps read only vintages listed in the lock. It and writes `$UKIS_DATA_ROOT/raw/manifest.lock.json` (the checksums live there, not in the TOML, so
    fetching never edits a tracked file). Every `ukis run` takes `--tier open|full`
    (default `open`) and writes to `data/interim/<tier>/` and `output/<area>/<tier>/`, so
    the two builds never share an interim file (eng review D6). OS products are fetched through the OS Downloads
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
    the enums from 03 §3.2. `io.write_exceptions(step, df)` writes `exceptions/<step>.parquet`
    with `subject_id`, `reason` and `detail`. `io.write_table(df, name, area)` validates
    against the schema,
    sorts by Hilbert distance and then by key, and writes with fixed compression and row
    group size.
  - **Verify:** the tests fail before and pass after; full suite passes.
  - **Depends on:** task 2.
- [ ] **Task 3b. Synthetic end-to-end area** (eng review D10)
  - **Files:** `tests/fixtures/make_area_mini.py`, `tests/fixtures/area_mini/` (its output,
    committed), `tests/test_e2e.py`.
  - **Test first:** `test_e2e.py` runs every implemented step on `area_mini` in the `open`
    tier (in the gate) and the `full` tier (marked `slow`, eng review D18), in order, and checks that each step's output reads back under its
    schema. Four named buildings carry the assertions: a single-occupier shed with a PRTR
    record, a multi-let workshop terrace with three VOA records (`full` only), a
    three-storey works with OSM levels, and an unrecorded shed inside `landuse=industrial`.
    Expected values live in one file per step, `tests/e2e/expected_step<NN>.py`, so lanes
    never edit the same test file; a lane that needs a new fixture element asks the primary
    session, which owns `make_area_mini.py` (outside voice O9). On a lane branch the test
    runs only the steps that exist there; the full chain first runs when the lanes merge
    into `feat/ukis-lanes`.
  - **Change:** a script that writes about 12 footprints, 30 UPRNs with TOIDs, 15 records
    across EPC, FSA, PRTR, NAEI and VOA formats, Business Counts for two MSOAs, and a
    100 by 100 m DSM and DTM, all synthetic, in each source's raw layout. Running the
    script twice writes identical files.
  - **Verify:** `uv run pytest tests/test_e2e.py -q` passes with only the steps that exist;
    the lanes run it before every merge into `feat/ukis-lanes`.
  - **Depends on:** task 3.
  - **Checkpoint A (Alexandre):** the schemas, the defaults for decisions 1 to 5, and the
    task 0 spike note, which confirms or revises task 13's design and task 11's scope
    before the lanes start (eng review D14). Then
    the primary session runs `make fetch-pilot` once, filling `$UKIS_DATA_ROOT/raw/` for
    every lane (eng review D7), and the lanes start.

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
  - **Change:** first check that the input extract's bounding box covers the buffered pilot
    polygon, and raise naming the source if it does not (eng review D13). Then QuackOSM with
    a tag filter (03 §4 step 2) and the pilot polygon as geometry filter, then reprojection
    to EPSG:27700 and type coercion. The test adds a case where the extract's box misses
    the polygon and expects the error.
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
  - **Change:** as 03 §4 step 3. Also writes `sites` from `osm_landuse` polygons
    (outside voice O4). SCUs are connected components of footprints that touch or
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
  - **Files:** `lookups/carb3_activities.csv` (the canonical list: all 55 Factory codes
    from CaRB3 Table 28, with name, premises, floor area and page reference; eng review
    D3), `lookups/scat_pd_to_carb3.csv`, `lookups/carb3_to_carbe_group.csv`,
    `lookups/nace_sic_to_carb3.csv`, `lookups/fsa_activity_to_carb3.csv`,
    `lookups/epc_type_to_class.csv`, `lookups/osm_tag_to_carb3.csv`, `lookups/README.md`,
    `tests/test_lookups.py`.
  - **Test first:** `test_lookups.py`: `carb3_activities.csv` holds exactly 55 distinct
    codes, and every one of its names appears character for character in the repo's
    `docs/notes/data/activity_process_register.csv` (outside voice O3); every `carb3_activity_code` in the other lookups exists in it (the repo's
    `docs/notes/data/carb3_comit_crosswalk.csv` is not the reference: it codes only 47 of
    the 55); every row has a non-empty
    `source` column; `carb3_to_carbe_group.csv` maps every Factory activity to exactly one
    of `FA_A` to `FA_O`; no duplicate keys in any file.
  - **Change:** build each lookup by hand, one source per row (the OGL SCat list, the PD list
    from the VOA specification once Human 1 lands, CaRB3 Table 28, the NACE Rev. 2 and SIC
    2007 lists, FSA activity names, EPC building types, the OSM wiki). Where a mapping is
    judgement, the `source` says `judgement` with a one-line reason. Check
    `carb3_to_carbe_group.csv` against the NBD phase 2 floor areas per group (01 §1.2):
    summing the floor areas in `carb3_activities.csv` by the mapped group should land within ±15% of
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
    area-level and writes to its own `area_activity_counts` table, not `records`. For each
    loader, a fixture with one required column removed raises an error naming that column
    (eng review D9).
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
    from the VOA specification, no real data). The loader calls
    `require_tier(build_tier, source)` before reading, so an `open` build never opens a
    VOA file.
  - **Test first:** list entries parse to `records` with `licence_tier = restricted` and
    `activity_scheme = scat_pd`; summary valuation floor-area lines for one assessment sum to
    that record's `floor_area_m2`; in an `open` build the loader raises before reading the
    file; a record written by this loader cannot be passed to `io.write_table` for an `open`
    output (it raises).
  - **Change:** parse both files per the specification. Its outputs go to
    `data/interim/full/`, the `full` tier's directory (outside voice O14).
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
      in one postcode (2,100, 90, 380 m² provisional GIA) are assigned 100 to 90, 400 to 380
      and 2,000 to 2,100; adding a fourth record of 150 m², which the one-to-one solve leaves
      unassigned, sends it in a second pass to the building with the most room left
      (2,100 − 2,000 = 100 m², against negative room in the other two), and both links on
      that building carry an `area_share`;
    - `test_step05_link.py`: `gia_provisional_m2` is 1 storey for a 600 m² footprint at
      p90 12 m, 3 storeys for a 400 m² footprint at p90 12.5 m (12.5 ÷ 4.0 rounds to 3), and
      1 storey with no height; a UPRN whose TOID point lies in footprint A while its own point
      lies in footprint B links to A with `link_method = toid`; a nearest match at 12 m is
      refused when the second-nearest building is at 18 m (less than twice as far).
  - **Candidate rule: pending until checkpoint A** (eng review D16). Task 0 measures the
    candidate rules for which buildings may receive a VOA record, and checkpoint A picks
    one; this task implements the chosen rule.
  - **Change:** as 03 §4 step 5, with the assignment solved by
    `scipy.optimize.linear_sum_assignment` on the absolute log ratio of areas, per postcode.
    The building side of the ratio is `gia_provisional_m2`, computed here from footprint and
    height without the class, because the final GIA (task 15) needs the class, which needs
    these links (eng review D8): 1 storey for a footprint over 500 m² with p90 height of
    15 m or less, else p90 ÷ 4.0 m rounded with a minimum of 1, and 1 where there is no
    height.
    After linking, merge SCUs so that no premises spans two SCUs. Writes `premises` (one row
    per linked record group) and attaches each `installation` to the `site` containing it
    (outside voice O4).
  - **Verify:** tests; then the pilot run, with match rate per source and the hold-out
    accuracy: VOA records whose address matches an EPC record carrying a UPRN have their
    known building withheld, are linked by the normal rules, and the share placed in the
    right building is reported (eng review D17).
  - **Depends on:** tasks 5, 6, 9, 10 and 12 (11 when available). If task 12's LiDAR spike
    stalls, task 13 still runs: D8's rule already gives 1 storey where there is no height,
    and the assignment is re-solved once heights land (outside voice O11).
  - **Checkpoint B (Alexandre):** the match rates per source and the hold-out accuracy. If
    VOA records reach buildings for under 60% of Factory-class floor area, **or** fewer than
    80% of the hold-out records land in the right building (threshold revisited with task
    0's numbers), stop and decide between the group-level fallback (03 §7) and more
    matching work (eng review D17).

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
    still writes (a second guard: in an `open` build no restricted source is ever loaded,
    eng review D6); the CaRB3 export writes `premise_record` with `carb3_activity`,
    `latitude`, `longitude`, `nation`, `floorspace`, `data_year`, `source` (the live spec
    §3.1 fields) and `premise_energy` with `data_status` in {measured, estimated, modelled,
    not_consumed}; a premises with no assessed carrier is omitted from the export and listed
    in its exceptions file; `premise_throughput` is written with the spec's columns and no
    rows, and every exported premise whose activity has a mass duty is listed in
    `carb3/exceptions.csv` with reason `no_throughput`. An activity has a mass duty when
    any unit eligible for it in `unit_eligibility.csv` has a `primary_output` row in
    `unit_input_output.csv` on a carrier with `may_export` TRUE and `denominator_kind`
    mass, excluding `co2_captured` (eng review D15, which replaced D4's source: the duty
    profile holds no mass carrier). A cement works fixture must appear in the list; an NI premise is not exported and is listed with reason
    `out_of_scope_nation` (eng review D4). The export writes all five files
    `carb3.load.PREMISE_SCHEMA` requires (`premise_record`, `premise_connection`,
    `premise_throughput`, `premise_process_detail`, `premise_process_unit`; the last three
    with headers and no rows where open data has nothing), plus `premise_energy` per spec
    §3.1.1, which the current carb3 slice does not read (outside voice O1). The test loops
    over every exported premise calling `carb3.load.load_premise_tables(premise_id, root)`
    and then `resolve_premise_references`, and expects no error; every `carb3_activity`
    must therefore match `activity_process_register.csv` exactly (outside voice O3).
  - **Change:** as 03 §4 step 10. Writes, per tier, `output/pilot/<tier>/buildings.parquet` (CRS84),
    `premises.parquet`, `building_premise.parquet`, `sites.parquet`, `evidence.parquet`, and
    `output/pilot/<tier>/carb3/`. In the `open` tier, premises exist only where an EPC,
    FSA or register record was linked, so unrecorded Factory buildings carry benchmark
    energy in `buildings` but are absent from the CaRB3 export; the export README states
    the count (outside voice O12).
  - **Verify:** tests; the pilot run; the output reads in GeoPandas and DuckDB.
  - **Depends on:** task 16.

- [ ] **Task 18. Validation report**
  - **Files:** `src/ukis/validate.py`, `tests/test_validate.py`.
  - **Test first:** each check in 03 §6 that applies to the pilot returns a structured
    result with value, aim and status; the determinism check runs the build twice on
    `area_mini` (task 3b) and compares bytes; the licence check runs the `open` build on the fixture
    area twice, once with a restricted VOA fixture present on disk and once without, and
    expects byte-identical outputs (eng review D6); the determinism and licence tests are
    marked `slow` (eng review D18); the linking check re-solves task 13's
    assignment on task 15's final GIA and reports how many links change (eng review D8).
  - **Change:** writes `output/pilot/<tier>/validation.md`. It opens with the exception
    counts per step and reason (eng review D9). Pilot-relevant checks: link hold-out accuracy
    (eng review D17), completeness per LSOA, area counts against VOA Stock of Properties, Business Counts mix, large-site
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

## Eng review (2026-11-08): scope record and decision ledger

Target: this file, `uk_industrial_stock/docs/04_implementation_plan.md`, with
`03_build_plan.md` as its spec. Reviewer: Claude (native `/plan-eng-review`).

**Scope record.** feature answers: none proposed; structure: A, original arrangement (D2);
accepted scope: the plan as written, about 28 modules; pending remedies: F1, F2, F3.
Scope Challenge result: scope accepted as-is.

## Decision ledger

### F1: canonical list of CaRB3 Factory activities for task 7
Finding: 1, P1, confidence 9/10, task 7 "Test first" ("every `carb3_activity_code` exists in the repo's `docs/notes/data/carb3_comit_crosswalk.csv` or is `FA99`"), reviewer Claude.
Plan baseline: original proposal: validate lookup codes against the repo crosswalk.
Runtime evidence: the crosswalk has 55 activity rows but only 47 distinct codes; 8 rows have a blank code (Exhaust and tyre centre, Mineral Production - Inert, - Coal, - Gas, - Other Mineral Category, - Brine, Mill, Pumping Mines). Table 28 of the phase 1 Part 1 report codes all 55, including FA04 (Exhaust and tyre centre), FA46 (Pumping Mines) and FA57 (Mineral Production - Brine). Read from the extracted report text.
Comparison grid:

| Choice | Current | A | B |
|---|---|---|---|
| F1 reference list for activity codes | repo crosswalk, 47 of 55 coded | new `lookups/carb3_activities.csv` from Table 28 (code, name, premises, floor area, page), tests check against it | fill the 8 blank codes in the repo crosswalk and test against that |
| Repo `docs/notes/data/` touched | no | no | yes, one CSV the R model never reads |
| Task 7 floor-area check source | unstated | Table 28 floor areas in the new file | crosswalk notes, which hold floor area only for some rows |

Question D3:
D3 — Which list should task 7 treat as the full set of CaRB3 Factory activities?
Project/branch/task: docs/industrial-stock-plan, reviewing task 7 (activity lookups) of 04_implementation_plan.md.
ELI10: Task 7's test checks every activity code against the repo's CaRB3 crosswalk. That crosswalk is missing the code for 8 of its 55 activities, such as FA04 (Exhaust and tyre centre) and FA57 (Mineral Production - Brine), so the test would reject valid codes or those activities could never be mapped. The source report's Table 28 has all 55 codes with premises counts and floor areas.
Stakes if we pick wrong: 8 activities silently unmappable, or a red test the lookups lane cannot fix inside its file allowlist.
Recommendation: A because it keeps this project independent of carb3's data folder, and Table 28's floor areas are exactly what task 7's ±15% group check needs.
Completeness: A=10/10, B=8/10
Pros / cons:
A) New activity list from Table 28 (recommended)
  ✅ All 55 codes, names, premises counts and floor areas in one cited file
  ✅ Stays inside uk_industrial_stock/, so no change to the carb3 reference data
  ❌ Two lists of the same activities now exist in the repo and can drift apart
B) Fill the blanks in the repo crosswalk
  ✅ One list for both projects, so the codes cannot drift
  ✅ Fixes a real gap in the carb3 reference data at the same time
  ❌ Touches docs/notes/data/ from this project's lane, and the floor areas still need a home
Net: a self-contained cited list versus one shared list that crosses the project boundary.
Header: Activity list
Options:
A) Table 28 list (recommended)
Add lookups/carb3_activities.csv built from Table 28 (all 55 codes, names, premises, floor area, page reference); task 7 tests check every code against it and the ±15% group check reads its floor areas.
B) Fill repo crosswalk
Fill the 8 blank codes in docs/notes/data/carb3_comit_crosswalk.csv and keep task 7's test pointed at it; floor areas for the group check come from a separate extract.

State: approved
Actual answer: A) Table 28 list (D3, 2026-11-08)
Accepted scope: add `lookups/carb3_activities.csv` built from Table 28 (all 55 codes, names, premises, floor area, page reference); task 7 tests check every code against it and the ±15% group check reads its floor areas. Applied to task 7 above.
History: none

### F2: the CaRB3 export and `premise_throughput`
Finding: 2, P2, confidence 8/10, task 17 "Test first" (writes `premise_record` and `premise_energy` only) and 03 §3.3 ("`premise_throughput`, which the spec requires, has no open source"), reviewer Claude.
Plan baseline: original proposal: the export writes `premise_record` and `premise_energy`; throughput is named as a gap.
Runtime evidence: `carb3/src/carb3/load.py:262` makes `premise_throughput` a required field of `PremiseTables`, and `load.py:252` says it is how a mass duty on an exportable product is derived (the cement works' 1.13 Mt/yr). So an export without the table cannot be loaded at all.
Factual correction, no question needed: the live spec's `nation` field (`docs/specs/2026-08-28-carb3-site-energy-system-implementation.md:234`) already says Northern Ireland is "rejected with reason `out_of_scope_nation`". 03 §3.3 calls this a gap to settle; it is settled. The export drops NI premises with that reason. 03 §3.3 is corrected below.
Comparison grid:

| Choice | Current | A | B |
|---|---|---|---|
| F2 `premise_throughput` in the export | absent | written with the spec's columns and no rows, plus `carb3/exceptions.csv` listing every exported premise whose activity has a mass duty, reason `no_throughput` | absent; the export is documented as not loadable by `carb3` until throughput exists upstream |
| carb3 can load the export | no | yes, for energy-only activities; mass-duty premises are named in the exceptions list | no |

Question D4:
D4 — How should the CaRB3 export handle the throughput table it cannot fill?
Project/branch/task: docs/industrial-stock-plan, reviewing task 17 (assembly and CaRB3 export) of 04_implementation_plan.md.
ELI10: The carb3 model refuses to load a premise set without a `premise_throughput` table, and uses it to size things like a cement works' clinker output. Open data gives throughput for almost no site, so the export can either write the table empty and list the premises that really need a figure, or leave it out and accept that carb3 cannot read the export yet.
Stakes if we pick wrong: an export that carb3 rejects on load, or premises that load but quietly lack a mass duty.
Recommendation: A because carb3 can then read the export straight away for energy-only activities, and the exceptions list says exactly which premises still need throughput.
Completeness: A=9/10, B=5/10
Pros / cons:
A) Empty table plus exceptions list (recommended)
  ✅ carb3 loads the export now, so the two projects can be tested end to end in the pilot
  ✅ Every premise that needs a throughput figure is named, with reason `no_throughput`
  ❌ A mass-duty premise could still be run without its duty if someone ignores the list
B) Leave throughput out
  ✅ Nothing in the export looks more complete than it is
  ✅ No dependency on carb3's duty profile to decide which activities need a figure
  ❌ carb3 cannot load the export at all, so the end-to-end check waits for upstream data
Net: an export carb3 can read today, with its gaps listed, versus one that waits for throughput.
Header: Throughput
Options:
A) Empty table + exceptions (recommended)
Task 17 writes `premise_throughput` with the spec's columns and no rows, and `carb3/exceptions.csv` naming every exported premise whose activity has a mass duty (read from `activity_process_duty_profile.csv`), reason `no_throughput`; its test checks both.
B) Leave it out
Task 17 writes `premise_record` and `premise_energy` only, and the export README says carb3 cannot load it until a throughput source exists.

State: approved
Actual answer: A) Empty table + exceptions (D4, 2026-11-08)
Accepted scope: task 17 writes `premise_throughput` with the spec's columns and no rows, and `carb3/exceptions.csv` naming every exported premise whose activity has a mass duty (read from `activity_process_duty_profile.csv`), reason `no_throughput`; NI premises are dropped with reason `out_of_scope_nation`; its test checks all three. Applied to task 17 above.
History: none

### F3: how many PRs the pilot takes
Finding: 3 (reality row `pr-count`), P2, confidence 8/10, "How the work is run" ("Each lane then works on its own branch off `fork/main` ... and opens its own PR to `main`"), reviewer Claude.
Plan baseline: original proposal: one PR for tasks 1 to 3, one per lane (5), and the integration work, about 8 PRs after #99.
Runtime evidence: no `.gstack/ship-policy.json`, so gstack's default is one PR per wave. Auto-merge is disabled on the fork (memory `comit-git-remotes-and-prs`), so each PR is a manual merge, and the fork takes no stacked PRs.
Comparison grid:

| Choice | Current | A | B |
|---|---|---|---|
| F3 PR granularity | one PR per lane, about 8 | one PR per phase: foundation (tasks 1-3), lanes (tasks 4-12, lane branches reviewed and merged by the primary session into `feat/ukis-lanes`), integration (tasks 13-19) | one PR per lane, as written |
| Manual merges by Alexandre | about 8 | 3 | about 8 |
| Size of the largest PR | one lane | all five lanes together | one lane |

Question D5:
D5 — One PR per lane, or one PR per phase?
Project/branch/task: docs/industrial-stock-plan, reviewing the branch and PR strategy of 04_implementation_plan.md.
ELI10: The plan opens a PR for every lane, about 8 in all, and each one needs you to merge it by hand because auto-merge is off on the fork. The alternative is one PR per phase: the foundation, then all five lanes together (the primary session reviews and merges each lane branch into a phase branch first), then the integration. That is 3 merges for you, but the lanes PR is large.
Stakes if we pick wrong: either 8 merge waits that stall the parallel lanes, or a lanes PR too big to review properly.
Recommendation: A because the primary session already reviews every lane before merging, your merge waits drop from about 8 to 3, and each phase still ends on a checkpoint you look at.
Note: options differ in kind, not coverage — no completeness score.
Pros / cons:
A) One PR per phase (recommended)
  ✅ 3 manual merges instead of about 8, each at a natural checkpoint (A, B or D)
  ✅ Lanes never wait on you to merge each other's work before integration starts
  ❌ The lanes PR carries tasks 4 to 12 at once, likely several thousand lines
B) One PR per lane, as written
  ✅ Each PR is one lane's work, small enough to read in one sitting
  ✅ A bad lane can be reverted on main without touching the others
  ❌ About 8 manual merges, and integration waits until all five lane PRs are merged
Net: fewer merges for you versus smaller PRs to read.
Header: PR count
Options:
A) One PR per phase (recommended)
Three PRs after #99: foundation (tasks 1-3), lanes (tasks 4-12, lane branches merged locally into feat/ukis-lanes after the primary session's review), integration (tasks 13-19). Each opens at its checkpoint.
B) One PR per lane
Keep the plan as written: a PR for tasks 1-3, one per lane, and the integration work, about 8 PRs, each merged by hand.

State: approved
Actual answer: A) One PR per phase (D5, 2026-11-08)
Accepted scope: three PRs after #99: foundation (tasks 1-3), lanes (tasks 4-12, lane branches merged locally into `feat/ukis-lanes` after the primary session's review), integration (tasks 13-19), each opened at its checkpoint. Applied to "How the work is run" above.
History: none

### F4: keeping restricted data out of the open build
Finding: 4, P1, confidence 8/10, Section 1 (architecture). 03 §2 principle 4 ("Columns derived from restricted sources ... live in a separate layer that joins by `building_id`. The released table can be rebuilt without them") and task 17 ("an `open` build drops every column whose source tier is `restricted`"), reviewer Claude.
Plan baseline: original proposal: one build that loads every source, then a filter at assembly drops restricted-derived columns.
Runtime evidence: unknown (no code). From the plan's own data flow, VOA records feed task 13's postcode assignment and SCU merges, task 14's evidence resolution (which lowers other sources' confidence when they disagree), task 15's floor areas and task 16's calibration scaling. Dropping columns at assembly leaves those effects in the open table: a building's open `carbe_group`, `scu_id` or calibrated energy can still have been decided by VOA data.
Comparison grid:

| Choice | Current | A | B |
|---|---|---|---|
| F4 how the open table is produced | one build, restricted columns dropped at assembly | two builds from the same code: `--tier open` never loads a restricted source (loaders refuse at load time), `--tier full` loads everything; only the open build's output is releasable | one build, as now, plus a per-row `voa_influenced` flag so a user can filter |
| Restricted influence in the released table | possible, undetectable | none by construction | possible, flagged |
| Pilot run time | one build | two builds (steps 2 to 4 and 7 shared, cached) | one build |
| Test | drop-columns test | a test that the open build's output is byte-identical whether or not restricted raw files exist on disk | flag test |

Question D6:
D6 — How should the pipeline keep VOA (restricted) data out of the releasable table?
Project/branch/task: docs/industrial-stock-plan, reviewing the licence-tier design behind tasks 11 and 17 of 04_implementation_plan.md.
ELI10: The plan runs everything together and deletes the VOA-derived columns at the end. But VOA data also steers decisions that leave no column behind: which building a premises is linked to, which buildings merge into one unit, which evidence wins a classification, how energy is scaled. Deleting columns cannot undo those, so the "open" file could still carry VOA's fingerprints. Running the pipeline twice, once without ever loading VOA, makes the open file clean by construction.
Stakes if we pick wrong: releasing an ODbL file that was shaped by data whose terms say an open licence does not apply.
Recommendation: A because it is the only option where the released table provably owes nothing to restricted data, and the shared early steps are cached so the second build is cheap.
Completeness: A=10/10, B=5/10
Pros / cons:
A) Two builds, open and full (recommended)
  ✅ The open table cannot contain VOA influence, and a test proves it byte for byte
  ✅ The full build still gives the best internal estimate for CaRB3 and validation
  ❌ Two outputs to keep apart, and the later steps run twice
B) One build with an influence flag
  ✅ One run and one set of outputs, simpler to operate
  ✅ Users see which rows VOA touched and can filter them
  ❌ The flag can miss indirect effects (calibration scales every building in an MSOA)
Net: a released table that is clean by construction versus one simpler run with a flag.
Header: Licence tiers
Options:
A) Two builds (recommended)
Add a `--tier open|full` build flag; in `open`, every loader with tier `restricted` refuses at load time; only open outputs are releasable; task 18 adds a test that the open build is byte-identical with and without the restricted raw files present. Task 17's drop-columns step stays as a second guard.
B) One build plus a flag
Keep one build; add a `voa_influenced` boolean per building set whenever a VOA record touched its linking, classification, floor area or MSOA calibration; task 17 keeps the drop-columns filter.

State: approved
Actual answer: A) Two builds (D6, 2026-11-08)
Accepted scope: a `--tier open|full` build flag; in `open`, every loader with tier `restricted` refuses at load time; only open outputs are releasable; task 18 adds a test that the open build is byte-identical with and without the restricted raw files present; task 17's drop-columns step stays as a second guard. Applied to tasks 2, 11, 17 and 18 above and to 03 §2.
History: none

### F5: where the raw data lives when five worktrees run at once
Finding: 5, P2, confidence 8/10, Section 1 (architecture). File map: "`.gitignore` | Ignores `data/`" and `paths.py` "Raw, interim and output directories from `config/pilot.toml`"; "How the work is run": each lane in "its own worktree under `.worktrees/<branch>`", reviewer Claude.
Plan baseline: original proposal: `data/` inside the project folder, so inside each checkout.
Runtime evidence: a git-ignored directory is per worktree, so each of the five lane worktrees plus the primary would download its own copy. The pilot needs the 2.0 GB Geofabrik GB extract, ONSUD (about 515 MB), OS Open UPRN, Linked Identifiers and Open TOID, and LiDAR for about 1,040 km² (DSM and DTM at 1 m, roughly 8 GB uncompressed) [estimated]. The machine has about 585 GB free (`df -h`). Two lanes fetching the same source at once could also race on one directory.
Comparison grid:

| Choice | Current | A | B |
|---|---|---|---|
| F5 raw data location | `<checkout>/uk_industrial_stock/data/raw`, one per worktree | one shared raw root outside every worktree, `UKIS_DATA_ROOT` (default `~/data/ukis`); fetched once by the primary session (`make fetch-pilot`) before the lanes start; lanes only read it; `ukis fetch` takes a lock file so two fetches cannot race | per worktree, as now |
| Interim and output | per checkout | per checkout, unchanged (`<checkout>/uk_industrial_stock/data/{interim,output}`) | per checkout |
| Copies of the raw data | up to 6 | 1 | up to 6 |

Question D7:
D7 — Where should the downloaded raw data live while five lane worktrees run?
Project/branch/task: docs/industrial-stock-plan, reviewing the data layout (task 2, `paths.py`) of 04_implementation_plan.md.
ELI10: Each lane runs in its own copy of the repository, and the plan keeps downloads inside the copy. That means up to six copies of the same 2 GB OSM file, the UPRN files and the LiDAR tiles, and two lanes could download the same file at the same moment. Keeping one shared download folder outside the repository, filled once before the lanes start, avoids both.
Stakes if we pick wrong: tens of GB of duplicate downloads and lanes stalled on fetching, or a corrupted file from two fetches at once.
Recommendation: A because the raw files never change once fetched, so one read-only copy is safe to share, while each lane keeps its own working outputs.
Completeness: A=9/10, B=6/10
Pros / cons:
A) One shared raw folder (recommended)
  ✅ Each source is downloaded once, before the lanes start, and checksummed once
  ✅ Lanes start on real data immediately instead of each fetching for an hour
  ❌ A folder outside the repo that each new machine has to set up via UKIS_DATA_ROOT
B) Per-worktree data, as written
  ✅ Each worktree is fully self-contained, with nothing outside the repo
  ✅ No environment variable to set
  ❌ Up to six copies of every download, and nothing stops two fetches racing
Net: one shared, read-only raw store versus fully self-contained worktrees.
Header: Data root
Options:
A) Shared raw folder (recommended)
`paths.py` reads `UKIS_DATA_ROOT` (default `~/data/ukis`) for raw data only; the primary session runs `make fetch-pilot` before the lanes start; `ukis fetch` holds a lock file per source; interim and output stay inside each checkout. Task 2 adds a test that two concurrent fetches of one source produce one directory.
B) Per-worktree data
Keep `data/` inside each checkout; each lane fetches the sources it needs.

State: approved
Actual answer: A) Shared raw folder (D7, 2026-11-08)
Accepted scope: `paths.py` reads `UKIS_DATA_ROOT` (default `~/data/ukis`) for raw data only; the primary session runs `make fetch-pilot` before the lanes start; `ukis fetch` holds a lock file per source; interim and output stay inside each checkout; task 2 adds a test that two concurrent fetches of one source produce one directory. Applied to the file map, the human steps, "How the work is run" and task 2 above.
History: none

### F6: linking needs a floor area that is only computed later
Finding: 6, P1, confidence 9/10, Section 2 (code quality). Task 13 "Change" ("the assignment solved by `scipy.optimize.linear_sum_assignment` on the absolute log ratio of areas") and its test ("candidate buildings in one postcode (2,100, 90, 380 m² geometric GIA)"); task 15 computes geometric GIA from storeys and "Depends on: tasks 12, 14"; task 14 "Depends on: tasks 7, 13"; the shed rule in task 15 needs "a class of `FA`, `WA` or `UT`", reviewer Claude.
Plan baseline: original proposal: task 13 assigns on geometric GIA.
Runtime evidence: the plan's dependency chain is circular: task 13 needs geometric GIA, which needs storeys (task 15), which need the class (task 14), which needs the links (task 13). As written, task 13 cannot run.
Comparison grid:

| Choice | Current | A | B |
|---|---|---|---|
| F6 the area task 13 assigns on | geometric GIA (not yet computed) | a class-free provisional GIA computed inside task 13: footprint × provisional storeys, where provisional storeys are 1 for a footprint over 500 m² with p90 height of 15 m or less, else p90 height ÷ 4.0 m rounded (minimum 1), and 1 where there is no height; stored as `gia_provisional_m2`; task 13 then depends on task 12 | footprint area only, ignoring storeys |
| Check that the provisional figure did not mislead | none | task 18 reports how many assignments would change if re-solved on task 15's final GIA | none |
| Multi-storey buildings | n/a | handled by height | understated, so large-area VOA records go to the wrong building |

Question D8:
D8 — What floor area should task 13 use to match VOA records to buildings, given the real one is computed later?
Project/branch/task: docs/industrial-stock-plan, reviewing task 13 (linking) and its dependencies in 04_implementation_plan.md.
ELI10: Task 13 matches each VOA record to a building by comparing floor areas. But the plan only computes a building's floor area in task 15, which needs the building's class, which needs task 13's links. That is a loop, so task 13 cannot run as written. The fix is a rough floor area worked out from footprint and height alone, which does not need the class.
Stakes if we pick wrong: a pipeline that cannot run, or VOA records attached to the wrong building in multi-storey works.
Recommendation: A because height-based storeys need no class, keep multi-storey buildings right, and task 18 measures whether the rough figure changed any match.
Completeness: A=10/10, B=6/10
Pros / cons:
A) Provisional floor area from height (recommended)
  ✅ Breaks the loop with a figure that still counts the floors of multi-storey buildings
  ✅ Task 18 reports how many matches the final floor area would change, so the shortcut is measured
  ❌ Task 13 now waits for task 12 (height), and the 4.0 m storey height is a guess until task 15 fits it
B) Footprint area only
  ✅ No dependency on height, so linking can start as soon as footprints exist
  ✅ Simplest rule, easy to explain
  ❌ A five-storey mill looks like a single shed, so large VOA records match the wrong building
Net: a height-aware rough area that waits for task 12 versus a simpler rule that misreads multi-storey sites.
Header: Linking area
Options:
A) Provisional area (recommended)
Task 13 computes `gia_provisional_m2` from footprint and LiDAR height without the class (1 storey for over 500 m² at p90 of 15 m or less, else p90 ÷ 4.0 m rounded, minimum 1, and 1 without height) and depends on task 12; task 18 reports how many assignments change when re-solved on task 15's final GIA.
B) Footprint only
Task 13 assigns on footprint area alone; no dependency on task 12.

State: approved
Actual answer: A) Provisional area (D8, 2026-11-08)
Accepted scope: task 13 computes `gia_provisional_m2` from footprint and LiDAR height without the class (1 storey for over 500 m² at p90 of 15 m or less, else p90 ÷ 4.0 m rounded, minimum 1, and 1 without height) and depends on task 12; task 18 reports how many assignments change when re-solved on task 15's final GIA. Applied to tasks 13 and 18 above.
History: none

### F7: failing loudly when an upstream file changes shape
Finding: 7, P2, confidence 7/10, Section 2 (code quality). Task 9 "Test first" (each fixture "loads into the `records` schema"), task 6 (only step 4 has "the step's exceptions file"), and task 3 (`io.write_table` "validates against the schema"), reviewer Claude.
Plan baseline: original proposal: schema validation on write; an exceptions file in step 4 only.
Runtime evidence: unknown (no code). These sources change their layouts between releases (the VOA publishes a new specification with each list; UK PRTR's preview showed 36 of 50 columns named; ONSUD's postcode column is already uncertain). A loader that maps a renamed column to null passes schema validation, because nullable columns accept nulls, and the loss is silent.
Comparison grid:

| Choice | Current | A | B |
|---|---|---|---|
| F7 missing or renamed source column | unspecified (likely silent nulls) | every loader declares its required source columns and raises naming the missing ones | unchanged |
| Rows a step cannot use | step 4 only writes an exceptions file | every step writes `exceptions/<step>.parquet` (`subject_id`, `reason`, `detail`) and task 18 reports counts per step and reason | unchanged |
| Test | none | one test per loader with a fixture missing a required column; one test that a step's dropped rows appear in its exceptions file | none |

Question D9:
D9 — Should every loader and step fail loudly and log the rows it drops?
Project/branch/task: docs/industrial-stock-plan, reviewing error handling across tasks 4 to 16 of 04_implementation_plan.md.
ELI10: Government data files change their column names between releases. If a loader quietly reads a renamed column as empty, the pipeline still runs and the output just has holes nobody notices. The fix is for each loader to list the columns it needs and stop with a clear message if one is missing, and for every step to write the rows it had to drop, with the reason, to a file the validation report counts.
Stakes if we pick wrong: a pilot whose activity or floor-area columns are quietly half empty because one upstream file changed.
Recommendation: A because a missing column is then an error with its name in it, and every dropped row is counted in the validation report instead of vanishing.
Completeness: A=10/10, B=4/10
Pros / cons:
A) Loud loaders and exception files (recommended)
  ✅ A renamed upstream column stops the run with the column's name, not hours later as holes
  ✅ Every dropped row is counted by step and reason in the validation report
  ❌ Each loader needs its required-column list kept in step with the source's specification
B) Leave as written
  ✅ No extra lists to maintain in each loader
  ✅ Fewer tests to write
  ❌ Schema checks accept nulls, so a renamed column passes silently
Net: explicit failure and an audit trail versus less code to maintain.
Header: Loud failure
Options:
A) Loud failure (recommended)
Every loader declares its required source columns and raises naming any that are missing; every step writes `exceptions/<step>.parquet` (`subject_id`, `reason`, `detail`); task 18 reports counts per step and reason; each loader gets a missing-column test and each step a dropped-rows test.
B) Leave as written
Schema validation on write only; step 4 keeps its exceptions file; nothing else changes.

State: approved
Actual answer: A) Loud failure (D9, 2026-11-08)
Accepted scope: every loader declares its required source columns and raises naming any that are missing; every step writes `exceptions/<step>.parquet` (`subject_id`, `reason`, `detail`); task 18 reports counts per step and reason; each loader gets a missing-column test and each step a dropped-rows test. Applied to "How the work is run" and tasks 3, 9 and 18 above.
History: none

### F8: no end-to-end test across the lanes
Finding: 8, P1, confidence 8/10, Section 3 (tests). Every task's tests are per step ("Test first" in tasks 4 to 17); task 18's determinism check "runs the build twice on a fixture area" but no task builds that fixture area; "Interim schemas (fixed in task 3)" is the only contract between lanes, reviewer Claude.
Plan baseline: original proposal: unit tests per step, then a real pilot run per step.
Runtime evidence: unknown (no code). Five lanes code against `schemas.py` in parallel; a column one lane writes with the wrong meaning (metres for a field read as m², a null where another step expects a value) passes both lanes' unit tests and first fails on the real pilot run, after the lanes have merged.
Comparison grid:

| Choice | Current | A | B |
|---|---|---|---|
| F8 cross-step test | none | `tests/fixtures/area_mini/` (task 3b, built by a script in the repo): about 12 footprints, 30 UPRNs, 15 records across sources, two MSOAs, a tiny DSM/DTM, all synthetic; `tests/test_e2e.py` runs steps 2 to 10 on it in both tiers and asserts named values on 4 known buildings (class, storeys, GIA, energy method) | rely on the real pilot runs after merge |
| Who owns the fixture | n/a | primary session, task 3b, before the lanes start; each lane extends it only through the primary | n/a |
| Task 18's determinism and licence checks | need a fixture area that no task builds | run on `area_mini` | still need one |

Question D10:
D10 — Add a small synthetic area that runs the whole pipeline end to end in the tests?
Project/branch/task: docs/industrial-stock-plan, reviewing test coverage across tasks 3 to 18 of 04_implementation_plan.md.
ELI10: Each step has its own tests, but nothing tests the steps together. Five lanes write code at the same time against shared table definitions, so one lane can write a column another reads the wrong way, and both pass their own tests. A tiny made-up area (a dozen buildings, a few addresses and records) run through every step catches that in seconds. Task 18 already assumes such an area exists, but no task builds it.
Stakes if we pick wrong: lane mismatches found only on the real pilot run after merging, or task 18's checks with nothing to run on.
Recommendation: A because it is the only test that catches mismatches between lanes before merge, and task 18 needs it anyway.
Completeness: A=10/10, B=5/10
Pros / cons:
A) Synthetic end-to-end area (recommended)
  ✅ Catches column-meaning mismatches between lanes in seconds, before any merge
  ✅ Gives task 18's determinism and licence checks the fixture area they assume
  ❌ A fixture of a dozen buildings and their records to keep in step as schemas change
B) Real pilot runs only
  ✅ No synthetic fixture to build or maintain
  ✅ Real data finds problems synthetic data will not think of
  ❌ Mismatches surface only after the lanes merge, and task 18 has no fixture area
Net: an early cross-lane safety net versus less fixture upkeep.
Header: E2E test
Options:
A) Synthetic area (recommended)
Add task 3b (primary session, before lanes): `tests/fixtures/area_mini/` built by `tests/fixtures/make_area_mini.py`, about 12 footprints, 30 UPRNs, 15 records, two MSOAs, tiny DSM/DTM; `tests/test_e2e.py` runs steps 2 to 10 in both tiers and asserts class, storeys, GIA and energy method on 4 named buildings; task 18's checks run on it.
B) Real runs only
No fixture area; lanes rely on unit tests and real pilot runs; task 18's determinism check runs on the real pilot output instead.

State: approved
Actual answer: A) Synthetic area (D10, 2026-11-08)
Accepted scope: task 3b (primary session, before lanes) builds `tests/fixtures/area_mini/` with `tests/fixtures/make_area_mini.py` (about 12 footprints, 30 UPRNs, 15 records, two MSOAs, tiny DSM/DTM); `tests/test_e2e.py` runs steps 2 to 10 in both tiers and asserts class, storeys, GIA and energy method on 4 named buildings; task 18's checks run on it. Applied as task 3b above.
History: none

### F9: an interrupted download looks like a finished one
Finding: 9, P2, confidence 7/10, Section 3 (tests: user flow `ukis fetch`). Task 2 "Change" ("`ukis fetch <id>` downloads into a new directory ... never overwriting"), reviewer Claude.
Plan baseline: original proposal: download into a new vintage directory and record the checksum.
Runtime evidence: unknown (no code). A 2 GB download that drops halfway leaves a vintage directory holding a truncated file. Since fetch never overwrites, the next run either skips the source (directory exists) or creates a second vintage, and a step reading "the latest vintage" may read the truncated one.
Comparison grid:

| Choice | Current | A | B |
|---|---|---|---|
| F9 download atomicity | write straight into the vintage directory | download to `<raw>/.partial/<id>-<random>/`, verify size and SHA-256, then rename into the vintage directory in one step; a failed or interrupted fetch leaves no vintage directory and is retried from scratch | unchanged |
| Steps reading a source | "latest vintage" | only vintages listed in `manifest.lock.json` | unchanged |
| Test | none | a fake downloader that raises halfway leaves no vintage directory and no lock entry; a second fetch then succeeds | none |

Question D11:
D11 — Should a fetch only become visible once the whole file has arrived and checked out?
Project/branch/task: docs/industrial-stock-plan, reviewing task 2 (`ukis fetch`) of 04_implementation_plan.md.
ELI10: Several sources are gigabytes. If the network drops halfway, the plan as written leaves a half file in the folder where finished downloads live, and later steps could read it as if it were complete. Downloading into a temporary folder and moving it into place only after the checksum passes means a half file can never be mistaken for a real one.
Stakes if we pick wrong: a pilot built on a truncated OSM or UPRN file, with errors far from their cause.
Recommendation: A because it costs a temporary folder and one rename, and makes a truncated input impossible to read.
Completeness: A=10/10, B=5/10
Pros / cons:
A) Download, verify, then move (recommended)
  ✅ A half-finished download can never be read by any step
  ✅ Steps read only vintages recorded in the lock file, so what was used is always known
  ❌ A crash leaves a `.partial/` folder behind that the next fetch has to clear first
B) Leave as written
  ✅ Simplest fetcher, one write path
  ✅ No temporary folder to clean up after crashes
  ❌ A dropped connection leaves a truncated file that later steps may read
Net: a fetch that is all-or-nothing versus the simplest fetcher.
Header: Atomic fetch
Options:
A) Atomic fetch (recommended)
Task 2 downloads to `<raw>/.partial/<id>-<random>/`, checks size and SHA-256, then renames into the vintage directory; steps read only vintages listed in `manifest.lock.json`; a test with a downloader that fails halfway expects no vintage directory and no lock entry, then a clean second fetch.
B) Leave as written
Fetch writes straight into the vintage directory; no change.

State: approved
Actual answer: A) Atomic fetch (D11, 2026-11-08)
Accepted scope: task 2 downloads to `<raw>/.partial/<id>-<random>/`, checks size and SHA-256, then renames into the vintage directory; steps read only vintages listed in `manifest.lock.json`; a test with a downloader that fails halfway expects no vintage directory and no lock entry, then a clean second fetch. Applied to task 2 above.
History: none

### F10: the regression contract for adding this project to `make check`
Finding: 10, P2, confidence 8/10, Section 3 (regression rule). Task 1 "Change" ("Add a `ukis` target to the root `Makefile` ... and make `check` depend on it"); root `Makefile:30` (`check: docs-check data-check carb3`); `tools/quality_gate.sh` runs `make check` on every pre-push, reviewer Claude.
Plan baseline: original proposal: `check` gains a `ukis` dependency; task 1 verifies with `bash ../tools/quality_gate.sh`.
Runtime evidence: `make check` currently runs docs-check, data-check and the carb3 suite (379 tests in 89.93 s on this branch, run earlier today). Every session in this repo pushes through it. The first `uv run` of the new project downloads its geospatial wheels (rasterio, pyogrio and duckdb all ship native libraries).
Comparison grid:

| Choice | Current | A | B |
|---|---|---|---|
| F10 `ukis` in the pre-push gate | not present | in `check`, always | in `check` only when the pushed commits touch `uk_industrial_stock/` (a path test in `tools/quality_gate.sh`), otherwise skipped with a printed line |
| Preserved behaviour (both options) | | docs-check, data-check and carb3 still run first and still block; the gate still passes on a clean clone | same |
| Acceptance assertions (both options) | | `bash tools/quality_gate.sh` passes from the root; its output names the ukis test count; ukis tests make no network call (sockets blocked in `conftest.py`); the ukis suite finishes in under 60 s | same, plus a push that touches only `carb3/` prints "ukis: skipped" |

Question D12:
D12 — How should this project's tests join the pre-push gate every session in the repo uses?
Project/branch/task: docs/industrial-stock-plan, reviewing task 1's change to the root Makefile in 04_implementation_plan.md.
ELI10: Every push from this repo runs `make check`, which today takes about a minute and a half. Task 1 adds this project's tests to it, which protects this project but also makes every other session's push wait for it, and the first run downloads its mapping libraries. Either it always runs, or it runs only when a push touches this project's folder. Both options keep the existing checks running first and add the same pass conditions.
Stakes if we pick wrong: slower pushes for unrelated carb3 work, or this project's tests skipped on a push that did change it.
Recommendation: A because it is one line in the Makefile with no path logic to get wrong, and the 60-second cap keeps it cheap.
Completeness: A=9/10, B=8/10
Pros / cons:
A) Always run (recommended)
  ✅ No path logic that could skip the tests on a push that needed them
  ✅ One Makefile line, like the existing carb3 target
  ❌ Every push in the repo pays up to 60 s more, plus a one-off wheel download
B) Run only when the folder changes
  ✅ carb3 and spec pushes stay as fast as today
  ✅ The gate still runs this project's tests whenever its files change
  ❌ A path test in quality_gate.sh that has to compute the pushed range correctly
Net: simplest always-on gate versus faster pushes for unrelated work.
Header: Gate scope
Options:
A) Always run (recommended)
`check: docs-check data-check carb3 ukis`; existing targets still run first and block; acceptance: the gate passes from the root, prints the ukis test count, ukis tests block sockets in `conftest.py`, and the suite finishes in under 60 s.
B) Only when touched
`tools/quality_gate.sh` runs `make ukis` only when the pushed commits touch `uk_industrial_stock/`, printing "ukis: skipped" otherwise; same acceptance assertions, plus a carb3-only push prints the skip line.

State: approved
Actual answer: A) Always run (D12, 2026-11-08)
Accepted scope: `check: docs-check data-check carb3 ukis`; existing targets still run first and block; acceptance: the gate passes from the root, prints the ukis test count, ukis tests block sockets in `conftest.py`, and the suite finishes in under 60 s. Applied to task 1 above.
History: none

### F11: the pilot reads the whole GB extract to get two authorities
Finding: 11, P2, confidence 8/10, Section 4 (performance). Task 2 source list ("Geofabrik GB") and task 4 "Change" ("QuackOSM with a tag filter ... and the pilot polygon as geometry filter"), reviewer Claude.
Plan baseline: original proposal: fetch the 2.0 GB Great Britain extract and clip it to the pilot.
Runtime evidence: Geofabrik publishes a Lincolnshire extract, `europe/united-kingdom/england/lincolnshire-latest.osm.pbf`, 43,293,361 bytes (`curl -sIL`, today), against 2.0 GB for Great Britain. Lincolnshire as Geofabrik cuts it is expected to include North and North East Lincolnshire, but that is not yet checked [unverified]. QuackOSM with a geometry filter still has to scan the whole input file, and the pyrosm benchmarks show QuackOSM's memory growing with file size.
Comparison grid:

| Choice | Current | A | B |
|---|---|---|---|
| F11 OSM input for the pilot | GB extract, 2.0 GB | Lincolnshire extract, about 43 MB, with a test-before-use check that its bounding box covers the buffered pilot polygon (raises if not); GB extract added at milestone 2 | GB extract, as now |
| Run time and memory for task 4 on the pilot | the whole GB file is scanned | about 2% of the bytes [estimated from file sizes] | unchanged |
| Same code path at scale-out | yes | yes; only the source id changes | yes |

Question D13:
D13 — Should the pilot read the Lincolnshire OSM extract instead of the whole of Great Britain?
Project/branch/task: docs/industrial-stock-plan, reviewing tasks 2 and 4 (the OSM extract) of 04_implementation_plan.md.
ELI10: The pilot covers two councils, but the plan downloads and scans the 2 GB file for all of Great Britain to find them. Geofabrik also publishes a 43 MB Lincolnshire file, which should contain both councils. Using it makes the OSM step and every rerun about fifty times lighter, and the code is the same: only which file it reads changes. A check confirms the smaller file really covers the pilot before it is used.
Stakes if we pick wrong: slow, memory-hungry reruns of task 4 throughout the pilot, or a smaller file that misses part of the pilot area if the coverage check is skipped.
Recommendation: A because it cuts the input by about 98% with no code difference, and the coverage check turns a wrong boundary into an error instead of missing buildings.
Completeness: A=9/10, B=8/10
Pros / cons:
A) Lincolnshire extract with a coverage check (recommended)
  ✅ 43 MB instead of 2.0 GB to fetch and scan on every pilot rerun
  ✅ The coverage check stops the run if the extract misses any part of the pilot
  ❌ One more source entry, and milestone 2 must switch the source to the GB extract
B) GB extract, as written
  ✅ One OSM source from the pilot through to scale-out
  ✅ No dependency on how Geofabrik draws its county boundary
  ❌ Each rerun of task 4 scans 2.0 GB to keep about 2% of it
Net: a much lighter pilot input with a guard versus one source throughout.
Header: OSM extract
Options:
A) Lincolnshire extract (recommended)
Task 2 adds source `geofabrik_lincolnshire` and the pilot uses it; task 4 first checks that the extract's bounding box covers the buffered pilot polygon and raises if not; the GB extract is added at milestone 2.
B) GB extract
Keep the Great Britain extract for the pilot, clipped by QuackOSM's geometry filter.

State: approved
Actual answer: A) Lincolnshire extract (D13, 2026-11-08)
Accepted scope: task 2 adds source `geofabrik_lincolnshire` and the pilot uses it; task 4 first checks that the extract's bounding box covers the buffered pilot polygon and raises if not; the GB extract is added at milestone 2. Applied to tasks 2 and 4 above.
History: none

### Outside voice (Claude subagent, native fallback)

Codex was unavailable (`gpt-6-astra` is not supported on this ChatGPT account; fix with
`gstack-config set model_frontier_openai <model-id>`). A native Claude Plan subagent ran
the independent challenge within the five-minute bound and returned 16 findings, numbered
O1 to O16 here. The parent verified O1 (`carb3/src/carb3/load.py:148-179` lists five
premise tables and `load.py:304` raises "no such table"), O2
(`activity_process_duty_profile.csv` has no mass carrier in its `carrier_id` column; the
exportable mass products in `carrier.csv` are cement, lime, hvc, ammonia, steel_hot_rolled,
glass, paper_basic, petroleum_products and aluminium) and O3 (the crosswalk's 55 names all
match `activity_process_register.csv` exactly, so Table 28 names need the same check).

### O16: a VOA match-feasibility spike before the lanes
Finding: outside voice 16, High (strategic), confidence 7/10, reviewer Claude subagent. "How the work is run" and checkpoint B (the 60% VOA match gate sits after task 13, after all five lanes).
Plan baseline: no spike; the VOA match rate is first measured at checkpoint B.
Runtime evidence: unknown until measured. The pilot's go or no-go turns on whether VOA records reach buildings (03 §7: "if the VOA-to-building match rate is too low ... the release falls back to group-level classification").
Comparison grid:

| Choice | Current | A Include | B Defer | C Cut |
|---|---|---|---|---|
| O16 spike (candidate scope) | not in plan | task 0, run alongside tasks 1 to 3: a throwaway script in `spikes/voa_match/` (not package code) that loads the VOA list, OS Open UPRN, ONSUD and the EPC records for the two pilot authorities, and reports VOA records per LAD, candidate buildings per VOA postcode (from OS OpenMap Local footprints), the share of VOA records whose address matches an EPC record carrying a UPRN, and a match rate on those as ground truth; written up as `docs/05_voa_match_spike.md`; checkpoint A then confirms or revises task 13's design and the records lane's VOA work before the lanes start | not run now; the spike script is written only if checkpoint B finds a match rate under 60% | never run; checkpoint B as written |
| Gate on the lanes | checkpoint A | checkpoint A plus the spike note | checkpoint A | checkpoint A |

Question D14:
D14 — Measure VOA-to-building matching in a quick spike before building the lanes?
Project/branch/task: docs/industrial-stock-plan, outside-voice finding O16 on the order of work in 04_implementation_plan.md.
ELI10: The pilot's big question is whether VOA records can be matched to buildings at all from open data. The plan only finds out at checkpoint B, after five lanes and about 28 modules are built. A throwaway script on the two councils' VOA, UPRN, ONSUD and EPC data could answer it in about a day, alongside the foundation tasks, and change the linking design before anyone writes it.
Stakes if we pick wrong: the lanes and the linking code built around a match rate that turns out too low to use.
Recommendation: A because it answers the pilot's decisive question for the price of one throwaway script, before the expensive work starts.
Note: options differ in kind, not coverage — no completeness score.
Pros / cons:
A) Include the spike as task 0
  ✅ The decisive number arrives before the lanes start, not after they merge
  ✅ Gives task 13 a measured candidate-set size and a ground-truth sample to design against
  ❌ Needs Human 1 and Human 2 (VOA and EPC downloads) done before checkpoint A
B) Defer to checkpoint B
  ✅ No extra task now, and the foundation is not held up by the human downloads
  ✅ The spike is still there to diagnose a low match rate if checkpoint B finds one
  ❌ The answer comes after all five lanes are built
C) Cut
  ✅ Least work, and nothing waits on the VOA download
  ✅ Checkpoint B's existing 60% gate still stops the pilot if matching fails
  ❌ No early signal and no diagnostic tool if the match rate is low
D) Hold
  ✅ No cons — this is a hard-stop choice
Net: one day's throwaway measurement up front versus finding out after the lanes.
Header: VOA spike
Options:
A) Include
Add task 0 (primary session, alongside tasks 1 to 3): a throwaway script in `spikes/voa_match/` measuring VOA records per LAD, candidate buildings per VOA postcode, the share of VOA records with an EPC address match carrying a UPRN, and the match rate against that ground truth; written up as `docs/05_voa_match_spike.md`; checkpoint A reviews it before the lanes start.
B) Defer
Not run now; the VOA match rate is first measured at checkpoint B after task 13, and the spike script is written only if that rate is under 60%.
C) Cut
No spike at any point; checkpoint B stays as written.
D) Hold
Stop and discuss the order of work before deciding.

State: approved
Actual answer: A) Include (D14, 2026-11-08)
Accepted scope: task 0 (primary session, alongside tasks 1 to 3): a throwaway script in `spikes/voa_match/` measuring VOA records per LAD, candidate buildings per VOA postcode, the share of VOA records with an EPC address match carrying a UPRN, and the match rate against that ground truth; written up as `docs/05_voa_match_spike.md`; checkpoint A reviews it before the lanes start. Applied as task 0 and to checkpoint A above.
History: none

### O2: where the list of mass-duty premises comes from (reopens D4)
Finding: outside voice 2, Critical, confidence 9/10 (verified), reviewer Claude subagent. D4's accepted scope ("`carb3/exceptions.csv` naming every exported premise whose activity has a mass duty (read from `activity_process_duty_profile.csv`)").
Plan baseline: D4 approved: the mass-duty list is read from `activity_process_duty_profile.csv`.
Runtime evidence: that file's `carrier_id` column holds only service and heat carriers (motive_power 220 rows, cooling_0_15 62, electric_service 58, heat_60_100 39 and so on); no row names a mass product. So D4's list is always empty and its test passes vacuously. In `carrier.csv`, the exportable mass products are cement, lime, hvc, ammonia, steel_hot_rolled, glass, paper_basic, petroleum_products and aluminium (`may_export` TRUE, `denominator_kind` mass; `co2_captured` is also one but is not a duty). Probe of option A's rule on today's tables (a stdlib Python join over `unit_input_output.csv` and `unit_eligibility.csv`): 21 units, and 7 activities: Aluminium Smelting Works, Cement Works, Chemical Works, Industrial Minerals NEC, Iron and/or Steel Works, Oil refinery, gas processing etc, and Paper Mill. Reason for reopening: contradictory evidence against the approved source.
Comparison grid:

| Choice | Current (D4) | A Apply | B Keep | C Investigate | D Defer |
|---|---|---|---|---|---|
| O2 source of the mass-duty list | `activity_process_duty_profile.csv` (always empty) | an activity is mass-duty if any unit eligible for it in `unit_eligibility.csv` has a `primary_output` row in `unit_input_output.csv` on a carrier with `may_export` TRUE and `denominator_kind` mass, excluding `co2_captured`; the rule lives in task 17 and its test uses a cement works fixture that must appear in the list | unchanged | the task 0 spike computes the list under the rule in A and reports it at checkpoint A; task 17's source stays pending | unresolved |
| Rest of D4 (empty `premise_throughput`, NI dropped) | approved | unchanged | unchanged | unchanged | unchanged |

Question D15:
D15 — Where should the export's list of premises that need a throughput figure come from?
Project/branch/task: docs/industrial-stock-plan, outside-voice finding O2, reopening D4 (task 17's CaRB3 export).
ELI10: D4 said the export lists every premise whose activity needs a physical output figure (a cement works' tonnes of cement), reading that from carb3's duty profile. But that file only lists energy services, so the list would always come out empty and cement works would go out silently without their duty. The products that are real mass duties (cement, lime, steel, glass, paper, ammonia, aluminium and so on) are marked in `carrier.csv`, so the rule can come from which units an activity is allowed to run.
Stakes if we pick wrong: cement, steel and refinery premises exported without their main duty, with a test that cannot catch it.
Recommendation: A because it uses the carb3 tables' own markers for an exportable mass product, and the cement fixture makes the test fail if the list comes out empty.
Note: options differ in kind, not coverage — no completeness score.
Pros / cons:
A) Apply the unit-output rule
  ✅ Reads the mass products straight from carb3's carrier and unit tables, so it tracks them
  ✅ A cement fixture that must appear makes an empty list a test failure
  ❌ A three-table join (eligibility, unit outputs, carriers) to keep in step with carb3 data
B) Keep D4 as approved
  ✅ No change to the approved task 17
  ✅ Simplest source, one file
  ❌ The list is always empty, so the exceptions file never names a premise
C) Investigate in the spike
  ✅ Sees the list on real pilot premises before committing to the rule
  ✅ Costs nothing extra, since task 0 already loads the activities
  ❌ Task 17's source stays undecided until checkpoint A
D) Defer this change
  ✅ No cons — this is a hard-stop choice
Net: a rule that actually finds mass-duty premises versus keeping a source known to be empty.
Header: Mass duties
Options:
A) Apply this change
Task 17 marks an activity mass-duty when any unit eligible for it in `unit_eligibility.csv` has a `primary_output` row on a carrier with `may_export` TRUE and `denominator_kind` mass, excluding `co2_captured`; its test uses a cement works fixture that must appear in `carb3/exceptions.csv`. The rest of D4 is unchanged.
B) Keep this row's current value
Task 17 keeps reading `activity_process_duty_profile.csv`; the rest of D4 is unchanged.
C) Investigate before choosing
Task 0 computes the list under the rule in A for the pilot premises and reports it at checkpoint A; task 17's source stays pending; the rest of D4 is unchanged.
D) Defer this proposed change only
Leave the source unresolved and carry it as an open decision; the rest of D4 is unchanged.

State: approved
Actual answer: A) Apply this change (D15, 2026-11-08)
Accepted scope: task 17 marks an activity mass-duty when any unit eligible for it in `unit_eligibility.csv` has a `primary_output` row on a carrier with `may_export` TRUE and `denominator_kind` mass, excluding `co2_captured`; its test uses a cement works fixture that must appear in `carb3/exceptions.csv`. The rest of D4 is unchanged. Applied to task 17 above.
History: D4 (2026-11-08) approved `activity_process_duty_profile.csv` as the source; reopened by O2 with the carrier evidence above.

### O6: which buildings are candidates for a VOA record
Finding: outside voice 6, High, confidence 8/10, reviewer Claude subagent. Task 13 "Change" ("solved ... per postcode") and task 6 ("whether ONSUD has a postcode column is detected from the header, not assumed").
Plan baseline: original proposal: candidates are the buildings in the VOA record's postcode; how a building gets a postcode is not stated.
Runtime evidence: OS Open UPRN carries no postcode; whether ONSUD does is unknown; EPC records carry a postcode and sometimes a UPRN; Code-Point Open gives a centroid per postcode. So without a defined rule the candidate set for the main matcher may be empty or undefined.
Comparison grid:

| Choice | Current | A Apply | B Keep | C Investigate | D Defer |
|---|---|---|---|---|---|
| O6 candidate buildings for a VOA record | "the postcode", undefined | the union of (i) buildings holding a UPRN whose postcode (from an EPC record, or ONSUD if it has one) equals the VOA postcode and (ii) buildings within 250 m of the postcode's Code-Point Open centroid inside the same industrial land-use or site polygon; each candidate records which rule admitted it | unchanged | task 0 measures candidate counts and ground-truth hit rate under rule (i) alone, (ii) alone and their union at 100, 250 and 500 m, and checkpoint A picks the rule; task 13's candidate rule stays pending until then | unresolved |

Question D16:
D16 — How should task 13 decide which buildings can receive a VOA record?
Project/branch/task: docs/industrial-stock-plan, outside-voice finding O6 on task 13 (linking).
ELI10: Task 13 matches each VOA record to one of the buildings in its postcode, but open data never says which postcode a building is in: UPRN points carry none, and ONSUD may not either. Two workable rules exist: buildings with an address in that postcode (via EPC records), and buildings near the postcode's centre point inside the same industrial estate. The spike already loads all of this, so it can measure which rule finds the right building most often before task 13 is written.
Stakes if we pick wrong: a matcher with no candidates for most records, or one so loose it matches records to the wrong estate.
Recommendation: C because task 0 already loads the data, so measuring both rules and three radii costs little and lets checkpoint A pick the rule from numbers.
Note: options differ in kind, not coverage — no completeness score.
Pros / cons:
A) Apply the union rule now
  ✅ Task 13 has a defined candidate set today, with each candidate's admitting rule recorded
  ✅ Covers both buildings with addresses and unaddressed sheds on the same estate
  ❌ The 250 m radius is a guess with no measurement behind it
B) Keep as written
  ✅ No change to task 13
  ✅ Leaves the rule to whoever implements linking
  ❌ The candidate set stays undefined, which blocks task 13
C) Investigate in the spike
  ✅ Picks the rule and radius from measured hit rates on ground-truth records
  ✅ Costs one extra report in task 0, which already loads these tables
  ❌ Task 13's candidate rule waits for checkpoint A
D) Defer this change
  ✅ No cons — this is a hard-stop choice
Net: a rule chosen from measurements at checkpoint A versus a reasonable guess now.
Header: Candidates
Options:
A) Apply this change
Task 13's candidates are the union of buildings holding a UPRN whose EPC or ONSUD postcode equals the VOA postcode, and buildings within 250 m of the postcode's Code-Point Open centroid inside the same industrial land-use or site polygon; each candidate records the rule that admitted it.
B) Keep this row's current value
Task 13 says "per postcode" with no rule for a building's postcode.
C) Investigate before choosing
Task 0 reports candidate counts and ground-truth hit rates for rule (i), rule (ii) and their union at 100, 250 and 500 m; checkpoint A picks the rule; task 13's candidate rule stays pending until then.
D) Defer this proposed change only
Leave the candidate rule unresolved and carry it as an open decision.

State: approved (investigation only; the candidate rule itself stays pending until checkpoint A)
Actual answer: C) Investigate before choosing (D16, 2026-11-08). The native question listed C first; the labels and descriptions were otherwise the saved ones.
Accepted scope: task 0 reports candidate counts and ground-truth hit rates for rule (i), rule (ii) and their union at 100, 250 and 500 m; checkpoint A picks the rule; task 13's candidate rule stays pending until then. Applied to tasks 0 and 13 above.
History: none

### O7: checkpoint B measures how many links exist, not how many are right
Finding: outside voice 7, High, confidence 8/10, reviewer Claude subagent. Checkpoint B ("If VOA records reach buildings for under 60% of Factory-class floor area, stop") and task 19 (the hand check covers activity only).
Plan baseline: original proposal: checkpoint B gates on coverage; no link-accuracy measure.
Runtime evidence: `linear_sum_assignment` assigns every record whenever its postcode has at least one candidate, so coverage rises with looser candidate rules whether or not the links are right. VOA records whose address matches an EPC record carrying a UPRN have a known building (through the UPRN's TOID point), which is a ground-truth sample task 0 already builds (D14, D16).
Comparison grid:

| Choice | Current | A Apply | B Keep | C Investigate | D Defer |
|---|---|---|---|---|---|
| O7 link accuracy | not measured | task 18 holds out the ground-truth VOA records (EPC-UPRN matched) from the assignment, links them by the normal rules, and reports the share placed in the right building; checkpoint B stops if coverage is under 60% of Factory floor area **or** accuracy on the hold-out is under 80% [estimated threshold, revisited with task 0's numbers] | coverage only | task 0 reports accuracy on its sample; checkpoint B unchanged | unresolved |

Question D17:
D17 — Should checkpoint B also require the links to be right, measured on records whose building is known?
Project/branch/task: docs/industrial-stock-plan, outside-voice finding O7 on checkpoint B and task 18.
ELI10: Checkpoint B asks whether VOA records reached buildings for at least 60% of factory floor area. But the matcher puts every record somewhere as long as its postcode has a building, so a high number can hide many wrong matches. Some VOA records can be tied to their exact building through an EPC record with a UPRN. Hiding those from the matcher, then checking where it puts them, measures how often links are right.
Stakes if we pick wrong: a pilot that passes checkpoint B with confidently wrong activities and floor areas on many buildings.
Recommendation: A because a coverage gate alone rewards loose matching, and the ground-truth sample already exists from task 0.
Completeness: A=10/10, B=5/10, C=7/10
Pros / cons:
A) Accuracy gate at checkpoint B
  ✅ Checkpoint B stops on wrong links, not only on missing ones
  ✅ Reuses task 0's ground-truth records, so no new data is needed
  ❌ The ground-truth records (those with EPCs) may be easier to match than the rest
B) Coverage only, as written
  ✅ No change to task 18 or checkpoint B
  ✅ One number to read at checkpoint B
  ❌ A loose candidate rule inflates the gate's number with wrong links
C) Measure in the spike only
  ✅ An early accuracy number at checkpoint A
  ✅ No change to the pipeline's validation
  ❌ The real pipeline's linking is never checked for accuracy
D) Defer this change
  ✅ No cons — this is a hard-stop choice
Net: a gate that checks links are right versus one that only counts them.
Header: Link accuracy
Options:
A) Apply this change
Task 18 holds out the EPC-UPRN-matched VOA records, links them by the normal rules, and reports the share placed in the right building; checkpoint B stops if coverage is under 60% of Factory floor area or hold-out accuracy is under 80% (threshold revisited with task 0's numbers).
B) Keep this row's current value
Checkpoint B gates on coverage only; task 18 adds nothing.
C) Investigate before choosing
Task 0 reports accuracy on its ground-truth sample at checkpoint A; checkpoint B and task 18 stay as written.
D) Defer this proposed change only
Leave link accuracy unmeasured and carry it as an open decision.

State: approved
Actual answer: A) Apply this change (D17, 2026-11-08)
Accepted scope: task 18 holds out the EPC-UPRN-matched VOA records, links them by the normal rules, and reports the share placed in the right building; checkpoint B stops if coverage is under 60% of Factory floor area or hold-out accuracy is under 80% (threshold revisited with task 0's numbers). Applied to task 13 (the hold-out is first computed in its pilot run, so checkpoint B can read it) and task 18 above.
History: none

### O13: the 60-second bound on the gate (reopens D12)
Finding: outside voice 13, Medium, confidence 7/10, reviewer Claude subagent. D12's accepted scope ("the suite finishes in under 60 s") against D10 (end-to-end in both tiers), D6 (the licence test builds twice) and task 18 (the determinism test builds twice), all in the same suite.
Plan baseline: D12 approved: `ukis` always in `check`, whole suite under 60 s.
Runtime evidence: unknown (no code). The suite as now specified runs at least five whole-pipeline builds on `area_mini` (end-to-end in two tiers, determinism twice, licence twice), each starting DuckDB with the spatial extension and QuackOSM. Whether five such builds fit in 60 s on this machine is unmeasured. Reason for reopening: later approved choices (D6, D10) added work that D12's bound did not account for.
Comparison grid:

| Choice | Current (D12) | A Apply | B Keep | C Investigate | D Defer |
|---|---|---|---|---|---|
| O13 what the pre-push gate runs | the whole ukis suite, under 60 s | unit tests plus one end-to-end build in the `open` tier, under 60 s; the whole-pipeline repeats (`full`-tier end-to-end, determinism, licence) are marked `slow`, excluded from the gate with `-m "not slow"`, and run in full at every phase PR and by `make ukis-all` | unchanged | task 3b times the whole suite on `area_mini` and checkpoint A decides; D12 stays as approved until then | unresolved |
| Rest of D12 (always in `check`, sockets blocked, test count printed) | approved | unchanged | unchanged | unchanged | unchanged |

Question D18:
D18 — Should the pre-push gate run only the fast tests, with the repeated whole-pipeline builds kept for phase PRs?
Project/branch/task: docs/industrial-stock-plan, outside-voice finding O13, reopening D12 (the pre-push gate).
ELI10: D12 promised that this project's tests add under a minute to every push in the repo. Since then, D6 and D10 added tests that run the whole pipeline five times over on the made-up area. That may not fit in a minute, and every carb3 push would pay for it. Keeping the unit tests and one end-to-end run in the push gate, and running the heavier repeats at each phase PR, keeps the promise while still running every test before anything merges.
Stakes if we pick wrong: every push in the repo slowed by several minutes, or the 60-second promise quietly broken.
Recommendation: A because it keeps D12's bound for everyone else's pushes and still runs the heavy tests before every merge.
Completeness: A=9/10, B=7/10, C=8/10
Pros / cons:
A) Fast tests in the gate, heavy ones at phase PRs
  ✅ Other sessions' pushes keep the bound D12 promised
  ✅ Every test still runs before each phase PR merges, through `make ukis-all`
  ❌ A determinism or licence regression is caught at the phase PR, not on the push
B) Keep D12 as approved
  ✅ Every push runs every test
  ✅ No test markers to maintain
  ❌ The 60-second bound is likely broken, slowing every push in the repo
C) Measure in task 3b first
  ✅ Decides from a real timing instead of a guess
  ✅ No change until the number is known
  ❌ D12's bound stays unverified until checkpoint A
D) Defer this change
  ✅ No cons — this is a hard-stop choice
Net: a fast gate with heavy tests at merge time versus every test on every push.
Header: Gate speed
Options:
A) Apply this change
The pre-push gate runs unit tests plus the `open`-tier end-to-end build, under 60 s; the `full`-tier end-to-end, determinism and licence builds are marked `slow`, excluded with `-m "not slow"`, and run by `make ukis-all` at every phase PR. The rest of D12 is unchanged.
B) Keep this row's current value
The whole ukis suite runs in the gate with the 60 s bound; the rest of D12 is unchanged.
C) Investigate before choosing
Task 3b times the whole suite on `area_mini`; checkpoint A decides; D12 stays as approved until then.
D) Defer this proposed change only
Leave the bound unresolved and carry it as an open decision; the rest of D12 is unchanged.

State: approved
Actual answer: A) Apply this change (D18, 2026-11-08)
Accepted scope: the pre-push gate runs unit tests plus the `open`-tier end-to-end build, under 60 s; the `full`-tier end-to-end, determinism and licence builds are marked `slow`, excluded with `-m "not slow"`, and run by `make ukis-all` at every phase PR. The rest of D12 is unchanged. Applied to tasks 1, 3b and 18 above.
History: D12 (2026-11-08) approved the whole suite in the gate under 60 s; reopened by O13 because D6 and D10 added whole-pipeline builds.

### Outside-voice corrections applied without a question
Each of these is necessary implementation or proof of an already approved contract, or a
factual correction, so it needs no new approval (Decision procedure, "Carry its necessary
code, tests, documentation"). Applied in the tasks above.

| Finding | Severity | Approved contract it serves | Change |
|---|---|---|---|
| O1 | Critical | D4: the export loads in carb3 | all five `PREMISE_SCHEMA` files written; load loop over every premise plus `resolve_premise_references` (`load.py:148-179`, `:304`, `:459`) |
| O3 | High | D3 and D4 | names in `carb3_activities.csv` checked against `activity_process_register.csv` |
| O4 | High | 03 §3.1's five tables | `sites`, `premises`, `area_activity_counts` added to the interim schemas, with owners (tasks 5, 13, 9) |
| O5 | High | D12: sockets blocked, gate passes | DuckDB `spatial` extension pre-installed by the `ukis` target; QuackOSM cache moved to the data root |
| O8 | High | 03 milestone 0 ("read the EPC address terms") | Human 5 added; EPC address bridge goes `full`-only if the terms are not open (D6's logic) |
| O9 | Medium | D10 and the no-shared-files rule | one expected-values file per step; fixture owned by the primary session; full chain runs at lane merge |
| O10 | Medium | task 1's "every dependency" | pyosmium in dev dependencies |
| O11 | Medium | D8 | stated that task 13 runs without heights under D8's no-height rule |
| O12 | Medium | task 17 | open-tier export coverage stated in its README |
| O14 | Low | D6 | VOA outputs go to the `full` tier directory |
| O15 | Low | task 18 | VOA Stock of Properties added to task 2's sources |

Outside-voice findings resolved by question: O2 (D15), O6 (D16), O7 (D17), O13 (D18), O16
(D14). All 16 are dispositioned.

### D19: TODO for the carb3 crosswalk's blank codes
Finding: found under F1 (Scope Challenge), reviewer Claude. Approved: A) Add to TODOS.md (D19, 2026-11-08). Accepted scope: one TODO in the repo's `TODOS.md` (Housekeeping) to fill the 8 blank codes in `docs/notes/data/carb3_comit_crosswalk.csv` from Table 28. Applied.

Approval readiness: PASS. Checked F1 (D3), F2 (D4, then D15), F3 (D5), F4 (D6), F5 (D7), F6 (D8), F7 (D9), F8 (D10), F9 (D11), F10 (D12, then D18), F11 (D13), O16 (D14), O6 (D16, investigation only), O7 (D17), D19; O1, O3, O4, O5, O8 to O12, O14 and O15 applied as necessary implementation of the approved contracts named in their table. Structure: D2. Office hours skipped: D1.

## Eng review body

### NOT in scope
- **Morphology height model for footprints without LiDAR.** 03 §4 step 7 describes it; the pilot area is covered by EA LiDAR, so task 12 does not build it. It joins at milestone 3 (Scotland).
- **Climate TRACE, HSE COMAH and the unchecked registers.** In 02 and 03, but no task loads them; the pilot's large sites are covered by PRTR, NAEI and ETS.
- **The adjacent layer (Warehouse and Utilities) validation.** Classified and kept, but checked only at milestone 2 (03 §9 decision 1).
- **GeoParquet 2.0.** 1.1 until reader support is checked (03 §3.3).

### What already exists
- `carb3/` sets the project pattern copied here: uv, `src/` layout, hatchling, Python 3.12, a pytest dev group (`carb3/pyproject.toml`).
- `carb3.load.PREMISE_SCHEMA` (`carb3/src/carb3/load.py:148-179`) is the export contract task 17 writes to; nothing is reimplemented.
- COMIT note 04's emissions-to-fuel back-derivation is reused in task 16, not rebuilt.
- `docs/notes/data/activity_process_register.csv` is the name reference for `carb3_activity`; the repo crosswalk is not (it codes 47 of 55).
- The root `Makefile` `check` target and `tools/quality_gate.sh` gain one dependency; no new gate.

### Diagram: the pilot pipeline and its tables

```
  config/sources/*.toml ──ukis fetch (atomic, locked)──▶ $UKIS_DATA_ROOT/raw/  (shared, read-only)
                                                              │
        ┌──────────────────────┬──────────────────────┬──────┴───────────────┬──────────────────┐
   step02 OSM            step04 geography       records loaders           step07 height     lookups
   osm_buildings         uprn_spine             records, installations    heights           (CSV, cited)
   osm_landuse  ──▶ step03 footprints, sites    area_activity_counts            │
        │               │        │                     │                        │
        └───────────────┴────────┴──────────┬──────────┴────────────────────────┘
                                            ▼
                           step05 link (gia_provisional, candidate rule from task 0)
                           building_premise, premises, sites.installation_id
                                            ▼
                           step06 classify (evidence, area prior)  ◀── lookups
                                            ▼
                           step08 storeys and GIA  ◀── heights
                                            ▼
                           step09 energy (reported site, benchmark, calibration)
                                            ▼
                           step10 assemble ──▶ output/pilot/<tier>/*.parquet, carb3/*.csv
                                            ▼
                           validate (report, exceptions counts, hold-out accuracy)

  --tier open : restricted loaders refuse at load time      --tier full : everything loads
```

### Failure modes

| Path | Realistic failure | Covered by | User sees |
|---|---|---|---|
| fetch | download drops halfway | D11 atomic fetch and its test | an error; no partial vintage |
| loaders | upstream renames a column | D9 required-column check and test | an error naming the column |
| step02 | extract does not cover the pilot | D13 coverage check and test | an error naming the source |
| step05 | candidate rule admits the wrong estate | D16 measured rule, D17 hold-out accuracy, checkpoint B | a low accuracy figure at checkpoint B |
| step05 | heights not ready | D8 no-height rule, O11 | links re-solved when heights land |
| step10 | export rejected by carb3 | O1 load loop test | a test failure |
| step10 | mass-duty premise without throughput | D15 rule and cement fixture | listed in `carb3/exceptions.csv` |
| open build | VOA influence leaks into the release | D6 byte-identity test | a test failure |
| gate | suite too slow for every push | D18 `slow` marker, `ukis-all` at phase PRs | gate stays under 60 s |
| tests | DuckDB extension download blocked | O5 pre-install | none |

No failure mode is untested, unhandled and silent: **0 critical gaps.**

### Worktree parallelization strategy

| Step | Modules touched | Depends on |
|---|---|---|
| Task 0 spike | `spikes/voa_match/`, `docs/` | Human 1, 2, 5 |
| Foundation (tasks 1 to 3b) | project root, `src/ukis/` core, `tests/fixtures/` | PR #99 merged |
| Geometry lane (4, 5) | `src/ukis/steps/step02_*`, `step03_*` | foundation |
| Geography lane (6) | `src/ukis/steps/step04_*` | foundation |
| Lookups lane (7, 8) | `lookups/` | foundation |
| Records lane (9, 10, 11) | `src/ukis/records/` | foundation; Human 1 for 11 |
| Height lane (12) | `src/ukis/lidar.py`, `steps/step07_*` | foundation |
| Integration (13 to 19) | `src/ukis/steps/step05_*` to `step10_*`, `validate.py`, `handcheck.py` | all lanes merged |

**Parallel lanes:** geometry, geography, lookups, records and height run at once, in five
worktrees off `feat/ukis-lanes`, each with its own `tests/e2e/expected_step<NN>.py`.
**Execution order:** run task 0 beside tasks 1 to 3b. Checkpoint A. Launch the five lanes.
Merge each into `feat/ukis-lanes` after review; open the lanes PR. Then integration,
sequentially, in the primary session.
**Conflict flags:** `schemas.py`, `pyproject.toml` and `tests/fixtures/make_area_mini.py`
are shared and owned by the primary session; a lane that needs a change asks for it.

### Implementation Tasks
Synthesized from this review's findings. Each is folded into the numbered tasks above.

- [ ] **T1 (P1, human: ~1 day / CC: ~30 min)** — spike — run task 0, the VOA match-feasibility spike
  - Surfaced by: Outside voice O16 (D14), O6 (D16)
  - Files: `spikes/voa_match/`, `docs/05_voa_match_spike.md`
  - Verify: the note states every number with its command; checkpoint A reads it
- [ ] **T2 (P1, human: ~2h / CC: ~10 min)** — tiers — add `--tier open|full` and refusing loaders
  - Surfaced by: Architecture F4 (D6)
  - Files: `src/ukis/manifest.py`, `src/ukis/records/voa.py`, `src/ukis/validate.py`
  - Verify: the open-build byte-identity test passes
- [ ] **T3 (P1, human: ~1h / CC: ~10 min)** — linking — provisional class-free GIA
  - Surfaced by: Code quality F6 (D8)
  - Files: `src/ukis/steps/step05_link.py`
  - Verify: `uv run pytest tests/test_step05_link.py -q`
- [ ] **T4 (P1, human: ~1 day / CC: ~30 min)** — tests — synthetic end-to-end area
  - Surfaced by: Tests F8 (D10), O9
  - Files: `tests/fixtures/make_area_mini.py`, `tests/test_e2e.py`, `tests/e2e/`
  - Verify: `uv run pytest tests/test_e2e.py -q`
- [ ] **T5 (P1, human: ~3h / CC: ~15 min)** — export — five carb3 tables, load loop, mass-duty rule
  - Surfaced by: Scope F2 (D4), O1, O2 (D15), O3
  - Files: `src/ukis/steps/step10_assemble.py`, `tests/test_step10_assemble.py`
  - Verify: the export loads through `carb3.load` for every premise
- [ ] **T6 (P1, human: ~2h / CC: ~10 min)** — lookups — canonical activity list from Table 28
  - Surfaced by: Scope F1 (D3), O3
  - Files: `lookups/carb3_activities.csv`, `tests/test_lookups.py`
  - Verify: `uv run pytest tests/test_lookups.py -q`
- [ ] **T7 (P2, human: ~2h / CC: ~10 min)** — data — shared raw root, atomic and locked fetch
  - Surfaced by: Architecture F5 (D7), Tests F9 (D11)
  - Files: `src/ukis/paths.py`, `src/ukis/manifest.py`, `tests/test_manifest.py`
  - Verify: `uv run pytest tests/test_manifest.py -q`
- [ ] **T8 (P2, human: ~3h / CC: ~15 min)** — robustness — required columns and exception files
  - Surfaced by: Code quality F7 (D9)
  - Files: every loader and step, `src/ukis/io.py`
  - Verify: the missing-column and dropped-rows tests pass
- [ ] **T9 (P2, human: ~1h / CC: ~5 min)** — gate — `ukis` and `ukis-all` targets, extension pre-install
  - Surfaced by: Tests F10 (D12), O13 (D18), O5, O10
  - Files: `../Makefile`, `Makefile`, `tests/conftest.py`, `pyproject.toml`
  - Verify: `bash ../tools/quality_gate.sh` with the ukis gate suite under 60 s
- [ ] **T10 (P2, human: ~2h / CC: ~10 min)** — validation — link hold-out accuracy at checkpoint B
  - Surfaced by: Outside voice O7 (D17)
  - Files: `src/ukis/steps/step05_link.py`, `src/ukis/validate.py`
  - Verify: the pilot run reports hold-out accuracy
- [ ] **T11 (P2, human: ~30 min / CC: ~5 min)** — performance — Lincolnshire extract with coverage check
  - Surfaced by: Performance F11 (D13)
  - Files: `config/sources/geofabrik_lincolnshire.toml`, `src/ukis/steps/step02_osm.py`
  - Verify: the coverage-check test passes
- [ ] **T12 (P2, human: ~1h / CC: ~5 min)** — PRs — one PR per phase
  - Surfaced by: Scope F3 (D5)
  - Files: none (process)
  - Verify: three PRs after #99

Effort assumes scaffolding ~100x, tests ~50x and features ~30x faster with CC than a person; the spike is research (~3x).

### Unresolved decisions that may bite you later
- **O6 candidate rule (D16):** which buildings may receive a VOA record is measured by task 0 and picked at checkpoint A. Task 13 cannot be written until then.

### Completion summary
- Step 0: Scope Challenge — scope accepted as-is
- Reality rows: 7/7 applicable rows emitted (`PLAN_REALITY: phase=eng rows=7/7 verdict=complete`), 4 unverified premises
- Architecture Review: 2 issues found
- Code Quality Review: 2 issues found
- Test Review: diagram produced, 3 gaps identified
- Performance Review: 1 issue found
- NOT in scope: written
- What already exists: written
- TODOS.md updates: 1 item proposed to user (accepted)
- Failure modes: 0 critical gaps flagged
- Unresolved decisions: 1 in this review
- Outside voice: codex unavailable (model not supported on the account); native Claude subagent completed, 16 findings (5 by question, 11 applied as required fixes)
- Parallelization: 5 lanes, 5 parallel / 3 sequential phases
- Lake Score: 7/12

### Suppressed findings (appendix)
- (confidence 4/10) OS Open TOID's point may be a seed point rather than a centroid for some building polygons, so a TOID point could fall outside its own building. Task 6's real run reports the share of TOID points inside an OSM polygon; not raised as a decision.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Outside Review | codex (unavailable), native Claude subagent fallback | Independent 2nd opinion | 1 | unavailable (native completed) | 16 findings, all dispositioned |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | issues_open | 8 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **OUTSIDE COVERAGE:** codex, plan-review phase: unavailable (`gpt-6-astra` not supported on this ChatGPT account). Native Claude Plan subagent completed within the five-minute bound with 16 findings; native results do not count as outside coverage.
- **VERDICT:** no review CLEAR. Eng review issues are all resolved into the plan (issues_open records mapped work, not failure); one decision (O6) is deferred to checkpoint A by design.

**UNRESOLVED DECISIONS:**
- O6 candidate rule (D16): picked at checkpoint A from task 0's measurements
