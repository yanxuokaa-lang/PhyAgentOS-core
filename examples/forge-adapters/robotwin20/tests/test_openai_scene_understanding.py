from __future__ import annotations

import base64
import json

import pytest
from PhyAgentOS.forge.tool_client import ForgeToolClient
from pick_place_workflow.fake_gateway import FakeGatewayTransport

from robotwin20_adapter import (
    ArtifactPayload,
    FilesystemArtifactResolver,
    OpenAIResponsesConfig,
    OpenAIResponsesInferenceError,
    OpenAIResponsesSceneUnderstandingInference,
    RoboTwinSceneUnderstandingProvider,
)

REQUEST = {
    "observation_ref": "observation://desktop-tidy-real/camera_front",
    "scene_revision": "desktop-tidy-real",
    "frame_id": "camera_front",
    "calibration_ref": "calibration://front/v3",
    "freshness_ms": 100,
    "max_age_ms": 1000,
    "artifacts": ["artifact://desktop-tidy-real/capture/rgb"],
}


class Response:
    output_text = json.dumps(
        {
            "entities": [
                {
                    "entity_ref": "entity://bottle-1",
                    "category": "container",
                    "confidence": 0.91,
                    "provenance": ["artifact://desktop-tidy-real/capture/rgb"],
                }
            ],
            "relations": [],
            "spatial_envelopes": [],
            "ambiguities": [],
        }
    )


class Responses:
    def __init__(self):
        self.calls = []

    def create(self, **payload):
        self.calls.append(payload)
        return Response()


class Client:
    def __init__(self):
        self.responses = Responses()
        self.closed = False

    def close(self):
        self.closed = True


class Resolver:
    def resolve(self, ref):
        assert ref == REQUEST["artifacts"][0]
        return ArtifactPayload(b"rgb-bytes", "image/png")


def test_responses_provider_builds_structured_image_request_and_projects_result(monkeypatch):
    monkeypatch.setenv("CUSTOM_API_KEY", "test-key")
    client = Client()
    client_options = {}

    def client_factory(**kwargs):
        client_options.update(kwargs)
        return client

    inference = OpenAIResponsesSceneUnderstandingInference(
        Resolver(),
        config=OpenAIResponsesConfig(model="gpt-5.6-sol"),
        client_factory=client_factory,
    )

    result = inference.infer(REQUEST)

    assert result["entities"][0]["entity_ref"] == "entity://bottle-1"
    payload = client.responses.calls[0]
    assert payload["model"] == "gpt-5.6-sol"
    assert payload["store"] is False
    assert payload["text"]["format"]["type"] == "json_schema"
    assert client_options["max_retries"] == 0
    prompt = json.loads(payload["input"][0]["content"][0]["text"])
    assert "desktop" not in prompt["task"].lower()
    assert "geometric blocks or cubes" in prompt["task"]
    assert "left-to-right layout" in prompt["task"]
    assert "simple geometric objects" in payload["instructions"]
    assert "not household items" in payload["instructions"]
    image = payload["input"][0]["content"][1]
    assert image["type"] == "input_image"
    assert image["image_url"] == "data:image/png;base64," + base64.b64encode(b"rgb-bytes").decode()
    assert client.closed is True


def test_provider_composes_with_generic_scene_understanding_endpoint(monkeypatch):
    monkeypatch.setenv("CUSTOM_API_KEY", "test-key")
    client = Client()
    inference = OpenAIResponsesSceneUnderstandingInference(
        Resolver(), client_factory=lambda **kwargs: client
    )
    snapshot = RoboTwinSceneUnderstandingProvider(inference).understand(REQUEST)
    assert snapshot is not None
    assert snapshot["entities"][0]["provenance"] == REQUEST["artifacts"]


def test_provider_binds_empty_semantic_provenance_to_current_rgb(monkeypatch):
    monkeypatch.setenv("CUSTOM_API_KEY", "test-key")

    class EmptyProvenanceResponse(Response):
        output_text = json.dumps(
            {
                "entities": [
                    {
                        "entity_ref": "entity://bottle-1",
                        "category": "container",
                        "confidence": 0.91,
                        "provenance": [],
                    }
                ],
                "relations": [],
                "spatial_envelopes": [],
                "ambiguities": [],
            }
        )

    class EmptyProvenanceClient(Client):
        def __init__(self):
            super().__init__()
            self.responses.create = lambda **kwargs: EmptyProvenanceResponse()

    inference = OpenAIResponsesSceneUnderstandingInference(
        Resolver(), client_factory=lambda **kwargs: EmptyProvenanceClient()
    )
    result = inference.infer(REQUEST)
    assert result["entities"][0]["provenance"] == REQUEST["artifacts"]


