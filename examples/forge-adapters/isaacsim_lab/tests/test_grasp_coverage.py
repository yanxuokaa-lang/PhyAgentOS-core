"""The deployed sampling budget must reach qualification through existing ports."""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from isaacsim_lab.perception_runtime import build_visual_providers


def build(tmp_path, monkeypatch, *, failure=False):
    seen = []
    native = []
    for index in range(70):
        pose = np.eye(4)
        pose[0, 3] = .01 * index  # Distinct contacts, outside normal NMS distance.
        native.append({'matrix': pose.tolist(), 'score': .9 - index * .01,
                       'grasp_geometry': {'width_m': .04, 'height_m': .02, 'depth_m': .03}})

    def invoke(request):
        seen.append(request)
        if failure:
            raise RuntimeError('replacement provider unavailable')
        assert request['max_candidates'] >= len(native)
        return {'request_id': request['request_id'], 'status': 'available', 'candidates': native,
                'funnel': dict.fromkeys(('decoded', 'canonicalized', 'deduplicated', 'retained'), len(native))}

    monkeypatch.setattr('isaacsim_lab.perception_runtime.JsonlProcessWorkerClient',
                        lambda _: SimpleNamespace(request=invoke, release=lambda: None))
    profile = Path(__file__).parents[1] / 'configs/labutopia-mixture-perception.json'
    visual, grasps = build_visual_providers(profile, None, tmp_path, None)
    points = visual.store.write('object-point-cloud', np.ones((20, 3)))
    identity = {'observation_ref': 'observation://capture/view', 'scene_revision': 'capture',
                'frame_id': 'view', 'calibration_ref': 'calibration://capture/view'}
    geometry = {**identity, 'entity_ref': 'entity://vessel', 'kind': 'object_point_cloud',
                'artifact_ref': points, 'provenance': [points]}
    request = {**identity, 'targets': [{'entity_ref': 'entity://vessel', 'geometry_artifacts': [geometry]}]}
    return grasps, request, native, seen


def test_deployed_budget_preserves_native_contacts_until_task_qualification(tmp_path, monkeypatch):
    grasps, request, native, seen = build(tmp_path, monkeypatch)
    result = grasps.propose(request)
    assert len(result['candidates']) == len(native)
    assert result['funnel']['retained'] == result['funnel']['deduplicated']
    expected = {tuple(np.array(c['matrix'])[:3, 3]): c for c in native}
    for candidate in result['candidates']:
        source = expected[tuple(candidate['grasp_frame']['position_m'])]
        assert candidate['score'] == source['score']
        assert candidate['grasp_geometry'] == source['grasp_geometry']
        assert candidate['grasp_frame']['frame_id'] == request['frame_id']
        assert candidate['candidate_ref'] in grasps.captures[request['calibration_ref']]
        assert grasps.candidate({**request, 'candidate_ref': candidate['candidate_ref'],
                                 'grasp_candidate': candidate}) == candidate
    assert seen[0]['observation_ref'] == request['observation_ref']
    assert seen[0]['scene_revision'] == request['scene_revision']
    assert seen[0]['apply_model_collision'] is False  # Runtime collision is still authoritative.


def test_expanded_pool_keeps_capture_scoped_opaque_refs(tmp_path, monkeypatch):
    grasps, request, _native, _seen = build(tmp_path, monkeypatch)
    first = grasps.propose(request)['candidates']
    second_request = {**request, 'calibration_ref': 'calibration://capture/second'}
    geometry = {**request['targets'][0]['geometry_artifacts'][0],
                'calibration_ref': second_request['calibration_ref']}
    second_request['targets'] = [{'entity_ref': 'entity://vessel', 'geometry_artifacts': [geometry]}]
    second = grasps.propose(second_request)['candidates']
    assert not {c['candidate_ref'] for c in first} & {c['candidate_ref'] for c in second}
    with pytest.raises(ValueError, match='selected grasp differs'):
        grasps.candidate({**second_request, 'candidate_ref': first[0]['candidate_ref'], 'grasp_candidate': first[0]})


def test_expanded_pool_provider_failure_does_not_publish_candidates(tmp_path, monkeypatch):
    grasps, request, _native, _seen = build(tmp_path, monkeypatch, failure=True)
    with pytest.raises(RuntimeError, match='replacement provider unavailable'):
        grasps.propose(request)
    assert grasps.captures == {} and grasps.candidate_sets == {}


@pytest.mark.parametrize('fail', [False, True])
def test_sampling_diagnostic_persists_metadata_and_never_manufactures_success(tmp_path, monkeypatch, fail):
    import importlib.util
    import json
    import sys

    path = Path(__file__).parents[1] / 'scripts/inspect_grasp_sampling.py'
    spec = importlib.util.spec_from_file_location('sampling_diagnostic', path)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    request = {'targets': [{'entity_ref': 'entity://observed', 'geometry_artifacts': [
        {'artifact_ref': 'artifact://labutopia/object-point-cloud/capture.npy'}]}]}
    prediction = tmp_path / 'prediction.json'
    prediction.write_text(json.dumps({'request': request}))
    output = tmp_path / 'new-output'
    profile = Path(__file__).parents[1] / 'configs/labutopia-mixture-perception.json'
    monkeypatch.setattr(sys, 'argv', ['inspect', '--profile', str(profile), '--prediction', str(prediction),
                                    '--artifact-root', str(tmp_path), '--output', str(output)])
    worker = SimpleNamespace(_parser=lambda: SimpleNamespace(parse_args=lambda _: SimpleNamespace()),
                             _sample_candidates=lambda candidates, limit, policy: candidates[:limit])

    def load():
        if fail:
            raise RuntimeError('model unavailable')

    def handle(payload):
        assert payload['point_cloud_path'] == str(tmp_path / 'object-point-cloud/capture.npy')
        return {'candidates': worker._sample_candidates([{'score': .3}], 1, 'score')}

    worker._load, worker._handle = load, handle
    monkeypatch.setitem(sys.modules, 'graspnet_worker', worker)
    monkeypatch.setattr(script.subprocess, 'check_output', lambda *_a, **_k: 'fixture-commit\n')
    if fail:
        with pytest.raises(RuntimeError, match='model unavailable'):
            script.main()
    else:
        script.main()
    receipt = json.loads((output / 'sampling.json').read_text())
    assert receipt['motion_authorized'] is False
    assert receipt['evidence_kind'] == 'historical_grasp_sampling_diagnostic'
    assert receipt['configuration']['grasp']['sample_count'] == 512
    assert receipt['commit'] == 'fixture-commit'
    assert 'def _input_regions(' in receipt['worker_source']
    assert receipt['status'] == ('failed' if fail else 'complete')
    if fail:
        assert 'native_candidates' not in receipt
    else:
        assert receipt['native_candidates'] == receipt['worker_outputs'][0]['candidates']
