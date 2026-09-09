"""RoboTwin-only bridge from PAOS collision-world artifacts to Curobo."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from robotwin20_adapter.collision_world import validate_collision_world
from robotwin20_adapter.dual_arm_state import (
    PEER_ARM_SPHERE_PROJECTION_SCHEMA_VERSION,
    DualArmStateError,
    build_peer_arm_sphere_projection,
    validate_peer_arm_projection,
    validate_peer_arm_sphere_projection,
)


class CuroboWorldPortError(RuntimeError):
    """The provider could not apply a collision world to all planners."""


def bind_scene_table(task: Any) -> None:
    """Bind the measured support box to both provider planners without stepping."""
    table = getattr(task, "table", None)
    table_pose = table.get_pose() if table is not None and callable(getattr(table, "get_pose", None)) else None
    if table_pose is None:
        raise CuroboWorldPortError("RoboTwin scene table pose is unavailable")
    table_component = next(
        (item for item in table.get_components() if callable(getattr(item, "get_collision_shapes", None))),
        None,
    )
    table_shapes = table_component.get_collision_shapes() if table_component is not None else []
    table_top_shape = next(
        (shape for shape in table_shapes if callable(getattr(shape, "get_half_size", None))),
        None,
    )
    if table_top_shape is None:
        raise CuroboWorldPortError("RoboTwin scene table box geometry is unavailable")
    table_center = table_pose * table_top_shape.get_local_pose()
    half_size = [float(value) for value in table_top_shape.get_half_size()]
    table_binding = {
        "position_m": [float(value) for value in table_center.p],
        "orientation_wxyz": [float(value) for value in table_center.q],
        "half_extents_m": half_size,
    }
    if not all(math.isfinite(value) for value in (*table_binding["position_m"], *table_binding["orientation_wxyz"], *half_size)):
        raise CuroboWorldPortError("RoboTwin scene table pose is non-finite")
    for arm in ("left", "right"):
        planner = getattr(task.robot, f"{arm}_planner")
        planner.arm_id = arm
        planner._paos_table_world_pose = dict(table_binding)


def capture_peer_projection(task: Any, state: Mapping[str, Any], selected_arm: str) -> dict[str, Any]:
    """Project the held arm using Curobo's native collision-sphere model.

    RoboTwin's SAPIEN links are mesh/convex geometry and cannot be represented
    safely by the old single-box extraction.  Curobo already owns a sphere
    approximation for the same robot model, so use that model at the captured
    hold qpos and transform its centers into the shared world frame.
    """
    import numpy as np
    import torch
    import transforms3d.quaternions as tquat

    peer_arm = "right" if selected_arm == "left" else "left"
    planner = task.robot.right_planner if peer_arm == "right" else task.robot.left_planner
    kinematics = getattr(getattr(planner, "motion_gen", None), "kinematics", None)
    get_spheres = getattr(kinematics, "get_robot_as_spheres", None)
    if not callable(get_spheres):
        raise CuroboWorldPortError("peer arm collision sphere model is unavailable")
    entity = task.robot.right_entity if peer_arm == "right" else task.robot.left_entity
    qpos = np.asarray(entity.get_qpos()[:7], dtype=np.float32).reshape(1, -1)
    tensor_args = getattr(planner.motion_gen, "tensor_args", None)
    device = getattr(tensor_args, "device", "cpu")
    try:
        sphere_batches = get_spheres(torch.as_tensor(qpos, device=device), filter_valid=True)
    except Exception as exc:
        raise CuroboWorldPortError("peer arm collision sphere model failed") from exc
    if not sphere_batches or not sphere_batches[0]:
        raise CuroboWorldPortError("peer arm collision sphere model is empty")
    base = planner.robot_origion_pose
    base_rotation = np.asarray(tquat.quat2mat(list(base.q)), dtype=np.float64)
    base_position = np.asarray(base.p, dtype=np.float64)
    spheres: list[dict[str, Any]] = []
    for sphere in sphere_batches[0]:
        pose = getattr(sphere, "pose", None)
        radius = getattr(sphere, "radius", None)
        if pose is None or radius is None or len(pose) < 3:
            raise CuroboWorldPortError("peer arm collision sphere record is invalid")
        center = base_position + base_rotation @ np.asarray(pose[:3], dtype=np.float64)
        spheres.append({"center_m": [*map(float, center)], "radius_m": float(radius)})
    try:
        return build_peer_arm_sphere_projection(
            scene_revision=state["scene_revision"],
            state_revision=state["state_revision"],
            frame_id=state["frame_id"],
            selected_arm=selected_arm,
            spheres=spheres,
            source_ref=state["provenance_refs"][0],
        )
    except DualArmStateError as exc:
        raise CuroboWorldPortError("peer arm projection is invalid") from exc


def _obb_capacity(motion_gen: Any) -> int:
    """Return the provider-reported OBB cache capacity (zero when unavailable)."""

    cache = getattr(motion_gen, "collision_cache", None)
    if isinstance(cache, Mapping):
        value = cache.get("obb")
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    checker = getattr(motion_gen, "world_coll_checker", None)
    tensors = getattr(checker, "_cube_tensor_list", None)
    if tensors:
        try:
            return int(tensors[0].shape[1])
        except (AttributeError, IndexError, TypeError, ValueError):
            return 0
    return 0


def _rebuild_motion_generators(
    planner: Any, world: Any, cache_capacity: int
) -> tuple[Any, Any]:
    """Build warmed MotionGen instances using RoboTwin's native planner settings."""

    from curobo.wrap.reacher.motion_gen import MotionGen, MotionGenConfig
    from envs import _GLOBAL_CONFIGS as CONFIGS

    yml_path = getattr(planner, "yml_path", None)
    if not yml_path:
        raise CuroboWorldPortError("planner does not expose its RoboTwin robot config")
    existing = planner.motion_gen
    common: dict[str, Any] = {
        "interpolation_dt": 1 / 250,
        "num_trajopt_seeds": 1,
        "collision_cache": {"obb": cache_capacity},
        "use_cuda_graph": bool(getattr(existing, "use_cuda_graph", True)),
    }
    tensor_args = getattr(existing, "tensor_args", None)
    if tensor_args is not None:
        common["tensor_args"] = tensor_args
    config = MotionGenConfig.load_from_robot_config(yml_path, world, **common)
    rebuilt = MotionGen(config)
    rebuilt.warmup()

    batch_common = dict(common)
    batch_common["num_graph_seeds"] = 1
    batch_config = MotionGenConfig.load_from_robot_config(yml_path, world, **batch_common)
    rebuilt_batch = MotionGen(batch_config)
    rebuilt_batch.warmup(batch=CONFIGS.ROTATE_NUM)
    return rebuilt, rebuilt_batch


