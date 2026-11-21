.PHONY: help lint format test dbt-vars

# make -C and recursive make print "Entering directory" to stdout, which would corrupt dbt-vars.
MAKEFLAGS += --no-print-directory

help: ## List the available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-10s %s\n", $$1, $$2}'

lint: ## Check linting and formatting
	uv run ruff check .
	uv run ruff format --check .

format: ## Fix lint issues and format the code
	uv run ruff check --fix .
	uv run ruff format .

test: ## Run the test suite
	uv run pytest

dbt-vars: ## Print config/pipeline.yaml as the JSON dbt takes through --vars
	@uv run --quiet python -m config.pipeline
