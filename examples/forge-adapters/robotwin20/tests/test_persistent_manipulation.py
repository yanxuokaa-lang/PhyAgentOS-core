from threading import Event, get_ident

import pytest

from robotwin20_adapter.persistent_manipulation import ManipulationStateError, PersistentManipulationProvider


class Engine:
    def __init__(self):
        self.thread = get_ident()
        self.scene = 0
        self.closed = False
        self.calls = []

    def execute(self, phase, arguments, cancel):
        assert get_ident() == self.thread
        self.calls.append((phase, self.scene))
        self.scene += 1
        return {"status": "succeeded", "world_change_started": True, "outcome_known": True, "new_scene_revision": str(self.scene)}

    def query(self, operation, arguments):
        assert get_ident() == self.thread
        return {"scene_revision": str(self.scene)}

    def close(self):
        assert get_ident() == self.thread
        self.closed = True


def settle(provider, key):
    provider._operations[key][0].result(timeout=5)
    return provider.poll(key)


def test_two_objects_share_world_and_require_owned_acquire_continuation():
    provider = PersistentManipulationProvider(Engine)
    try:
        for index in range(2):
            entity, acquire = f"entity://{index}", f"acquire-{index}"
            provider.start("acquire", acquire, "task-1", {"entity_ref": entity})
            assert settle(provider, acquire)["holding_state"] == "holding"
            with pytest.raises(ManipulationStateError, match="empty provider"):
                provider.query("route_readiness", {})
            assert provider.query("snapshot", {})["scene_revision"] == str(index * 2 + 1)
            with pytest.raises(ManipulationStateError):
                provider.start("acquire", "conflict", "task-2", {"entity_ref": entity})
            with pytest.raises(ManipulationStateError):
                provider.start("place", "wrong-owner", "task-2", {"entity_ref": entity, "acquire_invocation_id": acquire})
            place = f"place-{index}"
            provider.start("place", place, "task-1", {"entity_ref": entity, "acquire_invocation_id": acquire})
            assert settle(provider, place)["holding_state"] == "empty"
        assert provider._engine.calls == [("acquire", 0), ("place", 1), ("acquire", 2), ("place", 3)]
    finally:
        provider.close()


def test_cancelled_motion_retains_uncertain_possession_without_release():
    running = Event()
    class Cancellable(Engine):
        def execute(self, phase, arguments, cancel):
            running.set()
            assert cancel.wait(5)
            return {"status": "cancelled", "world_change_started": True, "outcome_known": False}
    provider = PersistentManipulationProvider(Cancellable)
    try:
        provider.start("acquire", "a", "owner", {"entity_ref": "entity://one"})
        assert running.wait(5)
        provider.cancel("a")
        assert settle(provider, "a")["holding_state"] == "uncertain"
        with pytest.raises(ManipulationStateError):
            provider.start("acquire", "b", "owner", {"entity_ref": "entity://two"})
    finally:
        provider.close()
