"""sets.py — minimal A2; Q, U, U_q via the three-table join; C10 widening; diagnosis.

The premise side is a fixture written here, not Lane D's ``carb3/data/premises/*.csv``: the
duty *structure* under test is read from the real reference tables either way, and only the
magnitude is synthetic, so nothing is weakened by owning the premise rows locally.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
import pytest
from test_load import write_premise_fixture

from carb3 import load, sets

# The two duties of ``boiler_steam_hot_water`` at the dairy fixture, whose shares are read
# from ``activity_process_duty_profile``: LTH on heat_60_100 at grade 2, STM on heat_100_150
# at grade 3. ``known_capacity`` is 1.0 PJ/yr, so quantity is the share itself.
DAIRY_G2 = ("fx-dairy", "boiler_steam_hot_water", "heat_60_100")
DAIRY_G3 = ("fx-dairy", "boiler_steam_hot_water", "heat_100_150")
DAIRY_G4 = ("fx-dairy", "direct_heating", "heat_150_400")
DAIRY_MOT = ("fx-dairy", "site_services", "motive_power")


@pytest.fixture(scope="module")
def reference() -> load.ReferenceTables:
    return load.load_reference_tables()


@pytest.fixture(scope="module")
def screen(reference: load.ReferenceTables) -> load.AdmissionScreen:
    return load.screen_units(reference)


@pytest.fixture
def premise_root(tmp_path: Path) -> Path:
    return write_premise_fixture(tmp_path / "premises")


def build(
    reference: load.ReferenceTables,
    screen: load.AdmissionScreen,
    root: Path,
    premise_id: str = "fx-dairy",
) -> sets.ModelSets:
    premise = load.load_premise_tables(premise_id, root)
    return sets.build_sets(reference, premise, screen, load.PERIOD_YEARS)


@pytest.fixture
def dairy(reference, screen, premise_root: Path) -> sets.ModelSets:
    return build(reference, screen, premise_root)


# ------------------------------------------------------------------ the frozen contract


def test_duty_carries_the_derived_structure() -> None:
    """Plan §3.3: which duty, on which carrier, at which grade_rank; only quantity is hand-written."""
    fields = {f.name for f in dataclasses.fields(sets.Duty)}
    assert fields == {
        "premise_id",
        "process_id",
        "carrier_id",
        "grade_rank",
        "quantity",
    }


def test_model_sets_carry_the_three_eligibility_columns() -> None:
    """Plan §3.1: earliest_year, max_share and min_duty are all live and all honoured."""
    fields = {f.name for f in dataclasses.fields(sets.ModelSets)}
    assert {"earliest_year", "max_share", "min_duty"} <= fields
    assert {"periods", "duties", "units", "eligible"} <= fields


def test_unservable_duty_names_premise_and_period() -> None:
    """Plan §5.2: infeasibility is diagnosed by name, not raised."""
    fields = {f.name for f in dataclasses.fields(sets.UnservableDuty)}
    assert fields == {"duty", "period", "removed"}


def test_signatures(assert_signature) -> None:
    assert_signature(sets, "derive_duties", ("reference", "premise", "periods"))
    assert_signature(sets, "build_sets", ("reference", "premise", "screen", "periods"))
    assert_signature(sets, "diagnose_unservable_duties", ("sets", "screen"))
    # ``carb3_activity`` is the one addition to the scaffolded signatures. See the module
    # header: unit_eligibility is keyed on the activity and Duty carries none, and 29 of the
    # 215 process_id values appear under more than one activity.
    assert_signature(
        sets, "eligible_units", ("reference", "duty", "admitted", "carb3_activity")
    )


def test_duty_key_is_premise_process_carrier() -> None:
    duty = sets.Duty("p", "proc", "heat_60_100", 2, {2021: 1.0})
    assert duty.key == ("p", "proc", "heat_60_100")


# ------------------------------------------------------------------- the minimal A2


def test_a2_derives_structure_from_the_duty_profile(dairy: sets.ModelSets) -> None:
    """Plan §3.3: the duty profile is genuinely read, so grade bands and carriers resolve."""
    by_key = {d.key: d for d in dairy.duties}
    assert DAIRY_G2 in by_key and DAIRY_G3 in by_key
    assert by_key[DAIRY_G2].carrier_id == "heat_60_100"
    assert by_key[DAIRY_G2].grade_rank == 2
    assert by_key[DAIRY_G3].grade_rank == 3
    assert by_key[DAIRY_G4].grade_rank == 4


def test_a2_grade_rank_is_none_only_where_the_carrier_is_not_gradeable(
    reference: load.ReferenceTables, dairy: sets.ModelSets
) -> None:
    """§3.3's rule: a heat duty with no grade is invisible to C10 and fails silently."""
    carrier = reference.carrier.set_index("carrier_id")
    for duty in dairy.duties:
        gradeable = bool(carrier.loc[duty.carrier_id, "is_gradeable"]) is True
        assert (duty.grade_rank is not None) == gradeable


