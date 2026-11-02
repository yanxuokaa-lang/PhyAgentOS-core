"""Paired no-motion inference on one saved capture; run in the GraspNet env."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--prediction", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--input-rotation-xyzw", type=float, nargs=4, action="append", required=True)
    args = parser.parse_args(argv)
    runtime = Path(__file__).resolve().parents[1] / "runtime"
    sys.path.insert(0, str(runtime))
    import graspnet_worker as worker

    worker._input_rotations(args.input_rotation_xyzw)
    profile = json.loads(args.profile.read_text())
    capture = json.loads(args.prediction.read_text())["request"]
    if len(capture["targets"]) != 1:
        parser.error("choose a prediction with exactly one captured entity")
    target = capture["targets"][0]
    artifacts = [item for item in target["geometry_artifacts"] if item["kind"] == "object_point_cloud"]
    if len(artifacts) != 1:
        parser.error("capture requires one object point-cloud artifact")
    cloud_ref = artifacts[0]["artifact_ref"]
    prefix = "artifact://labutopia/"
    if not cloud_ref.startswith(prefix):
        parser.error("this replay expects LabUtopia artifact references")
    cloud_path = (args.artifact_root / cloud_ref.removeprefix(prefix)).resolve()
    if not cloud_path.is_file() or not cloud_path.is_relative_to(args.artifact_root.resolve()):
        parser.error("captured point cloud must exist under artifact-root")
    args.output.mkdir(parents=True, exist_ok=False)
    options = worker._parser().parse_args(profile["grasp_worker"]["arguments"])
    options.seed = args.seed
    options.input_rotation_xyzw = None
    worker._OPTIONS = options
    request = {
        "schema_version": "paos-grasp-worker/v1", "provider": "graspnet",
        "request_id": "same-capture-replay", "point_cloud_path": str(cloud_path),
        "max_points": profile["grasp"]["point_budget"],
        "max_candidates": profile["grasp"]["sample_count"],
        "score_threshold": profile["grasp"]["score_threshold"],
        "apply_model_collision": False,
    }
    checkpoint = Path(options.checkpoint)
    repository = Path(__file__).resolve().parents[4]
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip(),
        "modified_files": subprocess.check_output(["git", "diff", "--name-only"], cwd=repository, text=True).splitlines(),
        "profile_path": str(args.profile.resolve()), "profile": profile,
        "prediction_path": str(args.prediction.resolve()), "capture": capture,
        "seed": args.seed, "input_rotations_xyzw": args.input_rotation_xyzw,
        "checkpoint": str(checkpoint), "checkpoint_size_bytes": checkpoint.stat().st_size,
        "checkpoint_mtime_ns": checkpoint.stat().st_mtime_ns,
        "python": sys.version, "request": request,
        "motion_authorized": False, "world_change_started": False, "runs": {},
    }

    def save():
        (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    try:
        worker._load()
        import numpy as np
        import torch
        report.update(numpy_version=np.__version__, torch_version=torch.__version__)
        for label, rotations in (("identity", None), ("coordinate_ensemble", args.input_rotation_xyzw)):
            options.input_rotation_xyzw = rotations
            start = time.monotonic()
            reply = worker._handle(request)
            (args.output / f"{label}.json").write_text(json.dumps(reply, indent=2) + "\n")
            report["runs"][label] = {"elapsed_s": time.monotonic() - start, "funnel": reply["funnel"],
                                     "result_path": f"{label}.json"}
            save()
            print(label, report["runs"][label], flush=True)
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        save()
        raise
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
