"""Session-owned, measured phase preparation for the Isaac laboratory adapter.

The route contains joint targets, not controller completion flags. Preparation
only reads physics state and performs FK, IK and overlap queries. Execution
uses articulation commands; it never teleports an object or attaches it by
editing a USD transform. Runtime remains the owner of possession/settlement.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from functools import cached_property
from itertools import chain, groupby, product, repeat
from pathlib import Path
from uuid import uuid4

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation, Slerp


class PhaseMotionError(ValueError):
    def __init__(self, code, detail, *, diagnostics=None):
        super().__init__(detail)
        self.code = code
        self.diagnostics = diagnostics


class PhaseMotionPreconditionError(PhaseMotionError):
    """A phase was rejected before issuing any actuator command."""


def collision_hits(query, *geometry, ignore):
    """Read PhysX OverlapHit attributes without losing callback exceptions in C++."""
    found, errors = [], []

    def report(hit):
        try:
            path = hit.collision
            if ignore(path):
                return True
            found.append(path)
        except Exception as exc:
            errors.append(exc)
        return False

    query(*geometry, report, False)
    if errors:
        raise PhaseMotionError("collision_query_failed", str(errors[0])) from errors[0]
    return found


def prim_path_is_within(path, root):
    """Match one USD prim or its descendants without prefix collisions."""
    root = str(root).rstrip("/")
    return bool(root and (path == root or path.startswith(root + "/")))


def preparation_result(arguments, route, evidence):
    """Project the measured route into the existing typed PAOS assignment."""
    from hashlib import sha256

    from PhyAgentOS.forge.capability_runtime.manipulation_prepare import preparation_ref_for_request
    from PhyAgentOS.forge.manipulation import ArmAssignment, arm_assignment_digest

    # ArmAssignment already requires the canonical route digest. This uses that
    # existing contract; it does not introduce a second route-integrity scheme.
    route_digest = sha256(json.dumps(route, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    private = {**deepcopy(dict(arguments)), "phase_route": route}
    intent = arguments["intent"]
    coordination_mode = intent.get("coordination_mode")
    allowed_arms = tuple(intent.get("allowed_arms") or ())
    # This LabUtopia profile exposes one measured Franka articulation. Do not
    # reinterpret one arm as left/right or silently collapse a bimanual request
    # into a single assignment at the provider boundary.
    if coordination_mode != "single_arm" or allowed_arms != ("franka",):
        raise PhaseMotionError(
            "unsupported_capability_topology",
            "LabUtopia exposes topology=single_arm with arm_id=franka; "
            f"received coordination_mode={coordination_mode!r}, allowed_arms={list(allowed_arms)!r}",
        )
    if arguments.get("held_invocation_ref"):
        return {"status": "available", "motion_authorized": False, "route_arguments": private,
                "route_digest": route_digest, "readiness_evidence_ref": evidence}
    assignment = {key: intent[key] for key in ("task_id", "revision_id", "node_id", "node_digest", "entity_ref",
                  "observation_ref", "scene_revision", "calibration_ref", "candidate_set_ref", "coordination_mode")}
    candidate = arguments["manipulation_target"]["candidate_ref"]
    if "franka" not in intent["allowed_arms"]:
        raise PhaseMotionError("arm_not_allowed", "the current scene exposes the franka arm")
    assignment.update(assignment_ref=f"artifact://labutopia/assignments/{uuid4().hex}", selected_arm_ids=["franka"],
                      candidate_ref=candidate, route_digest=route_digest,
                      capability_snapshot_ref=arguments["capability_snapshot_ref"], readiness_evidence_ref=evidence,
                      decision_basis=["measured FK/IK, workspace, robot/payload collision queries"], alternatives=[],
                      motion_authorized=False, schema_version="paos-arm-assignment/v1")
    assignment["assignment_digest"] = arm_assignment_digest(assignment)
    assignment = ArmAssignment.model_validate(assignment).model_dump(mode="json")
    private.update(candidate_ref=candidate, preparation_ref=preparation_ref_for_request(arguments),
                   assignment_ref=assignment["assignment_ref"])
    return {"status": "available", "motion_authorized": False,
            "prepared_candidates": [{"candidate_ref": candidate, "entity_ref": assignment["entity_ref"],
                                     "qualification": "prepared", "checks": {"kinematic": "pass", "collision": "pass", "workspace": "pass"},
                                     "evidence": [evidence]}],
            "assignments": [assignment], "destination_ref": arguments["destination_ref"], "route_arguments": private}


def lula_base_pose_from_link_world(world_from_link):
    """Lula base-pose arguments (position, wxyz quaternion) from an arm-link world matrix.

    ``set_robot_base_pose`` expects a scalar-first quaternion and the frame of
    the arm root, which for mounted robots (ridgeback: +0.3 m forward, +0.28 m
    up from the articulation root) is not the robot root pose the solver was
    previously seeded with.
    """
    matrix = np.asarray(world_from_link, dtype=float)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise PhaseMotionError("invalid_arm_base_pose",
                               "panda_link0 world transform must be a finite 4x4 matrix")
    rotation = matrix[:3, :3]
    if (not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6)
            or np.linalg.det(rotation) <= 0.):
        raise PhaseMotionError("invalid_arm_base_pose",
                               "panda_link0 world rotation must be a right-handed rotation matrix")
    return matrix[:3, 3].copy(), np.roll(Rotation.from_matrix(rotation).as_quat(), 1)


def pose_matrix(position, orientation_xyzw):
    result = np.eye(4)
    result[:3, :3] = Rotation.from_quat(orientation_xyzw).as_matrix()
    result[:3, 3] = position
    return result


def interpolate_pose(start, finish, translation_step=.01, rotation_step=.04):
    distance = np.linalg.norm(finish[:3, 3] - start[:3, 3])
    angle = Rotation.from_matrix(start[:3, :3].T @ finish[:3, :3]).magnitude()
    count = max(1, math.ceil(distance / translation_step), math.ceil(angle / rotation_step))
    rotations = Slerp([0., 1.], Rotation.from_matrix([start[:3, :3], finish[:3, :3]]))
    for fraction in np.linspace(0., 1., count + 1)[1:]:
        value = np.eye(4)
        value[:3, :3] = rotations(fraction).as_matrix()
        value[:3, 3] = start[:3, 3] + fraction * (finish[:3, 3] - start[:3, 3])
        yield value


def held_tool_pose(tcp_from_object, tip_offset, desired_tip, object_rotation):
    """Convert a process feature target to TCP using the measured grasp relation."""
    world_from_object = np.eye(4)
    world_from_object[:3, :3] = object_rotation
    world_from_object[:3, 3] = desired_tip - object_rotation @ tip_offset
    return world_from_object @ np.linalg.inv(tcp_from_object)


def tool_feature_errors(actual, target, tool):
    tip, axis = np.asarray(tool["tip_offset_m"]), np.asarray(tool["tip_axis_local"])
    tip_error = float(np.linalg.norm(actual[:3, 3] + actual[:3, :3] @ tip
                                    - target[:3, 3] - target[:3, :3] @ tip))
    axis_error = float(math.acos(np.clip(np.dot(actual[:3, :3] @ axis, target[:3, :3] @ axis), -1., 1.)))
    return tip_error, axis_error


def grasp_pose_errors(reference, current, axial_symmetry=None):
    """Measure slip at the bound grasp anchor, independent of the body origin.

    The reference TCP origin defines a physical point in the object. Track that
    same point in the current TCP frame; a bottle-base pivot must not turn a
    permitted rotation into an extra height-dependent translation failure.
    """
    anchor_in_object = -reference[:3, :3].T @ reference[:3, 3]
    anchor_in_tcp = current[:3, :3] @ anchor_in_object + current[:3, 3]
    if axial_symmetry is None:
        rotation_error = Rotation.from_matrix(reference[:3, :3].T @ current[:3, :3]).magnitude()
    else:
        axis = np.asarray(axial_symmetry, dtype=float)
        axis /= np.linalg.norm(axis)
        rotation_error = math.acos(np.clip(np.dot(reference[:3, :3] @ axis, current[:3, :3] @ axis), -1., 1.))
    return float(np.linalg.norm(anchor_in_tcp)), float(rotation_error)


def grasp_anchor_drift(anchor_in_object, reference_world, current_world):
    """World-frame displacement of a bound object-frame anchor between object world poses.

    ``grasp_pose_errors`` anchors at the reference origin, which for two world
    poses is the world origin up to a metre from the body — a touch-induced
    bottle rotation then reads as centimetres of drift. This variant tracks the
    named object-frame anchor (e.g. the TCP grasp point) directly.
    """
    anchor = np.asarray(anchor_in_object, dtype=float)
    reference_world = np.asarray(reference_world, dtype=float)
    current_world = np.asarray(current_world, dtype=float)
    return float(np.linalg.norm((current_world[:3, :3] - reference_world[:3, :3]) @ anchor
                                + current_world[:3, 3] - reference_world[:3, 3]))


def support_contact_allowed(stage, body_pose, supported_pose, tolerance):
    """Permit horizontal fixture contact only within its vertical departure band."""
    if stage not in {"lift", "lower"} or supported_pose is None:
        return False
    delta = body_pose[:3, 3] - supported_pose[:3, 3]
    return bool(-.002 <= delta[2] <= tolerance)


def smooth_joint_segment(start, goal, dt, velocity_limit, acceleration_limit):
    """Rest-to-rest quintic segment with bounded peak speed and acceleration."""
    delta = np.asarray(goal) - np.asarray(start)
    distance = float(np.max(np.abs(delta)))
    duration = max(1.875 * distance / velocity_limit,
                   math.sqrt((10 / math.sqrt(3)) * distance / acceleration_limit))
    frames = max(1, math.ceil(duration / dt))
    for frame in range(1, frames + 1):
        fraction = frame / frames
        progress = fraction**3 * (10 - 15 * fraction + 6 * fraction**2)
        yield np.asarray(start) + progress * delta


def continuous_joint_path(points, dt, duration, velocity_limit, acceleration_limit, *, ease_endpoints=False):
    """Sample a C2 path with rest endpoints and analytic timing bounds."""
    points = np.asarray(points, dtype=float)
    knots = np.linspace(0., 1., len(points))
    spline = CubicSpline(knots, points, axis=0, bc_type="natural" if ease_endpoints else "clamped")
    a, b, c, _ = spline.c
    width = np.diff(knots)[:, None]
    stationary = np.clip(np.divide(-b, 3 * a, out=np.zeros_like(a), where=a != 0), 0., width)
    peak_velocity = float(np.max(np.abs(np.stack((c, (3*a*width + 2*b)*width + c,
                                                  (3*a*stationary + 2*b)*stationary + c)))))
    peak_acceleration = float(np.max(np.abs(np.stack((2*b, 6*a*width + 2*b)))))
    if ease_endpoints:
        # A global quintic clock provides rest endpoints without forcing a
        # steep stop inside the first/last dense geometric knot interval.
        # Chain-rule bounds: q''(s) s'^2 + q'(s) s''.
        peak_acceleration = peak_acceleration * 1.875**2 + peak_velocity * (10 / math.sqrt(3))
        peak_velocity *= 1.875
    duration = max(duration, peak_velocity / velocity_limit, math.sqrt(peak_acceleration / acceleration_limit))
    frames = max(2, math.ceil(duration / dt))
    progress = np.linspace(0., 1., frames + 1)[1:]
    if ease_endpoints:
        progress = progress**3 * (10 - 15 * progress + 6 * progress**2)
    return spline(progress)


def acquire_transit_clearances(config):
    """Return the bounded Adapter-private height search configured for acquire."""
    values = config.get("acquire_transit_clearance_candidates_m")
    if (not isinstance(values, list) or not values
            or any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not math.isfinite(value) or value <= 0 for value in values)):
        raise PhaseMotionError(
            "invalid_motion_configuration",
            "acquire_transit_clearance_candidates_m must be a non-empty list of finite positive numbers",
        )
    return tuple(dict.fromkeys(float(value) for value in values))


def acquire_transport_orientations(config):
    """Return configured world-frame TCP orientations for raised translation."""
    values = config.get("acquire_transport_orientation_candidates_xyzw")
    if not isinstance(values, list) or not values:
        raise PhaseMotionError(
            "invalid_motion_configuration",
            "acquire_transport_orientation_candidates_xyzw must be a non-empty list",
        )
    orientations = []
    for value in values:
        if (not isinstance(value, (list, tuple)) or len(value) != 4
                or any(isinstance(component, bool) for component in value)):
            quaternion = np.asarray([])
        else:
            try:
                quaternion = np.asarray(value, dtype=float)
            except (TypeError, ValueError):
                quaternion = np.asarray([])
        if (quaternion.shape != (4,) or not np.isfinite(quaternion).all()
                or abs(float(np.linalg.norm(quaternion)) - 1.0) > 1e-3):
            raise PhaseMotionError(
                "invalid_motion_configuration",
                "acquire transport orientations must be normalized finite xyzw quaternions",
            )
        item = tuple(float(component) for component in quaternion)
        if item not in orientations:
            orientations.append(item)
    return tuple(orientations)


def acquire_axial_symmetry_angles(config):
    """Return bounded axial rotations used only with explicit geometry evidence."""
    values = config.get("acquire_axial_symmetry_angles_rad")
    if (not isinstance(values, list) or not values
            or any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not math.isfinite(value) or abs(float(value)) > math.pi for value in values)):
        raise PhaseMotionError(
            "invalid_motion_configuration",
            "acquire_axial_symmetry_angles_rad must contain finite angles within [-pi, pi]",
        )
    return tuple(dict.fromkeys(float(value) for value in values))


def acquire_min_reorient_radius(config):
    """Return the optional minimum base radius for orientation-changing waypoints.

    Zero (the default) preserves the legacy raise/orient positions; a positive
    value pushes the raised and staging waypoints radially outward from the
    base before any orientation change, moving reorientation out of the
    near-base wrist-fold region. Bounded, Adapter-private and geometry-only.
    """
    value = config.get("acquire_min_reorient_radius_m", 0.)
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0.):
        raise PhaseMotionError(
            "invalid_motion_configuration",
            "acquire_min_reorient_radius_m must be a finite non-negative number",
        )
    return float(value)


def acquire_probe_terminal_seed_count(config):
    """Return the bounded deterministic IK seed count for terminal-pose sampling.

    The probe samples several IK branches at the final grasp pose before any
    route search: when every sampled branch collides for the whole arm, the
    candidate is terminally doomed and corridor enumeration cannot rescue it.
    Pruning happens only on positive evidence (solutions exist and all
    collide); zero solutions never prunes.
    """
    value = config.get("acquire_probe_terminal_seed_count", 8)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 32:
        raise PhaseMotionError(
            "invalid_motion_configuration",
            "acquire_probe_terminal_seed_count must be an integer between 1 and 32",
        )
    return int(value)


def acquire_failure_recovery_codes(config):
    """Return configured acquire failures eligible for measured safe retreat."""
    values = config.get("acquire_failure_recovery_codes", [])
    if (
        not isinstance(values, list)
        or any(not isinstance(value, str) or not value.strip() for value in values)
        or len(set(values)) != len(values)
    ):
        raise PhaseMotionError(
            "invalid_motion_configuration",
            "acquire_failure_recovery_codes must contain distinct non-empty strings",
        )
    return tuple(values)


def deterministic_ik_seeds(seed_joints, limits, count):
    """Return a bounded deterministic warm-start set: current, midpoint, offsets."""
    lower, upper = limits[:, 0], limits[:, 1]
    span = upper - lower
    midpoint = lower + span * 0.5
    seeds = [np.asarray(seed_joints, dtype=float).copy(), midpoint]
    for index in range(2, max(2, int(count))):
        fraction = 0.25 * np.sin((index - 1) * 0.7 + np.arange(len(span)) * 0.9)
        seeds.append(np.clip(midpoint + span * fraction, lower, upper))
    return seeds[:max(2, int(count))]


def acquire_staging_corridors(config):
    """Return bounded Adapter-private pregrasp and staging geometry candidates."""
    values = config.get("acquire_staging_corridor_candidates")
    if values is None:
        values = [{
            "approach_distance_m": config.get("approach_distance_m"),
            "staging_backoff_m": 0.0,
            "tangential_offset_m": 0.0,
        }]
    if not isinstance(values, list) or not values:
        raise PhaseMotionError(
            "invalid_motion_configuration",
            "acquire_staging_corridor_candidates must be a non-empty list",
        )
    corridors = []
    for value in values:
        if not isinstance(value, dict):
            raise PhaseMotionError(
                "invalid_motion_configuration",
                "acquire staging corridor candidates must be objects",
            )
        raw = (
            value.get("approach_distance_m"),
            value.get("staging_backoff_m"),
            value.get("tangential_offset_m"),
        )
        if any(isinstance(component, bool) or not isinstance(component, (int, float))
               or not math.isfinite(component) for component in raw):
            raise PhaseMotionError(
                "invalid_motion_configuration",
                "acquire staging corridor values must be finite numbers",
            )
        approach_distance, staging_backoff, tangential_offset = map(float, raw)
        if approach_distance <= 0 or staging_backoff < 0:
            raise PhaseMotionError(
                "invalid_motion_configuration",
                "acquire approach distance must be positive and staging backoff non-negative",
            )
        corridor = (approach_distance, staging_backoff, tangential_offset)
        if corridor not in corridors:
            corridors.append(corridor)
    return tuple(corridors)


def acquire_route_selection(config):
    policy = config.get("acquire_route_selection", "minimum_joint_travel")
    if policy not in ("minimum_joint_travel", "first_feasible", "simulator_truth_preselected"):
        raise PhaseMotionError("invalid_motion_configuration", "unsupported acquire route selection policy")
    return policy


def acquire_route_search_timeout(config):
    """Return the Adapter-private wall-clock budget for complete acquire search."""
    value = config.get("acquire_route_search_timeout_s", 600.)
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0):
        raise PhaseMotionError(
            "invalid_motion_configuration",
            "acquire_route_search_timeout_s must be a finite positive number",
        )
    return float(value)


def acquire_route_strategies(config):
    """Return ordered Adapter-private acquire planners."""
    values = config.get("acquire_route_strategies", ["staged"])
    if (not isinstance(values, list) or not values
            or any(value not in {"direct", "staged"} for value in values)):
        raise PhaseMotionError(
            "invalid_motion_configuration",
            "acquire_route_strategies must be a non-empty list containing direct or staged",
        )
    return tuple(dict.fromkeys(values))


def acquire_direct_route_waypoints(tcp, desired, approach, corridor, config):
    """Build a natural current-pose to pregrasp route for full qualification."""
    tcp = np.asarray(tcp, dtype=float)
    desired = np.asarray(desired, dtype=float)
    approach = np.asarray(approach, dtype=float)
    if (tcp.shape != (4, 4) or desired.shape != (4, 4) or approach.shape != (3,)
            or not np.isfinite(tcp).all() or not np.isfinite(desired).all()
            or not np.isfinite(approach).all() or float(np.linalg.norm(approach)) <= 1e-9):
        raise PhaseMotionError(
            "invalid_grasp_approach",
            "direct acquire route requires finite poses and a non-zero approach direction",
        )
    approach = approach / np.linalg.norm(approach)
    approach_distance = corridor[0]
    pre = desired.copy()
    pre[:3, 3] -= approach * approach_distance
    lifted = desired.copy()
    lifted[2, 3] += config["lift_distance_m"]
    return [
        (tcp, config["settle_s"], "open"),
        (pre, 0., "direct_pregrasp"),
        (desired, config["settle_s"], "grasp"),
        (desired, config["settle_s"], "close"),
        (lifted, config["settle_s"], "lift"),
    ]


def _push_to_reorient_radius(pose, radius):
    """Return a copy of the pose pushed horizontally outward to the given base radius."""
    pose = pose.copy()
    if radius <= 0.:
        return pose
    xy = pose[:2, 3]
    current = float(np.linalg.norm(xy))
    if current < radius and current > 1e-9:
        pose[:2, 3] = xy * (radius / current)
    return pose


def acquire_route_waypoints(tcp, desired, approach, clearance, transport_quaternion, corridor, config):
    """Build one geometry-derived acquire corridor without robot or task labels.

    With ``acquire_min_reorient_radius_m`` configured, the raised and staging
    waypoints are pushed radially outward from the base before any orientation
    change so reorientation happens at a comfortable radius instead of folding
    the wrist high above the base. Final approach, grasp and lift poses are
    unchanged, and every route still passes the unchanged qualification.

    ``transport_quaternion=None`` is the carry-as-grasped candidate: the raised
    waypoint keeps the qualified grasp orientation, so ``transit_orient`` applies
    zero rotation. A world-frame transport quaternion can demand 50-90 degrees of
    wrist reorientation for tilted truth-derived grasp frames (or be unreachable
    at the raised waypoint with joint jumps), while carrying the grasp orientation
    needs none; every route still flows through the unchanged qualification and
    collision checks.
    """
    tcp = np.asarray(tcp, dtype=float)
    desired = np.asarray(desired, dtype=float)
    approach = np.asarray(approach, dtype=float)
    if (tcp.shape != (4, 4) or desired.shape != (4, 4) or approach.shape != (3,)
            or not np.isfinite(tcp).all() or not np.isfinite(desired).all()
            or not np.isfinite(approach).all() or float(np.linalg.norm(approach)) <= 1e-9):
        raise PhaseMotionError(
            "invalid_grasp_approach",
            "acquire corridor requires finite poses and a non-zero approach direction",
        )
    approach = approach / np.linalg.norm(approach)
    approach_distance, staging_backoff, tangential_offset = corridor
    pre = desired.copy()
    pre[:3, 3] -= approach * approach_distance
    lifted = desired.copy()
    lifted[2, 3] += config["lift_distance_m"]
    base_height = max(float(tcp[2, 3]), float(pre[2, 3]), float(desired[2, 3]))
    transit_height = base_height + clearance
    horizontal_tangent = np.cross(np.asarray([0., 0., 1.]), approach)
    if float(np.linalg.norm(horizontal_tangent)) <= 1e-9:
        horizontal_tangent = np.asarray([1., 0., 0.])
    else:
        horizontal_tangent /= np.linalg.norm(horizontal_tangent)
    staged = pre.copy()
    staged[:3, 3] -= approach * staging_backoff
    staged[:3, 3] += horizontal_tangent * tangential_offset
    staged[2, 3] = transit_height
    raised = tcp.copy()
    raised[2, 3] = transit_height
    reorient_radius = acquire_min_reorient_radius(config)
    raised = _push_to_reorient_radius(raised, reorient_radius)
    staged = _push_to_reorient_radius(staged, reorient_radius)
    transport_ready = raised.copy()
    if transport_quaternion is None:
        # Carry-as-grasped: hold the qualified grasp orientation through transit.
        transport_ready[:3, :3] = desired[:3, :3]
    else:
        transport_ready[:3, :3] = Rotation.from_quat(transport_quaternion).as_matrix()
    transported = transport_ready.copy()
    transported[:2, 3] = staged[:2, 3]
    return [
        (tcp, config["settle_s"], "open"),
        (raised, 0., "transit_raise"),
        (transport_ready, 0., "transit_orient"),
        (transported, 0., "transit_cross"),
        (staged, 0., "staging_reorient"),
        (pre, 0., "approach"),
        (desired, config["settle_s"], "grasp"),
        (desired, config["settle_s"], "close"),
        (lifted, config["settle_s"], "lift"),
    ]


def _acquire_waypoint_prefixes(waypoints):
    """Yield exact generated waypoint-prefix identities for one route."""
    prefix = []
    for pose, _hold_s, stage in waypoints:
        matrix = np.asarray(pose, dtype=float)
        prefix.append((stage, tuple(float(value) for value in matrix.reshape(-1))))
        yield stage, tuple(prefix)


def acquire_failure_summary(failures):
    """Bound route diagnostics while retaining failure ownership and coverage."""
    stage_names = {
        "open", "direct_pregrasp", "transit_raise", "transit_orient", "transit_cross",
        "staging_reorient", "approach", "grasp", "close", "lift",
    }
    counts = Counter()
    strategies = defaultdict(Counter)
    corridors = defaultdict(Counter)
    clearances = defaultdict(Counter)
    transports = defaultdict(Counter)
    examples = {}
    for failure in failures:
        if len(failure) == 5:
            strategy = "staged"
            clearance, transport_order, corridor_order, symmetry_angle, exc = failure
        else:
            strategy, clearance, transport_order, corridor_order, symmetry_angle, exc = failure
        detail = str(exc)
        prefix = detail.split(":", 1)[0]
        if prefix in stage_names:
            stage = prefix
        elif detail.startswith("no solution in "):
            stage = detail.removeprefix("no solution in ").split(":", 1)[0]
        else:
            stage = "unknown"
        key = (exc.code, stage)
        counts[key] += 1
        strategies[key][strategy] += 1
        corridors[key][corridor_order] += 1
        clearances[key][clearance] += 1
        transports[key][transport_order] += 1
        examples.setdefault(key, (strategy, clearance, transport_order, corridor_order, symmetry_angle, detail))
    sections = [f"routes={len(failures)}"]
    for key in sorted(counts):
        code, stage = key
        strategy, clearance, transport, corridor, angle, detail = examples[key]
        if len(detail) > 400:
            detail = detail[:397] + "..."
        sections.append(
            f"{code}[{stage}] count={counts[key]}, "
            f"strategy_counts={dict(sorted(strategies[key].items()))}, "
            f"corridor_counts={dict(sorted(corridors[key].items()))}, "
            f"clearance_counts={dict(sorted(clearances[key].items(), key=lambda item: str(item[0])))}, "
            f"transport_counts={dict(sorted(transports[key].items()))}; "
            f"example strategy={strategy}, clearance={clearance}, transport={transport}, corridor={corridor}, "
            f"axial_angle={angle}: {detail}"
        )
    return "; ".join(sections)


def acquire_grasp_variants(desired, approach, symmetry, angles):
    """Rotate a qualified grasp around a Provider-declared world-space axis."""
    desired = np.asarray(desired, dtype=float)
    approach = np.asarray(approach, dtype=float)
    if symmetry is None:
        return ((None, desired.copy(), approach.copy()),)
    if not isinstance(symmetry, dict) or symmetry.get("kind") != "axial":
        raise PhaseMotionError("invalid_grasp_symmetry_evidence", "unsupported grasp symmetry declaration")
    axis = np.asarray(symmetry.get("axis_world"), dtype=float)
    origin = np.asarray(symmetry.get("origin_world"), dtype=float)
    if (axis.shape != (3,) or origin.shape != (3,) or not np.isfinite(axis).all()
            or not np.isfinite(origin).all() or float(np.linalg.norm(axis)) <= 1e-9):
        raise PhaseMotionError(
            "invalid_grasp_symmetry_evidence",
            "axial grasp symmetry requires a finite world axis and origin",
        )
    axis /= np.linalg.norm(axis)
    variants = []
    for angle in angles:
        rotation = Rotation.from_rotvec(axis * angle).as_matrix()
        pose = desired.copy()
        pose[:3, :3] = rotation @ desired[:3, :3]
        pose[:3, 3] = origin + rotation @ (desired[:3, 3] - origin)
        variants.append((angle, pose, rotation @ approach))
    return tuple(variants)


def route_joint_travel(route):
    """Compare only routes already admitted by the embodiment safety checks."""
    points = np.asarray([route["start_joints"], *[step["joints"] for step in route["steps"]]])
    return float(np.abs(np.diff(points, axis=0)).sum())


def joint_delta(start, goal):
    """Return the largest physical joint displacement for one IK step."""
    start = np.asarray(start, dtype=float)
    goal = np.asarray(goal, dtype=float)
    if start.shape != goal.shape or not np.isfinite(start).all() or not np.isfinite(goal).all():
        return math.inf
    return float(np.max(np.abs(goal - start)))


def measured_feature_target(nominal_tcp, nominal_relation, measured_relation, tool):
    """Correct rod tip/axis tracking while leaving its free axial roll alone."""
    tip = np.asarray(tool["tip_offset_m"])
    axis = np.asarray(tool["tip_axis_local"])
    desired_body = nominal_tcp @ nominal_relation
    desired_tip = desired_body[:3, 3] + desired_body[:3, :3] @ tip
    desired_axis = desired_body[:3, :3] @ axis
    nominal_axis = nominal_tcp[:3, :3] @ measured_relation[:3, :3] @ axis
    correction, _ = Rotation.align_vectors([desired_axis], [nominal_axis])
    target = nominal_tcp.copy()
    target[:3, :3] = correction.as_matrix() @ nominal_tcp[:3, :3]
    target[:3, 3] = desired_tip - target[:3, :3] @ (measured_relation[:3, 3] + measured_relation[:3, :3] @ tip)
    return target


def observed_point_boxes(points, slice_length=.01):
    """Bound the observed surface in slabs; no hidden mesh is reconstructed."""
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 20 or not np.isfinite(points).all():
        raise PhaseMotionError("payload_geometry_unavailable", "payload needs finite observed depth points")
    lower, upper = points.min(0), points.max(0)
    axis = int(np.argmax(upper - lower))
    count = max(1, min(32, math.ceil((upper[axis] - lower[axis]) / slice_length)))
    boundaries = np.linspace(lower[axis], upper[axis], count + 1)
    boxes = []
    for low, high in zip(boundaries, boundaries[1:]):
        samples = points[(points[:, axis] >= low) & (points[:, axis] <= high)]
        if len(samples):
            boxes.append((samples.min(0), samples.max(0)))
    return boxes


def local_inverse_kinematics(forward, target, seed, limits, position_tolerance):
    """Seek the nearby redundant-arm solution without a periodic branch jump."""
    def residual(joints):
        actual = forward(joints)
        return np.r_[(actual[:3, 3] - target[:3, 3]) * 10.,
                     Rotation.from_matrix(target[:3, :3].T @ actual[:3, :3]).as_rotvec()]
    result = least_squares(residual, np.clip(seed, limits[:, 0], limits[:, 1]),
                           bounds=(limits[:, 0], limits[:, 1]), max_nfev=120,
                           ftol=1e-8, xtol=1e-8, gtol=1e-8)
    error = residual(result.x)
    valid = np.linalg.norm(error[:3]) <= 10 * position_tolerance and np.linalg.norm(error[3:]) <= .02
    return result.x, bool(valid)


def local_tool_inverse_kinematics(forward, target_body, relation, tool, seed, limits, position_tolerance):
    """Solve a cylindrical tool's tip and axis, retaining its free axial angle."""
    tip, axis = np.asarray(tool["tip_offset_m"]), np.asarray(tool["tip_axis_local"])
    wanted_tip = target_body[:3, 3] + target_body[:3, :3] @ tip
    wanted_axis = target_body[:3, :3] @ axis
    def residual(joints):
        actual = forward(joints) @ relation
        return np.r_[10 * (actual[:3, 3] + actual[:3, :3] @ tip - wanted_tip),
                     actual[:3, :3] @ axis - wanted_axis]
    result = least_squares(residual, np.clip(seed, limits[:, 0], limits[:, 1]),
                           bounds=(limits[:, 0], limits[:, 1]), max_nfev=120,
                           ftol=1e-8, xtol=1e-8, gtol=1e-8)
    actual = forward(result.x) @ relation
    error = residual(result.x)
    angle = math.acos(np.clip(np.dot(actual[:3, :3] @ axis, wanted_axis), -1., 1.))
    return result.x, bool(np.linalg.norm(error[:3]) <= 10 * position_tolerance and angle <= .02)


