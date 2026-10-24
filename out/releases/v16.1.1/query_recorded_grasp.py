"""Query the existing GraspNet provider on an Agent's saved, labelled capture."""
import argparse
import json
import os
from pathlib import Path

from isaacsim_lab.visual_perception import LabArtifactStore, RecordedGraspProvider
from pick_place_workflow.perception_binding import grasp_geometry_artifacts
from robotwin20_adapter.grasp_proposal import GraspNetProposalProvider
from robotwin20_adapter.perception_profile import _worker_config
from robotwin20_adapter.process_worker import JsonlProcessWorkerClient

from PhyAgentOS.forge.capability_runtime.grasp_proposal import GraspProposalEndpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, help="Use a new path for another query of the same capture")
    args = parser.parse_args()
    destination = args.output or args.run / "recorded-target-grasp.json"
    if destination.exists():
        raise FileExistsError(f"Result already exists: {destination}; select a new --output")
    root = args.run.resolve() / "artifacts/labutopia"
    matches = []
    for path in (root / "understanding").glob("*.json"):
        saved = json.loads(path.read_text(encoding="utf-8"))
        for entity in saved["result"]["entities"]:
            if args.label in entity.get("label", "").split():
                matches.append((path, saved, entity))
    if len(matches) != 1:
        raise ValueError(f"Expected one labelled capture; found {len(matches)}")
    path, saved, entity = matches[0]
    config_paths = list((root / "perception-configuration").glob("*.json"))
    if len(config_paths) != 1:
        raise ValueError("Expected one recorded deployment configuration")
    deployment = json.loads(config_paths[0].read_text(encoding="utf-8"))
    config = deployment["configuration"]
    variables = {**os.environ, "LAB_ARTIFACT_ROOT": str(root),
                 "LAB_CONFIG_DIR": str(Path(deployment["profile"]).parent)}
    provider = RecordedGraspProvider(GraspNetProposalProvider(
        JsonlProcessWorkerClient(_worker_config(config["grasp_worker"], variables, "grasp_worker")),
        artifact_store=LabArtifactStore(root), **config["grasp"]), LabArtifactStore(root))
    request = {k: saved["request"][k] for k in
               ("observation_ref", "scene_revision", "frame_id", "calibration_ref")}
    # Freshness is relative to this historical capture, as in perception_probe replay.
    # Nothing in this script binds or prepares a current simulator action.
    request.update(freshness_ms=0, max_age_ms=1000, targets=[{
        **{k: entity[k] for k in ("entity_ref", "category", "confidence")},
        "geometry_artifacts": grasp_geometry_artifacts(saved["result"], entity["entity_ref"]),
    }])
    report = {"scope": "offline GraspNet query; historical capture; no preparation or motion",
              "label": entity["label"], "source_understanding": str(path), "request": request,
              "geometry_qualification": "unverified_estimate"}
    try:
        report["result"] = GraspProposalEndpoint(provider).invoke(request)
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
    finally:
        provider.close()
    with destination.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(json.dumps({"output": str(destination), "status": report.get("result", {}).get("status"),
                      "candidates": len(report.get("result", {}).get("candidates", []))}))
    return 0 if report.get("result", {}).get("status") == "available" else 1


if __name__ == "__main__":
    raise SystemExit(main())
