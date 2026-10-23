"""Optional trained-model parity with the upstream ReMake inference method.

Run in the geometry runtime with PAOS_GEOMETRY_CACHE, PAOS_GEOMETRY_REPLAY and
PAOS_GEOMETRY_PARITY_OUTPUT set. Default unit suites skip the external model.
"""
import ast
import json
import os
import sys
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(not os.environ.get('PAOS_GEOMETRY_CACHE'), reason='external trained model not requested')


def _function(path, name):
    tree = ast.parse(path.read_text())
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    return compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec')


def test_trained_remake_matches_upstream_inference_on_recorded_capture():
    import cv2
    import torch
    from PIL import Image
    from torchvision.transforms import Compose

    sys.path.insert(0, str(Path(__file__).parents[1] / 'runtime'))
    from transparent_geometry_worker import TorchDepthBackend
    cache = Path(os.environ['PAOS_GEOMETRY_CACHE'])
    source = Path(os.environ['PAOS_GEOMETRY_REPLAY'])
    output = Path(os.environ['PAOS_GEOMETRY_PARITY_OUTPUT'])
    assert not output.exists(), 'parity output must not overwrite a previous run'
    repo = cache / 'ReMake'
    backend = TorchDepthBackend('remake', repo, cache/'checkpoints/remake.tar',
                               cache/'checkpoints/depth_anything_v2_vits.pth', 'cpu', 0)
    from depth_anything_v2.util.transform import NormalizeImage, PrepareForNet, Resize
    root = source / 'artifacts/labutopia'
    report = json.loads((source/'perception.json').read_text())
    capture = report['capture']
    def path(ref):
        return root / ref.removeprefix('artifact://labutopia/')
    rgb = np.asarray(Image.open(path(next(a['ref'] for a in capture['artifacts'] if a['kind'] == 'rgb'))).convert('RGB'))
    depth = np.load(path(next(a['ref'] for a in capture['artifacts'] if a['kind'] == 'depth')), allow_pickle=False)
    records = json.loads((source/'segmentation-replay.json').read_text())
    mask = np.logical_or.reduce([np.load(source/f"replay-mask-{r['index']}.npy", allow_pickle=False) for r in records]).astype(np.uint8)
    namespace = {'cv2': cv2, 'np': np, 'torch': torch, 'F': torch.nn.functional,
        'Compose': Compose, 'NormalizeImage': NormalizeImage, 'PrepareForNet': PrepareForNet,
        'Resize': Resize, 'perf_counter': perf_counter,
        'load_reldepth_model': lambda name, device: backend.relative}
    exec(_function(repo/'utils/data_preparation.py', 'img_rel_preprocess'), namespace)
    exec(_function(repo/'run_utils/inferencer.py', 'inference'), namespace)
    upstream = SimpleNamespace(args=SimpleNamespace(reldepth_model='depthanything'), image_size=(640, 480),
        depth_min=0., depth_max=3., depth_norm=1., device='cpu', model_type='remake', model=backend.model, with_info=False)
    expected = namespace['inference'](upstream, rgb.copy(), depth.copy(), mask.copy(), target_size=(rgb.shape[1], rgb.shape[0]))
    prepared_depth = np.where(np.isfinite(depth) & (depth > 0) & (depth <= 3), depth, 0).astype(np.float32)
    actual = backend.predict(cv2.resize(rgb, (640, 480), interpolation=cv2.INTER_NEAREST),
        cv2.resize(prepared_depth, (640, 480), interpolation=cv2.INTER_NEAREST),
        cv2.resize(mask, (640, 480), interpolation=cv2.INTER_NEAREST))
    actual = cv2.resize(actual, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)
    difference = float(np.max(np.abs(actual-expected)))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'upstream_source': str(repo), 'capture_source': str(source),
        'max_abs_difference_m': difference, 'torch': torch.__version__, 'numpy': np.__version__,
        'scope': 'same trained-model arithmetic; does not establish scene geometry accuracy'}, indent=2))
    assert difference < 1e-5
