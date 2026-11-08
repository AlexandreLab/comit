# 02 Open data inventory

Checked against publisher pages on 2026-11-08. "Unverified" means the licence or a field
could not be confirmed on the publisher's page and must be read before use. OS open
products are OGL in practice, but their product pages only say "free to use for everyone",
so they are marked "OGL (check docs)".

Every source is placed in one of three tiers:

- **Open:** OGL, ODbL, CC BY or similar. Can go into the released GeoParquet.
- **Restricted:** free to download but under terms that are not an open licence. Used to
  derive columns that live in a separate layer until the terms are cleared.
- **Excluded:** paid, PSGA-only, non-commercial or registration-gated. Not used.

**Share-alike.** OSM is ODbL, so the released building table is a derived database under
ODbL. OGL and CC BY inputs can be combined into it with attribution. Nothing restricted or
non-commercial may enter the released table.

## 1. Geometry

| Source | Tier | Licence | Coverage | Join key | Role | URL |
|---|---|---|---|---|---|---|
| Geofabrik Great Britain extract | Open | ODbL 1.0 | England, Scotland, Wales. 2.0 GB PBF, daily | coordinates, OSM id | Footprint spine, tags, `building:levels`, `height`, `addr:*`, `name` | https://download.geofabrik.de/europe/great-britain.html |
| Geofabrik Ireland and Northern Ireland | Open | ODbL 1.0 | Whole island, clip to NI. 398 MB | as above | NI footprints | https://download.geofabrik.de/europe/ireland-and-northern-ireland.html |
| OS OpenMap Local, Building layer | Open | OGL (check docs) | GB. April and October releases | coordinates | Completeness benchmark for OSM, and gap filling | https://www.ordnancesurvey.co.uk/products/os-open-map-local |
| Overture buildings | Open | ODbL theme; sources OSM (ODbL), Microsoft (ODbL), Google and Esri (CC BY 4.0) | Global GeoParquet, monthly (2026-10-21.0) | GERS id | Pre-conflated gap filling | https://docs.overturemaps.org/guides/buildings/ |
| Microsoft Global ML Building Footprints | Open | CDLA Permissive 2.0 (README); Overture lists ODbL | GB included (per-country table not checked) | none | Last-resort gap filling | https://github.com/microsoft/globalmlbuildingfootprints |
| HMLR INSPIRE Index Polygons | Open | OGL since July 2020 with an OS third-party caveat (unverified) | England and Wales, monthly | INSPIRE id | Plot boundaries to group buildings into sites | https://www.gov.uk/inspire-index-polygons-spatial-data |
| Google Open Buildings | n/a | CC BY 4.0 | **No UK coverage** | | | https://sites.research.google/open-buildings/ |
| EUBUCCO | n/a | mostly ODbL | **No UK coverage** | | | https://wagnerfe.github.io/eubucco |
| GlobalBuildingAtlas heights and LoD1 | Excluded | CC BY-NC 4.0 | Global | | Non-commercial | https://github.com/zhu-xlab/GlobalBuildingAtlas |

## 2. Addresses and identifiers

| Source | Tier | Licence | Coverage | Join key | Role | URL |
|---|---|---|---|---|---|---|
| OS Open UPRN | Open | OGL (check docs) | GB. 6-weekly (epoch 131, 29 Oct 2026). Points only, **no address text** | UPRN | Address points | https://www.ordnancesurvey.co.uk/products/os-open-uprn |
| OS Open Linked Identifiers | Open | OGL (check docs) | GB. 6-weekly CSV | UPRN to TOID (`BLPU_UPRN_TopographicArea_TOID_5`), UPRN to USRN, and others | **The open UPRN-to-building link** | https://docs.os.uk/os-downloads/identifiers/os-open-linked-identifiers |
| OS Open TOID | Open | OGL (check docs) | GB. 6-weekly | TOID with a point location | Places each building TOID so it can be matched to an OSM polygon | https://www.ordnancesurvey.co.uk/products/os-open-toid |
| OS Open USRN | Open | OGL (check docs) | GB. Monthly | USRN | Street context (optional) | https://www.ordnancesurvey.co.uk/products/os-open-usrn |
| Code-Point Open | Open | OGL (check docs) | GB. About 1.7 million postcode centroids, quarterly | postcode | Postcode fallback by nearest centroid | https://www.ordnancesurvey.co.uk/products/code-point-open |
| AddressBase (any tier) | Excluded | Licensed | | | | |
| NI Pointer (UPRNs) | Excluded | Paid, about £8,882 | | | | https://mapshop.nidirect.gov.uk/ |

## 3. Statistical geography

