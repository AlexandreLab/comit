# CaRB3 Site Energy System — Implementation Specification

**Status:** Draft — §1, §2, §3, §4, §5, §7, §9 and §10 written. §6, §8 and §11–§13 are not yet written
**Date:** 2026-09-07
**Scope:** Great Britain (England, Wales, Scotland) · CaRB3 **Factory class** only (55 activities)
**Companion documents:** [overview and decisions](2026-08-28-carb3-site-energy-system-overview.md) ·
[architecture](2026-08-28-carb3-site-energy-system-architecture.md) ·
[data migration](2026-08-28-carb3-site-energy-system-data-migration.md) ·
[delivery](2026-08-28-carb3-site-energy-system-delivery.md)

> **This document is self-contained.** Every entity, decision label and symbol it uses is
> defined here. Nothing in it requires reading another document first.

> **Incomplete by design.** It is being written section by section against the delivery
> plan, which names the owner of each outstanding section. Do not treat a missing section as
> a decision that it is unnecessary.

---

## 1. Scope, inputs, conventions, and how to read this

*Section last updated: 2026-09-07*

### 1.1 What this document is

A build specification: one record per premise in, a least-cost decarbonisation pathway out,
solved independently per premise. It states **what to build**, not how to build it in a
particular language.

**Validation chain.** The model's results are anchored to COMIT, the R optimisation model
that runs today, in two hops and neither may be skipped. **V1** asserts that the
[COMIT-parity baseline specification](archive/2026-08-19-carb3-site-decarbonisation-implementation.md)
reproduces coupled-off COMIT. **V1b** asserts that this model reproduces that baseline in
the *carrier-equivalent configuration* defined in §10.

### 1.2 What this architecture must express

Three capabilities are required of the model, and each is impossible under a design that
maps technologies to processes by table and prices every fuel exogenously. They are the
reason for the duty / unit / carrier spine described in §2 and specified in §3 and §5.

| Requirement | Why a table-mapped design cannot express it | How this design expresses it |
|---|---|---|
| **Onsite generation** — PV, CHP, electrolysers, anaerobic digestion | These produce a carrier rather than serving a process demand, so a duty-satisfaction constraint of the form `Σ output = demand` has no place to put them. Pricing onsite electricity at the grid tariff to compensate nullifies PV, whose entire value is that its energy costs LCOE and not the tariff | A generator is an ordinary **unit**. Its output enters the **carrier balance** (C8) alongside imports, and needs no special class |
| **Storage** | A battery or thermal store charges and discharges inside one annual period and nets to a round-trip loss, so a cost-minimising model never builds one | **Hybrid units** at a fixed sizing ratio (PD2), whose value is measured offline by the Tier A archetype layer and enters as the coefficients ψ, β, χ, ε |
| **Heat quality and waste heat** | Temperature lives in the *process code* (`LTH`/`HTH`/`STM`/`DRY`), so what stops a heat pump firing a kiln is a mapping table rather than physics. A kiln's reject heat has nowhere to go, and 28 of the 134 options in `decarbonisation_options_library.csv` are heat recovery | Heat is a **graded carrier** with a one-way cascade (C10). Reject heat is a low-grade supply, which is exactly the source a heat pump needs |

The single structural move behind all three is to **separate the duty from the unit that
meets it, and put a carrier network between them**. Everything else follows.

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
| `A1`–`A9` | Algorithms | §4 |
| `S0`–`S9` | Pipeline stages | §2.1 |
| `V1`–`V26` | Validation tests | §10 |
| `G1`–`G4` | Scale gates | §9 |
| `D1`–`D12` | Design decisions | §1.6 |
| `PD1`–`PD2` | Programme decisions | the [overview](2026-08-28-carb3-site-energy-system-overview.md) |

### 1.5 Glossary

| Term | Meaning |
|---|---|
| **Carrier** | Anything that flows and balances: gas, electricity, hydrogen, biomethane, CO₂, and heat at a grade |
| **Grade** | A temperature band on a heat carrier. Ordered, and the cascade runs one way only |
| **Duty** | What a process requires: a quantity of a carrier at a grade. The demand side |
| **Unit** | What converts between carriers. The supply side. Boiler, heat pump, kiln, CHP, PV, battery |
| **Hybrid unit** | A co-located package at a **fixed sizing ratio**, e.g. `pv_battery_2h`. One unit, one capex, one coefficient set (PD2) |
| **Primary carrier** | One that enters the site or is extracted: gas, coal, biomass, grid electricity. Emissions attach here |
| **Intermediate carrier** | One produced and consumed on site: heat, steam, recovered heat. Emissions never attach here |
| **Tier A / Tier B** | The offline archetype dispatch layer, and the per-premise annual investment LP |

**Not a virtual power plant.** A VPP aggregates assets across multiple sites, which is the
inter-premise coupling D2 forbids. "Hybrid unit" means co-located, one premise.

### 1.6 Design decisions

Twelve decisions fix the shape of the model. Everything in §2–§13 is written inside them,
and each is cited by label wherever it constrains a choice.

