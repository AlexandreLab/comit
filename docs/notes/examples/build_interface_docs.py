#!/usr/bin/env python3
"""Publish the interface sections of an implementation spec as standalone documents.

Section 3 (the data model) is the contract with whoever supplies premise records;
section 8 (the output schema) is the contract with whoever consumes results. Both
are read by people who have no reason to hold the whole specification, so both are
published on their own — but *generated*, never copied by hand, because a field
table maintained in two places is a field table that will disagree with itself.

Which spec, which sections, and which label families to cite all come from
`spec_docs.config.json`; nothing about a particular specification is compiled in
here. Label *ranges* are read from the target spec's own Notation table and
cross-checked against that config, so a new `C10` cannot slip past into a
published document still claiming `C1`-`C9`.

Emits, into the configured output directory:
  input-data-model.md    implementation section 3
  output-data-schema.md  implementation section 8

Usage:  python3 docs/notes/examples/build_interface_docs.py
        python3 docs/notes/examples/build_interface_docs.py --check
        python3 docs/notes/examples/build_interface_docs.py --spec site-energy-system
        python3 docs/notes/examples/build_interface_docs.py --list

--check regenerates in memory and exits non-zero if any file on disk differs,
so a hook or CI step can refuse a spec change that left the published copies behind.

No third-party packages. Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_docs_config as conf  # noqa: E402  (needs the path above)

# The generated header was hand-written at this width. It is not the spec's own
# wrap (~88): the header is a narrower block, and the label sentence is generated
# into the middle of it, so it has to match its neighbours or the paragraph looks
# ragged. The byte-identity check on the published documents is what holds this honest.
WRAP = 84


def slice_section(text: str, start: str, end: str) -> str:
    try:
        i = text.index(start)
        j = text.index(end, i)
    except ValueError as exc:
        raise conf.ConfigError(
            f"could not slice {start!r}..{end!r}; the spec's headings moved and "
            f"spec_docs.config.json still names the old ones"
        ) from exc
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


def relink(body: str, own: str, anchors: dict[str, str], spec_link: str) -> str:
    """Point outward references at the spec; leave references inside this doc alone.

    A standalone extract is full of citations to sections that did not come with
    it. Left bare they are dead ends, so each becomes a link back to the source.
    """
    def repl(m: re.Match) -> str:
        num = m.group(1)
        if num == own or num.startswith(own + "."):
            return m.group(0)          # resolves within this document
        anchor = anchors.get(num, "")
        target = f"{spec_link}#{anchor}" if anchor else spec_link
        return f"[§{num}]({target})"

    # skip refs already inside a markdown link, and fenced code
    parts = re.split(r"(```.*?```)", body, flags=re.S)
    for i, part in enumerate(parts):
        if part.startswith("```"):
            continue
        parts[i] = re.sub(r"(?<!\[)§(\d+(?:\.\d+)*)(?!\d*\])", repl, part)
    return "".join(parts)


def fix_relative_paths(body: str, out_name: str, depth: int) -> str:
    """Rewrite the spec's own relative links for a copy `depth` directories deeper.

    Every relative target the spec wrote needs one more `../` per level — except a
    link into the output directory itself, which is now a link to a sibling. Left
    alone that one points at a directory of the same name nested inside the output
    directory, which does not exist: `interfaces/input-data-model.md` read from
    `docs/specs/interfaces/` resolves to `docs/specs/interfaces/interfaces/…`.

    This runs on the extracted section only, before `relink`, because the links
    `relink` emits are built at the right depth already.
    """
    up = "../" * depth

    def repl(m: re.Match) -> str:
        target = m.group(1)
        if target.startswith(("#", "/")) or re.match(r"^[a-z][a-z0-9+.-]*:", target):
            return m.group(0)                       # anchor, absolute, or a scheme
        if target.startswith(out_name + "/"):
            return "](" + target[len(out_name) + 1:] + ")"
        return "](" + up + target + ")"

    return re.sub(r"\]\(([^)\s]+)\)", repl, body)


def label_sentence(cfg: dict, note: dict) -> str:
    """The 'Reading the references' paragraph, with ranges taken from the spec."""
    fams = conf.label_families(cfg, note)
    parts = [f"{f['range']} ({f['gloss']})" for f in fams]
    listed = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    para = (
        "**Reading the references.** `§`-numbers inside this document resolve "
        "within it; every other `§` links back to the specification. Labels of the "
        f"form {listed} all refer to the specification — see its §{note['see']}."
    )
    return "\n".join(
        textwrap.wrap(para, width=WRAP, break_long_words=False, break_on_hyphens=False)
    )


def build(doc: dict, cfg: dict, iface: dict, anchors: dict[str, str],
          spec_link: str, depth: int) -> str:
    body = slice_section(cfg["text"], doc["start"], doc["end"]).rstrip()
    date = section_date(body)

    # the section heading becomes the document title
    body = body.split("\n", 1)[1].lstrip("\n")
    body = re.sub(r"^\*Section last updated: [\d-]{10}\*\n+", "", body)
    body = fix_relative_paths(body, iface["out_dir"].name, depth)

    header = f"""# {doc["title"]}

