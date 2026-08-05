# Why Sites in the Same Sector Can Follow Different Pathways

## The short answer

At the start of the model, sites in one sector have the same modelled
technology and process set, in the same proportions. Both a site's initial
capacity and its demand are scaled by that site's share of the sector's
emissions. A larger emissions share therefore means a larger version of the
same starting configuration; it does not mean a different starting fuel or
process mix.

This is different from the optimisation that follows.  The model creates
separate site × technology × year capacity decisions, so sites can take
different future pathways when the available choices, constraints and costs
differ.  For the underlying site-energy calculation and the limits of measured
site-energy inputs, see [06_inputting_measured_site_energy.md](06_inputting_measured_site_energy.md).

## Same start, potentially different future

The table follows two illustrative sites in the same sector. It is deliberately
simplified, and every pathway and every value in it is **illustrative**: it
shows how divergence can arise, not what will happen at any real site.

| Model period | Illustrative Site A (60% emissions share) | Illustrative Site B (40% emissions share) |
|---|---|---|
| Base year (illustrative) | **Illustrative starting demand:** 60 units; **illustrative starting capacity:** 60% of every sector technology's capacity, with the same process set. | **Illustrative starting demand:** 40 units; **illustrative starting capacity:** 40% of every sector technology's capacity, with the same process set. |
| First later model period (illustrative) | **Illustrative access:** a hydrogen or CCS technology is eligible here and its connection option is lower cost. **Illustrative pathway:** the optimiser can select that eligible option if it is least cost under all constraints. | **Illustrative access:** the same technology is eligible, but its connection option is higher cost. **Illustrative pathway:** the optimiser can instead select another option if that is least cost under all constraints. |
| Second later model period (illustrative) | **Illustrative pathway:** capacity choices can continue along the Site A route, subject to infrastructure and cluster limits. | **Illustrative pathway:** capacity choices can continue along a different Site B route, subject to the same kinds of limits. |

Eligibility and relative access cost are different ideas.  If a technology is
**ineligible** at a site in a period, the corresponding capacity decision
variable is not created.  If it is **eligible** at two sites, both can have a
decision variable even though one site's connection or transport option is less
costly.  That lower-cost access can affect the least-cost choice; it does not
guarantee it.

## Site-level mechanisms in the model

The following mechanisms can make later choices differ.  They are not alternate
ways to enter an arbitrary site-specific starting mix.

| Mechanism | What it can vary | What it cannot vary accurately |
|---|---|---|
| Geographic H2/CCS eligibility | Whether hydrogen- or CCS-category technology capacity variables exist for a site and period. The model filters them using the site's H2/CCS cluster flags and first-available years. | It does not give a site a different base-year technology or process mix. |
| H2/CO2 infrastructure capacity and connection cost | The site-level H2 and CO2 connection/transport variables available, and the infrastructure capacity required when the associated technology use occurs. Site distance and the selected capacity band feed the pre-model transport option and cost data, so access can be relatively more or less attractive. | It does not make a technology unavailable merely because another eligible site's connection is cheaper; ineligibility comes from the eligibility filtering above. It also does not set a site's starting mix. |
| Cluster-level grid headroom | The aggregate permitted increase in electricity use for technologies in a cluster, relative to the base year, in constrained later periods. | It is not an individual-site electricity input or an individual-site electricity cap: sites in the cluster share the aggregate limit. |
| `known_changes` | PlantID/site-specific minimum and maximum production-share bounds for a named technology and output over specified years. These can steer the later use of technologies at that site. | It does not provide arbitrary PlantID-level base-year technology/process mixes, and it does not set unconstrained future choices outside the stated bounds and years. |

H2 infrastructure must be sufficient for the hydrogen use of a site's
hydrogen-consuming technologies.  CO2 infrastructure must be sufficient for
the CO2 captured by its CCS technologies.  These are capacity requirements tied
to selected technology use, rather than evidence that either technology will be
chosen.

## What this does not mean

- Separate site × technology × year variables do not automatically make sites
  different. Sites can still make the same choices when their available options
  and constraints lead to the same least-cost result.
- Arbitrary site-specific base-year technology or process mixes are not
  available as workbook inputs. The base-year allocation uses the one
  emissions-share scaling factor described above.
- Pathways are least-cost model outcomes under the stated assumptions, not
  forecasts of what individual sites will do.
