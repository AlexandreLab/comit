# Reference-data build — the open questions

**Date:** 2026-09-15 · **Companion to:** [`data/README_spec_tables.md`](data/README_spec_tables.md)

The thirteen §3 tables were built by eight research lanes under a no-invention rule, and each
lane's report ends with the questions it could not settle. This note gathers them, grouped by
what has to change to answer them, so they can be worked through in one sitting. Each item
names the report holding the full argument.

**Everything here is open unless the item says otherwise.** Items 1 and 36 were settled on
2026-09-15, items 2, 3, 4, 43 and 46 on 2026-09-16, and items 5 and 16 on 2026-09-17 — **nine
of the forty-nine**. Each carries the decision inline, with the work items 1 and 36 leave
behind in items 1a and 1b, and the work item 4 leaves behind in items 44 and 45. The rest are
undecided.

## A. Questions that change the specification

These are the ones with a consequence outside the reference data.

1. **§3.3 keys duties per process; the food-and-drink worked example resolves them per
   (process, vector).** The example lists `site_services` twice at `duty_share` 1.00 each, which
   sums to 2.0 under §3.3's rule. Both duty lanes built to §3.3 and rescaled the example's two
   rows on its own delivered energy. Adding a `vector` key column to §3.3, as §3.3.1 already has,
   would make 22 of lane `duty_b`'s 31 forced splits exact. *Both duty reports, Q1.*

   **Answered 2026-09-15, in §3.2 and §3.3 of the live spec.** Not a key change. A process is
   now defined as *one unit of demand — equipment whose duties share a driver*, drawing more
   than one vector is a **flag rather than a verdict**, and every such process resolves to one
   of three cases: **coupled** (one process, a `duty_share` from a sourced technical ratio),
   **uncoupled** (split the register, one process per driver), or **alternative technologies**
   (one process, one duty at 1.00, the vector split belonging to §3.16). The operational test
   is §3.13: two duties are coupled when they would carry the same `shape_class` and
   `seasonality`. §3.3 now forbids back-deriving a `duty_share` from the process's own §3.3.1
   vector shares, which is what produced all 22 fallback rows.

   **What that leaves to do is in item 1a. Nothing validates the classification** — there is no
   `coupling` field on §3.2 and no check that a multi-vector process was ever examined. Adding
   the field is the obvious enforcement point and is **not yet decided**: it would be required
   only where §3.3.1 gives the process more than one vector, and it would need populating
   across the register's 376 rows.

