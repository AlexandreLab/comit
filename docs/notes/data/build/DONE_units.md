# DONE — lane `units`

> **Dated record.** Written against the schema of September 2026, before §3.6's `role`
> enum replaced the three booleans and widened the key. See the banner in
> [`00_CONVENTIONS.md`](00_CONVENTIONS.md); the live gate is `make check`.

Files written (and nothing else):

| File | Rows |
|---|---|
| `docs/notes/data/unit.csv` | 137 |
| `docs/notes/data/unit_input_output.csv` | 446 |
| `docs/notes/data/unit_bill_of_materials.csv` | 24 |
| `docs/notes/data/build/carrier_products_units.csv` | 15 |
| `docs/notes/data/build/references_units.csv` | 11 |
| `docs/notes/data/build/check_units.py` | the check script |
| `docs/notes/data/build/PHASE1_units.md` | the phase-1 handoff, landed first |

`python3 docs/notes/data/build/check_units.py` **passes all blocking checks**, from any
directory. It asserts the seven the brief names — unique `unit_id`, every worked-example unit
present, every `carrier_id` resolving, exactly one `is_primary_output` per unit with
coefficients, at most one `is_fuel_input`, bill-of-materials `capacity_share` summing to 1,
every `[REF_ID]` resolving — plus enums, booleans, foreign keys, placeholder strings, the
`(unit_id, carrier_id)` primary key, V2's `capacity_to_activity_factor` round-trip, and D15's
rule (every emission is a carrier) that no `co2_fuel_*` row is ever authored as produced.

---

## 1. Where the 137 units came from

| Block | Rows | Derivation |
|---|---|---|
| Service spine, from the D13 (one primary carrier per unit) collapse | 66 | COMIT's 397 technologies, grouped by the 3-letter duty-family suffix of `process_commodity` × technology fuel |
| Chemistry spine, same collapse | 51 | The 14 node commodities with a mass denominator, × fuel |
| Supply units the options library lacks | 8 | PV ×2, solar thermal, battery ×2, thermal store ×2, anaerobic digester |
| Hybrids, PD2 (hybrid units at a fixed sizing ratio) | 12 | 4 families × 3 durations |

The brief expected ~55 service and ~40 chemistry. It came out **66 and 51**. Five things
account for the difference, all deliberate and all recorded in the rows' `provenance_ref`:

1. **The twelve service families, not eight.** §3.3 enumerates `DRY, EN, HRS, HTH, LTH, MOT,
   NEUOTH, OTH, PHEAT, REF, SPC, STM`. The four easy to miss map onto COMIT `HYGEN`
   (hydrogen generation, 7 units), `IISHRS` (hot rolled steel, 2), `PCHPHEAT` (refinery
   process heat, 1) and `ICHNEUOTH` (non-energy use, 1) — 11 units on their own.
2. **Biomethane is a carrier, and COMIT's `IND_NGABOM` is gas and biomethane together.**
   D13 therefore forces `boiler_lt_biomethane` and `chp_biomethane_ccgt` into existence.
3. **Light fuel oil likewise.** COMIT files oil-fired low-temperature heat under `LPG01`;
   `carrier.csv` separates `lpg` from `light_fuel_oil`, so `boiler_lt_oil` exists.
4. **Abatement is a unit (§3.5), so COMIT's whole-plant capture technologies became 13
   separate trains** rather than 13 more kilns.
5. **Lime mirrors cement.** COMIT carries `ILMCLK`/`ILM` as a near-copy of `ICMCLK`/`ICM`,
   and the collapse reproduces that.

Every unit named in either worked example's §1.11 table is present verbatim — 31 of them,
asserted by the check script.

## 2. Coverage

### `unit.csv`, 137 rows

