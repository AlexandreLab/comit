"""Cost by term, carrier mix, dispatch, build, disposal -> parquet.

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

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from carb3.build import (
    CARBON_UNIT_CONVERSION,
    SUPPLY_PREFIX,
    PeriodAxis,
    SolveResult,
    _annuity_factor,
    _balance_coefficients,
    _carrier_facts,
    _dispatch_pairs,
    _scalar_parameter,
    _scenario_series,
    _unit_parameters,
    biogenic_capture_weights,
    export_unit_cost,
)
from carb3.load import AdmissionScreen, ReferenceTables
from carb3.sets import ModelSets

#: The objective's five live terms, in §5.4's order. ``Z^infra``, ``Z^net`` and
#: ``Z^strand`` are out of the slice (§2.1) and carry no row rather than a row of zeros.
#: ``export`` is §5.4's ``Z^exp`` with the §3.7 transport tariff folded in, and it is the
#: one term that can carry either sign: electricity sold is a revenue, captured CO₂ handed
#: to a pipeline is a cost. At the cement works it is a cost.
COST_TERMS: tuple[str, ...] = ("capex", "opex", "fuel", "carbon", "export")

#: What :func:`write_parquet` writes, and the order it returns the paths in.
LEDGER_TABLES: tuple[str, ...] = (
    "cost_by_term",
    "carrier_mix",
    "dispatch",
    "build",
    "disposal",
)


@dataclass(frozen=True)
class Ledger:
    """The five output tables, long-form, one row per keyed observation."""

    #: One row per ``(period, term)`` over capex, opex, fuel and carbon. The terms must sum
    #: to the reported objective — that is one of the §5.3 test paths.
    cost_by_term: pd.DataFrame
    #: One row per ``(carrier_id, period)``: imported, produced, consumed, disposed.
    carrier_mix: pd.DataFrame
    #: z_{u,q,t} — one row per ``(unit_id, duty, period)``.
    dispatch: pd.DataFrame
    #: n_{u,t} and a_{u,t} — one row per ``(unit_id, period)``.
    build: pd.DataFrame
    #: d_{c,t} — one row per ``(carrier_id, period)``, the venting that carbon is charged on.
    disposal: pd.DataFrame


@dataclass(frozen=True)
class RunReport:
    """What the run says about itself, beside the ledger."""

    premise_id: str
    screen: AdmissionScreen
    n_variables: int
    n_constraints: int
    wall_clock_seconds: float
    status: str


def build_ledger(
    result: SolveResult,
    sets: ModelSets,
    axis: PeriodAxis,
    reference: ReferenceTables,
    tariff_override: float | None = None,
) -> Ledger:
    """Decompose the solution into the five tables above.

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
    supplied = {
        carrier_id: frozenset(units & sets.units)
        for carrier_id, units in sorted(sets.supply.items())
        if units & sets.units
    }
    coefficients = _balance_coefficients(
        reference, model_units, periods, carrier_facts, supplied
    )

    solution = result.solution
    z = _series(solution, "z", "dispatch", periods)
    n = _series(solution, "n", "unit", periods)
    a = _series(solution, "a", "unit", periods)
    e = _series(solution, "e", "unit", periods)
    m = _series(solution, "m", "carrier", periods)
    d = _series(solution, "d", "carrier", periods)
    x = _series(solution, "x", "carrier", periods)

    activity = _activity_by_unit(pairs, z, model_units, periods)
    dispatch = _dispatch_table(pairs, z, periods)
    build = _build_table(model_units, periods, n, a, e)
    disposal = _disposal_table(reference, carrier_facts, d, periods)
    carrier_mix = _carrier_mix_table(
        coefficients, carrier_facts, activity, m, d, x, dispatch, periods
    )
    cost_by_term = _cost_table(
        reference, axis, periods, model_units, parameters, carrier_facts, a, e, m, d, x,
        activity, tariff_override,
    )
    return Ledger(
        cost_by_term=cost_by_term,
        carrier_mix=carrier_mix,
        dispatch=dispatch,
        build=build,
        disposal=disposal,
    )


def write_parquet(ledger: Ledger, report: RunReport, out_dir: Path) -> tuple[Path, ...]:
    """Write the ledger and the run report under ``out_dir``, returning the paths written.

    One directory per premise, so two premises written to the same root do not overwrite
    each other. Seven files: the five ledger tables, ``run_report.parquet`` — one row, the
    G1 (single-premise wall clock) measurement and the solver status — and
    ``screen_dropped.parquet``, the §3.2 screen's work list, which is the table note 20
    records. The screen's list is written even when it is empty, because "nothing was
    dropped" is a finding too and an absent file cannot say it.

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
                "n_variables": report.n_variables,
                "n_constraints": report.n_constraints,
                "wall_clock_seconds": report.wall_clock_seconds,
                "n_units_admitted": len(report.screen.admitted),
                "n_units_dropped": len({drop.unit_id for drop in report.screen.dropped}),
            }
        ]
    ).to_parquet(report_path, index=False)
    written.append(report_path)

    dropped_path = directory / "screen_dropped.parquet"
    pd.DataFrame(
        [
            {"unit_id": drop.unit_id, "leg": drop.leg, "detail": drop.detail}
            for drop in report.screen.dropped
        ],
        columns=["unit_id", "leg", "detail"],
    ).to_parquet(dropped_path, index=False)
    written.append(dropped_path)

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

    A supply column carries ``kind`` ``supply`` and no process: it is a unit producing a
    carrier that carries no duty row, settled by C8 (carrier balance) rather than by C1
    (duty satisfaction). Two families sit here — the cement kilns making ``clinker``, an
    internal product, and ``ccs_amine`` making ``co2_captured``, an exportable one.
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


def _carrier_mix_table(
    coefficients: dict[str, dict[str, np.ndarray]],
    carrier_facts,
    activity: dict[str, np.ndarray],
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

    carriers = sorted(set(coefficients) | set(m) | set(d) | set(x) | set(dispatched))
    records = []
    for carrier_id in carriers:
        produced = np.zeros(len(periods))
        consumed = np.zeros(len(periods))
        for unit_id, weights in coefficients.get(carrier_id, {}).items():
            flow = np.asarray(weights, dtype=float) * activity.get(
                unit_id, np.zeros(len(periods))
            )
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
    activity: dict[str, np.ndarray],
    tariff_override: float | None = None,
) -> pd.DataFrame:
    """Z^capex, Z^opex, Z^fuel, Z^carbon and Z^exp by period, undiscounted and discounted.

    The discounted column sums to the objective the solver reported, which is the §5.3 path
    "objective decomposition — terms sum to the reported objective". Nothing here is a
    restatement of the objective expression: it reads the solved variables and the same
    ``scenario_parameters`` and ``unit.csv`` values the build read, so the two agreeing is
    evidence that the objective was assembled from the parameters it claims.

    §5.4's biogenic credit **is** live now and nets off the carbon term. It was
    structurally zero while no abatement unit could take an activity column, and a ledger
    that ignored it still balanced; once ``ccs_amine`` reached the dispatch dimension the
    decomposition stopped summing to the reported objective by exactly the credit. Both
    sides now read :func:`carb3.build.biogenic_capture_weights`.
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
    for unit_id, weight in biogenic_capture_weights(
        reference, model_units, parameters, carrier_facts
    ).items():
        carbon -= (
            activity.get(unit_id, np.zeros(n_periods))
            * weight
            * CARBON_UNIT_CONVERSION
            * carbon_price
        )

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
