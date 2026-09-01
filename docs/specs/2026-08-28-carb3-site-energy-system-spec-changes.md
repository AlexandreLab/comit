# CaRB3 Site Energy System — Spec Changes, Tests and Worked Example

**Status:** Draft v1 for review
**Date:** 2026-08-28
**Scope:** Great Britain · CaRB3 **Factory class** only (55 activities)
**Part of:** the v2 migration plan. What changes in the specification text.

**This plan is five documents.** Read the overview first; the other four are independent.

| Doc | For | |
|---|---|---|
| [Overview and decisions](2026-08-28-carb3-site-energy-system-overview.md) | everyone — start here |  |
| [Architecture](2026-08-28-carb3-site-energy-system-architecture.md) | modellers |  |
| [Spec changes and tests](2026-08-28-carb3-site-energy-system-spec-changes.md) | whoever writes the v2 spec | **you are here** |
| [Data migration](2026-08-28-carb3-site-energy-system-data-migration.md) | whoever owns the data tables |  |
| [Delivery](2026-08-28-carb3-site-energy-system-delivery.md) | whoever schedules the work |  |

> **This plans work; it does not specify it.** The v2 specification itself
> (`2026-08-28-carb3-site-energy-system-implementation.md`) does not exist yet — writing it is task T4.

---

## v2 spec content

### §3 Data model — entity changes

| v1 | v2 | Note |
|---|---|---|
| `commodity` | `carrier` | Gains `grade`, `grade_rank`, `is_gradeable`. `is_indirect` becomes config, closing §7.4's hardcoded-list debt. |
| `technology` | `unit` | Loses `fuel_category` (moves to carrier bindings). Gains `unit_class`, `min_viable_scale`, `grade_in`/`grade_out`, `is_storage`, `is_hybrid`. |
| `technology_input_output` | `unit_input_output` | **Sign convention unchanged.** |
| — | `unit_eligibility` | **New.** Where sector specificity lives. Carries the screening thresholds that replace the MILP binary. |
| — | `archetype_coefficient` | **New.** ψ, β, χ, ε — **one constant per coefficient per unit**, not a function of a design ratio, because a hybrid unit fixes the ratio. Carries D10 provenance. |
| — | `unit_bill_of_materials` | **New.** One row per hybrid unit per component, with the component's capacity share, capex share and lifetime. Lets §8's `Costs` and `Network` rows report per component, and is what makes the levelised bundle capex auditable. |
| `activity_process_energy_profile` | `process_duty` | Demand for a carrier at a grade. The vector-share allocation is replaced by the balance. |
| `premise_connection` | unchanged | Finally read. |

§3's prose count "Eighteen entities" (line 386) must be recomputed, not copied.

### §5 Constraint changes

| Label | v1 | v2 |
|---|---|---|
| C1 | `Σ_{k∈K_q} u = D_q` | Duty satisfaction over units eligible for the duty |
| C2–C5, C7 | over `k ∈ K` | over units; otherwise unchanged |
| C6 | two-legged stability | unchanged in form; σ recalibrates against unit deliverable output |
| **C8** | intermediates only | **every carrier**, with import/export terms |
| C9 | infrastructure availability | unchanged; extended to a `biomethane` carrier |
| **C10** | — | **New.** Heat-grade cascade: a unit may serve a duty only where `grade_out ≥ grade_duty` |
| **C11** | §5.6 Ext 1 (unbuilt) | **New.** Per-connection peak: `P_peak[c,t] ≤ P_import[c] + r[c,t] + β·b[c,t]` |
| **C12** | — | **New.** Siting cap: onsite generation ≤ available area × density |

Objective gains `Z^export = −Σ x[c,t]·p^export[c,t]`, a genuinely negative term. §5.4 must
say so explicitly — V6 already records the trap of assuming cost components are
non-negative.

**Non-degeneracy rule (Issue 5).** Load-scope assertion: `p^export[c,t] < p^import[c,t]`
strictly, per carrier per period. Tie-break key becomes lexicographic over
`(unit_id, carrier_id)`. §9.1's per-premise variable arithmetic is recomputed from the
unit, carrier-flow and storage families rather than carried over.

### §4 Algorithm changes

