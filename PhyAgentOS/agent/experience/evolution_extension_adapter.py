"""PAOS-owned adapter for optional evolution-extension candidate proposals.

The adapter translates an extension's method-agnostic proposal into the
existing ExperienceStore candidate records.  It deliberately stops at the
review boundary: no Skill file, planner policy, verifier, or runtime state is
changed here.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from PhyAgentOS.agent.experience.contracts import SkillCandidate, SkillWorkflowProposal
from PhyAgentOS.agent.experience.policy_candidates import WorkflowPolicyCandidateManager
from PhyAgentOS.agent.experience.store import ExperienceStore


class EvolutionCandidateLifecycleAdapter:
    """Implement the extension ``CandidateLifecyclePort`` on the PAOS side."""

    def __init__(
        self,
        store: ExperienceStore,
        *,
        policy_candidates: WorkflowPolicyCandidateManager | None = None,
        policy_digest_resolver: Callable[[Any], tuple[str, str] | None] | None = None,
        event_recorder: Callable[[str, str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.store = store
        self.policy_candidates = policy_candidates
        self.policy_digest_resolver = policy_digest_resolver
        self.event_recorder = event_recorder

    def submit(self, proposal: Any) -> None:
        """Persist a proposal in the existing PAOS candidate lifecycle."""
        if self._submit_policy_if_available(proposal):
            return
        skill_name = getattr(proposal, "skill_name", None)
        workflow_key = getattr(proposal, "workflow_key", None)
        if not skill_name or not workflow_key:
            self._event(
                "candidate_unmapped",
                str(getattr(proposal, "candidate_id", "unknown")),
                {"reason": "skill_scope_missing", "surface": getattr(proposal, "changed_surface", None)},
            )
            return
        skill_proposal = self._to_skill_proposal(proposal, skill_name, workflow_key)
        candidate = SkillCandidate(
            candidate_id=str(proposal.candidate_id),
            proposal=skill_proposal,
            supporting_episode_ids=[str(proposal.episode_id)],
            status="collecting",
        )
        self.store.upsert_candidate(candidate)
        self._event(
            "candidate_lifecycle_submitted",
            candidate.candidate_id,
            {"kind": "skill", "surface": proposal.changed_surface},
        )

    def record_evaluation(self, receipt: Any) -> None:
        """Persist one extension-owned evaluation receipt for a mapped Skill candidate."""
        candidate = self.store.get_candidate(str(getattr(receipt, "candidate_id", "")))
        payload = receipt.model_dump(mode="json")
        if candidate is None or not self._matches_candidate_method(candidate, payload):
            self._event(
                "candidate_evaluation_unmapped",
                str(getattr(receipt, "candidate_id", "unknown")),
                {"method_id": payload.get("method_id")},
            )
            return
        self.store.record_event_once(
            "candidate_evaluation_receipt", candidate.candidate_id, payload
        )

    def record_selection(self, decision: Any) -> None:
        """Persist a method-owned selection decision bound to its receipt set."""
        candidate = self.store.get_candidate(str(getattr(decision, "candidate_id", "")))
        payload = decision.model_dump(mode="json")
        if candidate is None or not self._matches_candidate_method(candidate, payload):
            self._event(
                "candidate_selection_unmapped",
                str(getattr(decision, "candidate_id", "unknown")),
                {"method_id": payload.get("method_id")},
            )
            return
        payload["receipt_payloads"] = self._receipt_payloads(
            candidate.candidate_id, str(payload["method_id"])
        )
        self.store.record_event_once(
            "candidate_evaluation_decision", candidate.candidate_id, payload
        )

    def _submit_policy_if_available(self, proposal: Any) -> bool:
        if (
            self.policy_candidates is None
            or self.policy_digest_resolver is None
            or getattr(proposal, "changed_surface", None) != "decision"
        ):
            return False
        digests = self.policy_digest_resolver(proposal)
        if digests is None:
            return False
        from PhyAgentOS.planning import WorkflowPolicyCandidate

        base_digest, proposed_digest = digests
        candidate = WorkflowPolicyCandidate(
            candidate_id=str(proposal.candidate_id),
            base_policy_digest=base_digest,
            proposed_policy_digest=proposed_digest,
            source_episode_ids=(str(proposal.episode_id),),
            change_summary=str(proposal.reason),
        )
        self.policy_candidates.submit(candidate)
        self._event(
            "candidate_lifecycle_submitted",
            candidate.candidate_id,
            {"kind": "workflow_policy", "surface": proposal.changed_surface},
        )
        return True

    @staticmethod
    def _matches_candidate_method(
        candidate: SkillCandidate, payload: dict[str, Any]
    ) -> bool:
        return candidate.proposal.evolution_metadata.get("method_id") == payload.get(
            "method_id"
        )

    def _receipt_payloads(self, candidate_id: str, method_id: str) -> list[str]:
        return sorted(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for payload in self.store.list_event_payloads(
                "candidate_evaluation_receipt", candidate_id
            )
            if payload.get("method_id") == method_id
        )

    @staticmethod
    def _to_skill_proposal(proposal: Any, skill_name: str, workflow_key: str) -> SkillWorkflowProposal:
        patch_items = tuple(getattr(proposal, "patch", ()) or ())
        values = [
            f"{item.operation} {item.target}" + (f": {item.value}" if item.value else "")
            for item in patch_items
        ]
        surface = str(getattr(proposal, "changed_surface", "expectation"))
        steps = values or [str(getattr(proposal, "reason", "revise workflow"))]
        checkpoints = [
            "recheck transition outcome before continuing",
            *[item for item in values if surface == "expectation"],
        ]
        recovery = [item for item in values if surface == "recovery"]
        applicability = list(getattr(proposal, "applicability", ()) or ())
        if not applicability:
            applicability = [f"transition:{proposal.transition_id}"]
        metadata = {
            "method_id": proposal.method_id,
            "parent_skill_revision": getattr(proposal, "skill_revision", None),
            "transition_id": proposal.transition_id,
            "changed_surface": surface,
            "patch": [item.model_dump(mode="json") for item in patch_items],
            "evidence_refs": list(getattr(proposal, "evidence_refs", ()) or ()),
            "does_not_apply_when": list(getattr(proposal, "does_not_apply_when", ()) or ()),
        }
        return SkillWorkflowProposal(
            operation="update",
            skill_name=skill_name,
            workflow_key=workflow_key,
            description=str(getattr(proposal, "reason", "evolution candidate")),
            steps=steps,
            verification_checkpoints=checkpoints or ["verify revised transition"],
            recovery_guidance=recovery,
            applicability_boundaries=applicability,
            evolution_metadata=metadata,
        )

    def _event(self, event_type: str, ref: str, payload: dict[str, Any]) -> None:
        if self.event_recorder is not None:
            self.event_recorder(event_type, ref, payload)


class EvolutionFutureUseLifecycleAdapter:
    """Persist and replay Future-use observations through ExperienceStore events."""

    def __init__(self, store: ExperienceStore, extension: Any) -> None:
        self.store = store
        self.extension = extension

    def submit(self, observation: Any) -> Any:
        payload = observation.model_dump(mode="json")
        candidate_id = str(observation.candidate_id)
        event_type = "future_use_observation"
        inserted = self.store.record_event_once(event_type, candidate_id, payload)
        if not inserted:
            return None
        rows = self.store.list_event_payloads(event_type, candidate_id)
        observations = [
            observation.__class__.model_validate(item)
            for item in rows
            if item.get("method_id") == observation.method_id
        ]
        paired_observation_keys = self._paired_observation_keys(observations)
        if not paired_observation_keys:
            return None
        completion_payload = {
            "method_id": str(observation.method_id),
            "observation_keys": paired_observation_keys,
        }
        if completion_payload in self.store.list_event_payloads(
            "future_use_comparison", candidate_id
        ):
            return None
        comparison = self.extension.observe_future_use(
            method_id=str(observation.method_id),
            candidate_id=candidate_id,
            observations=observations,
        )
        if comparison is not None:
            self.store.record_event_once(
                "future_use_comparison",
                candidate_id,
                completion_payload,
            )
        return comparison

    @staticmethod
    def _paired_observation_keys(observations: list[Any]) -> list[str]:
        roles_by_key: dict[str, set[str]] = {}
        for item in observations:
            roles_by_key.setdefault(str(item.comparison_key), set()).add(item.binding_role)
        complete_keys = {
            key for key, roles in roles_by_key.items() if roles == {"parent", "candidate"}
        }
        return sorted(
            f"{item.comparison_key}:{item.binding_role}"
            for item in observations
            if item.comparison_key in complete_keys
        )


__all__ = [
    "EvolutionCandidateLifecycleAdapter",
    "EvolutionFutureUseLifecycleAdapter",
]
