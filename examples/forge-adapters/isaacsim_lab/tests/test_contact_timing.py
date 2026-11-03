"""Exercise controller changes with measured replacement plant feedback."""
from copy import deepcopy
from threading import Event
from types import SimpleNamespace

import numpy as np
import pytest
from test_phase_motion import execution_fixture

from isaacsim_lab.phase_motion import PhaseMotionError, smooth_joint_segment


def contact_sensors(model, active):
    def frame():
        return {"time": model.world.current_time,
                "contacts": [{"body0": "/World/source/mesh", "body1": "/finger",
                              "impulse": [0., .001, 0.], "position": [.1, 0., .9], "normal": [0., 1., 0.]}]
                if active() else []}
    model.sensors = [SimpleNamespace(get_current_frame=frame)] * 2


def timed_contact_sensors(model, load_at_step):
    """Hold one immutable sensor frame for each simulated control interval."""
    def sensor_frame(side):
        def frame():
            mode = load_at_step(model.world.steps)
            if mode == "stale_right" and side == 1:
                timestamp = model.world.current_time - 1.
            else:
                timestamp = model.world.current_time
            present = mode != "missing_right" or side == 0
            loaded = mode == "bilateral" or (mode == "unilateral_left" and side == 0)
            contacts = ([{"body0": "/World/source/mesh", "body1": f"/finger/{side}",
                          "impulse": [0., .001 if loaded else 0., 0.],
                          "position": [.1, 0., .9], "normal": [0., 1., 0.]}]
                        if present else [])
            return {"time": timestamp, "contacts": contacts}
        return frame

    model.sensors = [SimpleNamespace(get_current_frame=sensor_frame(side)) for side in range(2)]

    def step(**_kwargs):
        model.world.current_time += model.dt
        model.world.steps += 1
        model._test_positions_ref[:] = model._test_commands_ref[-1]
        for callback in model.world.physics_callbacks.values():
            callback(model.dt)

    model.world.step = step


def test_closure_ramps_then_holds_contact_target_through_lift(monkeypatch):
    model, args, commands, artifacts = execution_fixture(monkeypatch)
    contact_sensors(model, lambda: model.robot.get_joint_positions()[7] < .025)
    model.execute(args, Event())
    samples = artifacts[-1][1]["samples"]
    close = [s for s in samples if s["stage"] == "close"]
    q = np.array([[.04, .04], *[s["finger_target_m"] for s in close]])
    assert np.max(np.abs(np.diff(q, axis=0))) / model.dt <= model.config["finger_velocity_m_s"]
    assert close[-1]["finger_target_m"][0] > .02  # Never crush the established grip toward zero.
    lift = [s for s in samples if s["stage"] == "lift"]
    assert lift
    assert all(s["finger_target_m"] == close[-1]["finger_target_m"] for s in lift)
    assert close[-1]["selected_contacts"][0][0]["contacts"][0]["normal"] == [0., 1., 0.]
    assert all(np.min(c[7:]) > .02 for c in commands)


@pytest.mark.parametrize("stage", ["grasp", "close"])
def test_object_displacement_stops_insertion_or_closure_before_lift(monkeypatch, stage):
    model, args, commands, artifacts = execution_fixture(monkeypatch)
    args["phase_route"]["steps"][0]["stage"] = stage
    original = model.body_pose("/World/source")
    def pose(_):
        value = original.copy()
        if model.world.steps:
            value[0, 3] += .009
        return value
    model.body_pose = pose
    contact_sensors(model, lambda: True)
    result = model.execute(args, Event())
    assert result["failure_code"] == "grasp_object_displaced"
    assert model.world.steps == 1
    assert all(c[0] == 0 for c in commands)
    assert not result["operation_completed"]


def test_transient_bilateral_contact_does_not_authorize_lift(monkeypatch):
    model, args, commands, artifacts = execution_fixture(monkeypatch)
    contact_sensors(model, lambda: 2 <= model.world.steps <= 4)
    result = model.execute(args, Event())
    assert result["failure_code"] == "physical_grasp_lost"
    assert model.world.steps < 10
    assert all(c[0] == 0 for c in commands)
    assert not result["operation_completed"]


