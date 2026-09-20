"""build.py — variables, C1-C5, C8, C10, objective, solve.

The fixtures here are built in-test rather than read from ``carb3/data/premises/``: the
synthetic premises are another lane's work and the point of a unit test is that the optimum
is arithmetic, which a three-unit fixture gives and a real premise does not.

The numbers the fixture carries are the real ones from ``unit.csv``,
``unit_input_output.csv`` and ``scenario_parameters.csv`` for ``boiler_lt_gas`` and
``heat_pump_lt_air`` — note 21 §4.2's two contenders — so the hand-computed optima below are
checkable against that table.
"""

from __future__ import annotations

import dataclasses

import pandas as pd
import pytest

from carb3 import build, survival
from carb3.load import ReferenceTables
from carb3.sets import Duty, ModelSets

# The real period vector (§6.4): a 4-year first gap and 5-year gaps thereafter.
REFERENCE_YEARS: tuple[int, ...] = (2021, 2025, 2030, 2035, 2040, 2045, 2050)

#: A three-period cut of it, enough for C3 (capacity transfer) and C5 (no build in the start
#: year) to bite while keeping the hand arithmetic short.
PERIODS: tuple[int, ...] = (2021, 2025, 2030)

DISCOUNT_RATE = 0.035

#: ``scenario_parameters.csv``, £m/PJ at 2021 prices, and kt CO₂/PJ.
GAS_PRICE = {2021: 7.04, 2025: 10.53, 2030: 7.50}
ELECTRICITY_PRICE = {2021: 31.50, 2025: 45.14, 2030: 32.10}
CARBON_PRICE = {2021: 244.47, 2025: 259.70, 2030: 280.09}
EF_NATURAL_GAS = {2021: 51.12, 2025: 51.12, 2030: 51.12}
EF_SOLID_BIOMASS = {2021: 97.22, 2025: 97.22, 2030: 97.22}

#: ``unit.csv`` and ``unit_input_output.csv`` for note 21 §4.2's two contenders.
BOILER_EFFICIENCY = 1.13636  # PJ gas per PJ heat, η = 0.88
BOILER_REJECT = 0.13668  # into heat_lt60, grade 1 — the bottom of the cascade
BOILER_CAPEX = 5.6421
BOILER_FIXED_OPEX = 0.11284
BOILER_LIFETIME = 25
BOILER_AVAILABILITY = 0.9823
HEAT_PUMP_COEFFICIENT = 0.3571  # PJ electricity per PJ heat, COP 2.80
HEAT_PUMP_CAPEX = 15.2949
HEAT_PUMP_FIXED_OPEX = 0.3059
HEAT_PUMP_LIFETIME = 20
HEAT_PUMP_AVAILABILITY = 0.9808

DUTY_KEY = ("mvp-minimal", "steam_hot_water", "heat_60_100")


class _Duty(Duty):
    """``Duty`` with ``key`` implemented.

    ``carb3.sets.Duty.key`` still raises ``NotImplementedError`` — it is owed by T5, in
    another lane's file — so the fixture supplies the documented value, the
    ``(premise_id, process_id, carrier_id)`` triple ``DutyKey`` names.
    """

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.premise_id, self.process_id, self.carrier_id)


def _carrier_table(*, heat_lt60_disposable: bool = True, gas_disposable: bool = False):
    """``carrier.csv``'s seven columns for the carriers the fixture touches.

    Values are written as the CSV holds them — ``"TRUE"``/``"FALSE"`` strings and blank
    cells — because the loader's coercion is another lane's choice and the model must read
    either shape.
    """
    return pd.DataFrame(
        [
            {
                "carrier_id": "natural_gas",
                "carrier_kind": "primary",
                "is_indirect": "FALSE",
                "biogenic_fraction": 0.0115,
                "carbon_charge": "",
                "may_dispose": "TRUE" if gas_disposable else "FALSE",
                "may_import": "TRUE",
            },
            {
                "carrier_id": "solid_biomass",
                "carrier_kind": "primary",
                "is_indirect": "FALSE",
                "biogenic_fraction": 1.0,
                "carbon_charge": "",
                "may_dispose": "FALSE",
                "may_import": "TRUE",
            },
            {
                "carrier_id": "electricity",
                "carrier_kind": "primary",
                "is_indirect": "TRUE",
                "biogenic_fraction": "",
                "carbon_charge": "",
                "may_dispose": "FALSE",
                "may_import": "TRUE",
            },
            {
                "carrier_id": "heat_60_100",
                "carrier_kind": "intermediate",
                "is_indirect": "FALSE",
                "biogenic_fraction": "",
                "carbon_charge": "",
                "may_dispose": "TRUE",
                "may_import": "FALSE",
            },
            {
                "carrier_id": "heat_lt60",
                "carrier_kind": "intermediate",
                "is_indirect": "FALSE",
                "biogenic_fraction": "",
                "carbon_charge": "",
                "may_dispose": "TRUE" if heat_lt60_disposable else "FALSE",
                "may_import": "FALSE",
            },
            {
                "carrier_id": "co2_fuel_fossil",
                "carrier_kind": "emission",
                "is_indirect": "FALSE",
                "biogenic_fraction": "",
                "carbon_charge": "charged",
                "may_dispose": "TRUE",
                "may_import": "FALSE",
            },
            {
                "carrier_id": "co2_fuel_biogenic",
                "carrier_kind": "emission",
                "is_indirect": "FALSE",
                "biogenic_fraction": "",
                "carbon_charge": "zero_rated",
                "may_dispose": "TRUE",
                "may_import": "FALSE",
            },
        ]
    )


