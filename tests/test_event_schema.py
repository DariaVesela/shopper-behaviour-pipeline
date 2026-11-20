"""Tests for the shared event schema and its validator."""

from typing import Any

import pytest
from fastavro import parse_schema

from schemas.event import InvalidEventError, load_event_schema, validate_event


def valid_event() -> dict[str, Any]:
    """A real event from the October 2019 file, plus the fields the pipeline adds."""
    return {
        "event_id": "0f3c9a1b2d4e5f60718293a4b5c6d7e8",
        "ingest_path": "stream",
        "event_time": "2019-10-01 00:00:00 UTC",
        "event_type": "view",
        "product_id": 44600062,
        "category_id": 2103807459595387724,
        "category_code": None,
        "brand": "shiseido",
        "price": 35.79,
        "user_id": 541312140,
        "user_session": "72d76fde-8bb3-4e00-8c23-a032dfed738c",
    }


def test_event_schema_parses_as_avro() -> None:
    parse_schema(load_event_schema())


def test_valid_event_passes() -> None:
    validate_event(valid_event())


@pytest.mark.parametrize(
    "field", ["event_id", "ingest_path", "event_time", "event_type", "product_id", "user_id"]
)
def test_missing_required_field_is_rejected_naming_the_field(field: str) -> None:
    event = valid_event()
    del event[field]

    with pytest.raises(InvalidEventError) as excinfo:
        validate_event(event)

    assert excinfo.value.field == field
    assert str(excinfo.value) == f"invalid event: required field {field!r} is missing"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("event_type", "click", id="unknown-event-type"),
        pytest.param("ingest_path", "kafka", id="unknown-ingest-path"),
        pytest.param("product_id", "44600062", id="wrong-type-product-id"),
        pytest.param("price", "35.79", id="wrong-type-price"),
        pytest.param("user_id", 541312140.5, id="wrong-type-user-id"),
    ],
)
def test_invalid_value_is_rejected_naming_the_field(field: str, value: object) -> None:
    event = {**valid_event(), field: value}

    with pytest.raises(InvalidEventError) as excinfo:
        validate_event(event)

    assert excinfo.value.field == field
    assert str(excinfo.value) == f"invalid event: field {field!r} has invalid value {value!r}"


@pytest.mark.parametrize(
    "field", ["category_id", "category_code", "brand", "price", "user_session"]
)
def test_optional_field_may_be_empty_or_missing(field: str) -> None:
    validate_event({**valid_event(), field: None})

    event = valid_event()
    del event[field]
    validate_event(event)
