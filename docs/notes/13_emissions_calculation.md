# How COMIT Calculates Emissions

A plain-language walkthrough of where emissions numbers come from in the
model: what goes in, how the model computes emissions while it optimises, and
what comes out. Follows the style of note
[09_objective_function.md](09_objective_function.md).

Workbook references are to `data_template_archive/comit_input_1_4_0_public_updated.xlsx`
(sheet names as written; in every data sheet the **column headers are on row 7
and data starts on row 8** — the model reads them with `skip = 6` in
[R/fct_read_data.R:133](../../R/fct_read_data.R#L133)). Code references are
clickable `file:line` links into the `R/` directory.

## The short answer

**The model never stores "emissions per site" as a single number it works
with.** Instead:

1. **Going in**, each site has one measured emissions number from NAEI, but it
   is only used as a *weight* to decide how big the site is relative to its
   sector.
2. **During optimisation**, emissions are calculated **per technology**: each
   technology (a gas boiler, an electric furnace, a CCS kiln…) has an
   emissions factor in "kilotonnes of CO₂e per unit of capacity used, per
   year". A site's emissions are then simply *implied*: add up, for every
   technology the optimiser runs at that site, (how much the technology is
   used) × (its emissions factor).
3. **Coming out**, the results tables *do* report emissions per site (or per
   cluster) — by doing exactly that multiplication on the solved answer.

The rest of this note walks through each stage.

---

## Part 1 — Going in: the base-year emissions of each site

Each real site appears as one row of the workbook sheet
**`NAEI_df_clean_2023_revised`**. The column **`Emissions_tco2e`** holds the
site's reported emissions (tonnes CO₂e) from the NAEI point-source inventory.

This number is used for exactly one thing: the site's *share of its sector*.
In [R/fct_sites.R:113](../../R/fct_sites.R#L113):

```
scaling_factor_within_sector = site emissions / total emissions of all sites in the sector
```

A site with 10% of its sector's emissions gets 10% of the sector's demand and
10% of every technology's starting capacity (notes 04 and 06 cover this in
detail). The *absolute* sector totals are anchored separately to the national
GHGI inventory via the **`Emissions`** sheet (columns `IPM_sector`,
`Total_emissions`), split into ETS/non-ETS portions by the **`traded_share`**
sheet and into point/non-point portions by `non_point_share`.

Two things follow that are easy to miss:

- **Emissions that aren't at a named site still exist in the model.** The
  non-point portion of each sector is bundled into artificial "sites", one
  per cluster × sector, whose names end in **`_npsg`** ("non-point source
  group") — created in
  [R/fct_process_sites.R:1063](../../R/fct_process_sites.R#L1063) and
  [:1197](../../R/fct_process_sites.R#L1197). That name suffix matters later
  (Part 3).
- **The site's NAEI number never appears in the optimisation again.** From
  here on, all emissions are recomputed bottom-up from fuels and processes.

## Part 2 — During optimisation: emissions per technology

The engine is one function, `get_emissions()` in
[R/fct_emissions.R:35](../../R/fct_emissions.R#L35). Ask it "how much does
technology X emit in year Y?" and it answers in **kt CO₂e per unit of used
capacity**. Here is the recipe it follows, in plain steps:

**Step 1 — look up what the technology consumes and produces.**
The sheet **`technology_input_output`** lists, for each technology code, every
commodity it uses or makes per unit of output (fuels in, products out,
process-emission commodities out). This is the same sheet that drives the
energy balance — emissions and energy come from one description of the
technology.

**Step 2 — for each fuel, multiply by that fuel's emission factor.**
The sheet **`Fuel_emissions`** has one row per year and one column per fuel
commodity (e.g. `INDMAINSGAS` for mains gas ≈ 60, `INDCOA` for coal ≈ 89.6 in
the public file — units are kt CO₂e per PJ of fuel). Factors can change over
time; that is how, say, grid biomethane blending would be represented. The
code joins these factors in at
[R/fct_emissions.R:207](../../R/fct_emissions.R#L207).

So: *fuel emissions = (PJ of fuel used per unit of capacity) × (kt CO₂e per
PJ for that fuel in that year)*.

**Step 3 — add process emissions.**
Some emissions don't come from burning anything (e.g. the CO₂ released
chemically when limestone is calcined in a cement kiln). These are
represented as commodities *produced* by the technology, flagged in the
**`commodities`** sheet: column **`process_emission`** = TRUE marks a
process-emission commodity, and column **`proportion_emissions_CO2`** says
what fraction of it is CO₂ vs other gases (methane, N₂O…).

**Step 4 — apply the capture rate.**
The **`Technologies`** sheet has a column **`emissions_released`**: the
fraction of the technology's emissions that escape to the atmosphere. A CCS
technology might have 0.05 here (95% captured). Everything above is split
into a "released" part and a "captured" part using this one number.

**Step 5 — the biomass rule.**
Fuels whose `commodity_category` (in the `commodities` sheet) is *"Biomass
and organic waste"* are treated as **zero-emission by default**
([R/fct_emissions.R:229](../../R/fct_emissions.R#L229)). Combined with Step 4,
this is what makes BECCS *negative*: burning biomass counts as zero, but
capturing its CO₂ still counts as removal.

**Step 6 — direct vs indirect.**
Four commodities are hard-coded as "indirect" (emissions happen somewhere
else, at a power station or hydrogen plant):
grid electricity `INDDISTELC` and the mains-hydrogen commodities
`INDMAINSHYG` / `INDMAINSHYGG` / `INDMAINSHYGB`
([R/fct_emissions.R:180-183](../../R/fct_emissions.R#L180-L183)). Everything
else is "direct" (emitted at the site).

### The five switches

`get_emissions()` can slice the result any way you need, along five
dimensions — every caller in the codebase is just choosing a combination:

| Switch | Options | Where the data lives |
|---|---|---|
| `gas` | CO₂ / non-CO₂ | `commodities!proportion_emissions_CO2` |
| `source` | fuel / process | `commodities!process_emission` |
| `capture` | released / captured | `Technologies!emissions_released` |
| `location` | direct / indirect | hard-coded commodity list |
| `zero_emissions_from_biomass` | TRUE / FALSE | `commodities!commodity_category` |

A useful derived quantity is `net_emissions()`
([R/fct_emissions.R:514](../../R/fct_emissions.R#L514)) = emissions before
capture (with biomass zero-rated) **minus** captured emissions (with biomass
counted). For an ordinary boiler that is just its emissions; for BECCS it
goes negative.

**Key consequence:** the factor depends only on *(technology, year)* — never
on the site. Two sites running the same gas boiler have identical emission
intensity. Site-to-site emission differences arise **only** from running
different technologies at different levels.

## Part 3 — Where emissions actually influence the optimisation

Only two places:

### 3a. The carbon cost in the objective function

[R/fct_pv_carbon_cost.R](../../R/fct_pv_carbon_cost.R) charges every unit of
used capacity a carbon cost:

```
carbon cost = traded CO₂e × traded price  +  untraded CO₂e × untraded price
```

with prices per year from the **`Carbon_price`** sheet (columns
`CarbonCost_traded`, `CarbonCost_untraded`) and emissions from
`net_emissions()`. Whether a site pays the *traded* (ETS) price is decided by
a naming trick at
[R/fct_pv_carbon_cost.R:63](../../R/fct_pv_carbon_cost.R#L63): a site is
"traded" **if its name does not end in `_npsg`** — i.e. real NAEI point
sources are in the ETS, the artificial non-point bundles are not. Non-CO₂
gases always pay the untraded price. (Note this is a *name-pattern*
convention, not a data column — fragile if site naming ever changes.)

### 3b. An annual cap on total industry emissions

[R/fct_constraints_emissions.R](../../R/fct_constraints_emissions.R) builds
one constraint per year:

```
Σ over every site and technology ( used capacity × direct emissions factor ) ≤ max_emissions
```

The cap comes from the **`emissions_limit`** sheet (columns `year`,
`max_emissions`). It is **one national number per year** — there are no
per-site or per-sector emission caps. In the public workbook the value is
1,000,000 kt for every year, i.e. the cap is effectively switched off and
decarbonisation is driven by the carbon price instead. (One special case:
the Hydrogen sector counts direct *and* indirect emissions against the cap;
all other sectors count direct only —
[R/fct_constraints_emissions.R:51-60](../../R/fct_constraints_emissions.R#L51-L60).)

## Part 4 — Coming out: the emissions results tables

After solving, [R/fct_create_emissions_tables.R](../../R/fct_create_emissions_tables.R)
turns the solution into emissions tables. This is where **per-site emissions
finally exist as numbers**: solved used-capacity × emissions factor, summed
per site (or per cluster — a `site_cluster` switch picks the granularity),
per sector, technology, and year. Rows are labelled by `Emissions_category`:

| Category | What it is |
|---|---|
| Direct_and_Indirect | everything released, at-site + upstream |
| Direct (split by ghg type) | at-site emissions, split into CO₂ / CH₄ / N₂O using the **`ghg_splits`** sheet — note these splits are **per sector**, not per site or technology |
| Captured | what CCS technologies captured |
| Indirect | upstream emissions of grid electricity and hydrogen — hydrogen's intensity is recomputed from the *solved* blue/green/grey mix ([fct_create_emissions_tables.R:268](../../R/fct_create_emissions_tables.R#L268)) |
| Negative | rows whose net emissions are below zero (BECCS) |

Each row also carries the site's Traded/NonTraded status (same `_npsg` rule).

Separately, the **attribution module**
([R/fct_attribution.R](../../R/fct_attribution.R), Shiny "Attribution" tab)
answers a different question — "which lever (electrification, hydrogen, CCS,
efficiency…) gets credit for the reductions?" — and it works at **sector**
level, rescaling the model's savings so they line up with the GHGI-anchored
sector pathways from the `Emissions` sheet.

## Part 5 — Implications and limitations to keep in mind

1. **Site emissions are emergent, not tracked.** There is no site emissions
   variable to constrain or report directly; anything per-site is
   reconstructed after solving. A per-site emissions cap or target would be a
   new constraint, though a cheap one (same shape as 3b, grouped by site).
2. **Input emissions and modelled emissions are two different worlds.** The
   NAEI number sizes the site; the bottom-up factors generate all modelled
   emissions. Nothing forces the model's base-year emissions at a site to
   equal its NAEI figure. This is exactly PRD open question Q2: if measured
   site energy (feature F1) changes a site's baseline, its NAEI-implied and
   energy-implied emissions will disagree, and the traded carbon cost
   currently follows the NAEI view of the site.
3. **Same technology ⇒ same emission intensity everywhere.** Site-specific
   emission factors (an older, dirtier kiln at one site) cannot be
   represented — that would need site-indexed factors or per-site technology
   variants (the archetype mechanism, PRD F6).
4. **Traded status is a naming convention** (`_npsg` suffix), not a data
   field. Worth formalising as a column before any feature that edits site
   identity.
5. **Non-CO₂ gases are coarse.** They are split out only via sector-level
   `ghg_splits` percentages at reporting time — one reason waste and
   wastewater (CH₄/N₂O-dominated) don't fit the current engine (note 11 §5).
6. **The emissions cap is national and, in the public file, inactive** — the
   carbon price does the work. Sector- or site-level carbon budgets would be
   new constraints.
