from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


RUNTIME = Path(__file__).parents[1] / "runtime"


def _module(name: str):
    path = RUNTIME / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"test_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Model:
    def __init__(self) -> None:
        self.devices: list[str] = []
        self.eval_calls = 0

    def to(self, device: str):
        self.devices.append(device)
        return self

    def eval(self):
        self.eval_calls += 1
        return self


def _fake_torch(monkeypatch):
    calls: list[str] = []
    module = SimpleNamespace(cuda=SimpleNamespace(empty_cache=lambda: calls.append("empty_cache")))
    monkeypatch.setitem(sys.modules, "torch", module)
    return calls


def test_locateanything_hibernates_to_cpu_and_wakes_on_configured_device(tmp_path, monkeypatch):
    worker_module = _module("locateanything_worker")
    empty_cache = _fake_torch(monkeypatch)
    worker = worker_module.LocateAnythingProposalWorker(
        model_id="local/model",
        revision="revision",
        device="cuda:0",
        cache_dir=tmp_path / "cache",
        modules_cache_dir=tmp_path / "modules",
        generation_mode="fast",
        max_new_tokens=32,
        repetition_penalty=1.0,
        temperature=1.0,
        top_p=1.0,
        decode_seed=0,
        local_files_only=True,
    )
    model = _Model()
    worker._model = model

    worker.sleep()
    worker.sleep()
    worker.wake()
    worker.wake()

    assert model.devices == ["cpu", "cuda:0"]
    assert model.eval_calls == 1
    assert empty_cache == ["empty_cache"]
    assert worker._sleeping is False


def test_sam2_resets_image_state_before_hibernation(tmp_path, monkeypatch):
    worker_module = _module("sam2_worker")
    empty_cache = _fake_torch(monkeypatch)
    repo = tmp_path / "sam2"
    repo.mkdir()
    checkpoint = tmp_path / "sam2.pt"
    checkpoint.write_bytes(b"checkpoint")
    worker = worker_module.Sam2BoxWorker(
        repo_root=repo,
        model_config="config.yaml",
        checkpoint=checkpoint,
        device="cuda:0",
        source_artifact_root=tmp_path,
        worker_artifact_root=tmp_path / "workers",
    )
    model = _Model()
    resets: list[bool] = []
    worker._predictor = SimpleNamespace(
        model=model,
        reset_predictor=lambda: resets.append(True),
    )

    worker.sleep()
    worker.wake()

    assert resets == [True]
    assert model.devices == ["cpu", "cuda:0"]
    assert model.eval_calls == 1
    assert empty_cache == ["empty_cache"]
    assert worker._sleeping is False
