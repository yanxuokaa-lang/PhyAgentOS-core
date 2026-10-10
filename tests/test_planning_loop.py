from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.long_horizon import LongHorizonTaskController
from PhyAgentOS.agent.loop import AgentLoop
from PhyAgentOS.agent.planner_plugin import PlannerPluginRegistry, PlanningRequest, ReplanProposal
from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.planning_loop import (
    AgentLoopNodeExecutor,
    EvidenceExecutionContext,
    NodeContextProvider,
    NodeExecutionContext,
    NodeTurnIncompleteError,
    NodeTurnProviderError,
    PlanningLoopAdapter,
    PlanningLoopError,
    PredecessorContext,
    PredecessorExecutionContext,
    StaleNodeContextError,
    _scene_bind_selection_context,
    node_context_prompt_projection,
    resolve_node_argument_sources,
)
from PhyAgentOS.agent.tools.base import Tool
from PhyAgentOS.agent.tools.forge_task import build_forge_task_tools
from PhyAgentOS.agent.tools.forge_tool_api import ForgeToolQueryTool
from PhyAgentOS.agent.tools.registry import ToolRegistry
from PhyAgentOS.config.schema import ForgeConfig
from PhyAgentOS.forge.binding import query_record_provider_blocked
from PhyAgentOS.forge.task import (
    AgentTaskBusyError,
    AgentTaskCoordinator,
    AgentTaskError,
    AgentTaskStatus,
    ToolExecutionRecord,
)
from PhyAgentOS.planning import (
    AdmissionContext,
    NodeSettlement,
    PlanGraph,
    PlanningExecutionBinding,
    PlanNode,
    ReplanDelta,
    ToolResultEnvelope,
    ToolSpecPolicy,
    build_replan_delta,
    plan_graph_digest,
    plan_node_digest,
    reconcile_replan_delta,
    tool_input_binding_digest,
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


@pytest.mark.parametrize(
    ("semantics", "payload", "expected"),
    [
        (
            "query",
            {
                "status": "unavailable",
                "error": {"failure_stage": "provider", "retryable": False},
            },
            True,
        ),
        (
            "query",
            {
                "status": "unavailable",
                "error": {"failure_stage": "request", "retryable": False},
            },
            False,
        ),
        (
            "query",
            {
                "status": "unavailable",
                "error": {"failure_stage": "provider", "retryable": True},
            },
            False,
        ),
        (
            "action",
            {
                "status": "unavailable",
                "error": {"failure_stage": "provider", "retryable": False},
            },
            False,
        ),
    ],
)
def test_query_provider_block_classification_is_provider_neutral(
    semantics, payload, expected
):
    record = SimpleNamespace(
        semantics=semantics,
        status="succeeded",
        response={"data": payload},
    )

    assert query_record_provider_blocked(record) is expected


def test_provider_block_is_not_preemptively_projected_to_replan(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="provider block projection",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-provider-projection", ("inspect",))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/provider-projection",
    )
    record = ToolExecutionRecord(
        record_id="provider-projection-attempt",
        revision_id=graph.revision_id,
        tool_id="perception.describe",
        semantics="query",
        caller_id="test",
        node_id="inspect",
        node_digest=plan_node_digest(graph.nodes[0]),
        obligation_id=graph.nodes[0].obligation_id,
        input_binding_digest=tool_input_binding_digest({}),
        decision_trace_ref="artifact://trace/provider-projection",
        status="succeeded",
        response={
            "data": {
                "status": "unavailable",
                "error": {"failure_stage": "provider", "retryable": False},
            }
        },
    )
    c.store.update(
        task.task_id,
        lambda current: current.active_revision.execution_records.append(record),
        event_type="test_provider_query",
    )

    c._project_query_failure_recovery(task.task_id, record.record_id)

    current = c.get_task(task.task_id)
    assert current.status == AgentTaskStatus.EXECUTING
    assert current.replan_deadline is None
    assert all(
        event["event_type"] != "query_failure_recovery_projected"
        for event in c.store.events(task.task_id)
    )


def test_node_prompt_projects_large_payload_to_catalog_and_resolves_exact_source():
    candidates = [
        {
            "candidate_ref": f"candidate://green/{index}",
            "entity_ref": "entity://green",
            "confidence": 0.9 - index / 100,
            "geometry": [index + offset / 1000 for offset in range(256)],
        }
        for index in range(24)
    ]
    context = NodeExecutionContext(
        task_id="task-1",
        revision_id="revision-1",
        node_id="prepare-green",
        capability="manipulation.prepare",
        dependencies=("propose-green",),
        required_evidence=(),
        input_bindings={"entity_ref": "entity://green"},
        scene_revision="scene-1",
        predecessor_context=(
            PredecessorContext(
                node_id="propose-green",
                status="completed",
                scene_revision="scene-1",
                executions=(
                    PredecessorExecutionContext(
                        record_id="tool-candidates",
                        tool_id="grasp.propose",
                        semantics="query",
                        status="succeeded",
                        arguments={"entity_ref": "entity://green"},
                        response={"data": {"result": {"candidates": candidates}}},
                    ),
                ),
            ),
        ),
    )

    projected = node_context_prompt_projection(context)
    encoded = json.dumps(projected)

    assert len(encoded) < 8_000
    assert "candidate://green/0" in encoded
    assert '"geometry": [0.0' not in encoded
    catalog = projected["predecessor_context"][0]["executions"][0][
        "available_sources"
    ]
    assert {
        "path": ["response", "data", "result", "candidates"],
        "type": "array",
        "count": 24,
        "item_type": "dict",
        "sample_identifiers": [
            {
                "candidate_ref": "candidate://green/0",
                "entity_ref": "entity://green",
                "confidence": 0.9,
            },
            {
                "candidate_ref": "candidate://green/1",
                "entity_ref": "entity://green",
                "confidence": 0.89,
            },
            {
                "candidate_ref": "candidate://green/2",
                "entity_ref": "entity://green",
                "confidence": 0.88,
            },
        ],
    } in catalog
    resolved = resolve_node_argument_sources(
        context,
        {"entity_ref": "entity://green"},
        {
            "candidates": {
                "record_id": "tool-candidates",
                "path": ["response", "data", "result", "candidates"],
            }
        },
    )
    assert resolved == {"entity_ref": "entity://green", "candidates": candidates}


def test_node_prompt_catalog_surfaces_opaque_arm_identity():
    context = NodeExecutionContext(
        task_id="task-capabilities",
        revision_id="revision-1",
        node_id="prepare-green",
        capability="manipulation.prepare",
        dependencies=("capabilities",),
        required_evidence=(),
        input_bindings={},
        scene_revision="scene-1",
        predecessor_context=(
            PredecessorContext(
                node_id="capabilities",
                status="completed",
                scene_revision="scene-1",
                executions=(
                    PredecessorExecutionContext(
                        record_id="tool-capabilities",
                        tool_id="manipulation.capabilities",
                        semantics="query",
                        status="succeeded",
                        arguments={},
                        response={
                            "data": {
                                "arms": [
                                    {"arm_id": "left"},
                                    {"arm_id": "right"},
                                ]
                            }
                        },
                    ),
                ),
            ),
        ),
    )

    projected = node_context_prompt_projection(context)
    encoded = json.dumps(projected)

    assert '"arm_id": "left"' in encoded
    assert '"arm_id": "right"' in encoded


def test_default_node_prompt_distinguishes_geometry_and_producer_projection_sources():
    context = NodeExecutionContext(
        task_id="task-1",
        revision_id="revision-1",
        node_id="prepare-red",
        capability="manipulation.prepare",
        dependencies=("grasp-red",),
        required_evidence=(),
        input_bindings={"entity_ref": "entity://red"},
        scene_revision="scene-1",
        predecessor_context=(),
    )

    prompt = AgentLoopNodeExecutor._default_prompt(context)

    assert "entity geometry (such as grasp.propose)" in prompt
    assert "successful direct-predecessor record (grasp.propose)" in prompt
    assert "candidate_set_ref and candidates" in prompt
    assert "Never assume every projection source is an understanding record" in prompt
    assert "match the producer candidate entity_ref byte-for-byte" in prompt
    assert "do not reuse an alias from an older rejected continuation" in prompt


def test_scene_bind_node_context_projects_current_candidates_without_auto_selecting():
    understand = PlanNode(
        node_id="understand",
        obligation_id="understand-current-scene",
        capability="scene.understand",
    )
    bind = PlanNode(
        node_id="bind",
        obligation_id="bind-required-task-entities",
        capability="scene.bind",
        dependencies=("understand",),
        input_bindings={"constraints": ["bind only required task entities"]},
    )
    graph_payload = {
        "schema_version": "paos-plan-graph/v1",
        "task_id": "task-bind-context",
        "revision_id": "revision-bind-context",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [understand.model_dump(mode="json"), bind.model_dump(mode="json")],
    }
    graph_payload["graph_digest"] = plan_graph_digest(graph_payload)
    graph = PlanGraph.model_validate(graph_payload)
    record = SimpleNamespace(
        record_id="understand-current",
        node_id="understand",
        tool_id="scene.understand",
        semantics="query",
        status="succeeded",
        arguments={"scene_revision": "scene-current"},
        response={"data": {
            "scene_revision": "scene-current",
            "entities": [
                {"entity_ref": "entity://task-a", "category": "task object"},
                {"entity_ref": "entity://task-b", "category": "task object"},
                {"entity_ref": "entity://surface-a", "category": "support surface"},
                {"entity_ref": "entity://surface-b", "category": "support surface"},
            ],
            "ambiguities": [{
                "code": "shared_metric_localization",
                "message": "environment surfaces share a localization",
                "entity_refs": ["entity://surface-a", "entity://surface-b"],
            }],
        }},
        error=None,
    )
    revision = SimpleNamespace(
        revision_id="revision-bind-context",
        plan_graph=graph,
        node_settlements=(SimpleNamespace(
            node_id="understand",
            status="completed",
            scene_revision="scene-current",
            evidence_refs=("tool:understand-current",),
            source_tool_id="scene.understand",
            failure_code=None,
        ),),
        execution_records=(record,),
        discovery_evidence_refs=(),
        fresh_evidence_requirements=(),
        replan_evidence_refs=(),
    )
    task = SimpleNamespace(
        task_id="task-bind-context",
        active_revision=revision,
        primary_skill_binding=None,
        tool_bindings=(),
    )

    context = NodeContextProvider(lambda _: task).build(
        task.task_id, "bind", scene_revision="scene-current"
    )
    projection = node_context_prompt_projection(context)
    prompt = AgentLoopNodeExecutor._default_prompt(context)

    assert projection["scene_bind_selection"]["status"] == "available"
    assert projection["scene_bind_selection"]["source_record_id"] == "understand-current"
    assert projection["scene_bind_selection"]["recommended_unambiguous_entity_refs"] == [
        "entity://task-a", "entity://task-b"
    ]
    assert projection["scene_bind_selection"]["ambiguous_entity_refs"] == [
        "entity://surface-a", "entity://surface-b"
    ]
    assert "submit one forge_plan_select" in prompt
    assert "Do not bind all candidates" in prompt
    assert "does not authorize motion" not in projection["scene_bind_selection"]


def test_scene_bind_node_context_marks_stale_understanding_unavailable():
    node = SimpleNamespace(capability="scene.bind")
    predecessor = PredecessorContext(
        node_id="understand",
        status="completed",
        scene_revision="scene-old",
        executions=(PredecessorExecutionContext(
            record_id="understand-old",
            tool_id="scene.understand",
            semantics="query",
            status="succeeded",
            response={"data": {
                "scene_revision": "scene-old",
                "entities": [{"entity_ref": "entity://old"}],
            }},
        ),),
    )

    selection = _scene_bind_selection_context(
        node, (predecessor,), "scene-current"
    )

    assert selection == {
        "status": "unavailable",
        "reason": "scene.understand predecessor is not from the current scene revision",
        "source_record_id": "understand-old",
    }


def test_scene_bind_node_context_does_not_fabricate_candidates_without_understanding():
    node = SimpleNamespace(capability="scene.bind")

    selection = _scene_bind_selection_context(node, (), "scene-current")

    assert selection == {
        "status": "unavailable",
        "reason": "scene.bind requires one successful current authorized scene.understand record",
    }


def test_scene_bind_node_context_suppresses_recommendations_for_global_ambiguity():
    node = SimpleNamespace(capability="scene.bind")
    predecessor = PredecessorContext(
        node_id="understand",
        status="completed",
        scene_revision="scene-current",
        executions=(PredecessorExecutionContext(
            record_id="understand-global",
            tool_id="scene.understand",
            semantics="query",
            status="succeeded",
            response={"data": {
                "scene_revision": "scene-current",
                "entities": [{"entity_ref": "entity://candidate"}],
                "ambiguities": [{
                    "code": "correspondence_uncertain",
                    "message": "global ambiguity",
                    "entity_refs": [],
                }],
            }},
        ),),
    )

    selection = _scene_bind_selection_context(
        node, (predecessor,), "scene-current"
    )

    assert selection["global_ambiguity"] is True
    assert selection["recommended_unambiguous_entity_refs"] == []


def test_unqualified_source_field_resolves_from_predecessor_arguments():
    context = NodeExecutionContext(
        task_id="task-source-fields",
        revision_id="revision-1",
        node_id="place",
        capability="object.place",
        dependencies=("acquire",),
        required_evidence=(),
        input_bindings={},
        scene_revision="scene-2",
        predecessor_context=(
            PredecessorContext(
                node_id="acquire",
                status="completed",
                scene_revision="scene-2",
                executions=(
                    PredecessorExecutionContext(
                        record_id="acquire-record",
                        tool_id="object.acquire",
                        semantics="action",
                        status="succeeded",
                        arguments={"freshness_ms": 0, "max_age_ms": 1000},
                        response={"status": "succeeded", "data": {"result": {}}},
                    ),
                ),
            ),
        ),
    )

    resolved = resolve_node_argument_sources(
        context,
        {},
        {
            "freshness_ms": {
                "record_id": "acquire-record",
                "path": ["freshness_ms"],
            },
            "max_age_ms": {
                "record_id": "acquire-record",
                "path": ["max_age_ms"],
            },
        },
    )

    assert resolved == {"freshness_ms": 0, "max_age_ms": 1000}


def test_unqualified_source_field_rejects_conflicting_argument_and_response_values():
    context = NodeExecutionContext(
        task_id="task-source-conflict",
        revision_id="revision-1",
        node_id="place",
        capability="object.place",
        dependencies=("acquire",),
        required_evidence=(),
        input_bindings={},
        scene_revision="scene-1",
        predecessor_context=(
            PredecessorContext(
                node_id="acquire",
                status="completed",
                scene_revision="scene-1",
                executions=(
                    PredecessorExecutionContext(
                        record_id="acquire-record",
                        tool_id="object.acquire",
                        semantics="action",
                        status="succeeded",
                        arguments={"freshness_ms": 0},
                        response={"freshness_ms": 20},
                    ),
                ),
            ),
        ),
    )

    with pytest.raises(PlanningLoopError, match="ambiguous"):
        resolve_node_argument_sources(
            context,
            {},
            {
                "freshness_ms": {
                    "record_id": "acquire-record",
                    "path": ["freshness_ms"],
                },
            },
        )


def test_frozen_entity_allows_stale_bind_as_provenance_only():
    node = PlanNode(
        node_id="place-red",
        obligation_id="place-red",
        capability="object.place",
        required_evidence=("tool:bind",),
        input_bindings={"entity_ref": "entity://red"},
    )
    graph_payload = {
        "schema_version": "paos-plan-graph/v1",
        "task_id": "task-stale-bind",
        "revision_id": "revision-stale-bind",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    graph_payload["graph_digest"] = plan_graph_digest(graph_payload)
    graph = PlanGraph.model_validate(graph_payload)
    bind = ToolExecutionRecord(
        record_id="bind-record",
        revision_id="revision-stale-bind",
        tool_id="scene.bind",
        semantics="query",
        caller_id="test",
        status="succeeded",
        arguments={"scene_revision": "scene-old"},
        response={"ok": True, "data": {"scene_revision": "scene-old"}},
        evidence_refs=["tool:bind"],
    )
    revision = SimpleNamespace(
        plan_graph=graph,
        node_settlements=(),
        execution_records=(bind,),
        discovery_evidence_refs=("tool:bind",),
        fresh_evidence_requirements=(),
        replan_evidence_refs=(),
        revision_id="revision-stale-bind",
    )
    task = SimpleNamespace(
        task_id="task-stale-bind",
        active_revision=revision,
        revisions=(revision,),
    )

    context = NodeContextProvider(lambda _: task).build(
        task.task_id,
        node.node_id,
        scene_revision="scene-new",
    )

    assert context.evidence_context == ()


def test_stale_non_bind_discovery_evidence_remains_rejected():
    node = PlanNode(
        node_id="place-red",
        obligation_id="place-red",
        capability="object.place",
        required_evidence=("tool:understand",),
        input_bindings={"entity_ref": "entity://red"},
    )
    graph_payload = {
        "schema_version": "paos-plan-graph/v1",
        "task_id": "task-stale-understand",
        "revision_id": "revision-stale-understand",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    graph_payload["graph_digest"] = plan_graph_digest(graph_payload)
    graph = PlanGraph.model_validate(graph_payload)
    understand = ToolExecutionRecord(
        record_id="understand-record",
        revision_id="revision-stale-understand",
        tool_id="scene.understand",
        semantics="query",
        caller_id="test",
        status="succeeded",
        arguments={"scene_revision": "scene-old"},
        response={"ok": True, "data": {"scene_revision": "scene-old"}},
        evidence_refs=["tool:understand"],
    )
    revision = SimpleNamespace(
        plan_graph=graph,
        node_settlements=(),
        execution_records=(understand,),
        discovery_evidence_refs=("tool:understand",),
        fresh_evidence_requirements=(),
        replan_evidence_refs=(),
        revision_id="revision-stale-understand",
    )
    task = SimpleNamespace(
        task_id="task-stale-understand",
        active_revision=revision,
        revisions=(revision,),
    )

    with pytest.raises(StaleNodeContextError):
        NodeContextProvider(lambda _: task).build(
            task.task_id,
            node.node_id,
            scene_revision="scene-new",
        )


def test_argument_sources_reject_hidden_record_and_literal_collision():
    context = NodeExecutionContext(
        task_id="task-1",
        revision_id="revision-1",
        node_id="prepare",
        capability="manipulation.prepare",
        dependencies=(),
        required_evidence=(),
        input_bindings={},
        scene_revision="scene-1",
        evidence_context=(
            EvidenceExecutionContext(
                revision_id="revision-1",
                record_id="visible",
                tool_id="grasp.propose",
                status="succeeded",
                evidence_refs=("tool:visible",),
                arguments={},
                response={"data": {"candidates": [1, 2]}},
            ),
        ),
    )
    with pytest.raises(PlanningLoopError, match="not visible"):
        resolve_node_argument_sources(
            context,
            {},
            {"candidates": {"record_id": "hidden", "path": ["response"]}},
        )
    with pytest.raises(PlanningLoopError, match="both literal and sourced"):
        resolve_node_argument_sources(
            context,
            {"candidates": []},
            {
                "candidates": {
                    "record_id": "visible",
                    "path": ["response", "data", "candidates"],
                }
            },
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


def test_node_context_projects_exact_direct_predecessor_tool_result(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="prepare persisted grasp candidates",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-candidates", ("grasp", "prepare"))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/candidates",
    )
    candidate = {
        "candidate_ref": "candidate://green/0",
        "entity_ref": "entity://green",
        "score": 0.91,
    }
    execution = ToolExecutionRecord(
        record_id="tool-grasp-candidates",
        revision_id=graph.revision_id,
        tool_id="grasp.propose",
        semantics="query",
        caller_id="agent-task-test",
        node_id="grasp",
        node_digest=plan_node_digest(graph.nodes[0]),
        obligation_id=graph.nodes[0].obligation_id,
        input_binding_digest=tool_input_binding_digest({}),
        decision_trace_ref="artifact://decision/grasp-candidates",
        status="succeeded",
        response={
            "ok": True,
            "data": {
                "candidate_set_ref": "candidate-set://scene-1/head-camera",
                "candidates": [candidate],
            },
        },
        evidence_refs=["tool:tool-grasp-candidates"],
    )
    c.store.update(
        task.task_id,
        lambda current: current.active_revision.execution_records.append(execution),
        event_type="fixture_grasp_query",
    )
    c.record_node_settlement(NodeSettlement(
        task_id=task.task_id,
        revision_id=graph.revision_id,
        node_id="grasp",
        status="completed",
        scene_revision="scene-1",
        evidence_refs=("tool:tool-grasp-candidates",),
        source_tool_id="grasp.propose",
    ))

    context = NodeContextProvider(c.get_task).build(
        task.task_id,
        "prepare",
        scene_revision="scene-1",
    )

    predecessor = context.predecessor_context[0]
    assert len(predecessor.executions) == 1
    assert predecessor.executions[0].record_id == "tool-grasp-candidates"
    assert predecessor.executions[0].response["data"]["candidates"] == [candidate]


def test_root_node_projects_only_required_discovery_query_results(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="select current green geometry for grasp",
        verification=TaskVerificationContract(mode="off"),
    )
    understanding = ToolExecutionRecord(
        record_id="tool-understanding-current",
        revision_id=task.active_revision_id,
        tool_id="scene.understand",
        semantics="query",
        caller_id="agent-task-test",
        arguments={"max_age_ms": 1000},
        status="succeeded",
        response={
            "ok": True,
            "data": {
                "status": "available",
                "scene_revision": "scene-1",
                "entities": [{
                    "entity_ref": "entity://green",
                    "category": "green block",
                    "confidence": 0.98,
                }],
                "spatial_envelopes": [{
                    "entity_ref": "entity://green",
                    "frame_id": "head_camera",
                    "unit": "m",
                    "min_xyz_m": [0.1, 0.2, 0.0],
                    "max_xyz_m": [0.2, 0.3, 0.1],
                }],
            },
        },
        evidence_refs=["tool:tool-understanding-current"],
    )
    unrelated = ToolExecutionRecord(
        record_id="tool-unrelated-target",
        revision_id=task.active_revision_id,
        tool_id="manipulation.target",
        semantics="query",
        caller_id="agent-task-test",
        status="succeeded",
        response={"ok": True, "data": {"status": "available"}},
        evidence_refs=["tool:tool-unrelated-target"],
    )
    c.store.update(
        task.task_id,
        lambda current: current.active_revision.execution_records.extend(
            [understanding, unrelated]
        ),
        event_type="fixture_discovery_queries",
    )
    node = PlanNode(
        node_id="grasp-green",
        obligation_id="propose-current-green-grasp",
        capability="grasp.propose",
        required_evidence=("tool:tool-understanding-current",),
        input_bindings={"entity_ref": "entity://green"},
    )
    payload = {
        "task_id": task.task_id,
        "revision_id": "revision-root-evidence",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/root-evidence",
        discovery_evidence_refs=("tool:tool-understanding-current",),
    )

    context = NodeContextProvider(c.get_task).build(
        task.task_id,
        "grasp-green",
        scene_revision="scene-1",
    )

    assert context.predecessor_context == ()
    assert len(context.evidence_context) == 1
    evidence = context.evidence_context[0]
    assert evidence.record_id == "tool-understanding-current"
    assert evidence.tool_id == "scene.understand"
    assert evidence.arguments == {"max_age_ms": 1000}
    assert evidence.response == understanding.response
    assert all(item.record_id != "tool-unrelated-target" for item in context.evidence_context)


def test_root_node_rejects_discovery_query_with_stale_request_scene(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="reject stale discovery geometry",
        verification=TaskVerificationContract(mode="off"),
    )
    stale = ToolExecutionRecord(
        record_id="tool-understanding-stale-request",
        revision_id=task.active_revision_id,
        tool_id="scene.understand",
        semantics="query",
        caller_id="agent-task-test",
        arguments={
            "scene_revision": "scene-old",
            "observation_ref": "observation://old",
        },
        status="succeeded",
        response={
            "ok": True,
            "data": {
                "status": "available",
                "entities": [{"entity_ref": "entity://old-green"}],
            },
        },
        evidence_refs=["tool:tool-understanding-stale-request"],
    )
    c.store.update(
        task.task_id,
        lambda current: current.active_revision.execution_records.append(stale),
        event_type="fixture_stale_discovery_query",
    )
    node = PlanNode(
        node_id="grasp-old-green",
        obligation_id="reject-old-green",
        capability="grasp.propose",
        required_evidence=("tool:tool-understanding-stale-request",),
    )
    payload = {
        "task_id": task.task_id,
        "revision_id": "revision-stale-request",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=PlanGraph.model_validate(payload),
        plan_graph_ref="artifact://plans/stale-request",
        discovery_evidence_refs=("tool:tool-understanding-stale-request",),
    )

    with pytest.raises(StaleNodeContextError, match="stale scene revision"):
        NodeContextProvider(c.get_task).build(
            task.task_id,
            node.node_id,
            scene_revision="scene-new",
        )


def test_root_node_accepts_refresh_query_source_scene_as_provenance():
    node = PlanNode(
        node_id="consume-refreshed-observation",
        obligation_id="consume-current-observation",
        capability="scene.understand",
        required_evidence=("tool:tool-observe-refresh",),
    )
    payload = {
        "task_id": "task-refresh-evidence",
        "revision_id": "revision-refresh-evidence",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    record = ToolExecutionRecord(
        record_id="tool-observe-refresh",
        revision_id="revision-discovery",
        tool_id="scene.observe",
        semantics="query",
        caller_id="agent-task-test",
        arguments={"scene_revision": "scene-old"},
        status="succeeded",
        response={
            "ok": True,
            "data": {"status": "available", "scene_revision": "scene-new"},
        },
        evidence_refs=["tool:tool-observe-refresh"],
    )
    revision = SimpleNamespace(
        revision_id="revision-refresh-evidence",
        plan_graph=PlanGraph.model_validate(payload),
        node_settlements=(),
        discovery_evidence_refs=("tool:tool-observe-refresh",),
        execution_records=(record,),
        fresh_evidence_requirements=(),
        replan_evidence_refs=(),
    )
    task = SimpleNamespace(
        active_revision=revision,
        revisions=(revision,),
        primary_skill_binding=None,
        tool_bindings=(SimpleNamespace(
            tool_id="scene.observe",
            planning_policy=SimpleNamespace(refreshes_scene=True),
        ),),
    )

    context = NodeContextProvider(lambda _: task).build(
        "task-refresh-evidence",
        node.node_id,
        scene_revision="scene-new",
    )

    assert context.evidence_context[0].arguments == {"scene_revision": "scene-old"}
    assert context.evidence_context[0].response == record.response


def test_context_preserves_historical_predecessor_after_scene_progression(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="stale context", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-1", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/stale")
    c.record_node_settlement(NodeSettlement(
        task_id=task.task_id, revision_id=graph.revision_id, node_id="arrange-red",
        status="completed", scene_revision="scene-1",
    ))
    provider = NodeContextProvider(c.get_task)
    context = provider.build(task.task_id, "verify", scene_revision="scene-2")
    assert context.scene_revision == "scene-2"
    assert context.predecessor_context[0].scene_revision == "scene-1"


def test_recovery_context_retains_stale_required_predecessor_as_provenance(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="recover after changed scene",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-recovery-context", ("observe", "arrange-red"))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/recovery/stale-predecessor",
    )
    c.record_node_settlement(NodeSettlement(
        task_id=task.task_id,
        revision_id=graph.revision_id,
        node_id="observe",
        status="completed",
        evidence_refs=("scene:inventory",),
        scene_revision="scene-1",
    ))
    provider = NodeContextProvider(c.get_task)

    with pytest.raises(StaleNodeContextError):
        provider.build(task.task_id, "arrange-red", scene_revision="scene-2")

    recovery = provider.build(
        task.task_id,
        "arrange-red",
        scene_revision="scene-2",
        allow_stale_predecessors=True,
    )
    assert recovery.scene_revision == "scene-2"
    assert recovery.predecessor_context[0].scene_revision == "scene-1"


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
        return ToolResultEnvelope(task_id=context.task_id, revision_id=context.revision_id, node_id=context.node_id, tool_id="scene.verify" if context.node_id == "verify" else "object.arrange", status="succeeded", evidence_refs=(f"placed:{context.node_id}",) if context.node_id != "verify" else ())

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


def test_planning_loop_reconciles_recovery_only_plugin_delta(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="replace failed work with recovery query",
        verification=TaskVerificationContract(mode="off"),
    )
    source = make_graph(task.task_id, "revision-1", ("completed", "failed"))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=source,
        plan_graph_ref="artifact://plans/plugin-effective/1",
    )
    calls: list[tuple[str, str]] = []

    def execute(context):
        calls.append((context.revision_id, context.node_id))
        failed = context.revision_id == source.revision_id and context.node_id == "failed"
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="test.query",
            status="failed" if failed else "succeeded",
            failure_code="no_result" if failed else None,
            evidence_refs=() if failed else (f"placed:{context.node_id}",),
        )

    def replan(_graph, _settlement, delta, _context):
        return ReplanProposal(
            delta=delta,
            plan_graph=make_graph(task.task_id, "revision-2", ("recovery-query",)),
            plan_graph_ref="artifact://plans/plugin-effective/2",
        )

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1",
            evidence_refs=frozenset({"scene:inventory"}),
        ),
        replan_proposer=replan,
    ).run(task.task_id, scene_revision="scene-1"))

    assert result.status == "completed"
    assert calls == [
        ("revision-1", "completed"),
        ("revision-1", "failed"),
        ("revision-2", "recovery-query"),
    ]
    active = c.get_task(task.task_id).active_revision
    assert active.preserved_node_ids == ()
    assert [item.node_id for item in active.node_settlements] == ["recovery-query"]


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


