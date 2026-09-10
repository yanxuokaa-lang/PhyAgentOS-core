from __future__ import annotations

import asyncio
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import yaml
from PhyAgentOS.forge.capability_runtime import CapabilityRuntime, CapabilityRuntimeTransport

import robotwin20_adapter.persistent_host as host_module
from robotwin20_adapter.persistent_deployment import PersistentDeployment
from robotwin20_adapter.persistent_host import (
    PersistentHost,
    PersistentHostConfigurationError,
    build_http_server,
    build_persistent_host,
    load_persistent_host_profile,
    serve_persistent_host,
)


def _profile(tmp_path: Path) -> tuple[dict, dict[str, str]]:
    adapter_root = Path(__file__).resolve().parents[1]
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    files = {}
    for name in ("runtime.yaml", "perception.yaml", "grasp.yaml", "arms.yaml"):
        files[name] = tmp_path / name
        files[name].write_text("{}\n", encoding="utf-8")
    materializer = tmp_path / "materializer.yaml"
    materializer.write_text(
        yaml.safe_dump(
            {
                "arm-planning-profile": str(files["arms.yaml"]),
                "route-input-profile": str(files["runtime.yaml"]),
            }
        ),
        encoding="utf-8",
    )
    profile = {
        "schema_version": "paos-robotwin20-persistent-host/v1",
        "agent": {"enabled": False},
        "tools": {"enabled": True},
        "host": "127.0.0.1",
        "port": 19020,
        "artifact_root": str(tmp_path / "artifacts"),
        "adapter_root": str(adapter_root),
        "runtime_root": str(runtime_root),
        "runtime_profile": str(files["runtime.yaml"]),
        "worker_python": sys.executable,
        "materializer_python": sys.executable,
        "perception_profile": str(files["perception.yaml"]),
        "grasp_profile": str(files["grasp.yaml"]),
        "materializer_arguments": str(materializer),
        "model": {
            "api_base": "https://models.invalid/v1",
            "model": "test-model",
            "api_key_env": "ROBOTWIN20_MODEL_API_KEY",
            "reasoning_effort": "low",
            "timeout_seconds": 5,
            "max_output_tokens": 128,
        },
        "worker": {
            "startup_timeout_s": 5,
            "request_timeout_s": 5,
            "shutdown_timeout_s": 5,
            "action_max_duration_s": 7,
        },
        "materializer_timeout_s": 5,
        "allow_benchmark_scene_facts": True,
    }
    return profile, {"ROBOTWIN20_MODEL_API_KEY": "test-secret"}


def test_profile_loader_requires_all_declared_environment(tmp_path):
    profile_path = tmp_path / "host.yaml"
    profile_path.write_text(
        """schema_version: paos-robotwin20-persistent-host/v1
agent: {enabled: false}
tools: {enabled: true}
host: 127.0.0.1
port: 19020
artifact_root: ${ARTIFACT_ROOT}
adapter_root: ${ADAPTER_ROOT}
runtime_root: /runtime
runtime_profile: /runtime.yaml
worker_python: /python
materializer_python: /paos-python
perception_profile: /perception.yaml
grasp_profile: /grasp.yaml
materializer_arguments: /materializer.yaml
model: {api_base: https://models.invalid/v1, model: test, api_key_env: KEY, reasoning_effort: low, timeout_seconds: 5, max_output_tokens: 128}
worker: {startup_timeout_s: 5, request_timeout_s: 5, shutdown_timeout_s: 5, action_max_duration_s: 7}
materializer_timeout_s: 5
allow_benchmark_scene_facts: true
""",
        encoding="utf-8",
    )
    with pytest.raises(PersistentHostConfigurationError, match="environment variable"):
        load_persistent_host_profile(profile_path, environ={"ARTIFACT_ROOT": "/artifacts"})
    loaded = load_persistent_host_profile(
        profile_path,
        environ={"ARTIFACT_ROOT": "/artifacts", "ADAPTER_ROOT": "/adapter"},
    )
    assert loaded["artifact_root"] == "/artifacts"
    assert loaded["agent"] == {"enabled": False}
    assert loaded["tools"] == {"enabled": True}


