# Decarbonisation options register — first draft

**Date:** 2026-08-24 · **Status:** Draft v0.1 for review · **Companion to:**
`activity_process_register.csv` / `activity_process_energy_profile.csv` (see
`README_activity_process_tables.md`)

Evidence-based first draft of decarbonisation options for all **55 CaRB3 Factory-class
activities**, mapped to the processes in the activity process register, including
lower-TRL options. Built the same way as the energy-profile tables: parallel web
research (one cross-cutting technology pass, six sector passes) against published
sources, with every populated row carrying a provenance pointer into the shared
`references.csv`.

## Files

| File | What it is | Rows |
|---|---|---|
| `decarbonisation_options_library.csv` | One row per option: 34 cross-cutting + 100 sector-specific, each with a **TRL column**, TRL basis, constraints, UK status | 134 |
| `process_decarbonisation_options.csv` | One row per (activity, process_set, process, option): which options apply to which process, with the option's TRL repeated for convenience | 1,109 |
| `decarbonisation_options_challenges.csv` | The 56 data challenges flagged by the researchers, by scope | 56 |
| `references.csv` | Shared reference table — now 270 entries (energy profile + options) | 270 |

## How to read the tables

- `trl` is **only populated where a published assessment states it** (IEA, Agora/
  Fraunhofer ISI 2024, TNO factsheets, de Boer/IEA HPT Annex 58, DESNZ Industrial Fuel
  Switching project reports, Green Steel for Europe, peer-reviewed reviews). Blank TRL
  = no published rating found — 51 of 134 options, deliberately left blank rather than
  guessed. `trl_basis` quotes what the source says.
- Ranges (e.g. `5-8`) are quoted as published, including where two sources disagree.
  Note the **IEA CCUS scale runs 1-11** (10 = commercial & competitive), so amine
  capture's `9-11` is not comparable 1:1 with a 1-9 scale rating.
- `applicability` in the mapping table rates readiness **for that specific duty**, not
  the technology in general: `commercial` / `demonstration` / `prospective` /
  `speculative`. An option can be TRL 9 as hardware but `prospective` for a given
  process (e.g. plasma torches in kiln service).
- `scope` in the library separates `cross_cutting` options (usable in many sectors)
  from `sector_specific` ones (e.g. `h2_dri_eaf`, `calcined_clay_lc3`,
  `inert_anodes` classes of option).
- Mapping rows with a `provenance` citation name a source that discusses that option
  for that sector/duty; rows marked "engineering judgement" (confidence `low`) are the
  researchers' inference from temperature/duty fit.
- 364 of 376 register processes carry at least one option. The 12 without are small
  electricity-only handling/packing/pumping steps where nothing beyond generic controls
  was defensible — left empty on purpose.

## Key challenges (full list in `decarbonisation_options_challenges.csv`)

1. **Numeric TRLs are scarcer than the concept suggests.** Most flagship UK studies
   (Element Energy/Jacobs 2018, Hy4Heat, ERM NRMM 2023 main text) use qualitative
   maturity classes or "first year available" dates, not TRL numbers. The numeric TRLs
   here come disproportionately from a handful of sources (IEA, Agora 2024, TNO, Annex
   58, DESNZ IFS project reports), and sector technologies mostly have none — hence the
   many blanks.
2. **TRL scale mismatch.** IEA's 1-11 scale vs the standard 1-9; quoted as published,
   not converted.
3. **TRLs are often application-specific.** H2 firing is TRL 9 for waste-heat boilers
   but ~5 for tissue drying hoods; microwave heating spans TRL 3-9 by application. The
   mapping table's `applicability` column, not the library TRL, is the per-duty signal.
4. **Grid connection capacity is the recurring binding constraint** for the
   highest-impact electrification options (electrode boilers, EAF/induction, static
   electric quarry plant, MVR) — site-specific and invisible to TRL. Ties directly to
   the spec's §5.6 network fields.
5. **Cluster dependence:** hydrogen and CCS mappings implicitly assume H2 pipeline /
   CO2 T&S access (HyNet, East Coast). For dispersed sites — most of the 55 activities —
   `demonstration` applicability overstates near-term availability; the model's
   per-cluster availability flags (§3.7) are the right gate.
6. **Real-world flux:** UK BF-BOF closures make the `bf_bof` mappings largely
   historical; distillery H2 supply projects have slipped; the alkali-activated binder
   supply chain is fragile (Cemfree owner in administration 2024). Re-verify before
   modelling rounds.
7. **Whole-route options don't fit per-process rows cleanly.** H2-DRI+EAF, molten oxide
   electrolysis, cupola→induction conversion replace several processes at once; they are
   anchored to the dominant process row with a note. The model may want a
   `route_change` flag later.
8. **Options interact.** AD heat integration vs biogas upgrading are alternatives, not
   additive; biochar/biomass options across sectors compete for one UK feedstock pool;
   efficiency options change the sizing of everything downstream.
9. **Source-quality caveats:** several vendor/trade pages are undated (years marked
   approximate); two paywalled papers verified from abstracts only; the Ceramics UK
   roadmap technical appendix (which holds sector TRLs) returned HTTP 429 and could not
   be fetched; large PDFs were sometimes cited at document level rather than
   page level. Confidence columns reflect this.
10. **Boundary questions for the model:** minewater heat recovery mostly displaces an
    offtaker's gas, not the site's own; EV fleet charging benefits accrue outside the
    site boundary; fermentation CO2 recovery had no natural process row (mapped to
    packaging/site_services as hosts).

## Verification applied

All option_ids in the mapping table resolve to the library; all (activity, set,
process) keys resolve to the register; enums and TRL formats validated; every `[REF_ID]`
resolves to `references.csv`; one missing reference (IEAGHG steel CCS) was identified,
verified against the IEAGHG publications library, and added at assembly. Spot-checks
re-fetched the four most-cited new sources (DESNZ/ERM electrification study, MPA
roadmap, Carbon Trust manufacturing guide, Sandvik electric crushing coverage) and
confirmed them live on 2026-08-24.

## Suggested next steps

- Review the 51 blank-TRL options and decide whether qualitative `uk_status` is enough
  for modelling or whether a TRL-equivalent should be assigned editorially.
- Decide the whole-route representation (`route_change` options vs per-process rows).
- Connect options to the spec's `technology` table (§3.5): each mapping row is a
  candidate (process × equipment × fuel) technology entry awaiting cost data (D6).
