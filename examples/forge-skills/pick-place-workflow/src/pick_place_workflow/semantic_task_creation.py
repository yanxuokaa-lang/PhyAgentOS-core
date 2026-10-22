"""Provider-neutral semantic task creation for the pick-place workflow.

The builder is an injected composition boundary.  It turns semantic requests
into measured bindings through PAOS Query ports, then delegates graph creation
to the existing subtask planner.  It owns no task store, AgentLoop state, or
actuator handle.
"""

from __future__ import annotations

import json
from typing import Any, Protocol
from uuid import uuid4

from PhyAgentOS.planning import canonical_sha256
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .agent_planning import (
    bind_subtask_from_semantics,
    bind_subtask_from_semantics_async,
    compose_subtask_plan,
)
from .perception_binding import BindingRequest, PerceptionBindingAdapter, QueryInvoker
from .subtask_executor import SubtaskOperation, SubtaskSpec


class SemanticTaskCreationError(ValueError):
    """Semantic requests cannot be converted into a measured PAOS plan."""


class SemanticSubtaskRequest(BaseModel):
    """Agent-level request containing only semantic target information."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    subtask_id: str = Field(min_length=1)
    operation: SubtaskOperation
    source_category: str = Field(min_length=1)
    destination_category: str = Field(min_length=1)
    sensor_refs: tuple[str, ...] = Field(min_length=1)
    max_age_ms: int = Field(gt=0)
    process_frame: str | None = Field(default=None, min_length=1)
    source_selector: dict[str, str | int | float | bool] | None = None
    destination_selector: dict[str, str | int | float | bool] | None = None
    depends_on: tuple[str, ...] = ()
    parameters: dict[str, Any] = Field(default_factory=dict)
    semantic_intent: dict[str, Any] | None = None
    return_destination_ref: str | None = Field(default=None, min_length=1)

    @field_validator("sensor_refs", "depends_on")
    @classmethod
    def nonempty_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError("semantic references must be non-empty strings")
        if len(value) != len(set(value)):
            raise ValueError("semantic references must be unique")
        return value

    @field_validator("parameters", "semantic_intent")
    @classmethod
    def finite_json(cls, value):
        if value is not None:
            try:
                json.dumps(value, ensure_ascii=False, allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise ValueError("semantic request contains non-finite JSON") from exc
        return value


class SemanticPlanBuilder(Protocol):
    def build(self, task_description: str, semantic_subtasks: list[dict[str, Any]]) -> Any: ...


class QuerySemanticPlanBuilder:
    """Build a concrete, measured subtask graph through an injected Query port."""

    def __init__(
        self,
        query_invoker: QueryInvoker,
        *,
        planner_decision_digest: str | None = None,
        policy_snapshot_digest: str | None = None,
    ) -> None:
        self.query_invoker = query_invoker
        self.planner_decision_digest = planner_decision_digest
        self.policy_snapshot_digest = policy_snapshot_digest

    def _plan_digests(self, task_description: str, semantic_subtasks: list[dict[str, Any]]):
        requests = [
            SemanticSubtaskRequest.model_validate(item).model_dump(mode="json")
            for item in semantic_subtasks
        ]
        planner_digest = self.planner_decision_digest or canonical_sha256({
            "task_description": task_description,
            "semantic_subtasks": requests,
        })
        policy_digest = self.policy_snapshot_digest or canonical_sha256({
            "contract": "paos.perception_binding/v1",
            "query_capabilities": [
                "scene.observe", "scene.understand", "grasp.propose",
                "manipulation.capabilities",
            ],
        })
        return planner_digest, policy_digest

    async def _runtime_policy_digest(self) -> str:
        get_tool = getattr(self.query_invoker, "get_tool", None)
        if not callable(get_tool):
            return self._plan_digests("", [])[1]
        contracts = []
        for tool_id in PerceptionBindingAdapter._QUERY_SPECS:
            response = await get_tool(tool_id)
            payload = response.get("data") if isinstance(response, dict) else None
            if not isinstance(payload, dict):
                raise SemanticTaskCreationError(f"{tool_id} ToolSpec is unavailable")
            expected = PerceptionBindingAdapter._QUERY_SPECS[tool_id]
            if (
                payload.get("tool_id") != tool_id
                or payload.get("semantics") != "query"
                or payload.get("endpoint_id") != expected.get("endpoint_id")
                or payload.get("operation") != expected.get("operation")
            ):
                raise SemanticTaskCreationError(f"{tool_id} ToolSpec differs from the PAOS Query contract")
            contracts.append(payload)
        return canonical_sha256({"query_tool_specs": contracts})

    def build(self, task_description: str, semantic_subtasks: list[dict[str, Any]]) -> dict[str, Any]:
        if not isinstance(semantic_subtasks, list) or not semantic_subtasks:
            raise SemanticTaskCreationError("semantic_subtasks must contain at least one request")
        planner_digest, policy_digest = self._plan_digests(task_description, semantic_subtasks)
        task_id = f"task_{uuid4().hex[:16]}"
        revision_id = f"revision_{uuid4().hex[:16]}"
        specs: list[SubtaskSpec] = []
        scene_revisions: set[str] = set()
        for raw in semantic_subtasks:
            request = SemanticSubtaskRequest.model_validate(raw)
            adapter = PerceptionBindingAdapter(
                self.query_invoker,
                BindingRequest(
                    sensor_refs=request.sensor_refs,
                    source_category=request.source_category,
                    destination_category=request.destination_category,
                    max_age_ms=request.max_age_ms,
                    process_frame=request.process_frame,
                    source_selector=request.source_selector,
                    destination_selector=request.destination_selector,
                ),
            )
            try:
                spec = bind_subtask_from_semantics(
                    request.subtask_id,
                    request.operation,
                    adapter,
                    depends_on=request.depends_on,
                    parameters=request.parameters,
                    semantic_intent=request.semantic_intent,
                    return_destination_ref=request.return_destination_ref,
                )
            except ValueError as exc:
                raise SemanticTaskCreationError(str(exc)) from exc
            if specs:
                serialized_dependencies = tuple(dict.fromkeys((*spec.depends_on, specs[-1].subtask_id)))
                spec = spec.model_copy(update={"depends_on": serialized_dependencies})
            specs.append(spec)
            scene_revisions.add(spec.binding.scene_revision)
        if len(scene_revisions) != 1:
            raise SemanticTaskCreationError("semantic subtasks must share one scene revision")
        try:
            return compose_subtask_plan(
                task_id,
                revision_id,
                tuple(specs),
                planner_decision_digest=planner_digest,
                policy_snapshot_digest=policy_digest,
            ).graph.model_dump(mode="json")
        except ValueError as exc:
            raise SemanticTaskCreationError(str(exc)) from exc


class AsyncQuerySemanticPlanBuilder(QuerySemanticPlanBuilder):
    """Async builder for Forge Gateway or another awaitable Query port."""

    async def build(self, task_description: str, semantic_subtasks: list[dict[str, Any]]) -> dict[str, Any]:
        if not isinstance(semantic_subtasks, list) or not semantic_subtasks:
            raise SemanticTaskCreationError("semantic_subtasks must contain at least one request")
        planner_digest, _ = self._plan_digests(task_description, semantic_subtasks)
        policy_digest = self.policy_snapshot_digest or await self._runtime_policy_digest()
        task_id = f"task_{uuid4().hex[:16]}"
        revision_id = f"revision_{uuid4().hex[:16]}"
        specs: list[SubtaskSpec] = []
        scene_revisions: set[str] = set()
        for raw in semantic_subtasks:
            request = SemanticSubtaskRequest.model_validate(raw)
            adapter = PerceptionBindingAdapter(
                self.query_invoker,
                BindingRequest(
                    sensor_refs=request.sensor_refs,
                    source_category=request.source_category,
                    destination_category=request.destination_category,
                    max_age_ms=request.max_age_ms,
                    process_frame=request.process_frame,
                    source_selector=request.source_selector,
                    destination_selector=request.destination_selector,
                ),
            )
            try:
                spec = await bind_subtask_from_semantics_async(
                    request.subtask_id, request.operation, adapter,
                    depends_on=request.depends_on, parameters=request.parameters,
                    semantic_intent=request.semantic_intent,
                    return_destination_ref=request.return_destination_ref,
                )
            except ValueError as exc:
                raise SemanticTaskCreationError(str(exc)) from exc
            if specs:
                dependencies = tuple(dict.fromkeys((*spec.depends_on, specs[-1].subtask_id)))
                spec = spec.model_copy(update={"depends_on": dependencies})
            specs.append(spec)
            scene_revisions.add(spec.binding.scene_revision)
        if len(scene_revisions) != 1:
            raise SemanticTaskCreationError("semantic subtasks must share one scene revision")
        try:
            return compose_subtask_plan(
                task_id, revision_id, tuple(specs),
                planner_decision_digest=planner_digest,
                policy_snapshot_digest=policy_digest,
            ).graph.model_dump(mode="json")
        except ValueError as exc:
            raise SemanticTaskCreationError(str(exc)) from exc


class PickPlaceSemanticPlanBuilderFactory:
    """Optional host plugin binding this workflow builder to a PAOS Query port."""

    builder_id = "pick_place_workflow"

    def create(self, *, query_invoker: QueryInvoker) -> AsyncQuerySemanticPlanBuilder:
        return AsyncQuerySemanticPlanBuilder(query_invoker)


__all__ = [
    "QuerySemanticPlanBuilder",
    "AsyncQuerySemanticPlanBuilder",
    "SemanticPlanBuilder",
    "SemanticSubtaskRequest",
    "SemanticTaskCreationError",
    "PickPlaceSemanticPlanBuilderFactory",
]
