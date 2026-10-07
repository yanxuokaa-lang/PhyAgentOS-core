import hashlib
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
import robotwin_simulation_probe_worker as probe_worker
from robotwin_capability_controller import ControllerLimits
from test_route_readiness import _request

from robotwin20_adapter.dual_arm_state import build_dual_arm_state
from robotwin20_adapter.persistent_action_approval import (
    PersistentActionApprovalError,
    PersistentSimulationActionApprover,
    validate_persistent_action_approval,
)
from robotwin20_adapter.route_readiness import route_geometry_digest


def _assignment(route):
    return {
        "assignment_ref": "artifact://assignments/task/revision/node",
        "assignment_digest": "a" * 64,
        "candidate_ref": route["candidates"][0]["candidate_ref"],
        "entity_ref": route["candidates"][0]["entity_ref"],
        "scene_revision": route["scene_revision"],
        "route_digest": route_geometry_digest(route),
        "motion_authorized": False,
    }


def _dual_arm_state(route):
    def arm(arm_id):
        return {
            "qpos": [0.0] * 7,
            "drive_target": [0.0] * 7,
            "gripper": 1.0,
            "links": [{
                "link_id": f"{arm_id}:panda_hand",
                "link_name": "panda_hand",
                "pose_wxyz": [0.0, 0.0, 0.8, 1.0, 0.0, 0.0, 0.0],
            }],
        }

    return build_dual_arm_state(
        scene_revision=route["scene_revision"],
        state_revision=f"{route['scene_revision']}:stabilized",
        frame_id=route["frame_id"],
        left=arm("left"),
        right=arm("right"),
        provenance_refs=[
            f"artifact://simulation-probe/{route['scene_revision']}/dual-arm-state"
        ],
    )


