import json
from pathlib import Path

import pytest

from robotwin20_adapter.lab_assets import container_collision, generate, open_container_mesh


def config():
    root = Path(__file__).resolve().parents[1]
    return json.loads((root / "profiles/robotwin20/lab-tabletop-assets.json").read_text())


def test_cluttered_layout_has_eight_visual_labels_and_independent_mapping(tmp_path):
    first = generate(config(), tmp_path / "one", seed=0)
    same = generate(config(), tmp_path / "same", seed=0)
    other = generate(config(), tmp_path / "other", seed=1)
    assert first == same and len(first["actors"]) == 18
    bottles = [actor for actor in first["actors"] if actor["kind"] == "reagent_bottle"]
    assert {actor["label"] for actor in bottles} == set("ABCDEFGH")
    assert [actor["label"] for actor in bottles] != [actor["label"] for actor in other["actors"][:8]]
    assert [actor["position_m"] for actor in bottles] == [actor["position_m"] for actor in other["actors"][:8]]
    assert (tmp_path / "one/bottle.obj").read_bytes() == (tmp_path / "other/bottle.obj").read_bytes()
    assert len({(tmp_path / "one" / actor["label_texture"]).read_bytes() for actor in bottles}) == 8
    target = next(actor for actor in bottles if actor["label"] == "A")
    blocker = next(actor for actor in first["actors"] if actor["kind"] == "blocker")
    assert blocker["position_m"][0] == target["position_m"][0]
    assert blocker["position_m"][1] < target["position_m"][1]
    assert (tmp_path / "one/layout.png").is_file()


def test_open_container_has_inner_floor_and_no_face_capping_mouth(tmp_path):
    path = tmp_path / "cup.obj"
    open_container_mesh(path, radius=0.055, height=0.1, wall=0.004)
    vertices, faces = [], []
    for line in path.read_text().splitlines():
        if line.startswith("v "):
            vertices.append(tuple(map(float, line.split()[1:])))
        if line.startswith("f "):
            faces.append([vertices[int(i) - 1] for i in line.split()[1:]])
    assert any(vertex == (0, 0, 0.004) for vertex in vertices)
    assert not any(vertex == (0, 0, 0.1) for vertex in vertices)
    # Mouth polygons are annular quads, never triangles to the axis.
    top = [face for face in faces if all(v[2] == 0.1 for v in face)]
    assert len(top) == 32 and all(len(face) == 4 for face in top)
    parts = container_collision(0.055, 0.1, 0.004)
    assert len(parts) == 25 and parts[0]["center_m"][2] == 0.002
    assert all(part["shape"] == "box" for part in parts[1:])
    assert all(part["half_extents_m"][0] == 0.002 for part in parts[1:])


@pytest.mark.parametrize("labels", [["A", "A"], ["A"], ["../A", "B"]])
def test_invalid_label_set_is_rejected_before_writing(tmp_path, labels):
    data = config()
    data["reagent_labels"] = labels
    with pytest.raises(ValueError):
        generate(data, tmp_path / "invalid", seed=0)
    assert not (tmp_path / "invalid").exists()
