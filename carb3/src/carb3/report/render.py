"""The report document, the template and the vendored d3 -> one HTML file.

Everything the page needs is inlined: the JSON, ``d3.min.js`` and ``d3-sankey.min.js``.
:func:`render` refuses a template that would reach the network, so the offline promise is
checked every time a page is written rather than trusted.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from carb3.report.sankey_data import build_report_data

#: The file written beside the parquet tables.
REPORT_FILENAME: str = "site_report.html"

_HERE = Path(__file__).resolve().parent
TEMPLATE_PATH: Path = _HERE / "template.html"
VENDOR_SCRIPTS: tuple[Path, ...] = (
    _HERE / "vendor" / "d3.min.js",
    _HERE / "vendor" / "d3-sankey.min.js",
)

_DATA_SLOT = "/*__REPORT_DATA__*/null"
_VENDOR_SLOT = "/*__VENDOR_SCRIPTS__*/"
_TITLE_SLOT = "__PREMISE_ID__"

#: What would make the page reach for the network: a remote src or href, or a fetch.
_NETWORK = re.compile(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//|\bfetch\s*\(|XMLHttpRequest""")


def render(data: dict[str, Any], template: str | None = None) -> str:
    """The HTML page for one premise's report document."""
    page = TEMPLATE_PATH.read_text(encoding="utf-8") if template is None else template
    for slot in (_DATA_SLOT, _VENDOR_SLOT, _TITLE_SLOT):
        if slot not in page:
            raise ValueError(f"the report template has no {slot!r} slot")
    offending = _NETWORK.search(page)
    if offending:
        raise ValueError(
            f"the report template reaches the network ({offending.group(0)!r}); "
            "the page must render offline"
        )
    vendor = "\n".join(_script_safe(path.read_text(encoding="utf-8")) for path in VENDOR_SCRIPTS)
    payload = _script_safe(json.dumps(data, ensure_ascii=False, allow_nan=False))
    title = _html_escape(str(data.get("premise_id", "")))
    # Replace the data slot last, so nothing inside the data can be read as a slot.
    return (
        page.replace(_TITLE_SLOT, title)
        .replace(_VENDOR_SLOT, vendor)
        .replace(_DATA_SLOT, payload)
    )


def write_report(premise_dir: Path) -> Path:
    """Rebuild ``site_report.html`` in ``premise_dir`` from the parquet there alone."""
    premise_dir = Path(premise_dir)
    path = premise_dir / REPORT_FILENAME
    path.write_text(render(build_report_data(premise_dir)), encoding="utf-8")
    return path


def _script_safe(text: str) -> str:
    """Text that cannot close the ``<script>`` element it is inlined into."""
    return text.replace("</", "<\\/")


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
