# CaRB3 Site Energy System — Delivery

**Status:** Draft v1 for review
**Date:** 2026-08-28
**Scope:** Great Britain · CaRB3 **Factory class** only (55 activities)
**Part of:** the v2 migration plan. Files, tasks, sequencing, scope boundary and verification.

**This plan is five documents.** Read the overview first; the other four are independent.

| Doc | For | |
|---|---|---|
| [Overview and decisions](2026-08-28-carb3-site-energy-system-overview.md) | everyone — start here |  |
| [Architecture](2026-08-28-carb3-site-energy-system-architecture.md) | modellers |  |
| [Spec changes and tests](2026-08-28-carb3-site-energy-system-spec-changes.md) | whoever writes the v2 spec |  |
| [Data migration](2026-08-28-carb3-site-energy-system-data-migration.md) | whoever owns the data tables |  |
| [Delivery](2026-08-28-carb3-site-energy-system-delivery.md) | whoever schedules the work | **you are here** |

> **This plans work; it does not specify it.** The v2 specification itself
> (`2026-08-28-carb3-site-energy-system-implementation.md`) does not exist yet — writing it is task T4.

---

## Files

### Create

| Path | What |
|---|---|
| `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md` | The v2 spec |
| `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-cement.md` | v2 worked example, cement works — proves parity with v1 (T10) |
| `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-food-drink.md` | v2 worked example, food & drink — proves the carrier mechanism (T16) |
| `docs/notes/examples/validate_carb3_data.py` | Stdlib-only validator (Issue 4) |
| `docs/notes/examples/spec_docs.config.json` | Section anchors, own-prefix, label ranges (Issue 3) |
| `Makefile` | `make docs-check` / `make data-check` |

### Modify

| Path | Change |
|---|---|
| `docs/notes/examples/build_interface_docs.py` | Read config not literals; fix the `](interfaces/…)` dead link; add v2 targets |
| `docs/notes/examples/build_spec_flow_diagram.py` | Add `--check`; parameterise the `3\.[\d.]+` entity regex and the hardcoded entity-name lists (41–59) |
| `docs/specs/2026-08-19-carb3-site-decarbonisation-vision.md` | §3 reuse claim; D3/D6/D11 rows; §4.2 variable arithmetic; §9 phasing; **and the λ→ξ bug at lines 146 and 240** |
| `docs/notes/README.md` | Register v2 spec, v2 worked example, v2 interface docs |
| `docs/specs/2026-08-19-carb3-site-decarbonisation-implementation.md` | Header note only: "v1, frozen. Superseded for architecture by v2; retained as the COMIT-parity baseline (V1)." |

### Do not touch

`docs/specs/2026-08-05-site-heterogeneity-prd.md` — already superseded, R-file-specific,
formally retired. Its banner stays accurate.

---


## Parallelisation

| Lane | Modules | Depends on |
|---|---|---|
| L1 — Tooling | `docs/notes/examples/`, `Makefile` | — |
| L2 — v2 spec §1–§5 | `docs/specs/` v2 | Issue 2 spine (settled) |
| L3 — Data taxonomy | `docs/notes/data/` Groups A, B | L1 (validator baseline) |
| L4 — Decarb options | `docs/notes/data/` Group C | L3 A1–A5 |
| L5 — v2 spec §6–§13 + example | `docs/specs/` v2 | L2 |
| L6 — Vision + index edits | vision, READMEs | L2 |

**L1 and L2 start in parallel immediately.** L3 waits on L1's green baseline. L4 waits on
L3's taxonomy split. L5 waits on L2. L6 last, so it describes what was actually built.

---

## Implementation Tasks

- [ ] **T1 (P1, human: ~1 day / CC: ~30min)** — tooling — Write the stdlib-only data validator and establish a green baseline
  - Surfaced by: Issue 4 — no generator and no validator exists for the seven Family-B files
  - Files: `docs/notes/examples/validate_carb3_data.py`, `Makefile`
  - Verify: `make data-check` green on unmodified `docs/notes/data/`
- [ ] **T2 (P1, human: ~1 day / CC: ~25min)** — tooling — Parameterise both spec generators, add `--check` to the diagram builder
  - Surfaced by: Issue 3 — `build_interface_docs.py:38-39,58-59,168-169` hardcodes headings, own-prefix and label ranges
  - Files: `build_interface_docs.py`, `build_spec_flow_diagram.py`, `spec_docs.config.json`, `Makefile`
  - Verify: `make docs-check` reproduces today's v1 interface docs byte-identically
