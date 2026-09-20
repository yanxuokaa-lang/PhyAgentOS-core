from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest
import robotwin_contact_qualification as contact

from robotwin20_adapter.preparation_deadline import (
    PreparationDeadline,
    PreparationDeadlineExceededError,
)


def inputs():
    pose = {"frame_id": "world", "position_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]}
    candidate = {"candidate_ref": "candidate://observed/0", "execution_grasp": {
        "robot_target_pose": pose, "contact_center_pose": {**pose, "position_m": [0., 0., .04]},
        "ingress_direction": {"vector": [0., 0., -1.]}},
        "route": [{"waypoints": [{**pose, "position_m": [0., 0., .08]}]}]}
    geometry = {"schema_version": "paos-robotwin20-grasp-contact-geometry/v1", "frame_id": "world",
        "scene_revision": "unused", "motion_authorized": False,
        "support_plane": {"normal": [0., 0., 1.], "offset_m": -.1}, "arms": {}}
    for arm in ("left", "right"):
        geometry["arms"][arm] = {"reference_hand_pose": {
            "frame_id": "world", "position_m": [0., 0., 0.], "orientation_wxyz": [1., 0., 0., 0.]},
            "links": {"panda_hand": [[-.03, -.05, -.02], [.03, .05, 0]],
                      "panda_leftfinger": [[-.01, -.05, .01], [.01, -.04, .06]],
                      "panda_rightfinger": [[-.01, .04, .01], [.01, .05, .06]]}}
    model = np.eye(4)
    model[2, 3] = .04
    record = {"world_T_object": model.reshape(-1).tolist(), "half_extents_m": [.01, .02, .01]}
    adaptation = {"robot_target_reference_distance_m": .12, "robot_gripper_bias_m": .12,
                  "robot_delta_matrix": np.eye(3).tolist(), "contact_backoff_candidates_m": [0., .005]}
    return candidate, geometry, record, adaptation


def test_qualification_uses_profile_variants_and_retains_per_arm_results(monkeypatch):
    candidate, geometry, record, adaptation = inputs()
    before = deepcopy(candidate)
    monkeypatch.setattr(contact, "capture_task_geometry", lambda *args: deepcopy(geometry))
    calls = []
    def evaluate(task, grasp, arm, clearance):
        calls.append((arm, grasp["robot_target_pose"]["position_m"][2], clearance))
        return {"planner_status": "success" if arm == "right" else "failed", "clearance_m": .01 if arm == "right" else None}
    monkeypatch.setattr(contact, "evaluate_contact", evaluate)
    result = contact.qualify_observed_contact(None, {"scene_revision": "scene"}, candidate, record,
                                             adaptation, ["left", "right"], PreparationDeadline.start(10), runtime_profile={})
    assert result["status"] == "qualified"
    assert result["arm_id"] == "right"
    assert result["qualification"]["selected_backoff_m"] == 0.
    assert len(result["arm_attempts"]) == 2
    assert calls == [("left", 0., .08), ("left", .005, .08), ("right", 0., .08), ("right", .005, .08)]
    assert candidate == before
    assert result["motion_authorized"] is False


def test_oversized_observed_object_rejects_before_planner(monkeypatch):
    candidate, geometry, record, adaptation = inputs()
    record["half_extents_m"] = [.1, .1, .1]
    monkeypatch.setattr(contact, "capture_task_geometry", lambda *args: geometry)
    monkeypatch.setattr(contact, "evaluate_contact", lambda *args: pytest.fail("invalid pinch must not call IK"))
    result = contact.qualify_observed_contact(None, {"scene_revision": "scene"}, candidate, record,
                                             adaptation, ["right"], PreparationDeadline.start(10), runtime_profile={})
    assert result["status"] == "unavailable"
    assert all("finger_envelope_rejected" in v["rejection_reasons"] for v in result["arm_attempts"][0]["qualification"]["variants"])


def test_expired_budget_cannot_produce_qualification(monkeypatch):
    candidate, geometry, record, adaptation = inputs()
    monkeypatch.setattr(contact, "capture_task_geometry", lambda *args: geometry)
    with pytest.raises(PreparationDeadlineExceededError):
        contact.qualify_observed_contact(None, {"scene_revision": "scene"}, candidate, record,
                                        adaptation, ["right"], PreparationDeadline(0), runtime_profile={})


@pytest.mark.parametrize("clearance,expected", [(None, "unavailable"), (-.001, "unavailable"),
                                               (float("nan"), "unavailable"), (float("inf"), "unavailable"),
                                               (0., "qualified")])
def test_observed_contact_requires_finite_nonnegative_planner_clearance(monkeypatch, clearance, expected):
    candidate, geometry, record, adaptation = inputs()
    monkeypatch.setattr(contact, "capture_task_geometry", lambda *args: geometry)
    mesh = {"variants": [{"backoff_m": 0., "status": "valid", "rejection_reasons": [],
                          "robot_target_position_m": [0., 0., 0.], "contact_center_position_m": [0., 0., .04]}]}
    monkeypatch.setattr(contact, "qualify_point_contact", lambda *args: deepcopy(mesh))
    monkeypatch.setattr(contact, "evaluate_contact", lambda *args: {"planner_status": "success", "clearance_m": clearance})
    task = SimpleNamespace(_paos_observed_collision={})
    result = contact.qualify_observed_contact(task, {"scene_revision": "scene"}, candidate, record,
                                             adaptation, ["right"], PreparationDeadline.start(10), runtime_profile={})
    assert result["status"] == expected
    if expected == "unavailable":
        assert result["arm_attempts"][0]["qualification"]["variants"][0]["rejection_reasons"] == ["contact_clearance_unproven_or_negative"]