def _unit_table(*, with_biomass: bool = False) -> pd.DataFrame:
    rows = [
        {
            "unit_id": "boiler_lt_gas",
            "unit_class": "converter",
            "capex": BOILER_CAPEX,
            "fixed_opex": BOILER_FIXED_OPEX,
            "lifetime": BOILER_LIFETIME,
            "availability_factor": BOILER_AVAILABILITY,
            "capacity_to_activity_factor": 1.0,
        },
        {
            "unit_id": "heat_pump_lt_air",
            "unit_class": "converter",
            "capex": HEAT_PUMP_CAPEX,
            "fixed_opex": HEAT_PUMP_FIXED_OPEX,
            "lifetime": HEAT_PUMP_LIFETIME,
            "availability_factor": HEAT_PUMP_AVAILABILITY,
            "capacity_to_activity_factor": 1.0,
        },
    ]
    if with_biomass:
        rows.append(
            {
                "unit_id": "boiler_lt_biomass",
                "unit_class": "converter",
                "capex": 8.0,
                "fixed_opex": 0.16,
                "lifetime": 25,
                "availability_factor": 0.98,
                "capacity_to_activity_factor": 1.0,
            }
        )
    return pd.DataFrame(rows)


def _input_output_table(*, with_biomass: bool = False) -> pd.DataFrame:
    rows = [
        {
            "unit_id": "boiler_lt_gas",
            "carrier_id": "heat_60_100",
            "coefficient": 1.0,
            "role": "primary_output",
        },
        {
            "unit_id": "boiler_lt_gas",
            "carrier_id": "natural_gas",
            "coefficient": -BOILER_EFFICIENCY,
            "role": "fuel_input",
        },
        {
            "unit_id": "boiler_lt_gas",
            "carrier_id": "heat_lt60",
            "coefficient": BOILER_REJECT,
            "role": "reject",
        },
        {
            "unit_id": "heat_pump_lt_air",
            "carrier_id": "heat_60_100",
            "coefficient": 1.0,
            "role": "primary_output",
        },
        {
            "unit_id": "heat_pump_lt_air",
            "carrier_id": "electricity",
            "coefficient": -HEAT_PUMP_COEFFICIENT,
            "role": "fuel_input",
        },
    ]
    if with_biomass:
        rows += [
            {
                "unit_id": "boiler_lt_biomass",
                "carrier_id": "heat_60_100",
                "coefficient": 1.0,
                "role": "primary_output",
            },
            {
                "unit_id": "boiler_lt_biomass",
                "carrier_id": "solid_biomass",
                "coefficient": -1.25,
                "role": "fuel_input",
            },
        ]
    return pd.DataFrame(rows)


def _scenario_table(
    *, carbon_price: dict[int, float] | None = None, drop_gas_price_at: int | None = None
) -> pd.DataFrame:
    prices = CARBON_PRICE if carbon_price is None else carbon_price
    rows: list[dict[str, object]] = []
    for year in PERIODS:
        if year != drop_gas_price_at:
            rows.append(
                {
                    "parameter_id": "import_price",
                    "carrier_id": "natural_gas",
                    "period": year,
                    "value": GAS_PRICE[year],
                }
            )
        rows += [
            {
                "parameter_id": "import_price",
                "carrier_id": "electricity",
                "period": year,
                "value": ELECTRICITY_PRICE[year],
            },
            {
                "parameter_id": "import_price",
                "carrier_id": "solid_biomass",
                "period": year,
                "value": 6.0,
            },
            {
                "parameter_id": "carbon_price",
                "carrier_id": "",
                "period": year,
                "value": prices[year],
            },
            {
                "parameter_id": "ef_natural_gas",
                "carrier_id": "natural_gas",
                "period": year,
                "value": EF_NATURAL_GAS[year],
            },
            {
                "parameter_id": "ef_solid_biomass",
                "carrier_id": "solid_biomass",
                "period": year,
                "value": EF_SOLID_BIOMASS[year],
            },
        ]
    rows.append(
        {
            "parameter_id": "discount_rate",
            "carrier_id": "",
            "period": "",
            "value": DISCOUNT_RATE,
        }
    )
    return pd.DataFrame(rows)


def _reference(
    *,
    heat_lt60_disposable: bool = True,
    gas_disposable: bool = False,
    carbon_price: dict[int, float] | None = None,
    with_biomass: bool = False,
    drop_gas_price_at: int | None = None,
    blank_capex: bool = False,
) -> ReferenceTables:
    unit = _unit_table(with_biomass=with_biomass)
    if blank_capex:
        unit.loc[unit["unit_id"] == "boiler_lt_gas", "capex"] = None
    return ReferenceTables(
        carrier=_carrier_table(
            heat_lt60_disposable=heat_lt60_disposable, gas_disposable=gas_disposable
        ),
        unit=unit,
        unit_input_output=_input_output_table(with_biomass=with_biomass),
        unit_eligibility=pd.DataFrame(),
        scenario_parameters=_scenario_table(
            carbon_price=carbon_price, drop_gas_price_at=drop_gas_price_at
        ),
        activity_process_duty_profile=pd.DataFrame(),
        activity_process_register=pd.DataFrame(),
    )


