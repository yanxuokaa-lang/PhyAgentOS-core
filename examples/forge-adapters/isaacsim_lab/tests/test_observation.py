from datetime import timezone

import pytest
from PhyAgentOS.forge.capability_runtime.observation import ObservationEndpoint

from isaacsim_lab.observation import IsaacCameraMetadataProvider, IsaacCameraObservationSource


class FakeCamera:
    def __init__(self):
        self.calls = []

    def get_rgb(self):
        self.calls.append("rgb")
        return [[[(1, 2, 3)]]]

    def get_depth(self):
        self.calls.append("depth")
        return [[1.25]]

    def get_pointcloud(self):
        self.calls.append("point_cloud")
        return [[0.1, 0.2, 0.3]]


class CalibratedCamera(FakeCamera):
    def get_intrinsics_matrix(self, *, device):
        assert device == "cpu"
        return [[100.0, 0.0, 32.0], [0.0, 101.0, 24.0], [0.0, 0.0, 1.0]]

    def get_world_pose(self, *, camera_axes):
        assert camera_axes == "world"
        return [1.0, 2.0, 3.0], [1.0, 0.0, 0.0, 0.0]

    def get_resolution(self):
        return 64, 48


class ArtifactWriter:
    def __init__(self):
        self.values = []

    def write(self, sensor_ref, kind, value, *, captured_at):
        self.values.append((sensor_ref, kind, value, captured_at))
        return {
            "ref": f"artifact://capture/{sensor_ref.replace('/', '_')}/{kind}",
            "media_type": "application/x-numpy",
        }


def metadata(sensor_ref):
    return {
        "frame_id": sensor_ref.replace("/", "_"),
        "calibration_ref": f"artifact://calibration/{sensor_ref.replace('/', '_')}/v1",
        "scene_revision": "scene-1",
    }


def test_source_captures_requested_camera_modalities_and_endpoint_validates_them():
    camera = FakeCamera()
    writer = ArtifactWriter()
    source = IsaacCameraObservationSource(
        {"camera/front": camera}, metadata, writer,
        modalities=("rgb", "depth", "point_cloud"),
    )
    endpoint = ObservationEndpoint(source)

    result = endpoint.invoke({"sensor_ref": "camera/front", "max_age_ms": 1000})

    assert result["status"] == "available"
    assert result["scene_revision"] == "scene-1"
    assert result["frame"]["frame_id"] == "camera_front"
    assert [item["kind"] for item in result["artifacts"]] == ["rgb", "depth", "point_cloud"]
    assert {item["media_type"] for item in result["artifacts"]} == {"application/x-numpy"}
    assert camera.calls == ["rgb", "depth", "point_cloud"]
    assert len(writer.values) == 3
    assert all(item[3].tzinfo is timezone.utc for item in writer.values)


def test_source_captures_each_sensor_in_one_observation_set():
    cameras = {"camera/front": FakeCamera(), "camera/wrist": FakeCamera()}
    writer = ArtifactWriter()
    result = ObservationEndpoint(
        IsaacCameraObservationSource(cameras, metadata, writer)
    ).invoke({
        "sensor_refs": ["camera/front", "camera/wrist"],
        "max_age_ms": 1000,
    })

    assert result["status"] == "available"
    assert [view["sensor_ref"] for view in result["views"]] == [
        "camera/front", "camera/wrist",
    ]
    assert len(result["artifacts"]) == 2


@pytest.mark.parametrize(
    "camera_registry,metadata_resolver,writer",
    [
        ({}, metadata, ArtifactWriter()),
        ({"camera/front": FakeCamera()}, lambda _ref: None, ArtifactWriter()),
        ({"camera/front": FakeCamera()}, metadata, None),
    ],
)
def test_missing_sensor_metadata_or_writer_never_returns_available(
    camera_registry, metadata_resolver, writer,
):
    if writer is None:
        with pytest.raises(TypeError, match="artifact_writer"):
            IsaacCameraObservationSource(camera_registry, metadata_resolver, writer)
        return
    source = IsaacCameraObservationSource(camera_registry, metadata_resolver, writer)

    result = ObservationEndpoint(source).invoke({
        "sensor_ref": "camera/front", "max_age_ms": 1000,
    })

    assert result["status"] == "unavailable"
    assert result["artifacts"] == []