1a. **The eight processes the §3.2 rule reclassifies, and the counts that were wrong.** The
   earlier text here said `site_services` was "20 of 31" in lane `duty_b` and that 11 cases
   would remain. Both figures were wrong: 20 is lane `duty_a`'s multi-duty count, not
   `duty_b`'s share. Counted from
   [`activity_process_duty_profile.csv`](data/activity_process_duty_profile.csv):

   | Lane | Multi-duty processes | `site_services` | other |
   |---|---|---|---|
   | `duty_a` | 20 | 19 | 1 (the worked example's sourced `boiler_steam_hot_water` split) |
   | `duty_b` | 31 | 14 | 17 |

   Splitting `site_services` into end-use processes — **agreed 2026-09-15**, and the substance
   of item 36 — clears 33 of the 51. The residual is **eight** invented splits, and they are
   three different problems, not one:

   | Process | Written as | §3.2 case | What it needs |
   |---|---|---|---|
   | `Paper Mill / paper_machine_drying` | STM 0.91 / MOT 0.09 | **coupled** | A sourced steam-and-drive ratio per tonne. Cylinders and hood fans both follow tonnes of paper |
   | `Mineral Production - Brine / vacuum_evaporation` | STM 0.71 / MOT 0.29 | **coupled** | A sourced ratio. Steam per tonne is set by the number of effects; pump power largely is not, so it varies by plant design |
   | `Paper Mill / stock_preparation` | MOT 0.74 / LTH 0.26 | **coupled**, weakly | A source, or write `MOT` at 1.00 and name the incidental press-section heat in provenance |
   | `Wafer Fabrication / cleanroom_hvac` | SPC 0.75 / MOT 0.25 | **uncoupled** | Split. Make-up-air reheat is weather-driven (`seasonal`), fan power is `standing`. One §3.13 row cannot describe both, and today it says `standing` for the pair |
   | `Shipbuilding / painting_coating` | SPC 0.68 / MOT 0.32 | **uncoupled** | Split. Hall heating is weather-driven, extraction fans follow the work |
   | `Large industrial NEC / other_process` | LTH 0.64 / OTH 0.36 | **uncoupled** | Split. A residual catch-all bundle — `site_services` under another name |
   | `Motor Vehicle Works / paint_shop` | DRY 0.51 / MOT 0.49 | **uncoupled** | Split. The register already names three things: "booth air handling fans, ovens, e-coat". Booth fans have a real source (LBNL-50939 Table 2: 27–50% of assembly-plant electricity); the 140–180 °C bake is a separate `DRY` duty |
   | `Shipbuilding / steel_prep_cutting` | ~~HTH 0.76 / MOT 0.24~~ → **HTH 0.88 / MOT 0.12** | **coupled**, with a technology mix inside it | **Fixed 2026-09-15**, option (b) below. One residual assumption remains open |

   **`steel_prep_cutting` — fixed 2026-09-15, and the one residual assumption.** The register
   lists three things — "plasma/oxy-fuel cutting tables; **plate rolls**; gas-fired plate/forge
   heating" — which is two duties, not one. Cutting is a >1000 °C thermal duty whichever way it
   is done; plate rolls and presses are motive. But
   [`activity_process_energy_profile.csv`](data/activity_process_energy_profile.csv) describes
   this process's electricity as *"Plasma cutting and plate machinery"*, so the whole electric
   portion had been written as `MOT`.

   The effect was milder than first reported: the `HTH` duty **did** exist at `heat_gt1000`
   grade 6, and `generic_process_elec` was already eligible through the `plasma_electric_cutting`
   option, so C10 (the grade cascade) could see an electrifiable high-temperature duty. What was
   wrong was the **size** — `HTH` short by the plasma share, `MOT` long by it, so the premise
   electrified too little heat and too much shaft work.

   **What was applied.** [REF_ESAB] — the source this process's own `plasma_electric_cutting`
   option cites — calls CNC plasma *"standard for plate prep, replacing oxy-fuel for most
   thicknesses"*, which is warrant for treating cutting electricity as thermal duty. The energy
   profile names two electric components and weights neither, so they are taken at **equal
   weight**: of the 0.24 electric portion, 0.12 is plasma cutting and joins `HTH` (0.76 → 0.88),
   and 0.12 stays on `MOT` for plate rolls, presses, table drives and extraction — which is
   exactly the scope of the repo's own `controls_vsds` option for this process. Both rows are
   `fallback` / `low` and say all of this in their provenance. §3.16 gained a matching row: the
   `HTH` incumbent is now `generic_process_gas` 0.8636 **and `generic_process_elec` 0.1364**,
   the duty's own composition, so the electric route to a >1000 °C duty is visible to A4 (the
   baseline back-solve) rather than implied.

   > **The equal weighting is the open part.** Nothing published splits plasma cutting from plate
   > machinery at a UK yard. Equal weight is *conservative* against [REF_ESAB], which has plasma
   > as the dominant plate-prep route and would support a larger `HTH` share — so the error, if
   > any, understates electrifiable heat. A single sourced figure replaces it.

   **The two options not taken:** (a) source the split properly — still worth doing, and it is
   what the note above asks for; (c) split the register into `steel_cutting` and
   `plate_forming`, which the §3.2 driver test argues against, since both are `intermittent` and
   follow plate throughput.

   **It is also the clearest argument that §3.2, not the §3.3 key, was the right place to act.**
   A `vector` key column would have made "all electricity is `MOT`" the *rule* rather than an
   accident, entrenching the misfiling instead of exposing it.

