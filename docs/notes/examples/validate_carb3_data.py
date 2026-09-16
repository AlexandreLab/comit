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
        "displaces_carrier_ids", "route_change", "exclusivity_group",
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
            cited_text = (row.get("provenance", "") or "") + " " + (row.get("provenance_ref", "") or "")
            for token in REF_TOKEN.findall(cited_text):
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


# ------------------------------------------------- the spec-section-3 entities (2026-09-15)
#
# The tables below populate the live specification's data model directly (section 3 of
# 2026-08-28-carb3-site-energy-system-implementation.md). Each carries the spec's own
# columns plus, where the build needed it, `provenance_ref` / `notes` / a disambiguating
# key column. `activity_default_unit.csv` is OPTIONAL: absent means T18 has not landed,
# and the run reports that rather than failing.

SPEC_COLUMNS = {
    "carrier.csv": [
        "carrier_id", "carrier_name", "carrier_kind", "is_gradeable", "grade_rank",
        "grade_label", "is_indirect", "emission_factor_source", "biogenic_fraction",
        "carbon_charge", "denominator_kind", "may_dispose", "vector", "comit_commodity",
        "provenance",
    ],
    "activity_process_duty_profile.csv": [
        "carb3_activity", "process_set_id", "process_id", "duty_family", "carrier_id",
        "grade_rank", "duty_share", "share_low", "share_high", "evidence_tier",
        "provenance", "confidence",
    ],
    "carb3_comit_process_crosswalk.csv": [
        "carb3_activity", "process_set_id", "process_id", "comit_process_code",
        "match_kind", "notes",
    ],
    "unit.csv": [
        "unit_id", "unit_name", "unit_class", "spine", "duty_family", "process_id",
        "fuel_carrier_id", "grade_out", "grade_in_max", "capex", "fixed_opex", "lifetime",
        "availability_factor", "capacity_to_activity_factor", "area_per_capacity",
        "emissions_released", "min_viable_scale", "load_shape_override", "is_hybrid",
        "draws_ambient", "abates_unit_id", "provenance", "confidence", "provenance_ref",
    ],
    "unit_input_output.csv": [
        "unit_id", "carrier_id", "coefficient", "role",
        "provenance", "confidence", "provenance_ref",
    ],
    "unit_bill_of_materials.csv": [
        "unit_id", "component_id", "capacity_share", "capex_share", "component_lifetime",
        "replacements_in_life", "provenance", "provenance_ref",
    ],
    "unit_eligibility.csv": [
        "unit_id", "carb3_activity", "process_id", "min_duty", "max_share",
        "earliest_year", "provenance", "notes", "provenance_ref",
    ],
    "decarbonisation_option_unit.csv": [
        "option_id", "unit_id", "relationship", "notes", "provenance", "confidence",
    ],
    "comit_technology_lineage.csv": [
        "technology_code", "technology_name", "sector", "technology_category",
        "output_commodity", "carrier_id", "unit_type", "abatement", "disposition",
        "unit_id", "fuel_carrier_id", "reason", "notes",
    ],
    "process_load_shape.csv": [
        "carb3_activity", "shape_id", "process_id", "shape_class", "duty_factor",
        "peak_to_mean", "runs_when_idle", "seasonality", "provenance", "confidence",
    ],
    "scenario_parameters.csv": [
        "parameter_id", "carrier_id", "period", "value", "unit", "provenance", "confidence",
    ],
    "infrastructure_scenario.csv": [
        "scenario_id", "carrier", "cluster_id", "period", "available", "capacity_limit",
        "unit_tariff", "provenance",
    ],
}
OPTIONAL_SPEC_COLUMNS = {
    "activity_default_unit.csv": [
        "carb3_activity", "process_set_id", "process_id", "duty_family", "unit_id",
        "default_share", "sizing_basis", "evidence_tier", "provenance", "confidence",
    ],
}

DUTY_FAMILIES = {"DRY", "EN", "HRS", "HTH", "LTH", "MOT", "NEUOTH", "OTH", "PHEAT", "REF",
                 "SPC", "STM"}
