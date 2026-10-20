from __future__ import annotations

import pytest

from pick_place_workflow.subtask_executor import PerceptionBinding, SubtaskExecutor, SubtaskSpec


def binding(**updates):
    value = {
        "entity_ref": "entity://reagent-a", "semantic_label": "reagent A", "category": "reagent_bottle",
        "measured_pose": {"position": [0.1, 0.2, 0.3]}, "measured_geometry": {"height_m": 0.18},
        "grasp_candidate_ref": "candidate-set://scene-1/reagent-a",
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


def test_executor_aggregates_five_internal_tools_into_one_subtask_settlement():
    invoker = Invoker(responses())
    result = SubtaskExecutor(invoker).execute(SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding()))
    assert result.status == "completed" and result.outcome_known is True
    assert [item[0] for item in invoker.calls] == ["object.acquire", "manipulation.prepare_held", "object.pour", "manipulation.prepare_held", "object.place"]
    settlement = result.to_node_settlement(task_id="lab-task", revision_id="scene-1")
    assert settlement.status == "completed" and settlement.node_id == "pour-a"
    assert len(result.receipts) == 5


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