1b. **Five duties that no rule can find: a second duty on the *same* fuel.** Lane `duty_a` met
   the same problem as item 1a and answered it differently — it wrote the dominant duty at 1.00
   and named the omitted one in `provenance` only. **Eight processes.** They are not one group:

   **Three are multi-vector, so the §3.2 rule does flag them.** They simply have not been
   reworked yet, and doing so is ordinary item-1a work:

   | Process | Vectors | Duty written | What is missing |
   |---|---|---|---|
   | Beet Sugar `crystallisation_sugar_house` | elec 0.25, gas 0.15 | `STM` 1.00 | centrifugal `MOT` and granulator `DRY` — the entire electric side |
   | Foundry `shakeout_sand_reclamation` | elec 0.04, gas 0.05 | `MOT` 1.00 | thermal sand reclamation — the entire gas side |
   | Aircraft works / Factory / Industrial NEC `other_process` | elec, gas | `OTH` 1.00 | the gas component (three activities) |

   **Five are single-vector, and nothing mechanical will ever find them.** The missing duty draws
   **the same fuel** as the one that was written — a different grade, or a different family, off
   one gas supply. The vector count cannot see it, because there is only one vector:

   | Process | Vector | Duty written | What is missing |
   |---|---|---|---|
   | Abattoir `scalding_singeing` | *(no energy-profile row at all)* | `LTH` band 2 | singeing, a direct flame above 1000 °C |
   | Abattoir `hot_water_sterilisation_cleaning` | gas only | `LTH` band 2 | the 45 °C washdown — band 1, same family, same boiler |
   | Creamery `heat_treatment_pasteurisation` | gas only | `LTH` band 2 | UHT at 120–140 °C — band 3, same family, same fuel |
   | Creamery `evaporation_drying` | gas only | `DRY` band 4 | the falling-film evaporator's own band-3 steam |
   | Artificial Fibre `drawing_texturing` | elec only | `PHEAT` band 4 | the draw-frame machine drive |

   **This is the standing limitation of the §3.2 rule, and §3.2 now says so.** A process showing
   one duty family at 1.00 is *unexamined*, not *confirmed simple*. Finding these needs someone
   reading process descriptions, not a validator. **A missing duty is worse than a wrong share**:
   a bad number is visible to C10 (the grade cascade), an absent one is not.
   *`DONE_duty_a.md`, "Gaps".*

1c. **The `coupling` field — six things to decide before it can be built.** §3.2 defines the
   three cases (coupled, uncoupled, alternative technologies) but carries no field holding the
   answer, so an unexamined process is indistinguishable from a classified one.

   | # | Decision | Note |
   |---|---|---|
   | 1 | **Scope** | Required only where §3.3.1 gives the process more than one vector — about **104 of 359 covered processes**, not all 376 register rows |
   | 2 | **Enum** | `coupled` / `uncoupled` / `alternative_technologies`, and whether to add `unexamined` so a backfill can be honest about what nobody has looked at |
   | 3 | **Blocking or advisory** | Does an unclassified multi-vector process fail `make data-check`? Blocking is the point of the field, and it means ~104 rows must be classified before the table ships |
   | 4 | **What the validator asserts** | The checks fall out of the enum: `uncoupled` ⇒ exactly one duty row; `alternative_technologies` ⇒ one duty row **and** more than one §3.16 row; `coupled` ⇒ more than one duty row, none tiered `fallback` once a ratio is sourced |
   | 5 | **Where it lives** | §3.2, not §3.3 — it is a property of the process, not of a duty |
   | 6 | **Who backfills** | ~104 rows is a lane, not an afternoon |

   It cannot catch the five single-vector cases in 1b either way; nothing can.

2. **§3.13 marked `duty_factor` and `peak_to_mean` required, and all 371 rows are blank.** No
   published load profile met the no-invention rule. *`DONE_loadshape.md`, Q1 and Q3.*

   **Answered 2026-09-16, in §3.13 of the live spec.** Both fields are now optional, and a
   blank means *shape known, magnitude not*. Where blank, §5.6 (the peak method) defaults
   `duty_factor` to 1.00 — the process runs on the plant's schedule, §3.12's shift pattern —
   and `peak_to_mean` to 1.00, no within-shift peakiness. That rebuilds the peak as the mean
   load over operating hours, the floor of the true peak, so C11 (the connection-capacity
   constraint) is lenient under it and never overstates a connection. The spec says in
   terms that the default is a conservative assumption informed by no data: it is not
   written into the table, the class table's indicative ranges are not the fallback, and a
   peak built from defaults is flagged in the output. The worked examples' 14 illustrative
   values stay in the examples and are **not** adopted as seeds, so that fourteen processes
   do not carry a precision the other 357 lack. Q3 of the lane report is closed by that.
3. **§3.13's and §3.14's `process_id` foreign key is one column short.** `process_id` is unique
   only within an activity. The table carries `carb3_activity` as an extra key; the spec should
   say so. *`DONE_loadshape.md`, Q4.*

   **Answered 2026-09-16, in the live spec.** The spec now says what the table and the
   validator already do. §3.13 keys on `(carb3_activity, process_id)`, references the register
   on the pair, and demotes `shape_id` to a surrogate; a key rule there records why the pair is
   needed (`dewatering_pumping` is `flat` at one activity and `standing` at another). §3.14,
   §3.9, §3.10 and §3.15, which had the same bare `process_id → activity_process_register`,
   now resolve through the premise's own `carb3_activity`. No data or validator change. The
   two options not taken: making `process_id` globally unique, which renames 141 register rows
   and everything citing them; and one shape row per name, which `dewatering_pumping` and the
   coming `site_services` split both break.
