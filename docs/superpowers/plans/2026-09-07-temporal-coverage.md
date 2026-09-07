# Temporal Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the CaRB3 site energy system hold several years of measured history for a premise, and record when that premise's processes actually changed, without either one leaking into the annual LP.

**Architecture:** Two additive changes to §3 of the live implementation specification, each closed by a validation test and guarded by `make check`. (1) A year enters the primary key of the measured-history entities, and `premise_record.data_year` is promoted to *the base year*: the one year the model reads, with a nearest-year substitution ladder for carriers metered off that vintage. (2) `premise_process_detail` gains a validity interval, so a premise's process list is stated **as at** a year. A third capability, a declared *forward* process switch, was scoped, reviewed, and **deferred**: see *Deferred, and why* below. It is blocked on §5, not on §3.

**Tech Stack:** Markdown specification (language-agnostic: typed entities, numbered rules, maths). Stdlib-only Python generators (`build_spec_flow_diagram.py`, `spec_docs_config.py`) driven by `spec_docs.config.json`. `make check`. **`pandas` is not installed.** Nothing in `R/` changes.

---

## Prerequisite (done)

This worktree was branched from `origin/main`, which does not carry `docs/specs/`. The branch
has been fast-forwarded to `fork/main` (`f691289`), and `make check` is green there:

```
diagrams (site-energy-system) are in step with the spec — 22 entities, 49 foreign keys
CaRB3 data is consistent (12 blocking checks passed).
```

PRs go to `AlexandreLab/comit`, not the upstream org repo.

---

## What is missing, precisely

| # | Gap | Evidence in the live spec | Status |
|---|---|---|---|
| 1 | **No multi-year history.** `premise_energy` is keyed `(premise_id, carrier_id, connection_id)` and `data_year` is a non-key column, so a second year of the same carrier collides on the key. `premise_throughput` has no year column. `premise_operating_profile` and `premise_weekly_profile` have none either, yet §3.12's consistency rule already blames divergence on "a vintage mismatch between **the profile year** and `data_year`", naming a field that does not exist | §3.1.1, §3.1.2, §3.12, §3.14 | **T20** |
| 2 | **No observed process change.** `premise_process_detail` is keyed `(premise_id, process_id)` with no validity dates and asserts a *complete* process list, so it can only describe one undated snapshot. A site that ran A until 2023 and B since cannot be stated, and A4 would back-solve a blended plant that never existed | §3.10 | **T21** |
| 3 | **No declared forward change.** `process_duty` is keyed by `period`, but nothing upstream varies with period, so A2 expands one process set flat across all periods. Separately, C7 ("Known changes") has no backing entity anywhere in §3 | §3.2, §3.3, §3.9, §5.5 C7 | **Deferred (T24)**, blocked on **T23** |

---

## Review outcome, 2026-09-07

Three independent reviews ran against the first draft of this plan: a plan-document reviewer,
a modelling-correctness reviewer, and Codex as the outside voice. They converged.

**Verdict: T20 and T21 proceed with the fixes below. The declared forward switch is deferred.**

Two of the three reviewers independently found the same root cause, and it is not in §3:

> §5.1 defines $Q$ as "Duties at this premise" with **no period index**, and C1 is written
> $\forall q \in Q$. A duty created part-way through the horizon is therefore never
> constrained. A declared switch would shed the old process's duty and the LP would never be
> required to serve the new one, so the premise's cost and emissions both collapse and the
> switch reads as total decarbonisation.

Two further claims in the deferred design turned out to be assertions the LP does not
deliver, both from the same place: **C4 and C6 exist in §5.5 as prose only, with no algebra.**
The stranding rule (retire the displaced plant, pay $\xi$) is not produced by C1 to C4 at all,
because C2 only bounds $z_{u,t} \le a_{u,t}\gamma_u\alpha_u$ from above. Idling at $z = 0$ with
capacity intact is always feasible, so the LP simply compares fixed opex against the write-off
and, for near-new plant, keeps it standing and never pays. That is exactly the case D11 exists
for. And the C6 ramp exemption was written per unit, while which unit serves a new duty is the
LP's choice, so the exemption set is a function of the solution and constraints are built
before solving.

### Fixes folded into T20 and T21

