# 03 Build plan

Plan written 2026-11-08 from the research in [01](01_research_summary.md) and the source
inventory in [02](02_open_data_inventory.md). Nothing is built yet.

## 1. Goal and scope

**Deliverable:** a GeoParquet of UK industrial buildings, one row per building footprint,
with these columns: footprint, height, storeys, floor area, postcode, LSOA (or its Scottish
and NI equivalents), local authority, CaRBE group and CaRB3 activity, energy by carrier
where the evidence allows, and the evidence and confidence behind every value. Two
companion tables hold premises and sites.

**What "industrial" means.** The core is the **CaRBE Factory class** (the 7 groups `FA_A`
to `FA_O`; CaRB3 activities `FA01` to `FA99`). This matches the CaRB3 programme's scope,
which is Factory-class activities only. Buildings that the pipeline finds but classes as
Warehouse or Utilities (sewage works, waste handling) are kept in an `adjacent` partition,
because the classification work has to look at them anyway and dropping them would cost
more to redo later.

**Order of coverage:** England and Wales first (richest open data), then Scotland, then
Northern Ireland (thin: no open UPRNs, valuation list or full LiDAR).

**Out of scope for the first release:** physical throughput (the CaRB3 site model's
`premise_throughput`), construction year, and anything that needs a licensed or
non-commercial input.

## 2. Design principles

1. **Label from records, predict only as a fallback.** Activity comes from VOA codes, EPC
   building types, FSA approvals, emissions registers and OSM tags. A morphology classifier
   only decides "industrial or not" for footprints that no record touches.
2. **Every derived value carries its source and a confidence.** Columns come in triples:
   value, `*_source`, `*_quality`. A reader can always filter to "measured or reported".
3. **Links are many to many.** UPRN, premises and building are joined through a bridge
   table with a method and score on every row. A multi-let shed with twelve units and a
   steelworks with eighty buildings are both normal cases.
4. **Licence tiers are kept apart in storage, not only in documentation.** Columns derived
   from restricted sources (VOA, the EA Pollution Inventory) live in a separate layer that
   joins by `building_id`. The released table can be rebuilt without them.
5. **Reproducible from a manifest.** Every input is downloaded by a script that records URL,
   retrieval date, vintage, licence and SHA-256 in `config/sources.toml`. Raw files are
   never edited. Rebuilding from the same manifest gives byte-identical output (sorted rows,
   stable identifiers).
6. **Metric work in a projected CRS.** Areas and distances are computed in EPSG:27700
   (British National Grid) for GB and EPSG:2157 (Irish Transverse Mercator) for NI.

## 3. Output data model

### 3.1 Tables

| Table | One row per | Purpose |
|---|---|---|
| `buildings` | building footprint | The deliverable: geometry plus every attribute |
| `premises` | occupier unit (VOA hereditament, or an EPC, FSA or register record with no VOA match) | Activity, floor area and energy as the records state them |
| `building_premise` | link between a building and a premises | Bridge with `link_method`, `link_score` and `area_share` |
| `sites` | group of buildings on one plot (HMLR INSPIRE polygon, OSM `landuse=industrial` or `man_made=works`, or a registered installation) | Where a large site's reported energy is attached |
| `evidence` | one piece of classification evidence for a building or premises | Audit trail: source, raw value, mapped class, weight |

The NBD's self-contained unit (SCU, adjoining footprints that never split a premises) is
computed as `scu_id` on `buildings` rather than as a separate table.

### 3.2 `buildings` columns

