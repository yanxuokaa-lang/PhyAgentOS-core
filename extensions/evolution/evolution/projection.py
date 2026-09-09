"""Provider-neutral projection helpers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol

from pydantic import Field

from evolution.api import (
    EpisodeProjection,
    EpisodeProjectionPort,
    EvolutionModel,
    OutcomeEvidenceSample,
    OutcomeObservation,
    OutcomeWindowCloseReason,
    SettlementTarget,
    TransitionExpectation,
)
from evolution.settlement import ConsequenceSettler


class EpisodeMetadata(EvolutionModel):
    episode_id: str = Field(min_length=1, max_length=200)
    root_task_id: str = Field(min_length=1, max_length=200)
    action_cost: float = Field(default=0.0, ge=0.0)
    time_cost_ms: int = Field(default=0, ge=0)


class TransitionProjectionPort(Protocol):
    def project_transitions(self, episode: Any) -> Sequence[TransitionExpectation]: ...


class OutcomeProjectionPort(Protocol):
    def project_outcomes(
        self,
        episode: Any,
        transitions: tuple[TransitionExpectation, ...],
    ) -> Sequence[OutcomeObservation]: ...


class SettledOutcomeProjectionPort:
    """Project provider evidence through the shared consequence settler."""

    def __init__(
        self,
        *,
        target_projector: Callable[
            [Any, tuple[TransitionExpectation, ...]], Sequence[SettlementTarget]
        ],
        sample_projector: Callable[
            [Any, tuple[TransitionExpectation, ...]], Sequence[OutcomeEvidenceSample]
        ],
        settler: ConsequenceSettler | None = None,
        at_ms_projector: Callable[[Any], int] | None = None,
        close_reason_projector: Callable[[Any], OutcomeWindowCloseReason | None] | None = None,
    ) -> None:
        self._target_projector = target_projector
        self._sample_projector = sample_projector
        self._settler = settler or ConsequenceSettler()
        self._at_ms_projector = at_ms_projector or (
            lambda episode: int(getattr(episode, "time_cost_ms", 0))
        )
        self._close_reason_projector = close_reason_projector

    def project_outcomes(
        self,
        episode: Any,
        transitions: tuple[TransitionExpectation, ...],
    ) -> Sequence[OutcomeObservation]:
        close_reason = (
            self._close_reason_projector(episode)
            if self._close_reason_projector is not None
            else None
        )
        return self._settler.settle(
            targets=self._target_projector(episode, transitions),
            samples=self._sample_projector(episode, transitions),
            at_ms=self._at_ms_projector(episode),
            close_reason=close_reason,
        )


class ComposedEpisodeProjectionPort:
    """Combine host identity, Skill transitions, and provider outcomes."""

    capabilities = frozenset({"transition_expectation", "outcome_observation"})

    def __init__(
        self,
        *,
        metadata_projector: Callable[[Any], EpisodeMetadata | None],
        transition_port: TransitionProjectionPort
        | Callable[[Any], Sequence[TransitionExpectation]],
        outcome_port: OutcomeProjectionPort
        | Callable[
            [Any, tuple[TransitionExpectation, ...]],
            Sequence[OutcomeObservation],
        ],
    ) -> None:
        self._metadata_projector = metadata_projector
        self._transition_port = transition_port
        self._outcome_port = outcome_port

    def project(self, episode: Any) -> EpisodeProjection | None:
        metadata = self._metadata_projector(episode)
        if metadata is None:
            return None
        if callable(self._transition_port):
            transitions = tuple(self._transition_port(episode))
        else:
            transitions = tuple(self._transition_port.project_transitions(episode))
        if callable(self._outcome_port):
            observations = tuple(self._outcome_port(episode, transitions))
        else:
            observations = tuple(self._outcome_port.project_outcomes(episode, transitions))
        return EpisodeProjection(
            episode_id=metadata.episode_id,
            root_task_id=metadata.root_task_id,
            transitions=transitions,
            observations=observations,
            action_cost=metadata.action_cost,
            time_cost_ms=metadata.time_cost_ms,
        )


class CallableProjectionPort:
    def __init__(self, projector: Callable[[Any], EpisodeProjection | None]) -> None:
        self._projector = projector

    def project(self, episode: Any) -> EpisodeProjection | None:
        return self._projector(episode)


def project_episode(
    episode: Any,
    *,
    port: EpisodeProjectionPort | Callable[[Any], EpisodeProjection | None],
) -> EpisodeProjection | None:
    if callable(port):
        return port(episode)
    return port.project(episode)


__all__ = [
    "CallableProjectionPort",
    "ComposedEpisodeProjectionPort",
    "EpisodeMetadata",
    "OutcomeProjectionPort",
    "SettledOutcomeProjectionPort",
    "TransitionProjectionPort",
    "project_episode",
]
