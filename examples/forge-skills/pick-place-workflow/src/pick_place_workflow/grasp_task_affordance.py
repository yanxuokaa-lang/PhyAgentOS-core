"""Provider-neutral task-aware grasp/process-feature candidate contract."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Mapping, Protocol


class GraspTaskAffordanceProvider(Protocol):
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None: ...

    def validate_selection(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None: ...


GRASP_TASK_AFFORDANCE_TOOL_SPEC = {
    "tool_id": "manipulation.grasp_task_affordances",
    "endpoint_id": "grasp_task_affordances",
    "operation": "propose",
    "semantics": "query",
    "description": "Propose task-qualified grasp/process-feature combinations without selecting one or authorizing motion.",
    "planning": {
        "schema_version": "paos-tool-spec-policy/v1",
        "capabilities": ["manipulation.grasp_task_affordances"],
        "input_binding_keys": ["operation", "entity_refs", "observation_ref", "scene_revision", "frame_id", "calibration_ref"],
        "argument_source_requirements": [
            {"when": {"operation": "pour"},
             "keys": ["process_feature_candidate_set_ref", "selected_process_feature_refs"],
             "source_tool_id": "manipulation.prepare_process_features",
             "source_paths": {"process_feature_candidate_set_ref": ["response", "data", "candidate_set_ref"],
                              "selected_process_feature_refs": ["response", "data", "selected_feature_refs"]}},
            {"when": {"operation": "stir"},
             "keys": ["process_feature_candidate_set_ref", "selected_process_feature_refs"],
             "source_tool_id": "manipulation.prepare_process_features",
             "source_paths": {"process_feature_candidate_set_ref": ["response", "data", "candidate_set_ref"],
                              "selected_process_feature_refs": ["response", "data", "selected_feature_refs"]}},
        ],
        "scene_write_behavior": "none",
    },
    "input_schema": {
        "type": "object", "additionalProperties": False,
        "required": ["operation", "entity_refs", "grasp_candidate_set_ref", "process_feature_candidate_set_ref", "selected_process_feature_refs", "observation_ref", "scene_revision", "frame_id", "calibration_ref", "freshness_ms", "max_age_ms"],
        "properties": {
            "operation": {"enum": ["pour", "stir"]},
            "entity_refs": {"type": "array", "minItems": 2, "uniqueItems": True,
                            "items": {"type": "string", "pattern": "^entity://[^/]+$"}},
            "grasp_candidate_set_ref": {"type": "string", "pattern": "^candidate-set://\\S+$"},
            "process_feature_candidate_set_ref": {"type": "string", "pattern": "^process-feature-set://\\S+$"},
            "selected_process_feature_refs": {"type": "array", "minItems": 2, "uniqueItems": True,
                "items": {"type": "string", "pattern": "^process-feature://\\S+$"}},
            "observation_ref": {"type": "string", "pattern": "^observation://[^/]+/[^/]+$"},
            "scene_revision": {"type": "string", "minLength": 1},
            "frame_id": {"type": "string", "minLength": 1},
            "calibration_ref": {"type": "string", "pattern": "^artifact://\\S+$"},
            "freshness_ms": {"type": "integer", "minimum": 0},
            "max_age_ms": {"type": "integer", "minimum": 1},
        },
    },
    "output_schema": {
        "type": "object", "additionalProperties": False,
        "required": ["status", "candidate_set_ref", "process_feature_candidate_set_ref", "grasp_candidate_set_ref", "observation_ref", "scene_revision", "frame_id", "calibration_ref", "candidates", "motion_authorized"],
        "properties": {
            "status": {"enum": ["available", "empty", "unavailable", "stale", "invalid", "ambiguous"]},
            "candidate_set_ref": {"type": "string", "pattern": "^grasp-affordance-set://\\S+$"},
            "process_feature_candidate_set_ref": {"type": "string", "pattern": "^process-feature-set://\\S+$"},
            "grasp_candidate_set_ref": {"type": "string", "pattern": "^candidate-set://\\S+$"},
            "observation_ref": {"type": "string", "pattern": "^observation://[^/]+/[^/]+$"},
            "scene_revision": {"type": "string", "minLength": 1},
            "frame_id": {"type": "string", "minLength": 1},
            "calibration_ref": {"type": "string", "pattern": "^artifact://\\S+$"},
            "candidates": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                "required": ["combination_ref", "entity_ref", "grasp_candidate_ref", "process_feature_refs"],
                "properties": {
                    "combination_ref": {"type": "string", "pattern": "^grasp-affordance://\\S+$"},
                    "entity_ref": {"type": "string", "pattern": "^entity://[^/]+$"},
                    "grasp_candidate_ref": {"type": "string", "pattern": "^candidate://\\S+$"},
                    "process_feature_refs": {"type": "array", "minItems": 1, "uniqueItems": True,
                        "items": {"type": "string", "pattern": "^process-feature://\\S+$"}},
                }}},
            "motion_authorized": {"const": False},
            "error": {"type": "string"},
        },
    },
}

GRASP_TASK_AFFORDANCE_PREPARATION_TOOL_SPEC = {
    "tool_id": "manipulation.prepare_grasp_task_affordance",
    "endpoint_id": "prepare_grasp_task_affordance",
    "operation": "validate_selection",
    "semantics": "query",
    "description": "Revalidate one selected task-qualified grasp combination against current evidence without motion.",
    "planning": {
        "schema_version": "paos-tool-spec-policy/v1",
        "capabilities": ["manipulation.prepare_grasp_task_affordance"],
        "input_binding_keys": ["operation", "entity_refs", "candidate_set_ref", "selected_combination_ref", "observation_ref", "scene_revision", "frame_id", "calibration_ref"],
        "argument_source_requirements": [
            {"when": {"operation": "pour"},
             "keys": ["candidate_set_ref", "selected_combination_ref", "process_feature_candidate_set_ref"],
             "source_tool_id": "manipulation.grasp_task_affordances",
             "source_paths": {"candidate_set_ref": ["response", "data", "candidate_set_ref"],
                              "process_feature_candidate_set_ref": ["response", "data", "process_feature_candidate_set_ref"]}},
            {"when": {"operation": "stir"},
             "keys": ["candidate_set_ref", "selected_combination_ref", "process_feature_candidate_set_ref"],
             "source_tool_id": "manipulation.grasp_task_affordances",
             "source_paths": {"candidate_set_ref": ["response", "data", "candidate_set_ref"],
                              "process_feature_candidate_set_ref": ["response", "data", "process_feature_candidate_set_ref"]}},
        ],
        "scene_write_behavior": "none",
    },
    "input_schema": {
        "type": "object", "additionalProperties": False,
        "required": ["operation", "entity_refs", "candidate_set_ref", "selected_combination_ref", "process_feature_candidate_set_ref", "observation_ref", "scene_revision", "frame_id", "calibration_ref", "freshness_ms", "max_age_ms"],
        "properties": {
            "operation": {"enum": ["pour", "stir"]},
            "entity_refs": GRASP_TASK_AFFORDANCE_TOOL_SPEC["input_schema"]["properties"]["entity_refs"],
            "candidate_set_ref": {"type": "string", "pattern": "^grasp-affordance-set://\\S+$"},
            "selected_combination_ref": {"type": "string", "pattern": "^grasp-affordance://\\S+$"},
            "process_feature_candidate_set_ref": GRASP_TASK_AFFORDANCE_TOOL_SPEC["output_schema"]["properties"]["process_feature_candidate_set_ref"],
            **{key: GRASP_TASK_AFFORDANCE_TOOL_SPEC["input_schema"]["properties"][key] for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref", "freshness_ms", "max_age_ms")},
        },
    },
}

_COMBINATION_REF = re.compile(r"^grasp-affordance://\S+$")
_SET_REF = re.compile(r"^grasp-affordance-set://\S+$")


class GraspTaskAffordanceQueryEndpoint:
    def __init__(self, provider: GraspTaskAffordanceProvider):
        self.provider = provider

    def invoke(self, arguments: Any) -> dict[str, Any]:
        from jsonschema import Draft202012Validator

        if list(Draft202012Validator(GRASP_TASK_AFFORDANCE_TOOL_SPEC["input_schema"]).iter_errors(arguments)):
            return self._failure("invalid", "grasp affordance Query arguments are invalid")
        request = deepcopy(dict(arguments))
        if request["observation_ref"] != f"observation://{request['scene_revision']}/{request['frame_id']}":
            return self._failure("invalid", "observation identity differs from scene/frame")
        if request["freshness_ms"] > request["max_age_ms"]:
            return self._failure("stale", "grasp affordance observation exceeds max_age_ms")
        try:
            result = self.provider.propose(request)
        except Exception:
            return self._failure("unavailable", "grasp affordance provider failed")
        if not isinstance(result, Mapping):
            return self._failure("unavailable", "grasp affordance provider is unavailable")
        identity_keys = ("candidate_set_ref", "process_feature_candidate_set_ref", "grasp_candidate_set_ref",
                         "observation_ref", "scene_revision", "frame_id", "calibration_ref")
        if any(result.get(key) != request.get(key) for key in identity_keys[1:]):
            return self._failure("stale", "grasp affordance evidence does not match current Query")
        set_ref, candidates = result.get("candidate_set_ref"), result.get("candidates")
        if not isinstance(set_ref, str) or _SET_REF.fullmatch(set_ref) is None or not isinstance(candidates, (list, tuple)):
            return self._failure("invalid", "grasp affordance provider returned invalid candidates")
        seen = set()
        normalized = []
        for item in candidates:
            if not isinstance(item, Mapping):
                return self._failure("invalid", "grasp affordance candidate is invalid")
            ref, entity, grasp, features = (item.get(key) for key in ("combination_ref", "entity_ref", "grasp_candidate_ref", "process_feature_refs"))
            if (not isinstance(ref, str) or _COMBINATION_REF.fullmatch(ref) is None or ref in seen
                    or entity not in request["entity_refs"] or not isinstance(grasp, str)
                    or not grasp.startswith("candidate://") or not isinstance(features, (list, tuple))
                    or not features or any(not isinstance(value, str) or not value.startswith("process-feature://") for value in features)):
                return self._failure("invalid", "grasp affordance candidate identity is invalid")
            seen.add(ref)
            normalized.append({"combination_ref": ref, "entity_ref": entity,
                               "grasp_candidate_ref": grasp, "process_feature_refs": list(features)})
        status = result.get("status", "available" if normalized else "empty")
        if status not in {"available", "empty", "ambiguous", "stale", "invalid", "unavailable"}:
            status = "unavailable"
        identity = {"candidate_set_ref": set_ref, **{key: request.get(key, result.get(key, "unknown")) for key in identity_keys[1:]}}
        return {"status": status, **identity, "candidates": normalized,
                "motion_authorized": False,
                **({"error": str(result["error"])} if result.get("error") else {})}

    @staticmethod
    def _failure(status: str, message: str) -> dict[str, Any]:
        return {"status": status, "candidate_set_ref": "grasp-affordance-set://unavailable",
                "process_feature_candidate_set_ref": "process-feature-set://unavailable",
                "grasp_candidate_set_ref": "candidate-set://unavailable",
                "observation_ref": "observation://unknown/unknown", "scene_revision": "unknown",
                "frame_id": "unknown", "calibration_ref": "artifact://unknown", "candidates": [],
                "motion_authorized": False, "error": message}


class GraspTaskAffordancePreparationEndpoint:
    def __init__(self, provider: GraspTaskAffordanceProvider):
        self.provider = provider

    def invoke(self, arguments: Any) -> dict[str, Any]:
        from jsonschema import Draft202012Validator

        if list(Draft202012Validator(GRASP_TASK_AFFORDANCE_PREPARATION_TOOL_SPEC["input_schema"]).iter_errors(arguments)):
            return {"status": "invalid", "motion_authorized": False, "error": "grasp affordance Preparation arguments are invalid"}
        request = deepcopy(dict(arguments))
        identity = {key: request.get(key, "unknown") for key in ("candidate_set_ref", "selected_combination_ref", "process_feature_candidate_set_ref", "observation_ref", "scene_revision", "frame_id", "calibration_ref")}
        if request["observation_ref"] != f"observation://{request['scene_revision']}/{request['frame_id']}":
            return {"status": "stale", **identity, "motion_authorized": False, "error": "observation identity differs from scene/frame"}
        if request["freshness_ms"] > request["max_age_ms"]:
            return {"status": "stale", **identity, "motion_authorized": False, "error": "grasp affordance evidence is stale"}
        validate = getattr(self.provider, "validate_selection", None)
        if not callable(validate):
            return {"status": "unavailable", **identity, "motion_authorized": False, "error": "provider cannot revalidate selected grasp affordance"}
        try:
            result = validate(request)
        except Exception:
            result = None
        if not isinstance(result, Mapping):
            return {"status": "unavailable", **identity, "motion_authorized": False, "error": "grasp affordance Preparation provider failed"}
        if any(result.get(key) != request.get(key) for key in identity):
            return {"status": "stale", **identity, "motion_authorized": False, "error": "selected combination differs from current Query"}
        status = result.get("status")
        if status not in {"available", "ambiguous", "stale", "invalid", "unavailable"}:
            status = "unavailable"
        selected = result.get("selected")
        if status == "available":
            if not isinstance(selected, Mapping):
                return {"status": "invalid", **identity, "motion_authorized": False,
                        "error": "provider omitted selected combination projection"}
            if (selected.get("combination_ref") != request["selected_combination_ref"]
                    or not isinstance(selected.get("grasp_candidate_ref"), str)
                    or not selected["grasp_candidate_ref"].startswith("candidate://")
                    or not isinstance(selected.get("process_feature_refs"), (list, tuple))
                    or not selected["process_feature_refs"]):
                return {"status": "invalid", **identity, "motion_authorized": False,
                        "error": "provider returned invalid selected combination"}
        return {"status": status, **identity,
                **({"selected": {"combination_ref": selected["combination_ref"],
                                  "grasp_candidate_ref": selected["grasp_candidate_ref"],
                                  "process_feature_refs": list(selected["process_feature_refs"])}}
                   if status == "available" else {}),
                "motion_authorized": False,
                **({"error": str(result["error"])} if result.get("error") else {})}


__all__ = ["GRASP_TASK_AFFORDANCE_TOOL_SPEC", "GRASP_TASK_AFFORDANCE_PREPARATION_TOOL_SPEC",
           "GraspTaskAffordanceProvider", "GraspTaskAffordanceQueryEndpoint",
           "GraspTaskAffordancePreparationEndpoint"]
