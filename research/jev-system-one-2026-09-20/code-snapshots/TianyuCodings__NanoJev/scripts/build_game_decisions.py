#!/usr/bin/env python3
"""生成按对称棋盘/同源地图隔离的小游戏决策数据，无教师 API。

Public rendering API: make_record(state, split, index=0, seed=17, rng=None).
Choice gold_probs is a uniform optimal-action policy, not calibrated uncertainty.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import unittest

from game_tasks import (all_ttt_states, grid_distances, self_test as test_environments,
                        solve, source_group_id, transform_state, valid_actions)


SPLITS = ('train', 'dev', 'calibration', 'test', 'ood')
DEFAULT_TTT_COUNTS = dict(zip(SPLITS, (360, 40, 40, 80, 40)))
DEFAULT_GRID_COUNTS = dict(zip(SPLITS, (400, 40, 40, 80, 40)))
HEADERS = {
    'train': 'Current game position:',
    'dev': 'Review this game position:',
    'calibration': 'Recorded game position:',
    'test': 'Independent game position:',
    'ood': 'New game position:',
    'rollout': 'Current game position:',
}
TEMPLATES = {
    'tic_tac_toe': {
        'state': '{header}\nTic-tac-toe. X starts; turns alternate. Three in a row wins. Empty=.; cells 1-9 go row by row.\n{board}\nTo move: {player}.',
        'action': 'Choose a legal move maximizing win/draw/loss under perfect play by both sides. Earlier wins are not preferred; all equally best moves count.',
        'candidate': 'Place {player} in row {row}, column {column} (cell {cell}).',
        'boolean': 'Can the player to move force a win against perfect opposing play?',
        'score': 'What is the best attainable outcome for the player to move, assuming perfect play by both sides?',
        'score_criteria': ['The player to move loses under perfect play.',
                           'The game is a draw under perfect play.',
                           'The player to move wins under perfect play.'],
    },
    'grid_navigation': {
        'state': '{header}\nGrid navigation. Each legal orthogonal step costs 1; no diagonals. A=agent, G=goal, #=wall, .=open.\n{board}',
        'action': 'Choose a legal next step on a shortest route to G. If G is unreachable, all legal moves tie. Walls cannot be crossed.',
        'candidate': 'Move one cell {direction}.',
        'boolean': 'Can the agent reach G by legal orthogonal moves?',
        'score': 'Classify the minimum number of legal steps from A to G; use the unreachable category if no route exists.',
        'score_criteria': ['The goal is reachable in one or two steps.',
                           'The goal is reachable in three to five steps.',
                           'The goal is reachable in six or more steps.',
                           'The goal cannot be reached.'],
    },
}


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def make_record(state, split, index=0, seed=17, rng=None):
    """Render a nonterminal JSON environment state using the training schema.

    No oracle solution enters the public state/questions text. One-action states
    are supported for rollout; callers must handle terminal states separately.
    """
    if split not in HEADERS:
        raise ValueError(f'Unknown render split: {split}')
    actions = valid_actions(state)
    if not actions:
        raise ValueError('A terminal/no-action state cannot form a Choice question')
    rng = random.Random(seed + index) if rng is None else rng
    game = state['game']
    templates = TEMPLATES[game]
    oracle = solve(state)
    group = source_group_id(state)
    candidate_order = list(actions)
    rng.shuffle(candidate_order)
    if game == 'tic_tac_toe':
        board = '\n'.join(' '.join(state['board'][i:i+3]) for i in range(0, 9, 3))
        rendered_state = templates['state'].format(header=HEADERS[split], board=board, player=state['player'])
        criteria = {}
        for action in candidate_order:
            cell = int(action.removeprefix('cell_'))
            criteria[action] = templates['candidate'].format(player=state['player'], row=(cell-1)//3+1,
                                                              column=(cell-1)%3+1, cell=cell)
        boolean = oracle['value'] == 1
        score = oracle['value'] + 1
        shift = ('early_game_6_to_9_legal_actions' if len(actions) >= 6 else
                 'mid_late_game_2_to_5_legal_actions' if len(actions) >= 2 else 'single_forced_action')
    else:
        size = state['size']
        cells = [['.'] * size for _ in range(size)]
        for row, col in state['walls']:
            cells[row][col] = '#'
        cells[state['goal'][0]][state['goal'][1]] = 'G'
        cells[state['position'][0]][state['position'][1]] = 'A'
        board = '\n'.join(' '.join(row) for row in cells)
        rendered_state = templates['state'].format(header=HEADERS[split], board=board)
        criteria = {action: templates['candidate'].format(direction=action) for action in candidate_order}
        boolean = oracle['reachable']
        distance = oracle['distance']
        score = 3 if distance is None else (0 if distance <= 2 else (1 if distance <= 5 else 2))
        shift = f'{size}x{size}_grid_size_shift' if size != 4 else '4x4_grid'
    optimal = sorted(oracle['optimal_actions'])
    representative = optimal[0]
    state_id = f'{game}:{stable_hash(state)[:24]}'
    questions = {
        'action': {'type': 'choice', 'instructions': templates['action'], 'criteria': criteria},
        'solvable': {'type': 'boolean', 'instructions': templates['boolean']},
        'value': {'type': 'score', 'instructions': templates['score'], 'criteria': templates['score_criteria']},
    }
    return {
        'id': state_id, 'state_id': state_id,
        'family_id': 'tic_tac_toe_minimax_v1' if game == 'tic_tac_toe' else 'grid_navigation_bfs_v1',
        'split': split, 'state': rendered_state, 'questions': questions,
        'gold': {'action': representative, 'solvable': boolean, 'value': score},
        'gold_probs': {
            'action': {action: (1 / len(optimal) if action in optimal else 0.0) for action in candidate_order},
            'solvable': {'false': float(not boolean), 'true': float(boolean)},
            'value': {str(i): float(i == score) for i in range(len(templates['score_criteria']))},
        },
        'gold_probs_kind': {'action': 'optimal_action_policy', 'solvable': 'deterministic_truth', 'value': 'deterministic_truth'},
        'optimal_actions': {'action': optimal},
        'metadata': {
            'source': 'self_authored_programmatic', 'license': 'CC0-1.0',
            'source_group_id': group, 'template_id': f'{game}:{split}:en:v1', 'language': 'en',
            'environment_state': state, 'oracle': oracle,
            'representative_optimal_action_not_unique_truth': len(optimal) > 1,
            'hard_action_selection': 'lexicographically first optimal action; evaluation must accept every optimal action',
            'action_distribution_meaning': 'uniform target over equally optimal actions, not real-world uncertainty or calibrated win probabilities',
            'distribution_shift': shift,
        },
    }


def ttt_pools():
    pools = {'id': {}, 'ood': {}}
    for state in all_ttt_states():
        legal = valid_actions(state)
        if len(legal) < 2:
            continue
        group = source_group_id(state)
        name = 'ood' if len(legal) >= 6 else 'id'
        pools[name].setdefault(group, state)
    return {key: list(groups.values()) for key, groups in pools.items()}


def sample_grid(size, unreachable, rng, seen_groups):
    # Rejection sampling fixes target reachability before solving labels. Maps,
    # including all rotated/reflected versions and all starts, are unique here.
    for _ in range(100000):
        density = rng.uniform(0.18, 0.38)
        walls = [[r, c] for r in range(size) for c in range(size) if rng.random() < density]
        wall_set = set(map(tuple, walls))
        free = [(r, c) for r in range(size) for c in range(size) if (r, c) not in wall_set]
        if len(free) < 4:
            continue
        goal = list(rng.choice(free))
        prototype = {'game': 'grid_navigation', 'size': size, 'walls': walls, 'position': goal, 'goal': goal}
        distances = grid_distances(prototype)
        starts = [list(cell) for cell in free if list(cell) != goal and ((cell not in distances) == unreachable)]
        rng.shuffle(starts)
        for start in starts:
            state = {**prototype, 'position': start}
            if len(valid_actions(state)) < 2:
                continue
            group = source_group_id(state)
            if group in seen_groups:
                break
            seen_groups.add(group)
            return state
    raise RuntimeError('Grid rejection sampling exhausted; reduce counts or change seed')


def validate_records(records):
    ids, groups, raw_states = set(), {}, set()
    for split, rows in records.items():
        for row in rows:
            if row['id'] in ids or row['split'] != split:
                raise ValueError('Duplicate state id or inconsistent split')
            ids.add(row['id'])
            env = row['metadata']['environment_state']
            raw_key = stable_hash(env)
            if raw_key in raw_states:
                raise ValueError('Duplicate environment state')
            raw_states.add(raw_key)
            group = source_group_id(env)
            if group != row['metadata']['source_group_id']:
                raise ValueError('Source group does not match environment')
            if group in groups:
                raise ValueError('Repeated symmetry/source-map group, including within a split')
            groups[group] = split
            answer = solve(env)
            optimal = set(answer['optimal_actions'])
            if set(row['questions']['action']['criteria']) != set(valid_actions(env)):
                raise ValueError('Candidate set must contain exactly the legal actions')
            if set(row['optimal_actions']['action']) != optimal or row['gold']['action'] not in optimal:
                raise ValueError('Action oracle mismatch')
            if row['metadata']['representative_optimal_action_not_unique_truth'] != (len(optimal) > 1):
                raise ValueError('Missing multi-optimum hard-label qualification')
            expected_bool = answer['value'] == 1 if env['game'] == 'tic_tac_toe' else answer['reachable']
            distance = answer.get('distance')
            expected_score = (answer['value'] + 1 if env['game'] == 'tic_tac_toe' else
                              (3 if distance is None else (0 if distance <= 2 else (1 if distance <= 5 else 2))))
            if row['gold']['solvable'] != expected_bool or row['gold']['value'] != expected_score:
                raise ValueError('Auxiliary oracle mismatch')
            for qid, question in row['questions'].items():
                if set(question) - {'type', 'instructions', 'criteria'}:
                    raise ValueError('Metadata leaked into public question payload')
                expected_ids = (set(question['criteria']) if question['type'] == 'choice' else
                                {'false', 'true'} if question['type'] == 'boolean' else
                                {str(i) for i in range(len(question['criteria']))})
                probabilities = row['gold_probs'][qid]
                if set(probabilities) != expected_ids or abs(sum(probabilities.values()) - 1) > 1e-12:
                    raise ValueError('Gold distribution mapping or normalization mismatch')
                if any(not 0 <= value <= 1 for value in probabilities.values()):
                    raise ValueError('Invalid target mass')
                if qid == 'action':
                    for action, probability in probabilities.items():
                        if probability != (1 / len(optimal) if action in optimal else 0.0):
                            raise ValueError('Action distribution is not uniform over all optimal moves')
    return {'states': len(ids), 'unique_source_groups': len(groups),
            'cross_split_source_group_overlap': 0, 'exact_duplicate_states': 0}


def build_records(seed=17, ttt_counts=None, grid_counts=None):
    ttt_counts = dict(DEFAULT_TTT_COUNTS if ttt_counts is None else ttt_counts)
    grid_counts = dict(DEFAULT_GRID_COUNTS if grid_counts is None else grid_counts)
    for counts in [ttt_counts, grid_counts]:
        if set(counts) != set(SPLITS) or any(type(n) is not int or n < 0 for n in counts.values()):
            raise ValueError('Every split count must be a nonnegative integer')
    pools = ttt_pools()
    if sum(ttt_counts[split] for split in SPLITS[:-1]) > len(pools['id']) or ttt_counts['ood'] > len(pools['ood']):
        raise ValueError(f'TTT capacity exceeded: ID={len(pools["id"])}, OOD={len(pools["ood"])} symmetry groups')
    rng = random.Random(seed)
    rng.shuffle(pools['id'])
    rng.shuffle(pools['ood'])
    records = {split: [] for split in SPLITS}
    offset, seen_grid_groups = 0, set()
    for split_index, split in enumerate(SPLITS):
        rendering_rng = random.Random(seed + 1000 + split_index)
        selected = pools['ood'][:ttt_counts[split]] if split == 'ood' else pools['id'][offset:offset+ttt_counts[split]]
        if split != 'ood':
            offset += ttt_counts[split]
        for index, state in enumerate(selected):
            state = transform_state(state, rendering_rng.randrange(8))
            records[split].append(make_record(state, split, index, rng=rendering_rng))
        grid_rng = random.Random(seed + 2000 + split_index)
        for index in range(grid_counts[split]):
            state = sample_grid(6 if split == 'ood' else 4, index % 4 == 0, grid_rng, seen_grid_groups)
            records[split].append(make_record(state, split, index, rng=rendering_rng))
        rendering_rng.shuffle(records[split])
    validate_records(records)
    return records


def write_dataset(output_dir, seed=17, ttt_counts=None, grid_counts=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records = build_records(seed, ttt_counts, grid_counts)
    manifest = {
        'schema_version': 'openjev-games-v1', 'seed': seed, 'source': 'self_authored_programmatic',
        'license': 'CC0-1.0', 'teacher': None, 'oracle_cost_usd': 0,
        'oracle_algorithms': {'tic_tac_toe': 'full finite minimax, memoized, win/draw/loss objective',
                              'grid_navigation': 'exact breadth-first shortest paths from goal'},
        'gold_probs_kind': {'action': 'optimal_action_policy', 'solvable': 'deterministic_truth', 'value': 'deterministic_truth'},
        'split_policy': {'tic_tac_toe': 'D4 board-symmetry groups disjoint; ID 2..5 legal moves, OOD 6..9',
                         'grid_navigation': 'D4 wall-map+goal groups disjoint, ignoring agent start; ID 4x4, OOD 6x6',
                         'templates': 'split-specific header, shared fully disclosed game rules and question templates'},
        'templates': TEMPLATES, 'headers': HEADERS,
        'code_sha256': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                        for name in ['game_tasks.py', 'build_game_decisions.py']},
        'limits': [
            'Uniform optimal-action target is not a probability of success or calibrated epistemic uncertainty.',
            'A representative hard action is not a unique truth when several moves are optimal.',
            'ID splits share the same finite game rules; D4/state isolation does not prove absence of all trajectory or structural similarity.',
            'Grid maps have exactly one rendered start here; grouping excludes alternative starts of the same map across splits.',
            'Unreachable grid cases deliberately give equal target mass to all legal moves.',
            'OOD changes remaining TTT horizon/action count or grid size; it is not a new game-rule family.',
            'Text is compact by construction; actual tokenizer length must be checked before training, with no truncation.',
            'These are original toy games, not Doom or an implementation of Jev.',
        ],
        'audit': validate_records(records), 'splits': {},
    }
    for split, rows in records.items():
        payload = ''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in rows)
        (output_dir / f'{split}.jsonl').write_text(payload, encoding='utf-8')
        by_game = {}
        for game in ['tic_tac_toe', 'grid_navigation']:
            selected = [row for row in rows if row['metadata']['environment_state']['game'] == game]
            by_game[game] = {
                'states': len(selected), 'questions': 3 * len(selected),
                'choice_k': dict(Counter(len(row['questions']['action']['criteria']) for row in selected)),
                'optimal_action_count': dict(Counter(len(row['optimal_actions']['action']) for row in selected)),
                'boolean_labels': dict(Counter(str(row['gold']['solvable']).lower() for row in selected)),
                'score_labels': dict(Counter(row['gold']['value'] for row in selected)),
            }
        manifest['splits'][split] = {'states': len(rows), 'questions': 3 * len(rows),
                                      'sha256': hashlib.sha256(payload.encode()).hexdigest(), 'by_game': by_game}
    all_payload = ''.join((output_dir / f'{split}.jsonl').read_text() for split in SPLITS)
    (output_dir / 'all.jsonl').write_text(all_payload, encoding='utf-8')
    manifest['all_sha256'] = hashlib.sha256(all_payload.encode()).hexdigest()
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def self_test():
    class DatasetTests(unittest.TestCase):
        def test_reproducibility_oracle_and_leakage(self):
            counts = dict(zip(SPLITS, (5, 2, 2, 3, 2)))
            first = build_records(31, counts, counts)
            second = build_records(31, counts, counts)
            self.assertEqual(first, second)
            self.assertEqual(validate_records(first)['states'], 28)
            broken = {split: list(rows) for split, rows in first.items()}
            changed = dict(first['train'][0])
            changed['split'] = 'test'
            broken['test'].append(changed)
            with self.assertRaises(ValueError):
                validate_records(broken)

        def test_uniform_ties_and_rollout_rendering(self):
            state = {'game': 'tic_tac_toe', 'board': '.' * 9, 'player': 'X'}
            row = make_record(state, 'rollout')
            self.assertEqual(len(row['optimal_actions']['action']), 9)
            self.assertTrue(row['metadata']['representative_optimal_action_not_unique_truth'])
            self.assertEqual(set(row['gold_probs']['action'].values()), {1/9})
            self.assertNotIn('oracle', row['state'])
            self.assertEqual(row['gold_probs_kind']['action'], 'optimal_action_policy')
            with self.assertRaises(ValueError):
                make_record({'game': 'tic_tac_toe', 'board': 'XXXOO....', 'player': 'O'}, 'rollout')

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DatasetTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    return {'tests': result.testsRun, 'passed': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', default='research/private_games_v2')
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--self-test', action='store_true')
    for game, counts in [('ttt', DEFAULT_TTT_COUNTS), ('grid', DEFAULT_GRID_COUNTS)]:
        for split in SPLITS:
            parser.add_argument(f'--{game}-{split}', type=int, default=counts[split])
    args = parser.parse_args()
    if args.self_test:
        test_environments()
        self_test()
    counts = {game: {split: getattr(args, f'{game}_{split}') for split in SPLITS} for game in ['ttt', 'grid']}
    manifest = write_dataset(args.output_dir, args.seed, counts['ttt'], counts['grid'])
    print(json.dumps({'output_dir': str(Path(args.output_dir)), 'audit': manifest['audit'],
                      'splits': {split: data['states'] for split, data in manifest['splits'].items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
