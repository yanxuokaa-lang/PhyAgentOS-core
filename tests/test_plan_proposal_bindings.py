from __future__ import annotations

from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.plan_proposal import (
    _complete_persisted_runtime_bindings,
    _validate_benchmark_plan_inputs,
    canonicalize_plan_graph,
)
from PhyAgentOS.forge.binding import BoundToolSpec, missing_preplan_queries
from PhyAgentOS.forge.manipulation import capability_snapshot_digest
from PhyAgentOS.planning import (
    ArgumentProjectionError,
    ArgumentProjectionPlan,
    PlanGraph,
    PlanNode,
    ToolSpecPolicy,
    execute_argument_projection,
    plan_graph_digest,
)


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


def test_execution_alias_in_entity_ref_is_normalized_before_projection_join():
    prepare = PlanNode(
        node_id="red.prepare",
        obligation_id="red.prepare",
        capability="manipulation.prepare",
        input_bindings={
            "entity_ref": "entity://block-red-1",
            "coordination_mode": "alternative_arm",
        },
    )
    task = _task((
        _record(
            "scene.bind",
            {"data": {"entities": [{
                "entity_ref": "entity://e1",
                "execution_entity_ref": "entity://block-red-1",
            }]}},
        ),
        _record("manipulation.capabilities", _snapshot_response()),
    ))

    completed = _complete_persisted_runtime_bindings(task, (prepare,))

    assert completed[0].input_bindings["entity_ref"] == "entity://e1"


@pytest.mark.parametrize("observed", ["entity://observed-object", "entity://custom-part-42"])
def test_standalone_grasp_execution_alias_joins_observed_geometry(observed):
    task = _task((_record("scene.bind", {"data": {"entities": [{
        "entity_ref": observed,
        "execution_entity_ref": "entity://runtime-object",
    }]}}),))
    grasp = PlanNode(
        node_id="grasp", obligation_id="grasp", capability="grasp.propose",
        input_bindings={"entity_ref": "entity://runtime-object"},
    )
    normalized = _complete_persisted_runtime_bindings(task, (grasp,))[0]
    plan = ArgumentProjectionPlan(
        projection_id="entity_geometry_target_v1",
        entity_collection="entities", envelope_collection="spatial_envelopes",
        output_collection="targets", entity_fields=("entity_ref", "category"),
        envelope_fields=("entity_ref", "frame_id"),
    )
    projected = execute_argument_projection(
        plan,
        records={"understood": ({}, {"data": {
            "entities": [{"entity_ref": observed, "category": "part"}],
            "spatial_envelopes": [{"entity_ref": observed, "frame_id": "world"}],
        }})},
        literals=normalized.input_bindings,
        source_record_id="understood",
    )

    assert projected["targets"][0]["entity_ref"] == observed
    assert grasp.input_bindings["entity_ref"] == "entity://runtime-object"


def test_standalone_grasp_ambiguous_alias_cannot_join_observed_geometry():
    task = _task((_record("scene.bind", {"data": {"entities": [
        {"entity_ref": entity, "execution_entity_ref": "entity://runtime-object"}
        for entity in ("entity://observed-a", "entity://observed-b")
    ]}}),))
    grasp = PlanNode(
        node_id="grasp", obligation_id="grasp", capability="grasp.propose",
        input_bindings={"entity_ref": "entity://runtime-object"},
    )
    normalized = _complete_persisted_runtime_bindings(task, (grasp,))[0]
    assert normalized.input_bindings["entity_ref"] == "entity://runtime-object"
    plan = ArgumentProjectionPlan(
        projection_id="entity_geometry_target_v1",
        entity_collection="entities", envelope_collection="spatial_envelopes",
        output_collection="targets",
    )
    with pytest.raises(ArgumentProjectionError, match="one uniquely matched entity"):
        execute_argument_projection(
            plan,
            records={"understood": ({}, {"data": {
                "entities": [{"entity_ref": "entity://observed-a"}, {"entity_ref": "entity://observed-b"}],
                "spatial_envelopes": [],
            }})},
            literals=normalized.input_bindings,
            source_record_id="understood",
        )


