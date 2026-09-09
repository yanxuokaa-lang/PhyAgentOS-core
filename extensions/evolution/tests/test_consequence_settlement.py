from __future__ import annotations

import pytest
from pydantic import ValidationError

from evolution import (
    ConsequenceSettler,
    EpisodeProjection,
    OutcomeEvidenceSample,
    OutcomeObservation,
    OutcomeWindow,
    OwnerHypothesis,
    SettlementTarget,
    TransitionExpectation,
)
from evolution.methods.evophy import EvoPhyMethod


def _target(*, opened_at_ms: int = 100, deadline_at_ms: int = 1000) -> SettlementTarget:
    return SettlementTarget(
        transition_id="place",
        predicate="object-stable",
        outcome_window=OutcomeWindow(
            opened_at_ms=opened_at_ms,
            deadline_at_ms=deadline_at_ms,
        ),
    )


def _sample(
    *,
    state: str,
    observed_at_ms: int,
    evidence_coverage: float = 0.9,
    **updates,
) -> OutcomeEvidenceSample:
    return OutcomeEvidenceSample(
        transition_id="place",
        predicate="object-stable",
        state=state,
        observed_at_ms=observed_at_ms,
        evidence_coverage=evidence_coverage,
        **updates,
    )


def test_open_window_keeps_latest_evidence_pending():
    observation = ConsequenceSettler().settle(
        targets=(_target(),),
        samples=(_sample(state="satisfied", observed_at_ms=500),),
        at_ms=600,
    )[0]

    assert observation.state == "pending"
    assert observation.evidence_coverage == pytest.approx(0.9)
    assert observation.observed_at_ms == 500
    assert observation.outcome_window_closed is False
    assert observation.outcome_window is not None
    assert observation.outcome_window.closed is False


def test_deadline_settlement_observes_delayed_slip():
    observation = ConsequenceSettler().settle(
        targets=(_target(),),
        samples=(
            _sample(
                state="satisfied",
                observed_at_ms=300,
                side_effects=("temporary-support",),
                owner_hypotheses=(OwnerHypothesis(owner="environment", confidence=0.95),),
                evidence_refs=("artifact://fake/stable",),
            ),
            _sample(
                state="violated",
                observed_at_ms=900,
                side_effects=("slip",),
                reversibility="irreversible",
                owner="workflow",
                evidence_refs=("artifact://fake/slip",),
            ),
        ),
        at_ms=1200,
    )[0]

    assert observation.state == "violated"
    assert observation.observed_at_ms == 900
    assert observation.side_effects == ("temporary-support", "slip")
    assert observation.reversibility == "irreversible"
    assert observation.owner == "workflow"
    assert observation.evidence_refs == (
        "artifact://fake/stable",
        "artifact://fake/slip",
    )
    assert observation.outcome_window is not None
    assert observation.outcome_window.closed_at_ms == 1000
    assert observation.outcome_window.close_reason == "deadline"


@pytest.mark.parametrize("close_reason", ["terminal_event", "interrupted"])
def test_early_close_without_evidence_settles_unknown(close_reason):
    observation = ConsequenceSettler().settle(
        targets=(_target(),),
        samples=(),
        at_ms=500,
        close_reason=close_reason,
    )[0]

    assert observation.state == "unknown"
    assert observation.evidence_coverage == 0.0
    assert observation.observed_at_ms == 500
    assert observation.outcome_window is not None
    assert observation.outcome_window.close_reason == close_reason


def test_latest_low_coverage_evidence_does_not_reuse_earlier_success():
    observation = ConsequenceSettler().settle(
        targets=(_target(),),
        samples=(
            _sample(state="satisfied", observed_at_ms=300),
            _sample(
                state="violated",
                observed_at_ms=900,
                evidence_coverage=0.2,
            ),
        ),
        at_ms=1000,
    )[0]

    assert observation.state == "unknown"
    assert observation.evidence_coverage == pytest.approx(0.2)
    assert observation.observed_at_ms == 900


