"""Discovery and composition for deployment-owned understanding inference."""

from __future__ import annotations

from copy import deepcopy
from importlib.metadata import entry_points
from typing import Any, Mapping, Protocol, runtime_checkable

from ..artifacts import ArtifactResolver
from .artifact_understanding import ArtifactResolvingSceneUnderstandingProvider


@runtime_checkable
class SceneUnderstandingInferenceFactory(Protocol):
    """Create one inference implementation from deployment-owned settings."""

    inference_id: str

    def create(self, *, configuration: Mapping[str, Any]) -> Any:
        """Return an object implementing ``infer(request)`` or a callable."""


class SceneUnderstandingInferenceRegistry:
    """Discover opt-in implementations without importing their vendors in Core."""

    ENTRY_POINT_GROUP = "paos.scene_understanding_inference"

    def __init__(self) -> None:
        self._factories: dict[str, SceneUnderstandingInferenceFactory] = {}

    def register(self, factory: SceneUnderstandingInferenceFactory) -> None:
        if not isinstance(factory, SceneUnderstandingInferenceFactory):
            raise TypeError("scene-understanding inference factory does not implement the PAOS interface")
        inference_id = factory.inference_id
        if not isinstance(inference_id, str) or not inference_id or inference_id.strip() != inference_id:
            raise ValueError("scene-understanding inference ID must be non-empty and normalized")
        if inference_id in self._factories:
            raise ValueError(f"scene-understanding inference factory already registered: {inference_id}")
        self._factories[inference_id] = factory

    def discover(self) -> tuple[str, ...]:
        discovered = entry_points()
        candidates = (
            discovered.select(group=self.ENTRY_POINT_GROUP)
            if hasattr(discovered, "select")
            else discovered.get(self.ENTRY_POINT_GROUP, ())
        )
        for item in candidates:
            self.register(item.load()())
        return tuple(sorted(self._factories))

    def create_inference(
        self, inference_id: str, *, configuration: Mapping[str, Any] | None = None
    ) -> Any:
        try:
            factory = self._factories[inference_id]
        except KeyError as exc:
            raise KeyError(f"scene-understanding inference is not registered: {inference_id}") from exc
        inference = factory.create(configuration=deepcopy(dict(configuration or {})))
        if not callable(getattr(inference, "infer", None)) and not callable(inference):
            raise TypeError("scene-understanding inference must expose infer(request) or be callable")
        return inference

    def compose(
        self,
        inference_id: str,
        *,
        resolver: ArtifactResolver,
        configuration: Mapping[str, Any] | None = None,
    ) -> ArtifactResolvingSceneUnderstandingProvider:
        inference = self.create_inference(inference_id, configuration=configuration)
        return ArtifactResolvingSceneUnderstandingProvider(resolver, inference)


__all__ = ["SceneUnderstandingInferenceFactory", "SceneUnderstandingInferenceRegistry"]
