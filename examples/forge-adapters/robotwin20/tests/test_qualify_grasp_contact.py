import json
from pathlib import Path

import pytest
import qualify_grasp_contact as cli


def _write(path: Path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _inputs(tmp_path: Path):
    candidate = {
        "candidate_ref": "candidate://block-green-1/0",
        "entity_ref": "entity://block-green-1",
        "scene_revision": "scene-1",
        "execution_grasp": {
            "contact_center_pose": {
                "frame_id": "world", "position_m": [0.0, 0.0, 0.8],
                "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
            },
            "robot_target_pose": {
                "frame_id": "world", "position_m": [0.0, 0.0, 1.0],
                "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
            },
            "ingress_direction": {"vector": [0.0, 0.0, -1.0]},
        },
    }
    geometry = {
        "schema_version": "paos-robotwin20-grasp-contact-geometry/v1",
        "frame_id": "world", "scene_revision": "scene-1", "motion_authorized": False,
        "arms": {"right": {
            "links": {name: [[0.0, 0.0, 0.0]] for name in (
                "panda_hand", "panda_leftfinger", "panda_rightfinger"
            )},
            "reference_hand_pose": {
                "frame_id": "world", "position_m": [0.0, 0.0, 0.0],
                "orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
            },
        }},
        "support_plane": {"normal": [0.0, 0.0, 1.0], "offset_m": 0.74},
    }
    scene = {"objects": [{
        "entity_ref": "entity://block-green-1", "half_extents_m": [0.05, 0.05, 0.05],
        "world_T_object": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0.8, 0, 0, 0, 1],
    }]}
    profile = """grasp_adaptation:\n  robot_target_reference_distance_m: 0.12\n  robot_gripper_bias_m: 0.08\n  robot_delta_matrix: [[1, 0, 0], [0, 1, 0], [0, 0, 1]]\n"""
    files = {
        "candidate": _write(tmp_path / "candidate.json", candidate),
        "geometry": _write(tmp_path / "geometry.json", geometry),
        "scene": _write(tmp_path / "scene.json", scene),
    }
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(profile, encoding="utf-8")
    files["profile"] = profile_path
    return files


def test_cli_qualifies_using_profile_derived_hand_pose(tmp_path):
    files = _inputs(tmp_path)
    result = cli.qualify(
        candidate_file=files["candidate"], geometry_file=files["geometry"],
        scene_file=files["scene"], profile_file=files["profile"],
        entity_ref="entity://block-green-1", arm_id="right",
    )
    assert result["status"] == "qualified"
    assert result["motion_authorized"] is False


def test_cli_reports_stale_geometry_binding(tmp_path):
    files = _inputs(tmp_path)
    geometry = json.loads(files["geometry"].read_text())
    geometry["scene_revision"] = "scene-old"
    _write(files["geometry"], geometry)
    with pytest.raises(cli.QualificationCliError, match="contact qualification failed"):
        cli.qualify(
            candidate_file=files["candidate"], geometry_file=files["geometry"],
            scene_file=files["scene"], profile_file=files["profile"],
            entity_ref="entity://block-green-1", arm_id="right",
        )


def test_cli_rejects_candidate_entity_mismatch(tmp_path):
    files = _inputs(tmp_path)
    candidate = json.loads(files["candidate"].read_text())
    candidate["entity_ref"] = "entity://block-red-1"
    _write(files["candidate"], candidate)
    with pytest.raises(cli.QualificationCliError, match="candidate entity binding"):
        cli.qualify(
            candidate_file=files["candidate"], geometry_file=files["geometry"],
            scene_file=files["scene"], profile_file=files["profile"],
            entity_ref="entity://block-green-1", arm_id="right",
        )


def test_cli_requires_new_output_file(tmp_path, monkeypatch):
    files = _inputs(tmp_path)
    output = tmp_path / "result.json"
    output.write_text("existing", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["qualify_grasp_contact", "--candidate", str(files["candidate"]), "--contact-geometry", str(files["geometry"]), "--scene-facts", str(files["scene"]), "--route-input-profile", str(files["profile"]), "--entity-ref", "entity://block-green-1", "--arm-id", "right", "--output", str(output)])
    with pytest.raises(SystemExit, match="new absolute file"):
        cli.main()
