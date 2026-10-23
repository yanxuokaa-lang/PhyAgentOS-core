"""Geometry estimated from segmented RGB-D; no simulator state or grasp rules."""
from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation


def world_from_camera(calibration):
    pose = calibration["camera_pose_world"]
    transform = np.eye(4)
    transform[:3, :3] = Rotation.from_quat(np.roll(pose["orientation_wxyz"], -1)).as_matrix()
    transform[:3, 3] = pose["position_m"]
    return transform


def pixel_to_world(pixel, depth, calibration):
    point = np.asarray(pixel, dtype=float)
    if point.shape != (2,) or not np.isfinite(point).all():
        raise ValueError("object pixel must have two finite coordinates")
    x, y = np.rint(point).astype(int)
    if not (0 <= y < depth.shape[0] and 0 <= x < depth.shape[1]):
        raise ValueError("object pixel is outside the image")
    z = float(depth[y, x])
    if not np.isfinite(z) or z <= 0:
        raise ValueError("object pixel has no measured depth")
    transform = world_from_camera(calibration)
    point = np.linalg.solve(np.asarray(calibration["intrinsics"]), [x, y, 1.]) * z
    return transform[:3, :3] @ point + transform[:3, 3], transform


def process_features(points, category, *, support=None, tolerance_m=.004):
    """Fit explicitly identified visible features, never cloud extrema.

    ``support`` contains world points projected from separately identified image
    landmarks. Fits are estimates; their residual is not a geometry confidence.
    A rod's ordered landmarks are the non-working end and the working end.
    """
    if not support:
        raise ValueError("process features require explicit image landmark support")
    if support.get("fully_visible") is not True:
        raise ValueError("required process landmarks are not fully visible")
    points = np.asarray(points, dtype=float)
    landmarks = np.asarray(support.get("points_world"), dtype=float)
    if (points.ndim != 2 or points.shape[1] != 3 or len(points) < 20
            or not np.isfinite(points).all() or landmarks.ndim != 2
            or landmarks.shape[1] != 3 or not np.isfinite(landmarks).all()):
        raise ValueError("process features require finite observed points and landmarks")
    low, high = points.min(0), points.max(0)
    residual = 0.
    if category == "stir_tool" and support.get("kind") == "rod_endpoints":
        if len(landmarks) != 2:
            raise ValueError("both physical rod endpoints must be observed")
        origin = landmarks.mean(0)
        axis = landmarks[1] - landmarks[0]
        length = np.linalg.norm(axis)
        if length <= tolerance_m:
            raise ValueError("observed rod endpoints are unresolved")
        axis /= length
        offsets = points - origin
        residual = float(np.sqrt(np.mean(np.linalg.norm(np.cross(offsets, axis), axis=1)**2)))
        if residual > tolerance_m:
            raise ValueError("observed rod surface disagrees with its endpoint axis")
        tip = landmarks[1]
    elif category in {"reagent_bottle", "mixing_vessel"} and support.get("kind") == "rim":
        if len(landmarks) < 8:
            raise ValueError("rim requires at least eight separately observed support points")
        center = landmarks.mean(0)
        _, singular, basis = np.linalg.svd(landmarks-center, full_matrices=False)
        if singular[1] <= tolerance_m:
            raise ValueError("observed rim coverage is unresolved")
        xy = (landmarks-center) @ basis[:2].T
        system = np.column_stack((2*xy, np.ones(len(xy))))
        fitted, _, rank, _ = np.linalg.lstsq(system, np.sum(xy*xy, axis=1), rcond=None)
        radius_squared = fitted[2] + fitted[:2] @ fitted[:2]
        if rank != 3 or radius_squared <= 0:
            raise ValueError("observed rim circle is unresolved")
        radial = np.linalg.norm(xy-fitted[:2], axis=1)-np.sqrt(radius_squared)
        planar = (landmarks-center) @ basis[2]
        residual = float(np.sqrt(np.mean(radial**2 + planar**2)))
        angles = np.sort(np.arctan2(*(xy-fitted[:2]).T[::-1]))
        if residual > tolerance_m or np.max(np.diff(np.r_[angles, angles[0]+2*np.pi])) > np.pi:
            raise ValueError("observed rim fit or angular coverage is insufficient")
        tip = center + fitted[:2] @ basis[:2]
        axis = basis[2]
        if axis[2] < 0:
            axis = -axis
        origin = (low+high)/2
    else:
        raise ValueError("unsupported process landmark kind or category")
    return {"origin_world": origin.tolist(), "tip_world": tip.tolist(), "axis_world": axis.tolist(),
            "size_m": (high-low).tolist(), "source": "image_landmarks_and_geometry_estimate",
            "fit_rmse_m": residual, "coverage": "observed_surface"}


def candidate_world_pose(candidate, transform, provider_from_tcp):
    """Apply calibrated frame conventions without replacing the predicted pose."""
    frame = candidate["grasp_frame"]
    pose = np.eye(4)
    pose[:3, :3] = Rotation.from_quat(frame["orientation_xyzw"]).as_matrix()
    pose[:3, 3] = frame["position_m"]
    approach = transform[:3, :3] @ np.asarray(candidate["approach_direction"]["vector"])
    result = transform @ pose @ provider_from_tcp
    if not np.allclose(result[:3, 2], approach, atol=1e-5):
        raise ValueError("grasp convention does not align the TCP approach with the predicted approach")
    return result, approach
