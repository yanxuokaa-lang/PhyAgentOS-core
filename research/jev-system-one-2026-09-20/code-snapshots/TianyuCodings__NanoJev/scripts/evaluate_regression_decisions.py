#!/usr/bin/env python3
"""Read-only V3-on-V2 non-grid regression diagnostic; never train or select a model."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import time

from train_pipeline_decisions import (
    distribution_metrics, evaluate_pipeline, load_training_examples, read_training_records,
)
from predict_toy_decisions import DecisionPredictor


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def summarize_predictions(rows):
    """Reuse the training evaluator's exact stable-logit CE/KL/TV definitions."""
    buckets = defaultdict(list)
    for row in rows:
        for axis, value in [('overall', 'all'), ('family', row['family_id']),
                            ('type', row['type']), ('target_kind', row.get('gold_probs_kind') or 'hard_gold_one_hot')]:
            buckets[(row['split'], axis, value)].append(row)
    result = {}
    for (split, axis, value), group in buckets.items():
        metrics = {}
        for target, field in [('gold_distribution', 'gold_distribution_probs'), ('teacher', 'teacher_probs')]:
            values = [distribution_metrics(row.get(field), row['student_logits']) for row in group]
            values = [x for x in values if x is not None]
            metrics[target] = {'n': len(values), **{key: sum(x[key] for x in values) / len(values) if values else None for key in ['ce', 'kl', 'tv']}}
        result.setdefault(split, {}).setdefault(axis, {})[value] = {'questions': len(group), 'targets': metrics}
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', required=True)
    ap.add_argument('--checkpoint-dir', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--precision', choices=['bf16', 'fp32'], default='bf16')
    ap.add_argument('--microbatch-questions', type=int, default=4)
    ap.add_argument('--max-microbatch-tokens', type=int, default=6000)
    ap.add_argument('--max-length', type=int, default=512)
    ap.add_argument('--disable-native-triton', action='store_true')
    args = ap.parse_args()
    out = Path(args.output_dir)
    if (out / 'summary.json').exists():
        raise ValueError('Refusing to overwrite a completed regression diagnostic')
    out.mkdir(parents=True, exist_ok=True)
    records, files = read_training_records(args.input)
    selected = [r for r in records if r['split'] in {'test', 'ood'}
                and r.get('metadata', {}).get('environment_state', {}).get('game') != 'grid_navigation']
    if not selected or any('grid' in r['family_id'] for r in selected):
        raise ValueError('Empty or incorrectly filtered non-grid regression cohort')
    filtered = out / 'input.jsonl'
    filtered.write_text(''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in selected))
    checkpoint = Path(args.checkpoint_dir)
    before_hash = digest(checkpoint / 'best.safetensors')
    start = time.perf_counter()
    engine = DecisionPredictor(checkpoint, max_length=args.max_length,
                               disable_native_triton=args.disable_native_triton, precision=args.precision)
    examples, _ = load_training_examples(filtered, engine.tokenizer, args.max_length)
    metrics = {}
    for split in ['test', 'ood']:
        group = [ex for ex in examples if ex['split'] == split]
        metrics[split] = evaluate_pipeline(engine.model, group, engine.tokenizer.pad_token_id,
                                           args, 'gold_distribution', out / f'predictions_{split}.jsonl')
    rows = [json.loads(line) for split in ['test', 'ood']
            for line in (out / f'predictions_{split}.jsonl').read_text().splitlines() if line.strip()]
    (out / 'predictions.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in rows))
    summary = {'name': checkpoint.name, 'diagnostic': 'Historical V2 held-out non-grid regression only; not new generalization evidence or a model-selection set.',
               'checkpoint_sha256': before_hash, 'source_sha256': {str(p): digest(p) for p in files},
               'filtered_input_sha256': digest(filtered), 'script_sha256': digest(__file__),
               'selected_records': len(selected), 'questions': len(examples),
               'record_counts_by_split': dict(Counter(r['split'] for r in selected)),
               'metrics_by_split': metrics, 'grouped_metrics': summarize_predictions(rows),
               'precision': args.precision, 'temperature': 1.0, 'temperature_fitted': False,
               'training_steps': 0, 'network_model_calls': 0, 'evaluation_seconds': time.perf_counter() - start,
               'max_gpu_allocated_gb': engine._torch.cuda.max_memory_allocated() / 1e9}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: summary[k] for k in ['name', 'checkpoint_sha256', 'selected_records', 'questions', 'evaluation_seconds', 'max_gpu_allocated_gb']}), flush=True)


if __name__ == '__main__':
    main()
