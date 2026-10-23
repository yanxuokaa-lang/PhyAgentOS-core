"""Recovery crosses the existing worker seam, without simulator state."""
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from robotwin20_adapter.geometry_recovery import (
    GeometryRecoveryError,
    GeometryRecoveryRequest,
    WorkerGeometryRecoveryProvider,
)


def request(tmp_path):
    return GeometryRecoveryRequest(
        observation_ref="observation://scene/front", scene_revision="scene",
        frame_id="front", calibration_ref="artifact://camera/calibration.json",
        rgb_path=tmp_path / "rgb.png", depth_path=tmp_path / "depth.npy",
        mask_path=tmp_path / "mask.npy", image_size_px=(8, 6),
    )


@pytest.mark.parametrize("method", ["remake", "dfnet"])
def test_models_use_same_capture_bound_recovery_interface(tmp_path, method):
    output = tmp_path / "worker" / "result.npy"
    output.parent.mkdir()
    np.save(output, np.full((6, 8), .8))
    client = Mock()
    def reply(payload):
        assert payload["observation_ref"] == "observation://scene/front"
        assert "prim_path" not in payload
        return {"request_id": payload["request_id"], "status": "available",
                "depth_path": str(output), "image_size_px": [8, 6],
                "metadata": {"method": method, "unit": "m", "geometry_qualification": "unverified_estimate"}}
    client.request.side_effect = reply
    provider = WorkerGeometryRecoveryProvider(client, worker_artifact_root=output.parent)
    result = provider.recover(request(tmp_path))
    assert result.depth_m.shape == (6, 8)
    assert result.metadata["method"] == method
    assert result.metadata["geometry_qualification"] == "unverified_estimate"
    provider.release()
    client.release.assert_called_once()


@pytest.mark.parametrize("failure", ["unavailable", "capture", "shape", "path", "units"])
def test_recovery_rejects_provider_failures_and_misaligned_output(tmp_path, failure):
    root = tmp_path / "worker"
    root.mkdir()
    output = root / "result.npy"
    np.save(output, np.ones((3, 4) if failure == "shape" else (6, 8)))
    def reply(payload):
        return {"request_id": "wrong" if failure == "capture" else payload["request_id"],
                "status": "unavailable" if failure == "unavailable" else "available",
                "error": "checkpoint inference failed",
                "depth_path": str(tmp_path / "escape.npy") if failure == "path" else str(output),
                "image_size_px": [8, 6], "metadata": {"unit": "mm" if failure == "units" else "m"}}
    provider = WorkerGeometryRecoveryProvider(SimpleNamespace(request=reply), worker_artifact_root=root)
    with pytest.raises(GeometryRecoveryError):
        provider.recover(request(tmp_path))