4. **`unit_input_output`'s `(unit_id, carrier_id)` key blocks two real cases**: every storage
   unit (consumes and produces the same carrier) and `ccs_amine`'s reboiler CO₂, which the cement
   example already flags. A `flow_direction` or `role` column in the key fixes both.
   *`DONE_units.md`, Q3 and G8.*

   **Answered 2026-09-16, in §3.6 of the live spec.** The key is now
   `(unit_id, carrier_id, role)`, and `role` replaces the three booleans
   `is_primary_output`, `is_reject` and `is_fuel_input` with one seven-value enum:
   `fuel_input`, `aux_input` and `emission_input` consume, `primary_output`, `coproduct`,
   `reject` and `emission` produce. `ccs_amine` now holds `co2_fuel_fossil` twice — the kiln's
   at −0.35257 as `emission_input` and its reboiler's at +0.10659 as `emission` — so the cement
   example's ⚠ is closed and its §13 item 10 with it. A store's charge leg is `aux_input` and
   its discharge leg `primary_output`.

   **The role rather than a bare `flow_direction`, because the direction was already in the
   sign.** What was *not* written down anywhere was whether an unflagged positive row was a
   co-product or a declared emission, and whether an unflagged negative one was an auxiliary
   input or captured CO₂; both were being inferred at read time from `(sign, carrier_kind)`,
   which is the same implicit derivation that produced the defect. V31 now checks that the
   role, the sign and the carrier kind agree, and that the triple is unique.

   **The 446 existing rows were migrated mechanically** by
   [`migrate_io_roles.py`](examples/migrate_io_roles.py), committed so the classification is
   auditable rather than asserted: 100 `fuel_input`, 115 `aux_input`, 4 `emission_input`, 111
   `primary_output`, 23 `coproduct`, 59 `reject`, 34 `emission`. The three booleans were
   mutually exclusive on every row and agreed with the sign on every row, so only the two
   unflagged buckets needed a discriminator, and `carrier_kind` supplied it.

   **What this does not do is make storage modellable.** The four standalone storage units
   (`battery_2h`, `battery_4h`, `thermal_store_hot_water`, `thermal_store_steam`) can now be
   written down, and still have no coefficients, because no published round-trip efficiency was
   found for the two thermal ones — that is item G7/G8 of `DONE_units.md` and is unchanged.
   PD2 (storage earns through hybrid units and through β) is also unchanged: β, the firm-capacity
   contribution in C11 (the connection-capacity constraint), is still the only way a standalone
   battery is worth building.
5. **Which host does a capture train name in `abates_unit_id` once D13 (a unit is family-or-node
   × fuel) has split the host into three?** Eleven of thirteen abatement units are blank. Making
   it a `process_id` matches how the cement example reasons. *`DONE_units.md`, Q2 and G3.*

    **Answered 2026-09-17, by removing the column.** Neither option was taken: `abates_unit_id`
    held one host and the question was which one, so the field was the defect. §3.5 drops it and
    the new §3.5.3 `unit_abatement_host` carries one row per (train, host) pair —
    `docs/notes/data/unit_abatement_host.csv`, **37 rows over all 13 abatement units**, none
    blank. The cement trains name the four kilns of `ICMKLND01`'s D13 fan-out; C3 and C4 take the
    **earliest** remaining life among a train's hosts, which at the cement works is one value
    because all three cohorts there are 2004. V33 (b) (every train names its hosts) is blocking
    in `make data-check`. A `process_id` would not have worked: `ccs_amine_ironmaking` hosts
    `hisarna_coal` and `tgr_blast_furnace_coke` but **not** `blast_furnace_coke`, all three of
    which share `blast_furnace_ironmaking`.
6. **Where does a demand-side option live?** Thirteen library options (insulation, controls,
   warm-mix asphalt) reduce a duty and change no unit, so `unit_eligibility` cannot express them.
   *`DONE_eligibility.md`, Q1.*
7. **§3.5.1 requires `process_id` in the key, and supply units have none.** Both worked examples
   leave it blank for PV and batteries; the table follows them. *`DONE_eligibility.md`, Q4.*
