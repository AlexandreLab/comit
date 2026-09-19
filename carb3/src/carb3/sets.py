"""Minimal A2; Q, U, U_q via the three-table join; C10 widening; the eligibility columns;
unservable-duty diagnosis.

**Minimal A2** (§3.3). Spec §3.9 is explicit that ``process_duty`` is derived at run time
from ``activity_process_register`` and ``activity_process_duty_profile``; it is not an input
table. A2 here reads those two tables to determine which duties each premise has, on which
carrier, at which ``grade_rank``. Only ``quantity`` is hand-written, taken from the worked
examples. No premise energy allocation, no A3, no A4 back-solve, no D10 refinement ladder.

**U_q is a three-table join, not a lookup** (§3.1). ``unit_eligibility.csv`` is keyed
``(unit_id, carb3_activity, process_id)`` — by *process*, not by duty — with no carrier or
grade column, and 142 of its rows carry a blank ``process_id`` and are activity-level supply.
Building U_q means joining it to ``activity_process_duty_profile`` for the duty and to
``unit.grade_out`` for C10 (heat grade cascade).

**C10 is enforced by widening U_q, not by a cascade variable** (§6.1). A unit is eligible for
any duty at or below its ``grade_out``. That is the ``MF-41`` Must form, not a debt.

**Infeasibility is an expected outcome, not an error** (§5.2). Before the LP is built, every
duty is checked for a non-empty eligible-unit set and any that is empty is reported by name,
with its premise, its period and the units the screen removed. No A7 relaxation ladder.

**Contract note — nothing here carries ``carb3_activity``, and the join needs it.**
``unit_eligibility`` is keyed ``(unit_id, carb3_activity, process_id)``, but neither
:class:`Duty` nor :class:`ModelSets` holds an activity, and 29 of the table's 215
``process_id`` values appear under more than one activity. Matching on ``process_id`` alone
would therefore read another activity's rows — including its ``max_share`` and ``min_duty``
— which is how a hard prohibition gets silently lifted. Until a ``carb3_activity`` field is
added to :class:`Duty`, the activity is threaded in explicitly: :func:`eligible_units` takes
it as a keyword-only argument and :func:`build_sets` reads it from ``premise_record``. No
frozen dataclass field was changed to do this.

Owed by T4, T5 and T6.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from carb3.load import (
    AdmissionScreen,
    PremiseTables,
    ReferenceTables,
    ResolutionError,
    UnitDrop,
    resolve_premise_references,
)

#: A duty's identity: premise, process, the carrier it is served on.
DutyKey = tuple[str, str, str]


class DutyDerivationError(ValueError):
    """The minimal A2 cannot derive a duty it must derive (§3.3)."""


@dataclass(frozen=True)
class Duty:
    """One element of Q — a duty at a premise, derived by the minimal A2 (§3.3).

    Structure (which duty, on which carrier, at which ``grade_rank``) is read from
    ``activity_process_duty_profile``; only ``quantity`` is hand-written.
    """

    premise_id: str
    process_id: str
    carrier_id: str
    #: ``None`` where the duty's carrier is not gradeable.
    grade_rank: int | None
    #: PJ/yr by period year.
    quantity: Mapping[int, float]

    @property
    def key(self) -> DutyKey:
        return (self.premise_id, self.process_id, self.carrier_id)


@dataclass(frozen=True)
class UnservableDuty:
    """A duty whose eligible-unit set is empty, named before the LP is built (§5.2)."""

    duty: DutyKey
    period: int
    #: The units the §3.2 screen removed that would otherwise have served it.
    removed: tuple[UnitDrop, ...]


@dataclass(frozen=True)
class ModelSets:
    """Q, U and U_q, plus the three eligibility columns the LP turns into bounds."""

    periods: tuple[int, ...]
    duties: tuple[Duty, ...]
    #: U — the admitted units, after the §3.2 screen.
    units: frozenset[str]
    #: U_q — eligible units per duty, already widened for C10 (heat grade cascade).
    eligible: Mapping[DutyKey, frozenset[str]]
    #: Upper bound of zero on new capacity before this year. 9 rows; 2030, 2035, 2040.
    earliest_year: Mapping[tuple[DutyKey, str], int]
    #: Upper bound on a unit's share of the duty in C1 (duty satisfaction). 4 rows, one of
    #: them ``boiler_lt_coal`` at ``Food Processing Centre`` at 0.00 — a hard prohibition.
    max_share: Mapping[tuple[DutyKey, str], float]
    #: Floor below which the unit is screened out of the duty. 15 rows, 0.01 to 0.50.
    min_duty: Mapping[tuple[DutyKey, str], float]


# ------------------------------------------------------------------- the minimal A2


def _activity_and_set(
    reference: ReferenceTables, premise: PremiseTables
) -> tuple[str, str]:
    """The premise's ``carb3_activity`` and the process set that applies (§3.1, §3.2)."""
    record = premise.premise_record.iloc[0]
    activity = str(record["carb3_activity"])
    register = reference.activity_process_register
    rows = register[register["carb3_activity"] == activity]
    declared = record.get("process_set_id")
    if pd.isna(declared) or not str(declared):
        defaults = rows[rows["is_default"].fillna(False)]
        return activity, str(defaults["process_set_id"].iloc[0])
    return activity, str(declared)


