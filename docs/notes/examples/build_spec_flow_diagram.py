#!/usr/bin/env python3
"""Generate a data-flow diagram of the CaRB3 per-site decarbonisation design.

Reads the implementation specification and derives the diagram from it, rather
than from a hand-maintained copy that would drift the moment the spec changed.

Sources in the spec:
  entities    - the `### 3.x` and `#### 3.1.x` headings of the data model
  algorithms  - the `### A1 - ...` headings of section 4
  edges       - the INPUT:/OUTPUT: lines of each algorithm's pseudocode block,
                plus entity names mentioned in the body (read edges)

Emits, into docs/specs/diagrams/:
  spec_journey.md     Mermaid sequence diagram: the journey from ingesting a premise
                      to writing its pathway, step by step
  spec_data_model.md  Mermaid class diagram: entities, their fields and foreign keys
  spec_flow.svg       dependency-free SVG overview; drop into Mural or any SVG tool

The two Markdown files preview in VS Code with a Mermaid extension and render
inline on GitHub.

No third-party packages. Standard library only.

Usage:  python3 docs/notes/examples/build_spec_flow_diagram.py
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SPEC = REPO / "docs/specs/archive/2026-08-19-carb3-site-decarbonisation-implementation.md"
OUT = REPO / "docs/specs/archive/diagrams"

# Some algorithms name an entity in a form the heading does not use: A1 takes
# `raw_premise_records`, not `premise_record`. Aliases keep the match honest
# rather than loosening the word-boundary rule for everything.
ALIASES = {
    "premise_record": [r"raw_premise_records", r"premise records"],
}

# Entities that are reference/scenario data rather than premise data get a
# different colour, so the diagram distinguishes what the stock model supplies
# from what the modelling team maintains.
INPUT_ENTITIES = {
    "premise_record",
    "premise_energy",
    "premise_throughput",
    "premise_connection",
    "premise_process_detail",
    "premise_process_vintage",
    "premise_measured_emissions",
    "premise_operating_profile",
    "premise_weekly_profile",
}
SCENARIO_ENTITIES = {"infrastructure_scenario", "scenario_parameters"}
OUTPUT_ENTITIES = {"site_pathway"}


def read_spec() -> str:
    return SPEC.read_text(encoding="utf-8")


def find_entities(text: str) -> list[str]:
    """Entity names from the data-model headings."""
    pattern = re.compile(r"^#{3,4} 3\.[\d.]+ `([a-z_]+)`", re.M)
    return [m.group(1) for m in pattern.finditer(text)]


def find_entity_fields(text: str) -> dict[str, list[dict]]:
    """Field tables of the data model, one list per entity.

    Foreign keys are written as an arrow to a backticked entity name, and may
    appear in either the Key column or the Validation column, so both are
    scanned.
    """
    heads = list(re.finditer(r"^#{3,4} 3\.[\d.]+ `([a-z_]+)`.*$", text, re.M))
    fields: dict[str, list[dict]] = {}
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        rows = []
        for line in text[h.end() : end].split("\n"):
            m = re.match(r"^\| `([a-z_0-9]+)` \| ([^|]+)\| [^|]*\| ([^|]*)\| ([^|]*)\| ([^|]*)\|", line)
            if not m:
                continue
            name, typ, req, key, valid = (g.strip() for g in m.groups())
            fk = re.search(r"→ `([a-z_]+)`", key + " " + valid)
            rows.append(
                {
                    "name": name,
                    "type": typ.split("{")[0].strip() or "string",
                    "required": req == "yes",
                    "pk": "PK" in key,
                    "fk": fk.group(1) if fk else None,
                }
            )
        if rows:
            fields[h.group(1)] = rows
    return fields


def find_algorithms(text: str) -> list[dict]:
    """Algorithms with their pseudocode block, in document order."""
    heads = list(re.finditer(r"^### (A\d+) — (.+)$", text, re.M))
    algos = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[h.start() : end]
        # an algorithm may open with a formula block before its pseudocode
        # (A4 does), so take the first block that actually declares INPUT:
        blocks = re.findall(r"```\n(.*?)```", body, re.S)
        block = next((b for b in blocks if "INPUT:" in b), blocks[0] if blocks else "")
        prose = re.sub(r"```\n.*?```", "", body, flags=re.S)
        algos.append(
            {
                "id": h.group(1),
                "title": h.group(2).strip(),
                "block": block,
                "prose": prose,
            }
        )
    return algos


def io_lines(block: str) -> tuple[str, str, str]:
    """Split a pseudocode block into its INPUT line, OUTPUT line, and body."""
    inp = out = ""
    body_lines = []
    mode = None
    for line in block.split("\n"):
        if line.startswith("INPUT:"):
            mode = "in"
            inp += line
            continue
        if line.startswith("OUTPUT:"):
            mode = "out"
            out += line
            continue
        if line.startswith("PRE:") or re.match(r"^\d", line.strip()):
            mode = "body"
        if mode == "in" and line.startswith(" " * 8):
            inp += " " + line.strip()
            continue
        if mode == "out" and line.startswith(" " * 8):
            out += " " + line.strip()
            continue
        body_lines.append(line)
    return inp, out, "\n".join(body_lines)


def build_graph(text: str) -> dict:
    entities = find_entities(text)
    algos = find_algorithms(text)
    edges: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for a in algos:
        inp, out, body = io_lines(a["block"])
        # a name inside a bracketed index is a dimension, not the entity:
        # A4 outputs existing_capacity[technology], which is not a write to the
        # technology table. Strip index expressions before matching.
        inp = re.sub(r"\[[^\]]*\]", "", inp)
        out = re.sub(r"\[[^\]]*\]", "", out)
        # prose around the block counts as a read: A4 cross-checks against
        # premise_operating_profile in its notes rather than in its pseudocode
        body = body + "\n" + a.get("prose", "")
        for e in entities:
            # word-boundary match so premise_energy does not match inside another name
            alts = "|".join([re.escape(e)] + ALIASES.get(e, []))
            word = re.compile(rf"\b(?:{alts})\b")
            in_input = bool(word.search(inp))
            in_output = bool(word.search(out))
            in_body = bool(word.search(body))
            if in_output:
                key = (a["id"], e, "writes")
                if key not in seen:
                    seen.add(key)
                    edges.append({"from": a["id"], "to": e, "kind": "writes"})
            if in_input or (in_body and not in_output):
                key = (e, a["id"], "reads")
                if key not in seen:
                    seen.add(key)
                    edges.append({"from": e, "to": a["id"], "kind": "reads"})

    # the pipeline order itself, A1 -> A2 -> ... -> A9
    for i in range(len(algos) - 1):
        edges.append({"from": algos[i]["id"], "to": algos[i + 1]["id"], "kind": "flow"})

    used = {e["from"] for e in edges} | {e["to"] for e in edges}
    nodes = [
        {
            "id": e,
            "label": e,
            "type": "entity",
            "role": (
                "input"
                if e in INPUT_ENTITIES
                else "scenario"
                if e in SCENARIO_ENTITIES
                else "output"
                if e in OUTPUT_ENTITIES
                else "reference"
            ),
        }
        for e in entities
        if e in used
    ] + [
        {"id": a["id"], "label": f"{a['id']} {a['title']}", "type": "algorithm", "role": "algorithm"}
        for a in algos
    ]
    return {"nodes": nodes, "edges": edges}


# --------------------------------------------------------------------------- #
# Mermaid
# --------------------------------------------------------------------------- #

MERMAID_CLASSES = """
    classDef input fill:#dbeafe,stroke:#1e40af,stroke-width:2px,color:#0f172a;
    classDef reference fill:#ede9fe,stroke:#5b21b6,stroke-width:2px,color:#0f172a;
    classDef scenario fill:#fef3c7,stroke:#92400e,stroke-width:2px,color:#0f172a;
    classDef output fill:#dcfce7,stroke:#166534,stroke-width:2px,color:#0f172a;
    classDef algorithm fill:#f1f5f9,stroke:#334155,stroke-width:2px,color:#0f172a;
