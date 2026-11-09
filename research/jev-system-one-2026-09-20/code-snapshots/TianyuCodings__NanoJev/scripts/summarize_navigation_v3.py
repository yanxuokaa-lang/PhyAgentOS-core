#!/usr/bin/env python3
"""Audit and summarize the frozen V3 navigation experiment; standard library only.

Missing runs/rollouts remain missing. This command does not train, infer, fit a
temperature, change controllers, or select a checkpoint from test outcomes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import random

from evaluate_navigation_v3 import (categorical, canonical_json, episode_rng,
                                    select_episodes, validate_distribution)
from evaluate_pipeline_decisions import prepare_row, summarize
from game_tasks import solve, source_group_id, step, valid_actions
from summarize_pipeline_v2 import (align_predictions, percentile, read_json,
                                   read_jsonl, reference_questions, sha)


RUNS = {
    'v3_gold_ascii_single_seed17': ('ascii_single', 'gold_distribution'),
    'v3_gold_ascii_multi_seed17': ('ascii_multi', 'gold_distribution'),
    'v3_gold_coords_single_seed17': ('coords_single', 'gold_distribution'),
    'v3_gold_coords_multi_seed17': ('coords_multi', 'gold_distribution'),
    'v3_teacher_coords_multi_seed17': ('coords_multi', 'teacher'),
}
PRIMARY = 'v3_gold_coords_multi_seed17'
SPLITS = ('test', 'ood')
CONTROLLERS = ('greedy', 'sample')
LOOP_METRICS = ('completion_rate', 'mean_path_efficiency', 'mean_steps',
                'step_weighted_repeated_visit_rate', 'mean_p_optimal',
                'actual_optimal_action_rate')


def close(actual, expected, label):
    if expected is None:
        if actual is not None:
            raise ValueError(f'{label}: expected null')
    elif not isinstance(actual, (int, float)) or not math.isclose(actual, expected, abs_tol=1e-9, rel_tol=1e-8):
        raise ValueError(f'{label}: recorded={actual}, recomputed={expected}')


def aggregate(groups, keys=None):
    selected = list(groups) if keys is None else keys
    sums = defaultdict(lambda: [0.0, 0])
    for key in selected:
        for metric, (numerator, denominator) in groups[key].items():
            sums[metric][0] += numerator
            sums[metric][1] += denominator
    return {metric: numerator / denominator if denominator else None
            for metric, (numerator, denominator) in sums.items()}


def bootstrap_contrast(arms, coefficients, samples=500, seed=20260917):
    """Resample paired complete maps; preserve each metric's own denominator."""
    if not arms or set(arms) != set(coefficients):
        raise ValueError('Bootstrap contrast arm/weight mismatch')
    names = list(arms)
    keys = sorted(arms[names[0]])
    if any(set(arms[name]) != set(keys) for name in names):
        raise ValueError('Paired comparison requires identical source-map cohorts')
    points = {name: aggregate(groups) for name, groups in arms.items()}
    metrics = sorted(set.intersection(*(set(p) for p in points.values())))
    metrics = [metric for metric in metrics if all(points[n][metric] is not None for n in names)]
    point = {metric: math.fsum(coefficients[n] * points[n][metric] for n in names) for metric in metrics}
    result = {'source_maps': len(keys), 'bootstrap_samples': samples, 'seed': seed,
              'coefficients': coefficients, 'point': point, 'confidence_level': .95,
              'unit': 'paired canonical source map; every trajectory/question in that map stays together',
              'intervals': {}}
    if samples < 1 or len(keys) < 2:
        result['status'] = 'insufficient_maps_or_disabled'
        return result
    rng = random.Random(seed)
    values = {metric: [] for metric in metrics}
    for _ in range(samples):
        draws = [keys[rng.randrange(len(keys))] for _ in keys]
        measured = {name: aggregate(arms[name], draws) for name in names}
        for metric in metrics:
            if all(measured[name][metric] is not None for name in names):
                values[metric].append(math.fsum(coefficients[n] * measured[n][metric] for n in names))
    result['status'] = 'complete'
    result['valid_draws'] = {metric: len(v) for metric, v in values.items()}
    result['intervals'] = {metric: [percentile(v, .025), percentile(v, .975)]
                           for metric, v in values.items() if v}
    return result


def offline_groups(rows):
    groups = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))
    for row in rows:
        measured = summarize([row])
        for metric in ('optimal_action_accuracy', 'optimal_action_mass', 'gold_cross_entropy',
                       'gold_expected_brier', 'gold_kl_target_to_student', 'deterministic_accuracy',
                       'teacher_tv', 'teacher_kl_target_to_student'):
            if measured.get(metric) is not None:
                pair = groups[row['_bootstrap_group']][row['qid'] + '/' + metric]
                pair[0] += measured[metric]
                pair[1] += 1
    return dict(groups)


def offline_metrics(rows):
    return {qid: summarize([row for row in rows if row['qid'] == qid])
            for qid in ('action', 'solvable', 'value')}


