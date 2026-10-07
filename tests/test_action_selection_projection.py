from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from PhyAgentOS.agent.planning_dispatch import AgentComposedDispatch
from PhyAgentOS.agent.tools.planning import ForgePlanSelectTool
from PhyAgentOS.planning import (
    AdmissionContext,
    ArgumentProjectionError,
    NodeSettlement,
    PlanGraph,
    PlanNode,
    execute_argument_projection,
    plan_graph_digest,
    project_tool_spec,
)

_CONTRACTS = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "forge-skills"
    / "pick-place-workflow"
    / "contracts"
)
ACQUIRE_TOOL_SPEC = yaml.safe_load(
    (_CONTRACTS / "object.acquire.tool.yaml").read_text(encoding="utf-8")
)
PLACE_TOOL_SPEC = yaml.safe_load(
    (_CONTRACTS / "object.place.tool.yaml").read_text(encoding="utf-8")
)


ENTITY = "entity://workpiece-17"
OBSERVATION = "observation://scene-1/sensor-frame"
CALIBRATION = "artifact://scene-1/calibration"
CANDIDATE_SET = "candidate-set://scene-1/provider-run"
PREPARATION = "preparation://scene-1/provider-run"
CANDIDATE = "candidate://workpiece-17/4"
CAPABILITIES = "artifact://capabilities/scene-1"
ASSIGNMENT = "artifact://assignments/task-1/revision-1/prepare"
DESTINATION = "destination://external-goal/slot-4"
INVOCATION = "invocation://object-acquire/attempt-1"


def _preparation_response(*, assignments: list[dict] | None = None) -> dict:
    return {
        "ok": True,
        "data": {
            "status": "available",
            "observation_ref": OBSERVATION,
            "scene_revision": "scene-1",
            "frame": {"frame_id": "sensor-frame", "unit": "m"},
            "calibration_ref": CALIBRATION,
            "candidate_set_ref": CANDIDATE_SET,
            "preparation_ref": PREPARATION,
            "assignments": assignments
            if assignments is not None
            else [
                {
                    "entity_ref": ENTITY,
                    "candidate_ref": CANDIDATE,
                    "capability_snapshot_ref": CAPABILITIES,
                    "assignment_ref": ASSIGNMENT,
                }
            ],
            "motion_authorized": False,
        },
    }


def _acquire_response(*, new_scene_revision: str = "scene-2") -> dict:
    return {
        "ok": True,
        "data": {
            "status": "succeeded",
            "invocation_id": INVOCATION,
            "result": {
                "status": "succeeded",
                "entity_ref": ENTITY,
                "observation_ref": OBSERVATION,
                "scene_revision": "scene-1",
                "frame": {"frame_id": "sensor-frame", "unit": "m"},
                "calibration_ref": CALIBRATION,
                "candidate_set_ref": CANDIDATE_SET,
                "preparation_ref": PREPARATION,
                "candidate_ref": CANDIDATE,
                "capability_snapshot_ref": CAPABILITIES,
                "assignment_ref": ASSIGNMENT,
                "acquire_invocation_ref": INVOCATION,
                "new_scene_revision": new_scene_revision,
            },
        },
    }


def _graph(nodes: list[PlanNode]) -> PlanGraph:
    payload = {
        "task_id": "task-1",
        "revision_id": "revision-1",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json") for node in nodes],
    }
    payload["graph_digest"] = plan_graph_digest(payload)
    return PlanGraph.model_validate(payload)


class _Coordinator:
    def __init__(self, task):
        self.task = task
        self.proposals: list[dict] = []

    def get_task(self, task_id):
        assert task_id == self.task.task_id
        return self.task

    def persist_planning_selection(self, proposal):
        self.proposals.append(proposal)
        return {**proposal, "decision_trace_ref": "artifact://planning/trace"}

    def planning_selection_rejections(self, *_args):
        return []


def _task(graph, *, records, settlements):
    revision = SimpleNamespace(
        revision_id="revision-1",
        plan_graph=graph,
        node_settlements=settlements,
        execution_records=records,
        discovery_evidence_refs=(),
        fresh_evidence_requirements=(),
        replan_evidence_refs=(),
    )
    return SimpleNamespace(
        task_id="task-1",
        active_revision_id="revision-1",
        active_revision=revision,
        revisions=(revision,),
        primary_skill_binding=None,
        tool_bindings=(),
    )


