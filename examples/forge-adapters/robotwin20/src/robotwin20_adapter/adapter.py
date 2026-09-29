"""Clean-room RoboTwin20 adapter seam for sensor-backed observations.

The adapter does not import RoboTwin or SAPIEN.  A deployment-owned backend is
injected and must expose camera/depth/state sensor captures.  Simulator actor
lists, segmentation truth, internal poses, and task success are intentionally
outside this interface and can never populate the public observation result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol


class AdapterConfigurationError(ValueError):
    """The adapter profile or backend does not satisfy the public seam."""


class AdapterSensorError(RuntimeError):
    """A sensor capture is unavailable or fails the observation contract."""


@dataclass(frozen=True)
class SensorArtifact:
    ref: str
    kind: str
    media_type: str


@dataclass(frozen=True)
class SensorCapture:
    captured_at: datetime
    scene_revision: str
    frame_id: str
    calibration_ref: str | None
    artifacts: tuple[SensorArtifact, ...]
    sensor_available: bool = True


class RoboTwinSensorBackend(Protocol):
    """Minimal injected seam implemented by the RoboTwin runtime workspace."""

    def reset(self, *, seed: int | None = None) -> None: ...

    def capture_sensors(self, sensor_ref: str) -> SensorCapture | Mapping[str, Any] | None: ...

    def capture_sensor_set(self, sensor_refs: list[str]) -> list[SensorCapture | Mapping[str, Any]]: ...

    def snapshot(self) -> Mapping[str, Any]: ...


_ARTIFACT_REF = re.compile(r"^artifact://[^/]+/.+$")
_KINDS = {"rgb", "depth", "state", "point_cloud"}
_REQUIRED_SENSOR_KINDS = {"rgb", "depth", "state"}


class RoboTwin20Adapter:
    """Environment lifecycle and sensor capture boundary for a RoboTwin20 profile."""

    def __init__(
        self,
        backend: RoboTwinSensorBackend,
        *,
        profile: Mapping[str, Any],
        required_sensor_kinds: frozenset[str] = frozenset(_REQUIRED_SENSOR_KINDS),
    ) -> None:
        if backend is None:
            raise AdapterConfigurationError("RoboTwin20 backend is required")
        if not isinstance(profile, Mapping) or not profile.get("name"):
            raise AdapterConfigurationError("RoboTwin20 profile requires a non-empty name")
        if not required_sensor_kinds or not required_sensor_kinds <= _KINDS:
            raise AdapterConfigurationError("required_sensor_kinds contains unsupported values")
        self.backend = backend
        self.profile = dict(profile)
        self.required_sensor_kinds = frozenset(required_sensor_kinds)
        self._started = False

    def reset(self, *, seed: int | None = None) -> None:
        reset = getattr(self.backend, "reset", None)
        if not callable(reset):
            raise AdapterConfigurationError("RoboTwin20 backend must expose reset(seed=...)")
        reset(seed=seed)
        self._started = True

    def snapshot(self) -> dict[str, Any]:
        """Return adapter identity only; never expose simulator object truth."""
        if not self._started:
            raise AdapterSensorError("RoboTwin20 environment has not been reset")
        raw = self.backend.snapshot()
        if not isinstance(raw, Mapping):
            raise AdapterSensorError("RoboTwin20 backend snapshot must be an object")
        scene_revision = raw.get("scene_revision")
        if not isinstance(scene_revision, str) or not scene_revision.strip():
            raise AdapterSensorError("RoboTwin20 backend snapshot lacks scene_revision")
        return {
            "profile": self.profile["name"],
            "scene_revision": scene_revision,
            "status": "ready",
        }

    def capture(self, sensor_ref: str) -> SensorCapture:
        if not self._started:
            raise AdapterSensorError("RoboTwin20 environment has not been reset")
        if not isinstance(sensor_ref, str) or not sensor_ref.strip():
            raise AdapterSensorError("sensor_ref must be a non-empty string")
        capture_sensors = getattr(self.backend, "capture_sensors", None)
        if not callable(capture_sensors):
            raise AdapterConfigurationError(
                "RoboTwin20 backend must expose capture_sensors(sensor_ref)"
            )
        raw = capture_sensors(sensor_ref)
        if raw is None:
            raise AdapterSensorError("requested RoboTwin20 sensor is unavailable")
        capture = _normalize_capture(raw)
        _validate_capture(capture, self.required_sensor_kinds)
        return capture

    def capture_many(self, sensor_refs: list[str]) -> tuple[SensorCapture, ...]:
        if not self._started:
            raise AdapterSensorError("RoboTwin20 environment has not been reset")
        if (
            not isinstance(sensor_refs, list) or not sensor_refs
            or any(not isinstance(item, str) or not item.strip() for item in sensor_refs)
            or len(set(sensor_refs)) != len(sensor_refs)
        ):
            raise AdapterSensorError("sensor_refs must contain distinct non-empty strings")
        capture_set = getattr(self.backend, "capture_sensor_set", None)
        if not callable(capture_set):
            raise AdapterConfigurationError(
                "RoboTwin20 backend must expose capture_sensor_set(sensor_refs) for synchronized capture"
            )
        raw = capture_set(sensor_refs)
        if not isinstance(raw, (list, tuple)) or len(raw) != len(sensor_refs):
            raise AdapterSensorError("synchronized sensor capture returned an invalid view set")
        captures = tuple(_normalize_capture(item) for item in raw)
        for capture in captures:
            _validate_capture(capture, self.required_sensor_kinds)
        if len({capture.scene_revision for capture in captures}) != 1:
            raise AdapterSensorError("synchronized sensor captures have mixed scene revisions")
        return captures


class RoboTwinObservationSource:
    """Structural implementation of the generic runtime ObservationSource port."""

    def __init__(self, adapter: RoboTwin20Adapter) -> None:
        self.adapter = adapter

    def capture(self, request: Mapping[str, Any]) -> dict[str, Any] | None:
        if not isinstance(request, Mapping):
            return None
        sensor_ref = request.get("sensor_ref")
        sensor_refs = request.get("sensor_refs")
        try:
            snapshots = (
                self.adapter.capture_many(sensor_refs)
                if isinstance(sensor_refs, list)
                else (self.adapter.capture(sensor_ref),)
            )
        except AdapterSensorError:
            return None
        snapshot = snapshots[0]
        views = [
            {
                "sensor_ref": requested,
                "captured_at": item.captured_at,
                "scene_revision": item.scene_revision,
                "frame_id": item.frame_id,
                "calibration_ref": item.calibration_ref,
                "artifacts": [
                    {"ref": artifact.ref, "kind": artifact.kind, "media_type": artifact.media_type}
                    for artifact in item.artifacts
                ],
                "sensor_available": item.sensor_available,
            }
            for requested, item in zip(sensor_refs or [sensor_ref], snapshots, strict=True)
        ]
        return {
            "captured_at": snapshot.captured_at,
            "scene_revision": snapshot.scene_revision,
            "frame_id": snapshot.frame_id,
            "calibration_ref": snapshot.calibration_ref,
            "artifacts": [
                {"ref": item.ref, "kind": item.kind, "media_type": item.media_type}
                for item in snapshot.artifacts
            ],
            "sensor_available": snapshot.sensor_available,
            "views": views,
        }


def _normalize_capture(raw: SensorCapture | Mapping[str, Any]) -> SensorCapture:
    if isinstance(raw, SensorCapture):
        return raw
    if not isinstance(raw, Mapping):
        raise AdapterSensorError("sensor capture must be an object")
    captured_at = raw.get("captured_at")
    if isinstance(captured_at, str):
        try:
            captured_at = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AdapterSensorError("sensor capture timestamp is invalid") from exc
    artifacts = raw.get("artifacts")
    if not isinstance(artifacts, (list, tuple)):
        raise AdapterSensorError("sensor capture artifacts must be a list")
    normalized_artifacts: list[SensorArtifact] = []
    for item in artifacts:
        if isinstance(item, SensorArtifact):
            normalized_artifacts.append(item)
        elif isinstance(item, Mapping):
            normalized_artifacts.append(
                SensorArtifact(
                    ref=item.get("ref"),
                    kind=item.get("kind"),
                    media_type=item.get("media_type"),
                )
            )
        else:
            raise AdapterSensorError("sensor artifact must be an object")
    return SensorCapture(
        captured_at=captured_at,
        scene_revision=raw.get("scene_revision"),
        frame_id=raw.get("frame_id"),
        calibration_ref=raw.get("calibration_ref"),
        artifacts=tuple(normalized_artifacts),
        sensor_available=raw.get("sensor_available", True),
    )


def _validate_capture(capture: SensorCapture, required_kinds: frozenset[str]) -> None:
    if not isinstance(capture.captured_at, datetime) or capture.captured_at.tzinfo is None:
        raise AdapterSensorError("sensor capture requires a timezone-aware captured_at")
    if not isinstance(capture.scene_revision, str) or not capture.scene_revision.strip():
        raise AdapterSensorError("sensor capture requires scene_revision")
    if not isinstance(capture.frame_id, str) or not capture.frame_id.strip():
        raise AdapterSensorError("sensor capture requires frame_id")
    if not isinstance(capture.calibration_ref, str) or not capture.calibration_ref.strip():
        raise AdapterSensorError("sensor capture requires calibration_ref")
    if capture.sensor_available is not True:
        raise AdapterSensorError("sensor capture is unavailable")
    seen: set[str] = set()
    for artifact in capture.artifacts:
        if (
            not isinstance(artifact.ref, str)
            or _ARTIFACT_REF.fullmatch(artifact.ref) is None
            or artifact.kind not in _KINDS
            or not isinstance(artifact.media_type, str)
            or not artifact.media_type.strip()
        ):
            raise AdapterSensorError("sensor artifact failed contract validation")
        seen.add(artifact.kind)
    missing = sorted(required_kinds - seen)
    if missing:
        raise AdapterSensorError(f"sensor capture is missing required kinds: {', '.join(missing)}")


__all__ = [
    "AdapterConfigurationError",
    "AdapterSensorError",
    "RoboTwin20Adapter",
    "RoboTwinObservationSource",
    "RoboTwinSensorBackend",
    "SensorArtifact",
    "SensorCapture",
]
