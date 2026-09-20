"""CaRB3 site energy system — the pre-M2 demonstration slice.

A least-cost industrial decarbonisation pathway over three synthetic premises, built on the
real reference tables under ``docs/notes/data/``. The specification is the live
implementation spec §5; the build is planned in ``docs/notes/21_mvp_slice_implementation_plan.md``.

Five modules, per plan §5.1 — the review reduced seven to five, so do not add a sixth:

``load``
    Reference + premise tables -> typed records; the §3.2 screen.
``sets``
    Minimal A2; Q, U, U_q via the three-table join; C10 (heat grade cascade) widening;
    ``earliest_year`` / ``max_share`` / ``min_duty``; unservable-duty diagnosis.
``survival``
    D11 (existing plant has an age) survival function, computed before the LP.
``build``
    Variables, C1 (duty satisfaction) to C5 (no building in the start year), C8 (carrier
    balance), C10 (heat grade cascade), objective, solve.
``ledger``
    Cost by term, carrier mix, dispatch, build, disposal -> parquet.

``carb3.__main__`` is the entry point — ``python -m carb3``, or ``make carb3-run`` — and is
not a sixth module: it holds no model code, only the order the five stages run in and the
run report §5.2 and §5.3 ask to be printed.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