def test_empty_scene_claims_are_projected_as_uncertain_without_inventing_entities(monkeypatch):
    monkeypatch.setenv("CUSTOM_API_KEY", "test-key")

    class EmptySceneResponse(Response):
        output_text = json.dumps(
            {"entities": [], "relations": [], "spatial_envelopes": [], "ambiguities": []}
        )

    class EmptySceneClient(Client):
        def __init__(self):
            super().__init__()
            self.responses.create = lambda **kwargs: EmptySceneResponse()

    inference = OpenAIResponsesSceneUnderstandingInference(
        Resolver(), client_factory=lambda **kwargs: EmptySceneClient()
    )

    result = inference.infer(REQUEST)

    assert result["entities"] == []
    assert result["ambiguities"] == [
        {
            "code": "entity_count_uncertain",
            "message": (
                "No entities were returned; verify whether visible objects were missed "
                "or whether the image contains no identifiable entities."
            ),
            "entity_refs": [],
        }
    ]


@pytest.mark.asyncio
async def test_openai_provider_crosses_forge_tool_client_and_fake_gateway(monkeypatch):
    monkeypatch.setenv("CUSTOM_API_KEY", "test-key")
    client = Client()
    provider = RoboTwinSceneUnderstandingProvider(
        OpenAIResponsesSceneUnderstandingInference(Resolver(), client_factory=lambda **kwargs: client)
    )
    observation_provider = type("Observation", (), {"observe": lambda self, sensor_ref: None})()
    transport = FakeGatewayTransport(observation_provider, understanding_provider=provider)
    async with ForgeToolClient("http://fake", transport=transport) as forge_client:
        response = await forge_client.invoke_query_tool("scene.understand", REQUEST)

    assert response["data"]["status"] == "available"
    assert [request.url.path for request in transport.requests] == [
        "/tools/scene.understand",
        "/tools/scene_understanding/understand:invoke",
    ]


def test_missing_key_fails_closed_before_client_creation(monkeypatch):
    monkeypatch.delenv("CUSTOM_API_KEY", raising=False)
    called = False

    def factory(**kwargs):
        nonlocal called
        called = True
        return Client()

    inference = OpenAIResponsesSceneUnderstandingInference(Resolver(), client_factory=factory)
    with pytest.raises(OpenAIResponsesInferenceError, match="Missing CUSTOM_API_KEY"):
        inference.infer(REQUEST)
    assert called is False


def test_non_image_or_missing_artifact_fails_closed(monkeypatch):
    monkeypatch.setenv("CUSTOM_API_KEY", "test-key")
    inference = OpenAIResponsesSceneUnderstandingInference(
        lambda ref: None,
        client_factory=lambda **kwargs: Client(),
    )
    with pytest.raises(OpenAIResponsesInferenceError, match="no image artifact"):
        inference.infer(REQUEST)


def test_filesystem_resolver_maps_external_rgb_artifact_and_rejects_escape(tmp_path):
    capture_dir = tmp_path / "desktop-tidy-real" / "capture"
    capture_dir.mkdir(parents=True)
    image_path = capture_dir / "rgb.png"
    image_path.write_bytes(b"rgb-bytes")
    resolver = FilesystemArtifactResolver(tmp_path)

    payload = resolver.resolve("artifact://desktop-tidy-real/capture/rgb")
    assert payload is not None
    assert payload.data == b"rgb-bytes"
    assert payload.media_type == "image/png"
    assert resolver.resolve("artifact://desktop-tidy-real/../escape/rgb") is None
    assert resolver.resolve("artifact://desktop-tidy-real/capture/depth") is None


def test_provider_specific_response_fields_fail_closed(monkeypatch):
    monkeypatch.setenv("CUSTOM_API_KEY", "test-key")

    class BadResponse(Response):
        output_text = json.dumps(
            {"entities": [], "relations": [], "spatial_envelopes": [], "ambiguities": [], "actor_id": "x"}
        )

    class BadClient(Client):
        def __init__(self):
            super().__init__()
            self.responses.create = lambda **kwargs: BadResponse()

    inference = OpenAIResponsesSceneUnderstandingInference(
        Resolver(), client_factory=lambda **kwargs: BadClient()
    )
    with pytest.raises(OpenAIResponsesInferenceError, match="violated the provider contract"):
        inference.infer(REQUEST)


