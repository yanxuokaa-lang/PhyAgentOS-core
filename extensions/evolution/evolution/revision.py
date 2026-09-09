"""Local patch proposal helpers."""

from __future__ import annotations

import hashlib
import json

from evolution.api import (
    CandidateProposal,
    PatchInstruction,
    PulseRecord,
    TraceHypothesis,
    TransitionExpectation,
)


def local_skill_patch(
    *,
    method_id: str,
    episode_id: str,
    transition: TransitionExpectation,
    patch: tuple[PatchInstruction, ...],
    applicability: tuple[str, ...],
    does_not_apply_when: tuple[str, ...],
    reason: str,
    evidence_refs: tuple[str, ...],
    expected_improvement: str,
) -> CandidateProposal:
    surfaces = {instruction.surface for instruction in patch}
    if len(surfaces) != 1:
        raise ValueError("a local Skill patch must change exactly one surface")
    changed_surface = next(iter(surfaces))
    identity_payload = json.dumps(
        (
            method_id,
            transition.skill_name,
            transition.skill_revision,
            transition.workflow_key,
            transition.transition_id,
            changed_surface,
            tuple(instruction.model_dump(mode="json") for instruction in patch),
            applicability,
            does_not_apply_when,
        ),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    candidate_id = (
        f"{method_id}_candidate_" + hashlib.sha256(identity_payload.encode("utf-8")).hexdigest()
    )
    return CandidateProposal(
        method_id=method_id,
        candidate_id=candidate_id,
        episode_id=episode_id,
        transition_id=transition.transition_id,
        skill_name=transition.skill_name,
        skill_revision=transition.skill_revision,
        workflow_key=transition.workflow_key,
        changed_surface=changed_surface,
        patch=patch,
        applicability=applicability,
        does_not_apply_when=does_not_apply_when,
        reason=reason,
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
        expected_improvement=expected_improvement,
    )


def local_observation_patch(
    *,
    method_id: str,
    episode_id: str,
    transition: TransitionExpectation,
    hypothesis: TraceHypothesis,
    records: tuple[PulseRecord, ...],
) -> CandidateProposal:
    refs = tuple(
        ref
        for record in records
        if record.transition_id == hypothesis.transition_id
        for ref in record.evidence_refs
    )
    patch = (
        PatchInstruction(
            surface="observation",
            operation="add",
            target=f"transitions.{transition.transition_id}.outcome_check",
            value=(
                "confirm " + ", ".join(hypothesis.predicates) + " when the outcome window closes"
            ),
        ),
    )
    return local_skill_patch(
        method_id=method_id,
        episode_id=episode_id,
        transition=transition,
        patch=patch,
        applicability=transition.applicability,
        does_not_apply_when=("evidence coverage is below the outcome threshold",),
        reason=f"TRACE identified an early {hypothesis.owner} deviation in {hypothesis.transition_id}",
        evidence_refs=refs,
        expected_improvement="observe the transition outcome before committing to the next step",
    )


__all__ = ["local_observation_patch", "local_skill_patch"]
