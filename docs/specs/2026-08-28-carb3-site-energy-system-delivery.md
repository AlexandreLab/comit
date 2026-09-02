# CaRB3 Site Energy System — Delivery

**Status:** Draft for review
**Date:** 2026-09-02
**Scope:** Great Britain · CaRB3 **Factory class** only (55 activities)

**Five documents describe the system.** Read the [overview](2026-08-28-carb3-site-energy-system-overview.md) first.

| Doc | For | |
|---|---|---|
| [Overview and decisions](2026-08-28-carb3-site-energy-system-overview.md) | everyone — start here |  |
| [Architecture](2026-08-28-carb3-site-energy-system-architecture.md) | modellers |  |
| [Implementation specification](2026-08-28-carb3-site-energy-system-implementation.md) | implementers |  |
| [Data migration](2026-08-28-carb3-site-energy-system-data-migration.md) | whoever owns the data tables |  |
| [Delivery](2026-08-28-carb3-site-energy-system-delivery.md) | whoever schedules the work | **you are here** |

> **Files, tasks, sequencing, scope boundary and verification.** Nothing here changes the
> model running in `R/`; see *NOT in scope* below.

---

## Files

### Create

| Path | What |
|---|---|
| `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md` | The implementation specification |
| `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-cement.md` | Worked example, cement works — the parity case (T10) |
| `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-food-drink.md` | Worked example, food & drink — the carrier mechanism (T16) |
| `docs/notes/examples/validate_carb3_data.py` | Stdlib-only validator for the reference data |
| `docs/notes/examples/spec_docs.config.json` | Per-spec section anchors, own-prefix, output dirs, entity roles. **Not label ranges** — those are read from each spec's Notation table, see T2 |
| `docs/notes/examples/spec_docs_config.py` | Shared config loader and the spec-vs-config label cross-check (T2) |
| `docs/notes/16_input_data_readiness.md` | Input-data audit: what has a schema, what has data, what has neither (T17) |
| `docs/notes/data/carb3_comit_process_crosswalk.csv` | CaRB3 process → COMIT process code, the join that does not exist (T17) |
| `docs/notes/data/activity_process_duty_profile.csv` | Default duty family + heat grade per process (T17) |
| `docs/notes/data/activity_default_unit.csv` | Default installed units per activity/process/duty, incl. CHP (T18) |
| `Makefile` | `make docs-check` / `make data-check` |

### Modify

| Path | Change |
|---|---|
| `docs/notes/examples/build_interface_docs.py` | Read config, not literals; fix the `](interfaces/…)` dead link; add a target for this specification |
| `docs/notes/examples/build_spec_flow_diagram.py` | Add `--check`; move the hardcoded entity-name lists to config. The `3\.[\d.]+` entity regex is **left alone** — this specification numbers its data model `### 3.x` too, so the existing pattern already parses it |
| `docs/notes/README.md` | Register the specification, its worked examples and its interface docs |

### Do not touch

Everything under `docs/specs/archive/`. Those documents are frozen: one of them is the
COMIT-parity baseline that V1 validates against, and rewriting it would invalidate the
baseline rather than improve it. Known defects in them are recorded in
[`archive/README.md`](archive/README.md).

---


## Parallelisation

| Lane | Modules | Depends on |
|---|---|---|
| L1 — Tooling | `docs/notes/examples/`, `Makefile` | — |
| L2 — Spec §1–§5 | `docs/specs/` | the unit spine (settled) |
| L3 — Data taxonomy | `docs/notes/data/` Groups A, B | L1 (validator baseline) |
| L4 — Decarb options | `docs/notes/data/` Group C | L3 A1–A5 |
| L5 — Spec §6–§13 + worked examples | `docs/specs/` | L2 |
| L6 — Index edits | READMEs | L2 |

**L1 and L2 start in parallel immediately.** L3 waits on L1's green baseline. L4 waits on
L3's taxonomy split. L5 waits on L2. L6 last, so it describes what was actually built.

---

## Implementation Tasks

