from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.tools.base import Tool
from PhyAgentOS.agent.tools.planning import ForgePlanActivateTool
from PhyAgentOS.agent.tools.registry import ToolRegistry
from PhyAgentOS.forge.binding import BoundToolSpec, RuntimeBinding
from PhyAgentOS.forge.capability_runtime.grasp_proposal import GRASP_TOOL_SPEC
from PhyAgentOS.planning import (
    AdmissionContext,
    PlanGraph,
    PlanNode,
    ToolSpecPolicy,
    canonical_sha256,
    plan_graph_digest,
    plan_node_digest,
    tool_input_binding_digest,
)


def _graph() -> PlanGraph:
    payload = {
        "schema_version": "paos-plan-graph/v1",
        "task_id": "task-1",
        "revision_id": "revision-1",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [
            PlanNode(node_id="observe", obligation_id="observe", capability="scene.observe").model_dump(mode="json"),
            PlanNode(node_id="verify", obligation_id="verify", capability="task.verify", dependencies=("observe",)).model_dump(mode="json"),
        ],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    return PlanGraph.model_validate(payload)


def _dispatch() -> AgentComposedDispatch:
    policy = ToolSpecPolicy(
        tool_id="scene.observe",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("scene.observe",),
    )
    return AgentComposedDispatch(
        _graph(), (policy,), AdmissionContext(scene_revision="scene-1")
    )


def test_runtime_only_task_builds_dispatch_from_enrolled_tool_policies():
    policy = ToolSpecPolicy(
        tool_id="scene.observe",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("scene.observe",),
    )
    task = SimpleNamespace(
        active_revision=SimpleNamespace(plan_graph=_graph()),
        primary_skill_binding=None,
        runtime_binding=RuntimeBinding(
            binding_id="runtime_binding_1",
            runtime_profile="fake",
            runtime_instance_id="runtime_1",
            gateway_url="http://fake",
        ),
        tool_bindings=(BoundToolSpec(
            tool_id="scene.observe",
            semantics="query",
            spec_sha256="3" * 64,
            ready_at_binding=True,
            planning_policy=policy,
        ),),
    )
    dispatch = AgentComposedDispatch.from_task(
        task, context_provider=lambda _task_id: AdmissionContext(scene_revision="scene-1")
    )
    assert dispatch.policies == (policy,)


def test_ready_tool_is_read_only_and_reports_candidates():
    data = _dispatch().describe()
    assert data["ready_nodes"][0]["candidate_tool_ids"] == ["scene.observe"]
    assert data["node_diagnostics"][0]["ready"] is True
    assert data["node_diagnostics"][0]["blockers"] == ()
    assert data["motion_authorized"] is False


def test_historical_unbindable_node_is_dependency_ready_but_not_selection_ready():
    node = PlanNode(
        node_id="acquire-blue",
        obligation_id="acquire-blue",
        capability="object.acquire",
    )
    payload = {
        "task_id": "task-1",
        "revision_id": "revision-1",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    policy = ToolSpecPolicy(
        tool_id="object.acquire",
        semantics="action",
        spec_digest="3" * 64,
        capabilities=("object.acquire",),
        input_binding_keys=("entity_ref",),
    )
    dispatch = AgentComposedDispatch(
        PlanGraph.model_validate(payload),
        (policy,),
        AdmissionContext(scene_revision="scene-1"),
    )

    data = dispatch.describe()

    assert data["ready_nodes"] == []
    diagnostic = data["node_diagnostics"][0]
    assert diagnostic["dependency_ready"] is True
    assert diagnostic["selection_ready"] is False
    assert diagnostic["bindable_tool_ids"] == ()
    assert diagnostic["missing_node_bindings"] == {
        "object.acquire": ("entity_ref",)
    }
    assert "missing_node_bindings" in diagnostic["blockers"]

    try:
        dispatch.prepare_selection(
            node_id=node.node_id,
            tool_id=policy.tool_id,
            arguments={},
            decision_reason="should require a scene-bound entity",
        )
    except Exception as exc:
        assert getattr(exc, "code") == "node_tool_binding_incompatible"
        assert getattr(exc, "requires_replan") is True
        assert getattr(exc, "retryable_in_revision") is False
        assert getattr(exc, "missing_fields") == ("entity_ref",)
    else:
        raise AssertionError("an unbindable historical node must fail closed")


def test_ready_diagnostics_explain_evidence_and_condition_blockers():
    node = PlanNode(
        node_id="target",
        obligation_id="target",
        capability="scene.observe",
        conditions=("scene_current", "binding_ready"),
        required_evidence=("artifact://observation/current",),
    )
    payload = {
        "schema_version": "paos-plan-graph/v1",
        "task_id": "task-1",
        "revision_id": "revision-1",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    dispatch = AgentComposedDispatch(
        PlanGraph.model_validate(payload),
        (_dispatch().policies[0],),
        AdmissionContext(scene_revision="scene-1"),
    )
    diagnostic = dispatch.describe()["node_diagnostics"][0]
    assert diagnostic["ready"] is False
    assert diagnostic["missing_evidence"] == ("artifact://observation/current",)
    assert diagnostic["unknown_conditions"] == ("scene_current", "binding_ready")
    assert "evidence" in diagnostic["blockers"]
    assert "unknown_conditions" in diagnostic["blockers"]


def test_dispatch_refreshes_authoritative_context_before_each_read():
    contexts = [AdmissionContext(scene_revision="scene-1"), AdmissionContext(scene_revision="scene-2")]
    dispatch = AgentComposedDispatch(
        _graph(),
        (_dispatch().policies[0],),
        contexts[0],
        context_provider=lambda _task_id: contexts.pop(0),
    )
    assert dispatch.describe()["scene_revision"] == "scene-1"
    assert dispatch.describe()["scene_revision"] == "scene-2"


def test_stale_scene_ready_projection_exposes_only_refresh_tools():
    policy = ToolSpecPolicy(
        tool_id="scene.observe",
        semantics="query",
        spec_digest="3" * 64,
        capabilities=("scene.observe", "object.relocate"),
        refreshes_scene=True,
    )
    dispatch = AgentComposedDispatch(
        _graph(), (policy,),
        AdmissionContext(scene_revision="scene-1", condition_facts={"scene_current": False}),
    )
    data = dispatch.describe()
    assert [item["node_id"] for item in data["ready_nodes"]] == ["observe"]
    assert all(item["node_id"] != "verify" for item in data["ready_nodes"])


def test_guard_rejects_missing_binding_and_wrong_node():
    dispatch = _dispatch()
    missing = dispatch.admit_forge_tool(
        "forge_tool_query", {"task_id": "task-1", "tool_id": "scene.observe", "arguments": {}}
    )
    assert missing is not None and missing.code == "missing_planning_binding"
    wrong = dispatch.admit_forge_tool(
        "forge_tool_query",
        {
            "task_id": "task-1",
            "tool_id": "scene.observe",
            "arguments": {},
            "planning_binding": {
                "node_id": "verify",
                "input_binding_digest": "4" * 64,
            },
        },
    )
    assert wrong is not None and wrong.code == "invalid_planning_binding"


def test_guard_rejects_node_and_obligation_drift():
    dispatch = _dispatch()
    base = {
        "node_id": "observe",
        "node_digest": plan_node_digest(dispatch.graph.nodes[0]),
        "obligation_id": "observe",
        "input_binding_digest": "4" * 64,
        "decision_trace_ref": "artifact://trace/1",
    }
    drift = dict(base, node_digest="5" * 64)
    result = dispatch.admit_forge_tool(
        "forge_tool_query",
        {"task_id": "task-1", "tool_id": "scene.observe", "arguments": {}, "planning_binding": drift},
    )
    assert result is not None and result.code == "invalid_planning_binding"
    drift = dict(base, obligation_id="other")
    result = dispatch.admit_forge_tool(
        "forge_tool_query",
        {"task_id": "task-1", "tool_id": "scene.observe", "arguments": {}, "planning_binding": drift},
    )
    assert result is not None and result.code == "invalid_planning_binding"


def test_prepare_selection_returns_paos_owned_binding_facts_without_execution():
    dispatch = _dispatch()
    proposal = dispatch.prepare_selection(
        node_id="observe",
        tool_id="scene.observe",
        arguments={},
        decision_reason="initial live observation",
    )
    assert proposal["node_digest"] == plan_node_digest(dispatch.graph.nodes[0])
    assert proposal["input_binding_digest"] == tool_input_binding_digest({})
    assert proposal["decision_reason"] == "initial live observation"
    assert proposal["scene_revision"] == "scene-1"
    assert proposal["context_digest"] == canonical_sha256(
        AdmissionContext(scene_revision="scene-1").model_dump(mode="json")
    )


def _grasp_dispatch() -> AgentComposedDispatch:
    node = PlanNode(
        node_id="grasp-green",
        obligation_id="propose-current-green-grasp",
        capability="grasp.propose",
        input_bindings={"entity_ref": "entity://green"},
    )
    payload = {
        "task_id": "task-1",
        "revision_id": "revision-1",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    policy = ToolSpecPolicy(
        tool_id="grasp.propose",
        semantics="query",
        spec_digest="4" * 64,
        capabilities=("grasp.propose",),
    )
    return AgentComposedDispatch(
        PlanGraph.model_validate(payload),
        (policy,),
        AdmissionContext(scene_revision="scene-1"),
        input_schemas={"grasp.propose": GRASP_TOOL_SPEC["input_schema"]},
    )


def _grasp_arguments() -> dict:
    observation_ref = "observation://scene-1/head_camera"
    calibration_ref = "artifact://scene-1/capture-1/calibration"
    provenance = ["artifact://scene-1/capture-1/depth"]
    return {
        "observation_ref": observation_ref,
        "scene_revision": "scene-1",
        "frame_id": "head_camera",
        "calibration_ref": calibration_ref,
        "freshness_ms": 0,
        "max_age_ms": 1000,
        "targets": [{
            "entity_ref": "entity://green",
            "category": "green block",
            "confidence": 0.98,
            "spatial_envelope": {
                "frame_id": "head_camera",
                "unit": "m",
                "min_xyz_m": [0.1, 0.2, 0.0],
                "max_xyz_m": [0.2, 0.3, 0.1],
                "confidence": 0.97,
                "provenance": provenance,
            },
            "geometry_artifacts": [{
                "artifact_ref": "artifact://scene-1/capture-1/green-cloud",
                "kind": "object_point_cloud",
                "observation_ref": observation_ref,
                "scene_revision": "scene-1",
                "entity_ref": "entity://green",
                "frame_id": "head_camera",
                "calibration_ref": calibration_ref,
                "provenance": provenance,
            }],
        }],
    }


def test_selection_rejects_incomplete_grasp_arguments_before_execution():
    dispatch = _grasp_dispatch()
    ready = dispatch.describe()["ready_nodes"][0]
    assert ready["required_tool_arguments"]["grasp.propose"] == tuple(
        GRASP_TOOL_SPEC["input_schema"]["required"]
    )

    with pytest.raises(Exception) as caught:
        dispatch.prepare_selection(
            node_id="grasp-green",
            tool_id="grasp.propose",
            arguments={"entity_ref": "entity://green"},
            decision_reason="use the selected green entity",
        )

    error = caught.value
    assert getattr(error, "code") == "tool_input_schema_invalid"
    assert set(getattr(error, "missing_fields")) == set(
        GRASP_TOOL_SPEC["input_schema"]["required"]
    )
    assert getattr(error, "recommended_action") == "select_values_from_bounded_node_context"


def test_selection_accepts_agent_assembled_grasp_arguments_without_producer_binding():
    dispatch = _grasp_dispatch()
    arguments = _grasp_arguments()

    proposal = dispatch.prepare_selection(
        node_id="grasp-green",
        tool_id="grasp.propose",
        arguments=arguments,
        decision_reason="assemble the selected entity and current calibrated geometry",
    )

    assert proposal["tool_arguments"] == arguments
    assert proposal["input_binding_digest"] == tool_input_binding_digest(arguments)


def test_prepare_selection_rejects_unready_or_wrong_tool():
    dispatch = _dispatch()
    try:
        dispatch.prepare_selection(
            node_id="verify", tool_id="scene.observe", arguments={},
            decision_reason="not ready",
        )
    except ValueError as exc:
        assert "planning node" in str(exc) or "not ready" in str(exc)
    else:
        raise AssertionError("unready node was accepted")
    try:
        dispatch.prepare_selection(
            node_id="observe", tool_id="unknown", arguments={},
            decision_reason="wrong tool",
        )
    except ValueError as exc:
        assert "not declared" in str(exc)
    else:
        raise AssertionError("undeclared tool was accepted")
def test_guard_admits_complete_binding_without_authorizing_motion():
    dispatch = _dispatch()
    binding = {
        "node_id": "observe",
        "node_digest": plan_node_digest(dispatch.graph.nodes[0]),
        "obligation_id": "observe",
        "input_binding_digest": tool_input_binding_digest({}),
        "decision_trace_ref": "artifact://trace/1",
    }
    result = dispatch.admit_forge_tool(
        "forge_tool_query",
        {"task_id": "task-1", "tool_id": "scene.observe", "arguments": {}, "planning_binding": binding},
    )
    assert result is not None and result.allowed is True
    assert result.motion_authorized is False


def test_activation_failure_clears_previous_dispatch():
    class _Coordinator:
        def get_task(self, task_id):
            raise RuntimeError("missing task")

    active = [_dispatch()]
    tool = ForgePlanActivateTool(
        _Coordinator(),
        lambda value: active.__setitem__(0, value),
        context_provider=None,
    )
    import asyncio

    result = json.loads(asyncio.run(tool.execute("task-1")))
    assert result["ok"] is False
    assert active[0] is None


class _Probe(Tool):
    @property
    def name(self):
        return "probe"

    @property
    def description(self):
        return "probe"

    @property
    def parameters(self):
        return {"type": "object", "properties": {}, "additionalProperties": False}

    async def execute(self):
        return "executed"


def test_registry_guard_runs_before_tool_execution():
    registry = ToolRegistry()
    registry.register(_Probe())
    registry.set_execution_guard(lambda name, params: json.dumps({"ok": False, "code": "blocked"}))
    assert json.loads(__import__("asyncio").run(registry.execute("probe", {}))) == {"ok": False, "code": "blocked"}
