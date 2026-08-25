# CaRB3-Driven Per-Site Decarbonisation — Implementation Specification

**Status:** Draft v1 for review
**Date:** 2026-08-19
**Vision and rationale:** [2026-08-19-carb3-site-decarbonisation-vision.md](2026-08-19-carb3-site-decarbonisation-vision.md)
**Supersedes:** [2026-08-05-site-heterogeneity-prd.md](2026-08-05-site-heterogeneity-prd.md)

---

## 1. Scope, inputs, conventions, and how to read this

*Section last updated: 2026-08-25*

### 1.1 What this document is

A complete build specification for a model that takes one record per GB Factory-class
premise — CaRB3 activity plus current energy consumption by vector — and produces a
least-cost decarbonisation pathway for each.

It specifies **what to build**, not what already exists. Where behaviour is inherited
from COMIT, this document states the rule and cites where COMIT currently implements it,
so the rule can be verified against a working model.

### 1.2 Language-agnostic conventions

This specification is implementable in **R or Python** without rewriting. To keep that
true, it holds to four rules:

1. **Data structures are entities** — named collections of typed fields with declared
   keys, units and validation rules. Never "data frame", "tibble", or "DataFrame".
2. **Logic is numbered pseudocode** with explicit inputs, outputs, preconditions,
   postconditions and failure modes. No language idioms.
3. **The optimisation is stated mathematically** — sets, parameters, variables,
   objective, constraints (§5). This is the authoritative definition of the model.
4. **COMIT's R code is cited as description, not as implementation to copy.** A
   reference like `R/fct_emissions.R:234` means *"the current model does X here; verify
   your implementation against it"*, not *"port this function"*.

Solver-specific concerns are confined to **§9.3**. Everything else is solver-neutral.

**Section dates.** Every `##` section carries a *Section last updated* line. They are not
decoration: this document is edited section by section, and the oldest dates are where
staleness accumulates. The three oldest sections at the last review — §6, §8 and §12,
all dated 2026-08-20 — were also the three found to be out of date with the data model.
When reviewing, start at the top of the date order, not the top of the document.

### 1.3 Notation

- Entity field tables use: `field · type · unit · required · key · validation`.
- Types are abstract: `string`, `integer`, `real`, `boolean`, `enum{...}`, `date`.
- `⟨entity⟩.⟨field⟩` refers to a field; `→` denotes a foreign key.
- Pseudocode is 1-indexed and uses `FOR EACH`, `IF`, `ASSERT`, `FAIL`.

**Labelled references.** Four label families are used throughout, often before the
section that defines them:

| Label | Meaning | Defined in |
|---|---|---|
| `A1`–`A9` | Algorithms — the processing steps, in order | §4 |
| `S1`–`S9` | Stages — the pipeline components that run those algorithms | §2.1 |
| `C1`–`C9` | Constraints of the per-premise optimisation | §5.5 |
| `V1`–`V16` | Validation tests and acceptance criteria | §10 |
| `D1`–`D10` | Design decisions | [Vision doc §6](2026-08-19-carb3-site-decarbonisation-vision.md) |

**The algorithms at a glance**, since §1.6 refers to several of them before §4 arrives:

| | Algorithm | What it does |
|---|---|---|
| **A1** | Ingest and validate | Accepts premise records, assigns each to a cluster, rejects bad rows with a reason |
| **A2** | Expand to process set | Turns a premise's activity into the list of processes it runs |
| **A3** | Allocate energy | Splits the premise's metered energy across those processes |
| **A4** | Back-solve capacity | Infers what equipment capacity must already exist to consume that energy |
| **A5** | Apply scenario | Attaches prices, carbon price and H₂/CO₂ availability |
| **A6** | Build problem | Constructs the per-premise optimisation |
| **A7** | Solve and extract | Runs the solver, handles infeasibility, pulls results out |
| **A8** | Assemble output | Produces the per-premise pathway tables |
| **A9** | Aggregate and compare | Rolls results up to GB and compares against ECUK/GHGI |

A1–A8 run once per premise and are independent across premises (D2). A9 runs once over
all results.

### 1.4 Glossary

| Term | Meaning in this document |
|---|---|
| **Premise** | One physical site in the CaRB3 building stock. The unit of assessment. |
| **Activity** | A CaRB3 classification of what a premise is (e.g. `Cement Works`). 55 in the Factory class. |
| **Process** | A unit operation performed at a premise (e.g. `Calcination`, `Welding`). The middle level of the CaRB3 taxonomy. |
| **Energy service** | COMIT's existing middle level (high-temperature heat, motor drive). A *process* may map onto one. |
| **Technology** | A specific way of performing a process, distinguished by equipment type **and fuel**. The decision variable's subject. |
| **Vector** | The grouping an energy carrier belongs to: electricity, gas, oil, coal, biomass, or `other`. Used to join the energy profile (§3.3). Each `premise_energy` row also names its specific `commodity_id`, so a carrier such as waste-derived fuel is an ordinary row rather than a special case. |
| **Commodity** | A modelled flow — a fuel, an intermediate material, a process-emission pseudo-commodity, or a process's output. |
| **Denominator** | The unit a technology's coefficients are expressed per: PJ of useful energy, or a physical mass. See D5. |
| **Process set** | A named route through an activity — e.g. kraft versus recycled fibre at a paper mill. Each activity has one default set plus any named alternatives (§3.2, D10). |
| **Evidence tier** | Which quality of evidence produced a value. Used in three places with three separate scales: process detail (`site_known` / `named_set` / `activity_default`, §A2), energy profile (`metered` / `published_sec` / `engineering` / `fallback`, §3.3.2), and cost provenance (`comit_reuse` / `bref` / `proxy`, D6). |
| **Utilisation** | The fraction of its capacity a technology actually runs at. Back-solved in A4 where capacity is known, and equal to the availability factor where capacity is inferred instead (§A4). |
| **Load shape** | How a process presents its demand over time — its class, duty factor and peak-to-mean ratio (§3.13). A property of the process, not of the technology serving it. |
| **Period** | One model time step. Periods run from `start_year` to `end_year` in steps of `timestep`. |

### 1.5 Design decisions assumed

This document implements decisions D1–D10 recorded in the vision document. The three
with the widest reach:

- **D2 — per-site independent solves.** Each premise is a separate optimisation. No
  constraint may couple two premises. Any requirement that appears to need cross-site
  information must be resolved into a per-site scenario input (§6.2) or a post-hoc
  comparison (§6.3).
- **D5 — hybrid denominators.** Each process declares whether its coefficients are
  denominated in energy or in physical mass.
- **D10 — tiered site intelligence.** Where a premise's actual processes, capacities or
  reported emissions are known, they replace the activity default outright. Tiers are
  exclusive, and every output row records the tier it came from.

### 1.6 What the building stock model must supply

This is the **interface contract with the upstream CaRB3 building-stock model** (D4),
stated here in full because everything downstream depends on it and because it is the
one part of this specification addressed to someone outside the modelling team.

Nothing in this document derives baseline energy. The stock model is authoritative for
what a premise *is* and what it *currently consumes*; this model decides only what it
could do instead. §3.1 is the normative field-level contract with validation rules —
this section states the requirement and why each item exists.

#### 1.6.1 The unit of delivery

**One record per premise, per data year, with a stable identifier.** `premise_id` must
refer to the same physical site across re-runs and across vintages of the stock model;
results are keyed on it and cannot be compared over time otherwise.

#### 1.6.2 Required for every premise

| Item | Unit | Why it is needed | Without it |
|---|---|---|---|
| `premise_id` | — | Keys every output row; joins results across runs | No stable results; no time comparison |
| `carb3_activity` | — | Selects the process set (A2) and the technology set | The premise cannot be expanded into processes at all |
| `premise_energy` rows — one per carrier | PJ/yr | Split across processes (A3), then back-solved into implied capacity (A4). Biomass rows also drive zero-rating (§7.3) | No baseline; nothing to decarbonise from |
| `latitude`, `longitude` | degrees | Assigns the premise to one of the 9 GB clusters (A1 step 11), which determines H₂/CO₂ availability (D7) | No infrastructure scenario can be applied |
| `nation` | enum | Enforces GB scope (D8) | NI premises contaminate GB aggregates |
| `data_year` | year | Provenance; anchors the baseline in time | Results cannot be dated or rebased |
| `source` | — | Provenance; supports the confidence reporting in §8.6 | Result quality cannot be characterised |

**The five energy vectors must be supplied separately.** A single total-energy figure is
not sufficient: A4 back-solves existing capacity by matching each vector to the
technologies that can consume it, so a total with no split cannot identify what equipment
the site currently runs. This is the single most important requirement in this section.

Energy arrives as **one row per carrier** (§3.1.1) rather than as fixed columns, so a
carrier outside the five main vectors — LPG, waste-derived fuel, purchased heat — is just
another row. Two consequences for the stock model:

- **State all five main vectors for every premise**, using an explicit zero with
  `data_status = not_consumed` where a carrier genuinely is not used.
- **An absent row means "not assessed", not "zero".** The distinction is preserved
  deliberately, and premises with incomplete carrier coverage are reported as such
  (§8.6). Absence should be a last resort.

#### 1.6.3 Required for some premises

| Item | Unit | When required | Why |
|---|---|---|---|
| `premise_throughput` rows — one per product | Mt/yr | Activities carrying a mass-denominated process (D5) | Process emissions are kt CO₂ per tonne of material. Without physical throughput they have no denominator and cannot be modelled — and these are exactly the activities where process emissions dominate |
| `data_status` on every energy and throughput row | — | Always | Distinguishes a measured zero from an unassessed carrier, and a measured tonnage from an estimated one |

#### 1.6.4 Optional, and what it buys

Everything below is genuinely optional — the model runs without any of it. But each item
replaces an assumption with a fact for the premises that have it, and the tier used is
recorded on every output row, so a reader can always tell a known site from an assumed
one.

| Item | Unit | What it enables |
|---|---|---|
| `floorspace` | m² | Cross-checking energy intensity on ingest; a fallback basis for site-services energy where the profile needs one |
| Additional `premise_energy` rows | PJ/yr | Carriers outside the five main vectors — LPG, waste-derived fuel, purchased heat. No schema change needed; each is simply another row |
| Additional `premise_throughput` rows | Mt/yr | Multi-product sites — a paper mill making several grades, a chemical site with several outputs — each stated separately rather than collapsed into one tonnage |
| `process_set_id` | — | Selects a known process route instead of the activity default — e.g. a kraft versus recycled-fibre paper mill (§3.2). One field, and it replaces an activity-wide average with the right route for that site |
| `premise_process_detail` rows | — | The site's actual process list, and where known its installed technology, capacity and commissioning year (§3.10). Highest tier of process evidence; A4 then infers utilisation rather than guessing capacity |
| `premise_measured_emissions` rows | kt CO₂e/yr | Reported emissions from UK ETS, permits or NAEI (§3.11). Reconciles the computed baseline, corrects the combustion/process split, and optionally calibrates process intensity (§7.6) |
| Operating schedule — `operating_pattern`, `operating_hours_per_year`, `operating_days_per_week`, `shutdown_weeks` | h/yr, d/wk, wk/yr | The independent check on utilisation (§3.12, A4). A site running 24/7 and one running a single shift can consume identical annual energy on very different plant, and only the schedule distinguishes them |
| Load statistics — `peak_electricity`, `peak_gas`, `load_factor_electricity`, `load_factor_gas`, `within_shift_peak_factor` | MW, fraction, ratio | **Future use (§5.6).** The true site peak, which is what a connection capacity is about. Derived from half-hourly or daily metering where it exists; gas is the better predictor of the *post-electrification* peak |
| `premise_weekly_profile` rows | fraction, MW | **Future use (§5.6).** A representative half-hourly week — 336 points per vector — plus the separately-recorded annual peak (§3.14). Gives observed diversity between processes rather than an assumed factor, and is the calibration point for any projected peak |
| `import_capacity` | MW | **Future use (§5.6).** How much electrification the connection physically allows before reinforcement is needed |
| `export_capacity` | MW | **Future use (§5.6).** Whether onsite generation can be exported, and how much |
| `connection_voltage` | kV | **Future use (§5.6).** Sets which reinforcement cost curve applies |
| `onsite_generation_capacity`, `onsite_generation_type` | MW, — | **Future use (§5.6).** Existing generation to be represented rather than double-counted |

**On schedules versus load statistics.** They are not two grades of the same thing. A
schedule gives *mean* demand during operating hours; a metered profile gives the *peak*.
The gap between them is real and always in the same direction — the mean understates the
peak — so a schedule is a floor to be adjusted upward, not a substitute for measurement
(§5.6). Sites supplying both are disproportionately valuable, because they let the
adjustment factor be observed rather than assumed and then applied to every site that has
only a schedule.

**On the four network fields.** Nothing in the model reads them today. They are requested
now because they are far cheaper to collect while the stock model is being built than to
retrofit later, and because two planned extensions — reinforcement cost in the objective,
and onsite generation with export — cannot be built at all without them. See §5.6, which
also flags that a **load factor** will be needed to connect annual energy to peak power.

#### 1.6.5 What the stock model does *not* need to supply

Bounding the ask matters as much as stating it. The stock model is **not** expected to
provide:

- **Emissions.** Computed here from energy and emission factors (§7). This is the point
  of D4 — COMIT's existing dependency on CO₂ point-source data is what made most
  premises unmodellable, and supplying energy directly removes it.
- **Existing plant, capacity, or equipment lists.** Back-solved in A4 from energy.
- **The split of energy across processes.** That is
  `activity_process_energy_profile` (§3.3), a per-*activity* assumption maintained by
  the modelling team, not per-premise data. Note the distinction from §3.10: a known
  process *list* and its capacities are very welcome where they exist; the *share of
  energy* each process takes is the modelling team's problem either way.
- **Costs, technology options, or fuel prices.** Scenario inputs (§3.8).
- **Anything about the future.** The record is a snapshot of the present; all projection
  happens here.

#### 1.6.6 Quality requirements

1. **Units as stated** — PJ/yr for energy, Mt/yr for throughput. Deliveries in kWh, GWh,
   or tonnes must be converted upstream, not guessed at on ingest.
