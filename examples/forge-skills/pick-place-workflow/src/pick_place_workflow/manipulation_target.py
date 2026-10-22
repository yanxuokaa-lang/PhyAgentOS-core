"""Provider-neutral perception targets shared by PAOS manipulation routes."""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any, Mapping, Protocol


class ManipulationTargetError(ValueError):
    """A perception target is stale, incomplete, or internally inconsistent."""


class ManipulationTargetResolver(Protocol):
    """Provider port for resolving measured references into execution data."""

    def resolve(
        self,
        binding: Mapping[str, Any],
        request: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


_REF = {"type": "string", "minLength": 1}
_WORLD_PATH = {"type": "string", "pattern": r"^/World/.+"}
_VECTOR3 = {"type": "array", "minItems": 3, "maxItems": 3, "items": {"type": "number"}}
_POSE = {
    "type": "object", "additionalProperties": False,
    "required": ["frame_id", "unit", "position_m", "orientation_xyzw"],
    "properties": {
        "frame_id": deepcopy(_REF), "unit": {"const": "m"},
        "position_m": deepcopy(_VECTOR3),
        "orientation_xyzw": {"type": "array", "minItems": 4, "maxItems": 4, "items": {"type": "number"}},
    },
}
_WORLD_FROM_CONTROL = {
    "type": "object", "additionalProperties": False,
    "required": ["parent_frame_id", "child_frame_id", "translation_m", "orientation_xyzw"],
    "properties": {
        "parent_frame_id": {"const": "world"},
        "child_frame_id": deepcopy(_REF),
        "translation_m": deepcopy(_VECTOR3),
        "orientation_xyzw": deepcopy(_POSE["properties"]["orientation_xyzw"]),
    },
}

MANIPULATION_TARGET_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": [
        "entity_ref", "destination_ref", "scene_revision", "frame_id", "calibration_ref",
        "control_frame_id",
        "world_from_control",
        "entity_prim_path", "destination_prim_path", "object_pose", "grasp_frame",
        "approach_direction", "destination_pose", "return_pose",
    ],
    "properties": {
        "candidate_ref": {"type": "string", "pattern": r"^candidate://[^/]+/.+$"},
        "entity_ref": {"type": "string", "pattern": r"^entity://[^/]+$"},
        "destination_ref": {"type": "string", "pattern": r"^destination://\S+$"},
        "scene_revision": deepcopy(_REF), "frame_id": deepcopy(_REF), "calibration_ref": deepcopy(_REF),
        "control_frame_id": deepcopy(_REF),
        "world_from_control": deepcopy(_WORLD_FROM_CONTROL),
        "entity_prim_path": deepcopy(_WORLD_PATH), "destination_prim_path": deepcopy(_WORLD_PATH),
        "tool_prim_path": deepcopy(_WORLD_PATH),
        "object_pose": deepcopy(_POSE), "grasp_frame": deepcopy(_POSE),
        "destination_pose": deepcopy(_POSE), "return_pose": deepcopy(_POSE),
        "approach_direction": {
            "type": "object", "additionalProperties": False,
            "required": ["frame_id", "unit", "vector"],
            "properties": {"frame_id": deepcopy(_REF), "unit": {"const": "unitless"}, "vector": deepcopy(_VECTOR3)},
        },
        "tool_frame": {
            "type": "object", "additionalProperties": False,
            "required": ["frame_id", "tip_axis_local"],
            "properties": {"frame_id": deepcopy(_REF), "tip_axis_local": deepcopy(_VECTOR3),
                           "tip_offset_m": deepcopy(_VECTOR3)},
        },
        "process_frame": {
            "type": "object", "additionalProperties": False,
            "required": ["frame_id", "origin_m", "axis"],
            "properties": {"frame_id": deepcopy(_REF), "origin_m": deepcopy(_VECTOR3), "axis": deepcopy(_VECTOR3)},
        },
        "geometry": {"type": "object", "additionalProperties": False,
                     "properties": {"size_m": deepcopy(_VECTOR3)}},
        "placement_tolerance_m": {"type": "number", "exclusiveMinimum": 0},
    },
}


