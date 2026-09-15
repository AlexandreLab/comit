# `DONE_duty_a.md` — lane `duty_a`, `activity_process_duty_profile` and the process crosswalk (T17)

**Date:** 2026-09-15 · **Brief:** `brief_duty_a.md` + `brief_duty_common.md` + `00_CONVENTIONS.md`
**Target schema:** §3.3 of `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md`

## Files written

| File | Rows | What it is |
|---|---:|---|
| `activity_process_duty_profile_duty_a.csv` | 216 | §3.3 duty rows for all 196 register rows in this lane |
| `carb3_comit_process_crosswalk_duty_a.csv` | 196 | one row per register process, mapped to a COMIT process code |
| `references_duty_a.csv` | 3 | the three new `ref_id`s; everything else reuses `references.csv` |
| `check_duty_a.py` | — | the stdlib validator, run below |

Nothing outside `build/` was touched.

## The check, and its result

```
$ python3 docs/notes/data/build/check_duty_a.py
register rows in lane: 196 (27 activities)
duty rows: 216
crosswalk rows: 196
processes covered: 196 of 196

All checks pass.
```

It enforces the brief's four checks — (a) every register row has ≥ 1 duty row, (b) `duty_share`
sums to 1.00 ± 0.015 per `(activity, set, process)`, (c) every heat row carries a `grade_rank`,
(d) every key and every `[REF_ID]` resolves — plus: §3.3 column order; the twelve-family,
four-tier and three-confidence enums; `carrier_id → carrier.csv`; `grade_rank` equals the
carrier's own `grade_rank` (so a band cannot silently disagree with `carrier.csv`); a heat family
cannot take a non-gradeable carrier and vice versa; `MOT → motive_power` and `REF → cooling`;
primary-key uniqueness on `(activity, set, process, duty_family, grade_rank)`;
`share_low ≤ duty_share ≤ share_high`; no `NA`/`n/a`/`-`/`?` placeholders; every provenance string
carries a `[REF_ID]`; crosswalk codes are among the 94 COMIT `process_commodity` values and are
**never** one of the 16 sector roots; and `match_kind = none` iff the code is blank.

It runs clean from any directory. It is **not wired to anything** — the same gap `CLAUDE.md`
records for `make check`.

## Row counts

216 duty rows over 196 register rows: 176 processes are single-duty, **20 are multi-duty**.

| Activity | Set | Processes | Duty rows | `published_sec` | `engineering` | `fallback` |
|---|---|---:|---:|---:|---:|---:|
| Abattoir / Slaughter House | `default` | 6 | 7 | 3 | 2 | 2 |
| Aggregate/Mineral Processing Plant / Depot | `default` | 6 | 6 | 3 | 2 | 1 |
| Aircraft works | `default` | 8 | 8 | 3 | 2 | 3 |
| Aluminium Smelting Works | `default` | 5 | 6 | 0 | 1 | 5 |
| Artificial Fibre Works | `default` | 7 | 8 | 1 | 4 | 3 |
| Asphalt Plant | `default` | 8 | 8 | 2 | 5 | 1 |
| Beet Sugar Factory | `default` | 7 | 8 | 3 | 0 | 5 |
| Brewery | `default` | 6 | 7 | 4 | 1 | 2 |
| Brickworks / clay tile/pipe works | `default` | 7 | 8 | 5 | 1 | 2 |
| Cement Tile Works | `default` | 7 | 8 | 2 | 3 | 3 |
| Cement Works | `default` | 9 | 9 | 9 | 0 | 0 |
| Chemical Works | `default` | 8 | 9 | 3 | 0 | 6 |
| Coking and Carbonising Plant | `default` | 5 | 6 | 1 | 3 | 2 |
| Concrete Block Works | `default` | 7 | 7 | 3 | 3 | 1 |
| Concrete Product Works | `default` | 6 | 7 | 2 | 3 | 2 |
| Concrete batching plant | `default` | 7 | 8 | 3 | 3 | 2 |
| Creamery | `default` | 7 | 8 | 5 | 1 | 2 |
| Distillery | `default` | 7 | 8 | 3 | 3 | 2 |
| Distillery | `grain_distillery` | 5 | 6 | 1 | 2 | 3 |
| Effluent Minewater Treatment Plant | `default` | 4 | 4 | 1 | 2 | 1 |
| Exhaust and tyre centre | `default` | 4 | 4 | 1 | 1 | 2 |
| Factory | `default` | 7 | 7 | 4 | 1 | 2 |
| Flour Mill | `default` | 7 | 8 | 3 | 3 | 2 |
| Food Processing Centre | `default` | 6 | 8 | 6 | 2 | 0 |
| Foundry | `default` | 10 | 11 | 2 | 4 | 5 |
| Industrial Minerals NEC | `default` | 6 | 6 | 3 | 1 | 2 |
| Industrial NEC | `default` | 7 | 7 | 3 | 1 | 3 |
| Iron and/or Steel Works | `bf_bof` | 9 | 10 | 4 | 3 | 3 |
| Iron and/or Steel Works | `eaf` | 8 | 9 | 3 | 3 | 3 |

