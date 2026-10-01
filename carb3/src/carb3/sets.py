"""Minimal A2; Q, U, U_q via the three-table join; C10 widening; the eligibility columns;
unservable-duty diagnosis; the start-year adequacy check.

**Minimal A2** (§3.3). Spec §3.9 is explicit that ``process_duty`` is derived at run time
from ``activity_process_register`` and ``activity_process_duty_profile``; it is not an input
table. A2 here reads those two tables to determine which duties each premise has, on which
carrier, at which ``grade_rank``. Only ``quantity`` is hand-written, taken from the worked
examples. No premise energy allocation, no A3, no A4 back-solve, no D10 refinement ladder.

**It reads a third table, and note 21 §3.3 omitted it.** The duty profile carries no mass
carrier anywhere — 427 rows, 26 ``carrier_id`` values, neither ``cement`` nor ``clinker``
among them — so a mass duty cannot come from it. §3.1.2 already says where it comes from:
"Where the ``carrier_id`` is a product with ``may_export`` true, the row is the premise's
duty on that product under D5 — a cement works' 1.13 Mt/yr of cement is what C1 makes it
produce." So A2 reads ``premise_throughput`` too, for product duties only, at the base year
only (D12). Without it A2 read the cement works' ``MOT`` profile row against a
``known_activity`` that is 1.13 **Mt of cement** and produced a 1.13 **PJ** motive-power
duty no unit could serve.

**Export, and C9's gate, are assembled here too** (:func:`export_windows`). §5.2 declares
x_{c,k,t} where ``carrier.may_export`` is true and a ``premise_connection`` row carries the
carrier, which is premise-side knowledge, so the joins belong beside the others rather than
in ``build.py``.

**U_q is a three-table join, not a lookup** (§3.1). ``unit_eligibility.csv`` is keyed
``(unit_id, carb3_activity, process_id)`` — by *process*, not by duty — with no carrier or
grade column, and 142 of its rows carry a blank ``process_id`` and are activity-level supply.
Building U_q means joining it to ``activity_process_duty_profile`` for the duty and to
``unit.grade_out`` for C10 (the grade cascade).

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

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace

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
class ExportWindow:
    """One carrier the premise may export, and when (§5.2's x_{c,k,t}, C9's gate).

    ``periods`` is the subset of the horizon in which the export variable may be positive.
    An empty tuple means the variable is declared and bounded to zero throughout, which is
    what a premise in a cluster CO₂ transport never reaches looks like.
    """

    carrier_id: str
    periods: tuple[int, ...]
    #: The §3.7 network this carrier rides on, or ``""`` where C9 does not gate it.
    network: str


@dataclass(frozen=True)
class ExportRefusal:
    """A carrier the premise could have exported and may not, with the reason.

    The same shape of finding as :class:`~carb3.load.UnitDrop`, and for the same reason: an
    export with no price is free disposal, and free disposal of a `primary` carrier is the
    hole §5.2's ``may_dispose`` gate exists to close. Refusing it loudly is what stops a CHP
    building itself an electricity sink.
    """

    carrier_id: str
    reason: str


@dataclass(frozen=True)
class EligibilityDrop:
    """A unit that reached a process through ``unit_eligibility`` and was refused by one of
    its constraint columns, with the reason the run report prints.

    Unlike :class:`~carb3.load.UnitDrop` this is not an admission-screen finding: the unit is
    admitted to U and is refused only for this process. It is recorded only for a unit that
    would otherwise have been eligible, so a unit already refused by C10 (the grade cascade)
    or by the §3.2 screen is not reported here a second time.
    """

    premise_id: str
    process_id: str
    unit_id: str
    #: ``min_duty`` (the duty is below the unit's floor), ``max_share`` (a 0.00 cap, which
    #: is a prohibition and so removes the unit rather than bounding it) or
    #: ``min_duty_unchecked`` (a supply unit's floor could not be read because
    #: ``known_activity`` is blank; the unit is kept, so this is a note and not a drop).
    reason: str
    detail: str


@dataclass(frozen=True)
class ModelSets:
    """Q, U and U_q, plus the three eligibility columns the LP turns into bounds."""

    periods: tuple[int, ...]
    duties: tuple[Duty, ...]
    #: U — the admitted units, after the §3.2 screen.
    units: frozenset[str]
    #: U_q — eligible units per duty, already widened for C10 (the grade cascade).
    eligible: Mapping[DutyKey, frozenset[str]]
    #: Upper bound of zero on new capacity before this year. 9 rows; 2030, 2035, 2040.
    earliest_year: Mapping[tuple[DutyKey, str], int]
    #: Upper bound on a unit's share of the duty in C1 (duty satisfaction). 4 rows, one of
    #: them ``boiler_lt_coal`` at ``Food Processing Centre`` at 0.00 — a hard prohibition.
    max_share: Mapping[tuple[DutyKey, str], float]
    #: Floor below which the unit is screened out of the duty. 15 rows, 0.01 to 0.50.
    min_duty: Mapping[tuple[DutyKey, str], float]
    #: Carrier -> the units that may supply it although it carries **no duty**. See
    #: :func:`undutied_supply`: without this the cement kilns have no activity variable and
    #: the ``clinker`` node can never be met, and ``ccs_amine`` has none either.
    supply: Mapping[str, frozenset[str]] = field(default_factory=dict)
    #: Processes valid at the base year that yielded no duty because ``known_activity`` is
    #: blank. Reported by the run report rather than silently absorbed — see
    #: :func:`derive_duties`.
    no_activity: tuple[str, ...] = ()
    #: The subset of ``no_activity`` whose ``known_capacity`` is stated: they size an
    #: incumbent but derive no duty.
    capacity_only: tuple[str, ...] = ()
    #: ``earliest_year`` for the supply units above. They sit in no U_q, so the duty-keyed
    #: mapping cannot hold them, and without this ``ccs_amine``'s 2035 gate would not be
    #: applied to the one unit it exists for.
    supply_earliest_year: Mapping[tuple[str, str], int] = field(default_factory=dict)
    #: Carriers the premise may export, and in which periods (§5.2, C9). Empty where the
    #: premise has no exportable carrier with a connection and a price.
    export_windows: tuple[ExportWindow, ...] = ()
    #: Carriers refused an export variable, with the reason. The run report prints these
    #: beside the §3.2 screen's dropped units.
    export_refused: tuple[ExportRefusal, ...] = ()
    #: Units removed from a process by ``min_duty`` or a 0.00 ``max_share``. Reported beside
    #: the §3.2 screen's drops, since otherwise these vanish from U_q without a trace.
    eligibility_dropped: tuple[EligibilityDrop, ...] = ()
    #: Carrier -> the model units that may release their primary output to C8 (carrier
    #: balance) through z° because another model unit draws that carrier, although the
    #: carrier carries a duty. ``heat_pump_lt_air`` serves the 60-100 °C duty and also feeds
    #: ``heat_pump_ht``, which lifts that heat. Kept apart from ``supply``, which is D16 (the
    #: site boundary is a property of the carrier) supply only. See :func:`released_supply`.
    released: Mapping[str, frozenset[str]] = field(default_factory=dict)


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


def _primary_outputs(reference: ReferenceTables, unit_ids: set[str]) -> set[str]:
    """The ``primary_output`` carriers of a set of units — §5.1's c*_u, collected."""
    io = reference.unit_input_output
    outputs = io[(io["unit_id"].isin(unit_ids)) & (io["role"] == "primary_output")]
    return {str(c) for c in outputs["carrier_id"]}


