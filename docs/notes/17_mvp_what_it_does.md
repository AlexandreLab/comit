# What the MVP does — compared with COMIT, and what parity means

The CaRB3 site energy system is specified but not built. This note says, for someone deciding
whether the first build is the right cut, **what a minimum viable product (MVP) of it does that
COMIT does not, what it deliberately does not do yet, and what "parity" with COMIT means as a
test rather than a slogan.** It walks two premises through both models so the difference is
concrete. The feature list and the build milestones are in
[18_mvp_feature_prioritisation.md](18_mvp_feature_prioritisation.md); this note is the why,
that one is the what and when.

Two decisions taken on 2026-09-08 frame everything below. **The build is in Python, for
everything**; nothing in `R/` is wrapped or kept, and the Python stack is the one
[08_python_redesign_approach.md](08_python_redesign_approach.md) recommends: linopy over
HiGHS, xarray for dimensioned data, pandera for table schemas, parquet as the native format.
**The R model is run once more, as the oracle for the parity tables, and is then retired.**

Companion documents: the
[overview](../specs/2026-08-28-carb3-site-energy-system-overview.md) says why the system is
shaped this way; the
[implementation specification](../specs/2026-08-28-carb3-site-energy-system-implementation.md)
is the normative contract and every `§` reference below points into it; the
[archived baseline specification](../specs/archive/2026-08-19-carb3-site-decarbonisation-implementation.md)
is the frozen document parity is measured against. Notes
[09](09_objective_function.md), [10](10_site_level_pathways.md) and
[13](13_emissions_calculation.md) describe how COMIT behaves today and are the source for the
"through COMIT" halves of the examples.

---

## COMIT today

COMIT solves **one coupled linear programme for the whole of Great Britain**: 16 modelled
sectors, 10 active clusters, and a table of 397 technologies keyed on
*(sector × process × equipment × fuel)*. A site is a row inside a sector, and its energy is
back-derived from its share of the sector's reported emissions
([04](04_site_energy_estimation.md)). Every technology row is a fixed bundle of device and fuel,
so the only lever the model has is to move activity from one row to another. Heat quality is a
suffix in the process code (`LTH`, `HTH`, `STM`, `DRY`) and a technology-to-process mapping
table decides what may serve what. Electricity is a priced fuel with unlimited supply, which is
why onsite generation has to be faked at the grid price and storage is worth nothing
([09](09_objective_function.md)). A national carbon cap, cluster infrastructure and grid
headroom couple every site to every other, and a binary per technology per site turns the LP
into a MILP whenever a minimum hydrogen plant size is set.

## The MVP

The MVP takes **one CaRB3 Factory-class premise at a time** and solves an independent annual
LP for it (D2). The premise's record states what it consumes by carrier and what it produces;
the model expands that into **duties** (a carrier at a grade, §3.9), chooses **units** to meet
them (§3.5), and puts a **carrier balance** between the two (C8). Heat is a set of graded
carriers with a one-way cascade (C10). Onsite generation is an ordinary unit whose output enters
the balance beside imports, export is a real negative cost term, and the connection's import
limit and the roof area bound what can be built (C11, C12). Nothing couples premises, so a
stock run is a batch of independent solves and the national picture is a roll-up afterwards
(S9). The emissions budget is **reported and compared, never enforced**. The problem stays a
pure LP throughout (§5.2).

The MVP is the smallest build that does two things in order: first it **reproduces the frozen
baseline** in a configuration where the two must agree, and then it **demonstrates the one
mechanism the model exists for** on a real site. Storage, and the offline dispatch layer that
gives storage a value (PD1, S0), are deliberately after the MVP.

## Side by side

