# When plant replacement opens a new process version

*Plan written 2026-10-02. Built 2026-10-02: Tasks 1–3 in c2ca017 and b3fe7c9, Task 4 in c7e9f4c.*

## Goal

The live spec ([implementation](../../specs/2026-08-28-carb3-site-energy-system-implementation.md))
has two dates that readers confuse: `premise_process_detail.valid_from_year` (§3.10, when a
version of a process began at the site) and `premise_process_unit.commissioned_year`
(§3.10.2, when one cohort of its plant was installed). The spec never says whether replacing
a process's plant should close the version and open a new one. Read literally, §3.10.2's
"a parent's children are its complete plant list" says a version's cohorts are everything it
ran across the whole interval, so a 1957 version whose only cohort is a 2016 motor would claim
that motor ran in 1957. Nine processes in the slice's premise data are in exactly that shape
(seven on `mvp-cement`, two on `mvp-dairy`, as at fork/main 34f5df6).

**Decision (2026-10-02, Alexandre):** a version's cohort rows list the plant **as at the end
of the version**, which for an open version is the base year. Replacing plant, in part or in
full, adds or changes cohort rows and does not open a new version. A new version opens only
when a fact on the §3.10 row itself changes. This needs no data migration: every existing row
is already valid under it. The alternative (full replacement opens a new version) was priced
at nine process splits across two premises, with test keys shifting, for no change in what the
model reads, and was declined.

## File map

| File | Change |
|---|---|
| `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md` §3.10 (lines ~1225–1300) | `valid_from_year` field row and a new rule: what opens a new version |
| same file, §3.10.2 (lines ~1350–1420) | Reword "a parent's children are its complete plant list" to "as at the end of the interval"; reword the sentence at ~1401 contrasting the two dates |
| same file, §10.3 V26 row (~2628) | Extend V26 (validity intervals are disjoint) with the new mechanical consequence |
| same file, `*Section last updated*` lines for §3 and §10 | Bump to the edit date |
| `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-cement.md` §1.5 (~163) | One sentence: the kiln has two versions because its rated capacity changed with the rebuild (0.70 → 0.95 Mt/yr), not because its plant was replaced |
| `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-food-drink.md` §1.6 (~177) | One sentence: the 2016 boiler joins the 2011 version as a cohort, and no new version opens |
| `carb3/data/premises/README.md` rows at lines 133, 153, 156 | Mirror the rule in the plain-language field tables |
| `carb3/data/premises/verify_premise_keys.py` (~108–185) | New blocking check: a cohort's `commissioned_year` must not be after its version's `valid_to_year` |
| `carb3/tests/test_load.py` (after ~760, the premise-rules block) | Test for the new check |
| `docs/notes/README.md` | Register this plan under the plans rows (line ~63) |

No change to `load.py` or `survival.py`. They read only the version valid at the base year,
and the new check concerns closed versions, which they never touch. The loader parity tests
therefore need no new case.

## The rule to write

Draft wording for §3.10, placed after "Rule (intervals do not overlap)":

> **Rule (what opens a new version).** A new interval opens when a fact on this row changes:
> the process's `connection_id`, or its `known_capacity` (a rebuild to a new rated capacity,
> as the cement works' kiln went from 0.70 to 0.95 Mt/yr in 2004). A change of plant alone
> does not open one, whether it replaces part of the plant or all of it. It is recorded in
> §3.10.2, whose rows under an interval list the plant **as at the end of that interval**:
> the base year for an open interval, `valid_to_year` for a closed one. A site that has made
> steam since 1960 and replaced its boiler in 2015 has one interval from 1960 and one cohort
> dated 2015. `known_activity` changes every year and opens nothing.

Consequences to state in §3.10.2:

- A cohort's `commissioned_year` may be **later** than its interval's `valid_from_year`
  (plant replaced or added during the version) or **earlier** (plant carried over into a new
  version, such as a cooler kept through a kiln rebuild).
- It may **not** be later than a closed interval's `valid_to_year`: plant installed after a
  version ended cannot be that version's plant. Reject with reason `vintage_after_interval`.
  (Grep shows no existing use of that string.)

## Tasks

