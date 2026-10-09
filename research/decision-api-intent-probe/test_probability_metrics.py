import math

import pytest

from decision_intent_probe import probability_metrics


def test_probability_metrics_uses_valid_distributions_and_reports_coverage() -> None:
    samples = {
        "c1": {"gold": "a"},
        "c2": {"gold": "b"},
        "c3": {"gold": "a"},
    }
    rows = [
        {
            "case_id": "c1",
            "answer": "a",
            "answers": {"answer": {"probabilities": {"a": 0.8, "b": 0.2}}},
        },
        {
            "case_id": "c2",
            "answer": "a",
            "answers": {"answer": {"probabilities": {"a": 0.6, "b": 0.4}}},
        },
        {"case_id": "c3", "answer": "a", "answers": {"answer": {}}},
    ]

    metrics = probability_metrics(rows, samples, "answer", ("a", "b"), "gold")

    assert metrics["samples"] == 2
    assert metrics["coverage"] == pytest.approx(2 / 3)
    assert metrics["ece_10_bin"] == pytest.approx(0.4)
    assert metrics["brier_multiclass"] == pytest.approx(0.4)
    assert metrics["nll"] == pytest.approx((-math.log(0.8) - math.log(0.4)) / 2)


def test_probability_metrics_normalizes_rounded_provider_values() -> None:
    samples = {"c1": {"gold": "a"}}
    rows = [
        {
            "case_id": "c1",
            "answer": "a",
            "answers": {"answer": {"probabilities": {"a": 0.67, "b": 0.34}}},
        }
    ]

    metrics = probability_metrics(rows, samples, "answer", ("a", "b"), "gold")

    expected_true_probability = 0.67 / 1.01
    assert metrics["samples"] == 1
    assert metrics["brier_multiclass"] == pytest.approx(
        2 * (1 - expected_true_probability) ** 2
    )
    assert metrics["nll"] == pytest.approx(-math.log(expected_true_probability))


def test_ece_uses_distribution_argmax_instead_of_separate_choice() -> None:
    samples = {"c1": {"gold": "a"}}
    rows = [
        {
            "case_id": "c1",
            "answer": "b",
            "answers": {"answer": {"probabilities": {"a": 0.8, "b": 0.2}}},
        }
    ]

    metrics = probability_metrics(rows, samples, "answer", ("a", "b"), "gold")

    assert metrics["ece_10_bin"] == pytest.approx(0.2)