| # | Decision | What it buys | What it costs |
|---|---|---|---|
| **D1** | Full CaRB3 **Factory-class** stock — all 55 activities, every premise | Coverage of the whole industrial stock, not just the ~1,026 point sources | Rules out a single coupled optimisation; non-Factory premises (offices, retail, schools, warehouses) are excluded |
| **D2** | Per-site independent solves | Linear scaling; embarrassingly parallel; genuinely per-site answers | Removes national and cluster coupling entirely |
| **D3** | Full CaRB3 unit operations as processes | Process switching becomes a real lever, not just fuel switching | A large data build |
| **D4** | Baseline energy supplied upstream by the stock model | Removes the emissions-proxy problem; real heterogeneity per site | A hard dependency on the stock model's quality |
| **D5** | Hybrid denominators — energy (PJ) by default, mass (Mt) for chemistry | Most coefficients derivable from supplied energy; keeps process emissions physically grounded (kt CO₂ per Mt) | Two denominator conventions to keep straight |
| **D6** | Tiered cost provenance — reuse COMIT, then BREF/BAT, then proxy | Shrinks the data build far below the naive count; weak estimates visible, not hidden | A mixed-confidence dataset needs careful reporting |
| **D7** | Infrastructure exogenous — H₂, CO₂ and biomethane availability as scenario input | Simple and explicable; the assumption is owned and stated | **No infrastructure co-optimisation** |
| **D8** | Great Britain scope | Keeps Grangemouth and Peterhead; matches expected stock coverage | Excludes Northern Ireland — 56 sites and the Londonderry cluster |
| **D9** | One direction for site heterogeneity — this specification, not a parallel roadmap | No conflicting roadmaps | — |
| **D10** | Tiered site intelligence — known site detail replaces activity defaults outright | Real sites modelled as themselves wherever evidence exists; the model improves as intelligence accumulates, without redesign | Mixed-evidence results; every output row must carry its evidence tier or the quality is invisible |
| **D11** | Existing plant has an age — it retires when its life ends, and early replacement pays the residual value | Replacement timing becomes an economic result instead of an artefact; near-new plant stops being scrapped for free | A vintage assumption for every premise with no age data, and one more parameter (ξ, §5.3) to defend |
| **D12** | Measured inputs are a time series; exactly one year is the **base year**, and only that year is read | History becomes available for reconciliation, trend evidence and audit without touching the annual LP or A4's back-solve | A base year must be named per premise, a substitution ladder is needed for carriers metered off it, and every history row is data nobody reads today |

Four have the widest reach in this document:

- **D2 — per-site independent solves.** No constraint may couple two premises. Anything
  needing cross-site information becomes a scenario input or a post-hoc comparison. This is
  structural; nothing in this document can undo it.
- **D5 — hybrid denominators.** Energy (PJ) by default, mass (Mt) for chemistry. This is
  also the line the unit spine splits on (§3.2).
- **D10 — tiered site intelligence.** Known site detail replaces activity defaults outright,
  and every output row carries its evidence tier.
- **D11 — plant has an age.** Ageing, early retirement and the stranding charge attach
  to units (C4).

---

## 2. System overview

*Section last updated: 2026-09-01*

### 2.1 Components

| # | Component | Responsibility |
|---|---|---|
| S0 | **Archetype dispatch (Tier A)** | Offline, hourly, once per archetype per hybrid sizing ratio. Emits ψ, β, χ, ε |
| S1 | Ingestion and validation | Accept premise records, validate, reject with reasons |
| S2 | Process and unit expansion | Premise → its duties, and the candidate unit set via `unit_eligibility` |
| S3 | Carrier allocation | Split metered energy onto carriers |
| S4 | Baseline capacity, mix and vintage | Back-solve implied unit capacity, the carrier mix (A4), and plant age |
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

*Section last updated: 2026-09-07*

**Twenty-two entities.** Every one of them is defined here in full: fields, types, units,
keys and validation rules. Four are supplied by the CaRB3 stock model, seven by the
modelling team, two by scenario definition, one is derived at run time, six are optional
per-premise intelligence, and two carry defaults and the offline archetype layer.

| | Supplied by | Entities |
|---|---|---|
| §3.1–§3.1.3 | the CaRB3 stock model | `premise_record`, `premise_energy`, `premise_throughput`, `premise_connection` |
| §3.2–§3.6 | the modelling team | `activity_process_register`, `activity_process_duty_profile`, `carrier`, `unit`, `unit_input_output` |
| §3.7–§3.8 | scenario definition | `infrastructure_scenario`, `scenario_parameters` |
| §3.9 | derived at run time (A2) | `process_duty` |
| §3.10–§3.15 | optional per-premise intelligence (D10) | `premise_process_detail` and companions |
| §3.16–§3.17 | defaults and the offline layer | `activity_default_unit`, `archetype_coefficient` |

### 3.1 `premise_record` — the premise itself

The interface between the CaRB3 stock model and this model is three **required**
entities — this one, plus `premise_energy` (§3.1.1) and `premise_throughput` (§3.1.2) —
and one optional fourth, `premise_connection` (§3.1.3) — C11 bounds import against it, and
C12 bounds onsite generation against its `available_area`.
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
| `data_year` | integer | year | yes | — | **The base year.** The one year the model reads, on §3.1.1's base-year rule. Where it differs from the scenario's start year the offset is recorded and reported, never silently absorbed |
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

One row per premise per carrier **per year**. Replaces the fixed `energy_electricity` …
`energy_other` columns: a new carrier is a new row, not a schema change, and the
`energy_other` / `energy_other_carrier` pair disappears because every carrier now names
itself. Only the base year is read (D12); the rest is history.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `carrier_id` | string | — | yes | PK part | → `carrier`. The carrier as metered |
| `connection_id` | string | — | no | PK part → `premise_connection` | **Optional.** The metered connection this quantity came through (§3.1.3). Absent ⇒ the premise's default connection |
| `vector` | enum{electricity, gas, oil, coal, biomass, other} | — | yes | — | The grouping used to join `activity_process_duty_profile` (§3.3). Must be consistent with the carrier's `carrier_kind` (§3.4) |
| `quantity` | real | PJ/yr | yes | — | ≥ 0 |
| `data_status` | enum{measured, estimated, modelled, not_consumed} | — | yes | — | See the absence rule below |
| `data_year` | integer | year | yes | PK part | The year this quantity was measured. One row per carrier per connection **per year**. See the base-year rule below |
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
  is reported as having incomplete carrier coverage (§8).

The stock model should aim to state all five main vectors for every premise, whether by a
positive quantity or an explicit zero. Absence is a last resort, not the default.

**Rule (one row per carrier per connection per year).** `(premise_id, carrier_id,
connection_id, data_year)` is unique. Two meters on the *same* connection are one row —
meter-level detail below the connection belongs upstream. Two meters on *different*
connections are two rows, because the connection is a modelled object (§3.1.3) and the
difference is load-bearing.

Sites with a single connection may omit `connection_id` entirely and are unaffected.

**Rule (the base year, and history) — D12.** `premise_record.data_year` is the premise's
**base year**. Exactly one row per key carries it, and that row is the only one any
algorithm reads. Rows at other years are **history**: held for reconciliation, trend
evidence and reporting, and never consumed by the model (V25).

