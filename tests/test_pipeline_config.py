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


def write_config(tmp_path: Path, values: dict[str, Any]) -> Path:
    path = tmp_path / "pipeline.yaml"
    path.write_text(yaml.safe_dump(values), encoding="utf-8")
    return path


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
    repo_root = Path(__file__).resolve().parent.parent

    result = subprocess.run(
        ["make", "dbt-vars"],
        cwd=repo_root,
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
    path = tmp_path / "pipeline.yaml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(PipelineConfigError, match="must be a mapping of keys to values"):
        load_pipeline_config(path)
