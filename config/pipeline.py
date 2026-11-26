"""The shared pipeline config: tunable values that dbt and Beam both read from one file.

Beam calls load_pipeline_config() at startup. dbt gets the same values as JSON from this
module, which exits non-zero on an invalid config. Scripts should run it directly and stop
on failure, since `$(...)` ignores exit codes and make may add its own lines to stdout:

    vars=$(uv run --quiet python -m config.pipeline) && dbt run --vars "$vars"

`make dbt-vars` prints the same JSON for people to read.
"""

import json
import re
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


def _whole_number_at_least(minimum: int) -> Callable[[str, object], int]:
    """A check that a YAML value is a whole number of `minimum` or more."""

    def check(key: str, value: object) -> int:
        # bool is a subclass of int, so `true` would otherwise load as 1.
        if isinstance(value, bool) or not isinstance(value, int):
            raise PipelineConfigError(key, f"{key!r} must be a whole number, got {value!r}")
        if value < minimum:
            raise PipelineConfigError(key, f"{key!r} must be {minimum} or more, got {value!r}")
        return value

    return check


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

    session_gap_minutes: int = _setting(_whole_number_at_least(1))
    allowed_lateness_minutes: int = _setting(_whole_number_at_least(1))
    idle_cart_minutes: int = _setting(_whole_number_at_least(1))
    early_result_event_count: int = _setting(_whole_number_at_least(1))
    decisive_buyer_max_views: int = _setting(_whole_number_at_least(0))
    browser_min_views: int = _setting(_whole_number_at_least(1))
    deal_hunter_share_below_reference_price: float = _setting(_share)


_YAML_INT_TAG = "tag:yaml.org,2002:int"


def _decimal_only_int_resolvers() -> dict[str, list[tuple[str, re.Pattern[str]]]]:
    """SafeLoader's implicit resolvers, with YAML 1.1's int rule narrowed to plain digits."""
    resolvers = {
        first_char: [(tag, regex) for tag, regex in rules if tag != _YAML_INT_TAG]
        for first_char, rules in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }
    decimal = re.compile(r"^(?:0|[-+]?[1-9][0-9]*)$")
    for first_char in "-+0123456789":
        resolvers.setdefault(first_char, []).append((_YAML_INT_TAG, decimal))
    return resolvers


class _StrictLoader(yaml.SafeLoader):
    """A SafeLoader that rejects duplicate keys and reads only plain decimal digits as ints.

    YAML 1.1 would read 15:00 as 900 and 015 as 13; here they stay strings and fail validation.
    """

    yaml_implicit_resolvers = _decimal_only_int_resolvers()

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        seen: set[Any] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise PipelineConfigError(str(key), f"duplicate key {key!r}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load_pipeline_config(path: str | Path) -> PipelineConfig:
    """Read and validate the pipeline config at `path`; raise PipelineConfigError naming the key.

    Every key is required, unknown keys are rejected, and only the first bad key is reported.
    """
    path = Path(path)
    with path.open(encoding="utf-8") as config_file:
        values = yaml.load(config_file, Loader=_StrictLoader)  # _StrictLoader is a SafeLoader
    if not isinstance(values, dict):
        raise PipelineConfigError(
            None, f"{path.name} must be a mapping of keys to values, got {values!r}"
        )
    for key in values:
        if not isinstance(key, str):
            raise PipelineConfigError(str(key), f"keys must be text, got {key!r}")
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
