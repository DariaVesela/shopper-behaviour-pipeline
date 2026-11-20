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

## Licence

MIT. See [LICENSE](LICENSE).
