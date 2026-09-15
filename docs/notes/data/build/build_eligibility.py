#!/usr/bin/env python3
"""Build the `eligibility` lane's three deliverables.

Stdlib only (pandas is not installed in this repo).

Outputs
-------
docs/notes/data/decarbonisation_option_unit.csv                     (C2)
docs/notes/data/build/decarbonisation_options_library_aligned.csv (C1, C3, C4)
docs/notes/data/unit_eligibility.csv                                (C8, spec 3.5.1)

Every judgement call made here is recorded in DONE_eligibility.md.
Run `check_eligibility.py` afterwards.
"""

import csv
import os
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.dirname(HERE)

# ---------------------------------------------------------------------------
# C1 — `displaces` free text -> carrier_id
#
# The token map is deliberately conservative: a token that names a duty
# ("kiln_fuel"), a material ("bitumen") or a substance carrier.csv does not
# carry ("petcoke", "refinery_fuel_gas") maps to nothing at all rather than to
# its nearest neighbour. Blanks are recorded as gaps in DONE_eligibility.md.
# ---------------------------------------------------------------------------
DISPLACES_TOKEN_MAP = {
    # --- gas -----------------------------------------------------------
    "gas": "natural_gas",
    "natural gas": "natural_gas",
    "natural_gas": "natural_gas",
    "natural gas (burners)": "natural_gas",
    "natural gas (cutting fuel)": "natural_gas",
    # --- oil -----------------------------------------------------------
    # "oil" is used for boiler/furnace oil and covers both carrier.csv grades.
    # The three mobile-plant options that mean diesel are overridden below.
    "oil": "light_fuel_oil;heavy_fuel_oil",
    "heating_oil": "light_fuel_oil",
    "diesel": "light_fuel_oil",
    "gasoil": "light_fuel_oil",
    "marine diesel/gas oil (auxiliary engines)": "light_fuel_oil",
    # --- solid fuel ----------------------------------------------------
    "coal": "coal",
    "anthracite": "coal",
    "pulverised coal (PCI)": "coal",
    "coking coal": "coking_coal",
    "coke": "coke",
    "foundry coke": "coke",
    "coke breeze": "coke",
    "coke oven gas (steam raising)": "coke_oven_gas",
    "waste_fuels": "waste_derived_fuel",
    # --- electricity and hydrogen --------------------------------------
    "electricity": "electricity",
    "grid electricity": "electricity",
    "grid_electricity": "electricity",
    "Hall-Heroult electrolysis electricity": "electricity",
    "grid hydrogen": "hydrogen",
    # --- lpg -----------------------------------------------------------
    "propane": "lpg",
    # --- emissions -----------------------------------------------------
    "process_co2": "co2_process",
    "carbon anodes (process CO2)": "co2_process",
    "process CO2 emissions (BF/BOF gas carbon)": "co2_process",
    # --- petroleum feedstock -------------------------------------------
    # carrier.csv's petroleum_products_misc is the non-energy-use petroleum
    # feedstock carrier (COMIT INDNEUMSC) and is what unit.csv's
    # non_energy_use_feedstock binds to.
    "crude_feedstock": "petroleum_products_misc",
    "fossil_feedstock": "petroleum_products_misc",
    # --- no carrier exists ---------------------------------------------
    "petcoke": "",                 # no petroleum-coke carrier
    "acetylene": "",               # no carrier
    "biogas": "",                  # only the upgraded form (biomethane) exists
    "petrol": "",                  # no carrier
    "refinery_fuel_gas": "",       # no carrier
    "f_gases": "",                 # not an energy carrier
    "fugitive_methane": "",        # not an energy carrier
    "purchased_co2": "",           # merchant CO2, not a modelled carrier
    "kiln_fuel": "",               # a duty, not a carrier
    "anode baking fuel": "",       # a duty, not a carrier
    "sinter": "",                  # a material
    "bitumen": "",                 # a material
    "virgin_aggregate": "",        # a material
    "chemicals": "",               # a material
}

# Options where the bare token "oil" means diesel for mobile plant, not
# boiler/furnace oil.
OIL_MEANS_DIESEL = {"battery_electric_nrmm", "hydrogen_nrmm", "hvo_bio_oils_dropin"}