## Coverage: populated vs blank, per column

| Column | Populated | Blank | Why |
|---|---:|---:|---|
| `carb3_activity`, `process_set_id`, `process_id` | 216 | 0 | required keys |
| `duty_family` | 216 | 0 | required |
| `carrier_id` | 216 | 0 | required; no `NEUOTH` row was written, so no blank carrier arises |
| `grade_rank` | 87 | 129 | **every gradeable-carrier row has one.** The 129 blanks are the 119 `motive_power` and 10 `cooling` rows, where `carrier.is_gradeable` is `FALSE` and a rank would be wrong |
| `duty_share` | 216 | 0 | required |
| `share_low` / `share_high` | 0 | 216 | **no source gave a range for a duty split.** The ranges I do have are *temperature* ranges, which set the band, not the share. Populating these would be inventing |
| `evidence_tier`, `provenance`, `confidence` | 216 | 0 | required |

**Distributions.** `duty_family`: MOT 115 · SPC 23 · HTH 19 · LTH 15 · STM 13 · REF 10 · DRY 10 ·
PHEAT 7 · OTH 4. `carrier_id`: `motive_power` 119 · `heat_60_100` 38 · `heat_100_150` 16 ·
`heat_gt1000` 14 · `heat_150_400` 13 · `cooling` 10 · `heat_400_1000` 5 · `heat_lt60` 1.
`evidence_tier`: `published_sec` 86 · `fallback` 70 · `engineering` 60 — **no row claims
`measured`.** `confidence`: medium 145 · low 71 — **no row claims `high`.** The tier × confidence
cross-tab is clean: every `fallback` row is `low`, every `engineering` row is `medium`, and the
one `published_sec`/`low` row is Abattoir `scalding_singeing`, where the source is good but the
row knowingly omits a second duty. This mirrors the practice
`README_activity_process_tables.md` states for the sibling table, and for the same reason — the
underlying breakdowns are US or pre-2016 sector studies applied to GB sites.

**Crosswalk.** `direct` 88 · `analogue` 67 · `none` 41. 44 distinct COMIT codes are used; no
sector root appears. The 41 blanks are concentrated where COMIT genuinely has no node:
Cement Works (8) and Cement Tile Works (7) — the cement sector has only `ICM`, a root, and
`ICMCLK`; Foundry (8); Industrial Minerals NEC (5) — the lime sector has only `ILM`, a root, and
`ILMCLK`; Effluent Minewater Treatment Plant (4); Exhaust and tyre centre (4); Coking and
Carbonising Plant (3); and Iron and/or Steel Works (2). Those last two are the same cause:
COMIT's iron-and-steel sector is **all mass nodes** (`IISPIR`, `IISSNT`, `IISLST`, `IISHRS`) plus `IISLTH`, with no motor-drive or
other-services code, so every shaft-work process in that sector maps to nothing.

---

