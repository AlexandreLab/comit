# Food Processing Centre: how the plant operates

*Last updated: 2026-10-02.* Activity key: `Food Processing Centre`. Related worked example: [food and drink worked example](../../specs/2026-08-28-carb3-site-energy-system-worked-example-food-drink.md) (a milk-powder dairy, premise P-004417). General food processing is described first and the dairy is the worked case. Page numbers below are PDF page numbers unless a section number is given.

## 1. What the activity is

Food and drink manufacturing is the sector the activity stands for. It is very diverse: dairy, bakery, meat, brewing, sugar, confectionery, canning and others [DECC2015FD] p12–13. The UK sector had over 7,800 companies, 86 percent of them with fewer than ten employees [DECC2015FD] p13, and used 33.97 TWh of final energy in 2012 [DECC2015FD] p30. Natural gas is about two thirds of fuel use [DECC2015FD] p12. The sector's energy splits roughly as boilers 54 percent, direct heating 27 percent, motors 12 percent, refrigeration 5 percent and compressed air 2 percent [DECC2015FD] p12, which is the origin of the six processes in the duty profile.

The worked case is a dairy making milk powder: liquid intake, pasteurising and clean-in-place, evaporation, spray drying and cold storage, on an 18,400 m² site using 0.30 PJ/yr of gas and 0.06 PJ/yr of net electricity import [CARB3_WE_FOOD] sections 1.1 and 1.2. A published European example of a large two-stage powder dairy is far bigger: 240,000 t of raw milk a year, 19,000 t of powder, 67.5 GWh/yr of thermal energy, of which drying took 58 percent [BREF_FDM2019] section 5.4.2.8. Sites of the worked case's size and larger both exist; practice below varies with that size.

The number of UK sites is not given by any source read for this note (section 9).

## 2. Processes and their duties

The duty profile has six processes for this activity [CARB3_WE_FOOD] section 3.2, with the band decisions recorded in the profile's provenance column.

| `process_id` | What it is physically | Temperature and band in the data | Duty family and carrier | Matches practice? |
|---|---|---|---|---|
| `boiler_steam_hot_water` | Steam and hot water for pasteurising, evaporators, spray dryers and CIP [DECC2015FD] p41; [ETSU_GPG209] section 2.1 | Two duties: LTH hot water and CIP at 80 °C, 46.2 percent, `heat_60_100`; STM evaporator steam at 120 °C, 53.8 percent, `heat_100_150` | LTH and STM, heat | Yes. Evaporator steam is the classic use [BREF_FDM2019] section 2.3.2.2.4 |
| `direct_heating` | The spray dryer's hot air. Air heating is by steam, direct gas-fired heaters, or indirect fired heaters [BREF_FDM2019] section 5.2 | One once-through air heating from 10.3 °C intake to 200 °C, stored as four band segments (shares 0.262, 0.211, 0.264, 0.264) | DRY, heat | Delivery temperature is within the published range (section 3). The split is bookkeeping, see section 8 |
| `refrigeration` | Chilled water and cold stores, running all year | `cooling_0_15` | REF, cooling | Yes. Milk is chilled, not frozen |
| `machinery_motors` | Pumps, separators, homogenisers, conveyors | none | MOT, motive power | Yes [DECC2015FD] p41 |
| `compressed_air` | Pneumatics, packing lines [DECC2015FD] p37 | none | MOT, motive power | Yes |
| `site_services` | Space heating, lighting, ICT, small power, fans, some cooling | Space heat on `heat_lt60`, 54.9 percent; electricity 45.1 percent split by [BEES2016] Table B.3 | SPC, OTH, MOT, REF | Space heat is mostly direct gas warm-air or radiant [DESNZ_LCHC_NONDOM2022] Table 1 |

The 10.3 °C intake is the 1991–2020 UK annual mean temperature [BEIS_LTM_2022] Table 1. The dryer's real inlet air varies: a New Zealand plant study takes 25 °C building air [ATKINS_ATE2011] section 2, and a UK case study preheats air to 55 °C before the final heater [ETSU_GPG209] section 8.3.

## 3. Energy plant layout