def validate_manipulation_target(value: Any, arguments: Mapping[str, Any], *, process_type: str | None = None) -> dict[str, Any]:
    """Validate a selected perception candidate without inferring missing data."""
    if not isinstance(value, Mapping):
        raise ManipulationTargetError("manipulation_target is required")
    target = deepcopy(dict(value))
    for key in ("entity_ref", "destination_ref", "scene_revision", "frame_id", "calibration_ref", "control_frame_id"):
        if not isinstance(target.get(key), str) or not target[key].strip():
            raise ManipulationTargetError(f"manipulation_target.{key} is required")
    for key in ("entity_ref", "destination_ref", "scene_revision", "frame_id", "calibration_ref"):
        expected = arguments.get(key)
        if expected is not None and target[key] != expected:
            raise ManipulationTargetError(f"manipulation_target.{key} does not match the Action")
    candidate_ref = target.get("candidate_ref")
    if candidate_ref is not None and candidate_ref != arguments.get("candidate_ref", candidate_ref):
        raise ManipulationTargetError("manipulation_target.candidate_ref does not match the selected candidate")
    for key in ("entity_prim_path", "destination_prim_path"):
        if not isinstance(target.get(key), str) or not target[key].startswith("/World/"):
            raise ManipulationTargetError(f"manipulation_target.{key} must be an absolute /World path")
    _validate_world_transform(target.get("world_from_control"), target["control_frame_id"])
    for key in ("object_pose", "grasp_frame", "destination_pose", "return_pose"):
        _validate_pose(target.get(key), key, target["control_frame_id"])
    approach = target.get("approach_direction")
    if not isinstance(approach, Mapping) or approach.get("frame_id") != target["control_frame_id"]:
        raise ManipulationTargetError("approach_direction must use control_frame_id")
    _validate_vector(approach.get("vector"), "approach_direction.vector", nonzero=True)
    if process_type == "stir":
        tool = target.get("tool_frame")
        if not isinstance(tool, Mapping):
            raise ManipulationTargetError("stir requires manipulation_target.tool_frame")
        _validate_vector(tool.get("tip_axis_local"), "tool_frame.tip_axis_local", nonzero=True)
        if tool.get("tip_offset_m") is not None:
            _validate_vector(tool["tip_offset_m"], "tool_frame.tip_offset_m")
    if process_type == "pour":
        frame = target.get("process_frame")
        if not isinstance(frame, Mapping) or frame.get("frame_id") != target["control_frame_id"]:
            raise ManipulationTargetError("pour requires process_frame in control_frame_id")
        _validate_vector(frame.get("origin_m"), "process_frame.origin_m")
        _validate_vector(frame.get("axis"), "process_frame.axis", nonzero=True)
    geometry = target.get("geometry")
    if isinstance(geometry, Mapping) and geometry.get("size_m") is not None:
        _validate_vector(geometry["size_m"], "geometry.size_m", positive=True)
    tolerance = target.get("placement_tolerance_m")
    if tolerance is not None and (not _finite(tolerance) or float(tolerance) <= 0):
        raise ManipulationTargetError("placement_tolerance_m must be positive")
    return target


