from __future__ import annotations

from threading import Event, Thread

from robotwin20_adapter.stack_relation_execution import StackRelationExecutionProvider


def _request():
    return {
        "entity_ref": "entity://stack-block-2",
        "goal_relation": "on",
        "relation_target_ref": "entity://stack-block-1",
        "scene_revision": "stack-0-2",
        "intent": {"task_id": "task-1", "motion_authorized": False},
        "relation_binding": {
            "entity_ref": "entity://stack-block-2",
            "relation_target_ref": "entity://stack-block-1",
            "destination_ref": "destination://stack-block-1",
            "world_T_object_target": [0.0] * 16,
            "evidence_refs": ["artifact://relation/target"],
        },
    }


def _route():
    assignment = {
        "task_id": "task-1",
        "entity_ref": "entity://stack-block-2",
        "candidate_ref": "candidate://stack-block-2/g1",
        "assignment_ref": "artifact://assignments/1",
    }
    return {
        "task_id": "task-1",
        "scene_revision": "stack-0-2",
        "entity_ref": "entity://stack-block-2",
        "candidate_ref": "candidate://stack-block-2/g1",
        "assignment_ref": assignment["assignment_ref"],
        "assignment": assignment,
        "approval_ref": "artifact://approvals/1",
        "route_request": {
            "scene_revision": "stack-0-2",
            "destination_ref": "destination://stack-block-1",
            "candidates": [{
                "candidate_ref": assignment["candidate_ref"],
                "entity_ref": assignment["entity_ref"],
            }],
        },
    }


class _Driver:
    def __init__(self, result):
        self.result = result
        self.cancelled = False
        self.stopped = False

    def poll(self):
        return self.result

    def cancel(self):
        self.cancelled = True

    def stop(self):
        self.stopped = True


class _Client:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []
        self.revision = "stack-0-2"

    def query(self, operation, _arguments):
        assert operation == "snapshot"
        return {"scene_revision": self.revision}

    def start(self, phase, invocation_id, owner, arguments):
        self.calls.append((phase, invocation_id, owner, arguments))
        return _Driver(next(self.results))


def _provider(client, *, available=True):
    return StackRelationExecutionProvider(
        client,
        prepare_route=lambda _request, _task_id: _route(),
        motion_supported=lambda: available,
    )


def test_stack_relation_composes_existing_acquire_and_place_drivers():
    acquire = {
        "status": "succeeded", "outcome_known": True, "world_change_started": True,
        "possession_state": "holding", "new_scene_revision": "stack-0-3",
        "evidence_refs": ["artifact://action/acquire"],
    }
    place = {
        "status": "succeeded", "outcome_known": True, "world_change_started": True,
        "possession_state": "empty", "new_scene_revision": "stack-0-4",
        "placement_measurement": {"position_error_m": 0.001, "orientation_error_rad": 0.01},
        "release_confirmed": True, "retreat_completed": True, "clear_of_target": True,
        "evidence_refs": ["artifact://action/place"],
    }
    client = _Client([acquire, place])
    admission = _provider(client).admit(
        _request(), invocation_id="gateway-1", attempt_id="attempt-1"
    )

    assert admission.driver is not None
    assert admission.driver.poll() is None
    result = admission.driver.poll()

    assert [call[0] for call in client.calls] == ["acquire", "place"]
    assert client.calls[0][1] == "gateway-1:acquire"
    assert client.calls[1][3]["scene_revision"] == "stack-0-3"
    assert client.calls[1][3]["acquire_invocation_id"] == "gateway-1:acquire"
    assert result["status"] == "succeeded"
    assert result["outcome_known"] is True
    assert result["evidence_refs"] == ["artifact://action/acquire", "artifact://action/place"]


