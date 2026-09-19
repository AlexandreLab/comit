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

Owed by T7.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def survival_fraction(install_year: int, lifetime_years: int, year: int) -> float:
    """η_{u,t} — the fraction of a vintage installed in ``install_year`` still standing at
    ``year``, given the unit's ``lifetime`` in **years**.

    Zero at and beyond end of life, including a unit already past its lifetime at t0.
    """
    raise NotImplementedError


def surviving_capacity(
    vintages: pd.DataFrame, unit: pd.DataFrame, periods: Sequence[int]
) -> pd.DataFrame:
    """e_{u,t} for every incumbent unit at a premise, over the period year vector.

    Long-form, one row per ``(unit_id, period)``. A unit with no vintage row carries no
    incumbent capacity rather than raising.
    """
    raise NotImplementedError
