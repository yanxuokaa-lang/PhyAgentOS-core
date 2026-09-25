"""GraspNet ranking contract; no optional image/model packages required."""

import importlib.util
import sys
from pathlib import Path

import numpy as np


def _module(name):
    runtime = Path(__file__).resolve().parents[1] / "runtime"
    if str(runtime) not in sys.path:
        sys.path.insert(0, str(runtime))
    spec = importlib.util.spec_from_file_location(name, runtime / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_graspnet_ranks_before_limit_and_reports_full_threshold_funnel(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace

    module = _module("graspnet_worker")
    points = tmp_path / "observed.npy"
    np.save(points, np.ones((20, 3), dtype=np.float32))
    grasps = [SimpleNamespace(
        translation=np.array([index * .01, 0, 1]), rotation_matrix=np.eye(3),
        score=score, width=.04, height=.02, depth=.01,
    ) for index, score in enumerate([.1, .4, .01, .9, .8])]

    class Network:
        def parameters(self):
            return iter([SimpleNamespace(device="cpu")])

        def __call__(self, inputs):
            return inputs

    decoded = SimpleNamespace(detach=lambda: SimpleNamespace(
        cpu=lambda: SimpleNamespace(numpy=lambda: grasps)))
    module._MODEL = (Network(), lambda _: [decoded], lambda values: values)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(
        no_grad=nullcontext,
        from_numpy=lambda array: SimpleNamespace(to=lambda device: array),
    ))
    result = module._handle({
        "schema_version": "paos-grasp-worker/v1", "provider": "graspnet",
        "request_id": "observed-test", "point_cloud_path": str(points),
        "max_candidates": 2, "score_threshold": .02,
    })
    assert [candidate["score"] for candidate in result["candidates"]] == [.9, .8]
    assert result["candidates"][0]["matrix"][0][3] == .03
    assert result["funnel"] == {
        "decoded": 5, "canonicalized": 4, "deduplicated": 4, "retained": 2,
    }


def test_orientation_sampling_covers_native_poses_without_rewriting_scores_or_geometry():
    module = _module("graspnet_worker")
    candidates = []
    for index in range(30):
        matrix = np.eye(4)
        matrix[0, 3] = index * .001
        candidates.append({"matrix": matrix.tolist(), "score": 1 - index * .001})
    matrix = np.diag([-1., -1., 1., 1.])
    distinct = {"matrix": matrix.tolist(), "score": .2}
    candidates.append(distinct)
    sampled = module._sample_candidates(candidates, 24, "orientation_diverse")
    assert len(sampled) == 24
    assert sampled[0] is candidates[0]
    assert sampled[1] is distinct
    assert len({id(item) for item in sampled}) == 24
    assert all(any(item is source for source in candidates) for item in sampled)
    assert module._sample_candidates(candidates[:3], 24, "orientation_diverse") == candidates[:3]


def test_sampling_treats_parallel_jaw_closing_sign_as_equivalent():
    module = _module("graspnet_worker")
    same = {"matrix": np.eye(4).tolist(), "score": .9}
    mirrored = {"matrix": np.diag([1., -1., -1., 1.]).tolist(), "score": .8}
    different = {"matrix": np.diag([-1., -1., 1., 1.]).tolist(), "score": .1}
    assert module._sample_candidates([same, mirrored, different], 2, "orientation_diverse") == [same, different]
