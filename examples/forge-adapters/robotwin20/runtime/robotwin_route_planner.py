"""Provider-owned no-motion evaluation of execution grasps and full routes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from robotwin_capability_controller import ControllerLimits
from robotwin_curobo_world_port import (
    add_released_object,
    apply_collision_world,
    bind_scene_table,
    capture_peer_projection,
    restore_collision_world,
)
from robotwin_gripper_geometry import planner_gripper_state
from robotwin_motion_policy import controller_limits, validate_motion_policy_bindings
from robotwin_planning_geometry import (
    ObservedGeometryActor,
    SimulationProbeError,
    _admit_capability_trajectory,
    _attach_object_to_planner,
    _capture_dual_arm_state,
    _initial_gripper_waypoint,
    _joint_limits,
    _route_pose,
    _table_top_z,
    _validate_attached_support_departure,
    _validate_gripper_table_clearance,
    _validate_trajectory,
    _validate_world_pose,
)


def plan_path_with_status(task, arm, pose, **kwargs):
    """Retain the native provider status that RoboTwin's public wrapper drops."""
    planner = getattr(task.robot, f"{arm}_planner")
    model = getattr(planner, "motion_gen", None)
    original = getattr(model, "plan_single", None)
    status = []
    def capture(*args, **kw):
        result = original(*args, **kw)
        status.append(str(getattr(result, "status", "unavailable")))
        return result
    # Runtime serializes all world queries. Restore the instance even on error.
    had_override = model is not None and "plan_single" in vars(model)
    if callable(original):
        model.plan_single = capture
    try:
        result = getattr(task.robot, f"{arm}_plan_path")(pose, **kwargs)
        if status and result.get("status") != "Success":
            result = {**result, "native_planner_status": status[-1]}
        return result
    finally:
        if callable(original):
            if had_override:
                model.plan_single = original
            else:
                del model.plan_single


def prepare_planning_world(task: Any, collision_world: Mapping[str, Any]) -> dict[str, Any]:
    bind_scene_table(task)
    state = _capture_dual_arm_state(task, collision_world["scene_revision"])
    peers = {arm: capture_peer_projection(task, state, arm) for arm in ("left", "right")}
    receipt = apply_collision_world(
        {arm: getattr(task.robot, f"{arm}_planner") for arm in ("left", "right")},
        collision_world,
        peer_projections=peers,
    )
    return {
        "dual_arm_state": state,
        "peer_arm_projection": peers,
        "collision_world_receipt": receipt,
    }


def sphere_support_clearance(task: Any, arm: str, qpos: Any) -> float:
    import numpy as np
    import transforms3d.quaternions as tquat

    planner = getattr(task.robot, f"{arm}_planner")
    model = planner.motion_gen
    spheres = model.kinematics.get_robot_as_spheres(
        model.tensor_args.to_device(np.asarray(qpos, dtype=np.float32).reshape(1, -1)),
        filter_valid=True,
    )[0]
    if not spheres:
        raise SimulationProbeError("Curobo robot spheres are unavailable")
    rotation = np.asarray(tquat.quat2mat(list(planner.robot_origion_pose.q)))
    base = np.asarray(planner.robot_origion_pose.p)
    # Touching the infinite support plane is a conservative contact screen;
    # the actual finite table and peer obstacles remain in MotionGen's world.
    return min(
        float((base + rotation @ np.asarray(s.pose[:3]))[2]) - float(s.radius) - _table_top_z(task)
        for s in spheres
    )


def evaluate_contact(
    task: Any, execution_grasp: Mapping[str, Any], arm: str, approach_clearance_m: float
) -> dict[str, Any]:
    with planner_gripper_state(task, arm, "open"):
        return _evaluate_contact(task, execution_grasp, arm, approach_clearance_m)


