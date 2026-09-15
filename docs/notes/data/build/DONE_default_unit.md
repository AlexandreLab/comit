# `DONE_default_unit.md` — lane `default_unit`, `activity_default_unit` (T18)

**Date:** 2026-09-15 · **Brief:** `brief_default_unit.md` + `00_CONVENTIONS.md`
**Target schema:** §3.16 of `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md`

## Files written

| File | Rows | What it is |
|---|---:|---|
| `docs/notes/data/activity_default_unit.csv` | 455 | the deliverable: §3.16 rows for all 427 duties |
| `build/check_default_unit.py` | — | the stdlib validator, run below |
| `build/build_default_unit.py` | — | the generator, so every number here is reproducible |
| `build/ecuk_u4_2024.json` | — | the ECUK Table U4 2024 fuel splits the generator reads |
| `references.csv` | +3 | `DUKES_7_4`, `ECUK_2025_U4`, `CARB3_EP` |

**Note on where these live.** The lane ran against `docs/notes/data/_staging/`; part-way through,
the coordinator renamed that directory to `docs/notes/data/build/` and merged
`references_default_unit.csv` into `references.csv` (now 306 rows). Both scripts resolve their
paths relative to themselves, so they run unchanged from the new location, and the validator now
treats the absence of the staging reference file as the merged state and checks that the three ids
resolve in `references.csv` instead — which they do.

## The check, and its result

```
$ python3 docs/notes/data/build/check_default_unit.py
duties in activity_process_duty_profile.csv: 427
default-unit rows:                          455
duties served:                              427 of 427
distinct units used:                        38 of 137 in unit.csv
...
All checks pass.
```

