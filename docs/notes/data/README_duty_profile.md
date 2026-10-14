# `activity_process_duty_profile.csv`: what each process needs

The reference table behind spec §3.3
([`activity_process_duty_profile`](../../specs/2026-08-28-carb3-site-energy-system-implementation.md)).
For every process of every CaRB3 activity it says **which duties the process presents**: the
services it needs, each a carrier at a temperature grade, and what share of the process's
energy each one is. It is the demand side of the carrier model.

**It states the kind of demand, never the amount.** How much a process needs comes from the
premise (`premise_process_detail.known_activity` in the carb3 slice; §3.3.1's shares of the
premise's metered energy in the spec). This table only says how that amount divides into
services.

**It names a service, never a fuel.** Which unit, burning what, serves a duty in a given year
is the optimiser's decision through C8 (carrier balance). Stating a fuel here as well would
over-determine the problem, which is why a duty on a fuel carrier is rejected at load.

The research behind the rows is in [`build/DONE_duty_a.md`](build/DONE_duty_a.md) and
[`build/DONE_duty_b.md`](build/DONE_duty_b.md); the open questions are in
[note 20](../20_reference_data_open_questions.md). Every `[REF_ID]` in `provenance` resolves to
[`references.csv`](references.csv).

## Field reference

**Reading the Key column.** **PK** marks the fields that together identify a row; "PK part"
means the field is one of several that do so together. **→** means the value must exist in
another table.

| Field | Required | Key | What it means | Example |
|---|---|---|---|---|
| `carb3_activity` | yes | **PK** part; → `activity_process_register.csv` | The CaRB3 activity class the row applies to. A premise reads the rows of its own `premise_record.carb3_activity` | `Cement Works` |
| `process_set_id` | yes | **PK** part; → `activity_process_register.csv` | The process set. `default` unless the activity has a named route. A named set need not restate every row: a `(process_id, duty_family, grade_rank)` it leaves out is inherited from `default` | `default` on 507 rows; `bf_bof` and `eaf` for `Iron and/or Steel Works`, `grain_distillery` for `Distillery` |
| `process_id` | yes | **PK** part; → `activity_process_register.csv`, on `(carb3_activity, process_set_id, process_id)` | The process. Unique only within an activity: `site_services` appears at all 55 | `kiln_pyroprocessing` |
| `duty_family` | yes | **PK** part. Pointed to by `activity_default_unit.csv` | The kind of service, one of the families below. It decides which carrier the row may sit on | `MOT` |
| `carrier_id` | yes | → `carrier.csv` | **What the duty is for**: a service carrier (graded heat, graded cooling, `motive_power` or `electric_service`). Never a `primary` carrier such as `electricity` or `natural_gas`, and never an `emission` carrier | `motive_power`; `heat_gt1000` on the cement kiln |
| `grade_rank` | where the carrier is gradeable | **PK** part; must equal `carrier.grade_rank` | The temperature band, rank 1 coldest within its family (heat or cooling). **Required on every heat and cooling row**: a heat duty with no grade is invisible to C10 (the grade cascade), so any heat at all could serve it and the solver would take the cheapest. Blank on `motive_power` and `electric_service` | `6` on `heat_gt1000`; `2` on `cooling_0_15`; blank on `motive_power` |
| `duty_share` | yes | | The fraction of the process's energy that is this duty, in [0, 1]. A process's rows sum to 1 (± 0.015) | `1.00000` on a single-duty process; `0.46180` hot water and `0.53820` steam on the dairy boiler |
| `share_low`, `share_high` | no | | A range on `duty_share`, where a source gave one. Must bracket it | blank on all but 2 rows |
| `evidence_tier` | yes | | How the share was established, on the D10 ladder (tiered site intelligence): `measured`, `engineering`, `published_sec` or `fallback` | `published_sec` on most `Cement Works` rows |
| `provenance` | yes | | The citation, `[REF_ID]` plus a pointer to the table, page or section read | `[BEES2016] Appendix B Table B.3 (p. 122)` on the `site_services` split |
| `confidence` | yes | | high, medium or low. Carried through to the outputs | `medium` |

## The duty families

Eleven families are defined (§3.3); nine appear in the data. Each resolves to a service carrier
by §3.4's table.

| Family | Service | Carriers it sits on here | Rows |
|---|---|---|---:|
| `MOT` | Motive power: shaft work from motors, fans, pumps, compressors, conveyors | `motive_power` | 243 |
| `REF` | Refrigeration and chilling | `cooling_0_15` 68, `cooling_lt0` 3, `cooling_gt15` 1 | 72 |
| `OTH` | A service none of the others names. Electricity-only end uses (lighting, ICT, small power, instruments, welding) go on `electric_service` | `electric_service` 64, `motive_power` 4 | 68 |
| `SPC` | Space heating | `heat_lt60` 34, `heat_60_100` 14 | 48 |
| `HTH` | High-temperature heat: kilns, furnaces | `heat_gt1000` 18, `heat_400_1000` 9 | 27 |
| `LTH` | Low-temperature heat: hot water, washing, cleaning in place | `heat_60_100` 21, `heat_100_150` 2, `heat_lt60` 1 | 24 |
| `STM` | Steam | `heat_100_150` 19, `heat_150_400` 3 | 22 |
| `DRY` | Drying | `heat_150_400` 9, `heat_60_100` 6, `heat_100_150` 4, `heat_lt60` 1 | 20 |
| `PHEAT` | Process heating. §3.4 does not yet name its carrier; the data treats it as a heat family (note 20) | `heat_150_400` 8, `heat_400_1000` 4, `heat_100_150` 2 | 14 |
| `NEUOTH` | Non-energy use: fuel used as feedstock. Presents no duty | none, and none allowed | 0 |
| `HRS` | Hot rolling, a chemistry node keyed per process. Presents no duty | none, and none allowed | 0 |

`EN` (hydrogen production) is **not** a duty family. It labels units only, in `unit.csv`.

The heat bands are `heat_lt60` (1, below 60 °C), `heat_60_100` (2), `heat_100_150` (3),
`heat_150_400` (4), `heat_400_1000` (5) and `heat_gt1000` (6, above 1000 °C); the cooling bands
are `cooling_lt0` (1), `cooling_0_15` (2) and `cooling_gt15` (3).
[README_spec_tables.md](README_spec_tables.md) explains where the lines fall.

## Rules the data must follow

- **Shares sum to one per process.** For each `(carb3_activity, process_set_id, process_id)`,
  `duty_share` sums to 1.00 ± 0.015.
- **Every heat or cooling row has a grade, and it is the carrier's own.** See `grade_rank` above.
- **A duty is a service, never a fuel.** No row may sit on a `primary` or `emission` carrier,
  and each family sits on its own family's carrier (V34, duties are services at a grade).
- **Two duties on one process must be one operation.** A second duty is allowed only where
  both come from the same driver: steam and drive power per tonne of paper, say. Their split
  must come from a source that measures that operation. **It must not be reverse-engineered
  from the process's fuel split in `activity_process_energy_share.csv`**: that would make the
  duty structure copy the activity-average fuel mix at every premise.
- **Two technologies serving one duty are still one duty.** Oxy-fuel and plasma both cut
  steel; the choice between them is a unit choice. Filing the electric variant under `MOT`
  because it runs on electricity leaves the heat duty undersized and the motive duty
  overstated, and nothing fails.
- **A once-through stream is split at the band edges it crosses.** The dairy spray dryer heats
  outside air from 10.3 °C to 200 °C, so it is four rows, one per band, each sharing the duty
  in proportion to its temperature rise (§3.4).

## What is in it

538 rows, covering all 375 `(activity, set, process)` keys of the register across 55
activities. 301 processes carry one duty and 74 carry several.

| | Count |
|---|---|
| `evidence_tier` | `fallback` 246, `published_sec` 205, `engineering` 87, `measured` 0 |
| `confidence` | medium 282, low 252, high 4 |
| `process_set_id` | `default` 507, `bf_bof` 12, `eaf` 11, `grain_distillery` 8 |

No row sits on a product carrier such as `cement` or `clinker`: a mass duty comes from the
premise's `premise_throughput` instead (see below).

### Two examples

**`Cement Works`**, 11 rows. Every process is one `MOT` row at 1.00 except two:

| `process_id` | `duty_family` | `carrier_id` | `grade_rank` | `duty_share` |
|---|---|---|---|---|
| `kiln_pyroprocessing` | `HTH` | `heat_gt1000` | 6 | 1.00000 |
| `site_services` | `OTH` | `electric_service` | | 0.859879 |
| `site_services` | `MOT` | `motive_power` | | 0.078629 |
| `site_services` | `REF` | `cooling_0_15` | 2 | 0.061492 |

The `site_services` split is lighting, ICT and small power, then fans, then chilled water, from
the industrial-sector electricity breakdown in [BEES2016] (note 20 item 72). The kiln's `HTH`
row classifies its heat need; under D16 it yields no duty (see below).

**`Food Processing Centre`**, the dairy of the second worked example:

| `process_id` | `duty_family` | `carrier_id` | `grade_rank` | `duty_share` |
|---|---|---|---|---|
| `boiler_steam_hot_water` | `LTH` | `heat_60_100` | 2 | 0.46180 |
| `boiler_steam_hot_water` | `STM` | `heat_100_150` | 3 | 0.53820 |
| `direct_heating` | `DRY` | `heat_lt60` | 1 | 0.261993 |
| `direct_heating` | `DRY` | `heat_60_100` | 2 | 0.210859 |
| `direct_heating` | `DRY` | `heat_100_150` | 3 | 0.263574 |
| `direct_heating` | `DRY` | `heat_150_400` | 4 | 0.263574 |
| `refrigeration` | `REF` | `cooling_0_15` | 2 | 1.00000 |
| `site_services` | `SPC` | `heat_lt60` | 1 | 0.54900 |

The spray dryer's four shares are (60 − 10.3), (100 − 60), (150 − 100) and (200 − 150) over the
189.7 °C rise. `site_services` carries three further electricity rows like cement's, scaled to
its 0.451 electricity share, and `machinery_motors` and `compressed_air` are one `MOT` row
each, 13 rows in all.

## How it is used

### In the specification

A2 (duties and candidate units) expands it into each premise's `process_duty` rows (§3.9): one
duty per row, on the row's carrier and grade, sized by the process's energy times
`duty_share`. It is the activity-level default, and per-premise evidence overrides it where
there is any (D10, tiered site intelligence).

### In the carb3 slice

`carb3` reads it from the reference root (the full table, or the 24-row subset in
[`carb3/data/reference_mvp/`](../../../carb3/data/reference_mvp/README.md) for the two MVP
activities). Three places use it, all in `carb3/src/carb3/sets.py`:

1. **Creating the duties** (`derive_duties`). For each process valid at the premise's base
   year, every profile row becomes one duty, keyed `(premise, process, carrier)`, with
   quantity `known_activity × duty_share`, flat across the periods. The run stops with an
   error if a process has no profile row, if a heat or cooling row has no grade, or if two
   rows give the same duty key.
2. **Rows that yield no duty.** Under D16 (an internal product is a carrier, not a duty), a
   process whose units make only a product (the kiln makes `clinker`) yields no duty from its
   profile row; the carrier balance fixes its output. An exportable product (`cement`) gets
   its duty from the premise's `premise_throughput` row, which is the mass duty under D5
   (mass-denominated activities). A process with a blank `known_activity` yields no duty and
   is named on the run report's *no duty derived* line.
3. **Choosing units** (`eligible_units`, `_is_drying_duty`). `unit_eligibility.csv` is keyed by
   process, with no carrier or grade, so the duty's carrier and grade from this table are what
   C10 (the grade cascade) tests each unit's `grade_out` against. The `DRY` family is also
   read back from here, because a drying duty may be served only by a `DRY` unit (§3.5.1):
   without that, any heat unit at the right grade would qualify.

### Outside the model

| Reader | What it does with the table |
|---|---|
| `docs/notes/examples/validate_carb3_data.py` (`make data-check`) | Blocking: keys resolve to the register, shares sum to 1 per process, every register key is covered, grades agree with the carrier, no `NEUOTH`, `HRS` or `EN` row, each family on its own carrier, no duty on a fuel. Advisory: duty rows no eligible unit can serve (2 of 538 today, both `HTH` at grade 6) |
| `build/rebuild_eligibility_join.py` | Rebuilds the family rows of `unit_eligibility.csv` from this table, the units and the carriers |
| `build/build_default_unit.py` | Builds `activity_default_unit.csv`, which is keyed on `duty_family` and points back here |
| `carb3/data/build_reference_mvp.py` | Copies the two MVP activities' 24 rows into `carb3/data/reference_mvp/` |

## Before you quote a number

- **`duty_share` is a share of energy, and the slice multiplies it by useful output.** The
  spec defines it as the process's *energy*; `derive_duties` applies it to `known_activity`,
  which is output. The two agree when every duty on the process is served at the same
  efficiency. They do not on the dairy boiler, where hot water and steam differ. A related
  question is open in the spec: §3.10 sizes a duty from `known_activity`, while A2 sizes it
  from shares of the premise's metered energy, and the two are not reconciled.
- **Nearly half the rows are `fallback`.** 246 of 538, and no row is `measured`. Read
  `provenance` before relying on a share.
- **A single row at 1.00 is unexamined, not confirmed simple.** A process with two duties on
  the same fuel (an 85 °C steriliser and a 45 °C washdown on one gas supply) looks exactly
  like a one-duty process. Five are known (note 20 item 1b); nothing can find the rest
  mechanically.
- **`PHEAT` has no carrier in §3.4's table yet.** The data puts it on graded heat, which is
  the obvious reading, but the spec does not say so (note 20).

## After editing the table

The eligibility rows and the MVP subset are derived from it, so regenerate both:

```
python3 docs/notes/data/build/rebuild_eligibility_join.py
python3 carb3/data/build_reference_mvp.py
make data-check
```
