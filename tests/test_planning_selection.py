from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

import PhyAgentOS.forge.task as forge_task_module
from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.tools.planning import ForgePlanSelectTool
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.binding import BoundToolSpec, RuntimeBinding
from PhyAgentOS.forge.capability_runtime.grasp_proposal import GRASP_TOOL_SPEC
from PhyAgentOS.forge.task import AgentTaskCoordinator, AgentTaskError, AgentTaskStatus
from PhyAgentOS.planning import (
    AdmissionContext,
    PlanGraph,
    PlanningExecutionBinding,
    PlanNode,
    ToolSpecPolicy,
    canonical_sha256,
    plan_graph_digest,
    plan_node_digest,
    tool_input_binding_digest,
)
from PhyAgentOS.verification.contracts import TaskVerificationContract


class _Coordinator:
    def __init__(self):
        self.proposals = []
        self.rejections = []

    def persist_planning_selection(self, proposal):
        self.proposals.append(proposal)
        return {
            "node_id": proposal["node_id"],
            "node_digest": proposal["node_digest"],
            "obligation_id": "observe",
            "input_binding_digest": proposal["input_binding_digest"],
            "decision_trace_ref": "artifact://planning-traces/task-1/revision-1/observe/t1",
            "task_id": proposal["task_id"],
            "revision_id": proposal["revision_id"],
            "scene_revision": proposal["scene_revision"],
            "tool_arguments": proposal["tool_arguments"],
        }

    def record_planning_selection_rejection(self, task_id, **kwargs):
        self.rejections.append((task_id, kwargs))


class _Dispatch:
    graph = SimpleNamespace(task_id="task-1")

    def prepare_selection(self, **kwargs):
        return {
            "task_id": "task-1",
            "revision_id": "revision-1",
            "node_id": kwargs["node_id"],
            "node_digest": "1" * 64,
            "obligation_id": "observe",
            "tool_id": kwargs["tool_id"],
            "candidate_tool_ids": (kwargs["tool_id"],),
            "input_binding_digest": "2" * 64,
            "scene_revision": "scene-1",
            "evidence_refs": (),
            "decision_reason": kwargs["decision_reason"],
            "tool_arguments": kwargs["arguments"],
        }


def test_plan_select_is_control_plane_only_and_returns_binding():
    coordinator = _Coordinator()
    tool = ForgePlanSelectTool(coordinator, lambda: _Dispatch())

    result = json.loads(asyncio.run(tool.execute(
        "task-1", "observe", "scene.observe", {}, "initial observation"
    )))

    assert result["ok"] is True
    assert result["motion_authorized"] is False
    assert result["data"]["planning_binding"]["decision_trace_ref"].startswith("artifact://")
    assert "scene_revision" not in result["data"]["planning_binding"]
    assert result["data"]["selection"]["scene_revision"] == "scene-1"
    assert result["data"]["selection"]["tool_arguments"] == {}
    assert coordinator.proposals[0]["tool_id"] == "scene.observe"


def test_plan_select_rejects_when_task_is_not_active_graph():
    coordinator = _Coordinator()
    tool = ForgePlanSelectTool(coordinator, lambda: None)

    result = json.loads(asyncio.run(tool.execute(
        "task-1", "observe", "scene.observe", {}, "initial observation"
    )))

    assert result["ok"] is False
    assert result["motion_authorized"] is False
    assert result["error"]["code"] == "inactive_plan_graph"
    assert result["error"]["recommended_action"] == "activate_current_task_plan"
    assert result["error"]["rejection_persisted"] is True
    assert coordinator.proposals == []


def test_plan_select_reports_rejection_persistence_failure():
    class FailingCoordinator(_Coordinator):
        def record_planning_selection_rejection(self, task_id, **kwargs):
            raise RuntimeError("task event store unavailable")

    result = json.loads(asyncio.run(ForgePlanSelectTool(
        FailingCoordinator(), lambda: None
    ).execute(
        "task-1", "observe", "scene.observe", {}, "initial observation"
    )))

    assert result["ok"] is False
    assert result["motion_authorized"] is False
    assert result["error"]["code"] == "inactive_plan_graph"
    assert result["error"]["rejection_persisted"] is False
    persistence = result["error"]["persistence_error"]
    assert persistence == {
        "type": "RuntimeError",
        "code": "planning_selection_rejection_not_persisted",
        "failure_owner": "coordinator",
        "message": "task event store unavailable",
        "recommended_action": "read_authoritative_task_state",
    }


