from __future__ import annotations

import json

import pytest

from robotwin20_adapter import (
    ArtifactPayload,
    Qwen3VLVLLMConfig,
    Qwen3VLVLLMSceneUnderstandingInference,
)
from robotwin20_adapter.qwen3_vl_vllm_scene_understanding import (
    Qwen3VLVLLMInferenceError,
    _project_vllm_claims,
)

REQUEST = {
    "observation_ref": "observation://scene/camera",
    "scene_revision": "scene-1",
    "frame_id": "camera",
    "calibration_ref": "calibration://camera/v1",
    "freshness_ms": 10,
    "max_age_ms": 1000,
    "artifacts": ["artifact://scene/capture/rgb"],
}


class _Resolver:
    def resolve(self, ref):
        assert ref == REQUEST["artifacts"][0]
        return ArtifactPayload(b"png", "image/png")


class _Response:
    choices = [
        type(
            "Choice",
            (),
            {
                "message": type(
                    "Message",
                    (),
                    {
                        "content": json.dumps(
                            {
                                "entities": [{"local_id": "e1", "category": "cup", "attributes": [], "confidence": 0.9}],
                                "relations": [],
                                "ambiguities": [],
                            }
                        )
                    },
                )()
            },
        )()
    ]


class _Completions:
    def __init__(self):
        self.calls = []

    def create(self, **payload):
        self.calls.append(payload)
        return _Response()


class _Client:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": _Completions()})()
        self.closed = False

    def close(self):
        self.closed = True


def test_vllm_provider_uses_openai_compatible_multimodal_schema():
    client = _Client()
    provider = Qwen3VLVLLMSceneUnderstandingInference(
        _Resolver(),
        config=Qwen3VLVLLMConfig(api_key_env="", model="qwen3-vl-4b-awq"),
        client_factory=lambda **kwargs: client,
    )

    result = provider.infer(REQUEST)

    assert result["entities"][0]["provenance"] == REQUEST["artifacts"]
    payload = client.chat.completions.calls[0]
    assert payload["model"] == "qwen3-vl-4b-awq"
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert payload["messages"][0]["content"][1]["type"] == "image_url"
    prompt = payload["messages"][0]["content"][0]["text"]
    assert "identifying attributes such as color in the category" in prompt
    assert "open-world semantic scene graph" in prompt
    assert "large or low-contrast physical structures" in prompt
    assert "contact/support, attachment" in prompt
    assert "broad uniform background may still be a physical structure" in prompt
    assert "Do not infer metric depth, coordinates, plane equations" in prompt
    assert "Do not report an ambiguity solely because" not in prompt
    assert "observation://scene/camera" not in prompt
    assert "scene-1" not in prompt
    assert client.closed is True


def test_vllm_provider_emits_optional_raw_to_projected_diagnostic_without_changing_result():
    events = []
    client = _Client()
    provider = Qwen3VLVLLMSceneUnderstandingInference(
        _Resolver(),
        config=Qwen3VLVLLMConfig(api_key_env="", model="qwen3-vl-4b-awq"),
        client_factory=lambda **kwargs: client,
        diagnostic_sink=events.append,
    )

    result = provider.infer(REQUEST)

    assert result["entities"][0]["category"] == "cup"
    assert len(events) == 1
    assert events[0]["status"] == "available"
    assert events[0]["provider"] == "qwen3-vl-vllm"
    assert events[0]["model"] == "qwen3-vl-4b-awq"
    assert events[0]["raw"]["entities"][0]["category"] == "cup"
    assert events[0]["projected"] == result


def test_vllm_provider_ignores_diagnostic_sink_failures():
    client = _Client()

    def broken_sink(_event):
        raise RuntimeError("diagnostic output is unavailable")

    provider = Qwen3VLVLLMSceneUnderstandingInference(
        _Resolver(),
        config=Qwen3VLVLLMConfig(api_key_env="", model="qwen3-vl-4b-awq"),
        client_factory=lambda **kwargs: client,
        diagnostic_sink=broken_sink,
    )

    assert provider.infer(REQUEST)["entities"][0]["category"] == "cup"


def test_vllm_projection_preserves_color_for_downstream_localization():
    result = _project_vllm_claims(
        {
            "entities": [{
                "local_id": "e1",
                "category": "cube",
                "attributes": [
                    {"name": "color", "value": "red", "confidence": 0.9},
                    {"name": "material", "value": "plastic", "confidence": 0.8},
                ],
                "confidence": 0.95,
            }],
            "relations": [],
            "ambiguities": [],
        },
        REQUEST["artifacts"][0],
    )

    assert result["entities"] == [{
        "entity_ref": "entity://e1",
        "category": "red cube",
        "confidence": 0.9,
        "provenance": REQUEST["artifacts"],
    }]


def test_vllm_projection_does_not_duplicate_color_already_in_category():
    result = _project_vllm_claims(
        {
            "entities": [{
                "local_id": "e1",
                "category": "red cube",
                "attributes": [{"name": "color", "value": "red", "confidence": 0.95}],
                "confidence": 0.95,
            }],
            "relations": [],
            "ambiguities": [],
        },
        REQUEST["artifacts"][0],
    )

    assert result["entities"][0]["category"] == "red cube"


def test_vllm_config_rejects_non_http_endpoint():
    try:
        Qwen3VLVLLMConfig(api_base="not-a-url").validate()
    except ValueError as exc:
        assert "absolute HTTP(S) URL" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("invalid endpoint must fail closed")


def test_vllm_projection_preserves_ambiguity_for_unmodeled_partial_object():
    result = _project_vllm_claims(
        {
            "entities": [
                {"local_id": "e1", "category": "cube", "attributes": [], "confidence": 0.95}
            ],
            "relations": [],
            "ambiguities": [
                {
                    "code": "partial_object",
                    "message": "foreground object is not identifiable",
                    "entity_ids": ["e0", "e1"],
                }
            ],
        },
        REQUEST["artifacts"][0],
    )

    assert result["ambiguities"] == [
        {
            "code": "partial_object",
            "message": "foreground object is not identifiable",
            "entity_refs": ["entity://e1"],
        }
    ]


def test_vllm_projection_still_rejects_unknown_relation_entity():
    with pytest.raises(Qwen3VLVLLMInferenceError, match="relation references unknown entity"):
        _project_vllm_claims(
            {
                "entities": [
                    {
                        "local_id": "e1",
                        "category": "cube",
                        "attributes": [],
                        "confidence": 0.95,
                    }
                ],
                "relations": [
                    {
                        "subject_id": "e1",
                        "predicate": "left_of",
                        "object_id": "e0",
                        "relation_space": "image-plane",
                        "confidence": 0.9,
                    }
                ],
                "ambiguities": [],
            },
            REQUEST["artifacts"][0],
        )