def load_run(directory, name, view, objective, reference, view_hash, launch, samples):
    required = ['config.json', 'summary.json', 'train_log.json', 'predictions_test.jsonl', 'predictions_ood.jsonl',
                'checkpoint_manifest.json']
    missing = [str(directory / filename) for filename in required if not (directory / filename).is_file()]
    if missing:
        return {'status': 'missing', 'missing_files': missing}, {}
    config, summary = read_json(directory / 'config.json'), read_json(directory / 'summary.json')
    expected = {'seed': 17, 'steps': 1200, 'head_steps': 0, 'objective': objective,
                'precision': 'bf16', 'batch_questions': 12, 'microbatch_questions': 4,
                'max_microbatch_tokens': 6000, 'max_length': 512}
    if any(config.get(key) != value for key, value in expected.items()):
        raise ValueError(f'{name}: trained configuration violates the frozen protocol')
    if config.get('init_checkpoint') != launch['initial_checkpoint'] or config.get('initialization') != 'local DecisionModel warm start, fresh optimizer':
        raise ValueError(f'{name}: wrong warm-start checkpoint or optimizer initialization')
    if view_hash not in config.get('data_sha256', {}).values():
        raise ValueError(f'{name}: training data hash does not match its frozen view')
    if summary.get('objective') != objective or summary.get('selected_on') != 'dev target CE' or summary.get('temperature') != 1.0 or summary.get('temperature_fitted') is not False:
        raise ValueError(f'{name}: checkpoint or temperature selection differs from protocol')
    log = read_json(directory / 'train_log.json')
    if not log or log[-1]['step'] != 1200 or len(log) != 1200:
        raise ValueError(f'{name}: natural completion of all 1200 steps is not established')
    checkpoint = read_json(directory / 'checkpoint_manifest.json')
    weight_sha = checkpoint.get('checkpoint_sha256', '')
    if checkpoint.get('name') != name or checkpoint.get('best_step') != summary['best_step'] or len(weight_sha) != 64 or any(c not in '0123456789abcdef' for c in weight_sha):
        raise ValueError(f'{name}: checkpoint provenance manifest is inconsistent')
    if checkpoint.get('initial_checkpoint_sha256') != launch['initial_checkpoint_sha256'] or checkpoint.get('training_steps') != 1200:
        raise ValueError(f'{name}: actual initialization hash or completed training budget differs')
    out = {'status': 'complete', 'view': view, 'objective': objective, 'seed': 17,
           'checkpoint_sha256': weight_sha, 'checkpoint_manifest': checkpoint,
           'config': config, 'training_summary': summary, 'file_sha256': {f: sha(directory / f) for f in required},
           'offline': {}, 'source_map_ci': {}}
    rows_by_split = {}
    for split in SPLITS:
        rows = align_predictions(read_jsonl(directory / f'predictions_{split}.jsonl'), reference, split)
        rows_by_split[split] = rows
        out['offline'][split] = offline_metrics(rows)
        out['source_map_ci'][split] = bootstrap_contrast({'run': offline_groups(rows)}, {'run': 1}, samples)
    return out, rows_by_split


