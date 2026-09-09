#!/usr/bin/env python3
"""Start one persistent simulator and verify two measured sensor captures."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from PhyAgentOS.forge.capability_runtime import (
    GRASP_PROPOSAL_TOOL_SPEC,
    OBSERVATION_TOOL_SPEC,
    SCENE_UNDERSTANDING_TOOL_SPEC,
    CapabilityRuntime,
    CapabilityRuntimeTransport,
    GraspProposalEndpoint,
    ObservationEndpoint,
    SceneUnderstandingEndpoint,
)
from PhyAgentOS.forge.tool_client import ForgeToolClient

from robotwin20_adapter.persistent_client import PersistentWorkerClient
from robotwin20_adapter.process_worker import JsonlProcessWorkerClient, ProcessWorkerConfig
from robotwin20_adapter.understanding import RoboTwinSceneUnderstandingProvider


async def invoke_public_query(runtime, tool_id, arguments):
    async with ForgeToolClient(
        "http://persistent-runtime", transport=CapabilityRuntimeTransport(runtime)
    ) as gateway:
        response = await gateway.invoke_query_tool(tool_id, arguments)
        return response["data"]


def select_grasp_target(understanding, category):
    entities = [item for item in understanding["entities"] if item["category"] == category]
    if len(entities) != 1:
        raise RuntimeError("grasp target category must identify exactly one observed entity")
    return entities[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--runtime-profile", required=True, type=Path)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--worker-python", required=True, type=Path)
    parser.add_argument("--paos-config", type=Path)
    parser.add_argument("--perception-profile", type=Path)
    parser.add_argument("--grasp-profile", type=Path)
    parser.add_argument("--grasp-target-category", help="Exact, unique observed category for the task target")
    parser.add_argument("--model-timeout-s", type=float, default=90)
    parser.add_argument("--model-max-output-tokens", type=int, default=2048)
    parser.add_argument("--model-reasoning-effort", choices=("low", "medium", "high"), default="low")
    args = parser.parse_args()
    if args.perception_profile is not None and args.paos_config is None:
        parser.error("--perception-profile requires --paos-config")
    if args.grasp_profile is not None and args.perception_profile is None:
        parser.error("--grasp-profile requires --perception-profile")
    if args.grasp_profile is not None and not args.grasp_target_category:
        parser.error("--grasp-profile requires --grasp-target-category")
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
        runtime = CapabilityRuntime()
        runtime.register_tool(
            OBSERVATION_TOOL_SPEC,
            ObservationEndpoint(SimpleNamespace(capture=lambda request: client.query("observe", request))),
        )
        observation = asyncio.run(invoke_public_query(
            runtime, "scene.observe", {"sensor_ref": "camera/head", "max_age_ms": 60000}))
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
            if args.perception_profile is not None:
                from robotwin20_adapter.perception_profile import (
                    build_single_view_perception,
                    load_perception_profile,
                )
                perception_profile = load_perception_profile(args.perception_profile.resolve())
                inference = build_single_view_perception(
                    inference, perception_profile,
                    environ={**os.environ, "ROBOTWIN20_ARTIFACT_ROOT": str(root)},
                )
                result["provenance"]["perception_profile"] = str(args.perception_profile.resolve())
                result["provenance"]["perception_configuration"] = perception_profile
            try:
                provider = RoboTwinSceneUnderstandingProvider(inference)

                class DiagnosedProvider:
                    def understand(self, arguments):
                        try:
                            return provider.understand(arguments)
                        except Exception as exc:
                            result["understanding_provider_exception"] = type(exc).__name__
                            if exc.__cause__ is not None:
                                result["understanding_provider_cause"] = type(exc.__cause__).__name__
                            raise

                runtime.register_tool(SCENE_UNDERSTANDING_TOOL_SPEC, SceneUnderstandingEndpoint(DiagnosedProvider()))
                result["understanding"] = asyncio.run(invoke_public_query(runtime, "scene.understand", request))
                if result["understanding"]["status"] != "available":
                    raise RuntimeError("scene understanding Tool did not return an available result")
                result["geometry_available"] = bool(result["understanding"]["derived_artifacts"])
                if args.grasp_profile is not None:
                    from robotwin20_adapter.grasp_profile import (
                        build_grasp_provider,
                        load_grasp_profile,
                    )

                    understanding = result["understanding"]
                    selected_entity = select_grasp_target(understanding, args.grasp_target_category)
                    result["provenance"]["grasp_target_category"] = args.grasp_target_category
                    envelopes = {item["entity_ref"]: item for item in understanding["spatial_envelopes"]}
                    geometry_keys = ("artifact_ref", "kind", "observation_ref", "scene_revision",
                                     "entity_ref", "frame_id", "calibration_ref", "provenance")
                    targets = []
                    for entity in (selected_entity,):
                        entity_ref = entity["entity_ref"]
                        geometry = [
                            {key: item[key] for key in geometry_keys}
                            for item in understanding["derived_artifacts"]
                            if item["entity_ref"] == entity_ref and item["kind"] == "object_point_cloud"
                        ]
                        if entity_ref in envelopes and geometry:
                            targets.append({
                                "entity_ref": entity_ref, "category": entity["category"],
                                "confidence": entity["confidence"],
                                "spatial_envelope": {key: value for key, value in envelopes[entity_ref].items() if key != "entity_ref"},
                                "geometry_artifacts": geometry,
                            })
                    if not targets:
                        raise RuntimeError("no measured target geometry is available for grasp proposal")
                    grasp_profile = load_grasp_profile(args.grasp_profile.resolve())
                    grasp_provider = build_grasp_provider(
                        grasp_profile, environ={**os.environ, "ROBOTWIN20_ARTIFACT_ROOT": str(root)})
                    runtime.register_tool(GRASP_PROPOSAL_TOOL_SPEC, GraspProposalEndpoint(grasp_provider))
                    grasp_request = {key: value for key, value in request.items() if key != "artifacts"}
                    grasp_request["targets"] = targets
                    result["grasp_request"] = grasp_request
                    result["provenance"]["grasp_configuration"] = grasp_profile
                    try:
                        result["grasp"] = asyncio.run(invoke_public_query(runtime, "grasp.propose", grasp_request))
                    finally:
                        (root / "grasp-worker.log").write_text(
                            "\n".join(grasp_provider.client.stderr_tail), encoding="utf-8")
                    if result["grasp"]["status"] != "available":
                        raise RuntimeError("grasp proposal Tool did not return available candidates")
            finally:
                os.environ.pop("PAOS_PERSISTENT_MODEL_KEY", None)
                for label in ("proposal", "segmentation"):
                    geometry_provider = getattr(inference, f"{label}_provider", None)
                    geometry_worker = getattr(geometry_provider, "client", None)
                    if geometry_worker is not None:
                        (root / f"{label}-worker.log").write_text(
                            "\n".join(geometry_worker.stderr_tail), encoding="utf-8")
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