8. **`OTH` binds `electricity`, a primary carrier, on 15 rows** (lighting, welding, fab tools,
   electrolytic treatment), because §3.4 offers no service carrier for them. The knock-on is §7
   attribution: the consuming unit looks like a fuel burner. An `other_service` intermediate
   would fix it; lane `units` needs the same carrier for 7 generic units. *`DONE_duty_b.md` Q3,
   `DONE_units.md` Q6.*
9. **§3.16's `evidence_tier = sector_statistic` on the food-and-drink example is wrong by the
   statistic it cites.** DUKES 7.4 and ECUK U4 give food and drink a CHP share of 0.235, not the
   0.60 the example asserts, and the eligible unit there is `chp_gas_ccgt`. §3.2's arithmetic
   downstream of the 0.60 changes. *`DONE_default_unit.md`, Q7.*
10. **The cement worked example says "no unit here draws ambient heat" while listing
    `pv_rooftop`,** whose only coefficient is its output. The build sets `draws_ambient = TRUE`
    on PV and solar thermal, or V2 (the round-trip check) fails them. *`DONE_units.md`, Q10.*
11. **§3.6's "must close on energy" and V2's round-trip are different tests**, and
    `boiler_lt_gas` passes one and fails the other. *`DONE_units.md`, Q9.*
12. **`earliest_year` appears in §3.5's prose but not its field table.** *`DONE_units.md`, Q8.*
13. **`unit.min_viable_scale` and `unit_eligibility.min_duty` look like the same number in two
    places.** Neither has a source beyond the worked examples. *`DONE_units.md` Q4,
    `DONE_eligibility.md` Q3.*
14. **The data-migration document's items C1–C8 collide with constraints C1–C12.** Every lane had
    to disambiguate in prose. Renaming them (M1–M8, say) is cheap while few documents cite them.
    *`DONE_eligibility.md`, Q5.*

## B. Questions about the carrier set and the emission factors

15. **Gross or net calorific basis?** Twelve carrier factors are on DESNZ gross CV and four on UK
    ETS MRR net CV. The MRR values are what both worked examples already use (56.1, 63.1, 94.6).
    The lane recommends moving everything to MRR net CV. *`DONE_carriers.md`, Q1.*
16. **Do the `ef_<carrier>` series carry the gross factor or the net-of-biogenic one?** The files
    say gross, on the D15 (every emission is a carrier) reading; both worked examples say net.
    Getting this wrong zero-rates biomass twice or not at all. *`DONE_carriers.md`, Q5 — the
    lane says settle this first.*

    **Answered 2026-09-17: gross, and the files were right.** Both worked examples were
    brought to it rather than the other way round. Cement's §6.3 carries `waste_derived_fuel`
    at **92.0 gross** with `biogenic_fraction` 0.5109, from which A6 (the problem builder)
    derives fossil 44.9972 and biogenic 47.0028; food and drink's carries `solid_biomass` at
    **97.22 gross** with `biogenic_fraction` 1, from which A6 derives a `co2_fuel_biogenic`
    coefficient and no fossil one. Neither pre-splits, so §7.3's zero-rating applies exactly
    once. The decision underneath it (Alexandre, 2026-09-17) is that **biogenic CO₂ is part of
    a site's accounted emissions**: it is derived, it balances through C8 (carrier balance)
    like any other emission carrier, and it is reported as a vented `zero_rated` quantity —
    free to vent, not absent. Item 15 (gross or net *calorific* basis) is a different question
    and is still open.
17. **`waste_derived_fuel` is mapped to COMIT's inorganic MSW code, yet the cement example gives
    it a biogenic fraction of 0.511.** Both cannot be right; the fraction is blank. *Q7.*
18. **Grid electricity: average or long-run marginal factor?** Both series are in the file; they
    differ by 29% at the base year. *Q2.*
19. **Carbon price: Green Book appraisal value (£244/t at 2021) or UK ETS market price (£44/t)?**
    The worked examples use neither. *Q4.*
20. **Hydrogen `available = FALSE` on all 63 rows** because nothing published names a region for
    the 2031 network; C9 (infrastructure availability) therefore removes every hydrogen unit. The
    minimal defensible relaxation is stated but not applied. *Q6.*
21. **Should `carrier.csv` gain a `steam` carrier?** The 21 COMIT `Steam` technologies carry no
    carrier on either side of the lineage join. *`DONE_lineage.md`, Q5.*
