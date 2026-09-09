import hashlib
import json
import subprocess
from copy import deepcopy

import pytest
import yaml
from test_arm_candidates import _intent, _profile
from test_route_inputs import _facts
from test_route_readiness import _request

from robotwin20_adapter.persistent_route_builder import BenchmarkSceneSource, PersistentRouteBuilder
from robotwin20_adapter.route_evidence import _artifact_path
from robotwin20_adapter.route_inputs import canonical_json
from robotwin20_adapter.route_readiness import route_geometry_digest


def test_benchmark_source_removes_only_provider_envelope():
    facts = _facts()

    class Client:
        def query(self, operation, arguments):
            assert operation == "benchmark_scene_facts"
            return {**deepcopy(facts), "holding_state": "empty", "owner": None,
                    "acquire_invocation_id": None, "entity_ref": None, "ok": True, "request_id": "transport-1"}

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


def test_finalize_binds_selected_request_and_never_issues_approval(tmp_path, monkeypatch):
    request, builder, _ = setup_builder(tmp_path, monkeypatch)
    bundle = builder.build(request)
    route = deepcopy(bundle["base_request"])
    original_id = route["request_id"]
    route["request_id"] += "-option-0-left"
    source = tmp_path / "source"
    source.mkdir()
    manifest = {"request_id": original_id, "candidate_ref": request["candidates"][0]["candidate_ref"],
                "scene_revision": request["scene_revision"], "motion_authorized": False}
    manifest_bytes = canonical_json(manifest)
    (source / "manifest.json").write_bytes(manifest_bytes)
    review = {**manifest, "decision": "pending_human_review", "source_manifest_ref": "artifact://source/manifest",
              "source_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest()}
    from pathlib import Path
    review_path = Path(bundle["reviews"][manifest["candidate_ref"]])
    review_path.write_text(json.dumps(review))
    for key in ("calibration_ref", "joint_limits_ref", "stop_policy_ref"):
        path = tmp_path / (route[key].removeprefix("artifact://") + ".json")
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text("{}")
    ref = builder.finalize(bundle, route)
    final = json.loads(_artifact_path(tmp_path, ref).read_text())
    assert final["request_id"] == route["request_id"]
    assert final["motion_authorized"] is False
    assert final["decision"] == "pending_human_review"
    assert final["route_geometry_digest"] == route_geometry_digest(route)
    final_manifest_path = _artifact_path(tmp_path, final["source_manifest_ref"])
    assert hashlib.sha256(final_manifest_path.read_bytes()).hexdigest() == final["source_manifest_sha256"]
    final_manifest = json.loads(final_manifest_path.read_text())
    final_route = _artifact_path(tmp_path, final_manifest["route_request"]["artifact_ref"])
    assert json.loads(final_route.read_text()) == route
    assert hashlib.sha256(final_route.read_bytes()).hexdigest() == final["route_request_sha256"]
    assert builder.finalize(bundle, route) == ref
    assert json.loads(review_path.read_text())["request_id"] == original_id
    (source / "manifest.json").write_text("{}")
    with pytest.raises(ValueError, match="differs from materializer"):
        builder.finalize(bundle, route)