Five of the nine algorithms change. This table was missing from the first draft, and its
absence hid the deepest problem in the plan (A4, below).

| Algorithm | Change |
|---|---|
| A2 — expand to process set | Also resolves the **unit candidate set** via `unit_eligibility`, including the minimum-scale screening that replaces the MILP binary |
| A3 — allocate energy | **Largely removed.** The vector-share allocation is replaced by the carrier balance. What survives is the initial split of metered energy onto carriers, not onto processes |
| **A4 — back-solve** | **Rewritten. See below.** |
| A6 — build the problem | Declares variables over units and carrier flows rather than over `k ∈ K`; attaches ψ, β, χ, ε as parameters |
| A7 — solve and extract | Relaxation ladder gains rungs for C10, C11 and C12 |

#### A4 — the carrier-mix rule

**The problem.** In v1 the technology code pins the fuel, so
`energy → capacity` has one answer. Under a carrier model a unit may burn a mix, so the
same metered energy is consistent with many (capacity, mix) pairs. The back-solve is
under-determined. A4 is the most-referenced algorithm in the v1 spec at 47 citations, and
**V1b cannot run at all until this is closed** — there is no determinate v2 baseline to
compare against v1.

**The rule.** Pin the mix from evidence, in the D10 pattern already used everywhere else:

| Tier | Evidence | Mix |
|---|---|---|
| 1 — `site_known` | `premise_process_detail` names the unit and its carriers | Observed. Fully determined |
| 2 — `carrier_bounded` | `premise_energy` gives site totals per carrier, and the premise runs one unit on that carrier | Determined by division |
| 3 — `activity_default` | Neither | Activity-default mix, carried as an assumption with its tier on every output row |

Where several units share a carrier at tier 2, split by duty share and **record the split
as an assumption** rather than presenting it as measured. Every output row carries a
`mix_evidence_tier` (§8.1), so a premise running on an assumed mix is never mistaken on
paper for one running on an observed one.

#### A7 — where the new constraints sit in the ladder

The existing order is C6 → C7 → C4b → C9 → C1. The three new constraints slot in as
**C12 → C10 → C11**, ahead of C9:

- **C12 (siting cap) relaxes first.** It is the softest: an over-large PV array is an
  input-data problem about roof area, not a statement about the site's physics.
- **C10 (grade cascade) next**, and relaxing it must be loud — it means the model served a
  duty with heat that cannot physically reach that temperature. Report it, never silently
  absorb it.
- **C11 (connection capacity) last of the three**, because relaxing it asserts a
  reinforcement that nobody has costed, which is exactly the error §5.6 warns about for
  peak.

### §7 Emissions accounting changes

**This section was missing from the first draft**, on the strength of an unverified claim
that "§7's formulae keep working". The formulae do still evaluate — the sign convention is
unchanged — but *attribution* changes, and attribution is the part that matters.

| §7 part | Change |
|---|---|
| 7.1 two sources | Unchanged in form. Fuel CO₂ is charged to the unit that **consumes the fuel carrier**, not to the unit that consumes the heat it makes |
| 7.2 non-CO₂ | Unchanged. CCS still never abates non-CO₂ |
| 7.3 biomass zero-rating | Unchanged, and still applied **before** capture |
| 7.4 direct vs indirect | `is_indirect` moves from the hardcoded list at `R/fct_emissions.R:180-183` onto `carrier`, which this plan already required for other reasons |
| 7.5 categories | Re-derived over units. The seven overlapping categories survive; their membership does not |
| 7.6 reconciliation | Unchanged |

**The rule that stops double-counting.** Emissions attach to the unit that consumes a
**primary** carrier (gas, coal, biomass, grid electricity). A unit consuming an
**intermediate** carrier — heat at any grade, steam, recovered heat — adds nothing. Heat
is already paid for upstream, and charging it again at the point of use would double-count
every boiler in the stock.

**Recovered heat is emissions-free, and that is a real result rather than an accounting
trick.** A kiln's reject heat carries no fuel, so a heat pump drawing on it inherits no
emissions. The fuel that made it was already charged to the kiln. This is precisely why
`efficiency_heat_recovery` abates, and it only works if the rule above is stated rather
than assumed.