| From | Fix | Where |
|---|---|---|
| Modelling review, item 6 | **Off-vintage carriers must not be dropped.** Promoting `data_year` into the key turns a carrier metered on a different vintage into history, so it reads as "not assessed" and A4 back-solves no plant for it. A nearest-year substitution ladder, on the §3.17 pattern, is required | T20 Step 4 |
| Modelling review, item 7 | **V25 was insufficient and four readers were unedited.** §7.6's reconciliation, the S0 archetype match, and §3.11's rejection path all read a year and none were touched | T20 Steps 7, 8, 11 |
| Plan review | **Three inconsistent statements of the base-year rule.** One rule, stated once, cited everywhere else | T20 Step 3 |
| Plan review | **The label-range safety net does not run for this spec.** See the boxed warning in T20 Step 9 | T20 Step 9, T21 Step 7 |
| Plan review | **T21 falsifies two paragraphs it left standing** | T21 Steps 3, 5 |
| Plan review | **§1.6's prose count and `docs/notes/README.md` go stale** | T20 Step 9, T22 |
| Modelling review, item 11 | **§3.15's foreign key target stops being unique** | T21 Step 5 |
| Architecture review | **The base year is per premise; periods are global** | T20 Step 3 |
| Step 0 | **Name the pattern.** `valid_from_year` / `valid_to_year` is slowly-changing-dimension type 2 valid-time modelling | T21 Step 2 |
| Second-round review | **Three "one row per …" intro sentences were falsified by the key change** and not edited: §3.1.1, §3.1.2, §3.14 | T20 Steps 4, 5, 6 |
| Second-round review | **`profile_year_unmatched` had two different triggers.** The base-year-missing case is now `profile_base_year_missing` | T20 Steps 3, 6 |
| Second-round review | **`valid_from_year` is required on optional intelligence with no stated convention for an unknown start year** | T21 Step 2 |
| Second-round review | **V25 asserted parameters and the solution, but §7.6's reconciliation is a report** | T20 Step 11 |

### Deferred, and why

The declared forward switch is not dropped, and none of its design work is lost. It is
registered as **T24** in the delivery document, blocked on **T23**, and the reason is stated
there in full: it needs §5.1's $Q$ period-indexed and C4 and C6 written as mathematics. The
entity design that survived review, and should be picked up when T23 lands, is:

- `premise_process_transition`, keyed on the premise and a transition id, carrying a
  **calendar** `transition_year` (not a period index; §5.1 already defines
  $y_t = y_{t_0} + \Delta t$ and every other year field in §3 is a calendar year), an explicit
  `to_process_set_id`, `share` stated against the **base-year** quantity with the sum rule
  cumulative in $t$, and `duty_ratio` **per duty family** rather than as one scalar, because a
  single scalar scales magnitude while composition comes from activity-level reference data
  shared by every premise.
- Rules the reviews showed are load-bearing: the to-process must belong to the premise's
  activity (the §3.2 `invalid_process_set` analogue), must have at least one `unit_eligibility`
  row, and must not silently lower `grade_rank` for a duty family, which would reintroduce
  §10.5's failure mode 6 through a legal, validated input.
- The C6 exemption defined on the **duty**, not the unit: suspend C6 for every $u \in U_q$
  where $D_{q,t}$ moves by more than $\sigma$ at a transition period. That depends only on $D$
  and $U_q$, both known at build time.
- `process_duty.evidence_tier` gains `declared_transition`, and §10.2's carrier-equivalent
  configuration gains a sixth condition, "no declared transitions", or V1b fails on any parity
  site that acquires one.

---

## Pre-existing defects surfaced by this work, and not fixed here

Recorded because they were verified, not to expand scope. Each is a candidate delivery task.

| # | Defect | Evidence |
|---|---|---|
| 1 | **§5.6 and §5.3.1 do not exist.** §5.6 (C11's peak-rebuild method) is cited at lines 643, 657, 929 and 1084; §5.3.1 (D11's vintage fallback ladder) at lines 226, 762 and 793. §5's headings run 5.1 to 5.5 only, and the document's status line says §5 is written | `grep -n "^### 5\."` returns 5.1, 5.2, 5.3, 5.4, 5.5 |
| 2 | **$Q$ is not period-indexed** (§5.1 line 946), so C1 cannot constrain a duty that appears mid-horizon | §5.1, §5.5 C1 line 1026 |
| 3 | **$z_{u,t}$ is not duty-indexed.** C1 sums $z_{u,t}$ over $U_q$ for each duty. §3.5 makes service units family-keyed, so one boiler can sit in two $U_q$ at one premise and its single activity variable is credited in full against both duties | §5.2 line 967, §5.5 C1, §3.5 line 460 |
| 4 | **C4 and C6 are prose only**, with no algebra, so nothing that depends on their behaviour can be tested | §5.5 lines 1039, 1046 |
| 5 | §3.3's intro points at "§3.7" for `process_duty`, which is §3.9 | §3.3 line 367 |

Defects 1 to 4 are what T23 exists to close. Defect 5 is a one-word fix and can ride along with
any spec commit.

---

## Design decisions taken in this plan

