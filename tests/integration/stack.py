"""Helpers for driving the local Docker Compose stack from integration tests."""

import subprocess

from tests.paths import REPO_ROOT

COMPOSE_FILE = REPO_ROOT / "docker" / "compose.yaml"
# The topics kafka-init creates, with their partition counts.
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
