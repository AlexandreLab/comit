"""build.py — variables, C1-C5, C8, C10, objective, solve."""

from __future__ import annotations

import dataclasses

import pytest

from carb3 import build


def test_solver_settings_match_the_cement_fixture() -> None:
    """Cement worked example §12: HiGHS, presolve on, single-threaded."""
    settings = build.SolverSettings()
    assert settings.solver == "highs"
    assert settings.presolve == "on"
    assert settings.threads == 1


def test_period_axis_is_a_vector_not_a_formula() -> None:
    """Plan §6.4: spans and delta_t are derived per period, not from a uniform delta."""
    fields = {f.name for f in dataclasses.fields(build.PeriodAxis)}
    assert fields == {"years", "spans", "discount_factors"}


def test_solve_result_reports_status_and_size() -> None:
    """Plan §5.2 and §5.3: a non-optimal status is reported, and the counts are printed."""
    fields = {f.name for f in dataclasses.fields(build.SolveResult)}
    assert {"status", "termination_condition", "objective"} <= fields
    assert {"n_variables", "n_constraints", "wall_clock_seconds"} <= fields


def test_signatures(assert_signature) -> None:
    assert_signature(build, "period_axis", ("years", "discount_rate"))
    assert_signature(
        build, "lifetime_in_periods", ("axis", "lifetime_years", "built_at")
    )
    assert_signature(build, "build_model", ("sets", "surviving", "axis", "reference"))
    assert_signature(build, "solve", ("model", "settings"))
    assert_signature(build, "check_constraint_rows", ("model", "result", "tolerance"))


def test_bodies_are_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError):
        build.period_axis((2021, 2025), 0.035)
    with pytest.raises(NotImplementedError):
        build.lifetime_in_periods(None, 25, 2025)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        build.build_model(None, None, None, None)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        build.solve(None)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        build.check_constraint_rows(None, None)  # type: ignore[arg-type]