def test_stack_relation_fails_closed_when_motion_is_unqualified():
    client = _Client([])
    result = _provider(client, available=False).admit(
        _request(), invocation_id="gateway-1", attempt_id="attempt-1"
    )

    assert result.driver is None
    assert result.terminal_result["status"] == "failed"
    assert result.terminal_result["outcome_known"] is True
    assert result.terminal_result["world_change_started"] is False
    assert client.calls == []


def test_stack_relation_rejects_stale_prepared_route_before_worker_start():
    client = _Client([])
    client.revision = "stack-0-9"
    result = _provider(client).admit(
        _request(), invocation_id="gateway-1", attempt_id="attempt-1"
    )

    assert result.driver is None
    assert result.terminal_result["status"] == "failed"
    assert result.terminal_result["world_change_started"] is False
    assert client.calls == []


def test_stack_relation_rejects_route_without_approval_before_worker_start():
    route = _route()
    route.pop("approval_ref")
    provider = StackRelationExecutionProvider(
        _Client([]), prepare_route=lambda _request, _task_id: route,
        motion_supported=lambda: True,
    )

    result = provider.admit(_request(), invocation_id="gateway-1", attempt_id="attempt-1")

    assert result.driver is None
    assert result.terminal_result["status"] == "failed"
    assert result.terminal_result["world_change_started"] is False


def test_stack_relation_rejects_route_candidate_not_bound_to_entity():
    route = _route()
    route["route_request"]["candidates"][0]["entity_ref"] = "entity://other"
    client = _Client([])
    provider = StackRelationExecutionProvider(
        client, prepare_route=lambda _request, _task_id: route,
        motion_supported=lambda: True,
    )

    result = provider.admit(_request(), invocation_id="gateway-1", attempt_id="attempt-1")

    assert result.driver is None
    assert result.terminal_result["status"] == "failed"
    assert client.calls == []


def test_known_acquire_failure_does_not_start_place():
    acquire = {
        "status": "failed", "outcome_known": True, "world_change_started": False,
        "possession_state": "empty", "failure_code": "no_grasp",
    }
    client = _Client([acquire])
    driver = _provider(client).admit(
        _request(), invocation_id="gateway-1", attempt_id="attempt-1"
    ).driver

    result = driver.poll()

    assert result["status"] == "failed"
    assert result["outcome_known"] is True
    assert result["failure_code"] == "no_grasp"
    assert [call[0] for call in client.calls] == ["acquire"]


def test_stack_relation_does_not_report_success_without_measured_postcondition():
    acquire = {
        "status": "succeeded", "outcome_known": True, "possession_state": "holding",
        "new_scene_revision": "stack-0-3",
    }
    place = {
        "status": "succeeded", "outcome_known": True, "possession_state": "empty",
        "new_scene_revision": "stack-0-4", "release_confirmed": True,
        "retreat_completed": True, "clear_of_target": True,
    }
    driver = _provider(_Client([acquire, place])).admit(
        _request(), invocation_id="gateway-1", attempt_id="attempt-1"
    ).driver

    assert driver.poll() is None
    result = driver.poll()
    assert result["status"] == "unknown"
    assert result["outcome_known"] is False
    assert result["failure_code"] == "relation_postcondition_not_measured"


def test_cancelled_acquire_never_starts_place_and_keeps_world_unknown():
    acquire = {
        "status": "succeeded", "outcome_known": True, "world_change_started": True,
        "possession_state": "holding", "new_scene_revision": "stack-0-3",
    }
    client = _Client([acquire])
    driver = _provider(client).admit(
        _request(), invocation_id="gateway-1", attempt_id="attempt-1"
    ).driver

    driver.cancel()
    result = driver.poll()

    assert result["status"] == "unknown"
    assert result["outcome_known"] is False
    assert result["failure_code"] == "cancelled_during_acquire"
    assert [call[0] for call in client.calls] == ["acquire"]


