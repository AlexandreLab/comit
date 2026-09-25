"""Variables, C1-C5, C8, C10, objective, solve.

The model is the live spec §5 with terms switched off (plan §2). Nothing is invented;
features are removed, never added.

Variables in: n_{u,t} new capacity, a_{u,t} capacity available, z_{u,q,t} activity
dispatched to duty, e_{u,t} surviving incumbent capacity, m_{c,t} / m_{c,k,t} import,
d_{c,t} **disposal** and x_{c,t} **export**. Out: h_{c->c',t} cascade (C10 is enforced by
eligibility instead), r_{u,t} early retirement, w_{k,t} reinforcement.

**x_{c,t} is back, narrowly, and without it no capture train can ever be built.**
``co2_captured`` appears exactly once in ``unit_input_output.csv``, as the capture train's
``primary_output``, and nothing consumes it. It is ``carrier_kind`` ``product``, so §5.2's
safety gate forbids disposing of it; its ``may_export`` is TRUE and the slice had dropped
the export variable, so C8 pinned the node — and every capture train — to zero however
cheap it was. The variable is declared where ``carrier.may_export`` is true, a
``premise_connection`` row carries the carrier, and a complete price series exists; C9
(infrastructure availability) bounds it to zero where §3.7 says the premise's cluster
cannot take the carrier. Exporting CO₂ is a **cost**, not a revenue: the site pays a
transport-and-storage tariff. What leaves through the pipe was not vented, so it never
reaches Z^carbon, and getting that sign wrong inverts the whole result.

**z°_{u,t} is in, but only for the D16 carriers, and note 21 §2.2 was wrong to put it
out.** §2.2's reason is "no internal ``product`` carriers in the synthetic premises", and
``mvp-cement``'s kilns make ``clinker`` — a ``product`` with ``may_export`` false, whose
premise-level duty row §3.9 therefore removes. The plan says C8 pins those kilns through the
``clinker`` balance, which is right, but a unit serving no duty has no z_{u,q,t} to be
pinned: without a variable the node has no producer, the grinder is forced to zero and the
1.13 Mt cement duty is infeasible. :func:`carb3.sets.undutied_supply` names those units and
they take a column on the ``dispatch`` dimension that C1 does not select. Nothing else about
z° is restored — an ordinary unit's output is still fully dispatched and settled by C1.

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
eligibility). Out: C6, C7, C11, C12. **C9 (infrastructure availability) is partially in**
— for the export of CO₂ only, as a bound of zero on x_{c,t} in every period the premise's
cluster cannot take it. The 63 ``co2_transport`` rows of §3.7 are real, sourced data: four
clusters turn available at 2030 and five never do.

**The problem is a pure LP and must stay one** (§2.3). No binaries: minimum viable scale is
the ``min_duty`` screen at load, never a fixed-charge binary.

**A6 (the problem builder) lives here.** §3.6's D15 rule is that process CO₂ is *declared* in
``unit_input_output`` and fuel CO₂ is *derived at build time*, because the emission factor is
a ``scenario_parameters`` series that varies by period. Without A6 the carbon term would read
an empty ``co2_fuel_fossil`` node and every fuel-fired unit would vent nothing. A6 fires on
the **carrier**, not on the role: the burnable set is the carriers a unit consumes that are
``primary`` and not ``is_indirect``, summed over every consuming role, so a second fuel
sitting in ``aux_input`` still burns carbon and ``electricity`` and ``hydrogen`` still emit
nothing on site.

**Sparsity is structural here, not a mask.** linopy #248 documents that an ineffective mask
silently builds a dense model rather than raising, and at three premises HiGHS solves either
version in under a second, so the mistake would not surface until M5. z_{u,q,t} is therefore
declared over a **flattened ``dispatch`` dimension** whose coordinates are the eligible
(unit, duty) pairs and the internal-supply columns above — no mask is involved, and a pair
that is not eligible has no coordinate to be masked out of. C1 and C2 recover the two
groupings with ``groupby`` (C1 selecting only the real duty labels), and C8 selects
only the units that carry a coefficient on the carrier. The counts are asserted in the tests
against the set sizes and printed per premise by :func:`solve`.

**Two deliberate departures from §5.2, both forced by the frozen contract.** First, the
import variable is site-level ``m_{c,t}`` only: :func:`build_model` is handed ``ModelSets``
and ``ReferenceTables`` and neither carries ``premise_connection`` (§3.1.3), so which
carriers are networked is not knowable here and ``m_{c,k,t}`` cannot be declared. Note 21 §9
already records that the connection index carries no information while C11 (connection
capacity), Z^net and export are all out, and ``import_price`` has no connection dimension, so
the two forms are numerically identical in this slice — but restoring the index needs a
connections argument, not a change here. **x_{c,t} is site-level for the same reason and no
other**: §5.2 indexes every export by connection, and the index would carry no information
while C11 is out and the tariff has no connection dimension. Which carriers *have* a
connection is knowable, because :class:`~carb3.sets.ModelSets` now carries the windows
:func:`carb3.sets.export_windows` derived from ``premise_connection``; only the index is
collapsed.

Second, ``z°`` is restored for the carriers that carry **no duty**, which is now two
families rather than one: the kilns making ``clinker``, an internal ``product``, and
``ccs_amine`` making ``co2_captured``, an exportable one that no premise states a
throughput of. A unit that serves no duty and supplies no such carrier still has no
activity variable at all. One consequence is that §5.4's biogenic credit, structurally
zero while no abatement unit could take a column, is now live — and
:func:`biogenic_capture_weights` is shared with the ledger so the cost decomposition still
sums to the reported objective.

Owed by T3, T6 and T7.
"""

from __future__ import annotations

import math
import time
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from functools import reduce

import linopy
import numpy as np
import pandas as pd
import xarray as xr

from carb3.load import ReferenceTables
from carb3.sets import ModelSets

#: §3.6's three consuming roles. A6 sums over these, never over ``fuel_input`` alone: 84 rows
#: draw a ``primary`` carrier as ``aux_input`` and a secondary fuel is still a fuel.
CONSUMING_ROLES: frozenset[str] = frozenset({"fuel_input", "aux_input", "emission_input"})

#: The one role C8 reads through z° rather than through z (§5.5). An ordinary unit's primary
#: output is fully dispatched and settled by C1, so these rows are excluded from the balance
#: coefficients — except on a D16 carrier, where there is no C1 row and the output *is* the
#: balance. See ``supplied`` in :func:`_balance_coefficients`.
PRIMARY_OUTPUT_ROLE: str = "primary_output"

#: The disposal gate of §5.2. ``intermediate`` and ``emission`` carriers may be disposed of;
#: ``primary`` and ``product`` may not, or the model could import gas and dump it.
DISPOSABLE_KINDS: frozenset[str] = frozenset({"intermediate", "emission"})

#: The role A6 files its derived fuel-CO₂ rows under. ``unit_input_output`` never uses it,
#: so a derived row cannot be confused with a declared ``emission`` row.
A6_ROLE: str = "emission_derived"

#: The two carriers A6 derives (D15). Process CO₂ is declared in ``unit_input_output``.
FOSSIL_FUEL_CO2: str = "co2_fuel_fossil"
BIOGENIC_FUEL_CO2: str = "co2_fuel_biogenic"

