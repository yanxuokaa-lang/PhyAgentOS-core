"""Provider-neutral, no-motion process-feature candidate Query."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Mapping, Protocol


class ProcessFeatureProvider(Protocol):
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None: ...


PROCESS_FEATURE_TOOL_SPEC = {
    "tool_id": "manipulation.process_features",
    "endpoint_id": "process_features",
    "operation": "propose",
    "semantics": "query",
    "description": "Propose current-scene process-feature candidates without selecting one or authorizing motion.",
    "planning": {
        "schema_version": "paos-tool-spec-policy/v1",
        "capabilities": ["manipulation.process_features"],
        "input_binding_keys": ["operation", "entity_refs", "observation_ref", "scene_revision", "frame_id", "calibration_ref"],
        "scene_write_behavior": "none",
    },
    "input_schema": {
        "type": "object", "additionalProperties": False,
        "required": ["operation", "entity_refs", "observation_ref", "scene_revision", "frame_id",
                     "calibration_ref", "freshness_ms", "max_age_ms"],
        "properties": {
            "operation": {"enum": ["pour", "stir"]},
            "entity_refs": {"type": "array", "minItems": 2, "uniqueItems": True,
                            "items": {"type": "string", "pattern": "^entity://[^/]+$"}},
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
        "required": ["status", "candidate_set_ref", "observation_ref", "scene_revision", "frame_id",
                     "calibration_ref", "candidates", "motion_authorized"],
        "properties": {
            "status": {"enum": ["available", "empty", "unavailable", "stale", "invalid"]},
            "candidate_set_ref": {"type": "string", "pattern": "^process-feature-set://\\S+$"},
            "observation_ref": {"type": "string", "pattern": "^observation://[^/]+/[^/]+$"},
            "scene_revision": {"type": "string", "minLength": 1},
            "frame_id": {"type": "string", "minLength": 1},
            "calibration_ref": {"type": "string", "pattern": "^artifact://\\S+$"},
            "candidates": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                "required": ["feature_ref", "entity_ref", "feature_kind", "feature_role"],
                "properties": {
                    "feature_ref": {"type": "string", "pattern": "^process-feature://\\S+$"},
                    "entity_ref": {"type": "string", "pattern": "^entity://[^/]+$"},
                    "feature_kind": {"type": "string", "minLength": 1},
                    "feature_role": {"type": "string", "minLength": 1},
                }}},
            "motion_authorized": {"const": False},
            "error": {"type": "string"},
        },
    },
}

_REF = re.compile(r"^process-feature://\S+$")


class ProcessFeatureQueryEndpoint:
    """Validate provider output and bind it to the exact current Query request."""

    def __init__(self, provider: ProcessFeatureProvider):
        self.provider = provider

    def invoke(self, arguments: Any) -> dict[str, Any]:
        from jsonschema import Draft202012Validator

        errors = list(Draft202012Validator(PROCESS_FEATURE_TOOL_SPEC["input_schema"]).iter_errors(arguments))
        if errors:
            return self._failure("invalid", "process feature Query arguments are invalid")
        request = deepcopy(dict(arguments))
        if request["observation_ref"] != f"observation://{request['scene_revision']}/{request['frame_id']}":
            return self._failure("invalid", "observation identity differs from scene/frame")
        if request["freshness_ms"] > request["max_age_ms"]:
            return self._failure("stale", "process feature observation exceeds max_age_ms")
        try:
            result = self.provider.propose(request)
        except Exception:
            return self._failure("unavailable", "process feature provider failed")
        if not isinstance(result, Mapping):
            return self._failure("unavailable", "process feature provider is unavailable")
        if any(result.get(key) != request[key] for key in (
            "observation_ref", "scene_revision", "frame_id", "calibration_ref"
        )):
            return self._failure("stale", "process feature evidence does not match the current Query")
        candidate_set_ref = result.get("candidate_set_ref")
        candidates = result.get("candidates")
        if not isinstance(candidate_set_ref, str) or not candidate_set_ref.startswith("process-feature-set://"):
            return self._failure("invalid", "process feature provider returned an invalid candidate set")
        if not isinstance(candidates, (list, tuple)):
            return self._failure("invalid", "process feature provider returned invalid candidates")
        seen: set[str] = set()
        normalized = []
        allowed_entities = set(request["entity_refs"])
        for item in candidates:
            if not isinstance(item, Mapping):
                return self._failure("invalid", "process feature candidate is not an object")
            ref, entity, kind, role = (item.get(key) for key in ("feature_ref", "entity_ref", "feature_kind", "feature_role"))
            if (not isinstance(ref, str) or _REF.fullmatch(ref) is None or ref in seen
                    or entity not in allowed_entities or not isinstance(kind, str) or not kind.strip()
                    or not isinstance(role, str) or not role.strip()):
                return self._failure("invalid", "process feature candidates failed identity validation")
            seen.add(ref)
            normalized.append({"feature_ref": ref, "entity_ref": entity,
                               "feature_kind": kind, "feature_role": role})
        return {
            "status": "available" if normalized else "empty",
            "candidate_set_ref": candidate_set_ref,
            **{key: request[key] for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref")},
            "candidates": normalized,
            "motion_authorized": False,
        }

    @staticmethod
    def _failure(status: str, message: str) -> dict[str, Any]:
        return {"status": status, "candidate_set_ref": "process-feature-set://unavailable",
                "observation_ref": "observation://unknown/unknown", "scene_revision": "unknown",
                "frame_id": "unknown", "calibration_ref": "artifact://unknown",
                "candidates": [], "motion_authorized": False, "error": message}


PROCESS_FEATURE_PREPARATION_TOOL_SPEC = {
    "tool_id": "manipulation.prepare_process_features",
    "endpoint_id": "process_feature_preparation",
    "operation": "validate_selection",
    "semantics": "query",
    "description": "Validate selected process-feature references and evidence lineage without motion.",
    "planning": {
        "schema_version": "paos-tool-spec-policy/v1",
        "capabilities": ["manipulation.prepare_process_features"],
        "input_binding_keys": ["operation", "entity_refs", "observation_ref", "scene_revision", "frame_id", "calibration_ref"],
        # The Agent selects opaque refs from the Query result. Preparation's
        # provider validates both refs against the current candidate set, so a
        # literal source slot would incorrectly reject a valid selection.
        "argument_source_requirements": [],
        "scene_write_behavior": "none",
    },
    "input_schema": {
        "type": "object", "additionalProperties": False,
        "required": ["operation", "entity_refs", "candidate_set_ref", "selected_feature_refs",
                     "observation_ref", "scene_revision", "frame_id", "calibration_ref",
                     "freshness_ms", "max_age_ms"],
        "properties": {
            "operation": {"enum": ["pour", "stir"]},
            "entity_refs": {"type": "array", "minItems": 2, "uniqueItems": True,
                            "items": {"type": "string", "pattern": "^entity://[^/]+$"}},
            "candidate_set_ref": {"type": "string", "pattern": "^process-feature-set://\\S+$"},
            "selected_feature_refs": {"type": "array", "minItems": 2, "uniqueItems": True,
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
        "required": ["status", "candidate_set_ref", "selected_feature_refs", "observation_ref",
                     "scene_revision", "frame_id", "calibration_ref", "motion_authorized"],
        "properties": {
            "status": {"enum": ["available", "ambiguous", "stale", "invalid", "unavailable"]},
            "candidate_set_ref": {"type": "string", "pattern": "^process-feature-set://\\S+$"},
            "selected_feature_refs": {"type": "array", "items": {"type": "string", "pattern": "^process-feature://\\S+$"}},
            "observation_ref": {"type": "string", "pattern": "^observation://[^/]+/[^/]+$"},
            "scene_revision": {"type": "string", "minLength": 1},
            "frame_id": {"type": "string", "minLength": 1},
            "calibration_ref": {"type": "string", "pattern": "^artifact://\\S+$"},
            "motion_authorized": {"const": False},
            "error": {"type": "string"},
        },
    },
}


class ProcessFeaturePreparationEndpoint:
    """Validate a planner-selected candidate set before composite Action admission."""

    def __init__(self, provider: ProcessFeatureProvider):
        self.provider = provider

    def invoke(self, arguments: Any) -> dict[str, Any]:
        from jsonschema import Draft202012Validator

        errors = list(Draft202012Validator(PROCESS_FEATURE_PREPARATION_TOOL_SPEC["input_schema"]).iter_errors(arguments))
        if errors:
            return self._failure("invalid", "process feature preparation arguments are invalid")
        request = deepcopy(dict(arguments))
        identity = {key: request[key] for key in (
            "candidate_set_ref", "selected_feature_refs", "observation_ref", "scene_revision", "frame_id", "calibration_ref"
        )}
        if request["observation_ref"] != f"observation://{request['scene_revision']}/{request['frame_id']}":
            return self._failure("stale", "observation identity differs from scene/frame", identity)
        if request["freshness_ms"] > request["max_age_ms"]:
            return self._failure("stale", "process feature observation exceeds max_age_ms", identity)
        validate = getattr(self.provider, "validate_selection", None)
        if not callable(validate):
            return self._failure("unavailable", "provider cannot validate selected process features", identity)
        try:
            result = validate(request)
        except Exception:
            return self._failure("unavailable", "process feature preparation provider failed", identity)
        if not isinstance(result, Mapping):
            return self._failure("unavailable", "process feature preparation provider is unavailable", identity)
        status = result.get("status")
        if status not in {"available", "ambiguous", "stale", "invalid", "unavailable"}:
            status = "unavailable"
        if any(result.get(key) != request[key] for key in identity):
            return self._failure("stale", "selected feature evidence does not match the Query", identity)
        if status != "available":
            return {"status": status, **identity, "motion_authorized": False,
                    "error": str(result.get("error", "selected process features are not qualified"))}
        return {"status": "available", **identity, "selected_feature_refs": list(request["selected_feature_refs"]),
                "motion_authorized": False}

    @staticmethod
    def _failure(status: str, message: str, identity: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return {"status": status, **(dict(identity) if identity else {}),
                "motion_authorized": False, "error": message}


__all__ = ["PROCESS_FEATURE_TOOL_SPEC", "PROCESS_FEATURE_PREPARATION_TOOL_SPEC",
           "ProcessFeatureProvider", "ProcessFeatureQueryEndpoint", "ProcessFeaturePreparationEndpoint"]