The rule binds differently on required and optional entities, because zero rows is the
normal case on the optional ones:

| Entity | Behaviour where no row carries the base year |
|---|---|
| `premise_energy` (this entity) | Substitute from the nearest year, see below |
| `premise_throughput` (§3.1.2) | Substitute from the nearest year, see below |
| `premise_measured_emissions` (§3.11) | §7.6's reconciliation is **skipped and reported** as `emissions_year_unmatched`. Never a rejection: the entity is optional intelligence, and rejecting the premise would discard the evidence |
| `premise_operating_profile` (§3.12), `premise_weekly_profile` (§3.14) | No profile is read, and the premise is **reported** as `profile_base_year_missing`. Never a rejection |

A duplicate `(key, year)` is rejected with reason `duplicate_year_row` on every entity above.

**Rule (a carrier metered off the base year substitutes; it does not vanish).** Where a
carrier has no row at the base year but has rows at other years, the **nearest** year is
used, ties resolving to the later one, and the substitution is recorded as
`year_evidence_tier = substituted` on the premise's output rows. Only a carrier with no row
at any year is "not assessed", and only then is the premise reported as having incomplete
carrier coverage (§8).

This is the §3.17 pattern applied to a new kind of evidence: `base_year` where the row sits
at `data_year`, `substituted` where it came from another year, `absent` where there is none.
A premise running on a substituted vintage must never be mistaken on paper for one running
on a base-year reading. Without this ladder the key change above would silently delete a
carrier that *was* assessed, merely on a different vintage, and A4 would back-solve no plant
for it.

**Rule (the base year is per premise; periods are not).** Stock data is mixed vintage, so
two premises may hold different `data_year` values while the model's periods are global. A
premise's base-year quantities are read as representing the scenario's start period, and the
offset in years is recorded on its output rows. Stating the offset is what stops a carbon
price at one period being applied to two different calendar years without trace.

#### 3.1.2 `premise_throughput` — physical output by carrier

One row per premise per product **per year**. Long for the same reason, and it lifts a real
limitation: the previous single `throughput_quantity` column could not represent a site
making more than one product, which paper, chemicals and food sites routinely do. Only the
base year is read (D12); the rest is history.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `carrier_id` | string | — | yes | PK part | → `carrier`. Must have `denominator_kind = mass` (D5) |
| `quantity` | real | Mt/yr | yes | — | > 0 |
| `data_year` | integer | year | yes | PK part | The year this throughput was measured. The base-year row, or its substitute, is what D5's mass denominators are computed from. See §3.1.1's base-year rule |
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

**The default duty of each process, per activity.** The activity-level default that A2
expands into a premise's `process_duty` (§3.9) wherever no site intelligence overrides it.
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
| `evidence_tier` | enum{measured, engineering, published_sec, fallback} | — | yes | — | The D10 ladder |
| `provenance` | string | — | yes | — | Citation |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried to output |

**Rule (shares sum to one).** For each `(carb3_activity, process_set_id, process_id)`,
`duty_share` must sum to 1.00 ± 0.015. The tolerance is the one
[`../notes/data/activity_process_energy_profile.csv`](../notes/data/activity_process_energy_profile.csv)
is already validated against, so a single check covers both tables.

**Rule (a heat duty must have a grade).** Where the carrier is gradeable, `grade_rank` is
non-nullable. A heat duty with no grade is invisible to C10's cascade: it can be served by
any grade at all, including one far below what the process needs, and the LP will take the
cheapest. This is the failure the data-migration plan flags as mode #6, and it fails silently.

**Rule (inheritance).** A non-default process set need not restate every row; where a
`(process_id, duty_family, grade_rank)` is absent it inherits the default set's value.

**A duty is not a fuel share, and the two must not both be supplied.** This entity states
which *duty* a process presents — a carrier at a grade. Which *fuel* serves that duty is
decided by the carrier balance, so supplying a fuel split as well would over-determine the
problem. The 490-row fuel split in
[`../notes/data/activity_process_energy_profile.csv`](../notes/data/activity_process_energy_profile.csv)
is therefore a **parity target for V1b** — the thing the model's chosen fuel mix is compared
against — and never an input.

### 3.4 `carrier`

Anything that flows and balances: a fuel, electricity, hydrogen, CO₂, or heat at a grade.

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

What converts between carriers. Fuel is not part of a unit's identity — it enters through
the unit's carrier bindings in §3.6.

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

**Abatement is a unit, not a cost differential against another unit.** A CCS train is a
unit that consumes a CO₂ carrier produced by its host and names that host in
`abates_unit_id`. It inherits the host's remaining life under D11 and strands nothing.

#### 3.5.1 `unit_eligibility`

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

Coefficients per unit per carrier, per unit of the unit's output. This entity is what makes
the carrier balance (C8) computable, and its **sign convention is load-bearing**: consumed
negative, produced positive.

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

Scalar and per-carrier series driving the objective and the constraints.

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

What a premise must produce, per period. Derived at run time by A2 from
`activity_process_register` and `activity_process_duty_profile`, refined by any
per-premise intelligence that exists (D10).

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

**Optional per-premise intelligence.** Where the actual processes at a site are known —
from a permit, an audit, a site visit, or an operator disclosure — they are stated here
and override both the default set and any named variant. Zero rows for a premise is the
normal case and means "use the register".

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `process_id` | string | — | yes | PK part | → `activity_process_register` |
| `valid_from_year` | integer | year | yes | PK part | The year this process started at the premise. ≤ `premise_record.data_year`. A future year is rejected with reason `process_change_in_future`: a *planned* change is not an observation |
| `valid_to_year` | integer | year | no | — | The year it stopped. Absent ⇒ still running. ≥ `valid_from_year` if present |
| `connection_id` | string | — | no | → `premise_connection` | **Optional.** Which electricity connection serves this process (§3.1.3). Absent ⇒ the default. This is what decides where electrified load lands |
| `known_capacity` | real | capacity units | no | — | > 0 if present. Units follow the process's denominator (D5): PJ/yr-equivalent for energy, Mt/yr for mass |
| `unit_id` | string | — | no | → `unit` | The specific installed unit, where known |
| `provenance` | string | — | yes | — | Citation: permit number, audit reference, disclosure |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried through to output |

