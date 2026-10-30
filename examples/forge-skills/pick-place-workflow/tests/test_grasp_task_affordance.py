from __future__ import annotations

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
                         "process_feature_refs": ["process-feature://bottle/opening"]}}


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
