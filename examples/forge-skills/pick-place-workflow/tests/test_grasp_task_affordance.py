from __future__ import annotations

from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from pick_place_workflow.grasp_task_affordance import (
    GRASP_TASK_AFFORDANCE_PREPARATION_TOOL_SPEC,
    GRASP_TASK_AFFORDANCE_TOOL_SPEC,
    GraspTaskAffordancePreparationEndpoint,
    GraspTaskAffordanceQueryEndpoint,
)


def request(**changes):
    value = {
        "operation": "pour",
        "entity_refs": ["entity://bottle", "entity://beaker"],
        "grasp_candidate_set_ref": "candidate-set://scene/bottle",
        "process_feature_candidate_set_ref": "process-feature-set://scene/entities",
        "selected_process_feature_refs": ["process-feature://bottle/opening", "process-feature://beaker/rim"],
        "observation_ref": "observation://scene/front",
        "scene_revision": "scene",
        "frame_id": "front",
        "calibration_ref": "artifact://calibration/front",
        "freshness_ms": 10,
        "max_age_ms": 1000,
    }
    value.update(changes)
    return value


class Provider:
    def __init__(self, prefix="a", status="available"):
        self.prefix = prefix
        self.status = status
        self.seen = []

    def propose(self, value):
        self.seen.append(value)
        return {
            "candidate_set_ref": f"grasp-affordance-set://{self.prefix}/capture",
            "grasp_candidate_set_ref": value["grasp_candidate_set_ref"],
            "process_feature_candidate_set_ref": value["process_feature_candidate_set_ref"],
            **{key: value[key] for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref")},
            "status": self.status,
            "candidates": [{
                "combination_ref": f"grasp-affordance://{self.prefix}/combo-1",
                "entity_ref": value["entity_refs"][0],
                "grasp_candidate_ref": "candidate://bottle/grasp-2",
                "process_feature_refs": ["process-feature://bottle/opening"],
            }],
        }

    def validate_selection(self, value):
        self.seen.append(value)
        return {"status": self.status, **{key: value[key] for key in (
            "candidate_set_ref", "selected_combination_ref", "process_feature_candidate_set_ref",
            "observation_ref", "scene_revision", "frame_id", "calibration_ref")},
            "selected": {"combination_ref": value["selected_combination_ref"],
                         "grasp_candidate_ref": "candidate://bottle/grasp-2",
                         "process_feature_refs": ["process-feature://bottle/opening"]},
            "qualified_grasp_candidate_refs": [
                "candidate://bottle/grasp-2",
                "candidate://bottle/grasp-5",
            ]}


def test_query_provider_is_replaceable_and_returns_only_opaque_relations():
    first, second = Provider("a"), Provider("b")
    left = GraspTaskAffordanceQueryEndpoint(first).invoke(request())
    right = GraspTaskAffordanceQueryEndpoint(second).invoke(request())
    assert left["status"] == right["status"] == "available"
    assert left["candidates"][0]["combination_ref"] != right["candidates"][0]["combination_ref"]
    assert set(left["candidates"][0]) == {
        "combination_ref", "entity_ref", "grasp_candidate_ref", "process_feature_refs"}
    assert left["motion_authorized"] is False


def test_stale_query_and_preparation_stop_before_provider_or_motion():
    provider = Provider()
    query = GraspTaskAffordanceQueryEndpoint(provider).invoke(request(freshness_ms=1001))
    assert query["status"] == "stale"
    assert provider.seen == []
    prepared = GraspTaskAffordancePreparationEndpoint(provider).invoke({
        **{key: value for key, value in request(freshness_ms=1001).items()
           if key not in {"grasp_candidate_set_ref", "selected_process_feature_refs"}},
        "candidate_set_ref": "grasp-affordance-set://a/capture",
        "selected_combination_ref": "grasp-affordance://a/combo-1",
            "process_feature_candidate_set_ref": "process-feature-set://scene/entities",
    })
    assert prepared["status"] == "stale"
    assert prepared["motion_authorized"] is False
    assert provider.seen == []


def test_ambiguous_provider_selection_remains_non_executable():
    provider = Provider(status="ambiguous")
    query = GraspTaskAffordanceQueryEndpoint(provider).invoke(request())
    assert query["status"] == "ambiguous"
    prepared = GraspTaskAffordancePreparationEndpoint(provider).invoke({
        **{key: value for key, value in request().items()
           if key not in {"grasp_candidate_set_ref", "selected_process_feature_refs"}},
        "candidate_set_ref": query["candidate_set_ref"],
        "selected_combination_ref": query["candidates"][0]["combination_ref"],
            "process_feature_candidate_set_ref": query["process_feature_candidate_set_ref"],
    })
    assert prepared["status"] == "ambiguous"
    assert prepared["motion_authorized"] is False


def test_preparation_projects_selected_first_qualified_grasp_refs_without_motion():
    provider = Provider()
    query = GraspTaskAffordanceQueryEndpoint(provider).invoke(request())
    prepared = GraspTaskAffordancePreparationEndpoint(provider).invoke({
        **{key: value for key, value in request().items()
           if key not in {"grasp_candidate_set_ref", "selected_process_feature_refs"}},
        "candidate_set_ref": query["candidate_set_ref"],
        "selected_combination_ref": query["candidates"][0]["combination_ref"],
        "process_feature_candidate_set_ref": query["process_feature_candidate_set_ref"],
    })

    assert prepared["status"] == "available"
    assert prepared["qualified_grasp_candidate_refs"] == [
        "candidate://bottle/grasp-2",
        "candidate://bottle/grasp-5",
    ]
    assert prepared["selected"]["grasp_candidate_ref"] == prepared[
        "qualified_grasp_candidate_refs"
    ][0]
    assert prepared["motion_authorized"] is False


def test_preparation_rejects_duplicate_or_non_selected_first_qualified_refs():
    class InvalidProvider(Provider):
        def validate_selection(self, value):
            result = super().validate_selection(value)
            result["qualified_grasp_candidate_refs"] = [
                "candidate://bottle/grasp-5",
                "candidate://bottle/grasp-2",
            ]
            return result

    provider = InvalidProvider()
    query = GraspTaskAffordanceQueryEndpoint(provider).invoke(request())
    prepared = GraspTaskAffordancePreparationEndpoint(provider).invoke({
        **{key: value for key, value in request().items()
           if key not in {"grasp_candidate_set_ref", "selected_process_feature_refs"}},
        "candidate_set_ref": query["candidate_set_ref"],
        "selected_combination_ref": query["candidates"][0]["combination_ref"],
        "process_feature_candidate_set_ref": query["process_feature_candidate_set_ref"],
    })

    assert prepared["status"] == "invalid"
    assert prepared["motion_authorized"] is False


def test_tool_specs_keep_provider_details_private_and_require_receipt_sources():
    assert GRASP_TASK_AFFORDANCE_TOOL_SPEC["semantics"] == "query"
    assert GRASP_TASK_AFFORDANCE_TOOL_SPEC["input_schema"]["additionalProperties"] is False
    assert GRASP_TASK_AFFORDANCE_TOOL_SPEC["output_schema"]["properties"]["motion_authorized"] == {"const": False}
    query_requirements = GRASP_TASK_AFFORDANCE_TOOL_SPEC["planning"]["argument_source_requirements"]
    assert [item["when"] for item in query_requirements] == [
        {"operation": "pour"}, {"operation": "stir"}
    ]
    assert all(item["source_tool_id"] == "manipulation.prepare_process_features"
               for item in query_requirements)
    requirements = GRASP_TASK_AFFORDANCE_PREPARATION_TOOL_SPEC["planning"]["argument_source_requirements"]
    assert [item["when"] for item in requirements] == [
        {"operation": "pour"}, {"operation": "stir"}
    ]
    assert all(item["source_tool_id"] == "manipulation.grasp_task_affordances"
               for item in requirements)
    assert all(item["keys"] == ["candidate_set_ref", "selected_combination_ref", "process_feature_candidate_set_ref"]
               for item in requirements)


def preparation_request(**changes):
    value = {key: item for key, item in request().items()
             if key not in {"grasp_candidate_set_ref", "selected_process_feature_refs"}}
    value.update(candidate_set_ref="grasp-affordance-set://a/capture",
                 selected_combination_ref="grasp-affordance://a/combo-1")
    value.update(changes)
    return value


@pytest.mark.parametrize("cause", ["scene", "frame", "age", "provider_identity", "provider_stale"])
def test_preparation_stale_requests_declared_evidence_refresh(cause):
    class CurrentCaptureProvider(Provider):
        def validate_selection(self, value):
            result = super().validate_selection(value)
            if cause == "provider_identity":
                result["calibration_ref"] = "artifact://calibration/current"
            elif cause == "provider_stale":
                result.update(status="stale", error="selected capture is no longer current")
            return result

    arguments = preparation_request()
    if cause in {"scene", "frame"}:
        arguments["scene_revision" if cause == "scene" else "frame_id"] = "different"
    elif cause == "age":
        arguments["freshness_ms"] = 1001
    original = deepcopy(arguments)
    provider = CurrentCaptureProvider()
    result = GraspTaskAffordancePreparationEndpoint(provider).invoke(arguments)

    Draft202012Validator(GRASP_TASK_AFFORDANCE_PREPARATION_TOOL_SPEC["output_schema"]).validate(result)
    assert result["status"] == "stale"
    assert result["failure_owner"] == "evidence"
    assert result["failure_code"] == "grasp_affordance_evidence_stale"
    assert result["world_change_started"] is False and result["outcome_known"] is True
    assert result["retryable_in_revision"] is False and result["requires_replan"] is True
    assert result["recommended_action"] == "refresh_declared_evidence"
    assert result["motion_authorized"] is False and "selected" not in result
    assert all(result[key] == original[key] for key in (
        "candidate_set_ref", "selected_combination_ref", "process_feature_candidate_set_ref",
        "observation_ref", "scene_revision", "frame_id", "calibration_ref"))
    assert arguments == original
    if cause in {"scene", "frame", "age"}:
        assert provider.seen == []
    elif cause == "provider_stale":
        assert result["error"] == "selected capture is no longer current"


@pytest.mark.parametrize("status", ["invalid", "unavailable", "ambiguous", "unexpected", "exception", "missing"])
def test_preparation_non_stale_provider_failure_does_not_request_refresh(status):
    class OtherProvider:
        def validate_selection(self, value):
            if status == "exception":
                raise RuntimeError("provider failed")
            if status == "missing":
                return None
            # Invalid/unavailable providers may return no identity at all.
            return {**(value if status == "ambiguous" else {}), "status": status, "error": "provider diagnostic"}

    result = GraspTaskAffordancePreparationEndpoint(OtherProvider()).invoke(preparation_request())
    assert result["status"] == (status if status in {"invalid", "unavailable", "ambiguous"} else "unavailable")
    assert result["motion_authorized"] is False
    assert "requires_replan" not in result and "recommended_action" not in result
    Draft202012Validator(GRASP_TASK_AFFORDANCE_PREPARATION_TOOL_SPEC["output_schema"]).validate(result)


def test_preparation_invalid_input_does_not_request_refresh():
    provider = Provider()
    result = GraspTaskAffordancePreparationEndpoint(provider).invoke({})
    assert result["status"] == "invalid" and provider.seen == []
    assert "requires_replan" not in result
    Draft202012Validator(GRASP_TASK_AFFORDANCE_PREPARATION_TOOL_SPEC["output_schema"]).validate(result)
