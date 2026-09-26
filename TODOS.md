# TODOS

Everything still open on the CaRB3 reference data after the duty-family and cooling work,
consolidated on 2026-09-26. Each entry stands on its own. The plan that produced it is
[note 22](docs/notes/22_duty_family_gap_plan.md) (duty families and processes); the open
questions live in [note 20](docs/notes/20_reference_data_open_questions.md) (reference-data
open questions), whose item numbers are quoted below. The coverage check — `make data-report`,
"duty coverage", and the work list `make data-worklist` writes to
`docs/notes/data/build/unservable_duties.csv` — counts **2 of 427 duty rows unservable**.

## Decisions for Alexandre

- [ ] **The heat-band set and the rule for placing a duty in a band (note 20 items 23 and
  27).** Item 23 (the six-band heat set is this build's proposal) and the first half of item
  27 (lime calcination at band 5 or 6, non-ferrous melting at 6, and the band-edge convention)
  are still open. §3.4 of the live spec states the rule the build used — a heat duty takes the
  band of the hottest temperature it needs, a cooling duty the band of the coldest, and a band
  includes its lower edge — but no one has confirmed it. **Item 27 is only half answered:** its
  second half, "no unit reaches rank 6", was settled on 2026-09-25 by adding `kiln_ht_gas`,
  which is why note 20 counts it among the decided items while this entry keeps it open.
  Confirming or reversing the rule can move duty rows between bands, and the cooling rule
  mirrors whichever stands.
- [ ] **The two coke-oven processes need a representation before a unit can be added (note 20
  item 30).** Iron and/or Steel Works `coke_ovens` and Coking and Carbonising Plant
  `oven_battery_carbonisation` are the only unservable rows left. The coefficients are sourced
  and ready — `IS_BREF2012` Table 5.2: 1,220–1,350 kg of dry coal per t of coke, 360–518 Nm³ of
  coke-oven gas at 17–18 MJ/Nm³ (7,200–9,000 MJ/t coke), 3,200–3,900 MJ/t coke of underfiring
  gas — but two rules block the unit, and both are the user's call:
  1. **Feedstock carbon would be counted twice.** A6 (the problem builder) charges fuel CO₂ on
     every consumed primary carrier, so the coking coal would be charged at the oven and the
     coke again at the blast furnace. It needs the feedstock carrier of note 20 items 22 and
     44, or a rule that a converted carrier is not burnt.
  2. **Coke is a fuel carrier, not a product.** §3.9's rule (a process whose units make a
     `product` states no energy duty) does not apply, so the node's `HTH` row would stay a
     heat duty the coke oven cannot serve. Either coke is treated as a node product here, or
     the rule is widened to chemistry-spine units.
  No capex was searched once these were found.
- [ ] **Should the CO₂ bound in carbonatation be credited at the beet-sugar lime kiln?**
  `lime_kiln_sugar_coke` declares the full 785 kt CO₂ per Mt of quicklime (`EULA_ECOFYS_2014`),
  because §3.6 declares `co2_process` from stoichiometry, §3.4 charges it, the spec has no
  rule for CO₂ bound in a product, and the EU ETS also counts CO₂ bound in precipitated
  calcium carbonate as emitted (`CEMNET_LIME2022`). Physically most of it is reabsorbed in the
  juice. A credit would need a spec rule (a sink carrier, or a capture-like unit) and a
  sourced reabsorbed share.
- [ ] **The beet-sugar lime kiln has no consumer for its quicklime.** `quicklime` is an
  internal product (`may_export` FALSE), so C8 (carrier balance) pins the kiln to zero unless
  something at the sugar factory draws quicklime. Modelling juice purification as a unit that
  consumes quicklime and CO₂ would let the kiln run. The same structure already holds for the
  cement kiln and its grinder.

## Data to review

- [ ] **Two duty shares may have been copied from the fuel split (note 20 item 1a).** Large
  industrial (> 20,000 m2) NEC `other_process` (0.36 on `electric_service`, 0.64 on
  `heat_100_150`) and Oil refinery, gas processing etc `alkylation` (0.03 `REF`, whose
  provenance says the split was "computed from published vector weights"). §3.3 now forbids
  renormalising a process's own vector shares into duty shares. Check both against item 1a's
  list before relying on them.
- [ ] **40 units cannot be fully costed (note 20 item 49).** 15 have a blank `capex`, 13 a
  blank `lifetime`, 15 a blank `fixed_opex`, 13 each a blank `availability_factor` and
  `capacity_to_activity_factor`, 25 have no `unit_input_output` rows, and 3 declare a fuel
  they never consume. They reach 50 of `unit_eligibility.csv`'s 3,314 rows, all
  worked-example or options rows; the rebuilt family rows admit none of them.
