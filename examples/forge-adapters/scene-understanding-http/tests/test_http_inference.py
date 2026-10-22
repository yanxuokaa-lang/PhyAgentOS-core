import base64
import io
import json
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace

import httpx
import numpy as np
import pytest
from isaacsim_lab.observation import (
    FilesystemObservationArtifactWriter,
    IsaacCameraObservationSource,
)
from PhyAgentOS.forge.artifacts import ArtifactContent, LocalFilesystemArtifactResolver
from PhyAgentOS.forge.capability_runtime import (
    ObservationEndpoint,
    SceneUnderstandingEndpoint,
    SceneUnderstandingInferenceRegistry,
)
from PIL import Image

from paos_http_understanding.factory import HttpJsonInferenceFactory


def test_real_local_http_round_trip_preserves_observation_lineage_and_artifact(tmp_path):
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            request = json.loads(self.rfile.read(length))
            received.update(request)
            artifact_ref = request["artifacts"][0]
            body = json.dumps({
                "entities": [{
                    "entity_ref": "entity://observed-bottle-1",
                    "category": "bottle",
                    "confidence": 0.93,
                    "provenance": [artifact_ref],
                }],
                "relations": [],
                "spatial_envelopes": [],
                "ambiguities": [],
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        artifact_root = tmp_path / "observations"
        writer = FilesystemObservationArtifactWriter(artifact_root, namespace="capture")

        class Camera:
            def get_rgb(self):
                return np.asarray([[[1, 2, 3]]], dtype=np.uint8)

        source = IsaacCameraObservationSource(
            {"camera/front": Camera()},
            lambda _ref: {
                "scene_revision": "live-scene-1",
                "frame_id": "camera-front",
                "calibration_ref": "artifact://capture/calibration/front.json",
            },
            writer,
        )
        observation = ObservationEndpoint(source).invoke({
            "sensor_ref": "camera/front",
            "max_age_ms": 100,
        })
        assert observation["status"] == "available"
        assert observation["observation_ref"] == "observation://live-scene-1/camera-front"

        registry = SceneUnderstandingInferenceRegistry()
        registry.register(HttpJsonInferenceFactory())
        provider = registry.compose(
            "http_json",
            resolver=LocalFilesystemArtifactResolver({"capture": artifact_root}),
            configuration={"endpoint": f"http://127.0.0.1:{server.server_address[1]}"},
        )
        result = SceneUnderstandingEndpoint(provider).invoke({
            "observation_ref": observation["observation_ref"],
            "scene_revision": observation["scene_revision"],
            "frame_id": observation["frame"]["frame_id"],
            "calibration_ref": observation["calibration_ref"],
            "freshness_ms": observation["freshness_ms"],
            "max_age_ms": 100,
            "artifacts": [item["ref"] for item in observation["artifacts"]],
        })
        assert result["status"] == "available"
        assert result["observation_ref"] == observation["observation_ref"]
        assert received["scene_revision"] == "live-scene-1"
        assert received["frame_id"] == "camera-front"
        assert received["calibration_ref"] == observation["calibration_ref"]
        assert received["observation_ref"] == observation["observation_ref"]
        assert received["resolved_artifacts"][0]["ref"] == observation["artifacts"][0]["ref"]
        assert received["resolved_artifacts"][0]["media_type"] == "image/png"
        image_bytes = base64.b64decode(received["resolved_artifacts"][0]["data_base64"])
        with Image.open(io.BytesIO(image_bytes)) as image:
            assert image.mode == "RGB"
            assert image.getpixel((0, 0)) == (1, 2, 3)
        assert result["entities"][0]["entity_ref"] == "entity://observed-bottle-1"
        assert result["entities"][0]["provenance"] == [observation["artifacts"][0]["ref"]]
    finally:
        server.shutdown()
        server.server_close()


def test_http_factory_composes_through_registry_and_transports_artifact_bytes(monkeypatch):
    captured = {}

    def post(endpoint, *, json, headers, timeout):
        captured.update(endpoint=endpoint, json=json, headers=headers, timeout=timeout)
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "entities": [{
                    "entity_ref": "entity://bottle-1",
                    "category": "bottle",
                    "confidence": 0.9,
                    "provenance": ["artifact://scene/front"],
                }],
                "relations": [],
                "spatial_envelopes": [],
                "ambiguities": [],
            },
        )

    monkeypatch.setattr("paos_http_understanding.factory.httpx.post", post)
    registry = SceneUnderstandingInferenceRegistry()
    registry.register(HttpJsonInferenceFactory())

    class Resolver:
        def resolve(self, artifact_ref):
            return ArtifactContent(b"rgb-image", "image/png") if artifact_ref == "artifact://scene/front" else None

    provider = registry.compose(
        "http_json",
        resolver=Resolver(),
        configuration={
            "endpoint": "https://inference.example/understand",
            "timeout_s": 4,
            "headers": {"X-Deployment": "lab"},
        },
    )
    result = SceneUnderstandingEndpoint(provider).invoke({
        "observation_ref": "observation://revision-1/front",
        "scene_revision": "revision-1",
        "frame_id": "front",
        "calibration_ref": "artifact://scene/calibration.json",
        "freshness_ms": 5,
        "max_age_ms": 100,
        "artifacts": ["artifact://scene/front"],
    })

    assert result["status"] == "available"
    assert result["entities"][0]["entity_ref"] == "entity://bottle-1"
    assert captured["endpoint"] == "https://inference.example/understand"
    assert captured["timeout"] == 4.0
    assert captured["headers"] == {"X-Deployment": "lab"}
    artifact = captured["json"]["resolved_artifacts"][0]
    assert artifact["data_base64"] == "cmdiLWltYWdl"
    assert "data" not in artifact