**Steam and hot water.** Gas-turbine or gas-engine CHP with waste heat recovery making steam or hot water is a standard concept in food and drink [BREF_FDM2019] section 2.1.2. BREF says CHP suits sites where heat and power loads are balanced, and that larger dairies, with growing evaporation and drying loads, make CHP feasible [BREF_FDM2019] section 2.1.2.1.1. The sector's improvement since 1990 includes over 400 MWe of installed CHP capacity [DECC2015FD] p40.

The usual connection is that the CHP adds its heat upstream of the existing boilers, which then run as top-up or stand-by [BEIS_CHP2021] section 2.6 (p22). Heat is connected in series in existing sites and in parallel for new builds [BEIS_CHP2021] section 2.6. This is the arrangement the owner describes: CHP on base load, boilers topping up and standing by, sharing one header. No source read states the header pressure or that a heat recovery steam generator (HRSG) is the unit used at a dairy of this size; a heat recovery boiler is only named generically [BREF_FDM2019] section 2.1.2 (section 9).

When CHP heat cannot be used but power must be kept, packaged CHP carries a dump radiator [BEIS_CHP2021] section 2.6. In summer, when heat demand is low, this matters most [BEIS_CHP2021] section 2.6.

**Hot water.** Hot water at 80 °C for CIP and cleaning is made at the boiler house [ETSU_GPG209] section 2.1. That it is raised from the steam header through heat exchangers is plausible and matches the data (one process, two duties, one carrier chain) but no source read states it (section 9). Pasteurisers regenerate much of their own heat [DECC2015FD] p41.

**Direct-fired dryer.** Spray dryer air is heated by steam, direct gas-fired heaters or indirect fired heaters [BREF_FDM2019] section 5.2. A UK powder dairy case study used steam-heated air at 90 °C for the static fluid bed and a gas-fired thermal fluid heater for the main air, after preheating the air to 55 °C from evaporator condensate and dryer outlet air [ETSU_GPG209] section 8.3. Published inlet temperatures: up to about 250 °C [BREF_FDM2019] section 5.2; 180 to 220 °C [MOEJES_IDS2016] Table A1; 200 °C at a modelled 23 t/h plant [ATKINS_ATE2011] section 2; up to 270 °C in the UK case [ETSU_GPG209] section 8.3. Outlet air is about 95 °C [BREF_FDM2019] section 5.2, 60 to 90 °C [MOEJES_IDS2016] introduction, or 75 °C [ATKINS_ATE2011] section 2.

The data's plant for the worked dairy is: CHP and a gas boiler on `boiler_steam_hot_water`, a direct gas dryer on `direct_heating`, all on the gas connection G-01, with the electric chiller and motors on E-01 [CARB3_WE_FOOD] sections 1.5 and 1.5.1.

| Unit | Serves | Carrier in | Commissioned | Note |
|---|---|---|---|---|
| `chp_gas_turbine` | `boiler_steam_hot_water` | gas | 2011 | Base load, shares the header |
| `boiler_lt_gas` | `boiler_steam_hot_water` | gas | 2016 | Top-up and stand-by |
| `dryer_direct_gas` | `direct_heating` | gas | 2019 | Own air heater, own burner |
| `boiler_spc_gas` | `site_services` (space heat) | gas | 2011 | Separate from the steam header |

## 4. Operating pattern

**Continuous or near so.** Some food manufacturing is non-stop, in particular soft drinks and dairy, while bakery, frozen food and meat run in a limited daily window [DECC2015FD] p56. The worked dairy is three shifts, 7,200 h/yr, six days a week, two shutdown weeks [CARB3_WE_FOOD] section 1.8. The cold store runs through the shutdown weeks and the evaporator does not [CARB3_WE_FOOD] section 1.10.

**Seasonality.** Milk supply peaks in spring: GB daily deliveries reached a record 38.90 million litres on 25 April 2026 [AHDB_SPRING2026]. A powder dairy is the plant that absorbs that flush, so its summer intake is its heaviest week. The worked example records exactly this: the representative week's electrical peak is 3.1 MW against an annual peak of 3.4 MW [CARB3_WE_FOOD] section 1.9. The size of the trough is not in any source read (section 9).

**Cleaning cycles.** CIP is a pre-rinse, alkaline and acid rinses. Tanks take about 30 minutes and evaporators up to five hours [ETSU_GPG209] section 9.1. Hot water at 80 °C is drawn for it, so CIP is a recurring hot water load on the boiler house.

**Peak to mean.** No published source read gives a figure. The worked example's values are for one illustrative premise, not a survey:

| Quantity | Value | Source |
|---|---|---|
| Within-shift peak factor, electricity | 1.47 | [CARB3_WE_FOOD] section 1.8 |
| Within-shift peak factor, gas | 1.25 | [CARB3_WE_FOOD] section 1.8 |
| Load factor, electricity | 0.56 | [CARB3_WE_FOOD] section 1.8 |
| Load factor, gas | 0.66 | [CARB3_WE_FOOD] section 1.8 |
| `boiler_steam_hot_water` peak to mean | 2.40, batch cyclic | [CARB3_WE_FOOD] section 1.10 |
| `direct_heating` peak to mean | 1.10, flat | [CARB3_WE_FOOD] section 1.10 |
| `refrigeration`, `site_services` | 1.00, standing | [CARB3_WE_FOOD] section 1.10 |

The pattern is physically sensible: the dryer runs flat while the steam header, fed by batch pasteurising and CIP, is the peaky load. The 1.47 feeds λ (the §5.6 peak factor), which concerns the grid connection only.

## 5. Backup and redundancy

| Process | Main unit | What happens when it is down | Backup normally kept |
|---|---|---|---|
| `boiler_steam_hot_water` | CHP | Boilers carry the heat. The CHP's electricity comes from the grid | The existing boilers stay as top-up and stand-by [BEIS_CHP2021] section 2.6. Whether they can carry the full steam load (N-1) is not sourced (section 9) |
| `boiler_steam_hot_water` | Boiler | CHP heat plus any remaining boiler | Not sourced |
| `direct_heating` | Spray dryer | The line stops. No source read describes a standby air heater | A site with several dryers has partial cover: the UK case had three [ETSU_GPG209] section 8.3 |
| `refrigeration` | Chiller | Not sourced | Not sourced |
| `machinery_motors`, `compressed_air` | Motors, compressors | Not sourced | Not sourced |
| Site electricity | CHP | Grid picks up instantly in parallel mode [BEIS_CHP2021] "Parallel Operation" (p18) | The grid, as back-up power |

**CHP outages.** Any engine or gas-turbine CHP needs inspection at least once a year, so at least one planned shutdown annually [BEIS_CHP2021] section 2.5 (p14). Typical availability is about 90 percent for gas engines and about 95 percent for gas turbines [BEIS_CHP2021] sections 2.2 and 2.3 (p12). A typical manufacturer's guarantee allows 438 h/yr scheduled and 420 h/yr unscheduled outage, which is a guaranteed availability of 90.21 percent, and the figures should be calculated for the planned operating regime [BEIS_CHP2021] section 2.5. 438 h is about 2.6 weeks. The CHP's own data row carries availability 0.93 and lifetime 25 years (`unit.csv`). CHP and turbines last about 20 years with a refurbishment at ten [DECC2015FD] p43.

**Gas supply.** A CHP on an interruptible gas supply must take all its electricity from the grid and its heat from other boilers during interruptions, ideally on a firm supply or another fuel [BEIS_CHP2021] section 2.8, Fuels (p25). A firm supply avoids this at a higher gas price.

## 6. Heat recovery and integration

| Route | What is recovered, and how much | Source |
|---|---|---|
| Spray dryer exhaust to inlet air or other sinks, via a coupled loop | Hot utility reduced by up to 21 percent with a well-chosen sink; recovery is limited by low exhaust temperature and fouling | [ATKINS_ATE2011] abstract and the summary of schemes (21.3 percent for the best milk-sink scheme) |
| Evaporator condensate and outlet air to preheat dryer air | Air reaches 55 °C before the final heater | [ETSU_GPG209] section 8.3 |
| Multistage drying (fluid bed integrated) | About 20 percent less drying energy | [BREF_FDM2019] section 5.4.2.8 |
| Multi-effect and vapour recompression evaporators | Steam use for single-stage 1.2 to 1.4 t/t water; TVR and MVR cut it further | [BREF_FDM2019] section 2.3.2.2.4 and Table 2.41 |
| CHP exhaust used for drying | Up to 90 to 95 percent fuel utilisation when HRSG exhaust feeds other drying | [BREF_FDM2019] section 2.1.2 |
| Pasteuriser regeneration | Much of the pasteurising heat is reused in the unit | [DECC2015FD] p41 |
| Boiler flue gas economiser | Raises boiler efficiency | [ETSU_GPG209] sections 8.3 and 11 |