def place_waypoints(supported_pose, tcp_from_object, config):
    desired = supported_pose @ np.linalg.inv(tcp_from_object)
    above = desired.copy()
    above[2, 3] += config["lift_distance_m"]
    settle = config["settle_s"]
    return [(above, 0., "transport"), (desired, settle, "lower"),
            (desired, settle, "release"), (above, settle, "retreat")]


def process_waypoints(operation, parameters, tcp, body, tcp_from_object, target, config):
    """Generate absolute tool-feature poses, preserving the measured attachment."""
    frame = target.get("process_frame", {})
    tool = target.get("tool_frame", {})
    if "tip_offset_m" not in tool:
        raise PhaseMotionError("measured_tool_feature_missing", "process requires measured tip_offset_m")
    tip = np.asarray(tool["tip_offset_m"], dtype=float)
    center = np.asarray(frame["origin_m"], dtype=float)
    axis = np.asarray(frame["axis"], dtype=float)
    axis /= np.linalg.norm(axis)
    task_pour_direction = None
    if operation == "pour" and frame.get("pour_direction") is not None:
        task_pour_direction = np.asarray(frame["pour_direction"], dtype=float)
        task_pour_direction -= axis * float(np.dot(task_pour_direction, axis))
        if np.linalg.norm(task_pour_direction) < 1e-6:
            raise PhaseMotionError("pour_direction_unresolved", "pour direction is parallel to the destination axis")
        task_pour_direction /= np.linalg.norm(task_pour_direction)
        horizontal = np.cross(task_pour_direction, axis)
    else:
        horizontal = np.cross(axis, [1., 0., 0.])
        if np.linalg.norm(horizontal) < .1:
            horizontal = np.cross(axis, [0., 1., 0.])
    horizontal /= np.linalg.norm(horizontal)
    if operation == "pour":
        horizontal = Rotation.from_rotvec(axis * config.get("pour_azimuth_rad", 0.)).apply(horizontal)
    other = np.cross(axis, horizontal)
    high = center + axis * config["process_clearance_m"]
    orientation = body[:3, :3]
    values = []

    def feature(position, rotation, duration=0., stage="transport"):
        values.append((held_tool_pose(tcp_from_object, tip, position, rotation), duration, stage))

    if operation == "pour":
        tilt = float(parameters["tilt_rad"])
        if tilt > config["maximum_tilt_rad"]:
            raise PhaseMotionError("tilt_limit_exceeded", "pour angle exceeds the deployment limit")
        orientation = Rotation.from_rotvec(axis * config.get("pour_yaw_rad", 0.)).as_matrix() @ orientation
        approach_direction = -other if task_pour_direction is not None else other
        feature(high + approach_direction * config["process_clearance_m"], orientation)
        tilted = Rotation.from_rotvec(-horizontal * tilt).as_matrix() @ orientation
        feature(high, tilted)
        feature(center + axis * config["pour_lip_clearance_m"], tilted,
                float(parameters["hold_s"]) + config["settle_s"], "process")
        feature(high, tilted, stage="exit")
        feature(high + approach_direction * config["process_clearance_m"], orientation, stage="exit")
    elif operation == "stir":
        radius, depth = float(parameters["radius_m"]), float(parameters["depth_m"])
        if radius > config["maximum_stir_radius_m"] or depth > config["maximum_stir_depth_m"]:
            raise PhaseMotionError("stir_geometry_limit_exceeded", "stir radius/depth exceeds deployment bounds")
        current_tip_axis = orientation @ np.asarray(tool["tip_axis_local"], dtype=float)
        alignment, _ = Rotation.align_vectors([-axis], [current_tip_axis])
        orientation = alignment.as_matrix() @ orientation
        feature(high + horizontal * radius, orientation)
        bottom = center - axis * depth
        feature(bottom + horizontal * radius, orientation, config["settle_s"], "insert")
        requested_turns = float(parameters["turns"])
        turns = requested_turns + config.get("stir_entry_reserve_turns", .25)
        count = max(64, math.ceil(turns * 2 * math.pi / .05))
        direction = -1 if parameters.get("direction", "ccw") == "cw" else 1
        for angle in np.linspace(0., direction * turns * 2 * math.pi, count + 1)[1:]:
            feature(bottom + radius * (horizontal * math.cos(angle) + other * math.sin(angle)),
                    orientation, float(parameters["duration_s"]) * turns / requested_turns / count, "process")
        feature(high + horizontal * radius, orientation, config["settle_s"], stage="exit")
    else:
        raise PhaseMotionError("unsupported_manipulation_phase", operation)
    return values


class GripContactWindow:
    """Selected-body contact load over one control interval's physics substeps."""

    def __init__(self, world, sensors, body_path, dt):
        self.world, self.sensors, self.body_path, self.dt = world, sensors, body_path, dt
        self.begin()

    def begin(self):
        self.start = float(self.world.current_time)
        self.frames = [{} for _ in self.sensors]
        self.contact_frames = [{} for _ in self.sensors]
        self.latest = [None for _ in self.sensors]
        self.error = None

    def capture(self, _step_size=None, *, require_raw_frame=False):
        # PhysX invokes callbacks outside the caller's exception stack. Preserve
        # errors for the motion loop instead of allowing stale evidence through.
        try:
            for index, sensor in enumerate(self.sensors):
                frame = sensor.get_current_frame()
                if require_raw_frame and (
                    not isinstance(frame.get("contacts"), (list, tuple)) or "in_contact" not in frame
                ):
                    raise ValueError("raw contact data is unavailable")
                timestamp = float(frame.get("time", -1.))
                contacts = [item for item in frame.get("contacts", [])
                            if self.body_path in (item["body0"], item["body1"])]
                impulse = sum(float(np.linalg.norm(item["impulse"])) for item in contacts)
                self.latest[index] = (timestamp, bool(contacts))
                if self.start <= timestamp <= float(self.world.current_time):
                    self.frames[index][timestamp] = impulse
                    self.contact_frames[index][timestamp] = [
                        {key: (np.asarray(item[key], dtype=float).tolist()
                               if key in {"impulse", "position", "normal"} else str(item[key]))
                         for key in ("body0", "body1", "impulse", "position", "normal") if key in item}
                        for item in contacts]
        except Exception as exc:
            self.error = exc

    def valid(self):
        self.capture()
        return self.fresh_bilateral_manifolds() and all(
            sum(frames.values()) > 0 for frames in self.frames
        )

    def fresh_bilateral_manifolds(self):
        """Return whether both selected-body contact manifolds are current."""
        if self.error is not None:
            raise PhaseMotionError("contact_sampling_failed", str(self.error)) from self.error
        now = float(self.world.current_time)
        return len(self.sensors) == 2 and all(
            latest is not None and latest[1] and abs(latest[0] - now) <= self.dt * 2
            for latest in self.latest
        )

    def has_current_feedback(self, *, after=None):
        """Check that both fingers contributed a fresh frame to this interval."""
        if self.error is not None:
            raise PhaseMotionError("contact_sampling_failed", str(self.error)) from self.error
        now = float(self.world.current_time)
        return len(self.sensors) == 2 and all(
            latest is not None and latest[0] in frames and 0. <= now - latest[0] <= self.dt * 2
            and (after is None or after < latest[0])
            for latest, frames in zip(self.latest, self.frames, strict=True)
        )

    def current_unloaded(self, *, require_clear=False, whole_interval=True):
        """Judge both fingers using their latest capture and current interval."""
        return self.has_current_feedback() and all(
            frames[latest[0]] == 0.
            and (not whole_interval or all(impulse == 0. for impulse in frames.values()))
            and (not require_clear or not latest[1])
            for latest, frames in zip(self.latest, self.frames, strict=True)
        )

    def has_unilateral_load(self):
        return self.has_current_feedback(after=self.start) and sum(
            all(impulse == 0. for impulse in frames.values()) for frames in self.frames
        ) == 1

    def evidence(self):
        return {"contact_window_start_s": self.start,
                "contact_window_end_s": float(self.world.current_time),
                "selected_contact_impulse_ns": [sum(frames.values()) for frames in self.frames],
                "contact_substep_samples": [len(frames) for frames in self.frames],
                "contact_vector_convention": "sensor_reported_body_order; not net body force",
                "selected_contacts": [[{"timestamp_s": timestamp, "contacts": contacts}
                                       for timestamp, contacts in frames.items() if contacts]
                                      for frames in self.contact_frames]}


