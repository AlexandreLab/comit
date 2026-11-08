# 01 Research summary

Research done on 2026-11-08 from the published reports, publisher pages and the methods
literature. Items marked **(unconfirmed)** came from a search summary or an abstract and
were not checked in the full text. Numbers in square brackets point to the reference list
at the end.

## 1. The National Buildings Database (NBD)

### 1.1 What exists

| Item | What it is | Ref |
|---|---|---|
| NBD phase 1 ("Non-Domestic Building Stock", NDBS) | DESNZ research paper 2024/005, published 8 Feb 2024, by UCL Consultants. Five PDFs: executive summary, Part 1 stock description (with Annex 1 Table 28, the CaRB3 activity list), Part 2 energy consumption, Part 3 hospitality, and a supplement on large off-gas-grid premises. England and Wales only | [1][2][3] |
| NBD phase 2 | "National Buildings Database: Understanding Great Britain's Non-Domestic Buildings", DESNZ, published 8 May 2026 and updated 6 Aug 2026, 273 pages. UCL Energy Institute Building Stock Lab with Verco and Winning Moves. Covers Great Britain (adds Scotland), snapshot at 1 April 2023 | [4] |
| Phase 2 summary tables | 16 Excel workbooks on gov.uk, one overview and one per class, including `NBD_Factory_Summary.xlsx` | [5] |
| NBD synthetic population | About 2.2 million synthetic premises at local authority and MSOA level, with size, age, activity class and energy. CC BY 4.0, UK Data Service, published 29 Jun 2026 | [6] |

The full NBD is restricted to DESNZ and wider government. The phase 2 report says it
"relies on commercial or restricted licenses for datasets such as OS and VOA" [4]. No phase 3
was found. The UK Data Service record mentions a future "National Buildings Model"
**(unconfirmed)**.

### 1.2 CaRB3 and CaRBE

**CaRB3** (Carbon Reduction in Buildings, version 3) is the phase 1 taxonomy [2]:

- It is driven by the combination of the VOA **Special Category (SCat) code** and the VOA
  **Primary Description (PD) code**. In 2017 there were 409 SCat codes and 106 PD codes.
  For example, SCat 096 ("Factories, workshops and warehouses") with PD IF3 gives "Workshop".
- 1,180 SCat/PD combinations become 315 activities in 17 classes. Two classes derived from
  OS AddressBase (Commercial, Domestic) are added, giving 19 classes and 401 activities.
- Premises with no VOA record (for example places of worship) are classed from the
  AddressBase classification instead.
- Part 1 Table 1 gives the Factory class 61 activities, but Table 28 lists only 55 distinct
  `FA` codes. The gap is unexplained. This repository's
  `docs/notes/data/carb3_comit_crosswalk.csv` holds the 55.
- The SCat/PD to activity lookup is **not published**: Table 28 has no SCat or PD column.

**CaRBE** is the phase 2 taxonomy, described as improving on CaRB3 [4]:

- It is built bottom up from a "derived activity" per premises, taken from VOA, Scottish
  Assessors (SAA) or AddressBase data.
- 365 activities and 84 activity groups in 15 reported classes, plus Domestic,
  Miscellaneous and UNCODED, which are not reported (Table 4-3).
- **Factory has 58 activities in 7 groups.** The groups and their codes, from the Factory
  workbook [5]:

| Code | CaRBE Factory group | Premises | SCUs | Floor area (Mm²) | Median total EUI (kWh/m²/yr) | Total energy (GWh) |
|---|---|---|---|---|---|---|
| `FA_A` | Workshops etc | 230,177 | 142,602 | 68.71 | 46 | 5,381.89 |
| `FA_B` | Factories etc | 31,855 | 26,336 | 88.57 | 73 | 29,105.61 |
| `FA_C` | Vehicle repair etc | 30,886 | 25,148 | 8.99 | 46 | 515.19 |
| `FA_D` | Mineral production etc | 2,967 | 1,402 | 1.36 | 236 | 851.48 |
| `FA_E` | High Energy Industries | 1,476 | 925 | 9.06 | 271 | 6,534.86 |
| `FA_F` | Food & Drink Production | 1,368 | 1,074 | 3.54 | 293 | 5,985.74 |
| `FA_O` | Factory, other | 1,444 | 714 | 0.98 | 57 | 155.18 |

  Source: phase 2 report, Tables 3.6-1 and 3.6-2. SCU means "self-contained unit" (see
  §1.3). The total GWh column is metered energy for matched premises only, so it is not a
  stock total.