22. **Eight carriers the options library's `displaces` column needed and the set lacks**: ammonia,
    biochar, raw biogas, HVO, petroleum coke, refinery fuel gas, marine gas oil, bio-feedstock.
    *`DONE_eligibility.md` §2.*

## C. Questions about the heat-grade bands

23. **The six-band set is this build's proposal.** Rank 1 (`<60C`) is used by one duty row;
    lane `duty_b` found no duty below 60 °C at all. *Both duty reports.*
24. **All 48 space-heat duties sit at band 2, and `unit.csv`'s `SPC` units have `grade_out` 1.**
    One side must move or no unit can serve space heat. *`DONE_default_unit.md`, Q1.*
25. **Refinery steam is band 4 and every CHP tops out at band 3.** *`DONE_default_unit.md`, Q2.*
26. **`heat_exchanger_lt_steam` consumes and produces the same band** (LTH and STM both at
    rank 3), so it has no coefficients. *`DONE_units.md`, G10.*
27. **Lime calcination at band 5 or 6? Non-ferrous foundry melting at 6?** *`DONE_duty_a.md`,
    Q2 and Q7.* **Band-boundary convention** (upper bound inclusive) to confirm. *`DONE_duty_b.md`, Q7.*

## D. Questions about units and costs

28. **Should the worked examples' costs win over COMIT's?** The build takes published UK figures
    first, then COMIT; the examples' fixture costs (`kiln_dry_coal` at £260m per Mt/yr against
    COMIT's £114.78m) are used only where nothing else exists. Re-running either example against
    this data reproduces its energy flows and not its £ figures. *`DONE_units.md`, Q1.*
29. **`glass_furnace_elec` moved from £380m to £33m per Mt/yr** on the BEIS 2018 fuel-switching
    figure — an order of magnitude, worth a second look. *`DONE_units.md`, §7.*
30. **Seventeen units the option join needs and the library lacks**, headed by any diesel
    mobile-plant unit (13 register processes have no unit at all), an aluminium electrolysis
    cell, vapour recompression and an electrode steam boiler. *`DONE_eligibility.md`, §2.*
31. **Nine COMIT technologies are `unmapped`** (three lime and two chemicals capture variants,
    two gas-fired boilers on works gases, two finishing processes): build the units or record
    them out of scope. *`DONE_lineage.md`, Q6.*
32. **Is 137 units the right size?** The brief expected about 98 before hybrids. *`DONE_units.md`, Q7.*
33. **Multi-fuel kilns are one-to-many in the lineage**; V1b needs an apportioning rule to be
    exact. *`DONE_lineage.md`, Q1.*
34. **Should the CHP share apply to `LTH` as well as `STM`?** Four rows drop if not.
    *`DONE_default_unit.md`, Q6.*
35. **Iron and steel has 840 GWh of CHP heat fuel in DUKES and no duty to put it on**, because the
    register has no steam or utilities process there. *`DONE_default_unit.md`, Q3.*

## E. Questions about the register and the existing tables