#: §5.4's unit conversion: emission factors are kt/PJ and the carbon price is £/t, and the
#: objective is £m.
CARBON_UNIT_CONVERSION: float = 1e-3

#: Marks an internal-supply column on the ``dispatch`` dimension — a unit whose output D16
#: left with no duty row. A duty label is three ``|``-joined parts, so this cannot collide.
SUPPLY_PREFIX: str = "supply:"


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
    """Derive spans and delta_t from the explicit year vector, not from a uniform Δ (§6.4).

    Per §5.1: Δ_t = y_{t+1} − y_t for t < N, and Δ_N = Δ_{N−1}, the terminal period carrying
    the last observed gap forward as a stated convention. Every cost term in §5.4 is an
    annual **rate**, so δ_t sums the single-year factor over each of the years its period
    stands for::

        δ_t = Σ_{j=0}^{Δ_t − 1} (1 + r)^{−(y_t + j − y_{t_0})}

    Giving the start period five years instead of the four it spans overstates its whole cost
    by a quarter.
    """
    ordered = tuple(int(year) for year in years)
    if not ordered:
        raise ValueError("the period year vector is empty; §5.1 makes the years an input")
    if any(later <= earlier for earlier, later in zip(ordered, ordered[1:], strict=False)):
        raise ValueError(f"the period year vector must be strictly increasing, got {ordered}")
    if discount_rate <= -1:
        raise ValueError(f"discount_rate must exceed -1, got {discount_rate!r}")

    gaps = [later - earlier for earlier, later in zip(ordered, ordered[1:], strict=False)]
    # Δ_N = Δ_{N-1}; a single-period axis has no observed gap and stands for one year.
    spans = tuple(gaps + [gaps[-1] if gaps else 1])

    base = ordered[0]
    factors = tuple(
        sum(
            (1.0 + discount_rate) ** -(year + offset - base)
            for offset in range(span)
        )
        for year, span in zip(ordered, spans, strict=True)
    )
    return PeriodAxis(years=ordered, spans=spans, discount_factors=factors)


def lifetime_in_periods(axis: PeriodAxis, lifetime_years: int, built_at: int) -> int:
    """Convert a unit's ``lifetime`` in years to periods against the actual years remaining.

    The failure this exists to prevent is a 25-year life read as 25 periods (§10).

    §5.1's ℓ_{u,s} = |{t ∈ T : y_s ≤ y_t < y_s + L_u}|, which is why C3 (capacity transfer)
    keys its window on the build period and not on the unit alone: on the reference vector a
    25-year life built in 2021 covers six periods and the same life built in 2025 covers five.
    """
    if lifetime_years <= 0:
        raise ValueError(f"lifetime_years must be positive, got {lifetime_years!r}")
    start = int(built_at)
    end = start + int(lifetime_years)
    return sum(1 for year in axis.years if start <= year < end)


