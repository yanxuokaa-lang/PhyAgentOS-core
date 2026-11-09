#!/usr/bin/env python3
"""Evaluate a frozen NanoJev checkpoint on complete held-out game questions."""
import argparse
from pathlib import Path
from types import SimpleNamespace
import json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--max-length", type=int, default=8192)
    p.add_argument("--splits", default="test,ood")
    args = p.parse_args()
    out = Path(args.output_dir)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Use a new empty output directory")
    from predict_toy_decisions import DecisionPredictor
    from train_pipeline_decisions import load_training_examples, evaluate_pipeline, dump
    engine = DecisionPredictor(args.checkpoint, max_length=args.max_length, disable_native_triton=True)
    examples, audit = load_training_examples(args.input, engine.tokenizer, args.max_length)
    settings = SimpleNamespace(microbatch_questions=4, max_microbatch_tokens=16384, precision="bf16")
    out.mkdir(parents=True, exist_ok=True)
    result = {"checkpoint": args.checkpoint, "max_length": args.max_length, "metrics": {}}
    for split in args.splits.split(","):
        subset = [ex for ex in examples if ex["split"] == split]
        if not subset:
            raise ValueError(f"Empty split {split}")
        result["metrics"][split] = evaluate_pipeline(engine.model, subset, engine.tokenizer.pad_token_id,
                                                   settings, "gold_distribution", out / f"predictions_{split}.jsonl")
    dump(out / "summary.json", result)
    dump(out / "token_audit.json", audit)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
