"""``python -m carb3.report <dir> [<dir> …]`` — rebuild site reports from parquet alone.

Each argument is either one premise's ledger directory (it holds ``run_report.parquet``) or
a root holding several, as ``python -m carb3 --out-dir`` writes them. No solve is run:
changing the page never costs one.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from carb3.report.render import write_report
from carb3.report.sankey_data import ReportDataError


def premise_dirs(path: Path) -> list[Path]:
    """``path`` itself if it is a premise's ledger directory, else its premise subdirectories."""
    if (path / "run_report.parquet").is_file():
        return [path]
    return sorted(child for child in path.iterdir() if (child / "run_report.parquet").is_file())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m carb3.report",
        description="Rebuild site_report.html from a premise's parquet ledger, without re-solving.",
    )
    parser.add_argument("paths", nargs="+", type=Path, metavar="DIR")
    args = parser.parse_args(argv)

    failed = 0
    found = 0
    for root in args.paths:
        if not root.is_dir():
            print(f"{root}: not a directory", file=sys.stderr)
            failed += 1
            continue
        for directory in premise_dirs(root):
            found += 1
            try:
                print(f"written          {write_report(directory)}")
            except ReportDataError as error:
                print(f"no report        {directory}: {error}", file=sys.stderr)
                failed += 1
    if not found and not failed:
        print("no premise ledger found under the paths given", file=sys.stderr)
        return 1
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover - exercised through the Makefile
    sys.exit(main())
