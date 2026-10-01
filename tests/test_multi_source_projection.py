from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.planning_loop import (
    AgentLoopNodeExecutor,
    EvidenceExecutionContext,
    NodeExecutionContext,
    PlanningLoopError,
    PredecessorContext,
    PredecessorExecutionContext,
    project_consumer_arguments,
)
from PhyAgentOS.agent.tools.planning import ForgePlanSelectTool
from PhyAgentOS.forge.capability_runtime.manipulation_prepare import MANIPULATION_TOOL_SPEC
from PhyAgentOS.planning import (
    AdmissionContext,
    ArgumentProjectionPlan,
    NodeSettlement,
    PlanGraph,
    PlanNode,
    plan_graph_digest,
    project_tool_spec,
)


def _plan() -> ArgumentProjectionPlan:
    return project_tool_spec(MANIPULATION_TOOL_SPEC).argument_projection_plan


def _grasp_response(*, entity_ref: str = "entity://green") -> dict:
    def candidate(candidate_ref: str, target: str) -> dict:
        return {
            "candidate_ref": candidate_ref,
            "entity_ref": target,
            "grasp_frame": {
                "frame_id": "camera",
                "unit": "m",
                "position_m": [0.1, 0.2, 0.3],
                "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
            },
            "approach_direction": {
                "frame_id": "camera",
                "unit": "unitless",
                "vector": [0.0, 0.0, -1.0],
            },
            "score": 0.9,
            "confidence": 0.9,
            "provenance": ["artifact://scene-1/grasp/candidate"],
            "qualification": "proposed",
        }

    return {
        "data": {
            "observation_ref": "observation://scene-1/camera",
            "scene_revision": "scene-1",
            "frame": {"frame_id": "camera", "unit": "m"},
            "calibration_ref": "artifact://scene-1/calibration",
            "candidate_set_ref": "candidate-set://scene-1/camera",
            "candidates": [
                candidate("candidate://red/0", "entity://red"),
                candidate("candidate://green/0", entity_ref),
            ],
        }
    }


def _capability_response(*, arms: list[dict] | None = None) -> dict:
    return {
        "data": {
            "snapshot_ref": "artifact://capabilities/scene-1/snapshot",
            "scene_revision": "scene-1",
            "observation_ref": "observation://scene-1/camera",
            "calibration_ref": "artifact://scene-1/calibration",
            "arms": arms
            or [
                {"arm_id": "left", "availability": "available"},
                {"arm_id": "right", "availability": "available"},
            ],
            "motion_authorized": False,
        }
    }


def _context(*, capability_response: dict | None = None) -> NodeExecutionContext:
    return NodeExecutionContext(
        task_id="task-1",
        revision_id="revision-1",
        node_id="prepare",
        capability="manipulation.prepare",
        dependencies=("grasp",),
        required_evidence=("tool:capabilities",),
        input_bindings={"entity_ref": "entity://green"},
        scene_revision="scene-1",
        predecessor_context=(
            PredecessorContext(
                node_id="grasp",
                status="completed",
                scene_revision="scene-1",
                executions=(
                    PredecessorExecutionContext(
                        record_id="grasp-record",
                        tool_id="grasp.propose",
                        semantics="query",
                        status="succeeded",
                        arguments={"freshness_ms": 3, "max_age_ms": 1000},
                        response=_grasp_response(),
                    ),
                ),
            ),
        ),
        evidence_context=(
            EvidenceExecutionContext(
                revision_id="discovery",
                record_id="capability-record",
                tool_id="manipulation.capabilities",
                status="succeeded",
                evidence_refs=("tool:capabilities",),
                arguments={
                    "scene_revision": "scene-1",
                    "observation_ref": "observation://scene-1/camera",
                    "calibration_ref": "artifact://scene-1/calibration",
                },
                response=capability_response or _capability_response(),
            ),
        ),
    )


def _project(context: NodeExecutionContext, *, literals: dict | None = None) -> dict:
    return project_consumer_arguments(
        context,
        projection="candidate_set_for_entity_v1",
        projection_plan=_plan(),
        literals={"entity_ref": "entity://green", **(literals or {})},
        source_record_ids={
            "candidates": "grasp-record",
            "capabilities": "capability-record",
        },
    )