2. **Activity vocabulary** — every `carb3_activity` must be one of the 55 Factory-class
   activities (D1). Premises outside that class should not be sent at all; if sent, they
   are rejected rather than approximated.
3. **Non-negative energy, and at least one vector strictly positive.** A zero-energy
   premise is not modellable.
4. **GB only** — England, Wales, Scotland (D8).
5. **Consistent vintage** — a batch should share a `data_year`, or carry the differences
   explicitly. Mixed vintages silently distort GB aggregates.
6. **Coverage stated, not implied.** The batch should say what fraction of the
   Factory-class stock it represents, since §8.6 reports results against it and A9
   compares aggregates to ECUK/GHGI.

#### 1.6.7 What happens when a requirement is not met

A1 rejects rather than repairs, and every rejection is logged with a reason. Silent
imputation is not permitted — a missing input must remain visible in the rejection log.

| Reason | Trigger |
|---|---|
| `out_of_scope_nation` | `nation` is not England, Wales or Scotland |
| `out_of_scope_activity` | A recognised CaRB3 activity outside the Factory class |
| `unknown_activity` | An activity string matching no known CaRB3 activity |
| `no_energy` | Total energy across all vectors is zero |
| `negative_energy` | Any vector is negative |
| `missing_throughput` | Mass-denominated activity with no `premise_throughput` row |
| `vector_commodity_mismatch` | A `premise_energy` row whose `vector` contradicts its commodity's category |

**Batch-level gate.** If the rejection rate exceeds a configured threshold, the whole
batch fails rather than proceeding on a filtered subset — a high rejection rate signals
a contract mismatch, not a data-cleaning opportunity.

---

## 2. System overview

*Section last updated: 2026-08-25*

### 2.1 Components

| # | Component | Responsibility |
|---|---|---|
| S1 | **Ingestion and validation** | Accept premise records, validate, reject with reasons |
| S2 | **Process expansion** | Premise → its set of processes, resolving the three evidence tiers of D10 (§A2) |
| S3 | **Energy allocation** | Split the premise's metered energy across its processes |
| S4 | **Baseline capacity solve** | Back-solve implied existing capacity per process — or, where capacity is known, back-solve utilisation instead (§A4) |
| S5 | **Scenario application** | Attach fuel prices, carbon price, infrastructure availability |
| S6 | **Problem builder** | Construct the per-premise optimisation (§5) |
| S7 | **Solver driver** | Solve, extract, handle infeasibility |
| S8 | **Output assembly** | Produce the per-premise pathway tables (§8) |
| S9 | **Aggregation and comparison** | Roll up to GB; compare against ECUK/GHGI |

S1–S8 run per premise and are independent across premises. S9 runs once over all
results.

### 2.2 Data flow

```
premise_record ──S1──► validated premise
 + premise_energy            (§3.1.1, one row per carrier)
 + premise_throughput        (§3.1.2, one row per product)
                        │
                        ├─S2─► process set              (activity_process_register)
                        ├─S3─► energy per process       (activity_process_energy_profile)
                        ├─S4─► implied existing capacity (technology, technology_input_output)
                        └─S5─► prices, availability     (scenario_parameters, infrastructure_scenario)
                                    │
                                    ▼
                              S6 build problem ──► S7 solve ──► S8 site_pathway
                                                                     │
                                                                     ▼
                                                          S9 aggregate → GB comparison
```

### 2.3 Boundaries

**In scope:** everything from a validated premise record to a per-premise pathway, plus
GB aggregation.

**Out of scope:** deriving the premise's baseline energy (upstream, D4); deciding
infrastructure build-out (exogenous, D7); enforcing a national emissions budget
(reported only); Northern Ireland (D8).

### 2.4 Geographic scope

Great Britain — England, Wales, Scotland. Consequences the implementation must honour:

- Cluster list is **9**, not 10. `Londonderry` is removed.
- One premise in COMIT's current site data sits in Scotland but is assigned to the
  Londonderry cluster; it must be reassigned to its nearest in-scope cluster on ingest.
- All aggregate comparisons are on a **GB** basis. Comparing against UK-wide GHGI totals
  without adjustment is an error.

---

## 3. Data model

*Section last updated: 2026-08-25*

Nine entities. Each is specified as a field table. Types are abstract (§1.3).

### 3.1 `premise_record` — the premise itself

The interface between the CaRB3 stock model and this model is three entities: this one,
plus `premise_energy` (§3.1.1) and `premise_throughput` (§3.1.2). One row per premise
here; the other two are long tables keyed on `premise_id`. Stated in requirement terms,
with rationale, in **§1.6**; these tables are normative for validation.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK | Unique, stable across runs |
| `carb3_activity` | string | — | yes | → `activity_process_register` | Must match one of the **55 CaRB3 Factory-class activities** (D1). Any other class is rejected with reason `out_of_scope_activity`; an unrecognised string with `unknown_activity` (§1.6.7) |
| `latitude` | real | degrees | yes | — | Within GB bounding box |
| `longitude` | real | degrees | yes | — | Within GB bounding box |
| `nation` | enum{England, Wales, Scotland} | — | yes | — | NI rejected with reason `out_of_scope_nation` |
| `floorspace` | real | m² | no | — | > 0 if present |
| `process_set_id` | string | — | no | → `activity_process_register` | Selects a named non-default process set (§3.2). Absent ⇒ the activity's default set |
| `import_capacity` | real | MW | no | — | > 0 if present. Agreed grid import capacity at the connection point |
| `export_capacity` | real | MW | no | — | ≥ 0 if present. Agreed export capacity; 0 ⇒ export not permitted |
| `connection_voltage` | real | kV | no | — | > 0 if present. Distinguishes LV/HV/EHV connections for reinforcement costing |
| `onsite_generation_capacity` | real | MW | no | — | ≥ 0 if present |
| `onsite_generation_type` | string | — | no | → `technology` | Required if `onsite_generation_capacity` > 0 |
| `data_year` | integer | year | yes | — | Provenance |
| `source` | string | — | yes | — | Provenance |

Energy and throughput are **not** columns here. Both are one-to-many — a premise consumes
several carriers and may make several products — so both are long tables keyed on
`premise_id`, matching the shape already used by `premise_measured_emissions` (§3.11) and
`premise_weekly_profile` (§3.14).

#### 3.1.1 `premise_energy` — consumption by carrier

One row per premise per carrier. Replaces the fixed `energy_electricity` … `energy_other`
columns: a new carrier is a new row, not a schema change, and the `energy_other` /
`energy_other_carrier` pair disappears because every carrier now names itself.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `commodity_id` | string | — | yes | PK part | → `commodity`. The carrier as metered |
| `vector` | enum{electricity, gas, oil, coal, biomass, other} | — | yes | — | The grouping used to join `activity_process_energy_profile` (§3.3). Must be consistent with the commodity's `commodity_category` |
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
  is reported as having incomplete carrier coverage (§8.6).

The stock model should aim to state all five main vectors for every premise, whether by a
positive quantity or an explicit zero. Absence is a last resort, not the default.

**Rule (one row per carrier).** `(premise_id, commodity_id)` is unique. A site with two
gas meters is one row; meter-level detail belongs upstream.

#### 3.1.2 `premise_throughput` — physical output by commodity

One row per premise per product. Long for the same reason, and it lifts a real
limitation: the previous single `throughput_quantity` column could not represent a site
making more than one product, which paper, chemicals and food sites routinely do.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `commodity_id` | string | — | yes | PK part | → `commodity`. Must have `denominator_kind = mass` (D5) |
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
| `process_id` | string | — | yes | PK part | → `commodity.commodity_id` |
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
rows in `activity_process_energy_profile`, directly or by inheritance (§3.3), or the set
cannot be modelled.

**Rule.** `process_set_id` must be valid *for the premise's activity*. A set belonging to
a different activity is rejected on ingest with reason `invalid_process_set`.

### 3.3 `activity_process_energy_profile` — how energy splits across processes

**The weakest link in the design** (vision §10). The premise record supplies *total*
energy per vector; the model needs it per process.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `carb3_activity` | string | — | yes | PK part | → `activity_process_register` |
| `process_set_id` | string | — | yes | PK part | → `activity_process_register`. Use the activity's default set unless the variant genuinely splits energy differently |
| `process_id` | string | — | yes | PK part | → `activity_process_register` |
| `vector` | enum{electricity, gas, oil, coal, biomass, other} | — | yes | PK part | — |
| `energy_share` | real | fraction | yes | — | ∈ [0, 1] |
| `share_low` | real | fraction | no | — | ∈ [0, 1]; ≤ `energy_share`. Lower bound of the sensitivity band (§3.3.5) |
| `share_high` | real | fraction | no | — | ∈ [0, 1]; ≥ `energy_share`. Upper bound of the sensitivity band |
| `evidence_tier` | enum{metered, published_sec, engineering, fallback} | — | yes | — | §3.3.2 |
| `provenance` | string | — | yes | — | Citation: document, table, page — not just a source name |
| `confidence` | enum{high, medium, low} | — | yes | — | Derived from `evidence_tier` per §3.3.2; reported alongside results |

**Rule (must be asserted at load).** For each `(carb3_activity, process_set_id, vector)`,
the sum of `energy_share` over processes equals 1 within 1e-6. A profile that does not
sum to 1 silently loses or creates energy.

**Rule (inheritance).** A non-default process set need not restate every row. Where a
`(process_id, vector)` combination has no row for that set, the default set's row is
inherited, and the renormalisation of R2 (§3.3.3) then restores the sum-to-1 invariant
over whichever processes the set actually contains. A set therefore only has to state
the shares it genuinely changes.

#### 3.3.1 What the profile has to contain

One row per `(activity, process, vector)` that can carry energy. For each of the 55
Factory-class activities:

1. **The process list** — already available from
   [`../notes/data/carb3_factory_processes.json`](../notes/data/carb3_factory_processes.json).
2. **Which vectors each process can consume.** A grinding mill takes electricity and
   nothing else; a kiln takes coal, gas or biomass but not electricity unless an electric
   variant exists. Combinations that cannot occur are simply absent — absent is not the
   same as a zero share, and §3.3.3 depends on the distinction.
3. **A share per surviving combination**, summing to 1 down each `(activity, vector)`
   column.
4. **A citation and an evidence tier** for every row.

The quantity being split is the premise's **metered energy for one vector**. The profile
never moves energy between vectors — that is the optimiser's job. It only answers: *of
the gas this site burns, how much goes to the kiln versus the dryer?*

#### 3.3.2 Evidence tiers

Mirrors the cost provenance tiers of D6, and maps to `confidence` the same way.

| Tier | What it is | Typical source | `confidence` |
|---|---|---|---|
| `metered` | Sub-metered or audited data for the actual process | Site energy audits, ESOS assessments, sector monitoring programmes | high |
| `published_sec` | Specific energy consumption per unit operation from a published breakdown | BREF/BAT documents, trade association benchmarks (e.g. mineral products, steel, paper), sector decarbonisation roadmaps | high / medium |
| `engineering` | Built up from an equipment inventory — rated load × utilisation × hours | Equipment lists, motor schedules, first-principles heat balances | medium |
| `fallback` | A generic profile for an activity with no breakdown available | A sibling activity's profile, or a generic light-manufacturing split | low |

**Rule.** An activity profiled entirely at `fallback` tier is usable but must be flagged
in outputs (§8.6), and its per-process results should not be published on their own —
only the premise total, which is unaffected by the split.

#### 3.3.3 Rules the profile must satisfy

Beyond the sum-to-1 rule above:

**R1 — Technology consistency.** If the profile gives process *q* a non-zero share of
vector *v*, at least one technology serving *q* must have `fuel_category` matching *v*.
Otherwise A4 fails at step 4 with "no technology serves process q on vector v". Assert
this at load, when it is cheap to diagnose, rather than mid-run.

**R2 — Renormalisation for absent processes.** `activity_process_register.is_optional`
allows a premise to lack a process its activity normally has. The shares then no longer
sum to 1, and A3 would lose energy. Renormalise over the processes actually present:

```
FOR EACH vector v:
1.    present := { q IN process_set(p) : profile[activity, q, v] EXISTS }
2.    denom   := SUM over q IN present OF energy_share[activity, q, v]
3.    IF denom = 0 AND premise_energy[p, v].quantity > 0:
4.        FAIL "premise consumes vector v but no present process can use it"
5.    FOR EACH q IN present:
6.        share'[q, v] := energy_share[activity, q, v] / denom
```

A3 uses `share'`, not the raw share. With no optional processes absent, `denom = 1` and
`share' = share`, so the common case is unchanged.

**R3 — Band ordering.** Where `share_low` and `share_high` are given,
`share_low ≤ energy_share ≤ share_high`. The bands need not sum to 1 across processes;
§3.3.5 says how they are used.

#### 3.3.4 Worked examples

Illustrative values, shown to fix the shape of the data. **Every number below must be
replaced by a cited figure before use** — they are exactly the kind of estimate the
`provenance` field exists to make auditable.

**Example A — `Cement Works`.** Energy-intensive, mass-denominated, carries process
emissions. The clearest case, because published breakdowns exist and the thermal and
electrical stories are completely different.

| Process | Electricity | Coal / gas / biomass |
|---|---|---|
| `quarry_crushing` | 0.08 | — |
| `raw_milling` | 0.24 | 0.03 |
| `kiln_pyroprocessing` | 0.22 | 0.97 |
| `clinker_cooling` | 0.06 | — |
| `cement_milling` | 0.34 | — |
| `packing_dispatch` | 0.06 | — |
| **Sum** | **1.00** | **1.00** |

Thermal energy is almost entirely the kiln, with a little for raw material drying.
Electricity is dominated by the two milling stages — which is why an electricity-side
result for a cement works is really a statement about grinding, not about the kiln.
Tier: `published_sec`, confidence high.

**Example B — `Bread and Flour Confectionery`.** Mid-intensity, energy-denominated, no
process emissions. Site services are a material share rather than a rounding error.

| Process | Electricity | Gas |
|---|---|---|
| `ingredient_handling` | 0.05 | — |
| `mixing` | 0.14 | — |
| `proving` | 0.03 | 0.06 |
| `baking_ovens` | 0.08 | 0.82 |
| `cooling_refrigeration` | 0.32 | — |
| `packaging` | 0.16 | — |
| `site_services` | 0.22 | 0.12 |
| **Sum** | **1.00** | **1.00** |