def _evaluate_contact(
    task: Any, execution_grasp: Mapping[str, Any], arm: str, approach_clearance_m: float
) -> dict[str, Any]:
    import numpy as np

    planner = getattr(task.robot, f"{arm}_planner")
    phase = "approach"
    try:
        pose = _route_pose(execution_grasp["robot_target_pose"], "world")
        approach = list(pose)
        for i in range(3):
            approach[i] -= approach_clearance_m * execution_grasp["ingress_direction"]["vector"][i]
        ingress = plan_path_with_status(task, arm, approach)
        _validate_trajectory(ingress, _joint_limits(planner))
        _validate_gripper_table_clearance(
            task, arm, ingress["position"], phase="approach", gripper_state="open"
        )
        predicted = np.asarray(getattr(task.robot, f"{arm}_entity").get_qpos()).copy()
        predicted[:7] = np.asarray(ingress["position"])[-1]
        phase = "contact"
        result = plan_path_with_status(task, arm, pose, last_qpos=predicted.tolist())
        _validate_trajectory(result, _joint_limits(planner))
        _validate_gripper_table_clearance(
            task, arm, result["position"], phase="contact", gripper_state="open"
        )
        phase = "contact_support_clearance"
        clearance = sphere_support_clearance(task, arm, result["position"][-1])
        return {"planner_status": "success", "clearance_m": clearance}
    except Exception as exc:
        return {"planner_status": "failed", "clearance_m": None,
                "failed_phase": phase, "reason": str(exc)}


def released_object_envelope(candidate):
    """Conservative box covering release-to-settled translation for retreat."""
    import numpy as np
    import transforms3d.quaternions as tquat

    placement = candidate["placement_target"]
    pose = deepcopy(placement["target_object_pose"])
    extents = list(candidate["attached_object"]["half_extents_m"])
    clearance = placement.get("release_clearance_m", 0.0)
    if not clearance:
        return pose, extents
    shift = np.asarray(candidate["execution_grasp"]["support_clear_direction"]["vector"]) * clearance
    q = pose["orientation_xyzw"]
    local_shift = tquat.quat2mat([q[3], *q[:3]]).T @ shift
    pose["position_m"] = (np.asarray(pose["position_m"]) + shift / 2).tolist()
    return pose, (np.asarray(extents) + np.abs(local_shift) / 2).tolist()


