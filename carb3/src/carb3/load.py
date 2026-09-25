"""Reference + premise tables -> typed records; the §3.2 screen.

The reference side is **read, not written** (plan §3). It is read from a configurable root
with a documented default resolved from the repo root — never a path literal, and never
relative to the caller's working directory. The premise side is synthetic CSV under
``carb3/data/premises/``.

The §3.2 admission screen is "the single most important guard in the build": a unit the
model cannot fully cost does not enter U, because a cost-minimiser reads a blank capex or an
unpriced fuel as free energy. Failures are dropped, not fatal; every drop is listed by
``unit_id`` with its reason in the run report.

Owed by T2.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

#: The repository root, derived from this file's own location
#: (``<repo>/carb3/src/carb3/load.py``), so the defaults below hold from any working
#: directory. An installed wheel has no repo above it and must pass the roots explicitly.
REPO_ROOT: Path = Path(__file__).resolve().parents[3]

#: Default reference root. CLAUDE.md's "COMIT never reads it" line is about the R model;
#: ``docs/notes/data/`` is an input to ``carb3`` (plan §3.1, T10).
DEFAULT_REFERENCE_ROOT: Path = REPO_ROOT / "docs" / "notes" / "data"

#: Default premise root — synthetic, CSV so every file a human edits stays diffable (§3.4).
DEFAULT_PREMISE_ROOT: Path = REPO_ROOT / "carb3" / "data" / "premises"

#: The real period vector (§6.4). A 4-year first gap and 5-year gaps thereafter: spec §5.1's
#: uniform-Δt assumption does not hold and neither of its two formulas can be used.
PERIOD_YEARS: tuple[int, ...] = (2021, 2025, 2030, 2035, 2040, 2045, 2050)

#: The cost fields of §3.2's first two legs. A blank in any of them is read as zero: the unit
#: is built free, annuitised over an undefined life, or has an undefined C2 (activity limited
#: by available capacity). Named here in the order the screen reports them.
COST_FIELDS: tuple[str, ...] = (
    "capex",
    "lifetime",
    "fixed_opex",
    "availability_factor",
    "capacity_to_activity_factor",
)

#: The ``unit_input_output`` roles that draw a carrier *in*. A unit's fuel bill is the union
#: of these and its declared ``unit.fuel_carrier_id`` (§3.6).
INPUT_ROLES: frozenset[str] = frozenset({"fuel_input", "aux_input", "emission_input"})


class SchemaError(ValueError):
    """A table is missing, missing a required column, or carries an unknown one.

    Fail-loud, per plan §5.3's loader paths. An unknown column is as much an error as a
    missing one: it means the table's schema moved and nothing here has been told.
    """


class ResolutionError(ValueError):
    """A premise names a reference key that does not resolve (plan §10)."""


# --------------------------------------------------------------------------- schemas
#
# ``required`` is what the model reads or the spec marks non-nullable; ``optional`` is the
# rest of the published header. A column in neither is unknown and raises. Reference schemas
# list the whole header, because ``docs/notes/data/`` is a controlled, generated-or-reviewed
# tree and a new column there is a schema change carb3 must be shown rather than tolerate.

_ReferenceSchema = tuple[tuple[str, ...], tuple[str, ...]]

REFERENCE_SCHEMA: dict[str, _ReferenceSchema] = {
    "carrier": (
        (
            "carrier_id", "carrier_name", "carrier_kind", "is_gradeable", "grade_family",
            "grade_rank", "grade_label", "is_indirect", "emission_factor_source", "biogenic_fraction",
            "carbon_charge", "denominator_kind", "may_dispose", "may_import", "may_export",
            "vector", "comit_commodity", "provenance",
        ),
        (),
    ),
    "unit": (
        (
            "unit_id", "unit_name", "unit_class", "spine", "duty_family", "process_id",
            "fuel_carrier_id", "grade_out", "grade_in_max", "capex", "fixed_opex",
            "lifetime", "availability_factor", "capacity_to_activity_factor",
            "area_per_capacity", "emissions_released", "min_viable_scale",
            "load_shape_override", "is_hybrid", "draws_ambient", "provenance",
            "confidence", "provenance_ref",
        ),
        (),
    ),
    "unit_input_output": (
        ("unit_id", "carrier_id", "coefficient", "role", "provenance", "confidence",
         "provenance_ref"),
        (),
    ),
    "unit_eligibility": (
        ("unit_id", "carb3_activity", "process_id", "min_duty", "max_share",
         "earliest_year", "provenance", "notes", "provenance_ref"),
        (),
    ),
    "scenario_parameters": (
        ("parameter_id", "carrier_id", "period", "value", "unit", "provenance",
         "confidence"),
        (),
    ),
    "activity_process_duty_profile": (
        ("carb3_activity", "process_set_id", "process_id", "duty_family", "carrier_id",
         "grade_rank", "duty_share", "share_low", "share_high", "evidence_tier",
         "provenance", "confidence"),
        (),
    ),
    "activity_process_register": (
        ("carb3_activity", "process_set_id", "set_name", "is_default", "process_id",
         "process_name", "is_optional", "equipment_examples", "provenance"),
        (),
    ),
    # §3.7, read for C9 (infrastructure availability) on CO₂ transport only. Its 63
    # ``co2_transport`` rows carry a sourced availability by cluster and period — four
    # clusters turn available at 2030 and five never do — which is better evidence about
    # when a capture train can run than ``unit_eligibility.earliest_year`` alone.
    "infrastructure_scenario": (
        ("scenario_id", "carrier", "cluster_id", "period", "available", "capacity_limit",
         "unit_tariff", "provenance"),
        (),
    ),
}

#: Premise schemas are spec §3.1, §3.10, §3.10.2 and §3.15. Unlike the reference side they
#: separate required from optional, because these files are hand-authored: a premise that
#: states no ``connection_id`` should not have to carry an empty column.
PREMISE_SCHEMA: dict[str, _ReferenceSchema] = {
    "premise_record": (
        ("premise_id", "carb3_activity", "latitude", "longitude", "nation", "data_year",
         "source"),
        ("floorspace", "process_set_id", "construction_year", "construction_year_band",
         "last_refurbishment_year", "cluster_id"),
    ),
    # §3.1.3. Read for one thing only in this slice: x_{c,k,t} is declared where
    # ``carrier.may_export`` is true **and** a connection row carries the carrier (§5.2),
    # because leaving the site means going onto a network. C11 (connection capacity) is
    # still out, so the capacity columns are carried and not read.
    "premise_connection": (
        ("premise_id", "connection_id", "carrier_id"),
        ("import_capacity", "export_capacity", "connection_voltage", "available_area"),
    ),
    # §3.1.2. "Where the carrier_id is a product with may_export true, the row is the
    # premise's duty on that product under D5 — a cement works' 1.13 Mt/yr of cement is
    # what C1 makes it produce." Where the product is internal (``may_export`` false) the
    # row is evidence and no duty (§3.9).
    "premise_throughput": (
        ("premise_id", "carrier_id", "quantity", "data_year", "data_status", "source"),
        (),
    ),
    "premise_process_detail": (
        ("premise_id", "process_id", "valid_from_year", "provenance", "confidence"),
        ("valid_to_year", "connection_id", "known_capacity"),
    ),
    "premise_process_unit": (
        ("premise_id", "process_id", "valid_from_year", "unit_id", "provenance",
         "confidence"),
        ("capacity_share",),
    ),
    "premise_process_vintage": (
        ("premise_id", "process_id", "cohort_id", "unit_id", "commissioned_year",
         "capacity_share", "provenance", "confidence"),
        (),
    ),
}

#: Columns coerced away from ``str`` after the round-trip. ``period`` and every other year
#: land in ``Int64`` rather than ``int64`` so a blank stays missing instead of becoming 0 —
#: the same failure the screen exists to stop, one table earlier.
_INTEGER_COLUMNS: dict[str, tuple[str, ...]] = {
    "carrier": ("grade_rank",),
    "unit": ("grade_out", "grade_in_max", "lifetime"),
    "unit_eligibility": ("earliest_year",),
    "scenario_parameters": ("period",),
    "activity_process_duty_profile": ("grade_rank",),
    "infrastructure_scenario": ("period",),
    "premise_record": ("data_year", "construction_year", "last_refurbishment_year"),
    "premise_throughput": ("data_year",),
    "premise_process_detail": ("valid_from_year", "valid_to_year"),
    "premise_process_unit": ("valid_from_year",),
    "premise_process_vintage": ("commissioned_year",),
}

_FLOAT_COLUMNS: dict[str, tuple[str, ...]] = {
    "carrier": ("biogenic_fraction",),
    "unit": (
        "capex", "fixed_opex", "availability_factor", "capacity_to_activity_factor",
        "area_per_capacity", "min_viable_scale",
    ),
    "unit_input_output": ("coefficient",),
    "unit_eligibility": ("min_duty", "max_share"),
    "scenario_parameters": ("value",),
    "activity_process_duty_profile": ("duty_share", "share_low", "share_high"),
    "infrastructure_scenario": ("capacity_limit", "unit_tariff"),
    "premise_record": ("latitude", "longitude", "floorspace"),
    "premise_throughput": ("quantity",),
    "premise_connection": (
        "import_capacity", "export_capacity", "connection_voltage", "available_area",
    ),
    "premise_process_detail": ("known_capacity",),
    "premise_process_unit": ("capacity_share",),
    "premise_process_vintage": ("capacity_share",),
}

_BOOLEAN_COLUMNS: dict[str, tuple[str, ...]] = {
    "carrier": ("is_gradeable", "is_indirect", "may_dispose", "may_import", "may_export"),
    "unit": ("is_hybrid", "draws_ambient"),
    "activity_process_register": ("is_default", "is_optional"),
    "infrastructure_scenario": ("available",),
}


@dataclass(frozen=True)
class ReferenceTables:
    """The eight reference tables the slice reads, unmodified (§3.1).

    ``infrastructure_scenario`` is the eighth, added when C9 (infrastructure availability)
    came partially back into scope for CO₂ transport.
    """

    carrier: pd.DataFrame
    unit: pd.DataFrame
    unit_input_output: pd.DataFrame
    unit_eligibility: pd.DataFrame
    scenario_parameters: pd.DataFrame
    activity_process_duty_profile: pd.DataFrame
    activity_process_register: pd.DataFrame
    infrastructure_scenario: pd.DataFrame


@dataclass(frozen=True)
class PremiseTables:
    """The six synthetic premise-side tables (§3.4).

    ``process_duty`` is deliberately absent: spec §3.9 derives it at run time from
    ``activity_process_register``, ``activity_process_duty_profile`` and — for a mass duty
    on an exportable product — ``premise_throughput`` (§3.1.2), which is
    :func:`carb3.sets.derive_duties`.

    ``premise_throughput`` and ``premise_connection`` were written by the premise lane and
    unread until now. The first carries the cement works' 1.13 Mt/yr duty; the second is
    what §5.2 requires before an export variable may be declared.
    """

    premise_record: pd.DataFrame
    premise_connection: pd.DataFrame
    premise_throughput: pd.DataFrame
    premise_process_detail: pd.DataFrame
    premise_process_unit: pd.DataFrame
    premise_process_vintage: pd.DataFrame


@dataclass(frozen=True)
class UnitDrop:
    """One unit refused by the §3.2 screen, with the reason the run report prints."""

    unit_id: str
    #: Which leg of the screen failed: ``capex``, ``cost_columns``, ``coefficients``,
    #: ``fuel_input`` or ``import_price``.
    leg: str
    #: Human-readable detail. For the price leg this names the carrier and the periods whose
    #: ``import_price`` is missing, which is what note 20 needs to record (§3.2).
    detail: str


@dataclass(frozen=True)
class AdmissionScreen:
    """The screen's output: the admitted set U, and the work list of what it removed."""

    admitted: frozenset[str]
    dropped: tuple[UnitDrop, ...]


