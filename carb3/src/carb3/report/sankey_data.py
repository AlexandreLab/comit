"""Parquet ledger directory -> the one JSON document the site report draws.

A pure function of the parquet files :func:`carb3.ledger.write_parquet` writes. It imports
nothing from ``build``, ``sets`` or ``load``, reads no CSV, and recomputes no flow: every
edge is a ledger row, aggregated.

**Three layers, one unit each.** A carrier's layer comes from its ``carrier_kind`` as the
ledger recorded it, never from its name: ``emission`` is the CO₂ layer (kt/yr), ``product``
the Materials layer (Mt/yr), and ``primary`` and ``intermediate`` the Energy layer (PJ/yr).
A unit appears in every layer it has a flow in. A layer with no flow at a premise is left
out.

**Edges, and where each is read from.**

============================  ==============================================================
``Imports -> carrier``        ``carrier_mix.imported``
``carrier -> unit``           ``unit_flow``, net per unit and carrier, where negative
``unit -> carrier``           ``unit_flow``, net per unit and carrier, where positive
``carrier -> process``        ``dispatch`` rows of ``kind`` ``duty``
``carrier -> Export``         ``carrier_mix.exported``
``carrier -> Disposal``       ``disposal.quantity``
``unit -> Losses``            Energy layer only: a unit's energy in less its energy out
``Ambient heat -> unit``      Energy layer only: the same difference where it is negative
============================  ==============================================================

``unit_flow`` is netted over roles per ``(unit, carrier, period)`` before it becomes an
edge, as ``carrier_mix`` does. Without the netting the capture train, which draws
``co2_fuel_fossil`` and makes some by burning gas, would be a two-edge cycle, and d3-sankey
cannot draw a cycle. The report's tooltip carries the gross roles.

**The Energy-layer residual is split by what the unit makes.** A unit with an output in
another layer — the kiln's clinker, the grinder's cement — sends its residual to
``Used in processing``: that energy went into the product, not up the stack. Any
other unit sends it to ``Losses``. A heat pump or a chiller delivers more than it draws, so
its residual is negative and appears as ``Ambient heat`` flowing in.

Any flow smaller than :data:`EPSILON` in magnitude is dropped, so solver noise of 1e-13
does not become a hair-thin ribbon or a negative link.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

#: The ledger tables the report reads, and the run report beside them.
REQUIRED_TABLES: tuple[str, ...] = (
    "carrier_mix",
    "dispatch",
    "build",
    "disposal",
    "cost_by_term",
    "unit_flow",
    "run_report",
)

#: Flows below this magnitude are solver noise, not a ribbon.
EPSILON: float = 1e-9


@dataclass(frozen=True)
class Layer:
    id: str
    label: str
    unit: str
    kinds: frozenset[str]


#: The three layers, in the order the report's tabs show them.
LAYERS: tuple[Layer, ...] = (
    Layer("energy", "Energy", "PJ/yr", frozenset({"primary", "intermediate"})),
    Layer("co2", "CO₂", "kt/yr", frozenset({"emission"})),
    Layer("materials", "Materials", "Mt/yr", frozenset({"product"})),
)

#: A unit's capacity is in its output's unit: Mt/yr for a unit making a product, else PJ/yr.
CAPACITY_BASIS: dict[str, str] = {"product": "Mt/yr"}
DEFAULT_CAPACITY_BASIS: str = "PJ/yr"

IMPORTS = "boundary:imports"
EXPORT = "boundary:export"
DISPOSAL = "boundary:disposal"
LOSSES = "boundary:losses"
PROCESS_USE = "boundary:process_use"
AMBIENT = "boundary:ambient"

_BOUNDARY_LABELS: dict[str, str] = {
    IMPORTS: "Imports",
    EXPORT: "Export",
    DISPOSAL: "Disposal",
    LOSSES: "Losses",
    PROCESS_USE: "Used in processing",
    AMBIENT: "Ambient heat",
}


class ReportDataError(ValueError):
    """The parquet directory cannot be drawn: a table is missing or the solve was not optimal."""


def read_ledger(directory: Path) -> dict[str, pd.DataFrame]:
    """The seven tables the report needs, by name. Raises naming any that is missing."""
    directory = Path(directory)
    missing = [
        name for name in REQUIRED_TABLES if not (directory / f"{name}.parquet").is_file()
    ]
    if missing:
        raise ReportDataError(
            f"{directory} is missing {', '.join(f'{name}.parquet' for name in missing)}; "
            "re-run `python -m carb3 --out-dir …` to write the ledger the report reads"
        )
    return {name: pd.read_parquet(directory / f"{name}.parquet") for name in REQUIRED_TABLES}


def build_report_data(directory: Path) -> dict[str, Any]:
    """Parquet ledger directory -> the report's JSON document, as plain Python objects."""
    tables = read_ledger(directory)
    run_report = tables["run_report"].iloc[0]
    status = str(run_report["status"])
    if status != "optimal":
        raise ReportDataError(
            f"{directory}: the solve terminated {status!r}; there is no pathway to draw"
        )

    periods = sorted(int(year) for year in tables["cost_by_term"]["period"].unique())
    kind_of = _carrier_kinds(tables)
    net = _net_unit_flow(tables["unit_flow"])

    layers = []
    for layer in LAYERS:
        drawn = _layer(layer, tables, kind_of, net, periods)
        if drawn is not None:
            layers.append(drawn)

    objective = run_report.get("objective")
    return {
        "premise_id": str(run_report["premise_id"]),
        "status": status,
        "objective": None if pd.isna(objective) else float(objective),
        "periods": periods,
        "layers": layers,
        "units": _unit_facts(tables, kind_of, periods),
        "gross": _gross_flows(tables["unit_flow"], periods),
        "evolution": _evolution(tables, kind_of, periods, objective),
    }


