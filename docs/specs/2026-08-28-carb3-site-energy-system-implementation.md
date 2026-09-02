# CaRB3 Site Energy System — Implementation Specification (v2)

**Status:** Draft — §1, §2, §3 and §5 written. §4 is a stub owned by T13; §6–§13 are not yet written
**Self-contained:** §3 inlines every entity carried over from v1, so nothing here requires opening the archived v1 spec
**Date:** 2026-09-01
**Scope:** Great Britain (England, Wales, Scotland) · CaRB3 **Factory class** only (55 activities)
**Plan:** [overview](2026-08-28-carb3-site-energy-system-overview.md) ·
[architecture](2026-08-28-carb3-site-energy-system-architecture.md) ·
[spec changes](2026-08-28-carb3-site-energy-system-spec-changes.md) ·
[data migration](2026-08-28-carb3-site-energy-system-data-migration.md) ·
[delivery](2026-08-28-carb3-site-energy-system-delivery.md)
**v1, frozen:** [archive/2026-08-19-carb3-site-decarbonisation-implementation.md](archive/2026-08-19-carb3-site-decarbonisation-implementation.md) — retained as the COMIT-parity baseline that V1 validates against
**Design decisions:** [vision §6](archive/2026-08-19-carb3-site-decarbonisation-vision.md) defines `D1`–`D11`

> **Incomplete by design.** This document is being written section by section against the
> delivery plan. §4 (algorithms) is T13. §6–§13 are T5, T6, T7, T14 and T15. Do not treat a
> missing section as a decision that it is unnecessary.

---

## 1. Scope, inputs, conventions, and how to read this

*Section last updated: 2026-09-01*

### 1.1 What this document is

A build specification: one record per premise in, a least-cost decarbonisation pathway out,
solved independently per premise. It states **what to build**, not how to build it in a
particular language.

It supersedes v1 **for architecture only**. v1 remains authoritative as the COMIT-parity
baseline, and the chain of custody runs in two hops: v1 reproduces coupled-off COMIT (V1,
unchanged), and v2 reproduces v1 in the carrier-equivalent configuration (V1b, T5). Neither
hop may be skipped.

### 1.2 What changed from v1, in one table

| | v1 | v2 |
|---|---|---|
| The thing that converts energy | `technology`, one row per *(process × equipment × fuel)*, 397 rows | `unit`, ~95 rows. Fuel moves out of the identity and into carrier bindings |
| What a process asks for | A quantity of its own output commodity | A **carrier at a grade** — `heat@60-150C`, not "gas" |
| How supply meets demand | Technologies mapped to processes by table | A **carrier balance at every node** (C8), plus a one-way heat-grade cascade (C10) |
| Electricity | A priced fuel with unconstrained supply | A balanced carrier with import, export and a connection limit |
| Onsite generation | Inexpressible. C1 has no place for a technology serving no process | An ordinary unit. PV, CHP, electrolysers and AD need no special class |
| Storage | Worth exactly zero — it nets to a round-trip loss inside one annual period | **Hybrid units** at a fixed sizing ratio (PD3), with coefficients from an offline archetype layer |
| Waste heat | Nowhere to go | A low-grade supply, which is exactly what a heat pump needs |
| Temporal structure | Annual only | **Two tiers.** Offline hourly dispatch produces ψ, β, χ, ε; the per-premise problem stays annual and a pure LP |

**What did not change, and is carried over unaltered:** D2 per-premise decomposition; D7
exogenous infrastructure; D11 plant vintage, ageing and the stranding charge; the
sign convention on input/output coefficients; the two-denominator rule (D5); the D10
three-tier evidence pattern; and the objective's discounting and annuitisation.

### 1.3 Language-agnostic conventions

1. **Entities, not tables.** §3 describes entities with fields and keys. A dataframe, a
   database table and a set of typed records are all valid.
2. **Numbered pseudocode** for algorithms, never source in any language.
3. **§5 is authoritative.** Where prose and the mathematics disagree, the mathematics wins.
4. **`R/file.R:line` citations describe the current model**, meaning *"COMIT does X here;
   verify against it"*. They are never an instruction to port that function.
5. **Every `##` section carries a `*Section last updated:*` line.** It is load-bearing for
   the interface-doc generator and must round-trip: edit the section, bump the date,
   regenerate.

### 1.4 Notation

Field tables have six columns: field · type · unit · required · key · validation. A foreign
key is written `→ \`entity\``. Abstract types (`string`, `real`, `integer`, `boolean`,
`enum{...}`) carry no language commitment.

Label families in this document, and where each is defined:

| Family | Meaning | Defined in |
|---|---|---|
| `C1`–`C12` | Constraints | §5.5 |
| `A1`–`A9` | Algorithms | §4 (T13) |
| `S0`–`S9` | Pipeline stages | §2.1. **`S0` is new** — the offline archetype layer. v1's family started at `S1` |
| `V1`–`V23` | Validation tests | §10 (T5, T14, T15) |
| `G1`–`G4` | Scale gates | §9 (T7, T15) |
| `D1`–`D11` | Design decisions | **the vision doc**, not here |
| `PD1`–`PD3` | Plan decisions | the v2 overview doc |

### 1.5 Glossary

| Term | Meaning |
|---|---|
| **Carrier** | Anything that flows and balances: gas, electricity, hydrogen, biomethane, CO₂, and heat at a grade |
| **Grade** | A temperature band on a heat carrier. Ordered, and the cascade runs one way only |
| **Duty** | What a process requires: a quantity of a carrier at a grade. The demand side |
| **Unit** | What converts between carriers. The supply side. Boiler, heat pump, kiln, CHP, PV, battery |
| **Hybrid unit** | A co-located package at a **fixed sizing ratio**, e.g. `pv_battery_2h`. One unit, one capex, one coefficient set (PD3) |
| **Primary carrier** | One that enters the site or is extracted: gas, coal, biomass, grid electricity. Emissions attach here |
| **Intermediate carrier** | One produced and consumed on site: heat, steam, recovered heat. Emissions never attach here |
| **Tier A / Tier B** | The offline archetype dispatch layer, and the per-premise annual investment LP |

**Not a virtual power plant.** A VPP aggregates assets across multiple sites, which is the
inter-premise coupling D2 forbids. "Hybrid unit" means co-located, one premise.

### 1.6 Design decisions assumed

D1–D11 are defined in the vision doc. Four have the widest reach here:

- **D2 — per-site independent solves.** No constraint may couple two premises. Anything
  needing cross-site information becomes a scenario input or a post-hoc comparison. This is
  structural; nothing in this document can undo it.
- **D5 — hybrid denominators.** Energy (PJ) by default, mass (Mt) for chemistry. This is
  also the line the unit spine splits on (§3.2).
- **D10 — tiered site intelligence.** Known site detail replaces activity defaults outright,
  and every output row carries its evidence tier.
- **D11 — plant has an age.** Carried over unchanged, now attaching to units.

---

## 2. System overview

*Section last updated: 2026-09-01*

### 2.1 Components

| # | Component | Responsibility |
|---|---|---|
| S0 | **Archetype dispatch (Tier A)** | **New.** Offline, hourly, once per archetype per hybrid sizing ratio. Emits ψ, β, χ, ε |
| S1 | Ingestion and validation | Accept premise records, validate, reject with reasons |
| S2 | Process and unit expansion | Premise → its duties, and the candidate unit set via `unit_eligibility` |
| S3 | Carrier allocation | Split metered energy onto carriers |
| S4 | Baseline capacity, mix and vintage | Back-solve implied unit capacity, the carrier mix (T13), and plant age |
| S5 | Scenario application | Attach prices, carbon price, infrastructure availability, archetype coefficients |
| S6 | Problem builder | Construct the per-premise optimisation (§5) |
| S7 | Solver driver | Solve, extract, handle infeasibility |
| S8 | Output assembly | Produce the per-premise pathway tables |
| S9 | Aggregation and comparison | Roll up to GB; compare against ECUK/GHGI |