def evaluate_route_arm(
    task: Any,
    request: Mapping[str, Any],
    candidate: Mapping[str, Any],
    arm: str,
    actor: Any,
    *,
    diagnose_failure: bool = False,
    initial_dual_arm_state: Mapping[str, Any] | None = None,
    capability_limits: ControllerLimits | None = None,
) -> dict[str, Any]:
    """Plan serially from predicted endpoints, restoring geometry in all cases.

    SAPIEN qpos is used only for FK and attachment geometry. No scene step,
    drive target, controller command, or Gateway invocation occurs here.
    """
    import numpy as np

    planner = getattr(task.robot, f"{arm}_planner")
    entity = getattr(task.robot, f"{arm}_entity")
    original = np.asarray(entity.get_qpos()).copy()
    initial_gripper_waypoint = _initial_gripper_waypoint(task, arm, request["frame_id"])
    planned_candidate = deepcopy(dict(candidate))
    planned_candidate["route"] = deepcopy(candidate["route"])
    planned_candidate["route"][-1]["waypoints"].append(initial_gripper_waypoint)
    predicted = original.copy()
    attached = False
    phase_name = "approach"
    index = 0
    segments = []
    execution_plan = []
    previous_worlds = []
    gripper = []
    try:
        from robotwin_observed_collision import released_target_mesh

        observed = getattr(task, "_paos_observed_bindings", {}).get(candidate.get("entity_ref"))
        if observed is not None:
            actor = ObservedGeometryActor(observed["model"]["world_T_object"])
        if getattr(task, "_paos_observed_collision", None) is not None and not isinstance(actor, ObservedGeometryActor):
            raise SimulationProbeError("observed route requires an observation-owned source pose")
        mesh = (released_target_mesh(task, candidate, actor.get_pose().to_transformation_matrix())
                if getattr(task, "_paos_observed_collision", None) is not None else None)
        limits = _joint_limits(planner)
        for phase in planned_candidate["route"]:
            phase_name = phase["phase"]
            if phase_name == "retreat" and attached:
                planner.motion_gen.detach_object_from_robot()
                attached = False
                released_pose, released_extents = released_object_envelope(planned_candidate)
                previous_worlds = add_released_object(
                    planner,
                    released_pose,
                    released_extents,
                    **({"observed_mesh": mesh} if mesh is not None else {}),
                )
            for index, waypoint in enumerate(phase["waypoints"]):
                pose = _route_pose(waypoint, request["frame_id"])
                _validate_world_pose(
                    pose,
                    request["workspace_bounds_m"],
                    candidate["attached_object"]["half_extents_m"],
                )
                with planner_gripper_state(task, arm, phase["gripper_state"]) as gripper:
                    result = plan_path_with_status(task, arm, pose, last_qpos=predicted.tolist())
                    _validate_trajectory(result, limits)
                    if capability_limits is not None:
                        result = _admit_capability_trajectory(result, capability_limits)
                    _validate_gripper_table_clearance(
                        task, arm, result["position"], phase=phase_name,
                        gripper_state=phase["gripper_state"],
                    )
                    if phase_name == "lift" and not attached:
                        entity.set_qpos(predicted.tolist())
                        attached = True
                        _attach_object_to_planner(
                            task, planner, actor, planned_candidate["attached_object"]["half_extents_m"], arm
                        )
                        _validate_attached_support_departure(planner, result["position"])
                predicted[:7] = np.asarray(result["position"])[-1]
                segments.append(
                    {
                        "phase": phase_name,
                        "waypoint_index": index,
                        "status": "pass",
                        "end_qpos": predicted[:7].tolist(),
                        "gripper_geometry": gripper,
                    }
                )
                execution_plan.append(
                    {
                        "phase": phase_name,
                        "gripper_state": phase["gripper_state"],
                        "waypoint_index": index,
                        "route_waypoint": deepcopy(waypoint),
                        "world_pose_pq_wxyz": list(pose),
                        "position": np.asarray(result["position"], dtype=float).tolist(),
                        "velocity": np.asarray(result["velocity"], dtype=float).tolist(),
                        "gripper_geometry": gripper,
                    }
                )
        return {
            "arm": arm,
            "status": "pass",
            "segments": segments,
            "execution_plan": {
                "schema_version": "paos-robotwin20-prepared-execution-plan/v2",
                "request_id": request.get("request_id"),
                "candidate_ref": candidate["candidate_ref"],
                "entity_ref": candidate.get("entity_ref"),
                "scene_revision": request.get("scene_revision"),
                "frame_id": request["frame_id"],
                "arm": arm,
                "initial_qpos": original[:7].tolist(),
                "initial_dual_arm_state": deepcopy(dict(initial_dual_arm_state)),
                "segments": execution_plan,
                "motion_authorized": False,
            } if initial_dual_arm_state is not None else None,
            "motion_authorized": False,
        }
    except Exception as exc:
        diagnostic = None
        if diagnose_failure and phase_name == "retreat":
            from robotwin_descent_diagnostic import diagnose_start_collisions

            try:
                with planner_gripper_state(task, arm, phase["gripper_state"]):
                    diagnostic = diagnose_start_collisions(task, arm, predicted)
            except Exception as diagnostic_error:
                diagnostic = {"error": str(diagnostic_error), "diagnostic_only": True}
        if diagnose_failure and attached and phase_name == "descent":
            from robotwin_descent_diagnostic import diagnose_attached_segment

            try:
                diagnostic = diagnose_attached_segment(
                    task, planned_candidate, arm, actor, pose, predicted
                )
            except Exception as diagnostic_error:
                diagnostic = {"error": str(diagnostic_error), "diagnostic_only": True}
        return {
            "arm": arm,
            "status": "fail",
            "failed_phase": phase_name,
            "failed_waypoint_index": index,
            "detail": str(exc),
            "gripper_geometry": gripper,
            "diagnostic": diagnostic,
            "segments": segments,
            "execution_plan": None,
            "motion_authorized": False,
        }
    finally:
        try:
            if attached:
                planner.motion_gen.detach_object_from_robot()
        finally:
            try:
                for model, world in previous_worlds:
                    restore_collision_world(model, world)
            finally:
                entity.set_qpos(original.tolist())


