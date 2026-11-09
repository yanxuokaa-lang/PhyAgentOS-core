"""Simulator-truth semantic grasp geometry for the explicit oracle execution mode.

This module is only used when the deployment explicitly selects
``grasp_source: "simulator_truth_oracle"`` in the perception profile. It
derives a small, category-aware set of grasp candidates directly from the
final-composed USD mesh truth already recorded by the simulator-truth
perception path, so the grasp point honours task semantics (bottle body band
below the rim, rod shaft leaving a working end free).

The output keeps the provider-neutral candidate shape used by the model grasp
providers. Every candidate still flows through the unchanged
task-affordance qualification gate and the no-motion approach probe; this
module never fabricates observations and never replaces qualification. All
lineage is marked ``simulator_ground_truth`` and is never presented as
sensor-derived geometry.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation

_GRIPPER_KEYS = ("gripper_width_m", "finger_height_m", "finger_depth_m")
_BOTTLE_DEPTH_FRACTIONS = (0.35, 0.50, 0.65)
_ROD_SHAFT_FRACTIONS = (0.30, 0.70)


def validate_depth_fractions(values, default):
    """Return bounded vessel body-depth fractions from config or defaults."""
    if values is None:
        return default
    if (not isinstance(values, (list, tuple)) or not values
            or any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not np.isfinite(float(value)) or not 0.05 < float(value) < 0.95
                   for value in values)):
        raise OracleGraspGeometryError(
            "oracle bottle_depth_fractions must be finite fractions strictly between 0.05 and 0.95",
        )
    return tuple(float(value) for value in values)


class OracleGraspGeometryError(ValueError):
    """The oracle grasp configuration or truth record is unusable."""


def validate_gripper_geometry(config):
    """Return validated positive gripper geometry for oracle candidates."""
    if not isinstance(config, dict):
        raise OracleGraspGeometryError("oracle grasp gripper geometry must be an object")
    values = {}
    for key in _GRIPPER_KEYS:
        value = config.get(key)
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not np.isfinite(float(value)) or float(value) <= 0.):
            raise OracleGraspGeometryError(
                f"oracle grasp {key} must be a finite positive number",
            )
        values[key] = float(value)
    return values


def _unit(value, label):
    vector = np.asarray(value, dtype=float)
    if vector.shape != (3,) or not np.isfinite(vector).all():
        raise OracleGraspGeometryError(f"{label} must be a finite 3-vector")
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-9:
        raise OracleGraspGeometryError(f"{label} is unresolved")
    return vector / norm


def _horizontal_toward_base(point, base_xy):
    """Unit horizontal direction from a world point toward the robot base."""
    base = np.asarray(base_xy, dtype=float)
    if base.shape != (2,) or not np.isfinite(base).all():
        raise OracleGraspGeometryError("oracle approach base_xy must be finite")
    horizontal = np.array([base[0] - float(point[0]), base[1] - float(point[1]), 0.])
    norm = float(np.linalg.norm(horizontal))
    if norm <= 1e-6:
        # The object sits at the base; pick a deterministic sideways approach.
        horizontal = np.array([1., 0., 0.])
        norm = 1.
    return horizontal / norm


def _approach_perpendicular_to_axis(approach, axis):
    """Orthogonalize an approach direction against a span axis, deterministically.

    When the requested approach runs along the span axis (for example a rod
    pointing straight at the robot base), the horizontal component degenerates;
    fall back to a fixed perpendicular of the axis instead of amplifying mesh
    sampling residue.
    """
    residual = approach - axis * float(np.dot(approach, axis))
    norm = float(np.linalg.norm(residual))
    if norm <= 0.1:
        # Nearly parallel to the span axis: the residual is mesh-sampling
        # noise. Use a fixed perpendicular of the axis instead.
        reference = np.array([0., 0., 1.])
        if abs(float(np.dot(axis, reference))) > 0.9:
            reference = np.array([1., 0., 0.])
        residual = np.cross(axis, reference)
        norm = float(np.linalg.norm(residual))
        if norm <= 1e-9:
            raise OracleGraspGeometryError("span axis is degenerate")
    return residual / norm


def _provider_rotation(approach, span_axis):
    """Right-handed provider rotation with x=approach and z=span_axis."""
    if abs(float(np.dot(approach, span_axis))) > 1. - 1e-6:
        raise OracleGraspGeometryError("approach direction degenerates along the span axis")
    closing = np.cross(span_axis, approach)
    closing /= float(np.linalg.norm(closing))
    rotation = np.column_stack((approach, closing, span_axis))
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-9) or np.linalg.det(rotation) <= 0.:
        raise OracleGraspGeometryError("provider rotation is not right-handed")
    return rotation


def _median_radius(points, origin, axis):
    offsets = points - origin
    radial = offsets - np.outer(offsets @ axis, axis)
    return float(np.median(np.linalg.norm(radial, axis=1)))


def bottle_grasp_candidates(world_points, rim_feature, *, gripper, base_xy,
                            depth_fractions=None):
    """Semantic body-band grasp candidates for a vessel with a qualified rim.

    Positions sit on the near sidewall along a horizontal approach toward the
    robot base, at several depths below the rim inside the observed body. The
    provider z-axis spans the vessel axis so the TCP finger span follows it,
    exactly as the task-affordance gate requires.
    """
    points = np.asarray(world_points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 20 or not np.isfinite(points).all():
        raise OracleGraspGeometryError("bottle oracle grasp requires finite mesh points")
    tip = np.asarray(rim_feature["tip_world"], dtype=float)
    axis = _unit(rim_feature["axis_world"], "rim axis")
    projections = (points - tip) @ axis
    extent = float(np.ptp(projections))
    if extent <= 0.02:
        raise OracleGraspGeometryError("vessel body extent is unresolved")
    radius = _median_radius(points, tip, axis)
    if radius <= 0.002:
        raise OracleGraspGeometryError("vessel radial extent is unresolved")
    approach = _approach_perpendicular_to_axis(
        _horizontal_toward_base(points.mean(0), base_xy), axis)
    rotation = _provider_rotation(approach, axis)
    candidates = []
    for fraction in validate_depth_fractions(depth_fractions, _BOTTLE_DEPTH_FRACTIONS):
        axis_point = tip + axis * (-extent * fraction)
        candidates.append({
            "position_world_m": axis_point + approach * radius,
            "rotation_world": rotation,
        })
    return candidates


def rod_grasp_candidates(world_points, endpoint_pair, *, gripper, base_xy):
    """Shaft grasp candidates that keep each rod end free in turn.

    Two shaft fractions are emitted so that whichever endpoint the task
    selects as the working end, one candidate keeps it farther from the grasp
    than the task-affordance ambiguity threshold.
    """
    points = np.asarray(world_points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 20 or not np.isfinite(points).all():
        raise OracleGraspGeometryError("rod oracle grasp requires finite mesh points")
    first = np.asarray(endpoint_pair["origin_world"], dtype=float)
    second = np.asarray(endpoint_pair["tip_world"], dtype=float)
    segment = second - first
    length = float(np.linalg.norm(segment))
    if length <= 0.05:
        raise OracleGraspGeometryError("rod length is unresolved")
    axis = segment / length
    radius = _median_radius(points, first, axis)
    if radius <= 0.0005:
        raise OracleGraspGeometryError("rod radial extent is unresolved")
    approach = _approach_perpendicular_to_axis(
        _horizontal_toward_base(points.mean(0), base_xy), axis)
    rotation = _provider_rotation(approach, axis)
    return [
        {
            "position_world_m": first + segment * fraction + approach * radius,
            "rotation_world": rotation,
        }
        for fraction in _ROD_SHAFT_FRACTIONS
    ]


class OracleSimulatorTruthGraspProvider:
    """Grasp provider that derives candidates from recorded simulator truth.

    The provider is deployed only behind the same ``RecordedGraspProvider``
    capture bookkeeping as the model workers. It resolves the entity record
    for the requesting capture, regenerates world geometry from the stored
    point cloud, and reuses the truth process-feature candidates (rim or rod
    endpoint pair) recorded by the simulator-truth understanding path.
    """

    def __init__(self, store, *, gripper_geometry, base_xy=(0., 0.), bottle_depth_fractions=None):
        self.store = store
        self.gripper = validate_gripper_geometry(gripper_geometry)
        self.base_xy = tuple(float(value) for value in base_xy)
        if len(self.base_xy) != 2 or not all(np.isfinite(self.base_xy)):
            raise OracleGraspGeometryError("oracle approach base_xy must be finite")
        self.bottle_depth_fractions = validate_depth_fractions(
            bottle_depth_fractions, _BOTTLE_DEPTH_FRACTIONS)
        self._records_accessor = None

    def bind_records(self, accessor):
        """Bind a callable returning the perception records for a capture."""
        if not callable(accessor):
            raise OracleGraspGeometryError("records accessor must be callable")
        self._records_accessor = accessor

    def release(self):
        return None

    def propose(self, request):
        if self._records_accessor is None:
            raise OracleGraspGeometryError("oracle grasp provider is not bound to perception records")
        identity = {key: request[key] for key in
                    ("observation_ref", "scene_revision", "frame_id", "calibration_ref")}
        records = self._records_accessor(request["calibration_ref"]) or {}
        candidates, ambiguities = [], []
        for target in request["targets"]:
            entity_ref = target["entity_ref"]
            record = records.get(entity_ref)
            if (not isinstance(record, dict)
                    or any(record.get(key) != value for key, value in identity.items())):
                raise OracleGraspGeometryError(
                    "oracle grasp requires a same-capture simulator-truth record",
                )
            if record.get("geometry_qualification") != "simulator_ground_truth":
                raise OracleGraspGeometryError(
                    "oracle grasp requires simulator_ground_truth geometry qualification",
                )
            features = record.get("process_feature_candidates") or []
            try:
                points = np.asarray(np.load(
                    self.store.path(record["points_ref"]), allow_pickle=False), dtype=float)
                transform = np.asarray(record["world_from_camera"], dtype=float)
            except (OSError, TypeError, ValueError, KeyError) as exc:
                raise OracleGraspGeometryError("oracle grasp record artifacts are unreadable") from exc
            if (points.ndim != 2 or points.shape[1] != 3 or len(points) < 3
                    or not np.isfinite(points).all() or transform.shape != (4, 4)):
                raise OracleGraspGeometryError("oracle grasp record geometry is invalid")
            world_points = points @ transform[:3, :3].T + transform[:3, 3]
            category = record.get("category")
            if category in {"reagent_bottle", "mixing_vessel"}:
                rims = [item for item in features
                        if item.get("feature_kind") == "rim" and item.get("tip_world")]
                if len(rims) != 1:
                    ambiguities.append({
                        "code": "oracle_grasp_requires_single_rim",
                        "message": "oracle vessel grasp needs exactly one truth rim candidate",
                        "entity_refs": [entity_ref],
                    })
                    continue
                generated = bottle_grasp_candidates(
                    world_points, rims[0], gripper=self.gripper, base_xy=self.base_xy,
                    depth_fractions=self.bottle_depth_fractions)
            elif category == "stir_tool":
                pairs = [item for item in features
                         if item.get("feature_kind") == "rod_endpoint_pair"]
                if len(pairs) != 2:
                    ambiguities.append({
                        "code": "oracle_grasp_requires_endpoint_pair",
                        "message": "oracle rod grasp needs the truth endpoint pair",
                        "entity_refs": [entity_ref],
                    })
                    continue
                generated = rod_grasp_candidates(
                    world_points, pairs[0], gripper=self.gripper, base_xy=self.base_xy)
            else:
                ambiguities.append({
                    "code": "oracle_grasp_unsupported_category",
                    "message": f"oracle grasp does not cover category {category!r}",
                    "entity_refs": [entity_ref],
                })
                continue
            camera_from_world = np.linalg.inv(transform)
            for item in generated:
                pose_world = np.eye(4)
                pose_world[:3, :3] = item["rotation_world"]
                pose_world[:3, 3] = item["position_world_m"]
                pose_camera = camera_from_world @ pose_world
                candidates.append({
                    "candidate_ref": f"candidate://{entity_ref.removeprefix('entity://')}/{len(candidates)}",
                    "entity_ref": entity_ref,
                    "grasp_frame": {
                        "frame_id": request["frame_id"],
                        "unit": "m",
                        "position_m": [float(value) for value in pose_camera[:3, 3]],
                        "orientation_xyzw": [
                            float(value) for value in Rotation.from_matrix(
                                pose_camera[:3, :3]).as_quat()],
                    },
                    "approach_direction": {
                        "frame_id": request["frame_id"],
                        "unit": "unitless",
                        "vector": [float(value) for value in
                                   camera_from_world[:3, :3] @ item["rotation_world"][:, 0]],
                    },
                    "score": 1.0,
                    "confidence": 1.0,
                    "provenance": [record["points_ref"], record["geometry_ref"]],
                    "qualification": "proposed",
                    "grasp_geometry": {
                        "width_m": self.gripper["gripper_width_m"],
                        "height_m": self.gripper["finger_height_m"],
                        "depth_m": self.gripper["finger_depth_m"],
                    },
                })
        # The snapshot field set and funnel stages are fixed by the generic
        # grasp-proposal contract; lineage stays in candidate provenance and
        # produced_evidence_refs instead of extra output keys.
        return {
            "candidates": candidates,
            "ambiguities": ambiguities,
            "funnel": {
                "decoded": len(candidates),
                "canonicalized": len(candidates),
                "deduplicated": len(candidates),
                "retained": len(candidates),
            },
            "provider_available": True,
            "produced_evidence_refs": sorted({
                ref
                for record in records.values()
                if record.get("calibration_ref") == request["calibration_ref"]
                for ref in (record.get("points_ref"), record.get("geometry_ref"))
                if isinstance(ref, str)
            }),
        }
