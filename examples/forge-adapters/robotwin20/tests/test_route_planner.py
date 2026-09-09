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
        robot=SimpleNamespace(left_entity=entity, left_planner=planner, left_plan_path=plan)
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
    assert len(result["segments"]) == 8
    assert starts[1] == pytest.approx([0.01] * 7)
    assert starts[-1] == pytest.approx([0.07] * 7)
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
