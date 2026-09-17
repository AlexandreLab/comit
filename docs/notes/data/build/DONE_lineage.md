# DONE — lane `lineage`

**Deliverable:** `docs/notes/data/comit_technology_lineage.csv` — 397 rows, one per technology
in `emissions_source_classification.csv`, every row dispositioned.

| | |
|---|---|
| Generator | `docs/notes/data/build/build_lineage.py` (stdlib only) |
| Validator | `docs/notes/data/build/check_lineage.py` — 10 blocking checks, runs from any directory, exit 0 = green |
| Task | T8 (the COMIT technology lineage table); data migration A1–A3 and B1–B2 |
| Web research | none — this lane is a reconciliation, so no `references_lineage.csv` was created |

```
$ python3 docs/notes/data/build/check_lineage.py
comit_technology_lineage.csv: 397 rows
  collapsed  311
  preserved   64
  dropped     13
  unmapped     9
  TOTAL      397
distinct units reached: 108 of 137 in unit.csv
worked-example units: 32 named, 5 unreachable (battery_2h, heat_pump_lt_reject, kiln_dry_gas, kiln_dry_wdf, pv_rooftop)

OK - all checks pass
```

---

## 1. Row counts

397 in, 397 out, zero rows without a disposition.

| Disposition | Rows | Meaning as used here |
|---|---:|---|
| `collapsed` | 311 | Shares its `unit_id` with at least one other source row |
| `preserved` | 64 | Is the only source row mapping to its `unit_id` |
| `dropped` | 13 | Not site plant — see §5 |
| `unmapped` | 9 | Real plant, no unit in `unit.csv` — see §6 |
| **Total** | **397** | |

**108 of the 137 units in `unit.csv` are reached.** The 29 that are not divide into three
groups, and none is an error:

- **Twenty supply and hybrid units** COMIT's 397 technologies do not contain at all — `pv_rooftop`,
  `pv_ground_mount`, `solar_thermal_flat`, `battery_2h`, `battery_4h`, `thermal_store_hot_water`,
  `thermal_store_steam`, `anaerobic_digester` — eight — plus the twelve hybrids of PD2 (the
  programme decision on how storage acquires a value).
