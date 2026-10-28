"""Sensor/model substitution tests: no Isaac imports, meshes or rule grasps."""
import io
import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from PhyAgentOS.forge.artifacts import LocalFilesystemArtifactResolver
from PhyAgentOS.forge.capability_runtime.grasp_proposal import GraspProposalEndpoint
from PhyAgentOS.forge.capability_runtime.understanding import SceneUnderstandingEndpoint
from pick_place_workflow.perception_binding import grasp_geometry_artifacts
from PIL import Image
from robotwin20_adapter.geometry_recovery import GeometryRecoveryResult
from robotwin20_adapter.grasp_proposal import GraspNetProposalProvider

from isaacsim_lab.visual_geometry import candidate_world_pose, pixel_to_world, process_features
from isaacsim_lab.visual_perception import (
    LabArtifactStore,
    LabVisualPerception,
    RecordedGraspProvider,
    RGBLabelPointInference,
)

CONVENTION = np.array([[0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1.]])


def test_depth_projection_uses_optical_frame_calibration():
    calibration = {"intrinsics": [[100., 0., 2.], [0., 100., 2.], [0., 0., 1.]],
                   "camera_pose_world": {"position_m": [1., 2., 3.], "orientation_wxyz": [1., 0., 0., 0.]}}
    world, _ = pixel_to_world([3., 2.], np.full((5, 5), 2.), calibration)
    assert world == pytest.approx([1.02, 2., 5.])
    with pytest.raises(ValueError, match="no measured depth"):
        pixel_to_world([2., 2.], np.zeros((5, 5)), calibration)
    with pytest.raises(ValueError, match="outside"):
        pixel_to_world([-1., 2.], np.ones((5, 5)), calibration)


def test_process_features_require_explicit_visible_support():
    theta = np.linspace(0, 2*np.pi, 100)
    rim = np.column_stack((.04*np.cos(theta)+.2, .04*np.sin(theta)-.1, np.ones(100)))
    points = np.concatenate([rim, rim-[0, 0, .1]])
    with pytest.raises(ValueError, match="explicit"):
        process_features(points, "mixing_vessel")
    support = {"kind": "rim", "points_world": rim.tolist(), "fully_visible": True}
    features = process_features(points, "mixing_vessel", support=support)
    assert features['tip_world'] == pytest.approx([.2, -.1, 1.])
    assert not any('grasp' in key for key in features)
    rod = np.column_stack((np.linspace(0., .2, 100), .0001*np.sin(theta), .001*np.cos(theta)))
    support = {"kind": "rod_endpoints", "points_world": [[0, 0, 0], [.2, 0, 0]], "fully_visible": False}
    with pytest.raises(ValueError, match="visible"):
        process_features(rod, 'stir_tool', support=support)
    support['fully_visible'] = True
    features = process_features(rod, 'stir_tool', support=support)
    assert features['tip_world'] == [.2, 0, 0]
    assert features['axis_world'] == [1, 0, 0]


