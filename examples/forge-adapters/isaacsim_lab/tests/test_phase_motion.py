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
    acquire_failure_summary,
    acquire_route_waypoints,
    acquire_staging_corridors,
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


@pytest.mark.parametrize("kind", ["sphere", "finger", "self"])
def test_collision_model_receipt_preserves_exact_queried_geometry(monkeypatch, kind):
    import json
    import sys
    import types

    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.config = config()
    model.robot = SimpleNamespace(prim_path="/robot")
    model.hand_from_tcp = np.eye(4)
    model.tcp = lambda _joints: pose_matrix([0., 0., 1.], [0., 0., 0., 1.])
    model.solver = SimpleNamespace(compute_forward_kinematics=lambda _link, _q: (np.array([0., 0., 1.]), np.eye(3)))
    model.spheres = [] if kind == "finger" else [
        {link: [{"center": [0., 0., 0.], "radius": .02}]}
        for link in (["panda_link1", "panda_link2", "panda_link5"] if kind == "self" else ["panda_hand"])]
    model.finger_boxes = lambda **_kw: [(np.array([-.01, -.02, -.03]), np.array([.01, .02, .03]))] if kind == "finger" else []
    carb = types.ModuleType("carb")
    carb.Float3 = carb.Float4 = lambda *args: tuple(args)
    monkeypatch.setitem(sys.modules, "carb", carb)
    physx = types.ModuleType("omni.physx")

    def overlap(*args):
        if kind != "self":
            args[-2](SimpleNamespace(collision="/table/mesh"))

    physx.get_physx_scene_query_interface = lambda: SimpleNamespace(overlap_box=overlap, overlap_sphere=overlap)
    monkeypatch.setitem(sys.modules, "omni.physx", physx)
    with pytest.raises(PhaseMotionError) as caught:
        model._collisions(np.zeros(7), "/source", False, False, np.eye(4))
    diagnostic = caught.value.diagnostics
    assert caught.value.code == ("self_collision" if kind == "self" else "route_collision")
    assert diagnostic["evidence_kind"] == "collision_model_overlap"
    assert diagnostic["checked_joints"] == [0.] * 7
    assert diagnostic["checked_tcp"][2][3] == 1.
    assert diagnostic["collision_margin_m"] == model.config["collision_margin_m"]
    assert json.loads(json.dumps(diagnostic)) == diagnostic
    if kind == "sphere":
        assert diagnostic["radius_m"] == pytest.approx(.023)
    elif kind == "finger":
        assert diagnostic["half_extents_m"] == pytest.approx([.013, .023, .033])
        assert diagnostic["finger_opening_mode"] == "full_travel_sweep"
    else:
        assert diagnostic["other_link"] == "panda_link5"


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
@pytest.mark.parametrize("radius,depth,turns,duration", [
    (.009, .04, 2., 4.),
    (.018, .04, 2., 4.),
    (.009, .055, 2., 4.),
    (.009, .04, 1., 4.),
    (.009, .04, 2., 7.),
    (.025, .06, 2., 4.),
])
def test_absolute_stir_circle_does_not_accumulate_positions(direction, sign, radius, depth, turns, duration):
    body = pose_matrix([.1, -.1, 1.], [0., 0., 0., 1.])
    tcp = pose_matrix([.1, -.1, 1.1], [0., 0., 0., 1.])
    relation = np.linalg.inv(tcp) @ body
    tip = np.array([0., 0., -.1])
    target = {"process_frame": {"origin_m": [.3, .05, .88], "axis": [0., 0., 1.]},
              "tool_frame": {"tip_offset_m": tip.tolist(), "tip_axis_local": [0., 0., -1.]}}
    before = deepcopy(target)
    points = process_waypoints("stir", {"radius_m": radius, "depth_m": depth, "turns": turns, "duration_s": duration, "direction": direction},
                               tcp, body, relation, target, config())
    actual = []
    for pose, _, stage in points:
        if stage == "process":
            placed = pose @ relation
            actual.append(placed[:3, 3] + placed[:3, :3] @ tip)
    actual = np.array(actual)
    assert np.linalg.norm(actual[:, :2] - [.3, .05], axis=1) == pytest.approx(np.full(len(actual), radius))
    assert actual[:, 2] == pytest.approx(np.full(len(actual), .88 - depth))
    assert target == before
    assert points[-1][2] == "exit"
    offsets = actual[:, :2] - [.3, .05]
    angles = np.unwrap(np.r_[np.pi / 2, np.arctan2(offsets[:, 1], offsets[:, 0])])
    assert angles[-1] - angles[0] == pytest.approx(sign * 2 * np.pi * (turns + config()["stir_entry_reserve_turns"]))
    assert sum(seconds for _, seconds, stage in points if stage == "process") == pytest.approx(
        duration * (turns + config()["stir_entry_reserve_turns"]) / turns)


@pytest.mark.parametrize("tilt,hold", [(.65, .6), (1.2, .6), (.65, 1.8), (1.5, .6)])
def test_pour_parameters_control_measured_body_tilt_and_hold(tilt, hold):
    body = pose_matrix([.1, -.1, 1.], Rotation.from_euler("z", .3).as_quat())
    tcp = pose_matrix([.13, -.08, 1.1], Rotation.from_euler("xy", [.2, -.1]).as_quat())
    relation = np.linalg.inv(tcp) @ body
    tip = np.array([.02, 0., .15])
    target = {"process_frame": {"origin_m": [.3, .05, .88], "axis": [0., 0., 1.]},
              "tool_frame": {"tip_offset_m": tip.tolist()}}
    points = process_waypoints("pour", {"tilt_rad": tilt, "hold_s": hold},
                               tcp, body, relation, target, config())
    process = [(pose @ relation, seconds) for pose, seconds, stage in points if stage == "process"]
    assert len(process) == 1
    placed, seconds = process[0]
    assert placed[:3, 3] + placed[:3, :3] @ tip == pytest.approx(
        [.3, .05, .88 + config()["pour_lip_clearance_m"]])
    upright = points[-1][0] @ relation
    assert Rotation.from_matrix(placed[:3, :3] @ upright[:3, :3].T).magnitude() == pytest.approx(tilt)
    assert seconds == pytest.approx(hold + config()["settle_s"])
    assert upright[:3, 2] == pytest.approx([0., 0., 1.])


