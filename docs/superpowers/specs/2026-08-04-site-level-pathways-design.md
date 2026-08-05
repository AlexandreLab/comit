# Site-Level Pathways Note — Design

## Goal

Add a standalone discussion note that explains, in plain language, how COMIT
represents sites in the same sector at the base year and how their pathways can
diverge over time.

## Audience

Readers with basic energy-system knowledge who need to interpret COMIT results
without reading the R source code.

## Scope

- Explain that a sector's sites start with the same modelled process and
  technology set, with initial capacity and demand scaled by each site's share
  of sector emissions.
- Distinguish this base-year construction from the model's separate site,
  technology and year decision variables.
- Give a worked, illustrative example of two sites in one sector diverging over
  time because one is eligible for or has lower-cost access to hydrogen/CO2
  infrastructure and the other faces different grid or infrastructure limits.
- State which site-specific constraints already exist (including geographic
  eligibility, infrastructure, grid headroom and `known_changes`) and which do
  not (arbitrary site-specific initial process/technology mixes).
- Link the note from the discussion-notes index and cross-link to note 06,
  which covers measured site energy and the homogeneous-sites assumption in
  detail.

## Non-goals

- Change model behaviour or workbook inputs.
- Claim that the illustrative pathway is a forecast or a universal outcome.
- Provide a procedure for implementing per-site overrides; note 06 already
  covers the available approaches and extensions.

## Content Design

The note will use a short-answer opening followed by a simple two-site table
with an initial year and two later model periods. It will label every number and
pathway in the example as illustrative. A final "What this does not mean"
section will prevent common misinterpretations: sites are not automatically
different merely because they have separate variables, and the model cannot
currently assign a different base-year process mix to an individual site.

The new file will be `docs/notes/10_site_level_pathways.md`. The example will
distinguish a technology being **eligible** at a site from it having **lower-cost
access** there: eligibility determines whether the model creates that option,
while access costs can make an eligible option more or less attractive.

## Evidence Base

- `R/fct_decision_variables.R`: generates site × technology × year decision
  variables and applies site-level H2/CCS eligibility filters.
- `R/fct_sites.R` and `R/fct_constraints_capacity_transfer.R`: derive the
  within-sector emissions scaling factor and use it to allocate initial
  capacity.
- `R/fct_constraints_headroom.R`, `R/fct_constraints_hydrogen.R`,
  `R/fct_constraints_CO2.R`, and `R/fct_constraints_known_changes.R`: provide
  spatial, infrastructure and specified site-level constraints.
- `docs/notes/06_inputting_measured_site_energy.md`: existing explanation of
  the homogeneous base-year assumption and its limitations.