def test_replan_budget_exhaustion_runs_terminal_cleanup(tmp_path):
    class Experience:
        def __init__(self):
            self.completed = []

        def schedule_forge_completion(self, task_id):
            self.completed.append(task_id)

    binding_id = "runtime-binding-budget-exhausted"
    experience = Experience()
    task_bindings = {binding_id}
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=object(),
        experience=experience,
        runtime_task_binding_ids=task_bindings,
        max_replans=0,
    )
    task = coordinator.create_task(
        task_description="reject an unbindable historical plan",
        verification=TaskVerificationContract(mode="off"),
    )
    task_id = task.task_id

    def attach_runtime_binding(current):
        current.runtime_binding = RuntimeBinding(
            binding_id=binding_id,
            runtime_profile="fake",
            runtime_instance_id="runtime-budget-exhausted",
            gateway_url="http://fake",
        )
        current.active_revision.runtime_binding_id = binding_id

    coordinator.store.update(
        task_id,
        attach_runtime_binding,
        event_type="test_runtime_binding",
    )

    result = coordinator.record_planning_selection_rejection(
        task_id,
        revision_id=task.active_revision_id,
        node_id="acquire-blue",
        tool_id="object.acquire",
        error={
            "type": "PlanningDispatchError",
            "code": "node_tool_binding_incompatible",
            "failure_owner": "plan_graph",
            "message": "entity_ref is not frozen",
            "retryable_in_revision": False,
            "requires_replan": True,
            "recommended_action": "replace_active_plan_graph",
        },
    )

    assert result.status == AgentTaskStatus.FAILED
    assert binding_id not in task_bindings
    assert experience.completed == [task_id]
    assert result.execution_records == []


def test_prepare_selection_reports_all_missing_runtime_arguments_and_persists_event(tmp_path):
    task_id = "task-missing-candidates"
    revision_id = "revision-missing-candidates"
    node = PlanNode(
        node_id="prepare-green",
        obligation_id="prepare-green",
        capability="manipulation.prepare",
        input_bindings={
            "goal": "prepare green",
            "success_criteria": ["one prepared candidate"],
            "allowed_arms": ["left"],
            "coordination_mode": "single_arm",
        },
    )
    payload = {
        "task_id": task_id,
        "revision_id": revision_id,
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    policy = ToolSpecPolicy(
        tool_id="manipulation.prepare",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("manipulation.prepare",),
        trusted_argument_builder="manipulation_intent_v2",
    )
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=object()
    )
    coordinator.create_task(
        task_description="prepare green",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref=f"artifact://plans/{task_id}/{revision_id}",
    )
    dispatch = AgentComposedDispatch(
        graph, (policy,), AdmissionContext(scene_revision="scene-1")
    )
    tool = ForgePlanSelectTool(coordinator, lambda: dispatch)

    result = json.loads(asyncio.run(tool.execute(
        task_id,
        node.node_id,
        policy.tool_id,
        {},
        "prepare current candidates",
    )))

    assert result["ok"] is False
    assert result["motion_authorized"] is False
    assert result["error"]["code"] == "missing_runtime_arguments"
    assert result["error"]["failure_owner"] == "agent_arguments"
    assert result["error"]["retryable_in_revision"] is True
    assert result["error"]["requires_replan"] is False
    assert result["error"]["task_status"] == "executing"
    assert set(result["error"]["missing_fields"]) == {
        "observation_ref",
        "scene_revision",
        "frame_id",
        "calibration_ref",
        "freshness_ms",
        "max_age_ms",
        "candidate_set_ref",
        "candidates",
        "destination_ref",
        "capability_snapshot_ref",
    }
    current = coordinator.get_task(task_id)
    assert current.execution_records == []
    rejection = coordinator.store.events(task_id)[-1]
    assert rejection["event_type"] == "planning_selection_rejected"
    assert rejection["payload"]["error"]["code"] == "missing_runtime_arguments"
    assert "arguments" not in rejection["payload"]
    assert rejection["payload"]["motion_authorized"] is False


