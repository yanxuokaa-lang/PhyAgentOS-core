"""Validation helpers for frozen provider-neutral Tool input schemas."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
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


def _selected_one_of_sibling_keys(
    input_schema: Mapping[str, Any],
    explicit_arguments: Mapping[str, Any],
) -> set[str]:
    """Return sibling discriminator keys excluded by the selected oneOf branch."""
    branches = input_schema.get("oneOf")
    if not isinstance(branches, list) or not branches:
        return set()

    explicit_keys = set(explicit_arguments)
    candidates: list[tuple[int, set[str], set[str]]] = []
    discriminator_keys: set[str] = set()
    for branch in branches:
        if not isinstance(branch, Mapping):
            continue
        required = set(branch.get("required") or ())
        not_schema = branch.get("not")
        forbidden = (
            set(not_schema.get("required") or ())
            if isinstance(not_schema, Mapping)
            else set()
        )
        discriminator_keys.update(required)
        if forbidden & explicit_keys:
            continue
        score = len(required & explicit_keys)
        if score:
            candidates.append((score, required, forbidden))

    if not candidates:
        return set()
    best_score = max(score for score, _required, _forbidden in candidates)
    winners = [item for item in candidates if item[0] == best_score]
    if len(winners) != 1:
        return set()
    _score, selected_required, selected_forbidden = winners[0]
    return selected_forbidden | (discriminator_keys - selected_required)


def materialize_tool_arguments(
    input_schema: Mapping[str, Any] | None,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Return one canonical Tool argument representation for planning and execution.

    Defaults are applied only at the top level because that is the supported
    PAOS ToolSpec boundary.  ``oneOf`` sibling fields from non-selected branches
    remain suppressed, matching JSON Schema branch semantics.
    """
    effective_arguments = deepcopy(dict(arguments))
    if not isinstance(input_schema, Mapping):
        return effective_arguments
    suppressed_defaults = _selected_one_of_sibling_keys(input_schema, effective_arguments)
    properties = input_schema.get("properties", {})
    if not isinstance(properties, Mapping):
        return effective_arguments
    for name, definition in properties.items():
        if (
            isinstance(name, str)
            and name not in effective_arguments
            and name not in suppressed_defaults
            and isinstance(definition, Mapping)
            and "default" in definition
        ):
            effective_arguments[name] = deepcopy(definition["default"])
    return effective_arguments


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
    "materialize_tool_arguments",
    "required_argument_keys",
    "validate_input_schema",
    "validate_tool_arguments",
]
