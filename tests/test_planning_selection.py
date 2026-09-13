from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.tools.planning import ForgePlanSelectTool
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.task import AgentTaskCoordinator
from PhyAgentOS.planning import (
    AdmissionContext,
    PlanGraph,
    PlanningExecutionBinding,
    PlanNode,
    ToolSpecPolicy,
    canonical_sha256,
    plan_graph_digest,
)
from PhyAgentOS.verification.contracts import TaskVerificationContract


class _Coordinator:
    def __init__(self):
        self.proposals = []

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
        }


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
    assert coordinator.proposals[0]["tool_id"] == "scene.observe"


def test_plan_select_rejects_when_task_is_not_active_graph():
    coordinator = _Coordinator()
    tool = ForgePlanSelectTool(coordinator, lambda: None)

    result = json.loads(asyncio.run(tool.execute(
        "task-1", "observe", "scene.observe", {}, "initial observation"
    )))

    assert result["ok"] is False
    assert result["motion_authorized"] is False
    assert coordinator.proposals == []


def test_real_coordinator_persists_context_bound_decision_trace(tmp_path):
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
    binding = coordinator.persist_planning_selection(proposal)
    validated = PlanningExecutionBinding.model_validate(
        {key: binding[key] for key in PlanningExecutionBinding.model_fields}
    )
    assert validated.node_id == "observe"
    trace_path = tmp_path / "artifacts" / "planning-traces" / task_id / revision_id / "observe"
    traces = list(trace_path.glob("*.json"))
    assert len(traces) == 1
    trace = json.loads(traces[0].read_text())
    assert trace["context_digest"] == canonical_sha256(context.model_dump(mode="json"))
    assert trace["selected_tool_id"] == "scene.observe"
