# Activity process register & energy profile — first draft

**Date:** 2026-08-24 · **Status:** Draft v0.1 for review · **Spec:** §3.2 and §3.3 of
`20260819carb3sitedecarbonisationimplementation.md`

First evidence-based draft of the two tables the implementation spec calls for, covering
all **55 CaRB3 Factory-class activities**. Built by web research against published
sector evidence (UK 2015 industrial decarbonisation roadmaps, EU BREF documents, US
DOE/LBNL ENERGY STAR guides, EIA MECS 2022 end-use tables, trade-association energy
benchmarks, Carbon Trust guides, and site-level audits where found). Every populated row
carries a provenance pointer into `references.csv`.

## Files

| File | Spec entity | Rows |
|---|---|---|
| `activity_process_register.csv` | §3.2 `activity_process_register` | 376 |
| `activity_process_energy_profile.csv` | §3.3 `activity_process_energy_profile` | 490 |
| `references.csv` | reference table (keyed `ref_id`) | 79 |
| `activity_profile_coverage_notes.csv` | per-activity evidence notes and known gaps | 55 |

`carb3_factory_processes.json` is untouched; the register CSV is its expanded,
provenance-carrying successor (process lists were widened well beyond the JSON's 2–3
per activity — e.g. Cement Works goes from 2 processes to 7).

## Schema notes (deviations and conventions)

- Column order and names follow the spec field tables. One extra column in the register:
  `equipment_examples` (semicolon-separated), carried over and expanded from the JSON.
- `provenance` is `[REF_ID] free-text pointer` — join `REF_ID` to `references.csv` for
  title, publisher, year and URL. Where a table/page is named, the researcher actually
  saw it; otherwise the note says "document level".
- `evidence_tier` uses the spec's enum. No row claims `metered`; the top tier present is
  `published_sec` (129 rows), then `engineering` (301), `fallback` (58).
- `confidence`: high 6 · medium 384 · low 98. Most `published_sec` rows are marked
  *medium* rather than high because the underlying breakdowns are US or pre-2016 sector
  studies applied to GB sites.
- `share_low`/`share_high` are populated only where a source gave a range or sources
  disagreed; blank otherwise.
- Named non-default process sets exist where routes genuinely differ:
  `Iron and/or Steel Works` (`eaf` = default, reflecting the post-2025 GB fleet;
  `bf_bof` named alternative) and `Distillery` (`default` = malt, `grain_distillery`
  named alternative).

## Validation already applied

- All 55 activities present in both tables; exactly one default set per activity.
- `energy_share` sums to 1.00 (±0.015) for every populated `(activity, set, vector)`.
- Band ordering (`share_low ≤ energy_share ≤ share_high`) holds on every row.
- Every `[REF_ID]` in a provenance string resolves to a row in `references.csv`.
- The six most-cited source URLs were re-fetched and confirmed live on 2026-08-24.

## What to treat with suspicion (read before using)

1. **Engineering-tier rows are estimates**, not measurements. They are built from
   rated-equipment logic or partial data, and the rationale is in the provenance note.
   Per §3.3.2 they should surface as `confidence = medium` in outputs.
2. **The generic activities** (Workshop, Factory, Works, Mill, Industrial NEC, Large
   industrial NEC) lean on EIA MECS 2022 sector-level end-use splits (NAICS 332/333/336)
   and Carbon Trust guides — sector averages standing in for site profiles. Fallback
   rows name the sibling activity they were copied from.
3. **US evidence dominates several profiles** (cement electricity, brewing, quarrying,
   metal casting, auto assembly). UK-specific splits, where they exist (2015 roadmaps,
   UK permit applications), were preferred or used as cross-checks.
4. **Vectors with a single process at share 1.0** (e.g. all cement coal → kiln) encode
   "virtually all fuel" statements from sources; they are the strongest rows, not the
   weakest.
5. **Coverage gaps are deliberate blanks.** Where nothing defensible was found for an
   (activity, vector), no rows exist rather than invented ones — see
   `activity_profile_coverage_notes.csv` for what is missing per activity and why.
6. **Mobile plant diesel is in scope** (decision, A. Canet, 2026-08-24): mobile plant
   and mobile machinery fuel is part of `premise_energy` and is captured in the profile
   as a `mobile_plant`-type process on the oil vector. Quarrying, aggregates, concrete
   and waste activities carried it already; Cement Works (oil re-split 0.8 quarry mobile
   plant / 0.2 kiln start-up, engineering tier) and Brickworks (clay pit mobile plant,
   oil 1.0) were updated to match. Iron & Steel internal mobile plant is in scope but
   its oil split is left absent (not assessed) pending evidence. The same decision
   confirmed `eaf` as the default steel process set.

## Suggested next steps

- Review the per-activity notes and decide which activities justify a deeper pass
  (sub-metered UK case studies, ESOS-derived audits) to lift rows from `engineering`
  to `published_sec`.
- Populate the Iron & Steel oil-vector split for internal mobile plant, now that it is
  in scope.
- Make sure the upstream stock model's `premise_energy` oil rows include mobile plant
  and machinery fuel, per the 2026-08-24 scoping decision — the profile now assumes it.
- Convert accepted rows into the load-time asserted format (sum-to-1 check per §3.3,
  R1 technology-consistency check against the technology table when it exists).