def test_replan_rejects_preserved_node_missing_from_replacement_graph(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="missing preserved node",
        verification=TaskVerificationContract(mode="off"),
    )
    original = make_graph(task.task_id, "revision-1", ("arrange-red", "verify"))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=original,
        plan_graph_ref="artifact://plans/preserve/1",
    )
    c.record_node_settlement(NodeSettlement(
        task_id=task.task_id,
        revision_id=original.revision_id,
        node_id="arrange-red",
        status="completed",
    ))
    c.request_replan(task.task_id, reason="replace remaining work")
    replacement = make_graph(task.task_id, "revision-2", ("verify",))

    with pytest.raises(AgentTaskError, match="absent from replacement graph: arrange-red"):
        c.begin_revision_from_delta(
            task.task_id,
            ReplanDelta(
                task_id=task.task_id,
                revision_id=original.revision_id,
                preserve_node_ids=("arrange-red",),
                reason="replace remaining work",
            ),
            plan_graph=replacement,
            plan_graph_ref="artifact://plans/preserve/2",
        )


def test_replan_effective_delta_omits_historical_node_absent_from_replacement():
    source = make_graph("task-effective", "revision-1", ("completed", "failed"))
    settlement = NodeSettlement(
        task_id=source.task_id,
        revision_id=source.revision_id,
        node_id="failed",
        status="failed",
    )
    delta = build_replan_delta(source, settlement)
    replacement = make_graph(source.task_id, "revision-2", ("recovery-query",))

    effective = reconcile_replan_delta(source, delta, replacement)

    assert delta.preserve_node_ids == ("completed",)
    assert effective.preserve_node_ids == ()
    assert effective.retry_parent_node_id == "failed"


