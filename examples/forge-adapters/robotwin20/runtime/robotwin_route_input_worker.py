"""No-motion benchmark scene-fact producer for complete route materialization."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from robotwin_backend import RoboTwinRuntimeProfile, RoboTwinSensorBackend, load_runtime_profile
from robotwin_blocks_ranking_adapter import task_adapter

from robotwin20_adapter.route_inputs import (
    CURRENT_SCENE_FACTS_SCHEMA_VERSION,
    ROUTE_SCENE_FACTS_SCHEMA_VERSION,
    validate_scene_facts,
)


class RouteInputWorkerError(RuntimeError):
    pass


def capture_scene_facts(
    *, runtime_root: Path, runtime_profile: Path, artifact_root: Path, calibration_ref: str,
    backend: Any = None, include_targets: bool = True,
) -> dict[str, Any]:
    profile = load_runtime_profile(runtime_profile)
    task_file = runtime_root / "envs" / f"{profile['task_name']}.py"
    if not task_file.is_file() or task_file.is_symlink():
        raise RouteInputWorkerError("benchmark task definition is unavailable")
    owned = backend is None
    backend = backend or RoboTwinSensorBackend(
        RoboTwinRuntimeProfile(
            runtime_root=runtime_root,
            artifact_root=artifact_root,
            task_name=profile["task_name"],
            task_config=profile["task_config"],
            embodiment=profile["embodiment"],
        )
    )
    try:
        if owned:
            backend.reset(seed=profile["seed"])
        task = backend._task
        revision = backend.snapshot().get("scene_revision")
        if task is None or not revision or (owned and revision != f"{profile['task_name']}-{profile['seed']}-1"):
            raise RouteInputWorkerError("benchmark scene revision is unavailable")
        adapter = task_adapter(profile["task_name"])
        objects = adapter.capture_objects(task, include_targets=include_targets)
        value = {
            "schema_version": ROUTE_SCENE_FACTS_SCHEMA_VERSION if owned else CURRENT_SCENE_FACTS_SCHEMA_VERSION,
            "task_name": profile["task_name"],
            "seed": profile["seed"],
            "scene_revision": revision,
            "observation_ref": f"observation://{revision}/head_camera",
            "observation_frame_id": "head_camera",
            "route_frame_id": "world",
            "calibration_ref": calibration_ref,
            "task_definition": {
                "relative_path": str(task_file.relative_to(runtime_root)),
                "sha256": hashlib.sha256(task_file.read_bytes()).hexdigest(),
            },
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "robot_control_steps": 0,
            "motion_authorized": False,
            "coverage": "complete",
            "objects": objects,
        }
        if include_targets:
            validate_scene_facts(value)
        return value
    finally:
        if owned:
            backend.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--runtime-profile", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--calibration-ref", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path, label, directory in (
        (args.runtime_root, "runtime root", True),
        (args.runtime_profile, "runtime profile", False),
        (args.artifact_root, "artifact root", True),
    ):
        if not path.is_absolute() or path.is_symlink() or (not path.is_dir() if directory else not path.is_file()):
            raise SystemExit(f"{label} must be an absolute {'directory' if directory else 'file'}")
    if not args.output.is_absolute() or args.output.exists() or args.output.is_symlink():
        raise SystemExit("output must be a new absolute file")
    value = capture_scene_facts(
        runtime_root=args.runtime_root.resolve(),
        runtime_profile=args.runtime_profile.resolve(),
        artifact_root=args.artifact_root.resolve(),
        calibration_ref=args.calibration_ref,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")
    args.output.chmod(0o600)
    print(json.dumps({"status": "completed", "output": str(args.output), "motion_authorized": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
