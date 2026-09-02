# CaRB3 Site Energy System — Overview and Decisions

**Status:** Draft v1 for review
**Date:** 2026-08-28
**Scope:** Great Britain · CaRB3 **Factory class** only (55 activities)
**Part of:** the v2 migration plan. The entry point.

**This plan is five documents.** Read the overview first; the other four are independent.

| Doc | For | |
|---|---|---|
| [Overview and decisions](2026-08-28-carb3-site-energy-system-overview.md) | everyone — start here | **you are here** |
| [Architecture](2026-08-28-carb3-site-energy-system-architecture.md) | modellers |  |
| [Spec changes and tests](2026-08-28-carb3-site-energy-system-spec-changes.md) | whoever writes the v2 spec |  |
| [Data migration](2026-08-28-carb3-site-energy-system-data-migration.md) | whoever owns the data tables |  |
| [Delivery](2026-08-28-carb3-site-energy-system-delivery.md) | whoever schedules the work |  |

> **This plans work; it does not specify it.** The v2 specification itself
> (`2026-08-28-carb3-site-energy-system-implementation.md`) does not exist yet — writing it is task T4.

---

## Context

The CaRB3 implementation spec models a site as a set of processes, each served by
technologies drawn from a 397-row table keyed on *(sector × process × equipment × fuel)*.
That structure has three consequences that block work the model is now being asked to do:

1. **Onsite generation cannot be expressed.** PV, CHP, electrolysers and anaerobic
   digestion produce commodities rather than serving a process demand, so C1
   (`Σ u = D`) has no place for them. §5.6 Extension 2 sketches onsite generation and
   export but stops short, because the model has no electricity balance. Note 09 records
   the workaround: onsite `ELCGEN` is priced at the grid rate so self-generation is not
   free — which nullifies PV, whose entire value is that its energy costs LCOE and not
   the tariff.
2. **Storage is worth exactly zero.** A battery or thermal store charges and discharges
   inside one annual period and nets to a round-trip loss, so a cost-minimising model
   never builds one.
3. **Heat quality is enforced by a mapping table, not by physics.** Temperature lives in
   the *process code* (`LTH`/`HTH`/`STM`/`DRY`) and the technology-to-process mapping is
   what stops a heat pump firing a kiln. Waste heat recovery — 28 of the 134 options in
   `decarbonisation_options_library.csv` — is structurally inexpressible, because a
   kiln's reject heat has nowhere to go.

The fix is one structural move: **separate the duty from the unit that meets it, and put a
carrier network between them.** Everything else in this plan is a consequence.

v1 stays frozen as the audited COMIT-parity baseline. v2 is a new document.

---

## Decisions taken in this review

**On labels — read this before the table.** Three families of label appear across these
five documents and two of them look alike:

