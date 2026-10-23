from copy import deepcopy
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from isaacsim_lab.phase_motion import (
    IsaacPhaseMotion,
    PhaseMotionError,
    collision_hits,
    held_tool_pose,
    interpolate_pose,
    pose_matrix,
    process_waypoints,
    smooth_joint_segment,
    support_contact_allowed,
)


def test_physx_object_hit_rejects_obstacle_after_ignored_robot():
    def query(_radius, _center, report, _any_hit):
        for path in ("/World/robot/hand", "/World/obstacle"):
            if not report(SimpleNamespace(collision=path)):
                break
    assert collision_hits(query, .1, [0, 0, 0], ignore=lambda path: path.startswith("/World/robot/")) == ["/World/obstacle"]


def test_physx_swallowed_callback_error_cannot_qualify_clear_route():
    def query(*args):
        try:
            args[-2](SimpleNamespace())
        except Exception:
            pass  # PhysX's C++ boundary logs and swallows Python errors.
    with pytest.raises(PhaseMotionError) as error:
        collision_hits(query, .1, [0, 0, 0], ignore=lambda _: False)
    assert error.value.code == "collision_query_failed"


def config():
    import json
    return json.loads((Path(__file__).parents[1] / "configs/labutopia-mixture-motion.json").read_text())


def test_tool_tip_target_accounts_for_rotated_grasp_offset():
    relation = pose_matrix([.03, .02, -.1], Rotation.from_euler("z", .6).as_quat())
    tip = np.array([0., 0., -.15])
    wanted = np.array([.2, -.1, .9])
    rotation = Rotation.from_euler("y", .8).as_matrix()
    tcp = held_tool_pose(relation, tip, wanted, rotation)
    object_pose = tcp @ relation
    assert object_pose[:3, 3] + object_pose[:3, :3] @ tip == pytest.approx(wanted)
    assert object_pose[:3, :3] == pytest.approx(rotation)


@pytest.mark.parametrize("direction,sign", [("ccw", 1), ("cw", -1)])
def test_absolute_stir_circle_does_not_accumulate_positions(direction, sign):
    body = pose_matrix([.1, -.1, 1.], [0., 0., 0., 1.])
    tcp = pose_matrix([.1, -.1, 1.1], [0., 0., 0., 1.])
    relation = np.linalg.inv(tcp) @ body
    tip = np.array([0., 0., -.1])
    target = {"process_frame": {"origin_m": [.3, .05, .88], "axis": [0., 0., 1.]},
              "tool_frame": {"tip_offset_m": tip.tolist(), "tip_axis_local": [0., 0., -1.]}}
    before = deepcopy(target)
    points = process_waypoints("stir", {"radius_m": .009, "depth_m": .04, "turns": 2., "duration_s": 4., "direction": direction},
                               tcp, body, relation, target, config())
    actual = []
    for pose, _, stage in points:
        if stage == "process":
            placed = pose @ relation
            actual.append(placed[:3, 3] + placed[:3, :3] @ tip)
    actual = np.array(actual)
    assert np.linalg.norm(actual[:, :2] - [.3, .05], axis=1) == pytest.approx(np.full(len(actual), .009))
    assert actual[:, 2] == pytest.approx(np.full(len(actual), .84))
    assert target == before
    assert points[-1][2] == "exit"
    offsets = actual[:, :2] - [.3, .05]
    angles = np.unwrap(np.r_[np.pi / 2, np.arctan2(offsets[:, 1], offsets[:, 0])])
    assert angles[-1] - angles[0] == pytest.approx(sign * 2 * np.pi * (2 + config()["stir_entry_reserve_turns"]))


def test_missing_measured_process_feature_is_rejected():
    with pytest.raises(PhaseMotionError, match="tip_offset_m"):
        process_waypoints("pour", {"tilt_rad": .87, "hold_s": .6}, np.eye(4), np.eye(4), np.eye(4),
                          {"process_frame": {}}, config())


def test_support_contact_window_covers_first_execution_interpolation_only():
    supported = pose_matrix([.1, 0., .8], [0., 0., 0., 1.])
    first = supported.copy()
    first[2, 3] += .001
    assert support_contact_allowed("lift", first, supported, .008)
    first[0, 3] += .012  # Closing/releasing may slide the object on its support.
    assert support_contact_allowed("lift", first, supported, .008)
    assert support_contact_allowed("lower", first, supported, .008)
    far = supported.copy()
    far[2, 3] += .012
    assert not support_contact_allowed("lift", far, supported, .008)
    below = supported.copy()
    below[2, 3] -= .004
    assert not support_contact_allowed("lower", below, supported, .008)
    assert not support_contact_allowed("transport", first, supported, .008)


