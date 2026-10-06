"""Shared parsing and normalization for Adapter-owned RoboTwin Runtime profiles."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

RUNTIME_PROFILE_SCHEMA_VERSION = "paos-robotwin20-runtime-profile/v1"
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
CAMERA_REFS = {
    "camera/head": "head_camera",
    "camera/front": "front_camera",
    "camera/left_wrist": "left_camera",
    "camera/right_wrist": "right_camera",
}

EmbodimentSpec = str | tuple[str, str, float]


class RuntimeProfileError(ValueError):
    """The Adapter-owned Runtime profile is unavailable or violates its schema."""


def normalize_embodiment(value: EmbodimentSpec | list[Any]) -> EmbodimentSpec:
    """Normalize RoboTwin's single- or two-single-arm embodiment syntax."""
    if isinstance(value, str):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 3:
        left, right, interval = value
        if (
            isinstance(left, str)
            and isinstance(right, str)
            and isinstance(interval, (int, float))
            and not isinstance(interval, bool)
            and math.isfinite(float(interval))
            and interval > 0
        ):
            return (left, right, float(interval))
    raise RuntimeProfileError(
        "embodiment must be a name or [left_name, right_name, positive_interval]"
    )


def normalize_additional_static_cameras(value: Any) -> tuple[dict[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise RuntimeProfileError("additional_static_cameras must be an array")
    result: list[dict[str, Any]] = []
    names: set[str] = set()
    required = {"name", "type", "position", "forward", "left"}
    for camera in value:
        if not isinstance(camera, Mapping) or set(camera) != required:
            raise RuntimeProfileError(
                "additional_static_cameras entries must define name, type, position, forward, left"
            )
        name = camera["name"]
        camera_type = camera["type"]
        if (
            not isinstance(name, str)
            or IDENTIFIER_PATTERN.fullmatch(name) is None
            or name in names
            or not isinstance(camera_type, str)
            or IDENTIFIER_PATTERN.fullmatch(camera_type) is None
        ):
            raise RuntimeProfileError("additional static camera identity is invalid")
        normalized: dict[str, Any] = {"name": name, "type": camera_type}
        for field in ("position", "forward", "left"):
            vector = camera[field]
            if (
                not isinstance(vector, (list, tuple))
                or len(vector) != 3
                or any(
                    not isinstance(item, (int, float))
                    or isinstance(item, bool)
                    or not math.isfinite(float(item))
                    for item in vector
                )
            ):
                raise RuntimeProfileError(
                    f"additional static camera {field} must contain three finite numbers"
                )
            normalized[field] = [float(item) for item in vector]
        names.add(name)
        result.append(normalized)
    return tuple(result)


def normalize_runtime_profile(value: Any) -> dict[str, Any]:
    """Validate one parsed Runtime profile and return its canonical consumer view."""
    required = {
        "schema_version",
        "task_name",
        "task_config",
        "embodiment",
        "max_observation_age_ms",
        "seed",
        "robot_identity",
        "gripper_identity",
        "embodiment_topology",
        "planner_profile",
    }
    optional = {"additional_static_cameras", "sensor_ref", "sensor_refs"}
    if (
        not isinstance(value, Mapping)
        or not required.issubset(value)
        or set(value) - required - optional
    ):
        raise RuntimeProfileError("runtime profile fields are invalid")
    if value["schema_version"] != RUNTIME_PROFILE_SCHEMA_VERSION:
        raise RuntimeProfileError("runtime profile schema_version is unsupported")

    sensor_ref = value.get("sensor_ref")
    sensor_refs = value.get("sensor_refs")
    if (sensor_ref is None) == (sensor_refs is None):
        raise RuntimeProfileError(
            "runtime profile must define exactly one of sensor_ref or sensor_refs"
        )
    if sensor_refs is not None:
        if (
            not isinstance(sensor_refs, (list, tuple))
            or not sensor_refs
            or any(
                not isinstance(item, str) or item not in CAMERA_REFS
                for item in sensor_refs
            )
            or len(set(sensor_refs)) != len(sensor_refs)
        ):
            raise RuntimeProfileError(
                "runtime profile sensor_refs must name distinct supported cameras"
            )
        normalized_sensor_refs = tuple(sensor_refs)
        sensor_ref = normalized_sensor_refs[0]
    else:
        if not isinstance(sensor_ref, str) or sensor_ref not in CAMERA_REFS:
            raise RuntimeProfileError("runtime profile sensor_ref is invalid")
        normalized_sensor_refs = (sensor_ref,)

    embodiment = normalize_embodiment(value["embodiment"])
    if (
        not isinstance(value["task_name"], str)
        or IDENTIFIER_PATTERN.fullmatch(value["task_name"]) is None
        or not isinstance(value["task_config"], str)
        or IDENTIFIER_PATTERN.fullmatch(value["task_config"]) is None
        or not isinstance(value["seed"], int)
        or isinstance(value["seed"], bool)
    ):
        raise RuntimeProfileError("runtime profile task fields are invalid")
    if (
        type(value["max_observation_age_ms"]) is not int
        or value["max_observation_age_ms"] < 1
    ):
        raise RuntimeProfileError("runtime profile observation age is invalid")
    for field in (
        "robot_identity",
        "gripper_identity",
        "embodiment_topology",
        "planner_profile",
    ):
        if not isinstance(value[field], str) or not value[field].strip():
            raise RuntimeProfileError(f"runtime profile {field} is invalid")
    expected_topology = "native-dual-arm" if isinstance(embodiment, str) else "two-single-arm"
    if value["embodiment_topology"] != expected_topology:
        raise RuntimeProfileError(
            "runtime profile embodiment_topology does not match embodiment"
        )
    return {
        **value,
        "embodiment": embodiment,
        "sensor_ref": sensor_ref,
        "sensor_refs": normalized_sensor_refs,
        "additional_static_cameras": normalize_additional_static_cameras(
            value.get("additional_static_cameras")
        ),
    }


def load_runtime_profile(path: Path) -> dict[str, Any]:
    """Load a profile once for all Adapter, Runtime, and materializer consumers."""
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise RuntimeProfileError("runtime profile must be an absolute regular file")
    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover - deployment dependency boundary
        raise RuntimeProfileError("PyYAML is required to load a runtime profile") from exc

    class _UniqueKeyLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in result:
                raise RuntimeProfileError("runtime profile contains duplicate YAML keys")
            result[key] = loader.construct_object(value_node, deep=deep)
        return result

    _UniqueKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise RuntimeProfileError("runtime profile could not be loaded") from exc
    return normalize_runtime_profile(value)
