"""The event schema shared by the replayer, backfill and Beam, and a validator for it.

Every component validates events here; none re-declares the fields.
"""

import json
from collections.abc import Mapping
from functools import cache
from pathlib import Path
from typing import Any

from fastavro import parse_schema
from fastavro.validation import ValidationError, validate

EVENT_SCHEMA_PATH = Path(__file__).with_name("event.avsc")


class InvalidEventError(ValueError):
    """An event that does not match the event schema. `field` names the first bad field."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"invalid event: {reason}")
        self.field = field


def load_event_schema() -> dict[str, Any]:
    """Return the Avro event schema as a JSON-decoded dict."""
    with EVENT_SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        return json.load(schema_file)


@cache
def _parsed_event_schema() -> dict[str, Any]:
    return parse_schema(load_event_schema())


def validate_event(event: Mapping[str, Any]) -> None:
    """Check `event` against the event schema; raise InvalidEventError naming the bad field.

    Only the first bad field is reported. Fields not in the schema are ignored.
    """
    try:
        validate(event, _parsed_event_schema(), raise_errors=True)
    except ValidationError as error:
        first = error.errors[0]
        # fastavro names the field by its full path, e.g. "shopper_pipeline.Event.user_id".
        field = first.field.rsplit(".", 1)[-1]
        if field not in event:
            raise InvalidEventError(field, f"required field {field!r} is missing") from error
        raise InvalidEventError(
            field, f"field {field!r} has invalid value {first.datum!r}"
        ) from error
