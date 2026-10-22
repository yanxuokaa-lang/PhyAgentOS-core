"""Compose artifact resolution with an injected scene-understanding inference."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol

from PhyAgentOS.forge.artifacts import ArtifactResolver


class SceneUnderstandingInference(Protocol):
    """Inference implementation that consumes resolved observation artifacts."""

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None: ...


class ArtifactResolvingSceneUnderstandingProvider:
    """Resolve observation artifacts before delegating semantic inference.

    The inference receives the original Query fields plus ``resolved_artifacts``
    entries containing the opaque ref, media type, optional kind, and raw bytes.
    It remains responsible for semantic claims; the PAOS endpoint validates the
    returned claims and their provenance.
    """

    def __init__(
        self,
        resolver: ArtifactResolver,
        inference: SceneUnderstandingInference | Callable[[Mapping[str, Any]], Any],
    ) -> None:
        if not callable(getattr(resolver, "resolve", None)):
            raise TypeError("artifact resolver must expose resolve(ref)")
        if not callable(getattr(inference, "infer", None)) and not callable(inference):
            raise TypeError("scene-understanding inference must expose infer(request) or be callable")
        self._resolver = resolver
        self._inference = inference

    def understand(self, request: dict[str, Any]) -> Mapping[str, Any] | None:
        if not isinstance(request, Mapping):
            raise TypeError("scene-understanding request must be an object")
        descriptors = _observation_artifacts(request)
        if not descriptors:
            raise ValueError("scene-understanding request has no observation artifacts")

        resolved = []
        for descriptor in descriptors:
            ref = descriptor["ref"]
            content = self._resolver.resolve(ref)
            if content is None:
                raise FileNotFoundError(f"observation artifact is unavailable: {ref}")
            declared_media_type = descriptor.get("media_type")
            if declared_media_type is not None and declared_media_type != content.media_type:
                raise ValueError(f"observation artifact media type mismatch: {ref}")
            resolved.append({
                **descriptor,
                "media_type": content.media_type,
                "data": content.data,
            })

        inference_request = dict(request)
        inference_request["resolved_artifacts"] = resolved
        infer = getattr(self._inference, "infer", None)
        result = infer(inference_request) if callable(infer) else self._inference(inference_request)
        if result is not None and not isinstance(result, Mapping):
            raise TypeError("scene-understanding inference must return an object or null")
        return result


def _observation_artifacts(request: Mapping[str, Any]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    positions: dict[str, int] = {}

    def add(value: Any) -> None:
        if isinstance(value, str):
            descriptor = {"ref": value}
        elif isinstance(value, Mapping) and isinstance(value.get("ref"), str):
            descriptor = {key: value[key] for key in ("ref", "kind", "media_type") if key in value}
        else:
            raise ValueError("observation artifact entry must be a ref or descriptor")
        ref = descriptor["ref"]
        if ref not in positions:
            positions[ref] = len(artifacts)
            artifacts.append(descriptor)
        else:
            artifacts[positions[ref]].update(descriptor)

    for value in request.get("artifacts", ()):
        add(value)
    for view in request.get("views", ()):
        if not isinstance(view, Mapping):
            raise ValueError("observation view must be an object")
        for value in view.get("artifacts", ()):
            add(value)
    return artifacts


__all__ = ["ArtifactResolvingSceneUnderstandingProvider", "SceneUnderstandingInference"]