| # | Decision | Why, and what was rejected |
|---|---|---|
| 1 | **One base year is read; every other year is held, not read.** `premise_record.data_year` names the base year | Letting the model consume the series collides with §5.1's annual model and with A4's back-solve, which is only determinate against a single snapshot. Holding history costs nothing and buys trend evidence, a reconciliation target and an audit trail |
| 2 | **A carrier metered off the base year substitutes from its nearest year rather than disappearing** | The straight reading of decision 1 silently deletes evidence that §3.1.1's current wording exists to preserve. §3.17 already uses `fitted` → `substituted` → `default` for exactly this shape of problem |
| 3 | **Process validity is an interval on `premise_process_detail`, not a second history table** | §3.10 already asserts completeness for a premise. A parallel history table would give two places to state the same list and they would disagree, which is the failure §3.16 avoids for CHP electricity |
| 4 | **A missing base-year row is a skipped-and-reported check on optional intelligence, and a rejection only on required entities** | §3.11, §3.12 and §3.14 are optional, where zero rows is normal. Rejecting a premise for holding 2019 and 2021 emissions but not 2020 would discard the evidence entirely |
| 5 | **The forward switch is deferred, not redesigned** | Three reviewers found the blocker is in §5, not §3. Shipping the entity anyway would put a capability claim in the document that §5 cannot honour, which is the "legacy-equivalence claim must enumerate every condition" failure this repo has already had |

### Open question, default stated

**Is history ever read? Default taken: no.** It is held for validation, reconciliation and
reporting. If duty growth is later derived from a trend, that is a new decision and a new task,
not a widening of this one.

### Settled

**A declared switch strands the old plant like any other early retirement, no exemption**
(confirmed 2026-09-07). Recorded here because it survives into T24, and because review showed
the LP does not currently *produce* that behaviour: it is a rule T23 has to make true, not a
rule §5 already delivers.

---

## What the change actually does

```
  WHAT THE STOCK MODEL SUPPLIES                WHAT THE MODEL READS
  ───────────────────────────────              ─────────────────────
  premise_energy                                     base year only
    (premise, carrier, connection, YEAR)  ──┐          │
  premise_throughput                        │          │
    (premise, carrier, YEAR)                ├── A1 ────┤ selects data_year,
  premise_operating_profile                 │          │ substitutes nearest
    (premise, connection, YEAR)             │          │ where a carrier has
  premise_weekly_profile                    │          │ no base-year row
    (premise, connection, vector, YEAR, …)  │          │
  premise_measured_emissions                │          ▼
    (premise, YEAR, category, ghg)        ──┘   A3 ─► carriers
                                                A4 ─► capacity, mix, vintage
  premise_process_detail                          │
    (premise, process, VALID_FROM)  ── A2 ────────┤ rows valid at the base
                                                  │ year are the complete list
  every other year  ────────────────────────────► held. Reported as trend and
                                                  reconciliation evidence.
                                                  Never enters the LP. (V25)
```

The LP is untouched. No new variables, no new constraints, no change to §5.

---

## File Structure

### Modify

| Path | Change |
|---|---|
| `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md` | §1.4 label ranges, §1.6 (D12 + prose count), §3.1, §3.1.1, §3.1.2, §3.10, §3.11, §3.12, §3.14, §3.15, §3.17, §4 (A1–A4), §7.6, §10.3 (V24–V26), §10.4, §10.5 |
| `docs/specs/2026-08-28-carb3-site-energy-system-delivery.md` | Add T20–T24 to *Implementation Tasks*; add this plan to *Files → Create* |
| `docs/notes/README.md` | Register this plan; refresh the four stale facts in the live-spec row |

### Regenerate, never hand-edit

| Path | Generated by |
|---|---|
| `docs/specs/diagrams/spec_entities.md` | `build_spec_flow_diagram.py` via `make docs-build` |

### Do not touch

Everything under `docs/specs/archive/`. Those documents are frozen; one is the COMIT-parity
baseline that V1 validates against. **No entity is added or renumbered by this plan**, so the
§3.1 to §3.15 section-number alignment with the baseline is untouched and the entity count
stays at 22.

Nothing in `R/` changes.

---

## Task Sequencing

| Task | In this plan | Depends on | Why |
|---|---|---|---|
| T20 multi-year history | yes | — | Defines "the base year", which T21 references |
| T21 process validity interval | yes | T20 | "Valid at the base year" has no meaning until the base year is named |
| T22 register the work | yes | T20, T21 | Describes what was actually built |
| T23 complete §5 | no, registered | — | Independently valuable; blocks T24 |
| T24 declared forward switch | no, registered | T23 | See *Deferred, and why* |