It runs the brief's four checks — `default_share` sums to 1.00 ± 0.015 per `(activity, set,
process, duty_family)`; every `unit_id` resolves to `unit.csv`; every `(activity, set, process)`
resolves to the register; and every `(unit_id, activity, process_id)` has a `unit_eligibility`
row, **reported as a count and never failed**, as the brief directs. It adds: §3.16 column order,
the three enums, `default_share ∈ [0, 1]`, primary-key uniqueness, `duty_family` resolves to a
real row of `activity_process_duty_profile.csv`, **no blank cells** (§3.16 allows none), no
`NA`/`-`/`?` placeholders, every `[REF_ID]` resolves, every duty is served, and — also **reported,
not failed** — the count of rows whose unit breaks C10.

---

## The CHP question, which the brief calls the point of this table

**CHP is now visible on 17 rows across 11 activities, and the share is traceable to two published
UK statistics.** I downloaded and read both.

**Numerator — [DUKES_7_4], worksheet 7.4.A, block "Fuel used to generate heat", column 2024.**
**Denominator — [ECUK_2025_U4], worksheet "Table U4", the 2024 block, "Low temperature process —
total" plus "Drying / separation — total".** Both sides are *fuel*, so the ratio is like for like,
and ECUK's rows are DUKES sectors, so the join is on the publisher's own SIC definition rather
than on a mapping I invented.

| DUKES 7.4 sector | CHP fuel for heat, 2024 (GWh) | ECUK U4 low-grade heat, 2024 (ktoe → GWh) | **CHP share** |
|---|---:|---:|---:|
| Chemicals | 7 358.3 | 916.9 → 10 663.5 | **0.690** |
| Paper, printing, textiles and other industries | 4 840.0 | 848.2 → 9 864.6 | **0.491** |
| Other industries | 2 545.0 | 827.9 → 9 628.5 | **0.264** |
| Food, beverages and tobacco | 5 156.2 | 1 886.4 → 21 938.8 | **0.235** |
| Mineral products | 288.7 | 199.3 → 2 317.9 | **0.125** |
| Vehicles | 71.7 | 239.9 → 2 790.0 | **0.026** |
| Mechanical engineering | 62.4 | 532.7 → 6 195.3 | **0.010** — below the 0.02 floor, no CHP row written |

Conversion 1 ktoe = 11.63 GWh. The share is applied to the `STM` and `LTH` duties — "the steam/LTH
duty", as the brief puts it — and the residual goes to boilers, `derived`, exactly as
`…-worked-example-food-drink.md` §1.12 shapes it.

**Three things about this number that a reader must not miss**, all of which are also written into
every CHP row's own `provenance`:

1. **It is a fuel-basis ratio, not a delivered-heat ratio.** A CHP delivers less heat per unit of
   fuel than a boiler, so the CHP's share of the *delivered duty* is lower than the figure here.
   Correcting it needs a fleet-average heat efficiency, which neither source gives, so I have not
   invented one.
2. **DUKES publishes no per-duty and no per-site share.** The denominator is the sector's whole
   low-grade heat end use, so this is a sector average applied to a duty, not a statistic about
   that duty.
3. **It is 2024 on both sides**, matching the worked examples' base year. DUKES also has 2025;
   ECUK U4's latest block is 2024, so 2024 is what makes the two joinable.

### Where the CHP actually landed

| Activity | Process | Duty | Unit | Share |
|---|---|---|---|---:|
| `Aircraft works` | `steam_hot_water` | STM | `chp_gas_ccgt` | **0.026** |
| `Beet Sugar Factory` | `evaporation` | STM | `chp_gas_ccgt` | **0.235** |
| `Beet Sugar Factory` | `crystallisation_sugar_house` | STM | `chp_gas_ccgt` | **0.235** |
| `Brewery` | `brewhouse` | STM | `chp_gas_ccgt` | **0.235** |
| `Chemical Works` | `distillation_separation` | STM | `chp_gas_ccgt` | **0.690** |
| `Chemical Works` | `utilities_steam` | STM | `chp_gas_ccgt` | **0.690** |
| `Distillery` | `distillation`, `coproduct_evaporation` | STM | `chp_gas_ccgt` | **0.235** |
| `Distillery` (`grain_distillery`) | `cooking_conversion`, `continuous_distillation` | STM | `chp_gas_ccgt` | **0.235** |
| `Food Processing Centre` | `boiler_steam_hot_water` | LTH **and** STM | `chp_gas_ccgt` | **0.235** |
| `Industrial NEC`, `Works`, `Large industrial NEC` | `steam_hot_water` | STM | `chp_gas_ccgt` | **0.264** |
| `Motor Vehicle Works` | `steam_hot_water` | STM | `chp_gas_ccgt` | **0.026** |
| `Provender Mill` | `steam_conditioning` | STM | `chp_gas_ccgt` | **0.235** |

### Four places the sector CHP exists but could not be asserted — all reportable

1. **Refineries have the largest CHP fleet in the UK and get no CHP row.** DUKES 2025 Chapter 7
   says "refineries alone accounting for the largest share of electrical capacity, 35 per cent",
   and Table 7.4.A gives coal extraction and oil refining **15 757.6 GWh** of CHP fuel for heat in
   2024 — more than every other industrial sector combined. `Oil refinery, gas processing etc` /
   `utilities_steam` is a **grade 4** duty in `activity_process_duty_profile.csv`, and every CHP
   unit in `unit.csv` has `grade_out` 3, so **C10 forbids a CHP from serving the UK's most
   CHP-intensive steam duty.** One of the two numbers is wrong. See question 2.
2. **Iron and steel has 839.9 GWh of CHP fuel for heat and no duty a CHP could serve.** The duty
   profile gives `Iron and/or Steel Works` no `STM` and no `LTH` duty at all — only `HTH`, `MOT`
   and `SPC`. ECUK's denominator for that sector is also structurally **zero** (ECUK puts all of
   iron and steel into high-temperature process and motors), so the share is not even computable.
   `unit.csv` carries `chp_bfg_gas_turbine` and `chp_cog_gas_turbine`, which exist precisely for
   this sector's blast-furnace and coke-oven gas. See question 3.
3. **Construction is deliberately excluded, and that removed two CHP rows.** An earlier pass
   mapped COMIT `Construction` onto DUKES "Other industries" and gave `Concrete Block Works` and
   `Concrete Product Works` a 0.264 CHP share. That is wrong: DUKES 7.4.A publishes **no
   construction row**, and "Other industries" is mostly sewerage and waste-management plant, which
   is not the same fleet. Construction now maps to nothing and gets no CHP. Stated because the
   generator records the choice in a comment and someone will otherwise re-introduce it.
4. **The CHP can only land where `unit_eligibility.csv` already offers one**, which is on
   `STM`-family register processes. `Creamery`, `Abattoir / Slaughter House` and `Flour Mill` are
   food-and-drink sites with real `LTH` duties and no eligible CHP, so the 0.235 share cannot be
   applied to them. §3.16 makes eligibility a precondition and I have not overridden it.

---

## Row counts and coverage

455 rows over 427 duties: **404 duties take one unit, 23 take more than one** (a CHP plus its
boiler residual, or a multi-fuel chemistry kiln).

| Column | Populated | Blank |
|---|---:|---:|
| all ten §3.16 columns | 455 | **0** — §3.16 allows no blank, and the validator enforces it |

| `evidence_tier` | Rows | | `confidence` | Rows | | `sizing_basis` | Rows |
|---|---:|---|---|---:|---|---|---:|
| `assumed` | 367 | | `medium` | 297 | | `duty_annual` | 435 |
| `derived` | 78 | | `low` | 158 | | `throughput` | 20 |
| `sector_statistic` | 10 | | `high` | 0 | | `duty_peak` | 0 |

The tier × confidence cross-tab is clean: `sector_statistic` and `derived` are always `medium`,
and every `low` row is `assumed`. **No row claims `high`**, for the reason
`README_activity_process_tables.md` already gives for its sibling tables.

`duty_peak` is unused: nothing in this lane's sources sizes plant off a peak, and choosing it
would be a claim about load shape that belongs to the `loadshape` lane, not here.

**38 of the 137 units in `unit.csv` are used.** The 99 unused are the decarbonisation options —
hydrogen boilers, heat pumps, electrolysers, CCS trains, PV, batteries — which is the correct
outcome for a *base-year* table and is enforced deliberately (see judgement call 2).

---

## Every judgement call I made

### 1. The four-rung ladder, and why eligibility beats C10

§3.16 makes two demands that the data cannot both satisfy: a row must have a `unit_eligibility`
entry ("is rejected" otherwise), and it must not "assert plant the model would refuse to build" —
which C10, enforced as a load filter (§5.5: "a unit whose `grade_out` is below the duty's grade is
not in `U_q`, so the variable is never created"), makes a real constraint. For **58 rows** no unit
satisfies both. The ladder, in order:

1. eligible **and** C10-clean **and** of the duty's own family → `derived`/`medium`;
2. eligible, C10-broken, right family → `assumed`/`low`, provenance says `C10 CONFLICT`;
3. eligible and C10-clean, wrong family → `assumed`/`low`, says `FAMILY FALLBACK`;
4. not eligible at all → `assumed`/`low`, says `NO ELIGIBILITY ROW`.

**Rung 2 comes before rung 3 deliberately.** An earlier pass had them the other way round and put
`motor_elec` on 42 space-heating duties, because on a `site_services` process the only C10-clean
eligible unit is a motor. A space-heating duty served by an electric motor is worse data than a
space-heating duty served by a boiler one grade too low, and the second is at least a *heat* unit
that names the right defect. Every one of these rows says which rung it came from, so
`grep -c 'C10 CONFLICT'` and `grep -c 'NO ELIGIBILITY ROW'` on the CSV return 58 and 49.

### 2. What counts as base-year plant

A heat pump, an electrolyser, a CCS reformer, a steam-fed heat exchanger, and anything burning
**hydrogen or grid biomethane** are excluded from the incumbent pool. They are what the model
*decides* to build; asserting one as the 2024 incumbent would let A4 back-solve a baseline that
does not exist. An earlier pass without this filter produced 33 rows of `heat_pump_lt_air`, 22 of
`heat_pump_ht` and one of `atr_gas_ccs` as *existing* plant, which is plainly wrong. The
abatement, storage and hybrid classes are excluded for the same reason, as are the novel routes
inside the chemistry spine (`kiln_fluidbed_wdf`, `*_calcium_looping_*`, `steam_cracker_elec`,
`hisarna_coal`, `tgr_blast_furnace_coke`, the low-carbon cement and lime variants). The cement
worked example's §1.11 agrees: it lists the CCS trains as candidates with `earliest_year` 2035 and
its §1.12 defaults name none of them.

**A CHP is never its own residual.** Three separate passes produced `chp_gas_ccgt` on both sides
of a split, because CHP units are the only `STM`-family units in the library. The residual pool
now excludes generators outright.

### 3. The fuel split does **not** come from renormalising the energy profile

The brief says to use `activity_process_energy_profile.csv`'s vectors to pick the incumbent fuel
unit. Its own example is the single-vector case, and that works. **For a multi-vector process it
does not, and doing it naively is a real defect I hit and backed out of.** `energy_share` sums to
1.00 *down the processes, per vector*: `Food Processing Centre` / `boiler_steam_hot_water` carries
`gas 0.62` and `oil 0.85`, which says "85% of this site's oil goes to the boiler", not "oil is 58%
of this boiler's fuel". Renormalising the two gave the dairy **more oil than gas**, which is
wrong. `Cement Works` / `kiln_pyroprocessing` carries six vectors at or near 1.00 and renormalised
to a meaningless 0.333 / 0.333 / 0.333.

So the split is now **two sources**, and every row says so:

- **which** fuels a process uses — `activity_process_energy_profile.csv`, as the brief directs;
- **how much of each** — `[ECUK_2025_U4]` Table U4, 2024, the per-sector, per-end-use fuel columns
  (solid / oil / gas / electricity), renormalised over the vectors the process actually carries.
  Duty families map to ECUK end uses as `HTH`,`PHEAT` → High temperature process; `LTH`,`STM` →
  Low temperature process; `DRY` → Drying / separation; `SPC` → Space heating; `MOT` → Motors;
  `REF` → Refrigeration; `OTH` → Other.

ECUK is on the brief's own list of admissible statistics, and this is what makes `Food Processing
Centre` come out at gas 0.708 / oil 0.057 rather than the reverse.

**One exception, and it is the better source.** `Cement Works` / `kiln_pyroprocessing` takes
`…-worked-example-cement.md` §1.12 **verbatim** — `kiln_dry_coal` 0.53, `kiln_dry_wdf` 0.39,
`kiln_dry_gas` 0.08 — because that is the only published per-unit fuel split for a chemistry
process anywhere in the repository, and ECUK cannot separate waste-derived fuel from coal anyway.

**Where ECUK cannot separate solid fuels** — five rows, at processes carrying both coal and
biomass or waste-derived fuel — the solid share is divided equally between them, the row is
`assumed`/`low`, and the provenance says in terms that **that division is not evidenced**.

### 4. `sector_statistic` is reserved, and only ten rows earn it

The brief allows `sector_statistic` for figures traceable to DUKES or ECUK, and `derived` where a
share was computed "from such a statistic **plus the energy profile**". The CHP share uses DUKES
and ECUK and *not* the energy profile, so the ten CHP rows are `sector_statistic`. Everything that
touches the energy profile — every fuel split, and every boiler residual — is `derived`, which is
also how the food-and-drink example marks its own 0.40 residual.

### 5. `throughput` for the chemistry spine, `duty_annual` for everything else

20 rows are `throughput`: the cement and lime kilns, cement and lime grinding, the steam cracker,
the blast furnace, the sinter plant, the BOF, the EAF, the paper machine and the refinery. That is
the cement example's §1.12 shape — a mass-denominated process sizes off throughput. Every service
unit is `duty_annual`, as both worked examples have it.

### 6. Where the energy profile has no row at all

**18 rows** sit on processes `activity_process_energy_profile.csv` does not cover — the silent
coverage gaps §3.3.1 names, `Cement Works` / `clinker_cooling` and `site_services` among them.
There is no evidenced incumbent fuel, so the row takes the duty family's default carrier
(electricity for `MOT`/`REF`/`OTH`, natural gas otherwise), is `assumed`/`low`, and says so.

---

## Gaps, and why each is a gap

### The single biggest finding: every `SPC` duty conflicts with every `SPC` unit

`activity_process_duty_profile.csv` puts **all 48 `SPC` duties at `grade_rank` 2** (60–100 °C),
taking the band from `…-worked-example-food-drink.md` §3.2's "SPC — space heating" at
`heat_60_100`. **Every `SPC` unit in `unit.csv` has `grade_out` 1** (`boiler_spc_gas`,
`boiler_spc_coal`, `boiler_spc_biomass`, `resistance_heater_spc`, `heat_pump_spc_air`,
`heat_exchanger_spc_steam`, `boiler_spc_hydrogen`, `boiler_spc_lpg`). Under C10 no space-heat unit
can serve a space-heat duty, and **43 of
my 58 C10-conflict rows are this one disagreement**. Neither lane is obviously wrong on its own;
together they are incoherent. The food-and-drink worked example sidesteps it by putting
`boiler_lt_gas` — an *LTH* unit, `grade_out` 3 — on the `SPC` duty, which is evidence the tension
was already felt and worked around rather than resolved. See question 1.

| Duty family | Unit | Rows | Activities |
|---|---|---:|---|
| SPC | `boiler_spc_gas` | 42 | 42 activities — effectively all of them |
| HTH | `furnace_ht_gas` | 9 | Aluminium, Brickworks, Coking, Iron and steel, Pottery, … |
| PHEAT | `refinery_process_heat_gas` | 3 | Oil refinery (`fcc`, `catalytic_reforming`, `other_units`) |
| SPC | `boiler_spc_biomass` | 1 | Distillery |
| HTH | `furnace_ht_coal` | 1 | Foundry (`melting_holding`) |
| PHEAT | `furnace_ht_gas` | 1 | Oil refinery |
| STM | `boiler_lt_gas` | 1 | Oil refinery (`utilities_steam`) |

The `HTH` group is a second, separate version of the same thing: **`unit.csv`'s highest
`grade_out` is 5, and the duty profile has 18 `HTH` duties at band 6** — cement and lime kilns,
coke ovens, brick firing, foundry melting, steel reheating, pottery firing. The kilns escape it
because their chemistry-spine units carry no `grade_out` at all; the rest do not. **There is no
unit in the library that can serve a >1000 °C duty.**

### Eligibility gaps — 49 rows, reported not failed as the brief directs

They fall into three kinds — **23** rows where `unit_eligibility.csv` has no entry for that
`(activity, process)` at all, **23** where it has entries but none burns the fuel the process
actually uses, and **3** where it offers every CHP variant and no boiler:

- **20 rows, mobile plant and quarrying.** `mobile_plant`, `quarry_mobile_plant`,
  `clay_extraction_mobile_plant`, `mobile_plant_trucks`, `drilling`, `digging_loading`,
  `haulage_mobile_plant`, `internal_haulage`, `materials_handling_loaders`,
  `mobile_crushing_screening`, `extraction_loading`, `windrow_turning` — 20 distinct
  `(activity, process)` pairs. These have **no `unit_eligibility` row at all**, and there is also **no diesel non-road-mobile-machinery unit in
  `unit.csv`** — so even if eligibility were added, `motor_elec` would be asserting that a quarry
  dump truck is an electric motor. That is a double gap and both halves need closing.
- **19 rows on the steam duties, where no eligible unit burns the incumbent fuel.** At `Brewery` /
  `brewhouse`, `Chemical Works` / `utilities_steam`, `Distillery` / `continuous_distillation`,
  `Beet Sugar Factory` / `evaporation` and the rest, `unit_eligibility.csv` offers every CHP
  variant plus an electric or hydrogen boiler, and **no gas boiler** — on 3 of them, no boiler at
  all, so a CHP would have to be its own residual. The boiler named is the library default and
  each row says which of the two it hit.
- The tail: `Aluminium Smelting Works` / `electrolysis_potlines` and `Beet Sugar Factory` /
  `lime_kiln` have no eligibility rows whatever; `Coking` / `oven_battery_carbonisation` is
  offered only a biomethane boiler and a biomethane CHP, neither of which is a coke oven.

The cause is visible in `unit_eligibility.csv`'s own notes: it was built **before T17 landed**
("Family derived from the worked examples: T17 … has not landed"), so it guessed each register
process's duty family. Now that T17 has landed, the two can be reconciled mechanically.

### Not done, and why

- **No `duty_peak` row.** Nothing here sizes plant off a peak; that is the `loadshape` lane's
  claim to make.
- **No refinery or iron-and-steel CHP**, per the four reportable cases above.
- **No delivered-heat correction to the CHP share.** It needs a fleet heat efficiency neither
  source publishes, and inventing one is exactly what convention rule 1 forbids.

## Sources: what I actually read

Unlike my `duty_a` lane, this one **did** go outside the repository, because the brief says T18
"has a real public source" and reserves a tier for it. I downloaded and parsed both workbooks
directly (stdlib `zipfile` + `xml.etree`; `pandas` is not installed):

- **[DUKES_7_4]** `DUKES_7.4.xlsx`, worksheet 7.4.A. I read the block headers (`Number of sites`,
  `Electrical capacity (MWe)`, `Heat capacity (MWth)`, `Electrical output (GWh)`, `Heat output
  (GWh)`, `Fuel used to generate electricity`, `Fuel used to generate heat`), the 1994–2025 year
  header, the sector rows, and the `DUKES Sectors` sheet's SIC definitions. Figures quoted are the
  2024 column.
- **[ECUK_2025_U4]** `ECUK_2025_End_Use_tables_200426.xlsx`, worksheet `Table U4`. Eight year
  blocks at rows 4, 46, 88, 130, 172, 214, 256, 298 (2024 back to 2017); I used the 2024 block and
  columns 4–53, whose headers name each end use × fuel pair.
- DUKES 2025 Chapter 7 (PDF) for the narrative quoted about refineries' 35 per cent share.

The two new `ref_id`s carry the exact worksheet, block, column and year in their `note` field, so
the figures are re-checkable without re-reading this file. `[CARB3_EP]` is the third, pointing at
the in-repo energy profile, and its note records the per-vector caveat in judgement call 3.
`references_default_unit.csv` had exactly the seven columns of `references.csv` and re-declared
none of its 270 ids; it has since been merged in and all three resolve there.

**Prices to 2021 GBP:** not applicable. This lane states no cost.

---

## Questions for Alexandre

1. **The `SPC` grade disagreement — which side moves?** All 48 space-heat duties are at band 2 and
   all eight space-heat units top out at band 1. Either the duty profile drops `SPC` to band 1
   (<60 °C, which is right for a wet radiator circuit but wrong for the 60–100 °C the food-and-drink
   example names), or `unit.csv` lifts the `SPC` units' `grade_out` to 2 (which is what a warm-air
   heater or an 80 °C LTHW circuit actually delivers). **I recommend the second**: the units are
   what changed, the duty band is quoted from a published worked example, and lifting `grade_out`
   also makes the example's use of `boiler_lt_gas` on an `SPC` duty unnecessary. One column, eight
   rows. Until it is decided, 43 of my rows carry a `C10 CONFLICT` marker.
2. **The refinery steam duty is grade 4 and every CHP is grade 3.** DUKES says refineries are the
   UK's largest CHP fleet by a wide margin. Either `Oil refinery, gas processing etc` /
   `utilities_steam` should be band 3 (refinery steam mains are typically below 400 °C but the
   *utility* steam header is not the hottest thing on the site), or the CHP units' `grade_out`
   should be 4. Whichever, at present the model cannot reproduce the real refinery baseline.
3. **Iron and steel has 839.9 GWh of CHP heat fuel and no duty to put it on.** The duty profile
   gives that activity no `STM` and no `LTH` row — my own `duty_a` lane wrote `site_services` as
   `SPC` + `MOT` and everything else as `HTH` or `MOT`. If integrated steelworks are to show their
   blast-furnace-gas and coke-oven-gas CHP (and `unit.csv` has `chp_bfg_gas_turbine` and
   `chp_cog_gas_turbine` waiting for it), the register needs a steam or site-utilities process at
   `Iron and/or Steel Works` and the duty profile an `STM` row for it. That is T17's file, not
   mine, so I have not added it.
4. **No unit in `unit.csv` reaches grade 6.** 18 `HTH` duties are at >1000 °C — cement and lime
   kilns, coke ovens, brick firing, foundry melting, steel reheating, pottery firing. The kilns are
   covered by chemistry-spine units with no `grade_out`, which is how they slip past C10, but that
   is an accident rather than a design. Should the service spine gain a `furnace_vht_*` family at
   `grade_out` 6, or should the chemistry spine absorb every band-6 duty?
5. **No diesel NRMM unit, and no eligibility for mobile plant.** 17 rows assert `motor_elec` on a
   quarry dump truck, a wheel loader or a truck mixer. A `nrmm_diesel` unit (and a
   `nrmm_battery_electric` beside it, since `battery_electric_nrmm` is already an option in
   `decarbonisation_options_library.csv`) would fix the base year and give the NRMM options
   something to displace.
6. **Should the CHP share be applied to `LTH` as well as `STM`?** The brief says "the steam/LTH
   duty", so I did both, which is why `Food Processing Centre` / `boiler_steam_hot_water` carries a
   CHP on its `LTH` row as well as its `STM` row. The worked example puts that `LTH` duty at
   `boiler_lt_gas` 1.00. If `STM` alone is intended, four rows drop out.
7. **The food-and-drink worked example's §1.12 will need updating, and so will §3.2 that depends
   on it.** The example asserts `chp_gas_turbine` **0.60** / `boiler_lt_gas` 0.40 on the `STM`
   duty, labelled `sector_statistic` "DUKES Table 7 / CHPQA register". The statistic actually gives
   food and drink **0.235**, and the unit that is eligible there is `chp_gas_ccgt` rather than
   `chp_gas_turbine`. The delivery document already says the example "rests on T17 and T18 data
   that does not exist … asserted by the example, not read from a table", so this is T18 doing its
   job — but §3.2's arithmetic uses the 0.60 explicitly ("the incumbent mix divisor of §1.12 —
   0.60 × 2.22220 + 0.40 × 1.13636 = 1.787864"), and that number and everything downstream of it
   change. **This is the one item here with a consequence outside the reference data.**

## Requests to other lanes / the coordinator

- **`unit.csv` (lane `units`):** questions 1, 2, 4 and 5 — `SPC` `grade_out`, CHP `grade_out`, a
  band-6 furnace family, and a diesel NRMM unit.
- **`unit_eligibility.csv` (lane `eligibility`):** the 49 rows above. The table was built before
  T17 landed and guessed duty families; it can now be regenerated against
  `activity_process_duty_profile.csv` instead. The two systematic fixes are (a) offer a boiler
  wherever a CHP is offered, and (b) give every mobile-plant process a row.
- **`activity_process_register.csv` / the duty profile (lane `duty_a`/`duty_b`):** question 3, a
  steam or site-utilities process at `Iron and/or Steel Works`.
- **The spec (`…-worked-example-food-drink.md` §1.12 and §3.2):** question 7.
- **Coordinator:** the three new ids are already merged into `references.csv` and resolve.
  Separately, `docs/notes/examples/validate_carb3_data.py` is modified in the working tree and I
  have not checked whether it yet knows about `activity_default_unit.csv`; T18's verify line in
  the delivery document names it, so it likely needs this lane's four checks folded in —
  **including the two that are reported rather than failed** (eligibility gaps, C10 conflicts),
  because failing those today would fail `make data-check`.
