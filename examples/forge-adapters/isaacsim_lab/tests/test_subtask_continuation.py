import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PhyAgentOS.agent.plan_proposal import compile_task_plan
from PhyAgentOS.agent.planner_plugin import PlanningRequest
from PhyAgentOS.agent.planning_context import context_from_task
from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.planning_loop import (
    EvidenceExecutionContext,
    NodeExecutionContext,
    project_consumer_arguments,
)
from PhyAgentOS.forge.task import ToolExecutionRecord, _tool_result_from_execution
from PhyAgentOS.planning import (
    NodeSettlement,
    build_replan_delta,
    plan_node_digest,
    project_tool_spec,
    settle_node,
    tool_input_binding_digest,
)
from pick_place_workflow.agent_planning import compose_subtask_plan
from pick_place_workflow.grasp_task_affordance import (
    GRASP_TASK_AFFORDANCE_PREPARATION_TOOL_SPEC,
    GRASP_TASK_AFFORDANCE_TOOL_SPEC,
    GraspTaskAffordancePreparationEndpoint,
)
from pick_place_workflow.perception_binding import BindingRequest, PerceptionBindingAdapter
from pick_place_workflow.persistent_runtime import _spec
from pick_place_workflow.process_features import (
    PROCESS_FEATURE_PREPARATION_TOOL_SPEC,
    PROCESS_FEATURE_TOOL_SPEC,
    ProcessFeatureQueryEndpoint,
)
from pick_place_workflow.subtask_executor import SUBTASK_TOOL_SPEC, SubtaskSpec

from isaacsim_lab.subtask_continuation import LabSubtaskContinuation
from isaacsim_lab.visual_perception import LabVisualPerception


def perception(scene, tool_id, arguments):
    identity = {"scene_revision": scene, "observation_ref": f"observation://{scene}/front",
                "calibration_ref": "artifact://calibration/front"}
    frame = {"frame_id": "front", "unit": "m"}
    result = {"status": "available", **identity}
    if tool_id == "scene.observe":
        return {**result, "frame": frame, "freshness_ms": 4,
                "artifacts": [{"ref": f"artifact://captures/{scene}/rgb"}]}
    if tool_id == "scene.understand":
        entities = [{"entity_ref": f"entity://{scene}-{label}", "semantic_label": label,
                     "category": category, "confidence": .98}
                    for label, category in [("R05", "bottle"), ("R03", "bottle"), ("BEAKER", "vessel")]]
        envelopes = [{"entity_ref": item["entity_ref"], "frame_id": "front", "unit": "m",
                      "min_xyz_m": [0., 0., 0.], "max_xyz_m": [.1, .1, .2],
                      "confidence": .9, "provenance": ["artifact://geometry/front"]} for item in entities]
        return {**result, "frame": frame, "entities": entities, "spatial_envelopes": envelopes}
    if tool_id == "grasp.propose":
        entity = arguments["targets"][0]["entity_ref"]
        label = entity.rsplit("-", 1)[-1]
        return {**result, "candidate_set_ref": f"candidate-set://{scene}/{label}",
                "candidates": [{"candidate_ref": f"candidate://{scene}/{label}/0",
                                "entity_ref": entity, "confidence": .9}]}
    assert tool_id == "manipulation.capabilities"
    return {**result, "snapshot_ref": f"artifact://capabilities/{scene}"}