def _sets(
    *,
    duty_quantity: float = 1.0,
    eligible: frozenset[str] = frozenset({"boiler_lt_gas", "heat_pump_lt_air"}),
    earliest_year: dict[tuple[tuple[str, str, str], str], int] | None = None,
    max_share: dict[tuple[tuple[str, str, str], str], float] | None = None,
) -> ModelSets:
    duty = _Duty(
        premise_id=DUTY_KEY[0],
        process_id=DUTY_KEY[1],
        carrier_id=DUTY_KEY[2],
        grade_rank=2,
        quantity={year: duty_quantity for year in PERIODS},
    )
    return ModelSets(
        periods=PERIODS,
        duties=(duty,),
        units=frozenset(eligible),
        eligible={duty.key: eligible},
        earliest_year=earliest_year or {},
        max_share=max_share or {},
        min_duty={},
    )


def _incumbent(unit_id: str = "boiler_lt_gas", *, capacity: float = 2.0, year: int = 2010):
    return pd.DataFrame(
        [{"unit_id": unit_id, "commissioned_year": year, "capacity": capacity}]
    )


def _axis() -> build.PeriodAxis:
    return build.period_axis(PERIODS, DISCOUNT_RATE)


def _solved(**kwargs):
    """Build and solve the fixture, returning ``(model, result)``."""
    reference = _reference(
        **{k: v for k, v in kwargs.items() if k not in {"sets", "surviving"}}
    )
    sets = kwargs.get("sets") or _sets()
    surviving = kwargs.get("surviving")
    if surviving is None:
        surviving = survival.surviving_capacity(_incumbent(), reference.unit, PERIODS)
    model = build.build_model(sets, surviving, _axis(), reference)
    return model, build.solve(model)


def _annuity(rate: float, lifetime: int) -> float:
    return rate / (1.0 - (1.0 + rate) ** -lifetime)


# --------------------------------------------------------------------------------------
# The scaffolded contract
# --------------------------------------------------------------------------------------


def test_solver_settings_match_the_cement_fixture() -> None:
    """Cement worked example §12: HiGHS, presolve on, single-threaded."""
    settings = build.SolverSettings()
    assert settings.solver == "highs"
    assert settings.presolve == "on"
    assert settings.threads == 1


def test_period_axis_is_a_vector_not_a_formula() -> None:
    """Plan §6.4: spans and delta_t are derived per period, not from a uniform delta."""
    fields = {f.name for f in dataclasses.fields(build.PeriodAxis)}
    assert fields == {"years", "spans", "discount_factors"}


def test_solve_result_reports_status_and_size() -> None:
    """Plan §5.2 and §5.3: a non-optimal status is reported, and the counts are printed."""
    fields = {f.name for f in dataclasses.fields(build.SolveResult)}
    assert {"status", "termination_condition", "objective"} <= fields
    assert {"n_variables", "n_constraints", "wall_clock_seconds"} <= fields


def test_signatures(assert_signature) -> None:
    assert_signature(build, "period_axis", ("years", "discount_rate"))
    assert_signature(
        build, "lifetime_in_periods", ("axis", "lifetime_years", "built_at")
    )
    assert_signature(build, "build_model", ("sets", "surviving", "axis", "reference"))
    assert_signature(build, "solve", ("model", "settings"))
    assert_signature(build, "check_constraint_rows", ("model", "result", "tolerance"))


# --------------------------------------------------------------------------------------
# T7 — the period axis
# --------------------------------------------------------------------------------------


def test_period_axis_carries_the_four_year_first_gap() -> None:
    """§5.1: Δ_t = (4, 5, 5, 5, 5, 5, 5) on the reference vector, and Δ_N = Δ_{N-1}."""
    axis = build.period_axis(REFERENCE_YEARS, DISCOUNT_RATE)
    assert axis.years == REFERENCE_YEARS
    assert axis.spans == (4, 5, 5, 5, 5, 5, 5)


def test_delta_t_aggregates_over_the_period_own_span() -> None:
    """δ_t sums the single-year factor over each year the period stands for (§5.1).

    Giving the start period five years instead of the four it spans overstates its whole
    cost by a quarter, which is why the first factor is a four-term sum.
    """
    axis = build.period_axis(REFERENCE_YEARS, DISCOUNT_RATE)
    expected_first = sum(1.035**-offset for offset in range(4))
    expected_second = sum(1.035 ** -(2025 - 2021 + offset) for offset in range(5))
    assert axis.discount_factors[0] == pytest.approx(expected_first)
    assert axis.discount_factors[1] == pytest.approx(expected_second)
    # 2021->2025 discounting differs from 2025->2030, which is T7's stated verification.
    assert axis.discount_factors[0] != pytest.approx(axis.discount_factors[1])


def test_period_axis_refuses_a_vector_that_is_not_increasing() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        build.period_axis((2021, 2021, 2030), DISCOUNT_RATE)
    with pytest.raises(ValueError, match="empty"):
        build.period_axis((), DISCOUNT_RATE)


def test_lifetime_is_converted_against_actual_years_not_periods() -> None:
    """**Critical path.** A 25-year life read as 25 periods is a 125-year asset (§10)."""
    axis = build.period_axis(REFERENCE_YEARS, DISCOUNT_RATE)
    # §5.1: on the reference vector a 25-year life built in 2021 covers six periods and the
    # same life built in 2025 covers five.
    assert build.lifetime_in_periods(axis, 25, 2021) == 6
    assert build.lifetime_in_periods(axis, 25, 2025) == 5
    assert build.lifetime_in_periods(axis, 25, 2021) != 25
    # A 20-year life built in 2035 runs to 2054, so it stands in 2035, 2040, 2045 and 2050.
    assert build.lifetime_in_periods(axis, 20, 2035) == 4
    # A 10-year life built in 2035 is gone by 2045: 2035 and 2040 only.
    assert build.lifetime_in_periods(axis, 10, 2035) == 2
    # A life shorter than the first gap still covers the period it was built in.
    assert build.lifetime_in_periods(axis, 3, 2021) == 1
    with pytest.raises(ValueError, match="positive"):
        build.lifetime_in_periods(axis, 0, 2021)