# ---------------------------------------------------------------------------
# C2 — the option -> unit join.
#
# relationship:
#   is_unit      the option *is* this unit
#   enables      efficiency / heat recovery; changes a named unit coefficient
#   route_change whole-route replacement spanning several processes
#   supply       PV / battery / thermal store / AD / electrolyser supply side
#   none         no unit representation possible (the note says why)
#
# A blank unit_id is used, as the brief allows, where the row needs a unit
# that unit.csv does not carry; every one is listed in DONE_eligibility.md.
# ---------------------------------------------------------------------------
JOIN = OrderedDict([
    ("abattoir_byproduct_ad", [
        ("anaerobic_digester", "supply",
         "The option is an on-site digester on ABP/paunch feedstock; biogas fuels site boilers or CHP.")]),
    ("ad_chp_heat_integration", [
        ("anaerobic_digester", "enables",
         "Raises the share of CHP jacket/exhaust heat actually used, cutting anaerobic_digester's parasitic heat input coefficient (digester ~40C, pasteurisation ~70C).")]),
    ("ad_heat_pump_digester_heating", [
        ("heat_pump_lt_air", "is_unit",
         "Electric heat pump supplying 40-70C digester/pasteuriser heat is the LTH air-source heat pump unit.")]),
    ("air_to_air_hp_warm_air", [
        ("heat_pump_spc_air", "is_unit",
         "Air-to-air replacement of gas warm-air unit heaters is the SPC air-source heat pump unit.")]),
    ("alkali_activated_binder", [
        ("cement_lowcarbon_elec", "route_change",
         "Replaces Portland cement entirely, so the clinker kiln disappears: spans kiln_pyroprocessing and cement_grinding.")]),
    ("ammonia_industrial_fuel", [
        ("", "none",
         "GAP-CARRIER: carrier.csv has no ammonia carrier and unit.csv no ammonia-fired boiler or furnace.")]),
    ("ashp_space_heating_industrial", [
        ("heat_pump_spc_air", "is_unit",
         "Air-to-water heat pump on AHU coils and radiant panels is the SPC air-source heat pump unit.")]),
    ("battery_electric_nrmm", [
        ("", "none",
         "GAP-UNIT: unit.csv has no mobile-plant / NRMM unit, so no forklift, loader or yard-vehicle drivetrain can be represented.")]),
    ("bf_biochar_injection", [
        ("blast_furnace_coke", "enables",
         "Biogenic char substituted for PCI coal changes blast_furnace_coke's solid-fuel input coefficients. GAP-CARRIER: no biochar carrier exists.")]),
    ("bf_h2_injection", [
        ("blast_furnace_coke", "enables",
         "Tuyere hydrogen injection changes blast_furnace_coke's coal and hydrogen input coefficients.")]),
    ("bio_feedstock_co_processing", [
        ("refinery_fixed_mix_gas", "enables",
         "Co-processed biogenic feedstock changes the refinery unit's feedstock coefficient. GAP-CARRIER: no bio-feedstock carrier."),
        ("refinery_flexible_mix_gas", "enables",
         "As refinery_fixed_mix_gas: the feedstock coefficient changes, the process does not.")]),
    ("biocarbon_fuel_substitution", [
        ("sinter_plant_coke", "enables",
         "Biochar/biocoke for coke breeze changes sinter_plant_coke's solid-fuel input coefficient."),
        ("eaf_elec", "enables",
         "Biogenic charge and injection carbon changes eaf_elec's carbon input coefficient.")]),
    ("biogas_upgrading_grid_injection", [
        ("anaerobic_digester", "is_unit",
         "unit.csv's anaerobic_digester is specified 'with biogas upgrading' — this option is that unit.")]),
    ("biomass_boiler", [
        ("boiler_lt_biomass", "is_unit", "Steam and hot water to conventional boiler conditions."),
        ("boiler_spc_biomass", "is_unit", "The same plant serving a space-heat duty.")]),
    ("biomethane_fuel", [
        ("boiler_lt_biomethane", "is_unit", "Drop-in for a gas boiler duty, no equipment change."),
        ("chp_biomethane_ccgt", "is_unit",
         "Drop-in for a gas CHP duty. GAP-UNIT: no biomethane-fired kiln unit exists, so the kiln leg of this option is unrepresented.")]),
    ("building_fabric_upgrade", [
        ("", "none",
         "DEMAND-SIDE: insulation, air-tightness and glazing reduce the space-heat duty (3.9/3.3), not any unit coefficient.")]),
    ("calcined_clay_lc3", [
        ("grinder_mixer_clinker_sub_elec", "is_unit",
         "LC3 is a clinker-substitution grinding route; unit.csv's 'cement grinding with increased clinker substitution' is it.")]),
    ("calcium_looping_ccs", [
        ("kiln_calcium_looping_coal", "is_unit", "Cement calcium-looping kiln."),
        ("lime_kiln_calcium_looping_coal", "is_unit", "Lime calcium-looping kiln.")]),
    ("carbonated_manufactured_aggregate", [
        ("", "none",
         "OUT-OF-SET: manufactured aggregate from APCr plus CO2 is a product route outside the premise's process set; no unit converts between modelled carriers.")]),
    ("carbonation_curing_precast", [
        ("", "none",
         "GAP-UNIT: no CO2-curing chamber unit. The option displaces steam/heat curing, i.e. it removes a curing duty rather than changing a unit.")]),
    ("carbothermic_aluminium", [
        ("", "route_change",
         "GAP-UNIT: unit.csv carries no aluminium smelting unit at all (no electrolysis_potlines node), so the replacement route has nothing to replace.")]),
    ("clinker_substitution_scm", [
        ("grinder_mixer_clinker_sub_elec", "is_unit",
         "SCM and limestone substitution at the finish mill is the increased-clinker-substitution grinding unit.")]),
    ("co2_mineralised_concrete", [
        ("", "none",
         "OUT-OF-SET: CO2 injected into fresh concrete mix; concrete batching is not a process this option's hosts model as a carrier conversion.")]),
    ("cog_hydrogen_recovery", [
        ("", "none",
         "GAP-UNIT: no coke-oven-gas hydrogen separation unit (PSA/membrane) in the EN family.")]),
    ("coke_dry_quenching", [
        ("", "none",
         "GAP-UNIT: the host (coke oven battery / coke quenching) has no chemistry unit in unit.csv, so the recovered sensible heat has no unit to sit on.")]),
    ("compressed_air_optimisation", [
        ("motor_elec", "enables",
         "Cuts the compressor's specific power: motor_elec's electricity input coefficient on a compressed_air MOT duty.")]),
    ("controls_vsds", [
        ("motor_elec", "enables",
         "Same coefficient as compressed_air_optimisation, across motor, fan and pump duties.")]),
    ("cupola_to_induction", [
        ("furnace_ht_elec", "route_change",
         "Coke-fired cupola replaced by electric induction melting; named as a whole-route option in README_decarbonisation_options.md challenge 7.")]),
    ("dairy_membrane_preconcentration", [
        ("", "none",
         "DEMAND-SIDE: RO/NF removes water ahead of the evaporator, reducing the evaporation duty rather than changing a unit coefficient.")]),
    ("destratification_radiant_conversion", [
        ("", "none",
         "DEMAND-SIDE: reduces the space-heat duty in tall spaces.")]),
    ("diesel_electric_hybrid_mobile_crushing", [
        ("", "none",
         "GAP-UNIT: no mobile-plant / NRMM unit.")]),
    ("digestate_drying_chp_waste_heat", [
        ("anaerobic_digester", "enables",
         "Recovered engine heat dries digestate fibre, changing anaerobic_digester's heat balance; competes with ad_chp_heat_integration for the same heat.")]),
    ("direct_separation_leilac", [
        ("", "none",
         "GAP-UNIT: no indirectly heated (direct-separation) calciner among the kiln_* or lime_kiln_* units.")]),
    ("distillery_coproduct_ad", [
        ("anaerobic_digester", "supply",
         "On/near-site digester on distillery co-products.")]),
    ("dry_body_preparation_ceramics", [
        ("", "none",
         "DEMAND-SIDE: eliminates the spray-dryer thermal demand, i.e. removes a DRY duty.")]),
    ("eaf_scrap_preheating", [
        ("eaf_elec", "enables",
         "Off-gas scrap preheating cuts eaf_elec's electricity input coefficient.")]),
    ("eb_cure_coatings", [
        ("generic_process_elec", "is_unit",
         "Electron-beam cure is an electric process-energy service; OTH is the catch-all family and carries no EB-specific unit.")]),
    ("electric_infrared_drying", [
        ("dryer_electric", "is_unit", "Electric surface drying and curing is the electric dryer unit.")]),
    ("electric_kiln_calcination", [
        ("", "none",
         "GAP-UNIT: every kiln_* and lime_kiln_* unit is fossil-fired; there is no electric kiln or calciner node.")]),
    ("electric_powder_coating_oven", [
        ("dryer_electric", "is_unit",
         "Electric convection/IR cure oven at ~160-200C is a DRY duty served by the electric dryer unit.")]),
    ("electric_radiant_space_heating", [
        ("resistance_heater_spc", "is_unit", "Electric infrared spot/zone heating is the SPC resistance heater unit.")]),
    ("electric_resistance_oven_furnace", [
        ("furnace_ht_elec", "is_unit", "The >1000C end of the option's range."),
        ("resistance_heater_lt", "is_unit", "The ~100C end of the option's range.")]),
    ("electric_steam_cracker", [
        ("steam_cracker_elec", "is_unit", "Electric heating of olefin cracker furnaces.")]),
    ("electric_tissue_drying_hood", [
        ("paper_dryer_elec", "is_unit",
         "Electric hood and electric steam/heat-pump drying is the paper machine drying-section unit.")]),
    ("electric_tunnel_kiln_firing", [
        ("furnace_ht_elec", "is_unit",
         "Ceramic kiln firing at ~1000-1100C is modelled as an HTH duty; D5 puts no ceramic kiln in the chemistry spine.")]),
    ("electrified_reforming_esmr", [
        ("", "none",
         "GAP-UNIT: the EN family carries smr_gas_ccs and atr_gas_ccs only; no electrified reformer.")]),
    ("electrified_static_processing_plant", [
        ("motor_elec", "route_change",
         "Diesel mobile crushing/screening replaced by fixed electric plant: the duty moves from an unrepresented NRMM machine to a MOT duty on motor_elec.")]),
    ("electrochemical_synthesis_routes", [
        ("", "route_change",
         "GAP-UNIT: no electrochemical synthesis node in the chemistry spine.")]),
    ("electrode_boiler", [
        ("resistance_heater_lt", "is_unit",
         "GAP-UNIT: unit.csv has no electrode boiler. resistance_heater_lt is the nearest LTH electric unit; the STM family has no electric boiler at all, so the steam duty of this option is unrepresented.")]),
    ("electrolytic_hydrogen_refinery_integration", [
        ("electrolyser_pem", "is_unit", "On-site electrolytic hydrogen."),
        ("electrolyser_alkaline", "is_unit", "On-site electrolytic hydrogen, alkaline stack.")]),
    ("ev_fleet_charging_infrastructure", [
        ("", "none",
         "OUT-OF-SET: vehicle charging; README_decarbonisation_options.md challenge 10 records that the benefit accrues outside the site boundary.")]),
    ("fab_low_grade_heat_recovery", [
        ("heat_pump_lt_reject", "is_unit",
         "Recovering process cooling water heat to a useful LTH duty is the reject-heat heat pump unit.")]),
    ("fast_firing_low_thermal_mass_kilns", [
        ("", "none",
         "DEMAND-SIDE: cuts specific firing energy; with no ceramic kiln unit there is no coefficient to carry it.")]),
    ("fermentation_co2_recovery", [
        ("", "none",
         "GAP-UNIT: no capture unit on a fermentation host, and carrier.csv defines co2_captured as CO2 leaving to the transport network, not merchant CO2 for reuse.")]),
    ("fume_cupboard_vav_sash_management", [
        ("", "none",
         "DEMAND-SIDE: reduces the laboratory ventilation duty.")]),
    ("gas_compression_electric_drive", [
        ("motor_elec", "is_unit",
         "Electric motor-driven export/process compression is a MOT duty on motor_elec.")]),
    ("grid_electric_drilling_rig", [
        ("", "none",
         "GAP-UNIT: no mobile-plant / genset unit.")]),
    ("h2_boiler", [
        ("boiler_lt_hydrogen", "is_unit", "Hydrogen steam and hot-water boiler."),
        ("boiler_spc_hydrogen", "is_unit", "The same plant serving a space-heat duty.")]),
    ("h2_dri_eaf", [
        ("dri_midrex_gas", "route_change",
         "GAP-UNIT: no hydrogen shaft-furnace unit; dri_midrex_gas is the gas-based analogue. The route spans coke_ovens, sinter_plant, blast_furnace_ironmaking and bof_steelmaking."),
        ("eaf_elec", "route_change",
         "The melting leg of the H2-DRI + EAF route.")]),
    ("h2_kiln_furnace_burner", [
        ("furnace_ht_hydrogen", "is_unit", "Hydrogen firing of furnaces and kilns above ~400C."),
        ("dryer_direct_hydrogen", "is_unit", "Hydrogen firing of direct-fired dryers from ~200C.")]),
    ("h2_ready_equipment", [
        ("", "none",
         "NOT-A-UNIT: a procurement attribute. It changes when a hydrogen unit becomes eligible (unit_eligibility.earliest_year), not what is built.")]),
    ("hbi_dri_charging_eaf", [
        ("eaf_elec", "enables",
         "Merchant DRI/HBI in the charge changes eaf_elec's charge and electricity coefficients.")]),
    ("heat_pump_above_200", [
        ("", "none",
         "GAP-UNIT: no heat pump unit above 200C; heat_pump_ht is the highest and it is an STM unit below that.")]),
    ("heat_pump_below_100", [
        ("heat_pump_lt_air", "is_unit", "Ambient-source low-temperature heat pump."),
        ("heat_pump_lt_reject", "is_unit", "The same duty served from recovered reject heat.")]),
    ("heat_recovery_heat_pump", [
        ("heat_pump_lt_reject", "is_unit",
         "Upgrading 20-70C waste heat to 60-150C is exactly the reject-heat heat pump unit.")]),
    ("hisarna_smelting_reduction", [
        ("hisarna_coal", "route_change",
         "Direct smelting of ore fines, eliminating coke_ovens and sinter_plant as well as replacing blast_furnace_ironmaking.")]),
    ("htp_heat_pump_100_150", [
        ("heat_pump_ht", "is_unit", "The high-temperature (steam) heat pump unit.")]),
    ("htp_heat_pump_150_200", [
        ("", "none",
         "GAP-UNIT: no 150-200C heat pump unit.")]),
    ("hvo_bio_oils_dropin", [
        ("", "none",
         "GAP-CARRIER and GAP-UNIT: no HVO/bio-oil carrier in carrier.csv, and no mobile-plant unit for the engine duty.")]),
    ("hydrogen_fuel_cell_haul_truck", [
        ("", "none", "GAP-UNIT: no mobile-plant / NRMM unit.")]),
    ("hydrogen_nrmm", [
        ("", "none", "GAP-UNIT: no mobile-plant / NRMM unit.")]),
    ("impingement_tad_drying_conversion", [
        ("paper_dryer_elec", "enables",
         "Raises the drying rate of the paper machine dryer section: changes paper_dryer_elec's energy coefficient.")]),
    ("increased_rap_content", [
        ("", "none",
         "OUT-OF-SET: recycled asphalt planings cut embodied carbon of binder and aggregate, which is outside the premise's carrier balance.")]),
    ("induction_heating", [
        ("furnace_ht_elec", "is_unit", "Induction heating and melting of conductive metals is the electric HTH furnace unit.")]),
    ("inert_anode_smelting", [
        ("", "route_change",
         "GAP-UNIT: no aluminium electrolysis unit; the option spans electrolysis_potlines and anode_production_baking.")]),
    ("insulation_upgrade", [
        ("", "none",
         "DEMAND-SIDE: cuts standing losses on steam systems, tanks and furnaces, i.e. the duty.")]),
    ("inverter_welding_equipment", [
        ("generic_process_elec", "enables",
         "Inverter power sources cut welding-set conversion losses: the electricity input coefficient of the OTH electric service unit.")]),
    ("ipcc_in_pit_crushing_conveying", [
        ("motor_elec", "route_change",
         "Diesel truck haulage from face to plant replaced by an in-pit crusher and electric conveyors: the haulage duty moves to a MOT duty.")]),
    ("iron_ore_electrowinning", [
        ("", "route_change",
         "GAP-UNIT: no electrowinning node in the chemistry spine; the route replaces coke_ovens, sinter_plant and blast_furnace_ironmaking.")]),
    ("kiln_dryer_cascade_heat_recovery", [
        ("", "none",
         "ARCHITECTURAL: kiln cooling-zone air feeding a dryer is a reject-heat coefficient (data migration B5) plus the C10 (heat grade cascade) constraint, not a unit.")]),
    ("kiln_net_zero_fuel_mix_h2_biomass", [
        ("", "none",
         "GAP-UNIT: kiln_* units are coal, gas, waste-derived fuel and oil only; there is no hydrogen or biomass cement kiln for a net-zero main-burner mix.")]),
    ("lab_air_change_reduction_dcv", [
        ("", "none", "DEMAND-SIDE: reduces the laboratory ventilation duty.")]),
    ("lab_exhaust_heat_recovery", [
        ("", "none",
         "ARCHITECTURAL: run-around coil recovery on 100% outside-air ventilation is a reject-heat coefficient (B5) plus C10, not a unit.")]),
    ("lab_led_lighting_controls", [
        ("", "none",
         "DEMAND-SIDE and GAP-UNIT: reduces the lighting duty, and unit.csv has no lighting unit.")]),
    ("led_high_bay_lighting", [
        ("", "none",
         "DEMAND-SIDE and GAP-UNIT: reduces the lighting duty, and unit.csv has no lighting unit.")]),
    ("led_uv_curing", [
        ("generic_process_elec", "is_unit",
         "Instant-cure LED-UV replacing gas heatset/IR dryers is an electric OTH service.")]),
    ("lime_oxyfuel_flash_calcination", [
        ("ccs_oxyfuel_lime", "is_unit",
         "Flash calcination with a concentrated capture-ready CO2 stream is the lime oxyfuel unit.")]),
    ("low_bake_paint_chemistry", [
        ("", "none", "DEMAND-SIDE: reformulated coatings reduce the cure-oven duty.")]),
    ("low_gwp_process_gas_substitution", [
        ("", "none",
         "OUT-OF-SET: F-gases are not carriers and their emissions are neither co2_process nor a fuel CO2 carrier.")]),
    ("low_temperature_tanning_chemistry", [
        ("", "none", "DEMAND-SIDE: reduces the hot-water and drying duty.")]),
    ("malting_kiln_heat_pump", [
        ("dryer_heat_pump", "is_unit",
         "Recovering latent heat from humid kiln exhaust to supply 60-90C kiln air is the heat-pump dryer unit.")]),
    ("microwave_assisted_ceramic_firing", [
        ("furnace_ht_elec", "enables",
         "Hybrid microwave plus conventional heating cuts the HTH unit's energy coefficient per unit of firing.")]),
    ("microwave_rf_drying", [
        ("dryer_electric", "is_unit", "Volumetric dielectric drying is an electric dryer.")]),
    ("minewater_heat_pump_recovery", [
        ("heat_pump_lt_reject", "is_unit",
         "Upgrading 15-20C minewater heat is the reject-heat heat pump unit. README challenge 10 records that the heat usually serves an off-site offtaker.")]),
    ("molten_oxide_electrolysis", [
        ("", "route_change",
         "GAP-UNIT: no molten oxide electrolysis node; the route replaces coke_ovens, sinter_plant, blast_furnace_ironmaking and bof_steelmaking.")]),
    ("mvr", [
        ("", "none",
         "GAP-UNIT: no mechanical vapour recompression unit. heat_pump_ht is not a substitute — MVR compresses the process vapour itself and its effective COP is an order of magnitude higher.")]),
    ("natural_refrigerant_refrigeration", [
        ("chiller_electric_hfo", "is_unit",
         "unit.csv's advanced (HFO) refrigeration plant is the nearest unit; ammonia and transcritical CO2 plant are not separately represented.")]),
    ("ohmic_heating_food", [
        ("generic_process_elec", "is_unit",
         "Direct volumetric electric heating of pumpable product is an electric OTH service.")]),
    ("onsite_solar_pv", [
        ("pv_rooftop", "supply", "Rooftop array."),
        ("pv_ground_mount", "supply", "Ground-mounted array where land is available.")]),
    ("oxyfuel_ccs", [
        ("ccs_oxyfuel", "is_unit", "Full oxyfuel capture on a cement kiln."),
        ("ccs_oxyfuel_partial", "is_unit", "Partial oxyfuel capture on a cement kiln."),
        ("ccs_oxyfuel_lime", "is_unit", "Full oxyfuel capture on a lime kiln.")]),
    ("paint_shop_heat_recovery", [
        ("", "none",
         "ARCHITECTURAL: cure-oven exhaust recovery and heat wheels are reject-heat coefficients (B5) plus C10, not a unit.")]),
    ("pfc_point_of_use_abatement", [
        ("", "none",
         "OUT-OF-SET: PFC/NF3/SF6 abatement; these are not carriers in carrier.csv.")]),
    ("plasma_electric_cutting", [
        ("generic_process_elec", "is_unit",
         "Electric plasma arc and laser cutting replacing oxy-fuel torches is an electric OTH service.")]),
    ("plasma_torch_heating", [
        ("furnace_ht_elec", "is_unit",
         "Very-high-temperature electric heat; furnace_ht_elec is the HTH family's only electric member.")]),
    ("plug_in_electric_mobile_crushing_screening", [
        ("", "none", "GAP-UNIT: no mobile-plant / NRMM unit.")]),
    ("post_combustion_amine_ccs", [
        ("ccs_amine", "is_unit", "MEA amine train on a cement kiln."),
        ("ccs_amine_mdea", "is_unit", "Advanced MDEA amine train on a cement kiln."),
        ("ccs_amine_coal_chp", "is_unit", "MEA amine train with coal CHP on a cement kiln."),
        ("ccs_amine_lime", "is_unit", "MEA amine train on a lime kiln."),
        ("ccs_amine_hvc_gas", "is_unit", "Amine train on a steam cracker, gas reboiler."),
        ("ccs_amine_hvc_biomass", "is_unit", "Amine train on a steam cracker, biomass co-firing."),
        ("ccs_amine_hvc_elec", "is_unit", "Amine train on an electric steam cracker."),
        ("ccs_amine_ammonia", "is_unit", "Amine train on an ammonia steam reformer."),
        ("ccs_amine_ironmaking", "is_unit", "Amine train on ironmaking."),
        ("ccs_amine_dri", "is_unit", "Amine train on direct reduced iron.")]),
    ("processless_ctp_plates", [
        ("", "none",
         "DEMAND-SIDE: eliminates plate-processor energy, water and chemistry in platemaking.")]),
    ("quarry_floating_solar_storage", [
        ("pv_ground_mount", "supply", "Array on quarry land and silt lagoons."),
        ("battery_2h", "supply", "The storage leg that supplies plant and charges electric mobile equipment.")]),
    ("recycled_cement_clinker_cec", [
        ("cement_lowcarbon_elec", "route_change",
         "Electric cement: hydrated cement from demolition waste reactivated as a slag/clinker substitute in a steel EAF, so the clinker kiln leg disappears.")]),
    ("refinery_low_carbon_hydrogen_fuel_switch", [
        ("", "none",
         "GAP-UNIT: the PHEAT family carries refinery_process_heat_gas only; there is no hydrogen-fired refinery process-heat unit.")]),
    ("refinery_process_heater_electrification", [
        ("", "none",
         "GAP-UNIT: the PHEAT family carries refinery_process_heat_gas only; there is no electric refinery process-heat unit.")]),
    ("rotating_packed_bed_intensification", [
        ("", "none",
         "DEMAND-SIDE: process intensification cuts the separation duty; no intensification unit exists.")]),
    ("rotodynamic_electric_heater", [
        ("furnace_ht_elec", "is_unit",
         "Turbomachinery electric heating of process air/material above 1000C; the HTH electric member.")]),
    ("shoe_press_advanced_dewatering", [
        ("paper_press_elec", "enables",
         "Raising post-press solids cuts the downstream paper_dryer_elec steam coefficient; the capex sits on paper_press_elec.")]),
    ("shore_power_cold_ironing", [
        ("", "none",
         "GAP-UNIT and GAP-CARRIER: vessel auxiliary power at berth has no unit, and marine gas oil has no carrier.")]),
    ("solar_thermal_process_heat", [
        ("solar_thermal_flat", "supply",
         "Flat-plate collector to ~100C; evacuated-tube and advanced designs are not separately represented.")]),
    ("sortation_regen_drives", [
        ("motor_elec", "enables",
         "Regenerative VSDs and IE4/IE5 motors cut motor_elec's electricity input coefficient.")]),
    ("steel_offgas_ccu_ethanol", [
        ("", "none",
         "OUT-OF-SET: gas fermentation to ethanol; no CCU unit and no ethanol carrier.")]),
    ("still_tvr_thermocompression", [
        ("", "none",
         "GAP-UNIT: no thermal vapour recompression unit; see mvr.")]),
    ("superheated_steam_drying", [
        ("", "none",
         "GAP-UNIT: dryer_steam is a conventional steam-heated dryer. Superheated steam drying recovers the evaporated water's latent heat, which is a materially different coefficient set.")]),
    ("superheated_steam_drying_paper", [
        ("", "none",
         "GAP-UNIT: as superheated_steam_drying, on a paper machine; paper_dryer_elec cannot carry near-total latent heat recovery.")]),
    ("tethered_electric_excavator", [
        ("", "none", "GAP-UNIT: no mobile-plant / NRMM unit.")]),
    ("tgr_bf_ccs", [
        ("tgr_blast_furnace_coke", "is_unit", "The top-gas-recovery blast furnace itself."),
        ("ccs_amine_ironmaking", "is_unit", "The capture train on the recovered top gas.")]),
    ("thermal_storage_power_to_heat", [
        ("thermal_store_steam", "supply", "Discharging steam."),
        ("thermal_store_hot_water", "supply", "Discharging hot water.")]),
    ("trolley_assist_haul_trucks", [
        ("", "none", "GAP-UNIT: no mobile-plant / NRMM unit.")]),
    ("ult_freezer_optimisation", [
        ("chiller_electric", "enables",
         "Setpoints, maintenance and efficient replacement cut chiller_electric's electricity input coefficient on the REF duty.")]),
    ("uv_cure_coatings", [
        ("generic_process_elec", "is_unit",
         "UV cure replacing thermally-baked coatings is an electric OTH service.")]),
    ("vam_thermal_oxidation", [
        ("", "none",
         "OUT-OF-SET: ventilation-air methane is a fugitive emission, not a carrier, and methane emissions are not in the carrier set.")]),
    ("warm_mix_asphalt", [
        ("", "none",
         "DEMAND-SIDE: a lower mixing temperature reduces the aggregate drying and heating duty.")]),
    ("waste_derived_fuels", [
        ("kiln_dry_wdf", "is_unit", "Dry preheater cement kiln on waste-derived fuel."),
        ("kiln_fluidbed_wdf", "is_unit", "Fluidised-bed cement kiln with waste utilisation."),
        ("lime_kiln_dry_wdf", "is_unit", "Dry lime kiln on waste-derived fuel."),
        ("lime_kiln_fluidbed_wdf", "is_unit", "Fluidised-bed lime kiln with waste utilisation.")]),
    ("waste_heat_recovery_process", [
        ("", "none",
         "ARCHITECTURAL: flue-gas and process heat recovery is the reject-heat coefficient set (B5) plus the C10 cascade. The upgrade path that does have a unit is heat_recovery_heat_pump.")]),
    ("wetted_drained_cathode", [
        ("", "none",
         "GAP-UNIT: no aluminium electrolysis unit to carry a cell-voltage coefficient.")]),
    ("wort_vapour_energy_recovery", [
        ("", "none",
         "GAP-UNIT: wort kettle vapour recompression; see mvr.")]),
    ("zeolite_adsorption_drying", [
        ("", "none",
         "GAP-UNIT: no sorption dryer unit. dryer_heat_pump is not a substitute — the sorbent regeneration duty is a different coefficient set.")]),
])

