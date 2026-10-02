# Creamery: how the plant operates

*Last updated: 2026-10-02.* Activity key: `Creamery`. Related worked example: [food and drink worked example](../../specs/2026-08-28-carb3-site-energy-system-worked-example-food-drink.md) (a milk-powder dairy, modelled under `Food Processing Centre`, not `Creamery`).

## 1. What the activity is

A creamery or dairy processing site takes in chilled raw milk and turns it into some mix of liquid milk, cream, butter, cheese (with whey as a by-product) and concentrated or dried products such as milk powder [BREF_FDM2019] Section 5.2 (5.2.1 milk and cream, 5.2.2 condensed and powdered milk, 5.2.3 butter, 5.2.4 cheese). The activity's register row describes it as a "liquid milk/cheese/powder mix" site [CARB3_REGISTER]. Sites differ a great deal by product: the European reference document finds that more energy is used where butter is made as well as drinking milk, and where powder production is larger [BREF_FDM2019] Section 5.3.1, p. 350. Dry whey powder is the most energy-intensive dairy product, mainly because of evaporation and spray drying [LBNL_DAIRY] Section 4, Figure 4.5 text, pp. 26-27.

Energy split. About 80 % of a European dairy's energy is thermal, from fossil fuel burnt to make steam and hot water, used for heating and cleaning; about 20 % is electricity for machinery, refrigeration, ventilation and lighting [BREF_FDM2019] Section 5.3.1, p. 349. A US source gives the same 80/20 for fuel use, almost all natural gas [LBNL_DAIRY] Section 4, p. 22. In the UK, refrigeration is about 25 % of liquid-milk-processing electricity [DECC2015FD] Section 3.2.7, p. 35.

UK intake is highly seasonal (section 4). The dairy sector as a whole is described as one of the "non-stop" manufacturing sectors [DECC2015FD] Section 3, p. 55.

Typical UK site size and the number of UK sites: no source found. See section 9.

Variation with product, in short: a liquid-milk site is dominated by pasteurisation, cooling and packing (heat at 70 to 140 C, plenty of refrigeration); a cheese site by vat heating and whey handling; a powder site by the evaporator and spray dryer, which together take 96 % of a milk powder's process energy [FOCUS_DAIRY] Table 1, p. 12 (as recorded in the register, [CARB3_REGISTER]).

## 2. Processes and their duties

One row per `process_id` in `activity_process_duty_profile.csv` for `Creamery` [CARB3_DUTY_PROFILE]. Provenance and band choices are in that file.