def _record(*, record_id, node_id, tool_id, arguments, response, semantics="query"):
    return SimpleNamespace(
        record_id=record_id,
        node_id=node_id,
        tool_id=tool_id,
        semantics=semantics,
        status="succeeded",
        arguments=arguments,
        response=response,
        error=None,
        evidence_refs=(f"tool:{record_id}",),
    )


def test_unique_item_projection_requires_exactly_one_join_match():
    plan = project_tool_spec(ACQUIRE_TOOL_SPEC).argument_projection_plan
    arguments = {
        "freshness_ms": 11,
        "max_age_ms": 1000,
    }

    result = execute_argument_projection(
        plan,
        records={"prepare-record": (arguments, _preparation_response())},
        literals={"entity_ref": ENTITY},
        source_record_ids={"preparation": "prepare-record"},
    )

    assert result == {
        "observation_ref": OBSERVATION,
        "scene_revision": "scene-1",
        "frame_id": "sensor-frame",
        "calibration_ref": CALIBRATION,
        "freshness_ms": 11,
        "max_age_ms": 1000,
        "candidate_set_ref": CANDIDATE_SET,
        "preparation_ref": PREPARATION,
        "candidate_ref": CANDIDATE,
        "capability_snapshot_ref": CAPABILITIES,
        "assignment_ref": ASSIGNMENT,
        "entity_ref": ENTITY,
    }

    for assignments, expected in (
        ([], "found 0"),
        (
            [
                _preparation_response()["data"]["assignments"][0],
                _preparation_response()["data"]["assignments"][0],
            ],
            "found 2",
        ),
    ):
        with pytest.raises(ArgumentProjectionError, match=expected):
            execute_argument_projection(
                plan,
                records={
                    "prepare-record": (
                        arguments,
                        _preparation_response(assignments=assignments),
                    )
                },
                literals={"entity_ref": ENTITY},
                source_record_ids={"preparation": "prepare-record"},
            )


def test_prepare_record_compiles_acquire_selection_without_starting_action():
    prepare = PlanNode(
        node_id="prepare",
        obligation_id="prepare",
        capability="manipulation.prepare",
        input_bindings={"entity_ref": ENTITY},
    )
    acquire = PlanNode(
        node_id="acquire",
        obligation_id="acquire",
        capability="object.acquire",
        dependencies=("prepare",),
        input_bindings={"entity_ref": ENTITY},
    )
    graph = _graph([prepare, acquire])
    policy = project_tool_spec(ACQUIRE_TOOL_SPEC)
    dispatch = AgentComposedDispatch(
        graph,
        (policy,),
        AdmissionContext(
            scene_revision="scene-1",
            settlements={"prepare": "completed"},
        ),
        input_schemas={"object.acquire": ACQUIRE_TOOL_SPEC["input_schema"]},
    )
    record = _record(
        record_id="prepare-record",
        node_id="prepare",
        tool_id="manipulation.prepare",
        arguments={"freshness_ms": 11, "max_age_ms": 1000},
        response=_preparation_response(),
    )
    task = _task(
        graph,
        records=[record],
        settlements=[
            NodeSettlement(
                task_id="task-1",
                revision_id="revision-1",
                node_id="prepare",
                status="completed",
                source_tool_id="manipulation.prepare",
                scene_revision="scene-1",
                evidence_refs=("tool:prepare-record",),
            )
        ],
    )
    coordinator = _Coordinator(task)

    ready = dispatch.describe()["ready_nodes"][-1]
    assert ready["argument_projection_sources"]["object.acquire"] == {
        "preparation": {
            "tool_id": "manipulation.prepare",
            "source_scope": "predecessor",
        }
    }
    result = json.loads(
        asyncio.run(
            ForgePlanSelectTool(coordinator, lambda: dispatch).execute(
                task_id="task-1",
                node_id="acquire",
                tool_id="object.acquire",
                decision_reason="select the unique prepared assignment",
                projection_sources={
                    "preparation": {"record_id": "prepare-record"}
                },
            )
        )
    )

    assert result["ok"], result
    assert len(coordinator.proposals) == 1
    assert coordinator.proposals[0]["tool_arguments"]["candidate_ref"] == CANDIDATE
    assert coordinator.proposals[0]["tool_arguments"]["assignment_ref"] == ASSIGNMENT
    assert "invocation_id" not in coordinator.proposals[0]
    assert result["motion_authorized"] is False