def _processes_at(premise: PremiseTables, data_year: int) -> pd.DataFrame:
    """The §3.10 rows valid at the base year.

    §3.10's completeness rule reads the rows valid at a given year as the premise's whole
    process list for that year, so an interval that closed before the base year — plant the
    site no longer has — contributes no duty.
    """
    detail = premise.premise_process_detail
    if detail.empty:
        return detail
    started = detail["valid_from_year"] <= data_year
    not_ended = detail["valid_to_year"].isna() | (detail["valid_to_year"] >= data_year)
    return detail[started & not_ended]


def _duty_profile_for(
    reference: ReferenceTables, activity: str, set_id: str, process_id: str
) -> pd.DataFrame:
    """The duty rows of one process, with §3.3's inheritance from the default set.

    A non-default set need not restate every row; where a process is absent from it the
    default set's rows apply.
    """
    profile = reference.activity_process_duty_profile
    rows = profile[
        (profile["carb3_activity"] == activity)
        & (profile["process_set_id"] == set_id)
        & (profile["process_id"] == process_id)
    ]
    if not rows.empty or set_id == "default":
        return rows
    return profile[
        (profile["carb3_activity"] == activity)
        & (profile["process_set_id"] == "default")
        & (profile["process_id"] == process_id)
    ]


def _units_run_by(
    reference: ReferenceTables,
    premise: PremiseTables,
    carb3_activity: str,
    process_id: str,
    valid_from_year: int,
) -> set[str]:
    """Which units a process runs: its §3.10.2 children, else its eligible candidates.

    §3.10's precedence rule — a parent row with children names the premise's existing plant;
    a parent with none means the plant is unknown and A4 resolves it from the candidate set.
    The minimal A2 has no A4, so the candidate set stands in for it, which is enough for the
    only question asked of it here: what kind of thing does this process make.
    """
    children = premise.premise_process_unit
    named = children[
        (children["process_id"] == process_id)
        & (children["valid_from_year"] == valid_from_year)
    ]
    if not named.empty:
        return {str(u) for u in named["unit_id"]}
    return {
        str(u)
        for u in _eligibility_rows(reference, carb3_activity, process_id)["unit_id"]
    }


def _makes_only_an_internal_product(
    reference: ReferenceTables, unit_ids: set[str]
) -> bool:
    """D16: every one of these units' primary output is a ``product`` it cannot export.

    A process of that shape has **no ``process_duty`` row at all** (§3.9). A cement kiln is
    the case: its units make ``clinker``, ``may_export`` false, so the duty row is gone and
    C8 (carrier balance) pins the kilns' activity instead — the grinder draws clinker off the
    balance and only the kilns produce it. The cement worked example §3.2 states exactly this
    outcome, and V32(b) checks it.
    """
    carrier = reference.carrier.set_index("carrier_id")
    io = reference.unit_input_output
    outputs = io[(io["unit_id"].isin(unit_ids)) & (io["role"] == "primary_output")]
    carriers = {str(c) for c in outputs["carrier_id"]}
    if not carriers:
        return False
    return all(
        str(carrier.loc[c, "carrier_kind"]) == "product"
        and bool(carrier.loc[c, "may_export"]) is not True
        for c in carriers
        if c in carrier.index
    )


