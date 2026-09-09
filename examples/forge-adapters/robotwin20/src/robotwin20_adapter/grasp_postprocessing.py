"""Provider-owned, no-motion GraspGen contact-depth qualification.

The GraspGen pose is kept as the perception result.  This module only derives
an execution variant by translating the complete gripper along the provider's
declared ingress axis.  It uses measured collision vertices and a support
plane; it does not call a planner, simulator, Gateway, or actuator.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from itertools import product
from typing import Any

GRASP_POSTPROCESSING_SCHEMA_VERSION = "paos-robotwin20-grasp-postprocessing/v1"


class GraspPostprocessingError(ValueError):
    """A contact variant cannot be qualified from the supplied geometry."""


def _vector(value: Any, length: int, label: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise GraspPostprocessingError(f"{label} must contain {length} numbers")
    result = [float(item) for item in value]
    if any(not math.isfinite(item) for item in result):
        raise GraspPostprocessingError(f"{label} contains non-finite values")
    return result


def _unit(value: Any, label: str) -> list[float]:
    result = _vector(value, 3, label)
    norm = math.sqrt(sum(item * item for item in result))
    if norm <= 1e-9:
        raise GraspPostprocessingError(f"{label} is degenerate")
    return [item / norm for item in result]


def _quaternion_rotation(value: Any, label: str) -> list[list[float]]:
    x, y, z, w = _vector(value, 4, label)
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if norm <= 1e-9:
        raise GraspPostprocessingError(f"{label} is degenerate")
    x, y, z, w = (item / norm for item in (x, y, z, w))
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]


def _rotate(rotation: Sequence[Sequence[float]], vector: Sequence[float]) -> list[float]:
    return [sum(float(rotation[row][index]) * float(vector[index]) for index in range(3)) for row in range(3)]


def _rotation_quaternion(rotation: Sequence[Sequence[float]]) -> list[float]:
    trace = sum(float(rotation[index][index]) for index in range(3))
    if trace > 0:
        scale = math.sqrt(trace + 1.0) * 2
        result = [
            (rotation[2][1] - rotation[1][2]) / scale,
            (rotation[0][2] - rotation[2][0]) / scale,
            (rotation[1][0] - rotation[0][1]) / scale,
            0.25 * scale,
        ]
    else:
        axis = max(range(3), key=lambda index: rotation[index][index])
        if axis == 0:
            scale = math.sqrt(1 + rotation[0][0] - rotation[1][1] - rotation[2][2]) * 2
            result = [0.25 * scale, (rotation[0][1] + rotation[1][0]) / scale, (rotation[0][2] + rotation[2][0]) / scale, (rotation[2][1] - rotation[1][2]) / scale]
        elif axis == 1:
            scale = math.sqrt(1 + rotation[1][1] - rotation[0][0] - rotation[2][2]) * 2
            result = [(rotation[0][1] + rotation[1][0]) / scale, 0.25 * scale, (rotation[1][2] + rotation[2][1]) / scale, (rotation[0][2] - rotation[2][0]) / scale]
        else:
            scale = math.sqrt(1 + rotation[2][2] - rotation[0][0] - rotation[1][1]) * 2
            result = [(rotation[0][2] + rotation[2][0]) / scale, (rotation[1][2] + rotation[2][1]) / scale, 0.25 * scale, (rotation[1][0] - rotation[0][1]) / scale]
    norm = math.sqrt(sum(float(item) * float(item) for item in result))
    return [float(item) / norm for item in result]


def derive_robot_hand_pose(
    robot_target_pose: Mapping[str, Any],
    *,
    reference_distance_m: float,
    gripper_bias_m: float,
    delta_matrix: Sequence[Sequence[float]],
) -> dict[str, Any]:
    """Derive RoboTwin's actual hand pose from its route gripper target.

    ``reference_distance_m`` is supplied by the provider profile used by
    RoboTwin's gripper-to-endlink transform.
    """

    position, quaternion = _pose(robot_target_pose, "robot_target_pose")
    if (
        isinstance(reference_distance_m, bool)
        or not math.isfinite(float(reference_distance_m))
        or float(reference_distance_m) <= 0
    ):
        raise GraspPostprocessingError("reference distance must be positive")
    if (
        isinstance(gripper_bias_m, bool)
        or not math.isfinite(float(gripper_bias_m))
        or float(gripper_bias_m) < 0
    ):
        raise GraspPostprocessingError("gripper bias must be finite and non-negative")
    delta = [[float(item) for item in row] for row in delta_matrix]
    if len(delta) != 3 or any(len(row) != 3 for row in delta) or any(
        not math.isfinite(item) for row in delta for item in row
    ):
        raise GraspPostprocessingError("delta matrix must be 3x3")
    rotation = _quaternion_rotation(quaternion, "robot target orientation")
    offset = _rotate(
        rotation, [float(reference_distance_m) - float(gripper_bias_m), 0.0, 0.0]
    )
    inverse_delta = [[delta[column][row] for column in range(3)] for row in range(3)]
    hand_rotation = [
        [sum(rotation[row][index] * inverse_delta[index][column] for index in range(3)) for column in range(3)]
        for row in range(3)
    ]
    return {
        "frame_id": robot_target_pose["frame_id"],
        "position_m": [position[index] + offset[index] for index in range(3)],
        "orientation_xyzw": _rotation_quaternion(hand_rotation),
    }


def _project_reference_vertices(
    vertices: Sequence[Sequence[float]],
    reference_pose: Mapping[str, Any],
    target_pose: Mapping[str, Any],
) -> list[list[float]]:
    """Move reset-world vertices from the reference hand pose to target pose."""

    if not isinstance(reference_pose, Mapping) or set(reference_pose) != {
        "frame_id", "position_m", "orientation_wxyz"
    }:
        raise GraspPostprocessingError("reference hand pose fields are invalid")
    if reference_pose["frame_id"] != "world":
        raise GraspPostprocessingError("reference hand pose frame is invalid")
    reference_position = _vector(reference_pose["position_m"], 3, "reference hand position")
    reference_wxyz = _vector(reference_pose["orientation_wxyz"], 4, "reference hand orientation")
    reference_rotation = _quaternion_rotation(
        [reference_wxyz[1], reference_wxyz[2], reference_wxyz[3], reference_wxyz[0]],
        "reference hand orientation",
    )
    target_position, target_quaternion = _pose(target_pose, "robot_target_pose")
    target_rotation = _quaternion_rotation(target_quaternion, "robot target orientation")
    # The reference rotation is orthonormal, so its transpose is the inverse.
    reference_inverse = [[reference_rotation[column][row] for column in range(3)] for row in range(3)]
    projected: list[list[float]] = []
    for vertex in vertices:
        world_vertex = _vector(vertex, 3, "gripper collision vertex")
        relative = [world_vertex[index] - reference_position[index] for index in range(3)]
        local = _rotate(reference_inverse, relative)
        moved = _rotate(target_rotation, local)
        projected.append([moved[index] + target_position[index] for index in range(3)])
    return projected


def _pose(value: Mapping[str, Any], label: str) -> tuple[list[float], list[float]]:
    if not isinstance(value, Mapping) or set(value) != {
        "frame_id", "position_m", "orientation_xyzw"
    }:
        raise GraspPostprocessingError(f"{label} fields are invalid")
    position = _vector(value["position_m"], 3, f"{label}.position_m")
    quaternion = _vector(value["orientation_xyzw"], 4, f"{label}.orientation_xyzw")
    norm = math.sqrt(sum(item * item for item in quaternion))
    if norm <= 1e-9:
        raise GraspPostprocessingError(f"{label}.orientation_xyzw is degenerate")
    return position, [item / norm for item in quaternion]


def _backoff_position(position: Sequence[float], ingress: Sequence[float], distance: float) -> list[float]:
    return [float(p) - float(distance) * float(axis) for p, axis in zip(position, ingress)]


def _object_contains(point: Sequence[float], center: Sequence[float], half_extents: Sequence[float], rotation: Sequence[Sequence[float]]) -> bool:
    local = _rotate(list(zip(*rotation)), [a - b for a, b in zip(point, center)])
    return all(abs(value) <= extent + 1e-9 for value, extent in zip(local, half_extents))


def _pinch_geometry(contact: Sequence[float], center: Sequence[float], extents: Sequence[float], object_rotation: Sequence[Sequence[float]], hand_pose: Mapping[str, Any], links: Mapping[str, Any], delta: Sequence[float]) -> bool:
    """Conservative Panda open-finger envelope, not a force-closure verdict."""
    position, quaternion = _pose(hand_pose, "hand pose")
    inverse = list(zip(*_quaternion_rotation(quaternion, "hand orientation")))
    def local(point):
        return _rotate(inverse, [point[i] - position[i] - delta[i] for i in range(3)])
    corners = [local([center[i] + offset[i] for i in range(3)]) for offset in (
        _rotate(object_rotation, [sign[i] * extents[i] for i in range(3)])
        for sign in product((-1, 1), repeat=3)
    )]
    object_low = [min(point[i] for point in corners) for i in range(3)]
    object_high = [max(point[i] for point in corners) for i in range(3)]
    # Link snapshots are already at the nominal hand pose; their local bounds
    # stay fixed when the complete gripper is translated by a backoff.
    bounds = {}
    for name, vertices in links.items():
        points = [_rotate(inverse, [point[i] - position[i] for i in range(3)]) for point in vertices]
        bounds[name] = ([min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)])
    fingers = sorted((bounds[name] for name in ("panda_leftfinger", "panda_rightfinger")), key=lambda bound: bound[0][1])
    if object_low[1] < fingers[0][1][1] or object_high[1] > fingers[1][0][1]:
        return False
    center_local = local(contact)
    for low, high in fingers:
        if any(not low[i] <= center_local[i] <= high[i] for i in (0, 2)):
            return False
    hand_low, hand_high = bounds["panda_hand"]
    return any(object_high[i] < hand_low[i] or object_low[i] > hand_high[i] for i in range(3))


def qualify_contact_variants(
    candidate: Mapping[str, Any],
    *,
    gripper_vertices_m: Sequence[Sequence[float]],
    object_center_m: Sequence[float],
    object_half_extents_m: Sequence[float],
    support_normal: Sequence[float],
    support_offset_m: float,
    backoff_candidates_m: Sequence[float],
    curobo_clearance_m: Sequence[float | None] | None = None,
    object_orientation_xyzw: Sequence[float] = (0, 0, 0, 1),
    hand_pose: Mapping[str, Any] | None = None,
    gripper_links_m: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Select the smallest declared backoff that clears support and keeps pinch.

    ``gripper_vertices_m`` are expressed in the route/world frame at the
    nominal robot-target pose (the provider worker's snapshot convention).
    Backoff translates that snapshot by the target-pose delta, so clearance
    is evaluated for the actual shallower execution pose.
    """

    if not isinstance(candidate, Mapping):
        raise GraspPostprocessingError("candidate is invalid")
    candidate_ref = candidate.get("candidate_ref")
    grasp = candidate.get("execution_grasp")
    if not isinstance(candidate_ref, str) or not candidate_ref.startswith("candidate://"):
        raise GraspPostprocessingError("candidate_ref is invalid")
    if not isinstance(grasp, Mapping):
        raise GraspPostprocessingError("candidate execution grasp is missing")
    contact_position, _ = _pose(grasp.get("contact_center_pose"), "contact_center_pose")
    target_position, _ = _pose(grasp.get("robot_target_pose"), "robot_target_pose")
    ingress = _unit(grasp.get("ingress_direction", {}).get("vector"), "ingress_direction")
    vertices = [_vector(item, 3, "gripper collision vertex") for item in gripper_vertices_m]
    if not vertices:
        raise GraspPostprocessingError("gripper collision vertices are empty")
    center = _vector(object_center_m, 3, "object center")
    object_rotation = _quaternion_rotation(object_orientation_xyzw, "object orientation")
    extents = _vector(object_half_extents_m, 3, "object half extents")
    if any(item <= 0 for item in extents):
        raise GraspPostprocessingError("object half extents must be positive")
    normal = _unit(support_normal, "support normal")
    support_offset = float(support_offset_m)
    if not math.isfinite(support_offset):
        raise GraspPostprocessingError("support offset is non-finite")
    distances = [float(item) for item in backoff_candidates_m]
    if not distances or any(not math.isfinite(item) or item < 0 for item in distances):
        raise GraspPostprocessingError("backoff candidates must be finite and non-negative")
    if distances != sorted(set(distances)):
        raise GraspPostprocessingError("backoff candidates must be strictly increasing")
    if curobo_clearance_m is not None:
        if len(curobo_clearance_m) != len(distances):
            raise GraspPostprocessingError(
                "curobo clearance evidence must match backoff candidates"
            )
        for value in curobo_clearance_m:
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise GraspPostprocessingError("curobo clearance evidence is invalid")

    variants: list[dict[str, Any]] = []
    for index, distance in enumerate(distances):
        target = _backoff_position(target_position, ingress, distance)
        contact = _backoff_position(contact_position, ingress, distance)
        delta = [target[index] - target_position[index] for index in range(3)]
        world_vertices = [[vertex[index] + delta[index] for index in range(3)] for vertex in vertices]
        clearance = min(sum(normal[index] * point[index] for index in range(3)) - support_offset for point in world_vertices)
        pinch = _object_contains(contact, center, extents, object_rotation)
        finger_fit = None if gripper_links_m is None else _pinch_geometry(
            contact, center, extents, object_rotation, hand_pose, gripper_links_m, delta
        )
        curobo_clearance = (
            None if curobo_clearance_m is None else curobo_clearance_m[index]
        )
        curobo_valid = curobo_clearance_m is None or (
            curobo_clearance is not None and float(curobo_clearance) >= 0
        )
        variants.append({
            "backoff_m": distance,
            "robot_target_position_m": target,
            "contact_center_position_m": contact,
            "support_clearance_m": clearance,
            "pinch_center_inside_object": pinch,
            "finger_envelope_fit": finger_fit,
            **({"curobo_clearance_m": curobo_clearance} if curobo_clearance_m is not None else {}),
            "rejection_reasons": [reason for rejected, reason in (
                (clearance < 0, "mesh_support_penetration"),
                (not pinch, "contact_center_outside_object"),
                (finger_fit is False, "finger_envelope_rejected"),
                (not curobo_valid, "curobo_collision_or_unavailable"),
            ) if rejected],
            "status": "valid" if clearance >= 0 and pinch and finger_fit is not False and curobo_valid else "rejected",
        })
    selected = next((item for item in variants if item["status"] == "valid"), None)
    return {
        "schema_version": GRASP_POSTPROCESSING_SCHEMA_VERSION,
        "parent_candidate_ref": candidate_ref,
        "selected_backoff_m": None if selected is None else selected["backoff_m"],
        "variants": variants,
        "status": "qualified" if selected is not None else "unavailable",
        "motion_authorized": False,
        "qualification_scope": "mesh_and_curobo_contact" if curobo_clearance_m is not None else "mesh_contact_only",
    }


