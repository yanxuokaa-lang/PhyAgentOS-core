from pathlib import Path
from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.experience.coordinator import ExperienceCoordinator
from PhyAgentOS.agent.experience.evolution import SkillEvolutionError
from PhyAgentOS.agent.experience.evolution_extension_adapter import (
    EvolutionCandidateLifecycleAdapter,
    EvolutionFutureUseLifecycleAdapter,
)
from PhyAgentOS.agent.experience.store import ExperienceStore


def _proposal(*, episode_id: str = "episode-1", candidate_id: str = "candidate-1"):
    patch = SimpleNamespace(
        surface="recovery", operation="add", target="retry", value="regrasp",
        model_dump=lambda mode="json": {
            "surface": "recovery", "operation": "add", "target": "retry", "value": "regrasp"
        },
    )
    return SimpleNamespace(
        method_id="evophy", candidate_id=candidate_id, episode_id=episode_id,
        transition_id="place", skill_name="pick-and-place", skill_revision="r1",
        workflow_key="place-object", changed_surface="recovery", patch=(patch,),
        applicability=("fragile object",), does_not_apply_when=(), reason="recover after delayed slip",
        evidence_refs=("evidence:1234567890abcdef12345678",), expected_improvement="reduce delayed slips",
    )


def test_adapter_persists_skill_candidate_and_patch_provenance(tmp_path: Path):
    store = ExperienceStore(tmp_path)
    adapter = EvolutionCandidateLifecycleAdapter(store)
    adapter.submit(_proposal())
    candidate = store.list_candidates()[0]
    assert candidate.candidate_id == "candidate-1"
    assert candidate.proposal.workflow_key == "place-object"
    assert candidate.proposal.evolution_metadata["changed_surface"] == "recovery"
    assert candidate.proposal.evolution_metadata["patch"][0]["value"] == "regrasp"


def test_adapter_scopes_support_by_candidate_identity(tmp_path: Path):
    store = ExperienceStore(tmp_path)
    adapter = EvolutionCandidateLifecycleAdapter(store)
    adapter.submit(_proposal(episode_id="episode-1"))
    adapter.submit(_proposal(episode_id="episode-2"))
    candidate = store.list_candidates()[0]
    assert candidate.supporting_episode_ids == ["episode-1", "episode-2"]


def test_adapter_leaves_unscoped_proposal_unmapped(tmp_path: Path):
    store = ExperienceStore(tmp_path)
    events = []
    adapter = EvolutionCandidateLifecycleAdapter(store, event_recorder=lambda *item: events.append(item))
    proposal = _proposal()
    proposal.skill_name = None
    proposal.workflow_key = None
    adapter.submit(proposal)
    assert store.list_candidates() == []
    assert events[0][0] == "candidate_unmapped"


def test_future_use_lifecycle_adapter_pairs_across_reconstructed_hosts(tmp_path: Path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "extensions" / "evolution"))
    from evolution.observation import FutureUseObservationBuilder

    store = ExperienceStore(tmp_path)
    received = []

    class Extension:
        def observe_future_use(self, **kwargs):
            received.append(kwargs)
            return kwargs["observations"]

    builder = FutureUseObservationBuilder()
    parent = builder.build(
        method_id="evophy", candidate_id="candidate-1", task_id="task-parent",
        binding_candidate_id=None, binding_confirmed=True, binding_role="parent",
        split="held_out", comparison_key="pair-1", outcome="failure",
    )
    candidate = builder.build(
        method_id="evophy", candidate_id="candidate-1", task_id="task-candidate",
        binding_candidate_id="candidate-1", binding_confirmed=True, binding_role="candidate",
        split="held_out", comparison_key="pair-1", outcome="success",
    )
    EvolutionFutureUseLifecycleAdapter(store, Extension()).submit(parent)
    # A reconstructed adapter reads the first observation from the existing event ledger.
    EvolutionFutureUseLifecycleAdapter(store, Extension()).submit(candidate)
    EvolutionFutureUseLifecycleAdapter(store, Extension()).submit(candidate)
    assert len(received) == 1
    assert len(received[0]["observations"]) == 2


