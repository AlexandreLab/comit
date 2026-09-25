"""load.py — reference + premise tables -> typed records; the §3.2 screen.

The counts asserted below were measured against ``docs/notes/data/`` on 2026-09-19 by the
code under test. They are a **baseline, not a specification**: the reference tables are
hand-researched and will move, and when they do these assertions are the thing that says so.
Each carries the figure plan §3.2 quotes, so a drift is legible rather than a bare number
change.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
import pytest

from carb3 import load

# --------------------------------------------------------------------------- fixtures

PREMISE_FILES: dict[str, str] = {
    "premise_record": (
        "premise_id,carb3_activity,latitude,longitude,nation,cluster_id,data_year,source\n"
        "fx-dairy,Food Processing Centre,52.0,-1.0,England,mersey,2021,fixture\n"
        "fx-cement,Cement Works,53.0,-2.0,England,humber,2021,fixture\n"
    ),
    "premise_connection": (
        "premise_id,connection_id,carrier_id,import_capacity,export_capacity\n"
        "fx-dairy,E-01,electricity,4,2\n"
        "fx-dairy,G-01,natural_gas,18,0\n"
        "fx-cement,C-01,electricity,25,0\n"
        "fx-cement,C-02,natural_gas,20,0\n"
        "fx-cement,C-03,co2_captured,0,\n"
    ),
    "premise_throughput": (
        "premise_id,carrier_id,quantity,data_year,data_status,source\n"
        "fx-cement,clinker,0.25,2021,measured,fixture\n"
        "fx-cement,cement,0.3,2021,measured,fixture\n"
    ),
    "premise_process_detail": (
        "premise_id,process_id,valid_from_year,known_capacity,provenance,confidence\n"
        "fx-dairy,boiler_steam_hot_water,2021,1.0,fixture,high\n"
        "fx-dairy,direct_heating,2021,0.4,fixture,high\n"
        "fx-dairy,site_services,2021,0.5,fixture,high\n"
        "fx-cement,kiln_pyroprocessing,2021,2.0,fixture,high\n"
        "fx-cement,cement_grinding,2021,0.3,fixture,high\n"
    ),
    "premise_process_unit": (
        "premise_id,process_id,valid_from_year,unit_id,provenance,confidence\n"
        "fx-dairy,boiler_steam_hot_water,2021,boiler_lt_gas,fixture,high\n"
        "fx-cement,kiln_pyroprocessing,2021,kiln_dry_gas,fixture,high\n"
    ),
    "premise_process_vintage": (
        "premise_id,process_id,cohort_id,unit_id,commissioned_year,capacity_share,"
        "provenance,confidence\n"
        "fx-dairy,boiler_steam_hot_water,1,boiler_lt_gas,2005,1.0,fixture,high\n"
    ),
}


def write_premise_fixture(root: Path, **overrides: str) -> Path:
    """Write the four premise tables under ``root``. Lane D's real CSVs are not depended on.

    ``overrides`` replaces one file's whole text, which is how the fail-loud and
    FK-resolution cases below state the one thing they are breaking.
    """
    root.mkdir(parents=True, exist_ok=True)
    for name, text in {**PREMISE_FILES, **overrides}.items():
        (root / f"{name}.csv").write_text(text)
    return root


@pytest.fixture(scope="module")
def reference() -> load.ReferenceTables:
    return load.load_reference_tables()


@pytest.fixture(scope="module")
def screen(reference: load.ReferenceTables) -> load.AdmissionScreen:
    return load.screen_units(reference)


@pytest.fixture
def premise_root(tmp_path: Path) -> Path:
    return write_premise_fixture(tmp_path / "premises")


# ------------------------------------------------------------------ the frozen contract


def test_roots_resolve_from_the_repo_not_the_caller() -> None:
    """Plan §3.1: a documented default resolved from the repo root, never the caller's cwd."""
    assert load.DEFAULT_REFERENCE_ROOT == load.REPO_ROOT / "docs" / "notes" / "data"
    assert load.DEFAULT_REFERENCE_ROOT.is_absolute()
    assert load.DEFAULT_PREMISE_ROOT == load.REPO_ROOT / "carb3" / "data" / "premises"


def test_period_years_are_the_real_vector() -> None:
    """Plan §6.4: a 4-year first gap and 5-year gaps thereafter, not a uniform delta."""
    assert load.PERIOD_YEARS == (2021, 2025, 2030, 2035, 2040, 2045, 2050)