Note `baking_ovens` appears on both vectors — 0.82 of the gas for the burners, 0.08 of
the electricity for fans and controls. That is normal and R1 is satisfied as long as
both a gas-fired and an electric oven technology exist. Tier: `published_sec` for the
ovens, `engineering` for the rest, confidence medium.

**Example C — `Fabricated Metal Products`.** Low-intensity, energy-denominated, and the
case with no published unit-operation breakdown — the situation most of the 55
activities will be in.

| Process | Electricity | Gas |
|---|---|---|
| `cutting` | 0.14 | — |
| `welding` | 0.22 | — |
| `machining` | 0.26 | — |
| `surface_treatment` | 0.10 | 0.35 |
| `assembly` | 0.06 | — |
| `site_services` | 0.22 | 0.65 |
| **Sum** | **1.00** | **1.00** |

Built from an equipment inventory, not a citation. Tier: `engineering` shading to
`fallback`, confidence low. Per-process results here carry little weight; the premise
total still does, because the split does not change it.

#### 3.3.5 Sensitivity

The profile is an assumption applied identically to every premise of an activity, so its
error is **systematic, not random** — it does not average out across the stock. Treat it
as follows:

1. Where `share_low` / `share_high` are populated, re-run the affected premises at both
   bounds and report the spread on per-process outputs. Premise totals are invariant.
2. Report the `confidence` distribution alongside every aggregate (§8.6), so a reader can
   see how much of a result rests on `fallback`-tier splits.
3. Any conclusion that flips between the low and high bound must be reported as
   unresolved, not as a finding.

### 3.4 `commodity` — extended

Extends COMIT's `commodities` sheet with a denominator declaration (D5).

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `commodity_id` | string | — | yes | PK | — |
| `description` | string | — | yes | — | — |
| `commodity_kind` | enum{fuel, process_output, intermediate, process_emission} | — | yes | — | — |
| `denominator_kind` | enum{energy, mass} | — | yes | — | **D5.** `energy` ⇒ unit PJ; `mass` ⇒ unit Mt |
| `unit` | string | — | yes | — | Consistent with `denominator_kind` |
| `commodity_category` | string | — | yes | — | Fuel grouping; drives biomass zero-rating (§7.3) |
| `proportion_emissions_CO2` | real | fraction | yes | — | ∈ [0, 1]. 1 ⇒ all CO₂; 0 ⇒ all non-CO₂ |
| `process_emission` | boolean | — | yes | — | **Data-driven.** True ⇒ quantity *is* the emission in kt CO₂e |
| `is_indirect` | boolean | — | yes | — | **Must be configuration, not code** (§7.4) |

**Rule (D5).** A commodity with `process_emission = true` may only be produced by
technologies whose process output has `denominator_kind = mass`. Process emissions are
kt per tonne; denominating them per PJ severs them from their physical basis.

### 3.5 `technology` — extended

One row per *(process × equipment type × fuel)* combination.

**Naming.** Field names deliberately match COMIT's existing columns (`technology_code`, `technology_name`, `capex`, `fixed_opex`, `lifetime`, `availability_factor`, `capacity_to_activity_factor`, `emissions_released`, `retrofit_to`) so that tier-1 reuse (D6) is a direct load from [`../notes/data/comit_sector_processes.csv`](../notes/data/comit_sector_processes.csv) and [`../notes/data/emissions_source_classification.csv`](../notes/data/emissions_source_classification.csv) with no column translation. `process_id` corresponds to COMIT's `output_commodity` / `process_commodity`.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `technology_code` | string | — | yes | PK | — |
| `technology_name` | string | — | yes | — | — |
| `process_id` | string | — | yes | → `commodity` | The process this serves |
| `equipment_type` | string | — | yes | — | e.g. `jaw_crusher`. May be `generic` |
| `fuel_category` | string | — | yes | — | The switching axis |
| `capex` | real | £m per capacity unit | yes | — | ≥ 0 |
| `fixed_opex` | real | £m/yr per capacity unit | yes | — | ≥ 0 |
| `lifetime` | integer | years | yes | — | > 0 |
| `availability_factor` | real | fraction | yes | — | ∈ (0, 1] |
| `capacity_to_activity_factor` | real | — | yes | — | > 0. Capacity units → output units |
| `emissions_released` | real | fraction | yes | — | ∈ [0, 1]. Fraction **not** captured |
| `start_year` | integer | year | no | — | Earliest build year |
| `retrofit_to` | string | — | no | → `technology` | Costs differenced against the base (§5.5) |
| `load_shape_override` | string | — | no | → `process_load_shape` | **Exception only.** Set where this technology's demand shape differs materially from its process's default (§3.13) |
| `provenance` | enum{comit_reuse, bref, proxy} | — | yes | — | **D6** |
| `confidence` | enum{high, medium, low} | — | yes | — | **D6.** Results filterable by this |

**Rule (D6).** Every technology declares provenance. Tier `proxy` entries must be
reportable and filterable; a result set dominated by `proxy`/`low` must be flagged as
such in outputs.

### 3.6 `technology_input_output`

Coefficients per technology per commodity, per unit of the technology's output.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `technology_code` | string | — | yes | PK part | → `technology` |
| `commodity_id` | string | — | yes | PK part | → `commodity` |
| `coefficient` | real | per output unit | yes | — | **Sign convention below** |
| `produces_emissions` | boolean | — | yes | — | Whether consumption of this commodity emits |
| `is_primary_output` | boolean | — | yes | — | Exactly one true per technology |

**Sign convention (must match COMIT).** Consumed commodities are **negative**; produced
commodities are **positive**. Process-emission commodities are produced, hence positive.
The emissions formulae in §7 depend on this.

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

| Field | Type | Unit | Req | Validation |
|---|---|---|---|---|
| `scenario_id` | string | — | yes | — |
| `start_year` | integer | year | yes | — |
| `end_year` | integer | year | yes | > `start_year` |
| `timestep` | integer | years | yes | > 0 |
| `discount_rate` | real | fraction | yes | ∈ [0, 1) |
| `interest_rate` | real | fraction | yes | ∈ [0, 1) |
| `base_price_year` | integer | year | yes | Costs rebased to this |
| `carbon_price_traded` | real per period | £/t | yes | — |
| `carbon_price_untraded` | real per period | £/t | yes | — |
| `fuel_price` | real per commodity per period | £m/PJ | yes | — |
| `fuel_emission_factor` | real per commodity per period | kt/PJ | yes | — |

### 3.9 `site_pathway` — output

One row per premise × process × technology × period. See §8 for the full output schema.

### 3.10 `premise_process_detail` — known site processes and capacity

**Optional per-premise intelligence.** Where the actual processes at a site are known —
from a permit, an audit, a site visit, or an operator disclosure — they are stated here
and override both the default set and any named variant. Zero rows for a premise is the
normal case and means "use the register".

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `process_id` | string | — | yes | PK part | → `commodity.commodity_id` |
| `known_capacity` | real | capacity units | no | — | > 0 if present. Units follow the process's denominator (D5): PJ/yr-equivalent for energy, Mt/yr for mass |
| `technology_code` | string | — | no | → `technology` | The specific installed technology, where known |
| `commissioned_year` | integer | year | no | — | Drives remaining life against `technology.lifetime` |
| `provenance` | string | — | yes | — | Citation: permit number, audit reference, disclosure |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried through to output |

**Rule (completeness).** The rows for a premise are treated as its **complete** process
list. A partial list would silently delete processes the site runs and misstate its
energy balance, so a premise with any rows must have rows for every process it runs. If
only fragmentary knowledge exists, use a named `process_set_id` instead.

**Rule (precedence).** Where `technology_code` is given, that technology is the premise's
existing plant for that process and A4 does not choose between candidates. Where
`known_capacity` is given, it is used directly and A4 back-solves *utilisation* instead
of capacity (§A4).

### 3.11 `premise_measured_emissions` — reported emissions, where they exist

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

**Optional per-premise intelligence.** Two distinct things live here, and they answer
different questions. The **operating schedule** says when the site runs, which validates
the utilisation A4 derives. The **load statistics** say how peaky it is, which is what a
connection capacity is actually about (§5.6).

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK | → `premise_record` |
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

**The shape belongs to the process, not to the technology.** A kiln runs continuously
whether it is fired by gas or by hydrogen; a batch dryer is batchy whether it is gas or
electric. What a unit operation *does* determines when it draws power, so the shape is
declared once per process and inherited by every technology serving it. Technologies
override it only by exception (`technology.load_shape_override`, §3.5).

This is the decomposition that makes the peak question tractable. Declaring shapes per
technology would multiply the data build by the fuel variants — 82 of 94 COMIT processes
differ only by fuel — for information that does not vary along that axis.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `shape_id` | string | — | yes | PK | — |
| `process_id` | string | — | yes | → `commodity` | The process this describes |
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
premise per vector, and per process only where sub-metering makes that real.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
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

## 4. Algorithms

*Section last updated: 2026-08-25*

Each is stated with inputs, outputs, preconditions, postconditions and failure modes.

### A1 — Ingest and validate premise records

```
INPUT:  raw_premise_records
OUTPUT: validated_premises, rejection_log
PRE:    activity_process_register loaded; cluster list loaded (9 GB clusters)

1. FOR EACH record r IN raw_premise_records:
2.     IF r.nation NOT IN {England, Wales, Scotland}:
3.         REJECT r REASON "out_of_scope_nation"; CONTINUE
4.     IF r.carb3_activity IS A KNOWN CaRB3 activity OUTSIDE the Factory class:
5.         REJECT r REASON "out_of_scope_activity"; CONTINUE
5a.    IF r.carb3_activity NOT IN activity_process_register:
5b.        REJECT r REASON "unknown_activity"; CONTINUE
6.     energy_rows := premise_energy WHERE premise_id = r.premise_id
7.     IF SUM of energy_rows.quantity <= 0:
8.         REJECT r REASON "no_energy"; CONTINUE
9.     IF ANY energy_rows.quantity < 0:
10.        REJECT r REASON "negative_energy"; CONTINUE
10a.   IF ANY energy_rows.vector INCONSISTENT WITH commodity_category:
10b.       REJECT r REASON "vector_commodity_mismatch"; CONTINUE
10c.   RECORD carrier_coverage(r) := which of the five main vectors have a row
              (positive or an explicit not_consumed zero)  -- §3.1.1, reported in §8.6
11.    r.cluster_id := nearest cluster to (r.latitude, r.longitude) among the 9
12.    r.cluster_distance := distance to that cluster
13.    IF activity requires mass denominator AND premise_throughput HAS NO ROW for r:
14.        REJECT r REASON "missing_throughput"; CONTINUE
15.    ACCEPT r INTO validated_premises

POST:   every validated premise has a cluster assignment and positive energy
FAILS IF: rejection rate exceeds a configured threshold (signals a bad input batch)
```

**Note on step 11.** This replaces COMIT's `H2_point` assignment. Because Londonderry is
out of scope (D8), any premise that would have been assigned there is assigned to its
nearest in-scope cluster instead.

### A2 — Expand premise to its process set

**Three tiers of evidence**, most specific first. The tier used is recorded on every
output row so a reader can tell a known site from an assumed one.

```
INPUT:  validated_premise p, activity_process_register, premise_process_detail
OUTPUT: process_set(p), process_evidence_tier(p)
PRE:    p.carb3_activity is known

1. detail := rows of premise_process_detail WHERE premise_id = p.premise_id
2. IF detail IS NON-EMPTY:                          -- TIER 1: known site
3.     process_set := { d.process_id FOR d IN detail }
4.     process_evidence_tier := "site_known"
5.     -- treated as complete, per the §3.10 completeness rule
6. ELSE IF p.process_set_id IS PRESENT:             -- TIER 2: named variant
7.     ASSERT p.process_set_id belongs to p.carb3_activity
            ELSE REJECT "invalid_process_set"
8.     process_set := rows of activity_process_register
                      WHERE carb3_activity = p.carb3_activity
                        AND process_set_id = p.process_set_id
9.     process_evidence_tier := "named_set"
10. ELSE:                                           -- TIER 3: activity default
11.     process_set := rows of activity_process_register
                       WHERE carb3_activity = p.carb3_activity
                         AND is_default = true
12.     process_evidence_tier := "activity_default"
13. REMOVE processes marked is_optional that the premise is known not to run
    (absent evidence, retain them — omission understates the site)
14. ASSERT process_set is non-empty

POST:   |process_set| >= 1; every process has profile rows resolvable per §3.3
FAILS IF: the activity has no default set, or a named set is empty
```

**Why tiering rather than blending.** A site either runs a process or it does not.
Averaging a known process list against an activity default would produce a site that
exists nowhere, so the tiers are strictly exclusive: better evidence replaces weaker
evidence outright.

### A3 — Allocate premise energy across processes

```
INPUT:  premise p, process_set(p), activity_process_energy_profile
OUTPUT: process_energy[process, vector]  (PJ/yr)
PRE:    profile sums to 1 per (activity, vector)   -- asserted at load, §3.3
        R1 technology consistency asserted at load  -- §3.3.3

1. FOR EACH row e IN premise_energy WHERE premise_id = p.premise_id:
2.     v := e.vector;  e_v := e.quantity
3.     IF e_v = 0: CONTINUE          -- includes every not_consumed row
4.     share' := RENORMALISE(p, v)      -- §3.3.3 R2; identity if no optional
5.     FOR EACH process q IN process_set(p) WHERE share'[q, v] EXISTS:
6.         process_energy[q, v] := e_v * share'[q, v]
7. ASSERT SUM over (q, v) of process_energy
          = SUM over premise_energy rows of quantity          (within 1e-6)

POST:   allocated energy equals metered energy exactly
FAILS IF: the assertion in step 7 fails -- indicates a malformed profile
```

**This is the design's weakest step** (vision §10). The profile is a benchmark
assumption, built and evidenced per §3.3.1–§3.3.5. Results must carry the profile's
`confidence` through to output, and its error is systematic across every premise of an
activity rather than random (§3.3.5).

### A4 — Back-solve implied existing capacity

