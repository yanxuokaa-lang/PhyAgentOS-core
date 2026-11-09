import math
import random

from jevmlx.calibrate import ece, fit_temperature


def _samples_from_true_temp(t_true: float, n: int = 400, k: int = 5, seed: int = 7):
    """Synthetic per-choice scores whose softmax at T=t_true is well-calibrated
    for a known argmax: draw p ~ Dirichlet-ish, label = argmax, invert softmax."""
    rng = random.Random(seed)
    samples = []
    for _ in range(n):
        logits = [rng.gauss(0, 1) for _ in range(k)]
        winner = rng.randrange(k)
        logits[winner] += rng.uniform(1.5, 4.0)
        scaled = [x / t_true for x in logits]
        m = max(scaled)
        exps = [math.exp(s - m) for s in scaled]
        z = sum(exps)
        probs = [e / z for e in exps]
        u = rng.random()
        acc = 0.0
        label = k - 1
        for i, p in enumerate(probs):
            acc += p
            if u <= acc:
                label = i
                break
        samples.append((logits, label))
    return samples


def test_fit_temperature_recovers_3x_sharpening():
    samples = _samples_from_true_temp(3.0, n=2000)
    # Scores are 3x too sharp relative to the sampling distribution -> fitted T ~ 3.
    t = fit_temperature(samples)
    assert abs(t - 3.0) < 0.2, f"fitted T={t}, expected ~3.0"


def test_ece_of_calibrated_samples_is_low():
    samples = _samples_from_true_temp(1.0, n=2000)
    assert ece(samples, 1.0) < 0.05


def test_ece_overconfident_scores_high():
    samples = _samples_from_true_temp(3.0)
    assert ece(samples, 1.0) > ece(samples, 3.0)
