"""The whole pipeline, on the real reference tables and the three synthetic premises.

These are the paths no per-module lane could write: every one of them needs ``load``,
``sets``, ``survival``, ``build`` and ``ledger`` at once, and the real
``docs/notes/data/`` rather than a three-unit fixture. The unit tests beside this file
prove each module against arithmetic; this file proves they compose.

**One of the three premises does not solve, and that is recorded here rather than worked
around.** ``mvp-cement``'s only real duty is a mass duty, and
``activity_process_duty_profile.csv`` contains no mass carrier anywhere — see
:func:`test_mvp_cement_is_blocked_by_a_duty_profile_with_no_mass_carrier`. Plan §5.2 makes
that an expected outcome with a named duty, not an error, and the assertion below is
written so that the day the reference table gains a ``cement`` row, it fails and asks to be
rewritten.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
import pytest

from carb3 import build, ledger, survival
from carb3.load import (
    PERIOD_YEARS,
    AdmissionScreen,
    ReferenceTables,
    load_premise_tables,
    load_reference_tables,
    screen_units,
)
from carb3.sets import ModelSets, build_sets, diagnose_unservable_duties

#: The three premises that solve on the reference tables as they stand today.
#: ``mvp-cement`` joined them when A2 learned to read ``premise_throughput`` for a D5 mass
#: duty (§3.1.2) — note 20 item 51 — and when the export variable gave ``co2_captured`` a
#: sink — item 53.
SOLVING_PREMISES: tuple[str, ...] = ("mvp-minimal", "mvp-dairy", "mvp-cement")

#: Every heat-pump unit note 21 §4.2's contest can be won by. The dairy's grade-4 drying
#: duty is won by ``dryer_heat_pump`` and its grade-2 duties by the two low-grade pumps.
HEAT_PUMPS: frozenset[str] = frozenset(
    {"heat_pump_lt_air", "heat_pump_lt_reject", "heat_pump_ht", "dryer_heat_pump"}
)

TOLERANCE = 1e-6


@dataclasses.dataclass(frozen=True)
class Run:
    """One premise solved end to end, with the model kept so the matrix can be re-read."""

    premise_id: str
    sets: ModelSets
    model: object
    result: build.SolveResult
    tables: ledger.Ledger


# --------------------------------------------------------------------------------------
# Fixtures — the pipeline runs once per session; each premise solves in well under a second
# --------------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def reference(reference_root: Path) -> ReferenceTables:
    return load_reference_tables(reference_root)


@pytest.fixture(scope="session")
def screen(reference: ReferenceTables) -> AdmissionScreen:
    return screen_units(reference, PERIOD_YEARS)


@pytest.fixture(scope="session")
def axis(reference: ReferenceTables) -> build.PeriodAxis:
    rate = build._scalar_parameter(reference, "discount_rate")
    return build.period_axis(PERIOD_YEARS, rate)


def _solve(
    premise_id: str,
    reference: ReferenceTables,
    screen: AdmissionScreen,
    axis: build.PeriodAxis,
) -> Run:
    premise = load_premise_tables(premise_id)
    sets = build_sets(reference, premise, screen, PERIOD_YEARS)
    vintages = survival.vintage_capacity(premise, reference.unit)
    surviving = survival.surviving_capacity(vintages, reference.unit, PERIOD_YEARS)
    model = build.build_model(sets, surviving, axis, reference)
    result = build.solve(model)
    tables = (
        ledger.build_ledger(result, sets, axis, reference)
        if result.solution is not None
        else None
    )
    return Run(premise_id, sets, model, result, tables)


@pytest.fixture(scope="session")
def runs(
    reference: ReferenceTables, screen: AdmissionScreen, axis: build.PeriodAxis
) -> dict[str, Run]:
    return {
        premise_id: _solve(premise_id, reference, screen, axis)
        for premise_id in SOLVING_PREMISES
    }


# --------------------------------------------------------------------------------------
# The solve itself
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("premise_id", SOLVING_PREMISES)
def test_the_premise_solves_to_optimality(runs: dict[str, Run], premise_id: str) -> None:
    """Plan §5.4's first exit condition, for the premises that can reach it.

    A non-optimal status would be *reported* rather than thrown (§5.2), which is why this
    asserts the termination condition rather than relying on the absence of an exception.
    """
    result = runs[premise_id].result
    assert result.termination_condition == "optimal", (
        f"{premise_id} terminated {result.termination_condition!r}; §5.2 reports that "
        "rather than raising, so a silent non-optimal run would otherwise pass"
    )
    assert result.objective is not None
    assert result.objective > 0.0


def test_mvp_cement_states_its_mass_duty_from_premise_throughput(
    reference: ReferenceTables, screen: AdmissionScreen
) -> None:
    """**The cement works' duty is a mass, and the duty profile cannot state it.**

    ``activity_process_duty_profile.csv`` holds no mass carrier anywhere: its 427 rows name
    26 distinct ``carrier_id`` values and neither ``cement`` nor ``clinker`` is among them.
    ``Cement Works``'s ``cement_grinding`` row is classified ``MOT`` on ``motive_power`` at
    ``duty_share`` 1.00000, so an A2 that read only the register and the profile turned
    1.130000 **Mt of cement** into 1.130000 **PJ of motive power** — a weight labelled as an
    energy, which no unit could serve, and ``mvp-cement`` did not solve at all.

    §3.1.2 is where the answer already was: "Where the ``carrier_id`` is a product with
    ``may_export`` true, the row is the premise's duty on that product under D5." So A2 now
    reads ``premise_throughput`` for product duties, and three things follow, all asserted
    here: the ``cement`` duty exists at 1.130000 Mt/yr on ``cement_grinding``; the
    ``motive_power`` duty that process used to carry is gone, because its profile row
    classifies its energy need rather than stating a demand; and ``clinker``, a product
    with ``may_export`` false, becomes **no duty at all** — §3.1.2 makes its row evidence.
    """
    premise = load_premise_tables("mvp-cement")
    sets = build_sets(reference, premise, screen, PERIOD_YEARS)

    profile = reference.activity_process_duty_profile
    assert "cement" not in set(profile["carrier_id"]), (
        "activity_process_duty_profile now carries a `cement` row; the duty would be "
        "derived twice and the throughput branch needs revisiting"
    )

    by_key = {duty.key: duty for duty in sets.duties}
    cement = by_key[("mvp-cement", "cement_grinding", "cement")]
    assert cement.grade_rank is None, "cement is not gradeable, so C10 has nothing to say"
    assert set(cement.quantity) == set(PERIOD_YEARS)
    assert all(
        quantity == pytest.approx(1.130000) for quantity in cement.quantity.values()
    )

    assert ("mvp-cement", "cement_grinding", "motive_power") not in by_key, (
        "cement_grinding's MOT profile row is a classification of its energy need; read "
        "as a duty it states 1.13 Mt of cement as 1.13 PJ of motive power"
    )
    assert not any(duty.carrier_id == "clinker" for duty in sets.duties), (
        "clinker is may_export FALSE, so §3.1.2 makes its throughput row evidence and "
        "§3.9 gives it no duty; C8 pins its makers instead"
    )

    # And the duty is servable: both grinders make cement and both clear the §3.2 screen.
    assert sets.eligible[cement.key] == frozenset(
        {"grinder_mixer_elec", "grinder_mixer_clinker_sub_elec"}
    )
    assert diagnose_unservable_duties(sets, screen) == ()


def test_mvp_cement_motive_power_duties_are_the_four_the_readme_states(
    reference: ReferenceTables, screen: AdmissionScreen
) -> None:
    """0.168000 PJ/yr over four processes — the premise README's own figure.

    The README was written expecting ``cement_grinding`` to carry no motive-power duty, and
    it is the arithmetic check that A2 now reads the premise the way the premise was
    authored: 0.021000 + 0.100800 + 0.025200 + 0.021000 = 0.168000.
    """
    premise = load_premise_tables("mvp-cement")
    sets = build_sets(reference, premise, screen, PERIOD_YEARS)
    motive = [duty for duty in sets.duties if duty.carrier_id == "motive_power"]
    assert {duty.process_id for duty in motive} == {
        "quarrying_crushing",
        "raw_grinding_blending",
        "raw_meal_homogenisation",
        "packing_dispatch",
    }
    total = sum(duty.quantity[PERIOD_YEARS[0]] for duty in motive)
    assert total == pytest.approx(0.168000)


def test_mvp_cement_kilns_and_the_capture_train_take_a_supply_column(
    reference: ReferenceTables, screen: AdmissionScreen
) -> None:
    """A unit with no duty still needs an activity variable, and two families need one.

    ``clinker`` is a ``product`` with ``may_export`` false, so §3.9 gives the kilns no duty
    and C8 (carrier balance) pins them instead. ``co2_captured`` is a ``product`` with
    ``may_export`` **true** and still no duty, because no premise states a throughput of
    captured CO₂ — so ``ccs_amine`` needs the same treatment, and before this it had no
    variable at all and was therefore unbuildable however cheap it was (note 20 item 53).

    ``cement`` is excluded: the grinder *is* dispatched, to the §3.1.2 throughput duty, and
    a second undispatched column would let one Mt satisfy C1 and enter C8 as well.
    """
    premise = load_premise_tables("mvp-cement")
    sets = build_sets(reference, premise, screen, PERIOD_YEARS)

    assert sets.supply == {
        "clinker": frozenset({"kiln_dry_coal", "kiln_dry_gas"}),
        "co2_captured": frozenset({"ccs_amine"}),
    }
    assert "cement" not in sets.supply

    supply_columns = {
        pair.unit_id for pair in build._dispatch_pairs(sets) if pair.duty_key is None
    }
    assert supply_columns == {"kiln_dry_coal", "kiln_dry_gas", "ccs_amine"}


def test_the_capture_trains_earliest_year_reaches_a_unit_with_no_duty(
    reference: ReferenceTables, screen: AdmissionScreen
) -> None:
    """``ccs_amine``'s 2035 gate is the only ``earliest_year`` row that binds on a train.

    It arrives through ``supply_earliest_year`` rather than through the duty-keyed map,
    because the train sits in no U_q. Reading only the duty-keyed map would have let the
    LP build a capture train in 2025.
    """
    premise = load_premise_tables("mvp-cement")
    sets = build_sets(reference, premise, screen, PERIOD_YEARS)
    assert sets.supply_earliest_year == {("co2_captured", "ccs_amine"): 2035}

    bounds = build._build_upper_bounds(
        sets,
        ["ccs_amine"],
        PERIOD_YEARS,
        pd.Index(["ccs_amine"], name="unit"),
        pd.Index(PERIOD_YEARS, name="period"),
    )
    gated = {
        int(year): float(bounds.sel(unit="ccs_amine", period=year))
        for year in PERIOD_YEARS
    }
    assert gated[2021] == 0.0 and gated[2030] == 0.0
    assert gated[2035] == float("inf") and gated[2050] == float("inf")


def test_c9_gates_the_co2_export_on_the_premises_cluster(
    reference: ReferenceTables, screen: AdmissionScreen
) -> None:
    """C9 (infrastructure availability), back in scope for one carrier and sourced.

    ``infrastructure_scenario.csv``'s 63 ``co2_transport`` rows say four clusters take CO₂
    from 2030 and five never do. ``mvp-cement`` sits at ``humber``, so its window opens at
    2030; moved to ``grangemouth`` it never opens and the export variable is bounded to
    zero throughout, which is the honest answer for a site with no pipeline.
    """
    premise = load_premise_tables("mvp-cement")
    sets = build_sets(reference, premise, screen, PERIOD_YEARS)
    windows = {window.carrier_id: window for window in sets.export_windows}
    assert windows["co2_captured"].network == "co2_transport"
    assert windows["co2_captured"].periods == (2030, 2035, 2040, 2045, 2050)

    stranded = dataclasses.replace(premise, premise_record=premise.premise_record.assign(
        cluster_id="grangemouth"
    ))
    sets = build_sets(reference, stranded, screen, PERIOD_YEARS)
    windows = {window.carrier_id: window for window in sets.export_windows}
    assert windows["co2_captured"].periods == ()


def test_an_unpriced_export_is_refused_rather_than_becoming_free_disposal(
    reference: ReferenceTables, screen: AdmissionScreen
) -> None:
    """``export_price`` covers ``electricity`` at six of seven periods, and not 2021.

    The partial case is the dangerous one — it is ``heavy_fuel_oil``'s single
    ``import_price`` row one table away. An export with no price is free disposal, and
    ``electricity`` is a ``primary`` carrier that §5.2's ``may_dispose`` gate forbids
    disposing of, so an unpriced export variable would reopen exactly what that gate
    closes. Every premise here has an electricity connection and all three refuse it.
    """
    prices = reference.scenario_parameters
    covered = {
        int(row.period)
        for row in prices.itertuples(index=False)
        if row.parameter_id == "export_price" and row.carrier_id == "electricity"
    }
    assert covered == {2025, 2030, 2035, 2040, 2045, 2050}, (
        "electricity's export_price now covers a different set of periods; if it covers "
        "all seven this test should assert an export window instead of a refusal"
    )

    for premise_id in SOLVING_PREMISES:
        premise = load_premise_tables(premise_id)
        sets = build_sets(reference, premise, screen, PERIOD_YEARS)
        refused = {refusal.carrier_id for refusal in sets.export_refused}
        assert "electricity" in refused, premise_id
        assert "electricity" not in {w.carrier_id for w in sets.export_windows}


def test_mvp_cement_reports_the_two_processes_it_could_not_size(
    reference: ReferenceTables, screen: AdmissionScreen
) -> None:
    """§3.10 cannot state a known zero, so a blank is named rather than read as one.

    ``clinker_cooling`` and ``site_services`` have a genuine duty of 0.00000 PJ/yr and are
    written blank with the reason in ``provenance``. A2 derives no duty for them, and the
    run report prints them — silence is the failure mode here, not the blank.
    """
    premise = load_premise_tables("mvp-cement")
    sets = build_sets(reference, premise, screen, PERIOD_YEARS)
    assert sets.no_magnitude == ("clinker_cooling", "site_services")
    assert not [duty for duty in sets.duties if duty.process_id in sets.no_magnitude]


# --------------------------------------------------------------------------------------
# C8, checked against the built matrix rather than against the solver
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("premise_id", SOLVING_PREMISES)
def test_c8_closes_at_every_carrier_node_in_every_period(
    runs: dict[str, Run], premise_id: str
) -> None:
    """**Critical path.** A × sol − b, computed here, not asked of the solver (§5.3).

    Plan §10's failure mode is "a carrier node does not balance and the solver hides it".
    Nothing in this test consults HiGHS' opinion: the matrix and the right-hand side come
    off the built model, the solution vector comes back from the solve, and the residual is
    multiplied out here — so a node that does not balance is caught even where the status
    says ``optimal``.
    """
    run = runs[premise_id]
    violations = build.check_constraint_rows(run.model, run.result, TOLERANCE)
    assert violations == (), f"{premise_id}: {violations}"

    # ...and there are C8 rows to have checked. An empty constraint set also passes the
    # loop above, which would make the assertion vacuous.
    c8 = [name for name in run.model.constraints if name.startswith("C8_")]
    assert c8, f"{premise_id} built no C8 rows at all"
    rows = sum(run.model.constraints[name].size for name in c8)
    assert rows == len(c8) * len(PERIOD_YEARS)


@pytest.mark.parametrize("premise_id", SOLVING_PREMISES)
def test_the_ledger_carrier_mix_nets_to_zero_at_every_c8_node(
    runs: dict[str, Run], premise_id: str
) -> None:
    """The same statement in the output: imported + produced − consumed − disposed = 0.

    The row check above proves the solver satisfied the constraint; this proves the ledger
    reports the flows the constraint was written over, which is a different failure — a
    coefficient read with the wrong sign would balance in the matrix and not in the table.
    """
    mix = runs[premise_id].tables.carrier_mix
    c8_carriers = {
        name.removeprefix("C8_") for name in runs[premise_id].model.constraints
        if name.startswith("C8_")
    }
    nodes = mix[mix["carrier_id"].isin(c8_carriers)]
    assert not nodes.empty
    assert nodes["net"].abs().max() < TOLERANCE


# --------------------------------------------------------------------------------------
# The objective
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("premise_id", SOLVING_PREMISES)
def test_the_objective_terms_sum_to_the_reported_objective(
    runs: dict[str, Run], premise_id: str
) -> None:
    """§5.3's "objective decomposition" path.

    The ledger reads the solved variables and goes back to ``unit.csv`` and
    ``scenario_parameters.csv`` for every price, so agreeing with the number HiGHS reported
    is evidence the objective was assembled from the parameters it claims — not a
    restatement of the expression that built it.
    """
    run = runs[premise_id]
    total = float(run.tables.cost_by_term["discounted"].sum())
    assert total == pytest.approx(run.result.objective, rel=1e-9, abs=1e-9)

    by_term = run.tables.cost_by_term.groupby("term")["discounted"].sum()
    assert set(by_term.index) == set(ledger.COST_TERMS)
    # Every live term is positive: a negative capex or fuel bill would sum correctly and
    # still be nonsense. The biogenic credit, the only term that may be negative, is
    # structurally zero in this slice and carries no row.
    assert (by_term >= -TOLERANCE).all()
    assert by_term["fuel"] > 0.0
    assert by_term["carbon"] > 0.0


@pytest.mark.parametrize("premise_id", SOLVING_PREMISES)
def test_capex_is_charged_on_new_capacity_only(
    runs: dict[str, Run], premise_id: str
) -> None:
    """An incumbent's capex is sunk (§4.2), and C5 forbids building in the start year.

    Together those make the start period's capex exactly zero, which is the cheapest
    available check that the annuity is charged on ``a − e`` and not on ``a``.
    """
    costs = runs[premise_id].tables.cost_by_term
    start = costs[(costs["period"] == PERIOD_YEARS[0]) & (costs["term"] == "capex")]
    assert float(start["annual"].iloc[0]) == pytest.approx(0.0, abs=TOLERANCE)
    assert float(costs[costs["term"] == "capex"]["annual"].sum()) > 0.0


# --------------------------------------------------------------------------------------
# Problem size — linopy #248
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("premise_id", SOLVING_PREMISES)
def test_the_problem_is_sparse_not_dense(runs: dict[str, Run], premise_id: str) -> None:
    """**Critical path.** linopy #248: an ineffective mask builds a dense model silently.

    At three premises HiGHS solves either version in under a second, so the mistake would
    not surface until M5. The band below is derived from the screened set sizes rather than
    hardcoded: z_{u,q,t} is declared over the eligible pairs and nothing else, so its size
    is exactly ``|pairs| x |T|``, and the dense alternative — a mask over ``|U| x |Q|`` —
    would be larger by the ratio of the admitted set to the eligible sets.
    """
    run = runs[premise_id]
    sets = run.sets
    periods = len(sets.periods)

    pairs = sum(
        len(sets.eligible[duty.key] & sets.units) for duty in sets.duties
    ) + sum(len(units & sets.units) for units in sets.supply.values())
    assert run.model.variables["z"].size == pairs * periods

    model_units = {pair.unit_id for pair in build._dispatch_pairs(sets)}
    # n, a, e and at most one import and one disposal variable per carrier in the tables.
    ceiling = (pairs + 3 * len(model_units) + 2 * len(sets.units)) * periods
    assert pairs * periods <= run.result.n_variables <= ceiling

    dense = len(sets.units) * len(sets.duties) * periods
    assert run.result.n_variables < dense, (
        f"{premise_id} built {run.result.n_variables} variables against a dense z of "
        f"{dense}; the eligibility sets are not narrowing the model"
    )


# --------------------------------------------------------------------------------------
# The pathway, and what drives it (§4.2)
# --------------------------------------------------------------------------------------


def _grade_two_dispatch(run: Run) -> pd.DataFrame:
    """z on ``boiler_steam_hot_water``'s grade-2 duty, which is §4.2's contest exactly.

    Not every ``heat_60_100`` row: ``mvp-dairy``'s ``site_services`` duty has a heat pump
    as its *incumbent* (the README's one substitution, forced by every SPC unit being
    ``grade_out`` 1), so including it would make "a heat pump runs at 2021" true for a
    reason that has nothing to do with the switch.
    """
    dispatch = run.tables.dispatch
    return dispatch[
        (dispatch["carrier_id"] == "heat_60_100")
        & (dispatch["process_id"] == "boiler_steam_hot_water")
    ]


# ``mvp-cement`` is out of this one and not by omission: the works has **no gradeable
# heat duty at all** — its only gradeable carrier, ``heat_lt60``, appears solely as the
# kilns' reject — so §4.2's contest does not exist there. That is the premise README's own
# statement and the structural point spec §13 makes about cement.
@pytest.mark.parametrize("premise_id", ("mvp-minimal", "mvp-dairy"))
def test_the_low_grade_heat_duty_switches_to_a_heat_pump_at_the_first_buildable_period(
    runs: dict[str, Run], premise_id: str
) -> None:
    """§4.2: the heat pump wins by 23% at the **first** opportunity, and C5 says when that is.

    The expected pathway is a step, not a ramp (§4.3): C4 and the vintages are mechanism,
    the incumbent's capex is sunk, and nothing waits for it to retire. So 2021 — the one
    period C5 (no building in the start year) closes — is served by the incumbents, and
    2025, the first buildable period, is served by heat pumps.
    """
    run = runs[premise_id]
    grade_two = _grade_two_dispatch(run)
    assert not grade_two.empty

    start = grade_two[grade_two["period"] == 2021]
    assert start[start["unit_id"].isin(HEAT_PUMPS)]["activity"].sum() == pytest.approx(
        0.0, abs=TOLERANCE
    ), "no heat pump can be built in the start year (C5), and none is an incumbent here"
    assert start["activity"].sum() > 0.0

    switched = grade_two[grade_two["period"] == 2025]
    served = switched["activity"].sum()
    by_pumps = switched[switched["unit_id"].isin(HEAT_PUMPS)]["activity"].sum()
    assert served > 0.0
    assert by_pumps == pytest.approx(served, abs=TOLERANCE), (
        f"{premise_id}: heat pumps take {by_pumps:.6f} of {served:.6f} PJ/yr at 2025; "
        "§4.2 says they take all of it"
    )

    gas = switched[switched["unit_id"] == "boiler_lt_gas"]["activity"].sum()
    assert gas == pytest.approx(0.0, abs=TOLERANCE)


def test_the_dairy_drying_duty_switches_to_a_heat_pump_too(runs: dict[str, Run]) -> None:
    """The grade-4 drying duty is the dairy's own case, and it is the same arithmetic."""
    dispatch = runs["mvp-dairy"].tables.dispatch
    drying = dispatch[dispatch["carrier_id"] == "heat_150_400"]
    at_2021 = drying[(drying["period"] == 2021) & (drying["unit_id"] == "dryer_direct_gas")]
    at_2025 = drying[(drying["period"] == 2025) & (drying["unit_id"] == "dryer_heat_pump")]
    assert float(at_2021["activity"].iloc[0]) > 0.0
    assert float(at_2025["activity"].iloc[0]) > 0.0