SPEC_ENUMS = {
    ("carrier.csv", "carrier_kind"): {"primary", "intermediate", "product", "emission"},
    ("carrier.csv", "carbon_charge"): {"charged", "zero_rated"},
    ("carrier.csv", "denominator_kind"): {"energy", "mass"},
    ("carrier.csv", "vector"): {"biomass", "coal", "electricity", "gas", "oil", "other"},
    ("activity_process_duty_profile.csv", "duty_family"): DUTY_FAMILIES,
    ("activity_process_duty_profile.csv", "evidence_tier"):
        {"measured", "engineering", "published_sec", "fallback"},
    ("activity_process_duty_profile.csv", "confidence"): {"high", "medium", "low"},
    ("carb3_comit_process_crosswalk.csv", "match_kind"): {"direct", "analogue", "none"},
    ("unit.csv", "unit_class"): {"converter", "generator", "storage", "hybrid", "abatement"},
    ("unit.csv", "spine"): {"service", "chemistry"},
    ("unit.csv", "duty_family"): DUTY_FAMILIES,
    ("unit.csv", "provenance"): {"comit_reuse", "bref", "proxy"},
    ("unit.csv", "confidence"): {"high", "medium", "low"},
    ("unit_eligibility.csv", "provenance"): {"comit_reuse", "bref", "proxy"},
    ("decarbonisation_option_unit.csv", "relationship"):
        {"is_unit", "enables", "route_change", "supply", "none"},
    ("comit_technology_lineage.csv", "disposition"):
        {"collapsed", "preserved", "dropped", "unmapped"},
    ("process_load_shape.csv", "shape_class"):
        {"flat", "throughput_following", "batch_cyclic", "intermittent", "standing",
         "seasonal"},
    ("process_load_shape.csv", "seasonality"):
        {"none", "winter_weighted", "summer_weighted", "campaign"},
    ("infrastructure_scenario.csv", "carrier"): {"hydrogen", "co2_transport", "grid_headroom"},
    ("activity_default_unit.csv", "sizing_basis"): {"duty_annual", "duty_peak", "throughput"},
    ("activity_default_unit.csv", "evidence_tier"): {"sector_statistic", "derived", "assumed"},
    ("unit_input_output.csv", "role"): {
        "fuel_input", "aux_input", "emission_input",
        "primary_output", "coproduct", "reject", "emission",
    },
}
BOOL_COLUMNS = {
    ("carrier.csv", "is_gradeable"), ("carrier.csv", "is_indirect"),
    ("carrier.csv", "may_dispose"), ("unit.csv", "is_hybrid"), ("unit.csv", "draws_ambient"),
    ("process_load_shape.csv", "runs_when_idle"),
    ("infrastructure_scenario.csv", "available"),
    ("decarbonisation_options_library.csv", "route_change"),
}


def _f(v: str) -> float | None:
    v = (v or "").strip()
    return float(v) if v else None


def check_spec_shape(tables: dict[str, list[dict]]) -> Result:
    r = Result("spec §3 tables: shape, enums, booleans")
    for name, expected in list(SPEC_COLUMNS.items()) + list(OPTIONAL_SPEC_COLUMNS.items()):
        rows = tables.get(name)
        if rows is None:
            if name in OPTIONAL_SPEC_COLUMNS:
                continue
            r.fail(f"{name}: missing or unreadable")
            continue
        actual = list(rows[0].keys()) if rows else []
        if actual != expected:
            r.fail(f"{name}: columns differ (missing={[c for c in expected if c not in actual]}, "
                   f"unexpected={[c for c in actual if c not in expected]})")
    for (fname, col), allowed in SPEC_ENUMS.items():
        for i, row in enumerate(tables.get(fname, []), start=2):
            v = (row.get(col) or "").strip()
            if v and v not in allowed:
                r.fail(f"{fname}:{i} {col}={v!r} not in {sorted(allowed)}")
    for fname, col in BOOL_COLUMNS:
        for i, row in enumerate(tables.get(fname, []), start=2):
            v = (row.get(col) or "").strip()
            if v not in {"TRUE", "FALSE", ""}:
                r.fail(f"{fname}:{i} {col}={v!r} is not TRUE/FALSE")
    present = [n for n in OPTIONAL_SPEC_COLUMNS if n in tables]
    r.note = f"{len(SPEC_COLUMNS)} required, optional present: {present or 'none'}"
    return r


