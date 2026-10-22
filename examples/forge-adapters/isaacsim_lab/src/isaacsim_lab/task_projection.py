"""Project Agent-confirmed laboratory goals into the PAOS cycle contract.

The Agent supplies semantic labels.  The deployment profile remains the owner
of USD paths and scene identities, so a language model cannot invent a prim
path and bypass the observed scene binding.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .profile import LabProfileError, LabUtopiaProfile


class LabTaskProjectionError(LabProfileError):
    """The Agent goal cannot be bound to the configured laboratory scene."""


def project_pour_task(
    profile: LabUtopiaProfile,
    task: Mapping[str, Any],
    *,
    binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project a semantic task using a previously measured PAOS binding.

    The binding is produced by the provider-neutral observation/understanding/
    grasp query chain.  Profile paths remain adapter-private and are not
    returned as Agent task data or used as object identity.
    """

    if not isinstance(task, Mapping):
        raise LabTaskProjectionError("Agent laboratory task must be a mapping")
    if task.get("task_type") != "pour_liquid":
        raise LabTaskProjectionError("only pour_liquid Agent tasks are supported")
    if not isinstance(binding, Mapping):
        raise LabTaskProjectionError("perception binding is required before task projection")
    required = (
        "entity_ref", "destination_ref", "observation_ref", "scene_revision",
        "frame_id", "calibration_ref", "freshness_ms", "max_age_ms", "binding_ref",
    )
    if any(key not in binding for key in required):
        raise LabTaskProjectionError("perception binding provenance is incomplete")
    if any(
        not isinstance(binding[key], str) or not binding[key].strip()
        for key in required
        if key not in {"freshness_ms", "max_age_ms"}
    ):
        raise LabTaskProjectionError("perception binding provenance is invalid")
    if (
        not isinstance(binding["freshness_ms"], int)
        or isinstance(binding["freshness_ms"], bool)
        or not isinstance(binding["max_age_ms"], int)
        or isinstance(binding["max_age_ms"], bool)
        or binding["freshness_ms"] < 0
        or binding["max_age_ms"] < 1
        or binding["freshness_ms"] > binding["max_age_ms"]
    ):
        raise LabTaskProjectionError("perception binding is stale or has invalid freshness")
    source_label = task.get("source_label")
    destination_label = task.get("destination_label")
    binding_label = binding.get("semantic_label") or binding.get("category")
    if source_label is not None and source_label != binding_label:
        raise LabTaskProjectionError(
            f"source label is not bound to the perception binding: {source_label!r}"
        )
    binding_destination = binding.get("destination_label") or binding.get("destination_category")
    if destination_label is not None and binding_destination is not None and destination_label != binding_destination:
        raise LabTaskProjectionError(
            f"destination label is not bound to the perception binding: {destination_label!r}"
        )

    parameters: dict[str, Any] = {}
    if "parameters" in task:
        supplied_parameters = task["parameters"]
        if not isinstance(supplied_parameters, Mapping):
            raise LabTaskProjectionError("task parameters must be a mapping")
        parameters = deepcopy(dict(supplied_parameters))
    return {
        "task_type": "pour_liquid",
        "source_label": binding_label,
        "destination_label": destination_label,
        "binding": deepcopy(dict(binding)),
        "parameters": parameters,
    }


__all__ = ["LabTaskProjectionError", "project_pour_task"]
