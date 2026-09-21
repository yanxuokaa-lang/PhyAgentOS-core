import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from test_route_readiness import _request

from robotwin20_adapter.persistent_action_approval import (
    PersistentActionApprovalError,
    PersistentSimulationActionApprover,
    validate_persistent_action_approval,
)
from robotwin20_adapter.route_readiness import route_geometry_digest


def _assignment(route):
    return {
        "assignment_ref": "artifact://assignments/task/revision/node",
        "assignment_digest": "a" * 64,
        "candidate_ref": route["candidates"][0]["candidate_ref"],
        "entity_ref": route["candidates"][0]["entity_ref"],
        "scene_revision": route["scene_revision"],
        "route_digest": route_geometry_digest(route),
        "motion_authorized": False,
    }


def test_runtime_monitored_approval_binds_exact_route_and_assignment(tmp_path):
    route = _request(tmp_path)
    assignment = _assignment(route)
    approver = PersistentSimulationActionApprover(
        tmp_path,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
    )
    reference = approver.issue(
        route,
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
        readiness_evidence_refs=["artifact://readiness/right-arm"],
    )
    approval = validate_persistent_action_approval(
        tmp_path,
        reference,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
        route_request=route,
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
    )
    assert approval["simulation_only"] is True
    assert approval["motion_authorized"] is True
    assert approval["required_execution_checks"] == [
        "contact_dynamics",
        "stop_control",
    ]


@pytest.mark.parametrize("change", ["route", "assignment", "mode", "task"])
def test_runtime_monitored_approval_rejects_changed_binding(tmp_path, change):
    route = _request(tmp_path)
    assignment = _assignment(route)
    approver = PersistentSimulationActionApprover(
        tmp_path,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
    )
    reference = approver.issue(
        route,
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
        readiness_evidence_refs=["artifact://readiness/right-arm"],
    )
    current_route = deepcopy(route)
    current_assignment = deepcopy(assignment)
    mode = "runtime_monitored"
    task_name = "blocks_ranking_rgb"
    if change == "route":
        current_route["request_id"] = "another-request"
    elif change == "assignment":
        current_assignment["assignment_digest"] = "b" * 64
    elif change == "mode":
        mode = "disabled"
    else:
        task_name = "another_task"
    with pytest.raises(PersistentActionApprovalError):
        validate_persistent_action_approval(
            tmp_path,
            reference,
            task_name=task_name,
            mode=mode,
            route_request=current_route,
            candidate_ref=assignment["candidate_ref"],
            assignment=current_assignment,
        )


def test_disabled_mode_cannot_issue_approval(tmp_path):
    with pytest.raises(PersistentActionApprovalError, match="runtime_monitored"):
        PersistentSimulationActionApprover(
            tmp_path,
            task_name="blocks_ranking_rgb",
            mode="disabled",
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("authorized_at", "2026-09-21T12:00:00", "timezone"),
        ("authorized_at", "not-a-timestamp", "timestamp"),
        ("readiness_evidence_refs", ["artifact://../escape"], "path is unsafe"),
        ("readiness_evidence_refs", ["not-an-artifact"], "reference is invalid"),
    ],
)
def test_runtime_revalidates_approval_metadata(tmp_path, field, value, message):
    route = _request(tmp_path)
    assignment = _assignment(route)
    approver = PersistentSimulationActionApprover(
        tmp_path,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
    )
    reference = approver.issue(
        route,
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
        readiness_evidence_refs=["artifact://readiness/right-arm"],
    )
    path = tmp_path.joinpath(*reference.removeprefix("artifact://").split("/")).with_suffix(".json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = value
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PersistentActionApprovalError, match=message):
        validate_persistent_action_approval(
            tmp_path,
            reference,
            task_name="blocks_ranking_rgb",
            mode="runtime_monitored",
            route_request=route,
            candidate_ref=assignment["candidate_ref"],
            assignment=assignment,
        )


