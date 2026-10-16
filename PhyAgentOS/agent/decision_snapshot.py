"""Collect fresh, no-motion observation inputs for later isolated decision replay."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from PhyAgentOS.agent.decision_evaluation import _create_run_dir, _git_commit, _write_json
from PhyAgentOS.forge.capability_runtime import (
    OBSERVATION_TOOL_SPEC,
    SCENE_UNDERSTANDING_TOOL_SPEC,
    ObservationEndpoint,
    SceneUnderstandingEndpoint,
)


class SnapshotConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_root: Path
    adapter_source_commit: str
    runtime_root: Path
    runtime_profile: Path
    worker_python: Path
    worker_script: Path | None = None
    output_root: Path
    local_api_base: str = "http://127.0.0.1:8012/v1"
    local_model: str = "qwen3-vl-4b-awq"
    worker_request_timeout_s: float = Field(default=60, gt=0, le=300)
    model_timeout_s: float = Field(default=30, gt=0, le=60)
    model_max_tokens: int = Field(default=1536, ge=1, le=4096)

    @field_validator("local_api_base")
    @classmethod
    def local_images_only(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"127.0.0.1", "::1"}
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment
        ):
            raise ValueError("raw images may only be sent to a literal loopback service")
        return value


def _capture(config: SnapshotConfig, root: Path) -> dict:
    # Adapter imports are optional and supplied by the CLI's explicit source root.
    from openai import OpenAI
    from robotwin20_adapter import Qwen3VLVLLMConfig, Qwen3VLVLLMSceneUnderstandingInference
    from robotwin20_adapter.openai_scene_understanding import FilesystemArtifactResolver
    from robotwin20_adapter.persistent_client import PersistentWorkerClient
    from robotwin20_adapter.process_worker import JsonlProcessWorkerClient, ProcessWorkerConfig
    from robotwin20_adapter.runtime_profile import load_runtime_profile
    from robotwin20_adapter.understanding import RoboTwinSceneUnderstandingProvider

    profile = load_runtime_profile(config.runtime_profile)
    _write_json(root / "runtime_profile.json", profile)
    worker_profile = root / "worker_profile.json"
    _write_json(worker_profile, {
        "runtime_root": str(config.runtime_root), "runtime_profile": str(config.runtime_profile),
        "artifact_root": str(root), "max_duration_s": 300, "stop_file": str(root / "stop"),
    })
    worker_script = config.worker_script or (config.adapter_root / "runtime/robotwin_persistent_worker.py")
    worker_config = ProcessWorkerConfig(
        command=(str(config.worker_python), str(worker_script),
                 "--profile", str(worker_profile)),
        cwd=config.adapter_root / "runtime",
        environment={"PYTHONPATH": f"{config.adapter_root / 'src'}:{config.adapter_root / 'runtime'}"},
        startup_timeout_s=90, request_timeout_s=config.worker_request_timeout_s, shutdown_timeout_s=15,
    )
    worker = JsonlProcessWorkerClient(worker_config)
    client = PersistentWorkerClient(worker)
    diagnostics = []
    try:
        observation_endpoint = ObservationEndpoint(SimpleNamespace(
            capture=lambda request: client.query("observe", request),
        ))
        request = {
            "sensor_refs": list(profile["sensor_refs"]),
            "max_age_ms": profile["max_observation_age_ms"],
            "max_capture_skew_ms": 100,
        }
        _write_json(root / "observation_request.json", request)
        observation = observation_endpoint.invoke(request)
        _write_json(root / "observation.json", observation)
        if observation.get("status") != "available":
            return {"status": "observation_unavailable"}
        provider = Qwen3VLVLLMSceneUnderstandingInference(
            FilesystemArtifactResolver(root),
            config=Qwen3VLVLLMConfig(
                api_base=config.local_api_base, model=config.local_model,
                timeout_seconds=config.model_timeout_s, max_output_tokens=config.model_max_tokens,
            ),
            client_factory=lambda **kwargs: OpenAI(
                max_retries=0, http_client=httpx.Client(trust_env=False), **kwargs,
            ),
            diagnostic_sink=diagnostics.append,
        )
        understanding_request = {
            key: observation[key]
            for key in ("observation_ref", "scene_revision", "calibration_ref", "freshness_ms",
                        "views", "capture_skew_ms")
        }
        understanding_request.update(
            frame_id=observation["frame"]["frame_id"], max_age_ms=request["max_age_ms"],
            artifacts=[artifact["ref"] for view in observation["views"] for artifact in view["artifacts"]],
        )
        now = datetime.now(timezone.utc)
        understanding_request["views"] = [
            {**view, "freshness_ms": max(view["freshness_ms"], int(
                (now - datetime.fromisoformat(view["captured_at"].replace("Z", "+00:00"))).total_seconds() * 1000
            ))}
            for view in observation["views"]
        ]
        understanding_request["freshness_ms"] = max(
            view["freshness_ms"] for view in understanding_request["views"]
        )
        _write_json(root / "understanding_request.json", understanding_request)
        started = monotonic()
        understanding = SceneUnderstandingEndpoint(
            RoboTwinSceneUnderstandingProvider(provider)
        ).invoke(understanding_request)
        elapsed = (monotonic() - started) * 1000
        _write_json(root / "understanding.json", understanding)
        return {
            "status": "captured" if understanding.get("status") == "available" else "understanding_unavailable",
            "scene_revision": observation["scene_revision"],
            "view_count": len(observation["views"]), "capture_skew_ms": observation["capture_skew_ms"],
            "entity_count": len(understanding.get("entities", [])),
            "ambiguity_count": len(understanding.get("ambiguities", [])),
            "understanding_elapsed_ms": elapsed,
        }
    finally:
        try:
            _write_json(root / "local_model_diagnostics.json", diagnostics)
        finally:
            try:
                client.close()
            finally:
                (root / "worker.log").write_text("\n".join(worker.stderr_tail), encoding="utf-8")


def capture_snapshot(config: SnapshotConfig, *, repo_root: Path) -> Path:
    root = _create_run_dir(config.output_root)
    summary = {
        "status": "interrupted", "code_commit": _git_commit(repo_root),
        "python_version": sys.version, "python_executable": sys.executable,
        "adapter_source_commit_declared": config.adapter_source_commit,
        "evidence_scope": "fresh_sensor_and_local_semantics_not_host_pair",
        "action_calls": 0, "session_calls": 0, "remote_model_calls": 0,
        "host_selection_measured": False,
    }
    try:
        _write_json(root / "config.json", config.model_dump(mode="json"))
        shutil.copyfile(__file__, root / "collector_source.py")
        shutil.copyfile(config.runtime_profile, root / "runtime_profile.yaml")
        # Source contracts, not a fabricated task binding or selection trace.
        _write_json(root / "query_tool_specs.json", {
            "scene.observe": OBSERVATION_TOOL_SPEC,
            "scene.understand": SCENE_UNDERSTANDING_TOOL_SPEC,
        })
        summary.update(_capture(config, root))
    except Exception as exc:
        summary.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
    finally:
        _write_json(root / "summary.json", summary)
    return root
