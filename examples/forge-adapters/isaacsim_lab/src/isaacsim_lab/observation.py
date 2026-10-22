"""Isaac camera ObservationSource backed by host-owned sensor and artifact ports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol


class ObservationArtifactWriter(Protocol):
    """Persist one sensor value and return its durable ref and actual media type."""

    def write(
        self, sensor_ref: str, kind: str, value: Any, *, captured_at: datetime
    ) -> Mapping[str, str]: ...


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


__all__ = ["IsaacCameraObservationSource", "ObservationArtifactWriter"]
