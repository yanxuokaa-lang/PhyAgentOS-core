from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MIN_TEMPERATURE = 1e-4


@dataclass(frozen=True, slots=True)
class CandidateDistribution:
    winner_index: int
    probabilities: tuple[float, ...]

    @property
    def winner_probability(self) -> float:
        return self.probabilities[self.winner_index]


def calibrated_distribution(
    vocabulary_logits: np.ndarray,
    candidate_token_ids: list[int] | tuple[int, ...],
    temperature: float,
) -> CandidateDistribution:
    if not candidate_token_ids:
        raise ValueError("At least one candidate token is required")
    if not np.isfinite(temperature) or temperature <= 0:
        raise ValueError("Temperature must be positive")

    scores = np.asarray(vocabulary_logits, dtype=np.float64)[list(candidate_token_ids)]
    if not np.all(np.isfinite(scores)):
        raise ValueError("Candidate logits must be finite")
    scaled = scores / max(temperature, MIN_TEMPERATURE)
    shifted = scaled - np.max(scaled)
    probabilities = np.exp(shifted)
    probabilities /= probabilities.sum()
    winner = int(np.argmax(probabilities))
    return CandidateDistribution(winner, tuple(float(value) for value in probabilities))
