# CaRB3 processes vs COMIT processes — how the two taxonomies compare

**Question this note answers:** given a list of processes and equipment assigned to each CaRB3 *Factory* activity, how does that decomposition compare with what COMIT already models? Where do the two line up, where does COMIT have more detail, and what is simply invisible to it?

Extends [11_sector_coverage_and_carb3_mapping.md](11_sector_coverage_and_carb3_mapping.md), which maps COMIT **sectors** to CaRB3 **activities**. This note goes one level deeper, to processes and technologies.

Data:

| File | What |
|---|---|
| [`data/carb3_factory_processes.json`](data/carb3_factory_processes.json) | The supplied CaRB3 list, verbatim — 55 activities → processes → equipment |
| [`data/comit_sector_processes.json`](data/comit_sector_processes.json) | COMIT in the same three-level shape — 17 sectors → processes → technologies |
| [`data/comit_sector_processes.csv`](data/comit_sector_processes.csv) | Flat version carrying the commodity and technology codes, for joining |
| [`data/carb3_comit_crosswalk.csv`](data/carb3_comit_crosswalk.csv) | All 55 activities with COMIT sector, coverage verdict and process analogue |

Regenerate the COMIT side with [`examples/build_comit_process_taxonomy.R`](examples/build_comit_process_taxonomy.R).

---

## 1. The headline

The two taxonomies are **not two descriptions of the same thing at different resolutions**. They decompose industry along different axes, and that matters more than any coverage count:

| | CaRB3 | COMIT |
|---|---|---|
| Level 1 | Activity — *what the site is* (55) | Sector — *what industry it belongs to* (17) |
| Level 2 | Unit operation — *what physically happens* (128 pairs, 76 distinct names) | Energy service or product stage — *what it needs or makes* (94 pairs, 30 families) |
| Level 3 | Equipment type (247 entries, 218 distinct) | **Fuel variant** of one technology (397) |
| Varies by | Physical process engineering | Which fuel the service runs on |

The bottom levels are **orthogonal**. CaRB3 distinguishes a jaw crusher from a cone crusher; COMIT distinguishes a gas-fired high-temperature heat boiler from a hydrogen-fired one. **82 of COMIT's 94 processes have variants that differ only by `technology_category`** — i.e. by fuel. Neither taxonomy can express the other's distinction.

That is not a defect. COMIT exists to answer *"what does it cost to switch this energy service to a different fuel?"*, so fuel is the axis it needs. CaRB3 exists to describe building stock, so equipment is the axis it needs.

## 2. Scale comparison

| Measure | CaRB3 (Factory class) | COMIT |
|---|---|---|
| Top-level entries | 55 activities | 17 sectors (16 industrial + Hydrogen) |
| Process entries | 128 activity-process pairs | 94 sector-process pairs |
| Distinct process labels | 76 | 30 families |
| Bottom-level entries | 247 (218 distinct) | 397 technologies |
| Bottom entries per process | 1.9 | 4.2 (max 12) |

COMIT has **more technologies but fewer distinct processes** — it goes narrow and deep on fuel options within a small set of services, where CaRB3 goes wide and shallow across many physical operations.

## 3. What a COMIT "process" actually is

Stripping the sector suffix from the 94 sector-process pairs leaves **30 families**, and they split into two very different kinds:

**Generic energy services — 10 families, 73 of 94 pairs (78%)**

