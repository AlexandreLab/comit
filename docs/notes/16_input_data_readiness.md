# Input Data Readiness — what exists, what is specified, and what is neither

An audit of every input the CaRB3 per-site model needs, done before committing to the
next stage of build. The question it answers is narrow and practical: **for each input,
does data exist, does a schema exist, and who supplies it?**

It was prompted by a scoping question — *can we define a "default" database of archetypes
per CaRB3 activity, covering the default energy split by process and the default on-site
generation associated with each process?* Two thirds of that turned out to be missing, and
the missing part is not where the existing plan was looking.

Companion documents: [01](01_input_data_overview.md) tours the COMIT workbook,
[04](04_site_energy_estimation.md) explains how site energy is currently back-derived, and
[15](15_carb3_process_comparison.md) compares the two process taxonomies. This note is the
readiness view across all of them.

---

## The three layers, and why the answer differs at each

"Do we understand the input data" has three different answers depending on which layer is
meant, and conflating them is what makes the position look better or worse than it is.

| Layer | What it is | State |
|---|---|---|
| **Taxonomy** | What an activity's processes *are*, and how energy splits across them | **Strong.** Real, cited, validated green by `make data-check` |
| **Contract** | What fields a per-site model would read | **Strong.** v1 §3 defines 18 entities; v2 §3 defines 9 more |
| **Per-site data** | What any actual premise does | **Essentially none.** Upstream, assumed, not built |

The third layer is a deliberate scope decision, not an oversight: a **CaRB3 building-stock
model** supplies activity, energy by vector and throughput per premise, and building that
is explicitly out of scope for the COMIT-side work. It is the assumption that removes
COMIT's hardest blocker — site sizing otherwise needs CO₂ point-source emissions that most
premises do not have. It is also load-bearing for everything else, so it is worth stating
plainly rather than leaving implicit.

---

## Readiness by input

`spec` = a schema exists. `data` = populated data exists in this repo or the workbook.

| Input | Schema | Data | Source | Notes |
|---|---|---|---|---|
| Premise identity, activity, location | v1 §3.1 | ✗ | CaRB3 stock model | Assumed upstream, not built |
| Premise energy by carrier | v1 §3.1.1 | ✗ | CaRB3 stock model | Today COMIT back-derives from emissions share ([04](04_site_energy_estimation.md)) |
| Premise physical throughput | v1 §3.1.2 | ✗ | CaRB3 stock model | Agreed 2026-08-21 to be added upstream |
| Premise connection — import/export/voltage | v1 §3.1.3, v2 §3.8 | ✗ | DNO agreements, supplier records | v1 collects but **does not read**; v2 C11 reads it |
| Available roof/land area | v2 §3.8 | ✗ | GIS footprint + usable fraction | Group D1. Without it **C12 is unbounded and the LP builds infinite PV** |
| Operating profile / load factor | v1 §3.12 | ✗ | HH metering, schedules | Needed to bridge PJ/yr → MW for any connection constraint |
| **Activity → processes** | v1 §3.2 | **✓** | Hand research, cited | 376 rows, **55/55** activities, 302 mandatory + 74 optional |
| **Process energy split by vector** | v1 §3.3 | **✓** | Hand research, cited | 490 rows, evidence-tiered, 137 share-sum groups all validate |
| **Process → duty family** | implied by v2 §3.2 | ✗ | Derivable from COMIT, partly | **Gap.** See below |
| **Process → heat grade (°C)** | v2 §3.1, §3.7 | ✗ | BREF, sector literature | **Gap.** See below |
| **Default on-site generation / storage** | *nowhere* | ✗ | DUKES Table 7, CHPQA | **Gap.** No schema and no data |
| Unit library (~95 units) | v2 §3.2 | ✗ | Collapse of 397 COMIT technologies | T8/T9 own it |
| Unit eligibility | v2 §3.4 | ✗ | Derived from duty families | Blocked on the duty-family gap |
| Archetype definitions | *nowhere* | ✗ | — | `archetype_id` has **no defining entity**; Group D4 |
| Archetype coefficients ψ/β/χ/ε | v2 §3.6 | ✗ | Tier A offline dispatch | Group D4. ε non-nullable on flexible-load hybrids |
| Decarbonisation options | — | **✓** | Hand research, 270 refs | 134 options, but **no option→unit join** (T9) |
| Emissions factors per technology | v1 §3.5 | **✓** | Workbook + classification | 397 technologies classified into 5 emission classes |