def test_named_projection_compiles_candidates_and_allowed_arms_from_declared_sources():
    result = _project(_context())

    assert [item["candidate_ref"] for item in result["candidates"]] == [
        "candidate://green/0"
    ]
    assert result["allowed_arms"] == ["left", "right"]
    assert result["capability_snapshot_ref"] == (
        "artifact://capabilities/scene-1/snapshot"
    )
    assert result["freshness_ms"] == 3


def test_node_prompt_directs_agent_to_named_slots_without_value_assembly():
    prompt = AgentLoopNodeExecutor._default_prompt(_context())

    assert "pass projection_sources with exactly those declared slot names" in prompt
    assert "do not provide source paths or projected values" in prompt
    assert "record (grasp.propose) containing candidate_set_ref and candidates" in prompt
    assert "manipulation.capabilities evidence record for available arms" in prompt


def test_named_projection_filters_unavailable_arms():
    response = _capability_response(
        arms=[
            {"arm_id": "left", "availability": "available"},
            {"arm_id": "right", "availability": "unavailable"},
        ]
    )

    result = _project(_context(capability_response=response))

    assert result["allowed_arms"] == ["left"]


def test_named_projection_rejects_when_all_arms_are_unavailable():
    response = _capability_response(
        arms=[
            {"arm_id": "left", "availability": "unavailable"},
            {"arm_id": "right", "availability": "unavailable"},
        ]
    )

    with pytest.raises(PlanningLoopError, match="allowed_arms.*empty"):
        _project(_context(capability_response=response))


def test_named_projection_rejects_duplicate_available_arm_ids():
    response = _capability_response(
        arms=[
            {"arm_id": "left", "availability": "available"},
            {"arm_id": "left", "availability": "available"},
        ]
    )

    with pytest.raises(PlanningLoopError, match="allowed_arms.*duplicates"):
        _project(_context(capability_response=response))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "scene_revision",
            "scene-2",
            "observation_ref conflicts with scene_revision",
        ),
        ("observation_ref", "observation://scene-1/other", "mismatched observation_ref"),
        ("calibration_ref", "artifact://scene-1/other-calibration", "mismatched calibration_ref"),
    ],
)
def test_named_projection_rejects_cross_world_sources(field, value, message):
    response = _capability_response()
    response["data"][field] = value
    with pytest.raises(PlanningLoopError, match=message):
        _project(_context(capability_response=response))


def test_named_projection_rejects_explicit_cross_frame_source():
    response = _capability_response()
    response["data"]["frame"] = {"frame_id": "other-camera"}
    with pytest.raises(PlanningLoopError, match="mismatched frame_id"):
        _project(_context(capability_response=response))


def test_named_projection_rejects_wrong_scope_tool_and_agent_authored_fields():
    context = _context()
    wrong_tool = context.evidence_context[0].model_copy(update={"tool_id": "scene.understand"})
    with pytest.raises(PlanningLoopError, match="requires Tool manipulation.capabilities"):
        _project(context.model_copy(update={"evidence_context": (wrong_tool,)}))

    with pytest.raises(PlanningLoopError, match="Coordinator-owned: allowed_arms"):
        _project(context, literals={"allowed_arms": ["left"]})

    with pytest.raises(PlanningLoopError, match="match ToolSpec source slots"):
        project_consumer_arguments(
            context,
            projection="candidate_set_for_entity_v1",
            projection_plan=_plan(),
            literals={"entity_ref": "entity://green"},
            source_record_ids={"candidates": "grasp-record"},
        )


