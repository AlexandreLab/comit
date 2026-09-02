#!/usr/bin/env python3
"""Shared configuration loading for the two spec generators.

Both `build_interface_docs.py` and `build_spec_flow_diagram.py` used to carry one
specification's structure as Python literals — heading strings, section numbers,
entity role sets, and the label ranges `A1-A9 / C1-C9 / V1-V17 / D1-D11`. Adding a
second specification therefore meant editing Python to publish a Markdown change.
This module moves all of it into `spec_docs.config.json` and adds the one thing a
config file cannot give on its own: a cross-check against the spec itself.

Label ranges are the part that rots. A range written down in two places will
disagree with itself eventually, and the failure is silent — a published document
that says `C1`-`C9` when the spec defines `C12` still renders perfectly. So the
ranges are *read from each spec's own Notation table* and the config only chooses
which families to mention and how to gloss them. If the config names a family the
spec has stopped declaring, or vice versa, `label_families` raises.

No third-party packages. Standard library only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CONFIG = Path(__file__).resolve().parent / "spec_docs.config.json"


class ConfigError(ValueError):
    """Raised for a config/spec disagreement, loudly and with both sides shown."""


def load(spec_key: str | None = None) -> dict:
    """Return one spec's configuration, with paths resolved and the text read."""
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    key = spec_key or raw["default"]
    if key not in raw["specs"]:
        known = ", ".join(sorted(raw["specs"]))
        raise ConfigError(f"unknown spec {key!r}; config defines: {known}")

    cfg = dict(raw["specs"][key])
    cfg["key"] = key
    cfg["spec_path"] = REPO / cfg["spec_path"]
    if not cfg["spec_path"].exists():
        raise ConfigError(f"spec {key!r} points at a missing file: {cfg['spec_path']}")
    cfg["text"] = cfg["spec_path"].read_text(encoding="utf-8")
    for part in ("interfaces", "diagrams"):
        if part in cfg:
            cfg[part] = dict(cfg[part])
            cfg[part]["out_dir"] = REPO / cfg[part]["out_dir"]
    return cfg


def spec_keys() -> list[str]:
    return sorted(json.loads(CONFIG.read_text(encoding="utf-8"))["specs"])


def enabled_keys(part: str) -> list[str]:
    """Spec keys whose `part` ('interfaces' or 'diagrams') is switched on.

    A spec can be registered before it is publishable — v2's §4 is a stub and its
    §8 does not exist yet — so the config carries an `enabled` flag and a
    `blocked_by` reason rather than being absent, and `make docs-check` covers
    exactly the targets that can actually be generated today.
    """
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    return sorted(k for k, s in raw["specs"].items() if s.get(part, {}).get("enabled"))


# --------------------------------------------------------------------------- #
# Label families, read from the spec rather than declared here
# --------------------------------------------------------------------------- #

# `| `C1`–`C12` | Constraints | §5.5 |` — the en-dash is what both specs use, but
# a plain hyphen is accepted so a typo does not read as a deleted family.
_RANGE_ROW = re.compile(
    r"^\|\s*`(?P<prefix>[A-Z]+)(?P<lo>\d+)`\s*[–—-]\s*`(?P=prefix)(?P<hi>\d+)`\s*\|",
    re.M,
)


def notation_section(cfg: dict) -> str:
    """The body of the spec's own `### N.M <notation_heading>` section."""
    heading = cfg.get("notation_heading", "Notation")
    m = re.search(rf"^(#{{2,4}}) [\d.]+ {re.escape(heading)}\s*$", cfg["text"], re.M)
    if not m:
        raise ConfigError(
            f"spec {cfg['key']!r} has no '### N.M {heading}' heading; either it was "
            f"renamed or `notation_heading` in spec_docs.config.json is wrong"
        )
    level = len(m.group(1))
    nxt = re.search(rf"^#{{2,{level}}} ", cfg["text"][m.end():], re.M)
    end = m.end() + (nxt.start() if nxt else len(cfg["text"]) - m.end())
    return cfg["text"][m.end():end]


def spec_label_ranges(cfg: dict) -> dict[str, tuple[int, int]]:
    """Every `X1`-`Xn` family the spec's Notation table declares."""
    body = notation_section(cfg)
    found = {m.group("prefix"): (int(m.group("lo")), int(m.group("hi")))
             for m in _RANGE_ROW.finditer(body)}
    if not found:
        raise ConfigError(
            f"spec {cfg['key']!r}'s notation section declares no label families; "
            f"the table format changed and the generators can no longer read it"
        )
    return found


def label_families(cfg: dict, note: dict) -> list[dict]:
    """Config's chosen families, with ranges filled in from the spec.

    The config says *which* families a published extract should mention and how to
    gloss each one; the spec says what each range actually is. Disagreement is an
    error, not a silently-preferred side.
    """
    declared = spec_label_ranges(cfg)
    out = []
    for fam in note["families"]:
        prefix = fam["prefix"]
        if prefix not in declared:
            known = ", ".join(sorted(declared))
            raise ConfigError(
                f"spec {cfg['key']!r} no longer declares a {prefix!r} label family in "
                f"its notation table (it declares: {known}), but "
                f"spec_docs.config.json still asks the generated docs to cite it"
            )
        lo, hi = declared[prefix]
        out.append({"prefix": prefix, "gloss": fam["gloss"], "lo": lo, "hi": hi,
                    "range": f"`{prefix}{lo}`–`{prefix}{hi}`"})
    return out