- [x] **T1 (P1, human: ~1 day / CC: ~30min)** — tooling — Write the stdlib-only data validator and establish a green baseline
  - Surfaced by: no generator and no validator existed for the seven hand-researched reference files
  - Files: `docs/notes/examples/validate_carb3_data.py`, `Makefile`
  - Verify: `make data-check` green on unmodified `docs/notes/data/`
  - **Done.** 12 blocking checks + 2 advisory, all green on unmodified data. Baseline counts: 376 register keys, 359 profile keys, 137 share-sum groups, 1109 option mappings, 134 library options, 270 references, 198 cited. Advisory: 17 processes with no profile, 12 with no option, 4 unused options — **these numbers are the baseline; a change in them after migration is the signal**
  - Surfaced while building it: only **37 of 490** profile rows carry uncertainty bands (8%), so V4's R3 band-ordering assertion barely runs today. Reported as advisory, not enforced — backfilling bands is research, not a correctness bug
- [x] **T2 (P1, human: ~1 day / CC: ~25min)** — tooling — Parameterise both spec generators, add `--check` to the diagram builder
  - Surfaced by: `build_interface_docs.py:38-39,58-59,168-169` hardcoded headings, own-prefix and label ranges
  - Files: `build_interface_docs.py`, `build_spec_flow_diagram.py`, `spec_docs_config.py`, `spec_docs.config.json`, `Makefile`
  - Verify: `make docs-check` reproduces the published interface docs byte-identically
  - **Done.** All five published outputs regenerate byte-identically — the only diff against the
    pre-T2 files is the two lines T3 fixes. Both generators take `--spec / --all / --check
    / --list`; `make docs-check` now covers the diagrams too, which it never did
  - **Label ranges were deliberately kept out of the config.** Putting `C1`–`C9` in JSON
    only moves the staleness from Python to JSON, and the failure is silent — a document
    citing `C1`–`C9` against a spec defining `C12` still renders. Instead each generator
    parses the target spec's own Notation table and cross-checks it against the families
    the config asks it to cite. Four injected defects all caught: a spec-side `C9`→`C10`
    and a hand-edited diagram both fail `--check` (exit 1); a deleted family and a renamed
    Notation heading both raise `ConfigError` naming the spec's value and the config's side
    by side (exit 2)
  - This specification is registered but both outputs are `enabled: false` with a
    `blocked_by` reason: §4 carries no `### A1 — ` headings yet, so the journey diagram and
    SVG would come out empty, and §8 is unwritten, so there is no output schema to publish.
    Flip the flags when those land; no code change needed
  - Fixed in passing: `make` targets used paths relative to the caller, so every target
    failed from a subdirectory with a `FileNotFoundError` that read like a missing
    generator. Paths are now derived from `MAKEFILE_LIST`; verified from `R/`
- [x] **T3 (P2, human: ~30min / CC: ~5min)** — tooling — Fix the live `](interfaces/…)` dead link in both generated files
  - Surfaced by: verified — spec lines 380 and 2306 sit inside both extracted ranges and `fix_relative_paths` does not depth-adjust them
  - Files: `build_interface_docs.py:136-140`
  - Verify: link resolves from `docs/specs/archive/interfaces/`
  - **Done**, folded into T2 since it is the same function. `fix_relative_paths` no longer
    matches on the `2026-08-19-` date slug — which never fired inside these two ranges
    anyway — but applies one rule to every relative target: prepend `../` per level of
    depth, except a link into the output directory itself, which becomes a bare sibling
    filename. `interfaces/input-data-model.md` read from `docs/specs/interfaces/` resolved
    to `docs/specs/interfaces/interfaces/…`; it now resolves to the file itself
- [x] **T4 (P1, human: ~2 days / CC: ~60min)** — spec — Write §1–§5 (carrier network, graded heat, units, two-tier temporal)
  - Surfaced by: PD1, PD2 and the unit-spine split
  - Files: `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md`
  - Verify: `make docs-check`; diagrams regenerate
  - **Done for §1, §2, §3 and §5.** 9 entities at the time (22 after T17 and the §3 consolidation), C1–C12, S0–S9
  - Satisfies the diagram parser contract: all 9 entities and their 72 fields parse, 19 foreign-key arrows resolve. **Re-verified after T17 added §3.10 and §3.11:** 11 entities, 94 fields, 29 FK arrows
