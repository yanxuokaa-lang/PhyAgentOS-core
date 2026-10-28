"""Simulator-authored scene truth projected through the normal perception ports."""

from __future__ import annotations

import json
from copy import deepcopy

import numpy as np

from .visual_geometry import world_from_camera


class SimulatorTruthManifestError(ValueError):
    """The authored LabUtopia truth manifest is incomplete or inconsistent."""


def load_truth_manifest(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("objects"), list):
        raise SimulatorTruthManifestError("simulator truth manifest requires an objects list")
    objects = {}
    for item in payload["objects"]:
        if not isinstance(item, dict):
            raise SimulatorTruthManifestError("simulator truth objects must be mappings")
        for key in ("label", "category", "prim_path", "origin_world", "tip_world", "axis_world", "size_m"):
            if key not in item:
                raise SimulatorTruthManifestError(f"simulator truth object is missing {key}")
        label = str(item["label"]).strip()
        if not label or label in objects:
            raise SimulatorTruthManifestError(f"simulator truth label is missing or duplicated: {label!r}")
        objects[label] = deepcopy(item)
    return {"schema": payload.get("schema", "labutopia-simulator-truth/v1"), "objects": objects}


def _finite_vector(value, size, field):
    result = np.asarray(value, dtype=float)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise SimulatorTruthManifestError(f"{field} must be a finite vector of length {size}")
    return result


def object_point_cloud(calibration, object_spec, point_cloud):
    """Select the local portion of the captured camera cloud near authored pose."""
    points = np.asarray(point_cloud, dtype=float)
    if points.ndim == 3 and points.shape[-1] == 3:
        image_points = points
        flat = points.reshape(-1, 3)
    elif points.ndim == 2 and points.shape[1] == 3:
        image_points = None
        flat = points
    else:
        raise ValueError("simulator point cloud must have shape HxWx3 or Nx3")
    flat = flat[np.isfinite(flat).all(axis=1)]
    if len(flat) < 3:
        raise ValueError("simulator point cloud has insufficient finite points")
    transform = world_from_camera(calibration)
    world = _finite_vector(object_spec["origin_world"], 3, "origin_world")
    camera = np.linalg.inv(transform)[:3, :3] @ world + np.linalg.inv(transform)[:3, 3]
    if camera[2] <= 0:
        raise ValueError(f"simulator truth object {object_spec['label']} is behind the camera")
    intrinsics = np.asarray(calibration["intrinsics"], dtype=float)
    pixel = intrinsics @ (camera / camera[2])
    if image_points is not None:
        height, width = image_points.shape[:2]
        radius = int(object_spec.get("pixel_radius", 24))
        x, y = np.rint(pixel[:2]).astype(int)
        y0, y1 = max(0, y - radius), min(height, y + radius + 1)
        x0, x1 = max(0, x - radius), min(width, x + radius + 1)
        local = image_points[y0:y1, x0:x1].reshape(-1, 3)
        local = local[np.isfinite(local).all(axis=1)]
        if len(local) >= 3:
            return local
    distances = np.linalg.norm(flat - camera, axis=1)
    return flat[np.argsort(distances)[: min(256, len(flat))]]