| `process_id` | What it is physically | Temperature it needs | Duty family, carrier, grade, share in the data | Does the band match practice? |
|---|---|---|---|---|
| `heat_treatment_pasteurisation` | Plate heat exchangers. HTST pasteurisation at 72 C for 15 s, with hot milk regenerating heat to incoming cold milk, then cooling to below 7 C [BREF_FDM2019] 5.2.1, p. 335. UHT at a minimum of 135 C for 1 s, either indirect, or in two stages with the second by direct steam injection at about 1 kg steam to 10 kg milk [BREF_FDM2019] 5.2.1, p. 337. | 72 to 85 C (HTST); 135 C and above (UHT) | `LTH`, `heat_60_100`, grade 2, share 1.0 | Matches HTST. UHT (band 3) is not split out because no source splits HTST from UHT; the data says so (stated gap). A UHT-heavy site is under-graded. |
| `evaporation_drying` | Multi-effect falling-film evaporator, concentrating milk from about 9-11 % to 50-60 % solids, then a spray dryer, usually with a fluidised bed after it [BREF_FDM2019] 5.2.2 p. 339 and 5.4.2.8; [ATKINS_ATE2011] Section 2. Spray dryer inlet air up to about 250 C, outlet about 95 C [BREF_FDM2019] 5.2.2, p. 340; 180 to 220 C is typical for milk [WATSON_SD]; 200 C in the plant modelled by [ATKINS_ATE2011]. | 180 to 200 C inlet air; evaporator steam at lower grade | `DRY`, `heat_150_400`, grade 4, share 1.0 | Matches the dryer's top temperature. The evaporator's own steam duty (band 3) is not separated. See section 8. |
| `cip_hot_water` | Clean-in-place sets and hot water. Alkali 0.5 to 2 % at 75 C for about 30 min, acid 0.5 to 1.5 % at 70 C for about 20 min, hot-water disinfection at 90 to 95 C [TETRAPAK_DPH] "Cleaning of dairy equipment", programme tables. | 70 to 95 C | `LTH`, `heat_60_100`, grade 2, share 1.0 | Matches, except the 90 to 95 C disinfection rinse, which is a short, small-volume step. |
| `refrigeration` | Chillers and cold stores. Raw milk is "quickly cooled to not more than 6 C" and held there until processed [REG853_2004] Annex III Section IX Ch. II I.1. | 0 to 6 C | `REF`, `cooling_0_15`, grade 2, share 1.0 | Matches. Dairy cold stores are chill stores, not freezers. |
| `processing_machinery_pumping` | Separators, homogenisers, pumps, filling lines. | n/a | `MOT`, `motive_power`, share 1.0 | Matches in kind. |
| `compressed_air` | Compressor shaft work. Its waste heat is a recovery opportunity, not a duty [CTV059]. | n/a | `MOT`, `motive_power`, share 1.0 (engineering tier) | Matches in kind. |
| `site_services` | Site overhead bundle: space heat, lighting, ICT, fans, building cooling. | Space heat below 60 C | Four rows (fallback tier): `SPC` `heat_lt60` 0.595762; `OTH` `electric_service` 0.347596; `MOT` 0.031785; `REF` `cooling_0_15` 0.024857. Shares are the industrial heat-to-electricity ratio and electricity end-use split of [BEES2016] Table B.3, p. 122, not dairy data. | Low confidence. A dairy's space heating is small beside process heat; the split is generic. |

## 3. Energy plant layout

**Steam header with hot water derived from it.** The heat is made as steam in boilers and distributed to the processes; hot water for CIP and pasteurisation is typically raised from that steam or from direct-contact heaters [BREF_FDM2019] 5.3.1 p. 349 ("steam and hot water"); [LBNL_DAIRY] Section 7.1, which also notes steam is sometimes used where hot water would do. A real UK example: Davidstow creamery (cheddar and demineralised whey powder) raises its heat "as steam in five boilers": three kerosene boilers of 11.5, 10.5 and 10.5 MW thermal input and two biomass wood-pellet boilers of 6.2 MW each (44.9 MW in total), the biomass boilers supplying "around 70%" of the creamery's heating [DAVIDSTOW_EA2024] Sections 1 and 2.5, Table 2. That document lists no CHP at the site.

**Spray dryer air heating is a choice, not a given.** The drying air can be heated "by steam or by direct gas-fired air heaters or by indirect heaters fired by gas, liquid or solid fuels" [BREF_FDM2019] 5.2.2, p. 340. In the milk powder plant studied by [ATKINS_ATE2011] Section 2, the air is heated from 25 C to 200 C and the plant's hot utility is steam. So the dryer may sit on the steam header (as at Davidstow, where a planned project would cut "heat demand from the steam raising boilers by circa 2 MWth" through dryer waste-heat recovery and part-electrification [DAVIDSTOW_EA2024] Section 2.6), or have its own burner. The data gives the dryer one gas-or-electric-or-steam-served duty and no sourced split between these routes. See section 9.

**Evaporator.** Evaporation is "normally combined with vapour recompression" [BREF_FDM2019] 5.3.1, p. 349. A mechanical vapour recompression (MVR) evaporator uses about 10 kWh of electricity per tonne of water evaporated with negligible steam [BREF_FDM2019] 2.3.2.2.4.1. One whey plant concentrated from 6 % to 35 % solids by MVR and then to 60 % by thermal vapour recompression (TVR) [BREF_FDM2019] 5.3 installation #406; the plant of [ATKINS_ATE2011] uses both. So the evaporator draws steam (TVR, and first effects) and electricity (MVR) in proportions that depend on the site.