**S0 runs once for the whole stock**, not per premise. S1–S8 run per premise and are
independent across premises. S9 runs once over all results.

### 2.2 Data flow

```
  S0  ARCHETYPE DISPATCH (offline, hourly, once per archetype × sizing ratio)
      process_load_shape + premise_operating_profile + premise_weekly_profile
                        │
                        └──►  archetype_coefficient  (ψ, β, χ, ε)
                                        │
  ────────────────────────────────────  │  ──────────────────────────────────
                                        │
  premise_record ──S1──► validated      │
   + premise_energy                     │
   + premise_throughput                 │
   + premise_connection                 │
          │                             │
          ├─S2─► duties (carrier@grade) + candidate units   [unit_eligibility]
          ├─S3─► energy onto carriers
          ├─S4─► implied capacity + carrier mix + vintage
          └─S5─► prices, availability, coefficients ◄───────┘
                        │
                        ▼
                  S6 build ──► S7 solve ──► S8 site_pathway ──► S9 GB aggregate
```

### 2.3 Boundaries

**In scope:** a validated premise record to a per-premise pathway, plus GB aggregation, plus
the offline archetype layer that makes storage representable.

**Out of scope:** deriving the premise's baseline energy (upstream, D4); deciding
infrastructure build-out (exogenous, D7); enforcing a national emissions budget (reported
only); Northern Ireland (D8); and **any temporal-correlation compliance claim** — RFNBO and
LCHS rules require hourly matching, which an annual model structurally cannot express. State
it, do not model it.

---

## 3. Data model

*Section last updated: 2026-09-02*

**Twenty-two entities, and this document is now self-contained** — nothing here sends you
to v1. Entities v1 defined and v2 keeps unchanged are inlined below rather than cited, which
is what the previous draft's §3.12 said had to happen before v2 could stand alone.

**Section numbers are aligned with v1 on purpose.** Where v1 and v2 both define an entity it
sits at the same number in both — §3.11 is `premise_measured_emissions` in each. Where v2
replaces a v1 entity, the replacement takes the number the original had: v2's `carrier` is
§3.4 because v1's `commodity` was, and `unit` is §3.5 because `technology` was. So a §3.x
reference means the same thing whichever document you came from, and the archived v1 spec
can be read alongside without translation.

| | Supplied by | Entities |
|---|---|---|
| §3.1–§3.1.3 | the CaRB3 stock model | `premise_record`, `premise_energy`, `premise_throughput`, `premise_connection` |
| §3.2–§3.6 | the modelling team | `activity_process_register`, `activity_process_duty_profile`, `carrier`, `unit`, `unit_input_output` |
| §3.7–§3.8 | scenario definition | `infrastructure_scenario`, `scenario_parameters` |
| §3.9 | derived at run time (A2) | `process_duty` |
| §3.10–§3.15 | optional per-premise intelligence (D10) | `premise_process_detail` and companions |
| §3.16–§3.17 | defaults and the offline layer | `activity_default_unit`, `archetype_coefficient` |

### 3.1 `premise_record` — the premise itself

*v1 §3.1, unchanged.*

The interface between the CaRB3 stock model and this model is three **required**
entities — this one, plus `premise_energy` (§3.1.1) and `premise_throughput` (§3.1.2) —
and one optional fourth, `premise_connection` (§3.1.3), which **v2 reads for the first time** — C11 bounds import against it, C12 bounds onsite generation against its `available_area`.
That is the same set §3's preamble calls the first four. One row per premise
here; the other two are long tables keyed on `premise_id`. Stated in requirement terms,
with rationale, in **§1.6**; these tables are normative for validation.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK | Unique, stable across runs |
| `carb3_activity` | string | — | yes | → `activity_process_register` | Must match one of the **55 CaRB3 Factory-class activities** (D1). Any other class is rejected with reason `out_of_scope_activity`; an unrecognised string with `unknown_activity` (A1) |
| `latitude` | real | degrees | yes | — | Within GB bounding box |
| `longitude` | real | degrees | yes | — | Within GB bounding box |
| `nation` | enum{England, Wales, Scotland} | — | yes | — | NI rejected with reason `out_of_scope_nation` |
| `floorspace` | real | m² | no | — | > 0 if present |
| `process_set_id` | string | — | no | → `activity_process_register` | Selects a named non-default process set (§3.2). Absent ⇒ the activity's default set |
| `construction_year` | integer | year | no | — | **D11.** ≤ `data_year` if present. When the premise was built. Bounds plant age from above (§3.15, §5.3.1) |
| `construction_year_band` | string | — | no | — | **D11.** Where only a band is held, e.g. `1945-1964`. Used only if `construction_year` is absent, and read as its **earliest** year |
| `last_refurbishment_year` | integer | year | no | — | **Future use.** ≥ `construction_year`, ≤ `data_year` if present. Collected, not read |
| `data_year` | integer | year | yes | — | Provenance |
| `source` | string | — | yes | — | Provenance |

**On the age band (D11).** CaRB3-style stock data usually holds building age as a band
rather than a year, so both forms are accepted and the year wins where both are present.
A band is read as its **earliest** year, which is the conservative reading: it admits the
widest range of plant ages and therefore stays closest to the default tier. Reading it as
the midpoint or the latest year would make plant look younger than the evidence supports,
and erring in that direction is the more dangerous mistake.

Energy and throughput are **not** columns here. Both are one-to-many — a premise consumes
several carriers and may make several products — so both are long tables keyed on
`premise_id`, matching the shape already used by `premise_measured_emissions` (§3.11) and
`premise_weekly_profile` (§3.14).

#### 3.1.1 `premise_energy` — consumption by carrier

*v1 §3.1.1, `commodity_id` renamed `carrier_id`.*

One row per premise per carrier. Replaces the fixed `energy_electricity` … `energy_other`
columns: a new carrier is a new row, not a schema change, and the `energy_other` /
`energy_other_carrier` pair disappears because every carrier now names itself.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `carrier_id` | string | — | yes | PK part | → `carrier`. The carrier as metered |
| `connection_id` | string | — | no | PK part → `premise_connection` | **Optional.** The metered connection this quantity came through (§3.1.3). Absent ⇒ the premise's default connection |
| `vector` | enum{electricity, gas, oil, coal, biomass, other} | — | yes | — | The grouping used to join `activity_process_duty_profile` (§3.3). Must be consistent with the carrier's `carrier_kind` (§3.4) |
| `quantity` | real | PJ/yr | yes | — | ≥ 0 |
| `data_status` | enum{measured, estimated, modelled, not_consumed} | — | yes | — | See the absence rule below |
| `data_year` | integer | year | no | — | Defaults to `premise_record.data_year`; set only where a carrier is metered on a different vintage |
| `source` | string | — | yes | — | Provenance for this carrier specifically |

**Rule (at least one positive).** A premise must have at least one row with
`quantity > 0`, or it is rejected with reason `no_energy`.

**Rule (absence is not zero — the one trap in this format).** A wide table with required
columns forces every carrier to be stated, so a zero is unambiguous. A long table loses
that: a missing row could mean *"this site burns no oil"* or *"nobody checked whether it
burns oil"*, and those two lead to very different conclusions about a site's
decarbonisation options. So:

- A carrier **known not to be consumed** is stated explicitly: `quantity = 0` with
  `data_status = not_consumed`.
- A carrier that was **not assessed** is simply absent, and any result for that premise
  is reported as having incomplete carrier coverage (§8, T14).

