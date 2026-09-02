# CaRB3 Site Energy System — Implementation Specification (v2)

**Status:** Draft — §1, §2, §3 and §5 written (T4). §4 is a stub owned by T13; §6–§13 are not yet written
**Date:** 2026-09-01
**Scope:** Great Britain (England, Wales, Scotland) · CaRB3 **Factory class** only (55 activities)
**Plan:** [overview](2026-08-28-carb3-site-energy-system-overview.md) ·
[architecture](2026-08-28-carb3-site-energy-system-architecture.md) ·
[spec changes](2026-08-28-carb3-site-energy-system-spec-changes.md) ·
[data migration](2026-08-28-carb3-site-energy-system-data-migration.md) ·
[delivery](2026-08-28-carb3-site-energy-system-delivery.md)
**v1, frozen:** [2026-08-19-carb3-site-decarbonisation-implementation.md](2026-08-19-carb3-site-decarbonisation-implementation.md) — retained as the COMIT-parity baseline that V1 validates against
**Design decisions:** [vision §6](2026-08-19-carb3-site-decarbonisation-vision.md) defines `D1`–`D11`

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

Eleven entities are defined below. Entities carried over from v1 unchanged are listed in §3.12
rather than restated; they must be inlined here before v2 can stand alone.

§3.10 and §3.11 are the **default database**: what duty each process presents, and what plant
typically serves it. Both were missing from v1 and v2 alike — the audit in
[notes/16](../notes/16_input_data_readiness.md) sets out what that left broken.

### 3.1 `carrier`

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

### 3.2 `unit`

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

### 3.3 `unit_input_output`

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

### 3.4 `unit_eligibility`

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

### 3.5 `unit_bill_of_materials`

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

### 3.6 `archetype_coefficient`

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

### 3.7 `process_duty`

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

### 3.8 `premise_connection`

Carried over from v1 §3.1.3 **unchanged in fields**, and read for the first time. One row per
MPAN or MPRN.

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

### 3.9 `scenario_parameters`

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

### 3.10 `activity_process_duty_profile`

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

### 3.11 `activity_default_unit`

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

### 3.12 Entities carried over from v1 unchanged

These are unchanged in fields and meaning and are **not restated here**. They must be
inlined before v2 supersedes v1; until then read them in the v1 spec at the section given.

**Every number in this list is a `v1 §` and none of them is a section of this document.**
The two specs now overlap in the 3.10–3.12 range — v1's `premise_process_detail`,
`premise_measured_emissions` and `premise_operating_profile` sit at exactly the numbers this
document gives `activity_process_duty_profile`, `activity_default_unit` and this section. The
`v1` prefix below is therefore load-bearing, not decoration.

`premise_record` (v1 §3.1) · `premise_energy` (v1 §3.1.1) · `premise_throughput` (v1 §3.1.2) ·
`activity_process_register` (v1 §3.2) · `infrastructure_scenario` (v1 §3.7) ·
`premise_process_detail` (v1 §3.10) · `premise_measured_emissions` (v1 §3.11) ·
`premise_operating_profile` (v1 §3.12) · `process_load_shape` (v1 §3.13) ·
`premise_weekly_profile` (v1 §3.14) · `premise_process_vintage` (v1 §3.15).

**`activity_process_energy_profile` is deliberately absent.** Its vector-share allocation is
replaced by the carrier balance. The table itself survives as an input to S3, which splits
metered energy onto carriers, and as V1b's parity target (§3.10 of *this* document), but it
no longer determines how energy reaches a process.

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