- The report states that CaRBE classes are **not** SIC-based: a refiner's head office is
  "office work", not refining.
- The mapping from each CaRBE activity to its group is **not** in the report text. The
  workbook has "CaRBE Code" columns at group level only.

**Consequence for this project.** Activity-level classification uses the CaRB3 `FA` codes
(published, already in this repository). Group-level classification uses the CaRBE groups
`FA_A` to `FA_O` (published, with calibration targets). The link between the two, and the
SCat/PD lookup behind both, must be rebuilt and versioned here. Asking UCL for the official
lookup is the cheaper route and should be tried first.

### 1.3 The NBD method, and what replaces each licensed input

The NBD hierarchy is **premises → UPRN → building (footprint, TOID) → SCU → site** [4][7]:

- A premises is the occupier unit (a VOA hereditament).
- An **SCU** groups adjoining footprints so that no premises is ever split across SCUs.
  This comes from Taylor et al. (2014) [8].
- A site groups SCUs on one campus, using HM Land Registry and OS Sites polygons.
- Of non-domestic SCUs, 59% have one occupier, 27% share with dwellings and 14% share with
  another non-domestic occupier.

Floor area takes the first available of: VOA (72% of premises), non-domestic EPC (5%),
domestic EPC (only some activities), 3DStock geometry (18%, the "slicer" cuts the SCU at
empirical floor-to-floor heights), or nothing (about 1%). Everything is normalised to gross
internal area (GIA).

Energy is annual metered gas and electricity from ND-NEED, matched to UPRN. For Factory
premises, 42% matched an electricity meter and 14% a gas meter. Bulk fuels are not
available at premises level.

| NBD input | Status | Open substitute here |
|---|---|---|
| VOA list with non-public fields (SCat, PD, floor area, age) | Restricted | Public VOA rating list download (free, restricted terms, not OGL); VOA Stock of Properties aggregates (OGL) |
| OS AddressBase Premium (address, UPRN, classification) | Licensed | OS Open UPRN (points only, no address), EPC register addresses, OSM `addr:*` tags |
| OS MasterMap Topography (footprints, TOIDs) | Licensed | OSM footprints; OS OpenMap Local buildings; OS Open TOID points plus OS Open Linked Identifiers (UPRN to building TOID) |
| OS Sites, HMLR National Polygon | Licensed | HMLR INSPIRE Index Polygons; OSM `landuse=industrial` and `man_made=works` |
| ND-NEED meter data | Restricted | DESNZ MSOA non-domestic gas and electricity; NBD phase 2 medians; NBD synthetic population |
| Non-public EPC and DEC fields | Restricted | Public EPC and DEC registers |
| SAA valuation roll | Restricted, bulk sales suspended | None at premises level; Scottish roll statistics |
| EA LiDAR | Open | Same |

### 1.4 Validation the NBD published

- **Activity accuracy:** in a telephone QA survey of 1,449 premises, the activity was
  correct for 69%, present but not primary for 5%, and wrong for 26% [4]. Expect no better
  from open data.
- **External count checks:** only about 5% of activities were within ±15% of external
  counts [4].
- **Not published:** a premises-to-footprint match rate for Factory, a LiDAR height error,
  or a floor-area accuracy figure.

## 2. Methods literature, by pipeline step

### 2.1 Classifying building use

