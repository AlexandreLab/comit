# Site Data — Sources, Point vs Non-Point, and Aggregation

Site emissions data is the spatial backbone of COMIT: each modelled "site" carries
an emissions load, a sector, and a location that determines its distance to a
hydrogen/CO₂ **cluster** (and hence its pipe/transport costs). This note explains
where sites come from and how they are processed.

Main code: `R/fct_process_sites.R` (entry point `process_sites()`), plus
`R/fct_sites.R`.

## The two origins of site data

### 1. Point sources → NAEI
Real, individually-located industrial installations come from the **NAEI**
(National Atmospheric Emissions Inventory), sheet `NAEI_df_clean_2023_revised`
(~955 rows, 2023 vintage). One row = one physical installation:

| Year | PlantID | Site | Easting | Northing | Operator | IPM_sector | Region | Beis_sector | Emissions_tco2e | cluster_location | lon | lat | traded_flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2023 | 992 | Tipton | 398190 | 292980 | Ervin Amasteel | Iron & steel industries | England | Iron and steel | 747.4 | Black Country | −2.03 | 52.53 | Non-traded |

### 2. Non-point (dispersed) sources → ONS / IDBR
Emissions from many small, dispersed emitters that are **not** individually in
NAEI. Represented statistically, not observed:
- `nps_sites` — counts of **PAYE-registered businesses per region, by 4-digit
  SIC code** (ONS business register).
- `Use_IDBR` toggle (default `TRUE`) — use the **IDBR** (Inter-Departmental
  Business Register) ratio method instead of the raw PAYE-site-data method.
- `nps_loc_mapping` — region-average lat/lon, so imputed sites sit at a
  **regional centroid**, not a real address.

Supporting mappings: `new_sector_mapping`, `NAEI_mapping`, `ONS_sector_mapping`,
`GHGI_sector_mapping`, `nps_loc_mapping`; cluster geography in `Cluster_location`;
sector emissions baselines in `Emissions` (GHGI) split by `traded_share`.

## What "point source" means
A **point source** is a single, geographically-identifiable emitter — one
installation whose emissions can be pinned to a precise map point (grid reference
/ coordinates). NAEI inventories these individually, so COMIT can treat each as
its own site with a real location.

A **non-point (a.k.a. dispersed / area) source** is the opposite: emissions
spread across many small emitters that are not individually inventoried (e.g.
lots of small businesses across a region). They can't be pinned to one point, so
they are represented in **aggregate, statistical** form and placed at a regional
centroid.

## How sites are assembled — `process_sites()`
Three streams are built and row-bound into the master table `NAEI_clean`:

1. **Large point sites** — kept individually.
2. **Aggregated small point sites** — small NAEI points bundled to cut compute.
3. **Aggregated non-point sites** — the ONS/IDBR-derived dispersed sites.

Every site is then enriched (`append_information_to_sites()`):
- sector remapped (`new_sector_mapping` / `NAEI_mapping`),
- Easting/Northing → lon/lat (`calculate_coordinates()`, OSGB 27700 → WGS84 4326),
- allocated to the **nearest cluster** by Haversine distance
  (`allocate_cluster_points()` using `Cluster_location` where `use_cluster == TRUE`),
- pipe distance to that cluster centre computed (`calculate_pipe_distances()`),
- emissions converted to MtCO₂; traded/non-traded share computed.

Separately, `plant_closures` removes or redistributes a site's demand when it
closes during the modelled period.

## Point sources: large vs small split
Point sources are split by size, because keeping every tiny emitter as its own LP
variable would blow up the problem.

**Filter (`get_small_point_sites_filter`):** a point site is "small" when
```
emissions_MtCO2 <= 0.01  AND  traded_flag == "Non-traded"
```
(`point_site_emissions_cut_off <- 0.01`, i.e. 0.01 MtCO₂e = 10 ktCO₂e.)

- **Large point sites** (`get_large_point_sites`): everything not small (bigger
  emitters, plus all traded sites). Kept as individual sites — `num_sites = 1`,
  `site_name = Operator`, real coordinates retained.
- **Small point sites** (`get_aggregated_small_point_sites`): still real NAEI
  points, but aggregated (see below).

## Small point source aggregation
Real small NAEI points are grouped into synthetic "grouped" sites:

1. **Group by** (`group_small_point_sites`):
   `IPM_sector`, cluster (`H2_point`), `pipe_dist_category`, `traded_flag`, and —
   when `Two_nps_sites == TRUE` — also `in_cluster_H2` (inside vs outside the
   cluster's H2 radius, from `cluster_radius`).
   *(Note: `pipe_dist_category` is currently a single coarse bucket, `[0,500)` km.)*
   **Pipe distance band (`pipe_dist_category`).** `pipe_dist` is the Haversine
   distance from a site to its nearest cluster centre, in **km**
   (`calculate_pipe_distances`: metres ÷ 1000). The band buckets that distance:
   ```r
   pipe_dist_category = cut(pipe_dist, breaks = seq(0, 500, by = 500), right = FALSE)
   ```
   `seq(0,500,by=500)` yields breaks `c(0,500)`, i.e. a **single interval
   `[0,500)` km**, later relabelled `"0_500"`. So as configured there is only
   **one catch-all band (0–500 km)** — it does *not* currently sub-divide sites
   by distance; the real grouping is by sector × cluster × traded flag
   (× in/out H2 radius). It's a lever: change `by = 500` to e.g. `by = 50` to get
   ten 50 km bands. Edge note: with `right = FALSE` and top break 500, a site at
   ≥ 500 km would fall outside all bins → `NA` (not an issue for UK distances).
2. **Aggregate within each group** (`aggregate_small_point_sites`):
   - `num_sites = n()` (how many real sites collapsed into this row),
   - `pipe_dist = mean(pipe_dist)`,
   - `total_MtCO2 = sum(emissions_MtCO2)`,
   - `grid_connection_year = mean(...)` (rounded).
3. **Impute a location** (`impute_site_location`): place the aggregate on a circle
   of radius = mean pipe distance around the cluster centre, using a random
   bearing (`geosphere::destPoint`, `set.seed(423)` for reproducibility).
4. **Name**: `"{cluster}_{sector}_{pipe_dist_category}_psg"` — `psg` = *point
   source grouped*; `PlantID` set to `NA`.

## Non-point (dispersed) source treatment
Two methods, chosen by `Use_IDBR`:

- **`Use_IDBR == TRUE` → `non_point_sites_from_ratios()`** (default): sector
  emission totals, filtered to Non-traded, converted to per-site emissions and
  spread using IDBR-derived ratios.
- **`Use_IDBR == FALSE` → `non_point_sites_from_site_data()`**: derive dispersed
  sites from the point-site data / business-count data directly.

The business-count → emissions logic (`get_non_point_sites`,
`get_non_point_sites_by_sector`, `allocate_emissions_to_non_point_sites_by_sector`):
1. Take `nps_sites` business counts, take the 4-digit SIC, map SIC → COMIT/IPM
   sector via `ONS_sector_mapping` + `GHGI_sector_mapping`.
2. Sum businesses per sector across the 12 regions (`num_non_point_sites`).
3. Take each sector's **non-point emissions** (`calculate_non_point_site_emissions`):
   - traded-share method (`Traded_share_calc == TRUE`): `non_point_share * Total_emissions`,
   - else: `Total_emissions - sector_emissions_from_all_sites` (the residual not
     captured by point sources).
4. **Distribute across regions in proportion to business count**
   (`regional_non_point_site_shares`):
   ```
   region_emissions = (businesses_in_region / total_businesses_in_sector)
                      * non_point_site_emissions_MtCO2
   ```
5. Locate each regional aggregate at its region centroid (`nps_loc_mapping`) and
   allocate it to a cluster (`H2_point`).

### One vs two dispersed sites per sector×cluster (`Two_nps_sites`)
- **`TRUE` (default):** produce **two** non-point sites per sector×cluster — one
  representing emitters **inside** the cluster's H2 radius and one **outside**
  (`generate_non_point_sites(inside = TRUE/FALSE)`), row-bound together. This lets
  the model treat in-range vs out-of-range dispersed emitters differently for
  H2/CCS access.
- **`FALSE`:** a **single** aggregate non-point site per sector×cluster
  (`get_single_non_point_sites`).

## Common columns on the final site table
`site_name`, `IPM_sector`, `H2_point` (cluster), `total_MtCO2`, `pipe_dist`,
`num_sites`, `Latitude`, `Longitude`, `traded_flag`, `grid_connection_year`,
`PlantID`.

## ⚠️ Public-file caveats
- `NAEI_df_clean_2023_revised`: *"'traded_flag' column based on dummy data."*
- `nps_sites`: *"numbers of paye registered sites … (out of date)."*
- `nps_loc_mapping`: *"Data out of date."*

Structure and geography are realistic; the emissions figures and flags in the
public version are artificial.
