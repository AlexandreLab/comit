"""C14 (a capture train treats its hosts' flue gas) and V37 (a capture rate is a fraction of
its hosts' streams), on a fixture small enough to check by hand.

Two kilns serve one heat duty: ``kiln_gas`` burns natural gas, whose 1.15% biogenic fraction
gives it a small ``co2_fuel_biogenic`` stream, and ``kiln_coal`` burns coal, which has none.
Both declare process CO₂. ``ccs`` is an ``abatement`` unit hosted on both, with a rate of 0.90
on each of the three CO₂ carriers (note 24, Decisions 2 and 3), a fired reboiler and an
auxiliary electricity draw. A capture train's ``emission_input`` row is a **fraction** of its
hosts' streams, not kt per Mt of ``co2_captured``: that is the whole change these tests pin.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
import pytest

from carb3 import build, ledger, survival
from carb3.load import ReferenceTables
from carb3.sets import Duty, ExportWindow, ModelSets, released_supply

PERIODS: tuple[int, ...] = (2021, 2025, 2030)
DISCOUNT_RATE = 0.035
DUTY_KEY = ("fx-cement", "kiln", "heat_60_100")

RATE = 0.90
PROCESS_CO2 = 50.0  # kt per PJ of kiln output, declared
EF_GAS = 51.12
EF_COAL = 94.0
GAS_BIOGENIC = 0.0115
REBOILER_GAS = 1.9  # PJ per Mt captured
TOLERANCE = 1e-6


class _Duty(Duty):
    @property
    def key(self) -> tuple[str, str, str]:
        return (self.premise_id, self.process_id, self.carrier_id)


def _carrier(carrier_id, kind, *, biogenic="", charge="", dispose="FALSE", imports="FALSE"):
    return {
        "carrier_id": carrier_id,
        "carrier_kind": kind,
        "is_indirect": "TRUE" if carrier_id == "electricity" else "FALSE",
        "biogenic_fraction": biogenic,
        "carbon_charge": charge,
        "may_dispose": dispose,
        "may_import": imports,
    }


def _unit(unit_id, unit_class, capex, opex, lifetime=25):
    return {
        "unit_id": unit_id,
        "unit_class": unit_class,
        "capex": capex,
        "fixed_opex": opex,
        "lifetime": lifetime,
        "availability_factor": 1.0,
        "capacity_to_activity_factor": 1.0,
    }


def _io(unit_id, carrier_id, coefficient, role):
    return {"unit_id": unit_id, "carrier_id": carrier_id, "coefficient": coefficient, "role": role}


def _train_rows(unit_id: str, rate: float = RATE) -> list[dict]:
    return [
        _io(unit_id, "co2_captured", 1.0, "primary_output"),
        _io(unit_id, "natural_gas", -REBOILER_GAS, "fuel_input"),
        _io(unit_id, "electricity", -0.35, "aux_input"),
        _io(unit_id, "co2_process", -rate, "emission_input"),
        _io(unit_id, "co2_fuel_fossil", -rate, "emission_input"),
        _io(unit_id, "co2_fuel_biogenic", -rate, "emission_input"),
    ]


def _reference(*, second_train: bool = False, hosts: tuple[str, ...] = ("kiln_gas", "kiln_coal"),
               carbon_price: float = 300.0) -> ReferenceTables:
    carrier = pd.DataFrame(
        [
            _carrier("natural_gas", "primary", biogenic=GAS_BIOGENIC, imports="TRUE"),
            _carrier("coal", "primary", biogenic=0.0, imports="TRUE"),
            _carrier("electricity", "primary", imports="TRUE"),
            _carrier("heat_60_100", "intermediate", dispose="TRUE"),
            _carrier("co2_process", "emission", charge="charged", dispose="TRUE"),
            _carrier("co2_fuel_fossil", "emission", charge="charged", dispose="TRUE"),
            _carrier("co2_fuel_biogenic", "emission", charge="zero_rated", dispose="TRUE"),
            _carrier("co2_captured", "product"),
        ]
    )
    units = [
        _unit("kiln_gas", "converter", 5.0, 0.1),
        _unit("kiln_coal", "converter", 5.0, 0.1),
        _unit("ccs", "abatement", 50.0, 1.0, lifetime=30),
        # A co-fired kiln, one unit burning two fuels: gas as its fuel, coal as a second fuel.
        _unit("kiln_mix", "converter", 5.0, 0.1),
    ]
    io = [
        _io("kiln_gas", "heat_60_100", 1.0, "primary_output"),
        _io("kiln_gas", "natural_gas", -1.0, "fuel_input"),
        _io("kiln_gas", "co2_process", PROCESS_CO2, "emission"),
        _io("kiln_coal", "heat_60_100", 1.0, "primary_output"),
        _io("kiln_coal", "coal", -1.0, "fuel_input"),
        _io("kiln_coal", "co2_process", PROCESS_CO2, "emission"),
        _io("kiln_mix", "heat_60_100", 1.0, "primary_output"),
        _io("kiln_mix", "natural_gas", -0.6, "fuel_input"),
        _io("kiln_mix", "coal", -0.4, "aux_input"),
        _io("kiln_mix", "co2_process", PROCESS_CO2, "emission"),
        *_train_rows("ccs"),
    ]
    host_rows = [{"unit_id": "ccs", "host_unit_id": host} for host in hosts]
    if second_train:
        units.append(_unit("ccs_b", "abatement", 40.0, 1.0, lifetime=30))
        io += _train_rows("ccs_b")
        host_rows += [{"unit_id": "ccs_b", "host_unit_id": host} for host in hosts]
    scenario = [{"parameter_id": "discount_rate", "carrier_id": "", "period": "",
                 "value": DISCOUNT_RATE}]
    for year in PERIODS:
        scenario += [
            {"parameter_id": "import_price", "carrier_id": "natural_gas", "period": year,
             "value": 7.0},
            {"parameter_id": "import_price", "carrier_id": "coal", "period": year, "value": 3.0},
            {"parameter_id": "import_price", "carrier_id": "electricity", "period": year,
             "value": 30.0},
            {"parameter_id": "carbon_price", "carrier_id": "", "period": year,
             "value": carbon_price},
            {"parameter_id": "ef_natural_gas", "carrier_id": "natural_gas", "period": year,
             "value": EF_GAS},
            {"parameter_id": "ef_coal", "carrier_id": "coal", "period": year, "value": EF_COAL},
            {"parameter_id": "co2_transport_tariff", "carrier_id": "co2_captured",
             "period": year, "value": 40.0},
        ]
    return ReferenceTables(
        carrier=carrier,
        unit=pd.DataFrame(units),
        unit_input_output=pd.DataFrame(io),
        unit_eligibility=pd.DataFrame(),
        scenario_parameters=pd.DataFrame(scenario),
        activity_process_duty_profile=pd.DataFrame(),
        activity_process_register=pd.DataFrame(),
        infrastructure_scenario=pd.DataFrame(),
        unit_abatement_host=pd.DataFrame(host_rows),
    )


def _sets(reference: ReferenceTables, kilns: frozenset[str], trains: frozenset[str]) -> ModelSets:
    duty = _Duty(DUTY_KEY[0], DUTY_KEY[1], DUTY_KEY[2], 2, {year: 1.0 for year in PERIODS})
    sets = ModelSets(
        periods=PERIODS,
        duties=(duty,),
        units=kilns | trains,
        eligible={duty.key: kilns},
        earliest_year={},
        max_share={},
        min_duty={},
        supply={"co2_captured": trains} if trains else {},
        export_windows=(ExportWindow("co2_captured", PERIODS, "co2", None),),
    )
    return dataclasses.replace(sets, released=released_supply(reference, sets))


@dataclasses.dataclass(frozen=True)
class _Run:
    reference: ReferenceTables
    sets: ModelSets
    model: object
    result: build.SolveResult
    tables: ledger.Ledger


def _run(reference: ReferenceTables, kilns: frozenset[str], trains: frozenset[str],
         incumbent: str) -> _Run:
    sets = _sets(reference, kilns, trains)
    sets, _ = build.screen_premise(sets, reference, frozenset({incumbent}))
    surviving = survival.surviving_capacity(
        pd.DataFrame([{"unit_id": incumbent, "commissioned_year": 2015, "capacity": 2.0}]),
        reference.unit,
        PERIODS,
    )
    axis = build.period_axis(PERIODS, DISCOUNT_RATE)
    model = build.build_model(sets, surviving, axis, reference)
    result = build.solve(model)
    assert result.termination_condition == "optimal"
    tables = ledger.build_ledger(result, sets, axis, reference)
    return _Run(reference, sets, model, result, tables)


def _gas_run(**kwargs) -> _Run:
    trains = frozenset({"ccs", "ccs_b"}) if kwargs.get("second_train") else frozenset({"ccs"})
    return _run(_reference(**kwargs), frozenset({"kiln_gas"}), trains, "kiln_gas")


def _flow(run: _Run, unit_id: str, carrier_id: str, roles: set[str]) -> pd.Series:
    flow = run.tables.unit_flow
    rows = flow[
        (flow["unit_id"] == unit_id) & (flow["carrier_id"] == carrier_id) & flow["role"].isin(roles)
    ]
    return rows.groupby("period")["flow"].sum().reindex(list(PERIODS), fill_value=0.0)


GROSS = {"emission", build.A6_ROLE}
CO2 = ("co2_process", "co2_fuel_fossil", "co2_fuel_biogenic")


# --------------------------------------------------------------------------------------
# The rate is a fraction of each stream, not a share of a blend
# --------------------------------------------------------------------------------------


def test_a_train_takes_its_rate_of_every_stream_its_host_makes() -> None:
    """With capture paying, the train treats the whole kiln and takes 0.90 of each stream.

    Under the old blend reading the biogenic stream, 1.15% of the gas's CO₂, capped the
    train; here every stream is captured at the same fraction of what the host makes.
    """
    run = _gas_run()
    for carrier_id in CO2:
        made = _flow(run, "kiln_gas", carrier_id, GROSS)
        captured = -_flow(run, "ccs", carrier_id, {"emission_input"})
        assert (made.loc[[2025, 2030]] > 0.0).all()
        np.testing.assert_allclose(captured.loc[[2025, 2030]], RATE * made.loc[[2025, 2030]],
                                   rtol=1e-6)
        assert captured.loc[2021] == pytest.approx(0.0, abs=TOLERANCE), "C5: nothing built in 2021"


def test_the_train_activity_is_its_capture_in_mt() -> None:
    """z_{u,t} = 10⁻³ Σ_c Γ_{u,c,t}: the train's activity is Mt of ``co2_captured``."""
    run = _gas_run()
    captured = sum(-_flow(run, "ccs", c, {"emission_input"}) for c in CO2)
    made = _flow(run, "ccs", "co2_captured", {"primary_output"})
    np.testing.assert_allclose(made, 1e-3 * captured, rtol=1e-9, atol=1e-12)


