# DONE — lane `loadshape` (`process_load_shape`, spec §3.13)

Written 2026-09-15.

## Files written

| File | What it is |
|---|---|
| `docs/notes/data/process_load_shape.csv` | The deliverable. 371 rows |
| `docs/notes/data/build/references_loadshape.csv` | 2 new references for the coordinator to merge |
| `docs/notes/data/build/check_loadshape.py` | The check the brief asks for; no such script existed, so I wrote one. Stdlib only, runs clean from any directory |
| `docs/notes/data/build/DONE_loadshape.md` | This file |

Nothing outside those four was touched. `docs/notes/README.md` needs a row for the new
table (per CLAUDE.md, an unregistered document is invisible) — that is a coordinator edit,
not mine, and so is merging `references_loadshape.csv` into `references.csv`.

```
$ python3 docs/notes/data/build/check_loadshape.py
OK — 371 rows, 55 activities, all enums valid, standing rule holds, all [REF_ID]s resolve,
both worked examples' §1.10 tables reproduce.
```

The check covers: column order; exactly one row per register `(carb3_activity, process_id)`
and no row without one; `shape_id` unique and equal to `<activity_slug>__<process_id>`;
every enum, boolean and confidence value valid; §3.13's rule that `standing` holds **iff**
`runs_when_idle = TRUE`; `duty_factor ∈ (0,1]` and `peak_to_mean ≥ 1` where populated; no
`NA`/`n/a`/`-`/`?` placeholders; non-empty provenance; every `[REF_ID]` resolving against
`references.csv` + `references_loadshape.csv`; and both worked examples' §1.10 tables
reproducing row for row.

## Row count — 371, not 376, and why

The register has 376 rows but only **371 distinct `(carb3_activity, process_id)` pairs**.
Five pairs appear in two process sets each:

| Activity | `process_id` | Sets |
|---|---|---|
| Distillery | `site_services` | `default`, `grain_distillery` |
| Iron and/or Steel Works | `secondary_metallurgy` | `eaf` (default), `bf_bof` |
| Iron and/or Steel Works | `continuous_casting` | `eaf`, `bf_bof` |
| Iron and/or Steel Works | `reheat_furnaces` | `eaf`, `bf_bof` |
| Iron and/or Steel Works | `site_services` | `eaf`, `bf_bof` |

The brief asks for both "376 rows" and "every register (activity, process) has exactly one
row", and those cannot both hold. I took the second, because it is also what the brief's own
rule implies — "named non-default sets share the default's shape unless a source says
otherwise" — and because `shape_id = <activity_slug>__<process_id>` would otherwise not be a
primary key. In all five cases the two sets describe the same physical operation (ladle
furnace, caster, reheat furnace, site utilities), so one shape row serves both. **No
`process_set_id` column is carried**; the shape is set-independent by construction.

## Coverage, per column

| Column | Populated | Blank | Note |
|---|---|---|---|
| `carb3_activity` | 371 | 0 | 55 activities |
| `shape_id` | 371 | 0 | unique |
| `process_id` | 371 | 0 | all resolve to the register |
| `shape_class` | 371 | 0 | required on every row |
| `duty_factor` | **0** | **371** | see "The numbers are all blank" |
| `peak_to_mean` | **0** | **371** | ditto |
| `runs_when_idle` | 371 | 0 | `TRUE` on 81 rows, all of them `standing` |
| `seasonality` | 371 | 0 | |
| `provenance` | 371 | 0 | 10 rows carry an external citation; 361 carry an honest "no load-shape source found" |
| `confidence` | 371 | 0 | `medium` 10, `low` 361, `high` 0 |

Class distribution: `throughput_following` 121, `standing` 81, `flat` 68, `batch_cyclic` 59,
`intermittent` 29, `seasonal` 13.
Seasonality: `none` 337, `summer_weighted` 16, `winter_weighted` 13, `campaign` 5.

## The numbers are all blank

`duty_factor` and `peak_to_mean` are empty on all 371 rows. The brief allows a number only
where a source states or lets you compute it, and says the §3.13 indicative ranges are not a
source. I found no published load profile, sub-metering study or stated load factor for any
of these 230 process types that would survive that test. What I have is:

