"""load.py — reference + premise tables -> typed records; the §3.2 screen."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from carb3 import load


def test_roots_resolve_from_the_repo_not_the_caller() -> None:
    """Plan §3.1: a documented default resolved from the repo root, never the caller's cwd."""
    assert load.DEFAULT_REFERENCE_ROOT == load.REPO_ROOT / "docs" / "notes" / "data"
    assert load.DEFAULT_REFERENCE_ROOT.is_absolute()
    assert load.DEFAULT_PREMISE_ROOT == load.REPO_ROOT / "carb3" / "data" / "premises"


def test_period_years_are_the_real_vector() -> None:
    """Plan §6.4: a 4-year first gap and 5-year gaps thereafter, not a uniform delta."""
    assert load.PERIOD_YEARS == (2021, 2025, 2030, 2035, 2040, 2045, 2050)


def test_reference_tables_carry_the_seven_tables() -> None:
    fields = {f.name for f in dataclasses.fields(load.ReferenceTables)}
    assert fields == {
        "carrier",
        "unit",
        "unit_input_output",
        "unit_eligibility",
        "scenario_parameters",
        "activity_process_duty_profile",
        "activity_process_register",
    }


def test_premise_tables_carry_four_and_not_process_duty() -> None:
    """Plan §3.4: process_duty is derived by the minimal A2, not an input table."""
    fields = {f.name for f in dataclasses.fields(load.PremiseTables)}
    assert fields == {
        "premise_record",
        "premise_process_detail",
        "premise_process_unit",
        "premise_process_vintage",
    }
    assert "process_duty" not in fields


def test_screen_reports_drops_rather_than_raising() -> None:
    fields = {f.name for f in dataclasses.fields(load.AdmissionScreen)}
    assert fields == {"admitted", "dropped"}
    assert {f.name for f in dataclasses.fields(load.UnitDrop)} == {
        "unit_id",
        "leg",
        "detail",
    }


def test_signatures(assert_signature) -> None:
    assert_signature(load, "load_reference_tables", ("root",))
    assert_signature(load, "load_premise_tables", ("premise_id", "root"))
    assert_signature(load, "screen_units", ("reference", "periods"))


def test_bodies_are_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError):
        load.load_reference_tables(Path("."))
    with pytest.raises(NotImplementedError):
        load.load_premise_tables("mvp-minimal", Path("."))
    with pytest.raises(NotImplementedError):
        load.screen_units(reference=None, periods=())  # type: ignore[arg-type]