| Dimension | COMIT today | MVP |
|---|---|---|
| Unit of analysis | Sector × cluster; sites are emissions-share slices | One premise, solved on its own (D2) |
| Baseline energy | Back-derived from the site's share of sector emissions | Supplied per premise by the CaRB3 stock model, by carrier and by year (D4, D12) |
| What the model chooses | One of 397 fixed (device, fuel) technology rows | A unit, and separately the carrier it consumes (§3.5, §3.6) |
| Heat quality | A suffix in the process code plus a mapping table | Graded heat carriers with a one-way cascade (§3.4, C10) |
| Onsite generation | Cannot be expressed; priced at grid rate as a workaround | PV and CHP are ordinary units feeding the carrier balance (C8) |
| Export | None | A negative objective term, bounded by export capacity, priced strictly below import (§5.4, V21) |
| Storage | Worth exactly zero in an annual model | Not in the MVP; arrives later as hybrid units valued offline (PD2, S0) |
| Existing plant | Linear decay of available capacity | Same decay as the MVP fallback tier; ageing with a stranding charge later (D11, C4) |
| Emissions cap | Enforced as a national constraint | Reported and compared against the budget, never constrained (§2.3) |
| Infrastructure | Pipeline and network build-out co-optimised | Exogenous availability and tariff per cluster per period (D7, §3.7) |
| Minimum plant size | A binary per technology per site (MILP) | Eligibility screening before the LP, then reporting; no binaries (§3.5.1, §5.2) |
| Site-specific knowledge | None; sites in a sector are copies | Tiered: known site detail replaces activity defaults, every output row carries its evidence tier (D10) |
| Language and stack | R, golem/Shiny, `ROI`/`highs` | Python, linopy, HiGHS, xarray, pandera, parquet |

---

## Parity, defined

"Parity" is a two-hop chain of tests, and **neither hop may be skipped** (§1.1). It exists
because a rewrite's dominant risk is silent divergence: a Python model that runs, looks
plausible, and disagrees with the R model by a few percent for reasons nobody can locate
([08 §1](08_python_redesign_approach.md)).

### Hop 1 — V1: the baseline reproduces coupled-off COMIT

Run COMIT on the reference workbook with the cluster and national coupling switched off, so
that each site is solved on its own, and freeze what it produces: the objective, the
per-technology capacity by period, and the cost, energy and emissions tables. The archived
baseline specification, solved per site, must reproduce those numbers. V1 is asserted against
the baseline specification, not against the live one (§10.3). It shows that solving per site
loses nothing that coupling was providing for those sites.

### Hop 2 — V1b: the MVP reproduces the baseline

Run the MVP in the **carrier-equivalent configuration** (§10.2) on the same 1,026 sites. All
five conditions hold together:

1. **One carrier per unit.** Every unit's carrier mix is pinned to one primary carrier, so a
   unit's identity determines its fuel.
2. **No storage.** No unit with `is_storage`, and no hybrid unit.
3. **No onsite generation.** No unit in the generation set.
4. **C10, C11 and C12 inactive.** No grade cascade, no connection limit, no siting cap.
5. **No export.** Export is zero for every carrier, connection and period, so the objective
   carries no negative term.

Under these conditions the carrier balance collapses to duty satisfaction plus a fuel price,
which is exactly what the baseline computes. V1b asserts that the MVP reproduces the
baseline's objective and per-carrier energy on those sites (§10.3).

### What is compared, and at what tolerance

Tolerances apply to the quantities an LP determines uniquely: the objective, period totals,
and which constraints bind. They are **not** applied cell by cell. Per-site fuel splits and
build timing can be degenerate, meaning several solutions are cost-equivalent and the solver
may legitimately pick a different one on a different machine
([08 §4](08_python_redesign_approach.md), §9.3). The price wedge and the lexicographic
tie-break (§5.5, §9.3) remove most of that degeneracy in the MVP, but the R oracle has neither,
so the comparison has to be robust to it.

### What the Python decision changes

Parity used to be a parallel-run migration, with both models kept alive and compared
constraint by constraint. With Python for everything, the R model is run **once**, with
coupling disabled, to produce the V1 tables. Those tables are committed as parquet golden
masters under the Python package's tests, and the R model is then frozen and retired. The
constraint-by-constraint comparison still happens, but against the frozen tables rather than
against a live R process. The archived baseline specification stays readable for the same
reason: it is what the tables mean.

---

## Worked example A — a food and drink site (the mechanism case)

