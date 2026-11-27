.PHONY: help lint format test test-integration dbt-vars up down logs clean \
	tf-init tf-check tf-plan tf-apply tf-destroy keys

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
up: ## Start Kafka, its topics, the exporter and Prometheus; waits until all are healthy
	$(COMPOSE) up --detach --wait kafka kafka-exporter prometheus
	$(COMPOSE) run --rm kafka-init

down: ## Stop local services, keeping topics, their records and metrics
	$(COMPOSE) down

logs: ## Show the local services' logs
	$(COMPOSE) logs

clean: ## Stop local services and delete their data
	$(COMPOSE) down --volumes

TF := terraform -chdir=infra/terraform

# Needs infra/terraform/backend.hcl and terraform.tfvars; copy them from the .example files.
tf-init: ## Initialise Terraform with the remote state bucket
	$(TF) init -input=false -backend-config=backend.hcl

tf-check: ## Check Terraform formatting, validity and the mocked Terraform tests (no credentials)
	$(TF) init -input=false -backend=false
	$(TF) fmt -check -recursive
	$(TF) validate
	$(TF) test

tf-plan: tf-init ## Show what Terraform would change in GCP
	$(TF) plan

tf-apply: tf-init ## Create or update the GCP resources (asks before changing anything)
	$(TF) apply

tf-destroy: tf-init ## Delete the GCP resources; refuses while the data bucket holds files
	$(TF) destroy

keys: tf-init ## Write a key file per service account to secrets/ (600); keeps existing ones
	uv run python -m scripts.service_account_keys
