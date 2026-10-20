from __future__ import annotations

import jsonschema
import pytest
from PhyAgentOS.forge.capability_runtime import ActionAdmission, CapabilityRuntime

from pick_place_workflow.subtask_executor import (
    SUBTASK_TOOL_SPEC,
    PerceptionBinding,
    SubtaskActionEndpoint,
    SubtaskExecutor,
    SubtaskSpec,
)


def binding(**updates):
    value = {
        "entity_ref": "entity://reagent-a", "semantic_label": "reagent A", "category": "reagent_bottle",
        "measured_pose": {"position": [0.1, 0.2, 0.3]}, "measured_geometry": {"height_m": 0.18},
        "grasp_candidate_ref": "candidate-set://scene-1/reagent-a",
        "candidate_set_ref": "candidate-set://scene-1/reagent-a",
        "preparation_ref": "preparation://scene-1/reagent-a",
        "candidate_ref": "candidate://reagent-a/0",
        "capability_snapshot_ref": "artifact://capabilities/lab-v1",
        "assignment_ref": "artifact://assignments/reagent-a",
        "destination_ref": "destination://beaker-1", "destination_pose": {"position": [0.2, 0.2, 0.1]},
        "process_frame": "frame://beaker-1", "observation_ref": "observation://lab/scene-1",
        "scene_revision": "scene-1", "frame_id": "lab-camera-front",
        "calibration_ref": "artifact://calibration/lab-v1", "freshness_ms": 10, "max_age_ms": 1000,
        "confidence": 0.98, "provenance": "artifact://perception/lab-scene-1",
    }
    value.update(updates)
    return PerceptionBinding.model_validate(value)


def responses():
    return {
        "object.acquire": {"status": "succeeded", "outcome_known": True, "possession_state": "holding", "world_change_started": True, "new_scene_revision": "scene-2"},
        "manipulation.prepare_held": {"status": "available", "motion_authorized": False},
        "object.pour": {"status": "succeeded", "outcome_known": True, "possession_state": "holding", "world_change_started": True, "new_scene_revision": "scene-3", "evidence_refs": ["artifact://feedback/pour-1"]},
        "object.place": {"status": "succeeded", "outcome_known": True, "possession_state": "empty", "world_change_started": True, "new_scene_revision": "scene-4", "evidence_refs": ["artifact://feedback/place-1"]},
    }


class Invoker:
    def __init__(self, values):
        self.values, self.calls = values, []

    def invoke(self, tool_id, arguments):
        self.calls.append((tool_id, arguments))
        return dict(self.values[tool_id])


class ImmediateActionEndpoint:
    def __init__(self, result):
        self.result = result

    def admit(self, arguments):
        return ActionAdmission(terminal_result=dict(self.result))


class PendingActionEndpoint(ImmediateActionEndpoint):
    def admit(self, arguments):
        return ActionAdmission(pending_polls=2, terminal_result=dict(self.result))


class ImmediateQueryEndpoint:
    def __init__(self, result):
        self.result = result

    def invoke(self, arguments):
        return dict(self.result)


def runtime_with_subtask_endpoint(refresh_binding=None, *, pending_acquire=False):
    runtime = CapabilityRuntime()
    for tool_id, result in {
        "object.acquire": {"status": "succeeded", "outcome_known": True, "possession_state": "holding", "world_change_started": True, "new_scene_revision": "scene-2"},
        "object.pour": {"status": "succeeded", "outcome_known": True, "possession_state": "holding", "world_change_started": True, "new_scene_revision": "scene-3", "evidence_refs": ["artifact://feedback/pour-1"]},
        "object.place": {"status": "succeeded", "outcome_known": True, "possession_state": "empty", "world_change_started": True, "new_scene_revision": "scene-4", "evidence_refs": ["artifact://feedback/place-1"]},
    }.items():
        endpoint = PendingActionEndpoint(result) if pending_acquire and tool_id == "object.acquire" else ImmediateActionEndpoint(result)
        runtime.register_tool(
            {"tool_id": tool_id, "endpoint_id": tool_id.replace(".", "_"), "operation": tool_id.rsplit(".", 1)[-1], "semantics": "action"},
            endpoint,
        )
    runtime.register_tool(
        {"tool_id": "manipulation.prepare_held", "endpoint_id": "held_preparation", "operation": "prepare", "semantics": "query"},
        ImmediateQueryEndpoint({"status": "available", "motion_authorized": False, "arguments": {}}),
    )
    runtime.register_tool(SUBTASK_TOOL_SPEC, SubtaskActionEndpoint(runtime, refresh_binding))
    return runtime


def test_executor_aggregates_five_internal_tools_into_one_subtask_settlement():
    invoker = Invoker(responses())
    result = SubtaskExecutor(invoker).execute(SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding()))
    assert result.status == "completed" and result.outcome_known is True
    assert [item[0] for item in invoker.calls] == ["object.acquire", "manipulation.prepare_held", "object.pour", "manipulation.prepare_held", "object.place"]
    settlement = result.to_node_settlement(task_id="lab-task", revision_id="scene-1")
    assert settlement.status == "completed" and settlement.node_id == "pour-a"
    assert len(result.receipts) == 5