| Column | Populated | The blanks are |
|---|---|---|
| `unit_id`, `unit_name`, `unit_class`, `spine` | 137 | — |
| `is_hybrid`, `draws_ambient`, `emissions_released` | 137 | — |
| `provenance`, `confidence`, `provenance_ref` | 137 | — |
| `duty_family` | 75 | the 51 chemistry units (node-keyed) and the 11 supply and PV/battery hybrid rows that serve no duty |
| `process_id` | 47 | the 66 service units (family-keyed), the 17 supply and hybrid rows, and **7 chemistry units with no CaRB3 process** — see §4 |
| `fuel_carrier_id` | 123 | 4 steam-fed units, PV ×2 + PV hybrids, solar thermal, batteries ×2, thermal stores ×2 |
| `capex`, `fixed_opex` | 122 | 15: solar thermal, both thermal stores, the digester, and 11 of the 12 hybrids |
| `lifetime`, `availability_factor`, `capacity_to_activity_factor` | 124 | 13, the same set less the three `pv_battery_*` rows |
| `grade_out` | 52 | every non-heat duty (`MOT`, `REF`, `EN`, `HRS`, `NEUOTH`, `OTH`), all chemistry, all supply units |
| `grade_in_max` | 8 | set only where a unit genuinely draws heat as a source |
| `area_per_capacity` | 5 | correct — §3.5 says set it **only** on area-bound units. PV ×2 and the three `pv_battery_*` packages carry it; every boiler, CHP, kiln and battery leaves it unset and is outside C12 (the siting cap) |
| `min_viable_scale` | 0 | **a gap.** See §4 |
| `load_shape_override` | 0 | correct — §3.5 makes it by exception only, and no source states an exception |
| `abates_unit_id` | 2 | **a gap.** See §4 |

Provenance mix after the phase-3 published-source pass (§7): 92 rows `comit_reuse` (69 high
confidence, 23 medium), 24 `bref` (11 medium, 13 low), 21 `proxy` (all low).

### `unit_input_output.csv`, 446 rows over 111 units

Every column is populated on every row. 100 rows carry `is_fuel_input`, 36 carry a declared
`co2_process` coefficient, 59 carry `is_reject` (2 from the food and drink worked example, 57
added in the phase-3 pass of §7). **No row carries a produced `co2_fuel_*`
coefficient**, which is D15's rule: A6 derives those at build time from the scenario's
factors. The four `co2_fuel_*` rows that do appear are all *consumed* by `ccs_amine`.

26 units have no coefficients at all. They fall into five groups, each a real gap, not an
omission — §4 names them.

### `unit_bill_of_materials.csv`, 24 rows over all 12 hybrids

`capacity_share` is populated on all 24 and sums to 1 per hybrid. `capex_share` is populated
on 2 rows (`pv_battery_2h`) and blank on 22; `component_lifetime` is blank on the 6 thermal-store
components. See §4.

---

## 3. Judgement calls

**(a) COMIT is the source of record for attributes; the worked examples are the source of
record for coefficients.** This is the largest call in the lane and it needs stating plainly.
The two worked examples state costs (`kiln_dry_coal` at £260m per Mt/yr, `chp_gas_turbine` at
£38.0m per PJ/yr) that the COMIT workbook does not agree with (£114.78m and £51.43m). Their
own §1.11 presents them as a **specification fixture**, and §12 of the cement example calls it
"the published fixture (`MF-23`)". Baking fixture economics into reference data every premise
reads would be wrong, so `capex`, `fixed_opex`, `lifetime`, `availability_factor`,
`capacity_to_activity_factor` and `emissions_released` come from COMIT wherever COMIT has a
row. Coefficients are the other way round: the worked examples' rows are graded-carrier-aware,
carry the COP-by-lift that data migration item B4 exists to produce, and carry the reject-heat
rows COMIT has none of — so where a worked example declares a unit's coefficients, those are
used verbatim (18 units, 52 rows, `provenance = proxy`, confidence medium).
**The consequence is that re-running either worked example against this reference data will
reproduce its energy flows and not its £ figures.** That is a question for Alexandre, in §5.

**(b) Cross-sector spread is resolved by the median.** D13's collapse is exactly the claim
that one `boiler_gas` serves a dairy and a paper mill. COMIT often carries different numbers
for the same family and fuel in different sectors — `LTH`+`NGA01` has 9 sector copies spanning
£1.57m–£4.49m per PJ/yr. The median is taken and the count and range are written into the
row's `provenance_ref`; confidence drops to medium wherever a spread exists.

