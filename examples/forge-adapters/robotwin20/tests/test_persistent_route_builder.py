import json
import subprocess
from copy import deepcopy

import pytest
import yaml
from test_arm_candidates import _intent, _profile
from test_route_inputs import _facts
from test_route_readiness import _request

from robotwin20_adapter.persistent_route_builder import BenchmarkSceneSource, PersistentRouteBuilder


def test_benchmark_source_removes_only_provider_envelope():
    facts = _facts()

    class Client:
        def query(self, operation, arguments):
            assert operation == "benchmark_scene_facts"
            return {**deepcopy(facts), "holding_state": "empty", "owner": None,
                    "acquire_invocation_id": None, "entity_ref": None}

    assert BenchmarkSceneSource(Client())({"calibration_ref": facts["calibration_ref"]}) == facts


def setup_builder(tmp_path, monkeypatch):
    profile = tmp_path / "arms.yaml"
    profile.write_text(yaml.safe_dump(_profile()))
    route = _request(tmp_path)
    facts = _facts()
    facts["calibration_ref"] = route["calibration_ref"]
    facts["objects"][0]["entity_ref"] = _intent().entity_ref
    destination = facts["objects"][0]["target_ref"]
    route["candidates"][0]["placement_target"]["target_ref"] = destination
    request = {key: route[key] for key in (
        "scene_revision", "observation_ref", "calibration_ref", "candidate_set_ref",
    )}
    request.update(intent=_intent().model_dump(mode="json"), destination_ref=destination,
                   frame_id="head_camera", candidates=deepcopy(route["candidates"]))

    class Client:
        snapshot = {"scene_revision": route["scene_revision"], "holding_state": "empty"}

        def query(self, operation, arguments):
            return dict(self.snapshot)

    calls = []

    def materialize(argv, **kwargs):
        from pathlib import Path
        arguments = dict(zip(argv[1::2], argv[2::2]))
        calls.append(arguments)
        generated = deepcopy(route)
        generated["request_id"] = arguments["--request-id"]
        generated["candidates"][0]["candidate_ref"] = arguments["--candidate-ref"]
        output = Path(arguments["--artifact-root"])
        (output / "route_request.json").write_text(json.dumps(generated))
        (output / "shared").mkdir()
        (output / "shared/calibration.json").write_text("{}")

    monkeypatch.setattr(subprocess, "run", materialize)
    builder = PersistentRouteBuilder(
        client=Client(), artifact_root=tmp_path, scene_source=lambda request: deepcopy(facts),
        command=("materializer",), materializer_arguments={"arm-planning-profile": str(profile)},
    )
    return request, builder, calls


def test_build_all_candidates_and_import_shared_artifacts_without_overwrite(tmp_path, monkeypatch):
    request, builder, calls = setup_builder(tmp_path, monkeypatch)
    second = deepcopy(request["candidates"][0])
    second["candidate_ref"] += "-second"
    request["candidates"].append(second)
    first = builder.build(request)
    assert len(first["options"]) == 4
    assert len(calls) == 2
    assert first["destination_ref"] == request["destination_ref"]
    assert (tmp_path / "shared/calibration.json").read_text() == "{}"
    builder.build(request)
    assert len(list((tmp_path / "preparation-builds").iterdir())) == 2
    assert len({call["--artifact-root"] for call in calls}) == 4


def test_wrong_destination_never_runs_materializer(tmp_path, monkeypatch):
    request, builder, calls = setup_builder(tmp_path, monkeypatch)
    request["destination_ref"] = "destination://wrong"
    with pytest.raises(ValueError, match="not grounded"):
        builder.build(request)
    assert not calls


def test_scene_changed_during_build_never_imports_artifacts(tmp_path, monkeypatch):
    request, builder, _ = setup_builder(tmp_path, monkeypatch)
    original = subprocess.run

    def run(*args, **kwargs):
        original(*args, **kwargs)
        builder.client.snapshot["scene_revision"] = "changed"

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ValueError, match="current empty scene"):
        builder.build(request)
    assert not (tmp_path / "shared").exists()


def test_conflicting_artifact_is_preserved(tmp_path, monkeypatch):
    request, builder, _ = setup_builder(tmp_path, monkeypatch)
    (tmp_path / "shared").mkdir()
    target = tmp_path / "shared/calibration.json"
    target.write_text("original")
    with pytest.raises(ValueError, match="conflicts"):
        builder.build(request)
    assert target.read_text() == "original"


def test_failed_materializer_retains_log_and_returns_no_route(tmp_path, monkeypatch):
    request, builder, _ = setup_builder(tmp_path, monkeypatch)

    def fail(argv, **kwargs):
        kwargs["stdout"].write("calibration unavailable")
        raise subprocess.CalledProcessError(1, argv)

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        builder.build(request)
    logs = list((tmp_path / "preparation-builds").glob("*/materializer-0.log"))
    assert logs[0].read_text() == "calibration unavailable"
    assert not (tmp_path / "shared").exists()
