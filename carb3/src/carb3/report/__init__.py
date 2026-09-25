"""The site report: one self-contained HTML page per solved premise.

**Not model code, and not a sixth module.** The package docstring fixes the model at five
modules; this reads only the parquet ledger they write and imports nothing from ``build``,
``sets`` or ``load``. Like ``carb3.__main__``, it is wiring: here, between the ledger and a
browser.

``sankey_data``
    Parquet ledger directory -> one JSON document: per layer, the nodes and each period's
    links; the evolution series; the facts behind the tooltips.
``render``
    That document, the page template and the vendored d3 -> ``site_report.html``, with no
    network reference, so it opens offline.

``python -m carb3.report <premise dir>`` rebuilds a page from the parquet alone.
"""

from carb3.report.render import REPORT_FILENAME, write_report
from carb3.report.sankey_data import ReportDataError, build_report_data

__all__ = ["REPORT_FILENAME", "ReportDataError", "build_report_data", "write_report"]
