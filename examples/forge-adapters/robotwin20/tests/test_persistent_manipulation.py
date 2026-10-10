import json
from threading import Event, get_ident
from types import SimpleNamespace

import numpy as np
import pytest

from robotwin20_adapter.persistent_manipulation import (
    ACTION_RECEIPT_MAX_BYTES,
    ManipulationStateError,
    PersistentManipulationProvider,
    bounded_action_receipt,
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


def test_unknown_place_with_runtime_confirmed_release_reconciles_empty():
    class ReleasedButUnverifiedEngine(Engine):
        def execute(self, phase, arguments, cancel, *, owner, invocation_id):
            if phase == "acquire":
                return super().execute(
                    phase, arguments, cancel, owner=owner, invocation_id=invocation_id
                )
            del phase, arguments, cancel, owner, invocation_id
            return {
                "status": "unknown",
                "world_change_started": True,
                "outcome_known": False,
                "new_scene_revision": "scene-after-place",
                "release_confirmed": True,
                "possession_state": "empty",
                "requires_replan": True,
            }

    provider = PersistentManipulationProvider(ReleasedButUnverifiedEngine)
    try:
        provider.start("acquire", "acquire", "owner", {"entity_ref": "entity://one"})
        assert settle(provider, "acquire")["holding_state"] == "holding"
        provider.start(
            "place", "place", "owner",
            {"entity_ref": "entity://one", "acquire_invocation_id": "acquire"},
        )
        receipt = settle(provider, "place")
        assert receipt["status"] == "unknown"
        assert receipt["holding_state"] == "empty"
        assert receipt["possession_state"] == "empty"
    finally:
        provider.close()


def test_unknown_place_without_runtime_possession_fact_remains_uncertain():
    class UnresolvedPlaceEngine(Engine):
        def execute(self, phase, arguments, cancel, *, owner, invocation_id):
            if phase == "acquire":
                return super().execute(
                    phase, arguments, cancel, owner=owner, invocation_id=invocation_id
                )
            del phase, arguments, cancel, owner, invocation_id
            return {
                "status": "unknown",
                "world_change_started": True,
                "outcome_known": False,
                "new_scene_revision": "scene-after-place",
                "requires_replan": True,
            }

    provider = PersistentManipulationProvider(UnresolvedPlaceEngine)
    try:
        provider.start("acquire", "acquire", "owner", {"entity_ref": "entity://one"})
        assert settle(provider, "acquire")["holding_state"] == "holding"
        provider.start(
            "place", "place", "owner",
            {"entity_ref": "entity://one", "acquire_invocation_id": "acquire"},
        )
        assert settle(provider, "place")["holding_state"] == "uncertain"
    finally:
        provider.close()


@pytest.mark.parametrize("mismatch", [False, True])
def test_provider_publishes_held_receipt_only_with_matching_settled_possession(mismatch):
    class HeldEngine(Engine):
        def execute(self, phase, arguments, cancel, *, owner, invocation_id):
            return {
                **super().execute(phase, arguments, cancel, owner=owner, invocation_id=invocation_id),
                "scene_effects": {"held_entity": {
                    "holding_state": "holding", "entity_ref": arguments["entity_ref"],
                    "owner": "other" if mismatch else owner,
                    "acquire_invocation_id": invocation_id,
                }},
            }
    provider = PersistentManipulationProvider(HeldEngine)
    try:
        provider.start("acquire", "invocation://acquire/1", "paos:task-1", {"entity_ref": "entity://container"})
        receipt = settle(provider, "invocation://acquire/1")
        assert receipt["holding_state"] == "holding"
        assert ("held_entity" in receipt["scene_effects"]) is not mismatch
    finally:
        provider.close()


def test_large_engine_diagnostics_stay_out_of_the_terminal_receipt(tmp_path):
    artifact = tmp_path / "complete-action.json"
    execution_plan = {"segments": [[float(index) for index in range(150_000)]]}

    class DiagnosticEngine(Engine):
        def execute(self, phase, arguments, cancel, *, owner, invocation_id):
            del phase, arguments, cancel, owner, invocation_id
            complete = {
                "status": "succeeded",
                "world_change_started": True,
                "outcome_known": True,
                "new_scene_revision": "scene-2",
                "failure_owner": "none",
                "failure_code": None,
                "retryable_in_revision": False,
                "requires_replan": False,
                "recommended_action": "continue",
                "phase": "acquire",
                "selected_arm": "arm-a",
                "failed_phase": None,
                "arm_attempts": [{
                    "arm": "arm-a",
                    "status": "pass",
                    "execution_plan": execution_plan,
                }],
                "artifact_refs": ["artifact://persistent/action-complete"],
                "evidence_refs": ["artifact://persistent/action-complete"],
            }
            artifact.write_text(json.dumps(complete), encoding="utf-8")
            return complete

    provider = PersistentManipulationProvider(DiagnosticEngine)
    try:
        provider.start("acquire", "large", "owner", {"entity_ref": "entity://one"})
        receipt = settle(provider, "large")
        assert receipt["status"] == "succeeded"
        assert receipt["outcome_known"] is True
        assert receipt["holding_state"] == "holding"
        assert receipt["arm_attempts"] == [{"arm": "arm-a", "status": "pass"}]
        assert "execution_plan" not in receipt
        assert len(json.dumps(receipt).encode("utf-8")) < ACTION_RECEIPT_MAX_BYTES
        assert artifact.stat().st_size > 1_048_576
        assert "execution_plan" in json.loads(artifact.read_text(encoding="utf-8"))["arm_attempts"][0]
    finally:
        provider.close()


def test_oversized_scene_effects_disable_carry_forward_instead_of_expanding_receipt():
    result = {
        "status": "succeeded",
        "world_change_started": True,
        "outcome_known": True,
        "new_scene_revision": "scene-2",
        "artifact_refs": ["artifact://persistent/action-complete"],
        "scene_effects": {
            "schema_version": "paos-scene-effects/v1",
            "source_scene_revision": "scene-1",
            "new_scene_revision": "scene-2",
            "changed_entity_refs": [],
            "unaffected_entity_refs": [f"entity://{index}-{'x' * 2000}" for index in range(200)],
            "changed_resources": [],
            "effect_evidence_refs": ["artifact://persistent/action-complete"],
            "effect_scope_complete": True,
            "carry_forward_authorized": True,
            "held_entity": {"holding_state": "holding", "entity_ref": "entity://container",
                            "owner": "paos:task-1", "acquire_invocation_id": "invocation://acquire/1"},
        },
    }

    receipt = bounded_action_receipt(result)

    assert len(json.dumps(receipt).encode("utf-8")) < ACTION_RECEIPT_MAX_BYTES
    assert receipt["receipt_truncated"] is True
    assert receipt["scene_effects"]["effect_scope_complete"] is False
    assert receipt["scene_effects"]["carry_forward_authorized"] is False
    assert "held_entity" not in receipt["scene_effects"]


def test_receipt_marks_truncated_refs_and_rejects_nested_terminal_values():
    receipt = bounded_action_receipt({
        "status": "succeeded",
        "outcome_known": True,
        "world_change_started": True,
        "error_detail": {"unbounded": ["private", "nested", "payload"]},
        "artifact_refs": [f"artifact://persistent/{index}" for index in range(18)],
        "evidence_refs": ["x" * 2049],
    })

    assert receipt["status"] == "succeeded"
    assert receipt["outcome_known"] is True
    assert "error_detail" not in receipt
    assert len(receipt["artifact_refs"]) == 16
    assert receipt["evidence_refs"] == []
    assert receipt["receipt_truncated"] is True


def test_receipt_does_not_serialize_non_finite_terminal_number():
    receipt = bounded_action_receipt({
        "status": "succeeded",
        "outcome_known": True,
        "world_change_started": True,
        "phase": float("nan"),
    })

    assert "phase" not in receipt
    assert receipt["receipt_truncated"] is True
    json.dumps(receipt, allow_nan=False)


def test_receipt_projection_failure_keeps_durable_evidence_and_uncertain_state(monkeypatch):
    import robotwin20_adapter.persistent_manipulation as module

    class SettledEngine(Engine):
        def execute(self, phase, arguments, cancel, *, owner, invocation_id):
            del phase, arguments, cancel, owner, invocation_id
            return {
                "status": "succeeded",
                "world_change_started": True,
                "outcome_known": True,
                "artifact_refs": ["artifact://persistent/action-complete"],
                "evidence_refs": ["artifact://persistent/action-complete"],
            }

    monkeypatch.setattr(
        module,
        "bounded_action_receipt",
        lambda _result: (_ for _ in ()).throw(ValueError("invalid receipt field")),
    )
    provider = PersistentManipulationProvider(SettledEngine)
    try:
        provider.start("acquire", "projection", "owner", {"entity_ref": "entity://one"})
        result = settle(provider, "projection")
    finally:
        provider.close()

    assert result["status"] == "unknown"
    assert result["world_change_started"] is True
    assert result["outcome_known"] is False
    assert result["failure_owner"] == "infrastructure"
    assert result["failure_code"] == "action_receipt_projection_failed"
    assert result["artifact_refs"] == ["artifact://persistent/action-complete"]
    assert result["holding_state"] == "uncertain"


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


@pytest.mark.parametrize("release_evidence", [True, None])
def test_place_engine_projects_verified_postconditions_without_video_encoder(
    tmp_path, release_evidence
):
    from json import loads
    from pathlib import Path

    from robotwin_persistent_engine import RoboTwinPersistentEngine, _StopSignal
    from robotwin_simulation_probe_worker import _artifact_path

    class Video:
        recorder = None

        def start_action(self, *_args, **_kwargs):
            return None

        def finish_action(self, *_args, **_kwargs):
            return ()

    engine = object.__new__(RoboTwinPersistentEngine)
    engine.root = Path(tmp_path)
    engine.epoch = "postconditions"
    engine.duration = 30
    engine.stop = _StopSignal(engine.root / "stop")
    engine.backend = SimpleNamespace(_task=SimpleNamespace(), snapshot=lambda: {"scene_revision": "scene-2"})
    engine.video = Video()
    engine._state = {"simulator_steps": 4, "assignment_ref": "assignment-1"}
    engine._request = {"scene_revision": "scene-1"}
    engine._advance_scene = lambda: "scene-3"
    engine._verify_release = lambda: None

    def phases():
        yield {"phase": "retreat"}
        result = {"trajectory": True}
        if release_evidence is not None:
            result["planner_detached_after_release"] = release_evidence
        return result

    engine._phases = phases()
    result = engine.execute(
        "place",
        {"scene_revision": "scene-2", "assignment_ref": "assignment-1", "entity_ref": "entity://one"},
        Event(),
        owner="paos:task-1",
        invocation_id="invocation://object-place/1",
    )

    assert result["status"] == "succeeded"
    assert result["release_confirmed"] is (release_evidence is True)
    assert result["retreat_completed"] is True
    assert result["clear_of_target"] is True
    assert result["observation_ready"] is (release_evidence is True)
    artifact = loads(_artifact_path(engine.root, result["artifact_refs"][0]).read_text())
    assert artifact["observation_ready"] is (release_evidence is True)
    assert artifact["invocation_id"] == "invocation://object-place/1"
    assert artifact["owner"] == "paos:task-1"
    assert artifact["artifact_refs"] == result["artifact_refs"]
    assert artifact["evidence_refs"] == result["evidence_refs"]


def test_place_engine_does_not_claim_clearance_without_retreat(tmp_path):
    from robotwin_persistent_engine import RoboTwinPersistentEngine, _StopSignal

    class Video:
        recorder = None

        def start_action(self, *_args, **_kwargs):
            return None

        def finish_action(self, *_args, **_kwargs):
            return ()

    engine = object.__new__(RoboTwinPersistentEngine)
    engine.root = tmp_path
    engine.epoch = "incomplete-route"
    engine.duration = 30
    engine.stop = _StopSignal(tmp_path / "stop")
    engine.backend = SimpleNamespace(_task=SimpleNamespace(), snapshot=lambda: {"scene_revision": "scene-2"})
    engine.video = Video()
    engine._state = {"simulator_steps": 1, "assignment_ref": "assignment-1"}
    engine._request = {"scene_revision": "scene-1"}
    engine._advance_scene = lambda: "scene-3"
    engine._verify_release = lambda: None

    def phases():
        yield {"phase": "descent"}
        return {"trajectory": True, "planner_detached_after_release": True}

    engine._phases = phases()
    result = engine.execute(
        "place",
        {"scene_revision": "scene-2", "assignment_ref": "assignment-1", "entity_ref": "entity://one"},
        Event(),
        owner="paos:task-1",
        invocation_id="invocation://object-place/incomplete",
    )

    assert result["status"] == "succeeded"
    assert result["release_confirmed"] is True
    assert result["retreat_completed"] is False
    assert result["clear_of_target"] is False
    assert result["observation_ready"] is False


def test_acquire_engine_persists_held_identity_separately_from_unchanged(tmp_path):
    from robotwin_persistent_engine import _StopSignal
    from robotwin_simulation_probe_worker import _artifact_path

    actors = {"entity://container": _Actor("container")}
    engine = _effect_engine(actors)
    engine.root, engine.epoch, engine.duration = tmp_path, "held-test", 30
    engine.stop = _StopSignal(tmp_path / "stop")
    engine._request = {"scene_revision": "scene-1"}
    engine._advance_scene = lambda: "scene-2"
    engine.video = SimpleNamespace(
        recorder=None, start_action=lambda *a, **k: None, finish_action=lambda *a, **k: (),
    )

    def prepare(arguments):
        def phases():
            actors["entity://container"].matrix[0, 3] = 0.1
            yield {"phase": "lift"}
        engine._phases = phases()
    engine._prepare = prepare
    result = engine.execute("acquire", {"entity_ref": "entity://container"}, Event(),
                            owner="paos:task-1", invocation_id="invocation://acquire/1")
    effects = result["scene_effects"]
    assert result["status"] == "succeeded"
    assert effects["unaffected_entity_refs"] == []
    assert effects["carry_forward_authorized"] is False
    assert effects["held_entity"] == {
        "holding_state": "holding", "entity_ref": "entity://container",
        "owner": "paos:task-1", "acquire_invocation_id": "invocation://acquire/1",
    }
    artifact = json.loads(_artifact_path(tmp_path, result["artifact_refs"][0]).read_text())
    assert artifact["scene_effects"] == effects


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
