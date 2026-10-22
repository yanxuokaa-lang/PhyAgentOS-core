from datetime import timezone

import pytest
from PhyAgentOS.forge.capability_runtime.observation import ObservationEndpoint

from isaacsim_lab.observation import IsaacCameraObservationSource


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
