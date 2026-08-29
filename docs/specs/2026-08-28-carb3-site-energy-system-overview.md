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

| # | Decision | Chosen |
|---|---|---|
| D1 | Where the re-architecture lands | **New v2 spec beside v1**; v1 frozen as the parity baseline |
| D2 | Temporal depth | **Full two-tier**, including the archetype dispatch layer that produces ψ and β |
| Issue 1 | COMIT chain of custody | **Two-hop**: v1↔COMIT via V1 (unchanged), v2↔v1 via a new V1b |
| Issue 2 | Unit taxonomy spine | **Hybrid**: family-keyed units for energy services, node-keyed for chemistry |
| Issue 3 | Spec generators | **Parameterise both**, add `--check` to the diagram builder, wire a Makefile |
| Issue 4 | Data validation | **Validator first**, green baseline on today's files, then migrate |
| Issue 5 | Solver degeneracy | **New tie-break key + price-wedge rule + recomputed §9.1 arithmetic** |

---


---

## Provenance

Produced 2026-08-28 from a design conversation covering onsite generation, storage,
electrolysers, biomethane and heat pumps, then put through an engineering plan review.

**Five findings, all folded into the plan above:**

| # | Finding | Confidence | Resolution |
|---|---|---|---|
| 1 | V1 step 4 compares *per-technology capacity by period*, which does not exist under a unit/carrier model. V1 is a blocking Phase 1 exit criterion | 9/10 | Two-hop parity: v1↔COMIT via V1 unchanged, v2↔v1 via new V1b |
| 2 | `technology_category` (11 values, 397 rows) conflates fuel carrier, conversion device and abatement bolt-on on one axis | 9/10 | Hybrid unit spine; taxonomy split is TODO group A |
| 3 | Both spec generators hardcode heading strings, section prefixes and the label ranges `A1-A9 / C1-C9 / V1-V17 / D1-D11`; neither is wired to CI; the diagram builder has no `--check` | 10/10 | Parameterise both (T2) |
| 4 | No committed validator exists for the seven hand-researched data files the migration rewrites | 10/10 | Validator first, green baseline before migrating (T1) |
| 5 | The carrier balance manufactures new solver degeneracy, and §9.3's tie-break key (`technology_code`) ceases to exist | 8/10 | New tie-break, price-wedge rule, recomputed §9.1 arithmetic (T7) |

**Two critical gaps** — silent, untested and unhandled as specified — are closed by T6:
ψ extrapolated outside its fitted design-ratio range, and a premise matching no archetype.

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

No unresolved decisions. An independent second-model review was not run (codex not
installed on the authoring machine).
