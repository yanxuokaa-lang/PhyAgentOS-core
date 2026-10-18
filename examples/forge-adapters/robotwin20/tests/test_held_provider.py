from threading import get_ident

import pytest

from robotwin20_adapter.persistent_manipulation import (
    ManipulationStateError,
    PersistentManipulationProvider,
    bounded_action_receipt,
)


class Engine:
    """No simulator imports or actuator calls; exercises the actual worker owner."""

    def __init__(self):
        self.thread = get_ident()
        self.scene = 0
        self.calls = []

    def execute(self, phase, arguments, cancel, *, owner, invocation_id):
        assert get_ident() == self.thread
        self.calls.append(phase)
        self.scene += 1
        return {
            "status": "succeeded", "outcome_known": True, "world_change_started": True,
            "new_scene_revision": str(self.scene), "possession_state": "empty" if phase == "place" else "holding",
            "entity_ref": arguments["entity_ref"], "destination_ref": "destination://lab/beaker",
            "operation_completed": True, "returned_to_safe_pose": True,
            "measurements": {"aligned_hold_s": 2.0, "maximum_tilt_rad": 1.8,
                             "private_trajectory": [0] * 1000},
            "artifact_refs": ["artifact://lab/execution"],
        }

    def query(self, operation, arguments):
        assert get_ident() == self.thread
        return {"scene_revision": str(self.scene)}

    def close(self):
        assert get_ident() == self.thread


def settle(provider, invocation):
    provider._operations[invocation][0].result(timeout=5)
    return provider.poll(invocation)


def test_worker_serializes_held_operations_and_requires_current_return_source():
    provider = PersistentManipulationProvider(Engine, held_operations=("pour", "stir"))
    try:
        assert provider.query("snapshot", {})["scene_revision"] == "0"
        provider.start("acquire", "acquire", "owner", {"entity_ref": "entity://a"})
        assert settle(provider, "acquire")["holding_state"] == "holding"
        args = {"entity_ref": "entity://a", "acquire_invocation_id": "acquire",
                "held_invocation_ref": "acquire", "scene_revision": "1"}
        provider.start("pour", "pour", "owner", args)
        result = settle(provider, "pour")
        assert result["holding_state"] == "holding" and result["held_invocation_ref"] == "pour"
        assert result["measurements"] == {"aligned_hold_s": 2.0, "maximum_tilt_rad": 1.8}
        with pytest.raises(ManipulationStateError, match="stale"):
            provider.start("pour", "again", "owner", args)
        with pytest.raises(ManipulationStateError, match="current held"):
            provider.start("place", "old-place", "owner", {"entity_ref": "entity://a", "acquire_invocation_id": "acquire"})
        args.update(held_invocation_ref="pour", scene_revision="2")
        provider.start("place", "place", "owner", args)
        result = settle(provider, "place")
        assert result["holding_state"] == "empty" and result["entity_ref"] == "entity://a"
        assert provider._engine.calls == ["acquire", "pour", "place"]
    finally:
        provider.close()


def test_legacy_worker_does_not_advertise_or_accept_unimplemented_operations():
    provider = PersistentManipulationProvider(Engine)
    try:
        with pytest.raises(ManipulationStateError, match="invalid manipulation"):
            provider.start("pour", "pour", "owner", {})
        assert provider._engine.calls == []
    finally:
        provider.close()


def test_provider_refuses_cycle_without_explicit_engine_support():
    provider = PersistentManipulationProvider(Engine)
    try:
        result = provider.prepare_cycle({"operation": "pour_cycle"})
        assert result == {"status": "unavailable", "error": "complete_cycle_not_supported"}
        with pytest.raises(ManipulationStateError, match="does not support complete"):
            provider.start("pour_cycle", "cycle", "owner", {"entity_ref": "entity://a"})
        assert provider._engine.calls == [] and provider.snapshot()["holding_state"] == "empty"
    finally:
        provider.close()


def test_held_measurement_projection_discards_invalid_values_and_private_data():
    receipt = bounded_action_receipt({"status": "succeeded", "measurements": {
        "aligned_hold_s": float("nan"), "maximum_tilt_rad": True,
        "in_container_turns": -2, "in_container_duration_s": 4.0,
        "trajectory": [[1, 2, 3]],
    }})
    assert receipt["measurements"] == {"in_container_duration_s": 4.0}
