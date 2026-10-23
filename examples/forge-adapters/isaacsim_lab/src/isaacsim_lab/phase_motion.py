"""Session-owned, measured phase preparation for the Isaac laboratory adapter.

The route contains joint targets, not controller completion flags. Preparation
only reads physics state and performs FK, IK and overlap queries. Execution
uses articulation commands; it never teleports an object or attaches it by
editing a USD transform. Runtime remains the owner of possession/settlement.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from datetime import datetime, timezone
from functools import cached_property
from itertools import chain, groupby, repeat
from pathlib import Path
from uuid import uuid4

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation, Slerp


class PhaseMotionError(ValueError):
    def __init__(self, code, detail):
        super().__init__(detail)
        self.code = code


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


def preparation_result(arguments, route, evidence):
    """Project the measured route into the existing typed PAOS assignment."""
    from hashlib import sha256

    from PhyAgentOS.forge.capability_runtime.manipulation_prepare import preparation_ref_for_request
    from PhyAgentOS.forge.manipulation import ArmAssignment, arm_assignment_digest

    # ArmAssignment already requires the canonical route digest. This uses that
    # existing contract; it does not introduce a second route-integrity scheme.
    route_digest = sha256(json.dumps(route, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    private = {**deepcopy(dict(arguments)), "phase_route": route}
    if arguments.get("held_invocation_ref"):
        return {"status": "available", "motion_authorized": False, "route_arguments": private,
                "route_digest": route_digest, "readiness_evidence_ref": evidence}
    intent = arguments["intent"]
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


def continuous_joint_path(points, dt, duration, velocity_limit, acceleration_limit):
    """Run a clamped C2 path with analytic velocity/acceleration timing bounds."""
    points = np.asarray(points, dtype=float)
    knots = np.linspace(0., 1., len(points))
    spline = CubicSpline(knots, points, axis=0, bc_type="clamped")
    a, b, c, _ = spline.c
    width = np.diff(knots)[:, None]
    stationary = np.clip(np.divide(-b, 3 * a, out=np.zeros_like(a), where=a != 0), 0., width)
    peak_velocity = float(np.max(np.abs(np.stack((c, (3*a*width + 2*b)*width + c,
                                                  (3*a*stationary + 2*b)*stationary + c)))))
    peak_acceleration = float(np.max(np.abs(np.stack((2*b, 6*a*width + 2*b)))))
    duration = max(duration, peak_velocity / velocity_limit, math.sqrt(peak_acceleration / acceleration_limit))
    frames = max(2, math.ceil(duration / dt))
    return spline(np.linspace(0., 1., frames + 1)[1:])


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
        feature(high + other * config["process_clearance_m"], orientation)
        tilted = Rotation.from_rotvec(-horizontal * tilt).as_matrix() @ orientation
        feature(high, tilted)
        feature(center + axis * config["pour_lip_clearance_m"], tilted,
                float(parameters["hold_s"]) + config["settle_s"], "process")
        feature(high, tilted, stage="exit")
        feature(high + other * config["process_clearance_m"], orientation, stage="exit")
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
        self.latest = [None for _ in self.sensors]
        self.error = None

    def capture(self, _step_size=None):
        # PhysX invokes callbacks outside the caller's exception stack. Preserve
        # errors for the motion loop instead of allowing stale evidence through.
        try:
            for index, sensor in enumerate(self.sensors):
                frame = sensor.get_current_frame()
                timestamp = float(frame.get("time", -1.))
                contacts = [item for item in frame.get("contacts", [])
                            if self.body_path in (item["body0"], item["body1"])]
                impulse = sum(float(np.linalg.norm(item["impulse"])) for item in contacts)
                self.latest[index] = (timestamp, bool(contacts))
                if self.start <= timestamp <= float(self.world.current_time):
                    self.frames[index][timestamp] = impulse
        except Exception as exc:
            self.error = exc

    def valid(self):
        self.capture()
        if self.error is not None:
            raise PhaseMotionError("contact_sampling_failed", str(self.error)) from self.error
        now = float(self.world.current_time)
        return len(self.sensors) == 2 and all(
            latest is not None and latest[1] and abs(latest[0] - now) <= self.dt * 2
            and sum(frames.values()) > 0
            for latest, frames in zip(self.latest, self.frames))

    def evidence(self):
        return {"contact_window_start_s": self.start,
                "contact_window_end_s": float(self.world.current_time),
                "selected_contact_impulse_ns": [sum(frames.values()) for frames in self.frames],
                "contact_substep_samples": [len(frames) for frames in self.frames]}


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
            if isinstance(value, (int, float)) and (isinstance(value, bool) or not math.isfinite(value) or value <= 0):
                raise PhaseMotionError("invalid_motion_configuration", f"{key} must be finite and positive")
        lower, upper = np.asarray(self.config["workspace_min_m"]), np.asarray(self.config["workspace_max_m"])
        if lower.shape != (3,) or upper.shape != (3,) or not np.isfinite([lower, upper]).all() or np.any(lower >= upper):
            raise PhaseMotionError("invalid_motion_configuration", "workspace bounds must be finite and ordered")
        self.scene = session.resolve("lab_scene_resources")
        self.robot, self.world, self.stage = (self.scene[key] for key in ("robot", "world", "stage"))
        if not self.scene["robot_initialized"]:
            self.robot.initialize()
            self.scene["robot_initialized"] = True
        configuration = interface_config_loader.load_supported_lula_kinematics_solver_config("Franka")
        self.solver = LulaKinematicsSolver(**configuration)
        self.solver.set_robot_base_pose(*self.robot.get_world_pose())
        self.joint_indices = [self.robot.get_dof_index(name) for name in self.solver.get_joint_names()]
        properties = self.robot.dof_properties
        self.limits = np.column_stack((properties["lower"], properties["upper"]))[self.joint_indices]
        self.spheres = yaml.safe_load(Path(configuration["robot_description_path"]).read_text())["collision_spheres"]
        self.bodies = {}
        self.payload_geometry = {}
        self.body_from_observed = {}
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

    def _artifact(self, kind, value):
        from PhyAgentOS.utils.atomic_file import atomic_write_bytes

        path = Path(kind) / f"{uuid4().hex}.json"
        atomic_write_bytes(self.artifact_root / path, json.dumps(value, allow_nan=False, ensure_ascii=False).encode())
        return f"artifact://labutopia/{path.as_posix()}"

    @cached_property
    def finger_geometry(self):
        """Individual finger geometry and prismatic joints in the hand frame."""
        from itertools import product

        from pxr import Usd, UsdGeom, UsdPhysics

        def joint_pose(position, quaternion):
            return pose_matrix(list(position), [*quaternion.GetImaginary(), quaternion.GetReal()])

        bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
        geometry = []
        for number in (1, 2):
            joint = UsdPhysics.PrismaticJoint(self.stage.GetPrimAtPath(
                f"{self.robot.prim_path}/panda_hand/panda_finger_joint{number}"))
            body_path = joint.GetBody1Rel().GetTargets()[0]
            body = self.stage.GetPrimAtPath(body_path)
            parent_from_joint = joint_pose(joint.GetLocalPos0Attr().Get(), joint.GetLocalRot0Attr().Get())
            body_from_joint = joint_pose(joint.GetLocalPos1Attr().Get(), joint.GetLocalRot1Attr().Get())
            axis = {"X": 0, "Y": 1, "Z": 2}[joint.GetAxisAttr().Get()]
            colliders = [child for child in Usd.PrimRange(body)
                         if child.HasAPI(UsdPhysics.CollisionAPI)
                         and UsdPhysics.CollisionAPI(child).GetCollisionEnabledAttr().Get()]
            if not colliders:
                raise PhaseMotionError("finger_geometry_unavailable", "finger link has no active collider")
            for collider in colliders:
                box = bounds.ComputeRelativeBound(collider, body).ComputeAlignedBox()
                local_corners = np.array([*product(*zip(box.GetMin(), box.GetMax()))])
                geometry.append((number, local_corners, parent_from_joint, body_from_joint, axis,
                                 (joint.GetLowerLimitAttr().Get(), joint.GetUpperLimitAttr().Get())))
        return geometry

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

        def hits(center, radius, link, ignore_source=False):
            def ignore(path):
                if path.startswith(robot_path) or (ignore_source and (path == source_path or path.startswith(source_path + "/"))):
                    return True
                if link == "panda_link0" and path in self.config["mount_collision_paths"]:
                    return True
                return False
            found = collision_hits(query.overlap_sphere, float(radius), carb.Float3(*center), ignore=ignore)
            if found:
                raise PhaseMotionError("route_collision", f"{link} overlaps {found[0]}")

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
            return path.startswith(robot_path) or (
                (attached or released_pose is not None or allow_contact)
                and (path == source_path or path.startswith(source_path + "/")))
        for lower, upper in self.finger_boxes(measured=held_fingers):
            finger_center = hand[:3, 3] + hand[:3, :3] @ ((lower + upper) / 2)
            finger_half = (upper - lower) / 2 + self.config["collision_margin_m"]
            found = collision_hits(query.overlap_box, carb.Float3(*finger_half), carb.Float3(*finger_center),
                                   carb.Float4(*Rotation.from_matrix(hand[:3, :3]).as_quat()), ignore=ignore_finger)
            if found:
                raise PhaseMotionError("route_collision", f"finger overlaps {found[0]}")
            for link, centers, radii in groups:
                if link not in {"panda_hand", "panda_link7"}:
                    if any(np.linalg.norm(np.maximum(np.abs(hand[:3, :3].T @ (center - finger_center)) - finger_half, 0.)) < radius
                           for center, radius in zip(centers, radii, strict=True)):
                        raise PhaseMotionError("self_collision", f"finger envelope overlaps {link}")
        # The model's adjacent links intentionally overlap at their joints.
        # All non-adjacent groups remain checked, including the payload below.
        for i, (link, centers, radii) in enumerate(groups):
            for other_link, other_centers, other_radii in groups[i+2:]:
                for center, radius in zip(centers, radii, strict=True):
                    if any(np.linalg.norm(center - other) < radius + other_radius
                           for other, other_radius in zip(other_centers, other_radii, strict=True)):
                        raise PhaseMotionError("self_collision", f"{link} overlaps {other_link}")
        if attached or released_pose is not None:
            if source_path not in self.payload_geometry:
                raise PhaseMotionError("payload_geometry_unavailable", "payload has no bound observed point cloud")
            payload = self.tcp(joints) @ tcp_from_object if attached else released_pose
            quaternion = Rotation.from_matrix(payload[:3, :3]).as_quat()
            def ignore_payload(path):
                if path.startswith(robot_path) or path == source_path or path.startswith(source_path + "/"):
                    return True
                if (support_contact or released_pose is not None) and path in self.config["support_collision_paths"]:
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
            pre = desired.copy()
            pre[:3, 3] -= approach * self.config["approach_distance_m"]
            lifted = desired.copy()
            lifted[2, 3] += self.config["lift_distance_m"]
            tcp_from_object = np.linalg.inv(desired) @ body
            waypoints = [(tcp, self.config["settle_s"], "open"), (pre, 0., "approach"),
                         (desired, self.config["settle_s"], "grasp"),
                         (desired, self.config["settle_s"], "close"), (lifted, self.config["settle_s"], "lift")]
        elif operation == "place":
            desired = np.asarray(original_return) @ np.linalg.inv(tcp_from_object)
            above = desired.copy()
            above[2, 3] += self.config["lift_distance_m"]
            waypoints = [(above, 0., "transport"), (desired, self.config["settle_s"], "lower"),
                         (desired, self.config["settle_s"], "release"), (above, self.config["settle_s"], "retreat")]
        else:
            # Receiving-vessel process features were refreshed from the current
            # observation by the Provider, not corrected from simulator truth.
            waypoints = process_waypoints(operation, arguments["parameters"], tcp, body,
                                          tcp_from_object, target, self.config)
        if operation == "pour":
            clearance_limit = self.profile.alignment_tolerance_m - self.config["position_tolerance_m"]
            clearances = sorted({self.config["pour_lip_clearance_m"], clearance_limit})
            failures, candidates = [], []
            from itertools import product
            for clearance, yaw, azimuth in product(clearances, (0., -math.pi / 2, math.pi / 2),
                                                   (0., math.pi, -math.pi / 2, math.pi / 2)):
                if clearance > clearance_limit:
                    continue
                candidate_config = {**self.config, "pour_lip_clearance_m": clearance, "pour_yaw_rad": yaw, "pour_azimuth_rad": azimuth}
                candidate_waypoints = process_waypoints(operation, arguments["parameters"], tcp, body,
                                                       tcp_from_object, target, candidate_config)
                try:
                    route = self.qualify(candidate_waypoints, source, tcp_from_object, operation, np.asarray(original_return))
                    route["pour_lip_clearance_m"] = clearance
                    route["pour_yaw_rad"] = yaw
                    route["pour_azimuth_rad"] = azimuth
                    candidates.append(route)
                except PhaseMotionError as exc:
                    failures.append(f"clearance={clearance}, yaw={yaw}, azimuth={azimuth}: {exc}")
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
        evidence = self._artifact("readiness", {"captured_at": datetime.now(timezone.utc).isoformat(),
                                  "scene_revision": arguments["scene_revision"], "motion_authorized": False,
                                  "checks": {"kinematic": "pass", "collision": "pass", "workspace": "pass"},
                                  "route": route})
        return route, evidence

    def qualify(self, waypoints, source, tcp_from_object, operation, supported_pose=None, tool_frame=None):
        joints = self.joints()
        initial = joints.copy()
        previous_pose = self.tcp(joints)
        steps = []
        for pose, hold_s, stage in waypoints:
            contact = stage in {"grasp", "close", "lift", "lower", "release", "retreat"}
            attached = (operation != "acquire" and stage not in {"release", "retreat"}) or stage == "lift"
            for sample in interpolate_pose(previous_pose, pose):
                if np.any(sample[:3, 3] < self.config["workspace_min_m"]) or np.any(sample[:3, 3] > self.config["workspace_max_m"]):
                    raise PhaseMotionError("workspace_violation", f"TCP outside workspace in {stage}")
                hand = sample @ np.linalg.inv(self.hand_from_tcp)
                goal, success = self.solver.compute_inverse_kinematics("panda_hand", hand[:3, 3],
                    np.roll(Rotation.from_matrix(hand[:3, :3]).as_quat(), 1), warm_start=joints,
                    position_tolerance=self.config["position_tolerance_m"], orientation_tolerance=.02)
                if not success or np.max(np.abs(goal - joints)) > .5 or (operation == "stir" and stage == "process"):
                    local_goal, local_success = local_inverse_kinematics(
                        self.tcp, sample, joints, self.limits, self.config["position_tolerance_m"])
                    if local_success:
                        goal, success = local_goal, True
                if tool_frame is not None:
                    goal, success = local_tool_inverse_kinematics(
                        self.tcp, sample @ tcp_from_object, tcp_from_object, tool_frame,
                        joints, self.limits, self.config["position_tolerance_m"])
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
                            raise PhaseMotionError(exc.code, f"{stage}: expected TCP={sample[:3, 3].tolist()}, goal TCP={self.tcp(goal)[:3, 3].tolist()}, joint delta={float(np.max(np.abs(goal-joints)))}; {exc}") from exc
                # Collision sampling is denser than the commanded path. Keep
                # its checks without making the arm stop at every check point.
                steps.append({"joints": goal.tolist(), "stage": stage, "hold_s": 0.,
                              "allow_contact": contact, "attached": attached, "support_contact": bool(support_contact)})
                joints = goal
            steps[-1]["hold_s"] += hold_s
            previous_pose = pose
        return {"start_joints": initial.tolist(), "steps": steps}

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

    def _execute(self, arguments, cancel, record_frame):
        source = arguments["phase_route"]["source_path"]
        contact_window = GripContactWindow(self.world, self.sensors, self.body(source).prim_path, self.dt)
        callback_name = f"paos_grip_{id(contact_window)}"
        self.world.add_physics_callback(callback_name, contact_window.capture)
        try:
            return self._execute_motion(arguments, cancel, record_frame, contact_window)
        finally:
            self.world.remove_physics_callback(callback_name)

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
        changed = False
        failure = None
        failure_detail = None
        status = "succeeded"
        finger_indices = [self.robot.get_dof_index(name) for name in ("panda_finger_joint1", "panda_finger_joint2")]
        finger_target = .04 if operation == "acquire" else 0.
        step_count = 0
        last_stage = None
        self.world.play()

        def contacts():
            return contact_window.valid()

        def record(stage):
            physical_body = self.observed_pose(source)
            tcp = self.tcp()
            relation = np.linalg.inv(tcp) @ physical_body
            relation_error, rotation_error = grasp_pose_errors(grasp_relation, relation, axial_symmetry)
            held = contacts() and relation_error <= self.config["grasp_position_tolerance_m"] and rotation_error <= self.config["grasp_rotation_tolerance_rad"]
            sample = {"timestamp_s": float(self.world.current_time), "feedback_valid": True,
                      "grasp_valid": held, "stage": stage, "joints": self.joints().tolist(),
                      "finger_positions_m": np.asarray(self.robot.get_joint_positions())[finger_indices].tolist(),
                      "object_pose": physical_body.tolist(), "tcp_pose": tcp.tolist(),
                      "object_pose_source": "physics_displacement_of_observed_model",
                      "attachment_position_error_m": relation_error, "attachment_rotation_error_rad": rotation_error,
                      "full_attachment_rotation_error_rad": float(Rotation.from_matrix(grasp_relation[:3, :3].T @ relation[:3, :3]).magnitude()),
                      "object_origin_position_error_m": float(np.linalg.norm(relation[:3, 3] - grasp_relation[:3, 3])),
                      **contact_window.evidence()}
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
            points = self._stir_execution_points(route, tracking_refs) if track_stir else route["steps"]
            for point in points:
                stage = point["stage"]
                if stage == "lift" and last_stage != "lift" and not contacts():
                    raise PhaseMotionError("grasp_not_confirmed", "both fingers must contact the selected body before lift")
                if stage == "lift" and last_stage != "lift":
                    if not record("grasp_check")[0]:
                        raise PhaseMotionError("grasp_transform_mismatch", "measured grip differs from the qualified grasp")
                    supported_pose = self.observed_pose(source)
                    grasp_relation = np.linalg.inv(self.tcp()) @ supported_pose
                if stage in {"open", "release", "retreat"}:
                    finger_target = .04
                elif stage == "close":
                    finger_target = 0.
                start = self.joints()
                goal = np.asarray(point["joints"])
                if track_stir and not point.get("continuous"):
                    relation = np.linalg.inv(self.tcp()) @ self.observed_pose(source)
                    target = self.tcp(goal) @ np.asarray(route["tcp_from_object"])
                    goal, valid = local_tool_inverse_kinematics(self.tcp, target, relation, route["target"]["tool_frame"],
                                                              start, self.limits, self.config["position_tolerance_m"])
                    if not valid:
                        raise PhaseMotionError("inverse_kinematics_failed", "measured tool-feature correction is unreachable")
                elif operation == "pour":
                    relation = np.linalg.inv(self.tcp()) @ self.observed_pose(source)
                    target = self.tcp(goal) @ np.asarray(route["tcp_from_object"]) @ np.linalg.inv(relation)
                    goal, valid = local_inverse_kinematics(
                        self.tcp, target, start, self.limits, self.config["position_tolerance_m"])
                    if not valid:
                        raise PhaseMotionError("inverse_kinematics_failed", "measured pour-pose correction is unreachable")
                hold_frames = math.ceil(point["hold_s"] / self.dt)
                segment = ([goal] if point.get("continuous") else smooth_joint_segment(
                    start, goal, self.dt, self.config["joint_velocity_rad_s"], self.config["joint_acceleration_rad_s2"]))
                for arm_command in chain(segment, repeat(goal, hold_frames)):
                    if cancel.is_set():
                        status = "cancelled"
                        raise PhaseMotionError("cancelled", "phase was cancelled")
                    if not self.session.app.is_running() or step_count >= self.config["max_execution_steps"]:
                        raise PhaseMotionError("execution_bound_reached", "simulation closed or the execution step limit was reached")
                    command = np.asarray(self.robot.get_joint_positions()).copy()
                    command[self.joint_indices] = arm_command
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
                    contact_window.begin()
                    self.world.step(render=True)
                    step_count += 1
                    record_frame(stage)
                    held, physical_body = record(stage)
                    if ((operation != "acquire" and stage not in {"release", "retreat"}) or stage == "lift") and not held:
                        raise PhaseMotionError("physical_grasp_lost", "selected-body contact or measured grasp transform changed")
                    measured_relation = (np.linalg.inv(self.tcp()) @ physical_body
                                         if point["attached"] else grasp_relation)
                    support_contact = support_contact_allowed(stage, physical_body, supported_pose,
                                                              self.config["placement_tolerance_m"])
                    self._collisions(self.joints(), source, point["allow_contact"], point["attached"],
                                     measured_relation, support_contact, held_fingers=point["attached"])
                if np.max(np.abs(self.joints() - goal)) > self.config["joint_tracking_tolerance_rad"]:
                    raise PhaseMotionError("joint_tracking_failed", f"tracking tolerance exceeded in {stage}")
                last_goal = goal
                last_stage = stage
        except PhaseMotionError as exc:
            failure = exc.code
            failure_detail = str(exc)
            status = "cancelled" if status == "cancelled" else "failed"
            # Hold the measured configuration; never open or replay after failure.
            try:
                if changed:
                    self.robot.get_articulation_controller().apply_action(
                        ArticulationAction(joint_positions=np.asarray(self.robot.get_joint_positions()).copy()))
            except Exception as stop_exc:
                reference = self._artifact("phase-feedback", {"operation": operation,
                    "entity_ref": arguments["entity_ref"], "scene_revision": arguments["scene_revision"],
                    "samples": samples, "status": "unknown", "failure_code": failure,
                    "failure_detail": failure_detail, "stop_failure_code": type(stop_exc).__name__})
                return {"status": "unknown", "outcome_known": False, "world_change_started": changed,
                        "possession_state": "uncertain", "operation_completed": False,
                        "failure_owner": "isaacsim_adapter", "failure_code": failure,
                        "artifact_refs": [reference, *tracking_refs], "measurements": {}}
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
            held, physical_body = record(last_stage or "stopped")
            lifted = physical_body[2, 3] - original[2, 3] >= self.profile.object_lift_threshold_m
            return_error = float(np.linalg.norm(physical_body[:3, 3] - original[:3, 3]))
            return_rotation_error = grasp_pose_errors(original, physical_body, axial_symmetry)[1]
            finish = self.tcp(last_goal if (track_stir or operation == "pour") and status == "succeeded"
                              else np.asarray(route["steps"][-1]["joints"]))
            actual_tcp = self.tcp()
            final_position_error = float(np.linalg.norm(actual_tcp[:3, 3] - finish[:3, 3]))
            final_rotation_error = float(Rotation.from_matrix(finish[:3, :3].T @ actual_tcp[:3, :3]).magnitude())
            final_pose_reached = final_position_error <= self.config["position_tolerance_m"] and final_rotation_error <= .02
            open_gripper = bool(np.min(np.asarray(self.robot.get_joint_positions())[finger_indices]) >= .035)
            supported = (return_error <= self.config["placement_tolerance_m"] and return_rotation_error <= self.config["grasp_rotation_tolerance_rad"]
                         and float(np.linalg.norm(self.body(source).get_linear_velocity())) <= .03)
            possession = "holding" if held else "empty" if supported and open_gripper else "uncertain"
            known = possession != "uncertain"
            measurements = {"return_error_m": return_error, "return_rotation_error_rad": return_rotation_error,
                            "full_return_rotation_error_rad": float(Rotation.from_matrix(original[:3, :3].T @ physical_body[:3, :3]).magnitude()),
                            "final_tcp_position_error_m": final_position_error, "final_tcp_rotation_error_rad": final_rotation_error}
            completed = status == "succeeded" and final_pose_reached
            if track_stir or operation == "pour":
                tool = route["target"]["tool_frame"]
                tip, axis = np.asarray(tool["tip_offset_m"]), np.asarray(tool["tip_axis_local"])
                expected = self.tcp(np.asarray(route["steps"][-1]["joints"])) @ np.asarray(route["tcp_from_object"])
                tip_error = float(np.linalg.norm(physical_body[:3, 3] + physical_body[:3, :3] @ tip
                                                - expected[:3, 3] - expected[:3, :3] @ tip))
                axis_error = float(math.acos(np.clip(np.dot(physical_body[:3, :3] @ axis, expected[:3, :3] @ axis), -1., 1.)))
                measurements.update(final_tool_tip_error_m=tip_error, final_tool_axis_error_rad=axis_error)
                completed = completed and tip_error <= self.config["position_tolerance_m"] and axis_error <= .02
            if operation == "acquire":
                completed = completed and held and lifted
            elif operation in {"pour", "stir"}:
                parameters = {"direction": "ccw", **arguments["parameters"]}
                measurements.update(evaluate_process_feedback(operation + "_cycle", samples, parameters, self.profile.evaluation_profile()))
                if operation == "pour":
                    measurements["aligned_hold_s"] = measurements["qualified_tilt_hold_s"]
                    measurements["maximum_tilt_rad"] = max((item.get("tilt_rad", 0.) for item in samples), default=0.)
                completed = completed and measurements["process_completed"] and held
            else:
                completed = completed and supported and open_gripper and last_stage == "retreat"
            if status == "succeeded" and not completed:
                status, failure = "failed", "measured_postcondition_failed"
            reference = self._artifact("phase-feedback", {"operation": operation, "entity_ref": arguments["entity_ref"],
                                      "scene_revision": arguments["scene_revision"], "samples": samples,
                                      "measurements": measurements, "status": status, "failure_code": failure,
                                      "failure_detail": failure_detail})
            return {"status": status if known else "unknown", "outcome_known": known,
                    "entity_ref": arguments["entity_ref"], "destination_ref": arguments.get("destination_ref"),
                    "world_change_started": changed, "operation_completed": completed and known,
                    "possession_state": possession, "artifact_refs": [reference, *tracking_refs], "measurements": measurements,
                    "failure_code": failure, "failure_owner": "isaacsim_adapter" if failure else None,
                    "object_support_state": "on_support" if supported else "lifted" if lifted else "unknown",
                    "returned_to_safe_pose": completed and operation in {"pour", "stir"},
                    "release_confirmed": completed and operation == "place",
                    "retreat_completed": completed and operation == "place",
                    "clear_of_target": completed and operation == "place",
                    "observation_ready": completed and operation == "place"}
        except Exception as exc:
            reference = self._artifact("phase-feedback", {"operation": operation,
                "entity_ref": arguments["entity_ref"], "scene_revision": arguments["scene_revision"],
                "samples": samples, "status": "unknown", "failure_code": type(exc).__name__,
                "error": str(exc), "original_failure_code": failure})
            return {"status": "unknown", "outcome_known": False, "world_change_started": changed,
                    "possession_state": "uncertain", "operation_completed": False,
                    "failure_owner": "isaacsim_adapter", "failure_code": type(exc).__name__,
                    "artifact_refs": [reference, *tracking_refs], "measurements": {}}
