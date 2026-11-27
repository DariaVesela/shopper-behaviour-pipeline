# Pub/Sub messages are written as Avro-JSON

Status: accepted (2026-11-27)

## Context

The `events` Pub/Sub topic will carry `schemas/event.avsc` with JSON message encoding. Google's docs do not say how strictly Pub/Sub reads JSON against an Avro schema, so we tested it on a throwaway schema and topic in the project, publishing variants of one valid Event:

| Message | Result |
| --- | --- |
| `"brand": "shiseido"` (plain value for an optional field) | rejected: `INVALID_JSON_AVRO_MESSAGE`, expected object |
| `"brand": {"string": "shiseido"}` (Avro-JSON union form) | accepted |
| `"brand": null` | accepted |
| `brand` left out (it has a default of null) | rejected: field was not found |
| `"price": 9.99` (plain value for an optional double) | rejected: expected object |
| fastavro `json_writer` output, fields set and fields left out | both accepted |

So Pub/Sub accepts only strict Avro-JSON: a non-null value of an optional field must be wrapped in its type name, null stays bare, and every field must be present; schema defaults are not applied.

## Decision

Everything that publishes Events to Pub/Sub serialises them with fastavro's `json_writer` against `schemas/event.avsc`, never with `json.dumps`. An Event is still checked with `validate_event` as a plain dict before it is serialised; `json_writer` then produces the wire form, including the wrapped unions and the nulls for fields left out.

## Consequences

- The replayer (and anything else that publishes) depends on fastavro's JSON encoder, not just its validator.
- Consumers reading Pub/Sub messages directly see the wrapped form (`{"string": "shiseido"}`), so they must decode with the schema (fastavro's `json_reader`) rather than read the JSON as-is. Whether a BigQuery subscription using the topic schema unwraps the unions into plain columns is not yet tested; check it in the Pub/Sub ticket.
- A hand-written test message must use the wrapped form, or it is rejected at publish time.
