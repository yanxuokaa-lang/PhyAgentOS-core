"""Independent candidate selection over evaluation receipts."""

from __future__ import annotations

from collections.abc import Iterable
from statistics import fmean
from typing import Literal

from pydantic import Field

from evolution.api import (
    CandidateProposal,
    EvaluationDecision,
    EvaluationMetrics,
    EvaluationReceipt,
    EvolutionModel,
)


class SelectionPolicy(EvolutionModel):
    success_gain_weight: float = Field(default=1.0, ge=0.0)
    action_cost_weight: float = Field(default=0.0, ge=0.0)
    time_cost_weight_per_second: float = Field(default=0.0, ge=0.0)
    side_effect_rate_weight: float = Field(default=0.0, ge=0.0)
    interference_weight: float = Field(default=0.0, ge=0.0)
    minimum_utility: float = 0.0


class CandidateEvaluator:
    """Select a proposal using matched, held-out, and hazard receipts."""

    def __init__(self, *, policy: SelectionPolicy | None = None) -> None:
        self.policy = policy or SelectionPolicy()

    def decide(
        self,
        proposal: CandidateProposal,
        *,
        receipts: Iterable[EvaluationReceipt],
    ) -> EvaluationDecision:
        relevant = [
            receipt
            for receipt in receipts
            if receipt.method_id == proposal.method_id
            and receipt.candidate_id == proposal.candidate_id
        ]
        duplicate_keys = [
            (
                item.split,
                item.trial_id
                or item.comparison_key
                or item.model_dump_json(exclude={"verdict"}),
            )
            for item in relevant
        ]
        if len(duplicate_keys) != len(set(duplicate_keys)):
            return EvaluationDecision(
                method_id=proposal.method_id,
                candidate_id=proposal.candidate_id,
                decision="hold",
                utility=0.0,
                receipt_count=len(relevant),
                reason="evaluation receipts contain duplicate trial identities",
            )
        by_split = {
            split: [item for item in relevant if item.split == split]
            for split in ("matched", "held_out", "hazard")
        }
        missing = [split for split, items in by_split.items() if not items]
        if missing:
            return EvaluationDecision(
                method_id=proposal.method_id,
                candidate_id=proposal.candidate_id,
                decision="hold",
                utility=0.0,
                receipt_count=len(relevant),
                reason=f"evaluation receipts are missing: {', '.join(missing)}",
            )
        if any(item.verdict == "fail" for item in by_split["matched"] + by_split["hazard"]):
            return EvaluationDecision(
                method_id=proposal.method_id,
                candidate_id=proposal.candidate_id,
                decision="reject",
                utility=-1.0,
                receipt_count=len(relevant),
                reason="candidate failed a matched or hazard evaluation",
            )
        if any(item.verdict == "fail" for item in by_split["held_out"]):
            return EvaluationDecision(
                method_id=proposal.method_id,
                candidate_id=proposal.candidate_id,
                decision="reject",
                utility=-1.0,
                receipt_count=len(relevant),
                reason="candidate failed a held-out evaluation",
            )
        if any(item.verdict == "unknown" for item in relevant):
            return EvaluationDecision(
                method_id=proposal.method_id,
                candidate_id=proposal.candidate_id,
                decision="hold",
                utility=0.0,
                receipt_count=len(relevant),
                reason="candidate evidence is incomplete",
            )
        if any(item.metrics is None for item in relevant):
            return EvaluationDecision(
                method_id=proposal.method_id,
                candidate_id=proposal.candidate_id,
                decision="hold",
                utility=0.0,
                receipt_count=len(relevant),
                reason="before/after metrics are required for candidate selection",
            )
        held_out_metrics = [
            item.metrics for item in by_split["held_out"] if item.metrics is not None
        ]
        deltas = self._mean_deltas(held_out_metrics)
        hazard_metrics = [item.metrics for item in by_split["hazard"] if item.metrics is not None]
        deltas["interference_delta"] = self._mean_deltas(hazard_metrics)["interference_delta"]
        utility = (
            self.policy.success_gain_weight * deltas["success_gain"]
            - self.policy.action_cost_weight * deltas["action_cost_delta"]
            - self.policy.time_cost_weight_per_second * deltas["time_cost_delta_ms"] / 1000.0
            - self.policy.side_effect_rate_weight * deltas["side_effect_rate_delta"]
            - self.policy.interference_weight * deltas["interference_delta"]
        )
        decision: Literal["promote", "hold", "reject"] = (
            "promote" if utility > self.policy.minimum_utility else "reject"
        )
        return EvaluationDecision(
            method_id=proposal.method_id,
            candidate_id=proposal.candidate_id,
            decision=decision,
            utility=utility,
            **deltas,
            receipt_count=len(relevant),
            reason=(
                "held-out improvement passes matched and hazard checks"
                if decision == "promote"
                else "held-out result did not improve"
            ),
        )

    @staticmethod
    def _mean_deltas(metrics: list[EvaluationMetrics]) -> dict[str, float]:
        return {
            "success_gain": fmean(
                item.candidate_success_rate - item.baseline_success_rate for item in metrics
            ),
            "action_cost_delta": fmean(
                item.candidate_action_cost - item.baseline_action_cost for item in metrics
            ),
            "time_cost_delta_ms": fmean(
                item.candidate_time_cost_ms - item.baseline_time_cost_ms for item in metrics
            ),
            "side_effect_rate_delta": fmean(
                item.candidate_side_effect_rate - item.baseline_side_effect_rate for item in metrics
            ),
            "interference_delta": fmean(
                item.candidate_interference - item.baseline_interference for item in metrics
            ),
        }


__all__ = ["CandidateEvaluator", "EvaluationDecision", "SelectionPolicy"]
