"""Cross-segment Query facts through real Coordinator persistence, without motion."""

import json
from copy import deepcopy

import pytest
from PhyAgentOS.agent.plan_proposal import compile_task_plan
from PhyAgentOS.agent.planning_context import context_from_task
from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.tools.forge_task import (
    ForgeTaskBeginRevisionTool,
    ForgeTaskContinuePlanTool,
    ForgeTaskMaterializePlanTool,
)
from PhyAgentOS.agent.tools.forge_tool_api import ForgeToolQueryTool
from PhyAgentOS.agent.tools.planning import ForgePlanSelectTool
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.binding import BoundToolSpec, RuntimeBinding
from PhyAgentOS.forge.capability_runtime.manipulation_prepare import (
    MANIPULATION_TOOL_SPEC,
    ManipulationPreparationEndpoint,
    PreparationSnapshot,
)
from PhyAgentOS.forge.manipulation import arm_assignment_digest
from PhyAgentOS.forge.task import AgentTaskCoordinator, ToolExecutionRecord
from PhyAgentOS.planning import (
    NodeSettlement,
    PlanGraph,
    PlanNode,
    ToolSpecPolicy,
    plan_graph_digest,
    plan_node_digest,
    project_tool_spec,
    tool_input_binding_digest,
)
from PhyAgentOS.verification.contracts import TaskVerificationContract

from pick_place_workflow.object_acquire import ACQUIRE_TOOL_SPEC
from pick_place_workflow.object_place import PLACE_TOOL_SPEC
from pick_place_workflow.persistent_runtime import _spec


class QueryClient:
    def __init__(self):
        self.calls = []
        self.endpoint = ManipulationPreparationEndpoint(self)

    def prepare(self, request):
        prepared = tuple({
            "candidate_ref": candidate["candidate_ref"],
            "entity_ref": candidate["entity_ref"],
            "checks": {"kinematic": "pass", "collision": "pass", "workspace": "pass"},
            "evidence": ["artifact://prepare/checks"],
            "qualification": "prepared",
        } for candidate in request["candidates"])
        assignments = []
        for candidate in request["candidates"]:
            assignment = {
                key: request["intent"][key] for key in (
                    "task_id", "revision_id", "node_id", "node_digest", "entity_ref",
                    "observation_ref", "scene_revision", "calibration_ref", "candidate_set_ref",
                    "coordination_mode",
                )
            }
            assignment.update(
                schema_version="paos-arm-assignment/v1", assignment_ref="artifact://prepare/assignment",
                candidate_ref=candidate["candidate_ref"], selected_arm_ids=["arm-A"],
                route_digest="4" * 64, capability_snapshot_ref=request["capability_snapshot_ref"],
                readiness_evidence_ref="artifact://prepare/checks", decision_basis=["test-route"],
                alternatives=[], motion_authorized=False,
            )
            assignment["assignment_digest"] = arm_assignment_digest(assignment)
            assignments.append(assignment)
        return PreparationSnapshot(prepared_candidates=prepared, assignments=tuple(assignments),
                                   destination_ref=request["destination_ref"])

    async def invoke_query_tool(self, tool_id, arguments, **kwargs):
        assert tool_id == "manipulation.prepare"
        self.calls.append(deepcopy(arguments))
        return {"ok": True, "data": self.endpoint.invoke(arguments)}

    def __getattr__(self, name):
        raise AssertionError(f"unexpected Gateway call: {name}")