Heat pumps are generally a good solution only once the site's heat recovery is optimised and only low-grade heat remains [BREF_FDM2019] section 2.1.2.1.2.

## 7. Decarbonisation in practice

| Route | Status and limit | Source |
|---|---|---|
| Steam production, distribution and end-use | Modelled as deployed to 25 percent of sites by 2050 in one roadmap scenario, 17.9 percent of that scenario's emissions reduction | [DECC2015FD] p69 |
| Waste heat recovery and CHP | Listed among the roadmap's modelled options; no deployment figure is quoted here | [DECC2015FD] p69 onward |
| Electrification of spray drying | Studied: a heat pump system with a heat recovery stage and three natural-refrigerant heat pumps, design air heating to 236 °C, energy saving ratio 0.55 to 0.58, levelised heat cost 35 to 36 €/MWh | [LIANG_ECOS2022] abstract |
| Heat pump options for spray drying | Air-to-air or water-source cascades, air heated from 11 to 15 °C to 200 to 210 °C, 1 to 10 MW; commercial products to 160 °C expected 2023/24, up to 250 °C later | [IEAHPT_A58_T2] section 2.1.3, Tables 2-8 and 2-9 |
| Barrier: production disruption | Medium to high impact on adopting low-carbon options; downtime on dairy lines is carefully planned and kept to a minimum | [DECC2015FD] p56 |

## 8. Reading the model's results

These points come from the `mvp-dairy` run (premise `mvp-dairy`, 2021 base year). They matter before any result is quoted.

**a. The dryer's four heat bands are one air stream.** `dryer_direct_gas` shows output on four bands in 2021: `heat_lt60` 0.0207, `heat_60_100` 0.0167, `heat_100_150` 0.0208 and `heat_150_400` 0.0208 PJ, total 0.0791. That is one stream of air heated once from 10.3 to 200 °C and split at the band edges for bookkeeping (note 20 item 71), using shares 0.262, 0.211, 0.264 and 0.264. In practice the lower segments can be served by exhaust preheat or a heat pump, as the sources above show ([ETSU_GPG209] section 8.3; [IEAHPT_A58_T2] section 2.1.3), and the optimiser may do the same. The model does not enforce the order of the segments, so it can serve an upper segment without the lower ones. Read the total, not the bands.

**b. The CHP and boiler split is an input, not a result.** Both units serve `boiler_steam_hot_water`. Their 0.35 and 0.65 split is a synthetic `capacity_share` in `premise_process_unit.csv`, not an optimiser choice: CHP heat 0.046053 is 0.35 × 0.131579. The worked example's own gas back-solve uses a CHP heat of 0.033595 PJ, about 26 percent of 0.131579 [CARB3_WE_FOOD] section 5.1, so the two differ. Which heat band each unit serves is arbitrary: the CHP serves all of `heat_100_150` and the boiler serves both bands, which are equal-cost solutions, with the surplus at 100 to 150 °C cascading down to 60 to 100 °C. Read each unit's total only.

**c. The model is annual.** CHP and boiler running together, and the boiler alone during CHP outages, both appear as one annual total per unit. The CHP's weeks of outage are in its availability factor, not in a time series.

**d. There is no backup or redundancy constraint.** On-site plant is bounded only by C2 (annual energy against capacity times availability). λ (the §5.6 peak factor) and C11 (connection capacity) concern the grid connection only. The model therefore will not size a boiler to carry the peak with the CHP out, and a result with no standby margin is not evidence that none is needed (section 5 gives what practice keeps).

**e. `boiler_spc_gas` is separate.** Its 0.0185 PJ is space heating under `site_services`, not the steam header.

**f. Reject heat is recovered by its source.** Each unit's reject heat lands on a carrier for its source class (spec §3.4, note 23 section 10). From 2025 the run builds `heat_pump_chiller_condenser`, which lifts the chillers' condenser heat to 60 to 100 °C for the boiler-house hot water, and, for the one period the CHP and the gas boiler still run, `recovery_engine_exhaust` and `economiser_flue_condensing` on their exhaust. The spray dryer's exhaust has no recovery unit yet, so the run disposes of it (0.0140 PJ in 2021), although section 6 lists exhaust-to-inlet-air recovery as practice [ATKINS_ATE2011].

