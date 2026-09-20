"""``python -m carb3`` — load, screen, derive, build, solve, write, report.

**This is the entry point, not a sixth module.** Plan §5.1 fixes the model at five modules
and the package docstring says not to add another; nothing here is model code. It is the
wiring between the five and a terminal: argument parsing, the order the stages run in, and
the run report §5.2 and §5.3 ask to be printed — the units the §3.2 screen dropped and why,
any unservable duty with its premise and period, the solver status, the variable and
constraint counts, the wall clock, and the objective decomposition.

The reference root stays configurable with its documented default (§3.1), so a caller may
point the run at a copy of ``docs/notes/data/`` without editing anything. Nothing under that
root is ever written.

**A premise that cannot be built is reported, not raised on** (§5.2). The run continues to
the next premise and the process exit status says how many failed, so one broken premise
does not hide the other two's answers.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from carb3 import build, ledger, survival
from carb3.load import (
    DEFAULT_PREMISE_ROOT,
    DEFAULT_REFERENCE_ROOT,
    PERIOD_YEARS,
    AdmissionScreen,
    ReferenceTables,
    load_premise_tables,
    load_reference_tables,
    screen_units,
)
from carb3.sets import ModelSets, build_sets, diagnose_unservable_duties

#: The three synthetic premises of plan §3.4, in the order the report prints them.
DEFAULT_PREMISES: tuple[str, ...] = ("mvp-minimal", "mvp-dairy", "mvp-cement")


@dataclass(frozen=True)
class PremiseRun:
    """One premise's outcome. ``blocked`` names why no LP was built, where that happened."""

    premise_id: str
    sets: ModelSets | None = None
    result: build.SolveResult | None = None
    tables: ledger.Ledger | None = None
    written: tuple[Path, ...] = ()
    row_violations: tuple[build.RowViolation, ...] = ()
    blocked: str = ""

    @property
    def ok(self) -> bool:
        return (
            not self.blocked
            and self.result is not None
            and self.result.termination_condition == "optimal"
            and not self.row_violations
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m carb3",
        description=(
            "Solve the CaRB3 pre-M2 demonstration slice over one or more synthetic "
            "premises and write the ledger."
        ),
    )
    parser.add_argument(
        "premises",
        nargs="*",
        default=list(DEFAULT_PREMISES),
        metavar="PREMISE_ID",
        help=f"premises to run; default all three ({', '.join(DEFAULT_PREMISES)})",
    )
    parser.add_argument(
        "--reference-root",
        type=Path,
        default=DEFAULT_REFERENCE_ROOT,
        help=(
            "the reference tables of plan §3.1, read and never written "
            f"(default: {DEFAULT_REFERENCE_ROOT})"
        ),
    )
    parser.add_argument(
        "--premise-root",
        type=Path,
        default=DEFAULT_PREMISE_ROOT,
        help=f"the synthetic premise tables of §3.4 (default: {DEFAULT_PREMISE_ROOT})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="where to write the parquet ledger; omit to solve and report without writing",
    )
    parser.add_argument(
        "--show-dropped",
        action="store_true",
        help="print the §3.2 screen's dropped-unit work list in full, not just its shape",
    )
    return parser.parse_args(argv)


