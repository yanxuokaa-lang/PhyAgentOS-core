"""Provider-owned no-motion evaluation of execution grasps and full routes."""

from __future__ import annotations

from typing import Any, Mapping

from robotwin_curobo_world_port import (
    add_released_object,
    apply_collision_world,
    bind_scene_table,
    capture_peer_projection,
)
from robotwin_planning_geometry import (
    SimulationProbeError,
    _attach_object_to_planner,
    _capture_dual_arm_state,
    _joint_limits,
    _route_pose,
    _table_top_z,
    _validate_attached_support_departure,
    _validate_gripper_table_clearance,
    _validate_trajectory,
    _validate_world_pose,
)


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
    import numpy as np

    planner = getattr(task.robot, f"{arm}_planner")
    try:
        pose = _route_pose(execution_grasp["robot_target_pose"], "world")
        approach = list(pose)
        for i in range(3):
            approach[i] -= approach_clearance_m * execution_grasp["ingress_direction"]["vector"][i]
        plan = getattr(task.robot, f"{arm}_plan_path")
        ingress = plan(approach)
        _validate_trajectory(ingress, _joint_limits(planner))
        _validate_gripper_table_clearance(
            task, arm, ingress["position"], phase="approach", gripper_state="open"
        )
        predicted = np.asarray(getattr(task.robot, f"{arm}_entity").get_qpos()).copy()
        predicted[:7] = np.asarray(ingress["position"])[-1]
        result = plan(pose, last_qpos=predicted.tolist())
        _validate_trajectory(result, _joint_limits(planner))
        _validate_gripper_table_clearance(
            task, arm, result["position"], phase="contact", gripper_state="open"
        )
        clearance = sphere_support_clearance(task, arm, result["position"][-1])
        return {"planner_status": "success", "clearance_m": clearance}
    except Exception as exc:
        return {"planner_status": "failed", "clearance_m": None, "reason": str(exc)}


def evaluate_route_arm(
    task: Any, request: Mapping[str, Any], candidate: Mapping[str, Any], arm: str, actor: Any
) -> dict[str, Any]:
    """Plan serially from predicted endpoints, restoring geometry in all cases.

    SAPIEN qpos is used only for FK and attachment geometry. No scene step,
    drive target, controller command, or Gateway invocation occurs here.
    """
    import numpy as np

    planner = getattr(task.robot, f"{arm}_planner")
    entity = getattr(task.robot, f"{arm}_entity")
    original = np.asarray(entity.get_qpos()).copy()
    predicted = original.copy()
    attached = False
    phase_name = "approach"
    index = 0
    segments = []
    previous_worlds = []
    try:
        limits = _joint_limits(planner)
        for phase in candidate["route"]:
            phase_name = phase["phase"]
            if phase_name == "retreat" and attached:
                planner.motion_gen.detach_object_from_robot()
                attached = False
                previous_worlds = add_released_object(
                    planner,
                    candidate["placement_target"]["target_object_pose"],
                    candidate["attached_object"]["half_extents_m"],
                )
            for index, waypoint in enumerate(phase["waypoints"]):
                pose = _route_pose(waypoint, request["frame_id"])
                _validate_world_pose(
                    pose,
                    request["workspace_bounds_m"],
                    candidate["attached_object"]["half_extents_m"],
                )
                result = getattr(task.robot, f"{arm}_plan_path")(pose, last_qpos=predicted.tolist())
                _validate_trajectory(result, limits)
                _validate_gripper_table_clearance(
                    task,
                    arm,
                    result["position"],
                    phase=phase_name,
                    gripper_state=phase["gripper_state"],
                )
                if phase_name == "lift" and not attached:
                    entity.set_qpos(predicted.tolist())
                    # Keep cleanup armed even if Curobo raises during attach.
                    attached = True
                    _attach_object_to_planner(
                        task, planner, actor, candidate["attached_object"]["half_extents_m"], arm
                    )
                    _validate_attached_support_departure(planner, result["position"])
                predicted[:7] = np.asarray(result["position"])[-1]
                segments.append(
                    {
                        "phase": phase_name,
                        "waypoint_index": index,
                        "status": "pass",
                        "end_qpos": predicted[:7].tolist(),
                    }
                )
        return {"arm": arm, "status": "pass", "segments": segments, "motion_authorized": False}
    except Exception as exc:
        return {
            "arm": arm,
            "status": "fail",
            "failed_phase": phase_name,
            "failed_waypoint_index": index,
            "detail": str(exc),
            "segments": segments,
            "motion_authorized": False,
        }
    finally:
        try:
            if attached:
                planner.motion_gen.detach_object_from_robot()
        finally:
            try:
                for model, world in previous_worlds:
                    model.update_world(world)
            finally:
                entity.set_qpos(original.tolist())


def evaluate_route(
    task: Any, request: Mapping[str, Any], candidate: Mapping[str, Any], actor: Any
) -> dict[str, Any]:
    attempts = [
        evaluate_route_arm(task, request, candidate, arm, actor) for arm in ("left", "right")
    ]
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

    def __init__(self, runtime_root, runtime_profile, artifact_root):
        self.runtime_root = runtime_root
        self.runtime_profile = runtime_profile
        self.artifact_root = artifact_root

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
        if request["scene_revision"] != f"{profile['task_name']}-{profile['seed']}-1":
            raise SimulationProbeError("route scene revision differs from runtime profile")
        world = artifact(
            request["collision_world"]["artifact_ref"], request["collision_world"]["sha256"]
        )
        scene = artifact(world["source_scene_facts_ref"], world["source_scene_facts_sha256"])
        backend = RoboTwinSensorBackend(
            RoboTwinRuntimeProfile(
                runtime_root=self.runtime_root,
                artifact_root=self.artifact_root,
                task_name=profile["task_name"],
                task_config=profile["task_config"],
                embodiment=profile["embodiment"],
            )
        )
        try:
            backend.reset(seed=profile["seed"])
            task = backend._task
            world_evidence = prepare_planning_world(task, world)
            results = {}
            for candidate in request["candidates"]:
                record = next(
                    item
                    for item in scene["objects"]
                    if item["entity_ref"] == candidate["entity_ref"]
                )
                actor = getattr(task, record["actor_name"])
                results[candidate["candidate_ref"]] = evaluate_route(
                    task, request, candidate, actor
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
            backend.close()