**(c) CHP costs are converted from GW to PJ/yr, with the arithmetic in the pointer.** COMIT
rates CHPs in GW of heat output (`capacity_to_activity_factor` 31.54); CaRB3 service units are
PJ/yr with γ = 1.0. Every CHP row carries `capex / 31.54` and says so. **This was wrong in the
phase-2 hand-off and §7 corrects it**: the divisor also carried the availability factor, which
does not belong there, because capacity is a full-output rating and availability multiplies
activity, not capacity. Twelve CHP rows were overstated by 1/α, between 5 % and 11 %.

**(d) The D13 fuel split sums COMIT's fuel rows, but only where one COMIT technology became
several CaRB3 units.** That is true of exactly two technologies: `ICMKLND01` (the cement dry
kiln, which became four units) and `ILMKLND01` (the lime kiln, three). There the whole
combustion-fuel energy moves onto each unit's own carrier, with the summed terms listed in the
pointer. Everywhere else COMIT already has one technology per fuel, so its own rows are kept
and `is_fuel_input` simply marks the row whose carrier is the unit's D13 fuel. An earlier pass
applied the sum everywhere and produced a naphtha steam cracker consuming 96.7 PJ of
"petroleum products" that was really naphtha plus gas plus two fuel oils on one row.

**(e) `kiln_dry_oil` consumes 4.60 PJ per Mt, not the 3.83 the sum gives.** The cement example
states "Each kiln unit consumes 4.60000 PJ per Mt clinker … of its own single fuel", and the
fourth unit split off the same COMIT technology has to agree with the three the example
declares. Flagged `proxy`.

**(f) PV and solar thermal carry `draws_ambient = TRUE`, against the cement example's word.**
That example's §1.11 says "no unit here draws ambient heat, so its exemption is not needed",
while listing `pv_rooftop` with a single coefficient (`electricity` +1.00000) in the same
table. A unit whose only coefficient is its output cannot round-trip; sunlight is outside the
carrier set by exactly the argument §3.6 makes for ambient air. The flag is set and the
example's sentence is recorded in §5 as a defect.

**(g) Heat-band assignment by duty family, at low confidence.** `grade_out` is taken verbatim
from the food and drink example for the 15 units it states (`LTH` boilers at rank 3, the
low-temperature heat pumps at 2, `heat_pump_ht` at 3 with `grade_in_max` 2, the dryers at 4)
and extended to the rest of each heat family: `SPC` → 1, `STM` → 3, `DRY` → 4, `HTH` → 5.
**The band set is not mine to fix** — the food and drink example says so itself, and `T17`
(give every process a duty family and a heat grade) owns it. Every extended row is low
confidence and will need revisiting when T17 lands.

**(h) The hybrid sizing ratio is this lane's, because PD2 leaves it open.** Every package is
one unit of the converting component to half a unit of the store, so `capacity_share` is
0.66667 / 0.33333 throughout; what varies across the 2h/4h/8h members is the store's
*duration*, hence its cost, not its rating. A hybrid's coefficients are its converting
component's, because a store shifts output in time and adds no coefficient.

**(i) `emissions_released` is 1.0 on every row, capture units included.** D15 puts the capture
rate in the coefficients, not in this field. COMIT's own values (0.1 for full capture, 0.35 for
partial oxyfuel) are therefore *not* carried across; they belong in the capture trains'
coefficients, which this lane could not source — see §4.

**(j) Non-CO₂ emissions and raw materials are dropped.** COMIT's `INDHFCP` (refrigerant HFCs),
`INDN2OP` and `INDCH4P` rows are not carriers — §7.2 says non-CO₂ gases are tracked separately
and CCS never abates them. Limestone, iron ore, scrap, oxygen and lime inputs (`MCM…`, `MIS…`,
`IISSIR`) are materials, not carriers, and are dropped too. `PRCOILCRD` (crude oil) is dropped
for the same reason, though it is arguably a feedstock carrier the set is missing — §5.

---

## 4. The gaps, and why each is a gap

**G1 — no CaRB3 carrier for the `OTH` and `NEUOTH` duty families (8 units, no coefficients).**
`generic_process_{gas,hydrogen,biomass,coal,lpg,elec,steam}` and `non_energy_use_feedstock` are
the D13 collapse of COMIT's 63 "other energy services" rows and its one non-energy-use row,
and `carrier.csv` has nothing they can produce. They need an `other_service` intermediate carrier
and a feedstock carrier. **This is a request to the carriers lane**, not something this lane
may write: convention 6 forbids touching `carrier.csv`.

