from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from robotwin20_adapter import (
    ArtifactPayload,
    Qwen3VLVLLMConfig,
    Qwen3VLVLLMSceneUnderstandingInference,
)
from robotwin20_adapter.qwen3_vl_vllm_scene_understanding import (
    Qwen3VLVLLMContractError,
    Qwen3VLVLLMInferenceError,
    _default_client_factory,
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


class _MultiResolver:
    def resolve(self, ref):
        payloads = {
            "artifact://scene/capture/front/rgb": b"front",
            "artifact://scene/capture/wrist/rgb": b"wrist",
        }
        return ArtifactPayload(payloads[ref], "image/png")


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
                ,
                "finish_reason": "stop",
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


def test_default_local_client_bypasses_environment_proxy(monkeypatch):
    captured = {}
    http_client = object()
    monkeypatch.setattr(
        "robotwin20_adapter.qwen3_vl_vllm_scene_understanding.httpx.Client",
        lambda **kwargs: captured.setdefault("http", (kwargs, http_client))[1],
    )
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(
            OpenAI=lambda **kwargs: captured.setdefault("openai", kwargs) or object()
        ),
    )

    _default_client_factory(api_key="EMPTY", base_url="http://127.0.0.1:8012/v1")

    assert captured["http"][0] == {"trust_env": False}
    assert captured["openai"]["http_client"] is http_client


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
    assert payload["response_format"]["json_schema"]["schema"]["properties"]["relations"]["maxItems"] == 8
    assert payload["response_format"]["json_schema"]["schema"]["properties"]["ambiguities"]["items"]["properties"]["entity_ids"]["minItems"] == 1
    assert payload["response_format"]["json_schema"]["schema"]["properties"]["ambiguities"]["items"]["properties"]["code"]["enum"] == [
        "entity_identity_uncertain", "entity_category_uncertain", "entity_count_uncertain",
        "visual_attribute_uncertain", "spatial_relation_uncertain", "occlusion_uncertain",
    ]
    assert payload["messages"][0]["content"][1]["type"] == "image_url"
    prompt = payload["messages"][0]["content"][0]["text"]
    assert "identifying attributes such as color in the category" in prompt
    assert "open-world semantic scene graph" in prompt
    assert "large or low-contrast physical structures" in prompt
    assert "contact/support, attachment" in prompt
    assert "at most 8 highest-confidence" in prompt
    assert "Never return both inverse directional descriptions" in prompt
    assert "do not return transitive relations" in prompt
    assert "broad uniform background may still be a physical structure" in prompt
    assert "Do not infer metric depth, coordinates, plane equations" in prompt
    assert "absence or occlusion in another view is not by itself an identity ambiguity" in prompt
    assert "return them as separate entities" in prompt
    assert "Never assign multiple source views" in prompt
    assert "never emit an ambiguity with empty entity_ids" in prompt
    assert "observation://scene/camera" not in prompt
    assert "scene-1" not in prompt
    assert client.closed is True


def test_vllm_scene_schema_avoids_xgrammar_unsupported_unique_items():
    client = _Client()
    provider = Qwen3VLVLLMSceneUnderstandingInference(
        _Resolver(), client_factory=lambda **kwargs: client
    )

    provider.infer(REQUEST)

    schema = client.chat.completions.calls[0]["response_format"]["json_schema"]["schema"]

    def collect_unique_items(value):
        if isinstance(value, dict):
            return [value["uniqueItems"]] if "uniqueItems" in value else sum(
                (collect_unique_items(item) for item in value.values()), []
            )
        if isinstance(value, list):
            return sum((collect_unique_items(item) for item in value), [])
        return []

    assert collect_unique_items(schema) == []