def completed_grasp_task(tmp_path, *, strict_predecessor=False):
    client = QueryClient()
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=client)
    node = PlanNode(node_id="propose-container", obligation_id="grasp", capability="grasp.propose")
    payload = {
        "task_id": "task-container", "revision_id": "revision-propose",
        "nodes": [node.model_dump(mode="json")],
        "planner_decision_digest": "1" * 64, "policy_snapshot_digest": "2" * 64,
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    task = coordinator.create_task(
        task_description="relocate an observed container",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph, plan_graph_ref="artifact://plans/container/propose",
    )
    spec = _spec(MANIPULATION_TOOL_SPEC)
    if strict_predecessor:
        spec["planning"]["argument_projection_plan"]["source_slots"]["candidates"][
            "source_scope"
        ] = "predecessor"
    prepare_policy = project_tool_spec(spec)
    prepare_tool = BoundToolSpec(
        tool_id=prepare_policy.tool_id, semantics="query",
        spec_sha256=prepare_policy.spec_digest, ready_at_binding=True,
        planning_policy=prepare_policy, input_schema=spec["input_schema"],
    )
    identity = {
        "observation_ref": "observation://scene-1/camera",
        "scene_revision": "scene-1", "frame_id": "camera",
        "calibration_ref": "artifact://scene-1/calibration",
    }
    candidate = {
        "candidate_ref": "candidate://container/1", "entity_ref": "entity://container",
        "grasp_frame": {"frame_id": "camera", "unit": "m", "position_m": [0.1, 0.2, 0.3],
                        "orientation_xyzw": [0.0, 0.0, 0.0, 1.0]},
        "approach_direction": {"frame_id": "camera", "unit": "unitless", "vector": [0, 0, -1]},
        "score": 0.9, "confidence": 0.9, "provenance": ["artifact://scene-1/cloud"],
        "qualification": "proposed",
    }
    facts = {
        "observe": {**identity, "status": "available"},
        "capabilities": {**identity, "status": "available", "snapshot_ref": "artifact://scene-1/arms",
                         "arms": [{"arm_id": "arm-A", "availability": "available"}]},
        "grasp": {**identity, "status": "available", "freshness_ms": 0, "max_age_ms": 1000,
                  "frame": {"frame_id": "camera", "unit": "m"},
                  "candidate_set_ref": "candidate-set://scene-1/camera", "candidates": [candidate]},
    }

    def seed(current):
        current.runtime_binding = RuntimeBinding(
            binding_id="runtime-container", runtime_profile="test", runtime_instance_id="runtime-test",
            gateway_url="http://fake",
        )
        current.active_revision.runtime_binding_id = current.runtime_binding.binding_id
        current.tool_bindings = [prepare_tool]
        for record_id, tool_id in (("observe", "scene.observe"),
                                   ("capabilities", "manipulation.capabilities"),
                                   ("grasp", "grasp.propose")):
            policy = ToolSpecPolicy(tool_id=tool_id, semantics="query", spec_digest="3" * 64,
                                    capabilities=(tool_id,))
            current.tool_bindings.append(BoundToolSpec(
                tool_id=tool_id, semantics="query", spec_sha256=policy.spec_digest,
                ready_at_binding=True, planning_policy=policy,
            ))
            current.active_revision.execution_records.append(ToolExecutionRecord(
                record_id=record_id, revision_id=current.active_revision_id,
                runtime_binding_id=current.runtime_binding.binding_id,
                node_id=node.node_id if record_id == "grasp" else None,
                node_digest=plan_node_digest(node) if record_id == "grasp" else None,
                obligation_id=node.obligation_id if record_id == "grasp" else None,
                input_binding_digest=(
                    tool_input_binding_digest(identity) if record_id == "grasp" else None
                ),
                decision_trace_ref=(
                    "artifact://decision-traces/grasp" if record_id == "grasp" else None
                ),
                tool_id=tool_id, semantics="query", caller_id="test", status="succeeded",
                evidence_refs=[f"tool:{record_id}"], arguments=identity,
                response={"ok": True, "data": facts[record_id]},
            ))

    coordinator.store.update(task.task_id, seed, event_type="test_completed_query")
    coordinator.record_node_settlement(NodeSettlement(
        task_id=task.task_id, revision_id=graph.revision_id, node_id=node.node_id,
        status="completed", scene_revision="scene-1",
    ))
    return coordinator, client, prepare_tool


def prepare_node():
    return PlanNode(
        node_id="prepare-container", obligation_id="prepare", capability="manipulation.prepare",
        input_bindings={
            "entity_ref": "entity://container",
            "binding_ref": "artifact://scene-1/bindings",
            "destination_ref": "destination://container/rack",
            "intent": {"goal": "place the container on its rack",
                       "success_criteria": ["released on rack"],
                       "coordination_mode": "alternative_arm"},
        },
    )


async def continue_prepare(coordinator):
    return json.loads(await ForgeTaskContinuePlanTool(coordinator).execute(
        "task-container",
        nodes=[prepare_node().model_dump(mode="json")],
        evidence_refs=["tool:observe", "tool:capabilities", "tool:grasp"],
        reason="prepare the existing candidates without repeating their Query",
    ))


async def select_prepare(coordinator, *, candidate_record="grasp", capability_record="capabilities"):
    dispatch = AgentComposedDispatch.from_task(
        coordinator.get_task("task-container"),
        context_provider=lambda task_id: context_from_task(coordinator.get_task(task_id)),
    )
    return json.loads(await ForgePlanSelectTool(coordinator, lambda: dispatch).execute(
        task_id="task-container", node_id="prepare-container", tool_id="manipulation.prepare",
        decision_reason="reuse the authorized current-scene candidate set",
        arguments={}, projection_sources={"candidates": {"record_id": candidate_record},
                                           "capabilities": {"record_id": capability_record}},
    ))


@pytest.mark.asyncio
async def test_completed_grasp_can_continue_to_persisted_prepare_and_execute_once(tmp_path, monkeypatch):
    coordinator, client, prepare_tool = completed_grasp_task(tmp_path)
    before = coordinator.get_task("task-container").active_revision.model_dump(mode="json")
    continued = await continue_prepare(coordinator)
    assert continued["ok"] and continued["motion_authorized"] is False
    assert client.calls == []
    task = coordinator.get_task("task-container")
    assert task.active_revision.counts_toward_replan_budget is False
    assert task.active_revision.plan_graph.nodes[0].dependencies == ()
    assert task.active_revision.execution_records == []
    selection = await select_prepare(coordinator)
    assert selection["ok"], selection.get("error", {}).get("message")
    assert selection["data"]["selection"]["tool_arguments"] == {}
    assert client.calls == []
    selected = coordinator.get_task("task-container").active_revision.planning_selections[0]
    saved = selected.resumable_selection.tool_arguments
    assert saved["candidate_set_ref"] == "candidate-set://scene-1/camera"
    assert saved["candidates"][0]["entity_ref"] == "entity://container"
    assert saved["intent"]["allowed_arms"] == ["arm-A"]
    assert saved["intent"]["revision_id"] == task.active_revision_id

    async def bound(*args):
        return prepare_tool

    monkeypatch.setattr(coordinator, "_require_binding_tool", bound)
    result = json.loads(await ForgeToolQueryTool(client, coordinator).execute(
        task_id="task-container", tool_id="manipulation.prepare", arguments={},
        planning_binding=selection["data"]["planning_binding"], use_selected_arguments=True,
    ))
    assert result["ok"], result
    assert result["data"]["status"] == "available", result["data"].get("error")
    assert result["data"]["motion_authorized"] is False
    assert client.calls == [saved]
    task = coordinator.get_task("task-container")
    assert len(task.active_revision.execution_records) == 1
    assert task.active_revision.execution_records[0].node_id == "prepare-container"
    assert task.revisions[0].execution_records[2].model_dump(mode="json") == before["execution_records"][2]
    assert task.revisions[0].node_settlements[0].status == "completed"


@pytest.mark.asyncio
async def test_strict_predecessor_contract_still_rejects_cross_segment_evidence(tmp_path):
    coordinator, client, _ = completed_grasp_task(tmp_path, strict_predecessor=True)
    with pytest.raises(ValueError, match="projection_source_unreachable"):
        await continue_prepare(coordinator)
    assert client.calls == []
    assert len(coordinator.get_task("task-container").revisions) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("omitted", ["grasp", "capabilities"])
async def test_continuation_rejects_omitted_projection_evidence_before_persistence(tmp_path, omitted):
    coordinator, client, _ = completed_grasp_task(tmp_path)
    before = coordinator.get_task("task-container").model_dump(mode="json")
    with pytest.raises(ValueError, match="projection_source_unreachable"):
        await ForgeTaskContinuePlanTool(coordinator).execute(
            "task-container", nodes=[prepare_node().model_dump(mode="json")],
            evidence_refs=[f"tool:{name}" for name in ("observe", "capabilities", "grasp")
                           if name != omitted], reason="reuse selected evidence only",
        )
    assert coordinator.get_task("task-container").model_dump(mode="json") == before
    assert client.calls == []


@pytest.mark.asyncio
async def test_continuation_keeps_inherited_projection_authorization(tmp_path):
    coordinator, client, _ = completed_grasp_task(tmp_path)

    def authorize(current):
        current.active_revision.discovery_evidence_refs = ("tool:grasp", "tool:capabilities")

    coordinator.store.update("task-container", authorize, event_type="test_inherited_authorization")
    result = json.loads(await ForgeTaskContinuePlanTool(coordinator).execute(
        "task-container", nodes=[prepare_node().model_dump(mode="json")],
        evidence_refs=["tool:observe"], reason="keep inherited authorized Query sources",
    ))
    assert result["ok"]
    assert (await select_prepare(coordinator))["ok"]
    assert client.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("full_graph", [False, True])
async def test_recovery_rejects_unselected_sources_without_consuming_attempt(tmp_path, full_graph):
    coordinator, client, _ = completed_grasp_task(tmp_path)
    task = coordinator.get_task("task-container")
    graph = compile_task_plan(
        task, [prepare_node().model_dump(mode="json")], reason="build a valid graph",
        initial_evidence_refs=("tool:observe", "tool:capabilities", "tool:grasp"),
    )
    coordinator.request_replan("task-container", reason="test source replacement")
    before = coordinator.get_task("task-container").model_dump(mode="json")
    submission = ({"plan_graph": graph.model_dump(mode="json"),
                   "plan_graph_ref": "artifact://plans/recovery"} if full_graph else {
                       "nodes": [prepare_node().model_dump(mode="json")],
                   })
    with pytest.raises(ValueError, match="projection_source_unreachable"):
        await ForgeTaskBeginRevisionTool(coordinator).execute(
            "task-container", reason="omit the candidate Query",
            discovery_evidence_refs=["tool:observe", "tool:capabilities"], **submission,
        )
    assert coordinator.get_task("task-container").model_dump(mode="json") == before
    assert client.calls == []


@pytest.mark.asyncio
async def test_full_graph_materialization_rejects_unselected_sources(tmp_path):
    coordinator, client, _ = completed_grasp_task(tmp_path)
    graph = compile_task_plan(
        coordinator.get_task("task-container"), [prepare_node().model_dump(mode="json")],
        reason="build a valid graph",
        initial_evidence_refs=("tool:observe", "tool:capabilities", "tool:grasp"),
    )

    def discovery(current):
        current.active_revision.plan_graph = None
        current.active_revision.node_settlements = []

    coordinator.store.update("task-container", discovery, event_type="test_discovery")
    before = coordinator.get_task("task-container").model_dump(mode="json")
    with pytest.raises(ValueError, match="projection_source_unreachable"):
        await ForgeTaskMaterializePlanTool(coordinator).execute(
            "task-container", plan_graph=graph.model_dump(mode="json"),
            plan_graph_ref="artifact://plans/materialize", reason="omit the candidate Query",
            evidence_refs=["tool:observe", "tool:capabilities"],
        )
    assert coordinator.get_task("task-container").model_dump(mode="json") == before
    assert client.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("inherit", [False, True])
async def test_recovery_preserves_exact_authorized_query_pool(tmp_path, inherit):
    coordinator, client, _ = completed_grasp_task(tmp_path)
    evidence = ("tool:observe", "tool:capabilities", "tool:grasp")
    if inherit:
        def authorize(current):
            current.active_revision.discovery_evidence_refs = evidence

        coordinator.store.update("task-container", authorize, event_type="test_recovery_evidence")
    coordinator.request_replan("task-container", reason="test recovery with valid sources")
    result = json.loads(await ForgeTaskBeginRevisionTool(coordinator).execute(
        "task-container", nodes=[prepare_node().model_dump(mode="json")],
        reason="reuse current-scene Query evidence during recovery",
        discovery_evidence_refs=None if inherit else list(evidence),
    ))
    assert result["ok"]
    assert coordinator.get_task("task-container").active_revision.discovery_evidence_refs == evidence
    assert (await select_prepare(coordinator))["ok"]
    assert client.calls == []


@pytest.mark.asyncio
async def test_continuation_default_pool_survives_coordinator_reload(tmp_path):
    coordinator, client, _ = completed_grasp_task(tmp_path)
    result = json.loads(await ForgeTaskContinuePlanTool(coordinator).execute(
        "task-container", nodes=[prepare_node().model_dump(mode="json")],
        reason="reuse the current trusted pool by default",
    ))
    assert result["ok"]
    restarted = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=client)
    assert (await select_prepare(restarted))["ok"]
    assert restarted.get_task("task-container").active_revision.counts_toward_replan_budget is False
    assert client.calls == []