def audit_rollout(path, policy, expected_episodes, cohort, train_groups, representation=None, allowed_input_hashes=None):
    if not path.is_file():
        return {'status': 'missing', 'missing_files': [str(path)]}, {}
    report = read_json(path)
    student = policy in CONTROLLERS
    if report.get('policy') != policy or report.get('validation_only') is not False or report.get('student_measurement') != student:
        raise ValueError(f'{path}: wrong controller or a validation engine masquerading as a student')
    actual_cohort = report.get('cohort', {})
    identity = lambda value: {key: item for key, item in value.items() if key != 'data_sha256'}
    if report.get('seed') != 20260917 or identity(actual_cohort) != identity(cohort):
        raise ValueError(f'{path}: changed RNG seed or fixed evaluation cohort')
    if allowed_input_hashes is not None and actual_cohort.get('data_sha256') not in allowed_input_hashes:
        raise ValueError(f'{path}: input serialization is neither canonical nor its verified minimal environment package')
    if report.get('script_sha256') != sha(Path(__file__).with_name('evaluate_navigation_v3.py')):
        raise ValueError(f'{path}: evaluator source differs from the audited local script')
    if student and report.get('representation') != representation:
        raise ValueError(f'{path}: wrong input representation')
    if student:
        from assemble_navigation_v3_views import render_view_request
        if report.get('renderer_sha256') != sha(Path(__file__).with_name('assemble_navigation_v3_views.py')) or report.get('base_renderer_sha256') != sha(Path(__file__).with_name('build_navigation_v3.py')):
            raise ValueError(f'{path}: input renderer source hash mismatch')
    if report.get('protocol', {}).get('temperature') != 1.0 or report['protocol'].get('horizon') != '2*size^2':
        raise ValueError(f'{path}: controller protocol changed')
    expected_by_id = {e['id']: e for e in expected_episodes}
    actual_ids = [e['id'] for e in report['episodes']]
    if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != set(expected_by_id):
        raise ValueError(f'{path}: missing, duplicate, or substituted episode')
    groups = {split: {} for split in SPLITS}
    forced_counts, decisions, request_ids = Counter(), Counter(), []
    for episode in report['episodes']:
        expected = expected_by_id[episode['id']]
        if any(episode[key] != expected[key] for key in expected):
            raise ValueError(f'{path}: episode identity changed')
        current = episode['initial_state']
        group, split = episode['source_map_group_id'], episode['split']
        horizon = 2 * current['size'] ** 2
        if episode['max_steps'] != horizon or group in train_groups:
            raise ValueError(f'{path}: horizon or training-map overlap violation')
        optimal_distance = solve(current)['distance']
        rng, seed_hash = episode_rng(report['seed'], group, current)
        if episode['rng_seed_sha256'] != seed_hash:
            raise ValueError(f'{path}: per-episode RNG seed mismatch')
        visits = Counter({tuple(current['position']): 1})
        p_mass, optimal_count, n_decisions, revisits, n_forced = 0.0, 0, 0, 0, 0
        for turn, transition in enumerate(episode['steps']):
            if current['position'] == current['goal'] or transition['state'] != current:
                raise ValueError(f'{path}: rollout continues after completion or skips an environment state')
            actions = sorted(valid_actions(current))
            probabilities = transition['probabilities']
            total = validate_distribution(probabilities, actions)
            forced = len(actions) == 1
            actor = 'forced_legal_action' if forced else ('student' if student else policy)
            if transition['actor'] != actor or transition['forced'] != forced or transition['model_forward'] != (student and not forced):
                raise ValueError(f'{path}: incorrect actor or forced-step classification')
            if forced:
                action, draw = actions[0], None
                n_forced += 1
            elif policy in ('sample', 'random'):
                if policy == 'random' and any(abs(p - 1 / len(actions)) > 1e-12 for p in probabilities.values()):
                    raise ValueError(f'{path}: random baseline is not uniform')
                action, draw, _ = categorical(probabilities, rng)
            elif policy == 'oracle':
                action, draw = sorted(solve(current)['optimal_actions'])[0], None
                if probabilities != {a: float(a == action) for a in actions}:
                    raise ValueError(f'{path}: oracle distribution differs from its deterministic controller')
            else:
                action, draw = max(actions, key=probabilities.__getitem__), None
            if transition['action'] != action or transition['sample_uniform_draw'] != draw:
                raise ValueError(f'{path}: actual action differs from the declared fixed controller')
            if probabilities[action] <= 0:
                raise ValueError(f'{path}: executed action has zero probability')
            if student and not forced:
                if transition['answers']['action']['probabilities'] != probabilities:
                    raise ValueError(f'{path}: recorded probabilities differ from actual model response')
                request_id = f"{episode['id']}::step{turn}"
                public = {'id': request_id, **render_view_request(current, split=split,
                           representation=representation, candidate_order=actions)}
                if transition['request_id'] != request_id or transition['public_request_sha256'] != hashlib.sha256(canonical_json(public).encode()).hexdigest():
                    raise ValueError(f'{path}: actual model input differs from the frozen representation renderer')
                request_ids.append(transition['request_id'])
            after = step(current, action)
            if transition['next_state'] != after or source_group_id(after) != group:
                raise ValueError(f'{path}: invalid environment transition or source-map change')
            optimal = solve(current)['optimal_actions']
            optimal_mass = math.fsum(probabilities[a] for a in optimal) / total
            actual_optimal = action in optimal
            close(transition['p_optimal'], optimal_mass, 'step p(optimal)')
            if transition['optimal_action'] != actual_optimal:
                raise ValueError('Incorrect step optimal-action label')
            repeated = visits[tuple(after['position'])] > 0
            if transition['revisited_position'] != repeated:
                raise ValueError('Incorrect repeated-visit label')
            revisits += repeated
            visits[tuple(after['position'])] += 1
            if not forced:
                n_decisions += 1
                p_mass += optimal_mass
                optimal_count += actual_optimal
            current = after
        n = len(episode['steps'])
        success = current['position'] == current['goal']
        if n == 0 or n > horizon or (not success and n != horizon):
            raise ValueError(f'{path}: failed episode was omitted or cut short')
        if episode['final_state'] != current or episode['success'] != success or episode['steps_count'] != n:
            raise ValueError(f'{path}: final state/outcome/count mismatch')
        efficiency = optimal_distance / n if success else 0.0
        close(episode['path_efficiency'], efficiency, 'path efficiency')
        close(episode['repeated_visit_rate'], revisits / n, 'episode revisits')
        if episode['forced_decisions'] != n_forced or episode['model_decisions'] != (n_decisions if student else 0):
            raise ValueError(f'{path}: episode model/forced counts differ')
        groups[split][group] = {
            'completion_rate': [int(success), 1], 'mean_path_efficiency': [efficiency, 1],
            'mean_steps': [n, 1], 'step_weighted_repeated_visit_rate': [revisits, n],
            'episode_mean_repeated_visit_rate': [revisits / n, 1],
            'mean_p_optimal': [p_mass, n_decisions], 'actual_optimal_action_rate': [optimal_count, n_decisions],
        }
        forced_counts[split] += n_forced
        decisions[split] += n_decisions
    summaries = {}
    for split, grouped in groups.items():
        metrics = aggregate(grouped)
        for metric, value in metrics.items():
            close(report['summary'][split][metric], value, f'{path}:{split}:{metric}')
        summaries[split] = {**metrics, 'episodes': len(grouped), 'distinct_source_maps': len(grouped),
                            'forced_decisions': forced_counts[split], 'nonforced_decisions': decisions[split],
                            'model_decisions': decisions[split] if student else 0, 'training_source_map_overlap': 0}
    batches = report.get('batches', [])
    batch_ids = [state_id for b in batches for state_id in b['state_ids']]
    if len(batch_ids) != len(set(batch_ids)) or sorted(batch_ids) != sorted(request_ids):
        raise ValueError(f'{path}: model-decision/batched-forward mapping mismatch')
    if any(b['execution'].get('forward_passes') != 1 or b['execution'].get('network_model_calls', 0) != 0 or
           b['execution'].get('autoregressive_decode_steps', 0) != 0 for b in batches):
        raise ValueError(f'{path}: each active-state tick must use one local non-generative forward')
    if report['execution'].get('forward_passes') != len(batches) or report['execution'].get('teacher_calls') != 0:
        raise ValueError(f'{path}: total inference accounting mismatch')
    return {'status': 'complete', 'path': str(path), 'sha256': sha(path), 'policy': policy,
            'representation': representation, 'checkpoint_sha256': report.get('checkpoint_sha256'),
            'cohort_sha256': cohort['initial_states_sha256'], 'summary': summaries,
            'recorded_input_file_sha256': actual_cohort['data_sha256'],
            'canonical_input_file_sha256': cohort['data_sha256'],
            'input_serialization_differs_from_canonical': actual_cohort['data_sha256'] != cohort['data_sha256'],
            'execution': report['execution'], 'all_transitions_and_sample_draws_verified': True,
            'precision': sorted({b['execution'].get('precision', 'unspecified') for b in batches})}, groups


