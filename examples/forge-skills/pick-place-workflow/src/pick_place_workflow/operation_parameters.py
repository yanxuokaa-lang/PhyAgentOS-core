"""Shared parameter contracts for provider-neutral process subtasks."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Mapping

from jsonschema import Draft202012Validator, ValidationError

_POSITIVE = {"type": "number", "exclusiveMinimum": 0}

PROCESS_PARAMETER_PROPERTIES: dict[str, dict[str, Any]] = {
    "pour": {
        "tilt_rad": {**_POSITIVE, "maximum": 3.141592653589793},
        "hold_s": deepcopy(_POSITIVE),
    },
    "stir": {
        "radius_m": deepcopy(_POSITIVE),
        "depth_m": deepcopy(_POSITIVE),
        "turns": deepcopy(_POSITIVE),
        "duration_s": deepcopy(_POSITIVE),
        "direction": {"enum": ["cw", "ccw"]},
    },
}


def process_parameters_schema(operation: str) -> dict[str, Any]:
    """Return the exact parameter object schema for one semantic operation."""
    properties = PROCESS_PARAMETER_PROPERTIES.get(operation)
    if properties is None:
        raise ValueError(f"unsupported process operation: {operation}")
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": deepcopy(properties),
        "required": list(properties),
    }


def validate_process_parameters(operation: str, parameters: Mapping[str, Any]) -> None:
    """Reject missing, unexpected, non-finite, or out-of-domain task values."""
    try:
        json.dumps(parameters, ensure_ascii=False, allow_nan=False)
        Draft202012Validator(process_parameters_schema(operation)).validate(parameters)
    except (TypeError, ValueError, ValidationError) as exc:
        detail = exc.message if isinstance(exc, ValidationError) else str(exc)
        raise ValueError(f"invalid {operation} parameters: {detail}") from exc
