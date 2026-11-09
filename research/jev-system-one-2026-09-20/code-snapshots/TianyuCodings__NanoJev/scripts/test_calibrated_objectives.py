#!/usr/bin/env python3
"""Independent CPU checks for the explicitly specified probability objectives.

This validates our implementation, not a disclosed TypeSafe training recipe.
The policy-gradient scalar is a surrogate: its numerical value is not Brier.
Only Python and PyTorch are needed; no model download, API, or GPU is used.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import time
from unittest.mock import patch

import torch

from calibrated_objectives import brier_loss, paired_brier_policy_loss


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not bool(condition):
        raise AssertionError(message)


def close(actual, expected, atol=1e-11, rtol=1e-10):
    torch.testing.assert_close(actual, expected, atol=atol, rtol=rtol)


def reference_local_loss(logits, outcome, actions, baseline):
    """Deliberately use explicit other-sample loops, not bincount algebra."""
    logp = logits.log_softmax(0)
    p = logp.detach().exp()
    count = len(actions)
    terms = []
    for i, action in enumerate(actions):
        others = [value for j, value in enumerate(actions) if j != i]
        reward = 2.0 / count * float(action == outcome)
        reward -= 2.0 / (count * (count - 1)) * sum(action == value for value in others)
        control = 0.0
        if baseline:
            control = 2.0 / count * p[outcome]
            control -= 2.0 / (count * (count - 1)) * sum(p[value] for value in others)
        advantage = torch.as_tensor(reward - control, dtype=logits.dtype).detach()
        terms.append(-advantage * logp[action])
    return torch.stack(terms).sum()


def call_with_actions(logits, outcome, actions, baseline):
    def fixed_draw(probabilities, num_samples, replacement=False, generator=None, **kwargs):
        require(replacement is True, "Predictive samples must use replacement")
        require(num_samples == len(actions), "Wrong predictive sample count")
        close(probabilities, logits.detach().softmax(0))
        return torch.tensor(actions, dtype=torch.long, device=probabilities.device)

    with patch.object(torch, "multinomial", side_effect=fixed_draw) as mocked:
        loss, stats = paired_brier_policy_loss(logits, outcome, len(actions), baseline=baseline)
    require(mocked.call_count == 1, "Expected one independent categorical sample operation")
    require(loss.ndim == 0 and loss.dtype == logits.dtype, "Scalar loss must preserve dtype")
    require(stats["samples"] == len(actions), "Wrong samples statistic")
    require(stats["outcome"] == outcome and stats["baseline"] == baseline, "Wrong statistics")
    require(stats["independent_sampling_with_replacement"] is True, "Missing sampling contract")
    reward = 2.0 * sum(a == outcome for a in actions) / len(actions)
    reward -= sum(a == b for i, a in enumerate(actions) for j, b in enumerate(actions) if i != j) / (len(actions) * (len(actions) - 1))
    require(abs(stats["reward"] - reward) < 1e-12, "Incorrect reward value")
    reference = reference_local_loss(logits, outcome, actions, baseline)
    close(loss, reference)
    return loss, stats


def exact_enumeration():
    rows = []
    for k, samples in [(2, 2), (3, 2), (5, 2), (2, 3)]:
        base = torch.linspace(-0.9, 1.1, k, dtype=torch.float64)
        base += torch.sin(torch.arange(k, dtype=torch.float64)) * 0.2
        p = base.softmax(0)
        q = torch.linspace(1.0, 2.0, k, dtype=torch.float64)
        q /= q.sum()
        for baseline in [False, True]:
            max_gradient_error = 0.0
            max_reward_error = 0.0
            mixture_gradient = torch.zeros_like(base)
            for outcome in range(k):
                expected_gradient = torch.zeros_like(base)
                expected_reward = 0.0
                for actions in itertools.product(range(k), repeat=samples):
                    weight = math.prod(float(p[a]) for a in actions)
                    z = base.clone().requires_grad_(True)
                    loss, stats = call_with_actions(z, outcome, actions, baseline)
                    expected_gradient += weight * torch.autograd.grad(loss, z)[0]
                    expected_reward += weight * stats["reward"]
                z = base.clone().requires_grad_(True)
                direct_gradient = torch.autograd.grad(brier_loss(z, outcome), z)[0]
                error = float((expected_gradient - direct_gradient).abs().max())
                reward_error = abs(expected_reward - float(2 * p[outcome] - p.square().sum()))
                max_gradient_error = max(max_gradient_error, error)
                max_reward_error = max(max_reward_error, reward_error)
                close(expected_gradient, direct_gradient)
                require(reward_error < 1e-12, "Enumerated reward expectation is not proper")
                mixture_gradient += q[outcome] * expected_gradient
            z = base.clone().requires_grad_(True)
            known_q_loss = (z.softmax(0) - q).square().sum()
            known_q_gradient = torch.autograd.grad(known_q_loss, z)[0]
            close(mixture_gradient, known_q_gradient)
            rows.append({"k": k, "samples": samples, "baseline": baseline,
                         "enumerated_outcome_and_sample_tuples": k ** (samples + 1),
                         "max_gradient_absolute_error": max_gradient_error,
                         "max_reward_expectation_absolute_error": max_reward_error,
                         "mixture_q_gradient_absolute_error": float((mixture_gradient - known_q_gradient).abs().max())})
    return rows


def monte_carlo(seed, repeats):
    rows = []
    for k in [2, 5]:
        base = torch.linspace(-0.6, 0.9, k, dtype=torch.float64)
        q = torch.linspace(2.0, 1.0, k, dtype=torch.float64)
        q /= q.sum()
        z_ref = base.clone().requires_grad_(True)
        target = torch.autograd.grad((z_ref.softmax(0) - q).square().sum(), z_ref)[0]
        true_reward = float(2 * base.softmax(0).dot(q) - base.softmax(0).square().sum())
        for samples in [2, 8, 32]:
            for baseline in [False, True]:
                generator = torch.Generator(device="cpu").manual_seed(seed + 1000 * k + 10 * samples + int(baseline))
                gradients, rewards = [], []
                for _ in range(repeats):
                    outcome = int(torch.multinomial(q, 1, generator=generator).item())
                    z = base.clone().requires_grad_(True)
                    loss, stats = paired_brier_policy_loss(z, outcome, samples, generator, baseline)
                    gradients.append(torch.autograd.grad(loss, z)[0])
                    rewards.append(stats["reward"])
                values = torch.stack(gradients)
                mean = values.mean(0)
                sem = values.std(0, unbiased=True) / math.sqrt(repeats)
                absolute_error = (mean - target).abs()
                tolerance = 7 * sem + 1e-4
                require((absolute_error <= tolerance).all(), "Monte Carlo gradient exceeds seven standard errors")
                reward_values = torch.tensor(rewards, dtype=torch.float64)
                reward_sem = float(reward_values.std(unbiased=True) / math.sqrt(repeats))
                reward_error = abs(float(reward_values.mean()) - true_reward)
                require(reward_error <= 7 * reward_sem + 1e-4, "Monte Carlo reward expectation failed")
                rows.append({"k": k, "samples": samples, "baseline": baseline, "repeats": repeats,
                             "reference_gradient": target.tolist(), "mean_gradient": mean.tolist(),
                             "gradient_standard_error": sem.tolist(),
                             "maximum_gradient_absolute_error": float(absolute_error.max()),
                             "maximum_standardized_gradient_error": float((absolute_error / sem.clamp_min(1e-12)).max()),
                             "reward_mean": float(reward_values.mean()), "reward_expectation": true_reward,
                             "reward_standard_error": reward_sem,
                             "criterion": "Each error <= 7 estimated standard errors + 0.0001; fixed seed, no reroll."})
    return rows


def dynamic_and_boolean(seed):
    generator = torch.Generator().manual_seed(seed)
    rows = []
    for k in [2, 3, 5, 20, 64, 255]:
        z = torch.linspace(-3.0, 2.0, k, dtype=torch.float64).requires_grad_(True)
        direct = brier_loss(z, k - 1)
        sampled, stats = paired_brier_policy_loss(z, k - 1, samples=32, generator=generator)
        gradients = torch.autograd.grad(direct + sampled, z)[0]
        require(torch.isfinite(gradients).all(), "Nonfinite dynamic-candidate gradient")
        require(abs(float(gradients.sum())) < 1e-11, "Softmax-shift gradient must sum to zero")
        rows.append({"k": k, "gradient_shape": list(gradients.shape), "brier": float(direct.detach()),
                     "sampled_reward": stats["reward"]})
    for outcome in [0, 1]:
        z = torch.tensor([0.3, -0.8], dtype=torch.float64, requires_grad=True)
        p_true = z.softmax(0)[1]
        scalar = (p_true - outcome).square()
        close(brier_loss(z, outcome), 2 * scalar)
    # Relabeling candidate identifiers must only relabel the gradients.
    z = torch.tensor([-1.0, 0.1, 0.8, -0.3], dtype=torch.float64, requires_grad=True)
    permutation = torch.tensor([2, 0, 3, 1])
    inverse = torch.argsort(permutation)
    original_actions, outcome = [0, 3, 3, 1, 2], 1
    loss, _ = call_with_actions(z, outcome, original_actions, True)
    original_gradient = torch.autograd.grad(loss, z)[0]
    permuted = z.detach()[permutation].requires_grad_(True)
    mapped = [int(inverse[a]) for a in original_actions]
    permuted_loss, _ = call_with_actions(permuted, int(inverse[outcome]), mapped, True)
    permuted_gradient = torch.autograd.grad(permuted_loss, permuted)[0]
    close(loss.detach(), permuted_loss.detach())
    close(original_gradient, permuted_gradient[inverse])
    return {"dynamic_k": rows, "binary_brier_is_twice_scalar_bernoulli_brier": True,
            "candidate_relabeling_gradient_equivalence": True}


def invalid_inputs():
    cases = [
        ("empty", torch.tensor([], dtype=torch.float64), 0),
        ("singleton", torch.tensor([0.0]), 0),
        ("batched_logits", torch.zeros(2, 3), 1),
        ("integer_logits", torch.tensor([0, 1]), 0),
        ("negative_outcome", torch.zeros(3), -1),
        ("outcome_outside_support", torch.zeros(3), 3),
        ("boolean_outcome", torch.zeros(3), True),
        ("float_outcome", torch.zeros(3), 1.0),
        ("padded_negative_infinity", torch.tensor([0.0, 1.0, -float("inf")]), 0),
        ("positive_infinity", torch.tensor([0.0, float("inf")]), 0),
        ("nan", torch.tensor([0.0, float("nan")]), 0),
    ]
    checked = []
    for name, logits, outcome in cases:
        for function in [brier_loss, paired_brier_policy_loss]:
            try:
                function(logits, outcome)
            except (ValueError, TypeError):
                checked.append(f"{function.__name__}:{name}")
            else:
                raise AssertionError(f"Accepted invalid input: {function.__name__}:{name}")
    for samples in [0, 1, -2, 2.0, True]:
        try:
            paired_brier_policy_loss(torch.zeros(2), 0, samples=samples)
        except (ValueError, TypeError):
            checked.append(f"invalid_samples:{samples!r}")
        else:
            raise AssertionError(f"Accepted invalid sample count: {samples!r}")
    return {"rejected": checked,
            "scope": "The scalar objective rejects nonfinite padding; the grouped adapter must remove padding first."}


def grouped_mean_and_padding():
    from calibrated_objectives import grouped_calibrated_loss
    examples = [
        {"candidate_ids": ["false", "true"], "gold_index": 1, "gold_label_kind": "observed_outcome"},
        {"candidate_ids": ["a", "b", "c", "d", "e"], "gold_index": 3, "gold_label_kind": "observed_outcome"},
    ]
    values = torch.tensor([[0.3, -0.6, -float("inf"), -float("inf"), -float("inf")],
                           [0.1, -0.5, 0.8, -0.2, 0.4]], dtype=torch.float32)
    samples = [[0, 1, 1, 0], [0, 3, 3, 4]]
    rows = []
    for kind in ["ce", "brier", "paired_brier_pg"]:
        z = values.clone().requires_grad_(True)
        if kind == "paired_brier_pg":
            draws = iter(samples)

            def fixed_draw(p, count, replacement=False, generator=None):
                actions = next(draws)
                require(replacement and count == len(actions), "Bad grouped sampling contract")
                return torch.tensor(actions, dtype=torch.long)

            with patch.object(torch, "multinomial", side_effect=fixed_draw):
                losses = grouped_calibrated_loss(z, examples, "observed_outcome", kind, samples=4)
        else:
            losses = grouped_calibrated_loss(z, examples, "observed_outcome", kind)
        expected = []
        for row, example, actions in zip(z, examples, samples):
            offered = row[:len(example["candidate_ids"])]
            y = example["gold_index"]
            if kind == "ce":
                expected.append(-offered.log_softmax(0)[y])
            elif kind == "brier":
                expected.append(brier_loss(offered, y))
            else:
                expected.append(reference_local_loss(offered, y, actions, True))
        expected = torch.stack(expected)
        close(losses, expected, atol=2e-7, rtol=2e-6)
        actual_gradient = torch.autograd.grad(losses.mean(), z, retain_graph=True)[0]
        expected_gradient = torch.autograd.grad(expected.sum() / len(examples), z)[0]
        close(actual_gradient, expected_gradient, atol=2e-7, rtol=2e-6)
        require(torch.isfinite(actual_gradient).all(), "Padding contaminated the gradient")
        require((actual_gradient[0, 2:] == 0).all(), "Padding receives gradient")
        rows.append({"objective": kind, "per_question_shape": list(losses.shape),
                     "mean_loss_value": float(losses.detach().mean()),
                     "equal_question_weight_not_candidate_weight": True, "padded_gradient_zero": True})
    return {"checks": rows, "note": "Sampled surrogate means are not proper-score values and must not be compared numerically with Brier."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("research/calibrated_objectives_check.json"))
    parser.add_argument("--seed", type=int, default=20260918)
    parser.add_argument("--mc-repeats", type=int, default=2000)
    parser.add_argument("--threads", type=int, default=1)
    args = parser.parse_args()
    if args.mc_repeats < 100 or args.threads < 1:
        parser.error("Use at least 100 Monte Carlo repeats and one CPU thread")
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    started = time.perf_counter()
    report = {"status": "running", "device": "cpu", "torch_version": torch.__version__,
              "seed": args.seed, "mc_repeats": args.mc_repeats,
              "implementation_scope": "Independent mathematical validation; not a recovered TypeSafe recipe.",
              "sources": {"test": digest(__file__),
                          "objectives": digest(Path(__file__).with_name("calibrated_objectives.py"))},
              "checks": {}, "failures": []}
    checks = [
        ("exact_enumeration", exact_enumeration),
        ("monte_carlo", lambda: monte_carlo(args.seed, args.mc_repeats)),
        ("dynamic_and_boolean", lambda: dynamic_and_boolean(args.seed)),
        ("invalid_inputs", invalid_inputs),
        ("grouped_mean_and_padding", grouped_mean_and_padding),
    ]
    for name, operation in checks:
        try:
            report["checks"][name] = operation()
            print(f"PASS {name}", flush=True)
        except Exception as error:
            report["failures"].append({"check": name, "type": type(error).__name__, "message": str(error)})
            print(f"FAIL {name}: {error}", flush=True)
    report["status"] = "passed" if not report["failures"] else "failed"
    report["runtime_seconds"] = time.perf_counter() - started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output), "runtime_seconds": report["runtime_seconds"]}))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