def test_the_train_does_not_capture_its_own_reboiler() -> None:
    """Decision 4: a train is never its own host, so its reboiler stack vents."""
    run = _gas_run()
    own = _flow(run, "ccs", "co2_fuel_fossil", {build.A6_ROLE})
    assert own.loc[2030] > 0.0
    taken = -_flow(run, "ccs", "co2_fuel_fossil", {"emission_input"})
    hosts = _flow(run, "kiln_gas", "co2_fuel_fossil", GROSS)
    built = [2025, 2030]  # C5: nothing is built in the start year
    np.testing.assert_allclose(taken.loc[built], RATE * hosts.loc[built], rtol=1e-6)
    vented = run.tables.disposal.set_index(["carrier_id", "period"])["quantity"]
    assert vented[("co2_fuel_fossil", 2030)] == pytest.approx(
        (1 - RATE) * hosts.loc[2030] + own.loc[2030], rel=1e-6
    )


def test_a_coal_only_works_now_captures() -> None:
    """Coal has no biogenic fraction, so under the blend the train had no biogenic CO₂ to
    draw and :func:`carb3.build.screen_premise` dropped it. Now it treats the coal kiln and
    captures the two streams that kiln makes, and nothing biogenic."""
    reference = _reference()
    sets, drops = build.screen_premise(
        _sets(reference, frozenset({"kiln_coal"}), frozenset({"ccs"})),
        reference,
        frozenset({"kiln_coal"}),
    )
    assert drops == ()
    assert "ccs" in sets.units
    run = _run(reference, frozenset({"kiln_coal"}), frozenset({"ccs"}), "kiln_coal")
    for carrier_id in ("co2_process", "co2_fuel_fossil"):
        made = _flow(run, "kiln_coal", carrier_id, GROSS)
        captured = -_flow(run, "ccs", carrier_id, {"emission_input"})
        assert captured.loc[2030] == pytest.approx(RATE * made.loc[2030], rel=1e-6)
    assert -_flow(run, "ccs", "co2_fuel_biogenic", {"emission_input"}).max() == pytest.approx(
        0.0, abs=TOLERANCE
    )