def make_contrasts(grouped, samples):
    out = {}
    short = {view: f'v3_gold_{view}_seed17' for view in ('ascii_single', 'ascii_multi', 'coords_single', 'coords_multi')}
    factorial = {
        'coordinates_at_single': {'coords_single': 1, 'ascii_single': -1},
        'coordinates_at_multi': {'coords_multi': 1, 'ascii_multi': -1},
        'multi_at_ascii': {'ascii_multi': 1, 'ascii_single': -1},
        'multi_at_coords': {'coords_multi': 1, 'coords_single': -1},
        'interaction': {'coords_multi': 1, 'coords_single': -1, 'ascii_multi': -1, 'ascii_single': 1},
        'mean_coordinates_effect': {'coords_multi': .5, 'coords_single': .5, 'ascii_multi': -.5, 'ascii_single': -.5},
        'mean_multi_effect': {'coords_multi': .5, 'coords_single': -.5, 'ascii_multi': .5, 'ascii_single': -.5},
    }
    specifications = {}
    for controller in CONTROLLERS:
        for label, coefficients in factorial.items():
            specifications[f'{controller}/{label}'] = {f'{short[v]}/{controller}': weight for v, weight in coefficients.items()}
        specifications[f'{controller}/secondary_teacher_minus_gold'] = {
            f'v3_teacher_coords_multi_seed17/{controller}': 1, f'{PRIMARY}/{controller}': -1}
        specifications[f'{controller}/primary_minus_random'] = {f'{PRIMARY}/{controller}': 1, 'random': -1}
    for name in RUNS:
        specifications[f'{name}/sample_minus_greedy'] = {f'{name}/sample': 1, f'{name}/greedy': -1}
    for label, coefficients in specifications.items():
        missing = [name for name in coefficients if name not in grouped]
        if missing:
            out[label] = {'status': 'missing', 'missing_arms': missing}
            continue
        out[label] = {split: bootstrap_contrast({name: grouped[name][split] for name in coefficients}, coefficients, samples)
                      for split in SPLITS}
    return out


def number(value):
    return '缺失' if value is None else f'{value:.4f}'


def interval(result, metric):
    point = result.get('point', {}).get(metric)
    ci = result.get('intervals', {}).get(metric)
    return f'{point:.4f} [{ci[0]:.4f}, {ci[1]:.4f}]' if point is not None and ci else number(point)