# ----------------------------------------------------------------------------- reading


def _read_table(path: Path, required: Sequence[str], optional: Sequence[str]) -> pd.DataFrame:
    """Read one CSV as text, then check its header against the schema.

    Everything arrives as ``str`` so the column-level coercions below are the only place a
    type is decided. Fails loud on a missing file, a missing required column and an unknown
    column alike (§5.3).
    """
    if not path.is_file():
        raise SchemaError(f"{path}: no such table")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
    header = tuple(frame.columns)
    known = set(required) | set(optional)
    missing = [c for c in required if c not in header]
    unknown = [c for c in header if c not in known]
    if missing:
        raise SchemaError(f"{path}: missing required column(s) {', '.join(missing)}")
    if unknown:
        raise SchemaError(f"{path}: unknown column(s) {', '.join(unknown)}")
    for column in optional:
        if column not in header:
            frame[column] = pd.Series([pd.NA] * len(frame), dtype="string")
    return frame


def _coerce(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    """Give one table its types. Years and periods stay integral; blanks stay missing."""
    for column in _INTEGER_COLUMNS.get(name, ()):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="raise").astype("Int64")
    for column in _FLOAT_COLUMNS.get(name, ()):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="raise").astype("Float64")
    for column in _BOOLEAN_COLUMNS.get(name, ()):
        if column in frame.columns:
            frame[column] = (
                frame[column]
                .map({"TRUE": True, "FALSE": False, "true": True, "false": False})
                .astype("boolean")
            )
    return frame


