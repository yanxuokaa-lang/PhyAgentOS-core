import pytest

from PhyAgentOS.forge.artifacts import LocalFilesystemArtifactResolver
from PhyAgentOS.forge.capability_runtime import (
    ArtifactResolvingSceneUnderstandingProvider,
    SceneUnderstandingEndpoint,
)


def request(**overrides):
    value = {
        "observation_ref": "observation://camera/front",
        "scene_revision": "revision-7",
        "frame_id": "camera-front",
        "calibration_ref": "artifact://store/calibration.json",
        "freshness_ms": 12,
        "max_age_ms": 100,
        "artifacts": ["artifact://store/rgb/front.png"],
    }
    value.update(overrides)
    return value


def test_artifact_resolving_provider_supplies_payload_to_replaceable_inference(tmp_path):
    (tmp_path / "rgb").mkdir()
    (tmp_path / "rgb/front.png").write_bytes(b"png-data")
    resolver = LocalFilesystemArtifactResolver({"store": tmp_path})

    class FirstInference:
        def infer(self, payload):
            self.payload = payload
            return {"entities": []}

    first = FirstInference()
    provider = ArtifactResolvingSceneUnderstandingProvider(resolver, first)

    assert provider.understand(request()) == {"entities": []}
    assert first.payload["observation_ref"] == "observation://camera/front"
    assert first.payload["resolved_artifacts"] == [{
        "ref": "artifact://store/rgb/front.png",
        "media_type": "image/png",
        "data": b"png-data",
    }]

    second_calls = []
    second = ArtifactResolvingSceneUnderstandingProvider(
        resolver,
        lambda payload: second_calls.append(payload) or {"relations": []},
    )
    assert second.understand(request()) == {"relations": []}
    assert second_calls[0]["resolved_artifacts"][0]["data"] == b"png-data"


def test_artifact_resolving_provider_includes_view_artifacts_and_deduplicates(tmp_path):
    (tmp_path / "rgb").mkdir()
    (tmp_path / "rgb/front.png").write_bytes(b"front")
    (tmp_path / "rgb/wrist.png").write_bytes(b"wrist")
    provider = ArtifactResolvingSceneUnderstandingProvider(
        LocalFilesystemArtifactResolver({"store": tmp_path}),
        lambda payload: {"resolved_artifacts": payload["resolved_artifacts"]},
    )
    payload = provider.understand(request(
        views=[{
            "artifacts": [
                {"ref": "artifact://store/rgb/front.png", "kind": "rgb", "media_type": "image/png"},
                {"ref": "artifact://store/rgb/wrist.png", "kind": "rgb", "media_type": "image/png"},
            ],
        }],
    ))
    assert [item["data"] for item in payload["resolved_artifacts"]] == [b"front", b"wrist"]
    assert payload["resolved_artifacts"][0]["kind"] == "rgb"


def test_artifact_resolving_provider_fails_when_artifact_is_missing(tmp_path):
    provider = ArtifactResolvingSceneUnderstandingProvider(
        LocalFilesystemArtifactResolver({"store": tmp_path}),
        lambda _payload: pytest.fail("inference must not run without its artifacts"),
    )
    with pytest.raises(FileNotFoundError, match="artifact is unavailable"):
        provider.understand(request())


def test_artifact_resolving_provider_rejects_media_type_mismatch(tmp_path):
    (tmp_path / "rgb").mkdir()
    (tmp_path / "rgb/front.png").write_bytes(b"png-data")
    provider = ArtifactResolvingSceneUnderstandingProvider(
        LocalFilesystemArtifactResolver({"store": tmp_path}),
        lambda _payload: pytest.fail("inference must not receive mismatched media"),
    )
    mismatched = request(views=[{
        "artifacts": [{
            "ref": "artifact://store/rgb/front.png",
            "kind": "rgb",
            "media_type": "application/x-npy",
        }],
    }])
    with pytest.raises(ValueError, match="media type mismatch"):
        provider.understand(mismatched)


def test_artifact_resolving_provider_rejects_non_mapping_inference_result(tmp_path):
    (tmp_path / "rgb").mkdir()
    (tmp_path / "rgb/front.png").write_bytes(b"png-data")
    provider = ArtifactResolvingSceneUnderstandingProvider(
        LocalFilesystemArtifactResolver({"store": tmp_path}),
        lambda _payload: ["not", "an", "object"],
    )
    with pytest.raises(TypeError, match="return an object or null"):
        provider.understand(request())


def test_artifact_resolving_provider_integrates_with_paos_understanding_query(tmp_path):
    (tmp_path / "rgb").mkdir()
    (tmp_path / "rgb/front.png").write_bytes(b"png-data")
    ref = "artifact://store/rgb/front.png"
    provider = ArtifactResolvingSceneUnderstandingProvider(
        LocalFilesystemArtifactResolver({"store": tmp_path}),
        lambda payload: {
            "entities": [{
                "entity_ref": "entity://observed-vial",
                "category": "container",
                "confidence": 0.91,
                "provenance": [payload["resolved_artifacts"][0]["ref"]],
            }],
        },
    )

    result = SceneUnderstandingEndpoint(provider).invoke(
        request(observation_ref="observation://revision-7/camera-front")
    )

    assert result["status"] == "available"
    assert result["entities"][0]["entity_ref"] == "entity://observed-vial"
    assert result["entities"][0]["provenance"] == [ref]
