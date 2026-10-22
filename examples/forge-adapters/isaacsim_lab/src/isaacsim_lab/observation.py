"""Isaac camera ObservationSource backed by host-owned sensor and artifact ports."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from numbers import Real
from typing import Any, Callable, Mapping, Protocol


class ObservationArtifactWriter(Protocol):
    """Persist one sensor value and return its durable ref and actual media type."""

    def write(
        self, sensor_ref: str, kind: str, value: Any, *, captured_at: datetime
    ) -> Mapping[str, str]: ...


class IsaacCameraMetadataProvider:
    """Resolve live camera calibration while keeping host frame/revision ownership."""

    def __init__(
        self,
        cameras: Mapping[str, Any] | Callable[[str], Any | None],
        frame_id: Callable[[str], str | None],
        scene_revision: Callable[[str], str | None],
        artifact_writer: ObservationArtifactWriter,
    ) -> None:
        if not callable(frame_id) or not callable(scene_revision):
            raise TypeError("frame_id and scene_revision must resolve live host metadata")
        if not callable(getattr(artifact_writer, "write", None)):
            raise TypeError("artifact_writer must expose write(sensor_ref, kind, value)")
        self._cameras = cameras
        self._frame_id = frame_id
        self._scene_revision = scene_revision
        self._artifact_writer = artifact_writer

    def __call__(self, sensor_ref: str) -> Mapping[str, str] | None:
        camera = self._resolve_camera(sensor_ref)
        if camera is None:
            return None
        get_intrinsics = getattr(camera, "get_intrinsics_matrix", None)
        get_pose = getattr(camera, "get_world_pose", None)
        get_resolution = getattr(camera, "get_resolution", None)
        if not all(callable(method) for method in (get_intrinsics, get_pose, get_resolution)):
            return None
        frame_id = self._frame_id(sensor_ref)
        scene_revision = self._scene_revision(sensor_ref)
        if not _nonempty_text(frame_id) or not _nonempty_text(scene_revision):
            return None
        try:
            intrinsics = _matrix3(get_intrinsics(device="cpu"))
            position, orientation = get_pose(camera_axes="world")
            resolution = _vector(get_resolution(), 2)
            payload = {
                "schema": "paos.camera_calibration.v1",
                "sensor_ref": sensor_ref,
                "frame_id": frame_id,
                "scene_revision": scene_revision,
                "resolution": resolution,
                "intrinsics": intrinsics,
                "camera_pose_world": {
                    "position_m": _vector(position, 3),
                    "orientation_wxyz": _vector(orientation, 4),
                },
            }
        except Exception:
            return None
        stored = self._artifact_writer.write(
            sensor_ref, "calibration", payload, captured_at=datetime.now(timezone.utc)
        )
        if not isinstance(stored, Mapping):
            return None
        calibration_ref = stored.get("ref")
        media_type = stored.get("media_type")
        if not _nonempty_text(calibration_ref) or not _nonempty_text(media_type):
            return None
        return {
            "frame_id": frame_id,
            "scene_revision": scene_revision,
            "calibration_ref": calibration_ref,
        }

    def _resolve_camera(self, sensor_ref: str) -> Any | None:
        if callable(self._cameras):
            return self._cameras(sensor_ref)
        return self._cameras.get(sensor_ref)


_MODALITIES = {
    "rgb": "get_rgb",
    "depth": "get_depth",
    "point_cloud": "get_pointcloud",
}


class IsaacCameraObservationSource:
    """Capture registered Isaac cameras without deriving scene truth from USD.

    The host owns the live camera objects, their measured frame/calibration and
    scene revision, and durable artifact writing. This class only reads enabled
    camera modalities and adapts their outputs to the PAOS observation source
    contract. It can be reused by any Isaac task that exposes these camera APIs.
    """

    def __init__(
        self,
        cameras: Mapping[str, Any] | Callable[[str], Any | None],
        metadata: Callable[[str], Mapping[str, Any] | None],
        artifact_writer: ObservationArtifactWriter,
        *,
        modalities: tuple[str, ...] = ("rgb",),
    ) -> None:
        if not callable(metadata):
            raise TypeError("metadata must resolve live sensor metadata by sensor_ref")
        if not callable(getattr(artifact_writer, "write", None)):
            raise TypeError("artifact_writer must expose write(sensor_ref, kind, value)")
        if not modalities or any(item not in _MODALITIES for item in modalities):
            raise ValueError("modalities must contain supported Isaac camera modalities")
        self._cameras = cameras
        self._metadata = metadata
        self._artifact_writer = artifact_writer
        self._modalities = tuple(dict.fromkeys(modalities))

    def capture(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None:
        sensor_ref = request.get("sensor_ref")
        sensor_refs = request.get("sensor_refs")
        refs = [sensor_ref] if isinstance(sensor_ref, str) else sensor_refs
        if not isinstance(refs, (list, tuple)) or not refs:
            return None
        views = []
        for ref in refs:
            view = self._capture_view(ref)
            if view is None:
                return None
            views.append(view)
        if len(views) == 1:
            return views[0]
        return {"views": views}

    def _capture_view(self, sensor_ref: Any) -> dict[str, Any] | None:
        if not isinstance(sensor_ref, str) or not sensor_ref.strip():
            return None
        camera = self._resolve_camera(sensor_ref)
        metadata = self._metadata(sensor_ref)
        if camera is None or not isinstance(metadata, Mapping):
            return None
        frame_id = metadata.get("frame_id")
        calibration_ref = metadata.get("calibration_ref")
        scene_revision = metadata.get("scene_revision")
        if not all(isinstance(value, str) and value.strip() for value in (frame_id, calibration_ref, scene_revision)):
            return None

        captured_at = datetime.now(timezone.utc)
        artifacts = []
        for kind in self._modalities:
            getter_name = _MODALITIES[kind]
            getter = getattr(camera, getter_name, None)
            if not callable(getter):
                return None
            value = getter()
            if not _has_data(value):
                return None
            stored = self._artifact_writer.write(sensor_ref, kind, value, captured_at=captured_at)
            if not isinstance(stored, Mapping):
                return None
            artifact_ref = stored.get("ref")
            media_type = stored.get("media_type")
            if not isinstance(artifact_ref, str) or not artifact_ref.strip():
                return None
            if not isinstance(media_type, str) or not media_type.strip():
                return None
            artifacts.append({"ref": artifact_ref, "kind": kind, "media_type": media_type})

        return {
            "sensor_ref": sensor_ref,
            "captured_at": captured_at,
            "scene_revision": scene_revision,
            "frame_id": frame_id,
            "calibration_ref": calibration_ref,
            "artifacts": artifacts,
        }

    def _resolve_camera(self, sensor_ref: str) -> Any | None:
        if callable(self._cameras):
            return self._cameras(sensor_ref)
        return self._cameras.get(sensor_ref)


def _has_data(value: Any) -> bool:
    if value is None:
        return False
    size = getattr(value, "size", None)
    if isinstance(size, int):
        return size > 0
    try:
        return len(value) > 0
    except TypeError:
        return True


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _plain_values(value: Any) -> Any:
    convert = getattr(value, "tolist", None)
    if callable(convert):
        value = convert()
    if isinstance(value, (list, tuple)):
        return [_plain_values(item) for item in value]
    if isinstance(value, Real) and not isinstance(value, bool):
        number = float(value)
        if math.isfinite(number):
            return number
    raise ValueError("camera calibration contains a non-finite or non-numeric value")


def _vector(value: Any, size: int) -> list[float]:
    values = _plain_values(value)
    if not isinstance(values, list) or len(values) != size or any(isinstance(item, list) for item in values):
        raise ValueError(f"camera calibration vector must contain {size} numbers")
    return values


def _matrix3(value: Any) -> list[list[float]]:
    values = _plain_values(value)
    if not isinstance(values, list) or len(values) != 3:
        raise ValueError("camera intrinsics must be a 3x3 matrix")
    return [_vector(row, 3) for row in values]


__all__ = ["IsaacCameraMetadataProvider", "IsaacCameraObservationSource", "ObservationArtifactWriter"]
