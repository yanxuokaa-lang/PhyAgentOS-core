from __future__ import annotations

from types import SimpleNamespace

import pytest
from PhyAgentOS.agent.planner_plugin import ReplanProposal
from PhyAgentOS.agent.planning_loop import (
    NodeExecutionContext,
    PlanningLoopAdapter,
    PlanningLoopError,
)
from PhyAgentOS.forge.task import (
    AgentTaskStatus,
    ToolExecutionRecord,
    _tool_result_from_execution,
)
from PhyAgentOS.planning import (
    AdmissionContext,
    PlanGraph,
    PlanNode,
    ToolResultEnvelope,
    build_replan_delta,
    plan_graph_digest,
    settle_node,
)


def _graph(task_id: str, revision_id: str, nodes: list[PlanNode]) -> PlanGraph:
    payload = {
        "task_id": task_id,
        "revision_id": revision_id,
        "nodes": [node.model_dump(mode="json") for node in nodes],
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    return PlanGraph.model_validate(payload)


class _ContextProvider:
    def __init__(self, task):
        self.task = task

    def build(self, task_id, node_id, *, scene_revision, **_kwargs):
        node = next(item for item in self.task.active_revision.plan_graph.nodes if item.node_id == node_id)
        return NodeExecutionContext(
            task_id=task_id,
            revision_id=self.task.active_revision.revision_id,
            node_id=node_id,
            capability=node.capability,
            dependencies=node.dependencies,
            required_evidence=node.required_evidence,
            input_bindings=node.input_bindings,
            scene_revision=scene_revision,
        )


class _Coordinator:
    def __init__(self, graph):
        self.task = SimpleNamespace(
            task_id=graph.task_id,
            status=AgentTaskStatus.EXECUTING,
            primary_skill_binding=None,
            tool_bindings=(
                SimpleNamespace(
                    tool_id="object.acquire",
                    semantics="action",
                    planning_policy=SimpleNamespace(
                        capabilities=("object.acquire",),
                        scene_write_behavior="new_revision",
                    ),
                ),
                SimpleNamespace(
                    tool_id="scene.observe",
                    semantics="query",
                    planning_policy=SimpleNamespace(
                        capabilities=("scene.observe",),
                        scene_write_behavior="none",
                        refreshes_scene=True,
                    ),
                ),
                SimpleNamespace(
                    tool_id="task.goal",
                    semantics="query",
                    planning_policy=SimpleNamespace(
                        capabilities=("task.goal",),
                        scene_write_behavior="none",
                        refreshes_scene=False,
                    ),
                ),
            ),
            active_revision=SimpleNamespace(
                revision_id=graph.revision_id,
                plan_graph=graph,
                node_settlements=[],
                fresh_evidence_requirements=(),
                discovery_evidence_refs=(),
            ),
            revisions=[SimpleNamespace(revision_id=graph.revision_id)],
        )
        self.blocked = []

    def get_task(self, _task_id):
        return self.task

    def effective_node_settlements(self, _task_id):
        return tuple(self.task.active_revision.node_settlements)

    def record_node_settlement(self, settlement):
        self.task.active_revision.node_settlements.append(settlement)

    def record_planning_node_blocked(self, _task_id, _revision_id, node_id, reason):
        self.blocked.append((node_id, reason))

    def request_replan(self, _task_id, *, reason):
        self.task.status = AgentTaskStatus.AWAITING_REPLAN
        self.task.replan_reason = reason
        return self.task

    def begin_revision_from_delta(
        self,
        _task_id,
        _delta,
        *,
        plan_graph,
        plan_graph_ref,
        reason=None,
        **_kwargs,
    ):
        del plan_graph_ref, reason
        self.task.active_revision = SimpleNamespace(
            revision_id=plan_graph.revision_id,
            plan_graph=plan_graph,
            node_settlements=[],
            fresh_evidence_requirements=(),
            discovery_evidence_refs=(),
        )
        self.task.revisions.append(self.task.active_revision)
        self.task.status = AgentTaskStatus.EXECUTING
        return self.task


def _action_result(context, *, requires_replan):
    return ToolResultEnvelope(
        task_id=context.task_id,
        revision_id=context.revision_id,
        node_id=context.node_id,
        tool_id=context.capability,
        status="unknown",
        world_change_started=True,
        outcome_known=False,
        failure_code="SimulationProbeError",
        requires_replan=requires_replan,
        recommended_action="reconcile_world",
    )


def test_settlement_preserves_runtime_recovery_facts():
    node = PlanNode(node_id="acquire", obligation_id="acquire", capability="object.acquire")
    result = ToolResultEnvelope(
        task_id="task-1",
        revision_id="revision-1",
        node_id="acquire",
        tool_id="object.acquire",
        status="unknown",
        world_change_started=True,
        outcome_known=False,
        retryable_in_revision=False,
        requires_replan=True,
        recommended_action="reconcile_world",
    )

    settlement = settle_node(node, result, current_scene_revision="scene://s1")

    assert settlement.status == "outcome_unknown"
    assert settlement.retryable_in_revision is False
    assert settlement.requires_replan is True
    assert settlement.recommended_action == "reconcile_world"


def test_persisted_runtime_receipt_projects_recovery_facts_into_tool_result():
    record = ToolExecutionRecord(
        record_id="record-1",
        revision_id="revision-1",
        tool_id="object.acquire",
        semantics="action",
        caller_id="paos:task-1:revision-1:node-acquire",
        node_id="acquire",
        node_digest="a" * 64,
        obligation_id="acquire",
        input_binding_digest="b" * 64,
        decision_trace_ref="artifact://trace/acquire",
        status="unknown",
        response={
            "data": {
                "status": "unknown",
                "result": {
                    "capability_outcome_summary": {
                        "world_change_started": True,
                        "outcome_known": False,
                        "retryable_in_revision": False,
                        "requires_replan": True,
                        "recommended_action": "reconcile_world",
                    },
                },
            },
        },
    )
    task = SimpleNamespace(
        task_id="task-1",
        primary_skill_binding=None,
        tool_bindings=(),
    )

    result = _tool_result_from_execution(task, record)

    assert result is not None
    assert result.world_change_started is True
    assert result.outcome_known is False
    assert result.retryable_in_revision is False
    assert result.requires_replan is True
    assert result.recommended_action == "reconcile_world"


@pytest.mark.asyncio
async def test_explicit_unknown_replan_enters_recovery_revision_without_action_retry():
    task_id = "task-unknown-replan"
    action = PlanNode(node_id="acquire", obligation_id="acquire", capability="object.acquire")
    initial = _graph(task_id, "revision-1", [action])
    coordinator = _Coordinator(initial)
    context_provider = _ContextProvider(coordinator.task)
    calls = []
    current_scene = {"value": "scene://s1"}

    reconcile = PlanNode(
        node_id="reconcile",
        obligation_id="reconcile",
        capability="scene.observe",
    )
    replacement = _graph(task_id, "revision-2", [reconcile])

    def execute(context):
        calls.append(context.node_id)
        if context.node_id == "acquire":
            current_scene["value"] = "scene://s2"
            return _action_result(context, requires_replan=True)
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id=context.capability,
            status="succeeded",
            outcome_known=True,
            evidence_refs=("artifact://observation/reconcile",),
        )

    def admission(_task_id):
        return AdmissionContext(scene_revision=current_scene["value"])

    def propose(graph, settlement, delta, _context):
        assert settlement.requires_replan is True
        assert delta.retry_parent_node_id == "acquire"
        return ReplanProposal(
            delta=build_replan_delta(graph, settlement),
            plan_graph=replacement,
            plan_graph_ref="artifact://plans/task-unknown-replan/revision-2",
            reason="reconcile unknown world effect",
        )

    result = await PlanningLoopAdapter(
        coordinator,
        context_provider=context_provider,
        node_executor=execute,
        admission_context_provider=admission,
        replan_proposer=propose,
        recovery_policy=lambda *_args: "replan",
        finalize_completed_graph=False,
    ).run(task_id, scene_revision="scene://s1")

    assert result.status == "segment_completed"
    assert result.replans == 1
    assert calls == ["acquire", "reconcile"]
    assert coordinator.blocked == []


