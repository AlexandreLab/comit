#!/usr/bin/env python3
"""Validate docs/notes/data/process_load_shape.csv against CaRB3 spec §3.13.

Stdlib only. Run from anywhere:  python3 docs/notes/data/build/check_loadshape.py
Exit status 0 = clean.
"""
import csv
import re
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1]
REG = DATA / "activity_process_register.csv"
SHAPE = DATA / "process_load_shape.csv"
REFS = [DATA / "references.csv", DATA / "build" / "references_loadshape.csv"]

CLASSES = {"flat", "throughput_following", "batch_cyclic", "intermittent", "standing", "seasonal"}
SEASONS = {"none", "winter_weighted", "summer_weighted", "campaign"}
BOOLS = {"TRUE", "FALSE"}
COLS = ["carb3_activity", "shape_id", "process_id", "shape_class", "duty_factor",
        "peak_to_mean", "runs_when_idle", "seasonality", "provenance", "confidence"]

# The two worked examples' §1.10 tables — every (activity, process_id, shape_class,
# runs_when_idle, seasonality) they state must still hold here.
WORKED_EXAMPLES = [
    ("Cement Works", "quarrying_crushing", "throughput_following", "FALSE", "none"),
    ("Cement Works", "raw_grinding_blending", "throughput_following", "FALSE", "none"),
    ("Cement Works", "raw_meal_homogenisation", "standing", "TRUE", "none"),
    ("Cement Works", "kiln_pyroprocessing", "flat", "FALSE", "none"),
    ("Cement Works", "clinker_cooling", "flat", "FALSE", "none"),
    ("Cement Works", "cement_grinding", "throughput_following", "FALSE", "none"),
    ("Cement Works", "packing_dispatch", "intermittent", "FALSE", "none"),
    ("Cement Works", "site_services", "standing", "TRUE", "none"),
    ("Food Processing Centre", "boiler_steam_hot_water", "batch_cyclic", "FALSE", "none"),
    ("Food Processing Centre", "direct_heating", "flat", "FALSE", "none"),
    ("Food Processing Centre", "refrigeration", "standing", "TRUE", "summer_weighted"),
    ("Food Processing Centre", "machinery_motors", "throughput_following", "FALSE", "none"),
    ("Food Processing Centre", "compressed_air", "throughput_following", "FALSE", "none"),
    ("Food Processing Centre", "site_services", "standing", "TRUE", "none"),
]


def slug(text):
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text.lower())).strip("_")


def main():
    fail = []
    rows = list(csv.DictReader(SHAPE.open(newline="")))
    reg = list(csv.DictReader(REG.open(newline="")))
    refs = set()
    for path in REFS:
        if path.exists():
            refs |= {r["ref_id"] for r in csv.DictReader(path.open(newline=""))}

    # 1. columns
    if list(rows[0].keys()) != COLS:
        fail.append(f"columns are {list(rows[0].keys())}, expected {COLS}")

    # 2. one row per register (activity, process), no extras
    want = {(r["carb3_activity"], r["process_id"]) for r in reg}
    got = [(r["carb3_activity"], r["process_id"]) for r in rows]
    for k in sorted(want - set(got)):
        fail.append(f"register pair with no shape row: {k}")
    for k in sorted(set(got) - want):
        fail.append(f"shape row with no register pair: {k}")
    for k in sorted({k for k in got if got.count(k) > 1}):
        fail.append(f"duplicate shape row: {k}")

    # 3. shape_id unique and well formed
    ids = [r["shape_id"] for r in rows]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        fail.append(f"duplicate shape_id: {i}")
    for r in rows:
        expect = f"{slug(r['carb3_activity'])}__{r['process_id']}"
        if r["shape_id"] != expect:
            fail.append(f"shape_id {r['shape_id']} should be {expect}")

    # 4. enums, booleans, blanks, the §3.13 standing rule
    for r in rows:
        tag = f"{r['carb3_activity']}/{r['process_id']}"
        if r["shape_class"] not in CLASSES:
            fail.append(f"{tag}: bad shape_class {r['shape_class']!r}")
        if r["seasonality"] not in SEASONS:
            fail.append(f"{tag}: bad seasonality {r['seasonality']!r}")
        if r["runs_when_idle"] not in BOOLS:
            fail.append(f"{tag}: bad runs_when_idle {r['runs_when_idle']!r}")
        if r["confidence"] not in {"high", "medium", "low"}:
            fail.append(f"{tag}: bad confidence {r['confidence']!r}")
        if (r["shape_class"] == "standing") != (r["runs_when_idle"] == "TRUE"):
            fail.append(f"{tag}: §3.13 rule — standing iff runs_when_idle TRUE "
                        f"({r['shape_class']}, {r['runs_when_idle']})")
        for col in ("duty_factor", "peak_to_mean"):
            v = r[col]
            if v == "":
                continue
            try:
                x = float(v)
            except ValueError:
                fail.append(f"{tag}: {col} {v!r} is not a number")
                continue
            if col == "duty_factor" and not (0 < x <= 1):
                fail.append(f"{tag}: duty_factor {x} outside (0, 1]")
            if col == "peak_to_mean" and x < 1:
                fail.append(f"{tag}: peak_to_mean {x} below 1")
        for col, v in r.items():
            if v.strip() in {"NA", "n/a", "N/A", "-", "?", "null", "None"}:
                fail.append(f"{tag}: {col} uses a placeholder blank {v!r}")
        if not r["provenance"].strip():
            fail.append(f"{tag}: empty provenance")
        for ref_id in re.findall(r"\[([A-Za-z0-9_\-]+)\]", r["provenance"]):
            if ref_id not in refs:
                fail.append(f"{tag}: unresolved [{ref_id}]")

    # 5. the worked examples still resolve
    index = {(r["carb3_activity"], r["process_id"]): r for r in rows}
    for act, pid, cls, idle, season in WORKED_EXAMPLES:
        r = index.get((act, pid))
        if r is None:
            fail.append(f"worked example row missing: {act}/{pid}")
            continue
        if (r["shape_class"], r["runs_when_idle"], r["seasonality"]) != (cls, idle, season):
            fail.append(f"worked example mismatch {act}/{pid}: "
                        f"{r['shape_class']}/{r['runs_when_idle']}/{r['seasonality']} "
                        f"vs {cls}/{idle}/{season}")

    if fail:
        print(f"FAIL ({len(fail)}):")
        print("\n".join("  - " + f for f in fail))
        return 1
    print(f"OK — {len(rows)} rows, {len({r['carb3_activity'] for r in rows})} activities, "
          f"all enums valid, standing rule holds, all [REF_ID]s resolve, "
          f"both worked examples' §1.10 tables reproduce.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
