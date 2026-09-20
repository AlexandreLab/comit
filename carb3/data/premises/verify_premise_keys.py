#!/usr/bin/env python3
"""Verify every key in carb3/data/premises/ resolves against docs/notes/data/.

Stdlib only (pandas is not installed here). Run from the repo root.
"""
import csv, os, sys, collections

REF = "docs/notes/data"
PRE = "carb3/data/premises"
err, warn = [], []

def rd(root, name):
    p = os.path.join(root, name)
    with open(p, newline="") as f:
        return list(csv.DictReader(f))

carrier   = {r["carrier_id"]: r for r in rd(REF, "carrier.csv")}
CLUSTERS  = {r["cluster_id"] for r in rd(REF, "infrastructure_scenario.csv")}
unit      = {r["unit_id"]: r for r in rd(REF, "unit.csv")}
elig      = rd(REF, "unit_eligibility.csv")
reg       = rd(REF, "activity_process_register.csv")
dutyprof  = rd(REF, "activity_process_duty_profile.csv")
sp        = rd(REF, "scenario_parameters.csv")
uio       = collections.defaultdict(list)
for r in rd(REF, "unit_input_output.csv"):
    uio[r["unit_id"]].append(r)

ACTIVITIES = {r["carb3_activity"] for r in reg}
REG_PROC   = {(r["carb3_activity"], r["process_id"]) for r in reg}
ELIG       = {(r["unit_id"], r["carb3_activity"], r["process_id"]) for r in elig}
ELIG_ACT   = {(r["unit_id"], r["carb3_activity"]) for r in elig if not r["process_id"].strip()}
PERIODS    = sorted({int(r["period"]) for r in sp if r["period"]})
PRICED     = {c for c in {r["carrier_id"] for r in sp if r["parameter_id"] == "import_price"}
              if set(PERIODS) <= {int(r["period"]) for r in sp
                                  if r["parameter_id"] == "import_price" and r["carrier_id"] == c}}

record     = rd(PRE, "premise_record.csv")
conn       = rd(PRE, "premise_connection.csv")
energy     = rd(PRE, "premise_energy.csv")
through    = rd(PRE, "premise_throughput.csv")
detail     = rd(PRE, "premise_process_detail.csv")
ppunit     = rd(PRE, "premise_process_unit.csv")
vintage    = rd(PRE, "premise_process_vintage.csv")

ACT   = {r["premise_id"]: r["carb3_activity"] for r in record}
DYEAR = {r["premise_id"]: int(r["data_year"]) for r in record}
CONN  = {(r["premise_id"], r["connection_id"]) for r in conn}
def E(m): err.append(m)
def W(m): warn.append(m)

# --- premise_record -------------------------------------------------------
seen = set()
for r in record:
    p = r["premise_id"]
    if p in seen: E(f"premise_record: duplicate premise_id {p}")
    seen.add(p)
    if r["carb3_activity"] not in ACTIVITIES:
        E(f"premise_record[{p}]: carb3_activity {r['carb3_activity']!r} not in activity_process_register")
    if r["nation"] not in ("England", "Wales", "Scotland"):
        E(f"premise_record[{p}]: nation {r['nation']!r} not in the enum")
    if not (49.9 <= float(r["latitude"]) <= 60.9 and -8.7 <= float(r["longitude"]) <= 1.8):
        E(f"premise_record[{p}]: lat/long outside the GB bounding box")
    if r["construction_year"] and int(r["construction_year"]) > DYEAR[p]:
        E(f"premise_record[{p}]: construction_year after data_year")
    if r["construction_year"] and r["construction_year_band"]:
        W(f"premise_record[{p}]: both construction_year and _band given; the year wins")
    # cluster_id is not a spec 3.1 field. Spec 3.7 says A1 assigns the nearest in-scope
    # cluster on ingest and gives the assignment nowhere to live (note 20 item 58), so the
    # slice keeps it here. Optional: absent means outside every cluster, which is 3.7's own
    # beyond-the-radius case, and C9 then permits no CO2 export at all.
    cluster = (r.get("cluster_id") or "").strip()
    if cluster and cluster != "none" and cluster not in CLUSTERS:
        E(f"premise_record[{p}]: cluster_id {cluster!r} not in infrastructure_scenario.csv")
    if not cluster:
        W(f"premise_record[{p}]: no cluster_id, so C9 marks CO2 transport unavailable")

# --- premise_connection ---------------------------------------------------
for r in conn:
    p = r["premise_id"]
    if p not in ACT: E(f"premise_connection: unknown premise_id {p}")
    if r["carrier_id"] not in carrier:
        E(f"premise_connection[{p}/{r['connection_id']}]: carrier_id {r['carrier_id']!r} not in carrier.csv")

