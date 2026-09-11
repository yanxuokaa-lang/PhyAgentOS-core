"""Geometry-only Queries; task strategy remains with the caller."""

IDENTITY_KEYS = ("observation_ref", "scene_revision", "calibration_ref")


def _spec(tool_id, properties, required, description):
    return {
        "tool_id": tool_id, "endpoint_id": tool_id.replace(".", "_"),
        "operation": "resolve", "semantics": "query", "description": description,
        "input_schema": {"type": "object", "additionalProperties": False,
                         "properties": properties, "required": required},
        "output_schema": {
            "type": "object", "required": ["status", "motion_authorized"],
            "properties": {"status": {"enum": ["available", "unavailable"]},
                           "motion_authorized": {"const": False}},
        },
        "planning": {"schema_version": "paos-tool-spec-policy/v1",
                     "capabilities": [tool_id], "refreshes_scene": False,
                     "input_binding_keys": [], "scene_write_behavior": "none"},
    }


_REF = {"type": "string", "minLength": 1}
BIND_TOOL_SPEC = _spec(
    "scene.bind",
    {**{k: _REF for k in IDENTITY_KEYS},
     "entity_refs": {"type": "array", "minItems": 1, "uniqueItems": True, "items": _REF}},
    [*IDENTITY_KEYS, "entity_refs"],
    "Resolve selected observed entities to execution objects using calibrated geometry. "
    "Returns binding_ref and world geometry; does not choose goals or authorize motion.",
)
TARGET_TOOL_SPEC = _spec(
    "manipulation.target",
    {"binding_ref": _REF, "entity_ref": _REF, "frame_id": _REF, "unit": {"const": "m"},
     "frame_T_object_target": {"type": "array", "minItems": 16, "maxItems": 16,
                               "items": {"type": "number"}}},
    ["binding_ref", "entity_ref", "frame_id", "unit", "frame_T_object_target"],
    "Resolve a caller-selected object target pose in world or the bound observation frame. "
    "Returns destination_ref and world_T_object_target. No sorting, slot selection, "
    "placement feasibility or motion authorization; use manipulation.prepare afterward.",
)

_POSE = {"type": "array", "minItems": 16, "maxItems": 16, "items": {"type": "number"}}
_COMMON_OUTPUT = {**{key: _REF for key in IDENTITY_KEYS}, "binding_ref": _REF,
                  "frame_id": {"const": "world"}, "unit": {"const": "m"},
                  "evidence_refs": {"type": "array", "items": _REF},
                  "error": {"type": "object", "properties": {"code": _REF, "message": _REF}}}
BIND_TOOL_SPEC["output_schema"]["properties"].update({
    **_COMMON_OUTPUT, "captured_at": _REF, "validity": {"const": "current_action_driven_scene"},
    "observation_frame_id": _REF, "world_T_observation": _POSE,
    "entities": {"type": "array", "items": {"type": "object", "properties": {
        "entity_ref": _REF, "execution_entity_ref": _REF, "world_T_object": _POSE,
        "half_extents_m": {"type": "array", "minItems": 3, "maxItems": 3, "items": {"type": "number"}},
    }}},
})
TARGET_TOOL_SPEC["output_schema"]["properties"].update({
    **_COMMON_OUTPUT, "entity_ref": _REF, "destination_ref": _REF, "world_T_object_target": _POSE,
})
