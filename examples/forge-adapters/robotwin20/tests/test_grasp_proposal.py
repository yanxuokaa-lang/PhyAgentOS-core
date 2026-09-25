from pathlib import Path

import numpy as np
import pytest
from PhyAgentOS.forge.capability_runtime.grasp_proposal import GraspProposalEndpoint

from robotwin20_adapter.grasp_proposal import (
    FilesystemPointCloudArtifactResolver,
    GraspGenProposalProvider,
    GraspNetProposalProvider,
    GraspProposalAdapterError,
)

REQUEST = {
    "observation_ref": "observation://scene-7/camera_front",
    "scene_revision": "scene-7",
    "frame_id": "camera_front",
    "calibration_ref": "calibration://front/v3",
    "freshness_ms": 20,
    "max_age_ms": 100,
    "targets": [
        {
            "entity_ref": "entity://bottle-1",
            "category": "container",
            "confidence": 0.9,
            "spatial_envelope": {
                "frame_id": "camera_front",
                "unit": "m",
                "min_xyz_m": [0.1, -0.2, 0.0],
                "max_xyz_m": [0.2, -0.1, 0.3],
                "confidence": 0.8,
                "provenance": ["artifact://scene-7/camera_front/rgb"],
            },
            "geometry_artifacts": [
                {
                    "artifact_ref": "artifact://scene-7/camera_front/derived/points-bottle",
                    "kind": "object_point_cloud",
                    "observation_ref": "observation://scene-7/camera_front",
                    "scene_revision": "scene-7",
                    "entity_ref": "entity://bottle-1",
                    "frame_id": "camera_front",
                    "calibration_ref": "calibration://front/v3",
                    "provenance": ["artifact://scene-7/camera_front/depth"],
                }
            ],
        }
    ],
}


class Worker:
    def __init__(self):
        self.requests = []
        self.released = False

    def request(self, payload):
        self.requests.append(payload)
        return {
            "request_id": payload["request_id"],
            "status": "available",
            "candidates": [
                {"matrix": np.eye(4).tolist(), "score": 0.8},
                {"matrix": (np.eye(4) + np.diag([0, 0, 0, 0])).tolist(), "score": 0.7},
            ],
            "funnel": {"decoded": 2, "canonicalized": 2, "deduplicated": 2, "retained": 2},
        }

    def release(self):
        self.released = True


class CleanupFailureWorker(Worker):
    def release(self):
        raise RuntimeError("shutdown failed")


def _store(tmp_path: Path):
    path = tmp_path / "scene-7" / "camera_front" / "derived"
    path.mkdir(parents=True)
    np.save(path / "points-bottle.npy", np.asarray([[0.1, 0.0, 0.5], [0.11, 0.0, 0.5]], dtype=np.float32))
    return FilesystemPointCloudArtifactResolver(tmp_path)


def test_graspgen_provider_maps_bound_geometry_to_neutral_candidates(tmp_path):
    worker = Worker()
    provider = GraspGenProposalProvider(worker, artifact_store=_store(tmp_path), apply_nms=True)
    data = provider.propose(REQUEST)
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["grasp_frame"]["frame_id"] == "camera_front"
    assert data["candidates"][0]["provenance"] == [
        "artifact://scene-7/camera_front/derived/points-bottle"
    ]
    assert data["funnel"] == {"decoded": 2, "canonicalized": 2, "deduplicated": 1, "retained": 1}
    assert worker.requests[0]["provider"] == "graspgen"
    assert worker.requests[0]["point_units"] == "m"


def test_provider_sampling_order_survives_nms_and_ten_candidate_cap(tmp_path):
    class SampledWorker(Worker):
        def request(self, payload):
            reply = super().request(payload)
            reply["candidates"] = []
            for index in range(24):
                matrix = np.eye(4)
                matrix[0, 3] = index * .01
                reply["candidates"].append({"matrix": matrix.tolist(), "score": .1 + index * .03})
            reply["funnel"] = {"decoded": 1024, "canonicalized": 1024, "deduplicated": 1024, "retained": 24}
            return reply

    worker = SampledWorker()
    provider = GraspNetProposalProvider(worker, artifact_store=_store(tmp_path),
        max_candidates=10, sample_count=24, apply_nms=True, selection_order="provider")
    result = provider.propose(REQUEST)
    assert worker.requests[0]["max_candidates"] == 24
    assert result["funnel"] == {"decoded": 1024, "canonicalized": 24, "deduplicated": 24, "retained": 10}
    assert [c["grasp_frame"]["position_m"][0] for c in result["candidates"]] == pytest.approx([i * .01 for i in range(10)])
    assert [c["score"] for c in result["candidates"]] == pytest.approx([.1 + i * .03 for i in range(10)])
    assert worker.released is True


def test_graspgen_provider_composes_with_generic_endpoint(tmp_path):
    provider = GraspGenProposalProvider(
        Worker(), artifact_store=_store(tmp_path), apply_nms=True
    )

    result = GraspProposalEndpoint(provider).invoke(REQUEST)

    assert result["status"] == "available"
    assert result["candidate_set_ref"] == "candidate-set://scene-7/camera_front"
    assert result["scene_revision"] == "scene-7"
    assert result["frame"] == {"frame_id": "camera_front", "unit": "m"}
    assert result["calibration_ref"] == "calibration://front/v3"
    assert result["candidates"][0]["provenance"] == [
        REQUEST["targets"][0]["geometry_artifacts"][0]["artifact_ref"]
    ]


def test_missing_geometry_fails_closed(tmp_path):
    provider = GraspGenProposalProvider(Worker(), artifact_store=_store(tmp_path))
    request = {**REQUEST, "targets": [{k: v for k, v in REQUEST["targets"][0].items() if k != "geometry_artifacts"}]}
    with pytest.raises(GraspProposalAdapterError, match="no bound geometry"):
        provider.propose(request)


