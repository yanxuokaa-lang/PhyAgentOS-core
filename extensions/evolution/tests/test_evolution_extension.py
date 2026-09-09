from __future__ import annotations

import json
import math
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from evolution.api import (
    EpisodeProjection,
    EvaluationDecision,
    EvaluationMetrics,
    EvaluationReceipt,
    OutcomeObservation,
    OutcomeWindow,
    OwnerHypothesis,
    PatchInstruction,
    TransitionExpectation,
)
from evolution.evaluation import CandidateEvaluator, SelectionPolicy
from evolution.experiment import EvaluationArtifactWriter, new_evaluation_manifest
from evolution.methods.evophy import EvoPhyMethod
from evolution.observation import FutureUseObserver
from evolution.plugin import EvolutionExtension
from evolution.projection import ComposedEpisodeProjectionPort, EpisodeMetadata
from evolution.pulse import PulseLogger
from evolution.registry import EvolutionMethodRegistry
from evolution.revision import local_skill_patch
from evolution.settlement import settle_pending
from evolution.trace import TraceAttributor, TracePolicy


def _metrics(
    *,
    success_gain: float = 0.2,
    action_cost_delta: float = 0.0,
    time_cost_delta_ms: float = 0.0,
    side_effect_rate_delta: float = 0.0,
    interference_delta: float = 0.0,
) -> EvaluationMetrics:
    return EvaluationMetrics(
        baseline_success_rate=0.5,
        candidate_success_rate=0.5 + success_gain,
        baseline_action_cost=2.0,
        candidate_action_cost=2.0 + action_cost_delta,
        baseline_time_cost_ms=2000.0,
        candidate_time_cost_ms=2000.0 + time_cost_delta_ms,
        baseline_side_effect_rate=0.2,
        candidate_side_effect_rate=0.2 + side_effect_rate_delta,
        baseline_interference=0.1,
        candidate_interference=0.1 + interference_delta,
    )


def _projection(*, delayed: bool = False, unknown: bool = False) -> EpisodeProjection:
    observations = [
        OutcomeObservation(
            transition_id="grasp",
            predicate="object-held",
            state="violated" if not unknown else "unknown",
            evidence_coverage=0.9 if not unknown else 0.1,
            observed_at_ms=1000,
            outcome_window_closed=True,
            owner="workflow",
            evidence_refs=("artifact://fake/grasp",),
        ),
        OutcomeObservation(
            transition_id="place",
            predicate="object-stable",
            state="violated" if delayed else "satisfied",
            evidence_coverage=0.9,
            observed_at_ms=3000 if delayed else 1200,
            outcome_window_closed=True,
            owner="workflow",
            evidence_refs=("artifact://fake/place",),
        ),
    ]
    return EpisodeProjection(
        episode_id="episode-fake",
        root_task_id="task-fake",
        transitions=(
            TransitionExpectation(
                transition_id="grasp",
                order=0,
                expected_predicates=("object-held",),
                skill_name="pick-place",
                skill_revision="1",
                workflow_key="pick-place",
                applicability=("object is visible",),
            ),
            TransitionExpectation(
                transition_id="place",
                order=1,
                expected_predicates=("object-stable",),
                skill_name="pick-place",
                skill_revision="1",
                workflow_key="pick-place",
                applicability=("object is held",),
            ),
        ),
        observations=tuple(observations),
        action_cost=2.0,
        time_cost_ms=3000,
    )


def test_evophy_generates_local_proposal_from_fake_physical_outcome():
    proposals: list[object] = []
    events: list[tuple[str, str, dict]] = []
    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([EvoPhyMethod()]),
        projection_port=lambda _: _projection(delayed=True),
        candidate_sink=proposals.append,
        event_sink=lambda event, ref, payload: events.append((event, ref, payload)),
    )

    result = extension.on_episode_closed(object())

    assert result
    assert proposals == list(result)
    assert {item.transition_id for item in result} == {"grasp", "place"}
    assert all(item.method_id == "evophy" for item in result)
    assert any(event[0] == "candidate_proposed" for event in events)


def test_evophy_skips_evidence_free_violation():
    base = _projection()
    projection = base.model_copy(
        update={
            "observations": (
                base.observations[0].model_copy(update={"evidence_refs": ()}),
                base.observations[1],
            )
        }
    )
    assert EvoPhyMethod().process(projection) == ()


@pytest.mark.parametrize(
    ("owner", "expected_surface"),
    [("workflow", "decision"), ("planner", "expectation"), ("perception", "observation")],
)
def test_evophy_selects_patch_surface_from_attributed_owner(owner, expected_surface):
    base = _projection().model_copy(
        update={
            "observations": tuple(
                item.model_copy(update={"owner": owner}) for item in _projection().observations
            )
        }
    )
    proposals = EvoPhyMethod().process(base)
    assert proposals
    assert all(item.changed_surface == expected_surface for item in proposals)