def test_http_factory_reads_deployment_credential_without_exposing_it(monkeypatch):
    monkeypatch.setenv("SCENE_TOKEN", "secret-value")
    inference = HttpJsonInferenceFactory().create(configuration={
        "endpoint": "https://inference.example/understand",
        "token_env": "SCENE_TOKEN",
    })
    assert inference.headers == {"Authorization": "Bearer secret-value"}


@pytest.mark.parametrize(
    "configuration,match",
    [
        ({}, "endpoint must be a URL"),
        ({"endpoint": "ftp://host/path"}, "must use http or https"),
        ({"endpoint": "https://host", "timeout_s": 0}, "positive finite number"),
        ({"endpoint": "https://host", "timeout_s": float("nan")}, "positive finite number"),
        ({"endpoint": "https://host", "headers": {"X": 1}}, "string mapping"),
    ],
)
def test_http_factory_rejects_invalid_deployment_configuration(configuration, match):
    with pytest.raises(ValueError, match=match):
        HttpJsonInferenceFactory().create(configuration=configuration)


def test_package_metadata_registers_provider_neutral_entry_point():
    project = Path(__file__).resolve().parents[1] / "pyproject.toml"
    metadata = tomllib.loads(project.read_text(encoding="utf-8"))
    assert metadata["project"]["entry-points"]["paos.scene_understanding_inference"]["http_json"] == (
        "paos_http_understanding.factory:HttpJsonInferenceFactory"
    )


def test_http_factory_fails_when_configured_credential_is_missing(monkeypatch):
    monkeypatch.delenv("SCENE_TOKEN", raising=False)
    with pytest.raises(ValueError, match="credential is not configured: SCENE_TOKEN"):
        HttpJsonInferenceFactory().create(configuration={
            "endpoint": "https://inference.example/understand",
            "token_env": "SCENE_TOKEN",
        })


def test_http_inference_propagates_transport_and_response_errors(monkeypatch):
    inference = HttpJsonInferenceFactory().create(configuration={"endpoint": "https://host"})

    def transport_error(*_args, **_kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr("paos_http_understanding.factory.httpx.post", transport_error)
    with pytest.raises(RuntimeError, match="network unavailable"):
        inference.infer({"resolved_artifacts": []})

    status_error = httpx.HTTPStatusError(
        "503 service unavailable",
        request=httpx.Request("POST", "https://host"),
        response=httpx.Response(503, request=httpx.Request("POST", "https://host")),
    )
    monkeypatch.setattr(
        "paos_http_understanding.factory.httpx.post",
        lambda *_args, **_kwargs: SimpleNamespace(raise_for_status=lambda: (_ for _ in ()).throw(status_error)),
    )
    with pytest.raises(httpx.HTTPStatusError, match="503 service unavailable"):
        inference.infer({"resolved_artifacts": []})

    monkeypatch.setattr(
        "paos_http_understanding.factory.httpx.post",
        lambda *_args, **_kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: ["not", "an", "object"],
        ),
    )
    with pytest.raises(TypeError, match="must be a JSON object"):
        inference.infer({"resolved_artifacts": []})