| Family | Means | Defined in |
|---|---|---|
| **PD1–PD3** | Plan decisions — scope calls made in this review | the table below |
| **Issue 1–5** | Review findings and their resolutions | [Provenance](#provenance) below |
| **D1–D11** | The **vision doc's** design decisions (per-site solves, exogenous infrastructure, plant vintage) | [vision §6](archive/2026-08-19-carb3-site-decarbonisation-vision.md) |

So `D2` always means the vision's *per-site independent solves*, never this plan's
temporal-depth decision — that is `PD2`. Group letters in the
[data migration](2026-08-28-carb3-site-energy-system-data-migration.md) doc (`A1`, `D3`, `E2`)
are a fourth, doc-local numbering and are always written bold at the start of a bullet.

The v1 spec carries the same kind of note at its §6, where the pipeline stages and the
constraints were both numbered `C` until the stages were renamed `S`. This is that lesson
applied rather than relearned.

| # | Decision | Chosen |
|---|---|---|
| PD1 | Where the re-architecture lands | **New v2 spec beside v1**; v1 frozen as the parity baseline |
| PD2 | Temporal depth | **Full two-tier**, including the archetype dispatch layer that produces ψ, β, χ and ε |
| PD3 | How storage acquires a value | **Hybrid units** — co-located packages at a fixed sizing ratio (`pv_battery_2h`, `chp_thermal_store`, `electrolyser_battery`). Standalone storage only where its value is β |
| Issue 1 | COMIT chain of custody | **Two-hop**: v1↔COMIT via V1 (unchanged), v2↔v1 via a new V1b |
| Issue 2 | Unit taxonomy spine | **Split**: family-keyed units for energy services, node-keyed for chemistry |
| Issue 3 | Spec generators | **Parameterise both**, add `--check` to the diagram builder, wire a Makefile |
| Issue 4 | Data validation | **Validator first**, green baseline on today's files, then migrate |
| Issue 5 | Solver degeneracy | **New tie-break key + price-wedge rule + recomputed §9.1 arithmetic** |

---

## Provenance

Produced 2026-08-28 from a design conversation covering onsite generation, storage,
electrolysers, biomethane and heat pumps, then put through an engineering plan review.

**Five findings, all folded into the plan above:**

| # | Finding | Confidence | Resolution |
|---|---|---|---|
| 1 | V1 step 4 compares *per-technology capacity by period*, which does not exist under a unit/carrier model. V1 is a blocking Phase 1 exit criterion | 9/10 | Two-hop parity: v1↔COMIT via V1 unchanged, v2↔v1 via new V1b |
| 2 | `technology_category` (11 values, 397 rows) conflates fuel carrier, conversion device and abatement bolt-on on one axis | 9/10 | Split unit spine; taxonomy split is TODO group A |
| 3 | Both spec generators hardcode heading strings, section prefixes and the label ranges `A1-A9 / C1-C9 / V1-V17 / D1-D11`; neither is wired to CI; the diagram builder has no `--check` | 10/10 | Parameterise both (T2) |
| 4 | No committed validator exists for the seven hand-researched data files the migration rewrites | 10/10 | Validator first, green baseline before migrating (T1) |
| 5 | The carrier balance manufactures new solver degeneracy, and §9.3's tie-break key (`technology_code`) ceases to exist | 8/10 | New tie-break, price-wedge rule, recomputed §9.1 arithmetic (T7) |

**One critical gap** — silent, untested and unhandled as specified — is closed by T6: a
premise matching no archetype.

There were two. The other was ψ extrapolated outside its fitted design-ratio range, and
the hybrid-unit decision (PD3) **removed it rather than testing for it**: a fixed sizing
ratio means there is no continuous ratio to extrapolate along, and no piecewise
linearisation to fall off the end of. That also deletes the one genuinely hard piece of
engineering the plan previously carried, since a bilinear ψ(ratio) × output term needed
SOS2 or binaries to linearise exactly, against a §5.2 requirement that the problem stay a
pure LP.

**Defects found in existing documents, independent of this migration:**

- `](interfaces/…)` at implementation spec lines 380 and 2306 sits inside both extracted
  ranges and is not depth-adjusted, producing **dead links in both generated interface
  docs today**. Verified by reading the generated files.
- Vision doc lines 146 and 240 use `λ` for the stranding factor, which the implementation
  spec calls `ξ`; `λ` is the §5.6 peak factor. The worked example already flags the
  collision at its line 248.
- Worked example line 372 cites `§1.5` for measured emissions, which are `§1.6`; line 414's
  stated withholding set omits `§1.9`, which the comparison it draws requires.
- Worked example A3 shares (coal 0.97 to the kiln) disagree with
  `../notes/data/activity_process_energy_profile.csv` (1.0).

### Second engineering review, 2026-09-01

Run against the merged documents. Nine findings, five of them P1, all folded in. Three
were gaps where the plan changed something and then said nothing about the consequence.

| # | Finding | Confidence | Resolution |
|---|---|---|---|
| 1 | **§7 emissions accounting never addressed.** The only claim was "§7's formulae keep working" — the formulae do, the *attribution* does not | 10/10 | New §7 change section + V22 (T14) |
| 2 | **§4 algorithms never addressed**, and A4's break was named "the deepest change" then left unfixed. V1b cannot run against an under-determined A4 | 10/10 | New §4 table with the carrier-mix tier rule + V23 (T13) |
| 3 | **Waste heat had no data item.** Claimed as a headline justification; grades say what a unit accepts, not what it rejects | 9/10 | New data item B5, reject-heat coefficients |
| 4 | **"~35 units" contradicted "preserve 57 non-fuel archetypes"**, and "24 duty families" counted 16 sector-root codes as duties | 10/10 | Recomputed: **~95 units**, 12 service families + 14 chemistry nodes |
| 5 | `TODOS.md` claimed as written; did not exist | 10/10 | Dropped — this document is the list |
| 6 | A7 relaxation ladder rung flagged and unowned | 10/10 | Rungs C12 → C10 → C11 specified in §4 |
| 7 | The concavity claim making hybrid interpolation safe was argued in prose and checked nowhere | 8/10 | V20 (e) |
| 8 | Tier A had no scale gate, and it is the new expensive thing | 8/10 | New gate G4 |
| 9 | **The planned worked example cannot demonstrate the carrier mechanism.** Cement has only `ICMCLK` and `ICM` — no `LTH`, `STM`, `DRY` or `SPC` — so no graded-heat cascade, no unit competition, no waste-heat sink, and CHP only fused inside CCS rows | 9/10 | Keep cement for parity; add a **food & drink** example for the mechanism (T16) |

Findings 4 and the item recount are the third and fourth instances this week of a count
written into prose without being counted, which is now a logged lesson and a rule in
`CLAUDE.md`.

No unresolved decisions. An independent second-model review was not run (codex not
installed on the authoring machine).
