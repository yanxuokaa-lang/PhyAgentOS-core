"""Replay recorded collision joint samples as geometry only; never command motion.

Run with the Isaac environment and an explicit profile/receipt/output directory.
Historical receipts are diagnostics, never fresh preparation or motion authority.
"""

from __future__ import annotations

import argparse
import faulthandler
import json
import re
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import numpy as np


def checked_samples(receipt):
    """Prefer structured geometry; retain support for legacy private receipts."""
    for index, attempt in enumerate(receipt.get("attempts", [])):
        diagnostic = attempt.get("collision_diagnostic") or {}
        if "checked_joints" in diagnostic:
            yield index, attempt, np.asarray(diagnostic["checked_joints"], dtype=float)
            continue
        match = re.search(r"checked joints=(\[[^\]]+\])", attempt.get("error", ""))
        if match:
            yield index, attempt, np.asarray(json.loads(match.group(1)), dtype=float)


def checked_final_poses(receipt):
    """Pose-only preflight evidence has no IK solution or checked joint vector."""
    for index, attempt in enumerate(receipt.get("attempts", [])):
        diagnostic = attempt.get("collision_diagnostic") or {}
        if diagnostic.get("stage") == "final_grasp" and "checked_joints" not in diagnostic:
            yield index, attempt, np.asarray(diagnostic.get("checked_tcp"), dtype=float)