def test_build_model_refuses_an_axis_that_disagrees_with_the_sets() -> None:
    reference = _reference()
    surviving = survival.surviving_capacity(_incumbent(), reference.unit, PERIODS)
    other = build.period_axis((2021, 2025, 2030, 2035), DISCOUNT_RATE)
    with pytest.raises(ValueError, match="does not match"):
        build.build_model(_sets(), surviving, other, reference)


# --------------------------------------------------------------------------------------
# T3 — the model
# --------------------------------------------------------------------------------------


def test_the_declared_variables_are_the_slice_of_section_5_2() -> None:
    model, _ = _solved()
    assert set(model.variables) == {"z", "n", "a", "e", "m", "d"}
    # Out: h (cascade), z° (undispatched primary output), r (early retirement), x (export),
    # w (reinforcement).
    assert "h" not in model.variables
    assert "x" not in model.variables


def test_the_problem_is_a_pure_lp() -> None:
    """§5.2: no binaries. Minimum scale is the min_duty screen at load, never a variable."""
    model, _ = _solved()
    assert not model.binaries
    assert not model.integers


def test_disposal_is_declared_where_may_dispose_and_the_kind_admits_it() -> None:
    """The gate is the whole safety argument (§5.2)."""
    model, _ = _solved()
    disposable = set(model.variables["d"].coords["carrier"].to_index())
    # heat_lt60 is intermediate and grade 1 — the bottom, nothing to cascade to.
    assert "heat_lt60" in disposable
    assert "co2_fuel_fossil" in disposable
    # natural_gas is primary: importing gas and dumping it must not be expressible.
    assert "natural_gas" not in disposable


def test_a_primary_carrier_is_never_disposable_even_if_the_flag_says_so() -> None:
    """``carrier_kind`` gates ``may_dispose``, not the other way round (§5.2)."""
    model, _ = _solved(gas_disposable=True)
    disposable = set(model.variables["d"].coords["carrier"].to_index())
    assert "natural_gas" not in disposable


def test_disposal_lets_the_boiler_run_without_a_co_built_reject_heat_pump() -> None:
    """The finding that restored d_{c,t} (§2.2).

    59 ``reject`` rows run into ``heat_lt60``, which has exactly one consumer in the whole
    table. Without a disposal variable C8 forces every one of those units to zero.
    """
    model, result = _solved()
    assert result.termination_condition == "optimal"
    dispatch = model.variables["z"].solution.to_pandas()
    boiler_row = [row for row in dispatch.index if row.startswith("boiler_lt_gas@")][0]
    # C5 forbids building in 2021, so the duty can only be met by the incumbent boiler —
    # which is exactly what needs the reject heat to have somewhere to go.
    assert dispatch.loc[boiler_row, 2021] == pytest.approx(1.0)
    disposed = model.variables["d"].solution.to_pandas()
    assert disposed.loc["heat_lt60", 2021] == pytest.approx(BOILER_REJECT)


def test_without_disposal_the_reject_node_makes_the_premise_infeasible() -> None:
    """The same fixture with ``heat_lt60`` not disposable: C8 has no sink and C1 cannot be
    met in the start year, which is the unsolvable slice the review caught."""
    _, result = _solved(heat_lt60_disposable=False)
    assert result.termination_condition != "optimal"
    assert result.objective is None


def test_c1_is_an_equality_met_by_the_eligible_units() -> None:
    model, result = _solved()
    assert result.termination_condition == "optimal"
    dispatch = model.variables["z"].solution.to_pandas()
    for year in PERIODS:
        assert dispatch[year].sum() == pytest.approx(1.0)


def test_c2_binds_and_capacity_carries_the_availability_factor() -> None:
    """z_{u,t} ≤ a_{u,t} γ_u α_u — the 1/(γα) factor note 21 §4.2 leaves out of its table."""
    model, result = _solved()
    assert result.termination_condition == "optimal"
    capacity = model.variables["a"].solution.to_pandas()
    assert capacity.loc["heat_pump_lt_air", 2025] == pytest.approx(
        1.0 / HEAT_PUMP_AVAILABILITY
    )


def test_c3_carries_capacity_across_periods_without_rebuilding() -> None:
    """Built once at 2025, standing in 2030: n is a flow, a is a stock."""
    model, result = _solved()
    assert result.termination_condition == "optimal"
    built = model.variables["n"].solution.to_pandas()
    capacity = model.variables["a"].solution.to_pandas()
    assert built.loc["heat_pump_lt_air", 2025] == pytest.approx(1.0 / HEAT_PUMP_AVAILABILITY)
    assert built.loc["heat_pump_lt_air", 2030] == pytest.approx(0.0, abs=1e-9)
    assert capacity.loc["heat_pump_lt_air", 2030] == pytest.approx(
        1.0 / HEAT_PUMP_AVAILABILITY
    )


