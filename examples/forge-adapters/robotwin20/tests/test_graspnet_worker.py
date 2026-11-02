"""GraspNet ranking contract; no optional image/model packages required."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


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
    assert [candidate["native_score"] for candidate in result["candidates"]] == [.9, .8]


def test_graspnet_saturates_native_scores_and_filters_negative_scores(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace

    module = _module("graspnet_worker")
    points = tmp_path / "observed.npy"
    np.save(points, np.ones((20, 3), dtype=np.float32))
    grasps = [SimpleNamespace(
        translation=np.array([index * .01, 0, 1]), rotation_matrix=np.eye(3),
        score=score, width=.04, height=.02, depth=.01,
    ) for index, score in enumerate([2.4, 1.3, .6, -.2])]

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
        "request_id": "normalization-test", "point_cloud_path": str(points),
        "max_candidates": 4, "score_threshold": .5,
    })

    assert [item["native_score"] for item in result["candidates"]] == [2.4, 1.3, .6]
    assert [item["score"] for item in result["candidates"]] == [1.0, 1.0, .6]
    assert result["funnel"] == {
        "decoded": 4, "canonicalized": 3, "deduplicated": 3, "retained": 3,
    }


def test_graspnet_rejects_non_finite_native_score(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace

    module = _module("graspnet_worker")
    points = tmp_path / "observed.npy"
    np.save(points, np.ones((20, 3), dtype=np.float32))
    grasps = [SimpleNamespace(
        translation=np.array([0, 0, 1]), rotation_matrix=np.eye(3),
        score=float("nan"), width=.04, height=.02, depth=.01,
    )]

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

    with pytest.raises(module.WorkerUnavailableError, match="malformed candidates"):
        module._handle({
            "schema_version": "paos-grasp-worker/v1", "provider": "graspnet",
            "request_id": "non-finite-test", "point_cloud_path": str(points),
            "max_candidates": 1, "score_threshold": 0,
        })


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


def test_geometric_sampling_preserves_a_spatial_family_with_identical_orientation():
    module = _module('graspnet_worker')
    candidates = []
    for index in range(20):
        pose = np.eye(4)
        pose[2, 3] = index * .0001
        candidates.append({'matrix': pose.tolist(), 'score': .9 - .01 * index,
                           'grasp_geometry': {'width_m': .04}})
    pose = np.eye(4)
    pose[2, 3] = .08
    different_region = {'matrix': pose.tolist(), 'score': .05, 'grasp_geometry': {'width_m': .04}}
    candidates.append(different_region)
    selected = module._sample_candidates(candidates, 2, 'geometry_diverse')
    assert selected == [candidates[0], different_region]
    assert all(any(item is native for native in candidates) for item in selected)


def test_observed_regions_preserve_full_cloud_and_only_add_existing_point_subsets():
    module = _module('graspnet_worker')
    points = np.column_stack((np.linspace(-.1, .1, 100), np.zeros(100), np.zeros(100)))
    regions = module._input_regions(points, 3)
    assert regions[0] is points and len(regions) == 4
    assert module._input_regions(points, 0) == [points]
    for region in regions[1:]:
        assert 3 <= len(region) < len(points)
        assert all(any(np.array_equal(p, q) for q in points) for p in region)
    shifted = module._input_regions(points + [2., 3., 4.], 3)
    for original, moved in zip(regions, shifted):
        np.testing.assert_allclose(original + [2., 3., 4.], moved)
    assert len(module._input_regions(np.ones((10, 3)), 3)) == 1


@pytest.mark.parametrize('count', [-1, 4, True, 1.5])
def test_region_inference_rejects_invalid_or_unbounded_pass_count(count):
    module = _module('graspnet_worker')
    with pytest.raises(module.WorkerUnavailableError, match='region count'):
        module._input_regions(np.zeros((10, 3)), count)


def test_optional_seed_pairs_point_indices_without_changing_global_rng():
    module = _module('graspnet_worker')
    points = np.arange(300).reshape(100, 3)
    shifted = points + 1000
    state = np.random.get_state()
    for count in (60, 140):
        first = module._sample_points(points, count, seed=7)
        second = module._sample_points(shifted, count, seed=7)
        assert np.array_equal(first + 1000, second)
        assert np.array_equal(first, module._sample_points(points, count, seed=7))
    assert np.array_equal(state[1], np.random.get_state()[1])
    assert module._parser().parse_args(['--checkpoint', 'model']).seed is None


@pytest.mark.parametrize("values", [[], [[0, 0, 0, 0]], [[0, 0, float('nan'), 1]],
                                   [[0, 0, 0, 2]], [[0, 0, 1]], [[0, 0, 0, 1]] * 5])
def test_input_rotation_configuration_rejects_invalid_or_unbounded_passes(values):
    module = _module("graspnet_worker")
    with pytest.raises(module.WorkerUnavailableError, match="input rotation"):
        module._input_rotations(values)


def _coordinate_inference_fixture(tmp_path, monkeypatch, *, fail_pass=None):
    from contextlib import nullcontext
    from types import SimpleNamespace

    module = _module("graspnet_worker")
    points = np.array([[.1, -.2, 1.], [.4, .1, 1.4], [-.2, .3, 1.2]], dtype=np.float32)
    path = tmp_path / "captured.npy"
    np.save(path, points)
    seen = []

    class Network:
        def parameters(self):
            return iter([SimpleNamespace(device="cpu")])

        def __call__(self, inputs):
            seen.append(inputs["point_clouds"][0].copy())
            if len(seen) == fail_pass:
                raise RuntimeError("inference failed")
            return inputs

    def decode(inputs):
        native = [SimpleNamespace(
            translation=inputs["point_clouds"][0][0].astype(float) + [.01, .02, .03],
            rotation_matrix=np.eye(3), score=.8,
            width=.04, height=.02, depth=.01,
        )]
        return [SimpleNamespace(detach=lambda: SimpleNamespace(
            cpu=lambda: SimpleNamespace(numpy=lambda: native)))]

    module._MODEL = (Network(), decode, lambda values: values)
    module._OPTIONS = SimpleNamespace(
        seed=7, sampling_policy="orientation_diverse",
        input_rotation_xyzw=[[0., 0., 0., 1.], [1., 0., 0., 0.]],
    )
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(
        no_grad=nullcontext, manual_seed=lambda _seed: None,
        from_numpy=lambda array: SimpleNamespace(to=lambda _device: array),
    ))
    request = {"schema_version": "paos-grasp-worker/v1", "provider": "graspnet",
               "request_id": "same-capture", "point_cloud_path": str(path),
               "max_points": 3, "max_candidates": 4, "score_threshold": .02}
    return module, request, points, seen


@pytest.mark.parametrize("quaternion, rotation", [
    ([1., 0., 0., 0.], np.diag([1., -1., -1.])),
    ([0., 0., 2**-.5, 2**-.5], np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])),
])
def test_coordinate_inference_recomputes_and_inverse_maps_native_predictions(tmp_path, monkeypatch, quaternion, rotation):
    module, request, points, seen = _coordinate_inference_fixture(tmp_path, monkeypatch)
    module._OPTIONS.input_rotation_xyzw[1] = quaternion
    original = points.copy()
    result = module._handle(request)
    pivot = points.astype(float).mean(axis=0)
    assert len(seen) == 2
    assert seen[1] == pytest.approx((seen[0] - pivot) @ rotation.T + pivot, abs=2e-7)
    assert np.array_equal(points, original)
    assert result["request_id"] == request["request_id"]
    assert result["funnel"] == {"decoded": 2, "canonicalized": 2, "deduplicated": 2, "retained": 2}
    matrices = [np.array(item["matrix"]) for item in result["candidates"]]
    assert matrices[0][:3, 3] == pytest.approx(seen[0][0] + [.01, .02, .03])
    assert matrices[1][:3, 3] == pytest.approx(
        rotation.T @ (seen[1][0] + [.01, .02, .03] - pivot) + pivot)
    assert matrices[1][:3, :3] == pytest.approx(rotation.T)
    assert all(item["score"] == .8 and item["grasp_geometry"]["width_m"] == .04
               for item in result["candidates"])


def test_coordinate_inference_respects_total_budget_and_single_pass_compatibility(tmp_path, monkeypatch):
    module, request, _, seen = _coordinate_inference_fixture(tmp_path, monkeypatch)
    result = module._handle({**request, "max_candidates": 1})
    assert len(seen) == 2
    assert len(result["candidates"]) == 1
    module._OPTIONS.input_rotation_xyzw = None
    seen.clear()
    result = module._handle(request)
    assert len(seen) == 1
    assert len(result["candidates"]) == 1
    assert np.array(result["candidates"][0]["matrix"])[:3, :3] == pytest.approx(np.eye(3))


def test_coordinate_inference_does_not_return_partial_success(tmp_path, monkeypatch):
    module, request, _, seen = _coordinate_inference_fixture(tmp_path, monkeypatch, fail_pass=2)
    with pytest.raises(module.WorkerUnavailableError, match="inference failed"):
        module._handle(request)
    assert len(seen) == 2


def test_region_inference_recomputes_same_capture_and_inverse_maps_each_pass(tmp_path, monkeypatch):
    module, request, _, seen = _coordinate_inference_fixture(tmp_path, monkeypatch)
    points = np.column_stack((np.linspace(.1, .3, 100), np.full(100, .2), np.ones(100))).astype(np.float32)
    np.save(request["point_cloud_path"], points)
    module._OPTIONS.input_region_count = 3
    module._OPTIONS.sampling_policy = "score"
    result = module._handle({**request, "max_candidates": 16})
    assert len(seen) == 8
    assert result["funnel"]["decoded"] == 8
    pivot = points.astype(float).mean(axis=0)
    regions = module._input_regions(points, 3)
    for index, candidate in enumerate(result["candidates"]):
        rotation = np.eye(3) if index % 2 == 0 else np.diag([1., -1., -1.])
        expected = rotation.T @ (seen[index][0] + [.01, .02, .03] - pivot) + pivot
        matrix = np.array(candidate["matrix"])
        np.testing.assert_allclose(matrix[:3, 3], expected, atol=2e-7)
        np.testing.assert_allclose(matrix[:3, :3], rotation.T)
        recovered = (seen[index] - pivot) @ rotation + pivot
        assert all(np.any(np.all(np.isclose(regions[index // 2], point, atol=2e-7), axis=1)) for point in recovered)
        assert candidate["native_score"] == .8
        assert candidate["grasp_geometry"] == {"width_m": .04, "height_m": .02, "depth_m": .01}
    seen.clear()
    assert len(module._handle({**request, "max_candidates": 2})["candidates"]) == 2
    assert len(seen) == 8
    assert module._parser().parse_args(["--checkpoint", "model"]).input_region_count == 0


def test_region_failure_does_not_publish_prior_full_cloud_success(tmp_path, monkeypatch):
    module, request, _, seen = _coordinate_inference_fixture(tmp_path, monkeypatch, fail_pass=3)
    points = np.column_stack((np.linspace(.1, .3, 100), np.zeros(100), np.ones(100))).astype(np.float32)
    np.save(request["point_cloud_path"], points)
    module._OPTIONS.input_region_count = 3
    with pytest.raises(module.WorkerUnavailableError, match="inference failed"):
        module._handle(request)
    assert len(seen) == 3


def test_coordinate_inference_empty_passes_remain_empty(tmp_path, monkeypatch):
    module, request, _, seen = _coordinate_inference_fixture(tmp_path, monkeypatch)
    result = module._handle({**request, "score_threshold": .99})
    assert len(seen) == 2
    assert result["status"] == "empty"
    assert result["candidates"] == []
    assert result["funnel"] == {"decoded": 2, "canonicalized": 0, "deduplicated": 0, "retained": 0}


def test_coordinate_results_substitute_through_existing_provider_protocol(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from robotwin20_adapter.grasp_proposal import GraspNetProposalProvider

    module, request, _, _ = _coordinate_inference_fixture(tmp_path, monkeypatch)
    reply = module._handle(request)
    client = SimpleNamespace(request=lambda payload: {**reply, "request_id": payload["request_id"]})
    source_ref = "artifact://captured/points"
    resolver = SimpleNamespace(resolve_point_cloud=lambda _ref: Path(request["point_cloud_path"]))
    provider = GraspNetProposalProvider(client, artifact_store=resolver, apply_nms=False)
    identity = {"observation_ref": "observation://captured", "scene_revision": "revision-1",
                "frame_id": "captured-camera", "calibration_ref": "artifact://captured/calibration"}
    target = {"entity_ref": "entity://bottle", "geometry_artifacts": [
        {**identity, "entity_ref": "entity://bottle", "kind": "object_point_cloud", "artifact_ref": source_ref},
    ]}
    result = provider.propose({**identity, "targets": [target]})
    assert result["provider_available"] is True
    assert len(result["candidates"]) == 2
    for candidate, raw in zip(result["candidates"], reply["candidates"]):
        assert candidate["grasp_frame"]["frame_id"] == identity["frame_id"]
        assert candidate["approach_direction"]["vector"] == pytest.approx(np.array(raw["matrix"])[:3, 0])
        assert candidate["provenance"] == [source_ref]


def test_input_rotation_parser_is_opt_in_and_repeatable():
    module = _module("graspnet_worker")
    assert module._parser().parse_args(["--checkpoint", "model"]).input_rotation_xyzw is None
    args = module._parser().parse_args([
        "--checkpoint", "model", "--input-rotation-xyzw", "0", "0", "0", "1",
        "--input-rotation-xyzw", "1", "0", "0", "0",
    ])
    assert len(module._input_rotations(args.input_rotation_xyzw)) == 2
