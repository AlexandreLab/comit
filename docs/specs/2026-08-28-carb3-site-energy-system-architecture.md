# CaRB3 Site Energy System — Architecture

**Status:** Draft v1 for review
**Date:** 2026-08-28
**Scope:** Great Britain · CaRB3 **Factory class** only (55 activities)
**Part of:** the v2 migration plan. The design itself, and what it reuses.

**This plan is five documents.** Read the overview first; the other four are independent.

| Doc | For | |
|---|---|---|
| [Overview and decisions](2026-08-28-carb3-site-energy-system-overview.md) | everyone — start here |  |
| [Architecture](2026-08-28-carb3-site-energy-system-architecture.md) | modellers | **you are here** |
| [Spec changes and tests](2026-08-28-carb3-site-energy-system-spec-changes.md) | whoever writes the v2 spec |  |
| [Data migration](2026-08-28-carb3-site-energy-system-data-migration.md) | whoever owns the data tables |  |
| [Delivery](2026-08-28-carb3-site-energy-system-delivery.md) | whoever schedules the work |  |

> **This plans work; it does not specify it.** The v2 specification itself
> (`2026-08-28-carb3-site-energy-system-implementation.md`) does not exist yet — writing it is task T4.

---

## The architecture

### Three layers, one balance

```
  ┌─────────────────────────────────────────────────────────────────┐
  │ LAYER 1 — DUTIES              what the site must produce        │
  │   process_duty[q,t]  →  demand for a CARRIER at a GRADE         │
  │   "0.85 Mt clinker"            "3.9 PJ/yr of heat@>1000C"       │
  └───────────────────────────┬─────────────────────────────────────┘
                              │  C1  duty satisfaction
  ┌───────────────────────────┴─────────────────────────────────────┐
  │ LAYER 2 — UNITS               what converts between carriers    │
  │   ~95 units: boiler, heat_pump, CHP, kiln, PV, battery,         │
  │   electrolyser, AD, thermal_store, CCS_train, motor, dryer      │
  │   + HYBRID units at a fixed sizing ratio: pv_battery_2h,        │
  │     chp_thermal_store, electrolyser_battery, hp_thermal_store   │
  │   each: input carriers (−) → output carriers (+), capex, life   │
  └───────────────────────────┬─────────────────────────────────────┘
                              │  C8  CARRIER BALANCE  (the core change)
                              │      Σ_k u[k,t]·ι[k,c] + m[c,t] − x[c,t] = 0
  ┌───────────────────────────┴─────────────────────────────────────┐
  │ LAYER 3 — CONNECTIONS         what crosses the site boundary    │
  │   premise_connection (§3.1.3, collected but never read)         │
  │   import m[c,t] @ tariff · export x[c,t] @ export price         │
  │   bounded by import_capacity / export_capacity per connection   │
  └─────────────────────────────────────────────────────────────────┘
```

**C8 generalised from intermediates to every carrier is the single change that makes the
rest work.** Today `C8` balances only `c ∈ C^int`; electricity is a priced fuel with
unconstrained supply. Once every carrier balances, PV / CHP / electrolysers / AD are
ordinary units and need no special class. Note 09's grid-rate fudge disappears: CHP
becomes gas in, heat and electricity out.

### Graded heat and the cascade

Heat becomes `heat@band` with a one-way cascade — high grade may serve a low-grade duty,
never the reverse. This is an ordering in the balance, still LP.

```
  heat@>1000C  ──┐  kiln, glass furnace                (chemistry duties)
       │         │
  heat@400-1000C ┤  HT furnace                          cascade flows
       │         │  ══════════════════════════════════▶ DOWNWARD ONLY
  heat@150-400C  ┤  steam boiler, HT heat pump
       │         │
  heat@60-150C   ┤  boiler, heat pump, WASTE HEAT ◀──── kiln reject heat
       │         │                                      enters here
  heat@<60C      ┘  heat pump, space heat
```

Two things fall out for free: **waste heat recovery becomes representable** (a kiln's
reject heat is a low-grade supply, which is exactly the source a heat pump needs), and
**the heat pump COP stops being a constant** — it is declared against the lift, so the
current situation where `IFDSTMHP01` (steam) carries the same `33.333` coefficient as
`IFDLTHELCHP01` (low-temperature hot water) cannot recur.

### Unit spine — split (Issue 2)

The 94 process codes are sector-prefixed. Stripping the 3-character prefix, and excluding
the 16 sector-root codes that are sector-level demand commodities rather than duties,
leaves **12 service duty families and 14 chemistry nodes**. The split follows D5's existing
two-denominator line:

| Class | Keying | Members | Denominator |
|---|---|---|---|
| **Energy services** | Family-keyed generic units | 12: `DRY`, `EN`, `HRS`, `HTH`, `LTH`, `MOT`, `NEUOTH`, `OTH`, `PHEAT`, `REF`, `SPC`, `STM` | PJ |
| **Chemistry** | Node-keyed per-process units | 14: `IAM`, `ICMCLK`, `IGLMRG`, `IHVC`, `IISHRS`, `IISLST`, `IISPIR`, `IISSNT`, `ILMCLK`, `INDHFCOTH`, `IPPBPA`, `IPPPBD`, `IPPPBP`, `PRCOIL` | Mt |

Sector specificity moves out of the unit identity and into `unit_eligibility`.

**Where ~95 comes from, and why it is not ~35.** An earlier draft of this document said
"~35 units", which cannot be right: B2 of the [data
migration](2026-08-28-carb3-site-energy-system-data-migration.md) requires the **57
non-fuel technologies** (CCS 25, heat pump 31, dry kiln 1) to survive as distinct
archetypes, and 57 alone exceeds 35. The floor is

```
   12  service duty families
 + 14  chemistry nodes
 + 57  preserved non-fuel archetypes (B2)
 + ~12 hybrid units (PD3)
 ────
  ~95  units
```

That is still a collapse from 397, and the maintainability argument survives it intact:
adding hydrogen firing is one carrier row rather than N technology rows either way. But the
number to quote is ~95. **Recompute it after Group B rather than carrying this figure
forward** — it is a floor, not a result.

### Two-tier temporal structure (PD2)

```
  TIER A — OFFLINE, high time resolution, run once per archetype
  ┌──────────────────────────────────────────────────────────────┐
  │  ~200-400 archetypes = activity × load shape × schedule × size│
  │  typical-day or hourly dispatch, evaluated once at EACH       │
  │  hybrid unit's fixed sizing ratio                             │
  │      │                                                        │
  │      ├── ψ  onsite-generation self-consumption fraction       │
  │      ├── β  storage firm-capacity contribution (feeds C11)    │
  │      ├── χ  paired-output utilisation (CHP heat, HP duty)     │
  │      ├── ε  effective purchase price for flexible loads       │
  │      └── λ, peak-to-mean  (already specified in §5.6)          │
  │  ONE CONSTANT per coefficient per HYBRID UNIT  ──────┐        │
  └──────────────────────────────────────────────────────┼────────┘
                                                         ▼
  TIER B — PER-PREMISE INVESTMENT LP, annual, 5-year steps
  ┌──────────────────────────────────────────────────────────────┐
  │  consumes ψ, β, χ, ε as PARAMETERS → stays a pure LP (§5.2)   │
  │  D2 decomposition intact · §9 tractability argument intact    │
  └──────────────────────────────────────────────────────────────┘
```

The investment decision needs a *correct annualised cost*, not hourly resolution. That
cost depends on hourly behaviour only through a handful of aggregate numbers. Computing
them a few hundred times instead of 300k times is the whole leverage.

### Hybrid units — how storage acquires a value

Storage on its own is worth nothing here: a battery or thermal store charges and
discharges inside one annual period and nets to a round-trip loss, so a cost-minimising
model never builds one. The value is real but it is *relational* — a battery is worth
something **relative to the asset it is paired with**.

So storage enters the model mainly through **hybrid units**: co-located packages at a
**fixed sizing ratio**, each a single unit with a single capex and a single set of
coefficients. `pv_battery_2h` is one unit, not two decision variables.

**The fixed ratio is what keeps the problem an LP, and this is the load-bearing reason
for the whole construction.** ψ depends on the storage-to-generation ratio. If both
capacities were free decision variables, ψ(ratio) × output would be a decision-dependent
coefficient multiplying a decision variable, which is bilinear; linearising it piecewise
inside a *pure* LP works only if the curve is convex in the right direction, and otherwise
costs SOS2 or binaries. §5.2 is explicit that the pure-LP property must be defended. A
fixed ratio makes ψ a constant and the difficulty disappears rather than being managed.

**When a hybrid unit is needed, and when it is not.** The test is whether the coefficient
depends on a ratio to a paired asset:

| Value the storage creates | Coefficient | Hybrid unit? |
|---|---|---|
| Raises self-consumption of onsite generation | ψ | **Yes** — depends on the storage/generation ratio |
| Raises CHP heat utilisation, or heat-pump duty via a thermal store | χ | **Yes** — depends on the store/converter ratio |
| Lowers the effective purchase price of a flexible load (electrolyser, heat pump) | ε | **Yes** — depends on the storage/load ratio |
| Defers a connection reinforcement | β | **No** — enters C11 linearly, no ratio dependence |