def load_reference_tables(root: Path = DEFAULT_REFERENCE_ROOT) -> ReferenceTables:
    """Read the eight reference tables from ``root``.

    Fails loud on a missing file, a missing column or an unknown column, and keeps ``period``
    an integer through the CSV round-trip (§5.3, loader paths).
    """
    root = Path(root)
    frames = {
        name: _coerce(_read_table(root / f"{name}.csv", required, optional), name)
        for name, (required, optional) in REFERENCE_SCHEMA.items()
    }
    return ReferenceTables(**frames)


def load_premise_tables(
    premise_id: str, root: Path = DEFAULT_PREMISE_ROOT
) -> PremiseTables:
    """Read one synthetic premise's six tables from ``root``.

    The four files hold every premise; this returns the slice of each keyed on
    ``premise_id``. A premise with no ``premise_record`` row is an error, not an empty
    result.

    The frozen signature takes no :class:`ReferenceTables`, so the cross-table checks the
    module owes — a ``carb3_activity`` absent from the register, a ``unit_id`` or
    ``process_id`` that does not resolve — live in :func:`resolve_premise_references`, which
    :func:`carb3.sets.build_sets` calls once it has both sides.
    """
    root = Path(root)
    frames: dict[str, pd.DataFrame] = {}
    for name, (required, optional) in PREMISE_SCHEMA.items():
        frame = _coerce(_read_table(root / f"{name}.csv", required, optional), name)
        frames[name] = (
            frame[frame["premise_id"] == premise_id].reset_index(drop=True).copy()
        )
    if frames["premise_record"].empty:
        raise ResolutionError(
            f"{root}/premise_record.csv: no row for premise_id {premise_id!r}"
        )
    if len(frames["premise_record"]) > 1:
        raise ResolutionError(
            f"{root}/premise_record.csv: {len(frames['premise_record'])} rows for "
            f"premise_id {premise_id!r}; §3.1 is one row per premise"
        )
    return PremiseTables(**frames)