| Study | Method and result | Ref |
|---|---|---|
| Fill, Eichelbeck, Ebner 2024 (preprint) | Graph transformer on OSM, Europe including the UK. 9 classes including industrial. Kappa 0.754. F1 for non-residential classes only 0.38 to 0.72; commercial and industrial are often confused. Labels come from OSM's own tags | [9] |
| Hecht, Meinel, Buchroithner 2015 | Random forest on footprint shape and neighbourhood, Germany. About 90 to 95% from vector footprints | [10] |
| Atwal et al. 2022 | Residential versus non-residential from OSM geometry and context, US. About 98% | [11] |
| Bandam et al. 2022 | Machine learning on OSM building data, Germany | [12] |
| Hussain and Chen 2014 | Three-level classification for Manchester from MasterMap and AddressBase. The only UK method found | [13] |
| Fleischmann and Arribas-Bel 2022 | GB "spatial signatures": 16 urban form and function types, including a warehouse/industrial type. A free context feature, not a building classifier | [14] |
| Milojevic-Dupont et al. 2023 (EUBUCCO) | EU-27 plus Switzerland. **No UK** | [15] |

**Implication:** label from records (VOA, EPC, FSA, site registers, OSM tags) wherever they
exist. Use a morphology classifier only for footprints with no record, and only to decide
"industrial or not", never the activity.

### 2.2 Height and storeys

| Study or source | Method and result | Ref |
|---|---|---|
| Evans, Liddiard, Steadman 2017 (3DStock) | LiDAR-derived height per footprint, eaves and maximum. Floor-to-floor heights by activity give storeys | [7] |
| Milojevic-Dupont et al. 2020 | XGBoost on footprint morphology. Mean absolute error (MAE) 1.5 to 3.0 m. Training data is mostly dwellings | [16] |
| Stipek et al. 2024 | 65 morphology features, 74.6 million buildings (US, FR, DE). 95% within 3 m | [17] |
| GHS-BUILT-H R2023A | 100 m grid. Too coarse for single sheds | [18] |
| VOA and agents' practice for warehouses | VOA basic rate for distribution warehouses assumes 9 to 12 m eaves. UK average clear height for large sheds rose from 7.6 m to 11.5 m over 20 years | [19] |

**Implication:** compute height from the LiDAR normalised surface (DSM minus DTM) per
footprint, with an inward buffer. Store the median, 90th percentile and maximum, because
roof plant and chimneys inflate the maximum. For sheds, a storey count from height is
meaningless: treat a shed as one storey plus an optional mezzanine, and use activity-specific
floor-to-floor heights only for multi-storey industrial buildings.

### 2.3 Linking addresses and valuation records to footprints

- 3DStock matched VOA hereditaments to AddressBase UPRNs (98% in Camden), then UPRNs to
  MasterMap footprints by point in polygon [7]. It names the three hard cases: several
  address points per footprint, several addresses per point, and one building made of
  several polygons of which only some carry an address.
- OS Open Linked Identifiers holds `BLPU_UPRN_TopographicArea_TOID_5`, the UPRN to building
  TOID link, about 40.7 million rows in April 2024 [20]. OS describes using it to get a
  building outline from a UPRN.
- OSM UK practice for `ref:GB:uprn` keeps only clean one-to-one point-in-polygon matches,
  because UPRN points can be offset and one building can carry a parent UPRN plus unit
  UPRNs (anecdotal, OSM wiki and talk-gb).
- No study was found on the accuracy of apportioning VOA floor area across a multi-building
  site. That step is this project's own design.

**Implication:** a many-to-many bridge table (UPRN, premises, building) with a method and a
confidence on every row, not a single join.

### 2.4 Energy at building or site level

| Study or source | Point | Ref |
|---|---|---|
| Oraiopoulos and Howard 2022 | Urban building energy model errors run from about 1% on annual aggregates to about 1000% on single buildings | [21] |
| Reinhart and Cerezo Davila 2016; Ferrando et al. 2020 | Reviews of urban building energy modelling. No standard ontology or test cases | [22][23] |
| BEES (BEIS 2016) | Industrial premises were about 22% of non-domestic floor area. **Process energy was not measured**, so BEES gives building-services energy only | [24] |
| ND-NEED 2026 | Aggregates by building use and size, OGL | [25] |
| Manz et al. 2018; Hotmaps; sEEnergies | Georeferenced EU industrial site databases built from ETS and emissions registers | [26] |
| egon-data `industrial_sites` | Open code that spreads regional industrial demand onto OSM land-use polygons and sites | [27] |

