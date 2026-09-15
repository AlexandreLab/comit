# DONE — lane `eligibility`

Deliverables for `T9` (connect the options library to the unit set) and data-migration
items **C1–C4 and C8**.

> **Label collision, flagged rather than worked around.** The data-migration document's
> TODO items are lettered `A1`–`E4`, so its **C1–C8** sit in the same letter space as the
> live spec §5.5 constraints **C1–C12**. Below, a data-migration item is always written
> *"data-migration C2 (build the missing option→unit join)"* and a constraint always
> *"C1 (duty satisfaction)"*. This is the third such collision the repository has hit
> (`CLAUDE.md`, "Label families"); a rename of the data-migration letters is a question
> for Alexandre, below.

## Files written

| File | Rows |
|---|---|
| `docs/notes/data/decarbonisation_option_unit.csv` | **163** (134 options, every one with ≥ 1 row) |
| `docs/notes/data/build/decarbonisation_options_library_aligned.csv` | **134** (the library unchanged, three columns added) |
| `docs/notes/data/unit_eligibility.csv` | **2,612** |
| `docs/notes/data/build/references_eligibility.csv` | 6 (all internal; see "References") |
| `docs/notes/data/build/build_eligibility.py` | the generator — every judgement below is a named constant in it |
| `docs/notes/data/build/check_eligibility.py` | 10 blocking checks, **all passing** |

Nothing outside this list was touched. `carrier.csv`, `unit.csv`,
`activity_process_register.csv`, `activity_process_energy_profile.csv`,
`decarbonisation_options_library.csv`, `process_decarbonisation_options.csv`,
`references.csv`, the specs and the READMEs are all unmodified.

Reproduce with:

```
python3 docs/notes/data/build/build_eligibility.py
python3 docs/notes/data/build/check_eligibility.py
```

## Check results

`check_eligibility.py` runs the brief's five checks plus five more and passes all of them:
every option has a join row; every `unit_id` resolves to `unit.csv`; every
`(carb3_activity, process_id)` resolves to the register; every `carrier_id` in
`displaces_carrier_ids` resolves to `carrier.csv`; every `[REF_ID]` resolves; the aligned
library's 134 rows and 12 original columns are byte-identical to the library's; enums are
spelled as §3.5.1 spells them and booleans are `TRUE`/`FALSE`; `unit_eligibility` is unique
on `(unit_id, carb3_activity, process_id)`; `min_duty`, `max_share` and `earliest_year`
parse and `max_share` lies in [0, 1]; `route_change` agrees with the join by construction.

---

## 1. `decarbonisation_option_unit.csv` — the join (data-migration C2)

### Coverage

| Column | Populated | Blank |
|---|---|---|
| `option_id` | 163 | 0 |
| `unit_id` | 100 | **63** |
| `relationship` | 163 | 0 |
| `notes` | 163 | 0 |
| `provenance` | 163 | 0 |
| `confidence` | 163 | 0 |

A blank `unit_id` means the row needs a unit `unit.csv` does not carry, which the brief
allows and §2 below enumerates.

### Relationship mix

| `relationship` | Rows | Options |
|---|---|---|
| `is_unit` | 65 | 42 |
| `none` | 58 | 58 |
| `enables` | 18 | 16 |
| `route_change` | 13 | 12 |
| `supply` | 9 | 6 |

No option carries two different relationships, which was not designed for but is worth
recording: the classification turned out to be a property of the option, not of the pairing.

### The 58 `none` rows are six different things, and only one of them is a data gap

Every `none` note opens with one of six prefixes, so the file can be filtered on it.

| Prefix | Options | What it means |
|---|---|---|
| **GAP-UNIT** | 27 | A unit *could* represent this and `unit.csv` has none. **This is the actionable set** — §2 |
| **DEMAND-SIDE** | 13 | The option reduces a **duty** (§3.3 / §3.9), not a unit coefficient. No unit can express it and none should |
| **OUT-OF-SET** | 8 | Genuinely outside the premise's carrier balance — F-gases, fugitive methane, embodied carbon in aggregate, off-boundary vehicle charging |
| **ARCHITECTURAL** | 4 | Already expressible, but as **reject-heat coefficients (data-migration B5) plus C10 (the heat grade cascade)**, not as a unit |
| **GAP-CARRIER** | 1 | `ammonia_industrial_fuel`: no ammonia carrier *and* no ammonia-fired unit |
| **NOT-A-UNIT** | 1 | `h2_ready_equipment` is a procurement attribute; it moves `earliest_year`, not what is built |

