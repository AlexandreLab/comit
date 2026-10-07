"""ledger.py — cost by term, carrier mix, dispatch, build, disposal, unit flow -> parquet.

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
from carb3.sets import EligibilityDrop


def test_ledger_carries_the_seven_output_tables() -> None:
    fields = {f.name for f in dataclasses.fields(ledger.Ledger)}
    assert fields == {
        "cost_by_term",
        "carrier_mix",
        "dispatch",
        "build",
        "disposal",
        "unit_flow",
        "capture_by_host",
    }
    assert set(ledger.LEDGER_TABLES) == fields


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
        cost_by_term=empty,
        carrier_mix=empty,
        dispatch=empty,
        build=empty,
        disposal=empty,
        unit_flow=empty,
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
        "eligibility_dropped.parquet",
        "sub_minimum_recovery.parquet",
    }
    assert all(path.parent.name == "fx-empty" for path in written)
    dropped = pd.read_parquet(tmp_path / "fx-empty" / "screen_dropped.parquet")
    assert list(dropped.columns) == ["unit_id", "leg", "detail"]
    assert dropped.empty
    refused = pd.read_parquet(tmp_path / "fx-empty" / "eligibility_dropped.parquet")
    assert list(refused.columns) == ["premise_id", "process_id", "unit_id", "reason", "detail"]
    assert refused.empty
    run = pd.read_parquet(tmp_path / "fx-empty" / "run_report.parquet")
    assert run.loc[0, "n_units_dropped_at_premise"] == 0
    small = pd.read_parquet(tmp_path / "fx-empty" / "sub_minimum_recovery.parquet")
    assert list(small.columns) == ["unit_id", "period", "new_capacity", "min_viable_scale"]
    assert small.empty


def test_eligibility_drops_get_their_own_table_not_the_screens(tmp_path: Path) -> None:
    """A ``min_duty`` or ``max_share`` drop is per process and the unit stays admitted, so
    it must not be mixed into ``screen_dropped``, which is a per-unit admission list."""
    empty = pd.DataFrame()
    tables = ledger.Ledger(
        cost_by_term=empty, carrier_mix=empty, dispatch=empty,
        build=empty, disposal=empty, unit_flow=empty,
    )
    drop = EligibilityDrop(
        "fx-dairy", "boiler_steam_hot_water", "boiler_lt_coal", "max_share",
        "max_share 0.00 is a prohibition on heat_60_100",
    )
    report = ledger.RunReport(
        premise_id="fx-dairy",
        screen=AdmissionScreen(frozenset({"boiler_lt_coal"}), ()),
        n_variables=1,
        n_constraints=1,
        wall_clock_seconds=0.5,
        status="optimal",
        eligibility_dropped=(drop,),
    )
    ledger.write_parquet(tables, report, tmp_path)
    refused = pd.read_parquet(tmp_path / "fx-dairy" / "eligibility_dropped.parquet")
    assert refused.to_dict("records") == [dataclasses.asdict(drop)]
    assert pd.read_parquet(tmp_path / "fx-dairy" / "screen_dropped.parquet").empty


def test_write_parquet_lists_the_premise_drops_after_the_screen_list(tmp_path: Path) -> None:
    """The per-premise screen's drops share the §3.2 list's file, told apart by ``leg``,
    and the run report counts them separately from the §3.2 screen's."""
    empty = pd.DataFrame()
    tables = ledger.Ledger(
        cost_by_term=empty,
        carrier_mix=empty,
        dispatch=empty,
        build=empty,
        disposal=empty,
        unit_flow=empty,
    )
    report = ledger.RunReport(
        premise_id="fx-dairy",
        screen=AdmissionScreen(
            frozenset(), (UnitDrop("heat_exchanger_lt_steam", "capex", "blank"),)
        ),
        n_variables=1,
        n_constraints=1,
        wall_clock_seconds=0.5,
        status="optimal",
        premise_dropped=(
            UnitDrop(
                "chp_bfg_gas_turbine",
                build.UNREACHABLE_INPUT_LEG,
                "consumes blast_furnace_gas, which this premise can neither import nor produce",
            ),
        ),
    )
    ledger.write_parquet(tables, report, tmp_path)
    dropped = pd.read_parquet(tmp_path / "fx-dairy" / "screen_dropped.parquet")
    assert list(dropped["leg"]) == ["capex", "unreachable_input"]
    assert dropped.loc[1, "unit_id"] == "chp_bfg_gas_turbine"
    run = pd.read_parquet(tmp_path / "fx-dairy" / "run_report.parquet")
    assert run.loc[0, "n_units_dropped"] == 1
    assert run.loc[0, "n_units_dropped_at_premise"] == 1


def test_write_parquet_keeps_one_directory_per_premise(tmp_path: Path) -> None:
    """Two premises written to one root must not overwrite each other."""
    empty = pd.DataFrame()
    tables = ledger.Ledger(
        cost_by_term=empty,
        carrier_mix=empty,
        dispatch=empty,
        build=empty,
        disposal=empty,
        unit_flow=empty,
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


def _build_rows(*rows: tuple[str, int, float]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "unit_id": unit_id, "period": period, "new_capacity": new,
                "available_capacity": new, "surviving_capacity": 0.0, "built_standing": new,
            }
            for unit_id, period, new in rows
        ]
    )


def test_a_recovery_unit_built_below_its_min_viable_scale_is_reported() -> None:
    """§3.5 and §5.7: the screen decides only whether a recovery unit is offered, and the LP
    stays linear, so it may still build one smaller than ``min_viable_scale``. That is
    reported after the solve, never constrained: (unit, period, new capacity, the floor) for
    every positive build below the floor. A build at or above it, a zero build and a unit
    that is not a recovery unit are not listed."""
    from carb3.load import load_reference_tables

    reference = load_reference_tables()
    scale = reference.unit.set_index("unit_id")["min_viable_scale"]
    floor = float(scale.loc["economiser_flue_condensing"])
    table = _build_rows(
        ("economiser_flue_condensing", 2025, 0.0),
        ("economiser_flue_condensing", 2030, floor * 0.5),
        ("economiser_flue_condensing", 2035, floor),
        ("boiler_lt_gas", 2030, 1e-6),
    )
    found = ledger.check_recovery_scale(table, reference)
    assert found == (
        ledger.SubMinimumBuild("economiser_flue_condensing", 2030, floor * 0.5, floor),
    )


def test_sub_minimum_builds_are_written_to_their_own_table(tmp_path: Path) -> None:
    empty = pd.DataFrame()
    tables = ledger.Ledger(
        cost_by_term=empty, carrier_mix=empty, dispatch=empty,
        build=empty, disposal=empty, unit_flow=empty,
    )
    small = ledger.SubMinimumBuild("economiser_flue_condensing", 2030, 0.001432, 0.00169)
    report = ledger.RunReport(
        premise_id="fx-dairy",
        screen=AdmissionScreen(frozenset(), ()),
        n_variables=1,
        n_constraints=1,
        wall_clock_seconds=0.5,
        status="optimal",
        sub_minimum=(small,),
    )
    ledger.write_parquet(tables, report, tmp_path)
    written = pd.read_parquet(tmp_path / "fx-dairy" / "sub_minimum_recovery.parquet")
    assert written.to_dict("records") == [dataclasses.asdict(small)]
