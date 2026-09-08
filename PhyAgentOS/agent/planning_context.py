"""Trusted planning-context projection for AgentTask execution.

The TUI must not invent a scene revision merely to make a background runner
look executable.  This adapter projects only facts already persisted by the
existing ``AgentTaskCoordinator``: scene revisions and evidence emitted by
completed Tool records, plus durable node settlements.
"""

from __future__ import annotations

from typing import Any

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
    for record in records:
        evidence.update(item for item in getattr(record, "evidence_refs", ()) if isinstance(item, str))
        response = getattr(record, "response", None)
        if not isinstance(response, dict):
            continue
        payload = response.get("data") if isinstance(response.get("data"), dict) else response
        scene = payload.get("new_scene_revision")
        if isinstance(scene, str) and scene.strip():
            revisions.append(scene.strip())
        elif isinstance(payload.get("scene_revision"), str) and payload["scene_revision"].strip():
            revisions.append(payload["scene_revision"].strip())
        for ref in payload.get("evidence_refs", ()) if isinstance(payload.get("evidence_refs"), (list, tuple, set)) else ():
            if isinstance(ref, str) and ref:
                evidence.add(ref)
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
        settlements=settlements,
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