The stock model should aim to state all five main vectors for every premise, whether by a
positive quantity or an explicit zero. Absence is a last resort, not the default.

**Rule (one row per carrier per connection).** `(premise_id, carrier_id, connection_id)`
is unique. Two meters on the *same* connection are one row — meter-level detail below the
connection belongs upstream. Two meters on *different* connections are two rows, because
the connection is a modelled object (§3.1.3) and the difference is load-bearing.

Sites with a single connection may omit `connection_id` entirely and are unaffected.

#### 3.1.2 `premise_throughput` — physical output by carrier

*v1 §3.1.2, `commodity_id` renamed `carrier_id`.*

One row per premise per product. Long for the same reason, and it lifts a real
limitation: the previous single `throughput_quantity` column could not represent a site
making more than one product, which paper, chemicals and food sites routinely do.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `carrier_id` | string | — | yes | PK part | → `carrier`. Must have `denominator_kind = mass` (D5) |
| `quantity` | real | Mt/yr | yes | — | > 0 |
| `data_status` | enum{measured, estimated, modelled} | — | yes | — | — |
| `source` | string | — | yes | — | Provenance |

**On throughput (agreed 2026-08-21).** Physical throughput is **not** a best-effort
optional input: without it, the mass denominators that D5 requires cannot be populated,
and process emissions — calcination CO₂ and equivalents — lose their physical basis for
precisely the activities where they dominate. The upstream stock model will be extended
to supply it. A premise whose activity carries a mass-denominated process must therefore
have at least one `premise_throughput` row, and A1 rejects it otherwise
(`missing_throughput`). Activities with no mass-denominated process need no rows at all.

#### 3.1.3 `premise_connection`

*v1 §3.1.3 plus `available_area`; **read for the first time** (C11, C12).*

One row per MPAN or MPRN.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part → `premise_record` | — |
| `connection_id` | string | — | yes | PK part | — |
| `carrier_id` | string | — | yes | → `carrier` | Which network this connects to |
| `import_capacity` | real | MW | no | — | ≥ 0 |
| `export_capacity` | real | MW | no | — | ≥ 0 |
| `connection_voltage` | real | kV | no | — | > 0 |
| `available_area` | real | m² | no | — | ≥ 0. Roof plus land available for onsite generation |

**Capacities are never summed across connections.** A site with two supplies has two limits,
and adding them grants headroom the load cannot physically reach. C11 is written per
connection for exactly this reason.

**`available_area` is the single biggest missing input.** Without it C12 is unbounded and
the LP builds infinite PV. Where the stock model cannot supply it, a per-activity usable-area
fraction applied to the GIS footprint is the fallback, and it carries its evidence tier.

### 3.2 `activity_process_register` — activity → processes

*v1 §3.2, unchanged.*

Which processes run at a premise of a given activity. Populated by
[`../notes/data/activity_process_register.csv`](../notes/data/activity_process_register.csv) —
376 rows covering all 55 activities, with provenance per row. That table supersedes
[`carb3_factory_processes.json`](../notes/data/carb3_factory_processes.json), which
remains as the narrower source it was expanded from.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `carb3_activity` | string | — | yes | PK part | — |
| `process_set_id` | string | — | yes | PK part | Names the variant. Every activity has exactly one set with `is_default = true` |
| `set_name` | string | — | yes | — | Human-readable, e.g. `kraft_pulping`, `recycled_fibre` |
| `is_default` | boolean | — | yes | — | Exactly one true per `carb3_activity` |
| `process_id` | string | — | yes | PK part | → `activity_process_register` |
| `process_name` | string | — | yes | — | Human-readable |
| `is_optional` | boolean | — | yes | — | If true, may be absent at a given premise |
| `provenance` | string | — | yes | — | For non-default sets: what intelligence justifies it |

**On process sets.** An activity rarely has one universal process route. Two paper mills
in the same CaRB3 activity may run kraft pulping and recycled-fibre lines that share
almost no unit operations, and where that is known for a specific site it should be used
rather than averaged away. Each activity therefore carries **one default set plus any
number of named alternatives**, and a premise selects one via
`premise_record.process_set_id` (§3.1). Absent that, the default applies. Finer-grained
still, a premise may declare its processes explicitly in `premise_process_detail`
(§3.10), which overrides both.

**Rule.** Every `(carb3_activity, process_set_id, process_id)` triple must resolve to
rows in `activity_process_duty_profile`, directly or by inheritance (§3.3), or the set
cannot be modelled.

**Rule.** `process_set_id` must be valid *for the premise's activity*. A set belonging to
a different activity is rejected on ingest with reason `invalid_process_set`.

### 3.3 `activity_process_duty_profile`

***new** — replaces v1 §3.3 `activity_process_energy_profile`.*

**The default duty of each process, per activity.** The activity-level default that A2
expands into a premise's `process_duty` (§3.7) wherever no site intelligence overrides it.
This is the demand side of the carrier model, and **nothing holds it today** — see
[notes/16](../notes/16_input_data_readiness.md).

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `carb3_activity` | string | — | yes | PK part | → `activity_process_register` |
| `process_set_id` | string | — | yes | PK part | → `activity_process_register`. `default` unless a named route |
| `process_id` | string | — | yes | PK part | → `activity_process_register` |
| `duty_family` | enum{DRY, EN, HRS, HTH, LTH, MOT, NEUOTH, OTH, PHEAT, REF, SPC, STM} | — | yes | PK part | The 12 service families |
| `carrier_id` | string | — | yes | → `carrier` | What the duty is *for* |
| `grade_rank` | integer | — | no | PK part → `carrier` | **Required where `carrier.is_gradeable`.** Non-nullable for heat |
| `duty_share` | real | fraction | yes | — | ∈ [0, 1]. Share of this process's energy that is this duty |
| `share_low` | real | fraction | no | — | ≤ `duty_share` if present |
| `share_high` | real | fraction | no | — | ≥ `duty_share` if present |
| `evidence_tier` | enum{measured, engineering, published_sec, fallback} | — | yes | — | Same ladder as the v1 energy profile |
| `provenance` | string | — | yes | — | Citation |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried to output |

**Rule (shares sum to one).** For each `(carb3_activity, process_set_id, process_id)`,
`duty_share` must sum to 1.00 ± 0.015 — the same tolerance the v1 energy profile is already
validated against, so one check covers both.

**Rule (a heat duty must have a grade).** Where the carrier is gradeable, `grade_rank` is
non-nullable. A heat duty with no grade is invisible to C10's cascade: it can be served by
any grade at all, including one far below what the process needs, and the LP will take the
cheapest. This is the failure the data-migration plan flags as mode #6, and it fails silently.

**Rule (inheritance).** A non-default process set need not restate every row; where a
`(process_id, duty_family, grade_rank)` is absent it inherits the default set's value.
Identical to the v1 energy profile's inheritance rule.

**This replaces the vector split as an input, and does not merely add to it.** v1 asks which
*fuel* serves a process (`activity_process_energy_profile.energy_share` by vector); v2's
carrier balance **decides** that, so supplying it too would over-determine the problem.
The 490-row v1 profile therefore becomes the **parity target for V1b** — the thing v2's
chosen fuel mix is compared against — rather than an input. §3.12 says the same from the
other direction.

### 3.4 `carrier`

***new** — replaces v1 §3.4 `commodity`.*

