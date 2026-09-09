"""Shared RoboTwin planner geometry checks; no controller or scene stepping."""

from __future__ import annotations

import math
from typing import Any, Mapping

from robotwin20_adapter.dual_arm_state import build_dual_arm_state

_GRIPPER_VALUES = {"open": 1.0, "contact": 1.0, "closed": 0.0, "released": 1.0}


class SimulationProbeError(ValueError):
    """The provider request or runtime result is unsafe or incomplete."""


def _route_pose(pose_value: Mapping[str, Any], route_frame_id: str) -> list[float]:
    import numpy as np
    import transforms3d as t3d

    if pose_value.get("frame_id") != route_frame_id:
        raise SimulationProbeError("route pose frame binding is invalid")
    q = np.asarray(pose_value["orientation_xyzw"], dtype=np.float64)
    norm = float(np.linalg.norm(q))
    if norm <= 1e-9 or not math.isfinite(norm):
        raise SimulationProbeError("candidate orientation is degenerate")
    q = q / norm
    position = np.asarray(pose_value["position_m"], dtype=np.float64)
    if position.shape != (3,) or not bool(np.isfinite(position).all()):
        raise SimulationProbeError("route pose position is invalid")
    q_wxyz = t3d.quaternions.mat2quat(t3d.quaternions.quat2mat([q[3], q[0], q[1], q[2]]))
    return position.tolist() + q_wxyz.tolist()


def _joint_limits(planner: Any) -> list[list[float]]:
    try:
        kinematics = planner.motion_gen.robot_cfg.kinematics
        limits = getattr(kinematics, "joint_limits", None)
        if limits is None:
            limits = kinematics.kinematics_config.joint_limits
        tensor = limits.position
        values = tensor.detach().cpu().tolist()
    except Exception as exc:
        raise SimulationProbeError("planner joint limits are unavailable") from exc
    if not isinstance(values, list) or len(values) != 2 or any(len(row) != 7 for row in values):
        raise SimulationProbeError("planner joint limits have unexpected shape")
    converted = [[float(item) for item in row] for row in values]
    if any(not math.isfinite(item) for row in converted for item in row) or any(
        low >= high for low, high in zip(converted[0], converted[1])
    ):
        raise SimulationProbeError("planner joint limits are invalid")
    return converted


def _validate_trajectory(
    result: Mapping[str, Any],
    limits: list[list[float]],
) -> None:
    import numpy as np

    if result.get("status") != "Success":
        raise SimulationProbeError("planner route segment failed")
    source_positions = np.asarray(result.get("position"))
    source_velocities = np.asarray(result.get("velocity"))
    if not np.issubdtype(source_positions.dtype, np.floating) or not np.issubdtype(
        source_velocities.dtype, np.floating
    ):
        raise SimulationProbeError("planner trajectory dtype is not floating point")
    positions = source_positions.astype(np.float64, copy=False)
    velocities = source_velocities.astype(np.float64, copy=False)
    if positions.ndim != 2 or positions.shape[1] != 7 or velocities.shape != positions.shape:
        raise SimulationProbeError("planner trajectory shape is invalid")
    if not np.isfinite(positions).all() or not np.isfinite(velocities).all():
        raise SimulationProbeError("planner trajectory contains non-finite values")
    low, high = np.asarray(limits[0]), np.asarray(limits[1])
    if bool((positions < low - 1e-5).any()) or bool((positions > high + 1e-5).any()):
        raise SimulationProbeError("planner trajectory exceeds joint limits")


def _validate_support_departure_results(results: list[tuple[bool, Any]]) -> None:
    """Accept only a leading support-world contact that clears and stays clear."""

    cleared = False
    for valid, status in results:
        if valid:
            cleared = True
            continue
        status_value = getattr(status, "value", str(status))
        if cleared or status_value != "Start state is colliding with world":
            raise SimulationProbeError("attached lift trajectory is collision-invalid")
    if not cleared:
        raise SimulationProbeError("attached object never clears its support world")


def _validate_attached_support_departure(planner: Any, positions: Any) -> None:
    """Check a robot-only lift plan again with the object attached.

    A resting object necessarily starts in contact with the support table, so
    Curobo rejects that state when the object becomes a robot attachment.  The
    lift is first planned with the robot model, then every planned sample is
    rechecked with the attachment.  Only a leading world-contact prefix is
    accepted; after the first clear sample, every remaining sample must stay
    collision-free.
    """

    import numpy as np
    import torch
    from curobo.types.robot import JointState

    check_start_state = getattr(planner.motion_gen, "check_start_state", None)
    if not callable(check_start_state):
        raise SimulationProbeError("planner cannot validate attached support departure")
    results: list[tuple[bool, Any]] = []
    for sample in np.asarray(positions, dtype=np.float32):
        state = JointState.from_position(
            torch.as_tensor(sample, dtype=torch.float32, device="cuda").reshape(1, -1),
            joint_names=planner.active_joints_name,
        )
        valid, status = check_start_state(state)
        results.append((bool(valid), status))
    _validate_support_departure_results(results)