def test_incomplete_grasp_selection_is_rejected_before_tool_record(tmp_path):
    task_id = "task-incomplete-grasp"
    revision_id = "revision-incomplete-grasp"
    node = PlanNode(
        node_id="grasp-green",
        obligation_id="grasp-green",
        capability="grasp.propose",
        input_bindings={"entity_ref": "entity://green"},
    )
    payload = {
        "task_id": task_id,
        "revision_id": revision_id,
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    policy = ToolSpecPolicy(
        tool_id="grasp.propose",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("grasp.propose",),
    )
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=object()
    )
    coordinator.create_task(
        task_description="propose a grasp for green",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref=f"artifact://plans/{task_id}/{revision_id}",
    )
    dispatch = AgentComposedDispatch(
        graph,
        (policy,),
        AdmissionContext(scene_revision="scene-1"),
        input_schemas={"grasp.propose": GRASP_TOOL_SPEC["input_schema"]},
    )

    result = json.loads(asyncio.run(ForgePlanSelectTool(
        coordinator, lambda: dispatch
    ).execute(
        task_id,
        node.node_id,
        policy.tool_id,
        {"entity_ref": "entity://green"},
        "select the current green entity",
    )))

    assert result["ok"] is False
    assert result["motion_authorized"] is False
    assert result["error"]["code"] == "tool_input_schema_invalid"
    assert "targets" in result["error"]["missing_fields"]
    assert coordinator.get_task(task_id).execution_records == []
    event = coordinator.store.events(task_id)[-1]
    assert event["event_type"] == "planning_selection_rejected"
    assert event["payload"]["motion_authorized"] is False


def test_unbindable_historical_selection_enters_bounded_replan(tmp_path):
    task_id = "task-historical-unbindable"
    revision_id = "revision-historical-unbindable"
    node = PlanNode(
        node_id="acquire-blue",
        obligation_id="acquire-blue",
        capability="object.acquire",
    )
    payload = {
        "task_id": task_id,
        "revision_id": revision_id,
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    policy = ToolSpecPolicy(
        tool_id="object.acquire",
        semantics="action",
        spec_digest="3" * 64,
        capabilities=("object.acquire",),
        input_binding_keys=("entity_ref",),
    )
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=object()
    )
    coordinator.create_task(
        task_description="resume a historical graph",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref=f"artifact://plans/{task_id}/{revision_id}",
    )
    dispatch = AgentComposedDispatch(
        graph, (policy,), AdmissionContext(scene_revision="scene-1")
    )

    result = json.loads(asyncio.run(ForgePlanSelectTool(
        coordinator, lambda: dispatch
    ).execute(
        task_id,
        node.node_id,
        policy.tool_id,
        {},
        "select historical node",
    )))

    assert result["error"]["code"] == "node_tool_binding_incompatible"
    assert result["error"]["requires_replan"] is True
    assert result["error"]["retryable_in_revision"] is False
    assert result["error"]["task_status"] == "awaiting_replan"
    current = coordinator.get_task(task_id)
    assert current.status.value == "awaiting_replan"
    assert current.replan_deadline is not None
    assert current.execution_records == []
    assert coordinator.store.events(task_id)[-1]["event_type"] == "planning_selection_rejected"


