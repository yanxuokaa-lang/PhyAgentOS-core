"""Provider-neutral observed row-layout Query contract."""

IDENTITY_KEYS = ("observation_ref", "scene_revision", "calibration_ref")
LAYOUT_TOOL_SPEC = {
    "tool_id": "manipulation.layout", "endpoint_id": "manipulation_layout",
    "operation": "resolve", "semantics": "query",
    "description": "Bind observed entities and resolve their requested row order in world coordinates. No motion authorization.",
    "input_schema": {
        "type": "object", "additionalProperties": False,
        "properties": {
            **{k: {"type": "string", "minLength": 1} for k in IDENTITY_KEYS},
            "ordered_entities": {"type": "array", "minItems": 2, "uniqueItems": True,
                                 "items": {"type": "string", "minLength": 1}},
            "axis": {"type": "string", "enum": ["world+x", "world+y"]},
            "max_age_ms": {"type": "integer", "minimum": 1, "maximum": 60000},
        },
        "required": [*IDENTITY_KEYS, "ordered_entities", "axis", "max_age_ms"],
    },
    "output_schema": {
        "type": "object", "required": ["status", "motion_authorized"],
        "properties": {
            "status": {"type": "string", "enum": ["available", "unavailable"]},
            "motion_authorized": {"const": False},
            "layout_ref": {"type": "string"},
            **{k: {"type": "string"} for k in IDENTITY_KEYS},
            "frame_id": {"const": "world"}, "unit": {"const": "m"},
            "entity_bindings": {"type": "array", "items": {
                "type": "object", "required": ["entity_ref", "execution_entity_ref"],
                "properties": {k: {"type": "string"} for k in ("entity_ref", "execution_entity_ref")},
            }},
            "targets": {"type": "array", "items": {
                "type": "object", "required": ["entity_ref", "destination_ref", "world_T_object_target"],
                "properties": {
                    "entity_ref": {"type": "string"}, "destination_ref": {"type": "string"},
                    "world_T_object_target": {"type": "array", "minItems": 16, "maxItems": 16,
                                              "items": {"type": "number"}},
                },
            }},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "error": {"type": "object"},
        },
    },
    "planning": {"schema_version": "paos-tool-spec-policy/v1",
                 "capabilities": ["manipulation.layout"], "refreshes_scene": False,
                 "input_binding_keys": [], "scene_write_behavior": "none"},
}