def test_evophy_selects_recovery_surface_for_shared_downstream_cause():
    base = _projection(delayed=True)
    shared = tuple(
        item.model_copy(update={"evidence_refs": ("artifact://fake/shared",)})
        for item in base.observations
    )
    proposal = EvoPhyMethod().process(base.model_copy(update={"observations": shared}))[0]
    assert proposal.changed_surface == "recovery"


def test_unknown_outcome_does_not_create_patch():
    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([EvoPhyMethod()]),
        projection_port=lambda _: _projection(unknown=True),
    )
    assert extension.on_episode_closed(object()) == ()


def test_verification_off_episode_is_not_learned():
    events: list[str] = []
    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([EvoPhyMethod()]),
        projection_port=lambda _: _projection(delayed=True),
        event_sink=lambda event, _ref, _payload: events.append(event),
    )
    episode = type("Episode", (), {"episode_id": "verification-off", "verification_mode": "off"})()

    assert extension.on_episode_closed(episode) == ()
    assert events == ["episode_skipped"]


def test_satisfied_outcomes_do_not_create_patch():
    projection = _projection().model_copy(
        update={
            "observations": tuple(
                item.model_copy(update={"state": "satisfied"})
                for item in _projection().observations
            )
        }
    )

    assert EvoPhyMethod().process(projection) == ()


def test_pulse_keeps_open_outcome_window_pending():
    projection = _projection().model_copy(
        update={
            "observations": tuple(
                item.model_copy(update={"outcome_window_closed": False})
                for item in _projection().observations
            )
        }
    )
    records = PulseLogger().build(projection)
    assert all(record.observed == "pending" for record in records)
    assert all(record.settled_at_ms is None for record in records)

    settled = settle_pending(records)
    assert all(record.observed == "unknown" for record in settled)
    assert all(record.settled_at_ms == projection.time_cost_ms for record in settled)


def test_trace_preserves_joint_cause_only_when_evidence_is_shared():
    projection = _projection(delayed=True).model_copy(
        update={
            "observations": tuple(
                item.model_copy(update={"evidence_refs": ("artifact://fake/shared",)})
                for item in _projection(delayed=True).observations
            )
        }
    )
    records = PulseLogger().build(projection)
    result = TraceAttributor().attribute(projection.episode_id, records)
    assert result.joint_cause_sets == (("grasp", "place"),)

    independent = TraceAttributor().attribute(
        _projection(delayed=True).episode_id,
        PulseLogger().build(_projection(delayed=True)),
    )
    assert independent.joint_cause_sets == ()


def test_candidate_and_event_sinks_fail_open():
    events: list[str] = []

    def failing_sink(_proposal):
        raise RuntimeError("fake sink")

    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([EvoPhyMethod()]),
        projection_port=lambda _: _projection(delayed=True),
        candidate_sink=failing_sink,
        event_sink=lambda event, _ref, _payload: events.append(event),
    )
    result = extension.on_episode_closed(object())
    assert result
    assert "candidate_sink_failed" in events


def test_candidate_lifecycle_port_receives_proposals():
    received = []

    class Lifecycle:
        def submit(self, proposal):
            received.append(proposal)

    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([EvoPhyMethod()]),
        projection_port=lambda _: _projection(delayed=True),
        candidate_lifecycle=Lifecycle(),
    )
    result = extension.on_episode_closed(object())
    assert received == list(result)


def test_event_sink_failure_does_not_block_candidates():
    def failing_event_sink(_event, _ref, _payload):
        raise RuntimeError("fake event sink")

    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([EvoPhyMethod()]),
        projection_port=lambda _: _projection(delayed=True),
        event_sink=failing_event_sink,
    )

    assert extension.on_episode_closed(object())


def test_candidate_evaluator_requires_all_three_splits():
    proposal = EvoPhyMethod().process(_projection(delayed=True))[0]
    evaluator = CandidateEvaluator()
    decision = evaluator.decide(proposal, receipts=[])
    assert decision.decision == "hold"
    decision = evaluator.decide(
        proposal,
        receipts=(
            EvaluationReceipt(
                method_id="evophy",
                candidate_id=proposal.candidate_id,
                split="matched",
                verdict="pass",
                metrics=_metrics(),
            ),
            EvaluationReceipt(
                method_id="evophy",
                candidate_id=proposal.candidate_id,
                split="held_out",
                verdict="pass",
                metrics=_metrics(),
            ),
            EvaluationReceipt(
                method_id="evophy",
                candidate_id=proposal.candidate_id,
                split="hazard",
                verdict="pass",
                metrics=_metrics(),
            ),
        ),
    )
    assert decision.decision == "promote"
    assert decision.success_gain == pytest.approx(0.2)