def test_a2_takes_only_the_magnitude_from_the_premise(dairy: sets.ModelSets) -> None:
    """quantity = known_capacity x duty_share, which is §3.3's own arithmetic for a share."""
    by_key = {d.key: d for d in dairy.duties}
    assert by_key[DAIRY_G2].quantity[2021] == pytest.approx(1.0 * 0.46180)
    assert by_key[DAIRY_G3].quantity[2021] == pytest.approx(1.0 * 0.53820)
    assert by_key[DAIRY_G4].quantity[2021] == pytest.approx(0.4 * 1.00000)
    # Flat across the horizon: the slice models no demand growth.
    assert set(by_key[DAIRY_G2].quantity) == set(load.PERIOD_YEARS)
    assert len(set(by_key[DAIRY_G2].quantity.values())) == 1


def test_a2_resolves_both_worked_example_activities(
    reference, screen, premise_root: Path
) -> None:
    """Plan §3.3: both are in the register, of 55."""
    register = reference.activity_process_register["carb3_activity"]
    assert {"Cement Works", "Food Processing Centre"} <= set(register)
    assert build(reference, screen, premise_root, "fx-dairy").duties
    assert build(reference, screen, premise_root, "fx-cement").duties


def test_d16_removes_the_kiln_duty_and_keeps_the_grinder(
    reference, screen, premise_root: Path
) -> None:
    """The cement worked example §3.2: "kiln_pyroprocessing is not one of them".

    Its units make ``clinker``, a ``product`` with ``may_export`` false, so D16 (the site
    boundary on the carrier) removes the premise-level duty row and C8 (carrier balance)
    pins the kilns' activity instead. ``cement_grinding``'s row remains, which is what
    V32(b) checks.
    """
    cement = build(reference, screen, premise_root, "fx-cement")
    processes = {d.process_id for d in cement.duties}
    assert "kiln_pyroprocessing" not in processes
    assert "cement_grinding" in processes


def test_a2_reports_a_process_it_cannot_size_rather_than_raising(
    reference, premise_root: Path
) -> None:
    """A blank ``known_capacity`` yields no duty, and the process is **named**.

    This test asserted a raise until the synthetic premises met it. §3.10 requires
    ``known_capacity > 0 if present``, so the column cannot state a *known* zero, and two
    ``mvp-cement`` processes — ``clinker_cooling`` and ``site_services`` — have a genuine
    duty of 0.00000 PJ/yr and are written blank with the reason in ``provenance``
    (the premise README's finding 5). Raising made a legitimate premise unloadable, and
    reading the blank as zero is the failure the §3.2 screen exists to prevent one table
    along. The third answer is the one here: derive no duty, and make the silence
    impossible by naming every process it happened to.
    """
    root = write_premise_fixture(
        premise_root,
        premise_process_detail=(
            "premise_id,process_id,valid_from_year,known_capacity,provenance,confidence\n"
            "fx-dairy,boiler_steam_hot_water,2021,,fixture,high\n"
        ),
    )
    premise = load.load_premise_tables("fx-dairy", root)
    assert sets.derive_duties(reference, premise, load.PERIOD_YEARS) == ()
    assert sets.processes_without_magnitude(premise) == ("boiler_steam_hot_water",)


