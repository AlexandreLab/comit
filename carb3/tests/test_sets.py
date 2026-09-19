"""sets.py — minimal A2; Q, U, U_q via the three-table join; C10 widening; diagnosis."""

from __future__ import annotations

import dataclasses

import pytest

from carb3 import sets


def test_duty_carries_the_derived_structure() -> None:
    """Plan §3.3: which duty, on which carrier, at which grade_rank; only quantity is hand-written."""
    fields = {f.name for f in dataclasses.fields(sets.Duty)}
    assert fields == {
        "premise_id",
        "process_id",
        "carrier_id",
        "grade_rank",
        "quantity",
    }


def test_model_sets_carry_the_three_eligibility_columns() -> None:
    """Plan §3.1: earliest_year, max_share and min_duty are all live and all honoured."""
    fields = {f.name for f in dataclasses.fields(sets.ModelSets)}
    assert {"earliest_year", "max_share", "min_duty"} <= fields
    assert {"periods", "duties", "units", "eligible"} <= fields


def test_unservable_duty_names_premise_and_period() -> None:
    """Plan §5.2: infeasibility is diagnosed by name, not raised."""
    fields = {f.name for f in dataclasses.fields(sets.UnservableDuty)}
    assert fields == {"duty", "period", "removed"}


def test_signatures(assert_signature) -> None:
    assert_signature(sets, "derive_duties", ("reference", "premise", "periods"))
    assert_signature(sets, "eligible_units", ("reference", "duty", "admitted"))
    assert_signature(sets, "build_sets", ("reference", "premise", "screen", "periods"))
    assert_signature(sets, "diagnose_unservable_duties", ("sets", "screen"))


def test_bodies_are_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError):
        sets.derive_duties(None, None, ())  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        sets.eligible_units(None, None, frozenset())  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        sets.build_sets(None, None, None, ())  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        sets.diagnose_unservable_duties(None, None)  # type: ignore[arg-type]