def resolve_manipulation_target(
    resolver: ManipulationTargetResolver,
    binding: Mapping[str, Any],
    request: Mapping[str, Any],
    *,
    process_type: str,
) -> dict[str, Any]:
    """Resolve and validate an adapter-private target without inventing identity."""
    if not isinstance(binding, Mapping) or not isinstance(request, Mapping):
        raise ManipulationTargetError("perception binding and target request are required")
    for key in ("entity_ref", "destination_ref", "scene_revision", "frame_id", "calibration_ref"):
        if not isinstance(binding.get(key), str) or not binding[key].strip():
            raise ManipulationTargetError(f"perception binding.{key} is required")
        if request.get(key) != binding[key]:
            raise ManipulationTargetError(f"target request {key} differs from perception binding")
    freshness, max_age = binding.get("freshness_ms"), binding.get("max_age_ms")
    if (
        isinstance(freshness, bool) or not isinstance(freshness, int) or freshness < 0
        or isinstance(max_age, bool) or not isinstance(max_age, int) or max_age < 1
        or freshness > max_age
    ):
        raise ManipulationTargetError("perception binding is stale or has invalid freshness")
    resolve = getattr(resolver, "resolve", None)
    if not callable(resolve):
        raise ManipulationTargetError("target resolver must expose resolve(binding, request)")
    result = resolve(deepcopy(dict(binding)), deepcopy(dict(request)))
    if not isinstance(result, Mapping):
        raise ManipulationTargetError("target resolver returned a non-object target")
    target = validate_manipulation_target(result, binding, process_type=process_type)
    expected = {
        "entity_ref": binding.get("entity_ref"),
        "destination_ref": binding.get("destination_ref"),
        "scene_revision": binding.get("scene_revision"),
        "frame_id": binding.get("frame_id"),
        "calibration_ref": binding.get("calibration_ref"),
        "candidate_ref": binding.get("candidate_ref"),
    }
    if any(value is not None and target.get(key) != value for key, value in expected.items()):
        raise ManipulationTargetError("resolved target does not preserve perception binding identity")
    return target


def target_diagnostics(value: Any, arguments: Mapping[str, Any], *, process_type: str | None = None) -> dict[str, Any]:
    if value is None:
        return {"status": "missing", "motion_authorized": False, "error": "manipulation_target is required"}
    try:
        target = validate_manipulation_target(value, arguments, process_type=process_type)
    except ManipulationTargetError as exc:
        return {"status": "invalid", "motion_authorized": False, "error": str(exc)}
    return {"status": "available", "motion_authorized": False,
            "entity_prim_path": target["entity_prim_path"],
            "destination_prim_path": target["destination_prim_path"],
            "tool_frame_id": (target.get("tool_frame") or {}).get("frame_id")}


def _validate_pose(value: Any, name: str, frame_id: str) -> None:
    if not isinstance(value, Mapping) or value.get("unit") != "m" or value.get("frame_id") != frame_id:
        raise ManipulationTargetError(f"{name} must use frame {frame_id} and meters")
    _validate_vector(value.get("position_m"), f"{name}.position_m")
    quat = value.get("orientation_xyzw")
    if not isinstance(quat, (list, tuple)) or len(quat) != 4 or not all(_finite(item) for item in quat):
        raise ManipulationTargetError(f"{name}.orientation_xyzw must contain four finite values")
    if abs(math.sqrt(sum(float(item) ** 2 for item in quat)) - 1.0) > 1e-3:
        raise ManipulationTargetError(f"{name}.orientation_xyzw must be normalized")


def _validate_world_transform(value: Any, child_frame_id: str) -> None:
    if not isinstance(value, Mapping) or value.get("parent_frame_id") != "world" or value.get("child_frame_id") != child_frame_id:
        raise ManipulationTargetError("world_from_control must bind world to control_frame_id")
    _validate_vector(value.get("translation_m"), "world_from_control.translation_m")
    quat = value.get("orientation_xyzw")
    if not isinstance(quat, (list, tuple)) or len(quat) != 4 or not all(_finite(item) for item in quat):
        raise ManipulationTargetError("world_from_control.orientation_xyzw must contain four finite values")
    if abs(math.sqrt(sum(float(item) ** 2 for item in quat)) - 1.0) > 1e-3:
        raise ManipulationTargetError("world_from_control.orientation_xyzw must be normalized")


def _validate_vector(value: Any, name: str, *, nonzero: bool = False, positive: bool = False) -> None:
    if not isinstance(value, (list, tuple)) or len(value) != 3 or not all(_finite(item) for item in value):
        raise ManipulationTargetError(f"{name} must contain three finite values")
    if nonzero and math.sqrt(sum(float(item) ** 2 for item in value)) <= 1e-9:
        raise ManipulationTargetError(f"{name} must not be zero")
    if positive and any(float(item) <= 0 for item in value):
        raise ManipulationTargetError(f"{name} must contain positive values")


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False
