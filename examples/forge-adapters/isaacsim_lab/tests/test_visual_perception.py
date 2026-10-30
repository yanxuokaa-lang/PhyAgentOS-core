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

from isaacsim_lab.simulator_truth_perception import (
    process_feature_candidates,
    process_feature_candidates_by_component,
)
from isaacsim_lab.visual_geometry import candidate_world_pose, pixel_to_world, process_features
from isaacsim_lab.visual_perception import (
    LabArtifactStore,
    LabGraspTaskAffordanceProvider,
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


def test_simulator_truth_geometry_derives_rim_and_preserves_rod_endpoint_ambiguity():
    theta = np.linspace(0, 2*np.pi, 128, endpoint=False)
    ring = np.column_stack((.04*np.cos(theta), .04*np.sin(theta), np.full(len(theta), .2)))
    side = np.column_stack((.04*np.cos(theta), .04*np.sin(theta), np.linspace(0, .2, len(theta))))
    shell = np.vstack((ring, side))
    edges = np.stack((ring, np.roll(ring, -1, axis=0)), axis=1)
    vessel = process_feature_candidates(shell, edges, 'mixing_vessel')
    assert vessel[0]['feature_kind'] == 'rim'
    assert vessel[0]['tip_world'] == pytest.approx([0., 0., .2], abs=1e-4)
    assert vessel[0]['source'] == 'final_composed_usd_mesh'

    z = np.linspace(0., .3, 100)
    rod = np.column_stack((np.zeros_like(z), np.zeros_like(z), z))
    candidates = process_feature_candidates(rod, [], 'stir_tool')
    assert len(candidates) == 2
    assert {item['feature_role'] for item in candidates} == {'endpoint_a', 'endpoint_b'}
    assert candidates[0]['origin_world'] == pytest.approx(candidates[1]['tip_world'])
    assert candidates[1]['origin_world'] == pytest.approx(candidates[0]['tip_world'])


def test_truth_manifest_discards_legacy_functional_coordinates(tmp_path):
    from isaacsim_lab.simulator_truth_perception import load_truth_manifest

    path = tmp_path / 'truth.json'
    path.write_text(json.dumps({'objects': [{
        'label': 'ROD', 'category': 'stir_tool', 'prim_path': '/World/Rod',
        'origin_world': [90, 90, 90], 'tip_world': [-90, -90, -90],
        'axis_world': [1, 0, 0], 'size_m': [99, 99, 99],
    }]}), encoding='utf-8')
    item = load_truth_manifest(path)['objects']['ROD']
    assert item == {'label': 'ROD', 'category': 'stir_tool', 'prim_path': '/World/Rod'}


def test_simulator_truth_geometry_rejects_open_or_nonmanifold_rim_boundary():
    theta = np.linspace(0, 2*np.pi, 64, endpoint=False)
    ring = np.column_stack((.03*np.cos(theta), .03*np.sin(theta), np.full(len(theta), .2)))
    side = np.column_stack((.03*np.cos(theta), .03*np.sin(theta), np.linspace(0, .2, len(theta))))
    shell = np.vstack((ring, side))
    edges = np.stack((ring[:-1], ring[1:]), axis=1)
    with pytest.raises(ValueError, match='open or non-manifold'):
        process_feature_candidates(shell, edges, 'reagent_bottle')


def test_simulator_truth_geometry_keeps_valid_rim_when_unrelated_boundary_is_open():
    theta = np.linspace(0, 2*np.pi, 32, endpoint=False)
    ring = np.column_stack((.03*np.cos(theta), .03*np.sin(theta), np.full(len(theta), .2)))
    branch = np.asarray([[.2, .2, .1], [.21, .2, .1], [.22, .2, .1], [.21, .21, .1]])
    ring_edges = np.stack((ring, np.roll(ring, -1, axis=0)), axis=1)
    branch_edges = np.asarray([[branch[0], branch[index]] for index in (1, 2, 3)])
    features = process_feature_candidates(
        np.vstack((ring, branch)), np.concatenate((ring_edges, branch_edges)), 'mixing_vessel'
    )
    assert len(features) == 1
    assert features[0]['feature_kind'] == 'rim'
    assert features[0]['tip_world'] == pytest.approx([0., 0., .2], abs=1e-4)


def test_simulator_truth_geometry_rejects_duplicate_nonmanifold_boundary_edges():
    theta = np.linspace(0, 2*np.pi, 32, endpoint=False)
    ring = np.column_stack((.03*np.cos(theta), .03*np.sin(theta), np.full(len(theta), .2)))
    edges = np.stack((ring, np.roll(ring, -1, axis=0)), axis=1)
    with pytest.raises(ValueError, match='open or non-manifold'):
        process_feature_candidates(ring, np.concatenate((edges, edges)), 'mixing_vessel')


def test_simulator_truth_geometry_keeps_coincident_mesh_component_candidates_separate():
    theta = np.linspace(0, 2*np.pi, 32, endpoint=False)
    ring = np.column_stack((.03*np.cos(theta), .03*np.sin(theta), np.full(len(theta), .2)))
    edges = np.stack((ring, np.roll(ring, -1, axis=0)), axis=1)
    unsupported_top = np.column_stack((np.linspace(-.1, .1, 24), np.linspace(.1, -.1, 24), np.full(24, .3)))
    candidates = process_feature_candidates_by_component(
        np.vstack((ring, unsupported_top)), [edges, edges.copy()], 'mixing_vessel'
    )
    assert len(candidates) == 2
    assert [item['mesh_component_index'] for item in candidates] == [0, 1]
    assert all(item['feature_kind'] == 'rim' for item in candidates)


def test_simulator_truth_geometry_ignores_degenerate_boundary_edges():
    theta = np.linspace(0, 2*np.pi, 32, endpoint=False)
    ring = np.column_stack((.03*np.cos(theta), .03*np.sin(theta), np.full(len(theta), .2)))
    degenerate = np.repeat(ring[:1, None, :], 2, axis=1)
    with pytest.raises(ValueError, match='open or non-manifold'):
        process_feature_candidates(ring, degenerate, 'mixing_vessel')


def test_simulator_truth_geometry_uses_fully_covered_top_mesh_ring_when_edges_degenerate():
    theta = np.linspace(0, 2*np.pi, 96, endpoint=False)
    rim = np.column_stack((.03*np.cos(theta)-.08, .03*np.sin(theta), np.full(len(theta), .8)))
    wall = np.column_stack((.03*np.cos(theta)-.08, .03*np.sin(theta), np.linspace(.72, .8, len(theta))))
    points = np.vstack((rim, wall))
    degenerate_edges = np.repeat(rim[:1, None, :], 2, axis=1)

    candidates = process_feature_candidates_by_component(
        points, [degenerate_edges], 'mixing_vessel'
    )

    assert len(candidates) == 1
    assert candidates[0]['feature_kind'] == 'rim'
    assert candidates[0]['tip_world'] == pytest.approx([-.08, 0., .8], abs=1e-5)
    assert candidates[0]['rim_radius_m'] == pytest.approx(.03, abs=1e-5)
    assert candidates[0]['coverage'] == 'top_mesh_vertex_ring'


def test_simulator_truth_geometry_does_not_fit_an_incomplete_top_mesh_arc():
    theta = np.linspace(0, np.pi / 2, 24)
    rim = np.column_stack((.03*np.cos(theta), .03*np.sin(theta), np.full(len(theta), .8)))
    wall = np.column_stack((.03*np.cos(theta), .03*np.sin(theta), np.linspace(.72, .8, len(theta))))
    with pytest.raises(ValueError, match='fully covered circular rim'):
        process_feature_candidates_by_component(
            np.vstack((rim, wall)), [], 'mixing_vessel'
        )


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
    state_ref = store.write('state', _truth_state())
    calibration_ref = store.write('calibration', {'scene_revision': 'scene', 'frame_id': 'front',
        'intrinsics': [[100., 0., 8.], [0., 100., 8.], [0., 0., 1.]],
        'camera_pose_world': {'position_m': [0, 0, 0], 'orientation_wxyz': [1, 0, 0, 0]}})
    request = {'observation_ref': 'observation://scene/front', 'scene_revision': 'scene', 'frame_id': 'front',
               'calibration_ref': calibration_ref, 'freshness_ms': 0, 'max_age_ms': 1000,
               'artifacts': [rgb_ref, depth_ref, cloud_ref, state_ref]}
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
    assert len(result['spatial_envelopes']) == 2
    assert all(item['provenance'] == [state_ref] for item in result['spatial_envelopes'])
    assert not segmentation.segment.called
    assert not geometry.recover.called
    for entity in result['entities']:
        record = visual.observations[calibration_ref][entity['entity_ref']]
        assert record['geometry_qualification'] == 'simulator_ground_truth'
        assert record['features'] is None
        evidence = json.loads(store.path(record['geometry_ref']).read_text())
        assert evidence['source_refs'][0].startswith('artifact://labutopia/simulator-truth/')
        assert evidence['process_features'] is None


def test_simulator_truth_extracts_private_mesh_candidates_without_manifest_coordinates(tmp_path):
    store = LabArtifactStore(tmp_path)
    rgb_ref = 'artifact://labutopia/rgb/truth-mesh.png'
    store.path(rgb_ref).parent.mkdir(parents=True)
    Image.new('RGB', (16, 16)).save(store.path(rgb_ref))
    depth_ref = store.write('depth', np.ones((16, 16), dtype=np.float32))
    cloud = np.zeros((16, 16, 3), dtype=np.float32)
    cloud[..., 0] = np.linspace(.03, .09, 16)[None, :]
    cloud[..., 1] = np.linspace(-.08, .08, 16)[:, None]
    cloud[..., 2] = 1.
    cloud_ref = store.write('point_cloud', cloud)
    theta = np.linspace(0, 2*np.pi, 64, endpoint=False)
    ring = np.column_stack((.04*np.cos(theta), .04*np.sin(theta), np.full(len(theta), 1.1)))
    side = np.column_stack((.04*np.cos(theta), .04*np.sin(theta), np.linspace(1., 1.1, len(theta))))
    shell = np.vstack((ring, side))
    edges = np.stack((ring, np.roll(ring, -1, axis=0)), axis=1).tolist()
    state = _truth_state(schema='labutopia-simulator-world-geometry/v1',
                         source='final_composed_usd_world_geometry')
    state['objects'][0].update({'mesh_points_world_m': shell.tolist(), 'boundary_edges_world_m': edges})
    state_ref = store.write('state', state)
    calibration_ref = store.write('calibration', {'scene_revision': 'scene', 'frame_id': 'front',
        'intrinsics': [[100., 0., 8.], [0., 100., 8.], [0., 0., 1.]],
        'camera_pose_world': {'position_m': [0, 0, 0], 'orientation_wxyz': [1, 0, 0, 0]}})
    request = {'observation_ref': 'observation://scene/front', 'scene_revision': 'scene', 'frame_id': 'front',
               'calibration_ref': calibration_ref, 'freshness_ms': 0, 'max_age_ms': 1000,
               'artifacts': [rgb_ref, depth_ref, cloud_ref, state_ref]}
    manifest = {'objects': {
        'R01': {'label': 'R01', 'category': 'reagent_bottle', 'prim_path': '/World/R01'},
        'BEAKER': {'label': 'BEAKER', 'category': 'mixing_vessel', 'prim_path': '/World/Beaker'},
    }}
    state['objects'][1].update({'mesh_points_world_m': shell.tolist(), 'boundary_edges_world_m': edges})
    state_ref = store.write('state', state)
    request['artifacts'][-1] = state_ref
    visual = LabVisualPerception(Mock(), LocalFilesystemArtifactResolver({'labutopia': tmp_path}), Mock(),
        segmentation=Mock(), geometry=Mock(), store=store, grasps=Mock(),
        provider_from_tcp=CONVENTION, truth_manifest=manifest)
    visual.understand(request)
    beaker = visual.observations[calibration_ref]['entity://simulator-truth-BEAKER']
    assert len(beaker['process_feature_candidates']) == 1
    assert beaker['process_feature_candidates'][0]['feature_kind'] == 'rim'
    assert beaker['features'] is None
    evidence = json.loads(store.path(beaker['geometry_ref']).read_text())
    assert evidence['process_features'] is None
    assert evidence['process_feature_candidates'][0]['source'] == 'final_composed_usd_mesh'


def test_simulator_truth_bounds_do_not_qualify_process_landmarks_for_preparation(tmp_path):
    store = LabArtifactStore(tmp_path)
    rgb_ref = 'artifact://labutopia/rgb/truth-process.png'
    store.path(rgb_ref).parent.mkdir(parents=True)
    Image.new('RGB', (16, 16)).save(store.path(rgb_ref))
    depth_ref = store.write('depth', np.ones((16, 16), dtype=np.float32))
    cloud = np.zeros((16, 16, 3), dtype=np.float32)
    cloud[..., 0] = np.linspace(-.1, .1, 16)[None, :]
    cloud[..., 1] = np.linspace(-.1, .1, 16)[:, None]
    cloud[..., 2] = 1.
    cloud_ref = store.write('point_cloud', cloud)
    state_ref = store.write('state', _truth_state())
    calibration_ref = store.write('calibration', {
        'scene_revision': 'scene', 'frame_id': 'front',
        'intrinsics': [[100., 0., 8.], [0., 100., 8.], [0., 0., 1.]],
        'camera_pose_world': {'position_m': [0, 0, 0], 'orientation_wxyz': [1, 0, 0, 0]},
    })
    request = {
        'observation_ref': 'observation://scene/front', 'scene_revision': 'scene',
        'frame_id': 'front', 'calibration_ref': calibration_ref, 'freshness_ms': 0,
        'max_age_ms': 1000, 'artifacts': [rgb_ref, depth_ref, cloud_ref, state_ref],
    }
    manifest = {'objects': {
        'R01': {'label': 'R01', 'category': 'reagent_bottle', 'prim_path': '/World/R01',
                'origin_world': [90., 90., 90.], 'tip_world': [91., 91., 91.],
                'axis_world': [0., 1., 0.], 'size_m': [9., 9., 9.]},
        'BEAKER': {'label': 'BEAKER', 'category': 'mixing_vessel', 'prim_path': '/World/Beaker',
                   'origin_world': [-90., -90., -90.], 'tip_world': [-91., -91., -91.],
                   'axis_world': [1., 0., 0.], 'size_m': [8., 8., 8.]},
    }}
    engine = Mock()
    visual = LabVisualPerception(
        engine, LocalFilesystemArtifactResolver({'labutopia': tmp_path}), Mock(),
        segmentation=Mock(), geometry=Mock(), store=store, grasps=Mock(),
        provider_from_tcp=CONVENTION, truth_manifest=manifest,
    )
    result = visual.understand(request)
    source = next(entity for entity in result['entities'] if entity['label'] == 'R01')
    destination = next(entity for entity in result['entities'] if entity['label'] == 'BEAKER')
    visual.grasps.candidate = Mock(return_value={
        'entity_ref': source['entity_ref'],
        'grasp_frame': {'frame_id': 'front', 'position_m': [0, 0, 1], 'orientation_xyzw': [0, 0, 0, 1]},
        'approach_direction': {'vector': [1, 0, 0]},
    })
    binding = {**request, 'entity_ref': source['entity_ref'],
               'destination_ref': destination['entity_ref'].replace('entity://', 'destination://')}

    with pytest.raises(ValueError, match='lack observed process features'):
        visual.resolve(binding, {})
    with pytest.raises(ValueError, match='current source and destination feature evidence'):
        visual.refresh_process(binding, {}, observation_model={'geometry_ref': 'artifact://geometry'},
                               phase_route={'body_from_observed': np.eye(4).tolist()})
    engine.bind_observed_entities.assert_not_called()


def _task_affordance_fixture(tmp_path, *, operation, grasp_position, source_category, source_points,
                             source_features):
    store = LabArtifactStore(tmp_path)
    identity = {
        "observation_ref": "observation://scene/front", "scene_revision": "scene",
        "frame_id": "front", "calibration_ref": "artifact://calibration/front",
    }
    source_ref, destination_ref = "entity://source", "entity://beaker"
    points_ref = store.write("object-point-cloud", np.asarray(source_points, dtype=np.float32))
    records = {
        source_ref: {**identity, "entity_ref": source_ref, "category": source_category,
                     "world_from_camera": np.eye(4).tolist(), "points_ref": points_ref},
        destination_ref: {**identity, "entity_ref": destination_ref, "category": "mixing_vessel",
                          "world_from_camera": np.eye(4).tolist(), "points_ref": points_ref},
    }
    grasp_ref = "candidate://source/grasp-1"
    grasp = {"candidate_ref": grasp_ref, "entity_ref": source_ref,
             "grasp_frame": {"frame_id": "front", "position_m": grasp_position},
             "approach_direction": {"frame_id": "front", "vector": [0., 1., 0.]},
             "grasp_geometry": {"width_m": .02, "height_m": .02, "depth_m": .02}}
    process_candidates = {}
    selected_refs = []
    for feature_ref, entity_ref, feature in source_features:
        process_candidates[feature_ref] = (entity_ref, len(process_candidates), feature)
        selected_refs.append(feature_ref)
    rim_ref = "process-feature://beaker/rim"
    rim = {"feature_kind": "rim", "feature_role": "opening", "tip_world": [0., 0., .8],
           "axis_world": [0., 0., 1.], "rim_radius_m": .03}
    process_candidates[rim_ref] = (destination_ref, len(process_candidates), rim)
    selected_refs.append(rim_ref)
    perception = SimpleNamespace(
        store=store,
        observations={identity["calibration_ref"]: records},
        grasps=SimpleNamespace(
            candidate_sets={"candidate-set://scene/source": {**identity, "candidate_set_ref": "candidate-set://scene/source",
                                                             "entities": {source_ref}, "candidate_refs": {grasp_ref}}},
            captures={identity["calibration_ref"]: {grasp_ref: grasp}},
        ),
        process_feature_sets={"process-feature-set://scene/current": {
            **identity, "candidate_set_ref": "process-feature-set://scene/current",
            "entity_refs": (source_ref, destination_ref), "candidates": process_candidates,
        }},
        _records=lambda _request: records,
    )
    request = {
        "operation": operation, "entity_refs": [source_ref, destination_ref],
        "grasp_candidate_set_ref": "candidate-set://scene/source",
        "process_feature_candidate_set_ref": "process-feature-set://scene/current",
        "selected_process_feature_refs": selected_refs, **identity,
    }
    return LabGraspTaskAffordanceProvider(perception), request, grasp_ref


def test_task_affordance_provider_qualifies_bottle_body_grasp_and_revalidates(tmp_path):
    theta = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    points = np.asarray([[.05 * np.cos(angle), .05 * np.sin(angle), z]
                         for z in np.linspace(.45, .95, 16) for angle in theta])
    bottle_rim = {"feature_kind": "rim", "feature_role": "pour_lip", "tip_world": [0., 0., 1.],
                  "axis_world": [0., 0., 1.], "pour_direction_world": [1., 0., 0.], "rim_radius_m": .02}
    provider, request, grasp_ref = _task_affordance_fixture(
        tmp_path, operation="pour", grasp_position=[.05, 0., .6833333333], source_category="reagent_bottle",
        source_points=points, source_features=[("process-feature://bottle/rim", "entity://source", bottle_rim)],
    )
    query = provider.propose(request)
    assert query["status"] == "available"
    assert len(query["candidates"]) == 1
    assert query["candidates"][0]["grasp_candidate_ref"] == grasp_ref
    prep_request = {key: request[key] for key in ("process_feature_candidate_set_ref", "observation_ref",
        "scene_revision", "frame_id", "calibration_ref")}
    prep_request.update(candidate_set_ref=query["candidate_set_ref"],
                        selected_combination_ref=query["candidates"][0]["combination_ref"])
    prepared = provider.validate_selection(prep_request)
    assert prepared["status"] == "available"
    assert prepared["selected"]["grasp_candidate_ref"] == grasp_ref
    stale = provider.validate_selection({**prep_request, "scene_revision": "new-scene"})
    assert stale["status"] == "stale"
    fabricated = provider.validate_selection({**prep_request, "selected_combination_ref": "grasp-affordance://fabricated"})
    assert fabricated["status"] == "stale"
    del provider.perception.process_feature_sets[request["process_feature_candidate_set_ref"]]
    missing_evidence = provider.validate_selection(prep_request)
    assert missing_evidence["status"] == "stale"


def test_task_affordance_provider_fails_closed_for_opening_grasp_and_ambiguous_rod_end(tmp_path):
    theta = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    bottle_points = np.asarray([[.05 * np.cos(angle), .05 * np.sin(angle), z]
                                for z in np.linspace(.45, .95, 16) for angle in theta])
    rim = {"feature_kind": "rim", "feature_role": "opening", "tip_world": [0., 0., 1.],
           "axis_world": [0., 0., 1.], "rim_radius_m": .02}
    provider, request, _ = _task_affordance_fixture(
        tmp_path / "bottle", operation="pour", grasp_position=[0., 0., .99],
        source_category="reagent_bottle", source_points=bottle_points,
        source_features=[("process-feature://bottle/rim", "entity://source", rim)],
    )
    assert provider.propose(request)["status"] == "unavailable"

    rod = np.asarray([[x, y, z] for x in np.linspace(0., .3, 80)
                      for y in (-.001, .001) for z in (-.001, .001)])
    endpoints = [
        ("process-feature://rod/a", "entity://source", {"feature_kind": "rod_endpoint_pair",
         "feature_role": "endpoint_a", "origin_world": [0., 0., 0.], "tip_world": [.3, 0., 0.]}),
        ("process-feature://rod/b", "entity://source", {"feature_kind": "rod_endpoint_pair",
         "feature_role": "endpoint_b", "origin_world": [.3, 0., 0.], "tip_world": [0., 0., 0.]}),
    ]
    rod_provider, rod_request, _ = _task_affordance_fixture(
        tmp_path / "rod", operation="stir", grasp_position=[.15, 0., 0.],
        source_category="stir_tool", source_points=rod, source_features=endpoints,
    )
    assert rod_provider.propose(rod_request)["status"] == "ambiguous"


def test_task_affordance_selects_rod_endpoint_opposite_the_shaft_grasp(tmp_path):
    rod = np.asarray([[x, y, z] for x in np.linspace(0., .3, 80)
                      for y in (-.001, .001) for z in (-.001, .001)])
    endpoints = [
        ("process-feature://rod/a", "entity://source", {"feature_kind": "rod_endpoint_pair",
         "feature_role": "endpoint_a", "origin_world": [0., 0., 0.], "tip_world": [.3, 0., 0.]}),
        ("process-feature://rod/b", "entity://source", {"feature_kind": "rod_endpoint_pair",
         "feature_role": "endpoint_b", "origin_world": [.3, 0., 0.], "tip_world": [0., 0., 0.]}),
    ]
    provider, request, _ = _task_affordance_fixture(
        tmp_path, operation="stir", grasp_position=[.09, 0., 0.], source_category="stir_tool",
        source_points=rod, source_features=endpoints,
    )
    result = provider.propose(request)
    assert result["status"] == "available"
    assert result["candidates"][0]["process_feature_refs"] == [
        "process-feature://rod/b", "process-feature://beaker/rim",
    ]


def test_simulator_truth_snapshot_passes_public_understanding_endpoint(tmp_path):
    store = LabArtifactStore(tmp_path)
    rgb_ref = 'artifact://labutopia/rgb/truth-endpoint.png'
    store.path(rgb_ref).parent.mkdir(parents=True)
    Image.new('RGB', (16, 16)).save(store.path(rgb_ref))
    depth_ref = store.write('depth', np.ones((16, 16), dtype=np.float32))
    cloud = np.zeros((16, 16, 3), dtype=np.float32)
    cloud[..., 2] = 1.0
    cloud[..., 0] = np.linspace(-.1, .1, 16)[None, :]
    cloud[..., 1] = np.linspace(-.1, .1, 16)[:, None]
    cloud_ref = store.write('point_cloud', cloud)
    state_ref = store.write('state', _truth_state())
    calibration_ref = store.write('calibration', {
        'scene_revision': 'scene', 'frame_id': 'front',
        'intrinsics': [[100., 0., 8.], [0., 100., 8.], [0., 0., 1.]],
        'camera_pose_world': {'position_m': [0, 0, 0], 'orientation_wxyz': [1, 0, 0, 0]},
    })
    request = {
        'observation_ref': 'observation://scene/front', 'scene_revision': 'scene',
        'frame_id': 'front', 'calibration_ref': calibration_ref, 'freshness_ms': 0,
        'max_age_ms': 1000, 'artifacts': [rgb_ref, depth_ref, cloud_ref, state_ref],
    }
    manifest = {'objects': {
        'R01': {'label': 'R01', 'category': 'reagent_bottle', 'prim_path': '/World/R01',
                'origin_world': [-.04, 0., 1.], 'tip_world': [-.04, 0., 1.1],
                'axis_world': [0., 0., 1.], 'size_m': [.1, .1, .2]},
        'BEAKER': {'label': 'BEAKER', 'category': 'mixing_vessel', 'prim_path': '/World/Beaker',
                   'origin_world': [.04, 0., 1.], 'tip_world': [.04, 0., 1.1],
                   'axis_world': [0., 0., 1.], 'size_m': [.2, .2, .2],
        },
    }}
    visual = LabVisualPerception(
        Mock(), LocalFilesystemArtifactResolver({'labutopia': tmp_path}), Mock(),
        segmentation=Mock(), geometry=Mock(), store=store, grasps=Mock(),
        provider_from_tcp=CONVENTION, truth_manifest=manifest,
    )

    response = SceneUnderstandingEndpoint(visual).invoke(request)

    assert response['status'] == 'available', json.dumps(response, ensure_ascii=False)
    assert {entity['label'] for entity in response['entities']} == {'R01', 'BEAKER'}
    assert all(entity['provenance'] == [depth_ref, cloud_ref] for entity in response['entities'])
    assert len(response['spatial_envelopes']) == 2
    assert all(envelope['provenance'] == [state_ref] for envelope in response['spatial_envelopes'])
    point_clouds = [item for item in response['derived_artifacts'] if item['kind'] == 'object_point_cloud']
    assert len(point_clouds) == 2
    for artifact in point_clouds:
        assert set(artifact['descriptor']) == {
            'width_px', 'height_px', 'bbox_xyxy_px', 'foreground_pixels', 'point_count',
            'unit', 'min_xyz_m', 'max_xyz_m', 'confidence',
        }
        assert artifact['provenance'] == [depth_ref, cloud_ref]

    partial_state = _truth_state()
    partial_state['objects'] = [item for item in partial_state['objects'] if item['label'] != 'R01']
    partial_state_ref = store.write('state', partial_state)
    partial_calibration_ref = store.write('calibration', {
        'scene_revision': 'scene', 'frame_id': 'front-partial',
        'intrinsics': [[100., 0., 8.], [0., 100., 8.], [0., 0., 1.]],
        'camera_pose_world': {'position_m': [0, 0, 0], 'orientation_wxyz': [1, 0, 0, 0]},
    })
    partial_request = {**request, 'frame_id': 'front-partial',
                       'observation_ref': 'observation://scene/front-partial',
                       'calibration_ref': partial_calibration_ref,
                       'artifacts': [rgb_ref, depth_ref, cloud_ref, partial_state_ref]}
    partial_response = SceneUnderstandingEndpoint(visual).invoke(partial_request)
    assert partial_response['status'] == 'available', json.dumps(partial_response, ensure_ascii=False)
    assert {entity['label'] for entity in partial_response['entities']} == {'R01', 'BEAKER'}
    assert [envelope['entity_ref'] for envelope in partial_response['spatial_envelopes']] == [
        'entity://simulator-truth-BEAKER'
    ]
    assert partial_response['ambiguities'][0]['code'] == 'simulator_truth_geometry_unavailable'
    assert partial_response['ambiguities'][0]['entity_refs'] == ['entity://simulator-truth-R01']


def _truth_state(*, schema='labutopia-simulator-world-bounds/v1',
                 source='final_composed_usd_world_bounds'):
    return {
        'schema': schema,
        'scene_revision': 'scene', 'unit': 'm',
        'source': source,
        'objects': [
            {'label': 'R01', 'category': 'reagent_bottle', 'prim_path': '/World/R01',
             'min_xyz_world_m': [-.1, -.1, .9], 'max_xyz_world_m': [-.02, .1, 1.1]},
            {'label': 'BEAKER', 'category': 'mixing_vessel', 'prim_path': '/World/Beaker',
             'min_xyz_world_m': [.02, -.1, .9], 'max_xyz_world_m': [.1, .1, 1.1]},
        ],
    }


def test_process_feature_selection_rejects_stale_or_cross_entity_refs_without_qualifying_geometry():
    visual = object.__new__(LabVisualPerception)
    identity = {
        'observation_ref': 'observation://scene/front', 'scene_revision': 'scene',
        'frame_id': 'front', 'calibration_ref': 'artifact://calibration/front',
    }
    visual.observations = {identity['calibration_ref']: {
        'entity://bottle': {**identity, 'category': 'reagent_bottle',
                            'process_feature_candidates': [{'feature_kind': 'rim'}, {'feature_kind': 'rim'}]},
        'entity://beaker': {**identity, 'category': 'mixing_vessel',
                            'process_feature_candidates': [{'feature_kind': 'rim'}]},
    }}
    visual.process_feature_sets = {
        'process-feature-set://current': {
            **identity, 'entity_refs': ('entity://bottle', 'entity://beaker'),
            'candidates': {
                'process-feature://bottle-rim-a': ('entity://bottle', 0, {'feature_kind': 'rim'}),
                'process-feature://bottle-rim-b': ('entity://bottle', 1, {'feature_kind': 'rim'}),
                'process-feature://beaker-rim': ('entity://beaker', 0, {'feature_kind': 'rim'}),
            },
        },
    }
    request = {
        **identity, 'operation': 'pour', 'entity_refs': ['entity://bottle', 'entity://beaker'],
        'candidate_set_ref': 'process-feature-set://current',
        'selected_feature_refs': [
            'process-feature://bottle-rim-a',
            'process-feature://beaker-rim',
        ],
    }
    result = visual.validate_selection(request)
    assert result['status'] == 'available'
    assert result['selected_feature_refs'] == request['selected_feature_refs']

    stale = visual.validate_selection({**request, 'selected_feature_refs': [
        'process-feature://fabricated', request['selected_feature_refs'][1],
    ]})
    assert stale['status'] == 'stale'

    ambiguous = visual.validate_selection({**request, 'selected_feature_refs': [
        'process-feature://bottle-rim-a',
        'process-feature://bottle-rim-b',
    ]})
    assert ambiguous['status'] == 'ambiguous'