def lab_task(outcome):
    specs = []
    for label, dependencies in [("R05", ()), ("R03", ("R05",))]:
        binding = PerceptionBindingAdapter(
            lambda key, args: perception("before", key, args),
            BindingRequest(sensor_refs=("sensor://front",), source_category="bottle",
                           destination_category="vessel", max_age_ms=1000,
                           source_selector={"semantic_label": label}),
        ).bind()
        specs.append(SubtaskSpec(
            subtask_id=label, operation="pour", binding=binding, depends_on=dependencies,
            parameters={"tilt_rad": 1.0, "hold_s": 2.0},
            semantic_intent={"allowed_arms": ["franka"], "coordination_mode": "single_arm",
                             "goal": f"Pour {label}", "success_criteria": ["Return and release"]},
        ))
    graph = compose_subtask_plan("task", "original", tuple(specs), planner_decision_digest="a" * 64,
                                 policy_snapshot_digest="b" * 64).graph
    recovered = {
        "status": "failed", "outcome_known": True, "world_change_started": True,
        "failure_owner": "execution", "requires_replan": True, "retryable_in_revision": False,
        "recommended_action": "refresh_perception_before_motion", "possession_state": "empty",
        "object_support_state": "on_support", "returned_to_safe_pose": True, "observation_ready": True,
        "new_scene_revision": "after",
    }
    if outcome == "completed":
        facts = {**recovered, "status": "succeeded"}
    elif outcome == "unknown":
        facts = {**recovered, "status": "unknown", "outcome_known": False}
    else:
        facts = {**recovered, "subtask_result": {
            "completed_tool_ids": ["manipulation.prepare", *(["object.pour"] if outcome == "partial" else [])],
            "receipts": [{"tool_id": "object.acquire", "phase": "acquire",
                          "outcome_known": True, "response": recovered}],
        }}
    action = SimpleNamespace(
        record_id="action", revision_id=graph.revision_id, node_id="R05", tool_id="manipulation.execute_subtask",
        semantics="action", terminal=True, status=facts["status"],
        arguments=next(node.input_bindings for node in graph.nodes if node.node_id == "R05"),
        response={"data": {"result": facts}}, evidence_refs=["invocation://R05"],
    )
    original_settlement = NodeSettlement(
        task_id="task", revision_id=graph.revision_id, node_id="R05",
        status="outcome_unknown" if outcome == "unknown" else "completed" if outcome == "completed" else "failed",
        world_change_started=True, requires_replan=outcome != "completed", outcome_known=outcome != "unknown",
    )
    tools = [*PerceptionBindingAdapter._QUERY_SPECS.values(), SUBTASK_TOOL_SPEC, PROCESS_FEATURE_TOOL_SPEC,
             PROCESS_FEATURE_PREPARATION_TOOL_SPEC, GRASP_TASK_AFFORDANCE_TOOL_SPEC,
             GRASP_TASK_AFFORDANCE_PREPARATION_TOOL_SPEC]
    tool_bindings = []
    for spec in tools:
        published = spec if spec is SUBTASK_TOOL_SPEC else _spec(spec)
        tool_bindings.append(SimpleNamespace(tool_id=spec["tool_id"], semantics=spec["semantics"],
                                             input_schema=published["input_schema"],
                                             planning_policy=project_tool_spec(published),
                                             model_dump=lambda **_kwargs: {}))
    original = SimpleNamespace(revision_id=graph.revision_id, plan_graph=graph, execution_records=[action],
                               node_settlements=[original_settlement], discovery_evidence_refs=())
    task = SimpleNamespace(task_id="task", active_revision_id=graph.revision_id, active_revision=original,
                           primary_skill_binding=None, runtime_binding=SimpleNamespace(binding_id="bound"),
                           tool_bindings=tuple(tool_bindings), revisions=[original], execution_records=[action],
                           verification=SimpleNamespace(goal="", success_criteria=()), task_description="Two pours")
    coordinator = SimpleNamespace(
        get_task=lambda _: task, store=Mock(),
        effective_node_settlements=lambda _, revision: next(
            item.node_settlements for item in task.revisions if item.revision_id == revision),
    )
    return task, action, original_settlement, LabSubtaskContinuation(None, None, coordinator, sensor_ref="sensor://front")