@pytest.mark.asyncio
async def test_unknown_without_runtime_replan_stays_reconciliation_blocked():
    task_id = "task-unknown-stop"
    action = PlanNode(node_id="acquire", obligation_id="acquire", capability="object.acquire")
    graph = _graph(task_id, "revision-1", [action])
    coordinator = _Coordinator(graph)
    calls = []

    def execute(context):
        calls.append(context.node_id)
        return _action_result(context, requires_replan=False)

    result = await PlanningLoopAdapter(
        coordinator,
        context_provider=_ContextProvider(coordinator.task),
        node_executor=execute,
        admission_context_provider=lambda _task_id: AdmissionContext(scene_revision="scene://s1"),
        replan_proposer=lambda *_args: pytest.fail("replan must not be proposed"),
        finalize_completed_graph=False,
    ).run(task_id, scene_revision="scene://s1")

    assert result.status == "blocked"
    assert result.last_failure == "reconciliation_required:acquire"
    assert calls == ["acquire"]
    assert coordinator.blocked == [("acquire", "reconciliation_required:acquire")]


def test_unknown_recovery_graph_accepts_action_gated_by_new_query():
    task_id = "task-unknown-query-gate"
    original_action = PlanNode(
        node_id="acquire", obligation_id="acquire", capability="object.acquire"
    )
    original = _graph(task_id, "revision-1", [original_action])
    coordinator = _Coordinator(original)
    adapter = PlanningLoopAdapter(
        coordinator,
        context_provider=_ContextProvider(coordinator.task),
        node_executor=lambda _context: pytest.fail("graph validation must not execute Tools"),
        admission_context_provider=lambda _task_id: AdmissionContext(scene_revision="scene://s1"),
        finalize_completed_graph=False,
    )
    observe = PlanNode(
        node_id="observe", obligation_id="observe", capability="scene.observe"
    )
    next_action = PlanNode(
        node_id="next-action",
        obligation_id="next-action",
        capability="object.acquire",
        dependencies=("observe",),
    )
    graph = _graph(task_id, "revision-2", [observe, next_action])

    adapter._validate_unknown_recovery_graph(task_id, graph, preserved_node_ids=set())


