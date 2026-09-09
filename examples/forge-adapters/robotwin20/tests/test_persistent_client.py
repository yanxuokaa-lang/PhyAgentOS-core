import pytest

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
