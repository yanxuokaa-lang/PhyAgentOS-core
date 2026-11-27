"""Replay measured Grounding geometry and mask-edge evidence without motion."""

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from robotwin20_adapter.grounding import Grounding
from robotwin20_adapter.observed_binding import rigid_transform
from robotwin20_adapter.observed_support import SupportEstimationPolicy, estimate_support
from robotwin20_adapter.route_evidence import _artifact_path


def diagnose(source: Path) -> dict:
    understanding = json.loads((source / "understanding.json").read_text())
    observation = json.loads((source / "capture.stdout").read_text())
    root = source / "artifacts"

    def read_array(ref):
        return np.load(_artifact_path(root, ref + ".npy"), allow_pickle=False)

    calibration = json.loads(_artifact_path(root, observation["calibration_ref"]).read_text())
    transform = np.linalg.inv(rigid_transform(calibration["extrinsic_cv"]))
    rotation = transform[:3, :3]
    derived = understanding["derived_artifacts"]
    depth_ref = next(item["ref"] for item in observation["artifacts"] if item["kind"] == "depth")
    depth = read_array(depth_ref)
    # This capture identifies its observed table as e4. The original semantic
    # relation supplies the support identity; no simulator extents are read.
    support_refs = {
        item["object_ref"]
        for item in understanding.get("relations", [])
        if item.get("predicate") in {"on", "is_on"}
    }
    if len(support_refs) != 1:
        raise ValueError("diagnostic requires one observed semantic support")
    support_ref = support_refs.pop()
    table_cloud = next(
        item
        for item in derived
        if item["kind"] == "object_point_cloud" and item["entity_ref"] == support_ref
    )
    table = read_array(table_cloud["artifact_ref"])
    table = table @ rotation.T + transform[:3, 3]
    policy = SupportEstimationPolicy()
    support = estimate_support(table, table_cloud["artifact_ref"], policy)
    height = support["estimation"]["height_m"]
    # Only the production projection method is exercised. This object owns no
    # worker client and cannot issue a snapshot, simulation or Action call.
    grounding = object.__new__(Grounding)
    grounding.root = root
    rows = []
    for envelope in understanding["spatial_envelopes"]:
        entity_ref = envelope["entity_ref"]
        if entity_ref == support_ref:
            continue
        cloud = next(
            item
            for item in derived
            if item["kind"] == "object_point_cloud" and item["entity_ref"] == entity_ref
        )
        geometry = [
            item
            for item in derived
            if item["kind"] == "object_geometry" and item["entity_ref"] == entity_ref
        ]
        points = read_array(cloud["artifact_ref"])
        world = points @ rotation.T + transform[:3, 3]
        low, high = np.array(envelope["min_xyz_m"]), np.array(envelope["max_xyz_m"])
        cloud_low, cloud_high = points.min(0), points.max(0)
        dimensions = np.array(geometry[0]["descriptor"]["dimensions_m"]) if geometry else high - low
        padding = np.maximum.reduce(
            [
                np.zeros(3),
                cloud_low - low,
                high - cloud_high,
                (dimensions - (cloud_high - cloud_low)) / 2,
            ]
        )
        world_padding = np.abs(rotation) @ padding
        model = grounding._project_visual_geometry(
            [entity_ref],
            {entity_ref: {"entity_ref": "identity-only", "actor_name": "unused"}},
            understanding,
            transform,
        )[entity_ref]
        pose = rigid_transform(model["world_T_object"])
        mask_ref = next(
            item["artifact_ref"]
            for item in derived
            if item["kind"] == "instance_mask" and item["entity_ref"] == entity_ref
        )
        mask = read_array(mask_ref).astype(bool)
        ys, xs = np.nonzero(mask)
        valid = np.isfinite(depth[ys, xs]) & (depth[ys, xs] > 0)
        ys, xs = ys[valid], xs[valid]
        # Pixel order is the original capture's mask/depth construction order.
        # Verify the association before attributing an extreme point to a pixel.
        intrinsic = np.asarray(calibration["intrinsic_cv"])
        z = depth[ys, xs] * 0.001
        reconstructed = np.c_[
            (xs - intrinsic[0, 2]) * z / intrinsic[0, 0],
            (ys - intrinsic[1, 2]) * z / intrinsic[1, 1],
            z,
        ]
        if points.shape != reconstructed.shape or not np.allclose(points, reconstructed, atol=1e-6):
            raise ValueError("saved cloud is not in original valid-mask pixel order")
        extreme = int(world[:, 1].argmax())
        x, y = int(xs[extreme]), int(ys[extreme])
        table_band = np.abs(world[:, 2] - height) <= policy.inlier_distance_m
        top = world[world[:, 2] >= world[:, 2].max() - policy.inlier_distance_m]
        rows.append(
            {
                "entity_ref": entity_ref,
                "cloud_ref": cloud["artifact_ref"],
                "mask_ref": mask_ref,
                "geometry_records": geometry,
                "point_count": len(points),
                "mask_valid_count": len(xs),
                "transformed_camera_AABB_dimensions_m": (np.abs(rotation) @ (high - low)).tolist(),
                "direct_world_cloud_dimensions_m": np.ptp(world, axis=0).tolist(),
                "world_padding_m": world_padding.tolist(),
                "actual_production_world_dimensions_m": (
                    np.abs(pose[:3, :3]) @ (2 * np.array(model["half_extents_m"]))
                ).tolist(),
                "actual_model_frame": model["object_frame_id"],
                "actual_rotation": pose[:3, :3].tolist(),
                "top_band_point_count": len(top),
                "top_band_xy_dimensions_m": np.ptp(top[:, :2], axis=0).tolist(),
                "max_y_pixel": {
                    "index": extreme,
                    "pixel_xy": [x, y],
                    "depth_mm": float(depth[y, x]),
                    "world_point": world[extreme].tolist(),
                    "distance_to_table_m": float(world[extreme, 2] - height),
                },
                "depth_3x3_mm": depth[max(0, y - 1) : y + 2, max(0, x - 1) : x + 2].tolist(),
                "mask_3x3": mask[max(0, y - 1) : y + 2, max(0, x - 1) : x + 2].astype(int).tolist(),
                "diagnostic_not_production": {
                    "table_band_count": int(table_band.sum()),
                    "outside_table_band_dimensions_m": np.ptp(world[~table_band], axis=0).tolist(),
                    "warning": "Classification also removes real object bottom edges; no source cloud is edited.",
                },
            }
        )
    return {
        "analysis_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source": str(source.resolve()),
        "captured_at": observation["captured_at"],
        **{
            key: observation[key]
            for key in ("observation_ref", "scene_revision", "calibration_ref")
        },
        "depth_ref": depth_ref,
        "support_cloud_ref": table_cloud["artifact_ref"],
        "mode": "offline_saved_capture",
        "current_scene_claim": False,
        "motion_started": False,
        "new_perception_run": False,
        "calibration_world_T_camera": transform.tolist(),
        "observed_support_fit": support,
        "entities": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Original capture directory")
    parser.add_argument("--output", required=True, type=Path, help="New diagnostic JSON path")
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.source.resolve()):
        parser.error("output must be outside the original capture directory")
    result = diagnose(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(f"Measured {len(result['entities'])} objects; no motion; output: {args.output}")


if __name__ == "__main__":
    main()
