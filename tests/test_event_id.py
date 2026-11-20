"""Tests for the deterministic event ID."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from schemas.event_id import event_id


@pytest.mark.parametrize(
    ("source_file", "line_number", "expected"),
    [
        # Expected values come from `printf '<name>:<line>' | shasum -a 256 | cut -c1-32`.
        ("2019-Oct.csv", 1, "8bb5b68b26122aacc4bc89501df780b3"),
        ("2019-Oct.csv", 2, "4e5f49e0226503783924e18bad4210c4"),
        ("2019-Nov.csv", 1, "6e96ff9c70448ff7095783d95f63e391"),
        ("2019-Nov.csv", 67501979, "aa3eb28a4c19d4c0c0f7eb31382579a8"),
    ],
)
def test_event_id_matches_the_committed_golden_value(
    source_file: str, line_number: int, expected: str
) -> None:
    assert event_id(source_file, line_number) == expected


@pytest.mark.parametrize(
    "path", ["data/raw/2019-Oct.csv", "/home/someone/data/2019-Oct.csv", "./2019-Oct.csv"]
)
def test_event_id_ignores_where_the_file_sits(path: str) -> None:
    assert event_id(path, 1) == event_id("2019-Oct.csv", 1)


def test_a_different_file_gives_a_different_id() -> None:
    assert event_id("2019-Oct.csv", 1) != event_id("2019-Nov.csv", 1)


def test_consecutive_lines_give_distinct_ids() -> None:
    ids = {event_id("2019-Oct.csv", line) for line in range(1, 10_001)}

    assert len(ids) == 10_000


def test_another_process_computes_the_same_id() -> None:
    """Guards against anything process-specific, such as Python's randomised str hash."""
    code = "from schemas.event_id import event_id; print(event_id('2019-Oct.csv', 1))"
    repo_root = Path(__file__).resolve().parent.parent

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env={**os.environ, "PYTHONHASHSEED": "random"},
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == event_id("2019-Oct.csv", 1)
