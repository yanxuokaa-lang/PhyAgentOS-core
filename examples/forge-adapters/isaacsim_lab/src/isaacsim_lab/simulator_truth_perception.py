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
        for key in ("label", "category", "prim_path"):
            if key not in item:
                raise SimulatorTruthManifestError(f"simulator truth object is missing {key}")
        label = str(item["label"]).strip()
        if not label or label in objects:
            raise SimulatorTruthManifestError(f"simulator truth label is missing or duplicated: {label!r}")
        # Legacy authored functional coordinates are intentionally discarded.
        objects[label] = {key: deepcopy(item[key]) for key in ("label", "category", "prim_path")}
    return {"schema": payload.get("schema", "labutopia-simulator-truth/v1"), "objects": objects}


def process_feature_candidates(points, boundary_edges, category, *, tolerance_m=.004):
    """Estimate operation affordance candidates from final composed mesh evidence."""
    values = np.asarray(points, dtype=float)
    if values.ndim != 2 or values.shape[1] != 3 or len(values) < 20 or not np.isfinite(values).all():
        raise ValueError("process feature candidates require finite mesh points")
    low, high = values.min(0), values.max(0)
    size = high - low
    if category in {"reagent_bottle", "mixing_vessel"}:
        edges = np.asarray(boundary_edges, dtype=float)
        if edges.ndim != 3 or edges.shape[1:] != (2, 3) or not np.isfinite(edges).all():
            raise ValueError("opening features require final mesh boundary edges")
        vertices = {}
        graph = {}
        vertex_resolution_m = min(tolerance_m * .01, 1e-5)
        for edge in edges:
            if np.linalg.norm(edge[1] - edge[0]) <= tolerance_m * .01:
                continue
            keys = [tuple(np.rint(point / vertex_resolution_m).astype(int)) for point in edge]
            for key, point in zip(keys, edge):
                vertices.setdefault(key, point)
                graph.setdefault(key, [])
            graph[keys[0]].append(keys[1])
            graph[keys[1]].append(keys[0])
        if not graph:
            raise ValueError("opening boundary topology is open or non-manifold")
        loops, invalid_topology, unseen = [], False, set(graph)
        while unseen:
            start = next(iter(unseen))
            loop, stack = set(), [start]
            while stack:
                key = stack.pop()
                if key in loop:
                    continue
                loop.add(key)
                unseen.discard(key)
                stack.extend(set(graph[key]) - loop)
            if any(len(graph[key]) != 2 for key in loop):
                invalid_topology = True
                continue
            if len(loop) >= 8:
                loops.append(np.asarray([vertices[key] for key in loop]))
        if not loops:
            if invalid_topology:
                raise ValueError("opening boundary topology is open or non-manifold")
            raise ValueError("final mesh has no closed opening boundary")
        top = max(float(loop[:, 2].mean()) for loop in loops)
        top_loops = [loop for loop in loops if top - float(loop[:, 2].mean()) <= max(tolerance_m * 2, size[2] * .02)]
        fits = []
        for loop in top_loops:
            centre = loop.mean(0)
            centred_loop = loop - centre
            _, singular, basis = np.linalg.svd(centred_loop, full_matrices=False)
            if singular[1] <= tolerance_m:
                continue
            planar = centred_loop @ basis[:2].T
            radius = np.linalg.norm(planar, axis=1)
            median_radius = float(np.median(radius))
            spread = float(np.std(radius))
            if median_radius > tolerance_m and spread <= max(tolerance_m, median_radius * .12):
                axis = basis[2]
                if axis[2] < 0:
                    axis = -axis
                fits.append((median_radius, centre, spread, axis))
        if not fits:
            raise ValueError("top opening boundary is not a stable circular rim")
        fits.sort(key=lambda item: item[0])
        candidates = []
        for index, (radius, centre, spread, axis) in enumerate(fits):
            feature = {"origin_world": ((low + high) / 2).tolist(), "tip_world": centre.tolist(),
                       "axis_world": axis.tolist(), "size_m": size.tolist(),
                       "feature_kind": "rim", "feature_role": "opening", "rim_radius_m": radius,
                       "fit_rmse_m": spread, "candidate_index": index,
                       "source": "final_composed_usd_mesh", "coverage": "closed_boundary_loop"}
            if category == "reagent_bottle":
                feature.update(_pour_lip_evidence(
                    radius, centre, axis, tolerance_m, boundary_edges=edges,
                ))
            candidates.append(feature)
        return candidates
    if category == "stir_tool":
        centred = values - values.mean(0)
        _, _, basis = np.linalg.svd(centred, full_matrices=False)
        axis = basis[0] / np.linalg.norm(basis[0])
        projection = centred @ axis
        length = float(projection.max() - projection.min())
        if length <= tolerance_m:
            raise ValueError("rod axis is unresolved")
        radial = centred - np.outer(projection, axis)
        if float(np.sqrt(np.mean(np.sum(radial * radial, axis=1)))) > max(tolerance_m, length * .08):
            raise ValueError("final mesh does not support a straight rod axis")
        margin = max(tolerance_m, length * .01)
        endpoints = [values[projection <= projection.min() + margin].mean(0),
                     values[projection >= projection.max() - margin].mean(0)]
        return [{"origin_world": endpoints[0].tolist(), "tip_world": endpoints[1].tolist(),
                 "axis_world": axis.tolist(), "size_m": size.tolist(),
                 "feature_kind": "rod_endpoint_pair", "feature_role": "endpoint_a",
                 "source": "final_composed_usd_mesh", "coverage": "mesh_vertices"},
                {"origin_world": endpoints[1].tolist(), "tip_world": endpoints[0].tolist(),
                 "axis_world": (-axis).tolist(), "size_m": size.tolist(),
                 "feature_kind": "rod_endpoint_pair", "feature_role": "endpoint_b",
                 "source": "final_composed_usd_mesh", "coverage": "mesh_vertices"}]
    raise ValueError(f"unsupported process feature category: {category}")


