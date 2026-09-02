#!/usr/bin/env python3
"""Validate the hand-researched CaRB3 data tables in docs/notes/data/.

Seven files in that directory were built by parallel web research rather than by a
script. Their READMEs describe validation that was performed once, at assembly time,
by hand. Nothing repeated it. This script does.

Run it BEFORE any migration, on unmodified data, to establish a green baseline. A
failure afterwards is then unambiguously the migration's fault, which is the whole
diagnostic value. Without the baseline you cannot tell a broken key from one that was
never right.

    python3 docs/notes/examples/validate_carb3_data.py          # human output
    python3 docs/notes/examples/validate_carb3_data.py --quiet  # failures only
    python3 docs/notes/examples/validate_carb3_data.py --json   # machine output

Exit 0 if every BLOCKING check passes, 1 otherwise. ADVISORY checks report counts and
never change the exit code, following the spec's own "reported comparison, not
constraint" pattern (implementation spec section 6.3).

Standard library only, deliberately: pandas is not installed in this environment and
the repo has no Python dependency management.

The five files that reference each other, and on which keys:

    references.csv
      ref_id ◄─────────────── [REF_ID] tokens inside every `provenance` column
                                 │
    activity_process_register.csv     (376 rows, the spine)
      (carb3_activity, process_set_id, process_id)
          ▲                        ▲
          │                        │
          │  activity_process_energy_profile.csv  (490 rows)
          │    + vector  → energy_share must sum to 1.00 per (activity, set, vector)
          │
          │  process_decarbonisation_options.csv  (1109 rows)
          │    + option_id ──────────► decarbonisation_options_library.csv (134 rows)
          │                              option_id  (PK)

Two files carry no cross-references and are checked for shape only:
activity_profile_coverage_notes.csv and decarbonisation_options_challenges.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"

# Tolerance on the per-(activity, set, vector) share sum. The value comes from
# README_activity_process_tables.md, which states shares were assembled to sum to
# 1.00 within +/-0.015. Do not tighten it without re-reading that claim.
SHARE_TOL = 0.015

REF_TOKEN = re.compile(r"\[([A-Z0-9_]+)\]")

EXPECTED_COLUMNS = {
    "activity_process_register.csv": [
        "carb3_activity", "process_set_id", "set_name", "is_default", "process_id",
        "process_name", "is_optional", "equipment_examples", "provenance",
    ],
    "activity_process_energy_profile.csv": [
        "carb3_activity", "process_set_id", "process_id", "vector", "energy_share",
        "share_low", "share_high", "evidence_tier", "provenance", "confidence",
    ],
    "process_decarbonisation_options.csv": [
        "carb3_activity", "process_set_id", "process_id", "option_id", "trl",
        "applicability", "notes", "provenance", "confidence",
    ],
    "decarbonisation_options_library.csv": [
        "option_id", "option_name", "option_class", "displaces", "duty", "trl",
        "trl_basis", "key_constraints", "uk_status", "scope", "provenance", "confidence",
    ],
    "references.csv": ["ref_id", "title", "publisher", "year", "url", "accessed", "note"],
    "activity_profile_coverage_notes.csv": ["carb3_activity", "notes"],
    "decarbonisation_options_challenges.csv": ["scope", "challenge"],
}

ENUMS = {
    ("activity_process_energy_profile.csv", "vector"):
        {"biomass", "coal", "electricity", "gas", "oil", "other"},
    ("activity_process_energy_profile.csv", "evidence_tier"):
        {"engineering", "fallback", "published_sec", "metered"},
    ("activity_process_energy_profile.csv", "confidence"): {"high", "medium", "low"},
    ("process_decarbonisation_options.csv", "applicability"):
        {"commercial", "demonstration", "prospective", "speculative"},
    ("process_decarbonisation_options.csv", "confidence"): {"high", "medium", "low"},
    ("decarbonisation_options_library.csv", "option_class"):
        {"bioenergy", "ccs_ccu", "efficiency_heat_recovery", "electrification",
         "hydrogen", "mobile_plant", "other", "process_change"},
    ("decarbonisation_options_library.csv", "scope"): {"cross_cutting", "sector_specific"},
    ("decarbonisation_options_library.csv", "confidence"): {"high", "medium", "low"},
    ("activity_process_register.csv", "is_default"): {"TRUE", "FALSE"},
    ("activity_process_register.csv", "is_optional"): {"TRUE", "FALSE"},
}


class Result:
    """One check's outcome. `blocking` decides whether a failure fails the run."""

    def __init__(self, name: str, blocking: bool = True):
        self.name = name
        self.blocking = blocking
        self.failures: list[str] = []
        self.note = ""

    def fail(self, msg: str) -> None:
        self.failures.append(msg)

    @property
    def ok(self) -> bool:
        return not self.failures

    def as_dict(self) -> dict:
        return {
            "check": self.name,
            "blocking": self.blocking,
            "ok": self.ok,
            "failures": self.failures,
            "note": self.note,
        }