def test_standalone_grasp_cannot_resolve_alias_from_previous_capture():
    old_binding = _scene_response("capture-old")
    old_binding["data"]["entities"] = [{
        "entity_ref": "entity://old-observed", "execution_entity_ref": "entity://runtime-object",
    }]
    records = (
        _record("scene.observe", _scene_response("capture-old")),
        _record("scene.bind", old_binding),
        _record("scene.observe", _scene_response("capture-new")),
    )
    for index, record in enumerate(records):
        record.record_id = f"record-{index}"
        record.terminal = True
        record.semantics = "query"
        record.invocation_id = None
        record.arguments = {}
        record.evidence_refs = (f"tool:record-{index}",)
    task = _task(records)
    task.execution_records = records
    grasp = PlanNode(
        node_id="grasp", obligation_id="grasp", capability="grasp.propose",
        input_bindings={"entity_ref": "entity://runtime-object"},
    )

    normalized = _complete_persisted_runtime_bindings(task, (grasp,))[0]

    assert normalized.input_bindings["entity_ref"] == "entity://runtime-object"


@pytest.mark.parametrize("capability", ["grasp.propose", "manipulation.prepare", "object.acquire", "object.place"])
def test_complete_graph_entry_uses_the_same_canonical_binding_boundary(capability):
    task = _task((_record(
        "scene.bind",
        {"data": {"entities": [{
            "entity_ref": "entity://e1",
            "execution_entity_ref": "entity://block-red-1",
        }]}},
    ),))
    node = PlanNode(
        node_id="red.prepare",
        obligation_id="red.prepare",
        capability=capability,
        input_bindings={"entity_ref": "entity://block-red-1"},
    )
    payload = {
        "task_id": "task-test",
        "revision_id": "revision-test",
        "graph_digest": "0" * 64,
        "planner_decision_digest": "1" * 64,
        "policy_snapshot_digest": "2" * 64,
        "nodes": [node.model_dump(mode="json")],
    }
    payload["graph_digest"] = plan_graph_digest(payload)

    normalized = canonicalize_plan_graph(task, PlanGraph.model_validate(payload))

    assert normalized.nodes[0].input_bindings["entity_ref"] == "entity://e1"


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


def test_manipulation_nodes_inherit_task_verification_intent_fields():
    _, prepare = _nodes()
    task = _task((_record("manipulation.capabilities", _snapshot_response()),))
    task.verification = SimpleNamespace(
        goal="Arrange the three observed blocks in RGB order",
        success_criteria=["all three blocks occupy their benchmark destinations"],
    )

    completed = _complete_persisted_runtime_bindings(task, (prepare,))

    assert completed[0].input_bindings["goal"] == task.verification.goal
    assert completed[0].input_bindings["success_criteria"] == task.verification.success_criteria


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


def _benchmark_task(records):
    task = _task(records)
    task.runtime_binding = SimpleNamespace(
        runtime_profile="robotwin-blocks-ranking-graspnet",
    )
    return task


def test_benchmark_plan_rejects_agent_authored_destination_before_selection():
    task = _benchmark_task((_record(
        "task.goal",
        {"data": {"status": "available", "goals": [{
            "execution_entity_ref": "entity://block-red-1",
            "destination_ref": "destination://blocks-ranking-rgb/red-slot",
        }]}},
    ),))
    node = PlanNode(
        node_id="red-prepare",
        obligation_id="red-prepare",
        capability="manipulation.prepare",
        input_bindings={
            "execution_entity_ref": "entity://block-red-1",
            "destination_ref": "destination://agent/staging",
        },
    )

    with pytest.raises(ValueError, match="omit destination_ref"):
        _validate_benchmark_plan_inputs(task, (node,))


def test_benchmark_plan_rejects_autonomous_target_and_staging_nodes():
    task = _benchmark_task((_record(
        "task.goal",
        {"data": {"status": "available", "goals": [{
            "execution_entity_ref": "entity://block-red-1",
            "destination_ref": "destination://blocks-ranking-rgb/red-slot",
        }]}},
    ),))
    node = PlanNode(
        node_id="red-staging",
        obligation_id="red-staging",
        capability="manipulation.staging",
    )

    with pytest.raises(ValueError, match="manipulation.staging"):
        _validate_benchmark_plan_inputs(task, (node,))


def test_benchmark_profile_requires_task_goal_before_materialization():
    task = _benchmark_task((_record("task.goal", {"data": {
        "goal_source": "benchmark_task_definition", "goals": [],
    }}),))
    node = PlanNode(
        node_id="red-prepare",
        obligation_id="red-prepare",
        capability="manipulation.prepare",
        input_bindings={"execution_entity_ref": "entity://block-red-1"},
    )

    with pytest.raises(ValueError, match="successful task.goal"):
        _validate_benchmark_plan_inputs(task, (node,))