def test_a2_fails_loud_with_no_process_valid_at_the_base_year(
    reference, premise_root: Path
) -> None:
    """§3.10's completeness rule: an interval that closed before the base year is history."""
    root = write_premise_fixture(
        premise_root,
        premise_process_detail=(
            "premise_id,process_id,valid_from_year,valid_to_year,known_capacity,"
            "provenance,confidence\n"
            "fx-dairy,boiler_steam_hot_water,1990,2010,1.0,fixture,high\n"
        ),
    )
    premise = load.load_premise_tables("fx-dairy", root)
    with pytest.raises(sets.DutyDerivationError, match="no_process_valid_in_base_year"):
        sets.derive_duties(reference, premise, load.PERIOD_YEARS)


# --------------------------------------------------- U_q and C10, in both directions


def test_c10_a_grade_3_unit_serves_a_grade_2_duty(dairy: sets.ModelSets) -> None:
    """C10 (the grade cascade) widens U_q downwards: heat made hotter still serves cooler."""
    assert "boiler_lt_gas" in dairy.eligible[DAIRY_G2]
    assert "boiler_lt_gas" in dairy.eligible[DAIRY_G3]


def test_c10_a_grade_3_unit_is_refused_a_grade_4_duty(dairy: sets.ModelSets) -> None:
    """The direction that matters. Nothing raises heat to a grade the plant cannot make.

    Getting this inequality backwards is a silent wrong answer, not a crash, which is why
    both directions are asserted rather than one.
    """
    assert "boiler_lt_gas" not in dairy.eligible[DAIRY_G4]
    assert "resistance_heater_lt" not in dairy.eligible[DAIRY_G4]


def test_c10_a_grade_2_unit_is_refused_a_grade_3_duty(dairy: sets.ModelSets) -> None:
    assert "heat_pump_lt_air" in dairy.eligible[DAIRY_G2]
    assert "heat_pump_lt_air" not in dairy.eligible[DAIRY_G3]


def test_c10_refuses_a_grade_1_unit_a_grade_2_duty(
    reference, dairy: sets.ModelSets
) -> None:
    """``site_services`` offers grade-1 boilers and grade-2 heat pumps to a grade-2 duty."""
    unit = reference.unit.set_index("unit_id")
    assert int(unit.loc["boiler_spc_gas", "grade_out"]) == 1
    service_g2 = dairy.eligible[("fx-dairy", "site_services", "heat_60_100")]
    assert "boiler_spc_gas" not in service_g2
    assert service_g2 == {"heat_pump_lt_air", "heat_pump_lt_reject"}


def _duty(carrier_id: str, grade_rank: int | None) -> sets.Duty:
    return sets.Duty("fx", "p", carrier_id, grade_rank, {2021: 1.0})


def _unit(grade_out: int | None) -> pd.Series:
    return pd.Series({"grade_out": pd.NA if grade_out is None else grade_out})


def test_c10_cooling_runs_the_other_way(reference) -> None:
    """Note 22 Task 9. For cooling, rank 1 is the coldest band, so the cascade is reversed:
    a sub-zero plant (``grade_out`` 1) serves a chilled-water duty (rank 2), and a cooling
    tower (``grade_out`` 3, ambient heat rejection) is refused a sub-zero duty (rank 1)."""
    families = sets._grade_families(reference)
    chilled = _duty("cooling_0_15", 2)
    freezer = _duty("cooling_lt0", 1)
    assert sets._serves(_unit(1), {"cooling_lt0"}, chilled, families)
    assert sets._serves(_unit(2), {"cooling_0_15"}, chilled, families)
    assert not sets._serves(_unit(3), {"cooling_gt15"}, freezer, families)
    assert not sets._serves(_unit(2), {"cooling_0_15"}, freezer, families)