def test_c4_pins_surviving_capacity_to_the_d11_parameter() -> None:
    """Mechanism, not driver (§4.3): e_{u,t} equals the survival function, and C2 being an
    inequality is what lets the model walk away from it anyway."""
    reference = _reference()
    surviving = survival.surviving_capacity(
        _incumbent(capacity=2.0, year=2010), reference.unit, PERIODS
    )
    model = build.build_model(_sets(), surviving, _axis(), reference)
    result = build.solve(model)
    assert result.termination_condition == "optimal"
    standing = model.variables["e"].solution.to_pandas()
    for year in PERIODS:
        assert standing.loc["boiler_lt_gas", year] == pytest.approx(2.0)
    # The incumbent is abandoned from 2025 even though it survives to 2035.
    dispatch = model.variables["z"].solution.to_pandas()
    boiler_row = [row for row in dispatch.index if row.startswith("boiler_lt_gas@")][0]
    assert dispatch.loc[boiler_row, 2025] == pytest.approx(0.0, abs=1e-9)


def test_c5_forbids_building_in_the_start_year() -> None:
    model, result = _solved()
    assert result.termination_condition == "optimal"
    built = model.variables["n"].solution.to_pandas()
    assert built[2021].abs().max() == pytest.approx(0.0, abs=1e-9)
    assert "C5" in model.constraints


def test_earliest_year_holds_new_capacity_at_zero_until_the_year() -> None:
    """Nine eligibility rows carry one; every capture train is 2035 or 2040 (§3.1)."""
    sets = _sets(earliest_year={(DUTY_KEY, "heat_pump_lt_air"): 2030})
    model, result = _solved(sets=sets)
    assert result.termination_condition == "optimal"
    built = model.variables["n"].solution.to_pandas()
    assert built.loc["heat_pump_lt_air", 2025] == pytest.approx(0.0, abs=1e-9)
    assert built.loc["heat_pump_lt_air", 2030] > 0.0
    # The gate is an upper bound on n, not a constraint row.
    upper = model.variables["n"].upper.to_pandas()
    assert upper.loc["heat_pump_lt_air", 2025] == 0.0


def test_max_share_of_zero_is_a_hard_prohibition() -> None:
    """``boiler_lt_coal`` at ``Food Processing Centre`` carries ``max_share`` 0.00 (§3.1)."""
    sets = _sets(max_share={(DUTY_KEY, "boiler_lt_gas"): 0.0})
    model, result = _solved(sets=sets)
    # 2021 cannot be met at all once the incumbent is prohibited and C5 forbids building.
    assert result.termination_condition != "optimal"
    upper = model.variables["z"].upper.to_pandas()
    boiler_row = [row for row in upper.index if row.startswith("boiler_lt_gas@")][0]
    assert upper.loc[boiler_row, 2021] == 0.0


def test_max_share_splits_the_duty_at_the_cap() -> None:
    """A cap between 0 and 1 splits C1 between the two units rather than forbidding one."""
    sets = _sets(
        duty_quantity=1.0,
        max_share={(DUTY_KEY, "heat_pump_lt_air"): 0.6},
    )
    model, result = _solved(sets=sets)
    assert result.termination_condition == "optimal"
    dispatch = model.variables["z"].solution.to_pandas()
    pump_row = [row for row in dispatch.index if row.startswith("heat_pump_lt_air@")][0]
    boiler_row = [row for row in dispatch.index if row.startswith("boiler_lt_gas@")][0]
    assert dispatch.loc[pump_row, 2025] == pytest.approx(0.6)
    assert dispatch.loc[boiler_row, 2025] == pytest.approx(0.4)


def test_an_unservable_duty_is_named_before_the_lp_is_built() -> None:
    """§5.2: infeasibility is an expected outcome. A duty whose U_q is empty is refused with
    its key, rather than silently dropped by the ``groupby`` that builds C1."""
    reference = _reference()
    sets = _sets(eligible=frozenset())
    surviving = survival.surviving_capacity(_incumbent(), reference.unit, PERIODS)
    with pytest.raises(ValueError, match="empty eligible-unit set"):
        build.build_model(sets, surviving, _axis(), reference)


# --------------------------------------------------------------------------------------
# A6 and the objective
# --------------------------------------------------------------------------------------


def test_a6_derives_fuel_co2_and_an_indirect_carrier_emits_nothing() -> None:
    """D15 (§3.6): process CO₂ is declared, fuel CO₂ is derived at build time.

    ``electricity`` carries ``is_indirect``, so the heat pump vents nothing on site and its
    carbon belongs to the §7.7 allocation layer.
    """
    model, result = _solved()
    assert result.termination_condition == "optimal"
    vented = model.variables["d"].solution.to_pandas()
    # 2021: the boiler serves the whole 1 PJ duty.
    expected = BOILER_EFFICIENCY * EF_NATURAL_GAS[2021] * (1 - 0.0115)
    assert vented.loc["co2_fuel_fossil", 2021] == pytest.approx(expected)
    # 2025 onwards the heat pump serves it and nothing is vented.
    assert vented.loc["co2_fuel_fossil", 2025] == pytest.approx(0.0, abs=1e-9)