@pytest.mark.asyncio
async def test_authorized_candidates_keep_graph_local_predecessor_route(tmp_path):
    coordinator, client, _ = completed_grasp_task(tmp_path)
    node = prepare_node().model_copy(update={"dependencies": ("propose-new",)})
    result = json.loads(await ForgeTaskContinuePlanTool(coordinator).execute(
        "task-container", nodes=[PlanNode(
            node_id="propose-new", obligation_id="grasp-new", capability="grasp.propose",
        ).model_dump(mode="json"), node.model_dump(mode="json")],
        evidence_refs=["tool:observe", "tool:capabilities"], reason="consume a new predecessor",
    ))
    assert result["ok"] and result["motion_authorized"] is False
    assert client.calls == []


@pytest.mark.asyncio
async def test_selection_rejects_matching_old_capture_pair(tmp_path):
    coordinator, client, _ = completed_grasp_task(tmp_path)

    def seed_old_capture(current):
        old = []
        for record in current.active_revision.execution_records[1:]:
            copied = record.model_copy(deep=True)
            copied.record_id = "old-" + record.record_id
            copied.evidence_refs = ["tool:" + copied.record_id]
            copied.arguments["observation_ref"] = "observation://scene-1/older-camera"
            copied.response["data"]["observation_ref"] = "observation://scene-1/older-camera"
            if copied.tool_id == "grasp.propose":
                copied.response["data"]["candidate_set_ref"] = "candidate-set://scene-1/older-camera"
            old.append(copied)
        current.active_revision.execution_records[0:0] = old

    coordinator.store.update("task-container", seed_old_capture, event_type="test_old_capture")
    result = json.loads(await ForgeTaskContinuePlanTool(coordinator).execute(
        "task-container", nodes=[prepare_node().model_dump(mode="json")],
        evidence_refs=["tool:observe", "tool:capabilities", "tool:grasp",
                       "tool:old-capabilities", "tool:old-grasp"],
        reason="reuse current Query sources",
    ))
    assert result["ok"]
    selected = await select_prepare(coordinator, candidate_record="old-grasp",
                                    capability_record="old-capabilities")
    assert selected["ok"] is False
    assert "observation" in selected["error"]["message"], selected["error"]
    assert coordinator.get_task("task-container").active_revision.planning_selections == []
    assert client.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_source", ["failed", "wrong_tool", "stale_scene", "old_capture"])
