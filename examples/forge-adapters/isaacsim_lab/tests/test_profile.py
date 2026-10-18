import json

import pytest

from isaacsim_lab.profile import LabProfileError, LabUtopiaProfile


def profile(tmp_path):
    scene = tmp_path / "lab.usd"
    config = tmp_path / "level.yaml"
    scene.write_text("usd", encoding="utf-8")
    config.write_text("name: lab", encoding="utf-8")
    return LabUtopiaProfile.from_mapping({
        "lab_root": str(tmp_path),
        "config_path": str(config),
        "scene_usd_path": str(scene),
        "robot_usd_path": str(scene),
        "source_path": "/World/conical_bottle03",
        "destination_path": "/World/beaker2",
    })


def test_paos_input_projects_bottle_and_beaker_refs(tmp_path):
    value = profile(tmp_path).paos_input()
    assert value["entity_ref"] == "entity://conical_bottle03"
    assert value["destination_ref"] == "destination://beaker2"
    assert value["operation"] == "pour_cycle"
    assert value["parameters"]["tilt_rad"] > 0


def test_previous_input_cannot_change_scene_identity(tmp_path):
    with pytest.raises(LabProfileError, match="different source"):
        profile(tmp_path).paos_input({"entity_ref": "entity://other"})


def test_profile_round_trips_json(tmp_path):
    value = {
        "lab_root": str(tmp_path),
        "config_path": str(tmp_path / "level.yaml"),
        "scene_usd_path": str(tmp_path / "lab.usd"),
        "robot_usd_path": str(tmp_path / "lab.usd"),
        "source_path": "/World/conical_bottle03",
        "destination_path": "/World/beaker2",
    }
    (tmp_path / "level.yaml").write_text("name: lab", encoding="utf-8")
    (tmp_path / "lab.usd").write_text("usd", encoding="utf-8")
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    assert LabUtopiaProfile.from_json(path).source_path == value["source_path"]
