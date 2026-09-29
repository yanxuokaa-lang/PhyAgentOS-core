"""Provider-neutral ``scene.observe`` endpoint.

The endpoint owns the public observation contract while an injected
``ObservationSource`` owns sensor access.  No environment, simulator, camera
SDK, or actuator dependency is imported here.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .ports import ObservationSource

_OBSERVATION_REF = re.compile(r"^observation://[^/]+/[^/]+$")
_ARTIFACT_REF = re.compile(r"^artifact://[^/]+/.+$")
_KINDS = {"rgb", "depth", "point_cloud", "state"}

TOOL_ID = "scene.observe"
ENDPOINT_ID = "scene_observation"
OPERATION = "observe"

# The public schema is deliberately kept here, next to the endpoint owner.
# Adapter profiles may add private fields to their own payloads, but those
# fields must never become part of the Gateway-facing ToolSpec implicitly.
OBSERVATION_TOOL_SPEC: dict[str, Any] = {
    "tool_id": TOOL_ID,
    "implementation_id": "scene.observation",
    "endpoint_id": ENDPOINT_ID,
    "operation": OPERATION,
    "semantics": "query",
    "planning": {
        "schema_version": "paos-tool-spec-policy/v1",
        "requires_before_plan": True,
    },
    "description": "Return a measured, calibrated scene observation without causing a physical effect.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["max_age_ms"],
        "oneOf": [
            {"required": ["sensor_ref"], "not": {"required": ["sensor_refs"]}},
            {"required": ["sensor_refs"], "not": {"required": ["sensor_ref"]}},
        ],
        "properties": {
            "sensor_ref": {"type": "string", "minLength": 1},
            "sensor_refs": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "minLength": 1},
                "description": "Ordered sensors captured in one synchronized observation set.",
            },
            "requested_frame": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Optional concrete Runtime frame_id to validate against the "
                    "returned frame. Omit for the initial observation; do not use "
                    "abstract labels such as 'sensor' or 'observation'."
                ),
            },
            "max_age_ms": {"type": "integer", "minimum": 1},
            "max_capture_skew_ms": {"type": "integer", "minimum": 0, "default": 50},
        },
    },
    "output_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "status", "observation_ref", "captured_at", "scene_revision", "frame",
            "calibration_ref", "freshness_ms", "artifacts", "views",
            "capture_skew_ms",
        ],
        "properties": {
            "status": {"enum": ["available", "unavailable", "stale", "invalid"]},
            "observation_ref": {"type": "string", "pattern": _OBSERVATION_REF.pattern},
            "captured_at": {"type": "string", "format": "date-time"},
            "scene_revision": {"type": "string", "minLength": 1},
            "frame": {
                "type": "object",
                "additionalProperties": False,
                "required": ["frame_id", "unit"],
                "properties": {
                    "frame_id": {"type": "string", "minLength": 1},
                    "unit": {"const": "m"},
                },
            },
            "calibration_ref": {"type": ["string", "null"]},
            "freshness_ms": {"type": "integer", "minimum": 0},
            "artifacts": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["ref", "kind", "media_type"],
                    "properties": {
                        "ref": {"type": "string", "pattern": _ARTIFACT_REF.pattern},
                        "kind": {"enum": sorted(_KINDS)},
                        "media_type": {"type": "string", "minLength": 1},
                    },
                },
            },
            "views": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "sensor_ref", "observation_ref", "captured_at", "frame",
                        "calibration_ref", "freshness_ms", "artifacts",
                    ],
                    "properties": {
                        "sensor_ref": {"type": "string", "minLength": 1},
                        "observation_ref": {"type": "string", "pattern": _OBSERVATION_REF.pattern},
                        "captured_at": {"type": "string", "format": "date-time"},
                        "frame": {
                            "type": "object", "additionalProperties": False,
                            "required": ["frame_id", "unit"],
                            "properties": {
                                "frame_id": {"type": "string", "minLength": 1},
                                "unit": {"const": "m"},
                            },
                        },
                        "calibration_ref": {"type": "string", "minLength": 1},
                        "freshness_ms": {"type": "integer", "minimum": 0},
                        "artifacts": {
                            "type": "array", "minItems": 1,
                            "items": {
                                "type": "object", "additionalProperties": False,
                                "required": ["ref", "kind", "media_type"],
                                "properties": {
                                    "ref": {"type": "string", "pattern": _ARTIFACT_REF.pattern},
                                    "kind": {"enum": sorted(_KINDS)},
                                    "media_type": {"type": "string", "minLength": 1},
                                },
                            },
                        },
                    },
                },
            },
            "capture_skew_ms": {"type": "integer", "minimum": 0},
            "error": {
                "type": "object",
                "additionalProperties": False,
                "required": ["code", "message"],
                "properties": {
                    "code": {"type": "string", "minLength": 1},
                    "message": {"type": "string", "minLength": 1},
                },
            },
        },
    },
    "robot_frame_profile": {
        "observation_frame": "sensor",
        "frame_id_source": "result.frame.frame_id",
        "requested_frame_semantics": "optional_concrete_runtime_frame_id",
        "initial_observation": "omit_requested_frame",
        "unit": "m",
    },
}


class ObservationContractError(ValueError):
    """Raised when a scene observation violates the public contract."""


class ObservationEndpoint:
    """Validate and project one provider observation without physical effects."""

    def __init__(self, source: ObservationSource, *, now: Callable[[], datetime] | None = None) -> None:
        if source is None or not callable(getattr(source, "capture", None)):
            raise ObservationContractError("ObservationSource must expose capture(request)")
        self.source = source
        self._now = now or (lambda: datetime.now(timezone.utc))

    def invoke(self, arguments: Any) -> dict[str, Any]:
        allowed = {
            "sensor_ref", "sensor_refs", "requested_frame", "max_age_ms",
            "max_capture_skew_ms",
        }
        if not isinstance(arguments, dict) or set(arguments) - allowed:
            return self._error("invalid_arguments", "scene.observe arguments must be an object")
        sensor_ref = arguments.get("sensor_ref")
        sensor_refs = arguments.get("sensor_refs")
        max_age_ms = arguments.get("max_age_ms")
        max_capture_skew_ms = arguments.get("max_capture_skew_ms", 50)
        requested_frame = arguments.get("requested_frame")
        if (sensor_ref is None) == (sensor_refs is None):
            return self._error("invalid_sensor_ref", "provide exactly one of sensor_ref or sensor_refs")
        if sensor_ref is not None and (not isinstance(sensor_ref, str) or not sensor_ref.strip()):
            return self._error("invalid_sensor_ref", "sensor_ref must be a non-empty string")
        if sensor_refs is not None and (
            not isinstance(sensor_refs, list) or not sensor_refs
            or any(not isinstance(item, str) or not item.strip() for item in sensor_refs)
            or len(set(sensor_refs)) != len(sensor_refs)
        ):
            return self._error("invalid_sensor_ref", "sensor_refs must contain distinct non-empty strings")
        ordered_sensor_refs = [sensor_ref] if sensor_ref is not None else list(sensor_refs)
        if isinstance(max_age_ms, bool) or not isinstance(max_age_ms, int) or max_age_ms < 1:
            return self._error("invalid_max_age", "max_age_ms must be a positive integer")
        if (
            isinstance(max_capture_skew_ms, bool)
            or not isinstance(max_capture_skew_ms, int)
            or max_capture_skew_ms < 0
        ):
            return self._error("invalid_capture_skew", "max_capture_skew_ms must be a non-negative integer")
        if requested_frame is not None and (not isinstance(requested_frame, str) or not requested_frame.strip()):
            return self._error("invalid_frame", "requested_frame must be a non-empty string")
        if requested_frame is not None and len(ordered_sensor_refs) != 1:
            return self._error("invalid_frame", "requested_frame is only valid for a single sensor_ref")
        try:
            raw = self.source.capture(dict(arguments))
        except Exception:
            # Provider failures are an unavailable observation, not a transport
            # exception and never a fabricated success.  Keep the cause private
            # so adapter/runtime internals cannot leak through the public API.
            return self._error("sensor_unavailable", "observation source failed")
        if raw is None:
            return self._error("sensor_unavailable", "requested sensor is unavailable")
        try:
            result = self._normalize(raw, ordered_sensor_refs)
        except ObservationContractError as exc:
            return self._error(str(exc), "observation failed contract validation")
        if requested_frame is not None and requested_frame != result["frame"]["frame_id"]:
            return self._error(
                "invalid_frame",
                "requested_frame must match the concrete Runtime frame_id returned "
                "for sensor_ref; omit it for the initial observation",
            )
        now = self._now()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ObservationContractError("observation clock must be timezone-aware")
        for view in result["views"]:
            view_time = datetime.fromisoformat(view["captured_at"].replace("Z", "+00:00"))
            view["freshness_ms"] = max(0, int((now - view_time).total_seconds() * 1000))
        result["freshness_ms"] = max(view["freshness_ms"] for view in result["views"])
        if result["capture_skew_ms"] > max_capture_skew_ms:
            return self._error("capture_skew_exceeded", "observation set exceeds max_capture_skew_ms")
        result["status"] = "stale" if result["freshness_ms"] > max_age_ms else "available"
        if result["status"] == "stale":
            result["error"] = {"code": "stale_observation", "message": "observation exceeds max_age_ms"}
        return result

    @staticmethod
    def _normalize(raw: Mapping[str, Any], sensor_refs: list[str]) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise ObservationContractError("invalid_observation")
        if raw.get("sensor_available", True) is not True:
            raise ObservationContractError("sensor_unavailable")
        raw_views = raw.get("views")
        if raw_views is None:
            raw_views = [{**dict(raw), "sensor_ref": sensor_refs[0]}]
        if not isinstance(raw_views, (list, tuple)) or len(raw_views) != len(sensor_refs):
            raise ObservationContractError("invalid_views")
        views = [ObservationEndpoint._normalize_view(item, expected) for item, expected in zip(raw_views, sensor_refs, strict=True)]
        scene_revisions = {item["scene_revision"] for item in views}
        if len(scene_revisions) != 1:
            raise ObservationContractError("mixed_scene_revision")
        timestamps = [datetime.fromisoformat(item["captured_at"].replace("Z", "+00:00")) for item in views]
        capture_skew_ms = int((max(timestamps) - min(timestamps)).total_seconds() * 1000)
        primary = views[0]
        artifacts = [artifact for view in views for artifact in view["artifacts"]]
        if len({item["ref"] for item in artifacts}) != len(artifacts):
            raise ObservationContractError("invalid_artifact")
        return {
            "status": "available",
            "observation_ref": primary["observation_ref"],
            "captured_at": min(timestamps).astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "scene_revision": primary["scene_revision"],
            "frame": primary["frame"],
            "calibration_ref": primary["calibration_ref"],
            "freshness_ms": 0,
            "artifacts": artifacts,
            "views": [{key: value for key, value in view.items() if key != "scene_revision"} for view in views],
            "capture_skew_ms": capture_skew_ms,
        }

    @staticmethod
    def _normalize_view(raw: Mapping[str, Any], sensor_ref: str) -> dict[str, Any]:
        if not isinstance(raw, Mapping) or raw.get("sensor_available", True) is not True:
            raise ObservationContractError("sensor_unavailable")
        if raw.get("sensor_ref", sensor_ref) != sensor_ref:
            raise ObservationContractError("invalid_sensor_ref")
        captured_at = raw.get("captured_at")
        if isinstance(captured_at, str):
            try:
                captured_at = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ObservationContractError("invalid_timestamp") from exc
        if not isinstance(captured_at, datetime) or captured_at.tzinfo is None:
            raise ObservationContractError("invalid_timestamp")
        scene_revision = raw.get("scene_revision")
        frame_id = raw.get("frame_id")
        calibration_ref = raw.get("calibration_ref")
        if not isinstance(scene_revision, str) or not scene_revision.strip():
            raise ObservationContractError("missing_scene_revision")
        if not isinstance(frame_id, str) or not frame_id.strip():
            raise ObservationContractError("missing_frame")
        if not isinstance(calibration_ref, str) or not calibration_ref.strip():
            raise ObservationContractError("missing_calibration")
        artifacts = raw.get("artifacts")
        if not isinstance(artifacts, (list, tuple)) or not artifacts:
            raise ObservationContractError("missing_artifacts")
        normalized: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in artifacts:
            if not isinstance(item, Mapping):
                raise ObservationContractError("invalid_artifact")
            ref, kind, media_type = item.get("ref"), item.get("kind"), item.get("media_type")
            if (
                not isinstance(ref, str) or _ARTIFACT_REF.fullmatch(ref) is None
                or ref in seen or not isinstance(kind, str) or kind not in _KINDS
                or not isinstance(media_type, str) or not media_type.strip()
            ):
                raise ObservationContractError("invalid_artifact")
            seen.add(ref)
            normalized.append({"ref": ref, "kind": kind, "media_type": media_type})
        observation_ref = raw.get("observation_ref") or f"observation://{scene_revision}/{frame_id}"
        if not isinstance(observation_ref, str) or _OBSERVATION_REF.fullmatch(observation_ref) is None:
            raise ObservationContractError("invalid_observation_ref")
        if observation_ref != f"observation://{scene_revision}/{frame_id}":
            raise ObservationContractError("invalid_observation_binding")
        return {
            "sensor_ref": sensor_ref,
            "observation_ref": observation_ref,
            "captured_at": captured_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "scene_revision": scene_revision,
            "frame": {"frame_id": frame_id, "unit": "m"},
            "calibration_ref": calibration_ref,
            "freshness_ms": 0,
            "artifacts": normalized,
        }

    def _error(self, code: str, message: str) -> dict[str, Any]:
        now = self._now()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ObservationContractError("observation clock must be timezone-aware")
        return {
            "status": "invalid" if code.startswith("invalid") else "unavailable",
            "observation_ref": "observation://unknown/unknown",
            "captured_at": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "scene_revision": "unknown",
            "frame": {"frame_id": "unknown", "unit": "m"},
            "calibration_ref": None,
            "freshness_ms": 0,
            "artifacts": [],
            "views": [],
            "capture_skew_ms": 0,
            "error": {"code": code, "message": message},
        }


__all__ = [
    "ENDPOINT_ID",
    "OBSERVATION_TOOL_SPEC",
    "OPERATION",
    "TOOL_ID",
    "ObservationContractError",
    "ObservationEndpoint",
]