def _write_artifact(root, ref, payload):
    path = root.joinpath(*ref.removeprefix("artifact://").split("/")).with_suffix(".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, sort_keys=True).encode()
    path.write_bytes(raw)
    return path, hashlib.sha256(raw).hexdigest()


def _prepared_artifact(root, route, candidate, initial_state):
    planned_route = deepcopy(candidate["route"])
    planned_route[-1]["waypoints"].append({
        "frame_id": route["frame_id"],
        "position_m": [0.0, 0.0, 0.8],
        "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
    })
    segments = [
        {
            "phase": phase["phase"],
            "gripper_state": phase["gripper_state"],
            "waypoint_index": index,
            "route_waypoint": deepcopy(waypoint),
            "position": [[0.0] * 7],
            "velocity": [[0.0] * 7],
        }
        for phase in planned_route
        for index, waypoint in enumerate(phase["waypoints"])
    ]
    plan = {
        "schema_version": "paos-robotwin20-prepared-execution-plan/v2",
        "request_id": route["request_id"],
        "candidate_ref": candidate["candidate_ref"],
        "entity_ref": candidate["entity_ref"],
        "scene_revision": route["scene_revision"],
        "frame_id": route["frame_id"],
        "arm": "left",
        "initial_qpos": list(initial_state["left"]["qpos"]),
        "initial_dual_arm_state": deepcopy(initial_state),
        "segments": segments,
        "motion_authorized": False,
    }
    ref = "artifact://readiness/complete-route"
    _write_artifact(root, ref, {
        "route_geometry_digest": route_geometry_digest(route),
        "request_id": route["request_id"],
        "candidate_ref": candidate["candidate_ref"],
        "entity_ref": candidate["entity_ref"],
        "scene_revision": route["scene_revision"],
        "motion_authorized": False,
        "world_change_started": False,
        "planner_evaluation": {
            "arm_attempts": [{
                "arm": "left",
                "status": "pass",
                "execution_plan": plan,
            }],
        },
    })
    return ref


def test_runtime_monitored_approval_binds_exact_route_and_assignment(tmp_path):
    route = _request(tmp_path)
    assignment = _assignment(route)
    approver = PersistentSimulationActionApprover(
        tmp_path,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
    )
    reference = approver.issue(
        route,
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
        readiness_evidence_refs=["artifact://readiness/right-arm"],
    )
    approval = validate_persistent_action_approval(
        tmp_path,
        reference,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
        route_request=route,
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
    )
    assert approval["simulation_only"] is True
    assert approval["motion_authorized"] is True
    assert approval["required_execution_checks"] == [
        "contact_dynamics",
        "stop_control",
    ]


@pytest.mark.parametrize("change", ["route", "assignment", "mode", "task"])
def test_runtime_monitored_approval_rejects_changed_binding(tmp_path, change):
    route = _request(tmp_path)
    assignment = _assignment(route)
    approver = PersistentSimulationActionApprover(
        tmp_path,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
    )
    reference = approver.issue(
        route,
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
        readiness_evidence_refs=["artifact://readiness/right-arm"],
    )
    current_route = deepcopy(route)
    current_assignment = deepcopy(assignment)
    mode = "runtime_monitored"
    task_name = "blocks_ranking_rgb"
    if change == "route":
        current_route["request_id"] = "another-request"
    elif change == "assignment":
        current_assignment["assignment_digest"] = "b" * 64
    elif change == "mode":
        mode = "disabled"
    else:
        task_name = "another_task"
    with pytest.raises(PersistentActionApprovalError):
        validate_persistent_action_approval(
            tmp_path,
            reference,
            task_name=task_name,
            mode=mode,
            route_request=current_route,
            candidate_ref=assignment["candidate_ref"],
            assignment=current_assignment,
        )


def test_disabled_mode_cannot_issue_approval(tmp_path):
    with pytest.raises(PersistentActionApprovalError, match="runtime_monitored"):
        PersistentSimulationActionApprover(
            tmp_path,
            task_name="blocks_ranking_rgb",
            mode="disabled",
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("authorized_at", "2026-09-21T12:00:00", "timezone"),
        ("authorized_at", "not-a-timestamp", "timestamp"),
        ("readiness_evidence_refs", ["artifact://../escape"], "path is unsafe"),
        ("readiness_evidence_refs", ["not-an-artifact"], "reference is invalid"),
    ],
)
def test_runtime_revalidates_approval_metadata(tmp_path, field, value, message):
    route = _request(tmp_path)
    assignment = _assignment(route)
    approver = PersistentSimulationActionApprover(
        tmp_path,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
    )
    reference = approver.issue(
        route,
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
        readiness_evidence_refs=["artifact://readiness/right-arm"],
    )
    path = tmp_path.joinpath(*reference.removeprefix("artifact://").split("/")).with_suffix(".json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = value
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PersistentActionApprovalError, match=message):
        validate_persistent_action_approval(
            tmp_path,
            reference,
            task_name="blocks_ranking_rgb",
            mode="runtime_monitored",
            route_request=route,
            candidate_ref=assignment["candidate_ref"],
            assignment=assignment,
        )