def test_reference_tables_carry_the_eight_tables() -> None:
    """``infrastructure_scenario`` is the eighth: C9 (infrastructure availability) came
    partially back into scope for CO₂ transport, and its 63 rows are where the gate is."""
    fields = {f.name for f in dataclasses.fields(load.ReferenceTables)}
    assert fields == {
        "carrier",
        "unit",
        "unit_input_output",
        "unit_eligibility",
        "scenario_parameters",
        "activity_process_duty_profile",
        "activity_process_register",
        "infrastructure_scenario",
    }


def test_premise_tables_carry_six_and_not_process_duty() -> None:
    """Plan §3.4: process_duty is derived by the minimal A2, not an input table.

    Six, not the four the plan commissioned. ``premise_throughput`` (§3.1.2) carries the
    cement works' mass duty, which the duty profile cannot state because it holds no mass
    carrier; ``premise_connection`` (§3.1.3) is what §5.2 requires before an export
    variable may be declared. Both were written by the premise lane and read by nothing.
    """
    fields = {f.name for f in dataclasses.fields(load.PremiseTables)}
    assert fields == {
        "premise_record",
        "premise_connection",
        "premise_throughput",
        "premise_process_detail",
        "premise_process_unit",
        "premise_process_vintage",
    }
    assert "process_duty" not in fields


def test_screen_reports_drops_rather_than_raising() -> None:
    fields = {f.name for f in dataclasses.fields(load.AdmissionScreen)}
    assert fields == {"admitted", "dropped"}
    assert {f.name for f in dataclasses.fields(load.UnitDrop)} == {
        "unit_id",
        "leg",
        "detail",
    }


def test_signatures(assert_signature) -> None:
    assert_signature(load, "load_reference_tables", ("root",))
    assert_signature(load, "load_premise_tables", ("premise_id", "root"))
    assert_signature(load, "screen_units", ("reference", "periods"))


# ------------------------------------------------------------------ loader, fail loud


def test_missing_file_fails_loud(tmp_path: Path) -> None:
    with pytest.raises(load.SchemaError, match="no such table"):
        load.load_reference_tables(tmp_path)


def test_missing_column_fails_loud(tmp_path: Path) -> None:
    root = write_premise_fixture(
        tmp_path / "p",
        premise_record=(
            "premise_id,carb3_activity,latitude,longitude,nation,source\n"
            "fx-dairy,Food Processing Centre,52.0,-1.0,England,fixture\n"
        ),
    )
    with pytest.raises(load.SchemaError, match="missing required column.*data_year"):
        load.load_premise_tables("fx-dairy", root)


def test_unknown_column_fails_loud(tmp_path: Path) -> None:
    """An unknown column means the schema moved and nothing here has been told (§5.3)."""
    root = write_premise_fixture(
        tmp_path / "p",
        premise_record=(
            "premise_id,carb3_activity,latitude,longitude,nation,data_year,source,"
            "annual_bonus\n"
            "fx-dairy,Food Processing Centre,52.0,-1.0,England,2021,fixture,7\n"
        ),
    )
    with pytest.raises(load.SchemaError, match="unknown column.*annual_bonus"):
        load.load_premise_tables("fx-dairy", root)


def test_absent_optional_column_is_supplied_not_rejected(premise_root: Path) -> None:
    """The fixture states no connection_id or valid_to_year; §3.10 marks both optional."""
    premise = load.load_premise_tables("fx-dairy", premise_root)
    assert "connection_id" in premise.premise_process_detail.columns
    assert premise.premise_process_detail["valid_to_year"].isna().all()


def test_unknown_premise_id_is_an_error_not_an_empty_frame(premise_root: Path) -> None:
    with pytest.raises(load.ResolutionError, match="no row for premise_id"):
        load.load_premise_tables("fx-nowhere", premise_root)


def test_two_premise_record_rows_are_rejected(tmp_path: Path) -> None:
    """§3.1 is one row per premise; two is a contradiction, not a longer table."""
    root = write_premise_fixture(
        tmp_path / "p",
        premise_record=(
            "premise_id,carb3_activity,latitude,longitude,nation,data_year,source\n"
            "fx-dairy,Food Processing Centre,52.0,-1.0,England,2021,fixture\n"
            "fx-dairy,Cement Works,53.0,-2.0,England,2021,fixture\n"
        ),
    )
    with pytest.raises(load.ResolutionError, match="2 rows for premise_id"):
        load.load_premise_tables("fx-dairy", root)


# ---------------------------------------------------------------------- type coercion


