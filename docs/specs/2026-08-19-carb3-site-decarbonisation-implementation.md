# CaRB3-Driven Per-Site Decarbonisation — Implementation Specification

**Status:** Draft v1 for review
**Date:** 2026-08-19
**Vision and rationale:** [2026-08-19-carb3-site-decarbonisation-vision.md](2026-08-19-carb3-site-decarbonisation-vision.md)
**Supersedes:** [2026-08-05-site-heterogeneity-prd.md](2026-08-05-site-heterogeneity-prd.md)

---

## 1. Scope, inputs, conventions, and how to read this

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
| `C1`–`C9` | Components — the software pieces that run those algorithms | §2.1 |
| `V1`–`V15` | Validation tests and acceptance criteria | §10 |
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
| **Vector** | An energy carrier as metered at the premise: electricity, gas, oil, coal, biomass. |
| **Commodity** | A modelled flow — a fuel, an intermediate material, a process-emission pseudo-commodity, or a process's output. |
| **Denominator** | The unit a technology's coefficients are expressed per: PJ of useful energy, or a physical mass. See D5. |
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
| `energy_electricity` | PJ/yr | Split across processes (A3), then back-solved into implied capacity (A4) | No baseline; nothing to decarbonise from |
| `energy_gas` | PJ/yr | As above | As above |
| `energy_oil` | PJ/yr | As above | As above |
| `energy_coal` | PJ/yr | As above | As above |
| `energy_biomass` | PJ/yr | As above; also drives biomass zero-rating (§7.3) | Biomass is silently treated as a fossil fuel or omitted |
| `latitude`, `longitude` | degrees | Assigns the premise to one of the 9 GB clusters (A1 step 11), which determines H₂/CO₂ availability (D7) | No infrastructure scenario can be applied |
| `nation` | enum | Enforces GB scope (D8) | NI premises contaminate GB aggregates |
| `data_year` | year | Provenance; anchors the baseline in time | Results cannot be dated or rebased |
| `source` | — | Provenance; supports the confidence reporting in §8.5 | Result quality cannot be characterised |

**The five energy vectors must be supplied separately.** A single total-energy figure is
not sufficient: A4 back-solves existing capacity by matching each vector to the
technologies that can consume it, so a total with no split cannot identify what
equipment the site currently runs. This is the single most important requirement in this
section.

#### 1.6.3 Required for some premises

| Item | Unit | When required | Why |
|---|---|---|---|
| `throughput_quantity` | Mt/yr | Activities carrying a mass-denominated process (D5) | Process emissions are kt CO₂ per tonne of material. Without physical throughput they have no denominator and cannot be modelled — and these are exactly the activities where process emissions dominate |
| `throughput_commodity` | — | Whenever `throughput_quantity` is present | Identifies which material the tonnage refers to |
| `energy_other_carrier` | — | Whenever `energy_other` > 0 | An unnamed carrier cannot be priced or given an emission factor |

#### 1.6.4 Optional, and what it buys

Everything below is genuinely optional — the model runs without any of it. But each item
replaces an assumption with a fact for the premises that have it, and the tier used is
recorded on every output row, so a reader can always tell a known site from an assumed
one.

| Item | Unit | What it enables |
|---|---|---|
| `floorspace` | m² | Cross-checking energy intensity on ingest; a fallback basis for site-services energy where the profile needs one |
| `energy_other` | PJ/yr | Coverage of carriers outside the five main vectors — LPG, waste-derived fuel, purchased heat |
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
   Factory-class stock it represents, since §8.5 reports results against it and A9
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
| `missing_throughput` | Mass-denominated activity with no `throughput_quantity` |

**Batch-level gate.** If the rejection rate exceeds a configured threshold, the whole
batch fails rather than proceeding on a filtered subset — a high rejection rate signals
a contract mismatch, not a data-cleaning opportunity.

---

## 2. System overview

### 2.1 Components