**CHP.** Gas turbines, gas engines and steam turbines with heat recovery are used across the sector; overall fuel utilisation exceeds 70 % and is typically about 85 %, and CHP suits sites where heat and power loads are balanced [BREF_FDM2019] Chapter 2, p. 14. The roadmap credits the UK food and drink sector with installing over 400 MWe of CHP [DECC2015FD] Section 3.3.2, p. 39. Examples: Arla's Aylesbury dairy runs two 2 MWe gas engines (1.9 MW heat each, natural gas plus on-site biogas) whose heat serves "pasteurisation, homogenisation and cleaning circuits" [EDINA_ARLA]. A 1983 feasibility study for a milk powder factory recommended a gas turbine whose hot exhaust directly heats the spray dryer air, with supplementary gas firing to control air temperature [LOVELL1983]. The BREF gives up to 90 to 95 % energy efficiency when waste-heat-recovery exhaust is used for drying [BREF_FDM2019] Chapter 2, p. 14.

**Who serves which duty together (inference from the above, not a sourced statement).** On a plant with CHP, the CHP heat and the boilers feed one steam or hot-water system, so CHP and boilers are not alternatives for a process but shares of one load. The dryer's burner, where it exists, is a third source for the 150 to 200 C part of the dryer duty only.

**Cooling.** The duty profile treats ammonia and glycol chillers and cold stores as one cooling service [CARB3_DUTY_PROFILE]; a vendor describes secondary glycol loops as common in dairies [GD_CHILLERS_DAIRY]. Compressor heat can be recovered at 50 to 90 % of the available heat [LBNL_DAIRY] Section 10.1, p. 72.

## 4. Operating pattern

**Continuous or near-continuous.** The dairy subsector operates "on a non-stop basis", and downtime on a line is "carefully planned and reduced to an absolute minimum" [DECC2015FD] Section 3, p. 55. Specific hours per year, days per week and shifts for UK creameries: no published source found. The worked example's dairy is illustrative only: three-shift, 7,200 operating hours a year, 6 days a week, 2 shutdown weeks, a within-shift electricity peak factor of 1.47 and a gas peak factor of 1.25 [CARB3_WE_FOOD] Section 1.8. Those figures are the example's own assumptions, not evidence.

**Seasonal milk flush.** GB milk delivery peaks in spring. In 2026 the highest single day was 38.90 million litres on 25 April, a record, against a 2025 peak of 38.88 million litres; the plateau began in late April, earlier than the usual first two weeks of May; the report says processor capacity measures and pricing helped slow the surge [AHDB_SPRING2026]. Processors balance a flush by shifting milk to storable products (powders, butter); see section 9 for the one figure could not confirm. A site that makes powder or butter from surplus milk therefore runs its evaporator and dryer hardest in spring, while a liquid-milk line is steady all year.

**Peak-to-mean.** No UK creamery peak-to-mean ratio for electricity, gas or steam was found (λ, the peak factor of spec §5.6, remains unsourced for this activity). Seasonal intake range: see section 9.

**Batch within continuous: CIP.** Plant is cleaned in place on a cycle. For pasteurisers the programme is a warm rinse, alkali (75 C, 30 min), rinse, acid (70 C, 20 min), cold rinse; the handbook gives 20 to 60 minutes for a protein-fouled heat exchanger and says cleaning should follow production runs because deposits change from whitish to brownish after eight or more hours [TETRAPAK_DPH] "Cleaning of dairy equipment". CIP is a large energy item: in Dutch dairies it takes 9.5 % of energy in fluid milk processing, 26 % in butter and 19 % in cheese [LBNL_DAIRY] Section 4, p. 25 (after Ramirez et al. 2006). CIP therefore adds a regular hot-water and steam peak on top of the process load, and an evaporator is taken off line for it [BREF_FDM2019] 5.2 whey recovery example, p. 385.

**Start-ups.** A spray dryer prefers continuous running; stop and start is complex and wasteful (patent literature; not verified, section 9).

## 5. Backup and redundancy

