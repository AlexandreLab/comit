"""survival.py — D11 survival function, computed before the LP.

Note 21 §4.3 is explicit that C4, e_{u,t} and the vintages are **mechanism, not driver**:
they change no number in this slice, because C2 (activity limited by available capacity) is
an inequality and an incumbent's capex is sunk, so the model abandons the incumbent at the
first buildable period regardless of age. These tests therefore assert **the decay itself**
— that surviving capacity falls as η_{u,t} says — and never that a build waits for a
retirement. That test would fail, and the plan says so.
"""

from __future__ import annotations

import pandas as pd
import pytest

from carb3 import survival

PERIODS: tuple[int, ...] = (2021, 2025, 2030, 2035, 2040, 2045, 2050)


def _unit_table() -> pd.DataFrame:
    """``unit.csv``'s two columns the survival function reads, plus one blank lifetime.

    13 of the reference table's 137 units carry a blank ``lifetime`` (§3.2); the screen drops
    them before the LP, and a vintage row naming one must not be aged silently.
    """
    return pd.DataFrame(
        [
            {"unit_id": "boiler_lt_gas", "lifetime": 25},
            {"unit_id": "heat_pump_lt_air", "lifetime": 20},
            {"unit_id": "kiln_cement_dry", "lifetime": 40},
            {"unit_id": "no_lifetime_unit", "lifetime": None},
        ]
    )


def test_signatures(assert_signature) -> None:
    assert_signature(
        survival, "survival_fraction", ("install_year", "lifetime_years", "year")
    )
    assert_signature(survival, "surviving_capacity", ("vintages", "unit", "periods"))


# --------------------------------------------------------------------------------------
# η — the survival fraction
# --------------------------------------------------------------------------------------


def test_survival_is_one_until_end_of_life_and_zero_after() -> None:
    """The archived baseline §5.3.1 tier-1 point mass: a cohort stands whole, then goes.

    A kiln commissioned in 2004 with a 40-year life stands until 2043 and is gone in 2044.
    """
    assert survival.survival_fraction(2004, 40, 2043) == 1.0
    assert survival.survival_fraction(2004, 40, 2044) == 0.0
    assert survival.survival_fraction(2004, 40, 2021) == 1.0


def test_lifetime_is_read_as_years_not_as_periods() -> None:
    """**The failure this prevents** (§10): a 25-year life read as 25 periods is a 125-year
    asset. A boiler commissioned in 2010 is gone by 2035, not by 2145."""
    assert survival.survival_fraction(2010, 25, 2030) == 1.0
    assert survival.survival_fraction(2010, 25, 2035) == 0.0
    # The period *index* would put the same unit alive throughout a seven-period horizon.
    assert survival.survival_fraction(2010, 25, 2050) == 0.0


def test_a_unit_already_past_its_lifetime_at_t0_survives_nothing() -> None:
    """A 1990 boiler with a 25-year life reaches 2021 already fifteen years past it.

    §5.3.1 clamps the final operating year to the base year so such a premise stays feasible
    on arrival; the contract here is the stricter one, which is safe in this slice only
    because C2 is an inequality and no stranding charge reads e_{u,t}.
    """
    assert survival.survival_fraction(1990, 25, 2021) == 0.0


def test_a_cohort_commissioned_after_the_period_is_clamped_not_negative() -> None:
    """§3.15 requires ``commissioned_year`` ≤ ``data_year``; a negative age is a base-year
    offset rather than a plant that has not been built."""
    assert survival.survival_fraction(2023, 25, 2021) == 1.0


def test_a_blank_lifetime_cannot_be_aged() -> None:
    with pytest.raises(ValueError, match="lifetime_years must be positive"):
        survival.survival_fraction(2010, 0, 2030)


# --------------------------------------------------------------------------------------
# e_{u,t} — surviving incumbent capacity
# --------------------------------------------------------------------------------------


def test_surviving_capacity_decays_as_eta_says() -> None:
    """The assertion note 21 §4.3 asks for: the **decay itself**, not a deferred build."""
    vintages = pd.DataFrame(
        [{"unit_id": "boiler_lt_gas", "commissioned_year": 2010, "capacity": 4.0}]
    )
    standing = survival.surviving_capacity(vintages, _unit_table(), PERIODS)
    by_period = dict(zip(standing["period"], standing["capacity"], strict=True))
    # A 25-year life from 2010 ends in 2035.
    assert by_period[2021] == pytest.approx(4.0)
    assert by_period[2030] == pytest.approx(4.0)
    assert by_period[2035] == pytest.approx(0.0)
    assert by_period[2050] == pytest.approx(0.0)
    # η is non-increasing in t, which is what §5.3.1 requires across every ageing tier.
    values = [by_period[year] for year in PERIODS]
    assert all(later <= earlier for earlier, later in zip(values, values[1:], strict=False))