def _world_pose_for_planner(planner: Any, pose: Mapping[str, Any]) -> list[float]:
    import numpy as np

    quaternion = pose["orientation_xyzw"]
    world_pose = np.asarray(
        [*pose["position_m"], quaternion[3], quaternion[0], quaternion[1], quaternion[2]],
        dtype=np.float64,
    )
    base_pose = np.asarray(
        [*planner.robot_origion_pose.p, *planner.robot_origion_pose.q], dtype=np.float64
    )
    position, rotation = planner._trans_from_world_to_base(base_pose, world_pose)
    return [*map(float, position), *map(float, rotation)]


def _native_table_geometry_for_planner(planner: Any) -> dict[str, Any] | None:
    """Project the scene table pose into the planner base frame when provided.

    RoboTwin's native ``CuroboPlanner`` seeds a table pose with a legacy
    shortcut that is not valid for the two-single-arm base frames.  The
    simulation worker binds the actual scene table collision box to each
    planner after reset; using its center, dimensions, and transform keeps the
    provider collision model in the scene's frame without changing grasp
    geometry.
    """

    pose = getattr(planner, "_paos_table_world_pose", None)
    if not isinstance(pose, Mapping):
        return None
    if set(pose) != {"position_m", "orientation_wxyz", "half_extents_m"}:
        raise CuroboWorldPortError("bound table world pose fields are invalid")
    position = pose["position_m"]
    orientation = pose["orientation_wxyz"]
    half_extents = pose["half_extents_m"]
    if (
        not isinstance(position, (list, tuple))
        or len(position) != 3
        or not isinstance(orientation, (list, tuple))
        or len(orientation) != 4
        or not isinstance(half_extents, (list, tuple))
        or len(half_extents) != 3
    ):
        raise CuroboWorldPortError("bound table world pose dimensions are invalid")
    values = [*position, *orientation, *half_extents]
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in values):
        raise CuroboWorldPortError("bound table world pose values are invalid")
    if any(float(item) <= 0 for item in half_extents):
        raise CuroboWorldPortError("bound table half extents are invalid")
    world_pose = {
        "position_m": [float(item) for item in position],
        # Curobo's world model uses its own planner-frame orientation.  The
        # SAPIEN table pose is in the scene frame; rotating it through the
        # robot-base transform would swap the support slab's thin axis into
        # the planner vertical axis.  Preserve the native table orientation
        # while projecting the measured center and dimensions.
        "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
    }
    base_world = getattr(getattr(planner, "motion_gen", None), "world_model", None)
    native_table = next(
        (item for item in getattr(base_world, "cuboid", []) if item.name == "table"),
        None,
    )
    if native_table is None or not isinstance(native_table.pose, (list, tuple)) or len(native_table.pose) != 7:
        raise CuroboWorldPortError("native planner table orientation is unavailable")
    native_orientation = native_table.pose[3:]
    projected = _world_pose_for_planner(planner, world_pose)
    import transforms3d.quaternions as tquat

    base_rotation = tquat.quat2mat(list(planner.robot_origion_pose.q))
    scene_half_extents = [float(item) for item in half_extents]
    planner_half_extents = [
        sum(abs(float(base_rotation[column][row])) * scene_half_extents[column] for column in range(3))
        for row in range(3)
    ]
    return {
        "pose": [*projected[:3], *map(float, native_orientation)],
        "dims": [2.0 * value for value in planner_half_extents],
    }