def check_carrier(car: list[dict]) -> Result:
    """§3.4: grades need a rank and a label; emissions carry a charge; may_dispose is
    derived from carrier_kind (true for intermediate and emission only)."""
    r = Result("carrier: grades, charges, may_dispose")
    seen: set[str] = set()
    ranks: dict[int, str] = {}
    for i, row in enumerate(car, start=2):
        cid = row["carrier_id"]
        if cid in seen:
            r.fail(f"row {i}: duplicate carrier_id {cid}")
        seen.add(cid)
        kind = row["carrier_kind"]
        gradeable = row["is_gradeable"] == "TRUE"
        if gradeable and not (row["grade_rank"].strip() and row["grade_label"].strip()):
            r.fail(f"{cid}: gradeable without grade_rank/grade_label")
        if gradeable:
            rk = int(row["grade_rank"])
            if rk in ranks:
                r.fail(f"{cid}: grade_rank {rk} already used by {ranks[rk]}")
            ranks[rk] = cid
        if kind == "emission" and not row["carbon_charge"].strip():
            r.fail(f"{cid}: emission carrier without carbon_charge")
        if kind != "emission" and row["carbon_charge"].strip():
            r.fail(f"{cid}: carbon_charge set on a non-emission carrier")
        want = "TRUE" if kind in {"intermediate", "emission"} else "FALSE"
        if row["may_dispose"] != want:
            r.fail(f"{cid}: may_dispose should be {want} for kind {kind}")
        if kind == "primary" and not row["emission_factor_source"].strip():
            r.fail(f"{cid}: primary carrier without emission_factor_source")
        b = _f(row["biogenic_fraction"])
        if b is not None and not 0 <= b <= 1:
            r.fail(f"{cid}: biogenic_fraction {b} outside [0,1]")
    r.note = f"{len(seen)} carriers, {len(ranks)} heat grades"
    return r


def check_duty_profile(duty: list[dict], reg: list[dict], car: list[dict]) -> Result:
    """§3.3: keys resolve, shares sum to 1 per (activity, set, process), a heat duty
    has a grade and the grade agrees with the carrier's own rank."""
    r = Result("duty profile: keys, share sums, heat grades")
    reg_keys = {key(x) for x in reg}
    carriers = {c["carrier_id"]: c for c in car}
    sums: dict[tuple, float] = defaultdict(float)
    covered: set[tuple] = set()
    for i, row in enumerate(duty, start=2):
        k = key(row)
        if k not in reg_keys:
            r.fail(f"row {i}: {k} not in register")
        covered.add(k)
        c = carriers.get(row["carrier_id"])
        if c is None:
            if row["duty_family"] != "NEUOTH" or row["carrier_id"].strip():
                r.fail(f"row {i}: carrier {row['carrier_id']!r} unknown")
        elif c["is_gradeable"] == "TRUE":
            g = row["grade_rank"].strip()
            if not g:
                r.fail(f"row {i}: heat duty on {c['carrier_id']} without grade_rank")
            elif g != c["grade_rank"].strip():
                r.fail(f"row {i}: grade_rank {g} disagrees with {c['carrier_id']} ({c['grade_rank']})")
        elif row["grade_rank"].strip():
            r.fail(f"row {i}: grade_rank on non-gradeable carrier {c['carrier_id']}")
        s = _f(row["duty_share"])
        if s is None or not 0 <= s <= 1:
            r.fail(f"row {i}: duty_share {row['duty_share']!r} not in [0,1]")
        else:
            sums[k] += s
        lo, hi = _f(row["share_low"]), _f(row["share_high"])
        if s is not None and ((lo is not None and lo > s) or (hi is not None and hi < s)):
            r.fail(f"row {i}: band does not bracket duty_share")
    for k, s in sums.items():
        if abs(s - 1.0) > SHARE_TOL:
            r.fail(f"{k}: duty_share sums to {s:.3f}")
    missing = reg_keys - covered
    for k in sorted(missing)[:5]:
        r.fail(f"register row {k} has no duty row")
    r.note = f"{len(duty)} rows, {len(covered)} of {len(reg_keys)} register rows covered"
    return r


