# Site-Level Pathways Note Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone, plain-language explanation of how sites share a base-year sector configuration but can follow different modelled pathways over time.

**Architecture:** Create one focused discussion note and link it from the existing notes index. The note will cite and cross-link existing notes instead of duplicating their detailed coverage of measured site energy.

**Tech Stack:** Markdown documentation; source-checked against the COMIT R model.

---

### Task 1: Write the standalone explanation

**Files:**
- Create: `docs/notes/10_site_level_pathways.md`
- Reference: `docs/notes/06_inputting_measured_site_energy.md`
- Reference: `R/fct_decision_variables.R`, `R/fct_sites.R`, `R/fct_constraints_capacity_transfer.R`, `R/fct_constraints_hydrogen.R`, `R/fct_constraints_CO2.R`, `R/fct_constraints_headroom.R`, `R/fct_constraints_known_changes.R`

- [x] **Step 1: Draft the reader-facing note**

Explain the base-year shared technology/process set and that both initial
capacity and demand are scaled by each site's share of sector emissions. Explain
the separately modelled site × technology × year decisions and the distinction
between eligibility and costs.
Include an explicit inventory of geographic eligibility, hydrogen/CO2 infrastructure,
grid headroom, and `known_changes`, stating what each can and cannot vary.
Link to note 06 for the detailed explanation of the base-year scaling assumption.

- [x] **Step 2: Add an illustrative two-site example**

Use a table with a base year and two later model periods. Label every value and
pathway as illustrative. Show two sites that begin with the same proportional
configuration and later diverge, explicitly distinguishing a technology option
being ineligible from an eligible option having lower-cost access.

- [x] **Step 3: State limits and interpretation**

Include a "What this does not mean" section: separate variables do not
automatically make sites different; arbitrary site-specific base-year
technology/process mixes are not a workbook feature; and an optimised pathway
is not a forecast.

### Task 2: Make the note discoverable

**Files:**
- Modify: `docs/notes/README.md`

- [x] **Step 1: Add the note to the discussion-notes index**

Use the existing table style and a concise description.

### Task 3: Verify the documentation change

**Files:**
- Verify: `docs/notes/10_site_level_pathways.md`
- Verify: `docs/notes/README.md`

- [x] **Step 1: Check Markdown and local links**

Run a small read-only check that verifies the new note exists, the index link
resolves, and the required link to note 06 resolves.

- [x] **Step 2: Review the diff**

Run `git diff --check` and inspect the documentation diff for accuracy, clarity and scope.

- [x] **Step 3: Commit**

```bash
git add docs/notes/10_site_level_pathways.md docs/notes/README.md docs/superpowers/plans/2026-08-04-site-level-pathways-note.md
git commit -m "docs: explain site-level pathways"
```
