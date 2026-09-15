#!/usr/bin/env python3
"""Lane `units` check script. Stdlib only (pandas is not installed in this repo).

Run from anywhere:  python3 docs/notes/data/build/check_units.py
Exit status 0 = all blocking checks pass.

Blocking checks, in the order the brief names them:
  1  unit_id unique
  2  every worked-example unit present
  3  every carrier_id resolves to carrier.csv or the product staging file
  4  exactly one is_primary_output per unit that has coefficients
  5  at most one is_fuel_input per unit  (§3.6; two is rejected at load as `unit_multi_fuel`)
  6  bill-of-materials capacity_share sums to 1 per hybrid, and every hybrid has rows
  7  every [REF_ID] resolves to references.csv or references_units.csv
plus structural checks: enums, booleans, foreign keys, no `NA`/`n/a`/`-`/`?` placeholders,
V2's round-trip, and the D15 rule that no co2_fuel_* row is authored on a producing unit.
"""
import csv, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(DATA))
def load(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))

units = load(os.path.join(DATA, "unit.csv"))
io    = load(os.path.join(DATA, "unit_input_output.csv"))
bom   = load(os.path.join(DATA, "unit_bill_of_materials.csv"))
car   = load(os.path.join(DATA, "carrier.csv"))
prod  = load(os.path.join(HERE, "carrier_products_units.csv"))
reg   = load(os.path.join(DATA, "activity_process_register.csv"))
refs  = load(os.path.join(DATA, "references.csv")) + load(os.path.join(HERE, "references_units.csv"))

CAR_IDS  = {r["carrier_id"] for r in car} | {r["carrier_id"] for r in prod}
PROC_IDS = {r["process_id"] for r in reg}
UNIT_IDS = [r["unit_id"] for r in units]
REF_IDS  = {r["ref_id"] for r in refs}

WORKED_EXAMPLE_UNITS = """
kiln_dry_coal kiln_dry_gas kiln_dry_wdf kiln_fluidbed_wdf kiln_calcium_looping_coal ccs_amine
ccs_amine_mdea ccs_oxyfuel ccs_oxyfuel_partial grinder_mixer_elec
grinder_mixer_clinker_sub_elec cement_lowcarbon_elec motor_elec pv_rooftop battery_2h
boiler_lt_gas boiler_lt_hydrogen boiler_lt_biomass boiler_lt_lpg boiler_lt_coal
resistance_heater_lt heat_pump_lt_air heat_pump_lt_reject heat_pump_ht chp_gas_turbine
chp_hydrogen_ccgt chp_biomass_st dryer_direct_gas dryer_direct_hydrogen dryer_electric
chiller_electric
""".split()

ENUMS = {
    "unit_class": {"converter", "generator", "storage", "hybrid", "abatement"},
    "spine": {"service", "chemistry"},
    "provenance": {"comit_reuse", "bref", "proxy"},
    "confidence": {"high", "medium", "low"},
}
DUTY_FAMILIES = {"DRY","EN","HRS","HTH","LTH","MOT","NEUOTH","OTH","PHEAT","REF","SPC","STM"}
PLACEHOLDERS = {"NA", "n/a", "N/A", "-", "?", "None", "null"}

fail, warn = [], []
def check(ok, msg):
    (fail if not ok else warn).append(msg) if not ok else None

# 1 -------------------------------------------------------------------------
dupes = [u for u, n in collections.Counter(UNIT_IDS).items() if n > 1]
if dupes: fail.append("1  duplicate unit_id: %s" % dupes)

# 2 -------------------------------------------------------------------------
missing = [u for u in WORKED_EXAMPLE_UNITS if u not in set(UNIT_IDS)]
if missing: fail.append("2  worked-example unit absent from unit.csv: %s" % missing)

# 3 -------------------------------------------------------------------------
bad = sorted({r["carrier_id"] for r in io if r["carrier_id"] not in CAR_IDS})
if bad: fail.append("3  unit_input_output.carrier_id does not resolve: %s" % bad)
bad = sorted({r["fuel_carrier_id"] for r in units if r["fuel_carrier_id"] and r["fuel_carrier_id"] not in CAR_IDS})
if bad: fail.append("3  unit.fuel_carrier_id does not resolve: %s" % bad)

# 4, 5 ----------------------------------------------------------------------
prim = collections.Counter(r["unit_id"] for r in io if r["is_primary_output"] == "TRUE")
fuel = collections.Counter(r["unit_id"] for r in io if r["is_fuel_input"] == "TRUE")
with_io = {r["unit_id"] for r in io}
bad = sorted(u for u in with_io if prim[u] != 1)
if bad: fail.append("4  not exactly one is_primary_output: %s" % [(u, prim[u]) for u in bad])
bad = sorted(u for u in with_io if fuel[u] > 1)
if bad: fail.append("5  more than one is_fuel_input (load would reject as unit_multi_fuel): %s" % bad)

