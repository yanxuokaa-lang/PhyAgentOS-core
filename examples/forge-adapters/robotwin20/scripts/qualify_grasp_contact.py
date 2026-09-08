#!/usr/bin/env python3
"""Create a provider-owned, no-motion GraspGen contact qualification artifact."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

import yaml

from robotwin20_adapter.grasp_postprocessing import (
    GraspPostprocessingError,
    derive_robot_hand_pose,
    qualify_geometry_artifact,
)


class QualificationCliError(RuntimeError):
    """Input or output binding for contact qualification is invalid."""


def _read_json(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise QualificationCliError(f"{label} must be an absolute regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationCliError(f"{label} is invalid JSON") from exc
    if not isinstance(value, Mapping):
        raise QualificationCliError(f"{label} must contain an object")
    return value


def _candidate(value: Mapping[str, Any]) -> Mapping[str, Any]:
    candidate = value.get("candidate", value)
    if not isinstance(candidate, Mapping):
        raise QualificationCliError("candidate artifact does not contain a candidate")
    if "execution_grasp" not in candidate:
        candidates = value.get("candidates")
        if isinstance(candidates, list) and len(candidates) == 1 and isinstance(candidates[0], Mapping):
            candidate = candidates[0]
    return candidate


def _profile(path: Path) -> Mapping[str, Any]:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise QualificationCliError("route input profile must be an absolute regular file")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise QualificationCliError("route input profile is invalid YAML") from exc
    if not isinstance(value, Mapping) or not isinstance(value.get("grasp_adaptation"), Mapping):
        raise QualificationCliError("route input profile lacks grasp adaptation")
    adaptation = value["grasp_adaptation"]
    required = {
        "robot_target_reference_distance_m", "robot_gripper_bias_m", "robot_delta_matrix"
    }
    if not required.issubset(adaptation):
        raise QualificationCliError("route input profile lacks RoboTwin transform fields")
    return adaptation


def _scene_object(scene: Mapping[str, Any], entity_ref: str) -> tuple[list[float], list[float]]:
    objects = scene.get("objects")
    if not isinstance(objects, list):
        raise QualificationCliError("scene facts objects are unavailable")
    match = next((item for item in objects if isinstance(item, Mapping) and item.get("entity_ref") == entity_ref), None)
    if not isinstance(match, Mapping):
        raise QualificationCliError("scene facts entity is unavailable")
    extents = match.get("half_extents_m")
    transform = match.get("world_T_object")
    if not isinstance(extents, list) or not isinstance(transform, list) or len(transform) != 16:
        raise QualificationCliError("scene facts object geometry is incomplete")
    center = [float(transform[index]) for index in (3, 7, 11)]
    half_extents = [float(item) for item in extents]
    if any(not math.isfinite(item) for item in [*center, *half_extents]) or any(item <= 0 for item in half_extents):
        raise QualificationCliError("scene facts object geometry is invalid")
    return center, half_extents


def qualify(*, candidate_file: Path, geometry_file: Path, scene_file: Path, profile_file: Path, entity_ref: str, arm_id: str) -> dict[str, Any]:
    candidate = _candidate(_read_json(candidate_file, "candidate artifact"))
    geometry = _read_json(geometry_file, "contact geometry artifact")
    scene = _read_json(scene_file, "scene facts")
    adaptation = _profile(profile_file)
    if candidate.get("entity_ref") != entity_ref:
        raise QualificationCliError("candidate entity binding is invalid")
    center, extents = _scene_object(scene, entity_ref)
    grasp = candidate.get("execution_grasp")
    if not isinstance(grasp, Mapping) or not isinstance(grasp.get("robot_target_pose"), Mapping):
        raise QualificationCliError("candidate execution grasp is incomplete")
    try:
        hand_pose = derive_robot_hand_pose(
            grasp["robot_target_pose"],
            reference_distance_m=adaptation["robot_target_reference_distance_m"],
            gripper_bias_m=adaptation["robot_gripper_bias_m"],
            delta_matrix=adaptation["robot_delta_matrix"],
        )
        return qualify_geometry_artifact(
            candidate,
            geometry,
            arm_id=arm_id,
            object_center_m=center,
            object_half_extents_m=extents,
            backoff_candidates_m=[0.0],
            target_hand_pose=hand_pose,
        )
    except (GraspPostprocessingError, TypeError, ValueError) as exc:
        raise QualificationCliError("contact qualification failed") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--contact-geometry", type=Path, required=True)
    parser.add_argument("--scene-facts", type=Path, required=True)
    parser.add_argument("--route-input-profile", type=Path, required=True)
    parser.add_argument("--entity-ref", required=True)
    parser.add_argument("--arm-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.output.is_absolute() or args.output.exists() or args.output.is_symlink():
        raise SystemExit("output must be a new absolute file")
    try:
        result = qualify(
            candidate_file=args.candidate,
            geometry_file=args.contact_geometry,
            scene_file=args.scene_facts,
            profile_file=args.route_input_profile,
            entity_ref=args.entity_ref,
            arm_id=args.arm_id,
        )
    except QualificationCliError as exc:
        raise SystemExit(str(exc)) from exc
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output), "motion_authorized": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