def test_c10_never_crosses_grade_families(reference) -> None:
    """A heat unit's ``grade_out`` 2 says nothing about cooling: before the family test,
    ``heat_pump_lt_reject`` (heat, ``grade_out`` 2) sat in U_q for a rank-2 chilled-water
    duty, and a chiller would have sat in U_q for a rank-2 heat duty."""
    families = sets._grade_families(reference)
    assert not sets._serves(_unit(2), {"heat_60_100"}, _duty("cooling_0_15", 2), families)
    assert not sets._serves(_unit(2), {"cooling_0_15"}, _duty("heat_60_100", 2), families)


def test_a_non_gradeable_duty_matches_on_the_carrier_instead(
    dairy: sets.ModelSets,
) -> None:
    """``motive_power`` has no cascade, so the test is the plain one: does the unit make it.

    Without this the eligibility row alone would let a gas boiler serve a motive-power duty,
    because ``site_services`` offers both and no grade constrains the match.
    """
    assert dairy.eligible[DAIRY_MOT] == {"motor_elec"}
    assert "boiler_spc_gas" not in dairy.eligible[DAIRY_MOT]


def test_u_q_is_restricted_to_the_admitted_set(
    dairy: sets.ModelSets, screen: load.AdmissionScreen
) -> None:
    """The §3.2 screen and the join compose: a dropped unit reaches no duty at all."""
    dropped = {d.unit_id for d in screen.dropped}
    for units in dairy.eligible.values():
        assert not (units & dropped)
        assert units <= screen.admitted
    assert "boiler_lt_hydrogen" not in dairy.eligible[DAIRY_G3]
    assert "heat_exchanger_lt_steam" not in dairy.eligible[DAIRY_G3]


def test_activity_level_rows_do_not_reach_a_duty_they_should_not(
    reference, dairy: sets.ModelSets
) -> None:
    """The documented rule for the 142 blank-``process_id`` rows (plan §10).

    They are activity-level supply and reach every process of the activity; what stops them
    reaching a duty they should not is the carrier and grade test, not the key. The three
    that reach the dairy are ``pv_rooftop``, ``pv_ground_mount`` and ``battery_2h``, none of
    which makes heat or motive power.
    """
    elig = reference.unit_eligibility
    blank = elig[elig["process_id"].isna()]
    assert len(blank) == 142
    activity_level = set(
        blank[blank["carb3_activity"] == "Food Processing Centre"]["unit_id"]
    )
    assert activity_level == {"pv_rooftop", "pv_ground_mount", "battery_2h"}
    for units in dairy.eligible.values():
        assert not (units & activity_level)


def test_eligible_units_needs_the_activity(reference, screen, dairy) -> None:
    """29 of the 215 process_id values appear under more than one activity."""
    elig = reference.unit_eligibility
    named = elig[elig["process_id"].notna()]
    per_process = named.groupby("process_id")["carb3_activity"].nunique()
    assert int((per_process > 1).sum()) == 29
    assert "site_services" in set(per_process[per_process > 1].index)

    duty = next(d for d in dairy.duties if d.key == DAIRY_G2)
    with pytest.raises(TypeError):
        sets.eligible_units(reference, duty, screen.admitted)  # type: ignore[call-arg]


# ------------------------------------------------ the three eligibility columns


def test_earliest_year_is_carried_out_to_the_lp(dairy: sets.ModelSets) -> None:
    """9 rows, 2030/2035/2040. A bound of zero on new capacity before the year, not a drop."""
    assert dairy.earliest_year[(DAIRY_G2, "heat_pump_ht")] == 2030
    assert dairy.earliest_year[(DAIRY_G3, "heat_pump_ht")] == 2030
    assert "heat_pump_ht" in dairy.eligible[DAIRY_G2]


