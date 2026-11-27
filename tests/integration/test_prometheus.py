"""Integration tests for Prometheus and the Kafka exporter in docker/compose.yaml."""

import json
import time
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from collections.abc import Callable, Iterator
from typing import TypeVar

import pytest

from tests.integration.stack import TOPIC_PARTITIONS, compose, kafka_tool

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("stack_running")]

PROMETHEUS_URL = "http://localhost:9090"
# Prometheus scrapes every 5s and the exporter may lag behind kafka-init, so allow a minute.
WAIT_SECONDS = 60

T = TypeVar("T")


def prometheus_api(path: str, **params: str) -> dict:
    """GET a Prometheus HTTP API endpoint on the host and return its `data`."""
    url = f"{PROMETHEUS_URL}/api/v1/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=10) as response:
        body = json.load(response)
    assert body["status"] == "success", body
    return body["data"]


def wait_for(observe: Callable[[], T], expected: T) -> T:
    """Observe until the value equals `expected` or time runs out, and return the last value.

    The caller asserts on the result, so a timeout fails showing what was actually seen.
    """
    deadline = time.monotonic() + WAIT_SECONDS
    while (value := observe()) != expected and time.monotonic() < deadline:
        time.sleep(2)
    return value


def query(promql: str) -> list[dict]:
    """Run an instant PromQL query and return its result series."""
    return prometheus_api("query", query=promql)["result"]


def series_per_topic(promql: str) -> dict[str, int]:
    """Count the series returned by `promql`, per topic label."""
    return dict(Counter(series["metric"]["topic"] for series in query(promql)))


def test_prometheus_scrapes_the_kafka_exporter_and_finds_it_up() -> None:
    def exporter_health() -> list[str]:
        targets = prometheus_api("targets", state="active")["activeTargets"]
        return [t["health"] for t in targets if t["labels"]["job"] == "kafka-exporter"]

    assert wait_for(exporter_health, ["up"]) == ["up"]


def test_offsets_are_recorded_for_every_partition_of_both_topics() -> None:
    def offsets() -> dict[str, int]:
        return series_per_topic("kafka_topic_partition_current_offset")

    assert wait_for(offsets, TOPIC_PARTITIONS) == TOPIC_PARTITIONS


@pytest.fixture
def consumer_group_on_events() -> Iterator[str]:
    """A throwaway consumer group with committed offsets on every events partition.

    Its offsets are set directly, so nothing is consumed from or written to events.
    """
    group = f"it-lag-{uuid.uuid4().hex[:8]}"
    kafka_tool(
        "kafka-consumer-groups.sh", "--group", group, "--topic", "events",
        "--reset-offsets", "--to-earliest", "--execute",
    )  # fmt: skip
    yield group
    kafka_tool("kafka-consumer-groups.sh", "--group", group, "--delete")


def test_consumer_group_lag_is_recorded_per_events_partition(consumer_group_on_events: str) -> None:
    promql = f'kafka_consumergroup_lag{{consumergroup="{consumer_group_on_events}"}}'
    expected = {"events": TOPIC_PARTITIONS["events"]}

    assert wait_for(lambda: series_per_topic(promql), expected) == expected


def test_record_rate_is_recorded_per_topic() -> None:
    """Records written per second to each topic, for the pipeline-health row of the dashboard."""
    expected = dict.fromkeys(TOPIC_PARTITIONS, 1)

    rate = wait_for(lambda: series_per_topic("topic:kafka_records_in:rate1m"), expected)

    assert rate == expected


def test_the_prometheus_config_and_rules_are_valid() -> None:
    """promtool also checks the rule files the config names; a failure fails the test."""
    compose(
        "exec", "-T", "prometheus", "promtool", "check", "config", "/etc/prometheus/prometheus.yml"
    )