T20 and T21 each commit on their own and leave `make check` green.

---

### Task 20: Multi-year measured history

**Files:**
- Modify: `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md` — §1.4, §1.6, §3.1, §3.1.1, §3.1.2, §3.11, §3.12, §3.14, §3.17, §4, §7.6, §10.3, §10.4, §10.5
- Regenerate: `docs/specs/diagrams/spec_entities.md`

- [x] **Step 1: Confirm the green baseline before touching anything**

Run: `make check`
Expected: four green lines ending `CaRB3 data is consistent (12 blocking checks passed).`
If it is not green *before* the edit, stop. A later red would not be attributable.

- [x] **Step 2: Promote `data_year` to the base year in §3.1**

Replace the `data_year` row's validation cell in `premise_record`:

```
| `data_year` | integer | year | yes | — | **The base year.** The one year the model reads, per §3.1.1's base-year rule. Where it differs from the scenario's start year the offset is recorded and reported, never silently absorbed |
```

- [x] **Step 3: Write the base-year rule once, in §3.1.1**

The rule is stated here and cited from §3.1.2, §3.11, §3.12 and §3.14. Do not restate it.
Three separate wordings in the first draft of this plan is what this step exists to prevent.

````
**Rule (the base year, and history).** `premise_record.data_year` is the premise's **base
year**. Exactly one row per key carries it, and that row is the only one any algorithm
reads. Rows at other years are **history**: held for reconciliation, trend evidence and
reporting, and never consumed by the model (V25).

The rule binds differently on required and optional entities, because zero rows is normal
on the optional ones:

| Entity | Missing base-year row |
|---|---|
| `premise_energy` (§3.1.1) | Substitute from the nearest year, see below |
| `premise_throughput` (§3.1.2) | Substitute from the nearest year, see below |
| `premise_measured_emissions` (§3.11) | The reconciliation of §7.6 is **skipped and reported** as `emissions_year_unmatched`. Never a rejection: this entity is optional intelligence and rejecting the premise would discard the evidence |
| `premise_operating_profile` (§3.12), `premise_weekly_profile` (§3.14) | No profile is read, and the premise is **reported** as `profile_base_year_missing`. Never a rejection |

A duplicate `(key, year)` is rejected with reason `duplicate_year_row` on every entity.

**Rule (the base year is per premise; periods are not).** Stock data is mixed vintage, so
two premises may hold different `data_year` values while the model's periods are global.
The premise's base-year quantities are read as representing the scenario's start period,
and the offset in years is recorded on the premise's output rows. Stating the offset is
what stops a carbon price at one period being silently applied to two different calendar
years without trace.
````

- [x] **Step 4: Add `data_year` to `premise_energy`'s key, with the substitution ladder (§3.1.1)**

Change the `data_year` row to a required key part:

```
| `data_year` | integer | year | yes | PK part | The year this quantity was measured. One row per carrier per connection **per year**. See the base-year rule above |
```

Amend the existing "one row per carrier per connection" rule to name the year, and add the
ladder. **This step is why the key change is safe.** Without it, `data_year`'s current
meaning ("set only where a carrier is metered on a different vintage") is reversed: a site
whose gas is metered 2022 and electricity 2023 against a 2023 base year would lose the gas
entirely, A4 would back-solve no gas-burning plant, and the site's baseline emissions would
fall.

````
**Rule (a carrier metered off the base year substitutes; it does not vanish).** Where a
carrier has no row at the base year but has rows at other years, the **nearest** year is
used, ties resolving to the later one, and the substitution is recorded as
`year_evidence_tier = substituted` on the premise's output rows. Only a carrier with no row
at any year is "not assessed", and only then is the premise reported as having incomplete
carrier coverage (§8).

This is the §3.17 pattern applied to a new kind of evidence: `base_year` where the row is at
`data_year`, `substituted` where it came from another year, `absent` where there is none. A
premise running on a substituted vintage must never be mistaken on paper for one running on
a base-year reading.
````

The absence rule already in §3.1.1 stays exactly as written. `not_consumed` at any year still
means the carrier is known not to be consumed.

- [x] **Step 5: Add `data_year` to `premise_throughput` (§3.1.2)**

The entity has no year column today. Insert after `quantity`:

```
| `data_year` | integer | year | yes | PK part | The year this throughput was measured. The base-year row, or its substitute, is what D5's mass denominators are computed from. See §3.1.1's base-year rule |
```

Do not restate the rule. Cite it. `premise_throughput` is required only for activities
carrying a mass-denominated process, and that is unchanged.

- [x] **Step 6: Give the two profile entities a year (§3.12, §3.14)**

