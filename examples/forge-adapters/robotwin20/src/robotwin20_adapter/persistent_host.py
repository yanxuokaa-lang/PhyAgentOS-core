"""Deploy the persistent RoboTwin adapter behind the standard Forge HTTP API."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import signal
from dataclasses import dataclass, field
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
from .oracle_grasp import PersistentOracleGraspProvider
from .perception_profile import build_single_view_perception, load_perception_profile
from .persistent_action_approval import (
    DISABLED_ACTION_MODE,
    RUNTIME_MONITORED_ACTION_MODE,
)
from .persistent_client import PersistentWorkerClient
from .persistent_deployment import (
    PersistentRuntimeBundle,
    build_persistent_deployment,
    build_persistent_runtime_bundle,
)
from .persistent_route_builder import BenchmarkSceneSource
from .process_worker import JsonlProcessWorkerClient, ProcessWorkerConfig
from .qwen3_vl_scene_understanding import Qwen3VLConfig, Qwen3VLSceneUnderstandingInference
from .qwen3_vl_vllm_lifecycle import (
    LifecycleManagedSceneUnderstandingInference,
    Qwen3VLVLLMLifecycleConfig,
    Qwen3VLVLLMLifecycleError,
    Qwen3VLVLLMLifecycleManager,
)
from .qwen3_vl_vllm_scene_understanding import (
    Qwen3VLVLLMConfig,
    Qwen3VLVLLMSceneUnderstandingInference,
)
from .scene_understanding_fallback import FallbackSceneUnderstandingInference
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
    lifecycle_managers: tuple[Qwen3VLVLLMLifecycleManager, ...] = field(
        default_factory=tuple
    )

    def close(self) -> None:
        for manager in self.lifecycle_managers:
            manager.close()
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
    if (
        not required <= set(profile)
        or set(profile)
        - required
        - {
            "video",
            "preparation_timeout_s",
            "route_geometry_source",
            "simulation_action_mode",
        }
        or profile.get("schema_version") != PROFILE_SCHEMA_VERSION
    ):
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
    """Construct the adapter Tool API around one worker client.

    Startup creates and validates the world with one read-only snapshot. It does not
    issue an Action or motion; enabled simulation Actions still require a
    route-bound approval emitted after no-motion preparation.
    """

    variables = dict(os.environ if environ is None else environ)
    lifecycle_managers: list[Qwen3VLVLLMLifecycleManager] = []
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
    route_geometry_source = profile.get("route_geometry_source", "observed")
    if route_geometry_source not in {"observed", "oracle"}:
        raise PersistentHostConfigurationError(
            "route_geometry_source must be observed or oracle"
        )
    simulation_action_mode = profile.get(
        "simulation_action_mode", DISABLED_ACTION_MODE
    )
    if simulation_action_mode not in {
        DISABLED_ACTION_MODE,
        RUNTIME_MONITORED_ACTION_MODE,
    }:
        raise PersistentHostConfigurationError(
            "simulation_action_mode must be disabled or runtime_monitored"
        )
    if (
        simulation_action_mode == RUNTIME_MONITORED_ACTION_MODE
        and route_geometry_source != "oracle"
    ):
        raise PersistentHostConfigurationError(
            "runtime_monitored simulation Actions require oracle route geometry"
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
    video_settings = profile.get(
        "video", {"enabled": False, "fps": 25.0, "stride_steps": 4}
    )
    if not isinstance(video_settings, Mapping) or set(video_settings) != {
        "enabled",
        "fps",
        "stride_steps",
    }:
        raise PersistentHostConfigurationError("video settings are invalid")
    if not isinstance(video_settings["enabled"], bool):
        raise PersistentHostConfigurationError("video.enabled must be boolean")
    video_fps = _positive_number(video_settings["fps"], "video.fps")
    video_stride = video_settings["stride_steps"]
    if (
        isinstance(video_stride, bool)
        or not isinstance(video_stride, int)
        or video_stride < 1
    ):
        raise PersistentHostConfigurationError(
            "video.stride_steps must be a positive integer"
        )
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
                "simulation_action_mode": simulation_action_mode,
                "video": {
                    "enabled": video_settings["enabled"],
                    "fps": video_fps,
                    "stride_steps": video_stride,
                },
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
        if not isinstance(model, Mapping) or not isinstance(model.get("provider", "openai_responses"), str):
            raise PersistentHostConfigurationError("model settings are invalid")
        resolver = FilesystemArtifactResolver(artifact_root)
        provider = model.get("provider", "openai_responses")
        if provider == "openai_responses":
            if set(model) != {
                "api_base", "model", "api_key_env", "reasoning_effort",
                "timeout_seconds", "max_output_tokens",
            }:
                raise PersistentHostConfigurationError("model settings are invalid")
            api_key_env = str(model["api_key_env"])
            if not variables.get(api_key_env):
                raise PersistentHostConfigurationError(
                    f"model credential environment is unavailable: {api_key_env}"
                )
            inference = OpenAIResponsesSceneUnderstandingInference(
                resolver,
                config=OpenAIResponsesConfig(
                    api_base=str(model["api_base"]), model=str(model["model"]),
                    api_key_env=api_key_env, reasoning_effort=str(model["reasoning_effort"]),
                    timeout_seconds=_positive_number(model["timeout_seconds"], "model.timeout_seconds"),
                    max_output_tokens=int(_positive_number(model["max_output_tokens"], "model.max_output_tokens")),
                ),
            )
        elif provider == "qwen3_vl_vllm_fallback":
            if set(model) != {"provider", "primary", "fallback"}:
                raise PersistentHostConfigurationError("qwen vLLM fallback model settings are invalid")
            primary = model.get("primary")
            fallback = model.get("fallback")
            if not isinstance(primary, Mapping) or not isinstance(fallback, Mapping):
                raise PersistentHostConfigurationError("qwen vLLM primary/fallback settings are invalid")
            if set(primary) != {"api_base", "model", "api_key_env", "timeout_seconds", "max_output_tokens", "lifecycle"}:
                raise PersistentHostConfigurationError("qwen vLLM primary settings are invalid")
            if set(fallback) != {
                "api_base", "model", "api_key_env", "reasoning_effort", "timeout_seconds", "max_output_tokens"
            }:
                raise PersistentHostConfigurationError("GPT fallback settings are invalid")
            qwen_inference = Qwen3VLVLLMSceneUnderstandingInference(
                resolver,
                config=Qwen3VLVLLMConfig(
                    api_base=str(primary["api_base"]),
                    model=str(primary["model"]),
                    api_key_env=str(primary["api_key_env"]),
                    timeout_seconds=_positive_number(primary["timeout_seconds"], "model.primary.timeout_seconds"),
                    max_output_tokens=int(_positive_number(primary["max_output_tokens"], "model.primary.max_output_tokens")),
                ),
            )
            lifecycle = primary.get("lifecycle")
            if not isinstance(lifecycle, Mapping) or set(lifecycle) != {
                "enabled", "control_api_base", "idle_timeout_s", "control_timeout_s", "sleep_level"
            }:
                raise PersistentHostConfigurationError("qwen vLLM lifecycle settings are invalid")
            if not isinstance(lifecycle["enabled"], bool):
                raise PersistentHostConfigurationError("qwen vLLM lifecycle enabled must be boolean")
            if lifecycle["enabled"]:
                manager = Qwen3VLVLLMLifecycleManager(
                    Qwen3VLVLLMLifecycleConfig(
                        control_api_base=str(lifecycle["control_api_base"]),
                        idle_timeout_s=_positive_number(lifecycle["idle_timeout_s"], "model.primary.lifecycle.idle_timeout_s"),
                        control_timeout_s=_positive_number(lifecycle["control_timeout_s"], "model.primary.lifecycle.control_timeout_s"),
                        sleep_level=int(lifecycle["sleep_level"]),
                    )
                )
                lifecycle_managers.append(manager)
                qwen_inference = LifecycleManagedSceneUnderstandingInference(
                    qwen_inference, manager
                )
            fallback_key_env = str(fallback["api_key_env"])
            if not variables.get(fallback_key_env):
                raise PersistentHostConfigurationError(
                    f"model credential environment is unavailable: {fallback_key_env}"
                )
            gpt_inference = OpenAIResponsesSceneUnderstandingInference(
                resolver,
                config=OpenAIResponsesConfig(
                    api_base=str(fallback["api_base"]),
                    model=str(fallback["model"]),
                    api_key_env=fallback_key_env,
                    reasoning_effort=str(fallback["reasoning_effort"]),
                    timeout_seconds=_positive_number(fallback["timeout_seconds"], "model.fallback.timeout_seconds"),
                    max_output_tokens=int(_positive_number(fallback["max_output_tokens"], "model.fallback.max_output_tokens")),
                ),
            )
            inference = FallbackSceneUnderstandingInference(
                qwen_inference,
                gpt_inference,
                primary_name="qwen3-vl-4b-vllm",
                fallback_name="gpt-5.6-terra-medium",
                fallback_exceptions=(Qwen3VLVLLMLifecycleError,),
                fallback_on_empty=False,
            )
        elif provider == "qwen3_vl_local":
            required = {
                "provider", "model_path", "worker_python", "worker_script", "worker_cwd",
                "device", "max_output_tokens", "startup_timeout_s", "request_timeout_s",
                "shutdown_timeout_s",
            }
            if set(model) != required:
                raise PersistentHostConfigurationError("qwen model settings are invalid")
            model_path = _path(model["model_path"], "model.model_path", directory=True)
            qwen_python = _path(model["worker_python"], "model.worker_python")
            qwen_script = _path(model["worker_script"], "model.worker_script")
            qwen_cwd = _path(model["worker_cwd"], "model.worker_cwd", directory=True)
            qwen_client = JsonlProcessWorkerClient(
                ProcessWorkerConfig(
                    command=(str(qwen_python), str(qwen_script), "--model-path", str(model_path), "--device", str(model["device"])),
                    cwd=qwen_cwd,
                    environment={
                        "PYTHONPATH": f"{adapter_root / 'src'}:{adapter_root / 'runtime'}",
                        "PYTHONUNBUFFERED": "1",
                    },
                    startup_timeout_s=_positive_number(model["startup_timeout_s"], "model.startup_timeout_s"),
                    request_timeout_s=_positive_number(model["request_timeout_s"], "model.request_timeout_s"),
                    shutdown_timeout_s=_positive_number(model["shutdown_timeout_s"], "model.shutdown_timeout_s"),
                )
            )
            inference = Qwen3VLSceneUnderstandingInference(
                resolver,
                config=Qwen3VLConfig(
                    model_path=str(model_path),
                    max_output_tokens=int(_positive_number(model["max_output_tokens"], "model.max_output_tokens")),
                    device=str(model["device"]),
                ),
                worker=qwen_client,
            )
        else:
            raise PersistentHostConfigurationError(f"unsupported semantic provider: {provider}")
        understanding = RoboTwinSceneUnderstandingProvider(
            build_single_view_perception(
                inference,
                load_perception_profile(perception_profile),
                environ=variables,
            )
        )
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
        task_name = None
        if simulation_action_mode == RUNTIME_MONITORED_ACTION_MODE:
            try:
                runtime_definition = yaml.safe_load(
                    runtime_profile.read_text(encoding="utf-8")
                )
                task_name = runtime_definition["task_name"]
            except (KeyError, TypeError, OSError, UnicodeError, yaml.YAMLError) as exc:
                raise PersistentHostConfigurationError(
                    "persistent Runtime task definition is unavailable"
                ) from exc
            if not isinstance(task_name, str) or not task_name:
                raise PersistentHostConfigurationError(
                    "persistent Runtime task_name is invalid"
                )
        if route_geometry_source == "oracle":
            try:
                route_profile = yaml.safe_load(
                    Path(materializer_arguments["route-input-profile"]).read_text(
                        encoding="utf-8"
                    )
                )
                provider_transform = route_profile["grasp_adaptation"][
                    "provider_T_contact_center"
                ]
            except (KeyError, TypeError, OSError, UnicodeError, yaml.YAMLError) as exc:
                raise PersistentHostConfigurationError(
                    "oracle grasp adaptation profile is unavailable"
                ) from exc
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
            preparation_timeout_s=_positive_number(
                profile.get("preparation_timeout_s", 330),
                "preparation_timeout_s",
            ),
            route_geometry_source=route_geometry_source,
            simulation_action_mode=simulation_action_mode,
            task_name=task_name,
        )
        if route_geometry_source == "oracle":
            grasp = PersistentOracleGraspProvider(
                client,
                provider_to_contact_flat=provider_transform,
                grounding=deployment.grounding,
            )
        else:
            grasp = build_grasp_provider(
                load_grasp_profile(grasp_profile), environ=variables
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
        for manager in lifecycle_managers:
            manager.close()
        client.close()
        raise
    return PersistentHost(
        client=client,
        bundle=bundle,
        lifecycle_managers=tuple(lifecycle_managers),
    )


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