def test_source_rejects_unsupported_modality_and_missing_camera_method():
    with pytest.raises(ValueError, match="supported Isaac camera modalities"):
        IsaacCameraObservationSource({}, metadata, ArtifactWriter(), modalities=("semantic",))

    source = IsaacCameraObservationSource(
        {"camera/front": object()}, metadata, ArtifactWriter(), modalities=("depth",),
    )
    result = ObservationEndpoint(source).invoke({
        "sensor_ref": "camera/front", "max_age_ms": 1000,
    })
    assert result["status"] == "unavailable"


def test_source_rejects_artifact_without_actual_media_type():
    class IncompleteWriter:
        def write(self, sensor_ref, kind, value, *, captured_at):
            return {"ref": "artifact://capture/rgb"}

    source = IsaacCameraObservationSource(
        {"camera/front": FakeCamera()}, metadata, IncompleteWriter(),
    )
    result = ObservationEndpoint(source).invoke({
        "sensor_ref": "camera/front", "max_age_ms": 1000,
    })
    assert result["status"] == "unavailable"


def test_live_metadata_provider_persists_camera_calibration_and_host_lineage():
    camera = CalibratedCamera()
    writer = ArtifactWriter()
    provider = IsaacCameraMetadataProvider(
        {"camera/front": camera},
        lambda _ref: "camera/front/world",
        lambda _ref: "scene-live-9",
        writer,
    )

    result = provider("camera/front")

    assert result == {
        "frame_id": "camera/front/world",
        "scene_revision": "scene-live-9",
        "calibration_ref": "artifact://capture/camera_front/calibration",
    }
    sensor_ref, kind, payload, captured_at = writer.values[0]
    assert sensor_ref == "camera/front"
    assert kind == "calibration"
    assert payload["schema"] == "paos.camera_calibration.v1"
    assert payload["intrinsics"] == [
        [100.0, 0.0, 32.0], [0.0, 101.0, 24.0], [0.0, 0.0, 1.0],
    ]
    assert payload["resolution"] == [64.0, 48.0]
    assert payload["camera_pose_world"] == {
        "position_m": [1.0, 2.0, 3.0],
        "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
    }
    assert captured_at.tzinfo is timezone.utc


@pytest.mark.parametrize(
    "camera,frame,revision",
    [
        (object(), lambda _ref: "frame", lambda _ref: "scene"),
        (CalibratedCamera(), lambda _ref: None, lambda _ref: "scene"),
        (CalibratedCamera(), lambda _ref: "frame", lambda _ref: ""),
    ],
)
def test_live_metadata_provider_fails_closed_for_missing_camera_evidence(camera, frame, revision):
    writer = ArtifactWriter()
    provider = IsaacCameraMetadataProvider(
        {"camera/front": camera}, frame, revision, writer,
    )

    assert provider("camera/front") is None
    assert writer.values == []


def test_live_metadata_provider_rejects_invalid_calibration_and_incomplete_artifact():
    camera = CalibratedCamera()
    camera.get_intrinsics_matrix = lambda **_kwargs: [[1.0, 0.0], [0.0, 1.0]]
    writer = ArtifactWriter()
    provider = IsaacCameraMetadataProvider(
        {"camera/front": camera}, lambda _ref: "frame", lambda _ref: "scene", writer,
    )
    assert provider("camera/front") is None

    camera = CalibratedCamera()
    camera.get_intrinsics_matrix = lambda **_kwargs: (_ for _ in ()).throw(
        RuntimeError("camera calibration unavailable")
    )
    provider = IsaacCameraMetadataProvider(
        {"camera/front": camera}, lambda _ref: "frame", lambda _ref: "scene", writer,
    )
    assert provider("camera/front") is None
    assert writer.values == []

    class MissingMediaTypeWriter:
        def write(self, sensor_ref, kind, value, *, captured_at):
            return {"ref": "artifact://calibration/live"}

    provider = IsaacCameraMetadataProvider(
        {"camera/front": CalibratedCamera()},
        lambda _ref: "frame", lambda _ref: "scene", MissingMediaTypeWriter(),
    )
    assert provider("camera/front") is None


def test_live_metadata_provider_does_not_hide_artifact_storage_failures():
    class FailingWriter:
        def write(self, sensor_ref, kind, value, *, captured_at):
            raise OSError("calibration artifact store unavailable")

    provider = IsaacCameraMetadataProvider(
        {"camera/front": CalibratedCamera()},
        lambda _ref: "frame", lambda _ref: "scene", FailingWriter(),
    )
    with pytest.raises(OSError, match="artifact store unavailable"):
        provider("camera/front")
