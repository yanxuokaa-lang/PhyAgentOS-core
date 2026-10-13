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
    error = payload.get("error")
    if isinstance(error, Mapping):
        retryable = error.get("retryable")
        if "retryable_in_revision" not in payload and isinstance(retryable, bool):
            payload = {**payload, "retryable_in_revision": retryable}
    return payload


def explicit_scene_revision(value: Mapping[str, Any] | None) -> str | None:
    """Return a normalized scene identity only when the payload states one."""
    if not isinstance(value, Mapping):
        return None
    scene_revision = value.get("scene_revision")
    if not isinstance(scene_revision, str) or not scene_revision.strip():
        return None
    return scene_revision.strip()


def fresh_binding_for_execution_identity(
    records: list[Any] | tuple[Any, ...],
    *,
    action_index: int,
    execution_entity_ref: str | None,
    source_scene_revision: str | None,
    expected_scene_revision: str | None = None,
) -> dict[str, str] | None:
    """Return a post-Action binding that re-establishes one stable identity.

    A binding is fresh only when it was appended after the Action, carries a
    complete observation/scene/calibration identity, and belongs to the
    Action's new scene (when the Runtime supplied one).  This proves visual
    identity only; it says nothing about possession or support state.
    """

    if (
        not isinstance(action_index, int)
        or action_index < 0
        or not isinstance(execution_entity_ref, str)
        or not execution_entity_ref
        or not isinstance(source_scene_revision, str)
        or not source_scene_revision
    ):
        return None
    if expected_scene_revision is not None and (
        not isinstance(expected_scene_revision, str) or not expected_scene_revision
    ):
        return None
    for record in reversed(tuple(records)[action_index + 1 :]):
        if (
            getattr(record, "tool_id", None) != "scene.bind"
            or getattr(record, "semantics", None) != "query"
            or getattr(record, "status", None) != "succeeded"
        ):
            continue
        facts = response_facts(getattr(record, "response", None))
        if facts.get("status") != "available":
            continue
        scene_revision = explicit_scene_revision(facts)
        if scene_revision is None or scene_revision == source_scene_revision:
            continue
        if expected_scene_revision is not None and scene_revision != expected_scene_revision:
            continue
        if any(
            not isinstance(facts.get(name), str) or not facts[name]
            for name in ("observation_ref", "calibration_ref")
        ):
            continue
        binding_ref = facts.get("binding_ref")
        if not isinstance(binding_ref, str) or not binding_ref.startswith("artifact://"):
            continue
        entity_ref = next(
            (
                item.get("entity_ref")
                for item in facts.get("entities", ())
                if isinstance(item, Mapping)
                and item.get("execution_entity_ref") == execution_entity_ref
                and isinstance(item.get("entity_ref"), str)
                and item["entity_ref"]
            ),
            None,
        )
        if entity_ref is None:
            continue
        return {
            "entity_ref": entity_ref,
            "execution_entity_ref": execution_entity_ref,
            "observation_ref": facts["observation_ref"],
            "scene_revision": scene_revision,
            "calibration_ref": facts["calibration_ref"],
            "binding_ref": binding_ref,
        }
    return None
