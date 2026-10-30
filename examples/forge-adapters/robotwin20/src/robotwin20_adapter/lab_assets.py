"""Generate labelled, open-container lab assets without loading a simulator.

The layout is in a table-top design frame. It must be bound to a calibrated
scene and checked by the existing planner before any manipulation.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path


def open_container_mesh(path: Path, *, radius: float, height: float, wall: float, segments: int = 32):
    """Closed wall/bottom mesh with a genuinely open mouth, in metres and Z-up."""
    vertices = []
    for r, z in ((radius, 0), (radius, height), (radius - wall, height), (radius - wall, wall)):
        vertices.extend((r * math.cos(2 * math.pi * i / segments),
                         r * math.sin(2 * math.pi * i / segments), z) for i in range(segments))
    faces = []
    for ring in range(3):
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((ring * segments + i + 1, ring * segments + j + 1,
                          (ring + 1) * segments + j + 1, (ring + 1) * segments + i + 1))
    # Interior floor and exterior underside; no polygon spans the mouth.
    vertices.extend(((0, 0, wall), (0, 0, 0)))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((4 * segments + 1, 3 * segments + i + 1, 3 * segments + j + 1))
        faces.append((4 * segments + 2, j + 1, i + 1))
    lines = ["# Procedural lab asset; units=m; local +Z is mouth axis"]
    lines += ["v " + " ".join(f"{v:.8f}" for v in vertex) for vertex in vertices]
    lines += ["f " + " ".join(map(str, face)) for face in faces]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def container_collision(radius, height, wall, segments=24):
    """Compound convex boxes retain the inner void instead of sealing the mouth."""
    parts = [{"shape": "cylinder", "axis": "z", "center_m": [0, 0, wall / 2],
              "radius_m": radius - wall, "half_length_m": wall / 2}]
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        center_radius = radius - wall / 2
        parts.append({"shape": "box", "center_m": [center_radius * math.cos(angle),
                                                       center_radius * math.sin(angle), height / 2],
                      "half_extents_m": [wall / 2, radius * math.tan(math.pi / segments), height / 2],
                      "yaw_rad": angle})
    return parts


def label_mesh(path: Path, width: float, height: float, radius: float):
    """Curved UV decal on the bottle wall, facing local -Y; no collision geometry."""
    lines, faces = [], []
    segments = 16
    for i in range(segments + 1):
        u = i / segments
        angle = (u - 0.5) * width / radius
        x, y = radius * math.sin(angle), -radius * math.cos(angle)
        for z in (-height / 2, height / 2):
            lines.append(f"v {x:.8f} {y:.8f} {z:.8f}")
        lines.extend((f"vt {u:.8f} 0", f"vt {u:.8f} 1"))
    for i in range(segments):
        a, b, c, d = 2*i+1, 2*i+3, 2*i+4, 2*i+2
        faces.extend((f"f {a}/{a} {b}/{b} {c}/{c}", f"f {a}/{a} {c}/{c} {d}/{d}"))
    path.write_text("\n".join(lines + faces) + "\n", encoding="utf-8")


def generate(config: dict, output: Path, *, seed: int) -> dict:
    from PIL import Image, ImageDraw, ImageFont

    labels = config["reagent_labels"]
    if not 2 <= len(labels) <= 8 or len(set(labels)) != len(labels):
        raise ValueError("use two to eight distinct reagent labels for the configured bottle slots")
    if any(not isinstance(label, str) or not label.isascii() or not label.isalnum() or len(label) > 8 for label in labels):
        raise ValueError("this label font profile supports 1-8 ASCII letters/digits; configure a new font profile for other scripts")
    output.mkdir(parents=True, exist_ok=True)
    label_dir = output / "labels"
    label_dir.mkdir(exist_ok=True)
    label_mesh(output / "label.obj", 0.045, 0.0225, 0.0282)
    font_path = Path(config["font_path"])
    title_font = ImageFont.truetype(str(font_path), 38)
    identity_font = ImageFont.truetype(str(font_path), 130)
    order = list(labels)
    random.Random(seed).shuffle(order)
    actors = []
    for index, label in enumerate(order):
        image = Image.new("RGB", (512, 256), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((5, 5, 506, 250), outline="black", width=5)
        draw.text((256, 40), "REAGENT", fill="black", font=title_font, anchor="mm")
        # Fit longer labels while keeping physical label dimensions identical.
        font = identity_font
        while draw.textbbox((0, 0), label, font=font)[2] > 460:
            font = ImageFont.truetype(str(font_path), font.size - 2)
        draw.text((256, 156), label, fill="black", font=font, anchor="mm")
        texture = f"labels/bottle-{index}.png"
        image.save(output / texture)
        actors.append({
            "actor_id": f"bottle-{index}", "kind": "reagent_bottle", "label": label,
            "position_m": [[-0.27, -0.09, 0.09, 0.27][index % 4], 0.12 + 0.14 * (index // 4), 0],
            "mesh": "bottle.obj", "collision": "bottle-collision.json", "fixed": False,
            "label_texture": texture, "label_mesh": "label.obj", "label_size_m": [0.045, 0.0225],
            "label_height_m": 0.065, "label_yaws_rad": [0, 2 * math.pi / 3, 4 * math.pi / 3],
            "functional_points_m": {"mouth": [0, 0, 0.12]},
        })
    actors.extend([
        {"actor_id": "beaker", "kind": "beaker", "position_m": [0, -0.13, 0.012],
         "mesh": "beaker.obj", "collision": "beaker-collision.json", "fixed": True,
         "functional_points_m": {"mouth": [0, 0, 0.10], "interior": [0, 0, 0.045]}},
        {"actor_id": "beaker-holder", "kind": "holder", "position_m": [0, -0.13, 0],
         "shape": "box", "size_m": [0.13, 0.13, 0.012], "fixed": True},
        {"actor_id": "stir-rod", "kind": "handled_rod", "position_m": [0.18, -0.13, 0.015],
         "shaft_radius_m": 0.004, "shaft_length_m": 0.12,
         "handle_radius_m": 0.012, "handle_length_m": 0.06, "fixed": False,
         "functional_points_m": {"tip": [0, 0, 0], "grip": [0, 0, 0.15]}},
        {"actor_id": "rod-stand", "kind": "stand", "position_m": [0.18, -0.13, 0],
         "shape": "box", "size_m": [0.06, 0.06, 0.015], "fixed": True},
    ])
    distractors = [(-0.30, -0.20), (-0.18, -0.09), (0.30, -0.20), (-0.30, 0.01), (0.30, 0.01)]
    for i, (x, y) in enumerate(distractors):
        actors.append({"actor_id": f"utensil-{i}", "kind": "distractor_container",
                       "position_m": [x, y, 0], "mesh": "bottle.obj", "collision": "bottle-collision.json",
                       "fixed": False})
    blocked = config.get("blocked_label")
    if blocked is not None:
        bottle = next((item for item in actors if item.get("label") == blocked), None)
        if bottle is None:
            raise ValueError("blocked_label must identify a configured reagent")
        x, y, _ = bottle["position_m"]
        actors.append({"actor_id": "movable-blocker", "kind": "blocker", "position_m": [x, y - 0.065, 0],
                       "shape": "box", "size_m": [0.07, 0.03, 0.15], "fixed": False})
    for name, radius, height, wall in (("bottle", 0.028, 0.12, 0.003), ("beaker", 0.055, 0.10, 0.004)):
        open_container_mesh(output / f"{name}.obj", radius=radius, height=height, wall=wall)
        (output / f"{name}-collision.json").write_text(json.dumps(container_collision(radius, height, wall), indent=2) + "\n")
    manifest = {"task_name": "lab_pour_stir", "frame": "table_top", "unit": "m", "seed": seed,
                "source": "procedural_scene_definition", "actors": actors,
                "staging_region": {"center_m": [-0.15, -0.25, 0], "size_xy_m": [0.10, 0.06]},
                "note": "Private asset/layout metadata; not sensor evidence or an Agent identity answer. Load with robotwin20_adapter.lab_scene.load_lab_scene; robot routes remain separate."}
    (output / "scene.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # A layout preview is deliberately labelled as a schematic, never a simulator screenshot.
    preview = Image.new("RGB", (1000, 850), "#d8e4e3")
    draw = ImageDraw.Draw(preview)
    small = ImageFont.truetype(str(font_path), 19)
    draw.text((20, 15), "LAB LAYOUT SCHEMATIC - not a simulation render", fill="black", font=small)
    for actor in actors:
        if actor["kind"] in {"holder", "stand"}:
            continue  # Shared footprint is captioned with the supported object below.
        x, y, _ = actor["position_m"]
        px, py = int(500 + x * 1250), int(450 - y * 1150)
        size = 30 if actor["kind"] == "reagent_bottle" else 22
        color = "#f4ce76" if actor["kind"] == "reagent_bottle" else "#a9bccb"
        draw.ellipse((px-size, py-size, px+size, py+size), fill=color, outline="black", width=2)
        text = actor.get("label", {"beaker": "beaker + holder", "stir-rod": "rod + stand"}.get(actor["actor_id"], actor["actor_id"]))
        draw.text((px, py + size + 3), text, fill="black", font=small, anchor="mt")
    draw.text((20, 810), f"{len(actors)} actors; seed={seed}; labels are independently shuffled", fill="black", font=small)
    preview.save(output / "layout.png")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    manifest = generate(config, args.output, seed=args.seed)
    print(json.dumps({"scene": str(args.output / "scene.json"), "actors": len(manifest["actors"]),
                      "labelled_bottles": len(config["reagent_labels"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
