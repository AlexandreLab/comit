#!/usr/bin/env python3
"""Rewrite ``unit_input_output.csv`` from three booleans to one ``role`` enum.

§3.6 used to key ``unit_input_output`` on ``(unit_id, carrier_id)`` and to carry
``is_primary_output``, ``is_reject`` and ``is_fuel_input`` as separate flags.  That key
admitted one row per carrier, so no unit could both consume and produce the same carrier:
every store (charge and discharge on one carrier) and every capture train with a fired
reboiler (host CO2 in, reboiler CO2 out) was unwritable.  The key is now
``(unit_id, carrier_id, role)``.

This script performs the one-time migration and is committed so that the classification of
the 446 existing rows is auditable rather than asserted.  It is idempotent: a file already
carrying ``role`` is left alone.

The three booleans were mutually exclusive on every row and agreed with the sign of
``coefficient`` on every row, so five of the seven roles fall straight out of them.  The two
that do not — an unflagged row is an input, a co-product or an emission — are separated by
``carrier.carrier_kind``, which is the same discriminator the reader was applying by eye.

    negative, is_fuel_input        -> fuel_input
    negative, emission carrier     -> emission_input
    negative, otherwise            -> aux_input
    positive, is_primary_output    -> primary_output
    positive, is_reject            -> reject
    positive, emission carrier     -> emission
    positive, otherwise            -> coproduct

Usage:  python3 migrate_io_roles.py [--check]

``--check`` reports what would change and writes nothing.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
IO_CSV = DATA / "unit_input_output.csv"
CARRIER_CSV = DATA / "carrier.csv"

OLD_COLUMNS = [
    "unit_id", "carrier_id", "coefficient", "is_primary_output", "is_reject",
    "is_fuel_input", "provenance", "confidence", "provenance_ref",
]
NEW_COLUMNS = [
    "unit_id", "carrier_id", "coefficient", "role",
    "provenance", "confidence", "provenance_ref",
]


def emission_carriers() -> set[str]:
    with CARRIER_CSV.open(newline="", encoding="utf-8") as fh:
        return {
            r["carrier_id"] for r in csv.DictReader(fh)
            if r["carrier_kind"] == "emission"
        }


def role_for(row: dict[str, str], emissions: set[str]) -> str:
    coefficient = float(row["coefficient"])
    is_emission = row["carrier_id"] in emissions
    if coefficient < 0:
        if row["is_fuel_input"] == "TRUE":
            return "fuel_input"
        return "emission_input" if is_emission else "aux_input"
    if row["is_primary_output"] == "TRUE":
        return "primary_output"
    if row["is_reject"] == "TRUE":
        return "reject"
    return "emission" if is_emission else "coproduct"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report the classification and write nothing")
    args = ap.parse_args()

    with IO_CSV.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        columns = list(reader.fieldnames or [])
        rows = list(reader)

    if columns == NEW_COLUMNS:
        print(f"{IO_CSV.name}: already migrated, {len(rows)} rows")
        return 0
    if columns != OLD_COLUMNS:
        print(f"{IO_CSV.name}: unexpected columns {columns}", file=sys.stderr)
        return 1

    emissions = emission_carriers()
    counts: dict[str, int] = {}
    out: list[dict[str, str]] = []
    for i, row in enumerate(rows, start=2):
        # A row flagged twice would silently take the first branch of role_for, so the
        # mutual exclusivity the mapping relies on is asserted rather than assumed.
        flags = sum(row[c] == "TRUE"
                    for c in ("is_primary_output", "is_reject", "is_fuel_input"))
        if flags > 1:
            print(f"row {i}: {row['unit_id']}/{row['carrier_id']} carries {flags} flags",
                  file=sys.stderr)
            return 1
        # The other premise: the flags agree with the sign. A fuel input with a positive
        # coefficient, or a primary output with a negative one, would be silently
        # reclassified rather than reported, and this file exists to be auditable.
        coefficient = float(row["coefficient"])
        if coefficient == 0:
            print(f"row {i}: {row['unit_id']}/{row['carrier_id']} has a zero coefficient, "
                  "which no role describes", file=sys.stderr)
            return 1
        consumed = row["is_fuel_input"] == "TRUE"
        produced = row["is_primary_output"] == "TRUE" or row["is_reject"] == "TRUE"
        if (consumed and coefficient > 0) or (produced and coefficient < 0):
            print(f"row {i}: {row['unit_id']}/{row['carrier_id']} flags disagree with the "
                  f"sign of {coefficient}", file=sys.stderr)
            return 1
        role = role_for(row, emissions)
        counts[role] = counts.get(role, 0) + 1
        out.append({
            "unit_id": row["unit_id"],
            "carrier_id": row["carrier_id"],
            "coefficient": row["coefficient"],
            "role": role,
            "provenance": row["provenance"],
            "confidence": row["confidence"],
            "provenance_ref": row["provenance_ref"],
        })

    for role in sorted(counts):
        print(f"  {role:<16} {counts[role]:>4}")
    print(f"  {'total':<16} {len(out):>4}")
    if args.check:
        print(f"{IO_CSV.name}: --check, nothing written")
        return 0

    with IO_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=NEW_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(out)
    print(f"{IO_CSV.name}: rewritten with `role`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