Anything that flows and balances. Replaces v1's `commodity`.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `carrier_id` | string | — | yes | PK | — |
| `carrier_name` | string | — | yes | — | — |
| `carrier_kind` | enum{primary, intermediate, product, emission} | — | yes | — | Decides emissions attribution (§7) |
| `is_gradeable` | boolean | — | yes | — | True only for heat |
| `grade_rank` | integer | — | no | — | Required if `is_gradeable`. Higher serves lower |
| `grade_label` | string | °C | no | — | Required if `is_gradeable`, e.g. `150-400C` |
| `is_indirect` | boolean | — | yes | — | Emissions counted as indirect. **Config, not a hardcoded list** |
| `emission_factor_source` | string | — | no | — | → `scenario_parameters` series |
| `denominator_kind` | enum{energy, mass} | — | yes | — | D5 |

**Grades are carriers, not an attribute of one.** `heat@60-150C` and `heat@150-400C` are two
`carrier` rows with different `grade_rank`. This is what lets C8 balance them independently
and C10 order them, without a special case in either.

**`carrier_kind` is load-bearing for emissions.** Fuel emissions attach only to units
consuming a `primary` carrier. A unit consuming an `intermediate` adds nothing, because the
fuel was already charged upstream. Getting this wrong double-counts every boiler in the
stock.

### 3.5 `unit`

***new** — replaces v1 §3.5 `technology`.*

What converts between carriers. Replaces v1's `technology`.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `unit_id` | string | — | yes | PK | — |
| `unit_name` | string | — | yes | — | — |
| `unit_class` | enum{converter, generator, storage, hybrid, abatement} | — | yes | — | — |
| `spine` | enum{service, chemistry} | — | yes | — | Service units are family-keyed, chemistry node-keyed |
| `duty_family` | string | — | no | — | Required if `spine` = service |
| `process_id` | string | — | no | → `activity_process_register` | Required if `spine` = chemistry |
| `grade_out` | integer | — | no | → `carrier` | Max grade rank it can produce |
| `grade_in_max` | integer | — | no | → `carrier` | Max grade rank it can consume as a source |
| `capex` | real | £m per capacity unit | yes | — | ≥ 0. **Levelised over components if hybrid** |
| `fixed_opex` | real | £m/yr per capacity unit | yes | — | ≥ 0 |
| `lifetime` | integer | years | yes | — | > 0. One value even for a hybrid |
| `availability_factor` | real | fraction | yes | — | ∈ (0, 1] |
| `capacity_to_activity_factor` | real | — | yes | — | > 0 |
| `emissions_released` | real | fraction | yes | — | ∈ [0, 1]. Fraction **not** captured |
| `min_viable_scale` | real | capacity units | no | — | Screening threshold, applied in A2 — **never a binary** |
| `load_shape_override` | string | — | no | → `process_load_shape` | **By exception only.** The shape belongs to the process (§3.13); a unit overrides it only where the device genuinely changes the draw |
| `is_hybrid` | boolean | — | yes | — | If true, `unit_bill_of_materials` rows must exist |
| `abates_unit_id` | string | — | no | → `unit` | For abatement units: the unit whose output it captures |
| `provenance` | enum{comit_reuse, bref, proxy} | — | yes | — | D6 |
| `confidence` | enum{high, medium, low} | — | yes | — | D6 |

**The spine is split, and the split follows D5.** Energy services (`LTH`, `HTH`, `STM`,
`DRY`, `MOT`, `SPC`, `OTH`, `REF`, and four more) are family-keyed: one `boiler` serves a
dairy and a paper mill alike. Chemistry (`ICMCLK`, `IHVC`, `IISPIR` and eleven more) is
node-keyed, because a cement kiln is not a generic device. Sector specificity lives in
`unit_eligibility`, not in the unit's identity.

**Abatement is a unit, not a retrofit pointer.** v1's `retrofit_to` differenced one
technology's costs against another. Here a CCS train is a unit that consumes a CO₂ carrier
produced by its host and names the host in `abates_unit_id`. It inherits the host's
remaining life under D11 and strands nothing.

#### 3.5.1 `unit_eligibility`

***new**.*

Which units may serve which duty, for which activity, and above what scale. **This is where
sector specificity lives.**

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `unit_id` | string | — | yes | PK part → `unit` | — |
| `carb3_activity` | string | — | yes | PK part | → `activity_process_register` |
| `process_id` | string | — | yes | PK part | → `activity_process_register` |
| `min_duty` | real | PJ/yr or Mt/yr | no | — | Below this the unit is not offered at all |
| `max_share` | real | fraction | no | — | ∈ (0, 1]. Cap on this unit's share of the duty |
| `earliest_year` | integer | year | no | — | Availability |
| `provenance` | enum{comit_reuse, bref, proxy} | — | yes | — | D6 |

**`min_duty` replaces the MILP binary.** COMIT introduces a binary per hydrogen technology
per site when a minimum plant size is set (`R/fct_constraints_hydrogen.R:650`,
`R/fct_decision_variables.R:597`), which at 300k premises is exactly the tractability
problem D7 removed. Here the decision is made **outside the LP**, in A2: a premise below the
threshold never gets the unit in its candidate set. Sites whose optimal size lands below a
credible minimum are **reported**, following the "reported comparison, not constraint"
pattern.

#### 3.5.2 `unit_bill_of_materials`

***new**.*

One row per hybrid unit per component. Required whenever `unit.is_hybrid` is true.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `unit_id` | string | — | yes | PK part → `unit` | Must have `is_hybrid` true |
| `component_id` | string | — | yes | PK part | e.g. `pv`, `battery`, `inverter` |
| `capacity_share` | real | fraction | yes | — | Shares sum to 1 per unit |
| `capex_share` | real | fraction | yes | — | Shares sum to 1 per unit |
| `component_lifetime` | integer | years | yes | — | > 0 |
| `replacements_in_life` | integer | — | yes | — | ≥ 0. How often it is replaced within the unit's life |

**Two jobs.** First, outputs can answer *how much battery does GB industry need* rather than
reporting bundle capacity — §8's `Costs` and `Network` rows decompose through this table.
Second, it makes the levelised capex auditable: PV lasts 30–40 years and a battery 10–15, so
`unit.capex` must already contain the battery replacement. `replacements_in_life` is what
V20 (c) checks that against.

### 3.6 `unit_input_output`

***new** — replaces v1 §3.6 `technology_input_output`.*

Coefficients per unit per carrier, per unit of the unit's output. Carried over from v1's
`technology_input_output` with the key renamed and **the sign convention unchanged**.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `unit_id` | string | — | yes | PK part → `unit` | — |
| `carrier_id` | string | — | yes | PK part → `carrier` | — |
| `coefficient` | real | per output unit | yes | — | **Consumed negative, produced positive** |
| `is_primary_output` | boolean | — | yes | — | Exactly one true per unit |
| `is_reject` | boolean | — | yes | — | True marks recovered heat leaving the unit |

**Sign convention, restated because §7 depends on it.** Consumed carriers are negative,
produced carriers positive. Process-emission carriers are produced, hence positive.

**`is_reject` is what makes waste heat work.** A kiln's reject heat is a *positive*
coefficient on a low-grade heat carrier. Without these rows every unit rejects zero, the
cascade has nothing to cascade, and the 28 `efficiency_heat_recovery` options in the library
stay unmodellable. A reject carrier is `intermediate`, so it carries no emissions — its fuel
was charged to the rejecting unit.

### 3.7 `infrastructure_scenario` — exogenous availability (D7)

*v1 §3.7, unchanged.*

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `scenario_id` | string | — | yes | PK part | — |
| `carrier` | enum{hydrogen, co2_transport, grid_headroom} | — | yes | PK part | — |
| `cluster_id` | string | — | yes | PK part | One of the 9 GB clusters, or `none` |
| `period` | integer | year | yes | PK part | A model period |
| `available` | boolean | — | yes | — | Whether the carrier can be used |
| `capacity_limit` | real | PJ/yr or kt/yr | no | — | Optional per-premise cap; unbounded if absent |
| `unit_tariff` | real | £m per PJ or kt | yes | — | **Replaces COMIT's four infrastructure PV terms** (§5.4) |

