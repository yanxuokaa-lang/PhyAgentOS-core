#!/usr/bin/env python3
"""Measure real Jev on the frozen V3 maps through a credential-isolated Node worker."""
import argparse
from functools import partial
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from assemble_navigation_v3_views import render_view_request
from evaluate_navigation_v3 import select_episodes,SEED,hash_file
from rollout_jev_navigation import rollout_jev


class JevEngine:
    def __init__(self,journal_dir,budget):
        self.stderr=(journal_dir/'worker_stderr.log').open('a')
        self.worker=subprocess.Popen(['node','--env-file=.env','scripts/jev_navigation_worker.mjs',
            '--journal-dir',str(journal_dir),'--budget-usd',str(budget),'--concurrency','8'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,text=True,bufsize=1)

    def predict(self,payload,batch_questions=0,temperature=1.):
        assert batch_questions==0 and temperature==1
        self.worker.stdin.write(json.dumps(payload,ensure_ascii=False)+'\n');self.worker.stdin.flush()
        line=self.worker.stdout.readline()
        if not line:raise RuntimeError('Jev worker ended without a measurement')
        response=json.loads(line)
        if 'error' in response:raise RuntimeError(response['error'])
        return response

    def close(self):
        self.worker.stdin.close()
        try:self.worker.wait(timeout=10)
        except subprocess.TimeoutExpired:self.worker.terminate();self.worker.wait(timeout=10)
        self.stderr.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',default='research/private_navigation_v3')
    p.add_argument('--journal-dir',type=Path,default=Path('research/private_nanojev_live_api'))
    p.add_argument('--output-dir',type=Path,default=Path('research'))
    p.add_argument('--budget-usd',type=float,default=2.)
    args=p.parse_args()
    episodes,groups,cohort=select_episodes(args.data_dir,20)
    args.journal_dir.mkdir(parents=True,exist_ok=True);args.output_dir.mkdir(parents=True,exist_ok=True)
    outputs={policy:args.output_dir/f'navigation_v3_jev_api_{policy}.json' for policy in ('greedy','sample')}
    if any(path.exists() for path in outputs.values()):raise ValueError('Comparison results exist; refusing overwrite')
    engine=JevEngine(args.journal_dir,args.budget_usd)
    try:
        for policy,path in outputs.items():
            result=rollout_jev(episodes,policy,engine=engine,renderer=partial(render_view_request,representation='coords'),
                train_groups=groups,seed=SEED,progress_every=12)
            journal=[json.loads(line) for line in (args.journal_dir/'calls.jsonl').read_text().splitlines() if line]
            successful=[row for row in journal if row['status']=='succeeded']
            result.update(name='Jev API · '+('贪心' if policy=='greedy' else '概率采样'),role='jev',cohort=cohort,
                representation='coords',model='typesafe-ai/jev',script_sha256=hash_file(__file__),
                renderer_sha256=hash_file('scripts/assemble_navigation_v3_views.py'),
                api_calls=[{k:row[k] for k in ['id','input_sha256','input','model','native_probs','rounding','cost_usd','started_at','finished_at','response_sha256']} for row in successful],
                api_measurement_note='Calls are newly measured for this comparison. Exact rendered inputs may reuse this run journal; no historical training labels are read.',
                cumulative_api_cost_usd=sum(row['cost_usd'] for row in successful))
            path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
            print(json.dumps({'output':str(path),'summary':result['summary'],'api_requests_this_controller':result['execution']['teacher_calls'],
                'cumulative_api_cost_usd':result['cumulative_api_cost_usd']},ensure_ascii=False),flush=True)
    finally:engine.close()


if __name__=='__main__':main()