def stale_process_feature_settlement(task):
    graph = task.active_revision.plan_graph
    node = next(item for item in graph.nodes if item.node_id == "R03.process_features")
    request = deepcopy(node.input_bindings)
    backend = SimpleNamespace(current_scene_revision=Mock(return_value="before"))
    visual = LabVisualPerception(SimpleNamespace(backend=backend), None, None, segmentation=None,
                                 geometry=None, store=None, grasps=None,
                                 provider_from_tcp=[[1., 0., 0., 0.], [0., 1., 0., 0.],
                                                    [0., 0., 1., 0.], [0., 0., 0., 1.]])
    identity = {key: request[key] for key in ("observation_ref", "scene_revision", "frame_id", "calibration_ref")}
    rim = {"feature_kind": "rim", "feature_role": "opening", "axis_world": [0., 0., 1.],
           "rim_radius_m": .02, "origin_world": [0., 0., .8], "size_m": [.1, .1, .2]}
    visual.observations[request["calibration_ref"]] = {
        ref: {**identity, "entity_ref": ref, "process_feature_candidates": [
            {**rim, "tip_world": [index * .3, 0., 1.]}]}
        for index, ref in enumerate(request["entity_refs"])}
    endpoint = ProcessFeatureQueryEndpoint(visual)
    assert endpoint.invoke(request)["status"] == "available"
    before = deepcopy(visual.process_feature_sets)
    backend.current_scene_revision.return_value = "after"
    response = endpoint.invoke(request)
    assert response["status"] == "stale"
    assert response["candidates"] == [] and response["motion_authorized"] is False
    assert response["scene_revision"] == "before"
    assert visual.process_feature_sets == before

    record = ToolExecutionRecord(
        record_id="stale-r03-features", revision_id=graph.revision_id, node_id=node.node_id,
        node_digest=plan_node_digest(node), obligation_id=node.obligation_id,
        input_binding_digest=tool_input_binding_digest(request), decision_trace_ref="artifact://decision/stale-r03",
        tool_id=node.capability, semantics="query", caller_id="paos:task:stale-r03",
        status="succeeded", arguments=request, response={"ok": True, "data": response},
        evidence_refs=["tool:stale-r03-features"],
    )
    # Use the same result projection and pure settlement as Coordinator replay.
    result = _tool_result_from_execution(task, record)
    assert result.status == "failed" and result.scene_write_behavior == "none"
    assert result.world_change_started is False and result.outcome_known is True
    failed = settle_node(node, result, current_scene_revision="after")
    assert failed.status == "failed"
    task.execution_records.append(record)
    task.active_revision.execution_records.append(record)
    task.active_revision.node_settlements.append(failed)
    return failed



def same_scene_affordance_settlement(task):
    graph = task.active_revision.plan_graph
    node = next(item for item in graph.nodes if item.node_id == "R03.prepare_grasp_task_affordance")
    request = {
        "operation": "pour", "entity_refs": ["entity://after-R03", "entity://after-BEAKER"],
        "candidate_set_ref": "grasp-affordance-set://current",
        "selected_combination_ref": "grasp-affordance://current/one",
        "process_feature_candidate_set_ref": "process-feature-set://current",
        "scene_revision": "after", "observation_ref": "observation://after/front", "frame_id": "front",
        "calibration_ref": "artifact://calibration/front-typo", "freshness_ms": 10, "max_age_ms": 1000,
    }
    node = node.model_copy(update={"input_bindings": request})
    task.active_revision.plan_graph = graph.model_copy(update={
        "nodes": tuple(node if item.node_id == node.node_id else item for item in graph.nodes)})

    class CaptureProvider:
        def validate_selection(self, arguments):
            return {**arguments, "status": "stale", "error": "task-affordance candidate set is stale"}

    response = GraspTaskAffordancePreparationEndpoint(CaptureProvider()).invoke(request)
    assert response["status"] == "stale" and response["requires_replan"] is True
    record = ToolExecutionRecord(
        record_id="stale-r03-affordance", revision_id=graph.revision_id, node_id=node.node_id,
        node_digest=plan_node_digest(node), obligation_id=node.obligation_id,
        input_binding_digest=tool_input_binding_digest(request), decision_trace_ref="artifact://decision/stale-affordance",
        tool_id=node.capability, semantics="query", caller_id="paos:test",
        status="succeeded", arguments=request, response={"ok": True, "data": response},
        evidence_refs=["tool:stale-r03-affordance"],
    )
    failed = settle_node(node, _tool_result_from_execution(task, record), current_scene_revision="after")
    task.execution_records.append(record)
    task.active_revision.execution_records.append(record)
    task.active_revision.node_settlements.append(failed)
    return failed