**G2 — no coefficients for 12 of the 13 capture trains.** §3.5 makes abatement a unit whose
primary output is `co2_captured`. COMIT has no such thing: `ICMKLNMAQ02` is a *whole kiln with
MDEA capture*, not a bolt-on train, so translating it yields a kiln producing clinker. The only
capture train with sourced coefficients is `ccs_amine`, which the cement example declares in
full. **A method exists and is arithmetic, not judgement**: subtract the unabated technology
from the captured one (`ICMKLNMAQ02` − `ICMKLND01` gives −1.948 PJ extra coal, −1.411 PJ extra
waste fuel and −0.900 PJ extra electricity per Mt clinker) and divide through by the CO₂
captured per Mt clinker to re-base onto `co2_captured` = +1. It needs a decision about which
host the subtraction is against, which is G3, so it was left undone rather than guessed.

**G3 — `abates_unit_id` is blank on 11 of 13 abatement units.** D13 split their hosts into
several fuel-specific units — the cement kiln is three — and §3.5 gives `abates_unit_id` room
for one. The cement example says the train "names it in `abates_unit_id`" without saying which
of the three. Only `ccs_amine_ammonia` and `ccs_amine_dri` resolve, because their hosts were
not split. **This is a specification gap, not a data gap**, and §5 puts it to Alexandre.

**G4 — seven chemistry units have no `process_id`.** The CaRB3 register has no Glass Works
activity at all (`glass_furnace_{gas,elec,hydrogen}`), no ammonia process (`ammonia_smr_gas`,
`ccs_amine_ammonia`) and no direct-reduced-iron process (`dri_midrex_gas`, `ccs_amine_dri`).
A blank beats a guess. **A request to whoever owns `activity_process_register.csv`.**

**G5 — `min_viable_scale` is empty on all 137 rows.** The food and drink example states
`min_duty` (0.01 PJ/yr for the low-temperature heat pumps, 0.03 for the CHPs, 0.25 for the
biomass steam-turbine CHP), but `min_duty` is a column of `unit_eligibility` (§3.5.1), which is
the eligibility lane's file. Whether `unit.min_viable_scale` should mirror it, or hold
something different, is §5's question.

**G6 — `is_reject` now appears on 59 rows out of 446, from one whole-of-industry fraction.**
**Closed in part by §7.** Every fuel-fired unit now rejects 12.03 % of its fuel energy onto
`heat_lt60`, from the DECC 2014 surplus-heat study. What is still missing is the *variation*:
no per-duty-family or per-node fraction was found, so a cement kiln and a space-heating boiler
reject the same share of their fuel, which they certainly do not. §7 records the one attempt at
a cement-specific figure and why it failed.

**G7 — no cost for thermal stores, the digester, solar thermal, or 11 of the 12 hybrids.**
**Partly closed by §7**: `battery_2h` and `battery_4h` are now priced from the BEIS storage
study, so the duration problem that blocked them is gone. What remains has no UK published
figure this pass could find: a hot-water thermal store, a steam accumulator, an anaerobic
digester and a flat-plate solar thermal collector. The BEIS storage study does carry a
"Thermal Energy Storage (200 MW, 800 MWh)" case, but that is electricity-in/electricity-out
storage, not a heat buffer, so it was not used.

**G8 — storage round-trip efficiency cannot be expressed, so batteries and thermal stores have
no coefficients.** A store consumes and produces the *same* carrier, and §3.6 keys
`unit_input_output` on `(unit_id, carrier_id)`, so the two rows cannot coexist. **This is the
same schema defect the cement example already records for `ccs_amine`**, which needs
`co2_fuel_fossil` at −0.35257 (captured from the kiln) and at +0.10659 (produced by its own
reboiler) and can hold only one. It is not a corner case: it blocks every storage unit in the
library, and PD2 makes storage a programme-level commitment.

**G9 — two COMIT lime-kiln values look physically wrong and were carried through unchanged.**
`ILMKLND01` gives 0.86 PJ per Mt of quicklime and `ILMKLNWST02` gives 51.49 PJ per Mt; a real
lime kiln is around 5–6 PJ/Mt. The second is so far out that `lime_kiln_fluidbed_wdf` has no
`is_fuel_input` row at all (its waste-fuel coefficient in COMIT is zero and its gas coefficient
is the 51.49). Both are flagged here rather than silently corrected.