def resolve_premise_references(
    reference: ReferenceTables, premise: PremiseTables
) -> None:
    """Check every premise key against the reference tables, and raise on the first gap.

    Plan §10 routes "a premise names an activity absent from the register" to *fail loud at
    load*. The same holds for a ``process_id`` outside the premise's own activity and set,
    and for a ``unit_id`` outside ``unit``: each is a synthetic-data typo that would
    otherwise become a silently missing duty or a silently missing incumbent.
    """
    record = premise.premise_record.iloc[0]
    premise_id = str(record["premise_id"])
    activity = str(record["carb3_activity"])

    register = reference.activity_process_register
    activity_rows = register[register["carb3_activity"] == activity]
    if activity_rows.empty:
        raise ResolutionError(
            f"{premise_id}: carb3_activity {activity!r} is not in "
            f"activity_process_register (§3.1, D1)"
        )

    set_id = record.get("process_set_id")
    if pd.isna(set_id) or not str(set_id):
        defaults = activity_rows[activity_rows["is_default"].fillna(False)]
        if defaults.empty:
            raise ResolutionError(
                f"{premise_id}: activity {activity!r} has no default process set (§3.2)"
            )
        set_id = str(defaults["process_set_id"].iloc[0])
    else:
        set_id = str(set_id)
        if set_id not in set(activity_rows["process_set_id"]):
            raise ResolutionError(
                f"{premise_id}: process_set_id {set_id!r} is not a set of activity "
                f"{activity!r} (§3.2)"
            )

    known_processes = set(
        activity_rows[activity_rows["process_set_id"] == set_id]["process_id"]
    )
    known_units = set(reference.unit["unit_id"])

    for table_name in ("premise_process_detail", "premise_process_unit",
                       "premise_process_vintage"):
        frame = getattr(premise, table_name)
        for process_id in sorted(set(frame["process_id"].dropna())):
            if process_id not in known_processes:
                raise ResolutionError(
                    f"{premise_id}: {table_name}.process_id {process_id!r} is not a "
                    f"process of ({activity!r}, {set_id!r}) (§3.10, §3.15)"
                )
        if "unit_id" not in frame.columns:
            continue
        for unit_id in sorted(set(frame["unit_id"].dropna())):
            if unit_id not in known_units:
                raise ResolutionError(
                    f"{premise_id}: {table_name}.unit_id {unit_id!r} is not in unit.csv "
                    f"(§3.10.2, §3.15)"
                )

    _resolve_carrier_keys(reference, premise, premise_id)
    _resolve_cluster(reference, record, premise_id)


