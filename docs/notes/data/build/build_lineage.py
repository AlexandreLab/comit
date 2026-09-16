#!/usr/bin/env python3
"""Build docs/notes/data/comit_technology_lineage.csv (lane `lineage`, T8, migration A1-A3 / B1-B2).

One row per technology in emissions_source_classification.csv (397), reconciled against
unit.csv. This is a reconciliation, not research: every assignment is derived from a source
field of the 397-row classification, from unit.csv's own provenance_ref (which names the
COMIT technology_code each unit was built from), or from an override table below whose
justification is written into the row's `reason`.

Stdlib only -- pandas is not installed in this repo.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.dirname(HERE)

ESC = os.path.join(DATA, "emissions_source_classification.csv")
UNIT = os.path.join(DATA, "unit.csv")
CARRIER = os.path.join(DATA, "carrier.csv")
OUT = os.path.join(DATA, "comit_technology_lineage.csv")

COLUMNS = [
    "technology_code", "technology_name", "sector", "technology_category",
    "output_commodity", "carrier_id", "unit_type", "abatement",
    "disposition", "unit_id", "fuel_carrier_id", "reason", "notes",
]

# --- A1: technology_category -> fuel carrier -------------------------------------------
# The seven fuel values of technology_category map straight onto carrier.csv. `Heat pump`
# is a device whose fuel is electricity. `Steam` is COMIT's heat-from-CHP commodity, which
# carrier.csv represents as six graded heat bands; the source row does not state a grade,
# so per convention 1 the carrier is left blank rather than guessed. `CCS`, `Standard_FF`
# and `Dry kiln` are not fuels at all and are resolved per row (A2, A3) below.
CATEGORY_CARRIER = {
    "Electricity": "electricity",
    "Natural gas": "natural_gas",
    "Hydrogen": "hydrogen",
    "Biomass": "solid_biomass",
    "Oil": "lpg",
    "Coal": "coal",
    "Heat pump": "electricity",
    "Steam": "",
    "CCS": None,
    "Standard_FF": None,
    "Dry kiln": None,
}

SECTOR_PREFIXES = [
    "ICM", "ICR", "ICH", "ICN", "IEE", "IFD", "IGL", "IIS",
    "ILM", "IME", "INF", "IOI", "IPP", "IPR", "ITX", "IVH",
]

# --- the service spine: (duty family, technology_category) -> unit_id --------------------
# Every service unit below is the D13 collapse of one (duty, fuel) pair across COMIT's
# per-sector copies. Confirmed against unit.csv provenance_ref, which names a sample of the
# sector copies for each ("n=9 sector copies, median taken").
SERVICE = {
    ("LTH", "Natural gas"): "boiler_lt_gas",
    ("LTH", "Hydrogen"): "boiler_lt_hydrogen",
    ("LTH", "Biomass"): "boiler_lt_biomass",
    ("LTH", "Oil"): "boiler_lt_lpg",
    ("LTH", "Coal"): "boiler_lt_coal",
    ("LTH", "Electricity"): "resistance_heater_lt",
    ("LTH", "Heat pump"): "heat_pump_lt_air",
    ("LTH", "Steam"): "heat_exchanger_lt_steam",
    ("SPC", "Natural gas"): "boiler_spc_gas",
    ("SPC", "Hydrogen"): "boiler_spc_hydrogen",
    ("SPC", "Biomass"): "boiler_spc_biomass",
    ("SPC", "Oil"): "boiler_spc_lpg",
    ("SPC", "Coal"): "boiler_spc_coal",
    ("SPC", "Electricity"): "resistance_heater_spc",
    ("SPC", "Heat pump"): "heat_pump_spc_air",
    ("SPC", "Steam"): "heat_exchanger_spc_steam",
    ("HTH", "Natural gas"): "furnace_ht_gas",
    ("HTH", "Hydrogen"): "furnace_ht_hydrogen",
    ("HTH", "Biomass"): "furnace_ht_biomass",
    ("HTH", "Oil"): "furnace_ht_lpg",
    ("HTH", "Coal"): "furnace_ht_coal",
    ("HTH", "Electricity"): "furnace_ht_elec",
    ("DRY", "Natural gas"): "dryer_direct_gas",
    ("DRY", "Hydrogen"): "dryer_direct_hydrogen",
    ("DRY", "Biomass"): "dryer_direct_biomass",
    ("DRY", "Oil"): "dryer_direct_lpg",
    ("DRY", "Coal"): "dryer_direct_coal",
    ("DRY", "Electricity"): "dryer_electric",
    ("DRY", "Heat pump"): "dryer_heat_pump",
    ("DRY", "Steam"): "dryer_steam",
    ("OTH", "Natural gas"): "generic_process_gas",
    ("OTH", "Hydrogen"): "generic_process_hydrogen",
    ("OTH", "Biomass"): "generic_process_biomass",
    ("OTH", "Oil"): "generic_process_lpg",
    ("OTH", "Coal"): "generic_process_coal",
    ("OTH", "Electricity"): "generic_process_elec",
    ("OTH", "Steam"): "generic_process_steam",
    ("MOT", "Electricity"): "motor_elec",
    ("REF", "Electricity"): "chiller_electric",
    ("STM", "Heat pump"): "heat_pump_ht",
}

# device kind per duty family, for the rows the SERVICE table resolves
SERVICE_UNIT_TYPE = {
    ("LTH", "Electricity"): "resistance_heater",
    ("LTH", "Heat pump"): "heat_pump",
    ("LTH", "Steam"): "heat_exchanger",
    ("SPC", "Electricity"): "resistance_heater",
    ("SPC", "Heat pump"): "heat_pump",
    ("SPC", "Steam"): "heat_exchanger",
    ("DRY", "Heat pump"): "heat_pump",
    ("STM", "Heat pump"): "heat_pump",
}
DUTY_UNIT_TYPE = {
    "LTH": "boiler", "SPC": "boiler", "HTH": "furnace", "DRY": "dryer",
    "OTH": "generic_process", "MOT": "motor", "REF": "chiller",
}

# --- per-code overrides ------------------------------------------------------------------
# (unit_id, unit_type, carrier_id, reason). unit_id None => unmapped; "" => dropped.
# Every chemistry-node row, every CCS row, every hydrogen-production row, and every
# Standard_FF row that A2 must resolve by reading the name and emitting_fuel_commodities.
O = {}


def ov(code, unit_id, unit_type, carrier_id, reason, notes=""):
    O[code] = (unit_id, unit_type, carrier_id, reason, notes)


# A3 -- the single `Dry kiln` row. D13 split it into four fuel-specific cement kiln units.
# The cement worked example instantiates it as kiln_dry_coal (unit.csv provenance_ref
# for kiln_dry_coal opens `[CARB3_WE_CEMENT] 1.11 unit table`), which is the tie-break.
ov("ICMKLND01", "kiln_dry_coal", "kiln", "coal",
   "A3: category `Dry kiln` is a device, not a fuel. Name is 'Dry kiln, best available "
   "technology (BAT)' and emitting_fuel_commodities lists seven fuels "
   "(IND_NGABOM;INDCOA;INDDISTELC;INDHFO;INDLFO;INDMSWINO;INDMSWORG), so the source row is "
   "multi-fuel. D13 splits it into four single-fuel cement kiln units; unit_id names the one "
   "the cement worked example instantiates.",
   "d13_fan_out=kiln_dry_coal;kiln_dry_gas;kiln_dry_wdf;kiln_dry_oil")

# The lime twin of the same kiln, which COMIT files under Standard_FF rather than Dry kiln.
# No worked example uses it, so the tie-break is COMIT's own emitting_fuel_commodities
# ordering, whose first entry is IND_NGABOM.
ov("ILMKLND01", "lime_kiln_dry_gas", "kiln", "natural_gas",
   "A2: `Standard_FF` on a multi-fuel lime kiln. Same seven-fuel emitting list as ICMKLND01. "
   "D13 splits it into three single-fuel lime kiln units; unit_id names the first fuel in "
   "emitting_fuel_commodities (IND_NGABOM -> natural_gas) because no worked example covers lime.",
   "d13_fan_out=lime_kiln_dry_gas;lime_kiln_dry_coal;lime_kiln_dry_wdf")

# Cement / lime chemistry, non-CCS
ov("ICMKLNWST02", "kiln_fluidbed_wdf", "kiln", "waste_derived_fuel",
   "A2: `Standard_FF` resolved from the name ('Fluidised bed kiln with waste utilisation') "
   "and INDMSWINO in emitting_fuel_commodities -> waste_derived_fuel.")
ov("ILMKLNWST02", "lime_kiln_fluidbed_wdf", "kiln", "waste_derived_fuel",
   "A2: as ICMKLNWST02, lime twin.")
ov("ICMLOCARB01", "cement_lowcarbon_elec", "grinder", "electricity",
   "A2: `Standard_FF` on 'Alternative low carbon cement'. The unit is a grinding/blending "
   "step; unit.csv gives cement_lowcarbon_elec fuel_carrier_id=electricity.")
ov("ILMLOCARB01", "lime_lowcarbon_elec", "grinder", "electricity",
   "A2: as ICMLOCARB01, lime twin.")
ov("ICMGRIMIX01", "grinder_mixer_elec", "grinder", "electricity", "Chemistry node, cement grinding.")
ov("ICMGRIMIX02", "grinder_mixer_clinker_sub_elec", "grinder", "electricity",
   "Chemistry node, cement grinding with increased clinker substitution.")
ov("ILMGRIMIX01", "lime_grinder_elec", "grinder", "electricity", "Chemistry node, lime grinding.")
ov("ILMGRIMIX02", "lime_grinder_sub_elec", "grinder", "electricity",
   "Chemistry node, lime grinding with increased substitution.")

# CCS -- cement
ov("ICMKLNCLQ01", "kiln_calcium_looping_coal", "kiln", "coal",
   "CCS category. Calcium looping is integrated capture, so unit.csv keeps it a converter "
   "kiln rather than a bolt-on abatement unit.")
ov("ICMKLNMNQ01", "ccs_amine", "kiln", "natural_gas",
   "CCS category. MEA train on a dry kiln with a natural gas CHP -> the train's own fuel is gas.")
ov("ICMKLNMAQ02", "ccs_amine_mdea", "kiln", "natural_gas",
   "CCS category. Advanced amine (MDEA) train; unit.csv gives fuel_carrier_id=natural_gas.")
ov("ICMKLNMCQ01", "ccs_amine_coal_chp", "kiln", "coal",
   "CCS category. MEA train on a dry kiln with a coal CHP -> the train's own fuel is coal.")
ov("ICMKLNOXQ01", "ccs_oxyfuel", "kiln", "electricity",
   "CCS category. Full oxyfuel; the added load is the air separation unit, so electricity.")
ov("ICMKLNPOQ01", "ccs_oxyfuel_partial", "kiln", "electricity",
   "CCS category. Partial oxyfuel; as ICMKLNOXQ01.")

# CCS -- lime
ov("ILMKLNCLQ01", "lime_kiln_calcium_looping_coal", "kiln", "coal", "CCS category, lime twin of ICMKLNCLQ01.")
ov("ILMKLNMNQ01", "ccs_amine_lime", "kiln", "natural_gas", "CCS category, lime twin of ICMKLNMNQ01.")
ov("ILMKLNOXQ01", "ccs_oxyfuel_lime", "kiln", "electricity", "CCS category, lime twin of ICMKLNOXQ01.")
ov("ILMKLNMAQ02", None, "kiln", "natural_gas",
   "CCS category. unit.csv has no lime MDEA train (the cement ccs_amine_mdea is cement-specific "
   "by process_id kiln_pyroprocessing). Requested in DONE_lineage.md.")
ov("ILMKLNMCQ01", None, "kiln", "coal",
   "CCS category. unit.csv has no lime coal-CHP MEA train. Requested in DONE_lineage.md.")
ov("ILMKLNPOQ01", None, "kiln", "electricity",
   "CCS category. unit.csv has no lime partial-oxyfuel train. Requested in DONE_lineage.md.")

# CCS -- chemicals
ov("ICHAMMSRQ01", "ccs_amine_ammonia", "reformer", "natural_gas",
   "CCS category. Steam reformer with CCS for ammonia; abates_unit_id resolves to ammonia_smr_gas.")
ov("ICHHVCSCQG01", "ccs_amine_hvc_gas", "cracker", "natural_gas", "CCS category, natural gas reboiler.")
ov("ICHHVCSCQB01", "ccs_amine_hvc_biomass", "cracker", "wood_pellets",
   "CCS category. INDPELL in emitting_fuel_commodities -> wood_pellets, matching unit.csv.")
ov("ICHHVCSCQE01", "ccs_amine_hvc_elec", "cracker", "electricity", "CCS category, electric steam cracker.")
ov("ICHHVCSCQH01", None, "cracker", "natural_gas",
   "CCS category. 'post-combustion CCS using excess heat' -- a distinct reboiler heat source. "
   "unit.csv has no excess-heat variant; folding it into ccs_amine_hvc_gas would assert a gas "
   "reboiler the source denies. Requested in DONE_lineage.md.")
ov("ICHHVCSCQN01", None, "cracker", "natural_gas",
   "CCS category. 'post-combustion CCS with NGCC' -- reboiler steam from a gas CCGT rather than "
   "a gas boiler. unit.csv has no NGCC variant. Requested in DONE_lineage.md.")

# CCS -- iron & steel
ov("IISHISARQ01", "ccs_amine_ironmaking", "blast_furnace", "coal",
   "CCS category. unit.csv names both IISHISARQ01 and IISTGRBFQ01 in ccs_amine_ironmaking's "
   "provenance_ref, so two source rows share one unit.")
ov("IISTGRBFQ01", "ccs_amine_ironmaking", "blast_furnace", "coke",
   "CCS category. Shares ccs_amine_ironmaking with IISHISARQ01 per that unit's provenance_ref.")
ov("IISULCOREDQ01", "ccs_amine_dri", "dri_shaft", "natural_gas",
   "CCS category. ULCORED direct reduced iron with CCS; abates_unit_id resolves to dri_midrex_gas.")

# CCS -- hydrogen production. These are site units in CaRB3 (duty family EN), not
# out-of-scope supply-side rows.
ov("PHYGNGALQ01", "smr_gas_ccs", "reformer", "natural_gas",
   "CCS category. Hydrogen production, EN duty family. emitting_fuel_commodities is empty and the "
   "row is classed A_pure_process: the reformer's natural gas is feedstock, so its carbon books as "
   "process CO2 (65.95 kt/unit). The carrier comes from the name and from unit.csv's binding.",
   "emitting_fuel_commodities is empty because the feedstock carbon is in process_co2_kt_per_unit")
ov("PHYGNGALQ02", "atr_gas_ccs", "reformer", "natural_gas",
   "CCS category. Hydrogen production, EN duty family. As PHYGNGALQ01: A_pure_process, and "
   "emitting_fuel_commodities lists only INDDISTELC (the auxiliary electricity), not the gas "
   "feedstock whose carbon is in process_co2_kt_per_unit (56.59 kt/unit).",
   "emitting_fuel_commodities omits the gas feedstock; its carbon is in process_co2_kt_per_unit")
ov("PHYGBPELQ01", "gasifier_biomass_ccs", "gasifier", "wood_pellets",
   "CCS category. INDPELL -> wood_pellets, matching unit.csv.")
ov("PHYGCOAQ01", "gasifier_coal_ccs", "gasifier", "coal",
   "CCS category. emitting_fuel_commodities says INDMAINSGAS, not coal, but that is not a "
   "conflict: a gasifier's feedstock carbon books as process CO2 (109.32 kt/unit here), so the "
   "coal never appears as an emitting fuel, and the mains gas is a real auxiliary burner "
   "(5.64 kt/unit direct). The headline fuel is the feedstock, which unit.csv binds as coal.",
   "emitting_fuel_commodities names combustion fuels only; this unit's feedstock carbon is in "
   "process_co2_kt_per_unit")

# Hydrogen production -- electrolysis
ov("PHYGEYALSL01", "electrolyser_alkaline", "electrolyser", "electricity", "Hydrogen production, EN duty family.")
ov("PHYGEYSL01", "electrolyser_pem", "electrolyser", "electricity", "Hydrogen production, EN duty family.")
ov("PHYGEYSOEL01", "electrolyser_soec", "electrolyser", "electricity", "Hydrogen production, EN duty family.")

# Chemicals chemistry nodes
ov("ICHAMMSRS01", "ammonia_smr_gas", "reformer", "natural_gas", "Chemistry node, ammonia steam reforming.")
ov("ICHHVCSCE01", "steam_cracker_gas", "cracker", "natural_gas",
   "A2: `Natural gas` category on the generic HVC production technology -> steam_cracker_gas.")
ov("ICHHVCSCN01", "steam_cracker_naphtha", "cracker", "petroleum_products_misc",
   "A1: category `Oil` here means naphtha feedstock, not LPG; unit.csv binds "
   "petroleum_products_misc.")
ov("ICHHVCSCO01", "steam_cracker_byproduct", "cracker", "petroleum_products_misc",
   "A2: `Standard_FF` on 'Oil byproduct catalytic cracker' -> petroleum_products_misc, "
   "matching unit.csv.")
ov("ICHHVCSCELEC01", "steam_cracker_elec", "cracker", "electricity", "Chemistry node, electric steam cracker.")
ov("ICHHVCSCHYD01", "steam_cracker_hydrogen", "cracker", "hydrogen", "Chemistry node, hydrogen fuel switch in HVC.")
ov("ICHNEUOTH01", "non_energy_use_feedstock", "feedstock", "petroleum_products_misc",
   "A2: `Standard_FF` on the residual non-energy fuel use process. unit.csv binds "
   "petroleum_products_misc (COMIT commodity INDNEUMSC).")
ov("ICHREFEHFO01", "chiller_electric_hfo", "chiller", "electricity",
   "Advanced refrigeration with HFO refrigerant -- a distinct unit from chiller_electric "
   "because the refrigerant changes the non-CO2 emission, not the fuel.")

# Iron & steel chemistry nodes
ov("IISBLAFUR01", "blast_furnace_coke", "blast_furnace", "coke",
   "A2: `Standard_FF` on 'Blast furnace, standard'. emitting_fuel_commodities carries INDCOK "
   "and INDCOACOK; unit.csv binds coke.")
ov("IISTGRBF01", "tgr_blast_furnace_coke", "blast_furnace", "coke",
   "A2: `Standard_FF` on the top-gas recovery blast furnace; INDCOK present, unit.csv binds coke.")
ov("IISHISAR01", "hisarna_coal", "blast_furnace", "coal",
   "A2: `Standard_FF` on HISarna, which is a coal-direct smelter; INDCOA present and unit.csv "
   "binds coal (no INDCOK, unlike the blast furnaces).")
ov("IISBOXFUR01", "bof_converter_cog", "bof_converter", "coke_oven_gas",
   "A2: `Standard_FF` on the basic oxygen furnace; INDCOG present, unit.csv binds coke_oven_gas.")
ov("IISELAFUR01", "eaf_elec", "eaf", "electricity", "Chemistry node, electric arc furnace.")
ov("IISMIDREX01", "dri_midrex_gas", "dri_shaft", "natural_gas",
   "A2: `Standard_FF` on MIDREX direct reduced iron; IND_NGABOM present, unit.csv binds natural_gas.")
ov("IISSINTER01", "sinter_plant_coke", "sinter_plant", "coke",
   "A2: `Standard_FF` on the sinter plant; INDCOK present, unit.csv binds coke.")
ov("IISCASHRM01", "rolling_mill_reheat_gas", "rolling_mill", "natural_gas",
   "Service spine, HRS duty family (caster and hot rolling mill reheat).")
ov("IISCASHRHYM01", "rolling_mill_reheat_hydrogen", "rolling_mill", "hydrogen",
   "Service spine, HRS duty family, hydrogen variant.")
ov("IISFINPRO01", None, "generic_process", "natural_gas",
   "A2: `Standard_FF` on downstream steel finishing. Real energy-consuming plant "
   "(IND_NGABOM;INDDISTELC), but unit.csv has no finishing unit and its output_commodity IIS is "
   "the sector demand commodity. Requested in DONE_lineage.md.")
ov("IISBOIBFG01", None, "boiler", "blast_furnace_gas",
   "A2: `Standard_FF` on a blast furnace gas boiler. carrier.csv has blast_furnace_gas, but "
   "unit.csv has no LTH boiler bound to it -- only chp_bfg_gas_turbine. Requested in "
   "DONE_lineage.md.")
ov("IISBOICOG01", None, "boiler", "coke_oven_gas",
   "A2: `Standard_FF` on a coke oven gas boiler. carrier.csv has coke_oven_gas, but unit.csv has "
   "no LTH boiler bound to it -- only chp_cog_gas_turbine. Requested in DONE_lineage.md.")
ov("IISBOIBIOS01", "boiler_lt_biomass", "boiler", "solid_biomass",
   "Iron & steel copy of the LTH biomass boiler; collapses into the service spine unit.")
ov("IISBOINGA01", "boiler_lt_gas", "boiler", "natural_gas",
   "Iron & steel copy of the LTH gas boiler; collapses into the service spine unit.")
ov("IISBOIHYG01", "boiler_lt_hydrogen", "boiler", "hydrogen",
   "Iron & steel copy of the LTH hydrogen boiler; collapses into the service spine unit.")

# Glass
ov("IGLKLN", "glass_furnace_gas", "furnace", "natural_gas",
   "Chemistry node. Regenerative end-port furnace with electric boosting; unit.csv binds the "
   "primary carrier natural_gas under D13 (one primary carrier per unit).")
ov("IGLKLNELC", "glass_furnace_elec", "furnace", "electricity", "Chemistry node, electric cold-top furnace.")
ov("IGLKLNHYD", "glass_furnace_hydrogen", "furnace", "hydrogen",
   "Chemistry node. Hydrogen furnace with electric boosting; emitting_fuel_commodities lists only "
   "INDDISTELC because hydrogen combustion is not an emitting fuel. unit.csv binds hydrogen.")
ov("IGLHTHNGA", "furnace_ht_gas", "furnace", "natural_gas",
   "A2: `Standard_FF` on 'High-temperature heat technology based on natural gas / biomethane "
   "(boiler)'; IND_NGABOM present. Collapses into the HTH service spine.")

# Paper
ov("IPPPRODRY01", "paper_dryer_elec", "paper_machine", "electricity", "Chemistry node, paper machine drying.")
ov("IPPPROPRS01", "paper_press_elec", "paper_machine", "electricity",
   "A2: `Standard_FF` on 'Press section (standard)'; only INDDISTELC in emitting_fuel_commodities.")
ov("IPPPROOTH01", "paper_stock_prep_elec", "paper_machine", "electricity",
   "A2: `Standard_FF` on 'Technologies for the other production steps (standard)'; only "
   "INDDISTELC. unit.csv names IPPPROOTH01 in paper_stock_prep_elec's provenance_ref.")
ov("IPPFINPRO01", None, "generic_process", "",
   "A2: `Standard_FF` on paper converting/finishing. Multi-fuel "
   "(IND_NGABOM;INDCOA;INDDISTELC;INDHFO;INDLFO;INDMAINSBOM;INDMAINSGAS) with no single primary, "
   "and unit.csv has no finishing unit; its output_commodity IPP is the sector demand commodity. "
   "Requested in DONE_lineage.md.")
ov("IPPBOICOA01", "boiler_lt_coal", "boiler", "coal",
   "Paper copy of the LTH coal boiler; collapses into the service spine unit.")
ov("IPPBOINGA01", "boiler_lt_gas", "boiler", "natural_gas",
   "Paper copy of the LTH gas boiler; collapses into the service spine unit.")
ov("IPPCHPGT01", "chp_gas_turbine", "chp", "natural_gas",
   "A2: `Standard_FF` on 'Gas turbine CHP based on natural gas'. IND_NGABOMLFO is COMIT's "
   "gas-turbine dual-fuel commodity; the primary carrier under D13 is natural_gas.")

# Refineries
ov("POILREF01", "refinery_fixed_mix_gas", "refinery", "natural_gas",
   "A2: `Standard_FF` on the fixed-output-mix oil refinery; IND_NGABOM present.")
ov("POILREF02", "refinery_flexible_mix_gas", "refinery", "natural_gas",
   "A2: `Standard_FF` on the flexible-output-mix oil refinery; IND_NGABOM present.")
ov("PCHP-CCP01", "refinery_process_heat_gas", "chp", "natural_gas",
   "Service spine, PHEAT duty family. Refinery CHP CCGT with flexible refinery gas / natural gas "
   "/ HFO input; unit.csv binds the primary carrier natural_gas under D13.")

# --- dropped: COMIT accounting rows that are not site plant ------------------------------
DROP_REASON_DEMAND = (
    "Dropped: COMIT demand technology. It converts a sector's energy-service commodities into "
    "the sector demand commodity, has no fuel input (emitting_fuel_commodities is empty) and no "
    "cost or capacity. The data migration's Group A excludes the sector-level demand commodities "
    "explicitly. V1b (parity against the frozen R run) compares nothing through it."
)
for _c in ["ICR01", "ICH01", "ICN01", "IEE01", "IFD01", "IGL01",
           "IME01", "INF01", "IOI01", "IPR01", "ITX01", "IVH01"]:
    ov(_c, "", "demand", "", DROP_REASON_DEMAND)
ov("INDHFCOTH01", "", "demand", "",
   "Dropped: accounting row, not plant. 'Dummy demand for Other HFC emissions' -- a residual "
   "non-CO2 emission bucket with no fuel, no cost and no capacity. CaRB3 carries refrigerant "
   "emissions on the chiller units instead.")

# --- CHP rules for the remaining per-sector copies ---------------------------------------
CHP_RULES = [
    ("CHPCCGTH", "chp_hydrogen_ccgt", "hydrogen"),
    ("CHPCCGT", "chp_gas_ccgt", "natural_gas"),
    ("CHPFCH", "chp_hydrogen_fuelcell", "hydrogen"),
    ("CHPGT", "chp_gas_turbine", "natural_gas"),
    ("CHPBIOS", "chp_biomass_st", "solid_biomass"),
    ("CHPCOA", "chp_coal_st", "coal"),
    ("CHPLPG", "chp_lpg_ccgt", "lpg"),
    ("CHPBFG", "chp_bfg_gas_turbine", "blast_furnace_gas"),
    ("CHPCOG", "chp_cog_gas_turbine", "coke_oven_gas"),
    ("CHPPRO", "chp_byproduct_ccgt", "petroleum_products_misc"),
]


def duty_of(output_commodity):
    for p in SECTOR_PREFIXES:
        if output_commodity.startswith(p) and len(output_commodity) > len(p):
            return output_commodity[len(p):]
    return None


def main():
    esc = list(csv.DictReader(open(ESC, newline="")))
    units = {r["unit_id"]: r for r in csv.DictReader(open(UNIT, newline=""))}
    carriers = {r["carrier_id"] for r in csv.DictReader(open(CARRIER, newline=""))}

    # how many source rows land on each unit -- decides collapsed vs preserved
    assign = {}
    for r in esc:
        code = r["technology_code"]
        cat = r["technology_category"]
        name = r["technology_name"]
        notes = ""

        if code in O:
            unit_id, unit_type, carrier_id, reason, notes = O[code]
        else:
            unit_id = unit_type = carrier_id = reason = None
            # CHP copies
            for token, uid, car in CHP_RULES:
                if token in code:
                    unit_id, unit_type, carrier_id = uid, "chp", car
                    reason = ("Per-sector copy of a CHP archetype; collapses into the STM service "
                              "spine unit under D13 (a unit is family-or-node x fuel).")
                    break
            if unit_id is None:
                duty = duty_of(r["output_commodity"])
                key = (duty, cat)
                if key in SERVICE:
                    unit_id = SERVICE[key]
                    unit_type = SERVICE_UNIT_TYPE.get(key, DUTY_UNIT_TYPE.get(duty, ""))
                    carrier_id = CATEGORY_CARRIER[cat]
                    reason = ("Per-sector copy of the %s duty served by category `%s`; collapses "
                              "into the service spine unit under D13 (a unit is family-or-node x "
                              "fuel)." % (duty, cat))
                    if cat == "Steam":
                        reason += (" carrier_id is deliberately blank: COMIT's `Steam` is "
                                   "heat-from-CHP, which carrier.csv represents as six graded heat "
                                   "bands, and the source row states no grade. Per convention 1 a "
                                   "blank beats a guess, and unit.csv leaves this unit's "
                                   "fuel_carrier_id blank for the same reason.")
                else:
                    raise SystemExit("unresolved row: %s | %s | %s | %s"
                                     % (code, cat, r["output_commodity"], name))

        assign[code] = dict(unit_id=unit_id, unit_type=unit_type, carrier_id=carrier_id,
                            reason=reason, notes=notes)

    counts = {}
    for code, a in assign.items():
        if a["unit_id"]:
            counts[a["unit_id"]] = counts.get(a["unit_id"], 0) + 1

    rows = []
    for r in esc:
        code = r["technology_code"]
        a = assign[code]
        unit_id = a["unit_id"]
        carrier_id = a["carrier_id"] or ""
        notes = a["notes"]
        reason = a["reason"]

        if unit_id is None:
            disposition, unit_id, fuel_carrier_id = "unmapped", "", ""
        elif unit_id == "":
            disposition, fuel_carrier_id = "dropped", ""
        else:
            fuel_carrier_id = units[unit_id]["fuel_carrier_id"]
            if counts[unit_id] > 1:
                disposition = "collapsed"
            else:
                disposition = "preserved"

        if carrier_id and fuel_carrier_id and carrier_id != fuel_carrier_id:
            notes = (notes + "; " if notes else "") + (
                "A1 splits this source row's own fuel as %s, but the unit it maps to binds %s. "
                "The two differ legitimately: the source technology is the host plant, the unit is "
                "the bolt-on, and they burn different fuels. V1b must compare energy on the unit's "
                "binding (%s), not on this column." % (carrier_id, fuel_carrier_id, fuel_carrier_id))

        rows.append({
            "technology_code": code,
            "technology_name": r["technology_name"],
            "sector": r["sector"],
            "technology_category": r["technology_category"],
            "output_commodity": r["output_commodity"],
            "carrier_id": carrier_id,
            "unit_type": a["unit_type"] or "",
            "abatement": "ccs" if r["technology_category"] == "CCS" else "",
            "disposition": disposition,
            "unit_id": unit_id,
            "fuel_carrier_id": fuel_carrier_id,
            "reason": reason,
            "notes": notes,
        })

    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    print("wrote %s: %d rows" % (OUT, len(rows)))
    print("dispositions:", dict(Counter(x["disposition"] for x in rows)))
    unknown = {x["carrier_id"] for x in rows if x["carrier_id"] and x["carrier_id"] not in carriers}
    if unknown:
        raise SystemExit("carrier_id not in carrier.csv: %s" % unknown)


if __name__ == "__main__":
    sys.exit(main())
