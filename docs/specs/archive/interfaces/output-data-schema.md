# CaRB3 Per-Site Decarbonisation — Output Data Schema

> **Generated file — do not edit.**
> Published from [implementation specification §8](../2026-08-19-carb3-site-decarbonisation-implementation.md), which is
> the single source of truth and was last revised 2026-08-26. To change anything here,
> edit that section and re-run
> `python3 docs/notes/examples/build_interface_docs.py`.

Every table a run produces, its keys, its units, and the traps that make two
of them look interchangeable when they are not.

**Who this is for.** Anyone consuming results — analysts, aggregation code,
and anyone comparing one run against another. The evidence-tier and confidence
fields are not decoration: they are the only way to tell how much of a result
rests on a measurement rather than on a default, and [§10](../2026-08-19-carb3-site-decarbonisation-implementation.md#10-validation-and-test-plan) has validation tests
that exist solely to keep them honest.

**Companion:** [input-data-model.md](input-data-model.md) — what the model reads.

**Reading the references.** `§`-numbers inside this document resolve within it;
every other `§` links back to the specification. Labels of the form `A1`–`A9`
(algorithms), `C1`–`C9` (constraints), `V1`–`V17` (validation tests) and `D1`–`D11`
(design decisions) all refer to the specification — see its [§1.3](../2026-08-19-carb3-site-decarbonisation-implementation.md#13-notation).

---

**Also published standalone** as
[interfaces/output-data-schema.md](interfaces/output-data-schema.md), for people who
consume results. Generated from this section on the same terms as [§3](../2026-08-19-carb3-site-decarbonisation-implementation.md#3-data-model) — edit here and
re-run the builder.

Reuse the structure documented in [notes/12](../../../notes/12_output_data_schema.md), extended
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
| `process_set_id` | string | **New (D10).** Which process set this premise resolved to ([§3.2](../2026-08-19-carb3-site-decarbonisation-implementation.md#32-activity_process_register-activity-processes)) |
| `process_evidence_tier` | enum{site_known, named_set, activity_default} | **New (D10).** Which tier A2 used. Required by V11 — without it an aggregate cannot say which premises were surveyed and which were defaulted |
| `utilisation` | real | **New.** Derived in A4. Equals the availability factor where capacity was back-solved, and the energy-implied value where capacity was known (§A4) |
| `carrier_coverage` | enum{complete, incomplete} | **New.** Whether all five main vectors were stated for this premise, whether positive or an explicit `not_consumed` zero ([§3.1.1](../2026-08-19-carb3-site-decarbonisation-implementation.md#311-premise_energy-consumption-by-carrier)) |
| `emissions_calibration_multiplier` | real | **New.** Present only where [§7.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#76-reconciling-against-measured-emissions) intensity calibration was enabled. Required by V13 |
| `vintage_evidence_tier` | enum{process_known, premise_bounded, uniform_default, no_ageing} | **New (D11).** Which tier A4 used to age this technology's incumbent capacity ([§5.3.1](../2026-08-19-carb3-site-decarbonisation-implementation.md#531-plant-vintage-and-the-survival-function-d11)). Blank for a technology with no existing capacity. Required by V17 |
| `commissioned_year` | integer | **New (D11).** The cohort year, present only at tier `process_known`. Blank at the other tiers rather than filled with the tier's assumption, so an assumed age can never be mistaken for a known one |
| `remaining_life_years` | real | **New (D11).** Mean remaining life of the surviving incumbent pool in this period ([§5.3.1](../2026-08-19-carb3-site-decarbonisation-implementation.md#531-plant-vintage-and-the-survival-function-d11)), anchored on the first model period and **not** on `data_year`. Required by V17 |
| `confidence` | enum | Lowest of technology and profile confidence |
| `⟨period⟩` | real | Activity in that period |

**Rule.** The eight evidence-bearing fields — `process_set_id`,
`process_evidence_tier`, `utilisation`, `carrier_coverage`,
`emissions_calibration_multiplier`, `vintage_evidence_tier`, `commissioned_year` and
`remaining_life_years` — are not decoration. (`process_id` and `equipment_type` are also
marked new, but they are dimensions rather than evidence markers.) Four validation tests
assert their presence — V11 on the process evidence tier, V12 on utilisation, V13 on the
calibration multiplier, V17 on the vintage tier and remaining life — because each is the
only way a reader can tell how much of a result rests on evidence rather than on a
default.

**On `commissioned_year` being blank at tiers 2 and 3.** Tiers 2 and 3 do have a working
age assumption, and it would be easy to write its midpoint into this column. Do not: a
column that sometimes holds a surveyed date and sometimes holds a derived one is a column
nobody can aggregate safely, and the derived value is already fully described by
`vintage_evidence_tier` plus `remaining_life_years`. Blank means *"nobody told us"*, which
is the fact a reader needs.

### 8.2 `Energy`

As above, plus `input_commodity`, with two period-column families:
`⟨period⟩_PJ` and `⟨period⟩_ktCO2e`.

**Carry forward the warning from [notes/12 gotcha 14](../../../notes/12_output_data_schema.md):**
the `ktCO2e` columns here are gross combustion emissions of the fuel, before biogenic
zero-rating and capture. They are **not** interchangeable with the `Emissions` table.
Document this in the output workbook itself.

### 8.3 `Emissions`

As `Outputs`, plus `emissions_category`, `co2_noncoo2`, `emission_type`, `ghg_type`.
Values in kt; negative permitted for the `Negative` category.

### 8.4 `Costs`

As `Outputs`, plus `cost_type` ∈ {`Capex`, `Capex_lump`, `Opex`, `Fuel cost`,
`Carbon cost`, `Infrastructure tariff`, `Stranded value`, `Network reinforcement`,
`Export revenue`}. Values in £m per period, un-discounted and rebased to
`base_price_year`.

**`Stranded value` is a write-off, not a purchase (D11).** It is the residual value of
incumbent plant scrapped before the end of its life ([§5.4](../2026-08-19-carb3-site-decarbonisation-implementation.md#54-objective)), booked in the period the
capacity leaves. It buys nothing and appears alongside the `Capex` of whatever replaced
it, so the two must not be netted. A run with `stranding_factor = 0` emits the column with
zeros throughout rather than omitting it, so that two runs stay column-comparable.

**`Capex` and `Capex_lump` are two views of the same money** — annuitised stream and
build-year spike. Never sum them.

**`Network reinforcement` and `Export revenue` appear only once [§5.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#56-planned-extensions-network-capacity-reinforcement-and-export)'s extensions are
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
| `connection_id` | string | **The row's subject.** Every metric below is per connection ([§3.1.3](../2026-08-19-carb3-site-decarbonisation-implementation.md#313-premise_connection-metered-connections-to-the-networks)), never a premise total |
| `cluster_id` | string | One of 9 |
| `process_id` | string | **Optional.** Present on per-process peak contributions; absent on whole-connection rows |
| `network_metric` | enum | See the table below |
| `basis` | enum{measured, derived_from_profile, derived_from_schedule, activity_default} | How the value was arrived at — the [§5.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#56-planned-extensions-network-capacity-reinforcement-and-export) tiers. `measured` only where `premise_operating_profile` supplied it |
| `is_enforced` | boolean | Whether the value constrained the solve, or was computed and reported only. See below |
| `confidence` | enum | Lowest of the shape and profile confidence contributing to it |
| `⟨period⟩_MW` | real | The value in that period |

**The metrics.**

| `network_metric` | Meaning |
|---|---|
| `import_capacity` | The connection's agreed import capacity, as supplied ([§3.1](../2026-08-19-carb3-site-decarbonisation-implementation.md#31-premise_record-the-premise-itself)) |
| `export_capacity` | Agreed export capacity; 0 where export is not permitted |
| `peak_demand_electricity` | Modelled electrical peak in that period, from the [§5.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#56-planned-extensions-network-capacity-reinforcement-and-export) derivation |
| `peak_demand_baseline` | The baseline-year peak, measured where available — the calibration anchor of [§5.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#56-planned-extensions-network-capacity-reinforcement-and-export) |
| `headroom` | `import_capacity + reinforcement − peak_demand_electricity`, **for that connection**. Negative means the pathway exceeds it |
| `reinforcement_required` | Additional capacity the pathway implies, i.e. `max(0, −headroom)` before any reinforcement |
| `reinforcement_purchased` | Reinforcement actually taken, once extension 1 makes this a decision variable. Equals `reinforcement_required` while the model only reports |
| `onsite_generation` | Installed generation capacity |
| `exported_power` | Peak power exported, bounded by `export_capacity` |

**Per-process rows are diagnostic.** Where `process_id` is present the row carries that
process's own peak contribution *before* diversification ([§5.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#56-planned-extensions-network-capacity-reinforcement-and-export) step 8), which is what
tells a reader which process drives a connection's peak. They therefore **sum to more
than** the whole-connection `peak_demand_electricity` row, and must not be added to reach
a total.

**There is deliberately no premise-level row.** A site with two connections has two
`import_capacity` rows and two `headroom` rows, and no row summing them, because that sum
is not a quantity that means anything ([§3.1.3](../2026-08-19-carb3-site-decarbonisation-implementation.md#313-premise_connection-metered-connections-to-the-networks)). A reader wanting "the site's headroom"
must be made to ask *which connection*, which is the real question.

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
| Rejection counts **by reason** ([§1.6.7](../2026-08-19-carb3-site-decarbonisation-implementation.md#167-what-happens-when-a-requirement-is-not-met)) | A batch failing on one reason is a contract problem; failing on many is a data problem |
| Share of results resting on **proxy-tier costs** (D6) | Cost confidence |
| Share resting on **fallback-tier energy profiles** ([§3.3.2](../2026-08-19-carb3-site-decarbonisation-implementation.md#332-evidence-tiers)) | Profile confidence |
| Distribution of **`process_evidence_tier`** across premises (D10) | How much of the run is surveyed versus defaulted |
| Count of premises with **incomplete carrier coverage** ([§3.1.1](../2026-08-19-carb3-site-decarbonisation-implementation.md#311-premise_energy-consumption-by-carrier)) | Where a vector was never assessed, so absence is not zero |
| Count of premises reporting `capacity_energy_inconsistent`, `utilisation_schedule_inconsistent`, `profile_energy_inconsistent` | Input disagreements surfaced by V12 and V14 |
| Aggregate **measured-emissions divergence** and the count of premises calibrated ([§7.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#76-reconciling-against-measured-emissions)) | Required by V13 |
| Count of **premise-connections** whose pathway exceeds capacity — negative `headroom` in any period (§8.5) | While the constraint is unenforced these pathways are not deliverable as costed. Counted per connection, since a site may breach one supply and not another |
| Total `reinforcement_required` across the run, in MW | The network investment the pathway implies but has not priced |
| Any validation test **deferred** rather than passed, with its reason ([§11.5](../2026-08-19-carb3-site-decarbonisation-implementation.md#115-tests-that-may-not-be-exercisable-in-their-phase)) | A deferred test must never read as a passed one |

**Rule.** Several sections promise that a condition is "reported" rather than corrected —
carrier coverage ([§3.1.1](../2026-08-19-carb3-site-decarbonisation-implementation.md#311-premise_energy-consumption-by-carrier)), emissions divergence ([§7.6](../2026-08-19-carb3-site-decarbonisation-implementation.md#76-reconciling-against-measured-emissions)), aggregate divergence (§A9),
utilisation disagreements (§A4). This table is where that promise is kept. A condition
detected and not surfaced here is a defect, not a silent success.

---