No UK source found states how many boilers a creamery keeps beyond duty or whether boilers are sized to carry the full steam load with the CHP out. The honest summary is below, with what each source does and does not say.

| Process or plant | What happens when the main unit is down | Backup normally kept | Source status |
|---|---|---|---|
| Steam boilers (all steam duties) | Pasteurisation, CIP and evaporation draw on steam or hot water, so a long outage would stop those lines (inference). | Not settled. Davidstow has five boilers (three oil at 10.5 to 11.5 MW, two biomass at 6.2 MW) and when the biomass boilers are derated the "three kerosene boilers" take up the load, so some boiler redundancy exists in practice; the document does not say whether any boiler is idle standby [DAVIDSTOW_EA2024] Table 2, Section 2.6. | Gap, see section 9 |
| CHP | CHP is typically not the only source; its heat is one part of the steam or hot water system. Whether the boilers alone can carry the whole load: no source. | Not stated: [EDINA_ARLA] does not mention boilers and [DAVIDSTOW_EA2024] has no CHP. | Gap |
| Spray dryer | A powder plant cannot store concentrate for long without it thickening hot or crystallising lactose cold, so the evaporator and dryer may have to stop together (no verified source; see section 9). A dryer with its own burner is outside the steam header, so a boiler outage does not affect it, but a burner trip stops drying. | None found. | Gap |
| Evaporator | Taken off line for CIP and, for whey, product in the line is flushed out first and recovered [BREF_FDM2019] 5.2 whey recovery example, p. 385. | No source found for buffering or how long the line can stay down. | Partial |
| Pasteuriser | A single line stops (inference; no source). | Not settled. | Gap |
| Refrigeration | Milk must be held at or below 6 C [REG853_2004] Annex III Section IX Ch. II I.1, so a chiller loss risks the product and the cold chain. Vendors recommend staged compressors, multiple chillers and standby pumps, with the redundancy level set by product value and acceptable downtime [GD_CHILLERS_DAIRY]. | Multiple compressors or chillers (vendor view only). | Vendor source only |
| Compressed air | A running compressor can be replaced from spares; controls sometimes free a compressor "to be sold or kept for backup" [LBNL_DAIRY] Section 10.1, p. 72. | Spare compressor. | Partial |

What is firm: production loss is feared. The UK roadmap work lists "risk of production disruption" as a medium-to-high barrier to decarbonising options and identifies dairy as non-stop [DECC2015FD] Section 3, p. 55. That is why any retrofit needs to preserve whatever backup exists, but the size of that backup is not documented.

## 6. Heat recovery and integration

- **Pasteuriser regeneration.** Hot milk heats incoming cold milk [BREF_FDM2019] 5.2.1, p. 335. Pasteurisation is one of the largest emission sources in dairy, although much of its heat is regenerated and reused [DECC2015FD] Section 3.3.3, p. 40.
- **Evaporator vapour recompression.** MVR at about 10 kWh/t of water evaporated [BREF_FDM2019] 2.3.2.2.4.1; TVR is less efficient than MVR [BREF_FDM2019] 2.3.2.2.4.1.
- **Spray dryer exhaust.** Recovery has had "limited success" because of economics, particle fouling and the low exhaust temperature (about 75 C leaving the baghouse in the studied plant), and the inlet air can be as warm as 40 C before its heater, which limits the recoverable heat [ATKINS_ATE2011] Section 1 and 2. Heating the inlet air from the exhaust gave a 12.8 % cut in hot utility at a 35 C inlet-air rise; the best integrated scheme cut hot utility by up to 21 % [ATKINS_ATE2011] Abstract and Section 4. A Davidstow project aims at waste-heat recovery from powder drying [DAVIDSTOW_EA2024] Section 1.3.
- **Dryer inlet temperature.** Raising the inlet from 160 C to 240 C can cut steam use 29 % and overall energy 50 % [LBNL_DAIRY] Section 13.3, p. 89 (after Carić 1994).
- **Condensate and flue gas.** Condensate return and economisers are standard steam-system measures [LBNL_DAIRY] Sections 7.1 and 7.2.
- **Compressed-air and refrigeration heat.** Compressor heat can be reclaimed for process water heating [LBNL_DAIRY] Section 10.1, p. 72. Refrigeration heat is an option for hot water; no source quantified it for UK dairies.
- **CHP exhaust to dryer.** See section 3 [LOVELL1983].

