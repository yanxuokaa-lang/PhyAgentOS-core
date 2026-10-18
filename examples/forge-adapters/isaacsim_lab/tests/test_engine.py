from threading import Event

import isaacsim_lab.engine as module
from isaacsim_lab.engine import (
    IsaacSimLabEngine,
    _continuous_pour_window,
    _episode_succeeded,
    _pour_controller_target,
)


class Backend:
    def run_cycle(self, arguments, cancel):
        assert arguments["operation"] == "pour_cycle"
        assert not cancel.is_set()
        return {"status": "unknown", "outcome_known": False, "world_change_started": False}


def make_profile(tmp_path):
    config = tmp_path / "level.yaml"
    scene = tmp_path / "scene.usd"
    robot = tmp_path / "robot.usd"
    config.write_text("name: lab", encoding="utf-8")
    scene.write_text("usd", encoding="utf-8")
    robot.write_text("usd", encoding="utf-8")
    from isaacsim_lab.profile import LabUtopiaProfile
    return LabUtopiaProfile.from_mapping({
        "lab_root": str(tmp_path), "config_path": str(config), "scene_usd_path": str(scene),
        "robot_usd_path": str(robot),
        "source_path": "/World/conical_bottle03", "destination_path": "/World/beaker2",
    })


def test_capability_is_disabled_without_isaac_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "_isaac_runtime_available", lambda: False)
    declaration = IsaacSimLabEngine(make_profile(tmp_path), backend=Backend()).cycle_capability("pour_cycle")
    assert declaration["preparation"] is False
    assert declaration["execution"] is False
    assert declaration["motion_authorized"] is False


def test_backend_result_is_not_promoted_to_success(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "_isaac_runtime_available", lambda: True)
    engine = IsaacSimLabEngine(make_profile(tmp_path), backend=Backend())
    result = engine.execute_cycle("pour_cycle", make_profile(tmp_path).paos_input(), Event())
    assert result["status"] == "unknown"
    assert result["outcome_known"] is False


def test_failed_feedback_phase_cannot_be_promoted_to_success():
    events = [
        {"phase": "acquire", "status": "completed", "outcome_known": True},
        {"phase": "transport", "status": "completed", "outcome_known": True},
        {"phase": "process", "status": "failed", "outcome_known": True},
        {"phase": "stow", "status": "completed", "outcome_known": True},
        {"phase": "release", "status": "completed", "outcome_known": True},
        {"phase": "retreat", "status": "completed", "outcome_known": True},
    ]
    assert not _episode_succeeded(True, True, events)


def test_continuous_pour_window_does_not_cross_sampling_gap(tmp_path):
    profile = make_profile(tmp_path)
    qualifying = {"grasp_valid": True, "target_container_aligned": True, "tilt_rad": profile.tilt_rad}
    samples = [
        {**qualifying, "timestamp_s": 0.0},
        {**qualifying, "timestamp_s": 0.3},
        {**qualifying, "timestamp_s": 0.41},
        {**qualifying, "timestamp_s": 0.52},
    ]
    assert _continuous_pour_window(samples, profile) is None


def test_pour_controller_target_compensates_measured_mouth_offset(tmp_path):
    profile = make_profile(tmp_path)
    import numpy as np
    from scipy.spatial.transform import Rotation

    state = {
        "object_position": np.array([0.4, 0.2, 1.0]),
        "target_position": np.array([0.4, 0.2, 1.2]),
        "object_quaternion": Rotation.identity().as_quat(),
        "object_size": np.array([0.1, 0.1, 0.6]),
    }
    target = _pour_controller_target(state, profile, np, Rotation)
    assert np.allclose(target, [0.4, 0.2, 0.9])


def test_pour_diagnosis_identifies_alignment_loss_before_target_tilt(tmp_path):
    profile = make_profile(tmp_path)
    samples = [
        {"grasp_valid": True, "target_container_aligned": True, "tilt_rad": 0.2, "timestamp_s": 0.0},
        {"grasp_valid": True, "target_container_aligned": False, "tilt_rad": 0.8, "timestamp_s": 0.1},
    ]
    report = module.diagnose_pour_observations(samples, profile)
    assert report["bottleneck"] == "alignment_lost_before_target_tilt"
    assert report["joint_sample_count"] == 0
