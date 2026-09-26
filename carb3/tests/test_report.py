"""The site report: parquet ledger -> JSON document -> one offline HTML page.

The premises are solved once, through ``python -m carb3 --out-dir``, so these tests also
cover the CLI wiring: every solved premise leaves a ``site_report.html`` beside its parquet.
What is checked is that the document is drawable (non-negative, finite, acyclic, balanced at
every carrier node), that it says what the ledger says, and that the page reaches for
nothing on the network.
"""

from __future__ import annotations

import ast
import json
import math
from pathlib import Path

import pandas as pd
import pytest

from carb3.__main__ import main as run_carb3
from carb3.report import __main__ as report_cli
from carb3.report import render, sankey_data
from carb3.report.sankey_data import ReportDataError, build_report_data

PREMISES: tuple[str, ...] = ("mvp-minimal", "mvp-dairy", "mvp-cement")

#: Plan Task 2's tolerance. It holds, at about 1e-15 on all three premises, because the
#: ledger computes ``net`` from the same arrays the edges are built from.
BALANCE_TOLERANCE = 1e-9


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("carb3-out")
    assert run_carb3(["--out-dir", str(root)]) == 0
    return root


@pytest.fixture(scope="module")
def documents(out_dir: Path) -> dict[str, dict]:
    return {premise_id: build_report_data(out_dir / premise_id) for premise_id in PREMISES}


def _links(layer: dict, year: int) -> list[tuple[str, str, float]]:
    ids = [node["id"] for node in layer["nodes"]]
    return [(ids[l["source"]], ids[l["target"]], l["value"]) for l in layer["links"][str(year)]]


def _layer(document: dict, layer_id: str) -> dict:
    return next(layer for layer in document["layers"] if layer["id"] == layer_id)


# --------------------------------------------------------------------------------------
# The CLI writes a page per solved premise
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("premise_id", PREMISES)
def test_the_run_writes_a_site_report_beside_the_parquet(out_dir: Path, premise_id: str) -> None:
    page = out_dir / premise_id / render.REPORT_FILENAME
    assert page.is_file()
    assert (out_dir / premise_id / "unit_flow.parquet").is_file()


def test_no_report_skips_the_page(tmp_path: Path) -> None:
    assert run_carb3(["mvp-minimal", "--out-dir", str(tmp_path), "--no-report"]) == 0
    assert (tmp_path / "mvp-minimal" / "carrier_mix.parquet").is_file()
    assert not (tmp_path / "mvp-minimal" / render.REPORT_FILENAME).exists()


def test_the_report_cli_rebuilds_from_parquet_alone(out_dir: Path, tmp_path: Path) -> None:
    """Copy the parquet somewhere with no page and no model, and rebuild it there."""
    target = tmp_path / "mvp-dairy"
    target.mkdir()
    for path in (out_dir / "mvp-dairy").glob("*.parquet"):
        (target / path.name).write_bytes(path.read_bytes())
    assert report_cli.main([str(tmp_path)]) == 0
    assert (target / render.REPORT_FILENAME).is_file()


def test_a_non_optimal_ledger_draws_nothing(out_dir: Path, tmp_path: Path) -> None:
    target = tmp_path / "fx-blocked"
    target.mkdir()
    for path in (out_dir / "mvp-minimal").glob("*.parquet"):
        (target / path.name).write_bytes(path.read_bytes())
    report = pd.read_parquet(target / "run_report.parquet")
    report["status"] = "infeasible"
    report.to_parquet(target / "run_report.parquet", index=False)
    with pytest.raises(ReportDataError, match="infeasible"):
        build_report_data(target)
    assert report_cli.main([str(target)]) == 1
    assert not (target / render.REPORT_FILENAME).exists()


def test_a_missing_table_is_named(tmp_path: Path) -> None:
    (tmp_path / "run_report.parquet").write_bytes(b"")
    with pytest.raises(ReportDataError, match="unit_flow.parquet"):
        build_report_data(tmp_path)


# --------------------------------------------------------------------------------------
# The document is drawable
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("premise_id", PREMISES)
def test_every_link_is_finite_and_non_negative_in_every_period(
    documents: dict[str, dict], premise_id: str
) -> None:
    document = documents[premise_id]
    json.dumps(document, allow_nan=False)  # raises on NaN or infinity anywhere
    assert document["layers"], "a solved premise has at least one layer"
    for layer in document["layers"]:
        assert set(layer["links"]) == {str(year) for year in document["periods"]}
        for year in document["periods"]:
            for source, target, value in _links(layer, year):
                assert math.isfinite(value) and value > 0.0, (layer["id"], year, source, target)