def read(name: str) -> list[dict]:
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def key(row: dict) -> tuple:
    return (row["carb3_activity"], row["process_set_id"], row["process_id"])


# --------------------------------------------------------------------------- checks

def check_shape(tables: dict[str, list[dict]]) -> Result:
    r = Result("file shape and columns")
    for name, expected in EXPECTED_COLUMNS.items():
        rows = tables.get(name)
        if rows is None:
            r.fail(f"{name}: missing or unreadable")
            continue
        if not rows:
            r.fail(f"{name}: no data rows")
            continue
        actual = list(rows[0].keys())
        if actual != expected:
            missing = [c for c in expected if c not in actual]
            extra = [c for c in actual if c not in expected]
            r.fail(f"{name}: columns differ (missing={missing}, unexpected={extra})")
    r.note = f"{len(EXPECTED_COLUMNS)} files"
    return r


def check_enums(tables: dict[str, list[dict]]) -> Result:
    r = Result("enum domains")
    for (fname, col), allowed in ENUMS.items():
        for i, row in enumerate(tables.get(fname, []), start=2):
            v = (row.get(col) or "").strip()
            if v and v not in allowed:
                r.fail(f"{fname}:{i} {col}={v!r} not in {sorted(allowed)}")
    r.note = f"{len(ENUMS)} columns"
    return r


def check_default_sets(reg: list[dict]) -> Result:
    """Exactly one default process set per activity (README_activity_process_tables)."""
    r = Result("one default process set per activity")
    sets_by_activity: dict[str, set[str]] = defaultdict(set)
    default_sets: dict[str, set[str]] = defaultdict(set)
    for row in reg:
        a = row["carb3_activity"]
        sets_by_activity[a].add(row["process_set_id"])
        if row["is_default"] == "TRUE":
            default_sets[a].add(row["process_set_id"])
    for a in sorted(sets_by_activity):
        n = len(default_sets.get(a, ()))
        if n != 1:
            r.fail(f"{a!r}: {n} default sets (expected exactly 1)")
    r.note = f"{len(sets_by_activity)} activities"
    return r


def check_register_keys_unique(reg: list[dict]) -> Result:
    r = Result("register keys unique")
    seen: dict[tuple, int] = {}
    for i, row in enumerate(reg, start=2):
        k = key(row)
        if k in seen:
            r.fail(f"row {i} duplicates row {seen[k]}: {k}")
        seen[k] = i
    r.note = f"{len(seen)} keys"
    return r


def check_share_sums(prof: list[dict]) -> Result:
    r = Result(f"energy_share sums to 1.00 +/-{SHARE_TOL} per (activity, set, vector)")
    sums: dict[tuple, float] = defaultdict(float)
    for i, row in enumerate(prof, start=2):
        try:
            sums[(row["carb3_activity"], row["process_set_id"], row["vector"])] += float(
                row["energy_share"]
            )
        except ValueError:
            r.fail(f"row {i}: energy_share={row['energy_share']!r} is not a number")
    for k, total in sorted(sums.items()):
        if abs(total - 1.0) > SHARE_TOL:
            r.fail(f"{k}: sums to {total:.4f}")
    r.note = f"{len(sums)} groups"
    return r


