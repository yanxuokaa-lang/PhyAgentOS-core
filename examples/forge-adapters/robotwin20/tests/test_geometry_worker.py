"""Exercise actual input/output adaptation with a deterministic model substitute."""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

RUNTIME = Path(__file__).parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))
spec = importlib.util.spec_from_file_location("transparent_geometry_worker", RUNTIME / "transparent_geometry_worker.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def setup(tmp_path, depth_max=3.0):
    Image.new("RGB", (20, 12), (100, 80, 60)).save(tmp_path / "rgb.png")
    np.save(tmp_path / "depth.npy", np.full((12, 20), 2.4, dtype=np.float32))
    np.save(tmp_path / "mask.npy", np.ones((12, 20), dtype=bool))
    worker = module.DepthRecoveryWorker(
        method="remake", repo_root=tmp_path, checkpoint=tmp_path / "model.pt",
        relative_checkpoint=None, device="cpu", source_artifact_root=tmp_path,
        worker_artifact_root=tmp_path / "worker", image_size=(16, 16),
        depth_min_m=.1, depth_max_m=depth_max, depth_scale_to_m=1.0,
    )
    class Backend:
        def predict(self, rgb, depth, mask):
            assert rgb.shape == (16, 16, 3)
            assert depth.shape == mask.shape == (16, 16)
            assert np.allclose(depth, 2.4)
            return np.full(depth.shape, .9, dtype=np.float32)
    worker.backend = Backend()
    payload = {"request_id": "test", "operation": "recover_depth",
               "rgb_path": str(tmp_path / "rgb.png"), "depth_path": str(tmp_path / "depth.npy"),
               "mask_path": str(tmp_path / "mask.npy"), "image_size_px": [20, 12]}
    return worker, payload


def test_preserves_source_resolution_and_metric_depth_beyond_upstream_default(tmp_path):
    worker, payload = setup(tmp_path)
    result = worker.handle(payload)
    assert result['status'] == 'available', result
    depth = np.load(result['depth_path'])
    assert depth.shape == (12, 20)
    assert np.allclose(depth, .9)
    assert result['metadata']['input_valid_fraction'] == 1
    assert result['metadata']['geometry_qualification'] == 'unverified_estimate'


def test_all_input_clipped_is_explicit_failure_before_model(tmp_path):
    worker, payload = setup(tmp_path, depth_max=1.5)
    result = worker.handle(payload)
    assert result['status'] == 'unavailable'
    assert 'depth' in result['error']


@pytest.mark.parametrize('kind', ['mask_size', 'outside_root', 'output_nonfinite'])
def test_bad_input_or_model_output_cannot_report_success(tmp_path, kind):
    worker, payload = setup(tmp_path)
    if kind == 'mask_size':
        np.save(tmp_path / 'mask.npy', np.ones((3, 3), dtype=bool))
    elif kind == 'outside_root':
        payload['depth_path'] = str(tmp_path.parent / 'outside.npy')
    else:
        worker.backend.predict = lambda rgb, depth, mask: np.full(depth.shape, np.nan)
    assert worker.handle(payload)['status'] == 'unavailable'