def apply_contact_variant(execution_grasp: Mapping[str, Any], qualification: Mapping[str, Any]) -> dict[str, Any]:
    """Return a route-ready execution grasp without mutating either input."""

    if qualification.get("schema_version") != GRASP_POSTPROCESSING_SCHEMA_VERSION:
        raise GraspPostprocessingError("qualification schema is unsupported")
    if qualification.get("status") != "qualified" or qualification.get("motion_authorized") is not False:
        raise GraspPostprocessingError("qualification does not contain a usable no-motion variant")
    selected = next((item for item in qualification.get("variants", []) if item.get("status") == "valid"), None)
    if selected is None:
        raise GraspPostprocessingError("qualification has no selected variant")
    result = deepcopy(dict(execution_grasp))
    for field, key in (("robot_target_pose", "robot_target_position_m"), ("contact_center_pose", "contact_center_position_m")):
        pose = deepcopy(result[field])
        pose["position_m"] = list(selected[key])
        result[field] = pose
    return result


def qualify_geometry_artifact(
    candidate: Mapping[str, Any],
    geometry_artifact: Mapping[str, Any],
    *,
    arm_id: str,
    object_center_m: Sequence[float],
    object_half_extents_m: Sequence[float],
    backoff_candidates_m: Sequence[float],
    target_hand_pose: Mapping[str, Any] | None = None,
    curobo_clearance_m: Sequence[float | None] | None = None,
    object_orientation_xyzw: Sequence[float] = (0, 0, 0, 1),
    check_finger_envelope: bool = False,
) -> dict[str, Any]:
    """Bridge a RoboTwin geometry artifact into the pure qualification seam."""

    if geometry_artifact.get("schema_version") != "paos-robotwin20-grasp-contact-geometry/v1":
        raise GraspPostprocessingError("contact geometry artifact schema is unsupported")
    if geometry_artifact.get("frame_id") != "world" or geometry_artifact.get("motion_authorized") is not False:
        raise GraspPostprocessingError("contact geometry artifact binding is invalid")
    if geometry_artifact.get("scene_revision") != candidate.get("scene_revision"):
        raise GraspPostprocessingError("contact geometry scene revision is stale")
    arms = geometry_artifact.get("arms")
    if not isinstance(arms, Mapping) or arm_id not in arms:
        raise GraspPostprocessingError("contact geometry arm is unavailable")
    links = arms[arm_id].get("links")
    if not isinstance(links, Mapping):
        raise GraspPostprocessingError("contact geometry links are unavailable")
    vertices: list[Sequence[float]] = []
    for name in ("panda_hand", "panda_leftfinger", "panda_rightfinger"):
        value = links.get(name)
        if not isinstance(value, list):
            raise GraspPostprocessingError("contact geometry link vertices are unavailable")
        vertices.extend(value)
    reference_pose = arms[arm_id].get("reference_hand_pose")
    if not isinstance(reference_pose, Mapping):
        raise GraspPostprocessingError("contact geometry reference hand pose is unavailable")
    grasp = candidate.get("execution_grasp")
    if not isinstance(grasp, Mapping):
        raise GraspPostprocessingError("candidate execution grasp is missing")
    target_pose = target_hand_pose or grasp.get("robot_target_pose")
    if not isinstance(target_pose, Mapping):
        raise GraspPostprocessingError("candidate robot target pose is missing")
    vertices = _project_reference_vertices(vertices, reference_pose, target_pose)
    support = geometry_artifact.get("support_plane")
    if not isinstance(support, Mapping):
        raise GraspPostprocessingError("contact geometry support plane is unavailable")
    return qualify_contact_variants(
        candidate,
        gripper_vertices_m=vertices,
        object_center_m=object_center_m,
        object_half_extents_m=object_half_extents_m,
        support_normal=support.get("normal"),
        support_offset_m=support.get("offset_m"),
        backoff_candidates_m=backoff_candidates_m,
        curobo_clearance_m=curobo_clearance_m,
        object_orientation_xyzw=object_orientation_xyzw,
        hand_pose=target_pose,
        gripper_links_m={name: _project_reference_vertices(value, reference_pose, target_pose) for name, value in links.items()} if check_finger_envelope else None,
    )


__all__ = [
    "GRASP_POSTPROCESSING_SCHEMA_VERSION",
    "GraspPostprocessingError",
    "apply_contact_variant",
    "derive_robot_hand_pose",
    "qualify_geometry_artifact",
    "qualify_contact_variants",
]
