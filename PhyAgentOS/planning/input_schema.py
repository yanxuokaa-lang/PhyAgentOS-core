"""Validation helpers for frozen provider-neutral Tool input schemas."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from jsonschema import SchemaError
from jsonschema.validators import validator_for


class ToolInputSchemaError(ValueError):
    """A Tool input schema is malformed or unsupported."""


def validate_input_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached, validated object schema suitable for task binding."""
    if not isinstance(schema, Mapping):
        raise ToolInputSchemaError("Tool input_schema must be an object")
    value = dict(schema)
    if value.get("type") != "object":
        raise ToolInputSchemaError("Tool input_schema must declare object type")
    validator = validator_for(value)
    try:
        validator.check_schema(value)
    except SchemaError as exc:
        raise ToolInputSchemaError(f"Tool input_schema is invalid: {exc.message}") from exc
    return value


def required_argument_keys(schema: Mapping[str, Any] | None) -> tuple[str, ...]:
    """Project only required top-level argument names for Agent diagnostics."""
    if not isinstance(schema, Mapping):
        return ()
    required = schema.get("required", ())
    if not isinstance(required, (list, tuple)):
        return ()
    return tuple(item for item in required if isinstance(item, str) and item)


def validate_tool_arguments(
    schema: Mapping[str, Any],
    arguments: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return deterministic JSON Schema violations for final Tool arguments."""
    value = validate_input_schema(schema)
    validator = validator_for(value)(value)
    errors = sorted(
        validator.iter_errors(dict(arguments)),
        key=lambda item: (tuple(str(part) for part in item.absolute_path), item.message),
    )
    issues: list[str] = []
    for error in errors:
        path = "$"
        for part in error.absolute_path:
            path += f"[{part}]" if isinstance(part, int) else f".{part}"
        issues.append(f"{path}: {error.message}")
    return tuple(issues)


__all__ = [
    "ToolInputSchemaError",
    "required_argument_keys",
    "validate_input_schema",
    "validate_tool_arguments",
]
