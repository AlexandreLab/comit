# Reference-data build — the open questions

**Date:** 2026-09-15 · **Companion to:** [`data/README_spec_tables.md`](data/README_spec_tables.md)

The thirteen §3 tables were built by eight research lanes under a no-invention rule, and each
lane's report ends with the questions it could not settle. This note gathers them, grouped by
what has to change to answer them, so they can be worked through in one sitting. Each item
names the report holding the full argument. Nothing here has been decided.

## A. Questions that change the specification

These are the ones with a consequence outside the reference data.

1. **§3.3 keys duties per process; the food-and-drink worked example resolves them per
   (process, vector).** The example lists `site_services` twice at `duty_share` 1.00 each, which
   sums to 2.0 under §3.3's rule. Both duty lanes built to §3.3 and rescaled the example's two
   rows on its own delivered energy. Adding a `vector` key column to §3.3, as §3.3.1 already has,
   would make 22 of lane `duty_b`'s 31 forced splits exact. *Both duty reports, Q1.*
2. **§3.13 marks `duty_factor` and `peak_to_mean` required, and all 371 rows are blank.** No
   published load profile met the no-invention rule. Either the fields become optional and §5.6
   (the peak method) falls back on the class, or the table is unshippable until half-hourly work
   is done. The worked examples' 14 illustrative values are listed in the report if they are to
   be adopted as seeds. *`DONE_loadshape.md`, Q1 and Q3.*
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

36. **`site_services` should probably be split** into an electrical bundle and a space-heating
    bundle; it is the largest source of forced duty splits (20 of 31 in one lane). *Both duty
    reports.*
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