**Implication:** a floor-area benchmark is a poor primary estimate for process industry,
because energy follows output, not area. The NBD's own medians differ six-fold between
`FA_A` (46) and `FA_F` (293). Use reported site data for large sites, group medians for the
rest, calibrate to DESNZ MSOA totals, and attach an uncertainty class to every value.

### 2.5 OSM data quality

- Herfort et al. 2023: footprint completeness in Europe and Central Asia about 71% in urban
  areas [28].
- Biljecki, Chow, Lee 2023: OSM attributes are heterogeneous; floors and building type are
  the most often recorded and usually accurate where present [29].
- Hecht, Kunze, Hahmann 2013: completeness measures are sensitive to how buildings are split
  in the reference data [30].
- **No GB study** of OSM `building:levels` or `height` completeness, or of footprint
  completeness on industrial estates, was found. This project has to measure it.

### 2.6 Tooling

- **GeoParquet:** 1.1.0 added an optional bounding-box covering column. 2.0.0 builds on Parquet's native GEOMETRY type
  **(unconfirmed: the release date and reader support were not checked)**. Use
  1.1 until the readers in use are checked.
- **Benchmarks** (pyrosm documentation, one laptop): buildings for Finland in 10 to 42 s
  across pyrosm and QuackOSM. QuackOSM runs out of memory on large files when it keeps every
  tag column [31]. Great Britain's extract is 2.0 GB, so filter tags with `osmium` first.
- **Overture buildings:** GeoParquet, monthly, OSM first, then Esri, Google and Microsoft
  machine-learned footprints, with stable GERS identifiers [32].

## References

