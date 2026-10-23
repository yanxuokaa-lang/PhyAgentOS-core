import json
from datetime import datetime, timezone
from io import BytesIO

import numpy as np
import pytest
from PhyAgentOS.forge.capability_runtime.observation import ObservationEndpoint

from isaacsim_lab.observation import (
    FilesystemObservationArtifactWriter,
    IsaacCameraMetadataProvider,
    IsaacCameraObservationSource,
)


class FakeCamera:
    def __init__(self):
        self.calls = []

    def get_rgb(self):
        self.calls.append("rgb")
        return [[[(1, 2, 3)]]]

    def get_depth(self):
        self.calls.append("depth")
        return [[1.25]]

    def get_pointcloud(self, *, world_frame):
        assert world_frame is False
        self.calls.append("point_cloud")
        return [[0.1, 0.2, 0.3]]


class CalibratedCamera(FakeCamera):
    def get_intrinsics_matrix(self, *, device):
        assert device == "cpu"
        return [[100.0, 0.0, 32.0], [0.0, 101.0, 24.0], [0.0, 0.0, 1.0]]

    def get_world_pose(self, *, camera_axes):
        assert camera_axes == "ros"
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


def test_filesystem_writer_persists_sensor_arrays_and_calibration(tmp_path):
    from PhyAgentOS.forge.artifacts import LocalFilesystemArtifactResolver

    writer = FilesystemObservationArtifactWriter(tmp_path, namespace="labutopia")
    captured_at = datetime(2026, 10, 22, tzinfo=timezone.utc)

    image = np.asarray([[[1, 2, 3]]], dtype=np.uint8)
    rgb = writer.write("camera/front", "rgb", image, captured_at=captured_at)
    depth = writer.write(
        "camera/front", "depth", np.asarray([[1.25]], dtype=np.float32),
        captured_at=captured_at,
    )
    calibration = writer.write(
        "camera/front", "calibration", {"frame_id": "camera/front"},
        captured_at=captured_at,
    )

    assert rgb["ref"].startswith("artifact://labutopia/rgb/")
    assert rgb["media_type"] == "image/png"
    rgb_path = tmp_path / rgb["ref"].removeprefix("artifact://labutopia/")
    from PIL import Image

    with Image.open(BytesIO(rgb_path.read_bytes())) as decoded:
        assert np.array_equal(np.asarray(decoded), image)
    assert rgb_path.suffix == ".png"
    depth_path = tmp_path / depth["ref"].removeprefix("artifact://labutopia/")
    assert depth["media_type"] == "application/x-npy"
    assert np.array_equal(
        np.load(BytesIO(depth_path.read_bytes()), allow_pickle=False),
        np.asarray([[1.25]], dtype=np.float32),
    )
    assert calibration["ref"].startswith("artifact://labutopia/calibration/")
    assert calibration["media_type"] == "application/json"
    calibration_path = tmp_path / calibration["ref"].removeprefix("artifact://labutopia/")
    assert json.loads(calibration_path.read_text(encoding="utf-8")) == {
        "frame_id": "camera/front"
    }
    resolved_rgb = LocalFilesystemArtifactResolver({"labutopia": tmp_path}).resolve(rgb["ref"])
    resolved_calibration = LocalFilesystemArtifactResolver({"labutopia": tmp_path}).resolve(
        calibration["ref"]
    )
    assert resolved_rgb is not None
    assert resolved_rgb.media_type == rgb["media_type"]
    assert resolved_rgb.data == rgb_path.read_bytes()
    assert resolved_calibration is not None
    assert resolved_calibration.media_type == calibration["media_type"]
    assert resolved_calibration.data == calibration_path.read_bytes()
    assert rgb["ref"] != calibration["ref"]


def test_filesystem_writer_normalizes_float_rgb_without_clipping(tmp_path):
    writer = FilesystemObservationArtifactWriter(tmp_path, namespace="labutopia")
    rgb = writer.write(
        "camera/front", "rgb", np.asarray([[[0.0, 0.5, 1.0]]]),
        captured_at=datetime(2026, 10, 22, tzinfo=timezone.utc),
    )
    from PIL import Image

    image_path = tmp_path / rgb["ref"].removeprefix("artifact://labutopia/")
    with Image.open(image_path) as decoded:
        assert np.array_equal(np.asarray(decoded), np.asarray([[[0, 128, 255]]], dtype=np.uint8))
    assert rgb["media_type"] == "image/png"


@pytest.mark.parametrize(
    "image",
    [np.zeros((2, 2), dtype=np.uint8), np.full((1, 1, 3), 256.0)],
)
def test_filesystem_writer_rejects_invalid_rgb_shapes_and_ranges(tmp_path, image):
    writer = FilesystemObservationArtifactWriter(tmp_path, namespace="labutopia")
    with pytest.raises(ValueError, match="RGB camera artifact"):
        writer.write(
            "camera/front", "rgb", image,
            captured_at=datetime(2026, 10, 22, tzinfo=timezone.utc),
        )


def test_filesystem_writer_rejects_invalid_capture_metadata(tmp_path):
    writer = FilesystemObservationArtifactWriter(tmp_path, namespace="labutopia")
    with pytest.raises(ValueError, match="timezone-aware"):
        writer.write("camera/front", "rgb", [[1]], captured_at=datetime(2026, 10, 22))
    with pytest.raises(ValueError, match="artifact kind"):
        writer.write("camera/front", "semantic", [[1]], captured_at=datetime.now(timezone.utc))


def test_observation_endpoint_fails_closed_when_filesystem_write_fails(tmp_path, monkeypatch):
    import isaacsim_lab.observation as observation_module

    writer = FilesystemObservationArtifactWriter(tmp_path, namespace="labutopia")
    monkeypatch.setattr(
        observation_module,
        "atomic_write_bytes",
        lambda *_args: (_ for _ in ()).throw(OSError("disk unavailable")),
    )
    source = IsaacCameraObservationSource(
        {"camera/front": FakeCamera()}, metadata, writer,
    )

    result = ObservationEndpoint(source).invoke({
        "sensor_ref": "camera/front", "max_age_ms": 1000,
    })

    assert result["status"] == "unavailable"
    assert result["artifacts"] == []