## 7. Decarbonisation in practice

- **Fuel switch to biomass.** Davidstow's wood-pellet boilers supply about 70 % of heating; limits are emission limits for medium combustion plant, which is why the boilers are being derated below 5 MW thermal input [DAVIDSTOW_EA2024] Sections 1.3 and 2.
- **Dryer electrification and waste heat recovery.** Davidstow submitted both to the Industrial Energy Transformation Fund in early 2024 (outcome not in the document) [DAVIDSTOW_EA2024] Section 1.3. Heat pumps are the natural fit for the 60 to 100 C pasteurisation and CIP duties [STAR_HP] (via `process_decarbonisation_options.csv`, as cited in the duty profile); the dryer's air above about 80 C is the barrier [LIANG_ECOS2022] (as quoted in note 20 item 71).
- **MVR in place of TVR.** An established route that cuts steam use [BREF_FDM2019] 2.3.2.2.4.1; [TNO_MVR2018] gives the technology readiness.
- **RO pre-concentration.** Reverse osmosis can double the solids content of milk and whey before evaporation, saving evaporator steam [BREF_FDM2019] 5.2.2, p. 339; installation #005 saved 22,000 kWh of electricity a month and 500 t of steam a year [BREF_FDM2019] Chapter 5, installation #005 example.
- **CHP.** Already present at some sites [EDINA_ARLA]; its future depends on the grid carbon factor.

Limits: the 180 to 220 C dryer air, the continuous operation that leaves no downtime for retrofit, the unsourced backup requirement, and for electrification the grid connection capacity.

## 8. Reading the model's results

- **Single band for the dryer.** `Creamery` gives `evaporation_drying` one row: `heat_150_400`, grade 4, `duty_share` 1. `Food Processing Centre`'s `direct_heating` dryer duty was split into four band segments (10.3 to 60 C, 60 to 100 C, 100 to 150 C, 150 to 200 C) under note 20 item 71, because a spray dryer's air is heated once through from ambient to about 200 C and the lower part of that rise can be served by a heat pump recovering exhaust heat. The two activities therefore treat the same spray-dryer physics differently. Read a `Creamery` run as one where a dryer heat pump (a `grade_rank` 2 unit) cannot be chosen for any of the dryer's duty, and where the evaporator's steam is graded with the dryer's hot air. Whether item 71's rule should also be applied to the creamery's dryer is a decision for the data owner, not a finding of this note.
- **The `Creamery` data omits UHT as a separate duty.** A UHT-heavy site will have part of its heat at 135 C, above the band the data gives.
- **No backup constraint.** The model bounds on-site plant only by annual energy against capacity times availability (C2, the capacity constraint). It has no rule that boilers must carry the steam load with the CHP out, no standby boiler, and no redundancy for a chiller. A least-cost run can therefore retire a boiler or size a heat pump to the whole 60 to 100 C duty, with no spare, that a real creamery would not accept. Treat unit counts from a run as a lower bound on the plant a site would keep, and add backup by hand.
- **λ and C11 are about the grid only.** λ (the peak factor of spec §5.6) and C11 (the connection capacity constraint) concern the grid connection. They do not size on-site boilers, chillers or standby plant. A heat pump or electric boiler that fits within a connection at annual-mean load may still fail in the spring-flush peak, and the model does not see that.
- **Seasonality.** The run uses annual and period totals, so the spring flush (section 4) is not modelled; peak steam load in April and May is hidden by the annual mean.
- **Site services.** Four fallback-tier rows with generic building shares; do not read the space-heat or lighting result as dairy-specific.
- **Worked example.** The food-and-drink example is a milk-powder dairy but is built under `Food Processing Centre` with a gas boiler, a gas turbine CHP, a direct-gas dryer and an electric chiller [CARB3_WE_FOOD] Section 5.1. Do not expect a `Creamery` run to look the same.