def test_period_stays_an_integer_through_the_csv_round_trip(
    reference: load.ReferenceTables,
) -> None:
    """Plan §5.3: a period read back as 2021.0 indexes nothing and matches nothing."""
    period = reference.scenario_parameters["period"]
    assert period.dtype == "Int64"
    assert set(period.dropna().unique()) >= set(load.PERIOD_YEARS)
    assert 2021 in set(period.dropna())


def test_a_blank_numeric_stays_missing_rather_than_becoming_zero(
    reference: load.ReferenceTables,
) -> None:
    """The screen's whole premise: a blank capex read as 0 builds the unit free."""
    unit = reference.unit.set_index("unit_id")
    assert unit["lifetime"].dtype == "Int64"
    assert unit["capex"].isna().sum() == 15
    blank = unit[unit["capex"].isna()]
    assert not (blank["capex"] == 0).any()


def test_premise_years_are_integers(premise_root: Path) -> None:
    premise = load.load_premise_tables("fx-dairy", premise_root)
    assert premise.premise_record["data_year"].dtype == "Int64"
    assert int(premise.premise_record["data_year"].iloc[0]) == 2021
    assert premise.premise_process_vintage["commissioned_year"].dtype == "Int64"


def test_booleans_round_trip_as_booleans(reference: load.ReferenceTables) -> None:
    carrier = reference.carrier.set_index("carrier_id")
    assert carrier["may_import"].dtype == "boolean"
    assert bool(carrier.loc["natural_gas", "may_import"]) is True
    assert bool(carrier.loc["heat_lt60", "may_import"]) is False


# -------------------------------------------------------------------- FK resolution


def test_good_premise_resolves(
    reference: load.ReferenceTables, premise_root: Path
) -> None:
    premise = load.load_premise_tables("fx-dairy", premise_root)
    assert load.resolve_premise_references(reference, premise) is None


def test_unknown_activity_fails_loud(
    reference: load.ReferenceTables, tmp_path: Path
) -> None:
    """Plan §10: a premise naming an activity absent from the register fails at load."""
    root = write_premise_fixture(
        tmp_path / "p",
        premise_record=(
            "premise_id,carb3_activity,latitude,longitude,nation,data_year,source\n"
            "fx-dairy,Interstellar Cheese,52.0,-1.0,England,2021,fixture\n"
        ),
        premise_process_detail=(
            "premise_id,process_id,valid_from_year,known_capacity,provenance,confidence\n"
        ),
        premise_process_unit=(
            "premise_id,process_id,valid_from_year,unit_id,provenance,confidence\n"
        ),
        premise_process_vintage=(
            "premise_id,process_id,cohort_id,unit_id,commissioned_year,capacity_share,"
            "provenance,confidence\n"
        ),
    )
    premise = load.load_premise_tables("fx-dairy", root)
    with pytest.raises(load.ResolutionError, match="is not in activity_process_register"):
        load.resolve_premise_references(reference, premise)


def test_unknown_process_id_fails_loud(
    reference: load.ReferenceTables, tmp_path: Path
) -> None:
    root = write_premise_fixture(
        tmp_path / "p",
        premise_process_detail=(
            "premise_id,process_id,valid_from_year,known_capacity,provenance,confidence\n"
            "fx-dairy,kiln_pyroprocessing,2021,1.0,fixture,high\n"
        ),
    )
    premise = load.load_premise_tables("fx-dairy", root)
    with pytest.raises(load.ResolutionError, match="is not a process of"):
        load.resolve_premise_references(reference, premise)


def test_unknown_unit_id_fails_loud(
    reference: load.ReferenceTables, tmp_path: Path
) -> None:
    root = write_premise_fixture(
        tmp_path / "p",
        premise_process_unit=(
            "premise_id,process_id,valid_from_year,unit_id,provenance,confidence\n"
            "fx-dairy,boiler_steam_hot_water,2021,boiler_lt_unobtainium,fixture,high\n"
        ),
    )
    premise = load.load_premise_tables("fx-dairy", root)
    with pytest.raises(load.ResolutionError, match="is not in unit.csv"):
        load.resolve_premise_references(reference, premise)


# --------------------------------------------------------------- the §3.2 screen


def test_screen_drops_are_not_fatal(screen: load.AdmissionScreen) -> None:
    """Failures are dropped, not fatal; the run continues on what is left (§3.2)."""
    assert screen.admitted
    assert screen.dropped
    assert not (screen.admitted & {d.unit_id for d in screen.dropped})


