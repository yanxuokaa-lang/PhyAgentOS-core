import runpy
from pathlib import Path

import pytest

_metrics = runpy.run_path(Path(__file__).parents[1] / "evals/metrics.py")
binary_metrics = _metrics["binary_metrics"]
reliability = _metrics["reliability"]


def test_perfect_binary_predictions():
    metrics = binary_metrics([0, 1, 0, 1], [0, 1, 0, 1])
    assert metrics["accuracy"] == 1
    assert metrics["brier"] == metrics["log_loss"] == 0
    assert metrics["positive_ece_10"] == metrics["top_ece_10"] == 0
    assert metrics["positive_reliability"][-1]["count"] == 2


def test_calibrated_constant_predictor_can_have_low_accuracy():
    metrics = binary_metrics([0.75] * 4, [1, 1, 1, 0])
    assert metrics["accuracy"] == 0.75
    assert metrics["brier"] == 0.1875
    assert metrics["positive_ece_10"] == metrics["top_ece_10"] == 0


def test_confident_errors_have_large_loss_and_calibration_gap():
    metrics = binary_metrics([0.9, 0.1], [0, 1])
    assert metrics["accuracy"] == 0
    assert metrics["brier"] == pytest.approx(0.81)
    assert metrics["positive_ece_10"] == pytest.approx(0.9)
    assert metrics["overconfidence_gap"] == pytest.approx(0.9)


def test_invalid_probabilities_fail_instead_of_being_silently_clipped():
    with pytest.raises(ValueError):
        reliability([float("nan")], [1])