def test_same_time_conflicting_evidence_settles_unknown():
    observation = ConsequenceSettler().settle(
        targets=(_target(),),
        samples=(
            _sample(state="satisfied", observed_at_ms=900),
            _sample(state="violated", observed_at_ms=900),
        ),
        at_ms=1000,
    )[0]

    assert observation.state == "unknown"
    assert observation.evidence_coverage == pytest.approx(0.9)


def test_provider_can_close_early_with_owner_hypothesis():
    observation = ConsequenceSettler().settle(
        targets=(_target(),),
        samples=(
            _sample(
                state="satisfied",
                observed_at_ms=500,
                reversibility="reversible",
                owner_hypotheses=(
                    OwnerHypothesis(owner="workflow", confidence=0.8),
                    OwnerHypothesis(owner="execution", confidence=0.2),
                ),
            ),
        ),
        at_ms=600,
        close_reason="provider_settled",
    )[0]

    assert observation.state == "satisfied"
    assert observation.owner == "workflow"
    assert observation.reversibility == "reversible"
    assert observation.outcome_window is not None
    assert observation.outcome_window.closed_at_ms == 600
    assert observation.outcome_window.close_reason == "provider_settled"


def test_low_confidence_owner_hypothesis_does_not_override_direct_owner():
    observation = ConsequenceSettler().settle(
        targets=(_target(),),
        samples=(
            _sample(
                state="violated",
                observed_at_ms=900,
                owner="infrastructure",
                owner_hypotheses=(OwnerHypothesis(owner="workflow", confidence=0.01),),
            ),
        ),
        at_ms=1000,
    )[0]

    assert observation.owner == "infrastructure"
    assert observation.owner_hypotheses == ()


def test_evidence_for_unknown_target_is_rejected():
    sample = _sample(state="violated", observed_at_ms=500).model_copy(
        update={"predicate": "object-visible"}
    )

    with pytest.raises(ValueError, match="unknown target"):
        ConsequenceSettler().settle(
            targets=(_target(),),
            samples=(sample,),
            at_ms=1000,
        )


def test_outcome_window_rejects_invalid_deadline_semantics():
    with pytest.raises(ValidationError, match="deadline cannot precede"):
        OutcomeWindow(opened_at_ms=500, deadline_at_ms=499)

    with pytest.raises(ValidationError, match="must occur at deadline"):
        OutcomeWindow(
            opened_at_ms=100,
            deadline_at_ms=1000,
            closed_at_ms=900,
            close_reason="deadline",
        )

    with pytest.raises(ValidationError, match="follow its outcome window deadline"):
        OutcomeObservation(
            transition_id="place",
            predicate="object-stable",
            state="pending",
            evidence_coverage=0.5,
            observed_at_ms=1001,
            outcome_window_closed=False,
            outcome_window=OutcomeWindow(
                opened_at_ms=100,
                deadline_at_ms=1000,
            ),
        )


def test_settled_delayed_effect_flows_into_evophy_candidate():
    transition = TransitionExpectation(
        transition_id="place",
        order=0,
        expected_predicates=("object-stable",),
        skill_name="pick-place",
        skill_revision="1",
        workflow_key="pick-place",
        applicability=("object is held",),
    )
    observations = ConsequenceSettler().settle(
        targets=(_target(),),
        samples=(
            _sample(state="satisfied", observed_at_ms=300),
            _sample(
                state="violated",
                observed_at_ms=900,
                owner="workflow",
                evidence_refs=("artifact://fake/delayed-slip",),
            ),
        ),
        at_ms=1000,
    )
    episode = EpisodeProjection(
        episode_id="episode-settled",
        root_task_id="task-settled",
        transitions=(transition,),
        observations=observations,
        action_cost=1.0,
        time_cost_ms=1000,
    )

    proposals = EvoPhyMethod().process(episode)

    assert len(proposals) == 1
    assert proposals[0].transition_id == "place"
    assert proposals[0].evidence_refs == ("artifact://fake/delayed-slip",)