Both carry no year today, yet §3.12's consistency rule already blames divergence on "a
vintage mismatch between the profile year and `data_year`", a field that does not exist.

To **§3.12 `premise_operating_profile`**:

```
| `profile_year` | integer | year | yes | PK part | The year the statistics were derived from. Closes the vintage-mismatch rule below, which until now named a field this entity did not have |
```

To **§3.14 `premise_weekly_profile`** (note the different validation text; the rule it closes
lives in §3.12, not here):

```
| `profile_year` | integer | year | yes | PK part | The year the series was drawn from. One representative week per season **per year**; the model reads the base year, per §3.1.1 |
```

In §3.12's consistency rule, reconcile **like years**: the profile is checked against
`premise_energy` at the same year, at every year for which both sides exist, and where no
energy row exists at a given `profile_year` that year's check is skipped and reported as
`profile_year_unmatched`. That is a different condition from a premise having no profile at
the base year at all, which is `profile_base_year_missing` in the §3.1.1 table. Two
conditions, two codes: one code for both is what the first draft had, and it makes the
report unreadable.

- [x] **Step 7: Pin the two readers that are not A3 or A4**

Both were missed in the first draft, and both would silently consume a non-base year.

**§3.17 / S0, the archetype match.** §2.2 shows `premise_operating_profile` and
`premise_weekly_profile` feeding the archetype layer, which emits ψ, β, χ, ε and therefore
moves C11 and the objective. Add one sentence to §3.17: the archetype match reads the base
year's profiles, on §3.1.1's rule, and a substituted vintage is carried into
`evidence_tier`.

**§7.6, the emissions reconciliation.** It currently reads "reported totals reconcile against
`premise_measured_emissions` wherever it exists", with no year selector, against an entity
this task makes multi-year. Amend to: reconciliation is against the **base-year** row; other
years are a reported trend and never a calibration target; a premise with rows but none at
the base year is reported `emissions_year_unmatched` and not reconciled.

**§5.6 cannot be pinned, because it does not exist.** C11's peak method is cited four times
and never written (see *Pre-existing defects*, item 1). Add a one-line note under §3.14
recording that when §5.6 is written it must select the base year, so the gap is visible to
whoever writes it rather than being discovered by a wrong connection size.

- [x] **Step 8: Amend §3.11's `emission_year` (§3.11)**

Change the validation from "Should match `premise_record.data_year`" to:

```
| `emission_year` | integer | year | yes | PK part | Multi-year. §7.6 reconciles against the base-year row; other years are a reported trend. A premise with no base-year row is reported, never rejected. See §3.1.1 |
```

- [x] **Step 9: Add D12 (§1.6), fix the prose count, widen the label ranges (§1.4)**

Append to §1.6's table:

```
| **D12** | Measured inputs are a time series; exactly one year is the base year, and only that year is read | History becomes available for reconciliation, trend evidence and audit without touching the annual LP or A4's back-solve | A base year must be named per premise, a substitution ladder for off-vintage carriers, and every history row is data nobody reads today |
```

§1.6 opens **"Eleven decisions fix the shape of the model."** Change it to **"Twelve"**. This
is verbatim the first entry in CLAUDE.md's *Things that have gone wrong here*, and nothing in
`make check` catches it.

In §1.4, change `D1`–`D11` to `D1`–`D12` and `V1`–`V23` to `V1`–`V25`. **T21 widens it again
to `V1`–`V26`; do not defer it there.**

> ### ⚠ The label-range cross-check does NOT run for this specification
>
> An earlier draft of this plan claimed the generators cross-check §1.4's ranges and that a
> stale range fails `make docs-check`. That is false twice over. `label_families()` is called
> from exactly one place, `build_interface_docs.py:137`, and `interfaces.enabled` is `false`
> for `site-energy-system` because §8 is unwritten, so it never runs for this spec.
> `build_spec_flow_diagram.py` never calls it. And even where it does run,
> `label_note.families` carries only `prefix` and `gloss`, so `spec_docs_config.py:114-131`
> checks family *presence*, never range values.
>
> **Widen the range by hand in the same commit that adds the label. Nothing will tell you if
> you forget.** The domain-partition check cited elsewhere in this repo *is* real; this one is
> not.

- [x] **Step 10: Update A1 to A4 (§4)**

- **A1** gains: resolve the base year, apply the §3.1.1 substitution ladder, and report
  `duplicate_year_row`, `profile_year_unmatched` and `emissions_year_unmatched`.
- **A3** gains: reads the base year only; history rows are carried to reporting untouched.
- **A4** gains: back-solves from the base year only, and a substituted carrier vintage is
  carried into the mix evidence.

- [x] **Step 11: Add V24 and V25 (§10.3), wire §10.4 and §10.5**