def fixture(tmp_path):
    store = LabArtifactStore(tmp_path)
    rgb_ref = 'artifact://labutopia/rgb/test.png'
    store.path(rgb_ref).parent.mkdir(parents=True)
    Image.new('RGB', (32, 32)).save(store.path(rgb_ref))
    depth_ref = store.write('depth', 1 + np.indices((32, 32))[0] * .0001)
    calibration_ref = store.write('calibration', {'scene_revision': 'scene', 'frame_id': 'front',
        'intrinsics': [[1000, 0, 16], [0, 1000, 16], [0, 0, 1]],
        'camera_pose_world': {'position_m': [0, 0, 0], 'orientation_wxyz': [1, 0, 0, 0]}})
    request = {'observation_ref': 'observation://scene/front', 'scene_revision': 'scene', 'frame_id': 'front',
               'calibration_ref': calibration_ref, 'freshness_ms': 0, 'max_age_ms': 1000,
               'artifacts': [rgb_ref, depth_ref]}
    mask = np.zeros((32, 32), dtype=bool)
    mask[5:27, 14:18] = True
    segmentation = Mock()
    segmentation.segment.return_value = SimpleNamespace(mask=mask)
    inference = Mock()
    inference.infer.return_value = {'objects': [{'category': 'stir_tool', 'label': 'ROD',
        'pixel_xy': [16, 16], 'bbox_xyxy': [14, 5, 18, 27], 'confidence': .95}], 'ambiguities': []}
    engine = Mock()
    engine.bind_observed_entities.return_value = {'status': 'available', 'capabilities': {},
        'records': [{'entity_ref': 'entity://rod', 'prim_path': '/World/private-rod',
                     'captured_body_pose': np.eye(4).tolist()}]}
    worker = Mock()
    def predict(payload):
        assert np.load(payload['point_cloud_path']).shape[1] == 3
        matrices = [np.eye(4), np.eye(4)]
        matrices[1][0, 3] = .02
        return {'request_id': payload['request_id'], 'status': 'available',
                'candidates': [{'matrix': m.tolist(), 'score': .9-i*.1} for i, m in enumerate(matrices)],
                'funnel': {'decoded': 2, 'canonicalized': 2, 'deduplicated': 2, 'retained': 2}}
    worker.request.side_effect = predict
    grasp = RecordedGraspProvider(GraspNetProposalProvider(worker, artifact_store=store), store)
    geometry = Mock()
    geometry.recover.return_value = GeometryRecoveryResult(
        depth_m=np.full((32, 32), .8, dtype=np.float32),
        metadata={"method": "test_recovery", "unit": "m", "geometry_qualification": "unverified_estimate"})
    visual = LabVisualPerception(engine, LocalFilesystemArtifactResolver({'labutopia': tmp_path}), inference,
        segmentation=segmentation, geometry=geometry, store=store, grasps=grasp, provider_from_tcp=CONVENTION)
    return visual, grasp, request, worker


def test_sensor_segmentation_cloud_pass_real_understanding_and_grasp_endpoints(tmp_path):
    visual, grasp, request, worker = fixture(tmp_path)
    result = SceneUnderstandingEndpoint(visual).invoke(request)
    assert result['status'] == 'available', result
    assert '/World' not in str(result)
    assert [x['kind'] for x in result['derived_artifacts']] == ['instance_mask', 'object_point_cloud']
    entity = result['entities'][0]
    proposal = {k: v for k, v in request.items() if k != 'artifacts'}
    proposal['targets'] = [{**{k: entity[k] for k in ('entity_ref', 'category', 'confidence')},
                            'geometry_artifacts': grasp_geometry_artifacts(result, entity['entity_ref'])}]
    predicted = GraspProposalEndpoint(grasp).invoke(proposal)
    assert predicted['status'] == 'available', predicted
    assert len(predicted['candidates']) == 2
    candidate = predicted['candidates'][1]
    binding = {**proposal, 'candidate_ref': candidate['candidate_ref'], 'grasp_candidate': candidate}
    assert grasp.candidate(binding) == candidate
    altered = deepcopy(binding)
    altered['grasp_candidate']['grasp_frame']['position_m'][0] += .01
    with pytest.raises(ValueError, match='differs'):
        grasp.candidate(altered)
    world = np.eye(4)
    world[:3, 3] = [1, 2, 3]
    target, approach = candidate_world_pose(candidate, world, CONVENTION)
    assert target[:3, 3] == pytest.approx([1.02, 2, 3])
    assert target[:3, 2] == pytest.approx(approach)
    with pytest.raises(ValueError, match='convention'):
        candidate_world_pose(candidate, world, np.eye(4))
    assert worker.request.call_count == 1


def test_visual_capture_mismatch_and_identity_pixel_outside_mask(tmp_path):
    visual, _, request, _ = fixture(tmp_path)
    visual.understand(request)
    with pytest.raises(ValueError, match='does not match'):
        visual._records({**request, 'observation_ref': 'observation://other/front'})
    visual.inference.infer.return_value['objects'][0]['pixel_xy'] = [0, 0]
    calibration = json.loads(visual.store.path(request['calibration_ref']).read_text())
    request = {**request, 'observation_ref': 'observation://new/front',
               'calibration_ref': visual.store.write('calibration', calibration)}
    result = visual.understand(request)
    assert not result['entities']
    assert 'not inside' in result['ambiguities'][0]['message']
    assert visual.segmentation.release.call_count == 2