def test_vllm_provider_sends_all_views_and_maps_source_view_provenance():
    response = type("Response", (), {"choices": [type("Choice", (), {
        "message": type("Message", (), {"content": json.dumps({
            "entities": [{
                "local_id": "e1", "category": "cube", "attributes": [],
                "confidence": 0.9, "source_view_indexes": [1],
            }],
            "relations": [],
            "ambiguities": [],
        })})()
    })()]})()
    client = _Client()
    client.chat.completions.create = lambda **payload: (client.chat.completions.calls.append(payload) or response)
    provider = Qwen3VLVLLMSceneUnderstandingInference(
        _MultiResolver(), client_factory=lambda **kwargs: client
    )
    request = {
        **REQUEST,
        "artifacts": [
            "artifact://scene/capture/front/rgb",
            "artifact://scene/capture/wrist/rgb",
        ],
    }

    result = provider.infer(request)

    content = client.chat.completions.calls[0]["messages"][0]["content"]
    assert [item["type"] for item in content] == ["text", "image_url", "image_url"]
    assert result["entities"][0]["provenance"] == ["artifact://scene/capture/wrist/rgb"]


def test_vllm_provider_reports_output_token_truncation_explicitly():
    response = type("Response", (), {"choices": [type("Choice", (), {
        "message": type("Message", (), {"content": '{"entities": ['})(),
        "finish_reason": "length",
    })()]})()
    client = _Client()
    client.chat.completions.create = lambda **payload: (
        client.chat.completions.calls.append(payload) or response
    )
    provider = Qwen3VLVLLMSceneUnderstandingInference(
        _Resolver(), client_factory=lambda **kwargs: client
    )

    with pytest.raises(Qwen3VLVLLMInferenceError, match="truncated by the output token limit"):
        provider.infer(REQUEST)


def test_vllm_projection_rejects_missing_multiview_provenance():
    with pytest.raises(Qwen3VLVLLMInferenceError, match="source view provenance"):
        _project_vllm_claims(
            {
                "entities": [{"local_id": "e1", "category": "cube", "attributes": [], "confidence": 0.9}],
                "relations": [],
                "ambiguities": [],
            },
            ["artifact://front/rgb", "artifact://wrist/rgb"],
        )


def test_vllm_projection_rejects_duplicate_multiview_provenance():
    with pytest.raises(Qwen3VLVLLMInferenceError, match="source view provenance"):
        _project_vllm_claims(
            {
                "entities": [{
                    "local_id": "e1",
                    "category": "cube",
                    "attributes": [],
                    "confidence": 0.9,
                    "source_view_indexes": [0, 0],
                }],
                "relations": [],
                "ambiguities": [],
            },
            ["artifact://front/rgb", "artifact://wrist/rgb"],
        )


def test_vllm_projection_rejects_more_than_eight_relations():
    with pytest.raises(Qwen3VLVLLMInferenceError, match="relation count"):
        _project_vllm_claims(
            {
                "entities": [
                    {"local_id": "e1", "category": "cube", "attributes": [], "confidence": 0.9},
                    {"local_id": "e2", "category": "surface", "attributes": [], "confidence": 0.9},
                ],
                "relations": [
                    {
                        "subject_id": "e1",
                        "predicate": f"relation_{index}",
                        "object_id": "e2",
                        "relation_space": "visible",
                        "confidence": 0.9,
                    }
                    for index in range(9)
                ],
                "ambiguities": [],
            },
            REQUEST["artifacts"][0],
        )


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


def test_vllm_config_defaults_to_complete_multiview_output_budget():
    assert Qwen3VLVLLMConfig().max_output_tokens == 1536


def test_vllm_projection_preserves_canonical_semantic_ambiguity():
    result = _project_vllm_claims(
        {
            "entities": [
                {"local_id": "e1", "category": "cube", "attributes": [], "confidence": 0.95}
            ],
            "relations": [],
            "ambiguities": [
                {
                    "code": "entity_identity_uncertain",
                    "message": "foreground object is not identifiable",
                    "entity_ids": ["e0", "e1"],
                }
            ],
        },
        REQUEST["artifacts"][0],
    )

    assert result["ambiguities"] == [
        {
            "code": "entity_identity_uncertain",
            "message": "foreground object is not identifiable",
            "entity_refs": ["entity://e1"],
        }
    ]


