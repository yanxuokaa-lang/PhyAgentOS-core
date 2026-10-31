from __future__ import annotations

import jsonschema
import pytest
from PhyAgentOS.forge.capability_runtime import (
    MANIPULATION_TOOL_SPEC,
    ActionAdmission,
    CapabilityRuntime,
)

from pick_place_workflow.held_manipulation import PREPARE_HELD_TOOL_SPEC, action_spec
from pick_place_workflow.object_acquire import ACQUIRE_TOOL_SPEC
from pick_place_workflow.object_place import PLACE_TOOL_SPEC
from pick_place_workflow.persistent_runtime import (
    SQLiteAssignmentArtifactStore,
    StoredAssignmentResolver,
)
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
        "destination_semantic_label": "beaker", "destination_category": "beaker",
        "measured_pose": {"position": [0.1, 0.2, 0.3]}, "measured_geometry": {"height_m": 0.18},
        "grasp_candidate": {
            "candidate_ref": "candidate://reagent-a/0", "entity_ref": "entity://reagent-a",
            "grasp_frame": {"frame_id": "lab-camera-front", "unit": "m",
                            "position_m": [0.1, 0.2, 0.3], "orientation_xyzw": [0, 0, 0, 1]},
            "approach_direction": {"frame_id": "lab-camera-front", "unit": "unitless", "vector": [0, 0, -1]},
            "score": 0.9, "confidence": 0.98, "provenance": ["artifact://grasp/reagent-a/0"],
            "qualification": "proposed",
        },
        "grasp_candidate_ref": "candidate-set://scene-1/reagent-a",
        "candidate_set_ref": "candidate-set://scene-1/reagent-a",
        "candidate_ref": "candidate://reagent-a/0",
        "capability_snapshot_ref": "artifact://capabilities/lab-v1",
        "binding_ref": "artifact://perception/lab-scene-1",
        "destination_ref": "destination://beaker-1", "destination_pose": {"position": [0.2, 0.2, 0.1]},
        "process_frame": "frame://beaker-1", "observation_ref": "observation://lab/scene-1",
        "scene_revision": "scene-1", "frame_id": "lab-camera-front",
        "calibration_ref": "artifact://calibration/lab-v1", "freshness_ms": 10, "max_age_ms": 1000,
        "confidence": 0.98, "provenance": "artifact://perception/lab-scene-1",
    }
    value.update(updates)
    return PerceptionBinding.model_validate(value)


def pour_parameters():
    return {"tilt_rad": 0.8, "hold_s": 1.0}


