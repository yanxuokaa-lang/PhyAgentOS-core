import json
import sys
import types
from threading import Event

import numpy as np
import pytest

import isaacsim_lab.engine as module
from isaacsim_lab.engine import (
    IsaacSimLabEngine,
    LabUtopiaBackend,
    _bound_endpoint,
    _continuous_pour_window,
    _episode_succeeded,
    _EpisodeVideoRecorder,
    _failed_events,
    _generic_phase_events,
    _generic_result,
    _get_session_scene_resources,
    _pour_controller_target,
    _stir_controller_target,
    _stir_phase_events,
    _stir_tip_offset,
    _stir_trace_metrics,
    normalize_process_parameters,
)


class Backend:
    def __init__(self, scene_revision="labutopia-scene-v1"):
        self.scene_revision = scene_revision

    def current_scene_revision(self):
        return self.scene_revision

    def run_cycle(self, arguments, cancel):
        assert arguments["operation"] == "pour_cycle"
        assert not cancel.is_set()
        return {"status": "unknown", "outcome_known": False, "world_change_started": False}


def make_profile(tmp_path, *, configured_process_type="pour"):
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
        "configured_process_type": configured_process_type,
    })


def make_target(profile, *, process_type="pour"):
    frame_id = profile.frame_id
    pose = {
        "frame_id": frame_id, "unit": "m", "position_m": [0.2, 0.1, 0.8],
        "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
    }
    target = {
        "candidate_ref": "candidate://conical_bottle03/test",
        "entity_ref": "entity://conical_bottle03",
        "destination_ref": "destination://beaker2",
        "scene_revision": profile.scene_revision,
        "frame_id": frame_id,
        "calibration_ref": profile.calibration_ref,
        "control_frame_id": frame_id,
        "world_from_control": {
            "parent_frame_id": "world", "child_frame_id": frame_id, "translation_m": [0.0, 0.0, 0.0],
            "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
        },
        "entity_prim_path": profile.source_path,
        "destination_prim_path": profile.destination_path,
        "object_pose": pose,
        "grasp_frame": pose,
        "approach_direction": {"frame_id": frame_id, "unit": "unitless", "vector": [0.0, 0.0, -1.0]},
        "destination_pose": pose,
        "return_pose": pose,
        "geometry": {"size_m": [0.04, 0.04, 0.12]},
    }
    if process_type == "stir":
        target["entity_ref"] = "entity://glass_rod"
        target["destination_ref"] = "destination://target_beaker"
        target["entity_prim_path"] = "/World/glass_rod"
        target["destination_prim_path"] = "/World/target_beaker"
        target["candidate_ref"] = "candidate://glass_rod/test"
        target["tool_prim_path"] = "/World/glass_rod/Cylinder"
        target["tool_frame"] = {"frame_id": frame_id, "tip_axis_local": [0.0, 0.0, -1.0]}
    if process_type == "pour":
        target["process_frame"] = {"frame_id": frame_id, "origin_m": [0.2, 0.1, 0.8], "axis": [0.0, 0.0, 1.0]}
    return target


def _stir_process_samples(radius, depth, start, duration, turns):
    return [
        {
            "timestamp_s": start + duration * index / 40,
            "controller_phase": "stirring",
            "grasp_valid": True,
            "feedback_valid": True,
            "target_container_aligned": True,
            "transform_progress": radius,
            "tool_tip_x_m": radius * np.cos(2 * np.pi * turns * index / 40),
            "tool_tip_y_m": radius * np.sin(2 * np.pi * turns * index / 40),
            "tool_tip_depth_m": depth,
        }
        for index in range(41)
    ]


def test_capability_is_disabled_without_isaac_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "_isaac_runtime_available", lambda: False)
    declaration = IsaacSimLabEngine(make_profile(tmp_path), backend=Backend()).cycle_capability("pour_cycle")
    assert declaration["preparation"] is False
    assert declaration["execution"] is False
    assert declaration["motion_authorized"] is False


def test_observation_is_not_advertised_without_live_camera_registry(tmp_path):
    backend = LabUtopiaBackend(make_profile(tmp_path))
    assert backend.observation_ready is False
    from isaacsim_lab.worker import WorkerSessionContext

    result = backend.observe_in_session(WorkerSessionContext(object()), {"sensor_ref": "sensor://front"})
    assert result["status"] == "unavailable"
    assert result["failure_code"] == "session_camera_registry_unavailable"
    assert result["motion_authorized"] is False


