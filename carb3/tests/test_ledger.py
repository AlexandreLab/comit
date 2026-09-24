"""ledger.py — cost by term, carrier mix, dispatch, build, disposal -> parquet.

The tables' *contents* are checked end to end in ``test_integration.py``, against a real
premise and a real solve. What is checked here is the shape of the contract and the two
things the ledger must refuse to do: decompose a solve that did not happen, and write
nothing where the screen dropped nothing.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
import pytest

from carb3 import build, ledger
from carb3.load import AdmissionScreen, UnitDrop


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
    """``build_ledger`` takes two arguments the scaffolded signature did not have.

    The scaffold named ``(result, sets, axis)``, none of which carries a price: κ, φ and L
    are in ``unit.csv`` and ``import_price``, ``carbon_price`` and ``discount_rate`` in
    ``scenario_parameters.csv``. ``cost_by_term``'s whole contract is to sum to the reported
    objective, and with those three arguments it cannot be computed at all. The fifth is
    ``tariff_override``, which has to reach the cost table for the same reason: the export
    term is priced from the same series the objective read, so a sensitivity run whose
    ledger ignored the override would not sum to its own objective.
    """
    assert_signature(
        ledger,
        "build_ledger",
        ("result", "sets", "axis", "reference", "tariff_override"),
    )
    assert_signature(ledger, "write_parquet", ("ledger", "report", "out_dir"))


def test_build_ledger_refuses_a_solve_that_did_not_happen() -> None:
    """§5.2: a non-optimal status is reported and has no pathway to decompose."""
    unsolved = build.SolveResult(
        status="warning",
        termination_condition="infeasible",
        objective=None,
        solution=None,
        n_variables=0,
        n_constraints=0,
        wall_clock_seconds=0.0,
    )
    with pytest.raises(ValueError, match="no solution"):
        ledger.build_ledger(unsolved, None, None, None)  # type: ignore[arg-type]


def test_write_parquet_writes_the_screen_list_even_when_it_is_empty(tmp_path: Path) -> None:
    """"Nothing was dropped" is a finding too, and an absent file cannot say it."""
    empty = pd.DataFrame()
    tables = ledger.Ledger(
        cost_by_term=empty, carrier_mix=empty, dispatch=empty, build=empty, disposal=empty
    )
    report = ledger.RunReport(
        premise_id="fx-empty",
        screen=AdmissionScreen(frozenset({"boiler_lt_gas"}), ()),
        n_variables=1,
        n_constraints=1,
        wall_clock_seconds=0.5,
        status="optimal",
    )
    written = ledger.write_parquet(tables, report, tmp_path)
    names = {path.name for path in written}
    assert names == {f"{table}.parquet" for table in ledger.LEDGER_TABLES} | {
        "run_report.parquet",
        "screen_dropped.parquet",
    }
    assert all(path.parent.name == "fx-empty" for path in written)
    dropped = pd.read_parquet(tmp_path / "fx-empty" / "screen_dropped.parquet")
    assert list(dropped.columns) == ["unit_id", "leg", "detail"]
    assert dropped.empty


def test_write_parquet_keeps_one_directory_per_premise(tmp_path: Path) -> None:
    """Two premises written to one root must not overwrite each other."""
    empty = pd.DataFrame()
    tables = ledger.Ledger(
        cost_by_term=empty, carrier_mix=empty, dispatch=empty, build=empty, disposal=empty
    )
    for premise_id in ("fx-a", "fx-b"):
        ledger.write_parquet(
            tables,
            ledger.RunReport(
                premise_id=premise_id,
                screen=AdmissionScreen(
                    frozenset(), (UnitDrop("heat_exchanger_lt_steam", "capex", "blank"),)
                ),
                n_variables=2,
                n_constraints=3,
                wall_clock_seconds=0.25,
                status="optimal",
            ),
            tmp_path,
        )
    assert sorted(path.name for path in tmp_path.iterdir()) == ["fx-a", "fx-b"]
    report = pd.read_parquet(tmp_path / "fx-b" / "run_report.parquet")
    assert report.loc[0, "n_units_dropped"] == 1
    assert report.loc[0, "wall_clock_seconds"] == pytest.approx(0.25)
