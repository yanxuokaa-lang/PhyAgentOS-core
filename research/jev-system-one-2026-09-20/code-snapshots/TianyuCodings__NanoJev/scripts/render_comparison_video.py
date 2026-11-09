#!/usr/bin/env python3
"""Render selected real three-system success cases to an HTML reader, MP4 and GIF.

No API/GPU calls. Supply actual trained/Jev/native artifacts explicitly. Chrome,
Playwright and FFmpeg must already be installed; output files are never replaced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from game_tasks import step as environment_step, valid_actions

FIXED_CASES = (
    ('test', 'navigation_v3:949e76c0d9a26606cb3373b6'),
    ('test', 'navigation_v3:450cb63d0bbd444de9ae877c'),
    ('ood', 'navigation_v3:06b38a6ade0754de661819ad'),
    ('ood', 'navigation_v3:53d0165e341321ab56b81c37'),
)
ROLES = ('trained', 'jev', 'base')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def validate_episode(episode):
    current = episode['initial_state']
    if current.get('game') != 'grid_navigation':
        raise ValueError('Video accepts actual grid-navigation states only')
    for transition in episode['steps']:
        if transition['state'] != current:
            raise ValueError('Discontinuous trajectory')
        action = transition['action']
        if action not in valid_actions(current):
            raise ValueError('Illegal executed action')
        probabilities = transition.get('probabilities')
        if probabilities is not None:
            if set(probabilities) != set(valid_actions(current)) or any(type(p) not in (int, float) or not 0 <= p <= 1 for p in probabilities.values()):
                raise ValueError('Malformed original candidate distribution')
        after = environment_step(current, action)
        if after != transition['next_state']:
            raise ValueError('Recorded transition differs from environment')
        current = after
    if episode.get('final_state', current) != current:
        raise ValueError('Final state differs from replay')
    if episode.get('success') is not None and episode['success'] != (current['position'] == current['goal']):
        raise ValueError('Success label differs from actual final state')
    return current


def reader_episode(episode):
    """Keep actual drawing fields; exclude raw provider/account/call metadata."""
    keys = ('id', 'game', 'split', 'initial_state', 'final_state', 'outcome', 'success', 'steps_count', 'max_steps')
    step_keys = ('state', 'action', 'next_state', 'probabilities', 'actor', 'controller', 'forced',
                 'model_forward', 'sample_uniform_draw', 'distribution_argmax')
    result = {key: episode[key] for key in keys if key in episode}
    result['steps'] = [{key: transition[key] for key in step_keys if key in transition} for transition in episode['steps']]
    return result


def assemble(paths):
    models, reference, sources = [], {}, []
    for role in ROLES:
        for filename in paths[role]:
            snapshot = Path(filename).read_bytes()
            source_sha = hashlib.sha256(snapshot).hexdigest()
            record = json.loads(snapshot)
            policy = record.get('policy')
            if policy not in ('greedy', 'sample'):
                raise ValueError(f'{filename}: policy must be greedy or sample')
            by_id = {e['id']: e for e in record['episodes']}
            if len(by_id) != len(record['episodes']):
                raise ValueError('Duplicate episode ID')
            selected = []
            for split, identity in FIXED_CASES:
                episode = by_id[identity]
                if episode['split'] != split:
                    raise ValueError('Selected case split changed')
                validate_episode(episode)
                if episode.get('success') is not (role != 'base'):
                    raise ValueError(f'{role}/{policy}: selected case has the wrong actual outcome')
                if role == 'base' and (episode.get('outcome') != 'horizon_exhausted'
                                      or len(episode['steps']) != episode['max_steps']):
                    raise ValueError('The complete unsuccessful baseline horizon must be preserved')
                if identity in reference and reference[identity] != episode['initial_state']:
                    raise ValueError('Systems do not share the same initial map/state')
                reference[identity] = episode['initial_state']
                selected.append(reader_episode(episode))
            if role == 'trained' and 'v3_teacher_coords_multi_seed17' not in (str(filename) + json.dumps(record.get('checkpoint', {}))):
                raise ValueError('Training arm must use the fixed v3_teacher_coords_multi_seed17 checkpoint')
            details = {'trained': '0.6B parallel decision model',
                       'jev': 'TypeSafe Jev · recorded API decisions',
                       'base': 'Qwen3-0.6B · no task fine-tuning'}
            names = {'trained': 'NanoJev', 'jev': 'Jev', 'base': 'Untuned Qwen'}
            models.append({'role': role, 'name': names[role], 'display_detail': details[role],
                           'policy': policy, 'checkpoint_sha256': record.get('checkpoint_sha256'),
                           'source_artifact': Path(filename).name, 'source_sha256': source_sha, 'episodes': selected})
            sources.append({'role': role, 'policy': policy, 'artifact': Path(filename).name, 'sha256': source_sha})
    policies = [p for p in ('greedy', 'sample') if any(m['policy'] == p for m in models)]
    for policy in policies:
        for role in ROLES:
            if sum(m['policy'] == policy and m['role'] == role for m in models) != 1:
                raise ValueError(f'Missing or duplicate {policy}/{role} artifact')
    cases = [{'id': identity, 'split': split, 'split_index': i % 2 + 1, 'initial_state': reference[identity]}
             for i, (split, identity) in enumerate(FIXED_CASES)]
    return {'schema_version': 'nanojev-three-system-reader-v1', 'policies': policies, 'cases': cases,
            'models': models, 'sources': sources,
            'protocol': {'selected_cases': 'Outcome-selected showcase: trained and Jev succeed, original Qwen fails in both policies; first two qualifying test and OOD maps in the frozen cohort order',
                         'expected_success': {'trained': True, 'jev': True, 'base': False},
                         'synchronization': 'environment step',
                         'trained_checkpoint': 'v3_teacher_coords_multi_seed17',
                         'baseline_distribution': 'Frozen original Qwen answer-label conditional probabilities; no project tuning',
                         'terminal_panels': 'Hold actual final state while other trajectories continue',
                         'no_synthetic_replacement_trajectories': True}}


def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'Command failed ({Path(command[0]).name}): {result.stderr[-3000:]}')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for role in ROLES:
        p.add_argument('--' + role, action='append', required=True, type=Path)
    p.add_argument('--web-root', type=Path, default=Path('web'))
    p.add_argument('--output-dir', type=Path, default=Path('assets'))
    p.add_argument('--data-output', type=Path, default=Path('web/comparison_results.json'))
    p.add_argument('--chrome', default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    p.add_argument('--playwright-module', help='Optional installed playwright/index.mjs absolute path')
    p.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    p.add_argument('--steps-per-second', type=float, default=4)
    p.add_argument('--assemble-only', action='store_true', help='Validate and save real reader data, without Chrome/encoding')
    args = p.parse_args()
    if not 0 < args.steps_per_second <= 12:
        p.error('Invalid playback rate')
    if args.data_output.exists():
        p.error('Data output already exists; use a new path')
    if not args.assemble_only and (not args.ffmpeg or not Path(args.ffmpeg).is_file()):
        p.error('An installed FFmpeg executable is required')
    data = assemble({role: getattr(args, role) for role in ROLES})
    outputs = [args.output_dir / f'comparison_{policy}.{suffix}' for policy in data['policies'] for suffix in ('mp4', 'gif', 'png')]
    audit_path = args.output_dir / 'comparison_media_manifest.json'
    if any(path.exists() for path in outputs + [audit_path]):
        p.error('Media output already exists; use a new output directory')
    json_write_new(args.data_output, data)
    if args.assemble_only:
        print(json.dumps({'reader_data': str(args.data_output), 'validated_cases': 4, 'policies': data['policies'], 'api_calls': 0})); return
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nanojev-video-') as temporary:
        temp = Path(temporary)
        command = ['node', str(Path(__file__).with_name('capture_comparison.mjs')), '--web-root', str(args.web_root.resolve()),
                   '--data', str(args.data_output.resolve()), '--output', str(temp), '--chrome', args.chrome,
                   '--steps-per-second', str(args.steps_per_second)]
        if args.playwright_module:
            command += ['--playwright-module', args.playwright_module]
        capture = run(command)
        print(capture.stdout, end='')
        audit = json.loads((temp / 'capture_check.json').read_text())
        manifest = {'schema_version': 'nanojev-three-system-media-v1', 'reader_data_sha256': sha(args.data_output),
                    'sources': data['sources'], 'capture': audit, 'media': {}, 'api_calls': 0, 'gpu_calls': 0,
                    'encoding': 'FFmpeg H.264/yuv420p; environment-step timing',
                    'gif_scope': 'Complete first selected case, including the full unsuccessful baseline horizon and final outcomes; 8 fps',
                    'poster_scope': 'Actual final frame of the first selected case',
                    'render_source_sha256': {str(path): sha(path) for path in [Path(__file__), Path(__file__).with_name('capture_comparison.mjs'), args.web_root/'comparison.html', args.web_root/'comparison.js', args.web_root/'comparison.css']}}
        for policy, captured in audit['policies'].items():
            folder = temp / policy
            concat = folder / 'frames.txt'
            lines = []
            for frame in captured['frames']:
                lines.extend([f"file '{frame['file']}'", f"duration {frame['duration_seconds']:.6f}"])
            lines.append(f"file '{captured['frames'][-1]['file']}'")
            concat.write_text('\n'.join(lines)+'\n')
            video, gif, poster = [args.output_dir / f'comparison_{policy}.{suffix}' for suffix in ('mp4','gif','png')]
            run([args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-n', '-f', 'concat', '-safe', '0', '-i', str(concat),
                 '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '24', '-pix_fmt', 'yuv420p', '-r', '12', '-movflags', '+faststart', str(video)])
            first_case = [frame for frame in captured['frames'] if frame['case_index'] == 0]
            gif_concat = folder / 'first_case.txt'
            gif_lines = []
            for frame in first_case:
                gif_lines.extend([f"file '{frame['file']}'", f"duration {frame['duration_seconds']:.6f}"])
            gif_lines.append(f"file '{first_case[-1]['file']}'")
            gif_concat.write_text('\n'.join(gif_lines)+'\n')
            run([args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-n', '-f', 'concat', '-safe', '0', '-i', str(gif_concat),
                 '-filter_complex', 'fps=8,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4', str(gif)])
            shutil.copyfile(folder / first_case[-1]['file'], poster)
            # Decode the actual exported MP4 all the way through, including its final frame.
            run([args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', str(video), '-f', 'null', '-'])
            manifest['media'][policy] = {suffix: {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)} for suffix, path in [('mp4',video),('gif',gif),('poster',poster)]}
            manifest['media'][policy].update(frame_count=captured['frame_count'], timeline_seconds=captured['duration_seconds'], final_frame_verified=True)
            manifest['media'][policy]['gif_case'] = {'id': first_case[0]['case_id'],
                'environment_steps': first_case[-1]['environment_step'], 'captured_frames': len(first_case),
                'timeline_seconds': sum(frame['duration_seconds'] for frame in first_case), 'includes_actual_final_outcomes': True}
        json_write_new(audit_path, manifest)
        print(json.dumps({'manifest':str(audit_path),'media':manifest['media'],'real_frames_verified':True,'api_calls':0},ensure_ascii=False))


if __name__ == '__main__':
    main()
