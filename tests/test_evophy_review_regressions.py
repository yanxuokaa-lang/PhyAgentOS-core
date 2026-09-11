from pathlib import Path
from types import SimpleNamespace

import pytest
from test_evolution_extension_adapter import (
    _NoopAnalyzer,
    _proposal,
    _record_promote_evaluation,
    _write_skill,
)

from PhyAgentOS.agent.experience.contracts import SkillWorkflowProposal
from PhyAgentOS.agent.experience.coordinator import ExperienceCoordinator
from PhyAgentOS.agent.experience.evolution import SkillEvolutionError
from PhyAgentOS.agent.experience.evolution_extension_adapter import (
    EvolutionCandidateLifecycleAdapter,
)


def test_generic_support_cannot_consume_extension_candidate(tmp_path):
    _write_skill(tmp_path)
    coordinator = ExperienceCoordinator(workspace=tmp_path, analyzer=_NoopAnalyzer())
    adapter = EvolutionCandidateLifecycleAdapter(coordinator.store)
    adapter.submit(_proposal())
    generic = SkillWorkflowProposal(
        operation="update", skill_name="pick-and-place", workflow_key="place-object",
        description="Check placement", steps=["Check the settled placement"],
        verification_checkpoints=["Verify task outcome"],
        applicability_boundaries=["Object placement workflows"],
    )
    episode = SimpleNamespace(
        episode_id="success",
        outcome=SimpleNamespace(capability_outcome_summary=SimpleNamespace(failure_owner_counts={})),
    )
    merged = coordinator.evolution._support_candidate(episode, generic, [])
    assert merged.candidate_id != "candidate-1"
    extension = coordinator.store.get_candidate("candidate-1")
    assert extension.proposal.evolution_metadata["method_id"] == "evophy"
    assert extension.supporting_episode_ids == ["episode-1"]
    with pytest.raises(SkillEvolutionError, match="evaluation"):
        coordinator.evolution._promote_if_ready(extension)
    coordinator.stop()


def test_two_reviewed_local_revisions_preserve_learning_and_exclusions(tmp_path, monkeypatch):
    path = _write_skill(tmp_path)
    coordinator = ExperienceCoordinator(
        workspace=tmp_path, analyzer=_NoopAnalyzer(), min_successful_episodes=1,
    )
    adapter = EvolutionCandidateLifecycleAdapter(coordinator.store)
    for identity, transition in (("candidate-a", "grasp"), ("candidate-b", "place")):
        proposal = _proposal(candidate_id=identity, episode_id=identity)
        proposal.transition_id = transition
        proposal.reason = f"Improve {transition} observation"
        proposal.does_not_apply_when = ("evidence is incomplete",)
        adapter.submit(proposal)
        _record_promote_evaluation(adapter, proposal, monkeypatch)
        result = coordinator.review_evolution_skill_candidate(identity, reviewer_id="reviewer")
        assert result.status == "promoted"
    content = path.read_text()
    assert "Improve grasp observation" in content
    assert "Improve place observation" in content
    assert "evidence is incomplete" in content
    assert "parent_skill_revision" in coordinator.store.get_candidate("candidate-a").proposal.evolution_metadata
    coordinator.activation.begin_turn("future", "place object")
    activation, loaded, _ = coordinator.activation.activate(
        session_key="future", name="pick-and-place", role="primary"
    )
    assert set(activation.evolution_candidate_ids) == {"candidate-a", "candidate-b"}
    assert "Improve grasp observation" in loaded
    assert activation.binding_candidate_id is None
    from test_evolution_extension_hook import _FakeOutcomeSource

    coordinator.outcome_source = _FakeOutcomeSource()
    coordinator._schedule_job = lambda _: None
    coordinator.store.save_binding("task-fake", {
        "skill_activations": [activation.model_dump(mode="json")],
    })
    coordinator.schedule_forge_completion("task-fake")
    for identity in ("candidate-a", "candidate-b"):
        events = coordinator.store.list_event_payloads("evolution_candidate_task_outcome", identity)
        assert events[0]["activation_id"] == activation.activation_id
        assert events[0]["verdict"] == "failure"
    coordinator.stop()


def test_restarted_coordinator_redelivers_unacknowledged_episode(tmp_path):
    import asyncio

    from test_evolution_extension_hook import _coordinator, _FailingHook, _RecordingHook

    initial = _coordinator(tmp_path, _FailingHook())
    initial.schedule_forge_completion("task-fake")
    initial.stop()
    hook = _RecordingHook()
    restarted = _coordinator(tmp_path, hook)
    asyncio.run(restarted.start())
    assert "task-fake" in restarted._extension_delivery_pending
    asyncio.run(restarted._process_job("task-fake"))
    assert len(hook.episodes) == 1
    assert restarted.store.list_event_payloads("evolution_extension_delivered", "task-fake") == [{}]
    restarted.stop()


def test_trace_requires_dependency_and_owner_evidence(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "extensions/evolution"))
    from evolution.api import OwnerHypothesis, PulseRecord
    from evolution.trace import TraceAttributor

    records = tuple(
        PulseRecord(transition_id=name, order=i, predicate="stable", observed="violated",
                    evidence_coverage=1, owner="workflow", evidence_refs=("shared-frame",))
        for i, name in enumerate(("a", "b"))
    )
    independent = TraceAttributor().attribute("episode", records)
    assert independent.ranked[0].downstream_violations == ()
    assert independent.joint_cause_sets == ()
    owner = OwnerHypothesis(owner="workflow", confidence=0.9, evidence_refs=("cause-observation",))
    linked = tuple(row.model_copy(update={"owner_hypotheses": (owner,), "depends_on": () if i == 0 else ("a",)})
                   for i, row in enumerate(records))
    result = TraceAttributor().attribute("episode", linked)
    assert result.ranked[0].downstream_violations == ("b",)
    assert result.joint_cause_sets == (("a", "b"),)
    uncertain = records[0].model_copy(update={"owner_hypotheses": (owner.model_copy(update={"confidence": 0.1}),)})
    assert TraceAttributor().attribute("episode", (uncertain,)).ranked[0].owner == "unknown"