# ---------------------------------------------------------------------------
# C4 — exclusivity groups.
#
# The test applied: would the LP's own algebra already stop these options being
# taken together?  Where two options resolve to the same unit, or compete for
# one duty through C1 (duty satisfaction), no group is needed.  A group is set
# only where addition is otherwise unchecked: a shared feedstock or heat
# stream, a whole-route choice, or options that carry no unit at all.
# ---------------------------------------------------------------------------
EXCLUSIVITY = {
    "ad_biogas_use": [
        "ad_chp_heat_integration", "ad_heat_pump_digester_heating",
        "biogas_upgrading_grid_injection", "digestate_drying_chp_waste_heat"],
    "biochar_feedstock": ["bf_biochar_injection", "biocarbon_fuel_substitution"],
    "clinker_substitution": [
        "clinker_substitution_scm", "calcined_clay_lc3",
        "alkali_activated_binder", "recycled_cement_clinker_cec"],
    "flue_gas_capture": [
        "post_combustion_amine_ccs", "oxyfuel_ccs", "calcium_looping_ccs",
        "direct_separation_leilac", "lime_oxyfuel_flash_calcination"],
    "primary_ironmaking_route": [
        "h2_dri_eaf", "hisarna_smelting_reduction", "molten_oxide_electrolysis",
        "iron_ore_electrowinning", "tgr_bf_ccs"],
    "aluminium_cell_route": ["carbothermic_aluminium", "inert_anode_smelting"],
    "vapour_recompression": [
        "mvr", "still_tvr_thermocompression", "wort_vapour_energy_recovery"],
    "paper_drying_route": [
        "superheated_steam_drying_paper", "impingement_tad_drying_conversion",
        "electric_tissue_drying_hood"],
    "coating_cure_route": [
        "uv_cure_coatings", "eb_cure_coatings", "low_bake_paint_chemistry",
        "electric_powder_coating_oven"],
    "ceramic_firing_route": [
        "electric_tunnel_kiln_firing", "microwave_assisted_ceramic_firing",
        "fast_firing_low_thermal_mass_kilns"],
    "space_heat_conversion": [
        "ashp_space_heating_industrial", "air_to_air_hp_warm_air",
        "electric_radiant_space_heating"],
    "nrmm_traction": [
        "battery_electric_nrmm", "hydrogen_nrmm", "hvo_bio_oils_dropin",
        "tethered_electric_excavator", "hydrogen_fuel_cell_haul_truck",
        "trolley_assist_haul_trucks", "grid_electric_drilling_rig"],
    "mobile_crusher_drive": [
        "diesel_electric_hybrid_mobile_crushing",
        "plug_in_electric_mobile_crushing_screening",
        "electrified_static_processing_plant", "ipcc_in_pit_crushing_conveying"],
    "lab_ventilation_reduction": [
        "fume_cupboard_vav_sash_management", "lab_air_change_reduction_dcv"],
    "refinery_process_heat_route": [
        "refinery_low_carbon_hydrogen_fuel_switch",
        "refinery_process_heater_electrification"],
    "concrete_co2_utilisation": [
        "co2_mineralised_concrete", "carbonation_curing_precast",
        "carbonated_manufactured_aggregate"],
}