```
| **V24** | load + premise | yes | One measured row per key at the base year or a recorded substitution, no duplicate `(key, year)`, and the optional entities report rather than reject |
| **V25** | premise | yes | **History is never read.** Adding history rows at years both **before and after** the base year leaves every §5.3 parameter, every constraint coefficient and the solution identical to 1e-9 |
```

V25's "before **and** after" is load-bearing. A reader that takes `max(data_year)` passes a
test that only adds older years.

§10.4 gains:

```
  base-year selection and substitution ───▶ V24               load+premise
  history isolation from the model     ───▶ V25               premise
```

§10.5 gains failure mode 9:

```
| 9 | Two years of the same carrier are averaged, or the later one silently wins, so the back-solve runs on a snapshot that never existed. Or a carrier metered off the base year is dropped and the site's baseline emissions fall | V24 + V25 | Load and premise assertions |
```

- [x] **Step 12: Bump every touched section's `*Section last updated:*` line to `2026-09-07`**

Touched `##` sections: §1, §3, §4, §7, §10. The line is load-bearing for the interface-doc
generator and must round-trip.

- [x] **Step 13: Regenerate and check**

Run: `make docs-build && make check`
Expected: `diagrams (site-energy-system) are in step with the spec — 22 entities, …`. The
entity count is **unchanged**; field and key counts rise.

- [x] **Step 14: Commit**

```bash
git add docs/specs/2026-08-28-carb3-site-energy-system-implementation.md docs/specs/diagrams/spec_entities.md
git commit -m "feat(spec): hold several years of measured history, read one base year (T20)"
```

---

### Task 21: Observed process change

**Files:**
- Modify: `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md` — §1.4, §3.10, §3.15, §4, §10.3, §10.4
- Regenerate: `docs/specs/diagrams/spec_entities.md`

- [x] **Step 1: Add the validity interval to `premise_process_detail` (§3.10)**

Insert after `process_id`:

```
| `valid_from_year` | integer | year | yes | PK part | The year this process started at the premise. ≤ `premise_record.data_year`. A future year is rejected with reason `process_change_in_future`: a *planned* change is not an observation |
| `valid_to_year` | integer | year | no | — | The year it stopped. Absent ⇒ still running. ≥ `valid_from_year` if present |
```

The key becomes `(premise_id, process_id, valid_from_year)`.

- [x] **Step 2: Name the pattern, and restate completeness as at a year (§3.10)**

Replace the existing completeness rule:

````
**Rule (completeness, as at a year).** The rows valid at a given year are the premise's
**complete** process list for that year. A partial list would silently delete processes the
site runs and misstate its energy balance. A premise with any rows must have at least one
row valid at the base year, or it is rejected with reason
`no_process_valid_in_base_year`. If only fragmentary knowledge exists, use a named
`process_set_id` instead.

**Rule (intervals do not overlap).** For each `(premise_id, process_id)` the validity
intervals must be disjoint. Overlap is two contradictory statements about the same process
in the same year, and the premise is rejected with `process_intervals_overlap`.

This is valid-time versioning, the pattern usually called a slowly-changing dimension of
type 2. The two rules above are its standard obligations and are stated here so an
implementer does not reinvent them.
````

- [x] **Step 3: Rewrite the "On vintage (D11)" paragraph, which this task falsifies (§3.10)**

The paragraph currently justifies moving vintage into §3.15 because this table "is keyed
premise × process and **can hold exactly one year**". After Step 1 that is no longer true, and
leaving it standing makes the document contradict itself. Rewrite it to keep the real
argument, which is about *granularity*, not about keys:

````
**On vintage (D11).** When the plant was commissioned lives in `premise_process_vintage`
(§3.15), not here. The two answer different questions. This table says **which processes the
site ran, and when it ran them**; §3.15 says **when the plant serving a process was
installed**, one row per cohort. A works running two lines of the same process installed
decades apart, a 1998 kiln and a 2016 one, has one row here and two there. Averaging those
two commissioning years is the thing D11 exists to stop, and no interval on this table can
express them.
````

- [x] **Step 4: State what the history is, and is not, used for (§3.10)**

```
**On history.** A closed interval is evidence, not an input to the optimisation. It does two
jobs. It tells A2 and A4 which rows to read, only those valid at the base year, so a site
that changed route mid-history is not back-solved into a blended plant that never existed.
And it explains a step change in `premise_energy`'s history (§3.1.1) that would otherwise
look like a data error. The optimisation starts from the base year and never looks back.
```

Also scope §3.10's existing precedence rule: where `unit_id` is given it names the premise's
existing plant **for an interval valid at the base year**. A closed interval's `unit_id`
describes plant the site no longer has.