The three lists worth reading in full:

- **DEMAND-SIDE (13):** `building_fabric_upgrade`, `dairy_membrane_preconcentration`,
  `destratification_radiant_conversion`, `dry_body_preparation_ceramics`,
  `fast_firing_low_thermal_mass_kilns`, `fume_cupboard_vav_sash_management`,
  `insulation_upgrade`, `lab_air_change_reduction_dcv`, `low_bake_paint_chemistry`,
  `low_temperature_tanning_chemistry`, `processless_ctp_plates`,
  `rotating_packed_bed_intensification`, `warm_mix_asphalt`.
- **OUT-OF-SET (8):** `carbonated_manufactured_aggregate`, `co2_mineralised_concrete`,
  `ev_fleet_charging_infrastructure`, `increased_rap_content`,
  `low_gwp_process_gas_substitution`, `pfc_point_of_use_abatement`,
  `steel_offgas_ccu_ethanol`, `vam_thermal_oxidation`.
- **ARCHITECTURAL (4):** `kiln_dryer_cascade_heat_recovery`, `lab_exhaust_heat_recovery`,
  `paint_shop_heat_recovery`, `waste_heat_recovery_process`.

**The finding underneath.** Thirteen options — a tenth of the library, and the cheapest
ones in it — are pure demand-side reductions, and the CaRB3 entity set has nowhere to put
them. `unit_eligibility` (§3.5.1) screens *supply*; there is no equivalent that scales a
`process_duty` (§3.9) row. Until there is, the model cannot choose insulation over a heat
pump, which is the wrong answer in most of the 55 activities. **Question 1 below.**

---

## 2. Units the join needs and `unit.csv` does not have

Grouped by the gap, not by the option, because several options share one missing unit.
The `units` lane owns `unit.csv`; per convention 6 these are requests, not edits.

| Missing unit | Options blocked | Note |
|---|---|---|
| **Mobile plant / NRMM** (any drivetrain) | 7 — `battery_electric_nrmm`, `hydrogen_nrmm`, `hvo_bio_oils_dropin`, `tethered_electric_excavator`, `hydrogen_fuel_cell_haul_truck`, `trolley_assist_haul_trucks`, `grid_electric_drilling_rig`, plus 2 crusher-drive options | **The single biggest gap.** 13 register `process_id`s across 13 activities are diesel mobile plant with no unit at all — §4 |
| **Aluminium electrolysis cell** | 3 — `carbothermic_aluminium`, `inert_anode_smelting`, `wetted_drained_cathode` | `electrolysis_potlines` and `anode_production_baking` are Aluminium Smelting Works processes with no chemistry node |
| **Vapour recompression (MVR / TVR)** | 3 — `mvr`, `still_tvr_thermocompression`, `wort_vapour_energy_recovery` | `heat_pump_ht` is **not** a substitute: MVR compresses the process vapour itself and its effective COP is an order of magnitude higher |
| **Superheated steam dryer** | 2 — `superheated_steam_drying`, `superheated_steam_drying_paper` | `dryer_steam` is a conventional steam-heated dryer; near-total latent-heat recovery is a different coefficient set |
| **Refinery process heat on hydrogen or electricity** | 2 — `refinery_low_carbon_hydrogen_fuel_switch`, `refinery_process_heater_electrification` | The `PHEAT` family carries `refinery_process_heat_gas` only |
| **Coke oven battery** | 2 — `coke_dry_quenching`, and the `coke_ovens` register process | No chemistry node; §4 |
| **Heat pump above 150 °C** | 2 — `htp_heat_pump_150_200`, `heat_pump_above_200` | `heat_pump_ht` is the top of the ladder |
| **Electric kiln / calciner** | 2 — `electric_kiln_calcination`, `kiln_net_zero_fuel_mix_h2_biomass` | Every `kiln_*` and `lime_kiln_*` unit is fossil-fired |
| **Electrode boiler on steam** | 1 — `electrode_boiler` (mapped to `resistance_heater_lt` as the nearest) | The `STM` family has **no** electric unit at all: only `heat_pump_ht` and eleven CHPs |
| Direct-separation (LEILAC) calciner | 1 | |
| Coke-oven-gas hydrogen separation | 1 | `EN` has electrolysers and reformers only |
| Electrified steam reformer | 1 | |
| Sorption (zeolite) dryer | 1 | |
| CO₂-curing chamber | 1 | |
| Fermentation CO₂ capture | 1 | And `co2_captured` is defined as CO₂ *to the transport network*, not merchant CO₂ |
| Electrochemical synthesis node | 1 | |
| Lighting | 2 — `led_high_bay_lighting`, `lab_led_lighting_controls` | Both are also DEMAND-SIDE, so a unit may not be the right answer |

