"""Render evidence-first visual comparisons for transparent-object models.

This report renderer consumes an existing recorded capture and never consults
simulation geometry.  It intentionally renders unavailable model outputs as
unavailable instead of substituting another model's result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


PALETTE = [
    (231, 76, 60), (46, 134, 193), (39, 174, 96), (155, 89, 182),
    (243, 156, 18), (22, 160, 133), (127, 140, 141), (52, 73, 94),
]


def font(size: int = 24):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def colorize(values: np.ndarray, *, lo: float | None = None, hi: float | None = None) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    finite = np.isfinite(values)
    if lo is None:
        lo = float(np.quantile(values[finite], 0.02)) if finite.any() else 0.0
    if hi is None:
        hi = float(np.quantile(values[finite], 0.98)) if finite.any() else 1.0
    hi = max(hi, lo + 1e-6)
    x = np.nan_to_num(np.clip((values - lo) / (hi - lo), 0.0, 1.0), nan=0.0)
    # Compact blue-green-yellow map, adequate for inspection without mpl.
    stops = np.array([[32, 57, 140], [35, 170, 150], [245, 220, 70]], dtype=np.float32)
    out = np.empty((*x.shape, 3), dtype=np.uint8)
    left = np.clip(x * 2, 0, 1)
    right = np.clip((x - 0.5) * 2, 0, 1)
    first = stops[0] * (1 - left[..., None]) + stops[1] * left[..., None]
    second = stops[1] * (1 - right[..., None]) + stops[2] * right[..., None]
    out[:] = np.where((x[..., None] <= 0.5), first, second).astype(np.uint8)
    out[~finite] = (245, 245, 245)
    return out


def panel(image: Image.Image, title: str, width: int = 640, height: int = 480) -> Image.Image:
    image = image.convert("RGB").resize((width, height))
    out = Image.new("RGB", (width, height + 44), "white")
    out.paste(image, (0, 44))
    ImageDraw.Draw(out).text((12, 10), title, fill=(20, 20, 20), font=font(22))
    return out


def depth_image(
    depth: np.ndarray,
    mask: np.ndarray | None = None,
    *,
    lo: float | None = None,
    hi: float | None = None,
) -> Image.Image:
    values = depth.copy().astype(np.float32)
    if mask is not None:
        values[~mask] = np.nan
    return Image.fromarray(colorize(values, lo=lo, hi=hi), "RGB")


def overlay(rgb: Image.Image, mask: np.ndarray, color: tuple[int, int, int], alpha: int = 105) -> Image.Image:
    base = rgb.convert("RGBA")
    layer = Image.new("RGBA", base.size, (*color, 0))
    layer.putalpha(Image.fromarray((mask.astype(np.uint8) * alpha), "L"))
    layer.paste((*color, alpha), (0, 0), Image.fromarray((mask.astype(np.uint8) * alpha), "L"))
    return Image.alpha_composite(base, layer).convert("RGB")


def projection(points: np.ndarray, width: int = 640, height: int = 480) -> Image.Image:
    points = np.asarray(points, dtype=np.float32)
    if len(points) == 0:
        return Image.new("RGB", (width, height), "white")
    points = points[np.isfinite(points).all(axis=1)]
    # Camera-frame x/y top-down view; color encodes optical-axis depth.
    x, y, z = points.T
    xlo, xhi = np.quantile(x, [0.01, 0.99])
    ylo, yhi = np.quantile(y, [0.01, 0.99])
    xhi = max(xhi, xlo + 1e-6)
    yhi = max(yhi, ylo + 1e-6)
    px = np.clip((x - xlo) / (xhi - xlo) * (width - 1), 0, width - 1).astype(int)
    py = np.clip((1 - (y - ylo) / (yhi - ylo)) * (height - 1), 0, height - 1).astype(int)
    canvas = Image.new("RGB", (width, height), "white")
    pix = np.asarray(canvas).copy()
    colors = colorize(z)
    pix[py, px] = colors
    return Image.fromarray(pix)


def cloud_pair(left: np.ndarray, right: np.ndarray, width: int = 640, height: int = 480) -> Image.Image:
    left = np.asarray(left, dtype=np.float32)
    right = np.asarray(right, dtype=np.float32)
    left = left[np.isfinite(left).all(axis=1)]
    right = right[np.isfinite(right).all(axis=1)]
    joined = np.concatenate((left, right))
    xlo, xhi = np.quantile(joined[:, 0], [0.01, 0.99])
    zlo, zhi = np.quantile(joined[:, 2], [0.01, 0.99])
    xhi, zhi = max(xhi, xlo + 1e-6), max(zhi, zlo + 1e-6)

    def draw_cloud(points: np.ndarray, canvas: Image.Image, x0: int) -> None:
        if not len(points):
            return
        px = np.clip((points[:, 0] - xlo) / (xhi - xlo) * (width // 2 - 1), 0, width // 2 - 1).astype(int)
        py = np.clip((1 - (points[:, 2] - zlo) / (zhi - zlo)) * (height - 1), 0, height - 1).astype(int)
        pix = np.asarray(canvas).copy()
        pix[py, px + x0] = colorize(points[:, 2], lo=float(zlo), hi=float(zhi))
        canvas.paste(Image.fromarray(pix))

    canvas = Image.new("RGB", (width, height), "white")
    draw_cloud(left, canvas, 0)
    draw_cloud(right, canvas, width // 2)
    draw = ImageDraw.Draw(canvas)
    draw.line((width // 2, 0, width // 2, height), fill=(190, 190, 190), width=2)
    draw.text((12, 10), "Raw mask cloud", fill=(20, 20, 20), font=font(18))
    draw.text((width // 2 + 12, 10), "ReMake mask cloud", fill=(20, 20, 20), font=font(18))
    return canvas


def raw_mask_cloud(mask: np.ndarray, depth: np.ndarray, intrinsics: list[list[float]]) -> np.ndarray:
    ys, xs = np.nonzero(mask & np.isfinite(depth) & (depth > 0))
    z = depth[ys, xs]
    fx, fy = intrinsics[0][0], intrinsics[1][1]
    cx, cy = intrinsics[0][2], intrinsics[1][2]
    x = (xs - cx) * z / fx
    y = (ys - cy) * z / fy
    return np.column_stack((x, y, z)).astype(np.float32)


def crop_with_padding(image: Image.Image, bbox: list[int], pad: int = 50) -> tuple[Image.Image, tuple[int, int]]:
    x1, y1, x2, y2 = bbox
    left, top = max(0, x1 - pad), max(0, y1 - pad)
    right, bottom = min(image.width, x2 + pad), min(image.height, y2 + pad)
    return image.crop((left, top, right, bottom)), (left, top)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--target-index", type=int, default=7)
    args = parser.parse_args()
    report = json.loads((args.run / "perception.json").read_text(encoding="utf-8"))
    root = args.run / "artifacts" / "labutopia"
    capture = report["capture"]
    rgb_ref = next(x["ref"] for x in capture["artifacts"] if x["kind"] == "rgb")
    depth_ref = next(x["ref"] for x in capture["artifacts"] if x["kind"] == "depth")
    rgb = Image.open(root / rgb_ref.split("artifact://labutopia/", 1)[1]).convert("RGB")
    raw_depth = np.load(root / depth_ref.split("artifact://labutopia/", 1)[1], allow_pickle=False)
    recovered_path = next((root / "recovered-depth").glob("*.npy"))
    recovered = np.load(recovered_path, allow_pickle=False)
    derived = report["understanding"]["derived_artifacts"]
    masks = [a for a in derived if a["kind"] == "instance_mask"]
    clouds = [a for a in derived if a["kind"] == "object_point_cloud"]
    target_entity = report["understanding"]["entities"][args.target_index]
    target_ref = target_entity["entity_ref"]
    target_mask_meta = next(a for a in masks if a["entity_ref"] == target_ref)
    target_cloud_meta = next(a for a in clouds if a["entity_ref"] == target_ref)
    target_mask = np.load(root / target_mask_meta["artifact_ref"].split("artifact://labutopia/", 1)[1], allow_pickle=False)
    target_cloud = np.load(root / target_cloud_meta["artifact_ref"].split("artifact://labutopia/", 1)[1], allow_pickle=False)
    bbox = target_mask_meta["descriptor"]["bbox_xyxy_px"]
    target_rgb, (ox, oy) = crop_with_padding(rgb, bbox)
    target_mask_crop = target_mask[oy:oy + target_rgb.height, ox:ox + target_rgb.width]
    raw_crop = raw_depth[oy:oy + target_rgb.height, ox:ox + target_rgb.width]
    recovered_crop = recovered[oy:oy + target_rgb.height, ox:ox + target_rgb.width]
    target_overlay = overlay(target_rgb, target_mask_crop, PALETTE[0])
    valid_pair = np.concatenate((raw_crop[target_mask_crop], recovered_crop[target_mask_crop]))
    valid_pair = valid_pair[np.isfinite(valid_pair)]
    depth_range = tuple(float(x) for x in np.quantile(valid_pair, [0.02, 0.98]))
    raw_panel = depth_image(raw_crop, target_mask_crop, lo=depth_range[0], hi=depth_range[1])
    remake_panel = depth_image(recovered_crop, target_mask_crop, lo=depth_range[0], hi=depth_range[1])
    diff = recovered_crop - raw_crop
    diff[~target_mask_crop] = np.nan
    diff_panel = depth_image(diff, target_mask_crop)
    candidates = [c for c in report["grasp"]["candidates"] if c["entity_ref"] == target_ref]
    candidates = sorted(candidates, key=lambda c: c["score"], reverse=True)
    candidate_view = target_overlay.copy()
    draw = ImageDraw.Draw(candidate_view)
    calibration = json.loads(next((root / "calibration").glob("*.json")).read_text(encoding="utf-8"))
    fx, fy = calibration["intrinsics"][0][0], calibration["intrinsics"][1][1]
    cx, cy = calibration["intrinsics"][0][2], calibration["intrinsics"][1][2]
    for rank, candidate in enumerate(candidates[:1], 1):
        x, y, z = candidate["grasp_frame"]["position_m"]
        if z <= 0:
            continue
        u, v = fx * x / z + cx - ox, fy * y / z + cy - oy
        if 0 <= u < candidate_view.width and 0 <= v < candidate_view.height:
            r = 10 if rank == 1 else 7
            draw.ellipse((u - r, v - r, u + r, v + r), fill=PALETTE[rank % len(PALETTE)], outline="white", width=2)
            draw.text((u + 8, v - 12), f"{rank}:{candidate['score']:.2f}", fill=(0, 0, 0), font=font(16))
    calibration_data = json.loads(next((root / "calibration").glob("*.json")).read_text(encoding="utf-8"))
    raw_cloud_target = raw_mask_cloud(target_mask, raw_depth, calibration_data["intrinsics"])
    unavailable = Image.new("RGB", (640, 480), (242, 242, 242))
    unavailable_draw = ImageDraw.Draw(unavailable)
    if candidates:
        unavailable_draw.text((28, 165), f"GraspNet: {len(candidates)} target candidates", fill=(40, 40, 40), font=font(24))
        unavailable_draw.text((28, 210), f"Top score {candidates[0]['score']:.3f}", fill=(80, 80, 80), font=font(18))
    else:
        unavailable_draw.text((28, 165), "GraspNet: no target candidates", fill=(40, 40, 40), font=font(24))
        unavailable_draw.text((28, 210), "Mixing vessel is excluded as a grasp source", fill=(80, 80, 80), font=font(18))
    target_strip = Image.new("RGB", (1280, 4 * 524), "white")
    tiles = [
        panel(target_overlay, "Target RGB + instance mask"),
        panel(raw_panel, "Raw depth baseline in target mask"),
        panel(remake_panel, "ReMake recovered depth in target mask"),
        panel(diff_panel, "Recovered minus raw depth (diagnostic)"),
        panel(cloud_pair(raw_cloud_target, target_cloud), "Raw vs ReMake target cloud (shared camera x/z scale)"),
        panel(candidate_view, "ReMake GraspNet top-scoring candidate projection"),
        panel(unavailable, "Candidate status for this target"),
        panel(Image.new("RGB", (640, 480), "white"), ""),
    ]
    for i, tile in enumerate(tiles):
        target_strip.paste(tile, ((i % 2) * 640, (i // 2) * 524))
    args.out.mkdir(parents=True, exist_ok=True)
    target_strip.save(args.out / "target-conical-flask-comparison.png")

    all_mask = np.zeros((rgb.height, rgb.width), dtype=bool)
    colored = rgb.copy()
    for index, meta in enumerate(masks):
        mask = np.load(root / meta["artifact_ref"].split("artifact://labutopia/", 1)[1], allow_pickle=False)
        all_mask |= mask
        colored = overlay(colored, mask, PALETTE[index % len(PALETTE)], 60)
    raw_all = depth_image(raw_depth, all_mask)
    remake_all = depth_image(recovered, all_mask)
    transparent_meta = next((root / "transparent-mask").glob("*.npy"), None)
    transparent_mask = (
        np.load(transparent_meta, allow_pickle=False)
        if transparent_meta is not None
        else np.zeros_like(all_mask)
    )
    transparent = Image.fromarray((transparent_mask.astype(np.uint8) * 255), "L").convert("RGB")
    raw_cloud_ref = next(x["ref"] for x in capture["artifacts"] if x["kind"] == "point_cloud")
    raw_cloud = np.load(root / raw_cloud_ref.split("artifact://labutopia/", 1)[1], allow_pickle=False)
    recovered_cloud = np.concatenate([
        np.load(root / a["artifact_ref"].split("artifact://labutopia/", 1)[1], allow_pickle=False)
        for a in clouds
    ])
    overview = Image.new("RGB", (1280, 3 * 524), "white")
    overview_tiles = [
        panel(colored, "Panorama: RGB + all instance masks"),
        panel(raw_all, "Panorama: raw depth in masks"),
        panel(remake_all, "Panorama: ReMake depth in masks"),
        panel(transparent, "Geometry input mask: union of all instances"),
        panel(projection(raw_cloud[:: max(1, len(raw_cloud) // 120000)]), "Raw full point cloud projection"),
        panel(projection(recovered_cloud), "ReMake recovered object-cloud projection"),
    ]
    for i, tile in enumerate(overview_tiles):
        overview.paste(tile, ((i % 2) * 640, (i // 2) * 524))
    overview.save(args.out / "panorama-model-comparison.png")
    (args.out / "target-summary.json").write_text(json.dumps({
        "target_index": args.target_index,
        "entity": target_entity,
        "bbox_xyxy_px": bbox,
        "mask_pixels": int(target_mask.sum()),
        "point_count": int(len(target_cloud)),
        "candidate_count": len(candidates),
        "top_candidates": candidates[:8],
        "candidate_status": (
            "available_for_target" if candidates
            else "no candidates: mixing_vessel is excluded as a grasp source in the replay probe"
        ),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