def test_a_train_with_no_host_in_the_model_is_dropped() -> None:
    """``ccs`` is hosted on ``kiln_gas`` only; at a coal-only works it has nothing to treat."""
    reference = _reference(hosts=("kiln_gas",))
    sets, drops = build.screen_premise(
        _sets(reference, frozenset({"kiln_coal"}), frozenset({"ccs"})),
        reference,
        frozenset({"kiln_coal"}),
    )
    assert [drop.unit_id for drop in drops] == ["ccs"]
    assert drops[0].leg == build.NO_CAPTURE_HOST_LEG
    assert "kiln_gas" in drops[0].detail
    assert "ccs" not in sets.units


def test_an_unscreened_train_with_no_host_is_held_at_zero() -> None:
    """Built without the screen, a train with no host has nothing to capture and C14 holds
    its activity at zero rather than letting it make ``co2_captured`` from nothing."""
    reference = _reference(hosts=("kiln_gas",))
    sets = _sets(reference, frozenset({"kiln_coal"}), frozenset({"ccs"}))
    surviving = survival.surviving_capacity(
        pd.DataFrame([{"unit_id": "kiln_coal", "commissioned_year": 2015, "capacity": 2.0}]),
        reference.unit,
        PERIODS,
    )
    model = build.build_model(sets, surviving, build.period_axis(PERIODS, DISCOUNT_RATE),
                              reference)
    result = build.solve(model)
    assert result.termination_condition == "optimal"
    z = model.variables["z"].solution.to_pandas()
    assert z.loc["ccs@supply:co2_captured"].abs().max() < TOLERANCE