def inspect(model, receipt):
    from pxr import Usd, UsdGeom, UsdPhysics

    from isaacsim_lab.finger_collision import cooked_body_boxes
    from isaacsim_lab.phase_motion import PhaseMotionError

    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
    stage = model.stage
    initial_joints = model.robot.get_joint_positions().copy()
    initial_time = model.world.current_time
    initial_links = []
    for group in model.spheres:
        for link in group:
            prim = stage.GetPrimAtPath(model.robot.prim_path + "/" + link)
            authored = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)).T
            position, rotation = model.solver.compute_forward_kinematics(link, model.joints())
            initial_links.append({"link": link, "fk_position_m": position.tolist(),
                                  "usd_position_m": authored[:3, 3].tolist(),
                                  "position_error_m": float(np.linalg.norm(position - authored[:3, 3])),
                                  "rotation_matrix_error": float(np.linalg.norm(rotation - authored[:3, :3]))})
    obstacles = []
    for prim in Usd.PrimRange(stage.GetPrimAtPath("/World"), Usd.TraverseInstanceProxies()):
        if str(prim.GetPath()).startswith(model.robot.prim_path + "/"):
            continue
        if prim.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get():
            bounds = cache.ComputeWorldBound(prim).ComputeAlignedBox()
            obstacles.append({"path": str(prim.GetPath()), "min_m": list(bounds.GetMin()),
                              "max_m": list(bounds.GetMax())})
    mesh_points = []
    # Force current-scene cooking before sampling; keep its private provenance.
    _ = model.finger_geometry
    for number in (1, 2):
        joint = UsdPhysics.PrismaticJoint(stage.GetPrimAtPath(
            f"{model.robot.prim_path}/panda_hand/panda_finger_joint{number}"))
        body = stage.GetPrimAtPath(joint.GetBody1Rel().GetTargets()[0])
        world_from_body = np.asarray(UsdGeom.Xformable(body).ComputeLocalToWorldTransform(0)).T
        for prim in Usd.PrimRange(body, Usd.TraverseInstanceProxies()):
            if not prim.IsA(UsdGeom.Mesh) or not prim.HasAPI(UsdPhysics.CollisionAPI):
                continue
            points = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(), dtype=float)
            relative = np.linalg.inv(world_from_body) @ np.asarray(
                UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)).T
            mesh_points.append((number, str(prim.GetPath()), points @ relative[:3, :3].T + relative[:3, 3]))
    samples = []
    rigid_parts = {}
    for index, attempt, joints in checked_samples(receipt):
        if joints.shape != model.joints().shape or not np.isfinite(joints).all():
            raise ValueError(f"attempt {index} has invalid checked joints")
        hand = model.tcp(joints) @ np.linalg.inv(model.hand_from_tcp)
        diagnostic = attempt.get("collision_diagnostic") or {}
        reported_link = diagnostic.get("link")
        rigid_geometry = []
        if reported_link and reported_link != "finger":
            if reported_link not in rigid_parts:
                body = stage.GetPrimAtPath(model.robot.prim_path + "/" + reported_link)
                parts = []
                _, evidence = cooked_body_boxes(stage, body, model.config["collision_margin_m"])
                for item in evidence:
                    parts.extend((item["collider_path"], np.asarray(points))
                                 for points in item.get("body_frame_convexes_m", []))
                rigid_parts[reported_link] = parts
            position, rotation = model.solver.compute_forward_kinematics(reported_link, joints)
            for path, points in rigid_parts[reported_link]:
                world = points @ rotation.T + position
                rigid_geometry.append({"path": path, "world_min_m": world.min(0).tolist(),
                                       "lowest_vertex_world_m": world[np.argmin(world[:, 2])].tolist(),
                                       "world_max_m": world.max(0).tolist()})
        boxes = []
        for lower, upper in model.finger_boxes():
            corners = np.asarray(list(product(*zip(lower, upper))))
            world = corners @ hand[:3, :3].T + hand[:3, 3]
            boxes.append({"hand_min_m": lower.tolist(), "hand_max_m": upper.tolist(),
                          "world_min_m": world.min(0).tolist(), "world_max_m": world.max(0).tolist()})
        meshes = []
        for number, path, points in mesh_points:
            _, _, parent, child, axis, limits = next(g for g in model.finger_geometry if g[0] == number)
            for opening in limits:
                shift = np.eye(4)
                shift[axis, 3] = opening
                transform = hand @ parent @ shift @ np.linalg.inv(child)
                world = points @ transform[:3, :3].T + transform[:3, 3]
                meshes.append({"path": path, "opening_m": float(opening),
                               "world_min_m": world.min(0).tolist(), "world_max_m": world.max(0).tolist()})
        try:
            model._collisions(joints, "", False, False, np.eye(4))
            replay = {"status": "clear"}
        except PhaseMotionError as exc:
            replay = {"status": "rejected", "code": exc.code, "error": str(exc),
                      "collision_diagnostic": exc.diagnostics}
        samples.append({"attempt_index": index, "original_error": attempt.get("error"),
                        "joints": joints.tolist(), "tcp_world": model.tcp(joints).tolist(),
                        "reported_link_cooked_geometry": rigid_geometry,
                        "finger_sweep_boxes": boxes, "finger_meshes": meshes, "replay": replay})
    final_samples = []
    for index, attempt, pose in checked_final_poses(receipt):
        if pose.shape != (4, 4) or not np.isfinite(pose).all():
            raise ValueError(f"attempt {index} has invalid final-grasp pose")
        try:
            model.check_final_gripper_pose(pose, "")
            replay = {"status": "clear"}
        except PhaseMotionError as exc:
            replay = {"status": "rejected", "code": exc.code, "error": str(exc),
                      "collision_diagnostic": exc.diagnostics}
        final_samples.append({"attempt_index": index, "original_error": attempt.get("error"),
                              "tcp_world": pose.tolist(), "replay": replay})
    unchanged = bool(np.array_equal(initial_joints, model.robot.get_joint_positions()))
    return {"captured_at": datetime.now(timezone.utc).isoformat(),
            "evidence_kind": "historical_joint_geometry_diagnostic",
            "motion_authorized": False, "controller_commands": 0,
            "joints_unchanged": unchanged, "physics_time_unchanged": initial_time == model.world.current_time,
            "receipt_identity": {key: receipt.get(key) for key in (
                "candidate_ref", "observation_ref", "scene_revision", "calibration_ref")},
            "current_scene_revision": model.session.current_scene_revision(),
            "hand_from_tcp": model.hand_from_tcp.tolist(), "initial_fk_usd_comparison": initial_links,
            "finger_geometry_evidence": model.finger_geometry_evidence,
            "overlap_replay_policy": "no source-contact exemption; diagnostic only",
            "obstacle_bounds": obstacles, "samples": samples,
            "final_pose_samples": final_samples,
            "unreplayed_attempts": len(receipt.get("attempts", [])) - len(samples) - len(final_samples)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    faulthandler.dump_traceback_later(120, repeat=True)
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True})
    from isaacsim_lab.engine import LabUtopiaBackend
    from isaacsim_lab.profile import LabUtopiaProfile
    from isaacsim_lab.worker import WorkerSessionContext

    profile = LabUtopiaProfile.from_json(args.profile)
    backend = LabUtopiaBackend(profile, observation_artifact_root=args.output / "artifacts")
    context = WorkerSessionContext(app)
    try:
        print("Initializing Adapter scene and reset state", flush=True)
        result = inspect(backend._phase_motion(context), receipt)
        result["profile_path"] = str(args.profile.resolve())
        result["receipt_path"] = str(args.receipt.resolve())
        (args.output / "geometry.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps({"samples": len(result["samples"]), "output": str(args.output),
                          "joints_unchanged": result["joints_unchanged"]}), flush=True)
    finally:
        backend.close_session(context)
        context.close()
        app.close()
        faulthandler.cancel_dump_traceback_later()


if __name__ == "__main__":
    main()