def _peer_pose_for_planner(planner: Any, peer: Mapping[str, Any]) -> list[float]:
    pose = peer["pose_wxyz"]
    return _world_pose_for_planner(
        planner,
        {
            "position_m": pose[:3],
            "orientation_xyzw": [pose[4], pose[5], pose[6], pose[3]],
        },
    )


def _world_config(
    planner: Any,
    artifact: Mapping[str, Any],
    peer_projection: Mapping[str, Any] | None = None,
) -> Any:
    from curobo.geom.types import Cuboid, WorldConfig

    base_world = getattr(planner, "_paos_collision_base_world", None)
    if base_world is None:
        base_world = planner.motion_gen.world_model.clone()
        planner._paos_collision_base_world = base_world.clone()
    cuboids = list(base_world.cuboid)
    names = {item.name for item in cuboids}
    native_table_geometry = _native_table_geometry_for_planner(planner)
    if native_table_geometry is not None:
        for index, item in enumerate(cuboids):
            if item.name == "table":
                cuboids[index] = Cuboid(
                    name=item.name,
                    dims=native_table_geometry["dims"],
                    pose=native_table_geometry["pose"],
                )
                break
    for obstacle in artifact["obstacles"]:
        name = str(obstacle["entity_ref"]).removeprefix("entity://")
        if name in names:
            raise CuroboWorldPortError(f"collision obstacle duplicates planner object: {name}")
        cuboids.append(
            Cuboid(
                name=name,
                dims=[2.0 * float(value) for value in obstacle["half_extents_m"]],
                pose=_world_pose_for_planner(planner, obstacle["world_T_entity"]),
            )
        )
    if peer_projection is not None:
        try:
            if peer_projection.get("schema_version") == PEER_ARM_SPHERE_PROJECTION_SCHEMA_VERSION:
                validated_peer = validate_peer_arm_sphere_projection(peer_projection)
            else:
                validated_peer = validate_peer_arm_projection(peer_projection)
        except ValueError as exc:
            raise CuroboWorldPortError("peer arm projection is invalid") from exc
        if validated_peer["scene_revision"] != artifact["scene_revision"]:
            raise CuroboWorldPortError("peer arm projection scene revision is stale")
        peer_arm = validated_peer["selected_arm"]
        planner_arm = getattr(planner, "arm_id", None)
        if planner_arm in {"left", "right"} and planner_arm != peer_arm:
            raise CuroboWorldPortError("peer arm projection is bound to the wrong planner")
        names = {item.name for item in cuboids}
        for peer in validated_peer["obstacles"]:
            name = f"peer-{peer['link_id'].replace(':', '-') }"
            if name in names:
                raise CuroboWorldPortError(f"peer arm obstacle duplicates planner object: {name}")
            if peer["shape"] == "sphere":
                # This vendored Curobo exposes WorldConfig.sphere but its
                # WorldPrimitiveCollision loader only installs cuboids.  Use
                # the enclosing cube so every native robot sphere really
                # participates in collision checking; the conversion is
                # conservative and remains explicit in the projection shape.
                radius = float(peer["radius_m"])
                dimensions = [2.0 * radius] * 3
            else:
                dimensions = [2.0 * float(value) for value in peer["half_extents_m"]]
            cuboids.append(Cuboid(name=name, dims=dimensions, pose=_peer_pose_for_planner(planner, peer)))
    return WorldConfig(cuboid=cuboids)


def add_released_object(planner: Any, pose: Mapping[str, Any], half_extents: Sequence[float]) -> list[tuple[Any, Any]]:
    """Make the detached object an obstacle for retreat; return worlds to restore."""
    from curobo.geom.types import Cuboid

    previous = []
    try:
        for model in (planner.motion_gen, planner.motion_gen_batch):
            world = model.world_model.clone()
            if len(world.cuboid) + 1 > _obb_capacity(model):
                raise CuroboWorldPortError("collision cache has no slot for released object")
            previous.append((model, model.world_model.clone()))
            world.cuboid.append(Cuboid(name="released_target", dims=[2 * float(v) for v in half_extents], pose=_world_pose_for_planner(planner, pose)))
            model.update_world(world)
    except Exception:
        for model, world in reversed(previous):
            model.update_world(world)
        raise
    return previous