| Column | Type | Notes |
|---|---|---|
| `building_id` | string | Stable: `osm:w<id>`, `osm:r<id>`, `osmap:<id>` or `ovt:<gers id>` |
| `geometry` | polygon (WKB) | Stored in OGC:CRS84 for the UK-wide file |
| `footprint_source` | enum{osm, os_openmap_local, overture, microsoft} | |
| `footprint_area_m2` | real | Computed in the projected CRS |
| `scu_id`, `site_id` | string | Groupings, see §3.1 |
| `height_p50_m`, `height_p90_m`, `height_max_m` | real | LiDAR DSM minus DTM, inside a 1 m inward buffer |
| `height_source` | enum{lidar_ea, lidar_wales, lidar_scotland, lidar_ni, osm_tag, modelled, none} | |
| `lidar_year` | integer | Survey year of the tiles used |
| `storeys` | integer | |
| `storeys_source` | enum{osm_tag, height_rule, epc, assumed_single} | |
| `gia_m2` | real | Best gross internal area for the whole building |
| `gia_source` | enum{voa, epc, geometric} | Precedence follows the NBD: VOA, then EPC, then geometry |
| `gia_geometric_m2` | real | Always computed: footprint area times storeys, times a GIA factor |
| `uprns` | list\<int64\> | From the link table |
| `postcode`, `postcode_source` | string, enum{record_vote, uprn_lookup, nearest_centroid} | |
| `oa_code`, `lsoa_code`, `msoa_code`, `lad_code`, `lad_name`, `nation` | string | 2021 LSOA/MSOA/OA (E&W), 2022 Data Zone (Scotland), 2021 Data Zone and SDZ (NI). `lsoa_code` holds the nation's equivalent; `geo_level` says which |
| `carbe_class` | enum{FA, WA, UT, ...} | |
| `carbe_group` | enum{FA_A, FA_B, FA_C, FA_D, FA_E, FA_F, FA_O, unknown} | |
| `carbe_group_prior` | struct of probabilities per group | Area activity prior from ONS Business Counts, set only on buildings no record classes (step 6) |
| `carb3_activity_code`, `carb3_activity` | string | For example `FA13`, "Food Processing Centre". Matches the CaRB3 site model's `carb3_activity` |
| `class_source`, `class_confidence` | enum, real 0-1 | Strongest evidence used; see §4 step 6 |
| `premise_count` | integer | |
| `energy_elec_kwh`, `energy_gas_kwh`, `energy_other_kwh` | real | Base year, see §8 decision 4 |
| `energy_method` | enum{reported_site, epc, group_benchmark, calibrated} | |
| `energy_uncertainty` | enum{low, medium, high} | |
| `licence_tier` | enum{open, restricted_derived} | `open` in the released file, always |
| `build_version`, `source_manifest_sha` | string | Which inputs built this row |

### 3.3 File layout

- GeoParquet **1.1** with the bounding-box covering column, rows sorted by Hilbert index,
  one file per nation plus a UK-wide file. GeoParquet 2.0 only after checking that GDAL,
  DuckDB, GeoPandas and QGIS versions in use can read it.
- Partitioned by `lad_code` for the working copy, so a pilot or one authority can be
  rebuilt alone.
- A **CaRB3 export** writes `premise_record` and `premise_energy` in the shape of the live
  spec §3.1 and §3.1.1, for Factory-class premises only. Two gaps to settle there: the
  spec's `nation` enum has no Northern Ireland, and `premise_throughput`, which the spec
  requires, has no open source for most premises.

## 4. Pipeline

Ten steps. Each reads only earlier outputs, writes GeoParquet to `data/interim/`, and has a
check that must pass before the next step runs.

### Step 1. Acquire

Download every source in `config/sources.toml` into `data/raw/<source>/<vintage>/`, one
new directory per download, and record the checksum. LiDAR is fetched later, only for the
tiles that step 7 needs.
**Check:** each manifest entry has a licence and a checksum; restricted sources are
flagged.

### Step 2. Extract OSM

- Filter the Geofabrik extracts with `osmium tags-filter` to: every `building=*` way and
  relation; `landuse=industrial|quarry`; `man_made=works|silo|storage_tank|chimney|kiln`;
  `industrial=*`, `craft=*`, `product=*`; and POIs carrying `name` or `addr:*`.
- Convert with QuackOSM to GeoParquet, keeping only the tags above plus `building:levels`,
  `height`, `roof:levels`, `name`, `operator` and `addr:*`.
- Keep **all** buildings, not only those tagged industrial: most sheds are `building=yes`.
- Clip the Ireland extract to the NISRA boundary.

**Check:** building counts per LAD against the previous run; geometry validity.

### Step 3. Fill footprint gaps