# ---------------------------------------------------------------------------
# Proxy duty families per register process_id.
#
# T17 (give every process a duty family and a heat grade) owns this properly
# and has not landed; neither build/activity_process_duty_profile_duty_a.csv
# nor _duty_b.csv exists.  Every family here is therefore derived from the
# register's own process_name and equipment_examples and is flagged
# provenance = proxy, except the six process_ids the two worked examples fix.
#
# CHEMISTRY  the process is a chemistry node; unit.csv's chemistry rows key on
#            it directly and no service unit is offered.
# NRMM       diesel mobile plant; unit.csv has no unit for it at all.
# ---------------------------------------------------------------------------
CHEMISTRY = "CHEMISTRY"
NRMM = "NRMM"

PROCESS_FAMILIES = {
    "aeration_odour_control": ["MOT"],
    "aeration_treatment": ["MOT"],
    "aggregate_drying_heating": ["DRY"],
    "aggregate_handling": ["MOT"],
    "aggregate_handling_conveying": ["MOT"],
    "alkylation": ["PHEAT"],
    "alumina_materials_handling": ["MOT"],
    "anode_production_baking": ["HTH"],
    "artificial_lift": ["MOT"],
    "batching_mixing": ["MOT"],
    "beet_reception_preparation": ["MOT"],
    "biscuit_firing": ["HTH"],
    "bitumen_storage_heating": ["LTH"],
    "blast_furnace_ironmaking": [CHEMISTRY],
    "block_machine_pressing": ["MOT"],
    "bof_steelmaking": [CHEMISTRY],
    "boiler_steam_hot_water": ["LTH", "STM"],
    "brewhouse": ["STM", "MOT"],
    "brine_purification": ["MOT"],
    "brine_well_pumping": ["MOT"],
    "bulk_gases_cda": ["MOT"],
    "byproduct_plant": ["MOT"],
    "cast_house": ["HTH"],
    "catalytic_reforming": ["PHEAT"],
    "cement_grinding": [CHEMISTRY],
    "centrifuging": ["MOT"],
    "charge_handling": ["MOT"],
    "chilled_water_plant": ["REF"],
    "chip_drying": ["DRY"],
    "cip_hot_water": ["LTH"],
    "cip_utilities": ["LTH"],
    "clay_extraction_mobile_plant": [NRMM],
    "clay_preparation": ["MOT"],
    "cleanroom_hvac": ["SPC", "MOT"],
    "clinker_cooling": ["MOT"],
    "coal_handling_preparation": ["MOT"],
    "coal_preparation": ["MOT"],
    "coating_finishing": ["DRY"],
    "coke_ovens": [CHEMISTRY],
    "coke_quenching_handling": ["MOT"],
    "cold_feed_conveying": ["MOT"],
    "compressed_air": ["MOT"],
    "continuous_casting": ["MOT"],
    "continuous_distillation": ["STM"],
    "conveying": ["MOT"],
    "cooking_conversion": ["STM"],
    "cooling_systems": ["REF"],
    "coproduct_evaporation": ["STM"],
    "coproduct_evaporation_drying": ["DRY", "STM"],
    "core_making": ["DRY"],
    "cranes_material_handling": ["MOT"],
    "crude_vacuum_distillation": [CHEMISTRY],
    "crushing": ["MOT"],
    "crystallisation_sugar_house": ["STM", "MOT"],
    "cubing_packaging": ["MOT"],
    "curing": ["STM"],
    "curing_chambers": ["LTH"],
    "curing_kilns": ["STM"],
    "depalletting_packaging": ["MOT"],
    "dewatering_pumping": ["MOT"],
    "digestate_processing": ["MOT"],
    "digester_mixing_pumping": ["MOT"],
    "digging_loading": [NRMM],
    "direct_heating": ["DRY"],
    "distillation": ["STM"],
    "distillation_separation": ["STM"],
    "dosing_sludge_handling": ["MOT"],
    "drawing_texturing": ["OTH"],
    "drilling": [NRMM],
    "dry_dock_services": ["MOT"],
    "drying": ["DRY"],
    "drying_grading": ["DRY"],
    "dust_extraction": ["MOT"],
    "eaf_melting": [CHEMISTRY],
    "effluent_treatment": ["MOT"],
    "effluent_water_services": ["MOT"],
    "electrochemical_processes": ["OTH"],
    "electrolysis_potlines": [CHEMISTRY],
    "evaporation": ["STM"],
    "evaporation_drying": ["DRY", "STM"],
    "exhaust_abatement": ["OTH"],
    "exhaust_baghouse": ["MOT"],
    "extraction_diffusion": ["LTH", "MOT"],
    "extraction_loading": [NRMM],
    "extrusion_pressing": ["MOT"],
    "fcc": ["PHEAT"],
    "fettling_finishing": ["MOT"],
    "finishing": ["MOT"],
    "floor_germination_turning": ["MOT"],
    "flour_packing_handling": ["MOT"],
    "forming": ["MOT"],
    "forming_casting_vibration": ["MOT"],
    "fume_extraction": ["MOT"],
    "fume_extraction_auxiliaries": ["MOT"],
    "gas_compression": ["MOT"],
    "germination_vessels": ["MOT"],
    "glazing_decoration": ["MOT"],
    "glost_decoration_firing": ["HTH"],
    "grain_handling_dressing": ["MOT"],
    "grain_intake_milling": ["MOT"],
    "grinding": ["MOT"],
    "grinding_roller_mills": ["MOT"],
    "haulage": [NRMM],
    "haulage_mobile_plant": [NRMM],
    "heat_treatment": ["HTH"],
    "heat_treatment_pasteurisation": ["LTH"],
    "hot_rolling": ["HRS"],
    "hot_rolling_mill": ["HRS"],
    "hot_water_sterilisation_cleaning": ["LTH"],
    "hvac_ventilation": ["SPC", "MOT"],
    "hydration": ["MOT"],
    "hydrocracking": ["PHEAT"],
    "hydrogen_production": ["EN"],
    "hydrotreating": ["PHEAT"],
    "internal_haulage": [NRMM],
    "kiln_calcination": [CHEMISTRY],
    "kiln_fans": ["MOT"],
    "kiln_firing": ["HTH"],
    "kiln_pyroprocessing": [CHEMISTRY],
    "kilning_heat": ["DRY"],
    "lab_equipment": ["OTH"],
    "leather_drying": ["DRY"],
    "lighting": ["OTH"],
    "lime_grinding_milling": [CHEMISTRY],
    "lime_kiln": [CHEMISTRY],
    "loadout_storage": ["MOT"],
    "machine_drive": ["MOT"],
    "machinery_motors": ["MOT"],
    "machining_metalworking": ["MOT"],
    "machining_outfitting": ["MOT"],
    "mailroom_finishing": ["MOT"],
    "material_handling": ["MOT"],
    "materials_handling": ["MOT"],
    "materials_handling_conveyors": ["MOT"],
    "materials_handling_loaders": [NRMM],
    "melting_holding": ["HTH"],
    "metal_forming": ["MOT"],
    "milling_grinding": ["MOT"],
    "milling_mashing": ["STM", "MOT"],
    "minewater_pumping": ["MOT"],
    "mixing_batching": ["MOT"],
    "mobile_crushing_screening": [NRMM],
    "mobile_plant": [NRMM],
    "mobile_plant_trucks": [NRMM],
    "mould_making": ["MOT"],
    "other_process": ["OTH"],
    "other_units": ["PHEAT"],
    "oven_battery_carbonisation": [CHEMISTRY],
    "packaging": ["MOT", "LTH"],
    "packing_dispatch": ["MOT"],
    "paint_shop": ["DRY", "MOT"],
    "painting_coating": ["DRY"],
    "paper_machine_drying": [CHEMISTRY],
    "paper_machine_wet_end": [CHEMISTRY],
    "pasteurisation_digester_heating": ["LTH"],
    "pelleting_press": ["MOT"],
    "pneumatic_conveying_aspiration": ["MOT"],
    "polymer_melt_extrusion": ["HTH", "MOT"],
    "pouring_casting": ["MOT"],
    "power_generation": ["STM"],
    "prepress_platemaking": ["OTH"],
    "press_auxiliaries": ["MOT"],
    "press_drives": ["MOT"],
    "process_cooling": ["REF"],
    "process_drums_machinery": ["MOT"],
    "process_float_heating": ["LTH"],
    "process_heating": ["HTH", "DRY", "STM"],
    "process_heating_drying": ["DRY"],
    "process_heating_regeneration": ["HTH"],
    "process_machine_drives": ["MOT"],
    "process_pumps_motors": ["MOT"],
    "process_tools": ["MOT"],
    "processing_machinery_pumping": ["MOT"],
    "processing_separation_export": ["MOT"],
    "pulp_pressing_drying": ["DRY"],
    "quarry_mobile_plant": [NRMM],
    "quarrying_crushing": ["MOT"],
    "quarrying_crushing_screening": ["MOT"],
    "raw_grinding_blending": ["MOT"],
    "raw_material_preparation": ["MOT", "DRY"],
    "raw_meal_homogenisation": ["MOT"],
    "reaction_heating": [CHEMISTRY],
    "reception_depackaging_shredding": ["MOT"],
    "refrigeration": ["REF"],
    "refrigeration_attemperation": ["REF"],
    "refrigeration_chilling": ["REF"],
    "reheat_furnaces": ["HTH"],
    "scalding_singeing": ["LTH"],
    "scrap_handling_preparation": ["MOT"],
    "screening": ["MOT"],
    "screening_mixing": ["MOT"],
    "screening_refining": ["MOT"],
    "secondary_metallurgy": ["HTH"],
    "setting_handling": ["MOT"],
    "shakeout_sand_reclamation": ["MOT"],
    "shaping_extrusion": ["MOT"],
    "shearing_baling": ["MOT"],
    "shredding_separation": ["MOT"],
    "sifting_purification": ["MOT"],
    "sinter_plant": [CHEMISTRY],
    "site_services": ["SPC", "MOT"],
    "slaughter_line_processing": ["MOT"],
    "sortation_machinery": ["MOT"],
    "space_heating": ["SPC"],
    "space_water_heating": ["SPC", "LTH"],
    "spinning_hvac": ["SPC", "MOT"],
    "spinning_quench_winding": ["MOT"],
    "steam_conditioning": ["STM"],
    "steam_hot_water": ["STM", "LTH"],
    "steel_prep_cutting": ["MOT", "OTH"],
    "steeping": ["MOT"],
    "stock_preparation": [CHEMISTRY],
    "stripping_handling_cranes": ["MOT"],
    "surface_prep_blasting": ["MOT"],
    "surface_treatment": ["OTH"],
    "torch_cutting": ["OTH"],
    "ultrapure_water": ["MOT"],
    "utilities_steam": ["STM"],
    "vacuum_evaporation": ["STM"],
    "ventilation": ["MOT"],
    "washing_classification": ["MOT"],
    "water_aggregate_heating": ["LTH"],
    "water_heating": ["LTH"],
    "water_injection": ["MOT"],
    "water_supply_pumping": ["MOT"],
    "welding": ["OTH"],
    "welding_fabrication": ["OTH"],
    "wheat_cleaning_conditioning": ["MOT"],
    "windrow_turning": [NRMM],
    "workshop_equipment": ["MOT"],
}