async def test_continuation_does_not_accept_invalid_historical_candidate_queries(tmp_path, invalid_source):
    coordinator, client, _ = completed_grasp_task(tmp_path)

    def invalidate(current):
        grasp = current.active_revision.execution_records[-1]
        if invalid_source == "failed":
            grasp.status = "failed"
        elif invalid_source == "wrong_tool":
            grasp.tool_id = "perception.inspect"
        else:
            field, value = ("scene_revision", "scene-old") if invalid_source == "stale_scene" else (
                "observation_ref", "observation://scene-1/older-camera"
            )
            grasp.arguments[field] = value
            grasp.response["data"][field] = value

    coordinator.store.update("task-container", invalidate, event_type="test_invalid_source")
    expected = "unknown or fabricated refs" if invalid_source == "stale_scene" else (
        "projection_source_unreachable"
    )
    with pytest.raises(ValueError, match=expected):
        await continue_prepare(coordinator)
    assert len(coordinator.get_task("task-container").revisions) == 1
    assert client.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(("invalid_source", "message"), [
    ("unselected", "not authorized"),
    ("failed", "not authorized"),
    ("wrong_tool", "requires Tool grasp.propose"),
    ("stale_scene", "not authorized"),
    ("calibration", "mismatched calibration_ref"),
    ("frame", "mismatched frame_id"),
    ("other_entity", "no entity_ref matching"),
])
async def test_selection_revalidates_cross_segment_sources_before_gateway(tmp_path, invalid_source, message):
    coordinator, client, _ = completed_grasp_task(tmp_path)
    await continue_prepare(coordinator)

    def invalidate(current):
        grasp = current.revisions[0].execution_records[-1]
        if invalid_source == "unselected":
            current.active_revision.discovery_evidence_refs = ("tool:observe", "tool:capabilities")
        elif invalid_source == "failed":
            grasp.status = "failed"
        elif invalid_source == "wrong_tool":
            grasp.tool_id = "perception.inspect"
        elif invalid_source == "stale_scene":
            grasp.arguments["scene_revision"] = "scene-old"
            grasp.response["data"]["scene_revision"] = "scene-old"
        elif invalid_source == "other_entity":
            grasp.response["data"]["candidates"][0]["entity_ref"] = "entity://other-container"
        else:
            field, value = ("calibration_ref", "artifact://scene-1/other-calibration") if (
                invalid_source == "calibration"
            ) else ("frame_id", "other-frame")
            grasp.arguments[field] = value
            grasp.response["data"][field] = value

    coordinator.store.update("task-container", invalidate, event_type="test_source_changed")
    result = await select_prepare(coordinator)
    assert result["ok"] is False
    assert message in result["error"]["message"], result["error"]["message"]
    current = coordinator.get_task("task-container")
    assert current.active_revision.planning_selections == []
    assert current.active_revision.execution_records == []
    assert client.calls == []