| Source | Tier | Licence | Coverage | Join key | Role | URL |
|---|---|---|---|---|---|---|
| ONS UPRN Directory (ONSUD) | Open (licence field unverified; contains OS, Royal Mail and Gridlink IPR) | check ONS licence page | GB, 6-weekly, about 515 MB | UPRN to OA, LSOA, MSOA, LAD | UPRN to statistical geography. **No NI** | https://ckan.publishing.service.gov.uk/dataset/onsud-latest1 |
| National Statistics Postcode Lookup (NSPL), Aug 2026 | Open | OGL (site footer) | UK incl. NI, 177 MB | postcode | Postcode to OA, LSOA, Data Zone, LAD, including NI | https://www.data.gov.uk/dataset/fa9ec151-618c-4b01-adb4-ecf772bd16fb |
| LSOA, MSOA, OA 2021 and LAD boundaries | Open | OGL | England and Wales | GSS codes | Point in polygon | https://geoportal.statistics.gov.uk/ |
| Scottish Data Zones 2022 | Open (boundary licence unverified; lookup OGL) | | Scotland, 7,392 zones | DZ code | Scottish LSOA equivalent | https://spatialdata.gov.scot/ |
| NISRA Data Zones and Super Data Zones 2021 | Open | OGL v3 | NI, 3,780 DZ in 850 SDZ | DZ2021, SDZ2021 | NI LSOA equivalent | https://www.nisra.gov.uk/publications/super-data-zone-boundaries-gis-format |
| NISRA Central Postcode Directory | Excluded | signed terms or paid | | | Use NSPL instead | |

## 4. Use and activity evidence

| Source | Tier | Licence | Coverage | Join key | Role | URL |
|---|---|---|---|---|---|---|
| VOA rating list downloads (2023 and 2026 lists, list entries and summary valuations) | **Restricted** | "An open government licence does not apply". Free; onward sharing only with the terms passed on. Full terms not yet read | England and Wales, over 2 million rows | UARN, billing authority reference, address, postcode. **No UPRN.** VOA refused an FOI for a UARN-to-UPRN lookup (4 Sept 2025) | SCat and PD codes (the CaRB3 inputs), description text, summary valuation floor areas | https://voaratinglists.blob.core.windows.net/html/rlidata.htm |
| VOA SCat code list | Open | OGL | | SCat code | Code meanings for the lookup | https://www.gov.uk/government/publications/special-category-codes-for-non-domestic-properties/special-category-scat-codes-for-non-domestic-properties |
| VOA Stock of Properties, March 2026 | Open | OGL | England and Wales, counts and rateable value by SCat, LSOA, MSOA | LSOA, SCat | **Validation:** premises counts per area and SCat. The 2023 edition also had floorspace | https://www.gov.uk/government/statistics/non-domestic-rating-stock-of-properties-march-2026 |
| Non-domestic EPC and DEC register | Open (OGL "except where otherwise stated"; address terms unverified) | | England and Wales since 2008, bulk CSV and API | UPRN (since Dec 2021, incomplete), address, postcode | Building type, floor area, main fuel, and an **address-to-UPRN bridge** for matching VOA records | https://get-energy-performance-data.communities.gov.uk/ |
| Scottish non-domestic EPC | Open, except address and postcode fields | OGL | Scotland, quarterly | address restricted | Floor area, fuel. Weak join | https://data.gov.scot/ |
| FSA Food Hygiene Rating Scheme | Open (terms on FSA page; data.gov.uk lists OGL) | | E, W, NI; Scotland via FHIS. Daily | FHRSID, coordinates, address | Food premises with business type | https://ratings.food.gov.uk/open-data |
| FSA approved establishments | Open | OGL | E and W monthly; NI and Scotland separate | approval number, address | **Food manufacturers, abattoirs, dairies** (evidence for `FA_F`) | https://www.data.gov.uk/dataset/2c80e0ce-ee1c-4f26-ba6f-1e1ae1bd8ee9 |
| NAEI point sources | Open | OGL | UK, 2023 file | site, grid reference | Large emitting sites, sector | https://naei.energysecurity.gov.uk/data/maps/emissions-point-sources |
| UK ETS allocation table | Open | OGL | UK installations | installation id | Installation list, free allocation | https://www.gov.uk/government/publications/uk-ets-allocation-table-for-operators-of-installations |
| SEPA SPRI | Open (sources conflict) | OGL | Scotland | site | Scottish emitting sites | https://sepa.org.uk/environment/environmental-data/spri |
| Climate Change Agreements facilities | Unclear ("No licence provided") | | UK | facility | Industrial facility list. Use only after checking | https://ckan.publishing.service.gov.uk/dataset/climate-change-agreements |
| EA Pollution Inventory | **Restricted** | EA Conditional Licence | England | site | Emissions per site | https://www.data.gov.uk/dataset/pollution-inventory |
| EA environmental permits register | **Restricted** (API under Conditional Licence; the OGL CSV is from 2015) | | England | permit, grid reference | Permitted industrial sites | https://www.data.gov.uk/dataset/c04dd73f-5308-41a6-9655-f35ed41a25d3 |
| Companies House basic company data | Unclear (licence not stated) | | UK, registered office only | company number, postcode | Weak SIC evidence. Registered office is not the site | https://download.companieshouse.gov.uk/en_output.html |
| Scottish Assessors valuation roll | Excluded | bulk sales suspended May 2024 | | | | https://www.saa.gov.uk/ |
| NI LPS valuation list | Excluded | paid | | | | https://www.finance-ni.gov.uk/ |
| HMLR CCOD and OCOD | Excluded | registration and revocable licence | | | | |