**G10 — `heat_exchanger_lt_steam` has no coefficients, because its input and output land in the
same band.** COMIT's `…LTHSTM01` takes site steam and delivers low-temperature heat. With `LTH`
→ rank 3 and `STM` → rank 3 that is a unit consuming and producing `heat_100_150`, which is the
circular node the worked examples warn about for `MOT` (motors) and `REF` (refrigeration).
Emitting the +1.00000 output row on its own would have made the heat free, so nothing was
emitted. `heat_exchanger_spc_steam`, `dryer_steam` and `generic_process_steam` do not have the
problem, because their outputs sit in different bands. **T17's band set fixes this**, or LTH
needs a rank below STM.

**G11 — CLOSED by §7.** Four published UK sources were fetched and read, 24 units now carry
`provenance = bref`, and 57 reject rows exist where there were none. What the pass could *not*
find is listed in §7.4.

---

## 5. Questions for Alexandre

1. **Should the worked examples' costs win over COMIT's, or the other way round?** This lane
   chose COMIT (judgement call (a)). The consequence is that the two published fixtures
   reproduce their energy flows against this data and not their £ figures — `kiln_dry_coal` is
   £114.78m per Mt/yr here against the cement example's £260m, `chp_gas_turbine` £51.43m per
   PJ/yr against £38.0m. If the fixtures are meant to be runnable end to end against the
   reference data, this is the wrong way round and I will flip it.
2. **Which host does a capture train name in `abates_unit_id` when D13 has split the host into
   three?** Three options: (i) point at the node's dominant-fuel unit and accept that the
   answer moves when the dispatch split moves; (ii) make `abates_unit_id` a `process_id`
   instead of a `unit_id`, which matches how the cement example actually reasons about it;
   (iii) create one train per host unit, tripling the abatement block. Until this is settled
   G2 and G3 both stay open. (ii) looks right to me.
3. **`unit_input_output`'s `(unit_id, carrier_id)` primary key blocks two real cases** — every
   storage unit (G8) and `ccs_amine`'s reboiler CO₂, which the cement example already flags
   with a ⚠. Adding a `flow_direction` or `role` column to the key would fix both at once.
   Worth raising as a spec change?
4. **Should `unit.min_viable_scale` mirror `unit_eligibility.min_duty`, or is it a different
   threshold?** §3.5 calls it "a screening threshold, applied in A2 (the relaxation ladder's
   sibling) — never a binary" and §3.5.1 says the same of `min_duty`. If they are the same
   number in two places, one of them should go.
5. **PV's capacity factor is 0.10 in the cement example and 0.11 in the food and drink one.**
   0.11 is used here. Which is intended, and should it be per-site rather than a library
   constant?
6. **`carrier.csv` needs three rows this lane could not write** (convention 6): an
   `other_service` intermediate for the `OTH` family, a feedstock carrier for `NEUOTH`, and a
   `crude_oil` primary for refining. Without the first two, 8 units have no coefficients (G1).
7. **Is 137 units the right size?** The brief expected ~98 before hybrids and this is 125
   before hybrids, for the five reasons in §1. If the library should be smaller, the `OTH`
   family (7 units) and the lime block (10) are the two obvious places to cut.
8. **`earliest_year` is named in §3.5's prose** ("capex, `lifetime`, `availability_factor`,
   `earliest_year` and `min_viable_scale` all differ by fuel") **but is not a column in §3.5's
   field table.** It is a column of `unit_eligibility` (§3.5.1). Either the prose or the table
   is wrong; COMIT's `Technologies.start_year` would populate it directly if it belongs here.
9. **§3.6 says every non-ambient unit "must close on energy to 1e-6 (V2)", and V2 does not say
   that** — §10.3 defines V2 as "`capacity_to_activity_factor` and `io_coefficient` round-trip
   per unit to 1e-6". They are different tests, and the food and drink example's own
   `boiler_lt_gas` (+1.00000 heat, −1.13636 gas) fails the first and passes the second. The
   check script asserts the round-trip. Which did §3.6 mean?
