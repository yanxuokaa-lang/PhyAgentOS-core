"""Multi-object AgentTask entry point for the pick/place workflow.

The runner turns trusted scene-understanding output into one persisted
AgentTask.  Execution is delegated to the existing AgentLoop long-horizon
controller; this module never calls a provider or treats Action admission as
completion.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable, Mapping
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
    capability_snapshot_ref: str | None = Field(default=None, min_length=1)
    assignment_ref: str | None = Field(default=None, min_length=1)
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

    @field_validator("capability_snapshot_ref", "assignment_ref")
    @classmethod
    def artifact_reference(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("artifact://"):
            raise ValueError("capability and assignment references must use artifact://")
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


def bind_understood_scene_objects(
    understanding: Mapping[str, Any],
    measured_objects: Iterable[Mapping[str, Any]],
    *,
    entity_refs: Iterable[str] | None = None,
    category: str = "block",
) -> tuple[SceneObjectBinding, ...]:
    """Join semantic claims to one current, measured scene.

    The understanding provider supplies semantic identity and geometry evidence;
    the adapter supplies benchmark identity and destination geometry.  This
    pure join is intentionally below the provider boundary: it does not call a
    model, inspect a simulator, persist a task, or authorize an Action.
    """

    if not isinstance(understanding, Mapping) or understanding.get("status") != "available":
        raise MultiObjectAgentError("scene understanding is not available")
    if understanding.get("ambiguities"):
        raise MultiObjectAgentError("scene understanding contains unresolved ambiguities")
    observation_ref = understanding.get("observation_ref")
    scene_revision = understanding.get("scene_revision")
    frame = understanding.get("frame")
    calibration_ref = understanding.get("calibration_ref")
    frame_id = frame.get("frame_id") if isinstance(frame, Mapping) else None
    if not all(isinstance(value, str) and value for value in (
        observation_ref, scene_revision, frame_id, calibration_ref,
    )):
        raise MultiObjectAgentError("scene understanding has incomplete binding facts")

    claims = understanding.get("entities")
    if not isinstance(claims, (list, tuple)):
        raise MultiObjectAgentError("scene understanding entities are missing")
    claims_by_ref: dict[str, Mapping[str, Any]] = {}
    for claim in claims:
        if not isinstance(claim, Mapping):
            raise MultiObjectAgentError("scene understanding entity claim is invalid")
        ref = claim.get("entity_ref")
        if not isinstance(ref, str) or not ref.startswith("entity://") or ref in claims_by_ref:
            raise MultiObjectAgentError("scene understanding entity identities are invalid")
        claims_by_ref[ref] = claim

    requested = tuple(entity_refs) if entity_refs is not None else tuple(
        ref for ref, claim in claims_by_ref.items() if claim.get("category") == category
    )
    if not requested or len(requested) != len(set(requested)):
        raise MultiObjectAgentError("semantic entity selection is empty or not unique")
    if any(ref not in claims_by_ref for ref in requested):
        raise MultiObjectAgentError("semantic entity selection references an unknown entity")
    if any(claims_by_ref[ref].get("category") != category for ref in requested):
        raise MultiObjectAgentError(f"semantic entity selection is not executable {category!r} objects")

    measured_by_ref: dict[str, Mapping[str, Any]] = {}
    for measured in measured_objects:
        if not isinstance(measured, Mapping):
            raise MultiObjectAgentError("measured scene object is invalid")
        ref = measured.get("entity_ref")
        if not isinstance(ref, str) or ref in measured_by_ref:
            raise MultiObjectAgentError("measured scene entity identities are invalid")
        measured_by_ref[ref] = measured

    derived = understanding.get("derived_artifacts", ())
    if not isinstance(derived, (list, tuple)):
        raise MultiObjectAgentError("scene understanding geometry evidence is invalid")
    derived_by_ref: dict[str, Mapping[str, Any]] = {}
    for item in derived:
        if not isinstance(item, Mapping) or not isinstance(item.get("artifact_ref"), str):
            raise MultiObjectAgentError("scene understanding geometry evidence is invalid")
        artifact_ref = item["artifact_ref"]
        if artifact_ref in derived_by_ref:
            raise MultiObjectAgentError("scene understanding geometry artifact identities are invalid")
        derived_by_ref[artifact_ref] = item
    bindings: list[dict[str, Any]] = []
    for ref in requested:
        measured = measured_by_ref.get(ref)
        if measured is None:
            raise MultiObjectAgentError(f"measured scene is missing semantic entity {ref}")
        required = (
            "benchmark_object_ref", "destination_ref", "observation_ref", "scene_revision",
            "frame_id", "calibration_ref", "geometry_artifact_ref", "category",
        )
        if any(not isinstance(measured.get(key), str) or not measured[key] for key in required):
            raise MultiObjectAgentError(f"measured scene binding is incomplete for {ref}")
        for key, expected in (
            ("observation_ref", observation_ref), ("scene_revision", scene_revision),
            ("frame_id", frame_id), ("calibration_ref", calibration_ref),
        ):
            if measured[key] != expected:
                raise MultiObjectAgentError(f"measured scene binding drift for {ref}: {key}")
        if measured["category"] != category:
            raise MultiObjectAgentError(f"measured scene object {ref} is not an executable {category!r}")
        geometry = derived_by_ref.get(measured["geometry_artifact_ref"])
        if not isinstance(geometry, Mapping) or any(
            geometry.get(key) != expected
            for key, expected in (
                ("entity_ref", ref), ("observation_ref", observation_ref),
                ("scene_revision", scene_revision), ("frame_id", frame_id),
                ("calibration_ref", calibration_ref),
            )
        ):
            raise MultiObjectAgentError(f"geometry evidence is not bound to measured entity {ref}")
        bindings.append({
            "entity_ref": ref,
            "benchmark_object_ref": measured["benchmark_object_ref"],
            "destination_ref": measured["destination_ref"],
            "observation_ref": observation_ref,
            "scene_revision": scene_revision,
            "frame_id": frame_id,
            "calibration_ref": calibration_ref,
            "geometry_artifact_ref": measured["geometry_artifact_ref"],
            "capability_snapshot_ref": measured.get("capability_snapshot_ref"),
            "assignment_ref": measured.get("assignment_ref"),
            "category": category,
            "required_evidence": tuple(dict.fromkeys((
                measured["geometry_artifact_ref"],
                *tuple(item for item in geometry.get("provenance", ()) if isinstance(item, str)),
            ))),
        })
    return bind_scene_objects(bindings, category=category)


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
                    *tuple(
                        (key, value)
                        for key, value in (
                            ("capability_snapshot_ref", item.capability_snapshot_ref),
                            ("assignment_ref", item.assignment_ref),
                        )
                        if value is not None
                    ),
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

    async def create_task_from_scene_understanding(
        self,
        *,
        task_description: str,
        understanding: Mapping[str, Any],
        measured_objects: Iterable[Mapping[str, Any]],
        verification: TaskVerificationContract,
        task_id: str,
        revision_id: str,
        entity_refs: Iterable[str] | None = None,
        category: str = "block",
    ) -> AgentTaskRecord:
        """Create one task from semantic claims joined to measured scene facts."""

        entities = bind_understood_scene_objects(
            understanding, measured_objects, entity_refs=entity_refs, category=category,
        )
        return await self.create_task(
            task_description=task_description, entities=entities, verification=verification,
            task_id=task_id, revision_id=revision_id,
        )

    async def run(
        self,
        *,
        task_description: str,
        entities: Iterable[SceneObjectBinding | dict[str, Any]],
        verification: TaskVerificationContract,
        task_id: str,
        revision_id: str,
    ) -> LongHorizonTaskResult:
        bound = bind_scene_objects(entities)
        bound_scene_revision = bound[0].scene_revision
        current_scene_revision = self.scene_revision_provider(task_id)
        if current_scene_revision != bound_scene_revision:
            raise MultiObjectAgentError(
                "bound scene revision is stale before AgentTask persistence"
            )
        task = await self.create_task(
            task_description=task_description,
            entities=bound,
            verification=verification,
            task_id=task_id,
            revision_id=revision_id,
        )
        controller = self.agent_loop.build_long_horizon_controller()
        if not isinstance(controller, LongHorizonTaskController):
            raise MultiObjectAgentError("AgentLoop did not provide an executable long-horizon controller")
        return await controller.run(task.task_id)

    async def run_from_scene_understanding(
        self,
        *,
        task_description: str,
        understanding: Mapping[str, Any],
        measured_objects: Iterable[Mapping[str, Any]],
        verification: TaskVerificationContract,
        task_id: str,
        revision_id: str,
        entity_refs: Iterable[str] | None = None,
        category: str = "block",
    ) -> LongHorizonTaskResult:
        """Run the existing Agent controller after the semantic/measured join."""

        entities = bind_understood_scene_objects(
            understanding, measured_objects, entity_refs=entity_refs, category=category,
        )
        return await self.run(
            task_description=task_description, entities=entities, verification=verification,
            task_id=task_id, revision_id=revision_id,
        )


__all__ = [
    "MultiObjectAgentError",
    "MultiObjectAgentRunner",
    "SceneObjectBinding",
    "bind_scene_objects",
    "bind_understood_scene_objects",
]
