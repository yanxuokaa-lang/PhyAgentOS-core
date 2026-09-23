"""Exact, task-owned copying of arguments from persisted execution records."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


class ArgumentSourceError(ValueError):
    """A declared argument source cannot be resolved without ambiguity."""


def source_path(value: Any, *, allow_empty: bool = False) -> tuple[str | int, ...]:
    if not isinstance(value, (list, tuple)) or (not value and not allow_empty):
        raise ArgumentSourceError("source/target path must be an explicit field/index array")
    if any(not ((isinstance(part, str) and part) or (type(part) is int and part >= 0)) for part in value):
        raise ArgumentSourceError("path components must be non-empty fields or non-negative integer indexes")
    return tuple(value)


def argument_path_schema(*, allow_empty: bool = False) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": 0 if allow_empty else 1,
        "items": {
            "anyOf": [
                {"type": "string", "minLength": 1},
                {"type": "integer", "minimum": 0},
            ]
        },
    }


def resolve_argument_sources(
    records: Mapping[str, tuple[Mapping[str, Any], Mapping[str, Any] | None]],
    literals: Mapping[str, Any],
    selectors: Mapping[str, Any],
) -> dict[str, Any]:
    """Copy exact authorized values into caller-declared argument paths."""

    resolved = deepcopy(dict(literals))
    assignments: list[tuple[tuple[str | int, ...], Any]] = []
    targets: list[tuple[str | int, ...]] = []
    for argument_name, selector in selectors.items():
        if not isinstance(argument_name, str) or not argument_name:
            raise ArgumentSourceError("argument source name must be non-empty")
        if (
            not isinstance(selector, Mapping)
            or not {"record_id", "path"} <= set(selector)
            or set(selector) - {"record_id", "path", "target_path", "map_field"}
        ):
            raise ArgumentSourceError(
                "source requires record_id, path and optional target_path/map_field"
            )
        path = source_path(selector["path"])
        target = source_path(selector.get("target_path", [argument_name]))
        if not isinstance(target[0], str):
            raise ArgumentSourceError("target_path must start with an object field")
        for previous in targets:
            size = min(len(previous), len(target))
            if previous[:size] == target[:size]:
                raise ArgumentSourceError("argument source targets overlap")
        targets.append(target)
        value = read_argument_source(records, selector["record_id"], path)
        map_field = selector.get("map_field")
        if map_field is not None:
            if not isinstance(map_field, str) or not map_field:
                raise ArgumentSourceError("map_field must be a non-empty object field name")
            if not isinstance(value, (list, tuple)) or any(
                not isinstance(item, Mapping) or map_field not in item for item in value
            ):
                raise ArgumentSourceError("map_field requires a list of objects containing that field")
            value = [item[map_field] for item in value]
        assignments.append((target, value))

    assignments.sort(key=lambda item: tuple(
        (0, part) if isinstance(part, str) else (1, part) for part in item[0]
    ))
    for target, value in assignments:
        _write_argument_path(resolved, target, value)
    return resolved


def read_argument_source(
    records: Mapping[str, tuple[Mapping[str, Any], Mapping[str, Any] | None]],
    record_id: Any,
    path: tuple[str | int, ...],
) -> Any:
    if not isinstance(record_id, str) or record_id not in records:
        raise ArgumentSourceError("argument source is not visible to this consumer")
    arguments, response = records[record_id]
    root: Any = {"arguments": arguments, "response": response}

    def read(value: Any, parts: tuple[str | int, ...]) -> tuple[bool, Any]:
        for part in parts:
            if isinstance(value, Mapping) and isinstance(part, str) and part in value:
                value = value[part]
            elif isinstance(value, (list, tuple)) and type(part) is int and 0 <= part < len(value):
                value = value[part]
            else:
                return False, None
        return True, value

    found, value = read(root, path)
    if found:
        return value
    if path and path[0] not in {"arguments", "response"}:
        argument_found, argument_value = read(arguments, path)
        response_found, response_value = read(response, path) if response is not None else (False, None)
        if argument_found and not response_found:
            return argument_value
        if response_found and not argument_found:
            return response_value
        if argument_found and response_found:
            if argument_value == response_value:
                return argument_value
            raise ArgumentSourceError(
                "argument source path is ambiguous between arguments and response"
            )
    part = path[-1] if path else None
    raise ArgumentSourceError(f"source path cannot be resolved at {part!r}")


def _write_argument_path(root: dict[str, Any], path: tuple[str | int, ...], value: Any) -> None:
    current: Any = root
    for index, part in enumerate(path):
        final = index == len(path) - 1
        child: Any = deepcopy(value) if final else ([] if type(path[index + 1]) is int else {})
        if isinstance(current, dict) and isinstance(part, str):
            if part in current:
                if final:
                    raise ArgumentSourceError("arguments cannot be both literal and sourced")
            else:
                current[part] = child
            current = current[part]
        elif isinstance(current, list) and type(part) is int and part <= len(current):
            if part == len(current):
                current.append(child)
            elif final:
                raise ArgumentSourceError("arguments cannot be both literal and sourced")
            current = current[part]
        else:
            raise ArgumentSourceError("argument source target has incompatible containers or a sparse array index")