def responses():
    return {
        "manipulation.prepare": {"status": "available", "motion_authorized": False},
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
        if tool_id == "manipulation.prepare":
            candidate = arguments["candidates"][0]
            return {
                "status": "available", "motion_authorized": False,
                "observation_ref": arguments["observation_ref"],
                "scene_revision": arguments["scene_revision"],
                "frame": {"frame_id": arguments["frame_id"], "unit": "m"},
                "calibration_ref": arguments["calibration_ref"],
                "candidate_set_ref": arguments["candidate_set_ref"],
                "preparation_ref": "preparation://scene-1/lab-camera-front",
                "prepared_candidates": [{
                    "candidate_ref": candidate["candidate_ref"], "entity_ref": candidate["entity_ref"],
                    "qualification": "prepared",
                    "checks": {"kinematic": "pass", "collision": "pass", "workspace": "pass"},
                }],
            }
        return dict(self.values[tool_id])


class ImmediateActionEndpoint:
    def __init__(self, result):
        self.result = result

    def admit(self, arguments):
        value = self.result(arguments) if callable(self.result) else self.result
        return ActionAdmission(terminal_result=dict(value))


class PendingActionEndpoint(ImmediateActionEndpoint):
    def admit(self, arguments):
        value = self.result(arguments) if callable(self.result) else self.result
        return ActionAdmission(pending_polls=2, terminal_result=dict(value))


class ImmediateQueryEndpoint:
    def __init__(self, result):
        self.result = result

    def invoke(self, arguments):
        return dict(self.result(arguments) if callable(self.result) else self.result)


class SubtaskPreparationEndpoint:
    def invoke(self, arguments):
        intent = dict(arguments["intent"])
        candidate = arguments["candidates"][0]
        assignment = {
            **{key: intent[key] for key in (
                "task_id", "revision_id", "node_id", "node_digest", "entity_ref",
                "observation_ref", "scene_revision", "calibration_ref", "candidate_set_ref",
                "coordination_mode",
            )},
            "candidate_ref": candidate["candidate_ref"],
            "capability_snapshot_ref": arguments["capability_snapshot_ref"],
            "assignment_ref": "artifact://assignments/task-1/pour-a",
            "selected_arm_ids": ["franka"],
        }
        return {
            "status": "available", "motion_authorized": False,
            "observation_ref": arguments["observation_ref"],
            "scene_revision": arguments["scene_revision"],
            "frame": {"frame_id": arguments["frame_id"], "unit": "m"},
            "calibration_ref": arguments["calibration_ref"],
            "candidate_set_ref": arguments["candidate_set_ref"],
            "preparation_ref": "preparation://scene-1/lab-camera-front",
            "destination_ref": arguments["destination_ref"],
            "prepared_candidates": [{
                "candidate_ref": candidate["candidate_ref"],
                "entity_ref": candidate["entity_ref"],
                "qualification": "prepared",
                "checks": {"kinematic": "pass", "collision": "pass", "workspace": "pass"},
            }],
            "assignments": [assignment],
            "route_arguments": {
                "entity_ref": candidate["entity_ref"],
                "candidate_ref": candidate["candidate_ref"],
                "preparation_ref": "preparation://scene-1/lab-camera-front",
                "scene_revision": arguments["scene_revision"],
                "destination_ref": arguments["destination_ref"],
            },
        }


def runtime_with_subtask_endpoint(refresh_binding=None, *, pending_acquire=False,
                                  validate_production_schemas=False, assignment_store=None):
    runtime = CapabilityRuntime()
    for tool_id, result in {
        "object.acquire": {"status": "succeeded", "outcome_known": True, "possession_state": "holding", "world_change_started": True, "new_scene_revision": "scene-2"},
        "object.pour": {"status": "succeeded", "outcome_known": True, "possession_state": "holding", "world_change_started": True, "new_scene_revision": "scene-3", "evidence_refs": ["artifact://feedback/pour-1"]},
        "object.place": {"status": "succeeded", "outcome_known": True, "possession_state": "empty", "world_change_started": True, "new_scene_revision": "scene-4", "evidence_refs": ["artifact://feedback/place-1"]},
    }.items():
        def terminal(arguments, result=result, tool_id=tool_id):
            value = {**arguments, **result}
            if tool_id == "object.acquire":
                value.update(assignment_ref="artifact://assignments/task-1/pour-a")
            return value

        endpoint = PendingActionEndpoint(terminal) if pending_acquire and tool_id == "object.acquire" else ImmediateActionEndpoint(terminal)
        action_spec = (
            ACQUIRE_TOOL_SPEC if tool_id == "object.acquire" else
            PLACE_TOOL_SPEC if tool_id == "object.place" else
            action_spec_for(tool_id)
        ) if validate_production_schemas else {
            "tool_id": tool_id, "endpoint_id": tool_id.replace(".", "_"),
            "operation": tool_id.rsplit(".", 1)[-1], "semantics": "action",
        }
        runtime.register_tool(
            action_spec,
            endpoint,
        )
    runtime.register_tool(
        MANIPULATION_TOOL_SPEC,
        SubtaskPreparationEndpoint(),
    )
    runtime.register_tool(
        PREPARE_HELD_TOOL_SPEC if validate_production_schemas else {
            "tool_id": "manipulation.prepare_held", "endpoint_id": "held_preparation",
            "operation": "prepare", "semantics": "query",
        },
        ImmediateQueryEndpoint(lambda arguments: {
            "status": "available", "motion_authorized": False,
            "entity_ref": arguments["entity_ref"],
            "arguments": {
                **arguments,
                "scene_revision": "scene-3",
                "preparation_ref": "preparation://scene-3/lab-camera-front",
                "assignment_ref": "artifact://assignments/task-1/pour-a-scene-3",
            },
        }),
    )
    runtime.register_tool(SUBTASK_TOOL_SPEC, SubtaskActionEndpoint(
        runtime, refresh_binding, lambda _caller_id: coordinator_context(),
        assignment_store=assignment_store,
    ))
    return runtime


def action_spec_for(tool_id):
    return action_spec("pour" if tool_id == "object.pour" else "place")


def coordinator_context(**overrides):
    current = binding()
    context = {
        "task_id": "task-1",
        "revision_id": "revision-1",
        "node_id": "pour-a",
        "node_digest": "a" * 64,
        "obligation_id": "pour-a-obligation",
        "input_binding_digest": "b" * 64,
        "decision_trace_ref": "artifact://decisions/pour-a",
        "planning_binding": {
            "node_id": "pour-a", "revision_id": "revision-1",
            "node_digest": "a" * 64, "obligation_id": "pour-a-obligation",
            "input_binding_digest": "b" * 64,
            "decision_trace_ref": "artifact://decisions/pour-a",
        },
        "intent": {
            "version": "manipulation_intent_v2",
            "task_id": "task-1",
            "revision_id": "revision-1",
            "node_id": "pour-a",
            "node_digest": "a" * 64,
            "entity_ref": current.entity_ref,
            "observation_ref": current.observation_ref,
            "scene_revision": current.scene_revision,
            "observation_frame_id": current.frame_id,
            "calibration_ref": current.calibration_ref,
            "candidate_set_ref": current.candidate_set_ref,
            "goal": "pour reagent into the selected vessel",
            "success_criteria": ["process feedback meets the pour criterion"],
            "allowed_arms": ["franka"],
            "coordination_mode": "single_arm",
            "constraints": [],
            "motion_authorized": False,
        },
    }
    context.update(overrides)
    return context


def action_arguments(spec):
    value = spec.model_dump(mode="json", exclude_none=True)
    if spec.operation in {"pour", "stir"}:
        value["process_feature_refs"] = [
            f"process-feature://{spec.binding.scene_revision}/{spec.binding.frame_id}/source/0",
            f"process-feature://{spec.binding.scene_revision}/{spec.binding.frame_id}/destination/0",
        ]
        value["process_feature_candidate_set_ref"] = (
            f"process-feature-set://{spec.binding.scene_revision}/{spec.binding.frame_id}"
        )
    value["intent"] = coordinator_context()["intent"]
    return value


def test_executor_aggregates_five_internal_tools_into_one_subtask_settlement():
    invoker = Invoker(responses())
    result = SubtaskExecutor(invoker).execute(SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters()))
    assert result.status == "completed" and result.outcome_known is True
    assert [item[0] for item in invoker.calls] == ["manipulation.prepare", "object.acquire", "manipulation.prepare_held", "object.pour", "manipulation.prepare_held", "object.place"]
    settlement = result.to_node_settlement(task_id="lab-task", revision_id="scene-1")
    assert settlement.status == "completed" and settlement.node_id == "pour-a"
    assert len(result.receipts) == 6