def build_model(
    sets: ModelSets,
    surviving: pd.DataFrame,
    axis: PeriodAxis,
    reference: ReferenceTables,
    tariff_override: float | None = None,
) -> linopy.Model:
    """Build the LP: the §2.2 variables, C1-C5, C8, C10 via eligibility, and the objective.

    The objective is min Z = sum_t delta_t (Z^capex + Z^opex + Z^fuel + Z^carbon), with capex
    annuitised over each unit's ``lifetime``. Z^infra, Z^net, Z^exp and Z^strand are out.

    Sparsity is load-bearing: linopy #248 documents that an ineffective mask silently builds
    a dense model rather than raising, and at three premises HiGHS solves either version in
    under a second, so the mistake would not surface until M5. Variable and constraint counts
    are asserted in the tests and printed per premise.

    ``surviving`` is :func:`carb3.survival.surviving_capacity`'s long frame — ``unit_id``,
    ``period``, ``capacity`` — and a unit absent from it carries no incumbent capacity.

    ``tariff_override`` replaces the ``co2_transport_tariff`` series with one flat value in
    £/t, for the sensitivity the tariff's own provenance asks for. It is a scenario knob,
    not a data edit: nothing under the reference root is written, and the run report prints
    the override whenever it is set so no number is ever quoted without it.
    """
    periods = tuple(int(year) for year in sets.periods)
    if tuple(axis.years) != periods:
        raise ValueError(
            f"the period axis {axis.years} does not match the model sets' periods {periods}; "
            "both read the same year vector (§5.1)"
        )

    _check_axis_rate(reference, axis)

    pairs = _dispatch_pairs(sets)
    model_units = sorted({pair.unit_id for pair in pairs})
    parameters = _unit_parameters(reference, model_units)
    carrier_facts = _carrier_facts(reference)
    # The primary output of an internal-supply unit is the only one C8 reads directly: every
    # other unit's output is settled by C1 instead, and adding it to the balance as well
    # would ask the site to both meet the duty and dispose of it.
    supplied = {
        carrier_id: frozenset(units & sets.units)
        for carrier_id, units in sorted(sets.supply.items())
        if units & sets.units
    }
    coefficients = _balance_coefficients(
        reference, model_units, periods, carrier_facts, supplied
    )

    period_index = pd.Index(periods, name="period")
    dispatch_index = pd.Index([pair.coordinate for pair in pairs], name="dispatch")
    unit_index = pd.Index(model_units, name="unit")

    duty_by_key = {duty.key: duty for duty in sets.duties}
    duty_labels = [_duty_label(duty.key) for duty in sets.duties]
    if len(set(duty_labels)) != len(duty_labels):
        raise ValueError("two duties share a (premise, process, carrier) key; Q must be a set")

    model = linopy.Model()

    # --- variables ---------------------------------------------------------------------
    # z_{u,q,t}, declared over the eligible pairs only, with max_share as an upper bound
    # rather than a constraint row: D_{q,t} is a parameter, so the cap is a bound on the
    # variable and costs the LP nothing.
    z = model.add_variables(
        lower=0.0,
        upper=_dispatch_upper_bounds(
            sets, pairs, duty_by_key, periods, dispatch_index, period_index
        ),
        coords=[dispatch_index, period_index],
        name="z",
    )
    # n_{u,t}, with earliest_year as an upper bound of zero before the year (§3.1).
    n = model.add_variables(
        lower=0.0,
        upper=_build_upper_bounds(sets, model_units, periods, unit_index, period_index),
        coords=[unit_index, period_index],
        name="n",
    )
    a = model.add_variables(lower=0.0, coords=[unit_index, period_index], name="a")

    incumbent = _incumbent_capacity(surviving, model_units, periods)
    incumbent_units = sorted(incumbent)
    e = None
    if incumbent_units:
        e = model.add_variables(
            lower=0.0,
            coords=[pd.Index(incumbent_units, name="unit"), period_index],
            name="e",
        )

    import_carriers = sorted(
        carrier for carrier in coefficients if carrier_facts[carrier].may_import
    )
    disposal_carriers = sorted(
        carrier
        for carrier in coefficients
        if carrier_facts[carrier].may_dispose
        and carrier_facts[carrier].kind in DISPOSABLE_KINDS
    )
    m_import = None
    if import_carriers:
        m_import = model.add_variables(
            lower=0.0,
            coords=[pd.Index(import_carriers, name="carrier"), period_index],
            name="m",
        )
    d_disposal = None
    if disposal_carriers:
        d_disposal = model.add_variables(
            lower=0.0,
            coords=[pd.Index(disposal_carriers, name="carrier"), period_index],
            name="d",
        )

    # x_{c,k,t}, site-level for the same reason m is (see the module docstring): C11
    # (connection capacity) is out, so the connection index carries no information and
    # neither price series has one. C9 (infrastructure availability) arrives as an upper
    # bound of zero in every period the premise's cluster cannot take the carrier.
    export_carriers = sorted(
        window.carrier_id
        for window in sets.export_windows
        if window.carrier_id in coefficients
    )
    x_export = None
    if export_carriers:
        x_export = model.add_variables(
            lower=0.0,
            upper=_export_upper_bounds(
                sets, export_carriers, periods, period_index
            ),
            coords=[pd.Index(export_carriers, name="carrier"), period_index],
            name="x",
        )

    # --- groupings ---------------------------------------------------------------------
    unit_of = xr.DataArray(
        [pair.unit_id for pair in pairs], coords=[dispatch_index], name="unit"
    )
    duty_of = xr.DataArray(
        [pair.label for pair in pairs], coords=[dispatch_index], name="duty"
    )
    # z_{u,t} of §5.2, the total activity C2 and C8 read. z° is out, so this is the whole of
    # it; groupby keeps the sum sparse — one term per eligible pair, never |U| x |Q|.
    total_activity = z.to_linexpr().groupby(unit_of).sum().sel(unit=model_units)

    # --- C1 duty satisfaction ------------------------------------------------------------
    demand = xr.DataArray(
        [
            [_duty_quantity(duty_by_key[duty.key], year) for year in periods]
            for duty in sets.duties
        ],
        coords=[pd.Index(duty_labels, name="duty"), period_index],
    )
    by_duty = z.to_linexpr().groupby(duty_of).sum().sel(duty=duty_labels)
    c1 = model.add_constraints(by_duty == demand, name="C1")
    if c1.size != len(duty_labels) * len(periods):
        raise ValueError(
            f"C1 built {c1.size} rows for {len(duty_labels)} duties over {len(periods)} "
            "periods; a duty was dropped by alignment rather than constrained"
        )

    # --- C2 activity limited by available capacity ---------------------------------------
    deliverable = xr.DataArray(
        [parameters[unit_id].gamma * parameters[unit_id].alpha for unit_id in model_units],
        coords=[unit_index],
    )
    model.add_constraints(total_activity - a * deliverable <= 0, name="C2")

    # --- C3 capacity transfer between periods --------------------------------------------
    window = _build_window(axis, periods, parameters, model_units, unit_index, period_index)
    built_standing = (n.rename({"period": "vintage"}) * window).sum("vintage")
    if e is None:
        model.add_constraints(a - built_standing == 0, name="C3")
    else:
        model.add_constraints(
            a.sel(unit=incumbent_units)
            - built_standing.sel(unit=incumbent_units)
            - e
            == 0,
            name="C3_incumbent",
        )
        greenfield = [unit_id for unit_id in model_units if unit_id not in incumbent]
        if greenfield:
            model.add_constraints(
                a.sel(unit=greenfield) - built_standing.sel(unit=greenfield) == 0,
                name="C3_new",
            )

    # --- C4 incumbent ageing ---------------------------------------------------------------
    if e is not None:
        # An equality, not a bound: early retirement (r_{u,t}) and the stranding charge are
        # out, so surviving capacity is pinned to the D11 survival parameter. Mechanism, not
        # driver (§4.3) — C2 is an inequality, so nothing compels the incumbent to run.
        surviving_da = xr.DataArray(
            [[incumbent[unit_id][year] for year in periods] for unit_id in incumbent_units],
            coords=[pd.Index(incumbent_units, name="unit"), period_index],
        )
        model.add_constraints(e == surviving_da, name="C4")

    # --- C5 no building in the start year --------------------------------------------------
    model.add_constraints(n.sel(period=periods[0]) == 0, name="C5")

    # --- C8 carrier balance, with the disposal term ------------------------------------------
    for carrier_id in sorted(coefficients):
        contributors = sorted(coefficients[carrier_id])
        weights = xr.DataArray(
            np.array([coefficients[carrier_id][unit_id] for unit_id in contributors]),
            coords=[pd.Index(contributors, name="unit"), period_index],
        )
        balance = (total_activity.sel(unit=contributors) * weights).sum("unit")
        if m_import is not None and carrier_id in import_carriers:
            balance = balance + m_import.sel(carrier=carrier_id, drop=True)
        if x_export is not None and carrier_id in export_carriers:
            # §5.5's −x term. What leaves the site is not vented, so it never reaches
            # Z^carbon; that is the whole point of the capture route and the sign that
            # inverts the result if it is got wrong.
            balance = balance - x_export.sel(carrier=carrier_id, drop=True)
        if d_disposal is not None and carrier_id in disposal_carriers:
            balance = balance - d_disposal.sel(carrier=carrier_id, drop=True)
        model.add_constraints(balance == 0, name=f"C8_{carrier_id}")

    # --- objective -----------------------------------------------------------------------
    model.add_objective(
        _objective(
            reference=reference,
            axis=axis,
            periods=periods,
            period_index=period_index,
            unit_index=unit_index,
            model_units=model_units,
            parameters=parameters,
            carrier_facts=carrier_facts,
            built_standing=built_standing,
            capacity=a,
            total_activity=total_activity,
            imports=m_import,
            import_carriers=import_carriers,
            disposal=d_disposal,
            disposal_carriers=disposal_carriers,
            exports=x_export,
            export_carriers=export_carriers,
            tariff_override=tariff_override,
        )
    )
    return model


def _export_upper_bounds(
    sets: ModelSets,
    export_carriers: Sequence[str],
    periods: Sequence[int],
    period_index: pd.Index,
) -> xr.DataArray:
    """C9 (infrastructure availability) as an upper bound of zero on x_{c,t} (§5.5).

    §3.7's rows are the sourced statement of when a network reaches a cluster, and they are
    better evidence than the ``earliest_year`` column: four clusters take CO₂ from 2030 and
    five never do. Written as a bound rather than a constraint row because the window is a
    parameter — the LP has no decision to make about whether a pipeline exists.
    """
    allowed = {
        window.carrier_id: set(window.periods) for window in sets.export_windows
    }
    bounds = np.full((len(export_carriers), len(periods)), np.inf)
    for row, carrier_id in enumerate(export_carriers):
        open_periods = allowed.get(carrier_id, set())
        for column, year in enumerate(periods):
            if year not in open_periods:
                bounds[row, column] = 0.0
    return xr.DataArray(
        bounds, coords=[pd.Index(list(export_carriers), name="carrier"), period_index]
    )


