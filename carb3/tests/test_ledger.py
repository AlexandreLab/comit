"""ledger.py — cost by term, carrier mix, dispatch, build, disposal -> parquet."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from carb3 import ledger


def test_ledger_carries_the_five_output_tables() -> None:
    fields = {f.name for f in dataclasses.fields(ledger.Ledger)}
    assert fields == {
        "cost_by_term",
        "carrier_mix",
        "dispatch",
        "build",
        "disposal",
    }


def test_run_report_carries_the_screen_and_the_g1_measurement() -> None:
    """Plan §5.4: the dropped-unit list is written to the run report; §5.3 prints the counts."""
    fields = {f.name for f in dataclasses.fields(ledger.RunReport)}
    assert {"premise_id", "screen", "status"} <= fields
    assert {"n_variables", "n_constraints", "wall_clock_seconds"} <= fields


def test_signatures(assert_signature) -> None:
    assert_signature(ledger, "build_ledger", ("result", "sets", "axis"))
    assert_signature(ledger, "write_parquet", ("ledger", "report", "out_dir"))


def test_bodies_are_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError):
        ledger.build_ledger(None, None, None)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        ledger.write_parquet(None, None, Path("."))  # type: ignore[arg-type]