- [ ] **11 of the 15 importable carriers lack a price in every period (note 20 item 48).**
  Only `natural_gas`, `light_fuel_oil`, `coal` and `electricity` are priced in all seven
  periods; `heavy_fuel_oil` has 2021 only. Units burning an unpriced fuel reach 1,392 of the
  3,314 eligibility rows. The new `lime_kiln_sugar_coke` burns `coke`, which has no price, so
  `carb3`'s admission screen drops it.

## Units not added for want of a source

- [ ] **An electric or induction furnace above 1000 °C.** The only candidate found, BEIS's
  electric tunnel kiln (`BEIS_IFS2018`), is "Ceramics only" and at TRL 5–6 (technology
  readiness level); no sourced induction-furnace cost was found.
- [ ] **A coal-fired unit above 1000 °C.** Foundry `melting_holding` keeps a coal furnace
  default that cannot reach rank 6 (the gas kiln serves the row as a candidate).
- [ ] **An absorption chiller and a dry cooler.** No sourced cost. No duty needs them today.
- [ ] **Band-4 steam ratings for the LPG, coal, oil and biomethane boilers.** The sources in
  hand (`BEIS_IFS2018`, `EPA_CHP_ST`) name the gas, hydrogen, biomass and electrode boilers
  only, so these four stay at `grade_out` 3.
- [ ] **A hydrogen mobile-plant unit.** `DESNZ_NRMM2023` gives component costs (fuel cells
  £250–500/kW, tanks £20–45/kWh, 45% efficiency), but a machine cost needs two unsourced sizing
  assumptions, and `hydrogen` has no import price (item 48), so the unit would be screened out
  anyway.
- [ ] **A coke-oven battery** — see the decision above.

## Proxy and fallback values to firm up

Each of these is in the data with `confidence` low and a provenance string saying why.

- [ ] `mobile_plant_diesel`: capex is the median of six endpoint costs per kW across loaders,
  excavators and dumpers, which vary by a factor of four; availability 0.9599 is borrowed from
  reciprocating CHP engines (`EPA_CHP_RICE`).
- [ ] `mobile_plant_battery`: no whole-machine price exists; capex is built from component
  costs with a battery sized from the report's own 150 kWh example, and lifetime and
  availability copy the diesel unit's.
- [ ] `potline_prebake_elec`: capex is the midpoint of the World Bank's $1,000–11,000 per
  annual tonne range; fixed opex is JRC's "capital and O&M" residual, which includes a capital
  charge; lifetime 30 years is an inert-anode conversion's; availability 0.8 is JRC's assumed
  capacity factor.
- [ ] `lime_kiln_sugar_coke`: costs, life and availability are COMIT's lime kiln, and the fuel
  figure is the EU average across kiln types.
- [ ] `cooling_tower_wet`: availability is `chiller_electric`'s, and its 1995 costs are
  converted at the 1997 euro rate (the series' first year).
- [ ] The Distillery `cooling_systems` 90/10 split (note 20 item 62).
- [ ] The `dryer_steam` 10% loss (note 20 item 64).
- [ ] `kiln_ht_gas`: availability is COMIT's gas furnace's, and the cost is a ceramics kiln's.
- [ ] `engine_mot_gas`: shaft efficiency is taken as the genset's electrical efficiency.
- [ ] `chiller_electric_lt0`: costs copy `chiller_electric`'s.

## Housekeeping

- [ ] **`docs/notes/data/build/check_units.py` does not run.** It reads
  `build/carrier_products_units.csv`, which is not in the tree, and dies with
  `FileNotFoundError`. Restore the staging file or drop the read. `make check` does not call it.
- [ ] **`check_duty_a.py` and `check_duty_b.py` do not run.** Both read lane staging files
  (`build/activity_process_duty_profile_duty_a.csv`, `_duty_b.csv`) that are not in the tree.
  Their `EN` family and cooling-band rules were updated on 2026-09-25. Restore or retire them.
- [ ] **Laboratory ultra-low-temperature freezers.** `lab_equipment` moved to
  `electric_service` as a whole. If `SLAB2011` Table 7 separates the freezers, split them out
  as a `REF` (refrigeration) duty on `cooling_lt0`.
- [ ] **Shipbuilding `steel_prep_cutting` names `generic_process_elec` as incumbent for its
  electric plasma-cutting share** (share 0.13636). That unit makes `electric_service`, not heat,
  so the default cannot serve the `HTH` (high-temperature heat) duty; no electric unit reaches
  rank 6.

## Done

The duty-family and cooling work of note 22 is complete: Tasks 1–10 and note 20 items 24, 25,
37, 60, 61, 62, 63, 64, 65 and 66 are settled, and item 27's unit half. The record of each is in
note 22 §8 and note 20. On 2026-09-26 the diesel and battery mobile-plant units, the aluminium
potline and the beet-sugar lime kiln took the unservable count from 24 to 2.