def check_share_bands(prof: list[dict]) -> Result:
    """R3 band ordering, and shares inside [0, 1]."""
    r = Result("share band ordering (low <= share <= high) and range")
    checked = 0
    for i, row in enumerate(prof, start=2):
        raw = (row["energy_share"], row["share_low"], row["share_high"])
        if any(v.strip() == "" for v in raw):
            continue
        try:
            share, lo, hi = (float(v) for v in raw)
        except ValueError:
            r.fail(f"row {i}: non-numeric band {raw}")
            continue
        checked += 1
        if not (lo <= share <= hi):
            r.fail(f"row {i}: {lo} <= {share} <= {hi} violated")
        if not (0.0 <= share <= 1.0):
            r.fail(f"row {i}: energy_share={share} outside [0, 1]")
    r.note = f"{checked} banded rows"
    return r


def check_profile_keys_resolve(prof: list[dict], reg: list[dict]) -> Result:
    r = Result("profile keys resolve to the register")
    known = {key(row) for row in reg}
    unresolved = {key(row) for row in prof} - known
    for k in sorted(unresolved):
        r.fail(f"no register row for {k}")
    r.note = f"{len({key(x) for x in prof})} distinct profile keys"
    return r


def check_option_keys_resolve(opt: list[dict], reg: list[dict]) -> Result:
    r = Result("option mapping keys resolve to the register")
    known = {key(row) for row in reg}
    unresolved = {key(row) for row in opt} - known
    for k in sorted(unresolved):
        r.fail(f"no register row for {k}")
    r.note = f"{len(opt)} mapping rows"
    return r


def check_option_ids_resolve(opt: list[dict], lib: list[dict]) -> Result:
    r = Result("option_id resolves to the library")
    known = {row["option_id"] for row in lib}
    for i, row in enumerate(opt, start=2):
        if row["option_id"] not in known:
            r.fail(f"row {i}: option_id={row['option_id']!r} not in library")
    r.note = f"{len(known)} library options"
    return r


def check_library_ids_unique(lib: list[dict]) -> Result:
    r = Result("library option_id unique")
    seen: dict[str, int] = {}
    for i, row in enumerate(lib, start=2):
        oid = row["option_id"]
        if oid in seen:
            r.fail(f"row {i} duplicates row {seen[oid]}: {oid!r}")
        seen[oid] = i
    r.note = f"{len(seen)} options"
    return r


def check_reference_ids_unique(refs: list[dict]) -> Result:
    r = Result("references ref_id unique")
    seen: dict[str, int] = {}
    for i, row in enumerate(refs, start=2):
        rid = row["ref_id"]
        if rid in seen:
            r.fail(f"row {i} duplicates row {seen[rid]}: {rid!r}")
        seen[rid] = i
    r.note = f"{len(seen)} references"
    return r


def check_citations_resolve(tables: dict[str, list[dict]], refs: list[dict]) -> Result:
    """Every [REF_ID] token in any provenance column resolves to references.csv."""
    r = Result("[REF_ID] citations resolve")
    known = {row["ref_id"] for row in refs}
    cited: set[str] = set()
    for fname, rows in tables.items():
        if fname == "references.csv":
            continue
        for i, row in enumerate(rows, start=2):
            for token in REF_TOKEN.findall(row.get("provenance", "") or ""):
                cited.add(token)
                if token not in known:
                    r.fail(f"{fname}:{i} cites [{token}], not in references.csv")
    r.note = f"{len(cited)} distinct ids cited of {len(known)} defined"
    return r


def check_coverage(reg: list[dict], prof: list[dict], opt: list[dict],
                   lib: list[dict]) -> Result:
    """ADVISORY. Gaps here are legitimate today; the point is that the counts are
    stable across a migration. A change in these numbers is a signal, not a failure."""
    r = Result("coverage counts (advisory)", blocking=False)
    reg_keys = {key(x) for x in reg}
    prof_keys = {key(x) for x in prof}
    opt_keys = {key(x) for x in opt}
    used = {x["option_id"] for x in opt}
    all_opts = {x["option_id"] for x in lib}
    r.note = (
        f"register={len(reg_keys)} "
        f"no-profile={len(reg_keys - prof_keys)} "
        f"no-option={len(reg_keys - opt_keys)} "
        f"library-unused={len(all_opts - used)}"
    )
    return r