## 9. Gaps and open questions

1. **Number of UK creameries, and typical site output and energy use.** No source found. Dairy UK and AHDB give sector milk totals but no site count.
2. **Boiler sizing and N-1.** No source says whether UK dairy boilers are sized to carry the steam load with the CHP out, or how many standby boilers are kept. The "N+1" statement came from a vendor web page could not be opened (dairyprocessing.com, an article on dairy boilers, HTTP 403).
3. **Refrigeration redundancy.** Only vendor guidance [GD_CHILLERS_DAIRY]; no UK dairy standard or case study.
4. **Spray dryer or evaporator down.** The "4 to 5 hour dryer shutdown during evaporator cleaning, with limited ability to buffer concentrate" came from a US patent text surfaced by search (US 10,182,580 or 10,687,540, "System and method for production of low thermophile and low spore milk powder"); the PDF was image-only and could not verify the passage. What a UK site does with milk (diverts to cheese or butter, sells on) is not sourced.
5. **Operating hours, days per week, shifts and a peak-to-mean ratio** for a UK creamery. Only the example premise's assumptions exist.
6. **Seasonal range.** A search result attributed to AHDB gave May 2025/26 milk production of 1,182 million litres against 1,071 million litres in November (about 10 %), with the trough having moved from October/November to August/September as calving patterns shifted, and powders up 18 % and butter up 6 % in 2025; could not be opened those pages (HTTP 404), so they are leads only.
7. **Which route heats the dryer air** (steam, direct gas, CHP exhaust) in UK plants, and the split of steam between evaporator and dryer.
8. **Direct-fired share of food and drink heat.** [DECC2015FD] Section 3.3.3, p. 40 gives boilers 54 % and direct-fired 21 %; the register data cites 27 % for direct heating at Section 1.3, p. 11. Not reconciled here.
9. **UHT share of UK liquid milk** and a sourced HTST/UHT split (acknowledged in the duty profile).
10. **Refrigeration heat reclaim in dairies** and any UK industrial heat pump case study in a dairy; the Annex 58 reports [ANNEX58_2023] were not searched for a dairy case.

## Sources