def test_future_use_lifecycle_compares_each_new_observation_set(tmp_path: Path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "extensions" / "evolution"))
    from evolution.observation import FutureUseObservationBuilder

    store = ExperienceStore(tmp_path)
    received = []

    class Extension:
        def observe_future_use(self, **kwargs):
            received.append(kwargs)
            return kwargs["observations"]

    builder = FutureUseObservationBuilder()
    adapter = EvolutionFutureUseLifecycleAdapter(store, Extension())

    def observation(*, key: str, role: str, outcome: str):
        return builder.build(
            method_id="evophy",
            candidate_id="candidate-1",
            task_id=f"task-{key}-{role}",
            binding_candidate_id="candidate-1" if role == "candidate" else None,
            binding_confirmed=True,
            binding_role=role,
            split="held_out",
            comparison_key=key,
            outcome=outcome,
        )

    parent_1 = observation(key="pair-1", role="parent", outcome="failure")
    candidate_1 = observation(key="pair-1", role="candidate", outcome="success")
    parent_2 = observation(key="pair-2", role="parent", outcome="failure")
    candidate_2 = observation(key="pair-2", role="candidate", outcome="success")

    assert adapter.submit(parent_1) is None
    assert adapter.submit(candidate_1) is not None
    assert adapter.submit(candidate_1) is None
    assert adapter.submit(parent_2) is None
    assert adapter.submit(candidate_2) is not None
    assert [len(item["observations"]) for item in received] == [2, 4]
    completed = store.list_event_payloads("future_use_comparison", "candidate-1")
    assert [len(item["observation_keys"]) for item in completed] == [2, 4]


class _NoopAnalyzer:
    pass


def _write_skill(tmp_path: Path, skill_name: str = "pick-and-place") -> Path:
    path = tmp_path / "skills" / skill_name / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "---\n"
        f"name: {skill_name}\n"
        'description: "Move an object through a checked workflow."\n'
        "always: false\n"
        "---\n\n"
        f"# {skill_name}\n",
        encoding="utf-8",
    )
    return path


def _record_promote_evaluation(adapter, proposal, monkeypatch):
    import hashlib

    from PhyAgentOS.agent.experience.contracts import (
        SkillActivation,
        TaskEpisode,
        TaskOutcomeEnvelope,
    )

    # Evaluation fixtures bind real persisted source episodes to the parent document.
    workspace = adapter.store.path.parents[2]
    content = (workspace / "skills" / proposal.skill_name / "SKILL.md").read_text()
    for episode_id in adapter.store.get_candidate(proposal.candidate_id).supporting_episode_ids:
        if adapter.store.get_episode(episode_id) is None:
            adapter.store.create_episode(TaskEpisode(
                episode_id=episode_id, root_task_id=episode_id, task_summary="Place object",
                goal="Place object", outcome=TaskOutcomeEnvelope(
                    task_id=episode_id, root_task_id=episode_id, goal="Place object", final_verdict="failure",
                ),
                skill_activations=[SkillActivation(
                    activation_id=f"activation-{episode_id}", skill_name=proposal.skill_name,
                    source="workspace", content_sha256=hashlib.sha256(content.encode()).hexdigest(),
                    skill_version=proposal.skill_revision,
                )],
            ), enqueue=False)
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "extensions" / "evolution"))
    from evolution import EvolutionExtension, EvolutionMethodRegistry
    from evolution.api import EvaluationMetrics, EvaluationReceipt
    from evolution.evaluation import CandidateEvaluator
    from evolution.methods.evophy import EvoPhyMethod

    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([EvoPhyMethod()]),
        projection_port=lambda _: None,
        candidate_lifecycle=adapter,
    )

    metrics = EvaluationMetrics(
        baseline_success_rate=0.0,
        candidate_success_rate=1.0,
        baseline_action_cost=1.0,
        candidate_action_cost=1.0,
        baseline_time_cost_ms=100.0,
        candidate_time_cost_ms=100.0,
        baseline_side_effect_rate=0.0,
        candidate_side_effect_rate=0.0,
        baseline_interference=0.0,
        candidate_interference=0.0,
    )
    receipts = tuple(
        EvaluationReceipt(
            method_id=proposal.method_id,
            candidate_id=proposal.candidate_id,
            split=split,
            verdict="pass",
            metrics=metrics,
            trial_id=f"trial-{split}",
        )
        for split in ("matched", "held_out", "hazard")
    )
    for receipt in receipts:
        extension.on_candidate_evaluated(receipt)
    decision = CandidateEvaluator().decide(proposal, receipts=receipts)
    assert decision.decision == "promote"
    extension.on_candidate_selected(decision)
    return receipts