def test_forge_plan_select_compiles_named_sources_without_agent_value_assembly():
    grasp_node = PlanNode(
        node_id="grasp",
        obligation_id="grasp",
        capability="grasp.propose",
        input_bindings={"entity_ref": "entity://green"},
    )
    node = PlanNode(
        node_id="prepare",
        obligation_id="prepare",
        capability="manipulation.prepare",
        dependencies=("grasp",),
        required_evidence=("tool:capabilities",),
        input_bindings={
            "entity_ref": "entity://green",
            "binding_ref": "artifact://bindings/scene-1",
            "destination_ref": "destination://targets/middle",
            "goal": "place green in the middle",
            "success_criteria": ["green reaches the middle"],
            "coordination_mode": "alternative_arm",
        },
    )
    payload = {
        "task_id": "task-1",
        "revision_id": "revision-1",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [
            grasp_node.model_dump(mode="json"),
            node.model_dump(mode="json"),
        ],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    graph = PlanGraph.model_validate(payload)
    spec = deepcopy(MANIPULATION_TOOL_SPEC)
    spec["planning"]["trusted_argument_builder"] = "manipulation_intent_v2"
    policy = project_tool_spec(spec)
    dispatch = AgentComposedDispatch(
        graph,
        (policy,),
        AdmissionContext(
            scene_revision="scene-1",
            evidence_refs=frozenset({"tool:capabilities"}),
            settlements={"grasp": "completed"},
        ),
        input_schemas={"manipulation.prepare": spec["input_schema"]},
    )
    ready = dispatch.describe()["ready_nodes"][-1]
    assert ready["selection_source_modes"]["manipulation.prepare"] == "projection_sources"
    assert ready["argument_projection_sources"]["manipulation.prepare"] == {
        "candidates": {
            "tool_id": "grasp.propose",
            "source_scope": "predecessor",
        },
        "capabilities": {
            "tool_id": "manipulation.capabilities",
            "source_scope": "evidence",
        },
    }

    grasp_record = SimpleNamespace(
        record_id="grasp-record",
        node_id="grasp",
        tool_id="grasp.propose",
        semantics="query",
        status="succeeded",
        arguments={"freshness_ms": 3, "max_age_ms": 1000},
        response=_grasp_response(),
        error=None,
        evidence_refs=["tool:candidates"],
    )
    capability_record = SimpleNamespace(
        record_id="capability-record",
        node_id=None,
        tool_id="manipulation.capabilities",
        semantics="query",
        status="succeeded",
        arguments={
            "scene_revision": "scene-1",
            "observation_ref": "observation://scene-1/camera",
            "calibration_ref": "artifact://scene-1/calibration",
        },
        response=_capability_response(),
        error=None,
        evidence_refs=["tool:capabilities"],
    )
    revision = SimpleNamespace(
        revision_id="revision-1",
        plan_graph=graph,
        node_settlements=[
            NodeSettlement(
                task_id="task-1",
                revision_id="revision-1",
                node_id="grasp",
                status="completed",
                source_tool_id="grasp.propose",
                scene_revision="scene-1",
                evidence_refs=("tool:candidates",),
            )
        ],
        execution_records=[grasp_record, capability_record],
        discovery_evidence_refs=("tool:capabilities",),
        fresh_evidence_requirements=(),
        replan_evidence_refs=(),
    )
    task = SimpleNamespace(
        task_id="task-1",
        active_revision_id="revision-1",
        active_revision=revision,
        revisions=(revision,),
        primary_skill_binding=None,
        tool_bindings=(),
    )

    class Coordinator:
        def get_task(self, task_id):
            assert task_id == task.task_id
            return task

        def persist_planning_selection(self, proposal):
            return {
                **proposal,
                "decision_trace_ref": "artifact://planning/trace",
            }

    wrong_mode = json.loads(
        asyncio.run(
            ForgePlanSelectTool(Coordinator(), lambda: dispatch).execute(
                task_id="task-1",
                node_id="prepare",
                tool_id="manipulation.prepare",
                decision_reason="reject legacy selector shape",
                projection_source={"record_id": "grasp-record"},
            )
        )
    )
    assert wrong_mode["error"]["code"] == "consumer_projection_invalid"
    assert wrong_mode["error"]["requires_replan"] is False
    assert wrong_mode["error"]["retryable_in_revision"] is True

    missing_slot = json.loads(
        asyncio.run(
            ForgePlanSelectTool(Coordinator(), lambda: dispatch).execute(
                task_id="task-1",
                node_id="prepare",
                tool_id="manipulation.prepare",
                decision_reason="reject incomplete named selector",
                projection_sources={"candidates": {"record_id": "grasp-record"}},
            )
        )
    )
    assert missing_slot["error"]["message"] == (
        "named projection sources must match ToolSpec source slots"
    )
    assert missing_slot["error"]["requires_replan"] is False

    result = json.loads(
        asyncio.run(
            ForgePlanSelectTool(Coordinator(), lambda: dispatch).execute(
                task_id="task-1",
                node_id="prepare",
                tool_id="manipulation.prepare",
                decision_reason="compile declared sources",
                projection_sources={
                    "candidates": {"record_id": "grasp-record"},
                    "capabilities": {"record_id": "capability-record"},
                },
            )
        )
    )

    assert result["ok"], result
    selected = result["data"]["selection"]
    assert selected["tool_arguments"] == {}
    assert selected["use_selected_arguments"] is True