def check_process_crosswalk(xw: list[dict], reg: list[dict]) -> Result:
    """One row per register row; codes are COMIT process codes, never sector roots."""
    r = Result("process crosswalk: one row per register row, no sector roots")
    roots = {"ICH", "ICN", "ICR", "IEE", "IFD", "IME", "INF", "IOI", "IPR", "ITX", "IVH",
             "ICM", "IGL", "IIS", "ILM", "IPP"}
    try:
        codes = {row["process_commodity"] for row in read("comit_sector_processes.csv")}
    except FileNotFoundError:
        codes = set()
    reg_keys = {key(x) for x in reg}
    seen: set[tuple] = set()
    for i, row in enumerate(xw, start=2):
        k = key(row)
        if k not in reg_keys:
            r.fail(f"row {i}: {k} not in register")
        if k in seen:
            r.fail(f"row {i}: duplicate {k}")
        seen.add(k)
        code = row["comit_process_code"].strip()
        if code in roots:
            r.fail(f"row {i}: {code} is a sector root, not a process")
        if code and codes and code not in codes:
            r.fail(f"row {i}: {code} not a COMIT process code")
        if (row["match_kind"] == "none") != (not code):
            r.fail(f"row {i}: match_kind {row['match_kind']!r} disagrees with code {code!r}")
    for k in sorted(reg_keys - seen)[:5]:
        r.fail(f"register row {k} has no crosswalk row")
    r.note = f"{len(seen)} rows"
    return r


# §3.6's role enum, split the two ways the checks below need it: by flow direction, which
# fixes the sign of the coefficient, and by whether the row belongs on an emission carrier.
INPUT_ROLES = {"fuel_input", "aux_input", "emission_input"}
EMISSION_ROLES = {"emission", "emission_input"}