def solve(model: linopy.Model, settings: SolverSettings = SolverSettings()) -> SolveResult:
    """Solve with the pinned HiGHS settings, reporting a non-optimal status rather than
    raising (§5.2). Counts and solve time are recorded, which starts the G1 measurement."""
    n_variables = model.nvars
    n_constraints = model.ncons
    started = time.perf_counter()
    try:
        status, condition = model.solve(
            solver_name=settings.solver,
            presolve=settings.presolve,
            threads=settings.threads,
            # HiGHS' own log, suppressed so the run report below is the output. This is a
            # logging choice, not one of the three settings §12 pins for determinism.
            output_flag=False,
            progress=False,
        )
    except Exception as error:  # noqa: BLE001 - a solver failure is reported, never raised
        elapsed = time.perf_counter() - started
        print(
            f"carb3: solve failed after {elapsed:.3f}s — {type(error).__name__}: {error}; "
            f"{n_variables} variables, {n_constraints} constraints"
        )
        return SolveResult(
            status="error",
            termination_condition=type(error).__name__,
            objective=None,
            solution=None,
            n_variables=n_variables,
            n_constraints=n_constraints,
            wall_clock_seconds=elapsed,
        )
    elapsed = time.perf_counter() - started

    optimal = condition == "optimal"
    objective = None
    solution = None
    if optimal:
        objective = float(model.objective.value)
        with warnings.catch_warnings():
            # linopy merges every variable into one Dataset here, and z, n, a, e, m and d
            # sit on four different dimensions by design, so the outer join it warns about
            # is the intended shape rather than a coordinate mismatch to fix.
            warnings.filterwarnings(
                "ignore", message="Coordinates across variables not equal"
            )
            solution = model.solution
    print(
        f"carb3: status={status} termination={condition} "
        f"variables={n_variables} constraints={n_constraints} "
        f"wall_clock={elapsed:.3f}s "
        + (f"objective={objective:.6g}" if objective is not None else "objective=none")
    )
    if not optimal:
        # §5.2: infeasibility is an expected outcome, not an error. It is reported here and
        # the caller reads the status; nothing is raised and no pathway is reported.
        print(
            f"carb3: the solve did not reach an optimum ({condition}); no pathway is "
            "reported. Run the pre-solve unservable-duty diagnosis for the likely cause"
        )
    return SolveResult(
        status=status,
        termination_condition=condition,
        objective=objective,
        solution=solution,
        n_variables=n_variables,
        n_constraints=n_constraints,
        wall_clock_seconds=elapsed,
    )


def check_constraint_rows(
    model: linopy.Model, result: SolveResult, tolerance: float = 1e-6
) -> tuple[RowViolation, ...]:
    """Multiply the built matrix by the returned solution and verify every row independently
    of the solver (§5.4). C8 must close at every carrier node in every period.

    The point is that nothing here asks the solver whether it was right. ``A`` and ``b`` come
    from the built model, the solution vector comes back from HiGHS, and the residual is
    computed here — so a carrier node that does not balance is caught even when the solver
    reports ``optimal``.
    """
    if result.solution is None:
        raise ValueError(
            "check_constraint_rows needs a solved model; the result carries no solution "
            f"(status={result.status!r}, termination={result.termination_condition!r})"
        )
    matrices = model.matrices
    residuals = np.asarray(matrices.A @ matrices.sol) - np.asarray(matrices.b)
    sense = np.asarray(matrices.sense)
    labels = np.asarray(matrices.clabels)
    rows = _constraint_rows(model)

    violations: list[RowViolation] = []
    for label, direction, residual in zip(labels, sense, residuals, strict=True):
        if direction == "=":
            violated = abs(residual) > tolerance
        elif direction == "<":
            violated = residual > tolerance
        else:
            violated = residual < -tolerance
        if violated:
            name, coords = rows.get(int(label), ("<unknown>", ()))
            violations.append(
                RowViolation(constraint=name, coords=coords, residual=float(residual))
            )
    return tuple(violations)


# --------------------------------------------------------------------------------------
# Internals
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Pair:
    """One column of the flattened ``dispatch`` dimension.

    ``duty_key`` is ``None`` for an internal-supply column — a unit producing a carrier D16
    left with no duty row — which is how C1 (duty satisfaction) tells the two apart.
    """

    duty_key: tuple[str, str, str] | None
    label: str
    unit_id: str

    @property
    def coordinate(self) -> str:
        return f"{self.unit_id}@{self.label}"


@dataclass(frozen=True)
class _UnitParameters:
    """The §5.3 parameters the objective and C2/C3 read, per unit.

    Every field is required. A blank is not read as zero: the §3.2 admission screen exists
    because a cost-minimiser reads a blank capex as free energy, and a unit that reached the
    LP without one is a screen failure, so this raises rather than defaulting.
    """

    kappa: float
    phi: float
    lifetime: int
    alpha: float
    gamma: float
    unit_class: str


@dataclass(frozen=True)
class _CarrierFacts:
    """The §3.4 columns C8, the disposal gate and A6 read."""

    kind: str
    is_indirect: bool
    biogenic_fraction: float | None
    carbon_charge: str
    may_dispose: bool
    may_import: bool


def _dispatch_pairs(sets: ModelSets) -> tuple[_Pair, ...]:
    """The coordinates of the flattened ``dispatch`` dimension.

    Two kinds of column sit on it. Most are the eligible **(duty, unit)** pairs and are
    summed into C1 (duty satisfaction) by ``groupby``. The rest are the **internal-supply**
    columns :func:`carb3.sets.undutied_supply` found — a unit producing a carrier that
    carries no duty row — and they carry ``duty_key`` ``None``, so C1 never selects their
    label and their level is settled by C8 (carrier balance) alone. That is exactly what
    note 21 §2.2 means by "C8 pins the kiln through the ``clinker`` balance instead", and it
    is the smallest restoration of z° that makes the sentence true.

    A duty with an empty U_q is refused here rather than silently dropped. C1 built by
    ``groupby`` would simply not emit a row for it, and the duty would go unmet with the
    solver reporting ``optimal`` — the silent wrong answer §5.2 sends to the diagnosis step.
    """
    pairs: list[_Pair] = []
    unservable: list[tuple[str, str, str]] = []
    for duty in sets.duties:
        eligible = sorted(sets.eligible.get(duty.key, frozenset()) & sets.units)
        if not eligible:
            unservable.append(duty.key)
            continue
        pairs.extend(
            _Pair(duty_key=duty.key, label=_duty_label(duty.key), unit_id=unit_id)
            for unit_id in eligible
        )
    if unservable:
        raise ValueError(
            "these duties have an empty eligible-unit set and cannot be built into the LP: "
            f"{unservable}. §5.2 makes this an expected outcome — call "
            "carb3.sets.diagnose_unservable_duties before building"
        )
    for carrier_id, units in sorted(sets.supply.items()):
        pairs.extend(
            _Pair(duty_key=None, label=_supply_label(carrier_id), unit_id=unit_id)
            for unit_id in sorted(units & sets.units)
        )
    if not pairs:
        raise ValueError("no duty has an eligible unit; there is no problem to build")
    return tuple(pairs)


def _check_axis_rate(reference: ReferenceTables, axis: PeriodAxis) -> None:
    """Refuse an axis discounted at a different rate from the one the objective annuitises at.

    δ_t is built by the caller through :func:`period_axis` and the annuity below reads
    ``scenario_parameters``. Two rates would discount the pathway at one and price capital at
    another, and nothing downstream would say so — the objective would simply be wrong.
    """
    rate = _scalar_parameter(reference, "discount_rate")
    expected = period_axis(axis.years, rate).discount_factors
    if any(
        abs(left - right) > 1e-12
        for left, right in zip(expected, axis.discount_factors, strict=True)
    ):
        raise ValueError(
            f"the period axis was discounted at a different rate from scenario_parameters' "
            f"discount_rate of {rate}; δ_t and the capex annuity must read one rate"
        )


