"""Outcome-window settlement over provider-neutral physical evidence."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import Field

from evolution.api import (
    EvolutionModel,
    OutcomeEvidenceSample,
    OutcomeObservation,
    OutcomeWindow,
    OutcomeWindowCloseReason,
    OwnerHypothesis,
    PulseRecord,
    SettlementTarget,
)


class SettlementPolicy(EvolutionModel):
    minimum_evidence_coverage: float = Field(default=0.5, ge=0.0, le=1.0)
    minimum_owner_confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ConsequenceSettler:
    """Settle expected predicates only after their observation windows close."""

    def __init__(self, *, policy: SettlementPolicy | None = None) -> None:
        self.policy = policy or SettlementPolicy()

    def settle(
        self,
        *,
        targets: Iterable[SettlementTarget],
        samples: Iterable[OutcomeEvidenceSample],
        at_ms: int,
        close_reason: OutcomeWindowCloseReason | None = None,
    ) -> tuple[OutcomeObservation, ...]:
        if at_ms < 0:
            raise ValueError("settlement time must be non-negative")
        target_rows = tuple(targets)
        sample_rows = tuple(samples)
        target_keys = [(item.transition_id, item.predicate) for item in target_rows]
        if len(target_keys) != len(set(target_keys)):
            raise ValueError("settlement targets must be unique per predicate")
        known_keys = set(target_keys)
        unknown_keys = sorted(
            {
                (item.transition_id, item.predicate)
                for item in sample_rows
                if (item.transition_id, item.predicate) not in known_keys
            }
        )
        if unknown_keys:
            raise ValueError(f"evidence sample references an unknown target: {unknown_keys[0]}")

        observations: list[OutcomeObservation] = []
        for target in target_rows:
            if at_ms < target.outcome_window.opened_at_ms:
                raise ValueError("settlement time cannot precede an outcome window")
            window = self._window_at(
                target.outcome_window,
                at_ms=at_ms,
                close_reason=close_reason,
            )
            horizon = window.closed_at_ms if window.closed_at_ms is not None else at_ms
            relevant = tuple(
                sorted(
                    (
                        item
                        for item in sample_rows
                        if item.transition_id == target.transition_id
                        and item.predicate == target.predicate
                        and window.opened_at_ms <= item.observed_at_ms <= horizon
                    ),
                    key=lambda item: (
                        item.observed_at_ms,
                        item.state,
                        item.evidence_refs,
                        item.side_effects,
                    ),
                )
            )
            observations.append(self._settle_target(target, window, relevant, at_ms=at_ms))
        return tuple(observations)

    def _window_at(
        self,
        window: OutcomeWindow,
        *,
        at_ms: int,
        close_reason: OutcomeWindowCloseReason | None,
    ) -> OutcomeWindow:
        if window.closed:
            if at_ms < (window.closed_at_ms or 0):
                raise ValueError("settlement time cannot precede a closed outcome window")
            return window
        if window.deadline_at_ms is not None and at_ms >= window.deadline_at_ms:
            return window.model_copy(
                update={
                    "closed_at_ms": window.deadline_at_ms,
                    "close_reason": "deadline",
                }
            )
        if close_reason is None:
            return window
        if close_reason == "deadline":
            raise ValueError("deadline closure requires reaching deadline_at_ms")
        return window.model_copy(update={"closed_at_ms": at_ms, "close_reason": close_reason})

    def _settle_target(
        self,
        target: SettlementTarget,
        window: OutcomeWindow,
        samples: tuple[OutcomeEvidenceSample, ...],
        *,
        at_ms: int,
    ) -> OutcomeObservation:
        latest = self._latest_samples(samples)
        coverage = max((item.evidence_coverage for item in latest), default=0.0)
        state = self._state(window=window, latest=latest)
        owner_hypotheses = self._owner_hypotheses(
            latest, minimum_confidence=self.policy.minimum_owner_confidence
        )
        owner = (
            owner_hypotheses[0].owner
            if owner_hypotheses
            else next(
                (item.owner for item in latest if item.owner != "unknown"),
                "unknown",
            )
        )
        reversibility = "unknown"
        if any(item.reversibility == "irreversible" for item in samples):
            reversibility = "irreversible"
        elif any(item.reversibility == "reversible" for item in samples):
            reversibility = "reversible"
        observed_at_ms = (
            max(item.observed_at_ms for item in latest)
            if latest
            else window.closed_at_ms
            if window.closed_at_ms is not None
            else at_ms
        )
        return OutcomeObservation(
            transition_id=target.transition_id,
            predicate=target.predicate,
            state=state,
            evidence_coverage=coverage,
            observed_at_ms=observed_at_ms,
            outcome_window_closed=window.closed,
            outcome_window=window,
            side_effects=tuple(
                dict.fromkeys(effect for item in samples for effect in item.side_effects)
            ),
            reversibility=reversibility,
            owner=owner,
            owner_hypotheses=owner_hypotheses,
            evidence_refs=tuple(
                dict.fromkeys(ref for item in samples for ref in item.evidence_refs)
            ),
        )

    def _state(
        self,
        *,
        window: OutcomeWindow,
        latest: tuple[OutcomeEvidenceSample, ...],
    ) -> str:
        if not window.closed:
            return "pending"
        eligible = tuple(
            item
            for item in latest
            if item.evidence_coverage >= self.policy.minimum_evidence_coverage
        )
        states = {item.state for item in eligible}
        if len(states) == 1 and "unknown" not in states:
            return next(iter(states))
        return "unknown"

    @staticmethod
    def _latest_samples(
        samples: tuple[OutcomeEvidenceSample, ...],
    ) -> tuple[OutcomeEvidenceSample, ...]:
        if not samples:
            return ()
        latest_at = max(item.observed_at_ms for item in samples)
        return tuple(item for item in samples if item.observed_at_ms == latest_at)

    @staticmethod
    def _owner_hypotheses(
        samples: tuple[OutcomeEvidenceSample, ...],
        *,
        minimum_confidence: float,
    ) -> tuple[OwnerHypothesis, ...]:
        by_owner: dict[str, OwnerHypothesis] = {}
        for sample in samples:
            for hypothesis in sample.owner_hypotheses:
                current = by_owner.get(hypothesis.owner)
                if current is None or hypothesis.confidence > current.confidence:
                    by_owner[hypothesis.owner] = hypothesis
        return tuple(
            sorted(
                (
                    item
                    for item in by_owner.values()
                    if item.confidence >= minimum_confidence
                ),
                key=lambda item: (-item.confidence, item.owner),
            )
        )


def settle_pending(records: tuple[PulseRecord, ...]) -> tuple[PulseRecord, ...]:
    """Finalize legacy PULSE records that reached episode close without evidence."""
    return tuple(
        record.model_copy(update={"observed": "unknown", "settled_at_ms": record.time_cost_ms})
        if record.observed == "pending"
        else record
        for record in records
    )


__all__ = ["ConsequenceSettler", "SettlementPolicy", "settle_pending"]