**All figures in this example are illustrative** and chosen only to make the mechanics
visible. The real, recomputed example is delivery task T16 and belongs in §13 of the
implementation specification once T17's duty families and grades exist.

### The site

A dairy in the CaRB3 activity *Food and drink*. Its CaRB3 record carries: the activity, energy
by carrier for the base year, physical throughput, one electricity connection with an import
limit, a gas connection, and an available roof area.

| Input | Illustrative value |
|---|---|
| Natural gas | 0.30 PJ/yr, one connection |
| Electricity | 0.06 PJ/yr, one connection, import limit 4 MW, export limit 2 MW |
| Roof area | 12,000 m² |
| Processes at the site | `IFDLTH` hot water, `IFDDRY` spray drying, `IFDREF` refrigeration, `IFDMOT` motors |

### Through COMIT

The dairy is not a thing COMIT can see. It is a fraction of the Food and drink sector's
low-temperature heat process, and that process is served by **eight technology rows that
differ only by fuel**. The model may move activity from the gas-boiler row to the hydrogen-boiler
row or the electric-boiler row, and to a heat-pump row if the mapping table lists one; the
heat pump's coefficient is the same flat figure used for steam, which the architecture document
records as physically wrong. If the real dairy already runs a CHP, COMIT cannot know it and
cannot build one either, because a CHP produces electricity and electricity is a fuel with no
balance. PV is impossible for the same reason. Whether the dairy decarbonises at all is decided
by the national cap and by whether its cluster gets hydrogen; the dairy's own roof and
connection play no part.

### Through the MVP

**S1 ingest.** The record is validated, its activity checked against the 55 Factory-class
activities, its base year resolved, and it is assigned to the nearest in-scope cluster.

**S2 expand to duties and candidate units.** The activity's default process set and duty
profile (§3.2, §3.3) turn the metered energy into duties, and `unit_eligibility` (§3.5.1)
names the units that may serve each one.

| Duty | Carrier and grade | Candidate units (illustrative) |
|---|---|---|
| Hot water for cleaning and pasteurising | `heat@60-150C` | gas boiler · electric resistance · heat pump · CHP |
| Spray drying | `heat@150-400C` | gas burner · electric heater · CHP (steam side) |
| Refrigeration | `electricity` into a `REF` duty | electric chiller |
| Motors and pumps | `electricity` into a `MOT` duty | electric motor |
| Supply-side candidates | produce carriers, serve no duty directly | rooftop PV · grid import · export |

**S3, S4 baseline.** Gas is allocated to the two heat carriers and electricity to the two
electrical duties; the implied incumbent capacity is back-solved with the carrier-mix rule
(§4.1) and tagged `mix_evidence_tier = activity_default` because the site supplied no process
detail.

**S6, S7 solve.** The LP minimises present-value cost over the horizon subject to duty
satisfaction (C1), capacity (C2, C3), the carrier balance at every carrier node (C8),
infrastructure availability (C9), the grade cascade (C10) and the roof cap (C12). What the
balance lets happen, and COMIT could not:

- **The heat pump may serve hot water and is refused for drying.** Its output grade is
  `heat@60-150C`, so C10 removes it from the drying duty's candidate set at load, not by a
  mapping table but because 150 °C output cannot reach a 200 °C duty.
- **A CHP produces two carriers at once.** Its `unit_input_output` rows consume gas and produce
  heat and electricity; the electricity offsets imports, and any surplus is exported at a
  price strictly below the import price (V21), so the model cannot arbitrage it.
- **PV is bounded by the roof.** C12 caps generation capacity at the area times the configured
  power density, so the LP cannot build unbounded PV and export it.
- **Electrification is checked against the connection.** The MVP reports whether the
  electrified peak exceeds the 4 MW import limit; costing a reinforcement (C11 with the
  reinforcement variable) is a later feature.

**S8 output.** One row per unit per carrier per period, each carrying its evidence tiers. An
illustrative slice for the hot-water duty in one period:

| Unit | Carrier | Flow | Evidence |
|---|---|---|---|
| gas boiler | gas in, `heat@60-150C` out | 0.10 PJ | `activity_default` |
| heat pump | electricity in, `heat@60-150C` out | 0.12 PJ heat from 0.04 PJ electricity | `activity_default` |
| rooftop PV | `electricity` out | 0.02 PJ | area tier `fallback` if the roof came from a per-activity fraction |

**Where emissions attach.** The boiler's gas is charged to the boiler because it consumes the
primary carrier (§7.1); the heat pump carries no direct emissions; the electricity it draws is
an indirect emission of the imported carrier, and self-consumed PV displaces that import. The
heat carrier itself never carries emissions, so nothing is double-counted (V22).

**S9 roll-up.** The dairy's rows are summed with every other premise's; the national total is
compared with ECUK and the inventory and with the emissions budget, and the comparison is a
reported number rather than a constraint.

---

## Worked example B — a cement works (the parity case)

This is the example the frozen archived worked example already walks, and delivery task T10
rewrites it for the live specification. It exercises everything the model **must not get
wrong** rather than the new mechanism, which is why it is the parity site.

- **The duty is a mass**, 0.85 Mt of clinker in the archived example, not an energy quantity
  (D5), and the emissions factor is kilotonnes of CO₂ per megatonne of product.
- **The kiln is a chemistry unit**, node-keyed on `ICMCLK`, not a member of a duty family.
- **A CCS train is a separate unit.** It consumes the kiln's CO₂ carrier, names the kiln in
  `abates_unit_id`, inherits the kiln's remaining life and strands nothing while the kiln
  stands (§3.5, C4, V17).
- **Run in the carrier-equivalent configuration**, one carrier per unit, no generation, no
  export, no cascade, the cement works' problem is duty satisfaction plus fuel prices, and V1b
  compares its objective and per-carrier energy with the baseline's.

Cement carries exactly two process codes, `ICMCLK` and `ICM`, so there is nothing at a
low grade and nothing to cascade. That is why the specification says **cement alone is not
sufficient** (§13) and the MVP's exit is the food and drink example, not this one.

---

## What the MVP gives up relative to COMIT

Each item names its category in [note 18](18_mvp_feature_prioritisation.md).

- **Cluster and national coupling.** No shared hydrogen pipeline or CO₂ network is sized by
  the model; availability and tariff arrive as a scenario (D7). *Won't*, by design decision.
- **Cap enforcement.** A scenario can overshoot the budget, and the roll-up says so. *Won't*.
- **The Shiny interface.** Not ported. The MVP is a package with a command-line entry point.
  *Won't* for the MVP.
- **Minimum hydrogen plant size as a hard constraint.** Replaced by eligibility screening and
  reporting, so no MILP. *Must*, in its new form.

## What the MVP defers relative to the specification

- **Storage value.** Hybrid units and the offline Tier A dispatch layer that produces
  ψ, β, χ and ε (PD1, PD2, S0). Hybrid units on default-tier coefficients are *Should*; the
  full Tier A build is *Could*, gated on the G4 wall-clock budget.
- **Waste heat recovery.** Needs the reject-heat coefficients (data-migration B5) before the
  cascade has anything to cascade. *Should*, first after MVP exit.
- **Connection reinforcement.** C11's peak rebuild (§5.6, unwritten) and the reinforcement
  variable. *Should*.
- **Plant ageing in full.** The stranding charge and early-retirement variable (D11, C4); the
  MVP keeps only the fallback tier, which is COMIT's linear decay. *Should*.
- **Measured history.** The base-year substitution ladder and history isolation (D12, V24–V26).
  *Should*.
- **Declared forward process switch** (T24), unit stability and known changes (C6, C7).
  *Could*.

---

## Sources

- Implementation specification §1.1, §1.2, §2.1–§2.3, §3.1–§3.9, §5.2, §5.4, §5.5, §7, §9.3,
  §10.2, §10.3, §13.
- Overview document, "Why it is built this way" and "Programme decisions".
- Architecture document, "Three layers, one balance" and "Hybrid units".
- Notes [04](04_site_energy_estimation.md), [08](08_python_redesign_approach.md),
  [09](09_objective_function.md), [13](13_emissions_calculation.md) for COMIT's current
  behaviour.