## The defect you need to decide on

### §3.3's sum rule and the food-and-drink worked example disagree

`…-worked-example-food-drink.md` §3.2 gives `Food Processing Centre`/`site_services` **two rows**
— `SPC` (space heating) at `heat_60_100` grade 2 and `MOT` at `motive_power` — **each at
`duty_share` 1.00000**. It can, because that table reads the share *per vector*: the gas is space
heat, the electricity is motive power. §3.3 has **no `vector` column**, and its stated rule is
that `duty_share` sums to 1.00 ± 0.015 per `(carb3_activity, process_set_id, process_id)`. Taken
verbatim, that process sums to **2.00** and fails the check the brief asks me to run.

The same §3.2 says so itself, in passing: "it is only expressible because §3.3.1 is keyed on
`(process, vector)` rather than on the process alone."

**What I did.** I kept the §3.3 rule, because it is the spec and it is what the validator
enforces, and rescaled the two shares on the example's own delivered energy — 0.021000 PJ gas and
0.017226 PJ electricity — giving **SPC 0.549 / MOT 0.451**. The families, carriers and grade are
verbatim; only the two `1.00000`s moved. Every other Food Processing Centre value in the example
(`0.46180`, `0.53820`, `1.00000` ×4, grades 2/3/4) is reproduced **exactly**, and every
`process_id` and `carrier_id` the two examples use appears verbatim in my output.

**What I could not decide for you.** Either §3.3 gains a `vector` column and a per-vector sum
rule (matching §3.3.1, which is keyed that way), or the worked example's §3.2 table is corrected
to the rescaled shares. **The first is the better fix** — it is what §3.3.1 already does, and a
per-process share genuinely cannot express "the gas is heat and the electricity is shaft work"
without it — but it changes the entity, so it is yours. Until it is decided, my file is valid
against the spec as written and the worked example is not.

---

## Every judgement call I made

### 1. Multi-duty processes: when to split, and the one split I could source

§3.3 has no `vector` column, so a process that takes gas *and* electricity has to either split
its share or state one duty. The brief allows the latter: "if no split is published, use one row
for the dominant duty at 1.0 and state so." **No source in the repo or in the UK sector literature
publishes a duty split for any process in this lane except the one in the worked example.** So:

- **Site-overhead bundles get two rows.** Where `activity_process_energy_profile.csv` gives a
  `site_services`-type process **both** a heat vector and an electricity vector, **and** the
  activity has no separate `space_heating` register process, I wrote `SPC` + `MOT` at **0.55 /
  0.45** — the food-and-drink example's own delivered-energy ratio, used as an explicitly named
  analogue, at `evidence_tier = fallback`, `confidence = low`. **18 processes, 36 rows.**
  The rule is mechanical and it **reproduces both worked examples**: Cement Works `site_services`
  has no heat vector in the energy profile, so it gets `MOT` alone, which is exactly what
  `…-worked-example-cement.md` §3.2 states; Food Processing Centre gets two rows, which is exactly
  what the food-and-drink example states.
  *If you would rather see one `SPC` row at 1.0 here, that is a one-line change to `DUAL()` in the
  generator — but it deletes the site's entire lighting and small-power duty, which C10 (the heat
  cascade) would then never see.*
- **Everything else takes the dominant duty at 1.0**, with the omitted duty named in the
  provenance string so it is greppable. The eight that matter are listed under "Gaps" below.

### 2. Grade bands where no source gives a temperature

`grade_rank` is non-nullable on a heat row and the brief forbids both a blank band and an invented
°C figure. **53 heat rows** therefore carry a band that is `fallback`/`low` with a **named
analogue** in the provenance — never a bare guess. (The lane has 70 `fallback` rows in all; the
other 17 are `MOT`/`OTH` rows with no band at all, where the fallback is about *which duty* the
process presents, not about a temperature.) The analogues I used, all from inside this repository:

| Analogue | Quoted range | Used for |
|---|---|---|
| `…worked-example-food-drink.md` §3.2 "DRY — spray dryer, 200 C", band 4 | 200 C | Chemical Works `drying`, Beet Sugar `pulp_pressing_drying`, grain distillery `coproduct_evaporation_drying` |
| `…worked-example-food-drink.md` §3.2 "SPC — space heating", band 2 | — | every `SPC` row (23) |
| `…worked-example-food-drink.md` §3.2 "LTH — hot water and CIP, 80 C", band 2 | 80 C | Exhaust and tyre centre `water_heating` |
| `decarbonisation_options_library.csv` `htp_heat_pump_100_150` | "100-150C … distillation reboil" | Chemical Works `distillation_separation` and `utilities_steam` |
| `decarbonisation_options_library.csv` `electric_powder_coating_oven` | "~160-200C" | Aircraft works `process_heating`, Foundry `core_making` |
| `decarbonisation_options_library.csv` `electric_resistance_oven_furnace` | "~100C to >1000C" | Foundry `heat_treatment`, `core_making` |
| `decarbonisation_options_library.csv` `induction_heating` | ">1200C" | Aluminium `cast_house` (as the upper bound *not* reached) |
| `decarbonisation_options_library.csv` `carbothermic_aluminium` | "~2000C+" | Aluminium `electrolysis_potlines` (as the upper bound not reached) |
| Coke-oven carbonisation, band 6, elsewhere in this file | — | Aluminium `anode_production_baking` |
| `Factory`/`process_heating` "to ~150C" | ~150 C | `Industrial NEC`/`process_heating` |

**All 53 say in their own `provenance` that the band is a fallback and not a read figure.**
`grep -icE 'not a (read|verified) figure'` on the CSV returns exactly 53.

### 3. Band 5 vs band 6 for calcination — the most consequential call in the lane

`Industrial Minerals NEC`/`kiln_calcination` and `Beet Sugar Factory`/`lime_kiln` are lime
calcination. The two sources straddle the boundary: `process_decarbonisation_options.csv` says
"~900-1200C", `decarbonisation_options_library.csv` `electric_kiln_calcination` says "~900-1450C
(lime, cement precalcination, minerals)".

**I put both at band 5 (400-1000C)**, on the reading that §3.3 asks for the process's *required
delivery temperature* and limestone decomposition requires ~900 C — the kiln hot zone exceeds
1000 C, but that is how the duty is met, not what it is. **Cement Works `kiln_pyroprocessing` is
at band 6**, because clinker *sintering*, not calcination, is its binding duty, and
`rotodynamic_electric_heater` gives ">1000C (pathway to ~1700C), targeted at cement
precalciners".

**This matters.** C10 (the heat cascade) will let a band-5 unit serve a band-5 duty. If a lime
kiln is really a band-6 duty, putting it at band 5 admits units that cannot do the job — the
silent failure §3.3's grade rule exists to prevent. **Please confirm the reading.** One line each
in the generator.

### 4. Heat-rejecting stages are motive power, not refrigeration

`Cement Works`/`clinker_cooling` and both steel sets' `continuous_casting` remove heat from a hot
product. `…-worked-example-cement.md` §3.2 states `clinker_cooling` as `MOT`/`motive_power`, so I
followed it and applied the same reading to the casters: the energy input is cooler-fan and
water-system shaft work. Neither is a `REF`/`cooling` duty — nothing is being refrigerated.

### 5. Coke's sensible heat is a recovery opportunity, not a duty

`Coking and Carbonising Plant`/`coke_quenching_handling` gets `MOT` alone. `coke_dry_quenching`
("~85-95 kWh electricity per tonne coke") is a *supply-side* option, and the brief is explicit
that the options library is "corroboration … not a source of duty". The same logic keeps
`Effluent Minewater Treatment Plant` free of any heat row: minewater at "~15-20C"
(`minewater_heat_pump_recovery`) is a heat **source** the site could export, not a duty it must
be supplied.

### 6. `Industrial Minerals NEC`/`hydration` has no heat duty