def test_engine_rejects_changed_approval_before_action_setup(tmp_path):
    from robotwin_persistent_engine import RoboTwinPersistentEngine

    route = _request(tmp_path)
    assignment = {
        **_assignment(route),
        "task_id": "task-1",
        "capability_snapshot_ref": "artifact://capabilities/snapshot",
        "selected_arm_ids": ["right"],
    }
    assignment_path = tmp_path / "assignments" / "task" / "revision" / "node.json"
    assignment_path.parent.mkdir(parents=True)
    assignment_path.write_text(json.dumps(assignment), encoding="utf-8")
    approval_ref = PersistentSimulationActionApprover(
        tmp_path,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
    ).issue(
        route,
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
        readiness_evidence_refs=["artifact://readiness/right-arm"],
    )
    approval_path = tmp_path.joinpath(
        *approval_ref.removeprefix("artifact://").split("/")
    ).with_suffix(".json")
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    approval["authorized_at"] = "not-a-timestamp"
    approval_path.write_text(json.dumps(approval), encoding="utf-8")

    snapshots = []
    engine = object.__new__(RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.profile = {"simulation_action_mode": "runtime_monitored"}
    engine.task_adapter = SimpleNamespace(task_name="blocks_ranking_rgb")
    engine.backend = SimpleNamespace(
        snapshot=lambda: snapshots.append(True)
        or {"scene_revision": route["scene_revision"]}
    )
    arguments = {
        "route_request": route,
        "candidate_ref": assignment["candidate_ref"],
        "entity_ref": assignment["entity_ref"],
        "assignment_ref": assignment["assignment_ref"],
        "assignment": assignment,
        "task_id": assignment["task_id"],
        "capability_snapshot_ref": assignment["capability_snapshot_ref"],
        "approval_ref": approval_ref,
    }

    with pytest.raises(PersistentActionApprovalError, match="timestamp"):
        engine._prepare(arguments)
    assert snapshots == [True]
    assert not hasattr(engine.backend, "_task")


def test_engine_uses_validated_runtime_identity_not_host_profile(tmp_path, monkeypatch):
    import robotwin_persistent_engine as module

    route = _request(tmp_path)
    assignment = {
        **_assignment(route),
        "task_id": "task-1",
        "capability_snapshot_ref": "artifact://capabilities/snapshot",
        "selected_arm_ids": ["right"],
    }
    assignment_path = tmp_path / "assignments" / "task" / "revision" / "node.json"
    assignment_path.parent.mkdir(parents=True)
    assignment_path.write_text(json.dumps(assignment), encoding="utf-8")
    approval_ref = PersistentSimulationActionApprover(
        tmp_path,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
    ).issue(
        route,
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
        readiness_evidence_refs=["artifact://readiness/right-arm"],
    )

    observed = {}

    def stop_after_identity(*args, **kwargs):
        observed["robot_identity"] = kwargs["robot_identity"]
        raise RuntimeError("policy boundary reached")

    monkeypatch.setattr(module.probe, "_validate_request_policies", stop_after_identity)
    engine = object.__new__(module.RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.profile = {"simulation_action_mode": "runtime_monitored"}
    engine.runtime_profile = {"robot_identity": "franka-panda"}
    engine.duration = 30.0
    engine.task_adapter = SimpleNamespace(task_name="blocks_ranking_rgb")
    engine.backend = SimpleNamespace(
        snapshot=lambda: {"scene_revision": route["scene_revision"]}
    )
    arguments = {
        "route_request": route,
        "candidate_ref": assignment["candidate_ref"],
        "entity_ref": assignment["entity_ref"],
        "assignment_ref": assignment["assignment_ref"],
        "assignment": assignment,
        "task_id": assignment["task_id"],
        "capability_snapshot_ref": assignment["capability_snapshot_ref"],
        "approval_ref": approval_ref,
    }

    with pytest.raises(RuntimeError, match="policy boundary"):
        engine._prepare(arguments)
    assert observed == {"robot_identity": "franka-panda"}


def _engine_prepare_fixture(tmp_path, monkeypatch, *, drift=False):
    import robotwin_observed_collision
    import robotwin_persistent_engine as module
    import robotwin_simulation_probe_worker as probe

    route = _request(tmp_path)
    candidate = route["candidates"][0]
    geometry_ref = candidate["attached_object"]["geometry_ref"]
    _geometry_path, geometry_sha = _write_artifact(tmp_path, geometry_ref, {"fixture": True})
    candidate["attached_object"]["geometry_sha256"] = geometry_sha
    world_ref = route["collision_world"]["artifact_ref"]
    _world_path, world_sha = _write_artifact(tmp_path, world_ref, {
        "world_digest": route["collision_world"]["world_digest"],
        "source_scene_facts_ref": "artifact://scene/source",
    })
    route["collision_world"]["sha256"] = world_sha
    _write_artifact(tmp_path, "artifact://scene/source", {"geometry_source": "synthetic"})
    initial_state = _dual_arm_state(route)
    readiness_ref = _prepared_artifact(tmp_path, route, candidate, initial_state)
    assignment = {
        **_assignment(route),
        "task_id": "task-1",
        "capability_snapshot_ref": "artifact://capabilities/snapshot",
        "selected_arm_ids": ["left"],
        "readiness_evidence_ref": readiness_ref,
    }
    assignment_ref = assignment["assignment_ref"]
    _write_artifact(tmp_path, assignment_ref, assignment)
    approval_ref = "artifact://approvals/action"
    _write_artifact(tmp_path, approval_ref, {"fixture": True})

    current_state = deepcopy(initial_state)
    if drift:
        current_state["right"]["qpos"][0] = 0.1

    task = SimpleNamespace(
        robot=SimpleNamespace(
            left_planner=SimpleNamespace(), right_planner=SimpleNamespace(),
        )
    )
    monkeypatch.setattr(module, "validate_persistent_action_approval", lambda *args, **kwargs: {})
    monkeypatch.setattr(probe, "_validate_request_policies", lambda *args, **kwargs: {
        "execution_input_digests": {}, "motion_capability_documents": {"left": object()},
        "controller_source_sha256": "controller-source",
    })
    monkeypatch.setattr(probe, "_controller_limits", lambda *_: ControllerLimits(
        joint_order=tuple(f"joint-{index}" for index in range(7)),
        position_lower_rad=(-3.0,) * 7,
        position_upper_rad=(3.0,) * 7,
        velocity_lower_radps=(-3.0,) * 7,
        velocity_upper_radps=(3.0,) * 7,
    ))
    monkeypatch.setattr(probe, "_validate_route_input_artifacts", lambda *args: {})
    monkeypatch.setattr(probe, "_validate_runtime_route_input_binding", lambda *args: None)
    monkeypatch.setattr(probe, "bind_scene_table", lambda *args: None)
    monkeypatch.setattr(probe, "_capture_dual_arm_state", lambda *args: deepcopy(current_state))
    monkeypatch.setattr(probe, "_capture_peer_projection", lambda task, state, arm: {"arm": arm})
    monkeypatch.setattr(probe, "apply_collision_world", lambda *args, **kwargs: {"applied": True})
    monkeypatch.setattr(probe, "_label_probe_actors", lambda *args: None)
    monkeypatch.setattr(probe, "_build_route_controllers", lambda *args: {})
    monkeypatch.setattr(robotwin_observed_collision, "configure_observed_collision", lambda *args: None)
    monkeypatch.setattr(probe, "evaluate_route_arm", lambda *args, **kwargs: pytest.fail("Action replanned a route"))

    engine = object.__new__(module.RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.profile = {"simulation_action_mode": "runtime_monitored", "start_state_tolerance_rad": 1e-4}
    engine.runtime_profile = {"robot_identity": "fixture-robot"}
    engine.duration = 10.0
    engine.stop = SimpleNamespace(exists=lambda: False)
    engine.task_adapter = SimpleNamespace(task_name="fixture-task")
    engine.backend = SimpleNamespace(
        _task=task,
        snapshot=lambda: {"scene_revision": route["scene_revision"]},
    )
    arguments = {
        "route_request": route,
        "candidate_ref": candidate["candidate_ref"],
        "entity_ref": candidate["entity_ref"],
        "assignment_ref": assignment_ref,
        "assignment": assignment,
        "task_id": assignment["task_id"],
        "capability_snapshot_ref": assignment["capability_snapshot_ref"],
        "approval_ref": approval_ref,
    }
    return engine, arguments, initial_state


def test_engine_prepare_loads_readiness_plan_without_second_route_solve(tmp_path, monkeypatch):
    engine, arguments, initial_state = _engine_prepare_fixture(tmp_path, monkeypatch)
    engine._prepare(arguments)
    assert engine._state["simulator_steps"] == 0
    assert engine._state["_prepared_execution_plan"]["arm"] == "left"
    assert engine._state["_prepared_execution_plan"]["world_state_comparison"]["within_tolerance"] is True
    assert engine._state["dual_arm_state"] == initial_state
    assert engine._phases is not None


def test_engine_prepare_rejects_peer_arm_drift_before_execution(tmp_path, monkeypatch):
    engine, arguments, _initial_state = _engine_prepare_fixture(tmp_path, monkeypatch, drift=True)
    with pytest.raises(probe_worker.PreparedExecutionPlanError) as rejected:
        engine._prepare(arguments)
    assert rejected.value.failure_code == "prepared_execution_world_state_drift"
    assert rejected.value.failure_owner == "binding"
    assert rejected.value.requires_replan is True
    assert engine._state["simulator_steps"] == 0