def test_vllm_projection_rejects_identity_ambiguity_for_merged_multiview_entity():
    with pytest.raises(Qwen3VLVLLMContractError, match="canonical multi-view entity"):
        _project_vllm_claims(
            {
                "entities": [{
                    "local_id": "e1", "category": "cube", "attributes": [],
                    "confidence": 0.95, "source_view_indexes": [0, 1],
                }],
                "relations": [],
                "ambiguities": [{
                    "code": "entity_identity_uncertain",
                    "message": "cross-view correspondence is unconfirmed",
                    "entity_ids": ["e1"],
                }],
            },
            ["artifact://scene/front/rgb", "artifact://scene/wrist/rgb"],
        )


def test_vllm_projection_filters_overbroad_identity_ambiguity_when_attributes_disambiguate():
    result = _project_vllm_claims(
        {
            "entities": [
                {
                    "local_id": "e1", "category": "cube",
                    "attributes": [{"name": "color", "value": "red", "confidence": 0.95}],
                    "confidence": 0.95, "source_view_indexes": [0, 1],
                },
                {
                    "local_id": "e2", "category": "cube",
                    "attributes": [{"name": "color", "value": "blue", "confidence": 0.95}],
                    "confidence": 0.95, "source_view_indexes": [0, 1],
                },
                {
                    "local_id": "e3", "category": "cube",
                    "attributes": [{"name": "color", "value": "green", "confidence": 0.95}],
                    "confidence": 0.95, "source_view_indexes": [0, 1],
                },
            ],
            "relations": [],
            "ambiguities": [{
                "code": "entity_identity_uncertain",
                "message": "the cube identities are visually similar",
                "entity_ids": ["e1", "e2", "e3"],
            }],
        },
        ["artifact://scene/front/rgb", "artifact://scene/wrist/rgb"],
    )

    assert result["ambiguities"] == []


def test_vllm_projection_keeps_identity_ambiguity_for_duplicate_semantic_signatures():
    result = _project_vllm_claims(
        {
            "entities": [
                {
                    "local_id": "e1", "category": "surface", "attributes": [],
                    "confidence": 0.95, "source_view_indexes": [0, 1],
                },
                {
                    "local_id": "e2", "category": "surface", "attributes": [],
                    "confidence": 0.95, "source_view_indexes": [0, 1],
                },
            ],
            "relations": [],
            "ambiguities": [{
                "code": "entity_identity_uncertain",
                "message": "the surfaces cannot be distinguished",
                "entity_ids": ["e1", "e2"],
            }],
        },
        ["artifact://scene/front/rgb", "artifact://scene/wrist/rgb"],
    )

    assert result["ambiguities"][0]["entity_refs"] == ["entity://e1", "entity://e2"]


def test_vllm_projection_drops_explicit_negative_identity_placeholder():
    result = _project_vllm_claims(
        {
            "entities": [{
                "local_id": "e1", "category": "cube", "attributes": [],
                "confidence": 0.95, "source_view_indexes": [0],
            }],
            "relations": [],
            "ambiguities": [{
                "code": "entity_identity_uncertain",
                "message": "No cross-view identity uncertainty detected.",
                "entity_ids": [],
            }],
        },
        ["artifact://scene/front/rgb", "artifact://scene/wrist/rgb"],
    )

    assert result["ambiguities"] == []


def test_vllm_projection_rejects_unscoped_non_placeholder_identity_ambiguity():
    with pytest.raises(Qwen3VLVLLMContractError, match="must reference a known entity"):
        _project_vllm_claims(
            {
                "entities": [{
                    "local_id": "e1", "category": "cube", "attributes": [],
                    "confidence": 0.95, "source_view_indexes": [0],
                }],
                "relations": [],
                "ambiguities": [{
                    "code": "entity_identity_uncertain",
                    "message": "No clear identity; uncertainty detected.",
                    "entity_ids": [],
                }],
            },
            ["artifact://scene/front/rgb", "artifact://scene/wrist/rgb"],
        )


def test_vllm_projection_rejects_entity_id_used_as_ambiguity_code():
    with pytest.raises(Qwen3VLVLLMContractError, match="semantic contract"):
        _project_vllm_claims(
            {
                "entities": [{"local_id": "e1", "category": "green cube", "attributes": [], "confidence": 0.95}],
                "relations": [],
                "ambiguities": [{"code": "e1", "message": "position unclear", "entity_ids": ["e1"]}],
            },
            REQUEST["artifacts"][0],
        )


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