- [x] **Step 5: Fix what §3.15's reference means, and the justification that rests on it**

Two edits, and the first is easy to miss. §3.15 relates to §3.10 on `(premise_id, process_id)`,
which after Step 1 is **no longer unique**. Add:

```
**Rule (the reference is to a process, not to a row).** This entity's `(premise_id,
process_id)` names a process identity at a premise, not one `premise_process_detail` row.
Cohorts are read only for processes valid at the base year (§3.10). Plant serving a process
the site has stopped running is not incumbent capacity, and ageing it under D11 would strand
an asset that is already gone.
```

Then rewrite the "Why a separate entity from §3.10" paragraph, which asserts §3.10 "is keyed
premise × process": it is now keyed one field wider, and the real distinction is that §3.15 is
keyed finer still, per cohort, and asserts nothing about completeness.

- [x] **Step 6: Update A2 and A4 (§4)**

Both gain: reads only the `premise_process_detail` rows valid at the base year.

- [x] **Step 7: Add V26 (§10.3), wire §10.4, widen §1.4**

```
| **V26** | premise | yes | Validity intervals per `(premise_id, process_id)` are disjoint, at least one row is valid at the base year, and A2, A4 and §3.15's cohort read touch no row outside it |
```

```
  process validity intervals       ───▶ V26               premise
```

§1.4: `V1`–`V25` becomes `V1`–`V26`. By hand; see the warning in T20 Step 9.

- [x] **Step 8: Bump the touched sections' update lines, regenerate, check**

Run: `make docs-build && make check`
Expected: still 22 entities. Field count rises by two; the foreign-key count is unchanged.

- [x] **Step 9: Commit**

```bash
git add docs/specs/2026-08-28-carb3-site-energy-system-implementation.md docs/specs/diagrams/spec_entities.md
git commit -m "feat(spec): state a premise's process list as at a year (T21)"
```

---

### Task 22: Register the work

**Files:**
- Modify: `docs/specs/2026-08-28-carb3-site-energy-system-delivery.md`
- Modify: `docs/notes/README.md`

- [x] **Step 1: Add T20 to T24 to the delivery document's Implementation Tasks**

House format, matching T17 to T19: checkbox, priority, effort, lane, *Surfaced by*, *Files*,
*Verify*. T23 and T24 are registered **unstarted**, with their blockers stated:

- **T23 (P1)** — spec — Complete §5: write §5.6 and §5.3.1, period-index $Q$, give C4 and C6
  their algebra. *Surfaced by:* the 2026-09-07 review. Four citations point at a peak method
  that was never written, and C11 is what every connection-capacity answer depends on.
- **T24 (P2)** — spec — Declared forward process switch. **Blocked by T23.** *Surfaced by:*
  the third gap in this plan. The entity design that survived review is in
  `docs/superpowers/plans/2026-09-07-temporal-coverage.md`.

- [x] **Step 2: Add this plan to the delivery document's Files → Create table**

- [x] **Step 3: Refresh `docs/notes/README.md`**

It is the only index and it is maintained by hand. Four facts in the live-spec row go stale:
`D1`–`D11`, `V1`–`V23`, and the delivery document's task count. The §3 entity count of 22 is
**unchanged** by this plan; leave it alone.

**Count before writing a count.** Run the counts, do not carry them over:

```bash
grep -cE '^\| \*\*D[0-9]+\*\*' docs/specs/...-implementation.md   # design decisions: a count
grep -oE '\bV[0-9]+' docs/specs/...-implementation.md \
  | sort -t V -k2 -n | tail -1                              # validation tests: a RANGE, so take the max
grep -cE '^- \[[ x]\] \*\*T[0-9]' docs/specs/...-delivery.md       # delivery task rows: a count
```

`docs/superpowers/plans/` already holds two unregistered plan documents and the index has no
section for plans. Add one, and register all three.

- [x] **Step 4: Check and commit**

```bash
make check
git add docs/specs/2026-08-28-carb3-site-energy-system-delivery.md docs/notes/README.md docs/superpowers/plans/2026-09-07-temporal-coverage.md
git commit -m "docs: register the temporal-coverage tasks and the deferred switch work"
```

---

## Validation coverage

