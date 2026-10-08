import sys
from pathlib import Path

import pytest

from robotwin20_adapter import (
    JsonlProcessWorkerClient,
    ProcessWorkerConfig,
    ProcessWorkerProtocolLimitError,
)
from robotwin20_adapter.persistent_client import PersistentWorkerClient


def test_lost_start_acknowledgement_stays_unknown_without_recreating_world():
    class Worker:
        calls = 0

        def request(self, request):
            self.calls += 1
            raise TimeoutError("acknowledgement lost")

    worker = Worker()
    client = PersistentWorkerClient(worker)
    driver = client.start("acquire", "invocation-1", "owner", {"entity_ref": "entity://red"})
    assert driver.poll()["status"] == "unknown"
    assert driver.poll()["world_change_started"] is None
    with pytest.raises(RuntimeError, match="connection lost"):
        client.query("snapshot", {})
    assert worker.calls == 1


def test_explicit_rejection_does_not_invalidate_live_world():
    class Worker:
        def request(self, request):
            if request["command"] == "start":
                return {"ok": False, "error": "held by another owner"}
            return {"ok": True, "scene_revision": "same-scene"}

    client = PersistentWorkerClient(Worker())
    with pytest.raises(RuntimeError, match="another owner"):
        client.start("acquire", "invocation-1", "owner", {})
    assert client.query("snapshot", {})["scene_revision"] == "same-scene"


def test_transport_limit_failure_remains_structured_for_reconciliation():
    class Worker:
        def request(self, _request):
            raise ProcessWorkerProtocolLimitError(
                "worker response exceeds max_line_bytes",
                code="worker_response_too_large",
            )

    client = PersistentWorkerClient(Worker())
    driver = client.start(
        "acquire",
        "invocation-1",
        "owner",
        {"entity_ref": "entity://one"},
    )

    result = driver.poll()
    assert result == {
        "status": "unknown",
        "outcome_known": False,
        "world_change_started": None,
        "failure_owner": "infrastructure",
        "failure_code": "worker_response_too_large",
        "error_detail": "worker response exceeds max_line_bytes",
        "retryable_in_revision": False,
        "requires_replan": False,
        "recommended_action": "stop",
    }
    assert client.transport_failure_code == "worker_response_too_large"


def test_oversized_untransmitted_request_does_not_mark_persistent_world_lost():
    fixture = Path(__file__).parent / "fixtures" / "jsonl_worker.py"
    worker = JsonlProcessWorkerClient(ProcessWorkerConfig(
        command=(sys.executable, str(fixture), "--mode", "normal"),
        cwd=fixture.parent,
        startup_timeout_s=1,
        request_timeout_s=1,
        shutdown_timeout_s=1,
        max_line_bytes=256,
    ))
    class PersistentFixtureWorker:
        def request(self, payload):
            return {**worker.request(payload), "ok": True}

        def release(self):
            worker.release()

    client = PersistentWorkerClient(PersistentFixtureWorker())
    try:
        with pytest.raises(ProcessWorkerProtocolLimitError):
            client.query("snapshot", {"padding": "x" * 512})
        assert client._transport_lost is False
        assert client.query("snapshot", {})["status"] == "available"
    finally:
        client.close()
