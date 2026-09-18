"""Read persisted Gateway facts without conflating input and effects."""

from collections.abc import Mapping
from typing import Any


def response_facts(response: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {}
    payload = response.get("data")
    payload = payload if isinstance(payload, dict) else response
    result = payload.get("result")
    if isinstance(result, dict):
        payload = {**payload, **result}
    summary = payload.get("capability_outcome_summary")
    if isinstance(summary, dict):
        payload = {**payload, **summary}
    return payload


def explicit_scene_revision(value: Mapping[str, Any] | None) -> str | None:
    """Return a normalized scene identity only when the payload states one."""
    if not isinstance(value, Mapping):
        return None
    scene_revision = value.get("scene_revision")
    if not isinstance(scene_revision, str) or not scene_revision.strip():
        return None
    return scene_revision.strip()
