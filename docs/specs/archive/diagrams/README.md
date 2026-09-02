# Spec flow diagrams

Generated from the [implementation specification](../2026-08-19-carb3-site-decarbonisation-implementation.md),
not drawn by hand. Regenerate after any change to the data model or the algorithms:

```bash
python3 docs/notes/examples/build_spec_flow_diagram.py            # rebuild
python3 docs/notes/examples/build_spec_flow_diagram.py --check    # is it stale?
make docs-check                                                   # both generators
```

`--check` exits non-zero if any file here differs from what the spec would produce
now, so a hook or CI step can refuse a spec change that left the pictures behind. A
stale diagram still renders perfectly, which is exactly why it needs checking.

Which spec is read, where the output goes, and which entities count as premise,
scenario or output data all come from
[`spec_docs.config.json`](../../notes/examples/spec_docs.config.json). Add a spec
there, not in the Python. `--spec KEY` selects one; `--all` builds every one that is
switched on.

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

Three views, each answering a different question. The two Markdown files preview in
VS Code with the **Markdown Preview Mermaid Support** extension (⇧⌘V) and render inline
on GitHub.

| File | Question it answers |
|---|---|
| `spec_journey.md` | *What happens to one premise, in order?* A sequence diagram: the nine steps of §4, with what each reads and writes |
| `spec_data_model.md` | *How is the data shaped?* A class diagram: entities, fields, and the foreign keys between them |
| `spec_flow.svg` | *What is the whole thing at a glance?* The overview graph, as a self-contained SVG that drops onto a Mural or Miro canvas |

The journey and the data model are the two questions worth asking of a pipeline, and one
diagram cannot answer both: a sequence diagram loses the shape of the data, and a class
diagram loses the order of operations. The SVG keeps the at-a-glance overview and is the
one to take somewhere else, since it needs no toolchain at the far end. Mural accepts `svg` among its supported
image formats, so it imports through the toolbar or by dropping the file on the canvas —
as a flat image rather than editable shapes.

**Why Markdown rather than a bare `.mmd`.** The VS Code Mermaid extensions hook Markdown
*preview*; a standalone `.mmd` file just opens as text. Wrapping the same graph in a
fenced block makes it previewable there and on GitHub without keeping a second format in
step.

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