def derive_duties(
    reference: ReferenceTables, premise: PremiseTables, periods: Sequence[int]
) -> tuple[Duty, ...]:
    """Minimal A2: derive Q for one premise from the register and the duty profile (§3.3).

    Structure is read, magnitude is hand-written. For each §3.10 process valid at the base
    year, every ``activity_process_duty_profile`` row of that process becomes a duty on that
    row's ``carrier_id`` at that row's ``grade_rank``, and its quantity is the premise's
    ``known_capacity`` for the process split by the row's ``duty_share`` — which is the
    arithmetic §3.3 defines for a share ("share of this process's energy that is this
    duty"). Nothing else about the magnitude is derived: it is flat across ``periods``,
    because this slice models no demand growth.

    **D16 (the site boundary on the carrier) removes the premise-level row, not the
    process.** A duty exists where the carrier is a service carrier — an ``intermediate``
    reached through a duty family — or a ``product`` that may be exported. A process whose
    output is a ``product`` the site cannot export keeps its register and profile entries and
    is fixed by C8 (carrier balance) instead, so it yields no duty here.

    Fails loud rather than yielding a thinner Q: an unknown activity, a process with no
    profile row, a missing ``known_capacity``, a gradeable carrier with no ``grade_rank``
    (§3.3's rule — a heat duty with no grade is invisible to C10 and fails silently), and a
    duty key that collides with one already derived.
    """
    periods = tuple(int(p) for p in periods)
    activity, set_id = _activity_and_set(reference, premise)
    record = premise.premise_record.iloc[0]
    premise_id = str(record["premise_id"])
    data_year = int(record["data_year"])

    carrier = reference.carrier.set_index("carrier_id")
    processes = _processes_at(premise, data_year)
    if processes.empty:
        raise DutyDerivationError(
            f"{premise_id}: no premise_process_detail row valid at data_year {data_year} "
            f"(§3.10, reason no_process_valid_in_base_year)"
        )

    duties: dict[DutyKey, Duty] = {}
    for _, process in processes.iterrows():
        process_id = str(process["process_id"])
        rows = _duty_profile_for(reference, activity, set_id, process_id)
        if rows.empty:
            raise DutyDerivationError(
                f"{premise_id}: process {process_id!r} has no "
                f"activity_process_duty_profile row for ({activity!r}, {set_id!r}) (§3.2)"
            )
        runs = _units_run_by(
            reference, premise, activity, process_id, int(process["valid_from_year"])
        )
        if _makes_only_an_internal_product(reference, runs):
            continue  # D16: the process keeps everything but its duty row (§3.9)

        capacity = process["known_capacity"]
        if pd.isna(capacity):
            raise DutyDerivationError(
                f"{premise_id}: process {process_id!r} has no known_capacity, so the "
                f"minimal A2 has no magnitude for its duties (§3.3, §3.10)"
            )

        for _, row in rows.iterrows():
            carrier_id = str(row["carrier_id"])
            if carrier_id not in carrier.index:
                raise ResolutionError(
                    f"{premise_id}: duty carrier {carrier_id!r} is not in carrier.csv"
                )
            spec = carrier.loc[carrier_id]
            kind = str(spec["carrier_kind"])
            exportable = bool(spec["may_export"]) is True
            if not (kind == "intermediate" or (kind == "product" and exportable)):
                continue  # D16: no premise-level duty row; C8 fixes its activity instead

            grade_rank: int | None = None
            if bool(spec["is_gradeable"]) is True:
                if pd.isna(row["grade_rank"]):
                    raise DutyDerivationError(
                        f"{premise_id}: duty {process_id!r} on gradeable carrier "
                        f"{carrier_id!r} has no grade_rank (§3.3); C10 cannot see it"
                    )
                grade_rank = int(row["grade_rank"])

            quantity = float(capacity) * float(row["duty_share"])
            duty = Duty(
                premise_id=premise_id,
                process_id=process_id,
                carrier_id=carrier_id,
                grade_rank=grade_rank,
                quantity={period: quantity for period in periods},
            )
            if duty.key in duties:
                raise DutyDerivationError(
                    f"{premise_id}: duty key {duty.key} is derived twice; DutyKey is "
                    f"(premise, process, carrier) and cannot separate them"
                )
            duties[duty.key] = duty

    return tuple(duties.values())