def test_recovery_only_effective_delta_passes_strict_revision_admission(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="replace failed work with current recovery",
        verification=TaskVerificationContract(mode="off"),
    )
    source = make_graph(task.task_id, "revision-1", ("completed", "failed"))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=source,
        plan_graph_ref="artifact://plans/effective/1",
    )
    c.record_node_settlement(NodeSettlement(
        task_id=task.task_id,
        revision_id=source.revision_id,
        node_id="completed",
        status="completed",
    ))
    failed = NodeSettlement(
        task_id=task.task_id,
        revision_id=source.revision_id,
        node_id="failed",
        status="failed",
    )
    c.record_node_settlement(failed)
    replacement = make_graph(task.task_id, "revision-2", ("recovery-query",))
    effective = reconcile_replan_delta(source, build_replan_delta(source, failed), replacement)

    c.request_replan(task.task_id, reason="current recovery query")
    c.begin_revision_from_delta(
        task.task_id,
        effective,
        plan_graph=replacement,
        plan_graph_ref="artifact://plans/effective/2",
    )

    active = c.get_task(task.task_id).active_revision
    assert active.preserved_node_ids == ()
    assert active.node_settlements == []
    assert tuple(node.node_id for node in active.plan_graph.nodes) == ("recovery-query",)
    assert active.execution_records == []


def test_replan_effective_delta_preserves_unchanged_included_node():
    source = make_graph("task-effective", "revision-1", ("completed", "failed"))
    settlement = NodeSettlement(
        task_id=source.task_id,
        revision_id=source.revision_id,
        node_id="failed",
        status="failed",
    )
    replacement = make_graph(source.task_id, "revision-2", ("completed", "recovery-query"))

    effective = reconcile_replan_delta(
        source,
        build_replan_delta(source, settlement),
        replacement,
    )

    assert effective.preserve_node_ids == ("completed",)


def test_replan_effective_delta_rejects_changed_preserve_candidate():
    source = make_graph("task-effective", "revision-1", ("completed", "failed"))
    settlement = NodeSettlement(
        task_id=source.task_id,
        revision_id=source.revision_id,
        node_id="failed",
        status="failed",
    )
    replacement = make_graph(source.task_id, "revision-2", ("completed", "recovery-query"))
    payload = replacement.model_dump(mode="json")
    payload["nodes"][0]["capability"] = "different.obligation"
    payload["graph_digest"] = plan_graph_digest(payload)
    changed = PlanGraph.model_validate(payload)

    with pytest.raises(ValueError, match="replacement content changed"):
        reconcile_replan_delta(source, build_replan_delta(source, settlement), changed)


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
        input_binding_digest=tool_input_binding_digest({}),
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
    current = c.get_task(task.task_id)
    assert result.status == "blocked"
    assert result.last_failure == "reconciliation_required:arrange-red"
    assert current.status.value == "awaiting_replan"
    assert calls["count"] == 1


@pytest.mark.parametrize("decision", ["stop", "replan"])
def test_unknown_outcome_always_requires_reconciliation_before_recovery_decision(
    tmp_path, decision
):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="unknown action decision",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-unknown-decision", ("move", "verify"))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/unknown-decision",
    )
    calls = {"execute": 0, "replan": 0}

    def execute(context):
        calls["execute"] += 1
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.move",
            status="unknown",
            world_change_started=True,
            outcome_known=False,
            invocation_id="invocation://move/unknown",
            failure_code="controller_command_error",
        )

    def replan(*_):
        calls["replan"] += 1
        raise AssertionError("unknown outcome must reconcile before replan")

    adapter = PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        recovery_policy=lambda *_: decision,
        replan_proposer=replan,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1", evidence_refs=frozenset({"scene:inventory"})
        ),
    )
    result = asyncio.run(adapter.run(task.task_id, scene_revision="scene-1"))

    assert result.status == "blocked"
    assert result.last_failure == "reconciliation_required:move"
    assert calls == {"execute": 1, "replan": 0}
    assert c.get_task(task.task_id).status.value == "awaiting_replan"