def _duty_label(duty_key: tuple[str, str, str]) -> str:
    return "|".join(str(part) for part in duty_key)


def _supply_label(carrier_id: str) -> str:
    """The label of an internal-supply column. ``|`` separates a duty key's three parts, so
    a single-segment label cannot collide with one however a duty is named."""
    return f"{SUPPLY_PREFIX}{carrier_id}"


def _duty_quantity(duty, year: int) -> float:
    """D_{q,t}. A period the duty does not quote is an input error, not a zero demand."""
    quantity = duty.quantity
    if year in quantity:
        return float(quantity[year])
    raise ValueError(
        f"duty {duty.key} quotes no quantity for {year}; D_{{q,t}} must cover every period"
    )


def _dispatch_upper_bounds(
    sets: ModelSets,
    pairs: Sequence[_Pair],
    duty_by_key: dict[tuple[str, str, str], object],
    periods: Sequence[int],
    dispatch_index: pd.Index,
    period_index: pd.Index,
) -> xr.DataArray:
    """``max_share`` as an upper bound on z_{u,q,t}: the unit's share of that duty (§3.1).

    Four rows carry one, and one of them is ``boiler_lt_coal`` at ``Food Processing Centre``
    at 0.00 — a hard prohibition, which this turns into an upper bound of exactly zero. An
    internal-supply column has no duty and so no share: it is bounded by C2 and C8 alone.
    """
    bounds = np.full((len(pairs), len(periods)), np.inf)
    for row, pair in enumerate(pairs):
        if pair.duty_key is None:
            continue
        share = sets.max_share.get((pair.duty_key, pair.unit_id))
        if share is None:
            continue
        duty = duty_by_key[pair.duty_key]
        for column, year in enumerate(periods):
            bounds[row, column] = float(share) * _duty_quantity(duty, year)
    return xr.DataArray(bounds, coords=[dispatch_index, period_index])


def _build_upper_bounds(
    sets: ModelSets,
    model_units: Sequence[str],
    periods: Sequence[int],
    unit_index: pd.Index,
    period_index: pd.Index,
) -> xr.DataArray:
    """``earliest_year`` as an upper bound of zero on n_{u,t} before the year (§3.1).

    The column is keyed by duty and n_{u,t} is not, so a unit eligible for two duties with
    different ``earliest_year`` values takes the **earliest** of them: the column gates when
    the technology may be built at all, and the nine rows carrying one are a hydrogen boiler,
    a high-temperature heat pump and the capture trains, none of which is eligible on two
    duties at two different years today.

    **Supply units carry a gate too, and reading only the duty-keyed map missed it.** A
    unit D16 leaves with no duty sits in no U_q, so ``ccs_amine``'s ``earliest_year`` 2035 —
    the only row in the table that gates a capture train at a premise that can host one —
    arrives through :attr:`~carb3.sets.ModelSets.supply_earliest_year` instead. Both
    sources are merged and the earliest wins.
    """
    wanted = set(model_units)
    earliest: dict[str, int] = {}
    gates = [
        (unit_id, year) for (_duty_key, unit_id), year in sets.earliest_year.items()
    ] + [
        (unit_id, year)
        for (_carrier_id, unit_id), year in sets.supply_earliest_year.items()
    ]
    for unit_id, year in gates:
        if unit_id in wanted:
            earliest[unit_id] = min(earliest.get(unit_id, int(year)), int(year))
    bounds = np.full((len(model_units), len(periods)), np.inf)
    for row, unit_id in enumerate(model_units):
        gate = earliest.get(unit_id)
        if gate is None:
            continue
        for column, year in enumerate(periods):
            if year < gate:
                bounds[row, column] = 0.0
    return xr.DataArray(bounds, coords=[unit_index, period_index])


def _build_window(
    axis: PeriodAxis,
    periods: Sequence[int],
    parameters: dict[str, "_UnitParameters"],
    model_units: Sequence[str],
    unit_index: pd.Index,
    period_index: pd.Index,
) -> xr.DataArray:
    """C3's indicator 1[s ≤ t ≤ s + ℓ_{u,s} − 1], over (unit, build period, period).

    The window is keyed on the **build** period, not on the unit alone (§5.1): on the
    reference vector a 25-year life built in 2021 covers six periods and the same life built
    in 2025 covers five, and dividing by a nominal step gets both wrong.
    """
    index_of = {year: position for position, year in enumerate(axis.years)}
    values = np.zeros((len(model_units), len(periods), len(periods)))
    for row, unit_id in enumerate(model_units):
        lifetime = parameters[unit_id].lifetime
        for built_at, built in enumerate(periods):
            last = index_of[built] + lifetime_in_periods(axis, lifetime, built)
            for standing_at, standing in enumerate(periods):
                if built <= standing and index_of[standing] < last:
                    values[row, built_at, standing_at] = 1.0
    return xr.DataArray(
        values, coords=[unit_index, pd.Index(list(periods), name="vintage"), period_index]
    )


def _incumbent_capacity(
    surviving: pd.DataFrame, model_units: Sequence[str], periods: Sequence[int]
) -> dict[str, dict[int, float]]:
    """e_{u,t}'s right-hand side, read from :func:`carb3.survival.surviving_capacity`.

    A unit absent from the frame carries no incumbent capacity (§survival). A unit present in
    it but eligible for no duty is skipped: with z° out it has no activity variable, so
    standing capacity for it would only carry fixed opex for a unit that cannot run.
    """
    if surviving is None or len(surviving) == 0:
        return {}
    required = {"unit_id", "period", "capacity"}
    missing = required - set(surviving.columns)
    if missing:
        raise ValueError(
            f"the surviving-capacity frame is missing {sorted(missing)}; "
            "carb3.survival.surviving_capacity returns unit_id, period and capacity"
        )
    wanted = set(model_units)
    standing: dict[str, dict[int, float]] = {}
    for row in surviving.itertuples(index=False):
        unit_id = str(row.unit_id)
        if unit_id not in wanted:
            continue
        standing.setdefault(unit_id, {})[int(row.period)] = float(row.capacity)
    for unit_id, by_period in standing.items():
        absent = [year for year in periods if year not in by_period]
        if absent:
            raise ValueError(
                f"surviving capacity for {unit_id!r} is missing periods {absent}; "
                "e_{u,t} is declared over every period"
            )
    return standing


def _unit_parameters(
    reference: ReferenceTables, model_units: Sequence[str]
) -> dict[str, _UnitParameters]:
    """Read κ, φ, L, α and γ for every unit in the model, failing loud on a blank."""
    table = reference.unit
    required = {
        "unit_id",
        "capex",
        "fixed_opex",
        "lifetime",
        "availability_factor",
        "capacity_to_activity_factor",
    }
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"the reference unit table is missing {sorted(missing)}")
    indexed = table.set_index("unit_id")
    parameters: dict[str, _UnitParameters] = {}
    for unit_id in model_units:
        if unit_id not in indexed.index:
            raise ValueError(f"unit {unit_id!r} is eligible for a duty but absent from unit.csv")
        row = indexed.loc[unit_id]
        parameters[unit_id] = _UnitParameters(
            kappa=_required_float(row, "capex", unit_id),
            phi=_required_float(row, "fixed_opex", unit_id),
            lifetime=int(round(_required_float(row, "lifetime", unit_id))),
            alpha=_required_float(row, "availability_factor", unit_id),
            gamma=_required_float(row, "capacity_to_activity_factor", unit_id),
            unit_class=_as_text(row.get("unit_class")),
        )
    return parameters


