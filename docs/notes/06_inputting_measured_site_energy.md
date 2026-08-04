# Inputting Measured Site Energy Data into COMIT

What to do if you **know a site's actual energy consumption** — e.g. metered
electricity, gas, and coal figures — and want the current version of COMIT to use
it. Builds on [04_site_energy_estimation.md](04_site_energy_estimation.md) (read
that first for the sheets and steps referenced here).

## The short answer

**There is no direct "site energy" input anywhere in the template.** COMIT never
reads site energy; it *derives* it:

```
site energy = sector fleet totals (Technologies × technology_input_output)
              × site emissions share (NAEI_df_clean_2023_revised, traded_share)
```

So measured data has to enter through one of those two levers — the sector fleet
or the emissions share. The only PlantID-level hook in the workbook
(`known_changes`) is for forcing *future* technology deployments and is marked
"currently in development"; it is not a base-year energy input.

## A key structural assumption: homogeneous sites within a sector

For the start-year estimate, **every site in a sector is a scaled-down copy of the
sector's technology fleet** — same fuel proportions, only the size differs (via
emissions share). In the public file, *every* Paper site is ~41% gas / 34%
electricity / 25% non-metered; every Cement site is ~93% coal.

This is because NAEI gives the model exactly one scalar per site (its CO₂
emissions) plus a sector label: enough to set a **scale**, not a **mix**. Two
consequences:

- Mix differences between sites come *only* from sector membership. Kemsley Mill
  (Paper) and a small paper mill have identical mixes; Kemsley Mill and Hope
  Cement Works differ enormously purely because they are in different sectors.
- Homogeneity applies to the **base year, not the future**. Once the optimisation
  runs, sites can diverge — technology switching depends on site-specific factors
  (cluster location, distance to H₂/CO₂ infrastructure, grid connection), so two
  sites starting with the same mix can end up on different decarbonisation
  pathways.

If your measured data shows a site's mix differs from its sector average, the
current model **structurally cannot represent that at site level** without the
own-sector workaround (Option 3 below).

## Three approaches, in increasing fidelity and effort

### Option 1 — Tune the site's emissions share (data-only; matches the total, not the mix)

The site's slice of the sector is `Emissions_tco2e / Σ sector point-source
emissions` (Steps 4–5 of note 04). Back-solve the site's `Emissions_tco2e` in
`NAEI_df_clean_2023_revised` so that:

```
share × sector total energy = your measured total energy
```

- **Pros:** pure workbook edit; one cell.
- **Cons:** one scalar — you can hit the site's *total* energy but its
  gas/electricity/coal split stays the sector average. You are also distorting
  the site's emissions to fix its energy, which propagates to everything else
  the emissions share drives.
- **Use when:** the site's fuel mix is fairly typical of its sector and you only
  trust the total.

### Option 2 — Fold your data into the sector fleet calibration (recommended default)

Treat your measured numbers the way ECUK was treated: as **calibration targets for
`Technologies!existing_capacity_2020`**. For each fuel, capacity is simple
arithmetic — inverting the Step 3 formula from note 04:

```
existing_capacity_2020 = measured fuel use
                         / (fuel-per-unit × availability_factor × capacity_to_activity_factor)