def test_unknown_outcome_replay_is_read_only_then_requires_reconciliation(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="unknown action reducer replay",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-unknown-replay", ("move", "verify"))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/unknown-replay",
    )
    calls = {"execute": 0, "replay": 0}

    def execute(context):
        calls["execute"] += 1
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.move",
            status="unknown",
            world_change_started=True,
            outcome_known=False,
            invocation_id="invocation://move/unknown-replay",
            failure_code="controller_command_error",
        )

    adapter = PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        recovery_policy=lambda *_: "replay",
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1", evidence_refs=frozenset({"scene:inventory"})
        ),
    )
    original_replay = adapter.reducer_replay

    def replay(*args, **kwargs):
        calls["replay"] += 1
        return original_replay(*args, **kwargs)

    adapter.reducer_replay = replay
    result = asyncio.run(adapter.run(task.task_id, scene_revision="scene-1"))

    assert result.status == "blocked"
    assert result.last_failure == "reconciliation_required:move"
    assert calls == {"execute": 1, "replay": 1}
    assert c.get_task(task.task_id).status.value == "awaiting_replan"


def test_unknown_outcome_converges_task_to_recovery_state_without_retry(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="unknown action recovery", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-unknown-recovery", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/unknown-recovery")

    def execute(context):
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.arrange",
            status="unknown",
            failure_code="action_poll_budget_exhausted",
        )

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        recovery_policy=lambda *_: "replan",
        replan_proposer=lambda *_: None,
        admission_context_provider=lambda _: AdmissionContext(scene_revision="scene-1", evidence_refs=frozenset({"scene:inventory"})),
    ).run(task.task_id, scene_revision="scene-1"))
    current = c.get_task(task.task_id)
    assert result.status == "blocked"
    assert current.status.value == "awaiting_replan"
    assert current.active_revision.node_settlements[-1].status == "outcome_unknown"
    assert current.execution_records == []


def test_recovery_stop_does_not_advance_to_dependent_node(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="explicit stop", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-stop", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/recovery/stop")
    calls: list[str] = []

    def execute(context):
        calls.append(context.node_id)
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.arrange",
            status="failed",
            failure_code="gripper_slip",
        )

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1", evidence_refs=frozenset({"scene:inventory"})
        ),
        recovery_policy=lambda *_: "stop",
    ).run(task.task_id, scene_revision="scene-1"))
    assert result.status == "failed"
    assert result.completed_nodes == ()
    assert calls == ["arrange-red"]
    current = c.get_task(task.task_id)
    assert current.status.value == result.status
    assert current.terminal is True
    assert current.replan_deadline is None


def test_recovery_replay_only_reduces_persisted_facts(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="reducer replay", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-replay", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/recovery/replay")
    calls: list[str] = []

    def execute(context):
        calls.append(context.node_id)
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.arrange",
            status="failed",
            failure_code="transport_timeout",
        )

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1", evidence_refs=frozenset({"scene:inventory"})
        ),
        recovery_policy=lambda *_: "replay",
    ).run(task.task_id, scene_revision="scene-1"))
    assert result.status == "replay_required"
    assert result.last_failure == "reducer_replay_only:arrange-red"
    assert calls == ["arrange-red"]
    assert len(c.get_task(task.task_id).revisions) == 2


def test_replan_provider_failure_enters_existing_recovery_with_original_failure(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="preserve the original grasp failure",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-replan-provider", ("arrange-red",))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/recovery/provider-failure",
    )

    def execute(context):
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="grasp.propose",
            status="failed",
            failure_code="invalid_arguments",
        )

    def replan(*_):
        raise ValueError("recovery model returned no unique decision; api_key=private-test-value")

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1",
            evidence_refs=frozenset({"scene:inventory"}),
        ),
        replan_proposer=replan,
        recovery_policy=lambda *_: "replan",
    ).run(task.task_id, scene_revision="scene-1"))

    assert result.status == "awaiting_replan"
    assert result.last_failure == (
        "replan_proposer_error:ValueError:arrange-red:invalid_arguments"
    )
    current = c.get_task(task.task_id)
    assert current.status.value == "awaiting_replan"
    assert current.replan_deadline is not None
    assert current.active_revision.node_settlements[0].failure_code == "invalid_arguments"
    assert any("recovery model returned no unique decision" in error for error in current.evidence_errors)
    assert all("private-test-value" not in error for error in current.evidence_errors)
    assert current.active_revision.execution_records == []


def test_replan_provider_and_state_failure_persist_terminal_task(tmp_path):
    c = AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=object(),
        verifier=None,
        max_replans=0,
    )
    task = c.create_task(
        task_description="terminate unavailable recovery",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-recovery-terminal", ("arrange-red",))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/recovery/terminal",
    )

    def execute(context):
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="grasp.propose",
            status="failed",
            failure_code="invalid_arguments",
        )

    def replan(*_):
        raise ValueError("recovery model returned no unique decision")

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1",
            evidence_refs=frozenset({"scene:inventory"}),
        ),
        replan_proposer=replan,
        recovery_policy=lambda *_: "replan",
    ).run(task.task_id, scene_revision="scene-1"))

    assert result.status == "failed"
    assert result.last_failure == (
        "replan_proposer_error:ValueError:arrange-red:invalid_arguments:"
        "recovery_state_error:AgentTaskError"
    )
    current = c.get_task(task.task_id)
    assert current.status.value == "failed"
    assert current.terminal is True
    assert current.replan_deadline is None
    assert current.active_revision.node_settlements[0].failure_code == "invalid_arguments"
    assert current.active_revision.execution_records == []
    assert c.store.events(task.task_id)[-1]["event_type"] == "plan_replan_outcome_recorded"


def test_reducer_replay_does_not_require_scene_refresh_or_execute_again(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="replay changed result", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-replay-change", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/recovery/replay-change")
    calls: list[str] = []

    def execute(context):
        calls.append(context.node_id)
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.arrange",
            status="unknown",
            world_changed=True,
            world_change_started=True,
            outcome_known=False,
            new_scene_revision="scene-2",
            failure_code="transport_lost_after_effect",
        )

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1", evidence_refs=frozenset({"scene:inventory"})
        ),
        recovery_policy=lambda *_: "replay",
    ).run(task.task_id, scene_revision="scene-1"))
    assert result.status == "blocked"
    assert result.last_failure == "reconciliation_required:arrange-red"
    assert calls == ["arrange-red"]
    assert c.get_task(task.task_id).status.value == "awaiting_replan"


def test_world_changing_failure_requires_scene_refresh_before_replan(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="refresh before recovery", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-refresh", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/recovery/refresh")
    admission_calls = {"count": 0}

    def admission(_):
        admission_calls["count"] += 1
        return AdmissionContext(scene_revision="scene-1", evidence_refs=frozenset({"scene:inventory"}))

    def execute(context):
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.arrange",
            status="failed",
            world_changed=True,
            world_change_started=True,
            new_scene_revision="scene-2",
            failure_code="object_dropped",
        )

    proposed = {"called": False}

    def replan(*_):
        proposed["called"] = True
        raise AssertionError("replan must wait for refreshed scene")

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=admission,
        replan_proposer=replan,
        recovery_policy=lambda *_: "replan",
    ).run(task.task_id, scene_revision="scene-1"))
    assert result.status == "blocked"
    assert result.last_failure == "scene_refresh_required:scene-2"
    assert not proposed["called"]
    assert admission_calls["count"] == 2


def test_world_changing_failure_resumes_replan_after_scene_refresh(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="resume refreshed recovery", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-refresh-resume", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/recovery/refresh-resume")
    current_scene = {"value": "scene-1"}

    def execute(context):
        failed = context.revision_id == graph.revision_id
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.arrange",
            status="failed" if failed else "succeeded",
            world_changed=failed,
            world_change_started=True if failed else None,
            new_scene_revision="scene-2" if failed else None,
            failure_code="object_dropped" if failed else None,
            evidence_refs=() if context.node_id == "verify" else ("placed:arrange-red",),
        )

    def replan(_graph, _settlement, delta, _context):
        return ReplanProposal(
            delta=delta,
            plan_graph=make_graph(task.task_id, "revision-refresh-resumed", ("arrange-red", "verify")),
            plan_graph_ref="artifact://plans/recovery/refresh-resumed",
        )

    adapter = PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision=current_scene["value"], evidence_refs=frozenset({"scene:inventory"})
        ),
        replan_proposer=replan,
        recovery_policy=lambda *_: "replan",
    )
    blocked = asyncio.run(adapter.run(task.task_id, scene_revision="scene-1"))
    assert blocked.last_failure == "scene_refresh_required:scene-2"

    current_scene["value"] = "scene-2"
    resumed = asyncio.run(adapter.run(task.task_id, scene_revision="scene-2"))
    assert resumed.status == "completed"
    assert c.get_task(task.task_id).active_revision.retry_parent_node_id == "arrange-red"


def test_unknown_outcome_cannot_enter_execution_replan(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="reconcile unknown", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-unknown-replan", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/recovery/unknown")
    proposals = {"count": 0}

    def execute(context):
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.arrange",
            status="unknown",
            world_change_started=True,
            outcome_known=False,
            failure_code="transport_lost",
        )

    def replan(*_):
        proposals["count"] += 1
        raise AssertionError("unknown outcome must reconcile before execution replan")

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1", evidence_refs=frozenset({"scene:inventory"})
        ),
        replan_proposer=replan,
        recovery_policy=lambda *_: "replan",
    ).run(task.task_id, scene_revision="scene-1"))
    assert result.status == "blocked"
    assert result.last_failure == "reconciliation_required:arrange-red"
    assert proposals["count"] == 0


def test_replan_receives_refreshed_scene_context(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="refresh planner context", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-refresh-context", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/recovery/refresh-context")
    admission_calls = {"count": 0}
    proposed_scenes: list[str] = []

    def admission(_task_id):
        admission_calls["count"] += 1
        return AdmissionContext(
            scene_revision="scene-1" if admission_calls["count"] == 1 else "scene-2",
            evidence_refs=frozenset({"scene:inventory"}),
        )

    def execute(context):
        failed = context.revision_id == graph.revision_id
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.arrange",
            status="failed" if failed else "succeeded",
            world_changed=failed,
            world_change_started=True if failed else None,
            new_scene_revision="scene-2" if failed else None,
            failure_code="object_dropped" if failed else None,
            evidence_refs=() if context.node_id == "verify" else ("placed:arrange-red",),
        )

    def replan(_graph, _settlement, delta, context):
        proposed_scenes.append(context.scene_revision)
        return ReplanProposal(
            delta=delta,
            plan_graph=make_graph(task.task_id, "revision-refresh-context-retry", ("arrange-red", "verify")),
            plan_graph_ref="artifact://plans/recovery/refresh-context-retry",
        )

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=admission,
        replan_proposer=replan,
        recovery_policy=lambda *_: "replan",
    ).run(task.task_id, scene_revision="scene-1"))
    assert result.status == "completed"
    assert proposed_scenes == ["scene-2"]


def test_replan_persists_retry_parent_lineage_on_new_revision(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(task_description="persist retry lineage", verification=TaskVerificationContract(mode="off"))
    graph = make_graph(task.task_id, "revision-lineage", ("arrange-red", "verify"))
    c.expand_discovery_revision(task.task_id, plan_graph=graph, plan_graph_ref="artifact://plans/recovery/lineage/1")

    def execute(context):
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.arrange",
            status="failed" if context.revision_id == graph.revision_id else "succeeded",
            failure_code="gripper_slip" if context.revision_id == graph.revision_id else None,
            evidence_refs=() if context.node_id == "verify" else ("placed:arrange-red",),
        )

    def replan(_graph, _settlement, delta, _context):
        replacement = make_graph(task.task_id, "revision-lineage-retry", ("arrange-red", "verify"))
        return ReplanProposal(
            delta=delta,
            plan_graph=replacement,
            plan_graph_ref="artifact://plans/recovery/lineage/2",
        )

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1", evidence_refs=frozenset({"scene:inventory"})
        ),
        replan_proposer=replan,
        recovery_policy=lambda *_: "replan",
    ).run(task.task_id, scene_revision="scene-1"))
    assert result.status == "completed"
    assert c.get_task(task.task_id).active_revision.retry_parent_node_id == "arrange-red"


