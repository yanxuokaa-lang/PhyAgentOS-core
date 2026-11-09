#!/usr/bin/env python3
"""Self-authored programmable decisions with explicit, independently known targets."""
import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

SPLITS = {'train': 200, 'dev': 32, 'calibration': 32, 'test': 64, 'ood': 32}
ROOMS = ['kitchen', 'bedroom', 'office', 'garage', 'living room', 'bathroom', 'attic', 'hall', 'garden', 'dining room', 'balcony', 'library']
DEVICES = ['lamp', 'fan', 'heater', 'speaker']
COLORS = ['red', 'blue', 'green', 'yellow', 'purple', 'white', 'black', 'orange', 'pink', 'brown', 'gray', 'cyan']


def record(family, split, index, state, questions, gold, probs, kind, facts):
    uid = f'{family}:{split}:{index}'
    return {'id': uid, 'state_id': uid, 'family_id': family, 'split': split,
            'state': state, 'questions': questions, 'gold': gold,
            'gold_probs': probs, 'gold_probs_kind': kind,
            'gold_label_kind': 'deterministic_truth' if kind == 'deterministic_truth' else 'unobserved',
            'metadata': {'source': 'self_authored_programmatic', 'license': 'CC0-1.0',
                         'source_group_id': facts.pop('source_group_id'),
                         'template_id': f'{family}:{split}', 'facts': facts}}


def onehot(keys, positive):
    return {str(k): float(k == positive) for k in keys}


def smart_home(split, i, facts, rng):
    room, device, command, authorized, occupancy, hour = facts
    # The held-out source group is the entire semantic configuration, independent of wording.
    source = 'home:' + json.dumps([room, device, authorized, occupancy], separators=(',', ':'))
    templates = {
        'train': 'Request: {command} the {device} in the {room}. Authorization={auth}; people present={people}; time={hour}:00.',
        'dev': 'Device command received: room {room}, device {device}, action {command}. Permission {auth}. Occupancy {people}. Hour {hour}.',
        'calibration': 'Control audit: {command} / {room} / {device}; authorized {auth}, occupancy {people}, hour {hour}.',
        'test': 'Home log: user wants the {room} {device} set to {command}; access={auth}; occupants={people}; clock={hour}:00.',
        'ood': '家庭控制记录：房间={room}，设备={device}，动作={command}；已授权={auth}，人数={people}，小时={hour}。',
    }
    state = templates[split].format(room=room, device=device, command=command,
                                    auth='yes' if authorized else 'no', people=occupancy, hour=hour)
    pairs = [(r, d) for r in ROOMS for d in DEVICES]
    target = (room, device)
    others = [x for x in pairs if x != target]
    rng.shuffle(others)
    candidates = [target] + others[:[1, 2, 4, 7, 11][i % 5]]
    rng.shuffle(candidates)
    criteria = {f'unit_{j}': f'{r} {d}' for j, (r, d) in enumerate(candidates)}
    action = f'unit_{candidates.index(target)}'
    allowed = authorized and not (device == 'heater' and occupancy == 0)
    risk = 2 if not authorized else 1 if device == 'heater' and occupancy == 0 else 0
    qs = {
        'device': {'type': 'choice', 'instructions': 'Select exactly the room and device named in the request. Ignore authorization and occupancy for this question.', 'criteria': criteria},
        'execute': {'type': 'boolean', 'instructions': 'Is execution allowed? Rule: authorization is required for every command; additionally any heater command requires at least one person present. Other devices do not require occupancy.'},
        'risk': {'type': 'score', 'instructions': 'Classify the control request using these mutually exclusive rules.', 'criteria': ['Authorized, and either not a heater or at least one person present', 'Authorized heater request with zero people present', 'Not authorized, regardless of device or occupancy']},
    }
    return record('smart_home_v2', split, i, state, qs,
                  {'device': action, 'execute': allowed, 'risk': risk},
                  {'device': onehot(criteria, action), 'execute': onehot(['false', 'true'], str(allowed).lower()), 'risk': onehot(range(3), risk)},
                  'deterministic_truth', {'source_group_id': source, 'configuration': facts})


def lookup(split, i, facts, rng):
    code, color, size, status, expedited = facts
    source = 'lookup:' + json.dumps(facts, separators=(',', ':'))
    prefixes = {'train': 'Product record', 'dev': 'Warehouse audit', 'calibration': 'Inventory review', 'test': 'Independent stock entry', 'ood': '库存记录'}
    state = f'{prefixes[split]}: item={code}; color={color}; size={size}; status={status}; expedited={expedited}.'
    specs = [(c, s) for c in COLORS for s in ['small', 'medium', 'large']]
    target = (color, size)
    others = [x for x in specs if x != target]
    rng.shuffle(others)
    chosen = [target] + others[:[1, 4, 7, 11, 19][i % 5]]
    rng.shuffle(chosen)
    criteria = {f'candidate_{j}': f'{c}, {s}' for j, (c, s) in enumerate(chosen)}
    match = f'candidate_{chosen.index(target)}'
    ready = status == 'packed'
    score = {'new': 0, 'picked': 1, 'packed': 2, 'shipped': 3}[status]
    qs = {'match': {'type': 'choice', 'instructions': 'Choose the candidate whose color AND size both match this item. Ignore item code and shipping status.', 'criteria': criteria},
          'ready': {'type': 'boolean', 'instructions': 'Is this item currently packed but not yet shipped? New, picked, and already shipped items do not qualify.'},
          'stage': {'type': 'score', 'instructions': 'Select the stage explicitly reported in the record; expedited shipping does not change the current stage.', 'criteria': ['New item, not picked', 'Picked, not packed', 'Packed, not shipped', 'Already shipped']}}
    return record('catalog_lookup_v2', split, i, state, qs, {'match': match, 'ready': ready, 'stage': score},
                  {'match': onehot(criteria, match), 'ready': onehot(['false', 'true'], str(ready).lower()), 'stage': onehot(range(4), score)},
                  'deterministic_truth', {'source_group_id': source, 'configuration': facts})


