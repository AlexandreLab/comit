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

from collections.abc import Sequence
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


@dataclass(frozen=True)
class ReferenceTables:
    """The seven reference tables the slice reads, unmodified (§3.1)."""

    carrier: pd.DataFrame
    unit: pd.DataFrame
    unit_input_output: pd.DataFrame
    unit_eligibility: pd.DataFrame
    scenario_parameters: pd.DataFrame
    activity_process_duty_profile: pd.DataFrame
    activity_process_register: pd.DataFrame


@dataclass(frozen=True)
class PremiseTables:
    """The four synthetic premise-side tables (§3.4).

    ``process_duty`` is deliberately absent: spec §3.9 derives it at run time from
    ``activity_process_register`` and ``activity_process_duty_profile``, which is
    :func:`carb3.sets.derive_duties`.
    """

    premise_record: pd.DataFrame
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


def load_reference_tables(root: Path = DEFAULT_REFERENCE_ROOT) -> ReferenceTables:
    """Read the seven reference tables from ``root``.

    Fails loud on a missing file, a missing column or an unknown column, and keeps ``period``
    an integer through the CSV round-trip (§5.3, loader paths).
    """
    raise NotImplementedError


def load_premise_tables(
    premise_id: str, root: Path = DEFAULT_PREMISE_ROOT
) -> PremiseTables:
    """Read one synthetic premise's four tables from ``root``.

    Fails loud where a premise names a ``carb3_activity`` absent from
    ``activity_process_register``, or a ``unit_id`` or ``process_id`` that does not resolve
    against the reference tables (§10).
    """
    raise NotImplementedError


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
    """
    raise NotImplementedError