def test_executor_persists_complete_preparation_artifact_without_rebuilding_route(tmp_path):
    class ArtifactInvoker(Invoker):
        def invoke(self, tool_id, arguments):
            self.calls.append((tool_id, arguments))
            if tool_id == "manipulation.prepare":
                candidate = arguments["candidates"][0]
                return {
                    "status": "available", "motion_authorized": False,
                    "observation_ref": arguments["observation_ref"],
                    "scene_revision": arguments["scene_revision"],
                    "frame": {"frame_id": arguments["frame_id"], "unit": "m"},
                    "calibration_ref": arguments["calibration_ref"],
                    "candidate_set_ref": arguments["candidate_set_ref"],
                    "preparation_ref": "preparation://scene-1/lab-camera-front",
                    "destination_ref": binding().destination_ref,
                    "prepared_candidates": [{
                        "candidate_ref": candidate["candidate_ref"],
                        "entity_ref": candidate["entity_ref"],
                        "qualification": "prepared",
                        "checks": {"kinematic": "pass", "collision": "pass", "workspace": "pass"},
                    }],
                    "assignments": [{
                        **{key: coordinator_context()["intent"][key] for key in (
                            "task_id", "revision_id", "node_id", "node_digest", "entity_ref",
                            "observation_ref", "scene_revision", "calibration_ref", "candidate_set_ref",
                            "coordination_mode",
                        )},
                        "candidate_ref": candidate["candidate_ref"],
                        "capability_snapshot_ref": binding().capability_snapshot_ref,
                        "assignment_ref": "artifact://assignments/task-1/pour-a",
                    }],
                    "route_arguments": {
                        "entity_ref": binding().entity_ref,
                        "candidate_ref": binding().candidate_ref,
                        "preparation_ref": "preparation://scene-1/lab-camera-front",
                        "scene_revision": binding().scene_revision,
                        "destination_ref": binding().destination_ref,
                    },
                }
            return super().invoke(tool_id, arguments)

    store = SQLiteAssignmentArtifactStore(tmp_path / "assignments.sqlite3")
    try:
        result = SubtaskExecutor(
            ArtifactInvoker(responses()), assignment_store=store
        ).execute(SubtaskSpec(
            subtask_id="pour-a", operation="pour", binding=binding(),
            parameters=pour_parameters(),
            trusted_intent=coordinator_context()["intent"],
        ))
        assert result.status == "completed"
        document = store.get("artifact://assignments/task-1/pour-a")
        assert document is not None
        assert document["route_arguments"]["candidate_ref"] == "candidate://reagent-a/0"
    finally:
        store.close()

    reopened = SQLiteAssignmentArtifactStore(tmp_path / "assignments.sqlite3")
    try:
        resolver = StoredAssignmentResolver(reopened)
        acquire_request = {
            **document["route_arguments"],
            "assignment_ref": "artifact://assignments/task-1/pour-a",
        }
        acquire = resolver.resolve_for_task("acquire", acquire_request, task_id="task-1")
        assert acquire["scene_revision"] == "scene-1"

        place_request = {
            **acquire_request,
            "scene_revision": "scene-2",
            "acquire_invocation_ref": "invocation://object-acquire/1",
        }
        place = resolver.resolve_for_task("place", place_request, task_id="task-1")
        assert place["scene_revision"] == "scene-2"
        assert place["destination_ref"] == binding().destination_ref
        with pytest.raises(ValueError, match="another task"):
            resolver.resolve_for_task("place", place_request, task_id="task-2")
    finally:
        reopened.close()


