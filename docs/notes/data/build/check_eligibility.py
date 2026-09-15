#!/usr/bin/env python3
"""Check the `eligibility` lane's three deliverables.

Stdlib only.  Exits non-zero on any blocking failure; prints an advisory
section that does not fail the run.

Blocking checks, from brief_eligibility.md:
  1  every option in decarbonisation_options_library.csv has >= 1 join row
  2  every unit_id in the join resolves to unit.csv (blank allowed, counted)
  3  every unit_id in unit_eligibility.csv resolves to unit.csv
  4  every (carb3_activity, process_id) in unit_eligibility.csv resolves to
     activity_process_register.csv (blank process_id allowed for supply units)
  5  every carrier_id in displaces_carrier_ids resolves to carrier.csv
  6  every [REF_ID] used resolves to references.csv or references_eligibility.csv
  7  the aligned library keeps every original column, row and value unchanged
  8  enums are spelled as the spec spells them; booleans are TRUE/FALSE
  9  unit_eligibility is unique on (unit_id, carb3_activity, process_id)
 10  min_duty, max_share, earliest_year parse, and max_share is in [0, 1]
"""

import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.dirname(HERE)

RELATIONSHIPS = {"is_unit", "enables", "route_change", "supply", "none"}
PROVENANCE = {"comit_reuse", "bref", "proxy"}
CONFIDENCE = {"high", "medium", "low"}

fail = []
warn = []


def read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def d(name):
    return read(os.path.join(DATA, name))


def s(name):
    return read(os.path.join(HERE, name))


library = d("decarbonisation_options_library.csv")
units = d("unit.csv")
carriers = d("carrier.csv")
register = d("activity_process_register.csv")
join = d("decarbonisation_option_unit.csv")
elig = d("unit_eligibility.csv")
aligned = s("decarbonisation_options_library_aligned.csv")
refs = d("references.csv") + s("references_eligibility.csv")

unit_ids = {u["unit_id"] for u in units}
carrier_ids = {c["carrier_id"] for c in carriers}
ref_ids = {r["ref_id"] for r in refs}
reg_keys = {(r["carb3_activity"], r["process_id"]) for r in register}
activities = {r["carb3_activity"] for r in register}
option_ids = [o["option_id"] for o in library]

# 1 -------------------------------------------------------------------------
joined = {r["option_id"] for r in join}
missing = [o for o in option_ids if o not in joined]
if missing:
    fail.append("options with no join row: %s" % missing)
stray = joined - set(option_ids)
if stray:
    fail.append("join rows for unknown options: %s" % sorted(stray))

# 2 -------------------------------------------------------------------------
blank_unit = 0
for r in join:
    if not r["unit_id"]:
        blank_unit += 1
    elif r["unit_id"] not in unit_ids:
        fail.append("join: unknown unit_id %s" % r["unit_id"])
    if r["relationship"] not in RELATIONSHIPS:
        fail.append("join: bad relationship %r" % r["relationship"])
    if r["confidence"] not in CONFIDENCE:
        fail.append("join: bad confidence %r" % r["confidence"])
    if not r["notes"].strip():
        fail.append("join: %s/%s has no note" % (r["option_id"], r["unit_id"]))

# 3, 4, 9, 10 ---------------------------------------------------------------
seen = set()
blank_process = 0
for r in elig:
    key = (r["unit_id"], r["carb3_activity"], r["process_id"])
    if key in seen:
        fail.append("unit_eligibility: duplicate key %s" % (key,))
    seen.add(key)
    if r["unit_id"] not in unit_ids:
        fail.append("unit_eligibility: unknown unit_id %s" % r["unit_id"])
    if r["carb3_activity"] not in activities:
        fail.append("unit_eligibility: unknown activity %s" % r["carb3_activity"])
    if r["process_id"] == "":
        blank_process += 1
        u = [x for x in units if x["unit_id"] == r["unit_id"]][0]
        if u["duty_family"] or u["spine"] != "service":
            fail.append("unit_eligibility: blank process_id on non-supply unit %s"
                        % r["unit_id"])
    elif (r["carb3_activity"], r["process_id"]) not in reg_keys:
        fail.append("unit_eligibility: (%s, %s) not in the register"
                    % (r["carb3_activity"], r["process_id"]))
    if r["provenance"] not in PROVENANCE:
        fail.append("unit_eligibility: bad provenance %r" % r["provenance"])
    for field in ("min_duty", "max_share"):
        if r[field]:
            try:
                v = float(r[field])
            except ValueError:
                fail.append("unit_eligibility: %s is not a number: %r" % (field, r[field]))
                continue
            if field == "max_share" and not 0.0 <= v <= 1.0:
                fail.append("unit_eligibility: max_share out of [0,1]: %r" % r[field])
    if r["earliest_year"] and not re.fullmatch(r"\d{4}", r["earliest_year"]):
        fail.append("unit_eligibility: bad earliest_year %r" % r["earliest_year"])
    if r["notes"].strip() == "":
        fail.append("unit_eligibility: %s has no note" % (key,))

