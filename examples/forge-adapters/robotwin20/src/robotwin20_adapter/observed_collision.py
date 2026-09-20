"""Observed occupancy and convex contact geometry; no simulator or motion IO."""

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class ObservedCollisionPolicy:
    depth_scale_to_m: float = .001
    voxel_size_m: float = .01
    uncertainty_m: float = .001
    minimum_inner_points: int = 3
    support_refinement_band_m: float = 0.0

    def __post_init__(self):
        if any(not np.isfinite(v) or v <= 0 for v in
               (self.depth_scale_to_m, self.voxel_size_m, self.uncertainty_m)):
            raise ValueError("observed collision metric settings must be positive and finite")
        if not isinstance(self.minimum_inner_points, int) or self.minimum_inner_points < 1:
            raise ValueError("minimum inner points must be a positive integer")
        if not np.isfinite(self.support_refinement_band_m) or self.support_refinement_band_m < 0:
            raise ValueError("support refinement band must be finite and nonnegative")

    def to_dict(self):
        return asdict(self)


def depth_points(depth, intrinsic, world_t_camera, scale):
    depth = np.asarray(depth, dtype=float)
    intrinsic = np.asarray(intrinsic, dtype=float)
    if depth.ndim != 2 or intrinsic.shape != (3, 3) or not np.isfinite(intrinsic).all() or min(intrinsic[0, 0], intrinsic[1, 1]) <= 0:
        raise ValueError("observed depth or intrinsics are invalid")
    ys, xs = np.nonzero(np.isfinite(depth) & (depth > 0))
    if len(xs) == 0:
        raise ValueError("observed depth contains no valid points")
    z = depth[ys, xs] * scale
    camera = np.stack(((xs - intrinsic[0, 2]) * z / intrinsic[0, 0],
                       (ys - intrinsic[1, 2]) * z / intrinsic[1, 1], z), axis=1)
    transform = np.asarray(world_t_camera).reshape(4, 4)
    return camera @ transform[:3, :3].T + transform[:3, 3], ys, xs


def voxel_boxes(points, size, padding, *, support_z=None, refinement_band=0.):
    """Use sensor-uncertainty-scale vertical cells near observed support.

    Coarse XY coverage and uncertainty padding remain unchanged. Refinement
    uses every return in the band, not a table label or fitted-plane replacement.
    """
    points = np.asarray(points, dtype=float).reshape(-1, 3)
    if support_z is None or refinement_band <= 0:
        return _grid_boxes(points, size, padding)
    near = np.abs(points[:, 2] - support_z) <= refinement_band
    coarse, coarse_count = _grid_boxes(points[~near], size, padding)
    fine, fine_count = _grid_boxes(points[near], np.array([size, size, min(size, padding)]), padding)
    return coarse + fine, coarse_count + fine_count


def _grid_boxes(points, size, padding):
    """Merge consecutive X cells only; never bridge an unoccupied voxel."""
    cells = np.unique(np.floor(points / size).astype(np.int64), axis=0)
    groups = {}
    for x, y, z in cells:
        groups.setdefault((int(y), int(z)), []).append(int(x))
    boxes = []
    for (y, z), xs in sorted(groups.items()):
        start = end = xs[0]
        for x in [*xs[1:], None]:
            if x is not None and x == end + 1:
                end = x
                continue
            low = np.array([start, y, z]) * size - padding
            high = np.array([end + 1, y + 1, z + 1]) * size + padding
            boxes.append({"position_m": ((low + high) / 2).tolist(),
                          "half_extents_m": ((high - low) / 2).tolist()})
            start = end = x
    return boxes, len(cells)


def inside_convex(points, vertices, padding=0.):
    """Exact convex shape halfspaces with a metric outward uncertainty offset."""
    from scipy.spatial import ConvexHull

    points = np.asarray(points, dtype=float).reshape(-1, 3)
    vertices = np.asarray(vertices, dtype=float)
    low, high = vertices.min(0) - padding, vertices.max(0) + padding
    broad = np.all((points >= low) & (points <= high), axis=1)
    selected = np.flatnonzero(broad)
    if len(selected):
        planes = ConvexHull(vertices).equations
        for indices in np.array_split(selected, max(1, int(np.ceil(len(selected) / 4096)))):
            broad[indices] = np.all(points[indices] @ planes[:, :3].T + planes[:, 3] <= padding + 1e-10, axis=1)
    return broad


def local_contact(target, environment, shapes, *, approach_delta, policy):
    """Reject occupied finger/palm solids and their straight approach sweeps.

    `shapes` contains separate convex collision components in hand coordinates.
    Only the empty space between the open fingers is a contact region; it does
    not exempt any target point inside a finger or palm collision solid.
    """
    failures, counts = [], {}
    for name, components in shapes.items():
        for index, vertices in enumerate(components):
            vertices = np.asarray(vertices)
            swept = np.vstack((vertices, vertices + approach_delta))
            for label, points in (("target", target), ("environment", environment)):
                hits = int(inside_convex(points, swept, policy.uncertainty_m).sum())
                counts[f"{label}:{name}:{index}"] = hits
                if hits:
                    failures.append(f"{label}_{name}_approach_collision")
    finger_bounds = []
    for name in ("panda_leftfinger", "panda_rightfinger"):
        vertices = np.concatenate(shapes[name])
        finger_bounds.append((vertices.min(0), vertices.max(0)))
    finger_bounds.sort(key=lambda b: b[0][1])
    low = np.maximum(finger_bounds[0][0], finger_bounds[1][0])
    high = np.minimum(finger_bounds[0][1], finger_bounds[1][1])
    low[1], high[1] = finger_bounds[0][1][1], finger_bounds[1][0][1]
    inner = np.all((target >= low) & (target <= high), axis=1)
    count = int(inner.sum())
    if count < policy.minimum_inner_points:
        failures.append("insufficient_observed_inner_contact")
    return {"status": "valid" if not failures else "rejected", "rejection_reasons": sorted(set(failures)),
            "inner_target_points": count, "collision_point_counts": counts,
            "visibility_scope": "observed_only", "hidden_surface_geometry": "unknown"}


def visibility_counts(world_points, depth, intrinsic, world_t_camera, scale, uncertainty):
    """Classify samples by depth rays; no unknown sample is labeled known free."""
    transform = np.asarray(world_t_camera).reshape(4, 4)
    camera = (np.asarray(world_points) - transform[:3, 3]) @ transform[:3, :3]
    k = np.asarray(intrinsic)
    valid = camera[:, 2] > 0
    u = np.zeros(len(camera), dtype=int)
    v = u.copy()
    u[valid] = np.rint(camera[valid, 0] * k[0, 0] / camera[valid, 2] + k[0, 2]).astype(int)
    v[valid] = np.rint(camera[valid, 1] * k[1, 1] / camera[valid, 2] + k[1, 2]).astype(int)
    valid &= (u >= 0) & (u < depth.shape[1]) & (v >= 0) & (v < depth.shape[0])
    measured = np.full(len(camera), np.nan)
    measured[valid] = depth[v[valid], u[valid]] * scale
    valid &= np.isfinite(measured) & (measured > 0)
    difference = camera[:, 2] - measured
    return {"observed_free_samples": int((valid & (difference < -uncertainty)).sum()),
            "surface_band_samples": int((valid & (np.abs(difference) <= uncertainty)).sum()),
            "occluded_samples": int((valid & (difference > uncertainty)).sum()),
            "unobserved_samples": int((~valid).sum())}