- [ ] **T3 (P2, human: ~30min / CC: ~5min)** — tooling — Fix the live `](interfaces/…)` dead link in both generated files
  - Surfaced by: verified — spec lines 380 and 2306 sit inside both extracted ranges and `fix_relative_paths` does not depth-adjust them
  - Files: `build_interface_docs.py:136-140`
  - Verify: link resolves from `docs/specs/interfaces/`
- [ ] **T4 (P1, human: ~2 days / CC: ~60min)** — spec — Write v2 §1–§5 (carrier network, graded heat, units, two-tier temporal)
  - Surfaced by: PD1 + PD2 + Issue 2
  - Files: `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md`
  - Verify: `make docs-check`; diagrams regenerate
- [ ] **T5 (P1, human: ~4h / CC: ~20min)** — spec — Define V1b and the carrier-equivalent configuration
  - Surfaced by: Issue 1 — V1 step 4 compares per-technology capacity, which does not exist in v2
  - Files: v2 spec §10
  - Verify: the configuration is stated as precisely as §5.4's three-condition pre-D11 baseline
- [ ] **T6 (P1, human: ~3h / CC: ~15min)** — spec — Close failure mode #5 with a fallback tier and an evidence label
  - Surfaced by: Failure modes table — a premise matching no archetype fails silently, untested and unhandled
  - Files: v2 spec §3 (`archetype_coefficient`), §8.1 (evidence fields)
  - Verify: every output row carries an archetype evidence tier
  - Note: this was two gaps. The other, ψ extrapolated outside its fitted design-ratio range, was **removed** by the hybrid-unit decision (PD3) rather than tested for — a fixed sizing ratio leaves nothing to extrapolate along
- [ ] **T7 (P1, human: ~4h / CC: ~20min)** — spec — New tie-break key, price-wedge rule, recomputed §9.1 arithmetic
  - Surfaced by: Issue 5 — §9.3's tie-break is `technology_code`, which v2 does not have
  - Files: v2 spec §9, §10 (V21)
  - Verify: V21 stated at load scope
- [ ] **T8 (P1, human: ~2 days / CC: ~45min)** — data — Group A + B taxonomy split and collapse
  - Surfaced by: Issue 2 — `technology_category` conflates carrier, device and abatement across 397 rows
  - Files: `docs/notes/data/emissions_source_classification.csv` and successors
  - Verify: `make data-check`; explicit 397-row reconciliation, zero orphans
- [ ] **T9 (P1, human: ~2 days / CC: ~45min)** — data — Group C decarbonisation options: the missing option→unit join, plus the hybrid-unit set and its bill of materials
  - Surfaced by: Agent inventory — options keyed to CaRB3 `process_id`, technologies keyed to `output_commodity`, no join exists. PD3 adds hybrid units, which have no representation in a library where all 134 options are demand-side
  - Files: `decarbonisation_options_library.csv`, `process_decarbonisation_options.csv`, new `unit_bill_of_materials`
  - Verify: `make data-check`; 130 used options all resolve; the 12 legitimately optionless processes stay exactly 12; every hybrid unit's BOM shares sum to 1 and reconcile to its capex (V20 b)
- [ ] **T10 (P1, human: ~1 day / CC: ~30min)** — spec — Rewrite the **cement** worked example, adding the PV/battery/connection section
  - Surfaced by: Nine structural breaks identified in the v1 example
  - Files: `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-cement.md`
  - Verify: every asserted number recomputes; A6–A9 actually walked
  - Scope: this example proves v2 did not break what v1 got right — mass denominator (D5), tier-1 vintage, stranding, CCS retrofit. It **cannot** show graded heat, unit competition or CHP; that is T16
- [ ] **T16 (P1, human: ~1 day / CC: ~30min)** — spec — Write a second worked example on a **food & drink** site, exercising the carrier mechanism
  - Surfaced by: Review issue 9 — cement has only `ICMCLK` and `ICM`, so no `LTH`/`STM`/`DRY`/`SPC`. The planned example is structurally blind to what v2 changed
  - Files: `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-food-drink.md`
  - Verify: shows `IFDLTH`'s 8 fuel-variant technologies collapsing to 3 units; a 120 °C duty with boiler / CHP / heat pump / electric competing under C10; an `IFDDRY` reject-heat leg feeding a heat pump (B5); CHP producing heat **and** electricity into the carrier balance
  - **Depends on:** T8 (Group A + B taxonomy), since the collapse it displays must be the real one