def test_real_coordinator_persists_context_bound_decision_trace(tmp_path, monkeypatch):
    task_id = "task-real-selection"
    revision_id = "revision-real-selection"
    node = PlanNode(node_id="observe", obligation_id="observe", capability="scene.observe")
    payload = {
        "schema_version": "paos-plan-graph/v1",
        "task_id": task_id,
        "revision_id": revision_id,
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    coordinator.create_task(
        task_description="observe",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-real-selection/revision-real-selection",
    )
    policy = ToolSpecPolicy(
        tool_id="scene.observe",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("scene.observe",),
    )
    context = AdmissionContext(scene_revision="scene-real")
    dispatch = AgentComposedDispatch(graph, (policy,), context)
    proposal = dispatch.prepare_selection(
        node_id="observe",
        tool_id="scene.observe",
        arguments={},
        decision_reason="initial observation",
    )
    atomic_write = forge_task_module.atomic_write_text
    write_attempts = 0

    def fail_first_trace_write(*args, **kwargs):
        nonlocal write_attempts
        write_attempts += 1
        if write_attempts == 1:
            raise OSError("simulated trace write failure")
        return atomic_write(*args, **kwargs)

    monkeypatch.setattr(forge_task_module, "atomic_write_text", fail_first_trace_write)
    with pytest.raises(OSError, match="simulated trace write failure"):
        coordinator.persist_planning_selection(proposal)
    assert len(coordinator.get_task(task_id).active_revision.planning_selections) == 1
    binding = coordinator.persist_planning_selection(proposal)
    assert write_attempts == 2
    duplicate = coordinator.persist_planning_selection(proposal)
    assert duplicate["decision_trace_ref"] == binding["decision_trace_ref"]
    assert len(coordinator.get_task(task_id).active_revision.planning_selections) == 1
    monkeypatch.setattr(coordinator, "pending_planning_selection", lambda *_args, **_kwargs: None)
    concurrent_retry = coordinator.persist_planning_selection(proposal)
    monkeypatch.undo()
    assert concurrent_retry["decision_trace_ref"] == binding["decision_trace_ref"]
    assert len(coordinator.get_task(task_id).active_revision.planning_selections) == 1
    different = dispatch.prepare_selection(
        node_id="observe",
        tool_id="scene.observe",
        arguments={"max_age_ms": 1000},
        decision_reason="different accepted input",
    )
    with pytest.raises(AgentTaskError, match="unconsumed selection"):
        coordinator.persist_planning_selection(different)
    validated = PlanningExecutionBinding.model_validate(
        {key: binding[key] for key in PlanningExecutionBinding.model_fields}
    )
    assert validated.revision_id == revision_id
    assert validated.node_id == "observe"
    trace_path = tmp_path / "artifacts" / "planning-traces" / task_id / revision_id / "observe"
    traces = list(trace_path.glob("*.json"))
    assert len(traces) == 1
    trace = json.loads(traces[0].read_text())
    assert trace["context_digest"] == canonical_sha256(context.model_dump(mode="json"))
    assert trace["selected_tool_id"] == "scene.observe"
    resumable = trace["resumable_selection"]
    assert resumable["tool_id"] == "scene.observe"
    assert resumable["semantics"] == "query"
    assert resumable["tool_arguments"] == {}
    assert resumable["planning_binding"]["decision_trace_ref"] == binding["decision_trace_ref"]
    assert binding["tool_arguments"] == {}
    assert coordinator.pending_planning_selection(
        task_id, "observe", scene_revision="scene-real"
    ) == {
        "task_id": task_id,
        "revision_id": revision_id,
        "node_id": "observe",
        "scene_revision": "scene-real",
        "execution_tool": "forge_tool_query",
        "tool_id": "scene.observe",
        "arguments": {},
        "planning_binding": validated.model_dump(mode="json"),
    }
    assert coordinator.pending_planning_selection(
        task_id, "observe", scene_revision="scene-stale"
    ) is None

    selected_tool = BoundToolSpec(
        tool_id="scene.observe",
        semantics="query",
        spec_sha256="4" * 64,
        ready_at_binding=True,
    )
    with pytest.raises(AgentTaskError, match="arguments do not match"):
        coordinator._append_execution(
            task_id,
            "scene.observe",
            "query",
            {"max_age_ms": 1000},
            tool=selected_tool,
            planning_binding=validated,
        )
    with pytest.raises(AgentTaskError, match="active revision selection"):
        coordinator._append_execution(
            task_id,
            "other.query",
            "query",
            {},
            tool=selected_tool.model_copy(update={"tool_id": "other.query"}),
            planning_binding=validated,
        )
    with pytest.raises(AgentTaskError, match="active revision selection"):
        coordinator._append_execution(
            task_id,
            "scene.observe",
            "action",
            {},
            tool=selected_tool.model_copy(update={"semantics": "action"}),
            planning_binding=validated,
        )
    with pytest.raises(AgentTaskError, match="stale revision"):
        coordinator._append_execution(
            task_id,
            "scene.observe",
            "query",
            {},
            tool=selected_tool,
            planning_binding=validated.model_copy(update={"revision_id": "revision-stale"}),
        )
    assert coordinator.get_task(task_id).active_revision.execution_records == []

    capture_calls = 0

    async def capture_before(_task_id):
        nonlocal capture_calls
        capture_calls += 1

    monkeypatch.setattr(coordinator, "_capture_before", capture_before)
    with pytest.raises(AgentTaskError, match="active revision selection"):
        asyncio.run(
            coordinator.start_action(
                task_id,
                "scene.observe",
                {},
                planning_binding=validated,
            )
        )
    assert capture_calls == 0

    class QueryClient:
        async def invoke_query_tool(self, *_args, **_kwargs):
            return {"ok": True, "data": {"status": "available"}}

    coordinator.client = QueryClient()
    asyncio.run(coordinator.invoke_query(
        task_id,
        "scene.observe",
        {},
        planning_binding=validated,
    ))
    assert coordinator.pending_planning_selection(
        task_id, "observe", scene_revision="scene-real"
    ) is None


def test_planning_node_accepts_only_one_execution_record(tmp_path):
    task_id = "task-one-execution"
    revision_id = "revision-one-execution"
    node = PlanNode(node_id="observe", obligation_id="observe", capability="scene.observe")
    payload = {
        "task_id": task_id,
        "revision_id": revision_id,
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object())
    coordinator.create_task(
        task_description="observe once",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-one-execution/revision-one-execution",
    )
    binding = PlanningExecutionBinding(
        node_id="observe",
        node_digest=plan_node_digest(node),
        obligation_id="observe",
        input_binding_digest=tool_input_binding_digest({}),
        decision_trace_ref="artifact://planning-traces/legacy/observe/one",
    )
    tool = BoundToolSpec(
        tool_id="scene.observe",
        semantics="query",
        spec_sha256="4" * 64,
        ready_at_binding=True,
    )
    coordinator._append_execution(
        task_id,
        "scene.observe",
        "query",
        {},
        tool=tool,
        planning_binding=binding,
    )
    with pytest.raises(AgentTaskError, match="already has an execution record"):
        coordinator._append_execution(
            task_id,
            "scene.observe",
            "query",
            {},
            tool=tool,
            planning_binding=binding,
        )


def test_prepare_selection_builds_coordinator_owned_manipulation_intent():
    node = PlanNode(
        node_id="prepare-green",
        obligation_id="prepare-green",
        capability="manipulation.prepare",
        input_bindings={"entity_ref": "entity://green"},
    )
    payload = {
        "task_id": "task-prepare",
        "revision_id": "revision-prepare",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    policy = ToolSpecPolicy(
        tool_id="manipulation.prepare",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("manipulation.prepare",),
        trusted_argument_builder="manipulation_intent_v2",
    )
    dispatch = AgentComposedDispatch(
        graph, (policy,), AdmissionContext(scene_revision="scene-1")
    )
    arguments = {
        "observation_ref": "observation://scene-1/camera",
        "scene_revision": "scene-1",
        "frame_id": "camera",
        "calibration_ref": "artifact://calibration/camera",
        "freshness_ms": 0,
        "max_age_ms": 1000,
        "candidate_set_ref": "candidate-set://scene-1/camera",
        "candidates": [{"entity_ref": "entity://green"}],
        "destination_ref": "destination://targets/middle",
        "capability_snapshot_ref": "artifact://capabilities/current",
        "intent": {
            "goal": "place green in the middle",
            "success_criteria": ["green reaches the resolved destination"],
            "allowed_arms": ["left"],
            "coordination_mode": "single_arm",
            "constraints": ["collision free"],
        },
    }

    proposal = dispatch.prepare_selection(
        node_id=node.node_id,
        tool_id=policy.tool_id,
        arguments=arguments,
        decision_reason="check readiness",
    )

    final = proposal["tool_arguments"]
    assert final["intent"]["task_id"] == graph.task_id
    assert final["intent"]["revision_id"] == graph.revision_id
    assert final["intent"]["node_id"] == node.node_id
    assert final["intent"]["node_digest"] == proposal["node_digest"]
    assert final["intent"]["motion_authorized"] is False
    assert proposal["input_binding_digest"] == tool_input_binding_digest(final)


def test_prepare_selection_rejects_model_owned_coordinator_identity():
    node = PlanNode(
        node_id="prepare-green",
        obligation_id="prepare-green",
        capability="manipulation.prepare",
        input_bindings={"entity_ref": "entity://green"},
    )
    payload = {
        "task_id": "task-prepare",
        "revision_id": "revision-prepare",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    dispatch = AgentComposedDispatch(
        PlanGraph.model_validate(payload),
        (ToolSpecPolicy(
            tool_id="manipulation.prepare",
            semantics="query",
            spec_digest="3" * 64,
            capabilities=("manipulation.prepare",),
            trusted_argument_builder="manipulation_intent_v2",
        ),),
        AdmissionContext(scene_revision="scene-1"),
    )

    try:
        dispatch.prepare_selection(
            node_id=node.node_id,
            tool_id="manipulation.prepare",
            arguments={"intent": {"task_id": "model-authored"}},
            decision_reason="invalid ownership",
        )
    except ValueError as exc:
        assert "Coordinator-owned" in str(exc)
    else:
        raise AssertionError("model-authored Coordinator identity must be rejected")


def test_prepare_selection_accepts_documented_flat_intent_fields():
    node = PlanNode(
        node_id="prepare-flat",
        obligation_id="prepare-flat",
        capability="manipulation.prepare",
        input_bindings={
            "entity_ref": "entity://green",
            "goal": "place green in the middle",
            "success_criteria": ["green reaches the resolved destination"],
            "allowed_arms": ["left"],
            "coordination_mode": "single_arm",
            "constraints": ["collision free"],
        },
    )
    payload = {
        "task_id": "task-flat",
        "revision_id": "revision-flat",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    dispatch = AgentComposedDispatch(
        PlanGraph.model_validate(payload),
        (ToolSpecPolicy(
            tool_id="manipulation.prepare",
            semantics="query",
            spec_digest="3" * 64,
            capabilities=("manipulation.prepare",),
            trusted_argument_builder="manipulation_intent_v2",
        ),),
        AdmissionContext(scene_revision="scene-flat"),
    )
    arguments = {
        "observation_ref": "observation://scene-flat/camera",
        "scene_revision": "scene-flat",
        "frame_id": "camera",
        "calibration_ref": "artifact://calibration/camera",
        "freshness_ms": 0,
        "max_age_ms": 1000,
        "candidate_set_ref": "candidate-set://scene-flat/camera",
        "candidates": [{"entity_ref": "entity://green"}],
        "destination_ref": "destination://targets/middle",
        "capability_snapshot_ref": "artifact://capabilities/current",
        "goal": "place green in the middle",
        "success_criteria": ["green reaches the resolved destination"],
        "allowed_arms": ["left"],
        "coordination_mode": "single_arm",
        "constraints": ["collision free"],
    }
    proposal = dispatch.prepare_selection(
        node_id=node.node_id,
        tool_id="manipulation.prepare",
        arguments=arguments,
        decision_reason="check flat contract",
    )
    assert proposal["tool_arguments"]["intent"]["goal"] == "place green in the middle"
    assert proposal["tool_arguments"]["intent"]["motion_authorized"] is False

    conflicting = dict(arguments, coordination_mode="bimanual")
    try:
        dispatch.prepare_selection(
            node_id=node.node_id,
            tool_id="manipulation.prepare",
            arguments=conflicting,
            decision_reason="reject semantic drift",
        )
    except ValueError as exc:
        assert "does not match the semantic node" in str(exc)
    else:
        raise AssertionError("conflicting flat intent must fail before Gateway invocation")


def test_prepare_selection_rejects_non_object_nested_intent_as_contract_error():
    node = PlanNode(
        node_id="prepare-invalid",
        obligation_id="prepare-invalid",
        capability="manipulation.prepare",
        input_bindings={"entity_ref": "entity://green"},
    )
    payload = {
        "task_id": "task-invalid",
        "revision_id": "revision-invalid",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    dispatch = AgentComposedDispatch(
        PlanGraph.model_validate(payload),
        (ToolSpecPolicy(
            tool_id="manipulation.prepare",
            semantics="query",
            spec_digest="3" * 64,
            capabilities=("manipulation.prepare",),
            trusted_argument_builder="manipulation_intent_v2",
        ),),
        AdmissionContext(scene_revision="scene-invalid"),
    )
    try:
        dispatch.prepare_selection(
            node_id=node.node_id,
            tool_id="manipulation.prepare",
            arguments={"intent": "not-an-object"},
            decision_reason="reject invalid shape",
        )
    except ValueError as exc:
        assert "must be an object" in str(exc)
    else:
        raise AssertionError("non-object nested intent must be rejected as a contract error")