> **Generated file — do not edit.**
> Published from [implementation specification §{doc["section"]}]({spec_link}), which is
> the single source of truth and was last revised {date}. To change anything here,
> edit that section and re-run
> `python3 docs/notes/examples/build_interface_docs.py`.

{doc["blurb"]}

{doc["audience"]}

**Companion:** [{doc["sibling_file"]}]({doc["sibling_file"]}) — {doc["sibling_desc"]}.

{label_sentence(cfg, iface["label_note"])}

---

"""
    return relink(header + body, doc["section"], anchors, spec_link) + "\n"


def run(spec_key: str, check: bool) -> int:
    cfg = conf.load(spec_key)
    iface = cfg.get("interfaces")
    if not iface or not iface.get("enabled"):
        why = (iface or {}).get("blocked_by", "no `interfaces` block in the config")
        print(f"spec {cfg['key']!r}: interface docs not published — {why}")
        return 0

    out_dir = iface["out_dir"]
    depth = len(out_dir.relative_to(cfg["spec_path"].parent).parts)
    spec_link = "../" * depth + cfg["spec_path"].name

    anchors = anchor_map(cfg["text"])
    if not check:
        out_dir.mkdir(parents=True, exist_ok=True)

    stale = []
    for doc in iface["documents"]:
        rendered = build(doc, cfg, iface, anchors, spec_link, depth)
        path = out_dir / doc["file"]
        if check:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != rendered:
                stale.append(doc["file"])
        else:
            path.write_text(rendered, encoding="utf-8")
            print(f"  {path.relative_to(conf.REPO)}  {len(rendered):,} bytes")

    if check:
        if stale:
            print(f"STALE ({cfg['key']}), spec has moved on: " + ", ".join(stale))
            print(f"Run: python3 docs/notes/examples/build_interface_docs.py "
                  f"--spec {cfg['key']}")
            return 1
        print(f"interface docs ({cfg['key']}) are in step with the spec")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--spec", help="config key to build (default: the config's `default`)")
    p.add_argument("--all", action="store_true",
                   help="every spec whose interface docs are enabled")
    p.add_argument("--check", action="store_true",
                   help="verify the published copies match; exit 1 if not")
    p.add_argument("--list", action="store_true", help="list the configured specs")
    args = p.parse_args()

    if args.list:
        for key in conf.spec_keys():
            cfg = conf.load(key)
            state = "on " if cfg.get("interfaces", {}).get("enabled") else "off"
            print(f"  {key:4s} [{state}] {cfg['title']}")
        return 0

    keys = conf.enabled_keys("interfaces") if args.all else [args.spec]
    try:
        return max((run(k, args.check) for k in keys), default=0)
    except conf.ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