def test_one_unloaded_lift_interval_is_execution_tolerance_not_grasp_evidence(monkeypatch):
    model, args, _commands, artifacts = execution_fixture(monkeypatch)
    # Closure stabilizes for ten intervals; the first lift interval unloads one
    # finger, then bilateral load returns on the next interval.
    timed_contact_sensors(model, lambda step: "unilateral_left" if step == 11 else "bilateral")
    result = model.execute(args, Event())
    samples = artifacts[-1][1]["samples"]
    transient = next(sample for sample in samples if sample.get("support_manifold_continuity_used"))
    assert transient["stage"] == "lift"
    assert transient["grasp_valid"] is False
    assert transient["contact_load_valid"] is False
    later_lift = [sample for sample in samples if sample["stage"] == "lift" and sample is not transient]
    assert later_lift and later_lift[0]["grasp_valid"] is True
    assert result["failure_code"] != "physical_grasp_lost"
    assert model.world.steps >= 12


def test_later_in_support_unloaded_lift_interval_recovers(monkeypatch):
    model, args, _commands, artifacts = execution_fixture(monkeypatch)
    # Real PhysX evidence can retain bilateral load for several lift intervals
    # before one finger unloads while the vessel is still leaving its support.
    model._time_acquire_route(args["phase_route"])
    timed_contact_sensors(model, lambda step: "unilateral_left" if step == 18 else "bilateral")
    result = model.execute(args, Event())
    samples = artifacts[-1][1]["samples"]
    transient = next(sample for sample in samples if sample.get("support_manifold_continuity_used"))
    assert transient["stage"] == "lift"
    assert transient["grasp_valid"] is False
    assert transient["contact_load_valid"] is False
    assert result["failure_code"] != "physical_grasp_lost"


def test_later_unloaded_lift_interval_outside_support_window_stops(monkeypatch):
    model, args, _commands, artifacts = execution_fixture(monkeypatch)
    monkeypatch.setattr("isaacsim_lab.phase_motion.support_contact_allowed", lambda *_args: False)
    model._time_acquire_route(args["phase_route"])
    timed_contact_sensors(model, lambda step: "unilateral_left" if step == 18 else "bilateral")
    result = model.execute(args, Event())
    samples = artifacts[-1][1]["samples"]
    assert result["failure_code"] == "physical_grasp_lost"
    assert not any(sample.get("support_manifold_continuity_used") for sample in samples)


def test_static_bilateral_manifold_can_bridge_support_departure(monkeypatch):
    model, args, _commands, artifacts = execution_fixture(monkeypatch)
    model._time_acquire_route(args["phase_route"])

    def load(step):
        if step == 18:
            return "unilateral_left"
        if step == 19:
            return "bilateral_unloaded"
        return "bilateral"

    timed_contact_sensors(model, load)
    monkeypatch.setattr(
        "isaacsim_lab.phase_motion.support_contact_allowed",
        lambda *_args: model.world.steps <= 19,
    )
    result = model.execute(args, Event())
    samples = artifacts[-1][1]["samples"]
    continuity = [sample for sample in samples if sample.get("support_manifold_continuity_used")]
    assert np.asarray(
        [sample["selected_contact_impulse_ns"] for sample in continuity]
    ) == pytest.approx(np.asarray([[.001, 0.], [0., 0.]]))
    assert all(sample["contact_manifold_valid"] for sample in continuity)
    assert all(sample["grasp_valid"] is False for sample in continuity)
    assert all(sample["contact_load_valid"] is False for sample in continuity)
    assert result["failure_code"] != "physical_grasp_lost"


def test_persistent_unilateral_manifold_stops_after_support_departure(monkeypatch):
    model, args, _commands, artifacts = execution_fixture(monkeypatch)
    timed_contact_sensors(
        model,
        lambda step: "bilateral" if step < 11 else "unilateral_left",
    )
    monkeypatch.setattr(
        "isaacsim_lab.phase_motion.support_contact_allowed",
        lambda *_args: model.world.steps <= 11,
    )
    result = model.execute(args, Event())
    lift_samples = [sample for sample in artifacts[-1][1]["samples"] if sample["stage"] == "lift"]
    assert result["failure_code"] == "physical_grasp_lost"
    assert lift_samples[0]["support_manifold_continuity_used"] is True
    assert not lift_samples[1].get("support_manifold_continuity_used")