- `[AHDB_SPRING2026]` AHDB, *GB milk production: 2026 spring peak*, 21 May 2026, https://ahdb.org.uk/news/gb-milk-production-2026-spring-peak. Peak daily volume, plateau timing.
- `[ANNEX58_2023]` IEA HPT Annex 58, Task 1 Technologies report, 2023 (listed in `references.csv`; cited for context only, not read for this note).
- `[ATKINS_ATE2011]` Atkins, Walmsley and Neale, *Integrating heat recovery from milk powder spray dryer exhausts in the dairy industry*, Applied Thermal Engineering, 2011, doi 10.1016/j.applthermaleng.2011.03.006, https://researchcommons.waikato.ac.nz/server/api/core/bitstreams/f6f0da01-39ad-4f49-a3c0-de201b80a73c/content. Abstract; Sections 1, 2 and 4 (plant description, utilities, recovery schemes).
- `[BEES2016]` BEIS, *Building Energy Efficiency Survey 2014-15: Overarching Report*, 2016, Appendix B Table B.3, p. 122 (as used in the duty profile).
- `[BREF_FDM2019]` European Commission JRC, *Best Available Techniques (BAT) Reference Document for the Food, Drink and Milk Industries*, 2019, https://bureau-industrial-transformation.jrc.ec.europa.eu/sites/default/files/2020-01/JRC118627_FDM_Bref_2019_published.pdf. Chapter 2 p. 14 (CHP); 2.3.2.2.4.1 (MVR); 5.2.1 to 5.2.4, pp. 335-343 (processes); 5.3.1, pp. 349-350 (energy); 5.4.2.8 (multistage drying); 5.3 whey recovery and installations #005 and #406, pp. 385-386.
- `[CARB3_DUTY_PROFILE]` This repository, `docs/notes/data/activity_process_duty_profile.csv`, `Creamery` rows.
- `[CARB3_REGISTER]` This repository, `docs/notes/data/activity_process_register.csv`, rows 111-113 (and the rest of the `Creamery` rows).
- `[CARB3_WE_FOOD]` This repository, worked example food and drink, Sections 1.8 and 5.1.
- `[CTV059]` Carbon Trust, *Manufacturing: introducing energy saving opportunities for business*, 2018 (as used in the duty profile for compressed air).
- `[DAVIDSTOW_EA2024]` Dairy Crest Ltd t/a Saputo Dairy UK, *Application for Variation of Permit BN6137IK, Davidstow Creamery: Supporting Information, MCPD derating of existing biomass boilers*, 2024, Environment Agency consultation, https://consult.environment-agency.gov.uk/psc/pl32-9xw-dairy-crest-limited-epr-bn6137ik-v013/supporting_documents/application-variation-v013-bn6137ik-variation-application-supporting-information-mcpd-03102024pdf. Sections 1.3, 2.5, 2.6, Table 2.
- `[DECC2015FD]` DECC/BIS, *Industrial Decarbonisation and Energy Efficiency Roadmaps to 2050: Food and Drink*, 2015, https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/416672/Food_and_Drink_Report.pdf. Section 3.2.7 p. 35; 3.3.2 p. 39; 3.3.3 p. 40; Section 3 barriers p. 55.
- `[EDINA_ARLA]` Edina, *Arla Foods CHP plant* case study, https://www.edina.eu/case-studies/arla-foods. Aylesbury, two gas engines, heat uses.
- `[FOCUS_DAIRY]` Wisconsin Focus on Energy, *Dairy Processing Industry Energy Best Practice Guidebook*, Table 1, p. 12 (as recorded in `references.csv` and the register; the PDF returned HTTP 403 and was not re-read).
- `[GD_CHILLERS_DAIRY]` GD Chillers, *Dairy Processing Cooling Requirements: From Pasteurization to Cold Storage*, https://gdchillers.com/resources/food-processing/dairy-processing-cooling-requirements-from-pasteurization-to-cold-storage. Vendor guidance, read via search summary only.
- `[LBNL_DAIRY]` LBNL, *Energy Efficiency Improvement and Cost Saving Opportunities for the Dairy Processing Industry*, https://www.osti.gov/servlets/purl/1171534. Section 4 pp. 22-27; Section 7.1-7.2 pp. 40-45; Section 10.1 p. 72; Section 13.3 p. 89.
- `[LIANG_ECOS2022]` as in `references.csv`, quoted in note 20 item 71.
- `[LOVELL1983]` Lovell-Smith and Vickers, *Cogeneration of heat and electricity in a spray drying plant*, 1983, https://www.osti.gov/etdeweb/biblio/8134531. Record abstract only.
- `[REG853_2004]` Regulation (EC) No 853/2004 as retained in UK law, Annex III Section IX Chapter II point I.1.
- `[STAR_HP]` Star Refrigeration, heat pump and heat recovery systems (as cited in the duty profile via `process_decarbonisation_options.csv`).
- `[TETRAPAK_DPH]` Tetra Pak, *Dairy Processing Handbook*, chapter "Cleaning of dairy equipment", https://dairyprocessinghandbook.tetrapak.com/chapter/cleaning-dairy-equipment. CIP programme tables.
- `[TNO_MVR2018]` TNO, *Technology factsheet: industrial mechanical vapour recompression*, 2018 (as in `references.csv`).
- `[WATSON_SD]` Watson Dairy Consulting, *Spray dryer technical information*, https://dairyconsultant.co.uk/milk_spray_dryers_drying.php. Inlet air 180 to 220 C.

Keys not yet in `docs/notes/data/references.csv`: `AHDB_SPRING2026`, `ATKINS_ATE2011`, `BREF_FDM2019`, `CARB3_DUTY_PROFILE`, `DAVIDSTOW_EA2024`, `EDINA_ARLA`, `GD_CHILLERS_DAIRY`, `LOVELL1983`, `TETRAPAK_DPH`, `WATSON_SD`.
