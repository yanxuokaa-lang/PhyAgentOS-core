#!/usr/bin/env python3
"""Exercise the actual local inference HTTP process twice and preserve its outputs."""
import argparse
import json
from pathlib import Path
import urllib.request


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',default='http://127.0.0.1:8765')
    p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();source=json.loads(Path(a.input).read_text())
    payload={'states':[{k:s[k] for k in ['id','state','questions']} for s in source['states'][:3]]}
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));responses=[]
    with opener.open(a.url+'/api/health',timeout=10) as response:health=json.load(response)
    for _ in range(2):
        req=urllib.request.Request(a.url+'/api/evaluate',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with opener.open(req,timeout=120) as response:responses.append(json.load(response))
    for result in responses:
        ex=result['execution'];assert ex['forward_passes']==1 and ex['autoregressive_decode_steps']==0 and ex['network_model_calls']==0 and ex['persistent_model_load_count']==1
        assert len(result['states'])==len(payload['states'])
    assert responses[1]['execution']['inference_call_index']==responses[0]['execution']['inference_call_index']+1
    delta=[]
    for one,two in zip(responses[0]['states'],responses[1]['states']):
        assert one['id']==two['id']
        for qid,answer in one['answers'].items():
            other=two['answers'][qid]['probabilities'];delta.extend(abs(v-other[k]) for k,v in answer['probabilities'].items())
    out={'passed':True,'health':health,'request':payload,'responses':responses,'max_repeated_probability_delta':max(delta)}
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':True,'output':a.output,'states':len(payload['states']),'max_repeated_probability_delta':max(delta),'executions':[r['execution'] for r in responses]}))
