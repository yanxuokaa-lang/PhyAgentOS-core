#!/usr/bin/env python3
"""Actual student-controlled rollouts, with independent random and oracle baselines."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import time

from game_tasks import valid_actions, step, solve, source_group_id, ttt_winner
from build_game_decisions import make_record


def select_episodes(data_dir, per_group):
    if type(per_group) is not int or per_group <= 0:
        raise ValueError('per_group must be a positive integer')
    selected = []
    for split in ['test','ood']:
        rows = [json.loads(l) for l in (Path(data_dir)/f'{split}.jsonl').read_text().splitlines()]
        counts = Counter()
        for row in rows:
            state = row['metadata']['environment_state']; game = state['game']
            # Explicit benchmark cohort: navigation starts must admit a solution.
            if game == 'grid_navigation' and not solve(state)['reachable']: continue
            if counts[game] >= per_group: continue
            counts[game] += 1
            selected.append({'id':row['id'],'game':game,'split':split,'initial_state':state})
        if any(counts[g] < per_group for g in ['tic_tac_toe','grid_navigation']):
            raise ValueError('Not enough prespecified episodes')
    return selected


def done(state):
    return state['position'] == state['goal'] if state['game']=='grid_navigation' else not valid_actions(state)


def rollout(episodes, policy, engine=None, seed=20260917):
    if policy not in {'student', 'random', 'oracle'} or (policy == 'student' and engine is None):
        raise ValueError('Unknown policy or missing student engine')
    rng = random.Random(seed)
    runs = []
    for episode in episodes:
        state = episode['initial_state']; oracle = solve(state)
        runs.append({**episode,'state':state,'steps':[], 'max_steps':2*state['size']**2 if episode['game']=='grid_navigation' else 9,
                     'student_player':state.get('player'), 'initial_oracle':oracle,
                     'active':True,'model_decisions':0,'forced_decisions':0,'opponent_forced_decisions':0})
    parallel_batches = []; inference_seconds = 0.0; total_forwards=0
    while any(r['active'] for r in runs):
        pending = []; selected = []
        choices = {}
        for i, r in enumerate(runs):
            if not r['active']: continue
            state = r['state']; actions = valid_actions(state)
            if done(state) or len(r['steps']) >= r['max_steps'] or not actions:
                r['active']=False; continue
            opponent = r['game']=='tic_tac_toe' and state['player'] != r['student_player']
            if opponent:
                # Fixed perfect opponent for every policy arm, not a student fallback.
                choices[i] = (sorted(solve(state)['optimal_actions'])[0],None,'minimax_opponent')
                r['opponent_forced_decisions'] += int(len(actions) == 1)
            elif len(actions)==1:
                choices[i] = (actions[0],None,'forced_legal_action');r['forced_decisions']+=1
            elif policy=='student':
                rec = make_record(state,r['split'],index=len(r['steps']),seed=seed)
                uid = f'episode_{i}_step_{len(r["steps"])}'
                public = {'id':uid,'state':rec['state'],'questions':rec['questions']}
                pending.append(public); selected.append(i)
            else:
                optimal = sorted(solve(state)['optimal_actions'])
                action = rng.choice(actions) if policy=='random' else optimal[0]
                p = {a:1/len(actions) if policy=='random' else float(a==action) for a in actions}
                choices[i]=(action,{'action':{'type':'choice','choice':action,'probabilities':p}},policy)
        if pending:
            before=time.perf_counter(); result=engine.predict({'states':pending}); inference_seconds+=time.perf_counter()-before
            returned_ids = [row['id'] for row in result['states']]
            if len(set(returned_ids)) != len(returned_ids) or set(returned_ids) != {row['id'] for row in pending}:
                raise ValueError('Student response must contain each requested state exactly once')
            execution = result['execution']
            if type(execution.get('forward_passes')) is not int or execution['forward_passes'] < 1:
                raise ValueError('Student predictions must report a real model forward')
            if execution.get('network_model_calls', 0) != 0 or execution.get('autoregressive_decode_steps', 0) != 0:
                raise ValueError('This benchmark requires local nongenerative student inference')
            total_forwards+=result['execution']['forward_passes']
            by_id={s['id']:s['answers'] for s in result['states']}
            if len(parallel_batches)<3:
                parallel_batches.append({'id':f'batch_{len(parallel_batches)}','execution':result['execution'],
                                         'states':[{**p,'answers':by_id[p['id']]} for p in pending]})
            for i,p in zip(selected,pending):
                answers=by_id[p['id']]
                action = answers['action']['choice']
                probabilities = answers['action']['probabilities']
                legal = valid_actions(runs[i]['state'])
                if not isinstance(probabilities, dict) or set(probabilities) != set(legal):
                    raise ValueError('Student action distribution must cover exactly the legal candidates')
                if any(type(value) not in {int, float} or not math.isfinite(value) or not 0 <= value <= 1
                       for value in probabilities.values()) or abs(math.fsum(probabilities.values()) - 1) > 1e-5:
                    raise ValueError('Invalid student action distribution')
                if action not in probabilities or probabilities[action] != max(probabilities.values()):
                    raise ValueError('Executed student action must be an argmax of its returned distribution')
                choices[i]=(action,answers,'student');runs[i]['model_decisions']+=1
        for i,(action,answers,actor) in choices.items():
            r=runs[i]; old=r['state'];new=step(old,action)
            oracle=solve(old)
            r['steps'].append({'state':old,'action':action,'probabilities':answers['action']['probabilities'] if answers else None,
                               'answers':answers,'actor':actor,'model_forward':actor=='student','forced':len(valid_actions(old))==1,
                               'optimal_action':action in oracle['optimal_actions'],'next_state':new})
            r['state']=new
            if done(new) or len(r['steps'])>=r['max_steps']:r['active']=False
    for r in runs:
        state=r.pop('state'); r.pop('active'); r['final_state']=state
        if r['game']=='grid_navigation':
            success=state['position']==state['goal'];r['outcome']='goal' if success else 'horizon_exhausted'
            r['success']=success;r['shortest_path_length']=r['initial_oracle']['distance']
            r['path_efficiency']=r['shortest_path_length']/len(r['steps']) if success else 0.0
        else:
            winner=ttt_winner(state['board']);value=0 if winner is None else (1 if winner==r['student_player'] else -1)
            r['outcome']={-1:'loss',0:'draw',1:'win'}[value];r['outcome_value']=value
            r['preserved_initial_minimax_value']=value>=r['initial_oracle']['value']
        r['steps_count']=len(r['steps'])
    summaries={}
    for game in ['grid_navigation','tic_tac_toe']:
        for split in ['test','ood']:
            rows=[r for r in runs if r['game']==game and r['split']==split]
            steps=[s for r in rows for s in r['steps'] if s['actor'] not in ['minimax_opponent','forced_legal_action']]
            metric={'episodes':len(rows),'outcomes':dict(Counter(r['outcome'] for r in rows)),
                    'choice_decisions':len(steps),'optimal_action_rate':sum(s['optimal_action'] for s in steps)/len(steps) if steps else None,
                    'forced_decisions':sum(r['forced_decisions'] for r in rows),
                    'opponent_forced_decisions':sum(r['opponent_forced_decisions'] for r in rows),
                    'model_decisions':sum(r['model_decisions'] for r in rows)}
            if game=='grid_navigation':metric.update(success_rate=sum(r['success'] for r in rows)/len(rows),mean_path_efficiency=sum(r['path_efficiency'] for r in rows)/len(rows))
            else:
                metric['preserved_minimax_value_rate']=sum(r['preserved_initial_minimax_value'] for r in rows)/len(rows)
                metric['by_initial_minimax_value'] = {}
                for value in [-1, 0, 1]:
                    group = [r for r in rows if r['initial_oracle']['value'] == value]
                    metric['by_initial_minimax_value'][str(value)] = {
                        'episodes': len(group), 'outcomes': dict(Counter(r['outcome'] for r in group)),
                        'preserved_minimax_value_rate': sum(r['preserved_initial_minimax_value'] for r in group)/len(group) if group else None,
                    }
                nonlosing = [r for r in rows if r['initial_oracle']['value'] >= 0]
                metric['preserved_nonlosing_initial_value_rate'] = sum(r['preserved_initial_minimax_value'] for r in nonlosing)/len(nonlosing) if nonlosing else None
                metric['mean_initial_minus_realized_value'] = sum(r['initial_oracle']['value']-r['outcome_value'] for r in rows)/len(rows)
            summaries[f'{split}/{game}']=metric
    return {'episodes':runs,'summary':summaries,'parallel_batches':parallel_batches,
            'execution':{'autoregressive_decode_steps':0,'teacher_calls':0,'forward_passes':total_forwards,'end_to_end_inference_seconds':inference_seconds}}


def annotate_training_overlap(result, train_groups):
    """Audit actual visited states, separating policy choices and opponent turns."""
    for episode in result['episodes']:
        episode['initial_state_overlaps_train_group'] = source_group_id(episode['initial_state']) in train_groups
        for transition in episode['steps']:
            transition['training_group_overlap'] = source_group_id(transition['state']) in train_groups
        episode['rollout_states_overlapping_train_groups'] = sum(s['training_group_overlap'] for s in episode['steps'])
        episode['model_decision_states_overlapping_train_groups'] = sum(s['training_group_overlap'] and s['actor'] == 'student' for s in episode['steps'])
        episode['policy_choice_states_overlapping_train_groups'] = sum(s['training_group_overlap'] and s['actor'] not in {'minimax_opponent', 'forced_legal_action'} for s in episode['steps'])
    for name, summary in result['summary'].items():
        split, game = name.split('/')
        selected = [r for r in result['episodes'] if r['split'] == split and r['game'] == game]
        summary['training_overlap'] = {
            'initial_states': sum(r['initial_state_overlaps_train_group'] for r in selected),
            'episodes_visiting_train_group': sum(r['rollout_states_overlapping_train_groups'] > 0 for r in selected),
            'visited_preaction_states': sum(r['rollout_states_overlapping_train_groups'] for r in selected),
            'policy_choice_states': sum(r['policy_choice_states_overlapping_train_groups'] for r in selected),
            'model_decision_states': sum(r['model_decision_states_overlapping_train_groups'] for r in selected),
        }
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-dir',required=True);p.add_argument('--checkpoint-dir');p.add_argument('--name',default='student')
    p.add_argument('--policy',choices=['student','random','oracle'],default='student');p.add_argument('--per-group',type=int,default=20)
    p.add_argument('--output',required=True);p.add_argument('--disable-native-triton',action='store_true');p.add_argument('--precision',choices=['fp32','bf16'],default='bf16')
    a=p.parse_args();engine=None
    if a.policy=='student':
        if not a.checkpoint_dir:raise ValueError('Student requires local checkpoint')
        from predict_toy_decisions import DecisionPredictor
        engine=DecisionPredictor(a.checkpoint_dir,disable_native_triton=a.disable_native_triton,precision=a.precision)
    episodes=select_episodes(a.data_dir,a.per_group)
    result=rollout(episodes,a.policy,engine)
    train_groups={r['metadata']['source_group_id'] for r in map(json.loads,(Path(a.data_dir)/'train.jsonl').read_text().splitlines())}
    annotate_training_overlap(result, train_groups)
    result.update(name=a.name,policy=a.policy,checkpoint_sha256=hashlib.file_digest(open(Path(a.checkpoint_dir)/'best.safetensors','rb'),'sha256').hexdigest() if a.checkpoint_dir else None,
                  cohort={'selection':'First N reachable navigation and first N tic-tac-toe episodes per frozen test/OOD split, before inference.',
                          'per_group':a.per_group,'opponent':'perfect minimax for every tic-tac-toe policy arm',
                          'initial_episode_ids':[episode['id'] for episode in episodes],
                          'initial_states_sha256':hashlib.sha256(json.dumps(episodes,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                          'forced_decision_definition':'forced_decisions counts only policy-controlled single-legal steps; opponent_forced_decisions counts the corresponding opponent steps.',
                          'minimax_value_note':'Preserving an initially losing value (-1) is automatic; consult the initial-value strata and nonlosing-value metric.',
                          'navigation_horizon':'2*size^2','limitations':['Tic-tac-toe rollouts may enter training board groups; counts are reported per episode.', 'Navigation maps remain held out throughout each rollout.', 'No oracle fallback in student decisions. Forced single legal actions are recorded separately.']})
    output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(output),'summary':result['summary'],'execution':result['execution']}))


if __name__=='__main__':main()
