from __future__ import annotations

from pick_place_workflow.grounding import STAGING_TOOL_SPEC


def _field(name: str):
    if isinstance(STAGING_TOOL_SPEC, dict):
        return STAGING_TOOL_SPEC[name]
    return getattr(STAGING_TOOL_SPEC, name)


def test_staging_tool_is_provider_neutral() -> None:
    assert _field("tool_id") == "manipulation.staging"
    schema = _field("input_schema")
    assert set(schema["required"]) == {"binding_ref", "entity_ref"}
    assert "destination_ref" not in schema.get("properties", {})
    assert "position" not in schema.get("properties", {})


def test_staging_tool_has_no_coordinate_input() -> None:
    properties = _field("input_schema")["properties"]
    assert set(properties) == {"binding_ref", "entity_ref"}
