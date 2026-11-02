"""Adapter-private conservative bounds of PhysX cooked gripper solids.

Each slab contains the *solid* convex intersection, not just vertices within
the slab. Bounding all edge/plane intersections preserves its interior. Sweeping
these boxes over linear prismatic travel therefore covers every finger opening.
"""

import math
from itertools import combinations

import numpy as np
from scipy.spatial import ConvexHull, QhullError


def _points(value):
    points = np.array(value, dtype=float, copy=True)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 4 or not np.isfinite(points).all():
        raise ValueError("cooked gripper convex must contain finite 3D vertices")
    return points


def cooked_convex_points(request, stage_id, prim_id, valid_result):
    """Copy every cooked component while the synchronous callback owns its data."""
    results, errors = [], []

    def receive(result, convexes):
        # Native callback boundaries can swallow exceptions; report afterwards.
        try:
            if result != valid_result or not convexes:
                raise ValueError("PhysX did not return valid cooked gripper geometry")
            results.extend(_points(convex.vertices) for convex in convexes)
        except Exception as exc:
            errors.append(exc)

    request(stage_id=stage_id, collision_prim_id=prim_id,
            run_asynchronously=False, on_result=receive)
    if errors:
        raise ValueError(str(errors[0])) from errors[0]
    if not results:
        raise ValueError("PhysX cooking returned no synchronous gripper evidence")
    return results


def convex_slice_boxes(vertices, maximum_slice_m):
    """Cover a cooked convex with slabs along its longest body-frame dimension."""
    points = _points(vertices)
    if not math.isfinite(maximum_slice_m) or maximum_slice_m <= 0:
        raise ValueError("finger slice extent must be finite and positive")
    try:
        hull = ConvexHull(points)
    except QhullError as exc:
        raise ValueError("cooked gripper convex must enclose a 3D solid") from exc
    axis = int(np.argmax(np.ptp(points, axis=0)))
    lower, upper = points[:, axis].min(), points[:, axis].max()
    edges = sorted({tuple(sorted(pair)) for face in hull.simplices for pair in combinations(face, 2)})
    start, end = points[np.array(edges)[:, 0]], points[np.array(edges)[:, 1]]
    delta = end[:, axis] - start[:, axis]
    cuts = np.linspace(lower, upper, math.ceil((upper - lower) / maximum_slice_m) + 1)
    boxes = []
    for low, high in zip(cuts[:-1], cuts[1:], strict=True):
        pieces = [points[(points[:, axis] >= low) & (points[:, axis] <= high)]]
        for plane in (low, high):
            crossing = ((np.minimum(start[:, axis], end[:, axis]) <= plane)
                        & (np.maximum(start[:, axis], end[:, axis]) >= plane) & (delta != 0))
            t = (plane - start[crossing, axis]) / delta[crossing]
            pieces.append(start[crossing] + t[:, None] * (end[crossing] - start[crossing]))
        clipped = np.concatenate(pieces)
        # Outward numerical rounding is separate from the unchanged safety margin.
        boxes.append((clipped.min(0) - 1e-10, clipped.max(0) + 1e-10))
    return boxes


def cooked_body_boxes(stage, body, maximum_slice_m):
    """Read current composed rigid-body colliders; return private bounds/evidence."""
    from omni.physx import get_physx_cooking_interface
    from omni.physx.bindings._physx import PhysxCollisionRepresentationResult
    from pxr import PhysicsSchemaTools, Usd, UsdGeom, UsdPhysics, UsdUtils

    colliders = [prim for prim in Usd.PrimRange(body, Usd.TraverseInstanceProxies())
                 if prim.HasAPI(UsdPhysics.CollisionAPI)
                 and UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()]
    if not colliders:
        raise ValueError("rigid gripper body has no active collider")
    boxes, evidence = [], []
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
    for collider in colliders:
        if collider.IsA(UsdGeom.Mesh):
            parts = cooked_convex_points(
                get_physx_cooking_interface().request_convex_collision_representation,
                UsdUtils.StageCache.Get().GetId(stage).ToLongInt(),
                PhysicsSchemaTools.sdfPathToInt(collider.GetPath()),
                PhysxCollisionRepresentationResult.RESULT_VALID,
            )
            relative = np.asarray(
                UsdGeom.Xformable(collider).ComputeLocalToWorldTransform(0)
                * UsdGeom.Xformable(body).ComputeLocalToWorldTransform(0).GetInverse()
            ).T
            parts = [points @ relative[:3, :3].T + relative[:3, 3] for points in parts]
            component_boxes = [box for points in parts for box in convex_slice_boxes(points, maximum_slice_m)]
            evidence.append({"collider_path": str(collider.GetPath()),
                             "representation": "physx_cooked_convex_slices",
                             "body_frame_convexes_m": [points.tolist() for points in parts],
                             "slice_count": len(component_boxes)})
        else:
            box = bounds.ComputeRelativeBound(collider, body).ComputeAlignedBox()
            component_boxes = [(np.asarray(box.GetMin()), np.asarray(box.GetMax()))]
            evidence.append({"collider_path": str(collider.GetPath()),
                             "representation": "analytic_primitive_bound", "slice_count": 1})
        boxes.extend(component_boxes)
    return boxes, evidence