def test_several_cohorts_decay_as_a_staircase() -> None:
    """§3.15's two-line works: a share-weighted sum of point masses, per §5.3.1."""
    vintages = pd.DataFrame(
        [
            {
                "unit_id": "kiln_cement_dry",
                "commissioned_year": 1998,
                "capacity": 10.0,
                "capacity_share": 0.6,
            },
            {
                "unit_id": "kiln_cement_dry",
                "commissioned_year": 2016,
                "capacity": 10.0,
                "capacity_share": 0.4,
            },
        ]
    )
    standing = survival.surviving_capacity(vintages, _unit_table(), PERIODS)
    by_period = dict(zip(standing["period"], standing["capacity"], strict=True))
    # A 40-year life: the 1998 line goes in 2038, the 2016 line in 2056.
    assert by_period[2021] == pytest.approx(10.0)
    assert by_period[2035] == pytest.approx(10.0)
    assert by_period[2040] == pytest.approx(4.0)
    assert by_period[2050] == pytest.approx(4.0)


def test_capacity_share_of_zero_is_honoured_rather_than_defaulted() -> None:
    """A stated 0.0 is a cohort with no capacity, not a missing column."""
    vintages = pd.DataFrame(
        [
            {
                "unit_id": "boiler_lt_gas",
                "commissioned_year": 2010,
                "capacity": 4.0,
                "capacity_share": 0.0,
            }
        ]
    )
    standing = survival.surviving_capacity(vintages, _unit_table(), PERIODS)
    assert standing["capacity"].abs().max() == pytest.approx(0.0)


def test_a_unit_with_no_vintage_row_carries_no_incumbent_capacity() -> None:
    """Zero rows for a premise is the normal case (§3.15), and it is not an error."""
    vintages = pd.DataFrame(
        [{"unit_id": "boiler_lt_gas", "commissioned_year": 2010, "capacity": 4.0}]
    )
    standing = survival.surviving_capacity(vintages, _unit_table(), PERIODS)
    assert set(standing["unit_id"]) == {"boiler_lt_gas"}
    assert "heat_pump_lt_air" not in set(standing["unit_id"])


def test_no_vintage_rows_at_all_returns_an_empty_frame() -> None:
    empty = survival.surviving_capacity(pd.DataFrame(), _unit_table(), PERIODS)
    assert list(empty.columns) == list(survival.SURVIVING_COLUMNS)
    assert len(empty) == 0


def test_the_frame_is_long_with_one_row_per_unit_and_period() -> None:
    vintages = pd.DataFrame(
        [
            {"unit_id": "boiler_lt_gas", "commissioned_year": 2010, "capacity": 4.0},
            {"unit_id": "heat_pump_lt_air", "commissioned_year": 2018, "capacity": 1.0},
        ]
    )
    standing = survival.surviving_capacity(vintages, _unit_table(), PERIODS)
    assert list(standing.columns) == list(survival.SURVIVING_COLUMNS)
    assert len(standing) == 2 * len(PERIODS)
    assert standing["period"].tolist() == list(PERIODS) * 2


def test_a_vintage_row_for_an_unknown_unit_raises() -> None:
    """A broken FK must not silently understate incumbent capacity."""
    vintages = pd.DataFrame(
        [{"unit_id": "not_a_unit", "commissioned_year": 2010, "capacity": 4.0}]
    )
    with pytest.raises(ValueError, match="no usable lifetime"):
        survival.surviving_capacity(vintages, _unit_table(), PERIODS)


def test_a_vintage_row_for_a_unit_with_a_blank_lifetime_raises() -> None:
    """13 units carry a blank ``lifetime``; one reaching the survival function is a screen
    failure, not something to age at zero."""
    vintages = pd.DataFrame(
        [{"unit_id": "no_lifetime_unit", "commissioned_year": 2010, "capacity": 4.0}]
    )
    with pytest.raises(ValueError, match="no usable lifetime"):
        survival.surviving_capacity(vintages, _unit_table(), PERIODS)


def test_missing_vintage_columns_fail_loud() -> None:
    vintages = pd.DataFrame([{"unit_id": "boiler_lt_gas", "commissioned_year": 2010}])
    with pytest.raises(ValueError, match="missing"):
        survival.surviving_capacity(vintages, _unit_table(), PERIODS)


def test_a_unit_table_without_a_lifetime_column_fails_loud() -> None:
    vintages = pd.DataFrame(
        [{"unit_id": "boiler_lt_gas", "commissioned_year": 2010, "capacity": 4.0}]
    )
    with pytest.raises(ValueError, match="'unit_id' and 'lifetime'"):
        survival.surviving_capacity(
            vintages, pd.DataFrame([{"unit_id": "boiler_lt_gas"}]), PERIODS
        )