def test_rgb_inference_preserves_unresolved_objects_for_geometry():
    objects = [{'category': 'reagent_bottle', 'label': 'REAGENT A', 'pixel_xy': [1, 1], 'bbox_xyxy': [0, 0, 2, 2],
                'confidence': .95, 'identity_resolved': True},
               {'category': 'stir_tool', 'label': None, 'pixel_xy': [2, 2], 'bbox_xyxy': [1, 1, 3, 3],
                'confidence': .72, 'identity_resolved': False}]
    client = Mock()
    client.responses.create.return_value.output_text = json.dumps({'objects': objects, 'ambiguities': ['Rod occluded']})
    data = io.BytesIO()
    Image.new('RGB', (4, 4)).save(data, format='PNG')
    result = RGBLabelPointInference(client, model='test').infer(SimpleNamespace(data=data.getvalue(), media_type='image/png'))
    assert [item['label'] for item in result['objects']] == ['REAGENT A', None]
    assert result['ambiguities'] == ['Rod occluded']
    assert client.responses.create.call_args.kwargs['max_output_tokens'] == 4096


def test_rgb_inference_records_bounded_json_decode_context():
    client = Mock()
    output = '{"objects": [],\n' + (' ' * 1000) + 'not-json'
    client.responses.create.return_value.output_text = output
    data = io.BytesIO()
    Image.new('RGB', (4, 4)).save(data, format='PNG')
    with pytest.raises(json.JSONDecodeError) as caught:
        RGBLabelPointInference(client, model='test').infer(
            SimpleNamespace(data=data.getvalue(), media_type='image/png'))
    diagnostics = caught.value.response_diagnostics
    assert diagnostics['output_length'] == len(output)
    assert diagnostics['line'] == 2
    assert diagnostics['column'] > 1
    assert len(diagnostics['excerpt']) <= 640
    assert 'not-json' in diagnostics['excerpt']


def test_malformed_model_response_context_is_persisted(tmp_path):
    visual, _, request, _ = fixture(tmp_path)
    output = '{"objects": [],\nnot-json'
    with pytest.raises(json.JSONDecodeError) as caught:
        json.loads(output)
    caught.value.response_diagnostics = {'output_length': len(output), 'line': caught.value.lineno,
                                         'column': caught.value.colno, 'position': caught.value.pos,
                                         'excerpt': output}
    visual.inference.infer.side_effect = caught.value
    result = SceneUnderstandingEndpoint(visual).invoke(request)
    assert result['status'] != 'available'
    diagnostics = list(visual.store.root.glob('perception-failure/*.json'))
    failure = json.loads(diagnostics[0].read_text())
    assert failure['error_type'] == 'JSONDecodeError'
    assert failure['response_diagnostics']['excerpt'] == output


def test_recovered_surface_is_not_truncated_by_a_raw_depth_seed_filter(tmp_path):
    visual, _, request, _ = fixture(tmp_path)
    depth = visual.geometry.recover.return_value.depth_m
    depth[:, 16:] = 1.2
    result = visual.understand(request)
    cloud = next(a for a in result['derived_artifacts'] if a['kind'] == 'object_point_cloud')
    points = np.load(visual.store.path(cloud['artifact_ref']))
    assert len(points) == int(visual.segmentation.segment.return_value.mask.sum())
    assert points[:, 2].min() == pytest.approx(.8)
    assert points[:, 2].max() == pytest.approx(1.2)


def test_predictions_for_two_queries_at_same_capture_are_not_overwritten(tmp_path):
    visual, grasp, request, _ = fixture(tmp_path)
    result = visual.understand(request)
    entity = result['entities'][0]
    proposal = {k: v for k, v in request.items() if k != 'artifacts'}
    proposal['targets'] = [{**{k: entity[k] for k in ('entity_ref', 'category', 'confidence')},
                           'geometry_artifacts': grasp_geometry_artifacts(result, entity['entity_ref'])}]
    first = grasp.propose(proposal)['candidates'][0]
    second = grasp.propose(proposal)['candidates'][0]
    assert first['candidate_ref'] != second['candidate_ref']
    for candidate in (first, second):
        assert grasp.candidate({**request, 'candidate_ref': candidate['candidate_ref'], 'grasp_candidate': candidate}) == candidate


