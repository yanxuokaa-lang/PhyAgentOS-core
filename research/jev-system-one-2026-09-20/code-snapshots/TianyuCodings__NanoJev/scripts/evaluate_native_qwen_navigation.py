#!/usr/bin/env python3
"""Frozen original Qwen native-vocabulary navigation baseline; no project training or decoding."""
import argparse
from functools import partial
import hashlib
import json
import math
import os
from pathlib import Path
import time

from assemble_navigation_v3_views import render_view_request
from evaluate_navigation_v3 import canonical_json, hash_file, rollout, select_episodes, SEED

MODEL = 'Qwen/Qwen3-0.6B'
REVISION = 'c1899de289a04d12100db370d81485cdf75e47ca'
BACKEND = 'untrained_qwen_lm_option_logits'


def build_prompt(public):
    if not isinstance(public, dict) or not isinstance(public.get('state'), str):
        raise ValueError('Expected an explicit public state string')
    q = public['questions']['action']
    if q['type'] != 'choice' or not 2 <= len(q['criteria']) <= 4:
        raise ValueError('Native navigation baseline requires two to four offered actions')
    if not isinstance(q.get('instructions'), str) or not q['instructions']:
        raise ValueError('Missing action instructions')
    candidates = sorted(q['criteria'])
    if not all(isinstance(c, str) and isinstance(q['criteria'][c], str) and q['criteria'][c] for c in candidates):
        raise ValueError('Invalid candidate text')
    labels = {candidate: chr(65 + i) for i, candidate in enumerate(candidates)}
    options = '\n'.join(f"{labels[c]}: {c} — {q['criteria'][c]}" for c in candidates)
    prompt = (f"State:\n{public['state']}\n\nQuestion:\n{q['instructions']}\n\n"
              f"Options:\n{options}\n\nAnswer with only the option letter. Do not provide an explanation.")
    return prompt, labels


def prompt_ids(tokenizer, public, max_length):
    prompt, labels = build_prompt(public)
    ids = tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}], tokenize=True,
                                         add_generation_prompt=True, enable_thinking=False,
                                         return_dict=False)
    if not isinstance(ids, list) or not ids or not all(type(x) is int for x in ids):
        raise ValueError('Unexpected tokenizer chat-template output')
    if len(ids) > max_length:
        raise ValueError(f'Full native prompt requires {len(ids)} tokens, over explicit max_length={max_length}; no truncation')
    return ids, labels, prompt


def load_tokenizer():
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    from transformers import AutoTokenizer
    from huggingface_hub import snapshot_download
    snapshot = Path(snapshot_download(MODEL, revision=REVISION, local_files_only=True))
    if snapshot.name != REVISION:
        raise ValueError('Cached snapshot revision differs from the frozen requested revision')
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    token_ids = {}
    for label in 'ABCD':
        encoded = tokenizer.encode(label, add_special_tokens=False)
        if len(encoded) != 1 or tokenizer.decode(encoded) != label:
            raise ValueError(f'{label} is not exactly one reversible native-vocabulary token')
        token_ids[label] = encoded[0]
    if len(set(token_ids.values())) != 4:
        raise ValueError('Option letters do not have unique token IDs')
    return tokenizer, snapshot, token_ids


def preflight(episodes, tokenizer, snapshot, token_ids, max_length):
    lengths, ks, inputs = [], [], []
    for episode in episodes:
        public = render_view_request(episode['initial_state'], split=episode['split'], representation='coords')
        ids, labels, prompt = prompt_ids(tokenizer, public, max_length)
        assert list(labels) == sorted(public['questions']['action']['criteria'])
        assert set(labels.values()) == set('ABCD'[:len(labels)])
        lengths.append(len(ids));ks.append(len(labels))
        inputs.append({'id':episode['id'],'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                       'prompt_token_ids_sha256':hashlib.sha256(canonical_json(ids).encode()).hexdigest(),
                       'prompt_tokens':len(ids),'candidate_to_token':{c:{'text':v,'id':token_ids[v]} for c,v in labels.items()}})
    return {'schema_version':'openjev-native-qwen-preflight-v1','model':MODEL,'revision':REVISION,
            'cached_snapshot':str(snapshot),'token_ids':token_ids,'episodes':len(episodes),
            'max_prompt_tokens':max(lengths),'min_prompt_tokens':min(lengths),
            'K_values':sorted(set(ks)),'max_length':max_length,'truncation':False,'GPU_calls':0,
            'template':'Official cached tokenizer chat template; add_generation_prompt=True, enable_thinking=False. Static empty thinking delimiters, if present in the template, are prompt tokens, not generated reasoning.',
            'prompt_rule':'Complete public coords state, action instructions and all offered actions. A-D map to lexicographic action IDs. Output probabilities condition on the next token being one of these offered letters.',
            'inputs':inputs}