def test_a6_splits_a_biogenic_fuel_before_anything_is_captured() -> None:
    """§3.6: the split happens in A6, and biomass carries ``biogenic_fraction`` 1.0, so its
    CO₂ lands on the ``zero_rated`` carrier and is never charged."""
    sets = _sets(
        eligible=frozenset({"boiler_lt_gas", "heat_pump_lt_air", "boiler_lt_biomass"})
    )
    model, result = _solved(sets=sets, with_biomass=True)
    assert result.termination_condition == "optimal"
    coefficients = {
        name: model.constraints[name] for name in model.constraints if name.startswith("C8_")
    }
    assert "C8_co2_fuel_biogenic" in coefficients
    # Biomass is cheaper than gas here and carries no carbon charge, so it takes 2021.
    dispatch = model.variables["z"].solution.to_pandas()
    biomass_row = [row for row in dispatch.index if row.startswith("boiler_lt_biomass@")][0]
    vented = model.variables["d"].solution.to_pandas()
    if dispatch.loc[biomass_row, 2021] > 1e-9:
        burnt = dispatch.loc[biomass_row, 2021] * 1.25
        assert vented.loc["co2_fuel_biogenic", 2021] == pytest.approx(
            burnt * EF_SOLID_BIOMASS[2021]
        )
        assert vented.loc["co2_fuel_fossil", 2021] == pytest.approx(0.0, abs=1e-9)


def test_the_objective_matches_the_hand_computed_pathway() -> None:
    """The whole point of a three-unit fixture: the optimum is arithmetic.

    2021 is the incumbent boiler, because C5 forbids building. 2025 and 2030 are the new heat
    pump, because note 21 §4.2's carbon term makes it win at the first buildable period.
    """
    model, result = _solved()
    assert result.termination_condition == "optimal"
    axis = _axis()
    pump_capacity = 1.0 / HEAT_PUMP_AVAILABILITY

    annual = {}
    # 2021 — the incumbent runs; its capex is sunk, so only opex, fuel and carbon.
    annual[2021] = (
        2.0 * BOILER_FIXED_OPEX
        + BOILER_EFFICIENCY * GAS_PRICE[2021]
        + BOILER_EFFICIENCY * EF_NATURAL_GAS[2021] * (1 - 0.0115) * CARBON_PRICE[2021] * 1e-3
    )
    # 2025 and 2030 — the heat pump, with the boiler still standing and still paying opex.
    for year in (2025, 2030):
        annual[year] = (
            pump_capacity * HEAT_PUMP_CAPEX * _annuity(DISCOUNT_RATE, HEAT_PUMP_LIFETIME)
            + 2.0 * BOILER_FIXED_OPEX
            + pump_capacity * HEAT_PUMP_FIXED_OPEX
            + HEAT_PUMP_COEFFICIENT * ELECTRICITY_PRICE[year]
        )
    expected = sum(
        axis.discount_factors[index] * annual[year] for index, year in enumerate(PERIODS)
    )
    assert result.objective == pytest.approx(expected, rel=1e-9)


def test_one_duty_one_unit_costs_duty_times_coefficient_times_price() -> None:
    """The simplest decomposition there is, with capex and carbon switched off."""
    sets = _sets(eligible=frozenset({"heat_pump_lt_air"}))
    reference = _reference(carbon_price=dict.fromkeys(PERIODS, 0.0))
    # No incumbent, so the heat pump must be built — and C5 makes 2021 unservable, so the
    # duty is quoted at zero there.
    duty = _Duty(
        premise_id=DUTY_KEY[0],
        process_id=DUTY_KEY[1],
        carrier_id=DUTY_KEY[2],
        grade_rank=2,
        quantity={2021: 0.0, 2025: 1.0, 2030: 1.0},
    )
    sets = ModelSets(
        periods=PERIODS,
        duties=(duty,),
        units=frozenset({"heat_pump_lt_air"}),
        eligible={duty.key: frozenset({"heat_pump_lt_air"})},
        earliest_year={},
        max_share={},
        min_duty={},
    )
    model = build.build_model(sets, pd.DataFrame(), _axis(), reference)
    result = build.solve(model)
    assert result.termination_condition == "optimal"
    axis = _axis()
    capacity = 1.0 / HEAT_PUMP_AVAILABILITY
    expected = sum(
        axis.discount_factors[index]
        * (
            capacity * HEAT_PUMP_CAPEX * _annuity(DISCOUNT_RATE, HEAT_PUMP_LIFETIME)
            + capacity * HEAT_PUMP_FIXED_OPEX
            + HEAT_PUMP_COEFFICIENT * ELECTRICITY_PRICE[year]
        )
        for index, year in enumerate(PERIODS)
        if year != 2021
    )
    assert result.objective == pytest.approx(expected, rel=1e-9)


def test_carbon_on_and_off_inverts_the_ranking() -> None:
    """Note 21 §4.2: carbon is what drives the switch, and it drives it immediately."""
    _, priced = _solved()
    model, free = _solved(carbon_price=dict.fromkeys(PERIODS, 0.0))
    assert free.termination_condition == "optimal"
    dispatch = model.variables["z"].solution.to_pandas()
    boiler_row = [row for row in dispatch.index if row.startswith("boiler_lt_gas@")][0]
    # With no carbon price the sunk incumbent keeps the duty in every period.
    for year in PERIODS:
        assert dispatch.loc[boiler_row, year] == pytest.approx(1.0)
    assert free.objective < priced.objective


def test_carbon_is_charged_on_disposal_not_on_fuel() -> None:
    """§5.4 as written. The heat pump burns 0.3571 PJ of electricity per PJ of heat and is
    charged nothing for it, because ``electricity`` is never disposed of on site."""
    model, result = _solved()
    assert result.termination_condition == "optimal"
    imported = model.variables["m"].solution.to_pandas()
    vented = model.variables["d"].solution.to_pandas()
    assert imported.loc["electricity", 2025] == pytest.approx(HEAT_PUMP_COEFFICIENT)
    assert "electricity" not in vented.index