```
  RULE / READER                              GUARDED BY   SCOPE          STATUS
  ─────────────────────────────────────────────────────────────────────────────
  one base-year row per key             ───▶ V24          load+premise   planned
  duplicate (key, year)                 ───▶ V24          load           planned
  nearest-year substitution + tier      ───▶ V24          premise        planned
  optional entities report, not reject  ───▶ V24          premise        planned
  A3 / A4 read the base year only       ───▶ V25          premise        planned
  archetype match (S0) reads base year  ───▶ V25          premise        planned
  §7.6 reconciles at the base year      ───▶ V25 (recon leg) premise      planned
  history before AND after is inert     ───▶ V25          premise        planned
  §5.6 peak selects the base year       ───▶ (none)       —              BLOCKED: §5.6 unwritten
  validity intervals disjoint           ───▶ V26          premise        planned
  ≥1 interval valid at the base year    ───▶ V26          premise        planned
  §3.15 cohorts follow validity         ───▶ V26          premise        planned
  §1.4 label ranges match the spec      ───▶ (none)       —              NOT CHECKED, by hand
```

Two uncovered rows, both stated rather than hidden. §5.6 cannot be tested because it does not
exist; T23 closes it. The label range has no automated guard for this spec, which is why T20
Step 9 carries a warning box instead of a claim.

---

## Verification

```bash
# Before any edit. A red here is not attributable to this work
make check

# After each task
make docs-build          # regenerate spec_entities.md from §3
make check               # generators reproduce the published outputs

# Manual, and not automatable
#  - §1.4's label ranges match the labels the spec actually defines (no automated check)
#  - §1.6's prose count matches its table
#  - the entity count stays 22 and the §3.1-§3.15 alignment with the archive is unchanged
#  - every new rule names its rejection or report reason, in the style §3.1.1 already uses
```

---

## NOT in scope

| Deferred | Why |
|---|---|
| The declared forward process switch (T24) | Blocked on §5, not on §3. Three reviewers found that $Q$ is not period-indexed, so a mid-horizon duty is never constrained by C1. Full design preserved in *Deferred, and why* above |
| Completing §5 (T23) | Registered as its own P1 task. It is a rewrite of the authoritative section and outranks this plan, but it is a different piece of work |
| Fixing $z_{u,t}$'s missing duty index | Pre-existing defect 3. Real, verified, and larger than this plan. Belongs with T23 |
| Deriving duty growth from the held history | The open question's default is that history is held, not read. Reading it is a new decision |
| Any change to `R/` | This specification targets a system that has not been built |
| Multi-year `premise_weekly_profile` shapes beyond one per year | §3.12's rule against raw series stands: derived statistics cross the interface, never 17,520 points per premise per year |
| Retiring or renumbering anything in §3.1 to §3.15 | Section-number alignment with the frozen baseline is what makes V1b's comparison readable |

---

## What already exists

| Sub-problem | Already in the spec | Reused? |
|---|---|---|
| A year in a primary key | `premise_measured_emissions.emission_year` (§3.11) | Yes. T20 copies the pattern rather than inventing one |
| A substitution ladder with an evidence tier | `archetype_coefficient.evidence_tier` (§3.17): `fitted` → `substituted` → `default` | Yes. T20 Step 4 is the same shape |
| Period-varying inputs | `infrastructure_scenario`, `scenario_parameters` (§3.7, §3.8) | Not needed by T20 or T21 |
| A period-keyed duty | `process_duty.period` already in the PK (§3.9) | Waiting for T24. Nothing writes it today |
| Plant arriving at different dates | `premise_process_vintage` cohorts (§3.15) | Yes, and T21 Step 3 rewrites the paragraph that explains the split |
| Bounding a unit over a year range | `R/fct_constraints_known_changes.R` | Not used. Review showed it constrains *proportions* and preserves final-commodity output, so it is not the shape a simple absolute bound would take. Noted for T24 |

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 1 | issues_found | 11 findings, all absorbed or deferred |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | issues_open | 12 issues, 2 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**CODEX:** Recommended not executing the forward-switch task as scoped. Independently found
that §5.1's $Q$ is not period-indexed, that the R `known_changes` precedent constrains
proportions rather than absolute bounds, and that the "history is never read" guard covered
only A3 and A4. All three absorbed.

**CROSS-MODEL:** Codex and the modelling-correctness reviewer converged on the same root
cause without contact: $Q$ carries no period index, so C1 cannot constrain a duty that appears
mid-horizon. Both independently rejected V28 as unfalsifiable. The eng review's own
calendar-versus-period finding was confirmed by both. Scope was reduced to T20 and T21 on the
user's decision (D2 → A).

**VERDICT:** ENG CLEARED for T20 and T21 with the fixes folded in. T24 deferred behind T23.
Two critical gaps are stated, not closed: §5.6 does not exist, and §1.4's label ranges have no
automated guard for this specification.

**UNRESOLVED DECISIONS:**
- Open question, default taken but not confirmed: is the held history ever read? Default is
  no, held for reconciliation, trend and reporting only. If duty growth is later derived from
  a trend, that is a new decision.
