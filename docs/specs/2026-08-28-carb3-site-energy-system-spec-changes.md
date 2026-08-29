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
| `technology` | `unit` | Loses `fuel_category` (moves to carrier bindings). Gains `unit_class`, `min_viable_scale`, `grade_in`/`grade_out`, `is_storage`. |
| `technology_input_output` | `unit_input_output` | **Sign convention unchanged.** |
| — | `unit_eligibility` | **New.** Where sector specificity lives. Carries the screening thresholds that replace the MILP binary. |
| — | `archetype_coefficient` | **New.** ψ, β, χ as piecewise segments against design ratio, with D10 provenance. |
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
| **V20** | **New, Load, blocking.** ψ, β, χ ∈ [0,1]; piecewise segments are monotone and continuous at breakpoints. |
| **V21** | **New, Load, blocking.** The price-wedge non-degeneracy rule holds for every carrier and period. |

Adding V18–V21 and C10–C12 requires the generator header edit from Issue 3 — the label
ranges `A1-A9 / C1-C9 / V1-V17 / D1-D11` are literals at
`build_interface_docs.py:168-169`.

### Test coverage diagram

```
  NEW CODEPATH                          GUARDED BY        SCOPE
  ─────────────────────────────────────────────────────────────────
  carrier balance closure          ───▶ V18               premise
  heat grade cascade (C10)         ───▶ V19               load
  archetype coefficients ψ/β/χ     ───▶ V20               load
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
| 2 | A duty has no eligible unit after screening ⇒ infeasible premise | A7 ladder | relaxation ladder needs a new rung for C10/C12 | yes | **needs a ladder entry** |
| 3 | ψ interpolated outside its fitted design-ratio range | V20 bounds only | none | **no** | **CRITICAL GAP — clamp and flag required** |
| 4 | Export price ≥ import price in a scenario ⇒ non-reproducible PV capacity | V21 | load assertion | yes | covered |
| 5 | Archetype assignment misses a premise (no matching cluster) | none | none | **no** | **CRITICAL GAP — needs a fallback tier + an evidence label** |
| 6 | Heat grade unset on a migrated process ⇒ C10 vacuous, heat pump fires a kiln | V19 | load assertion | yes | covered, provided grade is non-nullable |
| 7 | Option-to-unit join broken during data migration | validator | validator | yes | covered by Issue 4 |

Two critical gaps (#3, #5) must be closed in the spec, not deferred. Both take the same
shape as D10: a declared fallback tier plus an evidence label on every output row, so a
premise running on an extrapolated coefficient is never mistaken on paper for one running
on a fitted archetype.

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
