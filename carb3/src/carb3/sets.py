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

Owed by T4, T5 and T6.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from carb3.load import AdmissionScreen, PremiseTables, ReferenceTables, UnitDrop

#: A duty's identity: premise, process, the carrier it is served on.
DutyKey = tuple[str, str, str]


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
        raise NotImplementedError


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


def derive_duties(
    reference: ReferenceTables, premise: PremiseTables, periods: Sequence[int]
) -> tuple[Duty, ...]:
    """Minimal A2: derive Q for one premise from the register and the duty profile (§3.3)."""
    raise NotImplementedError


def eligible_units(
    reference: ReferenceTables, duty: Duty, admitted: frozenset[str]
) -> frozenset[str]:
    """U_q for one duty: the three-table join, widened for C10 (heat grade cascade).

    Joins ``unit_eligibility`` to ``activity_process_duty_profile`` for the duty and to
    ``unit.grade_out`` for the grade, admits a unit whose ``grade_out`` is at or above the
    duty's ``grade_rank``, and applies the documented rule for the 142 activity-level rows
    whose ``process_id`` is blank.
    """
    raise NotImplementedError


def build_sets(
    reference: ReferenceTables,
    premise: PremiseTables,
    screen: AdmissionScreen,
    periods: Sequence[int],
) -> ModelSets:
    """Assemble Q, U, U_q and the three eligibility columns for one premise."""
    raise NotImplementedError


def diagnose_unservable_duties(sets: ModelSets, screen: AdmissionScreen) -> tuple[UnservableDuty, ...]:
    """Report every duty with an empty U_q, by premise and period, before the LP is built.

    An empty tuple means the LP can be built. A non-empty one is diagnosis, not an
    exception: §5.2 keeps this an expected outcome rather than an error.
    """
    raise NotImplementedError
