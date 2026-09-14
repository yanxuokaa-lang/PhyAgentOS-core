from pathlib import Path

import pytest

from robotwin20_adapter import (
    ArtifactPayload,
    Qwen3VLConfig,
    Qwen3VLInferenceError,
    Qwen3VLSceneUnderstandingInference,
)


REF = "artifact://scene-1/capture-1/rgb"
REQUEST = {
    "observation_ref": "observation://scene-1/head_camera",
    "scene_revision": "scene-1",
    "frame_id": "head_camera",
    "calibration_ref": "artifact://scene-1/capture-1/calibration",
    "freshness_ms": 2,
    "max_age_ms": 1000,
    "artifacts": [REF],
}


class Resolver:
    def resolve(self, ref):
        assert ref == REF
        return ArtifactPayload(b"png", "image/png", Path("/tmp/rgb.png"))


class Worker:
    def __init__(self, result):
        self.result = result
        self.requests = []
        self.released = 0

    def request(self, payload):
        self.requests.append(payload)
        return {"request_id": payload["request_id"], "status": "available", "result": self.result}

    def release(self):
        self.released += 1


def _config(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    return Qwen3VLConfig(model_path=str(tmp_path))


def _result():
    return {
        "entities": [{"entity_ref": "entity://red-block", "category": "red block", "confidence": 0.9}],
        "relations": [],
        "spatial_envelopes": [],
        "ambiguities": [],
    }


def test_qwen_provider_projects_semantic_claims_and_releases_worker(tmp_path):
    worker = Worker(_result())
    inference = Qwen3VLSceneUnderstandingInference(
        Resolver(), config=_config(tmp_path), worker=worker
    )
    result = inference.infer(REQUEST)
    assert result["entities"][0]["provenance"] == [REF]
    assert result["spatial_envelopes"] == []
    assert worker.requests[0]["rgb_path"] == "/tmp/rgb.png"
    assert worker.released == 1


def test_qwen_provider_rejects_metric_claims(tmp_path):
    result = _result()
    result["spatial_envelopes"] = [{"entity_ref": "entity://red-block"}]
    worker = Worker(result)
    inference = Qwen3VLSceneUnderstandingInference(
        Resolver(), config=_config(tmp_path), worker=worker
    )
    with pytest.raises(Qwen3VLInferenceError, match="metric spatial envelopes"):
        inference.infer(REQUEST)
    assert worker.released == 1


def test_qwen_provider_rejects_unknown_relation_entity(tmp_path):
    result = _result()
    result["relations"] = [{
        "relation_ref": "relation://left",
        "subject_ref": "entity://red-block",
        "predicate": "left_of",
        "object_ref": "entity://missing",
        "confidence": 0.8,
    }]
    inference = Qwen3VLSceneUnderstandingInference(
        Resolver(), config=_config(tmp_path), worker=Worker(result)
    )
    with pytest.raises(Qwen3VLInferenceError, match="unknown entity"):
        inference.infer(REQUEST)


def test_qwen_config_requires_model_directory(tmp_path):
    with pytest.raises(ValueError, match="config.json"):
        Qwen3VLConfig(model_path=str(tmp_path)).validate()
