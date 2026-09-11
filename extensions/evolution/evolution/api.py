"""Public contracts for optional PAOS evolution methods."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EvolutionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


OutcomeOwner = Literal[
    "workflow",
    "planner",
    "execution",
    "perception",
    "environment",
    "infrastructure",
    "unknown",
]
PatchSurface = Literal["expectation", "observation", "decision", "recovery"]
OutcomeWindowCloseReason = Literal["provider_settled", "deadline", "terminal_event", "interrupted"]


class OwnerHypothesis(EvolutionModel):
    owner: OutcomeOwner
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: tuple[str, ...] = ()


class OutcomeWindow(EvolutionModel):
    opened_at_ms: int = Field(ge=0)
    deadline_at_ms: int | None = Field(default=None, ge=0)
    closed_at_ms: int | None = Field(default=None, ge=0)
    close_reason: OutcomeWindowCloseReason | None = None

    @model_validator(mode="after")
    def valid_interval(self) -> "OutcomeWindow":
        if self.closed_at_ms is not None and self.closed_at_ms < self.opened_at_ms:
            raise ValueError("outcome window cannot close before it opens")
        if self.deadline_at_ms is not None and self.deadline_at_ms < self.opened_at_ms:
            raise ValueError("outcome window deadline cannot precede its opening")
        if (
            self.closed_at_ms is not None
            and self.deadline_at_ms is not None
            and self.closed_at_ms > self.deadline_at_ms
        ):
            raise ValueError("outcome window cannot close after its deadline")
        if (self.closed_at_ms is None) != (self.close_reason is None):
            raise ValueError("closed_at_ms and close_reason must be provided together")
        if self.close_reason == "deadline":
            if self.deadline_at_ms is None:
                raise ValueError("deadline closure requires deadline_at_ms")
            if self.closed_at_ms != self.deadline_at_ms:
                raise ValueError("deadline closure must occur at deadline_at_ms")
        return self

    @property
    def closed(self) -> bool:
        return self.closed_at_ms is not None


class TransitionExpectation(EvolutionModel):
    transition_id: str = Field(min_length=1, max_length=200)
    order: int = Field(ge=0)
    depends_on: tuple[str, ...] = ()
    expected_predicates: tuple[str, ...] = Field(min_length=1)
    preconditions: tuple[str, ...] = ()
    semantic_action: str | None = Field(default=None, min_length=1, max_length=300)
    allowed_side_effects: tuple[str, ...] = ()
    outcome_window_ms: int | None = Field(default=None, ge=0)
    skill_name: str | None = None
    skill_revision: str | None = None
    workflow_key: str | None = None
    applicability: tuple[str, ...] = ()

    @field_validator(
        "expected_predicates",
        "preconditions",
        "allowed_side_effects",
        "applicability",
    )
    @classmethod
    def normalized_items(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in values)
        if any(not item for item in normalized):
            raise ValueError("transition fields must contain non-empty items")
        if len(normalized) != len(set(normalized)):
            raise ValueError("transition fields must be unique")
        return normalized


class OutcomeObservation(EvolutionModel):
    transition_id: str = Field(min_length=1, max_length=200)
    predicate: str = Field(min_length=1, max_length=200)
    state: Literal["satisfied", "violated", "unknown", "pending"]
    evidence_coverage: float = Field(ge=0.0, le=1.0)
    observed_at_ms: int = Field(ge=0)
    outcome_window_closed: bool = False
    outcome_window: OutcomeWindow | None = None
    side_effects: tuple[str, ...] = ()
    reversibility: Literal["reversible", "irreversible", "unknown"] = "unknown"
    owner: OutcomeOwner = "unknown"
    owner_hypotheses: tuple[OwnerHypothesis, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def consistent_window(self) -> "OutcomeObservation":
        if self.outcome_window is not None:
            if self.outcome_window.closed != self.outcome_window_closed:
                raise ValueError("outcome_window_closed must match outcome_window")
            if self.observed_at_ms < self.outcome_window.opened_at_ms:
                raise ValueError("observation cannot precede its outcome window")
            if (
                self.outcome_window.deadline_at_ms is not None
                and self.observed_at_ms > self.outcome_window.deadline_at_ms
            ):
                raise ValueError("observation cannot follow its outcome window deadline")
            if (
                self.outcome_window.closed_at_ms is not None
                and self.observed_at_ms > self.outcome_window.closed_at_ms
            ):
                raise ValueError("observation cannot follow its closed outcome window")
        owners = [item.owner for item in self.owner_hypotheses]
        if len(owners) != len(set(owners)):
            raise ValueError("owner hypotheses must contain unique owners")
        return self


class SettlementTarget(EvolutionModel):
    transition_id: str = Field(min_length=1, max_length=200)
    predicate: str = Field(min_length=1, max_length=200)
    outcome_window: OutcomeWindow


class OutcomeEvidenceSample(EvolutionModel):
    transition_id: str = Field(min_length=1, max_length=200)
    predicate: str = Field(min_length=1, max_length=200)
    state: Literal["satisfied", "violated", "unknown"]
    evidence_coverage: float = Field(ge=0.0, le=1.0)
    observed_at_ms: int = Field(ge=0)
    side_effects: tuple[str, ...] = ()
    reversibility: Literal["reversible", "irreversible", "unknown"] = "unknown"
    owner: OutcomeOwner = "unknown"
    owner_hypotheses: tuple[OwnerHypothesis, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def unique_owner_hypotheses(self) -> "OutcomeEvidenceSample":
        owners = [item.owner for item in self.owner_hypotheses]
        if len(owners) != len(set(owners)):
            raise ValueError("owner hypotheses must contain unique owners")
        return self


class EpisodeProjection(EvolutionModel):
    episode_id: str = Field(min_length=1, max_length=200)
    root_task_id: str = Field(min_length=1, max_length=200)
    transitions: tuple[TransitionExpectation, ...] = Field(min_length=1)
    observations: tuple[OutcomeObservation, ...] = ()
    action_cost: float = Field(default=0.0, ge=0.0)
    time_cost_ms: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def consistent_transitions(self) -> "EpisodeProjection":
        identities = [item.transition_id for item in self.transitions]
        if len(identities) != len(set(identities)):
            raise ValueError("episode transition identities must be unique")
        if len({item.order for item in self.transitions}) != len(self.transitions):
            raise ValueError("episode transition order must be unique")
        known = set(identities)
        order_by_id = {item.transition_id: item.order for item in self.transitions}
        for transition in self.transitions:
            if any(dep not in known or order_by_id[dep] >= transition.order for dep in transition.depends_on):
                raise ValueError("transition dependencies must reference earlier declared transitions")
        if any(item.transition_id not in known for item in self.observations):
            raise ValueError("outcome observation references an unknown transition")
        predicates_by_transition = {
            item.transition_id: set(item.expected_predicates) for item in self.transitions
        }
        if any(
            item.predicate not in predicates_by_transition[item.transition_id]
            for item in self.observations
        ):
            raise ValueError("outcome observation references an unexpected predicate")
        observation_keys = [(item.transition_id, item.predicate) for item in self.observations]
        if len(observation_keys) != len(set(observation_keys)):
            raise ValueError("episode outcome observations must be unique per predicate")
        return self


class PulseRecord(EvolutionModel):
    transition_id: str
    order: int
    depends_on: tuple[str, ...] = ()
    predicate: str
    expected: Literal["satisfied"] = "satisfied"
    observed: Literal["satisfied", "violated", "unknown", "pending"]
    evidence_coverage: float = Field(ge=0.0, le=1.0)
    settled_at_ms: int | None = Field(default=None, ge=0)
    side_effects: tuple[str, ...] = ()
    unexpected_side_effects: tuple[str, ...] = ()
    reversibility: Literal["reversible", "irreversible", "unknown"] = "unknown"
    owner: OutcomeOwner = "unknown"
    owner_hypotheses: tuple[OwnerHypothesis, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    action_cost: float = Field(default=0.0, ge=0.0)
    time_cost_ms: int = Field(default=0, ge=0)


class TraceHypothesis(EvolutionModel):
    transition_id: str
    order: int
    predicates: tuple[str, ...] = Field(min_length=1)
    state: Literal["violated", "unknown"]
    score: float = Field(ge=0.0)
    evidence_coverage: float = Field(ge=0.0, le=1.0)
    owner: OutcomeOwner
    owner_hypotheses: tuple[OwnerHypothesis, ...] = ()
    reversibility: Literal["reversible", "irreversible", "unknown"] = "unknown"
    downstream_violations: tuple[str, ...] = ()


class TraceResult(EvolutionModel):
    episode_id: str
    ranked: tuple[TraceHypothesis, ...] = ()
    joint_cause_sets: tuple[tuple[str, ...], ...] = ()
    unknown_predicates: tuple[str, ...] = ()


class PatchInstruction(EvolutionModel):
    surface: PatchSurface
    operation: Literal["add", "replace", "remove"]
    target: str = Field(min_length=1, max_length=500)
    value: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def operation_has_value(self) -> "PatchInstruction":
        if self.operation in {"add", "replace"} and not self.value:
            raise ValueError("add and replace patch instructions require a value")
        if self.operation == "remove" and self.value is not None:
            raise ValueError("remove patch instructions cannot carry a value")
        return self


class CandidateProposal(EvolutionModel):
    method_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    candidate_id: str = Field(min_length=1, max_length=500)
    episode_id: str
    transition_id: str
    skill_name: str | None = None
    skill_revision: str | None = None
    workflow_key: str | None = None
    changed_surface: PatchSurface
    patch: tuple[PatchInstruction, ...] = Field(min_length=1)
    applicability: tuple[str, ...] = ()
    does_not_apply_when: tuple[str, ...] = ()
    reason: str = Field(min_length=1, max_length=1000)
    evidence_refs: tuple[str, ...] = ()
    expected_improvement: str = Field(min_length=1, max_length=500)


class EvaluationMetrics(EvolutionModel):
    baseline_success_rate: float = Field(ge=0.0, le=1.0)
    candidate_success_rate: float = Field(ge=0.0, le=1.0)
    baseline_action_cost: float = Field(ge=0.0)
    candidate_action_cost: float = Field(ge=0.0)
    baseline_time_cost_ms: float = Field(ge=0.0)
    candidate_time_cost_ms: float = Field(ge=0.0)
    baseline_side_effect_rate: float = Field(ge=0.0, le=1.0)
    candidate_side_effect_rate: float = Field(ge=0.0, le=1.0)
    baseline_interference: float = Field(ge=0.0)
    candidate_interference: float = Field(ge=0.0)
    attribution_precision: float | None = Field(default=None, ge=0.0, le=1.0)
    attribution_recall: float | None = Field(default=None, ge=0.0, le=1.0)


class EvaluationReceipt(EvolutionModel):
    method_id: str
    candidate_id: str
    split: Literal["matched", "held_out", "hazard"]
    verdict: Literal["pass", "fail", "unknown"]
    metrics: EvaluationMetrics | None = None
    trial_id: str | None = Field(default=None, min_length=1, max_length=200)
    comparison_key: str | None = Field(default=None, min_length=1, max_length=200)


class EvaluationDecision(EvolutionModel):
    method_id: str
    candidate_id: str
    decision: Literal["promote", "hold", "reject"]
    utility: float
    success_gain: float = 0.0
    action_cost_delta: float = 0.0
    time_cost_delta_ms: float = 0.0
    side_effect_rate_delta: float = 0.0
    interference_delta: float = 0.0
    receipt_count: int = Field(default=0, ge=0)
    reason: str = Field(min_length=1)


@runtime_checkable
class EvolutionMethod(Protocol):
    method_id: str
    required_projections: frozenset[str]

    def process(self, episode: EpisodeProjection) -> Sequence[CandidateProposal]: ...

    def on_candidate_evaluated(self, receipt: EvaluationReceipt) -> None: ...


@runtime_checkable
class EpisodeProjectionPort(Protocol):
    def project(self, episode: Any) -> EpisodeProjection | None: ...


EvolutionEventSink = Callable[[str, str, dict[str, Any]], None]


@runtime_checkable
class CandidateLifecyclePort(Protocol):
    """Host-owned candidate lifecycle adapter; extension never promotes directly."""

    def submit(self, proposal: CandidateProposal) -> None: ...


@runtime_checkable
class EvaluationLifecyclePort(Protocol):
    """Optional host port for evaluation evidence and selection decisions."""

    def record_evaluation(self, receipt: EvaluationReceipt) -> None: ...

    def record_selection(self, decision: EvaluationDecision) -> None: ...


__all__ = [
    "CandidateProposal",
    "CandidateLifecyclePort",
    "EpisodeProjection",
    "EpisodeProjectionPort",
    "EvaluationDecision",
    "EvaluationLifecyclePort",
    "EvaluationReceipt",
    "EvaluationMetrics",
    "EvolutionEventSink",
    "EvolutionMethod",
    "OutcomeEvidenceSample",
    "OutcomeOwner",
    "OutcomeObservation",
    "OutcomeWindow",
    "OutcomeWindowCloseReason",
    "OwnerHypothesis",
    "PatchInstruction",
    "PatchSurface",
    "PulseRecord",
    "SettlementTarget",
    "TraceHypothesis",
    "TraceResult",
    "TransitionExpectation",
]