def apply_collision_world(
    planners: Mapping[str, Any] | Sequence[Any], artifact: Mapping[str, Any],
    *, peer_projections: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Apply one artifact to both arm planners and their batch planners.

    The function performs no scene stepping and returns a provider receipt.  A
    partial update is reported as an error instead of being treated as ready.
    """

    if isinstance(planners, Mapping):
        selected = [planners.get("left"), planners.get("right")]
    else:
        selected = list(planners)
    if len(selected) != 2 or any(item is None for item in selected):
        raise CuroboWorldPortError("both arm planners are required")
    if peer_projections is not None:
        state_revisions = {
            projection.get("state_revision")
            for projection in peer_projections.values()
            if isinstance(projection, Mapping)
        }
        if len(peer_projections) != 2 or len(state_revisions) != 1 or None in state_revisions:
            raise CuroboWorldPortError("peer projection state coverage is inconsistent")
    try:
        world_artifact = validate_collision_world(artifact)
    except ValueError as exc:
        raise CuroboWorldPortError("collision world artifact is invalid") from exc
    prepared = []
    for planner in selected:
        planner_arm = getattr(planner, "arm_id", None)
        peer_projection = None
        if peer_projections is not None:
            if planner_arm not in {"left", "right"}:
                raise CuroboWorldPortError("planner arm identity is required for peer projection")
            peer_projection = peer_projections.get(planner_arm)
            if peer_projection is None:
                raise CuroboWorldPortError("peer projection coverage is incomplete")
        motion_gen = getattr(planner, "motion_gen", None)
        batch = getattr(planner, "motion_gen_batch", None)
        if motion_gen is None or batch is None or not callable(getattr(motion_gen, "update_world", None)) or not callable(getattr(batch, "update_world", None)):
            raise CuroboWorldPortError("planner does not expose motion_gen and motion_gen_batch update_world")
        world = _world_config(planner, world_artifact, peer_projection)
        required_capacity = len(world.cuboid)
        prepared.append(
            (
                planner,
                motion_gen,
                batch,
                world,
                required_capacity,
                motion_gen.world_model.clone(),
                batch.world_model.clone(),
            )
        )
    rebuild_required = any(
        min(_obb_capacity(motion_gen), _obb_capacity(batch)) < required_capacity
        for _, motion_gen, batch, _, required_capacity, _, _ in prepared
    )
    receipts = []
    applied = []
    original_refs = [(planner, motion_gen, batch) for planner, motion_gen, batch, *_ in prepared]
    try:
        if rebuild_required:
            replacements = []
            for planner, motion_gen, batch, world, required_capacity, _, _ in prepared:
                cache_capacity = max(required_capacity, int(world_artifact["cache_capacity"]))
                rebuilt, rebuilt_batch = _rebuild_motion_generators(
                    planner, world, cache_capacity
                )
                replacements.append((planner, rebuilt, rebuilt_batch))
            for planner, rebuilt, rebuilt_batch in replacements:
                planner.motion_gen = rebuilt
                planner.motion_gen_batch = rebuilt_batch
        else:
            for planner, motion_gen, batch, world, _, old_world, old_batch_world in prepared:
                motion_gen.update_world(world)
                applied.append((motion_gen, old_world))
                batch.update_world(world)
                applied.append((batch, old_batch_world))
        for planner, *_ in prepared:
            receipts.append({
                "planner": id(planner),
                "world_revision": world_artifact["world_revision"],
                "world_digest": world_artifact["world_digest"],
                "operation": "rebuild_motion_gen" if rebuild_required else "update_world",
            })
    except Exception as exc:
        for motion_gen, previous_world in reversed(applied):
            try:
                motion_gen.update_world(previous_world)
            except Exception:
                pass
        if rebuild_required:
            for planner, motion_gen, batch in original_refs:
                planner.motion_gen = motion_gen
                planner.motion_gen_batch = batch
        raise CuroboWorldPortError("collision world update failed and was rolled back") from exc
    return {
        "schema_version": "paos-robotwin20-curobo-world-update/v1",
        "scene_revision": world_artifact["scene_revision"],
        "world_revision": world_artifact["world_revision"],
        "world_digest": world_artifact["world_digest"],
        "arm_receipts": receipts,
        "motion_authorized": False,
    }


__all__ = ["CuroboWorldPortError", "apply_collision_world"]
