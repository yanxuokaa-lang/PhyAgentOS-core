from __future__ import annotations

import asyncio
import json

import pytest

from PhyAgentOS.agent.experience.source import AgentTaskOutcomeSource
from PhyAgentOS.agent.tools.forge_task import ForgeTaskBeginRevisionTool
from PhyAgentOS.agent.tools.forge_tool_api import ForgeToolQueryTool
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.binding import BoundToolSpec, RuntimeBinding
from PhyAgentOS.forge.task import AgentTaskCoordinator, AgentTaskStatus, DiscoveryRequiredError
from PhyAgentOS.planning import (
    PlanGraph,
    PlanningExecutionBinding,
    PlanNode,
    ToolResultEnvelope,
    ToolSpecPolicy,
    build_replan_delta,
    derive_ready_nodes,
    plan_graph_digest,
    plan_node_digest,
    settle_node,
)
from PhyAgentOS.verification.contracts import TaskVerificationContract


class _Client:
    pass


class _QueryClient:
    def __init__(self):
        self.timeout_ms = None

    async def invoke_query_tool(
        self, tool_id, arguments, *, caller_id=None, timeout_ms=None
    ):
        self.timeout_ms = timeout_ms
        return {"ok": True, "data": {"status": "available"}}


def _graph(task_id: str, revision_id: str) -> PlanGraph:
    node = PlanNode(
        node_id="relocate-red",
        obligation_id="relocate-red",
        capability="object.relocate",
        required_evidence=("observation:red",),
    )
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
    return PlanGraph.model_validate(payload)


def test_coordinator_persists_concrete_graph_and_complete_execution_attribution(tmp_path):
    graph = _graph("task-1", "revision-1")
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client()
    )
    task = coordinator.create_task(
        task_description="relocate red",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-1/revision-1",
    )
    assert task.task_id == graph.task_id
    assert task.active_revision.plan_graph_digest == graph.graph_digest

    binding = PlanningExecutionBinding(
        node_id="relocate-red",
        node_digest=plan_node_digest(graph.nodes[0]),
        obligation_id="relocate-red",
        input_binding_digest="3" * 64,
        decision_trace_ref="artifact://traces/task-1/record-1",
    )
    record_id, _caller = coordinator._append_execution(
        task.task_id,
        "scene.observe",
        "query",
        {"sensor_ref": "camera/front"},
        tool=BoundToolSpec(
            tool_id="scene.observe",
            semantics="query",
            spec_sha256="4" * 64,
            ready_at_binding=True,
        ),
        planning_binding=binding,
    )
    record = coordinator.get_task(task.task_id).execution_records[0]
    assert record.record_id == record_id
    assert record.node_id == binding.node_id
    assert record.node_digest == binding.node_digest
    assert record.obligation_id == binding.obligation_id
    assert record.input_binding_digest == binding.input_binding_digest
    assert record.decision_trace_ref == binding.decision_trace_ref

    coordinator._finish_execution(
        task.task_id, record_id, status="succeeded", response={"status": "succeeded"}
    )
    settled = coordinator.get_task(task.task_id).active_revision.node_settlements
    assert len(settled) == 1
    assert settled[0].node_id == "relocate-red"
    assert settled[0].status == "completed"
    coordinator.store.update(
        task.task_id,
        lambda current: setattr(current, "status", AgentTaskStatus.SUCCEEDED),
        event_type="test_completed",
    )
    outcome = AgentTaskOutcomeSource(coordinator).build(task.task_id)
    assert len(outcome.decision_trace_refs) == 1
    assert outcome.decision_trace_refs[0].startswith("evidence:")


