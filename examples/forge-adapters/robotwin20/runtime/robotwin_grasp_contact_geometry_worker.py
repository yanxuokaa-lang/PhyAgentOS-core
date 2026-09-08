"""Extract RoboTwin Panda gripper/support geometry without stepping a scene."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from robotwin_backend import RoboTwinRuntimeProfile, RoboTwinSensorBackend, load_runtime_profile
from robotwin_simulation_probe_worker import _collision_vertices, _table_top_z

SCHEMA_VERSION = "paos-robotwin20-grasp-contact-geometry/v1"
_LINKS = ("panda_hand", "panda_leftfinger", "panda_rightfinger")


class GraspContactGeometryError(RuntimeError):
    """The provider cannot expose complete no-motion contact geometry."""


def capture_contact_geometry(*, runtime_root: Path, runtime_profile: Path, artifact_root: Path) -> dict[str, Any]:
    profile = load_runtime_profile(runtime_profile)
    backend = RoboTwinSensorBackend(
        RoboTwinRuntimeProfile(
            runtime_root=runtime_root,
            artifact_root=artifact_root,
            task_name=profile["task_name"],
            task_config=profile["task_config"],
            embodiment=profile["embodiment"],
        )
    )
    try:
        backend.reset(seed=profile["seed"])
        task = backend._task
        if task is None:
            raise GraspContactGeometryError("RoboTwin task is unavailable")
        arms: dict[str, Any] = {}
        for arm, attribute in (("left", "left_entity"), ("right", "right_entity")):
            entity = getattr(task.robot, attribute, None)
            if entity is None:
                raise GraspContactGeometryError(f"{arm} robot entity is unavailable")
            links = {str(link.get_name()): link for link in entity.get_links()}
            if set(_LINKS) - set(links):
                raise GraspContactGeometryError(f"{arm} Panda gripper links are incomplete")
            hand_pose = links["panda_hand"].get_entity_pose()
            arms[arm] = {
                "links": {
                    name: _collision_vertices(links[name]).tolist() for name in _LINKS
                },
                "reference_hand_pose": {
                    "frame_id": "world",
                    "position_m": [float(item) for item in hand_pose.p],
                    "orientation_wxyz": [float(item) for item in hand_pose.q],
                },
                "joint_position": [float(item) for item in entity.get_qpos()[:7]],
            }
        table_top = float(_table_top_z(task))
        if not math.isfinite(table_top):
            raise GraspContactGeometryError("table support plane is non-finite")
        return {
            "schema_version": SCHEMA_VERSION,
            "task_name": profile["task_name"],
            "seed": profile["seed"],
            "scene_revision": f"{profile['task_name']}-{profile['seed']}-1",
            "frame_id": "world",
            "support_plane": {"normal": [0.0, 0.0, 1.0], "offset_m": table_top},
            "arms": arms,
            "motion_authorized": False,
        }
    finally:
        backend.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--runtime-profile", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path, label, directory in (
        (args.runtime_root, "runtime root", True),
        (args.runtime_profile, "runtime profile", False),
        (args.artifact_root, "artifact root", True),
    ):
        if not path.is_absolute() or path.is_symlink() or (not path.is_dir() if directory else not path.is_file()):
            raise SystemExit(f"{label} path is invalid")
    if not args.output.is_absolute() or args.output.exists() or args.output.is_symlink():
        raise SystemExit("output must be a new absolute file")
    value = capture_contact_geometry(
        runtime_root=args.runtime_root.resolve(),
        runtime_profile=args.runtime_profile.resolve(),
        artifact_root=args.artifact_root.resolve(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    args.output.chmod(0o600)
    print(json.dumps({"status": "completed", "output": str(args.output), "motion_authorized": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