# --------------------------------------------------------------------------------------
# C14 across hosts and trains
# --------------------------------------------------------------------------------------


def test_two_trains_on_one_host_treat_at_most_its_activity() -> None:
    """Decision 7: one flue is treated once. Two trains on ``kiln_gas`` share its activity, so
    together they capture at most 0.90 of each stream, never 1.80 of it."""
    run = _gas_run(second_train=True)
    by_host = run.tables.capture_by_host
    treated = by_host.drop_duplicates(["unit_id", "host_unit_id", "period"])
    total = treated.groupby("period")["treated_activity"].sum().reindex(list(PERIODS))
    kiln = run.tables.dispatch
    kiln = kiln[kiln["unit_id"] == "kiln_gas"].groupby("period")["activity"].sum()
    assert (total <= kiln + TOLERANCE).all()
    for carrier_id in CO2:
        made = _flow(run, "kiln_gas", carrier_id, GROSS)
        captured = -(
            _flow(run, "ccs", carrier_id, {"emission_input"})
            + _flow(run, "ccs_b", carrier_id, {"emission_input"})
        )
        assert (captured <= RATE * made + TOLERANCE).all()
        assert captured.loc[2030] == pytest.approx(RATE * made.loc[2030], rel=1e-6)


def test_the_host_bound_is_one_row_per_host_and_period() -> None:
    run = _gas_run(second_train=True)
    assert run.model.constraints["C14_host"].shape == (1, len(PERIODS))
    assert run.model.variables["z_host"].shape == (2, len(PERIODS))


def test_c14_rows_hold_in_the_returned_solution() -> None:
    run = _gas_run(second_train=True)
    assert build.check_constraint_rows(run.model, run.result) == ()


def test_captured_streams_stand_in_the_hosts_proportions() -> None:
    """Within one host the mix is exact: Γ_c / (ν_c × host production of c) is the same
    share of the host's activity on every stream."""
    run = _gas_run()
    by_host = run.tables.capture_by_host
    rows = by_host[by_host["period"] == 2030].set_index("carrier_id")
    activity = run.tables.dispatch
    activity = activity[(activity["unit_id"] == "kiln_gas") & (activity["period"] == 2030)][
        "activity"
    ].sum()
    shares = []
    for carrier_id in CO2:
        made = _flow(run, "kiln_gas", carrier_id, GROSS).loc[2030]
        shares.append(rows.loc[carrier_id, "captured"] / (RATE * made / activity))
    np.testing.assert_allclose(shares, rows["treated_activity"].iloc[0], rtol=1e-6)