def test_candidate_evaluator_holds_duplicate_trial_receipts():
    proposal = EvoPhyMethod().process(_projection(delayed=True))[0]
    receipts = tuple(
        EvaluationReceipt(
            method_id="evophy",
            candidate_id=proposal.candidate_id,
            split=split,
            verdict="pass",
            metrics=_metrics(),
            trial_id="trial-1" if split == "held_out" else None,
        )
        for split in ("matched", "held_out", "hazard")
    ) + (
        EvaluationReceipt(
            method_id="evophy",
            candidate_id=proposal.candidate_id,
            split="held_out",
            verdict="pass",
            metrics=_metrics(),
            trial_id="trial-1",
        ),
    )
    decision = CandidateEvaluator().decide(proposal, receipts=receipts)
    assert decision.decision == "hold"
    assert "duplicate" in decision.reason


def test_matched_regression_rejects_candidate():
    proposal = EvoPhyMethod().process(_projection(delayed=True))[0]
    decision = CandidateEvaluator().decide(
        proposal,
        receipts=(
            EvaluationReceipt(
                method_id="evophy",
                candidate_id=proposal.candidate_id,
                split="matched",
                verdict="fail",
            ),
            EvaluationReceipt(
                method_id="evophy",
                candidate_id=proposal.candidate_id,
                split="held_out",
                verdict="pass",
            ),
            EvaluationReceipt(
                method_id="evophy",
                candidate_id=proposal.candidate_id,
                split="hazard",
                verdict="pass",
            ),
        ),
    )

    assert decision.decision == "reject"


def test_held_out_failure_rejects_candidate():
    proposal = EvoPhyMethod().process(_projection(delayed=True))[0]
    decision = CandidateEvaluator().decide(
        proposal,
        receipts=tuple(
            EvaluationReceipt(
                method_id="evophy",
                candidate_id=proposal.candidate_id,
                split=split,
                verdict="fail" if split == "held_out" else "pass",
                metrics=_metrics(),
            )
            for split in ("matched", "held_out", "hazard")
        ),
    )

    assert decision.decision == "reject"
    assert "held-out" in decision.reason


def test_future_use_observer_deduplicates_side_effects():
    observation = FutureUseObserver().observe(
        method_id="evophy",
        candidate_id="candidate-1",
        task_id="task-1",
        outcome="success",
        side_effects=("drift", "drift"),
    )
    assert observation.side_effects == ("drift",)


def test_composed_projection_keeps_host_skill_and_provider_ownership_separate():
    raw_episode = object()
    projection_port = ComposedEpisodeProjectionPort(
        metadata_projector=lambda episode: EpisodeMetadata(
            episode_id="episode-composed",
            root_task_id="task-composed",
            action_cost=3.0,
            time_cost_ms=4000,
        ),
        transition_port=lambda episode: _projection().transitions,
        outcome_port=lambda episode, transitions: _projection().observations,
    )

    projection = projection_port.project(raw_episode)

    assert projection is not None
    assert projection.episode_id == "episode-composed"
    assert projection.transitions[0].skill_name == "pick-place"
    assert projection.observations[0].evidence_refs == ("artifact://fake/grasp",)
    assert projection_port.capabilities == frozenset(
        {"transition_expectation", "outcome_observation"}
    )


def test_settled_outcome_projection_uses_deadline_and_conflict_semantics():
    from evolution.api import (
        OutcomeEvidenceSample,
        OutcomeWindow,
        SettlementTarget,
    )
    from evolution.projection import SettledOutcomeProjectionPort

    transition = _projection().transitions[0]
    port = SettledOutcomeProjectionPort(
        target_projector=lambda _episode, _transitions: (
            SettlementTarget(
                transition_id=transition.transition_id,
                predicate=transition.expected_predicates[0],
                outcome_window=OutcomeWindow(opened_at_ms=0, deadline_at_ms=100),
            ),
        ),
        sample_projector=lambda _episode, _transitions: (
            OutcomeEvidenceSample(
                transition_id=transition.transition_id,
                predicate=transition.expected_predicates[0],
                state="violated",
                evidence_coverage=0.9,
                observed_at_ms=100,
                evidence_refs=("artifact://fake/slip",),
            ),
        ),
        at_ms_projector=lambda _episode: 100,
    )
    observations = port.project_outcomes(object(), (transition,))
    assert observations[0].state == "violated"
    assert observations[0].outcome_window_closed is True