Inverts the relationship COMIT uses to compute a technology's output from its capacity
(described in [notes/04 §Step 3](../notes/04_site_energy_estimation.md)):

```
annual_output = capacity × capacity_to_activity_factor × availability_factor
fuel_use      = annual_output × |io_coefficient(technology, fuel_commodity)|
```

Therefore:

```
INPUT:  process_energy[q, v], technology set, technology_input_output
OUTPUT: existing_capacity[technology]
PRE:    every process has at least one technology whose fuel_category matches an
        observed vector

1. FOR EACH process q:
2.     FOR EACH vector v WHERE process_energy[q, v] > 0:
3.         IF premise_process_detail[q].technology_code IS PRESENT:
4.             candidates := { that technology }        -- known plant, no choice
5.         ELSE:
6.             candidates := technologies serving q WITH fuel_category matching v
7.         IF candidates IS EMPTY:
8.             FAIL "no technology serves process q on vector v"
9.         allocate process_energy[q, v] across candidates in proportion to a
             configured prior (default: equal split; overridable per activity)
10.        FOR EACH candidate k WITH allocated energy e_k:
11.            io := |coefficient(k, fuel commodity of v)|
12.            ASSERT io > 0
13.            annual_output := e_k / io
14.            IF premise_process_detail[q].known_capacity IS PRESENT:
15.                existing_capacity[k] := known_capacity          -- measured wins
16.                utilisation[k] := annual_output
                                     / (known_capacity
                                        × capacity_to_activity_factor(k))
17.                IF utilisation[k] > availability_factor(k):
18.                    REPORT "capacity_energy_inconsistent" (premise, q, k)
19.            ELSE:
20.                existing_capacity[k] := annual_output
                                           / (capacity_to_activity_factor(k)
                                              × availability_factor(k))
21.                utilisation[k] := availability_factor(k)

POST:   recomputing fuel use from existing_capacity and utilisation reproduces
        process_energy within 1e-6  -- this is acceptance criterion V2, §10
FAILS IF: any io coefficient is zero, or a process/vector pair has no technology
```

**On known capacity (step 14).** Metered energy and stated capacity are two different
measurements of the same site and will not generally agree. The resolution is not to
pick one: capacity fixes `existing_capacity`, and energy then determines **utilisation**,
which is the quantity nobody measured. Energy therefore still reconciles exactly, so V2
and V3 hold unchanged, and the disagreement surfaces as a utilisation figure an engineer
can sanity-check rather than as a silent adjustment.

**Cross-check against the operating schedule.** Where `premise_operating_profile` gives
`operating_hours_per_year`, the utilisation derived at step 16 has an independent check:
a site running 8,760 h/yr should not back-solve to a utilisation of 0.2, and one running
a single shift should not approach 1.0. Report the disagreement as
`utilisation_schedule_inconsistent`. This is the main modelling value of the schedule —
it is the only independent evidence available about a quantity that is otherwise inferred
from two inputs that may both be wrong.

**Step 17 is a report, not a failure.** A utilisation above the technology's availability
factor means the site consumed more energy than its stated capacity allows — usually a
units error, a capacity stated as nameplate versus operating, or an out-of-date figure.
It is worth surfacing loudly, but it is the input's problem, not the model's, and it must
not stop a national run.

### A5 — Apply the infrastructure scenario

```
INPUT:  premise p, infrastructure_scenario, cluster assignment
OUTPUT: availability[carrier, period], tariff[carrier, period], caps

1. FOR EACH carrier c IN {hydrogen, co2_transport, grid_headroom}:
2.     FOR EACH period t:
3.         row := infrastructure_scenario[scenario, c, p.cluster_id, t]
4.         IF p.cluster_distance > configured_radius(c):
5.             availability[c, t] := false
6.         ELSE:
7.             availability[c, t] := row.available
8.         tariff[c, t] := row.unit_tariff
9.         caps[c, t]   := row.capacity_limit   (unbounded if absent)

POST:   every carrier has a defined availability and tariff for every period
```

### A6 — Build the per-premise optimisation problem

```
INPUT:  process_set, process demands, existing_capacity, availability, tariffs,
        scenario_parameters
OUTPUT: an optimisation problem instance (§5)

1. Build the period set T from start_year, end_year, timestep
2. Build the technology set K = union over processes of serving technologies
3. Filter K: remove technologies whose fuel is unavailable in ALL periods (A5)
4. Declare variables n[k,t], a[k,t], u[k,t] for all k in K, t in T   (§5.2)
5. Build the objective as the sum of the cost terms in §5.4
6. Add constraints C1..C9 as specified in §5.5 and §6.1
7. RETURN the problem instance

POST:   the problem has a feasible solution if demand can be met by at least one
        available technology per process in every period
```

### A7 — Solve and extract

```
INPUT:  problem instance
OUTPUT: solution OR infeasibility diagnosis

1. Solve
2. IF status = OPTIMAL: extract n, a, u; RETURN solution
3. IF status = INFEASIBLE:
4.     Diagnose by relaxing constraint groups in this order, reporting the first
       relaxation that restores feasibility:
       (a) technology stability (C6)
       (b) known changes (C7)
       (c) infrastructure availability (C9)
       (d) demand satisfaction (C1)
5.     RETURN diagnosis, do not silently substitute a relaxed solution
6. IF status = UNBOUNDED: FAIL -- indicates a cost-sign error, not a data problem

POST:   an infeasible premise is reported with the constraint group responsible
```

**Rule.** Infeasible premises are reported, never dropped. A run's summary must state
how many premises failed and why.

### A8 — Assemble output tables

```
INPUT:  solution, premise, technology set
OUTPUT: site_pathway rows (§8)

1. FOR EACH technology k, period t WITH u[k,t] > tolerance:
2.     Emit an activity row: process, technology, u[k,t], unit
3.     Compute energy by commodity: u[k,t] × |io(k, c)| for each consumed c
4.     Compute emissions by source using §7
5.     Compute costs by type using §5.4, un-discounted to per-period values
       and rebased to base_price_year
6. Attach provenance: technology confidence (D6), profile confidence (§3.3)

POST:   every emitted row carries a confidence marker
```

### A9 — Aggregate to GB and compare

```
INPUT:  all site_pathway results
OUTPUT: GB aggregates, comparison report

1. Aggregate energy by vector, emissions, and cost by COMIT sector
   (mapping activities via ../notes/data/carb3_comit_crosswalk.csv)
2. Compare against ECUK/GHGI sector totals on a GB basis
3. Report divergence -- DO NOT rescale results to match
4. Report the aggregate national emissions trajectory against any policy
   trajectory of interest, as a comparison only (not a constraint)
5. Report the share of results resting on proxy-tier costs and low-confidence
   energy profiles

POST:   divergence is surfaced, never silently corrected
```

**Optional extension (not default).** A carbon-price outer loop could iterate A5–A9,
adjusting the carbon price until aggregate emissions meet a target. This reintroduces
coupling that D2 and D7 deliberately remove, and is specified here only so that a future
implementer knows the hook exists: it requires no change to the per-premise problem,
only a scenario-parameter sweep and a convergence test.

---

## 5. The optimisation model

*Section last updated: 2026-08-25*

This section is the authoritative definition. Everything else serves it.

### 5.1 Sets and indices

| Symbol | Meaning |
|---|---|
| $T$ | Model periods, $t \in \{t_0, t_0 + \Delta, \ldots, t_N\}$ |
| $Q$ | Processes at this premise (from A2) |
| $K$ | Technologies available, $K = \bigcup_{q \in Q} K_q$ |
| $K_q$ | Technologies serving process $q$ |
| $C$ | Commodities |
| $C^{\text{fuel}}$ | Fuel commodities, $C^{\text{fuel}} \subset C$ |
| $C^{\text{proc}}$ | Process-emission commodities, $C^{\text{proc}} \subset C$ |

### 5.2 Decision variables

All continuous and non-negative.

| Variable | Meaning | Unit |
|---|---|---|
| $n_{k,t}$ | New capacity of technology $k$ built in period $t$ | capacity units of $k$ |
| $a_{k,t}$ | Capacity of $k$ available (installed) in $t$ | capacity units of $k$ |
| $u_{k,t}$ | Activity of $k$ in $t$ | output units of $k$'s process |

**Note.** COMIT introduces binary variables when a minimum hydrogen plant size is set,
making the problem a MILP. Under this design, hydrogen supply is exogenous (D7), so the
per-premise problem is a **pure LP**. This is a significant tractability gain and should
be preserved — any proposal to add binaries must be weighed against §9.

### 5.3 Parameters

| Symbol | From | Meaning |
|---|---|---|
| $D_{q,t}$ | A3 + demand projection | Demand for process $q$'s output in $t$ |
| $\iota_{k,c}$ | `technology_input_output.coefficient` | Signed coefficient of $k$ for $c$ |
| $\kappa_k$ | `technology.capex` | Capex per capacity unit |
| $\phi_k$ | `technology.fixed_opex` | Fixed opex per capacity unit per year |
| $L_k$ | `technology.lifetime` | Lifetime, years |
| $\alpha_k$ | `technology.availability_factor` | Availability fraction |
| $\gamma_k$ | `technology.capacity_to_activity_factor` | Capacity → output conversion |
| $\rho_k$ | `technology.emissions_released` | Fraction not captured |
| $E^0_k$ | A4 | Implied existing capacity |
| $p_{c,t}$ | `scenario_parameters.fuel_price` | Fuel price |
| $f_{c,t}$ | `scenario_parameters.fuel_emission_factor` | Emission factor, kt/PJ |
| $\pi_t$ | `scenario_parameters.carbon_price_*` | Carbon price (traded or untraded) |
| $\tau_{c,t}$ | `infrastructure_scenario.unit_tariff` | Infrastructure tariff (D7) |
| $r$ | `scenario_parameters.discount_rate` | Discount rate |
| $i$ | `scenario_parameters.interest_rate` | Interest rate |

### 5.4 Objective

Minimise total present-value cost over the horizon:

$$\min \; Z = \sum_{t \in T} \delta_t \Big( Z^{\text{capex}}_t + Z^{\text{opex}}_t + Z^{\text{fuel}}_t + Z^{\text{carbon}}_t + Z^{\text{infra}}_t \Big)$$

where $\delta_t$ is the present-value factor for period $t$, aggregated over the
timestep — matching the treatment described in
[notes/09](../notes/09_objective_function.md).

**Capex — annuitised.** Capital is financed and repaid in level instalments over the
technology lifetime, truncated at the horizon:

$$Z^{\text{capex}}_t = \sum_{k \in K} \sum_{s \le t} n_{k,s} \, \kappa_k \, \mathrm{PMT}(1, i, L_k) \cdot \mathbb{1}[\,s \le t \le s + L_k - 1\,]$$

where $\mathrm{PMT}(1, i, L)$ is the level annuity payment on unit principal at rate $i$
over $L$ periods.

**Fixed opex.**

$$Z^{\text{opex}}_t = \sum_{k \in K} a_{k,t} \, \phi_k$$

**Fuel.**

$$Z^{\text{fuel}}_t = \sum_{k \in K} \sum_{c \in C^{\text{fuel}}} u_{k,t} \, |\iota_{k,c}| \, p_{c,t}$$

**Carbon.**

$$Z^{\text{carbon}}_t = \pi_t \cdot \mathrm{Em}_t$$

with $\mathrm{Em}_t$ the period's chargeable emissions from §7.

**Infrastructure (D7).** COMIT carries four separate infrastructure PV terms
(`PV_CO2_national_transport`, `PV_CO2_pipe_cluster_to_site`, `PV_H2_pipe_national`,
`PV_H2_pipe_cluster_to_site`). Because infrastructure is exogenous here, they **collapse
into per-unit tariffs** on the carriers consumed:

$$Z^{\text{infra}}_t = \sum_{k \in K} \Big( u_{k,t}\,|\iota_{k,\text{H}_2}|\,\tau_{\text{H}_2,t} \;+\; \mathrm{Em}^{\text{cap}}_{k,t}\,\tau_{\text{CO}_2,t} \Big)$$

where $\mathrm{Em}^{\text{cap}}_{k,t}$ is the CO₂ captured by technology $k$ in period
$t$ — the process and fuel CO₂ expressions of §7.1 with $\rho_k$ replaced by
$(1-\rho_k)$, since $\rho_k$ is the fraction **not** captured.

This is the single largest structural simplification versus COMIT, and the direct
consequence of D7.

### 5.5 Constraints

**C1 — Demand satisfaction.** Each process's demand is met in each period:

$$\sum_{k \in K_q} u_{k,t} = D_{q,t} \qquad \forall q \in Q,\; t \in T$$

**C2 — Activity limited by available capacity.**

$$u_{k,t} \le a_{k,t} \, \gamma_k \, \alpha_k \qquad \forall k,\, t$$

**C3 — Capacity transfer between periods.**

$$a_{k,t} = a_{k,t-1} + n_{k,t} - \text{(retirements reaching end of life)} \qquad \forall k,\, t > t_0$$

**C4 — Existing capacity in the first period.**

$$a_{k,t_0} = E^0_k \qquad \forall k$$

**C5 — No building in the start year.**

$$n_{k,t_0} = 0 \qquad \forall k$$

**C6 — Technology stability.** Activity may not swing more than a configured fraction
$\sigma$ between consecutive periods:

$$|u_{k,t} - u_{k,t-1}| \le \sigma \, u_{k,t-1} \qquad \forall k,\, t > t_0$$

**C7 — Known changes.** Where a premise has an announced commitment, the corresponding
$u_{k,t}$ or $a_{k,t}$ is fixed or bounded.

**C8 — Intermediate commodity balance.** For chain processes (clinker → cement, pig iron
→ liquid steel), production of an intermediate must cover its consumption:

$$\sum_{k} u_{k,t}\,\iota_{k,c} \ge 0 \qquad \forall c \in C^{\text{intermediate}},\, t$$

**C9 — Infrastructure availability (D7).** A technology whose fuel is unavailable at the
premise in a period cannot run:

$$u_{k,t} = 0 \quad \text{if} \quad \text{availability}[\text{carrier}(k), t] = \text{false}$$

and where a cap is specified:

$$\sum_{k} u_{k,t}\,|\iota_{k,c}| \le \text{caps}[c, t] \qquad \forall c \in \{\text{H}_2, \text{CO}_2\}$$

