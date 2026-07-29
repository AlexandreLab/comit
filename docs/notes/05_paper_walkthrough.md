# Hands-on Walkthrough — Paper Sector Base-Year Energy, Cell by Cell

A step-by-step guide to reproduce the Paper energy numbers in
[04_site_energy_estimation.md](04_site_energy_estimation.md) **directly in the
Excel workbook**, including which sheets to open, how to filter, and which
commodity codes to look for. Figures use the public (dummy) file.

## The four sheets and how they join

| Sheet | What it gives you | Join key |
|---|---|---|
| `Technologies` | Base-year fleet: capacity + factors per technology | `code` |
| `technology_input_output` | The "fuel recipe": fuels consumed per unit output | `technology_code` ↔ `code`; `commodity` |
| `commodities` | What each commodity code means + its fuel category | `commodity` |
| `NAEI_df_clean_2023_revised` | Site emissions (for the site apportionment) | `IPM_sector` |

The chain: **Technologies** (how much runs) → **technology_input_output** (what
fuel it burns per unit) → **commodities** (which bucket that fuel is) →
sum → **NAEI** (scale to a site).

## Reading the technology codes
Paper has two code families, both with `sector = Paper`:
- `IPP…` = **Paper** (main), `IPR…` = **Printing** subsector.
- Pattern is sector–process–fuel. Process: `BOI` boiler, `CHP` combined heat & power,
  `DRY` drying, `LTH` low-temp heat, `SPC` space heat, `MOT` motor, `OTH` other,
  `PRO`/`FINPRO` process steps. Fuel suffix: `COA` coal, `NGA` natural gas,
  `ELC` electricity, `BIOS` biomass, `LPG` LPG, `GT` gas turbine, `STM` steam.
- Example: `IPPBOINGA01` = Paper **boiler** running on **natural gas**.

## Step 1 — `Technologies` sheet: the base-year fleet
1. Open `Technologies`. The header row is row 7 (`code`, `name`, `sector`, …).
2. **Filter `sector` = `Paper`.**
3. **Filter `existing_capacity_2020` > 0** (these are the technologies assumed to
   exist in the start year; capacity 0/blank = not in the base-year fleet).
4. The columns you need: `code`, `existing_capacity_2020`,
   `capacity_to_activity_factor`, `availability_factor`.
5. Add a helper column **activity**:
   ```
   activity = existing_capacity_2020 × capacity_to_activity_factor × availability_factor
   ```
   (This is the "implied output" in the Technical Guide.)

Note on `capacity_to_activity_factor`: it is `1` for most technologies (capacity is
already in PJ/yr), but `31.54` for CHP units (capacity is in **GW**; 1 GW·yr =
31.54 PJ). That's why the two CHP rows have large activity from small capacity.

Result (31 Paper technologies with capacity > 0):

| code | output_commodity | tech_category | cap2020 | cta | avail | activity |
|---|---|---|---:|---:|---:|---:|
| IPPFINPRO01 | IPP | Standard_FF | 4.714 | 1.00 | 0.930 | 4.384 |
| IPPPRODRY01 | IPPBPA | Electricity | 4.658 | 1.00 | 0.930 | 4.332 |
| IPPBOICOA01 | IPPLTH | Coal | 0.696 | 1.00 | 0.971 | 0.676 |
| IPPBOINGA01 | IPPLTH | Natural gas | 7.339 | 1.00 | 0.982 | 7.209 |
| IPPCHPBIOS01 | IPPLTH | Biomass | 0.450 | 31.54 | 0.900 | 12.778 |
| IPPCHPGT01 | IPPLTH | Standard_FF | 0.546 | 31.54 | 0.930 | 16.022 |
| IPPPROPRS01 | IPPPBD | Standard_FF | 4.809 | 1.00 | 0.930 | 4.473 |
| IPPPROOTH01 | IPPPBP | Standard_FF | 4.471 | 1.00 | 0.930 | 4.158 |
| IPR01 | IPR | Standard_FF | 35.565 | 1.00 | 1.000 | 35.565 |
| IPRLTHNGA01 | IPRLTH | Natural gas | 2.827 | 1.00 | 0.982 | 2.777 |
| IPRLTHELC01 | IPRLTH | Electricity | 3.832 | 1.00 | 0.986 | 3.779 |
| IPRDRYNGA01 | IPRDRY | Natural gas | 1.282 | 1.00 | 0.982 | 1.260 |
| IPRDRYELC01 | IPRDRY | Electricity | 6.330 | 1.00 | 0.986 | 6.242 |
| IPROTHELC01 | IPROTH | Electricity | 5.734 | 1.00 | 0.986 | 5.655 |
| … | | | | | | |