10. **The cement example says "no unit here draws ambient heat" while listing `pv_rooftop`**
    whose only coefficient is its output (judgement call (f)). I read that as a defect in the
    sentence rather than in the flag, but it is the example's assertion and worth a decision.

---

## 6. How to rebuild

The three CSVs are generated, not hand-written. The generators are session scratch and are
**not** committed; they read the COMIT workbook through R `readxl` (sheets `Technologies` and
`technology_input_output`, both with two title rows) and write the three files in one pass. If
the files need regenerating rather than editing, say so and they can be promoted into
`docs/notes/examples/` alongside the other generators, with a `--check` mode like
`build_interface_docs.py`'s.

---

## 7. Phase 3 — the published-UK source pass

The brief's source order puts published UK work ahead of the COMIT workbook, and §4's G11
recorded that none of it had been fetched. This pass fetched and **read** four such documents
and rebuilt the three CSVs from scratch through them. Nothing here is a search-result summary:
every figure below was read out of the PDF text, and the citation in each row's
`provenance_ref` names the table and page it came from.

### 7.1 What was found, and what it replaced

| Source | What it gave | Rows changed |
|---|---|---|
| **`[BEIS_IFS2018]`** Industrial Fuel Switching Market Engagement Study (Element Energy and Jacobs for BEIS, Dec 2018), §7.2 tables pp 64–66 | Marginal capex £/kW, marginal opex £/kW/yr and lifetime for 22 fuel-switching technologies, plus §7.3's 1.4 MWh/tonne glass melting figure | **22 units** |
| **`[BEIS_STORAGE2018]`** Storage cost and technical assumptions for BEIS (Mott MacDonald, Aug 2018), Tables 6 and 30 | Lithium-ion capex £/kW and opex £/kW/yr by duration and year; round-trip efficiency 85 %; life 15 yr | **2 units** |
| **`[DESNZ_EGC2023]`** Electricity Generation Costs Report 2023, Table 3 | Solar PV fixed O&M, £6,000/MW/yr, already in 2021 prices | **2 units** |
| **`[DECC_SURPLUSHEAT2014]`** The potential for recovering and using surplus heat from industry (Element Energy, Ecofys, Imperial for DECC, 2014) | 48 TWh/yr rejected as concentrated sources, 13 TWh/yr of it in unrecoverable hot solids, against ca. 291 TWh/yr of UK industrial heat energy use | **57 new `is_reject` rows** |

`provenance` moves to **`bref`** on the 24 units whose cost now comes from a published source —
the enum has no `published_external` value and `bref` is the closest of the three.
`comit_reuse` falls from 113 rows to 92.

**The conversion, stated once.** A unit's capacity is a full-output rating, so
1 PJ/yr of capacity = 10¹⁵ J ÷ 31,536,000 s = **31,709.8 kW**, and

> £m per PJ/yr = (£/kW) × 31,709.8 × 10⁻⁶ × *deflator to 2021*

No availability factor enters: availability multiplies *activity*, not capacity. Neither the
fuel-switching study nor the storage study declares a price base, so each is taken as money of
its publication year and deflated with the COMIT workbook's own `gdp_deflators` sheet (GDP
deflator at market prices, 2022 = 100): **2018 → 2021 is 95.1126/88.7354 = 1.07185**, and
**2020 → 2021 is 95.1126/95.4171 = 0.99681**. Every changed row carries its own arithmetic.

**Worked example, `boiler_lt_gas`.** `[BEIS_IFS2018]` row "Natural gas boiler": £166.00/kW,
£3.32/kW/yr, 25 yr. 166.00 × 31,709.8 × 10⁻⁶ × 1.07185 = **£5.6421m per PJ/yr**, against
COMIT's £2.277m. The published figure is 2.5× COMIT's, because it is a total installed cost
including the civils and connection work COMIT's row does not carry.

Selected before-and-after, £m per PJ/yr (or per Mt/yr for glass):