def test_executor_fails_closed_when_store_is_configured_but_route_artifact_is_missing():
    class Store:
        def put(self, _assignment_ref, _document):
            raise AssertionError("incomplete preparation must not be persisted")

    result = SubtaskExecutor(
        Invoker(responses()), assignment_store=Store()
    ).execute(SubtaskSpec(
        subtask_id="pour-a", operation="pour", binding=binding(),
        parameters=pour_parameters(),
        trusted_intent=coordinator_context()["intent"],
    ))
    assert result.status == "failed"
    assert result.failed_phase == "prepare"
    assert result.receipts[0].tool_id == "manipulation.prepare"


def test_executor_projects_latest_held_preparation_into_place():
    class HeldPreparationInvoker(Invoker):
        def invoke(self, tool_id, arguments):
            self.calls.append((tool_id, arguments))
            if tool_id == "manipulation.prepare":
                return Invoker.invoke(self, tool_id, arguments)
            if tool_id == "manipulation.prepare_held":
                return {
                    "status": "available", "motion_authorized": False,
                    "arguments": {
                        **arguments,
                        "scene_revision": "scene-3",
                        "preparation_ref": "preparation://scene-3/lab-camera-front",
                        "assignment_ref": "artifact://assignments/task-1/pour-a-scene-3",
                    },
                }
            return dict(self.values[tool_id])

    invoker = HeldPreparationInvoker(responses())
    result = SubtaskExecutor(invoker).execute(
        SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters())
    )
    assert result.status == "completed"
    place_arguments = next(args for tool_id, args in invoker.calls if tool_id == "object.place")
    assert place_arguments["scene_revision"] == "scene-3"
    assert place_arguments["preparation_ref"] == "preparation://scene-3/lab-camera-front"
    assert place_arguments["assignment_ref"] == "artifact://assignments/task-1/pour-a-scene-3"


