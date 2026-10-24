"""Render a paired raw-depth/ReMake comparison from one LocateAnything target.

The renderer consumes only recorded RGB-D artifacts and provider outputs. It
does not read simulator geometry and does not authorize motion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


RED = (220, 60, 50)
GREEN = (35, 160, 90)
BLUE = (42, 102, 190)
BLACK = (20, 20, 20)


def font(size: int = 20):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def colorize(values: np.ndarray, lo: float | None = None, hi: float | None = None) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    finite = np.isfinite(values)
    if lo is None:
        lo = float(np.quantile(values[finite], 0.02)) if finite.any() else 0.0
    if hi is None:
        hi = float(np.quantile(values[finite], 0.98)) if finite.any() else 1.0
    hi = max(hi, lo + 1e-6)
    x = np.nan_to_num(np.clip((values - lo) / (hi - lo), 0.0, 1.0), nan=0.0)
    stops = np.array([[35, 60, 150], [30, 170, 150], [245, 220, 65]], dtype=np.float32)
    left = np.clip(x * 2, 0, 1)
    right = np.clip((x - 0.5) * 2, 0, 1)
    first = stops[0] * (1 - left[..., None]) + stops[1] * left[..., None]
    second = stops[1] * (1 - right[..., None]) + stops[2] * right[..., None]
    result = np.where((x[..., None] <= 0.5), first, second).astype(np.uint8)
    result[~finite] = (245, 245, 245)
    return result


def panel(image: Image.Image, title: str, width: int = 640, height: int = 390) -> Image.Image:
    out = Image.new("RGB", (width, height + 42), "white")
    out.paste(image.convert("RGB").resize((width, height)), (0, 42))
    ImageDraw.Draw(out).text((10, 10), title, fill=BLACK, font=font(20))
    return out


def overlay(rgb: Image.Image, mask: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    base = rgb.convert("RGBA")
    alpha = Image.fromarray((np.asarray(mask, dtype=np.uint8) * 105), "L")
    layer = Image.new("RGBA", base.size, (*color, 0))
    layer.putalpha(alpha)
    return Image.alpha_composite(base, layer).convert("RGB")


def box_overlay(rgb: Image.Image, bbox: list[int], label: str) -> Image.Image:
    out = rgb.copy().convert("RGB")
    draw = ImageDraw.Draw(out)
    draw.rectangle(tuple(bbox), outline=RED, width=5)
    draw.text((bbox[0] + 8, max(4, bbox[1] - 26)), label, fill=RED, font=font(20))
    return out


def depth_panel(depth: np.ndarray, mask: np.ndarray, lo: float, hi: float) -> Image.Image:
    values = np.asarray(depth, dtype=np.float32).copy()
    values[~mask] = np.nan
    return Image.fromarray(colorize(values, lo, hi), "RGB")


def cloud_image(points: np.ndarray, width: int = 640, height: int = 390) -> Image.Image:
    points = np.asarray(points, dtype=np.float32)
    points = points[np.isfinite(points).all(axis=1)]
    canvas = Image.new("RGB", (width, height), "white")
    if len(points) == 0:
        ImageDraw.Draw(canvas).text((20, 170), "No finite points", fill=BLACK, font=font(22))
        return canvas
    x, z = points[:, 0], points[:, 2]
    xlo, xhi = np.quantile(x, [0.01, 0.99])
    zlo, zhi = np.quantile(z, [0.01, 0.99])
    xhi, zhi = max(xhi, xlo + 1e-6), max(zhi, zlo + 1e-6)
    px = np.clip((x - xlo) / (xhi - xlo) * (width - 1), 0, width - 1).astype(int)
    py = np.clip((1 - (z - zlo) / (zhi - zlo)) * (height - 1), 0, height - 1).astype(int)
    pixels = np.asarray(canvas).copy()
    pixels[py, px] = colorize(z, float(zlo), float(zhi))
    return Image.fromarray(pixels)


def pose_image(
    rgb: Image.Image,
    candidates: list[dict],
    intrinsics: list[list[float]],
    label: str,
    crop_origin: tuple[int, int] = (0, 0),
) -> Image.Image:
    out = rgb.copy().convert("RGB")
    draw = ImageDraw.Draw(out)
    fx, fy, cx, cy = intrinsics[0][0], intrinsics[1][1], intrinsics[0][2], intrinsics[1][2]
    ox, oy = crop_origin
    for rank, candidate in enumerate(candidates[:8], 1):
        x, y, z = candidate["position_m"]
        if z <= 0:
            continue
        u, v = fx * x / z + cx - ox, fy * y / z + cy - oy
        if not (0 <= u < out.width and 0 <= v < out.height):
            continue
        radius = 9 if rank == 1 else 6
        draw.ellipse((u - radius, v - radius, u + radius, v + radius), fill=GREEN, outline="white", width=2)
        draw.text((u + 8, v - 11), f"{rank}:{candidate['score']:.2f}", fill=BLACK, font=font(15))
        rotation = np.asarray(candidate["rotation"], dtype=np.float32)
        approach = rotation[:, 2]
        tip = np.array([x, y, z], dtype=np.float32) + 0.08 * approach
        tu, tv = fx * tip[0] / tip[2] + cx - ox, fy * tip[1] / tip[2] + cy - oy
        draw.line((u, v, tu, tv), fill=BLUE, width=3)
    draw.text((10, 10), label, fill=BLACK, font=font(18))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rgb", type=Path, required=True)
    parser.add_argument("--raw-depth", type=Path, required=True)
    parser.add_argument("--remake-depth", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--mask", type=Path, required=True)
    parser.add_argument("--bbox", type=int, nargs=4, required=True)
    parser.add_argument("--locate-response", type=Path, required=True)
    parser.add_argument("--raw-grasps", type=Path, required=True)
    parser.add_argument("--remake-grasps", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--crop-pad", type=int, default=180)
    args = parser.parse_args()

    rgb = Image.open(args.rgb).convert("RGB")
    raw = np.load(args.raw_depth, allow_pickle=False).astype(np.float32)
    remake = np.load(args.remake_depth, allow_pickle=False).astype(np.float32)
    mask = np.load(args.mask, allow_pickle=False).astype(bool)
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    locate_response = json.loads(args.locate_response.read_text(encoding="utf-8"))
    raw_grasps = json.loads(args.raw_grasps.read_text(encoding="utf-8"))
    remake_grasps = json.loads(args.remake_grasps.read_text(encoding="utf-8"))
    if raw.shape != remake.shape or raw.shape != mask.shape or tuple(rgb.size[::-1]) != raw.shape:
        raise ValueError("RGB, depth, ReMake depth, and mask dimensions do not match")

    x1, y1, x2, y2 = args.bbox
    ox, oy = max(0, x1 - args.crop_pad), max(0, y1 - args.crop_pad)
    ex, ey = min(rgb.width, x2 + args.crop_pad), min(rgb.height, y2 + args.crop_pad)
    crop = (ox, oy, ex, ey)
    rgb_view = rgb.crop(crop)
    raw_view = raw[oy:ey, ox:ex]
    remake_view = remake[oy:ey, ox:ex]
    mask_view = mask[oy:ey, ox:ex]
    valid = np.concatenate((raw_view[mask_view], remake_view[mask_view]))
    valid = valid[np.isfinite(valid) & (valid > 0)]
    lo, hi = (float(np.quantile(valid, q)) for q in (0.02, 0.98))
    intrinsics = calibration["intrinsics"]
    fx, fy, cx, cy = intrinsics[0][0], intrinsics[1][1], intrinsics[0][2], intrinsics[1][2]

    def make_cloud(depth: np.ndarray) -> np.ndarray:
        ys, xs = np.nonzero(mask & np.isfinite(depth) & (depth > 0))
        z = depth[ys, xs]
        return np.column_stack(((xs - cx) * z / fx, (ys - cy) * z / fy, z)).astype(np.float32)

    raw_cloud = make_cloud(raw)
    remake_cloud = make_cloud(remake)
    local_bbox = [x1 - ox, y1 - oy, x2 - ox, y2 - oy]
    left_rgb = box_overlay(rgb_view, local_bbox, "raw-depth baseline")
    right_rgb = box_overlay(rgb_view, local_bbox, "ReMake")
    left_seg = overlay(left_rgb, mask_view, RED)
    right_seg = overlay(right_rgb, mask_view, GREEN)
    left_pose = pose_image(rgb_view, raw_grasps.get("candidates", []), intrinsics, "GraspNet raw point cloud", (ox, oy))
    right_pose = pose_image(rgb_view, remake_grasps.get("candidates", []), intrinsics, "GraspNet ReMake point cloud", (ox, oy))

    cell_w, cell_h = 640, 432
    rows = [
        (panel(left_rgb, "RGB | no ReMake"), panel(right_rgb, "RGB | ReMake")),
        (panel(left_seg, "LocateAnything -> SAM2 mask | raw"), panel(right_seg, "LocateAnything -> SAM2 mask | ReMake")),
        (panel(depth_panel(raw_view, mask_view, lo, hi), f"Raw depth | q50={np.nanmedian(raw_view[mask_view]):.3f} m"), panel(depth_panel(remake_view, mask_view, lo, hi), f"ReMake depth | q50={np.nanmedian(remake_view[mask_view]):.3f} m")),
        (panel(cloud_image(raw_cloud), f"Raw target cloud | {len(raw_cloud):,} pts"), panel(cloud_image(remake_cloud), f"ReMake target cloud | {len(remake_cloud):,} pts")),
        (panel(left_pose, f"Raw GraspNet | {len(raw_grasps.get('candidates', []))} retained"), panel(right_pose, f"ReMake GraspNet | {len(remake_grasps.get('candidates', []))} retained")),
    ]
    canvas = Image.new("RGB", (cell_w * 2, cell_h * len(rows)), "white")
    for row, (left, right) in enumerate(rows):
        canvas.paste(left, (0, row * cell_h))
        canvas.paste(right, (cell_w, row * cell_h))
    args.out.mkdir(parents=True, exist_ok=True)
    canvas.save(args.out / "locateanything-remake-grasp-comparison.png")
    np.save(args.out / "target-mask.npy", mask, allow_pickle=False)
    np.save(args.out / "raw-target-point-cloud.npy", raw_cloud, allow_pickle=False)
    np.save(args.out / "remake-target-point-cloud.npy", remake_cloud, allow_pickle=False)
    (args.out / "locateanything-response.json").write_text(json.dumps(locate_response, indent=2), encoding="utf-8")
    summary = {
        "target_bbox_xyxy_px": list(args.bbox),
        "mask_pixels": int(mask.sum()),
        "raw": {"depth_quantiles_m": [float(x) for x in np.quantile(raw[mask], [0.05, 0.5, 0.95])], "point_count": int(len(raw_cloud)), "grasp": raw_grasps},
        "remake": {"depth_quantiles_m": [float(x) for x in np.quantile(remake[mask], [0.05, 0.5, 0.95])], "point_count": int(len(remake_cloud)), "grasp": remake_grasps},
        "comparison": {"same_rgb": True, "same_locateanything_mask": True, "shared_depth_display_range_m": [lo, hi], "motion_authorized": False},
        "dfnet": {"status": "pending_checkpoint"},
    }
    (args.out / "comparison-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
