#!/usr/bin/env python3
"""CPU learning controls on fixed synthetic outcomes with known nontrivial q.

The candidate scorer, observations, initialization, batches, update count, and
dev selection rule are shared across objectives. No API or GPU is used. This is
an independent objective experiment, not the official TypeSafe training recipe
and not evidence about maze/Snake performance. Known q is never a training loss.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

import torch
from torch import nn

from calibrated_objectives import brier_loss, paired_brier_policy_loss


ARMS = ("observed_ce", "direct_brier", "paired_brier_pg", "correctness_reinforce")
METRICS = ("observed_nll", "observed_brier", "known_q_squared_l2", "known_q_kl",
           "top_label_ece", "accuracy", "expected_nll", "expected_brier")


def tensor_digest(*values):
    payload = [{"dtype": str(value.dtype), "shape": list(value.shape), "values": value.tolist()} for value in values]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class CandidateScorer(nn.Module):
    """A shared MLP over state, candidate, and their elementwise interaction."""
    def __init__(self, dimensions, hidden):
        super().__init__()
        self.network = nn.Sequential(nn.Linear(3 * dimensions, hidden), nn.Tanh(), nn.Linear(hidden, 1))

    def forward(self, context, candidates):
        expanded = context[:, None, :].expand_as(candidates)
        features = torch.cat([expanded, candidates, expanded * candidates], -1)
        return self.network(features).squeeze(-1)


def make_data(size, dimensions, support_sizes, seed):
    generator = torch.Generator(device="cpu").manual_seed(seed)
    context = torch.rand(size, dimensions, generator=generator) * 2 - 1
    candidates = torch.rand(size, max(support_sizes), dimensions, generator=generator) * 2 - 1
    sizes = torch.tensor([support_sizes[i % len(support_sizes)] for i in range(size)], dtype=torch.long)
    # Fixed probability generator. Its temperature and mixture weight are never tuned.
    smooth = (context[:, None, :] * candidates).sum(-1) / math.sqrt(dimensions)
    smooth += 0.6 * torch.sin(context[:, None, 0] + candidates[:, :, 0])
    smooth += 0.4 * candidates[:, :, 1]
    mask = torch.arange(max(support_sizes))[None, :] < sizes[:, None]
    base = (smooth / 0.9).masked_fill(~mask, -float("inf")).softmax(-1)
    q = 0.8 * base + 0.2 * mask.float() / sizes[:, None]
    outcomes = torch.multinomial(q, 1, generator=generator).squeeze(-1)
    return {"context": context, "candidates": candidates, "sizes": sizes, "mask": mask,
            "q": q, "outcomes": outcomes,
            "sha256": tensor_digest(context, candidates, sizes, q, outcomes)}


@torch.no_grad()
def evaluate(model, data, bins=15):
    logits = model(data["context"], data["candidates"])
    logp = logits.masked_fill(~data["mask"], -float("inf")).log_softmax(-1)
    p = logp.exp()
    q = data["q"]
    target = torch.zeros_like(p).scatter_(1, data["outcomes"][:, None], 1)
    nll = -logp.gather(1, data["outcomes"][:, None]).squeeze(-1)
    # Avoid 0 * -inf for padding without changing any offered probability.
    safe_logp = torch.where(data["mask"], logp, torch.zeros_like(logp))
    safe_logq = q.clamp_min(torch.finfo(q.dtype).tiny).log()
    known_l2 = (p - q).square().sum(-1)
    expected_nll = -(q * safe_logp).sum(-1)
    entropy = -(q * safe_logq).sum(-1)
    confidence, predictions = p.max(-1)
    correct = predictions == data["outcomes"]
    reliability = []
    ece = 0.0
    for i in range(bins):
        lower, upper = i / bins, (i + 1) / bins
        selected = (confidence >= lower) & ((confidence < upper) if i + 1 < bins else (confidence <= upper))
        count = int(selected.sum())
        item = {"lower": lower, "upper": upper, "count": count, "confidence": None, "accuracy": None}
        if count:
            item["confidence"] = float(confidence[selected].mean())
            item["accuracy"] = float(correct[selected].float().mean())
            ece += count / len(confidence) * abs(item["confidence"] - item["accuracy"])
        reliability.append(item)
    metrics = {
        "observed_nll": float(nll.mean()),
        "observed_brier": float((p - target).square().sum(-1).mean()),
        "known_q_squared_l2": float(known_l2.mean()),
        "known_q_kl": float((expected_nll - entropy).mean()),
        "top_label_ece": ece,
        "accuracy": float(correct.float().mean()),
        "expected_nll": float(expected_nll.mean()),
        "expected_brier": float((known_l2 + 1 - q.square().sum(-1)).mean()),
        "q_entropy": float(entropy.mean()),
        "q_bayes_brier": float((1 - q.square().sum(-1)).mean()),
        "reliability": reliability,
    }
    if not all(math.isfinite(metrics[key]) for key in METRICS):
        raise ValueError("Nonfinite held-out metrics")
    return metrics


def observed_loss(z, outcome, arm, samples, generator):
    if arm == "observed_ce":
        return -z.log_softmax(0)[outcome]
    if arm == "direct_brier":
        return brier_loss(z, outcome)
    if arm == "paired_brier_pg":
        return paired_brier_policy_loss(z, outcome, samples, generator, baseline=True)[0]
    if arm == "correctness_reinforce":
        logp = z.log_softmax(0)
        p = logp.detach().exp()
        actions = torch.multinomial(p, samples, replacement=True, generator=generator)
        reward = (actions == outcome).to(z.dtype)
        # An action-independent detached baseline preserves this linear objective.
        return -((reward - p[outcome]).detach() * logp[actions]).mean()
    raise ValueError(f"Unknown objective: {arm}")


def train_arm(initial, data, batch_plan, args, seed, arm):
    model = copy.deepcopy(initial)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    generator = torch.Generator(device="cpu").manual_seed(100000 + seed)
    initial_dev = evaluate(model, data["dev"], args.ece_bins)
    best_nll, best_step = initial_dev["observed_nll"], 0
    best_state = copy.deepcopy(model.state_dict())
    best_dev = initial_dev
    history = [{"step": 0, "dev": initial_dev, "train_surrogate_mean": None}]
    started = time.perf_counter()
    accumulated, count = 0.0, 0
    train = data["train"]
    for step, indices in enumerate(batch_plan, 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        values = model(train["context"][indices], train["candidates"][indices])
        sizes = train["sizes"][indices].tolist()
        outcomes = train["outcomes"][indices].tolist()
        losses = [observed_loss(row[:k], outcome, arm, args.samples, generator)
                  for row, k, outcome in zip(values, sizes, outcomes)]
        loss = torch.stack(losses).mean()
        if not torch.isfinite(loss):
            raise ValueError(f"Nonfinite loss: arm={arm}, seed={seed}, step={step}")
        loss.backward()
        if not all(parameter.grad is not None and torch.isfinite(parameter.grad).all() for parameter in model.parameters()):
            raise ValueError(f"Nonfinite gradient: arm={arm}, seed={seed}, step={step}")
        optimizer.step()
        accumulated += float(loss.detach())
        count += 1
        if step % args.eval_every == 0 or step == args.steps:
            model.eval()
            dev = evaluate(model, data["dev"], args.ece_bins)
            history.append({"step": step, "dev": dev, "train_surrogate_mean": accumulated / count})
            accumulated, count = 0.0, 0
            # One rule for every arm; strict comparison keeps the earlier checkpoint on ties.
            if dev["observed_nll"] < best_nll:
                best_nll, best_step = dev["observed_nll"], step
                best_dev = dev
                best_state = copy.deepcopy(model.state_dict())
    elapsed = time.perf_counter() - started
    model.load_state_dict(best_state)
    model.eval()
    # This is the only test evaluation for this trained arm.
    test = evaluate(model, data["test"], args.ece_bins)
    return {"name": arm, "seed": seed, "selected_step": best_step,
            "selection_metric": "minimum dev observed_nll; earliest checkpoint on a tie",
            "completed_optimizer_steps": args.steps, "runtime_seconds": elapsed,
            "train_examples_seen": args.steps * args.batch_size,
            "predictive_samples_per_training_question": args.samples if arm in ARMS[2:] else 0,
            "selected_dev": best_dev, "test": test, "history": history}


def summarize(runs):
    result = {}
    for arm in ("initial",) + ARMS:
        records = [run[arm] for run in runs]
        metrics = {}
        for key in METRICS:
            values = [record["test"][key] for record in records]
            metrics[key] = {"mean": statistics.mean(values),
                            "sample_sd": statistics.stdev(values) if len(values) > 1 else None,
                            "values": values}
        result[arm] = {"seeds": len(records), "test": metrics,
                       "selected_steps": [record["selected_step"] for record in records]}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("research/calibrated_learning_benchmark.json"))
    parser.add_argument("--steps", type=int, default=600)
    parser.add_argument("--seeds", type=int, nargs="+", default=[17, 18, 19])
    parser.add_argument("--data-seed", type=int, default=20260918)
    parser.add_argument("--train-size", type=int, default=1536)
    parser.add_argument("--dev-size", type=int, default=768)
    parser.add_argument("--test-size", type=int, default=2048)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--dimensions", type=int, default=4)
    parser.add_argument("--hidden", type=int, default=32)
    parser.add_argument("--candidate-counts", type=int, nargs="+", default=[2, 3, 5])
    parser.add_argument("--learning-rate", type=float, default=0.003)
    parser.add_argument("--samples", type=int, default=32)
    parser.add_argument("--eval-every", type=int, default=50)
    parser.add_argument("--ece-bins", type=int, default=15)
    parser.add_argument("--threads", type=int, default=1)
    args = parser.parse_args()
    positive = [args.steps, args.train_size, args.dev_size, args.test_size, args.batch_size,
                args.hidden, args.eval_every, args.ece_bins, args.threads]
    if min(positive) < 1 or args.dimensions < 2 or args.samples < 2 or min(args.candidate_counts) < 2:
        parser.error("Positive sizes/steps are required; dimensions, samples, and candidate counts must be >=2")
    if len(set(args.seeds)) != len(args.seeds) or len(set(args.candidate_counts)) != len(args.candidate_counts):
        parser.error("Seeds and candidate counts must not repeat")
    if not math.isfinite(args.learning_rate) or args.learning_rate <= 0:
        parser.error("learning-rate must be finite and positive")
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    data = {split: make_data(size, args.dimensions, args.candidate_counts, args.data_seed + offset)
            for split, size, offset in [("train", args.train_size, 0), ("dev", args.dev_size, 1), ("test", args.test_size, 2)]}
    identities = {split: {tuple(x.tolist()) for x in values["context"]} for split, values in data.items()}
    if any(identities[a] & identities[b] for a, b in [("train", "dev"), ("train", "test"), ("dev", "test")]):
        raise ValueError("Repeated visible context across data splits")
    started = time.perf_counter()
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    report = {
        "status": "running", "device": "cpu", "torch_version": torch.__version__, "config": config,
        "scope": "Synthetic known-q objective comparison; no pretrained model, API, GPU, or game claim.",
        "method_status": "The sampled objective is an independently specified proper-reward method; no official TypeSafe formula is asserted.",
        "protocol": {
            "arms": ["initial"] + list(ARMS), "fixed_data_across_all_seeds_and_arms": True,
            "training_target": "One observed categorical outcome per fixed synthetic example; known q is excluded from training losses.",
            "q_generator": "q=0.8*softmax((sum(context*candidate)/sqrt(d)+0.6*sin(context[0]+candidate[0])+0.4*candidate[1])/0.9)+0.2/K on offered candidates",
            "initialization": "Identical candidate-scorer parameters for every trained arm within a seed.",
            "batching": "The complete step-by-batch index matrix is fixed per seed and reused for all arms.",
            "optimization": "Same Adam learning rate, batch count, per-question mean, and update budget; no gradient clipping or entropy regularization.",
            "selection": "Minimum observed dev NLL at step 0/every eval-every/final step; earliest on ties; test evaluated once after selection per arm.",
            "paired_control": "Independent replacement samples and detached other-sample conditional baseline.",
            "correctness_control": "Mean REINFORCE reward 1[A=Y] with detached action-independent p[Y] baseline; not a proper probability objective.",
            "uncertainty": "Seed sample SD conditions on one fixed dataset; it is not a data-bootstrap confidence interval.",
            "compute": "Equal update counts do not imply equal CPU time; runtime and sample counts are reported.",
            "surrogate_scale": "Sampled surrogate values are not Brier scores; evaluation always uses direct probability metrics.",
            "ece": f"Top-label ECE with {args.ece_bins} equal-width bins; insufficient alone to establish calibration.",
        },
        "data": {}, "runs": [],
        "source_sha256": {"benchmark": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                          "objectives": hashlib.sha256(Path(__file__).with_name("calibrated_objectives.py").read_bytes()).hexdigest()},
    }
    for split, values in data.items():
        positive_q = values["q"][values["mask"]]
        report["data"][split] = {"records": len(values["sizes"]), "sha256": values["sha256"],
                                  "candidate_counts": {str(k): int((values["sizes"] == k).sum()) for k in args.candidate_counts},
                                  "minimum_offered_q": float(positive_q.min()), "maximum_offered_q": float(positive_q.max()),
                                  "distinct_contexts": len(identities[split])}
    for seed in args.seeds:
        torch.manual_seed(seed)
        initial = CandidateScorer(args.dimensions, args.hidden)
        batch_generator = torch.Generator(device="cpu").manual_seed(seed + 999)
        plan = torch.randint(args.train_size, (args.steps, args.batch_size), generator=batch_generator)
        run = {"seed": seed, "initial_parameters_sha256": tensor_digest(*initial.state_dict().values()),
               "batch_plan_sha256": tensor_digest(plan),
               "parameter_count": sum(p.numel() for p in initial.parameters()),
               "initial": {"selected_step": 0, "dev": evaluate(initial, data["dev"], args.ece_bins),
                           "test": evaluate(initial, data["test"], args.ece_bins)}}
        for arm in ARMS:
            run[arm] = train_arm(initial, data, plan, args, seed, arm)
            print(json.dumps({"seed": seed, "arm": arm, "selected_step": run[arm]["selected_step"],
                              "test": {key: run[arm]["test"][key] for key in METRICS},
                              "runtime_seconds": run[arm]["runtime_seconds"]}), flush=True)
        report["runs"].append(run)
    report["summary"] = summarize(report["runs"])
    report["status"] = "completed"
    report["runtime_seconds"] = time.perf_counter() - started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output), "runtime_seconds": report["runtime_seconds"]}))


if __name__ == "__main__":
    main()
