"""Typed answers are assembled from logits, not generated text."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

import numpy as np

from litjev.scoring import calibrated_distribution

CONFIDENCE_METHOD = "normalized_gini_concentration_v1"


@dataclass(frozen=True)
class RawFieldScores:
    name: str
    logits: np.ndarray
    input_tokens: int
    provenance: dict = field(default_factory=dict)


class LogitProvider(Protocol):
    def score(self, state, schema) -> tuple[RawFieldScores, ...]: ...


@dataclass(frozen=True)
class ChoiceAnswer:
    type: Literal["choice"]
    choice: str
    probabilities: dict[str, float]
    confidence: float


@dataclass(frozen=True)
class ScoreAnswer:
    type: Literal["score"]
    score: float
    legend: dict
    probabilities: dict[str, float]
    confidence: float


@dataclass(frozen=True)
class NoulAnswer:
    type: Literal["noul"]
    noul: float


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int = 0


@dataclass(frozen=True)
class DecisionResponse:
    model: str
    answers: dict[str, ChoiceAnswer | ScoreAnswer | NoulAnswer]
    usage: Usage


@dataclass(frozen=True)
class Evaluation:
    result: DecisionResponse
    diagnostics: dict


def concentration(probabilities):
    """LitJev statistic, not a reproduction of Jev's unpublished formula."""
    count = len(probabilities)
    if count == 1:
        return 1.0
    return float(np.clip((count * sum(p * p for p in probabilities) - 1) / (count - 1), 0, 1))


class SchemaDecisionEngine:
    def __init__(self, provider, temperature=1.0, model_id="unknown", calibration_fitted=False):
        if not np.isfinite(temperature) or temperature <= 0:
            raise ValueError("Temperature must be finite and positive")
        self.provider = provider
        self.temperature = temperature
        self.model_id = model_id
        self.calibration_fitted = calibration_fitted

    def decide(self, state, schema):
        return self.evaluate(state, schema).result

    def evaluate(self, state, schema):
        scores = self.provider.score(state, schema)
        if tuple(row.name for row in scores) != schema.names:
            raise RuntimeError("Scorer returned mismatched fields")
        answers, fields = {}, {}
        for row in scores:
            question = schema[row.name]
            if len(row.logits) != len(question.choices):
                raise RuntimeError("Scorer returned mismatched candidates")
            distribution = calibrated_distribution(
                row.logits, list(range(len(question.choices))), self.temperature
            )
            probabilities = dict(zip(question.choices, distribution.probabilities, strict=True))
            confidence = concentration(distribution.probabilities)
            if question.type == "noul":
                answer = NoulAnswer("noul", probabilities["true"])
            elif question.type == "score":
                answer = ScoreAnswer(
                    "score",
                    sum(int(k) * p for k, p in probabilities.items()),
                    dict(zip(question.choices, question.descriptions, strict=True)),
                    probabilities,
                    confidence,
                )
            else:
                answer = ChoiceAnswer(
                    "choice", question.choices[distribution.winner_index], probabilities, confidence
                )
            answers[row.name] = answer
            fields[row.name] = {
                "logits": tuple(float(value) for value in row.logits),
                "probabilities": probabilities,
                "max_probability": distribution.winner_probability,
                "provenance": {**row.provenance, "temperature": self.temperature},
            }
        return Evaluation(
            DecisionResponse(self.model_id, answers, Usage(scores[0].input_tokens)),
            {
                "fields": fields,
                "forward_calls": 2,
                "calibration_fitted": self.calibration_fitted,
                "confidence_method": CONFIDENCE_METHOD,
            },
        )