def test_nothing_is_built_in_the_start_year(runs: dict[str, Run]) -> None:
    """C5, read off the ledger rather than off the constraint."""
    for run in runs.values():
        built = run.tables.build
        start = built[built["period"] == PERIOD_YEARS[0]]["new_capacity"].abs().max()
        assert start < TOLERANCE, f"{run.premise_id} built capacity in {PERIOD_YEARS[0]}"


def _without_carbon(reference: ReferenceTables) -> ReferenceTables:
    """``reference`` with ``carbon_price`` zeroed, in a copy.

    Nothing under ``docs/notes/data/`` is touched: the frame is copied and the
    :class:`ReferenceTables` record rebuilt around it.
    """
    parameters = reference.scenario_parameters.copy()
    zeroed = parameters["parameter_id"] == "carbon_price"
    assert zeroed.any()
    parameters.loc[zeroed, "value"] = 0.0
    return dataclasses.replace(reference, scenario_parameters=parameters)


def _pump_share(run: Run) -> float:
    """The heat pumps' share of the grade-2 duty from the first buildable period on."""
    late = _grade_two_dispatch(run)
    late = late[late["period"] >= 2025]
    return late[late["unit_id"].isin(HEAT_PUMPS)]["activity"].sum() / late["activity"].sum()


def test_carbon_off_inverts_the_boiler_versus_heat_pump_ranking(
    reference: ReferenceTables, screen: AdmissionScreen, axis: build.PeriodAxis
) -> None:
    """§4.2's contest, run as the two-unit contest §4.2 actually describes.

    §4.2 ranks one new ``heat_pump_lt_air`` against the avoidable cost of one incumbent
    ``boiler_lt_gas`` and puts the pump ahead by 23% at 2025, entirely on the carbon charge:
    §4.1 establishes there is no price crossover anywhere in the horizon, so with
    ``carbon_price`` at zero the pump's 16.12 £m/yr of electricity must lose to the
    boiler's 11.97 £m/yr of gas and no annuity can close the gap.

    U_q is narrowed to those two units, because at ``mvp-minimal`` it really holds eleven
    and the wider contest has a different winner — see
    :func:`test_carbon_off_switches_the_premise_to_on_site_generation_not_to_the_boiler`.
    Narrowing it is what makes this a test of §4.2's arithmetic rather than of the
    eligibility tables.
    """
    contenders = frozenset({"boiler_lt_gas", "heat_pump_lt_air"})

    def head_to_head(source: ReferenceTables) -> Run:
        premise = load_premise_tables("mvp-minimal")
        sets = build_sets(source, premise, screen, PERIOD_YEARS)
        sets = dataclasses.replace(
            sets,
            units=contenders,
            eligible={key: units & contenders for key, units in sets.eligible.items()},
        )
        vintages = survival.vintage_capacity(premise, source.unit)
        surviving = survival.surviving_capacity(vintages, source.unit, PERIOD_YEARS)
        model = build.build_model(sets, surviving, axis, source)
        result = build.solve(model)
        return Run(
            "mvp-minimal", sets, model, result,
            ledger.build_ledger(result, sets, axis, source),
        )

    with_carbon = head_to_head(reference)
    without_carbon = head_to_head(_without_carbon(reference))
    assert with_carbon.result.termination_condition == "optimal"
    assert without_carbon.result.termination_condition == "optimal"

    assert _pump_share(with_carbon) == pytest.approx(1.0, abs=TOLERANCE)
    assert _pump_share(without_carbon) == pytest.approx(0.0, abs=TOLERANCE)

    built = without_carbon.tables.build
    pumps = built[built["unit_id"].isin(HEAT_PUMPS)]["new_capacity"]
    assert pumps.abs().max() < TOLERANCE if len(pumps) else True

    # The objective falls, because a cost was removed rather than shuffled.
    assert without_carbon.result.objective < with_carbon.result.objective