- [ ] **T11 (P2, human: ~2h / CC: ~10min)** — docs — Vision doc revisions including the λ→ξ bug
  - Surfaced by: vision lines 74, 78 (the reuse justification this change contradicts), 146 and 240 (λ used for the stranding factor, which is ξ)
  - Files: `docs/specs/2026-08-19-carb3-site-decarbonisation-vision.md`
  - Verify: no bare λ outside §5.6's peak-factor sense
- [ ] **T12 (P3, human: ~1h / CC: ~5min)** — docs — Freeze note on v1; register v2 in `docs/notes/README.md`
  - Surfaced by: PD1 — v1 stays as the parity baseline and readers must know which doc is which
  - Files: v1 spec header, `docs/notes/README.md`
  - Verify: index lists both with the distinction stated
- [ ] **T13 (P1, human: ~1 day / CC: ~30min)** — spec — Write v2 §4 (algorithms), resolving A4's carrier-mix rule and A7's ladder rungs
  - Surfaced by: Review issue 2 — `spec-changes.md` called A4's under-determination "the deepest change" and left it unfixed; issue 6 — the ladder rung was flagged and unowned
  - Files: v2 spec §4, §8.1 (`mix_evidence_tier`), §10 (V23)
  - Verify: V1b has a determinate v2 baseline to compare against, which it does not today
  - **Blocks T5** — V1b cannot be defined against an under-determined A4
- [ ] **T14 (P1, human: ~1 day / CC: ~30min)** — spec — Write v2 §7 (emissions attribution under carriers)
  - Surfaced by: Review issue 1 — §7 was never addressed; the only claim was an unverified "§7's formulae keep working"
  - Files: v2 spec §7, §10 (V22)
  - Verify: V22's three legs pass on a `gas → boiler → heat → dryer` chain including a recovered-heat leg
- [ ] **T15 (P2, human: ~2h / CC: ~10min)** — spec — Add the G4 Tier A scale gate and the V20 (e) concavity leg
  - Surfaced by: Review issues 7 and 8 — the archetype build has no cost gate, and the interpolation-safety argument is unchecked
  - Files: v2 spec §9.2, §10 (V20)
  - Verify: G4 has a stated wall-clock budget; V20 (e) runs at load scope

---

## NOT in scope

| Deferred | Why |
|---|---|
| Any change to `R/` (18,126 lines, 64 files) | The spec targets a future implementation. Phase 1 has not been built. Touching the legacy R model now buys nothing and risks the V1 baseline. |
| Full 8760-hour dispatch in the per-premise LP | Attacks §9's tractability argument directly at stock scale. Tier A exists precisely to avoid it. |
| Seasonal (inter-period) storage state | Matters for hydrogen, barely for industrial heat and batteries. Add only if a decision turns on it. |
| RFNBO / LCHS hourly temporal-correlation compliance | Structurally inexpressible in an annual model. State it as a boundary in v2 §2.3, do not model it. |
| Rewriting `2026-08-05-site-heterogeneity-prd.md` | Already formally superseded and R-specific. Its banner stays accurate. |
| Retiring v1 | It is the COMIT-parity baseline. It stays runnable, not archived. |
| CI wiring beyond a Makefile | No `.github/` exists. A Makefile target is the honest first step; CI is a separate call. |

---

## Verification

```bash
# 1. Tooling baseline — must be green BEFORE any data edit
make data-check          # validator on unmodified docs/notes/data/
make docs-check          # both generators reproduce today's v1 outputs byte-identically

# 2. After the spec work
python3 docs/notes/examples/build_interface_docs.py --check
python3 docs/notes/examples/build_spec_flow_diagram.py --check   # new in T2

# 3. After the data migration
make data-check          # share sums, band ordering, reference resolution,
                         # option/register key integrity, enum domains
                         # expect: 130 used options resolve, exactly 12 optionless processes

# 4. Manual, and not automatable
#    - 397-row reconciliation: every technology maps to exactly one (unit, carrier binding)
#    - every worked-example number recomputes by hand from the stated inputs
#    - v1 spec still generates its interface docs unchanged (the freeze actually held)
```

**The order matters.** Step 1 on today's data is what makes any later red attributable to
the migration rather than to a pre-existing condition.