def test_successful_acquire_record_compiles_place_selection_from_effect_scene():
    acquire = PlanNode(
        node_id="acquire",
        obligation_id="acquire",
        capability="object.acquire",
        input_bindings={"entity_ref": ENTITY},
    )
    place = PlanNode(
        node_id="place",
        obligation_id="place",
        capability="object.place",
        dependencies=("acquire",),
        input_bindings={
            "entity_ref": ENTITY,
            "destination_ref": DESTINATION,
        },
    )
    graph = _graph([acquire, place])
    policy = project_tool_spec(PLACE_TOOL_SPEC)
    dispatch = AgentComposedDispatch(
        graph,
        (policy,),
        AdmissionContext(
            scene_revision="scene-2",
            settlements={"acquire": "completed"},
        ),
        input_schemas={"object.place": PLACE_TOOL_SPEC["input_schema"]},
    )
    record = _record(
        record_id="acquire-record",
        node_id="acquire",
        tool_id="object.acquire",
        semantics="action",
        arguments={"freshness_ms": 11, "max_age_ms": 1000},
        response=_acquire_response(),
    )
    task = _task(
        graph,
        records=[record],
        settlements=[
            NodeSettlement(
                task_id="task-1",
                revision_id="revision-1",
                node_id="acquire",
                status="completed",
                source_tool_id="object.acquire",
                scene_revision="scene-2",
                evidence_refs=("tool:acquire-record",),
                world_change_started=True,
                outcome_known=True,
            )
        ],
    )
    coordinator = _Coordinator(task)

    result = json.loads(
        asyncio.run(
            ForgePlanSelectTool(coordinator, lambda: dispatch).execute(
                task_id="task-1",
                node_id="place",
                tool_id="object.place",
                decision_reason="place the successfully acquired entity",
                projection_sources={
                    "acquisition": {"record_id": "acquire-record"}
                },
            )
        )
    )

    assert result["ok"], result
    arguments = coordinator.proposals[0]["tool_arguments"]
    assert arguments["acquire_invocation_ref"] == INVOCATION
    assert arguments["destination_ref"] == DESTINATION
    assert arguments["scene_revision"] == "scene-1"
    assert result["motion_authorized"] is False


def test_place_selection_rejects_acquire_record_from_wrong_effect_scene():
    acquire = PlanNode(
        node_id="acquire",
        obligation_id="acquire",
        capability="object.acquire",
        input_bindings={"entity_ref": ENTITY},
    )
    place = PlanNode(
        node_id="place",
        obligation_id="place",
        capability="object.place",
        dependencies=("acquire",),
        input_bindings={
            "entity_ref": ENTITY,
            "destination_ref": DESTINATION,
        },
    )
    graph = _graph([acquire, place])
    dispatch = AgentComposedDispatch(
        graph,
        (project_tool_spec(PLACE_TOOL_SPEC),),
        AdmissionContext(
            scene_revision="scene-2",
            settlements={"acquire": "completed"},
        ),
        input_schemas={"object.place": PLACE_TOOL_SPEC["input_schema"]},
    )
    record = _record(
        record_id="acquire-record",
        node_id="acquire",
        tool_id="object.acquire",
        semantics="action",
        arguments={"freshness_ms": 11, "max_age_ms": 1000},
        response=_acquire_response(new_scene_revision="scene-other"),
    )
    task = _task(
        graph,
        records=[record],
        settlements=[
            NodeSettlement(
                task_id="task-1",
                revision_id="revision-1",
                node_id="acquire",
                status="completed",
                source_tool_id="object.acquire",
                scene_revision="scene-other",
                evidence_refs=("tool:acquire-record",),
                world_change_started=True,
                outcome_known=True,
            )
        ],
    )
    coordinator = _Coordinator(task)

    result = json.loads(
        asyncio.run(
            ForgePlanSelectTool(coordinator, lambda: dispatch).execute(
                task_id="task-1",
                node_id="place",
                tool_id="object.place",
                decision_reason="reject stale acquisition effect",
                projection_sources={
                    "acquisition": {"record_id": "acquire-record"}
                },
            )
        )
    )

    assert not result["ok"]
    assert result["error"]["code"] == "consumer_projection_invalid"
    assert "does not produce the current scene" in result["error"]["message"]
    assert coordinator.proposals == []
    assert result["motion_authorized"] is False
