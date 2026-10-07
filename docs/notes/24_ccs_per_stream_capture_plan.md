# A capture train takes a fraction of each stream: the plan

*Written 2026-10-07. Answers [note 20](20_reference_data_open_questions.md) item 57, whose
"Decided 2026-10-07" line chose per-stream capture rates over a train authored per premise.
Measured on `fork/main` at `369d051`. Reviewed 2026-10-07 by a fresh-context engineering
review against the spec, the data and the code; its findings are folded in (a host shared by
two trains, the capture-flow symbol, Form C's objective, the label-range quotes, the validator's
fuel-CO₂ derivation, Decision 5's cost, the report reader, Task 4's lines, §5.7 and three
smaller points).*

## In plain terms

`ccs_amine`, the only capture train with coefficients, is written as a fixed recipe: every
tonne it captures is 55.755% process CO₂, 35.257% fossil fuel CO₂ and 8.988% biogenic fuel
CO₂, which is the stack of the cement worked example's own kiln. C8 (carrier balance) makes
that recipe binding. A cement works with a different fuel mix runs out of one ingredient first,
and the train stops there. At `mvp-cement`, which burns no waste-derived fuel, the biogenic CO₂
runs out after 22.8 kt, so the train captures 4% of a 568 kt stack.

A real train does not work that way. It treats a flue gas and takes the same fraction, about
90%, of every CO₂ stream in it. This plan makes the model say that:

1. **Each `emission_input` row on a capture train becomes a rate**, the fraction of that CO₂
   carrier the train captures from its hosts, in place of a share of a fixed blend. For
   `ccs_amine` that is 0.90 on each of its three carriers, from the COMIT workbook.
2. **The train treats its hosts' flue gas, not the whole site's CO₂.** A new variable says how
   much of each host's activity the train treats, and the train captures its rate of every
   stream that activity produces. The hosts are the rows of `unit_abatement_host` (§3.5.3),
   which today the LP never reads.
3. **The problem stays a linear programme**, with no binary and no product of two variables.

The estimate at `mvp-cement` (section 6): capture rises from 0.0228 to about 0.511 Mt/yr, and
the objective falls by at least £915m, from £4,554.93m to about £3,640m. The cement worked
example is re-solved afterwards, as its own task (Task 4), so that it is done once.

## 1. What the model does today

- **`ccs_amine`'s three `emission_input` rows are a blend.** −557.55 `co2_process`, −352.57
  `co2_fuel_fossil` and −89.88 `co2_fuel_biogenic`, kt per Mt of `co2_captured`
  (`docs/notes/data/unit_input_output.csv:210-212`). They sum to 1000 kt, the Mt the train
  makes (`:209`), and each provenance string says it is the cement example's §8.1 base-year
  stack as a share. Its other rows are 1.9 PJ of `natural_gas` as `fuel_input` (`:213`) and
  0.35 PJ of `electricity` as `aux_input` (`:214`) per Mt captured.
- **C8 (carrier balance) multiplies each row by the train's total activity**
  (`carb3/src/carb3/build.py:1325-1328`, then `:468-498`). So the train draws the three
  carriers in fixed proportion, and the scarcest one, relative to its share, caps it.
- **C8 is a site-wide pool, and the host table is not in the LP.** Each carrier has one
  balance row per period (`build.py:468-498`). Any unit's CO₂ on a carrier can feed the train.
  `unit_abatement_host` is read only by the admission screen (`carb3/src/carb3/load.py:803-881`)
  and, in the spec, for the train's inherited life; `build.py` never reads it (its one mention,
  `:1086`, is a docstring).
- **The train's own reboiler CO₂ is not a declared row.** A6 (the problem builder) derives it
  from the `fuel_input` row (`build.py:1330-1334`, `:1760-1823`): 1.9 × 51.12 kt/PJ
  (`scenario_parameters.csv:2-8`) split by natural gas's `biogenic_fraction` 0.0115
  (`carrier.csv:2`), so 96.011 kt fossil and 1.117 kt biogenic per Mt captured. The +106.59
  quoted in spec §3.6 (`…-implementation.md:1100`) and the cement example (`:475`, `:496`) is
  the example's own 56.1 kt/PJ factor, not the reference data's.
- **Because the pool is site-wide, the train already draws its own reboiler's biogenic CO₂.**
  The cement example's §8.5.1 (`…-worked-example-cement.md:1483-1485`) counts 2.020614 kt/yr
  from the gas kiln and 0.025427 from the reboiler, 2.046041 kt in all, and 2.046041 ÷ 89.88 =
  0.022764 Mt/yr is the cap.
- **At a coal-only works the train cannot run at all.** Coal's `biogenic_fraction` is 0
  (`carrier.csv:9`), so no unit but the train itself makes `co2_fuel_biogenic`.
  `screen_premise` treats a unit as never its own source (`build.py:862-866`) and drops it.
- **§5.4's biogenic credit is $|\iota_{u,c,\text{emission\_input}}|\,z_{u,t}$**
  (`…-implementation.md:2169`), computed in `build.py:2005-2074` and repeated in the ledger
  (`carb3/src/carb3/ledger.py:738-745`) from the same function.