**Rule (completeness, as at a year).** The rows valid at a given year are treated as the
premise's **complete** process list for that year. A partial list would silently delete
processes the site runs and misstate its energy balance. A premise with any rows must have
at least one row valid at the base year, or it is rejected with reason
`no_process_valid_in_base_year`. If only fragmentary knowledge exists, use a named
`process_set_id` instead.

**Rule (intervals do not overlap).** For each `(premise_id, process_id)` the validity
intervals must be disjoint. Overlap is two contradictory statements about the same process
in the same year, and the premise is rejected with reason `process_intervals_overlap`.

This is valid-time versioning, the pattern usually called a slowly-changing dimension of
type 2. The two rules above are its standard obligations, stated here so an implementer
recognises them rather than reinventing them.

**Rule (an unknown start year is stated, not left blank).** A permit or an audit commonly
names the processes a site runs without saying when each began, and `valid_from_year` is
required. Where the year is unknown, state `premise_record.data_year` and say so in
`provenance`. That is the reading which asserts least: the process is known to run in the
base year, which is the only year the model reads, and nothing is claimed about years the
evidence does not cover. This mirrors §3.15's residual cohort, and the alternative — every
data supplier inventing a convention — is what makes the field unusable.

**Rule (precedence).** Where `unit_id` is given, that unit is the premise's existing plant
for that process **for an interval valid at the base year**, and A4 does not choose between
candidates. A closed interval's `unit_id` describes plant the site no longer has. Where
`known_capacity` is given, it is used directly and A4 back-solves *utilisation* instead of
capacity (§A4).

**On history.** A closed interval is evidence, not an input to the optimisation. It does
two jobs. It tells A2 and A4 which rows to read, only those valid at the base year, so a
site that changed route mid-history is not back-solved into a blended plant that never
existed. And it explains a step change in `premise_energy`'s history (§3.1.1) that would
otherwise look like a data error. The optimisation starts from the base year and never
looks back.

**On vintage (D11).** When the plant was commissioned lives in `premise_process_vintage`
(§3.15), not here. The two answer different questions. This table says **which processes
the site ran, and when it ran them**; §3.15 says **when the plant serving a process was
installed**, one row per cohort. A works running two lines of the same process installed
decades apart — a 1998 kiln line and a 2016 one — has one row here and two there. No
interval on this table can express those two commissioning years, and averaging them is the
thing D11 exists to stop.

### 3.11 `premise_measured_emissions` — reported emissions, where they exist

**Optional per-premise intelligence.** For sites in UK ETS, or covered by permit
reporting or NAEI point-source data, measured emissions exist and are better evidence
than anything this model computes. They are used to **reconcile and calibrate** the
baseline, not to replace the computed value — see §7.6 for why that distinction is
forced rather than chosen.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `emission_year` | integer | year | yes | PK part | Multi-year. §7.6 reconciles against the base-year row; other years are a reported trend. A premise with rows but none at the base year is reported `emissions_year_unmatched`, never rejected. See §3.1.1 |
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

**Optional per-premise intelligence.** Two distinct things live here, and they answer
different questions. The **operating schedule** says when the site runs, which validates
the utilisation A4 derives. The **load statistics** say how peaky it is, which is what a
connection capacity is actually about (§5.6).

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `connection_id` | string | — | no | PK part → `premise_connection` | Peak and load-factor fields are **per connection** where a site has more than one. Absent ⇒ the default connection. Schedule fields are premise-wide and repeat |
| `profile_year` | integer | year | yes | PK part | The year the statistics were derived from. Closes the vintage-mismatch rule below, which until now named a field this entity did not have. The model reads the base year, per §3.1.1 |
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

**Rule (consistency, at like years).** Where both a peak and a load factor are supplied for
a vector, they must reconcile against that vector's annual energy in `premise_energy`
(§3.1.1) **at the same year** within 5%. The check runs at every year for which both sides
exist, not only the base year, because a divergence in a history year is still evidence
about the meter. Where no `premise_energy` row exists at a given `profile_year`, that year's
check is skipped and reported as `profile_year_unmatched` rather than failed. A premise with
no profile at the base year at all is a different condition and carries a different code,
`profile_base_year_missing` (§3.1.1):

$$\text{load factor} = \frac{E\,[\text{PJ/yr}] \times 277{,}778}{P^{\text{peak}}\,[\text{MW}] \times 8{,}760}$$

Divergence beyond that is reported as `profile_energy_inconsistent` — most often a
vintage mismatch between `profile_year` and `data_year`, which this entity can now state
rather than merely blame.

### 3.13 `process_load_shape` — how a process presents its demand

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
| `process_id` | string | — | yes | → `activity_process_register` | The process this describes |
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

**Optional, and deliberately small.** A representative **half-hourly week** — 336
points — captures the daily cycle and the weekday/weekend difference, which is most of
what shape means for a connection question, at ~2% of a full year's data. Supplied per
premise per vector **per year**, and per process only where sub-metering makes that real.
Only the base year is read (D12).

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `connection_id` | string | — | no | PK part → `premise_connection` | Half-hourly data arrives per MPAN, so a multi-connection site has one series per connection. Absent ⇒ the default |
| `profile_year` | integer | year | yes | PK part | The year the series was drawn from. One representative week per season **per year**; the model reads the base year, per §3.1.1 |
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

**Open dependency (§5.6).** C11's peak is rebuilt from this entity by the §5.6 method, and
**§5.6 is not written** — it is cited from here, from §3.12, from §4.2 and from C11 itself.
Whoever writes it must select the base year on §3.1.1's rule. Recorded here so the choice is
made deliberately rather than discovered through a wrong connection size.

---

### 3.15 `premise_process_vintage` — when the plant was installed (D11)

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

