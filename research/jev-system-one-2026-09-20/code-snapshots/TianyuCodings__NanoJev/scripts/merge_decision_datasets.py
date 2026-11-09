#!/usr/bin/env python3
"""Merge already split local datasets without changing their split assignments."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def merge(inputs, output):
    rows, seen, groups, sources = [], set(), {}, []
    for name in inputs:
        file = Path(name); raw = file.read_bytes()
        sources.append({'path':str(file), 'sha256':hashlib.sha256(raw).hexdigest()})
        for line in raw.decode().splitlines():
            if not line.strip(): continue
            row = json.loads(line)
            if row['id'] in seen: raise ValueError('Duplicate record ID')
            seen.add(row['id'])
            group = row['metadata']['source_group_id']
            if group in groups and groups[group] != row['split']: raise ValueError('Cross-split source group')
            groups[group] = row['split']
            rows.append(row)
    order = {s:i for i,s in enumerate(['train','dev','calibration','test','ood'])}
    rows.sort(key=lambda r:(order[r['split']],r['family_id'],r['id']))
    text = ''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)
    output = Path(output); output.parent.mkdir(parents=True,exist_ok=True);output.write_text(text)
    manifest = {'schema_version':'openjev-merged-v2','sources':sources,'output_sha256':hashlib.sha256(text.encode()).hexdigest(),
                'states':len(rows),'questions':sum(len(r['questions']) for r in rows),'source_groups':len(groups),
                'split_states':dict(Counter(r['split'] for r in rows)),
                'split_family_states':dict(Counter(f"{r['split']}/{r['family_id']}" for r in rows)),
                'source_groups_overlap_between_splits':False, 'training_split_changed':False}
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',nargs='+',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(merge(a.inputs,a.output),indent=2))