def test_task_conditioned_pour_direction_controls_tilt_toward_destination():
    direction = np.asarray([.6, .8, 0.])
    body = np.eye(4)
    tcp = np.eye(4)
    relation = np.eye(4)
    target = {
        "process_frame": {"origin_m": [.3, .05, .88], "axis": [0., 0., 1.],
                          "pour_direction": direction.tolist()},
        "tool_frame": {"tip_offset_m": [.02, 0., .15]},
    }
    points = process_waypoints(
        "pour", {"tilt_rad": .87, "hold_s": .6}, tcp, body, relation, target, config(),
    )
    approach = points[0][0] @ relation
    tip = np.asarray(target["tool_frame"]["tip_offset_m"])
    process = next(pose @ relation for pose, _, stage in points if stage == "process")
    expected_approach = (np.asarray([.3, .05, .88]) + np.asarray([0., 0., 1.])
                         * config()["process_clearance_m"] - direction * config()["process_clearance_m"])
    assert approach[:3, 3] + approach[:3, :3] @ tip == pytest.approx(expected_approach)
    assert float(np.dot(process[:3, 2], direction)) == pytest.approx(np.sin(.87))


@pytest.mark.parametrize("operation,parameters,code", [
    ("pour", {"tilt_rad": 1.51, "hold_s": .6}, "tilt_limit_exceeded"),
    ("stir", {"radius_m": .026, "depth_m": .04, "turns": 2., "duration_s": 4., "direction": "ccw"},
     "stir_geometry_limit_exceeded"),
    ("stir", {"radius_m": .009, "depth_m": .061, "turns": 2., "duration_s": 4., "direction": "cw"},
     "stir_geometry_limit_exceeded"),
])
def test_process_parameters_exceeding_deployment_bounds_are_rejected(operation, parameters, code):
    target = {"process_frame": {"origin_m": [.3, .05, .88], "axis": [0., 0., 1.]},
              "tool_frame": {"tip_offset_m": [0., 0., -.1], "tip_axis_local": [0., 0., -1.]}}
    with pytest.raises(PhaseMotionError) as error:
        process_waypoints(operation, parameters, np.eye(4), np.eye(4), np.eye(4), target, config())
    assert error.value.code == code


def test_grasp_aperture_uses_composed_finger_limits_and_rejects_oversized_candidate():
    from isaacsim_lab.phase_motion import IsaacPhaseMotion

    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.finger_geometry = [
        (1, None, None, None, 0, (0.0, 0.04)),
        (2, None, None, None, 0, (0.0, 0.04)),
    ]

    assert model.maximum_gripper_opening_m == pytest.approx(0.08)
    assert model.validate_grasp_aperture({
        "grasp_geometry": {"width_m": 0.077},
    }) == {
        "required_width_m": pytest.approx(0.077),
        "maximum_opening_m": pytest.approx(0.08),
    }
    with pytest.raises(PhaseMotionError, match="composed Franka limit") as captured:
        model.validate_grasp_aperture({"grasp_geometry": {"width_m": 0.1}})
    assert captured.value.code == "gripper_aperture_exceeded"


def test_acquire_preparation_searches_clearances_and_selects_admissible_route():
    model = object.__new__(IsaacPhaseMotion)
    model.config = {
        "approach_distance_m": .12,
        "acquire_transit_clearance_candidates_m": [.04, .08, .12],
        "acquire_transport_orientation_candidates_xyzw": [[1., 0., 0., 0.]],
        "acquire_axial_symmetry_angles_rad": [0., np.pi / 2],
        "lift_distance_m": .10,
        "settle_s": .6,
    }
    model.validate_grasp_aperture = lambda _target: None
    current = np.eye(4)
    current[:3, 3] = [-.45, 0., 1.0]
    body = np.eye(4)
    body[:3, 3] = [-.27, -.36, .82]
    model.tcp = lambda: current.copy()
    model.observed_pose = lambda _source: body.copy()
    model.bind_observed_model = lambda *_args: (body.copy(), np.eye(4))
    model.body_pose = lambda _path: np.eye(4)
    model._artifact = lambda *_args: "artifact://readiness/test.json"
    captured = []

    def qualify(waypoints, *_args, **_kwargs):
        captured.append(waypoints)
        clearance = waypoints[1][0][2, 3] - 1.0
        if clearance == pytest.approx(.04):
            raise PhaseMotionError("route_collision", "low route intersects scene geometry")
        travel = .2 if clearance == pytest.approx(.08) else .4
        return {"start_joints": [0.] * 7,
                "steps": [{"joints": [travel] + [0.] * 6, "stage": "lift"}]}

    model.qualify = qualify
    target = {
        "world_from_control": {
            "translation_m": [0., 0., 0.],
            "orientation_xyzw": [0., 0., 0., 1.],
        },
        "entity_prim_path": "/World/R03/Model",
        "destination_prim_path": "/World/BEAKER/Model",
        "object_pose": {
            "position_m": [-.27, -.36, .82],
            "orientation_xyzw": [0., 0., 0., 1.],
        },
        "grasp_frame": {
            "position_m": [-.27, -.36, .86],
            "orientation_xyzw": [0., 0., 0., 1.],
        },
        "approach_direction": {"vector": [0., -1., 0.]},
        "destination_pose": {
            "position_m": [-.08, 0., .8],
            "orientation_xyzw": [0., 0., 0., 1.],
        },
        "return_pose": {
            "position_m": [-.27, -.36, .82],
            "orientation_xyzw": [0., 0., 0., 1.],
        },
    }
    arguments = {
        "manipulation_target": target,
        "observation_model": {},
        "scene_revision": "scene",
    }

    route, _evidence = model.prepare(arguments)

    assert len(captured) == 3
    selected = captured[1]
    stages = [stage for _pose, _hold, stage in selected]
    assert stages[:6] == [
        "open", "transit_raise", "transit_orient", "transit_cross", "staging_reorient", "approach",
    ]
    raised, transport_ready, transported, staged, pre = [selected[index][0] for index in (1, 2, 3, 4, 5)]
    assert raised[:2, 3] == pytest.approx(current[:2, 3])
    assert transport_ready[:3, 3] == pytest.approx(raised[:3, 3])
    assert Rotation.from_matrix(transport_ready[:3, :3]).as_quat() == pytest.approx([1., 0., 0., 0.])
    assert transported[:2, 3] == pytest.approx(pre[:2, 3])
    assert transported[:3, :3] == pytest.approx(transport_ready[:3, :3])
    assert staged[:2, 3] == pytest.approx(pre[:2, 3])
    assert staged[:3, :3] == pytest.approx(pre[:3, :3])
    assert raised[2, 3] == pytest.approx(1.08)
    assert staged[2, 3] == pytest.approx(1.08)
    assert pre[:3, 3] == pytest.approx([-.27, -.24, .86])
    assert route["operation"] == "acquire"
    assert route["acquire_transit_clearance_m"] == pytest.approx(.08)
    assert route["acquire_approach_distance_m"] == pytest.approx(.12)
    assert route["acquire_staging_backoff_m"] == pytest.approx(0.)
    assert route["acquire_staging_tangential_offset_m"] == pytest.approx(0.)