@pytest.mark.parametrize("premise_id", PREMISES)
def test_every_layer_is_acyclic(documents: dict[str, dict], premise_id: str) -> None:
    """d3-sankey cannot draw a cycle. The union over periods is what it lays out."""
    for layer in documents[premise_id]["layers"]:
        edges: dict[str, set[str]] = {}
        for year in documents[premise_id]["periods"]:
            for source, target, _value in _links(layer, year):
                edges.setdefault(source, set()).add(target)
        loop = _find_cycle(edges)
        assert loop is None, f"{premise_id} {layer['id']} layer has a loop: {' -> '.join(loop)}"


def _find_cycle(edges: dict[str, set[str]]) -> list[str] | None:
    state: dict[str, int] = {}
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        path.append(node)
        for nxt in sorted(edges.get(node, ())):
            if state.get(nxt) == 1:
                return path[path.index(nxt):] + [nxt]
            if nxt not in state:
                found = visit(nxt)
                if found:
                    return found
        path.pop()
        state[node] = 2
        return None

    for node in sorted(edges):
        if node not in state:
            found = visit(node)
            if found:
                return found
    return None


@pytest.mark.parametrize("premise_id", PREMISES)
def test_every_carrier_and_energy_unit_node_balances(
    documents: dict[str, dict], premise_id: str
) -> None:
    """Inflow equals outflow at every carrier node, and at every unit in the Energy layer.

    A carrier balances because C8 (carrier balance) or C1 (duty satisfaction) closed it; an
    Energy-layer unit balances because Losses, process use and ambient heat are its
    residual by construction. A gap at either is an edge the builder dropped.
    """
    for layer in documents[premise_id]["layers"]:
        for year in documents[premise_id]["periods"]:
            inflow: dict[str, float] = {}
            outflow: dict[str, float] = {}
            for source, target, value in _links(layer, year):
                outflow[source] = outflow.get(source, 0.0) + value
                inflow[target] = inflow.get(target, 0.0) + value
            balanced = [n["id"] for n in layer["nodes"] if n["kind"] == "carrier"]
            if layer["id"] == "energy":
                balanced += [n["id"] for n in layer["nodes"] if n["kind"] == "unit"]
            for node in balanced:
                gap = inflow.get(node, 0.0) - outflow.get(node, 0.0)
                assert abs(gap) < BALANCE_TOLERANCE, (layer["id"], year, node, gap)


# --------------------------------------------------------------------------------------
# The document says what the ledger says
# --------------------------------------------------------------------------------------


def test_layers_follow_carrier_kind(documents: dict[str, dict]) -> None:
    cement = documents["mvp-cement"]
    assert [layer["id"] for layer in cement["layers"]] == ["energy", "co2", "materials"]
    carriers = {
        layer["id"]: {n["label"] for n in layer["nodes"] if n["kind"] == "carrier"}
        for layer in cement["layers"]
    }
    assert {"clinker", "cement", "co2_captured"} <= carriers["materials"]
    assert {"co2_process", "co2_fuel_fossil"} <= carriers["co2"]
    assert {"natural_gas", "electricity", "heat_lt60"} <= carriers["energy"]
    # The dairy makes no product, so it has no Materials tab.
    assert "materials" not in [layer["id"] for layer in documents["mvp-dairy"]["layers"]]


def test_the_cement_kiln_switch_and_the_capture_train_are_visible(
    documents: dict[str, dict],
) -> None:
    """The two changes plan Task 3 asks to be seen: coal to gas by 2025, capture from 2035."""
    cement = documents["mvp-cement"]
    energy, co2 = _layer(cement, "energy"), _layer(cement, "co2")
    coal_2021 = [l for l in _links(energy, 2021) if l[:2] == ("carrier:coal", "unit:kiln_dry_coal")]
    assert coal_2021 and coal_2021[0][2] > 1.0
    assert not [l for l in _links(energy, 2025) if l[1] == "unit:kiln_dry_coal"]

    def captured(year: int) -> float:
        return sum(v for _s, t, v in _links(co2, year) if t == "unit:ccs_amine")

    assert captured(2030) == 0.0
    assert captured(2035) > 10.0
    assert _layer(cement, "energy")["links"]["2035"]  # the train draws gas and power too
    assert any(t == "unit:ccs_amine" for _s, t, _v in _links(energy, 2035))


def test_a_heat_pump_draws_ambient_heat(documents: dict[str, dict]) -> None:
    energy = _layer(documents["mvp-dairy"], "energy")
    ambient = {t: v for s, t, v in _links(energy, 2025) if s == sankey_data.AMBIENT}
    # The dairy's grade-2 duties go to ``heat_pump_lt_reject`` on the chillers' and dryers'
    # reject heat since ``dryer_steam`` was rebased (note 20 item 64, 2026-09-26), so the
    # ambient-source heat pump that runs in 2025 is the drying one.
    assert ambient.get("unit:dryer_heat_pump", 0.0) > 0.0
    assert ambient.get("unit:chiller_electric", 0.0) > 0.0


