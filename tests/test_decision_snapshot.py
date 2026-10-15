from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from PhyAgentOS.agent import decision_snapshot as snapshot


def config(tmp_path, **overrides):
    profile = tmp_path / "profile.yaml"
    profile.write_text("seed: 0\n", encoding="utf-8")
    return snapshot.SnapshotConfig(
        adapter_root=tmp_path, adapter_source_commit="declared-fixture",
        runtime_root=tmp_path, runtime_profile=profile,
        worker_python=tmp_path / "python", output_root=tmp_path / "runs", **overrides,
    )


@pytest.mark.parametrize("url", [
    "https://remote.example/v1", "http://localhost/v1", "http://127.0.0.1.evil/v1",
    "http://user:secret@127.0.0.1/v1", "ftp://127.0.0.1/v1",
])
def test_raw_images_cannot_be_redirected_to_remote_services(tmp_path, url):
    with pytest.raises(ValidationError, match="literal loopback"):
        config(tmp_path, local_api_base=url)


def test_captures_are_unique_and_not_host_measurements(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "_capture", lambda *_: {
        "status": "captured", "view_count": 2, "entity_count": 3,
    })
    first = snapshot.capture_snapshot(config(tmp_path), repo_root=tmp_path)
    second = snapshot.capture_snapshot(config(tmp_path), repo_root=tmp_path)
    assert first != second
    summary = json.loads((first / "summary.json").read_text())
    assert summary["status"] == "captured"
    assert summary["host_selection_measured"] is False
    assert summary["remote_model_calls"] == summary["action_calls"] == summary["session_calls"] == 0
    assert (first / "collector_source.py").exists()
    assert json.loads((first / "query_tool_specs.json").read_text())["scene.observe"]["semantics"] == "query"


@pytest.mark.parametrize("error", [RuntimeError("sensor failure"), KeyboardInterrupt()])
def test_failed_or_interrupted_capture_leaves_summary(tmp_path, monkeypatch, error):
    def fail(*_):
        raise error

    monkeypatch.setattr(snapshot, "_capture", fail)
    settings = config(tmp_path)
    if isinstance(error, KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            snapshot.capture_snapshot(settings, repo_root=tmp_path)
        run_dir = next(settings.output_root.iterdir())
        expected = "interrupted"
    else:
        run_dir = snapshot.capture_snapshot(settings, repo_root=tmp_path)
        expected = "failed"
    assert json.loads((run_dir / "summary.json").read_text())["status"] == expected


def test_unavailable_observation_closes_worker_without_model_or_action(tmp_path, monkeypatch):
    calls = []

    class Client:
        def __init__(self, worker):
            pass

        def query(self, operation, request):
            calls.append((operation, request))
            return {"status": "unavailable"}

        def close(self):
            calls.append(("close", None))

    modules = {
        "robotwin20_adapter": SimpleNamespace(
            Qwen3VLVLLMConfig=None, Qwen3VLVLLMSceneUnderstandingInference=None,
        ),
        "robotwin20_adapter.openai_scene_understanding": SimpleNamespace(FilesystemArtifactResolver=None),
        "robotwin20_adapter.persistent_client": SimpleNamespace(PersistentWorkerClient=Client),
        "robotwin20_adapter.process_worker": SimpleNamespace(
            JsonlProcessWorkerClient=lambda _: SimpleNamespace(stderr_tail=[]),
            ProcessWorkerConfig=lambda **kwargs: kwargs,
        ),
        "robotwin20_adapter.runtime_profile": SimpleNamespace(load_runtime_profile=lambda _: {
            "sensor_refs": ["camera/head", "camera/front"], "max_observation_age_ms": 1000,
        }),
        "robotwin20_adapter.understanding": SimpleNamespace(RoboTwinSceneUnderstandingProvider=None),
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(snapshot, "ObservationEndpoint", lambda provider: SimpleNamespace(invoke=provider.capture))
    settings = config(tmp_path)
    run_dir = snapshot.capture_snapshot(settings, repo_root=tmp_path)
    assert json.loads((run_dir / "summary.json").read_text())["status"] == "observation_unavailable"
    assert [call[0] for call in calls] == ["observe", "close"]
    assert calls[0][1]["sensor_refs"] == ["camera/head", "camera/front"]
    assert (run_dir / "worker.log").exists()