# --------------------------------------------------------------------------------------
# The Sankey layers
# --------------------------------------------------------------------------------------


def _carrier_kinds(tables: dict[str, pd.DataFrame]) -> dict[str, str]:
    kinds: dict[str, str] = {}
    for frame in (tables["carrier_mix"], tables["unit_flow"]):
        for carrier_id, kind in zip(frame["carrier_id"], frame["carrier_kind"], strict=True):
            if kind:
                kinds[str(carrier_id)] = str(kind)
    return kinds


def _net_unit_flow(unit_flow: pd.DataFrame) -> pd.DataFrame:
    """``unit_flow`` summed over roles: one signed flow per (unit, carrier, period)."""
    if unit_flow.empty:
        return pd.DataFrame(columns=["unit_id", "carrier_id", "period", "flow"])
    return unit_flow.groupby(["unit_id", "carrier_id", "period"], as_index=False)["flow"].sum()


def _layer(
    layer: Layer,
    tables: dict[str, pd.DataFrame],
    kind_of: dict[str, str],
    net: pd.DataFrame,
    periods: list[int],
) -> dict[str, Any] | None:
    """One layer's nodes (fixed across periods) and its links per period."""
    in_layer = {carrier for carrier, kind in kind_of.items() if kind in layer.kinds}
    links: dict[int, dict[tuple[str, str], float]] = {
        year: defaultdict(float) for year in periods
    }

    def add(year: int, source: str, target: str, value: float) -> None:
        if value > EPSILON:
            links[int(year)][(source, target)] += float(value)

    mix = tables["carrier_mix"]
    mix = mix[mix["carrier_id"].isin(in_layer)]
    for row in mix.itertuples(index=False):
        carrier = f"carrier:{row.carrier_id}"
        add(row.period, IMPORTS, carrier, row.imported)
        add(row.period, carrier, EXPORT, row.exported)

    disposal = tables["disposal"]
    disposal = disposal[disposal["carrier_id"].isin(in_layer)]
    for row in disposal.itertuples(index=False):
        add(row.period, f"carrier:{row.carrier_id}", DISPOSAL, row.quantity)

    flows = net[net["carrier_id"].isin(in_layer)]
    for row in flows.itertuples(index=False):
        carrier, unit = f"carrier:{row.carrier_id}", f"unit:{row.unit_id}"
        if row.flow > 0:
            add(row.period, unit, carrier, row.flow)
        else:
            add(row.period, carrier, unit, -row.flow)

    dispatch = tables["dispatch"]
    duties = dispatch[(dispatch["kind"] == "duty") & dispatch["carrier_id"].isin(in_layer)]
    for row in duties.itertuples(index=False):
        add(row.period, f"carrier:{row.carrier_id}", f"process:{row.process_id}", row.activity)

    if layer.id == "energy":
        _energy_residuals(net, kind_of, layer, add)

    used = {node for year in periods for pair in links[year] for node in pair}
    if not used:
        return None
    nodes = sorted(used, key=_node_order)
    index = {node: position for position, node in enumerate(nodes)}
    return {
        "id": layer.id,
        "label": layer.label,
        "unit": layer.unit,
        "nodes": [
            {"id": node, "kind": node.split(":", 1)[0], "label": _node_label(node)}
            for node in nodes
        ],
        "links": {
            str(year): [
                {"source": index[source], "target": index[target], "value": value}
                for (source, target), value in sorted(links[year].items())
                if value > EPSILON
            ]
            for year in periods
        },
    }