def test_the_imports_series_is_the_carrier_mix(out_dir: Path, documents: dict[str, dict]) -> None:
    mix = pd.read_parquet(out_dir / "mvp-cement" / "carrier_mix.parquet")
    series = {s["key"]: s["values"] for s in documents["mvp-cement"]["evolution"]["imports"]["series"]}
    periods = documents["mvp-cement"]["periods"]
    for carrier_id, values in series.items():
        expected = mix[mix["carrier_id"] == carrier_id].set_index("period")["imported"]
        assert values == pytest.approx([expected[year] for year in periods])


@pytest.mark.parametrize("premise_id", PREMISES)
def test_the_cost_terms_sum_to_the_reported_objective(
    documents: dict[str, dict], premise_id: str
) -> None:
    cost = documents[premise_id]["evolution"]["cost"]
    assert cost["objective"] == pytest.approx(documents[premise_id]["objective"])
    total = sum(sum(values) for values in cost["discounted"].values())
    assert total == pytest.approx(cost["objective"], rel=1e-9)
    assert abs(cost["residual"]) < 1e-6


def test_the_dairy_boiler_retires_and_is_rebuilt_in_2045(documents: dict[str, dict]) -> None:
    """Plan Task 4's check: ``build.parquet`` says 0.072 PJ/yr is rebuilt in 2045."""
    dairy = documents["mvp-dairy"]
    boiler = dairy["units"]["boiler_lt_gas"]
    index = dairy["periods"].index(2045)
    assert boiler["new_capacity"][index] == pytest.approx(0.07209, abs=1e-5)
    assert boiler["basis"] == "PJ/yr"
    capacity = {g["unit"]: g for g in dairy["evolution"]["capacity"]}
    assert "boiler_lt_gas" in {s["key"] for s in capacity["PJ/yr"]["series"]}


def test_capacity_is_grouped_by_basis(documents: dict[str, dict]) -> None:
    """A kiln's Mt/yr and a motor's PJ/yr are not on one axis."""
    capacity = {g["unit"]: {s["key"] for s in g["series"]} for g in documents["mvp-cement"]["evolution"]["capacity"]}
    assert "motor_elec" in capacity["PJ/yr"]
    assert {"kiln_dry_gas", "grinder_mixer_elec", "ccs_amine"} <= capacity["Mt/yr"]


def test_captured_co2_is_the_exported_stream(out_dir: Path, documents: dict[str, dict]) -> None:
    """The kt drawn by capture equals the Mt exported, times 1000, at the cement works."""
    captured = documents["mvp-cement"]["evolution"]["co2"]["captured"]
    mix = pd.read_parquet(out_dir / "mvp-cement" / "carrier_mix.parquet")
    exported = mix[mix["carrier_id"] == "co2_captured"].set_index("period")["exported"]
    periods = documents["mvp-cement"]["periods"]
    assert captured == pytest.approx([exported[year] * 1000 for year in periods], abs=1e-6)


# --------------------------------------------------------------------------------------
# The page
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("premise_id", PREMISES)
def test_the_page_is_self_contained(out_dir: Path, premise_id: str) -> None:
    page = (out_dir / premise_id / render.REPORT_FILENAME).read_text(encoding="utf-8")
    assert "<link" not in page
    assert " src=" not in page
    assert "fetch(" not in page
    assert "/*__" not in page, "a template slot was left unfilled"
    assert premise_id in page


def test_render_refuses_a_template_that_reaches_the_network() -> None:
    template = render.TEMPLATE_PATH.read_text(encoding="utf-8").replace(
        "<head>", '<head><script src="https://cdn.example/d3.js"></script>'
    )
    with pytest.raises(ValueError, match="network"):
        render.render({"premise_id": "x"}, template)


def test_data_cannot_close_the_script_element() -> None:
    page = render.render({"premise_id": "fx", "note": "</script><b>"})
    assert "</script><b>" not in page
    assert "<\\/script><b>" in page


def test_the_report_package_imports_no_model_code() -> None:
    """It reads the ledger's parquet; it is not a sixth module and must not grow into one."""
    package = Path(render.__file__).parent
    forbidden = {"carb3.build", "carb3.sets", "carb3.load", "carb3.survival", "carb3.ledger"}
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module not in forbidden, f"{path.name} imports {node.module}"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden, f"{path.name} imports {alias.name}"