### §9 Performance changes

Beyond T7's recomputed per-premise arithmetic, **§9.2 gains a fourth gate**:

| Gate | Subject | Requirement |
|---|---|---|
| **G4** | Tier A archetype build | The full coefficient build completes within a stated wall-clock budget, measured **before the data build is commissioned** |

G1–G3 size the per-premise LP. Tier A is the new expensive thing — hourly dispatch per
archetype per hybrid sizing ratio, so a few hundred archetypes times ~12 hybrids is a few
thousand hourly optimisations, each far heavier than one annual LP. §9.2's own logic
applies: learning it is unaffordable in Phase 1 costs days, learning it in Phase 4 costs
the data build.

### §10 Test changes

| Test | Disposition |
|---|---|
| V1 | **Stays in v1 only.** Unchanged. |
| **V1b** | **New, Release, blocking.** v2 reproduces v1's objective and per-carrier energy on the same 1,026 sites, in the *carrier-equivalent configuration*: one carrier per unit, no storage, no onsite generation, C10/C11/C12 inactive. This configuration must be defined as precisely as §5.4 defines the pre-D11 baseline. |
| V2 | Reword: `capacity_to_activity_factor` and `io_coefficient` now per unit. 1e-6 stands. |
| V4 | R1 "technology consistency" becomes carrier consistency against `unit_input_output`. |
| V5 | Emissions invariants over units; the biomass-before-capture rule is unaffected. |
| V17 | Vintage per unit. The retrofit `ê` rule needs restating: CCS is a capture unit on a CO₂ carrier, not a `retrofit_to` sibling row. |
| **V18** | **New, Premise, blocking.** Carrier balance closes to 1e-6 at every carrier node, every period. |
| **V19** | **New, Load, blocking.** No unit is eligible for a duty above its `grade_out`. Asserted at load, not per premise. |
| **V20** | **New, Load, blocking.** Four legs. (a) ψ, β, χ ∈ [0,1] and ε > 0 for every unit. (b) Every hybrid unit's `unit_bill_of_materials` shares sum to 1 and reconcile to its capex and capacity. (c) Every hybrid unit's lifetime is levelised over its components — no component lifetime exceeds the unit's $L$ without a replacement charge in the annuity. (d) Every unit with `is_storage` and no hybrid parent has β set and ψ, χ, ε unset, since standalone storage may only earn through C11. **(e)** Across the hybrid units sharing a pairing, each coefficient is **concave in the sizing ratio** — this is what makes LP interpolation between them err on the safe side, and it is currently argued in prose and checked nowhere. Needs ≥3 ratios per pairing to be meaningful. |
| **V22** | **New, Premise, blocking.** Emissions attribution closes across a carrier chain. Three legs. (a) Total emissions equal the sum over units consuming **primary** carriers only — no unit consuming an intermediate carrier contributes. (b) A chain `gas → boiler → heat@150-400C → dryer` books exactly the boiler's fuel once. (c) A recovered-heat leg contributes zero, and the fuel that produced it remains charged to the rejecting unit. |
| **V23** | **New, Load + Premise, blocking.** A4's carrier mix resolves to exactly one tier per unit, tiers are tried in order, and `mix_evidence_tier` appears on every output row. Mirrors V11 for process sets. |
| **V21** | **New, Load, blocking.** The price-wedge non-degeneracy rule holds for every carrier and period. |

Adding V18–V23, C10–C12 and G4 requires the generator header edit from Issue 3 — the label
ranges `A1-A9 / C1-C9 / V1-V17 / D1-D11` are literals at
`build_interface_docs.py:168-169`.

### Test coverage diagram

```
  NEW CODEPATH                          GUARDED BY        SCOPE
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
  Tier A build cost                ───▶ G4 (new gate)     release
  export price wedge (Issue 5)     ───▶ V21               load
  connection peak (C11)            ───▶ V16 (exists)      batch
  siting cap (C12)                 ───▶ V20 + new V12 leg premise
  unit vintage / stranding         ───▶ V17 (reworded)    premise
  v2 ↔ v1 equivalence              ───▶ V1b               release
  v1 ↔ COMIT equivalence           ───▶ V1 (untouched)    release
  determinism under new tie-break  ───▶ V10 (key changes) release
```

