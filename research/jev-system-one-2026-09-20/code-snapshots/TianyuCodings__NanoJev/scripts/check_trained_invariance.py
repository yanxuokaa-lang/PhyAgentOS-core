#!/usr/bin/env python3
"""Audit trained DecisionModel invariance and warm-GPU latency, without updates.

Uses only local artifacts and test data. Inference repeats full candidate paths;
it does not implement tree attention or prefix KV sharing.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time

import torch
import transformers
from safetensors.torch import load_file
from transformers import AutoConfig, AutoModel, AutoTokenizer

from train_toy_decisions import DecisionModel, load_examples


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def percentile(values, fraction):
    ordered = sorted(values)
    location = (len(ordered) - 1) * fraction
    low, high = math.floor(location), math.ceil(location)
    return ordered[low] + (ordered[high] - ordered[low]) * (location - low)


@torch.inference_mode()
def predict(model, examples, pad_token, *, bf16=True):
    with torch.autocast('cuda', dtype=torch.bfloat16, enabled=bf16):
        logits, _ = model(examples, pad_token)
    rows = {}
    for ex, row in zip(examples, logits):
        k = len(ex['candidate_ids'])
        z = row[:k].float().cpu()
        if not torch.isfinite(z).all():
            raise RuntimeError(f"Nonfinite logits: {ex['id']}")
        rows[ex['id']] = {
            'type': ex['type'], 'state_id': ex['state_id'],
            'candidate_ids': ex['candidate_ids'],
            'logits': dict(zip(ex['candidate_ids'], z.tolist())),
            'probs': dict(zip(ex['candidate_ids'], z.softmax(-1).tolist())),
        }
    if len(rows) != len(examples):
        raise ValueError('Question ids must be unique within one input batch')
    return rows


def compare(reference, observed, logit_atol, probability_atol):
    if reference.keys() != observed.keys():
        raise ValueError('Question mapping differs between compared predictions')
    deltas, flips = [], []
    for question_id, a in reference.items():
        b = observed[question_id]
        if set(a['candidate_ids']) != set(b['candidate_ids']):
            raise ValueError(f'Candidate mapping differs: {question_id}')
        for candidate_id in a['candidate_ids']:
            deltas.append({
                'question_id': question_id, 'candidate_id': candidate_id,
                'logit_abs': abs(a['logits'][candidate_id] - b['logits'][candidate_id]),
                'probability_abs': abs(a['probs'][candidate_id] - b['probs'][candidate_id]),
            })
        # Stable id sorting makes exact-tie handling independent of insertion order.
        before = max(sorted(a['candidate_ids']), key=a['probs'].__getitem__)
        after = max(sorted(b['candidate_ids']), key=b['probs'].__getitem__)
        if before != after:
            flips.append({'question_id': question_id, 'before': before, 'after': after})
    max_z = max(x['logit_abs'] for x in deltas)
    max_p = max(x['probability_abs'] for x in deltas)
    return {
        'questions': len(reference), 'candidate_outputs': len(deltas),
        'max_logit_abs_delta': max_z, 'max_probability_abs_delta': max_p,
        'mean_logit_abs_delta': math.fsum(x['logit_abs'] for x in deltas) / len(deltas),
        'mean_probability_abs_delta': math.fsum(x['probability_abs'] for x in deltas) / len(deltas),
        'within_declared_diagnostic_tolerance': max_z <= logit_atol and max_p <= probability_atol,
        'argmax_flips': flips,
        'largest_logit_deltas': sorted(deltas, key=lambda x: x['logit_abs'], reverse=True)[:5],
    }


def permute_candidates(examples, seed):
    rng = random.Random(seed)
    permuted, permutations = copy.deepcopy(examples), {}
    for ex in permuted:
        if ex['type'] == 'boolean':
            continue  # Boolean is one scalar with a fixed [false,true] interface.
        order = list(range(len(ex['candidate_ids'])))
        rng.shuffle(order)
        if order == list(range(len(order))):
            order = order[1:] + order[:1]
        permutations[ex['id']] = order
        ex['gold_index'] = order.index(ex['gold_index'])
        for field in ['candidate_ids', 'leaf_tokens', 'candidate_texts',
                      'teacher_raw_probs', 'teacher_probs']:
            if ex[field] is not None:
                ex[field] = [ex[field][i] for i in order]
    return permuted, permutations


def mutate_unrelated_state(examples, state_id, tokenizer):
    changed = copy.deepcopy(examples)
    first = next(ex for ex in changed if ex['state_id'] == state_id)
    prefix = tokenizer.encode(f"State:\n{first['source']['state']}\n", add_special_tokens=False)
    if len(prefix) < 4:
        raise ValueError('State prefix is too short for a nontrivial mutation')
    positions = sorted({len(prefix) // 3, len(prefix) // 2, 2 * len(prefix) // 3})
    replacement_pool = tokenizer.encode('unrelated altered content', add_special_tokens=False)
    substitutions = {}
    for position in positions:
        replacement = next((x for x in replacement_pool if x != prefix[position]), None)
        if replacement is None:
            raise ValueError('Unable to construct a nontrivial token mutation')
        substitutions[position] = replacement
    for ex in changed:
        if ex['state_id'] != state_id:
            continue
        for path in ex['leaf_tokens']:
            if path[:len(prefix)] != prefix:
                raise ValueError('State prefix does not match tokenized feature')
            for position, token_id in substitutions.items():
                path[position] = token_id
    return changed, {'mutated_state_id': state_id, 'changed_positions_within_state_prefix': positions,
                     'token_lengths_preserved': True, 'changed_tokens_per_path': len(positions)}


@torch.inference_mode()
def measure_timing(model, state_groups, pad_token):
    measurements = []
    for state_count in [1, 4, 8]:
        batch = [ex for group in state_groups[:state_count] for ex in group]
        if len(state_groups[:state_count]) != state_count:
            raise ValueError('Latency comparison requires eight test states')
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        allocated_before = torch.cuda.memory_allocated()
        for _ in range(2):
            with torch.autocast('cuda', dtype=torch.bfloat16):
                model(batch, pad_token)
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        timings = []
        for _ in range(20):
            torch.cuda.synchronize()
            started = time.perf_counter()
            with torch.autocast('cuda', dtype=torch.bfloat16):
                model(batch, pad_token)
            torch.cuda.synchronize()
            timings.append((time.perf_counter() - started) * 1000)
        p50, p95 = percentile(timings, 0.5), percentile(timings, 0.95)
        peak = torch.cuda.max_memory_allocated()
        measurements.append({
            'states': state_count, 'questions': len(batch),
            'candidate_paths': sum(len(ex['leaf_tokens']) for ex in batch),
            'unpadded_path_tokens': sum(len(path) for ex in batch for path in ex['leaf_tokens']),
            'max_path_tokens': max(len(path) for ex in batch for path in ex['leaf_tokens']),
            'warmup_calls': 2, 'measured_calls': 20, 'latency_ms': timings,
            'p50_ms': p50, 'p95_ms': p95,
            'questions_per_second_from_p50': 1000 * len(batch) / p50,
            'states_per_second_from_p50': 1000 * state_count / p50,
            'gpu_allocated_before_warmup_bytes': allocated_before,
            'gpu_peak_allocated_bytes': peak,
            'gpu_peak_increment_over_before_warmup_bytes': peak - allocated_before,
            'gpu_peak_reserved_bytes': torch.cuda.max_memory_reserved(),
        })
    return {
        'scope': 'warm GPU model forward, tensor assembly and host-to-device copies; no tokenization, output transfer, HTTP or queueing',
        'prefix_sharing': False, 'tree_attention': False, 'autoregressive_decode_steps': 0,
        'percentile_method': 'linear interpolation at (n-1)*fraction',
        'results': measurements,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--disable-native-triton', action='store_true')
    parser.add_argument('--seed', type=int, default=20260917)
    parser.add_argument('--logit-atol', type=float, default=0.02)
    parser.add_argument('--probability-atol', type=float, default=0.005)
    args = parser.parse_args()
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '7':
        raise RuntimeError('This check is authorized only with CUDA_VISIBLE_DEVICES=7')
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('Expected exactly one visible and usable CUDA device')
    if not torch.cuda.is_bf16_supported():
        raise RuntimeError('This check requires BF16 autocast support')
    if not args.run_dir.joinpath('summary.json').is_file():
        raise RuntimeError('Wait for the completed training summary before loading the checkpoint')
    if args.disable_native_triton:
        from torch._native import triton_utils
        triton_utils.deregister_op_overrides()
    torch.manual_seed(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    config = json.loads(args.run_dir.joinpath('config.json').read_text())
    data_hash = digest(args.input)
    if data_hash != config['data_sha256']:
        raise ValueError('Dataset hash differs from the completed training run')
    tokenizer = AutoTokenizer.from_pretrained(args.run_dir / 'tokenizer', local_files_only=True)
    backbone_config = AutoConfig.from_pretrained(args.run_dir / 'backbone_config', local_files_only=True)
    backbone = AutoModel.from_config(backbone_config, dtype=torch.float32, attn_implementation='sdpa')
    model = DecisionModel(backbone, config['set_head'])
    checkpoint_path = args.run_dir / 'best.safetensors'
    checkpoint = load_file(str(checkpoint_path), device='cpu')
    model.load_state_dict(checkpoint, strict=True)
    del checkpoint
    model = model.cuda().eval()
    examples, _ = load_examples(args.input, tokenizer, config['max_length'])
    groups = {}
    for ex in examples:
        if ex['split'] == 'test':
            groups.setdefault(ex['state_id'], []).append(ex)
    state_ids = list(groups)[:8]
    state_groups = [groups[key] for key in state_ids]
    if len(state_groups) != 8:
        raise ValueError('Need at least eight unique test states')
    selected = [ex for group in state_groups for ex in group]
    pad = tokenizer.pad_token_id
    reference = predict(model, selected, pad)
    results = {}

    singles = {}
    for ex in selected:
        singles.update(predict(model, [ex], pad))
    results['single_question_vs_eight_state_batch'] = compare(reference, singles, args.logit_atol, args.probability_atol)

    separate_states = {}
    for group in state_groups:
        separate_states.update(predict(model, group, pad))
    results['single_state_vs_eight_state_batch'] = compare(reference, separate_states, args.logit_atol, args.probability_atol)

    permutations, permutation_indices = permute_candidates(selected, args.seed)
    results['candidate_permutation_mapped_back'] = compare(
        reference, predict(model, permutations, pad), args.logit_atol, args.probability_atol)
    results['candidate_permutation_mapped_back']['permutations'] = permutation_indices
    results['candidate_permutation_mapped_back']['boolean_order_fixed'] = True

    reordered = [ex for group in reversed(state_groups) for ex in reversed(group)]
    results['state_and_question_reordering'] = compare(
        reference, predict(model, reordered, pad), args.logit_atol, args.probability_atol)

    unrelated, mutation_details = mutate_unrelated_state(selected, state_ids[-1], tokenizer)
    mutated_predictions = predict(model, unrelated, pad)
    unaffected = {key: value for key, value in reference.items() if value['state_id'] != state_ids[-1]}
    results['unrelated_state_mutation_isolation'] = compare(
        unaffected, {key: mutated_predictions[key] for key in unaffected}, args.logit_atol, args.probability_atol)
    affected = {key: value for key, value in reference.items() if value['state_id'] == state_ids[-1]}
    results['unrelated_state_mutation_isolation']['mutation'] = mutation_details
    results['unrelated_state_mutation_isolation']['affected_state_response'] = compare(
        affected, {key: mutated_predictions[key] for key in affected}, args.logit_atol, args.probability_atol)

    score_mutations = copy.deepcopy(selected)
    score_details = []
    for ex in score_mutations:
        if ex['type'] != 'score':
            continue
        # Change only level 1's semantics to equal level 0's; level 0 stays intact.
        ex['leaf_tokens'][1] = list(ex['leaf_tokens'][0])
        ex['candidate_texts'][1] = ex['candidate_texts'][0]
        score_details.append({'question_id': ex['id'], 'protected_candidate_id': ex['candidate_ids'][0],
                              'mutated_candidate_id': ex['candidate_ids'][1]})
    score_predictions = predict(model, score_mutations, pad)
    for detail in score_details:
        key, protect, changed = detail['question_id'], detail['protected_candidate_id'], detail['mutated_candidate_id']
        a, b = reference[key], score_predictions[key]
        detail.update({
            'protected_raw_logit_before': a['logits'][protect],
            'protected_raw_logit_after': b['logits'][protect],
            'protected_raw_logit_abs_delta': abs(a['logits'][protect] - b['logits'][protect]),
            'protected_softmax_probability_abs_delta': abs(a['probs'][protect] - b['probs'][protect]),
            'mutated_level_raw_logit_abs_delta': abs(a['logits'][changed] - b['logits'][changed]),
        })
    if not score_details:
        raise ValueError('Selected test states contain no score questions')
    max_score_delta = max(row['protected_raw_logit_abs_delta'] for row in score_details)
    results['score_other_level_semantics'] = {
        'scope': 'replace score level 1 path with level 0 path; protect raw logit of unchanged level 0',
        'softmax_invariance_required': False, 'choice_independence_required': False,
        'max_protected_raw_logit_abs_delta': max_score_delta,
        'within_declared_diagnostic_tolerance': max_score_delta <= args.logit_atol,
        'details': score_details,
    }

    precision_diagnostic = {'status': 'not_needed'}
    if not results['single_question_vs_eight_state_batch']['within_declared_diagnostic_tolerance']:
        fp32_batch = predict(model, selected, pad, bf16=False)
        fp32_singles = {}
        for ex in selected:
            fp32_singles.update(predict(model, [ex], pad, bf16=False))
        precision_diagnostic = {
            'trigger': 'BF16 single-question vs multistate batch exceeds predeclared diagnostic tolerance',
            'parameter_storage': 'float32', 'autocast_enabled': False,
            'fp32_single_vs_batch': compare(fp32_batch, fp32_singles, 1e-4, 1e-5),
            'bf16_batch_vs_fp32_batch': compare(fp32_batch, reference, args.logit_atol, args.probability_atol),
            'bf16_single_vs_fp32_single': compare(fp32_singles, singles, args.logit_atol, args.probability_atol),
            'interpretation_rule': 'Small FP32 single/batch differences support finite-precision or kernel-shape sensitivity; this is not a full kernel root-cause proof.',
        }

    report = {
        'schema': 'openjev-trained-invariance-timing-v1',
        'timestamp_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'script_sha256': digest(__file__),
        'trainer_sha256': digest(Path(__file__).with_name('train_toy_decisions.py')),
        'checkpoint_sha256': digest(checkpoint_path), 'data_sha256': data_hash,
        'run_dir': str(args.run_dir), 'training_config': config,
        'training_summary': json.loads(args.run_dir.joinpath('summary.json').read_text()),
        'environment': {'torch': torch.__version__, 'transformers': transformers.__version__,
                        'cuda_build': torch.version.cuda, 'gpu': torch.cuda.get_device_name(0),
                        'physical_gpu': 7, 'parameter_storage': 'float32', 'autocast': 'bfloat16',
                        'attention_backend': 'sdpa', 'native_triton_overrides_disabled': args.disable_native_triton},
        'selection': {'split': 'test', 'rule': 'first eight state ids in dataset file order',
                      'state_ids': state_ids, 'questions': len(selected), 'seed': args.seed},
        'diagnostic_tolerance': {'logit_absolute': args.logit_atol, 'probability_absolute': args.probability_atol,
                                'meaning': 'engineering diagnostic thresholds; measured deltas reported; no bitwise guarantee'},
        'invariance': results,
        'precision_diagnostic': precision_diagnostic,
        'all_invariance_checks_within_diagnostic_tolerance': all(
            row['within_declared_diagnostic_tolerance'] for row in results.values()),
        'timing': measure_timing(model, state_groups, pad),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'output': str(args.output),
                      'within_tolerance': report['all_invariance_checks_within_diagnostic_tolerance'],
                      'invariance': {key: {field: value for field, value in row.items()
                                         if field.startswith('max_') or field == 'argmax_flips'}
                                     for key, row in results.items()},
                      'timing': [{key: value for key, value in row.items()
                                  if key in ['states', 'p50_ms', 'p95_ms', 'questions_per_second_from_p50']}
                                 for row in report['timing']['results']]}), flush=True)


if __name__ == '__main__':
    main()