def test_extension_future_use_feedback_compares_parent_and_candidate():
    from evolution.observation import FutureUseObservation
    from evolution.plugin import EvolutionExtension
    from evolution.registry import EvolutionMethodRegistry

    events = []
    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([]),
        projection_port=lambda _episode: None,
        event_sink=lambda event, ref, payload: events.append((event, ref, payload)),
    )
    comparison = extension.observe_future_use(
        method_id="evophy",
        candidate_id="candidate-1",
        observations=(
            FutureUseObservation(
                method_id="evophy", candidate_id="candidate-1", task_id="t1",
                comparison_key="pair-1", binding_role="parent", split="held_out", outcome="failure",
            ),
            FutureUseObservation(
                method_id="evophy", candidate_id="candidate-1", task_id="t1",
                comparison_key="pair-1", binding_role="candidate", split="held_out", outcome="success",
            ),
        ),
    )
    assert comparison is not None
    assert comparison.forward_transfer_gain == 1.0
    assert events[-1][0] == "future_use_compared"


def test_extension_future_use_feedback_holds_unpaired_observations():
    from evolution.observation import FutureUseObservation
    from evolution.plugin import EvolutionExtension
    from evolution.registry import EvolutionMethodRegistry

    events = []
    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([]),
        projection_port=lambda _episode: None,
        event_sink=lambda event, ref, payload: events.append((event, ref, payload)),
    )
    result = extension.observe_future_use(
        method_id="evophy", candidate_id="candidate-1", observations=(
            FutureUseObservation(
                method_id="evophy", candidate_id="candidate-1", task_id="t1",
                comparison_key="pair-1", binding_role="candidate", split="matched", outcome="success",
            ),
        ),
    )
    assert result is None
    assert events[-1][0] == "future_use_incomplete"


def test_future_use_builder_requires_real_candidate_binding():
    from evolution.observation import FutureUseObservationBuilder

    builder = FutureUseObservationBuilder()
    observation = builder.build(
        method_id="evophy",
        candidate_id="candidate-1",
        task_id="task-1",
        binding_candidate_id="candidate-1",
        binding_confirmed=True,
        binding_role="candidate",
        split="held_out",
        comparison_key="family-a/object-b",
        outcome="success",
    )
    assert observation.binding_role == "candidate"
    with pytest.raises(ValueError, match="does not match"):
        builder.build(
            method_id="evophy", candidate_id="candidate-1", task_id="task-2",
            binding_candidate_id="candidate-2", binding_role="candidate",
            binding_confirmed=True,
            split="matched", comparison_key="pair-2", outcome="success",
        )


def test_future_use_builder_rejects_candidate_id_on_parent_binding():
    from evolution.observation import FutureUseObservationBuilder

    with pytest.raises(ValueError, match="parent binding"):
        FutureUseObservationBuilder().build(
            method_id="evophy", candidate_id="candidate-1", task_id="task-1",
            binding_candidate_id="candidate-1", binding_role="parent",
            binding_confirmed=True,
            split="matched", comparison_key="pair-1", outcome="failure",
        )


def test_future_use_builder_rejects_unconfirmed_binding():
    from evolution.observation import FutureUseObservationBuilder

    with pytest.raises(ValueError, match="confirmed Skill binding"):
        FutureUseObservationBuilder().build(
            method_id="evophy", candidate_id="candidate-1", task_id="task-1",
            binding_candidate_id="candidate-1", binding_confirmed=False,
            binding_role="candidate", split="matched", comparison_key="pair-1",
            outcome="success",
        )


def test_explicit_outcome_window_and_owner_hypothesis_reach_trace():
    projection = _projection().model_copy(
        update={
            "observations": (
                _projection()
                .observations[0]
                .model_copy(
                    update={
                        "owner": "unknown",
                        "owner_hypotheses": (
                            OwnerHypothesis(
                                owner="workflow",
                                confidence=0.8,
                                evidence_refs=("artifact://fake/owner",),
                            ),
                            OwnerHypothesis(owner="execution", confidence=0.2),
                        ),
                        "reversibility": "reversible",
                        "outcome_window": OutcomeWindow(
                            opened_at_ms=500,
                            closed_at_ms=1500,
                            close_reason="provider_settled",
                        ),
                        "outcome_window_closed": True,
                    }
                ),
                _projection().observations[1],
            )
        }
    )

    records = PulseLogger().build(projection)
    trace = TraceAttributor(policy=TracePolicy(minimum_coverage=0.5)).attribute(
        projection.episode_id, records
    )

    assert records[0].settled_at_ms == 1500
    assert trace.ranked[0].owner == "workflow"
    assert trace.ranked[0].owner_hypotheses[0].confidence == pytest.approx(0.8)
    assert trace.ranked[0].reversibility == "reversible"


@pytest.mark.parametrize("surface", ["expectation", "observation", "decision", "recovery"])
def test_local_skill_patch_supports_each_bounded_surface(surface):
    transition = _projection().transitions[0]
    proposal = local_skill_patch(
        method_id="evophy",
        episode_id="episode-patch",
        transition=transition,
        patch=(
            PatchInstruction(
                surface=surface,
                operation="add",
                target=f"transitions.grasp.{surface}",
                value="fake bounded update",
            ),
        ),
        applicability=transition.applicability,
        does_not_apply_when=("object is not visible",),
        reason="controlled fake fact",
        evidence_refs=("artifact://fake/patch",),
        expected_improvement="improve the controlled transition",
    )

    assert proposal.changed_surface == surface
    assert proposal.patch[0].target == f"transitions.grasp.{surface}"