def _quat_matrix_wxyz(quaternion: Any) -> Any:
    import numpy as np

    w, x, y, z = [float(item) for item in quaternion]
    return np.asarray(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def _collision_vertices(component: Any) -> Any:
    """Return component collision vertices in world coordinates, without stepping."""
    import numpy as np

    shapes = component.get_collision_shapes()
    component_pose = component.get_pose()
    component_rotation = _quat_matrix_wxyz(component_pose.q)
    vertices: list[Any] = []
    for shape in shapes:
        local_pose = shape.get_local_pose()
        local_rotation = _quat_matrix_wxyz(local_pose.q)
        get_vertices = getattr(shape, "get_vertices", None)
        if callable(get_vertices):
            local_vertices = np.asarray(get_vertices(), dtype=np.float64)
        else:
            half_size_getter = getattr(shape, "get_half_size", None)
            if not callable(half_size_getter):
                raise SimulationProbeError("collision shape vertices are unavailable")
            half_size = np.asarray(half_size_getter(), dtype=np.float64)
            if (
                half_size.shape != (3,)
                or not np.isfinite(half_size).all()
                or (half_size <= 0).any()
            ):
                raise SimulationProbeError("collision box dimensions are invalid")
            local_vertices = np.asarray(
                [
                    [sx * half_size[0], sy * half_size[1], sz * half_size[2]]
                    for sx in (-1, 1)
                    for sy in (-1, 1)
                    for sz in (-1, 1)
                ],
                dtype=np.float64,
            )
        if local_vertices.ndim != 2 or local_vertices.shape[1] != 3:
            raise SimulationProbeError("collision shape vertices are invalid")
        vertices.append(
            (local_vertices @ local_rotation.T + np.asarray(local_pose.p, dtype=np.float64))
            @ component_rotation.T
            + np.asarray(component_pose.p, dtype=np.float64)
        )
    if not vertices:
        raise SimulationProbeError("collision shape vertices are unavailable")
    return np.concatenate(vertices, axis=0)


def _table_top_z(task: Any) -> float:
    table = getattr(task, "table", None)
    if table is None:
        raise SimulationProbeError("RoboTwin scene table is unavailable")
    component = next(
        (
            item
            for item in table.get_components()
            if callable(getattr(item, "get_collision_shapes", None))
        ),
        None,
    )
    if component is None:
        raise SimulationProbeError("RoboTwin scene table collision geometry is unavailable")
    vertices = _collision_vertices(component)
    top = float(vertices[:, 2].max())
    if not math.isfinite(top):
        raise SimulationProbeError("RoboTwin scene table top is non-finite")
    return top


def _validate_gripper_table_clearance(
    task: Any, arm: str, positions: Any, *, phase: str, gripper_state: str | None = None
) -> None:
    """Reject a route sample whose real finger meshes penetrate the table.

    This is a provider-owned geometry qualification, not a grasp adjustment:
    it uses the loaded RoboTwin collision meshes at the planned joint samples
    and never inserts a positional offset or a tolerance.
    """
    import numpy as np

    entity = task.robot.left_entity if arm == "left" else task.robot.right_entity
    links = [
        link
        for link in entity.get_links()
        if link.get_name() in {"panda_hand", "panda_leftfinger", "panda_rightfinger"}
    ]
    if len(links) != 3:
        raise SimulationProbeError("RoboTwin gripper collision links are unavailable")
    original = np.asarray(entity.get_qpos(), dtype=np.float64).copy()
    geometry_qpos = original.copy()
    table_top = _table_top_z(task)
    if gripper_state is not None:
        if gripper_state not in _GRIPPER_VALUES:
            raise SimulationProbeError("gripper state is invalid for clearance qualification")
        gripper = task.robot.left_gripper if arm == "left" else task.robot.right_gripper
        scale = task.robot.left_gripper_scale if arm == "left" else task.robot.right_gripper_scale
        joint_indices = {
            joint.get_name(): index for index, joint in enumerate(entity.get_active_joints())
        }
        normalized = _GRIPPER_VALUES[gripper_state]
        real_value = float(scale[0]) + normalized * (float(scale[1]) - float(scale[0]))
        for joint, multiplier, offset in gripper:
            index = joint_indices.get(joint.get_name())
            if index is not None:
                geometry_qpos[index] = real_value * float(multiplier) + float(offset)
    try:
        for sample in np.asarray(positions, dtype=np.float64):
            qpos = geometry_qpos.copy()
            qpos[:7] = sample
            entity.set_qpos(qpos.tolist())
            minimum = min(float(_collision_vertices(link)[:, 2].min()) for link in links)
            if minimum < table_top:
                raise SimulationProbeError(
                    f"{phase} gripper collision geometry penetrates table "
                    f"(minimum_z={minimum:.6f}, table_top_z={table_top:.6f})"
                )
    finally:
        entity.set_qpos(original.tolist())


def _validate_world_pose(
    pose: list[float], bounds: Mapping[str, Any], half_extents: list[float]
) -> None:
    conservative_extent = max(half_extents)
    for axis, coordinate in zip("xyz", pose[:3]):
        if coordinate - conservative_extent < float(
            bounds[f"{axis}_min_m"]
        ) or coordinate + conservative_extent > float(bounds[f"{axis}_max_m"]):
            raise SimulationProbeError(
                "world-frame route waypoint or attached object exceeds workspace bounds"
            )


def _attach_object_to_planner(
    task: Any, planner: Any, actor: Any, half_extents: list[float], arm: str
) -> dict[str, Any]:
    """Attach the observed object geometry to Curobo's dedicated attached link."""
    try:
        import numpy as np
        import torch
        from curobo.geom.types import Cuboid
        from curobo.types.robot import JointState

        base_pose = np.asarray(
            list(planner.robot_origion_pose.p) + list(planner.robot_origion_pose.q),
            dtype=np.float64,
        )
        object_pose = np.asarray(
            list(actor.get_pose().p) + list(actor.get_pose().q), dtype=np.float64
        )
        base_position, base_quaternion = planner._trans_from_world_to_base(base_pose, object_pose)
        obstacle = Cuboid(
            name="probe_attached_object",
            pose=list(base_position) + list(base_quaternion),
            dims=[2.0 * float(item) for item in half_extents],
        )
        entity = task.robot.left_entity if arm == "left" else task.robot.right_entity
        qpos = entity.get_qpos()
        joint_state = JointState.from_position(
            torch.tensor(qpos[:7], dtype=torch.float32, device="cuda").reshape(1, -1),
            joint_names=planner.active_joints_name,
        )
        surface_sphere_radius_m = 0.001
        link_name = "attached_object"
        if not planner.motion_gen.attach_external_objects_to_robot(
            joint_state,
            [obstacle],
            surface_sphere_radius=surface_sphere_radius_m,
            link_name=link_name,
        ):
            raise SimulationProbeError("planner rejected attached object geometry")
        return {
            "status": "attached",
            "planner_link_name": link_name,
            "object_name": obstacle.name,
            "object_dimensions_m": [2.0 * float(item) for item in half_extents],
            "surface_sphere_radius_m": surface_sphere_radius_m,
            "active_route_phases": ["lift", "transport", "descent", "release"],
        }
    except SimulationProbeError:
        raise
    except Exception as exc:
        raise SimulationProbeError(
            "attached object geometry could not be added to planner"
        ) from exc


def _capture_dual_arm_state(task: Any, scene_revision: str) -> dict[str, Any]:
    """Capture the stabilized provider state used by sequential route planning."""
    import numpy as np

    def arm_payload(entity: Any, gripper: Any) -> dict[str, Any]:
        qpos = [float(item) for item in entity.get_qpos()[:7]]
        joints = list(entity.get_active_joints())[:7]
        targets: list[float] = []
        for joint in joints:
            value = joint.get_drive_target()
            value = value[0] if isinstance(value, (list, tuple, np.ndarray)) else value
            targets.append(float(value))
        links: list[dict[str, Any]] = []
        for link in entity.get_links():
            pose = link.get_pose()
            links.append(
                {
                    "link_id": f"placeholder:{link.get_name()}",
                    "link_name": str(link.get_name()),
                    "pose_wxyz": [*map(float, pose.p), *map(float, pose.q)],
                }
            )
        # build_dual_arm_state assigns the arm-qualified identity; remove the
        # temporary value only after preserving the provider link name.
        return {"qpos": qpos, "drive_target": targets, "gripper": float(gripper), "links": links}

    left = arm_payload(task.robot.left_entity, task.robot.get_left_gripper_val())
    right = arm_payload(task.robot.right_entity, task.robot.get_right_gripper_val())
    left["links"] = [{**item, "link_id": f"left:{item['link_name']}"} for item in left["links"]]
    right["links"] = [{**item, "link_id": f"right:{item['link_name']}"} for item in right["links"]]
    return build_dual_arm_state(
        scene_revision=scene_revision,
        state_revision=f"{scene_revision}:stabilized",
        frame_id="world",
        left=left,
        right=right,
        held_arm_policy="hold",
        provenance_refs=[f"artifact://simulation-probe/{scene_revision}/dual-arm-state"],
    )