def process_feature_candidates_by_component(points, boundary_components, category, *, tolerance_m=.004):
    """Derive vessel candidates without merging coincident USD mesh topology."""
    values = np.asarray(points, dtype=float)
    components = list(boundary_components or ())
    failures = []
    if category in {"reagent_bottle", "mixing_vessel"}:
        try:
            feature = _top_mesh_vertex_rim(values, tolerance_m=tolerance_m)
            if category == "reagent_bottle" and components:
                boundary_points = np.concatenate(
                    [np.asarray(component, dtype=float).reshape(-1, 3) for component in components],
                    axis=0,
                )
                feature.update(_pour_lip_evidence(
                    feature["rim_radius_m"], np.asarray(feature["tip_world"]),
                    np.asarray(feature["axis_world"]), tolerance_m,
                    boundary_edges=boundary_points,
                ))
            return [feature]
        except ValueError as exc:
            failures.append(str(exc))
    candidates = []
    for component_index, edges in enumerate(components):
        try:
            features = process_feature_candidates(points, edges, category, tolerance_m=tolerance_m)
        except (TypeError, ValueError) as exc:
            failures.append(str(exc))
            continue
        for feature in features:
            candidates.append({**feature, "mesh_component_index": component_index})
    if candidates:
        highest = max(float(item["tip_world"][2]) for item in candidates)
        return [item for item in candidates if highest - float(item["tip_world"][2]) <= tolerance_m * 2]
    if not components and category == "stir_tool":
        return process_feature_candidates(values, [], category, tolerance_m=tolerance_m)
    if failures:
        raise ValueError("; ".join(dict.fromkeys(failures)))
    raise ValueError("final mesh components have no opening boundary")


def _top_mesh_vertex_rim(points, *, tolerance_m):
    """Fit a fully covered top ring from final mesh vertices when topology is degenerate."""
    if (points.ndim != 2 or points.shape[1] != 3 or len(points) < 20
            or not np.isfinite(points).all()):
        raise ValueError("top mesh ring requires finite mesh vertices")
    low, high = points.min(0), points.max(0)
    height = float(high[2] - low[2])
    band = max(tolerance_m * .25, height * .005)
    ring = points[points[:, 2] >= high[2] - band]
    if len(ring) < 8:
        raise ValueError("top mesh ring has insufficient vertex support")
    xy = ring[:, :2]
    system = np.column_stack((2 * xy, np.ones(len(xy))))
    fitted, _, rank, _ = np.linalg.lstsq(system, np.sum(xy * xy, axis=1), rcond=None)
    radius_squared = fitted[2] + fitted[:2] @ fitted[:2]
    if rank != 3 or radius_squared <= tolerance_m * tolerance_m:
        raise ValueError("top mesh ring circle is unresolved")
    center_xy = fitted[:2]
    radius = float(np.sqrt(radius_squared))
    radial = np.linalg.norm(xy - center_xy, axis=1) - radius
    residual = float(np.sqrt(np.mean(radial * radial)))
    angles = np.sort(np.arctan2(xy[:, 1] - center_xy[1], xy[:, 0] - center_xy[0]))
    max_gap = float(np.max(np.diff(np.r_[angles, angles[0] + 2 * np.pi])))
    if residual > max(tolerance_m, radius * .12) or max_gap > np.pi / 2:
        raise ValueError("top mesh vertices do not support a fully covered circular rim")
    return {
        "origin_world": ((low + high) / 2).tolist(),
        "tip_world": [float(center_xy[0]), float(center_xy[1]), float(ring[:, 2].mean())],
        "axis_world": [0.0, 0.0, 1.0],
        "size_m": (high - low).tolist(),
        "feature_kind": "rim",
        "feature_role": "opening",
        "rim_radius_m": radius,
        "fit_rmse_m": residual,
        "source": "final_composed_usd_mesh",
        "coverage": "top_mesh_vertex_ring",
    }