def test_replan_budget_is_enforced(tmp_path):
    c = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object(), verifier=None, max_replans=0)
    task = c.create_task(task_description="budget", verification=TaskVerificationContract(mode="off"))
    with pytest.raises(AgentTaskError, match="budget exhausted"):
        c.request_replan(task.task_id, reason="no budget")


def test_replan_failure_does_not_overwrite_waiting_for_user(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="preserve clarification state",
        verification=TaskVerificationContract(mode="off"),
    )
    c.request_clarification(task.task_id, question="Which object should move?")

    with pytest.raises(AgentTaskError, match="cannot fail replan"):
        c.fail_replan(task.task_id, reason="concurrent recovery failure")

    assert c.get_task(task.task_id).status.value == "waiting_for_user"


def test_replan_failure_keeps_unknown_world_owned_by_same_task(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="unknown world effect",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-unknown-world", ("arrange-red",))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/unknown-world",
    )
    c.store.update(
        task.task_id,
        lambda current: current.active_revision.node_settlements.append(
            NodeSettlement(
                task_id=task.task_id,
                revision_id=graph.revision_id,
                node_id="arrange-red",
                status="outcome_unknown",
                world_change_started=True,
                requires_replan=True,
            )
        ),
        event_type="test_unknown_world_effect",
    )

    result = c.fail_replan(task.task_id, reason="recovery proposal unavailable")

    assert result.status is AgentTaskStatus.AWAITING_REPLAN
    assert result.replan_deadline is not None
    assert "world reconciliation remains required" in result.evidence_errors[-1]
    event = c.store.events(task.task_id)[-1]
    assert event["event_type"] == "plan_replan_outcome_recorded"
    assert event["payload"]["deferred_for_reconciliation"] is True


def test_replan_failure_ignores_unknown_execution_from_superseded_revision(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="superseded unknown world effect",
        verification=TaskVerificationContract(mode="off"),
    )
    first = make_graph(task.task_id, "revision-old-unknown", ("arrange-red",))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=first,
        plan_graph_ref="artifact://plans/old-unknown",
    )
    c.store.update(
        task.task_id,
        lambda current: current.active_revision.node_settlements.append(
            NodeSettlement(
                task_id=task.task_id,
                revision_id=first.revision_id,
                node_id="arrange-red",
                status="outcome_unknown",
                world_change_started=True,
                requires_replan=True,
            )
        ),
        event_type="test_superseded_unknown_world_effect",
    )
    c.request_replan(task.task_id, reason="fresh scene reconciled")
    second = make_graph(task.task_id, "revision-after-refresh", ("arrange-red",))
    c.begin_revision(
        task.task_id,
        reason="fresh scene reconciliation",
        plan_graph=second,
        plan_graph_ref="artifact://plans/after-refresh",
    )

    result = c.fail_replan(task.task_id, reason="new revision recovery unavailable")

    assert result.status is AgentTaskStatus.FAILED
    event = c.store.events(task.task_id)[-1]
    assert event["payload"]["deferred_for_reconciliation"] is False


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


def test_agent_loop_controller_without_planner_defaults_to_stop(tmp_path):
    c = coordinator(tmp_path)
    loop = object.__new__(AgentLoop)
    loop.forge_task_coordinator = c
    loop._planning_context_provider = lambda _: AdmissionContext(scene_revision="scene-1")
    loop._planner_plugin = None

    controller = loop.build_long_horizon_controller()

    assert controller.adapter is not None
    assert controller.adapter.replan_proposer is None
    assert controller.adapter.recovery_policy is None


def test_agent_loop_controller_wires_optional_planner_recovery_policy(tmp_path):
    class DemoPlugin:
        def compose_plan(self, **kwargs):
            return kwargs["request"]

        def propose_replan(self, **kwargs):
            return kwargs["context"]

        def select_recovery(self, **kwargs):
            return "replay" if kwargs["settlement"].status == "outcome_unknown" else "replan"

    c = coordinator(tmp_path)
    loop = object.__new__(AgentLoop)
    loop.forge_task_coordinator = c
    loop._planning_context_provider = lambda _: AdmissionContext(scene_revision="scene-1")
    loop._planner_plugin = DemoPlugin()

    controller = loop.build_long_horizon_controller()

    assert controller.adapter is not None
    assert controller.adapter.replan_proposer is not None
    assert controller.adapter.recovery_policy is not None
    settlement = NodeSettlement(
        task_id="task-1",
        revision_id="revision-1",
        node_id="node-1",
        status="outcome_unknown",
    )
    assert controller.adapter.recovery_policy(None, settlement, None, None) == "replay"


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


def _executor_context() -> NodeExecutionContext:
    return NodeExecutionContext(
        task_id="task-resume",
        revision_id="revision-resume",
        node_id="prepare",
        capability="manipulation.prepare",
        dependencies=(),
        required_evidence=(),
        input_bindings={},
        scene_revision="scene-1",
    )


def _terminal_record(*, semantics="query", status="succeeded"):
    return SimpleNamespace(
        record_id="tool-1",
        node_id="prepare",
        terminal=True,
        semantics=semantics,
        status=status,
        tool_id="manipulation.prepare",
        invocation_id="invocation-1" if semantics in {"action", "session"} else None,
        evidence_refs=("tool:tool-1",),
        response={
            "ok": status == "succeeded",
            "data": {
                "status": "available",
                "world_change_started": status == "unknown",
                "outcome_known": status != "unknown",
            },
        },
        error=None,
    )


class _SelectionTool(Tool):
    name = "forge_tool_query"
    description = "Local no-motion selection execution fixture"
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
            "tool_id": {"type": "string"},
            "arguments": {"type": "object"},
            "use_selected_arguments": {"type": "boolean"},
            "planning_binding": {"type": "object"},
        },
        "required": ["task_id", "tool_id", "arguments", "use_selected_arguments", "planning_binding"],
    }

    def __init__(self, records, *, record=None, wrapper_error=False):
        self.records = records
        self.record = record
        self.wrapper_error = wrapper_error
        self.calls = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)
        self.records.append(self.record if self.record is not None else _terminal_record())
        if self.wrapper_error:
            raise RuntimeError("transport failed after persistence")
        return '{"ok":true}'


@pytest.fixture
def selected_node():
    records = []
    task = SimpleNamespace(
        active_revision_id="revision-resume",
        active_revision=SimpleNamespace(execution_records=records),
        execution_records=records,
    )
    selection = {
        "execution_tool": "forge_tool_query",
        "tool_id": "manipulation.prepare",
        "planning_binding": {"node_id": "prepare"},
    }

    class Client:
        def __init__(self):
            self.calls = []
            self.result = {
                "status": "succeeded",
                "data": {"world_change_started": True, "outcome_known": True},
            }

        async def invocation_status(self, invocation_id):
            self.calls.append(("status", invocation_id))
            return {"status": "running"}

        async def invocation_result(self, invocation_id):
            self.calls.append(("result", invocation_id))
            return self.result

    class Coordinator:
        def __init__(self):
            self.client = Client()

        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            return selection

        def observe_action(self, _task_id, invocation_id, response, *, reconcile_settlement=True):
            record = records[0]
            assert invocation_id == record.invocation_id
            record.response = response
            if reconcile_settlement:
                record.status = response["status"]
                record.terminal = record.status in {"succeeded", "failed", "unknown"}

        observe_session = observe_action

    class Loop:
        def __init__(self):
            self.tools = ToolRegistry()
            self.model_calls = 0

        async def run_node_turn(self, **_kwargs):
            self.model_calls += 1
            raise AssertionError("pending selection must not call the model")

    return SimpleNamespace(
        records=records, coordinator=Coordinator(), loop=Loop(), selection=selection,
    )


@pytest.mark.parametrize("status", ["succeeded", "failed", "unknown"])
def test_pending_selection_durable_terminal_result_outranks_wrapper_exception(selected_node, status):
    state = selected_node
    state.loop.tools.register(_SelectionTool(
        state.records, record=_terminal_record(status=status), wrapper_error=True,
    ))
    executor = AgentLoopNodeExecutor(state.loop, state.coordinator)

    result = asyncio.run(executor(_executor_context()))
    replay = asyncio.run(executor(_executor_context()))

    assert result.status == replay.status == status
    assert state.loop.model_calls == 0
    assert len(state.loop.tools.get("forge_tool_query").calls) == 1
    assert len(state.records) == 1


@pytest.mark.parametrize("semantics", ["action", "session"])
@pytest.mark.parametrize("status", ["succeeded", "unknown"])
def test_pending_selection_wrapper_error_reconciles_original_invocation(selected_node, semantics, status):
    state = selected_node
    record = _terminal_record(semantics=semantics, status="accepted")
    record.terminal = False
    state.selection["execution_tool"] = "forge_tool_start"
    state.coordinator.client.result = {
        "status": status,
        "data": {"world_change_started": True, "outcome_known": status != "unknown"},
    }
    tool = _SelectionTool(state.records, record=record, wrapper_error=True)
    tool.name = "forge_tool_start"
    state.loop.tools.register(tool)
    executor = AgentLoopNodeExecutor(state.loop, state.coordinator, max_action_polls=1)

    result = asyncio.run(executor(_executor_context()))
    replay = asyncio.run(executor(_executor_context()))

    assert result.status == replay.status == status
    assert result.world_change_started is True
    assert result.outcome_known is (status != "unknown")
    assert state.loop.model_calls == 0
    assert len(tool.calls) == 1
    assert state.coordinator.client.calls == [
        ("status", "invocation-1"), ("result", "invocation-1"),
    ]


def test_pending_selection_still_uses_registry_guard_without_blind_retry(selected_node):
    state = selected_node
    tool = _SelectionTool(state.records)
    state.loop.tools.register(tool)
    guarded = []

    def reject(name, params):
        guarded.append((name, params))
        return "Error: motion authorization denied"

    state.loop.tools.set_execution_guard(reject)
    with pytest.raises(NodeTurnIncompleteError, match="motion authorization denied"):
        asyncio.run(AgentLoopNodeExecutor(state.loop, state.coordinator)(_executor_context()))

    assert len(guarded) == 1
    assert guarded[0][1]["planning_binding"] == state.selection["planning_binding"]
    assert guarded[0][1]["use_selected_arguments"] is True
    assert state.records == tool.calls == []
    assert state.loop.model_calls == 0


def test_pending_selection_without_execution_record_remains_incomplete(selected_node):
    state = selected_node
    state.loop.tools.register(_SelectionTool(state.records))
    state.loop.tools.set_execution_guard(lambda *_args: '{"ok":false}')

    with pytest.raises(NodeTurnIncompleteError, match="tool_wrapper_rejected"):
        asyncio.run(AgentLoopNodeExecutor(state.loop, state.coordinator)(_executor_context()))

    assert state.records == []
    assert state.loop.model_calls == 0