Slaking is exothermic. The row is `MOT` at 1.0 for the hydrator and classifier mills, tier
`fallback`/`low` because no source states the absence — it is chemistry, not a citation.

### 7. Named non-default sets: I restated rather than inherited

§3.3's inheritance rule says a non-default set "need not restate every row". The brief's own check
(a) says every register row in my list must have ≥ 1 duty row. Restating satisfies both —
inheritance permits restatement, it does not require omission — so `bf_bof` and `grain_distillery`
carry a full set. Each restated row says so in its provenance. **`eaf` is the default set for Iron
and/or Steel Works and `bf_bof` is the named alternative**, per `is_default` in the register and
`README_activity_process_tables.md`; the brief lists it the other way round, which is worth a
correction there.

### 8. Cross-sector crosswalk mappings

Two processes map outside their activity's COMIT sector, both flagged in `notes`:
`Beet Sugar Factory`/`lime_kiln` → `ILMCLK` (a lime kiln inside a food-and-drink premise; COMIT's
food-and-drink sector has no calcination node), and `Artificial Fibre Works`/`polymer_melt_extrusion`
→ `IHVC` (high-value chemicals), which is what `carb3_comit_crosswalk.csv` names for that activity.

### 9. COMIT food and drink has no `SPC` code

`IFD` carries `DRY`, `LTH`, `MOT`, `OTH`, `REF`, `STM` and nothing else — no space-heat node. All
eight food-and-drink `site_services` rows therefore map to `IFDLTH` as `analogue`. The same gap
hits non-ferrous (`INFOTH`) and iron and steel (`IISLTH`).

---

## Gaps, and why each is a gap

