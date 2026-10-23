"""Recorded input is explicit and never starts an execution environment."""
import json
from types import SimpleNamespace

import numpy as np
import pytest
from robotwin20_adapter.single_view_perception import Proposal

from isaacsim_lab.perception_probe import RecordedSegmentation, main, replay_capture
from isaacsim_lab.visual_perception import LabArtifactStore


def test_recorded_masks_use_the_same_provider_proposal(tmp_path):
    records = [{'index': 0, 'claim': {'bbox_xyxy': [1, 2, 3, 4]}}]
    np.save(tmp_path/'replay-mask-0.npy', np.ones((5, 5), dtype=bool))
    provider = RecordedSegmentation(tmp_path, records)
    request = SimpleNamespace(proposal=Proposal((1, 2, 3, 4), .9))
    assert provider.segment(request).mask.all()
    provider.records.append(records[0])
    with pytest.raises(ValueError, match='ambiguous'):
        provider.segment(request)


def test_replay_preserves_capture_references_and_copies_only_its_artifacts(tmp_path):
    source = tmp_path/'source'
    store = LabArtifactStore(source/'artifacts/labutopia')
    depth = store.write('depth', np.ones((2, 3)))
    calibration = store.write('calibration', {'frame_id': 'camera'})
    capture = {'status': 'available', 'calibration_ref': calibration, 'artifacts': [{'ref': depth}]}
    (source/'perception.json').write_text(json.dumps({'capture': capture}))
    (source/'segmentation-replay.json').write_text('[]')
    copied, inference, _ = replay_capture(source, tmp_path/'destination')
    assert copied == capture
    assert np.load(LabArtifactStore(tmp_path/'destination').path(depth)).shape == (2, 3)
    assert 'Replayed' in inference.infer(None)['ambiguities'][0]


def test_probe_rejects_existing_output_directory_before_loading_models(tmp_path):
    with pytest.raises(FileExistsError):
        main(['--profile', 'unused.json', '--workspace', str(tmp_path)])