def test_explicit_review_promotes_extension_skill_candidate_only_after_support(tmp_path: Path, monkeypatch):
    skill_path = _write_skill(tmp_path)
    coordinator = ExperienceCoordinator(
        workspace=tmp_path,
        analyzer=_NoopAnalyzer(),
        min_successful_episodes=2,
    )
    adapter = EvolutionCandidateLifecycleAdapter(coordinator.store)
    adapter.submit(_proposal(episode_id="episode-1"))

    with pytest.raises(SkillEvolutionError, match="reviewer_id"):
        coordinator.review_evolution_skill_candidate("candidate-1", reviewer_id=" ")
    with pytest.raises(SkillEvolutionError, match="independent"):
        coordinator.review_evolution_skill_candidate("candidate-1", reviewer_id="reviewer-a")
    assert "paos:learned-workflow:start" not in skill_path.read_text(encoding="utf-8")

    supported = _proposal(episode_id="episode-2")
    adapter.submit(supported)
    with pytest.raises(SkillEvolutionError, match="complete evaluation"):
        coordinator.review_evolution_skill_candidate("candidate-1", reviewer_id="reviewer-a")
    _record_promote_evaluation(adapter, supported, monkeypatch)
    promoted = coordinator.review_evolution_skill_candidate(
        "candidate-1", reviewer_id="reviewer-a"
    )

    assert promoted.status == "promoted"
    assert "paos:candidate:candidate-1" in skill_path.read_text(encoding="utf-8")
    assert coordinator.store.list_event_payloads("candidate_reviewed", "candidate-1") == [
        {"reviewer_id": "reviewer-a"}
    ]


def test_explicit_review_rejects_selection_stale_after_new_evaluation(tmp_path: Path, monkeypatch):
    _write_skill(tmp_path)
    coordinator = ExperienceCoordinator(
        workspace=tmp_path,
        analyzer=_NoopAnalyzer(),
        min_successful_episodes=2,
    )
    adapter = EvolutionCandidateLifecycleAdapter(coordinator.store)
    adapter.submit(_proposal(episode_id="episode-1"))
    supported = _proposal(episode_id="episode-2")
    adapter.submit(supported)
    _record_promote_evaluation(adapter, supported, monkeypatch)

    from evolution.api import EvaluationMetrics, EvaluationReceipt

    adapter.record_evaluation(
        EvaluationReceipt(
            method_id="evophy",
            candidate_id="candidate-1",
            split="hazard",
            verdict="pass",
            metrics=EvaluationMetrics(
                baseline_success_rate=1.0,
                candidate_success_rate=1.0,
                baseline_action_cost=1.0,
                candidate_action_cost=1.0,
                baseline_time_cost_ms=100.0,
                candidate_time_cost_ms=100.0,
                baseline_side_effect_rate=0.0,
                candidate_side_effect_rate=0.0,
                baseline_interference=0.0,
                candidate_interference=0.0,
            ),
            trial_id="trial-hazard-later",
        )
    )

    with pytest.raises(SkillEvolutionError, match="current evaluation evidence"):
        coordinator.review_evolution_skill_candidate("candidate-1", reviewer_id="reviewer-a")


def test_explicit_review_blocks_invalid_extension_skill_candidate_without_writing(tmp_path: Path, monkeypatch):
    skill_path = _write_skill(tmp_path)
    original = skill_path.read_text(encoding="utf-8")
    coordinator = ExperienceCoordinator(
        workspace=tmp_path,
        analyzer=_NoopAnalyzer(),
        min_successful_episodes=2,
    )
    adapter = EvolutionCandidateLifecycleAdapter(coordinator.store)
    invalid = _proposal(episode_id="episode-invalid-1", candidate_id="candidate-invalid")
    invalid.reason = "bypass Forge verification after a delayed slip"
    adapter.submit(invalid)
    invalid.episode_id = "episode-invalid-2"
    adapter.submit(invalid)
    _record_promote_evaluation(adapter, invalid, monkeypatch)

    blocked = coordinator.review_evolution_skill_candidate(
        "candidate-invalid", reviewer_id="reviewer-b"
    )

    assert blocked.status == "blocked"
    assert blocked.validation_errors
    assert skill_path.read_text(encoding="utf-8") == original