- [x] **T5 (P1, human: ~4h / CC: ~20min)** — spec — Define V1b and the carrier-equivalent configuration
  - Surfaced by: V1's step 4 compares per-technology capacity by period, which does not exist under a unit/carrier model, so parity needs a second hop
  - Files: spec §10.2, §10.3
  - Verify: the configuration is stated as precisely as §5.4's pre-D11 cost baseline
  - **Done.** §10.2 states five conditions that hold together — one carrier per unit, no storage, no onsite generation, C10/C11/C12 inactive, no export
- [ ] **T6 (P1, human: ~3h / CC: ~15min)** — spec — Close failure mode #5 with a fallback tier and an evidence label
  - Surfaced by: Failure modes table — a premise matching no archetype fails silently, untested and unhandled
  - Files: spec §3.17 (`archetype_coefficient`), §8 (evidence fields)
  - Verify: every output row carries an archetype evidence tier
  - **Partly done.** §3.17's `evidence_tier` declares the `fitted` → `substituted` → `default` ladder and §10.5 records the handling. What remains is §8, where the field has to appear on the output rows
  - Note: this was two gaps. The other, ψ extrapolated outside its fitted design-ratio range, was **removed** by PD2 rather than tested for — a fixed sizing ratio leaves nothing to extrapolate along
- [ ] **T7 (P1, human: ~4h / CC: ~20min)** — spec — New tie-break key, price-wedge rule, recomputed §9.1 arithmetic
  - Surfaced by: the carrier balance manufactures new solver degeneracy, and a tie-break keyed on `technology_code` no longer has a key to read
  - Files: spec §9, §10 (V21)
  - Verify: V21 stated at load scope
  - **Partly done.** The tie-break key and the price-wedge rule are stated in §5.5 and §9.3, and V21 is at load scope in §10.3. What remains is §9.1's per-premise variable and constraint arithmetic, recomputed from the unit, carrier-flow and storage families
- [ ] **T8 (P1, human: ~2 days / CC: ~45min)** — data — Group A + B taxonomy split and collapse
  - Surfaced by: `technology_category` conflates carrier, device and abatement across 397 rows
  - Files: `docs/notes/data/emissions_source_classification.csv` and successors
  - Verify: `make data-check`; explicit 397-row reconciliation, zero orphans
- [ ] **T9 (P1, human: ~2 days / CC: ~45min)** — data — Group C decarbonisation options: the missing option→unit join, plus the hybrid-unit set and its bill of materials
  - Surfaced by: options are keyed to CaRB3 `process_id` and technologies to `output_commodity`, and no join exists. PD2 adds hybrid units, which have no representation in a library where all 134 options are demand-side
  - Files: `decarbonisation_options_library.csv`, `process_decarbonisation_options.csv`, new `unit_bill_of_materials`
  - Verify: `make data-check`; 130 used options all resolve; the 12 legitimately optionless processes stay exactly 12; every hybrid unit's BOM shares sum to 1 and reconcile to its capex (V20 b)
- [ ] **T10 (P1, human: ~1 day / CC: ~30min)** — spec — Rewrite the **cement** worked example, adding the PV/battery/connection section
  - Surfaced by: the cement premise is the parity case and has to be walked end to end
  - Files: `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-cement.md`
  - Verify: every asserted number recomputes; A6–A9 actually walked
  - Scope: this example covers the mass denominator (D5), tier-1 vintage, stranding and the CCS capture unit. It **cannot** show graded heat, unit competition or CHP; that is T16
- [ ] **T16 (P1, human: ~1 day / CC: ~30min)** — spec — Write a second worked example on a **food & drink** site, exercising the carrier mechanism
  - Surfaced by: cement has only `ICMCLK` and `ICM`, so no `LTH`/`STM`/`DRY`/`SPC`. A cement example is structurally blind to the carrier mechanism (spec §13)
  - Files: `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-food-drink.md`
  - Verify: shows `IFDLTH`'s 8 fuel-variant technologies collapsing to 3 units; a 120 °C duty with boiler / CHP / heat pump / electric competing under C10; an `IFDDRY` reject-heat leg feeding a heat pump (B5); CHP producing heat **and** electricity into the carrier balance
  - **Depends on:** T8 (Group A + B taxonomy), since the collapse it displays must be the real one, **and T17** — the example asserts a 120 °C duty and a CHP default, neither of which exists in any table today
