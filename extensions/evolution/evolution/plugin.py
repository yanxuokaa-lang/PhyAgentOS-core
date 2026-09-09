"""Host adapter for optional evolution methods."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Any

from evolution.api import (
    CandidateLifecyclePort,
    CandidateProposal,
    EpisodeProjection,
    EpisodeProjectionPort,
    EvaluationDecision,
    EvaluationLifecyclePort,
    EvaluationReceipt,
    EvolutionEventSink,
)
from evolution.observation import (
    FutureUseComparison,
    FutureUseObservation,
    FutureUseObserver,
)
from evolution.projection import project_episode
from evolution.registry import EvolutionMethodRegistry

logger = logging.getLogger(__name__)


class EvolutionExtension:
    """Dispatch episode and evaluation events without owning PAOS state."""

    def __init__(
        self,
        *,
        registry: EvolutionMethodRegistry,
        projection_port: EpisodeProjectionPort | Callable[[Any], EpisodeProjection | None],
        event_sink: EvolutionEventSink | None = None,
        candidate_sink: Callable[[CandidateProposal], None] | None = None,
        candidate_lifecycle: CandidateLifecyclePort | None = None,
        future_use_sink: Callable[[FutureUseComparison], None] | None = None,
        available_projections: frozenset[str] | None = None,
    ) -> None:
        self.registry = registry
        self.projection_port = projection_port
        self.event_sink = event_sink
        self.candidate_sink = candidate_sink
        self.candidate_lifecycle = candidate_lifecycle
        self.future_use_sink = future_use_sink
        self._future_use = FutureUseObserver()
        self.available_projections = (
            available_projections
            if available_projections is not None
            else getattr(
                projection_port,
                "capabilities",
                frozenset({"transition_expectation", "outcome_observation"}),
            )
        )
        self.last_delivery_failed = False

    def on_episode_closed(self, episode: Any) -> tuple[CandidateProposal, ...]:
        self.last_delivery_failed = False
        try:
            if getattr(episode, "verification_mode", None) == "off":
                self._emit(
                    "episode_skipped",
                    str(getattr(episode, "episode_id", "unknown")),
                    {"reason": "verification_off"},
                )
                return ()
            projection = project_episode(episode, port=self.projection_port)
            if projection is None:
                return ()
            proposals: list[CandidateProposal] = []
            for method_id in self.registry.ids():
                method = self.registry.get(method_id)
                missing = method.required_projections - self.available_projections
                if missing:
                    self._emit(
                        "method_skipped",
                        projection.episode_id,
                        {
                            "method_id": method_id,
                            "missing_projections": sorted(missing),
                        },
                    )
                    continue
                try:
                    proposals.extend(method.process(projection))
                except Exception as exc:  # evolution remains fail-open
                    self._emit(
                        "method_failed",
                        projection.episode_id,
                        {"method_id": method_id, "error": type(exc).__name__},
                    )
                    logger.warning(
                        "Evolution method failed open: method=%s error=%s",
                        method_id,
                        type(exc).__name__,
                    )
            for proposal in proposals:
                submit = (
                    self.candidate_lifecycle.submit
                    if self.candidate_lifecycle is not None
                    else self.candidate_sink
                )
                if submit is not None:
                    try:
                        submit(proposal)
                    except Exception as exc:
                        self.last_delivery_failed = True
                        self._emit(
                            "candidate_sink_failed",
                            proposal.episode_id,
                            {"method_id": proposal.method_id, "error": type(exc).__name__},
                        )
                        continue
                self._emit(
                    "candidate_proposed",
                    proposal.episode_id,
                    {
                        "method_id": proposal.method_id,
                        "candidate_id": proposal.candidate_id,
                        "transition_id": proposal.transition_id,
                    },
                )
            return tuple(proposals)
        except Exception as exc:  # projection failures never affect task outcome
            episode_id = getattr(episode, "episode_id", "unknown")
            self._emit("projection_failed", str(episode_id), {"error": type(exc).__name__})
            logger.warning("Evolution projection failed open: error=%s", type(exc).__name__)
            return ()

    def on_candidate_evaluated(self, receipt: EvaluationReceipt) -> None:
        try:
            method = self.registry.get(receipt.method_id)
            method.on_candidate_evaluated(receipt)
            if isinstance(self.candidate_lifecycle, EvaluationLifecyclePort):
                self.candidate_lifecycle.record_evaluation(receipt)
            self._emit(
                "candidate_evaluated",
                receipt.candidate_id,
                {
                    "method_id": receipt.method_id,
                    "split": receipt.split,
                    "verdict": receipt.verdict,
                },
            )
        except Exception as exc:
            self._emit(
                "evaluation_failed",
                receipt.candidate_id,
                {"method_id": receipt.method_id, "error": type(exc).__name__},
            )
            logger.warning("Evolution evaluation failed open: error=%s", type(exc).__name__)

    def on_candidate_selected(self, decision: EvaluationDecision) -> None:
        """Forward a method-owned selection request without promoting a candidate."""
        try:
            self.registry.get(decision.method_id)
            if isinstance(self.candidate_lifecycle, EvaluationLifecyclePort):
                self.candidate_lifecycle.record_selection(decision)
            self._emit(
                "candidate_selected",
                decision.candidate_id,
                {
                    "method_id": decision.method_id,
                    "decision": decision.decision,
                    "receipt_count": decision.receipt_count,
                },
            )
        except Exception as exc:
            self._emit(
                "selection_failed",
                decision.candidate_id,
                {"method_id": decision.method_id, "error": type(exc).__name__},
            )
            logger.warning("Evolution selection failed open: error=%s", type(exc).__name__)

    def observe_future_use(
        self,
        *,
        method_id: str,
        candidate_id: str,
        observations: Iterable[FutureUseObservation],
    ) -> FutureUseComparison | None:
        """Compare host-provided parent/candidate observations when pairs exist."""
        try:
            comparison = self._future_use.compare(
                method_id=method_id,
                candidate_id=candidate_id,
                observations=observations,
            )
        except ValueError as exc:
            self._emit(
                "future_use_incomplete",
                candidate_id,
                {"method_id": method_id, "error": str(exc)},
            )
            return None
        if self.future_use_sink is not None:
            try:
                self.future_use_sink(comparison)
            except Exception as exc:
                self._emit(
                    "future_use_sink_failed",
                    candidate_id,
                    {"method_id": method_id, "error": type(exc).__name__},
                )
        self._emit(
            "future_use_compared",
            candidate_id,
            {
                "method_id": method_id,
                "paired_tasks": comparison.paired_tasks,
                "success_gain": comparison.success_gain,
                "forward_transfer_gain": comparison.forward_transfer_gain,
            },
        )
        return comparison

    def _emit(self, event_type: str, ref: str, payload: dict[str, Any]) -> None:
        if self.event_sink is not None:
            try:
                self.event_sink(event_type, ref, payload)
            except Exception as exc:
                logger.warning("Evolution event sink failed open: error=%s", type(exc).__name__)


__all__ = ["EvolutionExtension"]