Carriers the join needed and `carrier.csv` does not have — the `carriers` lane owns it:
**ammonia**, **biochar**, **raw biogas** (only the upgraded `biomethane` exists),
**HVO / bio-oil**, **petroleum coke**, **refinery fuel gas**, **marine gas oil**,
**bio-feedstock**. Each is named in the note of the row that needed it.

---

## 3. `decarbonisation_options_library_aligned.csv`

The 12 original columns and all 134 rows are unchanged and in the original order; three
columns are appended.

| Column | Populated | Blank |
|---|---|---|
| `displaces` (original) | 130 | 4 |
| `displaces_carrier_ids` (**C1**) | 124 | 10 |
| `route_change` (**C3**) | 134 (12 `TRUE`) | 0 |
| `exclusivity_group` (**C4**) | 56 | 78 |

### C1 — normalising `displaces`

44 distinct free-text tokens across the 134 rows. The map is a named constant,
`DISPLACES_TOKEN_MAP`, so every decision is one line of readable code. Reasoning:

- **Straight synonyms.** `gas`, `natural gas`, `natural_gas`, `natural gas (burners)`,
  `natural gas (cutting fuel)` → `natural_gas`. `grid electricity`, `grid_electricity`,
  `Hall-Heroult electrolysis electricity` → `electricity`. `grid hydrogen` → `hydrogen`.
  `propane` → `lpg`. `waste_fuels` → `waste_derived_fuel`.
- **Solid fuel grades.** `anthracite` and `pulverised coal (PCI)` → `coal`;
  `foundry coke` and `coke breeze` → `coke`; `coking coal` → `coking_coal`;
  `coke oven gas (steam raising)` → `coke_oven_gas`.
- **`oil` (23 rows) is the one genuinely ambiguous token.** `carrier.csv` splits oil into
  `light_fuel_oil` and `heavy_fuel_oil`; the library uses one word for both. For boiler and
  furnace duties it maps to **both**. For the three mobile-plant options where "oil" plainly
  means diesel — `battery_electric_nrmm`, `hydrogen_nrmm`, `hvo_bio_oils_dropin` — it maps to
  `light_fuel_oil` alone, whose `carrier_name` is "Light fuel oil (gas oil / diesel)". The
  override is the constant `OIL_MEANS_DIESEL`. `diesel`, `gasoil`, `heating_oil` and
  `marine diesel/gas oil (auxiliary engines)` → `light_fuel_oil`.
- **Feedstock.** `crude_feedstock` and `fossil_feedstock` → `petroleum_products_misc`, which
  is `carrier.csv`'s non-energy-use petroleum carrier (COMIT `INDNEUMSC`) and the one
  `unit.csv`'s `non_energy_use_feedstock` binds to. **This is the weakest mapping in the
  table** — crude oil at a refinery is not literally a miscellaneous non-energy-use product.
  Flagged, not hidden.
- **Emissions.** `process_co2`, `carbon anodes (process CO2)` and
  `process CO2 emissions (BF/BOF gas carbon)` → `co2_process`.