1. DESNZ (2024) National Buildings Database phase 1. https://www.gov.uk/government/publications/national-buildings-database-phase-1-non-domestic-building-stock-in-england-and-wales
2. DESNZ (2024) Non-domestic building stock, Part 1: stock description. https://assets.publishing.service.gov.uk/media/65c3b42a3f634b000d42c67b/non-domestic-building-stock-part-1-stock-description.pdf
3. DESNZ (2024) Non-domestic building stock, Part 2: energy consumption. https://assets.publishing.service.gov.uk/media/65c3ba2928a4a0000dd2ba59/non-domestic-building-stock-part-2-energy-consumption.pdf
4. DESNZ (2026) National Buildings Database phase 2: understanding Great Britain's non-domestic buildings. https://assets.publishing.service.gov.uk/media/69fd9d508cc72d2f863ea60c/national-buildings-database-phase-2.pdf ; landing page https://www.gov.uk/government/publications/national-buildings-database-phase-2-understanding-great-britains-buildings
5. DESNZ (2026) NBD Factory summary tables. https://assets.publishing.service.gov.uk/media/6a745f873a690e9ef0ea6cb7/NBD_Factory_Summary.xlsx
6. UK Data Service (2026) NBD synthetic population, SN 858479, CC BY 4.0. https://reshare.ukdataservice.ac.uk/858479/ , doi:10.5255/UKDA-SN-858479
7. Evans S., Liddiard R., Steadman P. (2017) 3DStock: a new kind of three-dimensional model of the building stock of England and Wales. Environment and Planning B 44(2), 227-255. doi:10.1177/0265813516652898. Also Steadman P. et al. (2020) Building stock energy modelling in the UK: the 3DStock method and the London Building Stock Model. Buildings and Cities 1(1), 100-119. doi:10.5334/bc.52
8. Taylor S., Fan D., Rylatt M. (2014) Enabling urban-scale energy modelling: a new spatial approach. Building Research & Information 42, 4-16. doi:10.1080/09613218.2013.813169
9. Fill J., Eichelbeck M., Ebner M. (2024) Predicting building types and functions at transnational scale. arXiv:2409.09692
10. Hecht R., Meinel G., Buchroithner M. (2015) Automatic identification of building types based on topographic databases. International Journal of Cartography 1(1), 18-31. doi:10.1080/23729333.2015.1055644
11. Atwal K.S. et al. (2022) Predicting building types using OpenStreetMap. Scientific Reports 12, 19976. doi:10.1038/s41598-022-24263-w
12. Bandam A. et al. (2022) Classification of building types in Germany: a data-driven modeling approach. Data 7(4), 45. doi:10.3390/data7040045
13. Hussain M., Chen D. (2014) Creating a three level building classification using topographic and address-based data for Manchester. ISPRS Annals II-2, 67-73
14. Fleischmann M., Arribas-Bel D. (2022) Geographical characterisation of British urban form and function using the spatial signatures framework. Scientific Data 9, 546. doi:10.1038/s41597-022-01640-8
15. Milojevic-Dupont N. et al. (2023) EUBUCCO v0.1. Scientific Data 10, 147. doi:10.1038/s41597-023-02040-2
16. Milojevic-Dupont N. et al. (2020) Learning from urban form to predict building heights. PLOS ONE 15(12), e0242010. doi:10.1371/journal.pone.0242010
17. Stipek C. et al. (2024) Inferring building height from footprint morphology data. Scientific Reports 14, 18651. doi:10.1038/s41598-024-66467-2
18. Pesaresi M. et al. (2024) GHS-BUILT-H R2023A methods. International Journal of Digital Earth 17(1). doi:10.1080/17538947.2024.2390454
19. VOA rating manual (distribution warehouses) and Knight Frank warehouse research, as summarised in the literature search (unconfirmed: figures not checked in the primary documents)
20. Ordnance Survey, OS Open Linked Identifiers technical specification, `BLPU_UPRN_TopographicArea_TOID_5`. https://docs.os.uk/os-downloads/identifiers/os-open-linked-identifiers/os-open-linked-identifiers-technical-specification/blpu_uprn_topographicarea_toid_5 ; April 2024 release notes https://docs.os.uk/os-downloads/~/changes/AJZwzCsyrD9hiTbOxIbO/identifiers/os-open-linked-identifiers/release-notes/april-2024-epoch-34
21. Oraiopoulos A., Howard B. (2022) On the accuracy of urban building energy modelling. Renewable and Sustainable Energy Reviews 158, 111976. https://discovery.ucl.ac.uk/10162701/
22. Reinhart C., Cerezo Davila C. (2016) Urban building energy modeling: a review of a nascent field. Building and Environment 97, 196-202. doi:10.1016/j.buildenv.2015.12.001
23. Ferrando M. et al. (2020) Urban building energy modeling (UBEM) tools: a state-of-the-art review. Sustainable Cities and Society 62, 102408. doi:10.1016/j.scs.2020.102408
24. BEIS (2016) Building Energy Efficiency Survey (BEES). https://www.gov.uk/government/publications/building-energy-efficiency-survey-bees
25. DESNZ (2026) ND-NEED 2026. https://www.gov.uk/government/statistics/non-domestic-national-energy-efficiency-data-framework-nd-need-2026
26. Manz P. et al. (2018) Developing a georeferenced database of energy-intensive industry plants. eceee Industrial Summer Study 2018
27. eGon-data, industrial sites module. https://github.com/openego/eGon-data (unconfirmed: module path not checked)
28. Herfort B. et al. (2023) A spatio-temporal analysis investigating completeness and inequalities of global urban building data in OpenStreetMap. Nature Communications 14. doi:10.1038/s41467-023-39698-6
29. Biljecki F., Chow Y.S., Lee K. (2023) Quality of crowdsourced geospatial building information. Building and Environment 237, 110295. doi:10.1016/j.buildenv.2023.110295
30. Hecht R., Kunze C., Hahmann S. (2013) Measuring completeness of building footprints in OpenStreetMap over space and time. ISPRS International Journal of Geo-Information 2(4), 1066
31. pyrosm scaling benchmarks. https://pyrosm.readthedocs.io/en/latest/benchmarks/benchmarks_scaling.html
32. Overture Maps buildings guide. https://docs.overturemaps.org/guides/buildings/
33. VOA (2025) FOI response: lookup table for UARN and UPRN (refused, 4 Sept 2025). https://www.gov.uk/government/publications/lookup-table-to-connect-all-publicly-available-uarn-to-the-uprn-system/response-for-a-lookup-table-for-uarn-and-uprn-data