def test_runtime_action_driver_uses_one_outer_invocation_for_internal_sequence():
    def refresh(current, revision):
        return current.model_copy(update={
            "scene_revision": revision,
            "observation_ref": f"observation://lab/{revision}",
            "candidate_set_ref": f"candidate-set://{revision}/reagent-a",
            "grasp_candidate_ref": f"candidate-set://{revision}/reagent-a",
            "preparation_ref": f"preparation://{revision}/reagent-a",
            "candidate_ref": f"candidate://{revision}/reagent-a/0",
            "assignment_ref": f"artifact://assignments/{revision}/reagent-a",
            "freshness_ms": 0,
        })

    runtime = runtime_with_subtask_endpoint(refresh)
    spec = SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding())
    jsonschema.validate(spec.model_dump(mode="json"), SUBTASK_TOOL_SPEC["input_schema"])
    outer = runtime.start_action(
        "manipulation.execute_subtask",
        spec.model_dump(mode="json"),
        caller_id="paos:task-1:revision-1:record-1",
    )["invocation_id"]
    result = None
    for _ in range(20):
        result = runtime.invocation_result(outer)
        if result["status"] != "pending":
            break
    assert result["status"] == "succeeded"
    assert result["result"]["subtask_result"]["subtask_id"] == "pour-a"
    assert result["result"]["subtask_result"]["status"] == "completed"
    assert len(result["result"]["subtask_result"]["receipts"]) == 5
    assert result["result"]["capability_outcome_summary"]["requires_replan"] is False


def test_runtime_driver_fails_closed_when_scene_revision_changes_without_refresh():
    runtime = runtime_with_subtask_endpoint()
    spec = SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding())
    outer = runtime.start_action(
        "manipulation.execute_subtask", spec.model_dump(mode="json"),
        caller_id="paos:task-1:revision-1:record-1",
    )["invocation_id"]
    for _ in range(10):
        result = runtime.invocation_result(outer)
        if result["status"] != "pending":
            break
    assert result["status"] == "unknown"
    subtask = result["result"]["subtask_result"]
    assert subtask["completed_tool_ids"] == ["object.acquire"]
    assert subtask["recommended_action"] == "refresh_perception_before_motion"


def test_runtime_driver_rejects_refresh_with_stale_motion_candidates():
    def stale_refresh(current, revision):
        return current.model_copy(update={
            "scene_revision": revision,
            "observation_ref": f"observation://lab/{revision}",
            "freshness_ms": 0,
        })

    runtime = runtime_with_subtask_endpoint(stale_refresh)
    spec = SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding())
    outer = runtime.start_action(
        "manipulation.execute_subtask", spec.model_dump(mode="json"),
        caller_id="paos:task-1:revision-1:record-1",
    )["invocation_id"]
    for _ in range(10):
        result = runtime.invocation_result(outer)
        if result["status"] != "pending":
            break
    assert result["status"] == "unknown"
    assert result["result"]["subtask_result"]["error"]["message"] == "refreshed perception reused stale candidate_set_ref"


def test_runtime_outer_cancel_propagates_to_active_internal_invocation():
    runtime = runtime_with_subtask_endpoint(pending_acquire=True)
    spec = SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding())
    outer = runtime.start_action(
        "manipulation.execute_subtask", spec.model_dump(mode="json"),
        caller_id="paos:task-1:revision-1:record-1",
    )["invocation_id"]
    assert runtime.invocation_result(outer)["status"] == "pending"
    assert runtime.cancel_invocation(outer)["accepted"] is True
    result = runtime.invocation_result(outer)
    assert result["status"] == "unknown"
    assert result["result"]["subtask_result"]["status"] == "outcome_unknown"


def test_executor_stops_at_failed_process_without_place():
    values = responses()
    values["object.pour"] = {"status": "failed", "outcome_known": True, "possession_state": "holding", "world_change_started": True}
    invoker = Invoker(values)
    result = SubtaskExecutor(invoker).execute(SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding()))
    assert result.status == "failed" and result.failed_phase == "process"
    assert "object.place" not in [item[0] for item in invoker.calls]


def test_executor_unknown_and_cancel_are_not_success():
    values = responses()
    values["object.pour"] = {"status": "unknown", "outcome_known": False, "possession_state": "uncertain", "world_change_started": True}
    result = SubtaskExecutor(Invoker(values)).execute(SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding()))
    assert result.status == "outcome_unknown"
    assert result.to_node_settlement(task_id="lab-task", revision_id="scene-1").requires_replan is True
    cancelled = SubtaskExecutor(Invoker(responses()), cancel_requested=lambda: True).execute(SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding()))
    assert cancelled.status == "cancelled" and cancelled.receipts == ()


def test_invoker_exception_is_unknown_and_stops_sequence():
    class BrokenInvoker(Invoker):
        def invoke(self, tool_id, arguments):
            self.calls.append((tool_id, arguments))
            if tool_id == "object.pour":
                raise TimeoutError("transport lost after dispatch")
            return dict(self.values[tool_id])

    invoker = BrokenInvoker(responses())
    result = SubtaskExecutor(invoker).execute(SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding()))
    assert result.status == "outcome_unknown"
    assert result.outcome_known is False
    assert result.receipts[-1].status == "unknown"
    assert "object.place" not in [item[0] for item in invoker.calls]


def test_stale_binding_is_rejected_before_internal_tools():
    with pytest.raises(ValueError, match="stale"):
        SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(freshness_ms=1001))
