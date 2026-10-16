"""JSON-lines worker for no-motion RoboTwin sensor capture only.

This worker intentionally avoids ``RoboTwinPersistentEngine``.  The full
engine owns task-specific goals and execution adapters, while this process
only needs the provider-neutral sensor boundary for held-out intake.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping


def _observation_payload(provider: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Project one provider observation using the persistent worker shape."""
    sensor_refs = arguments.get("sensor_refs")
    if sensor_refs is None:
        sensor_ref = arguments.get("sensor_ref")
        if not isinstance(sensor_ref, str) or not sensor_ref:
            raise ValueError("observe requires sensor_ref or sensor_refs")
        snapshot = provider.observe(sensor_ref)
        if snapshot is None:
            raise ValueError("requested RoboTwin sensor is unavailable")
        value = asdict(snapshot)
        value["sensor_ref"] = sensor_ref
        value["captured_at"] = value["captured_at"].isoformat()
        return value
    if not isinstance(sensor_refs, list) or not sensor_refs:
        raise ValueError("observe sensor_refs must be a non-empty array")
    snapshots = provider.observe_many(sensor_refs)
    views = []
    for sensor_ref, snapshot in zip(sensor_refs, snapshots, strict=True):
        view = asdict(snapshot)
        view["sensor_ref"] = sensor_ref
        view["captured_at"] = view["captured_at"].isoformat()
        views.append(view)
    primary = dict(views[0])
    primary["views"] = views
    return primary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, type=Path)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    output = sys.stdout

    # Runtime libraries may print diagnostics; keep stdout a strict JSONL port.
    sys.stdout = sys.stderr
    from robotwin_backend import (  # pylint: disable=import-outside-toplevel
        RoboTwinObservationProvider,
        RoboTwinRuntimeProfile,
        RoboTwinSensorBackend,
        load_runtime_profile,
    )

    runtime_profile_path = Path(profile["runtime_profile"]).resolve()
    runtime = load_runtime_profile(runtime_profile_path)
    backend = RoboTwinSensorBackend(
        RoboTwinRuntimeProfile(
            runtime_root=Path(profile["runtime_root"]).resolve(),
            artifact_root=Path(profile["artifact_root"]).resolve(),
            task_name=runtime["task_name"],
            task_config=runtime["task_config"],
            embodiment=runtime["embodiment"],
            additional_static_cameras=runtime["additional_static_cameras"],
        )
    )
    backend.reset(seed=runtime["seed"])
    provider = RoboTwinObservationProvider(backend)

    def emit(value: Mapping[str, Any]) -> None:
        output.write(json.dumps(value, separators=(",", ":"), default=str) + "\n")
        output.flush()

    emit({"event": "worker_ready"})
    try:
        for line in sys.stdin:
            request: dict[str, Any] = {}
            try:
                request = json.loads(line)
                command = request["command"]
                if command == "shutdown":
                    emit({"request_id": request["request_id"], "status": "shutdown"})
                    return 0
                if command != "query" or request.get("operation") != "observe":
                    raise ValueError("read-only observation worker accepts only observe queries")
                result = _observation_payload(provider, request.get("arguments", {}))
                emit({**result, "request_id": request["request_id"], "ok": True})
            except Exception as exc:
                print(
                    f"observation worker request failed: {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                emit({
                    "request_id": request.get("request_id", "invalid"),
                    "ok": False,
                    "error": {"code": type(exc).__name__, "message": str(exc)},
                })
    finally:
        backend.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