**Rule.** A premise is assigned to the nearest in-scope cluster on ingest (A1). Its
availability is read from that cluster's rows. Premises beyond a configured cluster
radius get `available = false` for hydrogen and CO₂ transport.

### 3.8 `scenario_parameters`

*v1 §3.8, extended.*

Extended from v1. New rows only are listed.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `parameter_id` | string | — | yes | PK | — |
| `carrier_id` | string | — | no | → `carrier` | Set for per-carrier series |
| `period` | integer | — | no | PK part | Period index |
| `value` | real | varies | yes | — | — |

New parameters: `import_price` and `export_price` per carrier per period; `export_price`
must be **strictly below** `import_price` (V21, and it is physically true anyway);
`reinforcement_cost` per voltage band; `area_density` in MW per m² for onsite generation.

### 3.9 `process_duty`

***new** — v1 §3.9 was `site_pathway`, an output, which belongs in §8.*

What a premise must produce, per period. Replaces v1's vector-share allocation, which the
carrier balance makes unnecessary.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part → `premise_record` | — |
| `process_id` | string | — | yes | PK part | → `activity_process_register` |
| `period` | integer | — | yes | PK part | Period index, not a calendar year |
| `carrier_id` | string | — | yes | → `carrier` | What the duty is *for* |
| `quantity` | real | PJ/yr or Mt/yr | yes | — | ≥ 0. Unit follows `carrier.denominator_kind` |
| `grade_rank` | integer | — | no | → `carrier` | Required where the carrier is gradeable |
| `evidence_tier` | enum{site_known, named_set, activity_default} | — | yes | — | D10 |

### 3.10 `premise_process_detail` — known site processes and capacity

*v1 §3.10, `technology_code` renamed `unit_id`.*

**Optional per-premise intelligence.** Where the actual processes at a site are known —
from a permit, an audit, a site visit, or an operator disclosure — they are stated here
and override both the default set and any named variant. Zero rows for a premise is the
normal case and means "use the register".

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `process_id` | string | — | yes | PK part | → `activity_process_register` |
| `connection_id` | string | — | no | → `premise_connection` | **Optional.** Which electricity connection serves this process (§3.1.3). Absent ⇒ the default. This is what decides where electrified load lands |
| `known_capacity` | real | capacity units | no | — | > 0 if present. Units follow the process's denominator (D5): PJ/yr-equivalent for energy, Mt/yr for mass |
| `unit_id` | string | — | no | → `unit` | The specific installed unit, where known |
| `provenance` | string | — | yes | — | Citation: permit number, audit reference, disclosure |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried through to output |

**Rule (completeness).** The rows for a premise are treated as its **complete** process
list. A partial list would silently delete processes the site runs and misstate its
energy balance, so a premise with any rows must have rows for every process it runs. If
only fragmentary knowledge exists, use a named `process_set_id` instead.

**Rule (precedence).** Where `unit_id` is given, that unit is the premise's
existing plant for that process and A4 does not choose between candidates. Where
`known_capacity` is given, it is used directly and A4 back-solves *utilisation* instead
of capacity (§A4).

**On vintage (D11).** When the plant was commissioned lives in `premise_process_vintage`
(§3.15), not here. It was moved out because this table is keyed premise × process and can
hold exactly one year, while a real works commonly runs two units of the same process
installed decades apart — a 1998 kiln line and a 2016 one. One year per process cannot
say that, and averaging the two is the thing D11 exists to stop.

### 3.11 `premise_measured_emissions` — reported emissions, where they exist

*v1 §3.11, unchanged.*

**Optional per-premise intelligence.** For sites in UK ETS, or covered by permit
reporting or NAEI point-source data, measured emissions exist and are better evidence
than anything this model computes. They are used to **reconcile and calibrate** the
baseline, not to replace the computed value — see §7.6 for why that distinction is
forced rather than chosen.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `emission_year` | integer | year | yes | PK part | Should match `premise_record.data_year` |
| `source_category` | enum{combustion, process, total} | — | yes | PK part | `total` only where the split is unavailable |
| `ghg` | enum{CO2, CH4, N2O, total_co2e} | — | yes | PK part | — |
| `quantity` | real | kt CO₂e/yr | yes | — | ≥ 0 |
| `scope` | enum{direct, indirect} | — | yes | — | Indirect excluded from the §7.4 direct comparison |
| `provenance` | string | — | yes | — | Citation: UK ETS account, permit, NAEI reference |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried through to output |

**Rule.** If both `total` and a `combustion`/`process` breakdown are supplied for the
same premise-year, the parts must sum to the total within 1%, or the record is rejected
with reason `emissions_inconsistent`.

### 3.12 `premise_operating_profile` — schedule and load shape

*v1 §3.12, unchanged.*

**Optional per-premise intelligence.** Two distinct things live here, and they answer
different questions. The **operating schedule** says when the site runs, which validates
the utilisation A4 derives. The **load statistics** say how peaky it is, which is what a
connection capacity is actually about (§5.6).

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `connection_id` | string | — | no | PK part → `premise_connection` | Peak and load-factor fields are **per connection** where a site has more than one. Absent ⇒ the default connection. Schedule fields are premise-wide and repeat |
| `operating_pattern` | enum{continuous, three_shift, double_day, single_shift, seasonal_campaign} | — | no | — | Coarse classification; `continuous` ⇒ ~8,760 h/yr |
| `operating_hours_per_year` | real | h/yr | no | — | ∈ (0, 8784]. Preferred over `operating_pattern` where known |
| `operating_days_per_week` | real | d/wk | no | — | ∈ (0, 7] |
| `shutdown_weeks` | real | wk/yr | no | — | ≥ 0. Planned maintenance or campaign downtime |
| `peak_electricity` | real | MW | no | — | > 0 if present. Measured maximum demand |
| `peak_gas` | real | MW | no | — | > 0 if present. Peak gas offtake expressed as power |
| `load_factor_electricity` | real | fraction | no | — | ∈ (0, 1]. Annual energy ÷ (peak × 8,760) |
| `load_factor_gas` | real | fraction | no | — | ∈ (0, 1] |
| `within_shift_peak_factor` | real | ratio | no | — | ≥ 1. Peak ÷ mean demand *during operating hours* (§5.6) |
| `profile_basis` | enum{half_hourly, daily, monthly, schedule_only, estimated} | — | yes | — | What the statistics were derived from |
| `provenance` | string | — | yes | — | Citation: meter operator, DNO connection record, site audit |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried through to output |

**Rule (derived statistics, not raw profiles).** Half-hourly data is ~17,520 points per
premise per year and does not belong in this contract — at stock scale it is larger than
every other input combined, and this model is annual (§5.1) so it cannot consume the
series directly. The stock model retains the raw profile; what crosses the interface is
the **derived statistics above**. If richer shape information is later needed, extend
this entity with a small number of representative day shapes or load-duration-curve
percentiles, never the full series.

**Rule (consistency).** Where both a peak and a load factor are supplied for a vector,
they must reconcile against that vector's annual energy in `premise_energy` (§3.1.1)
within 5%:

$$\text{load factor} = \frac{E\,[\text{PJ/yr}] \times 277{,}778}{P^{\text{peak}}\,[\text{MW}] \times 8{,}760}$$

Divergence beyond that is reported as `profile_energy_inconsistent` — most often a
vintage mismatch between the profile year and `data_year`.

### 3.13 `process_load_shape` — how a process presents its demand

*v1 §3.13, unchanged.*