# 5, 7, 8 -------------------------------------------------------------------
if len(aligned) != len(library):
    fail.append("aligned library has %d rows, the library has %d"
                % (len(aligned), len(library)))
orig_cols = list(library[0].keys())
new_cols = list(aligned[0].keys())
if new_cols[:len(orig_cols)] != orig_cols:
    fail.append("aligned library changed or reordered the original columns")
if new_cols[len(orig_cols):] != ["displaces_carrier_ids", "route_change",
                                 "exclusivity_group"]:
    fail.append("aligned library's added columns are wrong: %s"
                % new_cols[len(orig_cols):])
route_change_join = {r["option_id"] for r in join if r["relationship"] == "route_change"}
groups = {}
for a, o in zip(aligned, library):
    if a["option_id"] != o["option_id"]:
        fail.append("aligned library reordered rows at %s" % o["option_id"])
        continue
    for col in orig_cols:
        if a[col] != o[col]:
            fail.append("aligned library changed %s.%s" % (o["option_id"], col))
    for cid in (x for x in a["displaces_carrier_ids"].split(";") if x):
        if cid not in carrier_ids:
            fail.append("aligned library: unknown carrier_id %s on %s"
                        % (cid, a["option_id"]))
    if a["displaces_carrier_ids"] and not o["displaces"].strip():
        fail.append("aligned library: %s has carriers but a blank displaces"
                    % a["option_id"])
    if a["route_change"] not in ("TRUE", "FALSE"):
        fail.append("aligned library: route_change is not TRUE/FALSE on %s"
                    % a["option_id"])
    if (a["route_change"] == "TRUE") != (a["option_id"] in route_change_join):
        fail.append("aligned library: route_change disagrees with the join on %s"
                    % a["option_id"])
    if a["exclusivity_group"]:
        if not re.fullmatch(r"[a-z0-9_]+", a["exclusivity_group"]):
            fail.append("aligned library: exclusivity_group is not a slug on %s"
                        % a["option_id"])
        groups.setdefault(a["exclusivity_group"], []).append(a["option_id"])
for slug, members in groups.items():
    if len(members) < 2:
        fail.append("exclusivity group %s has one member: %s" % (slug, members))

# 6 -------------------------------------------------------------------------
pattern = re.compile(r"\[([A-Z0-9_]{2,24})\]")
for name, rows in (("join", join), ("unit_eligibility", elig)):
    for r in rows:
        for field in ("provenance", "provenance_ref", "notes"):
            for rid in pattern.findall(r.get(field, "")):
                if rid not in ref_ids:
                    fail.append("%s: [%s] does not resolve" % (name, rid))

# advisory ------------------------------------------------------------------
warn.append("join rows with a blank unit_id (unit requested): %d" % blank_unit)
warn.append("unit_eligibility rows with a blank process_id (supply units): %d"
            % blank_process)
by_prov = {}
for r in elig:
    by_prov[r["provenance"]] = by_prov.get(r["provenance"], 0) + 1
warn.append("unit_eligibility by provenance: %s" % sorted(by_prov.items()))
warn.append("unit_eligibility rows: %d over %d units and %d activities"
            % (len(elig), len({r["unit_id"] for r in elig}),
               len({r["carb3_activity"] for r in elig})))
never = sorted(unit_ids - {r["unit_id"] for r in elig})
warn.append("units with no eligibility row at all (%d): %s" % (len(never), never))

print("\n".join("note:  " + w for w in warn))
if fail:
    print("\n".join("FAIL:  " + f for f in sorted(set(fail))))
    print("\n%d blocking failure(s)" % len(set(fail)))
    sys.exit(1)
print("\nall blocking checks pass")