# ------------------------------------------------------------------------ U_q, the join


def _eligibility_rows(
    reference: ReferenceTables, carb3_activity: str, process_id: str
) -> pd.DataFrame:
    """The eligibility rows reaching one process, most specific first.

    **The documented rule for the 142 blank-``process_id`` rows** (plan §10): a blank
    ``process_id`` is *activity-level supply* and reaches every process of that activity. It
    is not a wildcard over the whole table — the ``carb3_activity`` still binds — and what
    stops it reaching a duty it should not is the carrier and grade test in
    :func:`eligible_units`, not the key. Where a unit is named by both an exact-process row
    and an activity-level row, the exact row is the more specific statement and its
    constraint columns win; ``drop_duplicates`` on the sorted frame is what picks it.
    """
    elig = reference.unit_eligibility
    rows = elig[elig["carb3_activity"] == carb3_activity].copy()
    exact = rows["process_id"] == process_id
    activity_level = rows["process_id"].isna() | (rows["process_id"] == "")
    rows = rows[exact | activity_level].copy()
    rows["_specific"] = (rows["process_id"] != process_id).map({False: 0, True: 1})
    return rows.sort_values("_specific", kind="stable").drop_duplicates("unit_id")


def _serves(unit: pd.Series, primary_outputs: set[str], duty: Duty) -> bool:
    """Whether one unit can serve one duty, on grade for heat and on carrier otherwise.

    **C10 (heat grade cascade), and its direction is the whole point.** A gradeable duty is
    served by a unit whose ``grade_out`` is at or *above* the duty's ``grade_rank`` — a
    grade-3 boiler serves a grade-2 duty by cascading down — and is **refused** by a unit
    below it, because nothing raises heat to a grade the plant cannot make. Getting that
    inequality backwards is a silent wrong answer, not a crash.

    A non-gradeable duty — ``motive_power``, ``cooling`` — has no cascade, so the test is the
    plain one: the unit's primary output is the duty's own carrier.
    """
    if duty.grade_rank is None:
        return duty.carrier_id in primary_outputs
    grade_out = unit["grade_out"]
    if pd.isna(grade_out):
        return False
    return int(grade_out) >= duty.grade_rank


def eligible_units(
    reference: ReferenceTables,
    duty: Duty,
    admitted: frozenset[str],
    *,
    carb3_activity: str,
) -> frozenset[str]:
    """U_q for one duty: the three-table join, widened for C10 (heat grade cascade).

    Joins ``unit_eligibility`` to ``activity_process_duty_profile`` for the duty and to
    ``unit.grade_out`` for the grade, admits a unit whose ``grade_out`` is at or above the
    duty's ``grade_rank``, and applies the documented rule for the 142 activity-level rows
    whose ``process_id`` is blank.

    ``carb3_activity`` is keyword-only and required: ``unit_eligibility`` is keyed
    ``(unit_id, carb3_activity, process_id)`` and :class:`Duty` carries no activity, so
    without it the join would have to match on ``process_id`` alone. 29 of the 215
    ``process_id`` values appear under more than one activity, so that would read another
    activity's rows — including its ``max_share`` and ``min_duty`` — for this duty.

    A unit whose ``max_share`` is 0.00 is removed here rather than bounded: the plan calls it
    "a hard prohibition", and a unit that may take no share of a duty is not eligible for it.
    Leaving it in U_q would make the prohibition depend on C1 (duty satisfaction) being
    written correctly downstream, which is the kind of single point of failure this screen
    exists to remove.
    """
    rows = _eligibility_rows(reference, carb3_activity, duty.process_id)
    if rows.empty:
        return frozenset()

    units = reference.unit.set_index("unit_id")
    io = reference.unit_input_output
    outputs = io[io["role"] == "primary_output"]
    primary_by_unit: dict[str, set[str]] = {}
    for unit_id, carrier_id in zip(outputs["unit_id"], outputs["carrier_id"], strict=True):
        primary_by_unit.setdefault(str(unit_id), set()).add(str(carrier_id))

    ceiling = max(duty.quantity.values()) if duty.quantity else 0.0
    eligible: set[str] = set()
    for _, row in rows.iterrows():
        unit_id = str(row["unit_id"])
        if unit_id not in admitted or unit_id not in units.index:
            continue
        if not _serves(units.loc[unit_id], primary_by_unit.get(unit_id, set()), duty):
            continue
        max_share = row["max_share"]
        if not pd.isna(max_share) and float(max_share) <= 0.0:
            continue
        floor = row["min_duty"]
        if not pd.isna(floor) and ceiling < float(floor):
            continue
        eligible.add(unit_id)
    return frozenset(eligible)


