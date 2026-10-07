#!/usr/bin/env python3
"""Build ``carb3/data/reference_mvp/``: the reference tables the three MVP premises need.

The nine tables ``carb3.load.REFERENCE_SCHEMA`` reads from the reference root are big
(``unit_eligibility.csv`` alone is 3773 rows) and the demo solves three premises. This script
copies, row for row and byte for byte, only the rows those premises can reach, so a reader
sees the whole of the data the MVP solves on. Pointing the CLI at the result
(``--reference-root carb3/data/reference_mvp``) must give the same answers as the full tables;
``carb3/tests/test_reference_mvp.py`` holds that.

The subset is **derived**, so it goes stale when ``docs/notes/data/`` or the premise tables
move. ``--check`` regenerates in memory and exits non-zero naming each file that differs,
and ``make data-check`` runs it.

The closure (one rule per table) is written out in ``reference_mvp/README.md``, which this
script also generates. Stdlib only: ``pandas`` is not available to a plain ``python3``, and
this must run from ``make data-check`` outside the carb3 environment.

Usage::

    python3 carb3/data/build_reference_mvp.py           # write carb3/data/reference_mvp/
    python3 carb3/data/build_reference_mvp.py --check   # exit 1 if the committed copy is stale
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = REPO / "docs" / "notes" / "data"
PREMISES = HERE / "premises"
OUT = HERE / "reference_mvp"

#: The nine tables ``carb3.load.REFERENCE_SCHEMA`` reads, in its order. ``test_reference_mvp``
#: asserts this list equals the schema's keys, so a table added there fails loudly here.
TABLES: tuple[str, ...] = (
    "carrier",
    "unit",
    "unit_input_output",
    "unit_abatement_host",
    "unit_eligibility",
    "scenario_parameters",
    "activity_process_duty_profile",
    "activity_process_register",
    "infrastructure_scenario",
)

README_NAME = "README.md"


@dataclass(frozen=True)
class Table:
    """One CSV as raw text: the header, and every record with its exact source text."""

    header: tuple[str, ...]
    header_raw: str
    records: tuple[tuple[dict[str, str], str], ...]  # (parsed fields, raw text)

    def select(self, keep) -> list[tuple[dict[str, str], str]]:
        return [(row, raw) for row, raw in self.records if keep(row)]


def read_table(path: Path) -> Table:
    """Read ``path`` keeping each record's raw text, so a number is never reformatted.

    ``csv.reader`` reports how many physical lines it has consumed, which maps each record
    back to its exact source lines (quoted fields hold embedded newlines, and the sources
    use CRLF, so neither a ``split`` on commas nor ``readlines`` would round-trip).
    """
    text = path.read_bytes().decode("utf-8")
    lines = re.findall(r"[^\n]*\n|[^\n]+", text)
    reader = csv.reader(io.StringIO(text, newline=""))
    header = tuple(next(reader))
    header_raw = "".join(lines[: reader.line_num])
    taken = reader.line_num
    records = []
    for fields in reader:
        raw = "".join(lines[taken : reader.line_num])
        taken = reader.line_num
        if len(fields) != len(header):
            raise SystemExit(f"{path}: record ending at line {taken} has {len(fields)} fields")
        records.append((dict(zip(header, fields)), raw))
    return Table(header, header_raw, tuple(records))


def blank(value: str) -> bool:
    return value.strip() == ""


def build() -> tuple[dict[str, str], dict[str, tuple[int, int]], dict[str, str]]:
    """Return ``(file text by name, (source rows, subset rows) by table, rule notes)``."""
    source = {name: read_table(SOURCE / f"{name}.csv") for name in TABLES}
    premise = {
        name: read_table(PREMISES / f"{name}.csv")
        for name in (
            "premise_record",
            "premise_connection",
            "premise_energy",
            "premise_throughput",
            "premise_process_unit",
            "premise_process_detail",
        )
    }

    activities = {row["carb3_activity"] for row, _ in premise["premise_record"].records}
    clusters = {
        row["cluster_id"]
        for row, _ in premise["premise_record"].records
        if not blank(row["cluster_id"]) and row["cluster_id"] != "none"
    }

    # Activity-keyed tables.
    register = source["activity_process_register"].select(
        lambda r: r["carb3_activity"] in activities
    )
    duty = source["activity_process_duty_profile"].select(
        lambda r: r["carb3_activity"] in activities
    )
    eligibility = source["unit_eligibility"].select(lambda r: r["carb3_activity"] in activities)

    # Units: eligible at the activities, named as incumbents, then the hosts of kept trains.
    units = {row["unit_id"] for row, _ in eligibility}
    units |= {row["unit_id"] for row, _ in premise["premise_process_unit"].records}
    hosts = source["unit_abatement_host"].select(lambda r: r["unit_id"] in units)
    units |= {row["host_unit_id"] for row, _ in hosts}
    unit = source["unit"].select(lambda r: r["unit_id"] in units)
    io_rows = source["unit_input_output"].select(lambda r: r["unit_id"] in units)

    # Infrastructure: every row of the kept clusters.
    infra = source["infrastructure_scenario"].select(lambda r: r["cluster_id"] in clusters)

    # Carriers: everything a kept row names.
    carriers: set[str] = set()
    carriers |= {row["carrier_id"] for row, _ in io_rows}
    carriers |= {row["fuel_carrier_id"] for row, _ in unit if not blank(row["fuel_carrier_id"])}
    carriers |= {row["carrier_id"] for row, _ in duty if not blank(row["carrier_id"])}
    for name in ("premise_connection", "premise_energy", "premise_throughput"):
        carriers |= {row["carrier_id"] for row, _ in premise[name].records}
    carriers |= {row["carrier"] for row, _ in infra}
    carrier = source["carrier"].select(lambda r: r["carrier_id"] in carriers)
    kept_carriers = {row["carrier_id"] for row, _ in carrier}

    # Scenario parameters: a kept carrier's series, and the global rows with no carrier.
    scenario = source["scenario_parameters"].select(
        lambda r: blank(r["carrier_id"]) or r["carrier_id"] in kept_carriers
    )

    kept = {
        "carrier": (source["carrier"], carrier),
        "unit": (source["unit"], unit),
        "unit_input_output": (source["unit_input_output"], io_rows),
        "unit_abatement_host": (source["unit_abatement_host"], hosts),
        "unit_eligibility": (source["unit_eligibility"], eligibility),
        "scenario_parameters": (source["scenario_parameters"], scenario),
        "activity_process_duty_profile": (source["activity_process_duty_profile"], duty),
        "activity_process_register": (source["activity_process_register"], register),
        "infrastructure_scenario": (source["infrastructure_scenario"], infra),
    }
    files: dict[str, str] = {}
    counts: dict[str, tuple[int, int]] = {}
    for name, (table, rows) in kept.items():
        files[f"{name}.csv"] = table.header_raw + "".join(raw for _, raw in rows)
        counts[name] = (len(table.records), len(rows))
    files[README_NAME] = readme(counts, sorted(activities), sorted(clusters))
    return files, counts, {}


RULES: tuple[tuple[str, str], ...] = (
    ("activity_process_register", "rows whose `carb3_activity` is one of the premises' activities"),
    ("activity_process_duty_profile", "rows whose `carb3_activity` is one of the premises' activities"),
    (
        "unit_eligibility",
        "rows whose `carb3_activity` is one of the premises' activities, blank `process_id` "
        "rows (activity-level supply) included",
    ),
    (
        "unit_abatement_host",
        "rows whose capture train (`unit_id`) is kept; the `host_unit_id` of each such row is "
        "then added to the kept units, since V33 leg (b) resolves both keys against `unit`",
    ),
    (
        "unit",
        "units in a kept eligibility row, or named in `premise_process_unit`, or the host of "
        "a kept abatement row",
    ),
    ("unit_input_output", "rows whose `unit_id` is a kept unit"),
    (
        "carrier",
        "every carrier a kept row names: `unit_input_output.carrier_id`, "
        "`unit.fuel_carrier_id`, the duty profile's `carrier_id`, the premise connection, "
        "energy and throughput carriers, and an `infrastructure_scenario.carrier` that is also "
        "a carrier id (`hydrogen`)",
    ),
    (
        "scenario_parameters",
        "rows whose `carrier_id` is a kept carrier, plus rows with a blank `carrier_id` "
        "(global: `carbon_price`, `discount_rate`)",
    ),
    (
        "infrastructure_scenario",
        "every row of the premises' clusters (`cluster_id` of `premise_record`)",
    ),
)


def readme(counts: dict[str, tuple[int, int]], activities: list[str], clusters: list[str]) -> str:
    rows = "\n".join(
        f"| `{name}` | {counts[name][0]} | {counts[name][1]} |" for name in TABLES
    )
    rules = "\n".join(f"- `{name}`: {text}." for name, text in RULES)
    return f"""# reference_mvp: the reference data the MVP solves on