def _required_float(row: pd.Series, column: str, unit_id: str) -> float:
    value = _as_float(row.get(column))
    if value is None:
        raise ValueError(
            f"unit {unit_id!r} has a blank {column!r} and reached the LP. The §3.2 admission "
            "screen exists to drop it: a blank is read as zero and the unit runs free"
        )
    return value


def _carrier_facts(reference: ReferenceTables) -> dict[str, _CarrierFacts]:
    table = reference.carrier
    required = {
        "carrier_id",
        "carrier_kind",
        "is_indirect",
        "biogenic_fraction",
        "carbon_charge",
        "may_dispose",
        "may_import",
    }
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"the reference carrier table is missing {sorted(missing)}")
    facts: dict[str, _CarrierFacts] = {}
    for row in table.itertuples(index=False):
        facts[str(row.carrier_id)] = _CarrierFacts(
            kind=_as_text(row.carrier_kind),
            is_indirect=_as_bool(row.is_indirect),
            biogenic_fraction=_as_float(row.biogenic_fraction),
            carbon_charge=_as_text(row.carbon_charge),
            may_dispose=_as_bool(row.may_dispose),
            may_import=_as_bool(row.may_import),
        )
    return facts


def _balance_coefficients(
    reference: ReferenceTables,
    model_units: Sequence[str],
    periods: Sequence[int],
    carrier_facts: dict[str, _CarrierFacts],
    supplied: dict[str, frozenset[str]] | None = None,
) -> dict[str, dict[str, np.ndarray]]:
    """C8's coefficient set: carrier → unit → ι over the periods.

    The roles of :func:`_balance_terms` summed. The ledger's ``unit_flow`` table reads the
    terms before the sum, so the two can never disagree about which rows C8 saw.
    """
    return {
        carrier_id: {
            unit_id: sum(by_role.values(), np.zeros(len(periods)))
            for unit_id, by_role in by_unit.items()
        }
        for carrier_id, by_unit in _balance_terms(
            reference, model_units, periods, carrier_facts, supplied
        ).items()
    }


def _balance_terms(
    reference: ReferenceTables,
    model_units: Sequence[str],
    periods: Sequence[int],
    carrier_facts: dict[str, _CarrierFacts],
    supplied: dict[str, frozenset[str]] | None = None,
) -> dict[str, dict[str, dict[str, np.ndarray]]]:
    """C8's coefficient set by role: carrier → unit → role → ι over the periods.

    Every role except ``primary_output`` enters, because C8 reads a primary output through
    z° and z° is out of this slice — a unit's whole output is dispatched to duties and is
    settled by C1 instead. The inner sum is over **roles**, per §5.5: a store holding a charge
    row and a discharge row on one carrier, or a fired capture train holding an
    ``emission_input`` and a derived ``emission`` row on ``co2_fuel_fossil``, sums both here.

    **``supplied`` is the one exception, and it is the D16 case.** A carrier D16 left with no
    duty row has no C1 row to settle its producers against, so for those (carrier, unit)
    pairs the ``primary_output`` coefficient *is* the balance: the kiln's ``+1`` clinker
    against the grinder's ``−0.752212`` draw. Including it for anything else would ask the
    site to meet the duty and dispose of the same output twice over.

    A6's two derived rows (§3.6, D15) are added on top, and they are period-dependent because
    the emission factor is a ``scenario_parameters`` series.
    """
    table = reference.unit_input_output
    required = {"unit_id", "carrier_id", "coefficient", "role"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"unit_input_output is missing {sorted(missing)}")

    wanted = set(model_units)
    n_periods = len(periods)
    coefficients: dict[str, dict[str, dict[str, np.ndarray]]] = {}
    burn: dict[str, dict[str, float]] = {}

    for row in table.itertuples(index=False):
        unit_id = str(row.unit_id)
        if unit_id not in wanted:
            continue
        carrier_id = str(row.carrier_id)
        if carrier_id not in carrier_facts:
            raise ValueError(
                f"unit_input_output row ({unit_id}, {carrier_id}) names a carrier absent "
                "from carrier.csv"
            )
        role = str(row.role or "").strip()
        value = _as_float(row.coefficient)
        if value is None:
            raise ValueError(
                f"unit_input_output row ({unit_id}, {carrier_id}, {role}) has a blank "
                "coefficient; a blank is read as zero and the flow becomes free"
            )
        reads_output = unit_id in (supplied or {}).get(carrier_id, frozenset())
        if role != PRIMARY_OUTPUT_ROLE or reads_output:
            slot = coefficients.setdefault(carrier_id, {}).setdefault(unit_id, {})
            slot[role] = slot.get(role, np.zeros(n_periods)) + value
        facts = carrier_facts[carrier_id]
        if role in CONSUMING_ROLES and facts.kind == "primary" and not facts.is_indirect:
            burn.setdefault(unit_id, {})[carrier_id] = (
                burn.setdefault(unit_id, {}).get(carrier_id, 0.0) + abs(value)
            )

    _apply_a6(reference, burn, carrier_facts, periods, coefficients)

    # Drop anything that is zero in every period: an all-zero row would add a term to C8 that
    # carries no flow, which is the dense-model habit #248 warns about. The test is on the
    # role sum, so two roles that cancel exactly drop together, as they did before the split.
    return {
        carrier_id: {
            unit_id: by_role
            for unit_id, by_role in by_unit.items()
            if np.any(np.abs(sum(by_role.values(), np.zeros(n_periods))) > 0.0)
        }
        for carrier_id, by_unit in coefficients.items()
        if any(
            np.any(np.abs(sum(by_role.values(), np.zeros(n_periods))) > 0.0)
            for by_role in by_unit.values()
        )
    }