# --------------------------------------------------------------------------------------
# The ledger: per-host table, credit, the post-solve check
# --------------------------------------------------------------------------------------


def test_capture_by_host_sums_to_unit_flows_capture() -> None:
    run = _gas_run(second_train=True)
    by_host = run.tables.capture_by_host
    assert list(by_host.columns) == list(ledger.CAPTURE_BY_HOST_COLUMNS)
    summed = by_host.groupby(["unit_id", "carrier_id", "period"])["captured"].sum()
    flow = run.tables.unit_flow
    taken = -flow[flow["role"] == "emission_input"].set_index(
        ["unit_id", "carrier_id", "period"]
    )["flow"]
    joined = pd.concat([summed.rename("by_host"), taken.rename("flow")], axis=1).fillna(0.0)
    assert (joined["by_host"] - joined["flow"]).abs().max() < 1e-9


def test_the_credit_is_the_rate_times_the_treated_biogenic_co2() -> None:
    """§5.4's credit is 10⁻³ π_t Σ Γ on the zero-rated carriers, recomputed here from the
    host's own biogenic production rather than from any build function."""
    run = _gas_run()
    costs = run.tables.cost_by_term
    carbon = costs[costs["term"] == "carbon"].set_index("period")["annual"]
    charged = run.tables.disposal.groupby("period")["carbon_cost"].sum()
    biogenic = _flow(run, "kiln_gas", "co2_fuel_biogenic", GROSS)
    # The train treats the whole kiln once it can be built; C5 holds it at zero in 2021.
    credit = RATE * biogenic * 1e-3 * 300.0
    credit.loc[2021] = 0.0
    assert credit.loc[2030] > 0.0
    np.testing.assert_allclose(carbon, charged - credit, atol=1e-9)


def test_the_cost_terms_sum_to_the_objective() -> None:
    run = _gas_run(second_train=True)
    total = float(run.tables.cost_by_term["discounted"].sum())
    assert total == pytest.approx(run.result.objective, rel=1e-9)


def test_the_post_solve_capture_check_passes_on_a_solved_run() -> None:
    run = _gas_run(second_train=True)
    assert ledger.check_capture(run.tables, run.reference) == ()


def test_the_post_solve_capture_check_names_a_stream_over_its_rate() -> None:
    """V37 leg (c): no train captures more of a carrier than ν times its hosts' production."""
    run = _gas_run()
    flow = run.tables.unit_flow.copy()
    mask = (flow["unit_id"] == "ccs") & (flow["role"] == "emission_input") & (
        flow["carrier_id"] == "co2_process"
    )
    flow.loc[mask, "flow"] *= 1.5
    by_host = run.tables.capture_by_host.copy()
    by_host.loc[by_host["carrier_id"] == "co2_process", "captured"] *= 1.5
    broken = dataclasses.replace(run.tables, unit_flow=flow, capture_by_host=by_host)
    found = ledger.check_capture(broken, run.reference)
    assert found
    assert {item.leg for item in found} >= {"c"}
    assert all(item.unit_id == "ccs" for item in found)


# --------------------------------------------------------------------------------------
# The rate reading is for abatement units only
# --------------------------------------------------------------------------------------


def test_a_converters_emission_input_keeps_its_kt_reading() -> None:
    """``tgr_blast_furnace_coke`` is a converter: its ``emission_input`` row stays kt per
    unit of its output, multiplied by its total activity in C8, and takes no z_host."""
    reference = _reference()
    io = pd.concat(
        [
            reference.unit_input_output,
            pd.DataFrame([_io("kiln_coal", "co2_process", -10.0, "emission_input")]),
        ],
        ignore_index=True,
    )
    reference = dataclasses.replace(reference, unit_input_output=io)
    run = _run(reference, frozenset({"kiln_coal"}), frozenset(), "kiln_coal")
    drawn = _flow(run, "kiln_coal", "co2_process", {"emission_input"})
    activity = run.tables.dispatch
    activity = activity[activity["unit_id"] == "kiln_coal"].groupby("period")["activity"].sum()
    np.testing.assert_allclose(drawn, -10.0 * activity, rtol=1e-9)
    assert "z_host" not in run.model.variables


