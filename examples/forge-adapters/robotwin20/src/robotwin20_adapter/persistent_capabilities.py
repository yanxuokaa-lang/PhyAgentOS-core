"""Scene-bound public capability snapshots for one persistent runtime."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

from .arm_candidates import (
    bind_motion_capability_refs,
    build_capability_snapshot,
    load_arm_planning_profile,
)
from .route_evidence import _artifact_path


class PersistentCapabilityProvider:
    def __init__(self, *, client, artifact_root: Path, arm_profile: Path, profile_digest: str,
                 motion_capability_refs: Mapping[str, str] | None = None):
        self.client = client
        self.root = artifact_root.resolve()
        self.profile = bind_motion_capability_refs(
            load_arm_planning_profile(arm_profile), motion_capability_refs
        )
        self.profile_digest = profile_digest
        self._snapshots = {}

    def describe(self, request):
        current = self.client.query("snapshot", {})
        if current["scene_revision"] != request["scene_revision"]:
            raise ValueError("capability request is not bound to the current scene")
        if not request["observation_ref"].startswith(f"observation://{request['scene_revision']}/"):
            raise ValueError("capability observation differs from current scene")
        _artifact_path(self.root, request["calibration_ref"])
        key = tuple(request[name] for name in ("scene_revision", "observation_ref", "calibration_ref"))
        if key not in self._snapshots:
            token = uuid4().hex
            snapshot = build_capability_snapshot(
                self.profile, **request, profile_digest=self.profile_digest,
                snapshot_ref=f"artifact://capabilities/{token}",
            )
            directory = self.root / "capabilities"
            directory.mkdir(parents=True, exist_ok=True)
            with (directory / f"{token}.json").open("x", encoding="utf-8") as stream:
                stream.write(snapshot.model_dump_json())
            self._snapshots[key] = snapshot
        return self._snapshots[key]