- [ ] **T17 (P1, human: ~3 days / CC: ~90min)** — data + spec — Give every process a duty family and a heat grade
  - Surfaced by: the input-data audit ([notes/16](../notes/16_input_data_readiness.md)). The model decides what a site may build by walking `process → duty → eligible units`, and **only the first link exists**. No temperature or grade column exists in any of the ten CaRB3 reference files; the 376 register rows carry no duty family
  - Files: spec §3.3 (**done** — `activity_process_duty_profile`), `docs/notes/data/carb3_comit_process_crosswalk.csv`, `docs/notes/data/activity_process_duty_profile.csv`, `validate_carb3_data.py`
  - Verify: `make data-check`; `duty_share` sums to 1.00 ±0.015 per (activity, set, process); **`grade_rank` non-nullable wherever the carrier is gradeable**; every row resolves to the register
  - **Seedable, but not scriptable.** COMIT's 94 `process_commodity` codes already encode the family as a suffix — `IFDLTH` is Food & Drink · Low-Temperature Heat — giving `LTH` 11, `OTH` 11, `MOT` 10, `SPC` 8, `HTH` 7, `DRY` 6, `STM` 6, `REF` 2, `HRS`/`NEUOTH` 1 each. But `carb3_comit_crosswalk.csv` is **activity-level** (55 rows → 16 COMIT sectors) and does not join CaRB3's 376 processes to those 94 codes. That process-level crosswalk is the missing artefact
  - **Scope honestly:** by crosswalk coverage, 228 register rows sit in `direct` activities (seedable with review), 57 in `catch-all`/`partial`/`generic` (partly), and **91 in `absent`/`gap`/`weak`/`ambiguous` — those have no COMIT analogue and need first-principles classification**
  - Temperatures do exist in the repo but on the **supply** side: 28 rows of `decarbonisation_options_library.duty` and 45 of `process_decarbonisation_options.notes` carry °C values, against **3 incidental** occurrences in the register. Useful as corroboration, not as a source
  - **Blocks T16.** Feeds T13 — A4's carrier-mix rule chooses between units serving a duty, and without duty families there is nothing for a unit to be eligible for
- [ ] **T18 (P1, human: ~2 days / CC: ~45min)** — data — Build the default installed-unit table, so existing CHP stops being invisible
  - Surfaced by: the same audit. A column scan of all ten reference files found **no column** matching generation, capacity, storage, onsite, import, export or self-consumption. Today a Chemical Works with a 20 MW CHP and one without are the same row
  - Files: spec §3.16 (**done** — `activity_default_unit`), `docs/notes/data/activity_default_unit.csv`, `validate_carb3_data.py`
  - Verify: `make data-check`; `default_share` sums to 1.00 ±0.015 per (activity, set, process, duty_family); every `(unit_id, activity, process_id)` has a `unit_eligibility` entry; no row asserts a unit the optimiser could not build
  - **Has a real public source**, unlike Group D1's roof-area problem: **DUKES Table 7** and the **CHPQA register** give existing industrial CHP capacity and output by sector. `evidence_tier = sector_statistic` is reserved for figures traceable to those
  - Today CHP appears only inside process *names* — `Chemical Works / utilities_steam` is "Steam system and utilities (boiler/CHP losses…)". The energy lands on the steam duty; nothing says whether a boiler or a CHP produces it, and **no electricity co-product exists**. `unit_input_output` already supplies that co-product once the unit is named, which is why this entity carries no electricity field
  - **Depends on T17** (a unit cannot be assigned to a duty that does not exist) and **T8/T9** (the unit library it references)
- [ ] **T19 (P2, human: ~4h / CC: ~15min)** — spec — Define the site-composition archetype and give `archetype_id` a referent
  - Surfaced by: the audit — `archetype_coefficient` is keyed `(archetype_id, unit_id)` but **no entity anywhere defines what an `archetype_id` is**. Group D4 lists the definitions as missing data; nothing owns the schema
  - Files: spec §3, §9.2
  - Verify: every `archetype_coefficient` row resolves to a defined archetype; the `activity × load shape × schedule × size` dimensions are enumerated
  - **Name it away from the Tier A sense.** The specification already uses "archetype" for the offline dispatch archetype (~200–400 of them, S0). A site-composition archetype is a different object, and reusing the word is the collision this repository has already hit three times

