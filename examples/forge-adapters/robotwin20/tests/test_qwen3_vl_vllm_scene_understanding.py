from __future__ import annotations

import json

from robotwin20_adapter import (
    ArtifactPayload,
    Qwen3VLVLLMConfig,
    Qwen3VLVLLMSceneUnderstandingInference,
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
    assert client.closed is True


def test_vllm_config_rejects_non_http_endpoint():
    try:
        Qwen3VLVLLMConfig(api_base="not-a-url").validate()
    except ValueError as exc:
        assert "absolute HTTP(S) URL" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("invalid endpoint must fail closed")