def _makes_only_a_product(reference: ReferenceTables, unit_ids: set[str]) -> bool:
    """Every one of these units' primary output is a ``product`` carrier.

    **This is the test that decides whether a process states an energy duty at all**, and
    widening it from "an *internal* product" is what makes the cement works solvable. §3.9
    is written on the carrier, not on the export flag: a process whose unit's primary output
    is a `product` presents no *energy* duty, because what it makes is a substance and its
    heat and power need is a classification rather than a demand — "those classify the
    process's heat need for eligibility and grouping rather than stating a demand the LP
    must serve".

    The export flag then decides what happens next, exactly as §3.1.2 says:

    * ``may_export`` **false** — ``clinker`` — there is no duty at all, and C8 (carrier
      balance) pins the maker's activity through :func:`undutied_supply`;
    * ``may_export`` **true** — ``cement`` — the duty exists and is stated by
      ``premise_throughput`` in Mt/yr (D5, hybrid denominators), not by the duty profile.

    Reading only the internal case was the first of the two defects that stopped
    ``mvp-cement``: ``cement_grinding`` makes an exportable product, so the old test let its
    ``MOT`` profile row through and A2 labelled 1.13 **Mt** of cement as 1.13 **PJ** of
    motive power — a weight read as an energy, servable by nothing.
    """
    carrier = reference.carrier.set_index("carrier_id")
    carriers = _primary_outputs(reference, unit_ids)
    if not carriers:
        return False
    return all(
        str(carrier.loc[c, "carrier_kind"]) == "product"
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
    ``known_activity`` for the process split by the row's ``duty_share``, which is the
    arithmetic §3.3 defines for a share ("share of this process's energy that is this
    duty"). Nothing else about the magnitude is derived: it is flat across ``periods``,
    because this slice models no demand growth.

    **D16 (the site boundary on the carrier) removes the premise-level row, not the
    process.** A duty exists where the carrier is a service carrier — an ``intermediate``
    reached through a duty family — or a ``product`` that may be exported. A process whose
    output is a ``product`` the site cannot export keeps its register and profile entries and
    is fixed by C8 (carrier balance) instead, so it yields no duty here.

    **A product duty is a mass, and it comes from ``premise_throughput`` (§3.1.2).** The
    duty profile carries no mass carrier at all — its 427 rows name 26 carriers and neither
    ``cement`` nor ``clinker`` is among them — so a process that makes a substance has its
    magnitude nowhere else. §3.1.2 settles it: "Where the ``carrier_id`` is a product with
    ``may_export`` true, the row is the premise's duty on that product under D5 — a cement
    works' 1.13 Mt/yr of cement is what C1 makes it produce." Such a process therefore
    yields **no profile duty** — its ``MOT`` or ``HTH`` row classifies its energy need, and
    that need reaches C8 through the unit's own input coefficients — and exactly one
    throughput duty instead. Only the base year is read (D12); the rest is history.

    **A process with a blank ``known_activity`` yields no duty, and is reported rather than
    raised on.** §3.10 requires ``known_activity > 0 if present``, so the column cannot state
    a *known* zero, and two ``mvp-cement`` processes — ``clinker_cooling`` and
    ``site_services`` — have a genuine duty of 0.00000 PJ/yr and are written blank with the
    reason in ``provenance``. That is the premise README's finding 5 and §3.1.1's
    absence-is-not-zero trap in a table with no ``data_status`` column to resolve it. The
    minimal A2 has no A4 back-solve, so it cannot recover a magnitude it was not given; a
    duty it cannot size is one it must not invent. Silence is what would be wrong, so
    :func:`processes_without_activity` names every one of them and the run report prints
    them beside the screen's dropped units.

    Fails loud rather than yielding a thinner Q: an unknown activity, a process with no
    profile row, a gradeable carrier with no ``grade_rank`` (§3.3's rule — a heat duty with
    no grade is invisible to C10 and fails silently), and a duty key that collides with one
    already derived.
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
        if _makes_only_a_product(reference, runs):
            # The process makes a substance. Its duty, if it has one, is the mass stated by
            # premise_throughput below; its profile row is a classification (§3.1.2, §3.9).
            continue

        activity_size = process["known_activity"]
        if pd.isna(activity_size):
            continue  # no magnitude, so no duty; :func:`processes_without_activity` reports it

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

            quantity = float(activity_size) * float(row["duty_share"])
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

    for duty in _throughput_duties(reference, premise, processes, activity, periods):
        if duty.key in duties:
            raise DutyDerivationError(
                f"{premise_id}: throughput duty {duty.key} collides with a duty the duty "
                "profile already stated; one process cannot state the same duty twice"
            )
        duties[duty.key] = duty

    return tuple(duties.values())


def _throughput_duties(
    reference: ReferenceTables,
    premise: PremiseTables,
    processes: pd.DataFrame,
    activity: str,
    periods: Sequence[int],
) -> tuple[Duty, ...]:
    """The §3.1.2 product duties: one per base-year throughput row on an exportable product.

    "A row is a duty or it is evidence, and ``may_export`` decides which (D16)." An
    exportable product becomes a C1 (duty satisfaction) duty at the stated quantity, in
    Mt/yr because the carrier's ``denominator_kind`` is mass (D5, hybrid denominators). An
    internal product — ``clinker`` — becomes nothing here: §3.9 gives it no duty and
    :func:`undutied_supply` hands its makers to C8 (carrier balance) instead.

    **The duty is attached to the process that makes the product**, found by asking which
    base-year process runs a unit whose ``primary_output`` is that carrier. DutyKey is
    ``(premise, process, carrier)`` and U_q is a join on ``(unit_id, carb3_activity,
    process_id)``, so a duty with no process would have no eligible-unit set to build. A
    throughput row naming a product no base-year process makes is an input error and raises:
    silently dropping it would delete the premise's whole reason for existing.

    Only the base year is read (D12). A row at another ``data_year`` is history and is
    skipped without comment, which is what §3.1.2's "the rest is history" means.
    """
    throughput = premise.premise_throughput
    if throughput is None or throughput.empty:
        return ()

    record = premise.premise_record.iloc[0]
    premise_id = str(record["premise_id"])
    data_year = int(record["data_year"])
    carrier = reference.carrier.set_index("carrier_id")

    maker_of: dict[str, str] = {}
    for _, process in processes.iterrows():
        process_id = str(process["process_id"])
        runs = _units_run_by(
            reference, premise, activity, process_id, int(process["valid_from_year"])
        )
        for carrier_id in _primary_outputs(reference, runs):
            maker_of.setdefault(carrier_id, process_id)

    derived: list[Duty] = []
    for _, row in throughput.iterrows():
        if int(row["data_year"]) != data_year:
            continue  # D12: only the base year is read
        carrier_id = str(row["carrier_id"])
        spec = carrier.loc[carrier_id]
        if bool(spec["may_export"]) is not True:
            continue  # §3.1.2: an internal product's row is evidence, not a duty
        if carrier_id not in maker_of:
            raise DutyDerivationError(
                f"{premise_id}: premise_throughput states a duty on {carrier_id!r} and no "
                "process valid at the base year runs a unit whose primary_output is that "
                "carrier; C1 would have no eligible-unit set to satisfy it (§3.1.2)"
            )
        quantity = float(row["quantity"])
        if quantity <= 0:
            raise DutyDerivationError(
                f"{premise_id}: premise_throughput.quantity for {carrier_id!r} is "
                f"{quantity}; §3.1.2 requires > 0"
            )
        derived.append(
            Duty(
                premise_id=premise_id,
                process_id=maker_of[carrier_id],
                carrier_id=carrier_id,
                # A product carrier is not gradeable, so C10 (the grade cascade) has
                # nothing to say about it and _serves falls back to the carrier test.
                grade_rank=None,
                quantity={period: quantity for period in periods},
            )
        )
    return tuple(derived)


def processes_without_activity(premise: PremiseTables) -> tuple[str, ...]:
    """Processes valid at the base year whose ``known_activity`` is blank (§3.10).

    :func:`derive_duties` derives no duty for these. They are named here so the run report
    can print them: a duty that quietly does not exist is the failure mode, not the blank.
    """
    record = premise.premise_record.iloc[0]
    processes = _processes_at(premise, int(record["data_year"]))
    if processes.empty:
        return ()
    blank = processes[processes["known_activity"].isna()]
    return tuple(sorted({str(process_id) for process_id in blank["process_id"]}))


def processes_with_capacity_only(premise: PremiseTables) -> tuple[str, ...]:
    """The processes of :func:`processes_without_activity` that state a ``known_capacity``."""
    record = premise.premise_record.iloc[0]
    processes = _processes_at(premise, int(record["data_year"]))
    if processes.empty:
        return ()
    capacity_only = processes[
        processes["known_activity"].isna() & processes["known_capacity"].notna()
    ]
    return tuple(sorted({str(process_id) for process_id in capacity_only["process_id"]}))


def undutied_supply(
    reference: ReferenceTables,
    premise: PremiseTables,
    admitted: frozenset[str],
    dutied_carriers: frozenset[str] = frozenset(),
) -> tuple[dict[str, frozenset[str]], dict[tuple[str, str], int]]:
    """Carrier -> the units that may supply it although it carries **no duty** (§3.9).

    The reasoning is in :func:`_undutied_supply`'s docstring; this returns its supply sets
    and ``earliest_year`` and leaves out the ``min_duty`` drops, which :func:`build_sets`
    collects through the private form.
    """
    supply, earliest, _dropped = _undutied_supply(
        reference, premise, admitted, dutied_carriers
    )
    return supply, earliest


def _undutied_supply(
    reference: ReferenceTables,
    premise: PremiseTables,
    admitted: frozenset[str],
    dutied_carriers: frozenset[str] = frozenset(),
) -> tuple[
    dict[str, frozenset[str]], dict[tuple[str, str], int], tuple[EligibilityDrop, ...]
]:
    """Carrier -> the units that may supply it although it carries **no duty** (§3.9).

    **The D16 branch of :func:`derive_duties` needs a matching branch here, and the plan
    missed it.** Note 21 §2.2 puts z° (undispatched primary output) out of scope because
    "no internal ``product`` carriers in the synthetic premises", and that premise is false:
    ``mvp-cement``'s kilns make ``clinker``, a ``product`` with ``may_export`` false, and
    §3.9 therefore removes its premise-level duty row. The plan's own words are that "C8
    (carrier balance) pins the kiln through the ``clinker`` balance instead" — but a unit
    that serves no duty has no z_{u,q,t} and so has no activity to pin. Without the set
    returned here the ``clinker`` node has no producer, the grinder is forced to zero and C1
    (duty satisfaction) on the 1.13 Mt cement duty is infeasible.

    The set is the same three-table join U_q is: the eligible, admitted units of a
    product-making process, narrowed to those whose own primary output is a ``product``
    carrier that ``dutied_carriers`` does not name. The premise's own §3.10.2 children are
    unioned in, so named plant is never lost to an eligibility gap.

    **``ccs_amine`` is now here, and that is the second defect closed.** Its
    ``co2_captured`` is a ``product`` with ``may_export`` true and no duty — no premise
    states a throughput of captured CO₂ — so the train serves nothing and, before this,
    took no activity variable at all. It sits in the ``kiln_pyroprocessing`` eligibility
    set, so it arrives here with the kilns, and C8 (carrier balance) plus the export
    variable settle its level. ``cement`` is excluded by ``dutied_carriers``, because the
    grinder *is* dispatched — to the §3.1.2 throughput duty — and giving it a second,
    undispatched column would let one Mt of cement satisfy C1 and enter C8 as well.

    Returns the supply sets and, beside them, the ``earliest_year`` of each supply unit.
    These units sit in no U_q, so the duty-keyed mapping cannot carry their gate, and
    ``ccs_amine``'s 2035 row is the only one in the table that binds on a capture train.
    """
    activity, set_id = _activity_and_set(reference, premise)
    record = premise.premise_record.iloc[0]
    processes = _processes_at(premise, int(record["data_year"]))
    if processes.empty:
        return {}, {}, ()

    carrier = reference.carrier.set_index("carrier_id")
    io = reference.unit_input_output
    outputs = io[io["role"] == "primary_output"]
    primary_by_unit: dict[str, set[str]] = {}
    for unit_id, carrier_id in zip(outputs["unit_id"], outputs["carrier_id"], strict=True):
        primary_by_unit.setdefault(str(unit_id), set()).add(str(carrier_id))

    supply: dict[str, set[str]] = {}
    earliest: dict[tuple[str, str], int] = {}
    refused: list[EligibilityDrop] = []
    premise_id = str(record["premise_id"])
    for _, process in processes.iterrows():
        process_id = str(process["process_id"])
        if _duty_profile_for(reference, activity, set_id, process_id).empty:
            continue
        runs = _units_run_by(
            reference, premise, activity, process_id, int(process["valid_from_year"])
        )
        if not _makes_only_a_product(reference, runs):
            continue
        rows = _eligibility_rows(reference, activity, process_id)
        gate = {
            str(row["unit_id"]): int(row["earliest_year"])
            for _, row in rows.iterrows()
            if not pd.isna(row["earliest_year"])
        }
        floor = {
            str(row["unit_id"]): float(row["min_duty"])
            for _, row in rows.iterrows()
            if not pd.isna(row["min_duty"])
        }
        # min_duty is a floor on a duty magnitude, and this process has no duty. The
        # premise's own known_activity for it is the nearest thing the data holds, so it is
        # what a duty would have been sized at — so the floor is applied against that where
        # it exists, rather than dropped. ccs_amine's 0.25 clears the kiln's 0.85 Mt/yr.
        magnitude = process["known_activity"]
        candidates = {str(unit_id) for unit_id in rows["unit_id"]} | runs
        for unit_id in sorted(candidates & admitted):
            made = {
                carrier_id
                for carrier_id in primary_by_unit.get(unit_id, set())
                if carrier_id in carrier.index
                and str(carrier.loc[carrier_id, "carrier_kind"]) == "product"
                and carrier_id not in dutied_carriers
            }
            if not made:
                continue
            if unit_id in floor and pd.isna(magnitude):
                # Not a drop: the unit still supplies. The floor just cannot be read.
                refused.append(EligibilityDrop(
                    premise_id, process_id, unit_id, "min_duty_unchecked",
                    f"known_activity is blank, so min_duty {floor[unit_id]:g} was not checked; "
                    f"the unit is kept as a supplier of {', '.join(sorted(made))}",
                ))
            if (
                unit_id in floor
                and not pd.isna(magnitude)
                and float(magnitude) < floor[unit_id]
            ):
                refused.append(EligibilityDrop(
                    premise_id, process_id, unit_id, "min_duty",
                    f"known_activity {float(magnitude):g} is below min_duty "
                    f"{floor[unit_id]:g}; the unit supplies {', '.join(sorted(made))} "
                    "with no duty",
                ))
                continue
            for carrier_id in sorted(made):
                supply.setdefault(carrier_id, set()).add(unit_id)
            if unit_id in gate:
                for carrier_id in sorted(made):
                    key = (carrier_id, unit_id)
                    earliest[key] = min(earliest.get(key, gate[unit_id]), gate[unit_id])
    return (
        {carrier_id: frozenset(units) for carrier_id, units in sorted(supply.items())},
        earliest,
        tuple(refused),
    )


# ------------------------------------------------------------------- export, and C9's gate

#: §3.4's carrier → the §3.7 network it rides on. The two vocabularies differ on purpose and
#: only here: ``carrier.csv`` names the substance, ``infrastructure_scenario.csv`` names the
#: network, and for CO₂ they are ``co2_captured`` and ``co2_transport``. C9 (infrastructure
#: availability) gates a carrier only where this map has an entry; ``electricity`` has none,
#: because §3.7's ``grid_headroom`` rows are about connection capacity, which is C11's
#: business and out of this slice.
EXPORT_NETWORK: Mapping[str, str] = {
    "co2_captured": "co2_transport",
    "hydrogen": "hydrogen",
}

#: The two ``scenario_parameters`` series that can price an export. At least one must cover
#: every period or the carrier is refused an export variable: an unpriced export is free
#: disposal, and a `primary` carrier may not be disposed of at all (§5.2).
EXPORT_PRICE_PARAMETERS: tuple[str, ...] = ("export_price", "co2_transport_tariff")


def export_windows(
    reference: ReferenceTables, premise: PremiseTables, periods: Sequence[int]
) -> tuple[tuple[ExportWindow, ...], tuple[ExportRefusal, ...]]:
    """Which carriers the premise may export, and when — §5.2's x_{c,k,t} and C9's gate.

    §5.2 declares an export "where ``carrier.may_export`` is true **and** a
    ``premise_connection`` row carries that carrier", because "leaving the site means going
    onto a network". Three further tests apply here, and each removes a way the variable
    would otherwise be a hole in the model:

    * **C9 (infrastructure availability), for the carriers §3.7 gates.** The 63
      ``co2_transport`` rows are real, sourced data: four clusters turn available at 2030
      and five never do. The export is bounded to zero in every period the premise's
      cluster is unavailable. A premise with no ``cluster_id`` is outside every cluster,
      which is §3.7's beyond-the-radius case, and exports nothing.
    * **A price, for every period.** An export with no price is free disposal. ``primary``
      carriers may not be disposed of (§5.2's gate), so an unpriced export variable would
      reintroduce exactly what that gate forbids — a CHP could overbuild and dump the
      electricity. ``export_price`` covers ``electricity`` at six of the seven periods, not
      2021, so electricity is refused: the partial case is the dangerous one, and it is the
      same failure mode as ``heavy_fuel_oil``'s single ``import_price`` row one table away.
    * **The carrier must be one a unit at this premise can make.** Not tested here — C8
      (carrier balance) settles it, since a carrier nothing produces has an export pinned to
      zero by its own node.

    Returns the windows and the refusals. A refusal is a finding, not an error: the run
    report prints it beside the §3.2 screen's dropped units.
    """
    periods = tuple(int(period) for period in periods)
    record = premise.premise_record.iloc[0]
    cluster = record.get("cluster_id")
    cluster = "" if cluster is None or pd.isna(cluster) else str(cluster).strip()

    carrier = reference.carrier.set_index("carrier_id")
    connected = sorted({str(c) for c in premise.premise_connection["carrier_id"]})

    windows: list[ExportWindow] = []
    refused: list[ExportRefusal] = []
    for carrier_id in connected:
        if carrier_id not in carrier.index:
            continue
        if bool(carrier.loc[carrier_id, "may_export"]) is not True:
            continue

        priced, missing = _export_price_cover(reference, carrier_id, periods)
        if priced is None:
            refused.append(ExportRefusal(
                carrier_id,
                "no export_price and no co2_transport_tariff at "
                + (", ".join(str(period) for period in missing) if missing else "any period")
                + "; an unpriced export is free disposal (§5.2)",
            ))
            continue

        network = EXPORT_NETWORK.get(carrier_id, "")
        if not network:
            windows.append(ExportWindow(carrier_id, periods, ""))
            continue
        if not cluster or cluster == "none":
            refused.append(ExportRefusal(
                carrier_id,
                f"the premise states no cluster, so §3.7 marks {network} unavailable "
                "(C9, beyond the cluster radius)",
            ))
            continue
        available = _available_periods(reference, network, cluster, periods)
        windows.append(ExportWindow(carrier_id, available, network))
    return tuple(windows), tuple(refused)


def _export_price_cover(
    reference: ReferenceTables, carrier_id: str, periods: Sequence[int]
) -> tuple[str | None, tuple[int, ...]]:
    """The first :data:`EXPORT_PRICE_PARAMETERS` series covering every period, and the gaps.

    Completeness, not presence — the same test the §3.2 screen applies to ``import_price``.
    Where no series is complete the returned gap list is the **shortest** one, because that
    is the series closest to being usable and so the one worth reporting.
    """
    parameters = reference.scenario_parameters
    shortest: tuple[int, ...] = tuple(int(period) for period in periods)
    for parameter_id in EXPORT_PRICE_PARAMETERS:
        rows = parameters[
            (parameters["parameter_id"] == parameter_id)
            & (parameters["carrier_id"] == carrier_id)
        ]
        covered = {
            int(period) for period in rows["period"] if not pd.isna(period)
        }
        missing = tuple(period for period in periods if period not in covered)
        if not missing:
            return parameter_id, ()
        if len(missing) < len(shortest):
            shortest = missing
    return None, shortest


def _available_periods(
    reference: ReferenceTables, network: str, cluster: str, periods: Sequence[int]
) -> tuple[int, ...]:
    """C9: the periods §3.7 marks ``network`` available at ``cluster``.

    A period with no row is **unavailable**. §3.7 makes ``available`` required, so a gap is
    an absent statement rather than a permissive one, and reading it the other way would
    turn a missing row into an open pipeline.
    """
    rows = reference.infrastructure_scenario
    rows = rows[(rows["carrier"] == network) & (rows["cluster_id"] == cluster)]
    available = {
        int(period)
        for period, flag in zip(rows["period"], rows["available"], strict=True)
        if not pd.isna(period) and bool(flag) is True
    }
    return tuple(period for period in periods if period in available)


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


def _grade_families(reference: ReferenceTables) -> dict[str, str | None]:
    """carrier_id -> its ``grade_family`` (§3.4), ``None`` where it is not gradeable."""
    families: dict[str, str | None] = {}
    for carrier_id, gradeable, family in zip(
        reference.carrier["carrier_id"],
        reference.carrier["is_gradeable"],
        reference.carrier["grade_family"],
        strict=True,
    ):
        families[str(carrier_id)] = (
            str(family) if bool(gradeable) is True and not pd.isna(family) else None
        )
    return families


def _serves(
    unit: pd.Series,
    primary_outputs: set[str],
    duty: Duty,
    families: Mapping[str, str | None],
) -> bool:
    """Whether one unit can serve one duty: C10 (the grade cascade) for a graded duty, the
    carrier otherwise.

    **C10 reads its direction from the duty carrier's ``grade_family``, and never crosses
    families** (§5.5). A graded duty is served only by a unit whose primary output lies in
    the same family, and then:

    * **heat** — ``grade_out`` at or *above* the duty's ``grade_rank``: a grade-3 boiler
      serves a grade-2 duty by cascading down, and a grade-2 heat pump is refused a grade-3
      one, because nothing raises heat to a grade the plant cannot make;
    * **cooling** — ``grade_out`` at or *below* it, since rank 1 is the coldest band: a
      sub-zero plant serves a chilled-water duty, and a chilled-water chiller is refused a
      freezer store.

    Getting either inequality backwards, or letting a heat unit's ``grade_out`` stand in for
    a cooling one, is a silent wrong answer rather than a crash — before the family test a
    grade-2 heat pump sat in U_q for a grade-2 chilled-water duty.

    A non-gradeable duty — ``motive_power``, ``electric_service`` — has no cascade, so the
    test is the plain one: the unit's primary output is the duty's own carrier.
    """
    if duty.grade_rank is None:
        return duty.carrier_id in primary_outputs
    family = families.get(duty.carrier_id)
    if family is None or not any(families.get(c) == family for c in primary_outputs):
        return False
    grade_out = unit["grade_out"]
    if pd.isna(grade_out):
        return False
    if family == "cooling":
        return int(grade_out) <= duty.grade_rank
    return int(grade_out) >= duty.grade_rank


def eligible_units(
    reference: ReferenceTables,
    duty: Duty,
    admitted: frozenset[str],
    *,
    carb3_activity: str,
) -> frozenset[str]:
    """U_q for one duty; see :func:`_eligible_with_drops`, which also reports what it removed."""
    return _eligible_with_drops(
        reference, duty, admitted, carb3_activity=carb3_activity
    )[0]


def _eligible_with_drops(
    reference: ReferenceTables,
    duty: Duty,
    admitted: frozenset[str],
    *,
    carb3_activity: str,
) -> tuple[frozenset[str], tuple[EligibilityDrop, ...]]:
    """U_q for one duty: the three-table join, widened for C10 (the grade cascade).

    Joins ``unit_eligibility`` to ``activity_process_duty_profile`` for the duty and to
    ``unit.grade_out`` for the grade, admits a unit whose primary output is in the duty
    carrier's ``grade_family`` and whose ``grade_out`` reaches the duty's ``grade_rank`` in
    that family's direction — at or above it for heat, at or below it for cooling — and applies the documented rule for the 142 activity-level rows
    whose ``process_id`` is blank.

    ``carb3_activity`` is keyword-only and required: ``unit_eligibility`` is keyed
    ``(unit_id, carb3_activity, process_id)`` and :class:`Duty` carries no activity, so
    without it the join would have to match on ``process_id`` alone. 33 of the 228
    ``process_id`` values appear under more than one activity, so that would read another
    activity's rows — including its ``max_share`` and ``min_duty`` — for this duty.

    A unit whose ``max_share`` is 0.00 is removed here rather than bounded: the plan calls it
    "a hard prohibition", and a unit that may take no share of a duty is not eligible for it.
    Leaving it in U_q would make the prohibition depend on C1 (duty satisfaction) being
    written correctly downstream, which is the kind of single point of failure this screen
    exists to remove.

    Returns U_q and, beside it, an :class:`EligibilityDrop` for each unit that passed the
    screen and the C10 test and was then removed by ``max_share`` or ``min_duty``.
    """
    rows = _eligibility_rows(reference, carb3_activity, duty.process_id)
    if rows.empty:
        return frozenset(), ()

    units = reference.unit.set_index("unit_id")
    io = reference.unit_input_output
    outputs = io[io["role"] == "primary_output"]
    primary_by_unit: dict[str, set[str]] = {}
    for unit_id, carrier_id in zip(outputs["unit_id"], outputs["carrier_id"], strict=True):
        primary_by_unit.setdefault(str(unit_id), set()).add(str(carrier_id))

    families = _grade_families(reference)
    ceiling = max(duty.quantity.values()) if duty.quantity else 0.0
    eligible: set[str] = set()
    refused: list[EligibilityDrop] = []
    for _, row in rows.iterrows():
        unit_id = str(row["unit_id"])
        if unit_id not in admitted or unit_id not in units.index:
            continue
        if not _serves(
            units.loc[unit_id], primary_by_unit.get(unit_id, set()), duty, families
        ):
            continue
        max_share = row["max_share"]
        if not pd.isna(max_share) and float(max_share) <= 0.0:
            refused.append(EligibilityDrop(
                duty.premise_id, duty.process_id, unit_id, "max_share",
                f"max_share {float(max_share):.2f} is a prohibition on {duty.carrier_id}",
            ))
            continue
        floor = row["min_duty"]
        if not pd.isna(floor) and ceiling < float(floor):
            refused.append(EligibilityDrop(
                duty.premise_id, duty.process_id, unit_id, "min_duty",
                f"duty on {duty.carrier_id} peaks at {ceiling:g}, below min_duty "
                f"{float(floor):g}",
            ))
            continue
        eligible.add(unit_id)
    return frozenset(eligible), tuple(refused)


def build_sets(
    reference: ReferenceTables,
    premise: PremiseTables,
    screen: AdmissionScreen,
    periods: Sequence[int],
) -> ModelSets:
    """Assemble Q, U, U_q and the three eligibility columns for one premise.

    Two fields beyond Q, U and U_q: ``supply`` carries the D16-suppressed producers
    :func:`undutied_supply` finds, and ``no_activity`` the processes
    :func:`processes_without_activity` could not size.

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

    eligibility_dropped: list[EligibilityDrop] = []

    for duty in duties:
        units, refused = _eligible_with_drops(
            reference, duty, screen.admitted, carb3_activity=activity
        )
        eligibility_dropped.extend(refused)
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

    supply, supply_earliest_year, supply_dropped = _undutied_supply(
        reference,
        premise,
        screen.admitted,
        dutied_carriers=frozenset(duty.carrier_id for duty in duties),
    )
    windows, refused = export_windows(reference, premise, periods)
    sets = ModelSets(
        periods=periods,
        duties=duties,
        units=screen.admitted,
        eligible=eligible,
        earliest_year=earliest_year,
        max_share=max_share,
        min_duty=min_duty,
        supply=supply,
        no_activity=processes_without_activity(premise),
        capacity_only=processes_with_capacity_only(premise),
        supply_earliest_year=supply_earliest_year,
        export_windows=windows,
        export_refused=refused,
        eligibility_dropped=tuple(dict.fromkeys((*eligibility_dropped, *supply_dropped))),
    )
    return replace(sets, released=released_supply(reference, sets))


#: The roles that draw a carrier, as :data:`carb3.load.INPUT_ROLES` reads them.
_DRAWING_ROLES: frozenset[str] = frozenset({"fuel_input", "aux_input", "emission_input"})


def model_units(sets: ModelSets) -> frozenset[str]:
    """The units the LP holds: every unit in some U_q or supply set, intersected with U.

    Never ``sets.units`` alone, which is the global admitted set and would include units a
    process refused by ``min_duty`` or a 0.00 ``max_share``.
    """
    held = {unit_id for duty in sets.duties for unit_id in sets.eligible.get(duty.key, ())}
    held |= {unit_id for units in sets.supply.values() for unit_id in units}
    return frozenset(held & sets.units)


def released_supply(reference: ReferenceTables, sets: ModelSets) -> dict[str, frozenset[str]]:
    """Carrier -> the model units given a z° column on it: their primary output is that
    carrier and some *other* model unit draws it.

    The spec defines z° for any unit (implementation spec §5.2): activity whose primary
    output is released into the carrier balance rather than dispatched to a duty. Without it
    a unit drawing a carrier that other units make only as primary output has no source in
    C8 (carrier balance) and is held at zero, as ``heat_pump_ht`` was on ``heat_60_100``. A
    unit never feeds itself, and a carrier nobody else draws gets no column, so a premise
    with no such chain builds exactly the model it did before.

    A pure function of the model units, so :func:`carb3.build.screen_premise` recomputes it
    after dropping units and :func:`carb3.build.build_model` can refuse sets that are stale.
    """
    present = model_units(sets)
    io = reference.unit_input_output
    makers: dict[str, set[str]] = {}
    drawers: dict[str, set[str]] = {}
    for unit_id, carrier_id, role in zip(io["unit_id"], io["carrier_id"], io["role"], strict=True):
        unit_id, carrier_id, role = str(unit_id), str(carrier_id), str(role).strip()
        if unit_id not in present:
            continue
        if role == "primary_output":
            makers.setdefault(carrier_id, set()).add(unit_id)
        elif role in _DRAWING_ROLES:
            drawers.setdefault(carrier_id, set()).add(unit_id)
    released: dict[str, frozenset[str]] = {}
    for carrier_id in sorted(makers):
        feeding = frozenset(
            unit_id
            for unit_id in makers[carrier_id]
            if drawers.get(carrier_id, set()) - {unit_id}
        )
        if feeding:
            released[carrier_id] = feeding
    return released


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


#: Relative tolerance on a shortfall. A premise written so that its incumbents exactly meet
#: its duties (``mvp-minimal``) lands within floating-point noise of zero, which is not a gap.
SHORTFALL_TOLERANCE = 1e-9


@dataclass(frozen=True)
class StartYearShortfall:
    """A group of duties the incumbents cannot meet together in the first period.

    ``duties`` and ``units`` are the sink side of the minimum cut: every incumbent eligible for
    one of these duties is in ``units`` (or reaches it only through a ``max_share`` cap), and
    all of them are already running flat out. ``demand`` exceeds ``deliverable`` by
    ``shortfall``, in the duties' own units (PJ/yr, or Mt/yr for a mass duty).
    """

    period: int
    duties: tuple[DutyKey, ...]
    demand: float
    units: tuple[str, ...]
    deliverable: float
    shortfall: float


def deliverable_incumbent_activity(
    surviving: pd.DataFrame, unit: pd.DataFrame, period: int
) -> dict[str, float]:
    """``e_{u,t} × γ_u × α_u`` per incumbent unit in ``period``: the most C2 lets it produce."""
    if surviving is None or len(surviving) == 0:
        return {}
    indexed = unit.set_index("unit_id")
    standing = surviving[surviving["period"] == period]
    deliverable: dict[str, float] = {}
    for row in standing.itertuples(index=False):
        capacity = float(row.capacity)
        if capacity <= 0:
            continue
        unit_id = str(row.unit_id)
        gamma = float(indexed.loc[unit_id, "capacity_to_activity_factor"])
        alpha = float(indexed.loc[unit_id, "availability_factor"])
        deliverable[unit_id] = deliverable.get(unit_id, 0.0) + capacity * gamma * alpha
    return deliverable


def diagnose_start_year_shortfall(
    sets: ModelSets, surviving: pd.DataFrame, unit: pd.DataFrame
) -> StartYearShortfall | None:
    """The group of duties the incumbents cannot meet in the first period, or ``None``.

    C1 (duty satisfaction) is an equality, C2 (activity limited by available capacity) caps
    each unit at ``e × γ × α``, and C5 (no building in the start year) forbids any new
    capacity in the first period. So in that period the plant named in
    ``premise_process_unit`` must cover every duty on its own, and if it cannot the LP comes
    back infeasible with nothing to say which duty failed. This check runs before the LP is
    built and names the duties instead.

    **Why a flow, not a per-duty sum.** C2 is written per ``unit_id``, not per process, so one
    unit's capacity is a single pool that every duty it is eligible for draws on. Comparing
    each duty with the total capacity of its eligible incumbents counts that pool once per
    duty and passes plant that cannot cover all of them at once. The question is a
    transportation problem (incumbents supply, duties demand, an edge wherever the unit is in
    U_q), and it is answered exactly by a maximum flow. Where the flow falls short, the
    minimum cut names a group of duties whose combined demand exceeds everything the
    incumbents able to serve them can deliver.

    **What it does not check.** Units that supply an internal product with no duty (D16, the
    cement works' clinker kiln) also draw on C2, through C8 (carrier balance) rather than C1,
    and are left out. The flow is therefore a necessary condition only: a premise that fails
    it is certainly infeasible in the start year, and one that passes it can still be
    infeasible for a reason this does not see.

    ``surviving`` is :func:`carb3.survival.surviving_capacity`'s frame and ``unit`` the
    reference unit table, for γ and α. Edges follow U_q (``sets.eligible``); a ``max_share``
    caps its edge at ``share × demand`` exactly as the LP's dispatch bound does.
    ``earliest_year`` is ignored: it gates building, and no incumbent is built.
    """
    period = sets.periods[0]
    supply = deliverable_incumbent_activity(surviving, unit, period)
    demand = {
        duty.key: float(duty.quantity[period])
        for duty in sets.duties
        if float(duty.quantity[period]) > 0
    }
    total = sum(demand.values())
    if total == 0:
        return None

    edges: dict[tuple[str, DutyKey], float] = {}
    for duty_key in demand:
        for unit_id in sorted(sets.eligible.get(duty_key, frozenset())):
            if unit_id not in supply:
                continue
            share = sets.max_share.get((duty_key, unit_id))
            edges[(unit_id, duty_key)] = (
                float("inf") if share is None else float(share) * demand[duty_key]
            )

    flow, short_side = _max_flow(supply, demand, edges)
    if total - flow <= SHORTFALL_TOLERANCE * total:
        return None

    duties = tuple(sorted(key for key in demand if ("duty", key) in short_side))
    units = tuple(sorted(u for u in supply if ("unit", u) in short_side))
    cut_demand = sum(demand[key] for key in duties)
    capped = sum(
        capacity
        for (unit_id, duty_key), capacity in edges.items()
        if duty_key in duties and ("unit", unit_id) not in short_side
    )
    deliverable = sum(supply[u] for u in units) + capped
    return StartYearShortfall(
        period=period,
        duties=duties,
        demand=cut_demand,
        units=units,
        deliverable=deliverable,
        shortfall=cut_demand - deliverable,
    )


def _max_flow(
    supply: Mapping[str, float],
    demand: Mapping[DutyKey, float],
    edges: Mapping[tuple[str, DutyKey], float],
) -> tuple[float, set[tuple[str, object]]]:
    """Edmonds-Karp on source → unit → duty → sink, and the sink side of the minimum cut.

    The sink side is every node that can still reach the sink in the residual graph: the
    duties left short, the units that could serve them, the other duties those units are
    already busy with, and so on. It is the **smallest** group whose demand exceeds what its
    incumbents can deliver, which is what makes the report point at the shortfall rather
    than at the whole site.

    The graphs here have tens of nodes, so a plain breadth-first search per augmentation is
    ample. Nodes are visited in sorted order so the report is the same on every run.
    """
    source, sink = ("source", ""), ("sink", "")
    residual: dict[tuple, dict[tuple, float]] = {source: {}, sink: {}}

    def add(a: tuple, b: tuple, capacity: float) -> None:
        residual.setdefault(a, {})
        residual.setdefault(b, {})
        residual[a][b] = residual[a].get(b, 0.0) + capacity
        residual[b].setdefault(a, 0.0)

    for unit_id, amount in supply.items():
        add(source, ("unit", unit_id), amount)
    for duty_key, amount in demand.items():
        add(("duty", duty_key), sink, amount)
    for (unit_id, duty_key), capacity in edges.items():
        add(("unit", unit_id), ("duty", duty_key), capacity)

    epsilon = SHORTFALL_TOLERANCE * max(sum(demand.values()), 1.0) * 1e-3
    flow = 0.0
    while True:
        parent = _residual_search(residual, source, epsilon)
        if sink not in parent:
            break
        path = []
        node = sink
        while node != source:
            path.append((parent[node], node))
            node = parent[node]
        push = min(residual[a][b] for a, b in path)
        for a, b in path:
            residual[a][b] -= push
            residual[b][a] += push
        flow += push
    reverse: dict[tuple, dict[tuple, float]] = {node: {} for node in residual}
    for a, neighbours in residual.items():
        for b, capacity in neighbours.items():
            reverse[b][a] = capacity
    return flow, set(_residual_search(reverse, sink, epsilon))


def _residual_search(
    residual: Mapping[tuple, Mapping[tuple, float]], source: tuple, epsilon: float
) -> dict[tuple, tuple]:
    """Breadth-first search over edges with residual capacity; returns each node's parent.

    Handed the reversed graph, the edges it follows are those *into* each node, so it finds
    every node that can reach ``source`` rather than every node ``source`` can reach.
    """
    parent: dict[tuple, tuple] = {source: source}
    queue = deque([source])
    while queue:
        node = queue.popleft()
        for neighbour in sorted(residual[node], key=repr):
            if neighbour not in parent and residual[node][neighbour] > epsilon:
                parent[neighbour] = node
                queue.append(neighbour)
    return parent


def explain_start_year_shortfall(shortfall: StartYearShortfall) -> str:
    """The run report's sentence for a start-year shortfall."""
    duties = ", ".join(
        f"{process_id} on {carrier_id}" for _p, process_id, carrier_id in shortfall.duties
    )
    units = ", ".join(shortfall.units) if shortfall.units else "none"
    return (
        f"the incumbent plant cannot meet its duties in {shortfall.period}, the start year, "
        f"where C5 (no building in the start year) allows no new capacity: "
        f"{duties} need {shortfall.demand:.6f} together, and the incumbents able to serve "
        f"them ({units}) can deliver {shortfall.deliverable:.6f}, short by "
        f"{shortfall.shortfall:.6f}. Check premise_process_unit's capacity_share against "
        f"the duties each unit can serve, and premise_process_detail's known_activity "
        f"and known_capacity"
    )