def check_units(unit: list[dict], io: list[dict], bom: list[dict], car: list[dict],
                reg: list[dict]) -> Result:
    """§3.5/§3.6: unique ids, fuel carriers resolve, exactly one primary output per
    unit with coefficients, at most one fuel input (D13), role and sign agree (V31),
    hybrids carry a bill of materials whose shares sum to one, chemistry units name a
    register process."""
    r = Result("units: identity, coefficients, bill of materials")
    ids: set[str] = set()
    carriers = {c["carrier_id"] for c in car}
    emission_carriers = {c["carrier_id"] for c in car if c["carrier_kind"] == "emission"}
    reg_procs = {x["process_id"] for x in reg}
    hybrids: set[str] = set()
    for i, row in enumerate(unit, start=2):
        u = row["unit_id"]
        if u in ids:
            r.fail(f"row {i}: duplicate unit_id {u}")
        ids.add(u)
        fc = row["fuel_carrier_id"].strip()
        if fc and fc not in carriers:
            r.fail(f"{u}: fuel_carrier_id {fc!r} unknown")
        # §3.5 requires duty_family on service units; supply, storage and hybrid units
        # serve no duty (they produce or shift a carrier), so only converters are held to it.
        if row["spine"] == "service" and row["unit_class"] == "converter" \
                and row["fuel_carrier_id"].strip() and not row["duty_family"].strip() \
                and not row["unit_id"].startswith("anaerobic_digester"):  # feedstock→biogas, no duty
            r.fail(f"{u}: service converter without duty_family")
        if row["spine"] == "chemistry" and row["process_id"].strip() \
                and row["process_id"] not in reg_procs:
            r.fail(f"{u}: process_id {row['process_id']!r} not in register")
        if row["is_hybrid"] == "TRUE":
            hybrids.add(u)
        ab = row["abates_unit_id"].strip()
        if ab and ab not in {x["unit_id"] for x in unit}:
            r.fail(f"{u}: abates_unit_id {ab!r} unknown")
        for col in ("capex", "fixed_opex", "availability_factor", "emissions_released"):
            v = _f(row[col])
            if v is not None and v < 0:
                r.fail(f"{u}: {col} negative")
        av = _f(row["availability_factor"])
        if av is not None and not 0 < av <= 1:
            r.fail(f"{u}: availability_factor {av} outside (0,1]")
    primary: dict[str, int] = defaultdict(int)
    fuel: dict[str, int] = defaultdict(int)
    io_units: set[str] = set()
    io_keys: set[tuple] = set()
    for i, row in enumerate(io, start=2):
        u, c, role = row["unit_id"], row["carrier_id"], row["role"]
        if u not in ids:
            r.fail(f"unit_input_output row {i}: unit {u!r} unknown")
        if c not in carriers:
            r.fail(f"unit_input_output row {i}: carrier {c!r} unknown")
        # §3.6 keys on the triple, which is what lets a store hold a charge row and a
        # discharge row on one carrier, and a fired capture train hold host CO2 in and
        # reboiler CO2 out.  (u, c) alone would reject both.
        if (u, c, role) in io_keys:
            r.fail(f"unit_input_output row {i}: duplicate ({u}, {c}, {role})")
        io_keys.add((u, c, role))
        io_units.add(u)
        # §3.6 marks role required, and check_spec_shape's enum guard skips a blank cell,
        # so a blank has to be rejected here or it passes every leg below by vacuity.
        if not role:
            r.fail(f"unit_input_output row {i}: role blank (V31: required)")
        coefficient = _f(row["coefficient"])
        if coefficient is None:
            r.fail(f"unit_input_output row {i}: coefficient blank")
        elif role in INPUT_ROLES and coefficient >= 0:
            r.fail(f"unit_input_output row {i}: role {role} with coefficient {coefficient}"
                   " (V31: inputs are negative)")
        elif role not in INPUT_ROLES and coefficient <= 0:
            r.fail(f"unit_input_output row {i}: role {role} with coefficient {coefficient}"
                   " (V31: outputs are positive)")
        if role in EMISSION_ROLES and c not in emission_carriers:
            r.fail(f"unit_input_output row {i}: role {role} on {c!r}, "
                   "which is not an emission carrier (V31)")
        if role not in EMISSION_ROLES and c in emission_carriers:
            r.fail(f"unit_input_output row {i}: emission carrier {c!r} carries role "
                   f"{role} (V31: use emission or emission_input)")
        if role == "primary_output":
            primary[u] += 1
        if role == "fuel_input":
            fuel[u] += 1
    for u in sorted(io_units):
        if primary[u] != 1:
            r.fail(f"{u}: {primary[u]} primary outputs (expected exactly 1)")
        if fuel[u] > 1:
            r.fail(f"{u}: {fuel[u]} fuel inputs (D13 allows at most 1)")
    shares: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    bom_units: set[str] = set()
    for i, row in enumerate(bom, start=2):
        u = row["unit_id"]
        if u not in hybrids:
            r.fail(f"bill_of_materials row {i}: {u} is not a hybrid unit")
        bom_units.add(u)
        shares[u][0] += _f(row["capacity_share"]) or 0.0
        shares[u][1] += _f(row["capex_share"]) or 0.0
    for u in sorted(hybrids - bom_units):
        r.fail(f"{u}: hybrid without bill of materials")
    for u, (a, b) in shares.items():
        # capex_share may be blank throughout a hybrid whose components are uncosted
        # (no source); a partly filled column is still an error.
        if abs(a - 1) > 1e-3 or (b != 0.0 and abs(b - 1) > 1e-3):
            r.fail(f"{u}: BOM shares sum to {a:.3f} / {b:.3f}")
    r.note = (f"{len(ids)} units, {len(io_units)} with coefficients, "
              f"{len(hybrids)} hybrids")
    return r


def check_eligibility_and_join(elig: list[dict], join: list[dict], unit: list[dict],
                               reg: list[dict], lib: list[dict]) -> Result:
    r = Result("eligibility and option→unit join: keys resolve")
    ids = {x["unit_id"] for x in unit}
    reg_ap = {(x["carb3_activity"], x["process_id"]) for x in reg}
    seen: set[tuple] = set()
    for i, row in enumerate(elig, start=2):
        k = (row["unit_id"], row["carb3_activity"], row["process_id"])
        if k in seen:
            r.fail(f"unit_eligibility row {i}: duplicate {k}")
        seen.add(k)
        if row["unit_id"] not in ids:
            r.fail(f"unit_eligibility row {i}: unit {row['unit_id']!r} unknown")
        if row["process_id"].strip() and (row["carb3_activity"], row["process_id"]) not in reg_ap:
            r.fail(f"unit_eligibility row {i}: ({row['carb3_activity']}, {row['process_id']}) "
                   f"not in register")
        ms = _f(row["max_share"])
        if ms is not None and not 0 <= ms <= 1:
            r.fail(f"unit_eligibility row {i}: max_share {ms} outside [0,1]")
    options = {x["option_id"] for x in lib}
    joined: set[str] = set()
    for i, row in enumerate(join, start=2):
        if row["option_id"] not in options:
            r.fail(f"option_unit row {i}: option {row['option_id']!r} unknown")
        joined.add(row["option_id"])
        u = row["unit_id"].strip()
        if u and u not in ids:
            r.fail(f"option_unit row {i}: unit {u!r} unknown")
        # A whole-route option (H2-DRI+EAF, cupola->induction) may span several units and
        # name none; every other relationship must name the unit it is about.
        if row["relationship"] not in {"none", "route_change"} and not u:
            r.fail(f"option_unit row {i}: relationship {row['relationship']} without a unit")
    for o in sorted(options - joined)[:5]:
        r.fail(f"option {o} has no option→unit row")
    r.note = f"{len(seen)} eligibility rows, {len(joined)} of {len(options)} options joined"
    return r