- **Four units the CaRB3 design adds** rather than collapses out of COMIT: `boiler_lt_oil`
  (`light_fuel_oil`, where COMIT's `Oil` category means LPG throughout the service spine),
  `boiler_lt_biomethane`, `chp_biomethane_ccgt` and `heat_pump_lt_reject`.
- **Five D13 (a unit is family-or-node × fuel) fan-out siblings** — `kiln_dry_gas`,
  `kiln_dry_wdf`, `kiln_dry_oil`, `lime_kiln_dry_coal`, `lime_kiln_dry_wdf`. These are reachable
  only through the `notes` column, and that is the one real limitation of this table: see §7,
  judgement call 1, and question Q1.

By spine: 62 of 86 service units and 46 of 51 chemistry units are reached.

By sector, every sector reconciles: Cement 11, Ceramics 25, Chemicals 55, Construction 7,
Electrical engineering 28, Food & drink 30, Glass 7, Hydrogen 7, Iron & steel 25, Lime 11,
Mechanical engineering 28, Non-ferrous metals 14, Other 38, Paper 43, Refineries 3, Textiles 30,
Vehicles 35.

## 2. Coverage, populated vs blank

| Column | Populated | Blank | Why blank |
|---|---:|---:|---|
| `technology_code` | 397 | 0 | — |
| `technology_name` | 397 | 0 | — |
| `sector` | 397 | 0 | — |
| `technology_category` | 397 | 0 | — |
| `output_commodity` | 397 | 0 | — |
| `carrier_id` | 362 | 35 | 21 `Steam` rows (§4), 13 `dropped` rows, 1 multi-fuel paper finishing row |
| `unit_type` | 397 | 0 | — |
| `abatement` | 25 | 372 | Only the 25 `CCS` rows carry a bolt-on |
| `disposition` | 397 | 0 | — |
| `unit_id` | 375 | 22 | 13 `dropped` + 9 `unmapped` |
| `fuel_carrier_id` | 354 | 43 | 13 `dropped` + 9 `unmapped` + the 21 `Steam` rows, whose units' own `fuel_carrier_id` is blank |
| `reason` | 397 | 0 | — |
| `notes` | 7 | 390 | Only where something needs saying |

`fuel_carrier_id` equals the mapped unit's own `fuel_carrier_id` on every one of the 375 mapped
rows — this is check 6 and it is blocking.

## 3. A1 — the three-column split

`technology_category` (11 values) became `carrier_id` (the fuel), `unit_type` (the device) and
`abatement` (the bolt-on).

**`carrier_id`** — seven of the eleven values are fuels and map straight onto `carrier.csv`:
`Electricity`→`electricity`, `Natural gas`→`natural_gas`, `Hydrogen`→`hydrogen`,
`Biomass`→`solid_biomass`, `Coal`→`coal`, `Oil`→`lpg`, and `Heat pump`→`electricity` (a device
whose fuel is electricity). `Steam` is handled in §4. `CCS`, `Standard_FF` and `Dry kiln` are not
fuels and were resolved per row — §5 and §6 of the brief's A2 and A3.

Resulting distribution: `electricity` 105, `natural_gas` 71, `hydrogen` 52, `solid_biomass` 46,
`coal` 38, `lpg` 33, `coke` 4, `petroleum_products_misc` 4, `coke_oven_gas` 3, `wood_pellets` 2,
`blast_furnace_gas` 2, `waste_derived_fuel` 2, blank 35. Every non-blank value resolves to
`carrier.csv` — blocking check 5.

**`unit_type`** — 26 device kinds: `boiler` 84, `generic_process` 64, `furnace` 38, `dryer` 36,
`chp` 31, `heat_pump` 31, `resistance_heater` 17, `kiln` 16, `demand` 13, `heat_exchanger` 11,
`motor` 10, `cracker` 10, `grinder` 6, `blast_furnace` 5, `reformer` 4, `chiller` 3,
`electrolyser` 3, `paper_machine` 3, `gasifier` 2, `rolling_mill` 2, `dri_shaft` 2, `refinery` 2,
`bof_converter` 1, `eaf` 1, `sinter_plant` 1, `feedstock` 1.

`unit_type` names the **device**, not the unit class. A cement amine train is
`unit_type = kiln`, `abatement = ccs` — read the three columns together and the row says "a kiln,
fuelled by gas, with a capture bolt-on", which is the orthogonality A1 asks for. `unit.csv` files
the same thing under `unit_class = abatement`; the two columns answer different questions.

**`abatement`** — `ccs` on exactly the 25 rows whose `technology_category` is `CCS`, blank on the
other 372.

## 4. `Steam` (21 rows) — `carrier_id` left deliberately blank

COMIT's `Steam` category is heat from CHP. `carrier.csv` represents heat as six graded bands
(`heat_lt60` rank 1 … `heat_gt1000` rank 6), and **the source row states no grade**. Per
convention 1 a blank is correct and a plausible band is a defect, so `carrier_id` is blank and the
row's `reason` says why. `unit.csv` agrees: the steam-fed service units
(`heat_exchanger_lt_steam`, `heat_exchanger_spc_steam`, `dryer_steam`, `generic_process_steam`)
carry a blank `fuel_carrier_id` for the same reason. See question Q5.

## 5. A2 — `Standard_FF` (39 rows), resolved explicitly

Every one was resolved by reading the technology name together with `emitting_fuel_commodities`,
as the brief directs. The outcome: 20 preserved, 13 dropped, 4 unmapped, 2 collapsed.

**Dropped (13).** Twelve sector demand technologies — `ICR01`, `ICH01`, `ICN01`, `IEE01`,
`IFD01`, `IGL01`, `IME01`, `INF01`, `IOI01`, `IPR01`, `ITX01`, `IVH01` — each of which converts a
sector's energy-service commodities into the sector demand commodity, with an empty
`emitting_fuel_commodities`, no cost and no capacity. The data migration's Group A excludes the
sector-level demand commodities by name. Plus `INDHFCOTH01`, "Dummy demand for Other HFC
emissions": a residual non-CO₂ bucket, not plant. V1b (parity against the frozen R run) compares
nothing through any of the thirteen.

**Resolved to a real fuel (22), in full:**

| Row | Resolved to | On what evidence |
|---|---|---|
| `ICMKLNWST02`, `ILMKLNWST02` | `waste_derived_fuel` | name "Fluidised bed kiln with waste utilisation" + `INDMSWINO` |
| `ICMLOCARB01`, `ILMLOCARB01` | `electricity` | "Alternative low carbon cement" is a grinding/blending step; `unit.csv` binds electricity |
| `IGLHTHNGA` | `natural_gas` | name says natural gas / biomethane boiler; `IND_NGABOM` present. Collapses into the HTH service spine |
| `IISBLAFUR01`, `IISTGRBF01` | `coke` | `INDCOK` present alongside `INDCOACOK`; `unit.csv` binds coke |
| `IISHISAR01` | `coal` | HISarna is a coal-direct smelter — `INDCOA` present and **no** `INDCOK`, unlike the blast furnaces |
| `IISBOXFUR01` | `coke_oven_gas` | `INDCOG` present |
| `IISCHPBFG01` | `blast_furnace_gas` | name "Gas turbine CHP based on blast furnace gas"; the works arising gas is not an emitting commodity, so the list is empty |
| `IISCHPCOG01` | `coke_oven_gas` | name "Gas turbine CHP based on coke oven gas"; `INDCOG` present |
| `IISSINTER01` | `coke` | `INDCOK` present |
| `IISMIDREX01` | `natural_gas` | `IND_NGABOM` present |
| `ICHCHPPRO01`, `ICHHVCSCO01`, `ICHNEUOTH01` | `petroleum_products_misc` | by-product / naphtha streams; COMIT commodity `INDNEUMSC` |
| `IPPCHPGT01` | `natural_gas` | `IND_NGABOMLFO` is COMIT's dual-fuel gas-turbine commodity; the D13 primary carrier is gas |
| `IPPPROPRS01`, `IPPPROOTH01` | `electricity` | only `INDDISTELC` in the emitting list |
| `POILREF01`, `POILREF02` | `natural_gas` | `IND_NGABOM` present |
| `ILMKLND01` | `natural_gas` | multi-fuel lime kiln — see judgement call 1 |

## 6. A3 — `Dry kiln` (1 row)

`ICMKLND01`, "Dry kiln, best available technology (BAT)". The category is a device, not a fuel.
`emitting_fuel_commodities` lists seven commodities
(`IND_NGABOM;INDCOA;INDDISTELC;INDHFO;INDLFO;INDMSWINO;INDMSWORG`) and `consumes_biomass_fuel` is
`TRUE`, so the source row is genuinely multi-fuel. D13 splits it into **four** single-fuel cement
kiln units. `unit_id` is `kiln_dry_coal` and all four are listed in `notes` — see judgement call 1.

## 7. Judgement calls

1. **One source row, several units — the two multi-fuel kilns.** `ICMKLND01` fans out to four
   cement kiln units and `ILMKLND01` to three lime kiln units, but the table's schema gives a row
   exactly one `unit_id`. I set `unit_id` to one variant and wrote the full fan-out into `notes`
   as `d13_fan_out=…`. The tie-break differs between the two rows, deliberately:
   - **Cement** takes `kiln_dry_coal`, because `unit.csv`'s `provenance_ref` for that unit opens
     `[CARB3_WE_CEMENT] 1.11 unit table` — the cement worked example, which is the V1b parity
     case, instantiates it.
   - **Lime** has no worked example, so the tie-break is COMIT's own ordering: the first entry in
     `emitting_fuel_commodities` is `IND_NGABOM`, giving `lime_kiln_dry_gas`. **That ordering
     looks alphabetical, so it is a weak signal.** It is recorded rather than hidden. Q2.

   **This is the one place where reading `unit_id` alone understates the lineage.** A V1b
   comparison that ignores `notes` will book all of `ICMKLND01`'s frozen capacity to
   `kiln_dry_coal`, when the cement worked example uses `kiln_dry_gas` and `kiln_dry_wdf` too.

2. **`disposition` semantics differ from the brief's wording, and the brief's cannot hold.**
   The brief defines `preserved` as "the 25 CCS, 31 heat pump, 1 dry kiln rows and every chemistry
   node". But the 31 heat pump rows are per-sector copies of four archetypes, so they demonstrably
   collapse (11 → `heat_pump_lt_air`, 8 → `heat_pump_spc_air`, 6 → `dryer_heat_pump`, 6 →
   `heat_pump_ht`), and 5 of the 25 CCS rows have no unit at all, so "25 CCS preserved" is
   arithmetically impossible. I therefore used the definition that carries information for V1b:
   **`collapsed` = the unit takes more than one source row, `preserved` = exactly one.** Blocking
   check 8 enforces it, so the two can never drift apart. B2's intent — do not fold a heat pump
   into an electric boiler, or a CCS row into its host — is honoured in full: no heat pump row
   maps to a `resistance_heater_*` or `boiler_*` unit, and no CCS row maps to its unabated host.
   Q3.

3. **The seven Hydrogen-sector rows are mapped, not dropped.** The brief offers
   "hydrogen-production sector rows that are not site units" as its example of a `dropped` row.
   They are site units in this model: `unit.csv` carries exactly seven units in the EN duty family
   — `electrolyser_alkaline`, `electrolyser_pem`, `electrolyser_soec`, `smr_gas_ccs`,
   `atr_gas_ccs`, `gasifier_biomass_ccs`, `gasifier_coal_ccs` — which map one-to-one onto them.
   Dropping rows that have a unit would make V1b blind to on-site hydrogen production. Q4.

4. **`emitting_fuel_commodities` names combustion fuels only; feedstock carbon books as process
   CO₂.** This bites three of the four CCS hydrogen rows and is worth knowing before anyone reads
   that column as "this technology's fuel":
   - `PHYGNGALQ01` (SMR with CCS): `emitting_fuel_commodities` is **empty** and the row is
     `A_pure_process` with 65.95 kt/unit process CO₂. The reformer's natural gas is feedstock.
   - `PHYGNGALQ02` (ATR with CCS): lists only `INDDISTELC`, the auxiliary electricity; 56.59
     kt/unit process CO₂.
   - `PHYGCOAQ01` (coal gasification with CCS): lists `INDMAINSGAS`, **not** coal. This is not the
     contradiction it looks like — the coal feedstock's carbon is the 109.32 kt/unit of process
     CO₂, and the mains gas is a real auxiliary burner at 5.64 kt/unit direct.

   In all three the carrier comes from the technology name and `unit.csv`'s binding, and the row's
   `reason` states the arithmetic. The same caveat applies to the chemistry nodes generally
   (blast furnace, ammonia, high-value chemicals).

5. **`ICHHVCSCN01`'s `Oil` is naphtha, not LPG.** Everywhere else in the service spine COMIT's
   `Oil` category resolves to `INDLPG`; on the naphtha steam cracker it is feedstock naphtha, and
   `unit.csv` binds `petroleum_products_misc`. Carried as a per-row override rather than letting
   the category default fire.

6. **`IGLKLN` and `IGLKLNHYD` bind their headline fuel, not their emitting list.** Both are
   furnaces "with electric boosting", so `emitting_fuel_commodities` carries `INDDISTELC`;
   `IGLKLNHYD` carries *only* that, because hydrogen combustion is not an emitting fuel. D13 gives
   a unit one primary carrier, and `unit.csv` binds `natural_gas` and `hydrogen` respectively.

7. **`ccs_amine_ironmaking` legitimately takes two source rows.** `IISHISARQ01` and `IISTGRBFQ01`
   are both named in that unit's own `provenance_ref`. Their `carrier_id` values differ (`coal`
   and `coke`, the host furnaces' fuels) from the unit's `fuel_carrier_id` (`natural_gas`, the
   amine train's reboiler fuel). Both rows carry a `notes` line spelling this out, because a V1b
   comparison must use the unit's binding, not the source row's.

8. **`chiller_electric_hfo` was kept separate from `chiller_electric`.** `ICHREFEHFO01` differs
   from `ICHREFEHFC01` in refrigerant, not fuel, and `unit.csv` keeps two units. The three `REF`
   rows therefore split 2 / 1.

## 8. Gaps — the 9 `unmapped` rows, and the units they need

Each is real plant with a real fuel and no unit in `unit.csv`. Per the brief, `unit_id` is blank
and the disposition is `unmapped`. **Request to the `units` lane — nine units:**

| Source row | Sector | What it is | Unit needed | Why not folded into an existing unit |
|---|---|---|---|---|
| `ILMKLNMAQ02` | Lime | Advanced amine (MDEA) train on a BAT lime kiln | lime MDEA train | The cement `ccs_amine_mdea` is cement-specific by `process_id = kiln_pyroprocessing`; lime is `kiln_calcination` |
| `ILMKLNMCQ01` | Lime | MEA train, coal CHP, lime kiln | lime coal-CHP MEA train | as above |
| `ILMKLNPOQ01` | Lime | Partial oxyfuel lime kiln with CCS | lime partial-oxyfuel train | as above |
| `ICHHVCSCQH01` | Chemicals | Steam cracker, post-combustion CCS **using excess heat** | HVC excess-heat capture | Folding it into `ccs_amine_hvc_gas` would assert a gas reboiler the source explicitly denies |
| `ICHHVCSCQN01` | Chemicals | Steam cracker, post-combustion CCS **with NGCC** | HVC NGCC capture | Reboiler steam from a gas CCGT, not a gas boiler — a different capex and a different auxiliary load |
| `IISBOIBFG01` | Iron & steel | Blast furnace gas boiler, low-temperature heat | `boiler_lt_bfg` | `carrier.csv` has `blast_furnace_gas`, but the only unit bound to it is `chp_bfg_gas_turbine` |
| `IISBOICOG01` | Iron & steel | Coke oven gas boiler, low-temperature heat | `boiler_lt_cog` | `carrier.csv` has `coke_oven_gas`, but the only unit bound to it is `chp_cog_gas_turbine` |
| `IISFINPRO01` | Iron & steel | Downstream steel finishing | steel finishing unit | Real energy use (`IND_NGABOM;INDDISTELC`), but its `output_commodity` `IIS` is the sector demand commodity |
| `IPPFINPRO01` | Paper | Paper converting / finishing | paper finishing unit | Seven fuels with no single primary; `output_commodity` `IPP` is the sector demand commodity |

The last two are the judgement call most worth a second opinion: they sit on a sector demand
commodity, which Group A excludes, yet unlike the twelve `…01` demand technologies they consume
fuel and have cost and capacity. I called them `unmapped` rather than `dropped` because dropping
them would silently delete real site energy from the V1b comparison. Q6.

**Two rows in `carrier.csv` with no unit to burn them.** `blast_furnace_gas` and `coke_oven_gas`
are each reachable only through a CHP unit today; the two boiler requests above would close that.

## 9. Requests to other lanes and to the coordinator

1. **`units` lane** — the nine units of §8.
2. **`units` lane** — the eleven `abatement` units with a blank `abates_unit_id` (PHASE1 note 2)
   are visible from this side too: `ccs_amine`, `ccs_amine_mdea`, `ccs_amine_coal_chp`,
   `ccs_oxyfuel` and `ccs_oxyfuel_partial` all map from cement rows whose host `ICMKLND01` D13
   split into four. This table's `notes` fan-out is the information needed to fill them, if the
   decision is ever to fill them at all.

   **Acted on 2026-09-17, and this note is what settled the count.** `abates_unit_id` is gone;
   `unit_abatement_host.csv` names every host of all thirteen trains. The five cement trains
   take **four** hosts each — `kiln_dry_coal`, `kiln_dry_gas`, `kiln_dry_wdf`, `kiln_dry_oil` —
   because this table's `d13_fan_out` on `ICMKLND01` says four, against a design note that named
   the three the cement worked example happens to reach. See `DONE_units.md` §8.
3. **Coordinator** — `docs/notes/data/README.md` needs a row for
   `comit_technology_lineage.csv`. It is the only index and an unregistered document is invisible;
   I did not edit it because it is a shared file (convention 6). Suggested row, matching the
   existing three-column shape: generated by `build/build_lineage.py`, validated by
   `build/check_lineage.py`.
4. **Coordinator** — if `build_lineage.py` and `check_lineage.py` should live outside `build/`
   alongside the other generators in `docs/notes/examples/`, say so; I left them in `build/`
   to match the `loadshape` lane.
5. **No `references_lineage.csv`.** Nothing in this lane cites an external source: every value is
   derived from `emissions_source_classification.csv`, `unit.csv` or `carrier.csv`, all already in
   the repository.

## 10. One observation outside this lane's scope

**`retrofit_to` is empty for all 397 rows** of `emissions_source_classification.csv`, although
`docs/notes/data/README.md` documents it as "Base technology this one retrofits, if any. Retrofit
costs are differenced against it." Every CCS row is a retrofit in COMIT, so the column being
uniformly blank means **the retrofit lineage cannot be derived from this file** — either
`build_emissions_classification.R` is not reading `Technologies!retrofit_to`, or the public
workbook ships that column empty. Anyone planning to reconstruct retrofit edges for the
abatement units should check the workbook directly first. Not this lane's file to fix.

## 11. Questions for Alexandre

**Q1.** The two multi-fuel kilns are the only genuine one-to-many rows in the table. Three options:
leave `unit_id` singular with the fan-out in `notes` (what I did); add a `unit_ids` column holding
a `;`-separated list; or have V1b apportion the frozen capacity across the siblings by a stated
rule. The third is the only one that makes the cement parity comparison exact, but it needs a
splitting rule and there is no source for one.

**Q2.** Should lime follow cement and take `lime_kiln_dry_coal`, for symmetry between two rows
with identical fuel lists? I used `lime_kiln_dry_gas` on COMIT's commodity ordering, which is
probably just alphabetical and so close to arbitrary.

**Q3.** Confirm the `disposition` definition of judgement call 2 — `collapsed` = the unit takes
more than one source row, `preserved` = exactly one. The brief's literal wording gives different
counts and cannot be satisfied as written.

**Q4.** Confirm the seven Hydrogen-sector rows should be mapped to the EN-family units rather than
dropped, as judgement call 3 argues.

**Q5.** Should `carrier.csv` gain a `steam` carrier, or is the graded-heat representation plus a
blank on the 21 `Steam` rows the right answer? Today those rows carry no carrier on either side of
the join, so the carrier balance (C8, the per-carrier energy balance) has nothing to bind them to.

**Q6.** The five unmapped CCS variants (3 lime, 2 high-value chemicals) and the two finishing
processes: build the units, or record them as deliberately out of scope? If out of scope they
should be `dropped` with a scope reason, not `unmapped` — the distinction matters because V1b
excludes a dropped row from *both* sides and merely fails to compare an unmapped one.

**Q7.** `PHASE1_units.md` says "the three steam-fed service units" carry a blank
`fuel_carrier_id`; there are four — `heat_exchanger_lt_steam`, `heat_exchanger_spc_steam`,
`dryer_steam` and `generic_process_steam`. Worth correcting in that note before it is quoted.

**Q8.** `chp_biomethane_ccgt`, `boiler_lt_biomethane` and `boiler_lt_oil` carry the
`provenance_ref` of a COMIT row they are not a collapse of (`ICHCHPCCGT01`, the natural gas LTH
rows, and the LPG LTH rows respectively). I treated all three as new units with no COMIT ancestor,
so they appear nowhere in this table. Confirm that is right — if any is meant to *share* a source
row's capacity with its gas or LPG twin, V1b needs to know.