def test_carbon_off_switches_the_premise_to_on_site_generation_not_to_the_boiler(
    reference: ReferenceTables, screen: AdmissionScreen, axis: build.PeriodAxis
) -> None:
    """**On-site generation is live in this slice, and note 21 says three times that it is not.**

    §2.1 drops Z^exp because "no on-site generation, so nothing to export"; §6.3 says
    ``MF-79`` "cannot bite here: it exists because on-site generation makes consumption
    exceed import, and there is no on-site generation"; §9 lists on-site generation, CHP
    and PV among the exclusions. None of that is enforced anywhere. ``unit_input_output``
    carries **23 ``coproduct`` rows**, four gas CHPs clear the §3.2 screen, and
    ``chp_gas_ccgt`` is eligible for ``boiler_steam_hot_water`` at ``Food Processing
    Centre`` with ``electricity`` at ``+1.3`` per PJ of grade-3 heat. C8 credits that
    coproduct like any other flow, so the site generates.

    With the carbon charge removed the model does not fall back on the gas boiler as §4.2
    predicts. It builds a gas CHP for the grade-3 duty, spends the coproduct electricity on
    heat pumps for the grade-2 duty, and **imports no electricity at all** — consumption
    exceeds import, which is exactly the condition ``MF-79`` exists for. The switch §4.2
    describes is real (the test above proves it head to head); it is simply not the whole
    contest at a premise whose U_q holds eleven units.
    """
    with_carbon = _solve("mvp-minimal", reference, screen, axis)
    without_carbon = _solve("mvp-minimal", _without_carbon(reference), screen, axis)
    assert without_carbon.result.termination_condition == "optimal"
    assert without_carbon.result.objective < with_carbon.result.objective

    def imported(run: Run, carrier_id: str) -> float:
        mix = run.tables.carrier_mix
        late = mix[(mix["carrier_id"] == carrier_id) & (mix["period"] >= 2025)]
        return float(late["imported"].sum())

    assert imported(with_carbon, "electricity") > 0.0
    assert imported(without_carbon, "electricity") == pytest.approx(0.0, abs=TOLERANCE)

    generated = without_carbon.tables.carrier_mix
    electricity = generated[generated["carrier_id"] == "electricity"]
    late = electricity[electricity["period"] >= 2025]
    assert late["produced"].sum() > 0.0, "the CHP's coproduct must reach the balance"
    assert late["consumed"].sum() > 0.0

    chp = without_carbon.tables.build
    chp = chp[chp["unit_id"].str.startswith("chp_")]
    assert chp["new_capacity"].max() > 0.0, "no CHP was built, so nothing generates"

    # ...and the heat pumps still win the grade-2 duty, powered by the CHP rather than the
    # grid. That is the finding: carbon off changes where the electricity comes from.
    assert _pump_share(without_carbon) == pytest.approx(1.0, abs=TOLERANCE)


