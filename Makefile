# comit — documentation and data consistency checks.
#
# These guard the generated documents and the hand-researched CaRB3 data tables.
# Nothing here touches the R package; use devtools::test() for that.
#
# Run `make check` before any change to docs/specs/ or docs/notes/data/.

PYTHON ?= python3

# The carb3 package has its own uv-managed environment. The stdlib-only generators
# under docs/notes/examples/ must not share it, so $(PYTHON) never sees carb3's deps.
UV     ?= uv

# Absolute, derived from this file's own location, so `make -f ../../Makefile
# docs-check` works from anywhere in the tree. Relative paths here silently
# resolved against the caller's directory and the targets failed with a
# FileNotFoundError that read like a missing generator.
REPO     := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
EXAMPLES := $(REPO)/docs/notes/examples
CARB3    := $(REPO)/carb3

.DEFAULT_GOAL := help

.PHONY: help check docs-check docs-list data-check data-report data-worklist docs-build carb3 carb3-run

help: ## Show available targets
	@grep -hE '^[a-z0-9-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2}'

check: docs-check data-check carb3 ## Run every consistency check

docs-check: ## Verify the generated interface docs and diagrams match their specs
	@$(PYTHON) $(EXAMPLES)/build_interface_docs.py --all --check
	@$(PYTHON) $(EXAMPLES)/build_spec_flow_diagram.py --all --check

docs-list: ## Show the configured specs and which outputs are switched on
	@$(PYTHON) $(EXAMPLES)/build_interface_docs.py --list

data-check: ## Validate the CaRB3 data tables (blocking checks only)
	@$(PYTHON) $(EXAMPLES)/validate_carb3_data.py --quiet

data-report: ## Full CaRB3 data report, including advisory counts
	@$(PYTHON) $(EXAMPLES)/validate_carb3_data.py

# The unservable-duty work list note 22 Task 10 reads: every duty row no eligible unit can
# serve, with its cause and the note 20 item or note 22 task that owns it. Regenerate it
# after any change to the duty profile, the unit tables or eligibility, and commit it.
WORKLIST := $(REPO)/docs/notes/data/build/unservable_duties.csv

data-worklist: ## Write the unservable-duty work list (docs/notes/data/build/unservable_duties.csv)
	@$(PYTHON) $(EXAMPLES)/validate_carb3_data.py --quiet --unservable-csv $(WORKLIST)

docs-build: ## Regenerate the interface docs and spec diagrams
	@$(PYTHON) $(EXAMPLES)/build_interface_docs.py --all
	@$(PYTHON) $(EXAMPLES)/build_spec_flow_diagram.py --all

carb3: ## Run the carb3 package tests
	@$(UV) run --directory $(CARB3) pytest

# Not part of `make check`: this solves and writes, where every other target only reads
# and verifies. PREMISES overrides which premises run, OUT_DIR asks for the parquet ledger.
#   make carb3-run PREMISES=mvp-dairy OUT_DIR=outputs/carb3
#
# PREMISES also carries the CLI's own switches, which is how the note 21 §4.4 sensitivity
# is run:
#   make carb3-run PREMISES="mvp-cement --co2-tariff 60"
#
# All three premises solve as of 2026-09-20, so it exits zero. It still exits non-zero if
# any premise does not solve — §5.2 makes that a reported outcome, and the whole report is
# printed above the error rather than swallowed by it.
carb3-run: ## Solve the synthetic premises and print the run report
	@$(UV) run --directory $(CARB3) python -m carb3 $(PREMISES) \
	  $(if $(OUT_DIR),--out-dir $(abspath $(OUT_DIR)))
