from __future__ import annotations

from PhyAgentOS.agent.argument_sources import resolve_argument_sources
from PhyAgentOS.forge.task import ToolExecutionRecord, _planning_record_status
from PhyAgentOS.planning import derive_ready_nodes, project_tool_spec

from pick_place_workflow.agent_planning import compose_subtask_plan
from pick_place_workflow.process_features import (
    PROCESS_FEATURE_PREPARATION_TOOL_SPEC,
    ProcessFeaturePreparationEndpoint,
    ProcessFeatureQueryEndpoint,
)
from pick_place_workflow.subtask_executor import SUBTASK_TOOL_SPEC, PerceptionBinding, SubtaskSpec


def _request():
    return {
        "operation": "pour",
        "entity_refs": ["entity://bottle", "entity://beaker"],
        "observation_ref": "observation://scene/front",
        "scene_revision": "scene",
        "frame_id": "front",
        "calibration_ref": "artifact://calibration/front",
        "freshness_ms": 10,
        "max_age_ms": 1000,
    }


class _ReplaceableProvider:
    def __init__(self, prefix="one", status="available"):
        self.prefix, self.status = prefix, status
        self.preparation_requests = []

    def propose(self, request):
        return {
            "candidate_set_ref": f"process-feature-set://{self.prefix}/{request['frame_id']}",
            **{key: request[key] for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref")},
            "candidates": [
                {"feature_ref": f"process-feature://{self.prefix}/bottle/rim",
                 "entity_ref": request["entity_refs"][0], "feature_kind": "rim", "feature_role": "opening"},
                {"feature_ref": f"process-feature://{self.prefix}/beaker/rim",
                 "entity_ref": request["entity_refs"][1], "feature_kind": "rim", "feature_role": "opening"},
            ],
        }

    def validate_selection(self, request):
        self.preparation_requests.append(request)
        expected = [f"process-feature://{self.prefix}/bottle/rim", f"process-feature://{self.prefix}/beaker/rim"]
        if request["selected_feature_refs"] != expected:
            return {"status": "ambiguous", "error": "selection differs from current candidates",
                    **{key: request[key] for key in ("candidate_set_ref", "selected_feature_refs", "observation_ref", "scene_revision", "frame_id", "calibration_ref")}}
        return {"status": self.status,
                **{key: request[key] for key in ("candidate_set_ref", "selected_feature_refs", "observation_ref", "scene_revision", "frame_id", "calibration_ref")}}


def test_query_and_preparation_are_provider_replaceable_and_no_motion():
    request = _request()
    first, replacement = _ReplaceableProvider("one"), _ReplaceableProvider("two")
    first_query = ProcessFeatureQueryEndpoint(first).invoke(request)
    second_query = ProcessFeatureQueryEndpoint(replacement).invoke(request)
    assert first_query["status"] == second_query["status"] == "available"
    assert first_query["candidates"][0]["feature_ref"] != second_query["candidates"][0]["feature_ref"]
    selected = [item["feature_ref"] for item in first_query["candidates"]]
    prepared = ProcessFeaturePreparationEndpoint(first).invoke({
        **request,
        "candidate_set_ref": first_query["candidate_set_ref"],
        "selected_feature_refs": selected,
    })
    assert prepared["status"] == "available"
    assert prepared["motion_authorized"] is False
    assert first.preparation_requests[0]["observation_ref"] == request["observation_ref"]


def test_stale_and_ambiguous_feature_selection_stops_before_action_ready():
    provider = _ReplaceableProvider(status="ambiguous")
    query = ProcessFeatureQueryEndpoint(provider).invoke(_request())
    prepared = ProcessFeaturePreparationEndpoint(provider).invoke({
        **_request(),
        "candidate_set_ref": query["candidate_set_ref"],
        "selected_feature_refs": [item["feature_ref"] for item in query["candidates"]],
    })
    assert prepared["status"] == "ambiguous"
    assert prepared["motion_authorized"] is False

    binding = PerceptionBinding.model_validate({
        "entity_ref": "entity://bottle", "semantic_label": "bottle", "category": "reagent_bottle",
        "destination_semantic_label": "beaker", "destination_category": "mixing_vessel",
        "measured_pose": {"position": [0, 0, 0]}, "measured_geometry": {"height_m": 1},
        "grasp_candidate": {"candidate_ref": "candidate://bottle/0", "entity_ref": "entity://bottle"},
        "grasp_candidate_ref": "candidate-set://scene/bottle", "candidate_set_ref": "candidate-set://scene/bottle",
        "candidate_ref": "candidate://bottle/0", "capability_snapshot_ref": "artifact://capabilities/scene",
        "binding_ref": "artifact://bindings/scene", "destination_ref": "destination://beaker",
        "destination_pose": {"position": [0, 0, 0]}, "process_frame": "frame://beaker",
        "observation_ref": "observation://scene/front", "scene_revision": "scene", "frame_id": "front",
        "calibration_ref": "artifact://calibration/front", "freshness_ms": 10, "max_age_ms": 1000,
        "confidence": 1, "provenance": "artifact://bindings/scene",
    })
    plan = compose_subtask_plan("task", "revision", (SubtaskSpec(
        subtask_id="pour", operation="pour", binding=binding,
        parameters={"tilt_rad": 0.7, "hold_s": 1},
    ),), planner_decision_digest="1" * 64, policy_snapshot_digest="2" * 64)
    settlements = {"pour.process_features": "completed", "pour.prepare_process_features": "failed"}
    ready = derive_ready_nodes(plan.graph, settlements, {"observation://scene/front"})
    assert "pour" not in ready
    assert provider.preparation_requests[0]["observation_ref"] == binding.observation_ref

    ambiguous_record = ToolExecutionRecord(
        record_id="prepare-ambiguous", revision_id="revision", tool_id="manipulation.prepare_process_features",
        semantics="query", caller_id="paos:task:revision:prepare-ambiguous", status="succeeded",
        response={"status": "ambiguous", "motion_authorized": False},
    )
    assert _planning_record_status(ambiguous_record) == "failed"
    ambiguous_ready = derive_ready_nodes(
        plan.graph,
        {"pour.process_features": "completed", "pour.prepare_process_features": _planning_record_status(ambiguous_record)},
        {"observation://scene/front"},
    )
    assert "pour" not in ambiguous_ready


def test_expired_evidence_is_rejected_without_provider_or_action_call():
    provider = _ReplaceableProvider()
    endpoint = ProcessFeaturePreparationEndpoint(provider)
    result = endpoint.invoke({
        **_request(), "freshness_ms": 1001,
        "candidate_set_ref": "process-feature-set://one/front",
        "selected_feature_refs": ["process-feature://one/bottle/rim", "process-feature://one/beaker/rim"],
    })
    assert result["status"] == "stale"
    assert provider.preparation_requests == []


def test_agent_selection_copies_exact_refs_from_query_receipt():
    query = ProcessFeatureQueryEndpoint(_ReplaceableProvider()).invoke(_request())
    chosen = [query["candidates"][0]["feature_ref"], query["candidates"][1]["feature_ref"]]
    arguments = resolve_argument_sources(
        {"feature-query-record": ({}, query)},
        {},
        {
            "candidate_set_ref": {"record_id": "feature-query-record", "path": ["response", "candidate_set_ref"]},
            "selected_feature_refs": {
                "record_id": "feature-query-record", "path": ["response", "candidates", 0, "feature_ref"],
                "target_path": ["selected_feature_refs", 0],
            },
            "second_feature_ref": {
                "record_id": "feature-query-record", "path": ["response", "candidates", 1, "feature_ref"],
                "target_path": ["selected_feature_refs", 1],
            },
        },
    )
    assert arguments["candidate_set_ref"] == query["candidate_set_ref"]
    assert arguments["selected_feature_refs"] == chosen


def test_action_selection_must_copy_the_prepared_opaque_refs():
    selected = ["process-feature://provider/bottle/rim", "process-feature://provider/beaker/rim"]
    preparation = {
        "status": "available",
        "candidate_set_ref": "process-feature-set://provider/capture-1",
        "selected_feature_refs": selected,
        "observation_ref": "observation://scene/front",
        "scene_revision": "scene",
        "frame_id": "front",
        "calibration_ref": "artifact://calibration/front",
        "motion_authorized": False,
    }
    action_arguments = resolve_argument_sources(
        {"preparation-record": ({}, preparation)},
        {"operation": "pour"},
        {
            "process_feature_candidate_set_ref": {
                "record_id": "preparation-record", "path": ["response", "candidate_set_ref"],
            },
            "process_feature_refs": {
                "record_id": "preparation-record", "path": ["response", "selected_feature_refs"],
            },
        },
    )
    assert action_arguments["process_feature_candidate_set_ref"] == preparation["candidate_set_ref"]
    assert action_arguments["process_feature_refs"] == selected


def test_tool_specs_declare_operation_scoped_predecessor_ref_sources():
    preparation = project_tool_spec(PROCESS_FEATURE_PREPARATION_TOOL_SPEC)
    action = project_tool_spec(SUBTASK_TOOL_SPEC)
    assert {tuple(item.when.items()) for item in preparation.argument_source_requirements} == {
        (("operation", "pour"),), (("operation", "stir"),),
    }
    assert {item.source_tool_id for item in preparation.argument_source_requirements} == {
        "manipulation.process_features"
    }
    assert all(item.keys == ("candidate_set_ref", "selected_feature_refs") for item in
               preparation.argument_source_requirements)
    assert all(item.source_paths == {"candidate_set_ref": ("response", "candidate_set_ref")} for item in
               preparation.argument_source_requirements)
    assert {item.source_tool_id for item in action.argument_source_requirements} == {
        "manipulation.prepare_grasp_task_affordance"
    }
    assert all(item.keys == ("process_feature_refs", "process_feature_candidate_set_ref",
                             "grasp_task_affordance_candidate_set_ref", "grasp_task_affordance_ref",
                             "selected_grasp_candidate_ref") for item in
               action.argument_source_requirements)
