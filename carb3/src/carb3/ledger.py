"""Cost by term, carrier mix, dispatch, build, disposal -> parquet.

CSV is for hand-authored inputs; **outputs and any fixture written for M2 are parquet**
(§3.4, §7). The run report the ledger writes alongside them carries the §3.2 screen's
dropped-unit list, which is what note 20 records (§5.4), and the per-premise variable count,
constraint count and solve time that start the G1 (single-premise wall clock) measurement.

There is no attribution layer here: ``MF-52``, ``MF-53`` and ``MF-79`` are out (§6.3). The
ledger reports what the LP decided, it does not allocate emissions.

Owed by T8's reporting paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from carb3.build import PeriodAxis, SolveResult
from carb3.load import AdmissionScreen
from carb3.sets import ModelSets


@dataclass(frozen=True)
class Ledger:
    """The five output tables, long-form, one row per keyed observation."""

    #: One row per ``(period, term)`` over capex, opex, fuel and carbon. The terms must sum
    #: to the reported objective — that is one of the §5.3 test paths.
    cost_by_term: pd.DataFrame
    #: One row per ``(carrier_id, period)``: imported, produced, consumed, disposed.
    carrier_mix: pd.DataFrame
    #: z_{u,q,t} — one row per ``(unit_id, duty, period)``.
    dispatch: pd.DataFrame
    #: n_{u,t} and a_{u,t} — one row per ``(unit_id, period)``.
    build: pd.DataFrame
    #: d_{c,t} — one row per ``(carrier_id, period)``, the venting that carbon is charged on.
    disposal: pd.DataFrame


@dataclass(frozen=True)
class RunReport:
    """What the run says about itself, beside the ledger."""

    premise_id: str
    screen: AdmissionScreen
    n_variables: int
    n_constraints: int
    wall_clock_seconds: float
    status: str


def build_ledger(result: SolveResult, sets: ModelSets, axis: PeriodAxis) -> Ledger:
    """Decompose the solution into the five tables above."""
    raise NotImplementedError


def write_parquet(ledger: Ledger, report: RunReport, out_dir: Path) -> tuple[Path, ...]:
    """Write the ledger and the run report under ``out_dir``, returning the paths written."""
    raise NotImplementedError