def test_runtime_action_driver_uses_one_outer_invocation_for_internal_sequence():
    def refresh(current, revision):
        return current.model_copy(update={
            "scene_revision": revision,
            "observation_ref": f"observation://lab/{revision}",
            "binding_ref": f"artifact://perception/{revision}",
            "candidate_set_ref": f"candidate-set://{revision}/reagent-a",
            "grasp_candidate_ref": f"candidate-set://{revision}/reagent-a",
            "candidate_ref": f"candidate://{revision}/reagent-a/0",
            "freshness_ms": 0,
        })

    runtime = runtime_with_subtask_endpoint(refresh)
    spec = SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters())
    jsonschema.validate(action_arguments(spec), SUBTASK_TOOL_SPEC["input_schema"])
    outer = runtime.start_action(
        "manipulation.execute_subtask",
        action_arguments(spec),
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
    assert len(result["result"]["subtask_result"]["receipts"]) == 6
    assert result["result"]["capability_outcome_summary"]["requires_replan"] is False


def test_runtime_subtask_projects_each_transition_through_production_tool_schemas():
    def refresh(current, revision):
        return current.model_copy(update={
            "scene_revision": revision,
            "observation_ref": f"observation://lab/{revision}",
            "binding_ref": f"artifact://perception/{revision}",
            "candidate_set_ref": f"candidate-set://{revision}/reagent-a",
            "grasp_candidate_ref": f"candidate-set://{revision}/reagent-a",
            "candidate_ref": f"candidate://{revision}/reagent-a/0",
            "freshness_ms": 0,
        })

    runtime = runtime_with_subtask_endpoint(refresh, validate_production_schemas=True)
    spec = SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters())
    jsonschema.validate(action_arguments(spec), SUBTASK_TOOL_SPEC["input_schema"])
    outer = runtime.start_action(
        "manipulation.execute_subtask", action_arguments(spec),
        caller_id="paos:task-1:revision-1:record-1",
    )["invocation_id"]
    result = None
    for _ in range(20):
        result = runtime.invocation_result(outer)
        if result["status"] != "pending":
            break
    assert result["status"] == "succeeded"
    subtask = result["result"]["subtask_result"]
    assert subtask["status"] == "completed"
    assert [receipt["tool_id"] for receipt in subtask["receipts"]] == [
        "manipulation.prepare", "object.acquire", "manipulation.prepare_held",
        "object.pour", "manipulation.prepare_held", "object.place",
    ]
    acquire = subtask["receipts"][1]["response"]
    process = subtask["receipts"][3]["response"]
    place = subtask["receipts"][5]["response"]
    assert acquire["assignment_ref"] == "artifact://assignments/task-1/pour-a"
    assert process["scene_revision"] == "scene-3"
    assert place["assignment_ref"] == "artifact://assignments/task-1/pour-a-scene-3"
    assert place["scene_revision"] == "scene-3"
    assert subtask["scene_revision"] == "scene-4"


def test_stir_contract_requires_and_projects_direction_before_acquire():
    from pick_place_workflow.subtask_executor import SubtaskExecutionContext

    parameters = {
        "radius_m": 0.009, "depth_m": 0.04, "turns": 2.0,
        "duration_s": 4.0, "direction": "cw",
    }
    spec = SubtaskSpec(
        subtask_id="stir-a", operation="stir", binding=binding(), parameters=parameters,
    )
    arguments = action_arguments(spec)
    jsonschema.validate(arguments, SUBTASK_TOOL_SPEC["input_schema"])
    held_prepare = spec.calls()[2]
    held_arguments = SubtaskExecutor._runtime_arguments(
        spec, held_prepare, SubtaskExecutionContext(scene_revision=spec.binding.scene_revision),
    )
    assert held_arguments["parameters"] == parameters
    assert held_arguments["operation"] == "stir"

    with pytest.raises(ValueError, match="invalid stir parameters"):
        SubtaskSpec(subtask_id="stir-a", operation="stir", binding=binding(),
                    parameters={key: value for key, value in parameters.items() if key != "direction"})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**arguments, "parameters": {**parameters, "direction": "left"}},
                            SUBTASK_TOOL_SPEC["input_schema"])


def test_missing_pour_parameters_fail_before_any_internal_tool_call():
    with pytest.raises(ValueError, match="invalid pour parameters"):
        SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding())


def test_subtask_admission_rejects_node_or_intent_mismatch_before_internal_calls():
    runtime = CapabilityRuntime()
    endpoint = SubtaskActionEndpoint(runtime, resolve_context=lambda _caller: coordinator_context())
    endpoint.resolve_context = lambda _caller: coordinator_context(node_id="other-node")
    spec = SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters())
    with pytest.raises(ValueError, match="PlanNode"):
        endpoint.admit_for_caller(action_arguments(spec), caller_id="paos:task-1:revision-1:record-1")

    endpoint.resolve_context = lambda _caller: coordinator_context(
        intent={**coordinator_context()["intent"], "node_digest": "b" * 64}
    )
    with pytest.raises(ValueError, match="node_digest"):
        endpoint.admit_for_caller(action_arguments(spec), caller_id="paos:task-1:revision-1:record-1")

    endpoint.resolve_context = lambda _caller: coordinator_context(
        intent={**coordinator_context()["intent"], "motion_authorized": True}
    )
    with pytest.raises(ValueError, match="no-motion"):
        endpoint.admit_for_caller(action_arguments(spec), caller_id="paos:task-1:revision-1:record-1")

    endpoint.resolve_context = lambda _caller: coordinator_context(
        intent={**coordinator_context()["intent"], "motion_authorized": True}
    )
    with pytest.raises(ValueError, match="no-motion"):
        endpoint.admit_for_caller(action_arguments(spec), caller_id="paos:task-1:revision-1:record-1")