def test_place_success_requires_finite_measurement_and_new_scene_revision():
    acquire = {
        "status": "succeeded", "outcome_known": True, "possession_state": "holding",
        "new_scene_revision": "stack-0-3",
    }
    place = {
        "status": "succeeded", "outcome_known": True, "possession_state": "empty",
        "new_scene_revision": "", "placement_measurement": {
            "position_error_m": float("nan"), "orientation_error_rad": 0.01,
        },
        "release_confirmed": True, "retreat_completed": True, "clear_of_target": True,
    }
    driver = _provider(_Client([acquire, place])).admit(
        _request(), invocation_id="gateway-1", attempt_id="attempt-1"
    ).driver

    assert driver.poll() is None
    result = driver.poll()

    assert result["status"] == "unknown"
    assert result["failure_code"] == "relation_postcondition_not_measured"


def test_place_success_requires_fresh_scene_revision_and_evidence_reference():
    acquire = {
        "status": "succeeded", "outcome_known": True, "possession_state": "holding",
        "new_scene_revision": "stack-0-3",
    }
    place = {
        "status": "succeeded", "outcome_known": True, "possession_state": "empty",
        "new_scene_revision": "stack-0-3", "placement_measurement": {
            "position_error_m": 0.001, "orientation_error_rad": 0.01,
        },
        "release_confirmed": True, "retreat_completed": True, "clear_of_target": True,
    }
    driver = _provider(_Client([acquire, place])).admit(
        _request(), invocation_id="gateway-1", attempt_id="attempt-1"
    ).driver

    assert driver.poll() is None
    result = driver.poll()
    assert result["status"] == "unknown"
    assert result["failure_code"] == "relation_postcondition_not_measured"

    place["new_scene_revision"] = "stack-0-4"
    driver = _provider(_Client([acquire, place])).admit(
        _request(), invocation_id="gateway-1", attempt_id="attempt-1"
    ).driver
    assert driver.poll() is None
    result = driver.poll()
    assert result["status"] == "unknown"
    assert result["failure_code"] == "relation_postcondition_evidence_missing"


def test_worker_poll_exception_is_unknown_and_does_not_start_following_phase():
    class BrokenDriver(_Driver):
        def poll(self):
            raise OSError("connection dropped")

    client = _Client([])
    client.start = lambda *_args: BrokenDriver(None)
    driver = _provider(client).admit(
        _request(), invocation_id="gateway-1", attempt_id="attempt-1"
    ).driver

    result = driver.poll()

    assert result["status"] == "unknown"
    assert result["outcome_known"] is False
    assert result["failure_code"] == "worker_poll_uncertain:OSError"
    assert len(client.calls) == 0


def test_cancel_racing_place_start_is_forwarded_to_place_driver():
    acquire = {
        "status": "succeeded", "outcome_known": True, "possession_state": "holding",
        "new_scene_revision": "stack-0-3",
    }
    place_started = Event()
    release_place_start = Event()
    place_driver = _Driver(None)

    class TransitionClient(_Client):
        def start(self, phase, invocation_id, owner, arguments):
            if phase == "place":
                place_started.set()
                assert release_place_start.wait(timeout=2)
                self.calls.append((phase, invocation_id, owner, arguments))
                return place_driver
            return super().start(phase, invocation_id, owner, arguments)

    client = TransitionClient([acquire])
    driver = _provider(client).admit(
        _request(), invocation_id="gateway-1", attempt_id="attempt-1"
    ).driver
    poll_thread = Thread(target=driver.poll)
    poll_thread.start()
    assert place_started.wait(timeout=2)
    cancel_called = Event()

    def cancel():
        cancel_called.set()
        driver.cancel()

    cancel_thread = Thread(target=cancel)
    cancel_thread.start()
    assert cancel_called.wait(timeout=2)
    release_place_start.set()
    poll_thread.join(timeout=2)
    cancel_thread.join(timeout=2)

    assert not poll_thread.is_alive()
    assert not cancel_thread.is_alive()
    assert place_driver.cancelled is True
