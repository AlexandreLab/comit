# Diagrams

Generated from
[the implementation specification](../2026-08-28-carb3-site-energy-system-implementation.md)
by `docs/notes/examples/build_spec_flow_diagram.py`. **Do not edit by hand** —
edit §3 of the spec and run `make docs-build`. `make docs-check` fails if the
published copies fall behind.

| File | Answers |
|---|---|
| [`spec_entities.md`](spec_entities.md) | *What tables are there, and how do they link?* Four views of §3: an ER diagram of the relationships, the same graph boxed by subject, a locator table naming every non-key column, and the full attribute model |

## Why four views and not one

An `erDiagram` carries cardinality — one premise, many connections — and whether a
foreign key is identifying. It has no grouping construct, so it cannot show that
`activity_process_register`, `premise_process_detail`, `premise_process_vintage` and
`process_load_shape` are all about processes. A `flowchart` with subgraphs shows exactly
that and loses the cardinality. Neither answers *which table holds the floor area*, which
is a column question, so that one is a table.

## Where the subjects come from

The eight subjects are not in the spec: §3 groups its entities by **who supplies them**
(stock model, modelling team, scenario, derived, optional intelligence, defaults), which
is the right cut for a data contract and the wrong one for finding where something lives.
The subject grouping is therefore config, under `diagrams.domains` in
`docs/notes/examples/spec_docs.config.json`.

It is checked to be a **partition**: an entity added to §3 and left out of every domain
fails the build rather than quietly vanishing from the grouped view. Adding a subject, or
moving an entity between subjects, is a JSON edit.

## What is not generated here

The journey sequence diagram and the SVG overview, which the baseline publishes in
[`../archive/diagrams/`](../archive/diagrams/README.md). Both read §4's algorithm
headings, and §4 here numbers them `### 4.1 A4 — …` rather than `### A1 — …`. They are
switched off individually under `diagrams.outputs`, each with its reason recorded in
`blocked_outputs`.