@pytest.mark.parametrize("mode", ["bilateral_unloaded", "missing_right", "stale_right"])
def test_unqualified_unloaded_lift_interval_stops(monkeypatch, mode):
    model, args, _commands, artifacts = execution_fixture(monkeypatch)
    timed_contact_sensors(model, lambda step: "bilateral" if step < 11 else mode)
    if mode == "bilateral_unloaded":
        monkeypatch.setattr("isaacsim_lab.phase_motion.support_contact_allowed", lambda *_args: False)
    result = model.execute(args, Event())
    lift_samples = [sample for sample in artifacts[-1][1]["samples"] if sample["stage"] == "lift"]
    assert result["failure_code"] == "physical_grasp_lost"
    assert len(lift_samples) == 1
    assert lift_samples[0]["grasp_valid"] is False
    assert not lift_samples[0].get("support_manifold_continuity_used")
    assert not result["operation_completed"]


def test_static_manifold_with_excessive_grasp_drift_stops(monkeypatch):
    model, args, _commands, artifacts = execution_fixture(monkeypatch)
    original = model.body_pose("/World/source")

    def pose(_path):
        value = original.copy()
        if model.world.steps >= 11:
            value[0, 3] += model.config["grasp_position_tolerance_m"] + .001
        return value

    model.body_pose = pose
    timed_contact_sensors(
        model,
        lambda step: "bilateral" if step < 11 else "bilateral_unloaded",
    )
    result = model.execute(args, Event())
    lift_samples = [sample for sample in artifacts[-1][1]["samples"] if sample["stage"] == "lift"]
    assert result["failure_code"] == "physical_grasp_lost"
    assert lift_samples[0]["contact_manifold_valid"] is True
    assert lift_samples[0]["attachment_position_error_m"] > model.config["grasp_position_tolerance_m"]
    assert not lift_samples[0].get("support_manifold_continuity_used")


def test_unilateral_contact_during_initial_closure_never_authorizes_lift(monkeypatch):
    model, args, _commands, artifacts = execution_fixture(monkeypatch)
    timed_contact_sensors(model, lambda _step: "unilateral_left")
    result = model.execute(args, Event())
    samples = artifacts[-1][1]["samples"]
    assert result["failure_code"] == "grasp_not_confirmed"
    assert all(sample["stage"] != "lift" for sample in samples)
    assert not any(sample.get("support_manifold_continuity_used") for sample in samples)


def test_no_contact_closure_stops_at_bounded_budget(monkeypatch):
    model, args, commands, _ = execution_fixture(monkeypatch)
    result = model.execute(args, Event())
    assert result["failure_code"] == "grasp_not_confirmed"
    assert 0 < model.world.steps < model.config["max_execution_steps"]
    q = np.array([[.04, .04], *[c[7:] for c in commands]])
    # The last command is measured hold after failure, not another closure retry.
    assert np.max(np.abs(np.diff(q, axis=0))) / model.dt <= model.config["finger_velocity_m_s"]


def timing_route(model, args):
    route = deepcopy(args["phase_route"])
    template = route["steps"][0]
    route["steps"] = [{**template, "stage": "transit_cross", "allow_contact": False,
                       "joints": [float(x), 0., 0., 0., 0., 0., 0.], "hold_s": 0.}
                      for x in np.linspace(.005, .25, 50)]
    route["steps"][-1]["hold_s"] = .2
    return route


def test_retiming_keeps_holds_checks_path_and_removes_intermediate_stops(monkeypatch):
    model, args, commands, _ = execution_fixture(monkeypatch)
    route = timing_route(model, args)
    checks = []
    model._collisions = lambda q, *a, **kw: checks.append(q.copy())
    model._time_acquire_route(route)
    samples = np.array([[0.] * 7, *[p["joints"] for p in route["execution_steps"]], [.25, 0, 0, 0, 0, 0, 0]])
    velocity = np.diff(samples, axis=0) / model.dt
    acceleration = np.diff(velocity, axis=0) / model.dt
    assert np.max(np.abs(velocity)) <= model.config["joint_velocity_rad_s"] * 1.001
    assert np.max(np.abs(acceleration)) <= model.config["joint_acceleration_rad_s2"] * 1.001
    assert all(p["continuous"] for p in route["execution_steps"])
    assert sum(p["hold_s"] for p in route["execution_steps"]) == .2
    legacy = sum(len(list(smooth_joint_segment(a, b, model.dt, .4, .8)))
                 for a, b in zip([[0.] * 7, *[p["joints"] for p in route["steps"]]],
                                 [p["joints"] for p in route["steps"]]))
    assert len(samples) < legacy / 2
    assert len(checks) >= len(route["execution_steps"])
    assert not commands and model.world.steps == 0


