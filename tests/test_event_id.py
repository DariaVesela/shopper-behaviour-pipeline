"""Tests for the deterministic event ID."""

import os
import subprocess
import sys

import pytest

from schemas.event_id import event_id
from tests.paths import REPO_ROOT


@pytest.mark.parametrize(
    ("source_file", "record_number", "expected"),
    [
        # Expected values come from `printf '<name>:<record>' | shasum -a 256 | cut -c1-32`.
        ("2019-Oct.csv", 1, "8bb5b68b26122aacc4bc89501df780b3"),
        ("2019-Oct.csv", 2, "4e5f49e0226503783924e18bad4210c4"),
        ("2019-Nov.csv", 1, "6e96ff9c70448ff7095783d95f63e391"),
        ("2019-Nov.csv", 67501979, "aa3eb28a4c19d4c0c0f7eb31382579a8"),
    ],
)
def test_event_id_matches_the_committed_golden_value(
    source_file: str, record_number: int, expected: str
) -> None:
    assert event_id(source_file, record_number) == expected


@pytest.mark.parametrize(
    "path", ["data/raw/2019-Oct.csv", "/home/someone/data/2019-Oct.csv", "./2019-Oct.csv"]
)
def test_event_id_ignores_where_the_file_sits(path: str) -> None:
    assert event_id(path, 1) == event_id("2019-Oct.csv", 1)


def test_a_different_file_gives_a_different_id() -> None:
    assert event_id("2019-Oct.csv", 1) != event_id("2019-Nov.csv", 1)


def test_consecutive_records_give_distinct_ids() -> None:
    ids = {event_id("2019-Oct.csv", record) for record in range(1, 10_001)}

    assert len(ids) == 10_000


def test_another_process_computes_the_same_id() -> None:
    """Guards against anything process-specific, such as Python's randomised str hash."""
    code = "from schemas.event_id import event_id; print(event_id('2019-Oct.csv', 1))"

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        # PYTHONPATH, not cwd, finds the repo, so this also works with PYTHONSAFEPATH set.
        env={
            **os.environ,
            "PYTHONHASHSEED": "random",
            "PYTHONSAFEPATH": "1",
            "PYTHONPATH": str(REPO_ROOT),
        },
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == event_id("2019-Oct.csv", 1)


@pytest.mark.parametrize(
    ("record_number", "error"),
    [
        pytest.param(0, ValueError, id="zero"),
        pytest.param(-1, ValueError, id="negative"),
        pytest.param(True, TypeError, id="bool"),
        pytest.param(1.0, TypeError, id="float"),
        pytest.param("1", TypeError, id="str"),
    ],
)
def test_a_record_number_that_is_not_a_positive_int_is_rejected(
    record_number: object, error: type[Exception]
) -> None:
    """1.0 or True would otherwise give a different ID from 1 for the same event."""
    with pytest.raises(error):
        event_id("2019-Oct.csv", record_number)


@pytest.mark.parametrize("source_file", ["", ".", "data/.."])
def test_a_source_file_without_a_name_is_rejected(source_file: str) -> None:
    """Otherwise record 1 of every file would share one ID."""
    with pytest.raises(ValueError, match="no file name"):
        event_id(source_file, 1)
