from __future__ import annotations

import asyncio

import pytest

from PhyAgentOS.agent.planner_plugin import PlannerPluginRegistry, PlanningRequest, ReplanProposal
from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.planning_loop import (
    NodeContextProvider,
    PlanningLoopAdapter,
    PlanningLoopError,
    StaleNodeContextError,
)
from PhyAgentOS.agent.tools.forge_task import build_forge_task_tools
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.task import AgentTaskCoordinator, AgentTaskError
from PhyAgentOS.planning import (
    AdmissionContext,
    NodeSettlement,
    PlanGraph,
    PlanningExecutionBinding,
    PlanNode,
    ReplanDelta,
    ToolResultEnvelope,
    ToolSpecPolicy,
    plan_graph_digest,
    plan_node_digest,
)
from PhyAgentOS.verification.contracts import TaskVerificationContract


def make_graph(task_id: str, revision_id: str, names: tuple[str, ...]) -> PlanGraph:
    nodes = []
    previous = None
    for name in names:
        nodes.append(PlanNode(
            node_id=name,
            obligation_id=f"obligation-{name}",
            capability="attribute.arrange" if name != "verify" else "scene.verify",
            dependencies=(previous,) if previous else (),
            required_evidence=("scene:inventory",) if name != "verify" else (),
            produced_evidence=(f"placed:{name}",) if name != "verify" else (),
        ))
        previous = name
    payload = {
        "schema_version": "paos-plan-graph/v1",
        "task_id": task_id,
        "revision_id": revision_id,
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [item.model_dump(mode="json") for item in nodes],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    return PlanGraph.model_validate(payload)


def coordinator(tmp_path):
    return AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=object(),
        verifier=None,
        max_replans=2,
        replan_timeout_s=10,
    )


def test_discovery_expands_same_task_and_injects_direct_predecessor_context(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="arrange blocks by discovered attribute",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-discovered", ("arrange-red", "arrange-green", "verify"))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/rgb/discovered",
        discovery_evidence_refs=("artifact://scene/inventory-1",),
    )
    provider = NodeContextProvider(c.get_task)
    root = provider.build(task.task_id, "arrange-red", scene_revision="scene-1")
    assert root.predecessor_context == ()
    c.record_node_settlement(NodeSettlement(
        task_id=task.task_id,
        revision_id=graph.revision_id,
        node_id="arrange-red",
        status="completed",
        scene_revision="scene-1",
        evidence_refs=("artifact://placed/red",),
        source_tool_id="object.arrange",
    ))
    next_context = provider.build(task.task_id, "arrange-green", scene_revision="scene-1")
    assert next_context.predecessor_context[0].node_id == "arrange-red"
    assert next_context.predecessor_context[0].evidence_refs == ("artifact://placed/red",)


def test_context_rejects_stale_predecessor(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="stale context", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-1", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/stale")
    c.record_node_settlement(NodeSettlement(
        task_id=task.task_id, revision_id=graph.revision_id, node_id="arrange-red",
        status="completed", scene_revision="scene-1",
    ))
    provider = NodeContextProvider(c.get_task)
    with pytest.raises(StaleNodeContextError):
        provider.build(task.task_id, "verify", scene_revision="scene-2")


def test_rgb_attribute_sorting_loop_replans_after_drop_and_reducer_replays(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="arrange blocks by color",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-1", ("arrange-red", "arrange-green", "verify"))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/rgb/revision-1",
        discovery_evidence_refs=("artifact://scene/observed-blocks",),
    )
    calls: list[str] = []
    dropped = {"seen": False}

    def admission(_task_id: str) -> AdmissionContext:
        evidence = {"scene:inventory"}
        for revision in c.get_task(task.task_id).revisions:
            for settlement in revision.node_settlements:
                evidence.update(settlement.evidence_refs)
        return AdmissionContext(scene_revision="scene-1", evidence_refs=frozenset(evidence))

    def execute(context):
        calls.append(context.node_id)
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.arrange" if context.node_id != "verify" else "scene.verify",
            status="succeeded",
            evidence_refs=(f"placed:{context.node_id}",),
        )

    def postcondition(context, result):
        if context.node_id == "arrange-green" and not dropped["seen"]:
            dropped["seen"] = True
            return NodeSettlement(
                task_id=context.task_id,
                revision_id=context.revision_id,
                node_id=context.node_id,
                status="stale",
                scene_revision="scene-1",
                evidence_refs=("artifact://counterevidence/green-dropped",),
                failure_code="postcondition_object_missing",
            )
        return None

    def replan(old_graph, settlement, delta, context):
        assert settlement.failure_code == "postcondition_object_missing"
        replacement = make_graph(task.task_id, "revision-2", ("arrange-red", "arrange-green-retry", "verify"))
        return ReplanProposal(
            delta=delta,
            plan_graph=replacement,
            plan_graph_ref="artifact://plans/rgb/revision-2",
            reason="replan after counterevidence",
        )

    adapter = PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=admission,
        replan_proposer=replan,
        postcondition_checker=postcondition,
    )
    result = asyncio.run(adapter.run(task.task_id, scene_revision="scene-1"))
    assert result.status == "completed"
    assert "arrange-green" in calls and "arrange-green-retry" in calls
    final_task = c.get_task(task.task_id)
    assert len(final_task.revisions) == 3  # empty discovery revision + two concrete revisions
    assert any(item.status == "completed" for item in final_task.revisions[1].node_settlements)
    assert final_task.revisions[1].counterevidence[0].failure_code == "postcondition_object_missing"
    assert final_task.active_revision.node_settlements[-1].node_id == "verify"
    assert final_task.active_revision.replan_evidence_refs == ("artifact://counterevidence/green-dropped",)
    replay = adapter.reducer_replay(task.task_id, evidence_refs={"scene:inventory"})
    assert "revision-1" in replay and "revision-2" in replay
    assert replay["revision-1"] == ("verify",)


