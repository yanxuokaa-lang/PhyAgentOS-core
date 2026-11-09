from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from litjev.slots import SLOT_FORMAT

LOG_TEMPERATURE_MIN = -5.0
LOG_TEMPERATURE_MAX = 5.0
GOLDEN_RATIO = (math.sqrt(5.0) - 1.0) / 2.0
OPTIMIZATION_STEPS = 100


@dataclass(frozen=True, slots=True)
class CalibrationProfile:
    temperature: float
    sample_count: int
    nll_before: float
    nll_after: float
    model_id: str | None = None
    slot_format: str = SLOT_FORMAT

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> CalibrationProfile:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("slot_format") != SLOT_FORMAT:
            raise ValueError("Calibration prompt format changed; refit on current validation logits")
        return cls(**data)


class TemperatureCalibrator:
    @staticmethod
    def fit(
        logits: np.ndarray,
        labels: np.ndarray,
        model_id: str | None = None,
    ) -> CalibrationProfile:
        matrix, targets = _validated_examples(logits, labels)
        objective = lambda log_temperature: _negative_log_likelihood(
            matrix, targets, math.exp(log_temperature)
        )
        best_log_temperature = _golden_section_minimize(objective)
        temperature = math.exp(best_log_temperature)
        return CalibrationProfile(
            temperature=temperature,
            sample_count=len(targets),
            nll_before=_negative_log_likelihood(matrix, targets, 1.0),
            nll_after=_negative_log_likelihood(matrix, targets, temperature),
            model_id=model_id,
        )


def _validated_examples(logits: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.asarray(logits, dtype=np.float64)
    targets = np.asarray(labels, dtype=np.int64)
    if matrix.ndim != 2 or targets.ndim != 1 or len(matrix) != len(targets):
        raise ValueError("logits must be [N, K] and labels must be [N]")
    if len(targets) == 0:
        raise ValueError("At least one calibration example is required")
    if np.any(targets < 0) or np.any(targets >= matrix.shape[1]):
        raise ValueError("A calibration label is outside the logit range")
    return matrix, targets


def _negative_log_likelihood(logits: np.ndarray, labels: np.ndarray, temperature: float) -> float:
    scaled = logits / temperature
    shifted = scaled - np.max(scaled, axis=1, keepdims=True)
    log_normalizer = np.log(np.exp(shifted).sum(axis=1))
    chosen = shifted[np.arange(len(labels)), labels]
    return float(np.mean(log_normalizer - chosen))


def _golden_section_minimize(objective) -> float:
    left = LOG_TEMPERATURE_MIN
    right = LOG_TEMPERATURE_MAX
    probe_left = right - GOLDEN_RATIO * (right - left)
    probe_right = left + GOLDEN_RATIO * (right - left)
    value_left = objective(probe_left)
    value_right = objective(probe_right)

    for _ in range(OPTIMIZATION_STEPS):
        if value_left < value_right:
            right = probe_right
            probe_right = probe_left
            value_right = value_left
            probe_left = right - GOLDEN_RATIO * (right - left)
            value_left = objective(probe_left)
        else:
            left = probe_left
            probe_left = probe_right
            value_left = value_right
            probe_right = left + GOLDEN_RATIO * (right - left)
            value_right = objective(probe_right)
    return (left + right) / 2.0
