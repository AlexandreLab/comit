# Conventions for every research lane (read first, follow exactly)

You are one of several parallel research agents building the CaRB3 site energy system
reference data in `docs/notes/data/`. The target schema is **§3 of
`docs/specs/2026-08-28-carb3-site-energy-system-implementation.md`** — read your entity's
section in full before writing a row. The two worked examples
(`docs/specs/2026-08-28-carb3-site-energy-system-worked-example-cement.md` §1.11–1.12 and
`…-worked-example-food-drink.md` §1.11–1.12) show the intended shape with real rows; **any
`unit_id`, `carrier_id` or `process_id` they use must appear verbatim in your output** so the
examples keep resolving.

## Hard rules

1. **Never invent or guess a value.** If no source states it, leave the field blank. A blank
   is correct; a plausible number is a defect. This applies to costs, efficiencies, temperatures,
   shares, TRLs, years — everything.
2. **Every populated row carries provenance** in the form `[REF_ID] pointer` where the pointer
   names the table, page, section or figure you actually saw. Document-level citation is
   allowed only when you say "document level".
3. **UK sources first.** Order of preference: DESNZ/BEIS/DECC publications (2015 industrial
   decarbonisation roadmaps, 2018 Industrial Fuel Switching, 2021–2024 electrification and
   heat-pump studies, DUKES, ECUK, CHPQA), UK ETS / Environment Agency permits, CCC, Carbon
   Trust, UK trade bodies (MPA, UK Steel, Ceramics UK, CPI, Food and Drink Federation, ADBA),
   the DESNZ/DEFRA GHG conversion factors; then EU BREF/JRC; then IEA/IRENA/DOE; then
   peer-reviewed papers; vendor material last and flagged `confidence = low`.
4. **Prices to 2021 GBP** where a cost is quoted; state the original year and currency in the
   provenance pointer and the conversion you applied (source the deflator / FX rate too).
   Units: energy PJ, capacity PJ/yr (MW for PV, storage, electrolysers, CHP electrical), cost
   £m, emissions kt CO₂e, distance km.
5. **References go in your own staging file**, `docs/notes/data/build/references_<lane>.csv`,
   with exactly the columns of `docs/notes/data/references.csv`
   (`ref_id,title,publisher,year,url,accessed,note`). Reuse an existing `ref_id` from
   `references.csv` where the source is already there — check before adding. New `ref_id`s are
   UPPER_SNAKE, ≤ 24 chars, unique. Do **not** edit `references.csv` itself; the coordinator
   merges.
6. **Write only the files your brief names.** Do not touch `carrier.csv`,
   `activity_process_register.csv`, `activity_process_energy_profile.csv`, the options
   library, the spec, the READMEs or any file another lane owns. If you believe another table
   needs a change, write the request into your `DONE_<lane>.md`.
7. **Enums exactly as the spec spells them.** Booleans as `TRUE`/`FALSE`. Blanks as empty
   strings, never `NA`, `n/a`, `-` or `?`.
8. **Keys must resolve.** `carb3_activity`, `process_set_id`, `process_id` come from
   `docs/notes/data/activity_process_register.csv` (376 rows, 55 activities). `carrier_id` from
   `docs/notes/data/carrier.csv` (29 rows; the six heat bands are `heat_lt60` rank 1 …
   `heat_gt1000` rank 6). Run the check script named in your brief before finishing.
9. **Stdlib Python only** (`pandas` is not installed) or R.
10. **Labels are never bare.** In your DONE file, write "C10 (the heat cascade)", not "C10".

## When you finish

Write `docs/notes/data/build/DONE_<lane>.md` with: row counts; coverage (populated vs
blank per column); the gaps and why each is a gap (no source found / source contradicts /
out of scope); every judgement call you made; questions for Alexandre. Then reply in the
terminal with only the path of that file.

If you cannot fetch a source (429, paywall), say so in the provenance and do not use it.
