"""Explicit no-motion ablation of a rejected attached segment.

The robot-only result is diagnostic evidence and can never replace the
production attached-route result. The full table/blocks/peer world stays loaded.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from robotwin_planning_geometry import (
    _joint_limits,
    _table_top_z,
    _validate_gripper_table_clearance,
    _validate_trajectory,
)


def sphere_box_clearance(center, radius, pose, dimensions):
    import transforms3d.quaternions as tquat

    local = np.asarray(tquat.quat2mat(pose[3:])).T @ (np.asarray(center) - pose[:3])
    distance = np.abs(local) - np.asarray(dimensions) / 2
    return float(np.linalg.norm(np.maximum(distance, 0)) + min(float(distance.max()), 0) - radius)


def diagnose_attached_segment(task: Any, candidate, arm, actor, pose, start_qpos):
    from curobo.types.robot import JointState

    planner = getattr(task.robot, f"{arm}_planner")
    model = planner.motion_gen
    attachment = model.kinematics.kinematics_config.get_link_spheres("attached_object").clone()
    model.detach_object_from_robot()
    try:
        robot_only = getattr(task.robot, f"{arm}_plan_path")(pose, last_qpos=list(start_qpos))
        _validate_trajectory(robot_only, _joint_limits(planner))
        target = np.asarray(robot_only["position"])[-1]
        robot_spheres = (
            model.kinematics.get_state(model.tensor_args.to_device(target.reshape(1, -1)))
            .get_link_spheres()[0]
            .cpu()
            .numpy()
            .copy()
        )
        mesh_result = "pass"
        try:
            _validate_gripper_table_clearance(
                task, arm, robot_only["position"], phase="descent", gripper_state="closed"
            )
        except ValueError as exc:
            mesh_result = str(exc)
    finally:
        # Restore the exact existing approximation rather than resampling the box.
        model.attach_spheres_to_robot(sphere_tensor=attachment, link_name="attached_object")
    q = model.tensor_args.to_device(target.reshape(1, -1))
    attached_spheres = model.kinematics.get_state(q).get_link_spheres()[0].cpu().numpy()
    valid, status = model.check_start_state(
        JointState.from_position(q, joint_names=planner.active_joints_name)
    )
    minima = {}
    collisions = []
    for index, sphere in enumerate(attached_spheres):
        if sphere[3] <= 0:
            continue
        group = "attached_object" if robot_spheres[index, 3] <= 0 else "robot"
        for box in model.world_model.cuboid:
            distance = sphere_box_clearance(sphere[:3], sphere[3], box.pose, box.dims)
            key = f"{group}:{box.name}"
            minima[key] = min(minima.get(key, float("inf")), distance)
            if distance < 0:
                collisions.append(
                    {
                        "group": group,
                        "sphere_index": index,
                        "obstacle": box.name,
                        "clearance_m": distance,
                        "radius_m": float(sphere[3]),
                        "center_to_box_distance_m": distance + float(sphere[3]),
                    }
                )
    import transforms3d.quaternions as tquat

    placement = candidate["placement_target"]["target_object_pose"]
    quaternion = placement["orientation_xyzw"]
    rotation = tquat.quat2mat([quaternion[3], *quaternion[:3]])
    bottom = float(placement["position_m"][2]) - sum(
        abs(rotation[2, i]) * candidate["attached_object"]["half_extents_m"][i] for i in range(3)
    )
    return {
        "robot_only_status": "success",
        "robot_mesh_clearance": mesh_result,
        "attached_target_valid": bool(valid),
        "attached_target_status": str(status),
        "minimum_clearances_m": minima,
        "colliding_spheres": collisions,
        "target_qpos": target.tolist(),
        "motion_authorized": False,
        "diagnostic_only": True,
        "desired_object_support_clearance_m": bottom - _table_top_z(task),
    }