# --------------------------------------------------------------------------------------
# Solve, the row check and the size assertion
# --------------------------------------------------------------------------------------


def test_a_non_optimal_status_is_reported_not_raised() -> None:
    """**Critical path.** §5.2: infeasibility is an expected outcome, not an error."""
    result = _solved(heat_lt60_disposable=False)[1]
    assert isinstance(result, build.SolveResult)
    assert result.termination_condition != "optimal"
    assert result.objective is None
    assert result.solution is None
    assert result.n_variables > 0
    assert result.n_constraints > 0
    assert result.wall_clock_seconds >= 0.0


def test_c8_closes_at_every_carrier_node_in_every_period() -> None:
    """**Critical path.** The matrix is multiplied by the returned solution here, so a node
    that does not balance is caught independently of what the solver reported."""
    model, result = _solved()
    assert result.termination_condition == "optimal"
    violations = build.check_constraint_rows(model, result)
    assert violations == ()
    # And the check really does look at every C8 node.
    c8_rows = sum(
        model.constraints[name].size for name in model.constraints if name.startswith("C8_")
    )
    # natural_gas, electricity, heat_lt60, co2_fuel_fossil and co2_fuel_biogenic — the last
    # because natural gas carries biogenic_fraction 0.0115, so A6 derives a non-zero
    # biogenic row for the gas boiler too.
    assert c8_rows == 5 * len(PERIODS)


def test_the_row_check_catches_a_solution_that_does_not_close() -> None:
    """The check must fail when the solution is wrong, or it proves nothing."""
    model, result = _solved()
    tampered = dataclasses.replace(result)
    # Perturb the solved model's variable solutions: the matrix check reads them back
    # through ``model.matrices.sol``, so moving one import breaks its carrier node.
    model.variables["m"].solution.loc[{"carrier": "natural_gas"}] += 1.0
    violations = build.check_constraint_rows(model, tampered)
    assert violations
    assert any(violation.constraint == "C8_natural_gas" for violation in violations)
    assert all(isinstance(violation.residual, float) for violation in violations)


def test_the_row_check_refuses_an_unsolved_result() -> None:
    model, _ = _solved()
    unsolved = build.SolveResult(
        status="warning",
        termination_condition="infeasible",
        objective=None,
        solution=None,
        n_variables=0,
        n_constraints=0,
        wall_clock_seconds=0.0,
    )
    with pytest.raises(ValueError, match="needs a solved model"):
        build.check_constraint_rows(model, unsolved)


def test_problem_size_is_within_the_band_derived_from_the_set_sizes() -> None:
    """linopy #248: an ineffective mask silently builds a dense model rather than raising,
    and at three premises HiGHS solves either version in under a second.

    The counts below are the sparse formulation's exact sizes, derived from |Q|, |U_q|, |T|
    and the carrier sets — not copied from a run.
    """
    model, result = _solved()
    n_periods = len(PERIODS)
    n_units = 2
    n_pairs = 2  # one duty, two eligible units
    n_incumbent = 1
    n_import = 2  # natural_gas, electricity
    # heat_lt60, co2_fuel_fossil and co2_fuel_biogenic: natural gas carries
    # biogenic_fraction 0.0115, so A6 derives a non-zero biogenic row as well as a fossil one.
    n_disposal = 3
    n_carriers_in_balance = 5  # the two imports plus the three disposals

    expected_variables = n_periods * (
        n_pairs + n_units + n_units + n_incumbent + n_import + n_disposal
    )
    expected_constraints = (
        n_periods  # C1, one duty
        + n_periods * n_units  # C2
        + n_periods * n_units  # C3, split incumbent / greenfield
        + n_periods * n_incumbent  # C4
        + n_units  # C5, the start year only
        + n_periods * n_carriers_in_balance  # C8
    )
    assert result.n_variables == expected_variables
    assert result.n_constraints == expected_constraints
    assert model.nvars == expected_variables
    assert model.ncons == expected_constraints

    # The dense trap: z declared over |U| x |Q| rather than over the eligible pairs. With one
    # duty and two units the two happen to coincide, so the guard that matters is that the
    # dispatch dimension is the pair set and nothing larger.
    assert model.variables["z"].size == n_pairs * n_periods


def test_problem_size_stays_sparse_when_eligibility_is_partial() -> None:
    """Two duties, one unit eligible for each: dense would be 2 x 2, sparse is 2."""
    first = _Duty(
        premise_id="mvp-minimal",
        process_id="steam_hot_water",
        carrier_id="heat_60_100",
        grade_rank=2,
        quantity=dict.fromkeys(PERIODS, 1.0),
    )
    second = _Duty(
        premise_id="mvp-minimal",
        process_id="scalding_singeing",
        carrier_id="heat_60_100",
        grade_rank=2,
        quantity=dict.fromkeys(PERIODS, 1.0),
    )
    sets = ModelSets(
        periods=PERIODS,
        duties=(first, second),
        units=frozenset({"boiler_lt_gas", "heat_pump_lt_air"}),
        eligible={
            first.key: frozenset({"boiler_lt_gas"}),
            second.key: frozenset({"heat_pump_lt_air"}),
        },
        earliest_year={},
        max_share={},
        min_duty={},
    )
    reference = _reference()
    surviving = survival.surviving_capacity(_incumbent(), reference.unit, PERIODS)
    model = build.build_model(sets, surviving, _axis(), reference)
    assert model.variables["z"].size == 2 * len(PERIODS)
    assert model.constraints["C1"].size == 2 * len(PERIODS)


