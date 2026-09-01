# comit — documentation and data consistency checks.
#
# These guard the generated documents and the hand-researched CaRB3 data tables.
# Nothing here touches the R package; use devtools::test() for that.
#
# Run `make check` before any change to docs/specs/ or docs/notes/data/.

PYTHON ?= python3
EXAMPLES := docs/notes/examples

.DEFAULT_GOAL := help

.PHONY: help check docs-check data-check data-report docs-build

help: ## Show available targets
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2}'

check: docs-check data-check ## Run every consistency check

docs-check: ## Verify the generated interface docs match the spec
	@$(PYTHON) $(EXAMPLES)/build_interface_docs.py --check

data-check: ## Validate the CaRB3 data tables (blocking checks only)
	@$(PYTHON) $(EXAMPLES)/validate_carb3_data.py --quiet

data-report: ## Full CaRB3 data report, including advisory counts
	@$(PYTHON) $(EXAMPLES)/validate_carb3_data.py

docs-build: ## Regenerate the interface docs and spec diagrams
	@$(PYTHON) $(EXAMPLES)/build_interface_docs.py
	@$(PYTHON) $(EXAMPLES)/build_spec_flow_diagram.py