def _apply_a6(
    reference: ReferenceTables,
    burn: dict[str, dict[str, float]],
    carrier_facts: dict[str, _CarrierFacts],
    periods: Sequence[int],
    coefficients: dict[str, dict[str, dict[str, np.ndarray]]],
) -> None:
    """A6 (§3.6, D15): derive the two fuel-CO₂ ``emission`` rows, per period.

    They are filed under the role :data:`A6_ROLE`, not ``emission``, so a declared process
    row and a derived fuel row on one carrier stay apart in the ledger's ``unit_flow``.

    ι_{u,co2_fuel_fossil} = Σ_c Σ_θ |ι_{u,c,θ}| f_{c,t} (1 − b_c), and the biogenic row the
    same with b_c. Both positive, because emissions are produced. The split happens here,
    **before** anything is captured, which is what makes capture of a co-fired stream
    net-negative rather than merely zero.
    """
    if not burn:
        return
    factors: dict[str, np.ndarray] = {}
    for by_carrier in burn.values():
        for carrier_id in by_carrier:
            if carrier_id in factors:
                continue
            factors[carrier_id] = np.array(
                _scenario_series(reference, f"ef_{carrier_id}", carrier_id, periods)
            )
    for unit_id, by_carrier in burn.items():
        fossil = np.zeros(len(periods))
        biogenic = np.zeros(len(periods))
        for carrier_id, quantity in by_carrier.items():
            share = carrier_facts[carrier_id].biogenic_fraction
            if share is None:
                raise ValueError(
                    f"carrier {carrier_id!r} is burnt by {unit_id!r} and carries no "
                    "biogenic_fraction; A6 cannot split its CO₂ (§3.6)"
                )
            emitted = quantity * factors[carrier_id]
            fossil += emitted * (1.0 - share)
            biogenic += emitted * share
        for carrier_id, values in ((FOSSIL_FUEL_CO2, fossil), (BIOGENIC_FUEL_CO2, biogenic)):
            if carrier_id not in carrier_facts:
                raise ValueError(
                    f"A6 derives {carrier_id!r} and carrier.csv does not define it (§3.6)"
                )
            slot = coefficients.setdefault(carrier_id, {}).setdefault(unit_id, {})
            slot[A6_ROLE] = slot.get(A6_ROLE, np.zeros(len(periods))) + values


def _objective(
    *,
    reference: ReferenceTables,
    axis: PeriodAxis,
    periods: Sequence[int],
    period_index: pd.Index,
    unit_index: pd.Index,
    model_units: Sequence[str],
    parameters: dict[str, _UnitParameters],
    carrier_facts: dict[str, _CarrierFacts],
    built_standing,
    capacity,
    total_activity,
    imports,
    import_carriers: Sequence[str],
    disposal,
    disposal_carriers: Sequence[str],
    exports=None,
    export_carriers: Sequence[str] = (),
    tariff_override: float | None = None,
):
    """min Z = Σ_t δ_t (Z^capex + Z^opex + Z^fuel + Z^carbon + Z^exp). Three terms are out.

    Capex is annuitised over each unit's lifetime and charged on the **new** capacity standing
    in the period, which is exactly C3's build convolution: an incumbent's capex is sunk and
    must not reappear (§4.2). ``scenario_parameters.csv`` carries no ``interest_rate`` row, so
    §5.4's annuity rate *i* is taken as the ``discount_rate``, which is what §4.2's own
    arithmetic does at 3.5%.
    """
    rate = _scalar_parameter(reference, "discount_rate")
    delta = xr.DataArray(list(axis.discount_factors), coords=[period_index])

    annuitised = xr.DataArray(
        [
            parameters[unit_id].kappa * _annuity_factor(rate, parameters[unit_id].lifetime)
            for unit_id in model_units
        ],
        coords=[unit_index],
    )
    fixed_opex = xr.DataArray(
        [parameters[unit_id].phi for unit_id in model_units], coords=[unit_index]
    )
    terms = [
        (built_standing * annuitised).sum("unit"),
        (capacity * fixed_opex).sum("unit"),
    ]

    if imports is not None and import_carriers:
        prices = xr.DataArray(
            np.array(
                [
                    _scenario_series(reference, "import_price", carrier_id, periods)
                    for carrier_id in import_carriers
                ]
            ),
            coords=[pd.Index(list(import_carriers), name="carrier"), period_index],
        )
        terms.append((imports * prices).sum("carrier"))

    carbon_price = xr.DataArray(
        _scenario_series(reference, "carbon_price", None, periods), coords=[period_index]
    )
    charged = [
        carrier_id
        for carrier_id in disposal_carriers
        if carrier_facts[carrier_id].carbon_charge == "charged"
    ]
    if disposal is not None and charged:
        vented = disposal.sel(carrier=charged).sum("carrier")
        terms.append(vented * (CARBON_UNIT_CONVERSION * carbon_price))

    credit = _biogenic_credit(
        reference=reference,
        periods=periods,
        period_index=period_index,
        model_units=model_units,
        parameters=parameters,
        carrier_facts=carrier_facts,
        total_activity=total_activity,
    )
    if credit is not None:
        terms.append(credit * (-CARBON_UNIT_CONVERSION * carbon_price))

    if exports is not None and export_carriers:
        prices = xr.DataArray(
            np.array(
                [
                    export_unit_cost(reference, carrier_id, periods, tariff_override)
                    for carrier_id in export_carriers
                ]
            ),
            coords=[pd.Index(list(export_carriers), name="carrier"), period_index],
        )
        terms.append((exports * prices).sum("carrier"))

    annual = reduce(lambda left, right: left + right, terms)
    return (annual * delta).sum()


def export_unit_cost(
    reference: ReferenceTables,
    carrier_id: str,
    periods: Sequence[int],
    tariff_override: float | None = None,
) -> list[float]:
    """What one unit of exported ``carrier_id`` costs the site, per period.

    §5.4 writes the export term as a **revenue**, $Z^{exp} = \\sum x\\,p^{exp}$, entering
    with a negative sign. Captured CO₂ inverts that: nobody buys it, the site pays a
    transport-and-storage tariff to be rid of it, and §3.7 already has a ``unit_tariff``
    column for exactly that — blank on all 63 ``co2_transport`` rows. So the cost per unit
    is the tariff less any export price, and the term enters the objective **positive**
    where the tariff dominates:

        cost = τ_{c,t} − p^exp_{c,t}

    with either side absent read as zero. :func:`carb3.sets.export_windows` has already
    refused any carrier where both are absent or partial, so at least one is complete here.

    **The carbon charge does not appear, and must not.** §5.4 charges carbon on d_{c,t},
    what is vented. Exported CO₂ went into a pipe, not up a stack, so it attracts nothing —
    which is the whole economic case for the capture route.
    """
    cost = [0.0] * len(periods)
    if tariff_override is not None and carrier_id in _TARIFFED_CARRIERS:
        tariff = [float(tariff_override)] * len(periods)
    else:
        tariff = _optional_series(reference, "co2_transport_tariff", carrier_id, periods)
    revenue = _optional_series(reference, "export_price", carrier_id, periods)
    if tariff is None and revenue is None:
        raise ValueError(
            f"carrier {carrier_id!r} has an export variable and neither a "
            "co2_transport_tariff nor an export_price covering every period; "
            "carb3.sets.export_windows should have refused it, because an unpriced "
            "export is free disposal (§5.2)"
        )
    for index in range(len(periods)):
        if tariff is not None:
            cost[index] += tariff[index]
        if revenue is not None:
            cost[index] -= revenue[index]
    return cost


#: Carriers the ``--co2-tariff`` sensitivity switch applies to. One today; the constant
#: exists so the switch cannot silently reprice an unrelated export.
_TARIFFED_CARRIERS: frozenset[str] = frozenset({"co2_captured"})


def _optional_series(
    reference: ReferenceTables,
    parameter_id: str,
    carrier_id: str,
    periods: Sequence[int],
) -> list[float] | None:
    """A ``scenario_parameters`` series, or ``None`` where it does not cover every period.

    A *partial* series returns ``None`` rather than being back-filled with zeros — the same
    reading the §3.2 screen takes of ``heavy_fuel_oil``'s single ``import_price`` row. A
    zero-filled price is a free flow in the periods it is missing from.
    """
    table = reference.scenario_parameters
    rows = table[
        (table["parameter_id"] == parameter_id) & (table["carrier_id"] == carrier_id)
    ]
    by_year: dict[int, float] = {}
    for row in rows.itertuples(index=False):
        year = _as_float(row.period)
        value = _as_float(row.value)
        if year is None or value is None:
            continue
        by_year[int(year)] = value
    if any(year not in by_year for year in periods):
        return None
    return [by_year[year] for year in periods]


