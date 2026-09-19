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

*Section last updated: 2026-09-17*

### 1.1 What this document is

A build specification: one record per premise in, a least-cost decarbonisation pathway out,
solved independently per premise. It states **what to build**, not how to build it in a
particular language.

**Validation chain.** The model's results are anchored to COMIT, the R optimisation model
that runs today, by one comparison. **V1** asserts that a single run of COMIT with its
coupling constraints switched off exists and is frozen: its tables, and a manifest naming
the workbook hash, the R package commit, the solver version and the switches used. **V1b**
asserts that this model reproduces that run in the *carrier-equivalent configuration*
defined in §10, with COMIT's technology rows related to this model's units through the
data migration's lineage table. The R run is a comparison point, not ground truth. The
[COMIT-parity baseline specification](archive/2026-08-19-carb3-site-decarbonisation-implementation.md)
is not built; it stays as the document that says what the R run's tables mean.

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
| `V1`–`V33` | Validation tests | §10 |
| `G1`–`G4` | Scale gates | §9 |
| `D1`–`D16` | Design decisions | §1.6 |
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

Sixteen decisions fix the shape of the model. Everything in §2–§13 is written inside them,
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
| **D13** | **One primary carrier per unit.** A unit's fuel is part of its identity: `boiler_gas` and `boiler_hydrogen` are two units, not one unit with two bindings | Capex, lifetime, efficiency, availability year and minimum scale become per-fuel attributes, which they physically are; `unit_eligibility` can cap one fuel without capping another; §10.2's carrier-equivalent configuration stops being a special setup and becomes how the library always works | The library roughly doubles, from ~40 units to ~98 before hybrids. The collapse across *sectors* — one boiler for a dairy and a paper mill — is untouched, and it is the larger saving |
| **D15** | **Every emission is a carrier.** Combustion CO₂ joins process CO₂ on the balance, so emissions are produced by units, consumed by capture, and vented through disposal | Capture needs no special case — a train simply consumes a carrier; the carbon price attaches to what is actually vented; biomass zero-rating and net-negative capture fall out of the carrier set instead of an accounting rule; §7 becomes a readout of the balance rather than a parallel calculation | Three more balance nodes per period, and fuel CO₂ coefficients must be **derived** at build time from the scenario's factors rather than declared, because a factor may vary by period |
| **D16** | **An internal product is a carrier, not a duty, and the site boundary is a property of the carrier.** `carrier` gains required `may_import` and `may_export` flags (§3.4); a `product` a site makes and consumes itself carries both false, presents no `process_duty` row (§3.9), and reaches its consumer through C8 by way of $z^{\circ}$ | The double-count between C1 (duty satisfaction) and C8 (carrier balance) on a product a downstream unit draws disappears — the two constraints stop competing for the same tonne. The boundary becomes data rather than convention, so a site's Sankey is derivable from §8's solved rows: imports on the left, carrier nodes in the middle, and on the right the four ways a stream ends — a duty delivered, an export, a disposal $d_{c,t}$, or a loss inside a unit | Two more required fields on every `carrier` row, and a process may now exist with units, vintage and a `premise_process_detail` row but no duty, so anything that counted duties as a proxy for processes has to stop |
| **D14** | **Emissions attach once, at the fuel. Any per-carrier figure is a reporting allocation that sums back to it** | A CHP's electricity can carry a defensible intensity without the same molecules being charged twice; the grid factor applies to imports only, so self-generation stops being counted as if it came off the grid | An allocation convention must be chosen and defended (§7.7), and two numbers now exist for one emission — accounted and allocated — which must never be added together |

Five have the widest reach in this document:

- **D2 — per-site independent solves.** No constraint may couple two premises. Anything
  needing cross-site information becomes a scenario input or a post-hoc comparison. This is
  structural; nothing in this document can undo it.
- **D5 — hybrid denominators.** Energy (PJ) by default, mass (Mt) for chemistry. This is
  also the line the unit spine splits on (§3.2).
- **D10 — tiered site intelligence.** Known site detail replaces activity defaults outright,
  and every output row carries its evidence tier.
- **D11 — plant has an age.** Ageing, early retirement and the stranding charge attach
  to units (C4).
- **D13 — one primary carrier per unit.** A unit's fuel is unambiguous by construction, and
  §3.5, §3.6, §4.1 and §10.2 all rest on it.

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

*Section last updated: 2026-09-17*

**Twenty-six entities.** Every one of them is defined here in full: fields, types, units,
keys and validation rules. Four are supplied by the CaRB3 stock model, nine by the
modelling team, two by scenario definition, one is derived at run time, eight are optional
per-premise intelligence, and two carry defaults and the offline archetype layer.

| | Supplied by | Entities |
|---|---|---|
| §3.1–§3.1.3 | the CaRB3 stock model | `premise_record`, `premise_energy`, `premise_throughput`, `premise_connection` |
| §3.2–§3.6 | the modelling team | `activity_process_register`, `activity_process_duty_profile`, `activity_process_energy_share`, `carrier`, `unit`, `unit_abatement_host`, `unit_input_output` |
| §3.7–§3.8 | scenario definition | `infrastructure_scenario`, `scenario_parameters` |
| §3.9 | derived at run time (A2) | `process_duty` |
| §3.10–§3.15 | optional per-premise intelligence (D10) | `premise_process_detail`, `premise_process_energy`, `premise_process_unit` and companions |
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

**A row is a duty or it is evidence, and `may_export` decides which (D16).** Where the
`carrier_id` is a `product` with `may_export` true, the row is the premise's **duty** on that
product under D5 — a cement works' 1.13 Mt/yr of cement is what C1 makes it produce. Where the
carrier is an **internal** product (`may_export` false), there is no duty to state (§3.9) and
the row is **evidence** instead: A4 cross-checks its back-solved capacity and implied output
against it (§5.1), and §7.6-style reconciliation reports it, but nothing in the LP is pinned by
it. The row is still worth carrying, and a premise should still state it.

**`missing_throughput` therefore applies to exported products only.** A premise whose only
mass-denominated process makes an internal product has its activity fixed by C8 through
$z^{\circ}$, not by a duty, so a missing row costs a cross-check rather than the problem. A1
reports it, and does not reject.

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
and adding them grants headroom the load cannot physically reach. C11 (connection capacity) is
written per connection for exactly this reason.

**A delivered fuel has no connection row, and needs none.** This entity covers *networked*
carriers — electricity, natural gas, hydrogen, CO₂ transport — where a physical connection
bounds the flow. Coal, waste-derived fuel, fuel oil and biomass arrive by road or rail, so they
carry no row here and are imported at **site level**, $m_{c,t}$ (§5.2), outside C11 altogether.
`carrier.may_import` (§3.4) is what says the premise may buy them at all; the absence of a
connection row says only that no capacity limit applies.

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

**What a process is.** A process is **one unit of demand**: equipment whose duties rise and
fall together because the same thing drives them. It is not a room, not a cost centre and not
a fuel. A paper machine's dryer section is one process because its steam and its drive power
both follow tonnes of paper; a site-overheads bundle is not, because its space heating follows
the weather and its small power does not.

**Drawing more than one vector is a flag, not a verdict.** §3.3.1 keys energy share on
`(process, vector)`, so a process taking both gas and electricity is visible in the data. That
alone says nothing about whether it is one process. Each such process resolves to exactly one
of three cases:

| Case | What is true | What the register does | Where the vector split is expressed |
|---|---|---|---|
| **Coupled** | Two duties, one driver. Steam and drive power on a paper machine; evaporator steam and vacuum pumps on a salt works | **One process.** One §3.3 row per duty | §3.3 `duty_share`, from a **sourced technical ratio** |
| **Uncoupled** | Two duties, different drivers. Space heating against small power; cleanroom reheat against fan power | **Split into separate processes**, one per driver | Not expressed anywhere — each part has one duty at 1.00 |
| **Alternative technologies** | **One** duty, served two ways. Oxy-fuel and plasma both cutting steel | **One process, one §3.3 row at 1.00** | §3.16 `activity_default_unit.default_share`, across the eligible units |

**The test is the driver, and §3.13 already names the drivers.** Two candidate duties are
coupled when they would carry the same `shape_class` and the same `seasonality`. Different
classes mean different drivers, so the duties cannot share a single annual share and the
process must be split — a `seasonal` reheat duty and a `standing` fan duty in one process
force one §3.13 row to describe both, and it can only be wrong about one of them.

**Splitting must fall on the coupling boundary, or it moves the invention rather than removing
it.** Splitting a site-overheads bundle into a heating process and an electrical process needs
no new evidence, because §3.3.1's existing vector shares already size both halves. Splitting
the electrical half further into lighting, small power and compressed air does need evidence,
because nothing in the input data distinguishes them. Split to the point where each part has
one driver and stop.

**Rule (a split process needs a crosswalk target).** Splitting changes `process_id`, which is
the key of §3.3, §3.3.1, §3.9, §3.10, §3.13, §3.16, `unit_eligibility` and the COMIT
crosswalk. The last is the binding one: V1b compares against COMIT's process commodities, and
several sectors have no node for a separated duty — `IFD`, `INF` and `IIS` carry no space-heat
commodity at all. A split whose parts cannot both be crosswalked must either map both parts to
the original node or be recorded as a known V1b divergence.

**The vector count is a flag, and it is blind in one direction.** It finds a process whose
duties sit on *different* fuels. It cannot find a process whose second duty sits on **the same
fuel** — one gas supply feeding both an 85 °C steriliser and a 45 °C washdown, or both a
pasteuriser at band 2 and a UHT plant at band 3. Nothing in the input data distinguishes those,
so no mechanical test will ever raise them; only someone reading the process description will.
**Five such processes are known and listed** in
[notes/20](../notes/20_reference_data_open_questions.md) item 1b. A process whose §3.3 rows
carry a single duty family at 1.00 is therefore *unexamined*, not *confirmed simple*.

> **Nothing validates this classification today.** There is no `coupling` field on the
> register and no check that a multi-vector process has been examined. Adding one is the
> obvious enforcement point and is open — see
> [notes/20](../notes/20_reference_data_open_questions.md). Until then the classification
> lives in each row's `provenance`, and a process that was never examined looks exactly like
> one that was.

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