**Rule (the reference is to a process, not to a row).** This entity's `(premise_id,
process_id)` names a process identity at a premise, not one `premise_process_detail` row —
that table is keyed one field wider since it gained validity intervals (§3.10). Cohorts are
read only for processes valid at the base year. Plant serving a process the site has stopped
running is not incumbent capacity, and ageing it under D11 would strand an asset that is
already gone.

**Why a separate entity from §3.10.** `premise_process_detail` asserts a *complete* process
list as at a year; this table is keyed finer still, per cohort within a premise-process, and
asserts nothing about completeness. A premise may have vintage rows for its kiln and none
for its mills, and the mills simply fall to the next tier. Forcing the two into one table
would have made vintage all-or-nothing for a site, which is the opposite of how the evidence
actually arrives.

### 3.16 `activity_default_unit`

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
described by `unit_input_output` (§3.6), which gives every unit its full carrier vector.
Restating it here would be a second place for the same number to live, and they would
disagree. This entity says only *which* unit and *how much of the duty*; what the unit does
with that duty is the unit's own definition.

**Why an activity default rather than back-solving.** Inferring existing plant from metered
energy works only while every unit is a fuel variant of a demand device, because then the
fuel identifies the plant. It stops working once generation, storage and CHP exist: a CHP is
not inferable from a heat duty, since the same heat is equally consistent with a boiler.
Some of the supply side therefore has to be asserted, and this entity is where it is
asserted for premises with no site intelligence. Where `premise_process_detail` (§3.10)
gives real plant for a real site, that wins — the D10 ladder applies unchanged.

### 3.17 `archetype_coefficient`

What Tier A emits. **One constant per coefficient per unit** — not a function of a design
ratio, because a hybrid unit fixes the ratio (PD2).

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

**Rule (the archetype match reads the base year).** A premise is matched to an archetype on
its `premise_operating_profile` and `premise_weekly_profile` at the **base year**, on
§3.1.1's rule, and a substituted profile vintage is carried into `evidence_tier`. The match
decides ψ, β, χ and ε, which move C11 and the objective, so reading an arbitrary year here
would change a premise's answer without changing any input the reader can see.

---

## 4. Algorithms

*Section last updated: 2026-09-07*

> **Partially written.** The numbered pseudocode for A1–A9 is outstanding; the delivery plan
> names its owner. What each algorithm is responsible for, and the two rules that were open
> questions in the design, are settled and stated below.

Nine algorithms run the pipeline of §2.1. A1–A9 map onto the stages S1–S9 one for one.

| # | Algorithm | Responsibility |
|---|---|---|
| A1 | Ingest and validate premise records | Accept a premise record and its companions, apply the load-scope validation of §10, reject with reasons. **Resolve the base year (D12), apply §3.1.1's substitution ladder, and report `duplicate_year_row`, `profile_year_unmatched` and `emissions_year_unmatched`** |
| A2 | Expand premise to duties and candidate units | Resolve the process set, produce `process_duty` rows, and resolve the **candidate unit set** from `unit_eligibility` — including the `min_duty` screening that keeps minimum viable scale out of the LP. **Reads only the `premise_process_detail` rows valid at the base year (§3.10)** |
| A3 | Allocate premise energy onto carriers | Split metered energy across carriers. It does **not** allocate energy across processes: the carrier balance decides that. **Reads the base year only; history rows are carried to reporting untouched** |
| A4 | Back-solve implied capacity, carrier mix and vintage | Turn metered energy into installed unit capacity, the mix of carriers each unit burns (§4.1), and plant age under D11. **Back-solves from the base year only, reads only base-year-valid process rows, and carries a substituted carrier vintage into the mix evidence** |
| A5 | Apply the scenario | Attach prices, carbon price, infrastructure availability and the archetype coefficients ψ, β, χ, ε |
| A6 | Build the per-premise problem | Declare variables over units and carrier flows, assemble C1–C12 and the objective of §5.4 |
| A7 | Solve and extract | Solve, extract the pathway, and handle infeasibility by the relaxation ladder of §4.2 |
| A8 | Assemble output tables | Produce the per-premise pathway rows, each carrying its evidence tier |
| A9 | Aggregate to GB and compare | Roll up across premises; compare against ECUK and the GHGI |

### 4.1 A4 — the carrier-mix rule

**The problem.** Where a unit's identity pins its fuel, `energy → capacity` has exactly one
answer. Here a unit may burn a mix, so the same metered energy is consistent with many
`(capacity, mix)` pairs and the back-solve is under-determined. The mix must therefore be
pinned from evidence rather than solved for, in the D10 pattern used everywhere else:

| Tier | Evidence | Mix |
|---|---|---|
| 1 — `site_known` | `premise_process_detail` names the unit and its carriers | Observed. Fully determined |
| 2 — `carrier_bounded` | `premise_energy` gives site totals per carrier, and the premise runs one unit on that carrier | Determined by division |
| 3 — `activity_default` | Neither | The activity-default mix, carried as an assumption |

Tiers are tried in order and exactly one resolves. Where several units share a carrier at
tier 2, split by duty share and **record the split as an assumption** rather than presenting
it as measured. Every output row carries a `mix_evidence_tier` (§8), so a premise running on
an assumed mix is never mistaken on paper for one running on an observed one. V23 asserts
all three properties.

### 4.2 A7 — the relaxation ladder

An infeasible premise is relaxed in a fixed order, and every relaxation is reported. The
order is **C6 → C7 → C4b → C12 → C10 → C11 → C9 → C1**:

- **C12 (siting cap) relaxes first** of the three connection-and-physics constraints. It is
  the softest: an over-large PV array is an input-data problem about roof area, not a
  statement about the site's physics.
- **C10 (grade cascade) next**, and relaxing it must be loud — it means the model served a
  duty with heat that cannot physically reach that temperature. Report it; never silently
  absorb it.
- **C11 (connection capacity) last of the three**, because relaxing it asserts a network
  reinforcement that nobody has costed, which is exactly the error §5.6 warns about for
  peak.

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

**Activity is $z$, not $u$.** $u$ indexes units throughout this document, so the activity
variable takes a different letter. The separation is deliberate and is the kind of clash the
label rules in §1.4 exist to prevent.

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

**D11's survival function $\eta$ and mean remaining life $\bar R$ are parameters, computed
per unit before the problem is built.** That is what keeps D11 free of binaries.

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

**Carbon cost carries a $10^{-3}$ unit conversion.** Emission
factors are kt/PJ and the carbon price is £/t.

### 5.5 Constraints

**C1 — Duty satisfaction.** Each duty is met in each period, by units eligible for it:

$$\sum_{u \in U_q} z_{u,t} = D_{q,t} \qquad \forall q \in Q,\; t \in T$$

**C2 — Activity limited by available capacity.**

$$z_{u,t} \le a_{u,t}\,\gamma_u\,\alpha_u \qquad \forall u,\, t$$

**C3 — Capacity transfer between periods.**

$$a_{u,t} = e_{u,t} + \sum_{s \le t} n_{u,s}\,\mathbb{1}[\,s \le t \le s + \ell_{u,s} - 1\,]$$

with $e_{u,t} \equiv 0$ for $u \notin U^0$. An abatement unit expires with its host, not on
its own life.

**C4 — Incumbent ageing and early retirement (D11).** Incumbent capacity decays by the
survival function $\eta$, may be retired early against a stranding charge in $\xi$, and the
abatement rule keys on `abates_unit_id`: a unit whose host is still standing has not been
scrapped, so it attracts no stranding charge and inherits the host's remaining life.

**C5 — No building in the start year.** $n_{u,t_0} = 0 \;\; \forall u$.

**C6 — Unit stability.** A two-legged ramp limit on how fast a unit's activity may change
between periods. $\sigma$ is measured against deliverable output
$\bar z_{u,t} = a_{u,t}\gamma_u\alpha_u$, not against installed capacity.

**C7 — Known changes.** Announced commitments fix or bound $z_{u,t}$ or $a_{u,t}$.

**C8 — Carrier balance. This is the core change.** For every carrier at every period, at the
premise:

$$\sum_{u \in U} z_{u,t}\,\iota_{u,c} \;+\; \sum_{k \in \mathcal{K}} \big(m_{c,k,t} - x_{c,k,t}\big) \;=\; 0 \qquad \forall c \in \mathcal{C},\, t$$

with $m_{c,k,t} = x_{c,k,t} = 0$ where the premise has no connection carrying $c$. Every
carrier balances, including electricity: that is what makes onsite generation, CHP and
export expressible at all.

**C9 — Infrastructure availability (D7).** A unit whose carrier is unavailable at the premise
in a period cannot run, and where a cap is specified the premise's draw respects it. This
covers `biomethane` as well as hydrogen and CO₂ transport: biomethane's real constraint is a
shared catchment, which D2 forbids modelling per premise.

**C10 — Heat grade cascade.** A unit may serve a duty only at or below its output grade:

$$z_{u,t} = 0 \quad \text{for } u \in U_q \text{ where } \text{grade\_out}(u) < g\big(\text{carrier}(q)\big)$$

In practice this is enforced by **eligibility at load** rather than as a row in the LP, which
is why V19 is a load-scope test. Stating it as a constraint keeps §5 complete; implementing
it as a filter keeps the problem small.

**High grade may serve a low-grade duty, never the reverse.** A steam boiler at 150–400 °C
serves a 120 °C duty; a heat pump capped at 100 °C does not. Stating it as physics rather
than as a technology-to-process mapping is what lets a new unit be added without editing a
mapping table.

**C11 — Connection capacity.** Per connection, never summed across connections:

$$P^{\text{peak}}_{k,t} \;\le\; \overline{P}^{\text{imp}}_{k} + w_{k,t} + \sum_{u} \beta_u\,a_{u,t} \qquad \forall k \in \mathcal{K},\, t$$

and export bounded by $\sum_c x_{c,k,t} \le \overline{P}^{\text{exp}}_k$ after conversion to
power. Peak is rebuilt from the solved pathway by the §5.6 method, using
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
$(\texttt{unit\_id}, \texttt{carrier\_id})$.

---

## 6. Constraint disposition

*Section last updated: 2026-09-02*

**Not yet written.** Which constraints bind in practice, which are reported rather than
enforced, and the "reported comparison, not constraint" pattern used for the national
emissions cap and for minimum viable scale.

---

## 7. Emissions accounting

*Section last updated: 2026-09-07*

Emissions have two sources: combustion of a fuel carrier, and process chemistry tied to
physical throughput. Both are attributed to units, and the attribution rule below is what
keeps a carrier chain from being counted twice.

| # | Rule |
|---|---|
| 7.1 | **Two sources.** Fuel CO₂ is charged to the unit that **consumes the fuel carrier**, never to the unit that consumes the heat that fuel made. Process CO₂ is charged to the chemistry unit against its mass denominator (D5) |
| 7.2 | **Non-CO₂ gases** are tracked separately and **CCS never abates them** |
| 7.3 | **Biomass zero-rating is applied before capture**, so a biomass unit with CCS reports net-negative emissions rather than zero |
| 7.4 | **Direct versus indirect** is a property of the carrier — `carrier.is_indirect` (§3.4) — not a list held in code |
| 7.5 | **Reporting categories** are derived over units. Categories may overlap, and a unit may appear in more than one |
| 7.6 | **Reconciliation, at the base year.** Reported totals reconcile against `premise_measured_emissions` (§3.11) **at the base year** wherever a row exists there. Other years are a reported trend and never a calibration target. A premise with rows but none at the base year is reported `emissions_year_unmatched` and not reconciled (§3.1.1) |

**The rule that stops double-counting.** Emissions attach to the unit that consumes a
**primary** carrier — gas, coal, biomass, grid electricity. A unit consuming an
**intermediate** carrier — heat at any grade, steam, recovered heat — adds nothing. The heat
was already paid for upstream, and charging it again at the point of use would double-count
every boiler in the stock.

**Recovered heat is emissions-free, and that is a real result rather than an accounting
trick.** A kiln's reject heat carries no fuel, so a heat pump drawing on it inherits no
emissions; the fuel that made it stays charged to the kiln. This is precisely why heat
recovery abates, and it works only because the rule above is stated rather than assumed.
V22 asserts all three legs.

---

## 8. Output schema

*Section last updated: 2026-09-02*

**Not yet written.** One row per premise per unit per carrier per period, plus the cost and
network roll-ups. Every row carries its evidence tiers, including `mix_evidence_tier` from
A4 (§4.1) and the archetype tier from §3.17.

---

## 9. Performance and scale

*Section last updated: 2026-09-02*

### 9.1 Problem size

**Not yet written.** The per-premise variable and constraint count, computed from the unit,
carrier-flow and storage families.

### 9.2 Scale gates

Four gates must be passed, each measured before the work that depends on it is commissioned.

| Gate | Subject | Requirement |
|---|---|---|
| G1 | Single-premise solve | A representative premise solves within a stated wall-clock budget |
| G2 | Batch solve | A representative batch scales linearly under D2's independence |
| G3 | Full stock | The whole Factory-class stock completes within a stated budget |
| **G4** | **Tier A archetype build** | The full coefficient build completes within a stated wall-clock budget, **measured before the data build is commissioned** |

G1–G3 size the per-premise LP. **G4 exists because Tier A is the expensive new thing:**
hourly dispatch per archetype per hybrid sizing ratio is a few hundred archetypes times
roughly twelve hybrid units, so a few thousand hourly optimisations, each far heavier than
one annual LP. Learning that it is unaffordable early costs days; learning it late costs the
data build.

### 9.3 Determinism

Two identical runs must produce identical results. The tie-break key is lexicographic over
$(\texttt{unit\_id}, \texttt{carrier\_id})$, and the price-wedge rule of §5.5 removes the
degeneracy that would otherwise let the solver report either of two equal-cost answers
(V21).

---

## 10. Validation

*Section last updated: 2026-09-07*

### 10.1 Scopes

Every test declares a scope: **load** (asserted once when reference data is read),
**premise** (asserted per premise solve), **batch**, or **release**.

### 10.2 The carrier-equivalent configuration

V1b compares this model against the
[COMIT-parity baseline specification](archive/2026-08-19-carb3-site-decarbonisation-implementation.md)
on the same 1,026 sites. The comparison is only meaningful in a configuration where the two
can agree, and that configuration is defined here as precisely as §5.4 defines the pre-D11
cost baseline. **All five conditions hold together:**

1. **One carrier per unit.** Every unit's carrier mix is pinned to a single primary carrier,
   so a unit's identity determines its fuel.
2. **No storage.** No unit with `is_storage`, and no hybrid unit.
3. **No onsite generation.** No unit in $U^{\text{gen}}$.
4. **C10, C11 and C12 inactive.** No grade cascade, no connection limit, no siting cap.
5. **No export.** $x_{c,k,t} = 0$ for every carrier, connection and period, so the objective
   carries no negative term.

Under these five conditions the carrier balance reduces to duty satisfaction plus a fuel
price, which is exactly what the baseline computes.

### 10.3 Tests

| # | Scope | Blocking | Assertion |
|---|---|---|---|
| V1 | release | yes | The COMIT-parity baseline reproduces coupled-off COMIT. Asserted against the baseline specification, not against this one |
| **V1b** | release | yes | This model reproduces that baseline's objective and per-carrier energy on the same 1,026 sites, in the carrier-equivalent configuration of §10.2 |
| V2 | load | yes | `capacity_to_activity_factor` and `io_coefficient` round-trip per unit to 1e-6 |
| V4 | load | yes | Carrier consistency: every unit's declared carriers appear in `unit_input_output`, and profile uncertainty bands order correctly (R1–R3) |
| V5 | premise | yes | Emissions invariants over units, including biomass zero-rating **before** capture |
| V6 | premise | yes | No component of the objective is assumed non-negative — $Z^{\text{exp}}$ is genuinely negative |
| V10 | release | yes | Determinism: two identical runs agree, under the §9.3 tie-break |
| V11 | load | yes | Process sets resolve to exactly one tier per premise |
| V12 | premise | yes | Capacity bounds hold, including the siting cap |
| V16 | batch | yes | Connection peak is rebuilt correctly from the solved pathway |
| V17 | premise | yes | Vintage and stranding per unit. An abatement unit inherits its host's remaining life through `abates_unit_id`, and strands nothing while the host stands |
| **V18** | premise | yes | **Carrier balance closes to 1e-6 at every carrier node, every period** |
| **V19** | load | yes | No unit is eligible for a duty above its `grade_out`. Asserted at load, not per premise |
| **V20** | load | yes | Five legs, all on the archetype and hybrid-unit data — see below |
| **V21** | load | yes | The price wedge $p^{\text{exp}} < p^{\text{imp}}$ holds strictly for every carrier and period |
| **V22** | premise | yes | Emissions attribution closes across a carrier chain — three legs, see below |
| **V23** | load + premise | yes | A4's carrier mix resolves to exactly one tier per unit, tiers are tried in order, and `mix_evidence_tier` appears on every output row |
| **V24** | load + premise | yes | One measured row per key at the base year or a recorded substitution; no duplicate `(key, year)`; the optional entities of §3.1.1's table report rather than reject |
| **V25** | premise | yes | **History is never read.** Adding history rows at years both **before and after** the base year leaves every §5.3 parameter, every constraint coefficient, the solution, **and every reported reconciliation (§7.6)** identical to 1e-9 |
| **V26** | premise | yes | Validity intervals per `(premise_id, process_id)` are disjoint, at least one row is valid at the base year, and A2, A4 and §3.15's cohort read touch no row outside it |

**V20's five legs.**

- (a) ψ, β, χ ∈ [0, 1] and ε > 0 for every unit that declares them.
- (b) Every hybrid unit's `unit_bill_of_materials` shares sum to 1 and reconcile to its capex
  and capacity.
- (c) Every hybrid unit's lifetime is levelised over its components — no component lifetime
  exceeds the unit's $L$ without a replacement charge inside the annuity.
- (d) Every unit with `is_storage` and no hybrid parent has β set and ψ, χ, ε unset, since
  standalone storage may only earn through C11.
- (e) Across the hybrid units sharing a pairing, each coefficient is **concave in the sizing
  ratio**. This is what makes LP interpolation between them err on the safe side, and it
  needs at least three ratios per pairing to be meaningful.

**V22's three legs.**

- (a) Total emissions equal the sum over units consuming **primary** carriers only. No unit
  consuming an intermediate carrier contributes.
- (b) A chain `gas → boiler → heat@150-400C → dryer` books exactly the boiler's fuel, once.
- (c) A recovered-heat leg contributes zero, and the fuel that produced it remains charged to
  the rejecting unit.

**V25 runs in both directions, and that is the point.** History must be added at years
**before and after** the base year. A test that only adds older years passes against an
implementation that silently reads `max(data_year)`, which is the most natural wrong thing to
write. Its scope is the whole built problem, not just A3 and A4: the archetype match (§3.17),
§7.6's reconciliation and, when it is written, §5.6's peak all read a year.

### 10.4 What each new mechanism is guarded by

```
  MECHANISM                             GUARDED BY        SCOPE
  ─────────────────────────────────────────────────────────────────
  carrier balance closure          ───▶ V18               premise
  heat grade cascade (C10)         ───▶ V19               load
  archetype coefficients ψ/β/χ/ε   ───▶ V20 (a)           load
  hybrid unit bill of materials    ───▶ V20 (b)           load
  hybrid unit capex levelisation   ───▶ V20 (c)           load
  standalone storage earns only β  ───▶ V20 (d)           load
  hybrid coefficient concavity     ───▶ V20 (e)           load
  emissions attribution (§7)       ───▶ V22               premise
  A4 carrier-mix tiering           ───▶ V23               load+premise
  A7 ladder rungs C10/C11/C12      ───▶ V23 + A7 report   premise
  Tier A build cost                ───▶ G4                release
  export price wedge               ───▶ V21               load
  connection peak (C11)            ───▶ V16               batch
  siting cap (C12)                 ───▶ V12 + V20         premise
  unit vintage / stranding         ───▶ V17               premise
  parity against the baseline      ───▶ V1b               release
  baseline parity against COMIT    ───▶ V1                release
  determinism under the tie-break  ───▶ V10               release
  base-year selection (D12)        ───▶ V24               load+premise
  off-vintage carrier substitution ───▶ V24               premise
  history isolation from the model ───▶ V25               premise
  process validity intervals       ───▶ V26               premise
  §5.6 peak selects the base year  ───▶ (none, §5.6 unwritten)
  §1.4 label ranges match the spec ───▶ (none, checked by hand)