**Generated. Do not edit.** Every file here is a row-for-row, byte-for-byte subset of
`docs/notes/data/`, produced by `carb3/data/build_reference_mvp.py`. Change the source tables
or the premises, then regenerate.

```
python3 carb3/data/build_reference_mvp.py           # rewrite this directory
python3 carb3/data/build_reference_mvp.py --check   # exit 1 naming any stale file
```

`make data-check` runs the `--check`. Run the MVP against this copy with

```
uv run --directory carb3 python -m carb3 --reference-root data/reference_mvp
```

`carb3/tests/test_reference_mvp.py` solves the three premises on both roots and asserts the
results agree.

## What it holds

The nine tables `carb3.load.REFERENCE_SCHEMA` reads, same header and column order as the
source, rows in source order, row text untouched (numbers are not reformatted). The three
premises (`mvp-minimal`, `mvp-dairy`, `mvp-cement`) sit at activities
{", ".join(f"`{a}`" for a in activities)} and clusters {", ".join(f"`{c}`" for c in clusters)}.

## Filtering rule per table

{rules}

## Row counts

| Table | Source rows | Subset rows |
|---|---|---|
{rows}

## What a subset changes

The reference tables as a whole are screened by `carb3.load.screen_units` (the section 3.2
admission screen), and its run report lists every unit it drops. Against this subset the
screen sees only the kept units, so the "admitted N units, dropped M" line and the drop list
cover fewer units than on the full tables. No unit the premises can reach is missing, so the
solves are the same.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check", action="store_true", help="exit 1 if the committed output is stale"
    )
    args = parser.parse_args(argv)
    files, _, _ = build()

    if args.check:
        stale = []
        for name, text in files.items():
            path = OUT / name
            if not path.is_file() or path.read_bytes() != text.encode("utf-8"):
                stale.append(name)
        stale += sorted(
            p.name for p in OUT.glob("*") if p.is_file() and p.name not in files
        ) if OUT.is_dir() else []
        if stale:
            print(
                "carb3/data/reference_mvp is stale: " + ", ".join(stale)
                + "\n  run: python3 carb3/data/build_reference_mvp.py",
                file=sys.stderr,
            )
            return 1
        print(f"reference_mvp: {len(files) - 1} tables up to date")
        return 0

    OUT.mkdir(exist_ok=True)
    for name, text in files.items():
        (OUT / name).write_bytes(text.encode("utf-8"))
    print(f"wrote {len(files)} files to {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