class IsaacPhaseMotion:
    """A mechanism owned by one WorkerSessionContext, without task lifecycle state."""

    def __init__(self, session, profile, artifact_root=None):
        import yaml
        from isaacsim.robot_motion.motion_generation import (
            LulaKinematicsSolver,
            interface_config_loader,
        )
        from pxr import UsdGeom

        self.session, self.profile = session, profile
        self.config = json.loads(Path(profile.motion_config_path).read_text(encoding="utf-8"))
        for key, value in self.config.items():
            if isinstance(value, bool):
                # Boolean switches (e.g. acquire_carry_as_grasped_fallback) are
                # consumed through fail-closed .get() defaults; scalar
                # positivity semantics do not apply to them.
                continue
            if isinstance(value, (int, float)) and (not math.isfinite(value) or value <= 0):
                raise PhaseMotionError("invalid_motion_configuration", f"{key} must be finite and positive")
        lower, upper = np.asarray(self.config["workspace_min_m"]), np.asarray(self.config["workspace_max_m"])
        if lower.shape != (3,) or upper.shape != (3,) or not np.isfinite([lower, upper]).all() or np.any(lower >= upper):
            raise PhaseMotionError("invalid_motion_configuration", "workspace bounds must be finite and ordered")
        acquire_transit_clearances(self.config)
        acquire_transport_orientations(self.config)
        acquire_axial_symmetry_angles(self.config)
        acquire_failure_recovery_codes(self.config)
        acquire_staging_corridors(self.config)
        acquire_route_selection(self.config)
        acquire_route_search_timeout(self.config)
        if self.config.get("acquire_timing", "waypoint") not in {"waypoint", "stage_continuous"}:
            raise PhaseMotionError("invalid_motion_configuration", "unsupported acquire timing")
        self.scene = session.resolve("lab_scene_resources")
        self.robot, self.world, self.stage = (self.scene[key] for key in ("robot", "world", "stage"))
        if not self.scene["robot_initialized"]:
            self.robot.initialize()
            self.scene["robot_initialized"] = True
        configuration = interface_config_loader.load_supported_lula_kinematics_solver_config("Franka")
        self.solver = LulaKinematicsSolver(**configuration)
        # The arm root, not the articulation root: mounted robots place
        # panda_link0 at an offset (ridgeback +0.3 m forward, +0.28 m up), and
        # the solver addresses every IK query from this base frame.
        arm_base = self.stage.GetPrimAtPath(self.robot.prim_path + "/panda_link0")
        if not arm_base.IsValid():
            raise PhaseMotionError(
                "arm_base_unavailable",
                "robot must expose a panda_link0 arm base prim below the robot root",
            )
        self.solver.set_robot_base_pose(*lula_base_pose_from_link_world(
            np.asarray(UsdGeom.Xformable(arm_base).ComputeLocalToWorldTransform(0)).T))
        self.joint_indices = [self.robot.get_dof_index(name) for name in self.solver.get_joint_names()]
        properties = self.robot.dof_properties
        self.limits = np.column_stack((properties["lower"], properties["upper"]))[self.joint_indices]
        self.spheres = yaml.safe_load(Path(configuration["robot_description_path"]).read_text())["collision_spheres"]
        self.bodies = {}
        self.payload_geometry = {}
        self.body_from_observed = {}
        # Adapter-private projection of available approach probes' variant
        # selections, keyed by candidate; consumed by the
        # simulator_truth_preselected collapse in prepare(). Freshness is
        # re-checked against scene identity inside that collapse, never by
        # wall-clock time.
        self._probe_variant_selection = {}
        hand = self.stage.GetPrimAtPath(self.robot.prim_path + "/panda_hand")
        center = self.stage.GetPrimAtPath(self.robot.prim_path + "/panda_hand/tool_center")
        if not hand.IsValid() or not center.IsValid():
            raise PhaseMotionError("tool_center_unavailable", "robot must expose the configured tool center")
        hand_world = UsdGeom.Xformable(hand).ComputeLocalToWorldTransform(0)
        center_world = UsdGeom.Xformable(center).ComputeLocalToWorldTransform(0)
        self.hand_from_tcp = np.asarray(center_world * hand_world.GetInverse()).T
        self.artifact_root = Path(artifact_root or profile.lab_root / "outputs" / "paos-observation-artifacts")
        # One command and feedback sample per rendered step; World owns the
        # configured physics substeps within that control interval.
        self.dt = float(self.world.get_rendering_dt())
        self.sensors = self.robot.get_contact_sensor()
        for sensor in self.sensors:
            sensor.initialize()
            sensor.add_raw_contact_data_to_frame()

    def joints(self):
        return np.asarray(self.robot.get_joint_positions())[self.joint_indices].copy()

    def tcp(self, joints=None):
        position, rotation = self.solver.compute_forward_kinematics("panda_hand", self.joints() if joints is None else joints)
        value = np.eye(4)
        value[:3, :3], value[:3, 3] = rotation, position
        return value @ self.hand_from_tcp

    def body(self, path):
        from isaacsim.core.prims import SingleRigidPrim
        from pxr import Usd, UsdPhysics

        if path not in self.bodies:
            prim = self.stage.GetPrimAtPath(path)
            matches = [item for item in Usd.PrimRange(prim) if item.HasAPI(UsdPhysics.RigidBodyAPI)] if prim.IsValid() else []
            if len(matches) != 1:
                raise PhaseMotionError("rigid_body_unavailable", f"expected one physical body under {path}")
            body = SingleRigidPrim(str(matches[0].GetPath()))
            body.initialize()
            self.bodies[path] = body
        return self.bodies[path]

    def body_pose(self, path):
        position, orientation = self.body(path).get_world_pose()
        return pose_matrix(position, np.roll(orientation, -1))

    def observed_pose(self, path):
        """Transport the captured visual frame using explicit physics feedback."""
        return self.body_pose(path) @ self.body_from_observed[path]

    def bind_observed_model(self, source, target, context, previous):
        from .visual_perception import LabArtifactStore

        if previous:
            relation = np.asarray(previous["body_from_observed"])
            model_pose = np.asarray(previous["observed_model_pose"])
        else:
            pose = target["object_pose"]
            model_pose = pose_matrix(pose["position_m"], pose["orientation_xyzw"])
            captured = np.asarray(context["captured_body_pose"])
            current = self.body_pose(source)
            if (np.linalg.norm(current[:3, 3] - captured[:3, 3]) > self.config["position_tolerance_m"]
                    or Rotation.from_matrix(current[:3, :3].T @ captured[:3, :3]).magnitude() > .02):
                raise PhaseMotionError("object_state_changed", "source moved after the visual capture")
            relation = np.linalg.inv(captured) @ model_pose
        self.body_from_observed[source] = relation
        store = LabArtifactStore(self.artifact_root)
        points = np.load(store.resolve_point_cloud(context["points_ref"]), allow_pickle=False)
        transform = np.linalg.inv(model_pose) @ np.asarray(context["world_from_camera"])
        local_points = points @ transform[:3, :3].T + transform[:3, 3]
        self.payload_geometry[source] = observed_point_boxes(local_points)
        return model_pose, relation

    @cached_property
    def provider_from_tcp(self):
        """Deployed provider calibration, or None when it is unavailable.

        Read from the same perception configuration that LabVisualPerception
        validates and consumes, so the collider telemetry's span axis shares
        one calibration source with qualification instead of a second copy of
        the matrix. No perception configuration, unreadable JSON, a missing
        key, or non-numeric values yield None; the span-axis derivation then
        records the identity fallback honestly in the artifact.
        """
        path = getattr(self.profile, "perception_config_path", None)
        if path is None:
            return None
        try:
            value = json.loads(Path(path).read_text(encoding="utf-8")).get("provider_from_tcp")
            return None if value is None else np.asarray(value, dtype=float)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return None

    def collider_profile_artifact(self, source, desired, scene_revision, candidate_ref):
        """Read-only cooked-collider radial profile at acquire; this never gates.

        Writes one collider-profile artifact carrying the source body's PhysX
        cooked convex vertices ring-aggregated into r(z) along the grasp span
        axis, so a diagnostic run can reconcile the commanded band against the
        composed collider (e.g. the V-HACD shoulder taper) without launching
        Kit. Any cooked-query failure is recorded honestly as status
        "unavailable"; acquire qualification is unchanged.
        """
        record = {
            "status": "unavailable", "operation": "acquire",
            "scene_revision": scene_revision, "candidate_ref": candidate_ref,
            "source_path": source,
        }
        # Outside Kit (unit tests, offline replay) no stage is attached; the
        # telemetry records that honestly instead of raising into the
        # unchanged acquire qualification.
        stage = getattr(self, "stage", None)
        if stage is None:
            record["reason"] = "no usd stage attached"
            return self._artifact("collider-profile", record)
        try:
            from pxr import Usd, UsdGeom, UsdPhysics

            from .finger_collision import (RADIAL_PROFILE_BIN_M, cooked_body_boxes,
                                           grasp_span_axis, points_within_radius,
                                           radial_profile)

            prim = stage.GetPrimAtPath(source)
            matches = [item for item in Usd.PrimRange(prim) if item.HasAPI(UsdPhysics.RigidBodyAPI)] \
                if prim.IsValid() else []
            if len(matches) != 1:
                raise ValueError(f"expected one physical body under {source}")
            _boxes, evidence = cooked_body_boxes(
                stage, matches[0], self.config["collision_margin_m"])
            record["colliders"] = [{"collider_path": item["collider_path"],
                                    "representation": item["representation"]} for item in evidence]
            cooked = [np.asarray(points, dtype=float) for item in evidence
                      for points in item.get("body_frame_convexes_m", [])]
            if not cooked:
                record["reason"] = "no physx cooked convex evidence on the source body"
                return self._artifact("collider-profile", record)
            # cooked_body_boxes composes each collider's authored transforms --
            # including ancestor mm->m scaling -- into its body-frame vertices
            # relative to this body prim (run19/run20: transporting those
            # vertices with the rigid-body pose left millimetre values in the
            # world points, because a physical rigid-body pose carries no
            # authored scale). The body prim's own USD local-to-world
            # transform carries that same authored composition, so at this
            # pre-physics-drift acquire moment LoW(body) @ body-frame points ==
            # LoW(collider) @ raw cooked points, and it is the matching world
            # transport here; the artifact self-describes this choice.
            pose = np.asarray(UsdGeom.Xformable(matches[0]).ComputeLocalToWorldTransform(0)).T
            world_points = (pose[:3, :3] @ np.concatenate(cooked, axis=0).T).T + pose[:3, 3]
            # The grasp frame follows the TCP convention, and the deployed
            # provider calibration maps TCP z to the approach axis, so the
            # span axis is the provider z axis expressed through that
            # calibration -- the same expression the qualification gate
            # anchors use. With no calibration the identity fallback
            # reproduces the historical TCP z column.
            span_axis, span_axis_source = grasp_span_axis(desired[:3, :3], self.provider_from_tcp)
            # Cooked compound bodies carry foreign geometry far from the grasp
            # axis (run19 saw rings out to ~1.7 m); r(z) telemetry is only
            # meaningful near the vessel, so points beyond vessel scale are
            # excluded before aggregation and the exclusion is recorded.
            profile_max_radius_m = 0.1
            world_points, excluded = points_within_radius(
                world_points, desired[:3, 3], span_axis, profile_max_radius_m)
            rings = radial_profile(world_points, desired[:3, 3], span_axis, RADIAL_PROFILE_BIN_M)
            return self._artifact("collider-profile", {**record, "status": "cooked",
                "world_from": "usd_local_to_world",
                "grasp_position_m": np.asarray(desired[:3, 3]).tolist(),
                "span_axis_world": np.asarray(span_axis).tolist(),
                "span_axis_source": span_axis_source,
                "bin_size_m": RADIAL_PROFILE_BIN_M,
                "profile_max_radius_m": profile_max_radius_m,
                "profile_excluded_points": excluded, "profile": rings})
        except (ValueError, RuntimeError) as exc:
            import threading
            record["reason"] = str(exc)
            # run20 saw 6/6 "unavailable" here while isolated worker-thread
            # cooks succeed and this code runs in the worker process, so the
            # live-session cause is unresolved; record the failing context.
            record["reason_context"] = {
                "thread": threading.current_thread().name,
                "error_type": type(exc).__name__,
            }
            return self._artifact("collider-profile", record)

    def _artifact(self, kind, value):
        from PhyAgentOS.utils.atomic_file import atomic_write_bytes

        path = Path(kind) / f"{uuid4().hex}.json"
        atomic_write_bytes(self.artifact_root / path, json.dumps(value, allow_nan=False, ensure_ascii=False).encode())
        return f"artifact://labutopia/{path.as_posix()}"

    @cached_property
    def finger_geometry(self):
        """Cooked convex slab bounds and prismatic joints in the body frame."""
        from itertools import product

        from pxr import UsdPhysics

        from .finger_collision import cooked_body_boxes

        def joint_pose(position, quaternion):
            return pose_matrix(list(position), [*quaternion.GetImaginary(), quaternion.GetReal()])

        geometry = []
        self.finger_geometry_evidence = []
        for number in (1, 2):
            joint = UsdPhysics.PrismaticJoint(self.stage.GetPrimAtPath(
                f"{self.robot.prim_path}/panda_hand/panda_finger_joint{number}"))
            body_path = joint.GetBody1Rel().GetTargets()[0]
            body = self.stage.GetPrimAtPath(body_path)
            parent_from_joint = joint_pose(joint.GetLocalPos0Attr().Get(), joint.GetLocalRot0Attr().Get())
            body_from_joint = joint_pose(joint.GetLocalPos1Attr().Get(), joint.GetLocalRot1Attr().Get())
            axis = {"X": 0, "Y": 1, "Z": 2}[joint.GetAxisAttr().Get()]
            try:
                boxes, evidence = cooked_body_boxes(self.stage, body, self.config["collision_margin_m"])
            except (ValueError, RuntimeError) as exc:
                raise PhaseMotionError("finger_geometry_unavailable", str(exc)) from exc
            self.finger_geometry_evidence.extend({**item, "finger_joint": number} for item in evidence)
            for lower, upper in boxes:
                local_corners = np.array([*product(*zip(lower, upper))])
                geometry.append((number, local_corners, parent_from_joint, body_from_joint, axis,
                                 (joint.GetLowerLimitAttr().Get(), joint.GetUpperLimitAttr().Get())))
        return geometry

    @cached_property
    def palm_boxes(self):
        from .finger_collision import cooked_body_boxes

        body = self.stage.GetPrimAtPath(self.robot.prim_path + "/panda_hand")
        try:
            boxes, self.palm_geometry_evidence = cooked_body_boxes(
                self.stage, body, self.config["collision_margin_m"])
        except (ValueError, RuntimeError) as exc:
            raise PhaseMotionError("palm_geometry_unavailable", str(exc)) from exc
        return boxes

    def check_final_gripper_pose(self, tcp, source_path):
        """Reject obstructed final geometry before IK; this never proves a route."""
        import carb
        from omni.physx import get_physx_scene_query_interface

        hand = tcp @ np.linalg.inv(self.hand_from_tcp)
        query = get_physx_scene_query_interface()
        robot_path = self.robot.prim_path + "/"

        def ignore(path):
            # Grasp contact with the bound source is intentional. All other
            # objects/support remain obstacles, exactly as at the grasp stage.
            return path.startswith(robot_path) or bool(source_path and (
                path == source_path or path.startswith(source_path + "/")))

        for link, boxes in (("panda_hand", self.palm_boxes), ("finger", self.finger_boxes())):
            for index, (lower, upper) in enumerate(boxes):
                center = hand[:3, 3] + hand[:3, :3] @ ((lower + upper) / 2)
                half = (upper - lower) / 2 + self.config["collision_margin_m"]
                orientation = Rotation.from_matrix(hand[:3, :3]).as_quat()
                found = collision_hits(query.overlap_box, carb.Float3(*half), carb.Float3(*center),
                                       carb.Float4(*orientation), ignore=ignore)
                if found:
                    raise PhaseMotionError("route_collision", f"final_grasp: {link} overlaps {found[0]}",
                        diagnostics={"evidence_kind": "collision_model_overlap", "frame_id": "world",
                                     "stage": "final_grasp", "checked_tcp": np.asarray(tcp).tolist(),
                                     "link": link, "obstacle_path": found[0], "primitive": "oriented_box",
                                     "center_m": center.tolist(), "half_extents_m": half.tolist(),
                                     "orientation_xyzw": orientation.tolist(), "gripper_box_index": index,
                                     "collision_margin_m": self.config["collision_margin_m"],
                                     "finger_opening_mode": "full_travel_sweep"})

    @cached_property
    def maximum_gripper_opening_m(self):
        """Derive the physical finger aperture from the composed articulation."""
        upper_by_joint = {}
        for number, _corners, _parent, _child, _axis, limits in self.finger_geometry:
            lower, upper = (float(value) for value in limits)
            if not np.isfinite([lower, upper]).all() or lower > upper:
                raise PhaseMotionError(
                    "finger_geometry_unavailable",
                    f"panda_finger_joint{number} has invalid limits {limits}",
                )
            upper_by_joint[number] = max(upper_by_joint.get(number, -math.inf), upper)
        if set(upper_by_joint) != {1, 2}:
            raise PhaseMotionError(
                "finger_geometry_unavailable",
                "Franka preparation requires both finger joint limits",
            )
        opening = sum(max(0.0, value) for value in upper_by_joint.values())
        if not math.isfinite(opening) or opening <= 0:
            raise PhaseMotionError(
                "finger_geometry_unavailable",
                "Franka finger limits do not expose a positive aperture",
            )
        return opening

    def validate_grasp_aperture(self, target):
        """Reject a Grasp Provider candidate the composed gripper cannot open around."""
        geometry = target.get("grasp_geometry")
        if not isinstance(geometry, dict) or "width_m" not in geometry:
            return None
        width = geometry["width_m"]
        if isinstance(width, bool) or not isinstance(width, (int, float)) or not math.isfinite(width) or width <= 0:
            raise PhaseMotionPreconditionError(
                "invalid_grasp_geometry",
                "candidate grasp width must be a finite positive number",
            )
        maximum = self.maximum_gripper_opening_m
        if float(width) > maximum + 1e-6:
            raise PhaseMotionPreconditionError(
                "gripper_aperture_exceeded",
                f"candidate requires {float(width):.6f} m opening; composed Franka limit is {maximum:.6f} m",
            )
        return {"required_width_m": float(width), "maximum_opening_m": maximum}

    def finger_boxes(self, measured=False):
        positions = np.asarray(self.robot.get_joint_positions()) if measured else None
        for number, corners, parent, child, axis, limits in self.finger_geometry:
            if measured:
                opening = positions[self.robot.get_dof_index(f"panda_finger_joint{number}")]
                tolerance = self.config["position_tolerance_m"]
                limits = (max(limits[0], opening - tolerance), min(limits[1], opening + tolerance))
            points = []
            for displacement in limits:
                shift = np.eye(4)
                shift[axis, 3] = displacement
                transform = parent @ shift @ np.linalg.inv(child)
                points.extend(corners @ transform[:3, :3].T + transform[:3, 3])
            points = np.asarray(points)
            yield points.min(0), points.max(0)

    def _collisions(self, joints, source_path, allow_contact, attached, tcp_from_object, support_contact=False,
                    released_pose=None, held_fingers=False):
        import carb
        from omni.physx import get_physx_scene_query_interface

        tcp = self.tcp(joints)
        if np.any(tcp[:3, 3] < self.config["workspace_min_m"]) or np.any(tcp[:3, 3] > self.config["workspace_max_m"]):
            raise PhaseMotionError("workspace_violation", "interpolated TCP is outside the configured workspace")
        query = get_physx_scene_query_interface()
        groups = []
        robot_path = self.robot.prim_path + "/"

        def ignore_robot(path):
            return path.startswith(robot_path) and path not in self.config["mount_collision_paths"]

        def reject(code, detail, **geometry):
            raise PhaseMotionError(code, detail, diagnostics={
                "evidence_kind": "collision_model_overlap", "frame_id": "world",
                "checked_joints": np.asarray(joints).tolist(), "checked_tcp": tcp.tolist(),
                "collision_margin_m": self.config["collision_margin_m"], **geometry,
            })

        def hits(center, radius, link, ignore_source=False):
            def ignore(path):
                if ignore_robot(path) or (ignore_source and (path == source_path or path.startswith(source_path + "/"))):
                    return True
                if link == "panda_link0" and path in self.config["mount_collision_paths"]:
                    return True
                return False
            found = collision_hits(query.overlap_sphere, float(radius), carb.Float3(*center), ignore=ignore)
            if found:
                reject("route_collision", f"{link} overlaps {found[0]}", link=link,
                       obstacle_path=found[0], primitive="sphere", center_m=np.asarray(center).tolist(),
                       radius_m=float(radius))

        for group in self.spheres:
            for link, spheres in group.items():
                position, rotation = self.solver.compute_forward_kinematics(link, joints)
                centers = [position + rotation @ np.array(sphere["center"]) for sphere in spheres]
                radii = [sphere["radius"] + self.config["collision_margin_m"] for sphere in spheres]
                for center, radius in zip(centers, radii, strict=True):
                    hits(center, radius, link, attached or released_pose is not None or (allow_contact and link == "panda_hand"))
                groups.append((link, centers, radii))
        # Lula omits movable fingers; use each authored collider separately.
        # Held phases use measured openings. Opening/closing sweeps full travel.
        tcp = self.tcp(joints)
        hand = tcp @ np.linalg.inv(self.hand_from_tcp)
        def ignore_finger(path):
            return ignore_robot(path) or (
                (attached or released_pose is not None or allow_contact)
                and (path == source_path or path.startswith(source_path + "/")))
        for box_index, (lower, upper) in enumerate(self.finger_boxes(measured=held_fingers)):
            finger_center = hand[:3, 3] + hand[:3, :3] @ ((lower + upper) / 2)
            finger_half = (upper - lower) / 2 + self.config["collision_margin_m"]
            found = collision_hits(query.overlap_box, carb.Float3(*finger_half), carb.Float3(*finger_center),
                                   carb.Float4(*Rotation.from_matrix(hand[:3, :3]).as_quat()), ignore=ignore_finger)
            if found:
                reject("route_collision", f"finger overlaps {found[0]}", link="finger",
                       obstacle_path=found[0], primitive="oriented_box",
                       center_m=finger_center.tolist(), half_extents_m=finger_half.tolist(),
                       orientation_xyzw=Rotation.from_matrix(hand[:3, :3]).as_quat().tolist(),
                       finger_box_index=box_index,
                       finger_opening_mode="measured" if held_fingers else "full_travel_sweep")
            for link, centers, radii in groups:
                if link not in {"panda_hand", "panda_link7"}:
                    if any(np.linalg.norm(np.maximum(np.abs(hand[:3, :3].T @ (center - finger_center)) - finger_half, 0.)) < radius
                           for center, radius in zip(centers, radii, strict=True)):
                        reject("self_collision", f"finger envelope overlaps {link}", link="finger",
                               other_link=link, primitive="oriented_box_sphere_group",
                               center_m=finger_center.tolist(), half_extents_m=finger_half.tolist(),
                               orientation_xyzw=Rotation.from_matrix(hand[:3, :3]).as_quat().tolist(),
                               finger_box_index=box_index, other_centers_m=np.asarray(centers).tolist(),
                               other_radii_m=list(radii),
                               finger_opening_mode="measured" if held_fingers else "full_travel_sweep")
        # The model's adjacent links intentionally overlap at their joints.
        # All non-adjacent groups remain checked, including the payload below.
        for i, (link, centers, radii) in enumerate(groups):
            for other_link, other_centers, other_radii in groups[i+2:]:
                for center, radius in zip(centers, radii, strict=True):
                    if any(np.linalg.norm(center - other) < radius + other_radius
                           for other, other_radius in zip(other_centers, other_radii, strict=True)):
                        reject("self_collision", f"{link} overlaps {other_link}", link=link,
                               other_link=other_link, primitive="sphere_groups",
                               centers_m=np.asarray(centers).tolist(), radii_m=list(radii),
                               other_centers_m=np.asarray(other_centers).tolist(), other_radii_m=list(other_radii))
        if attached or released_pose is not None:
            if source_path not in self.payload_geometry:
                raise PhaseMotionError("payload_geometry_unavailable", "payload has no bound observed point cloud")
            payload = self.tcp(joints) @ tcp_from_object if attached else released_pose
            quaternion = Rotation.from_matrix(payload[:3, :3]).as_quat()
            def ignore_payload(path):
                if ignore_robot(path) or path == source_path or path.startswith(source_path + "/"):
                    return True
                if (support_contact or released_pose is not None) and any(
                    prim_path_is_within(path, support)
                    for support in self.config["support_collision_paths"]
                ):
                    return True
                return False
            for lower, upper in self.payload_geometry[source_path]:
                center = payload[:3, 3] + payload[:3, :3] @ ((lower + upper) / 2)
                half = (upper - lower) / 2 + self.config["collision_margin_m"]
                found = collision_hits(query.overlap_box, carb.Float3(*half), carb.Float3(*center),
                                       carb.Float4(*quaternion), ignore=ignore_payload)
                if found:
                    raise PhaseMotionError("payload_collision",
                                           f"payload overlaps {found[0]}; center={center.tolist()}, half={half.tolist()}, TCP={tcp[:3, 3].tolist()}")
                for link, centers, radii in groups:
                    if link == "panda_hand":
                        continue  # Intentional grasp contact; fingers also touch the payload.
                    for robot_center, radius in zip(centers, radii, strict=True):
                        local = payload[:3, :3].T @ (robot_center - center)
                        if np.linalg.norm(np.maximum(np.abs(local) - half, 0.)) < radius:
                            raise PhaseMotionError("payload_robot_collision", f"payload overlaps {link}")

    def prepare(self, arguments):
        from .engine import _target_in_world

        operation = arguments.get("operation", "acquire") if arguments.get("held_invocation_ref") else "acquire"
        target = _target_in_world(arguments["manipulation_target"])
        aperture_check = self.validate_grasp_aperture(target) if operation == "acquire" else None
        source = target.get("tool_prim_path") or target["entity_prim_path"]
        previous = arguments.get("phase_route", {})
        model_pose, relation = self.bind_observed_model(source, target, arguments["observation_model"], previous)
        tcp, body = self.tcp(), self.observed_pose(source)
        tcp_from_object = np.linalg.inv(tcp) @ body
        original_return = previous.get("original_return_pose", model_pose.tolist())
        destination = target.get("destination_prim_path")
        destination_pose = self.body_pose(destination) if destination else None
        waypoints = []
        if operation == "acquire":
            grasp = target["grasp_frame"]
            desired = pose_matrix(grasp["position_m"], grasp["orientation_xyzw"])
            approach = np.asarray(target["approach_direction"]["vector"])
        elif operation == "place":
            waypoints = place_waypoints(np.asarray(original_return), tcp_from_object, self.config)
        else:
            # Receiving-vessel process features were refreshed from the current
            # observation by the Provider, not corrected from simulator truth.
            waypoints = process_waypoints(operation, arguments["parameters"], tcp, body,
                                          tcp_from_object, target, self.config)
        if operation == "acquire":
            # Read-only collider telemetry runs once, before any route search,
            # so the profile exists even when qualification later fails.
            collider_profile_ref = self.collider_profile_artifact(
                source, desired, arguments["scene_revision"], target.get("candidate_ref"))
            failures, candidates = [], []
            variants = acquire_grasp_variants(
                desired,
                approach,
                arguments["observation_model"].get("grasp_symmetry"),
                acquire_axial_symmetry_angles(self.config),
            )
            # Carry-as-grasped is a per-deployment opt-in fallback, never a silent
            # default: with joint-travel-minimizing selection the zero-reorientation
            # carry pose would otherwise silently outcompete configured world-frame
            # transport poses (e.g. keep-open-vessels-upright task semantics).
            if self.config.get("acquire_carry_as_grasped_fallback", False):
                transport_orientations = acquire_transport_orientations(self.config) + (None,)
            else:
                transport_orientations = acquire_transport_orientations(self.config)
            staging_corridors = acquire_staging_corridors(self.config)
            direct_corridors = tuple(dict.fromkeys(
                (corridor[0], 0., 0.) for corridor in staging_corridors
            ))
            policy = acquire_route_selection(self.config)
            strategies = acquire_route_strategies(self.config)
            clearances = acquire_transit_clearances(self.config)
            configured_search = (
                strategies, direct_corridors, clearances, transport_orientations, staging_corridors, variants,
            )
            if policy == "simulator_truth_preselected":
                # Try the probe's preferred search dimensions before enumerating
                # the configured alternatives. All routes qualify the same way.
                strategies = (strategies[0],)
                # Preselection honours the approach probe's validated variant
                # when its evidence identity still matches: the probe-qualified
                # azimuth and approach distance are the answer, not enumeration
                # order. Any candidate/scene drift, or a missing selection,
                # falls back to the first configured element.
                selection = getattr(self, "_probe_variant_selection", {}).get(target.get("candidate_ref"))
                if (selection is not None
                        and selection.get("scene_revision") == arguments.get("scene_revision")
                        and selection.get("axial_symmetry_angle_rad") is not None):
                    variants = tuple(variant for variant in variants
                                     if variant[0] is not None
                                     and abs(variant[0] - selection["axial_symmetry_angle_rad"]) <= 1e-9
                                     ) or (variants[0],)
                    staging_corridors = tuple(corridor for corridor in staging_corridors
                                              if abs(corridor[0] - selection["approach_distance_m"]) <= 1e-9
                                              ) or (staging_corridors[0],)
                else:
                    variants = (variants[0],)
                    staging_corridors = (staging_corridors[0],)
                # Truth-derived grasp poses are carried in their own grasp
                # orientation (carry-as-grasped), with no world-frame
                # reorientation; preselection semantics treat the truth pose
                # as the answer.
                transport_orientations = (None,)
                clearances = (clearances[0],)
                direct_corridors = tuple(dict.fromkeys(
                    (corridor[0], 0., 0.) for corridor in staging_corridors
                ))
            def count_routes(strategies, direct_corridors, clearances, orientations, corridors, variants):
                return sum(
                    len(direct_corridors) * len(variants) if strategy == "direct"
                    else len(clearances) * len(orientations) * len(corridors) * len(variants)
                    for strategy in strategies
                )

            initial_search = (
                strategies, direct_corridors, clearances, transport_orientations, staging_corridors, variants,
            )
            variant_count = count_routes(*initial_search)
            fallback_ref = None
            search_started = time.monotonic()
            search_timeout = acquire_route_search_timeout(self.config)
            search_deadline = search_started + search_timeout
            attempted_count = 0
            pruned_count = 0
            failed_prefixes = {}
            last_stage = "search"
            search_ref = self._artifact("acquire-search", {
                "status": "started", "scene_revision": arguments["scene_revision"],
                "candidate_ref": target.get("candidate_ref"), "policy": policy,
                "route_strategies": list(strategies), "variant_count": variant_count,
                "motion_authorized": False, "world_change_started": False,
            })

            def route_search_timeout(now):
                failure_counts = dict(sorted(Counter(
                    failure[-1].code for failure in failures
                ).items()))
                diagnostics = {
                    "search_ref": search_ref,
                    "attempted_count": attempted_count,
                    "pruned_count": pruned_count,
                    "variant_count": variant_count,
                    "failed_prefix_count": len(failed_prefixes),
                    "last_stage": last_stage,
                    "failure_counts": failure_counts,
                    "elapsed_s": max(0., now - search_started),
                    "timeout_s": search_timeout,
                }
                if fallback_ref is not None:
                    diagnostics["fallback_ref"] = fallback_ref
                timeout_ref = self._artifact("acquire-search", {
                    **diagnostics,
                    "status": "unavailable",
                    "failure_code": "route_search_timeout",
                    "scene_revision": arguments["scene_revision"],
                    "candidate_ref": target.get("candidate_ref"),
                    "motion_authorized": False,
                    "world_change_started": False,
                })
                diagnostics["timeout_evidence_ref"] = timeout_ref
                raise PhaseMotionError(
                    "route_search_timeout",
                    f"acquire route search exceeded {search_timeout:.3f}s after "
                    f"{attempted_count}/{variant_count} variants; last_stage={last_stage}",
                    diagnostics=diagnostics,
                )

            def searches():
                nonlocal fallback_ref, variant_count
                yield initial_search, policy == "first_feasible"
                if policy == "simulator_truth_preselected":
                    now = time.monotonic()
                    if now >= search_deadline:
                        route_search_timeout(now)
                    fallback_count = count_routes(*configured_search)
                    variant_count += fallback_count
                    fallback_ref = self._artifact("acquire-search", {
                        "search_ref": search_ref, "stage": "search", "status": "fallback",
                        "scene_revision": arguments["scene_revision"], "candidate_ref": target.get("candidate_ref"),
                        "policy": "first_feasible", "route_strategies": list(configured_search[0]),
                        "variant_count": fallback_count, "attempted_count": attempted_count,
                        "reason": "preselected_route_unavailable",
                        "motion_authorized": False, "world_change_started": False,
                    })
                    yield configured_search, True

            ordered_strategies = (
                (strategy, dimensions, first_feasible)
                for (route_strategies, *dimensions), first_feasible in searches()
                for strategy in route_strategies
            )
            for strategy, dimensions, first_feasible in ordered_strategies:
                direct_corridors, clearances, transport_orientations, staging_corridors, variants = dimensions
                strategy_candidates = []
                if strategy == "direct":
                    combinations = (
                        (-1, None, -1, None, corridor_order, corridor, symmetry_order, variant)
                        for (corridor_order, corridor), (symmetry_order, variant)
                        in product(enumerate(direct_corridors), enumerate(variants))
                    )
                else:
                    combinations = (
                        (clearance_order, clearance, transport_order, transport_quaternion,
                         corridor_order, corridor, symmetry_order, variant)
                        for (transport_order, transport_quaternion), (clearance_order, clearance),
                        (corridor_order, corridor), (symmetry_order, variant)
                        in product(enumerate(transport_orientations), enumerate(clearances),
                                   enumerate(staging_corridors), enumerate(variants))
                    )
                for (clearance_order, clearance, transport_order, transport_quaternion,
                     corridor_order, corridor, symmetry_order,
                     (symmetry_angle, variant_desired, variant_approach)) in combinations:
                    now = time.monotonic()
                    if now >= search_deadline:
                        route_search_timeout(now)
                    started = now
                    attempt = {"search_ref": search_ref, "route_strategy": strategy,
                               "clearance_m": clearance, "transport_order": transport_order,
                               "corridor_order": corridor_order,
                               "axial_symmetry_angle_rad": symmetry_angle,
                               "motion_authorized": False, "world_change_started": False}
                    if fallback_ref is not None:
                        attempt["fallback_ref"] = fallback_ref
                    candidate_relation = np.linalg.inv(variant_desired) @ body
                    prefix_by_stage = {}
                    attempt_stage = "route"
                    progress = None
                    try:
                        if strategy == "direct":
                            candidate_waypoints = acquire_direct_route_waypoints(
                                tcp, variant_desired, variant_approach, corridor, self.config,
                            )
                        else:
                            candidate_waypoints = acquire_route_waypoints(
                                tcp, variant_desired, variant_approach, clearance,
                                transport_quaternion, corridor, self.config,
                            )
                        waypoint_prefixes = tuple(_acquire_waypoint_prefixes(candidate_waypoints))
                        prefix_by_stage = dict(waypoint_prefixes)
                        matched_prefix = next((
                            (stage, failed_prefixes[prefix])
                            for stage, prefix in waypoint_prefixes
                            if prefix in failed_prefixes
                        ), None)
                        if matched_prefix is not None:
                            pruned_stage, source_failure = matched_prefix
                            pruned_count += 1
                            last_stage = pruned_stage
                            self._artifact("acquire-search", {
                                **attempt,
                                "stage": pruned_stage,
                                "status": "pruned",
                                "pruned_count": pruned_count,
                                "source_failure_code": source_failure["failure_code"],
                                "source_attempt_ordinal": source_failure["attempt_ordinal"],
                                "elapsed_s": time.monotonic() - started,
                            })
                            continue
                        attempted_count += 1
                        attempt["attempt_ordinal"] = attempted_count
                        attempt_stage = "route"

                        def progress(stage, status, **details):
                            nonlocal attempt_stage, last_stage
                            attempt_stage = stage
                            last_stage = stage
                            now = time.monotonic()
                            if now >= search_deadline:
                                route_search_timeout(now)
                            self._artifact("acquire-search", {
                                **attempt,
                                "stage": stage,
                                "status": status,
                                "elapsed_s": now - started,
                                **details,
                            })

                        progress("route", "started")
                        candidate = self.qualify(
                            candidate_waypoints, source, candidate_relation, operation,
                            np.asarray(original_return), progress=progress,
                        )
                        approach_distance, staging_backoff, tangential_offset = corridor
                        candidate["acquire_route_strategy"] = strategy
                        candidate["acquire_approach_distance_m"] = approach_distance
                        candidate["acquire_staging_backoff_m"] = staging_backoff
                        candidate["acquire_staging_tangential_offset_m"] = tangential_offset
                        if strategy == "staged":
                            candidate["acquire_transit_clearance_m"] = clearance
                            # None records carry-as-grasped: the route carries the
                            # grasp orientation instead of a world-frame quaternion.
                            candidate["acquire_transport_orientation_xyzw"] = (
                                None if transport_quaternion is None else list(transport_quaternion)
                            )
                        if symmetry_angle is not None:
                            candidate["acquire_axial_symmetry_angle_rad"] = symmetry_angle
                        candidate_target = deepcopy(target)
                        candidate_target["grasp_frame"]["position_m"] = variant_desired[:3, 3].tolist()
                        candidate_target["grasp_frame"]["orientation_xyzw"] = Rotation.from_matrix(
                            variant_desired[:3, :3]
                        ).as_quat().tolist()
                        candidate_target["approach_direction"]["vector"] = variant_approach.tolist()
                        strategy_candidates.append((
                            route_joint_travel(candidate), clearance_order, transport_order,
                            corridor_order, symmetry_order, candidate, candidate_target, candidate_relation,
                        ))
                        progress("route", "available")
                        if first_feasible:
                            break
                    except PhaseMotionError as exc:
                        if exc.code == "route_search_timeout":
                            raise
                        failed_stage = attempt_stage
                        failed_prefix = prefix_by_stage.get(failed_stage)
                        if failed_prefix is not None:
                            failed_prefixes.setdefault(failed_prefix, {
                                "failure_code": exc.code,
                                "attempt_ordinal": attempt.get("attempt_ordinal"),
                                "stage": failed_stage,
                            })
                        failures.append((strategy, clearance, transport_order, corridor_order,
                                         symmetry_angle, exc))
                        if progress is not None:
                            progress("route", "unavailable", failure_code=exc.code, error=str(exc),
                                     collision_diagnostic=exc.diagnostics)
                if strategy_candidates:
                    candidates = strategy_candidates
                    break
            if not candidates:
                if not failures:
                    raise PhaseMotionError("route_unavailable", "no acquire route variant was configured")
                codes = {failure[-1].code for failure in failures}
                representative = failures[0][-1]
                failure_code = representative.code if len(codes) == 1 else "route_unavailable"
                details = acquire_failure_summary(failures)
                if pruned_count:
                    details += f"; pruned_routes={pruned_count}"
                raise PhaseMotionError(failure_code, details, diagnostics={
                    "search_ref": search_ref,
                    "attempted_count": attempted_count,
                    "pruned_count": pruned_count,
                    "variant_count": variant_count,
                    "failed_prefix_count": len(failed_prefixes),
                    **({"fallback_ref": fallback_ref} if fallback_ref is not None else {}),
                    "motion_authorized": False,
                    "world_change_started": False,
                }) from representative
            selected = min(candidates, key=lambda item: item[:5])
            route, target, tcp_from_object = selected[5:]
            route.update(
                acquire_route_selection=policy,
                acquire_search_ref=search_ref,
                acquire_route_attempted_count=attempted_count,
                acquire_route_pruned_count=pruned_count,
                collider_profile_ref=collider_profile_ref,
            )
            if fallback_ref is not None:
                route["acquire_search_fallback_ref"] = fallback_ref
        elif operation == "pour":
            clearance_limit = self.profile.alignment_tolerance_m - self.config["position_tolerance_m"]
            clearances = sorted({self.config["pour_lip_clearance_m"], clearance_limit})
            failures, candidates = [], []
            centered = []

            def qualify_pour(points, clearance, yaw, azimuth, offset):
                try:
                    candidate = self.qualify(points, source, tcp_from_object, operation, np.asarray(original_return))
                    candidate.update(pour_lip_clearance_m=clearance, pour_yaw_rad=yaw,
                                     pour_azimuth_rad=azimuth, pour_lip_offset_m=offset.tolist(),
                                     pour_retreat_strategy="same_side_ingress")
                    return candidate
                except PhaseMotionError as exc:
                    failures.append(f"clearance={clearance}, yaw={yaw}, azimuth={azimuth}, "
                                    f"offset_m={offset.tolist()}: {exc}")
                    return None

            for clearance, yaw, azimuth in product(clearances, (0., -math.pi / 2, math.pi / 2),
                                                   (0., math.pi, -math.pi / 2, math.pi / 2)):
                if clearance > clearance_limit:
                    continue
                candidate_config = {**self.config, "pour_lip_clearance_m": clearance, "pour_yaw_rad": yaw, "pour_azimuth_rad": azimuth}
                candidate_waypoints = process_waypoints(operation, arguments["parameters"], tcp, body,
                                                       tcp_from_object, target, candidate_config)
                centered.append((clearance, yaw, azimuth, candidate_waypoints))
                candidate = qualify_pour(candidate_waypoints, clearance, yaw, azimuth, np.zeros(3))
                if candidate is not None:
                    candidates.append(candidate)
            if not candidates:
                center = np.asarray(target["process_frame"]["origin_m"], dtype=float)
                axis = np.asarray(target["process_frame"]["axis"], dtype=float)
                axis /= np.linalg.norm(axis)
                for clearance, yaw, azimuth, points in centered:
                    radius_squared = clearance_limit ** 2 - clearance ** 2
                    if clearance_limit <= 0 or radius_squared <= 0:
                        continue
                    process_pose = next(pose for pose, _, stage in points if stage == "process")
                    bottle_side = (process_pose @ tcp_from_object)[:3, 3] - center
                    bottle_side -= axis * float(np.dot(bottle_side, axis))
                    side_norm = float(np.linalg.norm(bottle_side))
                    if side_norm < 1e-9:
                        continue
                    bottle_side /= side_norm
                    tangent = np.cross(axis, bottle_side)
                    for direction in (bottle_side, tangent, -tangent):
                        offset = direction * math.sqrt(radius_squared)
                        shifted = [(pose.copy(), hold, stage) for pose, hold, stage in points]
                        for pose, _, stage in shifted:
                            if stage == "process":
                                pose[:3, 3] += offset
                        candidate = qualify_pour(shifted, clearance, yaw, azimuth, offset)
                        if candidate is not None:
                            candidates.append(candidate)
                            break
                    if candidates:
                        break
            if not candidates:
                raise PhaseMotionError("pour_route_unavailable", "\n".join(failures) or "lip clearance exceeds alignment tolerance")
            route = min(candidates, key=lambda item: (abs(item["pour_yaw_rad"]), -item["pour_lip_clearance_m"], float(np.abs(np.diff(
                np.asarray([item["start_joints"], *[point["joints"] for point in item["steps"]]]), axis=0)).sum())))
        else:
            route = self.qualify(waypoints, source, tcp_from_object, operation, np.asarray(original_return))
        route.update(operation=operation, scene_revision=arguments["scene_revision"],
                     original_return_pose=original_return, start_object_pose=self.body_pose(source).tolist(),
                     observed_model_pose=model_pose.tolist(), body_from_observed=relation.tolist(),
                     tcp_from_object=tcp_from_object.tolist(), source_path=source, target=target,
                     start_destination_pose=destination_pose.tolist() if destination_pose is not None else None)
        if aperture_check is not None:
            route["gripper_aperture_check"] = aperture_check
        if operation == "acquire" and self.config.get("acquire_timing") == "stage_continuous":
            self._time_acquire_route(route)
        physics_ref = getattr(self, "scene", {}).get("physics_evidence_ref")
        if physics_ref:
            route["physics_evidence_ref"] = physics_ref
        evidence = self._artifact("readiness", {"captured_at": datetime.now(timezone.utc).isoformat(),
                                  "scene_revision": arguments["scene_revision"], "motion_authorized": False,
                                  "checks": {"kinematic": "pass", "collision": "pass", "workspace": "pass"},
                                  "route": route})
        return route, evidence

    def _time_acquire_route(self, route):
        """Qualify the actual stage-continuous samples before Action admission.

        Interpolation can leave the original piecewise path: check its complete
        swept joint segments, not just the original IK knots. No world stepping.
        """
        previous = np.asarray(route["start_joints"])
        relation = np.asarray(route["tcp_from_object"])
        supported = np.asarray(route["original_return_pose"])
        timed = []
        for stage, group in groupby(route["steps"], key=lambda point: point["stage"]):
            points = list(group)
            if stage in {"open", "close"}:
                timed.extend(points)
                previous = np.asarray(points[-1]["joints"])
                continue
            samples = continuous_joint_path(
                [previous, *[point["joints"] for point in points]], self.dt, 0.,
                self.config["joint_velocity_rad_s"], self.config["joint_acceleration_rad_s2"], ease_endpoints=True)
            if len(timed) + len(samples) > self.config["max_execution_steps"]:
                raise PhaseMotionError("execution_bound_reached", "retimed acquire exceeds step budget")
            if not np.isfinite(samples).all() or np.any(samples < self.limits[:, 0]) or np.any(samples > self.limits[:, 1]):
                raise PhaseMotionError("joint_limit_violation", f"retimed {stage} exceeds joint limits")
            for joints in samples:
                count = max(1, math.ceil(float(np.max(np.abs(joints - previous))) / self.config["joint_step_rad"]))
                for checked in np.linspace(previous, joints, count + 1)[1:]:
                    tcp = self.tcp(checked)
                    if (np.any(tcp[:3, 3] < self.config["workspace_min_m"])
                            or np.any(tcp[:3, 3] > self.config["workspace_max_m"])):
                        raise PhaseMotionError("workspace_violation", f"retimed TCP outside workspace in {stage}")
                    support = support_contact_allowed(stage, tcp @ relation, supported, self.config["placement_tolerance_m"])
                    self._collisions(checked, route["source_path"], points[0]["allow_contact"],
                                     points[0]["attached"], relation, support)
                timed.append({**points[0], "joints": joints.tolist(), "hold_s": 0., "continuous": True})
                previous = joints
            timed[-1]["hold_s"] = sum(point["hold_s"] for point in points)
        route["execution_steps"] = timed
        route["execution_dt_s"] = self.dt
        route["timing"] = {"method": "stage_continuous", "scope": "planner_constrained",
                           "sample_count": len(timed),
                           "nominal_arm_duration_s": len(timed) * self.dt + sum(p["hold_s"] for p in timed),
                           "closure_duration": "contact_dependent"}

    def qualify(
        self,
        waypoints,
        source,
        tcp_from_object,
        operation,
        supported_pose=None,
        tool_frame=None,
        *,
        initial_joints=None,
        initial_pose=None,
        progress=None,
    ):
        joints = self.joints() if initial_joints is None else np.asarray(initial_joints, dtype=float).copy()
        initial = joints.copy()
        previous_pose = self.tcp(joints) if initial_pose is None else np.asarray(initial_pose, dtype=float).copy()
        if (joints.shape != (self.limits.shape[0],) or not np.isfinite(joints).all()
                or previous_pose.shape != (4, 4) or not np.isfinite(previous_pose).all()):
            raise PhaseMotionError(
                "invalid_initial_motion_state",
                "route qualification requires finite initial joints and TCP pose",
            )
        if initial_pose is not None:
            measured_initial = self.tcp(joints)
            position_error = float(np.linalg.norm(measured_initial[:3, 3] - previous_pose[:3, 3]))
            orientation_error = Rotation.from_matrix(
                measured_initial[:3, :3].T @ previous_pose[:3, :3]
            ).magnitude()
            if (position_error > self.config["position_tolerance_m"]
                    or orientation_error > .02):
                raise PhaseMotionError(
                    "invalid_initial_motion_state",
                    "seed joints and TCP pose do not describe the same kinematic state",
                )
        steps = []
        for pose, hold_s, stage in waypoints:
            if progress is not None:
                progress(stage, "started")
            contact = stage in {"grasp", "close", "lift", "lower", "release", "retreat"}
            attached = (operation != "acquire" and stage not in {"release", "retreat"}) or stage == "lift"
            for sample in interpolate_pose(previous_pose, pose):
                if np.any(sample[:3, 3] < self.config["workspace_min_m"]) or np.any(sample[:3, 3] > self.config["workspace_max_m"]):
                    raise PhaseMotionError("workspace_violation", f"TCP outside workspace in {stage}")
                hand = sample @ np.linalg.inv(self.hand_from_tcp)
                primary_goal, primary_success = self.solver.compute_inverse_kinematics("panda_hand", hand[:3, 3],
                    np.roll(Rotation.from_matrix(hand[:3, :3]).as_quat(), 1), warm_start=joints,
                    position_tolerance=self.config["position_tolerance_m"], orientation_tolerance=.02)
                maximum_delta = self.config["maximum_waypoint_joint_delta_rad"]
                primary_delta = joint_delta(joints, primary_goal)
                primary_finite = primary_delta < math.inf
                place_limit_failure = (operation == "place" and primary_success and primary_finite
                                       and (np.any(primary_goal < self.limits[:, 0])
                                            or np.any(primary_goal > self.limits[:, 1])))
                force_local = operation == "stir" and stage == "process"
                goal, success = primary_goal, bool(primary_success)
                if not primary_success or primary_delta > maximum_delta or force_local or place_limit_failure:
                    local_goal, local_success = local_inverse_kinematics(
                        self.tcp, sample, joints, self.limits, self.config["position_tolerance_m"])
                    local_delta = joint_delta(joints, local_goal)
                    if local_success and local_delta <= maximum_delta:
                        goal, success = local_goal, True
                    elif place_limit_failure:
                        raise PhaseMotionError("joint_limit_violation", stage)
                    elif (primary_success and primary_finite and primary_delta > maximum_delta
                          and not force_local and tool_frame is None):
                        raise PhaseMotionError(
                            "ik_discontinuity",
                            f"{stage}: primary IK joint delta {primary_delta:.6f} rad exceeds "
                            f"configured maximum {maximum_delta:.6f} rad and nearby IK did not "
                            f"produce a continuous solution (nearby delta={local_delta:.6f} rad); "
                            f"seed joints={joints.tolist()}, target TCP={sample[:3, 3].tolist()}",
                        )
                    else:
                        goal, success = local_goal, False
                if tool_frame is not None:
                    goal, success = local_tool_inverse_kinematics(
                        self.tcp, sample @ tcp_from_object, tcp_from_object, tool_frame,
                        joints, self.limits, self.config["position_tolerance_m"])
                    tool_delta = joint_delta(joints, goal)
                    if success and tool_delta > maximum_delta:
                        raise PhaseMotionError(
                            "ik_discontinuity",
                            f"{stage}: tool-feature IK joint delta {tool_delta:.6f} rad exceeds "
                            f"configured maximum {maximum_delta:.6f} rad",
                        )
                if not success or not np.isfinite(goal).all():
                    raise PhaseMotionError("inverse_kinematics_failed",
                                           f"no solution in {stage}: TCP={sample.tolist()}")
                if np.any(goal < self.limits[:, 0]) or np.any(goal > self.limits[:, 1]):
                    raise PhaseMotionError("joint_limit_violation", stage)
                count = max(1, math.ceil(float(np.max(np.abs(goal - joints))) / self.config["joint_step_rad"]))
                for value in np.linspace(joints, goal, count + 1)[1:]:
                    support_contact = support_contact_allowed(stage, self.tcp(value) @ tcp_from_object,
                                                              supported_pose, self.config["placement_tolerance_m"])
                    if stage in {"release", "retreat"}:
                        # The live scene still holds the object at its initial
                        # pose. Qualify the released body at the planned support
                        # pose, without moving any simulator object.
                        self._collisions(value, source, contact, attached, tcp_from_object, support_contact,
                                         released_pose=supported_pose)
                    else:
                        try:
                            self._collisions(value, source, contact, attached, tcp_from_object, support_contact,
                                             held_fingers=attached and operation != "acquire")
                        except PhaseMotionError as exc:
                            checked_tcp = self.tcp(value)
                            raise PhaseMotionError(
                                exc.code,
                                f"{stage}: expected TCP={sample[:3, 3].tolist()}, "
                                f"goal TCP={self.tcp(goal)[:3, 3].tolist()}, "
                                f"checked TCP={checked_tcp[:3, 3].tolist()}, "
                                f"checked joints={value.tolist()}, "
                                f"joint delta={joint_delta(joints, goal)}; {exc}",
                                diagnostics=exc.diagnostics,
                            ) from exc
                # Collision sampling is denser than the commanded path. Keep
                # its checks without making the arm stop at every check point.
                steps.append({"joints": goal.tolist(), "stage": stage, "hold_s": 0.,
                              "allow_contact": contact, "attached": attached, "support_contact": bool(support_contact)})
                joints = goal
            steps[-1]["hold_s"] += hold_s
            previous_pose = pose
            if progress is not None:
                progress(stage, "completed", qualified_steps=len(steps))
        return {"start_joints": initial.tolist(), "steps": steps}

    def _sample_terminal_arm_branches(self, variant_desired, source, candidate_relation,
                                      seed_joints, seed_count):
        """Sample whole-arm IK branches at one final grasp pose; never proves a route.

        Returns a summary with ``solution_count`` (IK solutions found within
        joint limits), ``collision_free_count`` and up to three collision-free
        joint vectors for branch-preferred pre-grasp seeding. Zero solutions
        is reported without any feasibility conclusion.
        """
        hand = variant_desired @ np.linalg.inv(self.hand_from_tcp)
        position = hand[:3, 3]
        quaternion = np.roll(Rotation.from_matrix(hand[:3, :3]).as_quat(), 1)
        solution_count = 0
        collision_free = []
        last_detail, last_diagnostics = "", None
        for warm in deterministic_ik_seeds(seed_joints, self.limits, seed_count):
            joints, success = self.solver.compute_inverse_kinematics(
                "panda_hand", position, quaternion,
                warm_start=warm,
                position_tolerance=self.config["position_tolerance_m"],
                orientation_tolerance=.02,
            )
            joints = np.asarray(joints, dtype=float)
            if (not success or joints.shape != self.limits.shape[:1]
                    or not np.isfinite(joints).all()
                    or np.any(joints < self.limits[:, 0]) or np.any(joints > self.limits[:, 1])):
                continue
            solution_count += 1
            try:
                self._collisions(joints, source, False, False, candidate_relation, False)
            except PhaseMotionError as exc:
                last_detail, last_diagnostics = str(exc), exc.diagnostics
                continue
            collision_free.append(joints)
        return {
            "solution_count": solution_count,
            "collision_free_count": len(collision_free),
            "collision_free_joints": collision_free[:3],
            "last_collision_detail": last_detail,
            "last_collision_diagnostics": last_diagnostics,
        }

    def qualify_grasp_approach(self, arguments):
        """Probe final grasp orientation and its short approach without motion.

        The probe deliberately does not claim a complete route.  It admits a
        candidate only when one geometry-equivalent final orientation has a
        collision-free pre-grasp pose and a continuous, collision-free short
        approach/close segment.  Full acquire preparation still rechecks the
        complete route from the measured articulation state.

        Whole-arm terminal sampling runs before the distance loop: when every
        sampled IK branch at a variant's final grasp pose collides, that
        variant is rejected as terminally doomed instead of spending corridor
        enumeration on a fixed fatal endpoint. Surviving collision-free
        branches seed the pre-grasp IK so the validated chain connects to a
        feasible terminal branch.
        """
        from .engine import _target_in_world

        target = _target_in_world(arguments["manipulation_target"])
        self.validate_grasp_aperture(target)
        source = target.get("tool_prim_path") or target["entity_prim_path"]
        _model_pose, _relation = self.bind_observed_model(
            source, target, arguments["observation_model"], {}
        )
        body = self.observed_pose(source)
        grasp = target["grasp_frame"]
        desired = pose_matrix(grasp["position_m"], grasp["orientation_xyzw"])
        approach = np.asarray(target["approach_direction"]["vector"], dtype=float)
        variants = acquire_grasp_variants(
            desired,
            approach,
            arguments["observation_model"].get("grasp_symmetry"),
            acquire_axial_symmetry_angles(self.config),
        )
        approach_distances = tuple(dict.fromkeys(
            corridor[0] for corridor in acquire_staging_corridors(self.config)
        ))
        seed_joints = self.joints()
        failures = []
        candidates = []
        attempts = []
        terminal_samples = []
        terminal_seed_count = acquire_probe_terminal_seed_count(self.config)
        identity = {key: arguments[key] for key in (
            "candidate_ref", "observation_ref", "scene_revision", "frame_id", "calibration_ref"
        )}
        for symmetry_order, (symmetry_angle, variant_desired, variant_approach) in enumerate(variants):
            direction = np.asarray(variant_approach, dtype=float)
            norm = float(np.linalg.norm(direction))
            if not math.isfinite(norm) or norm <= 1e-9:
                failures.append((symmetry_angle, None, PhaseMotionError(
                    "invalid_grasp_approach", "grasp approach direction is not finite and non-zero"
                )))
                continue
            direction /= norm
            candidate_relation = np.linalg.inv(variant_desired) @ body
            final_error = None
            try:
                self.check_final_gripper_pose(variant_desired, source)
            except PhaseMotionError as exc:
                final_error = exc
            terminal = None
            branch_seeds = []
            for distance_order, distance in enumerate(approach_distances):
                pre = variant_desired.copy()
                pre[:3, 3] -= direction * distance
                attempt = {
                    "axial_symmetry_angle_rad": symmetry_angle,
                    "approach_distance_m": distance,
                    "grasp_position_world_m": variant_desired[:3, 3].tolist(),
                    "grasp_pose_world": variant_desired.tolist(),
                    "pregrasp_position_world_m": pre[:3, 3].tolist(),
                    "approach_direction_world": direction.tolist(),
                }
                try:
                    if final_error is not None:
                        raise final_error
                    if (np.any(pre[:3, 3] < self.config["workspace_min_m"])
                            or np.any(pre[:3, 3] > self.config["workspace_max_m"])):
                        raise PhaseMotionError(
                            "workspace_violation",
                            f"pre-grasp TCP={pre[:3, 3].tolist()} outside world workspace "
                            f"min={self.config['workspace_min_m']}, max={self.config['workspace_max_m']}",
                        )
                    if terminal is None:
                        terminal = self._sample_terminal_arm_branches(
                            variant_desired, source, candidate_relation, seed_joints, terminal_seed_count
                        )
                        terminal_samples.append({
                            "axial_symmetry_angle_rad": symmetry_angle,
                            "solution_count": terminal["solution_count"],
                            "collision_free_count": terminal["collision_free_count"],
                        })
                        branch_seeds = terminal["collision_free_joints"]
                        if terminal["solution_count"] > 0 and terminal["collision_free_count"] == 0:
                            raise PhaseMotionError(
                                "grasp_terminal_arm_infeasible",
                                f"terminal grasp pose sampled {terminal['solution_count']} whole-arm IK "
                                f"branches and every branch collides: {terminal['last_collision_detail']}; "
                                f"corridor enumeration cannot change the fixed final pose",
                                diagnostics=terminal["last_collision_diagnostics"],
                            )
                    hand = pre @ np.linalg.inv(self.hand_from_tcp)
                    pre_joints, success = self.solver.compute_inverse_kinematics(
                        "panda_hand",
                        hand[:3, 3],
                        np.roll(Rotation.from_matrix(hand[:3, :3]).as_quat(), 1),
                        warm_start=branch_seeds[0] if branch_seeds else seed_joints,
                        position_tolerance=self.config["position_tolerance_m"],
                        orientation_tolerance=.02,
                    )
                    pre_joints = np.asarray(pre_joints, dtype=float)
                    if not success or pre_joints.shape != seed_joints.shape or not np.isfinite(pre_joints).all():
                        raise PhaseMotionError(
                            "inverse_kinematics_failed",
                            f"no pre-grasp IK solution: TCP={pre[:3, 3].tolist()}",
                        )
                    if np.any(pre_joints < self.limits[:, 0]) or np.any(pre_joints > self.limits[:, 1]):
                        raise PhaseMotionError("joint_limit_violation", "pre-grasp")
                    self._collisions(
                        pre_joints,
                        source,
                        False,
                        False,
                        candidate_relation,
                        False,
                    )
                    route = self.qualify(
                        [
                            (variant_desired, 0., "grasp"),
                            (variant_desired, 0., "close"),
                        ],
                        source,
                        candidate_relation,
                        "acquire",
                        initial_joints=pre_joints,
                        initial_pose=pre,
                    )
                    candidates.append((
                        route_joint_travel(route),
                        symmetry_order,
                        distance_order,
                        symmetry_angle,
                        distance,
                        route,
                    ))
                    attempt["status"] = "available"
                except PhaseMotionError as exc:
                    failures.append((symmetry_angle, distance, exc))
                    attempt.update(status="unavailable", failure_code=exc.code, error=str(exc))
                    if exc.diagnostics is not None:
                        attempt["collision_diagnostic"] = exc.diagnostics
                attempts.append(attempt)
        evidence_context = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            **identity,
            "motion_authorized": False,
            "world_change_started": False,
            "workspace_frame_id": "world",
            "workspace_min_m": self.config["workspace_min_m"],
            "workspace_max_m": self.config["workspace_max_m"],
            "finger_geometry_evidence": getattr(self, "finger_geometry_evidence", []),
            "palm_geometry_evidence": getattr(self, "palm_geometry_evidence", []),
            "attempts": attempts,
            "terminal_sampling": terminal_samples,
        }
        if not candidates:
            counts = Counter(exc.code for _angle, _distance, exc in failures)
            examples = {}
            for angle, distance, exc in failures:
                examples.setdefault(exc.code, (angle, distance, str(exc)))
            detail = "; ".join(
                f"{code} count={counts[code]}; example axial_angle={examples[code][0]}, "
                f"approach_distance={examples[code][1]}: {examples[code][2][:400]}"
                for code in sorted(counts)
            ) or "no grasp approach variant was configured"
            final_count = sum(
                (attempt.get("collision_diagnostic") or {}).get("stage") == "final_grasp"
                for attempt in attempts
            )
            public_detail = "; ".join(f"{code} count={counts[code]}" for code in sorted(counts))
            if final_count:
                public_detail += f"; final_grasp rejected approaches={final_count}"
            terminal_count = sum(
                attempt.get("failure_code") == "grasp_terminal_arm_infeasible" for attempt in attempts
            )
            if terminal_count:
                public_detail += f"; terminal_arm_infeasible variants={terminal_count}"
            evidence = self._artifact("grasp-approach-feasibility", {
                **evidence_context,
                "status": "unavailable",
                "failure_code": "grasp_approach_unavailable",
                "failure_counts": dict(sorted(counts.items())),
                "error": detail,
            })
            return {
                "status": "unavailable",
                "candidate_ref": arguments["candidate_ref"],
                "observation_ref": arguments["observation_ref"],
                "scene_revision": arguments["scene_revision"],
                "frame_id": arguments["frame_id"],
                "calibration_ref": arguments["calibration_ref"],
                "feasibility_ref": evidence,
                "failure_code": "grasp_approach_unavailable",
                "error": public_detail or "no grasp approach variant was configured",
                "motion_authorized": False,
                "world_change_started": False,
            }
        selected = min(candidates, key=lambda item: item[:3])
        _, _, _, angle, distance, route = selected
        # Adapter-private projection consumed by the simulator_truth_preselected
        # collapse: the probe-validated variant is the preselected answer, and
        # its freshness is re-checked there against candidate and scene identity.
        if not isinstance(getattr(self, "_probe_variant_selection", None), dict):
            self._probe_variant_selection = {}
        self._probe_variant_selection[arguments["candidate_ref"]] = {
            "scene_revision": arguments["scene_revision"],
            "axial_symmetry_angle_rad": angle,
            "approach_distance_m": distance,
        }
        evidence = self._artifact("grasp-approach-feasibility", {
            **evidence_context,
            "status": "available",
            "selected_axial_symmetry_angle_rad": angle,
            "selected_approach_distance_m": distance,
            "checks": {
                "pregrasp_ik": "pass",
                "short_approach_continuity": "pass",
                "workspace": "pass",
                "collision": "pass",
            },
            "route": route,
        })
        return {
            "status": "available",
            "candidate_ref": arguments["candidate_ref"],
            "observation_ref": arguments["observation_ref"],
            "scene_revision": arguments["scene_revision"],
            "frame_id": arguments["frame_id"],
            "calibration_ref": arguments["calibration_ref"],
            "feasibility_ref": evidence,
            "selected_axial_symmetry_angle_rad": angle,
            "selected_approach_distance_m": distance,
            "motion_authorized": False,
            "world_change_started": False,
        }

    def execute(self, arguments, cancel):
        """Record the existing rendered steps without advancing extra physics."""
        cameras = self.session.resolve("camera_registry")
        if not cameras:
            return self._execute(arguments, cancel, lambda _stage: None)
        from .engine import _EpisodeVideoRecorder

        try:
            import cv2
        except ImportError:
            result = self._execute(arguments, cancel, lambda _stage: None)
            result["video_error"] = "opencv_unavailable"
            return result
        relative = Path("phase-video") / f"{uuid4().hex}.mp4"
        recorder = _EpisodeVideoRecorder(self.artifact_root / relative, cv2, np, fps=1 / self.dt)
        camera_error = None

        def record_frame(stage):
            nonlocal camera_error
            try:
                recorder.write({ref: camera.get_rgba() for ref, camera in cameras.items()},
                               (f"{arguments['operation']}: {stage}", f"simulation time: {self.world.current_time:.3f}s"))
            except Exception as exc:
                camera_error = type(exc).__name__

        try:
            result = self._execute(arguments, cancel, record_frame)
        finally:
            recorder.close()
        metadata = recorder.metadata()
        result["video_frame_count"] = metadata["video_frame_count"]
        if metadata["video_available"]:
            result.setdefault("artifact_refs", []).append(f"artifact://labutopia/{relative.as_posix()}")
        if camera_error or metadata.get("video_error"):
            result["video_error"] = camera_error or metadata["video_error"]
        return result

    def _stir_execution_points(self, route, evidence_refs):
        """Stream transport without intermediate stops; rebind after insertion."""
        source, tool = route["source_path"], route["target"]["tool_frame"]
        nominal_relation = np.asarray(route["tcp_from_object"])
        for stage, group in groupby(route["steps"], key=lambda point: point["stage"]):
            points = list(group)
            if stage == "transport":
                tracking = {"start_joints": self.joints(), "steps": points}
            elif stage == "process":
                relation = np.linalg.inv(self.tcp()) @ self.observed_pose(source)
                targets = [(measured_feature_target(self.tcp(np.asarray(point["joints"])), nominal_relation, relation, tool),
                            point["hold_s"], "process") for point in points]
                tracking = self.qualify(targets, source, relation, "stir", np.asarray(route["original_return_pose"]), tool_frame=tool)
                evidence_refs.append(self._artifact("readiness", {
                    "kind": "measured_stir_tracking", "scene_revision": route["scene_revision"],
                    "source_path": source, "target": route["target"],
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "tcp_from_object": relation.tolist(), "route": tracking}))
            else:
                yield from points
                continue
            samples = continuous_joint_path([tracking["start_joints"], *[point["joints"] for point in tracking["steps"]]],
                self.dt, sum(point["hold_s"] for point in tracking["steps"]),
                self.config["joint_velocity_rad_s"], self.config["joint_acceleration_rad_s2"])
            if len(samples) > self.config["max_execution_steps"]:
                raise PhaseMotionError("execution_bound_reached", f"continuous {stage} exceeds the execution step budget")
            if np.any(samples < self.limits[:, 0]) or np.any(samples > self.limits[:, 1]):
                raise PhaseMotionError("joint_limit_violation", "continuous interpolation exceeds a joint limit")
            for joints in samples:
                yield {**tracking["steps"][0], "joints": joints.tolist(), "hold_s": 0., "continuous": True}

    def _pour_corrected_joints(self, start, planned, target_body, relation, tool, stage):
        target = target_body @ np.linalg.inv(relation)
        tolerance = self.config["position_tolerance_m"]
        maximum_delta = self.config["maximum_waypoint_joint_delta_rad"]
        closest_delta = math.inf
        for seed in (start, planned):
            goal, valid = local_inverse_kinematics(self.tcp, target, seed, self.limits, tolerance)
            if valid:
                delta = joint_delta(start, goal)
                if delta <= maximum_delta:
                    return goal
                closest_delta = min(closest_delta, delta)
        if tool is not None:
            for seed in (start, planned):
                goal, valid = local_tool_inverse_kinematics(
                    self.tcp, target_body, relation, tool, seed, self.limits, tolerance)
                if valid:
                    delta = joint_delta(start, goal)
                    if delta <= maximum_delta:
                        return goal
                    closest_delta = min(closest_delta, delta)
        if closest_delta < math.inf:
            raise PhaseMotionError(
                "ik_discontinuity", f"{stage}: measured pour-pose correction joint delta "
                f"{closest_delta:.6f} rad exceeds configured maximum {maximum_delta:.6f} rad")
        raise PhaseMotionError("inverse_kinematics_failed", "measured pour-pose correction is unreachable")

    def _qualify_pour_exit(self, route, exit_points, start, relation, supported_pose, cause, evidence_refs):
        nominal_relation = np.asarray(route["tcp_from_object"])
        adjustment = nominal_relation @ np.linalg.inv(relation)
        waypoints = [(self.tcp(np.asarray(point["joints"])) @ adjustment, point["hold_s"], "exit")
                     for point in exit_points]
        evidence = {"kind": "measured_pour_exit_requalification",
                    "scene_revision": route["scene_revision"],
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "source_path": route["source_path"], "start_joints": start.tolist(),
                    "tcp_from_object": relation.tolist(), "trigger_code": cause.code, "trigger_detail": str(cause)}
        try:
            qualified = self.qualify(waypoints, route["source_path"], relation, "pour", supported_pose,
                                     tool_frame=route["target"]["tool_frame"], initial_joints=start)
        except PhaseMotionError as exc:
            evidence_refs.append(self._artifact("readiness", {
                **evidence, "qualification": "rejected", "failure_code": exc.code, "failure_detail": str(exc),
                "diagnostics": exc.diagnostics}))
            raise
        evidence_refs.append(self._artifact("readiness", {
            **evidence, "qualification": "passed", "route": qualified}))
        return qualified["steps"]

    def _execute(self, arguments, cancel, record_frame):
        source = arguments["phase_route"]["source_path"]
        contact_window = GripContactWindow(self.world, self.sensors, self.body(source).prim_path, self.dt)
        callback_name = f"paos_grip_{id(contact_window)}"
        self.world.add_physics_callback(callback_name, contact_window.capture)
        try:
            return self._execute_motion(arguments, cancel, record_frame, contact_window)
        finally:
            self.world.remove_physics_callback(callback_name)

    def _qualify_acquire_recovery_start(self, route_start, source, finger_indices, relation, contact_window):
        """Measure whether the current acquire can recover to its own route start."""
        home = np.asarray(self.scene.get("initial_joint_positions"), dtype=float)
        if (
            route_start.shape != (len(self.joint_indices),)
            or not np.isfinite(route_start).all()
            or np.any(route_start < self.limits[:, 0])
            or np.any(route_start > self.limits[:, 1])
            or (home.shape == route_start.shape
                and np.max(np.abs(route_start - home)) <= self.config["joint_tracking_tolerance_rad"])
        ):
            return None
        fingers = np.asarray(self.robot.get_joint_positions())[finger_indices]
        if not np.isfinite(fingers).all() or np.min(fingers) < .035:
            return None
        # Isaac contact frames can lag the current render time by a physics
        # substep. Allow the same age as live grip feedback, without stepping.
        # Capture separately so missing entry evidence cannot poison live sampling.
        entry = GripContactWindow(self.world, contact_window.sensors, contact_window.body_path, self.dt)
        entry.capture(require_raw_frame=True)
        now = float(self.world.current_time)
        if entry.error is not None or len(entry.latest) != 2 or not all(
            frame is not None and 0. <= now - frame[0] <= self.dt * 2 and not frame[1]
            for frame in entry.latest
        ):
            return None
        try:
            self._collisions(route_start, source, False, False, relation, held_fingers=False)
        except PhaseMotionError:
            return None
        return {
            "joints_rad": route_start.tolist(),
            "finger_positions_m": fingers.tolist(),
            "timestamp_s": now,
            "contact_frame_timestamps_s": [frame[0] for frame in entry.latest],
            "selected_body_contact": False,
            "collision_check": "pass",
        }

    def _acquire_support_reader(self, source):
        """Bind normal-force readback for the selected body and exact support colliders."""
        from isaacsim.core.api.sensors import RigidContactView
        from pxr import PhysxSchema, Usd, UsdPhysics

        body = self.body(source)
        prim = self.stage.GetPrimAtPath(body.prim_path)
        if not prim.HasAPI(PhysxSchema.PhysxContactReportAPI):
            return None
        paths = []
        for root_path in self.config.get("support_collision_paths", ()):
            root = self.stage.GetPrimAtPath(root_path)
            if root.IsValid():
                paths.extend(str(item.GetPath()) for item in Usd.PrimRange(root)
                             if item.HasAPI(UsdPhysics.CollisionAPI)
                             and UsdPhysics.CollisionAPI(item).GetCollisionEnabledAttr().Get()
                             and not prim_path_is_within(str(item.GetPath()), body.prim_path))
        paths = tuple(dict.fromkeys(paths))
        if not paths:
            return None
        direction, magnitude = self.world.get_physics_context().get_gravity()
        weight = float(body.get_mass()) * float(magnitude)
        physics_dt = self.world.get_physics_dt()
        if (not np.allclose(direction, [0., 0., -1.]) or not math.isfinite(weight) or weight <= 0.
                or not math.isfinite(physics_dt) or physics_dt <= 0.):
            return None
        view = RigidContactView(
            prim_paths_expr=body.prim_path, filter_paths_expr=list(paths),
            prepare_contact_sensors=False, disable_stablization=False,
        )
        view.initialize(self.world.physics_sim_view)
        if (view.num_shapes, view.num_filters) != (1, len(paths)):
            return None

        def read(after):
            now = float(self.world.current_time)
            if not after < now or not view.is_physics_handle_valid():
                return None
            forces = np.asarray(view.get_contact_force_matrix(dt=physics_dt), dtype=float)
            if forces.shape != (1, len(paths), 3) or not np.isfinite(forces).all():
                return None
            upward = forces[0, :, 2]
            return {
                "body_path": body.prim_path,
                "support_paths": list(paths),
                "timestamp_s": now,
                "normal_force_world_n": forces[0].tolist(),
                "upward_force_n": float(upward.sum()),
                "weight_n": weight,
            }

        return read

    def _recover_failed_acquire(
        self,
        *,
        failure,
        source,
        original,
        axial_symmetry,
        finger_indices,
        executed_path,
        step_count,
        cancel,
        record_frame,
        record,
        contact_window,
        articulation_action,
        qualified_start,
    ):
        """Confirm unload at a fixed pose, then open and reverse the qualified path."""
        if failure not in acquire_failure_recovery_codes(self.config):
            raise PhaseMotionError("acquire_recovery_not_allowed", failure)
        initial_arm = np.asarray(self.scene.get("initial_joint_positions"), dtype=float)
        initial_gripper = np.asarray(self.scene.get("initial_gripper_positions"), dtype=float)
        if (
            initial_arm.shape != (len(self.joint_indices),)
            or initial_gripper.shape != (2,)
            or not np.isfinite(initial_arm).all()
            or not np.isfinite(initial_gripper).all()
            or np.any(initial_arm < self.limits[:, 0])
            or np.any(initial_arm > self.limits[:, 1])
            or np.min(initial_gripper) < .035
        ):
            raise PhaseMotionError(
                "acquire_recovery_state_unavailable",
                "configured observation posture and open gripper state are required",
            )
        route_start = np.asarray(executed_path[0].get("joints"), dtype=float)
        joint_tolerance = self.config["joint_tracking_tolerance_rad"]
        if route_start.shape != initial_arm.shape or not np.isfinite(route_start).all():
            raise PhaseMotionError("acquire_recovery_start_not_safe_pose", "qualified route start is invalid")
        at_home = np.max(np.abs(route_start - initial_arm)) <= joint_tolerance
        if not at_home and (qualified_start is None or qualified_start["joints_rad"] != route_start.tolist()):
            raise PhaseMotionError(
                "acquire_recovery_start_not_safe_pose",
                "non-home recovery requires open fingers, fresh clear contact frames and collision clearance at route start",
            )
        recovery_target = initial_arm if at_home else route_start

        tolerance = self.config["placement_tolerance_m"]

        def measure_support(pose):
            position_error = float(np.linalg.norm(pose[:3, 3] - original[:3, 3]))
            rotation_error = grasp_pose_errors(original, pose, axial_symmetry)[1]
            supported = (
                position_error <= tolerance
                and rotation_error <= self.config["grasp_rotation_tolerance_rad"]
                and float(np.linalg.norm(self.body(source).get_linear_velocity())) <= .03
            )
            return supported, position_error, rotation_error

        def in_support_band(pose):
            return support_contact_allowed("lift", pose, original, tolerance)

        def seated_on_support(pose):
            return in_support_band(pose) and abs(pose[2, 3] - original[2, 3]) <= .0005

        def safe_to_open(pose):
            return contact_window.current_unloaded(require_clear=True, whole_interval=False) or (
                failure == "physical_grasp_lost" and in_support_band(pose) and contact_window.current_unloaded()
            )

        support_reader = None

        def read_support():
            if support_reader is None:
                return None
            evidence = support_reader(contact_window.start)
            if (evidence is None
                    or not contact_window.start < evidence["timestamp_s"] <= float(self.world.current_time)):
                return None
            return evidence

        def support_bears_weight(evidence, minimum_fraction=.9):
            return evidence is not None and evidence["upward_force_n"] >= minimum_fraction * evidence["weight_n"]

        controller = self.robot.get_articulation_controller()

        def command(arm, fingers, stage, allow_contact, *, measure_support_load=False):
            nonlocal step_count
            if cancel.is_set():
                raise PhaseMotionError("cancelled", "recovery was cancelled")
            if not self.session.app.is_running() or step_count >= self.config["max_execution_steps"]:
                raise PhaseMotionError(
                    "execution_bound_reached",
                    "safe acquire recovery exceeded the execution step budget",
                )
            arm = np.asarray(arm, dtype=float)
            if (
                arm.shape != initial_arm.shape
                or not np.isfinite(arm).all()
                or np.any(arm < self.limits[:, 0])
                or np.any(arm > self.limits[:, 1])
            ):
                raise PhaseMotionError("joint_limit_violation", "safe acquire recovery joint target is invalid")
            if fingers.shape != initial_gripper.shape or not np.isfinite(fingers).all():
                raise PhaseMotionError("joint_limit_violation", "safe acquire recovery finger target is invalid")
            measured_relation = np.linalg.inv(self.tcp()) @ self.observed_pose(source)
            self._collisions(
                arm,
                source,
                allow_contact,
                False,
                measured_relation,
                False,
                held_fingers=False,
            )
            value = np.asarray(self.robot.get_joint_positions()).copy()
            value[self.joint_indices] = arm
            value[finger_indices] = fingers
            controller.apply_action(articulation_action(joint_positions=value))
            contact_window.begin()
            self.world.step(render=True)
            step_count += 1
            record_frame(stage)
            evidence = read_support() if measure_support_load else None
            held, pose = record(stage, commanded_fingers=fingers, support_evidence=evidence)
            if np.max(np.abs(self.joints() - arm)) > self.config["joint_tracking_tolerance_rad"]:
                raise PhaseMotionError("joint_tracking_failed", f"tracking tolerance exceeded in {stage}")
            return held, pose, evidence

        held, physical_body = record("recovery_check")
        supported, _, _ = measure_support(physical_body)
        can_open = not held and supported and safe_to_open(physical_body)
        require_supported_opening = False

        if (not can_open and failure == "physical_grasp_lost" and not held and supported
                and in_support_band(physical_body) and contact_window.has_current_feedback()):
            hold_arm = self.joints()
            hold_fingers = np.asarray(self.robot.get_joint_positions())[finger_indices]
            settle_steps = math.ceil(self.config.get("settle_s", 0.) / self.dt)
            for index in range(settle_steps):
                if index == settle_steps - 1 and contact_window.has_unilateral_load():
                    support_reader = self._acquire_support_reader(source)
                held, physical_body, evidence = command(
                    hold_arm, hold_fingers, "recovery_settle", True, measure_support_load=True,
                )
                supported, _, _ = measure_support(physical_body)
                if (held or not supported or not in_support_band(physical_body)
                        or not contact_window.has_current_feedback(after=contact_window.start)):
                    break
                if safe_to_open(physical_body):
                    can_open = True
                    break
            else:
                if (settle_steps and seated_on_support(physical_body) and support_bears_weight(evidence)
                        and contact_window.has_unilateral_load()):
                    require_supported_opening = can_open = True
        if not can_open:
            raise PhaseMotionError(
                "acquire_recovery_possession_uncertain",
                "safe opening requires a stable supported object and current unloaded fingers",
            )

        opening_arm = self.joints().copy()
        current_fingers = np.asarray(self.robot.get_joint_positions())[finger_indices]
        for fingers in smooth_joint_segment(
            current_fingers,
            initial_gripper,
            self.dt,
            self.config.get("finger_velocity_m_s", .015),
            self.config.get("finger_acceleration_m_s2", .15),
        ):
            held, physical_body, evidence = command(
                opening_arm, fingers, "recovery_open", True,
                measure_support_load=require_supported_opening,
            )
            if require_supported_opening:
                supported, _, _ = measure_support(physical_body)
                unloaded = safe_to_open(physical_body)
                # During partial release the seated bottle can share load with one finger.
                shared_support = not unloaded and contact_window.has_unilateral_load()
                if (held or not supported or not seated_on_support(physical_body)
                        or not contact_window.has_current_feedback(after=contact_window.start)
                        or not (unloaded or shared_support)
                        or not support_bears_weight(evidence, .75 if shared_support else .9)):
                    raise PhaseMotionError(
                        "acquire_recovery_support_lost",
                        "opening requires the bottle to remain stable on the measured support",
                    )

        def verify_empty(stage, *, require_support_load=False):
            evidence = read_support() if require_support_load else None
            held, physical_body = record(stage, support_evidence=evidence)
            supported, position_error, rotation_error = measure_support(physical_body)
            open_gripper = np.min(np.asarray(self.robot.get_joint_positions())[finger_indices]) >= .035
            if (held or not supported or not open_gripper
                    or not support_contact_allowed("lift", physical_body, original, tolerance)
                    or not contact_window.current_unloaded(require_clear=True)
                    or (require_support_load and not (
                        seated_on_support(physical_body)
                        and contact_window.has_current_feedback(after=contact_window.start)
                        and support_bears_weight(evidence)
                    ))):
                raise PhaseMotionError(
                    "acquire_recovery_postcondition_failed",
                    f"{stage} requires an open, clear gripper and a stable supported object",
                )
            return position_error, rotation_error

        verify_empty("recovery_open_check", require_support_load=require_supported_opening)

        current = self.joints()
        for point in reversed(executed_path):
            goal = np.asarray(point["joints"], dtype=float)
            if np.max(np.abs(current - goal)) <= 1e-9:
                continue
            command(goal, initial_gripper, "recovery_retreat", bool(point["allow_contact"]))
            current = goal

        final_return_error, final_rotation_error = verify_empty("recovery_complete")
        endpoint_error = float(np.max(np.abs(self.joints() - recovery_target)))
        if not math.isfinite(endpoint_error) or endpoint_error > joint_tolerance:
            raise PhaseMotionError(
                "acquire_recovery_postcondition_failed",
                "safe acquire recovery did not establish empty observation readiness",
            )
        if not at_home:
            self._collisions(self.joints(), source, False, False,
                             np.linalg.inv(self.tcp()) @ self.observed_pose(source), held_fingers=False)
        return {
            "step_count": step_count,
            "target_joints": recovery_target,
            "endpoint": "observation_home" if at_home else "qualified_route_start",
            "return_error_m": final_return_error,
            "return_rotation_error_rad": final_rotation_error,
            "endpoint_joint_error_rad": endpoint_error,
        }

    def _execute_motion(self, arguments, cancel, record_frame, contact_window):
        from isaacsim.core.utils.types import ArticulationAction
        from pick_place_workflow.cycle_protocol import evaluate_process_feedback

        # The public client already admitted an explicitly live Action.
        route = arguments["phase_route"]
        if route["operation"] != arguments["operation"] or route["scene_revision"] != self.session.current_scene_revision():
            raise PhaseMotionPreconditionError("stale_phase_route", "route operation/revision differs from the admitted action")
        if np.max(np.abs(self.joints() - route["start_joints"])) > self.config["joint_tracking_tolerance_rad"]:
            raise PhaseMotionPreconditionError("robot_state_changed", "robot moved after preparation")
        source = route["source_path"]
        self.body_from_observed[source] = np.asarray(route["body_from_observed"])
        for path, expected in ((source, route["start_object_pose"]),
                               (route["target"].get("destination_prim_path"), route.get("start_destination_pose"))):
            if path is not None and expected is not None:
                current = self.body_pose(path)
                expected = np.asarray(expected)
                if (np.linalg.norm(current[:3, 3] - expected[:3, 3]) > self.config["position_tolerance_m"]
                        or Rotation.from_matrix(current[:3, :3].T @ expected[:3, :3]).magnitude() > .02):
                    raise PhaseMotionPreconditionError("object_state_changed", "a bound object moved after preparation")
        original = np.asarray(route["original_return_pose"])
        supported_pose = original
        grasp_relation = np.asarray(route["tcp_from_object"])
        operation = route["operation"]
        axial_symmetry = None
        if any(source == path or source.startswith(path + "/") for path in self.config.get("axial_grip_paths", [])):
            axial_symmetry = route["target"]["tool_frame"]["tip_axis_local"]
        track_stir = operation == "stir" and axial_symmetry is not None
        tracking_refs = []
        last_goal = np.asarray(route["steps"][-1]["joints"])
        samples = []
        executed_path = [{
            "joints": np.asarray(route["start_joints"], dtype=float).tolist(),
            "stage": "start",
            "allow_contact": False,
        }]
        changed = False
        failure = None
        failure_detail = None
        status = "succeeded"
        finger_indices = [self.robot.get_dof_index(name) for name in ("panda_finger_joint1", "panda_finger_joint2")]
        qualified_recovery_start = (
            self._qualify_acquire_recovery_start(
                np.asarray(route["start_joints"], dtype=float), source, finger_indices, grasp_relation, contact_window,
            )
            if operation == "acquire" and acquire_failure_recovery_codes(self.config)
            else None
        )
        finger_target = np.full(2, .04) if operation == "acquire" else np.asarray(
            self.robot.get_joint_positions())[finger_indices].copy()
        if operation in {"pour", "place", "stir"} and self.config.get("finger_hold_follow", False):
            # Preserve bounded drive preload when a new phase inherits a held object.
            retain_overshoot = float(self.config.get("finger_retain_overshoot_m", 0.0))
            finger_target = np.maximum(finger_target - retain_overshoot, 0.0)
        hold_follow_active = False
        follow_diverged = False
        last_follow_fingers = None
        step_count = 0
        last_stage = None
        lift_grip_confirmed = False
        recovery = None
        terminal_exit_correction = None
        self.world.play()

        def contacts():
            return contact_window.valid()

        def record(stage, *, commanded_fingers=None, support_evidence=None):
            nonlocal finger_target
            if commanded_fingers is not None:
                finger_target = commanded_fingers
            physical_body = self.observed_pose(source)
            tcp = self.tcp()
            relation = np.linalg.inv(tcp) @ physical_body
            relation_error, rotation_error = grasp_pose_errors(grasp_relation, relation, axial_symmetry)
            contact_load_valid = contacts()
            contact_manifold_valid = contact_window.fresh_bilateral_manifolds()
            held = (contact_load_valid
                    and relation_error <= self.config["grasp_position_tolerance_m"]
                    and rotation_error <= self.config["grasp_rotation_tolerance_rad"])
            # Pour feedback judges the measured bottle tip and axis separately.
            grasp_valid = contact_load_valid if operation == "pour" else held
            sample = {"timestamp_s": float(self.world.current_time), "feedback_valid": True,
                      "grasp_valid": grasp_valid, "contact_load_valid": contact_load_valid,
                      "contact_manifold_valid": contact_manifold_valid,
                      "stage": stage, "joints": self.joints().tolist(),
                      "finger_positions_m": np.asarray(self.robot.get_joint_positions())[finger_indices].tolist(),
                      "finger_target_m": np.asarray(finger_target).tolist(),
                      "object_pose": physical_body.tolist(), "tcp_pose": tcp.tolist(),
                      "object_pose_source": "physics_displacement_of_observed_model",
                      "attachment_position_error_m": relation_error, "attachment_rotation_error_rad": rotation_error,
                      "full_attachment_rotation_error_rad": float(Rotation.from_matrix(grasp_relation[:3, :3].T @ relation[:3, :3]).magnitude()),
                      "object_origin_position_error_m": float(np.linalg.norm(relation[:3, 3] - grasp_relation[:3, 3])),
                      **contact_window.evidence()}
            if support_evidence is not None:
                sample["support_contact"] = support_evidence
            if operation in {"pour", "stir"}:
                target = route["target"]
                tip = physical_body[:3, 3] + physical_body[:3, :3] @ np.asarray(target["tool_frame"]["tip_offset_m"])
                axis = np.asarray(target["process_frame"]["axis"], dtype=float)
                axis /= np.linalg.norm(axis)
                delta = tip - np.asarray(target["process_frame"]["origin_m"])
                if operation == "pour":
                    pour_axis = physical_body[:3, :3] @ np.asarray(target["tool_frame"]["tip_axis_local"])
                    pour_axis /= np.linalg.norm(pour_axis)
                    alignment = float(np.linalg.norm(delta))
                    sample.update(alignment_error_m=alignment,
                                  target_container_aligned=alignment <= self.profile.alignment_tolerance_m,
                                  tilt_rad=float(math.acos(np.clip(np.dot(pour_axis, axis), -1., 1.))))
                else:
                    x = np.cross(axis, [1., 0., 0.])
                    if np.linalg.norm(x) < .1:
                        x = np.cross(axis, [0., 1., 0.])
                    x /= np.linalg.norm(x)
                    y = np.cross(axis, x)
                    sample.update(tool_tip_x_m=float(delta @ x), tool_tip_y_m=float(delta @ y), tool_tip_depth_m=float(-delta @ axis))
            samples.append(sample)
            return held, physical_body

        try:
            if "execution_steps" in route and not math.isclose(route["execution_dt_s"], self.dt):
                raise PhaseMotionPreconditionError("stale_phase_route", "retimed route control period changed")
            points = (self._stir_execution_points(route, tracking_refs) if track_stir
                      else iter(route.get("execution_steps", route["steps"])))
            place_pose_checked = False
            pour_exit_requalified = False
            terminal_exit_checked = False
            while True:
                point = next(points, None)
                if point is None:
                    if not pour_exit_requalified or terminal_exit_checked or last_stage != "exit":
                        break
                    terminal_exit_checked = True
                    planned = np.asarray(route["steps"][-1]["joints"])
                    tool = route["target"]["tool_frame"]
                    expected = self.tcp(planned) @ np.asarray(route["tcp_from_object"])
                    observed = self.observed_pose(source)
                    tip_error, axis_error = tool_feature_errors(observed, expected, tool)
                    if tip_error <= self.config["position_tolerance_m"] and axis_error <= .02:
                        break
                    terminal_exit_correction = {"tip_error_before_m": tip_error,
                                                "axis_error_before_rad": axis_error}
                    if not contacts():
                        raise PhaseMotionError("physical_grasp_lost",
                                               "fresh bilateral contact required for terminal exit correction")
                    start = self.joints()
                    relation = np.linalg.inv(self.tcp(start)) @ observed
                    goal = self._pour_corrected_joints(start, planned, expected, relation, tool, "exit")
                    point = {"stage": "exit", "joints": goal, "hold_s": 0.,
                             "allow_contact": False, "attached": True}
                stage = point["stage"]
                if operation == "place" and stage == "lower" and not place_pose_checked:
                    place_pose_checked = True
                    start = self.joints()
                    relation = np.linalg.inv(self.tcp(start)) @ self.observed_pose(source)
                    position_error, rotation_error = grasp_pose_errors(grasp_relation, relation)
                    if position_error > self.config["position_tolerance_m"] or rotation_error > .02:
                        # Approach the original support pose with the attachment
                        # measured at the end of transport.
                        waypoints = place_waypoints(supported_pose, relation, self.config)
                        if last_stage == "transport":
                            waypoints = waypoints[1:]
                        points = iter(self.qualify(waypoints, source, relation, operation, supported_pose,
                                                   initial_joints=start)["steps"])
                        continue
                if stage == "lift" and last_stage != "lift" and not contacts():
                    raise PhaseMotionError("grasp_not_confirmed", "both fingers must contact the selected body before lift")
                if stage == "lift" and last_stage != "lift":
                    if not record("grasp_check")[0]:
                        raise PhaseMotionError("grasp_transform_mismatch", "measured grip differs from the qualified grasp")
                    supported_pose = self.observed_pose(source)
                    grasp_relation = np.linalg.inv(self.tcp()) @ supported_pose
                    lift_grip_confirmed = last_stage == "close"
                if stage in {"open", "release", "retreat"}:
                    finger_target = np.full(2, .04)
                start = self.joints()
                goal = np.asarray(point["joints"])
                if track_stir and not point.get("continuous"):
                    relation = np.linalg.inv(self.tcp()) @ self.observed_pose(source)
                    target = self.tcp(goal) @ np.asarray(route["tcp_from_object"])
                    goal, valid = local_tool_inverse_kinematics(self.tcp, target, relation, route["target"]["tool_frame"],
                                                              start, self.limits, self.config["position_tolerance_m"])
                    if not valid:
                        raise PhaseMotionError("inverse_kinematics_failed", "measured tool-feature correction is unreachable")
                elif operation == "pour" and point["attached"] and (
                    stage == "transport" or (stage == "exit" and pour_exit_requalified)
                ):
                    # The command loop checks the qualified path with the
                    # measured attachment.
                    delta = joint_delta(start, goal)
                    maximum_delta = self.config["maximum_waypoint_joint_delta_rad"]
                    if delta > maximum_delta:
                        raise PhaseMotionError(
                            "ik_discontinuity", f"{stage}: qualified pour waypoint joint delta "
                            f"{delta:.6f} rad exceeds configured maximum {maximum_delta:.6f} rad")
                elif operation == "pour":
                    relation = np.linalg.inv(self.tcp(start)) @ self.observed_pose(source)
                    target_body = self.tcp(goal) @ grasp_relation
                    tool = route["target"]["tool_frame"] if point["attached"] and stage in {"process", "exit"} else None
                    try:
                        goal = self._pour_corrected_joints(start, goal, target_body, relation, tool, stage)
                    except PhaseMotionError as exc:
                        if stage != "exit" or not point["attached"] or pour_exit_requalified:
                            raise
                        if not contacts():
                            raise PhaseMotionError(
                                "physical_grasp_lost",
                                f"fresh bilateral contact required after {exc.code} for exit requalification") from exc
                        groups = groupby(chain((point,), points), key=lambda item: item["stage"])
                        _, remaining_exit = next(groups)
                        qualified = self._qualify_pour_exit(route, remaining_exit, start, relation,
                                                            supported_pose, exc, tracking_refs)
                        points = chain(qualified, chain.from_iterable(group for _, group in groups))
                        pour_exit_requalified = True
                        continue
                hold_frames = math.ceil(point["hold_s"] / self.dt)
                segment = ([goal] if point.get("continuous") else smooth_joint_segment(
                    start, goal, self.dt, self.config["joint_velocity_rad_s"], self.config["joint_acceleration_rad_s2"]))
                closure = None
                contact_established = False
                stable_frames = 0
                follow_hold = bool(self.config.get("finger_hold_follow", False))
                if stage == "close":
                    closure = list(smooth_joint_segment(
                        np.asarray(self.robot.get_joint_positions())[finger_indices], np.zeros(2), self.dt,
                        self.config.get("finger_velocity_m_s", .015), self.config.get("finger_acceleration_m_s2", .15)))
                    # The arm is already at its qualified grasp; wait for a measured,
                    # stable bilateral hold, bounded by full closure plus settle time.
                    segment = repeat(goal, len(closure))
                for command_index, arm_command in enumerate(chain(segment, repeat(goal, hold_frames))):
                    if cancel.is_set():
                        status = "cancelled"
                        raise PhaseMotionError("cancelled", "phase was cancelled")
                    if not self.session.app.is_running() or step_count >= self.config["max_execution_steps"]:
                        raise PhaseMotionError("execution_bound_reached", "simulation closed or the execution step limit was reached")
                    command = np.asarray(self.robot.get_joint_positions()).copy()
                    command[self.joint_indices] = arm_command
                    if closure is not None and not contact_established:
                        finger_target = closure[min(command_index, len(closure) - 1)]
                    command[finger_indices] = finger_target
                    commanded_joints = command[self.joint_indices]
                    measured_relation = (np.linalg.inv(self.tcp()) @ self.observed_pose(source)
                                         if point["attached"] else grasp_relation)
                    support_contact = support_contact_allowed(stage, self.tcp(commanded_joints) @ measured_relation,
                                                              supported_pose, self.config["placement_tolerance_m"])
                    self._collisions(commanded_joints, source, point["allow_contact"],
                                     point["attached"], measured_relation, support_contact, held_fingers=point["attached"])
                    changed = True
                    self.robot.get_articulation_controller().apply_action(ArticulationAction(joint_positions=command))
                    path_point = {
                        "joints": commanded_joints.tolist(),
                        "stage": stage,
                        "allow_contact": bool(point["allow_contact"]),
                    }
                    previous_path = executed_path[-1]
                    if (
                        np.max(np.abs(np.asarray(previous_path["joints"]) - commanded_joints)) > 1e-9
                        or previous_path["stage"] != stage
                        or previous_path["allow_contact"] != path_point["allow_contact"]
                    ):
                        executed_path.append(path_point)
                    contact_window.begin()
                    self.world.step(render=True)
                    step_count += 1
                    record_frame(stage)
                    held, physical_body = record(stage)
                    measured_support_contact = support_contact_allowed(
                        stage, physical_body, supported_pose,
                        self.config["placement_tolerance_m"])
                    support_manifold_continuity = False
                    if (operation == "acquire" and lift_grip_confirmed
                            and stage == "lift" and not held
                            and measured_support_contact
                            and samples[-1]["contact_manifold_valid"]):
                        measured_sample = samples[-1]
                        if (measured_sample["attachment_position_error_m"]
                                <= self.config["grasp_position_tolerance_m"]
                                and measured_sample["attachment_rotation_error_rad"]
                                <= self.config["grasp_rotation_tolerance_rad"]):
                            # A settled supported body may retain fresh contact
                            # manifolds while this interval's impulse is zero. Keep
                            # the raw load/grasp facts false and only continue until
                            # the existing support-departure boundary is crossed.
                            measured_sample["support_manifold_continuity_used"] = True
                            support_manifold_continuity = True
                    if (hold_follow_active and point["attached"] and held
                            and stage not in {"open", "release", "retreat"} and not follow_diverged):
                        # Keep the hold tracking surface recession during attached motion
                        # (lift/carry): the same bounded re-freeze as the close settle, so
                        # normal force does not decay on a tapering body. Commanded
                        # penetration stays at retain_overshoot while held is true; if the
                        # grip degrades the update stops and the existing failure paths
                        # decide the outcome. The stage exclusion protects the release
                        # opening target set at stage start.
                        retain_overshoot = float(self.config.get("finger_retain_overshoot_m", 0.0))
                        finger_target = np.maximum(
                            np.asarray(self.robot.get_joint_positions())[finger_indices].copy() - retain_overshoot,
                            0.0)
                    if (operation == "acquire" and stage in {"approach", "grasp", "close"}
                            and not (closure is not None and contact_established)):
                        # Displacement is judged at the grasp anchor (the TCP
                        # point bound to the object), not at the world origin:
                        # reference/current are world poses, so the generic
                        # helper's origin anchoring would amplify a permitted
                        # touch rotation by the body-to-world-origin lever.
                        # Once both pads hold the body this gate stands down:
                        # bounded settling motion is contact-time physics, and
                        # the settled transform is judged once at the lift-entry
                        # grasp check with the same frozen tolerances.
                        anchor = -grasp_relation[:3, :3].T @ grasp_relation[:3, 3]
                        drift = grasp_anchor_drift(anchor, original, physical_body)
                        _, rotation = grasp_pose_errors(original, physical_body, axial_symmetry)
                        if (drift > self.config["grasp_position_tolerance_m"]
                                or rotation > self.config["grasp_rotation_tolerance_rad"]):
                            raise PhaseMotionError("grasp_object_displaced", "object moved before a qualified lift")
                    if closure is not None:
                        # A parallel-jaw grip on a round body settles with bounded
                        # contact-time motion; a per-frame qualified-transform
                        # comparison here killed physically held grips. Only a
                        # real loss of bilateral contact stops the closure — the
                        # settled transform is judged once at the lift-entry
                        # grasp check.
                        if contact_established and not contacts():
                            raise PhaseMotionError("physical_grasp_lost", "bilateral contact lost during closure settling")
                        if contacts():
                            # Hold the grip at the measured bilateral-contact position minus a
                            # bounded retain overshoot. With finger_hold_follow enabled the hold
                            # re-freezes on every held step so the pads keep tracking surface
                            # recession (e.g. a bottle shoulder taper) and normal force does not
                            # decay during lift; penetration stays bounded at retain_overshoot,
                            # so commanded force cannot exceed stiffness * retain. Default False
                            # keeps the legacy one-time freeze at first contact.
                            # The follow ends when the fingers diverge — one pad advancing
                            # while the other is forced back is the signature of the body
                            # walking sideways through the grip (measured on the bridged
                            # shoulder: a perfect centered first touch dragged 18mm to the
                            # finger joint limit by the ever-deepening chase). Symmetric
                            # advance is legitimate recession tracking and keeps following.
                            measured_fingers = np.asarray(self.robot.get_joint_positions())[finger_indices].copy()
                            if (follow_hold and contact_established and last_follow_fingers is not None
                                    and np.any(measured_fingers > last_follow_fingers + 1e-4)):
                                follow_diverged = True
                            if not contact_established or (follow_hold and not follow_diverged):
                                retain_overshoot = float(self.config.get("finger_retain_overshoot_m", 0.0))
                                finger_target = np.maximum(measured_fingers - retain_overshoot, 0.0)
                                last_follow_fingers = measured_fingers
                            contact_established = True
                            hold_follow_active = follow_hold
                            stable_frames += 1
                    attached_stage = ((operation != "acquire" and stage not in {"release", "retreat"})
                                      or stage == "lift")
                    # A round body carried in parallel jaws settles with mm-level
                    # relative slip: run24d measured the bottle following the TCP
                    # at 71% with bilateral load on every frame when this gate's
                    # transform bound killed the lift mid-carry. While both pads
                    # still carry load the grip is real — only an actual loss of
                    # bilateral contact stops attached motion. The settled
                    # transform is judged once, at the lift-entry grasp check.
                    if attached_stage and not contacts() and not support_manifold_continuity:
                        raise PhaseMotionError("physical_grasp_lost", "bilateral contact lost during attached motion")
                    measured_relation = (np.linalg.inv(self.tcp()) @ physical_body
                                         if point["attached"] else grasp_relation)
                    self._collisions(self.joints(), source, point["allow_contact"], point["attached"],
                                     measured_relation, measured_support_contact,
                                     held_fingers=point["attached"])
                    if closure is not None and contact_established and stable_frames >= max(1, hold_frames):
                        break
                if closure is not None and stable_frames < max(1, hold_frames):
                    raise PhaseMotionError("grasp_not_confirmed", "bounded closure did not establish a stable bilateral grip")
                if np.max(np.abs(self.joints() - goal)) > self.config["joint_tracking_tolerance_rad"]:
                    raise PhaseMotionError("joint_tracking_failed", f"tracking tolerance exceeded in {stage}")
                last_goal = goal
                last_stage = stage
        except PhaseMotionError as exc:
            failure = exc.code
            failure_detail = str(exc)
            status = "cancelled" if status == "cancelled" else "failed"
            # Stop first. A configured, measured empty-gripper failure may then
            # reverse only the commands already executed from the qualified route.
            try:
                if changed:
                    stop_positions = np.asarray(self.robot.get_joint_positions()).copy()
                    self.robot.get_articulation_controller().apply_action(
                        ArticulationAction(joint_positions=stop_positions))
                    finger_target = stop_positions[finger_indices]
            except Exception as stop_exc:
                reference = self._artifact("phase-feedback", {"operation": operation,
                    "entity_ref": arguments["entity_ref"], "scene_revision": arguments["scene_revision"],
                    "samples": samples, "status": "unknown", "failure_code": failure,
                    "failure_detail": failure_detail, "stop_failure_code": type(stop_exc).__name__})
                return {"status": "unknown", "outcome_known": False, "world_change_started": changed,
                        "possession_state": "uncertain", "operation_completed": False,
                        "failure_owner": "isaacsim_adapter", "failure_code": failure,
                        "artifact_refs": [reference, *tracking_refs], "measurements": {}}
            if (
                changed
                and operation == "acquire"
                and status == "failed"
                and failure in acquire_failure_recovery_codes(self.config)
            ):
                try:
                    recovery = self._recover_failed_acquire(
                        failure=failure,
                        source=source,
                        original=original,
                        axial_symmetry=axial_symmetry,
                        finger_indices=finger_indices,
                        executed_path=executed_path,
                        step_count=step_count,
                        cancel=cancel,
                        record_frame=record_frame,
                        record=record,
                        contact_window=contact_window,
                        articulation_action=ArticulationAction,
                        qualified_start=qualified_recovery_start,
                    )
                    step_count = recovery["step_count"]
                    last_goal = recovery["target_joints"]
                    last_stage = "recovery_complete"
                except Exception as recovery_exc:
                    reference = self._artifact("phase-feedback", {
                        "operation": operation,
                        "entity_ref": arguments["entity_ref"],
                        "scene_revision": arguments["scene_revision"],
                        "samples": samples,
                        "status": "unknown",
                        "failure_code": failure,
                        "failure_detail": failure_detail,
                        "recovery_failure_code": getattr(
                            recovery_exc, "code", type(recovery_exc).__name__
                        ),
                        "recovery_failure_detail": str(recovery_exc),
                        "recovery_start_evidence": qualified_recovery_start,
                    })
                    return {
                        "status": "unknown",
                        "outcome_known": False,
                        "world_change_started": changed,
                        "possession_state": "uncertain",
                        "operation_completed": False,
                        "failure_owner": "isaacsim_adapter",
                        "failure_code": failure,
                        "artifact_refs": [reference, *tracking_refs],
                        "measurements": {},
                    }
        except Exception as exc:
            # Preserve partial feedback and the original failure if the plant
            # can no longer provide a trustworthy terminal measurement.
            stop_error = None
            try:
                if changed:
                    self.robot.get_articulation_controller().apply_action(
                        ArticulationAction(joint_positions=np.asarray(self.robot.get_joint_positions()).copy()))
            except Exception as stop_exc:
                stop_error = type(stop_exc).__name__
            reference = self._artifact("phase-feedback", {"operation": operation,
                "entity_ref": arguments["entity_ref"], "scene_revision": arguments["scene_revision"],
                "samples": samples, "status": "unknown", "failure_code": type(exc).__name__,
                "error": str(exc), "stop_failure_code": stop_error})
            return {"status": "unknown", "outcome_known": False, "world_change_started": changed,
                    "possession_state": "uncertain", "operation_completed": False,
                    "failure_owner": "isaacsim_adapter", "failure_code": type(exc).__name__,
                    "artifact_refs": [reference, *tracking_refs], "measurements": {}}
        try:
            _, physical_body = record(last_stage or "stopped")
            # Carry possession is a physical fact of the gripper: bilateral
            # load at the finish means the body is held, whatever mm-level
            # settling slip the carry produced (run24d: 8.2mm slip under
            # unbroken bilateral load). The transform bound stays where it is
            # honestly applied — once, at the lift-entry grasp check.
            carried = contacts()
            lifted = physical_body[2, 3] - original[2, 3] >= self.profile.object_lift_threshold_m
            return_error = float(np.linalg.norm(physical_body[:3, 3] - original[:3, 3]))
            return_rotation_error = grasp_pose_errors(original, physical_body, axial_symmetry)[1]
            finish = self.tcp(
                recovery["target_joints"]
                if recovery is not None
                else last_goal
                if (track_stir or operation in {"pour", "place"}) and status == "succeeded"
                else np.asarray(route["steps"][-1]["joints"])
            )
            actual_tcp = self.tcp()
            final_position_error = float(np.linalg.norm(actual_tcp[:3, 3] - finish[:3, 3]))
            final_rotation_error = float(Rotation.from_matrix(finish[:3, :3].T @ actual_tcp[:3, :3]).magnitude())
            final_pose_reached = final_position_error <= self.config["position_tolerance_m"] and final_rotation_error <= .02
            open_gripper = bool(np.min(np.asarray(self.robot.get_joint_positions())[finger_indices]) >= .035)
            supported = (return_error <= self.config["placement_tolerance_m"] and return_rotation_error <= self.config["grasp_rotation_tolerance_rad"]
                         and float(np.linalg.norm(self.body(source).get_linear_velocity())) <= .03)
            possession = "holding" if carried else "empty" if supported and open_gripper else "uncertain"
            known = possession != "uncertain"
            measurements = {"return_error_m": return_error, "return_rotation_error_rad": return_rotation_error,
                            "full_return_rotation_error_rad": float(Rotation.from_matrix(original[:3, :3].T @ physical_body[:3, :3]).magnitude()),
                            "final_tcp_position_error_m": final_position_error, "final_tcp_rotation_error_rad": final_rotation_error}
            if recovery is not None:
                at_home = recovery["endpoint"] == "observation_home"
                joint_error_name = "recovery_home_joint_error_rad" if at_home else "recovery_route_start_joint_error_rad"
                measurements[joint_error_name] = recovery["endpoint_joint_error_rad"]
                measurements.update(
                    recovery_return_error_m=recovery["return_error_m"],
                    recovery_return_rotation_error_rad=recovery["return_rotation_error_rad"],
                )
            completed = status == "succeeded" and final_pose_reached
            if track_stir or operation == "pour":
                tool = route["target"]["tool_frame"]
                expected = self.tcp(np.asarray(route["steps"][-1]["joints"])) @ np.asarray(route["tcp_from_object"])
                tip_error, axis_error = tool_feature_errors(physical_body, expected, tool)
                measurements.update(final_tool_tip_error_m=tip_error, final_tool_axis_error_rad=axis_error)
                completed = completed and tip_error <= self.config["position_tolerance_m"] and axis_error <= .02
                if terminal_exit_correction is not None:
                    terminal_exit_correction.update(tip_error_after_m=tip_error, axis_error_after_rad=axis_error)
            if operation == "acquire":
                completed = completed and carried and lifted
            elif operation in {"pour", "stir"}:
                parameters = {"direction": "ccw", **arguments["parameters"]}
                measurements.update(evaluate_process_feedback(operation + "_cycle", samples, parameters, self.profile.evaluation_profile()))
                if operation == "pour":
                    measurements["aligned_hold_s"] = measurements["qualified_tilt_hold_s"]
                    measurements["maximum_tilt_rad"] = max((item.get("tilt_rad", 0.) for item in samples), default=0.)
                completed = completed and measurements["process_completed"] and carried
            else:
                completed = completed and supported and open_gripper and last_stage == "retreat"
            if status == "succeeded" and not completed:
                status, failure = "failed", "measured_postcondition_failed"
            safely_recovered = recovery is not None and status == "failed" and possession == "empty"
            reference = self._artifact("phase-feedback", {"operation": operation, "entity_ref": arguments["entity_ref"],
                                      "scene_revision": arguments["scene_revision"], "samples": samples,
                                      "measurements": measurements, "status": status, "failure_code": failure,
                                      "failure_detail": failure_detail,
                                      **({"recovery_endpoint": recovery["endpoint"],
                                          "recovery_start_evidence": qualified_recovery_start}
                                         if recovery is not None else {}),
                                      **({"terminal_exit_correction": terminal_exit_correction}
                                         if terminal_exit_correction is not None else {}),
                                      "returned_to_safe_pose": safely_recovered,
                                      "observation_ready": safely_recovered})
            return {"status": status if known else "unknown", "outcome_known": known,
                    "entity_ref": arguments["entity_ref"], "destination_ref": arguments.get("destination_ref"),
                    "world_change_started": changed, "operation_completed": completed and known,
                    "possession_state": possession, "artifact_refs": [reference, *tracking_refs], "measurements": measurements,
                    "failure_code": failure,
                    "failure_owner": (
                        "execution" if safely_recovered
                        else "isaacsim_adapter" if failure else None
                    ),
                    "object_support_state": "on_support" if supported else "lifted" if lifted else "unknown",
                    "returned_to_safe_pose": safely_recovered or completed and operation in {"pour", "stir"},
                    "release_confirmed": completed and operation == "place",
                    "retreat_completed": completed and operation == "place",
                    "clear_of_target": completed and operation == "place",
                    "observation_ready": safely_recovered or completed and operation == "place",
                    "requires_replan": safely_recovered,
                    "recommended_action": (
                        "refresh_perception_before_motion" if safely_recovered else "continue"
                    )}
        except Exception as exc:
            reference = self._artifact("phase-feedback", {"operation": operation,
                "entity_ref": arguments["entity_ref"], "scene_revision": arguments["scene_revision"],
                "samples": samples, "status": "unknown", "failure_code": type(exc).__name__,
                "error": str(exc), "original_failure_code": failure})
            return {"status": "unknown", "outcome_known": False, "world_change_started": changed,
                    "possession_state": "uncertain", "operation_completed": False,
                    "failure_owner": "isaacsim_adapter", "failure_code": type(exc).__name__,
                    "artifact_refs": [reference, *tracking_refs], "measurements": {}}