- Per LSOA, compare OSM building area with OS OpenMap Local building area.
- Where OS has a polygon with no OSM overlap (intersection over union below 0.3 against
  every OSM building), add it with `footprint_source = os_openmap_local`.
- In NI, and anywhere OS OpenMap Local is also missing, use Overture's non-OSM footprints.

Record the completeness ratio per LSOA. It is a reported output in its own right, since no
GB study of it exists.
**Check:** no duplicates (intersection over union above 0.5 between kept polygons).

### Step 4. Build the address spine and geography

- Load OS Open UPRN points. Join ONSUD for OA, LSOA, MSOA and LAD. Check whether ONSUD
  carries a postcode field; if not, postcodes come from step 5's records.
- Load OS Open Linked Identifiers (`BLPU_UPRN_TopographicArea_TOID_5`) and OS Open TOID
  points. This gives each UPRN its MasterMap building TOID, and each TOID a location.
- Give each building a representative point (a point on the surface) and assign OA, LSOA,
  MSOA, LAD, Data Zone and nation by point in polygon.

**Check:** UPRNs with no geography; buildings whose geography disagrees with the majority
of their UPRNs.

### Step 5. Link UPRNs and records to buildings

**UPRN to building, in order of preference:**

1. **TOID route.** The UPRN's TOID point falls inside an OSM polygon. This groups the UPRNs
   of one MasterMap building even when their own points scatter.
2. **Point in polygon.** The UPRN point is inside an OSM polygon.
3. **Nearest within 15 m.** Only inside an industrial land-use or site polygon, and only
   when the second-nearest building is more than twice as far.

**Records to UPRN or building** (VOA, EPC, FSA, UK PRTR, NAEI, ETS, SPRI, Climate TRACE):

- **EPC:** use the UPRN where the record has one; otherwise match its address to another EPC
  record that does. The EPC register therefore also serves as an open address-to-UPRN
  gazetteer for the next matcher.
- **VOA:** match the normalised address (house number, street, postcode) to EPC addresses,
  then to OSM `addr:*` and `name` tags. Where several candidates remain within the postcode,
  assign by **size consistency**: the VOA floor area against each candidate's geometric GIA,
  solved as an assignment across all VOA records in that postcode, not one at a time.
- **FSA, UK PRTR, NAEI, ETS, SPRI, Climate TRACE:** they have coordinates, so use point in
  polygon, then the nearest building inside the same site polygon. UK PRTR also carries a
  postcode and street address, which confirm the match. These registers describe the same
  large sites several times over, so they are first deduplicated into one `installation`
  record per site (matched on coordinates within 250 m plus a normalised operator name).

Every link is written to `building_premise` with `link_method` and `link_score`.
**Check:** match rate per source and LAD. The pilot sets the acceptance threshold (§6); the
NBD did not publish one to copy.

### Step 6. Classify activity

Each building collects evidence rows in `evidence`. Each row maps to a CaRBE class, and
where possible to a group and a CaRB3 activity:

| Evidence | Maps to | Default weight |
|---|---|---|
| VOA SCat plus PD code (restricted layer) | CaRB3 activity, through the rebuilt lookup | highest |
| UK PRTR NACE activity code | CaRB3 activity through a NACE-to-CaRB3 lookup (for example NACE 23.51 to `FA45` Cement Works) | high |
| NAEI, UK ETS, SPRI or Climate TRACE installation sector | activity for the high-energy and mineral activities (cement, steel, refinery, chemicals, paper) | high |
| HSE COMAH establishment | class `FA`, chemicals or storage, as a supporting signal | medium |
| FSA approved establishment activity (meat, dairy, fish and so on) | `FA_F` activities, for example `FA16` Abattoir, `FA35` Creamery, `FA13` Food Processing Centre | high |
| EPC building type (for example "B2 to B7 General Industrial", "B8 Storage or Distribution") | class only | medium |
| OSM `industrial=*`, `product=*`, `man_made=works`, `craft=*` | activity where the tag is specific (for example `industrial=brewery`); class otherwise | medium |
| OSM `building=industrial`, `factory`, `manufacture`, `warehouse` | class only | low |
| Inside `landuse=industrial` | candidate flag only | low |
| Morphology classifier | "industrial or not" only | lowest |

