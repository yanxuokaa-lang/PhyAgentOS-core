"""Profile-owned contact qualification modes for no-motion route planning."""

from collections.abc import Mapping
from typing import Any

OBSERVED_OCCUPANCY = "observed_occupancy"
PLANNER_WORLD_ONLY = "planner_world_only"
CONTACT_QUALIFICATION_MODES = frozenset({OBSERVED_OCCUPANCY, PLANNER_WORLD_ONLY})


def contact_qualification_mode(profile: Mapping[str, Any]) -> str:
    """Validate and return the Adapter-owned contact qualification policy."""

    policy = profile.get("contact_qualification")
    if not isinstance(policy, Mapping) or set(policy) != {"mode"}:
        raise ValueError("contact_qualification must contain exactly one mode")
    mode = policy.get("mode")
    if mode not in CONTACT_QUALIFICATION_MODES:
        raise ValueError(
            "contact_qualification.mode must be observed_occupancy or planner_world_only"
        )
    if mode == OBSERVED_OCCUPANCY and not isinstance(
        profile.get("observed_collision"), Mapping
    ):
        raise ValueError("observed_occupancy requires observed_collision policy")
    if mode == PLANNER_WORLD_ONLY and "observed_collision" in profile:
        raise ValueError("planner_world_only must not configure observed_collision")
    return mode


__all__ = [
    "CONTACT_QUALIFICATION_MODES",
    "OBSERVED_OCCUPANCY",
    "PLANNER_WORLD_ONLY",
    "contact_qualification_mode",
]