- **14 tokens map to nothing**, per convention 1 — a blank beats a plausible neighbour:
  `petcoke` (2 options), `refinery_fuel_gas` (2), `f_gases` (2), `virgin_aggregate` (2),
  `kiln_fuel` (4), `acetylene`, `anode baking fuel`, `biogas`, `bitumen`, `chemicals`,
  `fugitive_methane`, `petrol`, `purchased_co2`, `sinter`. Four of these are *duties* or
  *materials* rather than carriers (`kiln_fuel`, `anode baking fuel`, `sinter`, `bitumen`)
  and should stay blank permanently; the rest are carrier requests in §2.

Six options end with a non-blank `displaces` and a **blank** `displaces_carrier_ids`:
`fermentation_co2_recovery`, `low_gwp_process_gas_substitution`,
`pfc_point_of_use_abatement`, `refinery_low_carbon_hydrogen_fuel_switch`,
`refinery_process_heater_electrification`, `vam_thermal_oxidation`. A further **15** lose
part of a list. A validator that asserted "non-blank `displaces` implies non-blank
`displaces_carrier_ids`" would be wrong today and the check script deliberately does not
assert it.

### C3 — `route_change`

`TRUE` on **12** options, and **derived from the join rather than judged twice**: it is true
exactly where a join row carries `relationship = route_change`, which `check_eligibility.py`
asserts. `alkali_activated_binder`, `carbothermic_aluminium`, `cupola_to_induction`,
`electrified_static_processing_plant`, `electrochemical_synthesis_routes`, `h2_dri_eaf`,
`hisarna_smelting_reduction`, `inert_anode_smelting`, `ipcc_in_pit_crushing_conveying`,
`iron_ore_electrowinning`, `molten_oxide_electrolysis`, `recycled_cement_clinker_cec`.

The test applied is README challenge #7's: does the option replace or eliminate **more than
one register process**? That admits the three the README names (H2-DRI+EAF, molten oxide
electrolysis, cupola→induction) and nine more it does not, each justified in the join row's
note — `hisarna_smelting_reduction` says in its own `duty` text that it eliminates the coke
ovens and sinter plant; `ipcc_in_pit_crushing_conveying` moves the haulage duty into
crushing; `alkali_activated_binder` removes the clinker kiln outright.

`tgr_bf_ccs` is deliberately **`FALSE`**: it is a retrofit to one process plus a capture
train, not a route replacement, and it earns its exclusivity through
`primary_ironmaking_route` instead.

### C4 — exclusivity groups

16 groups over 56 options. **The test applied: would the LP's own algebra already stop
these being taken together?** Where two options resolve to the same unit, or compete for one
duty through C1 (duty satisfaction) and the capacity balance, no group is set — otherwise
half the library would be one meaningless group, since every boiler fuel-switch option is an
"alternative" to every other. A group is set only where addition is otherwise unchecked: a
shared feedstock or heat stream, a whole-route choice, or options carrying no unit at all.