36. **`site_services` should be split** into end-use processes — at least an electrical bundle
    and a space-heating bundle. **Agreed 2026-09-15**; it is the single largest source of forced
    duty splits, 33 processes across the two lanes (19 of `duty_a`'s 20 multi-duty processes and
    14 of `duty_b`'s 31 — *not* "20 of 31 in one lane", which mixed the two). It needs no new
    evidence, because §3.3.1's existing vector shares already size both halves; splitting the
    electrical half further, into lighting, small power and compressed air, would need evidence
    nobody publishes. See items 1a and 1b for what this does *not* reach. *Both duty reports.*

    **The crosswalk is the only open part, and it is smaller than it looked.** COMIT's process
    commodities are `sector × duty × fuel`, so a space-heat node exists as `ICHSPC`, `ICRSPC`,
    `IEESPC`, `IMESPC`, `IOISPC`, `IPRSPC`, `ITXSPC`, `IVHSPC` — and **not** in `IFD` (food and
    drink), `INF` (non-ferrous), `IIS` (iron and steel) or `IPP` (paper). A separated space-heating
    process in a creamery therefore has no node to map to.

    **But space heating is not sector-specific, and COMIT's own data says so.** Every `SPC` node
    in every sector holds the same list of ordinary building-heating plant — gas boiler, electric
    boiler, hydrogen boiler, biomass boiler, heat pump, LPG, coal, and heat taken from site CHP.
    Nothing in any of them depends on what the building makes. Which subset a sector happens to
    carry varies arbitrarily (five rows in `ICR`, eight in `IOI`) and the naming is inconsistent
    (`IPR` says "Low-temperature heat space"), which reads as an artefact of how the workbook was
    assembled rather than a claim about the sectors. CaRB3 has already taken the same view:
    `unit.csv` holds `resistance_heater_spc`, `heat_pump_spc_air` and `heat_exchanger_spc_steam`
    with **no sector index at all**. What genuinely varies by sector is *how much* space heat a
    site needs — shed size, shift pattern — and that is demand, which CaRB3 holds in §3.3 and
    §3.3.1, not technology.

    **So the missing `IFD`/`INF`/`IIS`/`IPP` nodes are a gap in COMIT, not a statement that those
    sectors have no space heating.** Three ways to close it, cheapest first: map the separated
    process to the sector's `LTH` node and record a V1b divergence, which is what lane `duty_a`
    already does as a named analogue; leave the heating duty on the combined process for those
    four sectors only, splitting everywhere else; or add `SPC` nodes to the four sectors, which is
    a change to COMIT itself and not to CaRB3.
37. **`Mineral Production - Gas / power_generation` is a conversion unit, not a demand**, and
    should arguably leave the register. *`DONE_duty_b.md`, Q4.*
38. **SMR feedstock at oil refineries needs a `NEUOTH` row with a published feedstock/fuel
    split**; none was found. *`DONE_duty_b.md`, Q5.*
39. **`Mill`, Laboratory, Post Office Sorting Centre and Vehicle repair cannot be crosswalked** to
    COMIT and may not be modellable through V1b. *`DONE_duty_b.md`, Q9 and Q10.*
40. **`references.csv` has nine sources duplicated under two ids each.** *`DONE_duty_b.md`, Q8.*
41. **`retrofit_to` is empty on all 397 rows of `emissions_source_classification.csv`**, so the
    retrofit lineage cannot be derived from it. *`DONE_lineage.md`, §10.*
42. **`compressed_air`: §3.13's example list says `standing`, the food-and-drink example says
    `throughput_following`.** The table follows the example. *`DONE_loadshape.md`, Q2.*
43. **§10.2 and V20 (d) cite a `unit.is_storage` field that does not exist.** §3.5 carries
    `unit_class`, an enum whose values include `storage`, and `unit.csv` follows §3.5. Found
    2026-09-16 while doing item 4; nothing checks it.

    **Answered 2026-09-16, in §10.2 and V20 (d).** No new field. `unit_class = storage` is
    enough, because the other half of V20 (d) — "and no hybrid parent" — is a lookup against
    §3.5.2's bill of materials rather than a flag: `battery_2h`, `battery_4h` and
    `thermal_store_hot_water` are each named as a component of a hybrid and are exempt;
    `thermal_store_steam` is named by nothing and is the one unit V20 (d) actually binds
    today. A boolean would have had to be kept in step with the BOM by hand.
44. **Five `unit_input_output` rows net a fuel against a feedstock, or against a
    by-product, because the pair key left nowhere else to put the second term.** Each cites
    two COMIT rows falling on one CaRB3 carrier. **The arithmetic is correct** — every stored
    coefficient is the sum of its two source rows, checked against the workbook's
    `technology_input_output` sheet on 2026-09-16. What is wrong is what the sum *means*:

    | Row | Unit | CaRB3 carrier | COMIT rows summed | Stored |
    |---|---|---|---|---|
    | 248 | `steam_cracker_naphtha` | `petroleum_products_misc` | `INDNEUMSC` −90.72712 **feedstock** + `ICHPRO` **+5.05350** by-product | −85.67362 |
    | 256 | `steam_cracker_byproduct` | `petroleum_products_misc` | `INDNEUMSC` −19.81751 **feedstock** + `ICHPRO` **+3.93479** by-product | −15.88272 |
    | 273 | `steam_cracker_hydrogen` | `petroleum_products_misc` | `INDNEUMSC` −19.81751 **feedstock** + `ICHPRO` **+3.09015** by-product | −16.72736 |
    | 259 | `steam_cracker_byproduct` | `light_fuel_oil` | `INDLFO` −1.34181 fuel + `INDNEULFO` −2.28798 **feedstock** | −3.62979 |
    | 276 | `ammonia_smr_gas` | `natural_gas` | `IND_NGABOM` −9.95842 fuel + `INDNEUNGA` −33.99590 **feedstock** | −43.95432 |

    **Two distinct problems, and item 4 has already fixed one of them.** On rows 248, 256 and
    273 a *positive* by-product (`ICHPRO`, process by-products burned in CHP) is netted
    against a negative input — a carrier the unit both consumes and produces, which is
    exactly the case §3.6's `(unit_id, carrier_id, role)` key now holds as two rows. Writing
    them separately makes `steam_cracker_naphtha`'s 5.05 PJ of by-product visible to C8
    instead of buried in a feedstock number.

    **The other half needs a carrier that does not exist.** All five fold a `NEU`
    (non-energy use) **feedstock** into a fuel coefficient, because §3.4 has no feedstock
    carrier — which is item 22's eighth missing carrier and item 38's `NEUOTH` question. Until
    that exists the netting is unavoidable, and `ammonia_smr_gas` reads as burning 43.95 PJ of
    gas when 34.00 of it is never burnt at all. **That matters for §7**: a feedstock's carbon
    is embodied in the product, not released at the stack, so attributing it as fuel CO₂
    overstates the unit's direct emissions.

    **The provenance wording is also misleading** and should be fixed whenever the rows are:
    the bracket reads `(-43.95432 + -33.9959)`, which is the *result* and the second term, not
    the two terms. It also still cites the pair key as its reason. *`DONE_units.md`; the COMIT
    workbook sheet `technology_input_output`.*
45. **Two `unit_bill_of_materials.component_id` values resolve to nothing.** `pv` and
    `battery_8h` are named as components of the `pv_battery_*` hybrids, and `unit.csv` has
    `pv_rooftop` and no `battery_8h` at all. §3.5.2's component reference is not checked by
    `make data-check`, which is why it passes. It bites V20 (d) directly: that test asks
    whether a storage unit is named by a hybrid, and one of the three that are is named under
    an id that does not exist. Found 2026-09-16 while answering item 43. *This note.*
46. **The fuel-emissions rule was stated three times and two were incompatible; A6 now fires on
    the carrier, not the role.** §3.6 derived emissions "for every unit with a `fuel_input`
    row", while §3.4 and §5.1 both said emissions attach to any consumed `primary` carrier.
    D13 allows only one `fuel_input` per unit, so every *second* fuel a unit burns sits on
    `aux_input` and was silently zero-rated. Found 2026-09-16 by an independent review of the
    open-items triage.

    **Answered 2026-09-16, in §3.4, §3.6, §4 (A6), §5.1, §7.1 and V22.** A6 now derives fuel
    CO₂ over $\mathcal{C}^{\text{burn}}_u$ — every consumed carrier that is `primary` **and
    not** `is_indirect` — summed across carriers and roles. No new field and no new enum
    value: `is_indirect` already existed on §3.4 and already carried exactly this meaning.

    **The counts.** 84 rows in `unit_input_output.csv` draw a `primary` carrier as
    `aux_input`, across 35 units. 29 are `electricity` and stay zero-rated at the unit, because
    §7.8 charges an indirect carrier on the import — that is the whole reason `is_indirect` is
    the right discriminator rather than a new flag. The other **55 are combustible** and now
    book their carbon.

    **What it changes.** 24 of the 111 units with coefficients change their derived fossil
    CO₂. Four were emitting **exactly zero** while burning fossil fuel: `steam_cracker_hydrogen`
    (0 → 4190.8), `steam_cracker_elec` (0 → 3301.0), `lime_kiln_fluidbed_wdf` (0 → 2637.8) and
    `lime_lowcarbon_elec` (0 → 1310.0). `blast_furnace_coke` rises 36%, `tgr_blast_furnace_coke`
    45%. Three of the four zero cases are named as low-carbon routes, so under a carbon price
    they were strictly dominant and free. That is a modelling defect, not an accounting one.

    **It interacts with item 44 and the figures above are not final.** The steam crackers are
    exactly the units whose rows net a `NEU` feedstock into a fuel coefficient. Part of their
    increase is feedstock carbon that a feedstock carrier will remove again. Neither number is
    settled until both land; do not quote these four in isolation.

    **The sums are load-bearing.** A unit drawing three combustible carriers would, under a
    per-carrier derivation, emit three rows on one `(unit_id, co2_fuel_fossil, emission)`
    triple — a key collision of the kind §3.6's key was widened to prevent. A6 sums first.
    *This note; independent review of the triage, 2026-09-16.*