```

**Two rows carry no guard, and say so rather than hiding it.** §5.6 does not exist, so
nothing can assert which year its peak method reads; that is closed when §5.6 is written.
And the label ranges in §1.4 have no automated check for this document: `label_families()`
runs only from the interface-doc generator, which is switched off for this specification
while §8 is unwritten, and even where it runs it checks family *presence*, not range values.
Widening a range is a manual step in the same commit as the label.

### 10.5 Failure modes and their handling

| # | Failure | Guarded by | Handling |
|---|---|---|---|
| 1 | Carrier balance leaks — a unit produces a carrier nothing consumes and it silently vanishes | V18 | Premise assertion |
| 2 | A duty has no eligible unit after screening, so the premise is infeasible | A7 ladder | Relaxation in the §4.2 order, reported |
| 3 | A hybrid unit's capex is not levelised over component lifetimes, so C3's capacity window and C4's stranding charge both key on a wrong $L$ | V20 (c) | Load assertion |
| 4 | Export price ≥ import price in a scenario, giving non-reproducible onsite capacity | V21 | Load assertion |
| 5 | A premise matches no archetype | §3.17 `evidence_tier` | Substitution ladder: `fitted` → `substituted` → `default`, recorded on every output row |
| 6 | Heat grade unset on a process, making C10 vacuous so a heat pump can fire a kiln | V19 | Load assertion, and `grade_rank` is non-nullable wherever the carrier is gradeable (§3.3) |
| 7 | The option-to-unit join is broken in the reference data | `make data-check` | Load-time validator |
| 8 | ε unset on a flexible-load hybrid, so `electrolyser_battery` is strictly dominated by a bare electrolyser and never built | V20 (a) | Load assertion, and ε is non-nullable on flexible-load hybrids (§3.17) |
| 9 | Two years of the same carrier are averaged, or the later one silently wins, so the back-solve runs on a snapshot that never existed. Or a carrier metered on a different vintage is read as absent, and the site's baseline emissions fall | V24 + V25 | Load and premise assertions, plus §3.1.1's substitution ladder |
| 10 | A premise that changed process route mid-history is back-solved as a blend of both routes | V26 | Premise assertion; A2 and A4 read only base-year-valid rows (§3.10) |

---

## 11. Phasing

*Section last updated: 2026-09-02*

**Not yet written.** Which capabilities land in which phase, and the exit criteria for each.

---

## 12. Reference map

*Section last updated: 2026-09-02*

**Not yet written.** Where each reference table lives, who owns it, and what validates it.

---

## 13. Worked examples

*Section last updated: 2026-09-02*

**Not yet written.** Two examples are planned and both are needed.

- **A cement works** — one chemistry node at the top grade, a mass denominator (D5), tier-1
  vintage, stranding and a CCS capture unit. It exercises the parity case: everything the
  model must not get wrong.
- **A food and drink site** — `IFDLTH`, `IFDSTM`, `IFDDRY`, `IFDREF` and `IFDMOT`. It
  exercises the mechanism: eight fuel-variant rows collapsing to three units, a 120 °C duty
  with boiler, CHP, heat pump and electric resistance competing under C10, a reject-heat leg
  feeding a heat pump, CHP producing heat **and** electricity into the carrier balance, and
  PV, a battery and a connection limit.

**Cement alone is not sufficient**, and the reason is structural rather than a matter of
taste: cement carries exactly two process codes, `ICMCLK` and `ICM`. There is no `LTH`, no
`STM`, no `DRY` and no `SPC`, so nothing cascades, the candidates differ by *fuel* rather
than by device, no low-grade duty exists to receive reject heat, and CHP appears only fused
inside bundled capture rows. A worked example on a cement works would demonstrate everything
except the mechanism this model exists for.