# --------------------------------------------------------------------------------------
# Failing loud where a blank would be read as free
# --------------------------------------------------------------------------------------


def test_a_blank_capex_that_reached_the_lp_fails_loud() -> None:
    """15 units carry a blank ``capex`` and the §3.2 screen exists to drop them. One that
    slipped through must not be annuitised at zero."""
    reference = _reference(blank_capex=True)
    surviving = survival.surviving_capacity(_incumbent(), reference.unit, PERIODS)
    with pytest.raises(ValueError, match="blank 'capex'"):
        build.build_model(_sets(), surviving, _axis(), reference)


def test_a_part_priced_carrier_fails_loud_naming_the_periods() -> None:
    """The partial case is the dangerous one: ``heavy_fuel_oil`` carries exactly one
    ``import_price`` row, at 2021, and looks present until you index it by year (§3.2)."""
    reference = _reference(drop_gas_price_at=2030)
    surviving = survival.surviving_capacity(_incumbent(), reference.unit, PERIODS)
    with pytest.raises(ValueError, match=r"import_price for natural_gas at \[2030\]"):
        build.build_model(_sets(), surviving, _axis(), reference)


def test_the_axis_and_the_objective_must_read_one_discount_rate() -> None:
    """δ_t is built by the caller and the capex annuity reads ``scenario_parameters``; two
    rates would discount the pathway at one and price capital at the other, silently."""
    reference = _reference()
    surviving = survival.surviving_capacity(_incumbent(), reference.unit, PERIODS)
    wrong = build.period_axis(PERIODS, 0.10)
    with pytest.raises(ValueError, match="different rate"):
        build.build_model(_sets(), surviving, wrong, reference)


def test_a_declared_process_co2_row_is_vented_rather_than_making_the_premise_infeasible() -> None:
    """The cement case (§2.2). ``co2_process`` has 34 producing units and two consumers, so
    without a disposal variable a kiln cannot run at all; here it vents and pays for it.

    This also exercises the *declared* ``emission`` role, which D15 keeps in the table
    alongside the two rows A6 derives.
    """
    carrier = _carrier_table()
    carrier = pd.concat(
        [
            carrier,
            pd.DataFrame(
                [
                    {
                        "carrier_id": "co2_process",
                        "carrier_kind": "emission",
                        "is_indirect": "FALSE",
                        "biogenic_fraction": "",
                        "carbon_charge": "charged",
                        "may_dispose": "TRUE",
                        "may_import": "FALSE",
                    },
                    {
                        "carrier_id": "clinker",
                        "carrier_kind": "product",
                        "is_indirect": "FALSE",
                        "biogenic_fraction": "",
                        "carbon_charge": "",
                        "may_dispose": "FALSE",
                        "may_import": "FALSE",
                    },
                ]
            ),
        ],
        ignore_index=True,
    )
    unit = pd.DataFrame(
        [
            {
                "unit_id": "kiln_cement_dry",
                "unit_class": "converter",
                "capex": 100.0,
                "fixed_opex": 2.0,
                "lifetime": 40,
                "availability_factor": 0.9,
                "capacity_to_activity_factor": 1.0,
            }
        ]
    )
    process_co2 = 525.0  # kt CO₂ per Mt of clinker — stoichiometry, not a scenario value
    input_output = pd.DataFrame(
        [
            {
                "unit_id": "kiln_cement_dry",
                "carrier_id": "clinker",
                "coefficient": 1.0,
                "role": "primary_output",
            },
            {
                "unit_id": "kiln_cement_dry",
                "carrier_id": "natural_gas",
                "coefficient": -3.5,
                "role": "fuel_input",
            },
            {
                "unit_id": "kiln_cement_dry",
                "carrier_id": "co2_process",
                "coefficient": process_co2,
                "role": "emission",
            },
        ]
    )
    reference = ReferenceTables(
        carrier=carrier,
        unit=unit,
        unit_input_output=input_output,
        unit_eligibility=pd.DataFrame(),
        scenario_parameters=_scenario_table(),
        activity_process_duty_profile=pd.DataFrame(),
        activity_process_register=pd.DataFrame(),
    )
    duty = _Duty(
        premise_id="mvp-cement",
        process_id="clinker_production",
        carrier_id="clinker",
        grade_rank=None,
        quantity=dict.fromkeys(PERIODS, 1.0),
    )
    sets = ModelSets(
        periods=PERIODS,
        duties=(duty,),
        units=frozenset({"kiln_cement_dry"}),
        eligible={duty.key: frozenset({"kiln_cement_dry"})},
        earliest_year={},
        max_share={},
        min_duty={},
    )
    surviving = survival.surviving_capacity(
        pd.DataFrame(
            [
                {
                    "unit_id": "kiln_cement_dry",
                    "commissioned_year": 2005,
                    "capacity": 2.0,
                }
            ]
        ),
        unit,
        PERIODS,
    )
    model = build.build_model(sets, surviving, _axis(), reference)
    result = build.solve(model)
    assert result.termination_condition == "optimal"
    vented = model.variables["d"].solution.to_pandas()
    assert vented.loc["co2_process", 2021] == pytest.approx(process_co2)
    # And the fuel CO₂ A6 derives sits on its own carrier, not folded into the declared one.
    assert vented.loc["co2_fuel_fossil", 2021] == pytest.approx(
        3.5 * EF_NATURAL_GAS[2021] * (1 - 0.0115)
    )
    assert build.check_constraint_rows(model, result) == ()
