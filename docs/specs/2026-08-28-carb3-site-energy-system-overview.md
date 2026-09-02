# CaRB3 Site Energy System — Overview and Decisions

**Status:** Draft for review
**Date:** 2026-09-02
**Scope:** Great Britain · CaRB3 **Factory class** only (55 activities)

**This is the entry point.** Five documents describe the system; read this one first.

| Doc | For | |
|---|---|---|
| [Overview and decisions](2026-08-28-carb3-site-energy-system-overview.md) | everyone — start here | **you are here** |
| [Architecture](2026-08-28-carb3-site-energy-system-architecture.md) | modellers — the design and its reasoning | |
| [Implementation specification](2026-08-28-carb3-site-energy-system-implementation.md) | implementers — the normative contract | |
| [Data migration](2026-08-28-carb3-site-energy-system-data-migration.md) | whoever owns the data tables | |
| [Delivery](2026-08-28-carb3-site-energy-system-delivery.md) | whoever schedules the work | |

> **Nothing here is built yet.** The implementation specification targets a system that does
> not exist; the model running in `R/` today is COMIT, which this one is validated against.
> A change to these documents is not a change to that model.

---

## What the system is

One record per industrial premise in, a least-cost decarbonisation pathway out, solved
independently per premise across the whole CaRB3 Factory-class stock.

A site is modelled in three layers. **Duties** are what the site must produce — 0.85 Mt of
clinker, 3.9 PJ/yr of heat above 1000 °C. **Units** are what converts between energy
carriers — boilers, heat pumps, kilns, CHP, PV, batteries, electrolysers. **Connections**
are what crosses the site boundary, bounded by real import and export capacity. Between the
three sits a **carrier balance**: every carrier the site uses balances at every period, and
that single constraint is what lets a unit serve a duty without being wired to it by a
mapping table.

## Why it is built this way

COMIT, the model running today, represents a site as a set of processes each served by
technologies drawn from a 397-row table keyed on *(sector × process × equipment × fuel)*.
That structure has three consequences that block work the model is now being asked to do.

1. **Onsite generation cannot be expressed.** PV, CHP, electrolysers and anaerobic digestion
   produce carriers rather than serving a process demand, so a duty-satisfaction constraint
   of the form `Σ output = demand` has no place for them. The workaround on record prices
   onsite generation at the grid rate so that self-generation is not free — which nullifies
   PV, whose entire value is that its energy costs LCOE and not the tariff.
2. **Storage is worth exactly zero.** A battery or thermal store charges and discharges
   inside one annual period and nets to a round-trip loss, so a cost-minimising model never
   builds one.
3. **Heat quality is enforced by a mapping table, not by physics.** Temperature lives in the
   *process code* (`LTH`/`HTH`/`STM`/`DRY`), and what stops a heat pump firing a kiln is the
   technology-to-process mapping. Waste heat recovery — 28 of the 134 options in
   `decarbonisation_options_library.csv` — is structurally inexpressible, because a kiln's
   reject heat has nowhere to go.

The fix is one structural move: **separate the duty from the unit that meets it, and put a
carrier network between them.** Everything else in these documents is a consequence.

---

## Programme decisions

Two decisions fix the scope of the build. They are labelled `PD1`–`PD2` and cited by label
throughout.

| # | Decision | Chosen |
|---|---|---|
| **PD1** | Temporal depth | **Full two-tier.** An offline archetype dispatch layer runs at high time resolution and produces the coefficients ψ, β, χ and ε; the per-premise investment problem consumes them as parameters and stays annual and a pure LP |
| **PD2** | How storage acquires a value | **Hybrid units** — co-located packages at a fixed sizing ratio (`pv_battery_2h`, `chp_thermal_store`, `electrolyser_battery`). Standalone storage exists only where its value is β, the firm-capacity contribution that defers a connection reinforcement |

**On labels.** Two families of label look alike and mean different things:

| Family | Means | Defined in |
|---|---|---|
| **PD1–PD2** | Programme decisions — the scope calls above | the table above |
| **D1–D11** | Design decisions — per-site solves, exogenous infrastructure, plant vintage, evidence tiers | [implementation spec §1.6](2026-08-28-carb3-site-energy-system-implementation.md) |

So `D2` always means *per-site independent solves*, never this document's temporal-depth
decision, which is `PD1`. Group letters in the
[data migration](2026-08-28-carb3-site-energy-system-data-migration.md) document (`A1`,
`D3`, `E2`) are a third, document-local numbering and are always written bold at the start
of a bullet.

The implementation spec carries the same kind of note at its §1.4. Label collisions have
cost this repository real time more than once; check before introducing a new family.

---

## Where the boundaries are

**In scope:** a validated premise record to a per-premise pathway, plus GB aggregation, plus
the offline archetype layer that makes storage representable.

**Out of scope, and deliberately so:** deriving the premise's baseline energy, which is
supplied upstream by the stock model (D4); deciding infrastructure build-out, which is a
scenario input (D7); enforcing a national emissions budget, which is reported and compared
but never constrained; Northern Ireland (D8); and any hourly temporal-correlation compliance
claim, such as RFNBO or LCHS, which an annual model structurally cannot express.
