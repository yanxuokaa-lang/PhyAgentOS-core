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


# Ring width for collider radial-profile telemetry; fine enough to resolve the
# R05 shoulder taper (~0.36 mm radius recession per mm of height) over the
# +-30 mm finger pad window.
RADIAL_PROFILE_BIN_M = 0.002


def radial_profile(points, origin, axis, bin_size_m=RADIAL_PROFILE_BIN_M):
    """Ring-aggregate the radial distance r(z) of points along a span axis.

    Read-only collider telemetry: points are projected onto ``axis`` relative
    to ``origin``, grouped into ``bin_size_m`` rings ordered from lowest to
    highest span coordinate, and each ring records the median radius and point
    count. The axis need not pass through ``origin``'s neighbours; the radius
    is measured from the axis line itself, so a bottle collider produces its
    true r(z) taper profile.
    """
    points = _points(points)
    origin = np.asarray(origin, dtype=float)
    if origin.shape != (3,) or not np.isfinite(origin).all():
        raise ValueError("radial profile origin must be a finite 3-vector")
    axis = np.asarray(axis, dtype=float)
    if axis.shape != (3,) or not np.isfinite(axis).all():
        raise ValueError("radial profile axis must be a finite 3-vector")
    norm = float(np.linalg.norm(axis))
    if not math.isfinite(bin_size_m) or bin_size_m <= 0:
        raise ValueError("radial profile bin extent must be finite and positive")
    if norm <= 1e-9:
        raise ValueError("radial profile axis is unresolved")
    axis = axis / norm
    offsets = points - origin
    span = offsets @ axis
    radial = offsets - np.outer(span, axis)
    radius = np.linalg.norm(radial, axis=1)
    rings = []
    lowest = float(span.min())
    indices = np.floor((span - lowest) / bin_size_m).astype(int)
    for index in np.unique(indices):
        inside = indices == index
        rings.append({
            "span_center_m": lowest + (float(index) + 0.5) * bin_size_m,
            "median_radius_m": float(np.median(radius[inside])),
            "point_count": int(np.count_nonzero(inside)),
        })
    return rings


def points_within_radius(points, origin, axis, max_radius_m):
    """Keep only points within ``max_radius_m`` of the axis line through ``origin``.

    Same axis-line geometry as :func:`radial_profile`; returns the kept points
    (input order preserved) together with the excluded count, so callers can
    drop foreign cooked-compound geometry before ring aggregation while
    reporting the exclusion honestly.
    """
    points = _points(points)
    origin = np.asarray(origin, dtype=float)
    if origin.shape != (3,) or not np.isfinite(origin).all():
        raise ValueError("radius filter origin must be a finite 3-vector")
    axis = np.asarray(axis, dtype=float)
    if axis.shape != (3,) or not np.isfinite(axis).all():
        raise ValueError("radius filter axis must be a finite 3-vector")
    norm = float(np.linalg.norm(axis))
    if not math.isfinite(max_radius_m) or max_radius_m <= 0:
        raise ValueError("radius filter bound must be finite and positive")
    if norm <= 1e-9:
        raise ValueError("radius filter axis is unresolved")
    axis = axis / norm
    offsets = points - origin
    span = offsets @ axis
    radius = np.linalg.norm(offsets - np.outer(span, axis), axis=1)
    kept = points[radius <= max_radius_m]
    return kept, int(len(points) - len(kept))


def grasp_span_axis(grasp_rotation, provider_from_tcp=None):
    """World direction of the provider span axis for a TCP-convention grasp.

    ``grasp_rotation`` is the world orientation of the commanded grasp frame,
    which follows the TCP convention. ``provider_from_tcp`` is the deployed
    provider calibration mapping TCP coordinates into provider coordinates --
    the same matrix visual_perception validates -- and the provider span axis
    is provider z, so the world direction is the grasp rotation applied to
    ``provider_from_tcp[:3, :3].T @ (0, 0, 1)``. A missing calibration, or one
    that is not a rigid 4x4 transform, falls back to the identity mapping,
    which reproduces the historical grasp-rotation z column; the returned
    source records which mapping produced the axis so telemetry can show it.
    """
    grasp_rotation = np.asarray(grasp_rotation, dtype=float)
    if grasp_rotation.shape != (3, 3) or not np.isfinite(grasp_rotation).all():
        raise ValueError("grasp span axis requires a finite 3x3 grasp rotation")
    try:
        matrix = None if provider_from_tcp is None else np.asarray(provider_from_tcp, dtype=float)
    except (TypeError, ValueError):
        matrix = None
    if matrix is not None and (matrix.shape != (4, 4) or not np.isfinite(matrix).all()
                               or not np.allclose(matrix[3], [0, 0, 0, 1])
                               or not np.allclose(matrix[:3, :3].T @ matrix[:3, :3], np.eye(3))
                               or np.linalg.det(matrix[:3, :3]) < 0):
        matrix = None
    if matrix is None:
        return grasp_rotation[:, 2], "identity_fallback"
    return grasp_rotation @ (matrix[:3, :3].T @ np.array([0., 0., 1.])), "provider_from_tcp"


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