A standalone battery bought purely to shave peak and defer reinforcement therefore stays
a standalone unit and works unchanged. That is a real and common industrial case: the site
wants to electrify, the connection binds, the battery buys headroom. Hybrid units are for
the cases where the storage only means something relative to its partner.

**ε is not optional.** For `pv_battery` the value is self-consumption and for
`chp_thermal_store` it is heat utilisation, but for `electrolyser_battery` the battery is
buying *cheap hours* — arbitrage against a time-varying tariff. The annual model carries
one electricity price per period, so without ε that value is structurally invisible,
`electrolyser_battery` is strictly dominated by a bare electrolyser, and it never gets
built. That would reintroduce the exact problem hybrid units exist to solve.

**Interpolation between hybrid units is safe, and it is worth saying why.** The LP may
build half a `pv_battery_2h` and half a `pv_battery_4h`, and it then gets the chord between
them. Storage benefit is concave in storage size — the first hour buys far more than the
fourth — so the chord lies *below* the true curve. The LP understates a blend's benefit and
prefers the discrete endpoints, which are the real costed designs. The approximation errs
in the safe direction.

**Capex must be a levelised bundle annuity, not a sum of parts.** PV lasts 30–40 years and
a battery 10–15 with an augmentation partway, but a hybrid unit has one $L$, and both C3's
capacity window and C4's stranding charge key on it. Embed the battery replacement in the
annuitised capex and keep one lifetime. This also fixes something the component-wise
approach gets wrong anyway: inverter, connection works, land and project development are
*shared* costs that get double-counted or dropped when the parts are costed separately.

**Every hybrid unit needs a bill of materials.** "Built 5 MW of `pv_battery_2h`" does not
answer *how much battery does GB industry need*, which is a headline question this model
will be asked. A per-unit component decomposition lets §8's `Costs` and `Network` rows
report per component. Cheap to specify now, invisible until too late if omitted.

**On naming.** These are *not* virtual power plants. In the industry a VPP aggregates
assets **across multiple sites** and dispatches them as one, which is precisely the
inter-premise coupling D2 forbids — so a genuine VPP is architecturally impossible in this
model. Calling a co-located package a VPP would promise a reader exactly the thing that
cannot be built. **Hybrid unit** throughout.

### Lumpiness — an architectural rule, not a per-technology hack

Real units come in sizes, and `R/fct_constraints_hydrogen.R:650` plus
`R/fct_decision_variables.R:597` show what happens otherwise: a binary per technology per
site, which is the MILP D7 removed. Rule for v2:

> Minimum viable scale is handled by **eligibility screening upstream** (a site below the
> threshold never gets the unit in its candidate set, decided in A2) and by **reporting
> downstream** (§6.3's "reported comparison, not constraint" pattern). Never by a binary
> inside the per-premise LP.

---

## What already exists (reuse, do not rebuild)

| Asset | Path | How v2 uses it |
|---|---|---|
| `technology_input_output` sign convention | spec §3.6 (789–804) | Becomes `unit_input_output` **near-unchanged**. Consumed negative, produced positive is exactly what the carrier balance needs. §7's formulae depend on it and keep working. |
| `premise_connection` | spec §3.1.3 (492–537) | Already carries `import_capacity`, `export_capacity`, `connection_voltage`, `onsite_generation_*`. Collected specifically for this; **nothing reads it today**. v2 reads it. |
| §5.6 peak-derivation pseudocode | spec 2060–2085 | The 14-step method, `process_load_shape` (§3.13), `premise_operating_profile` (§3.12), `premise_weekly_profile` (§3.14) are the Tier A inputs. Do not invent a parallel mechanism. |
| D10 three-tier evidence pattern | vision §6, spec §3.3.2 | Reused verbatim for grades, areas, COPs and ψ/β provenance. |
| D11 vintage and stranding | spec §5.3.1, C4 | Generalises to units unchanged. η and R̄ stay parameters; the K⁰ scoping that keeps §9.1 honest still applies. |
| `Z^infra` tariff collapse | spec §5.4 (1729–1741) | The import-tariff term for every carrier, not just H₂/CO₂. |
| `build_interface_docs.py` relinker | `docs/notes/examples/` | Parameterised, not forked (Issue 3). |
| `build_spec_flow_diagram.py` | `docs/notes/examples/` | Regenerates all three diagram artefacts from the spec. Diagram work is *regenerate*, not redraw. |
| Decarb options library | `decarbonisation_options_library.csv` | 134 options with provenance and TRL. Its own README's suggested next step is this migration. |