# --------------------------------------------------------------------------------------
# Disposal — a reported quantity, not a residual
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("premise_id", SOLVING_PREMISES)
def test_disposal_is_reported_and_is_what_carbon_is_charged_on(
    runs: dict[str, Run], premise_id: str
) -> None:
    """Plan §2.2 and spec §5.4: carbon is charged on venting, never on fuel consumed.

    Both premises fire a gas boiler in 2021, so ``co2_fuel_fossil`` — the row A6 derives at
    build time rather than reads — must be vented and charged, and ``heat_lt60``, the
    boiler's reject, must be dumped: 59 ``reject`` rows run into a grade-1 carrier with one
    consumer, and without the disposal variable C8 would force the boiler to zero.
    """
    disposal = runs[premise_id].tables.disposal
    assert not disposal.empty

    fossil = disposal[disposal["carrier_id"] == "co2_fuel_fossil"]
    assert float(fossil[fossil["period"] == 2021]["quantity"].iloc[0]) > 0.0
    assert set(fossil["carbon_charge"]) == {"charged"}
    assert float(fossil[fossil["period"] == 2021]["carbon_cost"].iloc[0]) > 0.0

    reject = disposal[disposal["carrier_id"] == "heat_lt60"]
    assert float(reject[reject["period"] == 2021]["quantity"].iloc[0]) > 0.0
    # heat_lt60 carries no carbon_charge, and a blank must read as a blank rather than as
    # the string "nan": it is printed beside the quantity in the run report.
    assert set(reject["carbon_charge"]) == {""}
    assert reject["carbon_cost"].abs().max() < TOLERANCE

    biogenic = disposal[disposal["carrier_id"] == "co2_fuel_biogenic"]
    assert set(biogenic["carbon_charge"]) == {"zero_rated"}
    assert biogenic["carbon_cost"].abs().max() < TOLERANCE