**Rule (a multi-duty share is a technical ratio, never the process's fuel mix).** §3.2 admits
more than one duty on a process only where the duties are *coupled* — one driver, two
services. Their `duty_share` is then a technical coefficient of that operation, and it must
come from a source that measures the operation: steam and drive power per tonne of paper, say.
It must **not** be back-derived by renormalising the process's own vector shares from §3.3.1.
That restates the energy split as though it were a duty fact, makes the duty structure follow
the activity-average fuel mix at every premise, and can never be tiered above `fallback`. It
is also the failure this table is most exposed to, because the arithmetic is available and
looks plausible: **twenty-two rows of the current reference build do exactly this** — see
[notes/20](../notes/20_reference_data_open_questions.md).

**Where two technologies serve one duty, they do not become two duties.** Oxy-fuel and plasma
both cut steel; the choice between them is a unit choice, and its share belongs in §3.16. The
failure mode is filing the electric variant under `MOT` because its vector is electricity,
which leaves the thermal duty correctly *typed* but **undersized**, and the motive duty
overstated by the same amount. It is quieter than a missing duty — C10's cascade still sees a
duty at the right grade, so nothing fails — and the error surfaces only as a site that
electrifies too little heat. A process of this shape is where the temptation to key §3.3 on
`vector` does the most damage: it would make the misfiling systematic rather than accidental.

**A duty is not a fuel choice, and the two must not both be supplied.** This entity states
which *duty* a process presents — a carrier at a grade. Which *unit*, on which fuel, serves
that duty in a given period is decided by the carrier balance, so supplying a forward fuel
split as well would over-determine the problem.

**But how much energy each process takes is a different question, and it is an input.**
§3.3.1 holds it. The distinction is between a marginal and a conditional, and conflating them
is what left A2 with no way to size a premise's duties:

| | Claim | Status |
|---|---|---|
| **Marginal** — §3.3.1 | Of this premise's gas, what share goes to the dryer | A demand-side fact about the site's layout. **An input** |
| **Conditional over time** | In 2040, is that duty served by gas, hydrogen or a heat pump | What C8 decides. **V1b's parity target**, never an input |

Reading the marginal over-determines nothing: at the base year each carrier's site total is
pinned by `premise_energy` on both sides of the comparison anyway, because C8 forces import to
equal consumption. What it fixes is the duty structure, which is what drives every later
period.

### 3.3.1 `activity_process_energy_share` — how much energy each process takes

**The activity-level default share of a premise's metered energy, per process per vector.**
Populated by
[`../notes/data/activity_process_energy_profile.csv`](../notes/data/activity_process_energy_profile.csv) —
490 rows covering 359 of the register's 376 processes, with provenance per row.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `carb3_activity` | string | — | yes | PK part | → `activity_process_register` |
| `process_set_id` | string | — | yes | PK part | → `activity_process_register` |
| `process_id` | string | — | yes | PK part | → `activity_process_register` |
| `vector` | enum{electricity, gas, oil, coal, biomass, other} | — | yes | PK part | The grouping `premise_energy` (§3.1.1) carries on every row |
| `energy_share` | real | fraction | yes | — | ∈ [0, 1]. Share of the premise's quantity **of this vector** taken by this process |
| `share_low` | real | fraction | no | — | ≤ `energy_share` if present |
| `share_high` | real | fraction | no | — | ≥ `energy_share` if present |
| `evidence_tier` | enum{measured, engineering, published_sec, fallback} | — | yes | — | The D10 ladder |
| `provenance` | string | — | yes | — | Citation |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried to output |

**Rule (shares sum down the process column, per vector).** For each
`(carb3_activity, process_set_id, vector)`, `energy_share` must sum to 1.00 ± 0.015. This is
the opposite axis from §3.3's rule, which sums *across duties within* a process, and the two
are independent checks.

**Rule (keyed on vector, not carrier).** Which share of a site's gas the dryer takes does not
depend on whether that gas is natural gas or biomethane. Keying on `vector` also keeps the
table at hundreds of rows rather than thousands, and it is the same grouping §3.1.1 already
requires every `premise_energy` row to carry.

**Rule (a process consuming several sources gets several rows).** One row per
`(process, vector)`. A cement kiln takes all of the coal, gas, biomass and waste fuel, a fifth
of the oil and a fifth of the electricity — six rows. **104 of the 359 covered processes carry
more than one vector**, so multi-source processes are the ordinary case and not an exception.

**Rule (absence is zero, and that is safe here — unlike §3.1.1).** Because the shares close to
1.00 per vector, a process with no row for a vector unambiguously takes none of it. There is
no "not assessed" reading to confuse it with. **The corollary is that a coverage gap is
silent**: seventeen register processes carry no row at all, and the model gives them zero
energy. At `Cement Works` those are `clinker_cooling` and `site_services`, so a clinker cooler
is assigned no electricity while §3.13 classes it `flat` with `duty_factor` 1.00. Closing the
seventeen is reference-data work, and until it is done the `MOT` duties are understated and
the covered processes correspondingly overstated.

**Rule (renormalisation for absent processes).** Where a premise does not run one of the
activity's processes — because `premise_process_detail` (§3.10) omits it, or
`activity_process_register.is_optional` marks it absent — that process's share is removed and
the remaining shares for that vector are renormalised to 1.00. A vector whose every consumer
is absent renormalises to nothing and its quantity must be zero, or the premise is reported
`energy_share_unallocated`.

**This entity is also §4.1 tier 3's source.** The `activity_default` carrier mix that A4 falls
back to when neither site knowledge nor division determines it is read here, and until now
§4.1 named no table at all.

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
| `emission_factor_source` | string | — | no | — | → `scenario_parameters` series. Required on a `primary` carrier |
| `biogenic_fraction` | real | fraction | no | — | ∈ [0, 1]. Share of the carrier's carbon that is biogenic. Required where > 0; absent reads as 0. Splits a fuel's derived CO₂ between the fossil and biogenic carriers (D15, §7.3) |
| `carbon_charge` | enum{charged, zero_rated} | — | no | — | Set on `emission` carriers only. `zero_rated` is what makes biogenic CO₂ free to vent and a **credit** to capture (§7.3) |
| `denominator_kind` | enum{energy, mass} | — | yes | — | D5 |
| `may_dispose` | boolean | — | yes | — | Whether $d_{c,t}$ exists for this carrier (§5.2). **Derived from `carrier_kind`, not free**: true for `intermediate` and `emission`, false for `primary` and `product`. Stated as a column so the LP builder reads it rather than re-deriving it |
| `may_import` | boolean | — | yes | — | Whether the carrier may cross the site boundary inwards (D16), and the only thing that decides whether an import exists. A **networked** carrier a `premise_connection` row carries takes the connection-indexed $m_{c,k,t}$; a **delivered** fuel with no connection row takes the site-level $m_{c,t}$ (§5.2). True on every `primary` fuel and on `electricity`; false on `intermediate`, `emission` and `product` carriers |
| `may_export` | boolean | — | yes | — | Whether the carrier may cross the site boundary outwards (D16). $x_{c,k,t}$ is declared only where this is true **and** a `premise_connection` row carries $c$ (§5.2) — an export always goes onto a network. True on `electricity`, on a `product` with an outside market, and on `co2_captured`, which leaves through the CO₂ transport network under C9 (infrastructure availability); false on `intermediate`, `emission` and internal `product` carriers |

**Grades are carriers, not an attribute of one.** `heat@60-150C` and `heat@150-400C` are two
`carrier` rows with different `grade_rank`. This is what lets C8 balance them independently
and C10 order them, without a special case in either.

**`carrier_kind` is load-bearing for emissions.** Fuel emissions attach only to units
consuming a `primary` carrier that is **not** `is_indirect`. A unit consuming an
`intermediate` adds nothing, because the fuel was already charged upstream. Getting this wrong
double-counts every boiler in the stock.

**The pair `(carrier_kind, is_indirect)` is the whole test, and the role is not part of it.**
`primary` and not indirect means the carbon is released here, so §3.6's A6 derives an emission
row for it — whether the unit declares it as its `fuel_input` or as a second fuel on
`aux_input`. `primary` and indirect, which today is `electricity` and `hydrogen`, means the
emission belongs at the import instead (§7.8). `intermediate` means it was charged upstream.
Reading the role rather than the carrier is the error §3.6 records: it would silently
zero-rate every secondary fuel in the library.

**Rule (boundary). The site boundary is a property of the carrier, and it has four exits.**
`may_import` and `may_export` say which carriers may cross it, and every stream in a solved
premise ends in exactly one of four ways: **delivered to a duty** ($z_{u,q,t}$ against C1, duty satisfaction),
**exported** ($x_{c,k,t}$, only where `may_export`), **disposed of** ($d_{c,t}$, only where
`may_dispose`) or **lost inside a unit**, as the shortfall between a unit's input coefficients
and its outputs in §3.6. Nothing else terminates a stream, which is why a Sankey of a site is
derivable from §8's solved rows plus these two flags alone — imports on the left, units and
carrier nodes in the middle, the four endings on the right — rather than needing a separate
diagram model.

**A carrier with both flags false is internal to the site**, and that is the case D16 exists
for. An `intermediate` carrier has always been internal, and so has an `emission` carrier. What
D16 adds is that a **`product`** may be internal too: a cement works makes clinker and grinds it
itself, so `clinker` is `may_import` false and `may_export` false, while `cement` is false and
true. An internal product presents no duty (§3.9) and reaches its consumer through C8 (carrier
balance) by way of
$z^{\circ}$ — see §5.5. Buying clinker in is out of scope, and the flag is where that is
recorded.

**Three emission carriers, and the split is load-bearing (D15).** Emissions are produced,
balanced, captured and vented like anything else that flows:

| `carrier_id` | Origin | `carbon_charge` | Why separate |
|---|---|---|---|
| `co2_process` | Chemistry, against a mass denominator (D5) | `charged` | Cannot be touched by fuel switching, and §7.6 reconciles it against measured data separately |
| `co2_fuel_fossil` | Combustion of fossil carbon | `charged` | The ordinary case |
| `co2_fuel_biogenic` | Combustion of biogenic carbon | **`zero_rated`** | Vented it is free (§7.3); captured it is a **credit**, which is what makes bioenergy with capture net-negative rather than merely zero |

A capture unit consumes these and produces `co2_captured`, which leaves the site through the
CO₂ transport network under C9. Anything not captured leaves through $d_{c,t}$ (§5.2), and
**that disposal is the emission event** — it is what the carbon price is charged on and what
§7 reports.

**A duty's carrier is a service, never a fuel.** If a motor duty's carrier were `electricity`,
the motor would consume and produce the same carrier and C8's node at that carrier would be
circular. Every duty family therefore resolves to a carrier that represents the *service*:

| Duty family | Carrier | Kind | Boundary |
|---|---|---|---|
| `LTH`, `HTH`, `STM`, `DRY`, `SPC` | graded heat, `heat@band` | intermediate, gradeable | **internal** — `may_import` and `may_export` both false |
| `MOT` | **`motive_power`** | intermediate, not gradeable | **internal** |
| `REF` | **`cooling`** | intermediate, not gradeable | **internal** |
| `OTH` | resolves to whichever of the above the underlying service is | — | **internal** |

Every service carrier is internal by construction: a service is produced and consumed on the
premise, so neither $m$ nor $x$ is ever declared on one. A duty may also sit on a `product`
carrier, but only where `may_export` is true (§3.9).

Compressed air is a candidate for a carrier of its own rather than `motive_power`: it has real
distribution losses and is storable, and motive power is neither. Deferred until the duty
families are populated.

**Two of the twelve families are not energy services and take no carrier.** `NEUOTH` is
non-energy use — fuel consumed as feedstock, which presents no duty and must not be charged
combustion emissions (§7.1). `HRS` is `IISHRS`, hot rolling, which is one of the fourteen
**chemistry** nodes and is keyed per process, not per family. Both are listed among the twelve
in the architecture document and neither belongs there.

**The grade band set is not declared anywhere, and it decides eligibility.** `grade_rank` and
`grade_label` are fields; the list of bands is reference data nobody owns. Where the lines are
drawn decides which units are eligible for which duty — two bands let one heat pump serve an
80 °C duty and a 120 °C one, four bands separate them. Owned by the duty-family and heat-grade
data work.

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
| `area_per_capacity` | real | m² per capacity unit | no | — | ≥ 0. **Set only on area-bound units** — PV, solar thermal, anything sited against roof or land. Unset means the unit takes no area and is outside C12: a CHP is compact plant and leaves it unset |
| `emissions_released` | real | fraction | yes | — | ∈ [0, 1]. Fraction **not** captured |
| `min_viable_scale` | real | capacity units | no | — | Screening threshold, applied in A2 — **never a binary** |
| `load_shape_override` | string | — | no | → `process_load_shape` | **By exception only.** The shape belongs to the process (§3.13); a unit overrides it only where the device genuinely changes the draw |
| `is_hybrid` | boolean | — | yes | — | If true, `unit_bill_of_materials` rows must exist |
| `draws_ambient` | boolean | — | yes | — | True where the unit takes energy from ambient air, ground or water — outside the carrier set by §3.4. Exempts the unit from V2's energy-closure leg (§3.6) |
| `provenance` | enum{comit_reuse, bref, proxy} | — | yes | — | D6 |
| `confidence` | enum{high, medium, low} | — | yes | — | D6 |

**The spine is split, and the split follows D5.** Energy services (`LTH`, `HTH`, `STM`,
`DRY`, `MOT`, `SPC`, `OTH`, `REF`, and four more) are family-keyed: one `boiler` serves a
dairy and a paper mill alike. Chemistry (`ICMCLK`, `IHVC`, `IISPIR` and eleven more) is
node-keyed, because a cement kiln is not a generic device. Sector specificity lives in
`unit_eligibility`, not in the unit's identity.

**Fuel is part of the identity, though — D13.** A unit is keyed
`(family or node) × primary carrier`: `boiler_gas` and `boiler_hydrogen` are two units. Fuel
was briefly an attribute reached through the carrier bindings of §3.6, and that leaked, because
capex, `lifetime`, `availability_factor`, `earliest_year` and `min_viable_scale` all differ by
fuel and a single row cannot carry two values for any of them. `unit_eligibility` is keyed on
`unit_id`, so a shared unit could not be capped on one fuel without capping every fuel — a
site with no solid-fuel handling could not be told it may build a gas boiler but not a biomass
one.

**What this costs, and what it does not.** Keying on family or node alone gives ~40 units;
keying per fuel as well gives **~98** before hybrids. The collapse from 397 that matters is
the one across *sectors* — 331 service rows become 55, because `IFDLTHNGA01` and its
equivalents in fifteen other sectors are one `boiler_gas` — and D13 does not touch it. The
`~95` floor this document's architecture already quoted is the same number. What changes is
the maintainability claim: adding hydrogen firing is now one unit row per family that can burn
it, roughly ten rows against the 52 hydrogen technology rows today, rather than one.

**Abatement is a unit, not a cost differential against another unit.** A CCS train is a unit
that consumes a CO₂ carrier produced by its host. **A train may have several hosts**, and under
D13 (one primary carrier per unit) it usually does: a co-firing kiln is three units, and one
capture train serves all three. The hosts are therefore named in a table of their own,
`unit_abatement_host` (§3.5.3), not in a field on the unit. Under D11 (existing plant has an
age) the train inherits the **earliest** remaining life among its hosts and strands nothing
while any host still stands.

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

#### 3.5.3 `unit_abatement_host`

**Which units an abatement unit captures from.** One row per abatement unit per host.
Required for every unit with `unit_class = abatement`; meaningless for any other class.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `unit_id` | string | — | yes | PK part → `unit` | Must have `unit_class = abatement` |
| `host_unit_id` | string | — | yes | PK part → `unit` | Must have `unit_class = converter` and the **same `process_id`** as `unit_id`. May not equal `unit_id` |
| `provenance` | enum{comit_reuse, bref, proxy} | — | yes | — | D6 |

**Rule (a train has at least one host).** Every `abatement` unit has one or more rows here.
Zero rows is not "unknown host" but an undefined unit: without a host there is no CO₂ stream
for the train to consume, no process to site it on, and no life to inherit. V33 (plant is
named one unit at a time) rejects it.

**Rule (one row per host, and D13 is why there are several).** D13 (one primary carrier per
unit) splits a co-firing machine into one unit per fuel, so a cement works' dry kiln is
`kiln_dry_coal`, `kiln_dry_gas` and `kiln_dry_wdf`. The single physical capture train bolted
onto that line therefore has three hosts and writes three rows. The single optional field on
`unit` that this table replaces could name only one, which either lost two hosts or forced the
train to be split per host as well — tripling a capex that is paid once.

**Rule (earliest remaining life).** The train inherits the **minimum** remaining life over its
hosts, and attracts no stranding charge while **any** host still stands (C3, capacity transfer;
C4, incumbent ageing). Where the hosts share a vintage — the cement kiln's three cohorts are
all one commissioning year — the minimum is that single value, so the common case reads
exactly as the old single-host rule did. Where they differ, the train dies with the first host
to go, which is the conservative reading: a train sized for a line cannot outlive the part of
the line that still feeds it.

### 3.6 `unit_input_output`

Coefficients per unit per carrier per role, per unit of the unit's output. This entity is
what makes the carrier balance (C8) computable, and its **sign convention is load-bearing**:
consumed negative, produced positive.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `unit_id` | string | — | yes | PK part → `unit` | — |
| `carrier_id` | string | — | yes | PK part → `carrier` | — |
| `role` | enum{fuel_input, aux_input, emission_input, primary_output, coproduct, reject, emission} | — | yes | PK part | What the row *is*. Fixes the sign, and is what every rule below is phrased on (V31) |
| `coefficient` | real | per output unit | yes | — | **Consumed negative, produced positive**, agreeing with `role` (V31) |

**The seven roles.** Three consume and four produce, and nothing else is a row:

| Role | Sign | Means |
|---|---|---|
| `fuel_input` | − | **D13.** The one input row that is the unit's fuel. At most one per unit |
| `aux_input` | − | Any other consumed carrier: a capture train's electricity, a heat pump's source heat, a store's charge leg |
| `emission_input` | − | An emission carrier the unit consumes — a capture train taking its host's CO₂, a top-gas-recycling furnace taking back its own |
| `primary_output` | + | The carrier the unit exists to make. **Exactly one per unit** |
| `coproduct` | + | Another produced carrier that is not reject heat: `chp_gas_turbine`'s electricity |
| `reject` | + | Recovered heat leaving the unit |
| `emission` | + | An emission carrier the unit produces. Process CO₂ declared, fuel CO₂ derived (D15) |

**Sign convention, restated because §7 depends on it.** Consumed carriers are negative,
produced carriers positive. Process-emission carriers are produced, hence positive. The role
and the sign must agree on every row, which is V31; a role is not a second opinion about the
sign, it says *which* input or output the row is.

**Rule (a carrier appears once per role, not once per unit).** The key is the triple
`(unit_id, carrier_id, role)`, so one unit may consume and produce the same carrier. Two real
families need this and neither could be written down when the key was the pair:

| Case | The two rows |
|---|---|
| **Storage** | A battery charges and discharges on `electricity`; a hot-water store on the same heat band. `aux_input` for the charge leg, `primary_output` for the discharge leg, and the round-trip loss is the difference between them |
| **A capture train with a fired reboiler** | `ccs_amine` takes its host's `co2_fuel_fossil` at −0.35257 as `emission_input` and makes its own from the reboiler at +0.10659 as `emission` |

Netting the two legs into one coefficient is **not** an alternative. It makes the unit load and
destroys the number: a train that recirculates its flue gas and one that does not become the
same row, and §7's arithmetic reads the reboiler's contribution separately. A store's
round-trip efficiency disappears entirely.

A store's charge leg is `aux_input` and not `fuel_input`, so D15 derives no emission rows
against it. That is correct rather than convenient: `electricity` is an indirect carrier and
§7.8 charges an indirect carrier on the import, not on consumption, so the round-trip loss is
already paid for where it is imported.

**Rule (exactly one fuel input) — D13.** At most one row carries `role = fuel_input`, and
that carrier is the unit's fuel. `boiler_gas` names gas; `boiler_hydrogen` is a different
unit. This is what makes a unit's fuel unambiguous, and what §4.1's back-solve, §7.1's
attribution and §10.2's first condition all assume. Two `fuel_input` rows is rejected at load
with reason `unit_multi_fuel`.

**The rule is about the *fuel*, not about primary carriers, and not about input rows.** A unit
may draw any number of auxiliary inputs, primary ones included:

| Unit | Inputs | Fuel input | Auxiliary inputs |
|---|---|---|---|
| `boiler_gas` | gas | gas | — |
| `heat_pump_reject` | electricity, source heat below its `grade_in_max` | electricity | source heat (`intermediate`) |
| `heat_pump_air` | electricity, ambient | electricity | ambient, which is no carrier at all (`draws_ambient`) |
| `ccs_amine` | reboiler gas, auxiliary electricity, the host's CO₂ | gas | **electricity, which is `primary`** (`aux_input`), and the CO₂ carriers (`emission_input`) |
| `chp_gas_turbine` | gas → heat **and** electricity | gas | — |

A capture train is the case that settles it: its reboiler burns gas and its pumps and fans
draw grid electricity, and both are `primary` carriers. What must be unique is the carrier
that gives the unit its identity, not the count of primary inputs — an earlier statement of
this rule said one primary carrier and was wrong about every capture train in the library.

A unit producing several carriers is unconstrained: one row is `primary_output`, the rest are
`coproduct` (`chp_gas_turbine`'s electricity), `reject` heat or `emission` (D15).

**Rule (fuel CO₂ rows are derived, process CO₂ rows are declared) — D15.** A unit's emission
coefficients are not all authored the same way, because the two have different natures:

| Emission | Authored | Why |
|---|---|---|
| `co2_process` | **Declared** in this table | Stoichiometry. 525 kt CO₂ per Mt of clinker is chemistry, not a scenario assumption |
| `co2_fuel_fossil`, `co2_fuel_biogenic` | **Derived by A6 at build time** | The emission factor is a `scenario_parameters` series and may vary by period, so a declared coefficient could not follow it |

**A6 (the problem builder) fires on the carrier, not on the role.** Let $\mathcal{C}^{\text{burn}}_u$ be the
carriers $u$ consumes that are `primary` and **not** `is_indirect` (§3.4), and
$\Theta^{-}_{u,c}$ the consuming roles $u$ holds on $c$. For every unit, A6 generates exactly
two rows, both at `role = emission`,

$$\iota_{u,\text{co2\_fuel\_fossil},\,\text{emission}} = \sum_{c \,\in\, \mathcal{C}^{\text{burn}}_u} \;\sum_{\theta \,\in\, \Theta^{-}_{u,c}} \big|\iota_{u,c,\theta}\big|\, f_{c,t}\,(1 - b_c), \qquad \iota_{u,\text{co2\_fuel\_biogenic},\,\text{emission}} = \sum_{c \,\in\, \mathcal{C}^{\text{burn}}_u} \;\sum_{\theta \,\in\, \Theta^{-}_{u,c}} \big|\iota_{u,c,\theta}\big|\, f_{c,t}\, b_c$$

both positive, because emissions are produced. **A derived `emission` row never collides with
a declared `emission_input` row on the same carrier**, which is what the role in the key buys:
a fired capture train's own reboiler CO₂ and the host CO₂ it takes in are two rows, and before
the role was in the key the second overwrote the first. **The biogenic split happens here,
before anything is captured**, which is what §7.3 requires and what makes capture of a co-fired
stream net-negative rather than merely zero. Authoring these rows by hand instead would freeze
one scenario's factors into the unit library.

**Why the trigger is the carrier and not `fuel_input`.** D13 (one primary carrier per unit)
permits at most one `fuel_input`
row per unit, but a unit may burn more than one fuel, and the second and later ones have
nowhere to sit except `aux_input`. **84 rows in `unit_input_output.csv` draw a `primary`
carrier as `aux_input` today**, across 35 units: `rolling_mill_reheat_gas` takes blast-furnace
gas *and* coke-oven gas, `kiln_fluidbed_wdf` takes gas, coal and both fuel oils. Keying A6 on
the role alone would have every one of those burn carbon and emit nothing, while §3.4 and §5.1
say the opposite. Keying it on the carrier reconciles all three statements without a new field:
a secondary fuel is still a fuel.

**29 of those 84 rows are `electricity`, and they must keep emitting nothing.** That is what
`is_indirect` excludes, and it is not a special case — §7.8 charges an indirect carrier on
$m_{c,k,t}$, the import, precisely so that a premise generating its own supply is not billed
the grid factor on power that never came off the grid. Hydrogen carries `is_indirect` for the
same reason: its combustion releases water, and its emissions belong to whoever made it. The
two exclusions and the 55 inclusions all fall out of one existing column.

**The sums are load-bearing, not tidiness.** A unit drawing three combustible carriers would,
under a per-carrier form, produce three rows on the same
$(\texttt{unit\_id}, \texttt{co2\_fuel\_fossil}, \texttt{emission})$ triple — a key collision
of exactly the kind §3.6's key was widened to prevent. Summing first yields one row per unit
per emission carrier, which is what the key admits.

A unit consuming an `intermediate` carrier still generates nothing: its heat was already
charged to whatever made it.

**Rule (ambient heat is not a carrier, and V2 exempts it).** An air-source heat pump draws
roughly two-thirds of its output from ambient air, which does not flow between units and never
balances, so it is outside §3.4 by construction. Such a unit's coefficients therefore do
**not** sum to zero, and V2's round-trip must skip the energy-closure leg for any unit flagged
`draws_ambient`. Without the exemption every air-source heat pump fails at load.

**`role = reject` is what makes waste heat work.** A kiln's reject heat is a *positive*
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
`reinforcement_cost` per voltage band. There is no site-wide area density: how much area a
unit takes is the unit's own attribute, `area_per_capacity` in §3.5, so that C12 binds
area-bound units and no others.

### 3.9 `process_duty`

What a premise must produce, per period. Derived at run time by A2 from
`activity_process_register` and `activity_process_duty_profile`, refined by any
per-premise intelligence that exists (D10).

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part → `premise_record` | — |
| `process_id` | string | — | yes | PK part | → `activity_process_register`, on the pair `(premise_record.carb3_activity, process_id)` |
| `period` | integer | — | yes | PK part | Period index, not a calendar year |
| `carrier_id` | string | — | yes | → `carrier` | What the duty is *for* |
| `quantity` | real | PJ/yr or Mt/yr | yes | — | ≥ 0. Unit follows `carrier.denominator_kind` |
| `grade_rank` | integer | — | no | → `carrier` | Required where the carrier is gradeable |
| `evidence_tier` | enum{site_known, named_set, activity_default} | — | yes | — | D10 |

**Not every process presents a duty (D16).** A row exists where the `carrier_id` is a **service**
carrier — an `intermediate` reached through a duty family (§3.4) — or a **`product`** carrier
with `may_export` true. A process whose unit's primary output is a `product` with `may_export`
false has **no `process_duty` row at all**. The *activity-level* row stays, though: a chemistry
process keeps its `activity_process_duty_profile` (§3.3) and `activity_default_unit` (§3.16)
entries — `HTH` at `heat_gt1000` on a clinker kiln, say — because those classify the process's
heat need for eligibility and grouping rather than stating a demand the LP must serve; D16
removes the premise-level row only. The process still exists in every other sense: it is in the register,
it has candidate units, it may carry a `premise_process_detail` row and a vintage, and it is
reported. What it does not have is a demand the LP must meet.

**Its activity is fixed by C8 (carrier balance) instead.** The unit releases its whole primary output into the
carrier balance through $z^{\circ}_{u,t}$ (§5.2), and the downstream units drawing that carrier
determine how much it makes. This is what closes the double-count a downstream product consumer
would otherwise raise — C1 (duty satisfaction) demanding the output be dispatched to a duty while C8 demands it be
released to the balance, with doing both counting the same tonne twice. The throughput row on
that product remains as evidence and as A4's cross-check (§3.1.2, §5.1).

### 3.10 `premise_process_detail` — known site processes and capacity

**Optional per-premise intelligence.** Where the actual processes at a site are known —
from a permit, an audit, a site visit, or an operator disclosure — they are stated here
and override both the default set and any named variant. Zero rows for a premise is the
normal case and means "use the register".

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `process_id` | string | — | yes | PK part | → `activity_process_register`, on the pair `(premise_record.carb3_activity, process_id)` |
| `valid_from_year` | integer | year | yes | PK part | The year this process started at the premise. ≤ `premise_record.data_year`. A future year is rejected with reason `process_change_in_future`: a *planned* change is not an observation |
| `valid_to_year` | integer | year | no | — | The year it stopped. Absent ⇒ still running. ≥ `valid_from_year` if present |
| `connection_id` | string | — | no | → `premise_connection` | **Optional.** Which electricity connection serves this process (§3.1.3). Absent ⇒ the default. This is what decides where electrified load lands |
| `known_capacity` | real | capacity units | no | — | > 0 if present. Units follow the process's denominator (D5): PJ/yr-equivalent for energy, Mt/yr for mass |
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

**Rule (precedence).** Where a row has **child rows in `premise_process_unit` (§3.10.2)**,
those units are the premise's existing plant for that process **for an interval valid at the
base year**, and A4 does not choose between candidates. A parent row with no child rows means
the plant is unknown, and A4 resolves it from the candidate set as usual — exactly what a blank
`unit_id` meant before the child table existed. A closed interval's children describe plant the
site no longer has. Where `known_capacity` is given, it is used directly and A4 back-solves
*utilisation* instead of capacity (§A4).

**`known_capacity` is the line total, not a per-unit figure.** A permit states a kiln line's
capacity once, and D13 (one primary carrier per unit) then splits that line into several units.
The number therefore stays on this parent row and A4 divides it across the child units by the
§4.1 carrier mix, unless §3.10.2 gives an explicit `capacity_share`.

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

#### 3.10.1 `premise_process_energy` — sub-metered energy per process

**Optional per-premise intelligence.** Where a site sub-meters a process — a dryer, a boiler
house, a cold store — the reading is stated here and overrides §3.3.1's activity share for
that process. Zero rows is the normal case and means "use the activity default". This is the
D10 ladder applied to process size, and it is the reason §3.3.1 is a *default* rather than
the answer.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `process_id` | string | — | yes | PK part | → `activity_process_register`. Must be valid at the base year (§3.10) |
| `carrier_id` | string | — | yes | PK part | → `carrier`. The carrier as sub-metered |
| `quantity` | real | PJ/yr | yes | — | ≥ 0 |
| `data_year` | integer | year | yes | PK part | The year this reading was taken. §3.1.1's base-year rule applies |
| `data_status` | enum{measured, estimated, modelled} | — | yes | — | — |
| `provenance` | string | — | yes | — | Citation: sub-meter reference, audit, operator disclosure |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried to output |

**Rule (quantities, not shares).** Sub-metering arrives as a reading, and a share would have
to be computed against the main meter by whoever supplies it. Stating the quantity keeps the
discrepancy visible: if a site's sub-meters account for 80% of its metered gas, that 20% is
evidence about the meters, not a rounding error to be normalised away.

**Rule (keyed on carrier, while the default is keyed on vector).** A sub-meter reads a
specific supply, and a site metering LPG separately from natural gas should be able to say so.
The join to §3.3.1 is through `premise_energy.vector`, which §3.1.1 already requires to agree
with the carrier's kind. Evidence therefore degrades cleanly: carrier-level where the site
knows, vector-level where it does not.

**Rule (partial coverage is the normal case).** A premise sub-metering one process is the
expected shape, not an edge case. Sub-metered processes take their stated quantity; the
**residual** of each vector — the premise's total for that vector, less everything sub-metered
against it — is distributed over the remaining processes by §3.3.1's shares, renormalised over
just those processes. This is §3.3.1's renormalisation rule extended from absent processes to
unmetered ones.

**Rule (the residual may not be negative).** If a vector's sub-metered quantities exceed the
premise's total for that vector, the premise is **reported** `submeter_exceeds_meter` and the
whole vector falls back to the activity default. Never a rejection: the sub-meters are
evidence, and discarding the premise would discard them.

**The evidence tier resolves per `(process, carrier)`, not per premise.** `sub_metered` where
a row exists, `activity_default` for the residual, in the same solve — the pattern §3.15 uses
for vintage, where a works may know its kiln's age and not its mills'. §8 carries it as
`energy_evidence_tier`.

#### 3.10.2 `premise_process_unit` — which units a known process runs

**Optional per-premise intelligence.** One row per known unit per §3.10 interval. Zero rows
under a parent is the normal case and means the plant is unknown; A4 resolves it from the
candidate set.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_process_detail`, on the triple `(premise_id, process_id, valid_from_year)` |
| `process_id` | string | — | yes | PK part | Part of the same triple |
| `valid_from_year` | integer | year | yes | PK part | Part of the same triple. The parent interval this row belongs to |
| `unit_id` | string | — | yes | PK part | → `unit`. Must be eligible for this process at the premise's activity (§3.5.1) |
| `capacity_share` | real | fraction | no | — | ∈ (0, 1]. Where any row of one parent gives it, every row must, and they sum to 1 within 1e-6 |
| `provenance` | string | — | yes | — | Citation: permit number, audit reference, disclosure |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried through to output |

**Why a child table rather than a field.** §3.10 carried a single optional `unit_id`, which
could say "this process runs this unit" but not "this process runs these three". D13 (one
primary carrier per unit) makes that the common case, not an edge case: a co-firing kiln line
is three units. A single field forced a choice between naming the dominant unit and losing the
rest, or leaving the field blank — which made a site that genuinely runs one fuel
indistinguishable from one that runs three. A single-fuel works now writes one row, and the
distinction is in the data.

**Rule (a parent's children are its complete plant list).** The rows under one §3.10 interval
are treated as the whole of what that process runs in that interval, the same completeness
reading §3.10 takes over the process list itself. They must name distinct units.

**`capacity_share` is optional because the split is usually derivable.** Where it is absent,
A4 divides the parent's `known_capacity` by the §4.1 carrier mix — for a co-firing kiln, the
base-year fuel split. Where a permit states the split, giving it here pins the back-solve
instead. V33 (plant is named one unit at a time) checks the sum.

**§3.15 already has this shape, and that is the argument for it.** `premise_process_vintage`
is keyed per cohort with `unit_id` a plain field on the row, so a co-firing kiln decomposes
into three cohorts naturally and states vintage as shares. This table gives §3.10 the same
one-row-per-unit structure, so the two tables now answer *which units* and *how old each is*
in the same grain instead of disagreeing about how many there are.

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

**Key rule.** A `process_id` is unique only within an activity: §3.2 keys the register on
`(carb3_activity, process_id)`, and generic names such as `site_services` or
`compressed_air` recur across activities. A reference to a process is therefore always the
pair. The same process name may legitimately carry different shapes at different
activities — `dewatering_pumping` is `flat` where it follows the line and `standing` where
it drains a site — so the shape is declared per pair, one row for every register row.

This is the decomposition that makes the peak question tractable. Declaring shapes per
unit would multiply the data build by the fuel variants — 82 of 94 COMIT processes
differ only by fuel — for information that does not vary along that axis.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `carb3_activity` | string | — | yes | PK part | → `activity_process_register` |
| `process_id` | string | — | yes | PK part | → `activity_process_register`, on the pair with `carb3_activity` — see the key rule below |
| `shape_id` | string | — | yes | — | Surrogate label, `<activity>__<process>`; carries no information the key does not |
| `shape_class` | enum{flat, throughput_following, batch_cyclic, intermittent, standing, seasonal} | — | yes | — | See below |
| `duty_factor` | real | fraction | no | — | ∈ (0, 1]. Share of operating hours in which the process draws power. Blank ⇒ **1.00, the process runs whenever the site runs** — see the default rule below |
| `peak_to_mean` | real | ratio | no | — | ≥ 1. Peak ÷ mean demand across the hours it is running. Blank ⇒ **1.00, no within-shift peakiness** — see the default rule below |
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

**Rule (the two magnitudes default, and the default is not data).** `shape_class`,
`runs_when_idle` and `seasonality` are what the reference build can source; `duty_factor`
and `peak_to_mean` are what it mostly cannot, because no published load profile survives
the no-invention rule for most process types. A blank on either is therefore legitimate
and means *shape known, magnitude not*. Where blank, §5.6 (the peak method) uses:

| Field | Default | What it assumes |
|---|---|---|
| `duty_factor` | 1.00 | The process draws power for the whole of the site's operating hours — its schedule is the plant's schedule (§3.12's `shifts_per_day`, `days_per_week`, `weeks_per_year`), and `runs_when_idle` says whether it also draws outside them |
| `peak_to_mean` | 1.00 | The draw is flat across those hours |

Together the defaults rebuild the peak as the **mean load over operating hours**, which
is the **floor** of the true peak: every real process is at least this peaky, and most are
peakier. The default therefore never overstates a connection requirement and may understate
one, so C11 (the connection-capacity constraint) is lenient under it. Three consequences
are binding:

- The default is a **modelling assumption chosen for conservatism, informed by no data**.
  It is not to be written into `process_load_shape` as a value; a `1.00` in the table means
  a source said so. The table's blank and the method's 1.00 are different facts.
- The class table's indicative ranges are **not** the fallback. Reading `batch_cyclic` as
  "2–4" would invent a number the rule above forbids; the defaults are the same for every
  class.
- Any peak built from a defaulted row is reported as such (§8's output carries the flag),
  so a connection sizing from defaults is never mistaken for one from measured shape.
  Where §3.14 supplies a measured week, it wins and the defaults are not consulted.

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
| `process_id` | string | — | no | PK part | → `activity_process_register`, on the pair `(premise_record.carb3_activity, process_id)`. Present only where sub-metered; absent ⇒ whole site |
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
| `process_id` | string | — | yes | PK part | → `activity_process_register`, on the pair `(premise_record.carb3_activity, process_id)` |
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

**Rule (a chemistry process keeps its row even with no duty).** Where D16 removes a process's
premise-level `process_duty` row because its primary output is an internal product (§3.9), this
entity's row and its `duty_family` — `HTH` on a clinker kiln, for instance — are kept: they
classify the process's heat need so that `unit_eligibility` and the duty-family grouping still
work, and they name the incumbent plant A4 back-solves. They are a classification, not a demand
the LP serves.

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

*Section last updated: 2026-09-17*

> **Partially written.** The numbered pseudocode for A1–A9 is outstanding; the delivery plan
> names its owner. What each algorithm is responsible for, and the two rules that were open
> questions in the design, are settled and stated below.

Nine algorithms run the pipeline of §2.1. A1–A9 map onto the stages S1–S9 one for one.

| # | Algorithm | Responsibility |
|---|---|---|
| A1 | Ingest and validate premise records | Accept a premise record and its companions, apply the load-scope validation of §10, reject with reasons. **Resolve the base year (D12), apply §3.1.1's substitution ladder, and report `duplicate_year_row`, `profile_year_unmatched` and `emissions_year_unmatched`. `missing_throughput` is raised only for a `product` carrier with `may_export` true (D16); an internal product's throughput row is evidence, so its absence is reported, not rejected** |
| A2 | Expand premise to duties and candidate units | Resolve the process set, **size each process from §3.3.1's shares or §3.10.1's sub-meters**, produce `process_duty` rows, and resolve the **candidate unit set** from `unit_eligibility` — including the `min_duty` screening that keeps minimum viable scale out of the LP. **Reads only the `premise_process_detail` rows valid at the base year (§3.10). A process whose unit's primary output is a `product` with `may_export` false produces no duty row (D16, §3.9); its candidate units are resolved as usual and its activity is left to C8 (carrier balance)** |
| A3 | Allocate premise energy onto carriers | Split metered energy across carriers. It does **not** allocate energy across processes: the carrier balance decides that. **Reads the base year only; history rows are carried to reporting untouched** |
| A4 | Back-solve implied capacity, carrier mix and vintage | Turn metered energy into installed unit capacity, the mix of carriers each unit burns (§4.1), and plant age under D11. **Back-solves from the base year only, reads only base-year-valid process rows, and carries a substituted carrier vintage into the mix evidence. Where a process has no duty (D16), the `premise_throughput` evidence row is what the utilisation and implied-output checks of §5.1 are run against** |
| A5 | Apply the scenario | Attach prices, carbon price, infrastructure availability and the archetype coefficients ψ, β, χ, ε |
| A6 | Build the per-premise problem | Declare variables over units and carrier flows, assemble C1–C12 and the objective of §5.4. **Derive the fuel-emission coefficients of §3.6 over $\mathcal{C}^{\text{burn}}_u$** — every consumed carrier that is `primary` and not `is_indirect`, summed across carriers and roles, so a unit's secondary fuels are charged and its electricity is not |
| A7 | Solve and extract | Solve, extract the pathway, and handle infeasibility by the relaxation ladder of §4.2 |
| A8 | Assemble output tables | Produce the per-premise pathway rows, each carrying its evidence tier, **the disposal quantities of §5.2 and the §7.7 allocated intensities beside the accounted figures they derive from** |
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
| 3 — `activity_default` | Neither | The activity-default mix of **§3.3.1**, carried as an assumption |

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

*Section last updated: 2026-09-19*

**This section is authoritative.** Everything else serves it.

### 5.1 Sets and indices

| Symbol | Meaning |
|---|---|
| $T$ | Model periods, $t \in \{0, \ldots, N\}$. **$t$ is a period index, not a calendar year** |
| $y_t$ | The calendar year of period $t$, read from the **year vector** $\mathbf{y} = (y_0, \ldots, y_N)$. Strictly increasing; $y_0$ is the start year $y_{t_0}$ |
| $\Delta_t$ | Span of period $t$ in years: $\Delta_t = y_{t+1} - y_t$ for $t < N$, and $\Delta_N = \Delta_{N-1}$ |
| $\Delta$ | A single timestep in years. Defined **only** where every gap is equal, which is not the general case |
| $Q$ | Duties at this premise |
| $U$ | Units available, $U = \bigcup_{q} U_q$ |
| $U_q$ | Units eligible for duty $q$, after `unit_eligibility` screening |
| $Q_u$ | Duties $u$ is eligible for, $Q_u = \{q : u \in U_q\}$. The transpose of $U_q$ |
| $U^{\text{gen}}$ | Generator units, those with `unit_class` = generator |
| $U^{\text{area}}$ | Area-bound units, those with `area_per_capacity` set (§3.5). Not $U^{\text{gen}}$: PV is in both; a CHP, an engine or a boiler house takes no area and is outside $U^{\text{area}}$ whatever its class |
| $c^{\star}_u$ | Primary output carrier of $u$ — the one `role = primary_output` row of §3.6 |
| $U^0$ | **Incumbent** units, those with existing capacity |
| $\mathcal{C}$ | Carriers |
| $\mathcal{C}^{\text{prim}}$ | Primary carriers |
| $\mathcal{C}^{\text{burn}}_u$ | Carriers $u$ consumes that are `primary` and not `is_indirect`. **Fuel emissions attach here and nowhere else**, whatever role the row carries (§3.6) |
| $\mathcal{K}$ | The premise's connections |
| $g(c)$ | Grade rank of carrier $c$, where gradeable |

**The periods are data, not a formula.** $\mathbf{y}$ is an input to the model — the
scenario's own list of calendar years — and nothing may reconstruct it from a step. The
reference scenario runs 2021, 2025, 2030, 2035, 2040, 2045, 2050: the first gap is four
years and every later one is five, so $\Delta_t = (4, 5, 5, 5, 5, 5, 5)$. **A uniform step
is not an approximation of that, it is wrong**, and it is wrong from the first period
onward: $y_{t_0} + 5t$ puts period 1 at 2026 rather than 2025 and period 6 at 2051 rather
than 2050, so every period after the start lands a year late.

**$\Delta$ survives as a shorthand for the uniform case and nothing more.** Where all gaps
are equal, $\Delta_t = \Delta$ for every $t$ and the expressions below collapse to the
familiar uniform forms. That is a special case to recognise, never the definition: an
implementation that carries a scalar step cannot read the reference scenario at all.

**Any lifetime used as an index offset is converted against actual years, not against a
nominal step.** A unit built in period $s$ with lifetime $L_u$ years stands in every period
whose year falls inside that life:

$$\ell_{u,s} = \big|\{\, t \in T \;:\; y_s \le y_t < y_s + L_u \,\}\big|$$

which is why C3 (capacity transfer) keys its window on the build period $s$ and not on the
unit alone: on the reference vector a 25-year life built in 2021 covers six periods and the
same life built in 2025 covers five. Dividing by a nominal step gets both wrong, and
reading $L_u$ itself as a period count is a 125-year asset.

**The present-value factor aggregates over the period's own span.** With the discount rate
$r$ of §5.3, and $d_t = (1+r)^{-(y_t - y_{t_0})}$ the single-year factor §5.4 uses for the
stranding write-off:

$$\delta_t \;=\; \sum_{j=0}^{\Delta_t - 1} (1+r)^{-(y_t + j - y_{t_0})} \;=\; d_t\,\frac{1 - (1+r)^{-\Delta_t}}{1 - (1+r)^{-1}}$$

Every cost term in §5.4 is an annual **rate**, so a period carries that rate once for each
year it stands for. Giving the start period five years instead of the four it spans
overstates its whole cost by a quarter.

**The terminal period's span is a stated convention.** $y_N$ has no successor, so
$\Delta_N$ cannot be derived from the vector; the last observed gap is carried forward,
$\Delta_N = \Delta_{N-1}$, which weights 2050 as 2045 is weighted. It is a choice rather
than a fact, and it is written down here so that two implementations make the same one.

**What reads the vector.** Everything that crosses between a period index and a calendar
year: $\delta_t$ and $d_t$ above; C3's (capacity transfer) build window, through
$\ell_{u,s}$; C4's (incumbent ageing and early retirement) survival function $\eta_{u,t}$,
which ages a `commissioned_year` (§3.15) by elapsed years; C5 (no building in the start
year), which pins $t_0$ and so the year $y_0$ that bears no investment; and the
`earliest_year` screen of §3.5.1, which compares a calendar year against $y_t$ rather than
against $t$.

### 5.2 Decision variables

All continuous and non-negative. **The problem is a pure LP and must stay one.**

| Variable | Meaning | Unit |
|---|---|---|
| $n_{u,t}$ | New capacity of unit $u$ built in $t$ | capacity units |
| $a_{u,t}$ | Capacity of $u$ available in $t$ | capacity units |
| $z_{u,q,t}$ | Activity of $u$ dispatched to duty $q$, declared over $u \in U_q$ only | output units of $u$ |
| $z^{\circ}_{u,t}$ | Activity of $u$ whose primary output is released into the carrier balance rather than dispatched to a duty. **For a unit whose primary output is an internal `product` (D16), this carries the unit's whole activity, because no duty exists to dispatch to** | output units of $u$ |
| $h_{c \to c',t}$ | Heat cascaded from carrier $c$ down to carrier $c'$, declared only where both are gradeable and $g(c') < g(c)$ | PJ/yr |
| $e_{u,t}$ | Surviving incumbent capacity of $u$ (D11), declared over $U^0$ only | capacity units |
| $r_{u,t}$ | Incumbent capacity retired early in $t$ (D11), over $U^0$ only | capacity units |
| $m_{c,k,t}$ | **Connection-indexed** import of carrier $c$ at connection $k$. Declared where `carrier.may_import` (§3.4) is true **and** a `premise_connection` row carries $c$ | PJ/yr |
| $m_{c,t}$ | **Site-level** import of carrier $c$, with no connection index. Declared where `carrier.may_import` is true and **no** connection carries $c$ — a delivered fuel (coal, waste-derived fuel, fuel oil, biomass) arriving by road or rail | PJ/yr |
| $x_{c,k,t}$ | Export of carrier $c$ at connection $k$. Declared where `carrier.may_export` (§3.4) is true **and** a `premise_connection` row carries $c$ | PJ/yr |
| $w_{k,t}$ | Reinforcement purchased at connection $k$ | MW |
| $d_{c,t}$ | **Disposal of carrier $c$** — heat rejected to atmosphere, CO₂ vented. Declared only where `carrier.may_dispose` (§3.4) | PJ/yr or Mt/yr |

**An import exists wherever `may_import` does; only some imports are connection-indexed.** A
*networked* carrier — electricity, natural gas, hydrogen, CO₂ transport — arrives through a
`premise_connection` row (§3.1.3) and takes $m_{c,k,t}$, so C11 (connection capacity) can bound
it. A **delivered** fuel has no connection row and takes $m_{c,t}$ instead: coal, waste-derived
fuel, fuel oil and biomass arrive by road or rail, and a lorry is not a connection. The flag
decides whether an import exists at all; the presence of a connection decides only how it is
indexed. Exports are always connection-indexed, because leaving the site means going onto a
network.

**Total activity is a defined expression, not a variable.**
$z_{u,t} \equiv \sum_{q \in Q_u} z_{u,q,t} + z^{\circ}_{u,t}$, and it is what C2, C6, C7 and §7
read. **The duty index is what stops one unit being credited twice.** §3.5 makes service
units family-keyed, so one boiler at one premise sits in several $U_q$; with a single
activity variable it would be credited in full against every duty it is eligible for.
Dispatch is per duty, capacity is shared through C2, and a high-grade unit serving a
low-grade duty is simply a dispatch to a $q$ below its `grade_out` (C10).

**Activity is $z$, not $u$.** $u$ indexes units throughout this document, so the activity
variable takes a different letter. The separation is deliberate and is the kind of clash the
label rules in §1.4 exist to prevent.

**No binaries.** Minimum scale is handled by eligibility screening in A2 and by reporting,
never by a fixed-charge binary. Any proposal to add one must be weighed against §9.

**Disposal is a variable so that waste is a number.** Without it C8 has no sink: a carrier a
unit produces and nothing consumes — a kiln's process CO₂ before capture exists, a dryer's
reject heat before a heat pump is built — cannot balance, and V18 fails on a premise that is
physically fine. Making it explicit rather than implicit means the quantity is reported: how
much heat this site throws away, and how much CO₂ it vents, are output rows rather than
residuals someone has to infer.

**It is gated on `carrier_kind`, and the gate is the whole safety argument.** `intermediate`
and `emission` carriers may be disposed of; `primary` and `product` may not. Disposal of a
primary carrier would let the model import gas and dump it, and of a product would let it
build a kiln and throw the clinker away. Neither is ever optimal, but neither should be
expressible.

### 5.3 Parameters

| Symbol | From | Meaning |
|---|---|---|
| $D_{q,t}$ | `process_duty` | Duty quantity |
| $\iota_{u,c,\theta}$ | `unit_input_output.coefficient` | Signed coefficient of $u$ for $c$ in role $\theta$. A unit may hold one row per role on a carrier, which is how a store and a fired capture train are written (§3.6) |
| $\theta \in \Theta_{u,c}$ | `unit_input_output.role` | A §3.6 role, and the set of roles $u$ holds on $c$. **$\theta$, not $\rho$** — $\rho_u$ two rows below is the fraction not captured, and the two are unrelated |
| $\Theta^{-}_{u,c}$ | `unit_input_output.role` | The **consuming** roles in $\Theta_{u,c}$ — `fuel_input`, `aux_input`, `emission_input`. Used by §3.6's A6 derivation, which must not read a unit's *output* rows on a carrier it also burns. The superscript is a restriction of $\Theta_{u,c}$, not a second symbol |
| $\kappa_u, \phi_u, L_u$ | `unit` | Capex, fixed opex, lifetime |
| $\alpha_u, \gamma_u, \rho_u$ | `unit` | Availability, capacity→activity, fraction not captured |
| $\psi_u, \beta_u, \chi_u, \varepsilon_u$ | `archetype_coefficient` | Tier A coefficients |
| $\eta_{u,t}, \bar R_{u,t}$ | D11 survival function | Fraction surviving, mean remaining life |
| $\xi$ | `scenario_parameters` | Stranding factor |
| $p^{\text{imp}}_{c,t}, p^{\text{exp}}_{c,t}$ | `scenario_parameters` | Import and export prices |
| $\overline{P}^{\text{imp}}_k, \overline{P}^{\text{exp}}_k$ | `premise_connection` | Connection capacities |
| $A_k$ | `premise_connection` | Available area at connection $k$, m² |
| $\lambda_u$ | `unit.area_per_capacity` | Area taken per capacity unit, m². Defined over $U^{\text{area}}$ only |
| $\pi_t, \tau_{c,t}, \sigma, r, i$ | `scenario_parameters` | Carbon price, tariff, stability factor, discount and interest rates |

**D11's survival function $\eta$ and mean remaining life $\bar R$ are parameters, computed
per unit before the problem is built.** That is what keeps D11 free of binaries.

### 5.4 Objective

Minimise total present-value cost:

$$\min \; Z = \sum_{t} \Big[\; \delta_t \big( Z^{\text{capex}}_t + Z^{\text{opex}}_t + Z^{\text{fuel}}_t + Z^{\text{carbon}}_t + Z^{\text{infra}}_t + Z^{\text{net}}_t - Z^{\text{exp}}_t \big) \;+\; d_t \, Z^{\text{strand}}_t \;\Big]$$

with $\delta_t$ the present-value factor aggregated over the years period $t$ stands for
and $d_t$ the **single-year** factor used for the stranding write-off, both as §5.1 defines
them against the year vector. Capex is annuitised over $L_u$ at interest rate $i$; the
annuity for a hybrid already contains its component replacements (§3.5).

$$Z^{\text{fuel}}_t = \sum_{c}\Big(\sum_{k} m_{c,k,t} + m_{c,t}\Big)\big(p^{\text{imp}}_{c,t} + \tau_{c,t}\big) \cdot \varepsilon(c,t) \qquad Z^{\text{exp}}_t = \sum_{c,k} x_{c,k,t}\,p^{\text{exp}}_{c,t}$$

**Both import terms are priced, and at the same price.** A delivered fuel arriving at
$m_{c,t}$ (§5.2) costs what a networked one arriving at $m_{c,k,t}$ costs: the connection index
decides whether C11 (connection capacity) can bound the flow, never whether it is paid for.
Omitting the site-level term would make coal free.

$$Z^{\text{net}}_t = \sum_{k} \gamma_k\big(w_{k,t}\big)$$

**$Z^{\text{exp}}$ enters with a negative sign, so the objective now has a genuinely
negative term.** No implementation may assume cost components are non-negative. V6 already
records this trap for emissions; it now applies to costs.

**Carbon is charged on what is vented, not on what is burnt (D15).** Every emission is a
carrier, so produced CO₂ must either be captured or disposed of, and the disposal variable is
the emission event:

$$Z^{\text{carbon}}_t = 10^{-3}\,\pi_t \Big( \underbrace{\sum_{c\,:\,\text{charged}} d_{c,t}}_{\text{vented}} \;-\; \underbrace{\sum_{c\,:\,\text{zero\_rated}}\;\sum_{u \in U^{\text{abate}}} \big|\iota_{u,c,\,\text{emission\_input}}\big|\, z_{u,t}}_{\text{biogenic captured}} \Big)$$

with `charged` and `zero_rated` read from `carrier.carbon_charge` (§3.4). The first term is
what leaves the stack; the second is the credit for biogenic carbon that did not, and it is
the only negative emission the model can produce.

**This is equivalent to charging fuel consumption less capture, and better behaved.** C8
forces produced CO₂ to go somewhere, so venting cannot be avoided by not modelling it. What
changes is that capture needs no term of its own — a train simply consumes the carrier and
the charge falls — and that biomass zero-rating sits in the carrier set rather than in an
accounting rule applied afterwards.

**Carbon cost carries a $10^{-3}$ unit conversion.** Emission
factors are kt/PJ and the carbon price is £/t.

### 5.5 Constraints

**C1 — Duty satisfaction.** Each duty is met in each period, by units eligible for it:

$$\sum_{u \in U_q} z_{u,q,t} = D_{q,t} \qquad \forall q \in Q,\; t \in T$$

Dispatch is per (unit, duty) pair, so a unit sitting in several $U_q$ contributes to each
duty only what it sends there.

**An internal product never appears in C1 (duty satisfaction).** Under D16 a `product` carrier
with `may_export` false presents no duty at all (§3.9), so $Q$ holds no $q$ for it and no unit
is asked to dispatch to one. Its maker's output reaches its consumer through C8 below.

**C2 — Activity limited by available capacity.**

$$z_{u,t} \le a_{u,t}\,\gamma_u\,\alpha_u \qquad \forall u,\, t$$

with $z_{u,t}$ the total of §5.2, so a unit's dispatches to every duty it serves, plus what
it releases to the balance, share one capacity.

**C3 — Capacity transfer between periods.**

$$a_{u,t} = e_{u,t} + \sum_{s \le t} n_{u,s}\,\mathbb{1}[\,s \le t \le s + \ell_{u,s} - 1\,]$$

with $e_{u,t} \equiv 0$ for $u \notin U^0$. An abatement unit expires with its **earliest**
host, not on its own life: its hosts are the rows of `unit_abatement_host` (§3.5.3) and the
window it inherits is the minimum remaining life over them.

**C4 — Incumbent ageing and early retirement (D11).** Incumbent capacity decays by the
survival function $\eta$, may be retired early against a stranding charge in $\xi$, and the
abatement rule reads `unit_abatement_host` (§3.5.3): an abatement unit **any** of whose hosts is
still standing has not been scrapped, so it attracts no stranding charge, and the remaining life
it inherits is the **minimum** over its hosts. Where the hosts share a vintage the minimum is
that one value, which is the single-host rule this replaces.

**C5 — No building in the start year.** $n_{u,t_0} = 0 \;\; \forall u$.

**C6 — Unit stability.** A two-legged ramp limit on how fast a unit's activity may change
between periods. $\sigma$ is measured against deliverable output
$\bar z_{u,t} = a_{u,t}\gamma_u\alpha_u$, not against installed capacity.

**C7 — Known changes.** Announced commitments fix or bound $z_{u,t}$ or $a_{u,t}$.

**C8 — Carrier balance. This is the core change.** For every carrier at every period, at the
premise:

$$\sum_{u \in U} \;\sum_{\theta \,\in\, \Theta_{u,c}} \Big( \mathbb{1}[\theta \neq \texttt{primary\_output}]\, z_{u,t} \;+\; \mathbb{1}[\theta = \texttt{primary\_output}]\, z^{\circ}_{u,t} \Big)\,\iota_{u,c,\theta}
\;+\; \sum_{c'' :\, g(c'') > g(c)} h_{c'' \to c,t} \;-\; \sum_{c' :\, g(c') < g(c)} h_{c \to c',t}
\;+\; \sum_{k \in \mathcal{K}} \big(m_{c,k,t} - x_{c,k,t}\big) \;+\; m_{c,t} \;-\; d_{c,t} \;=\; 0 \qquad \forall c \in \mathcal{C},\, t$$

with $m_{c,k,t} = m_{c,t} = 0$ where `carrier.may_import` is false and $x_{c,k,t} = 0$ where
`carrier.may_export` is false (D16); of the two import terms **exactly one is declared** for a
carrier the flag admits — $m_{c,k,t}$ where a `premise_connection` row carries $c$, $m_{c,t}$
where none does (§5.2) — and $x_{c,k,t} = 0$ where the premise has no connection carrying $c$,
since an export must go onto a network. Both cascade sums are empty where $c$ is not gradeable,
and $d_{c,t} = 0$ where `carrier.may_dispose` is false. Every carrier balances, including
electricity: that is what makes onsite generation, CHP and export expressible at all.

**Three things the form settles.** A unit's inputs, co-products and reject heat scale with
its *total* activity — a CHP makes electricity whether its heat went to a duty or to the
steam node. Its primary output enters the balance only for the activity not dispatched to a
duty, so the same PJ of heat cannot both satisfy a duty in C1 and feed another unit here;
$\iota_{u,c^{\star}_u,\,\text{primary\_output}}$ is 1 per output unit by §3.6's definition.
**The inner sum runs over roles, and the indicator is on the role rather than on the
carrier** — $\Theta_{u,c}$ is the set of roles $u$ holds on $c$, usually one. Keying the
sum on $c = c^{\star}_u$ instead would misread every store, whose charge row and discharge row
sit on the same carrier and scale with different activity variables. And $h$ is the cascade
the architecture calls a one-way ordering in the balance: heat may flow down a grade at no
cost, never up, which is what lets a kiln's reject heat at one band be drawn by a heat pump
whose input row sits at a lower one.

**An internal product reaches its consumer here, and only here.** Because D16 gives it no duty,
its maker's whole activity enters this balance through $z^{\circ}$ and the downstream unit's
input coefficient draws it out; the node closes and the maker's activity is pinned by the draw.
That is what settles the double-count a downstream product consumer would otherwise raise: with
a duty as well, C1 would require the output to be dispatched and C8 to be released, satisfying
both would count the same tonne twice, and satisfying either alone would fail the other. One
constraint now owns the flow.

**C9 — Infrastructure availability (D7).** A unit whose carrier is unavailable at the premise
in a period cannot run, and where a cap is specified the premise's draw respects it. This
covers `biomethane` as well as hydrogen and CO₂ transport: biomethane's real constraint is a
shared catchment, which D2 forbids modelling per premise.

**C10 — Heat grade cascade.** A unit may serve a duty only at or below its output grade:

$$z_{u,q,t} = 0 \quad \text{where } \text{grade\_out}(u) < g\big(\text{carrier}(q)\big), \qquad\qquad h_{c \to c',t} \text{ exists only where } g(c') < g(c)$$

In practice the first is enforced by **eligibility at load** rather than as a row in the LP —
a unit whose `grade_out` is below the duty's grade is not in $U_q$, so the variable is never
created — which is why V19 is a load-scope test. The second is the declaration set of $h$,
so no upward variable exists to relax. Stating both as constraints keeps §5 complete;
implementing them as filters keeps the problem small.

**High grade may serve a low-grade duty, never the reverse.** A steam boiler at 150–400 °C
serves a 120 °C duty; a heat pump capped at 100 °C does not. Stating it as physics rather
than as a technology-to-process mapping is what lets a new unit be added without editing a
mapping table. The cascade has two sides and the algebra covers both: on the duty side a
unit in several $U_q$ serves each through its own $z_{u,q,t}$, sharing one capacity through
C2; on the carrier side $h$ in C8 carries heat down the grade ladder and nothing carries it up.

**C11 — Connection capacity.** Per connection, never summed across connections, and over
**connection-indexed flows only** — a delivered fuel arriving at $m_{c,t}$ with no connection
row (§5.2) has no connection to bound and never enters this constraint:

$$P^{\text{peak}}_{k,t} \;\le\; \overline{P}^{\text{imp}}_{k} + w_{k,t} + \sum_{u} \beta_u\,a_{u,t} \qquad \forall k \in \mathcal{K},\, t$$

and export bounded by $\sum_c x_{c,k,t} \le \overline{P}^{\text{exp}}_k$ after conversion to
power. Peak is rebuilt from the solved pathway by the §5.6 method, using
`process_load_shape` and the diversity step that must not be skipped.

**$\beta$ is how storage earns its keep here**, and it is the one place a standalone battery
is worth building: it contributes firm capacity linearly, with no dependence on a sizing
ratio, so it needs no hybrid pairing.

**C12 — Siting cap.** Area-bound units are bounded by usable area, each at its own footprint:

$$\sum_{u \in U^{\text{area}}} \lambda_u\, a_{u,t} \;\le\; \sum_{k \in \mathcal{K}} A_k \qquad \forall t$$

Without this the LP builds unbounded PV and exports it. This constraint is the reason
`available_area` is the highest-priority missing input.

**The coefficient is per unit, and the sum runs over area-bound units only.** One site-wide
area density applied to every generator would cap a CHP at the footprint of the PV array
that fits on the same roof, which is not a constraint a CHP has. A CHP, an engine or a
boiler house carries no `area_per_capacity` and is outside the sum; PV and solar thermal
carry theirs. Area is summed across connections here, unlike capacity in C11, because roof
and land are one estate however many supplies serve it.

**Non-degeneracy rule.** $p^{\text{exp}}_{c,t} < p^{\text{imp}}_{c,t}$ strictly, per carrier
per period, asserted at load (V21). Equal prices make building and importing exactly
cost-equivalent, and the solver is then free to report either — two identical runs would
disagree on onsite capacity. The deterministic tie-break is lexicographic over
$(\texttt{unit\_id}, \texttt{carrier\_id}, \texttt{role})$ — the §3.6 key, which the pair
stopped being once a store and a fired capture train could hold two rows on one carrier.

---

## 6. Constraint disposition

*Section last updated: 2026-09-02*

**Not yet written.** Which constraints bind in practice, which are reported rather than
enforced, and the "reported comparison, not constraint" pattern used for the national
emissions cap and for minimum viable scale.

---

## 7. Emissions accounting

*Section last updated: 2026-09-16*

Emissions have two sources: combustion of a fuel carrier, and process chemistry tied to
physical throughput. Under D15 both are **carriers**, so this section is a readout of the
balance rather than a calculation beside it:

$$\text{direct emissions}_t \;=\; \sum_{c\,:\,\text{charged}} d_{c,t} \;-\; \sum_{c\,:\,\text{zero\_rated}}\;\sum_{u \in U^{\text{abate}}} \big|\iota_{u,c,\,\text{emission\_input}}\big|\, z_{u,t}$$

the same expression the objective charges (§5.4), which is what stops the reported total and
the costed total from ever drifting apart. The rules below say how the carriers are produced
and who they are attributed to; none of them is a second calculation.

| # | Rule |
|---|---|
| 7.1 | **Two sources, both carriers (D15).** Fuel CO₂ is **produced by** the unit that burns the fuel, never by the unit that consumes the heat that fuel made; its coefficient is derived in §3.6 over $\mathcal{C}^{\text{burn}}_u$, so a unit's **second and later fuels count exactly like its first** — the role a row carries does not change whether its carbon is released. Process CO₂ is produced by the chemistry unit against its mass denominator (D5) and is declared |
| 7.2 | **Non-CO₂ gases** are tracked separately, are **not** carriers, and **CCS never abates them** |
| 7.3 | **Biomass zero-rating is applied before capture** — the split into `co2_fuel_fossil` and `co2_fuel_biogenic` happens at production (§3.6), so capture of a co-fired stream takes both pro rata and the biogenic share returns a **credit**. Net-negative, not zero |
| 7.4 | **Direct versus indirect** is a property of the carrier — `carrier.is_indirect` (§3.4) — not a list held in code |
| 7.5 | **Reporting categories** are derived over units. Categories may overlap, and a unit may appear in more than one |
| 7.6 | **Reconciliation, at the base year.** Reported totals reconcile against `premise_measured_emissions` (§3.11) **at the base year** wherever a row exists there. Other years are a reported trend and never a calibration target. A premise with rows but none at the base year is reported `emissions_year_unmatched` and not reconciled (§3.1.1) |
| 7.7 | **Allocation is reporting, and never a second set of books (D14).** A per-carrier intensity — gCO₂e per kWh of CHP electricity — is derived by allocating a generating unit's fuel emissions across its outputs, and the allocation must sum back to that unit's fuel emissions exactly |
| 7.8 | **An indirect carrier is charged on the import, not on consumption.** Where a premise generates some of its own supply, $\sum_u$ consumption exceeds $\sum_k m_{c,k,t}$, and the grid factor applies only to the second |
| 7.9 | **Disposal is where an emission carrier leaves the site.** $d_{c,t}$ on an `emission` carrier is the venting event and is reported as such (§5.2) |
| 7.10 | **Non-energy use is not combustion.** A `NEUOTH` feedstock carrier is consumed as material and carries no combustion emissions (§3.4) |

**The rule that stops double-counting.** Emissions attach to the unit that consumes a
**primary, non-indirect** carrier — gas, coal, biomass, the fuel oils, the works gases. A unit
consuming an **intermediate** carrier — heat at any grade, steam, recovered heat — adds
nothing. The heat was already paid for upstream, and charging it again at the point of use
would double-count every boiler in the stock.

**Grid electricity is not in that list, and the omission is deliberate.** It is `primary` but
`is_indirect`, so it is charged once on the import under §7.8 and never at the unit. Listing
it here — as an earlier statement of this rule did — charges a premise's own PV and CHP output
the grid factor, which is the error §7.8 exists to close.

**Recovered heat is emissions-free, and that is a real result rather than an accounting
trick.** A kiln's reject heat carries no fuel, so a heat pump drawing on it inherits no
emissions; the fuel that made it stays charged to the kiln. This is precisely why heat
recovery abates, and it works only because the rule above is stated rather than assumed.
V22 asserts all four legs.

### 7.7 Per-carrier intensities, and why they are a separate layer (D14)

A site that runs a CHP wants to know what its electricity is worth in gCO₂e per kWh, and so
does anyone reading its output rows. The number is legitimate; taking it from a second
emission factor is not.

**The trap.** Attach a factor to CHP electricity while also charging the CHP's gas under §7.1
and the same molecules are counted twice — once at the burner, once at the socket — and the
site total inflates by whatever the CHP generated. The same error appears in reverse if a
premise's self-generated electricity is charged the grid factor, which is what §7.8 closes.

**The structure.** Two layers, and they must not be added together:

| Layer | What it is | Sums to |
|---|---|---|
| **Accounted** (§7.1) | Emissions charged to the unit burning the fuel. One place, no allocation | The site's reported total. **This is the model's answer** |
| **Allocated** (§7.7) | Each generating unit's accounted emissions divided across the carriers it produces | Exactly its accounted emissions, by construction |

The allocation is therefore a view over the first layer and changes no total. It is what the
objective does **not** read: $Z^{\text{carbon}}_t$ is computed on the accounted layer, so a
change of allocation convention can never change a pathway.

**The convention.** Three are defensible and the choice must be stated in the scenario rather
than assumed:

| Method | Rule | Note |
|---|---|---|
| **Avoided boiler** (CHPQA) | Heat takes the fuel a reference boiler would have burned; the remainder goes to power | The UK convention, and the easiest to defend to a reviewer. **Recommended default** |
| Energy | Pro rata by output energy | Simplest; flatters power, because a kWh of electricity and a kWh of 90 °C water are not equivalent |
| Exergy | Pro rata by output exergy | The most physically honest and the least familiar |

**A premise's electricity then carries a weighted intensity**, not a single one: grid import at
the scenario's grid series, CHP output at its allocated figure, PV at zero. Which source
serves which load is not determined at annual resolution, so the convention is **pro rata by
generation share** — anything finer is precision the model does not have, and stating it is
what stops two implementations disagreeing.

**Rule (the two layers are reported side by side and never summed).** An output row carrying
an allocated intensity also carries the accounted figure it was derived from. V22 asserts the
accounted total; a further leg asserts that every unit's allocation sums back to it.

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
$(\texttt{unit\_id}, \texttt{carrier\_id}, \texttt{role})$ — §3.6's own key, and it takes the
role because the pair alone does not order a store's two rows on one carrier, nor a fired
capture train's. An unordered pair of rows is an unordered pair of columns in the LP, which is
exactly what V10 forbids. The price-wedge rule of §5.5 removes the
degeneracy that would otherwise let the solver report either of two equal-cost answers
(V21).

---

## 10. Validation

*Section last updated: 2026-09-17*

### 10.1 Scopes

Every test declares a scope: **load** (asserted once when reference data is read),
**premise** (asserted per premise solve), **batch**, or **release**.

### 10.2 The carrier-equivalent configuration

V1b compares this model against the coupled-off R run of §1.1 on the same 1,026 sites. The
comparison is only meaningful in a configuration where the two can agree, and that
configuration is defined here as precisely as §5.4 defines the pre-D11 cost baseline.
**All five conditions hold together:**

1. **One carrier per unit.** Every unit's carrier mix is pinned to a single primary carrier,
   so a unit's identity determines its fuel. **Automatic under D13** (§3.5, §3.6): this
   stopped being a configuration step and became how the library is keyed, so the condition
   now holds in every run rather than only in the comparison one.
2. **No storage.** No unit with `unit_class = storage`, and no hybrid unit.
3. **No onsite generation.** No unit in $U^{\text{gen}}$.
4. **C10, C11 and C12 inactive.** No grade cascade, no connection limit, no siting cap.
5. **No export.** $x_{c,k,t} = 0$ for every carrier, connection and period, so the objective
   carries no negative term.

Under these five conditions the carrier balance reduces to duty satisfaction plus a fuel
price, which is exactly what the R run computes.

**The comparison point.** One run of COMIT on the reference workbook with its cluster,
national-cap and headroom constraint functions switched off, so that each site is solved on
its own. What it produced is frozen — the objective, per-technology capacity by period, and
the cost, energy and emissions tables — with a manifest naming the workbook hash, the R
package commit, the solver version and the switches used. It is never rerun, and it is a
comparison point rather than ground truth: where the two models disagree, the checks that
need no other model — the invariants of §10.3 and §7.6's reconciliation — decide which one
is wrong. The
[COMIT-parity baseline specification](archive/2026-08-19-carb3-site-decarbonisation-implementation.md)
is what the frozen tables are read through; it is not built.

**The mapping.** COMIT's technology rows and this model's units are related through the
lineage table the data migration produces (Group B): every source row has exactly one
disposition — collapsed into a unit with a carrier binding, preserved as a unit, or dropped
with a reason. V1b compares through that table and nothing else, so a row it drops is
absent from both sides and a row it maps is compared unit for unit.

**What is compared, and how closely.** Objective per site, and energy per carrier per
period summed over the site. Which constraints bind is not compared: no row mapping exists
between the two models, and the R run has neither the price wedge nor the §9.3 tie-break,
so its degenerate choices are legitimately different. The tolerances are placeholders until
the first comparison confirms them:

| Quantity | Tolerance |
|---|---|
| Objective per site | within 0.5 percent |
| Energy per carrier per period, summed over the site | within 1 percent |

Every site outside tolerance is listed with a reason. The list is the deliverable, not a
pass mark.

### 10.3 Tests

| # | Scope | Blocking | Assertion |
|---|---|---|---|
| V1 | release | yes | The coupled-off R run of §10.2 exists, is bounded and optimal, and is frozen with its tables and manifest. Never rerun; a comparison point, not ground truth |
| **V1b** | release | yes | This model reproduces the R run's objective and per-carrier energy on the same 1,026 sites, in the carrier-equivalent configuration of §10.2, through the lineage table and within §10.2's tolerances |
| V2 | load | yes | `capacity_to_activity_factor` and `io_coefficient` round-trip per unit to 1e-6 |
| V4 | load | yes | Carrier consistency: every unit's declared carriers appear in `unit_input_output`, and profile uncertainty bands order correctly (R1–R3) |
| V5 | premise | yes | Emissions invariants over units, including biomass zero-rating **before** capture |
| V6 | premise | yes | No component of the objective is assumed non-negative — $Z^{\text{exp}}$ is genuinely negative |
| V10 | release | yes | Determinism: two identical runs agree, under the §9.3 tie-break |
| V11 | load | yes | Process sets resolve to exactly one tier per premise |
| V12 | premise | yes | Capacity bounds hold, including the siting cap, whose sum runs over area-bound units only |
| V16 | batch | yes | Connection peak is rebuilt correctly from the solved pathway |
| V17 | premise | yes | Vintage and stranding per unit. An abatement unit inherits the **minimum** remaining life over the hosts named in `unit_abatement_host` (§3.5.3), and strands nothing while any of them stands |
| **V18** | premise | yes | **Carrier balance closes to 1e-6 at every carrier node, every period** |
| **V19** | load | yes | No unit is eligible for a duty above its `grade_out`. Asserted at load, not per premise |
| **V20** | load | yes | Five legs, all on the archetype and hybrid-unit data — see below |
| **V21** | load | yes | The price wedge $p^{\text{exp}} < p^{\text{imp}}$ holds strictly for every carrier and period |
| **V22** | premise | yes | Emissions attribution closes across a carrier chain — four legs, see below |
| **V23** | load + premise | yes | A4's carrier mix resolves to exactly one tier per unit, tiers are tried in order, and `mix_evidence_tier` appears on every output row |
| **V24** | load + premise | yes | One measured row per key at the base year or a recorded substitution; no duplicate `(key, year)`; the optional entities of §3.1.1's table report rather than reject |
| **V25** | premise | yes | **History is never read.** Adding history rows at years both **before and after** the base year leaves every §5.3 parameter, every constraint coefficient, the solution, **and every reported reconciliation (§7.6)** identical to 1e-9 |
| **V26** | premise | yes | Validity intervals per `(premise_id, process_id)` are disjoint, at least one row is valid at the base year, and A2, A4 and §3.15's cohort read touch no row outside it |
| **V27** | load | yes | **Unit fuel identity (D13).** At most one row per unit carries `role = fuel_input`; two is rejected `unit_multi_fuel`. Auxiliary primary inputs — a capture train's electricity — are permitted and are not counted. Units flagged `draws_ambient` are exempt from V2's energy-closure leg and from nothing else |
| **V28** | load + premise | yes | **Process energy.** §3.3.1's `energy_share` sums to 1.00 ± 0.015 for every `(activity, set, vector)`; renormalisation over absent processes preserves that; a premise's sub-metered quantities never exceed its meter for a vector without being reported `submeter_exceeds_meter`; and `energy_evidence_tier` resolves per `(process, carrier)` |
| **V29** | premise | yes | **Disposal and allocation.** $d_{c,t}$ exists only where `carrier.may_dispose`, and every non-zero disposal appears as an output row. Every generating unit's §7.7 allocated emissions sum to its §7.1 accounted emissions to 1e-6, and no reported total adds the two layers together |
| **V30** | premise | yes | **Emissions close through the balance (D15).** Every emission carrier balances to 1e-6 like any other; §7's reported direct total equals the objective's $Z^{\text{carbon}}_t \div \pi_t \times 10^{3}$ exactly; a fuel's derived fossil and biogenic coefficients sum to its factor; and capture of a `zero_rated` carrier returns a **negative** contribution rather than zero |
| **V31** | load | yes | **Role and sign agree (§3.6).** `(unit_id, carrier_id, role)` is unique; `fuel_input`, `aux_input` and `emission_input` carry a negative coefficient and `primary_output`, `coproduct`, `reject` and `emission` a positive one; `emission` and `emission_input` appear on an emission carrier and no other role does. Exactly one `primary_output` per unit with coefficients |
| **V32** | load + premise | yes | **The site boundary is honoured (D16).** (a) connection-indexed $m_{c,k,t}$ and $x_{c,k,t}$ are declared only where `carrier.may_import` / `carrier.may_export` is true **and** a `premise_connection` row carries the carrier; site-level $m_{c,t}$ only where `may_import` is true and **no** connection carries it; nothing of either kind where the flag is false; (b) no `process_duty` row and no `activity_process_duty_profile` row names a `product` carrier whose `may_export` is false; (c) `may_import` and `may_export` are both false on every `emission` and every `intermediate` carrier. Failure names the carrier |
| **V33** | load + premise | yes | **Plant is named one unit at a time.** (a) every `premise_process_unit` row (§3.10.2) names a unit that `unit_eligibility` admits for that process at the premise's activity, the rows of one parent name distinct units, and `capacity_share` where given is present on every row of that parent and sums to 1 within 1e-6; (b) every `abatement` unit has at least one `unit_abatement_host` row (§3.5.3), each host is a `converter` on the same `process_id`, and no unit hosts itself; (c) the remaining life used for an abatement unit equals the **minimum** over its hosts. Failure names the unit |

**V20's five legs.**

- (a) ψ, β, χ ∈ [0, 1] and ε > 0 for every unit that declares them.
- (b) Every hybrid unit's `unit_bill_of_materials` shares sum to 1 and reconcile to its capex
  and capacity.
- (c) Every hybrid unit's lifetime is levelised over its components — no component lifetime
  exceeds the unit's $L$ without a replacement charge inside the annuity.
- (d) Every unit with `unit_class = storage` that is **named by no hybrid's bill of
  materials** has β set and ψ, χ, ε unset, since standalone storage may only earn through
  C11. "No hybrid parent" is a lookup against §3.5.2, not a flag: `battery_2h` is a
  component of `pv_battery_2h` and is exempt, `thermal_store_steam` is a component of
  nothing and is not.
- (e) Across the hybrid units sharing a pairing, each coefficient is **concave in the sizing
  ratio**. This is what makes LP interpolation between them err on the safe side, and it
  needs at least three ratios per pairing to be meaningful.

**V22's four legs.**

- (a) Total emissions equal the sum over units consuming **primary, non-indirect** carriers
  only, taken over every consuming role rather than `fuel_input` alone. No unit consuming an
  intermediate carrier contributes, and no unit is charged for the electricity or hydrogen it
  draws, both of which are charged on import under §7.8.
- (b) A chain `gas → boiler → heat@150-400C → dryer` books exactly the boiler's fuel, once.
- (c) A recovered-heat leg contributes zero, and the fuel that produced it remains charged to
  the rejecting unit.
- (d) **A secondary fuel is charged like a first fuel.** A unit holding a combustible
  `primary` carrier on `aux_input` — 55 rows do today — books its carbon. A unit holding
  `electricity` on `aux_input` — 29 rows — books none.

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
  parity against the R run         ───▶ V1b               release
  the R run exists and is frozen   ───▶ V1                release
  determinism under the tie-break  ───▶ V10               release
  base-year selection (D12)        ───▶ V24               load+premise
  off-vintage carrier substitution ───▶ V24               premise
  history isolation from the model ───▶ V25               premise
  process validity intervals       ───▶ V26               premise
  one primary carrier per unit     ───▶ V27               load
  ambient heat exempt from closure ───▶ V27 + V2          load
  storage and fired capture trains ───▶ V31               load
  process energy shares (§3.3.1)   ───▶ V28               load+premise
  sub-metered process energy       ───▶ V28               premise
  carrier disposal (§5.2)          ───▶ V29               premise
  emissions allocation (§7.7)      ───▶ V29               premise
  fuel CO2 as a carrier (D15)      ───▶ V30 + V18          premise
  biogenic split before capture    ───▶ V30 + V5           premise
  site boundary on the carrier     ───▶ V32               load+premise
  known plant, one row per unit    ───▶ V33               load+premise
  abatement host set and life      ───▶ V33 + V17          premise
  internal product has no duty     ───▶ V32 (b) + V18      premise
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
| 11 | A carrier a unit produces and nothing consumes cannot balance, so a physically fine premise is infeasible — vented process CO₂ before capture exists, reject heat before a heat pump is built | V18 + V29 | $d_{c,t}$ (§5.2), gated on `carrier_kind`, and reported as a quantity rather than absorbed |
| 12 | A shared multi-fuel unit carries one capex, one lifetime and one eligibility row for fuels that differ in all three, and `max_share` cannot cap one fuel without capping every fuel | V27 | Load assertion; D13 keys the unit per fuel (§3.5) |
| 13 | A CHP's electricity is given its own emission factor on top of its fuel being charged, and the site total inflates by whatever it generated | V29 | §7.7's two layers; the objective reads only the accounted one |
| 14 | A premise generating its own electricity is charged the grid factor on power that never came off the grid | V29 | §7.8 — an indirect carrier is charged on $m_{c,k,t}$, not on consumption |
| 15 | A product a downstream unit consumes is given a duty as well, so C1 (duty satisfaction) and C8 (carrier balance) compete for the same tonne and one of them must fail | V32 (b) + V18 | Load assertion on the duty tables, premise assertion on the node |
| 16 | A capture train is named one host of several, so two thirds of a co-firing kiln's CO₂ has no route to it and the train's life is read off whichever host happened to be named | V33 (b) + V17 | Load assertion on the host table, premise assertion on the inherited life |

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

*Section last updated: 2026-09-17*

Two examples, both written, each a document of its own because each is long enough to be one
and because both are published as test fixtures. They share a thirteen-section structure so
that the same step can be read side by side in either.

| Example | What it exercises |
|---|---|
| [A cement works](2026-08-28-carb3-site-energy-system-worked-example-cement.md) | **The parity case.** One chemistry node at the top grade, a mass denominator (D5), two products, tier-1 vintage with a 2004 cohort, the stranding charge, a CCS train as an abatement unit inheriting its host's remaining life, a footprint-proxy area against C12, C11 breached by the capture train's auxiliary load, §7.6 reconciling to 1.96%, and §10.2's carrier-equivalent configuration, which is what V1b compares |
| [A food and drink site](2026-08-28-carb3-site-energy-system-worked-example-food-drink.md) | **The mechanism case.** `IFDLTH`, `IFDSTM`, `IFDDRY`, `IFDREF` and `IFDMOT`: the cross-sector collapse — 84 low-temperature-heat rows across eleven sectors to eight units, of which this dairy reaches seven — a 120 °C duty with boiler, CHP, heat pump and electric resistance competing under C10, a heat pump refused at the 200 °C drying duty, a reject-heat leg from the dryer feeding a heat pump, an existing CHP made visible by §3.16 and producing heat **and** electricity into the carrier balance, PV bounded by C12 while the CHP is not, and surplus electricity exported below the import price |

**Cement alone is not sufficient**, and the reason is structural rather than a matter of
taste: cement carries exactly two process codes, `ICMCLK` and `ICM`. There is no `LTH`, no
`STM`, no `DRY` and no `SPC`, so nothing cascades, the candidates differ by *fuel* rather
than by device, no low-grade duty exists to receive reject heat, and CHP appears only fused
inside bundled capture rows. A worked example on a cement works would demonstrate everything
except the mechanism this model exists for.

**Neither example is sufficient alone, and the pair is deliberate.** Between them they cover
both denominators of D5, both branches of §3.1.1's base-year rule (a base-year row, and a
substitution from the nearest year), both branches of §7.6 (a reconciliation that runs, and
one reported as `emissions_year_unmatched`), all three tiers of §4.1's carrier-mix ladder, and
both areas of evidence for C12 (a measured survey and a floorspace proxy). The food and drink
example is milestone M4's exit gate; the cement one is M2's.

**Both documents carry an open-points table**, and four entries are shared between them: the
absence of any per-premise tier over
[`../notes/data/activity_process_energy_profile.csv`](../notes/data/activity_process_energy_profile.csv);
C8 (carrier balance)'s lack of a disposal route for a carrier nothing consumes; §7's
attribution once electricity is generated on site; and the service carrier a `MOT` or `REF`
duty needs. They are recorded there rather than closed there, and T23 (complete §5) owns the
last three. **A fifth shared entry is closed and should be dropped from both tables**: §3.3.1
makes that file the input that sizes a premise's processes, not the parity target §3.3 once
treated it as.

**The cement document's product-carrier point is closed by D16.** It recorded that a `product`
carrier consumed by a downstream unit had no route through C8 (carrier balance) that also
satisfied C1 (duty satisfaction) — the kilns' clinker is drawn by the grinder, C1 wanted it
dispatched to a duty, C8 wanted it released to the balance, and doing both counted the same
tonne twice. D16 removes the duty: an internal product is a carrier with `may_import` and
`may_export` both false, it presents no `process_duty` row (§3.9), and it reaches its consumer
through C8 by way of $z^{\circ}$. V32 guards it.

**The two singular-plant points are closed by a pair of child tables.** Both documents recorded
that one field could name only one unit where D13 (one primary carrier per unit) routinely makes
several: §3.10 named a process's installed plant with a single `unit_id`, and `unit` named a
capture train's host with a single field. Neither survived a co-firing kiln, which is three
units with one capture train bolted to the line. §3.10.2 `premise_process_unit` and §3.5.3
`unit_abatement_host` replace them with one row per unit and one row per host; the train inherits
the earliest remaining life over its hosts (C3, capacity transfer; C4, incumbent ageing) and
strands nothing while any host stands. V33 (plant is named one unit at a time) guards both.
