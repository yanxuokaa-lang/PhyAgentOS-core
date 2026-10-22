from types import SimpleNamespace

import pytest

from PhyAgentOS.forge.artifacts import ArtifactContent
from PhyAgentOS.forge.capability_runtime import (
    OpenAIResponsesSceneUnderstandingProvider,
    OpenAIUnderstandingConfig,
    OpenAIUnderstandingError,
    SceneUnderstandingEndpoint,
)


class Resolver:
    def resolve(self, ref):
        return ArtifactContent(b"png-bytes", "image/png") if ref == "artifact://scene/rgb" else None


def request():
    return {
        "observation_ref": "observation://scene-1/camera-front",
        "scene_revision": "scene-1",
        "frame_id": "camera-front",
        "calibration_ref": "artifact://scene/calibration",
        "freshness_ms": 5,
        "max_age_ms": 100,
        "artifacts": ["artifact://scene/rgb"],
    }


def result():
    return {"entities": [{"entity_ref": "entity://bottle-1", "category": "bottle",
                           "confidence": 0.9, "provenance": ["artifact://scene/rgb"]}],
            "relations": [], "spatial_envelopes": [], "ambiguities": []}


class Client:
    def __init__(self, output):
        self.calls = []
        self.responses = SimpleNamespace(create=self.create)
        self.output = output

    def create(self, **payload):
        self.calls.append(payload)
        return SimpleNamespace(output_text=self.output)

    def close(self):
        pass


def provider(client, **overrides):
    config = OpenAIUnderstandingConfig(api_base="https://api.example/v1", model="gpt-test", **overrides)
    return OpenAIResponsesSceneUnderstandingProvider(
        Resolver(), config, client_factory=lambda **_: client
    )


def test_provider_adapts_gpt_output_through_generic_understanding_endpoint(monkeypatch):
    client = Client(__import__("json").dumps(result()))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    endpoint = SceneUnderstandingEndpoint(provider(client))
    output = endpoint.invoke(request())
    assert output["status"] == "available"
    assert output["entities"][0]["entity_ref"] == "entity://bottle-1"
    assert client.calls[0]["model"] == "gpt-test"
    assert client.calls[0]["store"] is False
    image = client.calls[0]["input"][0]["content"][1]["image_url"]
    assert image.startswith("data:image/png;base64,")


def test_provider_rejects_missing_credential_without_fake_success(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(OpenAIUnderstandingError, match="credential"):
        provider(Client("{}" )).understand(request())


def test_provider_rejects_non_json_model_output(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with pytest.raises(OpenAIUnderstandingError, match="valid JSON"):
        provider(Client("not-json")).understand(request())


def test_provider_rejects_metric_claims_from_rgb_inference(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    claim = result()
    claim["spatial_envelopes"] = [{"entity_ref": "entity://bottle-1"}]
    with pytest.raises(OpenAIUnderstandingError, match="cannot provide metric"):
        provider(Client(__import__("json").dumps(claim))).understand(request())


def test_provider_is_configured_without_environment_specific_fields():
    config = OpenAIUnderstandingConfig(api_base="https://api.example/v1", model="gpt-test")
    config.validate()
    assert set(config.__dict__) == {
        "api_base", "model", "api_key_env", "reasoning_effort", "timeout_seconds", "max_output_tokens"
    }