```

e.g. for the Paper gas boiler `IPPBOINGA01` (public file):
`capacity = measured_gas / (1.075 × 0.982 × 1)`.

Set the sector's gas / electric / coal technology capacities to *"your site's
measured fuels + best estimate for the remaining sites"*.

- **Pros:** pure workbook edit; uses your data the same way the model already
  uses ECUK; improves the whole sector's totals and mix.
- **Cons:** the site still inherits the sector-average mix — you have pulled the
  average toward reality, not pinned the site itself.
- **Use when:** you have good data and especially when the site dominates its
  sector (a Hope-Cement-style site at ~20% share moves the average a lot).

### Option 3 — Give the site its own sector (exact three-fuel match; needs code changes)

The only way to pin gas, electricity **and** coal independently to one site is to
isolate it in a bespoke one-site sector:

1. Duplicate the parent sector's technologies in `Technologies` and
   `technology_input_output` under a new sector name.
2. Size each fuel's technology capacity to the measured value (Option 2 formula).
3. Add matching rows in `new_sector_mapping`, `NAEI_mapping`, `Demand_drivers`,
   `Emissions`, and `traded_share` — with `non_point_share = 0` so the site
   carries the whole sector.

**The catch:** sector names are not purely data-driven. They are hard-coded in
the Shiny UI selector (`R/app_ui.R`) and Iron & steel is special-cased in
`R/fct_attribution.R`, so in the current version this is a **data-plus-code
change**, not just an Excel edit.

- **Use when:** the site's fuel mix is genuinely unlike its sector (e.g. a
  coal-fired outlier in a gas-dominated sector) and that difference matters to
  your results.

## If you need per-site fuel mixes across many sites

Options 1–3 don't scale if you want *several* sites in a sector to each have
their own tailored energy-vector mix (one sector per site quickly becomes
unmanageable). Two further options, one data-led and one a proper code feature.

### Why the model can't do this today — one variable

All site heterogeneity within a sector is a **single scalar per site**:

```r
# R/fct_sites.R (get_site_demand)
scaling_factor_within_sector = total_MtCO2 / total_sector_emissions
```

That one number multiplies *everything* for the site — its demand
(`fct_sites.R`, `demand = demand * scaling_factor_within_sector`) and every
technology's capacity (`existing_capacity_2020 * scaling_factor_within_sector`
in `fct_constraints_capacity_transfer.R`, `fct_constraints_existing_capacity.R`,
`fct_comit_counterfactual_solver.R`). Because the *same* scalar scales the gas
boiler and the electric equipment, every site inherits the sector's proportions
by construction.

### Option 4 — Archetype sub-sectors (data-led, bounded code changes)

Instead of one sector per site, split a sector into a few **mix archetypes**
(e.g. `Paper_gasheavy`, `Paper_coalheavy`, `Paper_electric`) and assign each site
to one:

1. Define each archetype as a sector in `Technologies` /
   `technology_input_output` (duplicate the parent fleet, calibrate capacities to
   the archetype's mix using the Option 2 formula).
2. Assign sites individually by editing their `IPM_sector` value in
   `NAEI_df_clean_2023_revised` — sector membership is per site row, so this part
   is a pure data edit.
3. Add the archetype sectors to `new_sector_mapping`, `NAEI_mapping`,
   `Demand_drivers`, `Emissions`, `traded_share`.
4. Code touch-ups as in Option 3 (UI sector lists in `R/app_ui.R`; check
   special-casing in `R/fct_attribution.R`).

Sites within an archetype are still homogeneous, but you choose how fine the
archetypes are. Good when sites fall into a handful of recognisable fuel
patterns.

### Option 5 — Technology-specific site scaling (code feature; full flexibility)

The surgical fix is to make the scaling factor **technology-specific**:
`scaling_factor(site, technology)` instead of `scaling_factor(site)`.

Sketch:

1. **New input sheet** (e.g. `site_capacity_overrides`): `PlantID` ×
   `technology_code` → measured-implied capacity (from the Option 2 back-solve
   formula), for the sites you have data for.
2. **Compute a per-site, per-technology share table** in `fct_sites.R`:

   ```
   share(site, tech) = measured_capacity(site, tech) / sector_capacity(tech)   # sites with data
   share(site, tech) = emissions_share(site) × (1 − Σ measured shares(tech))
                        / Σ emissions_shares(unmeasured sites)                 # the rest
   ```

   The renormalisation keeps each technology's shares summing to 1 across the
   sector, so sector totals — and the ECUK/GHGI anchoring — are preserved:
   measured sites take exactly their measured capacity, and the remainder is
   spread over the other sites by emissions share as before.
3. **Replace the joins/multiplications** at the ~5 places that currently use
   `scaling_factor_within_sector` against capacities (listed above) with the
   technology-aware factor. Demand apportionment can stay emissions-share-based,
   or be derived from measured energy for overridden sites for full consistency.

This is a genuine feature development (new sheet, ingestion, several call sites,
tests), but it is well-localised — the homogeneity assumption lives in that one
column, not spread throughout the model.

## Process-level heterogeneity (e.g. one site dries more than another)

The distribution of energy between **processes** is also fixed per sector — but it
lives in the `technology_input_output` *coefficients*, not the capacities. Two
shapes:

- **Energy-based sectors** (e.g. Chemicals): a "demand technology" bundles energy
  services in fixed proportions — `ICH01` turns 1 PJ of final Chemicals demand
  into motors 0.60 / LTH 0.13 / refrigeration 0.13 / drying 0.06 / other 0.05 /
  space heat 0.03 / HTH 0.004.
- **Chain sectors** (e.g. Paper): a sequence of process steps, each with a fixed
  intensity per Mt of product — the drying step `IPPPRODRY01` consumes 4.03 PJ of
  low-temp heat + 0.42 PJ electricity per Mt dried, then `IPPFINPRO01` finishes.

Site demand = sector demand × one scalar, so every site also does its processes
in identical proportions. Which options can change that:

- **Option 4 (archetypes): yes, fully.** Each archetype carries its own copies of
  the process/demand technologies, so `Paper_tissue` can have a higher drying
  coefficient than `Paper_containerboard`. Archetypes cover *both* process mix
  and fuel mix.
- **Option 5 (per-site capacity scaling): no, not by itself.** The LP requires
  services/intermediates in the fixed coefficient ratios per unit of output —
  extra drying *capacity* at a site would simply sit unused. Capacities decide
  *which fuel* serves a process; coefficients decide *how much of each process*
  is needed, and Option 5 only touches the former.
- **Option 5 extension** (energy-based sectors only): give sites demand directly
  in *service* commodities (PJ of drying/motors/LTH per site) instead of the
  final commodity, bypassing the fixed bundle — a further change in
  `fct_sites.R` where site demand joins `Demand_drivers`. For chain sectors like
  Paper this is less meaningful: drying intensity is physics-per-product, so a
  "drying-heavy paper site" is really making a different product (tissue vs
  board) — i.e. an archetype.

**Rule of thumb:** process-mix differences → Option 4 (coefficient territory);
fuel-mix differences within the same processes → Option 5 (capacity territory);
both → archetypes for structure, per-site scaling within them.

## Recommended path

1. Start with **Option 2** — lowest-risk way to get real data into the model.
2. Layer **Option 1** on top only if the site's apportioned total still lands off.
3. Reserve **Option 3** for when the site's mix truly diverges from its sector
   and the divergence matters.

Whichever you pick, keep the anchoring sheets consistent: if you edit site
emissions or capacities, check `Emissions` (GHGI whole-sector totals) and
`traded_share` still make sense, since they set the absolute totals that NAEI
shares divide up (Step 5 of note 04).
