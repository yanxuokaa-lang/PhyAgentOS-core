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


def test_perception_binding_cannot_fall_back_to_profile_identity(tmp_path):
    binding = {
        "entity_ref": "entity://observed", "destination_ref": "destination://beaker",
        "observation_ref": "observation://scene/camera", "scene_revision": "scene-2",
        "frame_id": "camera-front", "calibration_ref": "artifact://calibration/v1",
        "binding_ref": "artifact://binding/observed", "freshness_ms": 5, "max_age_ms": 1000,
    }
    value = profile(tmp_path).paos_input(perception_binding=binding)
    assert value["entity_ref"] == "entity://observed"
    assert value["destination_ref"] == "destination://beaker"
    assert value["observation_ref"] == binding["observation_ref"]
    assert value["scene_revision"] == binding["scene_revision"]
    assert value["frame_id"] == binding["frame_id"]
    assert value["calibration_ref"] == binding["calibration_ref"]
    assert value["freshness_ms"] == binding["freshness_ms"]
    assert value["max_age_ms"] == binding["max_age_ms"]
    with pytest.raises(LabProfileError, match="provenance"):
        profile(tmp_path).paos_input(perception_binding={"entity_ref": "entity://observed"})


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


def test_label_inspection_camera_settings_are_profile_configured(tmp_path):
    scene = tmp_path / "lab.usd"
    config = tmp_path / "level.yaml"
    scene.write_text("usd", encoding="utf-8")
    config.write_text("name: lab", encoding="utf-8")
    configured = LabUtopiaProfile.from_mapping({
        "lab_root": str(tmp_path), "config_path": str(config),
        "scene_usd_path": str(scene), "robot_usd_path": str(scene),
        "source_path": "/World/conical_bottle03", "destination_path": "/World/beaker2",
        "label_inspection_prim_path": "/World/ReagentZones/A/R01",
        "label_inspection_focal_length_mm": 3.5,
    })
    assert configured.label_inspection_prim_path == "/World/ReagentZones/A/R01"
    assert configured.label_inspection_focal_length_mm == 3.5
    with pytest.raises(LabProfileError, match="label_inspection_prim_path"):
        LabUtopiaProfile.from_mapping({
            "lab_root": str(tmp_path), "config_path": str(config),
            "scene_usd_path": str(scene), "robot_usd_path": str(scene),
            "source_path": "/World/conical_bottle03", "destination_path": "/World/beaker2",
            "label_inspection_prim_path": "ReagentZones/A/R01",
        })


def test_profile_normalizes_source_pour_axis(tmp_path):
    configured = profile(tmp_path)
    assert configured.source_pour_axis == (0.0, 0.0, 1.0)
    assert configured.configured_process_type == "pour"
    assert "manipulation_cycle" in configured.supported_operations


def test_generic_cycle_requires_caller_parameters_and_profile_opt_in(tmp_path):
    (tmp_path / "level.yaml").write_text("name: lab", encoding="utf-8")
    (tmp_path / "lab.usd").write_text("usd", encoding="utf-8")
    configured = LabUtopiaProfile.from_mapping({
        "lab_root": str(tmp_path), "config_path": str(tmp_path / "level.yaml"),
        "scene_usd_path": str(tmp_path / "lab.usd"), "robot_usd_path": str(tmp_path / "lab.usd"),
        "source_path": "/World/cap", "destination_path": "/World/cap_target",
        "configured_process_type": "cap_unscrew",
        "supported_operations": ["manipulation_cycle"],
    })
    with pytest.raises(LabProfileError, match="caller-supplied"):
        configured.paos_input(operation="manipulation_cycle")
    value = configured.paos_input({"parameters": {
        "process_type": "cap_unscrew", "engagement": "cap", "hold_s": 0.5,
        "transform": {"mode": "rotation", "axis": [0, 0, 1], "magnitude": 1.0,
                      "speed": 0.5, "direction": "ccw", "tolerance": 0.05},
    }}, operation="manipulation_cycle")
    assert value["parameters"]["process_type"] == "cap_unscrew"


def test_stir_profile_projects_defaults_for_existing_glass_rod_scene(tmp_path):
    scene = tmp_path / "lab.usd"
    config = tmp_path / "level.yaml"
    scene.write_text("usd", encoding="utf-8")
    config.write_text("name: lab", encoding="utf-8")
    configured = LabUtopiaProfile.from_mapping({
        "lab_root": str(tmp_path), "config_path": str(config),
        "scene_usd_path": str(scene), "robot_usd_path": str(scene),
        "source_path": "/World/glass_rod", "destination_path": "/World/target_beaker",
        "source_control_path": "/World/glass_rod/Cylinder",
        "source_label": "玻璃棒", "destination_label": "烧杯",
        "configured_process_type": "stir", "supported_operations": ["stir_cycle"],
    })
    value = configured.paos_input(operation="stir_cycle")
    assert value["parameters"] == {
        "radius_m": 0.009, "depth_m": 0.04, "turns": 2.0,
        "duration_s": 4.0, "direction": "ccw",
    }
    assert configured.source_control_path == "/World/glass_rod/Cylinder"


def test_profile_rejects_non_world_source_control_path(tmp_path):
    (tmp_path / "level.yaml").write_text("name: lab", encoding="utf-8")
    (tmp_path / "lab.usd").write_text("usd", encoding="utf-8")
    with pytest.raises(LabProfileError, match="source_control_path"):
        LabUtopiaProfile.from_mapping({
            "lab_root": str(tmp_path),
            "config_path": str(tmp_path / "level.yaml"),
            "scene_usd_path": str(tmp_path / "lab.usd"),
            "robot_usd_path": str(tmp_path / "lab.usd"),
            "source_path": "/World/glass_rod",
            "destination_path": "/World/target_beaker",
            "source_control_path": "glass_rod/Cylinder",
        })


@pytest.mark.parametrize("values", [
    {"physics_dt_s": .02, "control_dt_s": .01},
    {"physics_dt_s": .01, "control_dt_s": .015},
    {"startup_settle_s": -1}, {"startup_settle_s": float("nan")},
    {"physics_scene_path": "relative"},
])
def test_profile_rejects_invalid_simulation_clock(tmp_path, values):
    from dataclasses import asdict

    configured = asdict(profile(tmp_path))
    configured = {key: str(value) if hasattr(value, "as_posix") else value
                  for key, value in configured.items()}
    configured.update(values)
    with pytest.raises(LabProfileError):
        LabUtopiaProfile.from_mapping(configured)
