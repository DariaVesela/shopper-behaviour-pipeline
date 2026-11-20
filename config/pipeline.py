"""The shared pipeline config: tunable values that dbt and Beam both read from one file.

Beam calls load_pipeline_config() at startup. dbt gets the same values as JSON through
`dbt run --vars "$(make dbt-vars)"`, which runs this module.
"""

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml

PIPELINE_CONFIG_PATH = Path(__file__).with_name("pipeline.yaml")


class PipelineConfigError(ValueError):
    """A pipeline config file that is invalid.

    `key` names the first bad key, or is None when the file as a whole is not a mapping.
    """

    def __init__(self, key: str | None, reason: str) -> None:
        super().__init__(f"invalid pipeline config: {reason}")
        self.key = key


def _positive_int(key: str, value: object) -> int:
    # bool is a subclass of int, so `true` would otherwise load as 1.
    if isinstance(value, bool) or not isinstance(value, int):
        raise PipelineConfigError(key, f"{key!r} must be a whole number, got {value!r}")
    if value < 1:
        raise PipelineConfigError(key, f"{key!r} must be 1 or more, got {value!r}")
    return value


def _share(key: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PipelineConfigError(key, f"{key!r} must be a number, got {value!r}")
    if not 0 <= value <= 1:
        raise PipelineConfigError(key, f"{key!r} must be between 0 and 1, got {value!r}")
    return float(value)


def _setting(validate: Callable[[str, object], int | float]) -> Any:
    """Declare a config field together with the check its YAML value must pass."""
    return field(metadata={"validate": validate})


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """The values in config/pipeline.yaml. Durations are whole minutes of event time."""

    session_gap_minutes: int = _setting(_positive_int)
    allowed_lateness_minutes: int = _setting(_positive_int)
    idle_cart_minutes: int = _setting(_positive_int)
    early_result_event_count: int = _setting(_positive_int)
    decisive_buyer_max_views: int = _setting(_positive_int)
    browser_min_views: int = _setting(_positive_int)
    deal_hunter_share_below_reference_price: float = _setting(_share)


def load_pipeline_config(path: Path) -> PipelineConfig:
    """Read and validate the pipeline config at `path`; raise PipelineConfigError naming the key.

    Every key is required, unknown keys are rejected, and only the first bad key is reported.
    """
    with path.open(encoding="utf-8") as config_file:
        values = yaml.safe_load(config_file)
    if not isinstance(values, dict):
        raise PipelineConfigError(
            None, f"{path.name} must be a mapping of keys to values, got {values!r}"
        )
    settings = {setting.name: setting.metadata["validate"] for setting in fields(PipelineConfig)}
    for key in values:
        if key not in settings:
            raise PipelineConfigError(key, f"unknown key {key!r}")
    for key in settings:
        if key not in values:
            raise PipelineConfigError(key, f"required key {key!r} is missing")
    return PipelineConfig(**{key: validate(key, values[key]) for key, validate in settings.items()})


def main() -> None:
    """Print the validated config as one line of JSON, the form dbt's --vars takes."""
    print(json.dumps(asdict(load_pipeline_config(PIPELINE_CONFIG_PATH))))


if __name__ == "__main__":
    main()