**The shape belongs to the process, not to the unit.** A kiln runs continuously
whether it is fired by gas or by hydrogen; a batch dryer is batchy whether it is gas or
electric. What a unit operation *does* determines when it draws power, so the shape is
declared once per process and inherited by every unit serving it. Units
override it only by exception (`unit.load_shape_override`, §3.5).

This is the decomposition that makes the peak question tractable. Declaring shapes per
unit would multiply the data build by the fuel variants — 82 of 94 COMIT processes
differ only by fuel — for information that does not vary along that axis.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `shape_id` | string | — | yes | PK | — |
| `process_id` | string | — | yes | → `carrier` | The process this describes |
| `shape_class` | enum{flat, throughput_following, batch_cyclic, intermittent, standing, seasonal} | — | yes | — | See below |
| `duty_factor` | real | fraction | yes | — | ∈ (0, 1]. Share of operating hours in which the process draws power |
| `peak_to_mean` | real | ratio | yes | — | ≥ 1. Peak ÷ mean demand across the hours it is running |
| `runs_when_idle` | boolean | — | yes | — | True ⇒ draws power outside the site's operating hours |
| `seasonality` | enum{none, winter_weighted, summer_weighted, campaign} | — | yes | — | Drives whether the annual peak falls outside a representative week |
| `provenance` | string | — | yes | — | Citation |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried through to output |

**The shape classes.**

| Class | Meaning | Typical `duty_factor` | Typical `peak_to_mean` | Examples |
|---|---|---|---|---|
| `flat` | Constant while the site operates | ~1.0 | ~1.0–1.1 | Rotary kiln, continuous furnace, continuous digester |
| `throughput_following` | Proportional to production rate | 0.7–1.0 | 1.1–1.4 | Mills, crushers, conveyors, pumps |
| `batch_cyclic` | Repeating on/off cycles | 0.3–0.7 | 2–4 | Batch ovens, autoclaves, curing, electric melting |
| `intermittent` | Driven by operator activity | 0.1–0.4 | 3–6 | Welding, hand tools, workshop equipment |
| `standing` | Runs regardless of production | ~1.0 | ~1.0 | Refrigeration, lighting, compressed air, site services |
| `seasonal` | Weather- or campaign-driven | varies | varies | Space heating, seasonal processing campaigns |

Values are indicative of the shape's character, not defaults to be adopted unexamined.

**Rule.** `standing` processes must have `runs_when_idle = true`; every other class must
have it false unless a citation says otherwise. This distinction is what makes a
single-shift site's peak differ from its energy — refrigeration runs through the night
and the presses do not.

### 3.14 `premise_weekly_profile` — measured shape, where it exists

*v1 §3.14, unchanged.*

**Optional, and deliberately small.** A representative **half-hourly week** — 336
points — captures the daily cycle and the weekday/weekend difference, which is most of
what shape means for a connection question, at ~2% of a full year's data. Supplied per
premise per vector, and per process only where sub-metering makes that real.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `connection_id` | string | — | no | PK part → `premise_connection` | Half-hourly data arrives per MPAN, so a multi-connection site has one series per connection. Absent ⇒ the default |
| `vector` | enum{electricity, gas} | — | yes | PK part | The metered vectors only |
| `process_id` | string | — | no | PK part | Present only where sub-metered; absent ⇒ whole site |
| `season` | enum{annual, winter, summer, shoulder} | — | yes | PK part | `annual` ⇒ a single representative week |
| `interval_index` | integer | — | yes | PK part | 1–336, Monday 00:00 to Sunday 23:30 |
| `fraction_of_peak` | real | fraction | yes | — | ∈ [0, 1]. Normalised so the maximum across the week is 1 |
| `annual_peak` | real | MW | yes | — | The **annual** maximum, recorded separately — see the rule below |
| `provenance` | string | — | yes | — | Citation: meter operator, DNO record |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried through to output |

**Rule (the representative week does not contain the annual peak).** A typical week is
typical by construction, so its maximum is not the year's maximum — and the year's
maximum is exactly what a connection capacity is sized against. The week gives the
*shape*; `annual_peak` carries the *level*, taken from the full series upstream. Using
the week's own maximum as the site peak understates it, and for `seasonal` processes
substantially.

**Rule (seasons are optional but recommended where seasonality is not `none`).** One
`annual` week suffices for a continuous process. Where §3.13 declares
`winter_weighted`, `summer_weighted` or `campaign` seasonality, supply `winter`, `summer`
and `shoulder` weeks — 1,008 points, still small — or the annual peak cannot be
attributed to the right process when the mix changes.

---

### 3.15 `premise_process_vintage` — when the plant was installed (D11)

*v1 §3.15, `technology_code` renamed `unit_id`.*

**Optional per-premise intelligence, and the highest tier of vintage evidence.** Where
the commissioning date of the plant serving a process is known — from a permit, a
BAT/BREF review, an asset register, a site visit or an operator disclosure — it is stated
here. Zero rows for a premise is the normal case and means "fall through to
`premise_record.construction_year`, and then to the default" (§5.3.1).

One row per **cohort**: a distinct tranche of capacity commissioned in the same year. A
works with one kiln has one row; a works whose second line was added eighteen years after
the first has two.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `process_id` | string | — | yes | PK part | → `activity_process_register` |
| `cohort_id` | string | — | yes | PK part | Stable within the premise-process. `1`, `2`, … is sufficient |
| `unit_id` | string | — | no | → `unit` | The unit this cohort is. Absent ⇒ whatever A4 resolves for the process |
| `commissioned_year` | integer | year | yes | — | ≤ `premise_record.data_year`. Rejected with reason `vintage_in_future` otherwise |
| `capacity_share` | real | fraction | yes | — | ∈ (0, 1]. Share of the process's existing capacity in this cohort |
| `provenance` | string | — | yes | — | Citation: permit number, asset register, disclosure |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried through to output |

**Rule (shares sum).** For each `(premise_id, process_id)` the `capacity_share` values
must sum to 1 within 1e-6, or the premise's vintage rows are rejected with reason
`vintage_shares_unbalanced` and that process falls back to the next tier. Partial vintage
knowledge is expressed as a cohort with the year you do know plus a residual cohort with
your best estimate — not as shares that do not close, which would silently shrink the
site's capacity.

**Rule (units are shares, not capacities).** The absolute capacity of the process is A4's
business and may be back-solved rather than known. Stating vintage as a share keeps the
two independent, so a site can supply ages without supplying capacities and vice versa.

**Rule (refurbishment is not recommissioning).** A cohort's year is when the plant was
*installed*, not when it was last overhauled. A 1998 kiln relined in 2019 is a 1998
cohort. Life extension through major refurbishment is real and is a known gap, noted in
§5.3.1 — recording an overhaul as a new commissioning date is the wrong way to represent
it, because it also resets the residual value the asset is carrying and makes early
replacement look more expensive than it is.

**Why a separate entity from §3.10.** `premise_process_detail` is keyed premise × process
and asserts a *complete* process list; this table is keyed one level finer and asserts
nothing about completeness. A premise may have vintage rows for its kiln and none for its
mills, and the mills simply fall to the next tier. Forcing the two into one table would
have made vintage all-or-nothing for a site, which is the opposite of how the evidence
actually arrives.

### 3.16 `activity_default_unit`

***new**.*

