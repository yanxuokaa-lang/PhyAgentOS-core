from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest
import robotwin_route_planner as module


class Entity:
    def __init__(self):
        self.qpos = [0.0] * 9

    def get_qpos(self):
        return self.qpos.copy()

    def set_qpos(self, qpos):
        self.qpos = list(qpos)


@pytest.fixture
def route(monkeypatch):
    monkeypatch.setattr(module, "planner_gripper_state", lambda *args: nullcontext([]))
    entity = Entity()
    events = []
    model = SimpleNamespace(detach_object_from_robot=lambda: events.append("detach"))
    planner = SimpleNamespace(motion_gen=model)
    starts = []

    def plan(pose, last_qpos):
        starts.append(last_qpos[:7])
        end = np.array(last_qpos[:7]) + 0.01
        return {
            "status": "Success",
            "position": np.array([last_qpos[:7], end]),
            "velocity": np.zeros((2, 7)),
        }

    task = SimpleNamespace(
        robot=SimpleNamespace(
            left_entity=entity,
            left_planner=planner,
            left_plan_path=plan,
            get_left_ee_pose=lambda: [0.0, 0.0, 0.8, 1.0, 0.0, 0.0, 0.0],
        )
    )
    monkeypatch.setattr(module, "_joint_limits", lambda planner: [[-3.0] * 7, [3.0] * 7])
    monkeypatch.setattr(module, "_validate_world_pose", lambda *args: None)
    monkeypatch.setattr(module, "_validate_gripper_table_clearance", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "_attach_object_to_planner", lambda *args: events.append("attach"))
    monkeypatch.setattr(
        module,
        "_validate_attached_support_departure",
        lambda *args: events.append("attached_check"),
    )
    monkeypatch.setattr(
        module, "add_released_object", lambda *args: events.append("released_obstacle") or []
    )
    pose = {"frame_id": "world", "position_m": [0, 0, 1], "orientation_xyzw": [0, 0, 0, 1]}
    phases = ("approach", "contact", "close", "lift", "transport", "descent", "release", "retreat")
    candidate = {
        "candidate_ref": "candidate://block/0",
        "attached_object": {"half_extents_m": [0.02] * 3},
        "placement_target": {"target_object_pose": deepcopy(pose)},
        "route": [
            {"phase": phase, "gripper_state": "open", "waypoints": [deepcopy(pose)]}
            for phase in phases
        ],
    }
    request = {"frame_id": "world", "workspace_bounds_m": {}}
    return task, request, candidate, entity, events, starts


def test_route_chains_predicted_endpoints_and_restores_without_scene_steps(route):
    task, request, candidate, entity, events, starts = route
    result = module.evaluate_route_arm(task, request, candidate, "left", object())
    assert result["status"] == "pass"
    assert len(result["segments"]) == 9
    assert starts[1] == pytest.approx([0.01] * 7)
    assert starts[-2] == pytest.approx([0.07] * 7)
    assert starts[-1] == pytest.approx([0.08] * 7)
    assert entity.qpos == [0.0] * 9
    assert events == ["attach", "attached_check", "detach", "released_obstacle"]
    assert result["motion_authorized"] is False


def test_contact_success_does_not_hide_retreat_failure(route):
    task, request, candidate, entity, events, starts = route
    original_plan = task.robot.left_plan_path

    def plan(pose, last_qpos):
        if len(starts) == 7:
            return {"status": "Fail"}
        return original_plan(pose, last_qpos)

    task.robot.left_plan_path = plan
    result = module.evaluate_route_arm(task, request, candidate, "left", object())
    assert result["status"] == "fail"
    assert result["failed_phase"] == "retreat"
    assert entity.qpos == [0.0] * 9
    assert events[-1] == "released_obstacle"


def test_attached_failure_restores_state_and_rejects(route, monkeypatch):
    task, request, candidate, entity, events, starts = route

    def reject(*args):
        raise ValueError("attached collision")

    monkeypatch.setattr(module, "_validate_attached_support_departure", reject)
    result = module.evaluate_route_arm(task, request, candidate, "left", object())
    assert result["failed_phase"] == "lift"
    assert result["status"] == "fail"
    assert events[-1] == "detach"
    assert entity.qpos == [0.0] * 9