@pytest.mark.parametrize("semantics", ["query", "action", "session"])
def test_terminal_planning_records_settle_all_tool_semantics(tmp_path, semantics):
    graph = _graph("task-1", "revision-1")
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client()
    )
    task = coordinator.create_task(
        task_description="settle one semantic node",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-1/revision-1",
    )
    binding = {
        "node_id": "relocate-red",
        "node_digest": plan_node_digest(graph.nodes[0]),
        "obligation_id": "relocate-red",
        "input_binding_digest": "3" * 64,
        "decision_trace_ref": "artifact://traces/task-1/record-1",
    }
    record_id, _caller = coordinator._append_execution(
        task.task_id,
        f"tool.{semantics}",
        semantics,
        {},
        tool=BoundToolSpec(
            tool_id=f"tool.{semantics}",
            semantics=semantics,
            spec_sha256="4" * 64,
            ready_at_binding=True,
        ),
        planning_binding=binding,
    )
    coordinator._finish_execution(
        task.task_id,
        record_id,
        status="succeeded",
        response={"status": "succeeded", "scene_revision": "scene-1"},
    )
    settlements = coordinator.get_task(task.task_id).active_revision.node_settlements
    assert [(item.node_id, item.status) for item in settlements] == [
        ("relocate-red", "completed")
    ]
    coordinator.reconcile_terminal_settlements(task.task_id)
    assert len(coordinator.get_task(task.task_id).active_revision.node_settlements) == 1


@pytest.mark.asyncio
async def test_bound_query_timeout_cannot_be_shorter_than_tool_spec_default(tmp_path):
    client = _QueryClient()
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=client
    )
    task = coordinator.create_task(
        task_description="run one bounded model Query",
        verification=TaskVerificationContract(mode="off"),
    )

    async def require_tool(task_id, tool_id, semantics):
        return BoundToolSpec(
            tool_id=tool_id,
            semantics=semantics,
            spec_sha256="4" * 64,
            ready_at_binding=True,
            default_timeout_ms=180_000,
        )

    coordinator._require_binding_tool = require_tool
    await coordinator.invoke_query(
        task.task_id,
        "grasp.propose",
        {},
        timeout_ms=30_000,
    )

    assert client.timeout_ms == 180_000


def test_terminal_planning_query_failure_enters_replan_without_motion(tmp_path):
    graph = _graph("task-1", "revision-1")
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client()
    )
    task = coordinator.create_task(
        task_description="recover one failed planning Query",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-1/revision-1",
    )
    binding = PlanningExecutionBinding(
        node_id="relocate-red",
        node_digest=plan_node_digest(graph.nodes[0]),
        obligation_id="relocate-red",
        input_binding_digest="3" * 64,
        decision_trace_ref="artifact://traces/task-1/record-1",
    )
    record_id, _caller = coordinator._append_execution(
        task.task_id,
        "grasp.propose",
        "query",
        {},
        tool=BoundToolSpec(
            tool_id="grasp.propose",
            semantics="query",
            spec_sha256="4" * 64,
            ready_at_binding=True,
        ),
        planning_binding=binding,
    )

    coordinator._finish_execution(
        task.task_id,
        record_id,
        status="succeeded",
        response={
            "status": "unavailable",
            "error": {"code": "grasp_proposal_provider_error"},
        },
    )

    current = coordinator.get_task(task.task_id)
    assert current.status == AgentTaskStatus.AWAITING_REPLAN
    assert current.replan_deadline is not None
    assert current.active_revision.node_settlements[0].status == "failed"
    assert all(record.semantics == "query" for record in current.execution_records)


def test_agent_recovery_nodes_are_compiled_by_paos_without_motion(tmp_path):
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client()
    )
    task = coordinator.create_task(
        task_description="compile a semantic recovery revision",
        verification=TaskVerificationContract(mode="off"),
    )
    policy = ToolSpecPolicy(
        tool_id="object.relocate",
        semantics="action",
        spec_digest="4" * 64,
        capabilities=("object.relocate",),
    )
    runtime_binding = RuntimeBinding(
        binding_id="runtime_binding_recovery",
        runtime_profile="fake",
        runtime_instance_id="runtime_recovery",
        gateway_url="http://fake",
    )
    tool_binding = BoundToolSpec(
        tool_id="object.relocate",
        semantics="action",
        spec_sha256="4" * 64,
        ready_at_binding=True,
        planning_policy=policy,
    )

    def attach_binding(current):
        current.runtime_binding = runtime_binding
        current.active_revision.runtime_binding_id = runtime_binding.binding_id
        current.tool_bindings = [tool_binding]

    coordinator.store.update(
        task.task_id,
        attach_binding,
        event_type="test_recovery_binding",
    )
    coordinator.request_replan(task.task_id, reason="replace failed semantic node")
    result = json.loads(asyncio.run(ForgeTaskBeginRevisionTool(coordinator).execute(
        task.task_id,
        reason="retry with corrected semantic inputs",
        nodes=[PlanNode(
            node_id="retry-relocate",
            obligation_id="retry-relocate",
            capability="object.relocate",
        ).model_dump(mode="json")],
    )))

    assert result["ok"] is True
    current = coordinator.get_task(task.task_id)
    assert current.status == AgentTaskStatus.EXECUTING
    assert current.active_revision.plan_graph is not None
    assert current.active_revision.plan_graph.revision_id.startswith("revision_")
    assert current.active_revision.plan_graph_ref.startswith("artifact://plans/")
    assert current.active_revision.execution_records == []
    assert current.active_revision.node_settlements == []