**Area activity prior.** After record evidence is applied, each MSOA still holds unclassed
industrial buildings. ONS Business Counts (local units by SIC) say how many sites of each
industry the MSOA has; subtracting the sites already classed leaves a residual mix. Each
unclassed building gets that residual mix as a probability per CaRBE group (stored in
`carbe_group_prior`, a struct of probabilities) and `carbe_group` takes the most likely group
only if its probability is at least 0.5; otherwise it stays `unknown`. Larger sheds are
weighted toward industries with larger sites, using the employment size bands. The prior is
never written as `class_source = record`.

**Resolution:** take the highest-weight evidence. Record the second-best where it disagrees,
and lower `class_confidence` when it does. A building with no record but a positive
classifier result gets `carbe_class = FA`, `carbe_group = unknown`.

**The lookups this needs are hand-built and versioned in `lookups/`:**

1. VOA SCat plus PD code to CaRB3 activity, rebuilt from the OGL SCat list, the PD list in
   the VOA download specification, and CaRB3 Table 28's activity names.
2. CaRB3 activity (`FA01` to `FA99`) to CaRBE group (`FA_A` to `FA_O`). The NBD's group
   floor areas are the check on it.
3. FSA activity, EPC building type, OSM tag and NAEI/ETS sector to CaRB3 activity.
4. NACE (UK PRTR) and SIC 2007 (Business Counts) to CaRB3 activity and CaRBE group. SIC 2007
   and NACE Rev. 2 agree to four digits, so one lookup serves both.

Ask UCL for lookups 1 and 2 before building them (§7, milestone 0).
**Check:** class totals against NBD phase 2 (§6).

### Step 7. Height

- Fetch the EA, Welsh, Scottish and NI LiDAR tiles that intersect candidate buildings only:
  `FA`, `WA` or `UT` class, or `unknown` inside industrial land use. Cache them and delete
  them after zonal statistics.
- Compute DSM minus DTM, then the median, 90th percentile and maximum inside a 1 m inward
  buffer, with exactextract. Footprints under 30 m² are not buffered.
- Where no LiDAR covers a building: use the OSM `height` tag; otherwise predict from
  morphology with a gradient-boosted model trained on LiDAR-covered **industrial** footprints
  (the published models were trained mostly on dwellings), and flag it as `modelled`.

**Check:** height against the OSM `height` tag where both exist; share of buildings with
negative or zero height (a stale footprint or a demolished building).

### Step 8. Storeys and floor area

**Storeys:**

1. OSM `building:levels`, if plausible against height (height divided by levels between
   2.5 and 8 m).
2. **Sheds**: one storey. A shed means a footprint over 500 m², a 90th-percentile height of
   15 m or less, and a class of `FA`, `WA` or `UT`. Mezzanines are not inferred.
3. Otherwise, the 90th-percentile height divided by an activity floor-to-floor height,
   rounded, with a minimum of 1. The floor-to-floor heights are calibrated in the pilot on
   buildings that have both OSM levels and LiDAR.

**Floor area:**

- `gia_geometric_m2` = footprint area × storeys × 0.95 (a GIA-to-GEA ratio to be checked in
  the pilot).
- A premises takes its VOA summary-valuation area (restricted layer), else its EPC area,
  else its share of the building's geometric GIA.
- `gia_m2` on a building is the sum of its linked premises' VOA or EPC areas when they cover
  the building. Otherwise it is the geometric figure.

**Check:** where VOA or EPC area and geometric area both exist, a ratio outside 0.5 to 2
flags the link for review.

### Step 9. Energy

Energy is built in tiers, and every value records which tier produced it:

