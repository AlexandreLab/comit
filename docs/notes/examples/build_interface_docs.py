#!/usr/bin/env python3
"""Publish the two interface sections of the implementation spec as standalone documents.

Section 3 (the data model) is the contract with whoever supplies premise records;
section 8 (the output schema) is the contract with whoever consumes results. Both
are read by people who have no reason to hold the whole specification, so both are
published on their own — but *generated*, never copied by hand, because a field
table maintained in two places is a field table that will disagree with itself.

Emits, into docs/specs/interfaces/:
  input-data-model.md    implementation section 3
  output-data-schema.md  implementation section 8

Usage:  python3 docs/notes/examples/build_interface_docs.py
        python3 docs/notes/examples/build_interface_docs.py --check

--check regenerates in memory and exits non-zero if either file on disk differs,
so a hook or CI step can refuse a spec change that left the published copies behind.

No third-party packages. Standard library only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SPEC = REPO / "docs/specs/2026-08-19-carb3-site-decarbonisation-implementation.md"
OUT = REPO / "docs/specs/interfaces"
SPEC_LINK = "../2026-08-19-carb3-site-decarbonisation-implementation.md"

DOCS = [
    {
        "file": "input-data-model.md",
        "section": "3",
        "start": "## 3. Data model",
        "end": "## 4. Algorithms",
        "title": "CaRB3 Per-Site Decarbonisation — Input Data Model",
        "blurb": (
            "Every entity the model reads: the premise record and its long companions,\n"
            "the reference tables the modelling team maintains, and the optional per-site\n"
            "intelligence that replaces an assumption with a fact where it exists."
        ),
        "audience": (
            "**Who this is for.** Anyone supplying data to the model — principally the\n"
            "CaRB3 building-stock team, who own §3.1 and its companions. §1.6 of the\n"
            "specification states the same contract as a requirement with rationale, and is\n"
            "the better starting point if you are deciding *what to collect*; this document\n"
            "is the normative field-level detail you validate against."
        ),
        "sibling": ("output-data-schema.md", "what the model produces"),
    },
    {
        "file": "output-data-schema.md",
        "section": "8",
        "start": "## 8. Output schema",
        "end": "## 9. Performance and parallelisation",
        "title": "CaRB3 Per-Site Decarbonisation — Output Data Schema",
        "blurb": (
            "Every table a run produces, its keys, its units, and the traps that make two\n"
            "of them look interchangeable when they are not."
        ),
        "audience": (
            "**Who this is for.** Anyone consuming results — analysts, aggregation code,\n"
            "and anyone comparing one run against another. The evidence-tier and confidence\n"
            "fields are not decoration: they are the only way to tell how much of a result\n"
            "rests on a measurement rather than on a default, and §10 has validation tests\n"
            "that exist solely to keep them honest."
        ),
        "sibling": ("input-data-model.md", "what the model reads"),
    },
]


def read_spec() -> str:
    return SPEC.read_text(encoding="utf-8")


def slice_section(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


def section_date(body: str) -> str:
    """The section's own maintained date, so regeneration is content-stable.

    Stamping the *generation* date instead would make every re-run a diff, and a
    --check that always fails is a --check nobody runs.
    """
    m = re.search(r"\*Section last updated: (\d{4}-\d{2}-\d{2})\*", body)
    return m.group(1) if m else "undated"


def github_anchor(heading: str) -> str:
    """GitHub's heading-anchor rule, well enough that a miss lands on the file."""
    s = heading.strip().lstrip("#").strip().lower()
    s = s.replace("`", "")
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s+", "-", s).strip("-")


def anchor_map(text: str) -> dict[str, str]:
    """Section number -> anchor, for every numbered heading in the spec."""
    out: dict[str, str] = {}
    for m in re.finditer(r"^(#{2,4}) (\d+(?:\.\d+)*)\.? (.+)$", text, re.M):
        out[m.group(2)] = github_anchor(m.group(0))
    return out


def relink(body: str, own: str, anchors: dict[str, str]) -> str:
    """Point outward references at the spec; leave references inside this doc alone.

    A standalone extract is full of citations to sections that did not come with
    it. Left bare they are dead ends, so each becomes a link back to the source.
    """
    def repl(m: re.Match) -> str:
        num = m.group(1)
        if num == own or num.startswith(own + "."):
            return m.group(0)          # resolves within this document
        anchor = anchors.get(num, "")
        target = f"{SPEC_LINK}#{anchor}" if anchor else SPEC_LINK
        return f"[§{num}]({target})"

    # skip refs already inside a markdown link, and fenced code
    parts = re.split(r"(```.*?```)", body, flags=re.S)
    for i, part in enumerate(parts):
        if part.startswith("```"):
            continue
        parts[i] = re.sub(r"(?<!\[)§(\d+(?:\.\d+)*)(?!\d*\])", repl, part)
    return "".join(parts)


def fix_relative_paths(body: str) -> str:
    """The published copies sit one directory deeper than the spec."""
    body = body.replace("](../notes/", "](../../notes/")
    body = body.replace("](2026-08-19-carb3", "](../2026-08-19-carb3")
    return body


def build(doc: dict, spec: str, anchors: dict[str, str]) -> str:
    body = slice_section(spec, doc["start"], doc["end"]).rstrip()
    date = section_date(body)

    # the section heading becomes the document title
    body = body.split("\n", 1)[1].lstrip("\n")
    body = re.sub(r"^\*Section last updated: [\d-]{10}\*\n+", "", body)

    sib_file, sib_desc = doc["sibling"]
    spec_ref = SPEC_LINK
    header = f"""# {doc["title"]}

> **Generated file — do not edit.**
> Published from [implementation specification §{doc["section"]}]({spec_ref}), which is
> the single source of truth and was last revised {date}. To change anything here,
> edit that section and re-run
> `python3 docs/notes/examples/build_interface_docs.py`.

{doc["blurb"]}

{doc["audience"]}

**Companion:** [{sib_file}]({sib_file}) — {sib_desc}.

**Reading the references.** `§`-numbers inside this document resolve within it;
every other `§` links back to the specification. Labels of the form `A1`–`A9`
(algorithms), `C1`–`C9` (constraints), `V1`–`V17` (validation tests) and `D1`–`D11`
(design decisions) all refer to the specification — see its §1.3.

---

"""
    out = relink(header + body, doc["section"], anchors)
    return fix_relative_paths(out) + "\n"


def main() -> int:
    check = "--check" in sys.argv
    spec = read_spec()
    anchors = anchor_map(spec)
    OUT.mkdir(parents=True, exist_ok=True)

    stale = []
    for doc in DOCS:
        rendered = build(doc, spec, anchors)
        path = OUT / doc["file"]
        if check:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != rendered:
                stale.append(doc["file"])
        else:
            path.write_text(rendered, encoding="utf-8")
            print(f"  {path.relative_to(REPO)}  {len(rendered):,} bytes")

    if check:
        if stale:
            print("STALE, spec has moved on: " + ", ".join(stale))
            print("Run: python3 docs/notes/examples/build_interface_docs.py")
            return 1
        print("interface docs are in step with the spec")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
