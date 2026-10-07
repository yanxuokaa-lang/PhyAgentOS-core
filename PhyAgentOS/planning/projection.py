"""Explicit projection from live, provider-neutral ToolSpecs to planning policy."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .contracts import (
    ArgumentProjectionPlan,
    ArgumentProjectionSourcePlan,
    ResourceClaim,
    ToolSpecPolicy,
    canonical_sha256,
)


class ToolSpecProjectionError(ValueError):
    """A live ToolSpec cannot safely participate in planning admission."""


class ArgumentProjectionError(ValueError):
    """A declared consumer projection cannot be compiled from its source record."""


class _PlanningExtension(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(pattern=r"^paos-tool-spec-policy/v1$")
    capabilities: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()
    required_evidence: tuple[str, ...] = ()
    produced_evidence: tuple[str, ...] = ()
    expected_effects: tuple[str, ...] = ()
    resource_claims: tuple[ResourceClaim, ...] = ()
    scene_write_behavior: str = "none"
    failure_classes: tuple[str, ...] = ()
    idempotency: str = "unknown"
    refreshes_scene: bool = False
    input_binding_keys: tuple[str, ...] = ()
    requires_before_plan: bool = False
    trusted_argument_builder: str | None = None
    argument_projection: str | None = None
    argument_projection_plan: ArgumentProjectionPlan | None = None


_PROVIDER_PRIVATE = re.compile(
    r"(?:robotwin|sapien|xpolicylab|dora|vendor[-_ ]?sdk|ultralytics|\byolo\b)",
    re.IGNORECASE,
)


def _unique_strings(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    if len(values) != len(set(values)):
        raise ToolSpecProjectionError(f"planning {label} must contain unique values")
    if any(not value.strip() for value in values):
        raise ToolSpecProjectionError(f"planning {label} must contain non-empty values")
    return values


def project_tool_spec(spec: Mapping[str, Any]) -> ToolSpecPolicy:
    """Project only an explicit ToolSpec ``planning`` extension.

    The returned policy is a planning projection and never changes the live
    ToolSpec or grants execution authority. Missing or malformed planning
    metadata is rejected instead of guessed from provider implementation names.
    """
    if not isinstance(spec, Mapping):
        raise ToolSpecProjectionError("ToolSpec must be an object")
    value = dict(spec)
    for key in ("tool_id", "semantics"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ToolSpecProjectionError(f"ToolSpec {key} must be a non-empty string")
    if value["semantics"] not in {"query", "action", "session"}:
        raise ToolSpecProjectionError("ToolSpec semantics is unsupported")
    try:
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ToolSpecProjectionError("ToolSpec must contain finite JSON values") from exc
    if _PROVIDER_PRIVATE.search(serialized):
        raise ToolSpecProjectionError("ToolSpec contains provider-specific planning data")
    extension = value.get("planning")
    if not isinstance(extension, Mapping):
        raise ToolSpecProjectionError("ToolSpec is missing explicit planning extension")
    try:
        parsed = _PlanningExtension.model_validate(extension)
    except ValidationError as exc:
        raise ToolSpecProjectionError(f"invalid ToolSpec planning extension: {exc}") from exc
    for label in (
        "capabilities", "preconditions", "required_evidence", "produced_evidence",
        "expected_effects", "failure_classes",
        "input_binding_keys",
    ):
        _unique_strings(getattr(parsed, label), label)
    if parsed.argument_projection is not None and not parsed.argument_projection.strip():
        raise ToolSpecProjectionError("planning argument_projection must be non-empty")
    projection_plan = None
    if isinstance(extension.get("argument_projection_plan"), Mapping):
        try:
            projection_plan = ArgumentProjectionPlan.model_validate(
                extension["argument_projection_plan"]
            )
        except ValidationError as exc:
            raise ToolSpecProjectionError(
                f"invalid ToolSpec argument projection plan: {exc}"
            ) from exc
        if parsed.argument_projection != projection_plan.projection_id:
            raise ToolSpecProjectionError(
                "argument_projection must match argument_projection_plan.projection_id"
            )
    try:
        policy = ToolSpecPolicy(
            tool_id=value["tool_id"],
            semantics=value["semantics"],
            spec_digest=canonical_sha256(value),
            capabilities=parsed.capabilities,
            preconditions=parsed.preconditions,
            required_evidence=parsed.required_evidence,
            produced_evidence=parsed.produced_evidence,
            expected_effects=parsed.expected_effects,
            resource_claims=parsed.resource_claims,
            scene_write_behavior=parsed.scene_write_behavior,
            failure_classes=parsed.failure_classes,
            idempotency=parsed.idempotency,
            refreshes_scene=parsed.refreshes_scene,
            input_binding_keys=parsed.input_binding_keys,
            requires_before_plan=parsed.requires_before_plan,
            trusted_argument_builder=parsed.trusted_argument_builder,
            argument_projection=parsed.argument_projection,
            argument_projection_plan=projection_plan,
        )
    except (ValidationError, ValueError) as exc:
        raise ToolSpecProjectionError(f"invalid ToolSpec planning policy: {exc}") from exc
    return policy


def execute_argument_projection(
    plan: ArgumentProjectionPlan,
    *,
    records: Mapping[str, tuple[Mapping[str, Any], Mapping[str, Any] | None]],
    literals: Mapping[str, Any],
    source_record_id: str | None = None,
    source_record_ids: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Execute a declarative projection without provider-specific field logic."""

    def read_path(root: Mapping[str, Any], path: tuple[str | int, ...]) -> Any:
        value: Any = root
        for part in path:
            if isinstance(value, Mapping) and isinstance(part, str):
                if part not in value:
                    raise ArgumentProjectionError(
                        f"projection source is missing field {'.'.join(map(str, path))}"
                    )
                value = value[part]
            elif isinstance(value, (list, tuple)) and isinstance(part, int):
                if part < 0 or part >= len(value):
                    raise ArgumentProjectionError(
                        f"projection source index is out of range for {path!r}"
                    )
                value = value[part]
            else:
                raise ArgumentProjectionError(
                    f"projection source path is invalid at {part!r}"
                )
        return value

    def read_record(record_id: str | None) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        if not isinstance(record_id, str) or record_id not in records:
            raise ArgumentProjectionError("consumer projection source record is not visible")
        arguments, response = records[record_id]
        facts = response.get("data", response) if isinstance(response, Mapping) else {}
        if not isinstance(facts, Mapping):
            raise ArgumentProjectionError("consumer projection source has no structured result")
        return arguments, facts

    def project_source(
        source: ArgumentProjectionSourcePlan,
        record_id: str,
        *,
        reject_owned_literals: bool,
    ) -> dict[str, Any]:
        arguments, facts = read_record(record_id)
        outputs = {
            *source.source_field_map,
            *source.list_field_map,
            *([source.filtered_output_field] if source.filtered_output_field else []),
            *source.unique_item_field_map,
        }
        authored = sorted(field for field in outputs if field in literals)
        if reject_owned_literals and authored:
            raise ArgumentProjectionError(
                "named projection fields are Coordinator-owned: " + ", ".join(authored)
            )
        result: dict[str, Any] = {}
        join_value = literals.get(plan.join_field)
        if source.join_field_path is not None:
            if not isinstance(join_value, str) or not join_value:
                raise ArgumentProjectionError(
                    f"consumer projection requires selected {plan.join_field}"
                )
            try:
                source_join_value = read_path(facts, source.join_field_path)
            except ArgumentProjectionError as response_error:
                try:
                    source_join_value = read_path(arguments, source.join_field_path)
                except ArgumentProjectionError:
                    raise response_error
            if source_join_value != join_value:
                raise ArgumentProjectionError(
                    f"projection source {plan.join_field} does not match selected entity"
                )
        for output_field, source_path in source.source_field_map.items():
            try:
                value = read_path(facts, source_path)
            except ArgumentProjectionError as response_error:
                try:
                    value = read_path(arguments, source_path)
                except ArgumentProjectionError:
                    raise response_error
            if output_field in literals and literals[output_field] != value:
                raise ArgumentProjectionError(
                    f"projection field {output_field!r} conflicts with its source"
                )
            result[output_field] = value
        for output_field, list_plan in source.list_field_map.items():
            try:
                collection = read_path(facts, list_plan.source_path)
            except ArgumentProjectionError as response_error:
                try:
                    collection = read_path(arguments, list_plan.source_path)
                except ArgumentProjectionError:
                    raise response_error
            if not isinstance(collection, (list, tuple)):
                raise ArgumentProjectionError(
                    f"projection list source {list_plan.source_path!r} is not an array"
                )
            values = []
            for item in collection:
                if not isinstance(item, Mapping):
                    continue
                if (
                    list_plan.where_field is not None
                    and item.get(list_plan.where_field) != list_plan.where_equals
                ):
                    continue
                value = item.get(list_plan.item_field)
                if isinstance(value, str) and value:
                    values.append(value)
            if list_plan.require_non_empty and not values:
                raise ArgumentProjectionError(
                    f"projection list field {output_field!r} is empty"
                )
            if list_plan.unique and len(values) != len(set(values)):
                raise ArgumentProjectionError(
                    f"projection list field {output_field!r} contains duplicates"
                )
            result[output_field] = values
        if source.filtered_collection is not None:
            collection = facts.get(source.filtered_collection)
            if not isinstance(collection, (list, tuple)):
                raise ArgumentProjectionError(
                    f"projection source collection {source.filtered_collection!r} is not an array"
                )
            if not isinstance(join_value, str) or not join_value:
                raise ArgumentProjectionError(
                    f"consumer projection requires selected {plan.join_field}"
                )
            join_field = source.filtered_join_field or plan.join_field
            filtered = [
                dict(item)
                for item in collection
                if isinstance(item, Mapping) and item.get(join_field) == join_value
            ]
            if not filtered:
                raise ArgumentProjectionError(
                    f"projection source collection has no {join_field} matching selected entity"
                )
            result[source.filtered_output_field] = filtered
        if source.unique_item_collection is not None:
            try:
                collection = read_path(facts, source.unique_item_collection)
            except ArgumentProjectionError as response_error:
                try:
                    collection = read_path(arguments, source.unique_item_collection)
                except ArgumentProjectionError:
                    raise response_error
            if not isinstance(collection, (list, tuple)):
                raise ArgumentProjectionError(
                    f"projection unique-item source {source.unique_item_collection!r} "
                    "is not an array"
                )
            if not isinstance(join_value, str) or not join_value:
                raise ArgumentProjectionError(
                    f"consumer projection requires selected {plan.join_field}"
                )
            join_field = source.unique_item_join_field or plan.join_field
            matches = [
                item
                for item in collection
                if isinstance(item, Mapping) and item.get(join_field) == join_value
            ]
            if len(matches) != 1:
                raise ArgumentProjectionError(
                    "projection unique-item source requires exactly one "
                    f"{join_field} match; found {len(matches)}"
                )
            matched = matches[0]
            for output_field, source_path in source.unique_item_field_map.items():
                value = read_path(matched, source_path)
                if output_field in literals and literals[output_field] != value:
                    raise ArgumentProjectionError(
                        f"projection field {output_field!r} conflicts with its source"
                    )
                result[output_field] = value
        return result

    if plan.source_slots:
        if source_record_id is not None:
            raise ArgumentProjectionError(
                "named projection sources do not accept legacy source_record_id"
            )
        if not isinstance(source_record_ids, Mapping):
            raise ArgumentProjectionError("consumer projection requires named source records")
        expected = set(plan.source_slots)
        supplied = set(source_record_ids)
        if supplied != expected:
            missing = sorted(expected - supplied)
            extra = sorted(supplied - expected)
            details = []
            if missing:
                details.append("missing " + ", ".join(missing))
            if extra:
                details.append("undeclared " + ", ".join(extra))
            raise ArgumentProjectionError(
                "named projection sources do not match ToolSpec slots: " + "; ".join(details)
            )
        result: dict[str, Any] = {}
        for slot, source in plan.source_slots.items():
            values = project_source(
                source,
                source_record_ids[slot],
                reject_owned_literals=True,
            )
            overlap = set(result) & set(values)
            if overlap:
                raise ArgumentProjectionError(
                    "named projection sources produced duplicate fields: "
                    + ", ".join(sorted(overlap))
                )
            result.update(values)
        for field in plan.top_level_fields:
            if field in literals:
                result[field] = literals[field]
        return result

    arguments, facts = read_record(source_record_id)

    if plan.source_field_map:
        result: dict[str, Any] = {}
        for output_field, source_path in plan.source_field_map.items():
            try:
                value = read_path(facts, source_path)
            except ArgumentProjectionError as response_error:
                # Query inputs are part of the same authorized record.  Some
                # producers echo only identity/results in response data while
                # freshness or bounds remain request-owned facts.
                try:
                    value = read_path(arguments, source_path)
                except ArgumentProjectionError:
                    raise response_error
            if output_field in literals and literals[output_field] != value:
                raise ArgumentProjectionError(
                    f"projection field {output_field!r} conflicts with its source"
                )
            result[output_field] = value
        for field in plan.top_level_fields:
            if field in literals:
                if field in result and result[field] != literals[field]:
                    raise ArgumentProjectionError(
                        f"projection top-level field {field!r} conflicts with its source"
                    )
                result[field] = literals[field]
        if plan.filtered_collection is not None:
            collection = facts.get(plan.filtered_collection)
            if not isinstance(collection, (list, tuple)):
                raise ArgumentProjectionError(
                    f"projection source collection {plan.filtered_collection!r} is not an array"
                )
            join_value = literals.get(plan.join_field)
            if not isinstance(join_value, str) or not join_value:
                raise ArgumentProjectionError(
                    f"consumer projection requires selected {plan.join_field}"
                )
            join_field = plan.filtered_join_field or plan.join_field
            filtered = [
                dict(item)
                for item in collection
                if isinstance(item, Mapping) and item.get(join_field) == join_value
            ]
            if not filtered:
                raise ArgumentProjectionError(
                    f"projection source collection has no {join_field} matching selected entity"
                )
            result[plan.filtered_output_field] = filtered
        return result

    def collection(name: str) -> list[Mapping[str, Any]]:
        value = facts.get(name, ())
        if not isinstance(value, (list, tuple)):
            raise ArgumentProjectionError(f"projection source collection {name!r} is not an array")
        return [item for item in value if isinstance(item, Mapping)]

    join_value = literals.get(plan.join_field)
    if not isinstance(join_value, str) or not join_value:
        raise ArgumentProjectionError(
            f"consumer projection requires selected {plan.join_field}"
        )
    entities = [
        item for item in collection(plan.entity_collection)
        if item.get(plan.join_field) == join_value
    ]
    envelopes = [
        item for item in collection(plan.envelope_collection)
        if item.get(plan.join_field) == join_value
    ]
    if len(entities) != 1:
        raise ArgumentProjectionError("consumer projection requires one uniquely matched entity")
    if len(envelopes) != 1:
        raise ArgumentProjectionError(
            "consumer projection requires one uniquely matched spatial envelope"
        )

    entity = entities[0]
    envelope = envelopes[0]
    target = {
        field: entity[field]
        for field in plan.entity_fields
        if field in entity
    }
    missing_entity_fields = [field for field in plan.entity_fields if field not in target]
    if missing_entity_fields:
        raise ArgumentProjectionError(
            "projection entity is missing fields: " + ", ".join(missing_entity_fields)
        )
    target[plan.envelope_output_field] = {
        field: envelope[field]
        for field in plan.envelope_fields
        if field in envelope
    }
    missing_envelope_fields = [
        field for field in plan.envelope_fields
        if field not in target[plan.envelope_output_field]
    ]
    if missing_envelope_fields:
        raise ArgumentProjectionError(
            "projection envelope is missing fields: " + ", ".join(missing_envelope_fields)
        )

    if plan.artifact_collection is not None and plan.artifact_output_field is not None:
        artifacts = [
            item for item in collection(plan.artifact_collection)
            if item.get(plan.join_field) == join_value
            and (
                plan.artifact_kind_field is None
                or item.get(plan.artifact_kind_field) == plan.artifact_kind_value
            )
        ]
        if artifacts:
            target[plan.artifact_output_field] = [
                {
                    field: artifact[field]
                    for field in plan.artifact_fields
                    if field in artifact
                }
                for artifact in artifacts
            ]
            for artifact, projected in zip(artifacts, target[plan.artifact_output_field]):
                missing = [field for field in plan.artifact_fields if field not in projected]
                if missing:
                    raise ArgumentProjectionError(
                        "projection artifact is missing fields: " + ", ".join(missing)
                    )

    result = {
        field: literals[field]
        for field in plan.top_level_fields
        if field in literals
    }
    for field in plan.top_level_fields:
        if field in result:
            continue
        if field in arguments:
            result[field] = arguments[field]
        elif field in facts:
            result[field] = facts[field]
    result[plan.output_collection] = [target]
    missing_top_level = [field for field in plan.top_level_fields if field not in result]
    if missing_top_level:
        raise ArgumentProjectionError(
            "projection source is missing top-level fields: " + ", ".join(missing_top_level)
        )
    return result


__all__ = [
    "ArgumentProjectionError",
    "ToolSpecProjectionError",
    "execute_argument_projection",
    "project_tool_spec",
]
