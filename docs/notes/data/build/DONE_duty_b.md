# DONE — lane `duty_b`

Duty profiles and the COMIT process crosswalk (T17, the duty-profile and crosswalk task) for the
28 activities of `brief_duty_b.md`. Written 2026-09-15.

## Files written

| File | Rows |
|---|---|
| `activity_process_duty_profile_duty_b.csv` | 211 duty rows, covering all 180 register rows |
| `carb3_comit_process_crosswalk_duty_b.csv` | 180, exactly one per register row |
| `references_duty_b.csv` | 5 new references (35 more were reused from `references.csv`) |
| `check_duty_b.py` | the validator; **runs clean, 0 errors, 0 warnings** |

Nothing outside `build/` was touched. All 28 activities are `default`-set only — no named
non-default process set falls in this lane, so the §3.3 inheritance rule never fires here.

```
$ python3 docs/notes/data/build/check_duty_b.py
lane duty_b: 180 register rows, 211 duty rows, 180 crosswalk rows, 275 references (5 new)
0 error(s), 0 warning(s)
```

## Row counts and coverage

**Duty families used** (9 of the 12; `EN`, `HRS` and `NEUOTH` are unused — see gaps 3 and 6):

| Family | Rows | | Family | Rows |
|---|---|---|---|---|
| `MOT` (motive power) | 128 | | `REF` (refrigeration) | 7 |
| `SPC` (space heat) | 25 | | `DRY` (drying) | 7 |
| `OTH` (other services) | 11 | | `PHEAT` (refinery process heat) | 7 |
| `LTH` (low-temperature heat) | 9 | | `HTH` (high-temperature heat) | 8 |
| `STM` (steam) | 9 | | | |

**Grade bands** (65 heat rows, every one graded — check (c) passes):
rank 2 `60-100C` × 36 · rank 3 `100-150C` × 10 · rank 4 `150-400C` × 7 · rank 5 `400-1000C` × 8 ·
rank 6 `>1000C` × 4. **No row sits in rank 1 `<60C`**: every heat duty found in these 28 activities
needs at least 60 °C. That is worth knowing for C10 (the heat cascade) — the lowest band is unused
by this half of the register.

**Evidence tier** (D10, the evidence ladder): `published_sec` 106 · `fallback` 81 · `engineering` 24 ·
`measured` 0. **Confidence**: medium 124 · low 83 · high 4.

**Populated vs blank, per column** (211 rows):

| Column | Populated | Note |
|---|---|---|
| `carb3_activity`, `process_set_id`, `process_id` | 211 | every key resolves to `activity_process_register.csv` |
| `duty_family`, `duty_share`, `evidence_tier`, `provenance`, `confidence` | 211 | all required fields |
| `carrier_id` | 211 | required on every family except `NEUOTH`, which is unused |
| `grade_rank` | 65 | exactly the 65 rows on a gradeable carrier; blank on all 146 others |
| `share_low`, `share_high` | 0 | **deliberate.** No source gives a *range for a share*. Several sources give a temperature range, but that belongs in the band choice, not in these columns |

**Crosswalk**: 61 `direct`, 56 `analogue`, 63 `none`. 40 distinct COMIT process codes used, no
sector-root code (`ICH`, `ICM`, … `IPP`) anywhere. The 63 `none` rows are the activities
`carb3_comit_crosswalk.csv` already records as `absent` or `ambiguous` — Laboratory, Post Office
Sorting Centre, Vehicle repair, Pumping Mines, all five extraction Mineral Production categories,
and Mill — plus `Paper Mill / effluent_water_services` and `Oil refinery / site_services`, which have
no analogue inside an otherwise-covered sector.

## The conventions I adopted, and why

These are judgement calls, applied uniformly, and repeated inside the provenance of every row they
touch so the table reads correctly without this file.