def evaluate_route(
    task: Any,
    request: Mapping[str, Any],
    candidate: Mapping[str, Any],
    actor: Any,
    *,
    diagnose_failure: bool = False,
    initial_dual_arm_state: Mapping[str, Any] | None = None,
    capability_limits: Mapping[str, ControllerLimits] | None = None,
) -> dict[str, Any]:
    options: dict[str, Any] = {}
    if diagnose_failure:
        options["diagnose_failure"] = True
    if initial_dual_arm_state is not None:
        options["initial_dual_arm_state"] = initial_dual_arm_state
    attempts = []
    for arm in ("left", "right"):
        arm_options = dict(options)
        if capability_limits is not None:
            limit = capability_limits.get(arm)
            if limit is None:
                raise SimulationProbeError("route capability limit coverage is incomplete")
            arm_options["capability_limits"] = limit
        attempts.append(evaluate_route_arm(
            task, request, candidate, arm, actor, **arm_options,
        ))
    selected = next((item["arm"] for item in attempts if item["status"] == "pass"), None)
    return {
        "candidate_ref": candidate["candidate_ref"],
        "selected_arm": selected,
        "status": "pass" if selected else "fail",
        "arm_attempts": attempts,
        "motion_authorized": False,
    }


class RoboTwinRouteEvaluator:
    """Injected implementation for the existing route-readiness worker."""

    def __init__(self, runtime_root, runtime_profile, artifact_root, *, diagnose_failure=False, backend=None,
                 contact_arms=None, contact_qualification_mode=None, deadline=None):
        self.runtime_root = runtime_root
        self.runtime_profile = runtime_profile
        self.artifact_root = artifact_root
        self.diagnose_failure = diagnose_failure
        self.backend = backend
        self.contact_arms = contact_arms
        self.contact_qualification_mode = contact_qualification_mode
        self.deadline = deadline

    def __call__(self, request):
        import hashlib
        import json

        from robotwin_backend import (
            RoboTwinRuntimeProfile,
            RoboTwinSensorBackend,
            load_runtime_profile,
        )

        def artifact(ref, digest):
            from robotwin20_adapter.route_evidence import _artifact_path

            path = _artifact_path(self.artifact_root, ref)
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != digest:
                raise SimulationProbeError("route input artifact digest mismatch")
            return json.loads(data)

        profile = load_runtime_profile(self.runtime_profile)
        motion = validate_motion_policy_bindings(
            self.artifact_root,
            request,
            robot_identity=profile["robot_identity"],
        )
        capability_limits = {
            arm_id: controller_limits(capability)
            for arm_id, capability in motion["motion_capability_documents"].items()
        }
        owned = self.backend is None
        expected_scene = (f"{profile['task_name']}-{profile['seed']}-1" if owned
                          else self.backend.snapshot()["scene_revision"])
        if request["scene_revision"] != expected_scene:
            raise SimulationProbeError("route scene revision differs from runtime profile")
        world = artifact(
            request["collision_world"]["artifact_ref"], request["collision_world"]["sha256"]
        )
        scene = artifact(world["source_scene_facts_ref"], world["source_scene_facts_sha256"])
        if world["scene_revision"] != expected_scene or scene["scene_revision"] != expected_scene:
            raise SimulationProbeError("route collision world or source facts are stale")
        backend = self.backend if not owned else RoboTwinSensorBackend(
            RoboTwinRuntimeProfile(
                runtime_root=self.runtime_root,
                artifact_root=self.artifact_root,
                task_name=profile["task_name"],
                task_config=profile["task_config"],
                embodiment=profile["embodiment"],
                additional_static_cameras=profile["additional_static_cameras"],
            )
        )
        try:
            if owned:
                backend.reset(seed=profile["seed"])
            task = backend._task
            if (("observed_collision" in world
                 or any(
                     c.get("attached_object", {}).get("object_frame_id", "").startswith(
                         "observed-envelope/"
                     )
                     for c in request["candidates"]
                 ))
                    and scene.get("geometry_source") != "observation"):
                raise SimulationProbeError("observed route requires observed collision geometry")
            if scene.get("geometry_source") == "observation":
                task._paos_observed_support = scene.get("support_surface")
            from robotwin_observed_collision import configure_observed_collision
            configure_observed_collision(task, world, self.artifact_root)
            if not owned:
                from robotwin_simulation_probe_worker import (
                    _validate_route_input_artifacts,
                    _validate_runtime_route_input_binding,
                )
                for candidate in request["candidates"]:
                    inputs = _validate_route_input_artifacts(self.artifact_root, request, candidate)
                    _validate_runtime_route_input_binding(task, candidate, inputs)
            world_evidence = prepare_planning_world(task, world)
            results = {}
            for candidate in request["candidates"]:
                record = next(
                    item
                    for item in scene["objects"]
                    if item["entity_ref"] == candidate["entity_ref"]
                )
                if self.contact_arms is not None:
                    from robotwin_contact_qualification import (
                        qualify_observed_contact,
                        qualify_planner_world_contact,
                    )
                    from robotwin_simulation_probe_worker import _load_json_artifact

                    from robotwin20_adapter.contact_qualification import (
                        OBSERVED_OCCUPANCY,
                        PLANNER_WORLD_ONLY,
                    )

                    if scene.get("geometry_source") != "observation":
                        raise SimulationProbeError("persistent contact qualification requires observed geometry")
                    adaptation = _load_json_artifact(self.artifact_root, candidate["execution_grasp"]["adaptation_provenance_ref"])
                    if self.contact_qualification_mode == OBSERVED_OCCUPANCY:
                        if getattr(task, "_paos_observed_collision", None) is None:
                            raise SimulationProbeError(
                                "observed_occupancy contact qualification requires observed collision data"
                            )
                        result = qualify_observed_contact(
                            task, request, candidate, record, adaptation,
                            self.contact_arms, self.deadline, runtime_profile=dict(profile),
                        )
                    elif self.contact_qualification_mode == PLANNER_WORLD_ONLY:
                        result = qualify_planner_world_contact(
                            task, request, candidate, adaptation,
                            self.contact_arms, self.deadline,
                        )
                    else:
                        raise SimulationProbeError("contact qualification mode is unsupported")
                    results[candidate["candidate_ref"]] = result
                    continue
                actor = (ObservedGeometryActor(record["world_T_object"])
                         if scene.get("geometry_source") == "observation"
                         else getattr(task, record["actor_name"]))
                route_options = {
                    "diagnose_failure": self.diagnose_failure,
                    "initial_dual_arm_state": world_evidence["dual_arm_state"],
                }
                if capability_limits:
                    route_options["capability_limits"] = capability_limits
                results[candidate["candidate_ref"]] = evaluate_route(
                    task, request, candidate, actor, **route_options,
                )
            return {
                "candidates": results,
                "world": world_evidence,
                "runtime_profile": dict(profile),
                "runtime_root": str(self.runtime_root),
                "simulator_steps": 0,
                "motion_authorized": False,
            }
        finally:
            if owned:
                backend.close()