(Plus the remaining `IPR…LPG/BIOS/STM/SPC/MOT` rows — full set has 31 rows.)

## Step 2 — `technology_input_output` sheet: the fuel recipe
1. Open `technology_input_output` (header row 7: `technology_code`, `commodity`,
   `output`, `end_commodity`, …).
2. **Filter `technology_code`** to your Paper techs (e.g. starts with `IPP` or `IPR`).
3. **The sign of `output` is the key rule:**
   - `output` **< 0** → the commodity is an **input consumed** (a fuel). `|output|`
     is the PJ of that fuel per 1 unit of the technology's main output.
   - `output` **> 0** → the commodity is **produced** (the technology's output). Ignore
     these for fuel accounting.
4. So the fuel recipe = the **negative rows**. `commodity` there is the fuel code.

Worked single rows:
- `IPPBOINGA01` (gas boiler): one negative row, `IND_NGABOM = −1.0753` → uses
  **1.0753 PJ gas per PJ** of low-temp heat.
- `IPPCHPGT01` (gas CHP): `IND_NGABOMLFO = −2.4286` → 2.4286 PJ gas per unit.
- `IPRDRYELC01` (electric dryer): `INDDISTELC = −1.0101` → 1.01 PJ electricity per unit.

## Step 3 — `commodities` sheet: classify each fuel
Look up each fuel `commodity` code (header row 7: `commodity`, `description`,
`commodity_category`, …). The `commodity_category` tells you the bucket.

Fuel codes that appear in Paper:

| commodity | description | commodity_category | Bucket |
|---|---|---|---|
| `IND_NGABOM` | Natural gas and biomethane | Gas | **Gas** |
| `IND_NGABOMLFO` | Natural gas, biomethane, light fuel oil | Gas | **Gas** |
| `INDDISTELC` | Electricity (after distribution grid) | Electricity | **Electricity** |
| `INDCOA` | Coal | Coal | **Non-metered** |
| `INDLFO` | Light fuel oil | Oil | **Non-metered** |
| `INDLPG` | Liquified petroleum gas | Oil | **Non-metered** |
| `IND_SOLIDBIO` / `IND_SOLIDBIOMSW` | Biomass / organic waste | Biomass and organic waste | **Non-metered** |

Bucket rule: `Gas`→Gas, `Electricity`→Electricity,
`Coal`/`Oil`/`Biomass and organic waste`(/`Hydrogen`)→Non-metered.

**Exclude** these categories (intermediate carriers / non-energy — see Step 5):
`Heat`, `Steam`, `Miscellaneous`, `Inorganic waste`, `NonEnergyUse`.

## Step 4 — multiply and sum
For every negative (fuel) row:
```
fuel_use_PJ = |output| × activity(of that technology)
```
Then group by bucket and sum. The fuel rows that count:

| technology | fuel commodity | bucket | input/unit | × activity | = PJ |
|---|---|---|---:|---:|---:|
| IPPBOINGA01 | IND_NGABOM | Gas | 1.0753 | 7.209 | 7.75 |
| IPPCHPGT01 | IND_NGABOMLFO | Gas | 2.4286 | 16.022 | 38.91 |
| IPRCHPGT01 | IND_NGABOMLFO | Gas | 2.4286 | 0.796 | 1.93 |
| IPRLTHNGA01 | IND_NGABOM | Gas | 1.0870 | 2.777 | 3.02 |
| IPRDRYNGA01 | IND_NGABOM | Gas | 1.0870 | 1.260 | 1.37 |
| IPRSPCNGA01 | IND_NGABOM | Gas | 1.0753 | 0.762 | 0.82 |
| IPROTHNGA01 | IND_NGABOM | Gas | 1.0870 | 0.137 | 0.15 |
| **Gas subtotal** | | | | | **53.95** |
| IPPFINPRO01 | INDDISTELC | Electricity | 2.3297 | 4.384 | 10.21 |
| IPPPROOTH01 | INDDISTELC | Electricity | 2.5219 | 4.158 | 10.49 |
| IPROTHELC01 | INDDISTELC | Electricity | 1.0101 | 5.655 | 5.71 |
| IPRDRYELC01 | INDDISTELC | Electricity | 1.0101 | 6.242 | 6.31 |
| IPRLTHELC01 | INDDISTELC | Electricity | 1.0101 | 3.779 | 3.82 |
| IPRMOTELC01 | INDDISTELC | Electricity | 1.0225 | 3.224 | 3.30 |
| IPPPRODRY01 | INDDISTELC | Electricity | 0.4206 | 4.332 | 1.82 |
| IPPPROPRS01 | INDDISTELC | Electricity | 0.2915 | 4.473 | 1.30 |
| IPRSPCELC01 | INDDISTELC | Electricity | 1.0101 | 1.004 | 1.01 |
| **Electricity subtotal** | | | | | **43.97** |
| IPPCHPBIOS01 | IND_SOLIDBIO | Non-metered (biomass) | 1.3750 | 12.778 | 17.57 |
| IPRCHPBIOS01 | IND_SOLIDBIOMSW | Non-metered (biomass) | 1.3750 | 6.996 | 9.62 |
| IPPFINPRO01 | INDCOA | Non-metered (coal) | 0.2789 | 4.384 | 1.22 |
| IPPBOICOA01 | INDCOA | Non-metered (coal) | 1.1236 | 0.676 | 0.76 |
| IPPFINPRO01 | INDLFO | Non-metered (oil) | 0.2640 | 4.384 | 1.16 |
| (+ small IPR…BIOS / LPG rows) | | | | | ~1.03 |
| **Non-metered subtotal** | | | | | **32.36** |

**Sector total: 130.28 PJ/yr** → Gas 53.95 (41.4%), Electricity 43.97 (33.8%),
Non-metered 32.36 (24.8%).

The single biggest line is the **gas CHP** (`IPPCHPGT01`, 38.9 PJ) — small GW
capacity × 31.54 × a high 2.43 gas-per-unit recipe.

## Step 5 — why some negative rows are NOT counted
Some technologies consume commodities that are **produced by other technologies in
the same sector**, not purchased primary fuel. Counting them would double-count.
These are excluded because their `commodity_category` is `Heat`/`Steam`/`Miscellaneous`:

| commodity | category | what it is |
|---|---|---|
| IPPLTH | Heat | low-temp heat from the paper boilers/CHP (already counted as their gas/coal/biomass) |
| IPRSTM | Heat | steam from printing CHP |
| IPRLTH, IPRSPC | Heat | intermediate heat services |
| IPPBPA, IPPPBD, IPPPBP | Miscellaneous | intermediate paper products (before pressing/drying) |
| IPRDRY, IPRMOT, IPROTH | Miscellaneous | intermediate energy-service commodities |

Example: the demand technology `IPPPRODRY01` consumes `IPPLTH` (heat) — but that
heat was made by `IPPBOINGA01`/`IPPCHPGT01` burning gas, which we already counted.
So we skip the `IPPLTH` row and keep only the primary fuels.

## Step 6 — scale to a site (`NAEI_df_clean_2023_revised`)
1. Open `NAEI_df_clean_2023_revised` (header row 7).
2. **Filter `IPM_sector` = `Paper, printing & publishing industries`** (this is the
   NAEI label that maps to modelled sector `Paper` via `new_sector_mapping`).
3. **Sum `Emissions_tco2e`** over those rows = sector total = **1,437,995 tCO₂e**
   (49 sites).
4. For a chosen site, `share = site Emissions_tco2e / sector total`. Largest is
   **Kemsley Mill CHP** = 253,528 → `share = 0.1763`.
5. Site energy = `share × sector bucket`:
   - Gas = 0.1763 × 53.95 = **9.51 PJ**
   - Electricity = 0.1763 × 43.97 = **7.75 PJ**
   - Non-metered = 0.1763 × 32.36 = **5.71 PJ**
   - Total ≈ **22.97 PJ/yr**

## One-line recap
> Filter `Technologies` to Paper + capacity>0 → compute activity → in
> `technology_input_output`, the **negative** rows are the fuels → classify each
> fuel via `commodities.commodity_category` → `|output| × activity`, sum by bucket →
> scale to a site by its share of Paper NAEI emissions.
