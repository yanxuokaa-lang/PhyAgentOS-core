"""Installable planner plugin seam for PAOS planning extensions."""

from __future__ import annotations

import json
from importlib.metadata import entry_points
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, field_validator

from PhyAgentOS.planning import NodeSettlement, PlanGraph, ReplanDelta


class PlanningRequest(BaseModel):
    """Task-conditioned, evidence-bound input to a planner plugin."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    revision_id: str
    task_description: str
    verification_goal: str = ""
    success_criteria: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    observations: dict[str, Any] = {}
    available_capabilities: tuple[str, ...] = ()

    @field_validator("observations")
    @classmethod
    def finite_observations(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("planner observations must contain finite JSON values") from exc
        return value


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
    "PlannerPlugin", "PlannerPluginRegistry", "PlanningRequest", "ReplanProposal",
]