def test_subtask_admission_without_coordinator_resolver_fails_closed():
    runtime = CapabilityRuntime()
    endpoint = SubtaskActionEndpoint(runtime)
    spec = SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters())
    with pytest.raises(ValueError, match="Coordinator context resolver"):
        endpoint.admit_for_caller(action_arguments(spec), caller_id="paos:task-1:revision-1:record-1")


def test_runtime_driver_fails_closed_when_scene_revision_changes_without_refresh():
    runtime = runtime_with_subtask_endpoint()
    spec = SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters())
    outer = runtime.start_action(
        "manipulation.execute_subtask", action_arguments(spec),
        caller_id="paos:task-1:revision-1:record-1",
    )["invocation_id"]
    for _ in range(10):
        result = runtime.invocation_result(outer)
        if result["status"] != "pending":
            break
    assert result["status"] == "unknown"
    subtask = result["result"]["subtask_result"]
    assert subtask["completed_tool_ids"] == ["manipulation.prepare", "object.acquire"]
    assert subtask["recommended_action"] == "refresh_perception_before_motion"


def test_runtime_driver_rejects_refresh_with_stale_motion_candidates():
    def stale_refresh(current, revision):
        return current.model_copy(update={
            "scene_revision": revision,
            "observation_ref": f"observation://lab/{revision}",
            "binding_ref": f"artifact://perception/{revision}",
            "freshness_ms": 0,
        })

    runtime = runtime_with_subtask_endpoint(stale_refresh)
    spec = SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters())
    outer = runtime.start_action(
        "manipulation.execute_subtask", action_arguments(spec),
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
    spec = SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters())
    outer = runtime.start_action(
        "manipulation.execute_subtask", action_arguments(spec),
        caller_id="paos:task-1:revision-1:record-1",
    )["invocation_id"]
    assert runtime.invocation_result(outer)["status"] == "pending"
    assert runtime.cancel_invocation(outer)["accepted"] is True
    result = runtime.invocation_result(outer)
    assert result["status"] == "cancelled"
    assert result["result"]["subtask_result"]["status"] == "cancelled"


def test_executor_stops_at_failed_process_without_place():
    values = responses()
    values["object.pour"] = {"status": "failed", "outcome_known": True, "possession_state": "holding", "world_change_started": True}
    invoker = Invoker(values)
    result = SubtaskExecutor(invoker).execute(SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters()))
    assert result.status == "failed" and result.failed_phase == "process"
    assert "object.place" not in [item[0] for item in invoker.calls]


def test_known_no_motion_route_rejection_requests_agent_replan_without_retry():
    class RejectedPreparationInvoker(Invoker):
        def invoke(self, tool_id, arguments):
            self.calls.append((tool_id, arguments))
            return {
                "status": "unavailable",
                "motion_authorized": False,
                "failure_owner": "runtime_adapter",
                "requires_replan": True,
                "recommended_action": "select_alternative_candidate",
                "outcome_known": True,
                "world_change_started": False,
                "possession_state": "empty",
                "error": {
                    "code": "no_admissible_grasp",
                    "message": "candidate route_collision",
                },
            }

    invoker = RejectedPreparationInvoker(responses())
    result = SubtaskExecutor(invoker).execute(
        SubtaskSpec(
            subtask_id="pour-a", operation="pour", binding=binding(),
            parameters=pour_parameters(),
        )
    )

    assert result.status == "failed"
    assert result.requires_replan is True
    assert result.to_node_settlement(
        task_id="lab-task", revision_id="scene-1",
    ).requires_replan is True
    assert [tool_id for tool_id, _ in invoker.calls] == ["manipulation.prepare"]