def test_capex_leg_drops_every_blank_capex_unit(
    reference: load.ReferenceTables, screen: load.AdmissionScreen
) -> None:
    """CRITICAL (§5.3). A blank capex is read as zero and the unit is built free."""
    blank = set(reference.unit[reference.unit["capex"].isna()]["unit_id"])
    assert len(blank) == 15, "plan §3.2: 15 units blank"
    named = {d.unit_id for d in screen.dropped if d.leg == "capex"}
    assert named == blank
    assert not (blank & screen.admitted)


def test_cost_column_leg_drops_the_other_four(
    reference: load.ReferenceTables, screen: load.AdmissionScreen
) -> None:
    """Annuitisation and C2 (activity limited by capacity) are undefined without them."""
    unit = reference.unit
    expected = {"lifetime": 13, "fixed_opex": 15, "availability_factor": 13,
                "capacity_to_activity_factor": 13}
    assert {c: int(unit[c].isna().sum()) for c in expected} == expected
    incomplete = set(unit[unit[list(expected)].isna().any(axis=1)]["unit_id"])
    assert not (incomplete & screen.admitted)


def test_coefficient_leg_refuses_heat_exchanger_lt_steam(
    screen: load.AdmissionScreen,
) -> None:
    """CRITICAL (§5.3). The worked example of why the screen exists.

    ``unit.csv:12`` has capex 0, fixed_opex 0 and no coefficient rows at all, so it makes
    low-temperature heat from nothing, for nothing, on the dairy's own duties.
    """
    assert "heat_exchanger_lt_steam" not in screen.admitted
    legs = {d.leg for d in screen.dropped if d.unit_id == "heat_exchanger_lt_steam"}
    assert "coefficients" in legs


def test_coefficient_leg_counts(
    reference: load.ReferenceTables, screen: load.AdmissionScreen
) -> None:
    with_rows = set(reference.unit_input_output["unit_id"])
    without = set(reference.unit["unit_id"]) - with_rows
    assert len(without) == 25, "plan §3.2's 26, less generic_process_elec (note 22 §2)"
    assert {d.unit_id for d in screen.dropped if d.leg == "coefficients"} == without


def test_fuel_input_leg_catches_a_declared_fuel_that_is_never_burned(
    screen: load.AdmissionScreen,
) -> None:
    """Three units name a fuel_carrier_id and carry no fuel_input row, so it burns free."""
    for unit_id in ("lime_kiln_fluidbed_wdf", "refinery_fixed_mix_gas",
                    "refinery_flexible_mix_gas"):
        assert unit_id not in screen.admitted
        reasons = [d.detail for d in screen.dropped
                   if d.unit_id == unit_id and d.leg == "fuel_input"]
        assert reasons and "no fuel_input row" in reasons[0]


def test_fuel_input_leg_does_not_flag_a_unit_that_legitimately_burns_nothing(
    reference: load.ReferenceTables, screen: load.AdmissionScreen
) -> None:
    """A heat pump is driven by an electricity fuel_input; a store shifts what it does not burn.

    The leg classifies rather than flagging blindly, which is the reading
    ``validate_carb3_data.py`` takes and the reason it is not simply "has a fuel_input row".
    """
    flagged = {d.unit_id for d in screen.dropped if d.leg == "fuel_input"}
    storage = set(reference.unit[reference.unit["unit_class"] == "storage"]["unit_id"])
    assert not (storage & flagged)
    assert "heat_pump_lt_air" not in flagged


def test_price_leg_is_completeness_not_presence(
    reference: load.ReferenceTables,
) -> None:
    """CRITICAL (§5.3). ``heavy_fuel_oil`` is priced at 2021 only — the dangerous shape.

    A check that asks whether a carrier has *a* price counts five importable carriers as
    priced and lets heavy fuel oil burn free from 2025 on. The test is every period.
    """
    unpriced = load._unpriced_carriers(reference, load.PERIOD_YEARS)
    carrier = reference.carrier
    importable = set(carrier[carrier["may_import"].fillna(False)]["carrier_id"])
    assert len(importable) == 15
    assert len(importable) - len(unpriced) == 4, "plan §3.2: only 4 of 15"
    assert set(importable) - set(unpriced) == {
        "natural_gas", "light_fuel_oil", "coal", "electricity",
    }
    assert unpriced["heavy_fuel_oil"] == (2025, 2030, 2035, 2040, 2045, 2050)
    assert "hydrogen" in unpriced and len(unpriced["hydrogen"]) == 7