@pytest.mark.parametrize(
    ("entity_refs", "expected_status", "expected_error"),
    [
        (["entity://e1", "entity://e2"], "succeeded", None),
        ([], None, "scene_bind_missing_entity_refs"),
    ],
)
def test_scene_bind_pending_selection_crosses_wrapper_boundary_or_reports_exact_rejection(
    entity_refs, expected_status, expected_error,
):
    records = [SimpleNamespace(
        record_id="understand-1",
        node_id="understand",
        tool_id="scene.understand",
        semantics="query",
        status="succeeded",
        terminal=True,
        revision_id="revision-bind",
        arguments={},
        response={
            "data": {
                "entities": [
                    {"entity_ref": "entity://e1", "category": "cube"},
                    {"entity_ref": "entity://e2", "category": "cube"},
                ],
                "ambiguities": [],
            }
        },
    )]
    task = SimpleNamespace(
        active_revision_id="revision-bind",
        active_revision=SimpleNamespace(execution_records=records),
        execution_records=records,
    )
    binding = {
        "revision_id": "revision-bind",
        "node_id": "bind",
        "node_digest": "1" * 64,
        "obligation_id": "bind",
        "input_binding_digest": "2" * 64,
        "decision_trace_ref": "artifact://planning-traces/task-bind/revision-bind/bind/t1",
    }

    class Binding:
        def model_dump(self, mode="json"):
            assert mode == "json"
            return binding

    class Coordinator:
        gateway_calls = 0

        def get_task(self, task_id):
            assert task_id == "task-bind"
            return task

        def pending_planning_selection(self, task_id, node_id, **_kwargs):
            assert (task_id, node_id) == ("task-bind", "bind")
            return {
                "execution_tool": "forge_tool_query",
                "tool_id": "scene.bind",
                "planning_binding": binding,
            }

        def selected_execution_binding(self, task_id, tool_id, semantics, planning_binding):
            assert (task_id, tool_id, semantics) == ("task-bind", "scene.bind", "query")
            assert planning_binding == binding
            return Binding()

        def selected_execution_arguments(self, *_args):
            return {"entity_refs": entity_refs}

        async def invoke_query(
            self, task_id, tool_id, arguments, *, timeout_ms, planning_binding,
        ):
            self.gateway_calls += 1
            assert (task_id, tool_id) == ("task-bind", "scene.bind")
            assert arguments == {"entity_refs": entity_refs}
            assert timeout_ms is None
            assert planning_binding == binding
            records.append(SimpleNamespace(
                record_id="bind-1",
                node_id="bind",
                tool_id="scene.bind",
                semantics="query",
                status="succeeded",
                terminal=True,
                invocation_id=None,
                evidence_refs=("tool:bind-1",),
                response={"ok": True, "data": {"status": "available"}},
                error=None,
            ))
            return {"ok": True, "data": {"status": "available"}}

    class Loop:
        def __init__(self, coordinator):
            self.tools = ToolRegistry()
            self.tools.register(ForgeToolQueryTool(object(), coordinator))
            self.model_calls = 0

        async def run_node_turn(self, **_kwargs):
            self.model_calls += 1
            raise AssertionError("persisted selection must not call the model")

    context = NodeExecutionContext(
        task_id="task-bind",
        revision_id="revision-bind",
        node_id="bind",
        capability="scene.bind",
        dependencies=("understand",),
        required_evidence=(),
        input_bindings={},
        scene_revision="scene-1",
    )
    coordinator = Coordinator()
    loop = Loop(coordinator)
    executor = AgentLoopNodeExecutor(loop, coordinator)

    if expected_error is not None:
        with pytest.raises(NodeTurnIncompleteError, match=expected_error):
            asyncio.run(executor(context))
        assert coordinator.gateway_calls == 0
    else:
        result = asyncio.run(executor(context))
        assert result.status == expected_status
        assert coordinator.gateway_calls == 1
        assert [record.record_id for record in records] == ["understand-1", "bind-1"]
    assert loop.model_calls == 0


def test_node_executor_reuses_pending_selection_on_bounded_continuation():
    records = []
    pending = {"value": None}
    prompts = []
    task = SimpleNamespace(
        active_revision_id="revision-resume",
        active_revision=SimpleNamespace(execution_records=records),
    )

    class Coordinator:
        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            return pending["value"]

    class Loop:
        def __init__(self):
            self.tools = ToolRegistry()
            self.tools.register(_SelectionTool(records))

        def activate_planning_task(self, _task_id):
            return None

        async def run_node_turn(self, *, prompt, **_kwargs):
            prompts.append(prompt)
            if len(prompts) == 1:
                pending["value"] = {
                    "execution_tool": "forge_tool_query",
                    "task_id": "task-resume",
                    "tool_id": "manipulation.prepare",
                    "arguments": {"candidate_set_ref": "candidate-set://1"},
                    "planning_binding": {"node_id": "prepare"},
                }

    loop = Loop()
    result = asyncio.run(AgentLoopNodeExecutor(loop, Coordinator())(_executor_context()))

    assert result.status == "succeeded"
    assert len(prompts) == 1
    assert "forge_tool_query" not in prompts[0]
    assert len(loop.tools.get("forge_tool_query").calls) == 1
    assert len(records) == 1


def test_node_executor_consumes_pending_selection_before_model_turn():
    records = []
    task = SimpleNamespace(
        active_revision_id="revision-resume",
        active_revision=SimpleNamespace(execution_records=records),
    )

    class Coordinator:
        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            return {
                "execution_tool": "forge_tool_query",
                "task_id": "task-resume",
                "tool_id": "manipulation.prepare",
                "planning_binding": {"node_id": "prepare"},
            }

    class Registry:
        calls = []

        async def execute(self, name, params):
            self.calls.append((name, params))
            records.append(_terminal_record())
            return '{"ok":true}'

    class Loop:
        def __init__(self):
            self.tools = Registry()
            self.model_calls = 0

        async def run_node_turn(self, **_kwargs):
            self.model_calls += 1

    loop = Loop()
    result = asyncio.run(AgentLoopNodeExecutor(loop, Coordinator())(_executor_context()))

    assert result.status == "succeeded"
    assert loop.model_calls == 0
    assert loop.tools.calls[0][0] == "forge_tool_query"
    assert loop.tools.calls[0][1]["use_selected_arguments"] is True


def test_node_executor_reconciles_existing_terminal_record_without_model_call():
    record = _terminal_record(semantics="action", status="unknown")
    task = SimpleNamespace(
        active_revision_id="revision-resume",
        active_revision=SimpleNamespace(execution_records=[record]),
    )

    class Coordinator:
        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            raise AssertionError("pending selection must not be read after execution")

    class Loop:
        calls = 0

        async def run_node_turn(self, **_kwargs):
            self.calls += 1

    loop = Loop()
    result = asyncio.run(AgentLoopNodeExecutor(loop, Coordinator())(_executor_context()))

    assert result.status == "unknown"
    assert result.world_change_started is True
    assert loop.calls == 0


def test_node_executor_reports_incomplete_after_bounded_no_record_turns():
    task = SimpleNamespace(
        active_revision_id="revision-resume",
        active_revision=SimpleNamespace(execution_records=[]),
    )

    class Coordinator:
        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            return None

    class Loop:
        calls = 0

        async def run_node_turn(self, **_kwargs):
            self.calls += 1

    loop = Loop()
    executor = AgentLoopNodeExecutor(loop, Coordinator())

    with pytest.raises(NodeTurnIncompleteError, match="node_turn_incomplete:prepare"):
        asyncio.run(executor(_executor_context()))
    assert loop.calls == 2
    assert task.active_revision.execution_records == []


def test_node_executor_carries_rejections_and_does_not_restart_failed_selection():
    diagnostic = {"code": "invalid_argument_source", "message": "invalid source path"}
    task = SimpleNamespace(active_revision_id="revision-resume",
                           active_revision=SimpleNamespace(execution_records=[]))
    prompts = []

    class Coordinator:
        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            return None

        def planning_selection_rejections(self, *args):
            assert args == ("task-resume", "revision-resume", "prepare")
            return [diagnostic]

    class Loop:
        async def run_node_turn(self, *, prompt, **kwargs):
            prompts.append(prompt)

    with pytest.raises(NodeTurnIncompleteError, match="invalid_argument_source"):
        asyncio.run(AgentLoopNodeExecutor(Loop(), Coordinator())(_executor_context()))
    assert len(prompts) == 1
    assert "Previous selection diagnostics" in prompts[0]
    assert diagnostic["message"] in prompts[0]
    assert task.active_revision.execution_records == []


def test_node_executor_pending_selection_without_registry_does_not_call_model():
    task = SimpleNamespace(
        active_revision_id="revision-resume",
        active_revision=SimpleNamespace(execution_records=[]),
    )

    class Coordinator:
        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            return {
                "execution_tool": "forge_tool_query",
                "task_id": "task-resume",
                "tool_id": "manipulation.prepare",
                "arguments": {"candidate_set_ref": "candidate-set://1"},
                "planning_binding": {"node_id": "prepare"},
            }

    class Loop:
        calls = 0

        async def run_node_turn(self, **_kwargs):
            self.calls += 1
            return SimpleNamespace(model_failure_code="provider_timeout")

    loop = Loop()
    executor = AgentLoopNodeExecutor(loop, Coordinator())

    with pytest.raises(
        NodeTurnIncompleteError,
        match="persisted selection requires the governed Tool registry",
    ):
        asyncio.run(executor(_executor_context()))

    assert loop.calls == 0
    assert task.active_revision.execution_records == []