def test_selection_policy_accounts_for_cost_and_interference():
    proposal = EvoPhyMethod().process(_projection(delayed=True))[0]
    policy = SelectionPolicy(
        success_gain_weight=1.0,
        action_cost_weight=0.1,
        time_cost_weight_per_second=0.1,
        side_effect_rate_weight=1.0,
        interference_weight=1.0,
    )
    receipts = tuple(
        EvaluationReceipt(
            method_id="evophy",
            candidate_id=proposal.candidate_id,
            split=split,
            verdict="pass",
            metrics=_metrics(
                success_gain=0.2,
                action_cost_delta=1.0,
                time_cost_delta_ms=1000.0,
                side_effect_rate_delta=0.1,
                interference_delta=0.1,
            ),
        )
        for split in ("matched", "held_out", "hazard")
    )

    decision = CandidateEvaluator(policy=policy).decide(proposal, receipts=receipts)

    assert decision.utility == pytest.approx(-0.2)
    assert decision.decision == "reject"


def test_selection_reads_interference_from_hazard_split():
    proposal = EvoPhyMethod().process(_projection(delayed=True))[0]
    policy = SelectionPolicy(success_gain_weight=1.0, interference_weight=1.0)
    receipts = tuple(
        EvaluationReceipt(
            method_id="evophy",
            candidate_id=proposal.candidate_id,
            split=split,
            verdict="pass",
            metrics=_metrics(
                success_gain=0.2,
                interference_delta=0.3 if split == "hazard" else 0.0,
            ),
        )
        for split in ("matched", "held_out", "hazard")
    )

    decision = CandidateEvaluator(policy=policy).decide(proposal, receipts=receipts)

    assert decision.interference_delta == pytest.approx(0.3)
    assert decision.utility == pytest.approx(-0.1)
    assert decision.decision == "reject"


def test_selection_holds_when_before_after_metrics_are_missing():
    proposal = EvoPhyMethod().process(_projection(delayed=True))[0]
    receipts = tuple(
        EvaluationReceipt(
            method_id="evophy",
            candidate_id=proposal.candidate_id,
            split=split,
            verdict="pass",
            metrics=None if split == "held_out" else _metrics(),
        )
        for split in ("matched", "held_out", "hazard")
    )

    decision = CandidateEvaluator().decide(proposal, receipts=receipts)

    assert decision.decision == "hold"
    assert "before/after metrics" in decision.reason


def test_evaluation_metrics_reject_non_finite_values():
    payload = _metrics().model_dump()
    payload["candidate_action_cost"] = math.nan

    with pytest.raises(ValidationError, match="finite number"):
        EvaluationMetrics.model_validate(payload)


def test_future_use_comparison_reports_paired_before_after_deltas():
    observer = FutureUseObserver()
    observations = (
        observer.observe(
            method_id="evophy",
            candidate_id="candidate-1",
            task_id="parent-task",
            comparison_key="held-out-1",
            binding_role="parent",
            split="held_out",
            outcome="failure",
            action_cost=3.0,
            time_cost_ms=3000,
            side_effects=("slip",),
        ),
        observer.observe(
            method_id="evophy",
            candidate_id="candidate-1",
            task_id="candidate-task",
            comparison_key="held-out-1",
            binding_role="candidate",
            split="held_out",
            outcome="success",
            action_cost=2.0,
            time_cost_ms=2500,
        ),
    )

    comparison = observer.compare(
        method_id="evophy",
        candidate_id="candidate-1",
        observations=observations,
    )

    assert comparison.success_gain == pytest.approx(1.0)
    assert comparison.forward_transfer_gain == pytest.approx(1.0)
    assert comparison.action_cost_delta == pytest.approx(-1.0)
    assert comparison.side_effect_rate_delta == pytest.approx(-1.0)


def test_future_use_without_held_out_pair_has_no_forward_transfer_claim():
    observer = FutureUseObserver()
    observations = (
        observer.observe(
            method_id="evophy",
            candidate_id="candidate-1",
            task_id="parent-task",
            comparison_key="matched-1",
            binding_role="parent",
            split="matched",
            outcome="failure",
        ),
        observer.observe(
            method_id="evophy",
            candidate_id="candidate-1",
            task_id="candidate-task",
            comparison_key="matched-1",
            binding_role="candidate",
            split="matched",
            outcome="success",
        ),
    )
    comparison = observer.compare(
        method_id="evophy", candidate_id="candidate-1", observations=observations
    )
    assert comparison.forward_transfer_gain is None


