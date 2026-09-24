from __future__ import annotations

from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.plan_proposal import _complete_persisted_runtime_bindings
from PhyAgentOS.forge.binding import BoundToolSpec, missing_preplan_queries
from PhyAgentOS.forge.manipulation import capability_snapshot_digest
from PhyAgentOS.planning import PlanNode, ToolSpecPolicy


def _record(tool_id: str, response: dict, *, node_id: str | None = None):
    return SimpleNamespace(
        record_id=f"record-{tool_id}",
        node_id=node_id,
        tool_id=tool_id,
        status="succeeded",
        response=response,
    )


def _snapshot_response() -> dict:
    payload = {
        "schema_version": "paos-manipulation-capability-snapshot/v1",
        "snapshot_ref": "artifact://capabilities/current",
        "snapshot_digest": "0" * 64,
        "scene_revision": "scene-1",
        "observation_ref": "observation://scene-1/head_camera",
        "calibration_ref": "artifact://scene-1/calibration",
        "embodiment_id": "franka-panda",
        "topology": "dual_independent",
        "profile_digest": "1" * 64,
        "captured_at": "2026-09-22T12:00:00+00:00",
        "arms": [
            {
                "arm_id": "left",
                "base_frame": "world",
                "tool_frame": "left-hand",
                "planner_profile_ref": "artifact://planner/left",
                "workspace_ref": "artifact://workspace/left",
                "joint_limits_ref": "artifact://limits/left",
                "motion_capabilities_ref": None,
                "gripper_identity": "gripper",
                "supported_modes": ["alternative_resource"],
                "availability": "available",
            },
            {
                "arm_id": "right",
                "base_frame": "world",
                "tool_frame": "right-hand",
                "planner_profile_ref": "artifact://planner/right",
                "workspace_ref": "artifact://workspace/right",
                "joint_limits_ref": "artifact://limits/right",
                "motion_capabilities_ref": None,
                "gripper_identity": "gripper",
                "supported_modes": ["alternative_resource"],
                "availability": "available",
            },
        ],
        "motion_authorized": False,
    }
    payload["snapshot_digest"] = capability_snapshot_digest(payload)
    return {"data": payload}


def _task(records):
    revision = SimpleNamespace(execution_records=tuple(records))
    return SimpleNamespace(active_revision=revision, revisions=(revision,))


def _discovery_task(records):
    tools = tuple(
        BoundToolSpec(
            tool_id=tool_id,
            semantics="query",
            spec_sha256="a" * 64,
            ready_at_binding=True,
            planning_policy=ToolSpecPolicy(
                tool_id=tool_id,
                semantics="query",
                spec_digest="b" * 64,
                requires_before_plan=True,
            ),
        )
        for tool_id in (
            "scene.observe",
            "manipulation.capabilities",
            "scene.understand",
            "scene.bind",
            "task.goal",
        )
    )
    revision = SimpleNamespace(execution_records=tuple(records))
    return SimpleNamespace(
        active_revision=revision,
        primary_skill_binding=SimpleNamespace(required_tools=tools),
    )


def _scene_response(capture: str) -> dict:
    scene = "scene-1"
    return {
        "data": {
            "status": "available",
            "scene_revision": scene,
            "observation_ref": f"observation://{scene}/head_camera",
            "calibration_ref": f"artifact://{scene}/{capture}/calibration",
        }
    }


def _nodes(*, allowed_arms=None):
    grasp = PlanNode(
        node_id="red.grasp",
        obligation_id="red.grasp",
        capability="grasp.propose",
    )
    bindings = {
        "target_execution_entity_ref": "entity://block-red-1",
        "coordination_mode": "alternative_arm",
    }
    if allowed_arms is not None:
        bindings["allowed_arms"] = allowed_arms
    prepare = PlanNode(
        node_id="red.prepare",
        obligation_id="red.prepare",
        capability="manipulation.prepare",
        dependencies=("red.grasp",),
        input_bindings=bindings,
    )
    return grasp, prepare


def test_unique_scene_identity_and_capability_ids_are_bound_before_agent_selection():
    grasp, prepare = _nodes()
    task = _task(
        (
            _record(
                "scene.bind",
                {"data": {"entities": [{
                    "entity_ref": "entity://observed-red",
                    "execution_entity_ref": "entity://block-red-1",
                }]}},
            ),
            _record("manipulation.capabilities", _snapshot_response()),
        )
    )

    completed = _complete_persisted_runtime_bindings(task, (grasp, prepare))

    assert completed[0].input_bindings["entity_ref"] == "entity://observed-red"
    assert completed[1].input_bindings["entity_ref"] == "entity://observed-red"
    assert completed[1].input_bindings["allowed_arms"] == ["left", "right"]


def test_discovery_requires_scene_bound_queries_from_latest_capture():
    records = [
        _record("scene.observe", _scene_response("capture-1")),
        _record("manipulation.capabilities", _scene_response("capture-0")),
        _record("scene.understand", _scene_response("capture-1")),
        _record("scene.bind", _scene_response("capture-1")),
        _record("task.goal", {"data": {"status": "available"}}),
    ]
    task = _discovery_task(records)

    assert missing_preplan_queries(task) == ("manipulation.capabilities",)

    records[1] = _record("manipulation.capabilities", _scene_response("capture-1"))
    task = _discovery_task(records)
    assert missing_preplan_queries(task) == ()


