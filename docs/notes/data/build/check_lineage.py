#!/usr/bin/env python3
"""Validator for docs/notes/data/comit_technology_lineage.csv (lane `lineage`).

Blocking checks, per the lane brief:
  1. exactly 397 rows
  2. technology_code unique, and the set equals emissions_source_classification.csv's
  3. every row has a disposition, from the four-value enum
  4. every unit_id resolves to unit.csv
  5. every carrier_id and fuel_carrier_id resolves to carrier.csv
  6. fuel_carrier_id equals the mapped unit's own fuel_carrier_id
  7. collapsed/preserved rows carry a unit_id; dropped/unmapped rows do not
  8. `collapsed` means the unit takes >1 source row, `preserved` exactly 1
  9. every unit_id used by either worked example's 1.11 table is reachable
 10. every row carries a reason
Then prints the disposition counts.

Stdlib only. Runs from any directory. Exit 0 = green.
"""
import csv
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.dirname(HERE)

LINEAGE = os.path.join(DATA, "comit_technology_lineage.csv")
ESC = os.path.join(DATA, "emissions_source_classification.csv")
UNIT = os.path.join(DATA, "unit.csv")
CARRIER = os.path.join(DATA, "carrier.csv")

DISPOSITIONS = {"collapsed", "preserved", "dropped", "unmapped"}

SPECS = os.path.join(os.path.dirname(os.path.dirname(DATA)), "specs")
WORKED_EXAMPLES = [
    os.path.join(SPECS, "2026-08-28-carb3-site-energy-system-worked-example-cement.md"),
    os.path.join(SPECS, "2026-08-28-carb3-site-energy-system-worked-example-food-drink.md"),
]

# Units a worked example names that legitimately have no COMIT ancestor, so the lineage
# cannot reach them. Anything outside this set that a worked example names and the lineage
# misses is a defect: V1b (parity against the frozen R run) would have nothing to compare.
NO_COMIT_ANCESTOR = {
    # supply-side plant COMIT's 397 technologies do not contain at all
    "pv_rooftop", "pv_ground_mount", "solar_thermal_flat", "battery_2h", "battery_4h",
    "thermal_store_hot_water", "thermal_store_steam", "anaerobic_digester",
    # new units added by the CaRB3 design, not a collapse of any COMIT row
    "heat_pump_lt_reject", "boiler_lt_oil", "boiler_lt_biomethane", "chp_biomethane_ccgt",
    # D13 fan-out siblings: one COMIT row splits into several units, and a lineage row can
    # carry only one unit_id, so the siblings appear in that row's `notes` fan-out instead
    "kiln_dry_gas", "kiln_dry_wdf", "kiln_dry_oil",
    "lime_kiln_dry_coal", "lime_kiln_dry_wdf",
}

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


def main():
    rows = list(csv.DictReader(open(LINEAGE, newline="")))
    esc = {r["technology_code"] for r in csv.DictReader(open(ESC, newline=""))}
    units = {r["unit_id"]: r for r in csv.DictReader(open(UNIT, newline=""))}
    carriers = {r["carrier_id"] for r in csv.DictReader(open(CARRIER, newline=""))}

    # 1 + 2
    check(len(rows) == 397, "row count is %d, expected 397" % len(rows))
    codes = [r["technology_code"] for r in rows]
    dupes = [c for c, n in Counter(codes).items() if n > 1]
    check(not dupes, "duplicate technology_code: %s" % dupes)
    check(set(codes) == esc,
          "technology_code set differs from emissions_source_classification.csv: "
          "missing %s / extra %s" % (sorted(esc - set(codes))[:5], sorted(set(codes) - esc)[:5]))

    used = Counter(r["unit_id"] for r in rows if r["unit_id"])

    for r in rows:
        code = r["technology_code"]
        d = r["disposition"]
        # 3
        check(d in DISPOSITIONS, "%s: disposition %r not in the enum" % (code, d))
        # 10
        check(r["reason"].strip(), "%s: empty reason" % code)
        # 5
        for col in ("carrier_id", "fuel_carrier_id"):
            v = r[col]
            check(not v or v in carriers, "%s: %s %r not in carrier.csv" % (code, col, v))
        if d in ("collapsed", "preserved"):
            # 7
            check(r["unit_id"], "%s: %s row has no unit_id" % (code, d))
            # 4
            check(r["unit_id"] in units, "%s: unit_id %r not in unit.csv" % (code, r["unit_id"]))
            if r["unit_id"] in units:
                # 6
                check(r["fuel_carrier_id"] == units[r["unit_id"]]["fuel_carrier_id"],
                      "%s: fuel_carrier_id %r != unit %s's %r"
                      % (code, r["fuel_carrier_id"], r["unit_id"],
                         units[r["unit_id"]]["fuel_carrier_id"]))
                # 8
                n = used[r["unit_id"]]
                check((d == "collapsed") == (n > 1),
                      "%s: disposition %s but unit %s takes %d source row(s)"
                      % (code, d, r["unit_id"], n))
        else:
            # 7
            check(not r["unit_id"], "%s: %s row carries unit_id %r" % (code, d, r["unit_id"]))
            check(not r["fuel_carrier_id"],
                  "%s: %s row carries fuel_carrier_id %r" % (code, d, r["fuel_carrier_id"]))

    # 9
    fan_out = set()
    for r in rows:
        for m in re.finditer(r"d13_fan_out=([a-z0-9_;]+)", r["notes"]):
            fan_out.update(m.group(1).split(";"))
    we_units = set()
    for path in WORKED_EXAMPLES:
        check(os.path.exists(path), "worked example not found: %s" % path)
        if not os.path.exists(path):
            continue
        text = open(path).read()
        we_units |= {u for u in units if re.search(r"\b%s\b" % re.escape(u), text)}
    unreached = sorted(u for u in we_units if used.get(u, 0) == 0)
    for u in unreached:
        check(u in NO_COMIT_ANCESTOR,
              "worked-example unit %s has no COMIT ancestor in the lineage and is not in the "
              "NO_COMIT_ANCESTOR allow-list" % u)
    for u in unreached:
        check(u not in fan_out or u in NO_COMIT_ANCESTOR,
              "D13 fan-out sibling %s is unreachable and unlisted" % u)

    counts = Counter(r["disposition"] for r in rows)
    print("comit_technology_lineage.csv: %d rows" % len(rows))
    for k in ("collapsed", "preserved", "dropped", "unmapped"):
        print("  %-10s %3d" % (k, counts.get(k, 0)))
    print("  %-10s %3d" % ("TOTAL", sum(counts.values())))
    print("distinct units reached: %d of %d in unit.csv" % (len(used), len(units)))
    print("worked-example units: %d named, %d unreachable (%s)"
          % (len(we_units), len(unreached), ", ".join(unreached) or "none"))

    if fails:
        print("\nFAIL (%d):" % len(fails))
        for f in fails:
            print("  - " + f)
        return 1
    print("\nOK - all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
