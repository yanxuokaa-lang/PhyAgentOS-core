from threading import Event, get_ident
from types import SimpleNamespace

import numpy as np
import pytest

from robotwin20_adapter.persistent_manipulation import (
    ManipulationStateError,
    PersistentManipulationProvider,
)


class Engine:
    def __init__(self):
        self.thread = get_ident()
        self.scene = 0
        self.closed = False
        self.calls = []

    def execute(self, phase, arguments, cancel, *, owner, invocation_id):
        assert get_ident() == self.thread
        self.calls.append((phase, self.scene, owner, invocation_id))
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
            with pytest.raises(ManipulationStateError, match="empty provider"):
                provider.query("bind_observed_entities", {})
            with pytest.raises(ManipulationStateError):
                provider.query("contact_qualification", {})
            assert provider.query("snapshot", {})["scene_revision"] == str(index * 2 + 1)
            with pytest.raises(ManipulationStateError):
                provider.start("acquire", "conflict", "task-2", {"entity_ref": entity})
            with pytest.raises(ManipulationStateError):
                provider.start("place", "wrong-owner", "task-2", {"entity_ref": entity, "acquire_invocation_id": acquire})
            place = f"place-{index}"
            provider.start("place", place, "task-1", {"entity_ref": entity, "acquire_invocation_id": acquire})
            assert settle(provider, place)["holding_state"] == "empty"
        assert provider._engine.calls == [
            ("acquire", 0, "task-1", "acquire-0"),
            ("place", 1, "task-1", "place-0"),
            ("acquire", 2, "task-1", "acquire-1"),
            ("place", 3, "task-1", "place-1"),
        ]
    finally:
        provider.close()


def test_cancelled_motion_retains_uncertain_possession_without_release():
    running = Event()
    class Cancellable(Engine):
        def execute(self, phase, arguments, cancel, *, owner, invocation_id):
            del phase, arguments, owner, invocation_id
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


class _Actor:
    def __init__(self, name, x=0.0):
        self.name = name
        self.matrix = np.eye(4)
        self.matrix[0, 3] = x

    def get_name(self):
        return self.name

    def get_pose(self):
        return SimpleNamespace(to_transformation_matrix=lambda: self.matrix)


def _effect_engine(actors, trace=()):
    from robotwin_persistent_engine import RoboTwinPersistentEngine

    engine = object.__new__(RoboTwinPersistentEngine)
    engine.backend = SimpleNamespace(_task=SimpleNamespace(_paos_observed_entities=actors))
    engine._state = {"contact_trace": list(trace)}
    return engine


def _success_result():
    return {
        "status": "succeeded",
        "outcome_known": True,
        "world_change_started": True,
        "source_scene_revision": "scene-1",
        "new_scene_revision": "scene-2",
    }


def test_scene_effects_authorize_only_pose_stable_uncontacted_entities():
    actors = {"entity://target": _Actor("target"), "entity://other": _Actor("other", 0.2)}
    engine = _effect_engine(actors)
    before = engine._bound_entity_poses()

    effects = engine._scene_effects(
        {"entity_ref": "entity://target"}, before, _success_result(),
        evidence_ref="artifact://persistent/action-1",
    )

    assert effects["changed_entity_refs"] == ["entity://target"]
    assert effects["unaffected_entity_refs"] == ["entity://other"]
    assert effects["effect_scope_complete"] is True
    assert effects["carry_forward_authorized"] is True


def test_zero_step_failure_claims_no_changed_entities():
    actors = {"entity://target": _Actor("target"), "entity://other": _Actor("other", 0.2)}
    engine = _effect_engine(actors)
    before = engine._bound_entity_poses()
    effects = engine._scene_effects(
        {"entity_ref": "entity://target", "scene_revision": "scene-1"},
        before,
        {"status": "failed", "outcome_known": True, "world_change_started": False},
        evidence_ref="artifact://persistent/action-zero-step",
    )
    assert effects["changed_entity_refs"] == []
    assert effects["new_scene_revision"] is None
    assert effects["carry_forward_authorized"] is False


@pytest.mark.parametrize("change", ["contact", "move", "missing", "unknown"])
def test_scene_effects_fail_closed_when_entity_impact_is_not_proven(change):
    actors = {"entity://target": _Actor("target"), "entity://other": _Actor("other", 0.2)}
    trace = [{"pair": ["gripper", "other"], "active_contact": True}] if change == "contact" else []
    engine = _effect_engine(actors, trace)
    before = engine._bound_entity_poses()
    result = _success_result()
    if change == "move":
        actors["entity://other"].matrix[0, 3] += 0.01
    elif change == "missing":
        del actors["entity://other"]
    elif change == "unknown":
        result.update(status="cancelled", outcome_known=False, new_scene_revision=None)

    effects = engine._scene_effects(
        {"entity_ref": "entity://target"}, before, result,
        evidence_ref="artifact://persistent/action-1",
    )

    assert "entity://other" not in effects["unaffected_entity_refs"]
    if change in {"contact", "move"}:
        assert "entity://other" in effects["changed_entity_refs"]
    else:
        assert effects["effect_scope_complete"] is False
        assert effects["carry_forward_authorized"] is False