def test_node_executor_retries_model_timeout_before_selection():
    records = []
    task = SimpleNamespace(
        active_revision_id="revision-resume",
        active_revision=SimpleNamespace(execution_records=records),
    )

    class Coordinator:
        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            return None

    class Loop:
        calls = 0

        async def run_node_turn(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(model_failure_code="provider_timeout")
            records.append(_terminal_record())
            return SimpleNamespace(model_failure_code=None, turn_failure_code=None)

    loop = Loop()
    result = asyncio.run(AgentLoopNodeExecutor(loop, Coordinator())(_executor_context()))

    assert result.status == "succeeded"
    assert loop.calls == 2
    assert len(records) == 1


def test_node_executor_blocks_after_bounded_model_timeouts_before_selection():
    task = SimpleNamespace(
        active_revision_id="revision-resume",
        active_revision=SimpleNamespace(execution_records=[]),
    )

    class Coordinator:
        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            return None

    class Loop:
        calls = 0

        async def run_node_turn(self, **_kwargs):
            self.calls += 1
            return SimpleNamespace(model_failure_code="provider_timeout")

    loop = Loop()
    with pytest.raises(NodeTurnProviderError, match="provider_timeout"):
        asyncio.run(AgentLoopNodeExecutor(loop, Coordinator())(_executor_context()))

    assert loop.calls == 2
    assert task.active_revision.execution_records == []


@pytest.mark.parametrize("continuations", [0, 1])
@pytest.mark.parametrize("failure", ["provider_timeout", "provider_error", "turn_error"])
def test_node_executor_consumes_new_selection_before_retrying_model(continuations, failure):
    records = []
    pending = {"value": None}
    task = SimpleNamespace(
        active_revision_id="revision-resume",
        active_revision=SimpleNamespace(execution_records=records),
    )

    class Coordinator:
        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            return pending["value"]

    class Loop:
        def __init__(self):
            self.calls = 0
            self.tools = ToolRegistry()
            self.tools.register(_SelectionTool(records))

        async def run_node_turn(self, *, prompt, **_kwargs):
            self.calls += 1
            assert self.calls == 1, "a durable selection must not require another model turn"
            pending["value"] = {
                "execution_tool": "forge_tool_query",
                "task_id": "task-resume",
                "tool_id": "manipulation.prepare",
                "arguments": {"candidate_set_ref": "candidate-set://1"},
                "planning_binding": {"node_id": "prepare"},
            }
            return SimpleNamespace(
                model_failure_code=failure if failure != "turn_error" else None,
                turn_failure_code=failure if failure == "turn_error" else None,
            )

    loop = Loop()
    executor = AgentLoopNodeExecutor(
        loop, Coordinator(), max_node_turn_continuations=continuations,
    )
    result = asyncio.run(executor(_executor_context()))

    assert result.status == "succeeded"
    assert loop.calls == 1
    assert loop.tools.get("forge_tool_query").calls == [{
        "task_id": "task-resume",
        "tool_id": "manipulation.prepare",
        "arguments": {},
        "use_selected_arguments": True,
        "planning_binding": {"node_id": "prepare"},
    }]
    assert len(records) == 1


@pytest.mark.parametrize("semantics", ["action", "session"])
def test_node_executor_reconciles_record_before_later_provider_failure(semantics):
    records = []
    task = SimpleNamespace(
        active_revision_id="revision-resume",
        active_revision=SimpleNamespace(execution_records=records),
        execution_records=records,
    )

    class Client:
        calls = []

        async def invocation_status(self, invocation_id):
            self.calls.append(("status", invocation_id))
            return {"status": "succeeded"}

        async def invocation_result(self, invocation_id):
            self.calls.append(("result", invocation_id))
            return {
                "status": "succeeded",
                "ok": True,
                "data": {
                    "status": "available",
                    "world_change_started": True,
                    "outcome_known": True,
                },
            }

    class Coordinator:
        client = Client()

        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            return None

        def _observe(self, invocation_id, response, expected_semantics):
            assert invocation_id == "invocation-accepted"
            record = records[0]
            assert record.semantics == expected_semantics
            record.status = response["status"]
            record.terminal = response["status"] == "succeeded"
            record.response = response

        def observe_action(
            self,
            _task_id,
            invocation_id,
            response,
            *,
            reconcile_settlement=True,
        ):
            self._observe(invocation_id, response, "action")

        def observe_session(
            self,
            _task_id,
            invocation_id,
            response,
            *,
            reconcile_settlement=True,
        ):
            self._observe(invocation_id, response, "session")

        def mark_execution_unknown(self, *_args, **_kwargs):
            raise AssertionError("known invocation must be reconciled, not marked unknown")

    class Loop:
        calls = 0

        async def run_node_turn(self, **_kwargs):
            self.calls += 1
            records.append(SimpleNamespace(
                record_id="tool-action",
                node_id="prepare",
                terminal=False,
                semantics=semantics,
                status="accepted",
                tool_id=("object.acquire" if semantics == "action" else "camera.stream"),
                invocation_id="invocation-accepted",
                evidence_refs=("tool:tool-action",),
                response={"status": "accepted"},
                error=None,
            ))
            return SimpleNamespace(
                model_failure_code="provider_timeout",
                turn_failure_code="provider_timeout",
            )

    loop = Loop()
    coordinator = Coordinator()
    result = asyncio.run(
        AgentLoopNodeExecutor(loop, coordinator)(_executor_context())
    )

    assert result.status == "succeeded"
    assert result.world_change_started is True
    assert loop.calls == 1
    assert coordinator.client.calls == [
        ("status", "invocation-accepted"),
        ("result", "invocation-accepted"),
    ]


def test_node_executor_leaves_known_running_session_nonterminal():
    records = []
    task = SimpleNamespace(
        active_revision_id="revision-resume",
        active_revision=SimpleNamespace(execution_records=records),
        execution_records=records,
    )

    class Client:
        async def invocation_status(self, _invocation_id):
            return {"status": "running"}

        async def invocation_result(self, _invocation_id):
            return {"status": "pending"}

    class Coordinator:
        client = Client()
        unknown_codes = []

        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            return None

        def observe_session(
            self,
            _task_id,
            _invocation_id,
            response,
            *,
            reconcile_settlement=True,
        ):
            records[0].status = response["status"]
            records[0].response = response

        def mark_execution_unknown(self, _task_id, _record_id, *, code, message):
            self.unknown_codes.append((code, message))

    class Loop:
        async def run_node_turn(self, **_kwargs):
            records.append(SimpleNamespace(
                record_id="tool-session",
                node_id="prepare",
                terminal=False,
                semantics="session",
                status="accepted",
                tool_id="camera.stream",
                invocation_id="session-accepted",
                evidence_refs=("tool:tool-session",),
                response={"status": "accepted"},
                error=None,
            ))
            return SimpleNamespace(
                model_failure_code=None,
                turn_failure_code=None,
            )

    coordinator = Coordinator()
    with pytest.raises(
        NodeTurnIncompleteError,
        match="did not reach a durable terminal state",
    ):
        asyncio.run(
            AgentLoopNodeExecutor(
                Loop(),
                coordinator,
                max_action_polls=1,
            )(_executor_context())
        )

    assert records[0].status == "pending"
    assert records[0].terminal is False
    assert coordinator.unknown_codes == []


def test_terminal_status_waits_for_result_facts_before_node_settlement(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="defer settlement until terminal result",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-result-first", ("arrange-red",))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/result-first",
    )
    invocation_id = "invocation-result-first"
    execution = ToolExecutionRecord(
        record_id="tool-result-first",
        revision_id=graph.revision_id,
        tool_id="object.place",
        semantics="action",
        caller_id="agent-task-test",
        node_id="arrange-red",
        node_digest="3" * 64,
        obligation_id="obligation-arrange-red",
        input_binding_digest="4" * 64,
        decision_trace_ref="decision:test:result-first",
        status="accepted",
        invocation_id=invocation_id,
        evidence_refs=[f"invocation:{invocation_id}"],
        response={"data": {"phase": "accepted"}},
    )
    c.store.update(
        task.task_id,
        lambda current: current.active_revision.execution_records.append(execution),
        event_type="fixture_action_accepted",
    )

    c.observe_action(
        task.task_id,
        invocation_id,
        {"data": {"status": "succeeded"}},
        reconcile_settlement=False,
    )
    after_status = c.get_task(task.task_id)
    status_record = after_status.active_revision.execution_records[0]
    assert status_record.status == "accepted"
    assert status_record.response == {"data": {"status": "succeeded"}}
    assert after_status.active_revision.node_settlements == []

    class Client:
        calls = []

        async def invocation_status(self, requested_id):
            self.calls.append(("status", requested_id))
            return {"data": {"status": "succeeded"}}

        async def invocation_result(self, requested_id):
            self.calls.append(("result", requested_id))
            return {
                "data": {
                    "status": "succeeded",
                    "result": {
                        "world_changed": True,
                        "world_change_started": True,
                        "outcome_known": True,
                        "new_scene_revision": "scene-2",
                        "evidence_refs": ["placed:arrange-red"],
                    },
                }
            }

    restarted = AgentTaskCoordinator(
        workspace=tmp_path,
        config=ForgeConfig(),
        client=Client(),
    )
    asyncio.run(restarted.reconcile_nonterminal())
    settlement = restarted.get_task(task.task_id).active_revision.node_settlements[0]
    assert settlement.status == "completed"
    assert settlement.scene_revision == "scene-2"
    assert settlement.evidence_refs == (
        f"invocation:{invocation_id}",
        "placed:arrange-red",
    )
    assert restarted.client.calls == [
        ("status", invocation_id),
        ("result", invocation_id),
    ]


def test_node_executor_prompt_budget_failure_does_not_consume_continuation():
    task = SimpleNamespace(
        active_revision_id="revision-resume",
        active_revision=SimpleNamespace(execution_records=[]),
    )

    class Coordinator:
        def get_task(self, _task_id):
            return task

        def pending_planning_selection(self, *_args, **_kwargs):
            return None

    class Loop:
        calls = 0

        async def run_node_turn(self, **_kwargs):
            self.calls += 1
            return SimpleNamespace(
                model_failure_code=None,
                turn_failure_code="prompt_budget_exceeded",
            )

    loop = Loop()
    executor = AgentLoopNodeExecutor(loop, Coordinator())

    with pytest.raises(
        NodeTurnIncompleteError,
        match="node_turn_incomplete:prepare:prompt_budget_exceeded",
    ):
        asyncio.run(executor(_executor_context()))

    assert loop.calls == 1
    assert task.active_revision.execution_records == []


def test_planning_loop_blocks_provider_failure_without_settlement(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="provider timeout during node turn",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-provider-timeout", ("arrange-red",))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/provider-timeout",
        discovery_evidence_refs=("scene:inventory",),
    )

    async def provider_timeout(context):
        raise NodeTurnProviderError(context.node_id, "provider_timeout")

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=provider_timeout,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1",
            evidence_refs=frozenset({"scene:inventory"}),
        ),
    ).run(task.task_id, scene_revision="scene-1"))

    assert result.status == "blocked"
    assert result.last_failure == (
        "node_turn_provider_error:arrange-red:provider_timeout"
    )
    current = c.get_task(task.task_id)
    assert current.status.value == "awaiting_replan"
    assert current.replan_deadline is not None
    assert current.active_revision.node_settlements == []
    assert current.active_revision.execution_records == []


def test_query_provider_block_waits_without_failing_task_or_opening_downstream(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="provider block is recoverable",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-provider-block", ("inspect", "act"))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/provider-block",
        discovery_evidence_refs=("scene:inventory",),
    )
    calls = []

    def execute(context):
        calls.append(context.node_id)
        if context.node_id == "inspect":
            record = ToolExecutionRecord(
                record_id="provider-attempt",
                revision_id=context.revision_id,
                tool_id="perception.describe",
                semantics="query",
                caller_id="test",
                node_id=context.node_id,
                node_digest=plan_node_digest(graph.nodes[0]),
                obligation_id=graph.nodes[0].obligation_id,
                input_binding_digest=tool_input_binding_digest({}),
                decision_trace_ref="artifact://trace/provider-attempt",
                status="succeeded",
                response={
                    "data": {
                        "status": "unavailable",
                        "error": {
                            "failure_stage": "provider",
                            "retryable": False,
                        },
                    }
                },
                evidence_refs=["tool:provider-attempt"],
            )
            c.store.update(
                task.task_id,
                lambda current: current.active_revision.execution_records.append(record),
                event_type="test_provider_query",
            )
            return ToolResultEnvelope(
                task_id=context.task_id,
                revision_id=context.revision_id,
                node_id=context.node_id,
                tool_id="perception.describe",
                status="failed",
                failure_code="provider_unavailable",
            )
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.act",
            status="succeeded",
            evidence_refs=("placed:act",),
        )

    adapter = PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1",
            evidence_refs=frozenset({"scene:inventory"}),
        ),
        finalize_completed_graph=False,
    )
    first = asyncio.run(adapter.run(task.task_id, scene_revision="scene-1"))

    assert first.status == "waiting_for_runtime"
    assert calls == ["inspect"]
    blocked = c.get_task(task.task_id)
    assert blocked.status == AgentTaskStatus.WAITING_FOR_RUNTIME
    assert blocked.active_revision.node_settlements == []
    assert blocked.active_revision.execution_records[0].record_id == "provider-attempt"
    assert c.active_query_provider_block(task.task_id)["tool_id"] == "perception.describe"
    with pytest.raises(AgentTaskBusyError):
        c.create_task(
            task_description="must not bypass runtime wait",
            verification=TaskVerificationContract(mode="off"),
        )
    cancelled = asyncio.run(c.cancel_task(task.task_id, reason="operator stop"))
    assert cancelled.status == AgentTaskStatus.CANCELLED


def test_provider_block_cannot_overwrite_concurrent_operator_stop(tmp_path):
    class CancellingClient:
        base_url = "http://runtime"

        async def get_tool_context(self, _tool_id):
            await c.cancel_task(task.task_id, reason="operator stop during context read")
            return {"data": {"ready": False, "provider_state": "unavailable"}}

    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="provider block cancellation race",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-provider-cancel-race", ("inspect",))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/provider-cancel-race",
    )
    record = ToolExecutionRecord(
        record_id="provider-cancel-race-attempt",
        revision_id=graph.revision_id,
        tool_id="perception.describe",
        semantics="query",
        caller_id="test",
        node_id="inspect",
        node_digest=plan_node_digest(graph.nodes[0]),
        obligation_id=graph.nodes[0].obligation_id,
        input_binding_digest=tool_input_binding_digest({}),
        decision_trace_ref="artifact://trace/provider-cancel-race",
        status="succeeded",
        response={
            "data": {
                "status": "unavailable",
                "error": {"failure_stage": "provider", "retryable": False},
            }
        },
    )
    c.store.update(
        task.task_id,
        lambda current: current.active_revision.execution_records.append(record),
        event_type="test_provider_query",
    )
    c.client = CancellingClient()

    with pytest.raises(
        AgentTaskError,
        match="changed state during readiness check",
    ):
        asyncio.run(c.record_query_provider_blocked(
            task.task_id,
            graph.revision_id,
            "inspect",
            tool_id="perception.describe",
            record_ids=(record.record_id,),
            reason="provider unavailable",
        ))

    stopped = c.get_task(task.task_id)
    assert stopped.status == AgentTaskStatus.CANCELLED
    assert stopped.cancellation_requested is True
    assert c.active_query_provider_block(task.task_id) is None


