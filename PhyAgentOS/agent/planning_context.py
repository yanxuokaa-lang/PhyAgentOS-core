"""Trusted planning-context projection for AgentTask execution.

The TUI must not invent a scene revision merely to make a background runner
look executable.  This adapter projects only facts already persisted by the
existing ``AgentTaskCoordinator``: scene revisions and evidence emitted by
completed Tool records, plus durable node settlements.
"""

from __future__ import annotations

from typing import Any

from PhyAgentOS.agent.planning_facts import response_facts
from PhyAgentOS.planning import AdmissionContext


class PlanningContextUnavailableError(RuntimeError):
    """No authoritative scene fact is available for admission yet."""


def context_from_task(task: Any) -> AdmissionContext:
    """Build an admission context from persisted task facts.

    Scene identity is read exclusively from Tool responses.  A task that has
    not yet completed an observation/understanding query therefore remains
    blocked instead of receiving a fabricated placeholder scene revision.
    """

    records = list(getattr(task, "execution_records", ()))
    revisions: list[str] = []
    evidence: set[str] = set()
    condition_facts: dict[str, bool] = {}
    resources_in_use: set[str] = set()
    needs_observation = False
    for record in records:
        if not getattr(record, "terminal", False):
            continue
        response = getattr(record, "response", None)
        if not isinstance(response, dict):
            continue
        payload = response_facts(response)
        scene = payload.get("new_scene_revision")
        effect_started = payload.get("world_change_started") is True or payload.get("world_changed") is True
        if effect_started and not (isinstance(scene, str) and scene.strip()):
            needs_observation = True
            evidence.clear()
            condition_facts.clear()
        if not isinstance(scene, str) or not scene.strip():
            scene = payload.get("scene_revision") if getattr(record, "status", None) == "succeeded" and not effect_started and not isinstance(payload.get("capability_outcome_summary"), dict) else None
        if isinstance(scene, str) and scene.strip():
            needs_observation = False
            scene = scene.strip()
            if revisions and revisions[-1] != scene:
                evidence.clear()
                condition_facts.clear()
            revisions.append(scene)
        evidence.update(item for item in getattr(record, "evidence_refs", ()) if isinstance(item, str))
        for ref in payload.get("evidence_refs", ()) if isinstance(payload.get("evidence_refs"), (list, tuple, set)) else ():
            if isinstance(ref, str) and ref:
                evidence.add(ref)
        facts = payload.get("condition_facts")
        if isinstance(facts, dict):
            condition_facts.update({key: value for key, value in facts.items() if isinstance(key, str) and isinstance(value, bool)})
        resources = payload.get("resources_in_use")
        if isinstance(resources, (list, tuple, set)):
            resources_in_use = {item for item in resources if isinstance(item, str) and item}
    if needs_observation:
        raise PlanningContextUnavailableError("physical effects require a fresh observation before planning admission")
    if not revisions:
        raise PlanningContextUnavailableError(
            "no persisted scene revision is available; complete an observation or understanding Tool first"
        )
    scene_revision = revisions[-1]
    settlements = {
        settlement.node_id: settlement.status
        for settlement in getattr(getattr(task, "active_revision", None), "node_settlements", ())
    }
    return AdmissionContext(
        scene_revision=scene_revision,
        evidence_refs=frozenset(evidence),
        resources_in_use=frozenset(resources_in_use),
        settlements=settlements,
        condition_facts=condition_facts,
    )


class AgentTaskPlanningContextProvider:
    """Callable provider suitable for AgentLoop and planning dispatch seams."""

    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator

    def __call__(self, task_id: str) -> AdmissionContext:
        return context_from_task(self.coordinator.get_task(task_id))


__all__ = [
    "AgentTaskPlanningContextProvider",
    "PlanningContextUnavailableError",
    "context_from_task",
]