def test_geometry_binding_mismatch_is_rejected(tmp_path):
    provider = GraspGenProposalProvider(Worker(), artifact_store=_store(tmp_path))
    target = dict(REQUEST["targets"][0])
    target["geometry_artifacts"] = [dict(target["geometry_artifacts"][0], scene_revision="other")]
    with pytest.raises(GraspProposalAdapterError, match="ambiguous or mismatched"):
        provider.propose({**REQUEST, "targets": [target]})


def test_worker_cleanup_failure_is_fail_closed(tmp_path):
    provider = GraspGenProposalProvider(CleanupFailureWorker(), artifact_store=_store(tmp_path))
    with pytest.raises(GraspProposalAdapterError, match="cleanup failed"):
        provider.propose(REQUEST)


def test_graspnet_uses_its_approach_axis_without_reusing_graspgen_semantics(tmp_path):
    class GraspNetWorker(Worker):
        def request(self, payload):
            self.requests.append(payload)
            matrix = np.eye(4)
            matrix[:3, :3] = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], dtype=float)
            return {
                "request_id": payload["request_id"], "status": "available",
                "candidates": [
                    {
                        "matrix": matrix.tolist(),
                        "score": 0.9,
                        "grasp_geometry": {
                            "width_m": 0.04,
                            "height_m": 0.02,
                            "depth_m": 0.01,
                        },
                    }
                ],
                "funnel": {"decoded": 1, "canonicalized": 1, "deduplicated": 1, "retained": 1},
            }

    worker = GraspNetWorker()
    provider = GraspNetProposalProvider(worker, artifact_store=_store(tmp_path), apply_nms=False)
    data = provider.propose(REQUEST)
    assert worker.requests[0]["provider"] == "graspnet"
    assert provider.approach_axis == 0
    assert provider.closing_axis == 1
    assert data["candidates"][0]["approach_direction"]["vector"] == [0.0, 1.0, 0.0]
    assert data["candidates"][0]["grasp_geometry"] == {
        "width_m": 0.04,
        "height_m": 0.02,
        "depth_m": 0.01,
    }


def test_invalid_worker_grasp_geometry_is_rejected(tmp_path):
    class InvalidGeometryWorker(Worker):
        def request(self, payload):
            return {
                "request_id": payload["request_id"],
                "status": "available",
                "candidates": [
                    {
                        "matrix": np.eye(4).tolist(),
                        "score": 0.9,
                        "grasp_geometry": {
                            "width_m": 0.04,
                            "height_m": 0.02,
                            "depth_m": 0.0,
                        },
                    }
                ],
                "funnel": {
                    "decoded": 1,
                    "canonicalized": 1,
                    "deduplicated": 1,
                    "retained": 1,
                },
            }

    provider = GraspNetProposalProvider(
        InvalidGeometryWorker(), artifact_store=_store(tmp_path), apply_nms=False
    )
    with pytest.raises(GraspProposalAdapterError, match="geometry is invalid"):
        provider.propose(REQUEST)


def test_sample_pool_is_filtered_before_retained_limit(tmp_path):
    class PoolWorker(Worker):
        def request(self, payload):
            self.requests.append(payload)
            candidates = []
            for i in range(20):
                pose = np.eye(4)
                pose[0, 3] = i * 0.01
                candidates.append({"matrix": pose.tolist(), "score": (i + 1) / 20})
            return {"request_id": payload["request_id"], "status": "available",
                    "candidates": candidates,
                    "funnel": {"decoded": 20, "canonicalized": 20, "deduplicated": 20, "retained": 20}}

    worker = PoolWorker()
    provider = GraspGenProposalProvider(worker, artifact_store=_store(tmp_path),
                                        sample_count=200, max_candidates=10)
    data = provider.propose(REQUEST)
    assert worker.requests[0]["max_candidates"] == 200
    assert data["funnel"] == {"decoded": 20, "canonicalized": 20, "deduplicated": 20, "retained": 10}
    assert len(data["candidates"]) == 10
    assert data["candidates"][0]["score"] == 1.0
    assert data["candidates"][-1]["score"] == 0.55


def test_graspnet_geometry_crosses_public_proposal_and_prepare_boundary(tmp_path):
    from jsonschema import validate
    from PhyAgentOS.forge.capability_runtime.grasp_proposal import (
        GRASP_TOOL_SPEC,
        GraspProposalEndpoint,
    )
    from PhyAgentOS.forge.capability_runtime.manipulation_prepare import (
        MANIPULATION_TOOL_SPEC,
        validate_arguments,
    )

    class GeometryWorker(Worker):
        def request(self, payload):
            reply = super().request(payload)
            for item in reply["candidates"]:
                item["grasp_geometry"] = {"width_m": .04, "height_m": .02, "depth_m": .01}
            return reply

    provider = GraspNetProposalProvider(GeometryWorker(), artifact_store=_store(tmp_path))
    proposed = GraspProposalEndpoint(provider).invoke(REQUEST)
    assert proposed["status"] == "available"
    validate(proposed, GRASP_TOOL_SPEC["output_schema"])
    prepared = {key: REQUEST[key] for key in (
        "observation_ref", "scene_revision", "frame_id", "calibration_ref", "freshness_ms", "max_age_ms",
    )}
    prepared.update(candidate_set_ref=proposed["candidate_set_ref"], candidates=proposed["candidates"])
    assert validate_arguments(prepared) is None
    validate(prepared, MANIPULATION_TOOL_SPEC["input_schema"])
    assert prepared["candidates"][0]["grasp_geometry"]["depth_m"] == .01
