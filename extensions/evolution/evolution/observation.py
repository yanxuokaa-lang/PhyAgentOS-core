"""Future-use observations for promoted candidates."""

from __future__ import annotations

from collections.abc import Iterable
from statistics import fmean
from typing import Literal

from pydantic import Field

from evolution.api import EvolutionModel


class FutureUseObservation(EvolutionModel):
    method_id: str
    candidate_id: str
    task_id: str
    comparison_key: str
    binding_role: Literal["parent", "candidate"]
    split: Literal["matched", "held_out", "hazard"]
    outcome: Literal["success", "failure", "unknown"]
    side_effects: tuple[str, ...] = ()
    action_cost: float = Field(default=0.0, ge=0.0)
    time_cost_ms: int = Field(default=0, ge=0)


class FutureUseComparison(EvolutionModel):
    method_id: str
    candidate_id: str
    paired_tasks: int = Field(ge=1)
    parent_success_rate: float = Field(ge=0.0, le=1.0)
    candidate_success_rate: float = Field(ge=0.0, le=1.0)
    success_gain: float
    action_cost_delta: float
    time_cost_delta_ms: float
    side_effect_rate_delta: float
    interference_delta: float
    forward_transfer_gain: float | None = None


class FutureUseObserver:
    def observe(
        self,
        *,
        method_id: str,
        candidate_id: str,
        task_id: str,
        binding_role: Literal["parent", "candidate"] = "candidate",
        split: Literal["matched", "held_out", "hazard"] = "matched",
        comparison_key: str | None = None,
        outcome: Literal["success", "failure", "unknown"],
        side_effects: tuple[str, ...] = (),
        action_cost: float = 0.0,
        time_cost_ms: int = 0,
    ) -> FutureUseObservation:
        return FutureUseObservation(
            method_id=method_id,
            candidate_id=candidate_id,
            task_id=task_id,
            comparison_key=comparison_key or task_id,
            binding_role=binding_role,
            split=split,
            outcome=outcome,
            side_effects=tuple(dict.fromkeys(side_effects)),
            action_cost=action_cost,
            time_cost_ms=time_cost_ms,
        )

    def compare(
        self,
        *,
        method_id: str,
        candidate_id: str,
        observations: Iterable[FutureUseObservation],
    ) -> FutureUseComparison:
        relevant = [
            item
            for item in observations
            if item.method_id == method_id and item.candidate_id == candidate_id
        ]
        parent: dict[str, FutureUseObservation] = {}
        candidate: dict[str, FutureUseObservation] = {}
        for item in relevant:
            target = parent if item.binding_role == "parent" else candidate
            if item.comparison_key in target:
                raise ValueError("future-use comparison accepts one observation per role and key")
            target[item.comparison_key] = item
        keys = sorted(parent.keys() & candidate.keys())
        mismatched = [key for key in keys if parent[key].split != candidate[key].split]
        if mismatched:
            raise ValueError("parent and candidate comparison pairs must use the same split")
        pairs = [
            (parent[key], candidate[key])
            for key in keys
            if parent[key].outcome != "unknown" and candidate[key].outcome != "unknown"
        ]
        if not pairs:
            raise ValueError(
                "future-use comparison requires at least one known parent/candidate pair"
            )

        def success(item: FutureUseObservation) -> float:
            return 1.0 if item.outcome == "success" else 0.0

        parent_success_rate = fmean(success(before) for before, _after in pairs)
        candidate_success_rate = fmean(success(after) for _before, after in pairs)
        side_effect_rate_delta = fmean(
            float(bool(after.side_effects)) - float(bool(before.side_effects))
            for before, after in pairs
        )
        hazard_pairs = [pair for pair in pairs if pair[0].split == "hazard"]
        interference_delta = (
            fmean(
                float(after.outcome == "failure") - float(before.outcome == "failure")
                for before, after in hazard_pairs
            )
            if hazard_pairs
            else 0.0
        )
        held_out_pairs = [pair for pair in pairs if pair[0].split == "held_out"]
        forward_transfer_gain = (
            fmean(success(after) - success(before) for before, after in held_out_pairs)
            if held_out_pairs
            else None
        )
        return FutureUseComparison(
            method_id=method_id,
            candidate_id=candidate_id,
            paired_tasks=len(pairs),
            parent_success_rate=parent_success_rate,
            candidate_success_rate=candidate_success_rate,
            success_gain=candidate_success_rate - parent_success_rate,
            action_cost_delta=fmean(
                after.action_cost - before.action_cost for before, after in pairs
            ),
            time_cost_delta_ms=fmean(
                after.time_cost_ms - before.time_cost_ms for before, after in pairs
            ),
            side_effect_rate_delta=side_effect_rate_delta,
            interference_delta=interference_delta,
            forward_transfer_gain=forward_transfer_gain,
        )


class FutureUseObservationBuilder:
    """Build one observation from host-owned binding and outcome facts.

    The builder intentionally requires all comparison metadata from the host;
    it cannot infer whether a promoted candidate was actually activated.
    """

    def build(
        self,
        *,
        method_id: str,
        candidate_id: str,
        task_id: str,
        binding_candidate_id: str | None,
        binding_confirmed: bool,
        binding_role: Literal["parent", "candidate"],
        split: Literal["matched", "held_out", "hazard"],
        comparison_key: str,
        outcome: Literal["success", "failure", "unknown"],
        side_effects: tuple[str, ...] = (),
        action_cost: float = 0.0,
        time_cost_ms: int = 0,
    ) -> FutureUseObservation:
        if not candidate_id.strip() or not method_id.strip() or not task_id.strip():
            raise ValueError("method_id, candidate_id, and task_id must be non-empty")
        if not comparison_key.strip():
            raise ValueError("comparison_key must be non-empty")
        if not binding_confirmed:
            raise ValueError("future-use observation requires confirmed Skill binding")
        if binding_role == "candidate" and binding_candidate_id != candidate_id:
            raise ValueError("candidate binding does not match candidate_id")
        if binding_role == "parent" and binding_candidate_id is not None:
            raise ValueError("parent binding cannot carry a candidate id")
        return FutureUseObservation(
            method_id=method_id,
            candidate_id=candidate_id,
            task_id=task_id,
            comparison_key=comparison_key,
            binding_role=binding_role,
            split=split,
            outcome=outcome,
            side_effects=tuple(dict.fromkeys(side_effects)),
            action_cost=action_cost,
            time_cost_ms=time_cost_ms,
        )


__all__ = [
    "FutureUseComparison",
    "FutureUseObservation",
    "FutureUseObservationBuilder",
    "FutureUseObserver",
]
