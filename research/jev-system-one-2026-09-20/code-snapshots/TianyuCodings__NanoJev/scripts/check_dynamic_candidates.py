#!/usr/bin/env python3
"""Check variable-size choice distributions in one trained FP32 forward.

No teacher calls, generation, training, or task-quality benchmark.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import time

import torch
import transformers
from safetensors.torch import load_file
from transformers import AutoConfig, AutoModel, AutoTokenizer

from train_toy_decisions import DecisionModel


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def build_examples(tokenizer):
    state = 'The customer requests deletion of personal data.'
    instructions = 'Choose the support queue responsible for this request.'
    unrelated = [
        'invoice payment disputes', 'parcel tracking', 'password resets',
        'hardware repair', 'software installation', 'product documentation',
        'subscription upgrades', 'sales quotations', 'printer maintenance',
        'office equipment returns', 'account balance inquiries', 'appointment scheduling',
    ]
    prefix = (
        tokenizer.encode(f'State:\n{state}\n', add_special_tokens=False)
        + tokenizer.encode(f'Question type: choice\nQuestion:\n{instructions}\n', add_special_tokens=False)
    )
    examples = []
    for k in [2, 5, 20, 64, 255]:
        ids = ['privacy'] + [f'queue_{i:03d}' for i in range(1, k)]
        texts = ['privacy: Personal data deletion and privacy requests.']
        texts += [f'{ids[i]}: Support queue {i}, handling {unrelated[(i-1) % len(unrelated)]} only.'
                  for i in range(1, k)]
        leaves = [prefix + tokenizer.encode(f'Candidate:\n{text}\nDecision:', add_special_tokens=False)
                  + [tokenizer.eos_token_id] for text in texts]
        examples.append({'id': f'dynamic_choice_k{k}', 'state_id': 'dynamic_privacy_state',
                         'qid': f'choice_k{k}', 'type': 'choice',
                         'candidate_ids': ids, 'candidate_texts': texts, 'leaf_tokens': leaves})
    return examples, {'state': state, 'instructions': instructions,
                      'candidate_definition': 'one privacy queue; remaining indexed queues cycle through twelve unrelated support topics',
                      'quality_evaluation': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--disable-native-triton', action='store_true')
    args = parser.parse_args()
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '7':
        raise RuntimeError('This check is authorized only with CUDA_VISIBLE_DEVICES=7')
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('Expected one visible, usable CUDA device')
    if not (args.run_dir / 'summary.json').is_file():
        raise RuntimeError('Training must be complete before checkpoint loading')
    if args.disable_native_triton:
        from torch._native import triton_utils
        triton_utils.deregister_op_overrides()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision('highest')
    training_config = json.loads((args.run_dir / 'config.json').read_text())
    tokenizer = AutoTokenizer.from_pretrained(args.run_dir / 'tokenizer', local_files_only=True)
    backbone_config = AutoConfig.from_pretrained(args.run_dir / 'backbone_config', local_files_only=True)
    backbone = AutoModel.from_config(backbone_config, dtype=torch.float32, attn_implementation='sdpa')
    model = DecisionModel(backbone, training_config['set_head'])
    checkpoint_path = args.run_dir / 'best.safetensors'
    checkpoint = load_file(str(checkpoint_path), device='cpu')
    model.load_state_dict(checkpoint, strict=True)
    del checkpoint
    model = model.cuda().eval()
    examples, fixture = build_examples(tokenizer)
    if max(len(path) for ex in examples for path in ex['leaf_tokens']) > training_config['max_length']:
        raise ValueError('Fixture exceeds configured token length; no silent truncation')
    calls = {'decision_model': 0, 'backbone': 0}

    def count_model(module, args):
        calls['decision_model'] += 1

    def count_backbone(module, args):
        calls['backbone'] += 1

    hooks = [model.register_forward_pre_hook(count_model), model.backbone.register_forward_pre_hook(count_backbone)]
    torch.cuda.synchronize()
    torch.cuda.empty_cache()
    baseline_allocated = torch.cuda.memory_allocated()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    with torch.inference_mode(), torch.autocast('cuda', enabled=False):
        logits, valid = model(examples, tokenizer.pad_token_id)
    torch.cuda.synchronize()
    elapsed_ms = (time.perf_counter() - started) * 1000
    peak_allocated = torch.cuda.max_memory_allocated()
    peak_reserved = torch.cuda.max_memory_reserved()
    for hook in hooks:
        hook.remove()
    rows = []
    for ex, z, mask in zip(examples, logits, valid):
        k = len(ex['candidate_ids'])
        values = z[:k].float().cpu()
        probabilities = values.softmax(-1)
        finite = bool(torch.isfinite(values).all() and torch.isfinite(probabilities).all())
        total = float(probabilities.double().sum())
        padded_mask_correct = bool(mask[:k].all() and not mask[k:].any())
        passed = finite and padded_mask_correct and abs(total-1) <= 1e-6
        rows.append({
            'question_id': ex['id'], 'k': k, 'probability_shape': list(probabilities.shape),
            'finite_logits_and_probabilities': finite, 'padded_valid_mask_correct': padded_mask_correct,
            'probability_sum_float64': total, 'probability_min': float(probabilities.min()),
            'probability_max': float(probabilities.max()), 'passed': passed,
            'candidate_ids': ex['candidate_ids'], 'logits': values.tolist(), 'probabilities': probabilities.tolist(),
        })
    report = {
        'schema': 'openjev-dynamic-candidates-check-v1',
        'timestamp_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'script_sha256': digest(__file__),
        'trainer_sha256': digest(Path(__file__).with_name('train_toy_decisions.py')),
        'checkpoint_sha256': digest(checkpoint_path), 'run_dir': str(args.run_dir),
        'model': training_config['model'], 'revision': training_config.get('resolved_model_revision'),
        'set_head': training_config['set_head'],
        'environment': {'torch': torch.__version__, 'transformers': transformers.__version__,
                        'gpu': torch.cuda.get_device_name(0), 'physical_gpu': 7,
                        'parameter_dtype': str(next(model.parameters()).dtype),
                        'output_dtype': str(logits.dtype), 'autocast_enabled': False,
                        'attention_backend': 'sdpa', 'tf32': False,
                        'native_triton_overrides_disabled': args.disable_native_triton},
        'fixture': fixture, 'questions': len(examples), 'states': 1,
        'candidate_paths': sum(len(ex['leaf_tokens']) for ex in examples),
        'total_unpadded_path_tokens': sum(len(path) for ex in examples for path in ex['leaf_tokens']),
        'max_path_tokens': max(len(path) for ex in examples for path in ex['leaf_tokens']),
        'combined_padded_output_shape': list(logits.shape),
        'actual_forward_calls': calls, 'autoregressive_decode_steps': 0,
        'prefix_sharing': False, 'tree_attention': False,
        'single_unwarmed_forward_ms_including_tensor_assembly': elapsed_ms,
        'gpu_allocated_before_forward_bytes': baseline_allocated,
        'gpu_peak_allocated_bytes': peak_allocated,
        'gpu_peak_increment_over_before_forward_bytes': peak_allocated - baseline_allocated,
        'gpu_peak_reserved_bytes': peak_reserved,
        'results': rows,
        'passed': all(row['passed'] for row in rows) and calls == {'decision_model': 1, 'backbone': 1},
        'scope': 'Dynamic output cardinality and normalized finite distributions only; no teacher, generation or quality benchmark. Larger unseen candidate sets may reduce decision quality.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'passed': report['passed'], 'output': str(args.output), 'calls': calls,
                      'candidate_paths': report['candidate_paths'], 'shape': report['combined_padded_output_shape'],
                      'gpu_peak_allocated_bytes': peak_allocated,
                      'results': [{key: value for key, value in row.items()
                                   if key not in ['candidate_ids', 'logits', 'probabilities']}
                                  for row in rows]}), flush=True)
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