# --- premise_energy -------------------------------------------------------
pos = collections.Counter()
for r in energy:
    p = r["premise_id"]
    if p not in ACT: E(f"premise_energy: unknown premise_id {p}")
    if r["carrier_id"] not in carrier:
        E(f"premise_energy[{p}]: carrier_id {r['carrier_id']!r} not in carrier.csv")
    if r["connection_id"] and (p, r["connection_id"]) not in CONN:
        E(f"premise_energy[{p}]: connection_id {r['connection_id']!r} not in premise_connection")
    if r["data_status"] not in ("measured", "estimated", "modelled", "not_consumed"):
        E(f"premise_energy[{p}]: data_status {r['data_status']!r} not in the enum")
    if float(r["quantity"]) > 0: pos[p] += 1
for p in ACT:
    if not pos[p]: E(f"premise_energy[{p}]: no row with quantity > 0 (A1 reason no_energy)")

# --- premise_throughput ---------------------------------------------------
for r in through:
    p = r["premise_id"]
    if p not in ACT: E(f"premise_throughput: unknown premise_id {p}")
    c = carrier.get(r["carrier_id"])
    if c is None: E(f"premise_throughput[{p}]: carrier_id {r['carrier_id']!r} not in carrier.csv")
    elif c["denominator_kind"] != "mass":
        E(f"premise_throughput[{p}]: {r['carrier_id']} denominator_kind is {c['denominator_kind']}, must be mass")

# --- premise_process_detail ----------------------------------------------
parents = set()
by_pp = collections.defaultdict(list)
for r in detail:
    p, proc, vf = r["premise_id"], r["process_id"], int(r["valid_from_year"])
    if p not in ACT: E(f"premise_process_detail: unknown premise_id {p}"); continue
    if (ACT[p], proc) not in REG_PROC:
        E(f"premise_process_detail[{p}]: ({ACT[p]}, {proc}) not in activity_process_register")
    if vf > DYEAR[p]:
        E(f"premise_process_detail[{p}/{proc}]: valid_from_year {vf} > data_year (process_change_in_future)")
    if r["valid_to_year"] and int(r["valid_to_year"]) < vf:
        E(f"premise_process_detail[{p}/{proc}]: valid_to_year before valid_from_year")
    if r["connection_id"] and (p, r["connection_id"]) not in CONN:
        E(f"premise_process_detail[{p}/{proc}]: connection_id {r['connection_id']!r} not in premise_connection")
    if r["known_capacity"].strip() and float(r["known_capacity"]) <= 0:
        E(f"premise_process_detail[{p}/{proc}]: known_capacity must be > 0 if present")
    if r["confidence"] not in ("high", "medium", "low"):
        E(f"premise_process_detail[{p}/{proc}]: confidence {r['confidence']!r} not in the enum")
    if (p, proc, vf) in parents:
        E(f"premise_process_detail: duplicate key ({p}, {proc}, {vf})")
    parents.add((p, proc, vf))
    by_pp[(p, proc)].append((vf, int(r["valid_to_year"]) if r["valid_to_year"] else 9999))
# intervals disjoint, and at least one row valid at the base year
for (p, proc), ivs in by_pp.items():
    for i in range(len(ivs)):
        for j in range(i + 1, len(ivs)):
            a, b = ivs[i], ivs[j]
            if a[0] <= b[1] and b[0] <= a[1]:
                E(f"premise_process_detail[{p}/{proc}]: intervals overlap (process_intervals_overlap)")
base_ok = collections.defaultdict(bool)
for r in detail:
    p = r["premise_id"]
    vt = int(r["valid_to_year"]) if r["valid_to_year"] else 9999
    if int(r["valid_from_year"]) <= DYEAR[p] <= vt: base_ok[p] = True
for p in ACT:
    if not base_ok[p]: E(f"premise_process_detail[{p}]: no row valid at the base year")

# --- premise_process_unit -------------------------------------------------
shares = collections.defaultdict(list)
for r in ppunit:
    p, proc, vf, u = r["premise_id"], r["process_id"], int(r["valid_from_year"]), r["unit_id"]
    if (p, proc, vf) not in parents:
        E(f"premise_process_unit[{p}/{proc}/{vf}]: no matching premise_process_detail row")
    if u not in unit:
        E(f"premise_process_unit[{p}/{proc}]: unit_id {u!r} not in unit.csv"); continue
    if (u, ACT[p], proc) not in ELIG and (u, ACT[p]) not in ELIG_ACT:
        E(f"premise_process_unit[{p}/{proc}]: {u} not eligible for ({ACT[p]}, {proc}) in unit_eligibility.csv")
    if r["confidence"] not in ("high", "medium", "low"):
        E(f"premise_process_unit[{p}/{proc}/{u}]: confidence not in the enum")
    shares[(p, proc, vf)].append((u, float(r["capacity_share"]) if r["capacity_share"] else None))
for k, v in shares.items():
    us = [u for u, _ in v]
    if len(us) != len(set(us)): E(f"premise_process_unit{k}: units are not distinct")
    given = [s for _, s in v if s is not None]
    if given and len(given) != len(v):
        E(f"premise_process_unit{k}: capacity_share given on some rows but not all")
    if given:
        if abs(sum(given) - 1.0) > 1e-6: E(f"premise_process_unit{k}: capacity_share sums to {sum(given)}, not 1 (V33)")
        if any(not (0 < s <= 1) for s in given): E(f"premise_process_unit{k}: capacity_share outside (0, 1]")