def test_host_composes_seven_tools_around_one_persistent_worker_client(tmp_path, monkeypatch):
    profile, environ = _profile(tmp_path)
    closed = []

    class Client:
        _transport_lost = False

        def query(self, operation, arguments):
            assert operation == "snapshot"
            assert arguments == {}
            return {"scene_revision": "runtime-1", "holding_state": "empty"}

        def close(self):
            closed.append(True)

    client = Client()
    worker_configs = []
    monkeypatch.setattr(
        host_module,
        "JsonlProcessWorkerClient",
        lambda config: worker_configs.append(config) or object(),
    )
    monkeypatch.setattr(host_module, "PersistentWorkerClient", lambda _worker: client)
    monkeypatch.setattr(host_module, "load_perception_profile", lambda _path: {})
    monkeypatch.setattr(host_module, "build_single_view_perception", lambda *_args, **_kwargs: lambda _request: {})
    monkeypatch.setattr(host_module, "load_grasp_profile", lambda _path: {})
    monkeypatch.setattr(
        host_module,
        "build_grasp_provider",
        lambda *_args, **_kwargs: SimpleNamespace(propose=lambda _request: None),
    )

    class Provider:
        def __init__(self):
            self.client = client

        def prepare(self, _request):
            return None

        def describe(self, _request):
            return None

        def __call__(self, _phase, _request):
            return {}

    preparation = Provider()
    capability = Provider()
    routes = Provider()
    deployment = PersistentDeployment(preparation, capability, routes)
    captured = {}

    def deployment_factory(**kwargs):
        captured.update(kwargs)
        return deployment

    monkeypatch.setattr(host_module, "build_persistent_deployment", deployment_factory)

    host = build_persistent_host(profile, environ=environ)

    assert captured["client"] is client
    assert len(worker_configs) == 1
    assert {item["tool_id"] for item in host.bundle.runtime.list_tools()["tools"]} == {
        "scene.observe",
        "manipulation.capabilities",
        "scene.understand",
        "grasp.propose",
        "manipulation.prepare",
        "object.acquire",
        "object.place",
    }
    assert all(
        host.bundle.runtime.get_context(item["tool_id"])["motion_authorized"] is False
        for item in host.bundle.runtime.list_tools()["tools"]
    )
    worker_profile = json.loads(
        (tmp_path / "artifacts" / "persistent-host-runtime.json").read_text(
            encoding="utf-8"
        )
    )
    assert worker_profile["allow_benchmark_scene_facts"] is True
    assert worker_profile["max_duration_s"] == 7
    client._transport_lost = True
    assert host.bundle.runtime.get_context("scene.observe") == {
        "ready": False,
        "binding_error": "persistent_world_connection_lost",
        "max_concurrency": 1,
        "motion_authorized": False,
        "provider_lifetime": "persistent",
        "tool_id": "scene.observe",
    }
    host.close()
    assert closed == [True]


def test_http_server_serializes_requests_for_the_shared_world():
    class DetectConcurrentDispatch(httpx.AsyncBaseTransport):
        def __init__(self):
            self.active = 0
            self.max_active = 0
            self.lock = threading.Lock()

        async def handle_async_request(self, request):
            del request
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            await asyncio.sleep(0.05)
            with self.lock:
                self.active -= 1
            return httpx.Response(200, json={"data": {"tools": []}})

    transport = DetectConcurrentDispatch()
    host = PersistentHost(
        client=SimpleNamespace(close=lambda: None),
        bundle=SimpleNamespace(transport=transport),
    )
    server = build_http_server(host, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/tools"
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(
                executor.map(
                    lambda _index: httpx.get(url, timeout=2, trust_env=False),
                    range(2),
                )
            )
        assert [response.status_code for response in responses] == [200, 200]
        assert transport.max_active == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_server_exposes_gateway_compatible_discovery_and_closes_explicitly():
    runtime = CapabilityRuntime()
    transport = CapabilityRuntimeTransport(runtime, gateway_identity="persistent-test")
    closed = []
    host = PersistentHost(
        client=SimpleNamespace(close=lambda: closed.append(True)),
        bundle=SimpleNamespace(transport=transport),
    )
    server = build_http_server(host, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        response = httpx.get(
            f"http://127.0.0.1:{server.server_port}/tools",
            timeout=2,
            trust_env=False,
        )
        assert response.status_code == 200
        assert response.json()["data"] == {
            "gateway_identity": "persistent-test",
            "tools": [],
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        host.close()
    assert closed == [True]


def test_serve_closes_persistent_world_when_http_bind_fails(monkeypatch):
    closed = []
    host = PersistentHost(
        client=SimpleNamespace(close=lambda: closed.append(True)),
        bundle=SimpleNamespace(transport=object()),
    )
    monkeypatch.setattr(
        host_module,
        "build_http_server",
        lambda *_args: (_ for _ in ()).throw(OSError("address in use")),
    )

    with pytest.raises(OSError, match="address in use"):
        serve_persistent_host(host, "127.0.0.1", 19020)

    assert closed == [True]
