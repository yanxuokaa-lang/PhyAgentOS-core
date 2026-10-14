"""Installable planner plugin seam for PAOS planning extensions."""

from __future__ import annotations

import json
from importlib.metadata import entry_points
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from PhyAgentOS.planning import NodeSettlement, PlanGraph, PlanNode, ReplanDelta


class PlanningRequest(BaseModel):
    """Task-conditioned, evidence-bound input to a planner plugin."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    revision_id: str
    scene_revision: str = ""
    task_description: str
    verification_goal: str = ""
    success_criteria: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    observations: dict[str, Any] = Field(default_factory=dict)
    available_capabilities: tuple[str, ...] = ()

    @field_validator("task_id", "revision_id")
    @classmethod
    def planning_identity(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("planner task and revision identities must be non-empty")
        return value

    @field_validator("scene_revision")
    @classmethod
    def optional_scene_identity(cls, value: str) -> str:
        return value.strip()

    @field_validator("observations")
    @classmethod
    def finite_observations(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("planner observations must contain finite JSON values") from exc
        return value


class MethodOption(BaseModel):
    """One already-materialized semantic method offered by a planner extension."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    method_id: str
    description: str
    applicable_obligations: tuple[str, ...]
    nodes: tuple[PlanNode, ...] = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()
    reason: str

    @field_validator("method_id")
    @classmethod
    def method_identity(cls, value: str) -> str:
        value = value.strip()
        if not value or value in {".", ".."} or "/" in value or "\\" in value:
            raise ValueError("method_id must be non-empty and path-safe")
        return value

    @field_validator("description", "reason")
    @classmethod
    def method_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("method option text must be non-empty")
        return value

    @field_validator("applicable_obligations", "evidence_refs")
    @classmethod
    def unique_nonempty_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized) or len(normalized) != len(set(normalized)):
            raise ValueError("method option references must be non-empty and unique")
        return normalized

    @model_validator(mode="after")
    def obligations_are_materialized(self) -> "MethodOption":
        if not self.applicable_obligations:
            raise ValueError("method option must identify an applicable obligation")
        materialized = {node.obligation_id for node in self.nodes}
        applicable = set(self.applicable_obligations)
        if applicable != materialized:
            raise ValueError(
                "method option applicable obligations must exactly identify its materialized "
                "node obligations"
            )
        return self


class ReplanProposal(BaseModel):
    """Pure plugin output consumed by the coordinator-owned revision path."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    delta: ReplanDelta
    plan_graph: PlanGraph
    plan_graph_ref: str
    reason: str | None = None

    @field_validator("plan_graph_ref")
    @classmethod
    def artifact_reference(cls, value: str) -> str:
        if not value.startswith("artifact://"):
            raise ValueError("planner proposal graph reference must be artifact://")
        return value


@runtime_checkable
class PlannerPlugin(Protocol):
    """Pure planner interface; implementations cannot own task or execution state."""

    plugin_id: str
    version: str

    def compose_plan(
        self,
        *,
        request: PlanningRequest,
    ) -> PlanGraph:
        """Derive a graph jointly from the task, scene, and capabilities."""

    def propose_replan(
        self,
        *,
        graph: PlanGraph,
        settlement: NodeSettlement,
        delta: ReplanDelta,
        context: object,
    ) -> ReplanProposal:
        """Return a replacement graph and artifact reference, without side effects."""


@runtime_checkable
class RecoveryPlannerPlugin(Protocol):
    """Optional planner capability for choosing a node recovery operation."""

    def select_recovery(
        self,
        *,
        graph: PlanGraph,
        settlement: NodeSettlement,
        delta: ReplanDelta,
        context: object,
    ) -> Literal["stop", "replay", "replan"]:
        """Choose recovery from persisted failure context without executing it."""


@runtime_checkable
class MethodFragmentPlugin(Protocol):
    """Optional pure capability for proposing complete semantic continuation options."""

    def propose_method_options(
        self,
        *,
        request: PlanningRequest,
    ) -> tuple[MethodOption, ...]:
        """Return in-memory options only; the host owns validation and persistence."""


class PlannerPluginRegistry:
    """Small registry supporting explicit registration and Python entry points."""

    def __init__(self) -> None:
        self._plugins: dict[str, PlannerPlugin] = {}

    def register(self, plugin: PlannerPlugin) -> None:
        if not isinstance(plugin, PlannerPlugin):
            raise TypeError("planner plugin does not implement the PAOS interface")
        if plugin.plugin_id in self._plugins:
            raise ValueError(f"planner plugin already registered: {plugin.plugin_id}")
        self._plugins[plugin.plugin_id] = plugin

    def get(self, plugin_id: str) -> PlannerPlugin:
        try:
            return self._plugins[plugin_id]
        except KeyError as exc:
            raise KeyError(f"planner plugin is not registered: {plugin_id}") from exc

    def discover(self) -> tuple[str, ...]:
        """Load opt-in ``paos.planners`` entry points; failures remain explicit."""
        discovered = entry_points()
        candidates = discovered.select(group="paos.planners") if hasattr(discovered, "select") else discovered.get("paos.planners", ())
        for item in candidates:
            plugin = item.load()()
            self.register(plugin)
        return tuple(sorted(self._plugins))


__all__ = [
    "MethodFragmentPlugin", "MethodOption", "PlannerPlugin", "PlannerPluginRegistry",
    "PlanningRequest", "RecoveryPlannerPlugin", "ReplanProposal",
]
