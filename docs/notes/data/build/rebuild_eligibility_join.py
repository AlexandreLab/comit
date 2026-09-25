#!/usr/bin/env python3
"""Rebuild the family rows of `unit_eligibility.csv` from the join (note 22 Task 10).

Stdlib only (pandas is not installed in this repo). Idempotent: run it after any change to
the duty profile, the unit library or the carriers, then `make data-check` and
`make data-worklist`.

What it replaces
----------------
`build_eligibility.py` step (c) offered every service unit of a duty family to every
register process its own `PROCESS_FAMILIES` table gave that family, with no grade filter
and no coefficient check: 1,852 `proxy` rows, written before the duty profile or any
`grade_out` existed. This script drops every `proxy` row and writes the family rows again
from the tables as they now stand. Rows with any other provenance — the worked examples
(`comit_reuse`), the options join (`bref`), the chemistry nodes (`comit_reuse`) and the
activity-level supply rows — are evidence, and are kept untouched.

The join
--------
A unit is offered at `(carb3_activity, process_id)` when, for at least one duty row there:

1. **Family.** The unit's `duty_family` is the row's, as the proxy had it — or, for a row
   on a non-gradeable service carrier (`motive_power`, `electric_service`), the unit's
   `primary_output` is that carrier whatever its family, which is how `motor_elec` reaches
   an `OTH` row whose service is motive power. Families that deliver heat through the same
   medium serve one another, by grade: `LTH`, `SPC` and `STM` are all hot water or steam
   from a boiler, heat pump or CHP — the `STM` family has no plain boiler, and a steam duty
   at rank 3 is what `boiler_lt_gas` (heat_100_150) makes — and `HTH` units serve `PHEAT`
   rows, both being fired process heat (§3.4 lists `PHEAT` with the heat families; note 22
   §5 names `furnace_ht_hydrogen` for the refinery's rank-5 `PHEAT` rows, and the options
   join already admits it at the refinery's other `PHEAT` processes). `DRY` (hot air in
   contact with the product) and `HTH` (furnaces) are not offered to the wet families.
   **Grade family** too: for a graded duty the unit's primary output is in the duty
   carrier's `grade_family` (§3.4) — heat for heat, cooling for cooling, never across.
2. **Grade, in C10's direction** (the grade cascade, §5.5): `grade_out` at or above the
   duty's rank for heat, at or below it for cooling (rank 1 is the coldest band). This is
   V19 (no unit eligible beyond its `grade_out`) applied at the source.
3. **Costable and runnable.** Every §3.2 cost field is filled, the unit has a
   `primary_output` row, a declared `fuel_carrier_id` has its `fuel_input` row — the unit
   leg of the admission screen — and every `intermediate` carrier the unit draws is
   produced, under some output role, by a unit eligible somewhere at the same activity
   (C8, the carrier balance, is per premise). A heat pump on reject heat is not offered
   where nothing rejects heat. A unit driven only by heat cannot deliver a hotter band than
   it draws: `dryer_steam` makes heat_150_400 from heat_100_150 at 1:1 with no work input,
   a free grade-up, and is withheld until its coefficients are fixed (note 20 item 64).
4. **Scope.** A generic service unit (`spine` = service, blank `process_id`) is offered
   wherever it serves. A service unit keyed to a process is node-keyed like a chemistry unit
   (D5) and keeps its reach: it is re-joined only at the `(activity, process)` pairs its
   rows already name (`refinery_process_heat_gas` at the refinery, `engine_mot_gas` at the
   three gas-only `OTH` motive rows, note 20 item 65), and a keyed unit whose primary output is a `product`
   (the two rolling mills) keeps its rows verbatim, since no duty row names its product and
   its process is a node (§3.9).

**Why the family stays.** Grade alone would offer a direct-fired dryer or a furnace to a
hot-water duty, because C10 sees only temperature, not the medium — a dryer heats air in
contact with the product and cannot fill an LPHW circuit. The family keeps the medium;
eligibility is per process, so at a process with both an `LTH` and an `STM` row the two
families' units are both offered and C10 in A3 decides which duty each may serve.

Two kinds of process are skipped, because offering a service unit there would be a
stand-in, which the task forbids:

* a **chemistry node** (`PROCESS_FAMILIES` marks it `CHEMISTRY`, or `HRS` for hot rolling):
  its duty rows classify the node's energy need (§3.9) and its units are node-keyed (D5);
  where the node has no unit the gap is note 20 item 30's, not a furnace's;
* **diesel mobile plant** (`NRMM`) for its `MOT` rows: a stationary electric motor is not a
  loader or a haul truck, and the library has no mobile-plant unit (note 20 item 30).
"""