def test_planning_loop_converges_on_concurrent_stop_during_provider_block(tmp_path):
    class CancellingClient:
        base_url = "http://runtime"

        async def get_tool_context(self, _tool_id):
            await c.cancel_task(task.task_id, reason="operator stop during block")
            return {"data": {"ready": False}}

    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="provider block stop convergence",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-provider-stop", ("inspect",))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/provider-stop",
    )
    c.client = CancellingClient()

    def execute(context):
        record = ToolExecutionRecord(
            record_id="provider-stop-attempt",
            revision_id=context.revision_id,
            tool_id="perception.describe",
            semantics="query",
            caller_id="test",
            node_id=context.node_id,
            node_digest=plan_node_digest(graph.nodes[0]),
            obligation_id=graph.nodes[0].obligation_id,
            input_binding_digest=tool_input_binding_digest({}),
            decision_trace_ref="artifact://trace/provider-stop",
            status="succeeded",
            response={
                "data": {
                    "status": "unavailable",
                    "error": {"failure_stage": "provider", "retryable": False},
                }
            },
        )
        c.store.update(
            task.task_id,
            lambda current: current.active_revision.execution_records.append(record),
            event_type="test_provider_query",
        )
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="perception.describe",
            status="failed",
            failure_code="provider_unavailable",
        )

    adapter = PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1",
            evidence_refs=frozenset({"scene:inventory"}),
        ),
        finalize_completed_graph=False,
    )

    result = asyncio.run(adapter.run(task.task_id, scene_revision="scene-1"))

    assert result.status == "cancelled"
    assert result.last_failure is None
    assert c.get_task(task.task_id).status == AgentTaskStatus.CANCELLED
    assert c.active_query_provider_block(task.task_id) is None


def test_provider_block_releases_only_after_ready_and_retries_same_node(tmp_path):
    from PhyAgentOS.forge.binding import BoundToolSpec

    class Client:
        base_url = "http://runtime"

        def __init__(self):
            self.context_calls = 0
            self.contexts = [
                {"data": {"ready": False, "binding_error": "provider_unavailable"}},
                {"data": {"ready": False, "binding_error": "provider_unavailable"}},
                {"data": {"ready": True}},
            ]

        async def get_tool_context(self, _tool_id):
            self.context_calls += 1
            return self.contexts.pop(0)

    c = coordinator(tmp_path)
    c.client = Client()
    task = c.create_task(
        task_description="provider block resumes",
        verification=TaskVerificationContract(mode="off"),
    )
    c.store.update(
        task.task_id,
        lambda current: current.tool_bindings.append(
            BoundToolSpec(
                tool_id="perception.describe",
                semantics="query",
                spec_sha256="a" * 64,
                ready_at_binding=False,
            )
        ),
        event_type="test_bind_query",
    )
    graph = make_graph(task.task_id, "revision-provider-resume", ("inspect", "act"))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/provider-resume",
        discovery_evidence_refs=("scene:inventory",),
    )
    calls = []

    def execute(context):
        calls.append(context.node_id)
        if context.node_id == "inspect" and calls.count("inspect") == 1:
            record = ToolExecutionRecord(
                record_id="provider-attempt",
                revision_id=context.revision_id,
                tool_id="perception.describe",
                semantics="query",
                caller_id="test",
                node_id=context.node_id,
                node_digest=plan_node_digest(graph.nodes[0]),
                obligation_id=graph.nodes[0].obligation_id,
                input_binding_digest=tool_input_binding_digest({}),
                decision_trace_ref="artifact://trace/provider-attempt",
                status="succeeded",
                response={
                    "data": {
                        "status": "unavailable",
                        "error": {"failure_stage": "provider", "retryable": False},
                    }
                },
            )
            c.store.update(
                task.task_id,
                lambda current: current.active_revision.execution_records.append(record),
                event_type="test_provider_query",
            )
            return ToolResultEnvelope(
                task_id=context.task_id,
                revision_id=context.revision_id,
                node_id=context.node_id,
                tool_id="perception.describe",
                status="failed",
                failure_code="provider_unavailable",
            )
        return ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="object.act",
            status="succeeded",
            evidence_refs=("placed:act",),
        ) if context.node_id == "act" else ToolResultEnvelope(
            task_id=context.task_id,
            revision_id=context.revision_id,
            node_id=context.node_id,
            tool_id="perception.describe",
            status="succeeded",
            evidence_refs=("placed:inspect",),
        )

    adapter = PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=execute,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1", evidence_refs=frozenset({"scene:inventory"})
        ),
        finalize_completed_graph=False,
    )
    first = asyncio.run(adapter.run(task.task_id, scene_revision="scene-1"))
    assert first.status == "waiting_for_runtime"
    controller = LongHorizonTaskController(
        c,
        adapter,
        scene_revision_provider=lambda _: "scene-1",
    )
    resumed = asyncio.run(controller.run(task.task_id))
    assert resumed.status == "segment_completed"
    assert calls == ["inspect", "inspect", "act"]
    assert c.client.context_calls == 3
    assert c.get_task(task.task_id).active_revision.execution_records[0].record_id == "provider-attempt"
    assert c.effective_planning_execution_records(task.task_id, graph.revision_id) == ()
    assert c.released_provider_query_record_ids(
        task.task_id, graph.revision_id, "inspect"
    ) == frozenset({"provider-attempt"})


def test_provider_block_requires_context_transition_when_initial_snapshot_is_ready(
    tmp_path,
):
    from PhyAgentOS.forge.binding import BoundToolSpec

    class Client:
        base_url = "http://runtime"

        def __init__(self):
            self.contexts = [
                {"data": {"ready": True, "provider_state": "fallback_pending"}},
                {"data": {"ready": True, "provider_state": "fallback_pending"}},
                {"data": {"ready": True, "provider_state": "ready"}},
            ]

        async def get_tool_context(self, _tool_id):
            return self.contexts.pop(0)

    c = coordinator(tmp_path)
    c.client = Client()
    task = c.create_task(
        task_description="provider transition",
        verification=TaskVerificationContract(mode="off"),
    )
    c.store.update(
        task.task_id,
        lambda current: current.tool_bindings.append(
            BoundToolSpec(
                tool_id="perception.describe",
                semantics="query",
                spec_sha256="b" * 64,
                ready_at_binding=True,
            )
        ),
        event_type="test_bind_query",
    )
    graph = make_graph(task.task_id, "revision-provider-transition", ("inspect",))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/provider-transition",
    )
    record = ToolExecutionRecord(
        record_id="provider-transition-attempt",
        revision_id=graph.revision_id,
        tool_id="perception.describe",
        semantics="query",
        caller_id="test",
        node_id="inspect",
        node_digest=plan_node_digest(graph.nodes[0]),
        obligation_id=graph.nodes[0].obligation_id,
        input_binding_digest=tool_input_binding_digest({}),
        decision_trace_ref="artifact://trace/provider-transition",
        status="succeeded",
        response={
            "data": {
                "status": "unavailable",
                "error": {"failure_stage": "provider", "retryable": False},
            }
        },
    )
    c.store.update(
        task.task_id,
        lambda current: current.active_revision.execution_records.append(record),
        event_type="test_provider_query",
    )
    asyncio.run(c.record_query_provider_blocked(
        task.task_id,
        graph.revision_id,
        "inspect",
        tool_id="perception.describe",
        record_ids=(record.record_id,),
        reason="provider unavailable",
    ))

    unchanged = asyncio.run(c.resume_query_provider_block(task.task_id))
    assert unchanged.status == AgentTaskStatus.WAITING_FOR_RUNTIME
    changed = asyncio.run(c.resume_query_provider_block(task.task_id))
    assert changed.status == AgentTaskStatus.EXECUTING
    binding = c.persist_planning_selection({
        "task_id": task.task_id,
        "revision_id": graph.revision_id,
        "node_id": "inspect",
        "node_digest": plan_node_digest(graph.nodes[0]),
        "tool_id": "perception.describe",
        "semantics": "query",
        "tool_arguments": {},
        "input_binding_digest": tool_input_binding_digest({}),
        "candidate_tool_ids": ("perception.describe",),
        "scene_revision": "scene-1",
        "context_digest": "c" * 64,
        "decision_reason": "retry after Runtime readiness changed",
        "evidence_refs": (),
    })
    assert binding["node_id"] == "inspect"


def test_provider_block_releases_after_ready_false_ready_transition(tmp_path):
    from PhyAgentOS.forge.binding import BoundToolSpec

    class Client:
        base_url = "http://runtime"

        def __init__(self):
            self.contexts = [
                {"data": {"ready": True, "provider_state": "ready"}},
                {"data": {"ready": False, "provider_state": "unavailable"}},
                {"data": {"ready": True, "provider_state": "ready"}},
            ]

        async def get_tool_context(self, _tool_id):
            return self.contexts.pop(0)

    c = coordinator(tmp_path)
    c.client = Client()
    task = c.create_task(
        task_description="provider readiness cycle",
        verification=TaskVerificationContract(mode="off"),
    )
    c.store.update(
        task.task_id,
        lambda current: current.tool_bindings.append(
            BoundToolSpec(
                tool_id="perception.describe",
                semantics="query",
                spec_sha256="d" * 64,
                ready_at_binding=True,
            )
        ),
        event_type="test_bind_query",
    )
    graph = make_graph(task.task_id, "revision-provider-ready-cycle", ("inspect",))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/provider-ready-cycle",
    )
    record = ToolExecutionRecord(
        record_id="provider-ready-cycle-attempt",
        revision_id=graph.revision_id,
        tool_id="perception.describe",
        semantics="query",
        caller_id="test",
        node_id="inspect",
        node_digest=plan_node_digest(graph.nodes[0]),
        obligation_id=graph.nodes[0].obligation_id,
        input_binding_digest=tool_input_binding_digest({}),
        decision_trace_ref="artifact://trace/provider-ready-cycle",
        status="succeeded",
        response={
            "data": {
                "status": "unavailable",
                "error": {"failure_stage": "provider", "retryable": False},
            }
        },
    )
    c.store.update(
        task.task_id,
        lambda current: current.active_revision.execution_records.append(record),
        event_type="test_provider_query",
    )
    asyncio.run(c.record_query_provider_blocked(
        task.task_id,
        graph.revision_id,
        "inspect",
        tool_id="perception.describe",
        record_ids=(record.record_id,),
        reason="provider unavailable",
    ))

    unavailable = asyncio.run(c.resume_query_provider_block(task.task_id))
    assert unavailable.status == AgentTaskStatus.WAITING_FOR_RUNTIME
    assert c.active_query_provider_block(task.task_id)[
        "readiness_transition_observed"
    ] is True
    resumed = asyncio.run(c.resume_query_provider_block(task.task_id))
    assert resumed.status == AgentTaskStatus.EXECUTING
    assert c.released_provider_query_record_ids(
        task.task_id, graph.revision_id, "inspect"
    ) == frozenset({record.record_id})


def test_planning_loop_blocks_incomplete_node_without_settlement(tmp_path):
    c = coordinator(tmp_path)
    task = c.create_task(
        task_description="incomplete node turn",
        verification=TaskVerificationContract(mode="off"),
    )
    graph = make_graph(task.task_id, "revision-incomplete", ("arrange-red",))
    c.expand_discovery_revision(
        task.task_id,
        plan_graph=graph,
        plan_graph_ref="artifact://plans/incomplete",
        discovery_evidence_refs=("scene:inventory",),
    )

    async def incomplete(context):
        raise NodeTurnIncompleteError(context.node_id, "selection remains unconsumed")

    result = asyncio.run(PlanningLoopAdapter(
        c,
        context_provider=NodeContextProvider(c.get_task),
        node_executor=incomplete,
        admission_context_provider=lambda _: AdmissionContext(
            scene_revision="scene-1",
            evidence_refs=frozenset({"scene:inventory"}),
        ),
    ).run(task.task_id, scene_revision="scene-1"))

    assert result.status == "blocked"
    assert result.last_failure == (
        "node_turn_incomplete:arrange-red:selection remains unconsumed"
    )
    event = c.store.events(task.task_id)[-1]
    assert event["event_type"] == "planning_node_blocked"
    assert event["payload"]["reason"] == result.last_failure
    current = c.get_task(task.task_id)
    assert current.status.value == "awaiting_replan"
    assert current.replan_deadline is not None
    assert current.active_revision.node_settlements == []
    assert current.active_revision.execution_records == []