def test_engine_rejects_changed_approval_before_action_setup(tmp_path):
    from robotwin_persistent_engine import RoboTwinPersistentEngine

    route = _request(tmp_path)
    assignment = {
        **_assignment(route),
        "task_id": "task-1",
        "capability_snapshot_ref": "artifact://capabilities/snapshot",
        "selected_arm_ids": ["right"],
    }
    assignment_path = tmp_path / "assignments" / "task" / "revision" / "node.json"
    assignment_path.parent.mkdir(parents=True)
    assignment_path.write_text(json.dumps(assignment), encoding="utf-8")
    approval_ref = PersistentSimulationActionApprover(
        tmp_path,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
    ).issue(
        route,
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
        readiness_evidence_refs=["artifact://readiness/right-arm"],
    )
    approval_path = tmp_path.joinpath(
        *approval_ref.removeprefix("artifact://").split("/")
    ).with_suffix(".json")
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    approval["authorized_at"] = "not-a-timestamp"
    approval_path.write_text(json.dumps(approval), encoding="utf-8")

    snapshots = []
    engine = object.__new__(RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.profile = {"simulation_action_mode": "runtime_monitored"}
    engine.task_adapter = SimpleNamespace(task_name="blocks_ranking_rgb")
    engine.backend = SimpleNamespace(
        snapshot=lambda: snapshots.append(True)
        or {"scene_revision": route["scene_revision"]}
    )
    arguments = {
        "route_request": route,
        "candidate_ref": assignment["candidate_ref"],
        "entity_ref": assignment["entity_ref"],
        "assignment_ref": assignment["assignment_ref"],
        "assignment": assignment,
        "task_id": assignment["task_id"],
        "capability_snapshot_ref": assignment["capability_snapshot_ref"],
        "approval_ref": approval_ref,
    }

    with pytest.raises(PersistentActionApprovalError, match="timestamp"):
        engine._prepare(arguments)
    assert snapshots == [True]
    assert not hasattr(engine.backend, "_task")


def test_engine_uses_validated_runtime_identity_not_host_profile(tmp_path, monkeypatch):
    import robotwin_persistent_engine as module

    route = _request(tmp_path)
    assignment = {
        **_assignment(route),
        "task_id": "task-1",
        "capability_snapshot_ref": "artifact://capabilities/snapshot",
        "selected_arm_ids": ["right"],
    }
    assignment_path = tmp_path / "assignments" / "task" / "revision" / "node.json"
    assignment_path.parent.mkdir(parents=True)
    assignment_path.write_text(json.dumps(assignment), encoding="utf-8")
    approval_ref = PersistentSimulationActionApprover(
        tmp_path,
        task_name="blocks_ranking_rgb",
        mode="runtime_monitored",
    ).issue(
        route,
        candidate_ref=assignment["candidate_ref"],
        assignment=assignment,
        readiness_evidence_refs=["artifact://readiness/right-arm"],
    )

    observed = {}

    def stop_after_identity(*args, **kwargs):
        observed["robot_identity"] = kwargs["robot_identity"]
        raise RuntimeError("policy boundary reached")

    monkeypatch.setattr(module.probe, "_validate_request_policies", stop_after_identity)
    engine = object.__new__(module.RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.profile = {"simulation_action_mode": "runtime_monitored"}
    engine.runtime_profile = {"robot_identity": "franka-panda"}
    engine.duration = 30.0
    engine.task_adapter = SimpleNamespace(task_name="blocks_ranking_rgb")
    engine.backend = SimpleNamespace(
        snapshot=lambda: {"scene_revision": route["scene_revision"]}
    )
    arguments = {
        "route_request": route,
        "candidate_ref": assignment["candidate_ref"],
        "entity_ref": assignment["entity_ref"],
        "assignment_ref": assignment["assignment_ref"],
        "assignment": assignment,
        "task_id": assignment["task_id"],
        "capability_snapshot_ref": assignment["capability_snapshot_ref"],
        "approval_ref": approval_ref,
    }

    with pytest.raises(RuntimeError, match="policy boundary"):
        engine._prepare(arguments)
    assert observed == {"robot_identity": "franka-panda"}
