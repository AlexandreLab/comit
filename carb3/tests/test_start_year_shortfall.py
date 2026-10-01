"""The start-year adequacy check in sets.py: can the incumbents alone meet every duty?"""

from __future__ import annotations

import pandas as pd
import pytest

from carb3.sets import (
    Duty,
    ModelSets,
    diagnose_start_year_shortfall,
    explain_start_year_shortfall,
)

PERIODS = (2021, 2025)


def _duty(process_id: str, carrier_id: str, quantity: float) -> Duty:
    return Duty(
        premise_id="p",
        process_id=process_id,
        carrier_id=carrier_id,
        grade_rank=None,
        quantity={year: quantity for year in PERIODS},
    )


def _sets(duties, eligible, max_share=None) -> ModelSets:
    return ModelSets(
        periods=PERIODS,
        duties=tuple(duties),
        units=frozenset(u for units in eligible.values() for u in units),
        eligible={key: frozenset(units) for key, units in eligible.items()},
        earliest_year={},
        max_share=max_share or {},
        min_duty={},
    )


def _unit_table(*unit_ids: str, alpha: float = 1.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "unit_id": list(unit_ids),
            "capacity_to_activity_factor": [1.0] * len(unit_ids),
            "availability_factor": [alpha] * len(unit_ids),
        }
    )


def _surviving(capacities: dict[str, float], period: int = 2021) -> pd.DataFrame:
    return pd.DataFrame(
        [{"unit_id": u, "period": period, "capacity": c} for u, c in capacities.items()]
    )


HEAT = _duty("site_services", "heat_60_100", 0.549)
MOTIVE = _duty("site_services", "motive_power", 0.451)


def test_shares_that_match_the_duties_pass() -> None:
    sets = _sets([HEAT, MOTIVE], {HEAT.key: {"heat_pump"}, MOTIVE.key: {"motor"}})
    surviving = _surviving({"heat_pump": 0.549, "motor": 0.451})
    unit = _unit_table("heat_pump", "motor")
    assert diagnose_start_year_shortfall(sets, surviving, unit) is None


def test_a_share_below_the_duty_only_that_unit_serves_is_named() -> None:
    """The README's worked case: 0.40 / 0.60 instead of 0.549 / 0.451."""
    sets = _sets([HEAT, MOTIVE], {HEAT.key: {"heat_pump"}, MOTIVE.key: {"motor"}})
    surviving = _surviving({"heat_pump": 0.40, "motor": 0.60})
    shortfall = diagnose_start_year_shortfall(sets, surviving, _unit_table("heat_pump", "motor"))
    assert shortfall is not None
    assert shortfall.period == 2021
    assert shortfall.duties == (HEAT.key,)
    assert shortfall.units == ("heat_pump",)
    assert shortfall.shortfall == pytest.approx(0.149)
    assert "site_services on heat_60_100" in explain_start_year_shortfall(shortfall)


def test_a_shared_unit_is_counted_once_not_once_per_duty() -> None:
    """One boiler eligible for two duties: a per-duty sum would pass it twice."""
    low = _duty("boiler", "heat_60_100", 0.6)
    high = _duty("boiler", "heat_100_150", 0.6)
    sets = _sets([low, high], {low.key: {"boiler"}, high.key: {"boiler"}})
    shortfall = diagnose_start_year_shortfall(
        sets, _surviving({"boiler": 1.0}), _unit_table("boiler")
    )
    assert shortfall is not None
    assert shortfall.duties == (low.key, high.key) or shortfall.duties == (high.key, low.key)
    assert shortfall.demand == pytest.approx(1.2)
    assert shortfall.deliverable == pytest.approx(1.0)


def test_availability_is_applied() -> None:
    """mvp-minimal's trap: a capacity equal to the duty falls short at α below 1."""
    duty = _duty("boiler", "heat_60_100", 0.1)
    sets = _sets([duty], {duty.key: {"boiler"}})
    shortfall = diagnose_start_year_shortfall(
        sets, _surviving({"boiler": 0.1}), _unit_table("boiler", alpha=0.9823)
    )
    assert shortfall is not None
    assert shortfall.shortfall == pytest.approx(0.1 - 0.09823)


def test_a_max_share_cap_limits_the_edge() -> None:
    duty = _duty("boiler", "heat_60_100", 1.0)
    sets = _sets(
        [duty],
        {duty.key: {"coal_boiler", "gas_boiler"}},
        max_share={(duty.key, "coal_boiler"): 0.0},
    )
    surviving = _surviving({"coal_boiler": 1.0, "gas_boiler": 0.5})
    shortfall = diagnose_start_year_shortfall(
        sets, surviving, _unit_table("coal_boiler", "gas_boiler")
    )
    assert shortfall is not None
    assert shortfall.shortfall == pytest.approx(0.5)


def test_only_the_first_period_is_checked() -> None:
    """Later periods can build, so a shortfall there is a cost, not an infeasibility."""
    sets = _sets([HEAT], {HEAT.key: {"heat_pump"}})
    surviving = pd.concat(
        [_surviving({"heat_pump": 0.549}, 2021), _surviving({"heat_pump": 0.0}, 2025)]
    )
    assert (
        diagnose_start_year_shortfall(sets, surviving, _unit_table("heat_pump"))
        is None
    )
