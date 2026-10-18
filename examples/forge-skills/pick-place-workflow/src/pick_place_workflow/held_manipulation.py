"""Prepared held-object operations on the existing Gateway Action lifecycle.

Providers own route preparation, admission and measured physical results. These
endpoints never generate motion or infer completion from requested parameters.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from PhyAgentOS.forge.capability_runtime import ActionAdmission

from .cycle_protocol import CyclePhaseProtocol, CycleProtocolError, evaluate_process_feedback

OPERATIONS = {"pour": "object.pour", "stir": "tool.stir", "place": "object.place"}
CYCLE_OPERATIONS = {"pour_cycle": "object.pour_cycle", "stir_cycle": "tool.stir_cycle"}
_TEXT = {"type": "string", "minLength": 1}
_POSITIVE = {"type": "number", "exclusiveMinimum": 0}
_PARAMETERS = {
    "pour": {"tilt_rad": {**_POSITIVE, "maximum": 3.141592653589793}, "hold_s": _POSITIVE},
    "stir": {"radius_m": _POSITIVE, "depth_m": _POSITIVE, "turns": _POSITIVE, "duration_s": _POSITIVE},
    "place": {},
}
_PROPERTIES = {
    name: deepcopy(_TEXT) for name in (
        "entity_ref", "destination_ref", "observation_ref", "scene_revision", "frame_id",
        "calibration_ref", "capability_snapshot_ref", "acquire_invocation_ref", "held_invocation_ref",
    )
}
_PROPERTIES.update(
    operation={"enum": list(OPERATIONS)},
    parameters={"type": "object"},
    freshness_ms={"type": "integer", "minimum": 0},
    max_age_ms={"type": "integer", "minimum": 1},
)
_PROPERTIES["entity_ref"]["pattern"] = r"^entity://[^/]+$"
_PROPERTIES["destination_ref"]["pattern"] = r"^destination://\S+$"
_PROPERTIES["acquire_invocation_ref"]["pattern"] = r"^invocation://object-acquire/[^/]+$"
_PROPERTIES["held_invocation_ref"]["pattern"] = r"^invocation://[^/]+/[^/]+$"


def input_schema(*, action: bool, operation: str | None = None) -> dict[str, Any]:
    properties = deepcopy(_PROPERTIES)
    if operation:
        properties["operation"] = {"const": operation}
    if action:
        properties.update(preparation_ref=deepcopy(_TEXT), assignment_ref=deepcopy(_TEXT))
    return {
        "type": "object", "additionalProperties": False,
        "properties": properties, "required": list(properties),
        "allOf": [
            {"if": {"properties": {"operation": {"const": kind}}},
             "then": {"properties": {"parameters": {
                 "type": "object", "additionalProperties": False,
                 "properties": deepcopy(params), "required": list(params),
             }}}}
            for kind, params in _PARAMETERS.items()
        ],
    }


def validate(arguments: Mapping[str, Any], *, action: bool, operation: str | None = None) -> None:
    # JSON Schema's number type accepts NaN in Python; transport values must be finite.
    json.dumps(arguments, allow_nan=False)
    Draft202012Validator(input_schema(action=action, operation=operation)).validate(arguments)
    if arguments["freshness_ms"] > arguments["max_age_ms"]:
        raise ValueError("held operation observation is stale")


def cycle_sourced_place_schema(*, action: bool) -> dict[str, Any]:
    schema = deepcopy(input_schema(action=action, operation="place"))
    schema["properties"]["cycle_invocation_ref"] = {
        "type": "string", "pattern": r"^invocation://(?:object-pour_cycle|tool-stir_cycle)/[^/]+$",
    }
    schema["required"].remove("acquire_invocation_ref")
    schema["allOf"].append({
        "oneOf": [
            {"required": ["cycle_invocation_ref"], "not": {"required": ["acquire_invocation_ref"]}},
            {"required": ["acquire_invocation_ref"], "not": {"required": ["cycle_invocation_ref"]}},
        ]
    })
    return schema


def validate_cycle_sourced_place(arguments: Mapping[str, Any], *, action: bool) -> None:
    schema = cycle_sourced_place_schema(action=action)
    json.dumps(arguments, allow_nan=False)
    Draft202012Validator(schema).validate(arguments)
    if arguments["freshness_ms"] > arguments["max_age_ms"]:
        raise ValueError("held operation observation is stale")


def _planning(tool_id: str, *, action: bool) -> dict[str, Any]:
    return {
        "schema_version": "paos-tool-spec-policy/v1", "capabilities": [tool_id],
        "input_binding_keys": ["entity_ref", "destination_ref"],
        "scene_write_behavior": "new_revision" if action else "none",
    }


PREPARE_HELD_TOOL_SPEC = {
    "tool_id": "manipulation.prepare_held", "endpoint_id": "held_preparation",
    "operation": "prepare", "semantics": "query",
    "description": "Prepare a bounded operation from current held-object and scene evidence without motion.",
    "planning": _planning("manipulation.prepare_held", action=False),
    "input_schema": input_schema(action=False),
    "output_schema": {
        "oneOf": [
            {"type": "object", "additionalProperties": False,
             "required": ["status", "entity_ref", "arguments", "motion_authorized"],
             "properties": {"status": {"const": "available"}, "entity_ref": _TEXT,
                            "arguments": input_schema(action=True), "motion_authorized": {"const": False}}},
            {"type": "object", "additionalProperties": False,
             "required": ["status", "error", "motion_authorized"],
             "properties": {"status": {"const": "unavailable"}, "error": _TEXT,
                            "motion_authorized": {"const": False}}},
        ],
    },
}


def action_spec(operation: str) -> dict[str, Any]:
    tool_id = OPERATIONS[operation]
    schema = input_schema(action=True, operation=operation)
    result_properties = deepcopy(schema["properties"])
    result_properties.update({
        "status": {"enum": ["succeeded", "failed", "cancelled", "stopped", "unknown"]},
        "new_scene_revision": {"type": ["string", "null"]},
        "operation_completed": {"type": "boolean"},
        "measurements": {"type": "object"},
        "evidence_refs": {"type": "array", "items": _TEXT},
        "capability_outcome_summary": {"type": "object"},
    })
    planning = _planning(tool_id, action=True)
    planning.update(
        argument_projection="prepared_held_operation_v1",
        argument_projection_plan={
            "projection_id": "prepared_held_operation_v1", "join_field": "entity_ref",
            "source_slots": {"preparation": {
                "tool_id": "manipulation.prepare_held", "source_scope": "predecessor",
                "source_field_map": {key: ["arguments", key] for key in schema["required"]},
            }},
            "top_level_fields": [],
        },
    )
    return {
        "tool_id": tool_id,
        "endpoint_id": "object_placement" if operation == "place" else tool_id.replace(".", "_"),
        "operation": operation, "semantics": "action",
        "description": f"Execute one prepared {operation} operation and report measured outcome and possession.",
        "planning": planning, "input_schema": schema,
        "output_schema": {
            "type": "object", "required": ["invocation_id", "attempt_id", "phase"],
            "properties": {
                "invocation_id": _TEXT, "attempt_id": _TEXT, "phase": _TEXT,
                "result": {"type": "object", "additionalProperties": False,
                           "properties": result_properties,
                           "required": ["status", "operation_completed", "measurements", "evidence_refs",
                                        "capability_outcome_summary", *schema["required"]]},
            },
        },
    }


POUR_TOOL_SPEC = action_spec("pour")
STIR_TOOL_SPEC = action_spec("stir")
HELD_PLACE_TOOL_SPEC = action_spec("place")


_CYCLE_PARAMETERS = {
    "pour_cycle": {"tilt_rad": {**_POSITIVE, "maximum": math.pi}, "hold_s": _POSITIVE},
    "stir_cycle": {
        "radius_m": _POSITIVE, "depth_m": _POSITIVE, "turns": _POSITIVE,
        "duration_s": _POSITIVE, "direction": {"enum": ["cw", "ccw"]},
    },
}
_CYCLE_PROPERTIES = {
    name: deepcopy(_TEXT) for name in (
        "entity_ref", "destination_ref", "return_destination_ref", "observation_ref",
        "scene_revision", "frame_id", "calibration_ref", "capability_snapshot_ref",
    )
}
_CYCLE_PROPERTIES["entity_ref"]["pattern"] = r"^entity://[^/]+$"
for _key in ("destination_ref", "return_destination_ref"):
    _CYCLE_PROPERTIES[_key]["pattern"] = r"^destination://\S+$"
_CYCLE_PROPERTIES.update(
    operation={"enum": list(CYCLE_OPERATIONS)}, parameters={"type": "object"},
    freshness_ms={"type": "integer", "minimum": 0}, max_age_ms={"type": "integer", "minimum": 1},
)


def cycle_input_schema(*, action: bool, operation: str | None = None) -> dict[str, Any]:
    properties = deepcopy(_CYCLE_PROPERTIES)
    if operation:
        properties["operation"] = {"const": operation}
    if action:
        properties.update(preparation_ref=deepcopy(_TEXT), assignment_ref=deepcopy(_TEXT))
    return {
        "type": "object", "additionalProperties": False,
        "properties": properties, "required": list(properties),
        "allOf": [
            {"if": {"properties": {"operation": {"const": kind}}},
             "then": {"properties": {"parameters": {
                 "type": "object", "additionalProperties": False,
                 "properties": deepcopy(params), "required": list(params),
             }}}}
            for kind, params in _CYCLE_PARAMETERS.items()
        ],
    }


def cycle_action_spec(operation: str) -> dict[str, Any]:
    tool_id = CYCLE_OPERATIONS[operation]
    schema = cycle_input_schema(action=True, operation=operation)
    planning = _planning(tool_id, action=True)
    planning["input_binding_keys"] = ["entity_ref", "destination_ref", "return_destination_ref"]
    planning.update(
        argument_projection="prepared_cycle_operation_v1",
        argument_projection_plan={
            "projection_id": "prepared_cycle_operation_v1", "join_field": "entity_ref",
            "source_slots": {"preparation": {
                "tool_id": "manipulation.prepare_cycle", "source_scope": "predecessor",
                "source_field_map": {key: ["arguments", key] for key in schema["required"]},
            }},
            "top_level_fields": [],
        },
    )
    result_properties = deepcopy(schema["properties"])
    result_properties.update({
        "status": {"enum": ["succeeded", "failed", "cancelled", "stopped", "unknown"]},
        "new_scene_revision": {"type": ["string", "null"]}, "operation_completed": {"type": "boolean"},
        "process_completed": {"type": "boolean"}, "return_completed": {"type": "boolean"},
        "failed_phase": {"type": ["string", "null"]}, "possession_state": {"enum": ["empty", "holding", "uncertain"]},
        "phase_facts": {"type": "object"}, "completed_phases": {"type": "array", "items": _TEXT},
        "measurements": {"type": "object"}, "evidence_refs": {"type": "array", "items": _TEXT},
        "capability_outcome_summary": {"type": "object"},
    })
    return {
        "tool_id": tool_id, "endpoint_id": tool_id.replace(".", "_"), "operation": operation,
        "semantics": "action", "description": f"Execute a complete {operation} cycle from empty hand through return.",
        "planning": planning, "input_schema": schema,
        "output_schema": {"type": "object", "required": ["invocation_id", "attempt_id", "phase"],
                          "properties": {"invocation_id": _TEXT, "attempt_id": _TEXT, "phase": _TEXT,
                                         "result": {"type": "object", "additionalProperties": False,
                                                    "properties": result_properties,
                                                    "required": ["status", "operation_completed", "process_completed",
                                                                 "return_completed", "failed_phase", "possession_state",
                                                                 "phase_facts", "completed_phases",
                                                                 "measurements", "evidence_refs", "capability_outcome_summary",
                                                                 *schema["required"]]}}},
    }


_PREPARE_CYCLE_OUTPUT_SCHEMA = deepcopy(PREPARE_HELD_TOOL_SPEC["output_schema"])
_PREPARE_CYCLE_OUTPUT_SCHEMA["oneOf"][0]["properties"]["arguments"] = cycle_input_schema(action=True)
PREPARE_CYCLE_TOOL_SPEC = {
    "tool_id": "manipulation.prepare_cycle", "endpoint_id": "cycle_preparation", "operation": "prepare",
    "semantics": "query", "description": "Prepare a complete manipulation cycle from empty hand without motion.",
    "planning": _planning("manipulation.prepare_cycle", action=False),
    "input_schema": cycle_input_schema(action=False),
    "output_schema": _PREPARE_CYCLE_OUTPUT_SCHEMA,
}
POUR_CYCLE_TOOL_SPEC = cycle_action_spec("pour_cycle")
STIR_CYCLE_TOOL_SPEC = cycle_action_spec("stir_cycle")


def extended_place_spec(legacy_spec):
    """The lab deployment accepts legacy placement and current held preparation."""
    value = deepcopy(HELD_PLACE_TOOL_SPEC)
    held_schema = cycle_sourced_place_schema(action=True)
    value["input_schema"] = held_schema
    held_result = value["output_schema"]["properties"]["result"]
    held_result["properties"]["cycle_invocation_ref"] = deepcopy(held_schema["properties"]["cycle_invocation_ref"])
    held_result["required"].remove("acquire_invocation_ref")
    source = value["planning"]["argument_projection_plan"]["source_slots"]["preparation"]
    source["source_field_map"].pop("acquire_invocation_ref")
    value["planning"]["argument_projection_plan"]["top_level_fields"] = [
        "acquire_invocation_ref", "cycle_invocation_ref",
    ]
    for key in ("input_schema",):
        old, new = legacy_spec[key], value[key]
        value[key] = {"type": "object", "properties": {**old["properties"], **new["properties"]},
                      "oneOf": [deepcopy(old), new]}
    old_result = legacy_spec["output_schema"]["properties"]["result"]
    new_result = value["output_schema"]["properties"]["result"]
    value["output_schema"]["properties"]["result"] = {"oneOf": [deepcopy(old_result), new_result]}
    return value


def extended_held_preparation_spec(spec):
    value = deepcopy(spec)
    schema = deepcopy(spec["input_schema"])
    schema["properties"]["cycle_invocation_ref"] = cycle_sourced_place_schema(action=False)["properties"]["cycle_invocation_ref"]
    schema["required"].remove("acquire_invocation_ref")
    schema["allOf"].append({
        "if": {"properties": {"operation": {"const": "place"}}},
        "then": {"oneOf": [
            {"required": ["acquire_invocation_ref"], "not": {"required": ["cycle_invocation_ref"]}},
            {"required": ["cycle_invocation_ref"], "not": {"required": ["acquire_invocation_ref"]}},
        ]},
        "else": {"required": ["acquire_invocation_ref"], "not": {"required": ["cycle_invocation_ref"]}},
    })
    value["output_schema"]["oneOf"][0]["properties"]["arguments"] = cycle_sourced_place_schema(action=True)
    value["planning"]["input_binding_keys"] = ["entity_ref", "destination_ref"]
    value["input_schema"] = schema
    return value


def _check_holding(possession, request, *, owner=None):
    # The latest held invocation is always required. Acquisition/cycle source is
    # optional for placement projection, but a supplied source must agree.
    if "acquire_invocation_ref" in request and request["acquire_invocation_ref"] != possession.acquire_invocation_ref:
        raise ValueError("held operation acquisition source mismatch")
    if "cycle_invocation_ref" in request and request["cycle_invocation_ref"] != possession.cycle_invocation_ref:
        raise ValueError("held operation cycle source mismatch")
    possession.validate_begin(
        request["operation"], owner=owner or possession.owner,
        entity_ref=request["entity_ref"], acquire_ref=possession.acquire_invocation_ref,
        cycle_ref=possession.cycle_invocation_ref,
    )
    if possession.last_invocation_ref != request["held_invocation_ref"]:
        raise ValueError("held operation source is not the latest possession result")
    if possession.scene_revision != request["scene_revision"]:
        raise ValueError("held operation scene is stale")


class HeldPreparationEndpoint:
    def __init__(self, provider, possession):
        self.provider, self.possession = provider, possession

    def invoke(self, arguments):
        if arguments.get("operation") == "place" and "cycle_invocation_ref" in arguments:
            validate_cycle_sourced_place(arguments, action=False)
        else:
            validate(arguments, action=False)
        _check_holding(self.possession, arguments)
        try:
            result = self.provider.prepare_held(deepcopy(arguments))
        except Exception as exc:
            return {"status": "unavailable", "motion_authorized": False,
                    "error": f"held_preparation_provider_failed:{type(exc).__name__}"}
        if not isinstance(result, Mapping) or result.get("status") != "available":
            return {"status": "unavailable", "motion_authorized": False,
                    "error": str((result or {}).get("error", "held_preparation_unavailable"))
                    if isinstance(result, Mapping) else "held_preparation_unavailable"}
        prepared = result.get("arguments")
        if prepared.get("operation") == "place" and "cycle_invocation_ref" in prepared:
            validate_cycle_sourced_place(prepared, action=True)
        else:
            validate(prepared, action=True)
        if any(prepared.get(key) != value for key, value in arguments.items()):
            raise ValueError("held preparation changed request identity or parameters")
        _check_holding(self.possession, prepared)
        return {"status": "available", "motion_authorized": False,
                "entity_ref": arguments["entity_ref"], "arguments": deepcopy(prepared)}


class CyclePreparationEndpoint:
    """Prepare an entire empty-hand cycle without starting physical work."""

    def __init__(self, provider, possession):
        self.provider, self.possession = provider, possession

    def invoke(self, arguments):
        validate_cycle(arguments, action=False)
        if self.possession.state != "empty":
            return {"status": "unavailable", "motion_authorized": False,
                    "error": "cycle preparation requires empty hand"}
        try:
            result = self.provider.prepare_cycle(deepcopy(arguments))
        except Exception as exc:
            return {"status": "unavailable", "motion_authorized": False,
                    "error": f"cycle_preparation_provider_failed:{type(exc).__name__}"}
        if not isinstance(result, Mapping) or result.get("status") != "available":
            error = result.get("error", "cycle_preparation_unavailable") if isinstance(result, Mapping) else "cycle_preparation_unavailable"
            return {"status": "unavailable", "motion_authorized": False, "error": str(error)}
        prepared = result.get("arguments")
        validate_cycle(prepared, action=True)
        if any(prepared.get(key) != value for key, value in arguments.items()):
            raise ValueError("cycle preparation changed request identity or parameters")
        if self.possession.state != "empty":
            raise ValueError("possession changed during cycle preparation")
        return {"status": "available", "motion_authorized": False,
                "entity_ref": arguments["entity_ref"], "arguments": deepcopy(prepared)}


def validate_cycle(arguments: Mapping[str, Any], *, action: bool, operation: str | None = None) -> None:
    json.dumps(arguments, allow_nan=False)
    Draft202012Validator(cycle_input_schema(action=action, operation=operation)).validate(arguments)
    if arguments["freshness_ms"] > arguments["max_age_ms"]:
        raise ValueError("cycle observation is stale")


def project_cycle_result(raw, arguments, possession, invocation_id):
    status = raw.get("status", "unknown")
    known = raw.get("outcome_known") is True
    refs = raw.get("artifact_refs", [])
    if not isinstance(refs, (list, tuple)) or not all(
        isinstance(ref, str) and ref.startswith("artifact://") for ref in refs
    ):
        refs = []
    events = raw.get("phase_events", [])
    samples = raw.get("feedback_samples", [])
    process_feedback = {}
    process_event = next((event for event in events if isinstance(event, Mapping)
                          and event.get("phase") == "process"), None) if isinstance(events, (list, tuple)) else None
    if process_event is not None:
        try:
            start_s, end_s = process_event.get("started_at_s"), process_event.get("completed_at_s")
            if not isinstance(start_s, (int, float)) or not isinstance(end_s, (int, float)):
                raise CycleProtocolError("process phase requires observed start and completion times")
            samples = [sample for sample in samples if isinstance(sample, Mapping)
                       and isinstance(sample.get("timestamp_s"), (int, float))
                       and start_s <= sample["timestamp_s"] <= end_s]
            process_feedback = evaluate_process_feedback(
                arguments["operation"], samples, arguments["parameters"], raw.get("evaluation_profile", {}),
            )
        except (CycleProtocolError, KeyError, TypeError, ValueError, OverflowError):
            known = False
    protocol_events = []
    for event in events if isinstance(events, (list, tuple)) else ():
        if not isinstance(event, Mapping):
            protocol_events.append(event)
            continue
        normalized = deepcopy(dict(event))
        if normalized.get("phase") == "process":
            facts = dict(normalized.get("facts", {}))
            facts["process_measurement_qualified"] = process_feedback.get("process_completed") is True
            normalized["facts"] = facts
        protocol_events.append(normalized)
    try:
        phase_result = CyclePhaseProtocol().consume(protocol_events)
    except CycleProtocolError:
        phase_result = {"phase_facts": {}, "completed_phases": [], "failed_phase": None,
                        "outcome_known": False, "process_completed": False, "return_completed": False}
        known = False
    known = known and phase_result["outcome_known"] is True
    metrics = process_feedback
    process_completed = (phase_result["process_completed"] and bool(refs))
    return_completed = phase_result["return_completed"] and bool(refs)
    identity_matches = (raw.get("entity_ref") == arguments["entity_ref"]
                        and raw.get("destination_ref") == arguments["destination_ref"])
    process_completed = process_completed and identity_matches
    expected_success = (
        process_completed and return_completed and known and bool(refs)
        and phase_result["outcome_known"] is True
        and raw.get("possession_state") == "empty"
        and raw.get("object_support_state") == "on_support"
        and isinstance(raw.get("new_scene_revision"), str)
        and raw["new_scene_revision"] != arguments["scene_revision"]
        and raw.get("world_change_started") is True
        and raw.get("entity_ref") == arguments["entity_ref"]
        and raw.get("destination_ref") == arguments["destination_ref"]
        and raw.get("return_destination_ref") == arguments["return_destination_ref"]
    )
    process_goal_failed = (
        process_event is not None and process_event.get("status") == "completed"
        and process_feedback.get("process_completed") is False
    )
    known_phase_failure = known and (phase_result.get("failed_phase") is not None or process_goal_failed)
    invalid_success = status == "succeeded" and not expected_success and not known_phase_failure
    if status == "succeeded" and known_phase_failure:
        status = "failed"
    elif status not in {"succeeded", "failed", "cancelled", "stopped", "unknown"} or not known or invalid_success:
        status, known = "unknown", False
    if not known:
        possession.state = "uncertain"
        possession.scene_revision = None
    else:
        possession.settle(arguments["operation"], {**raw, "status": status, "outcome_known": True})
        if possession.state == "holding":
            possession.owner = f"paos:{arguments['_task_id']}"
            possession.entity_ref = arguments["entity_ref"]
            possession.acquire_invocation_ref = None
            possession.cycle_invocation_ref = invocation_id
        possession.scene_revision = raw.get("new_scene_revision") if raw.get("new_scene_revision") else None
    possession.last_invocation_ref = invocation_id
    failed_phase = phase_result.get("failed_phase") or ("process" if process_goal_failed else None)
    summary = {
        "version": "capability_outcome_summary_v1", "status": status,
        "capability_phase": "none", "world_change_started": raw.get("world_change_started"),
        "outcome_known": known, "failure_owner": "evidence" if invalid_success else raw.get("failure_owner"),
        "failure_code": "missing_cycle_postconditions" if invalid_success else raw.get("failure_code"),
        "possession_state": possession.state, "phase": failed_phase,
        "process_completed": process_completed, "return_completed": return_completed,
        "evidence_availability": "complete" if expected_success else "partial" if refs else "none",
        "artifact_refs": list(refs), "bounded_metric_names": sorted(metrics),
        "retryable_in_revision": False, "requires_replan": status != "succeeded",
        "recommended_action": "continue" if status == "succeeded" else "stop",
    }
    return {
        **{key: value for key, value in deepcopy(arguments).items() if key != "_task_id"},
        "status": status, "new_scene_revision": raw.get("new_scene_revision"),
        "operation_completed": status == "succeeded" and expected_success,
        "process_completed": process_completed,
        "return_completed": return_completed,
        "phase_facts": phase_result["phase_facts"],
        "completed_phases": phase_result["completed_phases"],
        "failed_phase": failed_phase, "possession_state": possession.state,
        "measurements": deepcopy(dict(metrics)),
        "evidence_refs": list(refs), "capability_outcome_summary": summary,
    }


class CycleActionDriver:
    def __init__(self, driver, arguments, possession, invocation_id):
        self.driver, self.arguments = driver, arguments
        self.possession, self.invocation_id = possession, invocation_id

    def poll(self):
        try:
            raw = self.driver.poll()
        except Exception:
            self.possession.state, self.possession.scene_revision = "uncertain", None
            raise
        return None if raw is None else project_cycle_result(raw, self.arguments, self.possession, self.invocation_id)

    def cancel(self):
        try:
            self.driver.cancel()
        except Exception:
            self.possession.state, self.possession.scene_revision = "uncertain", None
            raise

    def stop(self):
        try:
            self.driver.stop()
        except Exception:
            self.possession.state, self.possession.scene_revision = "uncertain", None
            raise


class CycleActionEndpoint:
    def __init__(self, operation, client, resolve, possession):
        self.operation, self.client, self.resolve = operation, client, resolve
        self.possession = possession

    def admit(self, arguments):
        raise ValueError("complete cycle requires a task-owned caller")

    def admit_for_caller(self, arguments, *, caller_id):
        parts = caller_id.split(":") if isinstance(caller_id, str) else []
        if len(parts) != 4 or parts[0] != "paos" or not all(parts[1:]):
            raise ValueError("cycle Action caller must be bound to a PAOS task record")
        validate_cycle(arguments, action=True, operation=self.operation)
        if self.possession.state != "empty":
            raise ValueError("complete cycle requires empty hand")
        public = deepcopy(arguments)
        owner = f"paos:{parts[1]}"

        def resolve_current():
            if self.possession.state != "empty":
                raise ValueError("complete cycle requires empty hand")
            resolved = deepcopy(dict(self.resolve(self.operation, deepcopy(public))))
            if any(resolved.get(key) != value for key, value in public.items() if key != "operation"):
                raise ValueError("resolved cycle preparation changed inputs")
            assignment = resolved.get("assignment", {})
            if assignment.get("task_id") != parts[1] or assignment.get("assignment_ref") != public["assignment_ref"]:
                raise ValueError("cycle assignment does not belong to this task")
            resolved.update(operation=self.operation, task_id=parts[1])
            return resolved

        resolve_current()

        def start(invocation_id, attempt_id):
            resolved = resolve_current()
            self.possession.begin(self.operation, owner=owner, entity_ref=public["entity_ref"])
            resolved["cycle_invocation_id"] = invocation_id
            try:
                driver = self.client.start(self.operation, invocation_id, owner, resolved)
            except Exception:
                result = project_cycle_result({"status": "unknown", "outcome_known": False},
                                              {**public, "_task_id": parts[1]}, self.possession, invocation_id)
                return ActionAdmission(terminal_result=result)
            return ActionAdmission(driver=CycleActionDriver(
                driver, {**public, "_task_id": parts[1]}, self.possession, invocation_id,
            ))

        return ActionAdmission(start=start)


def _measured_completion(raw, arguments):
    if raw.get("entity_ref") != arguments["entity_ref"] or raw.get("destination_ref") != arguments["destination_ref"]:
        return False
    metrics = raw.get("measurements")
    if not isinstance(metrics, Mapping):
        return False
    def at_least(key, limit):
        value = metrics.get(key)
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= limit
    params = arguments["parameters"]
    if arguments["operation"] == "pour":
        return at_least("aligned_hold_s", params["hold_s"]) and at_least("maximum_tilt_rad", params["tilt_rad"])
    if arguments["operation"] == "stir":
        return at_least("in_container_turns", params["turns"]) and at_least("in_container_duration_s", params["duration_s"])
    return bool(metrics)  # Placement postconditions are checked separately below.


def project_result(raw, arguments, possession, invocation_id):
    phase = arguments["operation"]
    status = raw.get("status", "unknown")
    known = raw.get("outcome_known") is True
    refs = raw.get("artifact_refs", [])
    if not isinstance(refs, (list, tuple)) or not all(isinstance(ref, str) and ref.startswith("artifact://") for ref in refs):
        refs = []
    measurements = raw.get("measurements", {})
    measured = _measured_completion(raw, arguments)
    if not isinstance(measurements, Mapping):
        measurements = {}
    try:
        json.dumps(measurements, allow_nan=False)
    except (ValueError, TypeError):
        measured = False
        measurements = {}
    completed = raw.get("operation_completed") is True and measured and bool(refs) and known
    expected_holding = "empty" if phase == "place" else "holding"
    postconditions = (
        all(raw.get(key) is True for key in ("release_confirmed", "retreat_completed", "clear_of_target", "observation_ready"))
        if phase == "place" else raw.get("returned_to_safe_pose") is True
    )
    invalid_success = status == "succeeded" and not (
        completed and postconditions and raw.get("possession_state") == expected_holding
        and isinstance(raw.get("new_scene_revision"), str) and bool(raw["new_scene_revision"].strip())
        and raw["new_scene_revision"] != arguments["scene_revision"]
        and raw.get("world_change_started") is True
    )
    if status not in {"succeeded", "failed", "cancelled", "stopped", "unknown"} or not known or invalid_success:
        status, known = "unknown", False
    if not known:
        completed = False
    possession.settle(phase, {**raw, "status": status, "outcome_known": known})
    possession.last_invocation_ref = invocation_id
    possession.scene_revision = (
        raw.get("new_scene_revision") or arguments["scene_revision"]
        if known and (raw.get("new_scene_revision") or raw.get("world_change_started") is False) else None
    )
    summary = {
        "version": "capability_outcome_summary_v1", "status": status,
        "capability_phase": "hold" if status == "succeeded" and phase != "place" else "none",
        "world_change_started": raw.get("world_change_started"), "outcome_known": known,
        "failure_owner": "evidence" if invalid_success else raw.get("failure_owner"),
        "failure_code": "missing_held_postconditions" if invalid_success else raw.get("failure_code"),
        "possession_state": possession.state, "phase": phase,
        "evidence_availability": "complete" if status == "succeeded" else "partial" if refs else "none",
        "artifact_refs": list(refs), "bounded_metric_names": sorted(measurements),
        "retryable_in_revision": False, "requires_replan": status != "succeeded",
        "recommended_action": "continue" if status == "succeeded" else "stop",
    }
    return {
        **deepcopy(arguments), "status": status, "held_invocation_ref": invocation_id,
        "new_scene_revision": raw.get("new_scene_revision"), "operation_completed": completed,
        "measurements": deepcopy(dict(measurements)), "evidence_refs": list(refs),
        "capability_outcome_summary": summary,
    }


class HeldActionDriver:
    def __init__(self, driver, arguments, possession, invocation_id):
        self.driver, self.arguments = driver, arguments
        self.possession, self.invocation_id = possession, invocation_id

    def poll(self):
        try:
            raw = self.driver.poll()
        except Exception:
            self.possession.state = "uncertain"
            self.possession.scene_revision = None
            raise
        return None if raw is None else project_result(raw, self.arguments, self.possession, self.invocation_id)

    def cancel(self):
        try:
            self.driver.cancel()
        except Exception:
            self.possession.state, self.possession.scene_revision = "uncertain", None
            raise

    def stop(self):
        try:
            self.driver.stop()
        except Exception:
            self.possession.state, self.possession.scene_revision = "uncertain", None
            raise


class HeldActionEndpoint:
    def __init__(self, operation, client, resolve, possession, *, legacy_place=None):
        self.operation, self.client, self.resolve = operation, client, resolve
        self.possession, self.legacy_place = possession, legacy_place

    def admit(self, arguments):
        raise ValueError("held manipulation requires a task-owned caller")

    def admit_for_caller(self, arguments, *, caller_id):
        if self.legacy_place is not None and "held_invocation_ref" not in arguments:
            # Once a held operation has occurred, old acquire-only provenance is insufficient.
            if (self.possession.cycle_invocation_ref is not None
                    or self.possession.last_invocation_ref != self.possession.acquire_invocation_ref):
                raise ValueError("place requires the latest held preparation")
            return self.legacy_place.admit_for_caller(arguments, caller_id=caller_id)
        parts = caller_id.split(":") if isinstance(caller_id, str) else []
        if len(parts) != 4 or parts[0] != "paos" or not all(parts[1:]):
            raise ValueError("held Action caller must be bound to a PAOS task record")
        if self.operation == "place" and "cycle_invocation_ref" in arguments:
            validate_cycle_sourced_place(arguments, action=True)
        else:
            validate(arguments, action=True, operation=self.operation)
        public = deepcopy(arguments)
        owner = f"paos:{parts[1]}"
        _check_holding(self.possession, public, owner=owner)

        def resolve_current():
            _check_holding(self.possession, public, owner=owner)
            resolved = deepcopy(dict(self.resolve(self.operation, deepcopy(public))))
            if any(resolved.get(key) != value for key, value in public.items()):
                raise ValueError("resolved held preparation changed inputs")
            assignment = resolved.get("assignment", {})
            if assignment.get("task_id") != parts[1] or assignment.get("assignment_ref") != public["assignment_ref"]:
                raise ValueError("held assignment does not belong to this task")
            resolved.update(task_id=parts[1])
            if self.possession.acquire_invocation_ref is not None:
                resolved["acquire_invocation_id"] = self.possession.acquire_invocation_ref
            else:
                resolved["cycle_invocation_id"] = self.possession.cycle_invocation_ref
            return resolved

        resolve_current()

        def start(invocation_id, attempt_id):
            resolved = resolve_current()
            self.possession.begin(self.operation, owner=owner, entity_ref=public["entity_ref"],
                                  acquire_ref=self.possession.acquire_invocation_ref,
                                  cycle_ref=self.possession.cycle_invocation_ref)
            try:
                driver = self.client.start(self.operation, invocation_id, owner, resolved)
            except Exception:
                # A lost start acknowledgement does not prove that motion never began.
                result = project_result({"status": "unknown", "outcome_known": False,
                                         "failure_code": "held_action_start_unknown"},
                                        public, self.possession, invocation_id)
                return ActionAdmission(terminal_result=result)
            return ActionAdmission(driver=HeldActionDriver(driver, public, self.possession, invocation_id))

        return ActionAdmission(start=start)
