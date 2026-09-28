"""Horizontal support estimation from calibrated points, retaining all residuals.

The current route provider supports world-Z support only. Consensus outside that
model is unavailable, not silently flattened or replaced by simulator geometry.
"""

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class SupportEstimationPolicy:
    inlier_distance_m: float = .002
    minimum_inlier_fraction: float = .7
    minimum_points: int = 30
    residual_cell_m: float = .02
    uncertainty_m: float = .001
    maximum_slope: float = .02

    def __post_init__(self):
        for name in ("inlier_distance_m", "residual_cell_m", "uncertainty_m", "maximum_slope"):
            if not np.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"support {name} must be finite and positive")
        if not 0 < self.minimum_inlier_fraction <= 1 or self.minimum_points < 3:
            raise ValueError("support consensus policy is invalid")


def estimate_support(points, evidence_ref, policy=SupportEstimationPolicy()):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < policy.minimum_points or not np.isfinite(points).all():
        raise ValueError("observed support has insufficient finite metric points")
    height = float(np.median(points[:, 2]))
    inliers = np.abs(points[:, 2] - height) <= policy.inlier_distance_m
    if inliers.mean() < policy.minimum_inlier_fraction:
        raise ValueError("observed support has no dominant horizontal plane")
    surface = points[inliers]
    coefficients, _, rank, _ = np.linalg.lstsq(np.c_[surface[:, :2], np.ones(len(surface))], surface[:, 2], rcond=None)
    if rank < 3 or np.linalg.norm(coefficients[:2]) > policy.maximum_slope:
        raise ValueError("observed support tilt or spatial coverage is unsupported")
    low, high = points.min(axis=0), points.max(axis=0)
    high[2] = surface[:, 2].max() + policy.uncertainty_m
    low[2] = min(low[2], height - policy.uncertainty_m)
    if np.any(high <= low):
        raise ValueError("observed support extent is degenerate")
    residuals = points[~inliers]
    boxes = []
    if len(residuals):
        cells, indices = np.unique(np.floor(residuals[:, :2] / policy.residual_cell_m), axis=0, return_inverse=True)
        for index in range(len(cells)):
            group = residuals[indices == index]
            lo = group.min(axis=0) - policy.uncertainty_m
            hi = group.max(axis=0) + policy.uncertainty_m
            boxes.append({"position_m": ((lo + hi) / 2).tolist(), "half_extents_m": ((hi - lo) / 2).tolist()})
    return {"position_m": ((low + high) / 2).tolist(), "orientation_wxyz": [1., 0., 0., 0.],
            "half_extents_m": ((high - low) / 2).tolist(), "evidence_ref": evidence_ref,
            "residual_boxes": boxes, "estimation": {"method": "horizontal_consensus", "policy": asdict(policy),
            "height_m": height, "point_count": len(points), "inlier_count": int(inliers.sum()),
            "residual_count": len(residuals), "fitted_slope": coefficients[:2].tolist()}}


def estimate_support_from_depth(
    depth,
    intrinsic,
    world_t_camera,
    excluded_masks,
    evidence_ref,
    *,
    excluded_mask_refs=(),
    depth_scale_to_m=0.001,
    policy=SupportEstimationPolicy(),
):
    """Estimate support from current RGB-D returns outside observed objects."""
    depth = np.asarray(depth, dtype=float)
    intrinsic = np.asarray(intrinsic, dtype=float)
    transform = np.asarray(world_t_camera, dtype=float)
    if transform.size == 16:
        transform = transform.reshape(4, 4)
    elif transform.size == 12:
        transform = np.vstack((transform.reshape(3, 4), [0.0, 0.0, 0.0, 1.0]))
    if (
        depth.ndim != 2
        or intrinsic.shape != (3, 3)
        or transform.shape != (4, 4)
        or not np.isfinite(intrinsic).all()
        or not np.isfinite(transform).all()
        or intrinsic[0, 0] <= 0
        or intrinsic[1, 1] <= 0
        or not np.isfinite(depth_scale_to_m)
        or depth_scale_to_m <= 0
    ):
        raise ValueError("observed support depth calibration is invalid")
    if not isinstance(evidence_ref, str) or not evidence_ref:
        raise ValueError("observed support depth provenance is invalid")
    excluded = np.zeros(depth.shape, dtype=bool)
    masks = tuple(excluded_masks)
    if not masks:
        raise ValueError("observed support requires current instance masks")
    mask_refs = tuple(excluded_mask_refs)
    if len(mask_refs) != len(masks) or any(not isinstance(ref, str) or not ref for ref in mask_refs):
        raise ValueError("observed support mask provenance is invalid")
    for mask in masks:
        mask = np.asarray(mask)
        if mask.shape != depth.shape:
            raise ValueError("observed support instance mask differs from scene depth")
        mask = mask.astype(bool, copy=False)
        if not mask.any():
            raise ValueError("observed support instance mask is empty")
        excluded |= mask

    ys, xs = np.nonzero(np.isfinite(depth) & (depth > 0) & ~excluded)
    if len(xs) < policy.minimum_points:
        raise ValueError("observed support has insufficient unmasked depth points")
    z = depth[ys, xs] * depth_scale_to_m
    camera = np.stack(
        (
            (xs - intrinsic[0, 2]) * z / intrinsic[0, 0],
            (ys - intrinsic[1, 2]) * z / intrinsic[1, 1],
            z,
        ),
        axis=1,
    )
    world = camera @ transform[:3, :3].T + transform[:3, 3]
    support = estimate_support(world, evidence_ref, policy)
    support["source_refs"] = [evidence_ref, *mask_refs]
    return support