class NativeQwenPredictor:
    def __init__(self, tokenizer, snapshot, token_ids, max_length=512, precision='bf16', disable_native_triton=False):
        import torch
        from transformers import AutoModelForCausalLM
        if disable_native_triton:
            from torch._native import triton_utils
            triton_utils.deregister_op_overrides()
        if not torch.cuda.is_available():
            raise ValueError('This explicit baseline run requires the authorized CUDA device; no fallback')
        if precision == 'bf16' and not torch.cuda.is_bf16_supported():
            raise ValueError('Requested BF16 unsupported')
        torch.cuda.set_device(0)
        torch.backends.cuda.matmul.allow_tf32 = False
        self.torch, self.tokenizer, self.token_ids = torch, tokenizer, token_ids
        self.max_length, self.precision, self.calls = max_length, precision, 0
        self.model = AutoModelForCausalLM.from_pretrained(snapshot, local_files_only=True,
                      trust_remote_code=False, attn_implementation='sdpa', dtype=torch.float32).to('cuda:0').eval()
        self.model.config.use_cache = False
        if self.model.get_output_embeddings() is None:
            raise ValueError('Original native vocabulary output head unavailable')
        self.parameter_count = sum(p.numel() for p in self.model.parameters())

    def predict(self, payload, batch_questions=0, temperature=1.0):
        if batch_questions != 0 or temperature != 1.0:
            raise ValueError('Frozen protocol requires a single active-state batch and T=1')
        states = payload['states']
        if not states or len({s['id'] for s in states}) != len(states):
            raise ValueError('Each batch needs nonempty uniquely identified states')
        encoded = [prompt_ids(self.tokenizer, s, self.max_length) for s in states]
        torch = self.torch
        lengths = torch.tensor([len(e[0]) for e in encoded], device='cuda:0', dtype=torch.long)
        tokens = torch.full((len(states), int(lengths.max())), self.tokenizer.pad_token_id,
                            device='cuda:0', dtype=torch.long)
        for i, (ids, _, _) in enumerate(encoded):
            tokens[i, :len(ids)] = torch.tensor(ids, device='cuda:0')
        mask = torch.arange(tokens.shape[1], device='cuda:0')[None, :] < lengths[:, None]
        with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16, enabled=self.precision == 'bf16'):
            hidden = self.model.model(input_ids=tokens, attention_mask=mask, use_cache=False).last_hidden_state
            final = hidden[torch.arange(len(states), device='cuda:0'), lengths - 1]
            # Exact original LM output head at the last prompt position, no new parameters.
            logits = self.model.get_output_embeddings()(final).float()
        if not torch.isfinite(logits).all():
            raise RuntimeError('Nonfinite original vocabulary logits')
        self.calls += 1
        result = []
        for i, (state, (_, labels, prompt)) in enumerate(zip(states, encoded)):
            actions = list(labels)
            indices = [self.token_ids[labels[a]] for a in actions]
            offered = logits[i, indices]
            conditional = offered.softmax(-1).cpu().tolist()
            unconditional = (offered - logits[i].logsumexp(-1)).exp().cpu().tolist()
            probabilities = dict(zip(actions, conditional))
            details = {'type':'choice','choice':max(actions,key=probabilities.__getitem__),
                       'probabilities':probabilities,'backend':BACKEND,
                       'probability_semantics':'Next-token distribution conditional on an offered A-D token; not unconditional action probability or calibrated task success.',
                       'candidate_to_token':{a:{'text':labels[a],'id':indices[j]} for j,a in enumerate(actions)},
                       'native_option_logits':dict(zip(actions,offered.cpu().tolist())),
                       'native_option_unconditional_probs':dict(zip(actions,unconditional)),
                       'offered_token_mass':math.fsum(unconditional),
                       'prompt_tokens':len(encoded[i][0]),'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
            result.append({'id':state['id'],'answers':{'action':details}})
        return {'states':result,'temperature':{'value':1.0,'fitted':False},
                'execution':{'forward_passes':1,'network_model_calls':0,'autoregressive_decode_steps':0,
                             'backend':BACKEND,'engine':BACKEND,'native_vocabulary_projection':True,
                             'active_state_batch_size':len(states),'action_questions':len(states),
                             'auxiliary_questions_evaluated':0,'persistent_model_load_count':1,
                             'inference_call_index':self.calls,'precision':self.precision,
                             'max_prompt_tokens':int(lengths.max()),'generated_tokens':0}}


def relabel_result(result):
    result['student_measurement'] = False
    result['native_model_measurement'] = True
    result['backend'] = BACKEND
    result['execution']['engine'] = BACKEND
    result['execution']['generated_tokens'] = 0
    for episode in result['episodes']:
        for step in episode['steps']:
            if step['actor'] == 'student':
                step['actor'] = 'native_lm'
    result['protocol']['comparison_limits'] = [
        'Original Qwen checkpoint includes its upstream training, but no NanoJev/OpenJev project fine-tuning or new random head.',
        'Native model uses the complete action candidate set in one prompt, one action query per state; the decision student uses candidate paths and also returns Boolean/Score auxiliaries.',
        'Native probabilities condition on the next token being a mapped offered letter. The offered-token mass is recorded separately.',
        'Official chat formatting and A-D aliases may affect the baseline; this is one frozen prompt, not prompt-search-selected performance.',
        'Causal attention is used in one batched forward; no autoregressive token generation or sampled reasoning trajectory occurs.',
    ]
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data-dir',type=Path,default=Path('research/private_navigation_v3/eval_minimal'))
    ap.add_argument('--output-dir',type=Path,default=Path('research'))
    ap.add_argument('--max-length',type=int,default=512)
    ap.add_argument('--precision',choices=['bf16','fp32'],default='bf16')
    ap.add_argument('--disable-native-triton',action='store_true')
    ap.add_argument('--preflight-only',action='store_true')
    args=ap.parse_args()
    episodes, train_groups, cohort = select_episodes(args.data_dir,20)
    tokenizer,snapshot,token_ids=load_tokenizer()
    audit=preflight(episodes,tokenizer,snapshot,token_ids,args.max_length)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    audit.update(script_sha256=hash_file(__file__),cohort=cohort)
    (args.output_dir/'navigation_v3_native_qwen_preflight.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'preflight':{k:audit[k] for k in ['model','revision','token_ids','episodes','max_prompt_tokens','min_prompt_tokens','K_values','GPU_calls']}},ensure_ascii=False),flush=True)
    if args.preflight_only:return
    outputs={p:args.output_dir/f'navigation_v3_native_qwen_{p}.json' for p in ['greedy','sample']}
    if any(p.exists() for p in outputs.values()):
        raise ValueError('Refusing to overwrite a completed native baseline trajectory')
    started=time.perf_counter()
    engine=NativeQwenPredictor(tokenizer,snapshot,token_ids,args.max_length,args.precision,args.disable_native_triton)
    source_files=sorted(snapshot.glob('*.safetensors'))
    if not source_files:raise ValueError('No original cached safetensor artifacts to hash')
    provenance={'model':MODEL,'revision':REVISION,'original_weight_files_sha256':{p.name:hash_file(p) for p in source_files},
                'config_sha256':hash_file(snapshot/'config.json'),'model_training_steps_in_this_project':0,
                'head':'Original unchanged native vocabulary output embeddings; no learned or random project head.',
                'parameter_count':engine.parameter_count}
    summary={}
    for policy in ['greedy','sample']:
        result=rollout(episodes,policy,engine,partial(render_view_request,representation='coords'),train_groups,SEED,progress_every=12)
        result=relabel_result(result)
        result.update(name='untrained_qwen3_0.6b_native',cohort=cohort,representation='coords',
                      model_provenance=provenance,script_sha256=hash_file(__file__),
                      controller_script_sha256=hash_file(Path(__file__).with_name('evaluate_navigation_v3.py')),
                      renderer_sha256=hash_file(Path(__file__).with_name('assemble_navigation_v3_views.py')),
                      base_renderer_sha256=hash_file(Path(__file__).with_name('build_navigation_v3.py')))
        outputs[policy].write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
        summary[policy]={'summary':result['summary'],'execution':result['execution'],
                         'artifact':outputs[policy].name,'artifact_sha256':hash_file(outputs[policy])}
        print(json.dumps({'policy':policy,**summary[policy]},ensure_ascii=False),flush=True)
    aggregate={'schema_version':'openjev-navigation-v3-native-qwen-summary-v1','backend':BACKEND,
               'model_provenance':provenance,'cohort':cohort,'seed':SEED,'temperature':1.0,
               'precision':args.precision,'policies':summary,'end_to_end_seconds':time.perf_counter()-started,
               'peak_gpu_allocated_gb':engine.torch.cuda.max_memory_allocated()/1e9,
               'script_sha256':hash_file(__file__),'preflight_sha256':hash_file(args.output_dir/'navigation_v3_native_qwen_preflight.json')}
    (args.output_dir/'navigation_v3_native_qwen_summary.json').write_text(json.dumps(aggregate,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'complete':True,'end_to_end_seconds':aggregate['end_to_end_seconds'],'peak_gpu_allocated_gb':aggregate['peak_gpu_allocated_gb']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
