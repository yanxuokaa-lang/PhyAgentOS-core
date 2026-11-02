"""Replay a saved grasp request to measure sampling loss; no robot or admission.

Run in the configured GraspNet environment. Historical inputs remain diagnostics,
not fresh preparation. Outputs include unchanged native candidates before both
selection stages, so geometry qualification can be compared without re-inference.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--prediction', type=Path, required=True)
    parser.add_argument('--artifact-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.profile.read_text())
    request = json.loads(args.prediction.read_text())['request']
    worker_script = config['grasp_worker']['script'].replace('${LAB_CONFIG_DIR}', str(args.profile.resolve().parent))
    sys.path.insert(0, str(Path(worker_script).resolve().parent))
    import graspnet_worker as worker
    worker._OPTIONS = worker._parser().parse_args(config['grasp_worker']['arguments'])
    native, sampled, worker_requests = [], [], []
    original = worker._sample_candidates

    def capture(candidates, limit, policy):
        native.extend(candidates)
        return original(candidates, limit, policy)

    worker._sample_candidates = capture

    try:
        worker._load()
        for target in request['targets']:
            geometry = target['geometry_artifacts'][0]
            payload = {'schema_version': 'paos-grasp-worker/v1', 'provider': 'graspnet',
                       'request_id': target['entity_ref'], 'point_cloud_path': str(
                           args.artifact_root.resolve() / geometry['artifact_ref'].removeprefix('artifact://labutopia/')),
                       'max_candidates': config['grasp']['sample_count'],
                       'max_points': config['grasp']['point_budget'],
                       'score_threshold': config['grasp']['score_threshold'],
                       'apply_model_collision': config['grasp']['apply_model_collision']}
            worker_requests.append(payload)
            sampled.append(worker._handle(payload))
        result = {'status': 'complete', 'request': request, 'worker_requests': worker_requests,
                  'native_candidates': native, 'worker_outputs': sampled}
    except Exception as exc:
        result = {'status': 'failed', 'error_type': type(exc).__name__, 'error': str(exc)}
        raise
    finally:
        result.update(captured_at=datetime.now(timezone.utc).isoformat(),
                      evidence_kind='historical_grasp_sampling_diagnostic', motion_authorized=False,
                      profile=str(args.profile.resolve()), prediction=str(args.prediction.resolve()),
                      configuration=config, command=sys.argv,
                      worker_source=Path(worker_script).read_text(),
                      commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip())
        (args.output / 'sampling.json').write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps({'native': len(native), 'sampled': sum(len(r['candidates']) for r in sampled),
                      'output': str(args.output)}))


if __name__ == '__main__':
    main()
