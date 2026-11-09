#!/usr/bin/env python3
"""汇总已完成训练的冻结测试结果；缺失结果明确列出，绝不选择测试最优seed。

Standard-library-only: no training, GPU, API, or temperature fitting.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

from evaluate_pipeline_decisions import evaluate, prepare_row, probability_vector, summarize
from train_pipeline_decisions import candidate_ids, read_training_records, validate_training_row
from game_tasks import solve, source_group_id, step, ttt_winner, valid_actions
from evaluate_game_policy import annotate_training_overlap


SEEDS = (17, 18, 19)
OBJECTIVES = ('teacher', 'gold_distribution')
SPLITS = ('test', 'ood')
COHORT_METRICS = {
    'deterministic': ('deterministic_accuracy', 'gold_expected_brier', 'deterministic_ece'),
    'known_chance': ('gold_tv', 'gold_kl_target_to_student', 'gold_expected_brier', 'analytic_expected_ece'),
    'game_choice': ('optimal_action_accuracy', 'optimal_action_mass'),
    'tic_tac_toe_choice': ('optimal_action_accuracy', 'optimal_action_mass'),
    'grid_navigation_choice': ('optimal_action_accuracy', 'optimal_action_mass'),
    'teacher_imitation': ('teacher_tv', 'teacher_kl_target_to_student', 'teacher_argmax_agreement'),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values) - 1) * fraction
    low, high = math.floor(position), math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def reference_questions(records):
    reference, coverage = {}, Counter()
    for row in records:
        targets = validate_training_row(row)
        for qid, question in row['questions'].items():
            target = targets[qid]
            ids = candidate_ids(question)
            key = f"{row['id']}:{qid}"
            if key in reference:
                raise ValueError(f'Duplicate reference question: {key}')
            kind = target['gold_probs_kind'] or ('deterministic_truth' if target['gold_index'] is not None else None)
            reference[key] = {
                'id': key, 'state_id': row['state_id'], 'qid': qid, 'family_id': row['family_id'],
                'split': row['split'], 'type': question['type'], 'candidate_ids': ids,
                'gold_probs': dict(zip(ids, target['gold_distribution_probs'])) if target['gold_distribution_probs'] is not None else None,
                'gold_probs_kind': kind, 'gold_label_kind': target['gold_label_kind'],
                'gold_index': target['gold_index'], 'teacher_probs': target['teacher_probs'],
                'teacher_target_error': target['teacher_target_error'],
                '_bootstrap_group': row['metadata'].get('source_group_id', row['state_id']),
            }
            status = 'usable' if target['teacher_probs'] is not None else ('quarantined' if target['teacher_target_error'] else 'missing')
            for scope in ['all', row['split'], f"{row['split']}/{row['family_id']}/{question['type']}"]:
                coverage[(scope, 'questions')] += 1
                coverage[(scope, status)] += 1
    report = {}
    for scope, _ in coverage:
        if scope not in report:
            report[scope] = {key: coverage[(scope, key)] for key in ['questions', 'usable', 'quarantined', 'missing']}
    return reference, report


def align_predictions(rows, reference, split):
    expected = {key for key, row in reference.items() if row['split'] == split}
    actual = [row['id'] for row in rows]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError(f'{split}: prediction coverage mismatch, expected={len(expected)}, received={len(actual)}')
    aligned = []
    for row in rows:
        source = reference[row['id']]
        if row['split'] != split or row['family_id'] != source['family_id'] or row['type'] != source['type']:
            raise ValueError('Prediction identity differs from frozen data')
        ids = row['candidate_ids']
        if len(ids) != len(source['candidate_ids']) or set(ids) != set(source['candidate_ids']):
            raise ValueError('Prediction candidate set differs from frozen data')
        teacher = dict(zip(source['candidate_ids'], source['teacher_probs'])) if source['teacher_probs'] is not None else None
        current = {**row, **{key: source[key] for key in ['state_id', 'qid', 'gold_probs', 'gold_probs_kind',
                    'gold_label_kind', 'teacher_target_error', '_bootstrap_group']},
                   'teacher_probs': [teacher[key] for key in ids] if teacher is not None else None}
        if source['gold_index'] is not None:
            current['gold_index'] = ids.index(source['candidate_ids'][source['gold_index']])
        else:
            current['gold_index'] = None
        # Stored gold fields are not trusted as a substitute for the frozen input.
        current.pop('gold_distribution_probs', None)
        aligned.append(current)
    evaluate(aligned)  # Audited input validation and metric implementation.
    return aligned


def choose(rows, cohort):
    if cohort == 'deterministic':
        return [row for row in rows if row['gold_probs_kind'] == 'deterministic_truth']
    if cohort == 'known_chance':
        return [row for row in rows if row['family_id'] == 'known_chance_v2' and row['gold_probs_kind'] == 'programmatic_conditional_distribution']
    if cohort == 'teacher_imitation':
        return [row for row in rows if row['teacher_probs'] is not None]
    games = {'tic_tac_toe_minimax_v1', 'grid_navigation_bfs_v1'}
    if cohort == 'tic_tac_toe_choice':
        games = {'tic_tac_toe_minimax_v1'}
    elif cohort == 'grid_navigation_choice':
        games = {'grid_navigation_bfs_v1'}
    return [row for row in rows if row['family_id'] in games and row['type'] == 'choice'
            and row['gold_probs_kind'] == 'optimal_action_policy']


def cohort_metrics(rows):
    return {cohort: summarize(choose(rows, cohort)) for cohort in COHORT_METRICS}


def cluster_bootstrap(rows, cohort, samples=500, seed=20260917):
    """Question-mean metrics, resampling complete source groups, not questions.

    Per-question scalar losses use the audited evaluator; ECE is recomputed from
    weighted bin sufficient statistics for each bootstrap draw.
    """
    selected = [prepare_row(row) for row in choose(rows, cohort)]
    metrics = COHORT_METRICS[cohort]
    groups = {}
    ece_name = 'deterministic_ece' if cohort == 'deterministic' else 'analytic_expected_ece'
    for row in selected:
        group = groups.setdefault(row['_bootstrap_group'], {'n': 0, 'sums': Counter(), 'bins': [[0, 0.0, 0.0] for _ in range(10)]})
        measured = summarize([row])
        group['n'] += 1
        for metric in metrics:
            if metric != ece_name:
                group['sums'][metric] += measured[metric]
        p, q = row['student_probs'], row['_gold']
        best = max(range(len(p)), key=p.__getitem__)
        bucket = group['bins'][min(9, int(p[best] * 10))]
        bucket[0] += 1
        bucket[1] += p[best]
        bucket[2] += q[best]
    if len(groups) < 2 or samples < 1:
        return {'status': 'insufficient_clusters_or_disabled', 'groups': len(groups), 'samples': samples}
    buckets = list(groups.values())
    rng = random.Random(seed)
    collected = {metric: [] for metric in metrics}
    for _ in range(samples):
        draws = Counter(rng.randrange(len(buckets)) for _ in buckets)
        n = 0
        sums, bins = Counter(), [[0, 0.0, 0.0] for _ in range(10)]
        for index, multiplier in draws.items():
            group = buckets[index]
            n += multiplier * group['n']
            for metric, value in group['sums'].items():
                sums[metric] += multiplier * value
            for i, bucket in enumerate(group['bins']):
                for j in range(3):
                    bins[i][j] += multiplier * bucket[j]
        for metric in metrics:
            value = sum(abs(b[1]-b[2]) for b in bins) / n if metric == ece_name else sums[metric] / n
            collected[metric].append(value)
    return {'status': 'complete', 'samples': samples, 'seed': seed, 'groups': len(groups),
            'questions': len(selected), 'unit': 'metadata.source_group_id, fallback state_id',
            'weighting': 'question mean after whole-group resampling', 'confidence_level': 0.95,
            'intervals': {metric: [percentile(values, .025), percentile(values, .975)] for metric, values in collected.items()}}


def load_run(root, objective, seed, reference, data_hash, bootstrap_samples):
    directory = root / f'v2_{objective}_seed{seed}'
    required = ['config.json', 'summary.json', 'predictions_test.jsonl', 'predictions_ood.jsonl']
    missing = [name for name in required if not (directory / name).is_file()]
    if missing:
        return {'status': 'missing', 'directory': str(directory), 'missing_files': missing}, {}
    config, summary = read_json(directory / 'config.json'), read_json(directory / 'summary.json')
    if config.get('seed') != seed or config.get('objective') != objective or summary.get('objective') != objective:
        raise ValueError(f'Run identity mismatch: {directory}')
    hashes = config.get('data_sha256', {})
    if isinstance(hashes, str):
        hashes = {'input': hashes}
    if data_hash not in hashes.values():
        raise ValueError(f'Run was trained on a different data hash: {directory}')
    if summary.get('temperature_fitted') is not False or summary.get('selected_on') != 'dev target CE':
        raise ValueError('Unexpected calibration/checkpoint selection policy')
    result = {'status': 'complete', 'directory': str(directory), 'seed': seed, 'objective': objective,
              'config': config, 'training_summary': summary,
              'file_sha256': {name: sha(directory / name) for name in required},
              'metrics': {}, 'audited_full_metrics': {}, 'matched_jev_coverage_metrics': {}, 'primary_seed17_cluster_ci': {}}
    all_rows = {}
    for split in SPLITS:
        rows = align_predictions(read_jsonl(directory / f'predictions_{split}.jsonl'), reference, split)
        all_rows[split] = rows
        result['audited_full_metrics'][split] = evaluate(rows)
        result['metrics'][split] = cohort_metrics(rows)
        result['matched_jev_coverage_metrics'][split] = cohort_metrics([row for row in rows if row['teacher_probs'] is not None])
        if seed == 17:
            result['primary_seed17_cluster_ci'][split] = {
                cohort: cluster_bootstrap(rows, cohort, bootstrap_samples)
                for cohort in ['deterministic', 'known_chance']}
    return result, all_rows


def aggregate_runs(runs, metric_field='metrics'):
    output = {}
    for objective in OBJECTIVES:
        complete = [runs[f'{objective}_seed{seed}'] for seed in SEEDS if runs[f'{objective}_seed{seed}']['status'] == 'complete']
        data = {'completed_seeds': [run['seed'] for run in complete], 'required_seeds': list(SEEDS),
                'status': 'complete' if len(complete) == 3 else 'incomplete', 'splits': {}}
        if len(complete) == 3:
            for split in SPLITS:
                data['splits'][split] = {}
                for cohort, metrics in COHORT_METRICS.items():
                    counts = {run[metric_field][split][cohort]['questions'] for run in complete}
                    if len(counts) != 1:
                        raise ValueError('Seed runs evaluated different question counts')
                    data['splits'][split][cohort] = {'questions': counts.pop(), 'metrics': {}}
                    for metric in metrics:
                        values = [run[metric_field][split][cohort].get(metric) for run in complete]
                        data['splits'][split][cohort]['metrics'][metric] = (
                            {'mean': statistics.mean(values), 'sample_sd': statistics.stdev(values), 'n_seeds': 3,
                             'seed_values': dict(zip(SEEDS, values))} if all(value is not None for value in values) else None)
        output[objective] = data
    return output


def audit_rollout(path, train_groups):
    if not path.is_file():
        return {'status': 'missing', 'path': str(path)}
    report = read_json(path)
    if len(report['episodes']) != 80 or report['cohort']['per_group'] != 20:
        raise ValueError(f'Rollout cohort must retain all 80 prespecified episodes: {path}')
    counts = Counter((row['split'], row['game']) for row in report['episodes'])
    if set(counts.values()) != {20} or len(counts) != 4:
        raise ValueError('Rollout family/split cohort mismatch')
    for episode in report['episodes']:
        current = episode['initial_state']
        expected_horizon = 2 * current['size'] ** 2 if current['game'] == 'grid_navigation' else 9
        if episode['max_steps'] != expected_horizon or len(episode['steps']) > expected_horizon:
            raise ValueError('Rollout used a different horizon')
        for transition in episode['steps']:
            if transition['state'] != current or transition['action'] not in valid_actions(current):
                raise ValueError('Recorded rollout state/action is invalid')
            next_state = step(current, transition['action'])
            if transition['next_state'] != next_state:
                raise ValueError('Recorded transition does not match the actual game environment')
            actor = transition['actor']
            opponent_turn = current['game'] == 'tic_tac_toe' and current['player'] != episode['student_player']
            if (opponent_turn and actor != 'minimax_opponent') or (
                    not opponent_turn and actor not in {report['policy'], 'forced_legal_action'}):
                raise ValueError('Wrong actor controlled this game turn')
            if transition['optimal_action'] != (transition['action'] in solve(current)['optimal_actions']):
                raise ValueError('Recorded action quality disagrees with the exact solver')
            if actor == 'minimax_opponent' and transition['action'] != sorted(solve(current)['optimal_actions'])[0]:
                raise ValueError('Opponent deviates from the fixed minimax policy')
            if actor == 'forced_legal_action' and len(valid_actions(current)) != 1:
                raise ValueError('Non-forced action mislabeled as forced')
            if actor == 'student':
                probabilities = transition['probabilities']
                probability_vector(probabilities, valid_actions(current), 'student rollout')
                if probabilities[transition['action']] != max(probabilities.values()):
                    raise ValueError('Student rollout action differs from its predicted argmax')
            current = next_state
        if current != episode['final_state']:
            raise ValueError('Final state does not match the retained full trajectory')
        if current['game'] == 'grid_navigation':
            if episode['success'] != (current['position'] == current['goal']):
                raise ValueError('Reported navigation success is incorrect')
        else:
            winner = ttt_winner(current['board'])
            value = 0 if winner is None else (1 if winner == episode['student_player'] else -1)
            if episode['outcome_value'] != value:
                raise ValueError('Reported tic-tac-toe outcome is incorrect')
    cohort = [{key: row[key] for key in ['id', 'game', 'split', 'initial_state']} for row in report['episodes']]
    cohort_hash = hashlib.sha256(json.dumps(cohort, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    annotate_training_overlap(report, train_groups)
    return {'status': 'complete', 'path': str(path), 'sha256': sha(path), 'cohort_sha256': cohort_hash,
            'policy': report['policy'], 'checkpoint_sha256': report.get('checkpoint_sha256'),
            'episodes': len(report['episodes']), 'summary': report['summary'], 'execution': report['execution'],
            'recorded_forward_precisions': sorted({batch['execution'].get('precision', 'unspecified')
                                                   for batch in report.get('parallel_batches', [])}),
            'all_recorded_game_transitions_verified': True}


def format_number(value):
    return '缺失' if value is None else f'{value:.4f}'


def format_seed_stat(value):
    return '缺失' if value is None else f"{value['mean']:.4f} ± {value['sample_sd']:.4f}"


def render_report(report):
    navigation_failure = all(report['rollouts'][name]['status'] == 'complete' for name in ['teacher', 'gold', 'random']) and all(
        report['rollouts'][name]['summary'][f'{split}/grid_navigation']['success_rate'] <
        report['rollouts']['random']['summary'][f'{split}/grid_navigation']['success_rate']
        for name in ['teacher', 'gold'] for split in SPLITS)
    lines = ['# Pipeline v2 冻结评估报告', '', f"生成时间：{report['generated_at_utc']}。", '',
             f"状态：**{'全部结果齐全' if report['complete'] else '结果尚未齐全；下列缺失项没有估计值'}**。", '',
             '预先固定主展示 seed=17；训练重复为 17、18、19。均值±样本标准差只在同一目标的三次训练全部完成后给出；未按 test/ood 选择 seed、checkpoint 或温度。', '',
             *(['**V2 闭环导航未达可用，需要继续研究。** 两个学生在 test 和 ood 的导航成功率都低于固定随机策略。解析概率任务的改进不能代替实际环境中的控制能力，以下完整保留所有失败与冻结评估结果。', ''] if navigation_failure else []),
             '## 数据、教师覆盖与目标含义', '',
             f"冻结数据 SHA-256：`{report['data_sha256']}`。共有 {report['dataset']['states']} 个状态、{report['dataset']['questions']} 道题。", '',
             '| 分区 | 全部问题 | Jev 可用原样 rounded proxy | 隔离的无效分布 | 缺失教师 |',
             '|---|---:|---:|---:|---:|']
    for split in ['all', 'train', 'dev', 'calibration', 'test', 'ood']:
        c = report['jev']['coverage'][split]
        lines.append(f"| {split} | {c['questions']} | {c['usable']} | {c['quarantined']} | {c['missing']} |")
    lines += ['', 'Jev 自身指标仅使用上述可用题目；不把缺失或非归一化输出强行归一化。学生主指标覆盖完整冻结 test/ood；为避免不同分母误读，JSON 另提供与 Jev 相同覆盖范围的三 seed 对照。', '',
              '确定性判断的 accuracy/Brier/ECE、已知抽球分布的 TV/KL、游戏最优动作集合命中分别报告。游戏均匀最优动作目标是策略目标，不能解释成现实不确定性；抽球尚未观察实际结果，使用解析条件分布。Accuracy、概率质量、ECE、TV 使用比例而非百分数；多类 Brier 未除以类别数，范围为 0–2；KL 使用自然对数，单位为 nats。CE/KL 使用 1e-12 对数下限，JSON 披露受下限影响和预测零质量对应的目标质量，不能将有限显示值视为真实无限损失的精确值。', '',
              '## 三次训练与 Jev 的独立结果', '']
    displays = [('deterministic', '确定性问题', ['deterministic_accuracy', 'gold_expected_brier', 'deterministic_ece'], ['Accuracy', 'Brier', 'ECE']),
                ('known_chance', '已知随机分布', ['gold_tv', 'gold_kl_target_to_student', 'analytic_expected_ece'], ['TV', 'KL', '解析 top-label ECE']),
                ('tic_tac_toe_choice', '井字棋动作', ['optimal_action_accuracy', 'optimal_action_mass'], ['最优集合命中', '最优集合概率质量']),
                ('grid_navigation_choice', '网格动作', ['optimal_action_accuracy', 'optimal_action_mass'], ['最优集合命中', '最优集合概率质量'])]
    for cohort, title, metrics, labels in displays:
        lines += [f'### {title}', '', '| 分区/模型 | 题数 | ' + ' | '.join(labels) + ' |', '|---|---:|' + '---:|' * len(metrics)]
        for split in SPLITS:
            for objective in OBJECTIVES:
                result = report['three_seed'][objective]
                bucket = result['splits'].get(split, {}).get(cohort)
                vals = [format_seed_stat(bucket['metrics'].get(key)) if bucket else '待三次结果齐全' for key in metrics]
                lines.append(f"| {split}/{objective} | {bucket['questions'] if bucket else '—'} | " + ' | '.join(vals) + ' |')
            bucket = report['jev']['metrics'][split][cohort]
            lines.append(f"| {split}/Jev rounded proxy | {bucket['questions']} | " + ' | '.join(format_number(bucket.get(key)) for key in metrics) + ' |')
        lines.append('')
    lines += ['## 固定 seed 17 的按源组重采样区间', '',
              f"下表为 {report['bootstrap_samples']} 次源组 bootstrap 的 95% percentile CI；一个状态的各题共同重采样。区间描述固定 checkpoint 的数据采样不确定性，三 seed 标准差描述训练随机性，两者不混为一谈。", '',
              '| 分区/模型 | 确定性 Accuracy：点值；95% CI | 解析分布 TV：点值；95% CI |', '|---|---|---|']
    for split in SPLITS:
        for name in ['teacher_seed17', 'gold_distribution_seed17', 'jev']:
            intervals = (report['jev']['cluster_ci'].get(split, {}) if name == 'jev' else
                         report['runs'][name].get('primary_seed17_cluster_ci', {}).get(split, {}))
            cells = []
            for cohort, metric in [('deterministic', 'deterministic_accuracy'), ('known_chance', 'gold_tv')]:
                interval = intervals.get(cohort, {}).get('intervals', {}).get(metric)
                point = (report['jev']['metrics'][split][cohort].get(metric) if name == 'jev' else
                         report['runs'][name].get('metrics', {}).get(split, {}).get(cohort, {}).get(metric))
                cells.append(f'{point:.4f}；[{interval[0]:.4f}, {interval[1]:.4f}]' if interval and point is not None else '缺失')
            lines.append(f"| {split}/{name} | " + ' | '.join(cells) + ' |')
    lines += ['', 'Brier/ECE、KL 等其余主指标区间及源组数量保存在配套 JSON。bootstrap 以观察到的源组为单位，不能覆盖同一规则族的全部结构相关性。', '',
              '## 真实游戏回放', '',
              '固定每个 test/ood 分区前 20 个可达网格起点和前 20 个井字棋起点；每个策略共 80 局，失败完整保留。所有井字棋使用同一完美 minimax 对手，单合法动作单独记录且不调用学生模型。所有已加载轨迹逐步由环境重新校验。', '',
              '| 策略/分区 | 网格成功率 | 网格路径效率 | TTT 价值保留率 | TTT 轨迹进入训练组 |', '|---|---:|---:|---:|---:|']
    for name, result in report['rollouts'].items():
        for split in SPLITS:
            if result['status'] != 'complete':
                lines.append(f'| {name}/{split} | 缺失 | 缺失 | 缺失 | 缺失 |')
                continue
            grid, ttt = result['summary'][f'{split}/grid_navigation'], result['summary'][f'{split}/tic_tac_toe']
            lines.append(f"| {name}/{split} | {grid['success_rate']:.4f} | {grid['mean_path_efficiency']:.4f} | {ttt['preserved_minimax_value_rate']:.4f} | {ttt['training_overlap']['episodes_visiting_train_group']}/{ttt['episodes']} |")
    lines += ['', 'TTT 初始必败局面的“价值保留”自动满足，须结合 JSON 的初始价值分层与非败局面指标。早盘 OOD 回放可能进入训练的中后盘棋盘组，因此不代表全程未见状态；网格必须继续核对源地图全程隔离。该回放与离线动作集合命中是不同指标。', '',
              '离线指标按各训练 run 的冻结推理精度计算；学生回放的记录精度与固定 seed 17 checkpoint 哈希在 JSON 中单独核对，不能用另一个 seed 的较好离线结果替换这里的轨迹。', '',
              '## 完成状态与复现', '']
    for name, result in report['runs'].items():
        if result['status'] != 'complete':
            lines.append(f"- `{name}` 缺少：{', '.join(result['missing_files'])}。")
        else:
            lines.append(f"- `{name}`：dev 选中 step {result['training_summary']['best_step']}；输入和结果文件哈希已验证。")
    for name, result in report['rollouts'].items():
        if result['status'] != 'complete':
            lines.append(f"- 回放 `{name}` 缺失：`{result['path']}`。")
    lines += ['', '复现：`python3 scripts/summarize_pipeline_v2.py --allow-incomplete`。不带该开关时，缺失结果会写入报告并返回退出码 2。脚本不训练、不调用模型、不修改原始预测。所有完成结果、各 seed 数值、匹配教师覆盖的对照、完整 bootstrap 区间和哈希保存在 `research/pipeline_v2_summary.json`。', '',
              '这些是受控合成规则和自写小游戏，不是 Jev 通用能力、开放世界游戏能力或现实场景校准的证明。教师为低精度 API 输出代理；未测得其内部高精度分布。']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('research/private_pipeline_v2/merged.jsonl'))
    parser.add_argument('--runs-dir', type=Path, default=Path('research/private_pipeline_runs'))
    parser.add_argument('--output-json', type=Path, default=Path('research/pipeline_v2_summary.json'))
    parser.add_argument('--report', type=Path, default=Path('research/pipeline_v2_report_zh.md'))
    parser.add_argument('--bootstrap-samples', type=int, default=500)
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args()
    if args.bootstrap_samples < 0:
        parser.error('bootstrap-samples must be nonnegative')
    records, _ = read_training_records(args.data)
    reference, coverage = reference_questions(records)
    data_hash = sha(args.data)
    jev_rows = [{**row, 'student_probs': row['teacher_probs']} for row in reference.values() if row['teacher_probs'] is not None]
    report = {'schema': 'openjev-pipeline-v2-summary-v1', 'generated_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'script_sha256': sha(__file__), 'data_sha256': data_hash,
              'dataset': {'states': len(records), 'questions': len(reference)}, 'bootstrap_samples': args.bootstrap_samples,
              'fixed_primary_seed': 17, 'required_training_seeds': list(SEEDS),
              'jev': {'coverage': coverage, 'metrics': {}, 'audited_full_metrics': {}, 'cluster_ci': {}}, 'runs': {}, 'rollouts': {}}
    for split in SPLITS:
        rows = [row for row in jev_rows if row['split'] == split]
        report['jev']['metrics'][split] = cohort_metrics(rows)
        report['jev']['audited_full_metrics'][split] = evaluate(rows)
        report['jev']['cluster_ci'][split] = {cohort: cluster_bootstrap(rows, cohort, args.bootstrap_samples)
                                             for cohort in ['deterministic', 'known_chance']}
    for objective in OBJECTIVES:
        for seed in SEEDS:
            result, _ = load_run(args.runs_dir, objective, seed, reference, data_hash, args.bootstrap_samples)
            report['runs'][f'{objective}_seed{seed}'] = result
    checkpoint_manifest_path = args.runs_dir / 'checkpoint_manifest.json'
    checkpoint_entries = {}
    if checkpoint_manifest_path.is_file():
        manifest = read_json(checkpoint_manifest_path)
        if manifest['data_sha256'] != data_hash:
            raise ValueError('Checkpoint manifest refers to different frozen data')
        checkpoint_entries = {entry['name']: entry for entry in manifest['runs']}
        if len(checkpoint_entries) != len(manifest['runs']):
            raise ValueError('Duplicate checkpoint manifest entries')
        report['checkpoint_manifest_sha256'] = sha(checkpoint_manifest_path)
        for name, result in report['runs'].items():
            if result['status'] == 'complete':
                entry = checkpoint_entries.get('v2_' + name)
                if entry is None or entry['seed'] != result['seed'] or entry['objective'] != result['objective'] or entry['best_step'] != result['training_summary']['best_step']:
                    raise ValueError('Checkpoint manifest and completed run identity disagree')
                result['checkpoint_manifest_entry'] = entry
    report['three_seed'] = aggregate_runs(report['runs'])
    report['matched_jev_coverage_three_seed'] = aggregate_runs(report['runs'], 'matched_jev_coverage_metrics')
    train_groups = {row['metadata']['source_group_id'] for row in records if row['split'] == 'train'}
    for name in ['teacher', 'gold', 'random', 'oracle']:
        report['rollouts'][name] = audit_rollout(Path('research') / f'game_{name}_v2.json', train_groups)
        if name in {'teacher', 'gold'} and report['rollouts'][name]['status'] == 'complete':
            objective = 'teacher' if name == 'teacher' else 'gold_distribution'
            entry = checkpoint_entries.get(f'v2_{objective}_seed17')
            if entry is None or report['rollouts'][name]['checkpoint_sha256'] != entry['checkpoint_sha256']:
                raise ValueError('Student rollout checkpoint is not the prespecified seed 17 checkpoint')
            report['rollouts'][name]['prespecified_seed17_checkpoint_verified'] = True
    hashes = {row['cohort_sha256'] for row in report['rollouts'].values() if row['status'] == 'complete'}
    if len(hashes) > 1:
        raise ValueError('Policy arms did not use the same frozen rollout cohort')
    report['complete'] = all(row['status'] == 'complete' for row in report['runs'].values()) and all(
        row['status'] == 'complete' for row in report['rollouts'].values())
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    args.report.write_text(render_report(report))
    print(json.dumps({'complete': report['complete'], 'report': str(args.report), 'json': str(args.output_json),
                      'jev_coverage': report['jev']['coverage']['all'],
                      'missing_runs': [key for key, row in report['runs'].items() if row['status'] != 'complete'],
                      'missing_rollouts': [key for key, row in report['rollouts'].items() if row['status'] != 'complete']}, ensure_ascii=False))
    if not report['complete'] and not args.allow_incomplete:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