@pytest.mark.parametrize("premise_id", SOLVING_PREMISES)
def test_the_carbon_term_equals_the_disposal_charge_less_the_biogenic_credit(
    runs: dict[str, Run], reference: ReferenceTables, premise_id: str
) -> None:
    """§5.4 has two legs, and ``disposal`` can only ever hold one of them.

    Z^carbon charges the venting **and** credits back the zero-rated CO2 an abatement unit
    captures. A captured stream is a flow *into* a unit, not a disposal, so it appears in no
    row of the disposal table, and the identity is

        Z^carbon_t  =  sum_c d_{c,t} on the charged carriers  -  credit_t

    Asserting the two tables equal outright was only ever true while nothing captured any
    biogenic CO2 anywhere, which held until note 20 item 56 put the three dry cement kilns'
    ``co2_process`` back on the kt-per-Mt basis spec 3.6 states. ``ccs_amine`` then became
    worth building at ``mvp-cement`` and the objective's carbon term sat GBP 0.618m below
    the disposal table at 2035 -- 2.0457 kt of captured biogenic CO2 at GBP 302.08/t, the
    credit exactly.

    The credit is recomputed here from the reference CSVs rather than from
    :func:`carb3.build.biogenic_capture_weights`, so the two sides of the identity stay
    independent: the ledger reads the function, this reads the data.
    """
    run = runs[premise_id]
    costs = run.tables.cost_by_term
    carbon = costs[costs["term"] == "carbon"].set_index("period")["annual"]
    charged = (
        run.tables.disposal.groupby("period")["carbon_cost"].sum().reindex(carbon.index)
    )

    price = (
        reference.scenario_parameters.loc[
            reference.scenario_parameters["parameter_id"].astype(str) == "carbon_price"
        ]
        .astype({"period": int, "value": float})
        .set_index("period")["value"]
        .reindex(carbon.index)
    )
    assert not price.isna().any(), "carbon_price is missing a period"

    zero_rated = set(
        reference.carrier.loc[
            reference.carrier["carbon_charge"].astype(str).str.strip() == "zero_rated",
            "carrier_id",
        ].astype(str)
    )
    abatement = set(
        reference.unit.loc[
            reference.unit["unit_class"].astype(str).str.strip() == "abatement",
            "unit_id",
        ].astype(str)
    )
    io = reference.unit_input_output
    taken = io[
        io["unit_id"].astype(str).isin(abatement)
        & (io["role"].astype(str).str.strip() == "emission_input")
        & io["carrier_id"].astype(str).isin(zero_rated)
    ]
    weights = (
        taken["coefficient"].astype(float).abs().groupby(taken["unit_id"].astype(str)).sum()
    )

    dispatch = run.tables.dispatch
    credit = pd.Series(0.0, index=carbon.index)
    for unit_id, weight in weights.items():
        rows = dispatch[dispatch["unit_id"].astype(str) == unit_id]
        if rows.empty:
            continue
        activity = (
            rows.groupby("period")["activity"].sum().reindex(carbon.index).fillna(0.0)
        )
        credit = credit + activity * weight * build.CARBON_UNIT_CONVERSION * price

    assert (carbon - (charged - credit)).abs().max() < TOLERANCE
    # The premise that pays for the leg above: without it this test cannot tell a correct
    # ledger from one that dropped the credit.
    if premise_id == "mvp-cement":
        assert credit.abs().max() > TOLERANCE


