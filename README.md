# shopper-behaviour-pipeline

Real-time behavioural analytics on a replayed e-commerce clickstream: each shopping session is classified while it is still open, and the same events are processed in batch for comparison.

> **Work in progress.** The pipeline is being built ticket by ticket; most directories below are still empty.

## Layout

| Directory | What it holds |
| --- | --- |
| `replayer/` | Replays the historical event files into Kafka in event-time order, with optional fault injection |
| `backfill/` | Loads the full event history into the bronze layer in BigQuery |
| `beam/` | The Apache Beam streaming job: sessions, live classification and signals |
| `dbt/` | dbt models for the silver and gold layers (batch) |
| `infra/terraform/` | GCP infrastructure |
| `docker/` | Docker Compose stack for local Kafka, Connect, Prometheus and Grafana |
| `config/` | Shared pipeline settings read by both dbt and Beam |
| `schemas/` | The event schema shared by every component |
| `grafana/` | Provisioned data sources and dashboards |
| `scripts/` | One-off and helper scripts |
| `tests/` | The pytest suite |

## Development

Requires [uv](https://docs.astral.sh/uv/) and `make`.

```sh
uv sync          # installs the pinned Python and the dev tools
make lint test
```

Each component has its own dependency group, installed only when needed (for example `uv sync --group replayer`). `make help` lists every target.

Local services run in Docker (Docker Desktop or Docker Engine with Compose v2):

```sh
make up                 # Kafka on localhost:9092, with the events (6 partitions) and events-dlq topics
make test-integration   # tests against the running services
make down               # stop; topics and their records are kept (make clean deletes them)
```

GCP resources are managed with Terraform (version in `infra/terraform/versions.tf`) in `infra/terraform/`. After the one-off bootstrap (a project with billing, `gcloud auth application-default login`, and a versioned bucket for Terraform state), copy `terraform.tfvars.example` and `backend.hcl.example` there without the `.example` suffix and fill them in. Both copies are gitignored.

```sh
make tf-check     # formatting, validation and plan tests against a mocked provider; no credentials
make tf-plan      # what would change in GCP
make tf-apply     # enables the APIs, creates the data bucket and the monthly budget
make tf-destroy   # removes them again; refuses while the data bucket holds files
```

Each component (Kafka Connect, Grafana, Beam) runs as its own service account. `make keys` writes their key files to the gitignored `secrets/`, readable only by you, and leaves existing ones alone. To replace a key, revoke it first, since deleting the file alone leaves the old key valid: `gcloud iam service-accounts keys delete <private_key_id from the file> --iam-account=<client_email from the file>`, then delete the file and run `make keys`. Your own scripts use your `gcloud` login instead.

```console
$ make keys
...
created secrets/beam.json
created secrets/grafana.json
created secrets/kafka-connect.json
```

### Example output

The shared pipeline config, as the JSON that dbt receives through `--vars`:

```console
$ make dbt-vars
{"session_gap_minutes": 30, "allowed_lateness_minutes": 60, "idle_cart_minutes": 15, "early_result_event_count": 5, "decisive_buyer_max_views": 5, "browser_min_views": 3, "deal_hunter_share_below_reference_price": 0.5}
```

An invalid event is rejected naming the bad field:

```console
$ uv run python -c "from schemas.event import validate_event; validate_event({'event_type': 'click'})"
...
schemas.event.InvalidEventError: invalid event: required field 'event_id' is missing
```

## Key design decisions

- **Deterministic event IDs.** The dataset has no event ID, so each event's ID is a hash of its source file's name and its CSV record number (`schemas/event_id.py`). Replay and backfill therefore give the same event the same ID, and duplicates can be dropped by it anywhere in the pipeline. The recipe is fixed: changing it would give every stored event a new ID.
- **One event schema.** `schemas/event.avsc` is the single definition of an event, used by the replayer, backfill, Pub/Sub, bronze and Beam. Events with a missing, mistyped or unknown field are rejected rather than loaded.
- **One config file for batch and streaming.** Session gap, allowed lateness and the shopper-type thresholds live only in `config/pipeline.yaml`. Beam loads it and dbt receives it as `--vars`, so the two paths cannot drift apart. A YAML file rather than a Python constants module, because dbt cannot import Python.
- **Budget in the billing account's currency.** The monthly budget is 10 units with alerts at 50%, 90% and 100%. The Budgets API rejects any currency other than the billing account's own, so Terraform leaves it unset rather than hard-coding dollars.
- **Destroy keeps APIs and data.** `make tf-destroy` leaves the APIs on, since turning one off can break things outside this config, and refuses to delete a data bucket that still holds files.
- **Service account keys never touch Terraform.** Terraform creates the accounts, but the keys are made by `make keys` with `gcloud`, so no private key is ever stored in Terraform state. Each account gets only the roles on the resources it uses, added by the change that creates each resource; BigQuery Job User is the one project-wide role, for Grafana and Beam, since BigQuery has nothing narrower.
- **Kafka in KRaft mode, topics created explicitly.** One local broker with no ZooKeeper. Automatic topic creation is off, so a misspelt topic name fails instead of silently creating a new topic.

## Licence

MIT. See [LICENSE](LICENSE).