**Retrofit differencing.** Where `technology.retrofit_to` is set, the technology's costs
are charged **net of** the base technology it replaces, matching COMIT's treatment
(notes [09](../notes/09_objective_function.md), [14](../notes/14_emissions_source_split.md)).
This is why negative cost entries are legitimate and must not be clamped to zero.

---

### 5.6 Planned extensions — network capacity, reinforcement, and export

**Not implemented. Specified so the inputs collected now are the right ones.**

`premise_record` carries `import_capacity`, `export_capacity`, `connection_voltage`,
`onsite_generation_capacity` and `onsite_generation_type` (§3.1). Nothing in the current
model reads them: they are collected because they are far easier to obtain while the
stock model is being built than to retrofit later, and because two extensions depend
entirely on them.

**Extension 1 — electrification limited by connection capacity.** Today the optimiser may
electrify a site without limit. In reality a site's import capacity binds, and exceeding
it requires a reinforcement that costs money and takes time. The constraint has the form

$$P^{\text{peak}}_{t} \;\le\; \overline{P}^{\text{import}} + r_{t}$$

where $r_t$ is reinforcement capacity purchased, entering the objective as a new term
$Z^{\text{network}}_t = \sum_t \gamma(\overline{P}^{\text{import}}, r_t)$ with
$\gamma$ a cost function of voltage level and increment.

**This needs an input the model does not currently have.** Everything here is annual
energy in PJ/yr, while a connection capacity is instantaneous power in MW. Bridging them
needs a **load factor**, and it varies enormously by activity: a continuous kiln runs
near flat, a single-shift workshop does not. `premise_operating_profile` (§3.12) supplies
it, in three tiers of evidence — the D10 pattern again.

**Tier 1 — measured load statistics.** Where `peak_electricity` or `peak_gas` is
available from half-hourly or daily metering, the peak is known and no inference is
needed. This is the only tier that gives a *true* peak.

**Tier 2 — operating schedule.** Where only the schedule is known, mean demand during
operating hours follows directly:

$$\overline{P} = \frac{E\,[\text{PJ/yr}] \times 277{,}778}{H\,[\text{h/yr}]}\;[\text{MW}]$$

**A schedule alone does not give a peak — it gives a mean, and the difference matters.**
Treating $\overline{P}$ as the peak assumes demand is flat whenever the site is open,
which no real site is: start-up surges, batch cycles and non-coincident equipment all
push the true maximum above the mean. So a schedule-derived peak is a **lower bound**,
and using it unadjusted would systematically *understate* reinforcement need — the error
runs in the dangerous direction, concluding that no reinforcement is required when it is.
Hence `within_shift_peak_factor`:

$$P^{\text{peak}} = \overline{P} \times \lambda, \qquad \lambda \ge 1$$

$\lambda$ is close to 1 for continuous processes and substantially above it for batch
and single-shift operation. Where a site supplies both a schedule and a measured peak,
$\lambda$ is observed rather than assumed — which is the cheap way to build a credible
per-activity default for every site that has only a schedule.

**Tier 3 — per-activity default load factor**, maintained alongside the energy profile
(§3.3) with the same evidence tiers and the same systematic-error caveat: it is one
assumption applied to every premise of an activity, so its error does not average out.

**Gas profiles matter more than they first appear.** For a connection-capacity question
the instinct is to want electricity data, but the quantity being sized is the peak *after*
electrification — and that is set by the shape of the load being converted, not by the
site's current electrical load. A site's gas profile is therefore the better predictor of
its post-electrification peak. Daily-metered gas is coarser than half-hourly electricity
but is exactly the right signal.

**Deriving the peak of a configuration that does not exist yet.** The constraint binds on
the peak the site has *after* the optimiser has changed its technology mix, not on its
historical peak. `premise_operating_profile` fixes the baseline year truthfully but
cannot answer that on its own — so the shape has to be attached to something the model
still knows about after the mix changes. That something is the **process** (§3.13), not
the technology: what a unit operation does determines when it draws power, and a kiln
runs continuously whether fired by gas or hydrogen.

Peak is then rebuilt from the optimiser's own output:

```
INPUT:  process_energy_by_technology[q, k, t] from the solved pathway,
        process_load_shape, premise_operating_profile, premise_weekly_profile
OUTPUT: P_peak[t]  (MW)

1. FOR EACH period t:
2.     FOR EACH process q IN process_set(p):
3.         E_q  := electrical energy at q in period t, summed over technologies
4.         shape := load_shape_override(k) IF SET ELSE process_load_shape(q)
5.         H_q  := 8,760 IF shape.runs_when_idle ELSE operating_hours_per_year
6.         mean_q := E_q [PJ/yr] × 277,778 / (H_q × shape.duty_factor)   -- MW
7.         peak_q := mean_q × shape.peak_to_mean
8.     P_peak[t] := DIVERSIFY( { peak_q } )                             -- step 9
9.     -- processes do not peak simultaneously. Either sum the weekly
10.    -- profiles of §3.14 interval by interval and take the maximum, or
11.    -- apply a per-activity diversity factor to the sum of peaks.
12.    CALIBRATE: in the baseline period, P_peak must reproduce
13.               premise_operating_profile.peak_electricity within tolerance;
14.               carry the residual as a per-premise correction into later periods
```

**Step 8 is the part that must not be skipped.** Summing per-process peaks assumes every
process peaks at the same instant, which overstates the site maximum — often badly for
`intermittent` and `batch_cyclic` processes. Where §3.14 weekly profiles exist, the
diversity is *observed*: add the interval-by-interval shapes and read off the maximum.
Where they do not, a per-activity diversity factor is the fallback, and it is another
systematic assumption of the §3.3 kind.

**Step 12 is what makes the trajectory credible.** The baseline year has a measured peak.
Any method that cannot reproduce it should not be trusted about 2040, so the baseline is
a calibration point, not merely a validation one.

**Why a half-hourly week is the right size.** 336 points per premise per vector captures
the daily cycle and the weekday/weekend split — most of what shape means here — at ~2% of
a full year. Three seasonal weeks (1,008 points) cover the seasonality cases. The full
8,760-hour series buys little beyond this for an annual model and costs ~17× more per
premise at stock scale. What the week cannot supply is the annual maximum, which §3.14
carries separately as `annual_peak`.

**What this changes about the D6 data build.** Shapes attach to ~30–76 processes rather
than to 94+ technologies, and they do not multiply by fuel variant — 82 of 94 COMIT
processes differ only by fuel, and none of that affects when the process runs. The
`technology.load_shape_override` field exists for the genuine exceptions, where the
equipment's duty differs from its process's default: arc furnaces, electrolysis operated
flexibly, heat pumps with thermal storage. Expect these to be a handful, not the norm.

**Extension 2 — onsite generation with export.** With `export_capacity` known, onsite
generation becomes a technology whose output may either offset import or be exported,
adding a revenue term $-\sum_t x_t \, p^{\text{export}}_t$ bounded by
$x_t \le \overline{P}^{\text{export}}$. This changes the sign convention story: the
objective acquires a genuinely negative term, so any implementation must not assume cost
components are non-negative — a trap V6 already records for emissions.

**Where this surfaces.** The `Network` table (§8.5) already defines how these quantities
are reported, and §8.5.1 recommends emitting them with `is_enforced = false` **before**
the constraint exists — deriving the peak from the pathway the optimiser chose and
reporting the headroom against the connection. That makes the model's blind spot visible
at the cost of a reporting step rather than a formulation change.

**Sequencing.** Both extensions are per-premise and therefore compatible with D2 — a
connection capacity is a property of one site, not shared between sites. Neither should
be attempted before Phase 2, and both should be specified against real load-factor
evidence rather than assumed.

---

## 6. Constraint disposition

*Section last updated: 2026-08-25*

COMIT has 17 constraint families. Under D2 they divide three ways.

**The `C` labels in the tables below are the constraints of §5.5**, not the pipeline
stages of §2.1 — the two were both numbered `C` until the stages were renamed `S`.

### 6.1 Survive per-premise, unchanged in meaning

| COMIT family | Becomes | Note |
|---|---|---|
| `production` | C1 | Demand now exogenous, not apportioned |
| `availability` | C2 | Unchanged |
| `capacities` | C2, C3 | Unchanged |
| `existing_capacity` | C4 | Sourced from A4, not from sector share |
| `capacity_transfer` | C3 | Unchanged |
| `known_changes` | C7 | Unchanged |
| `tech_stability` | C6 | Unchanged |
| `no_building_in_start_year` | C5 | Unchanged |
| `intermediate_commodities` | C8 | Unchanged |

### 6.2 Become exogenous scenario inputs (D7)

| COMIT family | Cluster references in current code | Replacement |
|---|---|---|
| `hydrogen` | 51 | `infrastructure_scenario` rows for `hydrogen`; C9 + tariff |
| `CO2` | 34 | `infrastructure_scenario` rows for `co2_transport`; C9 + tariff |
| `headroom` | 10 | `infrastructure_scenario` rows for `grid_headroom`; C9 |

These families exist in COMIT precisely because they couple premises through shared
capacity. They cannot survive D2 in any form and are replaced by assumptions.

### 6.3 Become reported comparisons, not constraints

| COMIT family | Replacement |
|---|---|
| `emissions` (national cap) | A9 step 4 — reported trajectory |
| `fuel` (national availability) | A9 — reported breach diagnostic |
| `fuel_share` (national shares) | A9 — reported breach diagnostic |
| `supply_chain`, `new_supply_chains` | A9 — reported |

**Implication for interpretation.** A result set may collectively breach a national fuel
availability limit or emissions budget. The model will not prevent this; A9 must surface
it prominently.

---

## 7. Emissions accounting

*Section last updated: 2026-08-24*

These rules must be reproduced exactly. COMIT's implementation is the reference.

### 7.1 The two sources

Let $\theta_c$ be `proportion_emissions_CO2`, $\mathbb{1}^{\text{proc}}_c$ the
`process_emission` flag, $\mathbb{1}^{\text{dir}}_c$ whether the commodity is direct, and
$\mathbb{1}^{\text{emit}}_c$ `produces_emissions`.

**Process CO₂** — the quantity *is* the emission; there is **no fuel factor**:

$$\mathrm{Em}^{\text{proc,CO}_2}_{k,t} = u_{k,t} \sum_{c \in C^{\text{proc}}} \iota_{k,c}\,\theta_c\,\mathbb{1}^{\text{dir}}_c\,\rho_k$$

**Fuel CO₂** — scales with fuel burnt; sign flipped because fuel coefficients are
negative:

$$\mathrm{Em}^{\text{fuel,CO}_2}_{k,t} = -\,u_{k,t} \sum_{c \in C^{\text{fuel}}} \iota_{k,c}\,\theta_c\,\mathbb{1}^{\text{dir}}_c\,\mathbb{1}^{\text{emit}}_c\,f_{c,t}\,\rho_k$$

Reference: `R/fct_emissions.R:255-290`.

### 7.2 Non-CO₂ — and the capture rule

$$\mathrm{Em}^{\text{proc,nonCO}_2}_{k,t} = u_{k,t} \sum_{c \in C^{\text{proc}}} \iota_{k,c}\,(1-\theta_c)\,\mathbb{1}^{\text{dir}}_c$$

**Three things to note, all load-bearing:**

1. There is **no $\rho_k$ term**. Non-CO₂ is entirely released.
2. **CCS never abates non-CO₂.** COMIT fixes the captured non-CO₂ terms to zero
   (`R/fct_emissions.R:327-328`). A technology claiming methane capture cannot be
   represented by data alone.
3. **No GWP conversion happens anywhere.** `INDCH4P` and `INDN2OP` coefficients must
   already be in kt CO₂e. Supplying tonnes of CH₄ will be silently treated as CO₂e.

### 7.3 Biomass zero-rating

When the `zero_emissions_from_biomass` switch is on (the default), fuels whose
`commodity_category` is `Biomass and organic waste` have their emission factor set to
zero *before* capture is applied. The captured stream still counts, which is what makes
BECCS net negative.

Reference: `R/fct_emissions.R:234`. **The category name is a hardcoded string literal in
COMIT** — renaming that category silently disables zero-rating. In this implementation it
**must be configuration** (§3.4 `commodity_category`), not a literal.

### 7.4 Direct vs indirect

Emissions from grid electricity and mains hydrogen occur off-site and are classified
`indirect`. COMIT hardcodes the list (`R/fct_emissions.R:180-183`) as
`INDDISTELC`, `INDMAINSHYG`, `INDMAINSHYGG`, `INDMAINSHYGB`.

**This must become configuration** — the `commodity.is_indirect` field (§3.4). A new
carrier added to the commodity table would otherwise be booked as direct.

**Known inconsistency to avoid inheriting.** `INDMAINSHYGR` is treated as a hydrogen fuel
elsewhere in COMIT but is absent from that hardcoded list. It is currently inert, but the
colour variants carry a sentinel emission factor of `999`, so activating it would produce
absurd direct emissions. Making the list data-driven removes the trap.

### 7.5 Emissions categories to report

Reproduce COMIT's categories (see [notes/12 §4.4](../notes/12_output_data_schema.md)),
because they overlap by design and consumers must be able to filter:

`Direct (total CO2e)` · `Direct (split by ghg type)` · `Direct_and_Indirect` ·
`Electricity` · `Hydrogen` · `Captured` · `Negative`

**Net emissions = `Direct (total CO2e)` + `Negative`.**

### 7.6 Reconciling against measured emissions

Where `premise_measured_emissions` (§3.11) exists, it is the best evidence available
about the site's baseline. It cannot, however, simply replace the computed figure.

**Why an override is not possible.** Emissions here are *endogenous* — a function of the
decision variables, recomputed every period from whatever fuel the optimiser chooses.
Substituting a measured scalar would sever that link: the model would report the same
emissions whether the site kept its coal kiln or electrified it, and the carbon cost term
$Z^{\text{carbon}}$ would stop responding to the decision it exists to price. A measured
emissions figure is a fact about **one historical year of one configuration**, not a
property of the site that survives changing the configuration.

**What measured emissions are used for instead**, in increasing order of intrusiveness:

1. **Reconciliation (default, always on).** Compute baseline-year emissions from the
   model, compare against the measured figure, and report the divergence per premise and
   in the GB aggregate (V13). Divergence is surfaced, never silently corrected — the same
   rule A9 applies to sector totals.
2. **Split correction (default on where the split is supplied).** Where measured data
   distinguishes `combustion` from `process`, and the model's split rests on a
   low-confidence energy profile, the measured split is better evidence about *which
   source* the emissions come from. Adopt the measured ratio for the baseline year and
   report that it was adopted.
3. **Intensity calibration (default OFF — opt-in per run).** A per-premise multiplier on
   the process-emission intensity of that site's mass-denominated processes, chosen so
   baseline computed emissions match the measured figure. This keeps emissions endogenous
   — the multiplier scales a coefficient, not the result — while making year zero true.

**Rule for calibration.** The multiplier must be bounded (suggested: $[0.5, 2.0]$) and
recorded on every output row for the premise. A premise needing a multiplier outside the
bound is not calibrated; it is reported as an unexplained divergence, because at that
magnitude the disagreement is evidence of a data error rather than a site-specific
intensity.

**Rule for scope.** Only `scope = direct` measured emissions enter the comparison.
Indirect emissions depend on grid factors that the measured source and this model will
not have taken from the same vintage.

---

## 8. Output schema

*Section last updated: 2026-08-25*

Reuse the structure documented in [notes/12](../notes/12_output_data_schema.md), extended
with a **process** dimension. Convention: long in dimensions, wide in periods; the period
columns are generated from `start_year`/`end_year`/`timestep` and **must not be
hardcoded**.

### 8.1 `Outputs` — activity

| Field | Type | Note |
|---|---|---|
| `premise_id` | string | |
| `carb3_activity` | string | |
| `comit_sector` | string | Via the crosswalk, for aggregation |
| `cluster_id` | string | One of 9 |
| `process_id` | string | **New dimension** |
| `technology_code` | string | |
| `equipment_type` | string | **New** |
| `fuel_category` | string | The switching axis |
| `unit` | string | From the process denominator (D5) |
| `process_set_id` | string | **New (D10).** Which process set this premise resolved to (§3.2) |
| `process_evidence_tier` | enum{site_known, named_set, activity_default} | **New (D10).** Which tier A2 used. Required by V11 — without it an aggregate cannot say which premises were surveyed and which were defaulted |
| `utilisation` | real | **New.** Derived in A4. Equals the availability factor where capacity was back-solved, and the energy-implied value where capacity was known (§A4) |
| `carrier_coverage` | enum{complete, incomplete} | **New.** Whether all five main vectors were stated for this premise, whether positive or an explicit `not_consumed` zero (§3.1.1) |
| `emissions_calibration_multiplier` | real | **New.** Present only where §7.6 intensity calibration was enabled. Required by V13 |
| `confidence` | enum | Lowest of technology and profile confidence |
| `⟨period⟩` | real | Activity in that period |

**Rule.** The five fields marked new are not decoration. Three validation tests assert
their presence — V11 on the evidence tier, V12 on utilisation, V13 on the calibration
multiplier — because each is the only way a reader can tell how much of a result rests on
evidence rather than on a default.

### 8.2 `Energy`

As above, plus `input_commodity`, with two period-column families:
`⟨period⟩_PJ` and `⟨period⟩_ktCO2e`.

**Carry forward the warning from [notes/12 gotcha 14](../notes/12_output_data_schema.md):**
the `ktCO2e` columns here are gross combustion emissions of the fuel, before biogenic
zero-rating and capture. They are **not** interchangeable with the `Emissions` table.
Document this in the output workbook itself.

### 8.3 `Emissions`

As `Outputs`, plus `emissions_category`, `co2_noncoo2`, `emission_type`, `ghg_type`.
Values in kt; negative permitted for the `Negative` category.

### 8.4 `Costs`

As `Outputs`, plus `cost_type` ∈ {`Capex`, `Capex_lump`, `Opex`, `Fuel cost`,
`Carbon cost`, `Infrastructure tariff`, `Network reinforcement`, `Export revenue`}.
Values in £m per period, un-discounted and rebased to `base_price_year`.

**`Capex` and `Capex_lump` are two views of the same money** — annuitised stream and
build-year spike. Never sum them.

**`Network reinforcement` and `Export revenue` appear only once §5.6's extensions are
implemented**, and `Export revenue` is **negative** — it is income. This is the second
place after emissions where a blanket non-negativity assertion would falsely fail on
correct output, which is why V6 states non-negativity as a prohibition on cost as well as
on emissions.

### 8.5 `Network` — power quantities in MW

**Why this is a separate table and not columns on the others.** The four tables above are
keyed premise × process × technology × period, and their values are energy, emissions or
money. A connection capacity is none of those things: it is a **premise-level fact in
MW**, and putting it on `Outputs` would repeat one value across every technology row at
that premise, inviting exactly the double-counting §8.4 warns about for capex. The
existing tables are already separated by unit family — PJ, kt, £m — so MW gets its own,
following the same rule.

Long in dimensions, wide in periods, as elsewhere.

| Field | Type | Note |
|---|---|---|
| `premise_id` | string | |
| `cluster_id` | string | One of 9 |
| `process_id` | string | **Optional.** Present on per-process peak contributions; absent on whole-premise rows |
| `network_metric` | enum | See the table below |
| `basis` | enum{measured, derived_from_profile, derived_from_schedule, activity_default} | How the value was arrived at — the §5.6 tiers. `measured` only where `premise_operating_profile` supplied it |
| `is_enforced` | boolean | Whether the value constrained the solve, or was computed and reported only. See below |
| `confidence` | enum | Lowest of the shape and profile confidence contributing to it |
| `⟨period⟩_MW` | real | The value in that period |

**The metrics.**

| `network_metric` | Meaning |
|---|---|
| `import_capacity` | The connection's agreed import capacity, as supplied (§3.1) |
| `export_capacity` | Agreed export capacity; 0 where export is not permitted |
| `peak_demand_electricity` | Modelled electrical peak in that period, from the §5.6 derivation |
| `peak_demand_baseline` | The baseline-year peak, measured where available — the calibration anchor of §5.6 |
| `headroom` | `import_capacity + reinforcement − peak_demand_electricity`. **Negative means the pathway exceeds the connection** |
| `reinforcement_required` | Additional capacity the pathway implies, i.e. `max(0, −headroom)` before any reinforcement |
| `reinforcement_purchased` | Reinforcement actually taken, once extension 1 makes this a decision variable. Equals `reinforcement_required` while the model only reports |
| `onsite_generation` | Installed generation capacity |
| `exported_power` | Peak power exported, bounded by `export_capacity` |

**Per-process rows are diagnostic.** Where `process_id` is present the row carries that
process's own peak contribution *before* diversification (§5.6 step 8), which is what
tells a reader which process drives a site's peak. They therefore **sum to more than** the
whole-premise `peak_demand_electricity` row, and must not be added to reach a site total.

**Money and energy stay in their own tables.** Reinforcement cost is a cost, so it belongs
in §8.4 as a `cost_type`, not here. Exported *energy* in PJ belongs in §8.2; only exported
*power* in MW appears here.

#### 8.5.1 Report before you constrain

`is_enforced` exists because this table is useful **before** extension 1 is built, and
that is the recommended sequencing.

With the constraint unimplemented, the model can still derive a peak from the pathway it
chose and compare it against the connection. A premise whose least-cost pathway implies
128 MW against a 25 MW connection is a finding worth surfacing immediately, even though
the optimiser was not told it could not do that. Emitting these rows with
`is_enforced = false` makes the model's blind spot visible instead of invisible.

**Rule.** While `is_enforced = false`, a negative `headroom` means the pathway is
**not deliverable as costed** — the reinforcement it implies has not been priced into the
result. Any such premise must be flagged in §8.6 and must not be reported as a completed
least-cost pathway without that caveat. When extension 1 lands, the same rows switch to
`is_enforced = true` and `headroom` becomes non-negative by construction.

### 8.6 Run metadata

Every output set carries:

| Item | Why |
|---|---|
| Scenario id, infrastructure scenario id, period definition | Identifies the run |
| Counts of premises accepted / rejected / infeasible | Basic completeness |
| Rejection counts **by reason** (§1.6.7) | A batch failing on one reason is a contract problem; failing on many is a data problem |
| Share of results resting on **proxy-tier costs** (D6) | Cost confidence |
| Share resting on **fallback-tier energy profiles** (§3.3.2) | Profile confidence |
| Distribution of **`process_evidence_tier`** across premises (D10) | How much of the run is surveyed versus defaulted |
| Count of premises with **incomplete carrier coverage** (§3.1.1) | Where a vector was never assessed, so absence is not zero |
| Count of premises reporting `capacity_energy_inconsistent`, `utilisation_schedule_inconsistent`, `profile_energy_inconsistent` | Input disagreements surfaced by V12 and V14 |
| Aggregate **measured-emissions divergence** and the count of premises calibrated (§7.6) | Required by V13 |
| Count of premises whose pathway **exceeds their connection** — negative `headroom` in any period (§8.5) | While the constraint is unenforced these pathways are not deliverable as costed |
| Total `reinforcement_required` across the run, in MW | The network investment the pathway implies but has not priced |
| Any validation test **deferred** rather than passed, with its reason (§11.5) | A deferred test must never read as a passed one |

**Rule.** Several sections promise that a condition is "reported" rather than corrected —
carrier coverage (§3.1.1), emissions divergence (§7.6), aggregate divergence (§A9),
utilisation disagreements (§A4). This table is where that promise is kept. A condition
detected and not surfaced here is a defect, not a silent success.

---

## 9. Performance and parallelisation

*Section last updated: 2026-08-21*

### 9.1 The scaling argument

COMIT today: 1,026 premises → ~638,000 capacity variables, ~30 technologies and ~620
variables per premise. Under D2 each premise is an independent problem of roughly that
per-premise size, so:

- **Work scales linearly** in premise count.
- **Problem size per premise is constant** — bounded by the technologies serving its
  activity's processes.
- **No shared state** between premise solves.

### 9.2 Scale gates

These must be met in Phase 1, **before** the technology data build is commissioned:

| Gate | Premises | Requirement |
|---|---|---|
| G1 | 10,000 | Completes; per-premise memory measured and bounded |
| G2 | 100,000 | Completes within a working day on available hardware |
| G3 | 1,000,000 | Completes, or the design is revised to archetype aggregation |

**On G3.** With scope now fixed to the Factory class (D1), the GB premise count is
expected to be well below 1,000,000 — confirm it against the stock model before Phase 1
and treat G3 as a headroom test rather than a forecast of the real run size.

**If G3 fails, D1 is not achievable** and the design must fall back to representative
archetypes. Learning that in Phase 1 costs days; learning it in Phase 4 costs the data
build.

### 9.3 Solver notes — the only language-specific section

The per-premise problem is a **pure LP** (§5.2). Any LP solver suffices.

- **R:** the existing `ROI` / `highs` path (`R/comit_solver.R:284`, `comit_highs_solver`)
  can be reused per premise.
- **Python:** `linopy` + `highspy` as set out in
  [notes/08](../notes/08_python_redesign_approach.md). A per-premise problem is a
  natural fit for that stack, and the site dimension becomes an ordinary array axis.

Two cautions carried from COMIT:

1. **Solver choice by timestep.** COMIT selects simplex for timesteps ≥ 5 years and
   interior point otherwise (`R/comit_solver.R:327`). Retain an equivalent switch.
2. **Degeneracy.** COMIT's LP is degenerate — multiple technology mixes achieve the same
   objective. Per-premise results may therefore be unstable between solver versions.
   Fix a deterministic tie-break (e.g. lexicographic by `technology_code`) so that reruns
   reproduce, and document that ties exist.

### 9.4 Orchestration

- Premises are independent: distribute by any partition.
- Persist results incrementally; a failed premise must not lose the batch.
- Record per-premise solve status and wall-clock time for diagnostics.

---

## 10. Validation and test plan

*Section last updated: 2026-08-25*

### 10.1 How to read this section

Fifteen tests. Each is specified with the same six fields, so that a test can be
implemented from this section alone:

| Field | Meaning |
|---|---|
| **Checks** | The property being asserted, in one sentence |
| **Scope** | When it runs — see §10.2 |
| **Blocking** | Whether failure stops the work, or is recorded and carried forward |
| **Procedure** | Numbered steps, language-agnostic |
| **Pass criterion** | The precise threshold, with its tolerance |
| **On failure** | What a failure indicates, and what to do about it |

**Blocking has a specific meaning here.** A *blocking* failure stops the thing it
guards — a load-time test stops the reference data being loaded, a per-premise test
rejects that premise, a release test stops the release. An *advisory* failure is
recorded, attached to the affected outputs, and reported in aggregate (§8.6); the run
continues. Advisory does not mean optional: an unreported advisory failure is a defect.

The distinction matters because this model runs at stock scale. A blocking test that
fires on one premise in a million-premise run must not fail the run — it rejects that
premise and the batch continues, subject to the batch-level gate in §1.6.7.

### 10.2 Scopes

| Scope | Runs | Guards |
|---|---|---|
| **Load** | Once, when reference data is loaded, before any premise is processed | The register, profile, technology and shape tables |
| **Premise** | Once per premise, inside the pipeline | That premise's inputs and derived values |
| **Batch** | Once per run, after all premises are solved | Aggregates and cross-premise reporting |
| **Release** | Before shipping a model version; not part of a normal run | The implementation itself |

Load-scope tests are the cheapest place to catch a problem and should never be deferred
to a per-premise check. A profile that does not sum to 1 is one assertion at load, or a
million confusing energy-balance failures at premise scope.

### 10.3 The tests

#### V1 — Decoupling parity

**Checks.** That solving each site independently reproduces what the current model
produces when its cross-site constraints are switched off — isolating the decomposition
(D2) from every other change in this design.

**Scope.** Release. **Blocking.** Yes.

**Procedure.**

```
1. Take the 1,026 NAEI point-source sites the current COMIT model runs on.
2. In current COMIT, disable every constraint listed in §6.2 (the cluster and
   national couplings). Keep everything else — technologies, prices, horizon.
3. In this model, run the same 1,026 sites with the same scenario parameters,
   supplying their existing energy as premise_energy rows so no baseline
   inference differs between the two.
4. For each site, compare: objective value, per-technology capacity by period,
   per-vector energy by period, emissions by category.
5. Where a technology mix differs but the objective matches, classify the site
   as a solver tie rather than a discrepancy (see below).
```