def test_joint_segment_bounds_speed_and_acceleration():
    start = np.zeros(7)
    goal = np.array([.1, -.04, 0., 0., .03, .2, 0.])
    dt = .005
    samples = np.array([start, *smooth_joint_segment(start, goal, dt, .4, .8), goal])
    velocity = np.diff(samples, axis=0) / dt
    acceleration = np.diff(velocity, axis=0) / dt
    assert np.max(np.abs(velocity)) <= .4
    assert np.max(np.abs(acceleration)) <= .8
    assert samples[-2] == pytest.approx(goal)


def test_continuous_circle_retimes_limits_without_stopping_at_each_knot():
    from isaacsim_lab.phase_motion import continuous_joint_path

    angles = np.linspace(0., 4.5 * np.pi, 285)
    points = np.column_stack((.03 * np.cos(angles), .03 * np.sin(angles)))
    dt = 1 / 60
    frames = continuous_joint_path(points, dt, 4.5, .4, .8)
    samples = np.vstack((points[0], frames, frames[-1]))
    velocity = np.diff(samples, axis=0) / dt
    acceleration = np.diff(np.vstack((np.zeros((1, 2)), velocity)), axis=0) / dt
    assert np.max(np.abs(velocity)) <= .4
    assert np.max(np.abs(acceleration)) <= .8
    speed = np.linalg.norm(velocity, axis=1)
    assert np.min(speed[len(speed)//4:3*len(speed)//4]) > .01
    assert frames[-1] == pytest.approx(points[-1])


def test_measured_feature_target_removes_grip_tilt_bias_without_axial_roll_command():
    from isaacsim_lab.phase_motion import measured_feature_target

    tcp = pose_matrix([.2, .1, 1.], Rotation.from_euler("x", .4).as_quat())
    nominal = pose_matrix([0., 0., -.1], [0., 0., 0., 1.])
    measured = pose_matrix([.002, 0., -.1], Rotation.from_euler("xy", [.035, -.01]).as_quat())
    tool = {"tip_offset_m": [0., 0., -.125], "tip_axis_local": [0., 0., -1.]}
    goal = measured_feature_target(tcp, nominal, measured, tool)
    expected, actual = tcp @ nominal, goal @ measured
    tip, axis = np.asarray(tool["tip_offset_m"]), np.asarray(tool["tip_axis_local"])
    assert actual[:3, 3] + actual[:3, :3] @ tip == pytest.approx(expected[:3, 3] + expected[:3, :3] @ tip)
    assert actual[:3, :3] @ axis == pytest.approx(expected[:3, :3] @ axis)
    rolled = measured.copy()
    rolled[:3, :3] = measured[:3, :3] @ Rotation.from_euler("z", .8).as_matrix()
    assert measured_feature_target(tcp, nominal, rolled, tool) == pytest.approx(goal)


def test_payload_boxes_cover_only_observed_points_without_mesh_access():
    from isaacsim_lab.phase_motion import observed_point_boxes
    z = np.linspace(0., .1, 100)
    points = np.column_stack((.04-.3*z, np.zeros(100), z))
    boxes = observed_point_boxes(points)
    for sample in points:
        assert any(np.all(sample >= low) and np.all(sample <= high) for low, high in boxes)
    assert boxes[-1][1][0] < .014


def test_release_qualification_uses_expected_supported_body_without_scene_mutation():
    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.config = config()
    model.body_from_observed = {"/World/source": np.eye(4)}
    model.hand_from_tcp = np.eye(4)
    model.joints = lambda: np.zeros(7)
    model.tcp = lambda *_: pose_matrix([0., 0., 1.], [0., 0., 0., 1.])
    model.limits = np.tile([-3., 3.], (7, 1))
    model.solver = SimpleNamespace(compute_inverse_kinematics=lambda *_a, **_k: (np.zeros(7), True))
    calls = []
    model._collisions = lambda *args, **kwargs: calls.append((args, kwargs))
    supported = pose_matrix([.1, .1, .8], [0., 0., 0., 1.])
    model.qualify([(model.tcp(), .1, "release"), (model.tcp(), .1, "retreat")],
                  "/World/selected", np.eye(4), "place", supported)
    assert calls
    assert all(call[1]["released_pose"] is supported for call in calls)


def test_pose_interpolation_bounds_both_translation_and_rotation():
    start = np.eye(4)
    finish = pose_matrix([.04, .03, .02], Rotation.from_euler("z", .4).as_quat())
    poses = [start, *interpolate_pose(start, finish, .01, .04)]
    for previous, current in zip(poses, poses[1:]):
        assert np.linalg.norm(current[:3, 3] - previous[:3, 3]) <= .010001
        assert Rotation.from_matrix(previous[:3, :3].T @ current[:3, :3]).magnitude() <= .040001
    assert poses[-1] == pytest.approx(finish)


def test_collision_between_endpoints_rejects_entire_route():
    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.config = config()
    model.body_from_observed = {"/World/source": np.eye(4)}
    model.hand_from_tcp = np.eye(4)
    model.joints = lambda: np.zeros(7)
    model.tcp = lambda *_: pose_matrix([0., 0., 1.], [0., 0., 0., 1.])
    model.limits = np.tile([-3., 3.], (7, 1))
    def inverse(_frame, position, *_args, **_kwargs):
        return np.r_[position[0], np.zeros(6)], True
    model.solver = SimpleNamespace(compute_inverse_kinematics=inverse)
    samples = []
    def collide(joints, *_args, **_kwargs):
        samples.append(float(joints[0]))
        if .035 <= joints[0] <= .065:
            raise PhaseMotionError("route_collision", "obstacle between endpoints")
    model._collisions = collide
    goal = pose_matrix([.1, 0., 1.], [0., 0., 0., 1.])
    with pytest.raises(PhaseMotionError, match="between endpoints"):
        model.qualify([(goal, 0., "approach")], "/World/source", np.eye(4), "acquire")
    assert any(.035 <= value <= .065 for value in samples)
    assert max(samples) < .1


def test_dense_collision_sampling_does_not_add_execution_stops():
    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.config = config()
    model.body_from_observed = {"/World/source": np.eye(4)}
    model.hand_from_tcp = np.eye(4)
    model.joints = lambda: np.zeros(7)
    model.tcp = lambda *_: pose_matrix([0., 0., 1.], [0., 0., 0., 1.])
    model.limits = np.tile([-3., 3.], (7, 1))
    model.solver = SimpleNamespace(compute_inverse_kinematics=lambda _frame, p, *_a, **_k:
                                  (np.r_[p[0] * 10., np.zeros(6)], True))
    checks = []
    model._collisions = lambda joints, *_a, **_k: checks.append(joints.copy())
    target = pose_matrix([.02, 0., 1.], [0., 0., 0., 1.])
    coarse = model.qualify([(target, .6, "approach")], "/World/source", np.eye(4), "acquire")
    coarse_count = len(checks)
    checks.clear()
    model.config["joint_step_rad"] /= 10
    dense = model.qualify([(target, .6, "approach")], "/World/source", np.eye(4), "acquire")
    assert len(checks) > coarse_count
    assert dense == coarse
    assert len(dense["steps"]) == 2
    assert dense["steps"][-1]["hold_s"] == .6


def execution_fixture(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "isaacsim.core.utils.types", SimpleNamespace(
        ArticulationAction=lambda **value: SimpleNamespace(**value)))
    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.config = config()
    model.body_from_observed = {"/World/source": np.eye(4)}
    model.dt = .01
    model.profile = SimpleNamespace(object_lift_threshold_m=.04)
    model.joint_indices = list(range(7))
    model.limits = np.tile([-3., 3.], (7, 1))
    positions = np.r_[np.zeros(7), .04, .04]
    commands, artifacts = [], []
    robot = SimpleNamespace()
    robot.get_joint_positions = lambda: positions.copy()
    robot.get_dof_index = lambda name: {"panda_finger_joint1": 7, "panda_finger_joint2": 8}[name]
    robot.apply_action = lambda action: commands.append(action.joint_positions.copy())
    robot.get_articulation_controller = lambda: robot
    world = SimpleNamespace(current_time=0., steps=0, play=lambda: None)
    callbacks = {}
    world.physics_callbacks = callbacks
    world.add_physics_callback = lambda name, callback: callbacks.update({name: callback})
    world.remove_physics_callback = lambda name: callbacks.pop(name)
    def step(**_kwargs):
        for callback in callbacks.values():
            callback(model.dt)
        positions[:] = commands[-1]
        world.current_time += model.dt
        world.steps += 1
    world.step = step
    model.world, model.robot = world, robot
    model.session = SimpleNamespace(current_scene_revision=lambda: "scene-1", resolve=lambda _key: None,
                                    app=SimpleNamespace(is_running=lambda: True))
    body = pose_matrix([.1, 0., .9], [0., 0., 0., 1.])
    tcp = pose_matrix([.1, 0., 1.], [0., 0., 0., 1.])
    model.tcp = lambda *_: tcp.copy()
    model._collisions = lambda *_, **__: None
    model.body_pose = lambda _: body.copy()
    model.body = lambda _: SimpleNamespace(prim_path="/World/source/mesh", get_linear_velocity=lambda: np.zeros(3))
    # The fingers contact another object; this must not establish possession.
    model.sensors = [SimpleNamespace(get_current_frame=lambda: {
        "time": world.current_time, "contacts": [{"body0": "/World/wrong/mesh", "body1": "/World/Franka/finger", "impulse": [1., 0., 0.]}]})] * 2
    def artifact(kind, value):
        artifacts.append((kind, value))
        return "artifact://labutopia/phase-feedback/example.json"
    model._artifact = artifact
    arguments = {"operation": "acquire", "scene_revision": "scene-1", "entity_ref": "entity://source", "phase_route": {
        "operation": "acquire", "scene_revision": "scene-1", "start_joints": np.zeros(7).tolist(),
        "source_path": "/World/source", "original_return_pose": body.tolist(), "tcp_from_object": (np.linalg.inv(tcp) @ body).tolist(),
        "start_object_pose": body.tolist(), "target": {}, "body_from_observed": np.eye(4).tolist(),
        "steps": [{"joints": np.zeros(7).tolist(), "stage": "close", "hold_s": .1,
                   "allow_contact": True, "attached": False, "support_contact": False},
                  {"joints": [.1, 0., 0., 0., 0., 0., 0.], "stage": "lift", "hold_s": .1,
                   "allow_contact": True, "attached": True, "support_contact": False}]}}
    return model, arguments, commands, artifacts


def test_wrong_entity_contact_never_starts_lift(monkeypatch):
    model, arguments, commands, artifacts = execution_fixture(monkeypatch)
    result = model.execute(arguments, Event())
    assert result["failure_code"] == "grasp_not_confirmed"
    assert not result["operation_completed"]
    assert all(command[0] == 0. for command in commands)
    assert artifacts[-1][1]["failure_code"] == "grasp_not_confirmed"
    assert not model.world.physics_callbacks


@pytest.mark.parametrize("final_kind,expected", [("unloaded", True), ("missing", False), ("other", False), ("stale", False)])
def test_contact_window_requires_current_pair_and_current_interval_load(final_kind, expected):
    from isaacsim_lab.phase_motion import GripContactWindow

    world = SimpleNamespace(current_time=1.)
    frame = {"time": 1., "contacts": [{"body0": "/rod", "body1": "/finger", "impulse": [0., 0., .02]}]}
    sensor = SimpleNamespace(get_current_frame=lambda: frame)
    window = GripContactWindow(world, [sensor, sensor], "/rod", 1 / 60)
    window.capture()
    world.current_time += 1 / 960
    frame["time"] = world.current_time
    frame["contacts"][0]["impulse"] = [0., 0., 0.]
    if final_kind == "missing":
        frame["contacts"] = []
    elif final_kind == "other":
        frame["contacts"][0]["body0"] = "/other"
    elif final_kind == "stale":
        frame["time"] -= 1.
    assert window.valid() is expected
    assert window.evidence()["selected_contact_impulse_ns"] == pytest.approx([.02, .02])
    window.begin()
    # The preceding interval must not carry an unloaded grasp forward.
    assert not window.valid()


def test_contact_window_deduplicates_substeps_and_rejects_sampling_errors():
    from isaacsim_lab.phase_motion import GripContactWindow

    world = SimpleNamespace(current_time=1.)
    frame = {"time": 1., "contacts": [{"body0": "/rod", "body1": "/finger", "impulse": [.02, 0., 0.]}]}
    sensor = SimpleNamespace(get_current_frame=lambda: frame)
    window = GripContactWindow(world, [sensor, sensor], "/rod", 1 / 60)
    window.capture()
    window.capture()
    assert window.valid()
    assert window.evidence()["selected_contact_impulse_ns"] == pytest.approx([.02, .02])
    def failed():
        raise RuntimeError("contact provider unavailable")
    sensor.get_current_frame = failed
    window.capture()
    with pytest.raises(PhaseMotionError, match="contact provider unavailable"):
        window.valid()


def test_stir_transport_is_continuous_and_bounded_before_insertion(monkeypatch):
    from isaacsim_lab.phase_motion import smooth_joint_segment

    model, arguments, commands, _ = execution_fixture(monkeypatch)
    route = arguments["phase_route"]
    route["target"] = {"tool_frame": {"tip_offset_m": [0., 0., -.125], "tip_axis_local": [0., 0., -1.]}}
    point = dict(route["steps"][0], attached=True, hold_s=0.)
    goals = [np.full(7, value) for value in (.05, .10, .15)]
    route["steps"] = [dict(point, stage="transport", joints=goal.tolist()) for goal in goals]
    insert = dict(point, stage="insert", joints=goals[-1].tolist())
    route["steps"].append(insert)
    streamed = list(model._stir_execution_points(route, []))
    assert streamed[-1] == insert
    assert all(point["continuous"] and point["attached"] for point in streamed[:-1])
    samples = np.asarray([model.joints(), *[point["joints"] for point in streamed[:-1]]])
    assert samples[-1] == pytest.approx(goals[-1])
    velocity = np.diff(samples, axis=0) / model.dt
    acceleration = np.diff(velocity, axis=0) / model.dt
    assert np.max(np.abs(velocity)) <= model.config["joint_velocity_rad_s"]
    assert np.max(np.abs(acceleration)) <= model.config["joint_acceleration_rad_s2"]
    stopped_frames = sum(len(list(smooth_joint_segment(start, goal, model.dt,
        model.config["joint_velocity_rad_s"], model.config["joint_acceleration_rad_s2"])))
        for start, goal in zip([model.joints(), *goals[:-1]], goals))
    assert len(samples) - 1 < stopped_frames
    assert commands == []


def test_stir_circle_requalification_reads_grip_after_insertion_without_commands(monkeypatch):
    model, arguments, commands, artifacts = execution_fixture(monkeypatch)
    route = arguments["phase_route"]
    route["target"] = {"tool_frame": {"tip_offset_m": [0., 0., -.125], "tip_axis_local": [0., 0., -1.]}}
    point = dict(route["steps"][0], attached=True)
    route["steps"] = [dict(point, stage="insert"), dict(point, stage="process", hold_s=1.)]
    calls = []
    def qualify(targets, source, relation, operation, supported, **kwargs):
        calls.append((targets, relation))
        return {"start_joints": np.zeros(7).tolist(), "steps": [route["steps"][-1]]}
    model.qualify = qualify
    refs = []
    stream = model._stir_execution_points(route, refs)
    assert next(stream)["stage"] == "insert"
    assert not calls
    current_body = model.body_pose("/World/source")
    current_body[0, 3] += .005  # Drift during insertion, after the original preparation.
    model.body_pose = lambda _: current_body.copy()
    assert list(stream)
    target, relation = calls[0][0][0][0], calls[0][1]
    expected = model.tcp() @ np.asarray(route["tcp_from_object"])
    actual = target @ relation
    tip = np.array([0., 0., -.125])
    assert actual[:3, 3] + actual[:3, :3] @ tip == pytest.approx(expected[:3, 3] + expected[:3, :3] @ tip)
    assert relation == pytest.approx(np.linalg.inv(model.tcp()) @ current_body)
    assert commands == []
    assert artifacts[-1][0] == "readiness"
    assert refs


def test_tool_ik_reaches_tip_and_axis_when_full_axial_angle_is_unreachable():
    from isaacsim_lab.phase_motion import local_inverse_kinematics, local_tool_inverse_kinematics

    def forward(joints):
        return pose_matrix(np.array([0., 0., 1.]) + joints[:3], Rotation.from_rotvec([joints[3], joints[4], 0.]).as_quat())
    target = pose_matrix([.2, .1, 1.], Rotation.from_euler("z", .7).as_quat())
    limits = np.tile([-.5, .5], (7, 1))
    tool = {"tip_offset_m": [0., 0., -.125], "tip_axis_local": [0., 0., -1.]}
    _, full = local_inverse_kinematics(forward, target, np.zeros(7), limits, .002)
    assert not full
    joints, valid = local_tool_inverse_kinematics(forward, target, np.eye(4), tool, np.zeros(7), limits, .002)
    assert valid
    actual = forward(joints)
    tip, axis = np.asarray(tool["tip_offset_m"]), np.asarray(tool["tip_axis_local"])
    assert actual[:3, 3] + actual[:3, :3] @ tip == pytest.approx([.2, .1, .875], abs=.002)
    assert actual[:3, :3] @ axis == pytest.approx([0., 0., -1.], abs=.002)


def test_lift_contact_uses_measured_grasp_pose_and_preserves_return_target(monkeypatch):
    model, arguments, _, _ = execution_fixture(monkeypatch)
    original = deepcopy(arguments["phase_route"]["original_return_pose"])
    def tcp(joints=None):
        joints = model.robot.get_joint_positions() if joints is None else joints
        shift = .012 if model.world.steps else 0.
        return pose_matrix([.1 + shift, 0., 1. + joints[0]], [0., 0., 0., 1.])
    model.tcp = tcp
    def body_pose(_source):
        pose = tcp()
        pose[2, 3] -= .1
        return pose
    model.body_pose = body_pose
    model.sensors = [SimpleNamespace(get_current_frame=lambda: {
        "time": model.world.current_time,
        "contacts": [{"body0": "/World/source/mesh", "body1": "/World/Franka/finger", "impulse": [1., 0., 0.]}]})] * 2
    contact_checks = []
    def collisions(joints, _source, _contact, attached, relation, support, **_kwargs):
        if attached:
            height = (tcp(joints) @ relation)[2, 3] - .9
            contact_checks.append((height, support))
    model._collisions = collisions
    result = model.execute(arguments, Event())
    assert result["operation_completed"]
    assert any(support for height, support in contact_checks if height < .008)
    assert all(not support for height, support in contact_checks if height > .008)
    assert arguments["phase_route"]["original_return_pose"] == original
    assert result["measurements"]["return_error_m"] == pytest.approx(np.hypot(.012, .1))


def test_cylindrical_grasp_axis_allows_roll_but_rejects_tilt_and_translation():
    from isaacsim_lab.phase_motion import grasp_pose_errors

    reference = np.eye(4)
    rolled = pose_matrix([0., 0., 0.], Rotation.from_euler("z", .5).as_quat())
    assert grasp_pose_errors(reference, rolled)[1] == pytest.approx(.5)
    assert grasp_pose_errors(reference, rolled, [0., 0., 1.]) == pytest.approx((0., 0.))
    tilted = pose_matrix([0., 0., 0.], Rotation.from_euler("x", .081).as_quat())
    assert grasp_pose_errors(reference, tilted, [0., 0., 1.])[1] > .08
    rolled[2, 3] = .009
    assert grasp_pose_errors(reference, rolled, [0., 0., 1.])[0] > .008


@pytest.mark.parametrize("axial", [False, True])
def test_return_axial_freedom_is_limited_to_declared_fixture(monkeypatch, axial):
    model, arguments, _, _ = execution_fixture(monkeypatch)
    arguments["operation"] = arguments["phase_route"]["operation"] = "place"
    route = arguments["phase_route"]
    route["target"] = {"tool_frame": {"tip_axis_local": [0., 0., 1.]}}
    route["steps"] = [dict(route["steps"][0], stage="retreat")]
    current = pose_matrix([.1, 0., .9], Rotation.from_euler("z", .4).as_quat())
    route["start_object_pose"] = current.tolist()
    model.body_pose = lambda _: current.copy()
    model.config["axial_grip_paths"] = ["/World/source"] if axial else []
    result = model.execute(arguments, Event())
    assert result["operation_completed"] is axial
    assert result["measurements"]["full_return_rotation_error_rad"] == pytest.approx(.4)
    assert result["measurements"]["return_rotation_error_rad"] == pytest.approx(0. if axial else .4)


def test_cancel_before_first_step_issues_no_command(monkeypatch):
    model, arguments, commands, _ = execution_fixture(monkeypatch)
    cancel = Event()
    cancel.set()
    result = model.execute(arguments, cancel)
    assert result["status"] == "cancelled"
    assert result["world_change_started"] is False
    assert commands == []
    assert model.world.steps == 0


def test_unexpected_execution_failure_keeps_partial_evidence_and_unknown(monkeypatch):
    model, arguments, commands, artifacts = execution_fixture(monkeypatch)
    def fail(**_kwargs):
        raise RuntimeError("plant connection lost")
    model.world.step = fail
    result = model.execute(arguments, Event())
    assert result["status"] == "unknown"
    assert result["outcome_known"] is False
    assert result["world_change_started"] is True
    assert result["artifact_refs"]
    assert artifacts[-1][1]["error"] == "plant connection lost"
    assert all(command[0] == 0. for command in commands)


def test_new_obstacle_stops_before_first_command(monkeypatch):
    model, arguments, commands, artifacts = execution_fixture(monkeypatch)
    def blocked(*_args, **_kwargs):
        raise PhaseMotionError("route_collision", "obstacle moved into the route")
    model._collisions = blocked
    result = model.execute(arguments, Event())
    assert result["failure_code"] == "route_collision"
    assert not result["world_change_started"]
    assert commands == []
    assert model.world.steps == 0
    assert artifacts[-1][1]["failure_code"] == "route_collision"


def test_changed_object_is_rejected_before_any_command(monkeypatch):
    model, arguments, commands, _ = execution_fixture(monkeypatch)
    arguments["phase_route"]["start_object_pose"][0][3] += .03
    with pytest.raises(PhaseMotionError) as error:
        model.execute(arguments, Event())
    assert error.value.code == "object_state_changed"
    assert commands == []
    assert model.world.steps == 0


def test_terminal_measurement_failure_retains_evidence(monkeypatch):
    model, arguments, commands, artifacts = execution_fixture(monkeypatch)
    original = model.body_pose
    calls = 0
    def fail_terminal(path):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise RuntimeError("terminal sensor unavailable")
        return original(path)
    model.body_pose = fail_terminal
    cancel = Event()
    cancel.set()
    result = model.execute(arguments, cancel)
    assert result["status"] == "unknown"
    assert not result["world_change_started"]
    assert result["artifact_refs"]
    assert artifacts[-1][1]["original_failure_code"] == "cancelled"
    assert commands == []


def test_failed_phase_keeps_video_without_extra_physics_steps(monkeypatch, tmp_path):
    pytest.importorskip("cv2")
    model, arguments, _, _ = execution_fixture(monkeypatch)
    model.artifact_root = tmp_path
    model.session.resolve = lambda _key: {"sensor://front": SimpleNamespace(get_rgba=lambda: np.zeros((32, 32, 4), dtype=np.uint8))}
    result = model.execute(arguments, Event())
    assert result["failure_code"] == "grasp_not_confirmed"
    assert result["video_frame_count"] == model.world.steps
    video_ref = next(ref for ref in result["artifact_refs"] if ref.endswith(".mp4"))
    assert (tmp_path / video_ref.removeprefix("artifact://labutopia/")).stat().st_size > 0


def test_measured_fingers_keep_gap_and_bound_opening_uncertainty():
    from itertools import product

    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.config = config()
    model.body_from_observed = {"/World/source": np.eye(4)}
    model.robot = SimpleNamespace(get_joint_positions=lambda: np.array([.013, .013]),
                                  get_dof_index=lambda name: int(name[-1]) - 1)
    corners = np.array(list(product((-.01, .01), (0., .02), (0., .05))))
    second = pose_matrix([0., 0., 0.], Rotation.from_euler("z", np.pi).as_quat())
    model.finger_geometry = [(1, corners, np.eye(4), np.eye(4), 1, (0., .04)),
                             (2, corners, second, np.eye(4), 1, (0., .04))]
    first, second = list(model.finger_boxes(measured=True))
    assert first[0][1] == pytest.approx(.011)
    assert second[1][1] == pytest.approx(-.011)
    assert first[1][1] < list(model.finger_boxes())[0][1][1]


def test_local_ik_finds_nearby_solution_and_rejects_unreachable_target():
    from isaacsim_lab.phase_motion import local_inverse_kinematics

    def forward(q):
        return pose_matrix(q[:3], Rotation.from_rotvec(q[3:]).as_quat())
    limits = np.tile([-.5, .5], (6, 1))
    target = forward(np.array([.1, -.1, .2, .05, .1, -.1]))
    q, ok = local_inverse_kinematics(forward, target, np.zeros(6), limits, .002)
    assert ok
    assert forward(q) == pytest.approx(target, abs=.002)
    target[0, 3] = 2.
    _, ok = local_inverse_kinematics(forward, target, np.zeros(6), limits, .002)
    assert not ok


def test_measured_collision_stops_before_next_command(monkeypatch):
    model, arguments, commands, artifacts = execution_fixture(monkeypatch)
    read_positions = model.robot.get_joint_positions

    def measured_positions():
        positions = read_positions()
        if model.world.steps:
            # Drift is within tracking tolerance but crosses an obstacle.
            positions[0] += .005
        return positions

    model.robot.get_joint_positions = measured_positions
    def collision(joints, *_args, **_kwargs):
        if joints[0] > .004:
            raise PhaseMotionError("route_collision", "measured arm touches obstacle")
    model._collisions = collision
    result = model.execute(arguments, Event())
    assert result["failure_code"] == "route_collision"
    assert result["world_change_started"] is True
    assert result["operation_completed"] is False
    assert len(commands) == 2  # First command and terminal hold only.
    assert "measured arm" in artifacts[-1][1]["failure_detail"]


def test_stir_settlement_preserves_requested_direction(monkeypatch):
    from pick_place_workflow import cycle_protocol

    model, arguments, _, _ = execution_fixture(monkeypatch)
    arguments["operation"] = arguments["phase_route"]["operation"] = "stir"
    arguments["parameters"] = {"direction": "cw"}
    route = arguments["phase_route"]
    route["target"] = {"tool_frame": {"tip_offset_m": [0, 0, 0]},
                       "process_frame": {"origin_m": [0, 0, 0], "axis": [0, 0, 1]}}
    route["steps"] = [{**route["steps"][0], "stage": "process", "attached": True, "hold_s": 0}]
    model.sensors = [SimpleNamespace(get_current_frame=lambda: {
        "time": model.world.current_time, "contacts": [{"body0": "/World/source/mesh",
        "body1": "/World/Franka/finger", "impulse": [1, 0, 0]}]})] * 2
    model.profile.evaluation_profile = lambda: {}
    def evaluate(operation, samples, parameters, _profile):
        assert operation == "stir_cycle"
        assert samples and parameters["direction"] == "cw"
        return {"process_completed": True}
    monkeypatch.setattr(cycle_protocol, "evaluate_process_feedback", evaluate)
    assert model.execute(arguments, Event())["operation_completed"] is True


def test_pour_tracks_original_object_pose_after_measured_grip_drift(monkeypatch):
    from pick_place_workflow import cycle_protocol

    model, arguments, commands, _ = execution_fixture(monkeypatch)
    model.joints = lambda: model.robot.get_joint_positions()[:7]
    def tcp(joints=None):
        joints = model.joints() if joints is None else joints
        return pose_matrix(np.array([.1, 0., 1.]) + joints[:3],
                           Rotation.from_rotvec(joints[3:6]).as_quat())
    model.tcp = tcp
    nominal_relation = np.asarray(arguments['phase_route']['tcp_from_object'])
    drift = pose_matrix([.003, 0., 0.], Rotation.from_euler('y', .015).as_quat())
    model.body_pose = lambda _: tcp() @ (drift if model.world.steps else np.eye(4)) @ nominal_relation
    model.sensors = [SimpleNamespace(get_current_frame=lambda: {
        'time': model.world.current_time, 'contacts': [{'body0': '/World/source/mesh',
        'body1': '/World/Franka/finger', 'impulse': [1, 0, 0]}]})] * 2
    arguments['operation'] = arguments['phase_route']['operation'] = 'pour'
    arguments['parameters'] = {'tilt_rad': 1.3, 'hold_s': .1}
    route = arguments['phase_route']
    route['target'] = {'tool_frame': {'tip_offset_m': [0., 0., .1], 'tip_axis_local': [0., 0., 1.]},
                       'process_frame': {'origin_m': [.15, 0., 1.], 'axis': [0., 0., 1.]}}
    route['steps'] = [dict(route['steps'][0], stage=stage, attached=True, hold_s=0.,
                           joints=[x, 0., 0., 0., 0., 0., 0.])
                       for stage, x in [('transport', .01), ('process', .05), ('exit', 0.)]]
    model.profile.alignment_tolerance_m = .05
    model.profile.evaluation_profile = lambda: {}
    monkeypatch.setattr(cycle_protocol, 'evaluate_process_feedback', lambda *_:
                        {'process_completed': True, 'qualified_tilt_hold_s': .1})
    result = model.execute(arguments, Event())
    assert result['operation_completed'] is True
    assert result['measurements']['final_tool_tip_error_m'] < .002
    assert result['measurements']['final_tool_axis_error_rad'] < .002
    assert commands[-1][4] == pytest.approx(-.015, abs=.002)
    assert route['tcp_from_object'] == nominal_relation.tolist()


def test_grasp_error_is_independent_of_object_coordinate_origin():
    from isaacsim_lab.phase_motion import grasp_pose_errors

    reference = pose_matrix([.01, .02, .15], Rotation.from_euler('z', .4).as_quat())
    motion = pose_matrix([.003, 0, 0], Rotation.from_euler('x', .05).as_quat())
    current = motion @ reference
    reframe = pose_matrix([2, 1, -.7], Rotation.from_euler('xyz', [.3, -.2, .1]).as_quat())
    assert grasp_pose_errors(reference, current) == pytest.approx((.003, .05))
    assert grasp_pose_errors(reference @ reframe, current @ reframe) == pytest.approx((.003, .05))
    # The old body-origin displacement changes despite identical physical motion.
    assert np.linalg.norm((current @ reframe)[:3, 3] - (reference @ reframe)[:3, 3]) > .008


@pytest.mark.parametrize('translation,angle,index,threshold', [
    (.009, .01, 0, .008), (0., .081, 1, .08),
])
def test_grasp_anchor_still_rejects_true_translation_and_rotation(translation, angle, index, threshold):
    from isaacsim_lab.phase_motion import grasp_pose_errors

    reference = pose_matrix([0, 0, .15], [0, 0, 0, 1])
    motion = pose_matrix([translation, 0, 0], Rotation.from_euler('x', angle).as_quat())
    assert grasp_pose_errors(reference, motion @ reference)[index] > threshold


def test_observed_frame_tracks_body_displacement_without_using_body_origin_as_tool_origin():
    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    captured_body = pose_matrix([3., 2., 1.], Rotation.from_euler('z', .6).as_quat())
    observed_frame = pose_matrix([.1, .2, 1.1], [0, 0, 0, 1])
    body_from_observed = np.linalg.inv(captured_body) @ observed_frame
    motion = pose_matrix([.01, .02, .04], Rotation.from_euler('x', .2).as_quat())
    model.body_from_observed = {'object': body_from_observed}
    model.body_pose = lambda _: motion @ captured_body
    assert model.observed_pose('object') == pytest.approx(motion @ observed_frame)