def test_max_share_zero_is_a_hard_prohibition(
    reference, dairy: sets.ModelSets
) -> None:
    """``boiler_lt_coal`` at ``Food Processing Centre`` carries max_share 0.00.

    It is removed from U_q rather than bounded inside it: a unit that may take no share of a
    duty is not eligible for it, and leaving it in would make the prohibition depend on C1
    (duty satisfaction) being written correctly downstream.
    """
    elig = reference.unit_eligibility
    row = elig[(elig["unit_id"] == "boiler_lt_coal")
               & (elig["carb3_activity"] == "Food Processing Centre")]
    assert float(row["max_share"].iloc[0]) == 0.0
    assert "boiler_lt_coal" in dairy.units, "it passes the §3.2 screen; eligibility stops it"
    assert "boiler_lt_coal" not in dairy.eligible[DAIRY_G2]
    assert "boiler_lt_coal" not in dairy.eligible[DAIRY_G3]
    assert (DAIRY_G2, "boiler_lt_coal") not in dairy.max_share


def test_a_positive_max_share_is_recorded_as_a_c1_cap(
    reference, screen, premise_root: Path
) -> None:
    """The cap itself, on a copy of the table: all four real rows are inert in this slice.

    Three sit on ``cement_grinding`` and ``kiln_pyroprocessing``, whose duties D16 removes or
    the carrier test empties, and the fourth is the 0.00 prohibition above — so the only way
    to exercise the bound is to state one.
    """
    elig = reference.unit_eligibility.copy()
    row = (elig["unit_id"] == "boiler_lt_gas") & (
        elig["carb3_activity"] == "Food Processing Centre"
    )
    assert int(row.sum()) == 1
    elig.loc[row, "max_share"] = 0.35
    capped = dataclasses.replace(reference, unit_eligibility=elig)

    model = build(capped, screen, premise_root)
    assert model.max_share[(DAIRY_G2, "boiler_lt_gas")] == pytest.approx(0.35)
    assert "boiler_lt_gas" in model.eligible[DAIRY_G2]


def test_min_duty_screens_a_unit_out_below_its_floor(
    reference, screen, premise_root: Path
) -> None:
    """15 rows. ``heat_pump_lt_air`` carries 0.01 at the dairy, so a small duty loses it.

    Minimum viable scale is this screen and never a fixed-charge binary (§2.3): the decision
    is made outside the LP, in A2, exactly as §3.5.1 says.
    """
    root = write_premise_fixture(
        premise_root,
        premise_process_detail=(
            "premise_id,process_id,valid_from_year,known_capacity,provenance,confidence\n"
            "fx-dairy,boiler_steam_hot_water,2021,0.001,fixture,high\n"
        ),
    )
    small = build(reference, screen, root)
    assert "heat_pump_lt_air" not in small.eligible[DAIRY_G2]
    assert "heat_pump_lt_reject" not in small.eligible[DAIRY_G2]
    # boiler_lt_gas carries no min_duty row, so the floor removes nothing from it.
    assert "boiler_lt_gas" in small.eligible[DAIRY_G2]


def test_min_duty_admits_a_unit_that_clears_its_floor(dairy: sets.ModelSets) -> None:
    assert dairy.min_duty[(DAIRY_G2, "heat_pump_lt_air")] == pytest.approx(0.01)
    assert "heat_pump_lt_air" in dairy.eligible[DAIRY_G2]
    # The grade-3 duty is above heat_pump_lt_air's grade_out, so C10 removes it there and
    # no min_duty entry survives for it either.
    assert (DAIRY_G3, "heat_pump_lt_air") not in dairy.min_duty