| Group | Members | Why they cannot be summed |
|---|---|---|
| `ad_biogas_use` | `ad_chp_heat_integration`, `ad_heat_pump_digester_heating`, `biogas_upgrading_grid_injection`, `digestate_drying_chp_waste_heat` | README challenge #8's own example. Upgrading biogas to biomethane removes the CHP, so it kills both heat-integration options outright |
| `biochar_feedstock` | `bf_biochar_injection`, `biocarbon_fuel_substitution` | README challenge #8's second example: one UK char pool |
| `clinker_substitution` | `clinker_substitution_scm`, `calcined_clay_lc3`, `alkali_activated_binder`, `recycled_cement_clinker_cec` | One clinker-replacement headroom; the first two resolve to the *same* unit |
| `flue_gas_capture` | `post_combustion_amine_ccs`, `oxyfuel_ccs`, `calcium_looping_ccs`, `direct_separation_leilac`, `lime_oxyfuel_flash_calcination` | One capture train per stack |
| `primary_ironmaking_route` | `h2_dri_eaf`, `hisarna_smelting_reduction`, `molten_oxide_electrolysis`, `iron_ore_electrowinning`, `tgr_bf_ccs` | One primary ironmaking route per works |
| `aluminium_cell_route` | `carbothermic_aluminium`, `inert_anode_smelting` | Carbothermic smelting removes the cell the inert anode sits in |
| `vapour_recompression` | `mvr`, `still_tvr_thermocompression`, `wort_vapour_energy_recovery` | One recompression scheme per vapour stream; none has a unit, so nothing else separates them |
| `paper_drying_route` | `superheated_steam_drying_paper`, `impingement_tad_drying_conversion`, `electric_tissue_drying_hood` | One dryer-section conversion per machine |
| `coating_cure_route` | `uv_cure_coatings`, `eb_cure_coatings`, `low_bake_paint_chemistry`, `electric_powder_coating_oven` | One cure mechanism per oven |
| `ceramic_firing_route` | `electric_tunnel_kiln_firing`, `microwave_assisted_ceramic_firing`, `fast_firing_low_thermal_mass_kilns` | One kiln |
| `space_heat_conversion` | `ashp_space_heating_industrial`, `air_to_air_hp_warm_air`, `electric_radiant_space_heating` | The first two resolve to the same unit; all three serve the whole `SPC` duty |
| `nrmm_traction` | `battery_electric_nrmm`, `hydrogen_nrmm`, `hvo_bio_oils_dropin`, `tethered_electric_excavator`, `hydrogen_fuel_cell_haul_truck`, `trolley_assist_haul_trucks`, `grid_electric_drilling_rig` | One drivetrain per machine, and **none of the seven has a unit**, so the group is the only thing separating them |
| `mobile_crusher_drive` | `diesel_electric_hybrid_mobile_crushing`, `plug_in_electric_mobile_crushing_screening`, `electrified_static_processing_plant`, `ipcc_in_pit_crushing_conveying` | Four ways to drive one crushing duty; the hybrid is explicitly an "interim step" toward the plug-in |
| `lab_ventilation_reduction` | `fume_cupboard_vav_sash_management`, `lab_air_change_reduction_dcv` | Both cut the same exhaust volume; their savings are not additive |
| `refinery_process_heat_route` | `refinery_low_carbon_hydrogen_fuel_switch`, `refinery_process_heater_electrification` | One conversion per fired heater; neither has a unit |
| `concrete_co2_utilisation` | `co2_mineralised_concrete`, `carbonation_curing_precast`, `carbonated_manufactured_aggregate` | Compete for one CO₂ stream and one product |

**One option belongs in two groups and the column cannot say so.** `bf_biochar_injection`
competes with `biocarbon_fuel_substitution` for the national char pool *and* with
`bf_h2_injection` for the blast furnace's tuyere-injection headroom — the same
~40–50 % PCI substitution ceiling the library records in its own `key_constraints`. The
brief names `biochar_feedstock` as an example slug, so that is the one recorded, and
`bf_h2_injection` is left blank. **Question 2 below.**

---

## 4. `unit_eligibility.csv` (§3.5.1, data-migration C8)

2,612 rows over **125 of the 137 units**, all **55 activities** and **215 of the 230**
register `process_id`s.

| Column | Populated | Blank |
|---|---|---|
| `unit_id` | 2,612 | 0 |
| `carb3_activity` | 2,612 | 0 |
| `process_id` | 2,470 | **142** |
| `min_duty` | **15** | 2,597 |
| `max_share` | **4** | 2,608 |
| `earliest_year` | **9** | 2,603 |
| `provenance` | 2,612 | 0 |
| `notes` | 2,612 | 0 |
| `provenance_ref` | 2,612 | 0 |

### Where the rows come from

Sources are merged in descending order of evidence and deduplicated on
`(unit_id, carb3_activity, process_id)`; the first writer wins, so a worked-example row is
never overwritten by a derived one.

| Source | `provenance` | Rows |
|---|---|---|
| (a) the two worked examples' §1.11 tables, verbatim | `comit_reuse` | 40 |
| (b) `process_decarbonisation_options.csv`'s 1,109 mappings through the join | `bref` | 701 |
| (c) every register process whose duty family a service unit can serve, plus the chemistry nodes | `proxy` / `comit_reuse` | 1,871 |