def check_lineage(lin: list[dict], unit: list[dict], car: list[dict]) -> Result:
    """Data-migration B1: 397 rows, every one dispositioned, unit ids resolve."""
    r = Result("technology lineage: 397 rows, every one dispositioned")
    try:
        src = {x["technology_code"] for x in read("emissions_source_classification.csv")}
    except FileNotFoundError:
        src = set()
    ids = {x["unit_id"] for x in unit}
    carriers = {c["carrier_id"] for c in car}
    seen: set[str] = set()
    counts: dict[str, int] = defaultdict(int)
    for i, row in enumerate(lin, start=2):
        t = row["technology_code"]
        if t in seen:
            r.fail(f"row {i}: duplicate {t}")
        seen.add(t)
        if src and t not in src:
            r.fail(f"row {i}: {t} not in emissions_source_classification.csv")
        d = row["disposition"].strip()
        counts[d] += 1
        if not d:
            r.fail(f"row {i}: {t} has no disposition")
        u = row["unit_id"].strip()
        if d in {"collapsed", "preserved"} and not u:
            r.fail(f"row {i}: {t} {d} without unit_id")
        if u and u not in ids:
            r.fail(f"row {i}: unit {u!r} unknown")
        for col in ("carrier_id", "fuel_carrier_id"):
            v = row[col].strip()
            if v and v not in carriers:
                r.fail(f"row {i}: {col} {v!r} unknown")
    if src and seen != src:
        r.fail(f"{len(src - seen)} technologies missing, {len(seen - src)} extra")
    r.note = " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    return r


def check_load_shape(shape: list[dict], reg: list[dict]) -> Result:
    """§3.13: one row per (activity, process); standing iff runs_when_idle."""
    r = Result("load shape: one row per process, standing rule")
    reg_ap = {(x["carb3_activity"], x["process_id"]) for x in reg}
    seen: set[tuple] = set()
    for i, row in enumerate(shape, start=2):
        k = (row["carb3_activity"], row["process_id"])
        if k not in reg_ap:
            r.fail(f"row {i}: {k} not in register")
        if k in seen:
            r.fail(f"row {i}: duplicate {k}")
        seen.add(k)
        standing = row["shape_class"] == "standing"
        if standing != (row["runs_when_idle"] == "TRUE"):
            r.fail(f"row {i}: {row['shape_id']} standing/runs_when_idle disagree")
        df, pm = _f(row["duty_factor"]), _f(row["peak_to_mean"])
        if df is not None and not 0 < df <= 1:
            r.fail(f"row {i}: duty_factor {df} outside (0,1]")
        if pm is not None and pm < 1:
            r.fail(f"row {i}: peak_to_mean {pm} below 1")
    for k in sorted(reg_ap - seen)[:5]:
        r.fail(f"register process {k} has no shape row")
    r.note = f"{len(seen)} of {len(reg_ap)} (activity, process) pairs"
    return r