def build_sets(
    reference: ReferenceTables,
    premise: PremiseTables,
    screen: AdmissionScreen,
    periods: Sequence[int],
) -> ModelSets:
    """Assemble Q, U, U_q and the three eligibility columns for one premise.

    ``min_duty`` is applied against the duty's largest quantity over the horizon: "below this
    the unit is not offered at all" (§3.5.1) is a statement about the duty, and U_q is not
    period-indexed. ``earliest_year`` and ``max_share`` are carried out to the LP instead,
    where the period index exists; only the 0.00 ``max_share`` is resolved here, because a
    zero cap is a prohibition rather than a bound.
    """
    resolve_premise_references(reference, premise)
    periods = tuple(int(p) for p in periods)
    activity, _set_id = _activity_and_set(reference, premise)
    duties = derive_duties(reference, premise, periods)

    eligible: dict[DutyKey, frozenset[str]] = {}
    earliest_year: dict[tuple[DutyKey, str], int] = {}
    max_share: dict[tuple[DutyKey, str], float] = {}
    min_duty: dict[tuple[DutyKey, str], float] = {}

    for duty in duties:
        units = eligible_units(
            reference, duty, screen.admitted, carb3_activity=activity
        )
        eligible[duty.key] = units
        rows = _eligibility_rows(reference, activity, duty.process_id)
        for _, row in rows.iterrows():
            unit_id = str(row["unit_id"])
            if unit_id not in units:
                continue
            if not pd.isna(row["earliest_year"]):
                earliest_year[(duty.key, unit_id)] = int(row["earliest_year"])
            if not pd.isna(row["max_share"]):
                max_share[(duty.key, unit_id)] = float(row["max_share"])
            if not pd.isna(row["min_duty"]):
                min_duty[(duty.key, unit_id)] = float(row["min_duty"])

    return ModelSets(
        periods=periods,
        duties=duties,
        units=screen.admitted,
        eligible=eligible,
        earliest_year=earliest_year,
        max_share=max_share,
        min_duty=min_duty,
    )


def diagnose_unservable_duties(
    sets: ModelSets, screen: AdmissionScreen
) -> tuple[UnservableDuty, ...]:
    """Report every duty with an empty U_q, by premise and period, before the LP is built.

    An empty tuple means the LP can be built. A non-empty one is diagnosis, not an
    exception: §5.2 keeps this an expected outcome rather than an error.

    A duty is unservable in a period when no eligible unit can supply it *then* — either U_q
    is empty outright, or every member is gated out by an ``earliest_year`` later than the
    period. ``removed`` names the units the §3.2 screen took away, which is the run report's
    answer to "why", and note 20's work list.

    **``removed`` is the screen's whole work list, not this duty's share of it.**
    :class:`ModelSets` carries no ``carb3_activity`` and this function is given no
    :class:`~carb3.load.ReferenceTables`, so it cannot re-enter ``unit_eligibility`` to ask
    which of the dropped units this particular duty would have had. Narrowing it needs the
    contract note in the module header resolved first.
    """
    removed = tuple(sorted(screen.dropped, key=lambda d: (d.unit_id, d.leg)))

    unservable: list[UnservableDuty] = []
    for duty in sets.duties:
        units = sets.eligible.get(duty.key, frozenset())
        for period in sets.periods:
            available = {
                unit_id
                for unit_id in units
                if sets.earliest_year.get((duty.key, unit_id), period) <= period
            }
            if not available:
                unservable.append(UnservableDuty(duty.key, period, removed))
    return tuple(unservable)