| Unit | COMIT | Published | Source row |
|---|---|---|---|
| `boiler_lt_gas` | 2.2770 | **5.6421** | Natural gas boiler |
| `boiler_lt_hydrogen` | 2.7594 | **6.7638** | 100% H2 Fuel Boilers |
| `boiler_lt_biomass` | 13.4935 | **17.5042** | Large Biomass Steam Boiler |
| `resistance_heater_lt` | 4.9221 | **4.0786** | Electrode Steam Boiler (large) |
| `heat_pump_lt_air` | 25.4549 | **15.2949** | CL Heat Pump |
| `heat_pump_ht` | 25.4549 | **10.1966** | OL Heat Pump (MVR) |
| `furnace_ht_gas` | 4.3178 | **6.5598** | Natural gas fired furnace |
| `dryer_electric` | 3.8571 | **4.0786** | Electric Process Heater |
| `glass_furnace_elec` | 380.22 | **33.06** | Electric glass furnace, rebased through 1.4 MWh/t |
| `battery_2h` | *(fixture 0.58 £m/MW)* | **0.6884** | interpolated 1 h → 4 h |
| `battery_4h` | *(blank)* | **1.1192** | CPL-DA 10 MW / 40 MWh |

`glass_furnace_elec` is the largest single move, and it is worth a second look before it is
quoted: COMIT's £380.22m per Mt/yr becomes £33.06m, an order of magnitude. The direction is
right — `[BEIS_IFS2018]` §7.3 quotes Fives Glass that "electric furnace systems require capital
investment comparable or less than fuel fired alternative technologies" and the gas furnace here
is £162.95m — but a 4.9× gap between a published figure and COMIT's is large enough that one of
the two is measuring something the other is not.

The two heat-pump rows are the largest correction in the set, and they move the right way:
COMIT carries **one** flat £25.45m per PJ/yr heat pump for every family and every lift, which
is the same defect as its flat COP that data migration item B4 exists to fix. The published
study separates a closed-loop machine (£450/kW) from open-loop mechanical vapour recompression
(£300/kW), and the library now does too.

**`battery_2h` is the one interpolation in this pass.** The storage study has a 1-hour case
(frequency management, 50 MW / 50 MWh, £474.5/kW) and a 4-hour case (co-located peak lopping,
10 MW / 40 MWh, £1,122.8/kW) and nothing between. Linear in duration gives £216.10/kW per hour
and £690.60/kW at two hours. **The two anchors are at different plant scales**, which the
interpolation cannot separate from the duration effect, so the row is confidence `low` and says
so. `battery_4h` needs no interpolation: the co-located peak-lopping case *is* PD2's use case —
a battery sited to defer a connection reinforcement — and is used directly.

### 7.2 The reject-heat rows (G6)

`[DECC_SURPLUSHEAT2014]` §4.1 states: *"Of all heat consumed by industry, some 48 TWh/yr is
rejected as concentrated heat sources, 13 TWh/yr of this is in the form of heat contained in
hot solids … not taken into account … as no technology is currently available that is suited to
practically recover this heat"*, against *"overall UK industrial heat energy use (ca. 291
TWh/yr)"* at its footnote 15. So the recoverable, non-solid reject stream is

> (48 − 13) / 291 = **0.12027 of fuel energy in**

and each row's coefficient is 0.12027 × |its fuel coefficient|, per unit of output. For
`boiler_lt_gas` that is 0.12027 × 1.13636 = **+0.13668**; for `kiln_dry_coal`,
0.12027 × 4.60000 = **+0.55326** per Mt of clinker.

**Why 48 − 13 and not 11.** The study also reports an 11 TWh/yr *technical* potential, 7 TWh/yr
economic and 5 TWh/yr commercial. Those three already net off the temperature matching, the
distance and the payback — which are exactly what C10 (the heat cascade), C8 (carrier balance)
and the objective decide for themselves. `is_reject` describes what physically leaves the unit,
so the right layer is the 35 TWh/yr of recoverable stream, not the 11 TWh/yr that survives the
study's own screening. Using 11 would double-count the screening.

**Which units get a row.** A unit qualifies when it has an `is_fuel_input` row on a combustion
carrier — electricity and intermediate carriers are excluded, because an electric heater has no
flue stream. Abatement units (no coefficients at all) are excluded, as are the two food and
drink dryers that already declare a reject row, and any unit whose own output is `heat_lt60` or
which already trades on that band, which would make the node circular. **Three units were
excluded deliberately**: `steam_cracker_naphtha`, `steam_cracker_byproduct` and
`ammonia_smr_gas`, whose fuel row is the summed one that conflates feedstock with fuel (§3(d)),
so 12 % of it would be 12 % of the naphtha as well.