def test_min_duty_reads_the_right_activitys_row(
    reference, screen, premise_root: Path
) -> None:
    """``heat_pump_lt_air`` carries a 0.01 floor at the dairy and none at site_services.

    The floor is keyed by process, so reading the wrong process's row would apply a floor the
    duty never had — the same failure the missing ``carb3_activity`` would cause one level up.
    """
    dairy = build(reference, screen, premise_root)
    assert (DAIRY_G2, "heat_pump_lt_air") in dairy.min_duty
    service_g2 = ("fx-dairy", "site_services", "heat_60_100")
    assert "heat_pump_lt_air" in dairy.eligible[service_g2]
    assert (service_g2, "heat_pump_lt_air") not in dairy.min_duty


# --------------------------------------------------------- unservable-duty diagnosis


def test_a_servable_premise_diagnoses_nothing(
    dairy: sets.ModelSets, screen: load.AdmissionScreen
) -> None:
    assert sets.diagnose_unservable_duties(dairy, screen) == ()


def test_an_unservable_duty_is_named_with_premise_and_period(
    reference, screen, premise_root: Path
) -> None:
    """Plan §5.2: reported by name before the LP is built, not raised.

    ``cement_grinding`` is the real case. The reference duty profile types it ``MOT`` on
    ``motive_power`` while every eligible unit makes ``cement``, so the carrier test empties
    U_q. The cement worked example reaches the real duty — ``cement`` as a mass — only
    through the D10 site-intelligence override that plan §3.3 puts out of the minimal A2.
    """
    cement = build(reference, screen, premise_root, "fx-cement")
    assert cement.eligible[("fx-cement", "cement_grinding", "motive_power")] == frozenset()

    reported = sets.diagnose_unservable_duties(cement, screen)
    assert reported
    assert {r.duty for r in reported} == {("fx-cement", "cement_grinding", "motive_power")}
    assert {r.period for r in reported} == set(load.PERIOD_YEARS)
    assert all(r.removed for r in reported)
    assert all(isinstance(d, load.UnitDrop) for r in reported for d in r.removed)


def test_a_duty_gated_shut_by_earliest_year_is_diagnosed_per_period(
    reference, screen, premise_root: Path
) -> None:
    """A unit unavailable until 2030 leaves the duty unservable in 2021 and 2025.

    Built by shrinking U_q to ``heat_pump_ht`` alone, which carries ``earliest_year`` 2030.
    """
    elig = reference.unit_eligibility
    keep = ~(
        (elig["carb3_activity"] == "Food Processing Centre")
        & (elig["process_id"] == "boiler_steam_hot_water")
        & (elig["unit_id"] != "heat_pump_ht")
    )
    narrowed = dataclasses.replace(reference, unit_eligibility=elig[keep])

    model = build(narrowed, screen, premise_root)
    assert model.eligible[DAIRY_G2] == {"heat_pump_ht"}
    reported = sets.diagnose_unservable_duties(model, screen)
    gated = {r.period for r in reported if r.duty == DAIRY_G2}
    assert gated == {2021, 2025}
    assert 2030 not in gated


def test_diagnosis_is_data_not_an_exception(
    reference, screen, premise_root: Path
) -> None:
    """§5.2 keeps infeasibility an expected outcome; build_sets returns rather than raises."""
    cement = build(reference, screen, premise_root, "fx-cement")
    assert isinstance(cement, sets.ModelSets)
    assert isinstance(sets.diagnose_unservable_duties(cement, screen), tuple)


def test_sets_carry_the_periods_and_the_admitted_set(
    dairy: sets.ModelSets, screen: load.AdmissionScreen
) -> None:
    assert dairy.periods == load.PERIOD_YEARS
    assert dairy.units == screen.admitted
    assert set(dairy.eligible) == {d.key for d in dairy.duties}
    assert all(isinstance(k, tuple) and len(k) == 3 for k in dairy.eligible)