def test_future_use_comparison_rejects_split_mismatch():
    observer = FutureUseObserver()
    observations = (
        observer.observe(
            method_id="evophy",
            candidate_id="candidate-1",
            task_id="parent-task",
            comparison_key="pair-1",
            binding_role="parent",
            split="matched",
            outcome="failure",
        ),
        observer.observe(
            method_id="evophy",
            candidate_id="candidate-1",
            task_id="candidate-task",
            comparison_key="pair-1",
            binding_role="candidate",
            split="held_out",
            outcome="success",
        ),
    )

    with pytest.raises(ValueError, match="same split"):
        observer.compare(
            method_id="evophy",
            candidate_id="candidate-1",
            observations=observations,
        )


def test_future_use_comparison_rejects_duplicate_role_and_key():
    observer = FutureUseObserver()
    parent = observer.observe(
        method_id="evophy",
        candidate_id="candidate-1",
        task_id="parent-task",
        comparison_key="pair-1",
        binding_role="parent",
        split="held_out",
        outcome="failure",
    )
    candidate = observer.observe(
        method_id="evophy",
        candidate_id="candidate-1",
        task_id="candidate-task",
        comparison_key="pair-1",
        binding_role="candidate",
        split="held_out",
        outcome="success",
    )

    with pytest.raises(ValueError, match="one observation per role and key"):
        observer.compare(
            method_id="evophy",
            candidate_id="candidate-1",
            observations=(
                parent,
                parent.model_copy(update={"task_id": "duplicate"}),
                candidate,
            ),
        )


def test_evaluation_artifacts_record_reproducibility_and_never_overwrite(tmp_path):
    proposal = EvoPhyMethod().process(_projection(delayed=True))[0]
    policy = SelectionPolicy()
    receipts = tuple(
        EvaluationReceipt(
            method_id="evophy",
            candidate_id=proposal.candidate_id,
            split=split,
            verdict="pass",
            metrics=_metrics(),
        )
        for split in ("matched", "held_out", "hazard")
    )
    decision = CandidateEvaluator(policy=policy).decide(proposal, receipts=receipts)
    manifest = new_evaluation_manifest(
        slug="fake-eval",
        code_revision="local-uncommitted",
        config_ref="config://fake/eval-v1",
        random_seed=7,
        dataset_name="fake-long-horizon",
        dataset_version="v1",
        method_ids=("evophy",),
        selection_policy=policy,
        checkpoint_ref="checkpoint://fake/base",
        task_order=("task-a", "task-b"),
        now=datetime(2026, 9, 8, 10, 0, tzinfo=UTC),
    )
    writer = EvaluationArtifactWriter(tmp_path)

    paths = writer.write(
        manifest=manifest,
        receipts=receipts,
        decisions=(decision,),
    )

    saved_manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    saved_metrics = json.loads(paths.metrics.read_text(encoding="utf-8"))
    assert saved_manifest["random_seed"] == 7
    assert saved_manifest["dataset_version"] == "v1"
    assert saved_metrics["decision_counts"] == {"promote": 1}
    with pytest.raises(FileExistsError):
        writer.write(manifest=manifest, receipts=receipts, decisions=(decision,))


class _RecordingMethod:
    required_projections = frozenset()

    def __init__(self, method_id):
        self.method_id = method_id
        self.evaluations = []

    def process(self, episode):
        return ()

    def on_candidate_evaluated(self, receipt):
        self.evaluations.append(receipt)


def test_registry_isolates_methods_and_evaluation_receipts():
    evophy = _RecordingMethod("evophy")
    other = _RecordingMethod("other-method")
    registry = EvolutionMethodRegistry([evophy, other])
    assert registry.ids() == ("evophy", "other-method")
    with pytest.raises(ValueError, match="already registered"):
        registry.register(EvoPhyMethod())
    extension = EvolutionExtension(
        registry=registry,
        projection_port=lambda _: _projection(),
    )
    extension.on_candidate_evaluated(
        EvaluationReceipt(
            method_id="evophy",
            candidate_id="candidate-1",
            split="matched",
            verdict="pass",
        )
    )
    assert len(evophy.evaluations) == 1
    assert other.evaluations == []


def test_extension_forwards_evaluation_receipt_to_optional_lifecycle_port():
    method = _RecordingMethod("evophy")
    received = []

    class Lifecycle:
        def submit(self, proposal):
            return None

        def record_evaluation(self, receipt):
            received.append(receipt)

        def record_selection(self, decision):
            return None

    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([method]),
        projection_port=lambda _: _projection(),
        candidate_lifecycle=Lifecycle(),
    )
    receipt = EvaluationReceipt(
        method_id="evophy",
        candidate_id="candidate-1",
        split="matched",
        verdict="pass",
    )

    extension.on_candidate_evaluated(receipt)

    assert method.evaluations == [receipt]
    assert received == [receipt]