def test_discovery_failure_stays_open_but_planning_unknown_requests_replan(tmp_path):
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client()
    )
    task = coordinator.create_task(
        task_description="continue open discovery",
        verification=TaskVerificationContract(mode="off"),
    )
    record_id, _caller = coordinator._append_execution(
        task.task_id,
        "scene.understand",
        "query",
        {},
        tool=BoundToolSpec(
            tool_id="scene.understand",
            semantics="query",
            spec_sha256="4" * 64,
            ready_at_binding=True,
        ),
    )
    coordinator._finish_execution(
        task.task_id,
        record_id,
        status="succeeded",
        response={"status": "unavailable"},
    )
    assert coordinator.get_task(task.task_id).status == AgentTaskStatus.EXECUTING

    coordinator = AgentTaskCoordinator(
        workspace=tmp_path / "planned", config=ForgeConfig(), client=_Client()
    )
    graph = _graph("task-2", "revision-2")
    planned = coordinator.create_task(
        task_description="retain unknown Query state",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-2/revision-2",
    )
    binding = PlanningExecutionBinding(
        node_id="relocate-red",
        node_digest=plan_node_digest(graph.nodes[0]),
        obligation_id="relocate-red",
        input_binding_digest="3" * 64,
        decision_trace_ref="artifact://traces/task-2/record-1",
    )
    record_id, _caller = coordinator._append_execution(
        planned.task_id,
        "grasp.propose",
        "query",
        {},
        tool=BoundToolSpec(
            tool_id="grasp.propose",
            semantics="query",
            spec_sha256="4" * 64,
            ready_at_binding=True,
        ),
        planning_binding=binding,
    )
    coordinator._finish_execution(
        planned.task_id,
        record_id,
        status="unknown",
        error={"type": "ForgeToolAPITimeoutError"},
    )
    assert coordinator.get_task(planned.task_id).status == AgentTaskStatus.AWAITING_REPLAN
    assert coordinator.get_task(planned.task_id).replan_deadline is not None


def test_discovery_expansion_rejects_provider_failure_response(tmp_path):
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client()
    )
    task = coordinator.create_task(
        task_description="reject failed discovery evidence",
        verification=TaskVerificationContract(mode="off"),
    )
    task = coordinator.store.update(
        task.task_id,
        lambda current: current.tool_bindings.append(
            BoundToolSpec(
                tool_id="scene.observe",
                semantics="query",
                spec_sha256="5" * 64,
                ready_at_binding=True,
                planning_policy=ToolSpecPolicy(
                    tool_id="scene.observe",
                    semantics="query",
                    spec_digest="5" * 64,
                    requires_before_plan=True,
                    capabilities=("scene.observe",),
                ),
            )
        ),
        event_type="test_binding_added",
    )
    record_id, _caller = coordinator._append_execution(
        task.task_id,
        "scene.observe",
        "query",
        {},
        tool=BoundToolSpec(
            tool_id="scene.observe",
            semantics="query",
            spec_sha256="4" * 64,
            ready_at_binding=True,
        ),
    )
    coordinator._finish_execution(
        task.task_id,
        record_id,
        status="succeeded",
        response={"status": "unavailable", "scene_revision": "scene-1"},
    )
    assert coordinator.get_task(task.task_id).status == AgentTaskStatus.EXECUTING
    with pytest.raises(DiscoveryRequiredError):
        coordinator.expand_discovery_revision(
            task.task_id,
            plan_graph=_graph(task.task_id, "revision-discovery-failed"),
            plan_graph_ref=f"artifact://plans/{task.task_id}/revision-discovery-failed",
        )