# The six process_ids the worked examples fix outright; these are not proxies.
WORKED_EXAMPLE_FAMILIES = {
    "site_services", "boiler_steam_hot_water", "direct_heating",
    "refrigeration", "machinery_motors", "compressed_air",
}

# ---------------------------------------------------------------------------
# Worked-example unit_eligibility rows, reproduced verbatim (3.5.1).
# (unit_id, carb3_activity, process_id, min_duty, max_share, earliest_year)
# ---------------------------------------------------------------------------
CEMENT_ELECTRIC_PROCESSES = [
    "quarrying_crushing", "raw_grinding_blending", "raw_meal_homogenisation",
    "clinker_cooling", "packing_dispatch", "site_services",
]

WORKED_EXAMPLE_ROWS = []


def _we(unit, activity, process, min_duty="", max_share="", earliest="", ref="", note=""):
    WORKED_EXAMPLE_ROWS.append(
        (unit, activity, process, min_duty, max_share, earliest, ref, note))


_CEM = "CARB3_WE_CEMENT"
_CEM_NOTE = "Reproduced verbatim from the cement worked example 1.11 unit_eligibility table."
for _u, _md, _ms, _ey in [
    ("kiln_dry_coal", "0.15", "", ""),
    ("kiln_dry_gas", "0.15", "", ""),
    ("kiln_dry_wdf", "0.15", "0.55", ""),
    ("kiln_fluidbed_wdf", "0.40", "", ""),
    ("kiln_calcium_looping_coal", "1.20", "", "2035"),
    ("ccs_amine", "0.25", "", "2035"),
    ("ccs_amine_mdea", "0.25", "", "2035"),
    ("ccs_oxyfuel", "0.50", "", "2040"),
    ("ccs_oxyfuel_partial", "0.30", "", "2035"),
]:
    _we(_u, "Cement Works", "kiln_pyroprocessing", _md, _ms, _ey, _CEM,
        _CEM_NOTE + " min_duty in Mt/yr of clinker.")
