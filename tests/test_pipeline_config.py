"""Tests for the shared pipeline config file and its loader."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from config.pipeline import (
    PIPELINE_CONFIG_PATH,
    PipelineConfig,
    PipelineConfigError,
    load_pipeline_config,
)
from tests.paths import REPO_ROOT


def valid_values() -> dict[str, Any]:
    return {
        "session_gap_minutes": 30,
        "allowed_lateness_minutes": 60,
        "idle_cart_minutes": 15,
        "early_result_event_count": 5,
        "decisive_buyer_max_views": 5,
        "browser_min_views": 3,
        "deal_hunter_share_below_reference_price": 0.5,
    }


def write_yaml(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "pipeline.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def write_config(tmp_path: Path, values: dict[str, Any]) -> Path:
    return write_yaml(tmp_path, yaml.safe_dump(values))


def test_committed_config_loads_with_the_agreed_values() -> None:
    assert load_pipeline_config(PIPELINE_CONFIG_PATH) == PipelineConfig(**valid_values())


def test_missing_key_is_rejected_naming_the_key(tmp_path: Path) -> None:
    values = valid_values()
    del values["idle_cart_minutes"]

    with pytest.raises(PipelineConfigError) as excinfo:
        load_pipeline_config(write_config(tmp_path, values))

    assert excinfo.value.key == "idle_cart_minutes"
    assert "missing" in str(excinfo.value)


def test_unknown_key_is_rejected_naming_the_key(tmp_path: Path) -> None:
    """A misspelt key must not leave the real one silently missing or defaulted."""
    values = {**valid_values(), "sesion_gap_minutes": 30}

    with pytest.raises(PipelineConfigError) as excinfo:
        load_pipeline_config(write_config(tmp_path, values))

    assert excinfo.value.key == "sesion_gap_minutes"
    assert "unknown" in str(excinfo.value)


@pytest.mark.parametrize(
    ("key", "value", "reason"),
    [
        pytest.param("session_gap_minutes", "30", "must be a whole number", id="duration-str"),
        pytest.param("session_gap_minutes", True, "must be a whole number", id="duration-bool"),
        pytest.param("idle_cart_minutes", 15.5, "must be a whole number", id="duration-float"),
        pytest.param("allowed_lateness_minutes", 0, "must be 1 or more", id="zero-duration"),
        pytest.param("idle_cart_minutes", -15, "must be 1 or more", id="negative-duration"),
        pytest.param("early_result_event_count", 0, "must be 1 or more", id="zero-count"),
        pytest.param("browser_min_views", -3, "must be 1 or more", id="negative-count"),
        pytest.param(
            "deal_hunter_share_below_reference_price", "0.5", "must be a number", id="share-str"
        ),
        pytest.param(
            "deal_hunter_share_below_reference_price", True, "must be a number", id="share-bool"
        ),
        pytest.param(
            "deal_hunter_share_below_reference_price", 1.5, "between 0 and 1", id="share-above-1"
        ),
        pytest.param(
            "deal_hunter_share_below_reference_price", -0.1, "between 0 and 1", id="share-below-0"
        ),
    ],
)
def test_invalid_value_is_rejected_naming_the_key(
    tmp_path: Path, key: str, value: object, reason: str
) -> None:
    values = {**valid_values(), key: value}

    with pytest.raises(PipelineConfigError) as excinfo:
        load_pipeline_config(write_config(tmp_path, values))

    assert excinfo.value.key == key
    assert reason in str(excinfo.value)


def test_make_dbt_vars_prints_the_yaml_values_as_json() -> None:
    """Tests through make on purpose: this printed JSON is the contract dbt's --vars relies on."""
    result = subprocess.run(
        ["make", "dbt-vars"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    expected = yaml.safe_load(PIPELINE_CONFIG_PATH.read_text(encoding="utf-8"))
    assert json.loads(result.stdout) == expected


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("", id="empty"),
        pytest.param("- a\n", id="list"),
        pytest.param("x\n", id="word"),
    ],
)
def test_a_file_that_is_not_a_mapping_is_rejected(tmp_path: Path, content: str) -> None:
    path = write_yaml(tmp_path, content)

    with pytest.raises(PipelineConfigError, match="must be a mapping of keys to values"):
        load_pipeline_config(path)


def valid_yaml_lines() -> list[str]:
    return [f"{key}: {value}" for key, value in valid_values().items()]


def yaml_text(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def test_duplicate_key_is_rejected_naming_the_key(tmp_path: Path) -> None:
    """Otherwise the last value would silently win over the one a reader sees first."""
    path = write_yaml(tmp_path, yaml_text([*valid_yaml_lines(), "session_gap_minutes: 45"]))

    with pytest.raises(PipelineConfigError) as excinfo:
        load_pipeline_config(path)

    assert excinfo.value.key == "session_gap_minutes"
    assert "duplicate" in str(excinfo.value)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("15:00", id="sexagesimal"),
        pytest.param("015", id="leading-zero"),
        pytest.param("0x0f", id="hex"),
        pytest.param("1_5", id="underscore"),
    ],
)
def test_a_number_not_written_as_plain_digits_is_rejected(tmp_path: Path, text: str) -> None:
    """YAML 1.1 would read 15:00 as 900 and 015 as 13, both plausible-looking durations."""
    lines = [
        f"idle_cart_minutes: {text}" if line.startswith("idle_cart_minutes:") else line
        for line in valid_yaml_lines()
    ]

    with pytest.raises(PipelineConfigError) as excinfo:
        load_pipeline_config(write_yaml(tmp_path, yaml_text(lines)))

    assert excinfo.value.key == "idle_cart_minutes"
    assert "must be a whole number" in str(excinfo.value)


@pytest.mark.parametrize(("line", "key"), [("~: 5", "None"), ("1: 5", "1"), ("yes: 5", "True")])
def test_a_key_that_is_not_text_is_rejected(tmp_path: Path, line: str, key: str) -> None:
    path = write_yaml(tmp_path, yaml_text([*valid_yaml_lines(), line]))

    with pytest.raises(PipelineConfigError) as excinfo:
        load_pipeline_config(path)

    assert excinfo.value.key == key
    assert "must be text" in str(excinfo.value)


def test_a_path_given_as_text_loads() -> None:
    assert load_pipeline_config(str(PIPELINE_CONFIG_PATH)) == PipelineConfig(**valid_values())


def test_make_dbt_vars_prints_only_json_when_run_from_another_directory(tmp_path: Path) -> None:
    """`make -C` turns on directory printing, which would put 'Entering directory' in stdout."""
    result = subprocess.run(
        ["make", "-C", str(REPO_ROOT), "dbt-vars"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(result.stdout) == valid_values()


def test_decisive_buyer_max_views_may_be_zero(tmp_path: Path) -> None:
    """0 is a valid tuning: a Decisive buyer then buys without viewing anything first."""
    values = {**valid_values(), "decisive_buyer_max_views": 0}

    assert load_pipeline_config(write_config(tmp_path, values)).decisive_buyer_max_views == 0


def test_decisive_buyer_max_views_may_not_be_negative(tmp_path: Path) -> None:
    values = {**valid_values(), "decisive_buyer_max_views": -1}

    with pytest.raises(PipelineConfigError, match="must be 0 or more"):
        load_pipeline_config(write_config(tmp_path, values))
