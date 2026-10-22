"""Host discovery for optional semantic task-plan builder extensions."""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SemanticPlanBuilderFactory(Protocol):
    """Create a semantic plan builder around the host's PAOS Query client."""

    builder_id: str

    def create(self, *, query_invoker: Any) -> Any:
        """Return a builder implementing the Forge task-creation protocol."""


class SemanticPlanBuilderRegistry:
    """Discover opt-in ``paos.semantic_plan_builders`` factories."""

    ENTRY_POINT_GROUP = "paos.semantic_plan_builders"

    def __init__(self) -> None:
        self._factories: dict[str, SemanticPlanBuilderFactory] = {}

    def register(self, factory: SemanticPlanBuilderFactory) -> None:
        if not isinstance(factory, SemanticPlanBuilderFactory):
            raise TypeError("semantic plan builder factory does not implement the PAOS interface")
        if not factory.builder_id or factory.builder_id.strip() != factory.builder_id:
            raise ValueError("semantic plan builder factory ID must be non-empty and normalized")
        if factory.builder_id in self._factories:
            raise ValueError(f"semantic plan builder factory already registered: {factory.builder_id}")
        self._factories[factory.builder_id] = factory

    def discover(self) -> tuple[str, ...]:
        """Load installed opt-in factories; import and contract failures stay explicit."""
        discovered = entry_points()
        candidates = (
            discovered.select(group=self.ENTRY_POINT_GROUP)
            if hasattr(discovered, "select")
            else discovered.get(self.ENTRY_POINT_GROUP, ())
        )
        for item in candidates:
            factory = item.load()()
            self.register(factory)
        return tuple(sorted(self._factories))

    def create(self, builder_id: str, *, query_invoker: Any) -> Any:
        try:
            factory = self._factories[builder_id]
        except KeyError as exc:
            raise KeyError(f"semantic plan builder is not registered: {builder_id}") from exc
        builder = factory.create(query_invoker=query_invoker)
        if not callable(getattr(builder, "build", None)):
            raise TypeError("semantic plan builder must provide build(task_description, subtasks)")
        return builder


__all__ = ["SemanticPlanBuilderFactory", "SemanticPlanBuilderRegistry"]