# 6 -------------------------------------------------------------------------
hybrids = {r["unit_id"] for r in units if r["is_hybrid"] == "TRUE"}
bom_by = collections.defaultdict(list)
for r in bom: bom_by[r["unit_id"]].append(r)
miss = sorted(hybrids - set(bom_by))
if miss: fail.append("6  is_hybrid TRUE with no unit_bill_of_materials rows: %s" % miss)
extra = sorted(set(bom_by) - hybrids)
if extra: fail.append("6  unit_bill_of_materials row whose unit is not is_hybrid: %s" % extra)
for u, rs in sorted(bom_by.items()):
    s = sum(float(r["capacity_share"]) for r in rs if r["capacity_share"])
    if abs(s - 1.0) > 0.001:
        fail.append("6  capacity_share sums to %.5f, not 1, for %s" % (s, u))
    cx = [r["capex_share"] for r in rs if r["capex_share"]]
    if cx:
        s = sum(float(x) for x in cx)
        if len(cx) != len(rs):
            warn.append("6  %s has capex_share on %d of %d components; not summed" % (u, len(cx), len(rs)))
        elif abs(s - 1.0) > 0.001:
            fail.append("6  capex_share sums to %.5f, not 1, for %s" % (s, u))

# 7 -------------------------------------------------------------------------
cited = set()
for rows in (units, io, bom, prod):
    for r in rows:
        for v in r.values():
            cited |= set(re.findall(r"\[([A-Z0-9_]+)\]", v or ""))
bad = sorted(cited - REF_IDS)
if bad: fail.append("7  [REF_ID] does not resolve to references.csv or references_units.csv: %s" % bad)
for r in units:
    if r["provenance_ref"] and not re.search(r"\[[A-Z0-9_]+\]", r["provenance_ref"]):
        fail.append("7  provenance_ref carries no [REF_ID]: %s" % r["unit_id"])

# structural ----------------------------------------------------------------
for r in units:
    for f, allowed in ENUMS.items():
        if r[f] and r[f] not in allowed:
            fail.append("enum  %s.%s = %r" % (r["unit_id"], f, r[f]))
    for f in ("is_hybrid", "draws_ambient"):
        if r[f] not in ("TRUE", "FALSE"):
            fail.append("bool  %s.%s = %r" % (r["unit_id"], f, r[f]))
    if r["spine"] == "service" and r["duty_family"] and r["duty_family"] not in DUTY_FAMILIES:
        fail.append("enum  %s.duty_family = %r" % (r["unit_id"], r["duty_family"]))
    if r["process_id"] and r["process_id"] not in PROC_IDS:
        fail.append("fk    %s.process_id = %r does not resolve" % (r["unit_id"], r["process_id"]))
    if r["abates_unit_id"] and r["abates_unit_id"] not in set(UNIT_IDS):
        fail.append("fk    %s.abates_unit_id = %r does not resolve" % (r["unit_id"], r["abates_unit_id"]))
    for f, v in r.items():
        if (v or "").strip() in PLACEHOLDERS:
            fail.append("blank %s.%s is %r; a blank must be an empty string" % (r["unit_id"], f, v))
    af = r["availability_factor"]
    if af and not (0 < float(af) <= 1):
        fail.append("range %s.availability_factor = %s, not in (0, 1]" % (r["unit_id"], af))
    er = r["emissions_released"]
    if er and not (0 <= float(er) <= 1):
        fail.append("range %s.emissions_released = %s, not in [0, 1]" % (r["unit_id"], er))

for r in io:
    for f in ("is_primary_output", "is_reject", "is_fuel_input"):
        if r[f] not in ("TRUE", "FALSE"):
            fail.append("bool  %s/%s.%s = %r" % (r["unit_id"], r["carrier_id"], f, r[f]))
    if r["unit_id"] not in set(UNIT_IDS):
        fail.append("fk    unit_input_output row for unknown unit %s" % r["unit_id"])

# 3.6 primary key is (unit_id, carrier_id)
k = collections.Counter((r["unit_id"], r["carrier_id"]) for r in io)
bad = [x for x, n in k.items() if n > 1]
if bad: fail.append("pk    (unit_id, carrier_id) appears twice: %s" % bad)

# D15: co2_fuel_* is derived by A6, never authored on a producing unit
bad = [(r["unit_id"], r["carrier_id"]) for r in io
       if r["carrier_id"].startswith("co2_fuel") and float(r["coefficient"]) > 0]
if bad: fail.append("D15   co2_fuel_* authored as a positive (produced) coefficient; A6 derives these: %s" % bad)

# V2: capacity_to_activity_factor and the primary output round-trip
for r in units:
    c2a = r["capacity_to_activity_factor"]
    if c2a and float(c2a) <= 0:
        fail.append("V2    %s.capacity_to_activity_factor = %s, must be > 0" % (r["unit_id"], c2a))
by_unit = collections.defaultdict(list)
for r in io: by_unit[r["unit_id"]].append(r)
for u, rs in by_unit.items():
    p = [r for r in rs if r["is_primary_output"] == "TRUE"]
    if p and abs(float(p[0]["coefficient"]) - 1.0) > 1e-6:
        warn.append("V2    %s primary output is %s, not +1.00000" % (u, p[0]["coefficient"]))

# reporting ------------------------------------------------------------------
print("unit.csv                    %4d rows" % len(units))
print("unit_input_output.csv       %4d rows, %d units" % (len(io), len(by_unit)))
print("unit_bill_of_materials.csv  %4d rows, %d hybrids" % (len(bom), len(bom_by)))
print("carrier_products_units.csv  %4d rows" % len(prod))
print("units with no coefficients  %4d" % (len(units) - len(by_unit)))
print()
for w in warn: print("WARN  " + w)
if warn: print()
if fail:
    for f in fail: print("FAIL  " + f)
    print("\n%d blocking failure(s)" % len(fail))
    sys.exit(1)
print("all blocking checks pass")
