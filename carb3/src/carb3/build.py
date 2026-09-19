"""Variables, C1-C5, C8, C10, objective, solve.

The model is the live spec §5 with terms switched off (plan §2). Nothing is invented;
features are removed, never added.

Variables in: n_{u,t} new capacity, a_{u,t} capacity available, z_{u,q,t} activity
dispatched to duty, e_{u,t} surviving incumbent capacity, m_{c,t} / m_{c,k,t} import, and
d_{c,t} **disposal**. Out: h_{c->c',t} cascade (C10 is enforced by eligibility instead),
z°_{u,t} undispatched primary output, r_{u,t} early retirement, x_{c,k,t} export, w_{k,t}
reinforcement.

**d_{c,t} is not optional** (§2.2). 59 ``reject`` rows from 59 distinct units all run into
``heat_lt60``, which is grade 1 — the bottom, so there is nothing to cascade to — and exactly
one unit consumes it. Without a disposal variable C8 forces every fuel-fired low-temperature
boiler to zero. It is gated on ``carrier_kind``, and the gate is the whole safety argument:
``intermediate`` and ``emission`` carriers may be disposed of, ``primary`` and ``product``
may not, or the model could import gas and dump it.

**Carbon is charged on venting, not on fuel.** Z^carbon reads d_{c,t} over carriers whose
``carrier.carbon_charge`` is ``charged``, less the biogenic credit, exactly as §5.4 writes it.

Constraints in: C1 (duty satisfaction), C2 (activity limited by available capacity), C3
(capacity transfer between periods), C4 (incumbent ageing, fallback tier only), C5 (no
building in the start year), C8 (carrier balance) and C10 (heat grade cascade, via
eligibility). Out: C6, C7, C9, C11, C12.

**The problem is a pure LP and must stay one** (§2.3). No binaries: minimum viable scale is
the ``min_duty`` screen at load, never a fixed-charge binary.

Owed by T3, T6 and T7.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import linopy
import pandas as pd
import xarray as xr

from carb3.load import ReferenceTables
from carb3.sets import ModelSets


@dataclass(frozen=True)
class SolverSettings:
    """The pinned HiGHS settings from ``[tool.carb3]``.

    Cement worked example §12: HiGHS, version pinned in ``pyproject.toml``, presolve on,
    single-threaded, so V10 (determinism) can hold across machines. §12's lexicographic
    tie-break over ``(unit_id, carrier_id, role)`` is deliberately out — note 21 §6.2 defers
    ``MF-45`` and ``MF-74`` to M2 and leaves degenerate optima visible.
    """

    solver: str = "highs"
    presolve: str = "on"
    threads: int = 1


@dataclass(frozen=True)
class PeriodAxis:
    """The explicit period year vector and what is derived from it (§6.4).

    Spec §5.1 assumes a uniform timestep and neither of its formulas holds: the real periods
    are 2021, 2025, 2030, 2035, 2040, 2045, 2050 — a 4-year first gap and 5-year gaps
    thereafter. This is a defect in §5.1, raised by T11.
    """

    years: tuple[int, ...]
    #: Years each period stands for; ``spans[i]`` is the gap that period covers.
    spans: tuple[int, ...]
    #: delta_t, aggregated over each period's own span at the ``discount_rate``.
    discount_factors: tuple[float, ...]


@dataclass(frozen=True)
class SolveResult:
    """What the solve returned, including a non-optimal status (§5.2).

    A non-optimal status is reported and printed, never raised.
    """

    status: str
    termination_condition: str
    objective: float | None
    solution: xr.Dataset | None
    n_variables: int
    n_constraints: int
    wall_clock_seconds: float


@dataclass(frozen=True)
class RowViolation:
    """One constraint row that the returned solution does not satisfy."""

    constraint: str
    #: The row's coordinates, e.g. carrier and period for a C8 node.
    coords: tuple[object, ...]
    residual: float


def period_axis(years: Sequence[int], discount_rate: float) -> PeriodAxis:
    """Derive spans and delta_t from the explicit year vector, not from a uniform Δ (§6.4)."""
    raise NotImplementedError


def lifetime_in_periods(axis: PeriodAxis, lifetime_years: int, built_at: int) -> int:
    """Convert a unit's ``lifetime`` in years to periods against the actual years remaining.

    The failure this exists to prevent is a 25-year life read as 25 periods (§10).
    """
    raise NotImplementedError


def build_model(
    sets: ModelSets,
    surviving: pd.DataFrame,
    axis: PeriodAxis,
    reference: ReferenceTables,
) -> linopy.Model:
    """Build the LP: the §2.2 variables, C1-C5, C8, C10 via eligibility, and the objective.

    The objective is min Z = sum_t delta_t (Z^capex + Z^opex + Z^fuel + Z^carbon), with capex
    annuitised over each unit's ``lifetime``. Z^infra, Z^net, Z^exp and Z^strand are out.

    Sparsity is load-bearing: linopy #248 documents that an ineffective mask silently builds
    a dense model rather than raising, and at three premises HiGHS solves either version in
    under a second, so the mistake would not surface until M5. Variable and constraint counts
    are asserted in the tests and printed per premise.
    """
    raise NotImplementedError


def solve(model: linopy.Model, settings: SolverSettings = SolverSettings()) -> SolveResult:
    """Solve with the pinned HiGHS settings, reporting a non-optimal status rather than
    raising (§5.2). Counts and solve time are recorded, which starts the G1 measurement."""
    raise NotImplementedError


def check_constraint_rows(
    model: linopy.Model, result: SolveResult, tolerance: float = 1e-6
) -> tuple[RowViolation, ...]:
    """Multiply the built matrix by the returned solution and verify every row independently
    of the solver (§5.4). C8 must close at every carrier node in every period."""
    raise NotImplementedError