Six inputs have data. Everything else is a schema waiting for a supplier, or neither.

---

## The chain that is broken

v2 decides what plant a site may build by walking from a process to its duty to the units
eligible to serve it. Only the first link exists.

```
   process   ──►   duty (family + grade)   ──►   eligible units   ──►   default installed
     ✓                     ✗                          ✗                       ✗
  376 rows          no duty family              unit_eligibility        no entity at all
  55/55 acts        no temperature              has no data
```

This matters more than its position in the plan suggests, because three separate pieces of
work are all waiting behind the same missing link:

- **T16** is specified to demonstrate *"a 120 °C duty with boiler / CHP / heat pump /
  electric competing under C10"*. Neither the 120 °C nor the CHP default exists, so T16
  cannot be written against real data today.
- **`unit_eligibility`** is keyed `(unit_id, carb3_activity, process_id)`. Hand-authoring it
  is 376 processes × ~95 units of decisions. Duty families collapse that to a derivation
  plus refinement.
- **T13**'s A4 carrier-mix rule chooses between units serving a duty. Without duty families
  there is nothing for a unit to be eligible *for*.

---

## Finding 1 — temperatures exist, on the wrong side of the problem

There is **no temperature or grade column in any of the ten CaRB3 reference CSVs.**
Temperatures do appear, but only as free text, and overwhelmingly attached to
decarbonisation *options* rather than to processes:

| File | Column | Rows with a temperature |
|---|---|---|
| `decarbonisation_options_library.csv` | `duty` | 28 |
| `process_decarbonisation_options.csv` | `notes` | 45 |
| `decarbonisation_options_library.csv` | `trl_basis`, `option_name`, `key_constraints`, `provenance` | 24 |
| **`activity_process_register.csv`** | `provenance`, `equipment_examples` | **3 — all incidental** |

So the data says *"high-temperature heat pumps serve 100–150 C"* and *"digester and
pasteuriser heat at 40–70 C"*. It does not say what temperature **`evaporation` at a Beet
Sugar Factory requires**. The supply side is described; the demand side is not.

That is the wrong way round. The demand-side temperature is what decides which units may
serve a duty, and it is the input to `process_duty.grade_rank`.

**The schema for it does already exist, in v2 and only in v2.** `carrier.is_gradeable`,
`grade_rank` and `grade_label` (°C, e.g. `150-400C`) model each grade as its own carrier
row, so C8 balances grades independently and C10 cascades high to low. v1 has no
temperature concept at all. The shape is right; nothing populates it.

---

## Finding 2 — duty families are half-derivable, and the crosswalk stops one level short

Better news than expected. **COMIT's 94 `process_commodity` codes already encode the duty
family as a suffix**, which is what the data-migration plan means by "derive the duty
families from the 94 process codes" (A5):

| Suffix | Sectors carrying it | | Suffix | Sectors carrying it |
|---|---|---|---|---|
| `LTH` low-temp heat | 11 | | `DRY` drying | 6 |
| `OTH` other | 11 | | `STM` steam | 6 |
| `MOT` motive power | 10 | | `REF` refrigeration | 2 |
| `SPC` space heating | 8 | | `HRS` / `NEUOTH` | 1 each |
| `HTH` high-temp heat | 7 | | chemistry nodes (`CLK`, `LST`, `PIR`, `SNT`, …) | 14 |

So `IFDLTH` is *Industry · Food & Drink · Low-Temperature Heat*, and the duty family falls
out of the code.

**But the crosswalk joins at the wrong level.** `carb3_comit_crosswalk.csv` has **55 rows —
one per CaRB3 activity** — mapping activity → COMIT *sector*, with a coverage flag and a
free-text analogue. It does not map CaRB3's 376 *processes* to COMIT's 94 *process codes*.
That join is the missing artefact.

And a straight inheritance would not cover the register anyway. Register rows, grouped by
how well their activity maps to COMIT:

| Crosswalk coverage | Activities | Register rows | Can inherit a duty family from COMIT? |
|---|---|---|---|
| `direct` | 31 | 228 | Likely, with review |
| `catch-all` / `partial` / `generic` | 8 | 57 | Partly |
| `absent` / `gap` / `weak` / `ambiguous` | 16 | **91** | **No — needs first-principles classification** |