- [x] **T11–T12 (P3)** — docs — Register the documents in `docs/notes/README.md`
  - Files: `docs/notes/README.md`
  - Verify: the index lists the specification, its companions and the archive
  - **Done.** The defects found in the archived documents are recorded in
    [`archive/README.md`](archive/README.md) rather than fixed, since those documents are
    frozen and one of them is the parity baseline
- [ ] **T13 (P1, human: ~1 day / CC: ~30min)** — spec — Write §4's numbered pseudocode for A1–A9
  - Surfaced by: A4 is under-determined once a unit may burn a carrier mix, and A7's relaxation ladder had no rung for C10, C11 or C12
  - Files: spec §4, §8 (`mix_evidence_tier`), §10 (V23)
  - Verify: V1b has a determinate baseline to compare against
  - **Partly done.** §4 now states each algorithm's responsibility, A4's three-tier carrier-mix rule (§4.1) and A7's ladder order (§4.2), and V23 asserts the tiering. What remains is the numbered pseudocode for A1–A9 and the `mix_evidence_tier` field in §8
- [x] **T14 (P1, human: ~1 day / CC: ~30min)** — spec — Write §7 (emissions attribution under carriers)
  - Surfaced by: the sign convention survives a move to carriers but the *attribution* does not, and attribution is the part that matters
  - Files: spec §7, §10 (V22)
  - **Done.** §7 states the six accounting rules, the primary-carrier attribution rule that stops double-counting, and why recovered heat is emissions-free. V22's three legs are in §10.3
  - Verify: V22's three legs pass on a `gas → boiler → heat → dryer` chain including a recovered-heat leg
- [ ] **T15 (P2, human: ~2h / CC: ~10min)** — spec — Add the G4 Tier A scale gate and the V20 (e) concavity leg
  - Surfaced by: Review issues 7 and 8 — the archetype build has no cost gate, and the interpolation-safety argument is unchecked
  - Files: spec §9.2, §10 (V20)
  - Verify: G4 has a stated wall-clock budget; V20 (e) runs at load scope
  - **Partly done.** G4 is in §9.2 and V20 (e) is in §10.3. What remains is the wall-clock budget number itself, which needs a measurement

---

## NOT in scope

| Deferred | Why |
|---|---|
| Any change to `R/` (18,126 lines, 64 files) | This specification targets a system that has not been built. COMIT is what V1 validates against, so touching it now buys nothing and risks the baseline. |
| Full 8760-hour dispatch in the per-premise LP | Attacks §9's tractability argument directly at stock scale. Tier A exists precisely to avoid it. |
| Seasonal (inter-period) storage state | Matters for hydrogen, barely for industrial heat and batteries. Add only if a decision turns on it. |
| RFNBO / LCHS hourly temporal-correlation compliance | Structurally inexpressible in an annual model. Stated as a boundary in spec §2.3; not modelled. |
| Rewriting anything under `docs/specs/archive/` | Frozen by design; see *Do not touch* above. |
| Retiring the COMIT-parity baseline specification | It is what V1 and V1b are anchored to, and it stays runnable. It lives in `docs/specs/archive/` — archived, not retired: still read and still regenerated, just out of the main path. |
| CI wiring beyond a Makefile | No `.github/` exists. A Makefile target is the honest first step; CI is a separate call. |

---

## Verification

```bash
# 1. Tooling baseline — must be green BEFORE any data edit
make data-check          # validator on unmodified docs/notes/data/
make docs-check          # both generators reproduce the published outputs byte-identically

# 2. After the spec work
python3 docs/notes/examples/build_interface_docs.py --all --check
python3 docs/notes/examples/build_spec_flow_diagram.py --all --check   # --check new in T2

# 3. After the data migration
make data-check          # share sums, band ordering, reference resolution,
                         # option/register key integrity, enum domains
                         # expect: 130 used options resolve, exactly 12 optionless processes

# 4. Manual, and not automatable
#    - 397-row reconciliation: every technology maps to exactly one (unit, carrier binding)
#    - every worked-example number recomputes by hand from the stated inputs
#    - the archived baseline still generates its interface docs unchanged
```

**The order matters.** Step 1 on today's data is what makes any later red attributable to
the migration rather than to a pre-existing condition.
