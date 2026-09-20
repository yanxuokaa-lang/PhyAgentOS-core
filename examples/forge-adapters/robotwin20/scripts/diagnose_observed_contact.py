"""Sensor-only attribution of support ambiguity and local visible contact geometry.

This offline diagnostic never changes masks, geometry or route acceptance. It
reads saved observation/candidate artifacts and the observed support policy.
Simulator state.json and private actor geometry are not used.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import numpy as np

from robotwin20_adapter.grasp_postprocessing import _quaternion_rotation, derive_robot_hand_pose
from robotwin20_adapter.observed_binding import rigid_transform
from robotwin20_adapter.observed_support import SupportEstimationPolicy, estimate_support
from robotwin20_adapter.route_evidence import _artifact_path


def bounds(points):
    if len(points) == 0:
        return {"count": 0, "min_m": None, "max_m": None, "span_m": None}
    low, high = points.min(axis=0), points.max(axis=0)
    return {"count": len(points), "min_m": low.tolist(), "max_m": high.tolist(), "span_m": (high - low).tolist()}


def aligned_cloud(mask, depth, intrinsic, cloud, depth_scale):
    """Require exact pixel ordering; do not guess correspondence after subsampling."""
    if mask.shape != depth.shape or mask.ndim != 2:
        raise ValueError("mask and depth shapes differ")
    ys, xs = np.nonzero(mask)
    z = depth[ys, xs] * depth_scale
    valid = np.isfinite(z) & (z > 0)
    xs, ys, z = xs[valid], ys[valid], z[valid]
    k = np.asarray(intrinsic, dtype=float)
    if k.shape != (3, 3) or not np.isfinite(k).all() or k[0, 0] <= 0 or k[1, 1] <= 0:
        raise ValueError("invalid camera intrinsics")
    expected = np.stack(((xs - k[0, 2]) * z / k[0, 0], (ys - k[1, 2]) * z / k[1, 1], z), axis=1)
    if expected.shape != cloud.shape or not np.isfinite(cloud).all() or len(cloud) == 0:
        raise ValueError("point cloud is empty, invalid or subsampled; pixel attribution unavailable")
    residual = float(np.abs(expected - cloud).max())
    if residual > 1e-6:
        raise ValueError("saved cloud does not match mask/depth/calibration ordering")
    return ys, xs, residual


def adjacent(mask):
    """Eight-neighbor adjacency with no wraparound across image edges."""
    padded = np.pad(mask.astype(bool), 1)
    return np.logical_or.reduce([padded[y:y + mask.shape[0], x:x + mask.shape[1]]
                                 for y, x in product(range(3), repeat=2) if (y, x) != (1, 1)])


def local_visible_geometry(world, hand, contact, radii):
    rotation = np.asarray(_quaternion_rotation(hand["orientation_xyzw"], "hand orientation"))
    points = (world - hand["position_m"]) @ rotation
    center = (np.asarray(contact) - hand["position_m"]) @ rotation
    neighborhoods = []
    for radius in radii:
        selected = np.all(np.abs(points[:, [0, 2]] - center[[0, 2]]) <= radius, axis=1)
        subset = points[selected]
        neighborhoods.append({"half_span_xz_m": radius, **bounds(subset),
                              "closing_width_m": float(np.ptp(subset[:, 1])) if len(subset) else None})
    return {"all_visible_hand_bounds": bounds(points), "neighborhoods": neighborhoods,
            "nearest_visible_point_m": float(np.linalg.norm(world - contact, axis=1).min())}


def diagnose(args):
    from PIL import Image, ImageDraw

    root = args.replay_root.resolve()
    info = json.loads((root / "replay.json").read_text())
    binding = json.loads(_artifact_path(root, info["binding_ref"]).read_text())
    calibration_path = _artifact_path(root, binding["calibration_ref"])
    capture = calibration_path.parent
    calibration = json.loads(calibration_path.read_text())
    if calibration["camera_name"] != binding["frame_id"]:
        raise ValueError("calibration frame differs from observed binding")
    transform = rigid_transform(binding["world_T_observation"])
    extrinsic = np.eye(4)
    matrix = np.asarray(calibration["extrinsic_cv"])
    extrinsic[:matrix.shape[0], :] = matrix
    if not np.allclose(np.linalg.inv(extrinsic), transform, atol=1e-6, rtol=0):
        raise ValueError("calibration differs from binding")
    depth = np.load(capture / "depth.npy", allow_pickle=False)
    rgb = np.asarray(Image.open(capture / "rgb.png").convert("RGB"))
    loaded = {}
    for label, stem in (("object", args.object_stem), ("support", args.support_stem)):
        if Path(stem).name != stem:
            raise ValueError("artifact stem must be a filename component")
        mask = np.load(capture / f"derived/mask-{stem}.npy", allow_pickle=False).astype(bool)
        cloud = np.load(capture / f"derived/points-{stem}.npy", allow_pickle=False)
        identity = json.loads((capture / f"derived/localization-{stem}.json").read_text())
        if identity["frame_id"] != binding["frame_id"] or identity["unit"] != "m":
            raise ValueError("localization frame or unit differs")
        ys, xs, residual = aligned_cloud(mask, depth, calibration["intrinsic_cv"], cloud, args.depth_scale)
        world = cloud @ transform[:3, :3].T + transform[:3, 3]
        loaded[label] = dict(mask=mask, world=world, ys=ys, xs=xs, identity=identity, residual=residual)
    obj, support = loaded["object"], loaded["support"]
    entity = obj["identity"]["entity_ref"]
    if entity not in binding["objects"] or entity == support["identity"]["entity_ref"]:
        raise ValueError("object/support identities are invalid for binding")
    facts_path = next((root / "preparation-builds").glob("*/scene-facts.json"))
    # Read only observed support policy; private actor facts are never consumed.
    policy_data = json.loads(facts_path.read_text())["support_surface"]["estimation"]["policy"]
    policy = SupportEstimationPolicy(**policy_data)
    estimated = estimate_support(support["world"], str(capture / f"derived/points-{args.support_stem}.npy"), policy)
    height = estimated["estimation"]["height_m"]
    near = np.abs(obj["world"][:, 2] - height) <= policy.inlier_distance_m
    support_inliers = np.abs(support["world"][:, 2] - height) <= policy.inlier_distance_m
    inlier_mask = np.zeros(depth.shape, dtype=bool)
    inlier_mask[support["ys"][support_inliers], support["xs"][support_inliers]] = True
    neighbor = adjacent(inlier_mask)[obj["ys"], obj["xs"]]
    groups = {"all": np.ones(len(near), dtype=bool), "near_support": near, "above_support_band": obj["world"][:, 2] > height + policy.inlier_distance_m,
              "below_support_band": obj["world"][:, 2] < height - policy.inlier_distance_m}
    summary = {name: {**bounds(obj["world"][selection]),
                     "median_rgb": np.median(rgb[obj["ys"][selection], obj["xs"][selection]], axis=0).tolist() if selection.any() else None,
                     "adjacent_support_inlier_pixels": int((neighbor & selection).sum())}
               for name, selection in groups.items()}
    bundle = json.loads((root / "bundle.json").read_text())["base_request"]
    if bundle["scene_revision"] != binding["scene_revision"]:
        raise ValueError("candidate scene differs from binding")
    diagnostic_root = args.qualification_root / "preparation-builds/contact-qualification"
    qualifications = {}
    for path in diagnostic_root.glob("contact-*.json"):
        value = json.loads(path.read_text())
        if value["scene_revision"] != binding["scene_revision"]:
            raise ValueError("qualification scene differs")
        qualifications[value["candidate_ref"]] = value
    candidate_results = []
    counts = Counter()
    for candidate in bundle["candidates"]:
        if candidate["entity_ref"] != entity:
            continue
        grasp = candidate["execution_grasp"]
        adaptation = json.loads(_artifact_path(root, grasp["adaptation_provenance_ref"]).read_text())
        hand = derive_robot_hand_pose(grasp["robot_target_pose"], reference_distance_m=adaptation["robot_target_reference_distance_m"],
                                     gripper_bias_m=adaptation["robot_gripper_bias_m"], delta_matrix=adaptation["robot_delta_matrix"])
        qualification = qualifications[candidate["candidate_ref"]]
        for arm in qualification["arm_attempts"]:
            for variant in arm["qualification"]["variants"]:
                delta = np.asarray(variant["robot_target_position_m"]) - grasp["robot_target_pose"]["position_m"]
                moved_hand = {**hand, "position_m": (np.asarray(hand["position_m"]) + delta).tolist()}
                local = local_visible_geometry(obj["world"], moved_hand, variant["contact_center_position_m"], args.local_half_spans)
                local_above = local_visible_geometry(obj["world"][groups["above_support_band"]], moved_hand, variant["contact_center_position_m"], args.local_half_spans) if groups["above_support_band"].any() else None
                counts.update(variant["rejection_reasons"])
                candidate_results.append({"candidate_ref": candidate["candidate_ref"], "arm_id": arm["arm_id"],
                    "backoff_m": variant["backoff_m"], "visible_all": local, "above_support_band_diagnostic_only": local_above,
                    "original_qualification": variant})
    if not candidate_results:
        raise ValueError("no matching candidate qualification records")
    output = Path(tempfile.mkdtemp(prefix="observed-contact-diagnosis-", dir=args.output_parent))
    result = {"created_at": datetime.now(timezone.utc).isoformat(), "command": sys.argv,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source": str(Path(__file__).resolve()), "source_code": Path(__file__).read_text(),
        "replay_root": str(root), "qualification_root": str(args.qualification_root.resolve()),
        "observation": {k: binding[k] for k in ("observation_ref", "scene_revision", "calibration_ref")},
        "entity_ref": entity, "support_entity_ref": support["identity"]["entity_ref"],
        "parameters": {"depth_scale": args.depth_scale, "local_half_spans": args.local_half_spans, "support_policy": policy_data},
        "cloud_alignment_max_error_m": {k: v["residual"] for k, v in loaded.items()},
        "mask_overlap_pixels": int((obj["mask"] & support["mask"]).sum()),
        "support_estimation": estimated["estimation"], "point_groups": summary,
        "support_median_rgb": np.median(rgb[support["ys"][support_inliers], support["xs"][support_inliers]], axis=0).tolist(),
        "original_rejection_counts": dict(counts), "candidate_variants": candidate_results,
        "motion_authorized": False, "geometry_modified": False, "gateway_calls": 0, "simulator_steps": 0,
        "limits": "Single-view local width is not full object extent, opposing contact evidence, force closure or collision admission. Near-plane pixels remain ambiguous; none are removed."}
    (output / "diagnosis.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    panels = []
    for selection, title in ((np.ones(len(near), bool), "Object mask: cyan"), (near, "Near support plane: magenta")):
        pixels = rgb.copy()
        pixels[obj["ys"][selection], obj["xs"][selection]] = [0, 255, 255] if title.startswith("Object") else [255, 0, 255]
        panel = Image.new("RGB", (rgb.shape[1], rgb.shape[0] + 24), "white")
        panel.paste(Image.fromarray(pixels), (0, 24))
        ImageDraw.Draw(panel).text((4, 5), title, fill="black")
        panels.append(panel)
    original = Image.new("RGB", panels[0].size, "white")
    original.paste(Image.fromarray(rgb), (0, 24))
    ImageDraw.Draw(original).text((4, 5), "Original observed RGB", fill="black")
    canvas = Image.new("RGB", (panels[0].width * 3, panels[0].height))
    for index, panel in enumerate([original, *panels]):
        canvas.paste(panel, (index * panel.width, 0))
    canvas.save(output / "sensor-attribution.png")
    print(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--object-stem", required=True)
    parser.add_argument("--support-stem", required=True)
    parser.add_argument("--depth-scale", type=float, required=True)
    parser.add_argument("--local-half-spans", type=float, nargs="+", default=[.005, .01, .02])
    parser.add_argument("--output-parent", type=Path, required=True)
    args = parser.parse_args()
    if not all(np.isfinite(x) and x > 0 for x in [args.depth_scale, *args.local_half_spans]):
        parser.error("scale and neighborhood spans must be finite and positive")
    diagnose(args)


if __name__ == "__main__":
    main()