## 5. Height

| Source | Tier | Licence | Coverage | Role | URL |
|---|---|---|---|---|---|
| EA LIDAR composite DSM and DTM, 1 m | Open | OGL | England | Height = DSM minus DTM, per footprint | https://www.data.gov.uk/dataset/cf3f1137-c12b-44a1-a835-e80fe4a60b92 |
| DataMapWales LiDAR 2020-22, 1 m COG | Open | OGL on the COG records | Wales | as above | https://datamap.gov.wales/ |
| Scottish Remote Sensing Portal | Open in part (licence varies by phase; some phases reported non-commercial) | check per phase | Partial Scotland | as above, where covered and open | https://remotesensingdata.gov.scot/ |
| OpenDataNI LiDAR | Open | OGL | About 14-17% of NI | as above, where covered | https://admin.opendatani.gov.uk/ |
| OS Building Height Attribute; OS NGD Building Features | Excluded | PSGA or paid | | | |
| GHS-BUILT-H | Open | CC BY 4.0 | Global, 100 m | Context only, too coarse | |

## 6. Energy and calibration

| Source | Tier | Licence | Coverage | Role | URL |
|---|---|---|---|---|---|
| NBD phase 2 Factory summary tables | Open (gov.uk) | OGL (check workbook cover) | GB | **Targets:** premises, SCUs, floor area, floor area percentiles, median EUI and regional shares per CaRBE Factory group | https://assets.publishing.service.gov.uk/media/6a745f873a690e9ef0ea6cb7/NBD_Factory_Summary.xlsx |
| NBD synthetic population | Open | CC BY 4.0 | GB, MSOA and LAD | **Targets** per MSOA by class: floor area and energy | https://reshare.ukdataservice.ac.uk/858479/ |
| DESNZ sub-national electricity and gas | Open | OGL | GB. Non-domestic at MSOA. 2024 data released Dec 2025 | Control totals | https://www.gov.uk/government/collections/sub-national-electricity-consumption-data |
| ND-NEED 2026 | Open | OGL | England and Wales | Intensity by use and size | https://www.gov.uk/government/statistics/non-domestic-national-energy-efficiency-data-framework-nd-need-2026 |
| BEES | Open (reports) | OGL | England and Wales, 2014-15 | Building-services intensity benchmarks | https://www.gov.uk/government/publications/building-energy-efficiency-survey-bees |
| NAEI point sources, UK ETS | Open | OGL | UK | Site energy back-derived from emissions (method as COMIT note 04) | see §4 |
| National Heat Map (2012) | Excluded | not available | | | |

## 7. Gaps and traps

- **No open address gazetteer.** OS Open UPRN has no address text, and the VOA has no UPRN.
  Matching a VOA record to a building therefore goes through the EPC register (which holds
  address and UPRN), OSM `addr:*` and `name` tags, or postcode plus size. This is the
  single weakest link in the plan.
- **The VOA data that CaRB3 and CaRBE are built from is restricted.** Until its terms are
  read and cleared, the released table carries only open evidence and a VOA-derived layer is
  kept separately.
- **No open building height or use product.** OS NGD and the Building Height Attribute are
  licensed. Treat any OS 6 m default height seen in derived data as missing.
- **Northern Ireland is thin:** no open UPRNs, no open valuation list, partial LiDAR. Plan on
  OSM, NSPL, Data Zones, FSA and Overture footprints.
- **Scotland** has no open valuation data and only partial open LiDAR.
- **Looks open, is not:** VOA list downloads, EA Pollution Inventory and permits API,
  Scottish roll, NI LPS, NISRA postcode directory, HMLR CCOD/OCOD, GlobalBuildingAtlas.
- **Licence unclear, check before use:** ONSUD, Climate Change Agreements, Companies House.
