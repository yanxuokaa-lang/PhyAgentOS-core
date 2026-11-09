#!/usr/bin/env python3
"""Package actual evaluated episodes; never synthesize replacement predictions."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--models',nargs='+',required=True)
    p.add_argument('--parallel',nargs='*',default=[]);p.add_argument('--output',default='web/demo_results.json')
    a=p.parse_args();models=[]
    for file in a.models:
        record=json.loads(Path(file).read_text())
        if not record.get('episodes') or not record.get('summary'):raise ValueError('Only complete actual rollout results are accepted')
        if record.get('policy') in {'student','greedy','sample'} and not record.get('checkpoint_sha256'):raise ValueError('Student must record checkpoint hash')
        record['source_artifact']=Path(file).name
        models.append(record)
    unassigned=[]
    for file in a.parallel:
        batch=json.loads(Path(file).read_text())
        matches=[m for m in models if batch.get('checkpoint_sha256') and m.get('checkpoint_sha256')==batch['checkpoint_sha256']]
        if matches:
            # A checkpoint may have several controllers. The same independently
            # captured forward is valid for each; it is not a new rollout batch.
            for model in matches:
                attached={**batch,'model':model['name']}
                model['parallel_batches']=[attached]+model.get('parallel_batches',[])
        else:unassigned.append(batch)
    result={'schema_version':'openjev-reader-demo-v2','generated_at':datetime.now(timezone.utc).isoformat(),
            'models':models,'parallel_batches':unassigned,
            'sources':[{'title':'官方 Jev：文字状态 Doom 与 Wikiracing 演示','url':'https://typesafe.ai/blog/introducing-system-one-models-and-jev'},
                       {'title':'创始人 Doom 发布帖','url':'https://x.com/CompleteSkeptic/status/2099925687465570372'},
                       {'title':'第三方 jevlike：游戏 trace 与失败披露','url':'https://github.com/vinnylarouge/jevlike#demo'}],
            'scope':'Independent text-state grid and tic-tac-toe experiments inspired by public demos; not a reproduced Doom model or proprietary RLCD recipe.'}
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(path),'models':len(models),'episodes':sum(len(m['episodes']) for m in models)}))