**1. The band is the one containing the *upper bound* of the stated requirement.** A duty must be
served at its maximum, so a source that says "900 – 1050 °C" puts the row in rank 6 `>1000C`, not
rank 5. Where a source names a *principal* requirement plus a minor secondary stream at another
grade, the band follows the principal and the secondary is written into the provenance as a known,
unquantified second duty (this is what happens to the paper machine's 430 °C stream).

**2. Two vectors serving the same duty need no split.** Pottery's `biscuit_firing` draws electricity
and gas, but both fire the kiln, so it is one row at 1.00. Same for `Works / process_heating`,
`Maltings / kilning_heat` (gas and biomass), `Scrap Metal / material_handling` (electric cranes and
diesel handlers — both shaft work), and 11 others. 149 of the 180 processes are single-duty.

**3. Two vectors serving *different* duties are split — see Q1 below.** 31 processes do this. For
the 9 refinery units the split is computed from **published vector weights**: `[oil_roadmap_2015]`
p37 gives electricity as 3.3 % of UK refinery energy and p36 gives the fuel mix (refinery fuel gas
47.3 %, petroleum coke 24.8 %, natural gas 21.3 %, fuel oil 6.7 %). For the other 22 the split is the
process's own `activity_process_energy_profile.csv` vector shares renormalised across the vectors it
draws — **a structural placeholder, not evidence**, so every one of those rows is
`evidence_tier = fallback, confidence = low` and says so.

**4. `evidence_tier` describes the number, not the grade.** `duty_share` is the value a row carries,
so where the share came from convention 3's fallback the row is tiered `fallback` even when its band
is `published_sec` and well sourced. `Paper Mill / paper_machine_drying` is the clearest case: the
150–180 °C band is a strong UK citation, the 0.91/0.09 split is not. See Q2.

**5. `OTH` binds `electricity` where the service really is electricity.** §3.4 says `OTH` "resolves
to whichever of the above the underlying service is", but lighting, office ICT, arc and resistance
welding, semiconductor process tools and electrolysis are none of heat, motive power or cooling.
11 rows do this. See Q3.

**6. Where no source exists at all, the family is read off the register's own equipment list.**
9 rows (Maltings grain handling and germination, Mineral Production - Oil lift and injection,
Tannery compressed air, and three others) have no citable source: `activity_process_register.csv`
names the equipment and `activity_process_energy_profile.csv` records its own share as "engineering
rationale" with no reference. Those rows are `fallback / low` and carry **no `[REF_ID]`**, with the
provenance saying exactly that. This is a deliberate departure from convention 2 of
`00_CONVENTIONS.md`: I would rather have a row that says "no source" than one that cites a repo file
as if it were a source. Nothing on those rows is a number — only a family assignment.

## The 31 split processes

| Activity | Process | Split | Basis |
|---|---|---|---|
| `Large industrial (> 20,000 m2) NEC` | `other_process` | OTH 0.36 + LTH@3 0.64 | renormalised profile shares |
| `Large industrial (> 20,000 m2) NEC` | `site_services` | MOT 0.95 + SPC@2 0.05 | renormalised profile shares |
| `Maltings - Non Trad` | `site_services` | MOT 0.50 + SPC@2 0.50 | renormalised profile shares |
| `Maltings - Trad` | `site_services` | MOT 0.67 + SPC@2 0.33 | renormalised profile shares |
| `Mill` | `site_services` | MOT 0.93 + SPC@2 0.07 | renormalised profile shares |
| `Mineral Production - Brine` | `vacuum_evaporation` | STM@3 0.71 + MOT 0.29 | renormalised profile shares |
| `Mineral Production - Brine` | `site_services` | MOT 0.75 + SPC@2 0.25 | renormalised profile shares |
| `Motor Vehicle Works` | `paint_shop` | DRY@4 0.51 + MOT 0.49 | renormalised profile shares |
| `Motor Vehicle Works` | `site_services` | MOT 0.83 + SPC@2 0.17 | renormalised profile shares |
| `Newspaper print works` | `site_services` | SPC@2 0.78 + MOT 0.22 | renormalised profile shares |
| `Oil refinery, gas processing etc` | `crude_vacuum_distillation` | PHEAT@4 0.97 + MOT 0.03 | **published weights** |
| `Oil refinery, gas processing etc` | `hydrotreating` | PHEAT@4 0.97 + MOT 0.03 | **published weights** |
| `Oil refinery, gas processing etc` | `catalytic_reforming` | PHEAT@5 0.97 + MOT 0.03 | **published weights** |
| `Oil refinery, gas processing etc` | `hydrogen_production` | PHEAT@5 0.99 + MOT 0.01 | **published weights** |
| `Oil refinery, gas processing etc` | `hydrocracking` | PHEAT@4 0.97 + MOT 0.03 | **published weights** |
| `Oil refinery, gas processing etc` | `fcc` | PHEAT@5 0.97 + MOT 0.03 | **published weights** |
| `Oil refinery, gas processing etc` | `alkylation` | STM@4 0.97 + REF 0.03 | **published weights** |
| `Oil refinery, gas processing etc` | `other_units` | PHEAT@5 0.98 + MOT 0.02 | **published weights** |
| `Oil refinery, gas processing etc` | `utilities_steam` | STM@4 0.90 + MOT 0.10 | **published weights** |
| `Paper Mill` | `stock_preparation` | MOT 0.74 + LTH@2 0.26 | renormalised profile shares |
| `Paper Mill` | `paper_machine_drying` | STM@4 0.91 + MOT 0.09 | renormalised profile shares |
| `Paper Mill` | `site_services` | MOT 0.54 + SPC@2 0.46 | renormalised profile shares |
| `Pottery` | `site_services` | MOT 0.87 + SPC@2 0.13 | renormalised profile shares |
| `Provender Mill` | `site_services` | MOT 0.48 + SPC@2 0.52 | renormalised profile shares |
| `Scrap Metal/Breakers Yard` | `site_services` | SPC@2 0.80 + MOT 0.20 | renormalised profile shares |
| `Shipbuilding/ repair, boatyard` | `steel_prep_cutting` | HTH@6 0.76 + MOT 0.24 | renormalised profile shares |
| `Shipbuilding/ repair, boatyard` | `painting_coating` | SPC@2 0.68 + MOT 0.32 | renormalised profile shares |
| `Shipbuilding/ repair, boatyard` | `site_services` | SPC@2 0.60 + MOT 0.40 | renormalised profile shares |
| `Tannery` | `site_services` | MOT 0.60 + SPC@2 0.40 | renormalised profile shares |
| `Wafer Fabrication` | `cleanroom_hvac` | MOT 0.25 + SPC@2 0.75 | renormalised profile shares |
| `Works` | `site_services` | MOT 0.93 + SPC@2 0.07 | renormalised profile shares |

**Two of these are known to be badly wrong in magnitude, and the direction is known.**
`Wafer Fabrication / cleanroom_hvac` at SPC 0.75 and `Paper Mill / paper_machine_drying` at MOT 0.09
both assume the activity's vector totals are equal. A fab is heavily electricity-dominated, so its
true SPC share is far below 0.75; a paper mill is heat-dominated, so its true MOT share is below
0.09. Both rows say this in their own provenance.

## Gaps, and why each is a gap

**Second duties dropped because no split is published.** Each is named in the provenance of the row
that displaced it, so nothing is silently lost:

| Activity | Process | Duty not written | Why |
|---|---|---|---|
| Laboratory | `hvac_ventilation` | `REF` (cooling) | register names cooling in the bundle; no split found |
| Laboratory | `lab_equipment` | `REF` (ultra-low-temperature freezers, −70 °C) | the repo's own `ult_freezer_optimisation` option names them; no share published |
| Laboratory | `space_water_heating` | `LTH` (domestic hot water) | bundled with space heat by the register; both served at the same grade, so the loss is a family label, not a band |
| Mineral Production - Oil | `processing_separation_export` | `LTH` (crude/wash-water heating below 100 °C) | named only in the repo's own option note; no vector share supports it |
| Newspaper print works | `press_auxiliaries` | `REF` (press and ink cooling) | register names it; no split found |
| Oil refinery | `hydrogen_production` | **`NEUOTH`** (SMR natural-gas feedstock) | see Q5 |
| Paper Mill | `paper_machine_drying` | a second steam stream at **430 °C** (rank 5) | `[paper_roadmap_2015]` names it but does not quantify it |
| Post Office Sorting Centre | `site_services` | `OTH` (lighting, office ICT) | register names them; no split found |
| Pottery | `glost_decoration_firing` | decoration firing at a lower band | on-glaze decoration fires well below glost; the register combines the two |
| Motor Vehicle Works | `paint_shop` | booth make-up air heating at rank 2 | inseparable from the oven bake in the gas vector |
| Vehicle repair workshop | `site_services` | `OTH` (lighting, ICT) and `REF` (refrigeration) | register names all three; no split found |
| Works | `surface_treatment` | `OTH` (the electrolytic rectifier load) | **probably the larger of the two duties.** The bath-heating `LTH` row is the one the evidence supports |
| Works, Workshop, Large industrial NEC | `process_heating` | the low-temperature stoving/paint-drying part | the register bundles duties spanning bands 3 to 6 into one process |

**Six register rows have no `activity_process_energy_profile.csv` row at all**, so their energy is
unquantified upstream; I still wrote a duty row for each (the duty exists whether or not its share
is known), at `fallback / low`:
`Mineral Production - Brine / brine_purification` · `Mineral Production - Inert /
mobile_crushing_screening` · `Mineral Production - Other Mineral Category / dewatering_pumping` ·
`Mineral Production - Putrescible / pasteurisation_digester_heating` ·
`Mineral Production - Rock, Sand, Clay etc. / washing_classification` and `/ dewatering_pumping`.

**Sources I could not read.** ESAB's oxy-fuel page (`REF_ESAB`, the ref the repo's own
`process_decarbonisation_options.csv` cites for torch cutting) returns HTTP 403; I cite
`[FRACTORY_OXYFUEL]` for the flame temperature instead and say so. The Feed Strategy pelleting
reference guide PDF is behind Cloudflare; I used `[LAMECC_STEAM]`, vendor material, flagged `low`.
The MAGB energy-use page (`MAGB_ENERGY`) carries no kilning temperature, so the malting band rests
on `[BOORTMALT_HP]` and `[REF_DESNZ_ELEC]` Table 3 instead.

