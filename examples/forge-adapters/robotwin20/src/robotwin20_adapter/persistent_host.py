"""Deploy the persistent RoboTwin adapter behind the standard Forge HTTP API."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import signal
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Lock
from typing import Any, Mapping
from urllib.parse import urlsplit

import httpx

from .grasp_profile import build_grasp_provider, load_grasp_profile
from .openai_scene_understanding import (
    FilesystemArtifactResolver,
    OpenAIResponsesConfig,
    OpenAIResponsesSceneUnderstandingInference,
)
from .perception_profile import build_single_view_perception, load_perception_profile
from .persistent_client import PersistentWorkerClient
from .persistent_deployment import (
    PersistentRuntimeBundle,
    build_persistent_deployment,
    build_persistent_runtime_bundle,
)
from .persistent_route_builder import BenchmarkSceneSource
from .process_worker import JsonlProcessWorkerClient, ProcessWorkerConfig
from .understanding import RoboTwinSceneUnderstandingProvider

PROFILE_SCHEMA_VERSION = "paos-robotwin20-persistent-host/v1"
MAX_REQUEST_BYTES = 1_048_576


class PersistentHostConfigurationError(ValueError):
    """The adapter host profile cannot construct a persistent deployment."""


@dataclass(frozen=True)
class PersistentHost:
    """One worker/client/Runtime lifetime owned by the adapter process."""

    client: PersistentWorkerClient
    bundle: PersistentRuntimeBundle

    def close(self) -> None:
        self.client.close()


def _expand(value: Any, environ: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        expanded = os.path.expandvars(value) if environ is os.environ else value
        for name, item in environ.items():
            expanded = expanded.replace("${" + name + "}", item)
        if "${" in expanded:
            raise PersistentHostConfigurationError(
                f"host profile environment variable is unavailable: {expanded}"
            )
        return expanded
    if isinstance(value, list):
        return [_expand(item, environ) for item in value]
    if isinstance(value, dict):
        return {key: _expand(item, environ) for key, item in value.items()}
    return value


def load_persistent_host_profile(
    path: str | os.PathLike[str], *, environ: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Load the strict adapter-owned host profile and resolve its environment."""

    profile_path = Path(path)
    if not profile_path.is_absolute():
        profile_path = profile_path.resolve()
    if not profile_path.is_file():
        raise PersistentHostConfigurationError("persistent host profile is unavailable")
    try:
        import yaml
    except ImportError as exc:
        raise PersistentHostConfigurationError("PyYAML is required for host profiles") from exc
    try:
        raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise PersistentHostConfigurationError("persistent host profile could not be loaded") from exc
    if not isinstance(raw, dict):
        raise PersistentHostConfigurationError("persistent host profile must contain an object")
    profile = _expand(raw, os.environ if environ is None else environ)
    required = {
        "schema_version",
        "agent",
        "tools",
        "host",
        "port",
        "artifact_root",
        "adapter_root",
        "runtime_root",
        "runtime_profile",
        "worker_python",
        "materializer_python",
        "perception_profile",
        "grasp_profile",
        "materializer_arguments",
        "model",
        "worker",
        "materializer_timeout_s",
        "allow_benchmark_scene_facts",
    }
    if set(profile) != required or profile.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise PersistentHostConfigurationError("persistent host profile fields are invalid")
    return profile


def _path(value: Any, label: str, *, directory: bool = False) -> Path:
    if not isinstance(value, str) or not value:
        raise PersistentHostConfigurationError(f"{label} must be an absolute path")
    path = Path(value)
    if not path.is_absolute() or (not path.is_dir() if directory else not path.is_file()):
        kind = "directory" if directory else "file"
        raise PersistentHostConfigurationError(f"{label} must be an existing absolute {kind}")
    return path.resolve()


def _positive_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise PersistentHostConfigurationError(f"{label} must be positive")
    return float(value)


