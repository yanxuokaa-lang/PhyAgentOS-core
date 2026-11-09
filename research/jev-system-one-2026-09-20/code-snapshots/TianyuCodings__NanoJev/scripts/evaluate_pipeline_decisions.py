#!/usr/bin/env python3
"""Separate teacher imitation, deterministic correctness, analytic probabilities and policy quality."""
import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


LOG_FLOOR = 1e-12
GOLD_KINDS = {'deterministic_truth', 'optimal_action_policy', 'programmatic_conditional_distribution'}


def probability_vector(value, ids, name):
    if isinstance(value, dict):
        if set(value) != set(ids):
            raise ValueError(f'{name}: candidate mapping mismatch')
        value = [value[key] for key in ids]
    if not isinstance(value, list) or len(value) != len(ids):
        raise ValueError(f'{name}: probability vector length mismatch')
    if any(type(x) not in {int, float} or not math.isfinite(x) or not 0 <= x <= 1 for x in value):
        raise ValueError(f'{name}: invalid probability')
    if abs(math.fsum(value) - 1) > 1e-6:
        raise ValueError(f'{name}: non-unit probability vector')
    return value


def prepare_row(row):
    row = dict(row)
    for field in ['id', 'split', 'family_id', 'type']:
        if not isinstance(row.get(field), str) or not row[field]:
            raise ValueError(f'Missing or invalid prediction field: {field}')
    if row['type'] not in {'boolean', 'choice', 'score'}:
        raise ValueError('Unknown question type')
    ids = row.get('candidate_ids')
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('Candidate IDs must be unique nonempty strings')
    if row['type'] == 'boolean' and ids != ['false', 'true']:
        raise ValueError('Boolean candidate order must be false,true')
    row['student_probs'] = probability_vector(row.get('student_probs'), ids, 'student')
    if row.get('student_logits') is not None:
        logits = row['student_logits']
        if not isinstance(logits, list) or len(logits) != len(ids) or any(
                type(x) not in {int, float} or not math.isfinite(x) for x in logits):
            raise ValueError('Invalid student logits')
        maximum = max(logits)
        weights = [math.exp(value - maximum) for value in logits]
        total = math.fsum(weights)
        if max(abs(weight/total - probability) for weight, probability in zip(weights, row['student_probs'])) > 1e-5:
            raise ValueError('Reported student probabilities do not match the stored logits')
    q = row.get('gold_probs')
    if q is None:
        q = row.get('gold_distribution_probs')
    kind = row.get('gold_probs_kind')
    if q is None and row.get('gold_index') is not None:
        if kind in {'optimal_action_policy', 'programmatic_conditional_distribution'} or row.get('gold_label_kind') == 'unobserved':
            raise ValueError('Cannot replace a policy/analytic/unobserved target with a representative hard label')
        index = row['gold_index']
        if type(index) is not int or not 0 <= index < len(ids):
            raise ValueError('Hard gold index is out of range')
        q, kind = [float(i == index) for i in range(len(ids))], 'deterministic_truth'
    if q is not None:
        q = probability_vector(q, ids, 'gold')
        # Legacy hard-only records may carry a derived one-hot distribution.
        if kind is None and row.get('gold_index') is not None and row.get('gold_probs') is None:
            kind = 'deterministic_truth'
        if kind not in GOLD_KINDS:
            raise ValueError('Gold distribution requires an explicit supported target kind')
        if kind == 'deterministic_truth' and (sum(x == 1 for x in q) != 1 or sum(x != 0 for x in q) != 1):
            raise ValueError('Deterministic truth must be one-hot')
    row['_gold'], row['_kind'] = q, kind
    teacher = row.get('teacher_probs')
    row['_teacher'] = None
    row['_teacher_status'] = 'missing'
    if teacher is not None:
        try:
            row['_teacher'] = probability_vector(teacher, ids, 'teacher')
            row['_teacher_status'] = 'usable_rounded_proxy'
        except ValueError as exc:
            row['_teacher_status'] = f'quarantined: {exc}'
    elif row.get('teacher_target_error'):
        row['_teacher_status'] = f"quarantined: {row['teacher_target_error']}"
    return row


def divergence(q, p):
    if len(q) != len(p) or abs(math.fsum(q)-1) > 1e-6 or abs(math.fsum(p)-1) > 1e-6:
        raise ValueError('Mismatched or non-unit probability vectors')
    if any(not math.isfinite(x) or x < 0 or x > 1 for x in q+p):
        raise ValueError('Invalid probability')
    ce = -sum(a*math.log(max(b, LOG_FLOOR)) for a,b in zip(q,p) if a)
    entropy = -sum(a*math.log(a) for a in q if a)
    return {'tv':sum(abs(a-b) for a,b in zip(q,p))/2, 'kl_target_to_student':max(0.0, ce-entropy),
            'cross_entropy':ce, 'squared_probability_error':sum((a-b)**2 for a,b in zip(q,p)),
            'expected_brier':sum(b*b for b in p)-2*sum(a*b for a,b in zip(q,p))+1,
            'log_floor_affected_target_mass':sum(a for a,b in zip(q,p) if b < LOG_FLOOR),
            'zero_predicted_mass_on_target_support':sum(a for a,b in zip(q,p) if b == 0)}


