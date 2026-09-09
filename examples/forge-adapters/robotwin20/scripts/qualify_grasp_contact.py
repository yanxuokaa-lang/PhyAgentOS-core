#!/usr/bin/env python3
"""Create a provider-owned, no-motion GraspGen contact qualification artifact."""

from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yaml

from robotwin20_adapter.grasp_postprocessing import (
    GraspPostprocessingError,
    _rotation_quaternion,
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


def _candidate(value: Mapping[str, Any], candidate_ref: str | None = None) -> Mapping[str, Any]:
    if candidate_ref is not None:
        candidates = value.get("candidates", [value.get("candidate", value)])
        candidate = next((item for item in candidates if item.get("candidate_ref") == candidate_ref), None)
        if candidate is None:
            raise QualificationCliError("requested candidate is unavailable")
        return {**candidate, "scene_revision": candidate.get("scene_revision", value.get("scene_revision"))}
    candidate = value.get("candidate", value)
    if not isinstance(candidate, Mapping):
        raise QualificationCliError("candidate artifact does not contain a candidate")
    if "execution_grasp" not in candidate:
        candidates = value.get("candidates")
        if isinstance(candidates, list) and len(candidates) == 1 and isinstance(candidates[0], Mapping):
            candidate = candidates[0]
    if "scene_revision" not in candidate and isinstance(value.get("scene_revision"), str):
        candidate = {**candidate, "scene_revision": value["scene_revision"]}
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
    candidates = adaptation.get("contact_backoff_candidates_m", [0.0])
    if (
        not isinstance(candidates, list)
        or not candidates
        or any(
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(float(item))
            or float(item) < 0
            for item in candidates
        )
        or candidates != sorted(set(candidates))
    ):
        raise QualificationCliError("route input contact backoff candidates are invalid")
    return adaptation


def _scene_object(scene: Mapping[str, Any], entity_ref: str) -> tuple[list[float], list[float], list[float]]:
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
    return center, half_extents, _rotation_quaternion([transform[i:i + 3] for i in (0, 4, 8)])


def _curobo_clearance(
    path: Path | None,
    *,
    candidate: Mapping[str, Any],
    arm_id: str,
    backoff_candidates_m: list[float],
) -> list[float | None] | None:
    if path is None:
        return None
    value = _read_json(path, "Curobo contact qualification")
    if value.get("schema_version") != "paos-robotwin20-curobo-contact-qualification/v1":
        raise QualificationCliError("Curobo contact qualification schema is unsupported")
    if (
        value.get("candidate_ref") != candidate.get("candidate_ref")
        or value.get("scene_revision") != candidate.get("scene_revision")
        or value.get("arm_id") != arm_id
        or value.get("motion_authorized") is not False
    ):
        raise QualificationCliError("Curobo contact qualification binding is invalid")
    variants = value.get("variants")
    if not isinstance(variants, list) or len(variants) != len(backoff_candidates_m):
        raise QualificationCliError("Curobo contact qualification candidates are incomplete")
    result: list[float | None] = []
    for expected, item in zip(backoff_candidates_m, variants):
        if not isinstance(item, Mapping) or float(item.get("backoff_m", float("nan"))) != expected:
            raise QualificationCliError("Curobo contact qualification backoff binding is invalid")
        status = item.get("planner_status")
        clearance = item.get("clearance_m")
        if status != "success":
            result.append(None)
            continue
        if isinstance(clearance, bool) or not isinstance(clearance, (int, float)) or not math.isfinite(float(clearance)):
            raise QualificationCliError("Curobo contact qualification clearance is invalid")
        result.append(float(clearance))
    return result


def qualify(*, candidate_file: Path, geometry_file: Path, scene_file: Path, profile_file: Path, entity_ref: str, arm_id: str, curobo_file: Path | None = None, candidate_ref: str | None = None, runtime_root: Path | None = None, runtime_profile: Path | None = None, collision_world_file: Path | None = None, check_finger_envelope: bool = False) -> dict[str, Any]:
    candidate = _candidate(_read_json(candidate_file, "candidate artifact"), candidate_ref)
    geometry = _read_json(geometry_file, "contact geometry artifact")
    scene = _read_json(scene_file, "scene facts")
    adaptation = _profile(profile_file)
    if candidate.get("entity_ref") != entity_ref:
        raise QualificationCliError("candidate entity binding is invalid")
    center, extents, orientation = _scene_object(scene, entity_ref)
    grasp = candidate.get("execution_grasp")
    if not isinstance(grasp, Mapping) or not isinstance(grasp.get("robot_target_pose"), Mapping):
        raise QualificationCliError("candidate execution grasp is incomplete")
    backoff_candidates = adaptation.get("contact_backoff_candidates_m", [0.0])
    curobo_clearance = _curobo_clearance(
        curobo_file,
        candidate=candidate,
        arm_id=arm_id,
        backoff_candidates_m=backoff_candidates,
    )
    live_evidence = None
    if runtime_root is not None:
        if curobo_file is not None or runtime_profile is None or collision_world_file is None:
            raise QualificationCliError("live qualification requires runtime profile and collision world, without replay Curobo evidence")
        policy = yaml.safe_load(profile_file.read_text())["route_policy"]
        live_evidence, geometry = _live_qualification(runtime_root, runtime_profile, candidate, collision_world_file, backoff_candidates, arm_id, geometry_file.parent, float(policy["approach_clearance_m"]))
        curobo_clearance = [item["clearance_m"] if item["planner_status"] == "success" else None for item in live_evidence["variants"]]
        check_finger_envelope = True
    try:
        hand_pose = derive_robot_hand_pose(
            grasp["robot_target_pose"],
            reference_distance_m=adaptation["robot_target_reference_distance_m"],
            gripper_bias_m=adaptation["robot_gripper_bias_m"],
            delta_matrix=adaptation["robot_delta_matrix"],
        )
        result = qualify_geometry_artifact(
            candidate,
            geometry,
            arm_id=arm_id,
            object_center_m=center,
            object_half_extents_m=extents,
            backoff_candidates_m=backoff_candidates,
            target_hand_pose=hand_pose,
            curobo_clearance_m=curobo_clearance,
            object_orientation_xyzw=orientation,
            check_finger_envelope=check_finger_envelope,
        )
        if live_evidence is not None:
            result["provider_evaluation"] = live_evidence
        return result
    except (GraspPostprocessingError, TypeError, ValueError) as exc:
        raise QualificationCliError("contact qualification failed") from exc


def _live_qualification(runtime_root, runtime_profile, candidate, collision_world_file, distances, arm, artifact_root, approach_clearance_m):
    from robotwin_backend import RoboTwinRuntimeProfile, RoboTwinSensorBackend, load_runtime_profile
    from robotwin_grasp_contact_geometry_worker import capture_task_geometry
    from robotwin_route_planner import evaluate_contact, prepare_planning_world

    profile = load_runtime_profile(runtime_profile)
    if candidate["scene_revision"] != f"{profile['task_name']}-{profile['seed']}-1":
        raise QualificationCliError("live qualification scene revision mismatch")
    world = _read_json(collision_world_file, "collision world")
    if world["scene_revision"] != candidate["scene_revision"] or world["target_entity_ref"] != candidate["entity_ref"]:
        raise QualificationCliError("live qualification collision world mismatch")
    backend = RoboTwinSensorBackend(RoboTwinRuntimeProfile(runtime_root=runtime_root, artifact_root=artifact_root, task_name=profile["task_name"], task_config=profile["task_config"], embodiment=profile["embodiment"]))
    try:
        backend.reset(seed=profile["seed"])
        task = backend._task
        world_evidence = prepare_planning_world(task, world)
        geometry = capture_task_geometry(task, profile)
        variants = []
        for distance in distances:
            grasp = deepcopy(candidate["execution_grasp"])
            ingress = grasp["ingress_direction"]["vector"]
            for key in ("robot_target_pose", "contact_center_pose"):
                grasp[key]["position_m"] = [p - distance * axis for p, axis in zip(grasp[key]["position_m"], ingress)]
            variants.append({"backoff_m": distance, **evaluate_contact(task, grasp, arm, approach_clearance_m)})
        return {"candidate_ref": candidate["candidate_ref"], "arm_id": arm, "scene_revision": candidate["scene_revision"], "runtime_profile": dict(profile), "runtime_root": str(runtime_root), "variants": variants, "world": world_evidence, "simulator_steps": 0, "motion_authorized": False}, geometry
    finally:
        backend.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--contact-geometry", type=Path, required=True)
    parser.add_argument("--scene-facts", type=Path, required=True)
    parser.add_argument("--route-input-profile", type=Path, required=True)
    parser.add_argument("--entity-ref", required=True)
    parser.add_argument("--arm-id", required=True)
    parser.add_argument("--candidate-ref")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--runtime-profile", type=Path)
    parser.add_argument("--collision-world", type=Path)
    parser.add_argument("--check-finger-envelope", action="store_true")
    parser.add_argument(
        "--curobo-qualification",
        type=Path,
        help="Optional provider-owned no-motion Curobo sphere clearance artifact.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if any((args.runtime_root, args.runtime_profile, args.collision_world)) and not all((args.runtime_root, args.runtime_profile, args.collision_world)):
        parser.error("live qualification requires runtime-root, runtime-profile and collision-world together")
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
            curobo_file=args.curobo_qualification,
            candidate_ref=args.candidate_ref,
            runtime_root=args.runtime_root,
            runtime_profile=args.runtime_profile,
            collision_world_file=args.collision_world,
            check_finger_envelope=args.check_finger_envelope,
        )
    except QualificationCliError as exc:
        raise SystemExit(str(exc)) from exc
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output), "motion_authorized": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