| # | Component | Responsibility |
|---|---|---|
| C1 | **Ingestion and validation** | Accept premise records, validate, reject with reasons |
| C2 | **Process expansion** | Premise → its set of processes, via the activity register |
| C3 | **Energy allocation** | Split the premise's metered energy across its processes |
| C4 | **Baseline capacity solve** | Back-solve implied existing technology capacity per process |
| C5 | **Scenario application** | Attach fuel prices, carbon price, infrastructure availability |
| C6 | **Problem builder** | Construct the per-premise optimisation (§5) |
| C7 | **Solver driver** | Solve, extract, handle infeasibility |
| C8 | **Output assembly** | Produce the per-premise pathway tables (§8) |
| C9 | **Aggregation and comparison** | Roll up to GB; compare against ECUK/GHGI |

C1–C8 run per premise and are independent across premises. C9 runs once over all
results.

### 2.2 Data flow

```
premise_record ──C1──► validated premise
                        │
                        ├─C2─► process set              (activity_process_register)
                        ├─C3─► energy per process       (activity_process_energy_profile)
                        ├─C4─► implied existing capacity (technology, technology_input_output)
                        └─C5─► prices, availability     (scenario_parameters, infrastructure_scenario)
                                    │
                                    ▼
                              C6 build problem ──► C7 solve ──► C8 site_pathway
                                                                     │
                                                                     ▼
                                                          C9 aggregate → GB comparison
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

Nine entities. Each is specified as a field table. Types are abstract (§1.3).

### 3.1 `premise_record` — the input contract

The interface between the CaRB3 stock model and this model. One row per premise. Stated
in requirement terms, with rationale, in **§1.6**; this table is normative for validation.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK | Unique, stable across runs |
| `carb3_activity` | string | — | yes | → `activity_process_register` | Must match one of the **55 CaRB3 Factory-class activities** (D1). Any other class is rejected with reason `out_of_scope_activity`; an unrecognised string with `unknown_activity` (§1.6.7) |
| `latitude` | real | degrees | yes | — | Within GB bounding box |
| `longitude` | real | degrees | yes | — | Within GB bounding box |
| `nation` | enum{England, Wales, Scotland} | — | yes | — | NI rejected with reason `out_of_scope_nation` |
| `energy_electricity` | real | PJ/yr | yes | — | ≥ 0 |
| `energy_gas` | real | PJ/yr | yes | — | ≥ 0 |
| `energy_oil` | real | PJ/yr | yes | — | ≥ 0 |
| `energy_coal` | real | PJ/yr | yes | — | ≥ 0 |
| `energy_biomass` | real | PJ/yr | yes | — | ≥ 0 |
| `energy_other` | real | PJ/yr | no | — | ≥ 0; carrier named in `energy_other_carrier` |
| `energy_other_carrier` | string | — | no | → `commodity` | Required if `energy_other` > 0 |
| `floorspace` | real | m² | no | — | > 0 if present |
| `process_set_id` | string | — | no | → `activity_process_register` | Selects a named non-default process set (§3.2). Absent ⇒ the activity's default set |
| `import_capacity` | real | MW | no | — | > 0 if present. Agreed grid import capacity at the connection point |
| `export_capacity` | real | MW | no | — | ≥ 0 if present. Agreed export capacity; 0 ⇒ export not permitted |
| `connection_voltage` | real | kV | no | — | > 0 if present. Distinguishes LV/HV/EHV connections for reinforcement costing |
| `onsite_generation_capacity` | real | MW | no | — | ≥ 0 if present |
| `onsite_generation_type` | string | — | no | → `technology` | Required if `onsite_generation_capacity` > 0 |
| `data_year` | integer | year | yes | — | Provenance |
| `source` | string | — | yes | — | Provenance |
| `throughput_quantity` | real | Mt/yr | cond | — | **Required** for activities with mass-denominated processes (D5); see §3.4 and the note below |
| `throughput_commodity` | string | — | cond | → `commodity` | Required if `throughput_quantity` present |

**Rule.** At least one `energy_*` field must be strictly positive. A premise with zero
total energy is rejected with reason `no_energy`.

**On throughput (agreed 2026-08-21).** Physical throughput is **not** a best-effort
optional field: without it, the mass denominators that D5 requires cannot be populated,
and process emissions — calcination CO₂ and equivalents — lose their physical basis for
precisely the activities where they dominate. The upstream stock model will be extended
to supply it. This design therefore assumes `throughput_quantity` is present for every
premise whose activity carries a mass-denominated process, and A1 rejects such a premise
if it is absent (`missing_throughput`). For all other activities the field is optional
and unused.

### 3.2 `activity_process_register` — activity → processes

Which processes run at a premise of a given activity. Seeded from
[`../notes/data/carb3_factory_processes.json`](../notes/data/carb3_factory_processes.json).

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
in outputs (§8.5), and its per-process results should not be published on their own —
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
3.    IF denom = 0 AND p.energy_v > 0:
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
2. Report the `confidence` distribution alongside every aggregate (§8.5), so a reader can
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
they must reconcile against that vector's annual energy in `premise_record` within 5%:

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
6.     total_energy := SUM of r.energy_* fields
7.     IF total_energy <= 0:
8.         REJECT r REASON "no_energy"; CONTINUE
9.     IF ANY r.energy_* < 0:
10.        REJECT r REASON "negative_energy"; CONTINUE
11.    r.cluster_id := nearest cluster to (r.latitude, r.longitude) among the 9
12.    r.cluster_distance := distance to that cluster
13.    IF activity requires mass denominator AND r.throughput_quantity IS ABSENT:
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

1. FOR EACH vector v IN {electricity, gas, oil, coal, biomass, other}:
2.     e_v := p.energy_{v}
3.     IF e_v = 0: CONTINUE
4.     share' := RENORMALISE(p, v)      -- §3.3.3 R2; identity if no optional
5.     FOR EACH process q IN process_set(p) WHERE share'[q, v] EXISTS:
6.         process_energy[q, v] := e_v * share'[q, v]
7. ASSERT SUM over (q, v) of process_energy = SUM over v of p.energy_v   (within 1e-6)

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

$$Z^{\text{infra}}_t = \sum_{k \in K} \Big( u_{k,t}\,|\iota_{k,\text{H}_2}|\,\tau_{\text{H}_2,t} \;+\; \mathrm{CO}_2^{\text{captured}}_{k,t}\,\tau_{\text{CO}_2,t} \Big)$$

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

**Sequencing.** Both extensions are per-premise and therefore compatible with D2 — a
connection capacity is a property of one site, not shared between sites. Neither should
be attempted before Phase 2, and both should be specified against real load-factor
evidence rather than assumed.

---

## 6. Constraint disposition

COMIT has 17 constraint families. Under D2 they divide three ways.

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

**Two things to note, both load-bearing:**

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
| `confidence` | enum | Lowest of technology and profile confidence |
| `⟨period⟩` | real | Activity in that period |

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
`Carbon cost`, `Infrastructure tariff`}. Values in £m per period, un-discounted and
rebased to `base_price_year`.

**`Capex` and `Capex_lump` are two views of the same money** — annuitised stream and
build-year spike. Never sum them.

### 8.5 Run metadata

Every output set carries: scenario id, infrastructure scenario id, period definition,
counts of premises accepted/rejected/infeasible, and the **share of results resting on
proxy-tier costs and low-confidence energy profiles**.

---

## 9. Performance and parallelisation

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

| # | Test | Criterion |
|---|---|---|
| **V1** | **Decoupling parity.** Run current COMIT and this model over the same 1,026 NAEI sites with coupling constraints disabled on both sides | Per-site results agree to solver tolerance. Isolates decomposition from every other change |
| **V2** | **Baseline reproduction.** Recompute fuel use from `existing_capacity` produced by A4 | Reproduces the supplied per-vector energy within 1% |
| **V3** | **Energy conservation.** A3's allocation | Allocated energy equals metered energy within 1e-6 |
| **V4** | **Profile integrity.** `activity_process_energy_profile` | Shares sum to 1 per (activity, vector) within 1e-6; R1 technology consistency and R3 band ordering hold at load; R2 renormalisation reproduces the raw shares when no optional process is absent (§3.3.3) |
| **V5** | **Emissions invariants** (from [notes/14](../notes/14_emissions_source_split.md)) | `Direct (split by ghg type)` summed over gases equals `Direct (total CO2e)`; `available_capacity` equals cumulative `new_capacity`; `Generate_emissions = false` ⇒ zero ktCO₂e |
| **V6** | **Non-negativity, correctly scoped** | Activity, energy and capacity are non-negative. Costs and emissions **may be negative** (retrofit differencing, BECCS). Do not assert blanket non-negativity — [notes/14](../notes/14_emissions_source_split.md) records this as a falsified invariant |
| **V7** | **Scale gates** | G1–G3 per §9.2 |
| **V8** | **GB aggregate sanity** | Sector totals compared against ECUK/GHGI on a GB basis; divergence reported, never silently corrected |
| **V9** | **Infrastructure sensitivity** | Every clustered energy-intensive premise run under at least two bounding scenarios; spread reported |
| **V10** | **Determinism** | Same inputs reproduce the same outputs bit-for-bit, given the §9.3 tie-break |
| **V11** | **Process set integrity.** `activity_process_register` and A2 tiering | Exactly one default set per activity; every named set resolves to profile rows by §3.3 inheritance; a premise citing a set belonging to another activity is rejected; `premise_process_detail` overrides both and is treated as complete |
| **V12** | **Known-capacity reconciliation.** A4 steps 14–18 | Where `known_capacity` is supplied, energy still reconciles within 1e-6 (V2 unaffected) and the derived utilisation is reported. Utilisation exceeding the availability factor is logged as `capacity_energy_inconsistent`, not silently clipped |
| **V13** | **Measured-emissions divergence.** §7.6 | Baseline computed emissions compared against `premise_measured_emissions` per premise and in aggregate; divergence reported and never silently corrected. With calibration enabled, every multiplier lies in the configured bound and is recorded on output |
| **V14** | **Operating profile coherence.** §3.12, A4 | Peak, load factor and annual energy reconcile within 5%; utilisation derived in A4 is consistent with `operating_hours_per_year`, with disagreement logged as `utilisation_schedule_inconsistent`; `within_shift_peak_factor` ≥ 1 wherever present |
| **V15** | **Load shape coherence.** §3.13, §3.14, §5.6 | Every process resolves to a shape; `standing` ⇔ `runs_when_idle`; `peak_to_mean` ≥ 1 and `duty_factor` ∈ (0,1]; weekly profiles are normalised to a maximum of 1 over 336 intervals; the §5.6 method reproduces the measured baseline peak within tolerance before any projected peak is reported |

**On V1.** This is the single most valuable test, because it isolates the one change
most likely to be wrong. Note that parity with *fully coupled* COMIT is **not** a valid
criterion (vision §7.4).

---

## 11. Phasing with acceptance criteria

### Phase 1 — Architecture

**Entry:** premise records available for 2–3 activities.
**Build:** C1–C8 using **existing COMIT technologies only**; no new process taxonomy.
**Exit:** V1, V2, V3, V7 (G1 and G2) all pass; G3 attempted and its result recorded.

*Deliberately shallow on process depth. If the architecture does not hold, this is where
it should fail.*

### Phase 2 — Scenarios and aggregation

**Entry:** Phase 1 exit met.
**Build:** A5, A9; the infrastructure scenario entity; GB comparison reporting.
**Exit:** V8, V9 pass; a two-scenario spread is produced and reviewed for the clustered
energy-intensive subset.

### Phase 3 — Process taxonomy, high-energy activities

**Entry:** Phase 2 exit met; cost provenance tiers agreed (D6).
**Build:** commodities, technologies and coefficients for Cement, Iron & steel,
Chemicals, Food & drink, Paper — the sectors with real product chains and process
emissions.
**Exit:** V5 passes on the new taxonomy; every new technology carries provenance and
confidence; the proxy-tier share is reported.

### Phase 4 — Full coverage

**Entry:** Phase 3 exit met.
**Build:** remaining activities; full-stock run.
**Exit:** V7 (G3) passes; a complete GB run is produced with its confidence profile.

---

## 12. Reference map

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
| §3.2 | CaRB3 activity → process register source | [`../notes/data/carb3_factory_processes.json`](../notes/data/carb3_factory_processes.json) |
| §8.1, A9 | Activity → COMIT sector mapping | [`../notes/data/carb3_comit_crosswalk.csv`](../notes/data/carb3_comit_crosswalk.csv) |
| §3.5 | Existing technology structure to reuse (D6 tier 1) | [`../notes/data/comit_sector_processes.csv`](../notes/data/comit_sector_processes.csv) |
| §7 | Which technologies carry process emissions | [`../notes/data/emissions_source_classification.csv`](../notes/data/emissions_source_classification.csv) |

**What is hardcoded in COMIT today and must become configuration here:** the indirect
commodity list (§7.4), the biomass category string (§7.3), non-CO₂ capture fixed at zero
(§7.2), and the allowed emission-source taxonomy. Full analysis:
[notes/14 §6](../notes/14_emissions_source_split.md).

---

## 13. Worked example

One premise, end to end. Illustrative values.

**Input.**

```
premise_id           P-000123
carb3_activity       Cement Works
nation               England
latitude/longitude   53.35 / -1.75
energy_electricity   0.42 PJ/yr
energy_coal          3.90 PJ/yr
energy_gas           0.31 PJ/yr
throughput_quantity  0.85 Mt/yr   (clinker)
```

**A1 — validate.** Nation in scope; activity known; energy positive; throughput present
(required, because Cement Works has a mass-denominated process). Nearest of the 9
clusters assigned.

**A2 — expand.** `Cement Works` registers two processes:
`Calcination` (denominator **mass**, carries process emissions) and
`Milling` (denominator **energy**).

**A3 — allocate.** Applying the activity's energy profile:

| Process | Electricity | Coal | Gas |
|---|---|---|---|
| Calcination | 0.08 | 3.90 | 0.28 |
| Milling | 0.34 | 0.00 | 0.03 |
| **Total** | **0.42** | **3.90** | **0.31** |

Totals reconcile with the input (V3).

**A4 — back-solve capacity.** For the coal-fired calcination technology, with
`|io| = 4.6 PJ per Mt`, `capacity_to_activity = 1`, `availability = 0.9`:

```
annual_output = 3.90 / 4.6            = 0.848 Mt
capacity      = 0.848 / (1 × 0.9)     = 0.942 Mt capacity
```

The implied output (0.848 Mt) reconciles with the declared throughput (0.85 Mt) to
within 0.2% — a useful cross-check that the profile and coefficients agree.

**A5 — scenario.** The premise's cluster has `co2_transport.available = true` from 2035
at a tariff of £18m/Mt; hydrogen unavailable throughout.

**A6/A7 — solve.** Available calcination technologies: coal kiln (incumbent), gas kiln,
coal kiln with CCS (from 2035). The solver trades the CCS capex and CO₂ tariff against
avoided carbon cost on both the fuel **and** the calcination process emissions — the
latter being untouchable by fuel switching (D5, §7.1). Milling, being purely electric
motor load, switches on fuel price alone.

**A8 — output.** Rows emitted per process × technology × period across `Outputs`,
`Energy`, `Emissions`, `Costs`, each carrying the lower of the technology's and the
profile's confidence.

**A9 — aggregate.** The premise contributes to the `Cement` sector total via the
crosswalk, and to the GB energy and emissions trajectories.

**What the example demonstrates:** the mass denominator is load-bearing. Had
`Calcination` been denominated in PJ, its process emissions would have scaled with fuel
efficiency, and a more efficient kiln would have appeared to emit less calcination CO₂ —
which is physically wrong. That is the entire justification for D5.
