"""Provider-neutral, no-motion geometry Query for relational placement goals."""

from __future__ import annotations

import math
import re
from copy import deepcopy
from typing import Any, Mapping, Protocol


class RelationTargetProvider(Protocol):
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None: ...


RELATION_TARGET_TOOL_SPEC = {
    "tool_id": "relation.target",
    "endpoint_id": "relation_target",
    "operation": "propose",
    "semantics": "query",
    "description": (
        "Resolve a relational placement goal against the current scene into measured "
        "geometry candidates. This Query does not prepare or authorize motion."
    ),
    "planning": {
        "schema_version": "paos-tool-spec-policy/v1",
        "capabilities": ["relation.target"],
        "input_binding_keys": [
            "entity_ref", "goal_relation", "relation_target_ref", "observation_ref",
            "scene_revision", "frame_id", "calibration_ref",
        ],
        "scene_write_behavior": "none",
        "requires_before_plan": True,
    },
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "entity_ref", "goal_relation", "relation_target_ref", "observation_ref",
            "scene_revision", "frame_id", "calibration_ref", "freshness_ms", "max_age_ms",
        ],
        "properties": {
            "entity_ref": {"type": "string", "pattern": "^entity://[^/]+$"},
            "goal_relation": {"type": "string", "minLength": 1},
            "relation_target_ref": {"type": "string", "pattern": "^(entity|surface)://[^/]+$"},
            "observation_ref": {"type": "string", "pattern": "^observation://[^/]+/[^/]+$"},
            "scene_revision": {"type": "string", "minLength": 1},
            "frame_id": {"type": "string", "minLength": 1},
            "calibration_ref": {"type": "string", "pattern": "^artifact://\\S+$"},
            "freshness_ms": {"type": "integer", "minimum": 0},
            "max_age_ms": {"type": "integer", "minimum": 1},
        },
    },
    "output_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "status", "candidate_set_ref", "entity_ref", "goal_relation",
            "relation_target_ref", "observation_ref", "scene_revision", "frame_id",
            "calibration_ref", "candidates", "motion_authorized",
        ],
        "properties": {
            "status": {"enum": ["available", "empty", "ambiguous", "stale", "invalid", "unavailable"]},
            "candidate_set_ref": {"type": "string", "pattern": "^relation-target-set://\\S+$"},
            "entity_ref": {"type": "string", "pattern": "^entity://[^/]+$"},
            "goal_relation": {"type": "string", "minLength": 1},
            "relation_target_ref": {"type": "string", "pattern": "^(entity|surface)://[^/]+$"},
            "observation_ref": {"type": "string", "pattern": "^observation://[^/]+/[^/]+$"},
            "scene_revision": {"type": "string", "minLength": 1},
            "frame_id": {"type": "string", "minLength": 1},
            "calibration_ref": {"type": "string", "pattern": "^artifact://\\S+$"},
            "candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["candidate_ref", "destination_ref", "world_T_object_target", "evidence_refs"],
                    "properties": {
                        "candidate_ref": {"type": "string", "pattern": "^relation-target://\\S+$"},
                        "destination_ref": {"type": "string", "pattern": "^destination://\\S+$"},
                        "world_T_object_target": {"type": "array", "minItems": 16, "maxItems": 16, "items": {"type": "number"}},
                        "evidence_refs": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "pattern": "^artifact://\\S+$"}},
                    },
                },
            },
            "motion_authorized": {"const": False},
            "error": {"type": "string"},
        },
    },
}

_CANDIDATE_REF = re.compile(r"^relation-target://\S+$")