- [x] **Task 1: Spec rule in §3.10 and §3.10.2**
  - **Files:** implementation spec §3.10 and §3.10.2, `*Section last updated*` at line ~202.
  - **Test first:** none. This is prose. The check is Task 4's grep and `make docs-check`.
  - **Change:** Add the rule above. In §3.10's `valid_from_year` field row, change "The year this
    process started at the premise" to "The year this version of the process started at the
    premise", and point to the new rule. In §3.10.2, rewrite "Rule (a parent's children are its
    complete plant list)" so that it reads "as at the end of the interval", and add the two
    consequences above, with `vintage_after_interval` written in the same style as
    `vintage_in_future` in the `commissioned_year` field row. Replace the sentence at ~1401
    ("`premise_process_detail.valid_from_year` is a different date again …") with one that
    cites the new rule. **Gotchas:** keep §3.10 and §3.10.2 at their section numbers, because
    the archived baseline is aligned to them (CLAUDE.md, "Section numbers are aligned"). Add no
    version language. Bracket every label (D11 (existing plant has an age), V26 (…)).
  - **Verify:** `make docs-build && make docs-check` regenerates `docs/specs/diagrams/*` if the
    §3 field tables feed `entities`, then shows it clean. Commit the regenerated files with the
    edit.
  - **Depends on:** none.
  - **Settled (eng review D1):** the triggers are the row's facts only, `connection_id` and
    `known_capacity`. A production route change at the same capacity opens no version.

- [x] **Task 2: V26 widened**
  - **Files:** implementation spec §10.3 V26 row (~2628); §10's `*Section last updated*` (~2547).
  - **Change:** Append to V26: "and no §3.10.2 cohort under a closed interval has a
    `commissioned_year` after that interval's `valid_to_year`". This widens an existing test,
    not a new label, so the `V1`–`V35` range in §1.4 and CLAUDE.md stays as it is. Widen each
    worked example's V26 row (`cement:1572`, `food-drink:1711`) by the same clause (eng review
    D3): cement's closed wet-kiln cohort has no year, so it passes; the dairy has no closed
    interval, so the clause is vacuous there.
  - **Verify:** `grep -n "V26" docs/specs/2026-08-28-carb3-site-energy-system-*.md` and read each hit.
  - **Depends on:** Task 1. Same agent as Tasks 1 and 3 (one file, one owner).

- [x] **Task 3: Worked examples and premise README**
  - **Files:** cement example §1.5 (~163), food and drink example §1.6 (~177),
    `carb3/data/premises/README.md` lines 133, 153 and 156.
  - **Change:** Cement: one sentence after "`kiln_pyroprocessing` carries two disjoint validity
    intervals" saying the second interval opens because the rebuilt line's rated capacity
    changed (0.70 → 0.95 Mt/yr). Nothing about the other seven processes: the example gives
    them no cohort rows (eng review finding 1). Food and drink: one sentence saying
    the 2016 boiler joins the 2011 interval as cohort 2. README: line 133's "started at the
    site" becomes "this version started", line 153 gains "the plant as at the end of the
    window", and line 156's existing "a site can run a process for decades on newer equipment"
    is kept and linked to the rule. Add there (eng review D2) that in the slice's data seven
    `mvp-cement` processes keep their 1957 (or 2004) interval though their synthetic plant dates
    from 2016 (the motors) or 1998 (the grinder), which the rule makes valid.
  - **Verify:** `grep -rn "complete plant list\|started at the site\|process started" docs/specs carb3/data/premises/README.md`
    leaves no wording that contradicts the rule.
  - **Depends on:** Task 1. Same agent as Tasks 1 and 2.

- [x] **Task 4: Blocking check in the premise verifier**
  - **Files:** `carb3/data/premises/verify_premise_keys.py`, `carb3/tests/test_load.py`.
  - **Test first:** `test_verifier_rejects_vintage_after_interval` in the premise-rules block of
    `test_load.py`. Use `_premise_copy(tmp_path)` and the existing
    `_verifier_failures(tmp_path, *, expect_clean=False)` (`test_load.py:692`), then set `commissioned_year` to `2010` on the
    `mvp-cement` / `kiln_pyroprocessing` / `1957` / cohort `1` row (`kiln_wet_ICMCLK`, whose
    interval closes in 2003). Assert that the verifier's FAIL lines contain
    `vintage_after_interval`. **Gotcha:** `_edit` changes only the *first* row for a premise,
    which is not this one, so add a keyed variant (match on `process_id`, `valid_from_year` and
    `cohort_id`) or edit the CSV in the test directly. A second case sets the same row to `2003`
    and asserts it passes, because the bound is inclusive.
  - **Change:** In the `premise_process_detail` loop, record `valid_to_year` per
    `(premise_id, process_id, valid_from_year)` alongside `parents`. In the
    `premise_process_unit` loop, next to the `vintage_in_future` check, add
    `E(f"premise_process_unit[{p}/{proc}/{vf}/{coh}]: commissioned_year after the interval's valid_to_year (vintage_after_interval)")`
    when the parent is closed, the year is given and the year is greater than `valid_to_year`. Also add
    the rule to the README's list of what the verifier checks (~358).
  - **Verify:** before the change, `uv run --directory carb3 pytest tests/test_load.py -k vintage_after_interval`
    fails on the first case (no FAIL line). After it, both cases pass, `python3
    carb3/data/premises/verify_premise_keys.py` is clean on the real data, and `make check` is green.
  - **Depends on:** Task 1 (the reason string must match the spec). Independent of Tasks 2 and 3.

