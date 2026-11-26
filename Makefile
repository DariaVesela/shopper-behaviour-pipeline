.PHONY: help lint format test test-integration dbt-vars up down logs clean

# make -C and recursive make print "Entering directory" to stdout, which would corrupt dbt-vars.
MAKEFLAGS += --no-print-directory

help: ## List the available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-18s %s\n", $$1, $$2}'

lint: ## Check linting and formatting
	uv run ruff check .
	uv run ruff format --check .

format: ## Fix lint issues and format the code
	uv run ruff check --fix .
	uv run ruff format .

test: ## Run the unit tests
	uv run pytest

test-integration: ## Run the integration tests (needs Docker)
	uv run pytest -m integration

dbt-vars: ## Print config/pipeline.yaml as the JSON dbt takes through --vars
	@uv run --quiet python -m config.pipeline

COMPOSE := docker compose -f docker/compose.yaml

# Wait only for the long-running services, then run the one-shot topic creation on its own:
# `up --wait` on everything fails at random once kafka-init has exited.
up: ## Start local Kafka and create its topics; waits until the broker is healthy
	$(COMPOSE) up --detach --wait kafka
	$(COMPOSE) run --rm kafka-init

down: ## Stop local services, keeping topics and their records
	$(COMPOSE) down

logs: ## Show the local services' logs
	$(COMPOSE) logs

clean: ## Stop local services and delete their data
	$(COMPOSE) down --volumes