def method(plugin, task):
    ctx = context_from_task(task, allow_refresh=True)
    return plugin.propose_method_options(request=PlanningRequest(
        task_id=task.task_id, revision_id=task.active_revision_id, task_description=task.task_description,
        scene_revision=ctx.scene_revision, evidence_refs=tuple(ctx.evidence_refs),
        available_capabilities=tuple(tool.tool_id for tool in task.tool_bindings),
    )), ctx


@pytest.mark.parametrize("failure_kind", ["scene_stale", "same_scene_affordance"])
@pytest.mark.parametrize("outcome,label", [("completed", "R03"), ("recovered", "R05"),
                                          ("unknown", None), ("partial", None)])
def test_continuation_consumes_current_receipts_through_published_query_policies(outcome, label, failure_kind):
    task, action, action_settlement, plugin = lab_task(outcome)
    original_action = deepcopy(action)
    original_revision = task.active_revision
    graph = original_revision.plan_graph
    failed = (action_settlement if outcome == "recovered"
              else same_scene_affordance_settlement(task) if failure_kind == "same_scene_affordance"
              else stale_process_feature_settlement(task))
    graph = original_revision.plan_graph
    options, context = method(plugin, task)
    if label is None:
        assert not options
        assert plugin._refresh_spec(task, graph, failed, context) is None
        assert task.execution_records[0] == original_action
        return

    assert context.scene_revision == "after"
    assert "tool:stale-r03-features" not in context.evidence_refs
    if outcome == "completed" and failure_kind == "same_scene_affordance":
        # Same-scene identity failure must use the superclass evidence-refresh path.
        assert plugin._refresh_spec(task, graph, failed, context) is None
    delta = build_replan_delta(graph, failed)
    inputs = dict(graph=graph, settlement=failed, delta=delta, context=context)
    assert asyncio.run(plugin.select_recovery(**inputs)) == "replan"
    recovery = asyncio.run(plugin.propose_replan(**inputs))
    assert recovery.delta.preserve_node_ids == ()
    assert [node.capability for node in recovery.plan_graph.nodes] == ["scene.observe"]

    for index, tool_id in enumerate(PerceptionBindingAdapter._QUERY_SPECS):
        options, context = method(plugin, task)
        option, = options
        node, = option.nodes
        assert node.capability == tool_id
        bound = next(tool for tool in task.tool_bindings if tool.tool_id == tool_id)
        compiled = compile_task_plan(task, [node.model_dump(mode="json")], reason=option.reason,
                                     initial_evidence_refs=option.evidence_refs)
        dispatch = AgentComposedDispatch(compiled, (bound.planning_policy,), context,
                                         input_schemas={tool_id: bound.input_schema})
        if tool_id == "grasp.propose":
            understand = task.execution_records[-1]
            assert understand.evidence_refs[0] in node.required_evidence
            assert node.input_bindings["entity_ref"] == f"entity://after-{label}"
            node_context = NodeExecutionContext(
                task_id=task.task_id, revision_id=compiled.revision_id, node_id=node.node_id,
                capability=node.capability, dependencies=(), required_evidence=node.required_evidence,
                input_bindings=node.input_bindings, scene_revision="after",
                evidence_context=(EvidenceExecutionContext(
                    revision_id=understand.revision_id, record_id=understand.record_id,
                    tool_id=understand.tool_id, status=understand.status, evidence_refs=understand.evidence_refs,
                    arguments=understand.arguments, response=understand.response,
                ),),
            )
            policy = bound.planning_policy
            arguments = project_consumer_arguments(
                node_context, projection=policy.argument_projection, projection_plan=policy.argument_projection_plan,
                literals=node.input_bindings, source_record_id=understand.record_id,
            )
            selection = dispatch.prepare_selection(node_id=node.node_id, tool_id=tool_id,
                                                   decision_reason=option.reason, arguments=arguments)
        else:
            selection = dispatch.prepare_frozen_query_selection(node.node_id)
        assert selection is not None
        arguments = selection["tool_arguments"]
        record_id = f"query-{index}"
        record = SimpleNamespace(
            record_id=record_id, revision_id=compiled.revision_id, node_id=node.node_id, tool_id=tool_id,
            semantics="query", terminal=True, status="succeeded", arguments=arguments,
            response={"data": perception("after", tool_id, arguments)}, evidence_refs=[f"tool:{record_id}"],
        )
        task.active_revision_id = compiled.revision_id
        task.active_revision = SimpleNamespace(revision_id=compiled.revision_id, plan_graph=compiled,
                                               node_settlements=(), execution_records=[record],
                                               discovery_evidence_refs=option.evidence_refs)
        task.revisions.append(task.active_revision)
        task.execution_records.append(record)

    options, context = method(plugin, task)
    option, = options
    compiled = compile_task_plan(task, [node.model_dump(mode="json") for node in option.nodes],
                                 reason=option.reason, initial_evidence_refs=option.evidence_refs)
    assert compiled.nodes[0].produced_evidence == ()
    assert [node.node_id for node in compiled.nodes if node.capability == "manipulation.execute_subtask"] == [label]
    action_node = compiled.nodes[-1]
    assert action_node.input_bindings["binding"]["entity_ref"] == f"entity://after-{label}"
    assert action_node.input_bindings["binding"]["candidate_set_ref"] == f"candidate-set://after/{label}"
    assert action_node.input_bindings["parameters"] == {"tilt_rad": 1.0, "hold_s": 2.0}
    assert action_node.input_bindings["depends_on"] == []
    assert not any(node.capability == "task.verify" for node in compiled.nodes)
    assert task.revisions[0] is original_revision
    assert task.execution_records[0] == original_action
    assert original_revision.node_settlements[0] is action_settlement
    if outcome == "completed":
        assert action_settlement.status == "completed"
        assert all(not node.node_id.startswith("R05") for node in compiled.nodes)