@pytest.mark.parametrize("failure", ["collision", "workspace", "limits"])
def test_unsafe_retimed_samples_fail_before_commands(monkeypatch, failure):
    model, args, commands, _ = execution_fixture(monkeypatch)
    route = timing_route(model, args)
    if failure == "collision":
        def reject(q, *a, **kw):
            if .11 < q[0] < .14:
                raise PhaseMotionError("route_collision", "new interpolation hits obstacle")
        model._collisions = reject
    elif failure == "workspace":
        model.config["workspace_max_m"][2] = .95
    else:
        model.limits[0, 1] = .1
    with pytest.raises(PhaseMotionError):
        model._time_acquire_route(route)
    assert not commands and model.world.steps == 0
    assert "execution_steps" not in route


def test_changed_retiming_period_fails_before_command(monkeypatch):
    model, args, commands, _ = execution_fixture(monkeypatch)
    args["phase_route"]["execution_steps"] = []
    args["phase_route"]["execution_dt_s"] = .1
    result = model.execute(args, Event())
    assert result["failure_code"] == "stale_phase_route"
    assert not commands and model.world.steps == 0


def test_bilateral_misaligned_contact_stops_without_further_squeezing(monkeypatch):
    model, args, commands, _ = execution_fixture(monkeypatch)
    args["phase_route"]["tcp_from_object"][0][3] += .009
    contact_sensors(model, lambda: True)
    result = model.execute(args, Event())
    assert result["failure_code"] == "grasp_transform_mismatch"
    assert model.world.steps == 1
    assert all(c[7] > .039 for c in commands)


def test_cancellation_during_closure_holds_and_never_starts_lift(monkeypatch):
    model, args, commands, _ = execution_fixture(monkeypatch)
    cancel = Event()
    step = model.world.step
    def cancel_after_step(**kwargs):
        step(**kwargs)
        cancel.set()
    model.world.step = cancel_after_step
    result = model.execute(args, cancel)
    assert result["failure_code"] == "cancelled"
    assert model.world.steps == 1
    assert all(c[0] == 0 for c in commands)
    assert np.array_equal(commands[-1], model.robot.get_joint_positions())
    assert not model.world.physics_callbacks


def test_execution_consumes_qualified_samples_without_resmoothing(monkeypatch):
    model, args, commands, artifacts = execution_fixture(monkeypatch)
    route = args["phase_route"]
    route["steps"] = [{**route["steps"][0], "stage": "transit_cross", "hold_s": 0.,
                       "allow_contact": False, "joints": [.25, 0., 0., 0., 0., 0., 0.]}]
    model._time_acquire_route(route)
    model.execute(args, Event())
    assert model.world.steps == len(route["execution_steps"])
    assert np.allclose(np.array(commands)[:, :7], [p["joints"] for p in route["execution_steps"]])
    assert len(artifacts[-1][1]["samples"]) == model.world.steps + 1


def test_later_phase_starts_from_measured_finger_aperture(monkeypatch):
    model, args, commands, _ = execution_fixture(monkeypatch)
    original_positions = model.robot.get_joint_positions
    def positions():
        result = original_positions()
        result[7:] = [.021, .022]
        return result
    model.robot.get_joint_positions = positions
    args["operation"] = args["phase_route"]["operation"] = "place"
    args["phase_route"]["steps"] = [{**args["phase_route"]["steps"][0], "stage": "transport"}]
    contact_sensors(model, lambda: True)
    model.execute(args, Event())
    assert commands
    assert all(np.allclose(c[7:], [.021, .022]) for c in commands)