**The run, `uv run --directory carb3 python -m carb3 mvp-cement`, at `369d051`:** objective
£4,554.9330m. From 2035 the only kiln standing is `kiln_dry_gas`, producing 392.27992 kt/yr of
`co2_process`, 173.68492 of `co2_fuel_fossil` and 2.02061 of `co2_fuel_biogenic`, 567.98545 kt
in all. `ccs_amine` is built at 2035 at 0.024933 Mt/yr and captures 0.022764 Mt/yr: 12.69214 kt
of process CO₂, 8.02595 of fossil and 2.04604 of biogenic. Vented from 2035: 379.5878 kt of
`co2_process`, 167.8446 of `co2_fuel_fossil` and none of `co2_fuel_biogenic`.

### Every unit with an `emission_input` row, and every capture train

| Unit | Class | `emission_input` rows | What happens to it under this plan |
|---|---|---|---|
| `ccs_amine` | abatement | 3 (`unit_input_output.csv:210-212`) | Rows become rates (section 3) |
| `tgr_blast_furnace_coke` | **converter** | 1: `co2_process` −183 kt per Mt of pig iron (`:335`), from COMIT's `IISTGRBF01` | **Unchanged.** The rate reading applies to `abatement` units only, so this row keeps its kt-per-output meaning. See section 9 for a separate defect it carries |
| `ccs_amine_mdea`, `ccs_amine_coal_chp`, `ccs_oxyfuel`, `ccs_oxyfuel_partial`, `ccs_amine_lime`, `ccs_oxyfuel_lime`, `ccs_amine_hvc_gas`, `ccs_amine_hvc_biomass`, `ccs_amine_hvc_elec`, `ccs_amine_ammonia`, `ccs_amine_ironmaking`, `ccs_amine_dri` | abatement | none | The admission screen drops all twelve for want of coefficients today. Giving them rows is out of scope (section 9) |

`unit.csv` holds 13 `abatement` units, and `unit_abatement_host.csv` 37 rows, 20 of them for the
five cement trains (four dry kilns each). `ccs_amine`'s hosts are `kiln_dry_coal`, `_gas`,
`_wdf` and `_oil` (`unit_abatement_host.csv:2-5`).

## 2. The formulation

Physically a train on one flue captures the same fraction of every stream in it. Written
directly, "the same fraction of each stream" is a product of a fraction variable and the
streams, which are themselves variables: bilinear. Three linear forms avoid that. All three
use these symbols, each checked free in the live spec by `grep -cF` (0 hits each):