def test_arm_selection_uses_complete_route_not_contact(monkeypatch):
    monkeypatch.setattr(
        module,
        "evaluate_route_arm",
        lambda task, request, candidate, arm, actor: {
            "arm": arm,
            "status": "fail" if arm == "left" else "pass",
        },
    )
    result = module.evaluate_route(None, {}, {"candidate_ref": "candidate://block/0"}, None)
    assert result["selected_arm"] == "right"


def test_diagnostic_success_never_promotes_rejected_route(route, monkeypatch):
    task, request, candidate, entity, events, starts = route
    original_plan = task.robot.left_plan_path

    def plan(pose, last_qpos):
        if len(starts) == 5:
            return {"status": "Fail"}
        return original_plan(pose, last_qpos)

    task.robot.left_plan_path = plan
    monkeypatch.setattr(
        "robotwin_descent_diagnostic.diagnose_attached_segment",
        lambda *args: {"robot_only_status": "success", "diagnostic_only": True},
    )
    result = module.evaluate_route_arm(task, request, candidate, "left", object(), diagnose_failure=True)
    assert result["status"] == "fail"
    assert result["failed_phase"] == "descent"
    assert result["diagnostic"]["robot_only_status"] == "success"
    assert result["motion_authorized"] is False
    assert entity.qpos == [0.] * 9


def test_retreat_obstacle_covers_both_release_and_landing(route):
    candidate = route[2]
    candidate["placement_target"]["release_clearance_m"] = .005
    candidate["execution_grasp"] = {"support_clear_direction": {"vector": [0, 0, 1]}}
    pose, extents = module.released_object_envelope(candidate)
    assert pose["position_m"] == pytest.approx([0, 0, 1.0025])
    assert extents == pytest.approx([.02, .02, .0225])
    assert candidate["placement_target"]["target_object_pose"]["position_m"] == [0, 0, 1]


@pytest.mark.parametrize("failed_phase", ["approach", "contact"])
def test_contact_reports_exact_failed_phase_and_preserves_joint_state(route, monkeypatch, failed_phase):
    task, _, _, entity, _, _ = route
    calls = []

    def plan(*args, **kwargs):
        phase = "approach" if not calls else "contact"
        calls.append(phase)
        if phase == failed_phase:
            return {"status": "Fail", "native_planner_status": "MotionGenStatus.IK_FAIL"}
        return {"status": "Success", "position": np.zeros((2, 7)),
                "velocity": np.zeros((2, 7))}

    monkeypatch.setattr(module, "plan_path_with_status", plan)
    grasp = {"robot_target_pose": {"frame_id": "world", "position_m": [0, 0, 1],
                                   "orientation_xyzw": [0, 0, 0, 1]},
             "ingress_direction": {"vector": [0, 0, -1]}}
    result = module.evaluate_contact(task, grasp, "left", .05)
    assert result["planner_status"] == "failed"
    assert result["failed_phase"] == failed_phase
    assert "IK_FAIL" in result["reason"]
    assert calls == (["approach"] if failed_phase == "approach" else ["approach", "contact"])
    assert entity.qpos == [0.] * 9


def test_retreat_diagnostic_keeps_world_and_never_promotes_failure(route, monkeypatch):
    task, request, candidate, entity, events, starts = route
    original_plan = task.robot.left_plan_path

    def plan(pose, last_qpos):
        if len(starts) == 7:
            return {"status": "Fail"}
        return original_plan(pose, last_qpos)

    def diagnose(task, arm, qpos):
        assert events[-1] == "released_obstacle"
        assert qpos[:7] == pytest.approx([.07] * 7)
        return {"collisions": [{"obstacle": "released_target"}], "diagnostic_only": True}

    task.robot.left_plan_path = plan
    monkeypatch.setattr("robotwin_descent_diagnostic.diagnose_start_collisions", diagnose)
    result = module.evaluate_route_arm(task, request, candidate, "left", object(), diagnose_failure=True)
    assert result["status"] == "fail"
    assert result["diagnostic"]["collisions"][0]["obstacle"] == "released_target"
    assert entity.qpos == [0.] * 9
    assert result["motion_authorized"] is False