**Banded on `heat_lt60`, and that is conservative.** The study's low source band is
ambient–250 °C and holds 31 of the 48 TWh/yr; its sinks concentrate at 0–150 °C; and the food
and drink example bands its dryer reject the same way. Putting a 250 °C stream in band 1 throws
away exergy the cascade could otherwise use, so **this is a floor on what the cascade can do,
not an estimate of it.**

**One fraction for every unit is the weakness.** A cement kiln and a space-heating boiler now
reject the same share of their fuel. They do not.

### 7.3 One correction to phase 2

The GW → PJ/yr rebasing of COMIT's CHP costs divided by the availability factor as well as by
31.54. Capacity is a full-output rating and availability multiplies activity, so the divisor is
31.54 alone. Twelve CHP rows were overstated by 1/α — between 5 % and 11 %.
`chp_gas_turbine` moves from £51.43m to **£47.83m** per PJ/yr. §3(c) is corrected.

### 7.4 What the pass looked for and did not find

- **A cement-kiln-specific reject fraction.** The `[CLM_BREF2013]` cement, lime and magnesium
  oxide BREF was downloaded and read. It gives a modern dry kiln heat consumption of 3,300
  kJ/kg clinker (§1.3.3), a top-stage preheater exhaust at 300–400 °C (§1.2.5.3.4) and a clinker
  cooler waste heat output of **14 MW at 300 °C** (§1.4.2.4) — but states no clinker throughput
  for that plant, so the 14 MW cannot be turned into a fraction of fuel input without inventing
  the denominator. The ECRA/CEMBUREAU *Energy performance of cement kilns* heat balance, which
  would have it, returned 404, and the open-access Wiley kiln heat-balance paper returned 403.
  The reference row for the BREF is in `references_units.csv` as **evidence of absence**.
- **A UK £/MW capital cost for PV.** `[DESNZ_EGC2023]` Table 3 gives total construction cost in
  £m but not the plant capacity it is divided by, so no £/MW can be read from it; its fixed O&M
  *is* per MW and is used. The DESNZ *Solar PV cost data* statistics release now carries only
  2025–26 data. `pv_rooftop`'s capex therefore stays at the worked-example fixture, £0.62m/MW.
- **Electrolyser capex.** `[DESNZ_H2COSTS2021]` was downloaded, but its CAPEX values live in
  charts and a companion spreadsheet, not in the PDF text, and nothing in £/kW could be read
  out. COMIT's £46.63m per PJ/yr stands — which is £1,470/kW, a defensible 2020-era PEM figure.
- **CHP capex.** No Carbon Trust or DESNZ CHP cost guide was reached in this pass. COMIT stands,
  with the §7.3 correction. `chp_biomass_st` at £152.07m per PJ/yr against the food and drink
  example's £61.0m is the widest COMIT-versus-fixture gap left in the library and is worth a
  look before anyone quotes it.
- **A hot-water thermal store, a steam accumulator, an anaerobic digester, a flat-plate solar
  thermal collector.** No UK published capital cost found. Still blank (G7).
- **The DESNZ 2024 electrification-of-industrial-heat and industrial-heat-pump cost studies** the
  brief names could not be located under those titles on gov.uk; the searches returned the
  residential Electrification of Heat demonstration project instead. If Alexandre has the exact
  titles or URLs, the heat-pump rows are the ones that would benefit most.
- **CCC Sixth Carbon Budget technology tables.** Not reached this pass.

### 7.5 What phase 3 did not touch

Coefficients other than the new `is_reject` rows. The published study states a fuel input ratio
per technology — 1.09 kWh fuel per kWh output for a gas boiler, against the food and drink
example's 1.13636, and 0.25 for a closed-loop heat pump against the example's 0.35710 — but
judgement call (a) keeps the worked examples as the source of record for coefficients, and
changing them would break the two published fixtures for a second-order gain. The published
ratios are recorded here as a cross-check, not applied.

**Question 11 for Alexandre:** `provenance` is an enum of `{comit_reuse, bref, proxy}` and 24
rows now hold a figure from a UK government study that is not a BREF. `bref` is the closest
value but it is not the true one. Should the enum gain a `published` value, or is `bref` meant
to read as "published external" generally?