| Family | Sectors |
|---|---|
| Demand commodity (the sector's final output) | 12 |
| Other energy services | 11 |
| Motor drive | 10 |
| Low temperature heat | 9 |
| Low temperature space heat | 8 |
| High temperature heat | 7 |
| Drying / Separation services | 6 |
| Low-temperature steam/heat from CHP | 6 |
| Refrigeration | 2 |
| Low-temperature steam/heat from CHP/boilers | 2 |

These are replicated near-identically across sectors. Ceramics, Textiles and Vehicles are, structurally, *the same model* with different demand levels.

**Product and material stages — 21 pairs**

Clinker, Cement, Lime, Pig iron, Liquid steel, Hot rolled steel, Finished steel, Sinter, Ammonia, High-value chemicals, Melted refined glass, Finished glass, the four paper stages, Petroleum products, Generated hydrogen.

Only **six sectors** have a genuine multi-stage product chain: Cement, Lime, Iron & steel, Chemicals, Glass, Paper — plus Refineries with a single stage. These are exactly the sectors carrying process emissions (see [14_emissions_source_split.md](14_emissions_source_split.md)), which is not a coincidence: COMIT models the chemistry where the chemistry emits.

Everywhere else, the "process" list is just energy services and a demand commodity.

## 4. Activity coverage

All 55 activities, classified in [`data/carb3_comit_crosswalk.csv`](data/carb3_comit_crosswalk.csv):

| Verdict | Count | Meaning |
|---|---|---|
| `direct` | 31 | Maps cleanly to a COMIT sector |
| `absent` | 11 | No COMIT representation at all |
| `partial` | 3 | Maps, but only part of the activity is modelled |
| `catch-all` | 3 | NEC ↔ COMIT's `Other` |
| `gap` | 3 | Waste-handling; folded into `Other`, candidate for a new sector |
| `generic` | 2 | FA01 Workshop / FA02 Factory — unattributable from CaRB3 alone |
| `weak` | 1 | Industrial Minerals NEC → Lime, by proximity only |
| `ambiguous` | 1 | "Mill" — could be flour, paper, textile or metal |

The 11 `absent` activities are dominated by two themes note 11 already flagged: **extraction** (7 Mineral Production variants, Pumping Mines) and **servicing / non-manufacturing** (vehicle repair, exhaust & tyre, Laboratory, Post Office sorting, Minewater treatment).

## 5. The process-level gap

Of the **76 distinct CaRB3 process names**, how many can COMIT represent as a distinct process?

| COMIT representation | Count | Examples |
|---|---|---|
| Collapses into a heat service | 12 | Firing, Calcination, Drying, Pasteurisation, Distillation, Melting |
| Collapses into motor drive | 20 | Crushing, Milling, Screening, Rolling, Machining, Conveying |
| Collapses into refrigeration | 2 | Freezing/chilling, Carcass chilling |
| Is a real COMIT product stage | 5 | Ore reduction, Steelmaking, Chemical synthesis, Cracking, Reduction |
| **No analogue — invisible** | **37** | Welding, Painting, Sorting, Packaging, Casting, Forming, Printing, Etching, Fermentation, Tanning, Germination, Stunning, Quenching, Assembly |

*(The bucketing is analyst judgement; the underlying lists are in the JSON files.)*

So **39 of 76 map, 37 do not**. But note what "map" means: 34 of the 39 *collapse* — a jaw crusher and a hammer mill are both just "motor drive" load. Only 5 survive as a distinct modelled process.

The 37 invisible ones cluster tellingly: **fabrication and finishing operations** (welding, painting, machining, assembly, polishing, moulding, casting) and **biological/chemical batch operations** (fermentation, germination, composting, anaerobic digestion, tanning). Neither is represented, because neither is a distinguishable energy service in COMIT's ontology — they are all electricity or heat once you get down to the meter.

## 6. Where COMIT is richer

The comparison runs the other way too. For six sectors, COMIT has detail the CaRB3 list does not:

| CaRB3 | COMIT |
|---|---|
| Cement Works → Calcination, Milling (2 processes, 4 equipment) | Cement → Clinker (8 technologies incl. 6 CCS variants), Cement (3) |
| Iron and/or Steel Works → 3 processes, 6 equipment | Iron & steel → Pig iron (5), Liquid steel (4), Hot rolled steel (2), Sinter (1), Finished steel (1) |
| Chemical Works → 3 processes, 6 equipment | Chemicals → 12 processes, 55 technologies incl. 8 steam-cracker variants |

COMIT's extra depth is almost entirely **decarbonisation options** — CCS variants, fuel-switched variants, electrified variants. CaRB3 has no axis for those at all, because a building-stock classification has no reason to.

## 7. Practical implications

1. **Use CaRB3 for site identification, not process structure.** For the 31 `direct` activities, CaRB3/VOA gives a floorspace-based site register that can cross-check NAEI. Its process lists cannot populate COMIT's technology structure, because they describe a different thing.
2. **Do not expect an equipment-level join.** Any attempt to map 218 CaRB3 equipment types onto 397 COMIT technologies will fail: the former vary by machine type, the latter by fuel. A join is only meaningful at the activity ↔ sector level, which is what the crosswalk provides.
3. **The 37 invisible processes are a scoping question, not a data gap.** Representing welding or fermentation as distinct processes would mean adding energy services COMIT does not have. Worth doing only if a decarbonisation lever attaches to them specifically — and for most, the lever (electrify the heat, electrify the motor) is already captured generically.
4. **The CaRB3 list is a good prompt for the reverse check.** Activities like Brewery listing "Fermentation" and Tannery listing "Tanning" are a reminder that COMIT's Food & drink and Textiles sectors are modelled purely as heat + motor + drying, with no process-specific technology at all — consistent with them carrying **zero process emissions** in note 14.

## 8. Caveats

1. **The CaRB3 list is as supplied.** It was provided as a dictionary of processes and equipment per activity; it is stored verbatim and has not been checked against the NDBS source document. Activity names are the supplied ones.
2. **FA codes are from note 11, where known.** Note 11 cites Table 28 of the NDBS report but does not give a code for every activity. Codes are left blank in the crosswalk where they could not be sourced — they have not been guessed. Blank codes affect 9 rows, mostly the Mineral Production family.
3. **The crosswalk is analyst judgement**, built on note 11's sector↔activity mapping. The `coverage` verdict and the `comit_process_analogue` column are interpretive; the counts in §2 and §3 are computed from the data files.
4. **COMIT's side is workbook-derived** from `comit_input_1_4_0_public_updated.xlsx` (public v1.4.0). Sector and technology structure are real; the numbers in that workbook are dummy figures, though this note uses only structure, not values.
