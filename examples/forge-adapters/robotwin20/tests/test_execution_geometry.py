from types import SimpleNamespace

import numpy as np
import robotwin_route_input_worker as worker


def test_execution_geometry_never_reads_task_targets(tmp_path, monkeypatch):
    (tmp_path / "envs").mkdir()
    (tmp_path / "envs/task.py").write_text("# test task\n")
    pose = SimpleNamespace(to_transformation_matrix=lambda: np.eye(4))
    actor = SimpleNamespace(get_pose=lambda: pose, get_functional_point=lambda *_: pose)

    class Task:
        block1 = block2 = block3 = actor

        def __getattr__(self, name):
            if name.endswith("target_pose"):
                raise AssertionError("execution registry must not read benchmark target answers")
            raise AttributeError(name)

    backend = SimpleNamespace(_task=Task(), snapshot=lambda: {"scene_revision": "epoch-1"})
    monkeypatch.setattr(worker, "load_runtime_profile", lambda _: {
        "task_name": "task", "task_config": "test", "embodiment": "test", "seed": 0})
    monkeypatch.setattr(worker, "_half_extents", lambda _: [.02]*3)
    facts = worker.capture_scene_facts(runtime_root=tmp_path, runtime_profile=tmp_path / "profile",
        artifact_root=tmp_path, calibration_ref="artifact://capture/calibration", backend=backend,
        include_targets=False)
    assert len(facts["objects"]) == 3
    assert all(not any("target" in key for key in obj) for obj in facts["objects"])
    assert facts["motion_authorized"] is False