1. **Reported site:** CO₂ from the deduplicated installation record (UK PRTR, NAEI, UK ETS,
   SPRI; Climate TRACE as a cross-check only) is turned into fuel in three moves:
   - remove **process CO₂** with a per-sector share from published factors (cement, lime,
     steel, glass, ammonia and other chemistry). Without this, a cement works' fuel would
     come out about 2.5 times too high;
   - split the remaining combustion CO₂ into fuels with the sector fuel mix from ECUK and
     DUKES, as COMIT does (repo note 04), and convert with fuel emission factors;
   - leave **electricity** to tier 2, since grid electricity leaves no on-site emissions.
   The fuel is attached to the site, then spread over its buildings by GIA share.
   Uncertainty: medium at site level (it is a back-derivation, not a meter), high per
   building.
2. **Group benchmark:** GIA × the NBD phase 2 median EUI for the building's CaRBE group,
   split by carrier using the NBD gas and electricity medians. A building whose MSOA has no
   non-domestic gas meters in the DESNZ data gets no gas.
3. **Calibration:** per MSOA, scale the benchmark buildings (tier 1 held fixed) so that
   Factory-class energy matches the NBD synthetic population's Factory energy for that MSOA.
   The DESNZ MSOA non-domestic totals are an upper bound. Use iterative proportional fitting
   across MSOA and CaRBE group.
4. **EPC:** stored as a separate column for buildings that have one, not as the estimate.
   EPC energy is modelled building services energy, not process energy.

Every carrier the model did not assess is left absent, not zero, matching the CaRB3 site
model's rule that absence is not zero.
**Check:** MSOA totals against the synthetic population and DESNZ; group EUI distribution
against the NBD medians.

### Step 10. Assemble, validate, publish

Join every layer, apply the licence filter, write the GeoParquet files and the CaRB3 export,
then run the validation suite (§6). Publish a data card with the licence (ODbL), the
attribution list (OSM contributors, OS, ONS, DESNZ, FSA, EA and the others), and the
validation results.

## 5. Tooling and compute

- **Python 3.12 or later with `uv`**, in its own `pyproject.toml`. Libraries: `duckdb`
  (spatial extension) for joins, `quackosm` for OSM, `geopandas` and `shapely` 2 for
  geometry, `rasterio` and `exactextract` for zonal statistics, `pyarrow` for Parquet,
  `scikit-learn` or `lightgbm` for the two fallback models.
- **System tools:** `osmium-tool` and GDAL. Neither is installed on this machine, so install
  them with Homebrew or use the Python wheels.
- **This machine:** 17 GB RAM and about 585 GB free disk. That is enough for GB OSM if tags
  are filtered first, and for LiDAR if tiles are fetched per area and deleted after use.
  National LiDAR in one go is not.
- **Orchestration:** one CLI command per step (`ukis run step5 --lad E06000013`) plus a
  `Makefile` target for the whole chain. Each step skips itself when its inputs' checksums
  are unchanged.
- **Tests:** unit tests on the lookups and matchers with hand-made fixtures. Regression
  tests on the pilot area's outputs.

## 6. Validation

| Check | Against | Aim |
|---|---|---|
| Activity accuracy | A hand-checked sample of 500 buildings, stratified by CaRBE group and nation, checked against aerial imagery and operators' own websites | At least the NBD's 69% correct activity |
| Footprint completeness | OS OpenMap Local area per LSOA | Reported per LSOA, with no pass mark |
| Group totals | NBD phase 2 Factory tables: premises, floor area and percentiles per group (Table 3_3), regional shares (Table 3_2) | Within ±20% per group for E&W, once the CaRB3-to-CaRBE lookup is settled |
| Area counts | VOA Stock of Properties by LSOA and SCat (OGL) | Correlation per LSOA reported; outliers reviewed |
| Area activity mix | ONS Business Counts local units by SIC per MSOA | Classed plus prior-weighted counts per MSOA and group reported against the counts |
| Large-site coverage | Every UK PRTR, UK ETS and NAEI industrial installation | 100% linked to at least one building, or explained |
| Height | OSM `height` tags; a LiDAR hold-out for the modelled heights | Median absolute error reported per source |
| Floor area | EPC floor area where a building has exactly one EPC premises | Ratio distribution reported |
| Energy | DESNZ MSOA non-domestic totals; synthetic population MSOA Factory energy; NBD group medians | Never above the DESNZ total; group medians within ±25% |
| Determinism | A second build from the same manifest | Byte-identical files |

