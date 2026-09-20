from types import SimpleNamespace

import numpy as np
import pytest
from robotwin_gripper_geometry import geometry_samples, gripper_configuration


def robot():
    joints = [SimpleNamespace(get_name=lambda i=i: f"finger{i}",
                              get_limits=lambda: np.array([[0., .04]])) for i in range(2)]
    entity = SimpleNamespace(get_active_joints=lambda: joints, get_qpos=lambda: [.017, .018])
    return SimpleNamespace(robot=SimpleNamespace(
        right_entity=entity, right_gripper=[(joint, 1., 0.) for joint in joints],
        right_gripper_scale=[-.01, .05]))


def test_measurement_is_not_closed_command_or_open_lock():
    task = robot()
    measured = gripper_configuration(task, "right")
    assert [x["bounds_m"] for x in measured] == [[.017, .017], [.018, .018]]
    closed = gripper_configuration(task, "right", "closed")
    assert [x["bounds_m"] for x in closed] == [[.017, .017], [.018, .018]]
    assert all(x["source"] == "measured_reference_holding_prediction_unavailable" for x in closed)
    assert all(x["command_target_m"] == -.01 for x in closed)
    assert len(list(geometry_samples([.017, .018], closed))) == 1
    opened = gripper_configuration(task, "right", "open")
    assert all(x["bounds_m"] == [.04, .04] and x["command_target_m"] == .05 for x in opened)
    assert task.robot.right_entity.get_qpos() == [.017, .018]


def test_missing_or_invalid_state_never_becomes_zero_width():
    task = robot()
    task.robot.right_entity.get_qpos = lambda: [float("nan"), .02]
    with pytest.raises(ValueError, match="measured position"):
        gripper_configuration(task, "right")