def _energy_residuals(net: pd.DataFrame, kind_of: dict[str, str], layer: Layer, add) -> None:
    """Energy in less energy out, per unit and period, as Losses, process use or ambient heat."""
    if net.empty:
        return
    frame = net.assign(kind=net["carrier_id"].map(kind_of).fillna(""))
    makes_other_layer = set(
        frame.loc[(frame["flow"] > EPSILON) & ~frame["kind"].isin(layer.kinds), "unit_id"]
    )
    energy = frame[frame["kind"].isin(layer.kinds)]
    for (unit_id, period), flow in energy.groupby(["unit_id", "period"])["flow"].sum().items():
        residual = -float(flow)  # in minus out
        unit = f"unit:{unit_id}"
        if residual > 0:
            add(period, unit, PROCESS_USE if unit_id in makes_other_layer else LOSSES, residual)
        else:
            add(period, AMBIENT, unit, -residual)


_KIND_ORDER = {"boundary": 0, "carrier": 1, "unit": 2, "process": 3}


def _node_order(node: str) -> tuple[int, str]:
    kind = node.split(":", 1)[0]
    return (_KIND_ORDER.get(kind, 9), node)


def _node_label(node: str) -> str:
    if node in _BOUNDARY_LABELS:
        return _BOUNDARY_LABELS[node]
    return node.split(":", 1)[1]


# --------------------------------------------------------------------------------------
# Tooltip facts
# --------------------------------------------------------------------------------------


def _unit_facts(
    tables: dict[str, pd.DataFrame], kind_of: dict[str, str], periods: list[int]
) -> dict[str, Any]:
    """Per unit: capacity basis, available capacity and activity by period."""
    dispatch = tables["dispatch"]
    build = tables["build"]
    facts: dict[str, Any] = {}
    for unit_id in sorted(set(build["unit_id"]) | set(dispatch["unit_id"])):
        rows = dispatch[dispatch["unit_id"] == unit_id]
        kinds = {kind_of.get(str(carrier), "") for carrier in rows["carrier_id"]}
        basis = next(
            (CAPACITY_BASIS[kind] for kind in sorted(kinds) if kind in CAPACITY_BASIS),
            DEFAULT_CAPACITY_BASIS,
        )
        activity = rows.groupby("period")["activity"].sum()
        capacity = build[build["unit_id"] == unit_id].set_index("period")
        facts[unit_id] = {
            "basis": basis,
            "activity": [float(activity.get(year, 0.0)) for year in periods],
            "available_capacity": [
                float(capacity["available_capacity"].get(year, 0.0)) for year in periods
            ],
            "new_capacity": [
                float(capacity["new_capacity"].get(year, 0.0)) for year in periods
            ],
        }
    return facts


def _gross_flows(unit_flow: pd.DataFrame, periods: list[int]) -> dict[str, Any]:
    """The roles behind each netted (unit, carrier) edge, for the tooltip."""
    gross: dict[str, dict[str, dict[str, list[float]]]] = {}
    if unit_flow.empty:
        return gross
    for (unit_id, carrier_id, role), group in unit_flow.groupby(
        ["unit_id", "carrier_id", "role"], sort=True
    ):
        by_period = group.set_index("period")["flow"]
        gross.setdefault(str(unit_id), {}).setdefault(str(carrier_id), {})[str(role)] = [
            float(by_period.get(year, 0.0)) for year in periods
        ]
    return gross