## 7. Milestones

| Milestone | Contents | Done when |
|---|---|---|
| 0. Access and licences | Read the VOA download terms and the EPC address terms; confirm the ONSUD and OS licence texts; write to UCL (NBD team) for the SCat/PD-to-activity lookup and the CaRB3-to-CaRBE mapping; ask the VOA whether derived, aggregated classification may be released; confirm UK PRTR's Scotland and NI coverage, Business Counts' finest geography and the Nomis terms | Each restricted source has a written decision: open, restricted layer, or excluded |
| 1. Pilot | North Lincolnshire and North East Lincolnshire: steel at Scunthorpe, refineries and chemicals at Immingham, food at Grimsby, plus ordinary workshop estates. Steps 1 to 10 end to end, plus a 150-building hand check | Every column populated or explained; thresholds and floor-to-floor heights fixed; match rates known |
| 2. England and Wales | Scale out by LAD | Validation table (§6) produced for E&W |
| 3. Scotland | Data Zones, Scottish EPC, SPRI, partial LiDAR | Same checks, with the missing VOA layer stated |
| 4. Energy layer | Step 9 across GB | MSOA checks pass |
| 5. Northern Ireland | OSM plus Overture, NSPL, Data Zones, FSA, partial LiDAR | Coverage and quality reported honestly, even if thin |
| 6. Release | Data card, attribution, validation report, CaRB3 export | Published under ODbL |

The pilot is the decision point: if the VOA-to-building match rate is too low to support
activity-level classification, the release falls back to group-level classification from
open evidence, and the plan is revised before scaling out.

## 8. Risks

| Risk | Effect | Mitigation |
|---|---|---|
| VOA terms forbid releasing derived classes | The released file loses activity detail for most `FA_A` and `FA_B` buildings | Restricted layer kept separate (§2); ask the VOA early (milestone 0); open evidence still gives class and many groups |
| VOA to building matching is weak (no UPRN, no open address gazetteer) | Activity and floor area do not reach the buildings | EPC as a gazetteer, OSM address tags, size-consistent assignment within the postcode; match rate measured in the pilot |
| No published SCat/PD lookup | The classification diverges from the NBD's | Ask UCL first; otherwise rebuild it and check against the NBD group totals |
| Multi-let workshop estates (`FA_A`, 230,177 premises in 142,602 SCUs) | Many premises share one footprint; the floor area split is uncertain | Premises table plus bridge; area split by VOA areas where linked |
| OSM gaps on industrial estates | Missing buildings | OS OpenMap Local and Overture gap filling; completeness reported per LSOA |
| LiDAR vintage older than the footprint | Wrong or zero heights on new sheds | `lidar_year` column; a zero-height flag; modelled fallback |
| Building-level energy is far less certain than area totals | Misuse of single-building numbers | Uncertainty class on every value; documentation leads with aggregate use |
| Northern Ireland data is thin | Low coverage and quality | Separate milestone, reported separately |
| Licence mixing | A non-open input contaminates the ODbL release | Licence tier recorded on every source and every column; assembly filters by tier |

## 9. Decisions still open

1. **Scope.** Factory class only, or Factory plus Warehouse and Utilities as a published
   adjacent layer? Recommended: Factory core, adjacent layer kept but unvalidated.
2. **VOA.** Use it in a restricted layer while the terms are checked (recommended), or leave
   it out entirely so that everything stays open from the start?
3. **Unit of record.** One row per building with premises in a companion table
   (recommended), or one row per premises with the building geometry repeated?
4. **Base year.** 2023, matching the NBD snapshot (1 April 2023) and its calibration
   targets (recommended), or 2024, matching the latest DESNZ sub-national data?
5. **Where the code lives.** In this folder for now, then its own repository once code
   starts (recommended, since its ODbL data and licence obligations differ from COMIT's), or
   in this repository for good?
6. **Semantic judgements stay in code (settled 2026-11-08).** Mapping free-text VOA
   descriptions, names and OSM tags to a CaRB3 activity, and choosing a VOA record's
   building, are done with rules, lookups and the size-consistent assignment in step 5. No
   language-model step.
