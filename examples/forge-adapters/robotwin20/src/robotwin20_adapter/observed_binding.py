"""Calibrated observation correspondence, independent of placement goals."""

from copy import deepcopy
from itertools import product

import numpy as np


def rigid_transform(value):
    matrix = np.asarray(value, dtype=float)
    if matrix.shape == (3, 4):
        matrix = np.vstack((matrix, [0, 0, 0, 1]))
    matrix = matrix.reshape(4, 4)
    if (not np.isfinite(matrix).all() or not np.allclose(matrix[3], [0, 0, 0, 1])
            or not np.allclose(matrix[:3, :3].T @ matrix[:3, :3], np.eye(3), atol=1e-5)
            or not np.isclose(np.linalg.det(matrix[:3, :3]), 1, atol=1e-5)):
        raise ValueError("invalid rigid transform")
    return matrix


def correspond(entity_refs, understanding, objects, camera_to_world):
    """Require a unique geometric match, never a category or ID-name match."""
    result = {}
    for ref in entity_refs:
        matches = [e for e in understanding["spatial_envelopes"] if e["entity_ref"] == ref]
        if len(matches) != 1:
            raise ValueError("missing or ambiguous observed envelope")
        envelope = matches[0]
        if envelope["unit"] != "m" or envelope["frame_id"] != understanding["frame"]["frame_id"]:
            raise ValueError("envelope frame or unit mismatch")
        low, high = np.asarray(envelope["min_xyz_m"]), np.asarray(envelope["max_xyz_m"])
        if low.shape != (3,) or high.shape != (3,) or not np.isfinite([low, high]).all() or np.any(low >= high):
            raise ValueError("invalid observed envelope")
        world = np.array([(*point, 1) for point in product(*zip(low, high))]) @ camera_to_world.T
        candidates = []
        for obj in objects:
            local = world @ np.linalg.inv(rigid_transform(obj["world_T_object"])).T
            half = np.asarray(obj["half_extents_m"], dtype=float)
            if half.shape != (3,) or not np.isfinite(half).all() or np.any(half <= 0):
                raise ValueError("invalid execution object extents")
            if np.all(local[:, :3].min(0) <= half) and np.all(local[:, :3].max(0) >= -half):
                candidates.append((obj, bool(np.all(np.abs(local[:, :3].mean(0)) <= half))))
        if len(candidates) != 1 or not candidates[0][1]:
            raise ValueError("execution correspondence is missing or ambiguous")
        result[ref] = deepcopy(candidates[0][0])
    if len({obj["entity_ref"] for obj in result.values()}) != len(result):
        raise ValueError("multiple observations identify one execution object")
    return result
