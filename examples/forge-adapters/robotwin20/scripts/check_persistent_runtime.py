#!/usr/bin/env python3
"""Start one persistent simulator and verify two measured sensor captures."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from PhyAgentOS.forge.capability_runtime import ObservationEndpoint, SceneUnderstandingEndpoint

from robotwin20_adapter.persistent_client import PersistentWorkerClient
from robotwin20_adapter.process_worker import JsonlProcessWorkerClient, ProcessWorkerConfig
from robotwin20_adapter.understanding import RoboTwinSceneUnderstandingProvider


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--runtime-profile", required=True, type=Path)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--worker-python", required=True, type=Path)
    parser.add_argument("--paos-config", type=Path)
    parser.add_argument("--model-timeout-s", type=float, default=90)
    parser.add_argument("--model-max-output-tokens", type=int, default=2048)
    parser.add_argument("--model-reasoning-effort", choices=("low", "medium", "high"), default="low")
    args = parser.parse_args()
    root = args.artifact_root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    adapter = Path(__file__).resolve().parents[1]
    profile = root / "persistent-profile.json"
    profile.write_text(json.dumps({"runtime_root": str(args.runtime_root.resolve()),
                                  "runtime_profile": str(args.runtime_profile.resolve()),
                                  "artifact_root": str(root), "max_duration_s": 300,
                                  "stop_file": str(root / "stop")}, indent=2), encoding="utf-8")
    worker = JsonlProcessWorkerClient(ProcessWorkerConfig(
        command=(str(args.worker_python.resolve()), str(adapter / "runtime/robotwin_persistent_worker.py"), "--profile", str(profile)),
        cwd=adapter / "runtime", environment={"PYTHONPATH": f"{adapter / 'src'}:{adapter / 'runtime'}"},
        startup_timeout_s=180, request_timeout_s=60, shutdown_timeout_s=30,
    ))
    client = PersistentWorkerClient(worker)
    result = {"status": "running", "motion_executed": False}
    try:
        first = client.query("observe", {"sensor_ref": "camera/head"})
        second = client.query("observe", {"sensor_ref": "camera/head"})
        assert first["scene_revision"] == second["scene_revision"]
        assert first["artifacts"] != second["artifacts"]
        assert second["holding_state"] == "empty"
        result = {"status": "passed", "first": first, "second": second, "motion_executed": False}
        observation = ObservationEndpoint(SimpleNamespace(capture=lambda request: second)).invoke(
            {"sensor_ref": "camera/head", "max_age_ms": 60000})
        if observation["status"] != "available":
            raise RuntimeError("persistent observation failed the public Tool contract")
        result["observation_tool_result"] = observation
        result["provenance"] = {"created_at": datetime.now(timezone.utc).isoformat(),
                                "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=adapter, text=True).strip(),
                                "runtime_profile": str(args.runtime_profile.resolve()), "worker_python": str(args.worker_python.resolve()),
                                "scene_source": "rendered_rgb_depth", "seed_source": "runtime_profile"}
        if args.paos_config is not None:
            from openai import OpenAI
            from PhyAgentOS.config.loader import load_config

            from robotwin20_adapter.openai_scene_understanding import (
                FilesystemArtifactResolver,
                OpenAIResponsesConfig,
                OpenAIResponsesSceneUnderstandingInference,
            )
            config = load_config(args.paos_config)
            model = config.agents.defaults.model
            provider = config.get_provider(model)
            os.environ["PAOS_PERSISTENT_MODEL_KEY"] = provider.resolve_api_key(base_dir=args.paos_config.parent)
            inference = OpenAIResponsesSceneUnderstandingInference(FilesystemArtifactResolver(root), config=OpenAIResponsesConfig(
                api_base=config.get_api_base(model), model=model, api_key_env="PAOS_PERSISTENT_MODEL_KEY",
                timeout_seconds=args.model_timeout_s, max_output_tokens=args.model_max_output_tokens,
                reasoning_effort=args.model_reasoning_effort),
                client_factory=lambda **kwargs: OpenAI(max_retries=0, **kwargs))
            request = {key: observation[key] for key in ("observation_ref", "scene_revision", "calibration_ref", "freshness_ms")}
            request.update(frame_id=observation["frame"]["frame_id"], max_age_ms=60000,
                           artifacts=[artifact["ref"] for artifact in observation["artifacts"]])
            result["provenance"].update(model=model, reasoning_effort=args.model_reasoning_effort,
                                         max_output_tokens=args.model_max_output_tokens,
                                         timeout_seconds=args.model_timeout_s, max_retries=0)
            try:
                endpoint = SceneUnderstandingEndpoint(RoboTwinSceneUnderstandingProvider(inference))
                result["understanding"] = endpoint.invoke(request)
                if result["understanding"]["status"] != "available":
                    raise RuntimeError("scene understanding Tool did not return an available result")
            finally:
                os.environ.pop("PAOS_PERSISTENT_MODEL_KEY", None)
        print(json.dumps({"status": "passed", "scene_revision": second["scene_revision"], "artifact_root": str(root)}))
    except Exception as exc:
        result.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        (root / "persistent-sensor-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        client.close()
        (root / "worker.log").write_text("\n".join(worker.stderr_tail), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
