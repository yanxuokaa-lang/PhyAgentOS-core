#!/usr/bin/env python3
"""Verify frozen NanoJev/Jev/native-Qwen trajectories and export minimal public data.

CPU only. Never invokes a model, reads credentials, or changes an evaluation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import datetime as dt
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path

from assemble_navigation_v3_views import render_view_request
from evaluate_navigation_v3 import (canonical_json, categorical, episode_rng,
                                    select_episodes, validate_distribution)
from game_tasks import solve, source_group_id, step, valid_actions
from summarize_navigation_v3 import aggregate, bootstrap_contrast, close
from summarize_pipeline_v2 import read_json, read_jsonl, sha


TRAINED_SHA = 'fff62d1412685c1714eaa386acb603f9690371fb3cc8ad03dc41319302597c28'
QWEN_REVISION = 'c1899de289a04d12100db370d81485cdf75e47ca'
COHORT_SHA = '1132e0791ccd2f07be1a470f4612dd0f5787fb49077212d7e91a730dab60b4da'
SYSTEMS = ('nanojev', 'jev', 'qwen')
POLICIES = ('greedy', 'sample')
LABELS = {'nanojev': 'NanoJev — trained decision head', 'jev': 'Jev — live API rounded proxy',
          'qwen': 'Qwen3-0.6B — original LM head, offered-letter conditional distribution'}


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def js_stringify(value):
    """JSON.stringify-compatible values/order for these parsed JSON API receipts."""
    if value is None:
        return 'null'
    if type(value) is bool:
        return 'true' if value else 'false'
    if type(value) is int:
        return str(value)
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError('Nonfinite value in API receipt')
        if value == 0:
            return '0'
        raw = repr(value)
        if 1e-6 <= abs(value) < 1e21:
            return format(Decimal(raw), 'f').rstrip('0').rstrip('.') if '.' in format(Decimal(raw), 'f') else format(Decimal(raw), 'f')
        mantissa, exponent = raw.lower().split('e')
        mantissa = mantissa.rstrip('0').rstrip('.') if '.' in mantissa else mantissa
        exponent = int(exponent)
        return mantissa + 'e' + ('+' if exponent >= 0 else '') + str(exponent)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    if isinstance(value, list):
        return '[' + ','.join(js_stringify(v) for v in value) + ']'
    if isinstance(value, dict):
        return '{' + ','.join(js_stringify(k) + ':' + js_stringify(v) for k, v in value.items()) + '}'
    raise ValueError('Unsupported value in a parsed API JSON receipt')


def js_digest(value):
    return hashlib.sha256(js_stringify(value).encode()).hexdigest()


def load_api_context(path):
    if path is None or not path.is_file():
        return None
    records = read_jsonl(path)
    starts, successes, failures = {}, {}, []
    for row in records:
        identifier = row['id']
        if not identifier.startswith('nanojev-live-'):
            raise ValueError('API receipt does not belong to the fresh NanoJev comparison namespace')
        if row['status'] == 'started':
            if identifier in starts:
                raise ValueError('Duplicate API start receipt')
            starts[identifier] = row
        elif row['status'] == 'succeeded':
            if identifier in successes or identifier not in starts:
                raise ValueError('Duplicate success or success without its recorded request start')
            if starts[identifier]['input_sha256'] != row['input_sha256'] or starts[identifier]['started_at'] != row['started_at']:
                raise ValueError('API success does not match its started request')
            if row['input_sha256'] != js_digest(row['input']) or row['response_sha256'] != js_digest({
                    'native_probs': row['native_probs'], 'rounding': row['rounding']}):
                raise ValueError('Fresh API input/response receipt hash is inconsistent')
            start = dt.datetime.fromisoformat(row['started_at'].replace('Z', '+00:00'))
            finish = dt.datetime.fromisoformat(row['finished_at'].replace('Z', '+00:00'))
            if finish < start:
                raise ValueError('API receipt finish precedes its start')
            successes[identifier] = row
        elif row['status'] == 'failed':
            if identifier not in starts:
                raise ValueError('API failure has no recorded start')
            failures.append(identifier)
        else:
            raise ValueError('Unknown API journal record status')
    fields = {'started': ['id', 'status', 'input_sha256', 'started_at'],
              'succeeded': ['id', 'status', 'input_sha256', 'input', 'model', 'native_probs', 'rounding',
                            'started_at', 'finished_at', 'response_sha256'],
              'failed': ['id', 'status', 'input_sha256', 'finished_at', 'unknown_cost']}
    clean_records = [{key: row[key] for key in fields[row['status']] if key in row} for row in records]
    return {'path': str(path), 'sha256': sha(path), 'successes': successes, 'starts': starts,
            'failed_ids': failures, 'embedded_by_id': {}, 'public_records': clean_records}


def embedded_api_context(paths):
    """Check published receipt integrity without claiming private journal access."""
    successes, sources = {}, {}
    for path in paths:
        if not path.is_file():
            continue
        source = read_json(path)
        sources[path.name] = sha(path)
        for receipt in source.get('api_calls', []):
            identifier = receipt['id']
            if not identifier.startswith('nanojev-live-'):
                raise ValueError('Unexpected API receipt namespace in the published comparison')
            if receipt['input_sha256'] != js_digest(receipt['input']) or receipt['response_sha256'] != js_digest({
                    'native_probs': receipt['native_probs'], 'rounding': receipt['rounding']}):
                raise ValueError('Published embedded API input/response hash mismatch')
            start = dt.datetime.fromisoformat(receipt['started_at'].replace('Z', '+00:00'))
            finish = dt.datetime.fromisoformat(receipt['finished_at'].replace('Z', '+00:00'))
            if finish < start:
                raise ValueError('Published receipt has inconsistent timestamps')
            if identifier in successes and receipt != successes[identifier]:
                raise ValueError('The same API call ID has different embedded receipts across controllers')
            successes[identifier] = receipt
    return {'successes': successes, 'embedded_by_id': {}, 'sources': sources,
            'mode': 'published_embedded_receipts_only', 'private_journal_checked': False}


def check_qwen_answer(answer, public):
    from evaluate_native_qwen_navigation import build_prompt
    prompt, labels = build_prompt(public)
    if answer.get('prompt_sha256') != hashlib.sha256(prompt.encode()).hexdigest():
        raise ValueError('Qwen prompt differs from the fixed complete-state/options formatter')
    ids = sorted(public['questions']['action']['criteria'])
    mapping = answer['candidate_to_token']
    if set(mapping) != set(ids) or any(mapping[a]['text'] != labels[a] or type(mapping[a]['id']) is not int for a in ids):
        raise ValueError('Qwen A-D mapping differs from lexicographic offered candidates')
    if len({mapping[a]['id'] for a in ids}) != len(ids):
        raise ValueError('Native vocabulary option token IDs are not unique')
    logits = answer['native_option_logits']
    if set(logits) != set(ids) or any(type(v) not in {float, int} or not math.isfinite(v) for v in logits.values()):
        raise ValueError('Missing or invalid native option logits')
    maximum = max(logits.values())
    exp = {a: math.exp(logits[a] - maximum) for a in ids}
    z = math.fsum(exp.values())
    if max(abs(exp[a] / z - answer['probabilities'][a]) for a in ids) > 1e-6:
        raise ValueError('Native option probabilities do not equal T=1 softmax of offered logits')
    unconditional = answer['native_option_unconditional_probs']
    if set(unconditional) != set(ids) or any(type(v) not in {float, int} or not math.isfinite(v) or not 0 <= v <= 1 for v in unconditional.values()):
        raise ValueError('Invalid recorded unconditional vocabulary probabilities')
    mass = math.fsum(unconditional.values())
    close(answer['offered_token_mass'], mass, 'native offered-token mass')
    if not 0 < mass <= 1 + 1e-6:
        raise ValueError('Offered native tokens have zero or invalid total vocabulary mass')
    if max(abs(unconditional[a] / mass - answer['probabilities'][a]) for a in ids) > 1e-5:
        raise ValueError('Recorded unconditional and conditional native probabilities disagree')
    return {'native_option_logits': logits, 'native_option_unconditional_probs': unconditional,
            'candidate_to_token': mapping, 'offered_token_mass': mass,
            'probability_semantics': 'conditional on an offered A-D next token'}


def check_jev_answer(answer, public, api_context):
    """Live API receipt adapter; rejects unproven old-label playback by default."""
    if api_context is None:
        raise ValueError('Live Jev measurements require their fresh-run API provenance ledger')
    identifier = answer['source_api_call_id']
    if identifier not in api_context['successes'] or identifier not in api_context['embedded_by_id']:
        raise ValueError('Jev action cannot be traced to this comparison ledger and its embedded successful call')
    receipt = api_context['successes'][identifier]
    expected_input = {'model': 'typesafe-ai/jev', 'state': public['state'], 'questions': public['questions']}
    if receipt['input'] != expected_input or receipt['input_sha256'] != js_digest(expected_input) or answer['source_input_sha256'] != receipt['input_sha256']:
        raise ValueError('Jev source call is for a different state/question/candidate input')
    native = answer['native_probabilities']
    ids = sorted(public['questions']['action']['criteria'])
    if native != receipt['native_probs']['action'] or set(native) != set(ids) or any(
            type(v) not in {float, int} or not math.isfinite(v) or not 0 <= v <= 1 for v in native.values()):
        raise ValueError('Jev native rounded values differ from the complete fresh response')
    total = math.fsum(native.values())
    recorded_sum = answer['native_sum']
    close(recorded_sum, total, 'native rounded vector sum')
    if total <= 0:
        raise ValueError('All-zero rounded Jev vector cannot define an action controller')
    material_correction = abs(recorded_sum - 1) > 1e-12
    if answer['normalization_applied'] != material_correction or type(answer['cache_hit']) is not bool:
        raise ValueError('Jev normalization/cache annotation is inconsistent')
    if max(abs(native[a] / recorded_sum - answer['probabilities'][a]) for a in ids) > 1e-12:
        raise ValueError('Jev sampling distribution is not its explicitly normalized rounded proxy')
    return {'native_probabilities': native, 'native_sum': recorded_sum,
            'native_nonunit_sum': material_correction, 'native_sum_differs_exactly': recorded_sum != 1.0,
            'normalization_applied': material_correction, 'source_api_call_id': identifier,
            'source_input_sha256': receipt['input_sha256'], 'source_response_sha256': receipt['response_sha256'],
            'cache_hit': answer['cache_hit'], 'probability_semantics': 'normalized rounded Jev proxy; latent full precision is unavailable'}


def verify_result(path, system, policy, expected, cohort, train_groups, api_context=None):
    if not path.is_file():
        return {'status': 'missing', 'path': str(path)}, None, None
    report = read_json(path)
    if report.get('policy') != policy or report.get('seed') != 20260917 or report.get('validation_only') is not False:
        raise ValueError(f'{path}: wrong controller, seed or validation-only fixture')
    reported_cohort = report.get('cohort', {})
    if reported_cohort.get('initial_states_sha256') != COHORT_SHA or any(
            reported_cohort.get(k) != v for k, v in cohort.items() if k != 'data_sha256'):
        raise ValueError(f'{path}: cohort identity, order or initial states changed')
    if report['protocol'].get('temperature') != 1.0 or report['protocol'].get('horizon') != '2*size^2':
        raise ValueError(f'{path}: temperature or horizon was changed')
    sources = Path(__file__).parent
    source_hash_gaps = []
    if report.get('renderer_sha256') != sha(sources / 'assemble_navigation_v3_views.py'):
        raise ValueError(f'{path}: input geometry renderer source changed')
    if 'base_renderer_sha256' not in report and system == 'jev':
        source_hash_gaps.append('base_renderer_sha256')
    elif report.get('base_renderer_sha256') != sha(sources / 'build_navigation_v3.py'):
        raise ValueError(f'{path}: base geometry renderer source changed')
    if system == 'nanojev':
        if report.get('student_measurement') is not True or report.get('checkpoint_sha256') != TRAINED_SHA:
            raise ValueError('NanoJev must use the frozen trained checkpoint')
        if report.get('script_sha256') != sha(sources / 'evaluate_navigation_v3.py'):
            raise ValueError('NanoJev controller source mismatch')
    elif system == 'qwen':
        provenance = report['model_provenance']
        if report.get('student_measurement') is not False or report.get('native_model_measurement') is not True or provenance.get('model') != 'Qwen/Qwen3-0.6B' or provenance.get('revision') != QWEN_REVISION or provenance.get('model_training_steps_in_this_project') != 0:
            raise ValueError('Qwen baseline is not the declared original pretrained native model')
        if report.get('script_sha256') != sha(sources / 'evaluate_native_qwen_navigation.py') or report.get('controller_script_sha256') != sha(sources / 'evaluate_navigation_v3.py'):
            raise ValueError('Native Qwen/controller source mismatch')
    else:
        if report.get('student_measurement') is not False or report['execution'].get('engine') != 'jev_live_api':
            raise ValueError('Jev measurement does not declare a real external API backend')
        for key, source in [('script_sha256', 'evaluate_live_jev_navigation.py'),
                            ('controller_script_sha256', 'rollout_jev_navigation.py'),
                            ('worker_script_sha256', 'jev_navigation_worker.mjs')]:
            if key not in report and key != 'script_sha256':
                source_hash_gaps.append(key)
            elif report.get(key) != sha(sources / source):
                raise ValueError('Jev API/controller source hash mismatch')
        if api_context is None:
            raise ValueError('Fresh Jev API ledger is required, not historical teacher labels')
        embedded = {}
        for row in report['api_calls']:
            if row['id'] in embedded or row['id'] not in api_context['successes']:
                raise ValueError('Embedded Jev call is duplicated or absent from the fresh API journal')
            actual = api_context['successes'][row['id']]
            if any(actual.get(key) != value for key, value in row.items()):
                raise ValueError('Embedded Jev call disagrees with its original fresh-run receipt')
            embedded[row['id']] = row
        api_context = {**api_context, 'embedded_by_id': embedded}
    expected_by_id = {e['id']: e for e in expected}
    ids = [e['id'] for e in report['episodes']]
    if len(ids) != len(set(ids)) or set(ids) != set(expected_by_id):
        raise ValueError(f'{path}: episodes are missing, duplicated, or substituted')
    groups = {s: {} for s in ('test', 'ood')}
    public_episodes = []
    query_ids, query_answers, counters = [], {}, Counter()
    for episode in report['episodes']:
        initial = expected_by_id[episode['id']]
        if any(episode[k] != v for k, v in initial.items()):
            raise ValueError('Episode initial environment does not match the frozen source')
        state = episode['initial_state']
        split, group = episode['split'], episode['source_map_group_id']
        if group in train_groups:
            raise ValueError('Held-out environment overlaps the training source map')
        rng, seed_hash = episode_rng(20260917, group, state)
        if episode['rng_seed_sha256'] != seed_hash or episode['max_steps'] != 2 * state['size'] ** 2:
            raise ValueError('Per-episode sampling seed or horizon differs')
        distance = solve(state)['distance']
        visits = Counter({tuple(state['position']): 1})
        n_forced = revisits = n_decisions = optimal_count = 0
        optimal_mass = 0.0
        clean_steps = []
        for turn, transition in enumerate(episode['steps']):
            if transition['state'] != state or state['position'] == state['goal']:
                raise ValueError('Trajectory skips an environment state or continues after the goal')
            actions = sorted(valid_actions(state))
            forced = len(actions) == 1
            actor = 'forced_legal_action' if forced else {'nanojev': 'student', 'jev': 'jev_api', 'qwen': 'native_lm'}[system]
            if transition['actor'] != actor or transition['forced'] != forced:
                raise ValueError('Actual action actor/forced classification is incorrect')
            p = transition['probabilities']
            total = validate_distribution(p, actions)
            details = {}
            if forced:
                selected, draw = actions[0], None
                n_forced += 1
            else:
                public = {'id': f"{episode['id']}::step{turn}", **render_view_request(state, split=split,
                           representation='coords', candidate_order=actions)}
                if transition['request_id'] != public['id'] or transition['public_request_sha256'] != digest(public):
                    raise ValueError('Recorded model input differs from the frozen geometry-only request')
                answer = transition['answers']['action']
                if answer['probabilities'] != p:
                    raise ValueError('Executed probability vector differs from the actual model response')
                if system == 'qwen':
                    details = check_qwen_answer(answer, public)
                elif system == 'jev':
                    details = check_jev_answer(answer, public, api_context)
                    counters['native_nonunit_sum_decisions'] += details['native_nonunit_sum']
                    counters['exact_nonunit_sum_decisions'] += details['native_sum_differs_exactly']
                    counters['normalization_correction_decisions'] += details['normalization_applied']
                    counters['cache_hit_decisions'] += details['cache_hit']
                else:
                    details = {'probability_semantics': 'trained dynamic-candidate action distribution'}
                if policy == 'sample':
                    selected, draw, _ = categorical(p, rng)
                else:
                    selected, draw = max(actions, key=p.__getitem__), None
                query_ids.append(public['id'])
                query_answers[public['id']] = answer
                n_decisions += 1
            if transition['action'] != selected or transition['sample_uniform_draw'] != draw or p[selected] <= 0:
                raise ValueError('Actual action is not the declared greedy/categorical choice or lacks support')
            close(transition['selected_action_probability'], p[selected] / total, 'chosen action probability')
            if transition['distribution_argmax'] != max(actions, key=p.__getitem__):
                raise ValueError('Distribution argmax is incorrect; it must remain distinct from sampled action')
            after = step(state, selected)
            if transition['next_state'] != after or source_group_id(after) != group:
                raise ValueError('Recorded environment transition or map identity is incorrect')
            optimal = solve(state)['optimal_actions']
            p_optimal = math.fsum(p[a] for a in optimal) / total
            close(transition['p_optimal'], p_optimal, 'optimal action probability mass')
            actual_optimal = selected in optimal
            if transition['optimal_action'] != actual_optimal:
                raise ValueError('Actual optimal-action annotation is incorrect')
            repeated = visits[tuple(after['position'])] > 0
            if transition['revisited_position'] != repeated:
                raise ValueError('Repeated-visit annotation is incorrect')
            revisits += repeated
            visits[tuple(after['position'])] += 1
            if not forced:
                optimal_mass += p_optimal
                optimal_count += actual_optimal
            clean_steps.append({'state': state, 'action': selected, 'next_state': after, 'actor': actor,
                                'controller': policy, 'forced': forced, 'probabilities': p,
                                'sample_uniform_draw': draw, 'selected_action_probability': p[selected] / total,
                                'distribution_argmax': max(actions, key=p.__getitem__), 'p_optimal': p_optimal,
                                'optimal_action': actual_optimal, 'revisited_position': repeated,
                                'probability_details': details})
            state = after
        n = len(clean_steps)
        success = state['position'] == state['goal']
        if n == 0 or n > episode['max_steps'] or (not success and n != episode['max_steps']):
            raise ValueError('Failure was truncated, episode omitted, or horizon exceeded')
        if episode['final_state'] != state or episode['success'] != success or episode['steps_count'] != n:
            raise ValueError('Reported final state/outcome/step count is incorrect')
        efficiency = distance / n if success else 0.0
        close(episode['path_efficiency'], efficiency, 'path efficiency')
        close(episode['repeated_visit_rate'], revisits / n, 'episode revisit rate')
        if episode['forced_decisions'] != n_forced or episode['model_decisions'] != n_decisions:
            raise ValueError('Model and forced decision counts are inconsistent')
        groups[split][group] = {'completion_rate': [int(success), 1], 'mean_path_efficiency': [efficiency, 1],
                               'mean_steps': [n, 1], 'step_weighted_repeated_visit_rate': [revisits, n],
                               'mean_p_optimal': [optimal_mass, n_decisions], 'actual_optimal_action_rate': [optimal_count, n_decisions]}
        public_episodes.append({**initial, 'final_state': state, 'steps': clean_steps, 'steps_count': n,
                                'max_steps': episode['max_steps'], 'success': success, 'path_efficiency': efficiency,
                                'forced_decisions': n_forced, 'model_decisions': n_decisions})
    batch_ids = [q for b in report.get('batches', []) for q in b['state_ids']]
    if len(batch_ids) != len(set(batch_ids)) or sorted(batch_ids) != sorted(query_ids):
        raise ValueError('Active-state batch/request mapping is not complete and one-to-one')
    for batch in report['batches']:
        execution = batch['execution']
        if system == 'jev':
            if execution.get('forward_passes') is not None or execution.get('engine') != 'jev_live_api' or type(execution.get('network_model_calls')) is not int:
                raise ValueError('Jev API calls are being reported as local/internal model forwards')
            cache_hits = sum(query_answers[q]['cache_hit'] for q in batch['state_ids'])
            if execution.get('cache_hits') != cache_hits or execution['network_model_calls'] != len(batch['state_ids']) - cache_hits:
                raise ValueError('Jev HTTP request/cache-hit accounting disagrees with actual decisions')
        elif execution.get('forward_passes') != 1 or execution.get('network_model_calls') != 0 or execution.get('autoregressive_decode_steps') != 0:
            raise ValueError('Local model backend does not use exactly one non-generative batched forward')
    if system == 'jev':
        calls = sum(batch['execution']['network_model_calls'] for batch in report['batches'])
        if report['execution'].get('forward_passes') is not None or report['execution'].get('teacher_calls') != calls:
            raise ValueError('Jev total external request count/internal-forward boundary mismatch')
        counters['network_api_requests_this_controller'] = calls
        counters['embedded_successful_api_calls_cumulative'] = len(api_context['embedded_by_id'])
    elif report['execution'].get('forward_passes') != len(report['batches']):
        raise ValueError('Total local batched forwards disagree with their retained batches')
    metrics = {split: aggregate(bucket) for split, bucket in groups.items()}
    for split, measured in metrics.items():
        for name, value in measured.items():
            close(report['summary'][split][name], value, f'{system}/{policy}/{split}/{name}')
    verified = {'status': 'complete', 'path': str(path), 'source_sha256': sha(path), 'system': system,
                'controller': policy, 'episodes': len(public_episodes), 'summary': metrics,
                'counts': dict(counters), 'all_transitions_inputs_probabilities_sampling_draws_verified': True,
                'source_hash_fields_not_recorded_at_run': source_hash_gaps,
                'input_file_sha256': reported_cohort['data_sha256']}
    if source_hash_gaps:
        verified['posthoc_dependency_source_hashes'] = {filename: sha(sources / filename) for filename in
                    ['build_navigation_v3.py', 'rollout_jev_navigation.py', 'jev_navigation_worker.mjs']}
        verified['source_provenance_limit'] = 'Dependency hashes were not recorded in the original API run; these are post-hoc source audit hashes. Every actual rendered request and API receipt is verified independently.'
    cleaned = {'status': 'complete', 'controller': policy, 'summary': metrics, 'episodes': public_episodes,
               'source_sha256': sha(path), 'counts': dict(counters)}
    return verified, cleaned, groups


def result_markdown(audit):
    lines = ['# NanoJev、Jev 与原始 Qwen：冻结闭环对照', '',
             '**' + ('240 局真实轨迹与概率来源核验通过。' if audit['complete'] else '结果尚未齐全，缺失项未填估计值。') + '**', '',
             '每个系统都在相同的 20 张 test 地图和 20 张 OOD 地图上运行 greedy 与 T=1 采样。NanoJev 固定使用 训练后的模型 `v3_teacher_coords_multi_seed17`；原 V3 主 gold 模型及结果保持不变。本表的“原始 Qwen”是未经本项目微调的预训练 Qwen3-0.6B，通过原生 LM head 对所提供 A–D 选项取条件概率；并非随机模型。', '',
             '| 系统 | 控制器 | test 完成率 | OOD 完成率 | test 路径效率 | OOD 路径效率 |',
             '|---|---|---:|---:|---:|---:|']
    for system in SYSTEMS:
        for policy in POLICIES:
            result = audit['results'][system + '/' + policy]
            if result['status'] != 'complete':
                lines.append(f'| {system} | {policy} | 缺失 | 缺失 | 缺失 | 缺失 |')
                continue
            s = result['summary']
            lines.append(f"| {system} | {policy} | {s['test']['completion_rate']:.0%} | {s['ood']['completion_rate']:.0%} | {s['test']['mean_path_efficiency']:.4f} | {s['ood']['mean_path_efficiency']:.4f} |")
    lines += ['', '路径效率在成功时为最短距离／实际步数，失败为 0；完成率与效率分别评价。所有失败保留到固定 horizon；单合法动作无需模型并另计。完整步数、重复访问率、最优动作质量和实际动作见配套 JSON。', '']
    if audit['complete']:
        n = audit['results']['nanojev/sample']['summary']
        j = audit['results']['jev/sample']['summary']
        q = audit['results']['qwen/sample']['summary']
        lines += [f"在这批地图上，NanoJev 采样完成率为 test {n['test']['completion_rate']:.0%}、OOD {n['ood']['completion_rate']:.0%}；Jev 为 {j['test']['completion_rate']:.0%}／{j['ood']['completion_rate']:.0%}，原始 Qwen 选项接口为 {q['test']['completion_rate']:.0%}／{q['ood']['completion_rate']:.0%}。NanoJev 相对所测原始 Qwen 接口有明显的任务收益，但尚未达到 Jev 在这里的效率；这组小型导航任务也不足以证明一般能力相当。", '']
    lines += ['NanoJev 使用训练后的动态候选决策头；Qwen 使用原生词表头及完整选项提示；Jev 的内部实现不可见。它们同时存在结构、输入接口和训练差异，因此这是三种固定系统的对照，不能称为纯训练因素的因果实验。未为原始 Qwen 搜索最佳提示，也未按新对照结果挑选视频样例。', '',
              '## 概率与调用来源', '',
              'NanoJev 柱图表示动态候选动作分布；Qwen 柱图是“下一 token 属于所提供 A–D 之一”条件下的分布，完整词表中这些 token 的总质量另存；Jev 柱图是 native rounded 数值除以其总和得到的代理分布。它们都不是通关概率。Jev 原样 rounded 数值和原始和保留，未声称恢复服务端未舍入概率。', '']
    ledger = audit.get('live_api_ledger')
    if ledger:
        lines += [f"本次日志有 {ledger['started_calls']} 次请求开始、{ledger['successful_calls']} 次成功、{len(ledger['failed_ids'])} 次失败。每一步 Jev 决策均关联本次成功请求或该请求的 exact-input 缓存；状态、全部问题／候选、请求 hash、响应 hash 与原始日志逐项匹配，没有读取旧训练教师标签。", '']
        for policy in POLICIES:
            c = audit['results']['jev/' + policy].get('counts')
            if c:
                lines += [f"- {policy}：{c['network_api_requests_this_controller']} 次新 API 请求、{c['cache_hit_decisions']} 次缓存命中；动作向量原始和与 1 的偏差大于 1e-12 的决策引用为 {c['native_nonunit_sum_decisions']} 次，仅按浮点精确相等判断不等于 1 的引用为 {c['exact_nonunit_sum_decisions']} 次。"]
        lines += ['', '以上舍入统计只针对用于动作选择的 action 向量，计数单位是决策引用，缓存可重复引用同一个响应。API 内部 forward／解码次数记为未知；没有把并发 HTTP 请求伪称一次多状态原生 forward。', '']
    lines += ['来源核验依靠本次执行脚本、工具调用及 started／succeeded 日志链；本地文件本身无法独立证明外部服务执行。Jev 原运行记录未保存 base renderer／controller／worker 三项依赖 hash，核验 JSON 明确列出这一缺口，并把当前源码 hash 标为事后审读值；未改写历史轨迹或重跑 API。', '',
              '## 视频与统计边界', '',
              '固定展示 cohort 中 test 前两例和 OOD 前两例，greedy／采样均包含。每列按环境步同步，到终点后停住；这不是推理延迟竞赛。实际 API 延迟、缓存和 GPU 批处理方式不同，不能用影片播放速度比较服务延迟。', '',
              '只有一个训练 checkpoint 和一个采样 seed。配套核验 JSON 给出 500 次源地图配对 bootstrap；区间反映固定系统／固定 RNG 下的地图采样不确定性，不包含训练或 RNG 方差。三方使用同一新 V3 cohort，不能与旧 V2 的不同地图直接作胜负比较。', '',
              '[完整协议](nanojev_comparison_protocol_zh.md) · [公共轨迹与概率](nanojev_comparison_public.json) · [核验与配对区间](nanojev_comparison_verification.json) · [最小 API 来源记录](nanojev_comparison_api_receipts.jsonl)', '',
              '公开 API 来源记录只包含自写游戏请求、原生概率／舍入说明、时间和 hash；不含密钥、headers、账户／项目标识、供应商 envelope 或逐调用费用。保留完整原生概率对象是为了复核原响应 hash。', '']
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data-dir', type=Path, default=Path('research/private_navigation_v3'))
    ap.add_argument('--results-dir', type=Path, default=Path('research'))
    ap.add_argument('--api-ledger', type=Path, default=Path('research/private_nanojev_live_api/calls.jsonl'))
    ap.add_argument('--output', type=Path)
    ap.add_argument('--public-output', type=Path, default=Path('research/nanojev_comparison_public.json'))
    ap.add_argument('--report-output', type=Path, default=Path('research/nanojev_comparison_zh.md'))
    ap.add_argument('--api-receipts-output', type=Path, default=Path('research/nanojev_comparison_api_receipts.jsonl'))
    ap.add_argument('--cohort', type=Path, default=Path('research/nanojev_comparison_cohort.json'))
    ap.add_argument('--public-only', action='store_true', help='Verify published trajectories/embedded receipts without reading private data or the API journal; use a separate output.')
    ap.add_argument('--allow-incomplete', action='store_true')
    ap.add_argument('--bootstrap-samples', type=int, default=500)
    args = ap.parse_args()
    if args.bootstrap_samples < 0:
        ap.error('--bootstrap-samples must be nonnegative')
    if args.output is None:
        args.output = Path('research/nanojev_comparison_public_check.json' if args.public_only else 'research/nanojev_comparison_verification.json')
    if args.public_only:
        protected = [Path('research/nanojev_comparison_verification.json'), args.public_output,
                     args.report_output, args.api_receipts_output, args.cohort]
        if args.output.resolve() in {p.resolve() for p in protected}:
            ap.error('--public-only output must not overwrite the complete private-source audit or published source artifacts')
        published_cohort = read_json(args.cohort)
        expected, cohort, train = published_cohort['episodes'], published_cohort['cohort'], set()
        if len(expected) != 40 or digest(expected) != COHORT_SHA or len({e['id'] for e in expected}) != 40 or len({e['source_map_group_id'] for e in expected}) != 40:
            raise ValueError('Published 40-map cohort identity/hash changed')
        if Counter(e['split'] for e in expected) != {'test': 20, 'ood': 20}:
            raise ValueError('Published cohort does not contain 20 episodes per split')
        for episode in expected:
            state = episode['initial_state']
            solution = solve(state)
            if source_group_id(state) != episode['source_map_group_id'] or not solution['reachable'] or solution['terminal']:
                raise ValueError('Published initial environment is not the declared reachable nonterminal map')
    else:
        expected, train, cohort = select_episodes(args.data_dir, per_split=20)
    if cohort['initial_states_sha256'] != COHORT_SHA:
        raise ValueError('The frozen V3 40-map cohort has changed')
    video_ids = [e['id'] for split in ('test', 'ood') for e in [r for r in expected if r['split'] == split][:2]]
    names = {'nanojev': 'navigation_v3_v3_teacher_coords_multi_seed17_{policy}.json',
             'qwen': 'navigation_v3_native_qwen_{policy}.json', 'jev': 'navigation_v3_jev_api_{policy}.json'}
    if args.public_only:
        manifest = published_cohort['source_results_sha256']
        expected_names = {template.format(policy=p) for template in names.values() for p in POLICIES}
        if set(manifest) != expected_names:
            raise ValueError('Published source manifest does not cover exactly the six frozen results')
        for filename, expected_sha in manifest.items():
            source_path = args.results_dir / filename
            if source_path.is_file() and sha(source_path) != expected_sha:
                raise ValueError(f'Published result SHA differs from the frozen manifest: {filename}')
    api_context = (embedded_api_context([args.results_dir / names['jev'].format(policy=p) for p in POLICIES])
                   if args.public_only else load_api_context(args.api_ledger))
    audit = {'schema_version': 'nanojev-comparison-verification-v1', 'complete': False,
             'cohort_sha256': COHORT_SHA, 'video_episode_ids': video_ids,
             'checkpoint_sha256': TRAINED_SHA, 'results': {}, 'missing': [], 'paired_source_map_ci': {}}
    audit['verification_scope'] = {
        'mode': 'public_only' if args.public_only else 'private_sources_available',
        'published_initial_states_environment_probabilities_controllers_and_metrics': True,
        'embedded_api_receipt_integrity': True,
        'source_result_hashes_match_published_frozen_manifest': args.public_only,
        'private_api_started_succeeded_journal': not args.public_only and api_context is not None,
        'training_source_map_overlap_rechecked': not args.public_only,
        'cohort_selection_from_original_split_files_rechecked': not args.public_only,
        'independent_proof_of_remote_api_execution': False,
        'model_weights_reexecuted': False,
        'interpretation': 'complete means all checks in this declared scope passed; public-only does not reproduce private provenance or training-data isolation checks.'}
    public = {'schema_version': 'nanojev-comparison-public-v1', 'complete': False,
              'cohort_sha256': COHORT_SHA, 'seed': 20260917, 'temperature': 1.0,
              'video_episode_ids': video_ids, 'systems': {},
              'playback': 'synchronized environment steps, not latency race; completed panels remain at goal',
              'probability_note': 'NanoJev action distribution / Qwen offered-letter conditional distribution / Jev normalized rounded proxy'}
    if args.public_only:
        audit['public_cohort_sha256'] = sha(args.cohort)
        audit['public_api_receipts'] = {'mode': 'embedded source receipts', 'source_files': api_context['sources'],
                                        'unique_embedded_call_ids': len(api_context['successes']),
                                        'private_started_succeeded_journal_checked': False}
    elif api_context is not None:
        audit['live_api_ledger'] = {key: api_context[key] for key in ['path', 'sha256', 'failed_ids']}
        audit['live_api_ledger'].update(successful_calls=len(api_context['successes']), started_calls=len(api_context['starts']),
                                       limitation='Receipt consistency and this run source chain are verified; file fields alone are not independent proof of external execution.')
    groups = {}
    for system in SYSTEMS:
        public['systems'][system] = {'label': LABELS[system], 'controllers': {}}
        for policy in POLICIES:
            key = system + '/' + policy
            path = args.results_dir / names[system].format(policy=policy)
            verified, cleaned, grouped = verify_result(path, system, policy, expected, cohort, train, api_context)
            audit['results'][key] = verified
            if cleaned is None:
                audit['missing'].append(str(path))
                public['systems'][system]['controllers'][policy] = {'status': 'missing'}
            else:
                public['systems'][system]['controllers'][policy] = cleaned
                groups[key] = grouped
    for policy in POLICIES:
        for left, right in [('nanojev', 'qwen'), ('nanojev', 'jev')]:
            a, b = left + '/' + policy, right + '/' + policy
            if a in groups and b in groups:
                audit['paired_source_map_ci'][f'{a}_minus_{b}'] = {split: bootstrap_contrast(
                    {a: groups[a][split], b: groups[b][split]}, {a: 1, b: -1}, args.bootstrap_samples) for split in ('test', 'ood')}
    audit['complete'] = public['complete'] = not audit['missing']
    if args.public_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        print(json.dumps({'complete': audit['complete'], 'scope': 'public-only', 'missing_files': len(audit['missing']),
                          'output': str(args.output), 'private_source_checks_performed': False}, ensure_ascii=False))
        if not audit['complete'] and not args.allow_incomplete:
            raise SystemExit(2)
        return
    args.cohort.parent.mkdir(parents=True, exist_ok=True)
    args.cohort.write_text(json.dumps({'schema_version': 'nanojev-public-comparison-cohort-v1',
                         'episodes': expected, 'cohort': cohort,
                         'source_results_sha256': {Path(row['path']).name: row['source_sha256']
                             for row in audit['results'].values() if row['status'] == 'complete'},
                         'scope': 'Frozen self-authored initial environments only; no teacher training examples or training-map membership evidence.'},
                         ensure_ascii=False, indent=2) + '\n')
    if api_context is not None:
        args.api_receipts_output.parent.mkdir(parents=True, exist_ok=True)
        args.api_receipts_output.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n' for row in api_context['public_records']))
        public['api_receipts'] = {'file': args.api_receipts_output.name, 'sha256': sha(args.api_receipts_output),
                                  'successful_calls': len(api_context['successes']), 'raw_provider_envelope_included': False}
        audit['public_api_receipts'] = public['api_receipts']
    for path, value in [(args.output, audit), (args.public_output, public)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(result_markdown(audit) + '\n')
    print(json.dumps({'complete': audit['complete'], 'missing_files': len(audit['missing']),
                      'verification': str(args.output), 'public': str(args.public_output)}, ensure_ascii=False))
    if not audit['complete'] and not args.allow_incomplete:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