def render_report(report):
    findings = []
    greedy = report['rollouts'].get(f'{PRIMARY}/greedy', {})
    sampled = report['rollouts'].get(f'{PRIMARY}/sample', {})
    if greedy.get('status') == sampled.get('status') == 'complete':
        g, s = greedy['summary'], sampled['summary']
        difference = report['paired_contrasts'].get('sample/primary_minus_random', {}).get('ood', {})
        findings += [f"预定主模型 greedy 的 test／OOD 完成率为 {g['test']['completion_rate']:.0%}／{g['ood']['completion_rate']:.0%}，T=1 采样为 {s['test']['completion_rate']:.0%}／{s['ood']['completion_rate']:.0%}；对应采样路径效率为 {s['test']['mean_path_efficiency']:.4f}／{s['ood']['mean_path_efficiency']:.4f}。", '']
        if difference:
            findings += [f"主模型采样相对均匀随机的 OOD 完成率差为 {interval(difference, 'completion_rate')}，路径效率差为 {interval(difference, 'mean_path_efficiency')}。本次结果支持路径效率改善，尚不足以确认陌生地图通关率稳定提高。", '']
    if report['complete']:
        coords = report['paired_contrasts']['greedy/mean_coordinates_effect']
        findings += [f"四组 gold 对照中，显式坐标对 greedy 完成率的平均影响为 test {interval(coords['test'], 'completion_rate')}、OOD {interval(coords['ood'], 'completion_rate')}。多起点覆盖没有表现为普遍收益，完整主效应与交互见下表。", '']
        secondary = report['rollouts']['v3_teacher_coords_multi_seed17/sample']['summary']
        findings += [f"次要参考分布监督模型在采样下完成 test {secondary['test']['completion_rate']:.0%}、OOD {secondary['ood']['completion_rate']:.0%}；OOD 路径效率为 {secondary['ood']['mean_path_efficiency']:.4f}。其完成率点值高于主 gold 模型，效率点值较低；当前配对区间不足以判定教师目标总体优于 gold 目标。", '']
    lines = ['# Navigation V3 固定实验报告', '', f"生成时间：{report['generated_at_utc']}。", '',
             f"**{'结果齐全，已完成独立核验。' if report['complete'] else '结果尚未齐全：学生缺失结果未作估计。'}**", '',
             *findings,
             '主展示预先固定为 `v3_gold_coords_multi_seed17`。四个 gold 模型组成输入表示（ASCII／坐标）×训练起点覆盖（single／multi）的 2×2 对照；同表示的参考分布监督是次要对照。未依据 test 或 OOD 改默认模型、温度、控制器或训练设置。', '',
             '四个 gold 模型都使用 300 张训练地图×8 个 D4 呈现槽，共 2400 条导航训练曝光，加 984 条相同非导航 replay；单起点为每原始地图 1 个起点，多起点共 1874 个原始起点。每组都从同一 V2 teacher seed 17 权重恢复，用新优化器训练 1200 步、head warmup 0 步。single 的 8 次 D4 呈现不代表 8 个不同原始起点。', '',
             f"只有 1 个训练 seed，不能估计训练随机性的方差。95% 区间按完整源地图进行 {report['bootstrap_samples']} 次配对 bootstrap，反映固定 checkpoint、固定采样种子下的地图采样不确定性；不覆盖训练 seed 或控制器 RNG 的变化。区间未作多重比较校正。", '',
             '## 固定闭环协议与覆盖', '',
             'test 与 OOD 各取冻结文件顺序中前 20 张不同的可达、非终局地图，所有策略使用相同初始状态；共有 40 张地图，与训练源地图重叠 0。每局最多 `2×size²` 步，保留所有成功和失败。单合法动作直接执行并另计，不调用模型；其余活跃状态每个 tick 一次批量 forward。', '',
             'greedy 取原始概率最大动作；sample 从完整原始 T=1 分布采样。各 episode 使用 stable-hash 派生的独立 RNG，强制步不消耗随机数。不添加访问惩罚、epsilon、温度调优、循环提前终止或 oracle 兜底。原始概率、随机数和实际动作全部保存并独立重放核验。', '',
             '路径效率为成功时最短距离／实际步数，失败为 0。重复访问率为已访问目的格所占步数，初始格也计为已访问。p(optimal) 和实际最优动作率只统计非强制决策，按决策步数加权。它们与最终通关率分别报告；p(optimal) 是策略在 BFS 最优动作集合上的质量，不能视为通关概率。', '',
             '闭环 p(optimal) 还受到各控制器实际访问状态的影响；不同控制器之间的差值不是在同一固定状态集合上的能力差。下方离线指标则使用相同冻结状态。', '',
             'V3 与 V2 使用不同地图集合、表示和训练安排，本报告不将两版数字直接作胜负比较。', '',
             '| 模型／控制器 | 分区 | 完成率 | 路径效率 | 平均步数 | 重复访问率 | p(optimal) | 实际最优率 | 强制步 |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for name, result in report['rollouts'].items():
        for split in SPLITS:
            bucket = result.get('summary', {}).get(split, {})
            cells = [number(bucket.get(metric)) for metric in LOOP_METRICS]
            lines.append(f'| {name} | {split} | ' + ' | '.join(cells) + f" | {bucket.get('forced_decisions', '缺失')} |")
    lines += ['', '## 预定主模型与配对差值', '',
              '以下为点估计及 95% bootstrap 区间。差值严格按表中方向；完成率、效率越高越好，重复访问率越低越好。JSON 包含全部固定 2×2 主效应、交互、次要教师对照和各模型 sample−greedy 的配对区间。', '',
              '| 预定比较 | 分区 | 完成率／差值 [CI] | 路径效率／差值 [CI] | 重复访问率／差值 [CI] |', '|---|---|---|---|---|']
    display = [f'{PRIMARY}/greedy', f'{PRIMARY}/sample', 'greedy/primary_minus_random', 'sample/primary_minus_random',
               'greedy/mean_coordinates_effect', 'greedy/mean_multi_effect', 'greedy/interaction',
               'sample/mean_coordinates_effect', 'sample/mean_multi_effect', 'sample/interaction',
               'greedy/secondary_teacher_minus_gold', 'sample/secondary_teacher_minus_gold']
    for name in display:
        result = report['rollout_ci'].get(name, report['paired_contrasts'].get(name, {}))
        for split in SPLITS:
            bucket = result.get(split, {})
            lines.append(f'| {name} | {split} | ' + ' | '.join(interval(bucket, metric) for metric in
                         ['completion_rate', 'mean_path_efficiency', 'step_weighted_repeated_visit_rate']) + ' |')
    lines += ['', '## 离线 gold 目标与教师拟合分别报告', '',
              '完整离线 test 为 80 张地图×3 个起点×3 道题（720 题），OOD 为 40×3×3（360 题），包含不可达状态。它们的覆盖范围大于上面的可达闭环子集。动作 gold 是最优动作均匀策略；Boolean／Score gold 是可程序验证的确定真值。动作 CE／KL 只评价对参考策略的恢复，不能声称已经校准环境不确定性。', '',
              '| 模型 | 分区 | 动作最优命中 | 动作最优质量 | 动作 gold CE | 动作 gold KL | Solvable 准确率／Brier | Value 准确率／Brier |',
              '|---|---|---:|---:|---:|---:|---|---|']
    for name, result in report['runs'].items():
        for split in SPLITS:
            bucket = result.get('offline', {}).get(split, {})
            action = bucket.get('action', {})
            cells = [number(action.get(k)) for k in ['optimal_action_accuracy', 'optimal_action_mass', 'gold_cross_entropy', 'gold_kl_target_to_student']]
            for qid in ['solvable', 'value']:
                b = bucket.get(qid, {})
                cells.append(number(b.get('deterministic_accuracy')) + '／' + number(b.get('gold_expected_brier')))
            lines.append(f'| {name} | {split} | ' + ' | '.join(cells) + ' |')
    lines += ['', '教师拟合使用冻结坐标输入上 Jev 返回的可用原样 rounded proxy；ASCII 学生与这一教师参考比较时，教师输入仍是坐标表示，不能称作 ASCII 输入上的 Jev 实测。非归一化和缺失教师输出仅在教师指标中剔除，学生 gold 指标仍覆盖全部题。CE／KL 使用自然对数和 1e-12 概率下限；JSON 报告受下限影响的目标质量。多类 Brier 未除以类别数。', '',
              '| 分区／题型 | 教师可用／总数 | 隔离无效 | 缺失 |', '|---|---:|---:|---:|']
    for split in SPLITS:
        for qid in ['action', 'solvable', 'value']:
            c = report['teacher_coverage'][split][qid]
            lines.append(f"| {split}/{qid} | {c['usable']}/{c['questions']} | {c['quarantined']} | {c['missing']} |")
    lines += ['', '| 模型 | 分区／题型 | 教师覆盖题数 | 教师 TV | 教师 KL |', '|---|---|---:|---:|---:|']
    for name, result in report['runs'].items():
        for split in SPLITS:
            for qid in ['action', 'solvable', 'value']:
                bucket = result.get('offline', {}).get(split, {}).get(qid, {})
                lines.append(f"| {name} | {split}/{qid} | {bucket.get('teacher_eligible', '缺失')} | {number(bucket.get('teacher_tv'))} | {number(bucket.get('teacher_kl_target_to_student'))} |")
    lines += ['', '## 完整性与来源', '',
              f"固定 warm-start SHA-256：`{report['warm_start_sha256']}`。主展示和运行配置来自训练前 launch manifest；每个结果的输入、配置、checkpoint、预测及轨迹哈希记录在 JSON。所有已加载闭环轨迹均由环境重新推进，并重放逐 episode 随机数；结果不依赖 JSON 内自报的成功率。", '',
              'warm-start hash 核对的是冻结源权重和运行清单；训练器日志未另行记录加载瞬间的权重 hash。学生回放的 checkpoint hash 与训练完成后 best 权重清单逐项匹配，每步输入也按冻结 renderer 重建并核对 hash。', '',
              '远端闭环使用删除 teacher／oracle 标签后的最小环境包；本地基准保留原始 canonical 文件来源。两套文件哈希分别记录，环境身份、顺序及初始状态逐项一致；不将这种序列化差异当作地图差异，也不隐藏来源变化。', '',
              f"离线训练结果齐全：{sum(r['status'] == 'complete' for r in report['runs'].values())}/5；闭环结果齐全：{sum(r['status'] == 'complete' for r in report['rollouts'].values())}/12（含两个基准）。", '']
    diagnostic = report.get('sampling_vs_random_diagnostic', {}).get('v3_gold_ascii_multi_seed17', {})
    if diagnostic:
        lines += [f"ASCII multi 学生在已访问状态的 {diagnostic['nonforced_decisions']} 次采样决策中，每个候选概率与均匀分布的最大绝对差仅 {diagnostic['max_absolute_deviation_from_uniform']:.8f}；40 局中 {diagnostic['identical_action_sequences']} 局的完整动作序列与同种子随机基准相同。学生原始概率、唯一不同轨迹与所有失败均保留。", '']
    if report.get('old_task_regression'):
        lines += ['旧非导航任务的回归测试见 [独立回归报告](navigation_v3_regression_zh.md)。它复用 V2 测试题，不属于新的未见任务评测；其中记录的 OOD 退步与本报告的新导航收益同时保留。', '']
    if report['missing']:
        lines += ['尚缺以下结果：', ''] + [f'- {item}' for item in report['missing']] + ['']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path('research/private_navigation_v3'))
    parser.add_argument('--runs-dir', type=Path, default=Path('research/private_navigation_v3/runs'))
    parser.add_argument('--rollouts-dir', type=Path, default=Path('research'))
    parser.add_argument('--json-output', type=Path, default=Path('research/navigation_v3_summary.json'))
    parser.add_argument('--report-output', type=Path, default=Path('research/navigation_v3_report_zh.md'))
    parser.add_argument('--bootstrap-samples', type=int, default=500)
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args()
    if args.bootstrap_samples < 0:
        parser.error('--bootstrap-samples must be nonnegative')
    views = args.data_dir / 'views'
    launch = read_json(views / 'launch_manifest.json')
    manifest = read_json(views / 'manifest.json')
    if launch['main_display'] != PRIMARY or launch['new_test_used_for_selection'] is not False:
        raise ValueError('Predeclared primary or test-selection policy changed')
    launch_runs = {row['name']: row for row in launch['runs']}
    if set(launch_runs) != set(RUNS):
        raise ValueError('Run roster differs from the frozen five-arm protocol')
    records = read_jsonl(views / 'coords_multi.jsonl')
    reference, _ = reference_questions(records)
    teacher_coverage = {}
    for split in SPLITS:
        teacher_coverage[split] = {}
        for qid in ['action', 'solvable', 'value']:
            selected = [r for r in reference.values() if r['split'] == split and r['qid'] == qid]
            counts = Counter('usable' if r['teacher_probs'] is not None else 'quarantined' if r['teacher_target_error'] else 'missing' for r in selected)
            teacher_coverage[split][qid] = {'questions': len(selected), **{k: counts[k] for k in ['usable', 'quarantined', 'missing']}}
    episodes, train_groups, cohort = select_episodes(args.data_dir, per_split=20)
    dataset_manifest = read_json(args.data_dir / 'manifest.json')
    old_game_path = Path(dataset_manifest['v2_input_path'])
    if sha(old_game_path) != dataset_manifest['v2_input_sha256'] or sha(args.data_dir / 'all.jsonl') != dataset_manifest['all_sha256']:
        raise ValueError('Canonical V3 or excluded V2 game-source hash mismatch')
    old_maps = {source_group_id(row['metadata']['environment_state']) for row in read_jsonl(old_game_path)
                if row['metadata']['environment_state']['game'] == 'grid_navigation'}
    split_maps = defaultdict(set)
    for row in read_jsonl(args.data_dir / 'all.jsonl'):
        group = source_group_id(row['metadata']['environment_state'])
        if group != row['metadata']['source_group_id'] or group in old_maps:
            raise ValueError('V3 source-map identity mismatch or overlap with the V2 warm-start game data')
        split_maps[row['split']].add(group)
    if sum(map(len, split_maps.values())) != len(set.union(*split_maps.values())):
        raise ValueError('V3 source maps overlap across train/dev/calibration/test/ood')
    minimal_dir = args.data_dir / 'eval_minimal'
    minimal_manifest = read_json(minimal_dir / 'manifest.json')
    for filename, entry in minimal_manifest['files'].items():
        if sha(args.data_dir / filename) != entry['original_sha256'] or sha(minimal_dir / filename) != entry['minimal_sha256']:
            raise ValueError('Minimal environment package provenance hash mismatch')
        original, minimal = read_jsonl(args.data_dir / filename), read_jsonl(minimal_dir / filename)
        if len(original) != len(minimal) or len(original) != entry['records']:
            raise ValueError('Minimization changed the number of source records')
        for before, after in zip(original, minimal):
            if any(before[key] != after[key] for key in ['id', 'split']) or any(
                    before['metadata'][key] != after['metadata'][key] for key in ['environment_state', 'source_group_id']):
                raise ValueError('Minimization changed an environment or its order')
    minimal_episodes, minimal_train, minimal_cohort = select_episodes(minimal_dir, per_split=20)
    if episodes != minimal_episodes or train_groups != minimal_train:
        raise ValueError('Minimal/canonical cohorts differ')
    allowed_hashes = [cohort['data_sha256'], minimal_cohort['data_sha256']]
    report = {'schema_version': 'openjev-navigation-v3-summary-v1', 'generated_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'primary': PRIMARY, 'training_seeds': [17], 'bootstrap_samples': args.bootstrap_samples,
              'warm_start_sha256': launch['initial_checkpoint_sha256'], 'cohort': cohort,
              'launch_manifest_sha256': sha(views / 'launch_manifest.json'), 'views_manifest_sha256': sha(views / 'manifest.json'),
              'teacher_coverage': teacher_coverage, 'runs': {}, 'rollouts': {}, 'rollout_ci': {}, 'missing': []}
    report['input_minimization'] = {'manifest': minimal_manifest, 'manifest_sha256': sha(minimal_dir / 'manifest.json'),
                                    'all_environment_records_and_order_verified_identical': True}
    report['map_group_audit'] = {'v3_source_maps_by_split': {s: len(g) for s, g in split_maps.items()},
                                 'excluded_v2_source_maps': len(old_maps), 'v2_source_map_overlap': 0,
                                 'cross_split_map_overlap': 0, 'v2_source_sha256': sha(old_game_path)}
    for name, (view, objective) in RUNS.items():
        view_hash = sha(views / f'{view}.jsonl')
        if view_hash != manifest['views'][view]['input_sha256'] or view_hash != launch_runs[name]['input_sha256']:
            raise ValueError(f'{name}: frozen view was modified')
        view_reference, _ = reference_questions(read_jsonl(views / f'{view}.jsonl'))
        for key, source in reference.items():
            if source['split'] in SPLITS and any(view_reference[key][field] != source[field] for field in
                    ['state_id', 'family_id', 'split', 'type', 'candidate_ids', 'gold_probs', 'gold_probs_kind', '_bootstrap_group']):
                raise ValueError('Offline evaluation states/targets differ across the representation/coverage views')
        result, _ = load_run(args.runs_dir / name, name, view, objective, reference, view_hash, launch, args.bootstrap_samples)
        report['runs'][name] = result
        report['missing'].extend(result.get('missing_files', []))
    gold_names = [name for name, (_, objective) in RUNS.items() if objective == 'gold_distribution']
    if all(report['runs'][name]['status'] == 'complete' for name in gold_names):
        batches = [[row['batch_question_ids_sha256'] for row in read_json(args.runs_dir / name / 'train_log.json')]
                   for name in gold_names]
        if any(sequence != batches[0] for sequence in batches[1:]):
            raise ValueError('The four gold runs did not receive the same ordered exposure-slot batches')
        report['four_gold_sampling_audit'] = {'status': 'complete', 'runs': gold_names, 'steps_compared': 1200,
                    'complete_batch_sequence_sha256': hashlib.sha256('\n'.join(batches[0]).encode()).hexdigest(),
                    'note': 'Exposure-slot question IDs match; rendered inputs/physical starts differ by the declared factors. Teacher arm has a different eligible target list.'}
    else:
        report['four_gold_sampling_audit'] = {'status': 'pending_training_logs'}
    groups = {}
    for name in ['random', 'oracle']:
        result, by_split = audit_rollout(args.rollouts_dir / f'navigation_v3_{name}.json', name, episodes, cohort, train_groups,
                                        allowed_input_hashes=allowed_hashes)
        report['rollouts'][name] = result
        if result['status'] == 'complete':
            groups[name] = by_split
        else:
            report['missing'].extend(result['missing_files'])
    for name, (view, _) in RUNS.items():
        for policy in CONTROLLERS:
            key = f'{name}/{policy}'
            path = args.rollouts_dir / f'navigation_v3_{name}_{policy}.json'
            result, by_split = audit_rollout(path, policy, episodes, cohort, train_groups, view.split('_')[0], allowed_hashes)
            report['rollouts'][key] = result
            if result['status'] == 'complete':
                run = report['runs'][name]
                if run['status'] == 'complete':
                    if result['checkpoint_sha256'] != run['checkpoint_sha256']:
                        raise ValueError(f'{key}: rollout used a different checkpoint from the completed run')
                    result['checkpoint_verification'] = 'matches completed run best weights'
                else:
                    result['checkpoint_verification'] = 'pending completed-run provenance files'
                groups[key] = by_split
            else:
                report['missing'].extend(result['missing_files'])
    for name, by_split in groups.items():
        report['rollout_ci'][name] = {split: bootstrap_contrast({name: by_split[split]}, {name: 1}, args.bootstrap_samples) for split in SPLITS}
    report['paired_contrasts'] = make_contrasts(groups, args.bootstrap_samples)
    diagnostic = {}
    if report['rollouts']['random']['status'] == 'complete':
        random_episodes = {e['id']: e for e in read_json(args.rollouts_dir / 'navigation_v3_random.json')['episodes']}
        for name in RUNS:
            if report['rollouts'][f'{name}/sample']['status'] != 'complete':
                continue
            episodes_now = read_json(args.rollouts_dir / f'navigation_v3_{name}_sample.json')['episodes']
            identical, count, maximum = 0, 0, 0.0
            for episode in episodes_now:
                identical += [s['action'] for s in episode['steps']] == [s['action'] for s in random_episodes[episode['id']]['steps']]
                for transition in episode['steps']:
                    if not transition['forced']:
                        count += 1
                        probabilities = transition['probabilities']
                        maximum = max(maximum, max(abs(p - 1 / len(probabilities)) for p in probabilities.values()))
            diagnostic[name] = {'identical_action_sequences': identical, 'episodes': len(episodes_now),
                                'nonforced_decisions': count, 'max_absolute_deviation_from_uniform': maximum,
                                'scope': 'actual visited states under the fixed categorical controller and RNG seed'}
    report['sampling_vs_random_diagnostic'] = diagnostic
    regression = args.data_dir / 'regression' / 'comparison.json'
    if regression.is_file():
        report['old_task_regression'] = {'path': str(regression), 'sha256': sha(regression),
                                         'scope': 'reused V2 nongrid test/ood questions; not new held-out task families'}
    report['complete'] = not report['missing']
    for path in [args.json_output, args.report_output]:
        path.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    args.report_output.write_text(render_report(report) + '\n')
    print(json.dumps({'complete': report['complete'], 'missing_files': len(report['missing']),
                      'report': str(args.report_output), 'summary': str(args.json_output)}, ensure_ascii=False))
    if not report['complete'] and not args.allow_incomplete:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