def _resolve_carrier_keys(
    reference: ReferenceTables, premise: PremiseTables, premise_id: str
) -> None:
    """Every ``carrier_id`` on the two §3.1 companion tables resolves, and with the right kind.

    §3.1.2 requires a throughput carrier to be ``denominator_kind = mass`` (D5, hybrid
    denominators); a throughput row on an energy carrier would state a duty in the wrong
    unit, which is precisely the failure that made the cement works unservable.
    """
    carrier = reference.carrier.set_index("carrier_id")
    for _, row in premise.premise_throughput.iterrows():
        carrier_id = str(row["carrier_id"])
        if carrier_id not in carrier.index:
            raise ResolutionError(
                f"{premise_id}: premise_throughput.carrier_id {carrier_id!r} is not in "
                "carrier.csv (§3.1.2)"
            )
        if str(carrier.loc[carrier_id, "denominator_kind"]) != "mass":
            raise ResolutionError(
                f"{premise_id}: premise_throughput names {carrier_id!r}, whose "
                "denominator_kind is not 'mass'; §3.1.2 requires one (D5)"
            )
    for _, row in premise.premise_connection.iterrows():
        carrier_id = str(row["carrier_id"])
        if carrier_id not in carrier.index:
            raise ResolutionError(
                f"{premise_id}: premise_connection.carrier_id {carrier_id!r} is not in "
                "carrier.csv (§3.1.3)"
            )


def _resolve_cluster(reference: ReferenceTables, record: pd.Series, premise_id: str) -> None:
    """The premise's ``cluster_id``, where it states one, is a cluster §3.7 knows.

    **``cluster_id`` is not a §3.1 field, and this slice carries it anyway.** §3.7's rule is
    that "a premise is assigned to the nearest in-scope cluster on ingest (A1)", and A1 is
    out of scope here, so the assignment has to be written down somewhere or C9
    (infrastructure availability) has nothing to read. It is optional: a premise with no
    ``cluster_id`` is treated as outside every cluster, which is §3.7's own
    beyond-the-radius case and the conservative reading. Recorded as a spec gap — §3 has no
    field for A1's output.
    """
    cluster_id = record.get("cluster_id")
    if cluster_id is None or pd.isna(cluster_id) or not str(cluster_id).strip():
        return
    cluster_id = str(cluster_id).strip()
    if cluster_id == "none":
        return
    known = {str(value) for value in reference.infrastructure_scenario["cluster_id"]}
    if cluster_id not in known:
        raise ResolutionError(
            f"{premise_id}: cluster_id {cluster_id!r} is not a cluster of "
            f"infrastructure_scenario.csv (§3.7); known clusters are {sorted(known)}"
        )


# ------------------------------------------------------------------- the §3.2 screen


def _unpriced_carriers(
    reference: ReferenceTables, periods: Sequence[int]
) -> dict[str, tuple[int, ...]]:
    """Importable carriers whose ``import_price`` does not cover every period.

    **The test is completeness, not presence.** ``heavy_fuel_oil`` carries exactly one
    ``import_price`` row, at 2021, and a check that asks only whether a carrier has *a*
    price counts it as priced and lets the model burn it free from 2025 on.
    """
    parameters = reference.scenario_parameters
    prices = parameters[parameters["parameter_id"] == "import_price"]
    priced: dict[str, set[int]] = {}
    for carrier_id, period in zip(prices["carrier_id"], prices["period"], strict=True):
        if pd.isna(period):
            continue
        priced.setdefault(str(carrier_id), set()).add(int(period))

    carrier = reference.carrier
    importable = carrier[carrier["may_import"].fillna(False)]["carrier_id"]
    gaps: dict[str, tuple[int, ...]] = {}
    for carrier_id in importable:
        missing = tuple(sorted(set(periods) - priced.get(str(carrier_id), set())))
        if missing:
            gaps[str(carrier_id)] = missing
    return gaps