**`Mineral Production - Gas / power_generation` is not a duty at all** — see Q4.

## Requests to other lanes

- **`carriers` lane / `carrier.csv`.** There is no carrier for a service that is delivered as
  electricity and is neither heat, motive power nor cooling: lighting, office ICT, arc and resistance
  welding, semiconductor process tools, electrolytic surface treatment. I bound those 11 rows to the
  `electricity` primary carrier. If you would rather have an `other_services` intermediate carrier,
  say so and I will repoint them. Note the knock-on for §7 (emissions attribution): a duty bound to a
  `primary` carrier makes the consuming unit look like a fuel burner.
- **`carriers` lane.** Band rank 1 `heat_lt60` is used by none of this lane's 65 heat rows. Worth
  checking whether `duty_a` uses it before the six-band set is treated as settled.
- **Register owner.** `site_services` is the single largest source of forced splits in this lane
  (20 of the 31). Splitting it in `activity_process_register.csv` into an electrical bundle and a
  space-heating bundle, the way most activities already separate `space_heating`, would remove the
  fallback from 20 rows outright.

## Questions for Alexandre

**Q1 — §3.3 is keyed per process, but the food & drink worked example resolves duties per
(process, vector). Which is right?** §3.3's primary key is
`(carb3_activity, process_set_id, process_id, duty_family, grade_rank)` and its sum rule is per
`(activity, set, process)`. But the food & drink worked example's §3.2 lists `site_services` twice,
once at `SPC` 1.00000 and once at `MOT` 1.00000 — which sums to 2.0 under that rule — and its own
prose says it "is only expressible because §3.3.1 is keyed on `(process, vector)` rather than on the
process alone". **If §3.3 gained a `vector` key column, 22 of my 31 splits would become exact and
their fallback tier would disappear**, because each `(process, vector)` pair has exactly one duty.
I built to the brief's rule (sum to 1 per process) because that is what the validator checks, but I
think the worked example is describing the schema the entity actually needs. This is the single
biggest thing I would change.