def test_extension_forwards_selection_request_to_optional_lifecycle_port():
    method = _RecordingMethod("evophy")
    received = []

    class Lifecycle:
        def submit(self, proposal):
            return None

        def record_evaluation(self, receipt):
            return None

        def record_selection(self, decision):
            received.append(decision)

    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([method]),
        projection_port=lambda _: _projection(),
        candidate_lifecycle=Lifecycle(),
    )
    decision = EvaluationDecision(
        method_id="evophy",
        candidate_id="candidate-1",
        decision="promote",
        utility=1.0,
        receipt_count=3,
        reason="fake evaluation supports promotion",
    )

    extension.on_candidate_selected(decision)

    assert received == [decision]


class _FailingMethod:
    method_id = "failing"
    required_projections = frozenset()

    def process(self, episode):
        raise RuntimeError("fake method failure")

    def on_candidate_evaluated(self, receipt):
        return None


def test_method_failure_does_not_block_other_methods():
    events: list[str] = []
    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([_FailingMethod(), EvoPhyMethod()]),
        projection_port=lambda _: _projection(delayed=True),
        event_sink=lambda event, _ref, _payload: events.append(event),
    )

    result = extension.on_episode_closed(object())

    assert result
    assert {item.method_id for item in result} == {"evophy"}
    assert "method_failed" in events


def test_candidate_identity_is_stable_across_supporting_episodes():
    method = EvoPhyMethod()
    first = method.process(_projection(delayed=True))[0]
    later_projection = _projection(delayed=True).model_copy(
        update={"episode_id": "episode-fake-later", "root_task_id": "task-fake-later"}
    )
    later = method.process(later_projection)[0]

    assert first.candidate_id == later.candidate_id
    assert first.episode_id != later.episode_id

    changed_transition = later_projection.transitions[0].model_copy(
        update={"applicability": ("object is visible", "surface is dry")}
    )
    changed_projection = later_projection.model_copy(
        update={"transitions": (changed_transition, later_projection.transitions[1])}
    )
    changed = method.process(changed_projection)[0]
    assert changed.candidate_id != first.candidate_id


def test_candidate_identity_changes_with_patch_content():
    transition = _projection().transitions[0]

    def proposal_for(value: str):
        return local_skill_patch(
            method_id="evophy",
            episode_id="episode-patch-identity",
            transition=transition,
            patch=(
                PatchInstruction(
                    surface="observation",
                    operation="add",
                    target="transitions.grasp.outcome_check",
                    value=value,
                ),
            ),
            applicability=transition.applicability,
            does_not_apply_when=(),
            reason="controlled fake fact",
            evidence_refs=("artifact://fake/patch",),
            expected_improvement="improve the controlled transition",
        )

    assert proposal_for("confirm hold").candidate_id != proposal_for("confirm force").candidate_id


def test_candidate_identity_stays_bounded_for_maximum_patch_content():
    transition = _projection().transitions[0]

    proposal = local_skill_patch(
        method_id="evophy",
        episode_id="episode-large-patch",
        transition=transition,
        patch=(
            PatchInstruction(
                surface="observation",
                operation="add",
                target="t" * 500,
                value="v" * 2000,
            ),
        ),
        applicability=transition.applicability,
        does_not_apply_when=(),
        reason="controlled boundary fact",
        evidence_refs=("artifact://fake/large-patch",),
        expected_improvement="exercise the documented patch boundary",
    )

    assert proposal.candidate_id.startswith("evophy_candidate_")
    assert len(proposal.candidate_id) <= 500


def test_candidate_identity_includes_negative_applicability_boundary():
    transition = _projection().transitions[0]
    patch = (
        PatchInstruction(
            surface="observation",
            operation="add",
            target="transitions.grasp.outcome_check",
            value="confirm hold",
        ),
    )

    def proposal_for(negative_scope: tuple[str, ...]):
        return local_skill_patch(
            method_id="evophy",
            episode_id="episode-negative-scope",
            transition=transition,
            patch=patch,
            applicability=transition.applicability,
            does_not_apply_when=negative_scope,
            reason="controlled scope fact",
            evidence_refs=("artifact://fake/scope",),
            expected_improvement="keep candidate scopes separate",
        )

    assert (
        proposal_for(("surface is wet",)).candidate_id
        != proposal_for(("surface is dry",)).candidate_id
    )


def test_projection_failure_returns_no_candidate_and_emits_event():
    events: list[str] = []

    def fail_projection(_episode):
        raise RuntimeError("fake projection failure")

    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([EvoPhyMethod()]),
        projection_port=fail_projection,
        event_sink=lambda event, _ref, _payload: events.append(event),
    )

    assert extension.on_episode_closed(object()) == ()
    assert events == ["projection_failed"]