def check_scenario(sp: list[dict], infra: list[dict], car: list[dict]) -> Result:
    """§3.7/§3.8: carrier references resolve; export price below import per period."""
    r = Result("scenario parameters and infrastructure: carriers resolve, price wedge")
    carriers = {c["carrier_id"] for c in car}
    prices: dict[tuple, dict[str, float]] = defaultdict(dict)
    for i, row in enumerate(sp, start=2):
        c = row["carrier_id"].strip()
        if c and c not in carriers:
            r.fail(f"scenario_parameters row {i}: carrier {c!r} unknown")
        if _f(row["value"]) is None:
            r.fail(f"scenario_parameters row {i}: value blank")
        if row["parameter_id"] in {"import_price", "export_price"}:
            prices[(c, row["period"])][row["parameter_id"]] = _f(row["value"]) or 0.0
    for (c, p), d in prices.items():
        if "import_price" in d and "export_price" in d and d["export_price"] >= d["import_price"]:
            r.fail(f"{c} {p}: export_price not below import_price (V21)")
    keys: set[tuple] = set()
    for i, row in enumerate(infra, start=2):
        k = (row["scenario_id"], row["carrier"], row["cluster_id"], row["period"])
        if k in keys:
            r.fail(f"infrastructure_scenario row {i}: duplicate {k}")
        keys.add(k)
    r.note = f"{len(sp)} parameter rows, {len(infra)} infrastructure rows"
    return r


def check_default_unit(du: list[dict], duty: list[dict], elig: list[dict],
                       unit: list[dict]) -> Result:
    """§3.16: shares sum to 1 per (activity, set, process, family); every row has an
    eligibility entry. ADVISORY on eligibility until T18's coverage is settled."""
    r = Result("activity_default_unit: share sums and eligibility")
    ids = {x["unit_id"] for x in unit}
    elig_keys = {(x["unit_id"], x["carb3_activity"], x["process_id"]) for x in elig}
    duty_keys = {key(x) + (x["duty_family"],) for x in duty}
    sums: dict[tuple, float] = defaultdict(float)
    no_elig = 0
    for i, row in enumerate(du, start=2):
        k = key(row) + (row["duty_family"],)
        if k not in duty_keys:
            r.fail(f"row {i}: {k} not in duty profile")
        if row["unit_id"] not in ids:
            r.fail(f"row {i}: unit {row['unit_id']!r} unknown")
        elif (row["unit_id"], row["carb3_activity"], row["process_id"]) not in elig_keys:
            no_elig += 1
        sums[k] += _f(row["default_share"]) or 0.0
    for k, s in sums.items():
        if abs(s - 1) > SHARE_TOL:
            r.fail(f"{k}: default_share sums to {s:.3f}")
    r.note = f"{len(du)} rows, {len(sums)} duties, {no_elig} rows without an eligibility entry"
    return r


# ----------------------------------------------------------------------------- main

def run() -> tuple[list[Result], dict[str, list[dict]]]:
    names = list(EXPECTED_COLUMNS) + list(SPEC_COLUMNS)
    tables: dict[str, list[dict]] = {}
    load_errors: list[str] = []
    for n in names:
        try:
            tables[n] = read(n)
        except FileNotFoundError:
            load_errors.append(f"{n}: not found in {DATA}")
        except Exception as exc:  # noqa: BLE001 - report, do not crash
            load_errors.append(f"{n}: {exc}")
    for n in OPTIONAL_SPEC_COLUMNS:
        try:
            tables[n] = read(n)
        except FileNotFoundError:
            pass

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
    car = tables["carrier.csv"]
    duty = tables["activity_process_duty_profile.csv"]
    unit = tables["unit.csv"]
    elig = tables["unit_eligibility.csv"]

    results = [
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
        check_spec_shape(tables),
        check_carrier(car),
        check_duty_profile(duty, reg, car),
        check_process_crosswalk(tables["carb3_comit_process_crosswalk.csv"], reg),
        check_units(unit, tables["unit_input_output.csv"],
                    tables["unit_bill_of_materials.csv"], car, reg),
        check_eligibility_and_join(elig, tables["decarbonisation_option_unit.csv"],
                                   unit, reg, lib),
        check_lineage(tables["comit_technology_lineage.csv"], unit, car),
        check_load_shape(tables["process_load_shape.csv"], reg),
        check_scenario(tables["scenario_parameters.csv"],
                       tables["infrastructure_scenario.csv"], car),
    ]
    if "activity_default_unit.csv" in tables:
        results.append(check_default_unit(tables["activity_default_unit.csv"], duty,
                                          elig, unit))
    results += [check_coverage(reg, prof, opt, lib), check_band_coverage(prof)]
    return results, tables


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
