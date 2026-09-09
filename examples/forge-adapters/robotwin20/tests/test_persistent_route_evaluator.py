import hashlib
import json
from types import SimpleNamespace

import pytest
import robotwin_route_planner as planner
import robotwin_simulation_probe_worker as probe


def test_current_route_evaluation_reuses_world_and_rejects_stale_inputs(tmp_path, monkeypatch):
    import robotwin_backend
    backend = SimpleNamespace(_task=SimpleNamespace(block=object()), revision="scene-2")
    backend.snapshot = lambda: {"scene_revision": backend.revision}
    monkeypatch.setattr(robotwin_backend, "load_runtime_profile", lambda path: {"task_name": "blocks", "seed": 0})
    monkeypatch.setattr(robotwin_backend, "RoboTwinSensorBackend", lambda *args: pytest.fail("must not create a world"))
    checked = []
    monkeypatch.setattr(probe, "_validate_route_input_artifacts", lambda root, request, candidate: candidate)
    monkeypatch.setattr(probe, "_validate_runtime_route_input_binding", lambda task, candidate, inputs: checked.append(candidate["entity_ref"]))
    monkeypatch.setattr(planner, "prepare_planning_world", lambda task, world: {"scene_revision": world["scene_revision"]})
    monkeypatch.setattr(planner, "evaluate_route", lambda *args, **kwargs: {"status": "pass"})

    def artifact(name, value):
        data = json.dumps(value).encode()
        path = tmp_path / "scene" / (name + ".json")
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
        return "artifact://scene/" + name, hashlib.sha256(data).hexdigest()

    evaluator = planner.RoboTwinRouteEvaluator(tmp_path, tmp_path / "profile.yaml", tmp_path, backend=backend)
    for revision in ("scene-2", "scene-3"):
        backend.revision = revision
        scene_ref, scene_digest = artifact(revision + "-facts", {
            "scene_revision": revision, "objects": [{"entity_ref": "entity://block", "actor_name": "block"}],
        })
        world_ref, world_digest = artifact(revision + "-world", {
            "scene_revision": revision, "source_scene_facts_ref": scene_ref, "source_scene_facts_sha256": scene_digest,
        })
        request = {"scene_revision": revision, "collision_world": {"artifact_ref": world_ref, "sha256": world_digest},
                   "candidates": [{"candidate_ref": "candidate://block/0", "entity_ref": "entity://block"}]}
        result = evaluator(request)
        assert result["simulator_steps"] == 0
        assert result["motion_authorized"] is False
        assert result["world"]["scene_revision"] == revision
        with pytest.raises(planner.SimulationProbeError, match="scene revision"):
            evaluator({**request, "scene_revision": "old-scene"})
    assert checked == ["entity://block", "entity://block"]


def test_readiness_client_validates_live_world_evidence(tmp_path):
    from robotwin_route_readiness_worker import _handle_factory
    from robotwin20_adapter.persistent_client import build_persistent_route_readiness
    from test_route_readiness import _request

    request = _request(tmp_path)
    handle = _handle_factory(tmp_path, "persistent-route-readiness", lambda request: {
        "candidates": {c["candidate_ref"]: {"status": "pass"} for c in request["candidates"]},
        "world": {}, "simulator_steps": 0,
    })

    class Client:
        def query(self, operation, arguments):
            assert operation == "route_readiness"
            return {**handle(arguments), "request_id": "transport-id"}

    response = build_persistent_route_readiness(Client()).evaluate(request)
    assert response["request_id"] == request["request_id"]
    assert response["provider_available"] is True
    assert response["status"] == "fail"
    assert response["route_evidence"][0]["checks"]["complete_transport_descent_retreat"] == "pass"
    assert response["route_evidence"][0]["checks"]["contact_dynamics"] == "unavailable"


def test_worker_preserves_transport_identity_for_nested_query(monkeypatch, tmp_path):
    import io
    import sys
    import robotwin_persistent_worker as worker

    profile = tmp_path / "profile.json"
    profile.write_text("{}")
    closed = []

    class Provider:
        def __init__(self, factory):
            pass

        def query(self, operation, arguments):
            return {"request_id": "route-id", "status": "fail"}

        def close(self):
            closed.append(True)

    output = io.StringIO()
    monkeypatch.setattr(worker, "PersistentManipulationProvider", Provider)
    monkeypatch.setattr(sys, "argv", ["worker", "--profile", str(profile)])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"command": "query", "operation": "route_readiness", "request_id": "transport-id"}) + "\n"))
    monkeypatch.setattr(sys, "stdout", output)
    assert worker.main() == 0
    assert json.loads(output.getvalue().splitlines()[1])["request_id"] == "transport-id"
    assert closed