def test_continuation_advances_after_safe_acquire_failure_is_replaced():
    task, _, _, plugin = lab_task("recovered")
    original = task.active_revision.plan_graph

    for label, next_label in [("R05", "R03"), ("R03", None)]:
        options, _ = method(plugin, task)
        assert options[0].method_id == f"lab-{label}"
        node = next(node for node in original.nodes if node.node_id == label)
        replacement = compile_task_plan(task, [node.model_copy(update={
            "dependencies": (), "required_evidence": (),
        }).model_dump(mode="json")], reason=f"Complete {label} in a later revision")
        record = SimpleNamespace(
            record_id=f"completed-{label}", revision_id=replacement.revision_id,
            node_id=label, tool_id="manipulation.execute_subtask", semantics="action",
            terminal=True, status="succeeded", arguments=node.input_bindings,
            response={"data": {"result": {
                "status": "succeeded", "outcome_known": True, "possession_state": "empty",
                "new_scene_revision": f"after-{label}",
            }}},
            evidence_refs=[f"invocation://completed-{label}"],
        )
        settlement = NodeSettlement(
            task_id=task.task_id, revision_id=replacement.revision_id, node_id=label,
            status="completed", world_change_started=True, outcome_known=True,
        )
        task.active_revision_id = replacement.revision_id
        task.active_revision = SimpleNamespace(
            revision_id=replacement.revision_id, plan_graph=replacement, node_settlements=[settlement],
            execution_records=[record], discovery_evidence_refs=(),
        )
        task.revisions.append(task.active_revision)
        task.execution_records.append(record)

        options, _ = method(plugin, task)
        assert [option.method_id for option in options] == ([f"lab-{next_label}"] if next_label else [])