for _u, _ms, _ey in [
    ("grinder_mixer_elec", "", ""),
    ("grinder_mixer_clinker_sub_elec", "0.60", ""),
    ("cement_lowcarbon_elec", "0.35", "2035"),
]:
    _we(_u, "Cement Works", "cement_grinding", "", _ms, _ey, _CEM, _CEM_NOTE)
for _p in CEMENT_ELECTRIC_PROCESSES:
    _we("motor_elec", "Cement Works", _p, "", "", "", _CEM,
        _CEM_NOTE + " The table's '(six electric processes)' expanded against "
        "activity_process_register.csv: the nine Cement Works processes less "
        "kiln_pyroprocessing and cement_grinding (chemistry) and quarry_mobile_plant (diesel).")
_we("pv_rooftop", "Cement Works", "", "", "", "", _CEM,
    _CEM_NOTE + " process_id blank as the table has it: a supply unit serves no process.")
_we("battery_2h", "Cement Works", "", "", "", "", _CEM,
    _CEM_NOTE + " process_id blank as the table has it: a supply unit serves no process.")

_FD = "CARB3_WE_FOODDRINK"
_FD_NOTE = "Reproduced verbatim from the food and drink worked example 1.11 unit_eligibility table."
for _u, _md, _ms, _ey in [
    ("boiler_lt_gas", "", "", ""),
    ("boiler_lt_hydrogen", "", "", "2035"),
    ("boiler_lt_biomass", "", "", ""),
    ("boiler_lt_lpg", "", "", ""),
    ("boiler_lt_coal", "", "0.00", ""),
    ("resistance_heater_lt", "", "", ""),
    ("heat_pump_lt_air", "0.01", "", ""),
    ("heat_pump_lt_reject", "0.01", "", ""),
    ("heat_pump_ht", "0.02", "", "2030"),
    ("chp_gas_turbine", "0.03", "", ""),
    ("chp_hydrogen_ccgt", "0.03", "", "2035"),
    ("chp_biomass_st", "0.25", "", ""),
]:
    _we(_u, "Food Processing Centre", "boiler_steam_hot_water", _md, _ms, _ey, _FD,
        _FD_NOTE + " min_duty in PJ/yr.")