def test_recovered_cloud_reaches_grasp_without_simulator_identity(tmp_path):
    visual, grasp, request, worker = fixture(tmp_path)
    result = visual.understand(request)
    visual.engine.bind_observed_entities.assert_not_called()
    cloud = next(a for a in result['derived_artifacts'] if a['kind'] == 'object_point_cloud')
    assert np.load(visual.store.path(cloud['artifact_ref']))[:, 2] == pytest.approx(.8)
    assert cloud['descriptor']['confidence'] is None
    assert result['spatial_envelopes'] == []
    record = visual.observations[request['calibration_ref']][result['entities'][0]['entity_ref']]
    evidence = json.loads(visual.store.path(record['geometry_ref']).read_text())
    assert evidence['geometry_qualification'] == 'unverified_estimate'
    assert evidence['process_features'] is None
    assert visual.understand(request) == result
    assert visual.geometry.recover.call_count == 1


def test_geometry_failure_persists_diagnostics_and_does_not_use_raw_depth(tmp_path):
    visual, _, request, worker = fixture(tmp_path)
    visual.geometry.recover.side_effect = RuntimeError('missing trained checkpoint')
    result = SceneUnderstandingEndpoint(visual).invoke(request)
    assert result['status'] != 'available'
    assert visual.diagnostic_summary()['reason'] == 'provider_failure'
    diagnostics = list(visual.store.root.glob('perception-failure/*.json'))
    assert 'missing trained checkpoint' in diagnostics[0].read_text()
    worker.request.assert_not_called()
    visual.geometry.release.assert_called_once()


def test_one_bad_object_does_not_discard_other_masks(tmp_path):
    visual, _, request, _ = fixture(tmp_path)
    valid = visual.inference.infer.return_value['objects'][0]
    visual.inference.infer.return_value['objects'].append({**valid, 'pixel_xy': [0, 0]})
    result = visual.understand(request)
    assert len(result['entities']) == 1
    assert any('not inside' in a['message'] for a in result['ambiguities'])


def test_ambiguous_labels_do_not_create_duplicate_identity(tmp_path):
    visual, _, request, _ = fixture(tmp_path)
    valid = visual.inference.infer.return_value['objects'][0]
    visual.inference.infer.return_value['objects'].append(dict(valid))
    result = visual.understand(request)
    assert len({e['entity_ref'] for e in result['entities']}) == 2
    assert all('label' not in e for e in result['entities'])


def test_private_execution_uses_recovered_points_and_rejects_stale_evidence(tmp_path):
    from isaacsim_lab.execution_identity import association_points
    visual, _, request, _ = fixture(tmp_path)
    result = visual.understand(request)
    entity = result['entities'][0]['entity_ref']
    record = visual.observations[request['calibration_ref']][entity]
    claim = {'entity_ref': entity, 'points_ref': record['points_ref']}
    assert association_points(visual.store, claim, request)[:, 2] == pytest.approx(.8)
    with pytest.raises(ValueError, match='different observation'):
        association_points(visual.store, claim, {**request, 'scene_revision': 'new'})


def test_prepare_rejects_missing_process_features_before_simulator_binding(tmp_path):
    visual, _, request, _ = fixture(tmp_path)
    result = visual.understand(request)
    entity = result['entities'][0]['entity_ref']
    visual.grasps.candidate = Mock(return_value={'entity_ref': entity,
        'grasp_frame': {'frame_id': request['frame_id'], 'position_m': [0, 0, .8], 'orientation_xyzw': [0, 0, 0, 1]},
        'approach_direction': {'vector': [1, 0, 0]}})
    binding = {**request, 'entity_ref': entity, 'destination_ref': entity.replace('entity://', 'destination://')}
    with pytest.raises(ValueError, match='lack observed process features'):
        visual.resolve(binding, {})
    visual.engine.bind_observed_entities.assert_not_called()


