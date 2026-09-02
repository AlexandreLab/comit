# CaRB3 Per-Site Decarbonisation — Input Data Model

> **Generated file — do not edit.**
> Published from [implementation specification §3](../2026-08-19-carb3-site-decarbonisation-implementation.md), which is
> the single source of truth and was last revised 2026-08-26. To change anything here,
> edit that section and re-run
> `python3 docs/notes/examples/build_interface_docs.py`.

Every entity the model reads: the premise record and its long companions,
the reference tables the modelling team maintains, and the optional per-site
intelligence that replaces an assumption with a fact where it exists.

**Who this is for.** Anyone supplying data to the model — principally the
CaRB3 building-stock team, who own §3.1 and its companions. [§1.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#16-what-the-building-stock-model-must-supply) of the
specification states the same contract as a requirement with rationale, and is
the better starting point if you are deciding *what to collect*; this document
is the normative field-level detail you validate against.

**Companion:** [output-data-schema.md](output-data-schema.md) — what the model produces.

**Reading the references.** `§`-numbers inside this document resolve within it;
every other `§` links back to the specification. Labels of the form `A1`–`A9`
(algorithms), `C1`–`C9` (constraints), `V1`–`V17` (validation tests) and `D1`–`D11`
(design decisions) all refer to the specification — see its [§1.3](../2026-08-19-carb3-site-decarbonisation-implementation.md#13-notation).

---

**Also published standalone** as
[interfaces/input-data-model.md](input-data-model.md), for people who supply
data to the model and have no reason to hold the rest of this specification. That file is
**generated from this section** — edit here, then run
`python3 docs/notes/examples/build_interface_docs.py`. A field table maintained in two
places is a field table that will disagree with itself.

Eighteen entities. Each is specified as a field table. Types are abstract ([§1.3](../2026-08-19-carb3-site-decarbonisation-implementation.md#13-notation)).

The premise input contract is the first four — `premise_record` and its three long
companions, `premise_energy`, `premise_throughput` and `premise_connection`. Everything
from §3.2 onward is either reference data maintained by the modelling team, scenario
input, or output.

### 3.1 `premise_record` — the premise itself

The interface between the CaRB3 stock model and this model is three **required**
entities — this one, plus `premise_energy` (§3.1.1) and `premise_throughput` (§3.1.2) —
and one optional fourth, `premise_connection` (§3.1.3), which nothing reads today ([§5.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#56-planned-extensions-network-capacity-reinforcement-and-export)).
That is the same set §3's preamble calls the first four. One row per premise
here; the other two are long tables keyed on `premise_id`. Stated in requirement terms,
with rationale, in **[§1.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#16-what-the-building-stock-model-must-supply)**; these tables are normative for validation.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK | Unique, stable across runs |
| `carb3_activity` | string | — | yes | → `activity_process_register` | Must match one of the **55 CaRB3 Factory-class activities** (D1). Any other class is rejected with reason `out_of_scope_activity`; an unrecognised string with `unknown_activity` ([§1.6.7](../2026-08-19-carb3-site-decarbonisation-implementation.md#167-what-happens-when-a-requirement-is-not-met)) |
| `latitude` | real | degrees | yes | — | Within GB bounding box |
| `longitude` | real | degrees | yes | — | Within GB bounding box |
| `nation` | enum{England, Wales, Scotland} | — | yes | — | NI rejected with reason `out_of_scope_nation` |
| `floorspace` | real | m² | no | — | > 0 if present |
| `process_set_id` | string | — | no | → `activity_process_register` | Selects a named non-default process set (§3.2). Absent ⇒ the activity's default set |
| `construction_year` | integer | year | no | — | **D11.** ≤ `data_year` if present. When the premise was built. Bounds plant age from above (§3.15, [§5.3.1](../2026-08-19-carb3-site-decarbonisation-implementation.md#531-plant-vintage-and-the-survival-function-d11)) |
| `construction_year_band` | string | — | no | — | **D11.** Where only a band is held, e.g. `1945-1964`. Used only if `construction_year` is absent, and read as its **earliest** year |
| `last_refurbishment_year` | integer | year | no | — | **Future use.** ≥ `construction_year`, ≤ `data_year` if present. Collected, not read ([§1.6.4](../2026-08-19-carb3-site-decarbonisation-implementation.md#164-optional-and-what-it-buys)) |
| `data_year` | integer | year | yes | — | Provenance |
| `source` | string | — | yes | — | Provenance |

**On the age band (D11).** CaRB3-style stock data usually holds building age as a band
rather than a year, so both forms are accepted and the year wins where both are present.
A band is read as its **earliest** year, which is the conservative reading: it admits the
widest range of plant ages and therefore stays closest to the default tier. Reading it as
the midpoint or the latest year would make plant look younger than the evidence supports,
and [§1.6.4](../2026-08-19-carb3-site-decarbonisation-implementation.md#164-optional-and-what-it-buys) explains why erring in that direction is the more dangerous mistake.

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
| `connection_id` | string | — | no | PK part → `premise_connection` | **Optional.** The metered connection this quantity came through (§3.1.3). Absent ⇒ the premise's default connection |
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
  is reported as having incomplete carrier coverage ([§8.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#86-run-metadata)).

The stock model should aim to state all five main vectors for every premise, whether by a
positive quantity or an explicit zero. Absence is a last resort, not the default.

**Rule (one row per carrier per connection).** `(premise_id, commodity_id, connection_id)`
is unique. Two meters on the *same* connection are one row — meter-level detail below the
connection belongs upstream. Two meters on *different* connections are two rows, because
the connection is a modelled object (§3.1.3) and the difference is load-bearing.

Sites with a single connection may omit `connection_id` entirely and are unaffected.

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

#### 3.1.3 `premise_connection` — metered connections to the networks

**One row per MPAN or MPRN**, or more precisely per *physical connection*. Industrial
sites frequently have more than one: two electricity connections serving different
sections of the works, a separate supply for a later expansion, distinct gas offtakes for
process and for space heating.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `connection_id` | string | — | yes | PK part | Stable within the premise |
| `carrier` | enum{electricity, gas} | — | yes | — | The network this connects to |
| `identifier` | string | — | no | — | MPAN core or MPRN. See the note on sensitivity below |
| `is_default` | boolean | — | yes | — | Exactly one true per `(premise_id, carrier)`. Receives anything not explicitly assigned |
| `import_capacity` | real | MW | no | — | > 0 if present. Agreed import capacity **at this connection** |
| `export_capacity` | real | MW | no | — | ≥ 0 if present. 0 ⇒ export not permitted here |
| `connection_voltage` | real | kV | no | — | > 0 if present. Electricity only; sets the reinforcement cost curve |
| `metering_type` | enum{half_hourly, non_half_hourly, daily_metered, unmetered} | — | no | — | Determines what §3.14 can carry for this connection |
| `onsite_generation_capacity` | real | MW | no | — | ≥ 0 if present. Generation behind *this* connection |
| `onsite_generation_type` | string | — | no | → `technology` | Required if `onsite_generation_capacity` > 0 |
| `provenance` | string | — | yes | — | Citation: DNO connection agreement, supplier record, site audit |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried through to output |

**Rule — capacities are never summed across connections.** This is the whole point of the
entity, and getting it wrong produces confidently wrong answers. A site with 25 MW on
connection A and 10 MW on connection B does **not** have 35 MW of usable headroom: it has
25 MW where A's processes are and 10 MW where B's are, and moving load between them means
new cabling, not a spreadsheet addition. Headroom, reinforcement and the [§5.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#56-planned-extensions-network-capacity-reinforcement-and-export) constraint
are therefore all evaluated **per connection**, never on a premise total.

**Rule — a premise with no rows has one implied default connection per carrier**, of
unknown capacity. Single-connection sites need no rows at all and nothing downstream
changes for them.

**Rule — gas connections do not determine electrical headroom.** A process currently on a
gas MPRN, once electrified, draws from whichever *electricity* connection serves its part
of the site — which is a fact about site layout, not about the gas meter. The mapping that
resolves this is process-to-connection (§3.10), not meter-to-meter. Inferring the post-
electrification connection from the gas offtake is wrong and will misplace load.

**On `identifier` and sensitivity.** MPAN and MPRN identify a real supply point and are
commercially sensitive: they join to consumption, tariff and customer data held elsewhere.
Store them where they help reconcile against DNO or supplier records, but treat them as
restricted, and **do not emit them in published outputs** — `connection_id` is sufficient
to distinguish connections in results, and carries no external meaning.

### 3.2 `activity_process_register` — activity → processes

Which processes run at a premise of a given activity. Populated by
[`../notes/data/activity_process_register.csv`](../../../notes/data/activity_process_register.csv) —
376 rows covering all 55 activities, with provenance per row. That table supersedes
[`carb3_factory_processes.json`](../../../notes/data/carb3_factory_processes.json), which
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

**The weakest link in the design** (vision [§10](../2026-08-19-carb3-site-decarbonisation-implementation.md#10-validation-and-test-plan)). The premise record supplies *total*
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
   [`../notes/data/carb3_factory_processes.json`](../../../notes/data/carb3_factory_processes.json).
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
in outputs ([§8.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#86-run-metadata)), and its per-process results should not be published on their own —
only the premise total, which is unaffected by the split.

#### 3.3.3 Rules the profile must satisfy

Beyond the sum-to-1 rule above:

**R1 — Technology consistency.** If the profile gives process *q* a non-zero share of
vector *v*, at least one technology serving *q* must have `fuel_category` matching *v*.
Otherwise A4 fails at step 8 with "no technology serves process q on vector v". Assert
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
2. Report the `confidence` distribution alongside every aggregate ([§8.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#86-run-metadata)), so a reader can
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
| `commodity_category` | string | — | yes | — | Fuel grouping; drives biomass zero-rating ([§7.3](../2026-08-19-carb3-site-decarbonisation-implementation.md#73-biomass-zero-rating)) |
| `proportion_emissions_CO2` | real | fraction | yes | — | ∈ [0, 1]. 1 ⇒ all CO₂; 0 ⇒ all non-CO₂ |
| `process_emission` | boolean | — | yes | — | **Data-driven.** True ⇒ quantity *is* the emission in kt CO₂e |
| `is_indirect` | boolean | — | yes | — | **Must be configuration, not code** ([§7.4](../2026-08-19-carb3-site-decarbonisation-implementation.md#74-direct-vs-indirect)) |

**Rule (D5).** A commodity with `process_emission = true` may only be produced by
technologies whose process output has `denominator_kind = mass`. Process emissions are
kt per tonne; denominating them per PJ severs them from their physical basis.

### 3.5 `technology` — extended

One row per *(process × equipment type × fuel)* combination.

**Naming.** Field names deliberately match COMIT's existing columns (`technology_code`, `technology_name`, `capex`, `fixed_opex`, `lifetime`, `availability_factor`, `capacity_to_activity_factor`, `emissions_released`, `retrofit_to`) so that tier-1 reuse (D6) is a direct load from [`../notes/data/comit_sector_processes.csv`](../../../notes/data/comit_sector_processes.csv) and [`../notes/data/emissions_source_classification.csv`](../../../notes/data/emissions_source_classification.csv) with no column translation. `process_id` corresponds to COMIT's `output_commodity` / `process_commodity`.

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
| `retrofit_to` | string | — | no | → `technology` | Costs differenced against the base ([§5.5](../2026-08-19-carb3-site-decarbonisation-implementation.md#55-constraints)) |
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
The emissions formulae in [§7](../2026-08-19-carb3-site-decarbonisation-implementation.md#7-emissions-accounting) depend on this.

### 3.7 `infrastructure_scenario` — exogenous availability (D7)

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `scenario_id` | string | — | yes | PK part | — |
| `carrier` | enum{hydrogen, co2_transport, grid_headroom} | — | yes | PK part | — |
| `cluster_id` | string | — | yes | PK part | One of the 9 GB clusters, or `none` |
| `period` | integer | year | yes | PK part | A model period |
| `available` | boolean | — | yes | — | Whether the carrier can be used |
| `capacity_limit` | real | PJ/yr or kt/yr | no | — | Optional per-premise cap; unbounded if absent |
| `unit_tariff` | real | £m per PJ or kt | yes | — | **Replaces COMIT's four infrastructure PV terms** ([§5.4](../2026-08-19-carb3-site-decarbonisation-implementation.md#54-objective)) |

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
| `stranding_factor` | real | fraction | yes | **D11.** ξ ∈ [0, 1]. Share of an incumbent asset's residual value charged when it is retired early ([§5.4](../2026-08-19-carb3-site-decarbonisation-implementation.md#54-objective)). Default **1.0**. Setting it to 0 removes the charge but does **not** on its own reproduce pre-D11 behaviour — see the COMIT-equivalent configuration in [§5.4](../2026-08-19-carb3-site-decarbonisation-implementation.md#54-objective) |
| `stability_factor` | real | fraction | yes | **σ in C6.** ≥ 0. Measured against deliverable output, not previous activity ([§5.5](../2026-08-19-carb3-site-decarbonisation-implementation.md#55-constraints) C6). Was never declared as an input before, though C6 has always required it |
| `vintage_default` | enum{uniform_life, no_ageing} | — | yes | **D11.** The tier-3 assumption where no vintage evidence exists ([§5.3.1](../2026-08-19-carb3-site-decarbonisation-implementation.md#531-plant-vintage-and-the-survival-function-d11)). Default `uniform_life`, which reproduces COMIT's linear decay. `no_ageing` holds incumbent capacity at full survival and exists only as a diagnostic contrast |

### 3.9 `site_pathway` — output

One row per premise × process × technology × period. See [§8](../2026-08-19-carb3-site-decarbonisation-implementation.md#8-output-schema) for the full output schema.

### 3.10 `premise_process_detail` — known site processes and capacity

**Optional per-premise intelligence.** Where the actual processes at a site are known —
from a permit, an audit, a site visit, or an operator disclosure — they are stated here
and override both the default set and any named variant. Zero rows for a premise is the
normal case and means "use the register".

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `process_id` | string | — | yes | PK part | → `commodity.commodity_id` |
| `connection_id` | string | — | no | → `premise_connection` | **Optional.** Which electricity connection serves this process (§3.1.3). Absent ⇒ the default. This is what decides where electrified load lands |
| `known_capacity` | real | capacity units | no | — | > 0 if present. Units follow the process's denominator (D5): PJ/yr-equivalent for energy, Mt/yr for mass |
| `technology_code` | string | — | no | → `technology` | The specific installed technology, where known |
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

**On vintage (D11).** When the plant was commissioned lives in `premise_process_vintage`
(§3.15), not here. It was moved out because this table is keyed premise × process and can
hold exactly one year, while a real works commonly runs two units of the same process
installed decades apart — a 1998 kiln line and a 2016 one. One year per process cannot
say that, and averaging the two is the thing D11 exists to stop.

### 3.11 `premise_measured_emissions` — reported emissions, where they exist

**Optional per-premise intelligence.** For sites in UK ETS, or covered by permit
reporting or NAEI point-source data, measured emissions exist and are better evidence
than anything this model computes. They are used to **reconcile and calibrate** the
baseline, not to replace the computed value — see [§7.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#76-reconciling-against-measured-emissions) for why that distinction is
forced rather than chosen.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `emission_year` | integer | year | yes | PK part | Should match `premise_record.data_year` |
| `source_category` | enum{combustion, process, total} | — | yes | PK part | `total` only where the split is unavailable |
| `ghg` | enum{CO2, CH4, N2O, total_co2e} | — | yes | PK part | — |
| `quantity` | real | kt CO₂e/yr | yes | — | ≥ 0 |
| `scope` | enum{direct, indirect} | — | yes | — | Indirect excluded from the [§7.4](../2026-08-19-carb3-site-decarbonisation-implementation.md#74-direct-vs-indirect) direct comparison |
| `provenance` | string | — | yes | — | Citation: UK ETS account, permit, NAEI reference |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried through to output |

**Rule.** If both `total` and a `combustion`/`process` breakdown are supplied for the
same premise-year, the parts must sum to the total within 1%, or the record is rejected
with reason `emissions_inconsistent`.

### 3.12 `premise_operating_profile` — schedule and load shape

**Optional per-premise intelligence.** Two distinct things live here, and they answer
different questions. The **operating schedule** says when the site runs, which validates
the utilisation A4 derives. The **load statistics** say how peaky it is, which is what a
connection capacity is actually about ([§5.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#56-planned-extensions-network-capacity-reinforcement-and-export)).

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
| `within_shift_peak_factor` | real | ratio | no | — | ≥ 1. Peak ÷ mean demand *during operating hours* ([§5.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#56-planned-extensions-network-capacity-reinforcement-and-export)) |
| `profile_basis` | enum{half_hourly, daily, monthly, schedule_only, estimated} | — | yes | — | What the statistics were derived from |
| `provenance` | string | — | yes | — | Citation: meter operator, DNO connection record, site audit |
| `confidence` | enum{high, medium, low} | — | yes | — | Carried through to output |

**Rule (derived statistics, not raw profiles).** Half-hourly data is ~17,520 points per
premise per year and does not belong in this contract — at stock scale it is larger than
every other input combined, and this model is annual ([§5.1](../2026-08-19-carb3-site-decarbonisation-implementation.md#51-sets-and-indices)) so it cannot consume the
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

**Optional per-premise intelligence, and the highest tier of vintage evidence.** Where
the commissioning date of the plant serving a process is known — from a permit, a
BAT/BREF review, an asset register, a site visit or an operator disclosure — it is stated
here. Zero rows for a premise is the normal case and means "fall through to
`premise_record.construction_year`, and then to the default" ([§5.3.1](../2026-08-19-carb3-site-decarbonisation-implementation.md#531-plant-vintage-and-the-survival-function-d11)).

One row per **cohort**: a distinct tranche of capacity commissioned in the same year. A
works with one kiln has one row; a works whose second line was added eighteen years after
the first has two.

| Field | Type | Unit | Req | Key | Validation |
|---|---|---|---|---|---|
| `premise_id` | string | — | yes | PK part | → `premise_record` |
| `process_id` | string | — | yes | PK part | → `commodity.commodity_id` |
| `cohort_id` | string | — | yes | PK part | Stable within the premise-process. `1`, `2`, … is sufficient |
| `technology_code` | string | — | no | → `technology` | The technology this cohort is. Absent ⇒ whatever A4 resolves for the process |
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
[§5.3.1](../2026-08-19-carb3-site-decarbonisation-implementation.md#531-plant-vintage-and-the-survival-function-d11) — recording an overhaul as a new commissioning date is the wrong way to represent
it, because it also resets the residual value the asset is carrying and makes early
replacement look more expensive than it is.

**Why a separate entity from §3.10.** `premise_process_detail` is keyed premise × process
and asserts a *complete* process list; this table is keyed one level finer and asserts
nothing about completeness. A premise may have vintage rows for its kiln and none for its
mills, and the mills simply fall to the next tier. Forcing the two into one table would
have made vintage all-or-nothing for a site, which is the opposite of how the evidence
actually arrives.
