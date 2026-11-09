#!/usr/bin/env python3
"""Capture one actual forward over different held-out task families, without labels."""
import argparse
import hashlib
import json
from pathlib import Path
from predict_toy_decisions import DecisionPredictor


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--checkpoint-dir',required=True)
    p.add_argument('--output',required=True);p.add_argument('--disable-native-triton',action='store_true')
    a=p.parse_args();selected={}
    for row in map(json.loads,Path(a.input).read_text().splitlines()):
        if row['split']=='test':selected.setdefault(row['family_id'],{k:row[k] for k in ['id','state','questions']})
    engine=DecisionPredictor(a.checkpoint_dir,disable_native_triton=a.disable_native_triton)
    result=engine.predict({'states':list(selected.values())})
    answers={s['id']:s['answers'] for s in result['states']}
    with (Path(a.checkpoint_dir)/'best.safetensors').open('rb') as weights:
        checkpoint_sha256=hashlib.file_digest(weights,'sha256').hexdigest()
    output={'id':'mixed_heldout_families','model':Path(a.checkpoint_dir).name,'checkpoint_sha256':checkpoint_sha256,'execution':result['execution'],
            'states':[{**s,'answers':answers[s['id']]} for s in selected.values()],
            'selection':'First test record of each family, fixed without inspecting predictions.'}
    Path(a.output).write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':a.output,'execution':result['execution']}))
