# Splitting emissions by source — process chemistry vs energy combustion

**Question this note answers:** how much of a given process's greenhouse gas emissions comes from *burning fuel*, and how much is *inherent to the chemistry* — the calcination CO₂ in a cement kiln that would still be emitted if the kiln ran on hydrogen? How do you categorise every technology in COMIT this way, and which parameters do you change when better data arrives?

Companion data: [`data/emissions_source_classification.csv`](data/emissions_source_classification.csv) (397 technologies) — see [`data/README.md`](data/README.md) for the column dictionary, and [`examples/build_emissions_classification.R`](examples/build_emissions_classification.R) to regenerate it.

Builds on [13_emissions_calculation.md](13_emissions_calculation.md) (how `get_emissions()` works) and [12_output_data_schema.md](12_output_data_schema.md) (the output tables).

---

## 1. The short answer

**COMIT already does this split — you do not need to reconstruct it.** Every emissions row the model exports is tagged `Emission_type` ∈ `Energy` | `Process`.

The two behave completely differently, and that difference is the whole point:

| | Energy emissions | Process emissions |
|---|---|---|
| Scale with | **fuel consumed** | **output produced** |
| Formula factor | `fuel_CO2e` (kt per PJ of fuel) | none — the quantity *is* the emission |
| Abated by fuel switching | **yes** | **no** |
| Abated by CCS | yes (CO₂ only) | yes (CO₂ only) |
| Changes with the fuel mix | yes | never |

Because process emissions carry no fuel factor, no amount of electrification or hydrogen switching touches them. They are the residual that only carbon capture — or a different chemistry — can reach. That is exactly the cement intuition, and the model encodes it structurally rather than as an assumption you have to remember.

## 2. How the model represents process emissions

Process emissions are modelled as **pseudo-commodities**: things a technology "produces" per unit of output, listed in `technology_input_output` alongside its real fuel and material flows.

Only **3 of the 143 commodities** in the reference workbook are flagged `process_emission = TRUE`:

| Commodity | Unit | `proportion_emissions_CO2` | Carries |
|---|---|---|---|
| `INDCO2P` | kt | 1 | Process CO₂ |
| `INDCH4P` | kt | 0 | Process CH₄ |
| `INDN2OP` | kt | 0 | Process N₂O |

