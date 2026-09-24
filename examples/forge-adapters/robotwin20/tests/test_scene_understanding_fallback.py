from __future__ import annotations

import pytest

from robotwin20_adapter.qwen3_vl_vllm_lifecycle import Qwen3VLVLLMLifecycleError
from robotwin20_adapter.qwen3_vl_vllm_scene_understanding import (
    Qwen3VLVLLMContractError,
    Qwen3VLVLLMInferenceError,
)
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


class _ReleasableProvider(_Provider):
    def __init__(self, result=None, error=None, release_error=None):
        super().__init__(result=result, error=error)
        self.release_count = 0
        self.release_error = release_error

    def release(self):
        self.release_count += 1
        if self.release_error:
            raise self.release_error


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

    with pytest.raises(SceneUnderstandingFallbackError) as failure:
        route.infer({})
    assert route.last_route is None
    assert route.last_error == "TimeoutError; ConnectionError"
    assert failure.value.provider_error_class == "timeout+transport"
    assert failure.value.retryable is True
    assert route.diagnostic_summary() == {
        "provider_route": "none",
        "provider_error_class": "timeout+transport",
    }


def test_fallback_diagnostic_sink_is_bounded_and_does_not_copy_exception_text():
    events = []
    route = FallbackSceneUnderstandingInference(
        _Provider(error=TimeoutError("secret endpoint")),
        _Provider({"entities": []}),
        primary_name="qwen3-vl-4b-vllm",
        fallback_name="gpt-5.6-sol-high",
        diagnostic_sink=events.append,
    )

    assert route.infer({"observation_ref": "observation://s/c"}) == {"entities": []}
    assert route.diagnostic_summary() == {
        "provider_route": "gpt-5.6-sol-high",
        "provider_error_class": "timeout",
    }
    assert events == [{
        "status": "available",
        "route": "gpt-5.6-sol-high",
        "provider_error_class": "timeout",
        "observation_ref": "observation://s/c",
        "scene_revision": None,
        "elapsed_ms": events[0]["elapsed_ms"],
    }]


def test_lifecycle_only_route_does_not_hide_qwen_inference_failure():
    route = FallbackSceneUnderstandingInference(
        _Provider(error=Qwen3VLVLLMInferenceError("invalid output")),
        _Provider({"entities": [{"entity_ref": "entity://fallback"}]}),
        primary_name="qwen3-vl-4b-vllm",
        fallback_name="gpt-5.6-sol-high",
        fallback_exceptions=(Qwen3VLVLLMLifecycleError,),
        fallback_on_empty=False,
    )

    with pytest.raises(Qwen3VLVLLMInferenceError, match="invalid output"):
        route.infer({})


def test_local_semantic_contract_failure_uses_existing_fallback():
    route = FallbackSceneUnderstandingInference(
        _Provider(error=Qwen3VLVLLMContractError("ambiguity code violated the semantic contract")),
        _Provider({"entities": [{"entity_ref": "entity://fallback"}]}),
        primary_name="qwen3-vl-4b-vllm",
        fallback_name="gpt-6-sol-high",
        fallback_exceptions=(Qwen3VLVLLMLifecycleError, Qwen3VLVLLMContractError),
        fallback_on_empty=False,
    )

    assert route.infer({})["entities"][0]["entity_ref"] == "entity://fallback"
    assert route.last_error_class == "contract"


def test_lifecycle_only_route_uses_gpt_for_lifecycle_failure():
    route = FallbackSceneUnderstandingInference(
        _Provider(error=Qwen3VLVLLMLifecycleError("status unavailable")),
        _Provider({"entities": [{"entity_ref": "entity://fallback"}]}),
        primary_name="qwen3-vl-4b-vllm",
        fallback_name="gpt-5.6-sol-high",
        fallback_exceptions=(Qwen3VLVLLMLifecycleError,),
        fallback_on_empty=False,
    )

    assert route.infer({})["entities"][0]["entity_ref"] == "entity://fallback"
    assert route.last_error == "Qwen3VLVLLMLifecycleError"


def test_release_is_forwarded_only_after_primary_route():
    primary = _ReleasableProvider({"entities": []})
    route = FallbackSceneUnderstandingInference(
        primary,
        _Provider({"entities": [{"entity_ref": "entity://fallback"}]}),
        primary_name="qwen3-vl-4b-vllm",
        fallback_name="gpt-5.6-sol-high",
    )

    assert route.infer({}) == {"entities": []}
    route.release()

    assert primary.release_count == 1


def test_release_does_not_touch_failed_primary_after_fallback():
    primary = _ReleasableProvider(error=Qwen3VLVLLMLifecycleError("down"))
    route = FallbackSceneUnderstandingInference(
        primary,
        _Provider({"entities": [{"entity_ref": "entity://fallback"}]}),
        primary_name="qwen3-vl-4b-vllm",
        fallback_name="gpt-5.6-sol-high",
        fallback_exceptions=(Qwen3VLVLLMLifecycleError,),
    )

    assert route.infer({})["entities"][0]["entity_ref"] == "entity://fallback"
    route.release()

    assert primary.release_count == 0


def test_lifecycle_handoff_failure_uses_gpt_for_same_request():
    primary = _ReleasableProvider(
        {"entities": [{"entity_ref": "entity://qwen"}]},
        release_error=Qwen3VLVLLMLifecycleError("sleep failed"),
    )
    fallback = _Provider({"entities": [{"entity_ref": "entity://fallback"}]})
    route = FallbackSceneUnderstandingInference(
        primary,
        fallback,
        primary_name="qwen3-vl-4b-vllm",
        fallback_name="gpt-5.6-sol-high",
        fallback_exceptions=(Qwen3VLVLLMLifecycleError,),
        fallback_on_empty=False,
    )

    assert route.infer({"observation_ref": "observation://1/head"})["entities"][0]["entity_ref"] == "entity://qwen"
    recovered = route.release_for_request({"observation_ref": "observation://1/head"})

    assert recovered["entities"][0]["entity_ref"] == "entity://fallback"
    assert route.last_route == "gpt-5.6-sol-high"
    assert route.last_error == "Qwen3VLVLLMLifecycleError"
