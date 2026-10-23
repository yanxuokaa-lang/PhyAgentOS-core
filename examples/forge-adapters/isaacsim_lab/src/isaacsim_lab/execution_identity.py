"""Private RGB-D-to-rigid-body correspondence; never produces visual geometry."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import numpy as np
from PhyAgentOS.forge.artifacts import LocalFilesystemArtifactResolver

from .phase_motion import PhaseMotionError
from .visual_geometry import world_from_camera


def bind_observed_entities(model, request):
    import carb
    from omni.physx import get_physx_scene_query_interface
    from pxr import UsdPhysics

    revision = model.session.current_scene_revision()
    captures = model.session.resolve("observation_captures") or {}
    capture = captures.get(request["calibration_ref"])
    if request["scene_revision"] != revision or capture is None or capture["scene_revision"] != revision:
        raise PhaseMotionError("stale_visual_observation", "identity binding requires the current capture")
    if capture["frame_id"] != request["frame_id"] or set(request["artifacts"]) != {i["ref"] for i in capture["artifacts"]}:
        raise PhaseMotionError("visual_capture_mismatch", "identity binding must use one RGB-D capture")
    resolver = LocalFilesystemArtifactResolver({"labutopia": model.artifact_root})
    calibration = json.loads(resolver.resolve(request["calibration_ref"]).data)
    from .visual_perception import LabArtifactStore
    store = LabArtifactStore(model.artifact_root)
    transform = world_from_camera(calibration)
    records, selected = [], set()
    query = get_physx_scene_query_interface()
    for claim in request["claims"]:
        points = association_points(store, claim, request)
        origin = transform[:3, 3]
        matches, errors = [], []
        for camera_point in points:
            point = transform[:3, :3] @ camera_point + origin
            distance = float(np.linalg.norm(point-origin))
            surface_matches = set()
            def hit(item):
                try:
                    if abs(float(item.distance)-distance) <= .01:
                        prim = model.stage.GetPrimAtPath(str(item.rigid_body))
                        while prim.IsValid() and not prim.HasAPI(UsdPhysics.RigidBodyAPI):
                            prim = prim.GetParent()
                        if prim.IsValid() and not str(prim.GetPath()).startswith(model.robot.prim_path+"/"):
                            surface_matches.add(str(prim.GetPath()))
                except Exception as exc:
                    errors.append(exc)
                return True
            query.raycast_all(carb.Float3(*origin), carb.Float3(*((point-origin)/distance)), distance+.01, hit)
            if len(surface_matches) > 1:
                raise PhaseMotionError("visual_body_association_ambiguous", "one observed ray matches multiple bodies")
            matches.extend(surface_matches)
        if errors or len(matches) < 3 or len(set(matches)) != 1:
            raise PhaseMotionError("visual_body_association_ambiguous", "observed cloud does not identify one rigid body")
        path = matches[0]
        if path in selected:
            raise PhaseMotionError("duplicate_visual_body", "visual objects resolve to the same rigid body")
        selected.add(path)
        # Preserve the perception entity; physics never supplies identity,
        # repaired points, grasp candidates or process features.
        records.append({"entity_ref": claim["entity_ref"], "prim_path": path,
                        "captured_body_pose": model.body_pose(path).tolist()})
    return {"status": "available", "records": records, "capabilities": measured_capabilities(model, request),
            "scene_revision": revision, "motion_authorized": False}


def association_points(store, claim, request):
    """Resolve current recovered camera points, never the raw-depth seed."""
    path = store.resolve_point_cloud(claim["points_ref"])
    evidence = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if any(evidence[key] != request[key] for key in
           ("observation_ref", "scene_revision", "frame_id", "calibration_ref")) or evidence["entity_ref"] != claim["entity_ref"]:
        raise PhaseMotionError("visual_capture_mismatch", "execution cloud is from a different observation")
    points = np.load(path, allow_pickle=False)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 3 or not np.isfinite(points).all() or np.any(points[:, 2] <= 0):
        raise PhaseMotionError("invalid_observed_cloud", "execution correspondence requires finite camera points")
    return points[np.linspace(0, len(points)-1, min(25, len(points))).astype(int)]


def measured_capabilities(model, request):
    from PhyAgentOS.forge.manipulation import (
        ArmCapability,
        CapabilitySnapshot,
        capability_snapshot_digest,
    )
    from PhyAgentOS.utils.atomic_file import atomic_write_bytes

    description = {"configuration": model.config, "joint_names": model.solver.get_joint_names(),
                   "joint_limits": model.limits.tolist(), "robot_prim_path": model.robot.prim_path,
                   "hand_from_tcp": model.hand_from_tcp.tolist()}
    reference = model._artifact("capability-description", description)
    arm = ArmCapability(arm_id="franka", base_frame="world", tool_frame="tool_center",
                        planner_profile_ref=reference, workspace_ref=reference, joint_limits_ref=reference,
                        gripper_identity="franka_parallel_fingers", supported_modes=("single_resource",))
    relative = f"capabilities/{uuid4().hex}.json"
    snapshot = {"schema_version": "paos-manipulation-capability-snapshot/v1",
                "snapshot_ref": f"artifact://labutopia/{relative}", "snapshot_digest": "0" * 64,
                **{key: request[key] for key in ("scene_revision", "observation_ref", "calibration_ref")},
                "embodiment_id": "franka_lab", "topology": "single_arm",
                "profile_digest": sha256(json.dumps(description, sort_keys=True).encode()).hexdigest(),
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "arms": [arm.model_dump(mode="json")], "motion_authorized": False}
    snapshot["snapshot_digest"] = capability_snapshot_digest(snapshot)
    snapshot = CapabilitySnapshot.model_validate(snapshot).model_dump(mode="json")
    atomic_write_bytes(model.artifact_root / relative, json.dumps(snapshot).encode())
    return snapshot