**Pass criterion.** Per-site objective values agree to solver tolerance. Per-site
capacities agree to solver tolerance **or** are recorded as ties with identical
objective values.

**On failure.** A genuine objective difference means the decomposition changed the
answer, which is the single most consequential way this design can be wrong. Diagnose
before proceeding: the usual causes are a constraint in §6.1 that couples premises
after all, or a scenario parameter applied at different granularity on the two sides.

**Two cautions.** First, parity with *fully coupled* COMIT is **not** a valid criterion
and must not be substituted — the coupled model answers a different question (vision
§7.4). Second, COMIT's LP is degenerate (§9.3): several technology mixes reach the same
cost, so mix differences at equal objective value are expected and are not failures.
This is why the comparison leads on the objective, not the mix.

#### V2 — Baseline reproduction

**Checks.** That the capacity A4 infers, run forwards again, reproduces the energy the
stock model supplied — i.e. that the back-solve is self-consistent.

**Scope.** Premise. **Blocking.** Yes.

**Procedure.**

```
1. Take existing_capacity[k] and utilisation[k] from A4.
2. FOR EACH technology k:
       implied_output := existing_capacity[k] × capacity_to_activity_factor(k)
                          × utilisation[k]
       implied_fuel   := implied_output × |io_coefficient(k, fuel commodity)|
3. Sum implied_fuel by vector.
4. Compare against the premise_energy quantities for the same vectors.
```

**Pass criterion.** Reproduces the supplied per-vector energy within **1%**.

**On failure.** The chain from energy to capacity has lost information. Check in this
order: a zero or wrong-signed `io_coefficient`; an `availability_factor` of zero;
a technology allocated energy on a vector its `fuel_category` does not match (which V4's
R1 check should already have caught at load); or a `known_capacity` in different units
from the technology's capacity units.

#### V3 — Energy conservation and carrier integrity

**Checks.** That A3 neither creates nor destroys energy, and that the long-format
carrier table is internally coherent.

**Scope.** Premise (conservation) and Load (uniqueness, vector agreement).
**Blocking.** Yes.

**Procedure.**

```
1. ASSERT (premise_id, commodity_id) is unique across premise_energy.
2. FOR EACH premise_energy row:
       ASSERT row.vector agrees with commodity(row.commodity_id).commodity_category
       ASSERT row.data_status = not_consumed IMPLIES row.quantity = 0
3. After A3: SUM over (process, vector) of process_energy
              = SUM over premise_energy rows of quantity
4. RECORD carrier_coverage: which of the five main vectors have a row for this
   premise, whether positive or an explicit not_consumed zero.
```

**Pass criterion.** Step 3 holds within **1e-6**. Steps 1–2 hold exactly.

**On failure.** Conservation failures point at the profile, not the allocation: either
shares that do not sum to 1 (V4), or an R2 renormalisation that divided by a zero
denominator. Note that carrier coverage is **recorded, not asserted** — an incomplete
premise is reported (§8.6), never rejected.

#### V4 — Profile integrity

**Checks.** That `activity_process_energy_profile` obeys the three rules of §3.3.3
before any premise uses it.

**Scope.** Load. **Blocking.** Yes.

**Procedure.**

```
1. FOR EACH (carb3_activity, process_set_id, vector):
       ASSERT SUM of energy_share over processes = 1
2. R1 — FOR EACH profile row with energy_share > 0:
       ASSERT at least one technology serving that process has a
              fuel_category matching that row's vector
3. R3 — FOR EACH row carrying a band:
       ASSERT share_low <= energy_share <= share_high
4. R2 — for a premise with no optional process absent, ASSERT the renormalised
       shares equal the raw shares (denom = 1, so the identity must hold)
```

**Pass criterion.** Step 1 holds within **1e-6**; steps 2–4 hold exactly.

**On failure.** All four are data defects, not code defects, and all four are cheap to
fix at load. R1 is the one worth checking first: it is the difference between a
diagnosable load-time message and an opaque "no technology serves process q on vector v"
failure in the middle of a national run.

**Note the key.** The sum is over `(activity, process_set_id, vector)` — per process
*set*, not per activity. An activity with a named variant has one such group per set.

#### V5 — Emissions invariants

**Checks.** The post-solve emissions identities that COMIT already satisfies, carried
over unchanged from [notes/14](../notes/14_emissions_source_split.md).

**Scope.** Release, and Batch on any run whose technology data has changed.
**Blocking.** Yes.

**Procedure.**

```
1. ASSERT `Direct (split by ghg type)` summed over gases
          = `Direct (total CO2e)`
2. ASSERT available_capacity = cumulative new_capacity, per technology per period
3. FOR EACH technology with Generate_emissions = false:
       ASSERT reported emissions = 0 ktCO2e
```

**Pass criterion.** All three hold within solver tolerance.

**On failure.** These are structural. A break in (1) usually means a gas was added to
the split without being added to the total; (2) means capacity accounting has diverged
from the build decisions; (3) means an emissions path bypassed the `Generate_emissions`
switch.

#### V6 — Non-negativity, correctly scoped

**Checks.** That non-negativity is asserted on the quantities that genuinely cannot go
negative, and **not** on the ones that can.

**Scope.** Premise. **Blocking.** Yes.

**Procedure.**

```
1. ASSERT activity, energy and capacity >= 0 for every technology and period.
2. DO NOT assert non-negativity on cost or emissions.
```

**Pass criterion.** Step 1 holds for all rows.

**On failure of step 1**, the solver has produced a physically impossible result and the
problem formulation should be suspected before the data.

**Why step 2 is stated as a prohibition.** Costs may be negative through retrofit
differencing (§5.5), and emissions may be negative through BECCS. [notes/14](../notes/14_emissions_source_split.md)
records blanket non-negativity as a **falsified** invariant — it was asserted, and real
model output broke it. Re-adding that assertion will produce false failures on correct
results, which is worse than no test at all. If §5.6's export revenue term is ever
implemented, the objective acquires another genuinely negative component.

#### V7 — Scale gates

**Checks.** That per-premise independence delivers the linear scaling D1 depends on, at
the premise counts a national run implies.

**Scope.** Release. **Blocking.** Yes for G1 and G2; G3 is blocking for D1 but not for
Phase 1 (§11).

**Procedure.**

```
1. G1 — run 10,000 premises. Record wall-clock, peak memory, and per-premise
        memory. Confirm per-premise memory is bounded, not growing with count.
2. G2 — run 100,000 premises. Confirm completion within a working day on the
        available hardware.
3. G3 — run 1,000,000 premises. Record the result whether or not it completes.
4. At each gate, record solve status and wall-clock per premise (§9.4) so that
   a slow tail can be distinguished from a slow average.
```

**Pass criterion.** G1 and G2 complete within the stated bounds; G3 completes, **or** its
failure is recorded and the archetype fallback is triggered.

**On failure.** G3 failing means D1 — every premise individually — is not achievable, and
the design falls back to representative archetypes (§9.2). Learning this in Phase 1 costs
days; learning it in Phase 4 costs the technology data build. Note also that the
Factory-class premise count is expected to be well below 1,000,000, so G3 is headroom
rather than a forecast.

#### V8 — GB aggregate sanity

**Checks.** That aggregated results are of a credible magnitude against independent
national statistics.

**Scope.** Batch. **Blocking.** No — advisory.

**Procedure.**

```
1. Aggregate energy by vector, emissions and cost by COMIT sector, mapping
   activities through ../notes/data/carb3_comit_crosswalk.csv.
2. Compare against ECUK/GHGI sector totals on a GB basis.
3. Report divergence per sector and in total.
4. Report the share of the result resting on proxy-tier costs, fallback-tier
   energy profiles, and premises with incomplete carrier coverage.
5. DO NOT rescale results to match.
```

**Pass criterion.** Divergence is computed and reported for every sector. There is no
numeric threshold, and that is deliberate — see below.

**On failure.** The failure mode for this test is *silence*, not divergence. A large
divergence is a finding to be explained; an unreported divergence is a defect. Two
structural reasons for expected divergence must be stated whenever the comparison is
published: this is an **industrial** total covering only the Factory class (D1), not a
whole-economy or whole-non-domestic total; and it is **GB**, while GHGI is UK (D8).

#### V9 — Infrastructure sensitivity

**Checks.** That results which depend on the exogenous infrastructure assumption (D7)
are never presented as if they did not.

**Scope.** Batch. **Blocking.** No — advisory, but blocking for publication.

**Procedure.**

```
1. Identify clustered energy-intensive premises — those whose activity carries a
   mass-denominated process, or which sit within the cluster radius of an H2 or
   CO2 carrier.
2. Run each under at least two bounding infrastructure_scenario cases: one where
   the carrier is available early, one where it is never available.
3. For each premise, report the spread in pathway, cost and emissions.
4. Flag any premise whose chosen technology differs between the two scenarios.
```

**Pass criterion.** Every premise in the identified subset has results under at least two
scenarios, and the spread is reported alongside any single-scenario figure.

**On failure.** A single-scenario result for a clustered energy-intensive premise is not
a finding — it is a conditional statement presented as an unconditional one. For cement,
steel and chemicals the pathway can swing entirely on this assumption (vision §7.1), so
publishing one scenario for these premises misrepresents the model's confidence.

#### V10 — Determinism

**Checks.** That the same inputs produce the same outputs, run to run and machine to
machine.

**Scope.** Release. **Blocking.** Yes.

**Procedure.**

```
1. Run the same premise set twice in the same environment; compare outputs
   byte for byte.
2. Run it again with a different partition across workers; compare again.
3. Run it on a second machine or solver build; compare again.
4. Where any comparison differs, check whether the objective values are equal —
   a degenerate tie — and whether the §9.3 tie-break was applied.
```

**Pass criterion.** Identical outputs in (1) and (2). In (3), identical outputs, or
differences confined to documented ties with equal objective values.

**On failure.** The likely cause is the LP degeneracy of §9.3: several mixes reach the
same cost and the solver picks arbitrarily. The remedy is the deterministic tie-break —
lexicographic by `technology_code` — not a tolerance. Partition-dependent results in (2)
are more serious: they mean state is leaking between premise solves, which contradicts
D2.

#### V11 — Process set integrity

**Checks.** That the register's process sets are well formed and that A2's tiering
resolves in the intended order.

**Scope.** Load (register structure) and Premise (tier resolution). **Blocking.** Yes.

**Procedure.**

```
1. FOR EACH carb3_activity: ASSERT exactly one set has is_default = true.
2. FOR EACH (activity, set, process): ASSERT profile rows resolve, directly or
   by the §3.3 inheritance rule.
3. FOR a premise citing a process_set_id belonging to a different activity:
   ASSERT rejection with reason invalid_process_set.
4. FOR a premise with premise_process_detail rows: ASSERT the detail overrides
   both the named set and the default, and is treated as the complete list.
5. ASSERT the tier used is recorded on every output row.
```

**Pass criterion.** All five hold exactly.

**On failure of step 5** in particular, the results are not wrong but they are
unreadable: a national aggregate that mixes surveyed premises with defaulted ones, and
cannot say which is which, presents uniform confidence it does not have.

#### V12 — Known-capacity reconciliation

**Checks.** That supplying a known capacity improves the answer without breaking the
energy balance.

**Scope.** Premise. **Blocking.** Partly — the reconciliation is blocking, the
consistency report is advisory.

**Procedure.**

```
1. FOR a premise with premise_process_detail.known_capacity:
       ASSERT V2 still passes — energy reconciles within 1e-6.
2. ASSERT utilisation was derived and is present on output.
3. IF utilisation > availability_factor:
       REPORT capacity_energy_inconsistent. DO NOT clip, scale or reject.
4. Compare the same premise run with and without known_capacity; record the
   difference in inferred capacity.
```

**Pass criterion.** Step 1 holds within **1e-6**; step 2 holds exactly; step 3 produces a
report rather than a silent adjustment.

**On failure.** A step 3 report is usually an input problem, not a model problem —
nameplate versus operating capacity, an out-of-date figure, or a units error. It must be
surfaced loudly and must not stop a national run. Step 4 is diagnostic rather than
pass/fail: a large difference tells you how much the back-solve prior was doing.

#### V13 — Measured-emissions divergence

**Checks.** That reported emissions are used to reconcile the baseline, and never to
overwrite it.

**Scope.** Premise (comparison) and Batch (aggregate reporting). **Blocking.** No —
advisory, except the calibration bound.

**Procedure.**

```
1. FOR a premise with premise_measured_emissions:
       compute baseline-year emissions from the model
       compare against measured, scope = direct only
       report divergence per premise
2. Aggregate divergence across all such premises and report it.
3. IF the measured combustion/process split is supplied AND the model's split
   rests on a low-confidence profile: adopt the measured ratio for the baseline
   year and record that it was adopted.
4. IF intensity calibration is enabled:
       ASSERT every multiplier lies within the configured bound (suggested
              [0.5, 2.0]) and is recorded on every output row for that premise
       a premise needing a multiplier outside the bound is NOT calibrated and
              is reported as an unexplained divergence
5. ASSERT emissions remain a function of the decision variables in every case.
```

**Pass criterion.** Divergence reported at premise and aggregate level; step 4's bound
holds; step 5 holds structurally.

**On failure of step 5**, the implementation has substituted a measured scalar for the
computed value. This is the failure this test exists to catch: it makes reported
emissions identical whether a site keeps its coal kiln or electrifies, and the carbon
price stops pricing the decision it exists to price (§7.6).

#### V14 — Operating profile coherence

**Checks.** That the schedule and load statistics agree with each other, with the
premise's energy, and with the utilisation derived in A4.

**Scope.** Load (internal coherence) and Premise (cross-check against A4).
**Blocking.** No — advisory.

**Procedure.**

```
1. WHERE both a peak and a load factor are supplied for a vector:
       ASSERT load_factor = (E [PJ/yr] × 277,778) / (peak [MW] × 8,760)
2. ASSERT within_shift_peak_factor >= 1 wherever present.
3. Compare A4's derived utilisation against operating_hours_per_year:
       a continuous site should not back-solve to a low utilisation, and a
       single-shift site should not approach 1.0
4. REPORT disagreement as utilisation_schedule_inconsistent.
```

