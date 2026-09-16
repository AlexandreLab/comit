# Reference-data build — the open questions

**Date:** 2026-09-15 · **Companion to:** [`data/README_spec_tables.md`](data/README_spec_tables.md)

The thirteen §3 tables were built by eight research lanes under a no-invention rule, and each
lane's report ends with the questions it could not settle. This note gathers them, grouped by
what has to change to answer them, so they can be worked through in one sitting. Each item
names the report holding the full argument.

**Everything here is open unless the item says otherwise.** Items 1 and 36 were settled on
2026-09-15 and item 2 on 2026-09-16; each carries the decision inline, with the work items 1
and 36 leave behind in items 1a and 1b. The rest are undecided.

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

1b. **Lane `duty_a` answered the same problem by dropping the second duty instead of splitting
   it**, writing the dominant duty at 1.00 and naming the omitted one in `provenance` only.
   **Eight processes**, and neither the `site_services` split nor the §3.2 rule reaches them:
   Abattoir `scalding_singeing` (the >1000 °C singeing flame), Abattoir
   `hot_water_sterilisation_cleaning` (the 45 °C washdown), Creamery
   `heat_treatment_pasteurisation` (UHT at 120–140 °C), Creamery `evaporation_drying` (the
   evaporator's band-3 steam), Beet Sugar `crystallisation_sugar_house` (centrifugal `MOT` and
   granulator `DRY`), Foundry `shakeout_sand_reclamation` (thermal sand reclamation — a real
   gas duty, 0.05 of the activity's gas), Artificial Fibre `drawing_texturing` (the draw-frame
   drive), and Aircraft/Factory/Industrial NEC `other_process` (the gas component). **A missing
   duty is worse than a wrong share**: a bad number is visible to C10, an absent one is not.
   *`DONE_duty_a.md`, "Gaps".*
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
4. **`unit_input_output`'s `(unit_id, carrier_id)` key blocks two real cases**: every storage
   unit (consumes and produces the same carrier) and `ccs_amine`'s reboiler CO₂, which the cement
   example already flags. A `flow_direction` or `role` column in the key fixes both.
   *`DONE_units.md`, Q3 and G8.*
5. **Which host does a capture train name in `abates_unit_id` once D13 (a unit is family-or-node
   × fuel) has split the host into three?** Eleven of thirteen abatement units are blank. Making
   it a `process_id` matches how the cement example reasons. *`DONE_units.md`, Q2 and G3.*
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
    nobody publishes. The crosswalk is the open part: `IFD`, `INF` and `IIS` carry no space-heat
    commodity, so a separated heating process has no COMIT node and V1b needs a mapping rule.
    See item 1a for the eight processes this does *not* reach. *Both duty reports.*
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
