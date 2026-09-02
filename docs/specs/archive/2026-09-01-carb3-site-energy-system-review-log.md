# CaRB3 Site Energy System — Design Review Log (archived)

**Archived 2026-09-02.** This is the record of how the design was reviewed and what those
reviews changed. Every resolution listed here is already in force in the
[implementation specification](../2026-08-28-carb3-site-energy-system-implementation.md) and
its companions. **Nobody needs to read this to understand the model** — it exists so that a
future reader asking *why is it like this* can find the argument rather than re-run it.

---

## Origin

Produced 2026-08-28 from a design conversation covering onsite generation, storage,
electrolysers, biomethane and heat pumps, then put through two engineering plan reviews.

## Scope decision, since retired as a label

The live documents carry two programme decisions, `PD1` (temporal depth) and `PD2` (how
storage acquires a value). A third was taken first and is no longer cited anywhere, because
it was a decision about documents rather than about the model:

> **Where the re-architecture lands.** A new specification beside the existing one, with the
> existing one frozen as the COMIT-parity baseline, rather than an edit in place.

That decision is what created the two-hop validation chain the specification still states at
its §1.1: the baseline reproduces coupled-off COMIT (V1), and the new model reproduces the
baseline in the carrier-equivalent configuration (V1b).

The live documents were made self-contained on 2026-09-02, so the words *v1* and *v2* no
longer appear in them. The distinction they encoded survives only where it does real work —
in the validation chain — and is expressed there by naming the baseline for what it is.

---

## First engineering review, 2026-08-28

Five findings, all folded into the plan.

| # | Finding | Confidence | Resolution |
|---|---|---|---|
| 1 | V1 step 4 compares *per-technology capacity by period*, which does not exist under a unit/carrier model. V1 is a blocking Phase 1 exit criterion | 9/10 | Two-hop parity: baseline↔COMIT via V1 unchanged, new model↔baseline via a new V1b |
| 2 | `technology_category` (11 values, 397 rows) conflates fuel carrier, conversion device and abatement bolt-on on one axis | 9/10 | Split unit spine; taxonomy split is data-migration group A |
| 3 | Both spec generators hardcode heading strings, section prefixes and the label ranges `A1-A9 / C1-C9 / V1-V17 / D1-D11`; neither is wired to CI; the diagram builder has no `--check` | 10/10 | Parameterise both (T2) |
| 4 | No committed validator exists for the seven hand-researched data files the migration rewrites | 10/10 | Validator first, green baseline before migrating (T1) |
| 5 | The carrier balance manufactures new solver degeneracy, and the tie-break key `technology_code` ceases to exist | 8/10 | New tie-break, price-wedge rule, recomputed §9.1 arithmetic (T7) |

**One critical gap** — silent, untested and unhandled as specified — was a premise matching
no archetype, closed by the `fitted` → `substituted` → `default` ladder now in
specification §3.17.

There were two. The other was ψ extrapolated outside its fitted design-ratio range, and the
hybrid-unit decision (`PD2`) **removed it rather than testing for it**: a fixed sizing ratio
means there is no continuous ratio to extrapolate along, and no piecewise linearisation to
fall off the end of. That also deleted the one genuinely hard piece of engineering the plan
previously carried, since a bilinear ψ(ratio) × output term needed SOS2 or binaries to
linearise exactly, against a requirement that the problem stay a pure LP.

---

## Second engineering review, 2026-09-01

Run against the merged documents. Nine findings, five of them P1, all folded in. Three were
gaps where the plan changed something and then said nothing about the consequence.

| # | Finding | Confidence | Resolution |
|---|---|---|---|
| 1 | **§7 emissions accounting never addressed.** The only claim was "§7's formulae keep working" — the formulae do, the *attribution* does not | 10/10 | New §7 + V22 |
| 2 | **§4 algorithms never addressed**, and A4's break was named "the deepest change" then left unfixed. V1b cannot run against an under-determined A4 | 10/10 | New §4 with the carrier-mix tier rule + V23 |
| 3 | **Waste heat had no data item.** Claimed as a headline justification; grades say what a unit accepts, not what it rejects | 9/10 | New data item B5, reject-heat coefficients |
| 4 | **"~35 units" contradicted "preserve 57 non-fuel archetypes"**, and "24 duty families" counted 16 sector-root codes as duties | 10/10 | Recomputed: **~95 units**, 12 service families + 14 chemistry nodes |
| 5 | `TODOS.md` claimed as written; did not exist | 10/10 | Dropped — the data-migration document is the list |
| 6 | A7 relaxation ladder rung flagged and unowned | 10/10 | Rungs C12 → C10 → C11 specified in §4.2 |
| 7 | The concavity claim making hybrid interpolation safe was argued in prose and checked nowhere | 8/10 | V20 (e) |
| 8 | Tier A had no scale gate, and it is the new expensive thing | 8/10 | New gate G4 |
| 9 | **The planned worked example cannot demonstrate the carrier mechanism.** Cement has only `ICMCLK` and `ICM` — no `LTH`, `STM`, `DRY` or `SPC` — so no graded-heat cascade, no unit competition, no waste-heat sink, and CHP only fused inside CCS rows | 9/10 | Keep cement for the parity case; add a **food & drink** example for the mechanism |

Finding 4 and an item recount in the same week were the third and fourth instances of a
count written into prose without being counted, which is now a rule in `CLAUDE.md`.

An independent second-model review was not run (codex not installed on the authoring
machine).

---

## Defects found in the archived documents, and deliberately not fixed

These were found during the reviews. The documents they sit in are frozen — one of them is
the parity baseline V1 is anchored to — so the defects are recorded rather than corrected.
None of them affects the live specification, which restates the affected material itself.

- **`2026-08-19-…-vision.md` lines 146 and 240** use `λ` for the stranding factor, which is
  `ξ`; `λ` is the peak factor. The worked example already flags the collision at its line
  248. The live specification uses `ξ` throughout and inlines the eleven design decisions at
  its §1.6, so nothing depends on the vision document any more.
- **`2026-08-19-…-worked-example.md` line 372** cites `§1.5` for measured emissions, which
  are `§1.6`; **line 414**'s stated withholding set omits `§1.9`, which the comparison it
  draws requires.
- **`2026-08-19-…-worked-example.md`** A3 shares (coal 0.97 to the kiln) disagree with
  [`../../notes/data/activity_process_energy_profile.csv`](../../notes/data/activity_process_energy_profile.csv),
  which says 1.0.
