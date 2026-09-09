"""EvoPhy method: PULSE records followed by TRACE attribution."""

from __future__ import annotations

from collections.abc import Sequence

from evolution.api import CandidateProposal, EpisodeProjection, EvaluationReceipt, PatchInstruction
from evolution.pulse import PulseLogger
from evolution.revision import local_skill_patch
from evolution.trace import TraceAttributor, TracePolicy


class EvoPhyMethod:
    method_id = "evophy"
    required_projections = frozenset({"transition_expectation", "outcome_observation"})

    def __init__(self, *, trace_policy: TracePolicy | None = None) -> None:
        self._pulse = PulseLogger()
        self._trace = TraceAttributor(policy=trace_policy)

    def process(self, episode: EpisodeProjection) -> Sequence[CandidateProposal]:
        records = self._pulse.build(episode)
        trace = self._trace.attribute(episode.episode_id, records)
        proposals: list[CandidateProposal] = []
        for hypothesis in trace.ranked:
            if hypothesis.state != "violated" or hypothesis.owner not in {
                "workflow",
                "planner",
                "perception",
            }:
                continue
            transition = next(
                item
                for item in episode.transitions
                if item.transition_id == hypothesis.transition_id
            )
            evidence_refs = tuple(
                ref
                for record in records
                if record.transition_id == hypothesis.transition_id
                for ref in record.evidence_refs
            )
            if not evidence_refs:
                continue
            surface = (
                "recovery"
                if hypothesis.downstream_violations
                else {
                    "perception": "observation",
                    "planner": "expectation",
                    "workflow": "decision",
                }[hypothesis.owner]
            )
            target = f"transitions.{transition.transition_id}.{surface}"
            value = {
                "observation": "confirm " + ", ".join(hypothesis.predicates) + " when the outcome window closes",
                "expectation": "require " + ", ".join(hypothesis.predicates) + " before advancing",
                "decision": "branch on " + ", ".join(hypothesis.predicates) + " before continuing",
                "recovery": "recover before continuing to " + ", ".join(hypothesis.downstream_violations),
            }[surface]
            patch = (
                PatchInstruction(surface=surface, operation="add", target=target, value=value),
            )
            proposals.append(
                local_skill_patch(
                    method_id=self.method_id,
                    episode_id=episode.episode_id,
                    transition=transition,
                    patch=patch,
                    applicability=transition.applicability,
                    does_not_apply_when=("evidence coverage is below the outcome threshold",),
                    reason=f"TRACE identified an early {hypothesis.owner} deviation in {hypothesis.transition_id}",
                    evidence_refs=evidence_refs,
                    expected_improvement="prevent recurrence of the attributed transition deviation",
                )
            )
        return tuple(proposals)

    def on_candidate_evaluated(self, receipt: EvaluationReceipt) -> None:
        """EvoPhy keeps evaluation state in the host-owned candidate lifecycle."""


__all__ = ["EvoPhyMethod"]