| Symbol | Meaning |
|---|---|
| $H_u$ | The hosts of train $u$: its `unit_abatement_host` rows, intersected with the units in the model at the premise |
| $\nu_{u,c}$ | Train $u$'s capture rate on emission carrier $c$, a fraction in (0, 1]. Read from its `emission_input` row (section 3) |
| $\iota^{\text{gen}}_{u',c,t}$ | Host $u'$'s **gross** production of $c$ per unit of its activity: its declared `emission` row plus A6's derived row, and **never** net of its own `emission_input` row |
| $z^{\text{host}}_{u,u',t}$ | Form B only: host $u'$'s activity whose flue gas train $u$ treats |
| $\Gamma_{u,c,t}$ | Train $u$'s capture of carrier $c$ in period $t$, kt/yr: a variable in Form A, an expression in Form B. **Not $q$**, which is the live spec's duty index ($z_{u,q,t}$, $U_q$, $Q_u$; `…-implementation.md:1983`, `:2188`); `\Gamma` has 0 hits there |

**Gross, not net, is load-bearing.** `tgr_blast_furnace_coke` hosts `ccs_amine_ironmaking`
(`unit_abatement_host.csv:37-38`) and *consumes* 183 kt of `co2_process`. Netting would give it
a negative production, and a bound of "at most a negative number" would force the host to zero.

### Form A: per-stream flows bounded by host production

Variables $\Gamma_{u,c,t} \ge 0$ for each carrier $c$ the train has an `emission_input` row on.

$$\Gamma_{u,c,t} \;\le\; \nu_{u,c} \sum_{u' \in H_u} \iota^{\text{gen}}_{u',c,t}\, z_{u',t} \qquad\qquad z_{u,t} \;=\; 10^{-3} \sum_{c} \Gamma_{u,c,t}$$

As written, each train is bounded by its hosts' whole production, so two trains on one host
could each capture the same stream; Form A needs the shared-host fix of Form B below, here as
a bound on the sum over trains of their draw of $c$ from that host, which in turn needs the
flows split by host.

C8 (carrier balance) on $c$ takes $-\Gamma_{u,c,t}$ in place of $\iota_{u,c,\text{emission\_input}}\,z_{u,t}$. The
$10^{-3}$ turns kt into the Mt of `co2_captured` the train's activity is denominated in.

**What it relaxes.** When the train's capacity binds below $\sum_c \nu_{u,c} \times$ (host
production of $c$), the LP may take any mix of streams within their bounds: all of the
biogenic stream and less of the others, say. Physically the train would take the same smaller
fraction of each.

### Form B: treated host activity (recommended)

Variables $z^{\text{host}}_{u,u',t} \ge 0$, one per train, host and period.

$$\sum_{u \,:\, u' \in H_u} z^{\text{host}}_{u,u',t} \;\le\; z_{u',t} \quad \forall u',\, t \qquad\qquad \Gamma_{u,c,t} \;\equiv\; \nu_{u,c} \sum_{u' \in H_u} \iota^{\text{gen}}_{u',c,t}\, z^{\text{host}}_{u,u',t} \qquad\qquad z_{u,t} \;=\; 10^{-3} \sum_{c} \Gamma_{u,c,t}$$

Here $\Gamma_{u,c,t}$ is an expression, not a variable, and C8 on $c$ takes $-\Gamma_{u,c,t}$ as in Form A.

**The bound is summed over the trains on one host, and that is load-bearing.** Every dry
cement kiln hosts five trains (`unit_abatement_host.csv:2-21`), and all five are offered at
`Cement Works` (`unit_eligibility.csv:1022-1032`). A bound per train,
$z^{\text{host}}_{u,u',t} \le z_{u',t}$, would let two trains each treat the whole kiln and
capture 180% of its CO₂. Only `ccs_amine` has coefficients today, so the defect would stay
hidden until a second train is given rows. The summed form says one flue is treated once;
Decision 7 asks whether a second train may instead stack on the residual stream.

**What it relaxes.** Within one host the mix is exact: the train treats a share of that host's
activity and takes $\nu_{u,c}$ of every stream that share produces, so the streams are captured
in the host's own proportions by construction. Across hosts it is not: when capacity binds, the
LP may treat the gas kiln's flue and not the coal kiln's, where on a co-fired line D13 (one
primary carrier per unit) has split one physical flue into one unit per fuel. Form B's feasible
set is contained in Form A's.

**Why the relaxation moves no objective, in either form.** A kt of `co2_process` or
`co2_fuel_fossil` captured avoids a charge of $10^{-3}\pi_t$ per kt; a kt of
`co2_fuel_biogenic` captured earns a credit of $10^{-3}\pi_t$ (§5.4,
`…-implementation.md:2169`); the train's costs are per Mt captured whatever the stream. Every
kt is worth the same, so the LP is indifferent to the mix, and the optimum's objective is the
same in A, B and the exact bilinear form, given the same host bound. Only the *reported* split between streams, and so the
reported biogenic credit, can differ, and only in a period where the train's capacity binds.
With linear costs that happens only where the train was sized for another period's hosts.

**Can it over-credit biogenic capture?** Not beyond the bound: in both forms captured biogenic
CO₂ is at most $\nu$ times what the hosts produce. Form A can report more biogenic credit than
physics allows when capacity binds, with the charged venting higher by the same amount, so the
carbon term is unchanged. Form B cannot do that within a host.

### Form C: per-stream flows bounded by site production

Form A with the bound taken over every unit on the site that produces $c$, not only $H_u$. It
needs no host data, and it is closest to what C8's site-wide pool allows today. **It does
over-credit**: a kiln's train could capture, and be credited for, the biogenic CO₂ of a
biomass boiler elsewhere on the site, which is on a different flue. It would also make
`unit_abatement_host` irrelevant to what a train captures, which contradicts §3.5.3's own
statement of what the table is for ("Which units an abatement unit captures from").

### The train's own reboiler

Forms A and B exclude it: a train is never its own host (§3.5.3,
`…-implementation.md:1040`, "May not equal `unit_id`"), so its reboiler stack vents. That is
what the cement example's §8.4 does ("is not captured", `…-worked-example-cement.md:1383-1384`).
COMIT does the opposite: `ICMKLNMNQ01`'s bundle burns 4.91484 PJ of gas per Mt of clinker
(workbook sheet `technology_input_output`, against 0.03984 for the plain kiln `ICMKLND01`),
and `R/fct_emissions.R:280-289` applies the technology's one `emissions_released` to all its
fuel CO₂, so COMIT captures 90% of the CHP's CO₂ too. Capturing it in Form B is one linear term,
$\nu_{u,c}\,\iota^{\text{gen}}_{u,c,t}\,z_{u,t}$ added to $\Gamma_{u,c,t}$; Decision 4.

### Size

Form B adds $\sum_u |H_u| \times |T|$ variables and as many bound rows, plus $|U^{\text{abate}}|
\times |T|$ equalities. At `mvp-cement` the train has two hosts in the model (the coal and gas
kilns) and seven periods: 14 variables, 14 host rows (one per host and period, whatever the
number of trains) and 7 equalities. Form A is the same order. No binary in
either, so §2.3's linear programme stands.

## 3. Where the rate lives

Priced by `grep -c` per CLAUDE.md ("price a schema change before recommending against it").
The live spec publishes only the `entities` diagram from §3 (`spec_docs.config.json`;
`interfaces.enabled` is false), so a new field regenerates that diagram and nothing else.

| Option | Grain | Spec mentions | Code and validator mentions | Data | Schema change |
|---|---|---|---|---|---|
| **(a) `emission_input` coefficient on an `abatement` unit becomes $-\nu_{u,c}$** (the 2026-10-07 decision) | train × carrier, the grain wanted | `emission_input`: 7 in the live spec, 7 in the cement example | 8 in `carb3/src` (6 in the model, 2 in `report/sankey_data.py:403`, `:410`, which reads the `emission_input` rows of `unit_flow`), 7 in `docs/notes/examples/*.py`, 3 in `carb3/tests` | 3 rows, and the 3 in `reference_mvp` regenerated | none |
| (b) `unit.emissions_released`, one value per train | train only | `emissions_released`: 1 in the live spec, 1 in the cement example | 1 in `load.py` (schema list only), 2 in the validator | 13 cells, and `ccs_amine`'s 3 `emission_input` rows deleted | none, but per-stream is lost |
| (c) a new column on `unit_abatement_host` | train × host | `unit_abatement_host`: 8 in the live spec | 15 in `carb3/src`, 19 in `carb3/tests`, 3 in the validator | 37 rows | yes: loader schema (`load.py:109-112`), validator, `entities` diagram |

**(c) is the wrong grain**: the rate differs by stream, not by host. **(b) cannot say
per-stream**, which the 2026-10-07 decision chose; it would fit today's data, since COMIT carries
one value per technology, but a partial oxyfuel train that captures only the calciner's process
CO₂ could not be written. **(a) has the right grain and no schema change**, and its one danger
is that a role then has two bases: kt per output on a converter, a fraction on a train. That is
exactly the class of error note 20 item 56 was, a coefficient read on the wrong basis, so (a) is
recommended **only with a blocking guard**: every `emission_input` row on an `abatement` unit
lies in [−1, 0), `check_emission_coefficient_basis` skips exactly those rows and no others, and
a train's carrier must be produced by at least one of its hosts. Without the skip, the basis
check (`validate_carb3_data.py:1493-1547`) fails −0.90 as "below the mass band" and suggests
×1000, which would be the wrong fix.

### What `emissions_released` says today

§3.5 defines `emissions_released` as "Fraction **not** captured" (`…-implementation.md:900`),
and every one of the 13 trains carries 1 (`unit.csv`, column `emissions_released`), which reads
"captures nothing". The workbook carries 0.1 for each of their COMIT ancestors and 0.35 for partial
oxyfuel (`docs/notes/data/emissions_source_classification.csv`, column `emissions_released`; the
cement bundles at `:2-8`). No code reads the column:
its only `carb3` mention is the loader's schema list (`load.py:96`). Under (a) it would be a second
copy of the capture rate, in disagreement with the first. Decision 5.

### The rate for `ccs_amine`, sourced

**0.90 on each of `co2_process`, `co2_fuel_fossil` and `co2_fuel_biogenic`.** Source:
[COMIT_WB_140] (`references.csv:297`), sheet `Technologies`, the row with code `ICMKLNMNQ01`
("Dry kiln with natural gas CHP and MEA CCS"), column `emissions_released` = 0.1, so 1 − 0.1 =
0.90 captured. The lineage is confirmed three ways: `comit_technology_lineage.csv:6` maps
`ICMKLNMNQ01` to `ccs_amine`; the same workbook row's capex, 354.59814 £m per Mt/yr, is
`ccs_amine`'s capex in `unit.csv:80`; and the derived table repeats the 0.1
(`emissions_source_classification.csv:6`). COMIT applies the one value to process and fuel CO₂
alike (`R/fct_emissions.R:266-289`), which is what "the same fraction of every stream" means.
`provenance` is `comit_reuse`.

**Gap:** the workbook gives no primary literature source for its 0.1; its `Technologies` sheet
calls itself "A mixture of reviewed and not reviewed assumptions". No sourced rate that differs
by stream exists in the repository, so per-stream values other than 0.90 would be a gap until
researched (Decision 3). The cement example's "At 90% capture" (`…-worked-example-cement.md:1361`)
is the same figure with no citation of its own.

## 4. What else it touches

| Item | Effect |
|---|---|
| §5.4 biogenic credit | Becomes $\sum_{c\,:\,\text{zero\_rated}} \sum_{u \in U^{\text{abate}}} \Gamma_{u,c,t}$. `biogenic_capture_weights` (`build.py:2041-2074`) is no longer a weight on $z_{u,t}$; the build and the ledger (`ledger.py:738-745`) must both read $\Gamma$, from one function as now |
| C8 (carrier balance) | An `abatement` unit's `emission_input` rows leave the coefficient set `_balance_terms` builds (`build.py:1325-1328`) and enter as $-\Gamma_{u,c,t}$. Every other role, and every other unit's `emission_input` row, is unchanged |
| A6 (the problem builder) | Unchanged. It burns only `primary`, non-indirect carriers (`build.py:1330`); emission carriers are `emission`, so `emission_input` rows never reach it. A6's derived host rows are now also read as $\iota^{\text{gen}}$ |
| V31 (role and sign agree) | Holds: a rate is written negative, as a consumed carrier. Its spec text needs no change; §3.6's example row (`…-implementation.md:1100`) does |
| V33 (plant is named one unit at a time) | Leg (b) is unchanged, but the host table becomes load-bearing in the LP, not only for admission and life. A host producing none of the train's carriers is now a dead host, which the new guard reports. **Production must be derived, not read:** hosts declare only `co2_process`, and their fuel CO₂ is A6's (D15, fuel CO₂ is derived, process CO₂ declared), so the validator re-derives it from each host's burnt `primary`, non-indirect carriers and their `biogenic_fraction`, as `build.py:1330` does |
| Emission coefficient basis check | Must skip `abatement` `emission_input` rows and band them in [−1, 0) instead (section 3) |
| Energy closure (V2's closure leg) | Unaffected. It counts `energy`-denominated carriers only (`validate_carb3_data.py:1553-1600`), and every CO₂ carrier is `mass` (`carrier.csv:35-38`) |
| C13 (a cap is not routed through a consumer) | Unaffected. It traces energy carriers only (`build.py:1435-1444`) |
| `screen_premise` | Today it drops a train whose blend has an ingredient no other unit makes (`build.py:848-952`). Its train rule becomes "drop a train with no host in the model", and the train's `emission_input` rows stop counting as draws there |
| `carrier_mix` and `unit_flow` | The train's `emission_input` flows come from $\Gamma$, not from coefficient × activity (`ledger.py:552`, `:622`), and **keep the role label `emission_input`**: `report/sankey_data.py:403-410` reads captured CO₂ as exactly those rows |
| A per-host table | **In scope.** `capture_by_host.parquet`: train, host, carrier, period, treated activity, captured kt. Without it the host split of C14 is invisible. It needs a row in `carb3/README.md`'s output-table section (ten tables become eleven) and a test that it sums to `unit_flow`'s capture |
| `min_duty` and `earliest_year` | Unchanged. `ccs_amine`'s 0.25 Mt/yr floor and 2035 gate (`unit_eligibility.csv:1022`) are A2 (premise to duties and candidate units) screens |
| V10 (determinism) | Under Form B the split across hosts can be non-unique in a period where capacity binds. The run stays deterministic for one solver and one row order (§9.3), but the per-host split is an allocation, not a measurement, and should be reported as one |
| Linear programme | Holds: continuous variables, linear rows, no binary (§2.3) |

## 5. New labels

C1 to C13 and V1 to V36 are taken; `C14` and `V37` appear nowhere in `docs/`, `carb3/` or
CLAUDE.md (`grep -rnwE "C14|V37"`, no hits). The plan proposes:

- **C14 (a capture train treats its hosts' flue gas):** Form B's bound and equality rows.
- **V37 (a capture rate is a fraction of its hosts' streams):** at load, (a) every
  `emission_input` row on an `abatement` unit lies in [−1, 0), and the basis band skips exactly
  those rows; (b) each such carrier is produced by at least one of the train's hosts, with fuel
  CO₂ re-derived from the hosts' fuels as A6 does. After the solve, (c) no train captures more of
  a carrier than $\nu$ times its hosts' gross production; (d) within one host, the captured
  streams stand in that host's production proportions; (e) the trains on one host treat at most
  its activity in total; (f) the reported biogenic credit equals $10^{-3}\pi_t \sum \Gamma$ on
  the `zero_rated` carriers. Legs (c) to (f) are post-solve checks, so §5.7 lists them.

Both need §1.4's ranges widened in the same commit as every other place that quotes them:
A6's row in §4 ("assemble C1–C13", `…-implementation.md:1804`), the live spec's row in
`docs/notes/README.md:51` ("(C1–C13)", "(V1–V36)"), and CLAUDE.md's label table and its
"Widening … `C1`–`C13` or `V1`–`V36`" sentence. Decision 6.

## 6. Expected effect at `mvp-cement` (an estimate)

Hand arithmetic on the run figures of section 1, under the recommendation: Form B, $\nu = 0.90$
on all three carriers, the reboiler not captured. **An estimate, not a solve**; Task 3 replaces
it with the run.

From 2035 the one host standing is `kiln_dry_gas`, 567.98545 kt/yr of CO₂.

```
captured            0.90 x 567.98545                     = 511.18691 kt/yr = 0.511187 Mt/yr
capacity            0.511187 / (alpha 0.913 x gamma 1)    = 0.559898 Mt/yr   (today 0.024933)
reboiler gas        1.9 x 0.511187                        = 0.971255 PJ/yr
reboiler CO2        0.971255 x 51.12                      = 49.65056 kt  (49.07958 fossil, 0.57098 biogenic), vented
vented co2_process  0.10 x 392.27992                      = 39.22799 kt   (today 379.5878)
vented fossil       0.10 x 173.68492 + 49.07958           = 66.44807 kt   (today 167.8446)
vented biogenic     0.10 x 2.02061 + 0.57098              = 0.77304 kt    (today 0)
```

At 2035 prices (`scenario_parameters.csv`: carbon £302.08/t at `:152`, tariff £40m per Mt at
`:160`, gas £7.53m/PJ and electricity £30.45m/PJ at `:127-128`, discount rate 0.035 at `:156`;
annuity over `ccs_amine`'s own 30 years, as `build.py:1862` does):

| Term, 2035 | £m/yr |
|---|---|
| Capex, 354.5981 × 0.054371 × 0.559898 | 10.795 |
| Fixed opex, 8.86495 × 0.559898 | 4.963 |
| CO₂ transport tariff, 40 × 0.511187 | 20.447 |
| Reboiler gas, 0.971255 PJ × 7.53 | 7.314 |
| Auxiliary electricity, 0.178915 PJ × 30.45 | 5.448 |
| **Cost** | **48.967** |
| Carbon avoided less the reboiler's fossil stack, plus the biogenic credit | 139.593 |
| **Net benefit** | **+90.63** (today +4.04) |

Summed over 2035 to 2050 with the run's discount factors (2.886943, 2.430729, 2.046608,
1.723189) and each period's prices, the net benefit is about £957m against today's £43m.
**The objective falls by at least about £915m**, from £4,554.93m to about £3,640m or lower. "At
least", because today's solution with a larger train is feasible under Form B; the LP may then
re-optimise further, for instance in which kiln fuel it builds once 90% of the stack is captured.
Under Decision 4's alternative (the reboiler captured too), the train captures
511.18691 ÷ (1 − 0.90 × 1.9 × 51.12 ÷ 1000) = about 560.2 kt/yr.

Direction, in plain terms: capture becomes the cement works' largest abatement, and its charged
emissions from 2035 fall from about 547 kt/yr (379.59 of process CO₂ and 167.84 of fossil fuel
CO₂ vented) to about 106 kt/yr.

## 7. Decisions for Alexandre

One question each, so they can be asked one at a time.

1. **Which formulation?** (A) per-stream flows bounded by host production; (B) treated host
   activity, exact within each host; (C) per-stream flows bounded by site production. A and B
   give the same objective (section 2) and differ only in what they report. C does not: its bound
   is looser, so its objective can be lower, because a train may claim CO₂ from a flue it is not
   on. *Recommended: B. It is the tightest of the three at the
   same size, and it is the only one in which a host's streams are captured in the host's own
   proportions. C over-credits biogenic capture from units off the train's flue.*
2. **Where does the rate live?** (a) the `emission_input` coefficient on an `abatement` unit,
   read as $-\nu_{u,c}$, as the 2026-10-07 decision put it; (b) `unit.emissions_released`, one
   value per train; (c) a new column on `unit_abatement_host`. *Recommended: (a), confirmed,
   with V37's blocking guard and the basis check's exemption (section 3); it is the only option
   at the train × carrier grain with no schema change.*
3. **What are `ccs_amine`'s rates?** 0.90 on all three carriers, from [COMIT_WB_140]; or
   different rates by stream, which would need a source the repository does not hold. *Recommended:
   0.90 on all three. A post-combustion amine train sees one mixed flue gas, and COMIT applies one
   value to process and fuel CO₂ alike.*
4. **Does the train capture its own reboiler's CO₂?** No, as the cement example's §8.4 and
   §3.5.3's "a unit may not host itself" have it; or yes, as COMIT's bundle does. *Recommended:
   no. It keeps the host table the one statement of what a train captures, it is the conservative
   reading, and a reboiler or CHP stack is a separate flue unless a design ducts it to the
   absorber. Record the COMIT difference for the parity configuration of §10.2.*
5. **What happens to `unit.emissions_released`?** Retire it from §3.5 and `unit.csv`; or keep it
   and correct the 13 trains to their workbook values, 0.1 and 0.35, with a check that it agrees
   with a uniform rate; or leave it at 1. *Recommended: retire it. Nothing reads it, its 13 values
   contradict its own definition, and a second copy of the rate is the copy that goes stale. Its
   COMIT value survives in the provenance of the new `emission_input` rows. Cost: the §3.5 row
   (`…-implementation.md:900`) and the symbol $\rho_u$ it feeds, which would be orphaned in §5.3
   (`:2017`, the note that $\theta$ is not $\rho$, and `:2020`); 1 mention in the cement example;
   the loader schema (`load.py:96`); 2 in the validator (`:399`, `:1357`);
   `docs/notes/data/build/check_units.py:139-141`, which reads the column and would raise a
   `KeyError`; the column of `unit.csv` and of `reference_mvp/unit.csv`; and the `entities`
   diagram regenerated.*
6. **New labels, or fold into existing ones?** New C14 (a capture train treats its hosts' flue
   gas) and V37 (a capture rate is a fraction of its hosts' streams); or the rows written as part
   of C8 (carrier balance) and the checks as legs of V31 (role and sign agree) and V33 (plant is named one unit at a
   time). *Recommended: new labels. C14 is a new family of rows with its own variable, and V31 is
   a load check on signs, not on a premise's captured quantities.*
7. **May two trains treat one host?** No: one flue is treated once, and the trains on a host
   share its activity, $\sum_{u : u' \in H_u} z^{\text{host}}_{u,u',t} \le z_{u',t}$ (section 2);
   or yes, a second train stacked on the residual stream the first one vents, which needs a
   residual carrier or a chained bound and is not written here. *Recommended: no. Every dry
   cement kiln hosts five alternative trains, which are choices for one flue, not a series of
   absorbers, and stacking would need a second capture technology on a dilute residual that no
   unit in the library describes.*

### Decisions taken, 2026-10-07

Alexandre settled all seven on 2026-10-07, each as recommended above:

1. **Formulation:** B, treated host activity.
2. **Where the rate lives:** (a), the `emission_input` coefficient, read as a fraction on
   `abatement` units only and guarded by a blocking check (V37, a capture rate is a fraction of
   its hosts' streams). `tgr_blast_furnace_coke`, a `converter`, keeps the kt-per-Mt reading.
3. **`ccs_amine`'s rates:** 0.90 on each of its three carriers, from [COMIT_WB_140], sheet
   `Technologies`, row `ICMKLNMNQ01`, `emissions_released` = 0.1. The workbook cites no primary
   literature for the figure, and the provenance says so.
4. **The reboiler:** not captured. The train is never its own host.
5. **`unit.emissions_released`:** retired, from §3.5, the symbol $\rho_u$ in §5.3, `unit.csv`,
   the loader schema, the validator and `check_units.py`.
6. **Labels:** new C14 (a capture train treats its hosts' flue gas) and V37 (a capture rate is a
   fraction of its hosts' streams); the ranges widen to `C1`–`C14` and `V1`–`V37` everywhere they
   are quoted.
7. **Two trains on one host:** no. One flue is treated once,
   $\sum_{u : u' \in H_u} z^{\text{host}}_{u,u',t} \le z_{u',t}$.

## 8. Tasks

Each task names its goal, the files it may change, and how it is verified. **Task 3 is one
change**: data, validator, code, tests and the re-run land together, because `make check` runs
the `carb3` tests on pre-push and the new rows break the old C8 the moment they land.

### Task 1: Settle the seven decisions

- **Goal:** section 7 answered, and the answers recorded in note 20 item 57 under its
  2026-10-07 line.
- **Files:** `docs/notes/20_reference_data_open_questions.md`, this note.
- **Verification:** item 57 carries the decisions and the date.

### Task 2: Write the specification

- **Goal:** the live spec says what the plan does, with no version language.
- **Files:** `docs/specs/2026-08-28-carb3-site-energy-system-implementation.md`:
  - §1.4: `C1`–`C14` and `V1`–`V37` (Decision 6).
  - §3.5: the `emissions_released` row (Decision 5).
  - §3.5.3: the hosts are what C14 bounds a train by, not only what it inherits its life from.
  - §3.6: the `emission_input` role row (`:1082`), the capture-train case (`:1100`, which also
    quotes the example's +106.59 rather than the reference data's derived row), and a new rule:
    on an `abatement` unit the row is a rate, a fraction of the hosts' stream; on any other unit it
    stays kt per output unit.
  - §5.2: $z^{\text{host}}_{u,u',t}$. §5.3: $\nu_{u,c}$, $H_u$, $\iota^{\text{gen}}_{u',c,t}$.
  - §5.4: the credit (`:2169`) as a sum of $\Gamma$. §5.5: the train's term in C8 (carrier balance)
    and the new C14 (a capture train treats its hosts' flue gas).
  - §7: the direct-emissions readout (`:2505`) and rule 7.3, whose "takes both pro rata" becomes
    true by construction.
  - §5.7 (pre- and post-solve checks): V37's legs (c) to (f) as a post-solve check beside the
    row check, and `screen_premise`'s train rule.
  - §10.3: V37 (a capture rate is a fraction of its hosts' streams), and the wording of V30
    (emissions close through the balance) checked. §10.4's map and §10.5's failure mode 16.
  - §4: A6's row (`:1804`), which quotes "assemble C1–C13".
  - The `*Section last updated*` line of §1, §3, §5, §7 and §10.
- **Also:** CLAUDE.md's label table and its "Widening" sentence, and the live spec's row in
  `docs/notes/README.md:51` ("(C1–C13)", "(V1–V36)"), all in the same commit as §1.4; CLAUDE.md's
  data-caveat bullet on emission coefficients, which describes `ccs_amine`'s rows on the kt basis.
- **Verification:** `make docs-check` (the `entities` diagram regenerates if Decision 5 retires a
  field).

### Task 3: Data, validator, code, tests and re-run, as one change

- **Data:** `docs/notes/data/unit_input_output.csv:210-212` to −0.90 each, `provenance`
  `comit_reuse`, `provenance_ref` citing [COMIT_WB_140] `Technologies` `ICMKLNMNQ01`
  `emissions_released`. `unit.csv` under Decision 5. Then
  `carb3/data/build_reference_mvp.py` regenerates `carb3/data/reference_mvp/`, whose
  `unit_input_output.csv:147-149` carry the same rows.
- **Validator:** `docs/notes/examples/validate_carb3_data.py`: V37 as a blocking check, the
  exemption in `check_emission_coefficient_basis`, which needs `unit` passed in to know a unit's
  class (it takes `(io, car)` at `:1493` and is called at `:2063`), and Decision 5's column change in the schema
  list (`:399`) and the range check (`:1357`).
- **Code:** `carb3/src/carb3/build.py`: `_balance_terms` leaves `abatement` `emission_input` rows
  out; `build_model` adds $z^{\text{host}}$ and C14 and puts $-\Gamma$ into C8; `_biogenic_credit` and
  `biogenic_capture_weights` read $\Gamma$; `screen_premise`'s train rule. `ledger.py`: `unit_flow`,
  `carrier_mix` and `_cost_table` read $\Gamma$, with the capture flows keeping the role label
  `emission_input` that `report/sankey_data.py:403-410` reads; the per-host table
  `capture_by_host.parquet`, and its row in `carb3/README.md`'s output-table section. `load.py`: schema under Decision 5.
  The module docstring's paragraph on the credit (`build.py:95-102`).
- **Tests:** rewrite `test_the_carbon_term_equals_the_disposal_charge_less_the_biogenic_credit`
  (`carb3/tests/test_integration.py:1128-1204`) to recompute the credit from the solved flows and
  the reference CSVs, still independently of `build`; check
  `test_unit_flow_keeps_a_derived_emission_apart_from_a_declared_one` (`:751`), the subsidised-run
  node test (`:1380-1408`), `test_the_problem_is_sparse_not_dense` (`:843`), whose variable
  ceiling must count $z^{\text{host}}$, and `test_report.py:205-220`, `:282-295`; confirm the `scrubber`
  fixture in `test_build.py:1237-1252` is not an `abatement` unit, so its −0.9 keeps the kt
  reading. **New tests:** two trains on one host treat at most its activity in total (Decision
  7); captured streams in a host's proportions; no stream above $\nu$ times
  host production; a coal-only cement fixture now captures (today `screen_premise` drops the
  train); a train with no host in the model is dropped; the credit equals $\nu$ times the treated
  biogenic CO₂; Decision 4's choice asserted on the reboiler's stack; `capture_by_host` sums to
  `unit_flow`'s capture.
- **Docs:** `carb3/README.md:144` (objective), `:154-159` (the item 57 paragraph) and `:210`;
  `carb3/data/premises/README.md:299`; note 20 item 57 closed with the measured figures.
- **Verification:** `make check` passes. `mvp-cement` captures about 0.51 Mt/yr from 2035 and
  its objective falls by at least about £915m (section 6), or the difference is explained.
  `mvp-minimal` and `mvp-dairy` are unchanged, since neither holds a capture train.

### Task 4 (follow-on, not part of this change): re-solve the cement worked example

- **Goal:** the example quotes the rate form, and its §8.5.1 compares against the new run.
- **Files:** `docs/specs/2026-08-28-carb3-site-energy-system-worked-example-cement.md`: header
  (`:27-29`), §1.11's three rows and prose (`:470-472`, `:495`), §8.4's share table
  (`:1352-1357`, the shares at `:1354-1356`) and the old-blend prose under it (`:1359-1361`), §8.5.1
  (`:1478-1488`, `:1568`), the V31 row of §11 (`:1729`). Its hand solve already captures 90% of
  each stream at its own premise (`:1361-1368`), so §8.4's arithmetic stands and its prose does
  not.
- **The reboiler's factor** (`:475`, `:496`, `:1383`): the example derives its reboiler stack at
  its own 56.1 kt/PJ, so +106.59 kt per Mt, where the reference data's 51.12 gives 96.011 fossil
  plus 1.117 biogenic. *Recommended: the example keeps its own factor and says so at `:475`.* It is
  a hand solve on its own inputs (`:20-23`), §8.5.1's input table already lists 56.1 against 51.12
  (`:1532`), and aligning one factor would move every figure §8.1 to §8.5 derives from gas while
  leaving the other differing inputs in place. The live spec's §3.6 quote (`:1100`) then names
  it as the example's figure (Task 2).
- **Verification:** the example's §8.5.1 figures read from the new run's parquet tables.

## 9. What this plan does not settle

- **The other twelve trains.** None has a `fuel_input`, `aux_input` or `emission_input` row, so
  all twelve stay dropped. Their workbook rates are 0.1, and 0.35 for partial oxyfuel; their
  coefficients are a separate data item.
- **The train's life.** §8.5.1's second difference, that the slice annuitises the train over its
  own 30 years rather than its host's remainder (`build.py:1862`), is untouched.
- **`tgr_blast_furnace_coke`.** It draws 183 kt of `co2_process` per Mt of pig iron as
  `emission_input` (`unit_input_output.csv:335`) and declares no `co2_process` production of its
  own (`:326-335`), so wherever it is the only process-CO₂ maker, C8 (carrier balance) holds it at
  zero. COMIT's
  `IISTGRBF01` presumably meant a negative process emission, recycled top gas. Not this plan's,
  and it keeps its fixed form here; it is worth a note 20 item of its own.
- **Coincidence in time.** The model is annual, so it cannot check that a train and its hosts
  run in the same hours.

## 10. The cascade

Counted with `grep -rnE "557\.55|352\.57|89\.88|0\.55755|0\.35257|0\.08988" docs carb3`:
**31 lines in 8 files.**

| File | Lines | What happens to them |
|---|---|---|
| `docs/notes/data/unit_input_output.csv` | 3 | Task 3 |
| `carb3/data/reference_mvp/unit_input_output.csv` | 3 | Task 3, regenerated |
| `docs/specs/…-implementation.md` | 1 (`:1100`) | Task 2 |
| `carb3/README.md` | 1 (`:156`) | Task 3 |
| `docs/specs/…-worked-example-cement.md` | 10 | Task 4 |
| `docs/notes/20_reference_data_open_questions.md` | 7 | Kept as the record; item 57 gains a closing line |
| `docs/notes/21_mvp_slice_implementation_plan.md` | 5 | Kept as the record |
| `docs/notes/data/build/DONE_units.md` | 1 | Kept as the record |

So **8 lines change in Task 2 and 3, 10 in Task 4, and 13 stay as history.** The run figures
derived from the blend move as well: the 0.022764 Mt/yr cap and its 2.046 kt numerator in 4
lines of the cement example (`:1479`, `:1484`, `:1485`, `:1568`), 4 of note 20 and 5 of note 21;
the £4,554.93m objective in `carb3/README.md:144` and the cement example's `:1463`. The food and
drink example is not touched: its two `2.046` hits are an unrelated 2.04648 kt of CHP electricity
emissions.
