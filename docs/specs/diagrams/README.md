# Spec flow diagrams

Generated from the [implementation specification](../2026-08-19-carb3-site-decarbonisation-implementation.md),
not drawn by hand. Regenerate after any change to the data model or the algorithms:

```bash
python3 docs/notes/examples/build_spec_flow_diagram.py
```

Standard library only — no graphviz, no mermaid CLI, no npm.

## What it derives, and from where

| Diagram element | Parsed from |
|---|---|
| Entity nodes | the `### 3.x` / `#### 3.1.x` headings of the data model |
| Algorithm nodes | the `### A1 — …` headings of §4 |
| Read edges | entity names in each algorithm's `INPUT:` line, or in its surrounding prose |
| Write edges | entity names in each algorithm's `OUTPUT:` line |
| Pipeline edges | A1 → A2 → … → A9, in document order |

Because the edges come from the spec's own pseudocode, the diagram cannot quietly drift
from it. If an entity stops being referenced by any algorithm, it stops appearing — which
is information, not a defect.

## Files

| File | Use |
|---|---|
| `spec_flow.mmd` | Mermaid source. Renders natively on GitHub and in Claude Artifacts |
| `spec_flow.svg` | Self-contained SVG. Drag straight onto a Mural canvas |
| `spec_flow_graph.json` | Nodes and edges, for any other renderer |
| `mural_widgets.json` | Request bodies for the Mural API — shapes with position, size, text and colour, plus the connector list |

## Getting it into Mural

**Drag-and-drop.** Mural accepts `svg` among its supported image formats, so
`spec_flow.svg` can be dropped onto a canvas or added through the Import button. Fastest
route, but the result is one flat image — not editable shapes.

**Mural API.** `mural_widgets.json` is shaped for
`POST /murals/{muralId}/widgets/shape`, which takes `shape`, `x` and `y` as required
fields, with `width`, `height`, `text` and a style block optional, and accepts up to 1000
shapes per request. Authentication is OAuth2 with the `murals:write` scope. Connectors are
listed separately because arrows must reference the widget ids the shape call returns, so
they can only be created on a second pass.

The API is in beta, so check the current reference before relying on it:
<https://developers.mural.co/public/reference/createshapewidget>

## Colour key

| Colour | Meaning |
|---|---|
| Blue | Supplied by the upstream CaRB3 stock model (§1.6) |
| Purple | Reference data maintained by the modelling team |
| Amber | Scenario input |
| Green | Output |
| Grey | Algorithm |

## Known absences

`premise_weekly_profile` and `process_load_shape` appear in no algorithm, so they are
absent from the diagram. That is correct: both exist for the §5.6 network extension,
which is specified but not implemented. When that extension lands and gains an algorithm,
they will appear on the next regeneration without any change to this script.