import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from build_eligibility import CHEMISTRY, NRMM, PROCESS_FAMILIES  # noqa: E402

COST_FIELDS = ("capex", "lifetime", "fixed_opex", "availability_factor",
               "capacity_to_activity_factor")
INPUT_ROLES = {"fuel_input", "aux_input", "emission_input"}
CHEMISTRY_MARKERS = {CHEMISTRY, "HRS"}
COLUMNS = ["unit_id", "carb3_activity", "process_id", "min_duty", "max_share",
           "earliest_year", "provenance", "notes", "provenance_ref"]
STAMP = "note 22 Task 10, 2026-09-25"


def read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    carriers = {c["carrier_id"]: c for c in read("carrier.csv")}
    units = read("unit.csv")
    io = read("unit_input_output.csv")
    duty = read("activity_process_duty_profile.csv")
    elig = read("unit_eligibility.csv")

    def family(cid):
        c = carriers.get(cid)
        if c is None or c["is_gradeable"] != "TRUE":
            return None
        return c["grade_family"]

    def rank(cid):
        return int(carriers[cid]["grade_rank"])

    io_by = defaultdict(list)
    for r in io:
        io_by[r["unit_id"]].append(r)
    primary = {u: next((r["carrier_id"] for r in rows if r["role"] == "primary_output"), None)
               for u, rows in io_by.items()}
    makes = {u: {r["carrier_id"] for r in rows if r["role"] not in INPUT_ROLES}
             for u, rows in io_by.items()}
    draws = {u: {r["carrier_id"] for r in rows if r["role"] in INPUT_ROLES
                 and carriers[r["carrier_id"]]["carrier_kind"] == "intermediate"}
             for u, rows in io_by.items()}

    def grade_up_without_work(u):
        rows = io_by[u["unit_id"]]
        heat_in = [r for r in rows
                   if r["role"] in INPUT_ROLES and family(r["carrier_id"]) == "heat"]
        other_in = [r for r in rows
                    if r["role"] in INPUT_ROLES and family(r["carrier_id"]) is None
                    and carriers[r["carrier_id"]]["carrier_kind"] != "emission"]
        if not heat_in or other_in or u["draws_ambient"] == "TRUE" or not u["grade_out"].strip():
            return False
        return int(u["grade_out"]) > max(rank(r["carrier_id"]) for r in heat_in)

    def costable(u):
        uid = u["unit_id"]
        if any(not u[c].strip() for c in COST_FIELDS) or not primary.get(uid):
            return False
        fc = u["fuel_carrier_id"].strip()
        return not fc or any(r["role"] == "fuel_input" for r in io_by[uid])

    service = [u for u in units if u["spine"] == "service" and costable(u)
               and not grade_up_without_work(u)]
    withheld_physics = sorted(u["unit_id"] for u in units if u["spine"] == "service"
                              and costable(u) and grade_up_without_work(u))
    keyed = {u["unit_id"] for u in units if u["spine"] == "service" and u["process_id"].strip()}
    keyed_product = {uid for uid in keyed
                     if carriers.get(primary.get(uid) or "", {}).get("carrier_kind") == "product"}
    scope = defaultdict(set)  # keyed unit -> the (activity, process) pairs its rows reach
    for r in elig:
        if r["unit_id"] in keyed:
            scope[r["unit_id"]].add((r["carb3_activity"], r["process_id"]))
    candidates = [u for u in service if u["unit_id"] not in keyed_product]

    wet = {"LTH", "SPC", "STM"}
    cross_family = {f: wet - {f} for f in wet}
    cross_family["PHEAT"] = {"HTH"}

    def serves(u, row):
        uid, cid = u["unit_id"], row["carrier_id"]
        out = primary[uid]
        fam = family(cid)
        if fam is None:
            return out == cid
        uf, df = u["duty_family"], row["duty_family"]
        if uf != df and uf not in cross_family.get(df, set()):
            return False
        if family(out) != fam or not u["grade_out"].strip():
            return False
        g, need = int(u["grade_out"]), int(row["grade_rank"])
        return g <= need if fam == "cooling" else g >= need

    kept = [r for r in elig if r["provenance"] != "proxy" or r["unit_id"] in keyed_product]
    dropped = len(elig) - len(kept)
    kept_keys = {(r["unit_id"], r["carb3_activity"], r["process_id"]) for r in kept}

    # offers[(unit, activity, process)] = the duty rows it serves there
    offers = defaultdict(list)
    skipped = defaultdict(set)
    for row in duty:
        a, p, f = row["carb3_activity"], row["process_id"], row["duty_family"]
        markers = set(PROCESS_FAMILIES.get(p, []))
        if markers & CHEMISTRY_MARKERS:
            skipped["chemistry node"].add((a, p))
            continue
        if NRMM in markers and f == "MOT":
            skipped["diesel mobile plant"].add((a, p))
            continue
        for u in candidates:
            if u["unit_id"] in keyed and (a, p) not in scope[u["unit_id"]]:
                continue
            if serves(u, row):
                offers[(u["unit_id"], a, p)].append(row)

    # Leg 3's draw test, to a fixed point: a unit whose intermediate input nothing at the
    # activity produces is withdrawn, which may starve another unit in turn.
    kept_by_activity = defaultdict(set)
    for r in kept:
        kept_by_activity[r["carb3_activity"]].add(r["unit_id"])
    starved = {}
    while True:
        at = defaultdict(set)
        for (uid, a, _p) in offers:
            at[a].add(uid)
        produced = {a: set().union(*(makes.get(x, set()) for x in at[a] | kept_by_activity[a]))
                    for a in set(at) | set(kept_by_activity)}
        drop = [k for k in offers if draws.get(k[0], set()) - produced.get(k[1], set())]
        if not drop:
            break
        for k in drop:
            starved[k] = sorted(draws[k[0]] - produced.get(k[1], set()))
            del offers[k]

    new_rows = []
    for (uid, a, p), rows in offers.items():
        if (uid, a, p) in kept_keys:
            continue
        u = next(x for x in units if x["unit_id"] == uid)
        served = "; ".join(sorted({
            f"{r['duty_family']} on {r['carrier_id']}"
            + (f" (rank {r['grade_rank']})" if r["grade_rank"] else "") for r in rows}))
        how = (f"grade_out {u['grade_out']} reaches it under C10 (the grade cascade)"
               if u["grade_out"].strip() else f"its primary output is {primary[uid]}")
        new_rows.append({
            "unit_id": uid, "carb3_activity": a, "process_id": p,
            "min_duty": "", "max_share": "", "earliest_year": "", "provenance": "proxy",
            "notes": (f"Rebuilt from the join ({STAMP}): serves {served}; {how}. Carrier "
                      "family, grade in C10's direction, costed with coefficients, every "
                      "intermediate input produced at the activity - see "
                      "build/rebuild_eligibility_join.py."),
            "provenance_ref": "[CARB3_SPEC_IMPL]",
        })

    out = kept + new_rows
    out.sort(key=lambda r: (r["unit_id"], r["carb3_activity"], r["process_id"]))
    with open(os.path.join(DATA, "unit_eligibility.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\r\n")
        w.writeheader()
        w.writerows(out)

    print(f"unit_eligibility.csv: {len(out)} rows = {len(kept)} kept (evidence) + "
          f"{len(new_rows)} rebuilt from the join; {dropped} proxy rows dropped")
    print(f"candidate units: {len(candidates)}")
    print("withheld, heat-driven and delivering hotter than it draws: "
          + ", ".join(withheld_physics))
    for why, keys in sorted(skipped.items()):
        print(f"skipped, {why}: {len(keys)} (activity, process) pairs")
    by_unit = defaultdict(int)
    for (uid, _a, _p), carriers_missing in starved.items():
        by_unit[(uid, tuple(carriers_missing))] += 1
    for (uid, miss), n in sorted(by_unit.items()):
        print(f"withheld, draws {', '.join(miss)} that nothing at the activity makes: "
              f"{uid} at {n} processes")


if __name__ == "__main__":
    main()
