#!/usr/bin/env python3
"""Generate a data-flow diagram of the CaRB3 per-site decarbonisation design.

Reads the implementation specification and derives the diagram from it, rather
than from a hand-maintained copy that would drift the moment the spec changed.

Sources in the spec:
  entities    - the `### 3.x` and `#### 3.1.x` headings of the data model
  algorithms  - the `### A1 - ...` headings of section 4
  edges       - the INPUT:/OUTPUT: lines of each algorithm's pseudocode block,
                plus entity names mentioned in the body (read edges)

Which spec to read, where to write, and which entities count as premise, scenario
or output data all come from `spec_docs.config.json`; nothing about a particular
specification is compiled in here.

Emits, into the configured output directory:
  spec_journey.md     Mermaid sequence diagram: the journey from ingesting a premise
                      to writing its pathway, step by step
  spec_data_model.md  Mermaid class diagram: entities, their fields and foreign keys
  spec_flow.svg       dependency-free SVG overview; drop into Mural or any SVG tool

The two Markdown files preview in VS Code with a Mermaid extension and render
inline on GitHub.

No third-party packages. Standard library only.

Usage:  python3 docs/notes/examples/build_spec_flow_diagram.py
        python3 docs/notes/examples/build_spec_flow_diagram.py --check
        python3 docs/notes/examples/build_spec_flow_diagram.py --spec v2
        python3 docs/notes/examples/build_spec_flow_diagram.py --list

--check regenerates in memory and exits non-zero if any file on disk differs, so a
hook or CI step can refuse a spec change that left the diagrams behind. The
interface builder has had that since it was written; this one had no way to tell
you the picture was out of date, which is worse — a stale diagram still renders.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_docs_config as conf  # noqa: E402  (needs the path above)

REPO = conf.REPO


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


def build_graph(text: str, aliases: dict[str, list[str]], roles: dict[str, list[str]]) -> dict:
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
            alts = "|".join([re.escape(e)] + aliases.get(e, []))
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

    # Entities that are reference/scenario data rather than premise data get a
    # different colour, so the diagram distinguishes what the stock model supplies
    # from what the modelling team maintains. Anything unlisted is reference data.
    role_of = {name: role for role, names in roles.items() for name in names}

    used = {e["from"] for e in edges} | {e["to"] for e in edges}
    nodes = [
        {
            "id": e,
            "label": e,
            "type": "entity",
            "role": role_of.get(e, "reference"),
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


def header_line(spec_link: str) -> str:
    return (
        "Generated from [the implementation specification]"
        f"({spec_link}) by "
        "`docs/notes/examples/build_spec_flow_diagram.py`. Do not edit by hand — regenerate.\n"
    )


def wrap(title: str, intro: str, body: str, header: str) -> str:
    """A mermaid graph in a fenced block, inside a Markdown document.

    A bare .mmd file opens as plain text: the VS Code Mermaid extensions hook
    Markdown *preview*, not a standalone mermaid file. The fence makes it
    previewable there and on GitHub.
    """
    return f"# {title}\n\n{header}\n{intro}\n\n```mermaid\n{body}```\n"


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


def render(cfg: dict, diag: dict) -> dict[str, str]:
    """Every output file this spec produces, as name -> content, written nowhere yet.

    Rendering fully in memory is what makes --check possible: the same code path
    produces the bytes that are compared and the bytes that are written, so the
    check cannot pass against a build the writer would not have produced.
    """
    text = cfg["text"]
    out_dir = diag["out_dir"]
    depth = len(out_dir.relative_to(cfg["spec_path"].parent).parts)
    header = header_line("../" * depth + cfg["spec_path"].name)

    g = build_graph(text, diag.get("aliases", {}), diag.get("roles", {}))
    fields = find_entity_fields(text)
    algos = sum(1 for n in g["nodes"] if n["type"] == "algorithm")
    if not algos:
        raise conf.ConfigError(
            f"spec {cfg['key']!r} declares no algorithms — §4 has no '### A1 — ' "
            f"headings, so the journey diagram and the SVG flow would come out empty"
        )

    return {
        "spec_journey.md": wrap(
            "The journey of one premise",
            f"What happens to a single premise between arriving from the stock model and "
            f"leaving as a pathway. {algos} steps, in the order §4 specifies them. Data "
            f"stores are grouped into four lanes by who owns them — the entity name travels "
            f"on the arrow, so nothing is lost. Solid arrows into a step are reads; dashed "
            f"arrows out are writes.",
            to_sequence(g),
            header,
        ),
        "spec_data_model.md": wrap(
            "Data model",
            f"The {len(fields)} entities of §3 with their fields and foreign keys. "
            f"`+` marks a required field, `-` an optional one; `PK` marks a primary-key "
            f"part and `FK` a foreign key. Arrows read many-to-one.",
            to_classes(fields),
            header,
        ),
        "spec_flow.svg": to_svg(g, layout(g)),
        "_summary": (
            f"{sum(1 for n in g['nodes'] if n['type'] == 'entity')} entities, "
            f"{algos} algorithms, {len(g['edges'])} edges"
        ),
    }


def run(spec_key: str | None, check: bool) -> int:
    cfg = conf.load(spec_key)
    diag = cfg.get("diagrams")
    if not diag or not diag.get("enabled"):
        why = (diag or {}).get("blocked_by", "no `diagrams` block in the config")
        print(f"spec {cfg['key']!r}: diagrams not generated — {why}")
        return 0

    files = render(cfg, diag)
    summary = files.pop("_summary")
    out_dir = diag["out_dir"]

    if check:
        stale = []
        for name, body in files.items():
            path = out_dir / name
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != body:
                stale.append(name)
        if stale:
            print(f"STALE ({cfg['key']}), spec has moved on: " + ", ".join(sorted(stale)))
            print(f"Run: python3 docs/notes/examples/build_spec_flow_diagram.py "
                  f"--spec {cfg['key']}")
            return 1
        print(f"diagrams ({cfg['key']}) are in step with the spec — {summary}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        (out_dir / name).write_text(body, encoding="utf-8")
    print(summary)
    for name in sorted(files):
        f = out_dir / name
        print(f"  {f.relative_to(REPO)}  {f.stat().st_size:,} bytes")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--spec", help="config key to build (default: the config's `default`)")
    p.add_argument("--all", action="store_true",
                   help="every spec whose diagrams are enabled")
    p.add_argument("--check", action="store_true",
                   help="verify the generated diagrams match; exit 1 if not")
    p.add_argument("--list", action="store_true", help="list the configured specs")
    args = p.parse_args()

    if args.list:
        for key in conf.spec_keys():
            cfg = conf.load(key)
            state = "on " if cfg.get("diagrams", {}).get("enabled") else "off"
            print(f"  {key:4s} [{state}] {cfg['title']}")
        return 0

    keys = conf.enabled_keys("diagrams") if args.all else [args.spec]
    try:
        return max((run(k, args.check) for k in keys), default=0)
    except conf.ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