def test_failed_node_replan_preserves_completed_predecessor(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="retry one node", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-1", ("arrange-red", "arrange-green", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/retry/1")
    failures = {"arrange-green": 0}

    fresh_ready = {"value": False}

    def admission(_):
        evidence = {"scene:inventory"}
        if fresh_ready["value"]:
            evidence.add("scene:fresh")
        return AdmissionContext(scene_revision="scene-1", evidence_refs=frozenset(evidence))

    def execute(context):
        if context.node_id == "arrange-green" and failures[context.node_id] == 0:
            failures[context.node_id] += 1
            return ToolResultEnvelope(task_id=context.task_id, revision_id=context.revision_id, node_id=context.node_id, tool_id="object.arrange", status="failed", failure_code="gripper_slip")
        return ToolResultEnvelope(task_id=context.task_id, revision_id=context.revision_id, node_id=context.node_id, tool_id="scene.verify" if context.node_id == "verify" else "object.arrange", status="succeeded")

    def replan(_graph, _settlement, delta, _context):
        replacement = make_graph(task.task_id, "revision-2", ("arrange-red", "arrange-green-retry", "verify"))
        fresh_ready["value"] = True
        return ReplanProposal(
            delta=delta.model_copy(update={"fresh_evidence_requirements": ("scene:fresh",)}),
            plan_graph=replacement,
            plan_graph_ref="artifact://plans/retry/2",
        )

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=admission,
        replan_proposer=replan,
    ).run(task.task_id, scene_revision="scene-1"))
    assert result.status == "completed"
    active = c.get_task(task.task_id).active_revision
    assert active.node_settlements[0].node_id == "arrange-red"
    assert active.node_settlements[0].status == "completed"
    assert active.fresh_evidence_requirements == ("scene:fresh",)


def test_replan_rejects_preserving_changed_node_content(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="changed obligation", verification=TaskVerificationContract(mode="off"))
    original = make_graph(task.task_id, "revision-1", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=original, plan_graph_ref="artifact://plans/identity/1")
    c.record_node_settlement(NodeSettlement(
        task_id=task.task_id,
        revision_id=original.revision_id,
        node_id="arrange-red",
        status="completed",
    ))
    c.request_replan(task.task_id, reason="changed obligation")
    replacement = make_graph(task.task_id, "revision-2", ("arrange-red", "verify"))
    changed_node = replacement.nodes[0].model_copy(update={"capability": "different.obligation"})
    payload = replacement.model_dump(mode="json")
    payload["nodes"][0] = changed_node.model_dump(mode="json")
    payload["graph_digest"] = plan_graph_digest(payload)
    replacement = PlanGraph.model_validate(payload)
    with pytest.raises(AgentTaskError, match="replacement content changed"):
        c.begin_revision_from_delta(
            task.task_id,
            ReplanProposal(
                delta=ReplanDelta(
                    task_id=task.task_id,
                    revision_id=original.revision_id,
                    preserve_node_ids=("arrange-red",),
                    reason="changed obligation",
                ),
                plan_graph=replacement,
                plan_graph_ref="artifact://plans/identity/2",
            ).delta,
            plan_graph=replacement,
            plan_graph_ref="artifact://plans/identity/2",
        )


