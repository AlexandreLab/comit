# Clusters & Sectors

Reference counts for the two main grouping dimensions of the site data. These are
**independent** — the single 0–500 km `pipe_dist_category` band (see
[02_site_data.md](02_site_data.md)) does **not** collapse sites into one cluster.
Sites are still allocated across all active clusters.

Figures below are from the public file `comit_input_1_4_0_public_updated.xlsx`
(956 NAEI point-source rows; emissions figures are artificial in the public version).

## Clusters — 10 active (11 listed)
`Cluster_location` lists 11 clusters; 10 have `use_cluster = TRUE`. Each site is
allocated to its **nearest** active cluster centre (Haversine distance,
`allocate_cluster_points`).

Active clusters:
Teesside, Humberside, Humberside2, Southampton, South Wales, Merseyside,
Peterhead, Grangemouth, Medway, Londonderry.

Notes:
- Every site is assigned to one of the 10, even if far away. Whether it is
  *actually within reach* of H2/CCS is a separate flag:
  `in_cluster_H2 = pipe_dist <= cluster_radius_H2`.
- The raw NAEI sheet also has a `cluster_location` column, but the model **ignores
  it for allocation** and recomputes the nearest active cluster. That raw column
  contains labels that are **not** active clusters (e.g. "Black Country",
  "Not in cluster") — do not treat it as the model's cluster assignment.

## Sectors — 16 modelled (from 18 NAEI)
NAEI site data has 18 distinct `IPM_sector` values; `new_sector_mapping` collapses
them to **16 modelled COMIT sectors**:

Cement, Ceramics, Chemicals, Construction, Electrical engineering, Food & drink,
Glass, Iron & steel, Lime, Mechanical engineering, Non-ferrous metals, Other,
Paper, Refineries, Textiles, Vehicles.

NAEI → COMIT renames / merges (18 → 16):

| NAEI `IPM_sector` | Modelled COMIT sector |
|---|---|
| Chemical industry | Chemicals |
| Food, drink & tobacco industry | Food & drink |
| Iron & steel industries | Iron & steel |
| Non-ferrous metal industries | Non-ferrous metals |
| Other industries | Other |
| Paper, printing & publishing industries | Paper |
| Processing & distribution of petroleum products | Refineries |
| Textiles, clothing, leather & footwear | Textiles |
| Waste collection, treatment & disposal | **Other** (merge) |
| Water & sewerage | **Other** (merge) |

The 18 → 16 reduction comes from **Waste** and **Water & sewerage** both folding
into **Other** alongside "Other industries".

## Point-source site counts (NAEI, 956 rows)

### By modelled sector
| Modelled sector | Sites |
|---|---:|
| Food & drink | 210 |
| Chemicals | 168 |
| Ceramics | 161 |
| Other | 161 |
| Paper | 49 |
| Iron & steel | 41 |
| Vehicles | 35 |
| Refineries | 25 |
| Glass | 21 |
| Cement | 20 |
| Electrical engineering | 17 |
| Non-ferrous metals | 16 |
| Lime | 13 |
| Textiles | 10 |
| Mechanical engineering | 5 |
| Construction | 4 |
| **Total** | **956** |

### By raw `cluster_location` (NAEI column — not the model's allocation)
| Raw cluster_location | Sites |
|---|---:|
| Not in cluster | 688 |
| Merseyside | 82 |
| Black Country | 42 |
| Teesside | 42 |
| Grangemouth | 39 |
| Humberside | 28 |
| South Wales | 23 |
| Southampton | 12 |

Reminder: this raw column is **not** what the model uses — it recomputes nearest
active cluster for every site. The large "Not in cluster" count (688) reflects the
raw data, not the model's final allocation (where each of these still gets a
nearest cluster + an `in_cluster_H2` reachability flag).

## Aggregation grid implication
The effective grouping key for aggregating small point sources and non-point
sources is roughly **16 sectors × 10 clusters**, further split by traded flag and
(when `Two_nps_sites = TRUE`) inside/outside the cluster H2 radius. This — not the
distance band — is what determines how many aggregate "sites" the model creates.