- **In repo.** The register's provenance and `activity_process_energy_profile.csv` are
  *energy share* citations ("clinker production accounts for over 90% of total energy"),
  which say nothing about duty factor or peakiness. `docs/notes/data/` holds no load-shape
  data at all.
- **Web.** I attempted targeted UK-first lookups and stopped after they stopped paying.
  A search for an MPA/Cembureau/DESNZ statement that a UK cement kiln runs 24/7 returned
  fact sheets on cement chemistry, alternative fuels and embodied CO₂, none of which states
  an operating pattern. The VOA Rating Manual section on cement works (section 220) describes
  the process but, in its own words as fetched, gives "no verbatim descriptions of continuous
  kiln operation, maintenance shutdowns, or specific operating schedules". The VOA section on
  asphalt coating plants returned HTTP 404 at the URL I tried, so nothing about UK asphalt
  seasonality is cited here.

This is the expected outcome and the brief says so, but it is worth being blunt about the
consequence: **§5.6 (the peak method, still unwritten) cannot be exercised against this table
as it stands**, and neither can C11 (the connection-capacity constraint), whose peak §3.14
says is rebuilt by that method. What this table delivers is the *classification* — which
processes run through the night, which follow production, which cycle — and that is the part
§3.13 says the shape decomposition exists for. The magnitudes have to come from half-hourly
or sub-metering work that nobody in this repo has done yet.

## What the 10 cited rows are

| Rows | Source | What it actually says |
|---|---|---|
| 6 (Beet Sugar Factory) | `[VOA_RM_BEET_SUGAR]` §6.3 | Campaign months are September to February and the front-end plant is "utilised for only part of the year"; the back-end juice run "now occurs all year round". Read in full by me |
| 2 (Pottery) | `[DECC_CERAMIC_2015]` §3.3.1 | Whitewares involve "multiple firing steps, greater use of less-efficient batch firing" — read via the register's provenance, not the PDF |
| 1 (Asphalt Plant `screening_mixing`) | `[ES_ASPHALT_2023]` §1.1 p.2 | "batch plants screen to hot bins and mix in a pugmill" — via the register |
| 1 (Putrescible `digester_mixing_pumping`) | `[IEA_FW]` Table 5 p.20 | "Core continuous electrical loads of an AD plant" — via the register |

Where a pointer came from the register's recorded citation rather than from the document
itself, the provenance string says "via activity_process_register.csv" so the chain is
visible. Only `[VOA_RM_BEET_SUGAR]` was read first-hand.

The other 361 rows say, verbatim and uniformly: *"No load-shape source found. shape_class
assigned from the equipment recorded in activity_process_register.csv ('…') against the
[CARB3_SPEC_IMPL] §3.13 shape-class table (…)"*, and carry `confidence = low`. That is a
citation to the spec's own definition of the six classes, not to evidence about the process.

## Judgement calls

Every one of these is a class assignment, never a number.

1. **The class is read off the equipment, through §3.13's own examples.** §3.13 names
   example equipment for each class (mills, crushers, conveyors, pumps →
   `throughput_following`; batch ovens, autoclaves, curing, electric melting →
   `batch_cyclic`; and so on). I matched the register's `equipment_examples` against that
   list. Where a process listed equipment from two classes I picked the one carrying the
   energy, and the row is `low`.
2. **Compressed air is `throughput_following`, not `standing`** — see question 2 below. This
   follows the food & drink worked example rather than §3.13's own example list, and it
   propagates to all 10 dedicated `compressed_air` rows.
3. **Refrigeration is `standing` + `summer_weighted` everywhere** (16 rows, including
   `refrigeration_chilling`, `refrigeration_attemperation`, `process_cooling`,
   `chilled_water_plant`). The `standing` half is §3.13's own example and the food & drink
   example's; the `summer_weighted` half generalises that example's `refrigeration` row to
   every activity, on condenser duty rising with ambient. Cited nowhere. See question 5.
4. **Heated storage that is held hot overnight is `standing`.** `bitumen_storage_heating`
   (heated binder tanks) is the clear case: it draws when the plant is stopped, which is
   exactly the distinction §3.13's rule exists to make. Likewise `spinning_hvac` (spinning
   hall humidity control), `aeration_odour_control` (biofilter and ASP fans),
   `dry_dock_services` (shore power to berthed vessels), `lab_equipment` (ULT freezers,
   incubators) and the fab's `cleanroom_hvac`, `chilled_water_plant`, `ultrapure_water`,
   `bulk_gases_cda` and `exhaust_abatement`.