class RelationTargetQueryEndpoint:
    """Validate relation geometry output and bind it to the exact fresh Query."""

    def __init__(self, provider: RelationTargetProvider):
        self.provider = provider

    def invoke(self, arguments: Any) -> dict[str, Any]:
        from jsonschema import Draft202012Validator

        if list(Draft202012Validator(RELATION_TARGET_TOOL_SPEC["input_schema"]).iter_errors(arguments)):
            return self._failure("invalid", "relation target Query arguments are invalid")
        request = deepcopy(dict(arguments))
        identity_keys = (
            "entity_ref", "goal_relation", "relation_target_ref", "observation_ref",
            "scene_revision", "frame_id", "calibration_ref",
        )
        if request["observation_ref"] != f"observation://{request['scene_revision']}/{request['frame_id']}":
            return self._failure("invalid", "observation identity differs from scene/frame")
        if request["freshness_ms"] > request["max_age_ms"]:
            return self._failure("stale", "relation target observation exceeds max_age_ms")
        try:
            result = self.provider.propose(request)
        except Exception:
            return self._failure("unavailable", "relation target provider failed")
        if not isinstance(result, Mapping):
            return self._failure("unavailable", "relation target geometry is unavailable")
        if any(result.get(key) != request[key] for key in identity_keys):
            return self._failure("stale", "relation target evidence does not match the current Query")
        status = result.get("status")
        if status not in {"available", "empty", "ambiguous", "stale", "invalid", "unavailable"}:
            return self._failure("invalid", "relation target provider returned an unknown status")
        set_ref = result.get("candidate_set_ref")
        candidates = result.get("candidates")
        if (
            not isinstance(set_ref, str)
            or not set_ref.startswith("relation-target-set://")
            or not isinstance(candidates, (list, tuple))
        ):
            return self._failure("invalid", "relation target provider returned invalid candidates")
        normalized = []
        seen: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                return self._failure("invalid", "relation target candidate is not an object")
            candidate_ref = candidate.get("candidate_ref")
            destination_ref = candidate.get("destination_ref")
            pose = candidate.get("world_T_object_target")
            evidence_refs = candidate.get("evidence_refs")
            if (
                not isinstance(candidate_ref, str)
                or _CANDIDATE_REF.fullmatch(candidate_ref) is None
                or candidate_ref in seen
                or not isinstance(destination_ref, str)
                or not destination_ref.startswith("destination://")
                or not _valid_rigid_pose(pose)
                or not isinstance(evidence_refs, (list, tuple))
                or not evidence_refs
                or any(not isinstance(ref, str) or not ref.startswith("artifact://") for ref in evidence_refs)
            ):
                return self._failure("invalid", "relation target candidate identity or pose is invalid")
            seen.add(candidate_ref)
            normalized.append({
                "candidate_ref": candidate_ref,
                "destination_ref": destination_ref,
                "world_T_object_target": [float(value) for value in pose],
                "evidence_refs": list(dict.fromkeys(evidence_refs)),
            })
        if status == "available" and not normalized:
            return self._failure("invalid", "available relation target result has no candidates")
        if status in {"empty", "ambiguous", "stale", "invalid", "unavailable"} and normalized:
            return self._failure("invalid", "non-available relation target result contains candidates")
        return {
            "status": status,
            "candidate_set_ref": set_ref,
            **{key: request[key] for key in identity_keys},
            "candidates": normalized,
            "motion_authorized": False,
            **({"error": str(result["error"])} if result.get("error") else {}),
        }

    @staticmethod
    def _failure(status: str, message: str) -> dict[str, Any]:
        return {
            "status": status,
            "candidate_set_ref": "relation-target-set://unavailable",
            "entity_ref": "entity://unknown",
            "goal_relation": "unknown",
            "relation_target_ref": "surface://unknown",
            "observation_ref": "observation://unknown/unknown",
            "scene_revision": "unknown",
            "frame_id": "unknown",
            "calibration_ref": "artifact://unknown",
            "candidates": [],
            "motion_authorized": False,
            "error": message,
        }


def _valid_rigid_pose(value: Any) -> bool:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 16
        or any(isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)) for item in value)
    ):
        return False
    if not all(
        abs(float(value[12 + index]) - expected) <= 1e-6
        for index, expected in enumerate((0.0, 0.0, 0.0, 1.0))
    ):
        return False
    rotation = [[float(value[row * 4 + column]) for column in range(3)] for row in range(3)]
    for left in range(3):
        for right in range(3):
            dot = sum(rotation[row][left] * rotation[row][right] for row in range(3))
            if abs(dot - (1.0 if left == right else 0.0)) > 1e-3:
                return False
    return True


__all__ = ["RELATION_TARGET_TOOL_SPEC", "RelationTargetProvider", "RelationTargetQueryEndpoint"]