def run_premise(
    premise_id: str,
    reference: ReferenceTables,
    screen: AdmissionScreen,
    axis: build.PeriodAxis,
    premise_root: Path,
    out_dir: Path | None,
) -> PremiseRun:
    """Load, derive, build, solve and (optionally) write one premise.

    Every stage that §5.2 calls an expected outcome returns a :class:`PremiseRun` carrying
    ``blocked`` rather than raising: an unservable duty and a non-optimal solve are both
    answers about the data, and a traceback would bury them.
    """
    periods = axis.years
    premise = load_premise_tables(premise_id, premise_root)
    sets = build_sets(reference, premise, screen, periods)

    unservable = diagnose_unservable_duties(sets, screen)
    if unservable:
        return PremiseRun(
            premise_id=premise_id,
            sets=sets,
            blocked=_explain_unservable(reference, premise, sets, screen, unservable),
        )

    vintages = survival.vintage_capacity(premise, reference.unit)
    surviving = survival.surviving_capacity(vintages, reference.unit, periods)
    model = build.build_model(sets, surviving, axis, reference)
    result = build.solve(model)
    if result.solution is None:
        return PremiseRun(
            premise_id=premise_id,
            sets=sets,
            result=result,
            blocked=f"the solve terminated {result.termination_condition!r}",
        )

    violations = build.check_constraint_rows(model, result)
    tables = ledger.build_ledger(result, sets, axis, reference)
    written: tuple[Path, ...] = ()
    if out_dir is not None:
        report = ledger.RunReport(
            premise_id=premise_id,
            screen=screen,
            n_variables=result.n_variables,
            n_constraints=result.n_constraints,
            wall_clock_seconds=result.wall_clock_seconds,
            status=result.termination_condition,
        )
        written = ledger.write_parquet(tables, report, out_dir)
    return PremiseRun(
        premise_id=premise_id,
        sets=sets,
        result=result,
        tables=tables,
        written=written,
        row_violations=violations,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    reference = load_reference_tables(args.reference_root)
    screen = screen_units(reference, PERIOD_YEARS)
    # `build` reads the same row to check the axis it is handed, and refuses an axis
    # discounted at a rate other than this one, so reading it through build's own accessor
    # is what keeps δ_t and the capex annuity on one number.
    rate = build._scalar_parameter(reference, "discount_rate")
    axis = build.period_axis(PERIOD_YEARS, rate)

    print("=" * 78)
    print("carb3 — the CaRB3 pre-M2 demonstration slice")
    print("=" * 78)
    print(f"reference root   {args.reference_root}")
    print(f"premise root     {args.premise_root}")
    print(f"periods          {', '.join(str(year) for year in axis.years)}")
    print(f"spans (years)    {', '.join(str(span) for span in axis.spans)}")
    print(f"discount rate    {rate}")
    _print_screen(screen, show_all=args.show_dropped)

    runs: list[PremiseRun] = []
    for premise_id in args.premises:
        # Run and report one at a time: the solver prints its own status line, and batching
        # the runs would stack every one of them above the first premise's section.
        run = run_premise(
            premise_id, reference, screen, axis, args.premise_root, args.out_dir
        )
        runs.append(run)
        _print_premise(run)

    failed = [run.premise_id for run in runs if not run.ok]
    print()
    print("-" * 78)
    print(
        f"{len(runs) - len(failed)} of {len(runs)} premises solved to optimality"
        + (f"; not solved: {', '.join(failed)}" if failed else "")
    )
    return 1 if failed else 0


# --------------------------------------------------------------------------------------
# The run report
# --------------------------------------------------------------------------------------


def _explain_unservable(
    reference: ReferenceTables,
    premise,
    sets: ModelSets,
    screen: AdmissionScreen,
    unservable,
) -> str:
    """Why a duty has no eligible unit — by unit, not by count (§5.2).

    :func:`carb3.sets.diagnose_unservable_duties` names the duty and the period and hands
    back the screen's whole work list, because ``ModelSets`` carries no ``carb3_activity``
    and it cannot re-enter ``unit_eligibility``. Here both are in hand, so the report can
    say the thing worth knowing: of the units eligible for that process, which the §3.2
    screen removed and which survived it and were refused on carrier or grade instead. The
    second group is the interesting one — it means the data is complete and the duty is
    simply classified onto a carrier nothing eligible makes.
    """
    from carb3.sets import _eligibility_rows  # a private join, used for diagnosis only

    activity = str(premise.premise_record.iloc[0]["carb3_activity"])
    io = reference.unit_input_output
    outputs = io[io["role"] == "primary_output"]
    primary: dict[str, set[str]] = {}
    for unit_id, carrier_id in zip(outputs["unit_id"], outputs["carrier_id"], strict=True):
        primary.setdefault(str(unit_id), set()).add(str(carrier_id))
    dropped_units = {drop.unit_id for drop in screen.dropped}
    duty_by_key = {duty.key: duty for duty in sets.duties}

    lines: list[str] = []
    for duty_key in sorted({row.duty for row in unservable}):
        periods = sorted({row.period for row in unservable if row.duty == duty_key})
        _premise_id, process_id, carrier_id = duty_key
        duty = duty_by_key[duty_key]
        grade = "" if duty.grade_rank is None else f" at grade_rank {duty.grade_rank}"
        lines.append(
            f"duty {process_id} on {carrier_id}{grade} has no eligible unit in "
            f"{len(periods)} of {len(sets.periods)} periods ({', '.join(str(p) for p in periods)})"
        )
        candidates = sorted(
            {str(unit_id) for unit_id in _eligibility_rows(reference, activity, process_id)["unit_id"]}
        )
        if not candidates:
            lines.append(f"    unit_eligibility names no unit for ({activity}, {process_id})")
            continue
        screened = [unit_id for unit_id in candidates if unit_id in dropped_units]
        survived = [unit_id for unit_id in candidates if unit_id not in dropped_units]
        if screened:
            lines.append(
                f"    removed by the §3.2 screen ({len(screened)}): {', '.join(screened)}"
            )
        for unit_id in survived:
            made = ", ".join(sorted(primary.get(unit_id, set()))) or "nothing"
            lines.append(f"    admitted but refused: {unit_id} — primary output {made}")
    return "\n".join(lines)


def _print_screen(screen: AdmissionScreen, *, show_all: bool) -> None:
    """The §3.2 screen's work list — "each dropped unit names the carrier and the periods
    whose price is missing, which is precisely what note 20 needs to record"."""
    dropped = sorted({drop.unit_id for drop in screen.dropped})
    print()
    print("-" * 78)
    print("§3.2 admission screen")
    print("-" * 78)
    print(
        f"admitted {len(screen.admitted)} units, dropped {len(dropped)} "
        f"over {len(screen.dropped)} findings"
    )
    by_leg: dict[str, list[str]] = {}
    for drop in screen.dropped:
        by_leg.setdefault(drop.leg, []).append(drop.unit_id)
    for leg in sorted(by_leg):
        units = sorted(set(by_leg[leg]))
        print(f"  {leg:<14} {len(units):>3} units")
    if show_all:
        for drop in sorted(screen.dropped, key=lambda d: (d.unit_id, d.leg)):
            print(f"    {drop.unit_id:<32} {drop.leg:<14} {drop.detail}")
    else:
        print("  (--show-dropped prints every unit with its reason)")


def _print_premise(run: PremiseRun) -> None:
    print()
    print("-" * 78)
    print(f"premise {run.premise_id}")
    print("-" * 78)

    if run.sets is not None:
        print(f"duties derived   {len(run.sets.duties)}")
        for duty in run.sets.duties:
            grade = "-" if duty.grade_rank is None else f"g{duty.grade_rank}"
            eligible = sorted(run.sets.eligible.get(duty.key, frozenset()))
            print(
                f"  {duty.process_id:<26} {duty.carrier_id:<14} {grade:<3} "
                f"{next(iter(duty.quantity.values())):>10.6f}  "
                f"|U_q|={len(eligible)}"
            )
        for carrier_id, units in sorted(run.sets.supply.items()):
            print(
                f"  internal supply (D16, no duty row): {carrier_id} <- "
                f"{', '.join(sorted(units))}"
            )
        if run.sets.no_magnitude:
            print(
                "  no duty derived — known_capacity is blank (§3.10 cannot state a known "
                f"zero): {', '.join(run.sets.no_magnitude)}"
            )

    if run.blocked:
        print("NOT SOLVED — no LP was built (§5.2: an expected outcome, not an error)")
        print(_indent(run.blocked, "  "))
        return

    result = run.result
    assert result is not None  # not blocked implies a result
    print(
        f"solver           status={result.status} "
        f"termination={result.termination_condition}"
    )
    print(f"problem size     {result.n_variables} variables, {result.n_constraints} constraints")
    print(f"wall clock       {result.wall_clock_seconds:.3f}s  (the G1 measurement)")
    print(f"objective        £{result.objective:,.4f}m")
    print(f"C8 row check     {len(run.row_violations)} violations against the built matrix")
    for violation in run.row_violations[:10]:
        print(f"    {violation.constraint} {violation.coords} residual={violation.residual:.3e}")

    if run.tables is not None:
        _print_costs(run.tables, result.objective)
        _print_disposal(run.tables)
        _print_pathway(run.tables)
    if run.written:
        print(f"written          {run.written[0].parent} ({len(run.written)} parquet files)")


def _print_costs(tables: ledger.Ledger, objective: float | None) -> None:
    by_term = tables.cost_by_term.groupby("term")["discounted"].sum()
    total = float(by_term.sum())
    print("objective decomposition, £m discounted to 2021:")
    for term in ledger.COST_TERMS:
        value = float(by_term.get(term, 0.0))
        share = value / total * 100 if total else 0.0
        print(f"  {term:<10} {value:>14,.4f}  {share:>6.1f}%")
    print(f"  {'total':<10} {total:>14,.4f}")
    if objective is not None:
        print(f"  {'reported':<10} {objective:>14,.4f}   (residual {total - objective:+.3e})")


def _print_disposal(tables: ledger.Ledger) -> None:
    disposal = tables.disposal
    if disposal.empty:
        return
    live = disposal[disposal["quantity"].abs() > 1e-9]
    if live.empty:
        print("disposal         nothing vented or dumped in any period")
        return
    print("disposal (a reported quantity, and what carbon is charged on):")
    pivot = live.pivot_table(
        index=["carrier_id", "carbon_charge"], columns="period", values="quantity"
    )
    print(_indent(pivot.to_string(float_format=lambda v: f"{v:10.5f}")))


def _print_pathway(tables: ledger.Ledger) -> None:
    dispatch = tables.dispatch
    live = dispatch[dispatch["activity"].abs() > 1e-9]
    if live.empty:
        return
    print("dispatch by unit and duty (PJ/yr, or Mt/yr on a mass duty):")
    pivot = live.pivot_table(
        index=["duty", "unit_id"], columns="period", values="activity", fill_value=0.0
    )
    print(_indent(pivot.to_string(float_format=lambda v: f"{v:10.5f}")))

    built = tables.build
    new = built[built["new_capacity"].abs() > 1e-9]
    if new.empty:
        print("capacity built   nothing built in any period")
        return
    print("capacity built (n_{u,t}):")
    pivot = new.pivot_table(
        index="unit_id", columns="period", values="new_capacity", fill_value=0.0
    )
    print(_indent(pivot.to_string(float_format=lambda v: f"{v:10.5f}")))


def _indent(text: str, prefix: str = "  ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())


if __name__ == "__main__":  # pragma: no cover - exercised through the Makefile
    pd.set_option("display.width", 200)
    sys.exit(main())
