"""One observation-owned collision representation for readiness and execution."""

import json

import numpy as np
from robotwin_planning_geometry import _quat_matrix_wxyz

from robotwin20_adapter.observed_binding import rigid_transform
from robotwin20_adapter.observed_collision import (
    ObservedCollisionPolicy,
    depth_points,
    inside_convex,
    voxel_boxes,
)
from robotwin20_adapter.route_evidence import _artifact_path


def collision_components(component):
    """Keep separate convex shapes separate instead of filling their union hull."""
    pose = component.get_pose()
    rotation = _quat_matrix_wxyz(pose.q)
    parts = []
    for shape in component.get_collision_shapes():
        local_pose = shape.get_local_pose()
        if callable(getattr(shape, "get_vertices", None)):
            vertices = np.asarray(shape.get_vertices(), dtype=float)
        elif callable(getattr(shape, "get_half_size", None)):
            from itertools import product
            vertices = np.array(list(product((-1, 1), repeat=3))) * shape.get_half_size()
        else:
            raise ValueError("robot collision shape cannot be represented as a convex component")
        parts.append((vertices @ _quat_matrix_wxyz(local_pose.q).T + local_pose.p) @ rotation.T + pose.p)
    return parts


def configure_observed_collision(task, world, root):
    """Load full depth; self filtering uses measured robot geometry, never actors."""
    descriptor = world.get("observed_collision")
    if descriptor is None:
        if getattr(task, "_paos_observed_collision", None) is None:
            return
        task._paos_observed_collision = None
        for arm in ("left", "right"):
            getattr(task.robot, f"{arm}_planner")._paos_observed_collision = None
        return
    if (descriptor["scene_revision"] != world["scene_revision"]
            or descriptor["target_entity_ref"] != world["target_entity_ref"]
            or descriptor["calibration_ref"] != world["calibration_ref"]):
        raise ValueError("observed collision lineage differs from world")
    # Geometry changes invalidate this in-memory reuse; no extra persistent state.
    robot_poses = tuple(
        tuple((tuple(link.get_pose().p), tuple(link.get_pose().q))
              for link in getattr(task.robot, f"{arm}_entity").get_links())
        for arm in ("left", "right"))
    previous = getattr(task, "_paos_observed_collision", None)
    support = getattr(task, "_paos_observed_support", None)
    support_z = (float(support["position_m"][2]) + float(support["half_extents_m"][2])
                 if support is not None else None)
    if (previous is not None and previous["descriptor"] == descriptor
            and previous["robot_poses"] == robot_poses and previous.get("support_z") == support_z):
        return
    calibration = json.loads(_artifact_path(root, descriptor["calibration_ref"]).read_text())
    transform = rigid_transform(descriptor["world_T_camera"])
    if (calibration["camera_name"] != descriptor["frame_id"]
            or not np.allclose(np.linalg.inv(rigid_transform(calibration["extrinsic_cv"])), transform, atol=1e-6, rtol=0)):
        raise ValueError("observed collision calibration differs from binding")
    depth = np.load(_artifact_path(root, descriptor["depth_ref"] + ".npy"), allow_pickle=False)
    mask = np.load(_artifact_path(root, descriptor["target_mask_ref"] + ".npy"), allow_pickle=False)
    if mask.shape != depth.shape:
        raise ValueError("target mask differs from scene depth")
    policy = ObservedCollisionPolicy(**descriptor["policy"])
    points, ys, xs = depth_points(depth, calibration["intrinsic_cv"], transform, policy.depth_scale_to_m)
    selected = mask[ys, xs].astype(bool)
    if not selected.any():
        raise ValueError("target mask has no observed metric points")
    robot = np.zeros(len(points), dtype=bool)
    for arm in ("left", "right"):
        for link in getattr(task.robot, f"{arm}_entity").get_links():
            for vertices in collision_components(link):
                robot |= inside_convex(points, vertices, policy.uncertainty_m)
    # Conflicting target/self labels are not silently erased.
    if (robot & selected).any():
        raise ValueError("observed target overlaps robot self geometry")
    environment = points[~selected & ~robot]
    boxes, cell_count = voxel_boxes(environment, policy.voxel_size_m, policy.uncertainty_m,
                                   support_z=support_z, refinement_band=policy.support_refinement_band_m)
    value = {"descriptor": descriptor, "robot_poses": robot_poses, "policy": policy, "support_z": support_z,
             "target": points[selected], "environment": environment, "boxes": boxes,
             "depth": depth, "intrinsic": np.asarray(calibration["intrinsic_cv"]), "world_T_camera": transform,
             "evidence": {"scene_revision": world["scene_revision"], "depth_ref": descriptor["depth_ref"],
                 "target_mask_ref": descriptor["target_mask_ref"], "valid_depth_points": len(points),
                 "target_points": int(selected.sum()), "robot_self_points": int(robot.sum()),
                 "environment_points": len(environment), "occupied_voxels": cell_count, "merged_boxes": len(boxes),
                 "voxel_size_m": policy.voxel_size_m, "uncertainty_m": policy.uncertainty_m,
                 "support_refinement_band_m": policy.support_refinement_band_m,
                 "support_vertical_cell_m": min(policy.voxel_size_m, policy.uncertainty_m),
                 "support_refinement_applied": support_z is not None and policy.support_refinement_band_m > 0,
                 "visibility_scope": "observed_only", "unobserved_space": "unknown", "motion_authorized": False}}
    task._paos_observed_collision = value
    for arm in ("left", "right"):
        getattr(task.robot, f"{arm}_planner")._paos_observed_collision = value