def test_composed_projection_sub_port_failure_is_fail_open():
    events: list[str] = []

    def fail_outcome_projection(_episode, _transitions):
        raise RuntimeError("fake provider projection failure")

    port = ComposedEpisodeProjectionPort(
        metadata_projector=lambda _episode: EpisodeMetadata(
            episode_id="episode-composed-failure",
            root_task_id="task-composed-failure",
        ),
        transition_port=lambda _episode: _projection().transitions,
        outcome_port=fail_outcome_projection,
    )
    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([EvoPhyMethod()]),
        projection_port=port,
        event_sink=lambda event, _ref, _payload: events.append(event),
    )

    assert extension.on_episode_closed(object()) == ()
    assert events == ["projection_failed"]


def test_invalid_outcome_window_and_duplicate_observation_are_rejected():
    with pytest.raises(ValidationError, match="cannot close before"):
        OutcomeWindow(
            opened_at_ms=1000,
            closed_at_ms=999,
            close_reason="provider_settled",
        )

    projection = _projection()
    observation = projection.observations[0]
    with pytest.raises(ValidationError, match="unique per predicate"):
        EpisodeProjection.model_validate(
            projection.model_copy(update={"observations": (observation, observation)}).model_dump()
        )


def test_observation_for_unexpected_predicate_is_rejected():
    projection = _projection()
    with pytest.raises(ValidationError, match="unexpected predicate"):
        EpisodeProjection.model_validate(
            projection.model_copy(
                update={
                    "observations": (
                        projection.observations[0].model_copy(
                            update={"predicate": "object-stable-typo"}
                        ),
                        projection.observations[1],
                    )
                }
            ).model_dump()
        )


def test_unexpected_physical_side_effect_creates_candidate():
    projection = _projection(unknown=True).model_copy(
        update={
            "observations": (
                OutcomeObservation(
                    transition_id="grasp",
                    predicate="object-held",
                    state="satisfied",
                    evidence_coverage=0.9,
                    observed_at_ms=1200,
                    outcome_window_closed=True,
                    side_effects=("object-crushed",),
                    owner="workflow",
                    evidence_refs=("artifact://fake/force",),
                ),
                _projection().observations[1],
            )
        }
    )

    result = EvoPhyMethod().process(projection)

    assert len(result) == 1
    assert result[0].transition_id == "grasp"


def test_trace_ranks_earliest_observable_deviation_first():
    projection = _projection(delayed=True).model_copy(
        update={
            "observations": (
                _projection(delayed=True)
                .observations[0]
                .model_copy(update={"evidence_coverage": 0.5}),
                _projection(delayed=True)
                .observations[1]
                .model_copy(update={"evidence_coverage": 1.0}),
            )
        }
    )

    trace = TraceAttributor().attribute(projection.episode_id, PulseLogger().build(projection))

    assert tuple(item.transition_id for item in trace.ranked) == ("grasp", "place")


def test_trace_does_not_count_low_coverage_violation_as_downstream_evidence():
    projection = _projection(delayed=True).model_copy(
        update={
            "observations": (
                _projection(delayed=True).observations[0],
                _projection(delayed=True)
                .observations[1]
                .model_copy(update={"evidence_coverage": 0.1}),
            )
        }
    )

    trace = TraceAttributor().attribute(projection.episode_id, PulseLogger().build(projection))

    assert trace.ranked[0].transition_id == "grasp"
    assert trace.ranked[0].downstream_violations == ()
    assert trace.ranked[1].state == "unknown"


def test_trace_score_primary_policy_can_change_rank_without_changing_default_earliest_order():
    projection = _projection(delayed=True)
    records = PulseLogger().build(
        projection.model_copy(
            update={
                "observations": (
                    projection.observations[0].model_copy(update={"evidence_coverage": 0.5}),
                    projection.observations[1].model_copy(update={"evidence_coverage": 1.0}),
                )
            }
        )
    )
    default_trace = TraceAttributor().attribute(projection.episode_id, records)
    score_trace = TraceAttributor(
        policy=TracePolicy(score_primary=True, coverage_weight=100.0)
    ).attribute(projection.episode_id, records)

    assert default_trace.ranked[0].transition_id == "grasp"
    assert score_trace.ranked[0].transition_id == "place"


def test_method_is_skipped_when_projection_capability_is_missing():
    events: list[tuple[str, dict]] = []
    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([EvoPhyMethod()]),
        projection_port=lambda _: _projection(delayed=True),
        available_projections=frozenset({"transition_expectation"}),
        event_sink=lambda event, _ref, payload: events.append((event, payload)),
    )

    assert extension.on_episode_closed(object()) == ()
    assert events == [
        (
            "method_skipped",
            {
                "method_id": "evophy",
                "missing_projections": ["outcome_observation"],
            },
        )
    ]