def build_persistent_host(
    profile: Mapping[str, Any], *, environ: Mapping[str, str] | None = None
) -> PersistentHost:
    """Construct the adapter providers and seven Tools around one worker client.

    Startup creates and validates the world with one read-only snapshot. It does not
    issue an Action or motion; Actions still require externally bound approval.
    """

    variables = dict(os.environ if environ is None else environ)
    if profile.get("agent") != {"enabled": False} or profile.get("tools") != {
        "enabled": True
    }:
        raise PersistentHostConfigurationError(
            "persistent host must expose Tool API only"
        )
    if profile.get("allow_benchmark_scene_facts") is not True:
        raise PersistentHostConfigurationError(
            "this host requires explicit benchmark scene-fact projection"
        )
    adapter_root = _path(profile.get("adapter_root"), "adapter_root", directory=True)
    artifact_root = Path(str(profile.get("artifact_root")))
    if not artifact_root.is_absolute():
        raise PersistentHostConfigurationError("artifact_root must be absolute")
    artifact_root.mkdir(parents=True, exist_ok=True)
    runtime_root = _path(profile.get("runtime_root"), "runtime_root", directory=True)
    runtime_profile = _path(profile.get("runtime_profile"), "runtime_profile")
    worker_python = _path(profile.get("worker_python"), "worker_python")
    materializer_python = _path(
        profile.get("materializer_python"), "materializer_python"
    )
    perception_profile = _path(profile.get("perception_profile"), "perception_profile")
    grasp_profile = _path(profile.get("grasp_profile"), "grasp_profile")
    materializer_profile = _path(
        profile.get("materializer_arguments"), "materializer_arguments"
    )

    worker_settings = profile.get("worker")
    if not isinstance(worker_settings, Mapping) or set(worker_settings) != {
        "startup_timeout_s",
        "request_timeout_s",
        "shutdown_timeout_s",
        "action_max_duration_s",
    }:
        raise PersistentHostConfigurationError("worker settings are invalid")
    worker_runtime_profile = artifact_root / "persistent-host-runtime.json"
    worker_runtime_profile.write_text(
        json.dumps(
            {
                "runtime_root": str(runtime_root),
                "runtime_profile": str(runtime_profile),
                "artifact_root": str(artifact_root),
                "max_duration_s": _positive_number(
                    worker_settings["action_max_duration_s"],
                    "worker.action_max_duration_s",
                ),
                "stop_file": str(artifact_root / "persistent-host.stop"),
                "allow_benchmark_scene_facts": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    worker = JsonlProcessWorkerClient(
        ProcessWorkerConfig(
            command=(
                str(worker_python),
                str(adapter_root / "runtime" / "robotwin_persistent_worker.py"),
                "--profile",
                str(worker_runtime_profile),
            ),
            cwd=adapter_root / "runtime",
            environment={
                "PYTHONPATH": f"{adapter_root / 'src'}:{adapter_root / 'runtime'}",
                "PYTHONUNBUFFERED": "1",
            },
            startup_timeout_s=_positive_number(
                worker_settings["startup_timeout_s"], "worker.startup_timeout_s"
            ),
            request_timeout_s=_positive_number(
                worker_settings["request_timeout_s"], "worker.request_timeout_s"
            ),
            shutdown_timeout_s=_positive_number(
                worker_settings["shutdown_timeout_s"], "worker.shutdown_timeout_s"
            ),
        )
    )
    client = PersistentWorkerClient(worker)
    try:
        snapshot = client.query("snapshot", {})
        if (
            not isinstance(snapshot.get("scene_revision"), str)
            or not snapshot["scene_revision"]
            or snapshot.get("holding_state") not in {"empty", "holding"}
        ):
            raise PersistentHostConfigurationError(
                "persistent worker returned an invalid startup snapshot"
            )
        model = profile.get("model")
        if not isinstance(model, Mapping) or set(model) != {
            "api_base",
            "model",
            "api_key_env",
            "reasoning_effort",
            "timeout_seconds",
            "max_output_tokens",
        }:
            raise PersistentHostConfigurationError("model settings are invalid")
        api_key_env = str(model["api_key_env"])
        if not variables.get(api_key_env):
            raise PersistentHostConfigurationError(
                f"model credential environment is unavailable: {api_key_env}"
            )
        inference = OpenAIResponsesSceneUnderstandingInference(
            FilesystemArtifactResolver(artifact_root),
            config=OpenAIResponsesConfig(
                api_base=str(model["api_base"]),
                model=str(model["model"]),
                api_key_env=api_key_env,
                reasoning_effort=str(model["reasoning_effort"]),
                timeout_seconds=_positive_number(model["timeout_seconds"], "model.timeout_seconds"),
                max_output_tokens=int(_positive_number(
                    model["max_output_tokens"], "model.max_output_tokens"
                )),
            ),
        )
        understanding = RoboTwinSceneUnderstandingProvider(
            build_single_view_perception(
                inference,
                load_perception_profile(perception_profile),
                environ=variables,
            )
        )
        grasp = build_grasp_provider(load_grasp_profile(grasp_profile), environ=variables)
        try:
            import yaml
        except ImportError as exc:
            raise PersistentHostConfigurationError(
                "PyYAML is required for materializer arguments"
            ) from exc
        try:
            materializer_arguments = yaml.safe_load(
                materializer_profile.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise PersistentHostConfigurationError(
                "materializer arguments could not be loaded"
            ) from exc
        if not isinstance(materializer_arguments, dict):
            raise PersistentHostConfigurationError("materializer arguments must be an object")
        materializer_arguments = _expand(materializer_arguments, variables)
        deployment = build_persistent_deployment(
            client=client,
            artifact_root=artifact_root,
            scene_source=BenchmarkSceneSource(client),
            materializer_command=(
                str(materializer_python),
                str(adapter_root / "scripts" / "materialize_complete_route.py"),
            ),
            materializer_arguments=materializer_arguments,
            arm_profile_digest=hashlib.sha256(
                Path(materializer_arguments["arm-planning-profile"]).read_bytes()
            ).hexdigest(),
            materializer_timeout_s=_positive_number(
                profile["materializer_timeout_s"], "materializer_timeout_s"
            ),
        )

        def context(tool_id: str) -> dict[str, Any]:
            transport_lost = getattr(client, "_transport_lost", False) is True
            return {
                "ready": not transport_lost,
                "binding_error": (
                    "persistent_world_connection_lost" if transport_lost else None
                ),
                "max_concurrency": 1,
                "motion_authorized": False,
                "provider_lifetime": "persistent",
                "tool_id": tool_id,
            }

        bundle = build_persistent_runtime_bundle(
            deployment=deployment,
            client=client,
            understanding_provider=understanding,
            grasp_provider=grasp,
            tool_context_provider=context,
        )
    except Exception:
        client.close()
        raise
    return PersistentHost(client=client, bundle=bundle)


def _handler(transport: httpx.AsyncBaseTransport) -> type[BaseHTTPRequestHandler]:
    dispatch_lock = Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self._dispatch()

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch()

        def _dispatch(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(400)
                return
            if length < 0 or length > MAX_REQUEST_BYTES:
                self.send_error(413)
                return
            content = self.rfile.read(length) if length else b""
            request = httpx.Request(
                self.command,
                "http://persistent-runtime" + urlsplit(self.path).path,
                headers=dict(self.headers),
                content=content,
            )
            with dispatch_lock:
                response = asyncio.run(transport.handle_async_request(request))
            body = response.content
            self.send_response(response.status_code)
            self.send_header("Content-Type", response.headers.get("content-type", "application/json"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

    return Handler


def build_http_server(
    host: PersistentHost, bind_host: str, port: int
) -> ThreadingHTTPServer:
    """Bind the Gateway-compatible HTTP surface without starting its loop."""

    if not isinstance(bind_host, str) or not bind_host:
        raise PersistentHostConfigurationError("host must be a non-empty string")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise PersistentHostConfigurationError("port must be between 0 and 65535")
    return ThreadingHTTPServer((bind_host, port), _handler(host.bundle.transport))


def serve_persistent_host(host: PersistentHost, bind_host: str, port: int) -> None:
    """Serve until SIGINT/SIGTERM, then close the caller-owned persistent world."""

    stop = Event()
    try:
        server = build_http_server(host, bind_host, port)
    except Exception:
        host.close()
        raise
    server.timeout = 0.5
    previous = {}

    def request_stop(_signum: int, _frame: object) -> None:
        stop.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous[signum] = signal.signal(signum, request_stop)
    try:
        while not stop.is_set():
            server.handle_request()
    finally:
        server.server_close()
        host.close()
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, type=Path)
    args = parser.parse_args()
    profile = load_persistent_host_profile(args.profile)
    host = profile["host"]
    port = profile["port"]
    if not isinstance(host, str) or not host or isinstance(port, bool) or not isinstance(port, int):
        raise PersistentHostConfigurationError("host and port are invalid")
    serve_persistent_host(build_persistent_host(profile), host, port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PROFILE_SCHEMA_VERSION",
    "PersistentHost",
    "PersistentHostConfigurationError",
    "build_http_server",
    "build_persistent_host",
    "load_persistent_host_profile",
    "serve_persistent_host",
]