**Q2 — `evidence_tier` cannot carry two answers, and on 22 rows it needs to.** The grade on
`Paper Mill / paper_machine_drying` is `published_sec` from a 2024 DESNZ report; the share on the
same row is a fallback. I tiered the row by the share (convention 4). Should §3.3 carry separate
tiers for the band and the share, or is one tier per row the intended coarseness?

**Q3 — may `OTH` bind a `primary` carrier?** §3.4 says `OTH` "resolves to whichever of the above the
underlying service is", where "the above" is graded heat, `motive_power` and `cooling`. Lighting is
none of them, and neither is arc welding or an ion implanter. I used `electricity`. Confirm, or tell
me what to use instead — and see the request to the `carriers` lane above.

**Q4 — `Mineral Production - Gas / power_generation` is a conversion unit, not a demand.** The
register lists "On-site power generation" as a process and the energy profile gives it 25 % of the
activity's gas. It consumes gas and produces electricity, which is `unit` / `unit_input_output`
(§3.5–§3.6), not a duty profile. I wrote `OTH` → `electricity` at 1.00 as the least-wrong
placeholder that keeps the process's shares summing to one, flagged `fallback / low`. Should the
register drop this row instead?

**Q5 — SMR feedstock.** Part of the natural gas entering `Oil refinery / hydrogen_production` is
feedstock, not fuel: the hydrogen comes out of the methane. That belongs on a `NEUOTH` row with a
blank carrier, and §7.1 must not charge it combustion emissions. **Neither `[REFBREF2015]` nor
`[oil_roadmap_2015]` gives the feedstock/fuel split**, so I wrote no `NEUOTH` row rather than invent
one. Do you want me to go after a split (IEA or Concawe hydrogen studies would have it), or is this
out of scope until the chemicals sector arrives?