5. **`runs_when_idle` says nothing about a 24/7 site.** For continuously operating sites —
   minewater treatment, mine ventilation, gas compression, refineries — I used `flat`
   ("constant while the site operates") and `FALSE`, on the reading that the site's operating
   pattern belongs in §3.12 `premise_operating_profile`, not in the shape class. Using
   `standing` for them would have inflated the count of processes claimed to run outside
   operating hours to no purpose, since for those sites there are no such hours.
   **The one place I split this**: `dewatering_pumping` is `standing` at the two quarry
   activities (float-controlled sump pumps that run whether or not the pit is working) and
   `flat` at Pumping Mines, where dewatering *is* the production.
6. **Contested singles**, all `low`, each worth a second opinion:
   - `reaction_heating` (Chemical Works) → `flat`. The equipment list mixes continuous fired
     heaters with batch jacketed reactors; I went with the continuous plant that dominates UK
     chemical energy. A site-heterogeneity argument for `batch_cyclic` is just as available.
   - `paint_shop` (Motor Vehicle Works) → `flat`: booth air handling and stoving ovens hold
     condition through the shift rather than cycling per body.
   - `press_drives` and `mailroom_finishing` (Newspaper print works) → `batch_cyclic`: a
     newspaper press runs in print windows, not continuously.
   - `sortation_machinery` (Post Office Sorting Centre) → `batch_cyclic`: mail arrives in
     waves.
   - `water_heating` (welfare hot water, 4 rows) → `intermittent`, driven by occupancy.
   - `glazing_decoration` (Pottery) and `floor_germination_turning` (Maltings – Trad) →
     `intermittent`: both are operator-paced.
   - `beet_reception_preparation` → `throughput_following` + `campaign`: flumes and slicers
     follow the beet intake rate within the campaign.
   - `packing_dispatch` and `loadout_storage` → `intermittent`, following the cement worked
     example's treatment of `packing_dispatch`.
7. **`seasonal` is used only for space and building heat** (13 rows: `space_heating`,
   `space_water_heating`, `water_aggregate_heating`), all `winter_weighted`. Campaign
   processes got their seasonality through the `seasonality` column while keeping the class
   that describes their operation — a beet diffusion tower is `flat` *and* `campaign`, and
   collapsing that to `seasonal` would lose the shape within the campaign.

## Gaps

| Gap | Why |
|---|---|
| `duty_factor`, `peak_to_mean` — all 371 rows | No source found. See above. This is the whole quantitative content of §3.13 |
| `confidence = high` — 0 rows | Nothing was measured; the best evidence here describes an operating *mode*, never a magnitude |
| `campaign` seasonality outside beet sugar | The brief names maltings, seasonal distilling and quarry winter shutdowns as candidates. I found no citation for any of them and would not assert them unsourced. Modern Scotch distilleries and UK maltings run year round as far as I can tell, so a "silent season" claim may be historic rather than current — but that is a hunch, and it is not in the file |
| Asphalt plant seasonality | UK asphalt demand is widely understood to be laying-season weighted; the VOA page I tried for it 404'd and I found no substitute. All asphalt rows are `none` |
| Heterogeneous NEC activities (Factory, Works, Workshop, Mill, Industrial NEC, Large industrial NEC) | Their processes are ECUK end-use buckets, not unit operations. `process_heating` → `batch_cyclic` and `machine_drive` → `throughput_following` are the best that can honestly be said of a bucket. 40-odd rows are weak for this reason rather than for want of searching |
| `unit.load_shape_override` (§3.5) | Out of scope for this lane; the `units` lane owns it. No unit in either worked example sets it |

## Questions for Alexandre

1. **§3.13 marks `duty_factor` and `peak_to_mean` `Req: yes`, and I have shipped 371 blanks.**
   The brief is explicit that a plausible number is a defect, so I left them out — but as
   written, a validator built from §3.13 fails on every row of its own reference table. Does
   §3.13 relax them to optional (blank = "shape known, magnitude not"), or does the table stay
   unshippable until someone does the half-hourly work? My recommendation is to relax them and
   let §5.6 fall back on the class, since the class is the part the decomposition was designed
   to carry.