# --------------------------------------------------------------------------------------
# Check 6, one failing fixture per leg (V37 legs (c) to (f))
# --------------------------------------------------------------------------------------


def _legs(run: _Run, **tables) -> set[str]:
    broken = dataclasses.replace(run.tables, **tables)
    return {item.leg for item in ledger.check_capture(broken, run.reference)}


def test_the_capture_check_names_a_host_row_out_of_its_share() -> None:
    """Leg (d): what a host row says was captured must be ν × that host's production × the
    share of its activity treated. Only the per-host table is broken, so (c) still holds."""
    run = _gas_run()
    by_host = run.tables.capture_by_host.copy()
    rows = (by_host["carrier_id"] == "co2_process") & (by_host["period"] == 2030)
    by_host.loc[rows, "captured"] *= 1.5
    assert "d" in _legs(run, capture_by_host=by_host)


def test_the_capture_check_names_a_host_treated_twice_over() -> None:
    """Leg (e): the trains on one host treat at most its activity."""
    run = _gas_run(second_train=True)
    by_host = run.tables.capture_by_host.copy()
    by_host["treated_activity"] *= 2.0
    assert "e" in _legs(run, capture_by_host=by_host)


def test_the_capture_check_names_a_carbon_term_without_its_credit() -> None:
    """Leg (f): the carbon term is the charged venting less the biogenic credit."""
    run = _gas_run()
    costs = run.tables.cost_by_term.copy()
    rows = (costs["term"] == "carbon") & (costs["period"] == 2030)
    costs.loc[rows, "annual"] += 1.0
    assert _legs(run, cost_by_term=costs) == {"f"}


def test_the_capture_check_reads_hosts_from_the_data_not_from_the_build() -> None:
    """A self-link (the train named as its own host) would let leg (c) count the reboiler's
    CO₂ as the host's. Check 6 reads the hosts from ``unit_abatement_host``, so a train that
    claims its own reboiler stack is caught."""
    run = _gas_run()
    flow = run.tables.unit_flow.copy()
    own = flow[
        (flow["unit_id"] == "ccs") & (flow["carrier_id"] == "co2_fuel_fossil")
        & (flow["role"] == build.A6_ROLE)
    ].set_index("period")["flow"]
    taken = (flow["unit_id"] == "ccs") & (flow["role"] == "emission_input") & (
        flow["carrier_id"] == "co2_fuel_fossil"
    )
    flow.loc[taken, "flow"] -= RATE * flow.loc[taken, "period"].map(own).to_numpy()
    by_host = run.tables.capture_by_host
    self_rows = by_host[by_host["carrier_id"] == "co2_fuel_fossil"].assign(
        host_unit_id="ccs", treated_activity=0.0, captured=0.0
    )
    assert "c" in _legs(
        run, unit_flow=flow, capture_by_host=pd.concat([by_host, self_rows], ignore_index=True)
    )


# --------------------------------------------------------------------------------------
# A co-fired host, two trains
# --------------------------------------------------------------------------------------


