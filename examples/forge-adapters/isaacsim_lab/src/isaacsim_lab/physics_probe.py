"""Native initialization/reset physics readback; never submits a motion command."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    from .profile import LabUtopiaProfile
    profile = LabUtopiaProfile.from_json(args.profile)
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True})
    try:
        import numpy as np
        from omegaconf import OmegaConf

        from .engine import (
            LabUtopiaBackend,
            _apply_initial_robot_state,
            _refresh_initial_robot_state,
        )
        from .scene_physics import read_runtime_physics
        from .visual_perception import LabArtifactStore
        from .worker import WorkerSessionContext

        backend = LabUtopiaBackend(profile, observation_artifact_root=args.artifact_root)
        session = WorkerSessionContext(app)
        backend.ensure_action_scene(session)
        scene = session.resolve("lab_scene_resources")
        robot, world = scene["robot"], scene["world"]
        config = OmegaConf.load(profile.config_path)
        first = read_runtime_physics(scene["physics_report"])
        initial_joints = np.asarray(robot.get_joint_positions()).copy()
        time_before = float(world.current_time)
        second = read_runtime_physics(scene["physics_report"])
        assert float(world.current_time) == time_before
        assert np.array_equal(initial_joints, robot.get_joint_positions())
        world.reset()
        robot.initialize()
        _apply_initial_robot_state(robot, config.robot.initial_joint_positions, config.robot.initial_gripper_positions)
        _refresh_initial_robot_state(world, robot, config.robot.initial_joint_positions, config.robot.initial_gripper_positions)
        reset = read_runtime_physics(scene["physics_report"])
        assert np.allclose(initial_joints, robot.get_joint_positions(), atol=1e-6)
        for before, after in zip(first["bodies"], reset["bodies"]):
            assert before["path"] == after["path"]
            assert np.isclose(before["measured_mass_kg"], after["measured_mass_kg"])
            assert np.allclose(before["measured_inertia_kg_m2"], after["measured_inertia_kg_m2"])
        report = {"status": "passed", "scope": "native no-motion initialization/readback/reset",
                  "motion_commands": 0, "grasp_success_proven": False,
                  "scene_revision": session.current_scene_revision(),
                  "initial_physics_ref": scene["physics_evidence_ref"],
                  "readback_preserves_state": True, "reset_preserves_physics": True,
                  "initial_joints": initial_joints.tolist(), "initial": first, "readback": second, "reset": reset}
        ref = LabArtifactStore(args.artifact_root).write("physics-probe", report)
        print(json.dumps({"status": "passed", "artifact_ref": ref, "bodies": len(first["bodies"]),
                          "motion_commands": 0}, ensure_ascii=False))
        backend.close_session(session)
        session.close()
    finally:
        app.close()


if __name__ == "__main__":
    main()
