"""Config-gated safe acquire recovery: command log, driver and injection resolution."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import robotwin_simulation_probe_worker as probe_worker  # noqa: E402
from robotwin_simulation_probe_worker import (  # noqa: E402
    AcquireRecoveryFailedError,
    AcquireSafeRecoveryError,
    recover_acquire_to_observation,
)


class FakeController:
    def __init__(self):
        self.commands = []

    def command(self, position, velocity):
        self.commands.append(list(position))

    def before_step(self):
        return None

    def after_step(self):
        return None

    def stop(self):
        return None


class FakePose:
    def __init__(self, z):
        self.p = [0.0, 0.0, z]


class FakeActor:
    def __init__(self, z, name="block"):
        self._z = z
        self._name = name

    def get_pose(self):
        return FakePose(self._z)

    def get_name(self):
        return self._name


@pytest.fixture()
def recovery_env(monkeypatch):
    controller = FakeController()
    gripper_calls = []
    monkeypatch.setattr(probe_worker, "_set_gripper",
                        lambda *args, **kwargs: gripper_calls.append(kwargs.get("phase")))
    monkeypatch.setattr(probe_worker, "_step_bounded_controller", lambda *args, **kwargs: None)
    monkeypatch.setattr(probe_worker, "_capture_probe_video", lambda *args, **kwargs: None)
    monkeypatch.setattr(probe_worker, "_guard_execution_inputs", lambda *args, **kwargs: None)
    monkeypatch.setattr(probe_worker, "_guard_controller_source_digest", lambda *args, **kwargs: None)
    monkeypatch.setattr(probe_worker, "_contact_state", lambda *args, **kwargs: [])
    monkeypatch.setattr(probe_worker, "_table_top_z", lambda task: 0.74)
    actor = FakeActor(z=0.76)
    monkeypatch.setattr(probe_worker, "_actor_for_entity", lambda task, ref: actor)
    arm_entity = SimpleNamespace(get_links=lambda: [])
    robot = SimpleNamespace(left_entity=arm_entity, right_entity=arm_entity, gripper_name=["left_finger"])
    task = SimpleNamespace(robot=robot)
    return SimpleNamespace(controller=controller, gripper_calls=gripper_calls, actor=actor,
                           task=task, monkeypatch=monkeypatch)


def _state(log, controller):
    return {
        "_executed_arm_commands": log,
        "_controllers": {"left": controller, "right": controller},
        "_artifact_root": Path("/tmp/paos-recovery-test"),
        "_execution_input_digests": {},
        "_controller_source_sha256": "0" * 64,
        "contact_trace": [],
        "simulator_steps": 0,
    }


def test_recovery_reverses_command_log_and_returns_clearance(recovery_env):
    log = [
        {"arm": "left", "phase": "approach", "position": [0.0, 0.0]},
        {"arm": "left", "phase": "close", "position": [0.2, 0.1]},
        {"arm": "left", "phase": "close", "position": [0.2, 0.1]},
        {"arm": "left", "phase": "lift", "position": [0.2, 0.4]},
    ]
    state = _state(log, recovery_env.controller)
    clearance = recover_acquire_to_observation(
        recovery_env.task, "left", "entity://block", state,
        deadline=1e18, stop_file=None, half_extents=[0.02, 0.02, 0.02],
    )
    # Object bottom 0.76 - 0.02 = 0.74 equals the table top, so the support is proven.
    assert clearance == pytest.approx(0.0)
    assert recovery_env.gripper_calls == ["recovery_open"]
    commands = recovery_env.controller.commands
    # Reverse order, consecutive duplicates skipped, then ten hold steps at the start command.
    assert commands[0] == [0.2, 0.4]
    assert commands[1] == [0.2, 0.1]
    assert commands[2] == [0.0, 0.0]
    assert commands[3:] == [[0.0, 0.0]] * 10
    assert state["_arm_hold_targets"]["left"] == [0.0, 0.0]
    assert state["phase"] == "recovery_retreat"


def test_recovery_fails_closed_without_supported_object(recovery_env):
    recovery_env.actor._z = 0.95  # object far above the table: support unproven
    state = _state([{"arm": "left", "phase": "approach", "position": [0.1]}], recovery_env.controller)
    with pytest.raises(AcquireRecoveryFailedError):
        recover_acquire_to_observation(
            recovery_env.task, "left", "entity://block", state,
            deadline=1e18, stop_file=None, half_extents=[0.02, 0.02, 0.02],
        )


def test_recovery_requires_single_arm_command_log(recovery_env):
    state = _state([
        {"arm": "left", "phase": "approach", "position": [0.1]},
        {"arm": "right", "phase": "approach", "position": [0.1]},
    ], recovery_env.controller)
    with pytest.raises(AcquireRecoveryFailedError):
        recover_acquire_to_observation(
            recovery_env.task, "left", "entity://block", state,
            deadline=1e18, stop_file=None, half_extents=[0.02, 0.02, 0.02],
        )
    empty = _state([], recovery_env.controller)
    with pytest.raises(AcquireRecoveryFailedError):
        recover_acquire_to_observation(
            recovery_env.task, "left", "entity://block", empty,
            deadline=1e18, stop_file=None, half_extents=[0.02, 0.02, 0.02],
        )


def test_recovery_rejects_remaining_gripper_contact(recovery_env):
    contact = [{"pair": ["block", "left:left_finger"], "active_contact": True}]
    recovery_env.monkeypatch.setattr(probe_worker, "_contact_state", lambda *args, **kwargs: contact)
    state = _state([{"arm": "left", "phase": "approach", "position": [0.1]}], recovery_env.controller)
    with pytest.raises(AcquireRecoveryFailedError):
        recover_acquire_to_observation(
            recovery_env.task, "left", "entity://block", state,
            deadline=1e18, stop_file=None, half_extents=[0.02, 0.02, 0.02],
        )


def test_safe_recovery_error_receipt_matches_generic_contract():
    error = AcquireSafeRecoveryError("recovered", measurement={"lift_displacement_m": 0.0})
    assert error.outcome_known is True
    assert error.failure_code == "physical_grasp_lost"
    assert error.failure_owner == "execution"
    assert error.retryable_in_revision is False
    assert error.requires_replan is True
    assert error.recommended_action == "refresh_perception_before_motion"
    assert error.possession_state == "empty"
    assert error.object_support_state == "on_support"
    assert error.returned_to_safe_pose is True
    assert error.observation_ready is True
    assert error.acquisition_measurement == {"lift_displacement_m": 0.0}


def test_recovery_failure_error_stays_unknown_by_default():
    error = AcquireRecoveryFailedError("unproven")
    assert error.failure_code == "acquire_recovery_postcondition_failed"
    assert not hasattr(error, "outcome_known") or error.outcome_known is not False
    assert not hasattr(error, "possession_state")


def test_execute_segment_records_command_log(monkeypatch):
    import numpy as np

    controller = FakeController()
    monkeypatch.setattr(probe_worker, "_step_bounded_controller", lambda *a, **k: None)
    monkeypatch.setattr(probe_worker, "_capture_probe_video", lambda *a, **k: None)
    monkeypatch.setattr(probe_worker, "_contact_state", lambda *a, **k: [])
    monkeypatch.setattr(probe_worker, "_guard_execution_inputs", lambda *a, **k: None)
    monkeypatch.setattr(probe_worker, "_guard_controller_source_digest", lambda *a, **k: None)
    task = SimpleNamespace(
        robot=SimpleNamespace(get_left_ee_pose=lambda: np.zeros(7)),
        scene=SimpleNamespace(get_timestep=lambda: 0.005),
    )
    state = {"_controllers": {"left": controller}, "contact_trace": [], "simulator_steps": 0,
             "_artifact_root": Path("/tmp/paos-recovery-test"), "_execution_input_digests": {},
             "_controller_source_sha256": "0" * 64, "planner_object_attached": False}
    probe_worker._execute_segment(
        task, "left", {"position": [[0.1, 0.2], [0.3, 0.4]], "velocity": [[0.0, 0.0], [0.0, 0.0]]},
        phase="approach", deadline=1e18, stop_file=None, contacts=[], execution_state=state,
    )
    log = state["_executed_arm_commands"]
    assert [entry["position"] for entry in log] == [[0.1, 0.2], [0.3, 0.4]]
    assert all(entry["arm"] == "left" and entry["phase"] == "approach" for entry in log)


def _engine_with(config):
    import robotwin_persistent_engine as engine_module

    engine = object.__new__(engine_module.RoboTwinPersistentEngine)
    from types import MappingProxyType

    engine.profile = {"failure_injection": config}
    engine.backend = SimpleNamespace(snapshot=lambda: MappingProxyType({"scene_revision": "scene-1"}))
    return engine


def test_failure_injection_resolution_is_config_gated():
    assert _engine_with({"enabled": False, "mode": "gripper_close_offset", "close_value": 0.2})._resolve_failure_injection("acquire", "inv-1") is None
    assert _engine_with(None)._resolve_failure_injection("acquire", "inv-1") is None
    assert _engine_with({"enabled": True, "mode": "gripper_close_offset", "close_value": 0.2})._resolve_failure_injection("place", "inv-1") is None
    assert _engine_with({"enabled": True, "mode": "gripper_close_offset", "close_value": 0.2, "probability": 0.0})._resolve_failure_injection("acquire", "inv-1") is None
    resolved = _engine_with({"enabled": True, "mode": "gripper_close_offset", "close_value": 0.2})._resolve_failure_injection("acquire", "inv-1")
    assert resolved == {"mode": "gripper_close_offset", "close_value": 0.2}
    # Deterministic per scene revision and invocation identity.
    again = _engine_with({"enabled": True, "mode": "gripper_close_offset", "close_value": 0.2})._resolve_failure_injection("acquire", "inv-1")
    assert again == resolved
    for bad in (
        {"enabled": True, "mode": "friction", "close_value": 0.2},
        {"enabled": True, "mode": "gripper_close_offset", "close_value": 0.0},
        {"enabled": True, "mode": "gripper_close_offset", "close_value": 1.5},
        {"enabled": True, "mode": "gripper_close_offset", "close_value": 0.2, "probability": 1.5},
    ):
        with pytest.raises(ValueError):
            _engine_with(bad)._resolve_failure_injection("acquire", "inv-1")