def test_loop_rejects_result_bound_to_another_node(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="result identity", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-1", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/identity/result")

    def execute(context):
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id="verify",
            tool_id="object.arrange",
            status="succeeded",
        )

    adapter = PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(scene_revision="scene-1", evidence_refs=frozenset({"scene:inventory"})),
    )
    with pytest.raises(PlanningLoopError, match="different task, revision, or node"):
        asyncio.run(adapter.run(task.task_id, scene_revision="scene-1"))


def test_dispatch_does_not_reserve_a_fixed_verify_node_name():
    graph = make_graph("task-dispatch", "revision-1", ("verify",))
    policy = ToolSpecPolicy(
        tool_id="scene.verify",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("scene.verify",),
    )
    dispatch = AgentComposedDispatch(
        graph,
        (policy,),
        AdmissionContext(scene_revision="scene-1"),
    )
    node = graph.nodes[0]
    binding = PlanningExecutionBinding(
        node_id=node.node_id,
        node_digest=plan_node_digest(node),
        obligation_id=node.obligation_id,
        input_binding_digest="4" * 64,
        decision_trace_ref="artifact://trace/verify",
    )
    decision = dispatch.admit_forge_tool(
        "forge_tool_query",
        {
            "task_id": graph.task_id,
            "tool_id": policy.tool_id,
            "arguments": {},
            "planning_binding": binding.model_dump(mode="json"),
        },
    )
    assert decision is not None and decision.allowed


def test_coordinator_rejects_cyclic_plan_graph(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="cycle", verification=TaskVerificationContract(mode="off"))
    nodes = (
        PlanNode(node_id="a", obligation_id="oa", capability="x", dependencies=("b",)),
        PlanNode(node_id="b", obligation_id="ob", capability="y", dependencies=("a",)),
    )
    payload = {
        "schema_version": "paos-plan-graph/v1",
        "task_id": task.task_id,
        "revision_id": "revision-cycle",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json") for node in nodes],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    with pytest.raises(AgentTaskError, match="not a valid DAG"):
        c.expand_discovery_revision(
            task.task_id,
            plan_graph=graph,
            plan_graph_ref="artifact://plans/cycle",
        )


def test_unknown_outcome_stops_without_implicit_replay(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="unknown action", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-1", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/unknown")
    calls = {"count": 0}

    def execute(context):
        calls["count"] += 1
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.arrange",
            status="unknown",
            failure_code="transport_timeout",
        )

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(scene_revision="scene-1", evidence_refs=frozenset({"scene:inventory"})),
    ).run(task.task_id, scene_revision="scene-1"))
    assert result.status == "outcome_unknown"
    assert calls["count"] == 1


def test_replan_budget_is_enforced(tmp_path):
    c = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object(), verifier=None, max_replans=0)
    task = c.create_task(task_description="budget", verification=TaskVerificationContract(mode="off"))
    with pytest.raises(AgentTaskError, match="budget exhausted"):
        c.request_replan(task.task_id, reason="no budget")


def test_discovery_revision_does_not_consume_replan_budget(tmp_path):
    c = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object(), verifier=None, max_replans=1)
    task = c.create_task(task_description="discovery budget", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-discovered", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/discovery-budget")
    awaiting = c.request_replan(task.task_id, reason="first actual recovery")
    assert awaiting.status.value == "awaiting_replan"


def test_planner_plugin_registry_is_explicit_and_separate():
    class DemoPlugin:
        plugin_id = "demo"
        version = "1"

        def compose_plan(self, **kwargs):
            return kwargs["observations"]

        def propose_replan(self, **kwargs):
            return kwargs["context"]

    registry = PlannerPluginRegistry()
    registry.register(DemoPlugin())
    assert registry.get("demo").version == "1"
    assert registry.discover() == ("demo",)


def test_planner_request_supports_task_only_or_agent_selected_context():
    task_only = PlanningRequest(
        task_id="task-1", revision_id="revision-1",
        task_description="place objects in the requested order",
    )
    assert task_only.observations == {}
    observed = PlanningRequest(
        task_id="task-1", revision_id="revision-1",
        task_description="arrange blocks by color",
        verification_goal="layout matches the requested order",
        success_criteria=("all entities are ordered",),
        evidence_refs=("artifact://scene/observation-1",),
        observations={"entities": ["entity://block-1"]},
        available_capabilities=("scene.observe", "object.arrange"),
    )
    assert observed.evidence_refs == ("artifact://scene/observation-1",)


def test_agent_can_choose_plan_materialization_capability(tmp_path):
    c = coordinator(tmp_path)
    names = {tool.name for tool in build_forge_task_tools(c)}
    assert "forge_task_materialize_plan" in names
