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

#: The two premises that solve on the reference tables as they stand today.
SOLVING_PREMISES: tuple[str, ...] = ("mvp-minimal", "mvp-dairy")

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


def test_mvp_cement_is_blocked_by_a_duty_profile_with_no_mass_carrier(
    reference: ReferenceTables, screen: AdmissionScreen
) -> None:
    """**The third premise does not solve, and the cause is in the reference data.**

    ``mvp-cement`` exists to exercise the mass duty, the process CO₂ and the disposal term.
    Its ``cement_grinding`` process carries 1.130000 Mt/yr in ``known_capacity`` and
    ``premise_throughput.csv`` says of that row "this row is the premise's mass duty under
    D5". But the minimal A2 plan §3.3 specifies reads exactly two tables —
    ``activity_process_register`` and ``activity_process_duty_profile`` — and
    **``activity_process_duty_profile.csv`` contains no mass carrier anywhere**: its 427
    rows name 26 distinct ``carrier_id`` values and ``cement`` and ``clinker`` are not among
    them. ``Cement Works``'s ``cement_grinding`` row is classified ``MOT`` on
    ``motive_power``, so A2 derives a 1.130000 "PJ/yr" motive-power duty, and every grinder
    eligible for that process — ``grinder_mixer_elec`` and
    ``grinder_mixer_clinker_sub_elec``, both of which clear the §3.2 screen — has ``cement``
    as its primary output and cannot serve it.

    So the premise's README and ``sets.py`` disagree about where a D5 mass duty comes from,
    and neither is wrong on its own terms. Closing it is an A2 design decision — either the
    duty profile gains a ``cement`` row, or A2 learns to read ``premise_throughput`` — and
    it is recorded rather than guessed at here.

    This asserts the diagnosis, not the failure: the point is that §5.2's pre-solve check
    names the duty and the period instead of letting the LP be built and quietly under-met.
    """
    premise = load_premise_tables("mvp-cement")
    sets = build_sets(reference, premise, screen, PERIOD_YEARS)
    unservable = diagnose_unservable_duties(sets, screen)

    assert {row.duty for row in unservable} == {
        ("mvp-cement", "cement_grinding", "motive_power")
    }
    assert {row.period for row in unservable} == set(PERIOD_YEARS)

    profile = reference.activity_process_duty_profile
    assert "cement" not in set(profile["carrier_id"]), (
        "activity_process_duty_profile now carries a `cement` row, so the minimal A2 can "
        "derive mvp-cement's mass duty and this test should be replaced by a solve"
    )


def test_mvp_cement_kilns_take_an_internal_supply_column(
    reference: ReferenceTables, screen: AdmissionScreen
) -> None:
    """D16 removes the kiln's duty row; something still has to give it a variable.

    Note 21 §2.2 puts z° out of scope because there are "no internal ``product`` carriers
    in the synthetic premises", which is false — ``clinker`` is one — and then says C8
    pins the kiln through the ``clinker`` balance, which a unit with no variable cannot be.
    :func:`carb3.sets.internal_supply` supplies the set and
    :func:`carb3.build._dispatch_pairs` gives each member a column that C1 does not select.

    ``ccs_amine`` is deliberately absent: its ``co2_captured`` is ``may_export`` true, so it
    is not an internal product, and with export out of the slice C8 would pin it to zero.
    """
    premise = load_premise_tables("mvp-cement")
    sets = build_sets(reference, premise, screen, PERIOD_YEARS)

    assert sets.supply == {"clinker": frozenset({"kiln_dry_coal", "kiln_dry_gas"})}
    assert "ccs_amine" not in {u for units in sets.supply.values() for u in units}

    # The LP cannot be built while cement_grinding is unservable, so the column is checked
    # on the same sets with that duty removed. Everything else about them is the real thing.
    buildable = dataclasses.replace(
        sets, duties=tuple(duty for duty in sets.duties if sets.eligible[duty.key])
    )
    supply_columns = {
        pair.unit_id for pair in build._dispatch_pairs(buildable) if pair.duty_key is None
    }
    assert supply_columns == {"kiln_dry_coal", "kiln_dry_gas"}


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


@pytest.mark.parametrize("premise_id", SOLVING_PREMISES)
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
def test_the_carbon_term_equals_the_disposal_table_charge(
    runs: dict[str, Run], premise_id: str
) -> None:
    """The two tables are computed from the same solution and must not drift apart."""
    run = runs[premise_id]
    costs = run.tables.cost_by_term
    carbon = costs[costs["term"] == "carbon"].set_index("period")["annual"]
    charged = (
        run.tables.disposal.groupby("period")["carbon_cost"].sum().reindex(carbon.index)
    )
    assert (carbon - charged).abs().max() < TOLERANCE


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


def test_the_cli_runs_every_premise_and_reports_the_one_that_does_not_solve(
    tmp_path: Path, capsys
) -> None:
    """``python -m carb3`` end to end, including the premise that cannot be built.

    A blocked premise must not stop the others: the exit status says how many failed and
    the report carries every premise's section either way.
    """
    from carb3.__main__ import main

    status = main(["--out-dir", str(tmp_path)])
    captured = capsys.readouterr().out

    assert status == 1, "mvp-cement does not solve, so the run must not report success"
    for premise_id in (*SOLVING_PREMISES, "mvp-cement"):
        assert f"premise {premise_id}" in captured
    assert "NOT SOLVED" in captured
    assert "cement_grinding on motive_power" in captured
    assert "§3.2 admission screen" in captured
    assert "objective decomposition" in captured
    assert "2 of 3 premises solved to optimality" in captured

    for premise_id in SOLVING_PREMISES:
        assert (tmp_path / premise_id / "cost_by_term.parquet").is_file()
        assert (tmp_path / premise_id / "disposal.parquet").is_file()
    assert not (tmp_path / "mvp-cement").exists()