# --------------------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------------------


def test_the_ledger_round_trips_through_parquet(
    runs: dict[str, Run], screen: AdmissionScreen, tmp_path: Path
) -> None:
    """§3.4 and §7: hand-authored inputs stay CSV, outputs are parquet."""
    run = runs["mvp-dairy"]
    report = ledger.RunReport(
        premise_id=run.premise_id,
        screen=screen,
        n_variables=run.result.n_variables,
        n_constraints=run.result.n_constraints,
        wall_clock_seconds=run.result.wall_clock_seconds,
        status=run.result.termination_condition,
    )
    written = ledger.write_parquet(run.tables, report, tmp_path)
    assert all(path.suffix == ".parquet" and path.is_file() for path in written)

    for table in ledger.LEDGER_TABLES:
        original = getattr(run.tables, table)
        restored = pd.read_parquet(tmp_path / run.premise_id / f"{table}.parquet")
        pd.testing.assert_frame_equal(original, restored)

    dropped = pd.read_parquet(tmp_path / run.premise_id / "screen_dropped.parquet")
    assert len(dropped) == len(screen.dropped)
    assert "heat_exchanger_lt_steam" in set(dropped["unit_id"])
    assert "boiler_lt_hydrogen" in set(dropped["unit_id"])


# --------------------------------------------------------------------------------------
# The entry point
# --------------------------------------------------------------------------------------