The split falls out of two lines in `calculate_CO2_direct_emissions()` ([R/fct_emissions.R:255-290](../../R/fct_emissions.R#L255-L290)):

```r
CO2_process_released_direct = output * proportion_emissions_CO2 * direct_commodity
                              * process_emission * emissions_released

CO2_fuel_released_direct    = -1 * output * proportion_emissions_CO2 * direct_commodity
                              * commodity_produces_emissions * (!process_emission)
                              * fuel_CO2e * emissions_released
```

Three things to read off this:

- The process term has **no `fuel_CO2e`**. The commodity quantity is already the emission in kt, which is why its unit is `kt` and not `PJ`.
- The fuel term is negated because fuel inputs are stored as negative `output` (consumed); process commodities are positive (produced).
- `process_emission` and `!process_emission` make the two terms mutually exclusive — every commodity contributes to exactly one.

**No GWP conversion happens anywhere.** `INDCH4P` and `INDN2OP` must already be expressed in kt CO₂e in the input data. If you supply tonnes of CH₄, the model will treat them as tonnes of CO₂e.

## 3. Two ways to categorise — prefer the first

### A-priori, from the input workbook (recommended)

A technology has process emissions **if and only if** its `technology_input_output` rows include one of the three process commodities. This needs no solve, is scenario-independent, and gives an intensity per unit of output.

That is what the companion CSV holds. Across all 397 technologies:

| Class | Count | Condition | Reading |
|---|---|---|---|
| `A_pure_process` | 8 | process > 0, direct energy = 0 | Emits only through chemistry. Already fuel-switched or unfuelled — **fuel switching has nothing left to give**. |
| `B_process_dominant` | 23 | process ≥ 50% of direct | Kilns, reformers, refineries. |
| `C_mixed_energy_dominant` | 15 | process < 50% of direct | Both matter. |
| `D_pure_energy` | 170 | process = 0 | Fully abatable by fuel switching. |
| `E_zero_direct` | 181 | no direct emissions at all | Electric/hydrogen technologies and non-emitting demand technologies. Check `energy_indirect` before calling these clean. |

Process emissions are confined to **7 sectors** — Cement, Chemicals, Glass, Hydrogen, Iron & steel, Lime, Refineries. The other ten are pure energy, so for them fuel switching is a complete decarbonisation lever.

### Post-hoc, from a model run

Filter the `Emissions` sheet to `Emissions_category == "Direct (total CO2e)"` and group by `Emission_type`. This gives realised kt in that scenario — what you want for reporting rather than for screening.

```r
emissions %>%
  filter(Emissions_category == "Direct (total CO2e)") %>%
  pivot_longer(matches("^2[0-9]{3}$"), names_to = "year", values_to = "kt") %>%
  group_by(Sector, Emission_type, year) %>%
  summarise(kt = sum(kt), .groups = "drop") %>%
  pivot_wider(names_from = Emission_type, values_from = kt, values_fill = 0) %>%
  mutate(process_share = 100 * Process / (Energy + Process))
```

Sector split for 2021 in the reference run:

| Sector | Energy (kt) | Process (kt) | Process share |
|---|---|---|---|
| Refineries | 16 | 59 | **78%** |
| Lime | 67 | 205 | **75%** |
| Cement | 389 | 719 | **65%** |
| Glass | 209 | 237 | **53%** |
| Chemicals | 691 | 349 | 34% |
| Iron & steel | 136 | 16 | 10% |
| Ceramics, Construction, Electrical eng., Food & drink, Mechanical eng., Non-ferrous metals, Paper, Textiles, Vehicles | all | 0 | **0%** |

**The two methods agree — checked, not assumed.** Comparing a-priori `process_share_pct` against the realised 2021 split for every technology emitting more than 1 kt: **36 of 36 match exactly** (|difference| < 0.15 pp), including all 8 process-bearing ones. Cement's `ICMKLND01` is 64.9% both ways, lime `ILMKLND01` 75.4%, glass `IGLKLN` 54.9%.

They must agree, since both terms are linear in activity and the ratio cancels it out. That makes this a cheap regression check on any amended dataset: regenerate the CSV, re-run a scenario, and the two shares should still coincide. If they diverge, either an intensity was edited without regenerating or a hardcoded list in §6 has gone stale.

## 4. The detector: emissions per unit of energy

If you want to *find* the "emits a lot, burns little" processes without knowing the answer in advance, divide direct emissions by energy consumed.

Every gas-fired technology in the model lands on exactly **184 kt CO₂e/TWh** — the natural gas factor (`IND_NGABOM` = 51.2 kt/PJ × 3.6 PJ/TWh). That constant is the baseline; anything materially above it is carrying process emissions:

| Technology | kt/TWh | vs gas line | Process share |
|---|---|---|---|
| `ICMKLND01` cement dry kiln | **864** | 4.7× | 65% |
| `ILMKLND01` lime kiln | **854** | 4.6× | 75% |
| `IGLKLN` glass furnace | **378** | 2.1× | 55% |
| `IISCASHRM01` caster/hot rolling | 175 | 0.95× | 8.6% |
| any `*NGA01` gas boiler | 184 | 1.0× | 0% |

Cement is the largest single emitter in the reference run — 1,107 kt in 2021, two-thirds of it calcination.

## 5. Reframing "processes that don't consume much energy"

Worth stating precisely, because the natural phrasing is slightly off: **no technology in COMIT emits while consuming zero energy.** The eight `A_pure_process` technologies have zero *direct* energy emissions not because they are unfuelled, but because their fuel is electricity or mains hydrogen, which COMIT treats as **indirect** — the emissions happen at the power station, not on site.

`ICHHVCSCHYD01` ("Hydrogen fuel switching in High Value Chemicals") is the clearest case: fully fuel-switched, zero direct combustion emissions, and **396 kt of process CO₂ per Mt of output remaining**. That is the decarbonisation endpoint for a steam cracker, and the reason CCS variants exist alongside the hydrogen variant.

So the sharper framing is **"emissions not proportional to fuel burnt"** rather than "low energy use". `emission_class` in the CSV encodes exactly that.

## 6. What is hardcoded and what is data-driven

This is the part that determines how far you can go by amending the workbook alone.

### Data-driven — change the workbook, no code change needed

| Parameter | Sheet · column | Controls |
|---|---|---|
| `process_emission` | `commodities` · `process_emission` | **Which commodities count as process emissions.** The three codes are *not* referenced anywhere in `R/` — adding a fourth works by data alone. |
| `proportion_emissions_CO2` | `commodities` · `proportion_emissions_CO2` | CO₂ vs non-CO₂ split of a commodity. |
| `commodity_category` | `commodities` · `commodity_category` | Fuel grouping; membership of the biomass category. |
| `commodity_produces_emissions` | `technology_input_output` | Whether a consumed commodity emits at all. |
| `output` | `technology_input_output` | **The per-unit intensities.** This is where you amend a kiln's calcination factor. |
| `fuel_CO2e` | `Fuel_emissions` · per commodity, per year | Combustion factors. Year-varying. |
| `emissions_released` | `Technologies` · `emissions_released` | Capture rate — the fraction *not* captured. |

### Hardcoded in R — requires a code change

| What | Location | Consequence |
|---|---|---|
| **Indirect commodity list** — `INDDISTELC`, `INDMAINSHYG`, `INDMAINSHYGG`, `INDMAINSHYGB` | [fct_emissions.R:180-183](../../R/fct_emissions.R#L180-L183) | Which fuels count as off-site. A new electricity or hydrogen carrier added to the workbook would be treated as **direct** until this list is edited. |
| **Biomass category name** — the literal string `"Biomass and organic waste"` | [fct_emissions.R:234](../../R/fct_emissions.R#L234) | Renaming that category in `commodities` silently disables biomass zero-rating, and BECCS stops being negative. The *membership* is data-driven; the *label* is not. |
| **Non-CO₂ is never captured** — `nonCO2_process_captured_direct = 0`, `nonCO2_fuel_captured_direct = 0` | [fct_emissions.R:327-328](../../R/fct_emissions.R#L327-L328) | CCS abates CO₂ only. `emissions_released` has no effect on CH₄ or N₂O — the non-CO₂ released term does not even carry the factor. A CCS technology claiming methane capture cannot be represented by data alone. |
| **Allowed switch values** — `c("process","fuel")`, `c("direct","indirect")`, `c("CO2","nonCO2")` | [fct_emissions.R:49-53](../../R/fct_emissions.R#L49-L53) | The taxonomy itself. A third emission source (say, fugitive) needs code. |

### One inconsistency worth checking

`INDMAINSHYGR` is treated as a hydrogen fuel in [fct_hydrogen_modelling_adjustments.R:6](../../R/fct_hydrogen_modelling_adjustments.R#L6) but is **absent from the indirect list** in `fct_emissions.R:180-183`, which covers only the `G` and `B` variants. It is currently inert — no technology consumes it in the reference workbook — so this has no effect today. But all three colour variants carry a `fuel_CO2e` of `999`, an obvious sentinel, so if `INDMAINSHYGR` ever became an active fuel it would be booked as direct emissions at a placeholder factor. Worth confirming with the model owners whether the omission is deliberate.

## 7. Caveats

1. **The reference numbers are placeholders.** The `commodities` and `Fuel_emissions` sheets of the public workbook are labelled *"dummy figures"* / *"Mostly dummy numbers"*. The classification, the method and the code references are real; the intensities are not. Regenerate against a production workbook before quoting a figure.
2. **`*_per_unit` denominators differ.** `output_unit` is `Mt` for material processes and `PJ` for energy services — intensities are not comparable across differing units.
3. **The CSV holds gross intensities.** `emissions_released` is a separate column, deliberately not applied — and when you do apply it, remember it touches CO₂ only (§6).
4. **Biomass zero-rating is not in `direct_total`.** `energy_direct_kt_per_unit` is gross combustion; `energy_direct_biomass_zerorated_kt_per_unit` is what the model books by default. `emission_class` is built on the gross figure, so 50 biomass-fired technologies classed `D_pure_energy` here book zero direct emissions in an actual run.
5. **Do not use the `Energy` output sheet for this.** Its `ktCO2e` columns are gross combustion emissions carrying no process emissions at all — see [12_output_data_schema.md](12_output_data_schema.md) gotcha 14.