def test_runtime_binding_does_not_propagate_stale_capability_snapshot():
    _, prepare = _nodes()
    task = _task(
        (
            _record("scene.observe", _scene_response("capture-1")),
            _record("manipulation.capabilities", _snapshot_response()),
        )
    )

    completed = _complete_persisted_runtime_bindings(task, (prepare,))

    assert "capability_snapshot_ref" not in completed[0].input_bindings


def test_capability_topology_materializes_missing_prepare_semantics():
    prepare = PlanNode(
        node_id="red.prepare",
        obligation_id="red.prepare",
        capability="manipulation.prepare",
        input_bindings={"execution_entity_ref": "entity://block-red-1"},
    )
    task = _task((_record("manipulation.capabilities", _snapshot_response()),))

    completed = _complete_persisted_runtime_bindings(task, (prepare,))

    assert completed[0].input_bindings["coordination_mode"] == "alternative_arm"
    assert completed[0].input_bindings["allowed_arms"] == ["left", "right"]


def test_single_arm_capability_materializes_single_arm_semantics():
    response = _snapshot_response()
    snapshot = dict(response["data"])
    snapshot["topology"] = "single_arm"
    snapshot["arms"] = [dict(snapshot["arms"][0], supported_modes=["single_resource"])]
    snapshot["snapshot_digest"] = capability_snapshot_digest(snapshot)
    prepare = PlanNode(
        node_id="red.prepare",
        obligation_id="red.prepare",
        capability="manipulation.prepare",
        input_bindings={"execution_entity_ref": "entity://block-red-1"},
    )
    task = _task((_record("manipulation.capabilities", {"data": snapshot}),))

    completed = _complete_persisted_runtime_bindings(task, (prepare,))

    assert completed[0].input_bindings["coordination_mode"] == "single_arm"
    assert completed[0].input_bindings["allowed_arms"] == ["left"]


def test_ambiguous_scene_identity_remains_unbound():
    grasp, prepare = _nodes()
    task = _task((
        _record(
            "scene.bind",
            {"data": {"entities": [
                {"entity_ref": "entity://observed-red-a", "execution_entity_ref": "entity://block-red-1"},
                {"entity_ref": "entity://observed-red-b", "execution_entity_ref": "entity://block-red-1"},
            ]}},
        ),
    ))

    completed = _complete_persisted_runtime_bindings(task, (grasp, prepare))

    assert "entity_ref" not in completed[0].input_bindings
    assert "entity_ref" not in completed[1].input_bindings


def test_oracle_destination_compiles_agent_label_to_scene_binding():
    grasp = PlanNode(
        node_id="red.grasp",
        obligation_id="red.grasp",
        capability="grasp.propose",
        input_bindings={"entity_ref": "entity://red-block-1"},
    )
    prepare = PlanNode(
        node_id="red.prepare",
        obligation_id="red.prepare",
        capability="manipulation.prepare",
        dependencies=("red.grasp",),
        input_bindings={
            "entity_ref": "entity://red-block-1",
            "destination_ref": "destination://blocks-ranking-rgb/red-slot",
        },
    )
    task = _task(
        (
            _record(
                "scene.bind",
                {"data": {"entities": [{
                    "entity_ref": "entity://block-red-01",
                    "execution_entity_ref": "entity://block-red-1",
                }]}},
            ),
            _record(
                "task.goal",
                {"data": {
                    "goal_source": "benchmark_task_definition",
                    "goals": [{
                        "execution_entity_ref": "entity://block-red-1",
                        "destination_ref": "destination://blocks-ranking-rgb/red-slot",
                    }],
                }},
            ),
        )
    )

    completed = _complete_persisted_runtime_bindings(task, (grasp, prepare))

    assert completed[0].input_bindings["entity_ref"] == "entity://block-red-01"
    assert completed[1].input_bindings["entity_ref"] == "entity://block-red-01"


def test_invalid_capability_arm_identity_is_rejected_before_runtime():
    _, prepare = _nodes(allowed_arms=["left_arm"])
    task = _task((_record("manipulation.capabilities", _snapshot_response()),))

    with pytest.raises(ValueError, match="left_arm.*left, right"):
        _complete_persisted_runtime_bindings(task, (prepare,))


def test_explicit_nested_intent_mode_wins_over_derived_topology_mode():
    grasp, prepare = _nodes(allowed_arms=["left", "right"])
    prepare.input_bindings["intent"] = {
        "goal": "acquire",
        "success_criteria": ["terminal"],
        "coordination_mode": "single_arm",
    }
    prepare.input_bindings["coordination_mode"] = "alternative_arm"
    task = _task((_record("manipulation.capabilities", _snapshot_response()),))
    completed = _complete_persisted_runtime_bindings(task, (grasp, prepare))
    bindings = completed[1].input_bindings
    assert bindings["intent"]["coordination_mode"] == "single_arm"
    assert "coordination_mode" not in bindings