def test_the_cli_runs_every_premise_and_all_three_now_solve(
    tmp_path: Path, capsys
) -> None:
    """``python -m carb3`` end to end. All three premises solve, and the run says so.

    The previous form of this test asserted the opposite — exit status 1 and "2 of 3
    premises solved" — because ``mvp-cement`` was blocked by note 20 item 51. Both causes
    are closed, so the assertion is inverted rather than relaxed: a run that still reported
    a blocked premise would now be the failure.
    """
    from carb3.__main__ import main

    status = main(["--out-dir", str(tmp_path)])
    captured = capsys.readouterr().out

    assert status == 0, "all three premises solve; a non-zero status means one did not"
    for premise_id in SOLVING_PREMISES:
        assert f"premise {premise_id}" in captured
    assert "NOT SOLVED" not in captured
    assert "§3.2 admission screen" in captured
    assert "objective decomposition" in captured
    assert "3 of 3 premises solved to optimality" in captured
    # The two findings the run now has to surface beside the screen's dropped units.
    assert "export x_c,t: co2_captured available 2030" in captured
    assert "export refused: electricity" in captured

    for premise_id in SOLVING_PREMISES:
        assert (tmp_path / premise_id / "cost_by_term.parquet").is_file()
        assert (tmp_path / premise_id / "disposal.parquet").is_file()


def test_the_tariff_override_reprices_the_export_and_says_so(tmp_path: Path, capsys) -> None:
    """``--co2-tariff`` is a scenario knob, and a run under one must never be silent.

    The tariff is an assumption, so the number it produces is only readable beside the
    value it assumed. The report prints the override and the ledger's export term moves
    with it; ``scenario_parameters.csv`` is untouched on disk either way.
    """
    from carb3.__main__ import main

    status = main(["mvp-cement", "--co2-tariff", "60"])
    captured = capsys.readouterr().out
    assert status == 0
    assert "OVERRIDDEN to £60.00/t flat" in captured
    assert "scenario_parameters.csv is unchanged on disk" in captured


# --------------------------------------------------------------------------------------
# The export variable, end to end on the real cement premise
# --------------------------------------------------------------------------------------


def _cement_with_export(
    reference: ReferenceTables,
    screen: AdmissionScreen,
    axis: build.PeriodAxis,
    tariff: float,
) -> Run:
    """``mvp-cement`` solved at a stated CO₂ transport tariff.

    The tests below pass a **negative** tariff, which is a subsidy and not a forecast. It
    is how the export path is exercised on the real tables rather than on a fixture: with
    the reference data as it stands the capture route never pays at any positive tariff
    (note 20 item 55), so a positive-tariff test would assert an all-zero column and prove
    nothing about the mechanism. What is asserted here is the mechanism — the sign in C8,
    the C9 window, and that an exported tonne is not a vented tonne — none of which
    depends on the price being realistic.
    """
    premise = load_premise_tables("mvp-cement")
    sets = build_sets(reference, premise, screen, PERIOD_YEARS)
    vintages = survival.vintage_capacity(premise, reference.unit)
    surviving = survival.surviving_capacity(vintages, reference.unit, PERIOD_YEARS)
    model = build.build_model(sets, surviving, axis, reference, tariff)
    result = build.solve(model)
    tables = ledger.build_ledger(result, sets, axis, reference, tariff)
    return Run("mvp-cement", sets, model, result, tables)


@pytest.fixture(scope="session")
def cement_exporting(
    reference: ReferenceTables, screen: AdmissionScreen, axis: build.PeriodAxis
) -> Run:
    return _cement_with_export(reference, screen, axis, -1000.0)