---

## Failure modes

| # | Failure | Test? | Handling? | Visible? | Verdict |
|---|---|---|---|---|---|
| 1 | Carrier balance leaks (a unit produces a carrier nothing consumes and it silently vanishes) | V18 | assertion | yes | covered |
| 2 | A duty has no eligible unit after screening ⇒ infeasible premise | A7 ladder | ladder rungs C12 → C10 → C11 specified in §4 above | yes | covered |
| 3 | Hybrid unit capex not levelised over component lifetimes ⇒ C3's capacity window and C4's stranding charge both key on a wrong $L$ | V20 (c) | load assertion | yes | covered |
| 4 | Export price ≥ import price in a scenario ⇒ non-reproducible PV capacity | V21 | load assertion | yes | covered |
| 5 | Archetype assignment misses a premise (no matching cluster) | none | none | **no** | **CRITICAL GAP — needs a fallback tier + an evidence label** |
| 6 | Heat grade unset on a migrated process ⇒ C10 vacuous, heat pump fires a kiln | V19 | load assertion | yes | covered, provided grade is non-nullable |
| 7 | Option-to-unit join broken during data migration | validator | validator | yes | covered by Issue 4 |
| 8 | ε unset on a flexible-load hybrid ⇒ `electrolyser_battery` is strictly dominated by a bare electrolyser and is never built, so the hybrid-unit mechanism silently does nothing | V20 (a) | load assertion | yes | covered, **provided ε is non-nullable** |

**One critical gap (#5) must be closed in the spec, not deferred.** It takes the D10
shape: a declared fallback tier plus an evidence label on every output row, so a premise
running on a substituted archetype is never mistaken on paper for one running on a fitted
match.

Failure mode #3 was previously the more dangerous of two gaps — ψ extrapolated outside its
fitted design-ratio range — and it **no longer exists**. Hybrid units fix the sizing ratio,
so there is no continuous ratio to extrapolate along and no piecewise machinery to fall off
the end of. The remaining #3 is a bounded arithmetic error that a load assertion catches.
This is the main reason the hybrid-unit construction is worth its cost: it removes a whole
class of silent failure rather than adding tests to detect it.

---


## Worked example update

Same premise: `P-000123`, cement works, England, built 1957, 4.38 PJ/yr, 0.85 Mt clinker.
Keeping the site identical is what makes v1 and v2 comparable by eye.

Nine things break and must be rewritten:

1. `technology_code = kiln_dry_preheater_coal` (lines 94, 145, 222) is a literal
   (process × equipment × fuel) triple. Becomes a `calciner` unit with carrier bindings.
2. §5's *"there is no choice among candidate technologies"* argument (221–222) fails —
   supplying the unit no longer pins the fuel, so the back-solve is under-determined.
   **A4 needs a new rule for this**, and it is the deepest change in the example.
3. The candidate list (302–304: coal kiln, gas kiln, biomass/WDF kiln, coal+CCS) becomes
   one calciner unit with a carrier mix plus a CCS capture unit on the CO₂ carrier.
4. `|io| = 4.6 PJ/Mt` (line 223) is a single fuel-aggregated coefficient; becomes
   per-carrier, and the `2.0370 + 0.3007 + 1.5500 = 3.8877` collapse needs
   efficiency-weighting if carrier efficiencies differ.
5. "WDF assigned wholly to the kiln" (line 204) becomes a carrier routing, not a hand
   assignment.
6. §4's whole share-allocation table restructures — the balance replaces exogenous shares.
7. §10's hand-computed electrification arithmetic (398–409) becomes an endogenous result.
8. The retrofit story (329–335) restates: CCS inherits the host's 2043 life via the
   capture-unit relationship, not via `retrofit_to`.
9. §8's output grain "rows per process × technology × period" becomes per unit and per
   carrier.

**Additions the v1 example never had** (it claims A1–A9 but A6/A7 are prose only, A8 shows
no rows, and A9 is never walked): show the solved LP for at least one period, show real
output rows, and add a **PV + battery + connection-limit section** exercising C11, C12 and
the ψ/β coefficients. That section is the entire point of v2 and the example is where it
becomes legible.
