from __future__ import annotations

from pathlib import Path

from PhyAgentOS.agent.experience.contracts import ExperienceAssessment, TaskOutcomeEnvelope
from PhyAgentOS.agent.experience.coordinator import ExperienceCoordinator


class _FakeOutcomeSource:
    def build(self, task_ref: str) -> TaskOutcomeEnvelope:
        return TaskOutcomeEnvelope(
            task_id="task-fake",
            root_task_id="task-fake",
            goal="place object",
            final_verdict="failure",
            success_criteria=["object is stable"],
            criteria_statuses={"object is stable": "unsatisfied"},
        )


class _FakeAnalyzer:
    async def assess(self, *args, **kwargs) -> ExperienceAssessment:
        return ExperienceAssessment(
            outcome="ignored",
            reusable=False,
            confidence=1.0,
            rationale="fake integration test",
        )


class _RecordingHook:
    def __init__(self) -> None:
        self.episodes: list[object] = []

    def on_episode_closed(self, episode: object) -> None:
        self.episodes.append(episode)


class _FailingHook:
    def on_episode_closed(self, episode: object) -> None:
        raise RuntimeError("fake extension failure")


def _coordinator(tmp_path, hook) -> ExperienceCoordinator:
    coordinator = ExperienceCoordinator(
        workspace=tmp_path,
        analyzer=_FakeAnalyzer(),
        evolution_extension=hook,
        max_calls=1,
    )
    coordinator.outcome_source = _FakeOutcomeSource()
    coordinator._schedule_job = lambda _: None
    return coordinator


def test_coordinator_forwards_closed_episode_to_method_agnostic_hook(tmp_path):
    hook = _RecordingHook()
    coordinator = _coordinator(tmp_path, hook)

    coordinator.schedule_forge_completion("task-fake")

    assert len(hook.episodes) == 1
    assert hook.episodes[0].root_task_id == "task-fake"
    coordinator.stop()


def test_extension_failure_preserves_persisted_episode(tmp_path):
    coordinator = _coordinator(tmp_path, _FailingHook())

    coordinator.schedule_forge_completion("task-fake")

    assert coordinator.store.get_episode_by_root("task-fake") is not None
    coordinator.stop()


def test_core_episode_drives_optional_evolution_package_fake_facts(monkeypatch, tmp_path):
    extension_root = Path(__file__).resolve().parents[1] / "extensions" / "evolution"
    monkeypatch.syspath_prepend(str(extension_root))

    from evolution.api import OutcomeObservation, TransitionExpectation
    from evolution.methods.evophy import EvoPhyMethod
    from evolution.plugin import EvolutionExtension
    from evolution.projection import ComposedEpisodeProjectionPort, EpisodeMetadata
    from evolution.registry import EvolutionMethodRegistry

    proposals = []
    events = []
    projection_port = ComposedEpisodeProjectionPort(
        metadata_projector=lambda episode: EpisodeMetadata(
            episode_id=episode.episode_id,
            root_task_id=episode.root_task_id,
            action_cost=1.0,
            time_cost_ms=1200,
        ),
        transition_port=lambda _episode: (
            TransitionExpectation(
                transition_id="place",
                order=0,
                expected_predicates=("object-stable",),
                skill_name="pick-place",
                skill_revision="1",
                workflow_key="pick-place",
                applicability=("object is held",),
            ),
        ),
        outcome_port=lambda _episode, _transitions: (
            OutcomeObservation(
                transition_id="place",
                predicate="object-stable",
                state="violated",
                evidence_coverage=0.9,
                observed_at_ms=1200,
                outcome_window_closed=True,
                owner="workflow",
                evidence_refs=("artifact://fake/place-outcome",),
            ),
        ),
    )
    extension = EvolutionExtension(
        registry=EvolutionMethodRegistry([EvoPhyMethod()]),
        projection_port=projection_port,
        candidate_sink=proposals.append,
        event_sink=lambda event, ref, payload: events.append((event, ref, payload)),
    )
    coordinator = _coordinator(tmp_path, extension)

    coordinator.schedule_forge_completion("task-fake")

    assert len(proposals) == 1
    assert proposals[0].transition_id == "place"
    assert any(event[0] == "candidate_proposed" for event in events)
    assert coordinator.store.get_episode_by_root("task-fake") is not None
    coordinator.stop()
