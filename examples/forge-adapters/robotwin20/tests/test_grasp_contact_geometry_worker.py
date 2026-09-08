from types import SimpleNamespace

import numpy as np
import pytest
import robotwin_grasp_contact_geometry_worker as worker


class _Link:
    def __init__(self, name):
        self._name = name

    def get_name(self):
        return self._name


class _Entity:
    def __init__(self):
        self._links = [_Link(name) for name in worker._LINKS]

    def get_links(self):
        return self._links

    def get_qpos(self):
        return np.zeros(9)


def test_provider_worker_extracts_both_arms_and_support_without_step(monkeypatch, tmp_path):
    class Backend:
        def __init__(self, profile):
            self._task = SimpleNamespace(
                robot=SimpleNamespace(left_entity=_Entity(), right_entity=_Entity()),
            )
            self.closed = False

        def reset(self, seed):
            self.seed = seed

        def close(self):
            self.closed = True

    monkeypatch.setattr(worker, "RoboTwinSensorBackend", Backend)
    monkeypatch.setattr(worker, "_collision_vertices", lambda link: np.zeros((2, 3)))
    monkeypatch.setattr(worker, "load_runtime_profile", lambda path: {
        "task_name": "blocks_ranking_rgb", "task_config": "blocks_ranking_rgb",
        "embodiment": "franka_panda", "seed": 0,
    })
    monkeypatch.setattr(worker, "_collision_vertices", lambda link: np.zeros((2, 3)))
    monkeypatch.setattr(worker, "_table_top_z", lambda task: 0.74)
    result = worker.capture_contact_geometry(
        runtime_root=tmp_path, runtime_profile=tmp_path / "profile.yaml", artifact_root=tmp_path
    )
    assert result["schema_version"] == worker.SCHEMA_VERSION
    assert set(result["arms"]) == {"left", "right"}
    assert set(result["arms"]["left"]["links"]) == set(worker._LINKS)
    assert result["support_plane"]["offset_m"] == 0.74
    assert result["motion_authorized"] is False


def test_provider_worker_rejects_missing_peer_link(monkeypatch, tmp_path):
    class Backend:
        def __init__(self, profile):
            self._task = SimpleNamespace(
                robot=SimpleNamespace(left_entity=_Entity(), right_entity=SimpleNamespace(get_links=lambda: [])),
            )

        def reset(self, seed):
            pass

        def close(self):
            pass

    monkeypatch.setattr(worker, "RoboTwinSensorBackend", Backend)
    monkeypatch.setattr(worker, "_collision_vertices", lambda link: np.zeros((2, 3)))
    monkeypatch.setattr(worker, "load_runtime_profile", lambda path: {
        "task_name": "blocks_ranking_rgb", "task_config": "blocks_ranking_rgb",
        "embodiment": "franka_panda", "seed": 0,
    })
    with pytest.raises(worker.GraspContactGeometryError, match="links are incomplete"):
        worker.capture_contact_geometry(
            runtime_root=tmp_path, runtime_profile=tmp_path / "profile.yaml", artifact_root=tmp_path
        )