def test_reconcile_terminal_settlement_repairs_legacy_missing_projection(tmp_path):
    graph = _graph("task-1", "revision-1")
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client()
    )
    task = coordinator.create_task(
        task_description="repair an old terminal record",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-1/revision-1",
    )
    binding = {
        "node_id": "relocate-red",
        "node_digest": plan_node_digest(graph.nodes[0]),
        "obligation_id": "relocate-red",
        "input_binding_digest": "3" * 64,
        "decision_trace_ref": "artifact://traces/task-1/record-1",
    }
    record_id, _caller = coordinator._append_execution(
        task.task_id,
        "scene.observe",
        "query",
        {},
        tool=BoundToolSpec(
            tool_id="scene.observe",
            semantics="query",
            spec_sha256="4" * 64,
            ready_at_binding=True,
        ),
        planning_binding=binding,
    )
    coordinator.store.update(
        task.task_id,
        lambda current: (
            setattr(current.execution_records[0], "status", "succeeded"),
            setattr(
                current.execution_records[0],
                "response",
                {"status": "succeeded", "scene_revision": "scene-1"},
            ),
        ),
        event_type="test_legacy_terminal_record",
    )
    assert coordinator.get_task(task.task_id).active_revision.node_settlements == []
    repaired = coordinator.reconcile_terminal_settlements(task.task_id)
    assert repaired.active_revision.node_settlements[0].status == "completed"
    assert record_id == repaired.active_revision.execution_records[0].record_id


@pytest.mark.parametrize("semantics", ["action", "session"])
def test_terminal_observation_paths_settle_planning_nodes(tmp_path, semantics):
    graph = _graph("task-1", "revision-1")
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client()
    )
    task = coordinator.create_task(
        task_description="settle an observed invocation",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-1/revision-1",
    )
    binding = {
        "node_id": "relocate-red",
        "node_digest": plan_node_digest(graph.nodes[0]),
        "obligation_id": "relocate-red",
        "input_binding_digest": "3" * 64,
        "decision_trace_ref": "artifact://traces/task-1/record-1",
    }
    record_id, _caller = coordinator._append_execution(
        task.task_id,
        f"tool.{semantics}",
        semantics,
        {},
        tool=BoundToolSpec(
            tool_id=f"tool.{semantics}",
            semantics=semantics,
            spec_sha256="4" * 64,
            ready_at_binding=True,
        ),
        planning_binding=binding,
    )
    invocation_id = f"invocation-{semantics}"
    coordinator.store.update(
        task.task_id,
        lambda current: (
            setattr(current.execution_records[0], "invocation_id", invocation_id),
            setattr(current.execution_records[0], "status", "running"),
        ),
        event_type="test_invocation_running",
    )
    response = {"status": "succeeded", "scene_revision": "scene-1"}
    if semantics == "action":
        coordinator.observe_action(task.task_id, invocation_id, response)
    else:
        coordinator.observe_session(task.task_id, invocation_id, response)
    current = coordinator.get_task(task.task_id)
    assert current.execution_records[0].record_id == record_id
    assert current.execution_records[0].status == "succeeded"
    assert current.active_revision.node_settlements[0].status == "completed"