def _biogenic_credit(
    *,
    reference: ReferenceTables,
    periods: Sequence[int],
    period_index: pd.Index,
    model_units: Sequence[str],
    parameters: dict[str, _UnitParameters],
    carrier_facts: dict[str, _CarrierFacts],
    total_activity,
):
    """§5.4's subtrahend: Σ_{c zero_rated} Σ_{u ∈ U^abate} |ι_{u,c,emission_input}| z_{u,t}.

    The only negative emission the model can produce, and it is **live** at ``mvp-cement``
    from the moment ``ccs_amine`` takes a supply column. It was structurally zero before
    that: an abatement unit whose primary output carries no duty was eligible for nothing,
    entered no U_q and had no activity variable, which left U^abate empty. ``None`` rather
    than a zero term keeps the objective free of a row that carries nothing, which is still
    the answer at the two premises with no capture train.

    The weights are shared with :func:`carb3.ledger._cost_table` through
    :func:`biogenic_capture_weights`, because once the credit is non-zero a ledger that
    computed it separately — or not at all — stops summing to the reported objective.
    """
    captured = biogenic_capture_weights(
        reference, model_units, parameters, carrier_facts
    )
    creditable = sorted(captured)
    if not creditable:
        return None
    weights = xr.DataArray(
        np.array([[captured[unit_id]] * len(periods) for unit_id in creditable]),
        coords=[pd.Index(creditable, name="unit"), period_index],
    )
    return (total_activity.sel(unit=creditable) * weights).sum("unit")


def biogenic_capture_weights(
    reference: ReferenceTables,
    model_units: Sequence[str],
    parameters: dict[str, _UnitParameters],
    carrier_facts: dict[str, _CarrierFacts],
) -> dict[str, float]:
    """|ι_{u,c,emission_input}| summed over the ``zero_rated`` carriers, per abatement unit.

    The weight behind §5.4's only negative emission. Shared with the ledger on purpose: the
    cost decomposition has to sum to the reported objective, and before ``ccs_amine`` could
    take an activity variable the credit was structurally zero, so a ledger that omitted it
    still balanced. It no longer is, and a term computed twice from one function is the
    only version of "the terms sum" that means anything.
    """
    zero_rated = {
        carrier_id
        for carrier_id, facts in carrier_facts.items()
        if facts.carbon_charge == "zero_rated"
    }
    abatement = {
        unit_id for unit_id in model_units if parameters[unit_id].unit_class == "abatement"
    }
    if not zero_rated or not abatement:
        return {}

    captured: dict[str, float] = {}
    for row in reference.unit_input_output.itertuples(index=False):
        unit_id = str(row.unit_id)
        if unit_id not in abatement or str(row.role or "").strip() != "emission_input":
            continue
        if str(row.carrier_id) not in zero_rated:
            continue
        captured[unit_id] = captured.get(unit_id, 0.0) + abs(_as_float(row.coefficient) or 0.0)
    return {unit_id: value for unit_id, value in captured.items() if value > 0.0}


def _constraint_rows(model: linopy.Model) -> dict[int, tuple[str, tuple[object, ...]]]:
    """Constraint label → (name, coordinates), so a violated row names itself."""
    rows: dict[int, tuple[str, tuple[object, ...]]] = {}
    for name in model.constraints:
        labels = model.constraints[name].labels
        series = labels.to_series()
        for coords, label in series.items():
            if int(label) < 0:
                continue
            rows[int(label)] = (
                name,
                tuple(coords) if isinstance(coords, tuple) else (coords,),
            )
    return rows


def _annuity_factor(rate: float, lifetime_years: int) -> float:
    """The annual payment per unit of capex, over ``lifetime_years`` at ``rate``.

    A zero rate is straight-line: the limit of the annuity as i → 0 is 1/L, and writing it as
    a special case keeps a 0% sensitivity run from dividing by zero.
    """
    if lifetime_years <= 0:
        raise ValueError(f"lifetime must be positive to annuitise, got {lifetime_years!r}")
    if rate == 0.0:
        return 1.0 / lifetime_years
    return rate / (1.0 - (1.0 + rate) ** -lifetime_years)


def _scenario_series(
    reference: ReferenceTables,
    parameter_id: str,
    carrier_id: str | None,
    periods: Sequence[int],
) -> list[float]:
    """A ``scenario_parameters`` series over the period vector, failing loud on a gap.

    The partial case is the dangerous one (§3.2): ``heavy_fuel_oil`` carries exactly one
    ``import_price`` row, at 2021, and a test that asks only whether a carrier has *a* price
    misses it. Naming the missing periods is what note 20 records.
    """
    table = reference.scenario_parameters
    required = {"parameter_id", "carrier_id", "period", "value"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"scenario_parameters is missing {sorted(missing)}")
    rows = table[table["parameter_id"] == parameter_id]
    if carrier_id is not None:
        rows = rows[rows["carrier_id"] == carrier_id]
    by_year: dict[int, float] = {}
    for row in rows.itertuples(index=False):
        year = _as_float(row.period)
        value = _as_float(row.value)
        if year is None or value is None:
            continue
        by_year[int(year)] = value
    absent = [year for year in periods if year not in by_year]
    if absent:
        target = parameter_id if carrier_id is None else f"{parameter_id} for {carrier_id}"
        raise ValueError(
            f"scenario_parameters has no {target} at {absent}. A missing price or emission "
            "factor is read as free, which is the failure the §3.2 screen exists to prevent"
        )
    return [by_year[year] for year in periods]


def _scalar_parameter(reference: ReferenceTables, parameter_id: str) -> float:
    """A ``scenario_parameters`` row with no period, such as ``discount_rate``."""
    table = reference.scenario_parameters
    rows = table[table["parameter_id"] == parameter_id]
    values = [value for value in (_as_float(item) for item in rows["value"]) if value is not None]
    if not values:
        raise ValueError(f"scenario_parameters carries no {parameter_id!r} row")
    return values[0]


def _as_float(value: object) -> float | None:
    """Coerce a cell to a float, or ``None`` where it is blank. Never silently zero."""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        return float(text)
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def _as_text(value: object) -> str:
    """A cell as stripped text, with a blank for a missing one.

    ``str(value or "")`` will not do: a blank ``carbon_charge`` arrives as ``float('nan')``,
    which is **truthy**, so the idiom yields the string ``"nan"``. It compares unequal to
    ``"charged"`` either way, so nothing was mispriced — but it reached the ledger, where a
    carrier's charge status is printed beside the quantity it was charged on.
    """
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    if value is pd.NA or (not isinstance(value, str) and pd.isna(value)):
        return ""
    return str(value).strip()


def _as_bool(value: object) -> bool:
    """Coerce a CSV flag to a bool, whatever the loader made of it. A blank is ``False``."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().upper() in {"TRUE", "T", "YES", "Y", "1"}
    number = _as_float(value)
    return bool(number) if number is not None else False