(a) reproduces all 15 cement rows and all 18 food-and-drink rows exactly as written,
including the 15 `min_duty` values (0.15 ×3, 0.25 ×2, 0.30, 0.40, 0.50 and 1.20 Mt/yr of
clinker at the cement works; 0.01 ×2, 0.02, 0.03 ×2 and 0.25 PJ/yr at the food processing
centre), the four `max_share` values (0.55, 0.60, 0.35, and coal's 0.00) and the nine
`earliest_year` values (2035 ×7, plus one 2030 and one 2040). The cement table's *"(six electric processes)"* is expanded
against the register into `quarrying_crushing`, `raw_grinding_blending`,
`raw_meal_homogenisation`, `clinker_cooling`, `packing_dispatch` and `site_services` — the
nine Cement Works processes less the two chemistry nodes and `quarry_mobile_plant`, which is
diesel. That is why 15 + 18 rows become 40.

### `min_duty`, `max_share` and `earliest_year` are almost entirely blank, and that is the finding

**No published source in reach states a minimum viable plant size for any unit in
`unit.csv`.** Searched, and recorded rather than guessed:

- The options library's 134 `key_constraints`, `uk_status` and `trl_basis` fields were
  grepped for minimum-scale language. 27 rows mention scale; **not one states a minimum
  viable size**. The nearest is `electric_resistance_oven_furnace`'s "scale limits for
  all-electric melting (>600 t/d glass)", which is an *upper* limit, and glass has no unit.
- `process_decarbonisation_options.csv`'s `applicability` column is a maturity class
  (`commercial` / `demonstration` / `prospective` / `speculative`), not a year. Zero of its
  1,109 rows carry a future year in `notes` or `provenance`.
- The library carries exactly three availability statements, none usable: "commercial launch
  targeted before 2030" for rotodynamic heating (no electric kiln unit exists),
  "hydrogen ICE ... available ... by 2030" for NRMM (no NRMM unit exists), and TRL 9 for the
  electrode boiler (available now, so no `earliest_year`).
- A search of `gov.uk` and `theccc.org.uk` for a DESNZ/CCC minimum viable plant size across
  the Industrial Fuel Switching and Hydrogen Supply programmes returned programme
  evaluations and feasibility reports but **no threshold figure**. Nothing was taken from it.

So the 15 `min_duty`, 4 `max_share` and 9 `earliest_year` values in the file are the worked
examples' own numbers and nothing else. Per convention 1 that is correct, but it means
**data-migration C8's headline — "the minimum-scale screening thresholds that replace the
MILP binary" — is not yet satisfiable from any source this repository can reach.** The
thresholds that matter most, in rough order: CHP (`chp_*`, twelve units), electrolysers
(`electrolyser_*`), the capture trains (`ccs_*`), the anaerobic digester, and the cement and
lime kilns. Sourcing them is new research, not a data-migration exercise. **Question 3.**

### Judgement calls in the derivation

1. **Duty families are a proxy and are flagged as one.** `T17` (give every process a duty
   family and a heat grade) owns this and has not landed; neither
   `build/activity_process_duty_profile_duty_a.csv` nor `…_duty_b.csv` exists. All 230
   register `process_id`s were therefore classified by hand from the register's own
   `process_name` and `equipment_examples`, in the constant `PROCESS_FAMILIES`, and every
   row derived that way carries `provenance = proxy` and says so in `notes`. Six
   `process_id`s are **not** proxies because the two worked examples fix them outright:
   `site_services` → `SPC` + `MOT`, `boiler_steam_hot_water` → `LTH` + `STM`,
   `direct_heating` → `DRY`, `refrigeration` → `REF`, `machinery_motors` → `MOT`,
   `compressed_air` → `MOT`.
2. **A process may carry several families,** as §3.3's `duty_share` requires and as the
   food-and-drink example's §1.12 shows for `site_services`. 19 of the 230 do.
3. **No grade filter has been applied, because there is no grade to filter on.**
   §3.5's `grade_out` and `grade_in_max` are blank throughout `unit.csv` until the `units`
   lane's phase 2 (`PHASE1_units.md` says so explicitly), and no per-process heat grade
   exists either. Eligibility is therefore **family-only**. This over-offers: a `heat_pump_ht`
   capped at rank 3 is currently offered for a rank-4 dryer duty. Re-run this lane after
   phase 2 and after `T17`; the grade filter is four lines in `build_eligibility.py`.
4. **Chemistry units are offered only at their own node**, per `D5` (the split spine:
   chemistry is node-keyed, services family-keyed). A chemistry unit whose `process_id` does
   not match the row's process is skipped.
5. **Supply units get an activity-level row with a blank `process_id`**, exactly as both
   worked examples' tables have it (`pv_rooftop` and `battery_2h` with "—" for the process).
   142 rows. **This conflicts with §3.5.1, which makes `process_id` a required primary-key
   part with a foreign key to the register.** The worked examples are right and the schema is
   wrong: a PV array serves no process. Reported rather than papered over — **question 4**.
   `check_eligibility.py` permits the blank only for a service unit with no `duty_family`,
   which is exactly the supply and storage set, and fails on any other.
6. **Fuel plausibility was deliberately not used to prune.** Every unit of a family is
   offered for every process of that family, including `boiler_lt_coal` at a laboratory.
   Restricting eligibility to the fuels an activity burns *today* — which
   `activity_process_energy_profile.csv`'s `vector` column would have allowed — would forbid
   the fuel switching the whole model exists to find. The worked examples take the same line
   and cap rather than omit: the food-and-drink table lists `boiler_lt_coal` and gives it
   `max_share` 0.00. Caps were not invented anywhere the examples do not give one.
7. **Options-evidence beats the proxy where they disagree.** 356 rows come from a researcher
   mapping an option to a process whose proxy family does not match the unit's, the largest
   being 68 `LTH` units at `site_services` (welfare hot water, which the proxy `SPC` + `MOT`
   reading misses), 12 `LTH` at `process_heating` and 12 `SPC` at `steam_hot_water`. These
   rows were kept: a researcher's mapping is evidence and a process name is not. **The list
   is a direct input to `T17`** — it is 356 places where the register's wording under-states
   what the process actually does.

### Units, processes and activities with no row at all

**12 of 137 units get no eligibility row:**

- **Seven** are the chemistry rows `PHASE1_units.md` already flags as having no host in the
  register: `ammonia_smr_gas`, `ccs_amine_ammonia`, `dri_midrex_gas`, `ccs_amine_dri`,
  `glass_furnace_gas`, `glass_furnace_elec`, `glass_furnace_hydrogen`. Skipped per that
  file's instruction rather than landed on an invented host. Note that three of them —
  `ccs_amine_ammonia`, `ccs_amine_dri` and `dri_midrex_gas` — *would* have acquired rows
  through `post_combustion_amine_ccs` and `h2_dri_eaf` at whatever process those options are
  mapped to; the build guards against it explicitly.
- `non_energy_use_feedstock`: no register process was classified `NEUOTH`. Non-energy use is
  a fuel *destination*, not a process the register lists, so this may be correct rather than
  a gap — worth a ruling.
- `battery_4h`: only `battery_2h` is named by a worked example or reached by an option.
- `pv_battery_2h`, `pv_battery_4h`, `pv_battery_8h`: the `PD2` hybrids (the programme
  decision on how storage acquires a value) carry no `duty_family`, so the family derivation
  cannot reach them and no option maps to them. The other nine hybrids
  (`chp_thermal_store_*`, `electrolyser_battery_*`, `hp_thermal_store_*`) *do* carry a family
  and so are offered across it — an inconsistency in `unit.csv`, not here.

**13 register `process_id`s across 13 activities — 22 register rows — are diesel mobile
plant and get no row**, because `unit.csv` has no NRMM unit: `clay_extraction_mobile_plant`,
`digging_loading`, `drilling`, `extraction_loading`, `haulage`, `haulage_mobile_plant`,
`internal_haulage`, `materials_handling_loaders`, `mobile_crushing_screening`,
`mobile_plant`, `mobile_plant_trucks`, `quarry_mobile_plant`, `windrow_turning`. These
processes are not unmodelled demand — they are demand no unit can serve, so the LP cannot
satisfy their duty at all. **This is the most consequential single gap in the lane.**

**Four chemistry nodes have a register process and no unit:** `coke_ovens` and
`oven_battery_carbonisation` (Coking and Carbonising Plant, Iron and/or Steel Works),
`electrolysis_potlines` (Aluminium Smelting Works), and `lime_kiln` at Beet Sugar Factory —
the last is a naming mismatch rather than a missing unit, since the five `lime_kiln_*` units
key on `kiln_calcination`, not on `lime_kiln`. **That one is cheap to fix and worth fixing
in `unit.csv` or the register.**

---

## References

`references_eligibility.csv` adds **six** ids, all internal documents, and **no external
source** — nothing in this lane rests on an external citation, because no external source
was found that states a value this lane needed. `CARB3_SPEC_IMPL` is reproduced verbatim
from the `loadshape` lane's staging file so the coordinator can dedupe on `ref_id`; the
other five are new: `CARB3_WE_CEMENT`, `CARB3_WE_FOODDRINK`, `CARB3_OPT_LIB`,
`CARB3_UNIT_LIST`, `CARB3_REGISTER`. Each note states plainly that the id is an internal
pointer, not evidence. `references.csv` itself is untouched.

Every option-derived eligibility row cites `[CARB3_OPT_LIB]` and names the `option_id` that
put it there, so the underlying external evidence is one hop away in the library's own
`provenance` column, which already resolves into `references.csv`.

---

## Requests to other lanes

**To `units`** (§2 above is the full list): 17 missing units, headed by any NRMM unit, an
aluminium electrolysis cell, a vapour-recompression unit and an electric steam boiler. Two
smaller items: `lime_kiln` at Beet Sugar Factory needs either a unit or a register rename,
and the three `pv_battery_*` hybrids need a `duty_family` if they are to be reachable.

**To `carriers`**: eight carriers the `displaces` normalisation needed —
ammonia, biochar, raw biogas, HVO / bio-oil, petroleum coke, refinery fuel gas, marine gas
oil, bio-feedstock. Also a ruling on whether `crude_feedstock` and `fossil_feedstock` really
should resolve to `petroleum_products_misc`, which is how they are mapped today.

**To `duty_a` / `duty_b`**: the 230-entry `PROCESS_FAMILIES` constant in
`build_eligibility.py` is a complete first-pass duty-family classification of the register
and is yours to take, correct and supersede — it is a proxy, not a result. The 356
options-versus-proxy disagreements in §4.7 are the places to look first.

---

## Questions for Alexandre

1. **Where does a demand-side option live?** Thirteen library options — insulation, fabric,
   VAV controls, membrane pre-concentration, warm-mix asphalt — reduce a `process_duty`
   (§3.9) and change no unit coefficient, so `unit_eligibility` cannot express them and the
   optimiser cannot choose them. They are also among the cheapest abatement in the library.
   Does this need a `duty_modifier` entity, a multiplier on §3.3's `duty_share`, or is it
   deliberately out of scope for V1b?

2. **Should `exclusivity_group` be a column at all, or a table?** One option
   (`bf_biochar_injection`) already needs two groups — the national char pool and the blast
   furnace's tuyere headroom — and a single slug cannot carry both. A
   `decarbonisation_option_exclusivity(option_id, group_id)` table would, at the cost of one
   more file. I have kept the column the brief asked for and recorded the loss.

3. **`min_duty` has no source.** Data-migration C8 asks for the minimum-scale thresholds
   that replace the MILP binary, and after the search recorded in §4 I have 15 values, all of
   them the worked examples' own. Is commissioning that research a task in its own right, or
   should `A2` screen on something else until it exists?

4. **§3.5.1 makes `process_id` a required primary-key part, and both worked examples leave it
   blank for supply units.** I followed the examples. Should §3.5.1 be amended to make
   `process_id` nullable for units with no `duty_family`, or should supply units be pinned to
   a host process such as `site_services`?

5. **The data-migration document's items `C1`–`C8` collide with the spec's constraints
   `C1`–`C12`.** This brief and this file both had to disambiguate in prose every time. Worth
   renaming the data-migration letters — `M1`–`M8`, say — while only a handful of documents
   cite them?

6. **Is `non_energy_use_feedstock` reachable at all?** No register process is a non-energy
   use, so the unit gets no eligibility row. Is non-energy use meant to arrive through a
   process, or is it a premise-level carrier flow outside `unit_eligibility` entirely?
