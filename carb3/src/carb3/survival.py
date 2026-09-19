"""D11 (existing plant has an age) survival function, computed before the LP.

Surviving incumbent capacity e_{u,t} is a pure-parameter routine: it depends on the install
year in ``premise_process_vintage`` and the unit's ``lifetime``, and on nothing the solver
decides. Computing it ahead of the LP keeps C4 (incumbent ageing) a bound rather than a
recursion.

**This is mechanism, not driver** (§4.3). C4, e_{u,t}, this function and
``premise_process_vintage`` change no number in the slice — C2 is an inequality and C1 is an
equality, so nothing compels an incumbent to run, and §4.2's carbon term makes the model
abandon it at the first buildable period whatever its age. They are built because ``MF-43``
is a Must at M2. The test asserts **the decay itself**, that surviving capacity falls as
η_{u,t} says, not that a build waits for it.

Lifetimes convert against **actual years remaining**, never against a uniform Δ (§6.4).

**Which evidence tier this is, and why it is the only one reachable here.** The archived
baseline §5.3.1 gives the survival function three tiers: tier 1 ``process_known``, a point
mass on a ``premise_process_vintage`` cohort's commissioning year; tier 2
``premise_bounded``, a window ``[0, clamp(A, 0, L)]`` from ``premise_record.construction_year``;
and tier 3 ``uniform_default``, the window ``[0, L]`` whose η is COMIT's straight line. Only
**tier 1** is expressible through the two signatures below. :func:`survival_fraction` takes a
single ``install_year`` and so cannot carry a window, and :func:`surviving_capacity` is handed
``vintages`` and ``unit`` and never ``premise_record``, so the tier-2 bound is not in reach;
tier 3 needs an incumbent capacity, which in this slice arrives only on a vintage row. A unit
with no vintage row therefore carries **no** incumbent capacity, as the docstring below
requires, rather than falling back to a uniform-life pool.

Owed by T7.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import pandas as pd

#: Columns :func:`surviving_capacity` returns, long-form, one row per ``(unit_id, period)``.
SURVIVING_COLUMNS: tuple[str, ...] = ("unit_id", "period", "capacity")


def survival_fraction(install_year: int, lifetime_years: int, year: int) -> float:
    """η_{u,t} — the fraction of a vintage installed in ``install_year`` still standing at
    ``year``, given the unit's ``lifetime`` in **years**.

    Zero at and beyond end of life, including a unit already past its lifetime at t0.

    This is the archived baseline §5.3.1 tier-1 point mass: a cohort is one tranche of
    capacity with one commissioning year, so it stands whole until its final operating year
    and is gone the period after. The elapsed term is **actual years**, never a period count
    — the failure this exists to prevent is a 25-year life read as 25 periods (§10).

    A cohort whose ``install_year`` is later than ``year`` is treated as standing in full.
    §3.15 requires ``commissioned_year`` ≤ ``data_year``, so a negative age is a base-year
    offset rather than a plant that has not been built, and clamping it is the harmless
    reading. Note the one divergence from §5.3.1: that section clamps the final operating
    year to the base year (Ω = max(g + L − 1, y_{t_0})) so a premise arriving with plant
    already past its life stays feasible. Here the scaffolded contract is explicit that such
    a unit returns zero, which is safe in this slice only because C2 (activity limited by
    available capacity) is an inequality and no stranding charge reads e_{u,t}.
    """
    if lifetime_years <= 0:
        raise ValueError(
            f"lifetime_years must be positive, got {lifetime_years!r}; a unit with no "
            "lifetime cannot be aged and must not reach the survival function"
        )
    age = max(0, int(year) - int(install_year))
    return 1.0 if age < int(lifetime_years) else 0.0


def surviving_capacity(
    vintages: pd.DataFrame, unit: pd.DataFrame, periods: Sequence[int]
) -> pd.DataFrame:
    """e_{u,t} for every incumbent unit at a premise, over the period year vector.

    Long-form, one row per ``(unit_id, period)``. A unit with no vintage row carries no
    incumbent capacity rather than raising.

    ``vintages`` is ``premise_process_vintage`` (§3.15), one row per cohort, and must carry
    ``unit_id``, ``commissioned_year`` and ``capacity``. Where a ``capacity_share`` column is
    present it scales that row's capacity, which is how §3.15's cohort split of one process's
    existing capacity is written: several rows for one unit, shares summing to 1. Cohorts are
    summed per unit, so the result is §5.3.1's share-weighted sum, and a two-cohort unit
    decays as a staircase rather than in one step.

    ``unit`` is the reference ``unit`` table and supplies ``lifetime`` in years. A vintage row
    naming a unit absent from it, or one whose ``lifetime`` is blank, is a broken input and
    raises: silently dropping it would understate incumbent capacity, which is the failure
    §3.15's "shares sum" rule exists to prevent.
    """
    period_years = [int(year) for year in periods]
    empty = pd.DataFrame(
        {
            "unit_id": pd.Series(dtype="object"),
            "period": pd.Series(dtype="int64"),
            "capacity": pd.Series(dtype="float64"),
        }
    )
    if vintages is None or len(vintages) == 0 or not period_years:
        return empty

    missing = {"unit_id", "commissioned_year", "capacity"} - set(vintages.columns)
    if missing:
        raise ValueError(
            f"premise_process_vintage is missing {sorted(missing)}; "
            f"surviving_capacity needs {sorted({'unit_id', 'commissioned_year', 'capacity'})}"
        )

    lifetimes = _lifetimes(unit)
    unknown = sorted(set(vintages["unit_id"]) - set(lifetimes))
    if unknown:
        raise ValueError(
            "premise_process_vintage names units with no usable lifetime in the reference "
            f"unit table: {unknown}. A vintage row cannot be aged without one"
        )

    totals: dict[str, list[float]] = {}
    for row in vintages.itertuples(index=False):
        unit_id = str(row.unit_id)
        capacity = float(row.capacity) * _share(getattr(row, "capacity_share", None))
        install_year = int(row.commissioned_year)
        lifetime = lifetimes[unit_id]
        standing = totals.setdefault(unit_id, [0.0] * len(period_years))
        for index, year in enumerate(period_years):
            standing[index] += capacity * survival_fraction(install_year, lifetime, year)

    records = [
        {"unit_id": unit_id, "period": year, "capacity": standing[index]}
        for unit_id, standing in sorted(totals.items())
        for index, year in enumerate(period_years)
    ]
    return pd.DataFrame.from_records(records, columns=list(SURVIVING_COLUMNS))


def _lifetimes(unit: pd.DataFrame) -> dict[str, int]:
    """``unit_id`` → ``lifetime`` in years, skipping units whose lifetime is blank.

    13 of the reference table's 137 units carry a blank ``lifetime`` (§3.2). They are dropped
    by the admission screen before they reach the LP; here a vintage row naming one raises,
    through the caller's unknown-unit check.
    """
    if unit is None or "unit_id" not in unit.columns or "lifetime" not in unit.columns:
        raise ValueError("the reference unit table must carry 'unit_id' and 'lifetime'")
    lifetimes: dict[str, int] = {}
    for unit_id, lifetime in zip(unit["unit_id"], unit["lifetime"], strict=True):
        value = _as_years(lifetime)
        if value is not None:
            lifetimes[str(unit_id)] = value
    return lifetimes


def _share(value: object) -> float:
    """A cohort's ``capacity_share``, defaulting to 1 where the column is absent or blank.

    A stated 0.0 is honoured — it is a cohort with no capacity, not a missing column — which
    is why this is not written as ``value or 1.0``.
    """
    if value is None:
        return 1.0
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 1.0
        value = float(text)
    number = float(value)  # type: ignore[arg-type]
    return 1.0 if math.isnan(number) else number


def _as_years(value: object) -> int | None:
    """Coerce a lifetime cell to whole years, or ``None`` where it is blank."""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        value = float(text)
    number = float(value)  # type: ignore[arg-type]
    if math.isnan(number) or number <= 0:
        return None
    return int(round(number))