def test_terminal_settlement_unlocks_downstream_node(tmp_path):
    target = PlanNode(
        node_id="target",
        obligation_id="target",
        capability="manipulation.target",
    )
    grasp = PlanNode(
        node_id="grasp",
        obligation_id="grasp",
        capability="grasp.propose",
        dependencies=("target",),
    )
    payload = {
        "schema_version": "paos-plan-graph/v1",
        "task_id": "task-dag",
        "revision_id": "revision-dag",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [target.model_dump(mode="json"), grasp.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client()
    )
    task = coordinator.create_task(
        task_description="unlock the dependent grasp node",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-dag/revision-dag",
    )
    binding = {
        "node_id": "target",
        "node_digest": plan_node_digest(target),
        "obligation_id": "target",
        "input_binding_digest": "3" * 64,
        "decision_trace_ref": "artifact://traces/task-dag/target",
    }
    record_id, _caller = coordinator._append_execution(
        task.task_id,
        "manipulation.target",
        "query",
        {},
        tool=BoundToolSpec(
            tool_id="manipulation.target",
            semantics="query",
            spec_sha256="4" * 64,
            ready_at_binding=True,
        ),
        planning_binding=binding,
    )
    coordinator._finish_execution(
        task.task_id,
        record_id,
        status="succeeded",
        response={"status": "succeeded", "scene_revision": "scene-1"},
    )
    current = coordinator.get_task(task.task_id)
    ready = derive_ready_nodes(
        graph,
        {item.node_id: item.status for item in current.active_revision.node_settlements},
    )
    assert ready == ("grasp",)


def test_partial_planning_binding_and_unbound_graph_ref_fail_closed(tmp_path):
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client()
    )
    try:
        coordinator.create_task(
            task_description="invalid",
            verification=TaskVerificationContract(mode="off"),
            plan_graph_ref="artifact://plans/only-ref",
        )
    except Exception as exc:
        assert "requires a concrete PlanGraph" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("graph ref without graph must be rejected")

    task = coordinator.create_task(
        task_description="legacy",
        verification=TaskVerificationContract(mode="off"),
    )
    try:
        coordinator._append_execution(
            task.task_id,
            "scene.observe",
            "query",
            {},
            tool=BoundToolSpec(
                tool_id="scene.observe",
                semantics="query",
                spec_sha256="4" * 64,
                ready_at_binding=True,
            ),
            planning_binding={"node_id": "partial"},
        )
    except Exception as exc:
        assert "invalid planning execution binding" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("partial planning binding must be rejected")


@pytest.mark.parametrize("semantics", ["query", "action", "session"])
def test_complete_planning_binding_is_shared_by_all_tool_semantics(tmp_path, semantics):
    graph = _graph("task-1", "revision-1")
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client()
    )
    task = coordinator.create_task(
        task_description="attribute tool",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-1/revision-1",
    )
    binding = {
        "node_id": "relocate-red",
        "node_digest": plan_node_digest(graph.nodes[0]),
        "obligation_id": "relocate-red",
        "input_binding_digest": "3" * 64,
        "decision_trace_ref": "artifact://traces/task-1/record-1",
    }
    coordinator._append_execution(
        task.task_id,
        f"tool.{semantics}",
        semantics,
        {},
        tool=BoundToolSpec(
            tool_id=f"tool.{semantics}",
            semantics=semantics,
            spec_sha256="4" * 64,
            ready_at_binding=True,
        ),
        planning_binding=binding,
    )
    record = coordinator.get_task(task.task_id).execution_records[0]
    assert record.semantics == semantics
    assert record.decision_trace_ref == binding["decision_trace_ref"]


def test_replan_delta_adapter_creates_new_coordinator_revision(tmp_path):
    graph = _graph("task-1", "revision-1")
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client(), max_replans=2
    )
    task = coordinator.create_task(
        task_description="relocate red",
        verification=TaskVerificationContract(mode="off"),
        plan_graph=graph,
        plan_graph_ref="artifact://plans/task-1/revision-1",
    )
    settlement = settle_node(
        graph.nodes[0],
        ToolResultEnvelope(
            task_id=task.task_id,
            revision_id=task.active_revision_id,
            node_id="relocate-red",
            tool_id="scene.observe",
            status="failed",
            failure_code="no_candidate",
        ),
        current_scene_revision="scene-1",
    )
    delta = build_replan_delta(graph, settlement, fresh_evidence_requirements=("observation:red",))
    coordinator.store.update(
        task.task_id,
        lambda current: setattr(current, "status", AgentTaskStatus.AWAITING_REPLAN),
        event_type="test_awaiting_replan",
    )
    replacement = _graph(task.task_id, "revision-2")
    revised = coordinator.begin_revision_from_delta(
        task.task_id,
        delta,
        plan_graph=replacement,
        plan_graph_ref="artifact://plans/task-1/revision-2",
    )
    assert revised.active_revision_id == "revision-2"
    assert revised.active_revision.plan_graph_digest == replacement.graph_digest


def test_query_tool_does_not_drop_planning_binding_in_unbound_diagnostic_mode(tmp_path):
    coordinator = AgentTaskCoordinator(
        workspace=tmp_path, config=ForgeConfig(), client=_Client()
    )
    result = json.loads(
        asyncio.run(
            ForgeToolQueryTool(_Client(), coordinator).execute(
                "scene.observe", {}, planning_binding={"node_id": "n"}
            )
        )
    )
    assert result["ok"] is False
    assert result["error"]["message"] == "planning_binding requires task_id"