def test_the_export_variable_respects_c9_and_earliest_year_together(
    cement_exporting: Run,
) -> None:
    """Export is positive only where **both** gates are open, and they are different gates.

    C9 (infrastructure availability) opens ``humber`` at 2030; ``unit_eligibility``'s
    ``earliest_year`` holds ``ccs_amine`` shut until 2035. At an available cluster the
    eligibility gate binds first, which is worth stating plainly: the two are both live and
    the later one wins. Neither was applied before — C9 was out of the slice, and
    ``earliest_year`` never reached a unit with no duty.
    """
    assert cement_exporting.result.termination_condition == "optimal"
    mix = cement_exporting.tables.carrier_mix
    exported = {
        int(row.period): float(row.exported)
        for row in mix[mix["carrier_id"] == "co2_captured"].itertuples()
    }
    assert exported[2021] == pytest.approx(0.0, abs=TOLERANCE)
    assert exported[2025] == pytest.approx(0.0, abs=TOLERANCE)
    assert exported[2030] == pytest.approx(0.0, abs=TOLERANCE), (
        "C9 opens humber at 2030, but earliest_year holds ccs_amine until 2035"
    )
    assert exported[2035] > TOLERANCE
    assert exported[2050] > TOLERANCE


def test_exported_co2_is_not_vented_and_so_is_not_charged(cement_exporting: Run) -> None:
    """**The sign that inverts the result if it is got wrong.**

    §5.4 charges carbon on ``d_{c,t}``, what is vented. A tonne that left through the pipe
    is not vented, so it attracts nothing — that is the entire economic case for capture.
    The statement is algebraic rather than comparative on purpose: a subsidised run
    *raises* total emissions, because being paid per tonne captured makes producing more
    of them worth while, so "carbon falls" would be the wrong assertion and would fail for
    a right reason. What must hold at every node is that the charge lands on the disposal
    and on nothing else.

    At the ``co2_process`` node, production splits into what ``ccs_amine`` draws and what
    is vented. Only the vented half is charged, and ``co2_captured`` itself carries no
    disposal variable at all: §5.2 forbids disposing of a ``product``, so the pipe is the
    only way out and it is priced by the tariff rather than by the carbon price.
    """
    tables = cement_exporting.tables
    disposal = tables.disposal
    assert "co2_captured" not in set(disposal["carrier_id"]), (
        "co2_captured is a `product`; §5.2's may_dispose gate forbids a disposal variable "
        "for it, and one would be a second, uncharged way out of the model"
    )

    mix = tables.carrier_mix
    charged = {
        (row.carrier_id, int(row.period)): row
        for row in mix.itertuples()
        if row.carrier_id in {"co2_process", "co2_fuel_fossil"}
    }
    vented = {
        (row.carrier_id, int(row.period)): row
        for row in disposal.itertuples()
    }
    captured_somewhere = False
    for key, row in charged.items():
        node = vented[key]
        assert node.carbon_charge == "charged"
        # produced = captured + vented, and the charge is on the vented half alone.
        assert row.produced - row.consumed == pytest.approx(
            node.quantity, abs=TOLERANCE
        )
        assert node.carbon_cost == pytest.approx(
            node.quantity * 1e-3 * node.carbon_price, rel=1e-9
        )
        if row.consumed > TOLERANCE:
            captured_somewhere = True
    assert captured_somewhere, (
        "the subsidised run must draw some CO₂ into ccs_amine, or this asserts nothing"
    )


def test_c8_still_closes_at_every_node_with_the_export_term(cement_exporting: Run) -> None:
    """The matrix check of §5.4, re-run with x in the balance.

    Nothing here asks the solver whether it was right: A and b come from the built model
    and the residual is computed against the returned solution, so a carrier node whose
    export term carries the wrong sign is caught even when HiGHS reports ``optimal``.
    """
    violations = build.check_constraint_rows(
        cement_exporting.model, cement_exporting.result
    )
    assert violations == ()


def test_the_export_term_sums_into_the_reported_objective(cement_exporting: Run) -> None:
    """``cost_by_term`` has to sum to the objective, and the export term is a fifth row.

    It was also the first thing to break the sum: giving ``ccs_amine`` an activity variable
    made §5.4's biogenic credit live for the first time, and a ledger that omitted it was
    out by exactly the credit.
    """
    by_term = cement_exporting.tables.cost_by_term.groupby("term")["discounted"].sum()
    assert set(by_term.index) == set(ledger.COST_TERMS)
    assert float(by_term["export"]) < 0.0, "a negative tariff is a revenue, so the term is negative"
    assert float(by_term.sum()) == pytest.approx(
        cement_exporting.result.objective, rel=1e-9
    )


def test_export_unit_cost_is_the_tariff_less_the_export_price(
    reference: ReferenceTables,
) -> None:
    """§5.4 writes export as a revenue; §3.7 gives CO₂ a tariff. The unit cost is both.

    For ``co2_captured`` there is no ``export_price``, so the cost is the tariff alone and
    the objective term is positive — the site pays to be rid of it.
    """
    cost = build.export_unit_cost(reference, "co2_captured", PERIOD_YEARS)
    assert cost == [pytest.approx(40.0)] * len(PERIOD_YEARS), (
        "the synthetic co2_transport_tariff is £40/t flat across the horizon"
    )
    assert build.export_unit_cost(reference, "co2_captured", PERIOD_YEARS, 62.5) == [
        pytest.approx(62.5)
    ] * len(PERIOD_YEARS)


def test_an_export_with_no_price_at_all_fails_loud(reference: ReferenceTables) -> None:
    """The screen is the guard, and this is what happens if something gets past it.

    ``carb3.sets.export_windows`` refuses an unpriced carrier, so this path should be
    unreachable. It raises rather than returning zeros because a zero-cost export is free
    disposal, and a silent zero is the failure the §3.2 screen exists to prevent one table
    earlier.
    """
    with pytest.raises(ValueError, match="unpriced export is free disposal"):
        build.export_unit_cost(reference, "clinker", PERIOD_YEARS)