def test_a_co_fired_host_is_captured_across_both_fuels_and_treated_once() -> None:
    """``kiln_mix`` burns 0.6 PJ of gas and 0.4 of coal per PJ of heat. A6 sums the fuel CO₂
    over both fuels, so per unit of activity it makes 0.6 × 51.12 × 0.9885 + 0.4 × 94 =
    67.919 kt fossil and 0.6 × 51.12 × 0.0115 = 0.3527 kt biogenic, and Γ reads those sums.
    Two trains are offered on it and together treat it once."""
    reference = _reference(second_train=True, hosts=("kiln_coal", "kiln_mix"))
    run = _run(
        reference, frozenset({"kiln_mix", "kiln_coal"}), frozenset({"ccs", "ccs_b"}), "kiln_mix"
    )
    fossil = 0.6 * EF_GAS * (1 - GAS_BIOGENIC) + 0.4 * EF_COAL
    biogenic = 0.6 * EF_GAS * GAS_BIOGENIC
    assert fossil == pytest.approx(67.919, abs=1e-3)
    assert biogenic == pytest.approx(0.3527, abs=1e-4)

    by_host = run.tables.capture_by_host
    mix = by_host[(by_host["host_unit_id"] == "kiln_mix") & (by_host["period"] == 2030)]
    treated = mix.drop_duplicates("unit_id")["treated_activity"].sum()
    activity = run.tables.dispatch
    activity = activity[(activity["unit_id"] == "kiln_mix") & (activity["period"] == 2030)][
        "activity"
    ].sum()
    assert activity > 0.0
    assert treated == pytest.approx(activity, rel=1e-6), "capture pays, so the flue is treated"
    captured = mix.groupby("carrier_id")["captured"].sum()
    assert captured["co2_fuel_fossil"] == pytest.approx(RATE * fossil * activity, rel=1e-6)
    assert captured["co2_fuel_biogenic"] == pytest.approx(RATE * biogenic * activity, rel=1e-6)
    assert captured["co2_process"] == pytest.approx(RATE * PROCESS_CO2 * activity, rel=1e-6)
    assert ledger.check_capture(run.tables, reference) == ()


# --------------------------------------------------------------------------------------
# The screen reads gross production; an abatement unit with no rate captures nothing
# --------------------------------------------------------------------------------------


def test_the_screen_keeps_a_train_whose_host_also_draws_its_carrier() -> None:
    """A host that makes 50 kt of process CO₂ and draws back 60 is a net consumer, but its
    flue still carries 50. The screen judges a train's hosts on gross production, as C14
    does, so the train is not stranded."""
    reference = _reference()
    io = pd.concat(
        [
            reference.unit_input_output,
            pd.DataFrame([_io("kiln_gas", "co2_process", -60.0, "emission_input")]),
        ],
        ignore_index=True,
    )
    # The train captures process CO₂ only, so the host's fuel CO₂ cannot rescue it.
    io = io[~((io["unit_id"] == "ccs") & io["carrier_id"].isin(
        ["co2_fuel_fossil", "co2_fuel_biogenic"]))]
    reference = dataclasses.replace(reference, unit_input_output=io.reset_index(drop=True))
    sets, drops = build.screen_premise(
        _sets(reference, frozenset({"kiln_gas"}), frozenset({"ccs"})),
        reference,
        frozenset({"kiln_gas"}),
    )
    assert "ccs" in sets.units, drops


def _rateless_reference() -> ReferenceTables:
    """``ccs`` with its three rates removed: an abatement unit making ``co2_captured`` from
    a reboiler and power alone."""
    reference = _reference()
    io = reference.unit_input_output
    io = io[~((io["unit_id"] == "ccs") & (io["role"] == "emission_input"))]
    return dataclasses.replace(reference, unit_input_output=io.reset_index(drop=True))


def test_an_abatement_unit_with_no_rate_is_held_at_zero() -> None:
    """Without a rate it has nothing to capture, so C14 holds it at zero rather than letting
    it make ``co2_captured`` from nothing."""
    reference = _rateless_reference()
    sets = _sets(reference, frozenset({"kiln_gas"}), frozenset({"ccs"}))
    surviving = survival.surviving_capacity(
        pd.DataFrame([{"unit_id": "kiln_gas", "commissioned_year": 2015, "capacity": 2.0}]),
        reference.unit,
        PERIODS,
    )
    model = build.build_model(sets, surviving, build.period_axis(PERIODS, DISCOUNT_RATE),
                              reference)
    assert "C14_unhosted" in model.constraints
    result = build.solve(model)
    assert result.termination_condition == "optimal"
    z = model.variables["z"].solution.to_pandas()
    assert z.loc["ccs@supply:co2_captured"].abs().max() < TOLERANCE


def test_the_screen_drops_an_abatement_unit_with_no_rate() -> None:
    reference = _rateless_reference()
    _sets_out, drops = build.screen_premise(
        _sets(reference, frozenset({"kiln_gas"}), frozenset({"ccs"})),
        reference,
        frozenset({"kiln_gas"}),
    )
    assert [(drop.unit_id, drop.leg) for drop in drops] == [("ccs", build.NO_CAPTURE_HOST_LEG)]
    assert "no capture rate" in drops[0].detail

