"""Exercise camera/replayed observations through geometry and grasp Query ports."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PhyAgentOS.forge.capability_runtime.grasp_proposal import GraspProposalEndpoint
from PhyAgentOS.forge.capability_runtime.understanding import SceneUnderstandingEndpoint
from pick_place_workflow.perception_binding import grasp_geometry_artifacts

from .engine import IsaacSimLabEngine
from .perception_runtime import build_visual_providers
from .profile import LabUtopiaProfile
from .visual_perception import LabArtifactStore, RGBLabelPointInference


class RecordedSegmentation:
    """Replay recorded masks by their image proposal, without model claims."""
    def __init__(self, source, records):
        self.source, self.records = source, records

    def segment(self, request):
        matches = [r for r in self.records if tuple(r['claim']['bbox_xyxy']) == tuple(request.proposal.bbox_xyxy_px)]
        if len(matches) != 1:
            raise ValueError('recorded segmentation proposal is ambiguous or missing')
        path = self.source / f"replay-mask-{matches[0]['index']}.npy"
        return SimpleNamespace(mask=np.load(path, allow_pickle=False))

    def release(self):
        return None

    def shutdown(self):
        return None


class RecordedInference:
    def __init__(self, records):
        self.records = records

    def infer(self, image):
        return {'objects': [dict(r['claim']) for r in self.records],
                'ambiguities': ['Replayed VLM claims retain the original unreadable labels and category errors.']}


def replay_capture(source, artifact_root):
    report = json.loads((source / 'perception.json').read_text(encoding='utf-8'))
    capture = report['capture']
    if capture.get('status') != 'available':
        raise ValueError('recorded capture is unavailable')
    view = capture.get('views', [capture])[0]
    original = LabArtifactStore(source / 'artifacts/labutopia')
    destination = LabArtifactStore(artifact_root)
    for ref in [view['calibration_ref'], *[item['ref'] for item in view['artifacts']]]:
        path = destination.path(ref)
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original.path(ref), path)
    records = json.loads((source / 'segmentation-replay.json').read_text(encoding='utf-8'))
    return capture, RecordedInference(records), RecordedSegmentation(source, records)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--config', type=Path, default=Path.home()/'.PhyAgentOS/config.json')
    parser.add_argument('--perception-config', type=Path)
    parser.add_argument('--sensor-ref', default='sensor://tabletop_third_person')
    parser.add_argument('--replay', type=Path, help='Recorded probe workspace with segmentation-replay.json')
    parser.add_argument('--geometry-method', choices=('remake', 'dfnet'))
    args = parser.parse_args(argv)
    args.workspace = args.workspace.resolve()
    args.workspace.mkdir(parents=True, exist_ok=False)
    artifact_root = args.workspace/'artifacts/labutopia'
    visual, engine, client = None, None, None
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'profile': str(args.profile.resolve()),
              'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              'working_tree': subprocess.check_output(['git', 'status', '--porcelain'], text=True).splitlines(),
              'geometry_method': args.geometry_method, 'scope': 'perception and grasp query; no motion or Agent acceptance',
              'status': 'running', 'stage': 'configuration'}
    def save():
        (args.workspace/'perception.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    try:
        profile = LabUtopiaProfile.from_json(args.profile)
        segmentation = None
        if args.replay:
            source = args.replay.resolve()
            raw, inference, segmentation = replay_capture(source, artifact_root)
            report.update(replay_source=str(source), input_mode='recorded RGB-D, VLM claims and SAM2 masks; fresh geometry/GraspNet inference')
        else:
            import httpx
            from openai import OpenAI
            from PhyAgentOS.config.loader import load_config
            config = load_config(args.config)
            model = config.agents.defaults.model
            key = config.get_provider(model).resolve_api_key(base_dir=args.config.parent)
            client = OpenAI(api_key=key, base_url=config.get_api_base(model),
                            http_client=httpx.Client(trust_env=False, timeout=180))
            inference = RGBLabelPointInference(client, model=model)
            report.update(model=model, input_mode='fresh camera, VLM, segmentation, geometry and GraspNet')
            engine = IsaacSimLabEngine(profile, observation_artifact_root=artifact_root)
            report['stage'] = 'capture'
            save()
            raw = engine.observe({'sensor_refs': [args.sensor_ref]})
        visual, grasp = build_visual_providers(args.perception_config or profile.perception_config_path,
            engine, artifact_root, inference, segmentation=segmentation, geometry_method=args.geometry_method)
        report['capture'] = raw
        report['stage'] = 'understanding'
        save()
        if raw.get('status') != 'available':
            raise ValueError(f'capture failed: {raw.get("failure_code")}')
        view = raw.get('views', [raw])[0]
        identity = {'scene_revision': view['scene_revision'], 'frame_id': view['frame_id'],
                    'observation_ref': f"observation://{view['scene_revision']}/{view['frame_id']}",
                    'calibration_ref': view['calibration_ref'], 'freshness_ms': 0, 'max_age_ms': 1000}
        # In replay mode freshness is relative to the recorded capture, never a
        # claim that a historical view describes the live simulator now.
        understood = SceneUnderstandingEndpoint(visual).invoke({**identity, 'artifacts': [x['ref'] for x in view['artifacts']]})
        report['understanding'] = understood
        save()
        if understood.get('status') != 'available':
            raise ValueError(f'understanding failed: {understood.get("error")}')
        targets, metrics = [], []
        for entity in understood['entities']:
            geometry = grasp_geometry_artifacts(understood, entity['entity_ref'])
            if not geometry:
                continue
            points = np.load(visual.store.path(geometry[0]['artifact_ref']), allow_pickle=False)
            metrics.append({'entity_ref': entity['entity_ref'], 'category': entity['category'],
                'label': entity.get('label'), 'point_count': len(points), 'min_camera_m': points.min(0).tolist(),
                'max_camera_m': points.max(0).tolist(), 'depth_quantiles_m': np.quantile(points[:, 2], [.05, .5, .95]).tolist()})
            if entity['category'] in {'mixing_vessel', 'test_tube'}:
                continue
            target = {**{k: entity[k] for k in ('entity_ref', 'category', 'confidence')}, 'geometry_artifacts': geometry}
            envelope = next((e for e in understood['spatial_envelopes'] if e['entity_ref'] == entity['entity_ref']), None)
            if envelope:
                target['spatial_envelope'] = {k: v for k, v in envelope.items() if k != 'entity_ref'}
            targets.append(target)
        report.update(cloud_metrics=metrics, stage='grasp', process_preparation='unavailable: geometry/feature qualification remains unverified')
        save()
        if not targets:
            raise ValueError('no source has usable recovered geometry')
        report['grasp'] = GraspProposalEndpoint(grasp).invoke({**identity, 'targets': targets})
        if report['grasp'].get('status') != 'available' or not report['grasp']['candidates']:
            raise ValueError(f'grasp prediction failed: {report["grasp"].get("error")}')
        report.update(status='available', stage='queries_complete')
    except Exception as exc:
        report.update(status='failed', error=str(exc), error_type=type(exc).__name__)
    finally:
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        save()
        for resource in (visual, engine, client):
            if resource is not None:
                try:
                    resource.close()
                except Exception as exc:
                    report.setdefault('cleanup_errors', []).append(f'{type(exc).__name__}: {exc}')
        save()
    print(json.dumps({k: report[k] for k in ('status', 'stage', 'scope')}, ensure_ascii=False))
    return 0 if report['status'] == 'available' else 1


if __name__ == '__main__':
    raise SystemExit(main())