- [x] **Task 5: Register and ship**
  - **Files:** `docs/notes/README.md`, this plan's status line.
  - **Change:** Add a row for this plan beside the other `superpowers/plans` rows, and mark the
    plan built.
  - **Verify:** `make check`. Then open a PR to `fork` (`AlexandreLab/comit`) against `main`,
    with labels bracketed in the body.
  - **Depends on:** Tasks 1–4.

## Eng review, 2026-10-02 (/plan-eng-review)

**Scope Challenge.** 9 files, no new classes or services; the smallest change that closes the
gap is prose in §3.10 and §3.10.2 plus one blocking check. Scope accepted as-is.

**Findings**

1. [P2] (confidence 9/10) Task 3, cement example: the sentence about "the other seven
   processes keep their 1957 interval though their synthetic plant dates from 2016" does not
   belong in the worked example. The example says those processes have **no** cohort rows
   (`worked-example-cement.md:193`, "The other seven processes have **no child rows**"); the
   2016 motors and 1998 grinder exist only in the slice's `premise_process_unit.csv`.
2. [P2] (confidence 8/10) Task 1 checkpoint: the trigger list (`connection_id`,
   `known_capacity`) is the one judgement call, and it was parked mid-implementation. It
   must be settled before lanes start, because Task 3's cement sentence depends on it.
3. [P3] (confidence 8/10) Task 2: the worked examples' own V26 (validity intervals are
   disjoint) rows (`cement:1572`, `food-drink:1711`) would no longer quote V26 in full.
4. Factual: the test helper is `_verifier_failures(tmp_path, *, expect_clean=False)`
   (`carb3/tests/test_load.py:692`), not a "FAIL lines" helper to be written.
5. Factual: the worked examples carry no `*Section last updated*` lines, so only the
   implementation spec's §3 and §10 lines are bumped.

**Architecture.** No issues: the loader (`load.py`) and `survival.py` read only the version
valid at the base year (`survival.py:177`), so the new rule and check touch nothing they read.
**Code quality.** No issues beyond finding 4. **Performance.** Not applicable (a CSV scan).

**Tests.**

```
CODE PATHS (verify_premise_keys.py, premise_process_unit loop)
  commissioned_year blank                 -> skip         [GAP -> case c]
  parent open (valid_to_year blank)       -> skip         [★★ covered: real data runs clean]
  parent closed, year <= valid_to_year    -> pass         [GAP -> case b, 2003 inclusive]
  parent closed, year >  valid_to_year    -> FAIL vintage_after_interval  [GAP -> case a]
```

Case (c), a blank year under a closed parent, is the real cement wet-kiln row, so the
clean-data run already covers it. Value: protects=a cohort cannot postdate its closed
interval; fails_when=the comparison is dropped or inverted; why_new=no check reads
valid_to_year against commissioned_year today; seam=none.

**Outside voice.** Unavailable: Codex refuses gstack's default model on this account
(`model_unusable`), and the native fallback needs TaskOutput, which this session lacks.

**Parallelization.** Lane A (docs: Tasks 1, 2, 3, one agent for the whole spec file, per
CLAUDE.md's lesson on cascading edits) and Lane B (Task 4: verifier and test) touch disjoint
modules and can run together, since the reason string `vintage_after_interval` is fixed here.
Merge both, then Task 5.

**Decision ledger** (answers 2026-10-02, Alexandre)

- D1 (finding 2): version triggers. Answer: row facts only (`connection_id`, `known_capacity`). Applied to Task 1.
- D2 (finding 1): the synthetic-plant sentence. Answer: premise README, not the worked example. Applied to Task 3.
- D3 (finding 3): worked-example V26 rows. Answer: widen both. Applied to Task 2.
- Approval readiness: PASS (D1, D2, D3).

NOT in scope: a loader (`load.py`) copy of the check, since the loader never reads a closed
interval; a production-route field on §3.10 (declined under D1).

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Outside Review | codex (plan-eng-review) | Independent 2nd opinion | 1 | unavailable | model_unusable; no native fallback (TaskOutput absent) |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | issues_open | 3 issues (all resolved: D1–D3), 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **OUTSIDE COVERAGE:** codex, plan-review phase, unavailable (model refused on a ChatGPT account). No outside findings.
- **VERDICT:** Eng review findings all resolved and applied to the plan; ready to implement.

NO UNRESOLVED DECISIONS
