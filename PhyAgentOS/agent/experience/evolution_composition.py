"""Composition root for the optional evolution extension.

The host owns the coordinator, persistence, and candidate lifecycle.  This
module only wires those existing ports to an already selected extension (or
constructs one when the optional distribution is installed); it does not
infer provider semantics or create another scheduler/store.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from loguru import logger

from PhyAgentOS.agent.experience.evolution_extension_adapter import (
    EvolutionCandidateLifecycleAdapter,
)


def compose_evolution_extension(
    coordinator: Any,
    *,
    extension: Any | None = None,
    registry: Any | None = None,
    projection_port: Any | None = None,
    policy_digest_resolver: Callable[[Any], tuple[str, str] | None] | None = None,
    event_sink: Callable[[str, str, dict[str, Any]], None] | None = None,
    extension_factory: Callable[..., Any] | None = None,
) -> Any | None:
    """Attach one optional evolution extension to a PAOS coordinator.

    ``registry`` and ``projection_port`` are intentionally explicit when the
    extension must be constructed by the host.  If an extension is already
    supplied, its own selected registry/projection are reused.  Repeated calls
    are idempotent and never replace an installed extension.
    """

    existing = getattr(coordinator, "evolution_extension", None)
    if existing is not None:
        _ensure_candidate_lifecycle(coordinator, existing, policy_digest_resolver)
        return existing

    if extension is None:
        if registry is None or projection_port is None:
            return None
        try:
            if extension_factory is None:
                module = importlib.import_module("evolution.plugin")
                extension_factory = module.EvolutionExtension
            extension = extension_factory(
                registry=registry,
                projection_port=projection_port,
                event_sink=_host_event_sink(coordinator, event_sink),
            )
        except (ImportError, ModuleNotFoundError) as exc:
            logger.info("Evolution extension unavailable: error_type={}", type(exc).__name__)
            return None
        except Exception as exc:
            _record_host_event(
                coordinator,
                "evolution_composition_failed",
                "host",
                {"error": type(exc).__name__},
            )
            logger.warning("Evolution extension composition failed open: error_type={}", type(exc).__name__)
            return None

    _ensure_candidate_lifecycle(coordinator, extension, policy_digest_resolver)
    current_event_sink = getattr(extension, "event_sink", None)
    if current_event_sink is None:
        extension.event_sink = _host_event_sink(coordinator, event_sink)
    else:
        extension.event_sink = _host_event_sink(coordinator, current_event_sink)
    coordinator.evolution_extension = extension
    return extension


def _ensure_candidate_lifecycle(
    coordinator: Any,
    extension: Any,
    policy_digest_resolver: Callable[[Any], tuple[str, str] | None] | None,
) -> None:
    if getattr(extension, "candidate_lifecycle", None) is not None:
        return
    extension.candidate_lifecycle = EvolutionCandidateLifecycleAdapter(
        coordinator.store,
        policy_candidates=getattr(coordinator, "policy_candidates", None),
        policy_digest_resolver=policy_digest_resolver,
        event_recorder=coordinator.store.record_event,
    )


def _host_event_sink(
    coordinator: Any,
    external_sink: Callable[[str, str, dict[str, Any]], None] | None,
) -> Callable[[str, str, dict[str, Any]], None]:
    def record(event_type: str, ref: str, payload: dict[str, Any]) -> None:
        _record_host_event(coordinator, event_type, ref, payload)
        if external_sink is not None:
            external_sink(event_type, ref, payload)

    return record


def _record_host_event(coordinator: Any, event_type: str, ref: str, payload: dict[str, Any]) -> None:
    try:
        coordinator.store.record_event(event_type, ref, payload)
    except Exception as exc:
        logger.warning("Evolution host event persistence failed open: error_type={}", type(exc).__name__)


__all__ = ["compose_evolution_extension"]