**What plant an activity typically already has.** The base-year supply side: which units
serve each duty today, before any investment decision. Also **absent from both specs** until
now, and the reason a site with a 20 MW CHP and one without are currently the same row.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `carb3_activity` | string | — | yes | PK part | → `activity_process_register` |
| `process_set_id` | string | — | yes | PK part | → `activity_process_register` |
| `process_id` | string | — | yes | PK part | → `activity_process_register` |
| `duty_family` | string | — | yes | PK part | → `activity_process_duty_profile` |
| `unit_id` | string | — | yes | PK part | → `unit`. Must be eligible for this activity and process (§3.4) |
| `default_share` | real | fraction | yes | — | ∈ [0, 1]. Share of this duty the unit serves in the base year |
| `sizing_basis` | enum{duty_annual, duty_peak, throughput} | — | yes | — | How installed capacity is derived from the duty |
| `evidence_tier` | enum{sector_statistic, derived, assumed} | — | yes | — | **Non-nullable.** `sector_statistic` means a published figure (DUKES, CHPQA) |
| `provenance` | string | — | yes | — | Citation |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried to output |

**Rule (every duty is served).** For each `(carb3_activity, process_set_id, process_id,
duty_family)`, `default_share` must sum to 1.00 ± 0.015. A duty is met by *something* today;
a shortfall means the unit set is incomplete, not that the duty goes unmet.

**Rule (eligibility is a precondition).** A row whose `(unit_id, carb3_activity,
process_id)` has no `unit_eligibility` entry is rejected. The default cannot assert plant the
model would refuse to build, or A4 back-solves a baseline the optimiser cannot reproduce.

**No electricity co-product field, deliberately.** A CHP's electrical output is already
described by `unit_input_output` (§3.3), which gives every unit its full carrier vector.
Restating it here would be a second place for the same number to live, and they would
disagree. This entity says only *which* unit and *how much of the duty*; what the unit does
with that duty is the unit's own definition.

**Why an activity default rather than back-solving.** v1's A4 infers existing technology
from metered energy, which works while every technology is a fuel variant of a demand
device — the fuel identifies the plant. It stops working once generation, storage and CHP
exist: a CHP is not inferable from a heat duty, because the same heat is equally consistent
with a boiler. Some of the supply side has to be asserted, and the activity default is where
it is asserted for premises with no site intelligence. Where §3.10 of the v1 spec
(`premise_process_detail`) gives real plant for a real site, that wins — the D10 ladder is
unchanged.

### 3.17 `archetype_coefficient`

***new**.*

What Tier A emits. **One constant per coefficient per unit** — not a function of a design
ratio, because a hybrid unit fixes the ratio (PD3).

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `archetype_id` | string | — | yes | PK part | — |
| `unit_id` | string | — | yes | PK part → `unit` | — |
| `psi` | real | fraction | no | — | ∈ [0, 1]. Onsite-generation self-consumption |
| `beta` | real | fraction | no | — | ∈ [0, 1]. Firm capacity contribution, feeds C11 |
| `chi` | real | fraction | no | — | ∈ [0, 1]. Paired-output utilisation |
| `epsilon` | real | fraction | no | — | > 0. Effective purchase price multiplier for flexible loads |
| `evidence_tier` | enum{fitted, substituted, default} | — | yes | — | **Non-nullable.** See below |
| `sizing_ratio` | real | — | no | — | Required if the unit is hybrid. Concavity is checked across these |

**`epsilon` is not optional on a flexible-load hybrid.** For `pv_battery` the value is
self-consumption and for `chp_thermal_store` it is heat utilisation, but for
`electrolyser_battery` the battery buys cheap hours — arbitrage against a time-varying
tariff. An annual model carries one price per period, so without ε that value is invisible,
`electrolyser_battery` is strictly dominated by a bare electrolyser, and the hybrid-unit
mechanism silently does nothing.

**`evidence_tier` exists because a premise can match no archetype.** `fitted` means Tier A
ran for this archetype; `substituted` means the nearest archetype's coefficients were used
and the substitution is recorded; `default` means an activity-level fallback. A premise
running on a substituted coefficient must never be mistaken on paper for one running on a
fitted match. This is the D10 pattern, applied to a new kind of evidence.

---

## 4. Algorithms

*Section last updated: 2026-09-01*

**Not written. Owned by T13.** A1–A9 carry over from v1 in outline, but five change
materially and one of those is the deepest open question in the design:

- **A2** also resolves the candidate unit set and applies `unit_eligibility.min_duty`.
- **A3** is largely removed; the carrier balance replaces share allocation.
- **A4 is under-determined as written.** In v1 the technology code pins the fuel, so
  `energy → capacity` has one answer. Here a unit may burn a mix, so the same metered energy
  is consistent with many (capacity, mix) pairs. The proposed resolution is a three-tier
  carrier-mix rule in the D10 pattern; see the [spec changes
  document](2026-08-28-carb3-site-energy-system-spec-changes.md). **V1b cannot be defined
  until this is closed**, so T13 blocks T5.
- **A6** declares variables over units and carrier flows, and attaches ψ, β, χ, ε.
- **A7**'s relaxation ladder gains rungs **C12 → C10 → C11**, ahead of C9.

---

## 5. The optimisation model

*Section last updated: 2026-09-01*

**This section is authoritative.** Everything else serves it.

### 5.1 Sets and indices

| Symbol | Meaning |
|---|---|
| $T$ | Model periods, $t \in \{0, \ldots, N\}$. **$t$ is a period index, not a calendar year** |
| $\Delta$ | Timestep in years. The calendar year of period $t$ is $y_t = y_{t_0} + \Delta t$ |
| $Q$ | Duties at this premise |
| $U$ | Units available, $U = \bigcup_{q} U_q$ |
| $U_q$ | Units eligible for duty $q$, after `unit_eligibility` screening |
| $U^0$ | **Incumbent** units, those with existing capacity |
| $\mathcal{C}$ | Carriers |
| $\mathcal{C}^{\text{prim}}$ | Primary carriers. Emissions attach here and nowhere else |
| $\mathcal{K}$ | The premise's connections |
| $g(c)$ | Grade rank of carrier $c$, where gradeable |

**Any lifetime used as an index offset is converted to periods first:**
$\ell_{u} = \lceil L_u / \Delta \rceil$. A 25-year life on a 5-year timestep is 5 periods;
reading it as 25 is a 125-year asset.

### 5.2 Decision variables

All continuous and non-negative. **The problem is a pure LP and must stay one.**

| Variable | Meaning | Unit |
|---|---|---|
| $n_{u,t}$ | New capacity of unit $u$ built in $t$ | capacity units |
| $a_{u,t}$ | Capacity of $u$ available in $t$ | capacity units |
| $z_{u,t}$ | Activity of $u$ in $t$ | output units |
| $e_{u,t}$ | Surviving incumbent capacity of $u$ (D11), declared over $U^0$ only | capacity units |
| $r_{u,t}$ | Incumbent capacity retired early in $t$ (D11), over $U^0$ only | capacity units |
| $m_{c,k,t}$ | Import of carrier $c$ at connection $k$ | PJ/yr |
| $x_{c,k,t}$ | Export of carrier $c$ at connection $k$ | PJ/yr |
| $w_{k,t}$ | Reinforcement purchased at connection $k$ | MW |

**Activity is $z$, not $u$.** v1 used $u$ for activity; here $u$ indexes units, so the
activity variable is renamed to avoid the collision. This is deliberate and is the kind of
clash the label rules in §1.4 exist to prevent.

**No binaries.** Minimum scale is handled by eligibility screening in A2 and by reporting,
never by a fixed-charge binary. Any proposal to add one must be weighed against §9.

### 5.3 Parameters