_we("dryer_direct_gas", "Food Processing Centre", "direct_heating", "", "", "", _FD, _FD_NOTE)
_we("dryer_electric", "Food Processing Centre", "direct_heating", "", "", "", _FD, _FD_NOTE)
_we("chiller_electric", "Food Processing Centre", "refrigeration", "", "", "", _FD, _FD_NOTE)
for _p in ["machinery_motors", "compressed_air", "site_services"]:
    _we("motor_elec", "Food Processing Centre", _p, "", "", "", _FD, _FD_NOTE)
_we("pv_rooftop", "Food Processing Centre", "", "", "", "", _FD,
    _FD_NOTE + " process_id blank as the table has it.")
_we("battery_2h", "Food Processing Centre", "", "", "", "", _FD,
    _FD_NOTE + " process_id blank as the table has it.")


# ---------------------------------------------------------------------------
def read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    library = read("decarbonisation_options_library.csv")
    units = read("unit.csv")
    carriers = read("carrier.csv")
    register = read("activity_process_register.csv")
    mappings = read("process_decarbonisation_options.csv")

    unit_by_id = {u["unit_id"]: u for u in units}
    carrier_ids = {c["carrier_id"] for c in carriers}

    # -- deliverable 1: decarbonisation_option_unit.csv ---------------------
    join_rows = []
    for opt in library:
        oid = opt["option_id"]
        if oid not in JOIN:
            raise SystemExit("option %s has no join entry" % oid)
        for unit_id, rel, note in JOIN[oid]:
            if unit_id and unit_id not in unit_by_id:
                raise SystemExit("join names unknown unit %s" % unit_id)
            join_rows.append({
                "option_id": oid,
                "unit_id": unit_id,
                "relationship": rel,
                "notes": note,
                "provenance": "[CARB3_OPT_LIB] decarbonisation_options_library.csv row '%s'"
                              " (option_class, displaces, duty, uk_status) read against"
                              " [CARB3_UNIT_LIST] unit.csv and [CARB3_SPEC_IMPL] 3.5" % oid,
                "confidence": "high" if rel in ("is_unit", "supply") else "medium",
            })
    with open(os.path.join(DATA, "decarbonisation_option_unit.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "option_id", "unit_id", "relationship", "notes", "provenance", "confidence"])
        w.writeheader()
        w.writerows(join_rows)

    # -- deliverable 2: the aligned library --------------------------------
    opt_group = {}
    for slug, members in EXCLUSIVITY.items():
        for m in members:
            if m in opt_group:
                raise SystemExit("%s is in two exclusivity groups" % m)
            opt_group[m] = slug

    route_change_options = {r["option_id"] for r in join_rows
                            if r["relationship"] == "route_change"}

    fieldnames = list(library[0].keys()) + [
        "displaces_carrier_ids", "route_change", "exclusivity_group"]
    unmapped_tokens = defaultdict(set)
    aligned = []
    for opt in library:
        oid = opt["option_id"]
        ids = []
        for tok in (t.strip() for t in opt["displaces"].split(";")):
            if not tok:
                continue
            if tok not in DISPLACES_TOKEN_MAP:
                raise SystemExit("unmapped displaces token %r" % tok)
            mapped = DISPLACES_TOKEN_MAP[tok]
            if tok == "oil" and oid in OIL_MEANS_DIESEL:
                mapped = "light_fuel_oil"
            if not mapped:
                unmapped_tokens[tok].add(oid)
                continue
            for cid in mapped.split(";"):
                if cid not in carrier_ids:
                    raise SystemExit("token %r maps to unknown carrier %r" % (tok, cid))
                if cid not in ids:
                    ids.append(cid)
        row = dict(opt)
        row["displaces_carrier_ids"] = ";".join(ids)
        row["route_change"] = "TRUE" if oid in route_change_options else "FALSE"
        row["exclusivity_group"] = opt_group.get(oid, "")
        aligned.append(row)
    with open(os.path.join(HERE, "decarbonisation_options_library_aligned.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(aligned)

    # -- deliverable 3: unit_eligibility.csv -------------------------------
    units_by_family = defaultdict(list)
    for u in units:
        if u["spine"] == "service" and u["duty_family"]:
            units_by_family[u["duty_family"]].append(u["unit_id"])
    units_by_node = defaultdict(list)
    for u in units:
        if u["spine"] == "chemistry" and u["process_id"]:
            units_by_node[u["process_id"]].append(u["unit_id"])

    # rows keyed on (unit_id, activity, process_id); first write wins, and the
    # sources are visited in descending order of evidence.
    rows = OrderedDict()

    def put(unit_id, activity, process_id, min_duty, max_share, earliest,
            provenance, ref, note):
        key = (unit_id, activity, process_id)
        if key in rows:
            return False
        rows[key] = {
            "unit_id": unit_id,
            "carb3_activity": activity,
            "process_id": process_id,
            "min_duty": min_duty,
            "max_share": max_share,
            "earliest_year": earliest,
            "provenance": provenance,
            "notes": note,
            "provenance_ref": "[%s]" % ref,
        }
        return True

    # (a) the worked examples, verbatim
    n_a = 0
    for unit, activity, process, md, ms, ey, ref, note in WORKED_EXAMPLE_ROWS:
        if put(unit, activity, process, md, ms, ey, "comit_reuse", ref, note):
            n_a += 1

    # (b) the option mappings, through the join
    is_unit_map = defaultdict(list)
    supply_map = defaultdict(list)
    for r in join_rows:
        if not r["unit_id"]:
            continue
        if r["relationship"] in ("is_unit", "route_change"):
            is_unit_map[r["option_id"]].append(r["unit_id"])
        elif r["relationship"] == "supply":
            supply_map[r["option_id"]].append(r["unit_id"])

    n_b = 0
    unplaceable_chemistry = set()
    supply_seen = set()
    for m in mappings:
        act, proc, oid = m["carb3_activity"], m["process_id"], m["option_id"]
        note = ("Offered because %s maps this option to (%s, %s) in "
                "process_decarbonisation_options.csv; the option resolves to this unit "
                "in decarbonisation_option_unit.csv." % (oid, act, proc))
        for unit_id in is_unit_map.get(oid, []):
            u = unit_by_id[unit_id]
            if u["spine"] == "chemistry" and u["process_id"] != proc:
                # A chemistry unit only serves its own node (D5).  The seven
                # chemistry units PHASE1_units.md lists with a blank process_id
                # have no host in the register, so they are skipped here too
                # rather than being landed on whatever process the option maps
                # to; they are listed in DONE_eligibility.md.
                if not u["process_id"]:
                    unplaceable_chemistry.add(unit_id)
                continue
            if put(unit_id, act, proc, "", "", "", "bref", "CARB3_OPT_LIB", note):
                n_b += 1
        for unit_id in supply_map.get(oid, []):
            if (unit_id, act) in supply_seen:
                continue
            supply_seen.add((unit_id, act))
            if put(unit_id, act, "", "", "", "", "bref", "CARB3_OPT_LIB",
                   "Supply-side unit, offered at activity level: %s maps it to this "
                   "activity in process_decarbonisation_options.csv. process_id is blank "
                   "because a supply unit serves no single process, as both worked "
                   "examples' tables have it." % oid):
                n_b += 1

    # (c) every register process the unit's duty family can serve
    n_c = 0
    unknown_processes = set()
    chemistry_gaps = defaultdict(set)
    nrmm_gaps = defaultdict(set)
    for r in register:
        act, proc = r["carb3_activity"], r["process_id"]
        fams = PROCESS_FAMILIES.get(proc)
        if fams is None:
            unknown_processes.add(proc)
            continue
        for fam in fams:
            if fam == NRMM:
                nrmm_gaps[proc].add(act)
                continue
            if fam == CHEMISTRY:
                cand = units_by_node.get(proc, [])
                if not cand:
                    chemistry_gaps[proc].add(act)
                for unit_id in cand:
                    if put(unit_id, act, proc, "", "", "", "comit_reuse",
                           "CARB3_UNIT_LIST",
                           "Chemistry-spine unit keyed on process_id '%s' in unit.csv "
                           "(D5: chemistry is node-keyed)." % proc):
                        n_c += 1
                continue
            for unit_id in units_by_family.get(fam, []):
                src = ("the worked examples" if proc in WORKED_EXAMPLE_FAMILIES
                       else "the register's process_name and equipment_examples")
                if put(unit_id, act, proc, "", "", "", "proxy", "CARB3_REGISTER",
                       "Service unit of duty family %s, offered for every register process "
                       "of that family. Family derived from %s: T17 (give every process a "
                       "duty family and a heat grade) has not landed and neither "
                       "build/activity_process_duty_profile_duty_a.csv nor _duty_b.csv "
                       "exists, so this is a proxy. unit.grade_out is blank until the units "
                       "lane's phase 2, so no grade filter has been applied."
                       % (fam, src)):
                    n_c += 1

    if unknown_processes:
        raise SystemExit("register processes with no duty family: %s"
                         % sorted(unknown_processes))

    with open(os.path.join(DATA, "unit_eligibility.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "unit_id", "carb3_activity", "process_id", "min_duty", "max_share",
            "earliest_year", "provenance", "notes", "provenance_ref"])
        w.writeheader()
        for key in sorted(rows):
            w.writerow(rows[key])

    print("decarbonisation_option_unit.csv          %4d rows, %d options"
          % (len(join_rows), len(JOIN)))
    print("decarbonisation_options_library_aligned  %4d rows" % len(aligned))
    print("unit_eligibility.csv                     %4d rows "
          "(worked example %d, options join %d, family %d)"
          % (len(rows), n_a, n_b, n_c))
    print("displaces tokens with no carrier: %s"
          % ", ".join("%s (%d options)" % (t, len(v))
                      for t, v in sorted(unmapped_tokens.items())))
    print("chemistry nodes with no unit: %s"
          % ", ".join("%s (%d activities)" % (p, len(a))
                      for p, a in sorted(chemistry_gaps.items())))
    print("NRMM processes with no unit: %d process_ids, %d register rows"
          % (len(nrmm_gaps), sum(len(a) for a in nrmm_gaps.values())))
    print("chemistry units with no register host, skipped: %s"
          % ", ".join(sorted(unplaceable_chemistry)))


if __name__ == "__main__":
    main()
