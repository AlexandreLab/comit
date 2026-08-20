#!/usr/bin/env Rscript
# Build COMIT's sector -> process -> technology taxonomy.
#
# Companion to docs/notes/15_carb3_process_comparison.md.
#
# Emits the same three-level shape as docs/notes/data/carb3_factory_processes.json
# so the two taxonomies can be compared directly:
#
#   { sector: { process: [technology, ...] } }
#
# In COMIT the middle level is the technology's PRIMARY OUTPUT COMMODITY - the
# energy service or product it delivers (high-temperature heat, motor drive,
# clinker, high-value chemicals). That is the closest structural analogue to a
# CaRB3 "process", though the two are not the same kind of thing - see the note.
#
# Also writes a flat CSV carrying the codes, for joining.
#
# Usage:
#   Rscript docs/notes/examples/build_comit_process_taxonomy.R <input_workbook.xlsx> [out.json] [out.csv]

suppressMessages({
  library(readxl)
  library(dplyr)
  library(jsonlite)
})

args     <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("usage: build_comit_process_taxonomy.R <input_workbook.xlsx> [out.json] [out.csv]")
workbook <- args[1]
out_json <- if (length(args) >= 2) args[2] else "docs/notes/data/comit_sector_processes.json"
out_csv  <- if (length(args) >= 3) args[3] else "docs/notes/data/comit_sector_processes.csv"

SKIP <- 6  # all COMIT input sheets carry six title rows

tec <- suppressMessages(read_excel(workbook, sheet = "Technologies", skip = SKIP))
cm  <- suppressMessages(read_excel(workbook, sheet = "commodities",  skip = SKIP))

flat <- tec %>%
  select(sector, output_commodity, technology_code = code,
         technology_name = name, technology_category, output_unit) %>%
  left_join(cm %>% select(commodity, description), by = c("output_commodity" = "commodity")) %>%
  mutate(process = coalesce(description, output_commodity)) %>%
  filter(!is.na(sector), !is.na(output_commodity)) %>%
  arrange(sector, process, technology_code)

# ---- flat CSV (carries the codes) -------------------------------------------
dir.create(dirname(out_csv), recursive = TRUE, showWarnings = FALSE)
write.csv(flat %>% select(sector, process_commodity = output_commodity, process_description = process,
                          technology_code, technology_name, technology_category, output_unit),
          out_csv, row.names = FALSE, na = "")

# ---- nested JSON, mirroring the CaRB3 file's shape --------------------------
taxonomy <- lapply(split(flat, flat$sector), function(s) {
  lapply(split(s, s$process), function(p) unname(p$technology_name))
})
# split() sorts keys; keep that - it makes the file diff-stable.

dir.create(dirname(out_json), recursive = TRUE, showWarnings = FALSE)
write(toJSON(taxonomy, pretty = TRUE, auto_unbox = FALSE), out_json)

message(sprintf("wrote %s and %s", out_json, out_csv))
message(sprintf("  sectors: %d | processes: %d | technologies: %d",
                length(unique(flat$sector)),
                nrow(distinct(flat, sector, process)),
                nrow(flat)))
