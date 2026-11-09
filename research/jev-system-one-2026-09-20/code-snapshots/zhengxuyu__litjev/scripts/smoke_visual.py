"""GPU smoke: one pretrained Qwen load, real Doom/chess screenshots, no training."""

import argparse
import json
import time
from pathlib import Path

import torch

from litjev.backend import ModelSettings, TransformersScorer
from litjev.decision import SchemaDecisionEngine
from litjev.games import make_env
from litjev.games.film import build_film
from litjev.games.policy import LitJevPolicy, LocalDecisionClient
from litjev.games.rollout import record_episode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("runs/visual-smoke"))
    parser.add_argument("--steps", type=int, default=4)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    scorer = TransformersScorer.load(ModelSettings(model_id=args.model, device_map="cuda:0"))
    torch.cuda.synchronize()
    loaded = time.perf_counter() - start
    engine = SchemaDecisionEngine(scorer, model_id=args.model)
    calls, vision_calls = [], []
    hook = scorer.model.register_forward_pre_hook(
        lambda m, a, kw: calls.append(
            {"shape": list(kw["input_ids"].shape), "pixels": "pixel_values" in kw}
        ),
        with_kwargs=True,
    )
    vision_hook = scorer.model.model.visual.register_forward_hook(
        lambda *args: vision_calls.append(1)
    )
    summary = {"model_load_seconds": loaded, "gpu": torch.cuda.get_device_name(), "games": {}}
    try:
        for game in ["chess", "doom"]:
            calls.clear()
            vision_calls.clear()
            with make_env(game, max_steps=args.steps) as env:
                policy = LitJevPolicy(
                    LocalDecisionClient(engine),
                    env.unwrapped.action_names,
                    env.unwrapped.instructions,
                )
                trace = record_episode(env, policy, seed=7)
            trace_path = args.output_dir / f"{game}.json"
            trace_path.write_text(json.dumps(trace, allow_nan=False))
            build_film(trace_path, args.output_dir / f"{game}.html")
            n = len(trace["decisions"])
            assert len(calls) == n * 2 and len(vision_calls) == n
            assert all(d["output_tokens"] == 0 for d in trace["decisions"])
            summary["games"][game] = {
                "steps": n,
                "calls": list(calls),
                "vision_calls": len(vision_calls),
                "latency_ms": [d["latency_ms"] for d in trace["decisions"]],
                "actions": [d["action"] for d in trace["decisions"]],
                "reward": trace["episode_reward"],
            }
            (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2))
            print(json.dumps(summary["games"][game]), flush=True)
    finally:
        hook.remove()
        vision_hook.remove()


if __name__ == "__main__":
    main()