def _pour_lip_evidence(rim_radius, rim_center, rim_axis, tolerance_m, *, boundary_edges=None):
    """Qualify a sideward pour lip from final-mesh support near a fitted rim.

    A circular opening alone is deliberately insufficient.  The mesh must contain
    a spatially coherent, lateral extension beyond the fitted rim in the rim
    plane.  The returned fields are provider evidence, not authored landmarks.
    """
    axis = np.asarray(rim_axis, dtype=float)
    axis /= np.linalg.norm(axis)
    if boundary_edges is None:
        return {}
    boundary = np.asarray(boundary_edges, dtype=float).reshape(-1, 3)
    if boundary.ndim != 2 or boundary.shape[1] != 3 or len(boundary) < 8 or not np.isfinite(boundary).all():
        return {}
    axial = (boundary - rim_center) @ axis
    band = boundary[np.abs(axial) <= max(tolerance_m * 3.0, rim_radius * 0.35)]
    if len(band) < 8:
        return {}
    planar = band - np.outer((band - rim_center) @ axis, axis)
    radial_vectors = planar - rim_center
    radial = np.linalg.norm(radial_vectors, axis=1)
    extension_threshold = max(tolerance_m * 2.0, rim_radius * 0.18)
    extension = radial > rim_radius + extension_threshold
    support = radial_vectors[extension]
    if len(support) < 6:
        return {}
    direction_sum = support.sum(axis=0)
    direction = direction_sum - axis * float(np.dot(direction_sum, axis))
    direction_norm = float(np.linalg.norm(direction))
    if direction_norm <= max(tolerance_m, rim_radius * 0.05):
        return {}
    direction /= direction_norm
    alignment = (support @ direction) / np.maximum(np.linalg.norm(support, axis=1), 1e-12)
    if float(np.mean(alignment)) < 0.82 or int(np.count_nonzero(alignment > 0.55)) < 6:
        return {}
    tip = rim_center + direction * float(np.median(support @ direction))
    return {
        "feature_role": "pour_lip",
        "tip_world": tip.tolist(),
        "pour_direction_world": direction.tolist(),
        "lip_extension_m": float(np.median(support @ direction)),
        "lip_support_count": int(len(support)),
        "coverage": "closed_boundary_loop+lateral_mesh_support",
    }


def _finite_vector(value, size, field):
    result = np.asarray(value, dtype=float)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise SimulatorTruthManifestError(f"{field} must be a finite vector of length {size}")
    return result


def object_point_cloud(calibration, point_cloud, world_bounds):
    """Select same-capture points inside final composed USD world bounds."""
    points = np.asarray(point_cloud, dtype=float)
    if points.ndim == 3 and points.shape[-1] == 3:
        flat = points.reshape(-1, 3)
    elif points.ndim == 2 and points.shape[1] == 3:
        flat = points
    else:
        raise ValueError("simulator point cloud must have shape HxWx3 or Nx3")
    flat = flat[np.isfinite(flat).all(axis=1)]
    if len(flat) < 3:
        raise ValueError("simulator point cloud has insufficient finite points")
    transform = world_from_camera(calibration)
    if not isinstance(world_bounds, dict):
        raise SimulatorTruthManifestError("final composed USD world bounds are required")
    minimum = _finite_vector(world_bounds.get("min_xyz_world_m"), 3, "min_xyz_world_m")
    maximum = _finite_vector(world_bounds.get("max_xyz_world_m"), 3, "max_xyz_world_m")
    if np.any(minimum >= maximum):
        raise SimulatorTruthManifestError("world bounds must have positive extent")
    rotation, translation = transform[:3, :3], transform[:3, 3]
    world_points = flat @ rotation.T + translation
    inside = np.all((world_points >= minimum) & (world_points <= maximum), axis=1)
    return flat[inside]


def world_bounds_in_frame(calibration, world_bounds):
    """Project all world-AABB corners into the calibrated observation frame."""
    minimum = _finite_vector(world_bounds.get("min_xyz_world_m"), 3, "min_xyz_world_m")
    maximum = _finite_vector(world_bounds.get("max_xyz_world_m"), 3, "max_xyz_world_m")
    if np.any(minimum >= maximum):
        raise SimulatorTruthManifestError("world bounds must have positive extent")
    corners = np.asarray([
        [x, y, z]
        for x in (minimum[0], maximum[0])
        for y in (minimum[1], maximum[1])
        for z in (minimum[2], maximum[2])
    ])
    world_from_cam = world_from_camera(calibration)
    frame_from_world = np.linalg.inv(world_from_cam)
    points = corners @ frame_from_world[:3, :3].T + frame_from_world[:3, 3]
    if not np.isfinite(points).all():
        raise SimulatorTruthManifestError("projected world bounds are not finite")
    return points.min(axis=0), points.max(axis=0)