@pytest.mark.asyncio
async def test_cross_task_record_and_previous_node_cannot_be_imported_as_dependencies(tmp_path):
    coordinator, client, _ = completed_grasp_task(tmp_path)
    tool = ForgeTaskContinuePlanTool(coordinator)
    node = PlanNode(node_id="prepare-container", obligation_id="prepare", capability="manipulation.prepare")
    with pytest.raises(ValueError, match="unknown or fabricated refs"):
        await tool.execute("task-container", nodes=[node.model_dump(mode="json")],
                           evidence_refs=["tool:other-task-grasp"], reason="use an unrelated record")
    with pytest.raises(ValueError, match="dependencies must name nodes in this submitted segment"):
        await tool.execute("task-container", nodes=[node.model_copy(update={
            "dependencies": ("propose-container",),
        }).model_dump(mode="json")], reason="depend on a prior graph node")
    assert len(coordinator.get_task("task-container").revisions) == 1
    assert client.calls == []


@pytest.mark.asyncio
async def test_next_segment_can_declare_strict_action_chain_without_executing_it(tmp_path):
    coordinator, client, _ = completed_grasp_task(tmp_path)

    def enroll_actions(current):
        for source_spec in (ACQUIRE_TOOL_SPEC, PLACE_TOOL_SPEC):
            spec = _spec(source_spec)
            policy = project_tool_spec(spec)
            assert policy.argument_projection_plan.source_slots
            assert all(source.source_scope == "predecessor"
                       for source in policy.argument_projection_plan.source_slots.values())
            current.tool_bindings.append(BoundToolSpec(
                tool_id=policy.tool_id, semantics="action", spec_sha256=policy.spec_digest,
                ready_at_binding=True, planning_policy=policy, input_schema=spec["input_schema"],
            ))

    coordinator.store.update("task-container", enroll_actions, event_type="test_action_contracts")
    nodes = [prepare_node(), PlanNode(
        node_id="acquire-container", obligation_id="acquire", capability="object.acquire",
        dependencies=("prepare-container",), input_bindings={"entity_ref": "entity://container"},
    ), PlanNode(
        node_id="place-container", obligation_id="place", capability="object.place",
        dependencies=("acquire-container",), input_bindings={
            "entity_ref": "entity://container", "destination_ref": "destination://container/rack",
        },
    )]
    result = json.loads(await ForgeTaskContinuePlanTool(coordinator).execute(
        "task-container", nodes=[node.model_dump(mode="json") for node in nodes],
        evidence_refs=["tool:observe", "tool:capabilities", "tool:grasp"],
        reason="declare the dependent Action chain while waiting for each governed terminal result",
    ))
    assert result["ok"] and result["motion_authorized"] is False
    current = coordinator.get_task("task-container")
    assert len(current.active_revision.plan_graph.nodes) == 3
    assert current.active_revision.execution_records == []
    assert current.active_revision.planning_selections == []
    assert client.calls == []