def test_unknown_recovery_graph_rejects_non_refreshing_query_and_action():
    task_id = "task-unknown-query-not-gating"
    original_action = PlanNode(
        node_id="acquire", obligation_id="acquire", capability="object.acquire"
    )
    original = _graph(task_id, "revision-1", [original_action])
    coordinator = _Coordinator(original)
    adapter = PlanningLoopAdapter(
        coordinator,
        context_provider=_ContextProvider(coordinator.task),
        node_executor=lambda _context: pytest.fail("graph validation must not execute Tools"),
        admission_context_provider=lambda _task_id: AdmissionContext(scene_revision="scene://s1"),
        finalize_completed_graph=False,
    )
    observe = PlanNode(
        node_id="goal", obligation_id="goal", capability="task.goal"
    )
    next_action = PlanNode(
        node_id="next-action", obligation_id="next-action", capability="object.acquire"
    )
    graph = _graph(task_id, "revision-2", [observe, next_action])

    with pytest.raises(PlanningLoopError, match="requires a new scene-refresh Query"):
        adapter._validate_unknown_recovery_graph(task_id, graph, preserved_node_ids=set())


def test_unknown_recovery_graph_requires_scene_refresh_query_ancestor():
    task_id = "task-unknown-refresh-not-gating"
    original_action = PlanNode(
        node_id="acquire", obligation_id="acquire", capability="object.acquire"
    )
    original = _graph(task_id, "revision-1", [original_action])
    coordinator = _Coordinator(original)
    adapter = PlanningLoopAdapter(
        coordinator,
        context_provider=_ContextProvider(coordinator.task),
        node_executor=lambda _context: pytest.fail("graph validation must not execute Tools"),
        admission_context_provider=lambda _task_id: AdmissionContext(scene_revision="scene://s1"),
        finalize_completed_graph=False,
    )
    observe = PlanNode(
        node_id="observe", obligation_id="observe", capability="scene.observe"
    )
    next_action = PlanNode(
        node_id="next-action", obligation_id="next-action", capability="object.acquire"
    )
    graph = _graph(task_id, "revision-2", [observe, next_action])

    with pytest.raises(
        PlanningLoopError,
        match="is not gated by a new scene-refresh Query",
    ):
        adapter._validate_unknown_recovery_graph(task_id, graph, preserved_node_ids=set())


def test_unknown_recovery_graph_rejects_ambiguous_scene_refresh_metadata():
    task_id = "task-unknown-refresh-metadata-conflict"
    original_action = PlanNode(
        node_id="acquire", obligation_id="acquire", capability="object.acquire"
    )
    original = _graph(task_id, "revision-1", [original_action])
    coordinator = _Coordinator(original)
    coordinator.task.tool_bindings += (
        SimpleNamespace(
            tool_id="alternate-observer",
            semantics="query",
            planning_policy=SimpleNamespace(
                capabilities=("scene.observe",),
                scene_write_behavior="none",
                refreshes_scene=False,
            ),
        ),
    )
    adapter = PlanningLoopAdapter(
        coordinator,
        context_provider=_ContextProvider(coordinator.task),
        node_executor=lambda _context: pytest.fail("graph validation must not execute Tools"),
        admission_context_provider=lambda _task_id: AdmissionContext(scene_revision="scene://s1"),
        finalize_completed_graph=False,
    )
    observe = PlanNode(
        node_id="observe", obligation_id="observe", capability="scene.observe"
    )
    graph = _graph(task_id, "revision-2", [observe])

    with pytest.raises(
        PlanningLoopError,
        match="unambiguous Runtime ToolSpec semantics and scene-refresh metadata",
    ):
        adapter._validate_unknown_recovery_graph(task_id, graph, preserved_node_ids=set())