## 9. Gaps and open questions

- **Number of UK food processing sites.** No source read gives it.
- **Boilers sized N-1.** No UK source read states whether boilers carry the full steam load with the CHP out. Vendor material says food plants often keep N+1 steam boilers, but it is general and not UK specific, so it is not used.
- **Backup for dryers, chillers and compressors.** No source read says what is kept, beyond the multi-dryer UK case.
- **HRSG and header specifics.** The steam pressure, the unit type (HRSG, waste heat boiler) and whether hot water is raised from steam by heat exchangers are not sourced.
- **Cleaning cycle detail.** CIP duration is sourced; the interval between full CIPs for a spray dryer is not.
- **Seasonal trough.** The spring peak is sourced; the size of the autumn and winter trough, and so a seasonal peak to mean, is not.
- **Peak to mean.** Only the worked example's illustrative values exist.
- **CHP maintenance weeks.** Hours are sourced as a manufacturer guarantee, not as a food-site average.

## Sources

- `[DECC2015FD]` DECC and BIS, *Industrial Decarbonisation and Energy Efficiency Roadmaps to 2050: Food and Drink*, 2015. Pages 12–13 sector size and technology shares, p30 energy use, p40 CHP capacity and fuel switching, p41 dairy and canning heat uses, p43 asset lives, p56 barriers, p69 scenario options.
- `[BEES2016]` BEIS, *Building Energy Efficiency Survey 2014-15*, Appendix B Table B.3, p122.
- `[MOEJES_IDS2016]` Moejes, Visser and van Boxtel, 20th International Drying Symposium, 2016, introduction and Table A1.
- `[LIANG_ECOS2022]` Liang et al., ECOS 2022, abstract.
- `[BEIS_LTM_2022]` BEIS, *Long-term mean temperatures 1991-2020*, Table 1.
- `[DESNZ_LCHC_NONDOM2022]` Verco and Currie & Brown, *Evidence update of low carbon heating and cooling in non-domestic buildings*, 2022, Table 1.
- `[CARB3_WE_FOOD]` This repository, food and drink worked example, sections 1.1, 1.2, 1.5, 1.5.1, 1.8, 1.9, 1.10, 3.2, 5.1.
- `[BREF_FDM2019]` European Commission JRC, *BAT Reference Document for the Food, Drink and Milk Industries*, 2019, https://bureau-industrial-transformation.jrc.ec.europa.eu/sites/default/files/2020-01/JRC118627_FDM_Bref_2019_published.pdf. Sections 2.1.2, 2.1.2.1.1, 2.1.2.1.2, 2.3.2.2.4 with Table 2.41, 5.2 and 5.4.2.8.
- `[BEIS_CHP2021]` BEIS, *Combined Heat and Power: Technologies, a detailed guide for CHP developers, Part 2*, February 2021, https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/961492/Part_2_CHP_Technologies_BEIS_v03.pdf. Sections 2.2, 2.3, 2.5, 2.6 and 2.8, and the Parallel Operation passage.
- `[ETSU_GPG209]` ETSU for DETR, *Reducing energy costs in dairies*, Good Practice Guide 209, 1998. Sections 2.1, 8.3, 9.1 and 11.
- `[ATKINS_ATE2011]` Atkins, Walmsley and Neale, *Integrating heat recovery from milk powder spray dryer exhausts in the dairy industry*, Applied Thermal Engineering, 2011, doi 10.1016/j.applthermaleng.2011.03.006. Abstract, section 2 and the summary of heat recovery schemes.
- `[IEAHPT_A58_T2]` IEA HPT Annex 58, *Task 2 integration concepts report*, 2024, https://heatpumpingtechnologies.org/content/uploads/sites/70/2024/04/annex-58-task-2-integration-concepts-report.pdf. Section 2.1.3, Tables 2-8 and 2-9.
- `[AHDB_SPRING2026]` AHDB, *GB milk production: 2026 spring peak*, 21 May 2026, https://ahdb.org.uk/news/gb-milk-production-2026-spring-peak.

New keys `BREF_FDM2019`, `BEIS_CHP2021`, `ETSU_GPG209`, `ATKINS_ATE2011`, `IEAHPT_A58_T2` and `AHDB_SPRING2026` are not yet in `docs/notes/data/references.csv`.
