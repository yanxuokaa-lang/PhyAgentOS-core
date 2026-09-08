from __future__ import annotations

from types import SimpleNamespace

import pytest

from PhyAgentOS.agent.planning_context import (
    AgentTaskPlanningContextProvider,
    PlanningContextUnavailableError,
    context_from_task,
)
from PhyAgentOS.planning import AdmissionContext


def test_context_projection_uses_persisted_scene_and_evidence():
    task = SimpleNamespace(
        execution_records=[
            SimpleNamespace(
                evidence_refs=["tool:observe", "observation://scene-7/frame-1"],
                response={
                    "data": {
                        "scene_revision": "scene-7",
                        "evidence_refs": ["scene://scene-7"],
                        "condition_facts": {"workspace_clear": True},
                        "resources_in_use": ["arm:right"],
                    }
                },
            )
        ],
        active_revision=SimpleNamespace(
            node_settlements=[SimpleNamespace(node_id="observe", status="completed")]
        ),
    )

    context = context_from_task(task)
    assert isinstance(context, AdmissionContext)
    assert context.scene_revision == "scene-7"
    assert set(context.evidence_refs) == {
        "tool:observe",
        "observation://scene-7/frame-1",
        "scene://scene-7",
    }
    assert dict(context.settlements) == {"observe": "completed"}
    assert dict(context.condition_facts) == {"workspace_clear": True}
    assert set(context.resources_in_use) == {"arm:right"}


def test_context_projection_blocks_before_observation():
    task = SimpleNamespace(execution_records=[], active_revision=SimpleNamespace(node_settlements=[]))
    with pytest.raises(PlanningContextUnavailableError, match="no persisted scene revision"):
        context_from_task(task)


def test_context_provider_loads_current_task():
    task = SimpleNamespace(
        execution_records=[
            SimpleNamespace(evidence_refs=[], response={"scene_revision": "scene-1"})
        ],
        active_revision=SimpleNamespace(node_settlements=[]),
    )
    provider = AgentTaskPlanningContextProvider(SimpleNamespace(get_task=lambda _: task))
    assert provider("task-1").scene_revision == "scene-1"