def test_price_leg_drops_boiler_lt_hydrogen_naming_carrier_and_periods(
    screen: load.AdmissionScreen,
) -> None:
    """CRITICAL (§5.3). Complete capex and coefficients; only the price check stops it."""
    assert "boiler_lt_hydrogen" not in screen.admitted
    drops = [d for d in screen.dropped if d.unit_id == "boiler_lt_hydrogen"]
    assert {d.leg for d in drops} == {"import_price"}
    assert "hydrogen" in drops[0].detail
    assert "every period" in drops[0].detail


def test_price_leg_escape_is_non_importable_not_on_site_production(
    reference: load.ReferenceTables, screen: load.AdmissionScreen
) -> None:
    """"or is produced on site" means the carrier cannot be imported at all.

    ``heat_lt60`` has ``may_import`` false, so a unit drawing it is never dropped for price:
    it can only arrive through C8 from a unit that paid for its own inputs. ``hydrogen`` is
    importable and unpriced, so on-site production is no escape — the LP would take the
    costless import instead.
    """
    carrier = reference.carrier.set_index("carrier_id")
    assert bool(carrier.loc["heat_lt60", "may_import"]) is False
    assert "heat_pump_lt_reject" in screen.admitted
    assert bool(carrier.loc["hydrogen", "may_import"]) is True


def test_measured_counts_match_the_plan(
    reference: load.ReferenceTables, screen: load.AdmissionScreen
) -> None:
    """The four figures plan §3.2 quotes, re-measured by the code under test.

    The plan's "41 of 137" is the **unit-leg** subtotal — the units that cannot be costed
    from their own row. Adding the price leg, which is a property of the *carrier*, takes it
    to 81 and leaves U at 56.

    Each figure is one lower than the plan's (the eligibility count one higher) since
    2026-09-24: ``generic_process_elec`` gained its coefficient rows when it became the
    producer of ``electric_service`` (note 22 §2), and one eligibility row was added for it.

    Note 22 Task 10 (2026-09-25) added ``chiller_electric_lt0``, the only unit reaching the
    ``cooling_lt0`` band: 138 units, one more admitted; the unit leg is unchanged, since the
    new unit is fully costed. It also rebuilt ``unit_eligibility``'s family rows from the join
    (``docs/notes/data/build/rebuild_eligibility_join.py``): the 1,852 no-grade-filter proxy
    rows became 2,442 rows (2,498 after the PR #64 units) that each serve a duty in C10's direction with a costed unit, so
    the table grew to 3,207 (3,263) while the rows reaching an incomplete unit fell from 363 to 50 —
    the survivors are worked-example and options rows, which are evidence and were kept.

    The PR #64 decisions (2026-09-25) added ``kiln_ht_gas`` (heat above 1000 °C) and
    ``engine_mot_gas`` (gas engine for shaft work), both fully costed: 140 units, 60 admitted,
    and the rebuilt rows grew to 2,498 of 3,263.
    """
    dropped = {d.unit_id for d in screen.dropped}
    unit_leg = {d.unit_id for d in screen.dropped if d.leg != "import_price"}
    assert len(reference.unit) == 140
    assert len(unit_leg) == 40
    assert len(dropped) == 80
    assert len(screen.admitted) == 60

    elig = reference.unit_eligibility
    assert len(elig) == 3263
    assert int(elig["unit_id"].isin(unit_leg).sum()) == 50
    assert int(elig["unit_id"].isin(dropped).sum()) == 1391


def test_a_drop_is_reported_once_per_failing_leg(screen: load.AdmissionScreen) -> None:
    """``dropped`` is the work list note 20 needs, so a unit failing twice says so twice."""
    per_unit = pd.Series([d.unit_id for d in screen.dropped]).value_counts()
    assert per_unit.max() > 1
    assert all(d.detail for d in screen.dropped)
    assert {d.leg for d in screen.dropped} <= {
        "capex", "cost_columns", "coefficients", "fuel_input", "import_price",
    }


def test_shortening_the_horizon_admits_more(reference: load.ReferenceTables) -> None:
    """The price leg is measured against the horizon it is given, not a hardcoded span.

    At 2021 alone ``heavy_fuel_oil`` is fully priced, so the units burning it come back.
    """
    narrow = load.screen_units(reference, periods=(2021,))
    wide = load.screen_units(reference, periods=load.PERIOD_YEARS)
    assert len(narrow.admitted) > len(wide.admitted)
    assert "heavy_fuel_oil" not in load._unpriced_carriers(reference, (2021,))
