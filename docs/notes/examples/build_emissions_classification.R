#!/usr/bin/env Rscript
# Build the per-technology emissions-source classification table.
#
# Companion to docs/notes/14_emissions_source_split.md.
#
# Reads a COMIT input workbook and writes docs/notes/data/emissions_source_classification.csv:
# one row per technology, recording how much of its direct emissions come from
# PROCESS chemistry (scales with output) versus ENERGY combustion (scales with fuel).
#
# The classification is a-priori: it depends only on the input workbook, not on any
# solve, so it is stable across scenarios.
#
# Usage:
#   Rscript docs/notes/examples/build_emissions_classification.R <input_workbook.xlsx> [ref_year] [out.csv]
#
# Defaults to ref_year = 2021 (fuel emission factors are year-dependent).

suppressMessages({
  library(readxl)
  library(dplyr)
  library(tidyr)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("usage: build_emissions_classification.R <input_workbook.xlsx> [ref_year] [out.csv]")
workbook <- args[1]
ref_year <- if (length(args) >= 2) as.numeric(args[2]) else 2021
out_csv  <- if (length(args) >= 3) args[3] else "docs/notes/data/emissions_source_classification.csv"

# All COMIT input sheets carry six title rows above the header.
SKIP <- 6

# ---- Parameters that are HARDCODED in R/fct_emissions.R -----------------------
# These cannot be changed by editing the workbook; see note 14 section 6.
INDIRECT_COMMODITIES <- c("INDDISTELC", "INDMAINSHYG", "INDMAINSHYGG", "INDMAINSHYGB")  # :180-183
BIOMASS_CATEGORY     <- "Biomass and organic waste"                                     # :234

# ---- Read -------------------------------------------------------------------
io  <- suppressMessages(read_excel(workbook, sheet = "technology_input_output", skip = SKIP))
cm  <- suppressMessages(read_excel(workbook, sheet = "commodities",             skip = SKIP))
fe  <- suppressMessages(read_excel(workbook, sheet = "Fuel_emissions",          skip = SKIP))
tec <- suppressMessages(read_excel(workbook, sheet = "Technologies",            skip = SKIP))

io <- io %>%
  mutate(output                       = as.numeric(output),
         commodity_produces_emissions = as.logical(commodity_produces_emissions),
         primary_commodity            = as.logical(primary_commodity))

cm <- cm %>% mutate(process_emission = as.logical(process_emission))

# Process-emission commodities are DATA-DRIVEN: whatever the workbook flags.
# Adding a fourth needs no code change.
proc_commodities <- cm %>% filter(process_emission %in% TRUE) %>% pull(commodity)
if (length(proc_commodities) == 0) warning("no commodities flagged process_emission = TRUE")

# Fuel emission factors for the reference year, long form (kt per PJ).
fuel_factors <- fe %>%
  filter(year == ref_year) %>%
  select(-year) %>%
  pivot_longer(everything(), names_to = "commodity", values_to = "fuel_CO2e") %>%
  mutate(fuel_CO2e = as.numeric(fuel_CO2e))

# ---- Process intensity, split by gas ----------------------------------------
# Process commodities are produced (output > 0) and are already expressed in
# kt CO2e, so no fuel factor and no GWP conversion is applied.
process <- io %>%
  filter(commodity %in% proc_commodities) %>%
  group_by(technology_code, commodity) %>%
  summarise(kt = sum(output), .groups = "drop") %>%
  pivot_wider(names_from = commodity, values_from = kt, values_fill = 0)

for (nm in proc_commodities) if (!nm %in% names(process)) process[[nm]] <- 0

# ---- Energy intensity --------------------------------------------------------
# Fuels are consumed (output < 0), hence the sign flip, matching
# calculate_CO2_direct_emissions() in R/fct_emissions.R.
energy <- io %>%
  filter(commodity_produces_emissions %in% TRUE, !commodity %in% proc_commodities) %>%
  inner_join(fuel_factors, by = "commodity") %>%
  left_join(cm %>% select(commodity, commodity_category), by = "commodity") %>%
  mutate(kt         = -output * fuel_CO2e,
         is_direct  = !commodity %in% INDIRECT_COMMODITIES,
         is_biomass = commodity_category %in% BIOMASS_CATEGORY) %>%
  group_by(technology_code) %>%
  summarise(energy_direct_kt_per_unit   = sum(kt[is_direct]),
            energy_indirect_kt_per_unit = sum(kt[!is_direct]),
            # What the model actually books when zero_emissions_from_biomass is on
            # (the default): biomass fuels are recoded to a zero factor first.
            energy_direct_biomass_zerorated_kt_per_unit = sum(kt[is_direct & !is_biomass]),
            consumes_biomass_fuel       = any(is_biomass),
            n_emitting_fuel_inputs      = n(),
            emitting_fuel_commodities   = paste(sort(unique(commodity)), collapse = ";"),
            .groups = "drop")

# ---- Assemble ----------------------------------------------------------------
classification <- tec %>%
  select(technology_code = code, technology_name = name, sector,
         technology_category, output_commodity, output_unit,
         emissions_released, retrofit_to) %>%
  left_join(process, by = "technology_code") %>%
  left_join(energy,  by = "technology_code") %>%
  mutate(across(all_of(proc_commodities), ~ coalesce(.x, 0)),
         across(c(energy_direct_kt_per_unit, energy_indirect_kt_per_unit,
                  energy_direct_biomass_zerorated_kt_per_unit,
                  n_emitting_fuel_inputs), ~ coalesce(.x, 0)),
         consumes_biomass_fuel = coalesce(consumes_biomass_fuel, FALSE),
         emitting_fuel_commodities = coalesce(emitting_fuel_commodities, ""),
         process_total_kt_per_unit = rowSums(across(all_of(proc_commodities))),
         direct_total_kt_per_unit  = process_total_kt_per_unit + energy_direct_kt_per_unit,
         process_share_pct = ifelse(abs(direct_total_kt_per_unit) > 1e-9,
                                    round(100 * process_total_kt_per_unit / direct_total_kt_per_unit, 1),
                                    NA_real_),
         emission_class = case_when(
           abs(direct_total_kt_per_unit) < 1e-9                                  ~ "E_zero_direct",
           process_total_kt_per_unit > 1e-9 & abs(energy_direct_kt_per_unit) < 1e-9 ~ "A_pure_process",
           process_total_kt_per_unit > 1e-9 & process_share_pct >= 50             ~ "B_process_dominant",
           process_total_kt_per_unit > 1e-9                                       ~ "C_mixed_energy_dominant",
           TRUE                                                                   ~ "D_pure_energy"),
         fuel_factor_year = ref_year)

# Stable, reviewable ordering.
classification <- classification %>% arrange(sector, desc(process_share_pct), technology_code)

# Rename the raw process commodity columns to self-describing names.
rename_map <- c(INDCO2P = "process_co2_kt_per_unit",
                INDCH4P = "process_ch4_kt_per_unit",
                INDN2OP = "process_n2o_kt_per_unit")
for (old in names(rename_map)) {
  if (old %in% names(classification)) names(classification)[names(classification) == old] <- rename_map[[old]]
}

col_order <- c("technology_code", "technology_name", "sector", "technology_category",
               "output_commodity", "output_unit", "emission_class", "process_share_pct",
               "process_co2_kt_per_unit", "process_ch4_kt_per_unit", "process_n2o_kt_per_unit",
               "process_total_kt_per_unit", "energy_direct_kt_per_unit",
               "energy_direct_biomass_zerorated_kt_per_unit",
               "energy_indirect_kt_per_unit", "direct_total_kt_per_unit",
               "consumes_biomass_fuel",
               "emissions_released", "n_emitting_fuel_inputs", "emitting_fuel_commodities",
               "retrofit_to", "fuel_factor_year")
classification <- classification %>% select(any_of(col_order), everything())

dir.create(dirname(out_csv), recursive = TRUE, showWarnings = FALSE)
write.csv(classification, out_csv, row.names = FALSE, na = "")

message(sprintf("wrote %s: %d technologies", out_csv, nrow(classification)))
print(classification %>% count(emission_class, name = "technologies"))