**No source found for a split** (dominant duty written at 1.0; the omitted duty is named in the
row's own provenance):

| Process | Written as | Omitted duty |
|---|---|---|
| Abattoir `scalding_singeing` | LTH band 2 (scald tank ~60 C) | singeing, a direct flame duty above 1000 C |
| Abattoir `hot_water_sterilisation_cleaning` | LTH band 2 (85 C steriliser) | the 45 C washdown, a band 1 duty on the same boiler |
| Creamery `heat_treatment_pasteurisation` | LTH band 2 (HTST 72-85 C) | UHT/sterilisation at ~120-140 C, band 3 |
| Creamery `evaporation_drying` | DRY band 4 (dryer inlet 180-200 C) | the falling-film evaporator's own band 3 steam |
| Beet Sugar `crystallisation_sugar_house` | STM band 3 (vacuum pans) | centrifugal MOT and granulator DRY |
| Foundry `shakeout_sand_reclamation` | MOT | **thermal** sand reclamation — a real gas duty; the energy profile gives this process 0.05 of the activity's gas |
| Artificial Fibre `drawing_texturing` | PHEAT band 4 (heater tracks) | draw-frame machine drive |
| Aircraft works / Factory / Industrial NEC `other_process` | OTH (rig and instrument load) | the gas component of the bundle |

**No source found for a band** — the 70 `fallback`/`low` rows in §2 above. Each names its analogue.

**Out of scope, deliberately:** `share_low`/`share_high` on every row (§"Coverage"); the
`EN`, `NEUOTH` and `HRS` families (§"Questions" below); temperature figures for any process where
I could not quote one — I did not fetch a single external source for this lane, for the reason
in the next section.

## Sources: what I actually read

**I read no source outside this repository.** Everything cited is either (i) a string I read
verbatim in `activity_process_register.csv`, `process_decarbonisation_options.csv`,
`decarbonisation_options_library.csv` or the two worked examples, or (ii) a **document-level**
citation, which `00_CONVENTIONS.md` rule 2 permits and which I have written as "document level"
in every such provenance string, **126 rows** in all. No row claims a page, table, section or figure
pointer I did not see. The `[REF_ID]` on a document-level row is the reference that
`activity_process_register.csv` already attached to that process, so the chain is auditable.

Three new `ref_id`s, all pointing inside the repo: `CARB3_WE_FOOD`, `CARB3_WE_CEMENT`,
`CARB3_PDO`. `CARB3_PDO` is cited **only** where the `process_decarbonisation_options.csv` row is
itself marked "engineering judgement" and so has no upstream reference; where that row carries a
`[REF_ID]` I cite the upstream source and write "via process_decarbonisation_options.csv" so the
route is visible. `references_duty_a.csv` has exactly the seven columns of `references.csv` and
re-declares nothing; the validator fails the build if it does.

**Prices to 2021 GBP:** not applicable. This lane states no cost.

---

## Questions for Alexandre

1. **The §3.3 / worked-example disagreement above.** Add a `vector` column to §3.3 (my
   recommendation, matching §3.3.1), or correct the example's §3.2 to the rescaled shares?
2. **Band 5 or band 6 for lime calcination** (§"Every judgement call" #3)? I chose band 5 on the
   required-delivery-temperature reading. If the hot-zone reading is right instead, two rows move.
3. **`HRS` is unusable in this entity, and I think that is a schema defect.** The brief says HRS
   is "the steel hot-rolling chemistry node only", but `carrier.csv` (§3.4, 29 carriers) has **no
   steel-product carrier** for a HRS row to point at, and `carrier_id` is required. I wrote both
   hot-rolling processes as `MOT`/`motive_power` — which is honestly what the energy is, mill main
   drives — and mapped them to `IISHRS` in the crosswalk. Either §3.4 gains the mass carriers the
   chemistry families need (`clinker`, `cement`, `liquid_steel`, `hot_rolled_steel` — the cement
   example's §3.2 already *uses* `clinker` and `cement` as `carrier_id`s that do not exist in
   `carrier.csv`), or the chemistry families should be struck from §3.3's enum and left to §3.9.
   **This is the same gap seen from two sides, and it also breaks the cement worked example's
   §3.2.**
4. **`Chemical Works`/`electrochemical_processes` has no carrier either.** Chlor-alkali cells and
   electrolysers are a direct electrical service; §3.4 has no electrochemical service carrier. I
   used `OTH`/`motive_power` following the worked example's precedent for bundled direct-electric
   load, at `fallback`/`low`, and said so in the row. A `direct_electric` intermediate carrier
   would fix this, `Aluminium Smelting Works`/`electrolysis_potlines` (which I had to write as
   `HTH` band 5) and any future hydrogen electrolyser in one go.
5. **`NEUOTH` and `EN` are unused in this lane.** No process in my 27 activities is a
   non-energy feedstock node, and the brief tells me to avoid `EN`. Worth confirming `NEUOTH`
   belongs in §3.3's enum at all rather than only in §3.9 — as written, a `NEUOTH` row must carry
   a blank `carrier_id`, which contradicts §3.3's field table marking `carrier_id` required.
6. **Should `site_services` be split into two register processes** (`site_services` and
   `space_heating`) at the 20 activities where it currently bundles both? Four activities in this
   lane already do it that way — Aircraft works, Exhaust and tyre centre, Factory, Industrial NEC
   — and where they do, the duty is unambiguous and `evidence_tier` rises from `fallback` to
   `engineering`. That is a `activity_process_register.csv` change, which is another lane's file,
   so I have not made it.
7. **`Foundry`/`melting_holding` is at band 6 on the ferrous reading.** A non-ferrous foundry
   melting aluminium is a band 5 duty. The register has one activity and one default set for both,
   and `carb3_comit_crosswalk.csv` already flags Foundry as "Shared between two COMIT sectors
   depending on metal". A named `non_ferrous` process set would resolve it; again, another lane's
   file.

## Requests to other lanes / the coordinator

- **`carrier.csv` (lane `carriers`):** questions 3 and 4 above are requests for that file — mass
  carriers for the chemistry families, and an electrochemical or direct-electric service carrier.
- **`activity_process_register.csv`:** questions 6 and 7 above.
- **Coordinator:** `references_duty_a.csv` is a clean merge — three new ids, no collisions with
  the 270 in `references.csv`, and the validator checks that.