@pytest.mark.parametrize("changes", [
    {"world_change_started": True},
    {"possession_state": "holding"},
    {"requires_replan": False},
    {"failure_owner": "runtime_provider"},
    {"error": {"code": "preparation_provider_error", "message": "route_collision"}},
])
def test_prepare_failure_replan_hint_requires_known_zero_motion_route_rejection(changes):
    class RejectedPreparationInvoker(Invoker):
        def invoke(self, tool_id, arguments):
            self.calls.append((tool_id, arguments))
            return {
                "status": "unavailable", "motion_authorized": False,
                "failure_owner": "runtime_adapter", "requires_replan": True,
                "world_change_started": False, "possession_state": "empty",
                "error": {"code": "no_admissible_grasp", "message": "route_collision"},
                **changes,
            }

    result = SubtaskExecutor(RejectedPreparationInvoker(responses())).execute(
        SubtaskSpec(
            subtask_id="pour-a", operation="pour", binding=binding(),
            parameters=pour_parameters(),
        )
    )
    assert result.requires_replan is False


def test_executor_unknown_and_cancel_are_not_success():
    values = responses()
    values["object.pour"] = {"status": "unknown", "outcome_known": False, "possession_state": "uncertain", "world_change_started": True}
    result = SubtaskExecutor(Invoker(values)).execute(SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters()))
    assert result.status == "outcome_unknown"
    assert result.to_node_settlement(task_id="lab-task", revision_id="scene-1").requires_replan is True
    cancelled = SubtaskExecutor(Invoker(responses()), cancel_requested=lambda: True).execute(SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters()))
    assert cancelled.status == "cancelled" and cancelled.receipts == ()


def test_invoker_exception_is_unknown_and_stops_sequence():
    class BrokenInvoker(Invoker):
        def invoke(self, tool_id, arguments):
            self.calls.append((tool_id, arguments))
            if tool_id == "object.pour":
                raise TimeoutError("transport lost after dispatch")
            if tool_id == "manipulation.prepare":
                return Invoker.invoke(self, tool_id, arguments)
            return dict(self.values[tool_id])

    invoker = BrokenInvoker(responses())
    result = SubtaskExecutor(invoker).execute(SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(), parameters=pour_parameters()))
    assert result.status == "outcome_unknown"
    assert result.outcome_known is False
    assert result.receipts[-1].status == "unknown"
    assert "object.place" not in [item[0] for item in invoker.calls]


def test_stale_binding_is_rejected_before_internal_tools():
    with pytest.raises(ValueError, match="stale"):
        SubtaskSpec(subtask_id="pour-a", operation="pour", binding=binding(freshness_ms=1001), parameters=pour_parameters())


def test_preparation_can_select_second_candidate_and_acquire_keeps_that_selection():
    from copy import deepcopy

    from pick_place_workflow.subtask_executor import RuntimeSubtaskDriver, SubtaskExecutionContext
    first = binding().grasp_candidate
    second = deepcopy(first)
    second['candidate_ref'] = 'candidate://reagent-a/second'
    second['grasp_frame']['position_m'][0] += .025
    observed = binding(grasp_candidates=[first, second])
    spec = SubtaskSpec(subtask_id='pour-a', operation='pour', binding=observed, parameters={'tilt_rad': 1., 'hold_s': 1.})
    response = {'motion_authorized': False, 'observation_ref': observed.observation_ref,
                'scene_revision': observed.scene_revision, 'candidate_set_ref': observed.candidate_set_ref,
                'calibration_ref': observed.calibration_ref, 'frame': {'frame_id': observed.frame_id},
                'preparation_ref': 'preparation://selected/second',
                'assignments': [{'candidate_ref': second['candidate_ref']}],
                'prepared_candidates': [{'candidate_ref': second['candidate_ref'], 'entity_ref': observed.entity_ref,
                                          'qualification': 'prepared', 'checks': dict.fromkeys(['kinematic', 'collision', 'workspace'], 'pass')}]}
    context = SubtaskExecutionContext()
    arguments = RuntimeSubtaskDriver._prepared_arguments(spec, response, context)
    assert arguments['candidate_ref'] == second['candidate_ref']
    response['assignments'][0]['candidate_ref'] = 'candidate://reagent-a/unobserved'
    with pytest.raises(ValueError, match='outside'):
        RuntimeSubtaskDriver._prepared_arguments(spec, response, context)
