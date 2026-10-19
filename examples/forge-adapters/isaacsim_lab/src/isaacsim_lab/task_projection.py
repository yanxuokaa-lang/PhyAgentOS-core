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
) -> dict[str, Any]:
    """Bind ``source_label -> destination_label`` to one PAOS pour cycle.

    ``source_path`` and ``destination_path`` are intentionally not accepted as
    authority from ``task``.  They are returned for diagnostics from the
    profile that was already bound to the scene.
    """

    if not isinstance(task, Mapping):
        raise LabTaskProjectionError("Agent laboratory task must be a mapping")
    if task.get("task_type") != "pour_liquid":
        raise LabTaskProjectionError("only pour_liquid Agent tasks are supported")
    source_label = task.get("source_label")
    destination_label = task.get("destination_label")
    if source_label != profile.source_label:
        raise LabTaskProjectionError(
            f"source label is not bound to the configured scene: {source_label!r}"
        )
    if destination_label != profile.destination_label:
        raise LabTaskProjectionError(
            f"destination label is not bound to the configured scene: {destination_label!r}"
        )
    for key, expected in (
        ("entity_ref", f"entity://{profile.source_path.rsplit('/', 1)[-1]}"),
        ("destination_ref", f"destination://{profile.destination_path.rsplit('/', 1)[-1]}"),
    ):
        supplied = task.get(key)
        if supplied is not None and supplied != expected:
            raise LabTaskProjectionError(f"Agent task {key} does not match the configured scene")

    previous: dict[str, Any] = {}
    if "parameters" in task:
        parameters = task["parameters"]
        if not isinstance(parameters, Mapping):
            raise LabTaskProjectionError("task parameters must be a mapping")
        previous["parameters"] = deepcopy(dict(parameters))
    paos_input = profile.paos_input(previous, operation="pour_cycle")
    return {
        "task_type": "pour_liquid",
        "source_label": profile.source_label,
        "destination_label": profile.destination_label,
        "source_path": profile.source_path,
        "destination_path": profile.destination_path,
        "paos_input": paos_input,
    }


__all__ = ["LabTaskProjectionError", "project_pour_task"]