# --- premise_process_vintage ---------------------------------------------
vshares = collections.defaultdict(list)
vkeys = set()
for r in vintage:
    p, proc, coh, u = r["premise_id"], r["process_id"], r["cohort_id"], r["unit_id"]
    if p not in ACT: E(f"premise_process_vintage: unknown premise_id {p}"); continue
    if (ACT[p], proc) not in REG_PROC:
        E(f"premise_process_vintage[{p}]: ({ACT[p]}, {proc}) not in activity_process_register")
    if (p, proc, coh) in vkeys: E(f"premise_process_vintage: duplicate key ({p}, {proc}, {coh})")
    vkeys.add((p, proc, coh))
    if u and u not in unit: E(f"premise_process_vintage[{p}/{proc}]: unit_id {u!r} not in unit.csv")
    if int(r["commissioned_year"]) > DYEAR[p]:
        E(f"premise_process_vintage[{p}/{proc}/{coh}]: commissioned_year after data_year (vintage_in_future)")
    if r["confidence"] not in ("high", "medium", "low"):
        E(f"premise_process_vintage[{p}/{proc}/{coh}]: confidence not in the enum")
    vshares[(p, proc)].append(float(r["capacity_share"]))
    # the cohort must name a unit the premise actually runs at the base year
    live = {(pu["unit_id"]) for pu in ppunit
            if pu["premise_id"] == p and pu["process_id"] == proc
            and any(d["premise_id"] == p and d["process_id"] == proc
                    and int(d["valid_from_year"]) == int(pu["valid_from_year"])
                    and (int(d["valid_to_year"]) if d["valid_to_year"] else 9999) >= DYEAR[p]
                    for d in detail)}
    if u and live and u not in live:
        E(f"premise_process_vintage[{p}/{proc}/{coh}]: {u} is not a base-year unit of that process")
for k, v in vshares.items():
    if abs(sum(v) - 1.0) > 1e-6: E(f"premise_process_vintage{k}: capacity_share sums to {sum(v)}, not 1 (vintage_shares_unbalanced)")
    if any(not (0 < s <= 1) for s in v): E(f"premise_process_vintage{k}: capacity_share outside (0, 1]")

# --- the admission screen, on the units these premises actually name -------
REQ = ["capex", "lifetime", "fixed_opex", "availability_factor", "capacity_to_activity_factor"]
named = sorted({r["unit_id"] for r in ppunit})
for u in named:
    bad = [f"blank {k}" for k in REQ if not unit[u][k].strip()]
    if not uio[u]: bad.append("no unit_input_output rows")
    fc = unit[u]["fuel_carrier_id"].strip()
    if fc and not any(x["role"] == "fuel_input" for x in uio[u]):
        bad.append(f"declares fuel_carrier_id {fc} with no fuel_input row")
    for x in uio[u]:
        if x["role"] in ("fuel_input", "aux_input", "emission_input"):
            ci = carrier.get(x["carrier_id"])
            if ci is None: bad.append(f"unknown carrier {x['carrier_id']}")
            elif ci["may_import"].upper() == "TRUE" and x["carrier_id"] not in PRICED:
                bad.append(f"consumes {x['carrier_id']}, which is not priced for every period")
    if bad: E(f"admission screen: incumbent {u} would be DROPPED - {'; '.join(bad)}")

# --- every duty of every premise has an incumbent at the base year --------
for p in ACT:
    procs = {r["process_id"] for r in detail
             if r["premise_id"] == p
             and int(r["valid_from_year"]) <= DYEAR[p] <= (int(r["valid_to_year"]) if r["valid_to_year"] else 9999)}
    with_units = {r["process_id"] for r in ppunit if r["premise_id"] == p}
    for proc in sorted(procs - with_units):
        E(f"[{p}] process {proc} is valid at the base year and names no unit - C1 is an equality and C5 forbids building in 2021")
    for proc in sorted(procs):
        if not [d for d in dutyprof if d["carb3_activity"] == ACT[p] and d["process_id"] == proc]:
            W(f"[{p}] process {proc} has no activity_process_duty_profile row, so A2 derives no duty for it")

print(f"reference root : {REF}   premise root: {PRE}")
print(f"premises       : {', '.join(ACT)}")
print(f"rows checked   : record {len(record)}, connection {len(conn)}, energy {len(energy)}, "
      f"throughput {len(through)}, detail {len(detail)}, process_unit {len(ppunit)}, vintage {len(vintage)}")
print(f"distinct unit_id / process_id / carrier_id / carb3_activity resolved: "
      f"{len(named)} / {len({r['process_id'] for r in detail})} / "
      f"{len({r['carrier_id'] for r in energy} | {r['carrier_id'] for r in through} | {r['carrier_id'] for r in conn})} / "
      f"{len(set(ACT.values()))}")
for w in warn: print("WARN  ", w)
for e in err: print("FAIL  ", e)
print(("FAILED: %d" % len(err)) if err else "OK: every key resolves and every premise-side rule holds")
sys.exit(1 if err else 0)