def test_observation_uses_source_registered_on_worker_session(tmp_path):
    from isaacsim_lab.worker import WorkerSessionContext

    class ObservationSource:
        def capture(self, request):
            return {"status": "available", "sensor_ref": request["sensor_ref"]}

    session = WorkerSessionContext(object())
    session.register("observation_source", ObservationSource())
    result = LabUtopiaBackend(make_profile(tmp_path)).observe_in_session(
        session, {"sensor_ref": "sensor://front"}
    )

    assert result == {"status": "available", "sensor_ref": "sensor://front"}


def test_worker_registers_configured_isaac_cameras_and_persists_capture(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from PhyAgentOS.forge.capability_runtime.observation import ObservationEndpoint

    from isaacsim_lab.worker import WorkerSessionContext

    calls = []

    class Camera:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def set_local_pose(self, **kwargs):
            calls.append(("pose", kwargs))

        def set_focal_length(self, value):
            calls.append(("focal_length", value))

        def set_clipping_range(self, **kwargs):
            calls.append(("clipping", kwargs))

        def initialize(self):
            calls.append(("initialize", self.kwargs["name"]))

        def add_distance_to_image_plane_to_frame(self):
            calls.append(("depth", self.kwargs["name"]))

        def add_pointcloud_to_frame(self):
            calls.append(("point_cloud", self.kwargs["name"]))

        def get_rgb(self):
            return np.ones((2, 3, 3), dtype=np.uint8)

        def get_depth(self):
            return np.ones((2, 3), dtype=np.float32)

        def get_pointcloud(self):
            return np.ones((2, 3, 3), dtype=np.float32)

        def get_intrinsics_matrix(self, *, device):
            assert device == "cpu"
            return np.eye(3)

        def get_world_pose(self, *, camera_axes):
            assert camera_axes == "world"
            return np.zeros(3), np.asarray([1.0, 0.0, 0.0, 0.0])

        def get_resolution(self):
            return 3, 2

    class Stage:
        def get_prim_at_path(self, path):
            return SimpleNamespace(IsValid=lambda: path == "/World/ExistingCamera")

    stage = Stage()
    stage.GetPrimAtPath = stage.get_prim_at_path

    camera_module = types.ModuleType("isaacsim.sensors.camera")
    camera_module.Camera = Camera
    monkeypatch.setitem(sys.modules, "isaacsim", types.ModuleType("isaacsim"))
    monkeypatch.setitem(sys.modules, "isaacsim.sensors", types.ModuleType("isaacsim.sensors"))
    monkeypatch.setitem(sys.modules, "isaacsim.sensors.camera", camera_module)

    profile = make_profile(tmp_path)
    backend = LabUtopiaBackend(profile)
    session = WorkerSessionContext(object())
    session.initialize_scene_revision(profile.scene_revision)
    cfg = SimpleNamespace(cameras=[
        SimpleNamespace(
            name="front", prim_path="/World/NewCamera", resolution=[3, 2],
            translation=[1.0, 2.0, 3.0], orientation=[1.0, 0.0, 0.0, 0.0],
            focal_length=6.0,
        ),
        SimpleNamespace(
            name="wrist", prim_path="/World/ExistingCamera", resolution=[3, 2],
        ),
    ])

    backend._register_session_observation_source(session, cfg, stage)
    result = ObservationEndpoint(session.resolve("observation_source")).invoke({
        "sensor_ref": "sensor://front", "max_age_ms": 1000,
    })

    assert result["status"] == "available"
    assert result["scene_revision"].startswith(f"{profile.scene_revision}:")
    assert result["frame"]["frame_id"] == "front"
    assert {item["kind"] for item in result["artifacts"]} == {
        "rgb", "depth", "point_cloud",
    }
    assert all(item["ref"].startswith("artifact://labutopia/") for item in result["artifacts"])
    artifact_root = tmp_path / "outputs" / "paos-observation-artifacts"
    assert len(list(artifact_root.rglob("*.npy"))) == 3
    assert len(list(artifact_root.rglob("*.json"))) == 1
    assert calls.count(("initialize", "front")) == 1
    assert calls.count(("initialize", "wrist")) == 1


def test_worker_does_not_register_observation_source_without_camera_configuration(tmp_path):
    from types import SimpleNamespace

    from isaacsim_lab.worker import WorkerSessionContext

    session = WorkerSessionContext(object())
    backend = LabUtopiaBackend(make_profile(tmp_path))
    backend._register_session_observation_source(session, SimpleNamespace(cameras=[]), object())

    assert session.resolve("camera_registry") is None
    assert session.resolve("observation_source") is None


def test_session_owned_task_initializes_world_before_task_and_never_resets_it_again():
    events = []

    class World:
        def reset(self):
            events.append("world.reset")

    class Robot:
        def initialize(self):
            events.append("robot.initialize")

    class Task:
        def __init__(self, *, world, robot, session_owned_scene, **kwargs):
            assert isinstance(world, World)
            assert isinstance(robot, Robot)
            assert session_owned_scene is True
            assert kwargs == {"cfg": "config", "stage": "stage"}
            events.append("task.construct")

        def reset(self):
            events.append("task.reset")

    task = module._create_session_owned_task(
        World(), Robot(), Task, cfg="config", stage="stage"
    )

    assert isinstance(task, Task)
    assert events == ["world.reset", "task.construct", "robot.initialize", "task.reset"]


def test_worker_session_reuses_scene_resources_but_constructs_episode_tasks(tmp_path):
    from isaacsim_lab.worker import WorkerSessionContext

    profile = make_profile(tmp_path)
    session = WorkerSessionContext(object())
    counts = {"world": 0, "robot": 0, "stage": 0, "reference": 0, "object_utils": 0}

    class World:
        def reset(self):
            counts["world"] += 1

    class Robot:
        def initialize(self):
            counts["robot"] += 1

    stage = object()

    class ObjectUtils:
        @staticmethod
        def get_instance(actual_stage):
            assert actual_stage is stage
            counts["object_utils"] += 1

    def make_world():
        counts["world_created"] = counts.get("world_created", 0) + 1
        return World()

    def make_robot():
        counts["robot_created"] = counts.get("robot_created", 0) + 1
        return Robot()

    def resources():
        return _get_session_scene_resources(
            session,
            profile=profile,
            world_factory=make_world,
            robot_factory=make_robot,
            stage_provider=lambda: (counts.__setitem__("stage", counts["stage"] + 1) or stage),
            add_reference_to_stage=lambda **_kwargs: counts.__setitem__("reference", counts["reference"] + 1),
            object_utils=ObjectUtils,
        )

    first = resources()
    second = resources()

    class Task:
        def __init__(self, *, world, robot, session_owned_scene, **_kwargs):
            assert world is first["world"]
            assert robot is first["robot"]
            assert session_owned_scene is True
            self.reset_count = 0

        def reset(self):
            self.reset_count += 1

    first_task = module._create_session_owned_task(
        first["world"], first["robot"], Task, scene_state=first, cfg="pour", stage=first["stage"]
    )
    second_task = module._create_session_owned_task(
        second["world"], second["robot"], Task, scene_state=second, cfg="stir", stage=second["stage"]
    )

    assert first["world"] is second["world"]
    assert first["robot"] is second["robot"]
    assert first["stage"] is second["stage"]
    assert first_task is not second_task
    assert counts == {
        "world": 1, "robot": 1, "stage": 1, "reference": 1,
        "object_utils": 1, "world_created": 1, "robot_created": 1,
    }


def test_worker_session_rejects_scene_profile_switch(tmp_path):
    from isaacsim_lab.worker import WorkerSessionContext

    profile = make_profile(tmp_path)
    session = WorkerSessionContext(object())
    scene = {
        "world": object(), "robot": object(), "stage": object(),
        "scene_usd_path": "other.usd", "world_initialized": True, "robot_initialized": True,
    }
    session.register("lab_scene_resources", scene)
    with pytest.raises(module.IsaacLabRuntimeError, match="cannot switch its loaded scene"):
        _get_session_scene_resources(
            session,
            profile=profile,
            world_factory=lambda: pytest.fail("must not create a second World"),
            robot_factory=lambda: pytest.fail("must not create a second robot"),
            stage_provider=lambda: pytest.fail("must not resolve another stage"),
            add_reference_to_stage=lambda **_kwargs: pytest.fail("must not load another scene"),
            object_utils=object(),
        )


def test_session_cycle_reports_unintegrated_task_as_unsupported_without_world_change(tmp_path, monkeypatch):
    from isaacsim_lab.worker import WorkerSessionContext

    profile = make_profile(tmp_path)
    backend = LabUtopiaBackend(profile)
    monkeypatch.setattr(module, "normalize_process_parameters", lambda *_args: {"process_type": "handle_rotation"})
    session = WorkerSessionContext(object())
    result = backend._run_session_cycle(
        session,
        {"operation": "handle_rotation"},
        Event(),
        tmp_path / "episode.mp4",
    )

    assert result["status"] == "unsupported"
    assert result["world_change_started"] is False
    assert result["motion_authorized"] is False


def test_target_world_transform_projects_pose_and_process_frame(tmp_path):
    target = make_target(make_profile(tmp_path))
    target["world_from_control"]["translation_m"] = [1.0, 2.0, 3.0]
    target["destination_pose"]["position_m"] = [0.1, 0.2, 0.3]
    projected = module._target_in_world(target)
    assert projected["destination_pose"]["frame_id"] == "world"
    assert projected["destination_pose"]["position_m"] == pytest.approx([1.1, 2.2, 3.3])


def test_target_world_transform_rotates_approach_and_process_axis(tmp_path):
    target = make_target(make_profile(tmp_path))
    target["approach_direction"]["vector"] = [1.0, 0.0, 0.0]
    target["world_from_control"]["orientation_xyzw"] = [0.0, 0.0, np.sqrt(0.5), np.sqrt(0.5)]
    projected = module._target_in_world(target)
    assert projected["approach_direction"]["vector"] == pytest.approx([0.0, 1.0, 0.0])
    assert projected["process_frame"]["axis"] == pytest.approx([0.0, 0.0, 1.0])


def test_capability_does_not_claim_live_execution_before_eula_acceptance(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "_isaac_runtime_available", lambda: True)
    monkeypatch.delenv("OMNI_KIT_ACCEPT_EULA", raising=False)
    declaration = IsaacSimLabEngine(make_profile(tmp_path), backend=Backend()).cycle_capability("pour_cycle")
    assert declaration["preparation"] is True
    assert declaration["execution"] is False
    assert declaration["motion_authorized"] is False
    assert declaration["unavailable_reason"] == "OMNI_KIT_ACCEPT_EULA_not_accepted"


def test_backend_result_is_not_promoted_to_success(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "_isaac_runtime_available", lambda: True)
    monkeypatch.setenv("OMNI_KIT_ACCEPT_EULA", "YES")
    profile = make_profile(tmp_path)
    engine = IsaacSimLabEngine(profile, backend=Backend(profile.scene_revision))
    result = engine.execute_cycle(
        "pour_cycle", profile.paos_input({"manipulation_target": make_target(profile)}), Event()
    )
    assert result["status"] == "unknown"
    assert result["outcome_known"] is False


def test_live_cycle_rejects_missing_perception_target_before_backend(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "_isaac_runtime_available", lambda: True)
    monkeypatch.setenv("OMNI_KIT_ACCEPT_EULA", "YES")
    profile = make_profile(tmp_path)
    engine = IsaacSimLabEngine(profile, backend=Backend(profile.scene_revision))
    result = engine.execute_cycle("pour_cycle", profile.paos_input(), Event())
    assert result["status"] == "invalid"
    assert result["motion_authorized"] is False
    assert "manipulation_target" in result["error"]


def test_live_cycle_rejects_target_without_explicit_world_transform(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "_isaac_runtime_available", lambda: True)
    monkeypatch.setenv("OMNI_KIT_ACCEPT_EULA", "YES")
    profile = make_profile(tmp_path)
    target = make_target(profile)
    target.pop("world_from_control")
    result = IsaacSimLabEngine(profile, backend=Backend(profile.scene_revision)).execute_cycle(
        "pour_cycle", profile.paos_input({"manipulation_target": target}), Event()
    )
    assert result["status"] == "invalid"
    assert result["motion_authorized"] is False
    assert "world_from_control" in result["error"]


def test_legacy_backend_does_not_claim_unimplemented_generic_cycle(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "_isaac_runtime_available", lambda: True)
    engine = IsaacSimLabEngine(make_profile(tmp_path), backend=Backend())
    declaration = engine.cycle_capability("manipulation_cycle")
    assert declaration["execution"] is False
    assert declaration["motion_authorized"] is False


def test_legacy_pour_parameters_map_to_real_controller_dispatch(tmp_path):
    profile = make_profile(tmp_path)
    arguments = profile.paos_input({"parameters": {"speed": 0.4, "direction": "ccw"}}, operation="pour_cycle")
    normalized = normalize_process_parameters(arguments, profile)
    assert normalized["process_type"] == "pour"
    assert normalized["axis"] == [0.0, 0.0, 1.0]
    assert normalized["magnitude"] == profile.tilt_rad
    assert normalized["speed"] == 0.4
    assert normalized["controller_parameters"] == {"pour_speed": -0.4}
    assert normalized["mapped"]["speed"] == "pour_speed"


def test_legacy_stir_parameters_map_only_supported_controller_values(tmp_path):
    profile = make_profile(tmp_path, configured_process_type="stir")
    arguments = profile.paos_input({"parameters": {"radius_m": 0.01, "stir_speed": 2.0, "direction": "cw"}}, operation="stir_cycle")
    normalized = normalize_process_parameters(arguments, profile)
    assert normalized["process_type"] == "stir"
    assert normalized["controller_parameters"] == {"stir_radius": 0.01, "stir_speed": 2.0}
    assert normalized["mapped"]["magnitude"] == "stir_radius"
    assert normalized["turns"] == profile.stir_turns
    assert normalized["depth_m"] == profile.stir_depth_m
    assert normalized["duration_s"] == profile.stir_duration_s


def test_action_parameters_override_stir_settlement_thresholds(tmp_path):
    profile = make_profile(tmp_path, configured_process_type="stir")
    args = profile.paos_input({"parameters": {
        "radius_m": 0.012, "depth_m": 0.025, "turns": 1.0,
        "duration_s": 2.0, "direction": "cw",
    }}, operation="stir_cycle")
    normalized = normalize_process_parameters(args, profile)
    assert normalized["radius_m"] == 0.012
    assert normalized["depth_m"] == 0.025
    assert normalized["turns"] == 1.0
    assert normalized["duration_s"] == 2.0
    assert normalized["direction"] == "cw"


def test_usd_bound_endpoint_selects_the_configured_rod_tip():
    assert np.allclose(_bound_endpoint([0.0, 0.0, -0.1], [0.0, 0.0, 0.1], [0, 0, -1]),
                       [0.0, 0.0, -0.1])


def test_pour_controller_target_uses_perceived_process_origin(tmp_path):
    profile = make_profile(tmp_path)
    state = {
        "target_position": np.array([0.2, 0.1, 0.8]),
        "object_quaternion": np.array([0.0, 0.0, 0.0, 1.0]),
        "object_size": np.array([0.04, 0.04, 0.12]),
    }
    from scipy.spatial.transform import Rotation
    target = _pour_controller_target(
        state, profile, np, Rotation,
        {"axis": [0.0, 0.0, 1.0], "origin_m": [0.4, 0.5, 0.9]},
    )
    assert target == pytest.approx([0.4, 0.5, 0.84])


def test_stir_sample_reports_attached_object_and_container_frame_tip(tmp_path):
    from scipy.spatial.transform import Rotation

    profile = make_profile(tmp_path, configured_process_type="stir")
    from dataclasses import replace
    profile = replace(profile, source_control_path="/World/glass_rod/Cylinder")
    backend = module.LabUtopiaBackend(profile)
    state = {
        "feedback_object_position": np.array([0.3, -0.2, 0.8]),
        "object_position": np.array([0.3, -0.2, 0.8]),
        "object_quaternion": Rotation.identity().as_quat(),
        "object_size": np.array([0.02, 0.02, 0.2]),
        "target_position": np.array([0.3, -0.2, 0.75]),
        "container_quaternion": Rotation.identity().as_quat(),
        "tool_tip_position": np.array([0.31, -0.2, 0.75]),
        "grasped_object_path": "/World/glass_rod/Cylinder",
        "joint_positions": np.array([0.0] * 7 + [0.02, 0.02]),
        "gripper_position": np.array([0.3, -0.2, 0.8]),
    }
    sample = backend._sample(
        state, np.array([0.3, -0.2, 0.8]), Rotation.identity().as_quat(), 1.0,
        np, Rotation, "stirring", process_parameters={"process_type": "stir", "magnitude": 0.01},
    )
    assert sample["grasp_valid"] is True
    assert sample["tool_tip_x_m"] == pytest.approx(0.01)
    assert sample["tool_tip_y_m"] == pytest.approx(0.0)
    assert sample["tool_tip_depth_m"] == pytest.approx(0.04)
    assert sample["tool_tip_frame_id"] == profile.tool_tip_frame_id
    assert sample["feedback_valid"] is True


def test_stir_profile_keeps_control_path_separate_from_entity_path(tmp_path):
    profile = make_profile(tmp_path, configured_process_type="stir")
    from dataclasses import replace
    profile = replace(profile, source_control_path="/World/glass_rod/Cylinder")
    assert profile.source_path == "/World/conical_bottle03"
    assert profile.source_control_path == "/World/glass_rod/Cylinder"


def test_backend_dry_run_never_starts_simulation(tmp_path):
    profile = make_profile(tmp_path)
    arguments = profile.paos_input({"parameters": {
        "process_type": "stir", "engagement": "tool", "hold_s": 0.5,
        "transform": {"mode": "rotation", "axis": [0, 0, 1], "magnitude": 0.01,
                      "speed": 2.0, "direction": "cw", "tolerance": 0.01},
    }}, operation="manipulation_cycle")
    result = module.LabUtopiaBackend(profile).dry_run_cycle(arguments)
    assert result["status"] == "unsupported"
    assert result["motion_authorized"] is False
    assert result["world_change_started"] is False
    assert result["failure_code"] == "unsupported_controller"


def test_generic_pour_rejects_parameters_not_exposed_by_controller(tmp_path):
    profile = make_profile(tmp_path)
    arguments = profile.paos_input({"parameters": {
        "process_type": "pour", "hold_s": 0.5,
        "transform": {"mode": "rotation", "axis": [0, 0, 1], "magnitude": 0.8,
                      "speed": 0.4, "direction": "cw", "tolerance": 0.05},
    }}, operation="manipulation_cycle")
    result = module.LabUtopiaBackend(profile).dry_run_cycle(arguments)
    assert result["status"] == "unsupported"
    assert set(result["unsupported"]) == {"axis", "magnitude", "tolerance", "hold_s"}


def test_cap_operation_returns_explicit_unsupported_controller(tmp_path):
    profile = make_profile(tmp_path, configured_process_type="cap_unscrew")
    arguments = profile.paos_input({"parameters": {
        "process_type": "cap_unscrew", "hold_s": 0.5,
        "transform": {"mode": "rotation", "axis": [0, 0, 1], "magnitude": 1.0,
                      "speed": 0.4, "direction": "ccw", "tolerance": 0.05},
    }}, operation="manipulation_cycle")
    result = module.LabUtopiaBackend(profile).dry_run_cycle(arguments)
    assert result["status"] == "unsupported"
    assert result["failure_code"] == "unsupported_controller"
    assert result["motion_authorized"] is False


def test_generic_worker_events_always_expose_all_seven_phases():
    empty = _generic_phase_events([], process_completed=False, process_type="stir")
    assert [event["phase"] for event in empty] == [
        "acquire", "transport", "process", "reorient_exit", "stow", "release", "retreat"
    ]
    failed = _failed_events("process", [{"timestamp_s": 1.0}], "controller_not_completed")
    assert [event["phase"] for event in failed] == [
        "acquire", "transport", "process", "reorient_exit", "stow", "release", "retreat"
    ]
    assert failed[2]["status"] == "failed"
    assert failed[3]["status"] == "unknown"


def test_generic_worker_does_not_synthesize_post_process_success():
    samples = [{
        "timestamp_s": 1.0,
        "controller_phase": "stirring",
        "transform_progress": 0.01,
    }]
    events = _generic_phase_events(samples, process_completed=True, process_type="stir")
    assert events[2]["status"] == "completed"
    assert all(events[index]["status"] == "unknown" for index in (0, 1, 3, 4, 5, 6))


def test_generic_result_rejects_process_only_completion(tmp_path):
    profile = make_profile(tmp_path, configured_process_type="stir")
    arguments = profile.paos_input(operation="stir_cycle")
    samples = [{"timestamp_s": 1.0, "possession_state": "empty"}]
    events = _generic_phase_events(samples, process_completed=True, process_type="stir")
    result = _generic_result(arguments, samples, events, {"process_type": "stir"}, profile, {}, 1)
    assert result["status"] == "failed"
    assert result["outcome_known"] is True
    assert result["failure_code"] == "incomplete_cycle_phases"
    assert result["incomplete_phases"] == [
        "acquire", "transport", "reorient_exit", "stow", "release", "retreat"
    ]


def test_stir_phase_events_require_observed_grasp_motion_turns_and_release(tmp_path):
    profile = make_profile(tmp_path, configured_process_type="stir")
    from dataclasses import replace
    profile = replace(profile, stir_turns=1.0, stir_duration_s=2.0, stir_radius_m=0.01)
    samples = [
        {"timestamp_s": 1.0, "controller_phase": "acquiring", "grasp_valid": True,
         "target_container_aligned": False, "transform_progress": 0.0,
         "stir_angle_rad": 0.0, "possession_state": "holding"},
        {"timestamp_s": 2.0, "controller_phase": "transporting", "grasp_valid": True,
         "target_container_aligned": True, "transform_progress": 0.0,
         "stir_angle_rad": 0.0, "possession_state": "holding"},
        *_stir_process_samples(0.01, 0.04, 2.1, 2.0, 1.0),
        {"timestamp_s": 4.5, "controller_phase": "reorient_exit", "grasp_valid": True,
         "target_container_aligned": False, "transform_progress": 0.0,
         "stir_angle_rad": 2.0 * np.pi, "possession_state": "holding"},
        {"timestamp_s": 5.0, "controller_phase": "stowing", "grasp_valid": True,
         "target_container_aligned": False, "transform_progress": 0.0,
         "stow_completed": True, "object_support_state": "on_support",
         "stir_angle_rad": 2.0 * np.pi, "possession_state": "holding"},
        {"timestamp_s": 5.1, "controller_phase": "retreat", "grasp_valid": False,
         "target_container_aligned": False, "transform_progress": 0.0,
         "stow_completed": True, "release_confirmed": True,
         "retreat_completed": True, "object_support_state": "on_support",
         "stir_angle_rad": 2.0 * np.pi, "possession_state": "empty"},
    ]
    events = _stir_phase_events(samples, process_completed=True, process_type="stir", profile=profile,
                                process_parameters={"turns": 1.0, "duration_s": 2.0, "radius_m": 0.01})
    assert [event["status"] for event in events] == ["completed"] * 7
    assert events[2]["facts"]["stir_angle_rad"] >= events[2]["facts"]["required_stir_angle_rad"]


def test_stir_return_phases_stay_unknown_without_support_observation(tmp_path):
    profile = make_profile(tmp_path, configured_process_type="stir")
    from dataclasses import replace
    profile = replace(profile, stir_turns=1.0, stir_duration_s=2.0, stir_radius_m=0.01)
    samples = [
        {"timestamp_s": 1.0, "controller_phase": "acquiring", "grasp_valid": True,
         "target_container_aligned": False, "transform_progress": 0.0,
         "stir_angle_rad": 0.0, "possession_state": "holding"},
        {"timestamp_s": 2.0, "controller_phase": "transporting", "grasp_valid": True,
         "target_container_aligned": True, "transform_progress": 0.0,
         "stir_angle_rad": 0.0, "possession_state": "holding"},
        *_stir_process_samples(0.01, 0.04, 2.1, 2.0, 1.0),
        {"timestamp_s": 4.5, "controller_phase": "reorient_exit", "grasp_valid": True,
         "target_container_aligned": False, "transform_progress": 0.0,
         "stir_angle_rad": 2.0 * np.pi, "possession_state": "holding"},
        {"timestamp_s": 5.0, "controller_phase": "stowing", "grasp_valid": True,
         "target_container_aligned": False, "transform_progress": 0.0,
         "stow_completed": True, "object_support_state": "unknown",
         "stir_angle_rad": 2.0 * np.pi, "possession_state": "holding"},
        {"timestamp_s": 5.1, "controller_phase": "retreat", "grasp_valid": False,
         "target_container_aligned": False, "transform_progress": 0.0,
         "stow_completed": True, "release_confirmed": True,
         "retreat_completed": True, "object_support_state": "unknown",
         "stir_angle_rad": 2.0 * np.pi, "possession_state": "empty"},
    ]
    events = _stir_phase_events(samples, process_completed=True, process_type="stir", profile=profile,
                                process_parameters={"turns": 1.0, "duration_s": 2.0, "radius_m": 0.01})
    assert events[2]["status"] == "completed"
    assert [event["status"] for event in events[3:]] == ["completed", "unknown", "unknown", "unknown"]


def test_stir_phase_events_fail_without_measured_turns(tmp_path):
    profile = make_profile(tmp_path, configured_process_type="stir")
    samples = [{
        "timestamp_s": 1.0, "controller_phase": "stirring", "grasp_valid": True,
        "target_container_aligned": True, "transform_progress": profile.stir_radius_m,
        "stir_angle_rad": 0.0, "possession_state": "holding",
    }]
    events = _stir_phase_events(samples, process_completed=True, process_type="stir", profile=profile)
    assert events[2]["status"] == "failed"
    assert events[2]["facts"]["failure_reason"] == "stir_observation_not_qualified"


def test_stir_feedback_requires_requested_tip_radius_depth_direction_and_duration(tmp_path):
    from dataclasses import replace

    profile = replace(make_profile(tmp_path, configured_process_type="stir"),
                      stir_radius_m=0.01, stir_depth_m=0.04, stir_turns=1.0,
                      stir_duration_s=2.0)
    parameters = {"radius_m": 0.01, "depth_m": 0.04, "turns": 1.0,
                  "duration_s": 2.0, "direction": "ccw"}
    valid = _stir_process_samples(0.01, 0.04, 0.0, 2.0, 1.0)
    assert _stir_trace_metrics(valid, parameters, profile)["qualified"] is True
    assert _stir_trace_metrics(_stir_process_samples(0.049, 0.03, 0.0, 4.0, 2.0), parameters, profile)["qualified"] is False
    assert _stir_trace_metrics(_stir_process_samples(0.01, 0.04, 0.0, 4.0, -1.0), parameters, profile)["qualified"] is False
    assert _stir_trace_metrics(_stir_process_samples(0.01, 0.04, 0.0, 1.0, 1.0), parameters, profile)["qualified"] is False


def test_stir_target_compensates_measured_rod_tip_offset():
    offset = _stir_tip_offset([0.2, 0.4, 0.6], [0.15, 0.37, 0.58], np)
    target = _stir_controller_target([1.0, 2.0, 3.0], offset, np)
    assert np.allclose(target, [0.95, 1.97, 2.98])
    assert _stir_tip_offset(None, [0.0, 0.0, 0.0], np) is None


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


def test_feedback_uses_observed_gripper_and_lift_state(tmp_path):
    from scipy.spatial.transform import Rotation

    profile = make_profile(tmp_path)
    backend = module.LabUtopiaBackend(profile)
    state = {
        "object_position": np.array([0.4, 0.2, 0.30]),
        "target_position": np.array([0.4, 0.2, 0.45]),
        "object_quaternion": Rotation.identity().as_quat(),
        "object_size": np.array([0.1, 0.1, 0.2]),
        "gripper_position": np.array([0.4, 0.2, 0.30]),
        "joint_positions": np.array([0.0] * 7 + [0.02, 0.02]),
    }
    sample = backend._sample(
        state,
        np.array([0.4, 0.2, 0.20]),
        Rotation.identity().as_quat(),
        1.0,
        np,
        Rotation,
        "picking",
    )
    assert sample["controller_phase"] == "picking"
    assert sample["gripper_state"] == "closed"
    assert sample["object_lifted"] is True
    assert sample["possession_state"] == "holding"
    assert sample["grasp_valid"] is True


def test_video_recorder_persists_camera_frame(tmp_path):
    cv2 = pytest.importorskip("cv2")
    recorder = _EpisodeVideoRecorder(tmp_path / "episode.mp4", cv2, np, fps=10.0)
    recorder.write({"front": np.zeros((3, 16, 16), dtype=np.uint8)}, ("phase=failed",))
    recorder.close()
    metadata = recorder.metadata()
    assert metadata["video_frame_count"] == 1
    assert metadata["video_available"] is True


def test_inprocess_exception_preserves_video_metadata(tmp_path, monkeypatch):
    class FakeApp:
        def __init__(self, config):
            self.config = config

        def close(self):
            return None

    fake_isaacsim = types.ModuleType("isaacsim")
    fake_isaacsim.SimulationApp = FakeApp
    monkeypatch.setitem(sys.modules, "isaacsim", fake_isaacsim)

    profile = make_profile(tmp_path)
    backend = module.LabUtopiaBackend(profile)

    def fail_episode(app, arguments, cancel, video_path):
        backend._last_video_info = {
            "video_path": str(video_path),
            "video_frame_count": 3,
            "video_available": True,
        }
        raise RuntimeError("episode failed")

    monkeypatch.setattr(backend, "_run_episode", fail_episode)
    result_path = tmp_path / "result.json"
    result = backend._run_inprocess({}, Event(), result_path)
    assert result["status"] == "unknown"
    assert result["video_frame_count"] == 3
    assert json.loads(result_path.read_text(encoding="utf-8"))["video_available"] is True