**Pass criterion.** Step 1 reconciles within **5%**; step 2 holds exactly; step 3
produces a report rather than an adjustment.

**On failure.** A step 1 divergence is most often a vintage mismatch — the profile year
differs from `data_year` — and is reported as `profile_energy_inconsistent`. Step 3 is
the only independent evidence available about utilisation, which is otherwise inferred
from two inputs that may both be wrong; a disagreement says one of capacity, coefficients
or energy is wrong, without saying which.

#### V15 — Load shape coherence

**Checks.** That the shape data is well formed and that any projected peak is anchored to
a measured one.

**Scope.** Load (shape data) and Release (the §5.6 method). **Blocking.** Yes for the
data checks; blocking for publication of any projected peak.

**Procedure.**

```
1. ASSERT every process in the register resolves to a process_load_shape,
   directly or through technology.load_shape_override.
2. ASSERT shape_class = standing IF AND ONLY IF runs_when_idle = true.
3. ASSERT peak_to_mean >= 1 and duty_factor IN (0, 1].
4. FOR EACH premise_weekly_profile series: ASSERT 336 intervals per season and
   a maximum fraction_of_peak of exactly 1.
5. ASSERT annual_peak is present and >= the week's own maximum in MW terms.
6. Run the §5.6 derivation on the baseline period and compare against
   premise_operating_profile.peak_electricity.
```

**Pass criterion.** Steps 1–5 hold exactly. Step 6 reproduces the measured baseline peak
within tolerance **before** any projected peak is reported.

**On failure of step 6**, the projection is not trustworthy: a method that cannot
reproduce a peak that was actually measured should not be believed about 2040. Step 5 is
the subtle one — a representative week is typical by construction, so its maximum is
below the annual maximum, and treating the week's peak as the site peak understates it,
substantially for seasonal processes.

#### V16 — Network reporting coherence

**Checks.** That the MW quantities in the `Network` table are internally consistent, and
that an unenforced connection limit is never mistaken for a satisfied one.

**Scope.** Batch. **Blocking.** No — advisory, but blocking for publication of any
premise with negative headroom.

**Procedure.**

```
1. FOR EACH premise and period:
       ASSERT headroom = import_capacity + reinforcement_purchased
                          - peak_demand_electricity
2. ASSERT exported_power <= export_capacity.
3. ASSERT the baseline period's peak_demand_electricity reconciles with
   peak_demand_baseline within the §5.6 calibration tolerance.
4. Per-process rows: ASSERT their sum >= the whole-premise peak row, since
   they are pre-diversification contributions (§8.5).
5. IF is_enforced = false AND headroom < 0:
       FLAG the premise as not deliverable as costed; count it in §8.6.
6. IF is_enforced = true: ASSERT headroom >= 0 for every premise and period.
```

**Pass criterion.** Steps 1–4 hold; step 5 produces a flag and a count; step 6 holds
whenever the constraint is enforced.

**On failure.** A step 4 violation means diversification was applied twice, or the
per-process rows were written post-diversification — either way the table cannot answer
which process drives the peak. Step 5 is the one that matters before extension 1 exists:
its failure mode is a premise quietly reported as a completed least-cost pathway when the
reinforcement it implies was never priced.

### 10.4 What runs when

| Stage | Tests |
|---|---|
| Reference data load | V3 (uniqueness, vector agreement), V4, V11 (structure), V14 (internal coherence), V15 (steps 1–5) |
| Per premise | V2, V3 (conservation), V6, V11 (tier resolution), V12, V13 (comparison), V14 (A4 cross-check) |
| Per batch | V8, V9, V13 (aggregate), V16 |
| Per release | V1, V5, V7, V10, V15 (step 6) |

**Every test gates a phase.** §11 assigns each of the fifteen to the phase that builds
what it guards, and a test stays in force once introduced:

| Phase | Tests first gating here |
|---|---|
| 1 — Architecture | V1, V2, V3, V4, V6, V7 (G1–G2), V10, V11; V12 and V14 conditionally (§11.5) |
| 2 — Scenarios and aggregation | V8, V9, V13, V16; V12 and V14 if deferred |
| 3 — Process taxonomy | V5, V15; V4 re-run across the new processes |
| 4 — Full coverage | V7 (G3), and all of V1–V16 re-run on the full stock |

A test whose inputs do not exist in its phase is **deferred with the reason recorded**,
never marked passed — see §11.5.

### 10.5 What the tests need that a normal run does not

Three tests require inputs or environments beyond a standard run, and each should be
provisioned before the phase that depends on it (§11):

1. **V1** needs the current COMIT model runnable with its cross-site constraints
   disabled, and the 1,026 NAEI sites expressed as `premise_energy` rows. Confirm the
   coupling can actually be switched off before planning a phase around this test.
2. **V7** needs synthetic premise sets at 10k, 100k and 1M, and hardware representative
   of the intended production environment. The premises need not be realistic — only
   structurally valid — so they can be generated.
3. **V13** needs a subset of premises with reported emissions, which in practice means
   UK ETS or permit-covered sites. These are a small and non-random subset of the stock,
   so the aggregate divergence they show is not representative of the whole.

---

## 11. Phasing with acceptance criteria

*Section last updated: 2026-08-25*

Every test in §10 gates exactly one phase. A test first appears at the phase that builds
the thing it guards, and **remains in force from then on** — a Phase 1 exit criterion is
not retired when Phase 2 begins, it becomes part of the standing bar every later phase
must also clear. Where a test cannot be exercised in its phase because the inputs it
needs are absent, §11.5 says what to do rather than leaving it silently unmet.

### Phase 1 — Architecture

**Entry:** premise records available for 2–3 activities.
**Build:** S1–S8 using **existing COMIT technologies only**; no new process taxonomy.

**Exit:**

| Test | What it establishes here |
|---|---|
| **V1** | Decoupling reproduces coupled-off COMIT — the decomposition itself is sound |
| **V2** | The back-solve from energy to capacity is self-consistent |
| **V3** | A3 conserves energy and the carrier table is coherent |
| **V4** | The profile obeys R1–R3 at load, on the activities in scope |
| **V6** | Non-negativity is asserted where it holds and **not** where it does not |
| **V10** | Results are reproducible and no state leaks between premise solves |
| **V11** | Process sets are well formed and A2's tiering resolves in order |
| **V7** | G1 and G2 pass; G3 attempted and its result recorded |
| **V12**, **V14** | Conditional — see §11.5 |

*Deliberately shallow on process depth. If the architecture does not hold, this is where
it should fail.*

**Why V10 belongs here rather than later.** It is the test that detects state leaking
between premise solves, and that is a defect in the core loop D2 depends on. Finding it
in Phase 1 costs a fix; finding it in Phase 4 invalidates every run made in between.

### Phase 2 — Scenarios and aggregation

**Entry:** Phase 1 exit met, and all Phase 1 criteria still passing.
**Build:** A5, A9; the infrastructure scenario entity; GB comparison reporting.

**Exit:**

| Test | What it establishes here |
|---|---|
| **V8** | GB aggregates are compared against ECUK/GHGI and divergence is reported |
| **V9** | Every clustered energy-intensive premise is run under at least two bounding scenarios, and the spread is reported |
| **V13** | Measured emissions reconcile the baseline without overwriting it |
| **V16** | Network quantities are coherent, and any premise exceeding its connection is flagged rather than reported as complete (§8.5.1). Deferred per §11.5 if network reporting is not yet emitted |
| **V12**, **V14** | If deferred from Phase 1, they pass here — no further deferral |

Plus: a two-scenario spread is produced and reviewed for the clustered energy-intensive
subset.

**Why V13 belongs here.** It is a reconciliation against an external source, which is the
same job §11's Phase 2 gives V8. Both need aggregation reporting to exist before they can
say anything, and both share the discipline that divergence is reported and never
silently corrected.

### Phase 3 — Process taxonomy, high-energy activities

**Entry:** Phase 2 exit met, and all earlier criteria still passing; cost provenance
tiers agreed (D6).
**Build:** commodities, technologies and coefficients for Cement, Iron & steel,
Chemicals, Food & drink, Paper — the sectors with real product chains and process
emissions.

**Exit:**

| Test | What it establishes here |
|---|---|
| **V5** | The emissions invariants hold on the new taxonomy |
| **V15** | Every new process resolves to a load shape, and the §5.6 method reproduces measured baseline peaks |
| **V4** | Re-run — the profile still obeys R1–R3 across the newly added processes |

Plus: every new technology carries provenance and confidence, and the proxy-tier share is
reported.

**Why V15 belongs here.** Load shapes attach to processes (§3.13), so the shape table can
only be complete once the process taxonomy is. Attempting it in Phase 2 would validate a
table that is about to change.

### Phase 4 — Full coverage

**Entry:** Phase 3 exit met, and all earlier criteria still passing.
**Build:** remaining activities; full-stock run.

**Exit:**

| Test | What it establishes here |
|---|---|
| **V7** | G3 passes at full stock scale, or the archetype fallback is triggered (§9.2) |
| **All of V1–V16** | Re-run on the full stock; nothing regressed as coverage widened |

Plus: a complete GB run is produced with its confidence profile.

### 11.5 Tests that may not be exercisable in their phase

**V12** (known-capacity reconciliation) and **V14** (operating profile coherence) depend
on optional site intelligence — `premise_process_detail`, `premise_operating_profile`. If
no premise in the Phase 1 activity set carries those inputs, the tests are vacuous rather
than passing, and recording them as passed would be false.

**The rule.** A test whose inputs are absent is **deferred, with the reason recorded**,
never marked passed. Deferral is permitted once, to the next phase. If the inputs are
still absent at Phase 2, that is itself a finding: it means D10's tiering has never been
exercised on real data, and the tier-1 path is untested code shipping to a national run.

Two ways to close it, in preference order: obtain a premise that carries the inputs, or
construct a synthetic premise that does — the same approach V7 already takes for the
scale gates, where structural validity is enough and realism is not required.

---

## 12. Reference map

*Section last updated: 2026-08-25*

Where each specified behaviour currently lives in COMIT. Cited so an implementer in
either language can verify against a working model.

| Specified in | Behaviour | COMIT reference |
|---|---|---|
| §4 A4 | Capacity ↔ output relationship | [notes/04 Step 3](../notes/04_site_energy_estimation.md) |
| §5.4 | The eight PV cost terms | [notes/09](../notes/09_objective_function.md); `R/fct_pv_*.R` |
| §5.4 | Capex annuitisation, PMT, truncation at horizon | `R/fct_finance.R`; `R/fct_create_cost_tables.R` |
| §5.4 | Rebasing to base price year via deflators | `R/fct_finance.R:130` (`base_year_adjustment`) |
| §5.5 | Constraint families | `R/fct_constraints_*.R` (17 files) |
| §5.5 | Retrofit cost differencing | [notes/09](../notes/09_objective_function.md) |
| §7.1 | Process vs fuel CO₂ split | `R/fct_emissions.R:255-290` |
| §7.2 | Non-CO₂; capture fixed at zero | `R/fct_emissions.R:308-330`, esp. `:327-328` |
| §7.3 | Biomass zero-rating; hardcoded category string | `R/fct_emissions.R:234` |
| §7.4 | Indirect commodity list, hardcoded | `R/fct_emissions.R:180-183` |
| §7.5 | Emissions categories and their overlap | [notes/12 §4.4](../notes/12_output_data_schema.md), [notes/13](../notes/13_emissions_calculation.md) |
| §8 | Output table structure and traps | [notes/12](../notes/12_output_data_schema.md) |
| §9.3 | Solver invocation and selection | `R/comit_solver.R:284`, `:327` |
| §3.2 | CaRB3 activity → process register | [`../notes/data/activity_process_register.csv`](../notes/data/activity_process_register.csv) (376 rows, 55 activities) |
| §3.2 | The narrower source the register was expanded from | [`../notes/data/carb3_factory_processes.json`](../notes/data/carb3_factory_processes.json) |
| §3.3 | Activity → process energy profile | [`../notes/data/activity_process_energy_profile.csv`](../notes/data/activity_process_energy_profile.csv) (490 rows, 137 (activity, set, vector) groups) |
| §3.3 | Per-activity evidence notes and known gaps | [`../notes/data/activity_profile_coverage_notes.csv`](../notes/data/activity_profile_coverage_notes.csv) |
| §3.2, §3.3 | Source bibliography for both tables | [`../notes/data/references.csv`](../notes/data/references.csv) |
| §3.5, D6 | Decarbonisation options per process, with maturity evidence | [`../notes/data/process_decarbonisation_options.csv`](../notes/data/process_decarbonisation_options.csv), [`../notes/data/decarbonisation_options_library.csv`](../notes/data/decarbonisation_options_library.csv) |
| §8.1, A9 | Activity → COMIT sector mapping | [`../notes/data/carb3_comit_crosswalk.csv`](../notes/data/carb3_comit_crosswalk.csv) |
| §3.5 | Existing technology structure to reuse (D6 tier 1) | [`../notes/data/comit_sector_processes.csv`](../notes/data/comit_sector_processes.csv) |
| §7 | Which technologies carry process emissions | [`../notes/data/emissions_source_classification.csv`](../notes/data/emissions_source_classification.csv) |

**What is hardcoded in COMIT today and must become configuration here:** the indirect
commodity list (§7.4), the biomass category string (§7.3), non-CO₂ capture fixed at zero
(§7.2), and the allowed emission-source taxonomy. Full analysis:
[notes/14 §6](../notes/14_emissions_source_split.md).

---

## 13. Worked example

*Section last updated: 2026-08-24*

Moved to a companion document so this specification stays a reference rather than a
narrative: **[2026-08-19-carb3-site-decarbonisation-worked-example.md](2026-08-19-carb3-site-decarbonisation-worked-example.md)**.

It carries one cement premise end to end through A1–A9, exercising every input entity —
long-format energy including a waste-derived fuel row, known process detail and capacity,
measured emissions, operating schedule and load shapes — and re-runs the same premise
with the optional intelligence withheld to isolate what it buys.