def test_held_refresh_requires_current_source_and_preserves_acquisition_grasp(tmp_path):
    visual, _, request, _ = fixture(tmp_path)
    result = visual.understand(request)
    source = result['entities'][0]['entity_ref']
    destination = 'entity://receiver'
    records = visual.observations[request['calibration_ref']]
    records[destination] = {**deepcopy(records[source]), 'entity_ref': destination}
    arguments = {**request, 'entity_ref': source, 'destination_ref': 'destination://receiver'}
    target = {'entity_prim_path': '/private/source', 'destination_prim_path': '/private/destination',
              'candidate_ref': 'candidate://source/acquired', 'grasp_frame': {'unchanged': True}}
    context = {'geometry_ref': 'artifact://history/geometry'}
    route = {'body_from_observed': np.eye(4).tolist()}
    with pytest.raises(ValueError, match='current source and destination'):
        visual.refresh_process(arguments, target, observation_model=context, phase_route=route)
    # Test qualified upstream evidence as a substitute; it is not produced by
    # the unverified model worker or a claim about our scene's qualification.
    for record in records.values():
        record['geometry_qualification'] = 'validated_observation'
        record['features'] = {'tip_world': [1., 0., 1.2], 'axis_world': [0, 0, 1]}
    pose = np.eye(4)
    pose[:3, 3] = [1, 0, 1]
    visual._bind_execution = Mock(return_value={source: {'prim_path': '/private/source', 'captured_body_pose': pose.tolist()},
                                               destination: {'prim_path': '/private/destination'}})
    refreshed = visual.refresh_process(arguments, target, observation_model=context, phase_route=route)
    assert refreshed['tool_frame']['tip_offset_m'] == pytest.approx([0, 0, .2])
    assert refreshed['grasp_frame'] == target['grasp_frame']
    assert refreshed['candidate_ref'] == target['candidate_ref']
    assert refreshed['process_frame']['origin_m'] == [1., 0., 1.2]


def test_simulator_truth_injection_skips_model_workers_and_preserves_capture_lineage(tmp_path):
    store = LabArtifactStore(tmp_path)
    rgb_ref = 'artifact://labutopia/rgb/truth.png'
    store.path(rgb_ref).parent.mkdir(parents=True)
    Image.new('RGB', (16, 16)).save(store.path(rgb_ref))
    depth_ref = store.write('depth', np.ones((16, 16), dtype=np.float32))
    cloud = np.zeros((16, 16, 3), dtype=np.float32)
    cloud[..., 2] = 1.0
    cloud[..., 0] = np.linspace(-.1, .1, 16)[None, :]
    cloud[..., 1] = np.linspace(-.1, .1, 16)[:, None]
    cloud_ref = store.write('point_cloud', cloud)
    calibration_ref = store.write('calibration', {'scene_revision': 'scene', 'frame_id': 'front',
        'intrinsics': [[100., 0., 8.], [0., 100., 8.], [0., 0., 1.]],
        'camera_pose_world': {'position_m': [0, 0, 0], 'orientation_wxyz': [1, 0, 0, 0]}})
    request = {'observation_ref': 'observation://scene/front', 'scene_revision': 'scene', 'frame_id': 'front',
               'calibration_ref': calibration_ref, 'freshness_ms': 0, 'max_age_ms': 1000,
               'artifacts': [rgb_ref, depth_ref, cloud_ref]}
    manifest = {'objects': {
        'R01': {'label': 'R01', 'category': 'reagent_bottle', 'prim_path': '/World/R01',
                'origin_world': [-.04, 0., 1.], 'tip_world': [-.04, 0., 1.1],
                'axis_world': [0., 0., 1.], 'size_m': [.1, .1, .2]},
        'BEAKER': {'label': 'BEAKER', 'category': 'mixing_vessel', 'prim_path': '/World/Beaker',
                   'origin_world': [.04, 0., 1.], 'tip_world': [.04, 0., 1.1],
                   'axis_world': [0., 0., 1.], 'size_m': [.2, .2, .2]},
    }}
    segmentation, geometry, inference = Mock(), Mock(), Mock()
    grasps = Mock()
    visual = LabVisualPerception(Mock(), LocalFilesystemArtifactResolver({'labutopia': tmp_path}), inference,
        segmentation=segmentation, geometry=geometry, store=store, grasps=grasps,
        provider_from_tcp=CONVENTION, truth_manifest=manifest)
    result = visual.understand(request)
    assert {item['label'] for item in result['entities']} == {'R01', 'BEAKER'}
    assert not segmentation.segment.called
    assert not geometry.recover.called
    for entity in result['entities']:
        record = visual.observations[calibration_ref][entity['entity_ref']]
        assert record['geometry_qualification'] == 'simulator_ground_truth'
        evidence = json.loads(store.path(record['geometry_ref']).read_text())
        assert evidence['source_refs'][0].startswith('artifact://labutopia/simulator-truth/')
