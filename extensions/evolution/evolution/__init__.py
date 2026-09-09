"""Optional evolution host with pluggable self-evolution methods."""

from evolution.api import (
    CandidateLifecyclePort,
    CandidateProposal,
    EpisodeProjection,
    EpisodeProjectionPort,
    EvaluationDecision,
    EvaluationLifecyclePort,
    EvaluationMetrics,
    EvaluationReceipt,
    EvolutionEventSink,
    EvolutionMethod,
    OutcomeEvidenceSample,
    OutcomeObservation,
    OutcomeWindow,
    OutcomeWindowCloseReason,
    OwnerHypothesis,
    PatchInstruction,
    PulseRecord,
    SettlementTarget,
    TraceHypothesis,
    TraceResult,
    TransitionExpectation,
)
from evolution.observation import (
    FutureUseComparison,
    FutureUseObservation,
    FutureUseObservationBuilder,
    FutureUseObserver,
)
from evolution.plugin import EvolutionExtension
from evolution.projection import (
    ComposedEpisodeProjectionPort,
    EpisodeMetadata,
    SettledOutcomeProjectionPort,
)
from evolution.pulse import PulseLogger
from evolution.registry import EvolutionMethodRegistry
from evolution.settlement import ConsequenceSettler, SettlementPolicy
from evolution.trace import TraceAttributor, TracePolicy

__all__ = [
    "CandidateProposal",
    "CandidateLifecyclePort",
    "EpisodeProjection",
    "EpisodeProjectionPort",
    "EpisodeMetadata",
    "ComposedEpisodeProjectionPort",
    "SettledOutcomeProjectionPort",
    "EvaluationDecision",
    "EvaluationLifecyclePort",
    "EvaluationMetrics",
    "EvaluationReceipt",
    "EvolutionEventSink",
    "EvolutionExtension",
    "EvolutionMethod",
    "FutureUseComparison",
    "FutureUseObservation",
    "FutureUseObservationBuilder",
    "FutureUseObserver",
    "EvolutionMethodRegistry",
    "ConsequenceSettler",
    "SettlementPolicy",
    "SettlementTarget",
    "OutcomeEvidenceSample",
    "OutcomeObservation",
    "OutcomeWindow",
    "OutcomeWindowCloseReason",
    "OwnerHypothesis",
    "PatchInstruction",
    "PulseLogger",
    "PulseRecord",
    "TraceAttributor",
    "TracePolicy",
    "TraceHypothesis",
    "TraceResult",
    "TransitionExpectation",
]
