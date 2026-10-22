from types import SimpleNamespace

import pytest

from PhyAgentOS.forge.artifacts import ArtifactContent
from PhyAgentOS.forge.capability_runtime import (
    SceneUnderstandingEndpoint,
    SceneUnderstandingInferenceRegistry,
)


class Resolver:
    def resolve(self, ref):
        return ArtifactContent(b"image", "image/png") if ref == "artifact://scene/front" else None


class Factory:
    def __init__(self, inference_id, inference):
        self.inference_id = inference_id
        self.inference = inference
        self.configurations = []

    def create(self, *, configuration):
        self.configurations.append(configuration)
        return self.inference


def test_registry_discovers_and_composes_replaceable_inference_factories(monkeypatch):
    seen = []

    def first_inference(request):
        seen.append(("first", request))
        return {
            "entities": [{
                "entity_ref": "entity://bottle-1", "category": "bottle", "confidence": 0.9,
                "provenance": ["artifact://scene/front"],
            }],
            "relations": [], "spatial_envelopes": [], "ambiguities": [],
        }

    first = Factory("fixture-a", first_inference)
    second = Factory("fixture-b", lambda request: {"entities": []})
    points = [SimpleNamespace(load=lambda value=value: lambda: value) for value in (first, second)]
    monkeypatch.setattr(
        "PhyAgentOS.forge.capability_runtime.inference_registry.entry_points",
        lambda: SimpleNamespace(select=lambda *, group: points),
    )

    registry = SceneUnderstandingInferenceRegistry()
    assert registry.discover() == ("fixture-a", "fixture-b")
    provider = registry.compose("fixture-a", resolver=Resolver(), configuration={"endpoint": "deployment"})
    result = SceneUnderstandingEndpoint(provider).invoke({
        "observation_ref": "observation://revision-1/front",
        "scene_revision": "revision-1", "frame_id": "front",
        "calibration_ref": "artifact://scene/calibration.json",
        "freshness_ms": 2, "max_age_ms": 100,
        "artifacts": ["artifact://scene/front"],
    })
    assert result["status"] == "available"
    assert result["entities"][0]["entity_ref"] == "entity://bottle-1"
    assert first.configurations == [{"endpoint": "deployment"}]
    assert seen[0][1]["resolved_artifacts"][0]["data"] == b"image"

    second_provider = registry.compose("fixture-b", resolver=Resolver())
    assert second_provider.understand({
        "artifacts": ["artifact://scene/front"], "views": [],
    }) == {"entities": []}


def test_registry_rejects_invalid_factories_and_unknown_ids():
    registry = SceneUnderstandingInferenceRegistry()
    with pytest.raises(TypeError, match="does not implement"):
        registry.register(object())

    with pytest.raises(KeyError, match="not registered"):
        registry.create_inference("missing")

    invalid = Factory("invalid", object())
    registry.register(invalid)
    with pytest.raises(TypeError, match="must expose infer"):
        registry.create_inference("invalid")


def test_registry_rejects_duplicate_factory_ids():
    registry = SceneUnderstandingInferenceRegistry()
    registry.register(Factory("same", lambda _request: {}))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(Factory("same", lambda _request: {}))