def mean(rows, key):
    values = [r[key] for r in rows if key in r]
    return sum(values)/len(values) if values else None


def summarize(rows):
    rows = [row if '_gold' in row else prepare_row(row) for row in rows]
    stats = []
    for row in rows:
        p = row['student_probs']; best = max(range(len(p)), key=p.__getitem__)
        q, kind = row['_gold'], row['_kind']
        s = {'id':row['id']}
        teacher = row['_teacher']
        if teacher is not None:
            s.update({f'teacher_{k}':v for k,v in divergence(teacher,p).items()})
            s['teacher_argmax_agreement'] = float(best == max(range(len(p)), key=teacher.__getitem__))
        if q is not None:
            s.update({f'gold_{k}':v for k,v in divergence(q,p).items()})
            if kind == 'optimal_action_policy':
                s['optimal_action_accuracy'] = float(q[best] > 0)
                s['optimal_action_mass'] = sum(pi for qi,pi in zip(q,p) if qi > 0)
            elif kind == 'deterministic_truth':
                s['deterministic_accuracy'] = float(q[best] > 0.999999)
                s['confidence'] = p[best]; s['target_top_correctness'] = q[best]
            elif kind == 'programmatic_conditional_distribution':
                s['analytic_confidence'] = p[best]; s['analytic_top_probability'] = q[best]
        stats.append(s)
    names = sorted({k for s in stats for k in s} - {'id','confidence','target_top_correctness','analytic_confidence','analytic_top_probability'})
    result = {'questions':len(rows), **{name:mean(stats,name) for name in names},
              'teacher_eligible':sum('teacher_tv' in s for s in stats),
              'deterministic_questions':sum('deterministic_accuracy' in s for s in stats),
              'policy_questions':sum('optimal_action_accuracy' in s for s in stats),
              'analytic_questions':sum('analytic_confidence' in s for s in stats)}
    result['teacher_target_status_counts'] = dict(Counter(row['_teacher_status'] for row in rows))
    for label, ck, qk in [('deterministic_ece','confidence','target_top_correctness'), ('analytic_expected_ece','analytic_confidence','analytic_top_probability')]:
        eligible = [s for s in stats if ck in s]
        bins = [[] for _ in range(10)]
        for s in eligible: bins[min(9,int(s[ck]*10))].append(s)
        result[label] = sum(len(b)*abs(mean(b,ck)-mean(b,qk)) for b in bins if b)/len(eligible) if eligible else None
    return result


def evaluate(rows):
    if not rows:
        raise ValueError('No prediction rows to evaluate')
    rows = [prepare_row(row) for row in rows]
    seen, state_splits = set(), {}
    for row in rows:
        key = (row['split'], row['id'])
        if key in seen:
            raise ValueError(f'Duplicate prediction row: {key}')
        seen.add(key)
        state_id = row.get('state_id')
        if state_id is not None:
            if state_id in state_splits and state_splits[state_id] != row['split']:
                raise ValueError(f'State appears in multiple evaluation splits: {state_id}')
            state_splits[state_id] = row['split']
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row['split'],row['family_id'],row['type'])].append(row)
    return {'schema_version':'openjev-pipeline-metrics-v2',
            'definitions':{'teacher':'KL/TV against the explicitly usable rounded teacher proxy; non-unit teacher vectors are excluded only here.',
                           'gold':'KL/TV against independent gold distribution; optimal-action targets describe a policy, not event uncertainty.',
                           'deterministic_ece':'10-bin top-label ECE, only deterministic truth questions',
                           'analytic_expected_ece':'10-bin difference between predicted confidence and known conditional probability of its selected event; no sampled outcomes.',
                           'expected_brier':'sum(p^2)-2 dot(q,p)+1, expectation under known q',
                           'log_floor':f'CE/KL use log(max(p,{LOG_FLOOR})); report affected target mass, so infinite true losses are explicitly capped. Tiny negative KL from arithmetic is clamped to zero.',
                           'policy_brier':'For optimal-action targets, expected Brier is only a loss under the specified reference policy, not event calibration.',
                           'weighting':'Question mean; report family/type breakdown before considering any pooled value.',
                           'selection':'This evaluation does not fit temperatures or select checkpoints.'},
            'splits':{s:summarize([r for r in rows if r['split']==s]) for s in sorted({r['split'] for r in rows})},
            'by_family_type':{f'{s}/{f}/{t}':summarize(g) for (s,f,t),g in sorted(grouped.items())}}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();rows=[json.loads(l) for l in Path(a.input).read_text().splitlines() if l.strip()]
    Path(a.output).write_text(json.dumps(evaluate(rows),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':a.output,'questions':len(rows)}))
