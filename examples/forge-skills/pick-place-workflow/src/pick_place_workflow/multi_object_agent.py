"""Multi-object AgentTask entry point for the pick/place workflow.

The runner turns trusted scene-understanding output into one persisted
AgentTask.  Execution is delegated to the existing AgentLoop long-horizon
controller; this module never calls a provider or treats Action admission as
completion.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable
from typing import Any, Literal

from PhyAgentOS.agent.long_horizon import LongHorizonTaskController, LongHorizonTaskResult
from PhyAgentOS.forge.task import AgentTaskCoordinator, AgentTaskRecord
from PhyAgentOS.verification.contracts import TaskVerificationContract
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .agent_planning import (
    AgentSubtaskSpec,
    compose_agent_plan,
    compose_executable_pick_place_plan,
)


class MultiObjectAgentError(ValueError):
    """The trusted scene projection cannot form a multi-object task."""


class SceneObjectBinding(BaseModel):
    """One uniquely identified benchmark object and its destination."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_ref: str = Field(min_length=1)
    benchmark_object_ref: str = Field(min_length=1)
    destination_ref: str = Field(min_length=1)
    observation_ref: str = Field(min_length=1)
    scene_revision: str = Field(min_length=1)
    frame_id: str = Field(min_length=1)
    calibration_ref: str = Field(min_length=1)
    geometry_artifact_ref: str = Field(min_length=1)
    category: str = Field(default="block", min_length=1)
    required_evidence: tuple[str, ...] = ()

    @field_validator("entity_ref")
    @classmethod
    def entity_reference(cls, value: str) -> str:
        if not value.startswith("entity://"):
            raise ValueError("entity_ref must be an entity:// reference")
        return value

    @field_validator("destination_ref")
    @classmethod
    def destination_reference(cls, value: str) -> str:
        if "://" not in value or value.startswith("://"):
            raise ValueError("destination_ref must be an opaque URI reference")
        return value


def bind_scene_objects(
    entities: Iterable[SceneObjectBinding | dict[str, Any]],
    *,
        category: str = "block",
) -> tuple[SceneObjectBinding, ...]:
    """Select only uniquely bound objects from a trusted understanding result.

    Desktop surfaces and unbound model entities are rejected instead of being
    silently converted into executable obligations.
    """

    selected = tuple(
        item if isinstance(item, SceneObjectBinding) else SceneObjectBinding.model_validate(item)
        for item in entities
    )
    selected = tuple(item for item in selected if item.category == category)
    if not selected:
        raise MultiObjectAgentError(f"scene contains no executable {category!r} objects")
    entity_refs = [item.entity_ref for item in selected]
    benchmark_refs = [item.benchmark_object_ref for item in selected]
    destinations = [item.destination_ref for item in selected]
    for label, values in (
        ("entity_ref", entity_refs),
        ("benchmark_object_ref", benchmark_refs),
        ("destination_ref", destinations),
    ):
        if len(values) != len(set(values)):
            raise MultiObjectAgentError(f"{label} must be unique in a multi-object task")
    if len({item.scene_revision for item in selected}) != 1:
        raise MultiObjectAgentError("all objects must come from one scene revision")
    return selected


class MultiObjectAgentRunner:
    """Create and execute one multi-object AgentTask through PAOS authorities."""

    def __init__(
        self,
        *,
        coordinator: AgentTaskCoordinator,
        agent_loop: Any,
        scene_revision_provider: Callable[[str], str],
        planning_mode: Literal["baseline", "agent_composed"] = "baseline",
        planner_decision_digest: str = "0" * 64,
        policy_snapshot_digest: str = "1" * 64,
    ) -> None:
        if planning_mode not in {"baseline", "agent_composed"}:
            raise MultiObjectAgentError(f"unsupported planning mode: {planning_mode!r}")
        self.coordinator = coordinator
        self.agent_loop = agent_loop
        self.scene_revision_provider = scene_revision_provider
        self.planning_mode = planning_mode
        self.planner_decision_digest = planner_decision_digest
        self.policy_snapshot_digest = policy_snapshot_digest

    async def create_task(
        self,
        *,
        task_description: str,
        entities: Iterable[SceneObjectBinding | dict[str, Any]],
        verification: TaskVerificationContract,
        task_id: str,
        revision_id: str,
    ) -> AgentTaskRecord:
        bound = bind_scene_objects(entities)
        scene_revisions = {item.scene_revision for item in bound}
        if len(scene_revisions) != 1:
            raise MultiObjectAgentError("all objects must come from one scene revision")
        subtasks = tuple(
            AgentSubtaskSpec(
                subtask_id=f"relocate_{index + 1}",
                entity_ref=item.entity_ref,
                destination_ref=item.destination_ref,
                required_evidence=item.required_evidence,
                context_bindings=(
                    ("benchmark_object_ref", item.benchmark_object_ref),
                    ("observation_ref", item.observation_ref),
                    ("scene_revision", item.scene_revision),
                    ("frame_id", item.frame_id),
                    ("calibration_ref", item.calibration_ref),
                    ("geometry_artifact_ref", item.geometry_artifact_ref),
                ),
            )
            for index, item in enumerate(bound)
        )
        plan = (
            compose_executable_pick_place_plan(
                task_id,
                revision_id,
                subtasks,
                planner_decision_digest=self.planner_decision_digest,
                policy_snapshot_digest=self.policy_snapshot_digest,
            )
            if self.planning_mode == "baseline"
            else compose_agent_plan(
                task_id,
                revision_id,
                subtasks,
                planner_decision_digest=self.planner_decision_digest,
                policy_snapshot_digest=self.policy_snapshot_digest,
            )
        )
        task = self.coordinator.create_task(
            task_description=task_description,
            verification=verification,
            plan_graph=plan.graph,
            plan_graph_ref=f"artifact://plans/{task_id}/{revision_id}",
        )
        if inspect.isawaitable(task):
            task = await task
        return task

    async def run(
        self,
        *,
        task_description: str,
        entities: Iterable[SceneObjectBinding | dict[str, Any]],
        verification: TaskVerificationContract,
        task_id: str,
        revision_id: str,
    ) -> LongHorizonTaskResult:
        task = await self.create_task(
            task_description=task_description,
            entities=entities,
            verification=verification,
            task_id=task_id,
            revision_id=revision_id,
        )
        bound_scene_revision = task.active_revision.plan_graph.nodes[0].input_bindings.get("scene_revision")
        current_scene_revision = self.scene_revision_provider(task.task_id)
        if current_scene_revision != bound_scene_revision:
            raise MultiObjectAgentError(
                "bound scene revision is stale before AgentLoop execution"
            )
        controller = self.agent_loop.build_long_horizon_controller()
        if not isinstance(controller, LongHorizonTaskController):
            raise MultiObjectAgentError("AgentLoop did not provide an executable long-horizon controller")
        return await controller.run(task.task_id)


__all__ = [
    "MultiObjectAgentError",
    "MultiObjectAgentRunner",
    "SceneObjectBinding",
    "bind_scene_objects",
]
