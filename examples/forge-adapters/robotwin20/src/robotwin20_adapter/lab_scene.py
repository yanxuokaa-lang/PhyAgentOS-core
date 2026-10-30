"""Load the generated laboratory assets into a caller-owned SAPIEN 3 scene.

This loader never steps physics or commands a robot. Actor identities and
functional points are private scene metadata, not visual recognition results.
"""

from __future__ import annotations

import json
import math
import argparse
from pathlib import Path


def load_lab_scene(scene, asset_root: Path, *, world_from_table):
    """Return actor-id -> SAPIEN entity; the caller supplies the table transform."""
    import sapien

    asset_root = Path(asset_root)
    manifest = json.loads((asset_root / "scene.json").read_text(encoding="utf-8"))
    if manifest["frame"] != "table_top" or manifest["unit"] != "m":
        raise ValueError("laboratory assets must use the table_top frame in metres")
    entities = {}
    cylinder_q = [math.sqrt(0.5), 0, -math.sqrt(0.5), 0]  # SAPIEN cylinder +X -> +Z
    for actor in manifest["actors"]:
        builder = scene.create_actor_builder()
        color = [0.82, 0.87, 0.89, 1] if actor["kind"] == "reagent_bottle" else [0.3, 0.55, 0.65, 1]
        material = sapien.render.RenderMaterial(base_color=color, roughness=0.6)
        if "mesh" in actor:
            builder.add_visual_from_file(str(asset_root / actor["mesh"]), material=material)
            for part in json.loads((asset_root / actor["collision"]).read_text()):
                if part["shape"] == "cylinder":
                    builder.add_cylinder_collision(
                        pose=sapien.Pose(part["center_m"], cylinder_q),
                        radius=part["radius_m"], half_length=part["half_length_m"], density=300,
                    )
                else:
                    yaw = part["yaw_rad"]
                    builder.add_box_collision(
                        pose=sapien.Pose(part["center_m"], [math.cos(yaw/2), 0, 0, math.sin(yaw/2)]),
                        half_size=part["half_extents_m"], density=300,
                    )
        elif actor["kind"] == "handled_rod":
            shaft, handle = actor["shaft_length_m"], actor["handle_length_m"]
            for radius, length, z in ((actor["shaft_radius_m"], shaft, shaft/2),
                                      (actor["handle_radius_m"], handle, shaft+handle/2)):
                pose = sapien.Pose([0, 0, z], cylinder_q)
                builder.add_cylinder_collision(pose=pose, radius=radius, half_length=length/2, density=400)
                builder.add_cylinder_visual(pose=pose, radius=radius, half_length=length/2, material=material)
        elif actor["shape"] == "box":
            size = actor["size_m"]
            pose = sapien.Pose([0, 0, size[2]/2])
            builder.add_box_collision(pose=pose, half_size=[v/2 for v in size])
            builder.add_box_visual(pose=pose, half_size=[v/2 for v in size], material=material)
            if actor["kind"] == "stand":
                # Four rails support the vertical shaft, leaving its wider handle exposed.
                gap, wall, height = 0.005, 0.004, 0.09
                for axis in (0, 1):
                    for sign in (-1, 1):
                        center = [0, 0, size[2] + height/2]
                        center[axis] = sign*(gap+wall/2)
                        half = [gap+wall, gap+wall, height/2]
                        half[axis] = wall/2
                        builder.add_box_collision(pose=sapien.Pose(center), half_size=half)
                        builder.add_box_visual(pose=sapien.Pose(center), half_size=half, material=material)
        if "label_texture" in actor:
            label_material = sapien.render.RenderMaterial(base_color=[1, 1, 1, 1], roughness=1)
            label_material.set_base_color_texture(sapien.render.RenderTexture2D(str(asset_root / actor["label_texture"])))
            for yaw in actor["label_yaws_rad"]:
                builder.add_visual_from_file(
                    str(asset_root / actor["label_mesh"]), material=label_material,
                    pose=sapien.Pose([0, 0, actor["label_height_m"]], [math.cos(yaw/2), 0, 0, math.sin(yaw/2)]),
                )
        builder.set_initial_pose(world_from_table * sapien.Pose(actor["position_m"]))
        build = builder.build_static if actor["fixed"] else builder.build
        entities[actor["actor_id"]] = build(name=actor["actor_id"])
    return entities


def render_inspection(asset_root: Path, output: Path, *, width=1600, height=1200):
    """Render the actual SAPIEN assets without a robot or physics advancement."""
    import cv2
    import numpy as np
    import sapien

    scene = sapien.Scene()
    scene.set_ambient_light([0.5, 0.5, 0.5])
    scene.add_directional_light([0, 0, -1], [1, 1, 1], shadow=True)
    actors = load_lab_scene(scene, asset_root, world_from_table=sapien.Pose())
    builder = scene.create_actor_builder()
    builder.add_box_visual(half_size=[0.6, 0.5, 0.02], material=sapien.render.RenderMaterial(base_color=[0.6, 0.65, 0.65, 1]))
    builder.set_initial_pose(sapien.Pose([0, 0, -0.02]))
    builder.build_static(name="inspection-table")
    camera = scene.add_camera("inspection", width, height, 0.8, 0.01, 10)
    position, target = np.array([0, -0.85, 0.75]), np.array([0, 0.05, 0.05])
    forward = target-position
    forward /= np.linalg.norm(forward)
    left = np.cross([0, 0, 1], forward)
    left /= np.linalg.norm(left)
    matrix = np.eye(4)
    matrix[:3, :3] = np.column_stack([forward, left, np.cross(forward, left)])
    matrix[:3, 3] = position
    camera.set_entity_pose(sapien.Pose(matrix))
    scene.update_render()
    camera.take_picture()
    rgb = (np.clip(camera.get_picture("Color")[:, :, :3], 0, 1)*255).astype("uint8")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), rgb[:, :, ::-1]):
        raise OSError(f"could not save laboratory inspection image: {output}")
    return {"actors": len(actors), "physics_steps": 0, "robot_loaded": False,
            "render": str(output), "sapien_version": sapien.__version__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--render", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render_inspection(args.assets, args.render)))


if __name__ == "__main__":
    main()