def _fuel_input_leg(unit: pd.Series, roles: Iterable[str], declared_fuel: str) -> str:
    """Classify a unit with no ``fuel_input`` row. Empty string means the leg passes.

    Most units with no ``fuel_input`` row are not wrong, so this classifies rather than
    flagging blindly — the same reading ``validate_carb3_data.py`` takes. A store shifts a
    carrier it does not burn, a rooftop array draws ambient, and a heat exchanger or steam
    dryer is driven by an ``aux_input``. What is wrong is a unit that names the fuel it
    burns and then never consumes it, and a unit with no input row of any role at all: both
    produce output from nothing.
    """
    roles = set(roles)
    if "fuel_input" in roles:
        return ""
    if declared_fuel:
        return f"declares fuel_carrier_id {declared_fuel} but has no fuel_input row"
    if unit["unit_class"] == "storage":
        return ""
    if bool(unit["draws_ambient"]) is True:
        return ""
    if roles & INPUT_ROLES:
        return ""
    return "no fuel_input and no input row of any role"


def screen_units(
    reference: ReferenceTables, periods: Sequence[int] = PERIOD_YEARS
) -> AdmissionScreen:
    """Apply the §3.2 admission screen: a unit the model cannot fully cost does not enter U.

    A unit is admitted only if **all** of the following hold:

    * ``capex`` present and non-blank;
    * ``lifetime``, ``fixed_opex``, ``availability_factor`` and
      ``capacity_to_activity_factor`` all present;
    * at least one ``unit_input_output`` row;
    * a ``fuel_input`` row where its ``unit_class`` requires one;
    * every consumed carrier has an ``import_price`` for every period in ``periods``, or is
      produced on site.

    ``heat_exchanger_lt_steam`` is the worked example of why — zero capex, zero opex and no
    coefficient rows at all, eligible on three of the dairy's own duties.

    **"or is produced on site" means the carrier is not importable.** A carrier with
    ``may_import`` false can only reach the site through C8 (carrier balance) from a unit
    that made it, and that unit pays for its own inputs, so nothing is free. A carrier with
    ``may_import`` true and an incomplete price is free *however* it is produced, because the
    LP will take the costless import in preference to making it — on-site production is no
    escape from that leg, which is why ``boiler_lt_hydrogen`` is dropped.

    A unit failing several legs is reported once per leg, so ``dropped`` is the whole work
    list note 20 needs; the admitted set is U and ``{d.unit_id for d in dropped}`` is its
    complement.
    """
    periods = tuple(int(p) for p in periods)
    unpriced = _unpriced_carriers(reference, periods)

    io = reference.unit_input_output
    roles_by_unit: dict[str, set[str]] = {}
    drawn_by_unit: dict[str, set[str]] = {}
    for unit_id, carrier_id, role in zip(
        io["unit_id"], io["carrier_id"], io["role"], strict=True
    ):
        roles_by_unit.setdefault(str(unit_id), set()).add(str(role))
        if str(role) in INPUT_ROLES:
            drawn_by_unit.setdefault(str(unit_id), set()).add(str(carrier_id))

    admitted: list[str] = []
    dropped: list[UnitDrop] = []
    for _, unit in reference.unit.iterrows():
        unit_id = str(unit["unit_id"])
        roles = roles_by_unit.get(unit_id, set())
        declared_fuel = "" if pd.isna(unit["fuel_carrier_id"]) else str(unit["fuel_carrier_id"])
        drops: list[UnitDrop] = []

        if pd.isna(unit["capex"]):
            drops.append(UnitDrop(unit_id, "capex", "capex is blank: the unit is built free"))
        blank = [c for c in COST_FIELDS[1:] if pd.isna(unit[c])]
        if blank:
            drops.append(UnitDrop(
                unit_id, "cost_columns",
                f"blank {', '.join(blank)}: annuitisation or C2 is undefined",
            ))
        if not roles:
            drops.append(UnitDrop(
                unit_id, "coefficients",
                "no unit_input_output rows: the output is produced from nothing",
            ))
        fuel_reason = _fuel_input_leg(unit, roles, declared_fuel)
        if fuel_reason:
            drops.append(UnitDrop(unit_id, "fuel_input", fuel_reason))

        drawn = set(drawn_by_unit.get(unit_id, set()))
        if declared_fuel:
            drawn.add(declared_fuel)
        for carrier_id in sorted(drawn & set(unpriced)):
            missing = unpriced[carrier_id]
            span = (
                "every period"
                if len(missing) == len(periods)
                else ", ".join(str(p) for p in missing)
            )
            drops.append(UnitDrop(
                unit_id, "import_price",
                f"consumes {carrier_id}, which has no import_price for {span}",
            ))

        if drops:
            dropped.extend(drops)
        else:
            admitted.append(unit_id)

    return AdmissionScreen(frozenset(admitted), tuple(dropped))
