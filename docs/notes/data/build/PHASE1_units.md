# PHASE 1 — unit identity list ready

**`docs/notes/data/unit.csv` — 137 rows.** Identity columns only
(`unit_id, unit_name, unit_class, spine, duty_family, process_id, fuel_carrier_id,
is_hybrid, draws_ambient, abates_unit_id`, plus `provenance_ref`). All cost, efficiency
and coefficient columns are **blank until phase 2** — do not read them yet.

Also written: **`docs/notes/data/build/carrier_products_units.csv` — 15 rows**, the mass
products chemistry units produce, in `carrier.csv`'s own columns. `carrier.csv` itself is
untouched (it is the carriers lane's file).

## What downstream lanes can rely on now

| | |
|---|---|
| `unit_id` | Final. Unique, lower snake case. Safe to key on |
| `unit_class` | Final. `converter` / `generator` / `storage` / `hybrid` / `abatement` |
| `spine` | Final. `service` (family-keyed) or `chemistry` (node-keyed) |
| `duty_family` | Final for service units. One of the twelve of §3.3: `DRY, EN, HRS, HTH, LTH, MOT, NEUOTH, OTH, PHEAT, REF, SPC, STM` |
| `process_id` | Final for chemistry units, and resolves to `activity_process_register.csv` — **except the seven rows listed below** |
| `fuel_carrier_id` | Final. The D13 (one primary carrier per unit) fuel. Resolves to `carrier.csv`; blank for PV, batteries, thermal stores and the three steam-fed service units |
| `is_hybrid`, `draws_ambient` | Final |
| `abates_unit_id` | **Not yet usable** — see the open point below |

## Row counts

| Block | Rows |
|---|---|
| Service spine, from the D13 collapse of COMIT's 397 technologies | 66 |
| Chemistry spine, from the D13 collapse | 51 |
| Supply units the options library lacks (PV ×2, solar thermal, battery ×2, thermal store ×2, anaerobic digester) | 8 |
| Hybrid units (PD2 — programme decision on how storage acquires a value), 4 families × 3 fixed ratios | 12 |
| **Total** | **137** |

Every unit named in either worked example's §1.11 table is present verbatim — 31 of them,
checked by ID.

## Three things a waiting lane needs to know

1. **Seven chemistry rows carry a blank `process_id`,** because the CaRB3 register has no
   process for them: `glass_furnace_gas`, `glass_furnace_elec`, `glass_furnace_hydrogen`
   (no Glass Works activity exists at all), `ammonia_smr_gas`, `ccs_amine_ammonia`,
   `dri_midrex_gas`, `ccs_amine_dri`. Per convention 1 a blank beats a guess. If your lane
   keys on `process_id`, skip these seven rather than inventing a host.
2. **Eleven of the thirteen `abatement` units carry a blank `abates_unit_id`.** D13 split
   their host into several fuel-specific units — the cement kiln is three — and §3.5 gives
   `abates_unit_id` room for exactly one. Filling it would be a guess about which of the
   three the train bolts onto. `ccs_amine_ammonia` and `ccs_amine_dri` are the two that
   resolve, because their hosts were not split.
3. **`pv_rooftop`, `pv_ground_mount` and `solar_thermal_flat` carry `draws_ambient = TRUE`,**
   which the cement worked example's §1.11 coefficient table implicitly denies ("no unit here
   draws ambient heat"). Without the flag those units fail V2 (the round-trip energy-closure
   test), because their only coefficient is their output. Reasoning in `DONE_units.md`.

*Phase 2 — costs, efficiencies, `unit_input_output.csv` and `unit_bill_of_materials.csv` —
is in progress. `DONE_units.md` will land when it is complete.*