| Symbol | From | Meaning |
|---|---|---|
| $D_{q,t}$ | `process_duty` | Duty quantity |
| $\iota_{u,c}$ | `unit_input_output.coefficient` | Signed coefficient of $u$ for $c$ |
| $\kappa_u, \phi_u, L_u$ | `unit` | Capex, fixed opex, lifetime |
| $\alpha_u, \gamma_u, \rho_u$ | `unit` | Availability, capacity→activity, fraction not captured |
| $\psi_u, \beta_u, \chi_u, \varepsilon_u$ | `archetype_coefficient` | Tier A coefficients |
| $\eta_{u,t}, \bar R_{u,t}$ | D11 survival function | Fraction surviving, mean remaining life |
| $\xi$ | `scenario_parameters` | Stranding factor |
| $p^{\text{imp}}_{c,t}, p^{\text{exp}}_{c,t}$ | `scenario_parameters` | Import and export prices |
| $\overline{P}^{\text{imp}}_k, \overline{P}^{\text{exp}}_k$ | `premise_connection` | Connection capacities |
| $A_k, \delta^{\text{area}}$ | `premise_connection`, `scenario_parameters` | Available area, MW per m² |
| $\pi_t, \tau_{c,t}, \sigma, r, i$ | `scenario_parameters` | Carbon price, tariff, stability factor, discount and interest rates |

**D11's survival function $\eta$ and mean remaining life $\bar R$ are carried over from v1
§5.3.1 unchanged**, with `technology` reading as `unit`. They are parameters computed before
the problem is built, which is what keeps D11 free of binaries.

### 5.4 Objective

Minimise total present-value cost:

$$\min \; Z = \sum_{t} \Big[\; \delta_t \big( Z^{\text{capex}}_t + Z^{\text{opex}}_t + Z^{\text{fuel}}_t + Z^{\text{carbon}}_t + Z^{\text{infra}}_t + Z^{\text{net}}_t - Z^{\text{exp}}_t \big) \;+\; d_t \, Z^{\text{strand}}_t \;\Big]$$

with $\delta_t$ the present-value factor aggregated over the periods in a timestep and $d_t$
the **single-year** factor used for the stranding write-off. Capex is annuitised over
$L_u$ at interest rate $i$; the annuity for a hybrid already contains its component
replacements (§3.5).

$$Z^{\text{fuel}}_t = \sum_{c,k} m_{c,k,t}\,\big(p^{\text{imp}}_{c,t} + \tau_{c,t}\big) \cdot \varepsilon(c,t) \qquad Z^{\text{exp}}_t = \sum_{c,k} x_{c,k,t}\,p^{\text{exp}}_{c,t}$$

$$Z^{\text{net}}_t = \sum_{k} \gamma_k\big(w_{k,t}\big)$$

**$Z^{\text{exp}}$ enters with a negative sign, so the objective now has a genuinely
negative term.** No implementation may assume cost components are non-negative. V6 already
records this trap for emissions; it now applies to costs.

**Carbon cost carries the $10^{-3}$ unit conversion** that v1 §5.4 documents. Emission
factors are kt/PJ and the carbon price is £/t.

### 5.5 Constraints

**C1 — Duty satisfaction.** Each duty is met in each period, by units eligible for it:

$$\sum_{u \in U_q} z_{u,t} = D_{q,t} \qquad \forall q \in Q,\; t \in T$$

**C2 — Activity limited by available capacity.**

$$z_{u,t} \le a_{u,t}\,\gamma_u\,\alpha_u \qquad \forall u,\, t$$

**C3 — Capacity transfer between periods.** Carried over from v1 unchanged with $u$ reading
as a unit:

$$a_{u,t} = e_{u,t} + \sum_{s \le t} n_{u,s}\,\mathbb{1}[\,s \le t \le s + \ell_{u,s} - 1\,]$$

with $e_{u,t} \equiv 0$ for $u \notin U^0$. An abatement unit expires with its host, not on
its own life.

**C4 — Incumbent ageing and early retirement (D11).** Carried over from v1 §5.5 unchanged in
all four parts, with `technology` reading as `unit` and the retrofit rule restated on
`abates_unit_id`: a unit whose host is still standing has not been scrapped, so it attracts
no stranding charge and inherits the host's remaining life.

**C5 — No building in the start year.** $n_{u,t_0} = 0 \;\; \forall u$.

**C6 — Unit stability.** Two-legged ramp limit, carried over from v1 unchanged in form.
$\sigma$ is measured against deliverable output $\bar z_{u,t} = a_{u,t}\gamma_u\alpha_u$, so a
value calibrated for v1 carries over directly.

**C7 — Known changes.** Announced commitments fix or bound $z_{u,t}$ or $a_{u,t}$.

**C8 — Carrier balance. This is the core change.** For every carrier at every period, at the
premise:

$$\sum_{u \in U} z_{u,t}\,\iota_{u,c} \;+\; \sum_{k \in \mathcal{K}} \big(m_{c,k,t} - x_{c,k,t}\big) \;=\; 0 \qquad \forall c \in \mathcal{C},\, t$$

with $m_{c,k,t} = x_{c,k,t} = 0$ where the premise has no connection carrying $c$. v1
balanced only intermediate commodities and treated electricity as an unconstrained priced
fuel; balancing every carrier is what makes onsite generation, CHP and export expressible at
all.

**C9 — Infrastructure availability (D7).** A unit whose carrier is unavailable at the premise
in a period cannot run, and where a cap is specified the premise's draw respects it. Extended
from v1 to cover a `biomethane` carrier, whose real constraint is a shared catchment and
therefore cannot be modelled per premise.

**C10 — Heat grade cascade.** A unit may serve a duty only at or below its output grade:

$$z_{u,t} = 0 \quad \text{for } u \in U_q \text{ where } \text{grade\_out}(u) < g\big(\text{carrier}(q)\big)$$

In practice this is enforced by **eligibility at load** rather than as a row in the LP, which
is why V19 is a load-scope test. Stating it as a constraint keeps §5 complete; implementing
it as a filter keeps the problem small.

**High grade may serve a low-grade duty, never the reverse.** A steam boiler at 150–400 °C
serves a 120 °C duty; a heat pump capped at 100 °C does not. This is the physics v1 enforced
by a mapping table and could not state.

**C11 — Connection capacity.** Per connection, never summed across connections:

$$P^{\text{peak}}_{k,t} \;\le\; \overline{P}^{\text{imp}}_{k} + w_{k,t} + \sum_{u} \beta_u\,a_{u,t} \qquad \forall k \in \mathcal{K},\, t$$

and export bounded by $\sum_c x_{c,k,t} \le \overline{P}^{\text{exp}}_k$ after conversion to
power. Peak is rebuilt from the solved pathway by the §5.6 method carried over from v1, using
`process_load_shape` and the diversity step that must not be skipped.

**$\beta$ is how storage earns its keep here**, and it is the one place a standalone battery
is worth building: it contributes firm capacity linearly, with no dependence on a sizing
ratio, so it needs no hybrid pairing.

**C12 — Siting cap.** Onsite generation is bounded by usable area:

$$\sum_{u \in U^{\text{gen}}} a_{u,t} \;\le\; \delta^{\text{area}} \sum_{k} A_k \qquad \forall t$$

Without this the LP builds unbounded PV and exports it. This constraint is the reason
`available_area` is the highest-priority missing input.

**Non-degeneracy rule.** $p^{\text{exp}}_{c,t} < p^{\text{imp}}_{c,t}$ strictly, per carrier
per period, asserted at load (V21). Equal prices make building and importing exactly
cost-equivalent, and the solver is then free to report either — two identical runs would
disagree on onsite capacity. The deterministic tie-break is lexicographic over
$(\texttt{unit\_id}, \texttt{carrier\_id})$; v1's key was `technology_code`, which no longer
exists.

---

## 6–13. Not yet written

§6 constraint disposition, §7 emissions accounting (**T14**), §8 output schema, §9
performance and scale gates including G4 (**T7**, **T15**), §10 validation including V1b and
V18–V23 (**T5**, **T14**, **T15**), §11 phasing, §12 reference map, §13 worked examples
(**T10**, **T16**).