**Q6 — a real source conflict on catalytic reforming.** `[REFBREF2015]` p92 says the reforming
reactors "operate at temperatures in the range of 400 – 560 °C"; `[REF_DESNZ_ELEC]` Table 3 p20 puts
"Catalytic Reforming" in the **100 – 400 °C** band. They straddle a band boundary and disagree. I
took the process-specific BREF figure and put the row at rank 5 `400-1000C`, with the conflict
written into the provenance. If you would rather this table defer to the DESNZ banding wherever it
names a process, the row flips to rank 4 and I will redo it.

**Q7 — confirm the band-boundary convention.** Convention 1 above (band contains the upper bound of
the requirement) is mine, not the spec's. It decides four rows on its own: `Pottery / biscuit_firing`
(the general porcelain figure is 900–1050 °C, so rank 6 rather than rank 5 — though the UK bone-china
figure of 1100–1150 °C puts it in rank 6 regardless) and the three refinery units whose fired-heater
range is 250–500 °C. §3.3 should probably say this out loud, since C10 (the heat cascade) is what it
feeds.

**Q8 — `references.csv` has nine duplicated sources under two `ref_id`s each.** Same URL, two keys:
`DECC_CERAMIC_2015`/`R_BEIS_CER2015`, `UKPP2015`/`paper_roadmap_2015`,
`MDPITAN2023`/`tannery_energy_2023`, `MAGB_ENERGY`/`UKMALT_ENERGY`, `UNIDO2019`/`unido_framework_2019`,
`ANNEX58_2023`/`annex58_t1_2023`, `UKCHEM2015`/`chem_roadmap_2015`, `REF_MPA2020`/`R_MPA_ROADMAP`,
`HEIDELBERG2025`/`R_PADESWOOD`. I picked one of each pair and stayed consistent, but the merge should
probably collapse them. Nothing currently checks for it.

**Q9 — `Mill` cannot be crosswalked and probably cannot be modelled.** `carb3_comit_crosswalk.csv`
records it `ambiguous` — "could be flour, paper, textile or metal". I wrote its eight duty rows
against a flour-mill reading (`[WORLDGRAIN2010]`, `[ALIU2018]`) because that is what
`activity_process_energy_profile.csv` already assumes, and left all eight crosswalk rows `none`.
If the stock model can tell flour mills from paper mills, the duty rows should be redone per type.

**Q10 — Laboratory, Post Office Sorting Centre and Vehicle repair are `absent` from COMIT and their
duties are entirely building-like** (ventilation, lighting, space heat, hot water, small power).
17 register rows. They are legitimate CaRB3 activities but they will never have a COMIT-parity
comparison, which is what V1b (the COMIT-parity validation test) needs. Worth confirming they stay
in scope for the site energy system at all.