def chance(split, i, facts, rng):
    colors, counts, focus = facts
    from fractions import Fraction
    source = 'chance:' + json.dumps(sorted((c, str(Fraction(n, sum(counts)))) for c,n in zip(colors, counts)), separators=(',', ':'))
    total = sum(counts)
    probs = {color: count / total for color, count in zip(colors, counts)}
    prefix = {'train': 'Random-draw machine', 'dev': 'Sampling experiment', 'calibration': 'Probability review', 'test': 'Unobserved trial', 'ood': '随机抽样实验'}[split]
    state = f'{prefix}: exactly one ball is drawn uniformly from a bag. Counts: ' + ', '.join(f'{c}={n}' for c, n in zip(colors, counts)) + '. All possible colors are listed; the draw has NOT happened.'
    ordered = list(colors)
    rng.shuffle(ordered)
    criteria = {c: f'The sampled ball is {c}' for c in ordered}
    # Score describes a random event, not a rating of how certain the model is.
    groups = {c: j % 3 for j, c in enumerate(colors)}
    level_p = [sum(probs[c] for c in colors if groups[c] == j) for j in range(3)]
    levels = ['The drawn color is one of: ' + ', '.join(c for c in colors if groups[c] == j) if any(groups[c] == j for c in colors) else 'Impossible: this group contains no colors' for j in range(3)]
    qs = {'outcome': {'type': 'choice', 'instructions': 'Predict the unobserved random draw. Return the conditional probability of each candidate event given the bag. These events are mutually exclusive and exhaustive.', 'criteria': criteria},
          'focus': {'type': 'boolean', 'instructions': f'Will the unobserved draw produce a {focus} ball? Use the conditional probability given only this bag.'},
          'group': {'type': 'score', 'instructions': 'Predict which mutually exclusive group the unobserved sampled color belongs to. Probabilities are determined by the bag counts.', 'criteria': levels}}
    # There is no sampled observation, so do not invent a hard outcome label.
    return record('known_chance_v2', split, i, state, qs, {},
                  {'outcome': {c: probs[c] for c in ordered}, 'focus': {'false': 1-probs[focus], 'true': probs[focus]}, 'group': {str(j): p for j, p in enumerate(level_p)}},
                  'programmatic_conditional_distribution', {'source_group_id': source, 'counts': dict(zip(colors, counts)), 'focus': focus, 'observed_outcome': False})


def build(out, seed=20260917):
    import itertools
    rng = random.Random(seed)
    home = [(r, d, rng.choice(['on','off']), a, n, rng.randrange(24))
            for r,d,a,n in itertools.product(ROOMS, DEVICES, [False,True], range(4))]
    # Item code alone does not create a new semantic group: configurations below are unique already.
    inventory = [(f'SKU-{j:05}', *x) for j, x in enumerate(itertools.product(COLORS, ['small','medium','large'], ['new','picked','packed','shipped'], ['yes','no']))]
    # 288 lookup combinations: use balanced smaller split sizes, rather than duplicate labels under new IDs.
    counts_by_family = {'smart_home_v2': SPLITS, 'catalog_lookup_v2': {'train':160,'dev':24,'calibration':24,'test':48,'ood':32}, 'known_chance_v2': SPLITS}
    rng.shuffle(home); rng.shuffle(inventory)
    all_rows = {s: [] for s in SPLITS}
    for family, pool, render in [('smart_home_v2', home, smart_home), ('catalog_lookup_v2', inventory, lookup)]:
        offset = 0
        for split, count in counts_by_family[family].items():
            for i, facts in enumerate(pool[offset:offset+count]):
                all_rows[split].append(render(split, i, facts, rng))
            offset += count
    seen = set()
    for split, count in counts_by_family['known_chance_v2'].items():
        for i in range(count):
            while True:
                k = [3, 4, 5, 8, 12][i % 5]
                colors = rng.sample(COLORS, k)
                counts = [rng.randint(1, 9) for _ in colors]
                focus = rng.choice(colors)
                from fractions import Fraction
                group = json.dumps(sorted((c, str(Fraction(n, sum(counts)))) for c,n in zip(colors, counts)))
                if group not in seen:
                    seen.add(group); break
            all_rows[split].append(chance(split, i, (colors, counts, focus), rng))
    output = Path(out); output.mkdir(parents=True, exist_ok=True)
    source_splits = {}
    manifest = {'schema_version':'openjev-workflows-v2', 'seed':seed, 'source':'self_authored_programmatic', 'license':'CC0-1.0',
                'limitations':['Synthetic controlled tasks; not a representative sample of all Jev users.', 'OOD is Chinese task rendering with English field values; it is not a held-out task family.', 'Known-chance targets are analytic distributions; no realized outcomes were observed.'], 'splits':{}}
    for split, rows in all_rows.items():
        for row in rows:
            group = row['metadata']['source_group_id']
            if group in source_splits: raise ValueError('Duplicate semantic source group')
            source_splits[group] = split
        text = ''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows)
        (output/f'{split}.jsonl').write_text(text)
        manifest['splits'][split] = {'states':len(rows), 'questions':sum(len(r['questions']) for r in rows), 'families':dict(Counter(r['family_id'] for r in rows)), 'sha256':hashlib.sha256(text.encode()).hexdigest()}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir', default='research/private_workflows_v2'); p.add_argument('--seed', type=int, default=20260917)
    a = p.parse_args(); print(json.dumps(build(a.output_dir, a.seed), indent=2))