def check_band_coverage(prof: list[dict]) -> Result:
    """ADVISORY, and the most surprising number this script reports.

    R3 (band ordering) is asserted at load scope by V4, but only a small minority of
    profile rows carry `share_low`/`share_high` at all, so R3 barely runs. An unbanded
    share is a point estimate presented without its uncertainty, which is exactly the
    systematic-error problem implementation spec section 3.3.5 warns about. Reported
    rather than enforced, because backfilling bands is a research task and not a
    correctness bug."""
    r = Result("uncertainty band coverage (advisory)", blocking=False)
    banded = sum(
        1 for row in prof
        if row["share_low"].strip() and row["share_high"].strip()
    )
    half = sum(
        1 for row in prof
        if bool(row["share_low"].strip()) != bool(row["share_high"].strip())
    )
    pct = 100.0 * banded / len(prof) if prof else 0.0
    r.note = f"{banded}/{len(prof)} rows banded ({pct:.0f}%), {half} half-banded"
    if half:
        r.fail(f"{half} rows have one bound but not the other")
    return r


# ----------------------------------------------------------------------------- main

def run() -> tuple[list[Result], dict[str, list[dict]]]:
    names = list(EXPECTED_COLUMNS)
    tables: dict[str, list[dict]] = {}
    load_errors: list[str] = []
    for n in names:
        try:
            tables[n] = read(n)
        except FileNotFoundError:
            load_errors.append(f"{n}: not found in {DATA}")
        except Exception as exc:  # noqa: BLE001 - report, do not crash
            load_errors.append(f"{n}: {exc}")

    shape = check_shape(tables)
    for e in load_errors:
        shape.fail(e)
    if load_errors:
        return [shape], tables

    reg = tables["activity_process_register.csv"]
    prof = tables["activity_process_energy_profile.csv"]
    opt = tables["process_decarbonisation_options.csv"]
    lib = tables["decarbonisation_options_library.csv"]
    refs = tables["references.csv"]

    return [
        shape,
        check_enums(tables),
        check_default_sets(reg),
        check_register_keys_unique(reg),
        check_share_sums(prof),
        check_share_bands(prof),
        check_profile_keys_resolve(prof, reg),
        check_option_keys_resolve(opt, reg),
        check_option_ids_resolve(opt, lib),
        check_library_ids_unique(lib),
        check_reference_ids_unique(refs),
        check_citations_resolve(tables, refs),
        check_coverage(reg, prof, opt, lib),
        check_band_coverage(prof),
    ], tables


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--quiet", action="store_true", help="print failures only")
    ap.add_argument("--max-failures", type=int, default=10,
                    help="failures shown per check (default 10)")
    args = ap.parse_args(argv)

    results, _ = run()
    blocking_failed = [r for r in results if r.blocking and not r.ok]

    if args.json:
        print(json.dumps({
            "ok": not blocking_failed,
            "checks": [r.as_dict() for r in results],
        }, indent=2))
        return 1 if blocking_failed else 0

    for r in results:
        if r.ok:
            if not args.quiet:
                tag = "PASS" if r.blocking else "----"
                print(f"  {tag}  {r.name}" + (f"  ({r.note})" if r.note else ""))
            continue
        tag = "FAIL" if r.blocking else "WARN"
        print(f"  {tag}  {r.name}  ({len(r.failures)} problems)")
        for msg in r.failures[: args.max_failures]:
            print(f"          {msg}")
        if len(r.failures) > args.max_failures:
            print(f"          ... and {len(r.failures) - args.max_failures} more")

    if blocking_failed:
        print(f"\nFAILED: {len(blocking_failed)} blocking check(s). "
              f"CaRB3 data is not consistent.")
        return 1
    # Always confirm success, even in --quiet. A check that prints nothing is
    # indistinguishable from a check that did not run.
    n = sum(1 for r in results if r.blocking)
    print(f"\nCaRB3 data is consistent ({n} blocking checks passed)."
          if not args.quiet else
          f"CaRB3 data is consistent ({n} blocking checks passed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