def test_provider_rejects_metric_ambiguity_codes_even_if_a_client_ignores_schema(monkeypatch):
    monkeypatch.setenv("CUSTOM_API_KEY", "test-key")

    class MetricAmbiguityResponse(Response):
        output_text = json.dumps(
            {
                "entities": [],
                "relations": [],
                "spatial_envelopes": [],
                "ambiguities": [
                    {
                        "code": "NO_METRIC_3D_EXTENTS",
                        "message": "RGB cannot estimate metric size",
                        "entity_refs": [],
                    }
                ],
            }
        )

    class MetricAmbiguityClient(Client):
        def __init__(self):
            super().__init__()
            self.responses.create = lambda **kwargs: MetricAmbiguityResponse()

    inference = OpenAIResponsesSceneUnderstandingInference(
        Resolver(), client_factory=lambda **kwargs: MetricAmbiguityClient()
    )
    with pytest.raises(OpenAIResponsesInferenceError, match="non-semantic ambiguity code"):
        inference.infer(REQUEST)


def test_provider_accepts_canonical_visible_semantic_ambiguity(monkeypatch):
    monkeypatch.setenv("CUSTOM_API_KEY", "test-key")

    class SemanticAmbiguityResponse(Response):
        output_text = json.dumps(
            {
                "entities": [],
                "relations": [],
                "spatial_envelopes": [],
                "ambiguities": [
                    {
                        "code": "occlusion_uncertain",
                        "message": "the rear object is partly occluded",
                        "entity_refs": [],
                    }
                ],
            }
        )

    class SemanticAmbiguityClient(Client):
        def __init__(self):
            super().__init__()
            self.responses.create = lambda **kwargs: SemanticAmbiguityResponse()

    inference = OpenAIResponsesSceneUnderstandingInference(
        Resolver(), client_factory=lambda **kwargs: SemanticAmbiguityClient()
    )
    assert inference.infer(REQUEST)["ambiguities"][0]["code"] == "occlusion_uncertain"


def test_provider_prompt_assigns_metric_geometry_to_rgbd_composition():
    prompt = OpenAIResponsesSceneUnderstandingInference._system_prompt()
    assert "never emit an ambiguity merely because RGB alone cannot estimate metric" in prompt
    assert "3-D extents" in prompt
    assert "RGB-D composition" in prompt


def test_response_schema_declares_closed_neutral_claim_objects():
    from robotwin20_adapter import SCENE_UNDERSTANDING_JSON_SCHEMA

    entity_schema = SCENE_UNDERSTANDING_JSON_SCHEMA["properties"]["entities"]["items"]
    relation_schema = SCENE_UNDERSTANDING_JSON_SCHEMA["properties"]["relations"]["items"]
    envelope_schema = SCENE_UNDERSTANDING_JSON_SCHEMA["properties"]["spatial_envelopes"]["items"]
    ambiguity_schema = SCENE_UNDERSTANDING_JSON_SCHEMA["properties"]["ambiguities"]["items"]
    assert entity_schema["additionalProperties"] is False
    assert relation_schema["additionalProperties"] is False
    assert envelope_schema["additionalProperties"] is False
    assert ambiguity_schema["additionalProperties"] is False
    assert "actor_id" not in entity_schema["properties"]
    assert ambiguity_schema["properties"]["code"]["enum"] == [
        "entity_identity_uncertain",
        "entity_category_uncertain",
        "entity_count_uncertain",
        "visual_attribute_uncertain",
        "spatial_relation_uncertain",
        "occlusion_uncertain",
    ]


def test_response_schema_is_responses_strict_schema_conformant():
    """Catch omissions that a permissive fake Responses client cannot detect."""
    from robotwin20_adapter import SCENE_UNDERSTANDING_JSON_SCHEMA

    def walk(node):
        assert isinstance(node, dict)
        assert node.get("type") is not None or "anyOf" in node or "$ref" in node
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])
            for child in node["properties"].values():
                walk(child)
        elif node.get("type") == "array":
            walk(node["items"])
        elif "anyOf" in node:
            for child in node["anyOf"]:
                walk(child)

    walk(SCENE_UNDERSTANDING_JSON_SCHEMA)
    unit_schema = (
        SCENE_UNDERSTANDING_JSON_SCHEMA["properties"]
        ["spatial_envelopes"]["items"]["properties"]["unit"]
    )
    assert unit_schema == {"type": "string", "const": "m"}
