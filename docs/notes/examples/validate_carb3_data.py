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
constraint" pattern (implementation spec section 6.3). Their per-item work lists print
in the full report and under --json, and are suppressed by --quiet, which is how
`make data-check` stays a gate and `make data-report` carries the detail.

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
    """One check's outcome. `blocking` decides whether a failure fails the run.

    `failures` are printed whatever the verbosity, so an advisory check that wants to
    hand over a work list rather than raise an alarm puts it in `details` instead:
    details print in the full report and in --json, and are silent under --quiet. That
    is what keeps `make data-check` reading as a pass/fail gate while `make data-report`
    carries the detail.
    """

    def __init__(self, name: str, blocking: bool = True):
        self.name = name
        self.blocking = blocking
        self.failures: list[str] = []
        self.details: list[str] = []
        self.note = ""

    def fail(self, msg: str) -> None:
        self.failures.append(msg)

    def detail(self, msg: str) -> None:
        self.details.append(msg)

    @property
    def ok(self) -> bool:
        return not self.failures

    def as_dict(self) -> dict:
        return {
            "check": self.name,
            "blocking": self.blocking,
            "ok": self.ok,
            "failures": self.failures,
            "details": self.details,
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
        "carrier_id", "carrier_name", "carrier_kind", "is_gradeable", "grade_family",
        "grade_rank", "grade_label", "is_indirect", "emission_factor_source", "biogenic_fraction",
        "carbon_charge", "denominator_kind", "may_dispose", "may_import", "may_export",
        "vector", "comit_commodity", "provenance",
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
        "draws_ambient", "provenance", "confidence", "provenance_ref",
    ],
    "unit_abatement_host.csv": [
        "unit_id", "host_unit_id", "provenance", "confidence",
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

# §3.3: the eleven duty families. `EN` is not one of them — it is COMIT's hydrogen-production
# family and labels only units (§3.4), so it is valid for `unit.duty_family` and nowhere else.
# One shared set used to serve both columns, which meant an `EN` duty row could not be
# rejected without also rejecting the ten hydrogen-producing units (note 22 Task 1).
DUTY_FAMILIES = {"DRY", "HRS", "HTH", "LTH", "MOT", "NEUOTH", "OTH", "PHEAT", "REF", "SPC",
                 "STM"}
UNIT_FAMILIES = DUTY_FAMILIES | {"EN"}
# V34 (c): families the §3.3 enum admits but which present no service duty (§3.4), and `EN`,
# which the enum does not admit at all. A duty-profile row on any of them is refused.
NON_DUTY_FAMILIES = {"EN", "NEUOTH", "HRS"}
# §3.4's duty-family-to-carrier table, by what the family's carrier must be.
HEAT_DUTY_FAMILIES = {"LTH", "HTH", "STM", "DRY", "SPC", "PHEAT"}
COOLING_DUTY_FAMILIES = {"REF"}
GRADE_FAMILIES = {"heat", "cooling"}
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
    ("unit.csv", "duty_family"): UNIT_FAMILIES,
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
    ("carrier.csv", "may_dispose"), ("carrier.csv", "may_import"),
    ("carrier.csv", "may_export"), ("unit.csv", "is_hybrid"), ("unit.csv", "draws_ambient"),
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


def grade_family(row: dict) -> str | None:
    """A carrier's `grade_family` (§3.4), or None where it is not gradeable.

    Before `carrier.csv` carried the column, every gradeable carrier was heat, so a missing
    column reads as heat. Where the column is present a blank on a gradeable row is a
    failure of `check_carrier`, and this returns the blank rather than guessing."""
    if row.get("is_gradeable") != "TRUE":
        return None
    if "grade_family" not in row:
        return "heat"
    return (row["grade_family"] or "").strip()


def check_carrier(car: list[dict]) -> Result:
    """§3.4: grades need a family, a rank and a label, and the rank is unique within its
    family; emissions carry a charge; may_dispose is derived from carrier_kind (true for
    intermediate and emission only).

    V34 (duties are services at a grade) leg (d): every gradeable carrier has a
    `grade_family`, no other carrier has one, and `grade_rank` is unique within the family.
    Uniqueness used to be global, which would have rejected the first cooling band: cooling
    ranks 1 to 3 sit beside heat ranks 1 to 3 by design (note 22 Task 1)."""
    r = Result("carrier: grades per family, charges, may_dispose")
    seen: set[str] = set()
    ranks: dict[tuple[str, int], str] = {}
    has_family_column = bool(car) and "grade_family" in car[0]
    for i, row in enumerate(car, start=2):
        cid = row["carrier_id"]
        if cid in seen:
            r.fail(f"row {i}: duplicate carrier_id {cid}")
        seen.add(cid)
        kind = row["carrier_kind"]
        gradeable = row["is_gradeable"] == "TRUE"
        if gradeable and not (row["grade_rank"].strip() and row["grade_label"].strip()):
            r.fail(f"{cid}: gradeable without grade_rank/grade_label")
        fam = grade_family(row)
        if has_family_column:
            raw = (row["grade_family"] or "").strip()
            if gradeable and raw not in GRADE_FAMILIES:
                r.fail(f"{cid}: gradeable with grade_family {raw!r}, required one of "
                       f"{sorted(GRADE_FAMILIES)} (V34 (d))")
            if not gradeable and raw:
                r.fail(f"{cid}: grade_family {raw!r} on a non-gradeable carrier (V34 (d))")
        if not gradeable and (row["grade_rank"].strip() or row["grade_label"].strip()):
            r.fail(f"{cid}: grade_rank/grade_label on a non-gradeable carrier")
        if gradeable and row["grade_rank"].strip():
            rk = int(row["grade_rank"])
            if (fam, rk) in ranks:
                r.fail(f"{cid}: grade_rank {rk} already used in grade_family {fam} by "
                       f"{ranks[(fam, rk)]} (V34 (d): unique within the family)")
            ranks[(fam, rk)] = cid
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
    per_family = defaultdict(int)
    for fam, _ in ranks:
        per_family[fam] += 1
    r.note = (f"{len(seen)} carriers, "
              + ", ".join(f"{n} {fam} grades" for fam, n in sorted(per_family.items()))
              + ("" if has_family_column else "; no grade_family column, read as heat"))
    return r


def check_abatement_hosts(host: list[dict], unit: list[dict]) -> Result:
    """V33 (a capture train abates several hosts): leg (b).

    Every `abatement` unit has at least one host; each host is a `converter` on the same
    `process_id`; no unit hosts itself; both ids resolve. This replaces the single
    `unit.abates_unit_id` column, which could name only one host and was blank on 11 of
    the 13 trains.

    Leg (a) — `premise_process_unit` rows naming an eligible unit, distinct per parent,
    with `capacity_share` summing to 1 — has no premise data in this repository to check
    against, and leg (c) — an abatement unit's remaining life equals the minimum over its
    hosts — is an LP-build assertion. Neither is implemented here.
    """
    r = Result("V33 (a capture train abates several hosts): every train names its hosts")
    by_id = {x["unit_id"]: x for x in unit}
    trains = {u for u, x in by_id.items() if x["unit_class"] == "abatement"}
    named: dict[str, set[str]] = {}
    for i, row in enumerate(host, start=2):
        u, h = row["unit_id"], row["host_unit_id"]
        if u not in by_id:
            r.fail(f"unit_abatement_host.csv:{i}: unit_id {u!r} is not a unit "
                   "(V33 (b): both ids resolve)")
            continue
        if h not in by_id:
            r.fail(f"{u}: host_unit_id {h!r} is not a unit "
                   "(V33 (b): both ids resolve)")
            continue
        if by_id[u]["unit_class"] != "abatement":
            r.fail(f"{u}: unit_class {by_id[u]['unit_class']!r}, not abatement "
                   "(V33 (b): only an abatement unit has hosts)")
        if u == h:
            r.fail(f"{u}: hosts itself (V33 (b): no self-host)")
        if by_id[h]["unit_class"] != "converter":
            r.fail(f"{u}: host {h} is {by_id[h]['unit_class']!r}, not converter "
                   "(V33 (b): a host is the converter the train captures from)")
        if by_id[h]["process_id"] != by_id[u]["process_id"]:
            r.fail(f"{u}: host {h} is on process_id {by_id[h]['process_id']!r}, "
                   f"the train on {by_id[u]['process_id']!r} "
                   "(V33 (b): a host runs the same process)")
        if h in named.setdefault(u, set()):
            r.fail(f"{u}: host {h} named twice (V33 (b): the key is the pair)")
        named[u].add(h)
    for u in sorted(trains - set(named)):
        r.fail(f"{u}: abatement unit with no host row "
               "(V33 (b): every train names at least one host)")
    blank = sorted(u for u in trains if not by_id[u]["process_id"].strip())
    r.note = (f"{len(host)} rows, {len(trains)} abatement units, "
              f"{len(blank)} with a blank process_id")
    return r


def check_boundary(car: list[dict], duty: list[dict]) -> Result:
    """V32 (the site boundary is a property of the carrier, D16): legs (b) and (c).

    Leg (a) — that import and export variables are declared only where the carrier
    allows it *and* the connection carries the carrier — is an LP-build assertion and
    has no reference data to check here.
    """
    r = Result("V32 (site boundary on the carrier): may_import / may_export")
    kinds: dict[str, str] = {}
    exportable: dict[str, bool] = {}
    for i, row in enumerate(car, start=2):
        cid = row["carrier_id"]
        kind = row["carrier_kind"]
        kinds[cid] = kind
        imp = (row.get("may_import") or "").strip()
        exp = (row.get("may_export") or "").strip()
        for col, v in (("may_import", imp), ("may_export", exp)):
            if v not in {"TRUE", "FALSE"}:
                r.fail(f"carrier.csv:{i} {cid}: {col}={v!r}, required TRUE/FALSE "
                       "(V32: the boundary marker is not optional)")
        exportable[cid] = exp == "TRUE"
        # leg (c)
        if kind in {"emission", "intermediate"} and (imp == "TRUE" or exp == "TRUE"):
            r.fail(f"{cid}: {kind} carrier with may_import={imp} may_export={exp} "
                   "(V32 (c): an emission or intermediate carrier never crosses the "
                   "site boundary)")
    # leg (b)
    for i, row in enumerate(duty, start=2):
        cid = row["carrier_id"]
        if kinds.get(cid) == "product" and not exportable.get(cid, True):
            r.fail(f"activity_process_duty_profile.csv:{i} names {cid} "
                   "(V32 (b): a product carrier with may_export FALSE is internal to "
                   "the site and has no duty; its activity is fixed by C8, the carrier "
                   "balance)")
    n_int = sum(1 for c, k in kinds.items() if k == "product" and not exportable[c])
    r.note = (f"{sum(1 for k in kinds.values() if k == 'product')} product carriers, "
              f"{n_int} internal to the site")
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


def check_duty_families(duty: list[dict]) -> Result:
    """BLOCKING. V34 (duties are services at a grade) leg (c), the part that is green today:
    no duty-profile row carries `EN`, `NEUOTH` or `HRS`.

    `EN` labels hydrogen-producing units only; `NEUOTH` (feedstock) and `HRS` (hot rolling, a
    chemistry node) present no service duty (§3.4). Leg (b) — a row on a gradeable carrier
    carries that carrier's own rank — is in `check_duty_profile`; legs (a) and the rest of
    (c) are advisory in `check_duty_services` until note 22 Tasks 3 and 5 land."""
    r = Result("V34 (duties are services at a grade) (c): no EN, NEUOTH or HRS duty row")
    for i, row in enumerate(duty, start=2):
        f = row["duty_family"].strip()
        if f in NON_DUTY_FAMILIES:
            r.fail(f"activity_process_duty_profile.csv:{i} {key(row)} carries {f}, which "
                   "presents no duty (§3.4)")
    r.note = f"{len(duty)} rows"
    return r


def check_duty_services(duty: list[dict], car: list[dict]) -> Result:
    """ADVISORY. V34 (duties are services at a grade) legs (a) and (c), the parts the data
    does not yet meet.

    (a) no duty row names a `primary` or `emission` carrier — an `OTH` row on `electricity`
        makes C8 (carrier balance) circular at the `electricity` node (§3.4).
    (c) each family's rows sit on the carrier §3.4's table names for it: the six heat
        families on a heat band, `REF` on a cooling band, `MOT` on `motive_power`, `OTH` on a
        non-gradeable service carrier. A `product` carrier with `may_export` true is a
        legitimate duty on any row (§3.9) and is not judged here.

    Advisory until note 22 Task 5 (the `OTH` rows on `electricity`) and Task 3 (a band for
    each `REF` row) land; each then turns blocking."""
    r = Result("V34 (duties are services at a grade) (a), (c): duty carriers (advisory)",
               blocking=False)
    carriers = {c["carrier_id"]: c for c in car}
    on_fuel: list[str] = []
    off_family: dict[str, list[str]] = defaultdict(list)
    for i, row in enumerate(duty, start=2):
        f, cid = row["duty_family"].strip(), row["carrier_id"].strip()
        c = carriers.get(cid)
        if c is None:
            continue  # an unknown carrier is check_duty_profile's failure, not this one's
        where = f"row {i} {row['carb3_activity']} / {row['process_id']} {f} on {cid}"
        kind = c["carrier_kind"]
        if kind in {"primary", "emission"}:
            on_fuel.append(where)
            continue
        if kind == "product":
            continue
        fam = grade_family(c)
        if f in HEAT_DUTY_FAMILIES:
            ok = fam == "heat"
        elif f in COOLING_DUTY_FAMILIES:
            ok = fam == "cooling"
        elif f == "MOT":
            ok = cid == "motive_power"
        elif f == "OTH":
            ok = kind == "intermediate"
        else:
            ok = True  # NON_DUTY_FAMILIES are check_duty_families' failure
        if not ok:
            off_family[f].append(where)
    n_off = sum(len(v) for v in off_family.values())
    r.note = (f"(a) {len(on_fuel)} rows on a primary or emission carrier; "
              f"(c) {n_off} rows off their family's carrier"
              + (" — " + ", ".join(f"{f} {len(v)}" for f, v in sorted(off_family.items()))
                 if off_family else ""))
    for w in on_fuel:
        r.detail(f"  (a) {w}")
    for f in sorted(off_family):
        for w in off_family[f]:
            r.detail(f"  (c) {w}")
    return r


def _primary_output(io: list[dict]) -> dict[str, str]:
    return {row["unit_id"]: row["carrier_id"] for row in io if row["role"] == "primary_output"}


def check_unit_grade_out(unit: list[dict], io: list[dict], car: list[dict]) -> Result:
    """ADVISORY. §3.5: a unit's `grade_out` is a rank in the grade family of its primary
    output, and it is required where that output is gradeable.

    Also counts, as detail, units whose `grade_out` differs from their own primary output's
    rank: legal in principle (a unit may be rated above the band it is booked to), but in
    the current library it marks a unit whose output and rating disagree (note 22 §1).
    Advisory until note 22 Task 6 repairs `solar_thermal_flat` and the three heat-pump
    stores; it then turns blocking."""
    r = Result("unit grade_out in its primary output's grade family (advisory)",
               blocking=False)
    carriers = {c["carrier_id"]: c for c in car}
    ranks_by_family: dict[str, set[int]] = defaultdict(set)
    for c in car:
        fam = grade_family(c)
        if fam and c["grade_rank"].strip():
            ranks_by_family[fam].add(int(c["grade_rank"]))
    prim = _primary_output(io)
    missing: list[str] = []
    out_of_family: list[str] = []
    disagree: list[str] = []
    graded = 0
    for u in unit:
        uid = u["unit_id"]
        p = prim.get(uid)
        fam = grade_family(carriers[p]) if p in carriers else None
        g = u["grade_out"].strip()
        if fam is None:
            continue
        graded += 1
        if not g:
            missing.append(f"{uid}: primary output {p} ({fam}) is gradeable, grade_out blank")
            continue
        if int(g) not in ranks_by_family[fam]:
            out_of_family.append(f"{uid}: grade_out {g} is not a {fam} rank")
        elif int(g) != int(carriers[p]["grade_rank"]):
            disagree.append(f"{uid}: grade_out {g}, primary output {p} at rank "
                            f"{carriers[p]['grade_rank']}")
    for m in missing + out_of_family:
        r.detail(f"  {m}")
    r.note = (f"{graded} units with a gradeable primary output; {len(missing)} without a "
              f"grade_out, {len(out_of_family)} outside the family, {len(disagree)} whose "
              f"grade_out differs from the output's rank")
    for d in disagree:
        r.detail(f"  {d}")
    return r


def _eligible_sets(elig: list[dict]) -> tuple[dict[tuple, set[str]], dict[str, set[str]]]:
    """Per (activity, process) and per activity (the blank-`process_id` rows), the units
    `unit_eligibility` admits. An activity-level row admits its unit at every process of
    the activity, which is how A3 reads it."""
    per_process: dict[tuple, set[str]] = defaultdict(set)
    per_activity: dict[str, set[str]] = defaultdict(set)
    for row in elig:
        if row["process_id"].strip():
            per_process[(row["carb3_activity"], row["process_id"])].add(row["unit_id"])
        else:
            per_activity[row["carb3_activity"]].add(row["unit_id"])
    return per_process, per_activity


def check_unsourced_draws(elig: list[dict], io: list[dict], car: list[dict],
                          duty: list[dict]) -> Result:
    """ADVISORY. A unit eligible at a process draws an `intermediate` carrier that no unit
    eligible there produces, under any output role.

    The carrier is matched exactly, not through the heat cascade. C8 (carrier balance)
    lets hotter heat cascade into a colder band's node, so a boiler can in LP terms feed
    `heat_pump_lt_reject`'s `heat_lt60` draw — but that is burning fuel to feed a heat
    pump's source, not recovering reject heat, so it is not counted as a source here. The
    count under the cascade is given in the note for comparison.

    The case note 22 §3 names is `heat_pump_lt_reject` at the `REF` processes: it is meant
    to lift a chiller's condenser heat, and no chiller carries a `reject` row (Task 4)."""
    r = Result("intermediate draws with no eligible producer (advisory)", blocking=False)
    carriers = {c["carrier_id"]: c for c in car}
    draws: dict[str, set[str]] = defaultdict(set)
    makes: dict[str, set[str]] = defaultdict(set)
    for row in io:
        c = carriers.get(row["carrier_id"])
        if c is None or c["carrier_kind"] != "intermediate":
            continue
        (draws if row["role"] in INPUT_ROLES else makes)[row["unit_id"]].add(row["carrier_id"])

    def rank(cid: str) -> tuple[str | None, int | None]:
        c = carriers[cid]
        fam = grade_family(c)
        return fam, (int(c["grade_rank"]) if fam and c["grade_rank"].strip() else None)

    def cascades(cid: str, produced: set[str]) -> bool:
        fam, g = rank(cid)
        if fam is None or g is None:
            return False
        for p in produced:
            pf, pg = rank(p)
            if pf == fam and pg is not None and (pg > g if fam == "heat" else pg < g):
                return True
        return False

    per_process, per_activity = _eligible_sets(elig)
    gaps: list[tuple[str, str, str, str]] = []
    under_cascade = 0
    scopes = [((a, p), us, us | per_activity.get(a, set())) for (a, p), us in per_process.items()]
    scopes += [((a, ""), us, us) for a, us in per_activity.items()]
    for (a, p), drawers, here in scopes:
        produced = set().union(*(makes[u] for u in here)) if here else set()
        for u in sorted(drawers):
            for cid in sorted(draws[u] - produced):
                gaps.append((u, cid, a, p))
                if not cascades(cid, produced):
                    under_cascade += 1
    by_pair: dict[tuple[str, str], int] = defaultdict(int)
    for u, cid, _, _ in gaps:
        by_pair[(u, cid)] += 1
    ref_processes = {(d["carb3_activity"], d["process_id"]) for d in duty
                     if d["duty_family"] in COOLING_DUTY_FAMILIES}
    reject_at_ref = sum(1 for u, _, a, p in gaps
                        if u == "heat_pump_lt_reject" and (a, p) in ref_processes)
    r.note = (f"{len(gaps)} (unit, activity, process) draws with no exact producer, "
              f"{under_cascade} with none even through C8's heat cascade; "
              f"{len(by_pair)} (unit, carrier) pairs; heat_pump_lt_reject at "
              f"{reject_at_ref} REF processes")
    for (u, cid), n in sorted(by_pair.items(), key=lambda kv: (-kv[1], kv[0])):
        r.detail(f"  {u} draws {cid}: {n} places")
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


# ------------------------------------------- the emission-coefficient basis (2026-09-20)
#
# A §3.6 coefficient is "per unit of the unit's output", and the *unit* of that output is
# the `denominator_kind` of the unit's `primary_output` carrier — Mt for a mass carrier, PJ
# for an energy one. Emission carriers are themselves denominated in kt, because A6 derives
# fuel CO2 from an emission factor in kt/PJ. Nothing in the file records any of this, so a
# row authored on a Mt-per-Mt basis is indistinguishable from a legitimately tiny kt-per-Mt
# one, and every blocking check passes over it.
#
# That is exactly what happened. `kiln_dry_coal`, `kiln_dry_gas` and `kiln_dry_wdf`
# declared `co2_process` at 0.52500 where spec §3.6's derivation table says "525 kt CO2 per
# Mt of clinker is chemistry, not a scenario assumption", and `ccs_amine`'s three
# `emission_input` rows were shares of the same Mt-denominated stream. `mvp-cement` vented
# 0.44625 kt/yr of process CO2 where the cement worked example's §8.1 says 446.25, a cement
# works' carbon bill came out 58% low, and no capture train paid for itself at any tariff
# including zero. Note 20 item 56.
#
# THE BAND IS STOICHIOMETRIC, NOT EMPIRICAL. It is derived from what chemistry permits, not
# fitted to the rows in the file today, and widening it to admit a row is the wrong move —
# the row is what is wrong. Both bounds, per denominator:
#
#   mass output (kt CO2 per Mt of product)
#     ceiling  3666.67 = 1000 x 44/12. One Mt of product that is pure carbon, every atom of
#              it released as CO2. No chemistry puts more CO2 against a Mt of product than
#              the product's own mass in carbon, fully oxidised. The largest row in the
#              table is `ammonia_smr_gas` at 1489.354, well inside it.
#     floor       3.67 = the ceiling / 1000.
#
#   energy output (kt CO2 per PJ of product)
#     ceiling  1117.93 = 111.793 x 10. Pure carbon at 32.8 GJ/t releases 111.793 kt CO2 per
#              PJ burnt — compare coal's 94.6 kt/PJ in `scenario_parameters` — and no real
#              conversion delivers a PJ of product off more than ten PJ of feedstock. The
#              largest row is `gasifier_biomass_ccs` at 153.5423.
#     floor       1.118 = the ceiling / 1000.
#
# The floor is the ceiling divided by a thousand in both cases, and that is the whole
# argument: it is the largest coefficient that would *still* sit inside the band after
# being multiplied by 1000, so anything at or below it cannot be told apart from a row
# written a thousand times too small. A row below the floor also declares under one part in
# a thousand of its denominator as CO2, which is a zero rather than a declaration — a unit
# with no process chemistry carries no row at all, not a small one.

CARBON_TO_CO2 = 44.0 / 12.0          # kg CO2 per kg of carbon fully oxidised
KT_PER_MT = 1000.0
CARBON_LHV_GJ_PER_T = 32.8           # pure carbon, the most carbon-dense fuel there is
MIN_CONVERSION_EFFICIENCY = 0.10     # PJ of product per PJ of feedstock, a floor on any
                                     # real unit; below it nothing is a process

# kt CO2 released per PJ of pure carbon burnt: (1e6 GJ / 32.8 GJ/t) t of C, x 44/12, / 1e3.
CO2_PER_PJ_PURE_CARBON = (1e6 / CARBON_LHV_GJ_PER_T) * CARBON_TO_CO2 / 1e3

# The ceiling per denominator, and the floor as the ceiling one basis down. Writing the
# floor as `ceiling / KT_PER_MT` rather than as a literal is the point: it is the same
# thousandfold the defect was, not an independently chosen number.
_EMISSION_COEFFICIENT_CEILING = {
    "mass": CARBON_TO_CO2 * KT_PER_MT,                                   # kt CO2 per Mt
    "energy": CO2_PER_PJ_PURE_CARBON / MIN_CONVERSION_EFFICIENCY,        # kt CO2 per PJ
}
EMISSION_COEFFICIENT_BAND = {
    d: (hi / KT_PER_MT, hi) for d, hi in _EMISSION_COEFFICIENT_CEILING.items()
}


def check_emission_coefficient_basis(io: list[dict], car: list[dict]) -> Result:
    """BLOCKING. Every emission-carrier coefficient sits inside its stoichiometric band.

    Catches a coefficient written on the wrong basis — the thousandfold error of note 20
    item 56 — which no key, enum or sign check can see.
    """
    r = Result("emission coefficients on the kt basis (§3.6)")
    kind = {c["carrier_id"]: c["carrier_kind"] for c in car}
    denom = {c["carrier_id"]: c["denominator_kind"] for c in car}
    emission_carriers = {cid for cid, k in kind.items() if k == "emission"}

    primary: dict[str, str] = {}
    for row in io:
        if row["role"] == "primary_output":
            primary[row["unit_id"]] = row["carrier_id"]

    checked = 0
    for i, row in enumerate(io, start=2):
        cid = row["carrier_id"]
        if cid not in emission_carriers:
            continue
        uid = row["unit_id"]
        out = primary.get(uid)
        if out is None:
            r.fail(f"{uid}: {cid} {row['role']} row, but the unit has no primary_output "
                   f"row, so the coefficient's basis cannot be established")
            continue
        d = denom.get(out)
        band = EMISSION_COEFFICIENT_BAND.get(d)
        if band is None:
            r.fail(f"{uid}: primary_output {out} has denominator_kind {d!r}, "
                   f"which has no stoichiometric band")
            continue
        c = _f(row["coefficient"])
        if c is None:
            r.fail(f"row {i}: {uid}/{cid}/{row['role']} has no readable coefficient")
            continue
        lo, hi = band
        mag = abs(c)
        checked += 1
        if not (lo <= mag <= hi):
            per = "Mt" if d == "mass" else "PJ"
            side = "below" if mag < lo else "above"
            r.fail(f"{uid}: {cid} {row['role']} = {c} is {side} the {d} band "
                   f"[{lo:.3f}, {hi:.2f}] kt CO2 per {per} of {out}"
                   + (f" — x1000 would give {mag * 1000:.5f}, inside it; "
                      f"read spec §3.6 before changing the band"
                      if mag < lo and lo <= mag * 1000 <= hi else ""))

    mass_lo, mass_hi = EMISSION_COEFFICIENT_BAND["mass"]
    energy_lo, energy_hi = EMISSION_COEFFICIENT_BAND["energy"]
    r.note = (f"{checked} emission-carrier coefficients banded; "
              f"mass [{mass_lo:.3f}, {mass_hi:.2f}] kt/Mt, "
              f"energy [{energy_lo:.3f}, {energy_hi:.2f}] kt/PJ")
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


# -------------------------------------------------- the admission screen (2026-09-19)
#
# Note 21 section 3.2 describes the guard the first Python build needs: a unit the model
# cannot fully cost must not enter U. The blocking checks above are green on data that a
# cost-minimiser reads as free energy, because "blank" and "absent" are consistent — they
# are just not priced. The screen is ADVISORY here and BLOCKING in `carb3` (note 21
# section 7). Making it blocking here would turn tens of units red and break the green
# baseline note 18's M1 exit depends on, in a commit that changes no data.

# A blank in any of these is read as zero: the unit is built free, or annuitised over an
# undefined life, or has an undefined C2 (capacity to activity).
COST_FIELDS = ("capex", "lifetime", "fixed_opex", "availability_factor",
               "capacity_to_activity_factor")


def _fuel_input_verdict(u: dict, rows: list[dict]) -> tuple[str, str]:
    """Classify a unit's missing `fuel_input` row. Returns (verdict, reason).

    Most units with no `fuel_input` row are not wrong, so this classifies rather than
    flagging blindly. A store shifts a carrier it does not burn, a rooftop array draws
    ambient, and a heat exchanger or steam dryer is driven by an `aux_input`. What is
    wrong is a unit that names the fuel it burns and then never consumes it, and a unit
    with no input row of any role at all — both produce output from nothing.
    """
    if any(r["role"] == "fuel_input" for r in rows):
        return "ok", ""
    fc = u["fuel_carrier_id"].strip()
    if fc:
        return "gap", f"declares fuel_carrier_id {fc} but has no fuel_input row"
    if u["unit_class"] == "storage":
        return "fuel_free", "storage: shifts a carrier, burns none"
    if u["draws_ambient"] == "TRUE":
        return "fuel_free", "draws_ambient: the input is not a costed carrier"
    if any(r["role"] in INPUT_ROLES for r in rows):
        return "fuel_free", "driven by an aux_input, not by a fuel"
    return "gap", "no fuel_input and no input row of any role"


def check_admission_screen(unit: list[dict], io: list[dict], elig: list[dict],
                           car: list[dict], sp: list[dict]) -> Result:
    """ADVISORY. Note 21 section 3.2: the units a cost-minimiser would build or run for
    free, and the imported carriers it would burn for free.

    Reported per unit_id with the reason, as the work list note 20 needs. Never
    blocking: `make data-check` stays a gate on data consistency, `make data-report`
    carries this."""
    r = Result("admission screen: cost completeness (advisory)", blocking=False)
    io_by_unit: dict[str, list[dict]] = defaultdict(list)
    for row in io:
        io_by_unit[row["unit_id"]].append(row)

    # ---- legs 1 to 3: the unit itself
    blank_counts: dict[str, int] = defaultdict(int)
    no_io: list[str] = []
    fuel_gap: list[str] = []
    fuel_free: dict[str, str] = {}
    reasons: dict[str, list[str]] = {}
    for u in unit:
        uid = u["unit_id"]
        rows = io_by_unit.get(uid, [])
        why: list[str] = []
        blank = [c for c in COST_FIELDS if not u[c].strip()]
        for c in blank:
            blank_counts[c] += 1
        if blank:
            why.append("blank " + ", ".join(blank))
        if not rows:
            no_io.append(uid)
            why.append("no unit_input_output rows")
        verdict, reason = _fuel_input_verdict(u, rows)
        if verdict == "gap":
            fuel_gap.append(uid)
            # A unit with no rows at all has already been named for it; do not say it twice.
            if rows or u["fuel_carrier_id"].strip():
                why.append(reason)
        elif verdict == "fuel_free":
            fuel_free[uid] = reason
        if why:
            reasons[uid] = why

    # ---- leg 4: an importable carrier with no price is a free fuel
    periods = sorted({row["period"].strip() for row in sp if row["period"].strip()})
    priced: dict[str, set[str]] = defaultdict(set)
    for row in sp:
        if row["parameter_id"] == "import_price":
            priced[row["carrier_id"].strip()].add(row["period"].strip())
    importable = [c["carrier_id"] for c in car if c["may_import"] == "TRUE"]
    unpriced: dict[str, list[str]] = {}
    for cid in importable:
        missing = sorted(set(periods) - priced.get(cid, set()))
        if missing:
            unpriced[cid] = missing

    # ---- leg 5: what the gaps reach through eligibility
    # Two counts, because the price leg is a property of the carrier rather than of the
    # unit and roughly triples the reach: the unit legs alone are the migration work list,
    # the wider figure is what the LP would actually admit today.
    unit_gaps = set(reasons)
    with_price = set(unit_gaps)
    for u in unit:
        uid = u["unit_id"]
        drawn = {row["carrier_id"] for row in io_by_unit.get(uid, [])
                 if row["role"] in INPUT_ROLES}
        if u["fuel_carrier_id"].strip():
            drawn.add(u["fuel_carrier_id"].strip())
        if drawn & set(unpriced):
            with_price.add(uid)
    reach = sum(1 for row in elig if row["unit_id"] in unit_gaps)
    reach_price = sum(1 for row in elig if row["unit_id"] in with_price)

    r.note = (f"{len(unit_gaps)}/{len(unit)} units incomplete, "
              f"{len(unpriced)}/{len(importable)} may_import carriers unpriced, "
              f"{reach}/{len(elig)} eligibility rows reach an incomplete unit "
              f"({reach_price} including the unpriced-fuel leg)")

    r.detail(f"blank cost fields: "
             + ", ".join(f"{c}={blank_counts[c]}" for c in COST_FIELDS))
    r.detail(f"no unit_input_output rows: {len(no_io)} units")
    r.detail(f"missing a required fuel_input: {len(fuel_gap)} units "
             f"({len(fuel_free)} more have none legitimately)")
    # The case that motivated the screen. Named because it is the cheapest possible unit
    # in the table and eligible on the dairy premise's own duties, so an unscreened run
    # serves the whole low-temperature heat duty free and demonstrates nothing.
    worked = next((u for u in unit if u["unit_id"] == "heat_exchanger_lt_steam"), None)
    if worked is not None and "heat_exchanger_lt_steam" in reasons:
        n = sum(1 for row in elig if row["unit_id"] == "heat_exchanger_lt_steam")
        r.detail(f"worked example: heat_exchanger_lt_steam capex={worked['capex']!r} "
                 f"fixed_opex={worked['fixed_opex']!r} and no unit_input_output rows, so "
                 f"it produces low-temperature heat from nothing, for nothing, on "
                 f"{n} eligibility rows")
    for uid in sorted(reasons):
        r.detail(f"  {uid}: {'; '.join(reasons[uid])}")
    for cid in sorted(unpriced):
        missing = unpriced[cid]
        span = "all periods" if len(missing) == len(periods) else ", ".join(missing)
        r.detail(f"  carrier {cid}: may_import TRUE, no import_price for {span}")
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
        check_boundary(car, duty),
        check_abatement_hosts(tables["unit_abatement_host.csv"], unit),
        check_duty_profile(duty, reg, car),
        check_duty_families(duty),
        check_process_crosswalk(tables["carb3_comit_process_crosswalk.csv"], reg),
        check_units(unit, tables["unit_input_output.csv"],
                    tables["unit_bill_of_materials.csv"], car, reg),
        check_eligibility_and_join(elig, tables["decarbonisation_option_unit.csv"],
                                   unit, reg, lib),
        check_emission_coefficient_basis(tables["unit_input_output.csv"], car),
        check_lineage(tables["comit_technology_lineage.csv"], unit, car),
        check_load_shape(tables["process_load_shape.csv"], reg),
        check_scenario(tables["scenario_parameters.csv"],
                       tables["infrastructure_scenario.csv"], car),
    ]
    if "activity_default_unit.csv" in tables:
        results.append(check_default_unit(tables["activity_default_unit.csv"], duty,
                                          elig, unit))
    results += [
        check_coverage(reg, prof, opt, lib),
        check_band_coverage(prof),
        check_admission_screen(unit, tables["unit_input_output.csv"], elig, car,
                               tables["scenario_parameters.csv"]),
        check_duty_services(duty, car),
        check_unit_grade_out(unit, tables["unit_input_output.csv"], car),
        check_unsourced_draws(elig, tables["unit_input_output.csv"], car, duty),
    ]
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
                for msg in r.details:
                    print(f"          {msg}")
            continue
        tag = "FAIL" if r.blocking else "WARN"
        print(f"  {tag}  {r.name}  ({len(r.failures)} problems)")
        for msg in r.failures[: args.max_failures]:
            print(f"          {msg}")
        if len(r.failures) > args.max_failures:
            print(f"          ... and {len(r.failures) - args.max_failures} more")
        if not args.quiet:
            for msg in r.details:
                print(f"          {msg}")

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