2. **`compressed_air`: §3.13's class table and the food & drink worked example disagree.**
   §3.13 lists "compressed air" as an example of `standing`, which by §3.13's own rule forces
   `runs_when_idle = TRUE`. The food & drink worked example §1.10 gives `compressed_air` as
   `throughput_following`, `runs_when_idle = false`, and its prose then asserts that the site
   has exactly two `standing` rows. I followed the worked example — compressors unload when
   the plant stops — which keeps the example reproducing but leaves §3.13's example list
   saying something the reference data does not do. If §3.13 is right instead, 10 rows flip
   class and `runs_when_idle`, and the food & drink example's prose needs editing. One of the
   two documents should change; I did not touch either.

3. **Should the worked examples' numbers be adopted as the seed values?** Both examples' §1.10
   tables state `duty_factor` and `peak_to_mean` for 14 `(activity, process)` pairs, and my
   table leaves those 14 blank, so the examples currently show numbers their own reference
   table does not hold. They are, as far as I can tell, illustrative rather than sourced,
   which is why I did not import them. If you want them in, it is one edit — here they are:

   | Activity | `process_id` | `duty_factor` | `peak_to_mean` |
   |---|---|---|---|
   | Cement Works | `quarrying_crushing` | 0.85 | 1.30 |
   | Cement Works | `raw_grinding_blending` | 0.95 | 1.20 |
   | Cement Works | `raw_meal_homogenisation` | 1.00 | 1.05 |
   | Cement Works | `kiln_pyroprocessing` | 1.00 | 1.05 |
   | Cement Works | `clinker_cooling` | 1.00 | 1.05 |
   | Cement Works | `cement_grinding` | 0.90 | 1.25 |
   | Cement Works | `packing_dispatch` | 0.35 | 3.00 |
   | Cement Works | `site_services` | 1.00 | 1.00 |
   | Food Processing Centre | `boiler_steam_hot_water` | 0.55 | 2.40 |
   | Food Processing Centre | `direct_heating` | 1.00 | 1.10 |
   | Food Processing Centre | `refrigeration` | 1.00 | 1.00 |
   | Food Processing Centre | `machinery_motors` | 0.85 | 1.35 |
   | Food Processing Centre | `compressed_air` | 0.80 | 1.45 |
   | Food Processing Centre | `site_services` | 1.00 | 1.00 |

   The classes, `runs_when_idle` and `seasonality` in those 14 rows *do* match the examples
   exactly, and `check_loadshape.py` asserts it, so only the magnitudes are in question.

4. **§3.13's key is wrong for this data, and §3.14 inherits the problem.** §3.13 declares
   `process_id → activity_process_register` as the foreign key, but `process_id` is unique
   only within an activity — `site_services` appears at all 55 of them. The real key is
   `(carb3_activity, process_id)`, which is why the brief asked for the extra column. Should
   §3.13's field table say so, with `shape_id` demoted to a surrogate? §3.14
   `premise_weekly_profile` has the same `process_id` field and the same exposure.

5. **Is `summer_weighted` on all 16 refrigeration-family rows acceptable as a judgement, or
   should it be `none` until someone cites it?** It is the one place I generalised a worked
   example's value across activities without a source. Say the word and I will narrow it to
   the Food Processing Centre row the example actually states.

6. **`CARB3_SPEC_IMPL` is a self-citation.** 361 rows point at our own §3.13 as the basis for
   their class. `references.csv` otherwise holds only external sources, so the coordinator may
   prefer a different marker — a literal `inferred` token, or an empty ref with the sentence
   alone. I used a ref_id so that "every `[REF_ID]` resolves" stays a mechanical check.

7. **Related-table request (rule 6: I did not make this edit).** `premise_operating_profile`
   (§3.12) has `within_shift_peak_factor` and `operating_pattern`, and this table has
   `duty_factor`, `peak_to_mean` and `runs_when_idle`. When §5.6 is written it will need to
   say which wins when a premise states a within-shift peak factor that its processes' shapes
   cannot produce. Worth a line in §5.6's stub before anyone builds against it.
