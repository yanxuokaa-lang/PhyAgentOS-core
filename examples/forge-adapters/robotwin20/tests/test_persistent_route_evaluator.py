import hashlib
import json
from types import SimpleNamespace

import pytest
import robotwin_route_planner as planner
import robotwin_simulation_probe_worker as probe


def test_planner_world_contact_mode_is_wired_after_world_installation(tmp_path, monkeypatch):
    import robotwin_backend
    import robotwin_contact_qualification as contact
    import robotwin_observed_collision as observed_collision

    events = []
    backend = SimpleNamespace(
        _task=SimpleNamespace(),
        snapshot=lambda: {"scene_revision": "scene-2"},
    )
    monkeypatch.setattr(
        robotwin_backend,
        "load_runtime_profile",
        lambda path: {"task_name": "blocks", "seed": 0},
    )
    monkeypatch.setattr(
        observed_collision,
        "configure_observed_collision",
        lambda task, world, root: events.append("configure_collision_world"),
    )
    monkeypatch.setattr(
        planner,
        "prepare_planning_world",
        lambda task, world: events.append("prepare_planning_world") or {"scene_revision": "scene-2"},
    )
    monkeypatch.setattr(
        probe,
        "_load_json_artifact",
        lambda root, ref: {"schema_version": "adaptation/v1"},
    )
    monkeypatch.setattr(probe, "_validate_route_input_artifacts", lambda root, request, candidate: {})
    monkeypatch.setattr(probe, "_validate_runtime_route_input_binding", lambda task, candidate, inputs: None)
    monkeypatch.setattr(
        contact,
        "qualify_observed_contact",
        lambda *args, **kwargs: pytest.fail("planner-world mode selected observed qualification"),
    )
    monkeypatch.setattr(
        contact,
        "qualify_planner_world_contact",
        lambda *args, **kwargs: events.append("qualify_planner_world_contact")
        or {
            "status": "qualified",
            "motion_authorized": False,
            "scene_revision": "scene-2",
            "candidate_ref": "candidate://block/0",
            "arm_id": "left",
        },
    )

    scene = {
        "scene_revision": "scene-2",
        "geometry_source": "observation",
        "objects": [{"entity_ref": "entity://block"}],
    }
    scene_bytes = json.dumps(scene).encode()
    scene_ref = "artifact://scene/facts"
    scene_path = tmp_path / "scene" / "facts.json"
    scene_path.parent.mkdir(exist_ok=True)
    scene_path.write_bytes(scene_bytes)
    world = {
        "scene_revision": "scene-2",
        "source_scene_facts_ref": scene_ref,
        "source_scene_facts_sha256": hashlib.sha256(scene_bytes).hexdigest(),
    }
    world_bytes = json.dumps(world).encode()
    world_path = tmp_path / "scene" / "world.json"
    world_path.parent.mkdir(exist_ok=True)
    world_path.write_bytes(world_bytes)

    original_artifact = probe._load_json_artifact

    def load_artifact(root, ref):
        if ref == scene_ref:
            return scene
        if ref == "artifact://scene/world":
            return world
        return original_artifact(root, ref)

    monkeypatch.setattr(probe, "_load_json_artifact", load_artifact)
    evaluator = planner.RoboTwinRouteEvaluator(
        tmp_path,
        tmp_path / "profile.yaml",
        tmp_path,
        backend=backend,
        contact_arms=["left"],
        contact_qualification_mode="planner_world_only",
    )
    result = evaluator(
        {
            "scene_revision": "scene-2",
            "collision_world": {
                "artifact_ref": "artifact://scene/world",
                "sha256": hashlib.sha256(world_bytes).hexdigest(),
            },
            "candidates": [
                {
                    "candidate_ref": "candidate://block/0",
                    "entity_ref": "entity://block",
                    "execution_grasp": {
                        "adaptation_provenance_ref": "artifact://adaptation/0"
                    },
                }
            ],
        }
    )

    assert events == [
        "configure_collision_world",
        "prepare_planning_world",
        "qualify_planner_world_contact",
    ]
    assert result["simulator_steps"] == 0
    assert result["motion_authorized"] is False


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
        observed_ref, observed_digest = artifact(revision + "-observed-world", {
            "scene_revision": revision, "source_scene_facts_ref": scene_ref,
            "source_scene_facts_sha256": scene_digest, "observed_collision": {},
        })
        with pytest.raises(planner.SimulationProbeError, match="requires observed collision geometry"):
            evaluator({**request, "collision_world": {"artifact_ref": observed_ref, "sha256": observed_digest}})
    assert checked == ["entity://block", "entity://block"]


def test_readiness_client_validates_live_world_evidence(tmp_path):
    from robotwin_route_readiness_worker import _handle_factory
    from test_route_readiness import _request

    from robotwin20_adapter.persistent_client import build_persistent_route_readiness

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
