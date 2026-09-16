from __future__ import annotations

import pytest

from robotwin20_adapter.scene_understanding_fallback import (
    FallbackSceneUnderstandingInference,
    SceneUnderstandingFallbackError,
)


class _Provider:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def infer(self, request):
        if self.error:
            raise self.error
        return self.result


def test_local_provider_is_primary_and_route_is_diagnostic_only():
    route = FallbackSceneUnderstandingInference(
        _Provider({"entities": []}),
        _Provider({"entities": [{"entity_ref": "entity://fallback"}]}),
        primary_name="qwen3-vl-4b-vllm",
        fallback_name="gpt-5.6-sol-high",
    )

    assert route.infer({}) == {"entities": []}
    assert route.last_route == "qwen3-vl-4b-vllm"
    assert route.last_error is None


def test_gpt_fallback_runs_after_local_failure():
    route = FallbackSceneUnderstandingInference(
        _Provider(error=TimeoutError()),
        _Provider({"entities": [{"entity_ref": "entity://fallback"}]}),
        primary_name="qwen3-vl-4b-vllm",
        fallback_name="gpt-5.6-sol-high",
    )

    assert route.infer({})["entities"][0]["entity_ref"] == "entity://fallback"
    assert route.last_route == "gpt-5.6-sol-high"
    assert route.last_error == "TimeoutError"


def test_both_provider_failures_are_bounded():
    route = FallbackSceneUnderstandingInference(
        _Provider(error=TimeoutError()),
        _Provider(error=ConnectionError()),
        primary_name="qwen3-vl-4b-vllm",
        fallback_name="gpt-5.6-sol-high",
    )

    with pytest.raises(SceneUnderstandingFallbackError):
        route.infer({})
    assert route.last_route is None
    assert route.last_error == "TimeoutError; ConnectionError"