# --------------------------------------------------------------------------------------
# The evolution panel
# --------------------------------------------------------------------------------------


def _evolution(
    tables: dict[str, pd.DataFrame],
    kind_of: dict[str, str],
    periods: list[int],
    objective: object,
) -> dict[str, Any]:
    return {
        "imports": _imports_series(tables["carrier_mix"], periods),
        "capacity": _capacity_series(tables, kind_of, periods),
        "cost": _cost_series(tables["cost_by_term"], periods, objective),
        "co2": _co2_series(tables, kind_of, periods),
    }


def _series(frame: pd.DataFrame, key: str, value: str, periods: list[int]) -> list[dict]:
    out = []
    for name, group in frame.groupby(key, sort=True):
        by_period = group.groupby("period")[value].sum()
        values = [float(by_period.get(year, 0.0)) for year in periods]
        if any(abs(v) > EPSILON for v in values):
            out.append({"key": str(name), "values": values})
    return out


def _imports_series(mix: pd.DataFrame, periods: list[int]) -> dict[str, Any]:
    """Imports by carrier. Every importable carrier is ``primary``, so one unit holds."""
    energy = mix[mix["carrier_kind"].isin(LAYERS[0].kinds)]
    return {"unit": LAYERS[0].unit, "series": _series(energy, "carrier_id", "imported", periods)}


def _capacity_series(
    tables: dict[str, pd.DataFrame], kind_of: dict[str, str], periods: list[int]
) -> list[dict[str, Any]]:
    """Available capacity by unit, one group per capacity basis — PJ/yr and Mt/yr do not stack."""
    facts = _unit_facts(tables, kind_of, periods)
    groups: dict[str, list[dict]] = defaultdict(list)
    for unit_id, fact in facts.items():
        values = fact["available_capacity"]
        if any(abs(v) > EPSILON for v in values):
            groups[fact["basis"]].append({"key": unit_id, "values": values})
    order = [DEFAULT_CAPACITY_BASIS, *sorted(set(CAPACITY_BASIS.values()))]
    return [{"unit": basis, "series": groups[basis]} for basis in order if groups.get(basis)]


def _cost_series(
    cost: pd.DataFrame, periods: list[int], objective: object
) -> dict[str, Any]:
    """Cost by term, annual and discounted. The total is compared with the objective, not trusted."""
    terms = list(dict.fromkeys(str(term) for term in cost["term"]))
    table: dict[str, dict[str, list[float]]] = {"annual": {}, "discounted": {}}
    for column in table:
        pivot = cost.pivot_table(index="term", columns="period", values=column, aggfunc="sum")
        for term in terms:
            table[column][term] = [
                float(pivot.at[term, year]) if year in pivot.columns else 0.0
                for year in periods
            ]
    total = float(cost["discounted"].sum())
    reported = None if objective is None or pd.isna(objective) else float(objective)
    return {
        "unit": "£m",
        "terms": terms,
        "annual": table["annual"],
        "discounted": table["discounted"],
        "total_discounted": total,
        "objective": reported,
        "residual": None if reported is None else total - reported,
    }


def _co2_series(
    tables: dict[str, pd.DataFrame], kind_of: dict[str, str], periods: list[int]
) -> dict[str, Any]:
    """CO₂ vented, by carrier, against CO₂ drawn by capture units, both kt/yr.

    Captured is read as the ``emission_input`` draw in ``unit_flow``, which is already in kt.
    The exported stream, ``co2_captured``, is a Mt ``product``; reading the draw avoids
    converting it, and avoids naming the carrier.
    """
    disposal = tables["disposal"]
    vented = disposal[disposal["carrier_id"].map(kind_of) == "emission"]
    flow = tables["unit_flow"]
    drawn = flow[(flow["role"] == "emission_input") & (flow["carrier_kind"] == "emission")]
    drawn = drawn.assign(captured=-drawn["flow"])
    captured = _series(drawn.assign(key="captured"), "key", "captured", periods)
    return {
        "unit": "kt/yr",
        "vented": _series(vented, "carrier_id", "quantity", periods),
        "captured": captured[0]["values"] if captured else [0.0 for _ in periods],
    }
