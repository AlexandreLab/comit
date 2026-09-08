# MVP feature prioritisation — MoSCoW categories and validation milestones

The CaRB3 site energy system is specified but not built, and the
[delivery document](../specs/2026-08-28-carb3-site-energy-system-delivery.md) sequences the
remaining specification and data work, not a software build. This note is the build view:
**every feature a minimum viable product (MVP) would need, sorted Must / Should / Could /
Won't, and the milestones at which each is verified.** It is written for whoever schedules the
build. What the MVP does and why, with worked examples and the definition of parity, is in
[17_mvp_what_it_does.md](17_mvp_what_it_does.md).

**Decisions this note rests on**, taken 2026-09-08: the build is in Python for everything,
nothing in `R/` is kept, and the R model is run once with its coupling switched off as a
**comparison point, not ground truth**. The stack is the one
[note 08](08_python_redesign_approach.md) recommends: linopy over HiGHS, xarray, pandera,
parquet. An engineering review of the first draft of this note, with an independent second
model as outside voice, produced nine decisions on the same day; they are folded in below and
listed under *Review decisions* at the end.

**Labels.** Constraint, algorithm, stage, test, gate, decision and task labels (`C`, `A`, `S`,
`V`, `G`, `D`, `PD`, `T`) are the ones the
[implementation specification](../specs/2026-08-28-carb3-site-energy-system-implementation.md)
§1.4 and the delivery document define. Data-migration items (`A1`, `B5`, `C2`, `D1`) are the
[data-migration document's](../specs/2026-08-28-carb3-site-energy-system-data-migration.md)
own group letters and are always written after the word "migration" here to keep them apart
from the constraint and decision families. Two families are local to this note and used
nowhere else: **`MF-nn`** for a feature row in the table below, and **`M0`–`M6`** for a
milestone.

---

## What the MVP is

The smallest build that, in order:

1. **Reproduces the R run's comparison point** in the carrier-equivalent configuration
   (§10.2) on the same 1,026 sites, passing V1b within stated tolerances, with the
   oracle-free checks (analytical fixtures, constraint-row satisfaction, metamorphic
   relations, base-year reconciliation) already green; and then
2. **Demonstrates the mechanism the model exists for**, duty ↔ carrier balance ↔ unit with
   graded heat, an existing CHP made visible, and onsite generation, on the food and drink
   worked example (§13, T16), with every output row carrying its evidence tier.

Storage, and the offline Tier A dispatch layer that gives storage a value (PD1, PD2, S0), are
not in the MVP. The problem is a pure LP throughout (§5.2).

## How features were cut

| Category | Rule used here |
|---|---|
| **Must** | Without it, either V1b cannot be run, the mechanism demonstration cannot be shown, or a solve cannot be trusted. Also every piece of specification the build cannot start without. |
| **Should** | Decided in the specification (a `D` or `PD` label) and structurally cheap once the Must set exists, but the MVP proves its shape with a stub, a default evidence tier, or a report instead of a constraint. Lands in M6. |
| **Could** | The specification marks it later, deferred, optional, or gated on a measurement that has not been taken. |
| **Won't** | On the specification's own out-of-scope list (§2.3, the delivery document's "NOT in scope"), or a property of COMIT the design removes on purpose. |

---

## Feature table

Columns: feature · category · why it sits there · where the specification defines it · what it
depends on · what verifies it. "Verified by" names a test or gate label where one exists and a
manual check where the delivery document says the check is not automatable.

### Reference data

| ID | Feature | MoSCoW | Why here | Spec anchor | Depends on | Verified by |
|---|---|---|---|---|---|---|
| MF-01 | Taxonomy split: `technology_category` into carrier, unit type, abatement; resolve `Standard_FF` and `Dry kiln`; derive the 12 service families and 14 chemistry nodes | Must | Every later table keys on it | migration A1–A3, A5; architecture "Unit spine" | T8 | `make data-check`; lineage table with one disposition per source row (MF-03) |
| MF-02 | `carrier` table: 18 fuel carriers plus the graded heat carriers with cascade rank | Must | C8 and C10 have nothing to balance or cascade without it | §3.4; migration A4 | MF-01 | V4 at load |
| MF-03 | Unit collapse: 293 fuel-variant technologies into units plus carrier bindings; 57 non-fuel technologies preserved; `grade_in`/`grade_out` on every unit and heat duty; a **lineage table** giving every one of the 397 source rows exactly one disposition (collapsed into unit X with binding Y, preserved as unit Z, or dropped with reason) | Must | The unit set the LP chooses from, and the mapping V1b compares through | §3.5, §3.6; migration B1–B3 | MF-01, MF-02 | `make data-check`; lineage table sums to 397 with zero unassigned rows; declared unit and binding counts match; `grade_rank` non-null wherever gradeable; V19 |
| MF-04 | Duty family and heat grade per process, with the process-level CaRB3 ↔ COMIT crosswalk | Must | `process → duty → eligible units` is the chain the model walks and only the first link exists ([16](16_input_data_readiness.md)) | §3.3; T17 | MF-01 | `duty_share` sums to 1.00 ± 0.015; every row resolves to the register; `make data-check` |
| MF-05 | Option → unit join replacing the activity-level crosswalk | Must | Options and technologies do not join today | migration C2; T9 | MF-03 | 130 used options resolve; the 12 optionless processes stay 12 |
| MF-06 | `unit_eligibility` with `min_duty` screening thresholds | Must | Replaces the MILP binary; where sector specificity lives | §3.5.1; migration C8 | MF-03, MF-04 | V11; V19; A2 screening report |
| MF-07 | Heat-pump COP by grade lift, replacing the flat coefficients | Must | The 120 °C competition in T16 is meaningless with a flat COP | migration B4 | MF-02, MF-03 | V2 round-trip; T16 recomputes |
| MF-08 | Supply units PV and CHP as unit rows with signed input-output coefficients | Must | The mechanism demonstration needs generation in the balance | §3.5, §3.6; migration C5 | MF-03 | V4; V18 on the T16 premise |
| MF-09 | Available area per premise, Must tier: a footprint proxy from `premise_record.floorspace` times a per-activity usable-area ratio, tagged with its evidence tier | Must | Without an area C12 is unbounded and the LP builds infinite PV; a ratio alone cannot produce an area, so the proxy names its base | §3.1, §3.1.3; migration D1 | Per-activity ratio table (new, modelling team) | V12 (siting cap holds); every premise carries an area and a tier |
| MF-10 | Export price and per-carrier import/export tariff series | Must | The price wedge is the non-degeneracy rule | §3.8; migration D2 | — | V21 at load |
| MF-11 | Remaining supply units (electrolyser, AD, thermal store, battery) and the hybrid-unit set with bill of materials | Should | Needed for storage value, which is after the MVP | §3.5.2; migration C5–C7 | MF-08 | V20 (b), (c), (d) |
| MF-12 | Reject-heat coefficients on every heat-consuming unit | Should | Waste heat recovery is a headline capability but the LP runs without it | §3.6 `is_reject`; migration B5 | MF-03 | V22 (c) |
| MF-13 | Default installed-unit table per activity, so an existing CHP is visible | Must | A4 cannot infer a CHP from metered heat and electricity ([16](16_input_data_readiness.md)); M4 has to show an existing CHP, not only a new one | §3.16; T18 | MF-04, MF-06 | `default_share` sums to 1.00 ± 0.015; eligibility precondition; T16's existing-CHP row appears in the baseline |
| MF-14 | Site-composition archetype entity, giving `archetype_id` a referent | Should | Nothing defines the key today | §3.17, §9.2; T19 | — | Every `archetype_coefficient` row resolves |
| MF-15 | Archetype definitions and fitted ψ, β, χ, ε coefficient tables | Could | Produced by Tier A, which is gated on G4 | §3.17; migration D4 | MF-11, MF-14, MF-36 | V20 (a), (e) |
| MF-16 | Biomethane as an infrastructure carrier with regional availability and tariff | Could | Availability scenario refinement | §3.7; migration D3 | — | C9 report |
| MF-17 | Option library hygiene: `displaces` normalisation, `route_change` flag, exclusivity groups | Could | Reporting quality, not solve correctness | migration C1, C3, C4 | MF-05 | `make data-check` |
| MF-71 | Available area, Should tier: GIS building footprint per premise replacing the floorspace proxy | Should | Better data where it exists, on the D10 pattern | §3.1.3; migration D1 | MF-09 | Area evidence tier moves from `proxy` to `measured` on covered premises |

### Specification closure

| ID | Feature | MoSCoW | Why here | Spec anchor | Depends on | Verified by |
|---|---|---|---|---|---|---|
| MF-18 | Complete §5 so the core LP is closed: write §5.6 and §5.3.1; period-index the duty set; **give activity a duty index** so one unit cannot be credited against two duties and a high-grade unit can serve a low-grade duty through the cascade (C8 and C10 algebra); **make C12's area coefficient per unit** so a CHP is not roof-limited; assign each unit's import and export to a connection so C11 can be added later; state the relaxation ladder with slack variables, penalties, a maximum violation and a terminal failure state; give C4 and C6 their algebra | Must | Four verified defects plus three found in review; M4's cascade and CHP demonstration are not expressible until done | §5.1, §5.2, §5.3.1, §5.5, §5.6, §4.2; T23 | — | Every §5 citation resolves to a heading; every constraint is stated as mathematics; the T16 premise's cascade is expressible on paper; `make check` |
| MF-19 | Numbered pseudocode for A1–A9 and the `mix_evidence_tier` field in §8 | Must | The build follows it; V1b needs a determinate baseline | §4; T13 | MF-18 | V23 |
| MF-20 | §8 output schema, including every evidence-tier field | Must | S8 has no contract without it; the interface generator is switched off until it exists | §8; T6 remainder | MF-19 | `make docs-check` with `interfaces.enabled` flipped |
| MF-21 | §9.1 problem-size arithmetic | Must | G1–G3 budgets are stated against it | §9.1; T7 remainder | MF-18 | Manual recompute |
| MF-22 | Cement worked example rewritten for the live specification, **published as a fixture**: a parquet input record, the expected output tables, units, rounding and solver settings | Must | The parity site walked end to end, and M2's gate | §13; T10 | MF-18, MF-19 | Every asserted number recomputes by hand; the fixture loads through the package's schemas |
| MF-23 | Food and drink worked example, published as a fixture on the same pattern | Must | The MVP exit criterion | §13; T16 | MF-04, MF-08, MF-13, T17 | Its assertions hold in the built model |
| MF-24 | §6 constraint disposition, §11 phasing, §12 reference map | Should | Documentation the build reads but does not block on | §6, §11, §12 | — | `make docs-check` |
| MF-25 | Declared forward process switch entity and rules | Could | Blocked on MF-18 structurally, and deferred by review | T24, which adds two entities to §3 | MF-18 | A declared switch changes duty and import per the T24 test |

### Pipeline stages

| ID | Feature | MoSCoW | Why here | Spec anchor | Depends on | Verified by |
|---|---|---|---|---|---|---|
| MF-26 | S1 ingestion and validation with rejection reasons, cluster assignment, base-year read | Must | Entry point of every solve | §2.1, §3.1, A1 | MF-40 | V11; MF-72 rejection-code tests |
| MF-27 | S2 expansion to duties and candidate units with `min_duty` screening | Must | Produces `process_duty` and the unit set | §3.9, A2 | MF-04, MF-06 | V11; V19 |
| MF-28 | S3 carrier allocation of metered energy | Must | Base year only, never across processes | A3 | MF-26 | V18 |
| MF-29 | S4 back-solve of implied capacity and carrier mix with three-tier evidence; vintage at the fallback tier only; `known_capacity` switches the back-solve to utilisation | Must | Baseline the LP starts from | §4.1, A4 | MF-28, MF-13 | V23; MF-72 utilisation-branch test; base-year reconciliation (MF-59) |
| MF-30 | S5 scenario application: period and calendar definition, discount and interest rates, carbon price series, carrier emissions factors, prices and tariffs, infrastructure availability and caps | Must | Parameters into the problem; every series the objective reads | §3.7, §3.8, §5.3, A5 | MF-10 | V21; MF-72 missing-series and period-mismatch errors |
| MF-31 | S6 problem builder in linopy | Must | Builds §5 | §5, A6 | MF-18 | V18; V6; MF-61 |
| MF-32 | S7 solver driver with the relaxation ladder: slack variables and penalties per rung, every relaxation reported with its violation, a terminal failure state when C1 cannot be met | Must | Infeasibility is reported, never silent, and a relaxed solve is labelled as one | §4.2, A7 | MF-31 | MF-72 infeasible-premise test walks every rung |
| MF-33 | S8 output assembly with evidence tiers on every row | Must | The only product of a solve | §8, A8 | MF-20, MF-53 | V23 |
| MF-34 | S9 roll-up to GB totals | Must | The national picture is a sum | A9 | MF-33 | MF-73 sum-equals-parts test |
| MF-35 | Batch runner over premises, parallel, independent, tolerant of one worker failing | Must | D2 is what makes the stock run tractable | D2, §9.2 | MF-26–MF-33 | G2; MF-73 worker-failure test |
| MF-36 | S0 Tier A archetype dispatch, hourly, offline | Could | Gated on G4; the most expensive component | §2.1 S0, §9.2 G4; T15 | MF-11, MF-14 | G4; V20 (e) |
| MF-37 | S9 comparison against ECUK, the inventory, the emissions budget, and the committed coupled COMIT run as a bounded aggregate sanity check | Should | Reporting, not solve correctness; the coupled run is never a parity target | §2.3, A9 | MF-34 | Report present; budget never a constraint |
| MF-75 | Block-diagonal batching experiment: several premises built as one separable LP per chunk to amortise model-construction overhead | Could | D2 independence allows it; decided by measurement at G2 | §9.2 G2 | MF-35 | G2 slope with and without batching |

### Optimisation model

| ID | Feature | MoSCoW | Why here | Spec anchor | Depends on | Verified by |
|---|---|---|---|---|---|---|
| MF-38 | C1 duty satisfaction, C2 capacity, C3 capacity transfer, C5 no build in the start year | Must | The comparison point's problem | §5.5 | MF-31 | V12; V1b |
| MF-39 | C8 carrier balance at every carrier node, every period, with the duty-indexed activity from MF-18 | Must | "The core change" | §5.5 C8 | MF-02, MF-18 | V18 |
| MF-40 | C9 infrastructure availability, including caps | Must | Exogenous scenario enters here | §5.5 C9; D7 | MF-30 | C9 report |
| MF-41 | C10 heat grade cascade, enforced by eligibility at load and expressible in the balance | Must | The mechanism demonstration | §5.5 C10 | MF-03, MF-18 | V19; the T16 heat pump serves hot water and not drying |
| MF-42 | C12 siting cap on area-bound units only, per-unit area coefficient | Must | Without it PV is unbounded; with one coefficient a CHP is roof-limited | §5.5 C12 | MF-09, MF-18 | V12 |
| MF-43 | C4 at the fallback tier only: incumbent decay by the uniform survival function, no stranding | Must | Reproduces COMIT's linear decay, which V1b needs | §5.3, C4; D11 | MF-18 | V1b |
| MF-44 | Objective terms capex, opex, fuel, carbon, infrastructure, export; annuitised capex; carbon unit conversion | Must | §5.4 as stated, export present even where zero | §5.4 | MF-31 | V6 |
| MF-45 | Price wedge and lexicographic tie-break | Must | Removes most degeneracy | §5.5, §9.3 | MF-10 | V21 |
| MF-74 | Determinism made real: the tie-break encoded as a second-objective solve over the optimal face, or a bounded perturbation shown not to move the primary optimum; HiGHS version, presolve, thread count and options pinned in the package | Must | A price wedge plus a sort key does not by itself make two runs agree | §9.3 | MF-45 | V10 on two machines |
| MF-46 | C4 in full: cohort vintage tiers, stranding charge, early-retirement variable | Should | Decided (D11), structurally cheap once C4 has algebra | §3.15, §5.3, C4 | MF-18, MF-43 | V17 |
| MF-47 | C11 connection capacity per connection, the §5.6 peak rebuild, the reinforcement variable and its cost term | Should | Reads a field the MVP only collects; the connection assignment it needs is in MF-18 | §5.5 C11; §5.6 once MF-18 writes it | MF-18 | V16 |
| MF-48 | Hybrid units on `evidence_tier = default` coefficients | Should | Exercises the hybrid mechanism before Tier A exists | §3.17; PD2 | MF-11 | V20 (b), (c), (d) |
| MF-49 | D12 in full: base-year substitution ladder, history isolation, process validity intervals | Should | Contract already requires it; cheap once A1 exists | §3.1.1, §3.10; D12 | MF-26 | V24; V25; V26 |
| MF-50 | Standalone storage valued through β only | Could | Needs β from Tier A | §3.17, C11 | MF-15, MF-47 | V20 (d) |
| MF-51 | C6 unit stability and C7 known changes | Could | Deferred by the temporal-coverage review | §5.5 C6, C7 | MF-18 | Relaxation ladder rungs |

### Emissions and outputs

| ID | Feature | MoSCoW | Why here | Spec anchor | Depends on | Verified by |
|---|---|---|---|---|---|---|
| MF-52 | §7 rules 7.1–7.5: fuel charged to the consuming unit, process CO₂ to the chemistry unit, non-CO₂ tracked separately, biomass zero-rated before capture, direct/indirect by carrier | Must | Attribution is what changes under carriers; needed by M2's V22 | §7 | MF-39 | V5; V22 (a), (b) |
| MF-53 | Evidence tiers on every output row: process set, carrier mix, archetype, area, year | Must | D10's cost: "or the quality is invisible"; S8 has no rows without it | D10; §8 | MF-20 | V23 |
| MF-54 | §7.6 reconciliation against measured emissions at the base year, reported | Should | Calibration report; the base-year check in MF-59 is the Must form | §3.11, §7.6 | MF-49 | `emissions_year_unmatched` reported |

### Validation tooling

| ID | Feature | MoSCoW | Why here | Spec anchor | Depends on | Verified by |
|---|---|---|---|---|---|---|
| MF-55 | Load-scope tests V2, V4, V11, V19, V21; V20 (a) runs once any archetype row exists and is reported as not-run until then | Must | Run once when reference data is read; a vacuous pass is reported as such | §10.1, §10.3 | MF-01–MF-10 | Themselves |
| MF-56 | Premise-scope tests V5, V6, V12, V18, V22 (a) (b), V23 | Must | Run on every solve | §10.3 | MF-31, MF-52, MF-53 | Themselves |
| MF-57 | One R run with coupling switched off; its tables frozen as parquet with a manifest carrying the workbook hash, the R package commit, the solver version and the switches used | Must | The comparison point. Not ground truth, not kept runnable | §1.1; [08 §1](08_python_redesign_approach.md); [17](17_mvp_what_it_does.md) "Parity, defined" | COMIT solving with its coupling constraint functions switched off | Tables and manifest committed; coupled-off run is bounded and optimal |
| MF-58 | V1b comparison on the 1,026 sites through the MF-03 lineage table: objective per site within 0.5 percent, energy per carrier per period within 1 percent, binding set not compared; every site outside tolerance listed with a reason | Must | The MVP's first exit | §10.2, §10.3 | MF-57, MF-35, MF-03 | V1b report |
| MF-59 | Oracle-free correctness set, all Must in M2: analytical fixtures (the linopy proof-of-concept's 1425 objective plus one with a carrier balance, a graded duty and an export); post-solve constraint-row satisfaction from the built matrix; metamorphic relations (cost scaling, carbon-price monotonicity, dominant unit built wherever eligible); base-year reconciliation of back-solved energy and emissions against the premise record | Must | What decides who is wrong when the MVP and the R run disagree ([07 §2, §4, §5](07_high_level_testing_strategy.md)) | §7.6; note 07 | MF-31 | Each check is its own test |
| MF-60 | Scale gates G1, G2, G3 with placeholder budgets confirmed at M0: G1 under 10 seconds per premise; G2 batch time within 1.2 times linear from 10 to 1,000 premises; G3 the M5 sample under 2 hours; all on a named 4-core machine, HiGHS single-threaded, 3 repetitions, cold cache, versions pinned | Must | A gate without a number cannot fail | §9.2 | MF-21, MF-35 | Themselves, recorded with the machine and settings |
| MF-61 | Table snapshots of the fixture outputs, rounded, as the regression net | Should | Cheap once fixtures exist ([07 §3](07_high_level_testing_strategy.md)) | — | MF-22, MF-23 | Themselves |
| MF-62 | Tests attached to Should features: V16, V17, V20 (b)–(d), V22 (c), V24–V26 | Should | Land with their features | §10.3 | MF-46–MF-49, MF-12 | Themselves |
| MF-63 | G4 and V20 (e) concavity | Could | Decide whether Tier A is affordable | §9.2 G4; T15 | MF-36 | Themselves |
| MF-64 | Property-based harness with Hypothesis on the fast layers and the analytical fixtures | Could | Many fast executions ([07 §6](07_high_level_testing_strategy.md)) | — | MF-59 | Themselves |
| MF-72 | Behavioural unit tests: one per S1 rejection code; the `known_capacity` utilisation branch of A4; a deliberately infeasible premise walking every relaxation rung and ending in the terminal state; missing-series and period-mismatch errors in S5 | Must | Every branch the pipeline can take is exercised | §3.1, §4.1, §4.2 | MF-26, MF-29, MF-30, MF-32 | Themselves |
| MF-73 | Input, output and operations tests: pandera negative tests on malformed rows; parquet round-trip; S9 roll-up equals the sum of premise rows; CLI smoke test; one worker failing mid-batch leaves the batch reported, not silent | Must | The paths a user hits first | — | MF-34, MF-35, MF-66, MF-67 | Themselves |

### Project scaffolding

| ID | Feature | MoSCoW | Why here | Spec anchor | Depends on | Verified by |
|---|---|---|---|---|---|---|
| MF-65 | Python package with `pyproject.toml`: linopy, highspy, xarray, pandera, pyarrow; solver options pinned | Must | There is no dependency manifest today and `pandas` is not installed | [08 §3](08_python_redesign_approach.md) | — | Fresh-environment install |
| MF-66 | Canonical inputs and outputs as parquet with pandera schemas; Excel as one import adapter for the reference workbook | Must | Comparison tables, fixtures and premise records travel in it | [08 §3](08_python_redesign_approach.md) | MF-65 | Schema validation on load; MF-73 |
| MF-67 | Command-line entry points: one premise, a batch | Must | How every milestone is exercised | — | MF-35 | MF-73 smoke test |
| MF-68 | `make check` extended to run the package's test suite | Must | The single gate a hook would call | CLAUDE.md "Hook candidates" | MF-65 | `make check` green |
| MF-69 | CI wiring beyond the Makefile | Won't | Delivery document: "a separate call" | delivery "NOT in scope" | — | — |
| MF-70 | A user interface | Won't | Not ported; a thin front end later if needed | [08 §3](08_python_redesign_approach.md) | — | — |

### Won't, from the specification's own boundaries

Not features to schedule, listed so nobody re-opens them by accident.

- Deriving a premise's baseline energy (D4); deciding infrastructure build-out (D7); enforcing
  a national emissions budget; Northern Ireland (D8); any hourly temporal-correlation
  compliance claim such as RFNBO or LCHS (§2.3).
- Non-Factory premises (D1); inter-premise or virtual-power-plant coupling (D2, §1.5).
- Any binary or fixed-charge variable in the per-premise problem (§5.2).
- Full 8,760-hour dispatch inside the per-premise LP; seasonal inter-period storage state;
  rewriting anything under `docs/specs/archive/`; retiring the parity baseline specification
  (delivery "NOT in scope").
- Building the archived baseline specification as software. V1 as the specification writes it
  presumed that build; it is replaced by the R run of MF-57.
- Life extension through major refurbishment; `last_refurbishment_year` stays collected and
  unread (§3.1, §3.15).
- Any change to `R/` other than the one comparison run.

---

## Milestones

Each milestone has an entry condition, a scope in feature IDs, an exit gate, and the exact
verification. M4 is the MVP exit. The order matters in the same way the delivery document's
verification order matters: a green gate on the milestone before is what makes a red at this
one attributable.

### M0 — Specification closed for build

- **Entry:** now. `make check` green on `fork/main`.
- **Scope:** MF-18, MF-19, MF-20, MF-21, MF-22 (specification and the cement fixture);
  MF-57 (the R comparison run, which needs no Python); MF-65, MF-66 (package skeleton and
  parquet schemas, so the comparison tables and the fixture have somewhere to live); the
  placeholder numbers in MF-58 and MF-60 confirmed or replaced.
- **Exit gate:** every citation of §5.3.1 and §5.6 resolves to a heading; activity carries a
  duty index and the T16 cascade is expressible on paper; every constraint is stated as
  mathematics; §8 exists and the interface generator is switched on for the live
  specification; the comparison tables are committed with their manifest; the cement fixture
  loads through the package schemas.
- **Verification:** `make check` and `make docs-check`; `grep` for `§5.6` and `§5.3.1` shows
  only resolving references; the manifest's hashes match the committed inputs; the cement
  example's numbers recompute by hand.
- **Risk retired here:** whether COMIT solves with its coupling constraint functions switched
  off through `constraints_to_include`. If it does not, V1b has no comparison point and the
  oracle-free set of MF-59 becomes the whole of M3's gate.

### M1 — Reference data foundation

- **Entry:** M0 exit.
- **Scope:** MF-01 to MF-10; MF-55 (load-scope tests).
- **Exit gate:** `make data-check` green; the lineage table assigns all 397 source rows
  exactly one disposition and its unit and binding counts match the declared ones; every
  gradeable duty carries a `grade_rank`; the option join resolves all 130 used options and
  leaves exactly 12 optionless processes; every premise in the fixtures carries an area and
  its tier; V4, V11, V19, V21 pass at load and V20 (a) is reported as not-run.
- **Verification:** `make data-check`; the package's load-scope test target; the lineage table
  committed beside the collapsed unit file.

### M2 — Walking skeleton, trusted solve

- **Entry:** M1 exit.
- **Scope:** MF-26 to MF-34 for a single premise; MF-38, MF-39, MF-40, MF-43, MF-44, MF-45,
  MF-74; MF-52, MF-53; MF-56, MF-59, MF-72, MF-73; MF-67; MF-68.
- **Exit gate:** the cement fixture from MF-22 runs through S1–S8 in the carrier-equivalent
  configuration and its objective and per-carrier energy match the fixture's expected tables
  within the MF-58 tolerances; V2, V6, V12, V18, V22 (a) (b), V23 pass; every MF-59 check is
  green, including the post-solve constraint-row check and the analytical fixtures; every
  MF-72 and MF-73 test passes; V10 passes on two machines; G1 is measured and recorded with
  its settings.
- **Verification:** `make check`; the premise command-line entry point on the cement fixture;
  the fixtures' expected values in the test files.

### M3 — Comparison with the R run

- **Entry:** M2 exit.
- **Scope:** MF-35, MF-58, MF-60 (G2), MF-75 if G2 needs it.
- **Exit gate:** V1b on the 1,026 sites within the MF-58 tolerances, compared through the
  MF-03 lineage table; every site outside tolerance listed with a reason, and each reason
  traced to either the MVP or the R run by the MF-59 checks; G2 within 1.2 times linear from
  10 to 1,000 premises.
- **Verification:** the release-scope test target; the comparison report committed with the
  run.
- **After this gate** the R tables stay as the comparison point. The R model is not rerun and
  is not ground truth: a divergence found later is investigated with the MF-59 checks, and a
  confirmed COMIT defect is recorded against the comparison tables rather than fixed in R.

### M4 — MVP exit: the mechanism demonstration

- **Entry:** M3 exit.
- **Scope:** MF-08, MF-09, MF-13, MF-23, MF-41, MF-42.
- **Exit gate:** on the food and drink fixture, eight fuel-variant rows collapse to three
  units; a 120 °C duty has boiler, CHP, heat pump and electric resistance competing under C10
  and the heat pump is absent from the drying duty's candidate set; the premise's existing
  CHP from the default installed-unit table appears in the baseline with its electricity
  co-product; the CHP produces heat and electricity into the balance and surplus electricity
  exports below the import price; PV is bounded by the floorspace-proxy area and the CHP is
  not; V19, V21, V22 (a) (b), V23 pass; every output row carries its evidence tiers.
- **Verification:** the premise entry point on the T16 fixture; the fixture's expected
  tables against the solver's; the release-scope target. The reject-heat leg of T16 is
  **not** asserted here; it belongs to MF-12 in M6.

### M5 — Sample stock run

- **Entry:** M4 exit.
- **Scope:** MF-35 on a sample; MF-34; MF-37; MF-60 (G3).
- **Sample, not stock.** The readiness audit says premise energy, throughput, connections and
  area for the full Factory-class stock do not exist yet. M5 runs on the 1,026 comparison
  sites, with connections and area synthesised from the fallback tiers and tagged as such,
  plus a contract test on the upstream stock-model record so the full run can start the day
  the data lands. The full Factory-class run is the first milestone of the next plan.
- **Exit gate:** the sample batch completes within the G3 budget; the roll-up totals equal
  the sum of premise rows; the comparison against ECUK, the inventory, the budget and the
  committed coupled COMIT run is reported as bounded aggregate differences; every relaxation
  the ladder applied is listed with its premise, rung and violation; the upstream contract
  test passes on a synthetic record.
- **Verification:** the batch entry point; the roll-up report; a relaxation summary with
  counts per rung.

### M6 — Should-haves

- **Entry:** M5 exit. Items are independent of each other and can land in any order.
- **Scope:** MF-11, MF-12, MF-14, MF-24, MF-46, MF-47, MF-48, MF-49, MF-54, MF-61, MF-62,
  MF-71.
- **Exit gate per item:** its named test passes and `make check` stays green.
- **Decision taken at the end of M6:** measure G4 on a handful of archetypes and hybrid
  pairings. If the Tier A build fits the budget, MF-15, MF-36, MF-50 and MF-63 move from Could
  to the next plan; if it does not, hybrid units stay on default-tier coefficients and that
  choice is written into the specification.

---

## Assumptions and open calls

- **Language and solver are settled**: Python, linopy, HiGHS. The specification stays
  language-agnostic; this note and the package are where the choice lives.
- **The R model is a comparison point, not ground truth.** One run, tables and manifest
  committed, never rerun. When the two disagree the MF-59 checks decide which is wrong.
- **COMIT must solve with its coupling switched off.** The `constraints_to_include` sheet is
  read by `R/fct_combining_constraints.R` and lists the constraint functions to build, so the
  switch exists; whether the uncoupled problem is bounded and sensible is checked at M0.
- **The area proxy** needs a per-activity usable-area ratio table that nobody owns yet. It is
  a modelling-team input on the D10 pattern, and the GIS footprint (MF-71) replaces it where
  available.
- **The A4 technology-split prior** for premises with no process detail is still an equal
  split. It sets the back-solved baseline for most of the stock and is worth a decision before
  M3, where it will show up in the comparison report.
- **Which infrastructure scenarios to run** at M5. Two bounding scenarios are enough; their
  content is a modelling call, not a build call.
- **Gate numbers are placeholders** until M0 confirms them: 0.5 and 1 percent for V1b; 10
  seconds, 1.2 times linear and 2 hours for G1–G3.
- **Tier A affordability** decides M6's ending, and is measured rather than assumed.

## Review decisions

Taken on 2026-09-08 after an engineering review of the first draft, with an independent model
as outside voice. Recorded so the reasoning is not lost.

| # | Decision |
|---|---|
| 1 | M3 verifies by one comparison against a coupled-off R run, not a two-hop chain; the oracle-free checks (MF-59) are Must in M2 and decide disagreements |
| 2 | MF-18 grows to close the LP: duty-indexed activity, cascade algebra, per-unit C12 coefficient, connection assignment, a real relaxation ladder |
| 3 | Every gate carries a number now, as a placeholder confirmed at M0 |
| 4 | The R run is a comparison point, not ground truth: tables and manifest, no container, never rerun |
| 5 | Emissions attribution and evidence tiers move into M2, where V22 and S8 need them |
| 6 | The default installed-unit table is Must, so M4 shows an existing CHP and not only a new one |
| 7 | The area fallback names its base: floorspace times a per-activity ratio is Must, GIS is Should |
| 8 | Nine untested pipeline paths get Must tests (MF-72, MF-73, MF-74) |
| 9 | M5 runs a sample, the 1,026 comparison sites, with synthesised connections and area; the full stock run moves to the next plan |

## Cross-check — inconsistencies met while writing

Recorded so they are fixed at source rather than copied forward.

- The overview and CLAUDE.md say the design decisions are `D1`–`D11`; the implementation
  specification §1.4 and §1.6 and the notes index say `D1`–`D12`. D12 is real and load-bearing.
- CLAUDE.md says the delivery document has 18 tasks; the notes index says twenty-three; the
  file has 23 checkbox entries spanning T1–T24 with T11 and T12 combined.
- CLAUDE.md's label table says `V1`–`V23`; the specification declares `V1`–`V26`.
- The overview cites `E2` as an example of the data-migration numbering; Group E has one item.
- The delivery document's task list runs T1–T10, T16–T19, T11–T15, T20–T24 with no headings at
  the jumps.
- **Specification defects surfaced by the review**, to be closed by T23 (MF-18): activity has
  no duty index (§5.2), so one unit is credited against every duty it is eligible for and the
  cascade cannot be expressed in C8; C12 (§5.5) sums every generator against one area density,
  so a CHP is roof-limited; V1 (§1.1, §10.3) presumes the archived baseline is built, which
  the Python decision rules out, so §10.2 should name the R run as the comparison point and
  the lineage table as the mapping.

## Sources

- Implementation specification §1.1–§1.6, §2, §3, §4, §5, §7, §9, §10, §13.
- Delivery document: tasks T1–T24, lanes, "NOT in scope", verification order.
- Data-migration document: groups A–E.
- Notes [07](07_high_level_testing_strategy.md), [08](08_python_redesign_approach.md),
  [16](16_input_data_readiness.md).
- `R/fct_combining_constraints.R` for the `constraints_to_include` switch.