def test_acquire_preparation_preserves_zero_motion_when_all_clearances_fail():
    model = object.__new__(IsaacPhaseMotion)
    model.config = {
        "approach_distance_m": .12,
        "acquire_transit_clearance_candidates_m": [.04, .08],
        "acquire_transport_orientation_candidates_xyzw": [[1., 0., 0., 0.]],
        "acquire_axial_symmetry_angles_rad": [0.],
        "lift_distance_m": .10,
        "settle_s": .6,
    }
    model.validate_grasp_aperture = lambda _target: None
    model.tcp = lambda: np.eye(4)
    model.observed_pose = lambda _source: np.eye(4)
    model.bind_observed_model = lambda *_args: (np.eye(4), np.eye(4))
    model.body_pose = lambda _path: np.eye(4)
    attempts = []

    def reject(waypoints, *_args, **_kwargs):
        attempts.append(waypoints[1][0][2, 3])
        code = "self_collision" if len(attempts) == 1 else "route_collision"
        raise PhaseMotionError(code, "candidate route rejected")

    model.qualify = reject
    target = {
        "world_from_control": {"translation_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
        "entity_prim_path": "/World/R03/Model",
        "destination_prim_path": "/World/BEAKER/Model",
        "object_pose": {"position_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
        "grasp_frame": {"position_m": [0., 0., .2], "orientation_xyzw": [0., 0., 0., 1.]},
        "approach_direction": {"vector": [0., 0., 1.]},
        "destination_pose": {"position_m": [.2, 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
        "return_pose": {"position_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
    }

    with pytest.raises(PhaseMotionError) as captured:
        model.prepare({"manipulation_target": target, "observation_model": {}, "scene_revision": "scene"})

    assert captured.value.code == "route_unavailable"
    assert attempts == pytest.approx([.24, .28])
    assert "clearance=0.04" in str(captured.value)
    assert "clearance=0.08" in str(captured.value)
    assert "self_collision" in str(captured.value)
    assert "route_collision" in str(captured.value)


def test_acquire_staging_corridors_falls_back_to_legacy_approach_distance():
    assert acquire_staging_corridors({"approach_distance_m": .12}) == ((.12, 0., 0.),)


def test_acquire_staging_corridors_deduplicates_without_reordering():
    first = {"approach_distance_m": .12, "staging_backoff_m": 0., "tangential_offset_m": 0.}
    second = {"approach_distance_m": .18, "staging_backoff_m": .08, "tangential_offset_m": -.06}
    assert acquire_staging_corridors({
        "acquire_staging_corridor_candidates": [first, second, first],
    }) == ((.12, 0., 0.), (.18, .08, -.06))


@pytest.mark.parametrize("values", [
    [],
    "corridor",
    [None],
    [{"approach_distance_m": 0., "staging_backoff_m": 0., "tangential_offset_m": 0.}],
    [{"approach_distance_m": .12, "staging_backoff_m": -.01, "tangential_offset_m": 0.}],
    [{"approach_distance_m": True, "staging_backoff_m": 0., "tangential_offset_m": 0.}],
    [{"approach_distance_m": .12, "staging_backoff_m": "0", "tangential_offset_m": 0.}],
    [{"approach_distance_m": .12, "staging_backoff_m": 0., "tangential_offset_m": float("nan")}],
])
def test_acquire_staging_corridors_reject_invalid_configuration(values):
    with pytest.raises(PhaseMotionError) as captured:
        acquire_staging_corridors({"acquire_staging_corridor_candidates": values})
    assert captured.value.code == "invalid_motion_configuration"


def test_acquire_route_waypoints_apply_backoff_and_tangential_offset_before_approach():
    tcp = pose_matrix([-.4, 0., 1.], [0., 0., 0., 1.])
    desired = pose_matrix([.4, .2, .8], [0., 0., 0., 1.])
    waypoints = acquire_route_waypoints(
        tcp,
        desired,
        np.asarray([0., -1., 0.]),
        .1,
        [1., 0., 0., 0.],
        (.18, .08, .06),
        {"lift_distance_m": .1, "settle_s": .6},
    )

    transported, staged, pre, grasp = [waypoints[index][0] for index in (3, 4, 5, 6)]
    assert pre[:3, 3] == pytest.approx([.4, .38, .8])
    assert staged[:3, 3] == pytest.approx([.46, .46, 1.1])
    assert transported[:2, 3] == pytest.approx(staged[:2, 3])
    assert grasp == pytest.approx(desired)


def test_acquire_route_waypoints_use_world_x_tangent_for_vertical_approach():
    desired = pose_matrix([.2, -.1, .8], [0., 0., 0., 1.])
    waypoints = acquire_route_waypoints(
        np.eye(4),
        desired,
        np.asarray([0., 0., 1.]),
        .1,
        [0., 0., 0., 1.],
        (.18, .08, .05),
        {"lift_distance_m": .1, "settle_s": .6},
    )

    staged, pre = waypoints[4][0], waypoints[5][0]
    assert pre[:3, 3] == pytest.approx([.2, -.1, .62])
    assert staged[:2, 3] == pytest.approx([.25, -.1])
    assert staged[2, 3] == pytest.approx(.9)


@pytest.mark.parametrize("approach", [[0., 0., 0.], [0., float("nan"), 1.]])
def test_acquire_route_waypoints_reject_invalid_approach(approach):
    with pytest.raises(PhaseMotionError) as captured:
        acquire_route_waypoints(
            np.eye(4),
            np.eye(4),
            np.asarray(approach),
            .1,
            [0., 0., 0., 1.],
            (.12, 0., 0.),
            {"lift_distance_m": .1, "settle_s": .6},
        )
    assert captured.value.code == "invalid_grasp_approach"


def test_acquire_preparation_qualifies_each_corridor_and_selects_offset_route():
    model = object.__new__(IsaacPhaseMotion)
    model.config = {
        "approach_distance_m": .12,
        "acquire_staging_corridor_candidates": [
            {"approach_distance_m": .12, "staging_backoff_m": 0., "tangential_offset_m": 0.},
            {"approach_distance_m": .18, "staging_backoff_m": .08, "tangential_offset_m": .06},
        ],
        "acquire_transit_clearance_candidates_m": [.04],
        "acquire_transport_orientation_candidates_xyzw": [[1., 0., 0., 0.]],
        "acquire_axial_symmetry_angles_rad": [0.],
        "lift_distance_m": .10,
        "settle_s": .6,
    }
    model.validate_grasp_aperture = lambda _target: None
    current = pose_matrix([-.4, 0., 1.], [0., 0., 0., 1.])
    body = pose_matrix([0., 0., .8], [0., 0., 0., 1.])
    model.tcp = lambda: current.copy()
    model.observed_pose = lambda _source: body.copy()
    model.bind_observed_model = lambda *_args: (body.copy(), np.eye(4))
    model.body_pose = lambda _path: np.eye(4)
    model._artifact = lambda *_args: "artifact://readiness/test.json"
    staged_positions = []

    def qualify(waypoints, *_args, **_kwargs):
        staged_positions.append(waypoints[4][0][:3, 3].copy())
        if waypoints[4][0][0, 3] == pytest.approx(0.):
            raise PhaseMotionError("route_collision", "direct corridor is blocked")
        return {"start_joints": [0.] * 7,
                "steps": [{"joints": [.2] + [0.] * 6, "stage": "lift"}]}

    model.qualify = qualify
    target = {
        "world_from_control": {"translation_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
        "entity_prim_path": "/World/source/Model",
        "destination_prim_path": "/World/destination/Model",
        "object_pose": {"position_m": [0., 0., .8], "orientation_xyzw": [0., 0., 0., 1.]},
        "grasp_frame": {"position_m": [0., 0., .9], "orientation_xyzw": [0., 0., 0., 1.]},
        "approach_direction": {"vector": [0., -1., 0.]},
        "destination_pose": {"position_m": [.2, 0., .8], "orientation_xyzw": [0., 0., 0., 1.]},
        "return_pose": {"position_m": [0., 0., .8], "orientation_xyzw": [0., 0., 0., 1.]},
    }

    route, _evidence = model.prepare({
        "manipulation_target": target,
        "observation_model": {},
        "scene_revision": "scene",
    })

    assert len(staged_positions) == 2
    assert staged_positions[0][:2] == pytest.approx([0., .12])
    assert staged_positions[1][:2] == pytest.approx([.06, .26])
    assert route["acquire_approach_distance_m"] == pytest.approx(.18)
    assert route["acquire_staging_backoff_m"] == pytest.approx(.08)
    assert route["acquire_staging_tangential_offset_m"] == pytest.approx(.06)
    assert route["target"]["grasp_frame"]["position_m"] == target["grasp_frame"]["position_m"]
    assert route["target"]["grasp_frame"]["orientation_xyzw"] == target["grasp_frame"]["orientation_xyzw"]


def test_acquire_preparation_reports_each_failed_corridor_without_motion():
    model = object.__new__(IsaacPhaseMotion)
    model.config = {
        "approach_distance_m": .12,
        "acquire_staging_corridor_candidates": [
            {"approach_distance_m": .12, "staging_backoff_m": 0., "tangential_offset_m": 0.},
            {"approach_distance_m": .18, "staging_backoff_m": .08, "tangential_offset_m": .06},
        ],
        "acquire_transit_clearance_candidates_m": [.04],
        "acquire_transport_orientation_candidates_xyzw": [[1., 0., 0., 0.]],
        "acquire_axial_symmetry_angles_rad": [0.],
        "lift_distance_m": .10,
        "settle_s": .6,
    }
    model.validate_grasp_aperture = lambda _target: None
    model.tcp = lambda: np.eye(4)
    model.observed_pose = lambda _source: np.eye(4)
    model.bind_observed_model = lambda *_args: (np.eye(4), np.eye(4))
    model.body_pose = lambda _path: np.eye(4)
    attempts = []

    def reject(waypoints, *_args, **_kwargs):
        attempts.append(waypoints[4][0][:3, 3].copy())
        raise PhaseMotionError("route_collision", "candidate route rejected")

    model.qualify = reject
    target = {
        "world_from_control": {"translation_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
        "entity_prim_path": "/World/source/Model",
        "destination_prim_path": "/World/destination/Model",
        "object_pose": {"position_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
        "grasp_frame": {"position_m": [0., 0., .2], "orientation_xyzw": [0., 0., 0., 1.]},
        "approach_direction": {"vector": [0., -1., 0.]},
        "destination_pose": {"position_m": [.2, 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
        "return_pose": {"position_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
    }

    with pytest.raises(PhaseMotionError) as captured:
        model.prepare({"manipulation_target": target, "observation_model": {}, "scene_revision": "scene"})

    assert captured.value.code == "route_collision"
    assert len(attempts) == 2
    assert "corridor=0" in str(captured.value)
    assert "corridor_counts={0: 1, 1: 1}" in str(captured.value)


def test_acquire_failure_summary_bounds_repeated_route_diagnostics():
    failures = []
    for corridor in range(4):
        for attempt in range(24):
            code = "ik_discontinuity" if attempt % 2 else "route_collision"
            stage = "staging_reorient" if code == "ik_discontinuity" else "approach"
            failures.append((
                .04 + .04 * (attempt % 3),
                attempt % 2,
                corridor,
                0.,
                PhaseMotionError(code, f"{stage}: " + "diagnostic " * 200),
            ))

    summary = acquire_failure_summary(failures)

    assert len(summary) < 2500
    assert "routes=96" in summary
    assert "ik_discontinuity[staging_reorient] count=48" in summary
    assert "route_collision[approach] count=48" in summary
    assert "corridor_counts={0: 12, 1: 12, 2: 12, 3: 12}" in summary
    assert "clearance_counts={0.04: 16, 0.08: 16, 0.12: 16}" in summary


@pytest.mark.parametrize("values", [[], [0.], [float("nan")], "0.04"])
def test_acquire_transit_clearances_reject_invalid_configuration(values):
    from isaacsim_lab.phase_motion import acquire_transit_clearances

    with pytest.raises(PhaseMotionError) as captured:
        acquire_transit_clearances({"acquire_transit_clearance_candidates_m": values})
    assert captured.value.code == "invalid_motion_configuration"


@pytest.mark.parametrize("values", [
    [],
    [[0., 0., 0., 0.]],
    [[1., 0., 0.]],
    [[float("nan"), 0., 0., 1.]],
    [[True, 0., 0., 0.]],
    [["bad", 0., 0., 1.]],
])
def test_acquire_transport_orientations_reject_invalid_configuration(values):
    from isaacsim_lab.phase_motion import acquire_transport_orientations

    with pytest.raises(PhaseMotionError) as captured:
        acquire_transport_orientations({"acquire_transport_orientation_candidates_xyzw": values})
    assert captured.value.code == "invalid_motion_configuration"


@pytest.mark.parametrize("values", [[], [float("nan")], [np.pi + .01], "0"])
def test_acquire_axial_symmetry_angles_reject_invalid_configuration(values):
    from isaacsim_lab.phase_motion import acquire_axial_symmetry_angles

    with pytest.raises(PhaseMotionError) as captured:
        acquire_axial_symmetry_angles({"acquire_axial_symmetry_angles_rad": values})
    assert captured.value.code == "invalid_motion_configuration"


def test_acquire_preparation_ranks_geometry_equivalent_grasps_after_full_qualification():
    model = object.__new__(IsaacPhaseMotion)
    model.config = {
        "approach_distance_m": .12,
        "acquire_transit_clearance_candidates_m": [.04],
        "acquire_transport_orientation_candidates_xyzw": [[1., 0., 0., 0.]],
        "acquire_axial_symmetry_angles_rad": [0., np.pi / 2],
        "lift_distance_m": .10,
        "settle_s": .6,
    }
    model.validate_grasp_aperture = lambda _target: None
    current = pose_matrix([-.4, 0., 1.], [0., 0., 0., 1.])
    body = pose_matrix([0., 0., .8], [0., 0., 0., 1.])
    model.tcp = lambda: current.copy()
    model.observed_pose = lambda _source: body.copy()
    model.bind_observed_model = lambda *_args: (body.copy(), np.eye(4))
    model.body_pose = lambda _path: np.eye(4)
    model._artifact = lambda *_args: "artifact://readiness/test.json"
    captured = []

    def qualify(waypoints, *_args, **_kwargs):
        captured.append(waypoints)
        grasp_position = waypoints[6][0][:3, 3]
        travel = .1 if grasp_position[1] > .05 else .4
        return {"start_joints": [0.] * 7,
                "steps": [{"joints": [travel] + [0.] * 6, "stage": "lift"}]}

    model.qualify = qualify
    target = {
        "world_from_control": {"translation_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]},
        "entity_prim_path": "/World/R03/Model",
        "destination_prim_path": "/World/BEAKER/Model",
        "object_pose": {"position_m": [0., 0., .8], "orientation_xyzw": [0., 0., 0., 1.]},
        "grasp_frame": {"position_m": [.1, 0., .9], "orientation_xyzw": [0., 0., 0., 1.]},
        "approach_direction": {"vector": [1., 0., 0.]},
        "destination_pose": {"position_m": [.2, 0., .8], "orientation_xyzw": [0., 0., 0., 1.]},
        "return_pose": {"position_m": [0., 0., .8], "orientation_xyzw": [0., 0., 0., 1.]},
    }
    observation_model = {
        "grasp_symmetry": {"kind": "axial", "axis_world": [0., 0., 1.], "origin_world": [0., 0., .8]},
    }

    route, _evidence = model.prepare({
        "manipulation_target": target,
        "observation_model": observation_model,
        "scene_revision": "scene",
    })

    assert len(captured) == 2
    assert route["acquire_axial_symmetry_angle_rad"] == pytest.approx(np.pi / 2)
    assert route["target"]["grasp_frame"]["position_m"] == pytest.approx([0., .1, .9])
    assert route["target"]["approach_direction"]["vector"] == pytest.approx([0., 1., 0.])
    selected = captured[1]
    assert selected[3][0][:3, :3] == pytest.approx(Rotation.from_quat([1., 0., 0., 0.]).as_matrix())
    assert selected[4][2] == "staging_reorient"
    assert selected[4][0][:3, :3] == pytest.approx(selected[5][0][:3, :3])


def _grasp_approach_probe_fixture():
    model = object.__new__(IsaacPhaseMotion)
    model.config = {
        "acquire_axial_symmetry_angles_rad": [0., np.pi / 2],
        "acquire_staging_corridor_candidates": [
            {"approach_distance_m": .12, "staging_backoff_m": 0., "tangential_offset_m": 0.},
            {"approach_distance_m": .18, "staging_backoff_m": .08, "tangential_offset_m": .06},
        ],
        "workspace_min_m": [-1., -1., 0.],
        "workspace_max_m": [1., 1., 2.],
        "position_tolerance_m": .005,
    }
    model.hand_from_tcp = np.eye(4)
    model.limits = np.tile([-3., 3.], (7, 1))
    model.joints = lambda: np.zeros(7)
    model.validate_grasp_aperture = lambda _target: None
    body = pose_matrix([0., 0., .8], [0., 0., 0., 1.])
    model.bind_observed_model = lambda *_args: (body.copy(), np.eye(4))
    model.observed_pose = lambda _source: body.copy()
    model.solver = SimpleNamespace(
        compute_inverse_kinematics=lambda *_args, **_kwargs: (np.zeros(7), True)
    )
    model._collisions = lambda *_args, **_kwargs: None
    model._artifact = lambda _kind, _value: "artifact://labutopia/grasp-approach/test.json"
    model.check_final_gripper_pose = lambda *_args: None
    target = {
        "world_from_control": {
            "translation_m": [0., 0., 0.],
            "orientation_xyzw": [0., 0., 0., 1.],
        },
        "entity_prim_path": "/World/R03/Model",
        "object_pose": {"position_m": [0., 0., .8], "orientation_xyzw": [0., 0., 0., 1.]},
        "grasp_frame": {"position_m": [.1, 0., .9], "orientation_xyzw": [0., 0., 0., 1.]},
        "approach_direction": {"vector": [1., 0., 0.]},
        "destination_pose": {"position_m": [.2, 0., .8], "orientation_xyzw": [0., 0., 0., 1.]},
        "return_pose": {"position_m": [0., 0., .8], "orientation_xyzw": [0., 0., 0., 1.]},
        "grasp_geometry": {"width_m": .02},
    }
    arguments = {
        "candidate_ref": "candidate://source/one",
        "observation_ref": "observation://scene/front",
        "scene_revision": "scene",
        "frame_id": "front",
        "calibration_ref": "artifact://calibration/front",
        "manipulation_target": target,
        "observation_model": {
            "grasp_symmetry": {
                "kind": "axial",
                "axis_world": [0., 0., 1.],
                "origin_world": [0., 0., .8],
            },
        },
    }
    return model, arguments


def test_grasp_approach_probe_selects_geometry_equivalent_feasible_orientation_without_motion():
    model, arguments = _grasp_approach_probe_fixture()
    checked = []

    def qualify(waypoints, *_args, initial_joints, initial_pose, **_kwargs):
        checked.append((waypoints, initial_joints.copy(), initial_pose.copy()))
        desired = waypoints[0][0]
        if desired[1, 3] < .05:
            raise PhaseMotionError("route_collision", "approach: adjacent vessel")
        return {
            "start_joints": initial_joints.tolist(),
            "steps": [{"joints": [0.1] + [0.] * 6, "stage": "grasp"}],
        }

    model.qualify = qualify
    result = model.qualify_grasp_approach(arguments)

    assert result["status"] == "available"
    assert result["candidate_ref"] == arguments["candidate_ref"]
    assert result["selected_axial_symmetry_angle_rad"] == pytest.approx(np.pi / 2)
    assert result["selected_approach_distance_m"] == pytest.approx(.12)
    assert result["motion_authorized"] is False
    assert result["world_change_started"] is False
    assert len(checked) == 4
    assert all(item[0][0][2] == "grasp" and item[0][1][2] == "close" for item in checked)


def test_grasp_approach_probe_fails_closed_when_all_final_approaches_are_unavailable():
    model, arguments = _grasp_approach_probe_fixture()
    model.qualify = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        PhaseMotionError("ik_discontinuity", "approach: no continuous local solution")
    )

    result = model.qualify_grasp_approach(arguments)

    assert result["status"] == "unavailable"
    assert result["failure_code"] == "grasp_approach_unavailable"
    assert "ik_discontinuity" in result["error"]
    assert result["feasibility_ref"].startswith("artifact://")
    assert result["motion_authorized"] is False
    assert result["world_change_started"] is False


def test_obstructed_final_gripper_pose_rejects_before_any_ik_search():
    model, arguments = _grasp_approach_probe_fixture()
    checks, receipts = [], []

    def blocked(pose, source):
        checks.append((pose.copy(), source))
        raise PhaseMotionError("route_collision", "final_grasp: palm/table",
                               diagnostics={"stage": "final_grasp", "checked_tcp": pose.tolist()})

    model.check_final_gripper_pose = blocked
    model.solver.compute_inverse_kinematics = lambda *_a, **_k: pytest.fail("blocked endpoint must precede IK")
    model._artifact = lambda _kind, data: receipts.append(data) or "artifact://endpoint/check"
    result = model.qualify_grasp_approach(arguments)
    assert result["status"] == "unavailable" and result["world_change_started"] is False
    assert len(checks) == 2  # One preflight per axial orientation, reused across backoffs.
    assert len(receipts[0]["attempts"]) == 4
    for attempt in receipts[0]["attempts"]:
        assert attempt["collision_diagnostic"]["stage"] == "final_grasp"
        assert "checked_joints" not in attempt["collision_diagnostic"]
        assert np.array(attempt["grasp_pose_world"]).shape == (4, 4)


def test_clear_endpoint_still_requires_approach_qualification():
    model, arguments = _grasp_approach_probe_fixture()
    checks = []
    model.check_final_gripper_pose = lambda pose, _source: checks.append(pose.copy())
    model.qualify = lambda *_a, **_k: (_ for _ in ()).throw(PhaseMotionError("self_collision", "arm overlap"))
    result = model.qualify_grasp_approach(arguments)
    assert len(checks) == 2
    assert result["status"] == "unavailable"
    assert "self_collision" in result["error"]


def test_missing_palm_geometry_cannot_become_a_clear_endpoint():
    model, arguments = _grasp_approach_probe_fixture()
    model.check_final_gripper_pose = lambda *_a: (_ for _ in ()).throw(
        PhaseMotionError("palm_geometry_unavailable", "cooking failed"))
    model.solver.compute_inverse_kinematics = lambda *_a, **_k: pytest.fail("missing geometry must precede IK")
    result = model.qualify_grasp_approach(arguments)
    assert result["status"] == "unavailable"
    assert "palm_geometry_unavailable" in result["error"]


def test_approach_collision_geometry_stays_in_private_receipt():
    model, arguments = _grasp_approach_probe_fixture()
    diagnostic = {"evidence_kind": "collision_model_overlap", "frame_id": "world",
                  "checked_joints": [0.] * 7, "obstacle_path": "/World/table/mesh"}
    saved = []

    def collide(*_args, **_kwargs):
        raise PhaseMotionError("route_collision", "model overlaps /World/table/mesh", diagnostics=diagnostic)

    model._collisions = collide
    model._artifact = lambda _kind, value: saved.append(value) or "artifact://diagnostic/collision"
    result = model.qualify_grasp_approach(arguments)
    assert result["status"] == "unavailable"
    assert result["world_change_started"] is False
    assert all(item["collision_diagnostic"] == diagnostic for item in saved[0]["attempts"])
    assert "collision_diagnostic" not in result
    assert result["feasibility_ref"] == "artifact://diagnostic/collision"
    assert "/World/table/mesh" not in result["error"]
    assert "/World/table/mesh" in saved[0]["attempts"][0]["error"]


def test_route_qualification_can_start_from_probe_seed_without_reading_live_joints():
    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.config = config()
    model.hand_from_tcp = np.eye(4)
    model.limits = np.tile([-3., 3.], (7, 1))
    model.joints = lambda: (_ for _ in ()).throw(AssertionError("live joints should not be read"))
    model.tcp = lambda joints: pose_matrix([float(joints[0]), 0., 1.], [0., 0., 0., 1.])
    model.solver = SimpleNamespace(
        compute_inverse_kinematics=lambda _frame, position, *_args, **_kwargs:
        (np.r_[position[0], np.zeros(6)], True)
    )
    model._collisions = lambda *_args, **_kwargs: None
    initial = np.r_[.02, np.zeros(6)]
    pre = model.tcp(initial)
    desired = pose_matrix([.04, 0., 1.], [0., 0., 0., 1.])

    route = model.qualify(
        [(desired, 0., "grasp")],
        "/World/source",
        np.eye(4),
        "acquire",
        initial_joints=initial,
        initial_pose=pre,
    )

    assert route["start_joints"] == pytest.approx(initial)
    assert route["steps"][-1]["joints"][0] == pytest.approx(.04)


def test_grasp_probe_preserves_capture_and_real_workspace_rejection_before_ik():
    model, arguments = _grasp_approach_probe_fixture()
    model.config = config()
    target = arguments["manipulation_target"]
    target["grasp_frame"]["position_m"] = [-.262553, -.342018, .750917]
    target["approach_direction"]["vector"] = [.403409, -.659505, .634282]
    evidence = []
    model._artifact = lambda kind, value: evidence.append((kind, value)) or "artifact://probe/rejected"
    model.solver.compute_inverse_kinematics = lambda *_a, **_k: pytest.fail("workspace rejection precedes IK")
    model.qualify = lambda *_a, **_k: pytest.fail("no full route or controller call is allowed")

    result = model.qualify_grasp_approach(arguments)

    assert result["status"] == "unavailable"
    saved = evidence[0][1]
    for key in ("candidate_ref", "observation_ref", "scene_revision", "frame_id", "calibration_ref"):
        assert saved[key] == arguments[key]
    assert saved["failure_counts"] == {"workspace_violation": 8}
    assert saved["workspace_frame_id"] == "world"
    assert saved["motion_authorized"] is False
    assert saved["world_change_started"] is False
    assert len(saved["attempts"]) == 8
    heights = [attempt["pregrasp_position_world_m"][2] for attempt in saved["attempts"]]
    assert heights == pytest.approx([.674803, .636746] * 4, abs=1e-6)
    for attempt in saved["attempts"]:
        desired = pose_matrix(attempt["grasp_position_world_m"], [0., 0., 0., 1.])
        corridor = (attempt["approach_distance_m"], 0., 0.)
        route = acquire_route_waypoints(
            pose_matrix([0., 0., 1.], [0., 0., 0., 1.]), desired,
            attempt["approach_direction_world"], .04, [1., 0., 0., 0.], corridor, model.config,
        )
        full_pre = next(pose for pose, _, stage in route if stage == "approach")
        assert full_pre[:3, 3] == pytest.approx(attempt["pregrasp_position_world_m"])


def test_grasp_probe_uses_real_short_route_qualification_without_live_state_changes():
    model, arguments = _grasp_approach_probe_fixture()
    model.config = {**config(), "acquire_axial_symmetry_angles_rad": [0.]}
    arguments["observation_model"] = {}
    model.tcp = lambda joints: pose_matrix(joints[:3], [0., 0., 0., 1.])
    model.solver.compute_inverse_kinematics = lambda _frame, position, *_a, **_k: (
        np.r_[position, np.zeros(4)], True
    )
    checked = []
    model._collisions = lambda joints, *_a, **_k: checked.append(joints.copy())
    saved = []
    model._artifact = lambda _kind, value: saved.append(value) or "artifact://probe/accepted"
    before = deepcopy(arguments)

    result = model.qualify_grasp_approach(arguments)

    assert result["status"] == "available"
    assert arguments == before
    assert checked
    assert saved[0]["status"] == "available"
    assert saved[0]["motion_authorized"] is False
    assert saved[0]["world_change_started"] is False
    assert {s["stage"] for s in saved[0]["route"]["steps"]} == {"grasp", "close"}
    assert saved[0]["route"]["steps"][-1]["joints"][:3] == pytest.approx([.1, 0., .9])


def test_route_qualification_rejects_probe_seed_pose_that_disagrees_with_fk():
    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.config = config()
    model.hand_from_tcp = np.eye(4)
    model.limits = np.tile([-3., 3.], (7, 1))
    model.tcp = lambda _joints: pose_matrix([0., 0., 1.], [0., 0., 0., 1.])
    wrong = pose_matrix([.1, 0., 1.], [0., 0., 0., 1.])

    with pytest.raises(PhaseMotionError, match="same kinematic state") as captured:
        model.qualify(
            [(wrong, 0., "grasp")],
            "/World/source",
            np.eye(4),
            "acquire",
            initial_joints=np.zeros(7),
            initial_pose=wrong,
        )

    assert captured.value.code == "invalid_initial_motion_state"


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
            raise PhaseMotionError("route_collision", "obstacle between endpoints",
                                   diagnostics={"checked_joints": joints.tolist()})
    model._collisions = collide
    goal = pose_matrix([.1, 0., 1.], [0., 0., 0., 1.])
    with pytest.raises(PhaseMotionError, match="between endpoints") as captured:
        model.qualify([(goal, 0., "approach")], "/World/source", np.eye(4), "acquire")
    assert any(.035 <= value <= .065 for value in samples)
    assert max(samples) < .1
    assert "checked TCP=" in str(captured.value)
    assert "checked joints=" in str(captured.value)
    assert captured.value.diagnostics["checked_joints"][0] == pytest.approx(samples[-1])


def test_discontinuous_primary_ik_is_rejected_when_nearby_recovery_fails(monkeypatch):
    import isaacsim_lab.phase_motion as phase_motion

    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.config = config()
    model.hand_from_tcp = np.eye(4)
    model.joints = lambda: np.zeros(7)
    model.tcp = lambda joints=None: pose_matrix(
        [0. if joints is None else float(np.asarray(joints)[0]), 0., 1.],
        [0., 0., 0., 1.],
    )
    model.limits = np.tile([-5., 5.], (7, 1))
    model.solver = SimpleNamespace(compute_inverse_kinematics=lambda *_a, **_k:
                                   (np.r_[4.201, np.zeros(6)], True))
    monkeypatch.setattr(
        phase_motion,
        "local_inverse_kinematics",
        lambda *_a, **_k: (np.r_[.2, np.zeros(6)], False),
    )
    model._collisions = lambda *_a, **_k: pytest.fail("discontinuous IK must not reach collision sampling")

    target = pose_matrix([.01, 0., 1.], [0., 0., 0., 1.])
    with pytest.raises(PhaseMotionError) as captured:
        model.qualify([(target, 0., "transit_cross")], "/World/source", np.eye(4), "acquire")

    assert captured.value.code == "ik_discontinuity"
    assert "4.201000 rad" in str(captured.value)
    assert "configured maximum 0.500000 rad" in str(captured.value)


def test_nearby_ik_replaces_discontinuous_primary_solution(monkeypatch):
    import isaacsim_lab.phase_motion as phase_motion

    model = IsaacPhaseMotion.__new__(IsaacPhaseMotion)
    model.config = config()
    model.hand_from_tcp = np.eye(4)
    model.joints = lambda: np.zeros(7)
    model.tcp = lambda joints=None: pose_matrix(
        [0. if joints is None else float(np.asarray(joints)[0]), 0., 1.],
        [0., 0., 0., 1.],
    )
    model.limits = np.tile([-5., 5.], (7, 1))
    model.solver = SimpleNamespace(compute_inverse_kinematics=lambda *_a, **_k:
                                   (np.r_[4.201, np.zeros(6)], True))
    monkeypatch.setattr(
        phase_motion,
        "local_inverse_kinematics",
        lambda *_a, **_k: (np.r_[.1, np.zeros(6)], True),
    )
    checked = []
    model._collisions = lambda joints, *_a, **_k: checked.append(np.asarray(joints).copy())

    target = pose_matrix([.01, 0., 1.], [0., 0., 0., 1.])
    route = model.qualify([(target, 0., "transit_cross")], "/World/source", np.eye(4), "acquire")

    assert route["steps"][-1]["joints"] == pytest.approx([.1, 0., 0., 0., 0., 0., 0.])
    assert checked
    assert max(float(np.max(np.abs(value))) for value in checked) <= .1


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