So roughly 60% of the classification can be seeded from COMIT and ~24% cannot be seeded at
all. That is a tractable piece of work, but it is work, not a script.

---

## Finding 3 — default on-site generation has neither schema nor data

A column scan across all ten reference files found **no column** matching generation,
capacity, storage, onsite, import, export or self-consumption.

Three things come close without being it:

- `equipment_examples` names devices — *"two-post lifts; air compressor; MOT brake tester"* —
  but as illustration, with no capacity, share or output.
- Exactly **one** activity has a generation process: `Mineral Production - Gas /
  power_generation`, at 25% of the activity's gas.
- **CHP appears only inside process *names*.** `Chemical Works / utilities_steam` is
  described as *"Steam system and utilities (boiler/CHP losses…)"*. The energy lands on the
  steam duty, but nothing records whether a boiler or a CHP produces it, and **no
  electricity co-product exists anywhere.**

The sharp version: today a Chemical Works with a 20 MW CHP and one without are the same
row. That is not a rounding difference. A site with existing CHP self-supplies electricity,
its import capacity understates its effective load, and electrifying its heat strands the
CHP — a materially different decarbonisation problem.

v1's only on-site generation fields (`onsite_generation_capacity`, `onsite_generation_type`)
sit on `premise_connection`, i.e. optional *per-premise* site intelligence — and §5.6 states
that nothing reads them. There is no activity-level equivalent in either spec.

**Why it was never there.** Both specs infer the supply side rather than asserting it: v1's
A4 *back-solves* existing technology from metered energy. That is coherent while every
technology is a fuel variant of a demand device. It stops being coherent once generation,
storage and CHP exist, because a CHP is not inferable from a heat duty — it is a fact about
the site.

---

## Finding 4 — `archetype` is already taken, and its defining entity is missing

v2 uses "archetype" for **`activity × load shape × schedule × size`**, ~200–400 of them, run
offline at hourly resolution (stage S0, Tier A) to emit ψ/β/χ/ε for Tier B. That is a
*dispatch-behaviour* archetype, not a "typical site of this activity" archetype.

Underneath it is a real hole: `archetype_coefficient` is keyed `(archetype_id, unit_id)`,
but **no entity anywhere defines what an `archetype_id` is** — nothing lists the archetypes,
their activity, load shape, schedule or size band. Group D4 confirms it as data the model
does not have.

Anyone adding a site-composition archetype must therefore pick a distinct name. This repo
has been bitten by label collisions three times; the house pattern is rename plus a
disambiguation note.

---

## What this implies for sequencing

The gaps are ordered by dependency, not by size. You cannot assign units to a duty until
the duty exists.

1. **Duty family per process** — classify 376 register rows into the 12 service families and
   14 chemistry nodes. ~60% seedable from COMIT via a new process-level crosswalk; ~91 rows
   need first-principles work.
2. **Grade / temperature per process** — the demand-side temperature, which nothing holds
   today. Unblocks `process_duty.grade_rank`, C10's cascade, and T16.
3. **Default installed units per (activity, process, duty)** — the genuinely new data.
   Seedable from **DUKES Table 7 and the CHPQA register**, which give existing industrial
   CHP capacity and output by sector. Unlike Group D1's roof-area problem, this has a real
   published source.

Steps 1 and 2 are a classification pass over a table that already exists and is already
validated. Step 3 is new data collection but against a public source.

**Also worth noting:** in v2 the vector split stops being an input. v1 asks which *fuel*
serves a process; v2's carrier balance *decides* that, so supplying it would over-determine
the problem. `activity_process_energy_profile` therefore becomes a **parity target for V1b**
rather than an input — which is a use, not a retirement, and the 490 rows keep their value.

---

## Caveats

- `docs/notes/data/` is derived reference data. **COMIT never reads it.**
- The workbook's `commodities` and `Fuel_emissions` sheets are labelled *dummy figures*. The
  classification and method are real; the absolute intensities are not.
- The counts here were computed against the data on 2026-09-02 and are checked by
  `make data-check`. Recompute rather than quoting them forward.
- 17 register processes still have no energy-profile row (validator advisory, unchanged
  since T1's baseline).