"""


LANES = {
    "input": ("Stock", "CaRB3 stock model"),
    "reference": ("Ref", "Reference data"),
    "scenario": ("Scen", "Scenario data"),
    "output": ("Out", "Results"),
}


def to_sequence(g: dict) -> str:
    """The journey: each algorithm in turn, with what it reads and writes.

    Data stores are collapsed into four lanes by ownership rather than drawn as
    fifteen participants, which would be unreadable. The entity name travels on
    the arrow instead, so nothing is lost.
    """
    role = {n["id"]: n["role"] for n in g["nodes"]}
    label = {n["id"]: n["label"] for n in g["nodes"]}
    algos = [n["id"] for n in g["nodes"] if n["type"] == "algorithm"]

    out = ["sequenceDiagram", "    autonumber"]
    for _, (short, name) in LANES.items():
        out.append(f"    participant {short} as {name}")
    for a in algos:
        out.append(f'    participant {a} as {label[a].replace(":", "")}')

    for i, a in enumerate(algos):
        reads = [e["from"] for e in g["edges"] if e["to"] == a and e["kind"] == "reads"]
        writes = [e["to"] for e in g["edges"] if e["from"] == a and e["kind"] == "writes"]
        out.append(f"    activate {a}")
        for r in reads:
            lane = LANES.get(role.get(r, "reference"), LANES["reference"])[0]
            out.append(f"    {lane}->>{a}: {r}")
        for w in writes:
            out.append(f"    {a}-->>Out: {w}")
        if i + 1 < len(algos):
            out.append(f"    {a}->>{algos[i + 1]}: hand off")
        out.append(f"    deactivate {a}")
    return "\n".join(out) + "\n"


def to_classes(fields: dict[str, list[dict]]) -> str:
    """Entities, their fields, and the foreign keys between them."""
    out = ["classDiagram"]
    for entity, rows in fields.items():
        out.append(f"    class {entity} {{")
        for r in rows:
            mark = " PK" if r["pk"] else (" FK" if r["fk"] else "")
            req = "+" if r["required"] else "-"
            out.append(f'        {req}{r["type"]} {r["name"]}{mark}')
        out.append("    }")
    seen = set()
    for entity, rows in fields.items():
        for r in rows:
            target = r["fk"]
            if not target or target not in fields or target == entity:
                continue
            key = (entity, target, r["name"])
            if key in seen:
                continue
            seen.add(key)
            out.append(f'    {entity} "*" --> "1" {target} : {r["name"]}')
    return "\n".join(out) + "\n"


HEADER = (
    "Generated from [the implementation specification]"
    "(../2026-08-19-carb3-site-decarbonisation-implementation.md) by "
    "`docs/notes/examples/build_spec_flow_diagram.py`. Do not edit by hand — regenerate.\n"
)


def wrap(title: str, intro: str, body: str) -> str:
    """A mermaid graph in a fenced block, inside a Markdown document.

    A bare .mmd file opens as plain text: the VS Code Mermaid extensions hook
    Markdown *preview*, not a standalone mermaid file. The fence makes it
    previewable there and on GitHub.
    """
    return f"# {title}\n\n{HEADER}\n{intro}\n\n```mermaid\n{body}```\n"


def to_mermaid(g: dict) -> str:
    lines = ["flowchart LR"]
    for n in g["nodes"]:
        if n["type"] == "entity":
            lines.append(f'    {n["id"]}[({n["label"]})]')
        else:
            label = n["label"].replace('"', "'")
            lines.append(f'    {n["id"]}["{label}"]')
    for e in g["edges"]:
        arrow = "-->" if e["kind"] != "flow" else "==>"
        lines.append(f'    {e["from"]} {arrow} {e["to"]}')
    lines.append(MERMAID_CLASSES.rstrip())
    for role in ("input", "reference", "scenario", "output", "algorithm"):
        members = [n["id"] for n in g["nodes"] if n["role"] == role]
        if members:
            lines.append(f'    class {",".join(members)} {role};')
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #

COLOURS = {
    "input": ("#dbeafe", "#1e40af"),
    "reference": ("#ede9fe", "#5b21b6"),
    "scenario": ("#fef3c7", "#92400e"),
    "output": ("#dcfce7", "#166534"),
    "algorithm": ("#f1f5f9", "#334155"),
}
BOX_W, BOX_H = 240, 64
COL_GAP, ROW_GAP = 150, 26


def layout(g: dict) -> dict[str, dict]:
    """Algorithms down the centre; entities in columns either side by role."""
    algos = [n for n in g["nodes"] if n["type"] == "algorithm"]
    cols = {
        "input": [n for n in g["nodes"] if n["role"] == "input"],
        "reference": [n for n in g["nodes"] if n["role"] == "reference"],
        "scenario": [n for n in g["nodes"] if n["role"] == "scenario"],
        "output": [n for n in g["nodes"] if n["role"] == "output"],
    }
    pos: dict[str, dict] = {}
    order = [("input", 0), ("reference", 1), ("algorithm", 2), ("scenario", 3), ("output", 4)]
    for role, col in order:
        members = algos if role == "algorithm" else cols[role]
        x = 40 + col * (BOX_W + COL_GAP)
        total = len(members) * (BOX_H + ROW_GAP)
        y0 = 40 + max(0, (12 * (BOX_H + ROW_GAP) - total) // 2)
        for i, n in enumerate(members):
            pos[n["id"]] = {
                "x": x,
                "y": y0 + i * (BOX_H + ROW_GAP),
                "w": BOX_W,
                "h": BOX_H,
                "role": n["role"],
                "label": n["label"],
            }
    return pos


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_svg(g: dict, pos: dict[str, dict]) -> str:
    width = max(p["x"] + p["w"] for p in pos.values()) + 40
    height = max(p["y"] + p["h"] for p in pos.values()) + 40
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica,Arial,sans-serif">',
        '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs>',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    for e in g["edges"]:
        a, b = pos.get(e["from"]), pos.get(e["to"])
        if not a or not b:
            continue
        x1, y1 = a["x"] + a["w"], a["y"] + a["h"] / 2
        x2, y2 = b["x"], b["y"] + b["h"] / 2
        if x2 < x1:  # right-to-left edge: leave from the left face
            x1, x2 = a["x"], b["x"] + b["w"]
        dash = ' stroke-dasharray="5,4"' if e["kind"] == "reads" else ""
        wid = 2.5 if e["kind"] == "flow" else 1.4
        mx = (x1 + x2) / 2
        out.append(
            f'<path d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}" fill="none" '
            f'stroke="#64748b" stroke-width="{wid}"{dash} marker-end="url(#a)" opacity="0.75"/>'
        )
    for nid, p in pos.items():
        fill, stroke = COLOURS[p["role"]]
        rx = 30 if p["role"] != "algorithm" else 8
        out.append(
            f'<rect x="{p["x"]}" y="{p["y"]}" width="{p["w"]}" height="{p["h"]}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        label = p["label"]
        parts = [label] if len(label) <= 30 else [label[:30], label[30:60]]
        for i, part in enumerate(parts):
            ty = p["y"] + p["h"] / 2 + 5 + (i - (len(parts) - 1) / 2) * 15
            out.append(
                f'<text x="{p["x"] + p["w"] / 2}" y="{ty}" text-anchor="middle" '
                f'font-size="13" fill="#0f172a">{esc(part)}</text>'
            )
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    text = read_spec()
    g = build_graph(text)
    fields = find_entity_fields(text)
    pos = layout(g)
    OUT.mkdir(parents=True, exist_ok=True)
    entities = sum(1 for n in g["nodes"] if n["type"] == "entity")
    algos = sum(1 for n in g["nodes"] if n["type"] == "algorithm")

    (OUT / "spec_journey.md").write_text(
        wrap(
            "The journey of one premise",
            f"What happens to a single premise between arriving from the stock model and "
            f"leaving as a pathway. {algos} steps, in the order §4 specifies them. Data "
            f"stores are grouped into four lanes by who owns them — the entity name travels "
            f"on the arrow, so nothing is lost. Solid arrows into a step are reads; dashed "
            f"arrows out are writes.",
            to_sequence(g),
        ),
        encoding="utf-8",
    )
    (OUT / "spec_data_model.md").write_text(
        wrap(
            "Data model",
            f"The {len(fields)} entities of §3 with their fields and foreign keys. "
            f"`+` marks a required field, `-` an optional one; `PK` marks a primary-key "
            f"part and `FK` a foreign key. Arrows read many-to-one.",
            to_classes(fields),
        ),
        encoding="utf-8",
    )
    (OUT / "spec_flow.svg").write_text(to_svg(g, pos), encoding="utf-8")
    print(f"{entities} entities, {algos} algorithms, {len(g['edges'])} edges")
    for f in sorted(OUT.iterdir()):
        print(f"  {f.relative_to(REPO)}  {f.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
