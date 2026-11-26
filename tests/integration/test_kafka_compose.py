"""Integration tests for the local Kafka in docker/compose.yaml. They need Docker running."""

import re
import socket
import struct
import subprocess
import uuid

import pytest

from tests.paths import REPO_ROOT

pytestmark = pytest.mark.integration

COMPOSE_FILE = REPO_ROOT / "docker" / "compose.yaml"
TOPIC_PARTITIONS = {"events": 6, "events-dlq": 1}


def run_or_fail(*command: str, stdin: str | None = None) -> str:
    """Run `command` from the repo root and return its stdout; fail the test if it fails."""
    result = subprocess.run(
        command, cwd=REPO_ROOT, input=stdin, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"{' '.join(command)} failed:\n{result.stdout}{result.stderr}"
    return result.stdout


def compose(*args: str, stdin: str | None = None) -> str:
    return run_or_fail("docker", "compose", "-f", str(COMPOSE_FILE), *args, stdin=stdin)


def kafka_tool(tool: str, *args: str, stdin: str | None = None) -> str:
    """Run one of Kafka's CLI tools inside the broker container, against its internal listener."""
    return compose(
        "exec", "-T", "kafka", f"/opt/kafka/bin/{tool}",
        "--bootstrap-server", "kafka:29092", *args,
        stdin=stdin,
    )  # fmt: skip


def partition_count(topic: str) -> int:
    description = kafka_tool("kafka-topics.sh", "--describe", "--topic", topic)
    match = re.search(r"PartitionCount:\s*(\d+)", description)
    assert match, f"no partition count for {topic!r} in:\n{description}"
    return int(match.group(1))


def advertised_brokers(host: str, port: int) -> list[tuple[str, int]]:
    """Ask the broker at host:port, as a client would, which addresses clients must use.

    Sends a Kafka Metadata request (v0, no topics) and returns each broker's (host, port).
    """
    client_id = b"integration-test"
    body = struct.pack(">hhih", 3, 0, 1, len(client_id)) + client_id + struct.pack(">i", 0)
    with socket.create_connection((host, port), timeout=10) as connection:
        connection.sendall(struct.pack(">i", len(body)) + body)
        response = _read_exactly(connection, struct.unpack(">i", _read_exactly(connection, 4))[0])
    # Response: correlation_id int32, then an array of brokers (node_id, host, port).
    (broker_count,) = struct.unpack_from(">i", response, 4)
    offset, brokers = 8, []
    for _ in range(broker_count):
        _node_id, host_length = struct.unpack_from(">ih", response, offset)
        offset += 6
        broker_host = response[offset : offset + host_length].decode()
        offset += host_length
        (broker_port,) = struct.unpack_from(">i", response, offset)
        offset += 4
        brokers.append((broker_host, broker_port))
    return brokers


def _read_exactly(connection: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = connection.recv(size - len(data))
        assert chunk, "broker closed the connection mid-response"
        data += chunk
    return data


@pytest.fixture(scope="module")
def kafka_running() -> None:
    """Start Kafka with `make up`. It is left running afterwards on purpose: local work may be
    using it, and `make up` is idempotent. CI stops it with `make clean`."""
    run_or_fail("make", "up")


@pytest.mark.usefixtures("kafka_running")
def test_make_up_brings_the_broker_up_healthy() -> None:
    container = compose("ps", "--quiet", "kafka").strip()

    health = run_or_fail("docker", "inspect", "--format", "{{.State.Health.Status}}", container)

    assert health.strip() == "healthy"


@pytest.mark.usefixtures("kafka_running")
@pytest.mark.parametrize(("topic", "partitions"), TOPIC_PARTITIONS.items())
def test_make_up_creates_the_topics(topic: str, partitions: int) -> None:
    assert partition_count(topic) == partitions


@pytest.mark.usefixtures("kafka_running")
def test_console_produce_and_consume_round_trip() -> None:
    """Uses a throwaway topic, so test records never reach the events topic Connect forwards."""
    topic = f"it-round-trip-{uuid.uuid4().hex[:8]}"
    record = f"user-1:hello-{uuid.uuid4().hex}"
    kafka_tool("kafka-topics.sh", "--create", "--topic", topic, "--partitions", "1")
    try:
        kafka_tool(
            "kafka-console-producer.sh", "--topic", topic,
            "--property", "parse.key=true", "--property", "key.separator=:",
            stdin=record + "\n",
        )  # fmt: skip
        consumed = kafka_tool(
            "kafka-console-consumer.sh", "--topic", topic, "--from-beginning",
            "--max-messages", "1", "--timeout-ms", "20000",
            "--property", "print.key=true", "--property", "key.separator=:",
        )  # fmt: skip
    finally:
        kafka_tool("kafka-topics.sh", "--delete", "--topic", topic)

    assert consumed.strip() == record


@pytest.mark.usefixtures("kafka_running")
def test_broker_tells_host_clients_to_use_localhost_9092() -> None:
    """A client on the host connects to whatever address the broker advertises, so a wrong
    advertised listener (e.g. kafka:9092) would break the replayer even with the port open."""
    assert advertised_brokers("localhost", 9092) == [("localhost", 9092)]


@pytest.mark.usefixtures("kafka_running")
def test_make_up_succeeds_again_with_the_topics_already_present() -> None:
    run_or_fail("make", "down")
    run_or_fail("make", "up")

    assert {topic: partition_count(topic) for topic in TOPIC_PARTITIONS} == TOPIC_PARTITIONS


@pytest.mark.usefixtures("kafka_running")
def test_make_up_succeeds_when_already_up() -> None:
    """`up --wait` used to fail at random once the one-shot kafka-init had exited."""
    for _ in range(3):
        run_or_fail("make", "up")
