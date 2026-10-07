"""Cost by term, carrier mix, dispatch, build, disposal, unit flow -> parquet.

CSV is for hand-authored inputs; **outputs and any fixture written for M2 are parquet**
(§3.4, §7). The run report the ledger writes alongside them carries the §3.2 screen's
dropped-unit list, which is what note 20 records (§5.4), and the per-premise variable count,
constraint count and solve time that start the G1 (single-premise wall clock) measurement.

There is no attribution layer here: ``MF-52``, ``MF-53`` and ``MF-79`` are out (§6.3). The
ledger reports what the LP decided, it does not allocate emissions.

**Disposal is a reported quantity, not a residual.** How much low-grade heat a site throws
away and how much CO₂ it vents are rows in :attr:`Ledger.disposal`, not something a reader
has to infer by differencing the carrier mix — and since §5.4 charges carbon on venting
rather than on fuel, the disposal table is also where the carbon bill is legible.

**Every number here is read back from the solution, never recomputed from a pathway
narrative.** The cost decomposition in particular reads the same ``scenario_parameters``
rows and the same ``unit.csv`` columns the objective did, so "the terms sum to the reported
objective" is a real check on the build rather than a restatement of it.

Owed by T8's reporting paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from carb3.build import (
    CARBON_UNIT_CONVERSION,
    PRIMARY_OUTPUT_ROLE,
    SUPPLY_PREFIX,
    PeriodAxis,
    SolveResult,
    _annuity_factor,
    _balance_terms,
    _carrier_facts,
    _dispatch_pairs,
    _release_coordinate,
    _scalar_parameter,
    _scenario_series,
    _supplied,
    _unit_parameters,
    CaptureLink,
    biogenic_capture_links,
    capture_links,
    capture_rates,
    captured_flows,
    export_unit_cost,
)
from carb3.load import AdmissionScreen, ReferenceTables, UnitDrop
from carb3.sets import EligibilityDrop, ModelSets, recovery_units

#: The objective's five live terms, in §5.4's order. ``Z^infra``, ``Z^net`` and
#: ``Z^strand`` are out of the slice (§2.1) and carry no row rather than a row of zeros.
#: ``export`` is §5.4's ``Z^exp`` with the §3.7 transport tariff folded in, and it is the
#: one term that can carry either sign: electricity sold is a revenue, captured CO₂ handed
#: to a pipeline is a cost. At the cement works it is a cost.
COST_TERMS: tuple[str, ...] = ("capex", "opex", "fuel", "carbon", "export")

#: The role ``unit_flow`` files a unit's output to a duty under. It is not a
#: ``unit_input_output`` role: C1 (duty satisfaction) settles it, not C8 (carrier balance),
#: and the carrier is the one the duty is on, which C10 (heat grade cascade) lets differ
#: from the unit's declared primary output — a grade-3 boiler serving a grade-2 duty.
DUTY_OUTPUT_ROLE: str = "duty_output"

#: What :func:`write_parquet` writes, and the order it returns the paths in.
LEDGER_TABLES: tuple[str, ...] = (
    "cost_by_term",
    "carrier_mix",
    "dispatch",
    "build",
    "disposal",
    "unit_flow",
    "capture_by_host",
)

#: Columns of ``capture_by_host.parquet``: one row per (train, host, carrier, period).
CAPTURE_BY_HOST_COLUMNS: tuple[str, ...] = (
    "unit_id", "host_unit_id", "carrier_id", "period", "rate", "treated_activity", "captured",
)


@dataclass(frozen=True)
class Ledger:
    """The seven output tables, long-form, one row per keyed observation."""

    #: One row per ``(period, term)`` over :data:`COST_TERMS`: capex, opex, fuel, carbon and
    #: export. The terms must sum to the reported objective – that is one of the §5.3 test
    #: paths.
    cost_by_term: pd.DataFrame
    #: One row per ``(carrier_id, period)``: imported, produced, consumed, disposed.
    carrier_mix: pd.DataFrame
    #: z_{u,q,t} — one row per ``(unit_id, duty, period)``.
    dispatch: pd.DataFrame
    #: n_{u,t} and a_{u,t} — one row per ``(unit_id, period)``.
    build: pd.DataFrame
    #: d_{c,t} — one row per ``(carrier_id, period)``, the venting that carbon is charged on.
    disposal: pd.DataFrame
    #: How much of which carrier each unit drew or made — one row per
    #: ``(unit_id, carrier_id, role, period)``, signed: + produced, − consumed.
    unit_flow: pd.DataFrame
    #: C14 (a capture train treats its hosts' flue gas), split by host — one row per
    #: ``(unit_id, host_unit_id, carrier_id, period)``: the rate ν, the host activity the
    #: train treats (z^host) and the kt captured. Its ``captured`` sums, over hosts, to the
    #: train's ``emission_input`` rows in ``unit_flow``. Where a train's capacity binds the
    #: split across hosts is an allocation the LP chose, not a measurement.
    capture_by_host: pd.DataFrame = field(
        default_factory=lambda: pd.DataFrame(columns=list(CAPTURE_BY_HOST_COLUMNS))
    )


#: New capacity at or below this is solver noise, not a build.
BUILD_TOLERANCE: float = 1e-9

#: Columns of ``sub_minimum_recovery.parquet``, one row per :class:`SubMinimumBuild`.
SUB_MINIMUM_COLUMNS: tuple[str, ...] = (
    "unit_id", "period", "new_capacity", "min_viable_scale",
)


@dataclass(frozen=True)
class SubMinimumBuild:
    """A recovery unit the LP built in a period at less than its ``min_viable_scale`` (§3.5).

    The recovery unit size screen decides only whether the unit is offered; the problem stays
    a pure LP, with no binary to hold a build at zero or at the floor, so the optimiser may
    build less. That is reported after the solve rather than constrained, the way §3.5.1
    reports a site whose optimal size lands below a credible minimum (§5.7, check 5).
    """

    unit_id: str
    period: int
    #: n_{u,t}, PJ/yr of primary output.
    new_capacity: float
    #: PJ/yr of the reject class the unit draws.
    min_viable_scale: float


def check_recovery_scale(
    build_table: pd.DataFrame, reference: ReferenceTables
) -> tuple[SubMinimumBuild, ...]:
    """Every (recovery unit, period) whose new capacity is positive and below its
    ``min_viable_scale``, read from the ledger's ``build`` table (§5.7, check 5).

    A recovery unit is one drawing a reject source class (:func:`carb3.sets.recovery_units`);
    one with a blank ``min_viable_scale`` has no floor to fall below. A report, never an
    exception: the run stays solved and the objective is what the LP found.
    """
    if build_table is None or len(build_table) == 0:
        return ()
    scale = reference.unit.set_index("unit_id")["min_viable_scale"]
    floors = {
        unit_id: float(scale.loc[unit_id])
        for unit_id in recovery_units(reference)
        if unit_id in scale.index and not pd.isna(scale.loc[unit_id])
    }
    found: list[SubMinimumBuild] = []
    for row in build_table.itertuples(index=False):
        unit_id = str(row.unit_id)
        if unit_id not in floors:
            continue
        new = float(row.new_capacity)
        if BUILD_TOLERANCE < new < floors[unit_id]:
            found.append(SubMinimumBuild(unit_id, int(row.period), new, floors[unit_id]))
    return tuple(sorted(found, key=lambda item: (item.unit_id, item.period)))


@dataclass(frozen=True)
class RunReport:
    """What the run says about itself, beside the ledger."""

    premise_id: str
    screen: AdmissionScreen
    n_variables: int
    n_constraints: int
    wall_clock_seconds: float
    status: str
    #: The objective the solver reported, £m. Written so a reader of the parquet alone — the
    #: site report — can check the cost terms against it without re-solving.
    objective: float | None = None
    #: Units removed from a process by ``min_duty``, a 0.00 ``max_share`` or a recovery
    #: unit's ``min_viable_scale``. Written to its own table because the unit stays admitted:
    #: ``screen_dropped`` is per unit, this is per process.
    eligibility_dropped: tuple[EligibilityDrop, ...] = ()
    #: Units :func:`carb3.build.screen_premise` dropped at this premise, because an input
    #: could be neither imported nor made here. Written beside the §3.2 screen's list in
    #: ``screen_dropped.parquet`` under their own leg.
    premise_dropped: tuple[UnitDrop, ...] = ()
    #: Recovery units built below their ``min_viable_scale``, from
    #: :func:`check_recovery_scale`. Written to ``sub_minimum_recovery.parquet``.
    sub_minimum: tuple[SubMinimumBuild, ...] = ()


def build_ledger(
    result: SolveResult,
    sets: ModelSets,
    axis: PeriodAxis,
    reference: ReferenceTables,
    tariff_override: float | None = None,
) -> Ledger:
    """Decompose the solution into the seven tables above.

    **``reference`` is the fourth argument the scaffolded signature lacked.** The three it
    named carry the *shape* of the answer and none of its prices: κ, φ and L live in
    ``unit.csv``, ``import_price``, ``carbon_price`` and ``discount_rate`` in
    ``scenario_parameters.csv``, and the ι coefficients behind the carrier mix in
    ``unit_input_output.csv``. Without them ``cost_by_term`` — the table whose whole
    contract is to sum to the reported objective — cannot be computed at all.

    Raises on a result with no solution: a non-optimal solve is reported by
    :func:`carb3.build.solve` and has no pathway to decompose (§5.2).
    """
    if result.solution is None:
        raise ValueError(
            "build_ledger needs a solved model; the result carries no solution "
            f"(status={result.status!r}, termination={result.termination_condition!r}). "
            "§5.2 makes a non-optimal status a reported outcome, not a pathway"
        )
    periods = tuple(int(year) for year in sets.periods)
    if tuple(axis.years) != periods:
        raise ValueError(
            f"the period axis {axis.years} does not match the model sets' periods {periods}"
        )

    pairs = _dispatch_pairs(sets)
    model_units = sorted({pair.unit_id for pair in pairs})
    parameters = _unit_parameters(reference, model_units)
    carrier_facts = _carrier_facts(reference)
    supplied = _supplied(sets)
    terms = _balance_terms(reference, model_units, periods, carrier_facts, supplied)

    solution = result.solution
    z = _series(solution, "z", "dispatch", periods)
    n = _series(solution, "n", "unit", periods)
    a = _series(solution, "a", "unit", periods)
    e = _series(solution, "e", "unit", periods)
    m = _series(solution, "m", "carrier", periods)
    d = _series(solution, "d", "carrier", periods)
    x = _series(solution, "x", "carrier", periods)

    activity = _activity_by_unit(pairs, z, model_units, periods)
    # C14 (a capture train treats its hosts' flue gas): Γ_{u,c,t} from the solved z^host,
    # through the same links the LP was built from.
    links = capture_links(reference, model_units, terms)
    treated = _series(solution, "z_host", "capture", periods)
    captured = captured_flows(links, treated, len(periods))
    # Each unit's net C8 flow per carrier, with every role scaled by the variable C8 scales it
    # by: a primary output by the unit's z° column, everything else by total activity.
    c8_flow = {
        carrier_id: {
            unit_id: sum(
                (
                    np.asarray(weights, dtype=float)
                    * _role_activity(unit_id, carrier_id, role, activity, z, len(periods))
                    for role, weights in by_role.items()
                ),
                np.zeros(len(periods)),
            )
            for unit_id, by_role in by_unit.items()
        }
        for carrier_id, by_unit in terms.items()
    }
    for (train, carrier_id), values in captured.items():
        node = c8_flow.setdefault(carrier_id, {})
        node[train] = node.get(train, np.zeros(len(periods))) - values
    dispatch = _dispatch_table(pairs, z, periods)
    build = _build_table(model_units, periods, n, a, e)
    disposal = _disposal_table(reference, carrier_facts, d, periods)
    carrier_mix = _carrier_mix_table(c8_flow, carrier_facts, m, d, x, dispatch, periods)
    unit_flow = _unit_flow_table(terms, carrier_facts, activity, pairs, z, periods, captured)
    cost_by_term = _cost_table(
        reference, axis, periods, model_units, parameters, carrier_facts, a, e, m, d, x,
        links, treated, tariff_override,
    )
    return Ledger(
        cost_by_term=cost_by_term,
        carrier_mix=carrier_mix,
        dispatch=dispatch,
        build=build,
        disposal=disposal,
        unit_flow=unit_flow,
        capture_by_host=_capture_by_host_table(links, treated, periods),
    )


def write_parquet(ledger: Ledger, report: RunReport, out_dir: Path) -> tuple[Path, ...]:
    """Write the ledger and the run report under ``out_dir``, returning the paths written.

    One directory per premise, so two premises written to the same root do not overwrite
    each other. Eleven files: the seven ledger tables (``capture_by_host`` among them,
    empty at a premise with no capture train), ``run_report.parquet`` – one row, the
    G1 (single-premise wall clock) measurement, the solver status and the objective –
    ``screen_dropped.parquet``, the §3.2 screen's work list, which is the table note 20
    records, followed by this premise's ``unreachable_input`` and ``no_capture_host`` drops
    (:func:`carb3.build.screen_premise`). Those are not data defects: the unit is sound and
    was offered to a site that cannot fuel it, so a reader building note 20's list filters
    them out on ``leg``; ``n_units_dropped`` counts the §3.2 screen's units only and
    ``n_units_dropped_at_premise`` these. The tenth is
    ``eligibility_dropped.parquet``, the units a process refused by ``min_duty``, a 0.00
    ``max_share`` or a recovery unit's ``min_viable_scale`` (admitted units, so not in the
    screen's list). The eleventh is ``sub_minimum_recovery.parquet``, the recovery units the LP
    built below their ``min_viable_scale`` (:func:`check_recovery_scale`). All three lists
    are written even when empty, because "nothing was dropped" is a finding too and an
    absent file cannot say it.

    Parquet, not CSV: §3.4's split is that hand-authored inputs stay diffable and outputs do
    not need to be.
    """
    directory = Path(out_dir) / report.premise_id
    directory.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for name in LEDGER_TABLES:
        path = directory / f"{name}.parquet"
        getattr(ledger, name).to_parquet(path, index=False)
        written.append(path)

    report_path = directory / "run_report.parquet"
    pd.DataFrame(
        [
            {
                "premise_id": report.premise_id,
                "status": report.status,
                "objective": report.objective,
                "n_variables": report.n_variables,
                "n_constraints": report.n_constraints,
                "wall_clock_seconds": report.wall_clock_seconds,
                "n_units_admitted": len(report.screen.admitted),
                "n_units_dropped": len({drop.unit_id for drop in report.screen.dropped}),
                "n_units_dropped_at_premise": len(
                    {drop.unit_id for drop in report.premise_dropped}
                ),
            }
        ]
    ).to_parquet(report_path, index=False)
    written.append(report_path)

    dropped_path = directory / "screen_dropped.parquet"
    pd.DataFrame(
        [
            {"unit_id": drop.unit_id, "leg": drop.leg, "detail": drop.detail}
            for drop in (*report.screen.dropped, *report.premise_dropped)
        ],
        columns=["unit_id", "leg", "detail"],
    ).to_parquet(dropped_path, index=False)
    written.append(dropped_path)

    refused_path = directory / "eligibility_dropped.parquet"
    pd.DataFrame(
        [
            {
                "premise_id": drop.premise_id,
                "process_id": drop.process_id,
                "unit_id": drop.unit_id,
                "reason": drop.reason,
                "detail": drop.detail,
            }
            for drop in report.eligibility_dropped
        ],
        columns=["premise_id", "process_id", "unit_id", "reason", "detail"],
    ).to_parquet(refused_path, index=False)
    written.append(refused_path)

    small_path = directory / "sub_minimum_recovery.parquet"
    pd.DataFrame(
        [
            {
                "unit_id": item.unit_id,
                "period": item.period,
                "new_capacity": item.new_capacity,
                "min_viable_scale": item.min_viable_scale,
            }
            for item in report.sub_minimum
        ],
        columns=list(SUB_MINIMUM_COLUMNS),
    ).to_parquet(small_path, index=False)
    written.append(small_path)

    return tuple(written)


# --------------------------------------------------------------------------------------
# Internals
# --------------------------------------------------------------------------------------


def _series(
    solution: xr.Dataset, name: str, dimension: str, periods: tuple[int, ...]
) -> dict[str, np.ndarray]:
    """One solved variable as ``coordinate -> values over the periods``.

    A variable the model never declared — ``e`` at a greenfield premise, ``d`` where no
    carrier may be disposed of — is simply absent, and an empty mapping is the right answer
    rather than an error.

    **An all-``NaN`` row is dropped, and that is not cosmetic.** linopy merges every
    variable into one ``Dataset`` on an outer join, so ``m`` and ``d`` end up sharing one
    ``carrier`` dimension: every disposable carrier appears under ``m`` as ``NaN``, meaning
    "there is no import variable here". Reading those as zero would be numerically harmless
    and then fatal one step later, because the fuel term would ask
    ``scenario_parameters`` for an ``import_price`` for ``heat_lt60`` and be told, rightly,
    that there is none. A solved variable is never ``NaN``, so an all-``NaN`` row is an
    absence and nothing else.
    """
    if name not in solution:
        return {}
    array = solution[name]
    if dimension not in array.dims:
        return {}
    array = array.sel(period=list(periods))
    values: dict[str, np.ndarray] = {}
    for coordinate in array.coords[dimension].values:
        row = np.asarray(array.sel({dimension: coordinate}).values, dtype=float)
        if np.all(np.isnan(row)):
            continue
        values[str(coordinate)] = np.nan_to_num(row, nan=0.0)
    return values


def _column(values: dict[str, np.ndarray], key: str, n_periods: int) -> np.ndarray:
    return values.get(key, np.zeros(n_periods))


def _activity_by_unit(
    pairs, z: dict[str, np.ndarray], model_units: list[str], periods: tuple[int, ...]
) -> dict[str, np.ndarray]:
    """z_{u,t} — the total activity C2 and C8 read, recovered from the flattened dimension."""
    totals = {unit_id: np.zeros(len(periods)) for unit_id in model_units}
    for pair in pairs:
        totals[pair.unit_id] = totals[pair.unit_id] + _column(
            z, pair.coordinate, len(periods)
        )
    return totals


def _dispatch_table(pairs, z: dict[str, np.ndarray], periods: tuple[int, ...]) -> pd.DataFrame:
    """z_{u,q,t}, one row per ``(unit_id, duty, period)``.

    A z° column carries ``kind`` ``supply`` and no process: output released to C8 (carrier
    balance) rather than dispatched to a duty in C1 (duty satisfaction). Two sources sit
    here. D16 supply is a unit making a carrier that carries no duty row: the cement kilns'
    ``clinker`` and ``ccs_amine``'s ``co2_captured``. A released duty unit makes a carrier
    another unit draws: ``heat_pump_chiller_condenser``'s ``heat_60_100``, lifted by ``heat_pump_ht``.
    ``ModelSets.supply`` and ``ModelSets.released`` tell the two apart.
    """
    records = []
    for pair in pairs:
        values = _column(z, pair.coordinate, len(periods))
        if pair.duty_key is None:
            premise_id, process_id = "", ""
            carrier_id = pair.label.removeprefix(SUPPLY_PREFIX)
            kind = "supply"
        else:
            premise_id, process_id, carrier_id = pair.duty_key
            kind = "duty"
        for index, year in enumerate(periods):
            records.append(
                {
                    "unit_id": pair.unit_id,
                    "premise_id": premise_id,
                    "process_id": process_id,
                    "carrier_id": carrier_id,
                    "duty": pair.label,
                    "kind": kind,
                    "period": year,
                    "activity": float(values[index]),
                }
            )
    return pd.DataFrame.from_records(
        records,
        columns=["unit_id", "premise_id", "process_id", "carrier_id", "duty", "kind",
                 "period", "activity"],
    )


def _build_table(
    model_units: list[str],
    periods: tuple[int, ...],
    n: dict[str, np.ndarray],
    a: dict[str, np.ndarray],
    e: dict[str, np.ndarray],
) -> pd.DataFrame:
    """n_{u,t}, a_{u,t} and e_{u,t}, with the new capacity standing that capex is charged on.

    ``built_standing`` is ``a − e``, which is C3 (capacity transfer) read backwards: the
    constraint pins available capacity to the build convolution plus the surviving
    incumbent, so the difference is exactly the convolution the objective annuitises. Taking
    it from the solved ``a`` rather than re-convolving ``n`` keeps the cost table tied to
    the rows the solver actually satisfied.
    """
    records = []
    for unit_id in model_units:
        new = _column(n, unit_id, len(periods))
        available = _column(a, unit_id, len(periods))
        surviving = _column(e, unit_id, len(periods))
        for index, year in enumerate(periods):
            records.append(
                {
                    "unit_id": unit_id,
                    "period": year,
                    "new_capacity": float(new[index]),
                    "available_capacity": float(available[index]),
                    "surviving_capacity": float(surviving[index]),
                    "built_standing": float(available[index] - surviving[index]),
                }
            )
    return pd.DataFrame.from_records(
        records,
        columns=["unit_id", "period", "new_capacity", "available_capacity",
                 "surviving_capacity", "built_standing"],
    )


def _disposal_table(
    reference: ReferenceTables,
    carrier_facts,
    d: dict[str, np.ndarray],
    periods: tuple[int, ...],
) -> pd.DataFrame:
    """d_{c,t}, with the carbon each vented quantity was charged.

    Reported on purpose (plan §2.2): the heat a site throws away and the CO₂ it vents are
    answers, not leftovers. ``carbon_cost`` is zero for a ``zero_rated`` or unpriced carrier
    and non-zero only where ``carrier.carbon_charge`` is ``charged``, which is the whole of
    §5.4's Z^carbon read one carrier at a time.
    """
    if not d:
        return pd.DataFrame(
            columns=["carrier_id", "period", "quantity", "carbon_charge", "carbon_price",
                     "carbon_cost"]
        )
    carbon_price = _scenario_series(reference, "carbon_price", None, periods)
    records = []
    for carrier_id in sorted(d):
        values = d[carrier_id]
        charge = carrier_facts[carrier_id].carbon_charge
        for index, year in enumerate(periods):
            cost = (
                float(values[index]) * CARBON_UNIT_CONVERSION * carbon_price[index]
                if charge == "charged"
                else 0.0
            )
            records.append(
                {
                    "carrier_id": carrier_id,
                    "period": year,
                    "quantity": float(values[index]),
                    "carbon_charge": charge,
                    "carbon_price": float(carbon_price[index]),
                    "carbon_cost": cost,
                }
            )
    return pd.DataFrame.from_records(
        records,
        columns=["carrier_id", "period", "quantity", "carbon_charge", "carbon_price",
                 "carbon_cost"],
    )


def _role_activity(
    unit_id: str,
    carrier_id: str,
    role: str,
    activity: dict[str, np.ndarray],
    z: dict[str, np.ndarray],
    n_periods: int,
) -> np.ndarray:
    """The solved variable C8 scales a (unit, carrier, role) term by: the unit's z° column on
    the carrier for a primary output, its total activity for every other role."""
    if role == PRIMARY_OUTPUT_ROLE:
        return _column(z, _release_coordinate(unit_id, carrier_id), n_periods)
    return activity.get(unit_id, np.zeros(n_periods))


def _carrier_mix_table(
    c8_flow: dict[str, dict[str, np.ndarray]],
    carrier_facts,
    m: dict[str, np.ndarray],
    d: dict[str, np.ndarray],
    x: dict[str, np.ndarray],
    dispatch: pd.DataFrame,
    periods: tuple[int, ...],
) -> pd.DataFrame:
    """Imported, produced, consumed, disposed and dispatched, per carrier and period.

    ``produced`` and ``consumed`` are the C8 (carrier balance) coefficient set read with the
    solved activity — the positive and negative halves separately, so a carrier a unit both
    makes and burns is legible rather than netted. ``net`` is C8's own residual and is zero
    at every node the constraint covers; :func:`carb3.build.check_constraint_rows` proves
    that against the built matrix, and this column is the same statement in the output.

    ``dispatched`` is the duty side, which C8 never sees: a duty carrier is settled by C1
    (duty satisfaction), so without this column the heat a site actually delivers would not
    appear anywhere in the ledger.
    """
    dispatched: dict[str, np.ndarray] = {}
    duty_rows = dispatch[dispatch["kind"] == "duty"]
    for carrier_id, group in duty_rows.groupby("carrier_id", sort=True):
        by_period = group.groupby("period")["activity"].sum()
        dispatched[str(carrier_id)] = np.array(
            [float(by_period.get(year, 0.0)) for year in periods]
        )

    carriers = sorted(set(c8_flow) | set(m) | set(d) | set(x) | set(dispatched))
    records = []
    for carrier_id in carriers:
        produced = np.zeros(len(periods))
        consumed = np.zeros(len(periods))
        for flow in c8_flow.get(carrier_id, {}).values():
            produced += np.clip(flow, 0.0, None)
            consumed += -np.clip(flow, None, 0.0)
        imported = _column(m, carrier_id, len(periods))
        disposed = _column(d, carrier_id, len(periods))
        exported = _column(x, carrier_id, len(periods))
        served = _column(dispatched, carrier_id, len(periods))
        facts = carrier_facts.get(carrier_id)
        for index, year in enumerate(periods):
            records.append(
                {
                    "carrier_id": carrier_id,
                    "period": year,
                    "carrier_kind": facts.kind if facts else "",
                    "imported": float(imported[index]),
                    "produced": float(produced[index]),
                    "consumed": float(consumed[index]),
                    "disposed": float(disposed[index]),
                    "exported": float(exported[index]),
                    "dispatched": float(served[index]),
                    "net": float(
                        imported[index]
                        + produced[index]
                        - consumed[index]
                        - disposed[index]
                        - exported[index]
                    ),
                }
            )
    return pd.DataFrame.from_records(
        records,
        columns=["carrier_id", "period", "carrier_kind", "imported", "produced", "consumed",
                 "disposed", "exported", "dispatched", "net"],
    )


def _unit_flow_table(
    terms: dict[str, dict[str, dict[str, np.ndarray]]],
    carrier_facts,
    activity: dict[str, np.ndarray],
    pairs,
    z: dict[str, np.ndarray],
    periods: tuple[int, ...],
    captured: dict[tuple[str, str], np.ndarray] | None = None,
) -> pd.DataFrame:
    """Each unit's draw and output per carrier, role and period, signed.

    Two sources, both read from the solution. **C8's terms** — the same coefficient set the
    constraint was built from, by role, times the solved activity: a fuel or auxiliary
    draw, a reject, a declared or A6-derived emission, and the primary output of a D16
    (internal product) supplier such as the kiln's clinker. **C1's side** — the solved
    z_{u,q,t} summed per unit and duty carrier, under :data:`DUTY_OUTPUT_ROLE`; a
    ``primary_output`` coefficient is 1 on every row of ``unit_input_output``, so this is
    also the unit's primary output, re-labelled to the carrier the duty is on.

    The split is what makes the table checkable against ``carrier_mix``: the positive
    C8-side flows sum to ``produced``, the negative to ``consumed``, and the duty-side flows
    to ``dispatched``, per carrier and period. Nothing here is re-joined from the CSV.

    A capture train's draw is the third source: Γ_{u,c,t} from C14 (a capture train treats
    its hosts' flue gas), negative and under the role ``emission_input``, which is what
    ``report/sankey_data.py`` reads as captured CO₂. Its rate row is not a C8 coefficient,
    so it is not in ``terms``.

    A (unit, carrier, role) whose flow is zero in every period carries no rows.
    """
    n_periods = len(periods)
    series: dict[tuple[str, str, str], np.ndarray] = {}
    for carrier_id, by_unit in terms.items():
        for unit_id, by_role in by_unit.items():
            for role, weights in by_role.items():
                flow = np.asarray(weights, dtype=float) * _role_activity(
                    unit_id, carrier_id, role, activity, z, n_periods
                )
                key = (unit_id, carrier_id, role)
                series[key] = series.get(key, np.zeros(n_periods)) + flow
    for (train, carrier_id), values in (captured or {}).items():
        key = (train, carrier_id, "emission_input")
        series[key] = series.get(key, np.zeros(n_periods)) - values
    for pair in pairs:
        if pair.duty_key is None:
            continue
        _premise_id, _process_id, carrier_id = pair.duty_key
        key = (pair.unit_id, carrier_id, DUTY_OUTPUT_ROLE)
        series[key] = series.get(key, np.zeros(n_periods)) + _column(
            z, pair.coordinate, n_periods
        )

    records = []
    for (unit_id, carrier_id, role), values in sorted(series.items()):
        if not np.any(np.abs(values) > 0.0):
            continue
        facts = carrier_facts.get(carrier_id)
        for index, year in enumerate(periods):
            records.append(
                {
                    "unit_id": unit_id,
                    "carrier_id": carrier_id,
                    "role": role,
                    "period": year,
                    "carrier_kind": facts.kind if facts else "",
                    "flow": float(values[index]),
                }
            )
    return pd.DataFrame.from_records(
        records,
        columns=["unit_id", "carrier_id", "role", "period", "carrier_kind", "flow"],
    )


def _cost_table(
    reference: ReferenceTables,
    axis: PeriodAxis,
    periods: tuple[int, ...],
    model_units: list[str],
    parameters,
    carrier_facts,
    a: dict[str, np.ndarray],
    e: dict[str, np.ndarray],
    m: dict[str, np.ndarray],
    d: dict[str, np.ndarray],
    x: dict[str, np.ndarray],
    links: tuple[CaptureLink, ...] = (),
    treated: dict[str, np.ndarray] | None = None,
    tariff_override: float | None = None,
) -> pd.DataFrame:
    """Z^capex, Z^opex, Z^fuel, Z^carbon and Z^exp by period, undiscounted and discounted.

    The discounted column sums to the objective the solver reported, which is the §5.3 path
    "objective decomposition — terms sum to the reported objective". Nothing here is a
    restatement of the objective expression: it reads the solved variables and the same
    ``scenario_parameters`` and ``unit.csv`` values the build read, so the two agreeing is
    evidence that the objective was assembled from the parameters it claims.

    §5.4's biogenic credit nets off the carbon term: 10⁻³ π_t Σ Γ_{u,c,t} over the
    ``zero_rated`` carriers, with Γ read from the solved z^host through the same links the
    objective was built from. Both sides read :func:`carb3.build.biogenic_capture_links`, so a
    ledger that dropped the credit could not still sum to the reported objective.
    """
    rate = _scalar_parameter(reference, "discount_rate")
    n_periods = len(periods)

    capex = np.zeros(n_periods)
    opex = np.zeros(n_periods)
    for unit_id in model_units:
        available = _column(a, unit_id, n_periods)
        surviving = _column(e, unit_id, n_periods)
        unit = parameters[unit_id]
        capex += (available - surviving) * unit.kappa * _annuity_factor(rate, unit.lifetime)
        opex += available * unit.phi

    fuel = np.zeros(n_periods)
    for carrier_id, imported in m.items():
        prices = np.array(_scenario_series(reference, "import_price", carrier_id, periods))
        fuel += imported * prices

    carbon_price = np.array(_scenario_series(reference, "carbon_price", None, periods))
    carbon = np.zeros(n_periods)
    for carrier_id, vented in d.items():
        if carrier_facts[carrier_id].carbon_charge == "charged":
            carbon += vented * CARBON_UNIT_CONVERSION * carbon_price
    credited = biogenic_capture_links(links, carrier_facts)
    for values in captured_flows(credited, treated or {}, n_periods).values():
        carbon -= values * CARBON_UNIT_CONVERSION * carbon_price

    export = np.zeros(n_periods)
    for carrier_id, exported in x.items():
        export += exported * np.array(
            export_unit_cost(reference, carrier_id, periods, tariff_override)
        )

    delta = np.array(axis.discount_factors, dtype=float)
    records = []
    for term, values in zip(
        COST_TERMS, (capex, opex, fuel, carbon, export), strict=True
    ):
        for index, year in enumerate(periods):
            records.append(
                {
                    "period": year,
                    "term": term,
                    "annual": float(values[index]),
                    "discount_factor": float(delta[index]),
                    "discounted": float(values[index] * delta[index]),
                }
            )
    return pd.DataFrame.from_records(
        records, columns=["period", "term", "annual", "discount_factor", "discounted"]
    )


def _capture_by_host_table(
    links: tuple[CaptureLink, ...],
    treated: dict[str, np.ndarray],
    periods: tuple[int, ...],
) -> pd.DataFrame:
    """C14 split by host: what each train treats of each host and captures from it."""
    records = []
    for link in links:
        activity = treated.get(link.coordinate, np.zeros(len(periods)))
        captured = link.weight * activity
        for index, year in enumerate(periods):
            records.append(
                {
                    "unit_id": link.train,
                    "host_unit_id": link.host,
                    "carrier_id": link.carrier_id,
                    "period": year,
                    "rate": float(link.rate),
                    "treated_activity": float(activity[index]),
                    "captured": float(captured[index]),
                }
            )
    return pd.DataFrame.from_records(records, columns=list(CAPTURE_BY_HOST_COLUMNS))


@dataclass(frozen=True)
class CaptureViolation:
    """One way a solved capture breaks V37 (a capture rate is a fraction of its hosts'
    streams), by leg: (c) a stream above ν times its hosts' gross production, (d) streams
    out of their host's proportions, (e) the trains on a host treating more than its
    activity, (f) the carbon term disagreeing with the credit the captured biogenic CO₂
    earns."""

    leg: str
    unit_id: str
    carrier_id: str
    period: int
    detail: str


def check_capture(
    tables: Ledger, reference: ReferenceTables, tolerance: float = 1e-6
) -> tuple[CaptureViolation, ...]:
    """V37's post-solve legs (c) to (f), read from the ledger's own tables (§5.7, check 6).

    Nothing here asks the build: hosts' gross production comes from ``unit_flow``'s
    ``emission`` and derived rows, host activity from ``dispatch``, the rates from
    ``unit_input_output``, so a C14 written wrongly is caught even where the row check passes.
    A report, never an exception.
    """
    found: list[CaptureViolation] = []
    flow = tables.unit_flow
    by_host = tables.capture_by_host
    rates = capture_rates(reference)
    if by_host is None or len(by_host) == 0:
        return ()
    gross = (
        flow[flow["role"].isin(["emission", "emission_derived"])]
        .groupby(["unit_id", "carrier_id", "period"])["flow"]
        .sum()
    )
    taken = (
        -flow[(flow["role"] == "emission_input") & flow["unit_id"].isin(list(rates))]
        .groupby(["unit_id", "carrier_id", "period"])["flow"]
        .sum()
    )
    activity = tables.dispatch.groupby(["unit_id", "period"])["activity"].sum()
    # The hosts come from the data, not from the build's links: a link the build should not
    # have made (a train named as its own host) must not widen what leg (c) allows. A train
    # never hosts itself (§3.5.3), and only hosts with rows in this run count.
    in_run = set(flow["unit_id"].astype(str))
    host_table = reference.unit_abatement_host
    hosts_of: dict[str, list[str]] = {}
    if host_table is not None and "unit_id" in host_table.columns:
        for train, host in zip(host_table["unit_id"], host_table["host_unit_id"], strict=True):
            train, host = str(train), str(host)
            if host != train and host in in_run:
                hosts_of.setdefault(train, []).append(host)

    def scale(value: float) -> float:
        return tolerance * max(1.0, abs(value))

    # (c) no stream above ν times its hosts' gross production.
    for (train, carrier_id, period), value in taken.items():
        rate = rates.get(train, {}).get(carrier_id)
        if rate is None:
            continue
        made = sum(
            float(gross.get((host, carrier_id, period), 0.0)) for host in hosts_of.get(train, [])
        )
        if value > rate * made + scale(made):
            found.append(CaptureViolation(
                "c", train, carrier_id, int(period),
                f"captured {value:.6g} kt against {rate} x {made:.6g} kt its hosts make",
            ))

    # (d) within a host the captured streams stand in its production proportions, which
    # here reads: what is captured from a host is ν × its production × treated / activity.
    for row in by_host.itertuples(index=False):
        host_activity = float(activity.get((row.host_unit_id, row.period), 0.0))
        made = float(gross.get((row.host_unit_id, row.carrier_id, row.period), 0.0))
        if host_activity <= tolerance:
            expected = 0.0 if row.treated_activity <= tolerance else None
        else:
            expected = row.rate * made * row.treated_activity / host_activity
        if expected is None or abs(row.captured - expected) > scale(expected):
            found.append(CaptureViolation(
                "d", row.unit_id, row.carrier_id, int(row.period),
                f"captured {row.captured:.6g} kt from {row.host_unit_id}, where its share of "
                f"that host's stream gives {expected if expected is not None else 'nothing'}",
            ))

    # (e) the trains on one host treat at most its activity in total.
    shares = by_host.drop_duplicates(["unit_id", "host_unit_id", "period"])
    for (host, period), total in shares.groupby(["host_unit_id", "period"])[
        "treated_activity"
    ].sum().items():
        host_activity = float(activity.get((host, period), 0.0))
        if total > host_activity + scale(host_activity):
            found.append(CaptureViolation(
                "e", host, "", int(period),
                f"trains treat {total:.6g} of {host}'s activity of {host_activity:.6g}",
            ))

    # (f) the carbon term is the charged venting less 10⁻³ π Σ Γ on the zero-rated carriers.
    costs = tables.cost_by_term
    carbon = costs[costs["term"] == "carbon"].set_index("period")["annual"]
    charged = tables.disposal.groupby("period")["carbon_cost"].sum()
    prices = tables.disposal.groupby("period")["carbon_price"].first()
    zero_rated = set(
        reference.carrier.loc[
            reference.carrier["carbon_charge"].astype(str).str.strip() == "zero_rated",
            "carrier_id",
        ].astype(str)
    )
    biogenic = (
        taken[taken.index.get_level_values("carrier_id").isin(zero_rated)]
        .groupby(level="period")
        .sum()
    )
    for period, value in carbon.items():
        credit = float(biogenic.get(period, 0.0)) * CARBON_UNIT_CONVERSION * float(
            prices.get(period, 0.0)
        )
        expected = float(charged.get(period, 0.0)) - credit
        if abs(value - expected) > scale(expected):
            found.append(CaptureViolation(
                "f", "", "", int(period),
                f"carbon term {value:.6g} against charged venting less the credit, "
                f"{expected:.6g}",
            ))
    return tuple(found)
