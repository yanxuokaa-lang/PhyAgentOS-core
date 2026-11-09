#!/usr/bin/env python3
"""External Jev control loop, derived from the frozen local V3 rollout.

Kept separate so the historical no-network evaluator and its hashes stay intact.
Internal Jev forward/decode counts are unknown, never recorded as local forwards.
"""
from collections import Counter
import copy,hashlib,math,time,json
from game_tasks import source_group_id,solve,step,valid_actions
from evaluate_navigation_v3 import SEED,canonical_json,episode_rng,validate_distribution,categorical

def rollout_jev(episodes, policy, engine=None, renderer=None, train_groups=None, seed=SEED,
            validation_only=False, progress_every=0):
    if policy not in {'greedy', 'sample'} or validation_only:
        raise ValueError('This runner accepts only real Jev greedy/sample measurements')
    uses_student = policy in {'greedy', 'sample'}
    if uses_student and (engine is None or renderer is None):
        raise ValueError('Student controllers require a prediction engine and the V3 pure-geometric renderer')
    if not episodes:
        raise ValueError('Empty rollout cohort')
    train_groups = set() if train_groups is None else set(train_groups)
    states, rngs = [], {}
    seen_ids, seen_maps = set(), set()
    for episode in episodes:
        initial = copy.deepcopy(episode['initial_state'])
        group = source_group_id(initial)
        if group != episode['source_map_group_id'] or group in train_groups:
            raise ValueError('Initial environment map identity or training overlap mismatch')
        if episode['id'] in seen_ids or group in seen_maps:
            raise ValueError('Each benchmark episode must represent a distinct source map')
        seen_ids.add(episode['id']); seen_maps.add(group)
        answer = solve(initial)
        if initial['game'] != 'grid_navigation' or not answer['reachable'] or answer['terminal']:
            raise ValueError('Benchmark requires reachable nonterminal grid starts')
        rng, seed_hex = episode_rng(seed, group, initial)
        rngs[episode['id']] = rng
        states.append({**episode, 'state': initial, 'rng_seed_sha256': seed_hex,
                       'max_steps': 2 * initial['size'] ** 2, 'shortest_path_length': answer['distance'],
                       'steps': [], 'model_decisions': 0, 'validation_engine_decisions': 0,
                       'forced_decisions': 0, 'active': True,
                       '_visits': Counter({tuple(initial['position']): 1})})
    batches, batch_examples = [], []
    inference_seconds, total_forwards, tick = 0.0, 0, 0
    while any(episode['active'] for episode in states):
        choices, pending, mapping = {}, [], []
        for index, episode in enumerate(states):
            if not episode['active']:
                continue
            state = episode['state']
            actions = sorted(valid_actions(state))
            if state['position'] == state['goal'] or len(episode['steps']) >= episode['max_steps'] or not actions:
                episode['active'] = False
                continue
            if len(actions) == 1:
                choices[index] = {'action': actions[0], 'probabilities': {actions[0]: 1.0},
                                  'actor': 'forced_legal_action', 'draw': None, 'sampling_probability': 1.0,
                                  'answers': None, 'request_id': None}
                episode['forced_decisions'] += 1
            elif uses_student:
                public = renderer(state, split=episode['split'], candidate_order=actions)
                if set(public) != {'state', 'questions'}:
                    raise ValueError('V3 renderer must return only state and questions')
                if set(public['questions']['action']['criteria']) != set(actions):
                    raise ValueError('Rendered candidates differ from the legal environment actions')
                request_id = f"{episode['id']}::step{len(episode['steps'])}"
                pending.append({'id': request_id, **public})
                mapping.append(index)
            else:
                if policy == 'random':
                    probabilities = {action: 1 / len(actions) for action in actions}
                    action, draw, chosen_probability = categorical(probabilities, rngs[episode['id']])
                else:
                    action = sorted(solve(state)['optimal_actions'])[0]
                    probabilities = {candidate: float(candidate == action) for candidate in actions}
                    draw, chosen_probability = None, 1.0
                choices[index] = {'action': action, 'probabilities': probabilities, 'actor': policy,
                                  'draw': draw, 'sampling_probability': chosen_probability,
                                  'answers': None, 'request_id': None}
        if pending:
            started = time.perf_counter()
            response = engine.predict({'states': pending}, batch_questions=0, temperature=1.0)
            elapsed = time.perf_counter() - started
            inference_seconds += elapsed
            execution = response['execution']
            if execution.get('engine') != 'jev_live_api' or execution.get('forward_passes') is not None:
                raise ValueError('Jev must declare live API provenance and unknown internal forward count')
            if not isinstance(execution.get('network_model_calls'), int) or execution['network_model_calls'] < 0:
                raise ValueError('Jev network request count is required, including explicit cache hits')
            temperature = response.get('temperature', {}).get('value')
            if temperature != 1.0:
                raise ValueError('Controller ablation requires the original T=1 model distribution')
            ids = [row['id'] for row in response['states']]
            if len(ids) != len(set(ids)) or set(ids) != {row['id'] for row in pending}:
                raise ValueError('Prediction response does not map one-to-one to the requested states')
            by_id = {row['id']: row['answers'] for row in response['states']}
            batch_id = len(batches)
            batch = {'id': f'batch_{batch_id}', 'tick': tick, 'state_ids': [row['id'] for row in pending],
                     'execution': execution, 'inference_seconds': elapsed}
            batches.append(batch)
            total_forwards += execution['network_model_calls']
            if len(batch_examples) < 3:
                batch_examples.append({**batch, 'states': [{**row, 'answers': by_id[row['id']]} for row in pending]})
            for index, public in zip(mapping, pending):
                episode = states[index]
                answers = by_id[public['id']]
                probabilities = answers['action']['probabilities']
                actions = sorted(valid_actions(episode['state']))
                total = validate_distribution(probabilities, actions)
                if policy == 'greedy':
                    action = max(actions, key=probabilities.__getitem__)
                    draw, chosen_probability = None, probabilities[action] / total
                else:
                    action, draw, chosen_probability = categorical(probabilities, rngs[episode['id']])
                if probabilities[action] <= 0:
                    raise ValueError('Executed action must have positive support under the original distribution')
                if validation_only:
                    episode['validation_engine_decisions'] += 1
                else:
                    episode['model_decisions'] += 1
                choices[index] = {'action': action, 'probabilities': copy.deepcopy(probabilities),
                                  'actor': 'jev_api',
                                  'draw': draw, 'sampling_probability': chosen_probability,
                                  'answers': answers, 'request_id': public['id'], 'batch_id': batch_id,
                                  'public_request_sha256': hashlib.sha256(canonical_json(public).encode()).hexdigest()}
        for index, chosen in choices.items():
            episode = states[index]
            before = episode['state']
            probabilities = chosen['probabilities']
            total = validate_distribution(probabilities, valid_actions(before))
            after = step(before, chosen['action'])
            if source_group_id(after) != episode['source_map_group_id'] or source_group_id(after) in train_groups:
                raise ValueError('Rollout escaped its held-out source map')
            optimal = solve(before)['optimal_actions']  # Evaluation only; never modifies a student choice.
            actual_optimal = chosen['action'] in optimal
            p_optimal = math.fsum(probabilities[action] for action in optimal) / total
            controller_expected = (p_optimal if policy in {'sample', 'random'} else float(actual_optimal))
            coordinate = tuple(after['position'])
            revisited = episode['_visits'][coordinate] > 0
            episode['_visits'][coordinate] += 1
            episode['steps'].append({
                'state': before, 'action': chosen['action'], 'next_state': after,
                'actor': chosen['actor'], 'controller': policy, 'probabilities': probabilities,
                'raw_probability_sum': total, 'distribution_argmax': max(sorted(probabilities), key=probabilities.__getitem__),
                'sample_uniform_draw': chosen['draw'], 'selected_action_probability': chosen['sampling_probability'],
                'p_optimal': p_optimal, 'controller_expected_optimal': controller_expected,
                'optimal_action': actual_optimal, 'revisited_position': revisited,
                'visits_to_destination_after_step': episode['_visits'][coordinate],
                'model_forward': None if chosen['actor'] == 'jev_api' else False, 'forced': chosen['actor'] == 'forced_legal_action',
                'training_map_overlap': False, 'answers': chosen['answers'], 'request_id': chosen['request_id'],
                'batch_id': chosen.get('batch_id'), 'public_request_sha256': chosen.get('public_request_sha256'),
            })
            episode['state'] = after
            if after['position'] == after['goal'] or len(episode['steps']) == episode['max_steps']:
                episode['active'] = False
        tick += 1
        if progress_every and tick % progress_every == 0:
            print(json.dumps({'policy': policy, 'tick': tick, 'active_episodes': sum(row['active'] for row in states),
                              'jev_api_requests': total_forwards}), flush=True)
    for episode in states:
        episode['final_state'] = episode.pop('state')
        episode.pop('active')
        visits = episode.pop('_visits')
        n = len(episode['steps'])
        success = episode['final_state']['position'] == episode['final_state']['goal']
        episode.update(success=success, outcome='goal' if success else 'horizon_exhausted', steps_count=n,
                       path_efficiency=episode['shortest_path_length'] / n if success else 0.0,
                       steps_to_goal=n if success else None, unique_positions_visited=len(visits),
                       revisit_steps=sum(row['revisited_position'] for row in episode['steps']),
                       repeated_visit_rate=sum(row['revisited_position'] for row in episode['steps']) / n,
                       source_map_training_overlap=False)
    summaries = {}
    for split in sorted({episode['split'] for episode in states}):
        group = [episode for episode in states if episode['split'] == split]
        decisions = [transition for episode in group for transition in episode['steps'] if not transition['forced']]
        steps_count = sum(episode['steps_count'] for episode in group)
        summaries[split] = {
            'episodes': len(group), 'distinct_source_maps': len({row['source_map_group_id'] for row in group}),
            'outcomes': dict(Counter(row['outcome'] for row in group)),
            'completion_rate': sum(row['success'] for row in group) / len(group),
            'mean_path_efficiency': sum(row['path_efficiency'] for row in group) / len(group),
            'total_steps': steps_count, 'mean_steps': steps_count / len(group),
            'nonforced_decisions': len(decisions), 'model_decisions': sum(row['model_decisions'] for row in group),
            'forced_decisions': sum(row['forced_decisions'] for row in group),
            'actual_optimal_action_rate': sum(row['optimal_action'] for row in decisions) / len(decisions) if decisions else None,
            'mean_p_optimal': math.fsum(row['p_optimal'] for row in decisions) / len(decisions) if decisions else None,
            'mean_controller_expected_optimal': math.fsum(row['controller_expected_optimal'] for row in decisions) / len(decisions) if decisions else None,
            'step_weighted_repeated_visit_rate': sum(row['revisit_steps'] for row in group) / steps_count,
            'episode_mean_repeated_visit_rate': sum(row['repeated_visit_rate'] for row in group) / len(group),
            'training_source_map_overlap': 0,
        }
    return {
        'schema_version': 'nanojev-jev-live-navigation-v1', 'policy': policy, 'seed': seed,
        'student_measurement': False, 'validation_only': validation_only,
        'episodes': states, 'summary': summaries, 'batches': batches, 'parallel_batches': batch_examples,
        'execution': {'forward_passes': None, 'teacher_calls': total_forwards, 'autoregressive_decode_steps': None,
                      'end_to_end_inference_seconds': inference_seconds,
                      'engine': 'jev_live_api'},
        'protocol': {'temperature': 1.0, 'horizon': '2*size^2', 'all_successes_and_failures_retained': True,
                     'candidate_order': 'lexicographic action IDs; no shortest-path information',
                     'greedy_tie_break': 'lexicographically first maximum',
                     'sampling': 'categorical from normalized rounded Jev action probabilities; native values and sums retained in answers.action',
                     'rng': 'independent Random seeded by SHA256(global_seed, canonical_source_map_id, initial_state); forced steps consume no draw',
                     'rng_limit': 'Fixed per-episode draws; Jev outputs are newly measured in this comparison and exact-input cached with provenance. This is not API latency benchmarking.',
                     'revisit': 'destination previously visited in this episode, including the initial position; never used to change action selection',
                     'optimal_metrics': 'Nonforced decisions only; p_optimal is the original distribution mass on the exact BFS-optimal action set, while actual_optimal measures the executed action.',
                     'oracle_use': 'Only explicit oracle policy, cohort reachability, and post-decision evaluation; never a student fallback',
                     'jev_probability_semantics': 'sampling proxy = native rounded vector / native sum; no logits or latent probability recovery claimed',
                     'not_enabled': ['visit_penalty', 'epsilon_exploration', 'temperature_tuning', 'cycle_early_stop', 'oracle_student_fallback']},
    }
